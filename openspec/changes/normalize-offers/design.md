## Context

Eight M3 slices are complete and archived, with pinned-anomaly precedent (taxonomy opaque category codes, darts dynamic boundary, economy town/map identity). Direct reads fully characterize `offer_packs` (44 entries): uniform scalars, one null, five flat bundles, 38 nested group pools, and exactly two pinned leaf anomalies. This design scopes the planning artifacts for the ninth M3 normalization slice. Scope is the normalized offers plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Normalized `offer_packs.json` (44) with `legacy_id`, source, content version, verbatim scalars, verbatim item shapes with recorded shape classes, resolved references, and pinned anomaly notes.
- JSON schema for offer-pack definitions; stdlib-only builder/validator extension with patch-drift and active-mod guards plus the items reference edge and the exact-match anomaly allowlist.
- Round-trip evidence (legacy-shaped re-emission diffed exactly against stored content) and manifest `offers` section merged without touching prior keys.
- Focused regression tests for classification, shape handling, validation failures (including non-allowlisted anomalies), round-trip, manifest merge, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No interpretation of pack semantics: flat repetition, pair seconds, and group membership are carried as observed structures, never decoded as quantities, prices, weights, or choice rules (beyond the documented ref/opaque split).
- No repair of the two pinned anomalies: preserved verbatim with notes.
- No `images` asset index or other content domains.
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Stored content is the input; no layering.** No active patch targets `offer_packs` (verified against the census patch table), so the builder reads stored values directly, with the same patch-drift guard and active-mods refusal as prior no-layering builders.
- **Shape classes are recorded, structures preserved.** Each entry records `items_shape`: null, flat, pairs (all subgroups len 2), or groups (any other nested mix). Structures are deep-copied verbatim, including the float artifact.
- **Fail-closed refs with a pinned allowlist.** Flat leaves, pair firsts, and group integer leaves must resolve against the normalized items set; pair seconds must be numbers and are recorded opaque; the allowlist contains exactly `(4, 35)` and `(35, 1072.1224)` matched by offer id and leaf value — the builder asserts both are still exactly as documented and fails on any other unresolving leaf. This keeps the build green on real content without silently absorbing new drift.
- **Schemas are contracts; hand-rolled validator with traceability.** Same pattern as prior slices; `items` is typed as array-or-null with per-shape structural checks in the builder.
- **Round-trip diff is the fidelity gate.** Re-emitted entries must equal stored entries exactly, float artifact included.
- **Small domain module.** Add an offers builder module plus tests alongside the existing package tooling; no new dependencies.

## Risks / Trade-offs

- [Semantic ambiguity] → Pair seconds and group membership are deliberately not interpreted; any future gameplay change specifying pack semantics must revisit these notes, not the preserved structures.
- [Allowlist brittleness] → If stored content ever legitimately changes the two anomalies, the build fails until the allowlist is re-censused — by design, not by accident.
- [Future patch drift] → Any new patch targeting `offer_packs` fails the build explicitly until re-censused.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.

## Migration Plan

Not applicable: additive normalized outputs plus manifest merge; no legacy migration, no rollout, no rollback beyond reverting the new files.
