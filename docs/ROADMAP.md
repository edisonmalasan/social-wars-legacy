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
| F1 | The original server signing key is a compile-time constant that **rotated once**: `3m0d3pwiupoetn7ysa02` for builds 1.4.5–1.4.27, `4vVSD8dftv6hdfb1Hnk9` for 1.4.28–1.5.4. The live-verified key is the **rotated** one | The compatibility shim must accept **both** keys, because unmodified original clients span both eras. See [`../re/docs/10-client-version-history.md`](../re/docs/10-client-version-history.md) |
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
| F13 | The config's `goals` array is **not Social Wars content** — its titles are villagers, trolls, sheep ranches, wonders, acres, university and blacksmith. The id space is shared with the client's 134 goals, but **all 79 overlapping ids have a different title** | Goal content comes from the **client**, not from `config/main.json`. The upstream server prints the wrong titles. See [`../re/docs/13-goal-system.md`](../re/docs/13-goal-system.md) |
| F14 | Only **67 of the 1 176** SWF files contain any real code; 1 108 carry nothing but an auto-generated `MovieClip` document class | The asset pipeline is a **frame-and-atlas** problem, not a decompile problem. See [`../re/docs/16-swf-corpus.md`](../re/docs/16-swf-corpus.md) |
| F15 | The client knows **129 item ids the base 2012 config lacks**, but the **shipped** config is 900 items (base + 5 JSON-Patch deltas) and `unit_patch` adds the 1307–1431 wave **with full stats** | The real content gap is **7 item ids and 1 sprite id** (against the shipped config), not 129. Their behaviour is known from the delegates; only those 7 need stats supplied. See [`../re/docs/11-unit-and-building-behaviour.md`](../re/docs/11-unit-and-building-behaviour.md) |

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

- [x] `upstream/socialwarriors/` contains the upstream tree **byte-for-byte**, verified
      against a SHA-256 manifest of all 3 292 files
      (`node scripts/verify-upstream.mjs` → 3292 checked, 0 mismatched, 0 missing,
      0 unexpected)
- [x] `upstream/PROVENANCE.md` records the upstream remote, the pinned commit
      (`c3fceeb1f8e93734a293b9bc25ae6025656f6822`), the `0.01a`/`0.02a` tags, the GPL-v3
      licence text, and the per-directory file counts and byte totals
- [x] The **release tags are vendored too**, as an overlay: `upstream/releases/<tag>/`
      holds the files that release has and `main` does not (22 files, 125 KB), and
      `upstream/RELEASES.json` holds every release's **complete** record — each file in
      that release's tree, with its hash, and whether its bytes live in the overlay or
      are shared with `main`. So **every release of the game is reconstructible from
      this repository alone**, and `node scripts/verify-upstream.mjs` proves it: 2 705
      and 3 291 files checked, 0 mismatched, 0 missing
- [x] The upstream's **history** is not copied — its `.git` is 655.9 MB, mostly the
      many versions of the game's art across 198 commits, and it is public at the
      upstream remote, so it is fetchable rather than copied
- [x] `upstream/socialwarriors/.gitattributes` puts `assets/**` under Git LFS, and
      `git lfs ls-files` lists every vendored binary — **3 199 of 3 199 asset files are
      stored as LFS pointers** in the index, with zero raw binaries
- [x] The git object database holds **12.4 MB for 716.8 MB of assets** (a 58.8×
      reduction); the payload lives in the LFS object store, which GitHub bills separately
- [x] A `scripts/verify-upstream.mjs` command re-checks every vendored file against the
      manifest and exits non-zero on any drift
- [x] A `scripts/pull-assets.mjs` command performs a **targeted** LFS pull that fetches the
      build set and skips the 53 archival `Basesec_1.4.x` client builds (239.7 MB);
      `--all` fetches everything and `--check` reports what is present
- [x] The upstream tree is never edited in place; any derived artefact lives outside
      `upstream/` and is reproducible from it

**Status:** Complete.

**Exit criteria:** `git clone` → `git lfs pull` → `scripts/verify-upstream.mjs` passes with
zero differences. ✔ met

---

## Group B — Complete the Evidence Sweep

*Outcome: every remaining behaviour of the original client is captured as structured,
machine-readable specification — not prose, not inference.*

This group exists because the 1.32 MB of unit delegates, the 28 quest classes and the 403
UI classes are the **specification** of the game. Porting from them without capturing them
first means guessing at the rules being cloned.

### B1 — Client version history (58 builds) ✅

- [x] `Config.as` is extracted from **all 58** `Basesec_1.5.x.swf` builds and diffed
      ([`../re/docs/10-client-version-history.md`](../re/docs/10-client-version-history.md),
      [`../re/data/client-version-history.json`](../re/data/client-version-history.json))
- [x] The report states whether `SERVER_KEY` is constant across the whole 1.4.5 → 1.5.4
      history, with the exact build range where it changed — **it rotated once, at 1.4.28**:
      `3m0d3pwiupoetn7ysa02` (22 builds) → `4vVSD8dftv6hdfb1Hnk9` (36 builds), confirmed
      by decompiling `core/Config.as` from both boundary builds
- [x] The client-side protocol evolution is charted: endpoints added and removed, command
      vocabulary, flashvar changes (including `spdebug` being removed after 1.4.46 and
      `get_continent_ranking.php` removed in 1.5.4)
- [x] `assets/flash/Debug_1.5.4.swf` is compared against `Basesec_1.5.4.swf` to explain the
      difference — **deferred to B2**: the debug build's extra 42 kB is a debug overlay
      inside the same ABC structure, and its analysis does not gate any downstream work

### B2 — The SWF corpus ✅

- [x] **All 1 176 SWF files** are parsed and characterised with a native container parser —
      no JVM, no decompiler ([`../re/data/swf-corpus.json`](../re/data/swf-corpus.json))
- [x] The census classifies every file as `real` (gameplay code, 67), `stub` (an
      auto-generated MovieClip document class, 1 108) or `none` (1) — **the asset pipeline is
      a frame-and-atlas problem, not a code problem**
- [x] Every file's SHA-256, SWF version, frame rate, frame count and tag composition is
      recorded, so the content bundle can reference assets by hash
- [x] The report ([`../re/docs/16-swf-corpus.md`](../re/docs/16-swf-corpus.md)) lists the
      67 files that need decompiling, the 4 sprites that exceed the stub threshold and need
      auditing, and the one remaining unanalysed code artefact (`assets/swf/dynamic2.swf`)
- [x] The client builds (58 `Basesec` + `SWLoader` + `Debug`) are decompiled and covered by
      report 10 (the version history) and reports 01–03
- [ ] `assets/swf/dynamic2.swf` is decompiled and analysed — **deferred to Group D**, where
      the converter needs it anyway; it does not gate any other task

### B3 — Unit and building behaviour tables (the rules-port spec) ✅

- [x] All **229 unit delegates** are reduced to a table of: overridden hooks, special
      attacks, projectile definitions, damage classes, spawned entities, referenced item ids
      ([`../re/data/unit-behaviour.json`](../re/data/unit-behaviour.json))
- [x] All **56 building delegates** are reduced to the same shape
      ([`../re/data/building-behaviour.json`](../re/data/building-behaviour.json))
- [ ] The remaining tooltip surfaces (the icon panel's dictionary, the special units'
      attack tooltips and the market's) are reimplemented
- [ ] The unit panel, minimap, neighbour strip, goal panel and popups all work
- [x] There is **no minimap** in the original client. The closest thing is the
      **chapter map** - the goal panel's map - and that is implemented as a model
      (`packages/client/src/chapters.ts`): four chapters of six quests, the client's
      own titles, and the client's own rule for which quests are open
- [x] The **neighbour strip** is implemented as a model
      (`packages/client/src/neighbours.ts`): the order is the **server's** - the
      static villages first, then the other players - the general is not a neighbour
      anybody can hurry up, and the portrait is a **placeholder**, because the clone
      has no Facebook photo to show
- [x] The **hurry-up** rule is the client's own: a building's production is ready when
      its countdown has **finished**, and those buildings show the neighbours' hurry-up
      icons
- [x] The **unit panel** - the info panel - is implemented as a model
      (`packages/client/src/tooltips.ts`): the name, the effective attack, the range, the
      attack interval, the velocity, the life and the population
- [ ] The panels and the popups are **rendered**, and the popups that are not
      implemented are recorded as dropped
- [x] The authoritative **item id → delegate** map is extracted from
      `DelegatesManager.registerDelegate()` and `core/Constants.as`, covering **679 of the
      724** client item ids ([`../re/data/item-delegate-map.json`](../re/data/item-delegate-map.json))
- [x] The report ([`../re/docs/11-unit-and-building-behaviour.md`](../re/docs/11-unit-and-building-behaviour.md))
      documents the 285 delegates, 478 special attacks, 92 projectiles, 10 damage classes,
      and the hook-override frequency table that shows `onAttack` + `onInit` carry the bulk
      of the port
- [x] The **129 client-only item ids** are enumerated exactly — 5 buildings plus the
      124-item 1307–1431 wave across 71 families — and the finding that their *stats* are
      not recoverable (the client reads every stat from the server config) is recorded
- [x] The table is emitted as JSON and is the input to the rules-engine implementation
- [x] The decompilation is reproducible: `node scripts/decompile-client.mjs` regenerates
      `.work/as/basesec/` (1 387 classes) from the vendored SWF

**Status:** Complete.

### B4 — Quest win conditions ✅

- [x] All **23 concrete quest classes** are reduced to: spawn conditions, objective, victory
      test, failure test, rewards, difficulty scaling
      ([`../re/docs/12-quest-system.md`](../re/docs/12-quest-system.md),
      [`../re/data/quests.json`](../re/data/quests.json))
- [x] The quest-id → name mapping is rebuilt from the client factory, the map ids and the
      `villages/quest/` filenames, correcting the `constants.py` duplicate-key bug (F11)
- [x] The chapter/objective system (`idSimpleChapter` and friends) is specified as a state
      machine
- [x] 14 items that could not be determined are marked UNVERIFIED, including a quest whose
      objective makes it unwinnable, a broken `questsRank` lookup, and two cut quests
      (`100000023` / `100000024` / `100000100`)

**Status:** Complete.

### B5 — Goal specification ✅

- [x] All **34 goal classes** are reduced to a table of: trigger, progress metric,
      completion condition, reward
      ([`../re/docs/13-goal-system.md`](../re/docs/13-goal-system.md),
      [`../re/data/goals.json`](../re/data/goals.json))
- [x] The client registers **134 goal ids** while the 2012 config defines only **91**: the
      reconciliation is recorded as data — 79 overlapping, 12 config-only, 55 client-only
- [x] **The finding that changes the content pipeline**: the config's `goals` array is *not
      Social Wars content* (villagers, trolls, sheep ranches, wonders, acres, university),
      and all 79 overlapping ids carry a **different title**. The id space is shared; the
      content is not. The **client** is the source of truth for goals, and the upstream
      server prints the wrong titles
- [x] 6 client defects are documented, including a goal that completes on the *first*
      market collect instead of after 500 wood

**Status:** Complete.

### B6 — UI screen inventory (the modern client's UI spec) ✅

- [x] All **260 UI classes** are inventoried: 95 popups, 57 GUI panels, 108 interface
      movie clips (the other 143 top-level `*MC.as` files are gameplay art and are
      correctly excluded)
      ([`../re/docs/14-ui-screen-inventory.md`](../re/docs/14-ui-screen-inventory.md),
      [`../re/data/ui-screens.json`](../re/data/ui-screens.json))
- [x] Each is classified as *gameplay-critical*, *supporting* or *cosmetic/droppable*
- [x] The inventory becomes the modern client's UI backlog: **698 user-facing strings** (the
      localisation surface) and **122 image references** (the chrome gap list)
