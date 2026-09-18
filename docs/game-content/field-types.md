# Legacy content field-type survey

Source-grounded inventory of how values are encoded in the legacy Social Wars
stored game-content source (`config/main.json`), verified offline by
`tools/field-survey/verify_fields.py` against `field-types.json` in this
directory.

- **Evidence status: source inspection only.** Every entry below mirrors
  `field-types.json`; this document is a readable view, not a separate record.
  No content validity, gameplay parity, or normalization is claimed.
- **Observed encodings versus normalization decisions.** Sections marked
  "Observed encodings" report what the stored source contains, as recomputed
  by the verifier. The "Normalization decisions" section records what this
  survey explicitly does NOT decide: no coercion rule, default, schema,
  normalization, or ID reassignment is specified here. Those remain future
  work that will consume this survey.
- **Counts are stored, pre-layering values.** Profiles are recomputed from
  `config/main.json` as committed, before patch application, duplicate
  cleaning, or dynamic derivation (see the content census for layering).
- **Deterministic predicates.** A string counts as a string-encoded number
  only if it fully matches the numeric grammar
  `[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?`
  (optional sign, digits with optional fraction or leading-dot fraction,
  optional decimal exponent; no surrounding whitespace, hex, thousands
  separators, or Infinity/NaN spellings). A string counts as an embedded-JSON
  string only if the standard-library JSON decoder parses it; the two
  predicates are independent, so plain numeric strings, the string `null`,
  and whitespace-padded JSON all count as embedded JSON.
- **Whole file (observed).** `config/main.json` holds 43544 strings, 2997
  numbers, 0 booleans, and 780 nulls at the JSON level.

## Observed encodings: key inventory

Encoding classes: `string_encoded` means every present value is a string
(null marks absence, never a native value); `native` means no strings occur;
`mixed` means string-encoded and native JSON values coexist in the key.
Every `mixed` row below is an explicitly labeled mixed-encoding key.

| Key | Encoding | Entries | Notes |
| --- | --- | --- | --- |
| `items` | string_encoded | 778 | Fully string-encoded: every present value is a string except cost_type, which is null in all 778 entries. 41 of 53 fields are string-encoded numbers in every entry; costs, inventory_ids, properties, and premium_upgrade_costs carry embedded-JSON containers (objects/arrays/quoted nulls), 1697 container values in total. Empty strings appear only in best_against (299), group_type (46), premium_upgrade_costs (639), and properties (1). |
| `expansion_prices` | native | 98 | Fully native: all four fields are JSON numbers in every entry; no strings, nulls, or containers. |
| `levels` | mixed | 100 | Mixed key with homogeneous fields: name and reward_type are strings in all 100 entries, exp_required and reward_amount are numbers in all 100 entries. No string-encoded numbers, embedded JSON, empty strings, or nulls. |
| `neighbor_assists` | mixed | 5 | Mixed key: action, notification, and task are strings; rnd is a number; reward is an object with numeric coins/cash/xp in all 5 entries. |
| `town_prices` | native | 4 | Fully native: cash, coins, and level are JSON numbers in all 4 entries. |
| `map_prices` | native | 4 | Fully native: cash, coins, and level are JSON numbers in all 4 entries. |
| `findable_items` | mixed | 10 | Mixed key with homogeneous fields: id and coins are numbers, title and description are strings in all 10 entries. |
| `goals` | mixed | 91 | Mixed key with homogeneous fields: id and reward are numbers, title, description, and hint are strings in all 91 entries. hint is empty in all 91 entries. |
| `offer_packs` | mixed | 44 | Mixed key: 10 numeric fields, name and type strings, and items which is an array of id cross-references in 43 entries and null in 1 entry. type is empty in 18 entries. |
| `social_items` | mixed | 26 | Mixed key with homogeneous fields: id and worker_cost are numbers, description and workers are strings in all 26 entries. description is empty in all 26 entries. |
| `sounds` | string_encoded | 139 | Fully string-encoded: all 6 fields are strings in all 139 entries, and id, loops, max, and preload are string-encoded numbers throughout. |
| `collections` | string_encoded | 10 | Fully string-encoded: all 6 fields are strings in all 10 entries. cashPrice and id are string-encoded numbers; item_ids and prize carry embedded-JSON arrays/objects. |
| `level_ranking_reward` | mixed | 50 | Mixed key: cash and level are numbers and units is an object mapping item ids to quantities in all 50 entries. |
| `darts_items` | mixed | 30 | Mixed key: id and extra_item are numbers, items is an array of item ids, and start_date is a datetime string in all 30 entries. Stored start_date values are derivation input for make_dynamic, not served values. |
| `magics` | mixed | 10 | Mixed key with homogeneous fields: area, description, img_name, and name are strings; cash, gold, id, level, mana, and target are numbers in all 10 entries. area carries an embedded-JSON array string. |

