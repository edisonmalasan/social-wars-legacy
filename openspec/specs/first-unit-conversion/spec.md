## Purpose

Provide one assembled converted-unit package that inventories each sprite timeline (labels, frames, placements, shapes, bitmap links) for the smallest unit library so Godot import and M6 unit rendering work can start from validated inputs without executing Flash.

## Requirements

### Requirement: Single-unit package assembly
The tool SHALL assemble `assets/converted/units/10033_wild_elephant/` with `package.json` (legacy_id, normalized unit definition ref, source provenance, frame data, symbols with export ids, per-sprite animation states, shape bounds/style/bitmap-ref records, bitmap outputs with digests) plus byte-identical bitmap copies. Bitmap digests SHALL match extraction outputs exactly.

#### Scenario: Assemble the measured elephant
- **WHEN** the converter runs on the current corpus after the extraction builds
- **THEN** the package directory holds a validated `package.json` plus the 28 JPEGs and 28 alpha PNGs with matching digests, frame data records 550×400 at 30.0 fps with 1 frame, and reruns are byte-identical

#### Scenario: Resolve the content reference
- **WHEN** the converter links the unit definition
- **THEN** exactly one normalized units entry matches legacy_id `933` (`img_name` `10033_wild_elephant`), recorded verbatim with no other definition touched

### Requirement: Per-sprite animation inventory
The tool SHALL parse `DefineSprite` bodies and their timeline tags (`PlaceObject2`, `RemoveObject2`, `FrameLabel`, `ShowFrame`, `End`), recording for each sprite its id, declared frame count, frame labels with 1-based frame indices, placements (frame, depth, referenced character with kind, move flag), and removals; the root timeline SHALL be recorded the same way; `SymbolClass` mappings SHALL be recorded as id-name pairs. Label semantics SHALL be recorded as names only, never interpreted. Declared frame counts SHALL match observed `ShowFrame` counts, character references SHALL resolve, and unsupported timeline tags or unresolved references SHALL fail closed.

#### Scenario: Inventory the measured timelines
- **WHEN** the converter reads the elephant timelines
- **THEN** sprite 63 is recorded with 29 frames and labels QUIETO f1, ANDAR f6, ATAQUE f11, MUERTE f16, PICAR f21, placing shapes 2, 4, 6, 8, 10 and sprites 19, 28, 37, 46, 55, 62 — all at depth 1 — plus its removals; sprites 19/28/37/46/55 are recorded with 20 frames and 5 placements each, sprite 62 with 7 frames and 3 placements, and `main` with 1 frame placing sprite 63 at depth 1

#### Scenario: Attribute labels by parsing, not by filename or flat lists
- **WHEN** label attribution is built from sprite bodies
- **THEN** all five labels attribute to sprite 63 exactly once with their frame indices, no sprite or the root reports labels it does not contain, and the recorded label names equal the source inspection's label list for the file

#### Scenario: Reject an unresolvable timeline
- **WHEN** a timeline contains an unsupported control tag, references an undefined character, or declares a frame count that differs from its observed `ShowFrame` count
- **THEN** validation fails with the offending sprite or tag identified and no outputs are written

### Requirement: Shape records with byte-aligned style arrays
The tool SHALL parse SHAPEWITHSTYLE bounds, fill/line style arrays with counts and types, bitmap-fill character IDs, and raw matrices for every shape in the source, failing closed on other shape versions or unexpected layouts. Edge records SHALL be counted, never tessellated. The shared style parser SHALL align to a byte boundary after the fill-style array so files whose fill arrays end mid-byte parse, and existing package outputs SHALL be re-verified byte-identical under the fix.

#### Scenario: Parse the measured shapes under the alignment fix
- **WHEN** the converter reads the elephant's 28 shapes (whose fill arrays end mid-byte and fail under the previous byte-strict read)
- **THEN** all 28 parse with bounds, line styles, and edge counts recorded, and each referenced bitmap fill recorded with the matrix preserved as raw bytes

