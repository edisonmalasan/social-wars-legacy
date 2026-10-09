# M12 FX / animation re-scope decision

An investigation committed on its own branch, before any proposal. It resolves the
decision that `docs/legacy-m12-asset-parity.md` §6 item 3 named as "a decision, not a
line", and it re-measures §3.3 and §3.4 now that M12 lines 1 and 2 have landed.

**Status:** investigation only. It implements nothing, converts nothing, extracts
nothing, and changes no client source. Every figure below comes from committed
artifacts read by a script, or from a script run against committed artifacts.

---

## 0. Scope, method, and the decision being made

### 0.1 The question

`docs/legacy-m12-asset-parity.md` §6 recommended three items. Items 1
(`asset-package-parameterisation`) and 2 (`image-reference-resolution`) are
delivered and archived. Item 3 was written as:

> **FX / animation re-scope decision** - §3.3 and §3.4 both need a scope decision
> before they can be planned, because neither has committed content to work from.
> This is a decision, not a line.

M12's deliver list is:

```text
all runtime-required SWFs converted or recreated
UI assets converted
FX replaced
animation gaps resolved
```

Items 3 and 4 of that list are "FX replaced" and "animation gaps resolved". This
document decides, with measurements, what work those two items can support, if
any.

### 0.2 Method and sources

Read-only, over committed artifacts:

| source | what it establishes |
|---|---|
| `assets/fx/*.swf` (205 files) | the FX corpus |
| `tools/asset-registry/inspection.json` (1,176 entries) | per-file SWF structure: `frame_count`, `frame_labels`, `symbols`, `bitmap_ids`, `sound_ids`, `has_abc`, `sprite_count`, `exports`, `scene_count`, `max_sprite_depth` |
| `tools/asset-registry/asset_ids.json` (1,627 refs, 4 kinds) | every committed asset reference, with line-2's status vocabulary |
| `tools/asset-registry/target_census.json` (817 targets) | line 1's convertible verdict per target, and its 8 refusal classes |
| `tools/asset-registry/statuses.json` (1,048 files) | per-file extraction status |
| `tools/asset-registry/conversions.json` (2 packages) | the only two converted packages that exist |
| `tools/asset-registry/census_targets.py:104-143` | the candidate derivation rule itself, read as source |
| `packages/game-content/normalized/*.json` (16 files) | committed content |
| `config/main.json` | the raw, un-normalized content source |
| 1,246 text files repository-wide, binary corpus excluded | whether any FX stem is named anywhere |

Four distinct matching rules are applied wherever a stem is searched for, because a
substring match and a whole-token match answer different questions and this project
has been bitten by reading one as the other:

- `whole_file` - raw substring occurrences anywhere in the file
- `code_only` - occurrences with comments and string literals stripped (two-state lexer)
- `token` - the stem as a whole identifier or path component
- `quoted` - the stem inside a quoted string literal

---

## 1. FX re-measured: the 205 are 205, and the absence is structural

§3.3 recorded "**0 of 205** stems appear in the normalized content package". That is
**reproduced**, and it is now measured far more widely than the original pass.

### 1.1 Corpus shape

| property | value |
|---|---|
| files under `assets/fx/` | 205, all `.swf`, all in one directory |
| distinct stems | 205 |
| stems containing exactly one `.` | **205 of 205** |
| stem families | `b.` 56, `m.` 6, `p.` 143 |
| stem length min / median / max | 5 / 13 / 25 |

### 1.2 The naming search, under four rules

| corpus searched | `whole_file` | `code_only` | `token` | `quoted` |
|---|---|---|---|---|
| 16 normalized content files | 0 | 0 | 0 | 0 |
| raw `config/main.json` | 0 | 0 | 0 | 0 |
| all 1,627 `asset_ids.json` refs (images 607, item_sprites 872, magic_sprites 10, sounds 138) | 0 | 0 | 0 | 0 |

### 1.3 The FX vocabulary is disjoint from every vocabulary content does name

This is the finding that changes §3.3 from "a search that found nothing" into
"a structure that makes a hit impossible":

| domain | files | stems with a `.` |
|---|---|---|
| `assets/sprites` | 862 | **0** |
| `assets/fx` | 205 | **205** |

Content names sprites, magics, sounds and images. None of those vocabularies
contains a dotted identifier; the FX vocabulary is dotted by construction. So no
committed content row could name an FX asset even in principle, under the naming
convention the FX corpus itself uses. Collisions confirm it from the other side:

