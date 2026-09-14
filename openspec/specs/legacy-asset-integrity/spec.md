# Legacy Asset Integrity Specification

## Purpose

Defines deterministic integrity evidence for the immutable legacy asset corpus so preserved bytes can be verified without executing or rewriting them.

## Requirements

### Requirement: Immutable baseline asset selection
The manifest generator SHALL resolve the local `legacy-baseline` tag to its full commit and SHALL select every regular Git blob in that immutable tree whose case-insensitive extension is `.swf`, `.json`, `.xml`, `.png`, `.jpg`, `.jpeg`, `.mp3`, `.wav`, or `.gif`. Selection SHALL use repository-relative Git paths rather than ambient, ignored, untracked, or generated worktree files.

#### Scenario: Enumerate the recorded baseline corpus
- **WHEN** the generator processes the repository's current `legacy-baseline` commit
- **THEN** it selects exactly the 3,258 matching regular blobs while preserving each path's spelling and case

#### Scenario: Ignore later and mutable files
- **WHEN** a matching file exists only outside the immutable baseline tree
- **THEN** it is not added to the baseline manifest

#### Scenario: Reject an ambiguous source entry
- **WHEN** a selected path is unsafe, collides case-insensitively with another selected path, or is not a regular blob
- **THEN** generation fails explicitly without following the entry or producing a partial manifest

### Requirement: Raw Git-blob SHA-256 identity
Each manifest entry SHALL contain the SHA-256 digest and byte size of the exact Git blob stored by the baseline commit. Hashing SHALL treat content as opaque binary bytes and SHALL NOT apply checkout line-ending conversion, filters, text decoding, normalization, content reserialization, or runtime execution.

#### Scenario: Checkout conversion differs from committed bytes
- **WHEN** Git would materialize a text asset with platform-specific line endings
- **THEN** the recorded digest and size still identify the raw committed blob bytes

#### Scenario: Duplicate content exists at different paths
- **WHEN** two selected paths contain identical bytes
- **THEN** both paths remain separate manifest entries with their shared digest and size

### Requirement: Deterministic manifest serialization
The repository SHALL contain `legacy-manifest.json` as UTF-8 JSON with schema version `1`, algorithm `sha256`, the full resolved source commit, a stable policy identifier, and an ordered array of file entries. Each entry SHALL use the fixed fields `path`, `sha256`, and `size`; paths SHALL use `/`, digests SHALL be 64 lowercase hexadecimal characters, sizes SHALL be non-negative integers, entries SHALL be ordered by exact repository-relative path, and the file SHALL have no timestamp, machine-local value, byte-order mark, or nondeterministic metadata.

#### Scenario: Repeat generation
- **WHEN** the manifest is generated twice from the same baseline commit and policy
- **THEN** both outputs are byte-for-byte identical

#### Scenario: Record source provenance
- **WHEN** a maintainer reads the generated manifest
- **THEN** the schema, algorithm, policy, full source commit, path, digest, and size fields are sufficient to interpret every entry without relying on a mutable ref name

### Requirement: Read-only integrity verification
The tooling SHALL provide a verification mode that strictly validates the manifest schema and deterministically reconstructs the selected baseline entries from the recorded commit. Verification SHALL compare source identity, path set, order, digest, size, and canonical serialization, SHALL report integrity or format failures without disclosing asset content, and SHALL make no repository writes.

#### Scenario: Verify an unchanged manifest
- **WHEN** the committed manifest matches the locally available recorded baseline commit
- **THEN** verification exits successfully and reports the verified entry count

#### Scenario: Detect manifest tampering or corruption
- **WHEN** an entry is added, removed, reordered, renamed, given an incorrect digest or size, or the schema/source metadata is invalid
- **THEN** verification exits nonzero with a diagnostic that identifies the mismatch without silently regenerating the file

#### Scenario: Source commit is unavailable
- **WHEN** the exact commit recorded by the manifest is not available in the local Git repository
- **THEN** verification fails explicitly and performs no network operation

### Requirement: Preservation-safe operation and evidence
Generation and verification SHALL use only locally available Git data, SHALL NOT fetch, check out, execute, decode, convert, relocate, overwrite, or delete preserved content, and SHALL require no new third-party dependency. Repository documentation SHALL record the commands actually verified, the corpus policy and count, the immutable source commit, and limitations including the exclusion of non-matching extensions, mutable saves, packaged-release bytes, live-worktree integrity, runtime behavior, and later asset provenance or rights metadata.

#### Scenario: Generate preservation evidence
- **WHEN** the approved generation command completes
- **THEN** only the designated manifest output is created or replaced and all preserved source files remain byte-identical

#### Scenario: Review scope limitations
- **WHEN** a maintainer reviews the manifest documentation
- **THEN** it distinguishes the verified Git-blob corpus from excluded files and from claims about runtime behavior, distribution rights, or external release archives
