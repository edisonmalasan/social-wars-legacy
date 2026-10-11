# The gradient FILLSTYLE field order, corrected and measured

`tools/asset-registry/convert_building.py` read the gradient **record block
before the MATRIX**. The documented layout is MATRIX first. This records the
one-line correction, its own measurement, and four things I got wrong on the
way, two of which were defective instruments that had to be discarded rather
than reported.

The diagnosis that located the defect and established the field order is
`docs/legacy-m12-fill-gradient-layout.md`. It was merged before this change
(`ba31dac`) and is not restated here.

## 1. The change

`parse_fill_style` moved one statement:

```
-    if fill_type in FILL_GRADIENTS:
-        gradient_flags = reader.read_bits(8, label)
-        ...
-        matrix = parse_matrix(reader, label)
+    if fill_type in FILL_GRADIENTS:
+        matrix = parse_matrix(reader, label)
+        gradient_flags = reader.read_bits(8, label)
```

`convert_building.py:317-330` before, `:317-337` after. Nothing else moved.
The returned key set is unchanged â€” `interpolation`, `matrix`, `ratios`,
`spread`, `type` â€” which is asserted directly.

**Authority.** The order was not taken from memory. The pinned `swf` crate
0.3.0 reads `read_matrix()` and only then `read_gradient_flags()` and the
records (`src/read.rs:1689-1690`), and the spec's FILLSTYLE table lists
GradientMatrix ahead of Gradient. Two authorities agree.

**The focal point is retained, not established.** The `0x13` focal read still
follows the record block. The pinned crate reads no focal point at all, so it
is **not** an authority here, and no committed shape carries fill type `0x13`
(measured: `0x10` 44, `0x12` 85, `0x13` **0**). That branch stays unexercised
and unmeasured, and this line does not claim anything about it.

## 2. Controls, all of which passed before any number below was read

| control | result |
|---|---|
| existing converter suite, before the change | `Ran 26 tests`, OK, exit 0 |
| existing converter suite, after the change | `Ran 26 tests`, OK, exit 0 |
| new gradient suite, with the fix | `Ran 31 tests`, OK, exit 0 |
| **planted control** â€” revert the order, require failure | **5 of 5 gradient tests fail**, exit 1 |
| restore after the control, by SHA-256 | digest `3091ee96â€¦`, matches, suite green again |
| whole asset-registry suite | `Ran 226 tests`, OK, exit 0 |
| committed census reproduced pre-fix | byte-identical, sha256 `84B11BEEâ€¦` |
| guard baseline | `OK - 6 group(s), combined 233be548â€¦` |

The planted control is the load-bearing one. All five gradient tests fail
under the shipped order and pass under this one, so they discriminate the two
orders rather than merely passing.

### The two committed conversion packages do not move

Neither converted package contains a gradient fill (measured: 0 gradient fill
types across both `package.json` files, against 54 bitmap fills). Both were
re-converted after the change into a disposable out-root and compared to the
committed bytes:

| package | files | all byte-identical |
|---|---|---|
| `assets/converted/buildings/0001_house_1_m` | 3 | yes |
| `assets/converted/units/10033_wild_elephant` | 45 | yes |

So `conversion_packages` and `registry_manifests` in the guard baseline are
untouched and **no regeneration chain was triggered** â€” unlike the signed-RECT
line, this change needs no `conversions.json` â†’ `report.json` â†’
`guard-baseline.json` ordering.

## 3. The measurement

Whole population, 817 candidates, through the committed
`census_targets.evaluate`, pre-fix and post-fix, into disposable out-roots
outside the repository. Every figure reconciles.

**Population and converted set**

| | pre | post |
|---|---|---|
| candidates | 817 | 817 |
| converted | 290 | **291** |
| refused | 527 | 526 |
| newly converted | â€” | **1** (`0157_jet_robosoldier_academy_m`) |
| converted targets lost | â€” | **0** |

**Full post-fix refusal census**, all eight classes, every target:

