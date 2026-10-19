# Clone Roadmap — Cross-Platform Client-Server Rewrite

**Goal:** re-implement Social Wars as a **cross-platform client + server** with no Flash
dependency, while preserving observable game behaviour.

**Source of truth for every rule in this plan:** the analysis documents in this directory.
Nothing here is invented; every "must" traces back to a cited finding.

---

## 1. Principles

1. **The client is the specification.** The 1 387 decompiled AS3 classes *are* the game.
   The Python server is a thin state store built to satisfy that client, not the other way
   round. Port behaviour from the AS3, not from `command.py`.
2. **The server owns the simulation.** The upstream server trusts the client for combat
   outcomes, resource costs, build costs and goal completion. That must not survive the
   rewrite. See [`02-combat-and-units.md`](02-combat-and-units.md) §"trust boundary".
3. **Keep the vocabulary.** The 94 command names, the item ids, the config schema and the
   save semantics are the *domain model*. Preserve them; change only the transport and the
   enforcement.
4. **The content is the asset.** `config/main.json` + the 5 jsonpatch patches + the 3 199
   asset files are a 2012 snapshot. They are the most expensive part to recreate and the
   easiest to lose. Version them.
5. **Ship the protocol shim.** A clone that cannot talk to the original client is a
   re-implementation; a clone that *can* talk to the original client is a preserved game.
   Keep a compatibility server that the original SWF can drive, and build the new client
   alongside it.

## 2. Target architecture

