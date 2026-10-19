# Social Wars Legacy

**A cross-platform, Flash-free re-implementation of Zynga's *Social Wars* — client and server.**

The original game is a Flash application from 2012. Adobe Flash is dead, the original
backend is gone, and the community preservation project that kept the game alive is a
Python server that trusts the client for almost everything. This project rebuilds the game
properly: a modern client, an authoritative server, and a standalone desktop executable —
with the original game's behaviour reproduced from the original client's own code.

> **Status: investigation complete, build started.** Everything needed to rebuild the game
> is documented and evidenced in [`re/`](re/README.md). The upstream project is vendored
> and byte-for-byte verified, the pnpm workspace exists, and the content pipeline builds a
> validated, hashed content bundle from the original 2012 config. The client, server and
> desktop shells are next.

---

## Why this exists

The community preservation project (`AcidCaos/socialwarriors`) keeps the game playable by
shipping the **original Flash client** against a re-implemented Python backend. That works,
but it has two hard limits:

1. **It requires Flash.** The recommended setup is a fork of Chromium with the Adobe Flash
   Player embedded. Flash Player 32 is the last version that works, and it is EOL.
2. **It cannot be trusted.** The server applies the client's own declared resource deltas,
   accepts client-declared combat outcomes, and has no authentication at all. Every player
   can act as every other player, and can grant themselves unlimited gold.

The full findings are in [`re/docs/`](re/docs/). The short version:

| | |
|---|---|
| The original server signing key | **Recovered and verified live** — `HMAC-SHA256("4vVSD8dftv6hdfb1Hnk9", payload)` reproduces the client's own 64-hex `data` prefix byte-for-byte |
| The game rules | **Fully recovered** from 1 387 decompiled ActionScript 3 classes: the damage pipeline, 15 special attacks, unit progression, the economy, the quest and goal systems |
| The wire protocol | **Fully specified** and confirmed against 1 664 captured live requests |
| The content | 900 items, 104 globals, 100 levels, 134 goals — plus 3 199 asset files (716.8 MB) |

---

## Documentation

| | |
|---|---|
| **[`re/README.md`](re/README.md)** | **The document map.** Start here. |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | Project router, constraints, context-loading rules |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | The production roadmap: Groups A–I, locked decisions, critical path |
| [`AGENTS.md`](AGENTS.md) | How to work in this repository |

### The report set

| Document | Covers |
|---|---|
| [00 — Executive Summary](re/docs/00-EXECUTIVE-SUMMARY.md) | The cross-cutting findings and the rewrite thesis |
| [01 — Network & Protocol](re/docs/01-network-protocol.md) | 24 endpoints, the flashvar contract, the HMAC framing, map flavours |
| [02 — Combat & Units](re/docs/02-combat-and-units.md) | The damage pipeline, damage types, special attacks, counters, unit XP |
| [03 — Commands, Economy, Quests, Goals](re/docs/03-commands-quests-economy.md) | The 94-row command catalogue, economy rules, quest state machine, goal system |
| [04 — Python Server & Data](re/docs/04-python-server-and-data.md) | Route table, save schema, config pipeline, build/packaging, risk register |
| [05 — Assets & Content](re/docs/05-assets-and-content-pipeline.md) | Asset taxonomy, config→asset resolution, the 778-row table, conversion plan |
| [06 — Live Session Protocol](re/docs/06-LIVE-SESSION-PROTOCOL.md) | The observed wire traffic, the verified signature, how to reproduce it |
| [07 — REA Evidence Log](re/docs/07-REA-EVIDENCE.md) | What REA could and could not establish, and where other tools took over |
| [08 — Clone Roadmap](re/docs/08-CLONE-ROADMAP.md) | The detailed workstream breakdown |
| [09 — Limitations & Open Questions](re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md) | What we do **not** know, upstream bugs, open questions |

### Evidence

[`re/evidence/`](re/evidence/) holds the raw material: the captured HTTP traffic, the decoded
command batches, the HMAC verification, artefact digests, the full SWF tag dump, and
thirteen screenshots of the game running.

---

## Stack

Decided and locked — see the roadmap's *Locked Decisions* section.

| Layer | Choice |
|---|---|
| Game client (web) | TypeScript + **PixiJS v8** (WebGL2 isometric world) + **React** (DOM UI) |
| Desktop shell | **Tauri v2** over the same web client |
| Mobile shell | **Capacitor** over the same web client |
| Server + rules engine | **TypeScript** on Node.js 26, one shared rules engine |
| Database | **PostgreSQL** + Drizzle (PGlite offline for single-player) |
| Packages | pnpm workspaces |

**Why TypeScript for the rules engine?** The 229 unit delegates are 1.32 MB of bespoke
ActionScript — the single biggest and most intricate port — and they must be iterated
against the original client. The same engine has to run in Node (multiplayer) and in a
browser worker (offline). One language does both; Rust would need a second WASM build.

