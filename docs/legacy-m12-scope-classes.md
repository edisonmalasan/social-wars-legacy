# M12 Objective 2 — the cost of lifting the three scope-decision refusals

This document prices three refusals. It does **not** recommend lifting any of
them. A refusal is not reversible by derivation: derivation explains why a
rule holds, and this project's own record shows that a fix aimed at the
desync family three times relocated failure rather than converting a target.
What a scope decision needs is a number — how large is the change, and what
would it actually reach — and that is what follows.

Status: proposal-stage investigation. No production code was changed, no
refusal was lifted, and nothing here alters a converted package.

## 1. Method, and the baseline it is measured against

Figures come from the committed census `tools/asset-registry/target_census.json`
(committed digest `84B11BEE…`), which records **290 converted / 527 refused**
across 817 candidates in 8 refusal classes:

| domain | converted | refused |
|---|---|---|
| building | 222 | 230 |
| unit | 68 | 297 |

**That census is stale on `main`.** The current-tree baseline is `84B7D954…`;
the two differ on 109 targets with exactly one verdict change,
`0157_jet_robosoldier_academy_m`, the target PR #369 converted. This is a
transition, not a contradiction: the committed file simply predates that merge.
The census also records no input digests, so nothing in it can attest to the
tree it was computed from.

Two counting rules are used throughout and both matter:

* a target is counted into a class only when it has **exactly one** refusal
  class (`refused_targets_in_several_classes` is 0 in both runs, so no target
  is double-counted here, but the filter is kept rather than assumed away);
* a target is "isolated" for a class only if measurement shows nothing *else*
  in that class is also blocking it. Isolation is a measurement, never an
  inference from the refusal text.

## 2. Class 1 — `unsupported shape tag` / DefineShape4 (tag 83): 64 targets

**What refuses.** `TAG_REFUSED_SHAPE = (83,)` (`convert_building.py:56`),
checked once at the entry of `parse_shape_with_style` (`:442-444`). The check
is one comparison against a one-element tuple.

**Isolation: measured, yes.** All 64 targets have this as their single refusal
class, and none is blocked by a second refused shape tag.

**The refusal is a small minority of the work in these files**, from the
committed per-file tag histogram in `inspection.json`:

| measure | value |
|---|---|
| targets | 64 |
| DefineShape4 instances a new walk must read | 240 |
| all walkable shape instances in those files | 8,589 |
| share that are tag 83 | **2.8%** |
| per-target tag-83 count (min / median / max) | 1 / 1 / 19 |
| targets carrying exactly one instance | 35 of 64 |

Every one of the 64 also carries tag 2; 42 carry tag 22 and 47 carry tag 32 —
shape tags the parser already walks successfully. So lifting this refusal adds
a walk for 2.8% of the shape instances in files that are otherwise readable.

**What lifting it actually costs.** This is **not** a constant flip, and the
number of lines is deliberately not quoted, because quoting one would be a
guess dressed as a measurement. Two things are established:

* the shipped `count_shape_records` implements the StyleChangeRecord stream
  used by DefineShape through DefineShape3. DefineShape4's geometry is not
  that stream, so tag 83 needs its own record walk, not a wider version of the
  existing one;
* the pinned authority is itself incomplete on this tag. `swf` 0.3.0 reads
  `DefineShape4` through the same `read_define_shape(4)` entry point
  (`src/read.rs:475`), and carries an explicit
  `// TODO: Read LineStyle2 from DefineShape4.` at `src/read.rs:3015`, using
  LineStyle2 only for Shape3. So the crate cannot be used as a
  "this is all there is" reference for tag 83, and a Shape4 walk derived from
  it would inherit that gap.

One piece of the work is already done: `rgba = tag in (22, 32, 83)`
(`convert_building.py:448`) already anticipates tag 83's RGBA colour width, so
lifting the refusal does not also require a colour-width change.

**Upper bound on conversion: 64 targets.**

## 3. Class 2 — PlaceObject3 (code 70): 57 targets

**What refuses.** `TIMELINE_REFUSED_TAGS` (`convert_unit.py:71-77`), raised in
`walk_timeline` at `:261-264`.

**Isolation: measured, yes, and it is the cleanest of the three.** All 57
targets carry PlaceObject3 and **nothing else** from `TIMELINE_REFUSED_TAGS`.
The constant also refuses codes 4, 5, 12 and 59 (PlaceObject, RemoveObject,
DoAction, DoInitAction); none of them appears in any of these 57 files.

