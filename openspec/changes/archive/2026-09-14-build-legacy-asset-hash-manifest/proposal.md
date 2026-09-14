## Why

The immutable `legacy-baseline` tag identifies the preserved repository revision, but the project still lacks the per-file SHA-256 evidence required by M0 to detect loss or corruption of the original asset corpus. This change records that evidence before canonical-save capture or later migration work begins.

## What Changes

- Add a deterministic, read-only manifest generator and verifier for regular Git blobs at the immutable `legacy-baseline` commit.
- Cover every baseline file whose extension is `.swf`, `.json`, `.xml`, `.png`, `.jpg`, `.jpeg`, `.mp3`, `.wav`, or `.gif`, without decoding, normalizing, executing, or modifying asset content.
- Commit `legacy-manifest.json` with repository-relative paths, lowercase SHA-256 digests, and raw Git-blob byte sizes in stable order.
- Add focused automated tests and preservation documentation for generation, verification, scope, evidence, and limitations.
- Fail explicitly for an invalid source, unsafe or ambiguous selected paths, unsupported entry types, malformed manifests, or integrity mismatches.

## Capabilities

### New Capabilities

- `legacy-asset-integrity`: Defines deterministic enumeration, hashing, serialization, and verification of the immutable legacy asset corpus.

### Modified Capabilities

None.

## Impact

This change adds preservation tooling under `tools/hash-manifest/`, focused tests, the root `legacy-manifest.json`, narrowly scoped line-ending policy for that generated file, and documentation/verified command guidance. It adds no dependency, changes no application runtime behavior, executes no Flash content, and does not modify, relocate, convert, or delete any preserved asset, configuration, village, template, mod, or save file. Canonical save fixtures, wider provenance metadata, asset conversion, rights classification, and modern runtime integration remain out of scope.
