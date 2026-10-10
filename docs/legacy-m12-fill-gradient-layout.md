# M12: the `FILL_GRADIENTS` divergence diagnosed against the documented layout

**Status:** investigation only. **No line is proposed, no production code
changed, no conversion performed.** This document does the one thing
`docs/legacy-m12-fill-gradient-measurement.md` section 11 named as the next
eligible objective: it compares the measured layout against the documented SWF
`FILLSTYLE` gradient layout, field by field, and records which field the
measured offsets contradict.

**The diagnosis closes, and it is one field: the order inside the gradient
`FILLSTYLE`.** The shipped converter reads the record block before the matrix;
the documented layout is matrix first. That single ordering is contradicted by
every gradient in the corpus that can be checked at all, and the contradiction
is total rather than statistical — the shipped order never once produces a legal
`InterpolationMethod` where the documented order produces one in 182 of 182.

---

## 1. Summary

| | measured (shipped) | documented |
|---|---|---|
| gradient field order | records, then matrix | **matrix, then records** |
| arrival at the style array | byte-aligned | byte-aligned (same) |
| terminating shape tags | 10,112 / 16,828 | 10,135 / 16,828 |
| tags reaching a gradient | 159 | 182 |
| `InterpolationMethod` legal | **0 / 159** | **182 / 182** |
| ratios non-decreasing | 72 / 159 (45.3%) | **179 / 182 (98.4%)** |
| expected by chance | 2.5% | 1.4% |

Three findings, in decreasing order of how firmly they are established:

1. **Field order is the divergence.** `InterpolationMethod` occupies bits 6–7 of
   the gradient flags byte and `2` and `3` are **reserved values**. Under the
   shipped order every one of 159 surviving gradients reads a reserved value
   (28 read `2`, 3 read `3` in the comparable subset) and **not one** reads `0`
   or `1`. Under the documented order **182 of 182** read a legal value and
   **none** reads a reserved one. That is a complete separation on the same tag
   bytes, at the same arrival offset, under the same end condition, with only
   the field order differing.
2. **The arrival offset is byte-aligned, and this confirms the shipped code
   rather than faulting it.** `convert_building.py:441` calls
   `reader.align_to_byte()` after the shape `RECT`. Measured over all 16,828
   shape tags: the aligned variant reaches a gradient in **182** and the
   unaligned variant in **0**. A `RECT` is `5 + 4·Nbits` bits, which is never a
   multiple of 8, so a `RECT` beginning on a byte boundary cannot end on one and
   the shipped assumption is not free — it is correct, and now measured rather
   than assumed.
3. **The end-to-end parse succeeds 60% of the time under either order**, so this
   is not a parser that mostly fails and occasionally lands on a gradient. Both
   orders survive on nearly the same number of tags (10,135 against 10,112), so
   the separation in finding 1 is **not** an artefact of a survivor set selected
   for being parseable under one order.

---

## 2. Authorities, and what they establish

### 2.1 Primary — the `swf` crate

`swf` **0.3.0**, sha256
`B1840721AF70281567FDCBBF16E81B297DB77D695C7B4A64860B18DA15BB401A`, VCS sha1
`7436b84482be78032e63b3bed59b189353682af2`. Pinned at
`tools/asset-registry/../…/gradient_layout/crate/swf-0.3.0/src/read.rs`.

- `read.rs:1586` `read_fill_style`
- `read.rs:1688` `read_gradient`, with the **matrix read first, at `:1689`**
- `read.rs:1716` `read_gradient_flags`
- `read.rs:704-724` `read_matrix`
- `read.rs:315-316` `read_fbits`

### 2.2 Corroborating — the specification's own table

The `FILLSTYLE` table lists **`GradientMatrix` before `Gradient`**. Two
independent authorities agree on the order, and the shipped code contradicts
both.

### 2.3 The shipped code

`tools/asset-registry/convert_building.py`:

- `parse_fill_style` at `:311`, gradient branch `:317-330` — reads the record
  block first, the matrix last
- `parse_matrix` at `:296`
- `parse_style_arrays` at `:346`
- `align_to_byte()` at `:358`, called from `parse_shape_with_style` at `:441`
- `TAG_DEFINE_SHAPE = (2, 22, 32)`; tag `83` (`DefineMorphShape`) is excluded
  from style-array parsing entirely

### 2.4 Discarded — the PDF

