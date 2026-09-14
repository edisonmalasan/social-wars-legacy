## Why

M0 preservation requires canonical save evidence before legacy persistence behavior can be reproduced or replaced. The repository contains no tracked authentic player saves, but its fresh-player creation and migration path can be captured reproducibly now without relabeling static neighbor data as player history.

## What Changes

- Add a deterministic, repository-contained workflow that captures the legacy fresh-player save and its migration boundary using the actual legacy save creation and migration code with controlled UUID and time inputs.
- Commit the canonical fresh-player fixtures and a machine-readable provenance manifest that records immutable source identities, capture controls, file hashes, and sizes.
- Add read-only verification and focused tests for deterministic regeneration, full-state migration fidelity, manifest integrity, and containment outside the ignored runtime `saves/` directory.
- Document exactly which save states are verified and explicitly record early-, mid-, late-game, and stress-town player saves as unavailable and unverified.
- Preserve raw templates and static neighbor states unchanged; they are evidence inputs, not substitutes for observed player saves.

## Capabilities

### New Capabilities

- `legacy-save-fixtures`: Deterministic capture, provenance, integrity verification, and coverage classification for canonical legacy save fixtures.

### Modified Capabilities

None.

## Impact

This change affects preservation tooling, fixture data under `tests/saves/`, focused tests, and documentation. It does not change legacy application behavior, dependencies, runtime save files, source templates, static neighbor data, or any Flash/SWF artifact, and it does not begin protocol capture or modern client work.