```
┌───────────────────────────────────────────────────────────────────┐
│  Client (any platform)                                            │
│  • Web  : TypeScript + WebGL/Canvas2D  (primary, widest reach)   │
│  • Desktop: Tauri / Electron shell around the same web client    │
│  • Mobile : Capacitor or React Native wrapper                    │
│  Renders from converted art atlases; runs a local prediction    │
│  layer but never decides outcomes.                               │
└──────────────────────────┬────────────────────────────────────────┘
                           │  HTTPS + JSON (versioned REST or WebSocket)
                           │  • session token (real auth)
                           │  • server-authoritative command results
┌──────────────────────────┴────────────────────────────────────────┐
│  Server                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Simulation   │  │ Economy      │  │ Content service        │   │
│  │ core (port   │  │ (costs,      │  │ (items, globals,       │   │
│  │ of IsoEngine,│  │  caps, timers)│  │  levels, goals)        │   │
│  │ Stats, combat)│  │              │  │  from config + patches │   │
│  └──────────────┘  └──────────────┘  └────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Command bus  │  │ Persistence  │  │ Identity               │   │
│  │ (94 commands)│  │ (Postgres)   │  │ (password/OAuth,       │   │
│  │              │  │              │  │  per-player sessions)  │   │
│  └──────────────┘  └──────────────┘  └────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

## 3. Workstreams

### WS-1 — Content pipeline (prerequisite for everything)

Turn the raw game data into a typed, versioned, validated content bundle.

| Task | Input | Output |
|---|---|---|
| Extract the config | `config/main.json` + `config/patch/*.json` | `content/items.json`, `levels.json`, `goals.json`, `globals.json`, … |
| Apply + freeze patches | `config/patch/patches.txt` (5 patches) | a single deterministic build artifact + a hash |
| Reconcile with the client | the 123 client-only item ids (1307–1431) | a decision: add them to the config, or mark them unavailable |
| Validate | schema | typed structs; fail the build on unknown keys |
| Preserve the darts rotation | `get_game_config.py::make_dynamic` | a scheduled job that re-rotates the 30 darts entries weekly |

**Acceptance:** a single `content-bundle-<hash>.json` is produced from a checkout, and
re-running the build yields the same hash.

> Watch out: `config/main.json` is the 2012 capture **plus** 5 patches. The patches are
> JSON-Patch, applied in place. Re-implement with `jsonpatch` semantics or a typed
> equivalent — do not hand-merge.

### WS-2 — Asset conversion (longest lead time)

1 114 SWF files, 375.49 MB, must become renderable art.

| Task | Tooling | Notes |
|---|---|---|
| SWF → frame atlas + frame table | FFDec `-export frame` | **do not** use `-export shape`: its SVG fills are base64 PNG patterns, not paths |
| SWF → SVG paths (where possible) | FFDec `-export shape` + pattern flattening | needed for scalable/vector modern rendering |
| Thumbnails | keep the 1 314 JPGs | already correct |
| Audio | keep the 140 MP3s | already correct |
| Fonts | 6 embedded `DefineFont3` + `assets/fonts/*.swf` | **`BlockBertholdRegular` does not exist** — substitute or drop |
| UI chrome | **not in the asset tree** | the modern client must draw its own UI |
| Terrain tiles | partially present (`terreno.swf`, `arbol*.swf`) | 10 terrain/intro images are missing |

**Acceptance:** every `items[].img_name` resolves to a rendered frame set, and the
1307–1431 wave renders too.

**Resolution rules (all verified):**
`sprites/<img_name>.swf` · `thumbs/<img_name>.jpg` · `sounds/<file>.mp3` ·
`magic/<img_name>.swf` · `fx/<id>.swf` · `images/<lang>/<path>` · `fonts/<lang>_<name>.swf`.
`img_name` is a **comma-separated variant list** for 5 gendered units — pick one at random
(`StaticData.parseVectorString`).

### WS-3 — Rules engine (the real work)

Port the simulation from AS3 to a language that can run on the server.

| AS3 source | Port to | Notes |
|---|---|---|
| `core/isoengine/IsoEngine.as` | simulation core | tick loop, targeting, attack cadence |
| `core/isoengine/IsoFightingElement.as` | damage pipeline | the 8-stage damage chain (shield → best_against → modifiers → crit → defense → clamp) |
| `core/generalAttacks/**` | attack system | 15 special attacks, 6 attack conditions, 10 damage classes |
| `core/Stats.as`, `StatsModifier.as` | stat resolution | per-unit stat modifiers |
| `core/UnitXPLevelInfo.as` | unit progression | thresholds are multiples of base `life`; max level 9 → +30 attack, 3× HP |
| `core/goals/**` | goal system | 30 goal classes, 134 registered goals, max 5 active |
| `quest/**` | quest state machine | 24 assault quests + the chapter system |
| `core/manager/ResourceManager.as` | economy | resource caps, collect timers, population, energy |
| `core/manager/TownManager.as` | build/upgrade | build times, costs, upgrade chains |
| `core/magic/**` | magic & tech | 10 spells + 10 techs |
| `scripts/commands/**` | command bus | all 94 command classes |

**Critical facts to encode (from the analysis):**

* `attack_interval` is **frames at 30 fps**, not seconds. Units get a random 0–4 frame
  phase; **buildings have no phase and fire in global lockstep**, and use a different range
  rule (exact `attack_range`, centre-to-centre) from units
  (`attack_range + max(0, targetWidth − 2·attack_range)`).
* Crit: 10 % chance → `(base + |variance|) × 1.5`, `variance = random(−4, +4)`.
  Defence is flat (1 in all shipped content).
* `best_against` is a **property key**, not a class. Only four counter units exist:
  Antiaircraft 20× vs `ft_flying`, Demolition Tank 15×, Mortar Thrower 10×, B52 5× vs
  `ft_building`.
* A building's own attack is scaled by `garrison / unit_capacity` — **an empty bunker deals
  0**, and a bunker fires once per garrisoned unit.
* Machinegun streams damage **only on the first bullet**.
* Unit XP is earned as *effective damage dealt to units only*.
* **Energy is not a combat resource** — it is a construction speed-up currency (max 30,
  +1 / 5 min).
* Combat uses raw `Math.random()` (`RandomGenerator.as` is a Park–Miller LCG used only for
  shuffles). **A server-authoritative port must switch to a seeded PRNG** and ship the seed
  to the client so results are reproducible and auditable.

**Acceptance:** the server can resolve a battle between two armies and produce a result
that the client renders and the server independently agrees with.

### WS-4 — Server

| Area | Upstream behaviour | Target behaviour |
|---|---|---|
| Identity | none — `USERID` from the body | real accounts, sessions, per-player authorisation |
| Transport | form posts to `.php` paths | HTTPS JSON; keep a `.php` shim for the old client |
| Resources | client-declared delta applied verbatim | **server computes** every cost and delta |
| `flash_debug` | overwrites the whole wallet | **removed** |
| Combat | client-declared winner | **server re-simulates** |
| Goals | `complete_goal(id)` trusted | goal completion evaluated server-side |
| Daily bonus | no timestamp check | timestamp-checked, once per day |
| Persistence | whole-document JSON rewrite per command | Postgres, transactional, incremental |
| Concurrency | module-level dicts, no locking | proper transactional store |
| `load_saves()` on every login-page GET | wipes and reloads all saves | no such global reload |
| `session()` returns `None` → 500 | 500 on unknown user | typed 404 |
| `assert` for framing validation | 500 on bad framing | typed 400 |
| `flask.debughelpers` import | breaks on Flask ≥ 2.3 | pin or drop |

**Acceptance:** a scripted cheat attempt (inflate `res`, replay `win_daily_bonus`, call
`flash_debug`) is rejected or has no effect.

### WS-5 — Client

| Area | Approach |
|---|---|
| Rendering | WebGL/Canvas2D isometric renderer consuming the WS-2 atlases |
| Input → commands | reuse the 94-command vocabulary; the client *requests*, the server *decides* |
| Prediction | optional local interpolation only; never authoritative |
| Iso view | the map is a 2-D grid of item positions; the client renders z-sorted sprites |
| UI | must be **rebuilt** — the Flash UI chrome is not in the asset tree |
| Text/localisation | `assets/images/en/…` + the `gettext`-style parser in `utils/gettext/` |
| Offline | not supported in v1 (the original was online-only) |

**Acceptance:** a player can complete the tutorial, build, train, attack a neighbour, run a
quest, and use the darts minigame on desktop and mobile browsers.

### WS-6 — Protocol compatibility shim (parallel with WS-4)

A thin server that speaks the *original* `command.php` dialect exactly — including the
HMAC-SHA256 framing with `Config.SERVER_KEY` — so the untouched `Basesec_1.5.4.swf` can
drive the new backend. This is what makes the project a *preservation* rather than a
re-implementation, and it is the highest-value/lowest-cost piece of the whole plan:
the framing is already fully documented and verified.

## 4. Milestones

| # | Milestone | Outcome (observable, testable) | Depends on |
|---|---|---|---|
| M0 | **Harness** | A committed script starts the upstream server, launches Flashy, drives it over CDP, and dumps a decoded request trace. *(Already built during this investigation — see §6.)* | — |
| M1 | **Content bundle** | `content-bundle.json` builds reproducibly from the repo and passes a schema check; the darts rotation still advances weekly. | WS-1 |
| M2 | **Art pipeline** | Every `items[].img_name` renders in a test viewer at 3 zoom levels; the 1307–1431 wave is included. | WS-1, WS-2 |
| M3 | **Rules engine core** | Unit stat resolution, damage pipeline and unit XP level-up match the AS3 reference implementation on a fixed test corpus (golden tests). | WS-1 |
| M4 | **Combat server-side** | A server-side battle resolution reproduces the AS3 result for the golden corpus within tolerance, using a seeded PRNG. | M3 |
| M5 | **Authoritative server** | Commands are validated server-side; the cheat battery in §5 is rejected. | M4 |
| M6 | **Protocol shim** | The original `Basesec_1.5.4.swf` plays against the new server through the shim, with no client change. | M5 |
| M7 | **Modern client alpha** | The web client can complete the tutorial and the first chapter. | M2, M5 |
| M8 | **Feature parity** | Quests, goals, darts, magic/tech, marketplace, premium, alliances, weekly bonus all functional. | M7 |
| M9 | **Packaging** | Web build + desktop (Tauri) + mobile (Capacitor) builds ship from one source tree. | M8 |

## 5. The cheat battery the new server must pass

Each of these is a real, demonstrated hole in the upstream server.

| Attack | Upstream result | Required result |
|---|---|---|
| `command.php` with `res = [0,0,1e9,0,0,0,0,0]` | gold 2 000 → 1 000 002 000 | rejected / clamped to the true cost |
| `flash_debug` with arbitrary values | wallet overwritten | command removed |
| `win_daily_bonus` replayed | unlimited rewards | once per day per player |
| `complete_goal(134)` for every goal | all goals completed, 10 gold each | goals evaluated server-side |
| `set_goals` / `set_quest_var` / `admin_set_quest_rank` | trusted verbatim | validated |
| `end_attack` with a forged winner | accepted, victim untouched | re-simulated |
| `buy_offer_pack` with any item id | grants the item free | validated against the offer table |
| `data` with a wrong HMAC | accepted (prefix stripped, never checked) | 401 |
| `USERID` of another player | accepted | 403 |
| `command.php` with a missing `;` | 500 (AssertionError) | typed 400 |
| `end_quest` with a forged `win` | accepted | validated against the quest rules |
| `collect` on a building that is not ready | client decides | server checks the timer |

## 6. The harness already exists

The M0 harness was built during this investigation and is reproducible:

| Component | Path (investigation scratch area) | What it does |
|---|---|---|
| Traced server | `run/capture_server.py` | Wraps the untouched `server.py`, logs every request (method, path, query, full body) to JSONL, serves on 5055 |
| CDP driver | `tools/cdp.js` | ~120 lines, Node ≥ 22, no npm dependencies: `navigate`, `click`, `slowclick`, `hover`, `seq`, `shot`, `events`, `targets` |
| HMAC verifier | `tools/verify_hmac.py` | Tests 13 signature constructions against a captured payload |
| Evidence builder | `tools/build_evidence.py` | Produces `re/evidence/live/` from a raw trace |
| Decompiler | FFDec 26.3.0 (`ffdec-cli.exe`) | `-export script`, `-dumpSWF`, `-export frame` |

It is the regression harness for M6: if the shim is correct, the *original* SWF must still
play.

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| The 1307–1431 content wave is in the client but not the config | High | reconcile before M1; the sprites and delegates exist |
| Combat re-implementation diverges from the AS3 | High | golden-corpus tests (M3/M4); keep the original client as an oracle |
| 375 MB of SWF conversion is slow and lossy | Medium | start M2 in parallel with M1; `-export frame` atlases first, SVG paths only if needed |
| Proprietary fonts cannot be redistributed | Medium | 4 of 6 embedded fonts are third-party; substitute |
| UI chrome does not exist in the asset tree | Medium | rebuild the UI from scratch; budget for it explicitly |
| Zynga content rights | High | **legal decision required before any public release** — see §8 |
| The 2012 config may not describe 2026 expectations | Low | the client is the spec; M1 reconciles |
| `first_number` gaps complicate log replay | Low | tolerate gaps (see [`06-LIVE-SESSION-PROTOCOL.md`](06-LIVE-SESSION-PROTOCOL.md) §3.4) |

## 8. Licensing — decide before writing code

* The upstream **code** is GPL v3. Reusing `command.py`, `engine.py`, `sessions.py` or any
  of the Python makes the clone GPL v3.
* The upstream **content** (config JSON, sprites, audio, fonts) was created by Zynga and is
  covered by Zynga's terms, not GPL. The upstream project itself leans on archival
  exemptions (PCCPSACT, EFGAMP, UNESCO PERSIST, Flashpoint).
* A clone that ships Zynga's art to the public needs either a licence, the archival
  exemption, or a clean-room re-creation of the art.

**Recommendation:** keep the GPL v3 upstream server as a separate, clearly-licensed
component; write the new server under a licence compatible with both; and treat the art as
a separately-licensed asset bundle that can be dropped in. Get a legal opinion before
publishing.

---

**Next:** [`09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](09-LIMITATIONS-AND-OPEN-QUESTIONS.md) for
what we still do not know, or go back to
[`00-EXECUTIVE-SUMMARY.md`](00-EXECUTIVE-SUMMARY.md) for the top-level findings.
