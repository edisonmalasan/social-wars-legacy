# Developing Social Wars Legacy

This is the guide for working on the project. It covers the shape of
the code, the two pipelines, how to run the checks, and where the
decisions are written down.

For operating a server, see [`RUNBOOK.md`](RUNBOOK.md). For playing,
see [`PLAYING.md`](PLAYING.md). For the decisions and their reasons,
see [`adr/`](adr/).

## The shape of it

```
packages/protocol   the wire types: the command table, the legacy framing
packages/content    the content pipeline: the config and the deltas
packages/rules      the rules engine: the game, as pure functions
packages/server     the server: sessions, the shim, the store, the applier
packages/client     the client core: the projection, the depth sort, the atlas
apps/server         the server's socket and its entry point
apps/client         the web client: the scene, the renderer, the shell
apps/desktop        the Tauri desktop shell
```

The rule that shapes all of it: **the client draws and the server
decides**. The rules engine is pure and deterministic, the server owns
every outcome, and the client sends requests and renders the answers.

### The three that must agree

- `@swl/protocol` holds the **command table** — 94 commands, each with
  its argument shape. It is the authority: a client request builder is
  checked against it, and so is the shim.
- `@swl/rules` holds the **rules** — the damage pipeline, the economy,
  the quests, the goals, the battle simulation. Every one of them is a
  pure function of its inputs and a seed.
- `@swl/server` holds the **authority** — it applies the rules, computes
  the costs, and decides what a command did.

## Getting it running

```bash
pnpm install          # the workspace
pnpm build:content    # the content bundle, from the config and the deltas
pnpm test             # the unit tests
pnpm typecheck        # the type-check, over every package
```

The server:

```bash
pnpm --filter @swl/app-server dev
```

The client:

```bash
pnpm --filter @swl/app-client dev
```

The client needs a few generated files, which are **committed** so that
a clone can build it without the asset pipeline:

```bash
node scripts/build-client-manifest.mjs    # the client's own manifest
```

### The checks

| What | Command |
|---|---|
| The unit tests | `pnpm test` |
| The integration tests | `pnpm test:integration` |
| The type-check | `pnpm typecheck` |
| The coverage | `node scripts/check-coverage.mjs` |
| The golden master | `node scripts/golden-master.mjs` |
| The command catalogue | `node scripts/verify-command-catalogue.mjs` |
| The cheat battery | `node scripts/run-cheat-battery.mjs` |
| The vendored upstream | `node scripts/verify-upstream.mjs` |
| The licensing position | `node scripts/check-licensing.mjs` |
| The decision records | `node scripts/check-adrs.mjs` |
| The roadmap's items | `node scripts/check-roadmap.mjs` |
| The load test | `node scripts/load-test.mjs` |
| The web client, in a browser | `node scripts/smoke-test-client.mjs` |
| A whole play session | `node scripts/e2e-test.mjs` |
| The soak test | `node --expose-gc scripts/soak-server.mjs` |

All of them are in the CI, and all of them are in the command table in
[`../AGENTS.md`](../AGENTS.md).

## The two pipelines

### The content pipeline

The content is the original server's configuration, and it is
**assembled**, not copied:

```
upstream/socialwarriors/config/main.json   the 29-August-2012 capture
upstream/socialwarriors/config/patch/*.json  five JSON-Patch deltas
                    |
                    v
      packages/content/src/build.ts
                    |
                    v
  packages/content/dist/content-bundle.json
```

The build is **reproducible**: the same inputs give a byte-identical
bundle and the same build id, and the id is recorded in the roadmap.
It **fails** on an unknown key or a dangling id.

The bundle carries the items, the globals, the categories and the
quest and goal tables. The server's cost table is built from it, and
the client's manifest is built from it.

### The asset pipeline

The client's art is **converted, trimmed and packed**:

