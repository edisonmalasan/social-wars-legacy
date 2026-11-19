# Authoritative Quest Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the pure quest state machine into the authoritative server so chapters and assault quests grant content-derived rewards once, from server-owned state, closing the three open quest roadmap items.

**Architecture:** Add applier cases for the four existing quest commands; hold a JSON-safe `QuestState` in `privateState.activeQuest`; drive it with validated `set_quest_var` writes; resolve `end_quest` with `isQuestVictory`/`finishQuest`/`awardQuest`. No new commands; the 94-command catalogue stays intact.

**Tech Stack:** TypeScript, Node's built-in test runner, pnpm workspaces.

**Spec:** `docs/superpowers/specs/2026-11-20-quest-application-design.md` and `docs/ROADMAP.md` Group G4.

## Global Constraints

- The server is authoritative; the client sends identifiers only — never a win flag, a reward delta, a difficulty-derived rank or a price.
- The rules engine is pure: no `Date.now()`, unseeded randomness or I/O. Use `deps.now()` and the rules helpers.
- No runtime dependency; Node's built-in test runner.
- Do not add or remove any command in `packages/protocol/src/commands.ts` or `COMMAND_NAMES`; `verify-command-catalogue.mjs` must stay 94/94/94.
- A refused command leaves the wallet and the save untouched, in both the native endpoint and the shim.
- Quest rewards come from content (`REWARDS_CHAPTERS`) or from `finishQuest`/`awardQuest`, never from a client delta.
- `pnpm test`, `pnpm typecheck`, `pnpm lint`, `node scripts/check-roadmap.mjs`, `node scripts/check-report-sync.mjs` and `node scripts/verify-command-catalogue.mjs` must pass.

## Review Focus

- A client that sends `ended: true` without a spawned chapter, or a `win` flag with no server events, must not receive a reward.
- A replayed `collect_mission` or `end_quest` must pay nothing.
- A client-supplied `res` delta or legacy reward blob must change nothing.
- A malformed `killed` ref not in the server roster must be refused, not applied.
- The legacy shim and the native endpoint must take the same applier path.

---

### Task 1: Chapter commands — set_quest_var, collect_mission, admin_set_quest_rank

**Files:**
- Modify: `packages/server/src/apply.ts`
- Test: `packages/server/src/apply.test.ts`

**Interfaces:**
- Consumes: `applyQuestVar`, `readChapterStatus`, `QUEST_VAR_KEYS` from `@swl/rules`; `ownMap`, `questProgress`, `ApplierDeps`, `CommandOutcome`, `ShimWorld` from `apply.ts`.
- Produces: three applier cases and a `chapterRewards` dependency; new private-state award log key.

- [ ] **Step 1: Write failing tests** in `apply.test.ts` for: unknown key refused; malformed value shapes refused; `idSimpleChapter` ignored; `id` mirrored to `map.idCurrentMission`; `ended: true` without `spawned` refused; `collect_mission` refuses when not ended, grants exactly `REWARDS_CHAPTERS[completedId]` from content, advances and clears map state, wraps `>99 → 1`, and pays nothing on replay; `admin_set_quest_rank` never overwrites server ranks.
- [ ] **Step 2:** Run `node --test packages/server/src/apply.test.ts` and confirm RED.
- [ ] **Step 3:** Implement the three cases as pure helpers beside the existing ones in `apply.ts`. Add `chapterRewards` to `ApplierDeps`. Add a private-state award log. Keep `system_reset_quest` refused.
- [ ] **Step 4:** Run the focused test and `node --test packages/server/src/shim.test.ts` and confirm GREEN.
- [ ] **Step 5:** Commit `feat(f): apply chapter quest commands server-side`.

### Task 2: Assault quests — active QuestState and end_quest

**Files:**
- Modify: `packages/server/src/apply.ts`
- Test: `packages/server/src/apply.test.ts`

**Interfaces:**
- Consumes: `prepareQuest`, `startQuest`, `loadQuestMap`, `killQuestElement`, `isQuestVictory`, `finishQuest`, `awardQuest`, `getQuestSpec`, `emptyQuestProgress` from `@swl/rules`; the `killed` writes from Task 1.
- Produces: `activeQuest` private-state key, roster derivation, `end_quest` case accepting native and legacy shapes.

- [ ] **Step 1: Write failing tests** for: a `killed` write initialises the server quest state from the quest spec roster; a ref not in the roster is refused; `end_quest` with a claimed `win: true` and no server events is refused; after the scripted kills `end_quest` grants the content-derived reward and sets the server rank; a replay pays nothing; a legacy `[JSON blob]` argument is accepted for the quest id but its `win`/`loot` fields are ignored.
- [ ] **Step 2:** Run the focused test and confirm RED.
- [ ] **Step 3:** Implement helpers in `apply.ts`: `questRoster(spec, deps.items)`, `ensureActiveQuest`, `applyQuestKills`, `endQuestCommand`. Serialize `QuestState` as JSON-safe data in `privateState.activeQuest`. Use `deps.now()` and a content-derived `expRequired` default.
- [ ] **Step 4:** Run focused tests plus `node --test packages/server/src/shim.test.ts` and confirm GREEN.
- [ ] **Step 5:** Commit `feat(f): resolve quests from server-owned state`.

### Task 3: Wire dependencies, migration and roadmap disposition

**Files:**
- Modify: `apps/server/src/main.ts`, `packages/server/src/migrate.ts`, `docs/ROADMAP.md`, `docs/superpowers/plans/2026-11-20-quest-application.md`
- Test: `packages/server/src/migrate.test.ts`

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces: content globals wired into the applier; server-added state keys migrated; the three quest roadmap items closed with evidence.

- [ ] **Step 1:** In `apps/server/src/main.ts`, pass `chapterRewards` from `globalsOf(bundle)['REWARDS_CHAPTERS']` and any quest constants into `createApplier`. Add the new private-state keys (`chapterAwards`, `activeQuest`) to the migration's v0→1 block in `migrate.ts` and update its test.
- [ ] **Step 2:** Verify each of the three roadmap items against the explorer's layer table; tick only those with rules model + server applier + client request/model, naming the tests and marking full authoritative combat as the remaining dependency in *Unimplemented layers*.
- [ ] **Step 3:** Run the whole gate: `pnpm test && pnpm typecheck && pnpm lint && node scripts/check-roadmap.mjs && node scripts/check-report-sync.mjs && node scripts/verify-command-catalogue.mjs`.
- [ ] **Step 4:** Commit `docs(roadmap): close quest parity with evidence` and finish the branch.
