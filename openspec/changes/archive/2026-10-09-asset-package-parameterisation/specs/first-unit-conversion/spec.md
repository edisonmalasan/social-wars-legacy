# Spec Delta

## Purpose

Let the unit converter assemble a package for **any** declared target rather than one hard-wired
stem and id, and make the package's provenance digest independent of the checkout's line endings.
The unit converter already generalises across the whole candidate population; this requirement
makes that reachability an explicit, testable contract instead of an accident of the current
constants.

## MODIFIED Requirements

### Requirement: Single-unit package assembly

The tool SHALL assemble `assets/converted/units/<target-stem>/` for the **declared target stem and
its normalized content `legacy_id`**, both of which SHALL be required inputs; the tool SHALL NOT
carry a default target or id. It SHALL record `package.json` (legacy_id, normalized unit definition
ref, source provenance, frame data, symbols with export ids, per-sprite animation states, shape
bounds/style/bitmap-ref records, bitmap outputs with digests) plus byte-identical bitmap copies.
The definition SHALL be resolved by the pair (`legacy_id`, `img_name`) and SHALL fail closed unless
exactly one normalized units entry matches. Bitmap digests SHALL match extraction outputs exactly.

#### Scenario: Assemble the measured elephant

- **WHEN** the converter runs on `10033_wild_elephant` with content id `933` against the current
  corpus after the extraction builds
- **THEN** the package directory holds a validated `package.json` plus its JPEGs and alpha PNGs with
  matching digests, and frame data records 550×400 at 30.0 fps with 1 frame

#### Scenario: Assemble a different target

- **WHEN** the converter runs on any other declared target stem and content id whose bitmaps are
  extracted and whose pair resolves to exactly one normalized entry
- **THEN** it assembles the same package shape for that target, recording that target's own sprite
  timelines, labels, placements, shapes, provenance, and frame data
- **AND** it writes only that target's package directory and the manifests

#### Scenario: Require both inputs

- **WHEN** the converter is invoked without a target stem, or without its content id
- **THEN** it exits non-zero with a message naming the missing input
- **AND** it writes no package files, no manifest entry, and no status change

#### Scenario: Resolve the content reference

- **WHEN** the converter links the unit definition
- **THEN** exactly one normalized units entry matches the declared `legacy_id` and `img_name`,
  recorded verbatim with no other definition touched
- **AND** a pair matching zero or more than one entry fails closed

## ADDED Requirements

### Requirement: The unit package provenance digest is independent of the checkout's line endings

The tool SHALL compute the input fingerprint that becomes the package's `content_version` over
**line-ending-normalised** bytes, so that the same committed content yields the same
`content_version` on an LF checkout and a CRLF checkout alike. The tool SHALL NOT hash raw
working-tree bytes of any input whose line endings are not pinned.

#### Scenario: One digest across checkout forms

- **WHEN** the fingerprint is computed over inputs whose working-tree bytes contain CRLF
- **THEN** it equals the fingerprint computed over the same inputs with LF line endings

#### Scenario: The manifest is regenerated with the digest

- **WHEN** the fingerprint is first computed over normalised bytes
- **THEN** the recorded `content_version` changes from the previously committed raw-byte digest
- **AND** `conversions.json` records the new `package_sha256` for this package
- **AND** the other converter's foreign package entry and input keys are preserved verbatim

### Requirement: The placeholder rule is scoped to the unit converter's own subset and is not widened

The unit converter's recorded-placeholder handling for an **unreferenced** `bitmap_id 65535` fill,
and its refusal of a **referenced** one, SHALL remain exactly as specified. The tool SHALL NOT
extend that rule to the building converter, SHALL NOT relax it for units, and SHALL NOT treat a
`65535` fill as resolvable. Whether the building converter's population requires the same rule is
**not** established, and this capability asserts nothing about it.

#### Scenario: Keep the unit rule exact

- **WHEN** a unit shape records an unreferenced `65535` fill
- **THEN** the fill is recorded verbatim and the conversion proceeds
- **AND** a shape record that references a `65535` fill still fails closed with no writes

#### Scenario: Do not port the rule on inference

- **WHEN** the building converter's refusals are measured
- **THEN** this capability's unit rule is not cited as the explanation for any of them
- **AND** a change to the building converter's fill handling requires its own established cause