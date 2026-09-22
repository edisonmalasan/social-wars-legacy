# Items normalization package

Normalized, schema-checked building and unit definitions for the legacy
Social Wars `items` content domain, built offline from stored sources with
Python 3.9 standard library only; no new dependencies.

## Inputs

- `config/main.json` (stored source, 778 `items` entries: `b` 469, `u` 308,
  `l` 1; every entry carries 52 string-typed fields plus the
  always-null `cost_type` (53 keys total: 51 body fields plus `id` plus
  `cost_type`).
- `config/patch/patches.txt` plus the five ordered patch files:
  `atom_fusion_item` (1 add appending building id `302`),
  `unit_patch` (121 adds appending units), `atom_fusion_items_data`
  (600 adds of `breeding_order`/`sm_training_time` on 300 entries),
  `atom_fusion_powerup` (1 globals add), `targets` (1 `darts_items`
  replace).
- `mods/mods.txt` (must stay inactive; any active mod fails the build).
- `packages/game-content/schemas/building.schema.json` and
  `unit.schema.json` (contracts enforced by the builder).

## Layering

The builder mirrors the legacy loader (`get_game_config.py`, never
imported): ordered patch application restricted to the observed
add/replace subset, then keep-later duplicate cleaning. Loaded content is
900 entries (470 `b`, 429 `u`, 1 `l`; all 900 ids distinct), and every
definition carries `source_file`/`source_layer` plus a `content_version`
fingerprint (sha256 over the stored bytes plus the ordered patch and list
bytes), because the sources carry no version stamp of their own.

## Coercion rules (`coercion-ruleset-v1`, survey-cited)

- R1 numeric strings to numbers (integral floats become int), using the
  field-survey numeric grammar
  `[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?`.
- R2 embedded-JSON strings to structures: `costs` to an object,
  `properties` to an object, `inventory_ids` to an object or null (the
  stored `null` string), `premium_upgrade_costs` to an object (empty
  string handled by R3).
- R3 empty strings: preserved as `""` for `best_against` (299 stored) and
  `group_type` (46 stored), where the survey shows emptiness is meaningful;
  coerced to null for `premium_upgrade_costs` (639 stored) and
  `properties` (1 entry, id `925`), where emptiness marks absence.
- R4 `cost_type` (null in every stored and appended entry) is dropped with
  this note; the round-trip gate asserts its absence is null-only.
- R5 `legacy_id` preserves the stored string `id` verbatim.
- R6 `upgrades_to`/`trains_ids` coerce to int; `-1` and `0` mean none
  (stored `0` counts: 138 upgrades, 8 trains); any other value must
  resolve to a known `legacy_id`.
- R7 `best_against` numerics coerce to int but are opaque codes: all 138
  were verified non-resolving against loaded item ids, so they are never
  treated as item references. `inventory_ids` keys reference the
  `inventory_items` domain and are carried without item-id checks.

No value is rebalanced, renamed for gameplay, or assigned new meaning.

## Outputs

- `normalized/buildings.json`: 470 building definitions (stored `b` plus
  patch-appended id `302`).
- `normalized/units.json`: 429 unit definitions (stored `u` plus 121
  patch-appended units).
- `normalized/specials.json`: the documented special, id `925`
  (Expandable Land, stored `l`), with a `special_note` rationale.
- `manifest.json`: input sources with digests, layering order, coercion
  ruleset version, definition counts, and builder outcome. Regenerated on
  every successful build; the tests assert it matches the produced output.

## Validation gates (failures exit 1, outputs unwritten)

Duplicate ids removed by dedup (refusing silent loss), unknown `type`,
unresolvable non-sentinel `upgrades_to`/`trains_ids`, cost keys outside
`o/s/g/w/c` or negative/non-integer amounts, missing or mistyped
schema-required fields (every schema-required field is enforced; the
traceability test proves it by mutation), unexpected specials, and any
round-trip difference outside the documented coercions. The round-trip
gate re-coerces each loaded entry and compares by value, structures
parsed, empties exact, and field sets exact (modulo the dropped
`cost_type`).

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)).
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root:

```bash
python -B packages/game-content/tools/build_items.py
```

Exit 0 prints a JSON success report with counts and output files.
Exit 1 prints a `validation-failed` report listing each problem and
writes nothing. Exit 2 reports invalid input or unsupported shapes
(missing/unreadable files, unparseable content, an active mod, an
unknown patch op or target, an out-of-range patch index, or an invalid
schema file) on stderr.

## Evidence classification

