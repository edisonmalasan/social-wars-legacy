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
through extraction and conversion states; the registry and inspection
slices never change a status. Symbol names, dimensions, pivots, frame
counts, and conversion outputs belong to the SWF-parsing and conversion
slices, not here.

## SWF static inspection

`inspect_swf.py` parses every registry `.swf` file with static byte
reads (`struct` + `zlib` only) into `tools/asset-registry/inspection.json`:

- Headers: signature (`CWS` only in the measured corpus; `FWS`
  accepted, anything else fails closed), version (10/11/15/17),
  declared vs actual length (both recorded, declared never trusted),
  stage size, frame rate, frame count.
- Tag inventories with counts, merged across nested DefineSprite
  timelines (105,038 nested sprite tags corpus-wide, max nesting
  depth 1).
- SymbolClass/ExportAssets names verbatim, embedded bitmap IDs
  (61,702) and sound IDs (27), DoABC presence (1,175 files) and legacy
  action presence (0 files), frame labels, scene counts.
- Corpus statistics for conversion scoping: near-universal ABC
  presence means conversion tooling must assume scripted timelines by
  default; static-only art is the exception, not the rule.

See `tools/asset-registry/README.md` for invocation, parsing rules,
exit codes, evidence classification, and containment.

## Sound extraction

`extract_sounds.py` slices the 27 embedded MP3 payloads (all format
nibble 2, all in `assets/swf/dynamic2.swf`) verbatim from each tag's
first frame sync (uniform offset 9, asserted) into
`assets/converted/sounds/<id>.mp3`, with `extraction.json` provenance
and a `statuses.json` overlay advancing those registry paths to
`extracted`. No decoding, playback, transcoding, or source mutation;
MP3 stays MP3. Zero non-MP3 sounds exist corpus-wide; any future one
fails closed.

## Prioritization input (roadmap §14)

Suggested conversion order: terrain, one building, one unit, essential
HUD, selection indicators, placement grid, then common content. The
missing-name lists (`coverage.json` → `domains.*.missing`) identify
content at risk: referenced assets with no on-disk source must be
recreated rather than converted.
