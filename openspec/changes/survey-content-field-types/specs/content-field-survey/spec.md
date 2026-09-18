## Purpose

Provide a source-grounded survey of preserved legacy content field types and value encodings that distinguishes observed encoding facts from normalization decisions without executing the application.

## ADDED Requirements

### Requirement: Complete field-encoding inventory
The survey SHALL cover every top-level content key: per-field encoding profiles for array-of-object keys and value-shape profiles for object keys. Each field profile SHALL identify presence count, JSON-level type distribution, string-encoded-number count, embedded-JSON-string count, empty-string count, and null count. Deterministic predicates SHALL define the encoded-number and embedded-JSON classifications. No coercion, defaulting, or normalization SHALL be recorded as fact.

#### Scenario: Review current encoding coverage
- **WHEN** the current content sources are compared with the survey
- **THEN** all 20 top-level keys are represented with per-field or value-shape profiles as appropriate

#### Scenario: Distinguish observation from normalization
- **WHEN** a maintainer reviews a string-encoded numeric field
- **THEN** the survey states the observed encoding counts without prescribing a target type

### Requirement: Source-grounded profiles and evidence
Each survey entry SHALL describe its source key, observed counts recomputed from the committed file, and supporting source references. Documentation SHALL distinguish file inspection from executed behavioral evidence, label unavailable evidence explicitly, and contain no credential values or private player records. File review SHALL NOT be presented as content validity, normalization, or gameplay parity.

#### Scenario: Review a mixed-encoding key
- **WHEN** a maintainer reviews a key holding both strings and numbers
- **THEN** the survey identifies per field which values are encoded and which are native

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a survey entry
- **THEN** the entry states that only source inspection supports it and names normalization decisions as future work

### Requirement: Offline survey verification
A read-only verification command SHALL check survey structure, key coverage, per-field and value-shape profile equality recomputed from source, and consistency with the readable inventory. It SHALL report agreement with exit 0, survey drift with exit 1, and invalid inputs or unsupported content shapes with exit 2. Repeated verification of unchanged inputs SHALL produce identical results. Unsupported shapes SHALL fail explicitly rather than silently omit content.

#### Scenario: Detect encoding drift
- **WHEN** a field type distribution or encoding count differs from the reviewed survey
- **THEN** verification exits 1 and identifies the survey inconsistency

#### Scenario: Reject unsupported content shapes
- **WHEN** a content section cannot be resolved by the supported structural analysis
- **THEN** verification exits 2 without claiming complete coverage

### Requirement: Preservation-safe survey tooling
Survey verification SHALL NOT import or execute legacy application modules, coerce or rewrite content, read runtime saves, contact a network, start a server, open a browser, or execute Flash. The documented invocation SHALL leave repository and supplied input bytes unchanged and create no cache, bytecode, report, or temporary file in the repository. The survey change SHALL preserve existing content files and legacy behavior.

#### Scenario: Verify without runtime side effects
- **WHEN** verification succeeds, detects drift, or rejects invalid source
- **THEN** supplied inputs and repository files remain unchanged and no legacy runtime activity occurs