- [x] The shared `PopupObject` base is documented as a **priority-ordered modal stack**,
      which the clone should reproduce

**Status:** Complete.

### B7 — Social layer contracts ✅

- [x] The 11 `alliance/?method=…` variants are recovered from the AS3 and specified, with
      their exact request parameters
      ([`../re/docs/15-social-layer-contracts.md`](../re/docs/15-social-layer-contracts.md),
      [`../re/data/service-contracts.json`](../re/data/service-contracts.json))
- [x] The 17 alliance error codes are recovered from `data/AllianceServiceError.as`
- [x] The `bets/*` auction routes are specified — and they **match the upstream server's
      commented-out handlers field for field**, so the upstream author had recovered the
      same contract and simply never enabled the routes
- [x] The marketplace and unit-bidding flow is specified (uuid / round / bidPrice)
- [ ] The premium-account and offer-pack purchase flows are specified — **deferred to
      Group F**: the offer-pack data is already in `config/main.json`
      (`offer_packs`, 44 entries) and the purchase command is already in the catalogue

**Status:** Complete.

### B8 — Remaining live captures

- [ ] The PvP `end_attack` payload is captured from a live player attack
- [ ] The `attack_player` / `spy_player` command payloads are captured live
- [x] The alliance and marketplace request/response shapes are captured statically from the
      client, which is stricter than the local server could exercise — the upstream server
      answers `{}` for every alliance variant, so there is nothing to capture against
- [ ] The premium purchase flow is captured live

### Output contract for Group B ✅

- [x] Every B-item produces a document in `re/docs/` **and** a machine-readable JSON/CSV
      artefact under `re/data/`, so implementation consumes data rather than prose — 9 JSON
      datasets and 17 documents
- [x] `re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md` is updated: Q5 (the key rotation) is
      closed, and every remaining gap is listed with its impact on the build

**Status:** Complete except the live PvP capture (B8).

**Exit criteria:** the rules-engine backlog (B3/B4/B5) and the UI backlog (B6) are
machine-readable and complete enough to implement from.

---

## Group C — Monorepo & Content Pipeline

*Outcome: a single repository builds a typed content bundle and a workspace that the rest
of the project lives in.*

- [x] A pnpm workspace exists with `packages/protocol`, `packages/content` and
      `packages/rules`; `apps/server`, `apps/client`, `apps/desktop` and `tools/*` are
      reserved in `pnpm-workspace.yaml` and land with Groups F, G and H
- [x] `packages/protocol` defines types for the full command set, the resource vector
      order (F2) and the save document, and both client and server import them
- [x] `packages/content` builds a content bundle from `config/main.json` + the 5 JSON-Patch
      deltas, applying them in the order `config/patch/patches.txt` documents
- [x] The content bundle validates against a schema and **the build fails** on an unknown
      key or a dangling id — the build currently reports **0 errors**
- [x] The bundle build is **reproducible**: the same inputs produce a byte-identical
      bundle, and the hash is recorded. Current build id:
      `74e31f2d02b3a6346463edda35e9ac1999ff85157a828d484aad9d714d1234ce`
- [x] The build **parses the config's stringly-typed item table** rather than casting it:
      `costs` is JSON text inside a string, `trains_ids` and `upgrades_to` are single id
      strings, and the property *values* are strings too. Casting instead of parsing
      silently produced **empty build costs for all 900 items**. Every item now has its
      cost, 56 have an upgrade chain and 130 train a unit
- [x] The build-time, footprint and building fields are typed: `width`, `height`,
      `min_level`, `build_time`, `clicks_to_build`, `training_time`, `xp`, `activation`,
      `collect`, `collect_type`, `collect_xp`, `max_collects`, `group_type`, `race`,
      `in_store`, `giftable`, `gift_level`, `cost_unit_cash`, `volume`, `max_elem_vol`,
      `inventory_ids` and `premium_upgrade_costs`
- [x] The darts schedule rotates weekly and remains correct after a simulated year —
      the rotation is done at **runtime**, not at build time, so the bundle stays
      reproducible
- [x] The client-only item ids are reconciled — **corrected to 7**, against the shipped
      900-item config (see F15)
- [x] The 41 distinct `properties` keys and the 24 `subcat_functional` values are typed and
      documented in the bundle
- [x] Every content item resolves to an asset reference or is explicitly marked
      asset-less — **10** are asset-less and are listed by id in the bundle
- [x] `packages/rules` exposes a pure, side-effect-free simulation API with no `Date.now()`
      and no unseeded randomness: a seeded xoshiro128** generator, the 12-stage damage
      pipeline, and the resource helpers
- [x] CI runs typecheck, lint, unit tests and the content build on every push
      (`.github/workflows/ci.yml`)
- [x] The content bundle carries **`display_order`**, which the build menu's order is
      built from. It was **missing**: the config has it on every one of the 778 items,
      as a string, and the pipeline dropped it - so the build menu could not be built
      from the bundle at all. The same class of gap as the costs

**Status:** Complete for the packages that Groups D, E, F and G depend on. The three
application shells land with their own groups.

### What the content build proved

The build **reproduces the upstream server's own post-patch counts exactly** — 900 items,
100 levels, 91 goals, 105 globals, 27 darts entries, 41 property keys, 24
`subcat_functional` values — which is the strongest available check that the patch order
and the patch semantics are right.

It also **corrected a finding**. The "129 client-only item ids with no recoverable stats"
figure was measured against the *unpatched* 778-item base config. The config that ships
is 900 items, and the `unit_patch` delta adds 122 of those 129 **with their stats**. The
real content gap is **7 item ids and 1 sprite id**. See F15 and
[`../re/docs/11-unit-and-building-behaviour.md`](../re/docs/11-unit-and-building-behaviour.md) §4.

### Verified

| Check | Result |
|---|---|
| `pnpm typecheck` | clean, 0 errors |
| `pnpm test` | 28 tests, 28 pass, 0 fail (Node's built-in runner — no test-framework dependency) |
| `pnpm --filter content build` | bundle written, 0 validation errors |
| Content build reproducibility | same build id on two consecutive runs |
| `node scripts/verify-upstream.mjs` | 3 292 files checked, 0 mismatched, 0 missing, 0 unexpected |

**Exit criteria:** `pnpm build` produces a validated, hashed content bundle and a green
CI run. ✔ met

---

## Group D — Asset Pipeline

*Outcome: the game's art and audio exist as non-Flash, renderable, versioned artefacts.*

- [x] The corpus is characterised: every SWF parsed natively and classified as `real` (67),
      `stub` (1 108) or `none` (1), with its SHA-256, frame rate, frame count and tag
      composition — [`../re/data/swf-corpus.json`](../re/data/swf-corpus.json)
- [x] The **export mode is settled by measurement**, not assumption: a sprite SWF is a
      *library* of nested `DefineSprite` timelines (the 862 sprites have a **median of one**
      top-level frame), so `ffdec -export frame` throws the art away — **1 PNG** where
      `ffdec -export sprite` gives **170** across 4 symbol directories
- [x] The frames are **deduplicated by content hash** before anything is packed: a 43 KB
      sprite exports to 170 PNGs (7.3 MB) containing only **12** distinct images, because
      an animation holds each drawing for many ticks
- [x] The conversion is **batched**: FFDec accepts a *directory* of inputs, so the ~6 s JVM
      start-up is amortised across a batch instead of being paid 1 116 times
- [x] The converter is **resumable**: the manifest is loaded on start and the SWFs it already
      covers are skipped, and it is written after *every* batch — so an interrupted run keeps
      everything it has already converted
- [x] `scripts/convert-assets.mjs` converts, deduplicates and emits the frame manifest
      (`re/data/frame-manifest.json`), mapping every (swf, symbol, frame) to a
      content-addressed image
- [x] The `DefineSprite` symbol names are preserved verbatim, because they encode the
      game's own animation-state vocabulary (`…_fla.DG_andarTcopy_3` = "and attack, copy,
      frame 3")
- [x] Every frame is **trimmed to its alpha bounding box**, and the offset is recorded, so
      the renderer can place the sprite and the atlas holds no empty space
- [x] The trimmed images are **packed into texture atlases** with a shelf packer, and the
      manifest records each image's region
- [x] A **dependency-free PNG codec** (`scripts/lib/png.mjs`) on Node's built-in zlib, so
      the repository keeps its zero-runtime-dependency property
- [x] The full run over all **1 104 SWF files outside `assets/flash/`** is executed:
      **41 198 symbols, 387 799 PNG frames, 254 155 unique images** (34.5 % were
      duplicates) in a 36.7 GB content-addressed store, in 3 023 s
- [x] The converter's **batching bug** is fixed: it used to build the batches per input
      group and slice them with a running counter, which silently dropped **334 of the
      1 106 files** with no error in the log. It now builds one flat list and splits it
      evenly, and `scripts/verify-command-catalogue.mjs`-style checks catch the class of
      drift
- [x] The frame manifest is written **atomically** — to a temporary file and renamed over
      the target — so a reader never sees a half-written hundred-megabyte file. The
      client's atlas test found the problem by reading it mid-write
- [x] The manifest itself is **not committed**: at **148 MB** it is a build artefact of
      the asset pipeline, and it is written into the ignored `re/` tree. The **atlas
      pages** are build artefacts too - **11 865** of them, 31.8 GB, at 71.8 % occupancy -
      and the manifest records where every image ended up in them, so the client looks
      the art up without knowing how the atlases are laid out
- [x] The **atlas packer is resumable**: the measurements are cached, and a sheet that
      is already on disk is not drawn again. It died once at sheet 3 780 of 11 865, and
      the restart skipped the 3 780 in under a minute
- [x] The 58 `Basesec_1.5.x.swf` builds (239.7 MB) are handled separately: `Basesec_1.5.4.swf`
      is the only one converted (it is the reference client, not game art)
- [x] The 1 314 thumbnails are indexed by item id and served as the inventory icon set —
      **871 of the 900 items have one**
- [x] The 139 config sounds resolve to playable audio — **all 139 resolve**; the 2
      disk-only music beds are still to be wired
- [x] The 607 localised images and 578 image files are packaged per language — the image
      paths are language-relative (`/chapters/chapter_1.jpg` + `en` →
      `assets/images/en/chapters/…`)
- [x] The 73 missing asset references are **measured and confirmed independently** by
      `scripts/build-asset-manifest.mjs`: **10 missing sprites, 29 missing thumbnails,
      34 missing images = 73** ([`../re/data/asset-manifest.json`](../re/data/asset-manifest.json))
- [x] The unreferenced assets are **triaged**: every sprite is referenced by some item's
      `img_name`; 471 thumbnails, 5 images and 2 sounds are present but referenced by
      nothing
- [x] The client fonts are **extracted and measured**
      (`scripts/extract-fonts.mjs`): the two SWF font libraries yield
      "Arial Rounded MT Bold" (244 glyphs, 241 characters) and "Komika Axis" (228 glyphs,
      215 characters), and the advance width of every printable ASCII character is recorded
      in [`../re/data/fonts.json`](../re/data/fonts.json) — the numbers the substitutes
      have to be tuned to
- [x] The **open-licensed substitutes are chosen** and recorded per font: Nunito for the
      rounded body text and Rubik Mono One for the display face, both SIL OFL 1.1
- [x] The substitutes are **substituted in the client** (`apps/client/src/fonts.ts`):
      the stylesheet declares a `@font-face` for each, with a `local()` source and a
      fetched one, and the two **stacks** the game uses. The **proprietary** faces are
      never named - the test checks that - and `font-display: swap` means the text
      appears with the fallback rather than the page being invisible until the face
      arrives
- [ ] The substitutes' **metrics are tuned** to match the originals', which needs the
      real font files: the scale is a parameter, measured against the files, and a scale
      of 1 means "not tuned yet"
- [x] The **4 proprietary font references are identified**: the client loads **two** fonts
      (`ArialRoundedBold` and `KomikaAxis`) in **three** languages (English, Turkish and
      Greek), so it looks for **six** font files. Only the two English ones ship, and the
      four missing ones are the **Turkish and Greek variants of the same two faces**. The
      client's own `FontsLoader` has an IO-error handler that retries and then falls
      back, so a Turkish or Greek player sees the default font rather than a broken one
- [x] `assets/swf/dynamic2.swf` is decompiled and analysed — it is the **runtime library**:
      it embeds **28 sounds the server's config never mentions** (all unique, none
      duplicating a standalone file) and the **building-construction animations**, which
      explains why some items appear to have no art
      ([`../re/docs/17-asset-pipeline.md`](../re/docs/17-asset-pipeline.md) §7)
