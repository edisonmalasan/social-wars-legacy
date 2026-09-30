# Compatibility API v0 (`apps/compat-api`)

Read-only loopback bootstrap service that answers from the **unchanged legacy
modules** themselves — the Flask app imports `get_game_config`,
`get_player_info`, `sessions`, `engine`, and `version` and initializes them in
`server.py`'s order. It exists so the Godot client can obtain the session list
and one player's boot payload without Flash, without touching the working tree,
and without any persistence path.

## Contract

- Binds **only** `127.0.0.1`, port `5056` (`--port` / `COMPAT_API_PORT`
  override; there is deliberately no host option).
- Read-only: no route imports or calls `sessions.save_session`, opens no file
  for writing, and never serves from the working tree — it serves a disposable
  corpus (below).
- Everything under this directory runs with the pinned CPython 3.9.13
  interpreter and `-B` (no `__pycache__` next to preserved sources).

## Start command

From the repository root (pinned interpreter; `python` here is never the PATH
alias):

```bash
python -B apps/compat-api/run.py
```

Optional: `--corpus PATH` (or `COMPAT_CORPUS`) to use an explicit corpus,
`--keep-corpus` to keep a corpus this run created, `--port N` to move off
5056.

Exit codes: `0` clean stop (Ctrl+C / Ctrl+Break), `2` usage, environment, or
corpus/legacy initialization failure, `3` port already in use, `4` any other
server failure.

### Disposable corpus mechanics

The legacy modules resolve every path from the process working directory
(`bundle.py` uses `"."` paths), so `run.py` builds a temporary corpus under the
system temp directory (prefix `socialwars-compat-`) and `chdir`s into it
*before* the first legacy import:

- the corpus carries copies of `config/`, `mods/`, `villages/` and a `saves/`
  directory seeded from `tests/saves/fresh-player.json` (copied byte-for-byte);
- a corpus without `saves/` is refused — legacy `load_saves()` would otherwise
  create one;
- `config/main.json` must be byte-identical to the repository config, because
  the legacy configuration is read exactly once, at first import;
- the corpus this run created is deleted on exit (also on the port-busy exit
  path). `run.py` leaves the corpus directory before deleting it: the process
  was sitting inside it, and Windows refuses to remove a live working
  directory. A pre-existing `--corpus PATH` is never deleted.

## Endpoints

`GET /v0/session`

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790449969,
 "saves": [{"id": "...", "name": "Warrior", "xp": 4, "level": 1}]}
```

`saves` is the legacy `all_saves_info()` list with `userid` renamed to `id`.

`POST /v0/bootstrap` with body `{"user_id": "<save id>"}` returns the session
envelope plus:

```json
{"config": { ... legacy get_game_config() payload ... },
 "player_info": { ... legacy get_player_info() payload ... }}
```

**Documented deviation (design D3):** the bootstrap envelope also carries
`saves`. D3 lists only `config` and `player_info`; the extra key is a strict
superset of D3 and keeps the envelope uniform for the boot client (one shape,
plus the two payload keys).

`POST /v0/place` with body `{"user_id", "item_id", "x", "y", "orientation"?}`
is the one state-mutating surface of the API. The body is an **intent only**:
extra keys, including client-supplied resource deltas, are ignored. The
endpoint derives the legacy batch envelope internally — price vector from the
loaded config, smallest positive free slot, the documented placeholders — all
values **derived-provisional**, because the Flash client is never executed
(design D4 of the `building-placement` change). It then validates structurally
(fail-closed) and executes through the unchanged legacy `command()`
dispatcher in-process over the service corpus. Success returns the legacy
answer plus the authoritative superset:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790609721, "result": "success",
 "placement": [1, 51, 39, 1790609721, 0, [], {"nc": 0}, 1],
 "resources": {"xp": 4, "gold": 2000, "wood": 1970, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `result` is the legacy string verbatim; `placement` is the persisted
  eight-field entry (`item, x, y, timestamp, orientation, store, attr,
  player`); `resources` are the authoritative current values the client
  applies verbatim (design D7). `timestamp` is the server wall clock at
  execution — the one time-dependent field, normalized in parity.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_id` present in the loaded config (`bool` excluded), and
  anchor-based `x`/`y` in `0..99` (`GRID_EXTENT=100`; footprints may extend
  past the edge exactly as legacy placements already do). Occupancy and
  affordability are gameplay rules: the client enforces them for display
  (design D5), while insufficient funds reproduce the legacy `max(…, 0)`
  clamp rather than a rejection — server-side validation belongs to
  Server v1 / M13.

`POST /v0/purchase` with body `{"user_id", "item_id"}` is the second
state-mutating surface (the `building-purchase` change). The body is an **intent
only**: extra keys, including a client-supplied `price`, `quantity`, or resource
delta, are ignored. The endpoint derives the legacy batch envelope internally —
the **cash-only** price from the item's loaded config `costs`, one
`buy_stored_item_cash` command whose single argument is the item id, and the
documented placeholders, all values **derived-provisional** (design D2 of
`building-purchase`) — then executes the unchanged legacy `command()` dispatcher
in-process over the service corpus. Success returns the legacy answer plus the
authoritative superset:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790649056, "result": "success",
 "store": {"105": 1},
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 0, "mana": 0}}
```

- `result` is the legacy string verbatim; `store` is the **full** post-execution
  storage mapping `{str(item_id): int}` (quantity `0` and unresolvable ids
  preserved, never filtered) so the client needs no arithmetic; `resources` are
  the authoritative current values the client applies verbatim (design D4). This
  payload carries no time-dependent field beyond `server_time`.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_id` present in the loaded config, and a **cash-only** config
  price. An item priced in another resource (or mixed, or unpriced) fails closed
  with `costs_not_cash` — a derivation boundary for this command, not a gameplay
  rule: the client never offers such an entry, and any-price storage acquisition
  is the separate `store_add_items` grant path this change does not cover. The
  level gate and cash affordability are gameplay rules the client enforces
  (design D5), while insufficient cash reproduces the legacy `max(…, 0)` clamp
  rather than a rejection.

