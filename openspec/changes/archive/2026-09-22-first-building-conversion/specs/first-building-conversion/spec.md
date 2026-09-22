## Purpose

Provide one assembled converted-building package linking parsed shape records to extracted bitmaps so Godot import work can start from validated inputs without executing Flash.

## ADDED Requirements

### Requirement: Single-building package assembly
The tool SHALL assemble `assets/converted/buildings/0001_house_1_m/` with `package.json` (legacy_id, content definition ref, source provenance, frame data, symbols, shape bounds/style/bitmap-ref records, bitmap outputs with digests, placement tiles) plus byte-identical bitmap copies. Bitmap digests SHALL match extraction outputs exactly.

#### Scenario: Assemble the measured house
- **WHEN** the converter runs on the current corpus
- **THEN** the package directory holds a validated `package.json` plus the JPEG and alpha PNG with matching digests, and reruns are byte-identical

#### Scenario: Resolve the content reference
- **WHEN** the converter links the building definition
- **THEN** exactly one normalized buildings entry matches `img_name`, with tiles and costs recorded verbatim

### Requirement: Shape-style record parsing
The tool SHALL parse SHAPEWITHSTYLE bounds, fill/line style arrays with counts and types, bitmap-fill character IDs, and raw matrices, failing closed on other shape versions or unexpected layouts. Edge records SHALL be counted, never tessellated.

#### Scenario: Parse the measured shape
- **WHEN** the converter reads DefineShape2 id 2
- **THEN** bounds, one `0x41` bitmap fill referencing id 1, and line styles are recorded with the matrix preserved as raw bytes

#### Scenario: Reject an unexpected shape
- **WHEN** a shape version or style layout falls outside the parsed subset
- **THEN** validation fails identifying the file and tag without writing outputs

### Requirement: Validation and conversion manifest
The tool SHALL validate bounds presence, bitmap-fill resolution, content-ref uniqueness, schema fields, and determinism, and SHALL write `conversions.json` plus a `converted` statuses merge. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing outputs only on success.

#### Scenario: Detect an unresolvable bitmap fill
- **WHEN** a bitmap-fill ID has no extracted output
- **THEN** validation fails identifying the shape without writing outputs

#### Scenario: Prove outputs match inputs
- **WHEN** package outputs are re-derived in memory
- **THEN** records, copies, digests, and counts are recomputed equal before any write

### Requirement: Preservation-safe conversion tooling
The tool SHALL NOT tessellate, rasterize, interpret matrices or scripts, relocate, or modify any source asset; SHALL NOT use Flash, browser, network, server, or subprocess execution; and SHALL write only the package directory plus manifests on success. Registry, coverage, inspection, and extraction manifests SHALL remain untouched.

#### Scenario: Convert without source side effects
- **WHEN** the converter succeeds or fails
- **THEN** every source asset and prior manifest remains byte-identical and only package outputs plus manifests are created or replaced