```
upstream/socialwarriors/assets/swf/*.swf
                    |
                    v
     scripts/convert-assets.mjs    decompile, render, dedupe by hash
                    |
                    v
       .work/frames/store/*.png    the store: one file per distinct image
                    |
                    v
      scripts/pack-atlases.mjs     trim to the alpha bounds, pack
                    |
                    v
       .work/frames/atlases/*.png   11 865 sheets of 2048 by 2048
```

The conversion is **resumable** and so is the packing, and both cache
what they have done: a restart skips the work rather than redoing it.
The manifest — `re/data/frame-manifest.json` — records where every
image ended up, and it is **148 MB and not committed**: it is a build
artefact, and GitHub will not take a file that big.

The **client's** manifest (`apps/client/public/frame-manifest.json`) is
3.9 MB, holds only the symbols the content's items refer to, and *is*
committed — the client needs it to build and to run.

## How a command travels

1. The client builds a command with its own request builder
   (`packages/client/src/requests.ts`).
2. The client sends it with its transport
   (`packages/client/src/transport.ts`): the protocol version, the
   idempotency key and the session token. There is **no room** for a
   claimed outcome.
3. The server validates the envelope and the arguments against the
   command table, charges the **server-computed** cost, and applies the
   command through the applier.
4. The applier asks the rules engine, and the rules engine answers.
5. The server stores the world and answers.

The legacy path is the same, with the original `command.php` dialect:
the shim frames the request, verifies the HMAC against **both** keys,
and hands the commands to the same applier.

## The rules engine

It is **pure and seeded**. The generator is a xoshiro128** whose every
operation is a 32-bit integer operation, and the arithmetic is IEEE
754 double, so the same seed and the same inputs give the same answer
on any machine. That is checked in three ways:

- the generator's **reference vectors** are pinned
  (`packages/rules/src/determinism.test.ts`);
- the rules package is **scanned** for the sources of nondeterminism
  (`packages/rules/src/portability.test.ts`);
- the **golden master** compares the engine's answers with the
  original's.

The scan found two real defects when it was written — the darts
schedule was worked in the server's local time, and the shared core
imported `node:assert` — and both are fixed.

## Writing a rule

1. Put the rule in `packages/rules`, as a **pure function**. No clock, no
   randomness, no I/O.
2. Take the seed as an argument, or as a parameter.
3. Add a test that pins the answer for a known input.
4. If it changes the game, add it to the **golden corpus** and check the
   master still agrees.
5. If it is a command's semantics, wire it into the applier — and
   remember that the applier's answers are what the server believes.

## The tests

- The **unit tests** are in the package they test, and they are
  `node --test` — no framework, no runner, no configuration.
- The **integration tests** need a database, and they use PGlite, which
  is PostgreSQL in WebAssembly, so there is nothing to install.
- The **end-to-end test** starts the real server and loads the real
  client in a real browser. It is the only test that proves the whole
  thing works, and it is the slowest.
- The **cheat battery** is the server's own check that it does not
  trust the client. It is mutation-tested, so a passing battery is
  evidence.

The coverage floor is **85 % of the lines**, and it fails the build
below that.

## Working on the roadmap

The roadmap (`../docs/ROADMAP.md`) is the plan, and it is checked:
`node scripts/check-roadmap.mjs` fails if a group has lost an item, so
an item cannot go missing quietly. **Adding** an item is easy; losing
one is not.

When a decision is made, it goes in `docs/adr/` — the context, the
decision, the alternatives and the consequences. The index is
regenerated by `node scripts/check-adrs.mjs --index`.

## The rules of the repository

- The vendored upstream is **never edited**. It is GPL v3, it is a
  reference and a test oracle, and `verify-upstream.mjs` checks it on
  every build.
- The client's art, sounds and fonts are **Zynga's** and are not
  shipped. `check-licensing.mjs` and `check-no-flash.mjs` enforce it.
- The client is a **specification**. Where the upstream's Python and
  the client's ActionScript disagree, the client wins, and the
  disagreement is recorded.
- The roadmap's edits are **line-safe**. Use the edit tool, not a
  line-based replacement.
