## Why

The repository can record legacy command boundaries and structurally compare village states, but it cannot yet rerun a captured command against its recorded before-state to test whether the preserved legacy oracle reproduces the observed result. A deliberately small contained replay slice is the next M2 step before broader command discovery or compatibility work.

## What Changes

- Add an offline replay command for one explicitly supplied schema-version-1 command record whose batch contains only `complete_tutorial`, `level_up`, `ping`, or `set_variables`.
- Execute the pinned legacy dispatcher in a disposable isolated child with a fixed sentinel clock, bounded resources, redirected persistence, and no ambient save discovery, server, network, browser, or Flash activity.
- Compare the complete replayed in-memory state, normalized outcome, response contract, and success/failure persistence behavior with recorded evidence.
- Emit a deterministic value-free private report for matches and mismatches, while rejecting invalid, unavailable, unsupported, redacted execution data, provenance drift, ambiguous protected paths, containment failures, and child failures categorically.
- Exclude generalized command coverage, recorded-time reconstruction, raw HTTP replay, capture or fixture promotion, endpoint/command catalogs, and modern runtime work.

## Capabilities

### New Capabilities

- `legacy-command-replay`: Contained, provenance-pinned replay and full-boundary comparison for a bounded clock-independent subset of legacy command records.

### Modified Capabilities

None.

## Impact

- Adds a Python 3.9-compatible replay tool, pinned oracle manifest, focused tests, and operator documentation under `tools/protocol-replay/`.
- Reuses the existing structural comparison policy without changing its CLI or durable requirements.
- Reads recorder-v1 evidence and approved legacy sources as inputs; it never writes repository saves, canonical fixtures, recorder evidence, or legacy sources.
- Adds no dependency, server route, runtime behavior, gameplay change, Flash execution, Godot code, database work, or catalog generation.
