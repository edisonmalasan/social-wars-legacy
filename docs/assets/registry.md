# Asset registry (M4 foundation)

The validated on-disk asset registry lives in `tools/asset-registry/`:

- `build_registry.py` — stdlib-only offline builder/validator.
- `registry.json` — generated corpus registry (path, size, sha256 of
  worktree bytes, extension, directory class, status).
- `coverage.json` — generated join of normalized content references
  against the registry, with missing-name lists and unreferenced
  counts for conversion prioritization.
- `schemas/` — registry, entry, and coverage contracts.
- `tests/test_build_registry.py` — focused suite (synthetic fixtures
  plus read-only real-tree joins).

See `tools/asset-registry/README.md` for invocation, rules, exit
codes, evidence classification, and containment.

Measured coverage (verified by the suite against the current tree):

- SWF corpus 1176 files (sprites 862, fx 205, flash 60,
  characters_2 26, magic 10, images 9, fonts 2, swf 1,
  externalized 1); jpg 1756, png 143, mp3 140.
- Item sprites 907/917 refs resolve; 10 missing names listed in
  coverage (patch-era units and unmapped decorations).
- Magic sprites 10/10; sounds 139/139 refs.
- Images basename tiers: 525 single, 50 collisions, 32 missing.

## Worktree vs baseline distinction

Registry hashes identify current worktree bytes. Immutable baseline
Git-blob identity remains owned by `legacy-manifest.json` (3,258
blobs at the `legacy-baseline` commit). The two must not be confused:
the registry observes the mutable tree for conversion planning; the
manifest preserves the immutable baseline for integrity.

## Status lifecycle

Every entry starts at `registered`. Later M4 slices advance entries
through extraction and conversion states; this slice never changes a
status. Symbol names, dimensions, pivots, frame counts, and conversion
outputs belong to the SWF-parsing and conversion slices, not here.

## Prioritization input (roadmap §14)

Suggested conversion order: terrain, one building, one unit, essential
HUD, selection indicators, placement grid, then common content. The
missing-name lists (`coverage.json` → `domains.*.missing`) identify
content at risk: referenced assets with no on-disk source must be
recreated rather than converted.