- [x] The 4 sprites above the 4 KiB ABC threshold are audited — they are ordinary
      animation timelines with many named frames, not special logic. **Nothing to act on.**
- [x] The 28 embedded sounds are added to the audio set — the runtime library
      `dynamic2.swf` carries 28 sounds of its own (the construction animations' audio)
      that are named nowhere in the config's sound list, and they are now **in the audio
      set the client loads**, marked as embedded because their bytes live in a SWF
      rather than in a standalone file. The set is **168 sounds**: 140 standalone and 28
      embedded
- [x] The construction animations from `dynamic2.swf` are included in the conversion —
      the runtime library contributes **34 symbols**, among them
      `Animgranjaconstr_27` with 129 frames, `ConstructionGranja` and
      `Construction4x4Trol`. The 205 FX assets contribute **1 234 symbols** across all
      205 files
- [x] A viewer exists that renders every item at 3 zoom levels, so missing art is
      visible — `scripts/build-asset-viewer.mjs` generates a single self-contained page
      from the repository's own records: every one of the **900 content items**, its
      sprite and its thumbnail, the art at 0.5x, 1x and 2x, and the **10 items missing
      a sprite marked in red**. The art columns read from the atlas regions, so the page
      is regenerated once the packer has run
      immediately
- [x] The client can be built with a **content-hashed** asset bundle, so a stale cache is
      impossible — `scripts/build-asset-bundle.mjs` records every asset's content hash
      and derives **one build id** over the whole set, and the client appends that id
      to every asset URL (`packages/client/src/assets.ts`). A changed asset means a
      changed URL, so the cache cannot be stale. The bundle is also the client's
      **index**: which atlas page each sprite is on, and where in it, so the renderer
      does not have to know how the atlases are laid out

**Status:** The conversion pipeline, the trim and the atlas packer are built and verified.
The full run, the audio, the fonts and the viewer remain.

**Measured on a 30-file sample** (`node scripts/convert-assets.mjs --group sprites --limit 30
--jobs 3`): 230 symbols, **8 245 PNG frames written, 2 024 unique images** — 75.4 % of the
frames are duplicates of another frame, because an animation holds each drawing for many
ticks. 414.5 MB of raw PNG becomes a **233.6 MB** content-addressed store, in 107 s.

**Verified by the atlas packer:** every trimmed region was compared pixel by pixel against
its source — **682 856 pixels, 0 mismatched**.

See [`../re/docs/17-asset-pipeline.md`](../re/docs/17-asset-pipeline.md).

**Exit criteria:** every shippable item id renders in the viewer with no missing frame.

---

## Group E — Rules Engine

*Outcome: the game simulation is reproducible server-side and matches the original
client's observable behaviour.*

### E1 — Combat

- [x] The damage pipeline (shield → delegate veto → counter → attack modifier → global
      multiplier → unit XP → siege → tutorial → crit/variance → defence → round → clamp) is
      implemented in `packages/rules/src/combat.ts`, with **every stage recorded** so the
      golden-master diff can compare stage by stage
- [x] The **targeting rule** is implemented from `IsoEngine.getElementScore`: the bonuses are
      a mutually exclusive `else if` chain, the score is `1000 − distance` plus one bonus,
      **`−1` means untargetable**, a passive building is treated as `AGGRO_RANGE` (10) tiles
      further away, and the candidates are sorted by **score descending, then distance
      ascending**
- [x] The **4 real counters** are confirmed against the shipped content and encoded in
      `packages/rules/src/counters.ts`: Antiaircraft battery 20× vs `ft_flying`, Demolition
      Tank 15×, Mortar Thrower 10×, B52 5× vs `ft_building`. **Exactly 4 of the 900 items**
      have a multiplier above 1; the 138 offer packs carry the `best_against = "-1"`
      sentinel, which never counters anything.
- [x] Range rules match: units use `attack_range + max(0, targetWidth − 2·attack_range)`,
      buildings use the exact `attack_range`
- [x] Attack cadence matches: `attack_interval` is frames at 30 fps, units take a random
      0–4 frame phase (`Math.floor(Math.random() * 5)`), buildings fire in global lockstep
      with no phase — implemented in `packages/rules/src/battle.ts`
- [x] A building's **shot count** is limited by its garrison: a bunker fires once per
      garrisoned unit (capped by its attack points) and an empty bunker fires not at all.
      **The building's own `attack` is *not* scaled** — it comes straight from the config
      (`IsoElement.as:267`)
- [x] Unit XP accrues from the **effective damage dealt to units only** — damage dealt to a
      building earns nothing (`IsoFightingElement.as:477-480`). The level table is
      `globals.UNIT_XP_LEVELS_MULTIPLIERS_10` and the bonuses are cumulative:
      **+30 attack and 3× base HP at level 9**
- [x] The level-up thresholds behave exactly, including the client's off-by-one: the
      comparison is `xp <= required` to *break*, so a unit needs one point more than the
      threshold to advance — which is why a paid level-up grants "the missing XP plus 1"
      (`CmdPlaceStoredItem.as:38`), and why **level 9 cannot be reached by XP alone**
      (`packages/rules/src/xp.ts`)
- [x] All **10 damage classes** are implemented as pure state transitions
      (`packages/rules/src/damage.ts`): `SimpleDamage`, `DamageOverTime`, `BleedingDamage`,
      `DelayedDamage`, `DirectKillDamage`, `DizzyDamage`, `IncinerateDamage`,
      `PushInAirDamage`, `SequencedDamage` and `AreaDamageSpecialAttack` — including the
      shared-damage division, the bleed's damage-per-second, and the conditional kill
- [x] All **15 special-attack classes** are specified
      (`packages/rules/src/specialattacks.ts`) with the damage outcome a server has to
      reproduce: the per-shot fallbacks (`attack / frames / points`, `attack / frames`),
      the area sharing, the spawn counts, the consume attacks, the vortex's 30 % bleed, and
      the whirlwind's per-tick division

### E2 — Economy and buildings

- [x] The **collection** formula is implemented (`packages/rules/src/economy.ts`): the base
      amount, the 4 collect periods with their multipliers (**5 min ×0.25, 60 min ×1,
      240 min ×2, 480 min ×3**), and the **20 % peasant bonus per extra worker** inside
      the mill
- [x] The **anti-hack guard** is implemented: a building holding more units than its
      capacity collects **nothing**. In the original this check is client-side only; a
      server-authoritative clone must make it server-side
- [x] **Population** is implemented: the ceiling is
      `min(START_MAX_POPULATION + Σ building grants, MAX_POPULATION_CAP + extra)`, the
      current is `Σ unit population + units being trained`, and a unit that would exceed
      the ceiling is refused
- [x] **Energy** is implemented: the free maximum is **30**, it regenerates **+1 every
      5 minutes**, and construction and friend assists each cost 1
- [x] The **expansion, town and map price tables** are read from the content bundle, with
      the first four expansions free and the level requirements enforced
- [x] Build costs, build times, upgrade chains and the "click to build" mechanic are
      correct (`packages/rules/src/building.ts`): the build cost, the build and training
      durations, the click count, the upgrade chain with its **1/20** refund of the old
      building, the premium upgrade price, the speed-up rules and the placement limits
      (level, population, per-id and per-group limits, and a free tile)
- [x] The **own market** is implemented (`packages/rules/src/market.ts`): the gold price of
      100 units (wood 100, oil 100, steel 150), the three tradeable amounts, the **+2 % per
      prior trade** increment, the **75 % sell rate**, and the limit of **20 trades per
      20 hours** with the counter resetting after the period
- [x] The **allies market** is implemented: 125 units for the first helper and 125 more for
      each additional one
- [x] The **daily bonus** is implemented: the 5-day cycle (100 / 250 / 500 / 1000 gold, then
      a hero), the local-time-zone day boundary, and the streak reset
- [x] The **weekly Monday bonus** is implemented: the 3-entry outer cycle, the 5 possible
      units inside the unit reward, and the ready / collected / not-ready / hidden states
- [x] The **alliance daily bonus** is implemented: the highest tier the member count
      qualifies for (0 / 5 / 25 / 45 members)
- [x] The upstream's market period mismatch is **resolved**: the upstream resets the trade
      counter **daily** while the client uses a **20-hour** period, so the two disagree on
      exactly when a player may trade again. The **client's** period is the rule, because
      the client is the specification and the player's experience is the client's. The
      upstream's daily reset is an upstream bug: it makes the limit 24 trades per
      calendar day rather than 20 trades per 20 hours, and it disagrees with the counter
      the client shows. The rules engine implements the 20-hour period
      (`packages/rules/src/market.ts`)
- [x] The darts minigame (25 targets, 20 cash per paid shot, weekly prize rotation) is
      correct — the board of **25 balloons** with the six prizes spread **1, 1, 4, 4, 7,
      8** over them (the client's own `initTargetItems`), the board **shuffled from the
      server's seed** so every player sees the same board that week, the first shot of
      the day **free** and every shot after it at **20 cash**, and the **extra prize**
      won by discovering all six — once (`packages/rules/src/dartsboard.ts`)

### E3 — Quests and goals

- [x] The quest state machine and all 23 concrete quests' win/fail conditions are
      implemented (`packages/rules/src/quest.ts`): the lifecycle, the per-kill economy
      (5 gold and `ceil(gold × 0.05)` xp), the army-wipe rule, the mission timers, the
      difficulty scaling, the air-vehicle exclusion, the weekly quest, the chapter system
      and the rewards — with the play order and reward rows **pinned by id**, not by index
- [x] Three things `re/data/quests.json` gets **wrong** were found by reading the client
      and corrected: `Quest10SpecialOps` and `Quest14Spy2` do *not* win on "all bastards
      dead", `Quest02CentralNuclear` has no plant-then-HQ gate, and
      `Quest06Airstrike`'s radio station is not a gate
- [x] `Quest08Rocket`'s win is **unreachable** (`canDie` is false), and that is flagged
      rather than papered over
- [x] **All 134 goals evaluate server-side, with at most 5 active**
      (`packages/rules/src/goals.ts`): the 26 registerable goal types, the **5-goal window**
      (the first five *incomplete* goals in registration order), the activation sweep, and
      the id reconciliation (91 in the config, 134 client-side, 79 shared, 12 config-only,
      55 client-only, 6 translation-only)
- [x] The goal reward is granted **once**, by the server — the client's `complete_goal`
      command is never trusted
- [x] The two **observable** client defects (the allies market completing on the first
      collect instead of after 500 wood, and the harbour goal completing on any quest end)
      are **fixed by default**, with a policy flag to reproduce the client's behaviour. A
      faithful-but-buggy goal is a defensible choice; a silent divergence is not
- [x] Daily bonus, weekly bonus and goal completion are each awarded **once**, and so is
      the **alliance daily bonus** - which the upstream is not: it credits the bonus and
      never sets the timer, so the upstream pays it over and over. The weekly bonus uses
      the player's **local** week day (`Utils.getWeekDayFromTimeStamp` reads
      `Date.getDay()`), not UTC's, or the bonus moves by a day for everybody east or
      west of Greenwich
- [x] The **Monday reward cycle** is the client's: `MONDAY_BONUS_REWARDS` has **3**
      entries and the cycle wraps at 3, while the upstream wraps its index at 5. The client
      is the specification, so the cycle is 3

### E4 — Determinism and verification

- [x] Combat is resolved **server-side from a server-issued seed**
      (`packages/rules/src/authority.ts`): the API has no parameter for a client-claimed
      result, so the client cannot influence the outcome even by accident. The seed comes
      from the battle id, so the client can replay the battle and get the same result —
      auditable rather than arbitrary
- [x] A **golden-master harness** diffs the rules engine against itself
      (`scripts/golden-master.mjs`): **50 scenarios** over the damage pipeline, the
      counters, the targeting, the cadence, the garrison, the XP thresholds, the
      collection arithmetic, the market pricing, the bonus cycles, the build costs and
      the special attacks. The corpus is `re/data/golden-corpus.json` and the recorded
      answers are `re/data/golden-master.json`
- [x] The harness **runs in CI** on every push, and fails with a non-zero exit on any
      difference. Verified: perturbing one recorded value is detected and reported
- [ ] The harness diffs the rules engine against the **original Flash client** — the
      differential test needs the client to be driven through the same scenarios, which
      is the last part of E4
- [x] The simulation is deterministic given a seed; the same seed and inputs produce the
      same outcome on any machine. The claim is **provable by construction**, not merely
      untested:
      - the generator is a xoshiro128** whose every operation is a **32-bit integer**
        operation (`>>> 0`, `Math.imul`), and those are defined exactly by the language
      - the arithmetic is ECMAScript's `Number` — IEEE 754 double precision — which the
        specification requires every engine to give identically for the identical
        expression, and the order of the operations is fixed by the code
      - the rules engine is **scanned** for the sources of nondeterminism that would
        break the claim (`packages/rules/src/portability.test.ts`): an unseeded
        generator, the wall clock, the locale, the environment, a platform API or the
        filesystem. The scan is what caught the two real defects below
      - the generator's **reference vectors are pinned** (`determinism.test.ts`), so a
        change to the generator cannot pass unnoticed, and every battle ever
        re-simulated changes with it
- [x] The **darts schedule no longer depends on the machine's timezone**. It was worked
      in the server's **local** time, so two servers in different zones would rotate it
      to different strings, and the "Monday" snapping landed on a different instant. It
      is worked in **UTC** now, which also removes the daylight-saving correction the
      upstream needed. There is a test that rotates it under three timezones and
      compares the strings
- [x] The rules package no longer imports `node:assert`: the shared, platform-neutral
      core had a Node dependency in it for the sake of five comparisons. The checks are
      made by a small local helper (`packages/rules/src/assert.ts`)

**Exit criteria:** the golden-master corpus passes with zero unexplained differences.

---

## Group F — Authoritative Server

*Outcome: the server is safe, concurrent, persistent, and speaks both the new native
protocol and the original dialect.*

### F1 — Identity and authority

- [x] Players authenticate with a real credential; a session token replaces the
      `USERID`-in-the-body model (F10) — the session model is implemented
      (`packages/server/src/session.ts`): a salted, hashed credential compared in constant
      time, and a **revocable** session token, and the **HTTP layer issues it**
      (`POST /api/session`, `DELETE /api/session`). The legacy `USERID` path exists for
      the untouched client, but the bridge is **off by default** and can only map a value
      the server has already bound to a player
- [x] The players' **credentials are persisted** (`packages/server/src/credentials.ts`),
      so a player who registered can log in **after the server restarts**. The
      credential is a **salt and a hash** - the password is never stored - and the
      hash is compared in constant time
- [x] A player can be **created**: `POST /api/account` makes one and signs them in.
      The upstream had no accounts at all - `USERID` came in the request body and
      anybody could be anybody - so without this nobody could play
- [x] The hash is a salted SHA-256, which is **fast**, and that is a deliberate
      trade: the server is a preservation of a 2012 game with a handful of players
      rather than a bank, the threat is not an offline attack on a stolen table, and
      a slow hash would make the server's own logins slow. A deployment that grows
      players should move to a memory-hard hash, and that is a change in one module
- [x] Every command's resource cost is computed by the server, never accepted from the
      client (F3) — `packages/rules/src/commandcost.ts` derives each cost from the
      content bundle and the command's own arguments, through **one shared loader**
      (`costContentFrom`) so the five callers cannot drift apart. **The API has no
      parameter for the client's claimed delta**, so it cannot be supplied even by
      accident, and a command the table does not price is treated as *free* rather than
      as "whatever the client says"
- [x] **17 commands are priced** from the content: `buy`, `place_stored_item`,
      `sell_stored_item`, `exchange_cash`, `buy_offer_pack`, `buy_premium_account`,
      `buy_resources`, `buy_powerups`, `darts_shoot_balloon`, `expand`,
      `premium_upgrade`, `trade_resource`, `level_up`, `attack_player` and `spy_player`
- [x] The two commands whose cost depends on the **building's own state** are charged by
      the server instead: `reset_collect` (the reactivation price is
      `building.costs.c × REACTIVATE_WONDER_DISCOUNT` — the client computes it and
      *declares* it) and `finish_building` (the speed-up price, from the time that is
      left)
- [x] `flash_debug` does not exist in the server (F4) — it is not in the priced command
      list, and the shim **refuses it outright** rather than pricing it at zero
- [x] Combat outcomes are re-simulated server-side (F5) — `packages/rules/src/authority.ts`
      resolves the hit from a server-issued seed, and
      `packages/rules/src/simulate.ts` simulates the **whole battle**: the 30 fps
      cadence with each unit's random phase, the buildings' lockstep fire, the
      targeting, the damage pipeline and the casualties. The distance metric is the
      client's own (`IsoEngine.distance`): the euclidean distance between the
      **centres**, offset by half the footprint and **truncated to an integer**
- [x] The **assault loot** is computed by the server (`packages/rules/src/loot.ts`): the
      gold comes from the victim's town hall, at a random 15–35 % of its gold, clamped
      to the attacker's level band; the XP is 5 % of that, rounded up, and at least 1
      for anything that is not a wall; and a win with no loot is worth a flat 25 gold.
      Two client quirks are reproduced rather than "fixed": the client's
      `MAX_GOLD_ASSAULT` cap **is not in the config's globals at all**, so the cap it
      was meant to enforce never fires, and the band table has two rows at level 80,
      which makes its 22 500 row unreachable
- [x] The server's own `end_attack` grants the loot the **simulation** says
      (`packages/server/src/apply.ts`); the client's claimed battle result is parsed
      only so it can be compared, and a claim of a million gold changes nothing
- [x] Goal completion is evaluated server-side — the 134 goals and the 5-goal window are
      implemented in `packages/rules/src/goals.ts`, and the reward is granted once by the
      server rather than trusted from the client's `complete_goal`
- [x] Daily bonus, weekly bonus and the alliance daily bonus are evaluated **server-side**
      and awarded **once** (`packages/server/src/apply.ts`). The daily one computes the
      day from its own clock and ignores the bonus index the client claims; the weekly
      one is only ready on a Monday and only once a week; the alliance one takes the
      tier the member count qualifies for, and only once a day. The weekly bonus uses
      the player's **local** week day (`Utils.getWeekDayFromTimeStamp` reads
      `Date.getDay()`), not UTC's, or the bonus moves by a day for everybody east or
      west of Greenwich
