## Why

Endpoints and dispatcher commands are now inventoried, but the game's static data — `config/main.json` (1.7 MB, 20 top-level keys), five ordered JSON patches, an inactive mod pipeline, import-time duplicate cleaning, and per-request dynamic derivation — has no recorded inventory. Content normalization (roadmap section 10) cannot start safely without a source-grounded census stating what the content is, how it is layered, and which parts are deterministic.

## What Changes

- Add a reviewed machine-readable content census and readable documentation covering the 20 top-level keys of `config/main.json` (entry counts, container shapes, ID schemes, asset-reference fields), the five ordered patches from `config/patch/patches.txt` (op counts, target paths, ordering notes), the mods pipeline status (`mods/mods.txt` ships with its single mod commented out — inactive), the `remove_duplicate_items` import-time behavior (`get_game_config.py:11-34`, keeps the later duplicate), and the dynamic-derivation boundary (`make_dynamic` runs at import at `get_game_config.py:319` and on every served response at `get_game_config.py:89-91`, rewriting darts dates from the wall clock).
- Record explicitly that the census covers stored sources only: served configuration is time-dependent and therefore out of census scope.
- Add a read-only offline verifier that checks census structure, key coverage and entry counts against `config/main.json`, patch-file presence/order/parseability against `patches.txt`, and mods status against `mods/mods.txt`, without importing the legacy application or applying patches; reject unsupported content shapes instead of silently dropping them.
- Add focused regression tests for key extraction, count drift, patch-order drift, mods-status change, and containment.
- Leave all legacy content, patches, and behavior unchanged; perform no normalization, schema authoring, or ID reassignment.

## Source-grounded content inventory

References below identify content sources at proposal time. Counts are proposal-time observations; the implementation must verify them against source rather than trusting this list.

| Source | Shape | Proposal-time observation |
| --- | --- | --- |
| `config/main.json` | JSON object, 20 top-level keys | `categories`, `items`, `inventory_items`, `expansion_prices`, `levels`, `neighbor_assists`, `town_prices`, `map_prices`, `findable_items`, `goals`, `offer_packs`, `social_items`, `globals`, `images`, `sounds`, `collections`, `level_ranking_reward`, `darts_items`, `units_collections_categories`, `magics` |
| `config/patch/patches.txt` | Ordered list, `#` comments skipped | Active order: `atom_fusion_item`, `unit_patch`, `atom_fusion_items_data`, `atom_fusion_powerup`, `targets` |
| `config/patch/*.json` | RFC 6902 patch arrays | Applied via `jsonpatch` at import (`get_game_config.py:40-58`) |
| `mods/mods.txt` | Ordered list, all lines commented | Single mod `no_hiring_needed` commented out — pipeline inactive (`get_game_config.py:60-78`) |
| `remove_duplicate_items` | Import-time mutation | Deletes the earlier of two `items` entries sharing an `id`, keeps the later one |
| `make_dynamic` | Import-time and per-request mutation | Rewrites `darts_items` start dates from the wall clock; served bytes are time-dependent |

## Capabilities

### New Capabilities

- `content-census`: Source-grounded, evidence-labeled inventory of legacy game-content sources and their layering, with deterministic offline consistency verification.

### Modified Capabilities

None.

## Impact

Adds `docs/game-content/census.json`, `docs/game-content/census.md`, and focused tooling/tests under `tools/content-census/`; updates documentation links and executed-check references. Uses Python 3.9 standard-library tooling, with no dependency upgrade, server import, network, browser, Flash, save mutation, modern API, normalization, or gameplay change. Content normalization, schema authoring, and domain modeling remain future work; this change does not claim them.
