# AGENTS.md

## Project

- **Name:** Social Wars Legacy
- **Purpose:** Re-implement the Flash game *Social Wars* (Zynga, client v1.5.4) as a
  **cross-platform client-server application** — web, desktop and mobile — with no Flash
  dependency, for players and for preservation. Primary users: players who want the game to
  keep working, preservation archivists, and anyone studying the original client's rules.
- **Current state:** **The investigation is complete and the build is under way.** The
  repository contains the full reverse-engineering report set (`re/`), the project router
  (`docs/`) and the production roadmap (`docs/ROADMAP.md`). The upstream project under
  analysis is vendored at `upstream/socialwarriors/` with a SHA-256 manifest. The pnpm
  workspace exists with `packages/protocol`, `packages/content` and `packages/rules`; the
  content pipeline builds a validated, hashed bundle from the upstream config. The
  **server** (Groups F), the **web client** (Group G) and the **desktop shell** (Group H)
  exist; the mobile shell (Group G5) does not yet.

## Source of Truth

**Read only the documentation relevant to the task. Do not assume—verify.**

| Source                                  | Read when                                                    |
| --------------------------------------- | ------------------------------------------------------------ |
| `docs/CONTEXT.md`                       | Locating context, constraints, and relevant documentation    |
| `docs/ROADMAP.md`                       | Checking planned features, priorities, or verified progress  |
| `re/README.md`                          | Navigating the reverse-engineering findings                  |
| `re/docs/`                              | The detailed analysis of the original client, server and data |
| `re/evidence/`                          | Raw captured traffic, digests and screenshots                |
| `docs/ARCHITECTURE.md` _(if it exists)_ | Making changes to established boundaries or data flows       |
| Source code and tests                   | Determining actual current behavior and verifying a change   |
| `graphify-out/` _(if it exists)_        | Exploring code relationships; verify findings against source |

- Requirements and explicitly approved decisions define **intended behavior**; source code and passing tests provide evidence of **current behavior**.
- If documentation and code conflict, **report the discrepancy** and determine whether the code or documentation needs correction. Never silently rewrite a requirement to justify current code.
- Prefer one authoritative location per fact; link to it rather than copying it into multiple files.

## Tech Stack

_Fill from verified project files. Remove unused rows._

