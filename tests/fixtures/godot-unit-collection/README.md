# Executed-legacy collection fixture (`godot-unit-collection`)

The executed-legacy parity oracle for the Compatibility API v0 collection
endpoint: a real **`complete_collection`** against the committed corpus's
**empty** storage and **empty** collection ledger, carrying a **neutral**
vector, captured from the real legacy Flask server (design D1/D6 of the
`godot-unit-collection` OpenSpec change).  No Flash, browser, Ruffle,
ActionScript, or external network was involved — only the legacy server on
loopback under the pinned interpreter.

This is M8 line 5 of 8, and the **first content-derived, server-authoritative
unit acquisition in the project**: the client names *which* collection and the
server looks up *what it grants* in the committed `collections` table.

## What was captured, and why this one is different

`command.complete_collection` (`command.py:504-523`) is the **only** legacy
server-side grant in the unit area whose contents come out of **committed
content**:

```python
collection_id = args[0]
bought = args[1]
prize = get_collection_prize(collection_id)      # committed table
for key in prize:
    add_store_item(map, int(key), prize[key])     # engine.py:70-75
...
if collection_id not in privateState["collections"]:
    privateState["collections"].append(collection_id)
```

and `get_collection_prize` (`get_game_config.py:170-175`) does
`index = max(0, collection - 1)` against the loaded configuration's
`collections` **list**, then returns `json.loads(collections[index]["prize"])`.

So the recorded request carries a collection id and nothing else, and the
recorded after-state holds exactly what the committed table says that
collection grants.

| | value |
| --- | --- |
| collection id sent | `1` |
| committed collection | `1` — **Draggy Collection** |
| committed prize | **`{"1085": 1}`** |
| granted item | **unit `1085`, Metal Draggy** (committed `type` `u`) |
| `maps[0]["store"]` | `{}` → `{"1085": 1}` |
| `privateState["collections"]` | `[]` → `[1]` |
| every other map field, row, private-state key, and player-info field | byte-identical |
| all seven stored resources | unchanged (`xp` 4, `gold`/`wood`/`oil`/`steel` 2000, `cash` 5, `mana` 0) |
| placement count | **40 → 40** (no row is written) |
| response | `{"result": "success"}` |

The corpus records `maps[0]["store"] == {}` and
`privateState["collections"] == []`, so the committed grant is a **real,
observable write** against an empty storage and an empty ledger — **no
fabricated player state** is involved.

The recorded transaction's own leaf-level diff is exactly two paths:
`/maps/0/store/1085` and `/privateState/collections`.  The ledger reports at
the *container* path rather than as an appended index because a list that grows
differs at the list itself; the capture pins both observed paths.

## Six of the ten committed collections grant a unit

The other five unit prizes (1062 MegaBot, 1096 F-117, 1073 Erradicator, 1010
APC, 1056 Elephant rider) and the four building prizes (164 Laser Turret, 45
Dual-Rocket Turret, 136 General Sculpture, 106 Fountain) are equally
exercisable against the same corpus.  Probe 2 below completes collection 10, so
the fixture evidences **two** of them.

## What is NOT in this fixture, stated up front

**The stored-item placement step was deliberately NOT chained (design D6).**
`complete_collection` → `map["store"]` → `place_stored_item` is a two-step,
fully committed, server-derived path by which a unit enters a town, and this
fixture records **only the first step**.  The round trip is a **separate carried
follow-up**.  **This fixture therefore evidences a committed grant into storage
and NOT a unit placed on the map**: the placement count is unchanged at 40, no
map row is written, and no unit is garrisoned.

**No eligibility check was captured, because none exists (design D2).**  Nothing
in the legacy source verifies that a collection's items were collected.  The
committed `item_ids` requirement list is read by **no** branch at all (zero
quoted `"item_ids"` occurrences across the ten legacy root modules), and the
only read of `privateState["collections"]` is the append-if-absent test at
`command.py:517`.  So a caller may name **any** of the ten committed
collections.  This is a **recorded authority gap**, not a fixed one: adding a
check would invent a rule the legacy server does not have, and authoritative
validation belongs to a later server-authoritative milestone.

**No unit income, no cap semantics, and no experience are captured, because
none exist to capture (design D5).**  The `collect` command is field-agnostic —
the whole branch re-stamps the row's slot-3 instant and does nothing else — and
`collect_type`, `collect_xp`, `max_collects`, `max_elem_vol`, and `harvester`
have **zero** legacy reads; the single quoted `"collect"` is the *branch name* at
`command.py:136`.  On the content side, **0 of 429** units record a positive
`collect` and `max_collects` is `0` on **all 429** units, so the cap
`building-collect` deliberately refused has **no unit analogue**.  `collect_xp`
is non-zero on 427 units but is never read, and the only command writing a
placed row's `attr["xp"]` takes a **client-sent** amount that the delivered
`godot-unit-production` requirement already refuses.

