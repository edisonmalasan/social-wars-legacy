## Context

The endpoint catalog, command catalog, content census, recorder, replay, and state-diff capabilities are verified and archived. Direct reads show `config/main.json` is overwhelmingly string-encoded (43,544 strings vs 2,997 numbers, zero booleans), with `items` fully string-encoded and `goals`/`magics`/`levels` mixed. This design scopes the planning artifacts. Scope is documentation and read-only tooling; no content or behavior changes. No new execution evidence is captured here.

## Goals / Non-Goals

**Goals:**
- A reviewed, machine-readable field-type survey (`field-types.json`) and readable documentation (`field-types.md`) covering per-field encoding profiles for the 15 array-of-object keys and value-shape profiles for the 5 object keys.
- An offline, read-only verifier (`tools/field-survey/verify_fields.py`) that recomputes every profile from `config/main.json` without importing the legacy application.
- Focused regression tests for extraction, predicates, drift detection, and containment.

**Non-Goals:**
- No modification of any content file or behavior.
- No coercion rules, defaults, schemas, normalization, ID reassignment, or `packages/game-content` scaffolding — those are future changes that will consume this survey.
- No HTTP execution, network, browser, or Flash activity.
- No claim of M1 or M2 milestone exit, content validity, or gameplay parity.

## Decisions

- **Exact recomputation, never sampling.** Every profile count is recomputed over all entries with the standard library, so verification is deterministic and byte-identical across runs. Alternative (sampling large keys like `items`) was rejected because samples cannot support exact drift detection.
- **Fixed deterministic predicates.** String-encoded number: full match against a numeric grammar (optional sign, digits, optional fraction/exponent; no surrounding whitespace). Embedded JSON: parses with `json.loads`. Both are pure functions shared by design between verifier and tests, so predicate edge cases are unit-testable without fixtures.
- **Survey is data; verifier checks consistency.** `field-types.json` is a reviewed hand-maintained survey with schema version, per-key profiles, and source references. The verifier recomputes profiles from source and diffs them; it also cross-checks that `field-types.md` stays consistent with the JSON.
- **Exit codes follow the established tooling convention.** Exit 0 = agreement, 1 = survey drift, 2 = invalid input or unsupported content shape — matching the census, catalog, state-diff, and hash-manifest conventions already documented in AGENTS.md.
- **Small domain module.** One `tools/field-survey/verify_fields.py` plus `test_field_survey.py`; no new dependencies.

## Risks / Trade-offs

- [Source drift between review and merge] → The verifier reruns on every focused check; any profile change exits 1 and blocks until the survey is reviewed again.
- [Large content file] → `main.json` is ~1.7 MB; the verifier parses once with explicit size caps and never writes transformed copies into the repository.
- [Predicate edge cases] → Strings like `" 12"`, `"0x10"`, `"1,000"`, `"Infinity"`, or `"null"` must classify deterministically; the numeric grammar excludes them (verified by focused predicate tests) and embedded-JSON detection relies solely on `json.loads` success.
- [Readable-inventory drift in field-types.md] → The verifier cross-checks the readable inventory against the JSON; a mismatch exits 1.
