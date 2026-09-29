# Executed-legacy construction fixture (`godot-building-construction`)

The executed-legacy parity oracle for the Compatibility API v0 construction
endpoint: one real **two-command** construction batch captured from the real
legacy Flask server (design D9 of the `building-construction` OpenSpec change).
No Flash, browser, Ruffle, ActionScript, or external network was involved —
only the legacy server on loopback under the pinned interpreter.

## How it was captured

```bash
python -B apps/compat-api/capture_construction_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes two requests, stops the server
(`taskkill /T /F` + port-free re-check), re-checks the working-tree
containment snapshot and the committed boot/placement/purchase/move/sell/
store/upgrade fixture digests, discards the copy, and only then publishes this
directory. The opt-in legacy command recorder env var
(`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, move, sell,
store, and upgrade captures):

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
      directory changed, or the disposable corpus saves changed during
      server startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-building-construction/
├── README.md                     (this file, hand-authored)
├── capture-manifest.json         (generated: schema, interpreter, server,
│                                  corpus, intent + established/derived split,
│                                  steps, omitted third step, time-dependent
│                                  leaves, containment digests, cleanup)
└── steps/
    ├── login_post/               POST / — 302, save byte-unchanged
    │   ├── request.json          form + headers (sanitized)
    │   ├── before.json           full canonical save
    │   ├── response.body         the executed 302 body
    │   ├── response.meta.json    status/headers/size/sha256 (sanitized)
    │   └── after.json            full canonical save (equal to before)
    └── command_construction/     POST …/command.php — 200, save mutated
        ├── request.json          form incl. the exact `data` field (sanitized)
        ├── before.json           full canonical save
        ├── response.body         `{"result":"success"}`
        ├── response.meta.json    status/headers/size/sha256 (sanitized)
        └── after.json            full canonical save with the row's
                                  timestamp re-stamped and its attribute bag
                                  carrying the countdown and the click counter
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
LF endings) — full documents rather than hashes because construction parity
compares *state changes* on the addressed row.

## The transaction

Intent (constants in `capture_construction_fixture.py`, verified against the
committed config and fresh save):

- **Building**: the placed **Turret I**, item id `22` — `type "b"`,
  committed `build_time "5"`, `clicks_to_build "1"`, `activation "0"`,
  `costs {"s":125}` (its *purchase* price, irrelevant here) — at legacy map
  key `"11"`, anchored at `(58,48)` (`[22, 58, 48, 0, 0, [], {}, 1]` in the
  fresh save).
- **Why this row**: the committed fresh-player corpus has **no construction
  in progress** — all 40 rows carry `attr = {}`, `timestamp = 0`, and
  `store = []` — so any construction fixture must *start* a build rather than
  observe one. Slot `11` is a Turret I, the same row the move fixture
  repositions **in its own independent transaction** (each capture seeds a
  fresh corpus from the same committed save), so the two fixtures stay
  independently readable; the upgrade fixture's slot `12` (Wall I), the sell
  fixture's slot `20` (Turret I), and the store fixture's slot `2` (the Tree
  decoration) are untouched by this one.
- **Contract**: one intent per construction step — a save id, the legacy map
  index, and one action. No duration, price, quantity, or resource delta is
  sent by the client; the envelope is derived server-side (below).

Derived envelope:

