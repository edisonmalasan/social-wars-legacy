# M12: the located RECT defect, and corrections to the desync-origin record

Status: investigation. Corrections to a merged document, plus one newly located
defect. No production code is changed by this document.

Predecessor: `docs/legacy-m12-desync-origin.md` (PR #356, merged `07c8b19`).

This document does two things, and the order matters. It first withdraws three
claims from the predecessor, because they were produced by a faulty instrument
and they are the reason this document exists. It then records a defect that the
predecessor's own error was hiding: a **located, one-function, fully identified**
fault in `parse_rect_bits` that makes the converter emit impossible geometry for
**74 of the 290** targets it reports as converted.

---

## 1. Summary

| | Predecessor claimed | Measured here |
|---|---|---|
| Family conversion (272 targets) | 0 convert | **2 convert** |
| Whole candidate set (817) | not measured | **net 0** (3 gained, 3 lost) |
| Section 7 class table | implied 272 accounted for | **covers 77 of 272** |
| Section 8 blocker | 130 targets parse then hit a downstream refusal | **withdrawn**; derived from the faulty run |
| Correction C5 | patch's return key caused a refusal class | **withdrawn**; the class was present before the patch |

And the new finding, which no prior line has measured:

| | Value |
|---|---|
| Converted targets emitting a negative extent | **74 of 290** |
| Shapes with a negative extent | **2445 of 4347** |
| Repaired by sign extension alone | **2445 of 2445 shapes, 74 of 74 targets, 0 failures** |
| Committed files affected | **1** (`assets/converted/units/10033_wild_elephant/package.json`) |

The converter **fails open**. That is the substantive discovery, and it is
invisible in every count this project has reported to date.

---

## 2. Corrections to `docs/legacy-m12-desync-origin.md`

These are recorded with cause, not edited into the predecessor.

### C-1 — Section 7's class table covers 77 of 272 targets, and says nothing about the rest

The predecessor reported per-class refusal counts summing to 77 while stating
that all 272 targets were accounted for. The remaining 195 were a single class,
`content ref not unique for <stem>: 0`.

**Cause: a console filter, not a computation.** The predecessor's end-to-end
script piped its output through `Where-Object { $_ -notmatch 'content ref not
unique' }`. The refusal-class tally was computed from a JSON file, so it was
correct — but the class was invisible in every review of the run, and the table
was published without checking that it summed to the population.

### C-2 — The 195 were an instrument fault: one converter used for two domains

The 272 targets split **77 building / 195 unit**. The end-to-end script called
`convert_building.build_package` for all 272. For a unit target the *building*
content lookup finds no row whose `img_name` equals the stem, so it raised
`content ref not unique` **before any parsing happened**. 195 of the 272
therefore never reached the parser, and every parser-phase figure for them was
vacuous.

The census avoids this by routing through `CONVERTER_BY_DOMAIN`
(`census_targets.py:160-166`). The probe did not.

**The tell was available and was not used.** The class appears in the *before*
(unpatched) run with the identical 195 targets. A monkeypatch cannot create a
refusal the unpatched run already has. Two runs of the same data disagreed with
the patch's story, and the patch's story won.

### C-3 — "0 of 272 convert" is wrong; the family figure is 2, and the whole-set figure is net 0

With correct per-domain routing the located layout converts
`1076_robo_soldier_m` and `1155_dwarf_soldier`. Across **all 817** candidates it
gains **3** and loses **3**:

```
converted BEFORE : 290
converted AFTER  : 290
net              : +0
```

GAINED: `1076_robo_soldier_m`, `1155_dwarf_soldier`, `231_dwarf_deco_3`.
LOST: `0127_enemy_harbour_m`, `1005_special_spy_m`, `1421_cyberInquisitorDrone`.

All six are **stable across 3 repeats in each phase** — deterministic, not flaky.

### C-4 — Section 8's blocker claim is withdrawn

The claim that "130 targets that now parse land in refusals that are not parse
failures" is arithmetically derived from the 195 spurious class and is
**withdrawn**. The downstream picture was never measured, because the probe never
reached the downstream path for 195 of the targets.

### C-5 — Correction C5 in the predecessor is withdrawn

The predecessor attributed `content ref not unique` to its patch returning
`count` where the committed code returns `ratios`. That return-shape mismatch
was a **real defect in the probe** and is retained as such, but it was **not**
the cause of the class, and "fixing" it did not remove the class — the class rose
from 173 to 195. The cause is C-2. Attributing a class to the patch when the
class exists identically in the unpatched baseline is the specific error to avoid.

### C-6 — Instrument faults in this stage, discarded rather than reported

| Probe | Fault | Disposition |
|---|---|---|
| end-to-end v2 | one converter for two domains | 195 results discarded; re-run |
| plausibility probe | read shapes from the conversion manifest, not the package | re-run |
| plausibility probe | re-committed the same routing error | re-run |
| D2 reach, attempt 1 | compared `width_px` to `max(0, xmax // 20)` — **the exact expression the code uses**; could not fail | **tautology; figure discarded** |
| D2 reach, attempt 1 | read `width_px` off the shape; it lives inside the nested `bounds` | second, independent vacuity |

The first D2 attempt reported "0 of 290" and that zero was meaningless twice
over: tautological *and* vacuous. It is recorded because "0 findings" from a
broken instrument is the most dangerous shape a measurement can take.

---

## 3. Why the three "regressions" are corrections, not regressions

A correct parse cannot make a target that converts today stop converting, so
the three losses look like a refutation of the located fill layout. Inspecting
their output dissolves that.

All three emit geometry that cannot be drawn:

| target | domain | largest shape extent | declared frame |
|---|---|---|---|
| `0127_enemy_harbour_m` | building | 1087.7 x 528.8 px | 1000 x 800 |
| `1005_special_spy_m` | unit | **-288.6** x 145.0 px | 550 x 400 |
| `1421_cyberInquisitorDrone` | unit | **-288.6** x 145.0 px | 550 x 400 |

A negative width is not a large shape; it is a coordinate delta that ran
backwards. So these three convert today while emitting nonsense, and refusing
them is a correction.

**This inverts the priority.** The interesting question is not why 272 targets
refuse. It is how many of the 290 that convert are quietly wrong. A parser that
fails open is worse than one that fails closed, because the failure never
appears in a count.

---

## 4. The located defect: `parse_rect_bits` does not sign-extend

`convert_building.py:257-267`:

```python
nbits = reader.read_bits(5, label)          # spec says UB[5] -- correct
xmin  = reader.read_bits(nbits, label)      # spec says SB -- SIGNED
xmax  = reader.read_bits(nbits, label)
ymin  = reader.read_bits(nbits, label)
ymax  = reader.read_bits(nbits, label)
```

The four RECT fields are `SB` (signed, two's complement). `BitReader.read_bits`
(`:229-238`) is a correct **unsigned** MSB-first reader. Every shape with a
negative origin is therefore recorded with a large positive value where a
negative was meant.

### 4.1 A reasoning error of mine, and its correction

While investigating I recorded that sign extension could not produce an unordered
RECT, because reading the four fields unsigned "shifts all four by the same
amount ... and a uniform shift preserves order", and I used that to rule the
hypothesis out before testing it.

**That reasoning is wrong, and the error is instructive.** Sign extension is
*not* a uniform shift: it subtracts `2**nbits` only for those fields whose sign
bit is set, leaving the rest alone. That moves the negative-valued fields below
the non-negative ones and therefore *changes their relative order*. A uniform
shift preserves order; a conditional one does not, and RECT fields are
conditionally signed.

Applied to a real decoded shape, `xmin=6832, xmax=1900` at `nbits=13`:

```
6832 >= 4096 (sign bit)  ->  6832 - 8192 = -1360
1900 <  4096             ->  +1900
-1360 < 1900             ->  ORDERED
```

and likewise `ymin=6352 -> -1840` against `ymax=2500`. The scrambled values are
exactly what an unsigned read of signed data looks like. The hypothesis was
rejected by a plausible-sounding argument that I did not check, and the cost was
that the real defect sat unexamined for the whole of the predecessor.

### 4.2 The decisive measurement

One change — sign extension on the four fields — and nothing else:

```
                     baseline (unsigned)   with sign extension
negative shapes            2445 of 4347            0 of 4347
targets with >= 1             74                    0
D2 shapes (true extent)      3452                  3452      <- unchanged
failures                        0                    0
```

**2445 of 2445** negative shapes removed, **74 of 74** targets repaired, zero
failures.

`D2` is deliberately left unmoved by this change and is measured separately below.
If it had moved, two causes would have been confounded and neither could have
been credited. That it did not move is what makes the attribution clean.

### 4.3 It is not one tag's payload layout

Negative extents are spread across every shape tag, at similar rates, so the
defect is in the shared RECT decode rather than in one tag's layout:

| tag | shapes | negative | ordered |
|---|---|---|---|
| 2 (DefineShape) | 4171 | 2311 | 1860 |
| 22 (DefineShape2) | 165 | 126 | 39 |
| 32 (DefineShape3) | 11 | 8 | 3 |

---

## 5. A second, independent defect: pixel size read from the edge

Also at `convert_building.py:267`:

```python
"width_px":  max(0, xmax // 20),
"height_px": max(0, ymax // 20),
```

`width_px` is computed from `xmax`, not from `xmax - xmin`. For any RECT with a
non-zero origin this is wrong by exactly the origin, and non-zero origins are the
norm. Measured against the **true** extent — not against the buggy expression,
which is what made the first attempt a tautology:

| | Value |
|---|---|
| Shapes whose recorded size disagrees with their own bounds | **3452 of 4347** |
| Targets affected | **76 of 290** (8 building, 68 unit) |

**D3 — `max(0, ...)`** clamps a negative to zero instead of failing closed. It is
not a measured contributor here (sign extension removes the negatives first), but
it is the reason a bad RECT can pass silently, and a converter in this project is
expected to refuse a value it cannot represent.

These two defects are separable: D1 is about *what the values are*, D2 is about
*how a size is computed from them*, and the measurement above holds D2 fixed
while D1 moves.

---

## 6. Blast radius on committed bytes

Only **two** conversion packages are committed:

| file | shapes | negative | D2-wrong |
|---|---|---|---|
| `assets/converted/buildings/0001_house_1_m/package.json` | 1 | 0 | 0 |
| `assets/converted/units/10033_wild_elephant/package.json` | 28 | **19** | **22** |

So a fix would change **exactly one committed file**. `legacy-manifest.json`
does not cover `assets/converted`, so the 3,258-entry preservation manifest is
unaffected by such a change.

Three test sites pin the affected output and would be amended by the owning
change — `test_convert_building.py:240-241` and `:464-465`,
`test_convert_unit.py:268-269`.

---

## 7. Why this warrants a line and the desync family does not

The two cases look superficially alike and are not.

The desync family required a **layout underdetermined in 5 of 6 parameters**,
converted net zero across the whole candidate set, and had no monotonicity
guarantee separating a partial fix from a wrong one. It was correctly closed as
a measurement.

The RECT defect is different in every respect that matters:

- it is **one function**;
- it is **fully identified** — sign extension is not a free parameter, it is what
  the specification says `SB` means;
- it is **causally closed** — 2445 of 2445 with zero failures, and the
  independent defect held fixed while it moved;
- it is **large** — 74 of 290 converted targets, 56% of all shapes;
- and it is **verified against a fixed corpus**: two committed packages, one
  affected file.

It is the strongest fix candidate M12 has produced.

---

## 8. Claim limits

- **No production code is changed here.** This is a measurement document.
- **The fix is not applied and not tested.** Sections 4 and 5 establish the
  defects and their reach; they do not constitute a passing test suite, and no
  converter test was re-run for this document.
- **Only checks actually run are reported.** The figures come from the pinned
  CPython 3.9.13 interpreter against the working tree at `07c8b19`.
- **"Impossible geometry" means a negative extent**, which cannot be drawn. It is
  an invariant, not a heuristic. An earlier heuristic test — extent beyond 4x the
  declared frame — was reported as 0 and is **not** claimed here, because
  off-stage drawing is legitimate and the threshold was arbitrary.
- **The 3 gained / 3 lost split says nothing about the fill layout's merit.** It
  is net 0 on the candidate set; the losses are attributable to correctly
  refusing wrongly-passing targets, and the gains do not establish the layout.
- **The desync family remains open.** Nothing here closes 272 targets; the
  end-to-end figure for that family is 2.
- **Negative extents were not sought in the refused set**, which cannot contain
  them because it produces no package. The fail-open claim is about the 290 that
  convert.
- **A shape may legitimately be drawn off-stage**, so no in-frame bound is claimed
  for any shape, only the negative-extent invariant.
- **`nbits > 31` at `:260` is unreachable** (five bits cannot exceed 31). Noted as
  an observation, not changed.
- No Flash, Ruffle, ActionScript, or browser executes in any command here; no
  network is used; nothing is written into the repository by any probe.

---

## 9. Next step

A `fix/` line owning `parse_rect_bits` (D1 and D3), amending the three pinned
test sites, and regenerating the one affected committed package. D2 is separable
and could ride the same line or a second one; it is reported separately here so
that its attribution is not confounded with D1's.

The desync family stays open and unproposed. Section 4.1 is the cautionary note
for it: the reason that defect went unexamined was a plausible argument that was
never checked, and the cheapest available test would have found it.