# Social Wars: Redux — Design Plan for a Flash-free Desktop Client

> Status: **Proposed** — this document captures the architecture decided for continuing the Social Wars preservation project with a modern, Flash-free client.
> Date: 2026-09-10
> Scope: Desktop client for the existing preservation server. Everything described here is grounded in the current repo state (verified 2026-09-10).

---

## 1. Goal

A modern desktop client for the Social Wars preservation server that runs **without any Flash runtime** — no Ruffle, no Adobe Flash, no browser plugin.

- Same server, same saves, same game content; new client bones.
- Single-player default (local server); the same client works against a hosted server later for community play.

## 2. Non-goals (v1)

- Reimplementing every screen pixel-for-pixel.
- Ruffle / original-SWF parity for corner-case bugs.
- Real-time multiplayer combat.
- Monetization logic.

---

## 3. What the reimplementation actually is

The original game is a Flash client (the SWF) talking to a PHP game server. For this project, the server side has already been rebuilt in Python (`server.py`, `engine.py`, `command.py`) and the game data has been fully captured. A flash-free client means writing a **new client** — but only the *view and interaction layer* is new. Every content layer is already outside the SWF, as verified against the current repo:

| Layer | Where it lives | Reusable? |
|---|---|---|
| 778 items (stats, costs, timers, img mapping) | `config/main.json` — 469 buildings, 308 units, 1 'l' | ✅ complete |
| 26 quest maps (waves, bosses, treasure as placed units) | `villages/quest/*.json` | ✅ complete |
| Village/save format (map fields, `privateState`, items `[id,x,y,ts,orient,store,attr,player]`) | `villages/initial.json`, `sessions.py` | ✅ complete |
| Server rules (all ~60 commands, economy engine) | `command.py`, `engine.py`, `get_game_config.py` | ✅ complete |
| UI art (chapters, quest panels, shop banners) | `assets/images/en/**` (158 files) | ✅ complete |
| **Item sprites** | `assets/sprites/*.swf` (862 files) | ⚠️ needs a one-time extraction step (see §6) |
| Item thumbnails (shop previews) | `assets/thumbs/*.jpg` (1314 files) | ✅ usable immediately |

**The honest scope:** we are rebuilding *presentation* on top of an existing game server — not rebuilding the game. That is the difference between months and years.

---

## 4. Target architecture

```
┌───────────────────────────── Desktop EXE (PyInstaller) ─────────────────────────────┐
│  Python process                                                                      │
│   ├─ Flask server (existing: server.py, engine.py, command.py — unchanged)          │
│   └─ pywebview native window ──► http://127.0.0.1:5055/                             │
│                                      │                                               │
│   HTML5/JS client (new: client/)     ▼                                               │
│   ├─ Renderer (Canvas, iso village)   │                                              │
│   ├─ Game logic (timers, combat)      │  HTTP POSTs (same protocol the SWF used)    │
│   └─ API bridge ──────────────────────┘──► command.php, get_player_info.php         │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

- **Same HTTP protocol as the SWF.** Endpoints already exist and are SWF-compatible: `command.php` (`<64-hex-hash>;` + JSON batch), `get_player_info.php`, `get_game_config.php`, `track_game_status.php`, `sync_error_track.php`. Auth is the `USERID` / `user_key=123456789` fields — no reverse engineering needed.
- **Server untouched** during v1. All state changes flow through the existing `command()` dispatcher. Saves stay byte-compatible with the original game — a village can be played in Ruffle *and* in the new client interchangeably.
- **Desktop shell candidates:**
  - **PyWebView** *(recommended)* — pure Python, reuses the existing PyInstaller pipeline, native window, ~zero new toolchain.
  - **Electron** — heavier, requires Node.
  - **Tauri** — smallest binary, requires Rust.
  - All three run unchanged against the same server + client.
- **Dev mode:** run `server.py` + open any modern browser to `127.0.0.1:5055` — no Flash involvement anywhere.

---

## 5. Game data flow through the new client

```
get_game_config.php ──► config cache (items/categories/goals/darts)
get_player_info.php  ──► { playerInfo, map, privateState, neighbors }
   render map from map.items ──► iso draw (cost lookup = config item)
   UI timers (build_time, training_time, collect) ──► client clock
   user action ──► compute resources + build list ──► POST command.php batch
