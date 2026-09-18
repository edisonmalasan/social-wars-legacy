## Context

The endpoint catalog, recorder, replay, and state-diff capabilities are verified and archived. The dispatcher in `command.py` (956 lines, 63 named branches plus an unhandled fallthrough; the proposal first estimated 64) is the next undocumented behavioral surface. This design scopes the planning artifacts. Scope is documentation and read-only tooling; no dispatcher behavior changes. Runtime evidence comes from the existing recorder/replay tools covering four commands; no new execution evidence is captured here.

## Goals / Non-Goals

**Goals:**
- A reviewed, machine-readable command catalog (`commands.json`) and readable documentation (`commands.md`) covering the envelope contract, all 63 named commands, and the unhandled fallthrough.
- An offline, read-only verifier (`tools/command-catalog/verify_commands.py`) that confirms catalog coverage against the current source without importing the legacy application.
- Focused regression tests for extraction, drift detection, and containment.

**Non-Goals:**
- No modification of any legacy handler, branch, or behavior.
- No content normalization, modern API, or domain migration work.
- No HTTP execution, network, browser, or Flash activity.
- No claim of M1 or M2 milestone exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Static source analysis only.** The verifier parses dispatcher branches from `command.py` using inert-AST analysis of the `if cmd ==` / `elif cmd ==` chain: read the file, parse with `ast`, compare string constants only, and never import or execute `command.py`. Alternative (importing the dispatcher) was rejected because it executes legacy module side effects (config patching, save loading) and violates the preservation-containment rule.
- **Catalog is data; verifier checks consistency.** `commands.json` is a reviewed hand-maintained catalog with schema version, classification fields (handled, fallthrough), envelope contract, domain, argument shapes, resource effects, state reads/writes, persistence effects, client-trust notes, and source references. The verifier recomputes the branch set from source and diffs it against the catalog; it also cross-checks that `commands.md` stays consistent with the JSON.
- **Exit codes follow the established tooling convention.** Exit 0 = agreement, 1 = catalog drift, 2 = invalid input or unsupported dispatch syntax — matching the endpoint-catalog, state-diff, and hash-manifest conventions already documented in AGENTS.md.
- **Small domain module.** One `tools/command-catalog/verify_commands.py` plus `test_command_catalog.py`; no giant dispatcher, no new dependencies.

## Risks / Trade-offs

- [Source drift between review and merge] → The verifier reruns on every focused check; any branch/envelope change exits 1 and blocks until the catalog is reviewed again.
- [AST resolution misses dynamic dispatch] → Any non-literal command comparison raises an explicit error (exit 2) instead of silently omitting commands.
- [Argument-shape drift in commands.md] → The verifier cross-checks the readable inventory against the JSON; a mismatch exits 1.
- [Catalog size] → 64 entries is large for hand review; the verifier's per-command coverage diff plus the focused consistency tests are the review mechanism, and domain grouping in `commands.md` keeps the readable view navigable.