The specification PDF (`swf-spec-19.pdf`, 1,724,258 bytes, sha256
`6A1625B0929A86329021D365BA079C7E1F51502DFB4EA7D92EC9947841625CDD`) is a
**defective instrument and is discarded**. The title decodes; the body is CID
garbage, with **zero** hits for `SpreadMode`, `FILLSTYLEARRAY`, `GradientMatrix`,
`NumGradients`, `FocalPointRatio` and `FillStyleType`. The union `ToUnicode`
CMap is unsound — 6 conflicts across 135 entries. It contributed **nothing** to
this document, and the two authorities above were used instead.

---

## 3. The instrument, and why it is the one that worked

### 3.1 Why the previous instruments measured nothing

Four instruments were built and **all four are discarded as non-discriminating**,
each for a recorded reason. They share one shape: they looked **forward** from a
captured gradient entry and asked "where could the matrix be?"

| instrument | what it reported | why it measures nothing |
|---|---|---|
| `flags_scan.py` delta histogram | low-nibble counts per delta | a nonzero low nibble occurs in 15 of 16 byte values, so "count ≥ 1 at delta N" measures the byte alphabet |
| `flag_positions.py` | 153 distinct offsets carry blocks | every block has **more than one** legal position (0 blocks with exactly one), so a hit is not a location |
| `matrix_delta.py` corpus half | modal delta = 3 on 24% | it took the **nearest** of many anchors; nearest-anchor is not anchor |
| `matrix_starts.py` corpus half | feasible start at **every** offset 1–80, in **all 144** blocks | a total acceptance rate is a zero, not a measurement. Its planted controls passed, which licenses the *search*, never its corpus result |

This is the project's standing lesson applied again: **a tidy aggregate from a
check that cannot discriminate is worse than a failure**, because it reads as
evidence. Four clean-looking tables were produced and all four were wrong about
the world.

### 3.2 What changed: constrain from both sides

A `DefineShape` tag is **self-delimiting**: `ShapeId`, `ShapeBounds`,
`FILLSTYLEARRAY`, `LINESTYLEARRAY`, `NumFillBits`/`NumLineBits`, then shape
records ending in an `EndShapeRecord`. So a correctly-read gradient must let the
walk **reach an `EndShapeRecord` at or before the end of the tag**. A
mis-read gradient eats or invents records, the terminator is missed or the walk
overruns.

That is a filter none of the four discarded instruments had: they scanned
forward from a known point, and this one requires the parse to **close**. The
same tag bytes are parsed under both field orders at the same arrival offset,
so the comparison is controlled by construction rather than by argument.

### 3.3 Planted controls, run before any corpus figure

Six planted payloads whose layout is known by construction — `RECT` ending
**mid-byte**, a documented-order gradient, an empty line array, and a
`StyleChangeRecord` followed by an `EndShapeRecord` — across `rect_nbits` of 1,
4 and 7 and both RGB and RGBA tags. **6 / 6 terminated**, recovering
`FillStyleCount 1`, `count 2` and `ratios [0, 255]`, at a `style_start_residue`
of **1**, i.e. genuinely mid-byte.

The same controls show the `align` variant **failing** on a mid-byte `RECT`
(`fill_type_0x5b`), which is itself the point: the shipped alignment is not
optional, it is the thing that makes these shapes parse at all.

---

## 4. Results

### 4.1 Invariant B is the discriminator, and it is total

`GRADIENTRECORD`'s flags byte packs `NumGradients` in bits 0–3, `SpreadMode` in
bits 4–5 and `InterpolationMethod` in bits 6–7. `InterpolationMethod` **2 and 3
are reserved**.

| order | legal | reserved | bad `SpreadMode` |
|---|---|---|---|
| documented | **182 / 182 (100%)** | 0 | 0 |
| shipped | **0 / 159 (0%)** | **159** | 0 |

In the subset where **both** orders terminate **and** both find a gradient — the
only class in which the two are not void by construction — documented reads
`InterpolationMethod` `0` in **31 of 31** and shipped reads `2` in 28 and `3` in
3, never `0` or `1`.

### 4.2 Invariant A corroborates, against a computed null

Non-decreasing gradient ratios hold in **179 / 182** under the documented order
and **72 / 159** under the shipped order. The null is computed from each order's
own count distribution, because non-decreasing ratios arise by chance with
probability `1/n!`:

- documented: expected by chance **2.6 of 182** (1.4%) → observed 179
- shipped: expected by chance **4.0 of 159** (2.5%) → observed 72

### 4.3 Invariant C points the other way, and is reported rather than dropped

`NumGradients ≥ 1` holds in **55 / 182** documented against **152 / 159** shipped.
This is stated plainly because it is the one column that does not favour the
documented order. It does not overturn the finding, for two reasons that are
themselves measurements:

