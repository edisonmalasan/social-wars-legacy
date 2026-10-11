# first-building-conversion — delta

## MODIFIED Requirements

### Requirement: Single-building package assembly

The tool SHALL assemble `assets/converted/buildings/<target-stem>/` for the **declared target
stem**, with `package.json` (legacy_id, content definition ref, source provenance, frame data,
symbols, shape bounds/style/bitmap-ref records, bitmap references with digests, placement tiles).
The target stem SHALL be a required input; the tool SHALL NOT carry a default target. The content
definition SHALL be resolved by `img_name` and SHALL fail closed unless exactly one normalized
buildings entry matches. Bitmap digests SHALL match extraction outputs exactly, and every package
field other than `content_version` SHALL be identical in shape and meaning to the package assembled
for any other target.

**A package SHALL reference its bitmaps rather than copy them.** Each bitmap entry SHALL record the
extraction output path under the shared extracted image tree, together with its byte count and
SHA-256, and the package directory SHALL contain no copied bitmap bytes. The referenced path SHALL
be resolved and its bytes SHALL be hashed during conversion, and a digest mismatch SHALL fail
validation before any output is written. Converting a bitmap reference SHALL NOT depend on a prior
copy existing in the package directory.

#### Scenario: Assemble the measured house

- **WHEN** the converter runs on `0001_house_1_m` against the current corpus
- **THEN** the package directory holds a validated `package.json` whose bitmap entries name the
  shared extracted image tree with matching digests
- **AND** the package directory holds no copied bitmap bytes

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

#### Scenario: A referenced bitmap is checked, not merely recorded

- **WHEN** a referenced extraction path is missing, or its bytes do not hash to the recorded
  SHA-256
- **THEN** validation fails identifying the bitmap, and no output is written

### Requirement: Validation and conversion manifest

The tool SHALL validate bounds presence, bitmap-fill resolution, content-ref uniqueness, schema
fields, and determinism, and SHALL write `conversions.json` plus a `converted` statuses merge. It
SHALL report success with exit 0 and any validation failure with a non-zero exit, writing outputs
only on success.

**`output_bytes` SHALL be the package.json byte total.** Because a package references its bitmaps
rather than copying them, no copied bitmap bytes exist to add; the field SHALL NOT be documented as
including them.

#### Scenario: Detect an unresolvable bitmap fill

- **WHEN** a bitmap-fill ID has no extracted output
- **THEN** validation fails identifying the shape without writing outputs

#### Scenario: Prove outputs match inputs

- **WHEN** package outputs are re-derived in memory
- **THEN** records, references, digests, and counts are recomputed equal before any write

#### Scenario: The recorded byte total means what it says

- **WHEN** `conversions.json` records a package's `output_bytes`
- **THEN** the value equals that package's `package.json` byte length
- **AND** no documentation describes it as including copied bitmap bytes

### Requirement: Preservation-safe conversion tooling

The tool SHALL NOT tessellate, rasterize, interpret matrices or scripts, relocate, or modify any
source asset; SHALL NOT use Flash, browser, network, server, or subprocess execution; and SHALL
write only the package directory plus manifests on success. Registry, coverage, inspection, and
extraction manifests SHALL remain untouched.

**The tool SHALL NOT regenerate or modify the preservation manifest.** The preservation manifest is
built from the Git tree of a single pinned commit, so files added by later commits cannot enter it;
a conversion run that rewrote it would be asserting a change that cannot occur.

#### Scenario: Convert without source side effects

- **WHEN** the converter succeeds or fails
- **THEN** every source asset and prior manifest remains byte-identical and only package outputs plus manifests are created or replaced

#### Scenario: The preservation manifest does not move

- **WHEN** conversion succeeds and packages are committed
- **THEN** the preservation manifest still verifies at its original entry count and byte total