`POST /v0/move` with body `{"user_id", "item_index", "x", "y"}` is the third
state-mutating surface (the `building-move` change). The body is an **intent
only**: extra keys, including a client-supplied price, `resources_changed`, or
the arguments legacy discards (`frame`, `string`), are ignored. The endpoint
resolves `item_index` against the save's own `map["items"]` **before** executing
— legacy's missing-item path is a silent early return that still persists, so
reporting it as success would claim a change that never happened — then derives
the legacy batch envelope internally (one `move` command whose arguments are
`[item_index, x, y, frame, string]`, the `frame`/`string` placeholders legacy
discards, and a **neutral** resource vector, design D2 of `building-move`) and
executes the unchanged legacy `command()` dispatcher in-process over the service
corpus. Success returns the legacy answer plus the same authoritative superset
shape as `/v0/place`:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790657765, "result": "success",
 "placement": [22, 58, 47, 0, 0, [], {}, 1],
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `placement` is the persisted eight-field row **re-read from the save after
  execution** (`item, x, y, timestamp, orientation, store, attr, player`), so
  the client reuses the placement result type; `resources` are the authoritative
  current values. A move derives a neutral vector because the committed config
  records no move price, so a real move never changes resources.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_index` present in the save, and anchor-based `x`/`y` in
  `0..99`. Grid bounds, footprint occupancy (with the moving building's own
  cells excluded), and refusing a no-op move are gameplay rules the client
  enforces (design D5); there is no server-authoritative validation.

`POST /v0/sell` with body `{"user_id", "item_index"}` is the fourth
state-mutating surface (the `building-sell` change). The body is an **intent
only**: extra keys - including a `reason`, a price, a refund, or a resource
delta - are ignored, so the legacy combat reason that would route a row through
the resurrectable-unit path is unreachable through this endpoint. The endpoint
resolves `item_index` against the save's own `map["items"]` and reads that row
**before** executing (legacy's missing-item path is a silent early return that
still persists, so accepting it would claim a removal that never happened), then
derives the legacy batch envelope internally (one `sell` command with arguments
`[item_index, reason]`, the reason **derived** as the empty string legacy
compares against `"KILL"` and otherwise uses as a log label, and a **neutral**
resource vector, design D2 of `building-sell`) and executes the unchanged legacy
`command()` dispatcher in-process over the service corpus. Success returns the
legacy answer plus an authoritative superset naming the removal:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790665230, "result": "success",
 "removed": [22, 41, 48, 0, 0, [], {}, 1],
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `removed` is the eight-field row **as read before execution** (`item, x, y,
  timestamp, orientation, store, attr, player`), so the client can match exactly
  what disappeared; the service separately proves the key is absent from the
  persisted save after execution and fails closed otherwise. `resources` are the
  authoritative current values.
- **No refund is claimed.** The derived vector is neutral because the committed
  configuration records no building-sale refund rule (item `cost`/`cost_type`
  are dead fields, `costs` prices the purchase only, and
  `MARKET_SELL_PERCENTAGE` governs the resource market), the legacy refund
  travels only in client-sent deltas this contract refuses, and refund economics
  belong to Server v1 (M13) and the later *resources* line. A sale therefore
  removes the building and changes no balance.
- Validation is structural only: a JSON object body, a resolvable save id, and a
  strict-int `item_index` present in the save. Sellability and addressability are
  client-side rules (design D6); no server-authoritative validation exists.

`POST /v0/store` with body `{"user_id", "item_index"}` is the fifth
state-mutating surface (the `building-store` change). The body is an **intent
only**: extra keys - including a price, a quantity, or a resource delta - are
ignored. The endpoint resolves `item_index` against the save's own
`map["items"]` and reads that row **before** executing (legacy's missing-item
path is a silent early return that still persists), then derives the legacy
batch envelope internally (one `store_item` command whose single argument is
the item index, and a **neutral** resource vector, design D2 of
`building-store`) and executes the unchanged legacy `command()` dispatcher
in-process over the service corpus. Success returns the legacy answer plus a
two-sided authoritative superset:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790670611, "result": "success",
 "removed": [905, 53, 39, 0, 0, [], {}, 1],
 "store": {"905": 1},
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `removed` is the eight-field row **as read before execution** (the same
  record the sell line established); `store` is the **full** post-execution
  storage mapping, exactly what the purchase response carries, so the client
  needs no arithmetic for pre-existing contents; `resources` are the
  authoritative current values.
- The service proves both halves after execution: the popped key is absent
  from the map and the storage entry is present, failing closed with
  `internal_error` otherwise.
- **No storing cost and no capacity rule are claimed.** The derived vector is
  neutral because the committed configuration records no price for storing
  (item `cost`/`cost_type` are dead fields, `costs` prices the purchase only)
  and the catalog records that the legacy server has no capacity check; the
  refund-style economics belong to Server v1 (M13) and the later *resources*
  line.
- Unlike `buy`, `place_stored_item`, and `buy_stored_item_cash`, the
  `store_item` branch does **not** write `boughtUnits`; the endpoint reproduces
  that exactly rather than "fixing" it.
- Validation is structural only: a JSON object body, a resolvable save id, and
  a strict-int `item_index` present in the save. Storability and addressability
  are client-side rules (design D5); no server-authoritative validation exists.

`POST /v0/upgrade` with body `{"user_id", "item_index"}` is the sixth
state-mutating surface (the `building-upgrade` change) and the first one whose
legacy contract was **established by investigation** rather than chosen. The
body is an **intent only**: extra keys - including a target tier, a reason,
coordinates, an orientation, a player, a price, or a resource delta - are
ignored. The endpoint resolves the target tier from the committed configuration
(`upgrades_to`, with `-1`, `0`, and unresolvable values meaning "no path"), reads
the row before executing, and derives **both** legacy commands from the row's own
cell, orientation, and player:

```json
{"accessToken":"", "commands":[
   [0, "sell", [12, "UPGR"], [0,0,0,0,0,0,0,0]],
   [0, "buy",  [12, 24, 45, 49, 1, 0, 0, ""], [0,0,0,0,0,0,0,0]]],
 "first_number":0, "publishActions":[], "tries":1, "ts":<capture time>}