| first-refusal class | pre | post | delta |
|---|---|---|---|
| `unknown fill style` | 137 | **160** | **+23** |
| `shape bit overrun` | 20 | **47** | **+27** |
| `shape byte misaligned` | 11 | **42** | **+31** |
| `shape byte overrun` | 104 | **18** | **âˆ’86** |
| `unresolvable bitmap fill` | 133 | 134 | +1 |
| `unsupported shape tag` | 64 | 66 | +2 |
| `unsupported timeline tag` (PlaceObject#) | 57 | 58 | +1 |
| `unsupported tag in timeline` | 1 | 1 | 0 |
| **converted** | **290** | **291** | **+1** |
| total | 817 | 817 | |

**Reconciliation** â€” `base == new + outflow âˆ’ inflow` holds for all seven
refusal classes; population identity holds; unchanged 709, changed 108.

| flow | targets |
|---|---|
| `shape byte overrun` â†’ `unknown fill style` | 34 |
| `shape byte overrun` â†’ `shape bit overrun` | 38 |
| `shape byte overrun` â†’ `shape byte misaligned` | 31 |
| â†’ `converted` | 1 |
| smaller flows | 4 |

**The result is one converted target out of 817.** The signed-RECT
precedent is two out of 272, so this fix is worse on its own headline number,
and the full census shows why: it **relocates** failure rather than removing
it. `shape byte overrun` falls by 86 and three other classes grow by 23, 27
and 31.

## 4. Why: 96% of gradient MATRIX values end mid-byte

The corrected order exposes a second property of the format that the shipped
order masked. Measured over the whole corpus using only committed parser code
(`decompress_body`, `parse_frame_size`, `walk_shape_tags`, `parse_rect_bits`,
`parse_matrix`):

| | |
|---|---|
| files scanned | 862 |
| shape tags | 56,559 |
| gradient fills reached | **4,303** |
| MATRIX ends on a byte boundary | **157 (3.6%)** |
| MATRIX ends mid-byte | **4,146 (96.4%)** |

`BitReader.read_bytes` refuses a misaligned read, so under the corrected order
the gradient records that follow a MATRIX are read from a non-byte-aligned
position and the parser raises `shape byte misaligned`. That is the +31.

**This is not claimed to be a second defect.** Whether the format requires
byte alignment is **unresolved**: the pinned crate's `read_u8` comes from
`bitstream_io`, which is not vendored in the captured tree, so its alignment
rule could not be read and is recorded as unresolved rather than assumed.
What *is* established is the measured distribution above, and it is the
mechanism by which the fix relocates failure.

## 5. Withdrawn and discarded

Four claims of mine did not survive measurement. All four were mine, none is
in the repository.

**(a) Withdrawn â€” "the committed census is stale".** The census was written at
`2d51b61` and `convert_building.py` changed afterwards at `8961f8c`, so I
predicted the census described a parser no longer in the tree. Re-running the
census on the current parser reproduced `target_census.json`
**byte-identically**. The staleness reasoning is withdrawn; the census is
current, and the prior line's Â§2 finding stands.

**(b) Withdrawn â€” "the doc's 137â†’26 is the signed-RECT fix".** The census
reported 137 while the doc records that fix as moving that class to 26, which
I read as a contradiction. It is not: the doc's Â§3 patched column is a
**probe-level override of a solid-fill-width defect** (3 bytes versus 4 in an
RGBA shape), which is a different defect from the merged RECT
sign-extension. The conflation was in my summary, not in the repository.

**(c) Discarded â€” a tag-walk probe that read two 5-bit fields.** It disagreed
with the committed `parse_shape_with_style` on **1,021 of 2,333** tags and
appeared to show the shipped parser misreading the RECT `Nbits` in 44% of
shapes. The probe was wrong: the shipped parser reads one 5-bit RECT `Nbits`
at `:453` and NumFillBits/NumLineBits as 4+4 at `:456-457`, which is the
documented SHAPEWITHSTYLE layout. **A clean-looking 44% defect rate was my
instrument's error, and no such defect is claimed.** The alignment figures in
Â§4 come from a probe that delegates to committed code throughout.

**(d) Discarded â€” a probe that started the tag walk at byte 8**, reading the
frame header as tags and reporting 2,077 shape tags where the correct walk
yields 56,559. Its first output was a clean zero gradient fills, which is
what exposed it: a zero from a census is suspect until the instrument can be
shown to see something where it must.

Two earlier drafts of the new tests were also discarded before installation,
both for the same reason â€” a check that cannot discriminate. A test asserting
the interpolation mode is never a reserved value was a **tautology**: with
`flags=0x42` the interpolation is read from the flags byte under either order.
It was replaced by a byte-consumption assertion. And a second draft used a
matrix that ends mid-byte, which would have failed in `read_bytes` for reasons
unrelated to field order; the installed matrix is byte-aligned by measurement,
and the reason is recorded in the test's docstring.

The first installed version of the suite then **errored 5 of 5**, because the
gradient records were built with 3-byte colours while every call parses with
`rgba=True` and reads 4. That was my test data, not the fix; the probe was
re-run and the helper corrected.

## 6. What is not claimed

- **No parity is claimed for the gradient branch.** The corpus reaches 4,303
  gradient fills and the corrected order converts exactly one target, which
  the census attributes to a shape whose gradient parse succeeds. No claim is
  made about the other 4,302.
- **The `0x13` focal branch is untested and unmeasured.** No committed shape
  carries it.
- **Byte alignment is not resolved.** Â§4 reports a measurement, not a rule.
- **No pixel-parity claim**, and no rendering is involved: this line parses
  SWF bytes and writes a JSON package. No Flash, Ruffle, ActionScript or
  browser executes in any command here, and no network is used.
- **The census still records no input digests and no tool revision.** This
  change moves a parser and the census does not move with it, which is the gap
  the prior line recorded and did not fix. It remains open.
- **Coverage remains 1 of 2 committed converted packages** for anything the
  guard baseline guards. Neither contains a gradient.

## 7. Reproducing

Both census runs, pinned CPython 3.9.13, disposable out-roots outside the
repository:

```
python -B tools/asset-registry/census_targets.py --repo-root <repo> \
  --out-root <temp>\work --report <temp>\report.json
```

Elapsed ~380 s each, exit 0. Reconciliation requires the population identity,
the class identity for all seven classes, and no converted target lost.