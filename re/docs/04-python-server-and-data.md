<!--
  Generated investigation artifact.
  Source of truth for the details inside is the file it was produced from:
  decompiled ActionScript 3 (FFDec 26.3.0) of assets/flash/Basesec_1.5.4.swf,
  the Python server sources, and live traffic captured from a real Adobe Flash
  Player session against the local server.
-->

# Python Server, Save Format & Game Data

> **Scope:** Source reading of the whole Python project plus live runtime verification (server started and probed over HTTP; save files inspected on disk).
>
> **Method:** Source reading of the whole Python project plus live runtime verification (server started and probed over HTTP; save files inspected on disk).
>
> **Subject:** route table, save schema, config pipeline, build/packaging, rewrite risk register
>
> Part of the Social Wars reverse-engineering report set. See [`../README.md`](../README.md)
> for the document map and [`../docs/00-EXECUTIVE-SUMMARY.md`](00-EXECUTIVE-SUMMARY.md) for the
> cross-cutting conclusions.

---

# 04 — Python Server & Data Model (Social Wars preservation project)

**Repository analysed:** `<upstream-repo>`
**Analysis date:** 2026-10-20
**Python sources:** `server.py`, `command.py`, `engine.py`, `sessions.py`, `get_game_config.py`, `get_player_info.py`, `constants.py`, `auctions.py`, `version.py`, `bundle.py`
**Runtime verified:** server started locally (`python server.py --port 5099`) and probed over HTTP; all findings marked *Verified* were observed at runtime, the rest are read from source.

Everything below was derived from the actual files. Where the brief's premise did not match the code, the discrepancy is called out explicitly. Items that could not be confirmed are marked **UNVERIFIED**.

---

## 0. Executive summary of the most important facts

| # | Fact |
|---|---|
| 1 | The Flask app declares **16 live route handlers** (plus 3 commented-out auction routes). Only **6** are under the dynamic Zynga-style prefix `/dynamic/menvswomen/srvsexwars/`, 1 serves static assets, and 9 are page/utility routes. |
| 2 | **There is no authentication whatsoever on the dynamic endpoints.** `USERID` is read straight out of the request body/query string, never cross-checked against the Flask session cookie. Any client can act as any player. *Verified.* |
| 3 | The `command.php` payload framing is `data = <64 chars> + ";" + <JSON>`. The 64-char prefix is **parsed but never validated** — it is discarded. Only the `;` separator position is asserted. |
| 4 | Resource deltas (`comm[3]`) are applied with **lower clamping only** (`max(x, 0)`). There is **no upper bound**. *Verified live:* a `ping` command with `[0,0,1000000000,0,0,0,0,0]` raised a player's gold from 2000 → 1 000 002 000. |
| 5 | `sessions.py` keeps three **module-level mutable dicts** (`__saves`, `__villages`, `__quests`). `load_saves()` is re-invoked on every `GET/POST /` (login page), which **replaces `__saves` wholesale**, discarding in-memory state. |
| 6 | `sessions.session(USERID)` returns **`None`** for unknown IDs; every caller then dereferences it → `TypeError` → HTTP 500. There is no 404/401 path. *Verified.* |
| 7 | Persistence is **one JSON file per player** (`saves/<USERID>.save.json`), written with `json.dump(..., indent=4)` on **every** `command.php` request. No DB, no locking, no transactions, no atomic rename. |
| 8 | `config/main.json` is **byte-identical** to `config/get_game_config.php_29august2012_nohash.json` — i.e. the canonical config *is* the 29-Aug-2012 live server capture with the hash prefix stripped and re-serialised as pretty JSON. |
| 9 | At runtime the config is **900 items** (778 base + 1 Atom Fusion building + 121 unit-patch units) and **105 globals** (104 + `SOUL_MIXER_POWERUPS_LEVELS`). |
| 10 | `villages/quest/` contains **23** quest village files (not 22 as stated in the brief): `100000001`–`100000014`, `100000017`–`100000022`, `100000025`, `100000026`, `100000049`. |
| 11 | `constants.py` `Quests.QUEST` has **duplicate keys** in the source literal; Python collapses them to **28 effective entries** (the source lists 31 lines). |
| 12 | The **auction house is fully disabled**: the `AuctionHouse` import and all three `/bets/*.php` routes are commented out in `server.py`. |
| 13 | `build/build.bat` uses `--add-data "..\..\assets;assets"` — with the current repo layout that resolves **outside the repository** (`C:\Users\Edison\Desktop\assets`, which does not exist). The correct prefix is `..\`. *Verified by path resolution.* |

---

## 1. Complete route table

### 1.1 Dynamic game endpoints (Zynga-compatible prefix)

`__DYNAMIC_ROOT = "/dynamic/menvswomen/srvsexwars"` (`server.py:61`)

There are **16 route decorators in `server.py`**: 9 page/utility, 1 static-asset, 6 dynamic (plus 3 commented-out auction routes).

| # | Method | URL path | Handler | Reads from request | Returns | Status / Format |
|---|---|---|---|---|---|---|
| D1 | POST | `/dynamic/menvswomen/srvsexwars/track_game_status.php` | `track_game_status_response` | `request.values['status']`, `['installId']`, `['user_id']` | `("", 200)` — empty body | **200**, `text/html; charset=utf-8`, 0 bytes |
| D2 | GET (any) | `/dynamic/menvswomen/srvsexwars/get_game_config.php` | `get_game_config_response` | `request.values['USERID']`, `['user_key']`, `['language']` (all required; read but unused) | the whole runtime game config dict | **200**, `application/json` — 1 092 491 bytes with 900 items / 105 globals |
| D3 | POST | `/dynamic/menvswomen/srvsexwars/get_player_info.php` | `get_player_info_response` | `USERID`, `user_key`, `language` (required, unused); optional `user`, `client_id`, `map` | own save, or a neighbour/quest save | **200**, `application/json` — `{result, processed_errors, timestamp, playerInfo, map, privateState, neighbors}`; **500** on unknown `USERID` |
| D4 | POST | `/dynamic/menvswomen/srvsexwars/sync_error_track.php` | `sync_error_track_response` | `USERID`, `user_key`, `language` | `("", 200)` | **200**, empty body |
| D5 | POST | `/dynamic/menvswomen/srvsexwars/command.php` | `command_response` | `USERID`, `user_key`, `language`, `data` | `({"result": "success"}, 200)` | **200**, `application/json`, body `{"result":"success"}` |
| D6 | POST | `/dynamic/menvswomen/srvsexwars/alliance/` | `alliance` | `USERID`, `user_key`, `language`, `method` | `({}, 200)` | **200**, `application/json`, body `{}` |
| D7 | POST | `/dynamic/menvswomen/srvsexwars/bets/get_bets_list.php` | *commented out* | — | — | **Disabled** (`server.py:197-226`) |
| D8 | POST | `/dynamic/menvswomen/srvsexwars/bets/get_bet_detail.php` | *commented out* | — | — | **Disabled** (`server.py:228-257`) |
| D9 | POST | `/dynamic/menvswomen/srvsexwars/bets/set_bet.php` | *commented out* | — | — | **Disabled** (`server.py:259-288`) |

> Note on D2: the route is declared without `methods=`, so Flask accepts `GET`, `POST`, `HEAD`, `OPTIONS`. `request.values` merges query string + form body, so both work. *Verified:* GET with query params returned 200.
> Note on D1/D4: the handler returns a plain `str` tuple, so Flask wraps it as `text/html`. Verified content-type `text/html; charset=utf-8` with a 0-byte body.

### 1.2 Static game assets

`__STATIC_ROOT = "/static/socialwars"` (`server.py:60`)

| # | Method | URL path | Handler | Reads | Returns | Status / Format |
|---|---|---|---|---|---|---|
| S1 | GET | `/static/socialwars/<path:path>` | `static_assets_loader` | path segment | file from `ASSETS_DIR` | **200** file bytes (e.g. `flash/SWLoader.swf` → 127 786 bytes). A CDN-from-GitHub branch exists but is dead code (`if False:` at `server.py:132`) |

`ASSETS_DIR` = `sys._MEIPASS/assets` when frozen, else `./assets`. The shipped `assets/` tree is **3 199 files / 716.8 MB**, with subfolders `characters_2, externalized, flash, fonts, fx, images, magic, sounds, sprites, swf, thumbs`. `assets/flash/` holds every `Basesec_*.swf` client build.

### 1.3 Page / utility routes

| # | Method | URL path | Handler | Reads | Returns | Status / Format |
|---|---|---|---|---|---|---|
| P1 | GET, POST | `/` | `login` | GET: nothing. POST: `request.form['USERID']`, `request.form['GAMEVERSION']` | GET → `login.html` (empire picker). POST → 302 → `/play.html` | **200** `text/html`; POST **302** |
| P2 | GET | `/play.html` | `play` | Flask `session['USERID']`, `session['GAMEVERSION']` | `play.html` (embeds the SWF) | **200** `text/html`; **302 → `/`** if session missing or USERID not in saves |
| P3 | GET | `/new.html` | `new` | — | 302 → `play.html` | **302**; creates a new village + save file |
| P4 | GET | `/health` | `health` | — | `{"status":"ok","version":"alpha 0.02"}` | **200** `application/json` |
| P5 | GET | `/crossdomain.xml` | `crossdomain` | — | `stub/crossdomain.xml` | **200** `text/xml; charset=utf-8` |
| P6 | GET | `/img/<path:path>` | `images` | path | `templates/img/<path>` | **200** file |
| P7 | GET | `/avatars/<path:path>` | `avatars` | path | `templates/avatars/<path>` | **200** file |
| P8 | GET | `/css/<path:path>` | `css` | path | `templates/css/<path>` | **200** file |
| P9 | GET | `/null` | `flash_sync_error_response` | `request.values['sp_ref_cat']` | 302 → `/play.html` | **302** |

`/null` reads `sp_ref_cat` and maps it to a human-readable reason string (`flash_sync_error` → "reload On Sync Error", `flash_reload_quest` → "reload On End Quest", `flash_reload_attack` → "reload On End Attack"). If `sp_ref_cat` is none of these, `reason` is **unbound** → `UnboundLocalError` → 500. *Verified by code reading; the crash path is not exercised by the client.*

### 1.4 Flask session usage (pages only)

The Flask cookie session is used **exclusively** by the page routes:

* `login()` — `session.pop('USERID')`, `session.pop('GAMEVERSION')`, then on POST `session['USERID'] = request.form['USERID']`, `session['GAMEVERSION'] = request.form['GAMEVERSION']`.
* `play()` — reads `session['USERID']` and `session['GAMEVERSION']`; redirects to `/` if either is missing or if `session['USERID'] not in all_saves_userid()`.
* `new()` — sets `session['USERID']` to the newly created UUID and `session['GAMEVERSION'] = "Basesec_1.5.4.swf"`.

`app.secret_key = os.urandom(24)` is set **only inside the `if __name__ == '__main__':` block** (`server.py:351`). If the module is imported by a WSGI server (gunicorn/uwsgi), the secret key is **never set** → Flask raises `RuntimeError: The secret key must be set` on the first session write. This is a real deployment blocker. *Verified by code reading.*

---

## 2. Request / response contract per dynamic endpoint

### 2.1 Common parameters

Every dynamic handler reads the same three names from `request.values` (query string **or** form body):

| Parameter | Type | Read by | Used? |
|---|---|---|---|
| `USERID` | string | D1–D6 | **Only** D3 and D5 actually use it. D1/D2/D4/D6 read it and discard it. |
| `user_key` | string | D2, D3, D4, D5, D6 | **Never used** — no HMAC, no session lookup, no signature check. |
| `language` | string | D2, D3, D4, D5, D6 | **Never used.** The config is English-only (`images` values are all `"en"`). |
| `accessToken` | string (inside the JSON body) | `command()` | **Never validated** — read from `data["accessToken"]` and dropped. The template hard-codes a fake Facebook token in `play.html` (`flashvars ... accessToken=AAABbZAm0wdMUBALsOrR0Ho68CLjaOT8SV3vftKg9mbo1zZColaW5FljRVaLxPGxXXnm1M98mTZCAttcQ4GHwvSyXfsyxYmvKMH8Hmn5iliSPnjvIsZA6`) and `user_key=123456789`. |

Optional on D3: `user` (target player/neighbour/quest id), `client_id` (int), `map` (int, index into `maps[]`).

### 2.2 `get_game_config.php`

```
Request : GET|POST ?USERID=<id>&user_key=<k>&language=<lang>
Response: 200 application/json
Body    : the full game config object — 20 top-level sections
```

The response is the *same* object for every caller; `make_dynamic()` is re-run on each call (it is idempotent once the darts dates are already in the future).

Observed response body: 1 092 491 bytes, 900 items, 105 globals, 27 `darts_items`.

### 2.3 `get_player_info.php`

```
Request : POST  USERID=<id>&user_key=<k>&language=<lang>[&user=<target>][&map=<n>][&client_id=<n>]
Response: 200 application/json
```

Three dispatch branches (`server.py:179-193`):

1. **`user` absent** → `get_player_info(USERID)`:
   ```json
   { "result": "ok", "processed_errors": 0, "timestamp": <unix>,
     "playerInfo": {…}, "map": {…}, "privateState": {…}, "neighbors": [ … ] }
   ```
   Side effects: sets `playerInfo.last_logged_in = now`, and calls `reset_stuff(save)` which (a) resets `map.numTradesDone = 0` if `now // 86400 != timestampLastTrade // 86400`, and (b) sets `privateState.timeStampDartsReset = 0` when a new darts week has begun.
   *Verified:* `neighbors` is an array of `playerInfo`-shaped objects **plus** `xp`, `level`, `gold`, `wood`, `oil`, `steel` copied from `maps[0]`. In the probe it contained 8 entries.
   *Failure:* `USERID` not in `__saves` → `TypeError: 'NoneType' object is not subscriptable` → **HTTP 500**. *Verified* (asking for `USERID=Neutral`, a *static neighbour*, returned 500 because `sessions.session()` only searches `__saves`).

2. **`user` in `("100000030", "100000031")`** → General Mike: `get_neighbor_info("100000030", map)` — **both** ids always resolve to the `100000030` village. *Verified* (`user=100000030` → `playerInfo.pid == "100000030"`).

3. **`user` starts with `"100000"`** → quest map: `get_neighbor_info(user, map)`. *Verified* (`user=100000001` → `playerInfo.pid == "100000001"`, `map.level == 35`).

4. **otherwise** → static neighbour: `get_neighbor_info(user, map)`.

`get_neighbor_info` returns:
```json
{ "result": "ok", "processed_errors": 0, "timestamp": <unix>,
  "playerInfo": {…}, "map": {…}, "privateState": {…} }
```
(no `neighbors` key). If the target is not found, it returns the **empty string `""`** → Flask responds 200 with `text/html` and an empty body (not JSON). *Not exercised in the probe.*

### 2.4 `command.php` — the `data` framing

```
POST /dynamic/menvswomen/srvsexwars/command.php
USERID=<id>&user_key=<k>&language=<lang>&data=<DATA>
```

`DATA` layout (`server.py:321-325`):

```
+--------------------+-----------+------------------+
| 64 chars (hash)    |    ';'    |  JSON payload     |
+--------------------+-----------+------------------+
0                   64          65
```

```python
data_str = request.values['data']
data_hash = data_str[:64]          # <-- captured, never used
assert data_str[64] == ';'         # <-- the ONLY validation
data_payload = data_str[65:]
data = json.loads(data_payload)
command(USERID, data)
```

Key properties:

* The 64-char prefix is the same convention used by the original Zynga server for `get_game_config.php` (see the captures in `config/get_game_config.php_*.txt`, e.g. `ff31eef4221ea09cc84e9703ddcf54af7a26c133a33e1c2f765a34614f04d509;`). It is **stripped and discarded** — the Python server never computes or checks it. The Flash client computes it; the server ignores it.
* `assert` is used → the framing check is **compiled out under `python -O`**, and under normal operation it raises `AssertionError` → **HTTP 500**. *Verified:* sending `64×'x' + '|' + json` produced a 500 with `AssertionError` at `server.py:323`.
* A `data` shorter than 65 chars → `IndexError: string index out of range` → **HTTP 500**. *Verified.*
* Missing `data` entirely → Flask raises `BadRequestKeyError` → **HTTP 400**. *Verified.*

### 2.5 `alliance/`

`POST`, requires `USERID`, `user_key`, `language`, `method`. Returns `{}` with 200. Comment in source: *"Used by Player's World and Alliance buttons / I added this so the error message stops appearing"*.

### 2.6 `track_game_status.php` / `sync_error_track.php`

Both POST, read `USERID`/`user_key`/`language`, return an empty 200 body. `track_game_status.php` additionally reads `status`, `installId`, `user_id` and logs `[STATUS] USERID {user_id}: {status}`.

---

## 3. `command.php` payload structure and the anti-cheat surface

### 3.1 Top-level payload

`command.py:9-32`:

```python
def command(USERID, data):
    first_number  = data["first_number"]     # int   — read, NEVER used
    publishActions= data["publishActions"]   # bool  — read, NEVER used
    timestamp     = data["ts"]               # int   — read, NEVER used
    tries         = data["tries"]            # int   — read, NEVER used
    accessToken   = data["accessToken"]      # str   — read, NEVER used
    commands      = data["commands"]         # list  — the only field that matters
```

`data` is accessed with **direct subscripting** (`data["first_number"]`), so a missing key raises `KeyError` → HTTP 500. There is no schema validation.

`commands` is a list of 4-element arrays:

| Index | Name | Meaning | Consumed by |
|---|---|---|---|
| `comm[0]` | `map_id` | index into `save["maps"]` (always `0` in practice) | `save["maps"][map_id]` |
| `comm[1]` | `cmd` | command name string | `do_command` dispatch |
| `comm[2]` | `args` | list of command arguments (values are frequently **JSON-encoded strings** — e.g. `json.loads(args[1])` for goal progress) | per-command |
| `comm[3]` | `resources_changed` | 8-element resource delta array | `apply_resources` |

### 3.2 `comm[3]` — resource deltas

`engine.py:251-268`:

```python
def apply_resources(save, map, resource):
    unknown = resource[0]
    xp      = resource[1]
    gold    = resource[2]
    wood    = resource[3]
    oil     = resource[4]
    steel   = resource[5]
    cash    = resource[6]
    mana    = resource[7]

    map["xp"]    = max(map["xp"] + xp, 0)
    map["gold"]  = max(map["gold"] + gold, 0)
    map["wood"]  = max(map["wood"] + wood, 0)
    map["oil"]   = max(map["oil"] + oil, 0)
    map["steel"] = max(map["steel"] + steel, 0)
    save["playerInfo"]["cash"]      = max(save["playerInfo"]["cash"] + cash, 0)
    save["privateState"]["mana"]    = max(save["privateState"]["mana"] + mana, 0)
```

| Slot | Resource | Target field |
|---|---|---|
| 0 | `unknown` | **ignored** |
| 1 | xp | `maps[n].xp` |
| 2 | gold | `maps[n].gold` |
| 3 | wood | `maps[n].wood` |
| 4 | oil | `maps[n].oil` |
| 5 | steel | `maps[n].steel` |
| 6 | cash | `playerInfo.cash` |
| 7 | mana | `privateState.mana` |

