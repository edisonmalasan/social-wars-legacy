# Social Wars — Reverse-Engineering Report & Document Map

> **What this is:** the complete findings of an investigation into the **Social Wars**
> preservation project (`C:\Users\Edison\Desktop\socialwarriors`), conducted to enable
> **cloning it as a cross-platform client-server application** with no Flash dependency.
>
> **This file is the map.** Every finding lives in a linked document; this page tells you
> which one to open.

---

## 1. The short version

| | |
|---|---|
| **Target** | A Flask/Python re-implementation of Zynga's Flash game *Social Wars* (internally `SexWars`, client v1.5.4) |
| **Client** | `Basesec_1.5.4.swf` — SWF v10, **1 387 ActionScript 3 classes**, one 2 MB AVM2 bytecode block, loaded by `SWLoader.swf` |
| **Server** | 16 live Flask routes; 6 form the "dynamic" game API under `/dynamic/menvswomen/srvsexwars/` |
| **Content** | `config/main.json` (a **29-Aug-2012** live capture of the original config, plus 5 JSON-Patch patches) and **3 199 asset files / 716.77 MB** |
| **The headline** | The original **server signing key is recovered and verified live**: `HMAC-SHA256("4vVSD8dftv6hdfb1Hnk9", payload)` reproduces the client's own 64-hex `data` prefix byte-for-byte |
| **The trap** | The server **believes the client**: resource costs, combat outcomes, goal completion and daily rewards are all client-declared and never validated. A clone must fix this. |
| **Bottom line** | The game is **fully playable today** with a real Adobe Flash Player against the local server. The client — not the Python — is the game. Port the client, replace the server. |

### Ten findings you should not skip

1. `Config.SERVER_KEY = "4vVSD8dftv6hdfb1Hnk9"` — **verified against live traffic**.
2. The `command.php` resource vector is **`[energy, xp, gold, wood, oil, steel, cash, mana]`** — verified by watching the UI counters move.
3. `first_number` is a **global command index**, not a batch counter.
4. **94** command names exist; the server handles **63** and silently ignores **32**.
5. Combat is **100 % client-side**; `end_attack` ships the whole battle report.
6. `flash_debug` **overwrites the entire wallet** from client arguments.
7. There is **no authentication anywhere** — `USERID` comes from the request body.
8. The config is a **2012 snapshot**; the client knows **123 item ids the config does not**.
9. **1 114 SWF files (375 MB)** must be converted for a non-Flash client — and
   `ffdec -export shape` is the *wrong* tool for it.
10. `build/build.bat` has pointed at `..\..\assets` (outside the repo) **since 2022** — the
    Windows release has not built from source in years.

---

## 2. Document map

### 2.1 Read in this order

| # | Document | What you get | Size |
|---|---|---|---|
| **00** | **[Executive Summary](docs/00-EXECUTIVE-SUMMARY.md)** | The cross-cutting findings, the system map, and the rewrite thesis. **Start here.** | 14 kB |
| **01** | [Network & Protocol Layer](docs/01-network-protocol.md) | All 24 endpoints, the flashvar contract, the `command.php` framing, the HMAC, map flavours, and the client↔server gaps. | 81 kB |
| **02** | [Combat, Unit Stats & Progression](docs/02-combat-and-units.md) | The damage pipeline step by step, all damage types, all special attacks, counters, unit XP, and the combat trust boundary. | 73 kB |
| **03** | [Command Catalogue, Economy, Quests & Goals](docs/03-commands-quests-economy.md) | **The 94-row command table**, the economy rules, the quest state machine, the goal system, and the 32 commands the server drops. | 82 kB |
| **04** | [Python Server, Save Format & Game Data](docs/04-python-server-and-data.md) | Route table, the complete save schema, the config patch/darts pipeline, build & packaging, and a 20-item rewrite risk register. | 138 kB |
| **05** | [Assets & Content Pipeline](docs/05-assets-and-content-pipeline.md) | Asset taxonomy, the verified config→asset resolution rules, the **778-row per-item table**, the FX/audio/font catalogues, and the conversion plan. | 331 kB |
| **06** | [Live Session Protocol](docs/06-LIVE-SESSION-PROTOCOL.md) | The observed wire traffic: boot sequence, decoded payloads, the verified signature, and how to reproduce the whole session. | 19 kB |
| **07** | [REA MCP Evidence Log](docs/07-REA-EVIDENCE.md) | What REA could and could not establish, the byte-pattern sweep over the client bytecode, and the Electron analysis of the browser that runs it. | 19 kB |
| **08** | [Clone Roadmap](docs/08-CLONE-ROADMAP.md) | The actual rewrite plan: 6 workstreams, 10 milestones, the cheat battery the new server must pass, and the risks. | 17 kB |
| **09** | [Limitations & Open Questions](docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md) | What we do **not** know, the upstream bugs found, and 9 open questions with the cheapest first. | 14 kB |

