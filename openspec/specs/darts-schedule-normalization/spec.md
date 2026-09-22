## Purpose

Provide normalized, schema-validated darts schedule definitions for the legacy patch-replaced weekly event table while preserving every legacy ID and the patch lineage without changing legacy behavior.

## Requirements

### Requirement: Layered normalized darts definitions
The package SHALL contain one normalized definition per patched entry of `darts_items` after applying only the `targets` whole-array replace. Each definition SHALL preserve `legacy_id` as the decimal id, record its content source, patch lineage, and version, and carry the pooled item integers, extra item, and `start_date` derivation input. Patched order SHALL be preserved.

#### Scenario: Review domain coverage
- **WHEN** the patched darts array is compared with the normalized package
- **THEN** all 27 patched entries are represented with preserved legacy IDs and order, and the stored 30 are recorded as replace inputs only

#### Scenario: Distinguish derivation inputs from served values
- **WHEN** a maintainer reviews a normalized `start_date`
- **THEN** it is identified as a stored derivation input, never a served value

### Requirement: Documented patch lineage and verbatim pools
The builder SHALL verify the ordered patch list, apply only the single `targets` replace of `/darts_items`, and refuse any other darts target or divergent replace shape. Native integer pools SHALL be kept verbatim and validated against the normalized items legacy-ID set with references carried in stored order. `start_date` strings SHALL be preserved verbatim and never recomputed. No value SHALL be rebalanced, renamed for gameplay, or assigned a new gameplay meaning.

#### Scenario: Review a resolved darts pool
- **WHEN** a maintainer reviews a normalized darts entry
- **THEN** the six pooled ids, the extra id, and their resolved item references are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites census/survey evidence and states that normalization is a representation change, not gameplay parity, with served bytes explicitly out of scope

### Requirement: Validation and round-trip evidence
The builder SHALL validate id uniqueness, pool/reference resolution, required schema fields, and schema-validator traceability. It SHALL re-emit patched-shaped entries and diff them against the patched array, failing on any difference. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success. Patch drift or active mods SHALL fail explicitly without writing output.

#### Scenario: Detect an unresolvable pooled reference
- **WHEN** a pooled or extra id does not resolve against the normalized items legacy-ID set
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized darts definitions are re-emitted to patched shape
- **THEN** the result matches the patched array exactly

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, execute Flash, or read the wall clock. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
