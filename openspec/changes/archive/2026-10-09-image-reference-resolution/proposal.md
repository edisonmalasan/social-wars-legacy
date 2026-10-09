# Proposal

## Why

The committed asset ID registry cannot resolve 50 of the 607 image references, and reports them
`ambiguous` because it matches on **basename**. Every one of those 50 references already carries
the directory that disambiguates it — `/goals/1.png` against `/packs/1.png`, `/chapters/chapter_1.jpg`
against `/chapters2/chapter_1.jpg` — and the rule discards exactly the component that settles the
question. The ambiguity is not cosmetic: **17 of the 25 candidate pairs are byte-differing**, so 34
of the 50 entries would ship visibly different art.

The committed investigation (`docs/legacy-image-reference-resolution.md`, PR #348) measured that
joining the reference's own path onto `assets/images/en` resolves **50 of 50** ambiguous entries to
a single existing file, agrees with today's answer on **523 of 523** entries where both rules work
(**zero** disagreements), and is a **perfect bijection onto the corpus** — **573** references to
**573** distinct files, in a directory holding exactly **573** files, with **zero** unreferenced.
Every image file is named by exactly one reference at exactly the path that reference spells out,
which is what distinguishes an authored rule from a fitted one.

Now: **no client code resolves image references today.** `/chapters/`, `/goals/` and `/packs/` appear
in **zero** client files, and `town.gd`'s three `images/en` hits are inside prose evidence strings.
So this is **not a live user-facing defect**. It is a known ambiguity removed *before* something
depends on it, and the change is deliberately scoped to the resolution mechanism rather than to any
renderer.

## What Changes

- **The image join becomes path-first with a recorded basename fallback.** The reference's own path
  under `assets/images/en` is tried first; only when that file does not exist does the existing
  basename match apply. Coverage gains a distinct tier recording which references needed the
  fallback, so the fallback is visible in committed evidence rather than invisible in behaviour.
- **`ambiguous` leaves the images vocabulary in practice, by resolution rather than by deletion.**
  The status stays in the closed vocabulary — it remains truthful for any future reference whose
  path and basename both fail to identify a file — but the committed registry records **0**
  ambiguous image entries.
- **The two genuinely mis-pathed references stay resolved and become attributable.**
  `/chapters/simple/arachnids_old.jpg` and `/chapters/simple/orcs_old.jpg` name a directory the
  corpus does not use: both files exist only under `chapters2/simple/`. They resolve today by
  basename and must keep resolving, but under the new rule they are recorded as **fallback-resolved**
  rather than silently passing as path-resolved.
- **No status is invented and no gap is closed.** All 32 `missing_source` references stay
  `missing_source`: a corpus-wide search under every extension finds each of them absent outright.
  **No resolver work can close them**, and this change does not pretend otherwise.
- **No image is rendered, decoded, converted, or displayed.** The line delivers resolution only.
- **The `item_sprites` population is untouched.** Its 10 `missing_source` entries are a different
  population under a different rule (`assets/sprites/<stem>.swf`), scoped out explicitly by the
  investigation rather than dropped silently.

### Measured target numbers

Committed today, projected under the new rule, all measured rather than assumed:

| quantity | today | projected |
| --- | --- | --- |
| images `resolved` (coverage.json) | 525 | **575** |
| images `basename_single` / tier equivalent | 525 | **573** |
| fallback-resolved tier (new) | 0 | **2** |
| images `basename_collision` | 50 | **0** |
| `asset_ids.json` images `ambiguous` | 50 | **0** |
| `asset_ids.json` images `passthrough` | 516 | **566** |
| `asset_ids.json` images `extracted` | 9 | 9 |
| `asset_ids.json` images `missing_source` | 32 | **32** |

The 50 reclassified entries split by the extension of their path-resolved target: **30 `.jpg`** and
**20 `.png`**, all runtime-readable, hence `passthrough`. Totals hold at **607** image references
and **1,627** registry entries.

### Count pins this line legitimately moves

These are recorded pins that the change's own verified behaviour invalidates, amended **in place**
with their new values and no change to any assertion's intent:

- `tools/asset-registry/tests/test_build_registry.py` — images `basename_single` / `basename_collision`.
- `tools/asset-registry/tests/test_build_asset_ids.py` — the same two figures plus per-status counts.
- `apps/client-godot/tests/test_asset_ids.gd` — `EXPECTED_STATUS["images"]`.

## Capabilities

### New Capabilities
- `image-reference-resolution`: the path-first image reference join with a recorded basename
  fallback, the three-tier outcome it produces, and the claim limits that keep it a resolution
  mechanism rather than a rendering or content-authoring change.

### Modified Capabilities
- `asset-registry`: the content cross-reference coverage requirement changes — the images join rule
  becomes path-first, a fallback tier is recorded, and the "Review measured joins" scenario's
  basename-tiering figures are restated.
- `godot-content-registry`: the deterministic asset ID registry requirement changes — the images rule
  string, the per-status reconciliation figures, and the "Map every reference" scenario, which
  currently names `ambiguous` among the expected image outcomes.

## Impact

- **Tools**: `tools/asset-registry/build_registry.py` (coverage tiering),
  `tools/asset-registry/build_asset_ids.py` (`RULES["images"]`, `image_candidates`,
  `build_kind_entries`). Both must move together — the ID registry reconciles against coverage's
  `basename_single`/`basename_collision` and exits 1 on a mismatch, so a one-sided change fails closed.
- **Committed generated output**: `tools/asset-registry/coverage.json` and
  `tools/asset-registry/asset_ids.json` are regenerated. Both are byte-deterministic on rerun.
- **Tests**: the three suites listed above, plus new cases pinning the fallback tier's exact two
  members, the 32 refusals, and the zero-disagreement property against the previous rule's answers.
- **Client**: **no client source changes.** `test_asset_ids.gd` moves three pinned numbers and
  nothing else.
- **Not guarded, but consequential**: `coverage.json` and `asset_ids.json` are outside the Compatibility
  API guard baseline, which covers `conversions.json`, `inspection.json` and `image_extraction.json`.
  `verify.ps1` does guard `asset_ids.json` for byte-identity **across** its own battery, which
  regeneration before the battery satisfies.
- **Untouched**: every preserved input, save, config, village and content byte; the normalized
  content package; the conversion and extraction manifests; the legacy server; the Compatibility API.
  No Flash, Ruffle, ActionScript or browser executes, and no network is used.