`harvester` is **not a committed content field at all**: the string occurs five
times in the stored configuration and every one of them is a flag key inside a
committed `properties` blob — unit `1001` Worker I, `1039` Worker II, `1040`
Worker III, `1041` Worker IV, `1125` Orc Worker — all five recording `collect`
`0`.  (This **corrects** the committed investigation's framing of `harvester` as
a committed item field carrying a positive value on five units.)

## The two executed probes

Both run against the **same live server**, after the recorded step, and are
recorded in the manifest rather than as steps because they are evidence for the
derivation's guarantees rather than transactions of this fixture.

**Probe 1 — the neutral vector is necessary, and the ledger is idempotent.**
`complete_collection([1, 0])` with a **client-sent** vector
`[0, 500, 0, 0, 0, 0, 0, 0]`:

* `maps[0]["store"]` grew `{"1085": 1}` → `{"1085": 2}` — the committed bag was
  granted **again** from an **already-completed** collection;
* `privateState["collections"]` **stayed** `[1]` — the append is *if-absent*, so
  the **ledger is idempotent while the grant is not**;
* `xp` moved `4` → `504`, i.e. by exactly the **sent** delta, because
  `apply_resources` runs **before** the branch (`command.py:40`,
  `engine.py:251-271`) as `max(current + delta, 0)`;
* every other stored resource and field was untouched.

Without probe 1 the endpoint's "every stored resource is unchanged" proof would
be a tautology, and the append-if-absent rule would be asserted rather than
observed.

**Probe 2 — no eligibility check exists.**  `complete_collection([10, 0])`
completes collection `10` **Animal Collection**, whose committed `item_ids` are
`[61, 62, 63, 64, 65]` and whose committed prize is unit `1056` Elephant rider.
The corpus places **none** of those five items.  The legacy server answered
`{"result": "success"}`, granted `1056: 1` into the storage, and appended `10`
to the ledger.

## The index is one-based, and the clamp is an alias

`collection - 1` implies a **1-based** collection id, and it is recorded as
**derived-provisional** with the **zero-based** alternative retained.  It is
corroborated by the stored content rather than merely plausible:
`config/main.json` carries ten rows whose own native `id` column runs
`"1".."10"` over the ten **array positions** `0..9`, so `collection - 1` maps
that native id onto exactly its own position.  The zero-based reading is
rejected because it leaves the last committed collection (id `"10"`, the only
one granting a mounted unit) unreachable.

`max(0, collection - 1)` clamps **below** the requested index, so **collection
id 0 and collection id 1 resolve to the same committed prize** — as does every
negative id.  That alias is reported, never hidden, and the endpoint refuses an
out-of-range id **before** the dispatcher runs, because there
`get_collection_prize` returns `None` and the branch's next statement
(`for key in prize`) raises `TypeError`.

## How it was captured

```bash
python -B apps/compat-api/capture_collection_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes the recorded login plus the one recorded
command, runs the two **probe** requests against the same server, stops the
server (`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the twelve already-committed fixture directories,
deletes the disposable copy, and only then publishes the staged fixtures.

Exit codes: `0` success · `1` unexpected error · `2` environment/precondition
(refused derivation included) · `3` port `127.0.0.1:5055` busy · `4` legacy
server failed to start, crashed, or the port stayed busy · `5` a request failed,
returned an unexpected status, or the executed transaction did not match the
derived envelope · `6` containment violation · `7` fixture write failure.

## Containment

* the disposable copy lives under the system temp root and is removed on both
  success and failure (unless `--keep-disposable` is passed for debugging);
* `SOCIALWARS_COMMAND_RECORD_DIR` is stripped from the child environment, so the
  run writes no command recorder output into the working tree;
* every working-tree read group is SHA-256 snapshotted before the run and again
  after the server stopped; a difference fails the run **before** any fixture is
  written;
* the twelve already-committed fixture directories (boot, placement, purchase,
  move, sell, store, upgrade, construction, collect, expand, level, queue) are
  digest-pinned for the same reason;
* fixtures are staged outside the working tree and moved in only after every
  check passed, so a failed run writes nothing into the repository;
* `user_key` is redacted in every recorded form and `accessToken` in every
  recorded envelope; the envelope's SHA-256 digest is left intact so the
  redaction stays auditable.

## Determinism and time-dependent fields

Unlike the move, collect, and queue fixtures, this transaction carries **no**
time-dependent state value at all: `complete_collection` writes only the storage
and the collection ledger, and neither touches a clock.  The only wall-clock
values are record metadata (`captured_at_utc`, `executed_at_utc`, the HTTP
`Date` header) and the envelope's `ts`, all listed in
`capture-manifest.json` under `time_dependent_fields.leaves`.  Parity therefore
applies **no clock normalization**: the granted id and quantity are compared by
value against the committed bag, the ledger is compared entry by entry, and
every stored resource is compared by value.