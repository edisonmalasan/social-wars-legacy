## Purpose

Provide a normalized, schema-validated image-asset path registry for the legacy asset-path index while preserving every path verbatim without changing legacy behavior.

## Requirements

### Requirement: Classified normalized image registry
The package SHALL contain one normalized definition per stored entry of `images`. Each definition SHALL preserve `legacy_id` as the verbatim asset path, record its content source and version, and carry the locale verbatim. Entry order SHALL follow stored document order.

#### Scenario: Review domain coverage
- **WHEN** the stored images object is compared with the normalized package
- **THEN** all 607 paths are represented with preserved spellings and order

#### Scenario: Distinguish registry from asset truth
- **WHEN** a maintainer reviews a swf path or a locale value
- **THEN** they are identified as recorded references, never checked against disk and never executed

### Requirement: Documented verbatim path preservation
Asset paths SHALL be kept exactly as stored (slashes, case, extension untouched); the locale SHALL be exactly `en`, failing otherwise as drift. Extension distribution SHALL be recorded without enforcement. No path SHALL be rewritten, checked against disk, or executed; no value SHALL be assigned a new meaning.

#### Scenario: Review a recorded swf path
- **WHEN** a maintainer reviews a swf entry
- **THEN** it is identified as an archival reference for the M4 pipeline, not a runtime dependency

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not asset validation or gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate key uniqueness and non-emptiness, locale exactly `en`, required schema fields, and schema-validator traceability. It SHALL re-emit the legacy-shaped object and diff it against the stored object, failing on any difference. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect a locale drift
- **WHEN** a stored value is anything other than `en`
- **THEN** validation fails with a non-zero exit identifying the offending path

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized image definitions are re-emitted to legacy shape
- **THEN** the result matches the stored object exactly

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, execute Flash, or touch the filesystem beyond reading the stored sources. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build. The builder SHALL refuse patch drift targeting `images`.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
