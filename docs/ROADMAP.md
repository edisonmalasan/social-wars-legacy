# Social Wars Legacy — Roadmap

> **Purpose:** the complete, outcome-based guide from "nothing built" to "a production-ready
> cross-platform client-server game with a standalone desktop executable".
>
> **Deep analysis:** [`re/docs/08-CLONE-ROADMAP.md`](../re/docs/08-CLONE-ROADMAP.md) ·
> **Document map:** [`re/README.md`](../re/README.md) ·
> **Open questions:** [`re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md)

---

## Status Rules

- `[ ]` = not yet verified as complete. `[x]` = implemented **and verified**.
- **Not started:** no required items verified. **In progress:** some required items pending.
  **Complete:** all required items verified.
- **Deferred:** intentionally excluded from the current milestone.
- The agent must check actual implementation/tests before marking an item complete; if
  evidence is missing, leave it unchecked and note the uncertainty.
- Each checkbox should describe an **observable, testable outcome**, not a class name,
  code snippet, or implementation technique.
- Follow approved priorities; do not assume the next unchecked item is automatically
  authorized work.
- **Exit criteria** at the end of each group are the gate for starting the next one.

---

## Locked Decisions & Non-Negotiables

*Decisions already made and the findings that constrain the implementation. Changing any of
these requires a written rationale and a roadmap amendment.*

### Architecture

| Decision | Rationale |
|---|---|
| **TypeScript monorepo** (pnpm workspaces) | One language for the rules engine, server and client; shared protocol types with zero drift |
| **Rules engine in TypeScript, deterministic and seeded** | The 229 unit delegates (1.32 MB of bespoke AS3) must be iterated against the original client; iteration speed dominates. The same engine must run in Node (multiplayer) and in a browser worker (offline) |
| **Server-authoritative simulation** | Combat, resource costs and rewards must be decided by the server. The client renders and requests, never decides |
| **Client = PixiJS v8 (WebGL2) world + React DOM UI** | Pixi batches thousands of sprites, filters and particles; React handles the ~60–80 text-heavy panels far better than a canvas |
| **Tauri v2 desktop shell** wrapping the same web client | Native window/menus/tray, no Chromium version drift, small installer overhead. *Fallback: Electron if WebView2/WebGL2 proves problematic on a target platform* |
| **One web client → web, desktop (Tauri) and mobile (Capacitor)** | The client is the single source of truth for presentation |
| **PostgreSQL + Drizzle for the server; the same schema over PGlite for offline play** | One schema, one query layer, no second persistence dialect to maintain |
| **Git LFS for binary assets** | `assets/` is 716.8 MB; LFS keeps the repository at pointers while `git lfs pull` restores content |

### Findings that constrain the implementation

| # | Finding | Consequence for the build |
|---|---|---|
| F1 | The original server signing key is `Config.SERVER_KEY = "4vVSD8dftv6hdfb1Hnk9"` — **verified live** | The compatibility shim must sign requests exactly this way. The new native protocol does not need it, but the shim does |
| F2 | The command tuple is `[map_id, cmd, args[], res[8]]` with the resource vector ordered **`[energy, xp, gold, wood, oil, steel, cash, mana]`** — verified live by observing the UI counters move | Any re-implementation of the wire format must preserve this order exactly |
| F3 | The 8-slot `res` vector is **client-declared** and the upstream server applies it verbatim | The new server must compute every delta itself. This is the single most important behavioural change |
| F4 | `flash_debug` overwrites the whole wallet from client arguments — captured live | **Must not exist** in the new server |
| F5 | Combat is **100 % client-side**; `end_quest`/`end_attack` carry the entire outcome | The new server re-simulates from a server-issued seed and ignores the client's claimed outcome |
| F6 | `first_number` is a **global command index**, not a batch counter | The protocol shim must tolerate gaps (commands generated but dropped) |
| F7 | `config/main.json` is the **29-Aug-2012** original server capture plus 5 JSON-Patch deltas (778 → 900 items, 104 → 105 globals) | The content pipeline must apply the patches, not just copy the JSON |
| F8 | The client knows **123 item ids the config has never heard of** (199, 302, 1307–1431) | Content reconciliation is a required deliverable, not optional |
| F9 | `best_against` is a *property key*, not a class; only **4** items carry a real multiplier (Mortar 10×, Antiaircraft 20×, B52 5×, Demolition Tank 15×) | The counter system is small and must be modelled exactly as "attacker counters a target *property*", not as unit classes |
| F10 | The upstream server has **no authentication**: `USERID` comes from the request body; `user_key` and `accessToken` are read and discarded | The new server replaces all three with real auth |
| F11 | `constants.py` has **duplicate dict keys**; quests `100000024/25/26` resolve to the wrong names | The quest-name table is rebuilt from `villages/quest/` filenames, not copied |
| F12 | The upstream `build/build.bat` points `--add-data "..\..\assets"` **outside the repo** | Never reuse the upstream build scripts |

### Hard constraints

| Constraint | Consequence |
|---|---|
| **GPL v3** covers the upstream *code* | The vendored `upstream/` tree stays GPL v3 and is not linked into the new client's source. The new project ships its own licence, with the upstream kept as a clearly-marked GPL component |
| **Zynga owns the sprites, audio and config** | Asset licensing must be settled **before any public release** (see Group I). Until then, builds are private |
| The original Flash client is a **test fixture, not a runtime dependency** | The shipped desktop app must never require Flash, a Flash plugin or a Flash browser |

---

## Group 0 — Investigation & Documentation ✅

*Outcome: everything needed to rebuild the game as a cross-platform client-server
application is written down, evidenced, and navigable.*

- [x] The Flash client is fully decompiled and the 1 387 AS3 classes are analysed
      ([`re/docs/02`](../re/docs/02-combat-and-units.md), [`re/docs/03`](../re/docs/03-commands-quests-economy.md))
- [x] The network protocol is documented end to end, including the recovered HMAC key
      ([`re/docs/01`](../re/docs/01-network-protocol.md))
- [x] The HMAC key is **verified against live traffic** from a real Adobe Flash Player
      ([`re/evidence/live/hmac-verification.txt`](../re/evidence/live/hmac-verification.txt))
- [x] The save format and game-config pipeline are documented
      ([`re/docs/04`](../re/docs/04-python-server-and-data.md))
- [x] The asset tree is inventoried and mapped to every config item
      ([`re/docs/05`](../re/docs/05-assets-and-content-pipeline.md))
- [x] A live session is captured and reproducible (1 664 requests, 294 paths, 34 command
      batches, 17 command names) ([`re/docs/06`](../re/docs/06-LIVE-SESSION-PROTOCOL.md))
- [x] The `end_quest` battle report is captured from a live Mission 1 assault
      ([`re/evidence/live/command-payloads.txt`](../re/evidence/live/command-payloads.txt))
- [x] REA's contribution and its coverage limits are recorded
      ([`re/docs/07`](../re/docs/07-REA-EVIDENCE.md))
- [x] The rewrite plan, risks and open questions are written
      ([`re/docs/08`](../re/docs/08-CLONE-ROADMAP.md), [`re/docs/09`](../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md))
- [ ] The PvP `end_attack` payload is captured from a live player attack — folded into
      Group B8

**Status:** Complete (one item moved to B8).

---

## Group A — Vendor & Provenance

*Outcome: the upstream project is vendored inside this repository, verifiably unmodified
and unambiguously licensed, without bloating the git history.*

- [ ] `upstream/socialwarriors/` contains the upstream tree **byte-for-byte**, verified
      against a SHA-256 manifest of all 3 292 files
- [ ] `upstream/PROVENANCE.md` records the upstream remote, the pinned commit
      (`c3fceeb1f8e93734a293b9bc25ae6025656f6822`), the `0.01a`/`0.02a` tags, the GPL-v3
      licence text, and the per-directory file counts and byte totals
- [ ] `upstream/socialwarriors/.gitattributes` puts `assets/**` under Git LFS, and
      `git lfs ls-files` lists every vendored binary
- [ ] The repository working tree stays under 100 MB with assets present as LFS pointers,
      and `git lfs pull` restores all 716.8 MB byte-for-byte
- [ ] A `scripts/verify-upstream.mjs` command re-checks every vendored file against the
      manifest and exits non-zero on any drift
- [ ] The 58 `Basesec_1.5.x.swf` builds (239.7 MB) are stored under a separate LFS path so a
      clone build can pull only `Basesec_1.5.4.swf` + `SWLoader.swf` (4.5 MB)
- [ ] The upstream tree is never edited in place; any derived artefact lives outside
      `upstream/` and is reproducible from it

**Exit criteria:** `git clone` → `git lfs pull` → `scripts/verify-upstream.mjs` passes with
zero differences.

---

## Group B — Complete the Evidence Sweep

*Outcome: every remaining behaviour of the original client is captured as structured,
machine-readable specification — not prose, not inference.*

This group exists because the 1.32 MB of unit delegates, the 28 quest classes and the 403
UI classes are the **specification** of the game. Porting from them without capturing them
first means guessing at the rules being cloned.

### B1 — Client version history (58 builds)

- [ ] `Config.as` is extracted from **all 58** `Basesec_1.5.x.swf` builds and diffed
- [ ] A report states whether `SERVER_KEY` is constant across the whole 1.4.5 → 1.5.4
      history, with the exact commit range where it changed (or proof it never did)
- [ ] The client-side protocol evolution is charted: new endpoints, new commands, new
      globals, new flashvars, per build
- [ ] `assets/flash/Debug_1.5.4.swf` is compared against `Basesec_1.5.4.swf` to explain the
      difference

### B2 — Complete SWF corpus

- [ ] **All 1 176 SWF files** are decompiled and indexed, not just Basesec's 1 387 classes
- [ ] A searchable class index exists: SWF → class → package → file, with line counts
- [ ] Every `DefineScript`/`DoABC` name in the corpus is mapped to a subsystem
- [ ] `assets/swf/dynamic2.swf` is analysed for what it dynamically loads at runtime

### B3 — Unit and building behaviour tables (the rules-port spec)

- [ ] All **229 unit delegates** are reduced to a table of: stat overrides, special attacks
      used, damage types applied, targeting preferences, on-death/on-hit behaviour
- [ ] All **56 building delegates** are reduced to a table of: production, capacity,
      activation, garrison rules, upgrade behaviour
- [ ] The table is emitted as JSON and is the input to the rules-engine implementation
- [ ] Every special-attack class (15) and attack condition (6) has a documented
      precondition, effect and lifetime

### B4 — Quest win conditions

- [ ] All **28 quest classes** are reduced to: spawn conditions, objective, victory test,
      failure test, rewards, difficulty scaling
- [ ] The quest-id → name mapping is rebuilt from `villages/quest/` filenames, correcting
      the `constants.py` duplicate-key bug (F11)
- [ ] The chapter/objective system (`idSimpleChapter` and friends) is specified as a state
      machine

### B5 — Goal specification

- [ ] All **34 goal classes** are reduced to a table of: trigger, progress metric,
      completion condition, reward
- [ ] The client registers **134 goal ids** while the 2012 config defines only **91**: the
      reconciliation (which ids exist in one and not the other, in both directions) is
      recorded as data

### B6 — UI screen inventory (the modern client's UI spec)

- [ ] All **403 UI classes** (95 popups, 57 GUI, 251 top-level MovieClips) are inventoried:
      screen name, purpose, contents, entry point, exit conditions
- [ ] Each is classified as *gameplay-critical*, *cosmetic* or *droppable*
- [ ] The inventory becomes the modern client's UI backlog, so no screen is discovered late

### B7 — Social layer contracts

- [ ] The 11 `alliance/?method=…` variants are recovered from the AS3 and specified
- [ ] The marketplace and unit-bidding flows are specified
- [ ] The `bets/*` auction routes are specified (the upstream server has them commented out)
- [ ] The premium-account and offer-pack purchase flows are specified

### B8 — Remaining live captures

- [ ] The PvP `end_attack` payload is captured from a live player attack
- [ ] The `attack_player` / `spy_player` command payloads are captured live
- [ ] The alliance and marketplace request/response shapes are captured live where the
      local server can exercise them

### Output contract for Group B

- [ ] Every B-item produces a document in `re/docs/` **and** a machine-readable JSON/CSV
      artefact under `re/data/`, so implementation consumes data rather than prose
- [ ] `re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md` is updated: every closed gap is
      removed, every remaining gap is listed with its impact on the build

**Exit criteria:** the rules-engine backlog (B3/B4/B5) and the UI backlog (B6) are
machine-readable and complete enough to implement from.

---

## Group C — Monorepo & Content Pipeline

*Outcome: a single repository builds a typed content bundle and a workspace that the rest
of the project lives in.*

- [ ] A pnpm workspace exists with `packages/protocol`, `packages/content`,
      `packages/rules`, `apps/server`, `apps/client`, `apps/desktop`, `tools/*`
- [ ] `packages/protocol` defines types for the full command set, the resource vector
      order (F2) and the save document, and both client and server import them
- [ ] `packages/content` builds a content bundle from `config/main.json` + the 5 JSON-Patch
      deltas, applying them in the documented order
- [ ] The content bundle validates against a schema and **the build fails** on an unknown
      key or a dangling id
- [ ] The bundle build is **reproducible**: the same inputs produce a byte-identical
      bundle, and the hash is recorded
- [ ] The darts schedule rotates weekly and remains correct after a simulated year
- [ ] The 123 client-only item ids are reconciled: each is either given config data
      reconstructed from its delegate, or explicitly excluded with a recorded reason
- [ ] The 41 distinct `properties` keys and the 24 `subcat_functional` values are typed and
      documented in the bundle
- [ ] Every content item resolves to an asset reference or is explicitly marked
      asset-less
- [ ] `packages/rules` exposes a pure, side-effect-free simulation API with no `Date.now()`
      and no unseeded randomness
- [ ] CI runs typecheck, lint, unit tests and the content build on every push

**Exit criteria:** `pnpm build` produces a validated, hashed content bundle and a green
CI run.

---

## Group D — Asset Pipeline

*Outcome: the game's art and audio exist as non-Flash, renderable, versioned artefacts.*

- [ ] All **1 116 SWF files outside `assets/flash/`** (376.4 MB: 862 sprites, 205 FX, 26
      character, 10 magic, 9 intro/image, 2 font, `dynamic2.swf`, 1 externalised) are
      converted to PNG frame sequences with a frame table naming each (sprite, frame) pair —
      `ffdec -export frame`, **not** `-export shape` (whose fills are base64 PNG patterns,
      not paths)
- [ ] Frames are packed into atlases with a manifest mapping sprite + frame → atlas region
- [ ] The 58 `Basesec_1.5.x.swf` builds (239.7 MB) are handled separately: `Basesec_1.5.4.swf`
      is the only one converted (it is the reference client, not game art)
- [ ] The 1 314 thumbnails are indexed by item id and served as the inventory icon set
- [ ] The 139 config sounds resolve to playable audio; the 2 disk-only music beds are
      wired
- [ ] The 607 localised images and 578 image files are packaged per language
- [ ] The 4 proprietary fonts are replaced with permissively-licensed equivalents and the
      text metrics are tuned to match
- [ ] The 73 missing asset references (10 sprites, 29 thumbs, 34 chapter/intro images) are
      resolved, or permanently documented as unavailable with a visual fallback
- [ ] The 722 asset files unreferenced by the config are triaged: adopted, archived, or
      documented
- [ ] A viewer exists that renders every item at 3 zoom levels, so missing art is visible
      immediately
- [ ] The client can be built with a **content-hashed** asset bundle, so a stale cache is
      impossible

**Exit criteria:** every shippable item id renders in the viewer with no missing frame.

---

## Group E — Rules Engine

*Outcome: the game simulation is reproducible server-side and matches the original
client's observable behaviour.*

### E1 — Combat

- [ ] The 8-stage damage pipeline (shield → counter → attack modifier → global multiplier →
      unit XP → siege → tutorial → crit/variance → defence → clamp) is implemented
- [ ] Attack cadence matches: `attack_interval` is frames at 30 fps, units take a random
      0–4 frame phase, buildings fire in global lockstep
- [ ] Range rules match: units use `attack_range + max(0, targetWidth − 2·attack_range)`,
      buildings use the exact `attack_range`
- [ ] Targeting matches the score (`1000−distance`, +150 unit, +100 town hall, +75
      collectable, +50 attacker), including the untargetable rules
- [ ] The 4 real counters reproduce exactly: Antiaircraft 20× vs `ft_flying`,
      Demolition Tank 15×, Mortar Thrower 10×, B52 5× vs `ft_building`
- [ ] All 10 damage classes and all 15 special attacks behave as documented
- [ ] A building's own attack scales by `garrison / unit_capacity` — an empty bunker deals
      0, and a bunker fires once per garrisoned unit
- [ ] Unit XP accrues from effective damage to units only, with the documented thresholds
      and the level-9 cap (+30 attack, 3× HP)

### E2 — Economy and buildings

- [ ] Resource caps, the 5/60/240/480-minute collect tiers with their multipliers, and the
      peasant multiplier are enforced
- [ ] Population, energy (max 30, +1 per 5 min), expansion unlocking and town-hall costs
      are correct
- [ ] Build costs, build times, upgrade chains and the "click to build" mechanic are correct
- [ ] The market (20 trades / 20 h, +2 % per trade, 75 % sell rate), daily bonus cycle
      and Monday-bonus cycle are correct
- [ ] The darts minigame (25 targets, 20 cash per paid shot, weekly prize rotation) is
      correct

### E3 — Quests and goals

- [ ] The quest state machine and all 28 quests' win/fail conditions are implemented
- [ ] All 134 goals evaluate server-side, with at most 5 active
- [ ] Daily bonus, weekly bonus, premium expiry and goal completion are each awarded **once**

### E4 — Determinism and verification

- [ ] The simulation is deterministic given a seed; the same seed and inputs produce the
      same outcome on any machine
- [ ] A **golden-master harness** diffs the rules engine against the original Flash client:
      the same action produces the same state change
- [ ] The harness runs in CI on a fixed corpus of scenarios
- [ ] Combat is resolved server-side from a server-issued seed; the client's claimed outcome
      is ignored and cannot change the result

**Exit criteria:** the golden-master corpus passes with zero unexplained differences.

---

## Group F — Authoritative Server

*Outcome: the server is safe, concurrent, persistent, and speaks both the new native
protocol and the original dialect.*

### F1 — Identity and authority

- [ ] Players authenticate with a real credential; a session token replaces the
      `USERID`-in-the-body model (F10)
- [ ] Every command's resource cost is computed by the server, never accepted from the
      client (F3)
- [ ] `flash_debug` does not exist in the server (F4)
- [ ] Combat outcomes are re-simulated server-side (F5)
- [ ] Goal completion, daily bonus and premium expiry are evaluated server-side
- [ ] The full cheat battery is rejected or has no effect: inflated `res`, forged
      `flash_debug`, replayed `win_daily_bonus`, self-completed goals, forged
      `end_attack`, free `buy_offer_pack`, wrong HMAC, another player's `USERID`,
      malformed framing, forged `win`, over-collection

### F2 — Protocol

- [ ] The native command API is versioned, typed and documented
- [ ] A **compatibility shim** speaks the original `command.php` dialect — including the
      64-hex HMAC framing (F1) — so the untouched `Basesec_1.5.4.swf` plays against this
      server with no client change
- [ ] The shim tolerates `first_number` gaps (F6) and the `skiphash12341` response-hash
      bypass
- [ ] The shim serves `get_game_config.php` with the patched, darts-rotated content and
      `get_player_info.php` with own/neighbour/quest map flavours

### F3 — Persistence

- [ ] State is stored in PostgreSQL with transactional command application; concurrent
      commands cannot corrupt a player
- [ ] The save document format is migrated from the upstream schema (12 `playerInfo` +
      28 `maps[]` + 47 `privateState` fields) with a tested, versioned migration path
- [ ] Schema migrations are forward-only, reversible where safe, and run as part of deploy
- [ ] A backup and restore procedure exists and has been exercised against a real snapshot

### F4 — Robustness

- [ ] Bad input returns typed 4xx responses, never a 500
- [ ] Every endpoint has request-size limits, rate limits and timeouts
- [ ] The server survives a client disconnect mid-command without partial state
- [ ] A soak test of sustained play shows no memory growth and no state drift

### F5 — Social layer

- [ ] Alliances, marketplace and the auction/betting subsystem are implemented per the
      Group B7 contracts, or are explicitly and visibly out of scope

**Exit criteria:** the original Flash client can complete the tutorial and a Mission 1
assault against the new server, and the cheat battery is fully rejected.

---

## Group G — Modern Client

*Outcome: the game is fully playable on desktop and mobile with no Flash anywhere.*

### G1 — World rendering

- [ ] The isometric tile map renders with correct elevation, z-sorting and the
      server-authoritative item positions
- [ ] Every unit and building animates from its atlas frames, with correct frame timing
- [ ] Projectiles, particles and the 205 FX assets render
- [ ] Depth sorting and occlusion match the original engine
- [ ] The map pans, zooms and re-centres as the original does

### G2 — Interaction

- [ ] Selection, movement, building placement, training queues, collecting and upgrading
      all work through the command API
- [ ] The client never decides an outcome; it requests and renders the server's answer
- [ ] Input latency is hidden by local interpolation without ever showing an unconfirmed
      outcome as final

### G3 — The UI (rebuilt from scratch)

- [ ] Every screen in the B6 inventory is implemented, or explicitly dropped with a
      recorded decision
- [ ] The HUD (resources, level, population, energy), build menu, unit panel, minimap,
      neighbour strip, goal panel and popups all work
- [ ] Tooltips, tutorials and the "click here" guidance system are reimplemented
- [ ] Text renders with the substituted fonts at the original metrics

### G4 — Feature parity

- [ ] The tutorial and the first chapter are completable
- [ ] Quests, goals, the darts minigame, magic and tech, the marketplace, premium and the
      weekly bonus are functional
- [ ] Alliances and the social features are functional, or visibly out of scope
- [ ] The daily/weekly bonus cycles and premium expiry behave correctly across a
      server restart

### G5 — Clients

- [ ] The web build runs in Chrome, Edge, Firefox and Safari
- [ ] The desktop build (Tauri) runs on Windows, macOS and Linux
- [ ] The mobile build (Capacitor) runs on Android and iOS
- [ ] The game is playable at the original resolutions and scales cleanly to phone screens

**Exit criteria:** a new player completes the tutorial and a quest in every shipped client.

---

## Group H — Desktop Shell & Release

*Outcome: a standalone, signed, updatable desktop executable.*

- [ ] The Tauri shell launches the client, manages the window, and exposes the local
      persistence layer
- [ ] **The app never requires Flash, a Flash plugin or a Flash browser** — verified by
      running on a machine with no Adobe Flash Player installed
- [ ] The game works with the server on `localhost` and against a remote server
- [ ] Offline single-player works via the in-browser rules engine over PGlite, with the
      same schema as the server
- [ ] Installers are produced for Windows (`.msi` + `.exe`), macOS (`.dmg`) and Linux
      (`.deb`/`.AppImage`)
- [ ] The binaries are code-signed, and the macOS build is notarised
- [ ] Auto-update is configured, and a failed update rolls back cleanly
- [ ] The shipped client contains **no** Adobe Flash Player component and no SWF runtime

**Exit criteria:** a clean machine installs the app and plays the game.

---

## Group I — Production Readiness

*Outcome: the project can be operated, secured, observed and released like a real
product.*

### I1 — Testing

- [ ] Unit tests cover the rules engine, the economy and the command handlers
- [ ] The golden-master harness runs in CI and is a release gate
- [ ] Integration tests cover the full command surface against a real database
- [ ] End-to-end tests drive the web client through a complete play session
- [ ] A load test sustains the target concurrency with correct simulation timing
- [ ] Test coverage is measured and a threshold is enforced

### I2 — CI/CD

- [ ] Every push runs typecheck, lint, unit, integration and the content/asset build
- [ ] Every pull request runs the golden-master harness
- [ ] Branches are protected and require a green run plus review
- [ ] Release artefacts are produced automatically and published to a release
- [ ] The pipeline is reproducible and re-running it yields the same artefacts

### I3 — Security

- [ ] Secrets are managed outside the repository, and no credential is committed
- [ ] Dependency and container scanning run in CI, with a policy for what blocks a release
- [ ] All input is validated at the boundary; the server has no injection surface
- [ ] Rate limiting and abuse protection are in place on every mutating endpoint
- [ ] Session tokens are scoped, revocable and expire
- [ ] A security review of the auth, command and shim layers is completed
- [ ] The **client is not trusted for anything** — the cheat battery is re-run on every
      release

### I4 — Observability

- [ ] Structured logs with a request id that ties a client action to a server command
- [ ] Metrics for latency, command throughput, error rate, simulation tick time and
      active sessions
- [ ] Distributed tracing across the client, the API and the database
- [ ] Error reporting captures crashes with build and content version attached
- [ ] Alerts fire on error-rate, latency and tick-time regressions
- [ ] A dashboard shows live server health and the content/asset version in use

### I5 — Operations

- [ ] Deployment is scripted, repeatable and reversible
- [ ] Database migration runs as a gated deploy step, with a tested rollback
- [ ] Backups run automatically, are verified, and a restore has been rehearsed
- [ ] A runbook covers: stalled deployment, database failure, corrupted player state,
      content-bundle rollback and emergency player reset
- [ ] A documented procedure exists for pushing a hotfix to the rules engine

### I6 — Legal & licensing

- [ ] **The asset licensing position is settled and written down** — either a licence, a
      documented archival exemption, or a decision to clean-room the art
- [ ] The vendored upstream tree keeps its GPL-v3 notices and is not linked into
      proprietary source
- [ ] Third-party asset licences (fonts, audio, textures) are enumerated and compliant
- [ ] The attribution and preservation notices the original project makes are carried
      forward

### I7 — Documentation

- [ ] A developer guide covers the architecture, the content pipeline, the asset pipeline
      and the rules engine
- [ ] A runbook covers operating the server and the desktop build
- [ ] A user guide covers installing and playing
- [ ] The `re/` report set is kept in sync with the implementation
- [ ] Every architectural decision has a written rationale (ADR)

### I8 — Performance & release

- [ ] Performance budgets are defined and met: input-to-render latency, simulation tick
      time, memory and client frame rate
- [ ] The client holds a stable frame rate on the largest documented battle
- [ ] The asset bundle size is measured and minimised
- [ ] A release checklist is followed for the first production release
- [ ] The first production release is published, monitored for a full cycle, and any
      rollback path is proven

**Exit criteria:** the game is running in production under real players, monitored, backed
up, licensed and documented.

---

## Deferred / Future Work

*Intentionally postponed outcomes, with the reason.*

- [ ] Facebook / social-point integration — the original `graph.facebook` calls are inert
      in this build and the token is a frozen literal
- [ ] Recovering the original PHP backend or the 2012 response-hash scheme — the
      compatibility shim does not need them because `skiphash12341` disables response
      verification
- [ ] Recovering the missing `Basesec` builds (1.4.7 and others) or the 73 missing assets
      — believed unrecoverable without an archival source
- [ ] A 3D re-implementation — the original is 2D isometric; there is no evidence for 3D
      intent
- [ ] Clean-room re-creation of the art, to avoid the Zynga licence entirely — the
      fallback if I6 cannot be resolved in the client's favour

---

## Status Summary

| Group | Milestone | Status |
|---|---|---|
| 0 | Investigation & Documentation | Complete (1 item moved to B8) |
| A | Vendor & Provenance | Not started |
| B | Complete the Evidence Sweep | Not started |
| C | Monorepo & Content Pipeline | Not started |
| D | Asset Pipeline | Not started |
| E | Rules Engine | Not started |
| F | Authoritative Server | Not started |
| G | Modern Client | Not started |
| H | Desktop Shell & Release | Not started |
| I | Production Readiness | Not started |

### Critical path

```
A ──► B ──► C ──► D ──┐
         │             ├──► E ──► F ──► G ──► H ──► I
         └─────────────┘
```

* **B3/B4/B5 gate E.** The rules engine cannot be written from prose.
* **B6 gates G.** The UI backlog must exist before the UI is built.
* **E gates F.** The server has nothing to be authoritative about until the rules exist.
* **F gates G.** The client renders server state; there is nothing to render before F.
* **I6 gates public release.** Not the build — the *publication*.

### Parallelisable work

* B1–B8 are mutually independent and can run concurrently.
* D (asset pipeline) and E (rules engine) are independent once C is done.
* Within G, the renderer (G1) and the UI (G3) can proceed in parallel against the B6
  inventory.

---

## Maintenance

- Revisit this roadmap when scope or priorities change.
- Update statuses only after verification; distinguish untested from failed.
- Keep implementation details in code, code review, or a task-specific plan — not here.
- Preserve reasons for significant technical decisions in
  [`re/docs/08-CLONE-ROADMAP.md`](../re/docs/08-CLONE-ROADMAP.md) and
  [`re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md).
- The **Locked Decisions** section is binding. Amending it requires a written rationale and
  an update to the affected groups.