This package establishes source-grounded normalization consistency for
the loaded `items` domain: classification coverage, coercion fidelity,
reference resolution, and round-trip equivalence modulo documented
rules. It is evidence of representation change, not of served-byte
equality, content validity, gameplay parity, asset existence (M4 owns
asset truth), or progressed-player coverage. Served bytes stay out of
scope exactly as in the content census (`make_dynamic` never runs here).

## Containment

- Reads only `config/main.json`, `config/patch/patches.txt`, the five
  patch files, `mods/mods.txt`, and the two schema files (plus optional
  `--repo-root`/`--out-root` relocation of the same reads).
- Never imports or executes any legacy application module (no
  `get_game_config`, `jsonpatch`, or Flask import), never reads runtime
  saves, never contacts a network, never starts a server, and never
  opens a browser or Flash content.
- Writes only the three normalized files plus `manifest.json`, and only
  on success. No bytecode (`-B` recommended), no caches, no temporary
  files in the repository. Repeated runs over unchanged inputs are
  byte-identical.
- The focused tests in `tests/test_build_items.py` run the same way:

```bash
python -B -m unittest discover -s packages/game-content/tests -p test_build_items.py -v
```

---

# Quest normalization extension

Normalized, schema-checked quest and collection definitions for the
legacy Social Wars `goals` (91 entries) and `collections` (10 entries)
content domains, built offline from stored sources with Python 3.9
standard library only; no new dependencies. Run the items build first:
the quest builder reads the committed normalized items outputs as its
cross-domain reference edge, and merges its `quests` section into the
package manifest the items build produces.

## Inputs

- `config/main.json` (stored source: 91 `goals` entries with native
  integer `id`, native integer `reward`, string
  `title`/`description`/`hint` with `hint` empty in all 91; 10
  `collections` entries with all 6 fields string-typed: string `id`,
  `name`, `description`, embedded-JSON `item_ids` integer-array strings,
  embedded-JSON `prize` single-key object strings, string-encoded
  `cashPrice` numbers).
- `config/patch/patches.txt` plus the five ordered patch files, read
  only to verify no patch targets `goals` or `collections` (any such
  target fails the build explicitly; stored content is the input, there
  is no layering).
- `mods/mods.txt` (must stay inactive; any active mod fails the build).
- `packages/game-content/schemas/quest.schema.json` and
  `collection.schema.json` (contracts enforced by the builder).
- `packages/game-content/normalized/buildings.json`, `units.json`,
  `specials.json` (committed items outputs; their union of 900
  `legacy_id` values is the cross-domain reference set).

## Coercion rules (`quest-coercion-ruleset-v1`, survey-cited)

- Q1 numeric strings to numbers (integral floats become int), using the
  same field-survey numeric grammar as items
  `[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?`:
  collection `id` and `cashPrice`.
- Q2 embedded-JSON strings to structures: `item_ids` to an integer
  array (non-empty), `prize` to an object of item-id keys to positive
  integer counts.
- Q3 native and verbatim fields kept as stored: quest `id`/`reward`
  (native integers), quest `title`/`hint`/`description` and collection
  `name`/`description` (strings). The uniformly-empty `hint` (91 of 91)
  and the uniform `reward` (10 in all 91) are preserved verbatim with
  manifest notes, never defaulted or dropped.
- Q4 `legacy_id` preserves the stored `id` verbatim as a string (the
  decimal form of the native integer for quests, the stored string for
  collections).
- Q5 resolved item references: `item_refs` carries the `item_ids` ids
  as decimal `legacy_id` strings in stored order, and `prize_refs`
  carries the prize keys sorted; every referenced id must resolve
  against the normalized items legacy-ID set or validation fails.

No value is rebalanced, renamed for gameplay, or assigned new meaning.

## Outputs

- `normalized/quests.json`: 91 quest definitions (one per stored
  `goals` entry, stored order).
- `normalized/collections.json`: 10 collection definitions (one per
  stored `collections` entry, stored order).
- `manifest.json`: the existing items manifest with a `quests` section
  merged in, recording quest inputs with digests, the cross-domain
  items reference edge (files, counts, union size), the coercion
  ruleset version, the content fingerprint (sha256 over the stored
  source bytes plus the mods list), definition counts, builder outcome,
  output digests, and uniformity notes. Regenerated on every successful
  quest build; the tests assert it matches the produced output while
  the items keys survive the merge untouched.

## Validation gates (failures exit 1, outputs unwritten)

