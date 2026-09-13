## Why

The preservation roadmap requires an immutable name for the untouched legacy repository revision before modernization work begins. No local or remote `legacy-baseline` tag currently exists, so later migration work cannot identify the agreed behavioral-oracle baseline unambiguously.

## What Changes

- Create the lightweight Git tag `legacy-baseline` at the repository revision recorded during planning (`e8c98a0`).
- Verify that the tag resolves to that exact commit and does not alter tracked files or preserved assets.
- Record the completed preservation step in the roadmap Project Status ledger.

## Capabilities

### New Capabilities

None. This is repository preservation metadata, not product behavior.

### Modified Capabilities

None. The change opts out of delta specs because it changes no runtime behavior.

## Impact

The change affects Git refs and the root-owned Project Status block only. It changes no application code, dependencies, APIs, saves, configuration, or legacy assets. The tag name is fixed by the M0 roadmap.
