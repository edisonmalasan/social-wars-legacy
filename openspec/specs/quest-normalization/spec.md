# Quest Normalization Specification

## Purpose

Provide normalized, schema-validated quest and collection definitions for the legacy quest content domain while preserving every legacy ID and recording every encoding decision without changing legacy behavior.

## Requirements

### Requirement: Classified normalized quest definitions
The package SHALL contain one normalized quest definition per stored `goals` entry and one normalized collection definition per stored `collections` entry. Each definition SHALL preserve `legacy_id`, record its content source and version, and carry cross-references as observed. Uniform fields (`hint`, `reward`) SHALL be preserved verbatim with recorded notes, never dropped as redundant.

#### Scenario: Review domain coverage
- **WHEN** the stored quest content is compared with the normalized package
- **THEN** all 91 quests and 10 collections are represented with preserved legacy IDs

#### Scenario: Distinguish uniform fields from absent fields
- **WHEN** a maintainer reviews the uniform hint or reward
- **THEN** the stored uniformity is identified with its rationale, not mistaken for missing data

### Requirement: Documented encoding decisions
Every string-encoded value SHALL be coerced under a documented rule citing the field-type survey: string IDs and prices to numbers, embedded-JSON `item_ids`/`prize` strings to structures, native IDs kept. Collection cross-references SHALL resolve against the normalized items legacy-ID set. No value SHALL be rebalanced, renamed for gameplay, or assigned a new gameplay meaning.

#### Scenario: Review a resolved collection
- **WHEN** a maintainer reviews a normalized collection
- **THEN** every item reference is identified as resolving to a known items legacy ID

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate duplicate IDs, cross-reference resolution, price/cost shapes, required schema fields, and schema-validator traceability. It SHALL re-emit legacy-shaped entries and diff them against stored content modulo documented coercions, failing on unexplained differences. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect a broken item reference
- **WHEN** a collection references an unknown item ID
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized quest definitions are re-emitted to legacy shape
- **THEN** the result matches stored content except for documented coercions

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, or execute Flash. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