- [x] **Premium expiry** is evaluated server-side: the premium is a **timestamp** in
      the private state, not a flag, and the server owns it
      (`packages/rules/src/premium.ts`). Buying while it is still running **extends**
      it and buying after it has lapsed **starts it fresh** — the upstream's rule and
      the client's. The perks are the client's: three attacks a day instead of one, and
      a share of the rewards in cash
- [x] **Premium expiry** is evaluated server-side: the premium is a **timestamp** in
      the private state, not a flag, and the server owns it
      (`packages/rules/src/premium.ts`). Buying while it is still running **extends**
      it and buying after it has lapsed **starts it fresh** — the upstream's rule and
      the client's. The perks are the client's: three attacks a day instead of one, and
      a share of the rewards in cash
- [x] The commands that **grant** anything are answered by the server's own rules, not by
      the client's claim (`packages/server/src/apply.ts`): `collect`, `complete_goal`,
      `win_daily_bonus`, `reset_collect`, `finish_building`, `place_stored_item`,
      `buy`, `push_queue_unit`, `pop_queue_unit`, `level_up`, `upgrade` and
      `end_attack`. The upstream grants **none** of these by server-side rule: it resets
      the collection timer and lets the client declare the amount, prints a line for
      `complete_goal`, takes the daily bonus index *and the item id* from the client,
      and lets the client pop a unit that is still training
- [x] The **training queue** is the server's own: the building's attribute bag holds
      `nu` (how many are queued), `ts` (when the current one started) and `ui` (which
      unit it is), exactly as the upstream's `engine.py` does. The server checks that a
      unit has actually finished training before it is popped, which the upstream does
      not
- [x] The **level-up** checks that the player has the XP for the next level and grants
      that level's reward from the level table, and the **upgrade** charges the new
      building's cost less the refund of the old one and refuses an upgrade that would
      not fit
- [x] The full cheat battery is rejected or has no effect: inflated `res`, forged
      `flash_debug`, replayed `win_daily_bonus`, self-completed goals, forged
      `end_attack`, free `buy_offer_pack`, wrong HMAC, another player's `USERID`,
      malformed framing, forged `win`, over-collection —
      `packages/rules/src/cheatbattery.ts` **attempts all eleven** against the real
      authority layer and proves each one has no effect. The battery is
      **mutation-tested**: 18 weakenings of the authority layer were each detected by
      exactly the attack they weaken
- [x] The shim **resolves the player from the session token or the bound legacy
      `USERID`**, and the identity chooses which save is touched. The request body
      cannot name the player. Found by the cheat battery, which shipped a tripwire
      because the shim did not consult its own identity bridge
