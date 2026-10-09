# M12: the desync family's downstream, and why it is not one defect

Status: investigation. No production code is changed by this document, and no
line is proposed.

Predecessors: `docs/legacy-m12-desync-origin.md` (PR #356, merged `07c8b19`) and
`docs/legacy-m12-signed-rect.md` (PR #357, merged `ef93fdb`).

This document measures the one thing the predecessor left explicitly unmeasured,
and then reports a negative result that constrains every later attempt.

`docs/legacy-m12-signed-rect.md` correction **C-4** withdrew the predecessor's
downstream blocker claim and recorded why:

> The downstream picture was never measured, because the probe never reached the
> downstream path for 195 of the targets.

That is what this document measures. It is not a new claim about the family's
origin; it is the first valid reading of where the family goes once the located
defect is corrected.

---

## 1. Summary

| question | answer |
|---|---|
| Is the committed `target_census.json` still current? | **Yes**, measured over all 817 targets: zero differences |
| Where does the family land once the located defect is corrected? | **187 of 270 stay in a parse-phase refusal**; only 8 reach asset resolution |
| How many targets does the located defect convert? | **2** — reproducing C-3 by name |
| How many family targets does the located defect not touch at all? | **118 of 272**, byte-identically |
| Is the family one defect? | **No** — at least two disjoint populations, separated by measurement |

The headline is the 118. The located defect is the best-constrained parameter in
the family and it cannot reach 43% of it.

---

## 2. Precondition: is the committed census still current?

Nothing below is worth measuring against a stale baseline, so the baseline was
checked first.

`tools/asset-registry/target_census.json` was last written at `2d51b61`. Both
`convert_building.py` and its recorded input `asset_ids.json` changed afterwards
at `8961f8c`, the signed-RECT fix. So the committed census describes a parser
that is no longer in the tree, and **no test regenerates it** — every census test
writes to a temporary directory.

The whole population was therefore re-measured with the shipped parser into a
disposable out-root outside the repository, and compared target by target.

| check | result |
|---|---|
| candidates in both runs | 817 / 817, **same stem set** |
| converted in both | 290 / 290 |
| refused in both | 527 / 527 |
| calibration — committed-converted still converted | **290 of 290** |
| verdict moves in either direction | **0** |
| refusal-class changes among targets refused in both | **0** |
| four-class family, committed and re-run | **272 / 272** (77 building, 195 unit both) |

Every one of the eight refusal classes is byte-identical in count. **The
committed census is current**, and the family's whole recorded baseline — the
272, the 77/195 split, and all the class counts every prior line cites — stands
against the shipped parser.

### 2.1 And yet it cannot prove that

The null result is real, but the reason it is a null result is not reassuring.
The census's top-level keys are `counts`, `policy`, `refusal_class_totals`,
`refused_targets_in_several_classes`, `result`, `schema_version`, `targets`.
**It records no input digests and no tool revision.**

It is current by luck. The signed-RECT fix changed recorded *values* for targets
that already converted and never changed a verdict, so nothing that the census
records moved. A parser change that shifted one target across the
converted/refused boundary would leave this file silently wrong, and nothing in
the repository would detect it. That is the same dependency class as
`asset_ids.json` hashing `conversions.json`, which the signed-RECT line
discovered only because the full test discovery failed.

Recorded as a gap, not fixed here: this investigation owns no production code.

---

## 3. The downstream picture, measured for the first time

The located defect is a solid fill colour in an RGBA-tagged shape being 3 bytes
rather than 4. It is installed as a probe-level override of
`convert_building.parse_fill_style`, which reaches both domains because
`convert_unit` imports `convert_building as shared`.

Routing is delegated to `census_targets.evaluate`, the committed code that owns
`CONVERTER_BY_DOMAIN`. That is the specific fault that voided the predecessor's
attempt — it called `convert_building.build_package` for all 272, so the 195
unit targets died at the building content lookup before any parsing. This probe
cannot repeat it, because it does not choose the converter at all.

Controls, all of which had to pass before any number below was read:

| control | result |
|---|---|
| **calibration** — 10 stems the committed record calls converted | 10 of 10 still convert under the patch |
| **return shape** — the patched parser returns the committed key set | solid, gradient and bitmap all identical |
| **install** — the patch actually changes something | 135 of 272 targets change their first-refusal class |

### 3.1 The distributions

Baseline is the shipped parser; the patched column has the located defect
corrected.

| first-refusal class | baseline | located layout | net |
|---|---|---|---|
| `shape byte overrun` | 104 | **187** | **+83** |
| `unknown fill style` | 137 | **26** | **−111** |
| `shape bit overrun` | 20 | 20 | 0 |
| `unsupported timeline tag` (PlaceObject#) | 0 | **13** | +13 |
| `unsupported shape tag` | 0 | **10** | +10 |
| `unresolvable bitmap fill` | 0 | **8** | +8 |
| `shape byte misaligned` | 11 | 6 | −5 |
| **converted** | **0** | **2** | +2 |
| **total** | **272** | **272** | |

Every row is computed from the records and reconciled against the identity
`base == new + outflow − inflow` for all seven classes. That identity is what
makes the table publishable; see correction **C-A** for the formula error it
caught and **C-B** for why the flow table needed a filter before it could be
reconciled at all.

### 3.2 The dominant flow is a cascade, not an exit

Correcting the solid width does not move the family out of the parser. It moves
it *deeper into* the parser.

`unknown fill style` is the largest single flow in the whole experiment:

| from | to | targets |
|---|---|---|
| `unknown fill style` | **`shape byte overrun`** | **84** |
| `unknown fill style` | `unsupported timeline tag` | 10 |
| `unknown fill style` | `shape bit overrun` | 7 |
| `unknown fill style` | `unresolvable bitmap fill` | 6 |
| `unknown fill style` | `unsupported shape tag` | 5 |
| `unknown fill style` | `shape byte misaligned` | 2 |

`unknown fill style` emits **114** of its 137 targets, and 84 of those land in
`shape byte overrun` — a class that grows by 83. Reading a desynced style byte as
a fill type produces a nonsense count, and the walk then reads past the end of
the shape.

So the answer to "where does the family go" is: **mostly nowhere.** 89 targets
flow into `shape byte overrun`, which ends up holding **187 of the 270** refused
targets — 69% of the family, up from 38%.

### 3.3 Only 2 convert, and they reproduce C-3

`1076_robo_soldier_m` and `1155_dwarf_soldier`, both unit targets, both with
baseline class `shape bit overrun`. These are exactly the two named in the
signed-RECT document's C-3, reached independently by a different harness. The
figure reproduces; it is not claimed as new.

---

## 4. The family is not one defect

This is the finding that constrains everything later.

135 targets keep the same first-refusal *class* under the patch. That is weaker
than it looks, because two targets can share a class and differ in detail — so
those 135 were compared on their full recorded `problems` lists:

| group | targets |
|---|---|
| problems list **byte-identical** to baseline — the patch had no observable effect | **118** |
| same class, different recorded detail | 17 |
| first-refusal class changed | 135 |
| converted | 2 |
| **total** | **272** |

**118 of the family — 43% — is not reachable by the located defect at all.** Not
"resolves to the same class"; the converter's entire recorded verdict for those
targets is unchanged, byte for byte.

| untouched group | breakdown |
|---|---|
| by domain | 106 unit, 12 building |
| by baseline class | `shape byte overrun` 98, `shape bit overrun` 10, `unknown fill style` 6, `shape byte misaligned` 4 |

Of the 239 targets that remain inside the four-class family under the patch,
**118 do not move and 121 do**.

The consequence is direct. "The desync family" is not a single defect with a
single fix, and any line justified by the located defect reaches 154 of 272
targets at most and converts 2. The other 118 need a defect this investigation
has not located and has not looked for.

---

## 5. The three scope decisions, first measured inside the family

`docs/legacy-m12-desync-origin.md` and the pending decisions both treat
DefineShape4, PlaceObject3 and the bitmap-fill policy as unmasked: before the
located defect, the family refused earlier and these classes never appeared
within it.

They do appear. Under the patch, **31 of the 272** land in them rather than in a
parse failure:

| scope-decision class | inside the family | outside the family | total governed |
|---|---|---|---|
| `unresolvable bitmap fill` | 8 | 133 (all building) | **141** |
| `unsupported timeline tag` (PlaceObject#) | 13 | 57 (all unit) | **70** |
| `unsupported shape tag` (DefineShape4) | 10 | 64 (20 building, 44 unit) | **74** |
| `unsupported tag in timeline` | 0 | 1 (unit) | **1** |
| **total** | **31** | **255** | **286** |

Two observations for the open decisions, neither of which pre-authorises
anything:

1. **The scope decisions govern 286 of the 527 refused targets** — 54% — once the
   located defect is corrected. That is a materially larger share than the 255
   the committed census shows, because the patch unmasks 31 more.
2. **`unresolvable bitmap fill` is 100% building** (141 of 141) and PlaceObject#
   is 100% unit (70 of 70). The bitmap-fill policy is therefore not a symmetric
   decision; it can only ever affect buildings.

---

## 6. Why no line is proposed

1. The located defect converts **2 of 272**, reproducing a figure already
   recorded as C-3.
2. **118 of 272 are provably untouched by it**, so the defect cannot be the
   family's common cause.
3. The corrected layout converts nothing on the committed corpus beyond those
   two, and the family still converts net 0 across all 817 candidates.
4. The only classes that grew are the three scope decisions, which are **not
   pre-authorised** and are not parser defects.

A line built on this measurement would convert two unit targets. §3.2 of the
refusal-class investigation established the pattern; this stage establishes that
the pattern still holds, and adds the reason: the family's dominant population is
not the population the located defect explains.

---

## 7. What the next step must do, and what it cannot use

The census is the wrong instrument for the next step, and this is measurable
rather than a matter of taste.

**All 272 family targets record `problem_count` exactly 1.** The census captures
a target's first refusal and stops; it carries no information about how far the
walk got, where inside the shape the parse diverged, or how many bytes were left
unconsumed. Some non-family targets do record several problems — one building
records 5 — so the field is meaningful and its value of 1 across the family is
the finding: the family fails hard on the first shape it reaches.

So a next step aimed at the 118 cannot start from `target_census.json`. It needs
a per-shape trace that records the entry bit position at which the walk first
disagrees with a reference reading, so the untouched group can be partitioned by
*where* it diverges rather than lumped into one class. That is new evidence of a
kind no committed artifact currently holds.

---

## 8. Corrections

Including corrections to my own instruments. A measurement whose instrument is
defective is discarded, not reported.

**C-A — the reconciliation identity was wrong, and the self-check caught it.**
The flow table only counted target pairs whose verdict was refused in *both*
runs, so the two targets that convert under the patch contributed no outflow
from their baseline class. `shape bit overrun` failed the identity by exactly 2.
The corrected identity counts a converted target as an outflow from its baseline
class; all seven classes then reconcile. The self-check is what surfaced it, and
it was written before the table was believed.

**C-B — the flow table had no inequality filter.** Its first version listed the
135 pairs whose class did *not* change alongside the real ones. Hand-summing a
table of that shape gave 188 `shape byte overrun` against the run's own 187. The
discrepancy was the reason the aggregates stopped being read off the printout
and started being computed from the records and reconciled by identity. A table
that cannot be reconciled is a table that cannot be published.

**C-C — the return-shape probe was vacuous, and the control refused it.** The
gradient probe payload was one byte short, so the shipped and patched parsers
*both* overran and no key set was ever reached. The control reported the
comparison as failed rather than passing it, which is the correct behaviour and
the reason the control was worth writing. The shipped and corrected probes now
return identical key sets for all three fill types.

**C-D — a background run reported nothing.** A background invocation left a
0-byte stream and no artifact. The run had in fact executed, but its output was
not captured, so the foreground run was used. Two independent runs then agreed
on every aggregate before either was relied on.

**C-E — two crashes in reporting code after the measurements had printed.** A
generator iterated whole records where a stem-keyed map was expected
(`TypeError: unhashable type: 'dict'`), and a report read a `domain` key from
`evaluate()`'s result, which does not carry one (`KeyError`). Both were in the
reporting tail; the measured quantities had already been computed from records.
Fixed by keying on stems and looking the domain up from the family membership.

**C-F — the novelty of the "2 convert" figure was initially overstated.** The
first reading of this experiment treated two conversions as a new result. The
signed-RECT document's C-3 already records the same two targets by name. This
document claims them as an independent reproduction, not as a discovery.

---

## 9. Claim limits

- **No line is proposed, and nothing here is a deliverable.** The measurement
  converts 2 of 272 targets.
- **No defect is located for the untouched 118.** That group is a *negative*
  result: it bounds where the located defect reaches. It says nothing about what
  is wrong with those targets, and the two defects need not be the same kind.
- **"Not one defect" is a statement about the located defect's reach**, not a
  claim that the family has exactly two causes. At least two disjoint
  populations are established; there may be many more.
- **The parser patch is derived-provisional.** A solid fill colour being 3 bytes
  in an RGBA-tagged shape is read off the located defect in
  `docs/legacy-m12-desync-origin.md` §5 and is never observed from a Flash
  client.
- **Family membership is read from the committed census, not re-derived.** The
  census is verified current in §2 for verdicts and classes; its *membership*
  logic is the committed tool's, used as committed.
- **The three scope-decision classes are reported, never enabled.** Nothing in
  this document pre-authorises DefineShape4, PlaceObject3 or the bitmap-fill
  policy, and the counts in §5 are inputs to those decisions rather than a
  recommendation.
- **No conversion was performed and no repository file was written.** Every run
  used a disposable out-root outside the repository; the committed census was
  read, never regenerated.
- **No rendering, pixel parity, or windowed capture is claimed.** Nothing is
  drawn.
- The 118 figure compares the converter's recorded `problems` lists. Since every
  family target records exactly one problem, that list is its whole verdict, so
  the comparison is a whole-record comparison rather than a partial one.

---

## 10. Reproduction

Pinned CPython 3.9.13, Windows x64. No network, no browser, no Flash.

Preconditions, both outside the repository:

```
C:\Users\Edison\AppData\Local\Temp\opencode\cpython39\pkg\tools\python.exe
C:\Users\Edison\AppData\Local\Temp\opencode\                    (probes)
```

**Step 1 — the baseline check.** Re-measure all 817 candidates with the shipped
parser into a disposable out-root:

```
python -B tools/asset-registry/census_targets.py \
  --repo-root <repo> \
  --out-root <temp>\census_rerun\work \
  --report  <temp>\census_rerun\report.json
```

Elapsed 380.8s, exit 0. Then compare target by target against the committed
`tools/asset-registry/target_census.json`; the comparison asserts identity of
the stem set and calibration of the 290 converted targets.

**Step 2 — the downstream measurement.** Install the located layout as a
probe-level override of `convert_building.parse_fill_style`, run the 272 family
members through `census_targets.evaluate`, and reconcile the flows:

```
python -B <temp>\located_downstream.py     # 190.4s
python -B <temp>\reconcile.py              # reads persisted per-stem records
```

`located_downstream.py` must write its per-stem results before the reporting
tail, so the reconciliation can be re-run without re-executing 272 converters.

**What must hold before any figure is believed:** the return-shape control
reports identical key sets for solid, gradient and bitmap; calibration reports
10 of 10; the population identity `unchanged + changed + converted == 272`
reconciles; and the class identity `base == new + outflow − inflow` reconciles
for all seven classes, counting a converted target as an outflow from its
baseline class.

Not reproduced here: the 817-candidate sweep under the patch. C-3 records it as
3 gained and 3 lost, and this stage did not re-measure it, so no claim is made
about whether that figure still holds after the census check in §2.