Duplicate quest or collection ids (refusing silent loss), unresolvable
`item_ids`/`prize` references against the normalized items set,
non-integral or negative `cashPrice`, non-positive prize amounts,
empty `item_ids`, missing or mistyped schema-required fields (every
schema-required field is enforced; the traceability test proves it by
mutation), `item_refs`/`prize_refs` drift, and any round-trip
difference outside the documented coercions. The round-trip gate
re-coerces each stored entry and compares by value (embedded-JSON
structures parsed, numeric strings numeric, strings verbatim, field
sets exact); the derived `item_refs`/`prize_refs` are checked against
their sources instead of the stored bytes.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)).
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root (after the items build):

```bash
python -B packages/game-content/tools/build_quests.py
```

Exit 0 prints a JSON success report with counts and output files.
Exit 1 prints a `validation-failed` report listing each problem and
writes nothing (the manifest is left untouched). Exit 2 reports
invalid input or unsupported shapes (missing/unreadable files,
unparseable content, an active mod, a patch targeting quest content,
an invalid schema file, or a missing/malformed normalized items
output) on stderr.

## Evidence classification

This extension establishes source-grounded normalization consistency
for the stored `goals`/`collections` domains: classification coverage,
coercion fidelity, cross-domain reference resolution against the
normalized items package, and round-trip equivalence modulo documented
rules. It is evidence of representation change, not of served-byte
equality, content validity, gameplay parity, asset existence (M4 owns
asset truth), or progressed-player coverage. Served bytes stay out of
scope exactly as in the content census (`make_dynamic` never runs here).

## Containment

- Reads only `config/main.json`, `config/patch/patches.txt`, the five
  patch files (target check only), `mods/mods.txt`, the two quest
  schema files, the three committed normalized items outputs, and the
  package manifest for the merge (plus optional `--repo-root`/`--out-root`
  relocation of the same reads).
- Never imports or executes any legacy application module (no
  `get_game_config`, `jsonpatch`, or Flask import), never reads runtime
  saves, never contacts a network, never starts a server, and never
  opens a browser or Flash content.
- Writes only the two normalized quest files plus the merged
  `manifest.json`, and only on success. No bytecode (`-B` recommended),
  no caches, no temporary files in the repository. Repeated runs over
  unchanged inputs are byte-identical.
- The focused tests in `tests/test_build_quests.py` run the same way:

```bash
python -B -m unittest discover -s packages/game-content/tests -p test_build_quests.py -v
```

---

# Reference-tables normalization extension

Normalized, schema-checked magic, level-curve, and sound definitions
for the legacy Social Wars `magics` (10 entries), `levels` (100
entries), and `sounds` (139 entries) content domains, built offline
from stored sources with Python 3.9 standard library only; no new
dependencies. This extension has no cross-domain reference edge and
requires no prior build; it merges its `tables` section into the
package manifest the items and quest builds produce.

## Inputs

- `config/main.json` (stored source: 10 `magics` entries with native
  integer `id`, native integer `mana`/`level`/`gold`/`cash`/`target`,
  string `name`/`description`/`img_name`, and embedded-JSON `area`
  integer-array strings; 100 `levels` entries with fully native
  `name`/`exp_required`/`reward_type`/`reward_amount` and no stable
  id; 139 `sounds` entries with all 6 fields string-typed: string
  `id`, `file`, `description`, and string-encoded
  `loops`/`max`/`preload` numbers).
- `config/patch/patches.txt` plus the five ordered patch files, read
  only to verify no patch targets `magics`, `levels`, or `sounds`
  (any such target fails the build explicitly; stored content is the
  input, there is no layering).
- `mods/mods.txt` (must stay inactive; any active mod fails the build).
- `packages/game-content/schemas/magic.schema.json`,
  `level.schema.json`, and `sound.schema.json` (contracts enforced by
  the builder).

## Coercion rules (`tables-coercion-ruleset-v1`, survey-cited)

- T1 numeric strings to numbers (integral floats become int), using the
  same field-survey numeric grammar as items and quests
  `[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?`:
  sound `id`, `loops`, `max`, and `preload`.
- T2 embedded-JSON strings to structures: magic `area` to a
  non-empty integer array. Offsets are formation data, never item
  references.
- T3 native and verbatim fields kept as stored: magic
  `id`/`mana`/`level`/`gold`/`cash`/`target` (native integers),
  magic `name`/`description`/`img_name` (strings), all level fields
  (fully native), and sound `file`/`description` (strings).
  `img_name`, `file`, and `description` strings are recorded asset
  references, never validated; asset truth belongs to M4. The XP
  curve (`exp_required` spanning 0 to 2016089205) is preserved
  verbatim including any irregularities, never smoothed; XP order is
  positional.