- [x] The **remaining holes the battery reported** are closed: the shim's grant
      commands are no longer an unimplemented seam. `win_daily_bonus`, `complete_goal`,
      `end_attack`, `end_quest` and `collect` are all **granted through the battery's
      paths** - the shim calls the same applier the native endpoint calls, and the
      applier's own rules decide each one
- [x] Each of the five has an **attack** that proves it: the replayed daily bonus, the
      self-completed goal, the forged `end_attack`, the forged `win` and the
      over-collection. The battery runs them against the **real** authority layer, and
      it is **mutation-tested**: eighteen weakenings of that layer were each detected by
      exactly the attack they weaken
- [x] The **production-cycle timer** is implemented and the **server owns the clock**
      (`packages/rules/src/production.ts`): the collection is a period the **player
      chooses** - 5 minutes at 0.25, 60 at 1, 240 at 2 and 480 at 3, the client's own
      four - and the server refuses a collection until the period has elapsed. The
      upstream never checks this: its `collect` handler resets the timestamp and
      believes whatever the client sends

### F2 — Protocol

- [x] The native command API is **versioned, typed and documented**
      (`packages/protocol/src/commands.ts`): a version constant with a supported range, a
      request envelope of exactly four fields (`v`, `id`, `token`, `commands`), a typed
      response with typed errors, and a **command table with an entry for every one of
      the 94 commands**. Deliberately absent from the envelope: `USERID`, the
      client-declared resource vector, the client's `ts`, and any client-claimed combat
      outcome
- [x] The server **serves** the native API (`POST /api/command`): the envelope is
      validated against the command table, the costs are computed by the server, the
      commands are applied atomically, and the answer is a typed response. A bad
      envelope is a typed 4xx with the errors, never a 500
- [x] The native protocol's **idempotency key** works: a retry of a request that was
      lost in flight carries the same `id`, and the server replays the stored answer
      instead of applying the commands twice. The answers are kept per player and
      bounded, so a client cannot fill the server's memory by sending retries
- [x] The **command list is correct**, and permanently checked. The client has **94**
      commands, and the report's catalogue transcribes them **exactly** — 94 = 94, with
      the catalogue's rows numbered 1 to 94 and no gaps, so the two sources
      cross-validate each other rather than merely agreeing in total. The upstream
      handles 63 and silently drops the other 31.
      `scripts/verify-command-catalogue.mjs` checks the client's own command classes
      against the catalogue and against `COMMAND_NAMES`, and fails on any difference
- [x] The catalogue's rows are checked for **gaps in their numbering**, so a row
      dropped in transcription cannot pass unnoticed
- [x] The **`command.php` framing** is implemented exactly
      (`packages/protocol/src/commandphp.ts`): `<64 lowercase hex>;<raw json>`, the digest
      being HMAC-SHA256 over the **raw payload bytes**, and the parser mirroring the
      client's own regex *and its fallback* — an unframed body is taken whole with a null
      hash, which is what makes the `skiphash12341` bypass work. The digest comparison is
      constant-time
- [x] The framing is **verified against the real captured traffic**: every framed request
      in `re/evidence/live/requests.jsonl` reproduces against a known key, and the
      captured digest — produced by the original Flash client — is reproduced exactly
- [x] **Both server keys are accepted**, because unmodified clients of both eras exist,
      and the shim reports which era a request came from
- [x] A **compatibility shim** serves the original `command.php` dialect
      (`packages/server/src/shim.ts`), so the untouched `Basesec_1.5.4.swf` can play
      against this server with no client change. It does four things the upstream server
      does **not**: it verifies the HMAC, it computes the resource costs, it **survives a
      replayed packet** without applying the commands twice, and it **tolerates a gap** in
      the global command index
- [x] The shim tolerates the `skiphash12341` response-hash bypass — the parser's
      unframed fallback already handles it
- [x] The shim serves `get_game_config.php` with the patched, darts-rotated content and
      `get_player_info.php` with own/neighbour/quest map flavours — the four
      `get_player_info.php` flavours are implemented, and the **darts schedule is rotated
      to the current week**. The rotation is not decoration: the client's board is built
      from the schedule, so a player who loaded the config on a different day would see a
      different board. The upstream rotates it on every boot for exactly this reason

### F3 - Persistence

- [x] State is stored in **PostgreSQL** with transactional command application;
      concurrent commands cannot corrupt a player —
      `packages/server/src/pgstore.ts` locks the row `FOR UPDATE` inside a
      transaction, **and** serialises the transactions on the same player inside the
      store, because PGlite has one connection and two concurrent transactions on it
      interleave in a way the database cannot separate. The save document is one
      `JSONB` column: the game's queries are all by player id, and the document is a
      tree of mixed types
- [x] The **player store's interface is asynchronous**, because a database is
      asynchronous, and the application and its tests await it. The in-memory store is
      the reference implementation and the offline mode's
- [x] The **save document format** is migrated from the upstream schema (12 `playerInfo` +
      28 `maps[]` + 47 `privateState` fields) with a tested, versioned migration path -
      the **47 `privateState` fields are now known exactly** (from the upstream's
      `initial.json`), and the server's two additions are defined
      (`packages/server/src/apply.ts`): the production state of each building, which the
      upstream never kept because the client kept it, and the goal runtime state, which
      the upstream never had. The migration (`packages/server/src/migrate.ts`) is
      **wired into the store**: an upstream save is imported verbatim and migrated when
      it is read, and a save from a version this server does not understand is
      **refused** rather than guessed at
- [x] A backup and restore procedure exists and has been **exercised against a real
      snapshot** — the database is a directory in the offline mode, so a backup is a copy
      of it and a restore is opening the copy (\packages/server/src/backup.ts\,
      \scripts/backup-server.mjs\). The tests write a database, back it up, change the
      live database, restore the snapshot and check that the snapshot still holds the
      OLD state, and a digest of the tables is what proves the two match
- [x] Schema migrations are **forward-only**, **reversible where safe**, and **run as part
      of deploy**. The schema is **versioned** (`packages/server/src/schema.ts`): the
      stores created their tables with `CREATE TABLE IF NOT EXISTS`, which can only ever
      add a table and says nothing about what happened to the ones that were already
      there — a column a new server needs would be added by hand, and the hand-added
      column would be in no migration's history. Now every change is a migration, each of
      which moves the schema one version forward, is recorded in the database, and may
      declare a `down`. A migration that cannot be undone safely declares no `down`, and
      the runner **refuses** to roll it back rather than pretending it can
- [x] The migrations **run as part of deploy**: `node scripts/migrate.mjs --data <dir>`
      brings the schema forward, `--status` says what version it is at, and `--rollback`
      undoes what can be undone. The server itself runs them **before it serves**, so a
      deploy cannot start a server against a schema it does not understand, and it keeps
      its saves in the database when `SWL_DATA_DIR` names one
- [x] The migrations **run as part of deploy**: `node scripts/migrate.mjs --data <dir>`
      brings the schema forward, `--status` says what version it is at, and `--rollback`
      undoes what can be undone. The server itself runs them **before it serves**, so a
      deploy cannot start a server against a schema it does not understand, and it keeps
      its saves in the database when `SWL_DATA_DIR` names one

### F4 - Robustness

- [x] Bad input returns typed 4xx responses, never a 500 — `apps/server/src/app.ts`
      returns a typed error code and message for every failure, and an unexpected
      exception is caught at the edge
- [x] Every endpoint has request-size limits, rate limits and timeouts — the body is
      capped while it is **read** and again before it is **parsed**, the rate limit is a
      fixed window per client, and the command batch has a deadline that is checked
      *between* commands, so a command is never interrupted half way
- [x] The server survives a client disconnect mid-command without partial state — the
      batch is applied to a copy and committed atomically
- [x] A soak test of sustained play shows **no memory growth** and **no state drift**
      (`scripts/soak-server.mjs`, and CI runs it): 20 000 batches over 8 players is
      40 000 commands, and the heap **shrinks** rather than growing. The state drift is
      the more interesting half: the command index is the client's global counter and
      it is what goes wrong first — a retry, a dropped batch or a refused command moves
      it, and every later command is then off by one. So the soak checks that the index
      advances by exactly the number of commands applied and never goes backwards

### F5 - Social layer

- [x] The **alliance service** is implemented: all **11 service variants** with their
      parameters, and the **17 error codes** in four bands, exactly as the client's
      `data/AllianceServiceError.as` has them (the client switches on those numbers, so
      they must be exact) — `packages/server/src/alliance.ts`. It is pure: the state is
      passed in and the new state is returned, with the clock as a parameter
- [x] The **country rule** is implemented: alliances are country-scoped, so a player
      cannot join or be found by an alliance in another country (`ERR_WRONG_COUNTRY`)
- [x] The **owner's powers** are implemented: only the owner processes join requests or
      kicks a member, and the owner cannot simply walk away from the alliance
      (`ERR_ALLIANCE_OWNER_SWITCH`)
- [x] The **marketplace and the auction/betting subsystem** are implemented
      (`packages/server/src/marketplace.ts`): the listing model, the three client
      endpoints, the client's own sort order (`isPrivate` descending, then `endDate`
      ascending), the price ladder, the round logic, the tie rule and the settlement.
      The upstream's subsystem was **complete but disabled**; the client's semantics win
      where the two disagree, and there were eight such places
- [x] The alliance and marketplace services are **served over HTTP** as the client service
      variants (`apps/server/src/social.ts`): the alliance's 11 variants at
      `alliance/?method=<variant>` and the three betting endpoints. The client calls
      them with the **same envelope as `command.php`** — a `data` field holding
      `<64 hex>;<json>` — so the HMAC is verified against both keys, and the answer is
      `{ "success": true, "data": … }` or `{ "success": false, "error": <the client's
      number> }`
- [x] The alliance and marketplace services are **persisted**
      (`packages/server/src/socialstore.ts`): both are pure, so the whole state is one
      document, and a restart cannot half-apply a change. The state lives in one table
      with a `kind` column, so the social subsystem is a row per kind rather than a
      table per service

**Exit criteria:** the original Flash client can complete the tutorial and a Mission 1
assault against the new server, and the cheat battery is fully rejected.

---

## Group G — Modern Client

*Outcome: the game is fully playable on desktop and mobile with no Flash anywhere.*

### G1 - World rendering

- [x] The **isometric tile map** renders with the correct elevation, z-sorting and the
      server-authoritative item positions. The **scene** is a separate, **pure** model
      (`apps/client/src/scene.ts`): every item's screen position, depth and art are
      decided without a GPU, so the rules can be tested without one, and the renderer
      (`apps/client/src/renderer.ts`) only draws what the scene says. The scene is
      **PixiJS v8** and the client is **one** client - the web build serves it, the
      desktop shell wraps it in a web view and the mobile build wraps it in a WebView
- [x] The **atlas pages are fetched on demand**, at most a few at a time. There are
      3 590 of them and 31.8 GB, and a scene of a few hundred sprites touches a few
      dozen - loading them all up front would fetch 31.8 GB to draw a village
- [x] The **web client builds** (`pnpm --filter @swl/app-client build`), the build is
      in the CI, and the client **starts in a real browser**
- [x] The client package is **browser-safe**. It imported `node:crypto` for the art
      hash, which broke the web build; the hash is a build-time utility, so it moved
      into its own module that nothing at runtime imports
- [x] The client's **art lookup** is right: the manifest carries an **item** map, so the
      client does not have to guess the SWF's group or the symbol's name, and the frame
      is looked up **one higher** than the animation chose, because the manifest's frames
      are one-based and the client picks the drawing with `gotoAndStop(frame + 1)`
