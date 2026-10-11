# first-unit-conversion — delta

## MODIFIED Requirements

### Requirement: Single-unit package assembly

The tool SHALL assemble `assets/converted/units/<target-stem>/` for the **declared target stem and
its normalized content `legacy_id`**, both of which SHALL be required inputs; the tool SHALL NOT
carry a default target or id. It SHALL record `package.json` (legacy_id, normalized unit definition
ref, source provenance, frame data, symbols with export ids, per-sprite animation states, shape
bounds/style/bitmap-ref records, bitmap references with digests). The definition SHALL be resolved
by the pair (`legacy_id`, `img_name`) and SHALL fail closed unless exactly one normalized units entry
matches. Bitmap digests SHALL match extraction outputs exactly.

**A package SHALL reference its bitmaps rather than copy them.** Each bitmap entry SHALL record the
extraction output path under the shared extracted image tree, together with its byte count and
SHA-256, and the package directory SHALL contain no copied bitmap bytes. The referenced path SHALL
be resolved and its bytes SHALL be hashed during conversion, and a digest mismatch SHALL fail
validation before any output is written.

#### Scenario: Assemble the measured elephant

- **WHEN** the converter runs on `10033_wild_elephant` with content id `933` against the current corpus after the extraction builds
- **THEN** the package directory holds a validated `package.json` whose bitmap entries name the shared extracted image tree with matching digests and records no copied bitmap bytes, and frame data records 550×400 at 30.0 fps with 1 frame

#### Scenario: Assemble a different target

- **WHEN** the converter runs on any other declared target stem and content id whose bitmaps are extracted and whose pair resolves to exactly one normalized entry
- **THEN** it assembles the same package shape for that target, recording that target's own sprite timelines, labels, placements, shapes, provenance, and frame data
- **AND** it writes only that target's package directory and the manifests

#### Scenario: Require both inputs

- **WHEN** the converter is invoked without a target stem, or without its content id
- **THEN** it exits non-zero with a message naming the missing input
- **AND** it writes no package files, no manifest entry, and no status change

#### Scenario: Resolve the content reference

- **WHEN** the converter links the unit definition
- **THEN** exactly one normalized units entry matches the declared `legacy_id` and `img_name`, recorded verbatim with no other definition touched
- **AND** a pair matching zero or more than one entry fails closed

#### Scenario: A referenced bitmap is checked, not merely recorded

- **WHEN** a referenced extraction path is missing, or its bytes do not hash to the recorded
  SHA-256
- **THEN** validation fails identifying the bitmap, and no output is written

### Requirement: Neutral conversion manifest with merge

The tool SHALL write `conversions.json` as a neutral `conversion-v1` envelope whose package entries
each carry their own `policy` and byte count, with `counts` recomputed from the entries and `inputs`
keys merged per domain; each converter SHALL preserve foreign package entries and input keys
verbatim, replace only its own entry, stamp the envelope policy, and produce byte-identical output
regardless of which converter ran last. The building converter SHALL accept a legacy
`building-conversion-v1` envelope only while its sole entry is the building's own, and the unit
converter SHALL reject a non-`conversion-v1` envelope.

**A package entry's `output_bytes` SHALL be its `package.json` byte total.** Packages reference
rather than copy their bitmaps, so no copied bitmap bytes exist to add.

#### Scenario: Record both packages order-independently

- **WHEN** the building and unit converters run in either order
- **THEN** `conversions.json` ends with both package entries, envelope policy `conversion-v1`, correct per-entry policies, and counts equal regardless of run order, with each package's `package_sha256` unchanged

#### Scenario: Migrate the committed legacy envelope

- **WHEN** the building converter runs against the legacy manifest (or the unit converter runs against it)
- **THEN** the building converter rewrites it as `conversion-v1` with its fresh entry, while the unit converter fails closed with a clear message and no writes until the migration has run

#### Scenario: The recorded byte total means what it says

- **WHEN** a package entry's `output_bytes` is recorded
- **THEN** the value equals that package's `package.json` byte length
- **AND** no schema documentation describes it as including copied bitmap bytes

### Requirement: Validation and manifest-grade determinism

The tool SHALL validate animation-state coverage, bitmap-fill resolution, content-ref uniqueness,
schema fields, and determinism, and SHALL write the `conversions.json` merge plus a `converted`
statuses merge only on success. It SHALL report success with exit 0 and any validation failure with a
non-zero exit.

**Determinism SHALL be demonstrated over three consecutive runs**, not two, because these artefacts
are compared byte-for-byte across checkout forms by the census and conversion replay checks.

#### Scenario: Prove outputs match inputs

- **WHEN** the converter runs three consecutive times against unchanged inputs
- **THEN** the package directory, `conversions.json`, and statuses output are byte-identical across all three, and the digests recorded in `package.json` equal recomputed ones

#### Scenario: Fail closed without partial writes

- **WHEN** any validation check fails
- **THEN** the converter exits non-zero, writes no package files, manifest entries, or status changes, and leaves prior outputs byte-identical