```json
{"accessToken":"",
 "commands":[[0,"activate",[11,5],[0,0,0,0,0,0,0,0]],
             [0,"add_click",[11],[0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

### Established versus derived — the provenance split

This is the eighth change in the same family and the second treated
investigation-first: the contract was established and recorded in
`docs/legacy-construction-timing.md` before this fixture was written, so the
boundary is drawn explicitly here too.

**Established from committed legacy source and executed-legacy evidence**

| Fact | Evidence |
| --- | --- |
| `activate(item_index, duration)` writes `item[3] = time_now()` and, when `duration > 0`, sets `item[6]["cp"] = duration`; when the duration is non-positive it **clears the whole attribute bag** `item[6] = {}` | `command.py:412-429`; the `activate` entry of `docs/legacy-protocol/commands.json` records both writes |
| `add_click(item_index)` raises `item[6]["nc"]`, seeding it to `1` when absent | `command.py:525-536`, `engine.py:125-130` |
| `activate_item_click(item_index)` deletes `item[6]["nc"]` | `command.py:537-548`, `engine.py:132-135` |
| All three write **only** the addressed row's `timestamp` and its attribute bag | the three source ranges above; the catalog records no other state write for any of them |
| The click counter is seeded by the **purchase** half, not by these commands: `engine.map_add_item` writes `attr["nc"] = 0` for a `player == 1` item whose config has `clicks_to_build > 0` | `engine.py:25-28` — this is why the delivered `building-upgrade` fixture's row arrives as `[24, 45, 49, <ts>, 0, [], {"nc": 0}, 1]` |
| **No server-side completion rule exists**: no branch compares `nc` with `clicks_to_build` | the five construction-adjacent branches write only `item[3]` and `item[6]`; the comparison is the client's |
| The `cp`/timestamp shape of an activation, and that remaining time is `cp - (now - item[3])` | investigation probe B: `activate(11, 3600)` on this very row gave `[22, 58, 48, <ts>, 0, [], {"cp": 3600}, 1]` |
| The counter's whole life, and that finishing clears it | investigation probe C: `add_click(11)`, `activate_item_click(11)`, then `activate(11, 0)` left `[22, 58, 48, <ts>, 0, [], {}, 1]` |
| `build_time` is the per-item build duration and `clicks_to_build` the per-item click requirement | `config/main.json`: Turret I `22` → `5` and `1`; walls `1`; Turret II `600`; Command Center II `3600`; the map decorations `180` with `clicks_to_build 0`; 427 further items record `build_time "0"` **in the loaded config the service derives from** (the five ordered patches add entries to the stored `config/main.json`, where 306 of the 778 stored items record `"0"` and none of them is a building), which is not a duration |
| `BUILD_SPEEDUP_PRICING = [5, 1]`, `BUILD_SPEEDUP_MIN_TIME = 10`, and `UPGRADE_SPEEDUP_PRICING = [5, 1]` price a construction *speedup*, not a build | the loaded `globals` of `config/main.json` |
| No configuration field prices building a building | item `cost` is `"0"` and `cost_type` is `null` across all items (dead fields) and `costs` prices the *purchase* only |

**Derived and never observed from the Flash client**

- that a real construction sends exactly these commands;
- that the `duration` a client sends to `activate` is the item's committed
  `build_time` rather than its `activation` field, the `build_time` of another
  tier, or a speedup-adjusted figure (this contract **derives** it from
  `build_time` server-side, so a client cannot influence the countdown at all);
- whether the client sends `activate_item_click` immediately at
  `nc == clicks_to_build` or only after a visual build effect, and whether a
  `cp` countdown is ever started for an item whose `activation` is `0`;
- the **price vector**: all zeros on both commands, so **no building cost is
  claimed at all** — not the item's own purchase price (`{"s":125}`), and
  nothing about speedups.

### The commands

- `activate` takes exactly two positional args — the legacy map index and the
  countdown (`command.py:413-414`, and the `activate` row of
  `docs/legacy-protocol/commands.md`). The index is the legacy map key as an
  integer: legacy resolves the row with `engine.map_get_item(map, index)`,
  i.e. `map["items"][str(index)]` (`engine.py:36-40`).
- `add_click` takes exactly one positional arg — the same legacy map index
  (`command.py:526`) — and raises the counter.
- `resources_changed` is the legacy 8-slot vector
  `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  (`engine.apply_resources`, `engine.py:251-271`, applied *before* the
  branch at `command.py:40`) and it is **all zeros on both commands**.
- `first_number 0`, `publishActions []`, `tries 1`, `accessToken ""` are
  documented placeholders; all five non-`commands` fields are parsed and then
  unread by legacy code, so the time-dependent `ts` has no behavioral effect
  (parity normalizes it).
- The `data` form field is `<64-hex sha256 of the payload>;<payload>`;
  legacy asserts only that byte 64 is `;` and never verifies the digest.
- `command()` executes the commands in list order and persists the save
  **once** after the whole batch (`command.py:19-32`), so the two commands
  are atomic with respect to the save file.
- Unlike the upgrade line, each construction **action** is a single-command
  batch: the endpoint executes exactly one command per request. The two
  commands are combined here only because the fixture records one build in
  progress with both halves visible.

### Why this two-command form, and the step that is recorded but not captured

The executed batch is a **start followed by a build click**, not a start, a
click, and a completion, for exactly one reason: the two-command form leaves
**both** the countdown and the click counter visible in the committed
after-state, which is what makes the fixture a useful oracle. Adding the
completing command would delete the counter and hide its value.

The third command — `activate_item_click`, which **deletes** `attr["nc"]` and
completes the build — is therefore **covered but not captured**:

- its effect is **established**, not assumed: it is committed legacy source
  (`command.py:537-548` → `engine.py:132-135`, which deletes
  `attr["nc"]` and writes nothing else) and it was **executed** against the
  real legacy server by the earlier recorded investigation
  (`docs/legacy-construction-timing.md`, probe C, whose final row is
  `[22, 58, 48, <ts>, 0, [], {}, 1]`);
- it is **covered by the endpoint's per-action post-execution proof**: after a
  `finish` action the row's attribute bag must **not** contain `nc`, and any
  other outcome fails closed with `internal_error`;