**This is the entire "anti-cheat" surface.** It is a lower bound only.

* The source comment says: *"So these will be negative if the user used resources and positive if the user gained resources, we can detect cheats by checking if any are less than 0 after applying"* — **this detection is never implemented.** There is no `if resource[i] > 0: reject` check anywhere.
* **No upper clamp.** *Verified live:* `commands=[[0,"ping",[],[0,0,1000000000,0,0,0,0,0]]]` moved gold from 2000 to 1 000 002 000.
* `apply_resources` is called **unconditionally at the top of `do_command()`**, i.e. **once per command** in the batch. A batch of N commands therefore applies the per-command delta N times. (Whether the client sends the same delta in every command is a client-side concern — the server has no idea.)
* `max(..., 0)` clamps are applied to: `xp`, `gold`, `wood`, `oil`, `steel`, `cash`, `mana` — **7 clamps total** in the whole codebase.
* Other `max(0, ...)` uses are in `fast_forward` (timer rewinds), not resource clamps.

### 3.3 Other client-trusted values (no validation)

These are written straight from client-supplied `args` into the save with **no** range/format check:

| Command | Field written | Client-supplied value |
|---|---|---|
| `level_up` | `map["level"]` | `args[0]` — arbitrary int |
| `buy` | `map["items"][index]` | `item_id`, `x`, `y`, `orientation`, `playerID` — arbitrary; `x`/`y` are **not** range-checked against map bounds |
| `move` | `item[1]`, `item[2]` | arbitrary `x`, `y` |
| `orient` | `item[4]` | `int(orientation)` |
| `expand` | `map["expansions"]` | `int(expansion)` — arbitrary, appended |
| `add_xp_unit` | `item[6]["xp"]` | arbitrary int |
| `flash_debug` | `playerInfo.cash`, `map.xp/gold/oil/steel/wood` | arbitrary ints — a **full resource overwrite** |
| `buy_premium_account` | `privateState.timeStampEndPremium` | `days` comes from the **config** (`PREMIUM_ACCOUNTS[package_index].time`), but `package_index` is client-chosen and is only clamped to the last package index |
| `buy_magic` / `use_magic` | `privateState.magics[id]` | `min(50, count+1)` — capped at 50 |
| `darts_shoot_balloon` | `privateState.dartsBalloonsShot` | `index` appended verbatim (no bounds check) |
| `buy_offer_pack` | `map["store"]` | `items` list from the client is added to the store — **any item id, any quantity, for free** |
| `weekly_reward` | `map["items"]`, `privateState.weeklyRewardIndex` | item id/position from the client — free weekly reward |
| `win_daily_bonus` | `map["store"]` | item id from the client — free daily bonus |
| `buy_stored_item_cash` | `map["store"]` | free unit-collection purchase |
| `complete_collection` | `map["store"]`, `privateState.collections` | collection id → the *config* prize is granted, but the id is client-chosen |
| `end_attack` / `end_quest` | unit losses, `map["questTimes"]` | `unit[2] - unit[3]` losses are applied to the attacker's own map; **the victim's save is never touched** (`# TODO: Affect victim player save`) |
| `fast_forward` | many timers | `seconds` is client-supplied and unbounded — rewinds all timers, including `map["timestamp"]` |

---

## 4. All commands handled by `do_command` (63 total)

Grouped by domain. "Mutated state" lists the save paths written by that command.

### 4.1 Building / placement / map editing

| Command | Description | Mutates |
|---|---|---|
| `buy` | Places a new building/unit on the map at `(x,y)`; if `playerID == 1` also records it as bought | `map["items"][idx]` (8-elem array), `privateState.boughtUnits` |
| `move` | Moves the item at `item_index` to `(x,y)` | `map["items"][idx][1]`, `[2]` |
| `orient` | Rotates the item | `map["items"][idx][4]` |
| `collect` | Resets the item's production timer (harvest now) | `map["items"][idx][3] = now` |
| `sell` | Removes the item; if `reason == "KILL"` and the unit is `resurrectable` it is moved to the hospital | `map["items"]` (delete), `privateState.deadHeroes` |
| `kill` | Removes the item (no corpse) | `map["items"]` (delete) |
| `kill_iid` | Kills a unit by `item_id` (no map bookkeeping) | *(nothing — log only)* |
| `batch_remove` | Deletes a list of item indices | `map["items"]` |
| `expand` | Unlocks a land expansion | `map["expansions"]` (append) |
| `activate` | Activates/deactivates a building: sets `item[3] = now` and `item[6]["cp"] = args[1]`, or wipes `item[6] = {}` | `map["items"][idx][3]`, `[6]` |

### 4.2 Units / training queues

| Command | Description | Mutates |
|---|---|---|
| `push_unit` | Moves a unit from the map into a building's training queue | `building[5].append(unit)`, `building[3] = now` |
| `pop_unit` | Pulls a trained unit out of a building back onto the map | `map["items"][idx]`, `unit[0],[1],[2],[7]` |
| `push_queue_unit` | Enqueues a unit in a generic queue (e.g. Atom Fusion) | `item[6]["nu"] += 1`, `item[6]["ts"] = now` |
| `push_queue_unit2` | Enqueues a **specific** unit id into the Atom Fusion queue | `item[6]["nu"]`, `item[6]["ts"]`, `item[6]["ui"] = unit_id` |
| `pop_queue_unit` | Dequeues a unit from the queue | `item[6]` — deletes `nu`, `ts`, `ui` |
| `resurrect_hero` | Revives a hero from the hospital and places it | `privateState.deadHeroes[item_id] -= 1`, `map["items"][idx]` |
| `add_xp_unit` | Adds XP to a unit (unit level-up) | `item[6]["xp"] += xp_gain` |
| `unit_collections_completed` | Marks a unit collection as complete | `privateState.unitCollectionsCompleted` |
| `buy_stored_item_cash` | Buys a unit-collection unit for cash (server does **not** charge) | `privateState.boughtUnits`, `map["store"]` |

### 4.3 Storage / inventory

| Command | Description | Mutates |
|---|---|---|
| `store_item` | Moves an item from the map into storage | `map["items"]` (delete), `map["store"][item_id] += 1` |
| `place_stored_item` | Takes an item out of storage and places it on the map | `map["store"]` (−1), `map["items"][idx]`, `privateState.boughtUnits` |
| `sell_stored_item` | Removes an item from storage | `map["store"]` (−1 / delete) |
| `store_add_items` | Adds a list of item ids to storage | `map["store"]`, `privateState.boughtUnits` |
| `add_inventory_item` | Adds inventory consumables | `privateState.inventoryItems[item_id] += qty` |
| `remove_inventory_item` | Removes inventory consumables | `privateState.inventoryItems` |
| `complete_collection` | Claims a collection prize; prize from `config.collections[collection-1].prize` | `map["store"]`, `privateState.collections` |

### 4.4 Economy / resources

| Command | Description | Mutates |
|---|---|---|
| `flash_debug` | "Keep up with resources" — overwrites cash/xp/gold/oil/steel/wood from the client | `playerInfo.cash`, `map.xp/gold/oil/steel/wood` |
| `trade_resource` | Market trade; increments the daily trade counter, capped at 20 | `map["numTradesDone"] = min(20, n)`, `map["timestampLastTrade"]` |
| `set_resource_allies` | Sets the Allies-Market resource and refreshes the building timer | `map["resourceAlliesMarket"]`, `item[3]`, `item[6]` (`si` cleared) |
| `buy_offer_pack` | "Bought Offer Pack" — adds the client-supplied item list to storage | `map["store"]` |
| `win_daily_bonus` | Daily bonus: advances the bonus id (1..5) and grants an item or resources | `privateState.timestampLastBonus`, `privateState.bonusNextId`, `map["store"]`, `privateState.boughtUnits` |
| `buy_powerups` | Atom Fusion power-up — **TODO, does nothing** | *(nothing)* |
| `soulmixer_speedup` | Buys an Atom Fusion speed-up; sets `atom_fusion[6]["ts"] = 0` to cancel the timer | `item[6]["ts"]` |
| `buy_mana_new` | "Bought mana" — **no-op by design** | *(nothing)* |

### 4.5 Research (Area 51 / Robotic Center)

The two research tracks are indexed by `_type`: **0 = Area 51**, **1 = Robotic Center**.

| Command | Description | Mutates |
|---|---|---|
| `next_research_step` | Advances one research step | `privateState.researchStepNumber[_type] += 1`, `privateState.timeStampDoResearch[_type] = now` |
| `research_buy_step_cash` | Buys a research step with cash | `privateState.timeStampDoResearch[_type] = 0` |
| `next_research_item` | Completes the current research item | `privateState.researchItemNumber[_type] += 1`, `researchStepNumber[_type] = 0`, `timeStampDoResearch[_type] = 0` |
| `reset_research_item` | Resets the current research item | `researchItemNumber[_type] = 0`, `researchStepNumber[_type] = 0`, `timeStampDoResearch[_type] = 0` |

### 4.6 Quests / chapters / missions

| Command | Description | Mutates |
|---|---|---|
| `complete_tutorial` | Marks the tutorial done when `step >= 25` or `step == 15` | `playerInfo.completed_tutorial = 1` |
| `set_goals` | Sets a goal's progress `[visited, currentStep]` | `privateState.goals[goal_id]` (grown with `None` padding) |
| `complete_goal` | Log only — **no state change** | *(nothing)* |
| `set_quest_var` | Sets a quest variable (`id`, `spawned`, `ended`, `visited`, `activators`, `boss`, `treasure`, `killed`). `idSimpleChapter` is **deliberately ignored** so players can progress past chapter 99 | `map["idCurrentMission"]` (only for key `id`), `map["currentQuestVars"][key]` |
| `collect_mission` | Advances to the next chapter; wraps back to 1 after 99 | `map["idCurrentMission"] = str(next)`, `map["timestampLastChapter"]`, `map["currentQuestVars"] = {}` |
| `end_quest` | Ends a quest; applies the **attacker's own** unit losses, records the completion time | `privateState.deadHeroes` / `map["items"]` (losses), `map["questTimes"][quest_id] = now` |
| `admin_set_quest_rank` | Sets a quest difficulty/rank | `privateState.questsRank[str(quest_index)] = difficulty` |

### 4.7 Battle / attacks

| Command | Description | Mutates |
|---|---|---|
| `end_attack` | Ends an attack; parses `victim`, `attacker`, `resources`, `honor`, `duration`, `townhall_gold`, `win`, `different_island`, `victim_units`, `attacker_units`, `resources_victim`, `voluntary_end`; applies **attacker** unit losses only | `privateState.deadHeroes` / `map["items"]` (losses). **The victim's save is never modified** (`# TODO: Affect victim player save`, `# TODO: Attack logs`) |

### 4.8 Darts minigame

| Command | Description | Mutates |
|---|---|---|
| `darts_reset` | Starts a new darts week with a new random seed | `privateState.dartsRandomSeed`, `dartsBalloonsShot = []`, `dartsHasFree = True`, `dartsGotExtra = False`, `timeStampDartsReset`, `timeStampDartsNewFree` |
| `darts_new_free` | Grants a free shot | `privateState.dartsHasFree = True`, `timeStampDartsNewFree` |
| `darts_shoot_balloon` | Records a shot; `won_extra` sets `dartsGotExtra` | `privateState.dartsBalloonsShot` (append), `dartsHasFree = False`, `timeStampDartsNewFree`, `dartsGotExtra` |

### 4.9 Premium / monetisation

| Command | Description | Mutates |
|---|---|---|
| `buy_premium_account` | Extends premium; `days` from `config.globals.PREMIUM_ACCOUNTS[package_index].time` (360/180/30/7/3/1 days). If premium is still running the days are **added**; otherwise the clock restarts from now | `privateState.timeStampEndPremium` |
| `first_time_marketplace` | Marks the Auction House as seen | `privateState.marketPlaceFirstTime = True` |
| `weekly_reward` | Monday bonus: may place a free unit, then advances the reward index modulo `get_weekly_reward_length()` (= 3) and stamps the Monday timer | `map["items"]`, `privateState.boughtUnits`, `privateState.timeStampMondayBonus`, `privateState.weeklyRewardIndex` |

### 4.10 Magic spells

| Command | Description | Mutates |
|---|---|---|
| `buy_magic` | Buys a spell (mana is *not* deducted) | `privateState.magics[str(magic_id)] = min(50, count+1)` (or `0` if new) |
| `use_magic` | Uses a spell (same counter as buy) | `privateState.magics[str(magic_id)] = min(50, count+1)` |

### 4.11 Social / assists / friends

| Command | Description | Mutates |
|---|---|---|
| `add_click` | Increments the "clicks to build" counter | `item[6]["nc"] += 1` |
| `activate_item_click` | Marks the click-to-build as done | deletes `item[6]["nc"]` |
| `buy_si_help` | Buys a socially-in-construction helper | `item[6]["si"]` — `= [0]` if absent, else `.append(0)` |
| `finish_si` | Completes a socially-in-construction building | deletes `item[6]["si"]` |
| `rt_open_graph_unit` | Records a unit published to an Open Graph story | `privateState.publishedOpenGraphUnit` (append, de-duplicated) |

### 4.12 Meta / debug

| Command | Description | Mutates |
|---|---|---|
| `ping` | "Pong" | *(nothing)* |
| `set_variables` | "Set player resources" — **no-op** | *(nothing)* |
| `fast_forward` | Rewinds every timer by `seconds` | `map.timestamp`, `map.timestampLastChapter`, `map.timestampLastTreasure`, `map.timestampLastTrade`, `privateState.timestampLastBonus`, `privateState.timestampLastAllianceBonus`, `privateState.timeStampDartsNewFree`, `privateState.tsAttacksReset`, `privateState.tsSpyingsReset`, all `privateState.timeStampDoResearch[i]`, all `map["items"][i][3]`, all `map["items"][i][6]["ts"]`, all `map["questTimes"][*]`. **Deliberately skipped:** `timeStampMondayBonus` and `timeStampDartsReset` ("don't process weekly things") |

### 4.13 Unhandled

Any command name not in the list above falls through to:
```python
else:
    print(f"Unhandled command '{cmd}' -> args", args)
    return
```
i.e. the command is **silently ignored** (a 200 `{"result":"success"}` is still returned).

---

## 5. Save file format — `saves/<USERID>.save.json`

Written by `sessions.save_session()`:
```python
file = f"{USERID}.save.json"
village = session(USERID)
with open(os.path.join(SAVES_DIR, file), 'w') as f:
    json.dump(village, f, indent=4)
```
`SAVES_DIR` = `./saves` (relative to the **current working directory**, not the EXE dir). JSON is dumped with **4-space indent**, keys in insertion order, `ensure_ascii` default (True).

Document top level:

| Key | Type | Presence | Meaning |
|---|---|---|---|
| `playerInfo` | object | always | Player identity & cash |
| `maps` | array of objects | always | One or more maps (all shipped saves have exactly 1) |
| `privateState` | object | always | Per-player private data (not sent to neighbours) |
| `version` | string or null | optional | Save-format version (`"0.01a"` / `"0.02a"`). `initial.json` has **no** `version` key; `General_Mike_30/31.json` have `"version": null`; the other static villages have `"0.02a"`; all 23 quest villages have `"0.01a"`. |

### 5.1 `playerInfo` — complete field-by-field schema

| Field | Type | Example | Meaning |
|---|---|---|---|
| `pid` | string (UUID4) or null | `"9bfff6b2-…"` / `null` in `initial.json` | Player id. **This is the save-file primary key**: `load_saves()` keys `__saves` by `save["playerInfo"]["pid"]`. |
| `name` | string | `"Warrior"`, `"Kiriakos 96d"`, `"[Neutral]"` | Empire display name |
| `pic` | string (URL) | `"https://avatars.githubusercontent.com/u/135655497?s=68"` | Avatar URL (also used as `pic_square` in `neighbors` / `friendsInfo`) |
| `cash` | int | `5` (initial), `500` (AcidCaos) | Premium currency |
| `completed_tutorial` | int (0/1) | `0` / `1` | Tutorial finished flag |
| `default_map` | int | `0` | Index into `maps[]` used by `save_info()` |
| `map_names` | array of string | `["Empire"]`, `["Atlas Corp"]` | Per-map display names |
| `map_sizes` | array of int | `[0]` | Per-map size class |
| `world_id` | int or null | `null` in all shipped saves | Facebook world id (dead since FB deprecation) |
| `sp_ref_uid` | int | `1000` | Sponsored-referral uid |
| `sp_ref_cat_install` | string | `"ts"` | Sponsored-referral category |
| `last_logged_in` | int (unix ts) | `1705799336` | Updated on every `get_player_info.php` call for the *own* player only |

### 5.2 `maps[]` — complete field-by-field schema

All shipped saves have exactly **one** map. `playerInfo.default_map` and `map_names[]`/`map_sizes[]` imply multiple maps are supported by the schema, but nothing in the code ever creates a second map.

| Field | Type | Example | Meaning |
|---|---|---|---|
| `id` | int | `0` | Map index (matches `playerInfo.map_names` position) |
| `world_id` | int | `0` | Facebook world id |
| `expansions` | array of int | `[35, 36, 45, 46]` | Expansion tile ids unlocked on this map. `initial.json` ships with 4 pre-unlocked. `expand` appends. |
| `timestamp` | int (unix ts) | `0` | Map save timestamp (also rewound by `fast_forward`) |
| `xp` | int | `4` (initial) / `136878` (Neutral) | Total experience |
| `level` | int | `1` (initial) / `44` (Neutral) | Player level on this map |
| `gold` | int | `2000` | Gold |
| `wood` | int | `2000` | Wood |
| `oil` | int | `2000` | Oil |
| `steel` | int | `2000` | Steel |
| `race` | string | `"h"` (all shipped saves) | `"h"` = human, `"n"` = neutral. Item-level `race` uses the same convention (`"h"`, `"-"`, `"n"`). |
| `skin` | int | `0` | Empire skin id |
| `idCurrentTreasure` | int | `0`, `89` (Scarlet) | Current treasure hunt id |
| `timestampLastTreasure` | int | `0` | Timestamp of last treasure |
| `resourcesTraded` | object | `{}` | Per-resource trade bookkeeping (always empty in shipped saves) |
| `resourceAlliesMarket` | string | `""`, `"n"`, `"s"` | Which resource the Allies Market currently trades (`""` = none; `g/w/o/s/n` seen) |
| `receivedAssists` | object | `{}` | Assists received from friends (always empty in shipped saves) |
| `timestampLastTrade` | int | `0` | Last market trade time (used by `reset_stuff` for the daily reset) |
| `numTradesDone` | int | `0` … `20` | Trades done today (capped at 20 by `trade_resource`) |
| `store` | object `<item_id:string> -> int` | `{"1033": 1, "87": 1}` | **Unit storage**: item id → quantity. Keys are strings, values ints. 10 of the shipped saves have a non-empty store. |
| `increasedPopulation` | int | `0` | Population bought with premium |
| `expirableUnitsTime` | object | `{}` | Expiring unit timers (always empty in shipped saves) |
| `timestampLastChapter` | int | `0` | Time the current chapter started |
| `questTimes` | object `<quest_id:string> -> int` | `{"100000001": 1686570300, …}` | Completion timestamp per quest. 21 of 30 shipped maps have 26 entries each; the other 8 are `{}`. |
| `idCurrentMission` | int **or** string | `0` (initial), `"3"` (Neutral) | Current chapter number. Type is inconsistent across the corpus: 26 maps use `int`, 5 use `str`. `collect_mission` writes a `str`. |
| `currentQuestVars` | object or null | `null` (initial), `{}`, `{"spawned":"true","id":"1"}` | Quest state flags. Observed key sets: `{}`, `{spawned,id}`, `{spawned,id,activators}`, `{spawned,id,playerLevel,startTile}`. Values are **strings** (e.g. `"true"`, `"42"`) and `activators`/`startTile` are themselves JSON-encoded strings. |
| `items` | object `<index:string> -> array[8]` | see below | The map contents |
| `__#__ITEMS_hint` | array of string | `["0 = item_id", "1 = x", …]` | **Documentation-only** key, present in `Neutral.json` and `Scarlet.json` only. Not read by any code. It is the authoritative in-repo description of the item layout. |

