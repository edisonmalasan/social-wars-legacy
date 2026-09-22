## Why

Seven M3 slices (items, quests, reference tables, economy schedules, social tables, inventory taxonomy, darts schedule) proved the normalization pattern. The next smallest coherent slice is the last heterogeneous tuning domain: `globals` (104 stored constants plus the single `atom_fusion_powerup` add, 105 effective entries). Only three content keys remain after it (offers, images, and no other array/object domain), and the tuning table is the highest-value remainder for future authoritative-server work.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/globals.json` (105, one per loaded entry), a JSON schema (`global-entry` with a value-type union), a stdlib-only builder/validator tool extension, and manifest entries recording sources, patch lineage, content version, and legacy IDs.
- Apply the documented patch layering first (items/darts-builder precedent): verify the ordered patch list, apply only the `atom_fusion_powerup` add of `/globals/SOUL_MIXER_POWERUPS_LEVELS`, and refuse any other globals target or divergent add shape explicitly. Normalize the loaded object, with `source_layer` distinguishing `stored` from `patched(atom_fusion_powerup)`.
- Coerce per the field-type survey with documented rules: every value kept verbatim as observed JSON (62 integers, 4 floats, 8 strings, 8 objects, 22 lists, plus the 6-row patch-added schedule) with its value type recorded; string constants (version lists, URL, date, embedded-JSON-ish depot string, friend-reward CSV strings) carried opaque, never parsed as references or behavior. Every definition preserves `legacy_id` as the constant name.
- Validate: key uniqueness, patch-shape conformity, required schema fields (including the value-type union), and schema-validator traceability. Round-trip evidence: re-emitted loaded-shaped object diffed against the loaded object exactly.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| Stored `globals` | 104 entries: 62 int, 4 float, 8 str, 22 list, 8 dict values |
| Patch interaction | Exactly one: `atom_fusion_powerup` adds `/globals/SOUL_MIXER_POWERUPS_LEVELS` (6 rows of `{cash_cost,order_increment}`); no other patch touches the key |
| String constants | 8 quoted strings (news image/store version lists, depot-limits embedded object string, production URL, expiration date, friend-reward id/description/scale CSV strings) — all opaque, never parsed |
| Cross-references | None validated: friend-reward strings resemble item lists but their dotted-pair CSV format is speculative, so they are recorded opaque, never references |
| Served bytes | Out of scope |

## Capabilities

### New Capabilities

- `globals-tuning-normalization`: Normalized tuning-constant definitions with patch lineage, schema, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (one normalized file, one schema, builder/validator, manifest `globals` section) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Offer packs (heterogeneous/nested with a stored float artifact), images, domain model, and Godot loading remain future work; this change does not claim them.
