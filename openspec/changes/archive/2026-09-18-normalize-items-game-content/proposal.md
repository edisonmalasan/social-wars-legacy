## Why

M2 behavioral tooling is complete (recorder, replay, state diff, golden fixtures, plus catalogs, census, and field survey). M3 requires normalized game configuration with schemas, a validator, and a manifest, but the `items` content is stored string-encoded with embedded-JSON costs, upgrade chains, and training references. Normalizing the `items` domain first — the most cross-referenced content key — produces the first Godot-loadable definitions while bounding semantic risk to one domain.

## What Changes

- Add a normalized items content package under `packages/game-content/` with `normalized/buildings.json`, `normalized/units.json`, JSON schemas under `schemas/` (building, unit), a stdlib-only builder/validator tool, and a manifest entry recording sources, content version, and legacy IDs.
- Classify by the stored `type` field: stored `b` (469) plus one patch-appended `b` (id `302`) normalize to 470 buildings; stored `u` (308) plus 121 patch-appended `u` normalize to 429 units; the single `l` entry (id `925`, "Expandable Land") becomes a documented special definition, not a building or unit. All 900 loaded ids are distinct.
- Coerce per the field-type survey with documented rules: numeric strings to numbers, embedded-JSON strings (`costs`, `properties`, `inventory_ids`, `premium_upgrade_costs`) parsed to structures, `""` preserved only where the survey shows it is meaningful (e.g. `best_against`), `cost_type` (null in all 778 entries) dropped with a recorded note. Every definition preserves `legacy_id` (the stored string `id`).
- Normalize from loaded content (stored `main.json` plus the five ordered patches plus duplicate cleaning, mirroring the legacy loader without importing it), never from served bytes.
- Validate: duplicate IDs, `upgrades_to` (194 chains) and `trains_ids` (138 relations) resolving to known definitions, `costs` parsing to known resource keys (`o`, `s`, `g`, `w`, `c`) with non-negative amounts, required fields present per schema, and every schema-required field covered by a validator check (traceability test).
- Round-trip evidence: the builder re-emits legacy-shaped items and diffs them against loaded legacy content modulo documented coercions; unexplained differences fail validation.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `items` entries | 778 stored, string `id`, 778/778 distinct |
| `type` split | `b` 469, `u` 308, `l` 1 (id `925` Expandable Land) |
| `costs` shape | Always a JSON-object string; resource keys exactly `o`, `s`, `g`, `w`, `c` |
| `cost_type` | Null in all 778 entries (dead field, dropped with note) |
| Cross-references | `upgrades_to` non-sentinel in 56 entries (`-1` and `0` mean none; 138 further entries hold `0`); `trains_ids` non-sentinel in 130 entries (8 further entries hold `0`) |
| Load layering | Stored file + 5 ordered patches (which append 122 items and add fields) + keep-later duplicate cleaning |
| Served bytes | Out of scope (`make_dynamic` does not touch `items`, but normalization input is defined as loaded content, never served output) |

## Capabilities

### New Capabilities

- `items-normalization`: Normalized building and unit definitions with schemas, builder/validator, round-trip evidence, and manifest entry for the legacy items domain.

### Modified Capabilities

None.

## Impact

Adds `packages/game-content/` (normalized buildings/units, schemas, builder/validator tool, manifest) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Other content keys (quests, research, collections, missions), asset-existence validation (M4), and Godot loading remain future work; this change does not claim them.
