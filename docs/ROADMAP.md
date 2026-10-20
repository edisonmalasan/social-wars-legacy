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
      `11f1de0358b69d8ca3be91e1d8dc06f232ce49d0dd7ec79dbdd33204f540b5e3`
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
- [ ] The full run over all **1 116 SWF files outside `assets/flash/`** is executed and the
      complete manifest is committed
- [ ] The 58 `Basesec_1.5.x.swf` builds (239.7 MB) are handled separately: `Basesec_1.5.4.swf`
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
- [ ] The 4 proprietary fonts are replaced with permissively-licensed equivalents and the
      text metrics are tuned to match
- [x] `assets/swf/dynamic2.swf` is decompiled and analysed — it is the **runtime library**:
      it embeds **28 sounds the server's config never mentions** (all unique, none
      duplicating a standalone file) and the **building-construction animations**, which
      explains why some items appear to have no art
      ([`../re/docs/17-asset-pipeline.md`](../re/docs/17-asset-pipeline.md) §7)
- [x] The 4 sprites above the 4 KiB ABC threshold are audited — they are ordinary
      animation timelines with many named frames, not special logic. **Nothing to act on.**
- [ ] The 28 embedded sounds are added to the audio set
- [ ] The construction animations from `dynamic2.swf` are included in the conversion
- [ ] A viewer exists that renders every item at 3 zoom levels, so missing art is visible
      immediately
- [ ] The client can be built with a **content-hashed** asset bundle, so a stale cache is
      impossible

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
- [ ] Unit XP accrues from effective damage to units only, with the documented thresholds
      and the level-9 cap (+30 attack, 3× HP)
- [ ] All 10 damage classes and all 15 special attacks behave as documented

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
