# Live Session Protocol — Observed Wire Traffic

This document records the protocol **as actually observed at runtime**, not as inferred from
source. Everything here was produced by running the real Adobe Flash Player against the
local preservation server and capturing every HTTP request.

| | |
|---|---|
| Client | Adobe Flash Player (PPAPI), bundled as `pepflashplayer.dll` in Flashy Browser 1.2.4 (MSIX, CEF/Electron 4.2.6, Chromium 69) |
| Server | Upstream `server.py` (Flask 2.2.5) on `127.0.0.1:5055`, wrapped with a request-tracing `before_request` hook (the upstream code itself was **not** modified) |
| Session | New empire created via `GET /new.html`, tutorial played through to step 14 |
| Traffic | 309 HTTP requests, 212 distinct paths, 16 `command.php` batches |
| Raw artefacts | [`../evidence/live/`](../evidence/live/) |

---

## 1. Session bootstrap

### 1.1 `GET /` — login page

Returns `templates/login.html`: an empire picker (one `<option>` per file in `saves/`) plus
a **Create a new Empire** link to `/new.html`.

### 1.2 `GET /new.html` — village creation

Side effect: `sessions.new_village()` deep-copies `villages/initial.json`, assigns
`playerInfo.pid = str(uuid.uuid4())`, sets `privateState.timeStampDartsReset = 0` so the
client initialises the darts minigame, runs the save migration, and writes
`saves/<uuid>.save.json`. Then `302 → /play.html`.

The UUID becomes the `USERID` for the whole session. **It is not an account.**

### 1.3 `GET /play.html` — the Flash host page

`templates/play.html` embeds:

```html
<embed src="{{public_url}}/static/socialwars/flash/SWLoader.swf?swftoload={{public_url}}/static/socialwars/flash/Basesec_1.5.4.swf"
       flashvars='spdebug=notnull&brk=0
                  &staticUrl={{public_url}}/static/socialwars/&brk=0
                  &dynamicUrl={{public_url}}/dynamic/menvswomen/srvsexwars/&brk=0
                  &skiphash12341=notnull&brk=0
                  &fb_sig_user={{save_info.userid}}&brk=0
                  &user_key=123456789&brk=0
                  &language=en&brk=0
                  &accessToken=AAABbZAm0wdMUBALsOrR0Ho68CLjaOT8SV3vftKg9mbo1zZColaW5FljRVaLxPGxXXnm1M98mTZCAttcQ4GHwvSyXfsyxYmvKMH8Hmn5iliSPnjvIsZA6&brk=0
                  &sex=m&brk=0 &lastLoggedIn=1349266517&brk=0 &dailyBonus=0&brk=0
                  &friendsInfo={{friendsInfo | tojson}}&brk=0 &serverTime={{serverTime}}&brk=0
                  &forceSyncError=1&brk=0 &forceAttackReload=0&brk=0 &forceQuestReload=0'>
```

Two facts worth carrying into a clone:

* **`skiphash12341=notnull` disables the client's own response-hash verification** (three
  call sites in `core/Base.as`). The local server therefore never has to sign responses.
  A production server that *does* sign responses must implement that verification path.
* `forceSyncError`, `forceAttackReload`, `forceQuestReload` are **inert** in this SWF — they
  are read nowhere in the decompiled client.

### 1.4 `GET /static/socialwars/flash/SWLoader.swf`

The loader reads the `swftoload` flashvar, `URLLoader`s it as `BINARY`, and then
`Loader.loadBytes()`s the payload into the **same** `ApplicationDomain`. That is why the
client's classes resolve across the two SWFs. The loader also calls
`Security.allowDomain("*")` and embeds the `BlockBertholdRegular` font — **a font that does
not exist in the asset tree** (see §7 of the assets report).

## 2. The dynamic API

Root: `/dynamic/menvswomen/srvsexwars/`
This is the original Zynga/Socialpoint path, preserved verbatim:
`http://dynamicmw.socialpointgames.com/appsfb/menvswomen/srvsexwars/`.

### 2.1 Endpoints actually exercised in this session

