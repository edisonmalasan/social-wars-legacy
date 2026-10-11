# The gradient MATRIX alignment rule, resolved

`docs/legacy-m12-gradient-order-fix.md` section 4 measured the mechanism
behind its own regression and left the rule unresolved: **4,146 of 4,303**
gradient `MATRIX` values end mid-byte, and whether the format then requires
alignment could not be read because the pinned `swf` crate's `read_u8` comes
from `bitstream_io`, which was **not vendored** in the captured tree.

This records the resolution. The rule is now read from the source, not
inferred, and the answer is neither of the two obvious ones.

---

## 1. The blocker was a file that could simply be fetched

`bitstream-io` is a registry dependency of `swf` 0.3.0, so the captured crate
tree did not contain it. It was downloaded and **verified against the pinned
crate's own lockfile**:

| | |
|---|---|
| `swf/Cargo.lock` resolves `bitstream-io` to | `4.10.0` |
| `swf/Cargo.lock` checksum | `7eff00be299a18769011411c9def0d827e8f2d7bf0c3dbf53633147a8867fd1f` |
| SHA-256 of the downloaded `.crate` | `7EFF00BE299A18769011411C9DEF0D827E8F2D7BF0C3DBF53633147A8867FD1F` |

The two match, so the authority is the **exact resolved dependency of the
pinned crate**, not merely a version that satisfies its caret requirement. The
earlier note that the dependency "is not vendored" is a statement about the
capture, not an obstacle.

This matters beyond this document: the same `bitstream-io` is the reader
behind **every** bit-level read in `swf`, so this source was the missing
authority for the whole milestone, not only for this question.

## 2. What the reader actually does

`swf::Reader` is not a bit reader. It is a **byte-slice reader**:

- `src/read.rs:326-329` -- `pub struct Reader<'a> { input: &'a [u8], version: u8 }`.
- `src/extensions.rs:59-60` -- `impl_read_little_endian! { read_u8 for u8; ... }`
  expands to `self.read_array().map(<u8>::from_le_bytes)`, and `read_array`
  (`src/extensions.rs:38-46`) splits the slice. So **`read_u8` is a
  whole-byte read with no bit position at all.**
- `src/read.rs:377-379` -- `fn bits(&mut self) -> BitReader<'a, 'b> {
  BitReader::new(&mut self.input) }`: bit reading constructs a **fresh**
  reader over the current slice every time.

`read_gradient` (`src/read.rs:1688-1710`) then reads the MATRIX through
`self.bits()` and the flags and every record through `self.read_u8()`. The two
readers do not share a position; the `BitReader` is **dropped** when
`read_matrix` returns, and:

- `bitstream-io/src/read.rs:1525-1534` -- `BitReader` is
  `{ reader, value: u8, bits: u32 }`, holding a *partial byte*.
- `bitstream-io/src/read.rs` contains **no `impl Drop`** for `BitReader`
  (measured: zero matches for `impl.*Drop`).
- `bitstream-io/src/lib.rs:2803-2828` -- `read_bits_checked` consumes bits from
  the queue and refills it by pulling **whole bytes** from the underlying
  reader, so the slice advances one byte at a time and the residual stays in
  `queue`/`queue_bits`.

**Therefore: after the MATRIX the slice sits at the next byte boundary and the
leftover bits of the partially-consumed byte are silently discarded.** That is
`align_to_byte()` exactly -- `ceil(position / 8)` -- and it is the same
function the converter already applies after the RECT and after the fill-style
array.

So the rule is **align up, by discarding**, not "read unaligned" and not "refuse".
The shipped parser does both of the wrong things: it reads the gradient flags as
**8 bits across** the boundary (`convert_building.py:328`) and then refuses when
a record needs a whole byte (`convert_building.py:240-242`).

**It does not read unaligned either.** `bitstream-io`'s `read_bytes` has an
explicit unaligned path (`lib.rs:3138-3148`, `if queue_bits == 0 { read_exact }
else { ... }`), which was the reading that had to be ruled out.

## 3. Two planted controls, in both directions

A clean zero from a census is suspect until the instrument is shown to see
something where it must return non-zero. Both payloads are hand-built; every
read is delegated to the committed `parse_fill_style` / `parse_matrix` /
`BitReader`, so a defect in the probe's own reader is impossible.

**Payload A -- the two rules must differ.** A 7-bit MATRIX (no scale, no
rotate, `translate_bits = 0`) ends one bit before the second byte boundary.
Authority must read flags = `byte[2]`, report `ratios = 2` and consume exactly
13 bytes; the shipped parser must refuse.

**Payload B -- the two rules must agree.** A 16-bit MATRIX ends on a byte
boundary, so both rules read identical bytes. Payload B's first draft was
**broken and discarded**: it started the FILLSTYLE at bit offset 1 to force an
even MATRIX length, but a FILLSTYLE cannot start at a bit offset -- its type is
a whole-byte read -- so the plant failed rather than testing anything.

| | align-up | shipped |
|---|---|---|
| Payload A (7-bit MATRIX) | `ok ratios=2 matrix=00 position=104` | `refused: shape byte misaligned` |
| Payload B (16-bit MATRIX) | `ok ratios=2 matrix=4204 position=112` | `ok ratios=2 matrix=4204 position=112` |

**8 of 8 checks pass.**

## 4. A claim of mine that was wrong, and is withdrawn

