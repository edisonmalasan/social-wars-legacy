## Why

The content census records what the 20 content keys contain, but normalization cannot be designed without knowing how values are encoded: the whole `config/main.json` holds 43,544 strings against 2,997 numbers, zero booleans, and 780 nulls; `items` (778 entries) is fully string-encoded with 1,697 embedded-JSON values; `goals`, `magics`, and `levels` mix strings and numbers. A read-only field-type survey is the smallest safe step that turns these observations into reviewed, verifiable evidence before any coercion rule is written.

## What Changes

- Add a reviewed machine-readable field-type survey and readable documentation covering all 20 content keys: for the 15 array-of-object keys, per-field profiles (presence count, JSON-level type distribution, string-encoded-number count, embedded-JSON-string count, empty-string count, null count); for the 5 object keys (`categories`, `inventory_items`, `globals`, `images`, `units_collections_categories`), value-shape profiles (value type distribution and entry counts).
- Fix deterministic predicates: a string counts as a string-encoded number only if it fully matches the numeric grammar (optional sign, digits, optional fraction/exponent); a string counts as embedded JSON only if it parses with the standard-library JSON decoder; all counts are exact recomputations, never samples.
- Add a read-only offline verifier that recomputes every profile from `config/main.json` with the standard library and diffs it against the reviewed survey, without importing the legacy application; reject unsupported content shapes instead of silently dropping them.
- Add focused regression tests for profile extraction, drift detection, predicate edge cases, survey/markdown consistency, and containment.
- Leave all legacy content and behavior unchanged; write no coercion rules, schemas, normalization, or ID reassignment, and claim no content validity or gameplay parity.

## Source-grounded survey scope

References below are proposal-time measurements from direct reads of `config/main.json`; the implementation must verify them against source rather than trusting this list.

| Key group | Keys | Proposal-time observation |
| --- | --- | --- |
| Array-of-object, string-heavy | `items` (778), `offer_packs` (44), `collections` (10), `social_items` (26) | Zero or near-zero native numbers; `items` holds 1,697 embedded-JSON values and 1,763 null-or-empty values |
| Array-of-object, mixed | `goals` (91: 273 str / 182 num), `magics` (10: 40 str / 60 num), `levels` (100: 200 str / 200 num) | Per-field profiles must capture which fields are encoded vs native |
| Array-of-object, small/plain | `expansion_prices` (98), `neighbor_assists` (5), `town_prices` (4), `map_prices` (4), `findable_items` (10), `sounds` (139), `level_ranking_reward` (50), `darts_items` (30) | Few distinct field types each; baseline profiles |
| Object keys | `categories` (6), `inventory_items` (90), `globals` (104), `images` (607), `units_collections_categories` (20) | Value-shape profiles instead of field profiles |
| Whole file | 20 keys | 43,544 strings / 2,997 numbers / 0 booleans / 780 nulls |

## Capabilities

### New Capabilities

- `content-field-survey`: Source-grounded, evidence-labeled inventory of legacy content field types and value encodings, with deterministic offline consistency verification.

### Modified Capabilities

None.

## Impact

Adds `docs/game-content/field-types.json`, `docs/game-content/field-types.md`, and focused tooling/tests under `tools/field-survey/`; updates documentation links and executed-check references. Uses Python 3.9 standard-library tooling, with no dependency upgrade, server import, network, browser, Flash, save mutation, modern API, normalization, coercion, or gameplay change. Normalization design, schema authoring, and domain modeling remain future work; this change does not claim them.