| Key | Encoding | Entries | Notes |
| --- | --- | --- | --- |
| `categories` | object | 6 | Value shapes: 6 object. All 6 values are objects with integer id, string name, and a sub array of {id, name, parent} entries (5, 4, 5, 4, 1, 3 entries respectively). |
| `inventory_items` | object | 90 | Value shapes: 90 object. All 90 values are objects with the same 7 string fields (id, name, cashPrice, droppable, dropRate, dropsFrom, description); every value is string-encoded including the numeric ids and prices. |
| `globals` | object | 104 | Value shapes: 8 string, 66 number, 22 array, 8 object. Mixed value shapes: 62 integers, 4 floats (MARKET_INCREMENT, MARKET_SELL_PERCENTAGE, LIMIT_PER_LEVEL_SILO, REACTIVATE_WONDER_DISCOUNT), 8 strings (comma-separated lists, a URL, a date, and one embedded-JSON object string DEPOT_LIMITS), 8 objects (constant maps), and 22 arrays (numeric schedules and reward tables, some nesting objects). |
| `images` | object | 607 | Value shapes: 607 string. All 607 values are the locale string en; each key is the asset path. |
| `units_collections_categories` | object | 20 | Value shapes: 20 object. All 20 values are objects with integer category_id/cost/position/rewards, localized category_name_* strings (category_name_el is empty in every entry), a units array of integer item ids (89 total), and costs which is a numeric array in 19 entries and null in 1 entry. |

## Observed encodings: per-field profiles (array keys)

Columns: presence (entries carrying the field), JSON-level type distribution
(S strings, N numbers, B booleans, Z nulls, A arrays, O objects), #num
(string-encoded numbers), #json (embedded-JSON strings), #empty (empty
strings), #null (null values).

### `items` (string_encoded, 778 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `activation` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `attack` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `attack_interval` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `attack_range` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `best_against` | 778 | 778/0/0/0/0/0 | 138 | 138 | 299 | 0 |
| `best_against_mult` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `build_time` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `building_limit_same_id` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `building_limit_same_scf` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `category_id` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `clicks_to_build` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `collect` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `collect_type` | 778 | 778/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `collect_xp` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `cost` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `cost_type` | 778 | 0/0/0/778/0/0 | 0 | 0 | 0 | 778 |
| `cost_unit_cash` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `costs` | 778 | 778/0/0/0/0/0 | 0 | 778 | 0 | 0 |
| `defense` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `display_order` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `elevation` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `expiration` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `gift_level` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `giftable` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `group_type` | 778 | 778/0/0/0/0/0 | 0 | 0 | 46 | 0 |
| `height` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `id` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `img_name` | 778 | 778/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `in_store` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `inventory_ids` | 778 | 778/0/0/0/0/0 | 0 | 778 | 0 | 0 |
| `life` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `max_collects` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `max_elem_vol` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `max_frame` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `min_level` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `name` | 778 | 778/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `new_item` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `population` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `premium_upgrade_costs` | 778 | 778/0/0/0/0/0 | 0 | 139 | 639 | 0 |
| `properties` | 778 | 778/0/0/0/0/0 | 0 | 777 | 1 | 0 |
| `race` | 778 | 778/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `subcat_functional` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `subcategory_id` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `syringes` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `training_time` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `trains_ids` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `type` | 778 | 778/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `unit_capacity` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `upgrades_to` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `velocity` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `volume` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `width` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |
| `xp` | 778 | 778/0/0/0/0/0 | 778 | 778 | 0 | 0 |

### `expansion_prices` (native, 98 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `cash` | 98 | 0/98/0/0/0/0 | 0 | 0 | 0 | 0 |
| `coins` | 98 | 0/98/0/0/0/0 | 0 | 0 | 0 | 0 |
| `inventory_qte` | 98 | 0/98/0/0/0/0 | 0 | 0 | 0 | 0 |
| `neighbors` | 98 | 0/98/0/0/0/0 | 0 | 0 | 0 | 0 |

### `levels` (mixed, 100 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `exp_required` | 100 | 0/100/0/0/0/0 | 0 | 0 | 0 | 0 |
| `name` | 100 | 100/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `reward_amount` | 100 | 0/100/0/0/0/0 | 0 | 0 | 0 | 0 |
| `reward_type` | 100 | 100/0/0/0/0/0 | 0 | 0 | 0 | 0 |

### `neighbor_assists` (mixed, 5 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `action` | 5 | 5/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `notification` | 5 | 5/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `reward` | 5 | 0/0/0/0/0/5 | 0 | 0 | 0 | 0 |
| `rnd` | 5 | 0/5/0/0/0/0 | 0 | 0 | 0 | 0 |
| `task` | 5 | 5/0/0/0/0/0 | 0 | 0 | 0 | 0 |

### `town_prices` (native, 4 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `cash` | 4 | 0/4/0/0/0/0 | 0 | 0 | 0 | 0 |
| `coins` | 4 | 0/4/0/0/0/0 | 0 | 0 | 0 | 0 |
| `level` | 4 | 0/4/0/0/0/0 | 0 | 0 | 0 | 0 |