The 57 here are the *single-class* count. `docs/legacy-m12-byte-alignment.md`
records 126 targets naming `PlaceObject3` in a refusal string; that figure is
a different scope (all refusal text, not single-class), and both stand.

**What lifting it costs, from the pinned crate.** `swf` 0.3.0 handles
PlaceObject2 and PlaceObject3 through **one** function,
`read_place_object_2_or_3(place_object_version)` (`src/read.rs:1902`). Passing
version 3 changes exactly two things and adds three optional fields:

* the flag word becomes **UI16** instead of UI8 (`src/read.rs:1906-1910`);
* `HAS_FILTER_LIST` → UI8 count then N filters (`src/read.rs:1968`);
* `HAS_BLEND_MODE` → one byte (`src/read.rs:1978`);
* `HAS_CACHE_AS_BITMAP` → one byte (`src/read.rs:1983`).

So the size of the change is decided by whether these placements actually set
`HAS_FILTER_LIST`. Measured across **7,898** PlaceObject3 payloads:

| flag | set on | share |
|---|---|---|
| `HAS_FILTER_LIST` | **7,631** | **96.6%** |
| `HAS_BLEND_MODE` | 388 | 4.9% |
| `HAS_CACHE_AS_BITMAP` | 0 | 0.0% |
| `HAS_CLASS_NAME` | 0 | 0.0% |
| `HAS_IMAGE` | 0 | 0.0% |
| `HAS_VISIBLE` | 0 | 0.0% |
| `OPAQUE_BACKGROUND` | 0 | 0.0% |
| `HAS_NAME` / `HAS_CLIP_DEPTH` / `HAS_CLIP_ACTIONS` | 0 | 0.0% |

