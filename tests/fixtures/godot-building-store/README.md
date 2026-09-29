# Executed-legacy store fixture (`godot-building-store`)

The executed-legacy parity oracle for the Compatibility API v0 store
endpoint: one real `store_item` transaction captured from the real
legacy Flask server (design D9 of the `building-store` OpenSpec change).
No Flash, browser, Ruffle, ActionScript, or external network was involved —
only the legacy server on loopback under the pinned interpreter.

## How it was captured

```bash
python -B apps/compat-api/capture_store_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement/purchase/move/sell
fixture digests, discards the copy, and only then publishes this directory.
The opt-in legacy command recorder env var (`SOCIALWARS_COMMAND_RECORD_DIR`)
is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, move, and
sell captures):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed or the executed transaction did not match the
      derived envelope
6     Containment violation (working-tree bytes changed, a committed fixture
      directory changed, or the disposable corpus saves changed during server
      startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-building-store/
├── README.md                     (this file, hand-authored)
├── capture-manifest.json         (generated: schema, interpreter, server,
│                                  corpus, intent + derivations, steps,
│                                  containment digests, cleanup)
└── steps/
    ├── login_post/               POST / — 302, save byte-unchanged
    │   ├── request.json          form + headers (sanitized)
    │   ├── before.json           full canonical save
    │   ├── response.body         the executed 302 body
    │   ├── response.meta.json    status/headers/size/sha256 (sanitized)
    │   └── after.json            full canonical save (equal to before)
    └── command_store_item/       POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the row popped
                                  and the storage entry added
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because store parity
compares *state changes* on both the map and the storage.

## The transaction

Intent (constants in `capture_store_fixture.py`, verified against the
committed config and fresh save):

- **Building**: the Tree, item id `905` — 1×1, `type "b"`, `in_store 0`
  (a map decoration, not a shop item), `costs {"w":30}` (its *purchase*
  price, irrelevant here) — at legacy map key `"2"`, anchored at `(53,39)`
  (`[905, 53, 39, 0, 0, [], {}, 1]` in the fresh save).
- **Target rule**: none — a store has no target cell and no grid input. Slot
  `2` is chosen so this fixture's target differs from the move fixture's
  `11` and the sell fixture's `20` and the three stay independently readable.
- **Contract**: one intent only — a save id and the legacy map index. No
  price, no quantity, and no resource deltas are sent by the client; the
  envelope is derived server-side (below). The fresh save's `store` is `{}`,
  so the storage mapping is directly observable before and after.

Derived envelope (all values **derived-provisional**: the Flash client is
never executed, so the argument value a real store action sends and any
deltas it sends are unobservable — design D1/D2/D3/D6):

```json
{"accessToken":"", "commands":[[0,"store_item",[2],[0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

- `store_item` takes exactly **one** positional arg — the item index
  (`command.py:218-232`, and the `store_item` row of
  `docs/legacy-protocol/commands.md` / the `store_item` entry of
  `docs/legacy-protocol/commands.json`). It pops the row with
  `engine.map_pop_item(map, index)`, i.e. `map["items"].pop(str(index))`
  (`engine.py:42-47`), and adds the popped row's item id with
  `engine.add_store_item` (`engine.py:70-76`).
- `item_index` is the legacy map key as an integer; a missing row is legacy's
  silent early return, which the endpoint resolves itself before executing.
- No quantity argument exists: `add_store_item(map, item_id)` is called
  without its third argument, so the branch's quantity is always exactly 1
  and the contract accepts none.
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* the
  branch at `command.py:40`) and it is **all zeros** (design D2). The
  committed configuration records no price for storing anything: every item's
  `cost` is `"0"` and every `cost_type` is `null` (dead fields) and `costs`
  prices the *purchase* only, and the catalog records no capacity check
  ("Client moves any indexed item into storage; no capacity check").
  **This change therefore claims no storing cost and no capacity rule** — the
  neutral vector is a derivation boundary, not a claim about the legacy
  client.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.

Executed outcome (as recorded, verified by the tool before publishing):

- response `{"result":"success"}`;
- `maps[0].items["2"]` — `[905, 53, 39, 0, 0, [], {}, 1]` — is **absent**
  afterwards: legacy pops exactly that key (`command.py:221`,
  `engine.py:42-47`) and re-keys nothing;
- `maps[0].store` becomes `{"905": 1}` — the pop and the storage increment
  land together, and every other storage entry is unchanged (there were none);
- every other placement row byte-identical, and the placement count drops
  `40` → `39`;
- the **whole** `privateState` is byte-identical, including `boughtUnits`
  (`[]`) and `deadHeroes` (`{}`): unlike `buy`, `place_stored_item`, and
  `buy_stored_item_cash`, `store_item` calls **no** `bought_unit_add`, and
  this change reproduces that exactly rather than "fixing" it;
- `playerInfo` byte-identical;
- `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`,
  `playerInfo.cash 5`, `privateState.mana 0` — all unchanged, because the
  derived vector is neutral and the legacy clamp `max(…, 0)` therefore never
  rewrites a value.

`/maps/0/items/2` and `/maps/0/store/905` are the **only** differences
between the recorded before- and after-states, and neither is a clock
reading: `command.store_item` writes no timestamp, and `apply_resources`'
timestamp write is commented out in legacy (`engine.py:269`). Both saves are
byte-stable across reruns and store parity needs **no** time-dependent
normalization on the state.

## Sanitization

Records never carry secret-valued fields: `user_key` is recorded as
`<redacted>`, the disposable server's session cookie (`Cookie` and
`Set-Cookie`) is recorded as `<redacted>`, and `accessToken` is the
crafted empty placeholder (never a token value; a non-empty one would be
redacted too). The live requests always sent the real values — only the
records are redacted. Parity works from the recorded intent and saves,
never by replaying HTTP.

## Rerun behavior

Re-running the capture exits 0 and reproduces every file byte-identically
**except** these documented time-dependent fields:

- `captured_at_utc` in every `request.json` / `response.meta.json`, and
  `executed_at_utc` in `capture-manifest.json`;
- the HTTP `Date` response header (both steps);
- the envelope `ts` inside `command_store_item/request.json`'s `data` field,
  and therefore that field's sha256 digest.

Everything else — both save states, both response bodies, and the
envelope's single command, argument list, and neutral resource vector — is
byte-stable.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the five already committed fixture directories
(`tests/fixtures/godot-compatibility-boot/`,
`tests/fixtures/godot-building-placement/`, `tests/fixtures/godot-item-purchase/`,
`tests/fixtures/godot-building-move/`, and `tests/fixtures/godot-building-sell/`)
and fails closed if any of them changed during the run, so this capture can
never silently absorb an earlier change's evidence. Only the disposable copy
is written and it is removed on every exit path.

## What this fixture proves, and what it does not

**Proves** (replayed offline by `apps/compat-api/tests/test_store_parity.py`
and the endpoint's own tests, with no server and no network):

- the exact `store_item` batch envelope the Compatibility API derives for a
  store intent, and that the unchanged legacy dispatcher accepts it;
- that the executed transaction pops exactly the named row, adds exactly one
  storage entry, and writes nothing else — including `boughtUnits`;
- that the endpoint's response equals the captured response and that its
  corpus save equals the captured after-state for every stable field.

**Does not prove**:

- any Flash-observed behavior: the Flash client is never executed, so the
  command, its argument value, and its deltas are derived, never observed;
- that storing costs anything, or nothing, in the legacy client — the derived
  vector is neutral and the committed configuration records no storing price,
  so **no cost is claimed**;
- any storage **capacity** rule: legacy has no capacity check, and this change
  invents none;
- that a stored building can be used again: this line only moves a building
  *into* storage, so `place_stored_item` (storage → map) and
  `sell_stored_item` remain open legacy commands;
- anything about progressed players: the corpus is the committed
  fresh-player save;
- any gameplay, economy, or pixel parity beyond the recorded transaction.
