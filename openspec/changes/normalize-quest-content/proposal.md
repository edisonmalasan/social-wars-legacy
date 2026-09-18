## Why

Items normalization proved the M3 pattern (schemas, stdlib builder/validator, round-trip evidence, manifest). The next smallest M3 slice is quest content: `goals` (91 entries) and `collections` (10 entries) are small, structurally simple, and — unlike items — untouched by patches, so no layering logic is needed. Collections cross-reference item IDs, which exercises dependency validation against the normalized items package.

## What Changes

- Add normalized quest definitions under `packages/game-content/`: `normalized/quests.json` (91, from `goals`) and `normalized/collections.json` (10), JSON schemas under `schemas/` (quest, collection), a stdlib-only builder/validator tool extension, and manifest entries recording sources, content version, and legacy IDs.
- Coerce per the field-type survey with documented rules: `collections` string IDs and `cashPrice` to numbers, `item_ids`/`prize` embedded-JSON strings to structures, `goals` native IDs kept, uniform `hint` (`""` in all 91) and uniform `reward` (10 in all 91) preserved verbatim with recorded notes. Every definition preserves `legacy_id`.
- Normalize from stored content directly (no patch targets `goals` or `collections`; the builder still refuses active mods). Cross-reference validation resolves collection `item_ids` and `prize` keys against the normalized items legacy-ID set (470+429+1).
- Validate: duplicate IDs, unresolvable item references, bad cost/price values, required schema fields, and schema-validator traceability. Round-trip evidence: re-emitted legacy-shaped entries diffed against stored content modulo documented coercions.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `goals` entries | 91; native integer `id`; `title`/`description` strings; `hint` empty in all 91; `reward` uniformly 10 |
| `collections` entries | 10; string `id`; `item_ids` always an embedded-JSON integer array string; `prize` always a single-key embedded-JSON object string; `cashPrice` string-encoded number |
| Reference resolution | All 10 collections' `item_ids` and `prize` keys resolve against stored item IDs (0 unresolved) |
| Patch interaction | None: no active patch targets `goals` or `collections`; mods pipeline must stay inactive |
| Served bytes | Out of scope (quest content is not touched by `make_dynamic`) |

## Capabilities

### New Capabilities

- `quest-normalization`: Normalized quest and collection definitions with schemas, builder/validator, cross-domain reference checks, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (normalized quests/collections, schemas, builder/validator, manifest) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Other content keys (research timers are state, not content; missions, offers, magics) and Godot loading remain future work; this change does not claim them.