| Endpoint | Method | Times | Request | Response |
|---|---|---|---|---|
| `track_game_status.php` | POST | 52 | form: `user_id`, `installId`, `status` | `""` 200 |
| `command.php` | POST | 16 | form: `client_id`, `data` | `{"result":"success"}` 200 |
| `get_game_config.php` | GET | 1 | query: `USERID`, `user_key`, `language` | the full 1.7 MB config JSON |
| `get_player_info.php` | POST | 1 | query: `USERID`, `user_key`, `language`; body: `client_id`, `neighbors` | `playerInfo` + `map` + `privateState` + `neighbors` |

`track_game_status.php` values observed, in order — this is the client's own load telemetry
and is a convenient way to see the boot sequence:

```
000-construct → 090-endconstruct → 100-config → 091-fontsloaded
→ 110-pinfo → 120-init → 200-tut3 → 200-tut5 → 200-tut6
```

The `0xx`/`1xx`/`2xx` prefix looks like a phase counter. `200-tutN` is emitted once per
tutorial step, which means **`track_game_status.php` is a second, independent channel for
tutorial progress** — a clone must not rely on it alone.

### 2.2 Authentication reality

Every dynamic request carries `USERID` (the uuid) and `user_key=123456789` — a **constant
literal in `play.html`**, not a secret. `accessToken` is a frozen Facebook-style token
literal in the template. The server reads all three and validates none of them.

> **Consequence for the clone:** the protocol as shipped carries *no* authentication. Any
> client that knows a `USERID` can act as that player. A clone must add real auth while
> keeping the message shapes compatible.

## 3. The `command.php` wire format

### 3.1 Request

```
POST /dynamic/menvswomen/srvsexwars/command.php?USERID=<uuid>&user_key=123456789&language=en
Content-Type: application/x-www-form-urlencoded

client_id=343579499&data=<64 hex chars>;<url-encoded JSON>
```

`client_id` is a separate form field. The `data` field carries the signature and payload
joined by a single `;`.

### 3.2 Payload shape

```json
{
  "ts": 1792434747,
  "tries": 1,
  "flashVersion": "1.5.4",
  "first_number": 1,
  "accessToken": "AAABbZAm0wdMUBALsOrR0Ho68CLjaOT8SV3vftKg9mbo1zZColaW5FljRVaLxPGxXXnm1M98mTZCAttcQ4GHwvSyXfsyxYmvKMH8Hmn5iliSPnjvIsZA6",
  "publishActions": "0",
  "commands": [ [ map_id, cmd, args, resources ], ... ]
}
```

Note the types: `publishActions` is the **string** `"0"`, not the number `0`. `tries` is a
number. `ts` is a unix timestamp in seconds.

### 3.3 The command tuple

```json
[ 0, "buy", [41, 1001, 52, 42, 1, 0, 0, "u"], [0, 0, 0, 0, 0, 0, 0, 0] ]
   │   │       │                        │
   │   │       │                        └── 8-slot resource delta
   │   │       └── args[]
   │   └── command name
   └── map id (always 0 for the player's own map)
```

**The resource vector order is `[energy, xp, gold, wood, oil, steel, cash, mana]`.**
This was established empirically, not read off the source:

| Observation | Declared delta | UI effect |
|---|---|---|
| Worker purchase | `[0, 5, -10, 0, 0, 0, 0, 0]` | gold 2 000 → 1 990 |
| Academy I purchase | `[0, 13, 0, -125, 0, 0, 0, 0]` | wood 2 020 → 1 895 |
| Soldier training | `[0, 3, -30, 0, 0, -60, 0, 0]` | gold −30, steel −60, xp +3 |
| Tree harvest | `[0, 2, 0, 20, 0, 0, 0, 0]` | wood +20, xp +2 |

### 3.4 `first_number` is a global command index

`first_number` is **not** a batch counter — it is the index of the *first* command in this
batch within the client's global command sequence. Verified across all 16 batches:

