## Purpose

Provide format-faithful bitmap payload extraction to standard JPG/PNG files so embedded game art exists as convertible inputs without rendering or Flash involvement.

## Requirements

### Requirement: Family-faithful bitmap extraction
The tool SHALL re-walk bitmap tags in every inspected SWF and SHALL write per-bitmap outputs under `assets/converted/images/<swf-stem>/`: verbatim `.jpg` (with JPEGTables splice only when SOI is absent), `_alpha.png` grayscale from dimension-matched decoded alpha, and `.png` RGBA from lossless ARGB/colormap via the hand-rolled encoder. Unknown bitmap formats SHALL fail closed.

#### Scenario: Extract the measured families
- **WHEN** the extractor runs on the current corpus
- **THEN** all JPEG, JPEG3-plus-alpha, ARGB, and colormap payloads convert with per-output digests, and reruns are byte-identical

#### Scenario: Reject an unknown format
- **WHEN** a lossless tag carries a bitmap format outside {3, 5}
- **THEN** validation fails identifying the file and tag without writing outputs

### Requirement: Extraction manifest and status overlay
The tool SHALL write `image_extraction.json` with per-bitmap source tag, family, format, dimensions, output digests, and byte counts, and SHALL merge new `extracted` entries into `statuses.json`. Registry, coverage, and inspection outputs SHALL remain untouched.

#### Scenario: Review extraction provenance
- **WHEN** a maintainer reads the extraction manifest
- **THEN** every output byte is traced to its source tag with a matching digest

#### Scenario: Regenerate bulk outputs
- **WHEN** converted images are deleted and the extractor reruns
- **THEN** outputs regenerate byte-identical to the committed manifest digests

### Requirement: Validation and round-trip evidence
The tool SHALL validate payload structure, zlib integrity, alpha dimension match, PNG re-parse (signature plus IHDR), JPEG SOI presence, schema fields, and determinism. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing outputs only on success.

#### Scenario: Detect an alpha dimension mismatch
- **WHEN** a decoded alpha length differs from width-times-height
- **THEN** validation fails identifying the bitmap without writing outputs

#### Scenario: Prove outputs match inputs
- **WHEN** extraction outputs are re-derived in memory
- **THEN** payload slices, PNG encodings, digests, and counts are recomputed equal before any write

### Requirement: Preservation-safe extraction tooling
The tool SHALL NOT render, decode JPEG to pixels, play back, transcode JPEG data, convert vectors, relocate, or modify any source asset; SHALL NOT use Flash, browser, network, server, or subprocess execution; and SHALL write bulk outputs only under the ignored `assets/converted/images/` plus the committed manifest and statuses merge. Raw sources stay byte-identical.

#### Scenario: Extract without source side effects
- **WHEN** the extractor succeeds or fails
- **THEN** every source asset remains byte-identical and only converted outputs plus manifests are created or replaced