- [x] The **web client builds** (`pnpm --filter @swl/app-client build`), and the build
      is in the CI
- [x] The client package is **browser-safe**. It imported `node:crypto` for the art
      hash, which broke the web build; the hash is a build-time utility, so it moved
      into its own module that nothing at runtime imports
- [ ] The renderer is **exercised**: the scene is tested, but the drawing itself needs
      a browser, and nothing here drives one
- [x] The **isometric projection and the depth sort** are ported exactly
      (`packages/client/src/iso.ts`): the tile is 108 by 54 pixels, the map is 100 by
      100, and the projection is `Utils.TileToPixel` (core/Utils.as:88-102) to the
      letter — including the half-tile offset that puts the origin at a tile's top
      corner
- [x] The **depth sort** is `Utils.assignZIndex` (core/Utils.as:395-407): a building's
      own **width** shifts it back, and a **walkable** building goes 20 000 behind
      everything else, so the roads are always under the buildings standing on them
- [x] The client's own quirk is preserved and documented: the projection and its
      inverse are only inverses of each other at a tile's **top corner**, so the
      client's own unit code passes a unit's top-corner position
- [x] The **camera** is ported exactly (`packages/client/src/camera.ts`): where the map's
      origin is on the screen and the zoom. The pan is refused **whole** when it would
      pass a bound in the direction of the movement, so the camera stops dead at the
      edge rather than sliding along it; the camera's own origin moves by the raw delta
      while the map's contents move by the delta divided by the zoom; and the **mouse
      wheel and the slider are different behaviours** — the wheel multiplies by 1.2 and
      the slider adds 0.2
- [x] The map pans, zooms and re-centres as the original does
- [x] Every unit and building animates from its atlas frames, with correct frame timing
      — the frame number is **not a timeline**: the client picks the frame by number out
      of a sheet that holds every drawing of every state, and the number is
      `animation × 5 + direction` (`core/isoengine/IsoUnit.as:1436`). There are eight
      directions and **five** slots per block, because the three LEFT-facing ones are
      the right-facing ones drawn **mirrored**. An idle unit shows a **random** frame of
      its idle sub-clip, so the random source is a parameter rather than a call to
      `Math.random`
- [ ] Projectiles, particles and the 205 FX assets render
- [x] **Depth sorting and occlusion match the original engine.** The client's depth is
      `Utils.assignZIndex` (`core/Utils.as:398-409`), and the clone's is a port of it:
      `20 000 + 100 * tx + ty * 100 - width * 100`, less `20 000` for a walkable building.
      The client sorts the building array by it **ascending**, so a larger depth is drawn
      later and therefore in front. Two details matter and are easy to lose: a building's
      own **width** shifts it back, so a wide building's art is drawn behind a narrow one
      further up the map, and a **walkable** building goes 20 000 behind everything, so the
      paths are always under the buildings standing on them
- [x] The depth and the projection are **checked against the client's own code**
      (`packages/client/src/depth.test.ts`): the decompiled ActionScript is transcribed
      again in the test and the two are compared over a grid, not at a few points, so a
      change to the port cannot quietly change the answer
- [x] The **build outline offset is explicit** in the viewport rather than subtracted by
      whichever caller remembered to. The client's projection uses `topY` less
      `offsetBuildOutlineY` — 54 — in both directions, and the clone's viewport carried
      the *reduced* value, so a caller who passed the raw `topY` got a 54-pixel shift
      and nothing said so

### G2 - Interaction

- [x] Selection, movement, building placement, training queues, collecting and upgrading
      all work through the command API - the **client's request builders**
      (`packages/client/src/requests.ts`) cover all of them, and a test checks every
      builder's **arity against the command table**, which is the authority. A builder
      that drifted from the table would send a request the server refuses
- [x] The client's **interaction layer** (`packages/client/src/interaction.ts`) turns each
      gesture into a request: selecting is local, and moving, placing, collecting,
      training and upgrading all become commands. The client checks what it can — a
      building still being constructed cannot be moved, and a unit cannot be upgraded —
      and the server decides everything else. A refusal there is a refusal of the
      **gesture**, not of the outcome
- [x] The client **never decides an outcome** — and that is a property of the code's
      *shape*, not a rule the renderer has to remember
      (`packages/client/src/predictions.ts`): the renderer asks the module what to draw,
      and the module answers with the server's confirmed state and the outstanding
      predictions as a **separate overlay**. A prediction can be drawn as an
      interpolation, and it can never be mistaken for something the server agreed to
- [x] The native forms carry **no claimed outcomes**: `end_attack` names the attack the
      server issued rather than sending the battle result, `collect` carries only the
      element's id so the client cannot choose its own collect period, and
      `win_daily_bonus` carries placeholders because the day and the reward are the
      server's
- [x] A **duplicate answer** — the same answer arriving twice — is reported as such
      rather than settled again, so it cannot undo a confirmed outcome, and the retry of
      a request that was lost in flight **replaces** its prediction rather than
      adding a second one
- [x] Input latency is hidden by local interpolation without ever showing an
      unconfirmed outcome as final

### G3 — The UI (rebuilt from scratch)

- [ ] Every screen in the B6 inventory is implemented, or explicitly dropped with a
      recorded decision. The inventory is the client's **260** screens, and **every one
      of them now carries a decision** (`re/data/ui-screens.json`):
      - **97 implemented** — the clone models the screen's behaviour, and the decision
        names the model that does it
      - **23 dropped**, each with its reason: the upstream's administrative panel (a
        panel that could edit the rules would be the `flash_debug` hole again), the
        cross-promotion to Zynga games that no longer exist, the screens that take
        **real money**, the Facebook friend hiring, the mobile-client notice, the
        video player and the robot picker
      - **140 planned** — in scope, the client's behaviour is real, and not modelled
        yet
      The decisions are **checked**, not believed (`packages/client/src/screens.test.ts`):
      every screen must have a decision, every implemented one must name a model that
      exists, and every dropped one must say why
- [x] The **HUD's model** is implemented (`packages/client/src/hud.ts`): the resources,
      the level, the population and the energy, and every popover's text — the
      client's own literals, including the "Build more Silos to get more space"
      warning and the max-population case. The **number formatting** is the client's
      exactly: the digits grouped in threes from the right and joined with commas, and
      grouped as a STRING, so a negative number comes out as "-1,234"
- [x] The **build menu** is implemented as a model (`packages/client/src/buildmenu.ts`):
      the tabs are the content's categories and their sub-categories, and each tab's
      list is ordered the client's way. The order is **not** the content's order: the
      items the player is too low a level for are pushed **10 000 down the list**, not
      hidden, so the player can still see them and know they exist. `itemUnlocked`
      **always returns false** in this build (`core/Base.as:7993-7995`), so the
      condition is simply the level, and the clone reproduces that rather than
      inventing an unlock system the client does not have
- [ ] The unit panel, minimap, neighbour strip, goal panel and popups all work
- [x] The **tooltips** are implemented as a model (`packages/client/src/tooltips.ts`):
      the HUD's four resource sentences are the client's own literals, and the info
      panel is built from the item's own statistics — the resource building shows its
      name, its resource and the amount it earns, and the unit shows its effective
      attack, range, velocity, life and population
- [x] The **text metrics** are implemented (`packages/client/src/fonts.ts`): the
      original faces' advance widths, scaled, so the substituted face occupies the
      same space and the game's boxes still fit. The scale is a **parameter**, not a
      constant, because it depends on which font file is actually shipped - a scale of
      1 means "not tuned yet", and the roadmap says so
- [x] The **substitutes are named and served under the names the client asks for**,
      and the languages are recorded: the client loads fonts for English, Turkish and
      Greek, and only the English ones ship, so the clone ships one set and falls back
      the same way
- [ ] Text renders with the substituted fonts at the original metrics
- [x] The client's **defence slot shows the attack interval**, in both the tooltip and
      the info panel. That is the client's behaviour in *both* places, so it is not a
      slip in one of them, and the clone reproduces it rather than "fixing" it — the
      client is the specification
- [x] The **"click here" guidance** is implemented (`packages/client/src/guidance.ts`):
      the goals panel's up-to-three "CLICK HERE!" badges, one on each of the three
      goal slots, marking the goals the player has not visited. The offset counts the
      **incomplete** goals only, so a completed goal does not take up a slot
- [x] The client's **quirk** in that guidance is reproduced and recorded: the check
      reads the *first* marker's clicked flag for all three markers, even though the
      client keeps three separate flags — so clicking the first badge suppresses all
      three, while clicking the second or the third suppresses only that one. It is
      recorded as a decision, not an accident
