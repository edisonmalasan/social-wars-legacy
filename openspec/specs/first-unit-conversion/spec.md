## Purpose

Provide one assembled converted-unit package that inventories each sprite timeline (labels, frames, placements, shapes, bitmap links) for the smallest unit library so Godot import and M6 unit rendering work can start from validated inputs without executing Flash.

## Requirements

### Requirement: Single-unit package assembly
The tool SHALL assemble `assets/converted/units/<target-stem>/` for the **declared target stem and its normalized content `legacy_id`**, both of which SHALL be required inputs; the tool SHALL NOT carry a default target or id. It SHALL record `package.json` (legacy_id, normalized unit definition ref, source provenance, frame data, symbols with export ids, per-sprite animation states, shape bounds/style/bitmap-ref records, bitmap outputs with digests) plus byte-identical bitmap copies. The definition SHALL be resolved by the pair (`legacy_id`, `img_name`) and SHALL fail closed unless exactly one normalized units entry matches. Bitmap digests SHALL match extraction outputs exactly.

#### Scenario: Assemble the measured elephant
- **WHEN** the converter runs on `10033_wild_elephant` with content id `933` against the current corpus after the extraction builds
- **THEN** the package directory holds a validated `package.json` plus its JPEGs and alpha PNGs with matching digests, and frame data records 550×400 at 30.0 fps with 1 frame

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

### Requirement: The unit package provenance digest is independent of the checkout's line endings
The tool SHALL compute the input fingerprint that becomes the package's `content_version` over **line-ending-normalised** bytes, so that the same committed content yields the same `content_version` on an LF checkout and a CRLF checkout alike. The tool SHALL NOT hash raw working-tree bytes of any input whose line endings are not pinned.

#### Scenario: One digest across checkout forms
- **WHEN** the fingerprint is computed over inputs whose working-tree bytes contain CRLF
- **THEN** it equals the fingerprint computed over the same inputs with LF line endings

#### Scenario: The manifest is regenerated with the digest
- **WHEN** the fingerprint is first computed over normalised bytes
- **THEN** the recorded `content_version` changes from the previously committed raw-byte digest
- **AND** `conversions.json` records the new `package_sha256` for this package
- **AND** the other converter's foreign package entry and input keys are preserved verbatim

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
The tool SHALL parse SHAPEWITHSTYLE bounds, fill/line style arrays with counts and types, bitmap-fill character IDs, and raw matrices for every shape in the source, failing closed on other shape versions or unexpected layouts. Edge records SHALL be counted, never tessellated. The shared style parser SHALL align to a byte boundary after the fill-style array so files whose fill arrays end mid-byte parse, and existing package outputs SHALL be re-verified byte-identical under the fix. `RECT` coordinate fields SHALL be decoded as the signed bit fields the format specifies: a field whose sign bit within the declared `Nbits` is set SHALL be sign-extended to its negative value rather than read as a large unsigned value. A decoded `RECT` whose `xmax` is below its `xmin`, or whose `ymax` is below its `ymin`, SHALL fail closed as an inverted rectangle, and SHALL NOT be reported as an extent of zero.

#### Scenario: Parse the measured shapes under the alignment fix
- **WHEN** the converter reads the elephant's 28 shapes (whose fill arrays end mid-byte and fail under the previous byte-strict read)
- **THEN** all 28 parse with bounds, line styles, and edge counts recorded, and each referenced bitmap fill recorded with the matrix preserved as raw bytes

#### Scenario: Prove the fix does not drift existing output
- **WHEN** the house package is regenerated with the shared parser change
- **THEN** its `package_sha256` and bitmap digests are byte-identical to the committed values

#### Scenario: Correct origins without moving sizes
- **WHEN** the committed elephant package is regenerated under the signed rule
- **THEN** 19 of its 28 shapes record a corrected `xmin` or `ymin`
- **AND** `width_px` and `height_px` are unchanged on all 28 shapes and every non-shape package field is unchanged

#### Scenario: Reject an inverted rectangle
- **WHEN** a decoded `RECT` has `xmax` below `xmin`, or `ymax` below `ymin`
- **THEN** validation fails with a non-zero exit and no writes
- **AND** the extent is not floored at zero

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

### Requirement: The placeholder rule is scoped to the unit converter's own subset and is not widened
The unit converter's recorded-placeholder handling for an **unreferenced** `bitmap_id 65535` fill, and its refusal of a **referenced** one, SHALL remain exactly as specified. The tool SHALL NOT extend that rule to the building converter, SHALL NOT relax it for units, and SHALL NOT treat a `65535` fill as resolvable. Whether the building converter's population requires the same rule is **not** established, and this capability asserts nothing about it.

#### Scenario: Keep the unit rule exact
- **WHEN** a unit shape records an unreferenced `65535` fill
- **THEN** the fill is recorded verbatim and the conversion proceeds
- **AND** a shape record that references a `65535` fill still fails closed with no writes

#### Scenario: Do not port the rule on inference
- **WHEN** the building converter's refusals are measured
- **THEN** this capability's unit rule is not cited as the explanation for any of them
- **AND** a change to the building converter's fill handling requires its own established cause

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
