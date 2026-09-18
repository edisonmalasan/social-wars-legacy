# Content Census Specification

## Purpose

Provide a source-grounded census of preserved legacy game-content sources and their layering that distinguishes stored content from time-dependent served bytes without executing the application.

## Requirements

### Requirement: Complete stored-content inventory
The census SHALL cover every top-level key of the canonical content file, every active patch in application order, the mods pipeline status, the import-time duplicate-cleaning behavior, and the dynamic-derivation boundary. Each content-key entry SHALL identify its container shape, entry count, ID scheme, and asset-reference fields. Patch entries SHALL identify file order, operation counts, and target paths. Content that is only produced at serve time SHALL NOT be presented as stored content.

#### Scenario: Review current content coverage
- **WHEN** the current content sources are compared with the census
- **THEN** all 20 top-level keys, five ordered patches, the inactive mods pipeline, duplicate cleaning, and dynamic derivation are represented separately

#### Scenario: Distinguish stored from served bytes
- **WHEN** a maintainer reviews a time-dependent content section
- **THEN** the census identifies the stored source values and states that served bytes are re-derived from the wall clock

### Requirement: Source-grounded layering and evidence
Each census entry SHALL describe its source file, layering order relative to other sources, and supporting source references. Documentation SHALL distinguish file inspection from executed behavioral evidence, label unavailable evidence explicitly, and contain no credential values or private player records. File review SHALL NOT be presented as gameplay parity, content validity, or normalization.

#### Scenario: Review patch layering
- **WHEN** a maintainer reviews a patched content value
- **THEN** the census identifies which patch file, in which order position, targets that value

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a census entry
- **THEN** the entry states that only source inspection supports it and names served-byte equality as unverified

### Requirement: Offline census verification
A read-only verification command SHALL check census structure, key coverage and entry counts, patch presence/order/parseability, mods status, and consistency with the readable inventory. It SHALL report agreement with exit 0, census drift with exit 1, and invalid inputs or unsupported content shapes with exit 2. Repeated verification of unchanged inputs SHALL produce identical results. Unsupported shapes SHALL fail explicitly rather than silently omit content.

#### Scenario: Detect content drift
- **WHEN** a content key, entry count, patch order, or mods status differs from the reviewed census
- **THEN** verification exits 1 and identifies the census inconsistency

#### Scenario: Reject unsupported content shapes
- **WHEN** a content section cannot be resolved by the supported structural analysis
- **THEN** verification exits 2 without claiming complete coverage

### Requirement: Preservation-safe census tooling
Census verification SHALL NOT import or execute legacy application modules, apply patches through the legacy path, read runtime saves, contact a network, start a server, open a browser, or execute Flash. The documented invocation SHALL leave repository and supplied input bytes unchanged and create no cache, bytecode, report, or temporary file in the repository. The census change SHALL preserve existing content files and legacy behavior.

#### Scenario: Verify without runtime side effects
- **WHEN** verification succeeds, detects drift, or rejects invalid source
- **THEN** supplied inputs and repository files remain unchanged and no legacy runtime activity occurs