- T4 `legacy_id` preserves the stored identity verbatim as a string:
  the decimal form of the native integer `id` for magics, the stored
  string `id` for sounds, and the 0-based positional index for
  levels (levels carry no stable stored id and the legacy loader
  indexes the array positionally), with `level_index` carrying the
  numeric position.

No value is rebalanced, renamed for gameplay, or assigned new meaning.

## Outputs

- `normalized/magics.json`: 10 magic definitions (one per stored
  `magics` entry, stored order).
- `normalized/levels.json`: 100 level definitions (one per stored
  `levels` entry, stored XP-curve order preserved positionally).
- `normalized/sounds.json`: 139 sound definitions (one per stored
  `sounds` entry, stored order).
- `manifest.json`: the existing items/quest manifest with a `tables`
  section merged in, recording tables inputs with digests, the
  coercion ruleset version, the content fingerprint (sha256 over the
  stored source bytes plus the mods list), definition counts
  (including the XP range, monotonicity note, and reward-type set),
  builder outcome, and output digests. Regenerated on every successful
  tables build; the tests assert it matches the produced output while
  the items and quests keys survive the merge untouched.

## Validation gates (failures exit 1, outputs unwritten)

Duplicate magic or sound ids (refusing silent loss), negative magic
amounts, negative XP or reward amounts, negative sound params,
non-integral sound numerics, non-integer area elements, missing or
mistyped schema-required fields (every schema-required field is
enforced; the traceability test proves it by mutation), and any
round-trip difference outside the documented coercions. The round-trip
gate re-coerces each stored entry and compares by value (embedded-JSON
structures parsed, numeric strings numeric, strings verbatim, field
sets exact); level identity is positional.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)).
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root:

```bash
python -B packages/game-content/tools/build_tables.py
```

Exit 0 prints a JSON success report with counts and output files.
Exit 1 prints a `validation-failed` report listing each problem and
writes nothing (the manifest is left untouched). Exit 2 reports
invalid input or unsupported shapes (missing/unreadable files,
unparseable content, an active mod, a patch targeting tables content,
or an invalid schema file) on stderr.

## Evidence classification

This extension establishes source-grounded normalization consistency
for the stored `magics`/`levels`/`sounds` domains: classification
coverage, coercion fidelity, positional XP-curve preservation, and
round-trip equivalence modulo documented rules. It is evidence of
representation change, not of served-byte equality, content validity,
gameplay parity, asset existence (M4 owns asset truth), or
progressed-player coverage. Served bytes stay out of scope exactly as
in the content census (`make_dynamic` never runs here).

## Containment

- Reads only `config/main.json`, `config/patch/patches.txt`, the five
  patch files (target check only), `mods/mods.txt`, the three tables
  schema files, and the package manifest for the merge (plus optional
  `--repo-root`/`--out-root` relocation of the same reads).
- Never imports or executes any legacy application module (no
  `get_game_config`, `jsonpatch`, or Flask import), never reads runtime
  saves, never contacts a network, never starts a server, and never
  opens a browser or Flash content.
- Writes only the three normalized tables files plus the merged
  `manifest.json`, and only on success. No bytecode (`-B` recommended),
  no caches, no temporary files in the repository. Repeated runs over
  unchanged inputs are byte-identical.
- The focused tests in `tests/test_build_tables.py` run the same way:

```bash
python -B -m unittest discover -s packages/game-content/tests -p test_build_tables.py -v
```

---

# Economy-schedules normalization extension

Normalized, schema-checked price-schedule and reward definitions for the
legacy Social Wars `expansion_prices` (98 entries), `town_prices`
(4 entries), `map_prices` (4 entries), and `level_ranking_reward`
(50 entries) content domains, built offline from stored sources with
Python 3.9 standard library only; no new dependencies. Run the
items-normalization build first: the economy builder reads the committed
normalized items outputs as its cross-domain reference edge for ranking
rewards and merges its `economy` section into the package manifest.

## Inputs

- `config/main.json` (stored source: 98 `expansion_prices` entries with
  fully native `coins`/`cash`/`neighbors`/`inventory_qte` and no stable
  id; 4 `town_prices` and 4 `map_prices` entries with fully native
  `coins`/`cash`/`level` and no stable id, identical values as stored;
  50 `level_ranking_reward` entries with native integer `level`
  descending 50..1, native integer `cash` uniform 1, and a native
  single-entry `units` object mapping item-id keys to integer
  quantities).
- `config/patch/patches.txt` plus the five ordered patch files, read
  only to verify no patch targets any economy-schedule key (any such
  target fails the build explicitly; stored content is the input, there
  is no layering).
