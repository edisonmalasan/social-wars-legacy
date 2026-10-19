# Executive Summary — Social Wars Flash Game: Investigation Findings

**Target analysed:** `C:\Users\Edison\Desktop\socialwarriors` (the *Social Wars preservation project*)
**Goal of the investigation:** everything needed to re-implement the game as a **cross-platform client-server application** with no Flash dependency.
**Method:** REA MCP reverse engineering, FFDec decompilation of the ActionScript 3 client, source review of the Python server, and a **live end-to-end session** with the real Adobe Flash Player driving the local server.
**Date:** 2026-10-20

---

## 1. What this project actually is

| Layer | Technology | Notes |
|---|---|---|
| Game client | **Flash / ActionScript 3** (`Basesec_1.5.4.swf`) | SWF v10, 1 387 AS3 classes, AVM2 46.16 |
| Client loader | `SWLoader.swf` (6 classes) | Downloads and `loadBytes()`s the real client at runtime |
| Server | **Python 3 + Flask** | 16 live routes; 6 of them the "dynamic" game API |
| Persistence | JSON files on disk (`saves/<USERID>.save.json`) | No database |
| Static content | 3 199 asset files (716.77 MB) | 1 114 SWF, 1 753 JPG, 140 MP3, 130 PNG |
| Game data | `config/main.json` (1.7 MB) | 778 items, 104 globals, 100 levels, … |
| Licence | **GPL v3** | Preservation/archival framing; see §7 |

The Python server is **not** the original Zynga backend. It is a community re-implementation
of the *wire protocol* that the Flash client speaks, backed by a 2012 capture of the original
`get_game_config.php` response. Understanding that distinction is the single most important
framing for the clone work: **the client is the authoritative game implementation; the server
is a thin state store.**

## 2. The eleven findings that matter most

### 2.1 The original server signing key is recovered and verified

`command.php` bodies are signed:

```
data = <64 hex chars> + ";" + <JSON payload>
```

The hex prefix is `HMAC-SHA256(Config.SERVER_KEY, json_payload)`. The key was recovered from
the decompiled `core/Config.as`:

```
Config.SERVER_KEY = "4vVSD8dftv6hdfb1Hnk9"
```

**This was verified against a live capture** — the recovered key reproduces the client's own
64-hex prefix byte-for-byte. See [`../evidence/live/hmac-verification.txt`](../evidence/live/hmac-verification.txt).
The local preservation server never validates this signature; a clone should.

### 2.2 Combat is 100 % client-side, and the server believes it

`end_attack` and `end_quest` carry the *entire* battle report (winner, loot, per-unit losses).
The server applies only `lost = max(0, unit[2] - unit[3])` and never touches the victim's save.
`apply_resources()` trusts the client's declared 8-slot resource delta and only clamps at zero.

A clone must decide explicitly whether to re-simulate combat server-side or to accept the
client's outcome. The upstream project accepts it — which is why it is trivially cheatable.

### 2.3 The command catalogue: 94 sent, 63 handled, 32 silently dropped

| | Count |
|---|---|
| Distinct command names the client can send | **94** |
| Handled by `command.py::do_command` | **63** |
| Sent by the client but **ignored** by the server | **32** |
| Handled by the server but never sent by the client | **1** (`first_time_marketplace`) |

The 32 ignored commands include `finish_building`, `upgrade`, `premium_upgrade`,
`attack_player`, `spy_player`, `modify_energy`, `buy_resources`, `place_gift`,
`set_strategy`, `win_alliance_daily_bonus`, `assist_neighbor`, `assist_receive`,
`cross_promotion_finished`. Full table in
[`03-commands-quests-economy.md`](03-commands-quests-economy.md).

### 2.4 The command wire format (verified live)

A batch is a JSON object; each command is a 4-tuple:

```json
[ map_id, "<command_name>", [ args... ], [ energy, xp, gold, wood, oil, steel, cash, mana ] ]
```

The 8-slot resource vector order was **confirmed empirically** from a live session: a worker
purchase reported `res=[0,5,-10,0,0,0,0,0]` and the gold counter fell by exactly 10; a
building purchase reported `res=[0,13,0,-125,0,0,0,0]` and the **wood** counter fell by
exactly 125.