```

Success returns the legacy answer plus an authoritative superset naming both sides
of the replacement:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790683377, "result": "success",
 "removed": [23, 45, 49, 0, 0, [], {}, 1],
 "upgraded": [24, 45, 49, 1790683377, 0, [], {"nc": 0}, 1],
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

`removed` is the row **as read before execution** and `upgraded` is that row
**re-read after execution**; both are the same eight-field entry the other
gameplay surfaces use. `upgraded[3]` is a fresh wall-clock `timestamp` and
`upgraded[6]` is the `{"nc": 0}` construction seed `engine.map_add_item` writes for
items with `clicks_to_build > 0` - reported as it arrives and deliberately not
consumed, because the construction timers belong to the next M7 deliver line.

- **The order is forced and success is not proof.** The dispatcher has no
  `upgrade` branch, so an upgrade must be a pair; the reason is the committed
  constant `constants.py:970` `SELL_REASON_UPGRADE = "UPGR"`; and `buy` takes a
  **client-supplied** map key and cell (`command.py:42-58`), so the pair can reuse
  the exact key. The reverse order also answers `{"result":"success"}` and leaves
  the key **absent** (40 -> 39 placements) - legacy reports success either way, so
  the endpoint requires three post-execution facts before it reports success: the
  key still exists, its item id equals the derived target tier, and its cell equals
  the pre-execution cell. Anything else is a fail-closed `internal_error`.
- A placement with no resolvable next tier answers `no_upgrade_path` (400)
  **before** the dispatcher runs: a building that cannot be upgraded must never be
  reduced to a bare sale.
- **No upgrade cost is claimed.** Both commands carry the neutral derived vector:
  no configuration field prices an upgrade (item `cost`/`cost_type` are dead
  fields, `costs` prices the purchase only, and the 139 `premium_upgrade_costs`
  entries belong to the unproven premium path), and a client-sent delta would let
  any client mint resources.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_index` present in the save, and a resolvable upgrade path.
  Upgradability is a client-side rule (design D7); no server-authoritative
  validation exists.

**Provenance - established versus derived.** Established from committed legacy
source and executed-legacy captures: there is no upgrade command among the 63 named
branches; the `UPGR` reason constant; `buy`'s client-supplied key and cell; the
fresh-row semantics (`timestamp_now()`, `store: []`, the `{"nc": 0}` seed); the
`bought_unit_add` record (appended only when the tier is not already listed,
`engine.py:86-89`); the forced order; and the resulting state. Derived and never
observed from the Flash client: that the client sends exactly this pair, the buy
half's `orientation`/`playerID`/`unknown`/`reason` arguments, and the price vector.

`POST /v0/construction` with body `{"user_id", "item_index", "action"}` is
the seventh state-mutating surface (the `building-construction` change) and the
second whose contract was established by investigation rather than chosen - the
investigation is committed as `docs/legacy-construction-timing.md`. The body is
an **intent only**: the client names a placement and one of three documented
actions, and the endpoint derives the legacy command and every one of its
arguments. A `start` action derives its countdown from the item's **committed
`build_time`**, so - unlike every earlier surface - no client value can influence
it at all; extra keys such as a `duration` are ignored.

```
action     derived command                derived arguments
--------   ----------------------------   ---------------------------------
"start"    [0, "activate",        [i, D]]  D = the item's committed build_time
"click"    [0, "add_click",       [i]]     -
"finish"   [0, "activate_item_click", [i]] -
```

Success returns the legacy answer plus an authoritative superset naming both sides
of the in-place update:

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790690555, "result": "success",
 "previous": [22, 58, 48, 0, 0, [], {}, 1],
 "row": [22, 58, 48, 1790690555, 0, [], {"cp": 5, "nc": 1}, 1],
 "action": "start",
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- `previous` is the row **as read before execution** and `row` is that row
  **re-read after execution**; both are the same eight-field entry the other
  gameplay surfaces use. `row[3]` is the construction's start instant (wall-clock,
  and the fixture's one documented time-dependent field).
