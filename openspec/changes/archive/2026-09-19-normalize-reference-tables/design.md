## Context

Items and quest normalization are complete and archived (builders, schemas, round-trip gates, manifest with items+quests sections). Direct reads show `magics` (10, mixed native/embedded), `levels` (100, fully native), and `sounds` (139, string-encoded) need no patch layering and carry no cross-references. This design scopes the planning artifacts for the third M3 normalization slice. Scope is the normalized tables plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code.

## Goals / Non-Goals

**Goals:**
- Normalized `magics.json` (10), `levels.json` (100), `sounds.json` (139) with `legacy_id`, source, content version, coerced fields, and recorded asset refs.
- JSON schemas for magic, level, and sound definitions; stdlib-only builder/validator extension with patch-drift and active-mod guards.
- Round-trip evidence (legacy-shaped re-emission diffed modulo coercions) and manifest entries.
- Focused regression tests for classification, coercion, validation failures, round-trip, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No economy tables, remaining misc keys, or other content domains.
- No asset-existence validation (M4 owns asset truth).
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Stored content is the input; no layering.** No active patch targets any of the three keys (verified against the census patch table), so the builder reads stored values directly, with the same patch-drift guard and active-mods refusal as the quest builder. The XP curve order is positional and preserved.
- **Asset names recorded, never validated.** `img_name`/`file` strings are carried verbatim; existence checks belong to the M4 asset pipeline. The schemas type them as strings only.
- **Schemas are contracts; hand-rolled validator with traceability.** Same pattern as items/quests: stdlib has no JSON-Schema validator, so the builder enforces requirements directly and a traceability test asserts every schema-required field has a validator check.
- **Round-trip diff is the fidelity gate.** Same pattern: re-emitted entries must equal stored entries except documented coercions.
- **Small domain module.** Extend the existing package tooling with a tables builder module plus tests; no new dependencies.

## Risks / Trade-offs

- [XP curve semantics] → `exp_required` values are preserved verbatim, including any curve irregularities; the builder notes but never smooths the curve.
- [Mana/cost semantics] → Spell costs are carried as observed amounts; no per-level scaling is inferred.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.
- [Future patch drift] → Any new patch targeting these keys fails the build explicitly until re-censused.
