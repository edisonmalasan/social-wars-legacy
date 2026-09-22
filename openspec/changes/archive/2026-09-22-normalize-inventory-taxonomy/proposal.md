## Why

Five M3 slices (items, quests, reference tables, economy schedules, social tables) proved the normalization pattern for array-keyed content. The next smallest coherent slice is the object-keyed classification content the game reads but no patch ever mutates: `inventory_items` (90 inventory definitions), `categories` (6 shop-taxonomy groups), and `units_collections_categories` (20 unit-collection groups). Together 116 entries sharing one new object-key preservation pattern plus two clean item-reference edges — the cheapest remaining normalization with the same round-trip guarantees.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/inventory_items.json` (90), `normalized/categories.json` (6), `normalized/unit_collection_categories.json` (20), JSON schemas under `schemas/` (inventory-item, category, unit-collection-category), a stdlib-only builder/validator tool extension, and manifest entries recording sources, content version, and legacy IDs.
- Coerce per the field-type survey with documented rules: `inventory_items` string-encoded numerics (`id`, `cashPrice`, `droppable`, `dropRate`, `dropsFrom`) to integers with display strings verbatim; `categories` integer ids and localized names verbatim with `sub` arrays carried as observed; `units_collections_categories` native integers verbatim, localized names verbatim (uniformly-empty `category_name_el` preserved with a note), `units` integer arrays validated against the normalized items legacy-ID set, and the single null `costs` (key `1`) preserved as null with a note. Every definition preserves `legacy_id` as the stored object key verbatim.
- Normalize from stored content directly (no patch targets any of the three keys; the builder refuses patch drift and active mods explicitly).
- Validate: key uniqueness, non-negative amounts, unresolvable `units` references, item `inventory_ids`-key resolvability spot evidence, required schema fields, and schema-validator traceability. Stored item `category_id`/`subcategory_id` codes 6/7/8/9/81/91 have no category entry and are carried as opaque codes with a manifest note (items-`best_against` precedent), never treated as references and never failing the build. Round-trip evidence: re-emitted legacy-shaped objects diffed against stored content modulo documented coercions.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `inventory_items` entries | 90; object keyed `1`..`90`; every value carries the same 7 string fields (`id`, `name`, `cashPrice`, `droppable`, `dropRate`, `dropsFrom`, `description`); numeric ids/prices string-encoded |
| `inventory_ids` edge | 775 stored `items` entries carry the `null` string, 3 carry embedded-JSON objects, all patch-appended entries carry `null`; every object key resolves against the 90 inventory keys (0 missing at proposal time) |
| `categories` entries | 6; object keyed `1`,`2`,`3`,`4`,`5`,`12`; every value carries integer `id`, string `name`, and a `sub` array of `{id,name,parent}` (5,4,5,4,1,3 entries); item category codes 6/7/8/9 and subcategory codes 6/7/81/91 (patch-era units) have no entry — opaque codes with a note |
| `units_collections_categories` entries | 20; non-sequential keys; uniform 14-field values; `units` holds 89 total integer item ids, all resolving against the loaded 900 items legacy-ID set (0 missing at proposal time); `costs` is a numeric array in 19 entries and null in key `1`; `rewards` uniform 0; `category_name_el` empty in all 20 |
| Patch interaction | None: no active patch targets any of the three keys; mods pipeline must stay inactive |
| Cross-references | Two validated edges: inventory `units`-style object keys are not refs, but `units_collections_categories.units` integers and `items.inventory_ids` object keys resolve against items/inventory sets; category codes are opaque, not refs |
| Served bytes | Out of scope |

## Capabilities

### New Capabilities

- `inventory-taxonomy-normalization`: Normalized inventory, shop-taxonomy, and unit-collection definitions with schemas, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (three normalized files, three schemas, builder/validator, manifest `taxonomy` section) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Offer packs (heterogeneous/nested with a stored float artifact), globals, images, darts dynamics, domain model, and Godot loading remain future work; this change does not claim them.