- **A per-action post-execution proof is required before success is reported**
  (design D3): the row must still exist and its `attr` be a mapping, then `start` ->
  `attr["cp"]` equals the derived duration, `click` -> `attr["nc"]` is an integer of
  at least `1`, `finish` -> `attr["nc"]` is absent. Anything else is a fail-closed
  `internal_error`. The upgrade line showed that legacy answers
  `{"result":"success"}` for a batch that *destroys* the row, so this check is
  load-bearing rather than decorative.
- The `activate` branch that clears the row's whole attribute bag (destroying the
  click counter and any friend-assistance state) is **never used**: the contract
  only ever sends a positive derived duration and exposes no cancel.
- **No building cost is claimed.** Every action carries the neutral derived
  vector: no configuration field prices a build, and the speedup prices
  (`BUILD_SPEEDUP_PRICING`, `BUILD_SPEEDUP_MIN_TIME`, `UPGRADE_SPEEDUP_PRICING`)
  price speedups, which are out of scope. The click threshold and the remaining
  time are **client-side derivations** with no server enforcement - no branch
  compares the counter with the item's click requirement, and the countdown minus
  the elapsed time is never computed server-side.
- Validation is structural only: a JSON object body, a resolvable save id, a
  strict-int `item_index` present in the save, an action in the documented set,
  and - for `start` only - a resolvable positive committed build time
  (`no_build_time`). Whether a build may start on a row that already carries
  construction state, and the click threshold, are client-side rules (design D7).

**Provenance - established versus derived.** Established from committed legacy
source and executed-legacy captures: the three commands' argument shapes and
effects (`command.py:412-428`, `525-535`, `537-548`; `engine.py:125-135`); that
they write only the row's `item[3]` timestamp and `item[6]` attribute bag; that
the click counter is **seeded by the purchase half** (`engine.py:25-28`); the
countdown's recorded shape `attr["cp"] = duration`; and that no server-side
completion rule exists. Derived and never observed from the Flash client: that a
real construction sends these commands, and that the duration is the item's
committed `build_time` rather than its `activation` field or a speedup-adjusted
figure.

`POST /v0/collect` with body `{"user_id", "item_index"}` is the eighth
state-mutating surface (the `building-collect` change) and **the first whose
resource vector is derived from committed content rather than refused**. Extra
keys — an amount, a resource, a tier, a time, a price, a resource delta — are
ignored, so the client cannot influence the payout.

The legacy mechanics were established by investigation first
(`docs/legacy-collect-income.md`): the `collect` branch writes **only**
`item[3] = time_now` (`command.py:136-147`), and the income is the client-sent
8-slot vector applied verbatim per resource as `max(current + delta, 0)`
(`engine.py:251-271`). What the service adds is the *derivation* of that vector
from the item's committed income content:

| Field | Use | Census |
| --- | --- | --- |
| `collect` | the amount per collection | `0` for 727 of 778 stored items |
| `collect_type` | which resource: `g`/`w`/`o`/`s`/`c` | 731 / 23 / 11 / 11 / 2 |
| `collect_xp` | the experience per collection | `0` for 419 items |
| `max_collects` | a cap where non-zero | `0` for 767 items |
| `COLLECT_MINUTES` | the ladder rungs | `[5, 60, 240, 480]` — **minutes** |
| `COLLECT_MULTIPLIER` | the rung multipliers | `[0.25, 1, 2, 3]` |