command.php response ──► update local state mirrors
```

**Important detail:** the server is *trusted-client* (it clamps resource deltas at 0 and persists what is sent). For single-player / offline this is ideal — combat and timer rules can live in the client and the server happily persists results. For a future public online server, flip a `server_authoritative` flag and move validation server-side (see §10 decisions).

---

## 6. The one real technical unknown: item sprites

**Finding:** item sprites are **not** PNGs — they are tiny individual **Flash 10 movie clips** (`CWS` compressed, ~10 KB): `assets/sprites/0001_house_1_m.swf`. Coverage: **763 / 778** items have sprite SWFs; **744 / 778** have JPG thumbs.

**Plan:** a one-time build-time pipeline `tools/extract_sprites.py` that decompresses each sprite SWF (zlib) and dumps the embedded image frames (`DefineBitsJPEG` / `DefineBitsLossless` tags) into sprite sheets + a JSON manifest (`item_id → frames, fps, hotspot`). Sprites are uniform, tiny, and dependency-light — a pure-Python parser is realistic (fallback: `swfextract` / JPEXS CLI).

- **M1 can ship today without this** using `assets/thumbs/*.jpg` (744 items, static). Extraction upgrades the village from "static previews" to "animated sprites" later.

---

## 7. Client subsystems → server commands map

| Subsystem | Client work | Server side (exists) |
|---|---|---|
| Village map, pan/zoom, selection | iso renderer from `map.items` | `get_player_info.php` |
| Build / place / rotate / move / sell | shop UI + placement grid | `buy`, `move`, `orient`, `sell`, `batch_remove` |
| Production & collecting | timers from `collect`, `collect_type`, `max_collects` | `collect` |
| Storage & inventory | store UI | `store_item`, `place_stored_item`, `sell_stored_item`, `store_add_items` |
| Expansions | world UI | `expand` |
| Research (Area 51 / Robotic) | research tree UI | `next_research_step/item`, `research_buy_step_cash`, `reset_research_item` |
| Unit training + army | training queue from `training_time` / `trains_ids` | `push_queue_unit`, `pop_queue_unit` |
| Quest battles | **reimplement wave/combat engine**; produce `end_quest` payload | `end_quest` (parses boss/kills/treasure — shapes in `command.py`) |
| PvP attacks | battle sim + `end_attack` payload | `end_attack` (server TODOs: victim save, attack logs) |
| Aux systems: darts, magic, Atom Fusion, offer packs, premium | minigame UIs | all commands present (`buy_magic`, `darts_*`, `push_queue_unit2`, `buy_offer_pack`, `buy_premium_account`…) |
| Goals / tutorial / weekly reward | goal system UI | `set_goals`, `complete_goal`, `complete_tutorial`, `set_variables` |

Out of ~60 server commands, the client needs to drive all of them — but each is a small, testable interaction. The combat/quest engines are the largest single piece of new logic. Unit stats (`attack/defense/life/velocity/attack_range/attack_interval/best_against`) are all in config; `tools/atom_fusion_builder.py` already proves the team can re-derive formulas.

---

## 8. Renderer design (village)

- Grid-based isometric projection: screen = `(x−y, x+y)` basis; per-item `width`/`height` cells; `elevation` for draw order; `orientation` 0–3.
- Draw order: depth-sort by `(y + x·λ)` with elevation offset; verify visually against Ruffle screenshots (parity testing, §10).
- Item lookup: `map.items[i][0]` → `config.items[].img_name` → sprite manifest → frame `[n]`; `max_frame` = loop length.
- HUD: resources from map (`gold/wood/oil/steel` + `playerInfo.cash` + `privateState.mana`); timers from item attrs (`build_time`, queue `nu`/`ts` in `attr` — already modeled by `engine.py`).
- Camera: smooth pan/zoom; hotkeys from `constants.py` (`KEY_*` table = original key map).

---

## 9. Milestones (each shippable)

- **M0 — Seed:** `client/` served by Flask; canvas loads `get_player_info` → draws debug grid. *Done when: server + empty canvas handshake works.*
- **M1 — Village viewer (read-only):** all `map.items` drawn at correct iso positions using thumbs; resources HUD; pan/zoom. *Acceptance: an existing save renders; 40/40 initial items visible.*
- **M2 — The economy loop:** select → collect (timers), build (cost check + placement), move/rotate/sell/store → command batches → **save survives logout/relogin**. *Acceptance: build a House, produce gold, restart cleanly.*
- **M3 — Shop & world:** category shop from config, expansions, offer packs, magic panel.
- **M4 — Units & army:** training queues, unit drag-to-map, `boughtUnits` / `deadHeroes` / resurrect.
- **M5 — Quests:** quest loader (waves from quest JSON `u` items), JS combat engine, `end_quest` payloads **matching `command.py`'s parser exactly** (it documents the required keys). *Acceptance: complete Quest 01 two ways.*
- **M6 — Neighbors & PvP:** visit villages, attacks (`end_attack`), market.
- **M7 — Shine:** sprite extraction polish, settings, cloud-sync-ready profiles, Ruffle **parity toggle** for A/B testing.

---

## 10. Decisions to make (and recommendations)

1. **Trusted-client vs server-authoritative.** *Recommended:* trusted-client for v1; revisit if a public online server is ever hosted.
2. **Visual fidelity: pixel-faithful (original sprites, classic look) vs modernized (responsive canvas).** *Recommended:* original assets on a scalable modern canvas — best of both.
3. **Desktop shell:** *PyWebView* unless Node is already a team skill (then Electron). Reversible decision — client and protocol are shell-agnostic.
4. **Parity testing harness:** keep a debug button that boots the SWF in Ruffle next to the new client, so every milestone can be verified side-by-side.

---

## 11. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Sprite frame extraction hits an SWF tag we don't parse | Med | Thumbs work today; extraction is M7, not a blocker |
| `max_frame` ≠ extracted frame count | Med | Manifest generation logs mismatches; fall back to frame 0 |
| Combat/quest fidelity drifts from original | High (effort) | Data is complete; `end_*` payload shapes documented in `command.py`; A/B via Ruffle parity toggle |
| WebView2 missing on old Windows | Low | Shell launches default browser as fallback |
| `jsonpatch` / `requests` missing from `requirements.txt` | Known now | Fix in the same PR as M0 |

---

## 12. Countdown to "it's doing the thing"

The proof point for this whole plan is **M2**: ~1 week of focused work from an empty `client/` to "build a House, collect gold, reload from save." Everything after M2 is feature surface, not architecture.