- FX stems that are also sprite stems: **0**
- FX stems that are also magic stems: **0**
- FX stems that are also image basenames: **0**
- non-FX files whose exported `symbols` include an FX stem: **0**

### 1.4 The one naming source that exists is a self-reference

Each FX file's own exported symbol equals its own file stem, for **205 of 205**
files, with zero exceptions. Occurrence accounting, spelled out for one stem so the
figure is checkable rather than asserted:

```text
file                              assets/fx/b.acidBlue.swf
stem                              b.acidBlue
symbols                           ['b.acidBlue']
exports                           []
occurrences of the stem            3
  explained by its own path       2
  explained by its own symbol     1
  unexplained                     0
```

So every FX stem that appears anywhere in `inspection.json` is accounted for by that
file's own path and its own symbol. There is no cross-reference.

### 1.5 The candidate explanation is undecidable with this oracle

The original investigation offered a candidate explanation - that FX is referenced
from ActionScript inside the game SWF, "which this oracle cannot read" - and
correctly refused to record it as a conclusion. That refusal is now measured rather
than assumed:

- **205 of 205** FX files carry ActionScript (`has_abc: true`).
- `inspect_swf.py` records **presence** (`has_abc`, `abc_count`) and **not contents**.

So the candidate explanation is not merely unrecorded; it is **unreadable with the
committed tooling**. `assets/flash/` holds 60 `Basesec_*.swf` builds, all with
`has_abc: true`, 39 frame labels, and 407-420 exported symbols each. Nothing in the
committed corpus links any of them to any FX file.

### 1.6 FX is not a census domain, and could not become one

`target_census.json` covers exactly two domains, `building` and `unit`. The string
`assets/fx` occurs **0** times in it. Because candidates are derived from committed
content (§2.2), an FX file cannot acquire a verdict without a content row naming it,
and §1.3 shows no such row can exist. FX verdicts in the census: **0**.

---

## 2. What the earlier investigation did not record: 86 of 205 FX files are already extracted

This is the substantive new measurement, and it was absent from §3.3.

### 2.1 The extracted FX population, measured three independent ways

| measure | value |
|---|---|
| `statuses.json` keys under `assets/fx/` with status `extracted` | 86 |
| directories under `assets/converted/images/` whose name is an FX stem | 86 |
| sum of `bitmap_ids` over the 205 FX inspection records | 639 |
| PNG files under those 86 directories | 639 |

The two 86s are computed over different artifacts and agree; the two 639s are
computed over different artifacts and agree. **86 of 205 FX SWFs have their bitmaps
extracted and committed; 639 bitmaps exist on disk.**

### 2.2 Nothing is stranded

The 119 unextracted FX files were checked for content that was merely never
extracted:

| | value |
|---|---|
| unextracted FX files | 119 |
| of those, carrying **zero** `bitmap_ids` | **119** |
| of those, carrying bitmaps that were not extracted | **0** |
| bitmaps stranded by not being extracted | **0** |

Every one of the 119 is empty of bitmaps. Bitmap extraction over the FX corpus is
**complete**, not partial - there is no un-run extraction job hiding here. Corpus-wide,
`statuses.json` records 1,046 `extracted` and 2 `converted` across 1,048 files.

### 2.3 Animation inside the FX corpus is nearly absent

| frame_count | FX files |
|---|---|
| 1 | 198 |
| 2 | 1 |
| 18 | 2 |
| 21 | 2 |
| 25 | 1 |
| 42 | 1 |

Only **7 of 205** FX files carry a timeline longer than one frame, and **2 of 205**
carry any frame label at all. The 198 single-frame files are not unanimated artwork:
186 of them declare more than one `sprite`, which means N placements on a one-frame
timeline, not N frames. `scene_count` is 1 and `max_sprite_depth` is 1 for all 205.

---

## 3. §3.4 animation is now measurable, and FX is not its blocker

§3.4 said animation was "blocked behind §3.1, with one measured contradiction already
recorded". Line 1 closed the tooling gap and produced the census, so §3.4 is measurable
for the first time. The result does not match the expectation recorded in §3.4.

### 3.1 The animation vocabulary is small, Portuguese, and unit-shaped

Of 862 sprite files, **422** carry `frame_labels`. Every label in the convertible
population, verbatim:

