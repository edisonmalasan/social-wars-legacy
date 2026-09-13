## Why

M0 requires evidence-backed environment and startup documentation before the legacy implementation can be treated as reproducible. Existing operator notes cover basic play setup, but they do not record the baseline revision, source-runtime dependencies and gaps, directory expectations, bootstrap sequence, default save state, content/client versions, or a classified list of known limitations.

## What Changes

- Add `docs/legacy-baseline.md` as the preservation record for the `legacy-baseline` tag, including provenance, historical/runtime version evidence, operating-system expectations, source and packaged startup flows, ports, paths, configuration, default player/save behavior, Flash bootstrap URLs, and asset/content versions.
- Add `docs/known-legacy-bugs.md` with source-evidenced bugs, disabled or incomplete features, compatibility risks, and explicitly unverified observations; do not present static inferences as reproduced failures.
- Link the new preservation documents from `README.md` without replacing the existing player-facing installation guidance.
- State that clean-machine reproduction remains unverified until the separately scoped dependency-lock change supplies and tests complete pinned dependencies.
- Preserve all application behavior, dependencies, assets, saves, configuration, and historical documentation unchanged.

## Capabilities

### New Capabilities

None. This is a documentation-only preservation change.

### Modified Capabilities

None. The change opts out of delta specs because it changes no runtime behavior.

## Impact

Only `docs/legacy-baseline.md`, `docs/known-legacy-bugs.md`, the README documentation index, the OpenSpec change artifacts, and the root-owned roadmap Project Status block are affected. Dependency locking, package installation, runtime fixes, executable rebuilding, asset hashing, save-fixture creation, protocol cataloging, and Flash retirement are explicit non-goals.
