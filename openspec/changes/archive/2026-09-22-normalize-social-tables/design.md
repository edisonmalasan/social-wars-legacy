## Context

Items, quest, reference-tables, and economy-schedules normalization are complete and archived (builders, schemas, round-trip gates, manifest with items+quests+tables+economy sections). Direct reads show `neighbor_assists` (5, uniform help tasks with identical rewards), `findable_items` (10, sequential ids with uniform coin rewards), and `social_items` (26, non-sequential ids with uniformly-empty descriptions) need no patch layering and carry no cross-references. This design scopes the planning artifacts for the fifth M3 normalization slice. Scope is the normalized social tables plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Normalized `neighbor_assists.json` (5), `findable_items.json` (10), `social_items.json` (26) with `legacy_id`, source, content version, verbatim native amounts, verbatim display strings, and recorded uniformity notes.
- JSON schemas for neighbor-assist, findable-item, and social-item definitions; stdlib-only builder/validator extension with patch-drift and active-mod guards.
- Round-trip evidence (legacy-shaped re-emission diffed; expected exact equality) and manifest `social` section merged without touching items/quests/tables/economy keys.
- Focused regression tests for classification, verbatim fidelity, validation failures, round-trip, manifest merge, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No offer packs (heterogeneous/nested shapes with a stored float artifact need their own analysis), globals, inventory/taxonomy objects, images, darts dynamics, unit-collection categories, or other content domains.
- No social-graph or hiring-behavior implementation; worker names and reward amounts are carried as observed data, never interpreted as behavior.
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Stored content is the input; no layering.** No active patch targets any of the three keys (verified against the census patch table), so the builder reads stored values directly, with the same patch-drift guard and active-mods refusal as the economy builder.
- **`legacy_id` is positional for assists, id-valued for findables and social items.** Neighbor assists carry no stable stored ID (like price schedules), so `legacy_id` is the 0-based positional index with a numeric position field; findables and social items carry native integer ids, so `legacy_id` is the decimal id string (quest-precedent pattern).
- **Uniform values preserved, never normalized away.** The identical assist rewards, uniform findable coins, uniform assist `rnd`, and uniformly-empty social descriptions are carried verbatim with manifest notes; uniformity is an observation, not a default to factor out.
- **Schemas are contracts; hand-rolled validator with traceability.** Same pattern as prior slices: stdlib has no JSON-Schema validator, so the builder enforces requirements directly and a traceability test asserts every schema-required field has a validator check.
- **Round-trip diff is the fidelity gate.** Same pattern: re-emitted entries must equal stored entries exactly.
- **Small domain module.** Add a social builder module plus tests alongside the existing package tooling; no new dependencies.

## Risks / Trade-offs

- [Uniformity semantics] → Uniform rewards/coins/descriptions are preserved verbatim with notes; no per-row distinctness is inferred and no uniformity is enforced on future content (any drift is carried, not failed, except schema-type violations).
- [Worker-name semantics] → `workers` strings are display data, never parsed as references or behavior; hiring logic belongs to a later gameplay change.
- [Future patch drift] → Any new patch targeting these keys fails the build explicitly until re-censused.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.

## Migration Plan

Not applicable: additive normalized outputs plus manifest merge; no legacy migration, no rollout, no rollback beyond reverting the new files.
