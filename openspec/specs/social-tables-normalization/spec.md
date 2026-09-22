## Purpose

Provide normalized, schema-validated neighbor-assist, findable-item, and social-item definitions for the legacy social/ambient lookup tables while preserving every legacy position and ID without changing legacy behavior.

## Requirements

### Requirement: Classified normalized social table definitions
The package SHALL contain one normalized definition per stored entry of `neighbor_assists`, `findable_items`, and `social_items`. Each definition SHALL preserve `legacy_id` (positional index for neighbor assists, decimal id for findables and social items), record its content source and version, and carry all native amounts and display strings verbatim. Entry order SHALL be preserved positionally.

#### Scenario: Review domain coverage
- **WHEN** the stored social tables are compared with the normalized package
- **THEN** all 5 neighbor assists, 10 findable items, and 26 social items are represented with preserved legacy IDs and order

#### Scenario: Distinguish data from behavior
- **WHEN** a maintainer reviews a worker name or assist reward
- **THEN** they are identified as recorded display data and amounts, not implemented social behavior

### Requirement: Documented verbatim representation
All schedule fields SHALL be carried verbatim as observed: native integers (`rnd`, reward `coins`/`cash`/`xp`, `id`, `coins`, `worker_cost`) and display strings (`task`/`action`/`notification`, `title`/`description`, `workers`). The uniformly-empty `social_items` `description` (26 of 26) SHALL be preserved verbatim with a manifest note, never defaulted or dropped. Uniform values (identical assist rewards, uniform findable coins) SHALL be carried as stored, never factored out. No value SHALL be rebalanced, renamed for gameplay, or assigned a new gameplay meaning.

#### Scenario: Review a uniformly-empty description
- **WHEN** a maintainer reviews a normalized social item
- **THEN** the empty description and its uniformity note are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate positional/id uniqueness, non-negative amounts, required schema fields, and schema-validator traceability. It SHALL re-emit legacy-shaped entries and diff them against stored content, failing on any difference. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect a duplicate ID
- **WHEN** two entries share a legacy ID
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized social table definitions are re-emitted to legacy shape
- **THEN** the result matches stored content exactly

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, or execute Flash. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build. The builder SHALL refuse patch drift targeting any of the three keys.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
