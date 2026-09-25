## Why

The building slice proved package assembly for static single-frame art. The M4 exit needs a unit too, and units are sprite-library SWFs: `10033_wild_elephant` (unit 933) holds 7 nested sprites with 5 Spanish animation labels (QUIETO/ANDAR/ATAQUE/MUERTE/PICAR), 28 bitmaps, and 28 shapes in one frame. Converting it exercises per-sprite animation inventory (label → sprite → frames/shapes/bitmaps) — the exact structure M6 unit idle/walk/attack rendering will consume — while staying the smallest animation set in the corpus.

## What Changes

- Add `tools/asset-registry/convert_unit.py` (stdlib-only, reusing the building converter's shape parser by local import, not duplication) that assembles `assets/converted/units/10033_wild_elephant/` with `package.json` (legacy_id, normalized unit definition ref, source provenance, frame data, symbols, per-sprite animation states with labels/frames/shapes/bitmap refs, bitmap outputs with digests) plus byte-identical bitmap copies, and merges a package entry into `conversions.json` plus a `converted` statuses entry.
- Record per-sprite timelines (sprite id, frame count, frame labels, shape bounds/style/bitmap-ref records, edge counts) with the same no-tessellation boundary; label semantics (idle vs attack behavior) are recorded as names only, never interpreted.
- Validate: animation-state coverage (every labeled sprite inventoried), bitmap-fill resolution, content-ref uniqueness (unit 933), schema fields, and byte-identical reruns. Claim no animation playback, no visual correctness, no Godot involvement.
- Leave all sources, registry outputs, content, and behavior unchanged; touch no other definition.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| Source file | `assets/sprites/10033_wild_elephant.swf` (CWS, 1 main frame, 7 sprites, 28 bitmaps, 28 shapes, ABC present) |
| Animation labels | QUIETO, ANDAR, ATAQUE, MUERTE, PICAR recorded across nested sprites (Spanish state names, carried as names only) |
| Content ref | Normalized `units.json` entry legacy_id `933` is the sole `img_name` match for `10033_wild_elephant` |
| Execution boundary | Tag-structure reads and record parsing only; no playback, no tessellation, no Flash runtime |

## Capabilities

### New Capabilities

- `first-unit-conversion`: Single-unit converted package assembly with per-sprite animation inventory and conversion manifest entry.

### Modified Capabilities

None.

## Impact

Adds `tools/asset-registry/convert_unit.py` plus generated package outputs, conversions merge, statuses merge, focused tests (synthetic sprite timelines plus the real elephant file), schema, and docs links. Uses Python 3.9 standard-library tooling with no dependency upgrade, no server import, no network, no browser, no Flash execution, no raw-source mutation, and no Godot code. Remaining units, timeline assembly for playback, and any rendering verification stay future work (M5/M6 own Godot verification).