- its exact recorded command entry, the reason it is not part of this batch,
  and the fact that *when* the Flash client sends it is never observed, are
  all recorded in this fixture's `capture-manifest.json` under
  `omitted_step`.

The friend-assist cluster (`buy_si_help` / `finish_si` and the `attr["si"]`
bag, `command.py:549-572`, `engine.py:137-147`) shares the attribute bag and
is **out of scope**: this change must not imply a friend can be hired.

## Executed outcome (as recorded, verified by the tool before publishing)

- response `{"result":"success"}`;
- `maps[0].items["11"]` — `[22, 58, 48, 0, 0, [], {}, 1]` — becomes
  `[22, 58, 48, <wall-clock timestamp>, 0, [], {"cp": 5, "nc": 1}, 1]`:
  - the same **key** and the same **cell** `(58,48)`, the same
    `orientation 0`, the same `player 1`, and still no stored units — a
    construction action never destroys, moves, or re-keys a row;
  - `item[3]` becomes the **start instant** (`activate` stamps the current
    time), which is the one documented time-dependent leaf of the recorded
    state; the remaining countdown is `cp - (now - item[3])`, a **pure client
    derivation** over data the server never interprets;
  - `attr` becomes `{"cp": 5, "nc": 1}`: the start's countdown `cp` equals
    the item's committed `build_time`, and the click counter `nc` equals the
    item's `clicks_to_build` of `1`. **The server never compares them** — that
    the build is complete is the client's decision, established by the
    absence of any completion branch;
- the placement count stays `40` — no key is added or removed;
- every other placement row byte-identical;
- `maps[0].store` stays `{}` — a construction stores nothing;
- the whole `privateState` byte-identical, including `boughtUnits` (`[]`) and
  `deadHeroes` (`{}`): no construction command calls `bought_unit_add`,
  `push_dead_unit`, `buy_si_help`, or `finish_si`;
- `playerInfo` byte-identical;
- `xp 4`, `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`,
  `playerInfo.cash 5`, `privateState.mana 0` — all unchanged, because both
  derived vectors are neutral and the legacy clamp `max(…, 0)` therefore never
  rewrites a value.

Exactly **three** leaves differ between the recorded before- and after-states,
and exactly **one** of them is a clock reading (asserted by
`apps/compat-api/tests/test_construction_parity.py`):

| leaf | change |
| --- | --- |
| `/maps/0/items/11/3` | `0` → a wall-clock start stamp — **the documented time-dependent field** |
| `/maps/0/items/11/6/cp` | absent → `5` — the derived countdown |
| `/maps/0/items/11/6/nc` | absent → `1` — the raised click counter |

The `attr` bag as a whole therefore goes `{}` → `{"cp": 5, "nc": 1}`.

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
**except** these documented time-dependent fields. Verified by a leaf-level
diff of two consecutive runs: 11 differing leaves in total, every one of them
named in the manifest's `time_dependent_fields.leaves`:

- `/captured_at_utc` in every `request.json` / `response.meta.json`;
- `/executed_at_utc` in `capture-manifest.json`;
- `/headers/Date` in both `response.meta.json` files;
- the envelope `ts` inside `command_construction/request.json`'s
  `/form/data` (and therefore that field's sha256 digest);
- the row's re-stamped wall-clock start time at
  `steps/command_construction/after.json`'s `/maps/0/items/11/3`, and the two
  manifest leaves derived from it — `/transaction/row_after/3` and
  `/transaction/steps/1/save_after_sha256`.

Everything else — both save states, both response bodies, and the envelope's
two commands, their order, both argument lists, the derived duration, and both
neutral resource vectors — is byte-stable.

## Containment

The tool snapshots SHA-256 digests of every working-tree group it reads
(root `*.py`, `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`) before the run and after the server stops, and
fails with exit 6 before writing anything if a single byte changed
(combined digest for this capture: `18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724`).
It additionally digest-pins the seven already committed fixture directories
(`tests/fixtures/godot-compatibility-boot/` →
`4d389707e0f18676fb23b3a2a8a47031b4e233366e4066437f8bad6854e15234`,
`tests/fixtures/godot-building-placement/` →
`546a5f00e5e45319ffd17f5ee67201dd2b72cb21de833a3e35e8a9a98d60c5a8`,
`tests/fixtures/godot-item-purchase/` →
`d05e5b92b26a1222774bb32e76a42417c692e65ee1b87abdb8a2f4e6cd84e813`,
`tests/fixtures/godot-building-move/` →
`b3c477a7947fbe409330f03a8658cdca707a2631b52d1d4c5127f440619799c1`,
`tests/fixtures/godot-building-sell/` →
`fa85af3fb12ef8b9298203a64632b6d7b31c1ed48f8d1ba716151f25ec7ab1c4`,
`tests/fixtures/godot-building-store/` →
`d4dff84132353a60e3a005c42d067185772ec8d6a2548ffdc5aa4779a2055194`, and
`tests/fixtures/godot-building-upgrade/` →
`398675ad94928dd75f7fbcd9f62e082d73ee973d3c973f5bbdf44a083a9c0521`) and
fails closed if any of them changed during the run, so this capture can never
silently absorb an earlier change's evidence. Only the disposable copy is
written and it is removed on every exit path; no working-tree save is ever
written; the service never binds anywhere but `127.0.0.1`.

## Tests and claim limits

Offline unit tests for the derivation, the capture contract, the endpoint,
and the executed-legacy replay:

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

(`test_construction_envelope.py` for the derivation, the action vocabulary,
sanitization, and the capture contract; `test_construction_endpoint.py` for
the `/v0/construction` structural contract, the three actions and their
post-conditions, the per-action post-execution proof, and corpus-only
persistence; `test_construction_parity.py` consumes this fixture and replays
the recorded intent's two actions through the endpoint offline.)

### What this fixture proves

- the exact two-command batch the Compatibility API derives for a construction
  start followed by a build click, and that the unchanged legacy dispatcher
  accepts it;
- that the executed transaction rewrites **exactly one** row in place — the
  same key, cell, item, orientation, store, and player — writing only its
  timestamp and its attribute bag, and changes nothing else in the save;
- that the countdown equals the item's committed `build_time` and the click
  counter reaches its committed `clicks_to_build` while **no** server branch
  compares the two;
- that the endpoint's responses and its corpus save equal the captured
  response and after-state for every stable field.

### Claim limits

- Parity covers **this one recorded construction transaction against the
  fresh-player corpus** — not progressed players, not other commands, not a
  second construction, and not the friend-assist cluster. The committed corpus
  has no build in progress, so a single transaction is the whole corpus-side
  story available here.
- That a real construction sends these commands, and that the duration is the
  item's committed `build_time` rather than its `activation` field or a
  speedup-adjusted figure, is **derived** and never observed from the Flash
  client. The commands' argument shapes, their effects, the purchase-side
  seeding of the counter, the countdown's shape, the clearing branch, the
  absence of any server-side completion rule, and the resulting state are
  **established**.
- The completing command is **recorded but not captured** here: its effect is
  established by the earlier executed investigation and by committed legacy
  source, and it is covered by the endpoint's per-action `finish`
  post-execution proof rather than by this fixture's after-state.
- **No building cost is claimed.** The committed configuration records no
  price for building anything, prices travel only in client-sent deltas that
  this contract refuses, and therefore both derived vectors are neutral. That
  is a derivation boundary, not a claim that building is free in the legacy
  client. Nothing is claimed about `BUILD_SPEEDUP_PRICING` /
  `BUILD_SPEEDUP_MIN_TIME` / `UPGRADE_SPEEDUP_PRICING` either, and
  construction **speedups are out of scope**: no speedup command is in this
  contract and inventing one would fabricate a price.
- The **click threshold and the remaining time are client-side derivations
  with no server enforcement**: no branch compares `nc` with
  `clicks_to_build`, and `cp - (now - item[3])` is computed by the client from
  data the server never interprets. Legacy performs no ownership, state, or
  gameplay validation for a construction either, so the endpoint's validation
  is structural fail-closed only: whether a build may start on a row that
  already carries construction state is a client-side display rule, and
  authoritative server-side validation belongs to Server v1 / M13. An index
  that names no row is answered with `unknown_item_index` rather than legacy's
  silent early return; an action outside the closed set with `invalid_action`;
  a placement whose item has no resolvable positive committed build time with
  `no_build_time` before the dispatcher runs; and a post-state that is not the
  promised construction fails closed with `internal_error`.
- The **attribute-bag-clearing branch is never used as a cancel**: legacy's
  `activate` with a non-positive duration clears the *entire* bag, destroying
  the click counter and any friend-assist entries, so this contract only ever
  sends a positive derived duration, refuses a non-positive one twice over,
  and exposes **no "cancel build" action**. Any future cancel path must not
  route through `activate(…, 0)`.
- The **friend-assist mechanism is out of scope**: `buy_si_help` /
  `finish_si` and the `attr["si"]` bag belong to social behaviour, so no
  friend can be hired or finished here even though they share the bag.
- The upgrade line's deliberately unconsumed `{"nc": 0}` seed is **not**
  consumed by this change either: doing so would need a `sell`+`buy`+build
  batch that re-derives the upgrade contract inside this change, so the
  counter's origin is covered by the endpoint's own tests over the delivered
  upgrade fixture instead.
- The premium upgrade path, `orient`, `collect`, town expansion, resources,
  XP, and anything server-authoritative are later deliver lines.
- No Flash, Ruffle, ActionScript, or browser executes, no external network is
  used, and no pixel-parity oracle against the legacy client exists.