| label | occurrences |
|---|---|
| `QUIETO` | 68 |
| `ANDAR` | 68 |
| `ATAQUE` | 68 |
| `MUERTE` | 68 |
| `PICAR` | 63 |
| `QUIETO ARBUSTO` | 1 |
| `ANDAR ARBUSTO` | 1 |
| `ATAQUE CUCHILLO` | 1 |
| `SA1` | 1 |
| `ESPECIAL` | 1 |

**10 distinct labels**, five of them on all 68 convertible targets. They are reported
verbatim and deliberately not translated, for the reason `godot-unit-animations`
recorded: nothing selects a state for a translation to name.

### 3.2 `frame_count` is not the animation measure

| population | targets with `frame_count > 1` |
|---|---|
| all 817 census targets | **5** |
| the 290 convertible targets | **1** |

68 of the 290 convertible targets carry labels while only 1 has more than one frame.
The root-level `frame_count` a SWF header records is therefore not a proxy for
animation, and a line that used it as one would understate the animation surface by
roughly 68 to 1.

### 3.3 Where the 422 labelled sprites actually stand

| | value |
|---|---|
| labelled sprite files | 422 |
| converted by the census | **68** |
| refused by the census | **313** |
| not a census candidate | **41** |
| sums to the population | yes (68 + 313 + 41 = 422) |

**Animation is blocked behind refusal classes, not behind FX.** 313 of 422 labelled
sprites carry a converter refusal.

### 3.4 The refusal classes, sized, with the labelled share of each

`refused_targets_in_several_classes` is 0, so each refused target has exactly one
class, and the eight classes sum exactly to the recorded 527:

| refusal class | total | of which labelled |
|---|---|---|
| `unknown fill style at swf <target>: #` | 137 | 76 |
| `unresolvable bitmap fill at shape # -> #` | 133 | 9 |
| `shape byte overrun at swf <target>` | 104 | 89 |
| `unsupported shape tag at swf <target>: #` | 64 | 53 |
| `unsupported timeline tag at swf <target> sprite #: code # (PlaceObject#)` | 57 | 56 |
| `shape bit overrun at swf <target>` | 20 | 18 |
| `shape byte misaligned at swf <target>` | 11 | 11 |
| `unsupported tag in timeline at swf <target>: code #` | 1 | 1 |
| **sum** | **527** | **313** |

The largest single lever for animation is **`shape byte overrun`**: 104 targets, of
which 89 are labelled. Lifting that one class alone would move convertible animation
sprites from 68 to 157. Lifting all eight would reach 381 of 422 (90%), leaving the 41
non-candidates still uncovered (§3.5).

### 3.5 The 41 non-candidates are a content-side gap, and the split has two opposite causes

Reading `census_targets.py:113-143` gives the derivation rule directly. A target is a
candidate when **both** clauses hold:

- (a) the sprite's bitmaps are already recorded as `extracted`
- (b) its `img_name` resolves to **exactly one** normalized content row

Clause (b)'s failure has two opposite sub-cases that mean different things. Measured
over the 862 real sprite files, this reproduces the recorded 817 exactly:

| outcome | files |
|---|---|
| clause (a) fails: not `extracted` | 5 |
| clause (b) fails: resolves to **zero** content rows | 10 |
| clause (b) fails: resolves to **2 or more** content rows | 30 |
| both clauses pass -> candidate | **817** |

Restricted to the 422 labelled sprites: 4 clause-(a) failures, 9 zero-row, 28
multi-row, 381 candidates. The 28 multi-row cases are genuine **content ambiguity** -
one sprite claimed by several items, which the docstring says would otherwise
"report a refusal class that is really a content ambiguity":

```text
1001_worker_m        claims=3 -> unit 1039 Worker II, 1040 Worker III, 1041 Worker IV
1053_golem_boss_m    claims=3 -> unit 1049 TankBoss, 1053 GolemBoss, 1086 Mechanical Golem
0185_orc_turret_m    claims=2 -> building 185 Ork Turret II, 208 Enemy Ork Turret II
1057_t-rex_m         claims=2 -> unit 1057 T-Rex Green, 1087 T-Rex
```

The 9 zero-row cases are the opposite: the reference is real and `extracted`, and no
content row claims it at all - `1001_worker_w`, `1007_soldier_1_m`,
`1007_soldier_1_w`, `1008_bazooka_1_m`, `1008_bazooka_1_w`,
`1014_machinegunjeep_1_m`, `1014_machinegunjeep_1_w`, `1034_un_allied_1_m`,
`1034_un_allied_1_w`.

### 3.6 So animation has two independent blockers

