# Authoritative Quest Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every remaining quest completable through an authoritative client-server workflow while preserving the 94-command catalogue and the two-argument `set_quest_var` contract.

**Architecture:** Build-time extraction supplies server-owned quest event data (trucks, eligible enemies, civilians). Native POST operations initialise and advance a JSON-safe `activeQuest` state containing an engagement ledger and counters. The client reports kills through a two-argument `set_quest_var` builder; the applier accepts a kill only when the ledger says the element is dead. `end_quest` remains the sole reward path and never starts a quest.

**Tech Stack:** TypeScript, Node's built-in test runner, pnpm workspaces, PGlite.

**Spec:** `docs/superpowers/specs/2026-11-20-authoritative-quest-workflow-design.md`

## Global Constraints

- 94-command catalogue unchanged; `set_quest_var` has exactly two arguments (key, JSON value). No undocumented third argument.
- `end_quest` resolves completion and rewards only — never initialises quest state.
- Roster membership is not proof of a kill: validate against a server-owned engagement ledger.
- Counters and event sources come from server-owned/built-time-extracted data, never from client declarations.
- Reject forged, duplicate, off-roster, wrong-quest and invalid-state events; unchanged wallet/save on refusal.
- Rewards via `finishQuest`/`awardQuest`, once only, replay-protected; chapter state untouched.
- No runtime dependency on `upstream/`; rules engine stays pure. No new runtime dependency.
- Roadmap updated only after every acceptance criterion is verified.

## Review Focus

- A client cannot start a quest by calling `end_quest` or by sending a `killed` ref with no active quest.
- A client cannot kill an element that the ledger does not mark engaged/dead.
- A client cannot seed or zero `bastardsAlive`/`workersInVillages`/`trucksArrived` by declaration.
- Replayed `quest/start`, `quest/action` or `set_quest_var` events cannot double-apply.
- Chapter `currentQuestVars.killed` writes remain compatible; quest progress uses `activeQuest`, not that array.

---

### Task 1: Build-time quest event data

**Files:** `packages/content/src/build.ts`, `schema.ts`, `build.test.ts`

- [ ] Step 1: failing tests for extracted event data for Q03 (truck refs/count), Q10 and Q14 (eligible enemy refs/counts by group_type), Q11 (civilian refs/count) — all `item:<isoId>` refs, deterministic, counts from the vendored quest maps.
- [ ] Step 2: run content tests, confirm RED.
- [ ] Step 3: extract into a new optional `questEvents` bundle field keyed by quest id. Do not read upstream at runtime.
- [ ] Step 4: run content tests + two builds, confirm GREEN and stable build id.
- [ ] Step 5: commit `feat(content): extract quest event data at build time`.

### Task 2: Server-owned quest start and authoritative events

**Files:** `packages/server/src/apply.ts`, `apps/server/src/app.ts`, `apps/server/src/main.ts`, `apps/server/src/shim.ts`, tests

- [ ] Step 1: failing tests: `POST /api/quest/start` creates persistent activeQuest with engagement ledger and seeded counters; refuses when a quest is already active; `POST /api/quest/action` advances truck/eligible-enemy/civilian events with validation; `set_quest_var('killed',[ref])` is accepted only when the ledger marks the element dead; a third argument is ignored/refused; `end_quest` without an active quest is refused; forged/duplicate/off-roster/wrong-quest/invalid-state events refused with unchanged save; replay of start/action pays nothing.
- [ ] Step 2: run focused tests, confirm RED.
- [ ] Step 3: implement native endpoints with `store.transact`, auth via `identify`, idempotency memo, typed 4xx; implement pure server helpers in apply.ts for start/action; remove the third-argument read and the implicit-start fallback; generalise `applyQuestEvents` to validate against the ledger.
- [ ] Step 4: run server + shim tests, confirm GREEN.
- [ ] Step 5: run `pnpm test && pnpm typecheck && pnpm lint && node scripts/verify-command-catalogue.mjs`.
- [ ] Step 6: commit `feat(f): add authoritative quest start and event operations`.

### Task 3: Client workflow and quest e2e

**Files:** `packages/client/src/requests.ts`, `transport.ts`, `session.ts`, `featurestate.ts`, `apps/client/src/main.ts`, `scripts/e2e-test.mjs`, tests

- [ ] Step 1: failing tests: two-arg `reportQuestKill(ref)` builder; native `startQuest`/`questAction` helpers using the auth header; `activeQuest` surfaced in the client state; e2e steps that start a quest, report events, call `end_quest` and verify the reward after restart.
- [ ] Step 2: run focused tests, confirm RED.
- [ ] Step 3: implement the builders/helpers and the `__swl` e2e hooks; extend the e2e script.
- [ ] Step 4: run focused tests + the real e2e script, confirm GREEN.
- [ ] Step 5: run the whole gate.
- [ ] Step 6: commit `feat(g): drive the authoritative quest workflow from the client`.

### Task 4: Final gate and roadmap

**Files:** `docs/ROADMAP.md`

- [ ] Step 1: run protocol, rules, server, client, integration, golden-master, cheat-battery, coverage and e2e checks; list every result.
- [ ] Step 2: only if all pass, close G4 and the two chapter items with evidence; record the honest residual boundary (no positional simulator) in *Unimplemented layers*; add an amendment-log entry.
- [ ] Step 3: commit `docs(roadmap): close G4 with verified quest workflow`.
- [ ] Step 4: continue with agent-implementable items from the remaining 27, keeping external blockers and non-goals separate.
