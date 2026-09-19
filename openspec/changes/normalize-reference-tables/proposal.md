## Why

Items and quest normalization proved the M3 pattern. The next smallest slice is the static lookup tables the game reads but never mutates through patches: `magics` (10 spell definitions), `levels` (100-entry XP curve), and `sounds` (139-entry audio registry). Together 149 entries with simple shapes, no patch layering, and no cross-references — the cheapest remaining normalization with the same round-trip guarantees.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/magics.json` (10), `normalized/levels.json` (100), `normalized/sounds.json` (139), JSON schemas under `schemas/` (magic, level, sound), a stdlib-only builder/validator tool extension, and manifest entries recording sources, content version, and legacy IDs.
- Coerce per the field-type survey with documented rules: `magics` native IDs kept, `area` embedded-JSON array string to integer array, costs kept native; `levels` fully native kept verbatim; `sounds` string IDs and numeric params coerced to integers, `file`/`description` preserved verbatim as asset references (recorded, not validated — asset truth is M4). Every definition preserves `legacy_id`.
- Normalize from stored content directly (no patch targets any of the three keys; the builder refuses patch drift and active mods explicitly).
- Validate: duplicate IDs, non-negative amounts and XP monotonicity notes, required schema fields, and schema-validator traceability. Round-trip evidence: re-emitted legacy-shaped entries diffed against stored content modulo documented coercions.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `magics` entries | 10; native integer `id`; `mana`/`level`/`gold`/`cash`/`target` native numbers; `area` embedded-JSON integer-array string (e.g. `[5,7,9]`); `img_name` asset ref preserved |
| `levels` entries | 100; `name` string; `exp_required` native number (0 to 2016089205 across the curve); `reward_type`/`reward_amount` native |
| `sounds` entries | 139; string `id`; `loops`/`max`/`preload` string-encoded numbers; `file`/`description` strings |
| Patch interaction | None: no active patch targets `magics`, `levels`, or `sounds`; mods pipeline must stay inactive |
| Cross-references | None: `area` holds formation offsets, not item IDs; `file` names are M4 asset truth, not validated here |
| Served bytes | Out of scope |

## Capabilities

### New Capabilities

- `reference-tables-normalization`: Normalized magic, level-curve, and sound definitions with schemas, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (normalized magics/levels/sounds, schemas, builder/validator, manifest) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Economy tables, remaining misc keys, domain model, and Godot loading remain future work; this change does not claim them.
