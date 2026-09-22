## Purpose

Provide normalized, schema-validated offer-pack definitions for the legacy purchasable-pack table while preserving every legacy ID, item shape, and pinned anomaly without changing legacy behavior.

## Requirements

### Requirement: Classified normalized offer definitions
The package SHALL contain one normalized definition per stored entry of `offer_packs`. Each definition SHALL preserve `legacy_id` as the decimal id, record its content source and version, carry scalars and item shapes verbatim with a recorded shape class, and carry resolved references with pinned anomaly notes. Entry order SHALL be preserved.

#### Scenario: Review domain coverage
- **WHEN** the stored offer packs are compared with the normalized package
- **THEN** all 44 entries are represented with preserved legacy IDs, shape classes, and order, including the single null-items entry

#### Scenario: Distinguish validated refs from opaque leaves
- **WHEN** a maintainer reviews a pair second or the documented float
- **THEN** they are identified as opaque preserved leaves with notes, not validated references and not repaired data

### Requirement: Documented shape-preserving representation
Scalar amounts and display strings SHALL be kept verbatim; `items` structures SHALL be deep-copied verbatim with shape classes null/flat/pairs/groups. Flat leaves, pair firsts, and group integer leaves SHALL resolve against the normalized items legacy-ID set; pair seconds SHALL be numbers recorded opaque; exactly the two pinned anomalies SHALL be preserved under an exact-match allowlist. No value SHALL be rebalanced, reinterpreted semantically, repaired, or assigned a new gameplay meaning.

#### Scenario: Review a pinned anomaly
- **WHEN** a maintainer reviews offer 35
- **THEN** the float leaf, its sibling evidence, and its verbatim preservation are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate id uniqueness, reference resolution outside the pinned allowlist, pair/group structural conformity, required schema fields, and schema-validator traceability. It SHALL re-emit legacy-shaped entries and diff them against stored content, failing on any difference. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect a non-allowlisted anomaly
- **WHEN** an unresolving leaf appears outside the exact-match allowlist
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized offer definitions are re-emitted to legacy shape
- **THEN** the result matches stored content exactly

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, or execute Flash. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build. The builder SHALL refuse patch drift targeting `offer_packs`.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
