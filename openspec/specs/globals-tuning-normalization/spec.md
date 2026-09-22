## Purpose

Provide normalized, schema-validated tuning-constant definitions for the legacy heterogeneous globals table with patch lineage while preserving every constant name and value without changing legacy behavior.

## Requirements

### Requirement: Layered normalized tuning definitions
The package SHALL contain one normalized definition per loaded entry of `globals` after applying only the `atom_fusion_powerup` add. Each definition SHALL preserve `legacy_id` as the constant name, record its content source, per-entry layer, and version, and carry the verbatim value with its recorded value type. Loaded key order SHALL be preserved.

#### Scenario: Review domain coverage
- **WHEN** the loaded globals object is compared with the normalized package
- **THEN** all 105 loaded constants are represented with preserved names and order, and the stored 104 are recorded as layering inputs with the single patch-added schedule identified

#### Scenario: Distinguish opaque strings from structured values
- **WHEN** a maintainer reviews a friend-reward CSV string or a numeric schedule
- **THEN** the string is identified as opaque config data while the schedule is identified as a verbatim structured value, neither interpreted as behavior

### Requirement: Documented patch lineage and verbatim values
The builder SHALL verify the ordered patch list, apply only the single powerup add of `/globals/SOUL_MIXER_POWERUPS_LEVELS`, and refuse any other globals target or divergent add shape. Values SHALL be kept verbatim as observed JSON with recorded types; string constants SHALL never be parsed. No value SHALL be rebalanced, renamed, regrouped, or assigned a new gameplay meaning.

#### Scenario: Review a patch-added schedule
- **WHEN** a maintainer reviews the soul-mixer schedule definition
- **THEN** its patched layer, verbatim rows, and lineage are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites census/survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate key uniqueness, patch-shape conformity, required schema fields including the value-type union, and schema-validator traceability. It SHALL re-emit the loaded-shaped object and diff it against the loaded object, failing on any difference. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success. Patch drift or active mods SHALL fail explicitly without writing output.

#### Scenario: Detect a divergent patch shape
- **WHEN** the powerup patch carries anything other than the single schedule add
- **THEN** the build fails explicitly without writing output

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized tuning definitions are re-emitted to loaded shape
- **THEN** the result matches the loaded object exactly by key, type, and value

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, execute Flash, or read the wall clock. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