`amount = collect × multiplier[r]` and `experience = collect_xp × multiplier[r]`,
where `r` is the highest rung the elapsed time has reached, **clamped at the top**.
The ladder is in minutes and both row instants are Unix seconds, so the
comparison converts through one named constant (300 / 3 600 / 14 400 / 28 800
seconds) and every boundary is asserted from both sides. Slots 0 and 7 (the unread
slot and mana) are always zero, because no item records a mana collect type.

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790705901, "result": "success",
 "previous": [905, 53, 39, 0, 0, [], {}, 1],
 "row": [905, 53, 39, 1790705901, 0, [], {}, 1],
 "payout": [0, 3, 0, 60, 0, 0, 0, 0], "tier": 3,
 "reference_time": 1790705901,
 "resources": {"xp": 7, "gold": 2000, "wood": 2060, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- **The post-state is proved twice** (design D8): the row still exists and its
  recorded instant moved **forward**, **and** every stored resource changed by
  **exactly** the derived delta — so a clamp that reduced a payout, or any other
  divergence, is a fail-closed `internal_error` rather than a reported success.
  This is the first delivered surface whose proof checks a *value* the client
  would otherwise trust.
- **Five 409 refusals, all before the dispatcher runs**, so the corpus is never
  touched: `no_income` (a row whose item records no amount — 39 of the 40 placed
  corpus rows), `capped_collection` (a non-zero committed cap, whose semantics
  are unobserved), `unknown_collect_type` (a resource type outside the committed
  five), `too_early` (no committed rung reached), and `construction_in_progress`
  (the row carries a countdown or a build-click counter).
- **`construction_in_progress` is the evidence-based safety rule.** A collection
  executed on a row whose construction was just started overwrites that build's
  start instant while the countdown attribute survives, silently restarting an
  active build's timer, and the legacy server answers
  `{"result":"success"}` — so a collection must never be executed there, and the
  refusal is enforced in **both** layers rather than trusting the client.
- Validation is structural plus the content refusals above; the click threshold
  and the ladder are derived client-side rules (design D9), and authoritative
  validation remains Server v1 (M13) work.

**Provenance - established versus derived.** Established from committed legacy
source and executed-legacy captures: that the branch writes only the collection
instant, that the vector is applied verbatim per resource under the documented
clamp, the income content fields and ladder globals, the corpus facts, and the
shared-field corruption. **Derived and never observed from the Flash client — all
six:** the amount formula, the experience scaling, the sub-first-rung refusal, the
cap refusal, the shared-field refusal, and the cash/experience mapping. The claim
is that a payout grows in four committed rungs derived from the item's committed
income fields, never any specific amount the legacy client pays.

`POST /v0/expand` with body `{"user_id", "expansion_id"}` is the ninth
state-mutating surface (the `building-expand` change) and the first whose derived
vector is a **debit**. Extra keys — a price, a cost, an amount, a requirement, a
time, a resource delta — are ignored, so the client cannot influence what it pays.

The legacy branch is one line of state change (`command.py:211-216`):
`map["expansions"] += [int(expansion)]`. It changes nothing else, and the price is
**entirely client-sent**, applied verbatim per resource as `max(current + delta, 0)`.
The investigation's probe found the clamp **reachable for the first time in this
family**: a client-sent 2500 gold debit against a 2000 balance landed on **0**, not
`-500`. That is what a client-sent price buys, and it is why this endpoint derives
the debit from committed content instead.

| Source | Role |
| --- | --- |
| `expansion_prices` (98 entries, positional, no stable id) | `coins`, `cash`, `neighbors`, `inventory_qte` per expansion id |
| `assets/images/en/expansion_gold.jpg`, `expansion_cash.jpg` | the popup's two price components: the config's `coins` field is the client's `gold` |

The debit for a row priced `coins C, cash K` is `[0, 0, -C, 0, 0, 0, -K, 0]`; six
of the eight slots are always zero, and a zero-cost row derives the all-zero
vector, which is legal — indexes 0–3 are free.

```json
{"protocol": "compat-v0", "ok": true, "game_version": "alpha 0.02",
 "server_time": 1790737317, "result": "success",
 "expansions_before": [35, 36, 45, 46],
 "expansions_after": [35, 36, 45, 46, 0],
 "debit": [0, 0, 0, 0, 0, 0, 0, 0],
 "price": {"coins": 0, "cash": 0, "neighbors": 0, "inventory_qte": 0},
 "resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
               "steel": 2000, "cash": 5, "mana": 0}}
```

- **The two guards the legacy server omits** — `unknown_expansion_id` (404, an id
  outside the 98-entry table) and `already_expanded` (409) — exist because an
  executed probe showed the real server accepting `expand(999)`, a duplicate
  `expand(35)`, and `expand(-1)`, all answering `{"result":"success"}`. Without
  them a client could buy expansion 999 for a price derived from a row that does
  not exist.
- **`expansion_requirements_unmet` (409)** refuses any row recording a positive
  `neighbors` or `inventory_qte`, because nothing the delivered stack can read
  evaluates either requirement. **94 of 98 rows are refused this way, including
  all four ids the corpus owns** (`35, 36, 45, 46`, each `neighbors 15` /
  `inventory_qte 30`), so the only purchasable entries are the free indexes 0–3
  and the delivered end-to-end transaction is a **zero-cost** expansion. That is
  the correct outcome under the evidence and the wrong outcome for gameplay; it is
  recorded as a claim limit rather than patched by lowering the bar.
- **`insufficient_resources` (409)** refuses a balance below the derived debit
  instead of reproducing the clamp, because the debit is server-derived here: a
  silent partial charge would move a balance by less than the debit, which the
  value-level proof could not distinguish from a bug.
- **The post-state is proved twice**: the owned list grew by **exactly one** entry
  equal to the sent id **at the end**, with every existing entry unchanged, in
  order, and never reordered or deduplicated; **and** every stored resource changed
  by **exactly** the derived debit.
- A negative id is refused `invalid_expansion_id` (400) rather than treated as a
  range miss, because Python would otherwise resolve it to the schedule's last row.
- **No land, grid, buildable-cell, or placement-bound effect is claimed or
  implemented.** The committed SWF symbols (`PopupExpandMC`, `btnBuyExpandTileMC`)
  establish that an expansion is a purchasable **tile**, and the committed images
  establish the two price components — but nothing preserved maps a tile to a
  cell, because the SWF inspection is symbols-and-tags only and its own scope
  statement disclaims timeline semantics, script behavior, and rendering. This
  endpoint delivers the **unlock ledger**; closing the geometry gap requires new
  evidence, not a derivation.

**Provenance - established versus derived.** Established from committed legacy
source, executed-legacy probes, and committed asset evidence: that the branch
appends and changes nothing else; that the price is client-sent and applied
verbatim under the documented clamp; that the clamp is reachable; that the server
accepts out-of-range, duplicate, and negative ids and raises on a non-integer; and
that the price's gold component is named `gold` by the client's own committed
asset. **Derived and never observed from the Flash client:** the id-space indexing,
the requirements refusal, the affordability refusal, and the debit's sign and shape.

## No change from the resources projection

The `building-resources` change corrected the client's resource readout and left this
service **completely untouched**: no accessor, no response field, no route, no
error-table row, and no widening of the `resources()` accessor that all nine
state-mutating endpoints' value-level post-execution proofs compare. The seven keys
`resources()` returns are unchanged and remain the `apply_resources` contract.

That is worth stating explicitly because the change's design originally expected an
additive read-only accessor for the stored energy value. Apply established it was not
needed: the client's `TownState.RESOURCE_FIELDS` already maps `energy` to
`privateState.energy` and the delivered payload already carries it, so the row was
unsourced only in the client's display table. The client-side detail is documented in
`apps/client-godot/README.md` ("Resource readout") and in
`docs/legacy-resources.md`; the recorded gap — that **no committed source records how
`privateState.energy` changes over time**, `apply_resources` never writes it, and the
eight-slot mutation vector has no slot for it — holds on this side exactly as recorded.

### Structured errors

Always JSON, always `ok:false`, keys exactly
`{protocol, ok, error}` with `error: {code, message}` — never a partial payload:

| code | HTTP | when |
| --- | --- | --- |
| `invalid_payload` | 400 | body missing, not JSON, or not a JSON object |
| `missing_user_id` | 400 | `user_id` absent, null, or empty/whitespace |
| `invalid_user_id` | 400 | `user_id` present but not a string |
| `unknown_user_id` | 404 | well-formed id that names no save |
| `missing_item_id` | 400 | `/v0/place` or `/v0/purchase` body carries no `item_id` |
| `invalid_item_id` | 400 | `item_id` present but not an integer (`bool` excluded) |
| `unknown_item_id` | 404 | integer id absent from the loaded config |
| `invalid_coordinates` | 400 | `x`/`y` missing, not integers, or outside `0..99` |
| `invalid_orientation` | 400 | `orientation` present but not an integer |
| `costs_not_cash` | 400 | `/v0/purchase` item's config `costs` is not exactly a cash price (absent, empty, another resource, or mixed) |
| `missing_item_index` | 400 | `/v0/move` body carries no `item_index` |
| `invalid_item_index` | 400 | `item_index` present but not an integer (`bool` excluded) |
| `unknown_item_index` | 404 | integer index that names no placement in the save's `map["items"]` (legacy would silently no-op) |
| `invalid_reason` | 400 | server-side only: the derived sell reason is not a string (unreachable through the contract) |
| `no_upgrade_path` | 400 | `/v0/upgrade` placement's item has no resolvable next tier in the committed configuration (`upgrades_to` is absent, `-1`, `0`, or unresolvable) |
| `missing_action` | 400 | `/v0/construction` body carries no `action` |
| `invalid_action` | 400 | `action` present but not one of `start`, `click`, `finish` (the legacy command names are never accepted) |
| `no_build_time` | 400 | `/v0/construction` `start` on an item with no resolvable positive committed `build_time` (absent, non-integer, or `0`) |
| `invalid_duration` | 400 | envelope-level only: a derived start duration that is not a positive integer (unreachable through the contract) |
| `no_income` | 409 | `/v0/collect` the addressed item records no committed collection amount |
| `capped_collection` | 409 | `/v0/collect` the item records a non-zero committed collection cap, whose semantics are unobserved and therefore refused |
| `unknown_collect_type` | 409 | `/v0/collect` the item's committed resource type is outside the committed five |
| `too_early` | 409 | `/v0/collect` the row's elapsed time has not reached the first committed ladder rung |
| `construction_in_progress` | 409 | `/v0/collect` the addressed row carries a countdown or a build-click counter: collecting there would overwrite the build's start instant |
| `unknown_expansion_id` | 404 | `/v0/expand` the expansion id names no row in the committed 98-entry schedule; the legacy server performs no range check |
| `already_expanded` | 409 | `/v0/expand` the id is already in the player's owned list; the legacy server accepts duplicates |
| `expansion_requirements_unmet` | 409 | `/v0/expand` the row records a positive `neighbors` or `inventory_qte` requirement, which nothing in the delivered stack can evaluate |
| `insufficient_resources` | 409 | `/v0/expand` a balance is below the server-derived debit; refused rather than absorbed by the per-resource clamp |
| `bad_request` | 400 | other malformed requests Flask rejects |
| `not_found` | 404 | unknown path |
| `method_not_allowed` | 405 | known path, unsupported method |
| `internal_error` | 500 | unhandled server failure, including legacy execution raising after validation passed |

## Commands actually executed

All run from the repository root on Windows x64 with the pinned interpreter
(CPython 3.9.13); exit codes are the real observed ones (bootstrap-era
counts 2026-09-27; placement-, purchase-, move-, sell-, store-, upgrade-,
construction-, and collect-era counts 2026-09-29 and 2026-09-30;
expand-era counts 2026-09-30):

```bash
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

→ `Ran 947 tests ... OK`, exit `0` (90 before `building-purchase`, 157 before
`building-move`, 227 before `building-sell`, 306 before `building-store`, 390 before
`building-upgrade`, 491 before `building-construction`, 616 before `building-collect`, 768 before `building-expand`).
Covers envelope/error shapes, bootstrap and
session parity against the committed fixtures, pre/post save SHA-256 identity,
the no-persistence source guard, and the offline socket guard (the suite opens
no socket and starts no server) — plus, since the `building-placement` change,
the placement envelope derivation and sanitization (`test_placement_envelope`),
the `/v0/place` structural contract and corpus-only persistence
(`test_place_endpoint`), and the executed-legacy placement parity replay of
the committed `buy` fixture (`test_place_parity`) — and, since the
`building-purchase` change, the cash-only purchase envelope derivation
(`test_purchase_envelope`), the `/v0/purchase` structural contract, the
clamp-at-zero path, and corpus-only persistence (`test_purchase_endpoint`),
plus the executed-legacy purchase parity replay of the committed
`buy_stored_item_cash` fixture (`test_purchase_parity`).

```bash
python -B apps/compat-api/tests/smoke_loopback.py
```

→ 24 checks, `SMOKE RESULT: PASS`, exit `0`. Starts the real service on
`127.0.0.1:5056`, exercises both endpoints and the 400/404/404-error paths
over real HTTP, asserts the port-busy exit (`3`) plus that instance's corpus
cleanup, then stops the server (exit `0`) and asserts the disposable corpus was
removed and the working tree still has no `saves/`. Opt-in only — discovery
matches `test_*.py`, so this file never runs inside the unit suite, and it
needs port 5056 to be free.

```bash
python -B apps/compat-api/guard_baseline.py verify
```

→ `guard-baseline: OK - 6 group(s), combined 6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348`,
exit `0`. Verifies the pre-change SHA-256 guard set (legacy sources, `config/`,
both conversion packages, three registry manifests, committed M4 evidence,
on-disk saves) against `tests/fixtures/godot-compatibility-boot/guard-baseline.json`.
Guard digests are line-ending invariant (`guard-baseline-v2`): text files
(valid UTF-8 without NUL) are hashed after CRLF → LF normalization, all other
files as exact bytes — so a `core.autocrlf=true` checkout form and the
`report.json` producer's LF output never change a digest of unchanged content.

Fixture capture (task 1.1/1.2 evidence, one-shot) — see
`tests/fixtures/godot-compatibility-boot/README.md` for its invocation, exit
code `0`, and containment record:

```bash
python -B apps/compat-api/capture_legacy_fixtures.py
```

Placement fixture capture (the `building-placement` change's executed-legacy
oracle, one-shot) — see `tests/fixtures/godot-building-placement/README.md`
for its invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_placement_fixture.py
```

Purchase fixture capture (the `building-purchase` change's executed-legacy
oracle, one-shot) — see `tests/fixtures/godot-item-purchase/README.md`
for its invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_purchase_fixture.py
```

Move fixture capture (the `building-move` change's executed-legacy oracle,
one-shot) — see `tests/fixtures/godot-building-move/README.md` for its
invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_move_fixture.py
```

Sell fixture capture (the `building-sell` change's executed-legacy oracle,
one-shot) - see `tests/fixtures/godot-building-sell/README.md` for its
invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_sell_fixture.py
```

Store fixture capture (the `building-store` change's executed-legacy oracle,
one-shot) - see `tests/fixtures/godot-building-store/README.md` for its
invocation, exit code `0`, and containment record:

```bash
python -B apps/compat-api/capture_store_fixture.py
```

Upgrade fixture capture (the `building-upgrade` change's executed-legacy
oracle, one-shot; the request carries the two-command batch) - see
`tests/fixtures/godot-building-upgrade/README.md` for its invocation, exit
code `0`, its containment record, and the reverse-order negative oracle:

```bash
python -B apps/compat-api/capture_upgrade_fixture.py
```

Construction fixture capture (the `building-construction` change's
executed-legacy oracle, one-shot) - see
`tests/fixtures/godot-building-construction/README.md` for its invocation,
exit code `0`, its containment record, and why the completing command is
recorded but not captured:

```bash
python -B apps/compat-api/capture_construction_fixture.py
```

Collect fixture capture (the `building-collect` change's executed-legacy
oracle, one-shot) - see `tests/fixtures/godot-building-collect/README.md` for its
invocation, exit code `0`, its containment record, both recorded probes, and
the six derived decisions the request carries:

```bash
python -B apps/compat-api/capture_collect_fixture.py
```

Expand fixture capture (the `building-expand` change's executed-legacy oracle, one-shot) -
see `tests/fixtures/godot-building-expand/README.md` for its invocation, exit code `0`,
its containment record, the three recorded probes, and the four resolved decisions.
This capture has **no** time-dependent field, so a rerun reproduces its bytes exactly:

```bash
python -B apps/compat-api/capture_expand_fixture.py
```

## Layout

- `compat_legacy.py` — corpus build/layout checks and the in-process adapter
  over the legacy modules (`initialize()` mirrors `server.py`'s import and
  `load_saves` / `load_static_villages` / `load_quests` order).
- `compat_service.py` — Flask app, envelopes, and the error table; owns
  `PROTOCOL`, `HOST`, `DEFAULT_PORT`.
- `placement_envelope.py` — the derived-provisional `/v0/place` envelope
  (slot choice, price vector, documented placeholders) and sanitizers.
- `purchase_envelope.py` — the derived-provisional `/v0/purchase` envelope
  (cash-only price vector, one `buy_stored_item_cash` command, the documented
  placeholders), reusing the placement module's shared helpers unchanged.
- `run.py` — documented start command (corpus lifecycle, exit codes).
- `guard_baseline.py` — generate/verify the SHA-256 guard set.
- `field_stability.py` — derive the field-stability record from two captures.
- `capture_legacy_fixtures.py` — executed-legacy boot fixture capture.
- `capture_placement_fixture.py` — executed-legacy placement fixture capture.
- `capture_purchase_fixture.py` - executed-legacy purchase fixture capture.
- `move_envelope.py` - the derived-provisional `/v0/move` envelope (argument
  list, neutral resource vector, the `frame`/`string` placeholders legacy
  discards), reusing the placement module's shared helpers unchanged.
- `sell_envelope.py` - the derived-provisional `/v0/sell` envelope (argument
  list, neutral resource vector, derived reason), reusing the placement
  module's shared helpers unchanged.
- `capture_move_fixture.py` - executed-legacy move fixture capture.
- `capture_sell_fixture.py` - executed-legacy sell fixture capture.
- `store_envelope.py` - the derived-provisional `/v0/store` envelope (single
  argument, neutral resource vector).
- `capture_store_fixture.py` - executed-legacy store fixture capture.
- `upgrade_envelope.py` - the derived-provisional `/v0/upgrade` envelope: the
  two-command batch (`sell` with the committed `UPGR` reason, then `buy` of
  the target tier) with neutral resource vectors.
- `capture_upgrade_fixture.py` - executed-legacy upgrade fixture capture.
- `construction_envelope.py` - the derived-provisional `/v0/construction`
  envelopes: one command per documented action, with the start duration
  derived from committed content and neutral resource vectors.
- `capture_construction_fixture.py` - executed-legacy construction fixture
  capture.
- `tests/` — `test_compat_v0.py` (service + containment), `test_parity.py`
  (offline replay against the committed boot fixtures),
  `test_placement_envelope.py` (offline envelope derivation/sanitization),
  `test_place_endpoint.py` (structural contract + corpus-only persistence),
  `test_place_parity.py` (offline placement replay against the executed
  fixture), `test_purchase_envelope.py` (offline cash-only purchase
  derivation), `test_purchase_endpoint.py` (structural contract, clamp,
  corpus-only persistence), `test_purchase_parity.py` (offline purchase replay
  against the executed fixture), `test_move_envelope.py` (offline move envelope
  derivation: argument list, neutral vector, discarded placeholders, grid
  bounds), `test_move_endpoint.py` (structural contract, unknown-index
  fail-closed, neutral resources, corpus-only persistence),
  `test_move_parity.py` (offline move replay against the executed fixture),
  `test_sell_envelope.py` (offline sell envelope derivation: argument list,
  neutral vector, derived reason), `test_sell_endpoint.py` (structural
  contract, post-execution removal proof, unknown-index fail-closed, no client
  reason), `test_sell_parity.py` (offline sell replay against the executed
  fixture),
  `compat_test_harness.py`,
  `smoke_loopback.py` (opt-in loopback smoke).

## Claim limits

This service establishes **bootstrap parity for the fresh-save corpus**:
session list, game version, config, and player-info payloads equal to the
committed executed-legacy fixtures for stable fields and under the documented
normalizations for time-dependent fields. Since the `building-placement`
change it also establishes **placement parity for one recorded `buy`
transaction**: `POST /v0/place` replayed against the executed-legacy
placement fixture equals its response and after-state for every stable field
(the envelope `ts` and the placement entry's wall-clock `timestamp` are the
documented time-dependent fields). Since the `building-purchase` change it
additionally establishes **purchase parity for one recorded
`buy_stored_item_cash` transaction**: `POST /v0/purchase` replayed against the
executed-legacy purchase fixture equals its response and after-state for every
stable field (the envelope `ts` and the HTTP `Date` header are the documented
time-dependent fields). Since the `building-move` change it establishes **move
parity for one recorded `move` transaction**: `POST /v0/move` replayed against
the executed-legacy move fixture equals its response and after-state for every
stable field (the envelope `ts` and the HTTP `Date` header are the documented
time-dependent fields). Since the `building-sell` change it establishes **sell
parity for one recorded `sell` transaction**: `POST /v0/sell` replayed against
the executed-legacy sell fixture equals its response and after-state for every
stable field (the envelope `ts` and the HTTP `Date` header are the documented
time-dependent fields).

It does **not** establish authentication security, progressed-player coverage,
or parity for any other command. The price vector, envelope placeholders, and
slot choice are derived-provisional — never observed from the Flash client; the
same holds for the **choice of `buy_stored_item_cash` as the purchase command**
and for the **cash-only price derivation**, which also means the service claims
nothing about whether a resource-priced storage purchase exists in the legacy
client, and for the **move command's argument values**, the **arguments legacy
discards** (`frame`, `string`), and the **neutral move price vector** — the
service therefore claims neither that moving is free in the legacy client nor
that it costs anything. The **sell reason** is derived the same way (the empty
string, which legacy compares against `"KILL"` and otherwise uses as a log
label) and the **sell price vector** is neutral for the same reason the move
one is, so the change **claims no refund at all**: the committed configuration
records no building-sale refund rule and the legacy refund travels only in
client-sent deltas this contract refuses. Insufficient resources reproduce the
legacy `max(…, 0)` clamp, never a rejection (authoritative server-side validation
belongs to Server v1 / M13), and occupancy, grid-bounds, level-gate,
cash-affordability, no-op-move, sellability, storability, upgradability,
buildability, collectability, expandability, and addressability rules are
enforced client-side only, and the expansion land effect is deliberately absent: Persistence is confined to the disposable service
corpus: `POST /v0/place`, `POST /v0/purchase`, `POST /v0/move`,
`POST /v0/sell`, `POST /v0/store`, `POST /v0/upgrade`,
`POST /v0/construction`, `POST /v0/collect`, and `POST /v0/expand` persist through the legacy
dispatcher into the corpus `saves/`,
while the session and bootstrap endpoints remain strictly non-persisting, and
the working tree is never written.