The probe's first draft asserted that a MATRIX is always an odd number of bits,
so one starting at a byte boundary can never end on one. **That is false and is
withdrawn.** The probe now *measures* the parity, and 4 of 8 MATRIX forms are
even-length:

| form | bits | parity |
|---|---|---|
| no scale, no rotate, `translate_bits = 0` | 7 | odd |
| no scale, no rotate, `translate_bits = 1` | 9 | odd |
| rotate present, `translate_bits = 0` | 14 | even |
| rotate present, `translate_bits = 1` | 16 | even |
| scale present, no rotate, `translate_bits = 0` | 14 | even |
| scale present, no rotate, `translate_bits = 1` | 16 | even |
| scale and rotate, `translate_bits = 0` | 21 | odd |
| scale and rotate, `translate_bits = 1` | 23 | odd |

This matters for the previous stage's headline. It reported **96.4%** of
gradient MATRIX values ending mid-byte and implied the remaining **3.6%** were
anomalies. That reading is wrong: about half of MATRIX forms are even-length, so
a byte-aligned finish is entirely ordinary and the 157 byte-aligned cases are
**not** evidence of a desynchronised parse. The 96.4% figure stands; its
interpretation did not, and the interpretation is withdrawn.

## 5. The paired corpus measurement

The identical 817-candidate population, the identical committed harness
(`census_targets.py`), **one variant per process** because variants leak module
state. The variant is a monkeypatch of `parse_fill_style` that inserts one
statement, `reader.align_to_byte()`, after `parse_matrix`. Non-gradient fill
types are **not reimplemented**: the variant reads the fill type, rewinds, and
delegates to the shipped function, so there is exactly one implementation of
every other branch and the variant cannot drift from the baseline there.

### Refusal classes, both directions

| class | shipped | align-up | delta |
|---|---:|---:|---:|
| `shape bit overrun` | 47 | 9 | **-38** |
| `shape byte misaligned` | 42 | 1 | **-41** |
| `shape byte overrun` | 18 | 10 | **-8** |
| `unknown fill style` | 160 | 164 | +4 |
| `unresolvable bitmap fill` | 134 | 139 | +5 |
| `unsupported shape tag` | 66 | 75 | +9 |
| `unsupported timeline tag ... (PlaceObject#)` | 58 | **126** | **+68** |
| `unsupported tag in timeline ... code #` | 1 | 1 | **0** |

**7 of 8 classes moved. 1 is identical in both runs**, so it is explicitly not
attributable to the patch.

### Per-target movement

- converted: **291 -> 292** (gained `1056_elephant_rider_m`, **lost 0**)
- **104 targets changed refusal class while keeping their verdict**
- all 291 previously-converted targets convert in both runs

The three desync classes fall from **107 to 20**. The gain is **+1**.

### The +68 is a class being revealed, not created

All 126 are the **same** tag: `PlaceObject3`, code 70. The 68 that newly name it
previously refused at an **earlier** tag:

| previous class | count |
|---|---:|
| `shape bit overrun` | 30 |
| `shape byte misaligned` | 23 |
| `unknown fill style` | 11 |
| `shape byte overrun` | 4 |

`refused_targets_in_several_classes` is **0 in both runs** and every one of the
68 previously carried exactly one class, so none of them was already reaching
this tag. The converter stops at the first refusal, so a target refused during
shape parsing never reaches the tag after it. **The `PlaceObject3` figure of 58
in every committed record of this milestone is an understatement of at least 68**,
and it was an artefact of the parser refusing earlier.

## 6. A correction to a recorded claim

`target_census.json` (`84B11BEE...`) **no longer reproduces on `main`.** The
shipped baseline in this run is `84B7D954...` and differs on **109 targets**,
with exactly **one** verdict change: `0157_jet_robosoldier_academy_m`, refused
-> converted. That is the target PR #369 converted, so the committed census
describes the **pre-order-fix** parser.

This does not contradict the previous stage's withdrawal of "the census is
stale". That claim was **true when made** -- the census reproduced
byte-identically at `84B11BEE...` on the tree as it then stood. It stopped
being true when the order fix merged, and nothing recorded that transition,
because the census records **no input digests** and therefore cannot prove its
own currency. The already-recorded gap is now a demonstrated failure, and this
is the transition record for it.

## 7. Non-claims

- **No fix is proposed and none may be.** The desync family is under a standing
  instruction to investigate and propose nothing. This document is the
  investigation.
- **No claim that the SWF format requires byte alignment.** What is established
  is what the reference reader does. Ruffle could be lenient and still correct
  on well-formed input; leniency is evidence, not proof. It is, however, the
  same authority already accepted for the gradient field order, and it is a
  reference implementation of the format rather than a third-party reader.
- **No claim about the one remaining `shape byte misaligned` target.**
  `1419_warlordDrone` still refuses after the rule is applied. The cause was not
  investigated and is **not** assumed to be another alignment case.
- **No claim that the 9 remaining `shape bit overrun` targets share a cause.**
  They are listed, not explained.
- **The `0x13` focal branch stays unexercised.** Unchanged from the previous
  stage, and for the same reason: the pinned crate reads no focal point and no
  committed shape carries fill type `0x13`.
- **No pixel parity and no rendering claim.** Nothing here renders anything.
- **+1 converted is the honest headline, not +104.** 104 targets changed class;
  that is not 104 conversions.