### 2.5 The live session proves the whole stack still runs

A real **Adobe Flash Player** (bundled in Flashy Browser 1.2.4, `pepflashplayer.dll`) loaded
`Basesec_1.5.4.swf` from the local Flask server, completed the tutorial, trained units,
built an Academy, entered **Mission 1** and finalised a live assault — producing
**1 664 HTTP requests across 294 distinct paths and 34 `command.php` batches** covering
**17 distinct command names**, including the full `end_quest` battle report. The game is
fully playable today. See [`06-LIVE-SESSION-PROTOCOL.md`](06-LIVE-SESSION-PROTOCOL.md).

The `end_quest` payload, observed verbatim:

```json
{"difficulty":1,"map":0,"quest_id":"100000001","voluntary_end":1,"win":0,
 "units":[[1007,3,0,0]],"duration":662}
```

`units` is `[item_id, sent_to_battle, A, B]` and the server computes `lost = max(0, A − B)`
— confirming the whole battle outcome is client-declared.

### 2.6 The game data is a 2012 snapshot, but the client is newer

`config/main.json` is byte-identical to `config/get_game_config.php_29august2012_nohash.json`
— a live capture of the original server's configuration from **29 August 2012**. But the
client contains **123 item ids the config has never heard of** (the 1307–1431 mech/drone
wave), and 722 asset files are unreferenced by the config. Any clone must reconcile the
config with the client, not just copy the config.

### 2.7 The config is patched, not static

At import time the server applies **5 `jsonpatch` patches** (`config/patch/patches.txt`):
`atom_fusion_item`, `unit_patch`, `atom_fusion_items_data`, `atom_fusion_powerup`, `targets`.
This takes the config from 778 to **900 items** and 104 → 105 globals. It then runs
`remove_duplicate_items()` (reported 0 duplicates) and `make_dynamic()`, which **rotates the
darts minigame schedule 29 times** forward so the weekly prize rotation still works in 2026.

### 2.8 There is no authentication anywhere

`USERID` is read straight out of the request body. `user_key` and `accessToken` are read and
thrown away. Any HTTP client can act as any player. The Flask `session` cookie used by the
login page is not consulted by any dynamic endpoint.

### 2.9 `flash_debug` is a full wallet overwrite

Sent automatically by the client roughly every 20 commands at level ≥ 10, it replaces cash,
xp, gold, oil, steel and wood with client-supplied values. **Observed live** as
`flash_debug 5,50,3000,1890,2000,1820,1895`. It is the single most exploitable command
in the protocol.

### 2.10 The asset tree is 375 MB of SWF that must be converted

1 114 SWF files (375.49 MB) hold the vector art. A modern client needs them as SVG paths or
as a sprite atlas. **Caveat:** `ffdec -export shape` produces SVG whose fills are base64 PNG
patterns rather than paths — `-export frame` (atlas + frame table) is the correct path.
JPG/PNG/MP3 can be used as-is.

### 2.11 The upstream build script has been broken since 2022

