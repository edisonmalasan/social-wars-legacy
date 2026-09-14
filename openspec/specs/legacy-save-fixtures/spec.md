# Legacy Save Fixtures Specification

## Purpose

Define reproducible preservation evidence for legacy player-save creation and migration while distinguishing verified fixture states from unavailable historical coverage.

## Requirements

### Requirement: Controlled fresh-player capture
The fixture workflow SHALL exercise the repository's legacy fresh-player creation, migration, validation, and persistence behavior with explicitly controlled UUID and time inputs. It SHALL write only to a disposable capture location and SHALL preserve the complete resulting save state, including fields not otherwise interpreted by the fixture workflow.

#### Scenario: Capture a fresh player deterministically
- **WHEN** the capture workflow runs twice from the same verified sources and controlled inputs
- **THEN** both runs produce byte-identical canonical fresh-player output representing the persisted legacy save

#### Scenario: Contain runtime writes
- **WHEN** the capture workflow exercises legacy persistence
- **THEN** it creates no file in the repository's ignored runtime `saves/` directory and changes no legacy source, template, static-neighbor, or archival asset

### Requirement: Migration-boundary evidence
The fixture set SHALL include the controlled pre-migration state and the corresponding post-migration state produced by the actual legacy migration path. Verification SHALL compare each complete state rather than a selected field subset.

#### Scenario: Verify the migration boundary
- **WHEN** the canonical pre-migration input is processed by the verified legacy migration source
- **THEN** the complete resulting state exactly matches the committed post-migration fresh-player fixture

#### Scenario: Detect migration drift
- **WHEN** any field in the recomputed post-migration state differs from the committed fixture
- **THEN** verification fails and identifies the mismatched fixture

### Requirement: Immutable provenance and integrity manifest
Every canonical fixture SHALL have a machine-readable manifest entry recording its repository-relative path, SHA-256 digest, byte size, semantic role, controlled nondeterministic inputs, and immutable provenance for the legacy sources used to produce it. The provenance SHALL include the baseline Git commit and source blob identities needed to detect source drift.

#### Scenario: Verify fixture and source integrity
- **WHEN** verification runs against an unchanged fixture set and matching legacy source blobs
- **THEN** every recorded fixture digest, byte size, provenance value, and source identity matches

#### Scenario: Reject unrecorded drift
- **WHEN** a canonical fixture or provenance source differs from its manifest record
- **THEN** verification exits unsuccessfully and reports the affected path or provenance field

### Requirement: Read-only deterministic verification
The repository SHALL provide a verification mode that regenerates evidence in disposable storage, compares it with the committed fixture set, and leaves tracked files and canonical fixtures unchanged. The workflow SHALL require no network access, browser, Flash runtime, or dependency beyond the verified legacy Python environment.

#### Scenario: Verify without modifying the repository
- **WHEN** verification succeeds from a clean checkout
- **THEN** the canonical fixture paths and other tracked files retain their original bytes and no runtime save is left behind

#### Scenario: Report a tampered fixture
- **WHEN** verification is run against a fixture set whose bytes no longer match the deterministic capture
- **THEN** it returns a non-zero result with a concrete integrity or content mismatch

### Requirement: Evidence classification
Fixture documentation and metadata SHALL classify the fresh-player and migration-boundary states as controlled canonical test inputs derived from repository behavior, not as historical player observations. It SHALL identify early-game, mid-game, late-game, and stress-town player-save coverage as unavailable and unverified until authentic evidence is acquired, and SHALL not present static neighbor states as player-save substitutes.

#### Scenario: Review fixture coverage
- **WHEN** a maintainer inspects the fixture documentation or manifest
- **THEN** the verified fresh and migration states and the unavailable progressed-player categories are explicitly distinguishable

#### Scenario: Preserve static neighbor semantics
- **WHEN** static neighbor state files are referenced as supporting repository evidence
- **THEN** they remain labeled as static neighbor data and are neither copied nor claimed as canonical player progression fixtures
