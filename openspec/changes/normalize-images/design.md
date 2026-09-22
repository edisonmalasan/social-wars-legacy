## Context

Nine M3 slices are complete and archived, covering 19 of 20 census keys. Direct reads show `images` (607 path keys, all values `en`, no patch interaction, no references) is the final stored-content key. This design scopes the planning artifacts for the tenth and final M3 content slice. Scope is the normalized path registry plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code, no asset conversion. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Normalized `images.json` (607) with `legacy_id` as the verbatim path, source, content version, and locale, in stored document order.
- JSON schema for image-asset definitions; stdlib-only builder/validator extension with patch-drift and active-mod guards.
- Round-trip evidence (legacy-shaped re-emission diffed exactly) and manifest `images` section merged without touching prior keys, completing 20/20 census-key coverage.
- Focused regression tests for classification, verbatim fidelity, validation failures, round-trip, manifest merge, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No asset-existence checks: paths are never stat'ed against disk (M4 owns asset truth).
- No path normalization: leading-slash and relative forms are preserved exactly as stored, never rewritten.
- No SWF execution or conversion: the 10 swf paths are recorded references only.
- No Godot loading code or gameplay code.
- No claim of M3 exit beyond stored-content coverage, gameplay parity, or progressed-player coverage.

## Decisions

- **Stored content is the input; no layering.** No active patch targets `images` (verified against the census patch table), so the builder reads the stored object directly, with the same patch-drift guard and active-mods refusal as prior no-layering builders.
- **Paths are identity and stay verbatim.** `legacy_id` is the stored key exactly (slashes, case, and extension untouched); output order follows stored document order; round-trip rebuilds the keyed object exactly.
- **Locale `en` is enforced, not assumed.** Every value must be exactly the string `en`; anything else fails as drift with the offending path identified. Extension distribution is recorded (jpg/png/swf counts) without enforcement.
- **Schemas are contracts; hand-rolled validator with traceability.** Same pattern as prior slices.
- **Small domain module.** Add an images builder module plus tests alongside the existing package tooling; no new dependencies.

## Risks / Trade-offs

- [Path-form variance] → Leading-slash and relative forms coexist; both are preserved and counted, never unified — unification belongs to M4 if ever.
- [Locale brittleness] → A future non-`en` locale fails the build until re-censused — by design.
- [Future patch drift] → Any new patch targeting `images` fails the build explicitly until re-censused.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.

## Migration Plan

Not applicable: additive normalized outputs plus manifest merge; no legacy migration, no rollout, no rollback beyond reverting the new files.
