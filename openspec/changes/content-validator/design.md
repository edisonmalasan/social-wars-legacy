# Design

## Context

The committed package (`packages/game-content/`) is produced by ten self-contained builders, each of which enforces its own schema gates, round-trip gates, and reference edges at build time, and is consumed at runtime by Godot's `ContentRegistry`, which verifies the manifest's recorded byte counts and SHA-256 per output at load. Between those two points the package is unexamined: no offline tool applies all 21 schemas to all committed entries, cross-checks the manifest's section records and counts against the files, or re-verifies the cross-domain reference edges the different builders each own a piece of. Roadmap M3 lists "content validator" and "dependency validation" as the two open Deliver lines; §14 names the tool. Constraints: Python 3.9 standard library only, no new dependencies, read-only with respect to every committed byte, no legacy-source reads, and every prior verification must stay green (see proposal.md for guard posture — the package is in no `guard_baseline.py` group and `verify.ps1`'s content digest is pre-vs-post within each run).

## Goals / Non-Goals

**Goals:**

- One offline command that answers "does the committed package conform to its own manifest, schemas, and reference edges?" with an auditable exit code and report.
- Deterministic, byte-stable reports; complete containment (no writes, no legacy reads).
- Test evidence proportional to a validator's claim: every documented check family proven by mutation, every schema-required field proven enforced.

**Non-Goals:**

- Re-deriving or re-emitting content (builders own source fidelity and round-trips; the validator never recomputes `content_fingerprint` or reads `config/`/`mods/`).
- Runtime guarantees (the `ContentRegistry` keeps its own load-time checks untouched).
- A generic JSON-Schema engine: only the documented subset actually used by the committed schemas is implemented.

## Decisions

**D1 — Placement and identity.** The tool lives at `packages/game-content/tools/validate_content.py` with its suite at `packages/game-content/tests/test_validate_content.py`, capability `content-validation`. Alternatives: a repo-level `tools/content-validator/` (rejected — the package already owns its tools, tests, and README extension sections; discovery command `-s packages/game-content/tests` picks the suite up without new wiring) and a Godot-side check (rejected — the runtime layer already covers digests; this change is the offline layer).

**D2 — Self-contained subset checker, no `jsonschema`.** The validator implements the schema subset the builders document: `required`, `type` unions (bool never integer), `const`, `enum`, `minimum`, `minItems`, `minProperties`, `propertyNames`, `additionalProperties: false`, and nested object gates, plus the structural rules for a schema file itself (object schema, `required` ⊆ `properties`, `kind` const present). It never imports the ten builders (they are standalone scripts with domain-private helpers; importing couples build-time code into a read-only checker) and never adds a dependency (package policy: stdlib only). Alternatives considered: importing builder helpers (rejected — coupling and side-effect risk) and `jsonschema` (rejected — new dependency). Parity is anchored by dual-acceptance: the committed package must pass both the builders and this checker, and mutation tests prove the checker actually enforces each gate.

**D3 — Manifest-derived expectations with one mapping table.** The expected file set, digests, byte counts, and section records come from `manifest.json` itself (single source of truth; set equality is manifest-vs-directory in both directions). A single documented mapping table in the tool binds each of the 22 outputs to its schema file and its count keys (the names are not mechanical: `inventory_items` → `inventory_item.schema.json`, `images` → `image_asset.schema.json`, `globals` → `global_entry.schema.json`; `specials.json` maps to its explicit gates instead of a schema).

**D4 — Count checks only where a count names entries.** Per section, the mapping lists which count keys are file-verifiable (`quests: 91`, `buildings: 470`, …) and the rest (`stored_items`, `appended_items`, `reward_values`, `hint_empty`, …) are provenance recorded verbatim and deliberately not compared to files. Alternative: verify every count (rejected — several are build-time statistics with no file counterpart and would force false failures).

**D5 — Exit semantics mirror the builders.** Exit 0 = valid with JSON success report (per-file entry counts, files verified, references checked; no timestamps — determinism). Exit 1 = `validation-failed` report on stdout listing problems sorted by (family, file, entry, field), nothing written. Exit 2 = unusable input on stderr (missing/unreadable/unparseable file, invalid schema, bad usage) — the validator never prints a validity report it cannot back. Alternative: a single non-zero code for everything (rejected — tests and callers need to distinguish "package is broken" from "cannot validate").

**D6 — Reference edges verified two ways: resolution AND derivation.** Every stored reference must (a) resolve against its target domain and (b) equal what the stored source field derives under the owning builder's rule: collections `item_ids` → `item_refs` and `prize` → `prize_refs`, `level_ranking_reward.units` → `unit_refs`, `unit_collection_categories.units` → `unit_refs`, darts pooled `items` → `item_refs` and `extra_item` → `extra_ref`, offers `items`/`items_shape` → `item_refs` (flat leaves, pair firsts, group integer leaves; pair seconds opaque; the pinned anomalies at offer `4` pair second `35` and offer `35` group float `1072.1224` asserted exact, with any other unresolving leaf failing), items `upgrades_to`/`trains_ids` with `-1`/`0` sentinels, `inventory_ids` object keys against the inventory domain, and categories `sub` parents against the categories domain. Ordering (stored vs sorted) is taken from each builder's source during implementation. Alternative: resolution-only (rejected — a resolvable-but-wrong id is exactly the drift the spec's scenario requires catching).

**D7 — Layered API for test speed.** The module exposes load/validate layers with `main(argv)` as a thin wrapper: mutation-matrix and traceability tests call the validate layer in-process on temporary package copies (fast), while exit-code and report-format assertions run the CLI as a subprocess on disposable copies (0 on committed, 1 on a mutation, 2 on a missing file). Temporary copies live under the system temp directory and are removed per test; the committed package is never touched by any test.

**D8 — Determinism by construction.** No wall clock, sorted problem lists, fixed JSON encoding (`sort_keys`, fixed separators) → identical report bytes across runs; the success report's counts double as a cross-check that the tool reads what it claims (tests compare them against independently loaded files).

**D9 — Documentation follows the extension pattern.** The README gains a `content validator` section (invocation, exit codes, evidence classification, containment) matching the ten existing extension sections; `AGENTS.md` gains the two verified commands only after they have actually been executed. Evidence classification: package conformance (manifest, schemas, references) of committed bytes — explicitly not served-byte equality, content validity, asset existence, gameplay parity, or progressed-player coverage.

## Risks / Trade-offs

- [Subset parity drift — the validator accepts or rejects differently from a builder.] Mitigated by D2's dual-acceptance anchor, the mutation matrix covering every documented gate, and explicit replication of non-schema gates (the special, the pinned offer anomalies).
- [A wrong count/schema mapping table causes false failures or missed files.] Mitigated by deriving each mapping entry from the owning builder's source during implementation and a test asserting the table covers all 22 outputs exactly once.
- [Offer traversal diverges from `build_offers.py`'s derivation.] Mitigated by implementing the traversal directly from the builder's source and pinning both anomalies; the committed package passing both tools is the parity anchor.
- [Large mutation matrix runtime.] Mitigated by D7's layered API (in-process mutation, subprocess only for exit codes).
- [Trade-off: the validator reads no legacy sources, so it cannot detect stale outputs whose inputs changed after the last build.] Accepted — build-time source fidelity stays the builders' contract by design; the validator validates the package as committed.

## Migration Plan

Purely additive: no existing file's behavior changes, and rollback is removing the two new files plus the two doc sections. No data migration, no dependency install, no service deploy.

## Open Questions

None — the exit-code split, mapping-table ownership, and reference-derivation sources are all resolved above and feed the task breakdown directly.
