## Why

Static inspection inventoried the corpus: 61,702 bitmap IDs across JPEG/lossless families versus exactly 27 embedded sounds, all MP3 (format 2) in a single file (`assets/swf/dynamic2.swf`). Bitmap extraction needs per-format writers (JPEG-table splicing, alpha separation, hand-rolled PNG encoding) — a large slice. Sound extraction is the smallest coherent extraction step: one format, one source file, verbatim payload slicing, and it fully closes the embedded-audio domain while proving the extract-to-`converted/` pipeline that bitmap slices will reuse.

## What Changes

- Add `tools/asset-registry/extract_sounds.py` (stdlib-only) that re-walks DefineSound tags in `assets/swf/dynamic2.swf` (paths from the committed inspection output, never hardcoded discovery), validates format nibble 2 (MP3) plus rate/size/type characteristics, slices sound payloads verbatim into `assets/converted/sounds/<id>.mp3`, and writes `tools/asset-registry/extraction.json` (per-sound source tag, characteristics, output digest, MP3 sync validation) plus a console/JSON report.
- Validate: MP3 frame-sync at payload start, characteristic sanity, output digests recomputed before manifesting, byte-identical reruns, and schema fields. Non-MP3 formats fail closed as drift.
- Advance the 27 involved registry entries' lifecycle state in a generated `statuses.json` overlay (`registered` → `extracted`); raw sources and `registry.json`/`coverage.json`/`inspection.json` stay untouched.
- Leave all source assets, registry outputs, content, and behavior unchanged; claim no transcoding (MP3 stays MP3 — Godot plays it natively), no timeline work, no Godot rendering.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| Embedded sounds | 27 DefineSound tags, all format nibble 2 (MP3), all in `assets/swf/dynamic2.swf` with character IDs 1..27 |
| Other formats | Zero non-MP3 DefineSound tags corpus-wide; any future one fails closed |
| Bitmap contrast | 46,425 JPEG3 + 14,364 lossless + 913 plain-JPEG tags remain for later slices; untouched here |
| Execution boundary | Tag-structure reads and byte slicing only; no decoding to samples, no playback, no Flash runtime |

## Capabilities

### New Capabilities

- `sound-extraction`: Verbatim MP3 payload extraction with characteristics validation, outputs manifest, and status overlay.

### Modified Capabilities

None.

## Impact

Adds `tools/asset-registry/extract_sounds.py` plus generated `extraction.json`/`statuses.json` and converted MP3s under `assets/converted/sounds/`, focused tests (synthetic DefineSound tags per format nibble plus the real file), schema, and docs links. Uses Python 3.9 standard-library tooling with no dependency upgrade, no server import, no network, no browser, no Flash execution or decoding, no raw-source mutation, and no Godot code. Bitmap extraction, timeline conversion, and converted buildings/units remain future M4 slices; Godot rendering verification belongs to M5/M6 and is not claimed here.