- `mods/mods.txt` (must stay inactive; any active mod fails the build).
- `packages/game-content/schemas/expansion_price.schema.json`,
  `town_price.schema.json`, `map_price.schema.json`, and
  `level_ranking_reward.schema.json` (contracts enforced by the builder).
- `packages/game-content/normalized/buildings.json`, `units.json`,
  `specials.json` (committed items outputs; their union of 900
  `legacy_id` values is the cross-domain reference set for ranking
  `units` keys).

## Coercion rules (`economy-coercion-ruleset-v1`, survey-cited)

- E1 native fields kept verbatim: every schedule amount is a native
  JSON integer carried exactly as stored (booleans never count as
  integers); `units` quantities are native positive integers. No
  string-encoded numbers, no embedded JSON, no empty strings occur in
  these four keys.
- E2 `legacy_id` preserves schedule identity: the 0-based positional
  index as a string with a numeric `position` field for the three price
  schedules (which carry no stable stored id and load positionally),
  and the decimal form of the native integer `level` for ranking
  rewards (rows cover 50..1 exactly once). Schedule order is preserved
  positionally; town and map schedules stay separate files even though
  their stored values are identical, never merged or deduplicated.
- E3 resolved ranking references: `unit_refs` carries the `units` keys
  sorted; every referenced id must resolve against the normalized items
  legacy-ID set or validation fails.

No value is rebalanced, renamed for gameplay, or assigned new meaning.

## Outputs

- `normalized/expansion_prices.json`: 98 price definitions (one per
  stored entry, stored order).
- `normalized/town_prices.json`: 4 price definitions (one per stored
  entry, stored order).
- `normalized/map_prices.json`: 4 price definitions (one per stored
  entry, stored order).
- `normalized/level_ranking_reward.json`: 50 reward definitions (one
  per stored entry, stored order).
- `manifest.json`: the existing items/quest/tables manifest with an
  `economy` section merged in, recording economy inputs with digests,
  the cross-domain items reference edge (files, counts, union size),
  the coercion ruleset version, the content fingerprint (sha256 over
  the stored source bytes plus the mods list), definition counts
  (including ranking level range, cash values, and the
  town/map-identical observation), builder outcome, output digests, and
  uniformity notes. Regenerated on every successful economy build; the
  tests assert it matches the produced output while the items, quests,
  and tables keys survive the merge untouched.

## Validation gates (failures exit 1, outputs unwritten)

Duplicate positional ids or ranking levels, ranking coverage other than
exactly 50..1, negative amounts, non-positive ranking quantities,
unresolvable ranking `units` references against the normalized items
set, `unit_refs` drift, missing or mistyped schema-required fields
(every schema-required field is enforced; the traceability test proves
it by mutation), and any round-trip difference (expected: exact
equality, since every field is native). The round-trip gate re-coerces
each stored entry and compares by value with field sets exact.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)).
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root (after the items build):

```bash
python -B packages/game-content/tools/build_economy.py
```

Exit 0 prints a JSON success report with counts and output files.
Exit 1 prints a `validation-failed` report listing each problem and
writes nothing (the manifest is left untouched). Exit 2 reports
invalid input or unsupported shapes (missing/unreadable files,
unparseable content, an active mod, a patch targeting economy content,
an invalid schema file, or a missing/malformed normalized items
output) on stderr.

## Evidence classification

This extension establishes source-grounded normalization consistency
for the stored economy-schedule domains: classification coverage,
verbatim native fidelity, cross-domain reference resolution for ranking
rewards against the normalized items package, and exact round-trip
equivalence. It is evidence of representation change, not of
served-byte equality, content validity, gameplay parity, asset
existence (M4 owns asset truth), or progressed-player coverage. Served
bytes stay out of scope exactly as in the content census
(`make_dynamic` never runs here).

## Containment

- Reads only `config/main.json`, `config/patch/patches.txt`, the five
  patch files (target check only), `mods/mods.txt`, the four economy
  schema files, the three committed normalized items outputs, and the
  package manifest for the merge (plus optional `--repo-root`/`--out-root`
  relocation of the same reads).
- Never imports or executes any legacy application module (no
  `get_game_config`, `jsonpatch`, or Flask import), never reads runtime
  saves, never contacts a network, never starts a server, and never
  opens a browser or Flash content.
- Writes only the four normalized economy files plus the merged
  `manifest.json`, and only on success. No bytecode (`-B` recommended),
  no caches, no temporary files in the repository. Repeated runs over
  unchanged inputs are byte-identical.
- The focused tests in `tests/test_build_economy.py` run the same way:

```bash
python -B -m unittest discover -s packages/game-content/tests -p test_build_economy.py -v
```
