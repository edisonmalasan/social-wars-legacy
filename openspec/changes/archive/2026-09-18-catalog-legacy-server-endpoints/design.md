## Context

The recorder, replay, and state-diff capabilities are verified. The proposal on this branch inventories the legacy server's endpoints from `server.py` source; `design.md` previously held only a probe placeholder, and `tasks.md` did not exist. This design completes the planning artifacts. Scope is documentation and read-only tooling; no server behavior changes. Runtime evidence comes from the existing preservation tools; no new execution evidence is captured here.

## Goals / Non-Goals

**Goals:**
- A reviewed, machine-readable endpoint catalog (`endpoints.json`) and readable documentation (`endpoints.md`) covering all 15 explicit active routes, Flask's implicit static registration, and three commented-out auction declarations.
- An offline, read-only verifier (`tools/endpoint-catalog/verify_endpoints.py`) that confirms catalog coverage against the current source without importing the legacy application.
- Focused regression tests for extraction, drift detection, and containment.

**Non-Goals:**
- No modification of any legacy handler, route, or behavior.
- No command catalog, content normalization, or modern API work.
- No HTTP execution, network, browser, or Flash activity.
- No claim of M1 or M2 milestone exit.

## Decisions

- **Static source analysis only.** The verifier parses route registrations from `server.py` using the same inert-AST approach validated during proposal probing: read the file, parse with `ast`, resolve string constants and concatenations for route paths, and never import or execute `server.py`. Alternative (importing the Flask app) was rejected because it executes legacy module side effects (save loading) and violates the preservation-containment rule.

- **Catalog is data; verifier checks consistency.** `endpoints.json` is a reviewed hand-maintained catalog with schema version, classification fields (explicit_active, framework_default, disabled), declared methods, effective method derivation notes, inputs, response branches, state effects, and source references. The verifier recomputes the active-route set from source and diffs it against the catalog; it also cross-checks that `endpoints.md` stays consistent with the JSON.

- **Exit codes follow the established tooling convention.** Exit 0 = agreement, 1 = catalog drift, 2 = invalid input or unsupported registration syntax — matching the state-diff and hash-manifest conventions already documented in AGENTS.md.

- **Small domain module.** One `tools/endpoint-catalog/verify_endpoints.py` plus `test_endpoint_catalog.py`; no giant dispatcher, no new dependencies.

## Risks / Trade-offs

- [Source drift between review and merge] → The verifier reruns on every focused check; any route/method change exits 1 and blocks until the catalog is reviewed again.
- [AST resolution misses dynamic route construction] → Unsupported constructs raise an explicit error (exit 2) instead of silently omitting routes; the proposal documents the supported expression forms (constants and string concatenation).
- [Placeholder drift in endpoints.md] → The verifier cross-checks the readable inventory against the JSON; a mismatch exits 1.
