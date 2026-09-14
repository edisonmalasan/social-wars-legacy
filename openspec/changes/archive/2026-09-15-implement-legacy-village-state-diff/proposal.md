## Why

The command recorder now preserves complete before/after legacy village states, but the repository has no deterministic way to describe what changed between them. A bounded structural differ is the next roadmap step needed to turn captured state boundaries into reviewable preservation evidence before command replay or protocol cataloging.

## What Changes

- Add an offline Python 3.9-compatible command that compares either two explicit JSON village snapshots or the `before` and `after` boundaries of one schema-version-1 command record.
- Emit a deterministic, value-free structural report describing added, removed, and changed paths with strict JSON types, while preserving exact object keys and positional array semantics.
- Reject unavailable, ambiguous, malformed, non-finite, duplicate-key, unsupported, or resource-limit-exceeding inputs with bounded privacy-safe diagnostics and no partial success report.
- Document and test read-only containment, sensitive-path handling, deterministic serialization, exit status semantics, and the distinction between in-memory transaction boundaries and persisted saves.
- Exclude replay, patch application, domain-aware normalization, ignore rules, progressed-player fixture synthesis, runtime integration, and gameplay changes.

## Capabilities

### New Capabilities

- `legacy-village-state-diff`: Deterministic, privacy-conscious structural comparison of supplied legacy village states and recorded command boundaries.

### Modified Capabilities

None.

## Impact

- Adds a standard-library-only tool, focused tests, and operator documentation under `tools/state-diff/`.
- May add verified command guidance and a documentation link to `AGENTS.md` and `README.md` after the commands are executed successfully.
- Reads existing canonical save fixtures and schema-version-1 recorder records as inputs without modifying them or importing legacy runtime modules.
- Adds no dependency, network, server, browser, Flash, save-migration, Godot, database, or runtime behavior change.
