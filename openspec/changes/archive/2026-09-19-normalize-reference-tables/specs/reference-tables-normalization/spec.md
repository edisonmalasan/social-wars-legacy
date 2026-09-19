## Purpose

Provide normalized, schema-validated magic, level-curve, and sound definitions for the legacy static lookup tables while preserving every legacy ID and recording every encoding decision without changing legacy behavior.

## ADDED Requirements

### Requirement: Classified normalized table definitions
The package SHALL contain one normalized definition per stored entry of `magics`, `levels`, and `sounds`. Each definition SHALL preserve `legacy_id`, record its content source and version, and carry asset references as observed. The XP curve order SHALL be preserved positionally.

#### Scenario: Review domain coverage
- **WHEN** the stored tables are compared with the normalized package
- **THEN** all 10 magics, 100 levels, and 139 sounds are represented with preserved legacy IDs

#### Scenario: Distinguish references from asset names
- **WHEN** a maintainer reviews a sound file name or magic area array
- **THEN** they are identified as recorded asset/formation data, not validated cross-references

### Requirement: Documented encoding decisions
Every string-encoded value SHALL be coerced under a documented rule citing the field-type survey: `sounds` IDs and numeric params to integers, `magics` area arrays to integer arrays, native numbers kept. Asset names and descriptions SHALL be preserved verbatim. No value SHALL be rebalanced, renamed for gameplay, or assigned a new gameplay meaning.

#### Scenario: Review a coerced spell area
- **WHEN** a maintainer reviews a normalized magic area
- **THEN** the integer array and the coercion rule from the embedded-JSON string are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate duplicate IDs, non-negative amounts, required schema fields, and schema-validator traceability. It SHALL re-emit legacy-shaped entries and diff them against stored content modulo documented coercions, failing on unexplained differences. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect a duplicate ID
- **WHEN** two entries share a legacy ID
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized table definitions are re-emitted to legacy shape
- **THEN** the result matches stored content except for documented coercions

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, or execute Flash. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