### `map_prices` (native, 4 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `cash` | 4 | 0/4/0/0/0/0 | 0 | 0 | 0 | 0 |
| `coins` | 4 | 0/4/0/0/0/0 | 0 | 0 | 0 | 0 |
| `level` | 4 | 0/4/0/0/0/0 | 0 | 0 | 0 | 0 |

### `findable_items` (mixed, 10 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `coins` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |
| `description` | 10 | 10/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `id` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |
| `title` | 10 | 10/0/0/0/0/0 | 0 | 0 | 0 | 0 |

### `goals` (mixed, 91 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `description` | 91 | 91/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `hint` | 91 | 91/0/0/0/0/0 | 0 | 0 | 91 | 0 |
| `id` | 91 | 0/91/0/0/0/0 | 0 | 0 | 0 | 0 |
| `reward` | 91 | 0/91/0/0/0/0 | 0 | 0 | 0 | 0 |
| `title` | 91 | 91/0/0/0/0/0 | 0 | 0 | 0 | 0 |

### `offer_packs` (mixed, 44 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `cost_cash` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `enabled` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `gold` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `id` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `items` | 44 | 0/0/0/1/43/0 | 0 | 0 | 0 | 1 |
| `mana` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `name` | 44 | 44/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `oil` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `position` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `steel` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `type` | 44 | 44/0/0/0/0/0 | 0 | 0 | 18 | 0 |
| `wood` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |
| `xp` | 44 | 0/44/0/0/0/0 | 0 | 0 | 0 | 0 |

### `social_items` (mixed, 26 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `description` | 26 | 26/0/0/0/0/0 | 0 | 0 | 26 | 0 |
| `id` | 26 | 0/26/0/0/0/0 | 0 | 0 | 0 | 0 |
| `worker_cost` | 26 | 0/26/0/0/0/0 | 0 | 0 | 0 | 0 |
| `workers` | 26 | 26/0/0/0/0/0 | 0 | 0 | 0 | 0 |

### `sounds` (string_encoded, 139 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `description` | 139 | 139/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `file` | 139 | 139/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `id` | 139 | 139/0/0/0/0/0 | 139 | 139 | 0 | 0 |
| `loops` | 139 | 139/0/0/0/0/0 | 139 | 139 | 0 | 0 |
| `max` | 139 | 139/0/0/0/0/0 | 139 | 139 | 0 | 0 |
| `preload` | 139 | 139/0/0/0/0/0 | 139 | 139 | 0 | 0 |

### `collections` (string_encoded, 10 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `cashPrice` | 10 | 10/0/0/0/0/0 | 10 | 10 | 0 | 0 |
| `description` | 10 | 10/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `id` | 10 | 10/0/0/0/0/0 | 10 | 10 | 0 | 0 |
| `item_ids` | 10 | 10/0/0/0/0/0 | 0 | 10 | 0 | 0 |
| `name` | 10 | 10/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `prize` | 10 | 10/0/0/0/0/0 | 0 | 10 | 0 | 0 |

### `level_ranking_reward` (mixed, 50 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `cash` | 50 | 0/50/0/0/0/0 | 0 | 0 | 0 | 0 |
| `level` | 50 | 0/50/0/0/0/0 | 0 | 0 | 0 | 0 |
| `units` | 50 | 0/0/0/0/0/50 | 0 | 0 | 0 | 0 |

### `darts_items` (mixed, 30 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `extra_item` | 30 | 0/30/0/0/0/0 | 0 | 0 | 0 | 0 |
| `id` | 30 | 0/30/0/0/0/0 | 0 | 0 | 0 | 0 |
| `items` | 30 | 0/0/0/0/30/0 | 0 | 0 | 0 | 0 |
| `start_date` | 30 | 30/0/0/0/0/0 | 0 | 0 | 0 | 0 |

### `magics` (mixed, 10 entries)

| Field | Presence | S/N/B/Z/A/O | #num | #json | #empty | #null |
| --- | --- | --- | --- | --- | --- | --- |
| `area` | 10 | 10/0/0/0/0/0 | 0 | 10 | 0 | 0 |
| `cash` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |
| `description` | 10 | 10/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `gold` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |
| `id` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |
| `img_name` | 10 | 10/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `level` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |
| `mana` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |
| `name` | 10 | 10/0/0/0/0/0 | 0 | 0 | 0 | 0 |
| `target` | 10 | 0/10/0/0/0/0 | 0 | 0 | 0 | 0 |

## Normalization decisions (explicitly not made)

This survey records observed encodings only. It does NOT specify:

- No coercion rule (for example, parsing string-encoded numbers into
  numbers) is defined or applied.
- No defaults for absent, empty, or null fields are defined.
- No schema, validation rule, or ID reassignment is specified; legacy
  content IDs are preserved as observed.
- No stored source file is modified; `config/main.json` is read-only input.

Normalization design, schema authoring, and domain modeling remain future
work that must cite this survey as its source-grounded input.
