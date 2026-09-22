## Why

M4 slices 1–4 built the pipeline (registry, inspection, sound and bitmap extraction) but no assembled converted asset yet. The M4 exit demands one converted building and unit (rendering verified later in M5/M6). The smallest coherent conversion step assembles exactly one building package — `0001_house_1_m` (1 JPEG3 bitmap, 1 frame, 2 sprites, 1 shape, ABC present) — from already-extracted bitmaps plus newly parsed shape-style records (bounds, fill/line style arrays, bitmap-fill references). Full edge tessellation and the unit counterpart stay separate slices.

## What Changes

- Add `tools/asset-registry/convert_building.py` (stdlib-only) that assembles `assets/converted/buildings/0001_house_1_m/` containing `package.json` (legacy_id, normalized content definition ref, source SWF with digest, frame size/rate/count, symbols, shape records with bounds/style types/bitmap refs, bitmap outputs with dims and digests, placement metadata from content width/height tiles) plus byte-copies of (or references to) the extracted bitmap outputs, and merges a `conversions.json` manifest plus `converted` status entries into `statuses.json`.
- Parse SHAPEWITHSTYLE records (bounds RECT, fill/line style arrays with counts and types, bitmap-fill character IDs, matrices recorded as raw bytes) without edge-record tessellation; any other shape version or unexpected style layout fails closed with the file and tag identified.
- Validate: shape bounds present, every bitmap-fill reference resolves to an extracted bitmap output, content definition ref resolves to the normalized buildings package, package schema fields, and byte-identical reruns. Claim no rendering, no visual correctness, no gameplay footprint semantics beyond recording content tile values.
- Leave all sources, registry outputs, content, and behavior unchanged; claim no Godot loading or rendering (M5/M6 own verification).

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| Source file | `assets/sprites/0001_house_1_m.swf` (9,484 B, CWS v10, 1 frame @24fps, 2 sprites, ABC present) |
| Shapes | One top-level DefineShape2 (id 2, 40 B): bounds RECT nbits 14, 1 fill of type `0x41` referencing bitmap id 1 (the extracted JPEG3), matrix follows; line styles to be inventoried by the builder |
| Bitmap | Character id 1 → extracted `.jpg` plus `_alpha.png` with manifest digests |
| Content ref | Normalized `buildings.json` entry with `img_name` `0001_house_1_m` carries placement tiles and costs (recorded, never rebalanced) |
| Execution boundary | Tag-structure reads and record parsing only; no tessellation, no rasterization, no Flash runtime |

## Capabilities

### New Capabilities

- `first-building-conversion`: Single-building converted package assembly with shape-style parsing, bitmap linkage, and conversion manifest.

### Modified Capabilities

None.

## Impact

Adds `tools/asset-registry/convert_building.py` plus generated package outputs, `conversions.json`, statuses merge, focused tests (synthetic shape records per style type plus the real house file), schema, and docs links. Uses Python 3.9 standard-library tooling with no dependency upgrade, no server import, no network, no browser, no Flash execution, no raw-source mutation, and no Godot code. Edge tessellation, unit conversion, and any rendering verification remain future work (M5/M6 own Godot verification).
