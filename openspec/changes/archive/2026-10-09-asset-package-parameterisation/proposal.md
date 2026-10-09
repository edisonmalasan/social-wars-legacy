# Proposal

## Why

M12's investigation (`docs/legacy-m12-asset-parity.md`, merged `f7f9861`) recorded that the
milestone exit criterion is **already met** while the deliverables are essentially unstarted, and
it named `godot-asset-package-parameterisation` as the recommended first line because it is
feasible, has an oracle in M4's two committed packages, and unblocks the rest.

Before proposing it, I measured whether it is actually feasible. **It is not the plumbing the
recommendation implied, and the measurement changed the shape of the change twice.**

### 1. The two converters are hard-wired to one target each

`convert_building.py` (805 lines) hard-codes `TARGET_STEM = "0001_house_1_m"` at line 36 and uses
it at **10** sites. `convert_unit.py` (596 lines) hard-codes `TARGET_STEM` **and**
`TARGET_LEGACY_ID = "933"` **and** a derived `SOURCE` at lines 38–40, used at **10** sites. Their
only CLI arguments are `--repo-root` and `--out-root`.

Content resolution is already target-parameterised in shape: the building converter finds its row
by `img_name == stem` (line 609) and the unit converter requires **both** `legacy_id` and
`img_name` to match (lines 313–314). Both already fail closed on a non-unique match. So the
selection logic exists and is guarded; only the *inputs* are missing.

### 2. Parameterisation is only half the story — 290 of 817 targets convert today

> **CORRECTION (Apply stage, 2026-10-09).** This section originally read *"365 of 817"* and
> reported units at **365 / 365 (100%)**, **587** packages available, and the unit converter as
> generalising cleanly. **The unit figure was false; it was produced by a defect in the measuring
> instrument, not by the unit converter.** See the correction record immediately below. The
> corrected figures are **290 / 817**, units **68 / 365**, and **290** packages available. The
> building figures below were re-measured and are **unchanged**.

I ran both committed converters over **every** candidate, not a sample. A candidate is a sprite
whose bitmaps are already `extracted` and whose `img_name` resolves to **exactly one** row in the
committed normalized content. That is **452** buildings and **365** units — re-confirmed by the
delivered census.

| | converts | fails |
|---|---|---|
| **units** | **68 / 365 (18.6%)** | **297 (81.4%)** |
| **buildings** | **222 / 452 (49.1%)** | **230 (50.9%)** |

Neither converter generalises cleanly. Building failures fall into **five disjoint classes** and
unit failures into **seven**, with **no target in more than one class** in either domain, so the
class boundaries are four/two separate root causes rather than one:

| domain | class | targets |
|---|---|---|
| building | `unresolvable bitmap fill at shape # -> #` | **133** |
| building | `unknown fill style` | **61** |
| building | `unsupported shape tag: 83` | **20** |
| building | `shape byte overrun` / `shape bit overrun` | **14** / **2** |
| unit | `shape byte overrun` | **90** |
| unit | `unknown fill style` | **76** |
| unit | `unsupported timeline tag … (PlaceObject#)` | **57** |
| unit | `unsupported shape tag: 83` | **44** |
| unit | `shape bit overrun` | **18** |
| unit | `shape byte misaligned` | **11** |
| unit | `unsupported tag in timeline` | **1** |

The building **133 / 61 / 20 / 16** figures are unchanged and confirmed; **16** resolves to
**14** `shape byte overrun` plus **2** `shape bit overrun`, which the original hand-written
classifier had lumped through a catch-all branch.

So **290 packages are available immediately** (222 buildings, 68 units) and **527 targets are
blocked** by unresolved format questions. That is the honest deliverable boundary, and it is why
this change is scoped to *parameterisation and measurement*, not to mass conversion.

#### Correction record — the 365/365 unit figure was an artefact of the measuring instrument

The Propose-stage measurement drove the converters by **reassigning their module-level target
constants** in memory. It reassigned `TARGET_STEM` and `TARGET_LEGACY_ID`, but the pre-change
`convert_unit.py` also carried a third constant:

```python
SOURCE = "assets/sprites/" + TARGET_STEM + ".swf"
```

`SOURCE` was computed **at import time**. Reassigning `TARGET_STEM` afterwards never moved it, so
**every one of the 365 unit targets was parsed from the same `10033_wild_elephant.swf`** while
being attributed to a different stem and `legacy_id`. The 365 "successes" were the elephant
converted 365 times. The figure's implausibility — a perfect 365/365 — was the tell.

