## Context

Five M3 slices are complete and archived (items, quests, tables, economy, social tables: builders, schemas, round-trip gates, manifest with items+quests+tables+economy+social sections). Direct reads show `inventory_items` (90 string-encoded definitions), `categories` (6 taxonomy groups with sub arrays), and `units_collections_categories` (20 collection groups with item arrays) need no patch layering and carry two clean item-set edges plus one documented opaque-code gap. This design scopes the planning artifacts for the sixth M3 normalization slice and introduces the object-key preservation pattern. Scope is the normalized inventory/taxonomy plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Normalized `inventory_items.json` (90), `categories.json` (6), `unit_collection_categories.json` (20) with `legacy_id` as the stored object key, source, content version, coerced numerics, verbatim display strings, validated unit references, and recorded uniformity/gap notes.
- JSON schemas for inventory-item, category, and unit-collection-category definitions; stdlib-only builder/validator extension with patch-drift and active-mod guards plus the two items-set reference edges.
- Round-trip evidence (legacy-shaped re-emission diffed modulo documented coercions) and manifest `taxonomy` section merged without touching items/quests/tables/economy/social keys.
- Focused regression tests for classification, coercion, validation failures, round-trip, manifest merge, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No offer packs (heterogeneous/nested shapes with a stored float artifact need their own analysis), globals, images, darts dynamics, or other content domains.
- No resolution repair for unresolving item category codes (6/7/8/9/81/91): recorded as opaque codes with a note, following the items-`best_against` precedent.
- No inventory-behavior or shop-behavior implementation; definitions are carried as observed data.
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Stored content is the input; no layering.** No active patch targets any of the three keys (verified against the census patch table), so the builder reads stored values directly, with the same patch-drift guard and active-mods refusal as prior builders.
- **Object keys are the identity.** Unlike array slices with positional or id-valued `legacy_id`, these three keys are JSON objects: `legacy_id` is the stored key verbatim (`1`..`90` for inventory, `1`/`2`/`3`/`4`/`5`/`12` for categories, the 20 non-sequential keys for collections). Output files are arrays of definitions in stored key order (numeric-aware: `12` sorts after `5`), and round-trip rebuilds the keyed object.
- **Two validated edges, one opaque gap.** `units` integers must resolve against the normalized items legacy-ID set and stored `items.inventory_ids` object keys must resolve against the normalized inventory key set (both fail closed, quest-precedent pattern). Item `category_id`/`subcategory_id` codes are carried as opaque integers with a manifest note recording the unresolving patch-era codes; the builder never treats them as references.
- **Null `costs` preserved, never defaulted.** Key `1` of the collections carries JSON null where 19 siblings carry numeric arrays; the schema types it integer-array-or-null and the round-trip asserts exact null preservation.
- **Schemas are contracts; hand-rolled validator with traceability.** Same pattern as prior slices.
- **Round-trip diff is the fidelity gate.** Re-emitted keyed objects must equal stored objects modulo documented coercions (numeric strings numeric, structures parsed, empties exact, key sets exact).
- **Small domain module.** Add a taxonomy builder module plus tests alongside the existing package tooling; no new dependencies.

## Risks / Trade-offs

- [Category-code gap] → Patch-era item category codes without category entries are opaque data, not validation failures; if future content adds the missing groups, the note (not the gate) needs revisiting.
- [Key-order semantics] → Stored key order is preserved as observed; numeric-aware ordering (`12` after `5`) is documented, never re-sorted alphabetically.
- [Future patch drift] → Any new patch targeting these keys fails the build explicitly until re-censused.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.

## Migration Plan

Not applicable: additive normalized outputs plus manifest merge; no legacy migration, no rollout, no rollback beyond reverting the new files.
