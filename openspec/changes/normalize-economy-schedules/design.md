## Context

Items, quest, and reference-tables normalization are complete and archived (builders, schemas, round-trip gates, manifest with items+quests+tables sections). Direct reads show `expansion_prices` (98, fully native), `town_prices` (4, fully native), `map_prices` (4, fully native, identical values to town as stored), and `level_ranking_reward` (50, native level/cash plus native single-entry units objects) need no patch layering and carry exactly one cross-domain edge (ranking units → items). This design scopes the planning artifacts for the fourth M3 normalization slice. Scope is the normalized economy schedules plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Normalized `expansion_prices.json` (98), `town_prices.json` (4), `map_prices.json` (4), `level_ranking_reward.json` (50) with `legacy_id`, source, content version, verbatim native fields, and resolved ranking unit references.
- JSON schemas for expansion-price, town-price, map-price, and level-ranking-reward definitions; stdlib-only builder/validator extension with patch-drift and active-mod guards plus the quest-precedent items reference edge for ranking rewards.
- Round-trip evidence (legacy-shaped re-emission diffed; expected exact equality since all fields are native) and manifest `economy` section merged without touching items/quests/tables keys.
- Focused regression tests for classification, verbatim fidelity, validation failures, round-trip, manifest merge, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No offer packs (heterogeneous/nested shapes with a stored float artifact need their own analysis), globals, inventory/taxonomy, images, darts dynamics, social tables, or other content domains.
- No asset-existence validation (M4 owns asset truth); ranking unit keys are content references, not file assets.
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Stored content is the input; no layering.** No active patch targets any of the four keys (verified against the census patch table: `atom_fusion_*` target `items`/`globals`, `targets` replaces `darts_items`), so the builder reads stored values directly, with the same patch-drift guard and active-mods refusal as the tables builder. Schedule order is positional and preserved; town/map identity of values is preserved verbatim, never deduplicated.
- **`legacy_id` is positional for prices, `level`-valued for ranking rewards.** Price schedules carry no stable stored ID (like `levels`), so `legacy_id` is the 0-based positional index as a string with a numeric position field; ranking rows carry integer `level` 50..1, so `legacy_id` is the decimal level string. This matches the legacy positional loader for schedules and the explicit level key for rewards.
- **Ranking units reuse the quest reference edge.** The builder reads the committed normalized items outputs (900 union legacy IDs) and every ranking `units` key must resolve or validation fails — the same fail-closed pattern as quest `item_refs`/`prize_refs`. Price schedules carry no references and need no edge.
- **Schemas are contracts; hand-rolled validator with traceability.** Same pattern as items/quests/tables: stdlib has no JSON-Schema validator, so the builder enforces requirements directly and a traceability test asserts every schema-required field has a validator check.
- **Round-trip diff is the fidelity gate.** Same pattern: re-emitted entries must equal stored entries exactly (all fields native, so no coercion modulo is expected); any difference fails the build.
- **Small domain module.** Add an economy builder module plus tests alongside the existing package tooling; no new dependencies.

## Risks / Trade-offs

- [Town/map value identity] → Stored values are identical but semantically distinct schedules; the builder preserves both files verbatim and never merges them, with a manifest note recording the observation.
- [Ranking level coverage] → Levels must be exactly 50..1 with no gaps or duplicates; any drift fails validation rather than being repaired.
- [Future patch drift] → Any new patch targeting these keys fails the build explicitly until re-censused.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.

## Migration Plan

Not applicable: additive normalized outputs plus manifest merge; no legacy migration, no rollout, no rollback beyond reverting the new files.