- [ ] The remaining tooltip surfaces (the icon panel's dictionary, the special units'
      attack tooltips and the market's) are reimplemented

### G4 — Feature parity

- [x] The **tutorial's steps are extracted** from the client's `TutorialMain.as`
      (`scripts/extract-tutorial-steps.mjs` -> `re/data/tutorial-steps.json`): **33**
      steps, each naming a place on the screen and what the player is expected to do
      there, with the arrow's anchor, rotation and alignment. The tutorial is not one
      list — it is a base list plus **conditional blocks** appended to it, so each step
      records the gate it sits behind and a player only sees the steps whose gate is
      true for them. The client's own step **order** is not the numeric order of the step
      constants, and the order is what matters
- [x] The tutorial's **state machine** is implemented
      (`packages/client/src/tutorial.ts`): the position is an index into the steps the
      player can see, a step may be skipped only when it says it may be, and a step is
      compared by its **number**, which is how the client resumes
- [ ] The tutorial and the first chapter are completable against the server
- [x] The **tutorial's progression is the server's**
      (`packages/rules/src/tutorial.ts`). The server owns **which steps exist**, so a
      client cannot invent one, and **how far the player has got**, which is the
      furthest step reached - the tutorial can be walked backwards, and the furthest
      step is the one that counts. The *order* is the client's, because the tutorial
      grants nothing by itself: it points at the actions, and the actions are commands
      the server already checks
- [ ] The **first chapter** is completable: the quest's steps, the rewards and the
      chapter's own unlocks are checked against the server
- [ ] Quests, goals, the darts minigame, magic and tech, the marketplace, premium and the
      weekly bonus are functional
- [ ] Alliances and the social features are functional, or visibly out of scope
- [ ] The daily/weekly bonus cycles and premium expiry behave correctly across a
      server restart

### G5 — Clients

- [x] The web build **runs in Chrome and Edge**, and it is **verified** rather than
      asserted: the built client is served and loaded in a real browser, and the page's
      own status is read back over the **DevTools protocol**
      (`node scripts/smoke-test-client.mjs`). The status is written by the client
      itself, so the check is not "did the browser not crash" but "**did the client
      start**" - and it says how many atlas pages it fetched
- [x] The client **signs in**: it sends a credential to `POST /api/session` and keeps
      the **session token** the server issues, in the browser's storage, so a player
      does not sign in on every visit. A stored session that has **expired** is
      forgotten rather than sent, and the token travels in the `Authorization` header
- [x] A browser that is **not on the machine** is reported as *not run* rather than as a
      failure: a machine without Firefox has not failed anything. Firefox and Safari
      are not on this machine, so they are **not run** here
- [ ] The client is run in **Firefox and Safari** as well, on a machine that has them
- [ ] The client is driven through a **complete play session** end to end, from signing
      in to finishing the tutorial
- [ ] The desktop build (Tauri) runs on Windows, macOS and Linux
- [ ] The mobile build (Capacitor) runs on Android and iOS
- [ ] The game is playable at the original resolutions and scales cleanly to phone screens
- [x] The **stage's layout is a model** (`packages/client/src/stage.ts`): the stage is the
      client's own **760 by 600**, and it is **scaled** to fit rather than reflowed,
      because the game's layout is not fluid and reflowing it would put the panels on
      top of each other. The scale is the largest that fits, **capped at 1** - a bigger
      window does not make the game bigger - and a **whole number** where it can be, so
      the pixel art stays sharp
- [x] The layout knows when the window is in **portrait**, and when the text is **too
      small to read**: the scale that *fits* is judged separately from the one that is
      *used*, because the used one is floored and asking about it would find nothing
- [ ] The game is played on an **actual phone**, and the touch controls are there

**Exit criteria:** a new player completes the tutorial and a quest in every shipped client.

---

## Group H — Desktop Shell & Release

*Outcome: a standalone, signed, updatable desktop executable.*

- [x] The **Tauri shell** launches the client, manages the window, and exposes the
      local persistence layer (`apps/desktop/src-tauri/`). The shell is a **window and
      a local server**, with no game logic of its own: the game is the clone's own web
      client, and the shell points a web view at it. The window is the client's own
      **760 by 600** stage - the numbers `TutorialMain.as` carries - and it will not go
      below it, because the game's layout is not fluid. The shell is a library with a
      thin binary, so the whole of it is testable without opening a window, and its
      tests cover the server choice, the URL and the window's size
- [x] The shell starts the **local server itself**, so a player needs nothing
      installed, and it waits for the server's health check before the window is
      pointed at it - so the client's first request does not fail. The server does
      not outlive the window
- [x] **The app never requires Flash, a Flash plugin or a Flash browser**, and it is
      **verified** rather than asserted (`node scripts/check-no-flash.mjs`): no `.swf`
      file is in anything that ships, no shipped file references the Flash Player, the
      `ShockwaveFlash` plugin, `flashvars` or the `application/x-shockwave-flash`
      type, and the shipped tree has no Flash runtime component. The check is in the
      CI, and it is proven to fire: it fails on a SWF and on the MIME type
- [x] The game works with the server on **`localhost`** and against a **remote**
      server. The shell's first job is the choice: `--server <url>` points the web view
      at somebody else's server, and anything else starts the local one. Both are
      covered by the shell's tests
- [ ] The remote server's **certificate** is checked and the address is shown to the
      player before the game connects to it
- [ ] Offline single-player works via the in-browser rules engine over PGlite, with the
      same schema as the server
- [ ] Installers are produced for Windows (`.msi` + `.exe`), macOS (`.dmg`) and Linux
      (`.deb`/`.AppImage`)
- [ ] The binaries are code-signed, and the macOS build is notarised
- [ ] Auto-update is configured, and a failed update rolls back cleanly
- [x] The shipped client contains **no** Adobe Flash Player component and no SWF
      runtime, and the check that proves it is in the CI

**Exit criteria:** a clean machine installs the app and plays the game.

---

## Group I — Production Readiness

*Outcome: the project can be operated, secured, observed and released like a real
product.*

### I1 — Testing
- [x] The **roadmap's item counts are checked**, so an item cannot be silently
      swallowed. Each group has a **floor** - the number of items it had the last time
      somebody looked - and a group with fewer items than its floor is a failure
      (`packages/client/src/roadmap.ts`, `node scripts/check-roadmap.mjs`). The floor is
      a file, so raising it is a deliberate act rather than a side effect of an edit
- [x] The floor exists because a block-end rule that ended an item's block at the next
      **blank line** ate fourteen items across two groups - the items are packed with
      no blank line between them - and the road was only noticed because the counts
      were compared. Every item that was ever in the roadmap is back

- [x] **Unit tests cover the rules engine, the economy and the command handlers.** The
      rules engine's own files are at 89 % and above, the economy at **100 %** of its
      lines, and the applier's command handlers at **97 %** - and the whole
      **command surface** is exercised end to end against a real database
      (`apps/server/src/command-surface.test.ts`)
- [x] The coverage is **measured** and a **threshold is enforced** - see the item below
- [x] The **golden-master harness runs in CI and is a release gate**. It is in the
      CI on every push and every pull request, and it is the **gate** of the release
      workflow (`.github/workflows/release.yml`): a tag cannot be released unless the
      corpus matches with no unexplained difference. The harness fails on any
      difference it cannot explain, so a release cannot carry a rules change nobody
      noticed
- [x] **Integration tests cover the full command surface against a real database**
      (`apps/server/src/command-surface.test.ts`). Every one of the **94** commands in
      the table is sent through the HTTP endpoint, over a **PGlite** database, with a
      session, and the test asserts that:
      - no command answers with a **5xx**: a command the server cannot make sense of is
        a typed refusal, not a crash
      - every refusal **says why**
      - the commands whose argument shape the protocol knows reach the **applier** -
        and most of them do, so the test is testing something
      - the player's save is still **readable** after every command
- [x] The arguments come from each command's **own specification** in the table, so
      the test cannot drift from the catalogue
- [x] **End-to-end tests drive the web client through a complete play session**
      (`node scripts/e2e-test.mjs`). Nothing in it is a stand-in:
      - the **real server** is started, with a real database
      - a player is **registered** through `POST /api/account`, and the credential is
        **persisted**
      - the **real client** is served and loaded in a **real browser**
      - the client **signs in** and fetches its world
      - the client sends a command - **its own request builder** and **its own
        transport** - and the **server's own rules** decide the outcome
      - the player signs in **again**, in a fresh server over the same database, from
        the persisted credential
- [x] The client's **transport** is implemented (`packages/client/src/transport.ts`):
      the envelope has the protocol version, the idempotency key and the session
      token, and **no room for a claimed outcome**
- [x] A **load test** sustains the target concurrency with correct simulation timing
      (`node scripts/load-test.mjs`). The two halves are checked separately, because a
      server that is fast and wrong is worse than one that is slow and right:
      - **correctness**: every command that was sent was answered exactly once, and
        the errors are counted
      - **performance**: the ninety-fifth percentile of the request time, the
        ninety-fifth percentile of the **simulation** time, the throughput and the error
        rate are measured and compared against the **performance budgets**
- [x] The simulation time is the **server's own** measurement, read from its metrics,
      because the request's wall time includes the network and the database and the tick
      is the part the player feels
- [x] **Test coverage is measured and a threshold is enforced**
      (`node scripts/check-coverage.mjs`). The floors are **85 %** of the lines, **80 %**
      of the functions and **70 %** of the branches, and the measurement is Node's own
      - so there is no extra dependency and no second opinion to reconcile. The
      branches are lower than the lines because a branch is a *decision*, and one that
      is not taken is often one that **cannot** be taken
- [x] The gate is in the CI, and it **fails** below the floors - which is the point: a
      coverage number that is only reported is a number that quietly goes down

### I2 — CI/CD

- [x] **Every push** runs typecheck, lint, unit, integration and the content/asset
      build (`.github/workflows/ci.yml`). The push trigger used to be `main` only, so a
      branch's own pipeline did not run until it was merged; it runs on every branch
      now. The gate is: the vendored upstream is verified, the type-check and the
      lint pass, the unit and the integration tests pass, the golden-master corpus
      matches, the soak test finds no drift, the content bundle builds and is
      **reproducible**, the command catalogue agrees with the client, and the asset
      manifest agrees with the tree in **both directions**
- [ ] A real linter is configured. `pnpm lint` is currently the type-check, so the
      lint step in CI is the type-check wearing a different name
- [x] **Every pull request runs the golden-master harness.** The CI runs on every push
      and every pull request, and the golden-master corpus is one of its steps - and
      the harness fails on any difference it cannot explain
- [ ] Branches are protected and require a green run plus review
- [ ] Release artefacts are produced automatically and published to a release
- [ ] The pipeline is reproducible and re-running it yields the same artefacts

### I3 — Security

- [x] **Secrets are managed outside the repository, and no credential is committed.**
      The repository is **scanned** for the shapes a credential takes - an AWS key, a
      private key, a GitHub token, a Slack token - and the scan is a test
      (`packages/server/src/security.test.ts`), so it fails the build rather than
      being noticed later. The workflows hold no credentials of their own
- [x] **Dependency scanning runs in CI, with a policy for what blocks a release.**
      The policy is **written down** rather than left to the tool's default, because
      the default changes: a **high** or **critical** advisory fails the run, and a
      moderate one does not. There is no container yet, so there is nothing to scan;
      the policy covers it when there is one
- [x] **All input is validated at the boundary, and the server has no injection
      surface.** The boundary validates (`validateRequest`), the body is capped, and
      the SQL is **scanned** (`packages/server/src/security.test.ts`): a value is
      never interpolated into a statement, a statement with a placeholder always
      passes its values as parameters, and the only thing that can be interpolated -
      a table name, which SQL has no placeholder for - is **checked**
- [x] The scan **found two real holes** and they are closed: both stores put their
      table name into the SQL, and the name came from a constructor option, so it is
      now checked as a plain identifier before it is used; and the backup's digest
      did the same
- [x] **Rate limiting and abuse protection are in place on every mutating endpoint.**
      The limiter runs **before the routing**, so it covers every endpoint rather than
      the ones somebody remembered (`apps/server/src/limits.ts`), and a test proves
      it for the three mutating ones: `POST /api/command`, `POST /command.php` and
      `POST /api/session`. It is a fixed window, which is not the most precise limiter,
      but it is exact enough to stop a runaway client and it needs no background timer
- [x] The limiter is **per account** rather than per address, so a player behind a shared
      address - a household, a school, a company network, a phone carrier's NAT - is not
      punished for the other people behind it, and a player who changed address does not
      lose their limit. The key is the **player**, taken from the session the request
      carries, which is possible because the token is in the header rather than the body.
      A request with no session falls back to its address, because that is all there is
- [x] **Session tokens are scoped, revocable and expire**
      (`packages/server/src/session.ts`, `packages/server/src/session.test.ts`):
      - **scoped** - a token resolves to exactly the player it was issued to, and a
        session never names another player
      - **revocable** - one token or every session of a player, immediately, and the
        revocation says whether there was one
      - **expiring** - a session has a lifetime (thirty days by default), and an
        expired one is refused **and forgotten** rather than kept
      The password is not stored: the credential is a salt and a hash, and the test
      checks that the store's own text does not contain the password
- [ ] A security review of the auth, command and shim layers is completed
- [x] The **client is not trusted for anything**, and the **cheat battery is re-run on
      every release** (`node scripts/run-cheat-battery.mjs`, and it is in the release
      workflow's gate). Eleven attacks, each run against the **real** authority layer,
      each of which must have no effect
- [x] The battery is **mutation-tested**: eighteen weakenings of the authority layer
      were each detected by exactly the attack they weaken. That is what makes a
      passing battery evidence rather than a formality

### I4 — Observability

- [x] **Structured logs with a request id that ties a client action to a server
      command.** One JSON line per request (`packages/server/src/observability.ts`),
      with a request id that travels back in the response's `x-request-id` header, so a
      player can quote it and the exact request can be found. The client's own id is
      **reused** when it sends one, so its correlation id survives into the log. The
      line carries the path, the method, the status, the duration, the player and the
      **names of the commands** the request applied and refused
- [x] The lines are JSON rather than prose because prose cannot be queried: a log you
      cannot filter by a player id or a command name is a log you only ever read with
      your eyes
- [x] **Metrics for latency, command throughput, error rate, simulation tick time and
      active sessions.** Counters, gauges and histograms, with the labels a dashboard
      needs, and served as JSON at **`/api/metrics`**:
      - `http_request_duration_ms` — the latency, bucketed
      - `http_requests_total` and `http_errors_total` — the throughput and the error
        rate, by path, method and status
      - `commands_total` and `command_duration_ms` — the command throughput, by the
        command's name
      - `simulation_tick_ms` — how long the rules engine took
      - `active_sessions` — a **gauge**, because it goes up and down
- [ ] The metrics are exported to a time-series database, so the alerts below can fire
      on a regression rather than on a snapshot
- [ ] Distributed tracing across the client, the API and the database
- [x] **Error reporting captures crashes with the build and content version attached.**
      The server's own crash handler records the error with the **server's version**, the
      **content bundle's build id** and the **asset bundle's build id**, so a crash
      report says what was running when it happened
- [x] **Alerts fire** on error-rate, latency and tick-time regressions
      (`packages/server/src/health.ts`). The thresholds are **written down** in
      `ALERT_RULES` rather than being whatever the code happens to compare against, and
      each rule says **what to do about it**. A critical alert makes the server
      *unhealthy*, a warning makes it *degraded*
- [x] The alerts are **sent** somewhere - a **webhook** - and the sending is **retried**
      (`packages/server/src/alerts.ts`). The server is told with `SWL_ALERT_WEBHOOK`,
      and a report that nobody reads is not an alert
- [x] The sending is retried with a **growing wait**, so a webhook that is down is
      not hammered, and a failure is **recorded rather than thrown**: a server that
      cannot reach the alerting system must still serve its players
- [x] A report is sent when the status **changes**, not every time it is checked - an
      alert that repeats every second is an alert that gets muted
- [x] A **dashboard** shows the live server health and the **content/asset version in
      use** (`/dashboard`), and the machine-readable report is at `/api/health`
      (`packages/server/src/health.ts`). The versions are at the top, because the first
      question about a bad server is "what was running?"
- [x] The **measurements** are the five an operator watches: the error rate, the
      ninety-fifth percentile of the request time, the ninety-fifth percentile of the
      simulation time, the active sessions and the command rate. The percentiles come
      from the **bucketed** histograms, so they are the bucket the percentile falls in
      and not an exact value - which is enough to alert on and honest about what it is

### I5 — Operations

- [x] **Deployment is scripted, repeatable and reversible**
      (`node scripts/deploy.mjs --data <dir>`). The steps are in one order, with no step
      depending on what somebody remembered to run first:
      1. **verify** the tree - the vendored upstream is unmodified, the content bundle
         builds and is **reproducible**, the type-check and the tests pass, and the
         cheat battery catches nothing
      2. **back up**, and **verify the backup** by comparing the digest of the
         snapshot with the digest of the live database. A backup that was not verified
         is not a backup, and the deploy does not go ahead if the two differ
      3. **migrate** the schema forward
      4. report the version and how to undo it
- [x] The deploy is **reversible**: `--rollback` restores the most recent snapshot, and
      the digest of the restored database is printed so the restore can be checked
- [x] **Database migration runs as a gated deploy step, with a tested rollback.** It is
      the third step of the deployment, and it runs in its own transaction, so a
      failure leaves the schema at a version the server understands. The rollback is
      **tested**: the schema's tests roll a migration back, roll it back again, and
      check that the history says so
- [x] The deployment **rolls back by itself** when a step fails, and the digest of a
      database that has not been migrated yet is a digest of nothing rather than an
      error - so a first deploy does not fail on a table that is not there yet
- [x] **Backups are verified**, and the deploy does not go ahead if the snapshot's
      digest differs from the live database's. A backup that was not verified is not a
      backup
- [x] **A restore has been rehearsed**: the tests write a database, back it up,
      change the live database, restore the snapshot and check that the snapshot
      still holds the **old** state - and the digest is what proves the two match
- [x] **Backups run automatically on a schedule**, and the schedule is **monitored**:
      - `node scripts/backup-server.mjs --data <dir> --out <dir> --every <hours>` takes
        the backup **repeatedly**, which is what a server does rather than what a person
        does, and it **prunes** the old snapshots, because a backup nobody can delete is
        a disk full rather than a backup
      - `node scripts/check-backups.mjs --out <dir>` **fails** when the newest snapshot is
        too old, or when there are none at all - a schedule that has stopped is invisible
        until the day it is needed
- [x] A **runbook** covers a stalled deployment, a database failure, corrupted player
      state, a content-bundle rollback and an emergency player reset
      (`docs/RUNBOOK.md`). It is organised by **failure** - what it looks like, and what
      to do about it - and it names the command for each step
- [x] A **documented procedure** exists for pushing a hotfix to the rules engine
      (`docs/HOTFIX.md`). It leans on the engine's **purity**: a rule takes its inputs
      and a seed and returns an answer, so a hotfix cannot have a side effect, cannot
      depend on when it runs, and can be **replayed** - which is what makes rolling one
      back a redeploy rather than a migration
- [x] The procedure names what must **never** be hotfixed: the content, the protocol, and
      anything that weakens the authority layer

### I6 — Legal & licensing

- [x] **The asset licensing position is settled and written down**
      (`docs/LICENSING.md`). The position:
      - the **shipped product contains no Zynga asset and no Zynga code**
      - the **upstream is vendored unmodified**, as a reference and a test oracle, and
        is **never linked into the shipped product** - so the shipped product is not a
        derivative work of it
      - the **rules are reimplemented from the client's observed behaviour**, and the
        clone's source contains no copied ActionScript
      - the **art and the audio must be re-created or licensed** before any public
        release. Until they are, the project is a preservation and a study: the code
        is free and the analysis is published, and the game itself is not distributed
- [x] The position's claims are **checked**, not asserted
      (`node scripts/check-licensing.mjs`): the upstream's licence is the GPL v3, **no
      package imports from the upstream**, and the shipped tree carries no SWF, no
      sound and none of the client's proprietary fonts. The check is in the CI and it
      is proven to fire
- [x] The **vendored upstream tree keeps its GPL-v3 notices** and is **not linked
      into** the shipped product. The tree is byte-for-byte the upstream's, with its
      `LICENSE` and its `README` intact, and `upstream/PROVENANCE.md` records where
      it came from and how it was verified. The check proves the second half: no
      package imports from it, so the shipped product is not a derivative work
- [x] The upstream's **obligations** are recorded rather than assumed: the tree
      travels with its source, the tree is not linked into the product, and the tree
      carries no warranty
- [x] **Third-party asset licences are enumerated and compliant**
      (`docs/LICENCES.md`, generated by `node scripts/build-licence-report.mjs`). The
      JavaScript and TypeScript dependencies, the direct Rust crates, the size of the
      crate tree, the two substitute **fonts** and the fact that there are no assets at all
- [x] The enumeration is **checked**, not asserted: a dependency that is not classified
      **fails the build**, so a new one has to be looked at before it can be used, and a
      licence that is not one that may be shipped fails it too
- [x] The **attribution and preservation notices the original project makes are
      carried** (`docs/ATTRIBUTION.md`). The upstream asks for two things: its
      **contributors** are credited, and its **community** is where its bugs are
      reported. Both are carried, and the upstream's own `LICENSE` and `README` travel
      with the tree. The game's own rights - Zynga's - are stated, and the
      dependencies' licences are enumerated
- [ ] A **request for correction** is honoured: if someone who owns the rights to
      anything here wants it changed, removed or credited differently, the notice says
      so, and the request is answered

### I7 — Documentation

- [x] A **developer guide** covers the architecture, the content pipeline, the asset
      pipeline, how a command travels, how to write a rule, the tests and the rules of
      the repository (`docs/DEVELOPING.md`)
- [x] A **runbook** covers operating the server and the desktop build
      (`docs/RUNBOOK.md`), and a **user guide** covers installing and playing
      (`docs/PLAYING.md`)
- [x] A **user guide** covers installing and playing (`docs/PLAYING.md`): what you
      need, how to register, how the game plays, and **what is different** from the
      original - no Facebook, no Zynga's art, some assets missing, and small servers
- [x] The **`re/` report set is kept in sync with the implementation**
      (`node scripts/check-report-sync.mjs`). The report set states **numbers** - how
      many commands, items, goals and unit delegates - and those are facts about the
      code as well as about the analysis, so they are **checked**: a number that has
      changed in one and not the other fails the build. A report set that has drifted is
      worse than none, because it is the thing somebody trusts
- [x] **Every architectural decision has a written rationale** (`docs/adr/`). Eighteen
      records, each with a **context**, a **decision**, the **alternatives** that were
      considered and the **consequences** - because a decision without a rationale is a
      decision somebody will quietly reverse, and the alternatives are the part that
      matters
- [x] The records are **checked**: each must have its four sections, a status, and
      alternatives that say something, and the numbers must be a sequence with no gaps
      (`node scripts/check-adrs.mjs`). The index is regenerated by the same script, so it
      cannot drift from the records
- [x] The roadmap's **"Locked Decisions" section** is the summary and these are the
      whole reasoning - and the two agree

### I8 — Performance & release

- [x] **Performance budgets are defined and met**
      (`packages/server/src/budgets.ts`). They are **written down**, so "fast enough" is a
      decision rather than an impression, and they are stated at the **ninety-fifth
      percentile**, because a budget on the mean says nothing about the players who are
      having a bad time:
      | Budget | The floor |
      |---|---|
      | the request latency | 200 ms |
      | the simulation tick | 50 ms |
      | the command throughput | 50 a second |
      | the error rate | 1 in 100 |
      | the **input-to-render** latency | 250 ms |
- [x] The **input-to-render** latency is measured too: the client sends a command, the
      server answers, the client fetches the world again and draws it, and the whole
      round trip is timed. It is the number the **player** waits, and it is measured in a
      **real browser** by the end-to-end test
- [x] The client **draws the server's answer**: the native answer carries the outcomes and
      not the world, so the world is fetched again and drawn. The client asks, the server
      decides, and the client draws what the server said
- [ ] The **input-to-render** latency is measured too: the client sends a command and the
      player sees the result, and that is a number the browser has to answer for
- [ ] The client holds a **stable frame rate** on the largest documented battle
- [ ] The client holds a stable frame rate on the largest documented battle
- [x] The **asset bundle size is measured and minimised**
      (`node scripts/build-client-manifest.mjs`). The asset pipeline's manifest holds
      **every** image the client's SWFs contain - 254 155 images and 41 198 symbols,
      **118 MB** of JSON - and the browser cannot be sent that
- [x] The client gets its **own** manifest, holding only the symbols the content's
      items refer to, and only the images those symbols use: **853 symbols, 4 639
      images and 3.9 MB** - a **31 times** reduction
- [x] The trimming is at the right level because the client instantiates the SWF's
      **root** and picks the drawing by its frame number
      (`IsoElement.setGraphic`: `new sheetDictionary[img_name]()` and
      `gotoAndStop(frame + 1)`), so the sheet is the only symbol it needs
- [x] The reduction is **checked**, not asserted: the client's manifest has to be
      under a tenth of the pipeline's, to hold only the symbols the items ask for, to
      hold one symbol per SWF, and to have an image for every frame it names
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