### 5.3 `map["items"]` — the item map

**Key:** the item index as a **string** (JSON object keys are always strings). The client uses this index to address the item in later commands (`move`, `sell`, `orient`, …). New items are appended with `map["items"][str(index)] = ...` in `engine.map_add_item()`.

**Value:** an array of exactly **8** elements. Verified: **12 954 / 12 954** item arrays across all 30 shipped village files have length 8, and all have the type tuple `(int, int, int, int, int, list, dict, int)`.

| Index | Name | Type | Meaning |
|---|---|---|---|
| `[0]` | `item_id` | int | Config item id → `config.items[].id` |
| `[1]` | `x` | int | Grid X coordinate |
| `[2]` | `y` | int | Grid Y coordinate |
| `[3]` | `timestamp` | int | Last production/activation timestamp (unix). Set by `collect` (`= now`), `activate`, `push_unit`, `set_resource_allies`; rewound by `fast_forward`. |
| `[4]` | `orientation` | int | Sprite frame / rotation. `orient` writes `int(orientation)`. |
| `[5]` | `store` | array | **Training queue** of pending units. Each entry is itself an 8-element array (same layout) — 142 such entries observed across the corpus. `push_unit` appends, `pop_unit` pops by `item_id`. |
| `[6]` | `attr` | object | Per-item attribute dictionary (see below) |
| `[7]` | `player_id` | int | Owning team. `1` = PLAYER_SELF, `2` = PLAYER_ENEMY, `3` = PLAYER_NEUTRAL (per `__#__ITEMS_hint`). Observed in the corpus: `1` × 11 337, `3` × 1 617. `2` never appears. |

`engine.map_add_item()` writes:
```python
map["items"][str(index)] = [item, x, y, timestamp, orientation, store, attr, player]
```
and, when `player == 1`, pre-populates the attribute dict from the config:
* if the item's `properties` JSON contains `friend_assistable > 0` → `attr["si"] = []`
* if the item's `clicks_to_build > 0` → `attr["nc"] = 0`

### 5.4 `attr_dict` (`item[6]`) — every key found in the corpus