#### Scenario: Prove the fix does not drift existing output
- **WHEN** the house package is regenerated with the shared parser change
- **THEN** its `package_sha256` and bitmap digests are byte-identical to the committed values

#### Scenario: Reject an unexpected shape
- **WHEN** a shape version or style layout falls outside the parsed subset
- **THEN** validation fails with a non-zero exit and no writes

### Requirement: Bitmap-fill resolution with recorded placeholders
The tool SHALL validate that every fill referenced by shape records is in range and resolves to an extraction output with a `bitmap_id` other than `65535`, SHALL record unreferenced `bitmap_id 65535` placeholder fills verbatim without resolving them, and SHALL fail when a referenced fill is unresolvable, out of range, or `65535`.

#### Scenario: Resolve the measured fills
- **WHEN** the converter validates the elephant's fills
- **THEN** 25 shapes record one unreferenced `65535` placeholder fill plus their referenced real fill, 3 shapes record only their referenced fill, all 28 referenced ids resolve to extraction outputs for the source, and the package copies match those outputs byte-for-byte

#### Scenario: Detect an unresolvable referenced fill
- **WHEN** a shape record references a fill with id `65535`, an index outside the fill array, or an id with no extraction output
- **THEN** validation fails with a non-zero exit and no writes

### Requirement: Neutral conversion manifest with merge
The tool SHALL write `conversions.json` as a neutral `conversion-v1` envelope whose package entries each carry their own `policy` and byte count, with `counts` recomputed from the entries and `inputs` keys merged per domain; each converter SHALL preserve foreign package entries and input keys verbatim, replace only its own entry, stamp the envelope policy, and produce byte-identical output regardless of which converter ran last. The building converter SHALL accept a legacy `building-conversion-v1` envelope only while its sole entry is the building's own, and the unit converter SHALL reject a non-`conversion-v1` envelope.

#### Scenario: Record both packages order-independently
- **WHEN** the building and unit converters run in either order
- **THEN** `conversions.json` ends with both package entries, envelope policy `conversion-v1`, correct per-entry policies, and counts equal regardless of run order, with each package's `package_sha256` unchanged

#### Scenario: Migrate the committed legacy envelope
- **WHEN** the building converter runs against the legacy manifest (or the unit converter runs against it)
- **THEN** the building converter rewrites it as `conversion-v1` with its fresh entry, while the unit converter fails closed with a clear message and no writes until the migration has run

### Requirement: Validation and manifest-grade determinism
The tool SHALL validate animation-state coverage, bitmap-fill resolution, content-ref uniqueness, schema fields, and determinism, and SHALL write the `conversions.json` merge plus a `converted` statuses merge only on success. It SHALL report success with exit 0 and any validation failure with a non-zero exit.

#### Scenario: Prove outputs match inputs
- **WHEN** the converter runs twice against unchanged inputs
- **THEN** the package directory, `conversions.json`, and statuses output are byte-identical, and the digests recorded in `package.json` equal recomputed ones

#### Scenario: Fail closed without partial writes
- **WHEN** any validation check fails
- **THEN** the converter exits non-zero, writes no package files, manifest entries, or status changes, and leaves prior outputs byte-identical

### Requirement: Preservation-safe conversion tooling
The tool SHALL parse tags and records only: no tessellation, no rasterization, no matrix, ratio, or script interpretation, no label-semantic interpretation, and no Flash, browser, server, network, or subprocess activity. It SHALL write only the package directory plus `conversions.json` and the statuses merge on success, SHALL leave sources, registry, coverage, inspection, and extraction manifests byte-identical, and SHALL not modify any other content definition.

#### Scenario: Convert without source side effects
- **WHEN** the converter runs on the current corpus
- **THEN** every source asset, registry output, and prior manifest remains byte-identical and only package outputs plus manifests are created or replaced

#### Scenario: Record labels as names only
- **WHEN** animation states are serialized
- **THEN** label names and frame indices are recorded verbatim with no mapping to idle, walk, attack, death, or sting behavior, and placement optional payloads beyond the character id are skipped rather than decoded