**Why Tauri?** The asset payload dwarfs any shell difference, so Tauri's usual size
advantage is moot — but native windows, menus and trays, no Chromium version drift, and
clean auto-update still win. WebView2 on Windows is Chromium 120+, so WebGL2 is fine.

---

## Project layout

```
.
├── AGENTS.md              # how to work in this repository
├── README.md              # this file
├── package.json           # the pnpm workspace root
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── docs/
│   ├── CONTEXT.md         # project router and constraints
│   └── ROADMAP.md         # the production roadmap, Groups A–I
├── packages/
│   ├── protocol/          # @swl/protocol — the wire types, the resource vector, the save document
│   ├── content/           # @swl/content — the content build: config + patches -> a hashed bundle
│   └── rules/             # @swl/rules — the deterministic simulation core
├── re/                    # the reverse-engineering report set
│   ├── README.md          # the document map
│   ├── docs/              # 16 analysis documents + items-assets.csv
│   ├── data/              # 9 machine-readable datasets
│   └── evidence/          # raw captured traffic, digests, screenshots
├── scripts/               # the analysis and build tooling
│   ├── verify-upstream.mjs # the provenance check
│   ├── pull-assets.mjs     # a targeted Git LFS pull
│   ├── decompile-client.mjs
│   └── analyze-*.mjs       # the B-group extractors
└── upstream/              # the vendored upstream project, verbatim, GPL v3
    ├── PROVENANCE.md
    ├── MANIFEST.sha256
    └── socialwarriors/
```

## Working on it

```bash
pnpm install          # install the workspace
pnpm test             # run the test suite
pnpm typecheck        # type-check everything
pnpm build:content    # build the content bundle
node scripts/verify-upstream.mjs   # prove the vendored upstream is unmodified
```

---

## Roadmap at a glance

```
A ──► B ──► C ──► D ──┐
         │             ├──► E ──► F ──► G ──► H ──► I
         └─────────────┘
```

| Group | Milestone |
|---|---|
| **0** | Investigation & documentation — ✅ complete |
| **A** | Vendor the upstream project with provenance and Git LFS — ✅ complete |
| **B** | Complete the evidence sweep: 58-build diff, full SWF corpus, 229 unit delegates, 28 quests, 134 goals, 403 UI screens, social contracts — ✅ complete except the live PvP capture |
| **C** | Monorepo, typed content pipeline, protocol types — ✅ complete |
| **D** | Asset pipeline: 1 116 SWF → frame atlases, audio, fonts |
| **E** | Rules engine: combat, economy, quests, goals — deterministic and golden-master verified |
| **F** | Authoritative server: real auth, server-side economy and combat, Postgres, protocol shim |
| **G** | Modern client: renderer, interaction, the rebuilt UI, feature parity, three platforms |
| **H** | Desktop shell, installers, code signing, auto-update, offline play |
| **I** | Production readiness: tests, CI/CD, security, observability, operations, licensing, docs |

Full detail, exit criteria and checkboxes in [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## Reproducing the investigation

The analysis is fully reproducible. See
[`re/docs/06 §8`](re/docs/06-LIVE-SESSION-PROTOCOL.md#8-reproducing-this-session).

```bash
# Serve the upstream project with a request tracer (does not modify it)
python upstream/socialwarriors/server.py --host 127.0.0.1 --port 5055

# Drive the real Flash client over the DevTools Protocol
node tools/cdp.js navigate "http://127.0.0.1:5055/"
node tools/drive.js run "click 1248 686
wait 3000
shot frame.png"

# Verify the recovered signing key against a captured payload
python tools/verify_hmac.py "<captured data= value>"
```

The live session was driven with a real Adobe Flash Player (bundled in Flashy Browser 1.2.4)
against the local server: **1 664 requests, 294 distinct paths, 34 command batches, 17
distinct command names**, including a completed Mission 1 assault whose `end_quest` report
was captured verbatim.

---

## Licensing

Two separate licences apply, and the distinction matters:

| | Licence |
|---|---|
| The upstream **code** (`upstream/`, the Python server) | **GPL v3** — the vendored copy keeps its notices and is not linked into the new client's source |
| The upstream **content** (sprites, audio, config, fonts) | **Zynga's** — not GPL. The upstream project itself relies on archival exemptions (PCCPSACT, EFGAMP, UNESCO PERSIST, Flashpoint) |

**The asset licensing position must be settled before any public release.** It is tracked
as a release gate in Group I of the roadmap. Until then, builds are private.

---

## Contributing

Read [`AGENTS.md`](AGENTS.md) first — it defines the working method, the branch workflow
and the autonomous execution mode.