1. **C is degeneracy, not a specification rule.** `NumGradients = 0` is an empty
   gradient, not a forbidden one. C is therefore reported separately and is
   deliberately **not** folded into a combined "legality" verdict.
2. The 127 documented `count = 0` cases are overwhelmingly shapes where the
   walk consumed a plausible style array and found no real gradient at all.
   Under the joint A∧B∧C score the documented order still leads **52 / 182
   against 0 / 159**.

### 4.4 Survivor bias was checked, not assumed

A terminator found in a subset selected for being parseable is evidence only if
the exclusions are unrelated to the order. Measured:

| | documented | shipped |
|---|---|---|
| tags parsed | 10,342 | 10,311 |
| tags terminated | 10,135 | 10,112 |
| terminated **with** a gradient | 182 | 159 |

The two orders survive on **nearly the same** tags, so the B separation is not
an artefact of which shapes parsed. Non-terminating tags break down as
`EOF_overran_tag` 5,906, `unsupported_fill_type` 580, `walk_lost_no_gradient`
196, and `walk_lost_after_gradient` **11** — only 11 of 16,828 ever reached a
gradient and then failed, so the excluded set is overwhelmingly gradient-free
in both orders.

Surviving gradients by tag: `32` 149, `2` 24, `22` 9, across **70** distinct
source files.

### 4.5 Where each order, field by field

The shipped offsets, against the documented reading, at the same arrival point:

| field | documented | shipped | contradicted? |
|---|---|---|---|
| `MATRIX` | first | last | **yes — total** |
| flags byte | after matrix | before matrix | **yes — total** |
| `NumGradients` | bits 0–3 of flags | bits 0–3 of matrix head | **yes** |
| `SpreadMode` | bits 4–5 | bits 4–5 of matrix head | yes, 0 bad either order |
| `InterpolationMethod` | bits 6–7 | bits 6–7 of matrix head | **yes — 0/159 vs 182/182** |
| `GRADIENTRECORD` ratios | 8 bits + colour | same, but offset by the matrix | **yes** |
| arrival after `RECT` | byte-aligned | byte-aligned | **no — they agree** |
| end of tag | — | — | **no — both under-run** |

**Only the ordering rows are contradicted.** The arrival offset and the
end-of-tag behaviour, the two things the previous stage measured, are confirmed.

---

## 5. Withdrawals and corrections

Recorded visibly, with cause. None of these is a silent edit.

1. **The byte-alignment requirement is WITHDRAWN.** It was **my invention**,
   never stated by the format, and the format in fact permits a style array to
   begin mid-byte. Measured, alignment is what the corpus requires (0 gradients
   unaligned against 182 aligned), but a requirement the format does not impose
   is not a correctness rule. What survives is narrower and is recorded as
   observation: byte-aligned end occurred in 8 of the 30 previously-measured
   blocks, and was **recorded, never required**.
2. **The count-byte check is WITHDRAWN.** It accepts 255 of 256 byte values and
   therefore measures nothing.
3. **Four instruments discarded as non-discriminating** — the table in §3.1. Each
   produced a clean-looking number; none could tell a present field from an
   absent one.
4. **A mechanistic explanation is WITHDRAWN.** The natural story — "the shipped
   order reads the matrix's head as a flags byte, so matrix presence bits land
   in `InterpolationMethod`" — was **tested and measured at 17 / 31**, failing
   on 14. Its concluding sentence claimed it "holds for every live pair"; that
   sentence was wrong and is withdrawn. The reading direction remains
   *consistent* with the data and is **not** reported as the cause. The cause is
   established only as far as: the two orders read different bytes at this
   position, and only the documented order yields reserved-field-free values
   across the corpus.
5. **A legality check of my own was wrong before it was reported.** It tested
   `flags in (0x00, 0x10, 0x20, 0x30)`, which ignores that `SpreadMode` and
   `InterpolationMethod` are bits 4–5 and 6–7, so `flags = 0x02` is count 2 with
   spread 0 and interp 0 — perfectly legal. It rejected every block in **both**
   orders, which is what exposed it. Fixed to test the real bit fields; §4.1 is
   the corrected measurement.
6. **The planted control failed three times, and every failure was in the
   plant.** (a) It wrote `TypeFlag=1, flags=3`, a `StraightEdgeRecord`, where it
   meant a `StyleChangeRecord`. (b) It omitted the six presence bits a
   `StyleChangeRecord` spends after `FillStyle1`. (c) It wrote `FillStyle1`
   before the `MoveTo` presence bit, while the format reads `MoveTo` first. In
   all three the parser was correct and the control was wrong — which is exactly
   what a planted control is for, and why the control is planted rather than
   derived from the parser under test.