| Key | Type | Where written | Meaning |
|---|---|---|---|
| `si` | list | `engine.map_add_item` (`= []`), `engine.buy_si_help` (`= [0]` or `.append(0)`), `engine.finish_si` (delete) | **Socially In Construction** helper list. `[]` = the building is waiting for help. `[0, 0, …]` = helper slots, `0` marks a *bought* helper (as opposed to a friend's). `buy_si_help` appends `0`; `finish_si` deletes the key. |
| `nc` | int | `engine.map_add_item` (`= 0`), `engine.add_click` (`+= 1`), `engine.activate_item_click` (delete) | **"N Clicks"** — number of remaining clicks required to finish a click-to-build. Deleted when done. |
| `cp` | int | `command.activate` (`item[6]["cp"] = args[1]`) | **Collection Point** / activation counter. Set to the `activate` command's `args[1]`. `activate` with `args[1] <= 0` wipes the whole `attr` dict (`item[6] = {}`). |
| `nu` | int | `engine.push_queue_unit` / `push_queue_unit2` (`+= 1` or `= 1`), `engine.pop_queue_unit` (`-= 1` or delete) | **N Umber** — number of units queued at a building (Atom Fusion, etc.) |
| `ts` | int | `engine.push_queue_unit` / `push_queue_unit2` (`= now`), `engine.pop_queue_unit` (delete), `command.soulmixer_speedup` (`= 0`), `command.fast_forward` (rewound) | Queue **t**ime**S**tamp — when the queued training started. For the Atom Fusion it is the training start time used by `soulmixer_speedup` to compute the remaining time. |
| `ui` | int | `engine.push_queue_unit2` (`= unit_id`), `engine.pop_queue_unit` (delete) | **U**nit **I**d — the specific unit id queued in the Atom Fusion (only present with `push_queue_unit2`). |
| `xp` | int | `command.add_xp_unit` (`= xp_gain` or `+= xp_gain`) | Accumulated unit XP (unit level-up progress). 171 items carry it across the corpus. |

> The queue sub-array at `item[5][i]` is a full 8-element item array; the only `attr` key observed inside a queued unit is `xp` (10 occurrences).
>
> **Total distinct `attr_dict` keys: 7** — `si`, `nc`, `cp`, `nu`, `ts`, `ui`, `xp`.

### 5.5 `privateState` — every key, what it means, and whether the server touches it

All 30 shipped village files have the **same 47 keys** in `privateState`, in the **same order** (verified: `list(initial.privateState.keys()) == list(Neutral.privateState.keys())`). The table lists each key, its type, a real value, its meaning, and whether the Python server reads/writes it.

| # | Key | Type | Real value (Neutral.json) | Meaning | Server touches it? |
|---|---|---|---|---|---|
| 1 | `publishedOpenGraphUnit` | list\<str\> | `["1296","1028","1042",…]` | Item ids already published to a Facebook Open Graph story | **W** — `rt_open_graph_unit` |
| 2 | `weeklyRewardIndex` | int | `3` | Index into the Monday-bonus reward table (length 3) | **W** — `weekly_reward` |
| 3 | `neighborAssists` | object | `{}` | Pending friend-assist requests/rewards | No (client-only) |
| 4 | `friendsHelpedCoveredItem` | null / list | `null` | Item id already rewarded for helping a friend | No |
| 5 | `lastUpgrades` | list | `[]` | Recently upgraded buildings (client-side "upgrade" tracking) | No |
| 6 | `timestampLastBonus` | int | `1688653422` | Last daily-bonus claim | **W** — `win_daily_bonus`, `fast_forward` |
| 7 | `timeStampMondayBonus` | int | `1686569823` | Last Monday-bonus claim | **W** — `weekly_reward` (deliberately *not* rewound by `fast_forward`) |
| 8 | `timestampLastAllianceBonus` | int | `0` | Last alliance bonus claim | **W** — `fast_forward` only |
| 9 | `bestUnit` | null / int | `null` | Player's "best unit" (for the profile/leaderboard) | No |
| 10 | `firstTimeAlliance` | null / bool | `null` | Whether the alliance screen has been seen | No |
| 11 | `marketPlaceFirstTime` | null / bool | `true` | Whether the Auction House has been seen | **W** — `first_time_marketplace` |
| 12 | `message` | null / string | `null` | Alliance/notification message | No |
| 13 | `strategy` | int | `1` | Attack strategy preference (1 = default) | No |
| 14 | `betWin` | list | `[]` | Auction-house wins history | No (auctions disabled) |
| 15 | `attacksSent` | list | `[]` | Outgoing attack log | No |
| 16 | `attacksReceived` | list | `[]` | Incoming attack log | No |
| 17 | `tsAttacksReset` | int | `0` | Timestamp of the last attack-counter reset | **W** — `fast_forward` |
| 18 | `tsSpyingsReset` | int | `0` | Timestamp of the last spy-counter reset | **W** — `fast_forward` |
| 19 | `attacksPack` | int | `0` | Number of attacks bought in a pack | No |
| 20 | `spyings` | list | `[]` | Spy log | No |
| 21 | `spyingsPack` | int | `0` | Number of spyings bought in a pack | No |
| 22 | `deadHeroes` | object\<str→int\> | `{"1050": 12, "1001": 28, …}` | **Hospital**: item id → number of dead (resurrectable) units awaiting revival | **W** — `sell`/`kill` (via `push_dead_unit`), `resurrect_hero`, `end_quest`/`end_attack` (via `map_lose_item`) |
| 23 | `timeStampEndPremium` | int | `1682945878` | Unix ts when premium expires | **W** — `buy_premium_account` |
| 24 | `unlockedSkins` | null / list | `null` | Unlocked empire skins | No |
| 25 | `unlockedQuestIndex` | int | `0` | Highest quest index unlocked | No |
| 26 | `questsRank` | object\<str→str\> | `{"0":"1","1":"1",…}` | Quest index (string) → difficulty rank (string) | **W** — `admin_set_quest_rank` |
| 27 | `magics` | object\<str→int\> | `{"10":0,"9":1,"1":2,"2":0,"4":2}` | Magic spell id (string) → number of charges | **W** — `buy_magic`, `use_magic` |
| 28 | `timeStampDartsReset` | int | `1705795645` | Start of the current darts week. `0` means "the client must call `darts_reset`" (this is how `new_village()` and `reset_stuff()` initialise it) | **W** — `darts_reset`, `reset_stuff` (sets to 0 on a new week) |
| 29 | `timeStampDartsNewFree` | int | `1705795645` | Timestamp of the last free darts shot | **W** — `darts_reset`, `darts_new_free`, `darts_shoot_balloon`, `fast_forward` |
| 30 | `dartsBalloonsShot` | list\<int\> | `[]` (AcidCaos: `[18,17]`) | Indices of balloons already shot this week | **W** — `darts_reset`, `darts_shoot_balloon` |
| 31 | `dartsRandomSeed` | int | `9709` | RNG seed for the darts layout | **W** — `darts_reset` |
| 32 | `dartsHasFree` | bool | `true` | Whether a free shot is available | **W** — `darts_reset`, `darts_new_free`, `darts_shoot_balloon` |
| 33 | `dartsGotExtra` | bool | `false` | Whether the "extra" (jackpot) shot was won | **W** — `darts_reset`, `darts_shoot_balloon` |
| 34 | `boughtUnits` | list\<int\> | `[1001, 30, 1007, 1, 86, …]` | Item ids the player has ever bought (drives the store UI) | **W** — `bought_unit_add` from many commands |
| 35 | `unitCollectionsCompleted` | list\<int\> | `[]` (Nerri: `[1]`) | Completed unit-collection ids | **W** — `unit_collections_completed` |
| 36 | `mana` | int | `15` | Premium "mana" currency (used by magic spells) | **W** — `apply_resources` (clamped at 0) |
| 37 | `inventoryItems` | object\<str→int\> | `{"61": 208, "55": 16, …}` | Inventory consumables: item id → quantity | **W** — `add_inventory_item`, `remove_inventory_item` |
| 38 | `collections` | list\<int\> | `[10, 3, 8, 5, 1, 2, 4, 6, 7, 9]` | Completed collection ids | **W** — `complete_collection` |
| 39 | `energy` | int | `50` | Action energy | No (client-only) |
| 40 | `researchItemNumber` | array\<int\>[2] | `[0, 6]` | Completed research items per track: **[0] = Area 51, [1] = Robotic Center** | **W** — `next_research_item`, `reset_research_item` |
| 41 | `researchStepNumber` | array\<int\>[2] | `[0, 0]` | Current research step per track | **W** — `next_research_step`, `next_research_item`, `reset_research_item` |
| 42 | `timeStampDoResearch` | array\<int\>[2] | `[0, 0]` | Research start timestamp per track | **W** — `next_research_step`, `research_buy_step_cash`, `next_research_item`, `reset_research_item`, `fast_forward` |
| 43 | `crossPromotionsFinished` | list | `[]` | Which cross-promotions (Social Empires / Dragon City) have been shown | No |
| 44 | `helpMap` | list | `[]` | Onboarding/help-screen progress | No |
| 45 | `worldChange` | int | `0` | Counter for the "world changed" notification | No |
| 46 | `bonusNextId` | int | `2` | Next daily-bonus slot (1..5) | **W** — `win_daily_bonus` |
| 47 | `goals` | array | `[null, [1,1], null, [1,1], …]` | Goal progress, **indexed by goal id**: `null` = not started, `[visited, currentStep]` = in progress. Padded with `null` to the goal id. | **W** — `set_goals` (via `engine.set_goals`) |

> **Count check.** The table has exactly **47** rows, matching the 47 keys present in every shipped `privateState` object (verified programmatically against `initial.json` and `Neutral.json`). The full key list, in file order, is: `publishedOpenGraphUnit, weeklyRewardIndex, neighborAssists, friendsHelpedCoveredItem, lastUpgrades, timestampLastBonus, timeStampMondayBonus, timestampLastAllianceBonus, bestUnit, firstTimeAlliance, marketPlaceFirstTime, message, strategy, betWin, attacksSent, attacksReceived, tsAttacksReset, tsSpyingsReset, attacksPack, spyings, spyingsPack, deadHeroes, timeStampEndPremium, unlockedSkins, unlockedQuestIndex, questsRank, magics, timeStampDartsReset, timeStampDartsNewFree, dartsBalloonsShot, dartsRandomSeed, dartsHasFree, dartsGotExtra, boughtUnits, unitCollectionsCompleted, mana, inventoryItems, collections, energy, researchItemNumber, researchStepNumber, timeStampDoResearch, crossPromotionsFinished, helpMap, worldChange, bonusNextId, goals`.

### 5.6 Save validation

`sessions.is_valid_village(save)` is applied to every file in `saves/`, every static village, and every quest village:
* must contain `playerInfo`, `maps`, `privateState`;
* every map must contain `oil` and `steel`;
* a map must **not** contain `stone` or `food` (Social Empires guard);
* every map must contain an `items` key that is a `dict`.

Invalid files are skipped with a printed message (`"Invalid Save"` / `"Invalid neighbour"` / `"Invalid Quest"`).

---

## 6. The `villages/` content model

### 6.1 `villages/initial.json` — the new-player template

Loaded once at import time into `sessions.__initial_village` (`copy.deepcopy`'d on each new village).

* `playerInfo.pid` = `null` (replaced with a fresh UUID4 by `new_village()`).
* `playerInfo.name` = `"Warrior"`, `pic` = `""`, `cash` = `5`, `completed_tutorial` = `0`, `default_map` = `0`, `map_names` = `["Empire"]`, `map_sizes` = `[0]`, `world_id` = `null`, `sp_ref_uid` = `1000`, `sp_ref_cat_install` = `"ts"`, `last_logged_in` = `0`.
* `maps[0]`: `expansions = [35, 36, 45, 46]`, `timestamp = 0`, `xp = 4`, `level = 1`, `gold/wood/oil/steel = 2000` each, `race = "h"`, `skin = 0`, all other counters 0, `currentQuestVars = null`.
* `maps[0].items`: **40 entries**, indices `"1"`–`"40"`. Composition:
  * `"1"` = `[26, 51, 41, 0, 0, [], {}, 1]` — item 26 = command centre (town hall)
  * `"2"` = `[905, 53, 39, 0, 0, [], {}, 1]` — item 905 = tree 1×1
  * `"3"`–`"20"` = item 23 (wall 1) and 22 (tower 1) — 18 wall/tower pieces
  * `"21"`–`"37"` = items 930 (tree 2×2), 931 (tree 3×3), 929 (bridge), 928 (broken bridge) — the terrain, all with `player_id = 3` (neutral)
  * `"38"` = `[909, 17, 6, 0, 0, [], {}, 3]` (space station), `"39"` = `[907, 74, 29, 0, 0, [], {}, 3]` (small harbour), `"40"` = `[908, 99, 92, 0, 0, [], {}, 3]` (harbour)
  * Measured totals: 20 items with `player_id = 1` and 20 with `player_id = 3`; item ids `23`×16, `929`×7, `930`×6, `22`×2, `931`×2, `928`×2, and one each of `26`, `905`, `909`, `907`, `908`.
* `privateState`: the 47-key default with `strategy = 1`, `energy = 50`, `mana = 0`, `timeStampDartsReset = 0`, `goals` = **151 × `null`**.

`new_village()` then:
1. generates `USERID = str(uuid.uuid4())`,
2. `assert USERID not in all_userid()`,
3. deep-copies `__initial_village`,
4. sets `village["version"] = None` (so `migrate_loaded_save` will tag it),
5. sets `village["playerInfo"]["pid"] = USERID`,
6. sets `village["maps"][0]["timestamp"] = timestamp_now()`,
7. sets `village["privateState"]["timeStampDartsReset"] = 0` (forces the client to call `darts_reset`),
8. runs `migrate_loaded_save(village)`,
9. registers it in `__saves` and calls `save_session(USERID)`.

### 6.2 Static neighbours — `villages/*.json` (7 files)

| File | `playerInfo.pid` | `name` | Level | Items | `version` |
|---|---|---|---|---|---|
| `AcidCaos.json` | `AcidCaos` | `AcidCaos` | 41 | 319 | `0.02a` |
| `General_Mike_30.json` | `100000030` | `General` | 40 | 436 | `null` |
| `General_Mike_31.json` | `100000031` | `General` | 40 | 436 | `null` |
| `Kiriakos.json` | `Kiriakos` | `Kiriakos 96d` | 46 | 569 | `0.02a` |
| `Nerri.json` | `Nerri` | `Nerri` | 42 | 367 | `0.02a` |
| `Neutral.json` | `Neutral` | `[Neutral]` | 44 | 549 | `0.02a` |
| `Scarlet.json` | `Scarlet` | `Scarlet` | 33 | 576 | `0.02a` |

All 7 have exactly one map, `race = "h"`, `skin = 0`, `world_id = null`, `sp_ref_uid = 1000`, `sp_ref_cat_install = "ts"`.

`Neutral.json` and `Scarlet.json` additionally carry the `__#__ITEMS_hint` documentation key.

They are loaded by `load_static_villages()` into `sessions.__villages`, keyed by `playerInfo.pid`. They are **never written back to disk** — they are read-only content.

`fb_friends_str()` and `neighbors()` both **exclude** pids `100000030` and `100000031` (General Mike) from the friend list.

### 6.3 Quest villages — `villages/quest/*.json` (**23 files**, not 22)

| File | pid | `name` | Level | xp | Items |
|---|---|---|---|---|---|
| `100000001.json` | 100000001 | `Mission` | 35 | 0 | 381 |
| `100000002.json` | 100000002 | `Mission` | 65 | 0 | 494 |
| `100000003.json` | 100000003 | `Mission` | 34 | 0 | 154 |
| `100000004.json` | 100000004 | `Mission` | 67 | 0 | 348 |
| `100000005.json` | 100000005 | `Mission` | 15 | 0 | 337 |
| `100000006.json` | 100000006 | `Mission` | 36 | 0 | 465 |
| `100000007.json` | 100000007 | `Mission` | 21 | 0 | 310 |
| `100000008.json` | 100000008 | `Mission` | 28 | 5 | 430 |
| `100000009.json` | 100000009 | `Mission` | 12 | 0 | 236 |
| `100000010.json` | 100000010 | `Mission` | 33 | 0 | 276 |
| `100000011.json` | 100000011 | `Mission` | 58 | 0 | 724 |
| `100000012.json` | 100000012 | `Mission` | 2 | 0 | 39 |
| `100000013.json` | 100000013 | `Mission` | 6 | 0 | 293 |
| `100000014.json` | 100000014 | `Mission` | 14 | 0 | 841 |
| `100000017.json` | 100000017 | `Mission` | 26 | 0 | 616 |
| `100000018.json` | 100000018 | `Mission` | 19 | 0 | 773 |
| `100000019.json` | 100000019 | `Mission` | 19 | 0 | 728 |
| `100000020.json` | 100000020 | `Mission` | 13 | 0 | 367 |
| `100000021.json` | 100000021 | `mission` | 13 | 10000 | 253 |
| `100000022.json` | 100000022 | `mission` | 17 | 15000 | 548 |
| `100000025.json` | 100000025 | `mission` | 16 | 15000 | 811 |
| `100000026.json` | 100000026 | `mission` | 23 | 20000 | 219 |
| `100000049.json` | 100000049 | `Weekly Mission` | 4 | 0 | 19 |

All 23 have `version: "0.01a"` (they will be migrated to `0.02a` in memory on load — but **quest files are never re-saved**, so the on-disk file keeps `0.01a`; `load_quests()` calls `migrate_loaded_save` but never `save_session`).

**Id convention.** The quest id is `1000000NN`:
* `100000001`–`100000014` → the 14 scripted chapters (Quest 1–14).
* `100000015`, `100000016` are **absent** — the numbering jumps to `100000017`.
* `100000017`–`100000022` → HARDCORE 1–6.
* `100000023`, `100000024` are **absent** as files.
* `100000025`, `100000026` → ISLA episodes.
* `100000049` → `QUEST: WEEKLY_01` (the weekly mission).
* `100000100` → `QUEST: DEFEND_CONVOY` (in the constants map, but **no file**).

The `1000000xx` prefix is also what `get_player_info.php` uses to route a `user=` parameter to the quest branch (`user.startswith("100000")`), and `globals.ISLE_ORDER` lists the quest ids as strings in play order:
`["100000006","100000007","100000008","100000002","100000012","100000021","100000022","100000003","100000028","100000014","100000013","100000020","100000015","100000019","100000018","100000023","100000011","100000033"]` — note several of these (15, 23, 28, 33) have **no** quest village file.

`load_quests()` enforces the filename↔pid correspondence with an `assert`:
```python
QUESTID = village["playerInfo"]["pid"]
assert file.split(".")[0] == QUESTID
```
→ A mismatched filename crashes the server at startup.

### 6.4 `constants.py` — `Quests.QUEST`

`Quests.QUEST` is a **dict literal with duplicate keys**, so Python keeps only the last occurrence. The source text lists 31 entries; the effective dict has **28**. The duplicates are:

| Key | Written as | Effective value |
|---|---|---|
| `100000023` | `QUEST 21: HARDCORE7` | `QUEST 21: HARDCORE7` |
| `100000024` | `QUEST 22: HARDCORE8` → later `QUEST: ISLA_RUBEN3D` | **`QUEST: ISLA_RUBEN3D`** |
| `100000025` | `QUEST 23: HARDCORE10` → later `QUEST: ISLA_KASPAR` | **`QUEST: ISLA_KASPAR`** |
| `100000026` | `QUEST 22: HARDCORE9` → later `QUEST: ISLA_EGG2` | **`QUEST: ISLA_EGG2`** |

The effective 28-entry map:

```
100000001 → QUEST 01: BAZOOKA              100000015 → (absent)
100000002 → QUEST 02: CENTRAL_NUCLEAR      100000016 → (absent)
100000003 → QUEST 03: DEFEND_CONVOY_AUTO   100000017 → QUEST 15: HARDCORE1
100000004 → QUEST 04: SUPERTANK            100000018 → QUEST 16: HARDCORE2
100000005 → QUEST 05: ASSAULT_CONVOY       100000019 → QUEST 17: HARDCORE3
100000006 → QUEST 06: AIRSTRIKE            100000020 → QUEST 18: HARDCORE4
100000007 → QUEST 07: SHIP                 100000021 → QUEST 19: HARDCORE5
100000008 → QUEST 08: ROCKET               100000022 → QUEST 20: HARDCORE6
100000009 → QUEST 09: LABORATORIES         100000023 → QUEST 21: HARDCORE7
100000010 → QUEST 10: SPECIAL_OPS          100000024 → QUEST: ISLA_RUBEN3D
100000011 → QUEST 11: SAVE_VILLAGES        100000025 → QUEST: ISLA_KASPAR
100000012 → QUEST 12: TANKBOSS             100000026 → QUEST: ISLA_EGG2
100000013 → QUEST 13: TYRANNOSAURUS        100000027 → QUEST: ISLA_EGG1
100000014 → QUEST 14: SPY_2                100000028 → QUEST: BOSS_DRAGON_1
                                           100000049 → QUEST: WEEKLY_01
                                           100000100 → QUEST: DEFEND_CONVOY
```

The map is used in exactly two places:
* `sessions.load_quests()` — only to print a friendly name at load time.
* `server.get_player_info_response()` — only to print the quest name in the `[QUEST] USERID … loading <name> (<id>).` log line.

It is **not** used for routing, validation, or gating. `globals.QUESTS_MIN_LEVELS = {"100000021": 40, "100000022": 40, "100000025": 40, "100000026": 40}` is the only level gate in the config, and nothing in the Python server enforces it.

### 6.5 The "General Mike" special case

`General_Mike_30.json` (pid `100000030`) and `General_Mike_31.json` (pid `100000031`) are two **near-identical** level-40 villages (both 436 items, same expansions, same resources to within a rounding difference: GM30 has `g=62955, w=961532, o=976279, s=957172`). The two files are **not** byte-identical (`GM30 == GM31 → False`).

The special case lives in `server.get_player_info_response()`:
```python
elif user in ["100000030", "100000031"]:
    return (get_neighbor_info("100000030", map), 200)
```
→ **Both ids resolve to the `100000030` village.** `100000031` is never served. Presumably the SW client requests one id for the "General Mike" NPC and the other for a variant, and the original server treated them as the same player with two save slots.

They are also excluded from `fb_friends_str()` and `neighbors()` so they never appear as friends/neighbours.

### 6.6 `constants.py` — the `Constant` class

`constants.py` is 1 110 lines with **1 072** class-level constant assignments:

| Group | Count | Examples |
|---|---|---|
| `ID_UNIT_*` | 431 | `ID_UNIT_SPY = 1005`, `ID_UNIT_ZODIAC = 1018`, `ID_UNIT_SHIP = 1019` |
| `ID_BUILDING_*` | 288 | `ID_BUILDING_OIL_1 = 901`, `ID_BUILDING_ROBOTIC_CENTER = 86`, `ID_BUILDING_SOUL_MIXER = 302` |
| `SUBCATFUNC_*` | 35 | `SUBCATFUNC_BUILDING_TOWNHALL = 135`, `SUBCATFUNC_UNIT_SIEGE = 81` |
| `SUBCAT_*` | 15 | `SUBCAT_HOUSE = 11`, `SUBCAT_TREASURE = 81` |
| `CAT_*` | 8 | `CAT_BUILDING_TOWN = 1`, `CAT_UNIT = 7` |
| Other | 290 | `WEEKDAY_*` (7), `KEY_*` (20), `GROUP_TYPE_*` (9), `SPELL_*` (~20), `TERRAIN_*` (4), `INCREMENT_*` (5), `INVENTORY_ITEM_*` (2), `ID_INV_ITEM_LICENSE = 10`, … |

Note `SUBCATFUNC_UNIT_MOUNTED = 79` and `SUBCATFUNC_UNIT_MOTORIZED = 79` collide (same value); `SUBCAT_UNIT = 7` and `SUBCATFUNC_TERRAIN = 6` / `SUBCAT_TERRAIN = 6` also collide.

**`Constant` is imported by `command.py` but never used.** A grep for `Constant.` across the repo returns **zero** hits. The whole 1 072-constant table is dead weight in the Python server — it exists for reference / for the Flash client.

---

## 7. The game-config pipeline

### 7.1 The config artefacts

| File | Size | What it is |
|---|---|---|
| `config/main.json` | 1 702 871 B | The **canonical** config: pretty-printed (4-space) JSON, 20 top-level sections. |
| `config/get_game_config.php_29august2012_nohash.json` | 1 702 871 B | **Byte-identical to `main.json`** (verified by direct byte comparison). |
| `config/get_game_config.php_29august2012_nohash.txt` | 945 466 B | The *same data* as compact (separators-free) JSON — a `json.dumps` without indentation. Semantically equal, 44 % smaller. |
| `config/get_game_config.php_29august2012.txt` | 945 531 B | The **original server response** of 29 Aug 2012: `8f41e55bbe8e19395295adbaa656b1e25b0cfc9363ab89c6b0c38705d7982e7e;` + compact JSON. The 64-char hash + `;` is the same framing as `command.php`. |
| `config/get_game_config.php_23july2012.txt` | 930 791 B | The original server response of 23 Jul 2012: `ff31eef4221ea09cc84e9703ddcf54af7a26c133a33e1c2f765a34614f04d509;` + compact JSON. |

**Section-by-section equality between the 29-Aug capture and `main.json`: all 20 sections are exactly equal** (verified). So `main.json` *is* the 29-Aug-2012 live config, re-serialised with `indent=4`.

**Difference between the 23-July and 29-August captures** (4 sections changed, all others byte-equal):

| Section | 23 Jul 2012 | 29 Aug 2012 | Change |
|---|---|---|---|
| `items` | 766 | 778 | +12 new items |
| `offer_packs` | 38 | 44 | +6 new offer packs |
| `images` | 594 | 607 | +13 new image entries |
| `globals` | 104 | 104 | same key set, some values changed (e.g. `NEWS_IMAGE`, `NEWS_STORE`, `ISLE_ORDER`, `LIMITED_EDITION_EXPIRATION`) |

Everything else (`categories`, `inventory_items`, `expansion_prices`, `levels`, `neighbor_assists`, `town_prices`, `map_prices`, `findable_items`, `goals`, `social_items`, `sounds`, `collections`, `level_ranking_reward`, `darts_items`, `units_collections_categories`, `magics`) is identical between the two captures.

`main.json` also contains the `darts_items` from the 29-Aug capture — e.g. entry 1 starts `"2012-01-31 23:00:00"` and entry 30 starts `"2012-08-30 23:00:00"`, with `extra_item` 1226 for entry 30.

### 7.2 Load order at import time

`get_game_config.py` executes at **import**, before Flask starts:

```
__game_config = json.load(open(CONFIG_DIR/"main.json"))
patch_game_config()        # config/patch/patches.txt  -> config/patch/<name>.json
modify_game_config()       # mods/mods.txt            -> mods/<name>.json
remove_duplicate_items()   # de-duplicate config["items"] by "id"
...
make_dynamic(__game_config)   # called at module bottom (line 319)
```

`patch_game_config()` / `modify_game_config()` read a plain-text list file, one name per line; `#` starts a comment; blank lines are skipped; `.json` is optional; the name is resolved as `{dir}/{name}.json` and applied with `jsonpatch.apply_patch(__game_config, patch, in_place=True)`. A missing file prints `" * Patch ERROR: Could not find <name>"` and is skipped (no exception).

`get_game_config()` calls `make_dynamic(__game_config)` and returns the (mutated) dict — the same object every time, so the response is the mutable global.

### 7.3 The patches (`config/patch/`)

`config/patch/patches.txt` (verbatim, with the section comments):
```
### Add items at the end of the array ("/items/-")
atom_fusion_item
unit_patch

### Order-dependent item modifications. Craft carefully (mindful of the above)
atom_fusion_items_data

### Patch other config values
atom_fusion_powerup

### Darts wrap fix
targets
```

| Patch | Ops | Effect (measured) |
|---|---|---|
| `atom_fusion_item.json` | 1 × `add` at `/items/-` | Adds **item id `302` "Atom Fusion"** — a 3×3 bunker building, `subcat_functional 211`, `min_level 19`, `unit_capacity 2`, `building_limit_same_id 1`, `group_type "BUNKER"`, `costs {"g":0}`. |
| `unit_patch.json` | 121 × `add` at `/items/-` | Adds **121 units**, ids **1307–1431** (e.g. `1307 Glaivestorm Mech`, `1308 Glaivestorm Drone`, … `1431 Intruder Drone`). All are `type: "u"`, `in_store: "0"`, `costs {"c": N}` (cash-only), `subcat_functional 80` (ground) or `83` (air). **None of the ids collide with `main.json`** (verified: 0 overlaps). |
| `atom_fusion_items_data.json` | 600 × `add` (300 item indexes × 2 fields) | Adds `breeding_order` and `sm_training_time` to **300 items** (array indexes **382 – 898**, i.e. item ids `1002`…`1305`). Generated by `tools/atom_fusion_builder.py`. Example: `/items/382/breeding_order = "7"`, `/items/382/sm_training_time = "14000"`. |
| `atom_fusion_powerup.json` | 1 × `add` at `/globals/SOUL_MIXER_POWERUPS_LEVELS` | Adds a **new global** (the only one): 6 tiers of `{cash_cost, order_increment}` — `(1,1), (2,2), (4,4), (8,8), (15,15), (20,20)`. |
| `targets.json` | 1 × `replace` at `/darts_items` | **Replaces the whole 30-entry `darts_items` array with a 27-entry array.** The 27 entries are the original entries 1–27 **rotated one week later** (entry 1 gets entry 5's content, entry 2 gets entry 6's, … entry 27 gets entry 5's content again — i.e. the list is shifted), with the new dates starting `2012-03-02 23:00:00` and ending `2012-09-06 23:00:00`. Entries 28, 29, 30 are **dropped**. The effect is to move the darts rotation's wrap point back so that `make_dynamic()` can roll it forward. |

**Net effect of the 5 patches:**

| Metric | `main.json` | After patches |
|---|---|---|
| `items` | 778 | **900** |
| `globals` | 104 | **105** (+`SOUL_MIXER_POWERUPS_LEVELS`) |
| `darts_items` | 30 | **27** |

### 7.4 The mods (`mods/`)

`mods/mods.txt` (verbatim):
```
# Mods are loaded from the "mods" folder in the order provided below
# You don't need to provide the .json extension here, just the name
# If a line starts with #, it is ignored

# This mod removes the need to pay with cash or hire friends for most buildings making it easier to progress.
# Usually you would have to pay cash to open a building like a factory since hiring friends cannot be done anymore.
# no_hiring_needed
```

> **The mod is COMMENTED OUT by default.** The shipped configuration therefore applies **zero mods**. The log line is `" * Mod applied: no_hiring_needed"` only when the user uncomments it.

`mods/no_hiring_needed.json` has **4 ops**:

| Op | Path | Effect |
|---|---|---|
| `replace` | `/social_items` | Replaces the whole 26-entry `social_items` array with a **2-entry** array: id `61` (worker_cost 2, "Ally I…Ally IX") and id `74` (worker_cost 2, "Friend" ×8). |
| `add` | `/items/-` | Adds **item `6` "Wood Factory II"** with `activation: "1"` (free to open) — the base config's item 6 has `activation: "0"`. |
| `add` | `/items/-` | Adds **item `8` "Steel Factory II"** with `activation: "1"`. |
| `add` | `/items/-` | Adds **item `90` "Market II"** with `activation: "0"` but `costs {"g":500}` (base item 90 has a different cost). |

**Measured effect of enabling the mod** (patch + mod, in code order):

| Stage | `items` | duplicate ids |
|---|---|---|
| after `main.json` | 778 | 0 |
| after `atom_fusion_item` | 779 | 0 |
| after `unit_patch` | 900 | 0 |
| after `atom_fusion_items_data` | 900 | 0 |
| after `atom_fusion_powerup` | 900 | 0 |
| after `targets` | 900 | 0 |
| after mod `no_hiring_needed` | 903 | **3** (`6`, `8`, `90` — each twice) |
| after `remove_duplicate_items()` | **900** | 0 |

With the mod enabled the server log prints `" * Removed 3 duplicate items."`. With the shipped (mod-disabled) configuration it prints `" * Removed 0 duplicate items."` — *Verified in the live server log.*

### 7.5 `remove_duplicate_items()` — how the tie is broken

```python
def remove_duplicate_items():
    indexes = {}
    items = __game_config["items"]
    num_duplicate = 0
    while True:
        index = 0
        duplicate = False
        for item in items:
            if item["id"] in indexes:
                del items[indexes[item["id"]]]     # delete the EARLIER occurrence
                indexes.clear()
                duplicate = True
                num_duplicate += 1
                break
            indexes[item["id"]] = index
            index += 1
        if duplicate:
            continue
        break
```

* It compares the raw `item["id"]` **as a string** (`"6"` vs `"6"`), so `"06"` and `"6"` would **not** be considered duplicates.
* On a duplicate it deletes the **earlier** occurrence and restarts the scan — so the **later** occurrence wins. For `no_hiring_needed` this means the mod's `activation: "1"` versions of items 6, 8, 90 replace the base versions. This is the intended behaviour of the mod.
* It is O(n²) in the worst case (restart the scan after each deletion) — 900 items is fine, but it is a bad algorithm to port.
* It only touches `config["items"]`; no other section is de-duplicated.

### 7.6 `make_dynamic()` — the weekly Monday darts rotation

`get_game_config.make_dynamic(config)` + `update_darts(darts_items, ts_first, seconds, ts_now, debug)`.

Algorithm:
1. Take the **last** entry of `darts_items` as the wrap anchor; parse its `start_date` (`"%Y-%m-%d %H:%M:%S"`) into a local-time unix ts.
2. While `now >= last_ts`: call `update_darts(...)` and increment `wraps`.
3. `update_darts` rebuilds **every** entry's `start_date` from the anchor:
   * `new_date = ts_first + shift`, where `shift` starts at 0 and increases by **604 800 s (1 week)** per entry.
   * **DST correction:** if the resulting local hour is `23`, `shift += 3600`; if it is `1`, `shift -= 3600`.
   * **Monday alignment:** using `new_date.isoweekday()` (Mon=1 … Sun=7), the shift is nudged so the result lands on a Monday:
     `weekday 2 → shift -= 86400`, `3 → -= 2×86400`, `4 → -= 3×86400`, `5 → += 3×86400`, `6 → += 2×86400`, `7 → += 86400`.
   * `game["start_date"] = new_date.strftime("%Y-%m-%d %H:%M:%S")`.
   * `last_ts = ts_first + shift`; `shift += week_length`.
4. The function returns the new `last_ts`, and the outer loop repeats until the anchor is in the future.

Because the wrap point is 27 weeks long, each entry occupies exactly one week, in order, starting on a Monday.

**Measured on 2026-10-20** with the shipped configuration: `wraps = 29` (the log prints `"[CONFIG] Darts minigame is now dynamic again! - Wrapped 29 time(s)!"`). The resulting dates are:

| id | start_date (after wrapping) | id | start_date |
|---|---|---|---|
| 1 | 2026-08-24 00:00:00 | 15 | 2026-11-30 00:00:00 |
| 2 | 2026-08-31 00:00:00 | 16 | 2026-12-07 00:00:00 |
| 3 | 2026-09-07 00:00:00 | 17 | 2026-12-14 00:00:00 |
| 4 | 2026-09-14 00:00:00 | 18 | 2026-12-21 00:00:00 |
| 5 | 2026-09-21 00:00:00 | 19 | 2026-12-28 00:00:00 |
| 6 | 2026-09-28 00:00:00 | 20 | 2027-01-04 00:00:00 |
| 7 | 2026-10-05 00:00:00 | 21 | 2027-01-11 00:00:00 |
| 8 | 2026-10-12 00:00:00 | 22 | 2027-01-18 00:00:00 |
| 9 | 2026-10-19 00:00:00 | 23 | 2027-01-25 00:00:00 |
| 10 | 2026-10-26 00:00:00 | 24 | 2027-02-01 00:00:00 |
| 11 | 2026-11-02 00:00:00 | 25 | 2027-02-08 00:00:00 |
| 12 | 2026-11-09 00:00:00 | 26 | 2027-02-15 00:00:00 |
| 13 | 2026-11-16 00:00:00 | 27 | 2027-02-22 00:00:00 |
| 14 | 2026-11-23 00:00:00 | | |

Notes:
* The `23:00:00` hour in the source data becomes `00:00:00` after wrapping because of the DST/`isoweekday` nudge. This is a real behavioural quirk of the algorithm.
* The `debug` knob in `make_dynamic` (`0` = off, `1` = print wrap dates, `2` = also print minor prizes, `3` = everything) is hard-coded to `0` in production; `debug - 1` is passed to `update_darts`, so with `debug = 0` the inner function receives `-1` and prints nothing.
* `make_dynamic` is called **once at import** (line 319) and **again on every `get_game_config()` call**. The second call is a no-op because the dates are already in the future.
* `engine.reset_stuff()` also resets the darts week on the *save* side: it compares `(now + 259200) // 604800` against `(timeStampDartsReset + 259200) // 604800` — the +3-day offset exists because **ts 0 is a Thursday** and the reset must land on Monday. If a new week is detected it sets `privateState.timeStampDartsReset = 0`, which makes the client call `darts_reset`.

### 7.7 Runtime config summary

| | Value |
|---|---|
| Top-level sections | 20 (identical key set to `main.json`) |
| `items` | **900** |
| `globals` | **105** |
| `darts_items` | **27** (dates rolled forward) |
| Served JSON size | **1 092 491 bytes** |
| Load time | The whole config is parsed, patched (5 jsonpatch ops over 900 items) and de-duplicated at import; the darts wrap loop runs 29 iterations. *Measured server start-to-ready: ~9 s* (dominated by the 1.7 MB JSON parse + 600 jsonpatch ops). |

---

## 8. Full schema of `config/main.json`

20 top-level sections. Counts are for `main.json` as shipped (before patches).

| # | Section | Type | Count | Notes |
|---|---|---|---|---|
| 1 | `categories` | dict\<id→obj\> | 6 | Top-level shop categories |
| 2 | `items` | list\<obj\> | **778** | Every building, unit, decoration, terrain piece |
| 3 | `inventory_items` | dict\<id→obj\> | **90** | Inventory consumables |
| 4 | `expansion_prices` | list\<obj\> | **98** | Price per expansion (index = expansion ordinal) |
| 5 | `levels` | list\<obj\> | **100** | Level table |
| 6 | `neighbor_assists` | list\<obj\> | 5 | Random "help me!" friend-assist events |
| 7 | `town_prices` | list\<obj\> | 4 | Additional-town price tiers |
| 8 | `map_prices` | list\<obj\> | 4 | Additional-map price tiers |
| 9 | `findable_items` | list\<obj\> | 10 | Share-to-find "park" items |
| 10 | `goals` | list\<obj\> | **91** | Tutorial/goal objectives, ids 1–91 |
| 11 | `offer_packs` | list\<obj\> | **44** | Cash purchase packs |
| 12 | `social_items` | list\<obj\> | 26 | Hireable social/ally workers |
| 13 | `globals` | dict | **104** | Flat tunables — dumped in full below |
| 14 | `images` | dict\<path→lang\> | **607** | Asset path → language code (all `"en"`) |
| 15 | `sounds` | list\<obj\> | **139** | Sound effect table |
| 16 | `collections` | list\<obj\> | 10 | Unit collections with cash prizes |
| 17 | `level_ranking_reward` | list\<obj\> | **50** | Leaderboard reward for levels 1–50 |
| 18 | `darts_items` | list\<obj\> | **30** | Weekly darts minigame rotation |
| 19 | `units_collections_categories` | dict\<id→obj\> | **20** | "Buy the whole collection" categories |
| 20 | `magics` | list\<obj\> | 10 | Magic spells |

### 8.1 `items` (778) — element schema

Every field is a **string** except `cost_type` (which is `null` for every item). The only "structured" fields are JSON-encoded strings: `costs`, `properties`, `premium_upgrade_costs` (empty string), `inventory_ids` (`"null"`).

| Field | Type | Meaning |
|---|---|---|
| `id` | str | Unique item id. Range in `main.json`: 1 – 10090. `type` breakdown: `b` = 469 (building), `u` = 308 (unit), `l` = 1 (the only "land" item: `925 Expandable Land`). |
| `in_store` | str `"0"`/`"1"` | Whether the item can be bought from the unit store. 166 items are `"1"`. |
| `name` | str | Display name, e.g. `"House I"`, `"Aircraft"`, `"Special Spy"`, `"Atom Fusion"` |
| `type` | str | `b` building / `u` unit / `l` land |
| `cost` | str | Legacy cost field (always `"0"`) |
| `cost_type` | null | Always `null` |
| `costs` | str (JSON) | Resource cost, e.g. `{"w":30}`, `{"g":150,"o":300}`, `{"c":10}` (cash). Observed key sets: `{c}`×375, `{g}`×96, `{w}`×95, `{g,s}`×86, `{g,o}`×64, `{g,w}`×33, `{s}`×24, `{o}`×5. |
| `xp` | str | XP awarded for placing/training |
| `display_order` | str | Sort order in the build menu |
| `activation` | str | `"1"` = can be opened without paying cash (this is what the `no_hiring_needed` mod flips) |
| `inventory_ids` | str | `"null"` or a JSON list of inventory-item ids that can be used on it |
| `expiration` | str | `"0"` = never expires |
| `collect` | str | Resources produced per collection cycle (`"250"` for depots) |
| `max_collects` | str | Maximum stacked collections |
| `collect_type` | str | Which resource is produced: `g`, `w`, `o`, `s` |
| `collect_xp` | str | XP per collection |
| `category_id` | str | Top-level category: 1 Village, 2 Defense, 3 Army, 4 Decorations, 5 Wonders, 6 Terrain, 7 Units, 8 Energy, 9 (1 item), 12 New |
| `subcategory_id` | str | Sub-category (see `categories`) |
| `subcat_functional` | str | Functional sub-category: `111` house, `121` mill, `124` mine, `129` depot, `131` blacksmith, `132` market, `133` church, `134` university, `135` townhall, `136` eagle, `137` healing, `138` collect, `211` tower, `221` wall, `222` door, `231` castle, `311` barracks, `321` archery, `331` stable, `341` workshop, `411` deco, `511` wonder, `1011` atrezo, `1211` heroes, `1311` refuge, `811` treasure, `71/72/73/78/79/80/81` unit classes, `6` terrain |
| `min_level` | str | Minimum player level |
| `width` | str | Grid width (tiles) |
| `height` | str | Grid height (tiles) |
| `giftable` | str | Can be gifted to a friend |
| `max_frame` | str | Number of animation frames |
| `img_name` | str | Base asset name under `/static/socialwars/` (e.g. `0001_house_1_m`) |
| `elevation` | str | Z-order layer |
| `unit_capacity` | str | How many units can be trained/stored in it |
| `attack` | str | Unit attack stat (buildings: `"0"`) |
| `defense` | str | Unit defense stat |
| `life` | str | Unit hit points |
| `velocity` | str | Unit movement speed |
| `attack_range` | str | Unit attack range |
| `attack_interval` | str | Attack cooldown (frames) |
| `new_item` | str | `"1"` marks newly added content |
| `population` | str | Population consumed/provided |
| `gift_level` | str | Minimum player level to receive as a gift |
| `cost_unit_cash` | str | Cash price per unit when batch-built |
| `race` | str | `h` human, `n` neutral, `-` n/a |
| `clicks_to_build` | str | Number of clicks to construct (`"1"` = click-to-build → drives `attr["nc"]`) |
| `trains_ids` | str | `"-1"` or a list of unit ids this building can train |
| `upgrades_to` | str | `"-1"` or the id of the next upgrade tier (e.g. House I `1` → `47`) |
| `best_against` | str | Unit class this counters: `ft_ground`, `ft_flying`, `ft_armored`, `ft_building` |
| `best_against_mult` | str | Damage multiplier vs. `best_against` |
| `properties` | str (JSON) | Flags. Observed flags: `ft_building`, `ft_ground`, `ft_flying`, `ft_armored`, `bulldozable`, `demolishable`, `resurrectable`, `seeStealthUnits`, `human`, `mechanic`, `grants_population`, `raisePopulationCap`, `depot`, `farm`, `multiCollectable`, `friend_assistable`, `tower`, `wall`, `hq`, `silo`, `wonder`, `auto_activable`, `chained`, `decoration`, `lost_item`, `regenerating`, `training_queue`, `allows_spy`, `pickable`, `usable`, `walkable`, `explosive`, `bunker`, `healer`, `harvester`, `worker`, `animal`, `fireman`, `animated`, `resource`, `waterborne` |
| `syringes` | str | Hero-revival syringes (the `INVENTORY_ITEM_SYRINGE = 35` item) |
| `volume` | str | Transport volume |
| `max_elem_vol` | str | Max volume of carried elements |
| `building_limit_same_id` | str | Max copies of this exact building per map (`-1` = unlimited) |
| `building_limit_same_scf` | str | Max copies per functional sub-category |
| `group_type` | str | `HOUSING`, `WOOD_FACTORY`, `STEEL_FACTORY`, `MARKET`, `BUNKER`, `ROBOT`, `AIR_VEHICLE`, `DRAGON`, `HEALER`, `LONG_RANGE`, `WORKER`, … |
| `training_time` | str | Training duration in frames |
| `premium_upgrade_costs` | str | JSON/empty — premium-speed-up pricing |
| `build_time` | str | Construction time (seconds) |
| `breeding_order` | str | **Added by the `atom_fusion_items_data` patch** to 300 items. Atom Fusion breeding power. |
| `sm_training_time` | str | **Added by the same patch** to 300 items. Atom Fusion training duration (seconds). |

### 8.2 `levels` (100)

| Field | Type | Meaning |
|---|---|---|
| `name` | str | Level title (`"Slave"`, `"Servant"`, `"Peon"`, `"Villager"`, `"Cadet"`, `"Squire"`, …, `"Conqueror"` from level 50 on) |
| `exp_required` | int | Cumulative XP needed. First 10: `0, 40, 60, 100, 200, 350, 550, 800, 1113, 1504`. Last 5: `6393631, 7286601, 8313517, 9494470, 2016089205` (the last is a sentinel / unreachable) |
| `reward_type` | str | `c` (cash) ×96, `s` (steel) ×2, `w` (wood) ×1, `g` (gold) ×1 |
| `reward_amount` | int | Reward quantity on reaching the level |

`get_xp_from_level(level)` returns `levels[level]["exp_required"]`; `get_level_from_xp(xp)` scans for the first level whose `exp_required > xp`. **`get_xp_from_level` is imported by `command.py` but never used**; `get_level_from_xp` is never used at all.

### 8.3 `goals` (91)

| Field | Type | Meaning |
|---|---|---|
| `id` | int | 1–91. `set_goals` uses this as an **array index** into `privateState.goals`. |
| `title` | str | e.g. `"Train another Villager"`, `"Build 5 wonders"` |
| `hint` | str | Hint text (empty in all shipped goals) |
| `description` | str | Long description shown in the client |
| `reward` | int | XP/cash reward (10 in all shipped goals) |

### 8.4 `collections` (10)

| Field | Type | Meaning |
|---|---|---|
| `id` | str `"1"`–`"10"` | **1-based**: `get_collection_name(id)` / `get_collection_prize(id)` use `index = max(0, collection - 1)` |
| `name` | str | e.g. `"Draggy Collection"`, `"Transformer Collection"`, `"Plane Collection"`, `"Defense Collection"`, `"Gun Collection"`, `"Tank Collection"`, `"Launcher Collection"`, `"Soldier Awards Collection"`, `"Relaxing Time Collection"`, `"Animal Collection"` |
| `item_ids` | str (JSON list) | e.g. `"[66,67,68,69,70]"` — 5 unit ids each |
| `prize` | str (JSON dict) | e.g. `"{\"1085\":1}"` — item id → quantity, added to `map["store"]` on `complete_collection` |
| `description` | str | `"collection description 1"` … `"collection description 6"` (the last several are copy-pasted) |
| `cashPrice` | str | `"9"`–`"75"` |

### 8.5 `inventory_items` (90) — dict keyed by id string `"1"`–`"90"`

| Field | Type | Meaning |
|---|---|---|
| `id` | str | Item id |
| `name` | str | e.g. `"Cement"`, `"Wood"`, `"Fire extinguisher"` |
| `cashPrice` | str | Cash price (`"2"`) |
| `droppable` | str | `"0"`/`"1"` — can be dropped |
| `dropRate` | str | Drop chance |
| `dropsFrom` | str | Item id that drops it |
| `description` | str | e.g. `"You can get this item as a gift from your friends"` |

### 8.6 `expansion_prices` (98)

| Field | Type | Meaning |
|---|---|---|
| `coins` | int | Premium currency price (0 for the first entries, 100 000 at the end) |
| `cash` | int | Cash price (0 → 20) |
| `neighbors` | int | Friend-assist requirement (0 → 15) |
| `inventory_qte` | int | Inventory item quantity requirement (0 → 30) |

### 8.7 `neighbor_assists` (5)

| Field | Type | Meaning |
|---|---|---|
| `reward` | dict | `{"coins": 50, "cash": 0, "xp": 15}` — the reward for helping |
| `rnd` | int | Randomness weight |
| `task` | str | The prompt text, e.g. `"Help! Some trolls are attacking my villagers!"` |
| `action` | str | Button label, e.g. `"Click OKAY to eliminate the trolls"` |
| `notification` | str | Toast text, e.g. `"helped to eliminate the trolls"` |

### 8.8 `town_prices` (4) and `map_prices` (4)

Identical shape and identical values in `main.json`:

| Field | Type | Values |
|---|---|---|
| `coins` | int | 100 000 / 300 000 / 550 000 / 1 000 000 |
| `cash` | int | 20 (all four) |
| `level` | int | 15 / 25 / 35 / 45 |

### 8.9 `findable_items` (10)

| Field | Type | Meaning |
|---|---|---|
| `id` | int | 1–10 |
| `title` | str | e.g. `"Clown"`, `"Little Boy"`, `"Little Girl"` |
| `description` | str | "You've found a sad Clown on your park. Share it with your friends…" |
| `coins` | int | 100 (share reward) |

### 8.10 `offer_packs` (44)

| Field | Type | Meaning |
|---|---|---|
| `id` | int | 1–44 |
| `cost_cash` | int | Cash price (20–60) |
| `gold`,`wood`,`steel`,`oil`,`xp` | int | Resource grant (only pack 1 grants resources) |
| `items` | list or null | Either a flat list of item ids (e.g. `[1042, 84]`) **or** a list of 3 **sub-lists** (mystery boxes: 3 candidate items per row). `null` for the premium pack. |
| `enabled` | int | `0`/`"1"` — shown in the store |
| `position` | int | Sort position (0 = hidden) |
| `mana` | int | Mana grant (0) |
| `type` | str | `""`, `"premium_account"`, `"super"` |
| `name` | str | e.g. `"starter pack"`, `"Mistery Box 2"`, `"New Mistery Box 44"`, `"Premium Account"` |

> **Bug in shipped data:** offer packs 35 and 37–43 contain a malformed item id `"1072.1224"` (a decimal instead of an int) — e.g. pack 35 row 3 = `[1072.1224, 1071, 1031, 1033, 1059]`. The server's `buy_offer_pack` does `add_store_item(map, item)` → `str(item)` → the key becomes `"1072.1224"`. Harmless but worth knowing.

### 8.11 `social_items` (26)

| Field | Type | Meaning |
|---|---|---|
| `id` | int | Building id the workers belong to: `3, 9, 12, 16, 28, 37, 44, 54, 61, 64, 74, 75, 140` and the `3xxx` variants (`3003, 3009, 3012, 3016, 3028, 3037, 3044, 3054, 3061, 3064, 3074, 3075, 3140`) — 13 + 13 |
| `worker_cost` | int | Cash cost to hire one worker (1–3) |
| `workers` | str | Comma-separated worker titles, e.g. `"Oil QA Supervisor, Chemical"`, `"Mechanic,Mechanic"` |
| `description` | str | `""` in all shipped entries |

### 8.12 `images` (607)

`dict<path, language>`. Keys are asset paths relative to the static root, e.g. `/chapters/chapter_1.jpg`, `/chapters/chapter_10_m.jpg`, `tech_stealth_instinct.jpg`, `WIN_MEN.jpg`, `WIN_WOMEN.jpg`. **All 607 values are `"en"`** — the config ships only English.

### 8.13 `sounds` (139)

| Field | Type | Meaning |
|---|---|---|
| `id` | str `"1"`–`"139"` | Sound id |
| `file` | str | Base file name, e.g. `"explo1"`, `"139_hit"` |
| `max` | str | Max simultaneous plays (`"5"`) |
| `loops` | str | `"0"`/`"1"` |
| `preload` | str | `"0"`/`"1"` |
| `description` | str | e.g. `"hammer sound"`, `"Test"` |

### 8.14 `level_ranking_reward` (50)

| Field | Type | Meaning |
|---|---|---|
| `level` | int | **1–50, one entry per level** |
| `cash` | int | Cash prize (1) |
| `units` | dict\<str→int\> | e.g. `{"1016": 1}` — leaderboard unit reward |

### 8.15 `darts_items` (30 in `main.json`, 27 after the `targets` patch)

| Field | Type | Meaning |
|---|---|---|
| `id` | int | 1–30 (1–27 after patch) |
| `start_date` | str | `"%Y-%m-%d %H:%M:%S"` — when this week's minigame becomes available (recomputed by `make_dynamic`) |
| `items` | list\<int\> | 6 minor-prize unit ids, e.g. `[1061, 1073, 1071, 1031, 1058, 1045]` |
| `extra_item` | int | The major/jackpot prize unit id, e.g. `1152` |

### 8.16 `units_collections_categories` (20) — dict keyed by id string

| Field | Type | Meaning |
|---|---|---|
| `category_id` | int | Same as the key |
| `units` | list\<int\> | 3–5 unit ids in the category |
| `rewards` | int | 0 in all shipped entries |
| `cost` | int | `1` for category 1, `200` for the rest (cash) |
| `costs` | list or null | Per-unit cash cost, e.g. `[1, 1, 2, 2, 2]`; `null` for category 1 |
| `position` | int | Sort order (10–200) |
| `category_name` | str | English name |
| `category_name_es` / `_br` / `_it` / `_fr` / `_de` / `_tr` | str | Localised names (mostly identical to English) |
| `category_name_el` | str | Greek name — `""` for all shipped entries |

The 20 categories: `1 Earth Soldiers`, `2 Earth Bazookas I`, `3 Machine Gun Jeeps`, `4 Earth Tanks`, `5 Earth Tanks II`, `6 Earth Special Vehicles`, `7 Earth Aircrafts`, `10 Earth Helicopters`, `11 Earth Helicopters II`, `12 Special Units I`, `13 Special Units II`, `14 Special Units III`, `16 Special Units IV`, `17 Mechs & Bots I`, `21 Drones I`, `22 Drones II`, `23 Dragons`, `24 Draggies`, `34 Aliens & Spiders`, `35 Nebular Civ I`. (Ids 8, 9, 15, 18–20, 25–33 are absent.)

### 8.17 `magics` (10)

| Field | Type | Meaning |
|---|---|---|
| `id` | int | 1–10 |
| `name` | str | `"AirStrike"`, `"Medic Case Rain"`, `"Protection Shield"`, `"Nuclear Bomb"`, `"Shortcircuit Inductor"`, `"Magnetic Trap"`, `"Mech Summoner"`, `"Stealth Sneak"`, `"Alien Abduction"`, `"Attack Boost"` |
| `description` | str | Flavour text |
| `mana` | int | Mana cost (8–20) |
| `area` | str | JSON list, e.g. `"[5,7,9]"` or `"[25,30,35]"` |
| `level` | int | Minimum level (35–55) |
| `gold` | int | Gold cost (10 000–100 000) |
| `cash` | int | Cash cost (30–120) |
| `img_name` | str | e.g. `"tech_airstrike"` |
| `target` | int | 0 = self, 1 = friendly area, 2 = enemy area |

### 8.18 `globals` (104) — **complete key/value table**

Values are reproduced exactly as stored (JSON text). Runtime count is **105** because the `atom_fusion_powerup` patch adds `SOUL_MIXER_POWERUPS_LEVELS`.

| # | Key | Value | Type |
|---|---|---|---|
| 1 | `CONSTRUCTING_TIME` | `1000` | int |
| 2 | `ENERGY_INCREASE_ENERGY_INTERVAL` | `300000` | int |
| 3 | `ENERGY_MAX_REGULAR_VALUE` | `30` | int |
| 4 | `ENERGY_CONSTRUCTION_COST` | `1` | int |
| 5 | `ENERGY_COSTS` | `{"10": 10, "20": 20, "30": 30, "40": 40}` | dict |
| 6 | `BASE_RESOURCE_LIMITS` | `{"g": 20000, "o": 20000, "s": 20000, "w": 20000}` | dict |
| 7 | `NUM_ACTIVE_MISSIONS` | `5` | int |
| 8 | `COLLECT_MINUTES` | `[5, 60, 240, 480]` | list |
| 9 | `COLLECT_MULTIPLIER` | `[0.25, 1, 2, 3]` | list |
| 10 | `ENERGY_ASSIST_QTY` | `1` | int |
| 11 | `COST_HURRY_UP` | `2` | int |
| 12 | `HEALTH_SPY_EAGLES` | `[200, 400, 800, 10000]` | list |
| 13 | `PRIZE_COLLECTIONS_CASH` | `[0, 5, 5, 5, 5, 5, 5, 5, 5, 5, 15, 5, 5, 5, 5, 5, 5, 5, 5, 5, 20]` | list |
| 14 | `MARKET_BASE_COSTS` | `{"o": 100, "s": 150, "w": 100}` | dict |
| 15 | `MARKET_MAX_NUM_TRADES` | `20` | int |
| 16 | `MARKET_INCREMENT` | `0.02` | float |
| 17 | `MARKET_MAX_INCREMENTS` | `200` | int |
| 18 | `MARKET_MAX_DECREMENTS` | `25` | int |
| 19 | `MARKET_SELL_PERCENTAGE` | `0.75` | float |
| 20 | `MARKET_PERIOD_HOURS` | `20` | int |
| 21 | `MARKET_AMOUNT_TRADE` | `[100, 200, 300]` | list |
| 22 | `MIN_LEVEL_ATTACKS_1` | `10` | int |
| 23 | `MIN_LEVEL_ATTACKS_2` | `15` | int |
| 24 | `MIN_LEVEL_ATTACKS_3` | `20` | int |
| 25 | `MIN_LEVEL_ATTACK_SIEGE_1` | `25` | int |
| 26 | `MIN_LEVEL_ATTACK_SIEGE_2` | `30` | int |
| 27 | `MIN_LEVEL_ATTACK_SIEGE_3` | `35` | int |
| 28 | `MAX_MINES_STONE` | `1` | int |
| 29 | `MAX_MINES_GOLD` | `1` | int |
| 30 | `MAX_MINES_FOOD` | `1` | int |
| 31 | `MAX_MINES_WOOD` | `1` | int |
| 32 | `SPYINGS_MAX` | `3` | int |
| 33 | `SPYINGS_PERIOD_HOURS` | `24` | int |
| 34 | `MAX_SELECTED_OBJECTS` | `20` | int |
| 35 | `SPACE_SELECTED_ELEMENTS` | `50` | int |
| 36 | `SPACEY_SELECTED_ELEMENTS` | `50` | int |
| 37 | `LEFT_MARGIN_SELECTED_ELEMENTS` | `17` | int |
| 38 | `TOP_MARGIN_SELECTED_ELEMENTS` | `20` | int |
| 39 | `INCREMENT_HEALTH_REPAIR` | `10` | int |
| 40 | `TIMER_NEIGHBOUR` | `300000` | int |
| 41 | `TIMER_HARVEST` | `1000` | int |
| 42 | `TIMER_DEAD_DISAPPEAR` | `4000` | int |
| 43 | `TIMER_SPEECH_ACTIVE` | `3000` | int |
| 44 | `TIMER_OGRES_VILLAGE` | `14400` | int |
| 45 | `TIMER_REPOSITION` | `300` | int |
| 46 | `TIMER_REATACAR` | `300` | int |
| 47 | `DISTANCE_INTERACTION` | `1` | int |
| 48 | `AGGRO_RANGE` | `10` | int |
| 49 | `DISTANCIA_MINIMA_ARQUEROS` | `3` | int |
| 50 | `LIMIT_PER_LEVEL_TOWER` | `4` | int |
| 51 | `LIMIT_PER_LEVEL_SILO` | `0.2` | float |
| 52 | `START_MAX_POPULATION` | `20` | int |
| 53 | `SHOW_ADD_ENERGY_BUTTON_LIMIT` | `3` | int |
| 54 | `NEWS_IMAGE` | `"new_bestciv2_5,megabot_NEW,reptilegun_NEW,NEWS_QUESTS,NEWS_QUESTS19_20,NEWS_casa_subasta,news_laboratory,new_wonder,NEWS_ALLIANCE,new_premium2,NEWS_SHOTTING,4_NEW_QUEST,new_xp,NEWS_tanques_helicopteros5,NEWS_tanques_helicopteros4,NEWS_massive_damage,NEWS_NIDO_ROBOTS,NEWS_recruitmentcenter,NEWS_new_quest,NEWS_mr_t,NEWS_healer,NEWS_mecanico,news_aviones_2,NEWS_fortress,NEWS_wonders,031111_news_helicopters"` | str (CSV) |
| 55 | `NEWS_STORE` | `"12.121.0,12.121.0,12.121.0,,,1.17.0,1.17.0,7.0.0,,premium,,,,4.31.0,4.31.0,4.35.0,1.17.0,1.17.0,,12.121.0,4.34.0,4.34.0,4.0.0,3.23.0,7.0.0,4.33.0"` | str (CSV) |
| 56 | `PERMISSION_PACK_UNITS` | `[10, 20, 30, 40]` | list |
| 57 | `PERMISSION_COSTS` | `{"10": 10, "20": 20, "30": 30, "40": 40}` | dict |
| 58 | `LIMIT_PER_LEVEL_WALL` | `6` | int |
| 59 | `INITIAL_LIMIT_PER_WALL` | `80` | int |
| 60 | `INITIAL_PER_LEVEL_TOWER` | `20` | int |
| 61 | `ROUND_TABLE` | `[389]` | list |
| 62 | `RECRUITMENT_PRIZE` | `[140]` | list |
| 63 | `ALLIES_BUILDING` | `[61, 3061]` | list |
| 64 | `ALLIES_MARKET` | `[74, 3074]` | list |
| 65 | `ALLIES_MARKET_INCREMENTAL_COLLECT` | `{"w": 125, "s": 125, "o": 125, "g": 125}` | dict |
| 66 | `ALLIES_MARKET_INITIAL_COLLECT` | `{"w": 125, "s": 125, "o": 125, "g": 125}` | dict |
| 67 | `ALLIES_MARKET_TROLLS` | `352` | int |
| 68 | `MAX_POPULATION_PER_LEVEL` | `3` | int |
| 69 | `COLLECT_HELP_SECONDS` | `3600` | int |
| 70 | `DAILY_GOLD_REWARDS` | `[100, 250, 500, 1000, 0]` | list |
| 71 | `DEPOT_LIMITS` | `"{\"g\":[1, 7, 17,27],\"o\":[1, 8,18,28],\"w\":[1, 5,15,25],\"s\":[1, 6,16,26]};"` | str (JSON + trailing `;`) |
| 72 | `MANA_PER_PURCHASE` | `5` | int |
| 73 | `MANA_REWARD_PER_LEVEL` | `2` | int |
| 74 | `ISLE_ORDER` | `["100000006","100000007","100000008","100000002","100000012","100000021","100000022","100000003","100000028","100000014","100000013","100000020","100000015","100000019","100000018","100000023","100000011","100000033"]` | list\<str\> |
| 75 | `URL_APP_PROD` | `"http://apps.facebook.com/socialwarsgame/"` | str |
| 76 | `REACTIVATE_WONDER_DISCOUNT` | `0.5` | float |
| 77 | `MAX_POPULATION_CAP` | `175` | int |
| 78 | `REWARDS_CHAPTERS` | `[{}, {"g": 250, "w": 200}, {"g": 500, "o": 400}, {"g": 750, "s": 600}, {"g": 1000, "w": 800}, {"g": 1250, "o": 1000}, {"g": 1500, "s": 1200}, {"g": 1750, "w": 1400}, {"g": 2000, "o": 1600}, {"g": 2250, "o": 1800}, {"g": 2500, "s": 2000}, {"g": 2750, "o": 2200}, {"g": 3000, "s": 2400}]` | list (13) |
| 79 | `REWARDS_QUESTS` | `[{}, {"g": 1500, "w": 400}, …, {"g": 24000, "w": 4200}]` | list (23) |
| 80 | `LIMITED_EDITION_EXPIRATION` | `"2012-09-14"` | str (date) |
| 81 | `NEWFRIENDS_REWARD_ID_UNIT` | `"1046.1, 1055.1, 1048.1, 1050.2, 1051.1"` | str (CSV, `id.level`) |
| 82 | `NEWFRIENDS_REWARD_DESCRIPTION` | `"1180,1181,1182,1183,1184"` | str (CSV) |
| 83 | `NEWFRIENDS_REWARD_SCALE_UNIT` | `"1,1,.7,1,1"` | str (CSV) |
| 84 | `MAX_GOLD_STOLEN` | `20000` | int |
| 85 | `GOLD_STOLEN_TOP_PCT` | `35` | int |
| 86 | `GOLD_STOLEN_BOTTOM_PCT` | `15` | int |
| 87 | `MONDAY_BONUS_REWARDS` | `[{"type": "g", "value": 2500}, {"type": "u", "value": [1055, 1033, 1046, 1063, 1198]}, {"type": "c", "value": 5}]` | list (3) |
| 88 | `UNIT_XP_LEVELS_MULTIPLIERS` | `[[0,0,0,0],[5,2,20,50],[10,2,20,25],[20,3,20,12],[40,3,20,6],[65,4,20,4]]` | list\<list\<int\>\> |
| 89 | `ALLIANCE_DAILY_BONUS_REWARDS` | `[{"type": "g", "value": 150, "members": 0}, {"type": "g", "value": 1500, "members": 5}, {"type": "g", "value": 5000, "members": 25}, {"type": "c", "value": 1, "members": 45}]` | list |
| 90 | `BUILD_SPEEDUP_MIN_TIME` | `10` | int |
| 91 | `BUILD_SPEEDUP_PRICING` | `[5, 1]` | list |
| 92 | `UPGRADE_SPEEDUP_PRICING` | `[5, 1]` | list |
| 93 | `DART_COST_CASH` | `20` | int |
| 94 | `PREMIUM_ACCOUNTS` | `[{"time": 360, "price": 800}, {"time": 180, "price": 450}, {"time": 30, "price": 80}, {"time": 7, "price": 40}, {"time": 3, "price": 20}, {"time": 1, "price": 8}]` | list (6 packages: 360/180/30/7/3/1 days) |
| 95 | `UNIT_XP_LEVELS_MULTIPLIERS_10` | `[[0,0,0,0],[5,2,20,50],…,[200,4,25,1.5]]` | list\<list\<int\>\> (10) |
| 96 | `LEVEL_MAGIC` | `2` | int |
| 97 | `COST_MANA_CASH` | `1` | int |
| 98 | `COST_MANA_GOLD` | `10000` | int |
| 99 | `NUM_SPELL_USES_LVL2` | `25` | int |
| 100 | `NUM_SPELL_USES_LVL3` | `50` | int |
| 101 | `CASH_WONDER` | `176` | int |
| 102 | `QUESTS_MIN_LEVELS` | `{"100000021": 40, "100000022": 40, "100000025": 40, "100000026": 40}` | dict |
| 103 | `RESOURCE_PACKS` | 12 entries: `{"g":5000,"price":{"c":10},"img":"res_g_1"}` … `{"s":50000,"price":{"c":90},"img":"res_s_3"}` | list |
| 104 | `CROSS_ITEMS` | `{"SE": {"id": 10020, "img": "socialempires", "functionExternal": "socialempires", "gameName": "Social Empires", "position": 1}, "DC": {"id": 10078, "img": "dragoncity", "functionExternal": "dragoncity", "gameName": "Dragon City", "position": 2}}` | dict |
| **105** | `SOUL_MIXER_POWERUPS_LEVELS` | `[{"cash_cost": 1, "order_increment": 1}, {2,2}, {4,4}, {8,8}, {15,15}, {20,20}]` | list — **added by the `atom_fusion_powerup` patch, not present in `main.json`** |

Globals actually read by the Python code: `PREMIUM_ACCOUNTS` (`get_premium_days`), `MONDAY_BONUS_REWARDS` (`get_weekly_reward_length`). **The other 103 are dead data from the server's point of view** — they are consumed by the Flash client.

---

## 9. Build & packaging

### 9.1 `bundle.py` — the `sys._MEIPASS` layout

```python
TMP_BUNDLED_DIR = sys._MEIPASS if getattr(sys, 'frozen', None) else "."

ASSETS_DIR      = os.path.join(TMP_BUNDLED_DIR, "assets")
STUB_DIR        = os.path.join(TMP_BUNDLED_DIR, "stub")
TEMPLATES_DIR   = os.path.join(TMP_BUNDLED_DIR, "templates")
VILLAGES_DIR    = os.path.join(TMP_BUNDLED_DIR, "villages")
QUESTS_DIR      = os.path.join(VILLAGES_DIR, "quest")
CONFIG_DIR      = os.path.join(TMP_BUNDLED_DIR, "config")
CONFIG_PATCH_DIR= os.path.join(CONFIG_DIR, "patch")

BASE_DIR = "."
MODS_DIR     = os.path.join(BASE_DIR, "mods")
SAVES_DIR    = os.path.join(BASE_DIR, "saves")
AUCTIONS_DIR = os.path.join(BASE_DIR, "auctions")
```

* `sys._MEIPASS` is the directory PyInstaller extracts the bundled data into. For `--onefile` it is a **temporary directory created per run**; for `--onedir` it is the `_internal` folder next to the EXE.
* When not frozen, `TMP_BUNDLED_DIR = "."` — i.e. the **current working directory**, not the script directory. Running `python server.py` from anywhere other than the repo root breaks the data lookups.
* **Bundled** (read-only content): `assets/`, `stub/`, `templates/`, `villages/` (+ `villages/quest/`), `config/` (+ `config/patch/`).
* **Not bundled** (expected next to the EXE / CWD): `mods/`, `saves/`, `auctions/`. These are the *user-writable* parts. **They are resolved relative to the process CWD, not the EXE directory** — so double-clicking the EXE works (CWD = EXE dir) but launching it from a shortcut with a different "Start in" directory will silently create a new empty `saves/` next to wherever CWD points.
* `mods/` is read-only at runtime, but it is **not bundled**, so a packaged build has no `mods/` directory → `modify_game_config()` finds no `mods.txt` and applies no mods (which is the shipped default anyway). A user can drop a `mods/` folder next to the EXE to add mods.
* `config/patch/` **is** bundled, so patches are baked into the shipped config.
* `auctions/` is created on demand by `AuctionHouse.__init__` (`os.makedirs`), but the auction house is disabled, so it is never created.

### 9.2 `build/build.bat` — the Windows bundle build

```bat
set NAME=social-warriors_0.02a
pyinstaller ^
 --onedir ^
 --console ^
 --noupx ^
 --noconfirm ^
 --runtime-hook=".\path_bundle.py" ^
 --add-data "..\..\assets;assets" ^
 --add-data "..\..\config;config" ^
 --add-data "..\..\stub;stub" ^
 --add-data "..\..\templates;templates" ^
 --add-data "..\..\villages;villages" ^
 --paths ..\. ^
 --workpath .\work ^
 --distpath .\dist ^
 --specpath .\bundle ^
 --icon=..\icon.ico ^
 --name %NAME% ..\server.py
del /F /Q .\dist\%NAME%\%NAME%.exe.manifest
del /F /S /Q .\dist\%NAME%\certifi
rmdir .\dist\%NAME%\certifi
mkdir .\dist\%NAME%\bundle
echo [MANUAL] Move all files to the bundle folder (except game folders, base_library.zip and python3X.dll).
```

Pipeline:
1. PyInstaller `--onedir` build of `server.py` → `build/dist/social-warriors_0.02a/`.
2. `--add-data` copies `assets`, `config`, `stub`, `templates`, `villages` into the bundle (under `dist/social-warriors_0.02a/_internal/` for PyInstaller ≥ 6).
3. The EXE manifest and the `certifi` CA-bundle directory are deleted (the server makes **no** outbound HTTPS calls in the shipped build — the CDN branch is dead code).
4. A `bundle` subfolder is created next to the EXE.
5. **A manual step is required:** the user must move "all files to the bundle folder (except game folders, `base_library.zip` and `python3X.dll`)". This produces the *Bundle* release format (a single folder with the EXE + data) that `RELEASES.md` links to.

**Verified defect in the `--add-data` paths.** The script is meant to be run from the `build/` directory (`--paths ..\.` and `..\server.py` both point one level up, at the repo root, and are correct). But the `--add-data` source paths use `..\..\` (two levels up). From `<upstream-repo>\build`, `..\..\assets` resolves to `C:\Users\Edison\Desktop\assets` — **outside the repository and non-existent** (verified: `Test-Path ..\..\assets` → `False`; `Test-Path ..\assets` → `True`). The same applies to `..\..\config`, `..\..\stub`, `..\..\templates`, `..\..\villages`. The correct prefix is `..\`. This has been the case since the script was first committed (`0dcb5c5`, 2022-12-22) and was never fixed in `e27c81a` ("Cleaner bundle build"). **UNVERIFIED:** whether the author's original checkout layout had the data one level higher — but in the current repository the paths are wrong.

**`build/path_bundle.py`** (the `--runtime-hook`):
```python
import sys, os
sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), "bundle"))
```
It appends `<dir of the EXE>/bundle` to `sys.path`. Because `build.bat` also does `mkdir .\dist\%NAME%\bundle` and uses `--specpath .\bundle`, the `bundle` name is used for two different things (the PyInstaller spec directory and the runtime `sys.path` entry), and it collides with the application module `bundle.py`. Python resolves `import bundle` to `bundle.py` (a regular module beats a namespace-package directory across path entries), so it works — but it is fragile. *UNVERIFIED* whether the runtime hook has any effect at all in practice; the appended directory contains only the `.spec` file.

**`build/icon.ico`** (32 988 B) is the EXE icon; `build/icons/sw.ico` and `build/icons/sw_bg.ico` are byte-identical copies (32 988 B each) that are not referenced by either build script.

### 9.3 `build/launcher_build.bat` — the legacy one-file launcher

```bat
set NAME=social-warriors_0.02a
pyinstaller --onefile --console --add-data "..\..\assets;assets" ... --name %NAME% ..\server.py
```
Plus a commented-out `:clean` target that deletes `work`, `dist` and `bundle`.

* `--onefile` → a single EXE; the 716 MB of assets are extracted to a temp dir on every run.
* It does **not** use `--runtime-hook=path_bundle.py`.
* It has the **same `..\..\` path defect**.
* `RELEASES.md` shows the 0.01a release shipped both a `.exe` launcher (32-bit and 64-bit) **and** a bundle zip; the 0.02a release (2024-01-27) ships only the bundle zip. The launcher is effectively **deprecated** (commit `e27c81a` "Cleaner bundle build. Launcher build deprecated.").

### 9.4 What is bundled vs. kept next to the EXE — summary

| Path | Bundled into the EXE? | Notes |
|---|---|---|
| `assets/` (716.8 MB, 3 199 files) | **Yes** | `--add-data`; includes every `Basesec_*.swf` client build |
| `config/` (1.7 MB `main.json` + 5 patches + 3 captured responses) | **Yes** | `config/patch/` included → patches are baked in |
| `stub/crossdomain.xml` | **Yes** | |
| `templates/` (login.html, play.html, css, img, avatars) | **Yes** | |
| `villages/` (7 static + 23 quest + initial) | **Yes** | `villages/quest/` included |
| `mods/` | **No** | expected next to the EXE; optional |
| `saves/` | **No** | created on demand next to the EXE; per-player JSON |
| `auctions/` | **No** | created on demand; never created (auctions disabled) |
| `*.py` sources | Compiled into the EXE (`--paths ..\.`) | |

### 9.5 Runtime dependencies

`requirements.txt` (2 lines):
```
flask
jsonpatch
```
`server.py` also imports `requests` (used only by the dead CDN branch) and `urllib` (unused). `flask.debughelpers.attach_enctype_error_multidict` is imported but **never used**.

`requirements.txt` pins **no versions**. The analysis environment had `flask 2.2.5` and `jsonpatch 1.33`. `flask.debughelpers` was **removed in Flask 2.3**, so `server.py` will fail to import on Flask ≥ 2.3 — a hard, version-fragile dependency. (The import is unused, so the fix is trivial, but the pin is missing.)

---

## 10. The `tools/` scripts

`tools/` holds 5 files that are **developer tools, run by hand from the `tools/` directory** (they use relative paths like `../config/main.json`).

### 10.1 `tools/atom_fusion_builder.py` (2 960 B)

**Purpose:** generate `config/patch/atom_fusion_items_data.json` — the `breeding_order` + `sm_training_time` fields for the Atom Fusion (Soul Mixer) building.

**How it works:**
1. Loads `../config/main.json`.
2. Applies two prerequisite patches in order: `../config/patch/atom_fusion_item.json` then `../config/patch/unit_patch.json` (so the generated indexes match the runtime item array).
3. Loads `atom_fusion_excluded_units.json`.
4. `must_exclude(item)` skips an item if: `item["type"] != "u"` (not a unit), or `"chained" in item["name"].lower()`, or `item["group_type"] == "WORKER"`, or `item["id"] in exclude_list`.
5. For every remaining unit it computes `breeding_order` and `sm_training_time` and emits **two** jsonpatch `add` ops per item.

**The formula actually used** is `breeding_order_health`:
```python
def breeding_order_health(a, ar, ai, d, l, v):
    return min(int(l/20), 240)