### 2.2 Machine-readable

| Artefact | Contents |
|---|---|
| [`docs/items-assets.csv`](docs/items-assets.csv) | The 778 config items → resolved sprite / thumbnail / sound files. One row per item. |
| [`evidence/live/requests.jsonl`](evidence/live/requests.jsonl) | Every HTTP request the real Flash client made (309 requests, static-asset noise trimmed). |
| [`evidence/live/command-payloads.txt`](evidence/live/command-payloads.txt) | All 16 `command.php` batches, decoded: signature, query, and every command with its arguments and resource delta. |
| [`evidence/live/endpoint-summary.txt`](evidence/live/endpoint-summary.txt) | Per-endpoint request counts and response statuses. |
| [`evidence/live/hmac-verification.txt`](evidence/live/hmac-verification.txt) | 13 candidate signature constructions tested against a real payload; exactly one matches. |
| [`evidence/live/screenshots/`](evidence/live/screenshots/) | Six screenshots of the live game: splash, town, tutorial, harvesting, building placement, Academy panel. |

---

## 3. Task → document routing

| If you want to… | Read |
|---|---|
| Understand the whole system in 10 minutes | [00](docs/00-EXECUTIVE-SUMMARY.md) |
| Implement a client that talks to the server | [01](docs/01-network-protocol.md) + [06](docs/06-LIVE-SESSION-PROTOCOL.md) |
| Re-implement combat faithfully | [02](docs/02-combat-and-units.md) |
| Know exactly what each command carries | [03](docs/03-commands-quests-economy.md) |
| Migrate the save format | [04](docs/04-python-server-and-data.md) |
| Convert the art | [05](docs/05-assets-and-content-pipeline.md) |
| See the traffic the real client generates | [06](docs/06-LIVE-SESSION-PROTOCOL.md) |
| Know what REA contributed | [07](docs/07-REA-EVIDENCE.md) |
| Plan the rewrite | [08](docs/08-CLONE-ROADMAP.md) |
| Know the gaps before you commit | [09](docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md) |
| Reproduce a live session | [06](docs/06-LIVE-SESSION-PROTOCOL.md) §8 |

---

## 4. Target map — where each finding came from

