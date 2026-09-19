## Context

Items normalization is complete and archived (470 buildings, 429 units, 1 special, schemas, builder/validator, round-trip gate, manifest). Direct reads show `goals` (91, native IDs, uniform hint/reward) and `collections` (10, string IDs, embedded-JSON item references resolving cleanly against item IDs) need no patch layering. This design scopes the planning artifacts for the second M3 normalization slice. Scope is the normalized quest package plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code.

## Goals / Non-Goals

**Goals:**
- Normalized `quests.json` (91) and `collections.json` (10) with `legacy_id`, source, content version, coerced fields, and resolved item references.
- JSON schemas for quest and collection definitions; stdlib-only builder/validator extension with cross-domain reference checks against the normalized items ID set.
- Round-trip evidence (legacy-shaped re-emission diffed modulo coercions) and manifest entries.
- Focused regression tests for classification, coercion, validation failures, round-trip, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No research timers (runtime state, not content), missions, offers, magics, or other content keys.
- No asset-existence validation (M4 owns asset truth).
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Stored content is the input; no layering.** No active patch targets `goals` or `collections` (verified against the census patch table), so the builder reads stored values directly. The active-mods refusal stays as a guard. Alternative (reusing the full items layering path) was rejected as unnecessary complexity; the builder shares only the predicate/coercion helpers' design.
- **Cross-domain resolution against normalized items.** Collection `item_ids`/`prize` keys must resolve against the union of normalized items legacy IDs (470+429+1), read from the built package outputs — this is the first dependency-validation edge and directly serves the M3 exit. Unresolvable references fail validation.
- **Uniform fields preserved with notes.** `hint` (empty ×91) and `reward` (10 ×91) are stored facts, not redundancy; dropping them would lose round-trip fidelity. Notes record the uniformity.
- **Schemas are contracts; hand-rolled validator with traceability.** Same pattern as items: stdlib has no JSON-Schema validator, so the builder enforces requirements directly and a traceability test asserts every schema-required field has a validator check.
- **Round-trip diff is the fidelity gate.** Same pattern as items: re-emitted entries must equal stored entries except documented coercions.
- **Small domain module.** Extend the existing package tooling with a quest builder module plus tests; no new dependencies.

## Risks / Trade-offs

- [Items package drift] → Cross-domain checks read the committed normalized items outputs; if those change shape, quest validation fails explicitly until reconciled.
- [Uniform-field semantics] → A future reader might mistake uniform hint/reward for defaults; the recorded notes plus round-trip exactness prevent silent reinterpretation.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.
- [Reference rot] → Any item ID removal in a future items rebuild breaks quest validation loudly rather than producing dangling references.