7. **A genuine bug in my own walker.** `MoveToBits` is a single 5-bit field; the
   walker read two. Found while fixing the plant.

---

## 6. What is **not** claimed

- **No fix, and no line proposed.** No production code changed. The converter
  still reads records before matrix, and fails open exactly as it did before
  this document existed.
- **No claim that fixing the order fixes the desync family.** The located defect
  converts 2 of 272 with net 0 across all 817 targets, and 118 of 272 are
  byte-identically untouched by it. Whether reordering converts more is
  **untested** and is not estimated here.
- **The `0x13` focal branch remains entirely unexercised and unmeasured.** No
  `0x13` fill type occurs anywhere in the corpus, so the two-focal-byte branch
  is untouched by this diagnosis and no claim is made about it. Any
  documented-layout comparison must report it as untested, not as passing.
- **`DefineMorphShape` (tag 83) is unmeasured**, being excluded from
  style-array parsing entirely.
- **No claim about what the Flash client displayed.** Absence of a server rule
  says nothing about the client.
- **No rendering, no asset truth, no gameplay parity.**
- **No claim that the documented order is the *only* correct one**, only that it
  is the one both pinned authorities state and the only one consistent with the
  corpus.
- **The recorded flaky surfaces remain open.** This stage fixed none. The
  ledger's own enumeration is **thirteen** across all five of its prior
  statements; an earlier draft of this section said fourteen, which was inherited
  from a working summary rather than measured, and is corrected here rather than
  repeated.

### `verify-boot.ps1` fails on clean `main`, and not because of this stage

Recorded rather than omitted, because a failing battery that is not mentioned
reads as a clean one.

`verify-boot.ps1` reports **4** failing checks, all guard-baseline:
`guard baseline verify exits 0 before the run`, `guard baseline reports a combined
digest`, the same after the run, and `guarded bytes are identical before and after
(pre= post=)` with **both digests empty**.

**Root cause, located:** `tests/fixtures/godot-compatibility-boot/guard-baseline.json`
was last written in `2d51b61`, while `tools/asset-registry/conversions.json` and
`assets/converted/units/10033_wild_elephant/package.json` were both last changed
in **`8961f8c`** — the signed-`RECT` fix, PR #357 — which is an ancestor of
`main`. **The baseline was never regenerated after a commit changed files it
guards**, so the guard has failed since that merge.

Verified pre-existing rather than inferred: all work was stashed and the guard
run on a clean tree, where it fails identically. It is **not** a line-ending
artefact — the tool's own docstring records its digests as line-ending invariant,
both files are pure LF, and `git status` reports both **clean**, because git
normalises on compare while the guard hashes raw bytes against a stale recorded
value.

`apps/client-godot/evidence/first-render/report.json` drifts in the same commit
and for the same reason, recording `conversions.json` as `622c1489…` where the
committed bytes now hash to `f5d4118c…`, so that evidence artefact is stale too.

**Not fixed here.** This investigation is docs-only: it changed no production code
and no guarded bytes. Regenerating a baseline in order to make a check pass is
exactly the move that would hide the drift rather than record it, and the honest
fix belongs to whoever owns the guard. **This is a recorded surface, not a flaky
one — it is deterministic and reproduces on clean `main`.**

---

## 7. Where this leaves the cursor

The divergence is **diagnosed**: one field order, contradicted totally by
`InterpolationMethod` and corroborated by ratio monotonicity against a computed
null, with the arrival offset confirmed rather than faulted and the two
previously-measured behaviours confirmed intact.

The next eligible objective is therefore bounded and named, and is deliberately
**not begun** here:

**Reorder the gradient `FILLSTYLE` to read the matrix first, then re-measure the
desync family's 272 targets through the calibrated harness, and report how many
convert.** The prior end-to-end result to beat is 2 of 272 converting with net 0
across all 817. A fix that relocates the failure rather than removing it is the
recorded precedent from `docs/legacy-m12-refusal-classes.md` C1–C4, so the
post-fix census must be reported in full and not as a single converted count.

The two open decisions are unchanged and still **not pre-authorised**:

1. whether to mass-convert the 290 available packages (~15,000 files plus a
   preservation-manifest regeneration);
2. whether to revisit the three scope-decision classes (`DefineShape4`,
   `PlaceObject3`, bitmap-fill policy) — **286 of 527** refused targets, 54%.