Why it did not fail outright: the unit converter resolves each bitmap `character_id` against **the
target's own** extraction directory, and the elephant's ids `[1, 3, 5, 7, 9, 11, 13, 15, 17, 20]`
are all present in most unit sprites' directories (`1002_Red_Tank_m` has `[1, 3, 5, 7, 9, 11, 14,
17, 20, 23]`). So the elephant's shape data resolved against each target's bitmaps and assembled
without error.

This is **precisely the failure mode design D1 exists to prevent**, and the census was the thing
that caught it: D1 deletes the module constants so a batch run cannot silently re-derive one
target. Independent confirmation, run after the fact against the parameterised CLI:

- `convert_unit.py --target-stem 1006_red_bazooka_jeep_m --target-legacy-id 1006` → exit **1**,
  `shape byte misaligned at swf assets/sprites/1006_red_bazooka_jeep_m.swf`
- `convert_unit.py --target-stem 10023_gorilla --target-legacy-id 923` → exit **0**

**What this does and does not change.** The *requirements* are unaffected: the census spec asks
for the convertible set to be measured and refusals recorded, and it now is. What changed is the
premise that a mass-conversion line could start with units — **no domain is 100% convertible**, so
there is no domain where a line can be scoped without first resolving refusal classes.

### 3. Two plausible fixes were tried and both were refuted

**Refuted — "the sentinel is just the unit converter's placeholder rule".** `first-unit-conversion`
already specifies a *Bitmap-fill resolution with recorded placeholders* rule: unreferenced
`65535` fills are recorded verbatim, referenced ones fail. The building converter has no such
rule; it validates every fill in every style array. That made the dominant 133-target class look
like a missing port. I ported the rule into a temp copy and re-ran all 452 buildings:
**0 additional targets converted and 0 regressed.** Worse, a separate 40-target probe *disagrees*
with that result: it finds **697 unreferenced** and **14 referenced** 65535 fills, and finds
neither in **27 of 40** targets. **The cause of the largest failure class is unestablished**, and
this change must not ship a guess at it.

**Refuted — "a single-target run will clobber the other tool's manifest entry".** Reading the
code suggested the merge was single-target, which would make an N-target batch lose N−1 entries.
Measurement shows both converters merge into the committed manifest: either one alone emits a
**two**-package `packages` list with `counts.packages = 2`. There is no data loss and no
merge-threading requirement.

### 4. The reproduction oracle is checkout-form dependent — a fourth LF-defect instance

Both committed packages reproduce their recorded `package_sha256` exactly (`7de262e9…366b92a7`,
`c40b754c…05d1c7`), and so do `conversions.json` and `statuses.json` — **but only once
line endings are normalised**. Three of those four files carry CRLF in the working tree
(`statuses.json` +1,054 bytes, `conversions.json` +35, the unit `package.json` +1,790) while their
committed blobs are LF, because `.gitattributes` pins `asset_ids.json` and `coverage.json` but
**not** these paths.

The sharp edge is deeper than a comparison. `fingerprint_inputs` (`convert_building.py:517-525`)
digests **raw working-tree bytes** of `buildings.json`, `inspection.json`, and
`image_extraction.json`, and that digest *is* the package's `content_version`. The latter two are
unpinned and carry **170,096** and **1,219,378** CRLF on disk. So the committed `content_version`
values are digests of one checkout form:

| | raw disk bytes | LF-normalised |
|---|---|---|
| buildings fingerprint | `ddeca799…` **(matches committed)** | `c4e76e6d…` |
| units fingerprint | `9d8ad3b3…` **(matches committed)** | `a0c3861f…` |

On any LF checkout both committed packages stop reproducing and `conversions.json` becomes
unreproducible. The project already fixed this exact class for the compatibility guard
(`apps/compat-api/guard_baseline.py`, "text digests are line-ending invariant, so the baseline
holds across checkout forms"); the converters never received the same treatment.

## What Changes

1. **Target selection becomes a required input** in both converters — building: the sprite stem;
   unit: the stem plus its content `legacy_id`. The module constants become defaults that are
   removed, not silently retained, and a missing target fails closed with a clear message and no
   writes.
2. **`fingerprint_inputs` digests line-ending-normalised bytes**, so `content_version` is
   checkout-independent, and the affected paths are pinned LF in `.gitattributes`.
3. **A target census tool** (`tools/asset-registry/census_targets.py`) runs both converters over a
   declared candidate set into a contained output root and writes a deterministic
   `tools/asset-registry/target_census.json` recording every target's verdict and, for failures,
   its refusal class.
4. **The two committed packages are re-derived** under the deterministic fingerprint and
   `conversions.json`, `statuses.json`, and the compatibility guard baseline are regenerated.
5. **The 230 building refusals are recorded**, with their measured classes and counts, as an
   explicit refusal surface — never silently dropped.

## Non-goals

- **No fix for any of the 230 building refusals.** Three of the four classes are unresolved
  format questions and the fourth's cause is unestablished by my own contradictory measurements.
  Each is a separate investigation line.
- **No mass conversion.** 290 packages are available; committing them is roughly 15,000 files and
  a preservation-manifest regeneration. That is a separate line with its own measured diff, and it
  delivers no client-visible progress while `package_paths.gd` still pins two packages.
- **No client change.** `package_paths.gd`, the Godot client, the Compatibility API, and the
  legacy server are untouched.
- **No change to the parsed subset, the package schema, or the `conversion-v1` envelope.**
- **No Flash, Ruffle, ActionScript, or browser execution**, and no network access.

## Impact

- `tools/asset-registry/convert_building.py`, `convert_unit.py`, new `census_targets.py`.
- `tools/asset-registry/target_census.json` (new evidence), `conversions.json`, `statuses.json`,
  and both committed packages (re-derived, `content_version` only).
- `.gitattributes`; `tests/fixtures/godot-compatibility-boot/guard-baseline.json` (regenerated).
- `openspec/specs/first-building-conversion`, `first-unit-conversion` (modified) and a new
  `asset-package-census` capability.
- Preserved inputs — sprites, extracted bitmaps, inspection and extraction manifests, normalized
  content, saves, config, villages — are **read-only** and must remain byte-identical.