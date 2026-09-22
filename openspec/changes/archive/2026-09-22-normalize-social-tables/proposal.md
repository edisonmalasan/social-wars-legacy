## Why

Items, quest, reference-tables, and economy-schedules normalization proved the M3 pattern. The next smallest coherent slice is the small social/ambient lookup tables the game reads but no patch ever mutates: `neighbor_assists` (5 help-task definitions), `findable_items` (10 park-findable definitions), and `social_items` (26 hireable-worker definitions). Together 41 entries with simple fully-native-plus-string shapes and no cross-references — the cheapest remaining normalization with the same round-trip guarantees.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/neighbor_assists.json` (5), `normalized/findable_items.json` (10), `normalized/social_items.json` (26), JSON schemas under `schemas/` (neighbor-assist, findable-item, social-item), a stdlib-only builder/validator tool extension, and manifest entries recording sources, content version, and legacy IDs.
- Coerce per the field-type survey with documented rules: native integers kept verbatim (`rnd`, reward amounts, `id`, `coins`, `worker_cost`); display strings kept verbatim (`task`/`action`/`notification`, `title`/`description`, `workers`); the uniformly-empty `description` in all 26 `social_items` entries is preserved verbatim with a manifest note, never defaulted or dropped (quest-`hint` precedent). Every definition preserves `legacy_id` (positional index for neighbor assists, which carry no stable id; decimal id for findables and social items).
- Normalize from stored content directly (no patch targets any of the three keys; the builder refuses patch drift and active mods explicitly).
- Validate: positional/id uniqueness, non-negative amounts, required schema fields, and schema-validator traceability. Round-trip evidence: re-emitted legacy-shaped entries diffed against stored content exactly (expected: exact equality, since every field is native or verbatim string).
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `neighbor_assists` entries | 5; uniform keys `action`/`notification`/`reward`/`rnd`/`task`; `reward` is a native object uniform `{coins:50,cash:0,xp:15}` in all 5; `rnd` uniform 0; no stable ID, positional index preserved |
| `findable_items` entries | 10; uniform keys `coins`/`description`/`id`/`title`; native integer `id` sequential 1..10; `coins` uniform 100; `title`/`description` display strings verbatim |
| `social_items` entries | 26; uniform keys `description`/`id`/`workers`/`worker_cost`; native integer `id` non-sequential; `worker_cost` in {1,2,3}; `workers` non-empty name strings verbatim; `description` empty in all 26, preserved with a note |
| Patch interaction | None: no active patch targets any of the three keys (`atom_fusion_*` target `items`/`globals`, `targets` replaces `darts_items`); mods pipeline must stay inactive |
| Cross-references | None: reward amounts are coins/cash/xp literals and `workers` strings are display names, not item IDs |
| Served bytes | Out of scope |

## Capabilities

### New Capabilities

- `social-tables-normalization`: Normalized neighbor-assist, findable-item, and social-item definitions with schemas, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (three normalized files, three schemas, builder/validator, manifest `social` section) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Offer packs (heterogeneous/nested with a stored float artifact), globals, inventory/taxonomy objects, images, darts dynamics, unit-collection categories, domain model, and Godot loading remain future work; this change does not claim them.
