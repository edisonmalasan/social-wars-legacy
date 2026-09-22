## Why

Six M3 slices (items, quests, reference tables, economy schedules, social tables, inventory taxonomy) proved the normalization pattern. The next smallest coherent slice is the last small array-keyed content domain: `darts_items` (30 stored entries, replaced wholesale by the `targets` patch with 27 effective entries). It is the only remaining normalized slice with patch layering since items, and its time-dependent serve boundary is already censused — 27 uniform entries with clean item references, bounded and well-understood.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/darts_items.json` (27, one per patched entry), a JSON schema (`darts-item`), a stdlib-only builder/validator tool extension, and manifest entries recording sources, patch lineage, content version, and legacy IDs.
- Apply the documented patch layering first (items-builder precedent): verify the ordered patch list, apply only the `targets` whole-array replace of `/darts_items`, and refuse any other darts target or a missing/divergent `targets` patch explicitly. Normalize the patched array, with `source_layer` recording `patched(targets)`.
- Coerce per the field-type survey with documented rules: native integer `id`, six-element native integer `items` pool, and native integer `extra_item` kept verbatim and validated against the normalized items legacy-ID set (quest-precedent edge, carried in stored order plus a single `extra_ref`); `start_date` datetime strings preserved verbatim as derivation inputs, never interpreted as served values. Every definition preserves `legacy_id` as the decimal id.
- Validate: id uniqueness, six pooled ids plus extra reference resolution, required schema fields, and schema-validator traceability. Round-trip evidence: re-emitted patched-shaped entries diffed against the patched array exactly. `make_dynamic` never runs; served bytes stay out of scope exactly as in the content census.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| Stored `darts_items` | 30 entries, ids 1..30, uniform keys `id`/`start_date`/`items`/`extra_item` |
| Patched `darts_items` | 27 entries via the `targets` whole-array replace, ids sequential 1..27, uniform shape, `items` always 6 native ints, `extra_item` native int, `start_date` uniform 19-char datetime strings |
| Patch interaction | Exactly one: `targets` replaces `/darts_items`; no other patch touches the key; the builder applies only this replace and refuses drift |
| Cross-references | One edge: pooled `items` integers plus `extra_item` resolve against the loaded 900 items legacy-ID set (0 missing at proposal time) |
| Served bytes | Out of scope: `make_dynamic` rewrites every `start_date` from the wall clock, so served configuration drifts and is explicitly unverified |

## Capabilities

### New Capabilities

- `darts-schedule-normalization`: Normalized darts schedule definitions with patch lineage, schema, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (one normalized file, one schema, builder/validator, manifest `darts` section) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. Offer packs (heterogeneous/nested with a stored float artifact), globals, images, domain model, and Godot loading remain future work; this change does not claim them.