(`HAS_MATRIX` 98.8%, `MOVE` 79.9%, `HAS_COLOR_TRANSFORM` 22.6%,
`HAS_CHARACTER` 20.1%, `HAS_RATIO` 12.2%. No payload sets a bit outside the
crate's `PlaceFlag` mask.)

**The cost is therefore a filter-list parser, not a two-byte flag read.** 96.6%
of placements carry a filter list; a fourth carry a blend mode; nothing carries
a cache bit, class name, image, visibility or opaque-background flag. Three of
the four crate-side additions are therefore free here, and the expensive one is
the one that is present almost everywhere.

The **composition** of those filter lists is deliberately not reported. Reading
it requires implementing the parser whose cost is being measured, so it is the
work rather than a step before it. See §5 for the probe that tried and was
discarded.

**Upper bound on conversion: 57 targets.**

## 4. Class 3 — `unresolvable bitmap fill`: 133 targets, and it cannot be lifted

**This class is not a scope decision at all.** It is not a parser refusal and
not a refusal that a better parser would clear.

**What refuses.** Not the parser: `convert_building.py:708-714`, after every
shape has already parsed successfully. It tests each bitmap fill's id against
`bitmap_by_id`, built at `:703-707` from extraction-manifest entries filtered
by `source == source` — that is, **strictly from the same file**. Resolution is
within-file by construction.

**What the id is.** All 133 targets reference the **same id, 65535**, and the
bytes carrying it are real rather than a desync artefact:

* the id read is byte-aligned (`bit offset 0` at every occurrence);
* `read_bytes` raises on overrun (`convert_building.py:244-245`) rather than
  padding, so the two bytes exist in the file;
* they follow a genuine bitmap fill-type byte — `0x41` (clipped) 1,716,
  `0x43` (non-smoothed clipped) 27, `0x40` (repeating) 4 — carried by shape
  tags 2 (919 occurrences), 22 (611) and 32 (217);
* the same 133 files also reference ordinary, resolvable bitmaps, so they are
  not files where bitmap support is uniformly broken.

**And the corpus does not contain it.** From committed artefacts only:

| measure | value |
|---|---|
| SWF files defining any bitmap id | 1,048 |
| distinct bitmap ids defined anywhere in the corpus | 2,056 |
| id space | **1 … 3,903** |
| id 65535 defined anywhere in the corpus | **no — 0 of 1,048** |
| of the 133 targets, those whose own file defines 65535 | **0** |
| of the 133, those that also define ordinary ids | 133 |

**Consequence.** No parser change and no extractor change can make 65535
resolve, because resolving it requires the file to contain that character and
the file does not. Lifting this refusal would not convert 133 targets; it would
convert them *with a dangling bitmap reference*, which is a different product
decision than the one this class appears to offer. **Upper bound on conversion
by lifting the refusal: 0.**

## 5. Instruments that were built, failed their controls, and were discarded

Four probes were written for this objective. Three produced numbers that were
thrown away because the instrument failed a control. They are recorded because
a discarded measurement that is not written down becomes the next session's
unquestioned premise.

1. **The first cost probe reported a clean zero for all 64 DefineShape4
   targets** — "unreadable/registry miss: 64". That was a defective instrument,
   not a result: it read `inspection.json` as an array of entries when the
   committed document is a **map keyed by SWF path**. Discarded. The rewritten
   probe asserts its own registry lookup found the file it asked for before any
   count is printed.

2. **The MATRIX-coherence probe, v1**, reported the MATRIX header *illegal* for
   2,823 of 2,869 **resolvable** bitmap fills — fills that convert successfully
   today. It had matched each fill to its two-byte id read *by value*, so a
   LINESTYLE width equal to a bitmap id matched first and the wrong bytes were
   decoded. The control is the only reason this was visible. Discarded.

3. **v2** anchored on the MATRIX read but cleared its hook list at the start of
   every FILLSTYLE, so only the last fill of each shape kept its bytes; every
   fill came back unconfirmed (4,616 of 4,616). Discarded.

4. **v3** recorded per fill but confirmed by matching bytes to the fill id, and
   matched only 18 of 4,616 — a third defect of the same family. **v4** dropped
   hooks entirely and read `fill["matrix"]`, which the committed parser already
   captures (`parse_matrix` returns `data[start:end].hex()` and
   `parse_fill_style` stores it). That is the one instrument that survived, and
   it is the source of §6.

A fifth instrument, the PlaceObject3 header walk, **failed its control and its
output is not reported anywhere in this document.** It reached the filter-list
offset for only 1 of 267 filter-free placements, which must land exactly on the
payload end. It is listed here as discarded. The flag census in §3 does **not**
come from it: that census is read from the UI16 flag word directly and is
confirmed independently, since 7,898 − 7,631 = 267 filter-free placements by
one path and 267 by the other.

Two defects found by controls rather than by reading were in this objective's
own new code: the PlaceObject3 `UI16` was first read big-endian, which
byte-swapped the flag word and made 1,587 placements look filter-free instead of
267; and the tag scan was first flat rather than recursing into `DefineSprite`
payloads, which made it see 1 ShowFrame where the committed histogram records
205. Both were caught by controls, and the tag-histogram control now passes
57 of 57 exactly.

## 6. A separate latent finding, reported and not acted on

Reading the MATRIX bytes the parser itself captured, decoded with the parser's
own MSB-first bit order, the header of every bitmap fill decodes to
`HasScale = 1` and `NScaleBits = 22` — in **2,869 of 2,869 resolvable fills**
and **1,747 of 1,747** `65535` fills. The format caps `NScaleBits` at 11.
`parse_matrix` (`convert_building.py:296-308`) performs no validation at all, so
whatever the encoding is, it is consumed silently.

**This is not the cause of the §4 refusal**, which is a resolution failure
after a clean parse, and it is deliberately not acted on here. Two things
about it are not established and are not claimed: what those bytes mean, and
whether a legal reading exists. The stream stays coherent across 4,616 fills,
which argues against a simple mis-decode. It is a carried finding for whoever
owns matrix parsing, and it is recorded here rather than left in a probe
directory.

## 7. Non-claims

* **Nothing was lifted.** No refusal was relaxed, no parser branch changed, no
  converted package altered. `git status` shows no production change.
* **121 is an upper bound, not a prediction.** 64 + 57 targets would pass
  *these* refusals. Whether they then convert or merely relocate is exactly the
  question the three desync-family fixes answered negatively, and it is not
  answered again here.
* **No line count is quoted for the tag-83 walk**, because establishing one
  would require writing it.
* **The filter-list composition is unknown**, per §3.
* **The census is stale by one target** (§1), and its figures are quoted as the
  committed document's, not as the current tree's.
* **No pixel parity, no windowed capture, no rendering claim**: nothing here
  renders anything.
* No Flash, Ruffle, ActionScript or browser executes in any measurement above;
  no network is used.
