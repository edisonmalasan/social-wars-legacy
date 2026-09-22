## Why

Sound extraction closed the audio domain (27 MP3s). The remaining embedded domain is bitmaps: 46,425 JPEG3 + 14,364 lossless + 913 plain-JPEG tags (~525 MB payloads) whose subformats are now fully characterized. This slice builds the image extraction pipeline — the prerequisite for first-building conversion — with one format-faithful rule per family. Bulk outputs are regenerated build artifacts (ignored); the committed manifest with digests is the permanent evidence.

## What Changes

- Add `tools/asset-registry/extract_images.py` (stdlib-only) that re-walks bitmap tags in every inspected SWF, converts per family, and writes outputs under `assets/converted/images/<swf-stem>/` plus `tools/asset-registry/image_extraction.json` (per-bitmap provenance, format, dimensions, digests) and merges new `extracted` entries into `statuses.json`.
- Conversion rules: DefineBits/DefineBitsJPEG2 (6/21) → verbatim `.jpg`, splicing JPEGTables only when the payload lacks its own SOI (never observed; implemented and synthetically tested); DefineBitsJPEG3 (35) → verbatim `.jpg` plus zlib-decoded alpha channel as grayscale `_alpha.png` (decoded length must equal width×height); DefineBitsLossless/Lossless2 formats 5 (32-bit ARGB) and 3 (colormapped, expanded to RGBA) → `.png` via a hand-rolled stdlib encoder (signature, IHDR, filter-0 IDAT, IEND with CRCs). Any other bitmap format fails closed as drift.
- Validate: payload structure, zlib integrity, alpha dimension match, PNG re-parse (signature + IHDR dimensions), JPEG SOI presence, schema fields, determinism. Report format distribution and converted byte totals.
- Advance `statuses.json` for files with extracted bitmaps; raw sources and registry/coverage/inspection outputs stay untouched. Claim no timeline work, no Godot rendering.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| Bitmap tags | 35: 46,425; 36/20: 14,364 (format 5 all but 118 format-3 colormap); 6/21: 913; JPEGTables tag in 63 files |
| JPEG self-containment | All 47,338 JPEG payloads start with `FFD8`; splice path implemented but never triggered on real corpus |
| Alpha channels | All JPEG3 alpha blobs zlib-decode cleanly (0 failures); widths×heights verifiable per tag |
| Outputs volume | ~525 MB payloads → ignored `assets/converted/images/` (committing 61k binaries is rejected); manifest with digests is the committed evidence |
| Execution boundary | Tag-structure reads, zlib decompression, and byte re-encoding only; no rendering, no Flash runtime |

## Capabilities

### New Capabilities

- `bitmap-extraction`: Format-faithful bitmap payload extraction to JPG/PNG with validation manifest and status overlay.

### Modified Capabilities

None.

## Impact

Adds `tools/asset-registry/extract_images.py` plus generated `image_extraction.json`, statuses merge, ignored bulk outputs, focused tests (synthetic payloads per format/failure plus real spot checks with PNG/JPG re-parse), schema, and docs links. Uses Python 3.9 standard-library tooling with no dependency upgrade, no server import, no network, no browser, no Flash execution or decoding-to-screen, no raw-source mutation, and no Godot code. Timeline/shape conversion and converted buildings/units remain future M4 slices; Godot rendering verification belongs to M5/M6 and is not claimed here.
