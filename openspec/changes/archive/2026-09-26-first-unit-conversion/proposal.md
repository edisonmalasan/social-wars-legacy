## Why

The building slice proved package assembly for static single-frame art. The M4 exit needs a unit too, and units are sprite-library SWFs: `10033_wild_elephant` (unit 933) holds 7 sprite timelines with 5 Spanish animation labels (QUIETO/ANDAR/ATAQUE/MUERTE/PICAR), 28 shapes, and 28 bitmaps, all in a single 550×400 @ 30 fps frame. Converting it exercises per-sprite animation inventory (label → sprite → frames/shapes/bitmaps) — the exact structure M6 unit idle/walk/attack rendering will consume — while staying the smallest animation set in the corpus.

## What Changes

- Add `tools/asset-registry/convert_unit.py` (stdlib-only, reusing the building converter's shape parser by local import, not duplication) that assembles `assets/converted/units/10033_wild_elephant/` with `package.json` (legacy_id, normalized unit definition ref, source provenance, frame data, symbols, per-sprite animation states with labels/frames/shapes/bitmap refs, bitmap outputs with digests) plus byte-identical bitmap copies, and merges a package entry into `conversions.json` plus a `converted` statuses entry.
- Record per-sprite timelines (sprite id, frame count, frame labels, shape bounds/style/bitmap-ref records, edge counts) with the same no-tessellation boundary; label semantics (idle vs attack behavior) are recorded as names only, never interpreted.
- Validate: animation-state coverage (every sprite and label inventoried, declared frame counts matching observed ones, character references resolving), bitmap-fill resolution with the recorded placeholder policy, content-ref uniqueness (unit 933), schema fields, and byte-identical reruns. Claim no animation playback, no visual correctness, no Godot involvement.
- Byte-align the shared style parser after the FillStyleArray (the elephant's bitmap fills end mid-byte, so the current byte-strict read fails on 19 of 28 shapes; the house's single fill is already aligned) and re-verify the house package regenerates byte-identically.
- Migrate `conversions.json` to a neutral `conversion-v1` envelope whose package entries each carry their own `policy` and byte count, with both converters merging and preserving foreign entries so reruns are order-independent (today `convert_building.py` rewrites the manifest with only its own entry).
- Leave all sources, registry outputs, content, and behavior unchanged; touch no other definition.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| Source file | `assets/sprites/10033_wild_elephant.swf` (CWS, 550×400 @ 30 fps, 1 main frame, 7 sprites, 28 bitmaps, 28 shapes, ABC present) |
| Animation labels | All five are `FrameLabel` tags inside `DefineSprite` id 63 (29 frames: QUIETO f1, ANDAR f6, ATAQUE f11, MUERTE f16, PICAR f21); no other sprite and not the root carries labels (Spanish state names, carried as names only) |
| Timeline structure | Root places sprite 63 (SymbolClass `10033_wild_elephant`) at depth 1 on frame 1; all 40 `PlaceObject2` placements are at depth 1; sprite 63 places shapes 2/4/6/8/10 and sprites 19/28/37/46/55/62; sprite 63 also holds all 7 `RemoveObject2`; ATAQUE and PICAR are label-only segments with no placements |
| Declared frames | Sprites 19/28/37/46/55 = 20 frames, sprite 62 = 7, sprite 63 = 29; each declared count equals the observed `ShowFrame` count |
| Bitmap linkage | 25 of 28 shapes carry an unreferenced `bitmap_id 65535` placeholder fill; the 28 referenced fills map one-to-one onto the 28 extracted JPEG3 outputs (28 shapes ↔ 28 bitmaps) |
| Shared parser gap | The byte-strict style-array read fails on 19 of 28 elephant shapes (fill arrays end mid-byte); `0001_house_1_m` is unaffected (its single fill already ends aligned) |
| Content ref | Normalized `units.json` entry legacy_id `933` (429 entries) is the sole `img_name` match for `10033_wild_elephant` |
| Execution boundary | Tag-structure reads and record parsing only; no playback, no tessellation, no Flash runtime |

## Capabilities

### New Capabilities

- `first-unit-conversion`: Single-unit converted package assembly with per-sprite animation inventory and conversion manifest entry.

### Modified Capabilities

None.

## Impact

Adds `tools/asset-registry/convert_unit.py` plus generated package outputs, a conversions merge that also requires `conversions.json` envelope migration (schema constant, merge/preserve semantics in `convert_building.py`, regenerated manifest), a shared style-array alignment fix with house byte-identical re-verification, statuses merge, focused tests (synthetic sprite timelines plus the real elephant file), a unit package schema, and docs links. Uses Python 3.9 standard-library tooling with no dependency upgrade, no server import, no network, no browser, no Flash execution, no raw-source mutation, and no Godot code. Remaining units, timeline assembly for playback, and any rendering verification stay future work (M5/M6 own Godot verification).