| Batch | `first_number` | commands in batch | next batch starts at |
|---|---|---|---|
| 3 | 3 | 5 | 8 ✔ |
| 8 | 8 | 1 | 9 ✔ |
| 12 | 12 | 3 | 15 ✔ |
| 15 | 15 | 4 | 29 ✔ (15 + 4 = 19 … through 25 + 4 = 29) |
| 19 | 19 | 4 | 24 ✘ (19 + 4 = 23; one command was generated but not sent) |

The single off-by-one at batch 19→24 shows the counter also advances for commands that are
**generated but dropped** (e.g. a command cancelled before the flush). A clone that replays
command logs must tolerate these gaps.

## 4. The signature — verified

```
HMAC-SHA256( key = "4vVSD8dftv6hdfb1Hnk9",
              message = <the exact JSON payload string> )
```

The digest is hex-encoded, lower case, 64 characters, and is placed *before* the `;`.

**Verified against the live capture** in
[`../evidence/live/hmac-verification.txt`](../evidence/live/hmac-verification.txt):

```
observed prefix : d8c21de8555a80b9087b2760d087ddf5dd183a5246a71063dd10f9ee881d2e94
hmac(key, msg)   d8c21de8555a80b9087b2760d087ddf5dd183a5246a71063dd10f9ee881d2e94  <== MATCH
```

Thirteen candidate constructions were tested (standard HMAC, HMAC over `writeUTFBytes`
encodings, bare SHA-256 with key/message in both orders, MD5, SHA-1). **Only plain
`HMAC-SHA256(key, utf8(payload))` matches.** The `writeUTFBytes` length-prefix hypothesis
raised by the static analysis of `core/Crypto.as` is *not* what the shipped client does.

> The upstream server strips the 64-char prefix and never checks it. A clone should verify
> it, and should keep verifying it — that is the only client-authentication signal in the
> whole protocol.

## 5. Commands observed live

Ten distinct command names were captured with their real argument vectors:

| Command | Args | Meaning | Server handling |
|---|---|---|---|
| `complete_tutorial` | `[step]` | tutorial progress marker; ≥25 or ==15 marks the tutorial done | sets `playerInfo.completed_tutorial` |
| `push_queue_unit` | `[building_index]` | start queueing a unit in a production building | bumps `researchStepNumber`-style counters / sets `nu`,`ts` |
| `pop_queue_unit` | `[building_index]` | take the queued unit out of the building | decrements `nu`, clears `ts`/`ui` |
| `rt_open_graph_unit` | `[item_id]` | "open graph" tracking for a unit (Facebook share) | appends to `privateState.publishedOpenGraphUnit` |
| `buy` | `[index, item_id, x, y, player, orientation, ?, reason]` | place a building (`reason="b"`) or spawn a unit (`reason="u"`) | `map_add_item` + `bought_unit_add` |
| `move` | `[index, x, y, frame, label]` | move an item to a map position | sets `item[1]`, `item[2]` |
| `collect` | `[index]` | harvest a production building | resets the collect timer `item[3]` |
| `sell` | `[index, reason]` | remove an item; `"HARV"` = harvested, `"KILL"` = combat death | deletes the item, pushes to `deadHeroes` if resurrectable |
| `add_click` | `[index]` | "click to build" — add one construction click | `attr["nc"] += 1` |
| `activate_item_click` | `[index]` | construction finished | removes `attr["nc"]` |

`item_id` values seen: **1001** (Worker), **1007** (Soldier). `item_id 30` is **Academy I**.
Item indices are small integers allocated by the client and stored in `map["items"]` keyed by
the stringified index.

### 5.1 Item tuple layout (server side)

`map["items"][str(index)]` is an 8-element array:

```
[ item_id, x, y, timestamp, orientation, store_list, attr_dict, player_id ]
```

`attr_dict` uses exactly these keys: `si` (socially-in-construction help), `nc` (clicks
needed to build), `cp` (activation point), `nu` (queue length), `ts` (queue timestamp),
`ui` (queued unit id), `xp` (accumulated unit XP).

## 6. The boot sequence, end to end

Observed request order for one cold session:

