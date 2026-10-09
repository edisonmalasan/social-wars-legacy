## Purpose

Provide one assembled converted-building package linking parsed shape records to extracted bitmaps so Godot import work can start from validated inputs without executing Flash.

## Requirements

### Requirement: Single-building package assembly
The tool SHALL assemble `assets/converted/buildings/<target-stem>/` for the **declared target stem**, with `package.json` (legacy_id, content definition ref, source provenance, frame data, symbols, shape bounds/style/bitmap-ref records, bitmap outputs with digests, placement tiles) plus byte-identical bitmap copies. The target stem SHALL be a required input; the tool SHALL NOT carry a default target. The content definition SHALL be resolved by `img_name` and SHALL fail closed unless exactly one normalized buildings entry matches. Bitmap digests SHALL match extraction outputs exactly, and every package field other than `content_version` SHALL be identical in shape and meaning to the package assembled for any other target.

#### Scenario: Assemble the measured house
- **WHEN** the converter runs on `0001_house_1_m` against the current corpus
- **THEN** the package directory holds a validated `package.json` plus the JPEG and alpha PNG with matching digests

#### Scenario: Assemble a different target
- **WHEN** the converter runs on any other declared target stem whose bitmaps are extracted and whose `img_name` resolves to exactly one normalized entry
- **THEN** it assembles the same package shape for that target, recording that target's own bounds, style records, bitmap links, provenance, and frame data
- **AND** it writes only that target's package directory and the manifests

#### Scenario: Require a target
- **WHEN** the converter is invoked without a target stem
- **THEN** it exits non-zero with a message naming the missing input
- **AND** it writes no package files, no manifest entry, and no status change

#### Scenario: Resolve the content reference
- **WHEN** the converter links the building definition
- **THEN** exactly one normalized buildings entry matches `img_name`, with tiles and costs recorded verbatim
- **AND** a stem matching zero or more than one entry fails closed

### Requirement: The package provenance digest is independent of the checkout's line endings
The tool SHALL compute the input fingerprint that becomes the package's `content_version` over **line-ending-normalised** bytes, so that the same committed content yields the same `content_version` on an LF checkout and a CRLF checkout alike. The tool SHALL NOT hash raw working-tree bytes of any input whose line endings are not pinned. This is the treatment `apps/compat-api/guard_baseline.py` already applies to its own digests.

#### Scenario: One digest across checkout forms
- **WHEN** the fingerprint is computed over inputs whose working-tree bytes contain CRLF
- **THEN** it equals the fingerprint computed over the same inputs with LF line endings

#### Scenario: The measured digest changes once, deliberately
- **WHEN** the fingerprint is first computed over normalised bytes
- **THEN** the recorded `content_version` changes from the previously committed raw-byte digest
- **AND** `conversions.json` records the new `package_sha256` for this package
- **AND** the compatibility guard baseline covering both conversion packages and the registry manifests is regenerated in the same change

### Requirement: Buildings outside the parsed subset are refused and the refusals are measured
The tool SHALL fail closed, with no writes, for a target whose shape records fall outside the parsed subset, and the refusal SHALL name the file and the offending record. The tool SHALL NOT relax, widen, or reinterpret the parsed subset to make a target convertible, and SHALL NOT skip an unresolvable fill, an unknown style, or an unsupported tag. The refusal classes observed across the candidate population SHALL be recorded as data by the census capability rather than suppressed.

#### Scenario: Refuse rather than guess
- **WHEN** a target's style bytes name a fill type outside the parsed subset
- **THEN** validation fails naming the file and the value, and no outputs are written
- **AND** the tool reports no partial package and no substituted default

#### Scenario: Keep each refusal class distinct
- **WHEN** refusals are tallied across the candidate population
- **THEN** each failing target is attributed to exactly one refusal class
- **AND** no target is attributed to more than one class

#### Scenario: A refusal class with no established cause is not treated as understood
- **WHEN** a refusal class dominates the population but its cause has not been established
- **THEN** it is recorded as unestablished with the measurements that disagree
- **AND** no fix is adopted for it on the strength of either measurement alone

### Requirement: Shape-style record parsing
The tool SHALL parse SHAPEWITHSTYLE bounds, fill/line style arrays with counts and types, bitmap-fill character IDs, and raw matrices, failing closed on other shape versions or unexpected layouts. Edge records SHALL be counted, never tessellated.

#### Scenario: Parse the measured shape
- **WHEN** the converter reads DefineShape id 2
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
