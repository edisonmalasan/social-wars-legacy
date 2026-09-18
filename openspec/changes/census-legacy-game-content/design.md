## Context

The endpoint catalog, command catalog, recorder, replay, and state-diff capabilities are verified and archived. The static game content — `config/main.json`, five ordered patches, an inactive mods pipeline, import-time duplicate cleaning, and per-request dynamic derivation — is the next uninventoried surface. This design scopes the planning artifacts. Scope is documentation and read-only tooling; no content or behavior changes. No new execution evidence is captured here.

## Goals / Non-Goals

**Goals:**
- A reviewed, machine-readable content census (`census.json`) and readable documentation (`census.md`) covering the 20 top-level content keys, five ordered patches, mods status, duplicate cleaning, and the dynamic-derivation boundary.
- An offline, read-only verifier (`tools/content-census/verify_content.py`) that confirms census coverage against the current sources without importing the legacy application or applying patches.
- Focused regression tests for extraction, drift detection, and containment.

**Non-Goals:**
- No modification of any content file, patch, mod, or behavior.
- No normalization, JSON schemas, ID reassignment, or `packages/game-content` scaffolding — those are future changes that will consume this census.
- No HTTP execution, network, browser, or Flash activity.
- No claim of M1 or M2 milestone exit, content validity, or gameplay parity.

## Decisions

- **Stored sources only; served bytes out of scope.** `make_dynamic` rewrites darts dates from the wall clock at import and per request, so served configuration is nondeterministic across runs. The census records `main.json`, patches, mods status, and the derivation boundary itself — never served output. Alternative (snapshotting served config) was rejected because snapshots would drift with the clock and falsely fail repeat verification.
- **Structural patch analysis, no patch application.** The verifier parses RFC 6902 patch files (ops, paths) with the standard library and checks them against `patches.txt` order; it never imports `jsonpatch` or mutates content. This keeps the tool dependency-free and read-only.
- **Census is data; verifier checks consistency.** `census.json` is a reviewed hand-maintained census with schema version, per-key shapes/counts/ID schemes/asset refs, patch order/op summaries, mods status, derivation notes, and source references. The verifier recomputes key sets, counts, patch order, and mods status from source and diffs them against the census; it also cross-checks that `census.md` stays consistent with the JSON.
- **Exit codes follow the established tooling convention.** Exit 0 = agreement, 1 = census drift, 2 = invalid input or unsupported content shape — matching the endpoint-catalog, command-catalog, state-diff, and hash-manifest conventions already documented in AGENTS.md.
- **Small domain module.** One `tools/content-census/verify_content.py` plus `test_content_census.py`; no new dependencies.

## Risks / Trade-offs

- [Source drift between review and merge] → The verifier reruns on every focused check; any key/count/patch/mods change exits 1 and blocks until the census is reviewed again.
- [Large content file] → `main.json` is ~1.7 MB; the verifier streams structurally via `json.load` with explicit size caps and never writes transformed copies into the repository.
- [ID-scheme ambiguity] → Some keys may use heterogeneous or missing IDs; the census records the observed scheme per key (including "no stable ID") instead of inventing one — normalization decides later.
- [Readable-inventory drift in census.md] → The verifier cross-checks the readable inventory against the JSON; a mismatch exits 1.