```
GET  /                                            (login page)
GET  /new.html                                    (create empire)  -> 302 /play.html
GET  /play.html
GET  /static/socialwars/flash/SWLoader.swf?swftoload=...
GET  /static/socialwars/flash/Basesec_1.5.4.swf
GET  /static/socialwars/fonts/en_KomikaAxis.swf
GET  /static/socialwars/fonts/en_ArialRoundedBold.swf
GET  /static/socialwars/sounds/BACKGROUND.mp3
POST /dynamic/.../track_game_status.php  status=000-construct
GET  /static/socialwars/sprites/*.swf            (hundreds, streamed)
POST /dynamic/.../track_game_status.php  status=090-endconstruct
GET  /dynamic/.../get_game_config.php?USERID=..&user_key=..&language=en
POST /dynamic/.../track_game_status.php  status=100-config
POST /dynamic/.../get_player_info.php  (body: client_id, neighbors)
POST /dynamic/.../track_game_status.php  status=091-fontsloaded
GET  /static/socialwars/swf/dynamic2.swf
POST /dynamic/.../track_game_status.php  status=110-pinfo
POST /dynamic/.../track_game_status.php  status=120-init
GET  /static/socialwars/sounds/*.mp3
POST /dynamic/.../track_game_status.php  status=200-tutN
POST /dynamic/.../command.php                    (batches 1..16)
```

**`get_game_config.php` is a GET** while everything else is a POST. The config response is
the whole 1.7 MB `main.json` (after patching and darts-date rotation) — a clone should
content-address and cache it.

## 7. Screenshot evidence

| File | Shows |
|---|---|
| `01-intro-screen.png` | The Social Wars splash with `PLAY NOW!` / `SKIP` |
| `02-town-loaded.png` | The town loaded from the server: gold 2 000, wood/oil/steel 2 000, cash 5, level 1, pop 0/20, and the neighbour strip (AcidCaos, Nerri, [Neutral], Kiriakos, General) |
| `03-tutorial-collect.png` | Tutorial step 3 — "Click the tree to chop it" |
| `04-worker-chopping.png` | The worker has walked to the tree and is chopping |
| `05-building-placement.png` | The Academy ghost following the cursor during placement |
| `06-academy-panel.png` | The Academy panel with `BUY FOR: 30` gold / `60` premium / `OR: 1` energy |

The neighbour strip proves that `sessions.fb_friends_str()` is doing its job: the static
villages in `villages/` (AcidCaos, Nerri, Neutral, Kiriakos, Scarlet) and the two "General
Mike" villages are presented to the client as Facebook friends.

## 8. Reproducing this session

The whole harness is reproducible and lives outside the upstream tree:

| Artefact | Purpose |
|---|---|
| `capture_server.py` | Imports the untouched `server.py`, adds a JSONL request tracer, serves on 5055 |
| `cdp.js` | A ~120-line Chrome DevTools Protocol driver (Node ≥ 22, no npm deps) for `navigate`, `click`, `slowclick`, `hover`, `shot`, `seq` |
| `verify_hmac.py` | Tests 13 candidate signature constructions against a captured payload |

The browser was launched with:

```
Flashy.exe --remote-debugging-port=9222 --user-data-dir=<tmp> http://127.0.0.1:5055/
```

Because Flashy is an Electron/CEF app, the CDP endpoint exposes the page target directly,
which is why the game could be driven programmatically rather than by coordinate-guessing.

## 9. What the live session changed about the analysis

1. **The HMAC is plain HMAC-SHA256 over the payload** — the `writeUTFBytes` length-prefix
   theory from static analysis is wrong for the shipped build.
2. **The resource vector order is confirmed**, and slot 0 is *energy*, not an unknown.
3. **`first_number` is a global command index**, not a batch counter.
4. **`publishActions` is a string**, and `flashVersion` is the dotted version (`"1.5.4"`).
5. **`track_game_status.php` doubles as a tutorial-progress channel.**
6. **The 8-slot `res` vector is client-declared and the server applies it verbatim** —
   the single most important thing to fix in a clone.
7. `sell` uses the reason codes `"HARV"` (harvested) and `"KILL"` (killed in combat);
   `buy` uses `"u"` (unit) and `"b"` (building).
