## Purpose

Provide the first normalized, schema-validated, Godot-loadable game definitions for the legacy items domain while preserving every legacy ID and recording every encoding decision without changing legacy behavior.

## ADDED Requirements

### Requirement: Classified normalized definitions
The package SHALL contain one normalized definition per loaded items entry, classified by the stored `type` field into buildings, units, or documented specials. Each definition SHALL preserve `legacy_id` (the stored string `id`), record its content source and version, and carry asset references as observed. The single `l` entry SHALL be a documented special, never silently a building or unit.

#### Scenario: Review domain coverage
- **WHEN** the loaded items content is compared with the normalized package
- **THEN** all 470 buildings, 429 units, and the documented special are represented with preserved legacy IDs (stored 778 plus 122 patch-appended entries, all ids distinct)

#### Scenario: Distinguish specials from definitions
- **WHEN** a maintainer reviews the Expandable Land entry
- **THEN** it is identified as a documented special with its rationale, not a building or unit

### Requirement: Documented encoding decisions
Every string-encoded value SHALL be coerced under a documented rule: numeric strings to numbers, embedded-JSON strings to structures, meaningful empty strings preserved, and the always-null `cost_type` dropped with a recorded note. The rule set SHALL cite the field-type survey as its input. No value SHALL be rebalanced, renamed for gameplay, or assigned a new gameplay meaning.

#### Scenario: Review a coerced cost
- **WHEN** a maintainer reviews a normalized cost map
- **THEN** the resource keys, amounts, and the coercion rule from the embedded-JSON string are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate duplicate IDs, cross-reference resolution (`upgrades_to`, `trains_ids`, item-id references), cost-key membership and non-negative amounts, required schema fields, and schema-validator traceability (every schema-required field has a validator check). It SHALL re-emit legacy-shaped items and diff them against loaded legacy content modulo documented coercions, failing on unexplained differences. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect a broken reference
- **WHEN** an upgrade, training, or cost reference does not resolve
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized definitions are re-emitted to legacy shape
- **THEN** the result matches loaded legacy content except for documented coercions

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, or execute Flash. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. Unknown legacy save fields and unmodeled content keys SHALL remain untouched.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
