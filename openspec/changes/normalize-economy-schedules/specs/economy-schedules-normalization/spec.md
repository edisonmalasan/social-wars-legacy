## Purpose

Provide normalized, schema-validated expansion, town/map unlock, and level-ranking reward schedules for the legacy economy tables while preserving every legacy position and level identity without changing legacy behavior.

## ADDED Requirements

### Requirement: Classified normalized economy schedule definitions
The package SHALL contain one normalized definition per stored entry of `expansion_prices`, `town_prices`, `map_prices`, and `level_ranking_reward`. Each definition SHALL preserve `legacy_id` (positional index for the three price schedules, decimal level for ranking rewards), record its content source and version, and carry all native amounts verbatim. Schedule order SHALL be preserved positionally; town and map schedules SHALL be preserved as separate files even though their stored values are identical.

#### Scenario: Review domain coverage
- **WHEN** the stored economy schedules are compared with the normalized package
- **THEN** all 98 expansion prices, 4 town prices, 4 map prices, and 50 level-ranking rewards are represented with preserved legacy IDs and order

#### Scenario: Distinguish price schedules from reward references
- **WHEN** a maintainer reviews a ranking reward units map
- **THEN** its keys are identified as validated item references while price-schedule amounts are identified as verbatim native values with no references

### Requirement: Documented verbatim native representation
All schedule fields SHALL be carried verbatim as observed native numbers and objects with no string coercion and no embedded-JSON parsing: expansion `coins`/`cash`/`neighbors`/`inventory_qte`, town/map `coins`/`cash`/`level`, ranking `level`/`cash`/`units`. Ranking `units` keys SHALL be validated against the normalized items legacy-ID set and carried with resolved reference lists. No value SHALL be rebalanced, renamed for gameplay, deduplicated across town/map schedules, or assigned a new gameplay meaning.

#### Scenario: Review a ranking reward reference
- **WHEN** a maintainer reviews a normalized ranking reward
- **THEN** the units map and its resolved item references against the normalized items set are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate positional uniqueness, non-negative amounts, ranking level coverage exactly 50..1, unresolvable ranking unit references, required schema fields, and schema-validator traceability. It SHALL re-emit legacy-shaped entries and diff them against stored content, failing on any difference. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect an unresolvable ranking reference
- **WHEN** a ranking units key does not resolve against the normalized items legacy-ID set
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized economy schedule definitions are re-emitted to legacy shape
- **THEN** the result matches stored content exactly

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, or execute Flash. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build. The builder SHALL refuse patch drift targeting any of the four keys.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
