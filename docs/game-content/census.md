# Legacy game-content census

Source-grounded inventory of the legacy Social Wars stored game-content
sources (`config/main.json`, five ordered patches, the mods pipeline,
import-time duplicate cleaning, and the dynamic-derivation boundary),
verified offline by `tools/content-census/verify_content.py` against
`census.json` in this directory.

- **Evidence status: source inspection only.** Every entry below mirrors
  `census.json`; this document is a readable view, not a separate record.
  No served-byte equality, content validity, gameplay parity, or
  normalization is claimed.
- **Stored sources versus served bytes.** The census covers **stored**
  sources only: `config/main.json` as committed, the five patch files in
  `config/patch/` applied in `patches.txt` order, and the mods pipeline
  status in `mods/mods.txt`. The bytes actually **served** to clients are
  time-dependent: `make_dynamic` rewrites every `darts_items`
  `start_date` from the wall clock, so served configuration drifts with
  the clock and is explicitly out of census scope.
- **Mods pipeline: inactive.** `mods/mods.txt` ships with its single mod
  `no_hiring_needed` commented out, so `modify_game_config`
  (`get_game_config.py:60-78`) applies nothing at load time. The archived
  payload `mods/no_hiring_needed.json` is preserved but never loaded.
- **Duplicate cleaning.** Import-time `remove_duplicate_items`
  (`get_game_config.py:11-34`) deletes the earlier of two `items`
  entries sharing an `id` and keeps the later one. The stored file
  contains no duplicate item ids (778 of 778 distinct), so the cleaner
  is a no-op on current sources; census counts are pre-cleaning stored
  values.
- **Counts are stored, pre-layering values.** Entry counts below are read
  from `config/main.json` before patch application. Patches append
  entries afterwards: `atom_fusion_item` adds 1 item, `unit_patch` adds
  121 items, `atom_fusion_items_data` adds fields to 300 existing items,
  `atom_fusion_powerup` adds one `globals` key, and `targets` replaces
  the whole `darts_items` array.

## Content keys (`config/main.json`, 20 top-level keys)

| Key | Shape | Entries | ID scheme | Asset-reference fields |
| --- | --- | --- | --- | --- |
| `categories` | object | 6 | String keys mirroring integer `id`; nested `sub` entries carry integer `id` + `parent` | none |
| `items` | array | 778 | Unique string `id` (778 of 778 distinct) | `img_name` |
| `inventory_items` | object | 90 | String keys mirroring string `id` | none |
| `expansion_prices` | array | 98 | No stable ID; positional index | none |
| `levels` | array | 100 | No stable ID; positional index (0-based level) | none |
| `neighbor_assists` | array | 5 | No stable ID; positional index | none |
| `town_prices` | array | 4 | No stable ID; positional index | none |
| `map_prices` | array | 4 | No stable ID; positional index | none |
| `findable_items` | array | 10 | Unique integer `id` | none |
| `goals` | array | 91 | Unique integer `id` | none |
| `offer_packs` | array | 44 | Unique integer `id`; `items` holds item-id cross-references | none |
| `social_items` | array | 26 | Unique integer `id`, non-sequential | none |
| `globals` | object | 104 | String constant names as keys (62 int, 22 list, 8 dict, 8 str, 4 float values) | none |
| `images` | object | 607 | Key itself is the asset path; every value is the locale string `en` | key (asset path) |
| `sounds` | array | 139 | Unique string `id` | `file` |
| `collections` | array | 10 | Unique string `id`; `item_ids`/`prize` are JSON-encoded item-id references | none |
| `level_ranking_reward` | array | 50 | No `id`; integer `level` field, descending 50..1 | none |
| `darts_items` | array | 30 | Unique integer `id`; stored `start_date` values are derivation input, rewritten at serve time | none |
| `units_collections_categories` | object | 20 | String keys mirroring integer `category_id`; `units` holds item-id references | none |
| `magics` | array | 10 | Unique integer `id` | `img_name` |

Cross-content references (`offer_packs` `items`, `collections`
`item_ids`, `darts_items` `items`/`extra_item`,
`units_collections_categories` `units`) point at `items` string ids;
`level_ranking_reward` `units` maps item ids to quantities. These are
content references, not file-asset paths, and are recorded in the ID
schemes above rather than as asset-reference fields.

## Patch layering (`config/patch/patches.txt` order)

Patches apply at import via `patch_game_config`
(`get_game_config.py:40-58`), in this exact order; comment and blank
lines in `patches.txt` are skipped. Later patches observe earlier
patches' effects, so reordering would change the result.

| Position | Patch file | Ops | Target paths |
| --- | --- | --- | --- |
| 1 | `atom_fusion_item` | 1 add | `/items/-` (appends the Atom Fusion building, id `302`) |
| 2 | `unit_patch` | 121 add | `/items/-` (appends 121 unit entries) |
| 3 | `atom_fusion_items_data` | 600 add | `/items/{index}/breeding_order`, `/items/{index}/sm_training_time` (300 existing items x 2 fields) |
| 4 | `atom_fusion_powerup` | 1 add | `/globals/SOUL_MIXER_POWERUPS_LEVELS` |
| 5 | `targets` | 1 replace | `/darts_items` (replaces the whole array; stored `start_date` values here are still only derivation input for `make_dynamic`) |

## Mods pipeline (inactive)

`mods/mods.txt` lists one mod, `no_hiring_needed`, commented out.
`modify_game_config` (`get_game_config.py:60-78`) therefore loads
nothing. The preserved payload `mods/no_hiring_needed.json` (which
would patch building costs) stays on disk unapplied. Any future
activation must be re-censused: the verifier treats any active mod as
drift.

## Dynamic-derivation boundary

`make_dynamic` (`get_game_config.py:213-317`, invoked at import at
`get_game_config.py:319` and on every served response at
`get_game_config.py:89-91`) rebuilds each `darts_items` `start_date`
from the wall clock with Monday-anchored week wrapping. Consequences:

- Stored `darts_items` dates (30 entries, ids 1..30) are inputs, not
  outputs. Two reads of served configuration at different wall-clock
  times legitimately differ.
- The verifier never imports the legacy application and never produces
  served bytes, so it stays deterministic across runs.
- Served-byte equality is unverified by design; only the boundary
  itself is censused.