**Decision status matters here: the stack below is *approved and locked* (see the "Locked
Decisions" section of `docs/ROADMAP.md`) but is *not yet implemented*. Only rows marked
"Present" exist in the repository today.**

| Layer                | Technology / version                        | Status  | Evidence                        |
| -------------------- | ------------------------------------------- | ------- | ------------------------------- |
| Workspace            | pnpm 12.6 workspaces, TypeScript 5.9        | **Present** | `pnpm-workspace.yaml`, `packages/*`, `apps/*` |
| Protocol types       | TypeScript, in `@swl/protocol`              | **Present** | `packages/protocol/src/` — the wire types, the `command.php` framing, the 94-command table |
| Content pipeline     | TypeScript + a dependency-free JSON Patch applier, in `@swl/content` | **Present** | `packages/content/src/` |
| Rules engine core    | TypeScript, in `@swl/rules`                 | **Present** | `packages/rules/src/` — the seeded PRNG, the 12-stage damage pipeline, the battle simulation, the quests, the goals, the loot |
| Server core          | TypeScript, in `@swl/server`                | **Present** | `packages/server/src/` — the sessions, the compatibility shim, the command applier, the save migration |
| Server application   | TypeScript on `node:http`, in `apps/server` | **Present** | `apps/server/src/` — the routing, the limits, the native and legacy endpoints |
| Client core          | TypeScript, in `@swl/client`                | **Present** | `packages/client/src/` — the isometric projection, the depth sort, the atlas index |
| Game client (web)    | TypeScript + PixiJS v8 (WebGL2) + React DOM | **Present** | `apps/client/src/` — the renderer, the scene, the React interface |
| Desktop shell        | Tauri v2 (Rust) over the same web client     | **Present** | `apps/desktop/src-tauri/` — the window, the remote server's certificate check |
| Mobile shell         | Capacitor over the same web client          | Planned | `docs/ROADMAP.md` Group G5       |
| Server + rules engine| TypeScript on Node.js 26                     | **Present** | `apps/server` and `packages/rules` |
| Database             | PostgreSQL (server); PGlite for the development server and the tests | **Present** | `packages/server/src/pgstore.ts` |
| Upstream reference   | Python 3.9 + Flask 2.2.5                    | Present (vendored, read-only) | `upstream/socialwarriors/` |
| Asset tooling        | JPEXS FFDec 26.3.0 (Java 21), Git LFS 3.7.1 | Present | `re/docs/05-assets-and-content-pipeline.md` |
| Reverse engineering  | REA MCP (Ghidra 12.1.4 headless)             | Present | `re/docs/07-REA-EVIDENCE.md`     |
| Tests                | Node's built-in test runner (`node --test`) | **Present** | `pnpm test` — 1268 tests, no test-framework dependency |

## Build, Test, and Development Commands

_Use commands that really exist in this repository. Never invent a script._

**The workspace, the content pipeline, the server, the web client and the desktop shell
exist (roadmap Groups C, F, G and H). The mobile shell does not — it lands with
Group G5.**

| Purpose                     | Command                            | Status | Evidence / notes |
| --------------------------- | ---------------------------------- | ------ | ---------------- |
| Install dependencies        | `pnpm install`                     | Working | Group C |
| Type-check everything       | `pnpm typecheck`                   | Working | Group C |
| Run the tests               | `pnpm test`                        | Working | Group C — Node's built-in runner, no test-framework dependency |
| Build the content bundle    | `pnpm build:content`               | Working | Group C |
| Validate the content bundle | `pnpm check:content`               | Working | Group C — same checks, no write |
| Build everything            | `pnpm build`                       | Working | Group C — the content build; the client's is `pnpm --filter @swl/app-client build` |
| Verify the vendored upstream | `node scripts/verify-upstream.mjs` | Working | Group A — fails on any drift |
| Re-vendor the upstream releases | `node scripts/vendor-releases.mjs` | Working | Group A — needs the upstream checkout |
| Fetch the vendored assets   | `node scripts/pull-assets.mjs`     | Working | Group A — targeted LFS pull |
| Decompile the client        | `node scripts/decompile-client.mjs` | Working | Group B |
| Convert the SWF art to frames | `node scripts/convert-assets.mjs` | Working | Group D — resumable |
| Pack the frames into atlases | `node scripts/pack-atlases.mjs`   | Working | Group D — trims and packs |
| Catalogue the images and sounds | `node scripts/build-asset-manifest.mjs` | Working | Group D |
| Extract and measure the client fonts | `node scripts/extract-fonts.mjs` | Working | Group D |
| Run the end-to-end session        | `node scripts/e2e-test.mjs` | Working | Group I — the real server, client and browser |
| Smoke-test the web client        | `node scripts/smoke-test-client.mjs` | Working | Group G — loads it in Chrome and Edge |
| Build the client's manifest        | `node scripts/build-client-manifest.mjs` | Working | Group I — 118 MB becomes 3.9 MB |
| Check the test coverage          | `node scripts/check-coverage.mjs` | Working | Group I — fails below the floors |
| Check the golden-master corpus | `node scripts/golden-master.mjs` | Working | Group E4 — fails on any difference |
| Prepare the desktop shell's inputs | `node scripts/prepare-desktop.mjs` | Working | Group H — the icons and the placeholder |
| Check the backups are current    | `node scripts/check-backups.mjs --out <dir>` | Working | Group I — fails when the newest is too old |
| Check the report set               | `node scripts/check-report-sync.mjs` | Working | Group I — the report against the code |
| Lint the project's own rules    | `node scripts/lint-project.mjs` | Working | Group I — the browser must not need node |
| Check the build is reproducible    | `node scripts/check-reproducible-build.mjs` | Working | Group I — builds the client twice |
| Check the release checklist        | `node scripts/check-release.mjs` | Working | Group I — the checklist covers the gate |
| Check the corrections policy      | `node scripts/check-corrections.mjs` | Working | Group I — the notices point at it |
| Check the security review          | `node scripts/check-security-review.mjs` | Working | Group I — the claims are covered |
| Check the decision records         | `node scripts/check-adrs.mjs` | Working | Group I — `--index` rewrites it |
| Build the licence report          | `node scripts/build-licence-report.mjs` | Working | Group I — `--check` fails on an unclassified dependency |
| Check the licensing position        | `node scripts/check-licensing.mjs` | Working | Group I — the claims in `docs/LICENSING.md` |
| Check nothing that ships needs Flash | `node scripts/check-no-flash.mjs` | Working | Group H — proves it rather than asserting it |
| Run the cheat battery             | `node scripts/run-cheat-battery.mjs` | Working | Group I — the release gate |
| Check the roadmap's item counts    | `node scripts/check-roadmap.mjs`  | Working | Group I — fails if a group lost an item |
| Deploy the server               | `node scripts/deploy.mjs --data <dir>` | Working | Group I — `--rollback` undoes it |
| Run the schema migrations        | `node scripts/migrate.mjs --data <dir>` | Working | Group F — `--status` and `--rollback` too |
| Run the load test                | `node scripts/load-test.mjs` | Working | Group I — measured against the performance budgets |
| Soak the server | `node --expose-gc scripts/soak-server.mjs` | Working | Group F4 — no memory growth, no state drift |
| Check the command catalogue against the client | `node scripts/verify-command-catalogue.mjs` | Working | Group F2 — fails on any difference |
| Refresh the code graph | `graphify extract . --code-only` | Working | Derived knowledge; run after a structural change |
| Fetch and measure the substitute fonts | `node scripts/fetch-fonts.mjs` | Working | Group D — downloads them and measures the scale |
| Run the client (dev)        | `pnpm --filter @swl/app-client dev`    | Working | Group G |
| Build the client            | `pnpm --filter @swl/app-client build`  | Working | Group G — fetches the fonts, then builds |
| Run the server (dev)        | `pnpm --filter @swl/app-server dev`    | Working | Group F — `apps/server` |
| Golden-master rules diff    | `pnpm --filter rules test:golden`  | Planned | Group E4 |

Run from the repository root unless a command explicitly requires another directory.

The analysis scripts under `scripts/` are plain Node ES modules and run directly with
`node`; they need no build step. The TypeScript under `packages/` is run by Node 26's
native type stripping, so there is no compile step either — `tsc` is only used for
type-checking.

## Architecture Non-Negotiables

_These are **verified** constraints from the investigation and the approved roadmap. The
full rationale is in `docs/ROADMAP.md` ("Locked Decisions & Non-Negotiables")._

1. **The upstream project is vendored, never edited.** It lives under `upstream/` at a
   pinned commit with a SHA-256 manifest, and is GPL v3. It is a reference and a test
   fixture — never a runtime dependency of the shipped product.
2. **The client is the specification.** The decompiled ActionScript 3 (1 387 classes in
   `Basesec_1.5.4.swf`) describes the real game. Where the Python upstream server and the
   AS3 disagree, the AS3 wins. Port behaviour from the client, not from `command.py`.
3. **The server is authoritative.** Combat outcomes, resource costs, goal completion and
   reward grants are computed server-side from a server-issued seed. The client requests
   and renders; it never decides.
4. **The 8-slot resource vector is `[energy, xp, gold, wood, oil, steel, cash, mana]`.**
   Verified live against a real client session. Preserve this order in any wire format.
5. **The `command.php` wire format is `<64 hex chars>;<JSON>`, where the hex is
   `HMAC-SHA256(<server key>, payload)`.** Verified live. **The key rotated once**, at
   client build 1.4.28: `3m0d3pwiupoetn7ysa02` for builds 1.4.5–1.4.27 and
   `4vVSD8dftv6hdfb1Hnk9` for 1.4.28–1.5.4. The live-verified key is the **rotated** one.
   The compatibility shim must reproduce the framing exactly **and accept both keys**,
   because unmodified original clients span both eras. See
   [`re/docs/10-client-version-history.md`](re/docs/10-client-version-history.md).
6. **`flash_debug` must not exist** in the new server. It overwrites the whole wallet from
   client arguments.
7. **No authentication may be inherited from upstream.** `USERID` came from the request
   body; the new server uses real credentials and revocable session tokens.
8. **The rules engine is deterministic and pure.** No `Date.now()`, no unseeded randomness,
   no I/O inside the simulation. Same seed + same inputs ⇒ same outcome on any machine.
9. **Content is versioned and reproducible.** `config/main.json` plus the 5 JSON-Patch
   deltas (778 → 900 items, 104 → 105 globals) produce a single hashed content bundle;
   the build fails on an unknown key or a dangling id.
10. **No Flash anywhere in the shipped product.** No SWF runtime, no Adobe Flash Player
    component, no Flash browser dependency. The original client may be used *only* as a
    test oracle.
11. **The asset licence position must be settled before any public release.** The upstream
    code is GPL v3; the sprites, audio and config are Zynga's.

## Working Method (Lightweight ICM)

1. **Orient:** Read `docs/CONTEXT.md`, then only the relevant roadmap section, existing source files, and needed references.
2. **Plan when warranted:** For substantial changes, summarize approach, affected files, risks, and verification criteria before coding. Small, clear fixes do not need separate plan documents.
3. **Implement within scope:** Follow existing conventions and avoid unrelated changes.
4. **Verify:** Run applicable checks; report passed, failed, skipped, and unavailable checks accurately.
5. **Preserve:** Update `docs/ROADMAP.md` only for verified outcomes, and update other authoritative docs only when facts change.

Do not create extra ICM stage folders or permanent plan files unless the task benefits from them.

## Graphify

- Graphify is **derived project knowledge**, not the source of truth for code behavior.
- When available and relevant, query the existing graph to find related symbols and dependencies; inspect source files before acting on results.
- After meaningful structural changes, refresh the graph using the **installed** Graphify skill or CLI workflow. Do not presume Graphify is installed or that a graph exists.
- If exporting to Obsidian, use only this project's generated area: `C:\Users\Edison\Documents\Obsidian/10 - Projects/Social Wars Legacy/_Graphify/`.
- Never export into the vault root or overwrite curated PARA notes. Refreshing the graph is **not** the same as saving session decisions.

## Obsidian / Cross-Project Knowledge

- **Central vault:** `C:\Users\Edison\Documents\Obsidian`
- **Project notes:** `10 - Projects/Social Wars Legacy/`, if present.
- Read only relevant notes, when the vault is configured and accessible; repository docs remain authoritative for project-specific requirements.
- Propose meaningful updates after substantial work: project progress/decisions under `10 - Projects`, reusable lessons under `30 - Resources`, unverified ideas under `00 - Inbox`.
- **Ask before editing curated vault notes.** Avoid duplicates, stale claims, secrets, and copying entire chat transcripts.
- If the vault is inaccessible, continue using local project context and mention the limitation.

## Git Workflow

1. **Never commit directly to `main`.** Use task branches prefixed with `feat/`, `fix/`, `chore/`, `docs/`, or `refactor/`.
2. Before modifying files, check `git status`, switch to `main`, pull the latest `origin/main`, create a task branch, and push it with upstream tracking.
3. Commit at logical checkpoints and push changes to the remote.
4. Use the `git` subagent when available; otherwise, use permitted Git tools.
5. After implementation, run relevant tests, resolve issues, and **merge verified work into `main` through a pull request**. `main` is **protected**: the CI's four checks must pass, the conversations must be resolved, and a direct push is refused — so the work arrives as a PR, the CI runs on it, and it is merged once it is green (`gh pr merge --merge`).
6. Never discard existing changes, force-push, or commit temporary agent-generated plans unless explicitly authorized.
7. **Do not consider a task complete until it is verified, merged, and reflected in `docs/ROADMAP.md`.**

### Branch Lifecycle

```bash
git status
git switch main
git pull --ff-only origin main
git switch -c <branch-name>
git push -u origin <branch-name>
gh pr create --base main --head <branch-name> --title "<title>" --body "<what and why>"
gh pr checks          # the four CI checks
gh pr merge --merge   # once they are green
git switch main
git pull --ff-only origin main
```

If the working tree is dirty or Git operations are blocked, resolve safely without overwriting existing work.

---

## Autonomous Orchestration Mode

_Activate only when the user explicitly requests autonomous roadmap execution._

1. **Orchestrator:** Read `docs/CONTEXT.md` and `docs/ROADMAP.md`, select the next eligible task, manage Git operations, and verify completion.
2. **Subagent:** Spawn **one implementation-and-testing subagent** per task when supported. Otherwise, perform the work directly.
3. **Execution:** Create branch → Implement → Test → Commit → Push → Merge → Update roadmap.
4. **Continuity:** Automatically proceed to the next eligible roadmap task. **Do not stop after one feature or merge.**
5. **Blockers:** Attempt safe recovery. Pause only for unresolved errors, missing requirements, permissions, required approvals, or unsafe operations. Continue independent tasks when possible.
6. **Completion:** Stop when all authorized tasks are finished, remaining tasks are deferred or blocked, or the user stops execution.
7. **Knowledge:** Update relevant documentation, preserve reusable lessons in Obsidian, and refresh Graphify after significant changes.

### Autonomous Mode Execution Order

The roadmap's **critical path** is `A → B → C → D → E → F → G → H → I`, with `B1–B8`
mutually independent and `D` ∥ `E`, and `G1` ∥ `G3`. Prefer work that unblocks the most
downstream tasks, and record a checkmark in `docs/ROADMAP.md` only for outcomes that are
**verified** by an executed check.

## Template Initialization (only when requested)

When asked to initialize these templates for a new repository:

1. Inspect the repository's `README`, manifests, folder structure, configuration, tests, and existing documentation.
2. Fill this file plus `docs/CONTEXT.md` and `docs/ROADMAP.md` using **verified** information. Keep the roadmap grouped by useful milestones, not implementation steps.
3. Preserve existing user-written requirements. Use `Not verified` or ask a targeted question for genuinely unknown details.
4. Remove inapplicable template rows and placeholders. Do not claim features are complete without evidence.
5. Do **not** automatically install Graphify, create branches/commits, modify the Obsidian vault, or create optional docs without permission.
6. Summarize the populated files, sources consulted, and remaining uncertainties for review.
