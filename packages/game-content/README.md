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