| Artefact in the target | Size | What it told us | Document |
|---|---|---|---|
| `assets/flash/Basesec_1.5.4.swf` | 4.54 MB → 6.09 MB | 1 387 AS3 classes in one 2 MB AVM2 block; the whole client | 01, 02, 03 |
| `assets/flash/SWLoader.swf` | 128 kB | The runtime loader; `swftoload` flashvar; `Security.allowDomain("*")` | 01, 06 |
| `assets/flash/` (58 more `Basesec` builds) | 1.4.5 → 1.5.4 | The client's own version history — an open follow-up | 09 |
| `assets/sprites/`, `assets/fx/`, `assets/magic/`, `assets/thumbs/` | 2 200+ files | Per-item art; the config→asset resolution rules | 05 |
| `assets/images/`, `assets/sounds/`, `assets/fonts/` | 578 / 140 / 2 | Localised images, audio, and the 2 SWF font libraries | 05 |
| `config/main.json` | 1.70 MB | The 2012 game data; 20 sections; 778 items | 03, 04 |
| `config/patch/*.json` (5) | 780 kB | The shipped delta over the 2012 capture: 778 → 900 items | 04 |
| `config/get_game_config.php_*.txt` | 3.7 MB | Two original server captures (Jul + Aug 2012) | 04, 09 |
| `server.py`, `command.py`, `engine.py`, `sessions.py`, … | 130 kB | The 16 routes, the 63 handled commands, the save model | 04 |
| `constants.py` | 38 kB | Quest ids, category/subcategory constants — and a duplicate-key bug | 00, 03 |
| `villages/` (7 static + 23 quest) | 1.6 MB | The save schema in the wild, and the quest id convention | 04 |
| `templates/*.html` | 44 kB | The flashvar contract the client receives | 01, 06 |
| `build/`, `tools/`, `mods/` | 90 kB | The (broken) Windows build, the content tooling, the mod system | 04 |

---

## 5. How this was produced

| Phase | Tool | Output |
|---|---|---|
| Container analysis | FFDec 26.3.0 `-dumpSWF` | 22 228-line tag listing; the single `DoABC2` block located |
| Client decompilation | FFDec 26.3.0 `-export script` | 1 387 `.as` files → reports 01, 02, 03 |
| Byte-level confirmation | **REA MCP** `search_bytes` over 64 KiB ABC chunks | 25 protocol strings located in the shipped binary → report 07 |
| Server analysis | Source reading + live HTTP probing | Report 04 |
| Data analysis | Programmatic JSON analysis | Reports 03, 04, 05 |
| Asset inventory | Filesystem analysis + FFDec frame export | Report 05 |
| **Live session** | **Real Adobe Flash Player** (in Flashy Browser 1.2.4) + a purpose-built CDP driver | Reports 01, 06; `evidence/live/` |
| Browser shell analysis | **REA MCP** `analyze_javascript_application` on the browser's `app.asar` | Report 07 |
| Synthesis | Cross-checking every claim against a second call site or against live traffic | Reports 00, 08, 09 |

**Reproduce the live session:** the harness is described in
[06 §8](docs/06-LIVE-SESSION-PROTOCOL.md#8-reproducing-this-session) —
a traced server wrapper, a ~120-line CDP driver with no npm dependencies, and an HMAC
verifier.

---

## 6. Ground rules for reading this report

* **The client is the specification.** Where the Python server and the AS3 disagree, the AS3
  describes the real game and the Python describes an approximation of it.
* **Static analysis is cross-checked.** Every non-trivial claim in reports 01–03 was
  confirmed at a second call site; the highest-risk claims were confirmed against live
  traffic.
* **Uncertainty is labelled.** `VERIFIED` / `UNVERIFIED` markers are used in the deep
  reports. [09](docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md) lists every open item.
* **This is a research artifact, not a product.** It documents someone else's game for
  preservation and study. The licence question in
  [08 §8](docs/08-CLONE-ROADMAP.md#8-licensing--decide-before-writing-code) must be settled
  before anything is published.

---

## 7. Ten minutes, one page

If you read nothing else, read these three things:

1. [00 §2 — The eleven findings that matter most](docs/00-EXECUTIVE-SUMMARY.md#2-the-eleven-findings-that-matter-most)
2. [03 — The 94-row command table](docs/03-commands-quests-economy.md) (the single most
   actionable artefact in the whole set)
3. [08 — The clone roadmap](docs/08-CLONE-ROADMAP.md) (six workstreams, ten milestones,
   and the cheat battery the new server has to pass)

Then come back to [09](docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md) before you promise
anyone a date.