`build/build.bat` passes `--add-data "..\..\assets;assets"`, which resolves **outside the
repository** (`C:\Users\Edison\Desktop\assets`, which does not exist). The correct prefix is
`..\`. The Windows release path has not built from source in years.

## 3. System map

```
                     +----------------------------------------+
                     |  Browser (Flashy Browser / Chrome      |
                     |  + Ruffle extension)                    |
                     |  -- <embed> SWLoader.swf (flashvar      |
                     |       swftoload)                        |
                     |       +-- loads Basesec_1.5.4.swf       |
                     |           (1387 AS3 classes)            |
                     +-----------------+----------------------+
                                       |  HTTP
        +------------------------------+------------------------------+
        |  Flask server (127.0.0.1:5055)                             |
        |  /static/socialwars/**   -- 3199 asset files              |
        |  /dynamic/menvswomen/srvsexwars/**  -- game API           |
        |     get_game_config.php   get_player_info.php             |
        |     command.php           track_game_status.php            |
        |     sync_error_track.php  alliance/                       |
        +------------------------------+------------------------------+
                                       |  JSON files
                                saves/<USERID>.save.json
                                (playerInfo / maps[] / privateState)
```

Two roots, one session:

| Root | Flashvar | Default (production) |
|---|---|---|
| Static assets | `staticUrl` | `http://staticmw.socialpointgames.com/appsfb/` |
| Dynamic API | `dynamicUrl` | `http://dynamicmw.socialpointgames.com/appsfb/menvswomen/srvsexwars/` |

## 4. What a faithful clone must reproduce

| System | Reference document |
|---|---|
| Endpoints, flashvars, HMAC framing, map flavours | [`01-network-protocol.md`](01-network-protocol.md) |
| Damage pipeline, counters, unit XP, special attacks | [`02-combat-and-units.md`](02-combat-and-units.md) |
| 94-command catalogue, economy, quests, goals | [`03-commands-quests-economy.md`](03-commands-quests-economy.md) |
| Save format, config pipeline, routes, build/packaging | [`04-python-server-and-data.md`](04-python-server-and-data.md) |
| Asset taxonomy, config→asset resolution, conversion | [`05-assets-and-content-pipeline.md`](05-assets-and-content-pipeline.md) |
| Observed live traffic, verified HMAC, real payloads | [`06-LIVE-SESSION-PROTOCOL.md`](06-LIVE-SESSION-PROTOCOL.md) |
| REA MCP capability assessment and byte-pattern findings | [`07-REA-EVIDENCE.md`](07-REA-EVIDENCE.md) |
| The actual rewrite plan, in dependency order | [`08-CLONE-ROADMAP.md`](08-CLONE-ROADMAP.md) |
| What we still do not know | [`09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](09-LIMITATIONS-AND-OPEN-QUESTIONS.md) |

## 5. The rewrite plan in one paragraph

Do **not** port the Python. The upstream server is a 2012-era state-store with no auth, no
concurrency control, no validation, and a save format that re-writes the whole document on
every command. Build instead: (a) a **rules engine** ported from the decompiled AS3
(`IsoEngine`, `Stats`, `UnitXPLevelInfo`, the 94 command classes) so the simulation is
server-owned; (b) a **content pipeline** that ingests `config/main.json` + the 5 patches and
emits a typed, versioned content bundle; (c) an **asset converter** that turns the 1 114 SWF
into SVG atlases; (d) a **modern client** (WebGL/canvas) that speaks the same command
vocabulary but a JSON+TLS transport instead of `command.php` form posts; and (e) a **proper
server** with authentication, an authoritative economy, and a database. The detailed,
dependency-ordered breakdown is in [`08-CLONE-ROADMAP.md`](08-CLONE-ROADMAP.md).

## 6. Two upstream bugs worth fixing in the clone

1. **`constants.py` duplicate dict keys.** `Quests.QUEST` defines `100000024`, `100000025`
   and `100000026` twice. Python keeps the last binding, so quest 8 (`HARDCORE8`) resolves to
   `ISLA_RUBEN3D`, quest 10 (`HARDCORE10`) to `ISLA_KASPAR` and quest 9 (`HARDCORE9`) to
   `ISLA_EGG2`. The `villages/quest/` directory contains all of them; only the *name lookup*
   is wrong.
2. **`PropertyManager.FIGHTING_TYPE_ARMORED = "ft__armored"`** (double underscore) never
   matches the config's `ft_armored`, so the armoured-unit damage rule is dead code.

## 7. Legal / archival note

The upstream repository is **GPL v3** and explicitly frames itself as a preservation project,
citing the US Copyright Office's PCCPSACT exemption, EFGAMP, the UNESCO PERSIST programme,
Flashpoint, and the Adobe Flash Player Archive. A clone that reuses the upstream *code* is
therefore GPL v3. A clone that reuses only the *content* (sprites, config, audio) inherits
Zynga's original asset rights unless the archival exemption applies. This needs a legal
decision **before** any public release — it is tracked as an open question in
[`09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](09-LIMITATIONS-AND-OPEN-QUESTIONS.md).

---

**Next:** [`06-LIVE-SESSION-PROTOCOL.md`](06-LIVE-SESSION-PROTOCOL.md) for the observed wire
traffic, or [`08-CLONE-ROADMAP.md`](08-CLONE-ROADMAP.md) to jump straight to the rewrite plan.