| blocker | labelled sprites |
|---|---|
| a converter refusal | **313** |
| a content-side gap (zero-row or multi-row) | **41** |
| convertible today | 68 |
| total | 422 |

Neither axis alone reaches the population, and the two do not overlap, because the 41
non-candidates were never evaluated by a converter at all.

### 3.7 The `max_frame` contradiction is the normal case, not a rarity

`godot-unit-animations` recorded that for the one committed converted unit package,
committed `max_frame` was 2 while the parsed root `frame_count` was 1 and the labelled
sprite held 29 - and correctly refused to adopt `max_frame` as a frame count on the
strength of that one data point. Over the 290 convertible targets, where both values
exist:

| | value |
|---|---|
| `max_frame` equals recorded `frame_count` | **14** |
| they differ | **276** |

So the recorded contradiction generalises: `max_frame` is not the asset's frame count,
and treating it as one would be wrong for 95% of the convertible population. The
distributions behind it are near-constant: `max_frame` is 5 on 427 of 429 units and 2 on
ids 923 and 933; over 470 buildings it is 2 on 446 and 1 on 24.

### 3.8 Converted packages do record labels

The one committed converted unit package, `10033_wild_elephant`, has
`bitmaps=56`, `output_bytes=384701`, and its source SWF carries exactly
`['QUIETO', 'ANDAR', 'ATAQUE', 'MUERTE', 'PICAR']`. Note that it is **not** a census
candidate - its `asset_ids` status is `converted`, so clause (a) excludes it by design.
Conversion does preserve the animation vocabulary; what is missing is coverage.

---

## 4. The decision

### 4.1 "FX replaced" - close by measurement as unsatisfiable from this oracle

| question | measured answer |
|---|---|
| does any committed artifact name an FX asset? | no, under 4 rules across 16 normalized files, the raw config, and 1,627 refs |
| could one, given the vocabulary? | no - the FX vocabulary is dotted and no content-facing vocabulary is, so 205 of 205 stems are structurally unnameable |
| is there a naming source in the corpus? | only each file's own symbol, which is a self-reference (205 of 205, 0 unexplained occurrences) |
| could the likely source be read? | no - 205 of 205 files carry ABC, and the committed tooling records presence, never contents |
| is there FX work left undone? | no - 86 of 205 are extracted, 639 bitmaps on disk, and all 119 unextracted files carry zero bitmaps |
| could FX enter the census? | no - FX is not a census domain and candidacy requires a content row |

**Decision: §3.3 closes as an explicit re-scope.** "FX replaced" cannot be delivered
by this oracle, because there is no committed FX specification to replace anything
with, and manufacturing one would fabricate content. The bitmaps that can exist
already exist. The residue worth committing is this record, not a mechanism.

### 4.2 "animation gaps resolved" - measurable, and not gated on FX

**Decision: §3.4 is feasible and its prerequisite is refusal-class work, not FX work.**
The line this re-scope authorises is a refusal-class line, and the measurement above
sizes which class matters:

> Lifting `shape byte overrun` (104 targets, 89 labelled) alone would take convertible
> animation sprites from **68 to 157**, more than doubling them.

This is a recommendation, not an authorisation. §4.1 and §4.2 change M12's ordering:
the 8 refusal classes move from "one of three open decisions" to the critical path for
**two** deliver items - "all runtime-required SWFs converted or recreated" (290 of 817
convertible) and "animation gaps resolved" (68 of 422 labelled sprites convertible).

### 4.3 §3.2 "UI assets converted", re-measured after line 2

| status | count |
|---|---|
| `passthrough` | 566 |
| `extracted` | 9 |
| `ambiguous` | **0** |
| `missing_source` | 32 |
| total | 607 |

Line 2 closed the 50 `ambiguous` references. The residue is the 32 `missing_source`
images, which stay absent **by decision, not oversight**.

---

## 5. Claim limits

- **This investigation implements nothing.** No conversion, extraction, client change,
  spec change, or tool change. Every figure comes from committed artifacts.
- **"Extracted" means bitmaps exist on disk; it is not conversion.** An extracted
  bitmap is not claimed to be drawable, correctly cropped, or correctly scaled.
- **`frame_count` is reported as the inspection manifest records it**, a root-level
  header value. No claim is made that it bounds a sprite's timeline.
- **Frame labels are reported verbatim and not translated.** No label is claimed to
  name a game state, because nothing selects a state.