sm_training_time = 2000 * breeding_order   # seconds
```
i.e. **breeding order = min(life/20, 240)** and **training time = 2000 s × order** (so 1 order ≈ 33.3 min; the maximum is 240 × 2000 = 480 000 s ≈ 5.6 days).

Three other formulas exist in the file but are **unused**:
* `breeding_order_simple(a, ar, ai, d, l, v)` = `int((10*a*ar)/(ai+1) + 10*d + l/100 + v)`
* `breeding_order_tier_based(...)` — 4 tiers by life (8000 / 2500 / 1600), clamped to `[1..74]`, `[75..149]`, `[150..219]`, `[220..2000]`
* `breeding_order_simple2(a, ar, ai, d, l, v)` = `int((10*a*ar)/(ai+1) + l/10 + v)` (prints debug output)

**Output format:** a jsonpatch array written to `../config/patch/atom_fusion_items_data.json`:
```json
[
{"op": "add", "path": "/items/382/breeding_order", "value": "7"},
{"op": "add", "path": "/items/382/sm_training_time", "value": "14000"},
…
]
```
**Measured:** 300 items patched, 600 ops, covering array indexes **382–898** (item ids `1002`…`1305`). Note the values are written as **strings**, matching the rest of the item schema.

### 10.2 `tools/make_sw_unit_patch.py` (2 547 B)

**Purpose:** generate `config/patch/unit_patch.json` — the 121 extra "Social Wars unit" items (ids 1307–1431) — from the CSV table + the item templates.

**How it works:**
1. Loads `unit_templates.json` (the `group_type` → base item template map).
2. Reads `sw_unit_patch.csv` (tab-separated, header-less).
3. For each row it splits on `\t` into 14 columns:
   `ITEM_ID, ITEM_ASSET, ITEM_NAME, ITEM_HEALTH, ITEM_ATTACK, ITEM_RANGE, ITEM_SPEED, ITEM_INTERVAL, ITEM_POPULATION, ITEM_SYRINGES, ITEM_XP, ITEM_COST, ITEM_GROUP, ITEM_PROPERTIES`
4. `trimquotes()` strips characters before the first `{` and after the last `}` (so the CSV's quoted JSON is cleaned).
5. Skips rows with an empty `ITEM_ASSET` (`"Failed - Asset missing"`) or an unknown `ITEM_GROUP` (`"Failed - Template {group} not found"`).
6. Deep-copies the template and overwrites: `id`, `img_name`, `name`, `life`, `attack`, `attack_range`, `velocity`, `attack_interval`, `population`, `syringes`, `xp`, `costs` (with `\\` removed), `properties` (with `\\` removed).
7. Emits a jsonpatch `add` op at `/items/-` per item.

**Outputs:**
* `../config/patch/unit_patch.json` — the jsonpatch array (**121 ops**, ids 1307–1431, ~150 KB).
* `unit_patch_storage.json` — a `{"<item_id>": 1}` map meant to be dropped into a save so the player owns all patched units. This file is **gitignored** (`.gitignore`: `tools/unit_patch_storage.json`) and is **not** shipped.

### 10.3 `tools/unit_templates.json` (5 475 B)

A dict of **`group_type` → full item template object** (all fields as strings, exactly the item schema):

| Key | Template id | Template name | Key stats |
|---|---|---|---|
| `ROBOT` | `1062` | `MegaBot` | atk 40, def 1, life 1600, range 7, interval 35, vel 5, pop 3, syringes 3, xp 80, `costs {"c": 6}`, `properties {"ft_armored":"1","bulldozable":"1","mechanic":"1","seeStealthUnits":"1","resurrectable":"1"}` |
| `AIR_VEHICLE` | `1168` | `Blue Steel Draggy` | atk 27, life 450, range 11, interval 30, pop 2, syringes 2, xp 30, `costs {"c": 4}`, `properties {"ft_flying":"1",…}` |
| `DRAGON` | `1167` | `Blue Steel Bahamut` | atk 48, life 1900, range 12, syringes 5, xp 80, `costs {"c": 10}`, `properties {"bulldozable":"1","mechanic":"1","seeStealthUnits":"1","resurrectable":"1"}` (no `ft_*` class!) |
| `HEALER` | `1050` | `Medic` | atk 8, life 110, range 1, interval 60, pop 1, syringes 1, xp 10, `costs {"g":250,"w":500}`, `properties {"ft_ground":"1","healer":"1","human":"1","seeStealthUnits":"1","resurrectable":"1"}`, `building_limit_same_id 5` |

The CSV's `ITEM_GROUP` column selects one of these four templates. **Any other group value is rejected.**

### 10.4 `tools/atom_fusion_excluded_units.json` (1 241 B)

A flat JSON array of **125** item-id strings that must not be breedable in the Atom Fusion. It contains every unit id in the `1307`–`1431` range (the new patch units) plus older specials:
`"923","933","1005","1009","1011","1012","1013","1017","1018","1019","1024","1032","1034","1035","1043","1049","1050","1051","1052","1053","1068","1103","1108","1118","1130","1131","1132","1140","1142","1176","1401"…,"1431","1384"`.
Note `"1402"` appears **twice** in the list (lines 32 and 110) — harmless for a membership test.

### 10.5 `tools/sw_unit_patch.csv` (24 503 B)

Tab-separated, **no header row**, **122 lines** (121 data rows + a trailing newline).

| Column | Name | Example (row 1) |
|---|---|---|
| 0 | `ITEM_ID` | `1307` |
| 1 | `ITEM_ASSET` | `1307_glaivestorm_mech` |
| 2 | `ITEM_NAME` | `Glaivestorm Mech` |
| 3 | `ITEM_HEALTH` | `3900` |
| 4 | `ITEM_ATTACK` | `86` |
| 5 | `ITEM_RANGE` | `10` |
| 6 | `ITEM_SPEED` | `6` |
| 7 | `ITEM_INTERVAL` | `35` |
| 8 | `ITEM_POPULATION` | `4` |
| 9 | `ITEM_SYRINGES` | `3` |
| 10 | `ITEM_XP` | `80` |
| 11 | `ITEM_COST` | `"{\"c\": 10}"` |
| 12 | `ITEM_GROUP` | `ROBOT` |
| 13 | `ITEM_PROPERTIES` | `"{\"ft_armored\":\"1\",\"bulldozable\":\"1\",\"mechanic\":\"1\",\"seeStealthUnits\":\"1\",\"resurrectable\":\"1\""` (note: the last row's closing brace is missing — `trimquotes` tolerates it) |

The 121 rows cover ids **1307–1431** (every id in the range, alternating Mech/Drone), i.e. 61 mechs and 60 drones.

### 10.6 Tool/data cross-references

* `atom_fusion_builder.py` depends on `atom_fusion_item.json` and `unit_patch.json` existing and on `atom_fusion_excluded_units.json`.
* `make_sw_unit_patch.py` depends on `unit_templates.json` and `sw_unit_patch.csv`; it **overwrites** `config/patch/unit_patch.json` and `atom_fusion_builder.py` then depends on that regenerated file.
* `config/patch/atom_fusion_items_data.json` is **generated** output — regenerating it after changing `unit_patch.json` changes the item indexes, so the two tools must be run in order: `make_sw_unit_patch.py` → `atom_fusion_builder.py`.
* `tools/` is not referenced by any runtime code and is not bundled into the EXE.

---

## 11. `auctions.py` + `config/auctionhouse.json` — the betting subsystem (disabled)

### 11.1 Current status

**Fully disabled.** In `server.py`:
```python
# print (" [+] Loading auction house data...")
# from auctions import AuctionHouse
# auction_house = AuctionHouse()
```
and all three `/bets/*.php` routes are commented out (`server.py:197-288`). `auctions.py` is therefore **never imported** at runtime and the class is never instantiated. `config/auctionhouse.json` is bundled but unused. `auctions/auctions.json` (the state file) is gitignored and never created.

The only surviving trace in the live data is `privateState.marketPlaceFirstTime` (set by the `first_time_marketplace` command) and `privateState.betWin` (always `[]`).

### 11.2 `config/auctionhouse.json` — the config model

```json
{ "auctions": [
  { "uuid": "1", "unit": 1167, "level": 1, "interval": 120, "price": 5000, "priceIncrement": 1000, "betPrice": 2 },
  { "uuid": "2", "unit": 1168, "level": 1, "interval": 60,  "price": 1000, "priceIncrement": 200,  "betPrice": 2 },
  { "uuid": "3", "unit": 1226, "level": 2, "interval": 120, "price": 8000, "priceIncrement": 1500, "betPrice": 2 }
]}
```

| Field | Type | Meaning |
|---|---|---|
| `uuid` | str | Stable auction identifier ("1", "2", "3") |
| `unit` | int | Item id being auctioned (1167 Blue Steel Bahamut, 1168 Blue Steel Draggy, 1226) |
| `level` | int | Unit level / tier |
| `interval` | int | **Minutes** the auction runs before expiring (60 or 120) |
| `price` | int | Starting price |
| `priceIncrement` | int | Minimum bid increment |
| `betPrice` | int | Cost of placing a bid |

### 11.3 `auctions.AuctionHouse` — the runtime state model

**Config**: `CONFIG_DIR/auctionhouse.json`.
**State**: `AUCTIONS_DIR/auctions.json` (= `./auctions/auctions.json`), created with `os.makedirs` on first run.

State document:
```json
{ "auctions": { "<uuid>": { …bid… } } }
```

Each bid:
| Field | Type | Meaning |
|---|---|---|
| `uuid` | str | Matches the config |
| `idUnit` | int | The unit id |
| `level` | int | Unit level |
| `beginDate` / `endDate` | int | Unix ts window (`endDate = beginDate + interval*60`) |
| `beginPrice` | int | Starting price (reset on expiry) |
| `currentPrice` | int | Current highest bid |
| `priceIncrement` | int | Minimum increment |
| `betPrice` | int | Cost of a bid |
| `round` | int | Auction round (always reset to 1; **multi-round logic is a TODO**) |
| `betUsers` | list\<obj\> | `{user_id, fb_name, bet, fb_picture}` — one entry per bet placed |
| `betUsersPrev` | list | Previous round's bettors (always reset to `[]`) |
| `bidders` | list\<obj\> | Mirror of `betUsers` |
| `prevRoundBidders` | list | Previous round's bidders (always reset to `[]`) |
| `userRounds` | list | Per-user round bookkeeping (always reset to `[]`) |

**Transient fields added by `_set_bet_flags()`** on the response copy (not persisted):
`isPrivate` (0), `isWinning` (1 if the requesting user is the last bettor), `won` (1), `finished` (`timestamp_now() >= endDate`), `betDetail` ([]), and `betWinner` (set only when `checkFinish` is truthy and the user is winning).

**Methods:**
| Method | Behaviour |
|---|---|
| `init_auctions()` | Called from `__init__`: removes auctions no longer in the config, then updates/creates all auctions, then writes state if anything changed. |
| `_remove_auctions()` | Deletes state entries whose uuid is not in the config (so config changes take effect). |
| `update_all_auctions(time_now, update=True)` | Iterates the config, updates each auction, optionally writes state. |
| `update_auction(auction, time_now)` | Creates the auction if absent, else updates it. |
| `_create_auction(uuid, auction, seconds, time_now)` | Builds the initial bid dict. |
| `_update_auction(bet, uuid, auction, seconds, time_now)` | If the unit changed → recreate. If `time_now > endDate` → **restart** the auction with a fresh window, preserving the *remaining* time: `count_expired = difference // seconds`, `remaining = difference % seconds`, `beginDate = time_now - remaining`, `endDate = beginDate + seconds`. There is a 60-second guard: if the auction expired less than 60 s ago and there were bettors, it is not restarted yet. |
| `_write_state()` | `json.dump(self.auction_state, f, indent="\t")`, swallowing all exceptions. |
| `_set_bet_flags(bet, user_id, checkFinish=0)` | Sets the response flags. |
| `set_bet(user_id, uuid, bet_amount, bet_round)` | Appends a `{user_id, fb_name: "Test", bet, fb_picture: ""}` to `betUsers` and `bidders`, and sets `currentPrice = bet_amount + priceIncrement`. **`bet_round` is ignored**, `fb_name` is hard-coded to `"Test"`, and **no cash is deducted**. |
| `get_auctions(user_id, level)` | Updates all auctions, then returns a deep copy of every bid with the flags set. **`level` is ignored** — the client-side level filter is not applied server-side. |
| `get_auction_detail(user_id, uuid, checkFinish)` | Returns one bid with flags, or `None`. |

**Intended HTTP contract** (from the commented-out routes):
* `POST /dynamic/menvswomen/srvsexwars/bets/get_bets_list.php` — `data` framed the same way as `command.php` (`if not data.startswith("{"): data = data[65:]`), JSON `{user_id, level}` → `{"result": "success", "data": {"bets": [...]}}`.
* `POST /dynamic/menvswomen/srvsexwars/bets/get_bet_detail.php` — JSON `{uuid, checkFinish?}` → `{"result": "success", "data": <bid>}`.
* `POST /dynamic/menvswomen/srvsexwars/bets/set_bet.php` — JSON `{uuid, bet, round}` → `{"result": "success", "data": {"betResult": "OK"}}`.

**Known gaps in the subsystem** (all marked TODO or hard-coded in the source): no cash accounting, no round logic, no `fb_name`/`fb_picture` from the real profile, no `level` filtering, `bet_users` never validated against the player's balance, and the `betUsers`/`bidders` duplication is redundant.

---

## 12. `version.py` — the save-migration chain

```python
version_name = "alpha 0.02"
version_code = "0.02a"
```

`migrate_loaded_save(save) -> bool` returns `True` if the save was modified (so the caller re-saves it).

### 12.1 The chain

| From | To | Trigger | Exact operations |
|---|---|---|---|
| *(none)* | `0.01a` | `"version" not in save or save["version"] is None` | `save["version"] = "0.01a"`; `_changed = True`; prints `" [!] Applied version to save"` |
| `0.01a` | `0.01a` | `save["version"] == "0.01a"` | **0.01a compatibility fixes** (below) |
| `0.01a` | `0.02a` | `save["version"] == "0.01a"` (the *same* condition) | `save["version"] = "0.02a"`; `_changed = True` |

Note the two `if save["version"] == "0.01a"` blocks both fire on the same pass, so a 0.01a save is fixed **and** upgraded in one call.

### 12.2 The exact 0.01a fixes

```python
if "inventoryItems" not in privateState:
    privateState["inventoryItems"] = None
if type(privateState["inventoryItems"]) != dict:
    _changed = True
    privateState["inventoryItems"] = {}
    print(" [!] Applied inventory fix")

if "deadHeroes" not in privateState:
    privateState["deadHeroes"] = None
if type(privateState["deadHeroes"]) != dict:
    _changed = True
    privateState["deadHeroes"] = {}
    print(" [!] Applied hospital fix")

if "magics" not in privateState:
    privateState["magics"] = None
if type(privateState["magics"]) != dict:
    _changed = True
    privateState["magics"] = {}
    print(" [!] Applied magics fix")

for map in maps:
    if "questTimes" not in map:
        map["questTimes"] = None
    if type(map["questTimes"]) != dict:
        _changed = True
        map["questTimes"] = {}
        print(" [!] Applied quest fix")
```

In words:
1. **`privateState.inventoryItems`** — ensure present and a dict; otherwise reset to `{}`. ("inventory fix")
2. **`privateState.deadHeroes`** — ensure present and a dict; otherwise reset to `{}`. ("hospital fix")
3. **`privateState.magics`** — ensure present and a dict; otherwise reset to `{}`. ("magics fix")
4. **every `maps[i].questTimes`** — ensure present and a dict; otherwise reset to `{}`. ("quest fix")

**Important detail:** the "not in" branch writes `None` and does **not** set `_changed = True`; the "wrong type" branch immediately after then converts that `None` to `{}` **and** sets `_changed = True`. So a missing key ends up as `{}` and the save *is* marked changed. The `None` assignment is effectively dead code.

**Data loss risk:** because the check is `type(x) != dict`, any *other* non-dict type is silently **destroyed** and replaced with `{}`. A save with `inventoryItems` as a list loses it. (This is exactly what the 0.01a → 0.02a upgrade had to do to old saves where these fields were `null`.)

### 12.3 Where migration is called

| Call site | Effect |
|---|---|
| `sessions.load_saves()` | After loading each save from `saves/`, `modified = migrate_loaded_save(save)`; if `modified`, `save_session(USERID)` writes the file back. **This is the only place that persists a migration.** |
| `sessions.new_village()` | Migrates the freshly built village (from `initial.json`, which has **no** `version` key → it is tagged `0.01a`, fixed, then upgraded to `0.02a`) and then saves it. |
| `sessions.load_quests()` | Migrates quest villages **in memory only** — quest files are never written back, so all 23 quest files keep `"version": "0.01a"` on disk. |
| `sessions.load_static_villages()` | **Does not migrate.** The static neighbours keep whatever version they have: `AcidCaos`/`Kiriakos`/`Nerri`/`Neutral`/`Scarlet` = `"0.02a"`, `General_Mike_30/31` = `null` (i.e. they are effectively "0.01a" but are never migrated because the loader doesn't call `migrate_loaded_save`). |

**`version_code` (`"0.02a"`) is imported by `sessions.py` but never used.** `version_name` is used only for display (`/health`, the login page, `play.html`).

### 12.4 The migration chain, visualised

```
save file on disk
   │
   ├─ "version" absent or null ──► set "0.01a"  (changed = True)
   │
   ▼
version == "0.01a"
   │  ├─ ensure privateState.inventoryItems is a dict  (else {})
   │  ├─ ensure privateState.deadHeroes    is a dict  (else {})
   │  ├─ ensure privateState.magics        is a dict  (else {})
   │  └─ ensure every maps[i].questTimes   is a dict  (else {})
   │
   ▼
version = "0.02a"  (changed = True)
   │
   ▼
save_session(USERID)  →  saves/<USERID>.save.json
```

**There is no migration path beyond 0.02a.** A save with `version == "0.02a"` is passed through unchanged. A save with an *unknown* version (e.g. `"0.03a"`) is also passed through unchanged — the code only special-cases `"0.01a"`.

---

## 13. Assessment for a cross-platform rewrite

### 13.1 What is portable as-is

| Asset | Portability | Notes |
|---|---|---|
| **`config/main.json`** | **100 % portable** | Pure data. 1.7 MB, 20 sections, self-describing. Directly usable by any language. The only transformation needed is the jsonpatch pipeline (below). |
| **`config/patch/*.json`** | **100 % portable** | RFC 6902 JSON Patch. Any language with a jsonpatch library can apply them. The 5 patches are pure data. |
| **`mods/*.json`** | **100 % portable** | Same format. |
| **`villages/*.json`** (7 static + 23 quest + initial) | **100 % portable** | Pure data + the documented schema in §5. The `__#__ITEMS_hint` key is a free schema annotation. |
| **`assets/`** (716.8 MB) | **100 % portable** | Binary assets + SWF clients. Platform-independent, but a Flash client is **not** — see §13.4. |
| **`config/get_game_config.php_*.txt`** | Archival only | Historical record of the original server. Not needed at runtime. |
| **The save-file schema** (§5) | **100 % portable** | The JSON structure is the de-facto data model and should be preserved verbatim, because existing `saves/*.save.json` files and the 30 shipped villages use it. |
| **The `command.php` wire protocol** | **Portable, but must be preserved exactly** | The 64-char-hash + `;` + JSON framing, the `commands[][]` shape and the `comm[3]` 8-slot resource vector are the **client contract**. A rewrite must accept the same framing or the Flash client will break. |
| **`make_dynamic()` darts wrapping** | **Portable, but the algorithm must be re-derived** | It is date/timezone-sensitive (`time.mktime`, `datetime.fromtimestamp`, `isoweekday`). A port to a language with a different DST model must reproduce the Monday-alignment nudge exactly, or the minigame rotation will drift. Best treated as "compute the next N Mondays from an anchor" rather than a literal port. |
| **The `constants.py` table** (1 072 constants) | **Data, not code** | Should become a generated table/JSON, not a hand-ported constant list. |
| **`tools/` scripts** | **100 % portable** | `atom_fusion_builder.py` and `make_sw_unit_patch.py` are pure data transforms; re-implement in any language. They are offline tools and can stay Python. |

### 13.2 What is *not* portable and must be rewritten

| Component | Why |
|---|---|
| **`sessions.py`'s global mutable state** | `__saves`, `__villages`, `__quests` are module-level dicts mutated in place by every request. There is no per-player isolation, no locking, and no transaction boundary. `load_saves()` **replaces `__saves` entirely** (`__saves = {}`) — it is called on every `GET/POST /` (the login page), so any in-flight mutation of a save is silently lost. In a threaded WSGI server (`app.run(threaded=True)`) two concurrent `command.php` calls for the same player can interleave read-modify-write on the same dict and corrupt the save. **This is a data-corruption bug, not just a style issue.** |
| **`sessions.session()` returning `None`** | The function's contract is "return the save dict, or `None` if unknown", but **every** caller immediately indexes it. There is no `KeyError`, no 404, no typed error. Result: unknown USERID → HTTP 500 with a Python traceback in the log. |
| **`session()` name collision** | `sessions.session(USERID)` (a save lookup) vs `flask.session` (the cookie jar) are different things with the same name. `sessions.py` even does `from flask import session` at the top and then defines `def session(USERID)` — the local definition shadows the import, so the Flask import is dead. Confusing and a trap for a rewrite. |
| **Filesystem JSON persistence** | One file per player, whole-document rewrite on every command batch, `json.dump(..., indent=4)`, no `fsync`, no atomic rename (a crash mid-write truncates the file), no file locking, no backup. `backup_session()` is a **`TODO` stub that does nothing**. `save_session()` also prints to stdout on every save. |
| **No database** | There is no schema, no indexes, no querying. All "queries" are full-document JSON loads. For a multiplayer rewrite this is the single biggest structural change. |
| **No concurrency control** | No optimistic locking (no save revision/hash), no per-player mutex, no transaction. Two clients on the same account (or the same client with a stale tab) will last-write-win. |
| **Missing authentication** | `user_key` is read and ignored. `accessToken` is read and ignored. The `USERID` in the request body is trusted absolutely. `play.html` ships a hard-coded fake `accessToken` and `user_key=123456789`. **Any HTTP client can read or mutate any player's save.** For a public/internet-facing rewrite this is the #1 must-fix. |
| **`assert` used for control flow** | `assert data_str[64] == ';'` (framing), `assert file.split(".")[0] == QUESTID` (quest filename), `assert USERID not in all_userid()` (new village), `assert isinstance(USERID, str)` (accessors). All of these **disappear under `python -O`** and all of them produce a bare 500 with a traceback instead of a 4xx. |
| **Flask `session` usage for the page routes** | The cookie session holds `USERID` and `GAMEVERSION` and is used to gate `/play.html`. It is entirely decoupled from the dynamic endpoints, which is why the dynamic endpoints are unauthenticated. A rewrite should have **one** auth mechanism. |
| **`print()` logging** | ~60 `print()` calls across the codebase, all to stdout, mixed with actual user-facing output (`" [+] Loading basics..."`). No levels, no timestamps (except Flask's own access log), no file/structured output, no request correlation, and the whole per-command log (`print(" [+] COMMAND: ", cmd, "(", args, ") -> ", ...)`) is unbounded and unredacted. In a server context this is a performance and privacy problem. |
| **Flask-version fragility** | `from flask.debughelpers import attach_enctype_error_multidict` — removed in Flask 2.3. `requirements.txt` pins nothing. A rewrite must not depend on a private Flask API. |
| **`app.secret_key` set only under `__main__`** | Any WSGI import breaks session handling. |
| **`os.system("color")` / `os.system("title ...")`** | Windows-only console tweaks at import time; they spawn a shell. |
| **`os.path` / CWD-relative paths** | `BASE_DIR = "."` means the data root is the *process CWD*, not the executable directory. A rewrite should anchor paths to the executable or an explicit data dir. |
| **Duplicate `constants.py` values** | `SUBCATFUNC_UNIT_MOUNTED == SUBCATFUNC_UNIT_MOTORIZED == 79`; `Quests.QUEST` has 4 duplicate keys. Port the *effective* values, not the source text. |
| **The `templates/play.html` Flash embed** | The whole UI is a `<object><embed>` SWF. A "cross-platform client-server application" needs a **new client**; the server contract must therefore stay bit-compatible with the Flash client *or* the Flash client must be re-implemented against a new protocol. This is the single largest decision in the rewrite. |

### 13.3 Concrete risk register for the rewrite

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **No authentication** — any client can act as any player. | **Critical** | Introduce real auth (signed session token bound to `USERID`); validate `user_key`/`accessToken`; bind the `USERID` in the request to the authenticated session. |
| R2 | **Unbounded resource grants** via `comm[3]` — verified 1e9 gold. | **Critical** | Server-authoritative economy: recompute resource deltas from the command semantics; reject or clamp client deltas; add upper bounds. |
| R3 | **Save-file corruption** — non-atomic full-document rewrite, no locking. | **Critical** | Move to a transactional store (SQLite with WAL, or Postgres) or at minimum write-temp + `os.replace` + per-player lock + keep a revision counter. |
| R4 | **`load_saves()` wipes `__saves`** on every login-page hit. | High | Never reload-from-disk over live state; use a store with proper caching/invalidation. |
| R5 | **Concurrent `command.php` on the same player corrupts the save** (threaded Flask). | High | Per-player serialisation (async queue / row lock). |
| R6 | **Client can place/move items anywhere, set any level, grant any unit.** | High | Validate item ids against the config, validate coordinates against the map grid, validate level/XP against the level table, and re-derive rewards server-side. |
| R7 | **`end_attack` never touches the victim's save** — PvP is entirely client-authoritative. | High | Implement a real battle resolution on the server. This is the biggest *missing feature*, not just a bug. |
| R8 | **No request/response schema** — `data["first_number"]` etc. raise `KeyError` → 500. | Medium | Explicit request parsing with typed errors → 400/422 instead of 500. |
| R9 | **Darts `make_dynamic` timezone/DST drift** across ports. | Medium | Re-implement as an explicit "next Monday 00:00 local" schedule, and add a regression test with a frozen clock. |
| R10 | **The 64-char hash is not validated** — a rewrite that *does* validate it will break clients that compute it differently. | Medium | Decide explicitly: keep the framing byte-compatible and ignore the hash (as today), or implement the real HMAC on both sides. |
| R11 | **Config pipeline ordering is load-bearing** — `atom_fusion_items_data` uses **array indexes** (`/items/382`), so it silently corrupts if `unit_patch` or `atom_fusion_item` change size/order. | Medium | Move the patch targets to stable JSON pointers (e.g. `/items/by-id/1307`) or a keyed map. |
| R12 | **`remove_duplicate_items()` is O(n²) and string-based.** | Low | Use a keyed map / id index; compare numerically. |
| R13 | **`print()` logging** — unbounded, unlevelled, no timestamps. | Low | Structured logging with levels; redact the per-command arg dump or make it debug-only. |
| R14 | **Flask private API + unpinned deps.** | Low | Pin versions or drop the dependency entirely. |
| R15 | **Data-anchored paths (`BASE_DIR = "."`)** — the packaged app breaks if launched with a different CWD. | Low | Anchor to the executable / explicit `--data-dir`. |
| R16 | **`build.bat` `--add-data` paths are wrong** (`..\..\` instead of `..\`) — the build has been broken since 2022. | Low | Fix and add a CI check that the built EXE actually starts. |
| R17 | **`assets/` is 716.8 MB** and is copied into every build. | Low (build time / size) | Split the bundle; serve assets from a CDN or a separate download. |
| R18 | **All 30 shipped villages carry `version` values that are only partially migrated** (quest files stay `0.01a`; General Mike files stay `null`). | Low | Run a one-off migration over the whole content set and commit the result. |
| R19 | **`get_game_config()` mutates and returns a shared global dict** — a caller could mutate the config for everyone. | Low | Return a deep copy or an immutable view. |
| R20 | **The `data` framing assertion is compiled out under `python -O`** and the whole thing 500s instead of 400. | Low | Replace `assert` with an explicit `raise BadRequest`. |

### 13.4 The Flash client question (out of scope but load-bearing)

The server's *entire* contract is shaped around the Flash client:
* the `64-hash;JSON` framing mirrors the original Zynga API;
* the `flashvars` in `play.html` inject `fb_sig_user`, `user_key`, `accessToken`, `language`, `friendsInfo`, `serverTime`, `lastLoggedIn`, `dailyBonus` — a mix of real and fake values;
* `assets/flash/` contains ~100 `Basesec_*.swf` client builds, i.e. the *client* is also preserved content.

A cross-platform rewrite therefore has two coherent options, and the decision must be made **before** any server work:

* **Option A — server-compatible rewrite.** Keep the exact HTTP contract (§2) and the exact save schema (§5); replace the Flask/global-state/filesystem implementation with a proper client-server stack (a real DB, real auth, server-authoritative economy). The existing Flash client and all 30 shipped villages keep working. **This is the lower-risk option** and preserves the preservation project's stated goal.
* **Option B — new client + new protocol.** Design a modern protocol (WebSocket, binary or compact JSON, server-authoritative simulation) and write a new cross-platform client. The Flash client becomes archival. This frees the design but means re-implementing the *simulation* (battle resolution, market, quests, collections, research, darts) rather than the current thin command-translation layer — which is by far the larger job, because the current server implements almost no game rules.

The middle ground (a new client that still speaks the legacy HTTP protocol) is attractive: it reuses Option A's server work and only requires a Flash-protocol client library.

---

## Appendix A — File inventory (relevant to this report)

| Path | Size | Role |
|---|---|---|
| `server.py` | 11 631 B | Flask app, 13 live routes, CLI args (`--host/--ip`, `--port`, `--public-url`) |
| `command.py` | 31 193 B | 63 command handlers + the `command()` batch driver |
| `engine.py` | 9 000 B | Map/item primitives + `apply_resources` + `reset_stuff` |
| `sessions.py` | 8 261 B | Global save/village/quest stores + persistence |
| `get_game_config.py` | 10 726 B | Config load, patches, mods, dedup, `make_dynamic`, accessors |
| `get_player_info.py` | 1 478 B | `get_player_info` / `get_neighbor_info` |
| `constants.py` | 38 423 B | `Quests.QUEST` (28 effective entries) + `Constant` (1 072 constants) |
| `auctions.py` | 7 835 B | `AuctionHouse` (disabled) |
| `version.py` | 1 698 B | `version_name`/`version_code` + `migrate_loaded_save` |
| `bundle.py` | 773 B | `sys._MEIPASS` path resolution |
| `config/main.json` | 1 702 871 B | Canonical config (== 29-Aug-2012 capture) |
| `config/patch/patches.txt` + 5 × `.json` | 271 B + ~196 KB | jsonpatch pipeline |
| `mods/mods.txt` + `no_hiring_needed.json` | 429 B + 4 819 B | Optional mods (disabled by default) |
| `config/auctionhouse.json` | 467 B | 3 auction definitions |
| `config/get_game_config.php_*.txt/.json` | ~2.8 MB | Original server captures (23 Jul + 29 Aug 2012) |
| `villages/initial.json` | 8 080 B | New-player template (40 items) |
| `villages/{AcidCaos,General_Mike_30,General_Mike_31,Kiriakos,Nerri,Neutral,Scarlet}.json` | 92–184 KB each | 7 static neighbours |
| `villages/quest/*.json` | 23 files, 8.6–214 KB | 23 quest villages |
| `tools/atom_fusion_builder.py` | 2 960 B | Generates `atom_fusion_items_data.json` |
| `tools/make_sw_unit_patch.py` | 2 547 B | Generates `unit_patch.json` + `unit_patch_storage.json` |
| `tools/unit_templates.json` | 5 475 B | 4 item templates (ROBOT / AIR_VEHICLE / DRAGON / HEALER) |
| `tools/atom_fusion_excluded_units.json` | 1 241 B | 125 excluded ids |
| `tools/sw_unit_patch.csv` | 24 503 B | 121 tab-separated unit rows (ids 1307–1431) |
| `build/build.bat`, `build/launcher_build.bat`, `build/path_bundle.py`, `build/icon.ico` | 906 / 924 / 94 / 32 988 B | PyInstaller packaging |
| `stub/crossdomain.xml` | 224 B | Flash cross-domain policy (`allow-access-from domain="*"`) |
| `templates/login.html`, `templates/play.html` | 3 658 / 7 003 B | Login page + SWF embed page |
| `requirements.txt` | 16 B | `flask`, `jsonpatch` (unpinned) |

## Appendix B — Reproduction commands

```powershell
# Start the server
cd <upstream-repo>
python server.py --port 5099

# Health
curl http://127.0.0.1:5099/health

# Config (1.09 MB, 900 items, 105 globals)
curl "http://127.0.0.1:5099/dynamic/menvswomen/srvsexwars/get_game_config.php?USERID=x&user_key=y&language=en"

# Command: framing check (must be <64 chars> + ';' + json)
$json = '{"first_number":1,"publishActions":true,"ts":0,"tries":0,"accessToken":"x","commands":[[0,"ping",[],[0,0,0,0,0,0,0,0]]]}'
$h = [System.BitConverter]::ToString((New-Object Security.Cryptography.SHA256Managed).ComputeHash([Text.Encoding]::UTF8.GetBytes($json))).Replace('-','').ToLower()
curl -X POST -d "USERID=<uuid>&user_key=y&language=en&data=$h%3B$json" http://127.0.0.1:5099/dynamic/menvswomen/srvsexwars/command.php
```
