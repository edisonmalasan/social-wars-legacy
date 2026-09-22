## Why

Items, quest, and reference-tables normalization proved the M3 pattern. The next smallest coherent slice is the static economy schedules the game reads but no patch ever mutates: `expansion_prices` (98-entry town-expansion price ladder), `town_prices` (4-entry town unlock schedule), `map_prices` (4-entry map unlock schedule), and `level_ranking_reward` (50-entry level-ranking reward table). Together 156 entries with fully native shapes and a single proven item-reference edge — the cheapest remaining normalization with the same round-trip guarantees.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/expansion_prices.json` (98), `normalized/town_prices.json` (4), `normalized/map_prices.json` (4), `normalized/level_ranking_reward.json` (50), JSON schemas under `schemas/` (expansion-price, town-price, map-price, level-ranking-reward), a stdlib-only builder/validator tool extension, and manifest entries recording sources, content version, and legacy IDs.
- Coerce per the field-type survey with documented rules: all four keys are fully native numbers/objects kept verbatim — no string-encoded numbers, no embedded JSON, no empty strings; `level_ranking_reward.units` is a native single-entry object mapping item-id keys to integer quantities, validated against the normalized items legacy-ID set (the quest-precedent cross-domain edge). Every definition preserves `legacy_id` (positional index for the three price schedules, `level` value for ranking rewards); schedule order is preserved positionally.
- Normalize from stored content directly (no patch targets any of the four keys; the builder refuses patch drift and active mods explicitly).
- Validate: positional uniqueness, non-negative amounts, level coverage 50..1 for ranking rewards, unresolvable ranking unit references, required schema fields, and schema-validator traceability. Round-trip evidence: re-emitted legacy-shaped entries diffed against stored content modulo documented coercions (expected: exact equality).
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `expansion_prices` entries | 98; fully native; every entry carries `coins`/`cash`/`neighbors`/`inventory_qte` as JSON numbers; no stable ID, positional index is the expansion step; first `{coins:0,cash:0,neighbors:0,inventory_qte:0}`, last `{coins:100000,cash:20,neighbors:15,inventory_qte:30}`; no negatives |
| `town_prices` entries | 4; fully native; every entry carries `coins`/`cash`/`level` as JSON numbers; levels 15/25/35/45; no stable ID, positional index preserved |
| `map_prices` entries | 4; fully native; identical values to `town_prices` as stored (levels 15/25/35/45); preserved verbatim, never deduplicated against town prices |
| `level_ranking_reward` entries | 50; `level` descending 50..1 with `cash` uniform 1; `units` is a native single-entry object per row (e.g. `{"1016":1}`) with native integer quantities; every unit key resolves against the loaded 900 items legacy-ID set (0 missing at proposal time) |
| Patch interaction | None: no active patch targets any of the four keys (`atom_fusion_*` target `items`/`globals`, `targets` replaces `darts_items`); mods pipeline must stay inactive |
| Cross-references | One edge: ranking `units` keys → normalized items `legacy_id` set (quest-precedent pattern); price schedules carry no item references |
| Served bytes | Out of scope |

## Capabilities

### New Capabilities

- `economy-schedules-normalization`: Normalized expansion/town/map price schedules and level-ranking reward definitions with schemas, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (four normalized files, four schemas, builder/validator, manifest `economy` section) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Offer packs (heterogeneous/nested with a stored float artifact), globals, inventory/taxonomy, images, darts dynamics, social tables, domain model, and Godot loading remain future work; this change does not claim them.