- **`max_frame` is reported as a distribution, and is adopted nowhere** as a frame
  count, duration or loop bound. Section 3.7 strengthens rather than relaxes the
  refusal `godot-unit-animations` recorded from one data point.
- **The refusal-class lever is sized, not validated.** Section 3.4 shows which class
  holds the most labelled sprites. Whether `shape byte overrun` can be lifted without
  inventing a parsing rule is a separate question this document does not answer, and
  guessing at it is exactly the failure this project has declined repeatedly.
- **The 41 non-candidates are described, not resolved.** Recommending that
  `1001_worker_m` belong to Worker II rather than Worker III or IV would be a content
  decision this oracle cannot make.
- **`assets/flash/` builds are historical.** No claim is made that any `Basesec_*.swf`
  is the build the legacy client loaded, beyond what §2.3 of the binding investigation
  recorded.
- **Absence of a committed FX reference says nothing about what the Flash client
  displayed.** FX may have been referenced entirely from ActionScript at runtime, which
  is the undecidable candidate in §1.5.
- **No pixel parity and no windowed capture**, because nothing is rendered.
- **No Flash, Ruffle, ActionScript, or browser executes**, and no network is used.

---

## 6. Corrections

Six instrument defects were found and corrected during this investigation. Five were
mine and are recorded here rather than quietly fixed; two of them were **printed
conclusions that their own data falsifies**, which is the class worth recording.

**C1 - "92 FX stems extracted" is wrong; the figure is 86.**
An early pass counted FX stems by raw substring search over `image_extraction.json`
text and reported 92. The token-exact population is **86**, confirmed by two
independent measures that agree (`statuses.json` keys, on-disk directories). The
six-stem delta is substring containment, each named and measured:

```text
b.electrical    contained in b.electricalExplosion, b.electricalYellow, b.electrical_verde, b.electrical_verde2
p.beamBlue      contained in p.beamBlueElectric
p.blueLaser     contained in p.blueLaserBeamThin, p.blueLaserBullet, p.blueLaserShot
p.bullet        contained in 7 longer stems
p.energyBall    contained in p.energyBall2, p.energyBallBlue, p.energyBallBlueBig
p.laser         contained in 12 longer stems
```

This is the recorded substring-vs-token hazard, and it would have overstated FX
readiness by 7%.

**C2 - the first extraction pass read the wrong file and reported 0 extracted.**
It read per-file status from `registry.json`, where all 205 FX entries carry status
`registered`. Extraction status lives in `statuses.json`. The "0 extracted / 205
untouched" figure that pass printed was wrong; the correct figure is 86 extracted, 119
untouched.

**C3 - `inspection.json` `entries` is a dict keyed by path, not a list.**
The first inspection script tested `isinstance(v, list)`, concluded there was no entry
list, and exited without reporting anything. It reported a shape rather than a
finding, and would have read as "no data" instead of "wrong assumption".

**C4 - a printed conclusion was asserted, and its own section falsifies it.**
An intermediate pass ended with the line:

> every unit sprite with an animation is already in the convertible set, so animation
> is NOT blocked behind a refusal

while its own section 1, twenty lines earlier, recorded 313 of 422 labelled sprites
as `refused`. The conclusion was written before the number was read. **Withdrawn.**
The measured statement is in §3.3: animation *is* blocked behind refusal classes. This
correction is the reason §3 exists in this document's form.

**C5 - a second printed conclusion was asserted, and measurement falsified it.**
Another pass ended with:

> the census's 817 candidates are derived from committed content; a file no content
> row names is not a candidate

while its own §6 measured that **all 41** labelled non-targets **are** named by an
`item_sprites` reference. Both halves were wrong: the real rule is the two-clause
derivation in `census_targets.py:113-143` (§3.5), and clause (b) excludes a sprite
precisely when a content row *does* name it, several times. **Withdrawn** and replaced
by the measured derivation.

**C6 - a partition arithmetic error in the blocker summary.**
A pass reported "content side would give at most 418, refusal side at most 694". The
694 exceeds the 422 population, and 37 omitted the 4 clause-(a) failures. The correct
partition, which sums to 422, is in §3.6: 68 convertible, 313 refused, 41
content-side gap.

**No correction changes a conclusion.** C1 changed a figure (92 to 86) and C2 changed
one back (0 to 86); C4 and C5 withdrew two asserted sentences and replaced them with
measured ones; C6 fixed a sum. The decision in §4 is stated on the corrected figures.