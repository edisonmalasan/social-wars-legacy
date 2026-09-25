## Context

The building converter assembles static packages from top-level shapes; units need per-sprite animation inventory because their art lives in nested labeled timelines. Direct reads show the elephant file is the smallest such library (7 sprites, 5 labels, 28 bitmaps/shapes). This design scopes the sixth M4 slice: one unit, inventoried per sprite, playback deferred. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Converted package `assets/converted/units/10033_wild_elephant/` with `package.json` (identity, unit definition ref, provenance, frame data, symbols, per-sprite animation states, bitmap outputs with digests) plus bitmap copies.
- Stdlib-only per-sprite inventory reusing the building shape parser by local sibling import (no code duplication), with the same no-tessellation boundary.
- `conversions.json` package entry plus `converted` statuses merge; bitmap-fill resolution and content-ref uniqueness enforced.
- Focused tests on synthetic sprite timelines and the real file, plus determinism and containment.

**Non-Goals:**
- No animation playback, blending, or state-machine interpretation; labels are names only.
- No edge tessellation, rasterization, matrix/script interpretation.
- No remaining units (separate future slices driven by M6 needs).
- No registry/coverage/inspection/extraction-manifest mutation.
- No Godot code or rendering verification of any kind.
- No claim of M4 exit; render verification belongs to M5/M6.

## Decisions

- **Reuse by import, not duplication.** `convert_unit.py` inserts its own directory on `sys.path` and imports the building converter's bit-reader, style parser, record counter, schema validator, and digest helpers. Rationale: one parsing implementation; alternative duplication rejected as drift risk. Containment tests allow local sibling imports (only third-party/network/Flash modules are forbidden).
- **Sprites are animation states.** Each DefineSprite becomes an animation entry (sprite id, frame count, its own labels/shapes/bitmap refs); top-level shapes (if any) become a `base` entry. Label-to-sprite attribution comes from parsing, never from filename heuristics.
- **Package by directory, manifest globally.** Same layout as buildings under `assets/converted/units/`; `conversions.json` gains a second package entry with its own policy preserved (`building-conversion-v1` stays the manifest policy? No — manifest policy must cover both). Decision: `conversions.json` keeps one policy per generating tool run... Simpler: conversions manifest policy becomes `conversion-v1` neutral envelope holding package entries each with their own `policy` field. The building slice wrote `building-conversion-v1`; this slice migrates the envelope neutrally (small retroactive consistency fix, documented).
- **Small domain module.** New converter beside the registry tools sharing the schemas/tests/README pattern; no new dependencies.

## Risks / Trade-offs

- [Sibling import coupling] → Unit tool depends on building tool internals; changes to shared parsers must keep both suites green (both run in verification).
- [Label attribution] → Labels inside nested sprites attribute to those sprites; file-level merged label lists (inspection style) are not used for attribution.
- [Manifest policy migration] → The committed `conversions.json` envelope changes once, documented here and re-verified; per-package entries keep their tool policies.
- [Schema/validator drift] → Tests assert every required package field has a validator check.

## Migration Plan

Not applicable: new additive tooling plus generated package; envelope migration is a small documented format change with both tools updated; no legacy migration, no rollout, no rollback beyond reverting the new files.
