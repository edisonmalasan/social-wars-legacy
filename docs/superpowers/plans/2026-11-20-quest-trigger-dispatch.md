# Quest Trigger Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve five more assault quests by dispatching validated kill refs through the rules' trigger-specific mutators, without adding commands or reintroducing the empty-roster exploit.

**Architecture:** `QuestElementSpec.trigger` already says which mutator an element's death should drive (`onKill` → `killQuestElement`, `onNearDeath` → `nearDeathQuestElement`, `onKillDefenders` → `defendersClearedQuestElement`). The applier currently ignores it and only writes `script.destroyed`. Add one dispatch helper used by both event entry points, and relax the "work was done" guard to accept any validated event channel.

**Tech Stack:** TypeScript, Node's built-in test runner, pnpm workspaces.

**Spec:** `docs/superpowers/specs/2026-11-20-quest-application-design.md` and the explorer's findings (captured in the plan's Global Constraints).

## Global Constraints

- No new protocol commands: `COMMAND_NAMES` and the report catalogue stay at 94/94/94.
- The server owns the win and reward; a client-supplied win/loot/rank is never trusted.
- Every ref must be validated against the server roster before any mutation; off-roster refs are refused, silently filtered only in the documented legacy-replay fallback.
- The zero-event guard must remain: a quest with no validated events cannot pay, even when its win predicate is vacuously true (`countersZero` on an empty roster). A recorded loss still cannot pay.
- No runtime dependency; Node's built-in test runner. pnpm test, typecheck, lint, check-roadmap, check-report-sync and verify-command-catalogue must pass.

## Review Focus

- A `nearDeath` ref for a `canDie:false` element must not be accepted as a destruction (no `script.destroyed` entry).
- A re-sent ref must not double-apply an event.
- A forged `win` with no events, or a loss with events, must still be refused.
- The legacy `end_quest` replay must use the same trigger dispatch as the live `set_quest_var` path.
- The roadmap must not claim the quest item is closed — the remaining win-condition kinds need rosters/counters the repository cannot supply at runtime.

---

### Task 1: Trigger dispatch in the applier

**Files:**
- Modify: `packages/server/src/apply.ts`
- Test: `packages/server/src/apply.test.ts`

**Interfaces:**
- Consumes: `killQuestElement`, `nearDeathQuestElement`, `defendersClearedQuestElement`, `QuestElementSpec.trigger` from `@swl/rules`; `questRoster`, `applyQuestKills`, `ensureActiveQuest`, `endQuestCommand`, `setQuestVarCommand` from `apply.ts`.
- Produces: a `applyQuestEvents(state, refs, spec, deps)` helper that dispatches by trigger; both event entry points using it.

- [ ] **Step 1: Write failing tests** in `apply.test.ts`:
  - Q01 Bazooka (`nearDeathAll` boss1 + jeep): two `killed` refs with `onNearDeath` triggers make `isQuestVictory` true and pay on `end_quest`.
  - Q06 Airstrike (`defendersClearedAll radioStation` + `destroyAll enemyCommandCenter`): the radio ref drives `defendersCleared` and the command-center ref drives `destroyed`.
  - A ref dispatched to `nearDeath` does NOT appear in `script.destroyed` (canDie:false fidelity).
  - A re-sent ref is idempotent (no double reward).
  - The legacy `end_quest` replay resolves Q01 via the same dispatch.
  - A forged win with no events, a zero-event hardcore quest, and a recorded loss are still refused (existing tests must remain green).
- [ ] **Step 2:** Run `node --test packages/server/src/apply.test.ts` and confirm RED.
- [ ] **Step 3:** Implement the dispatch helper beside `applyQuestKills`, reusing the existing roster validation and dedupe. Replace the call in the `killed` branch of `setQuestVarCommand` and in the `end_quest` legacy fallback. Relax the guard at the end of `endQuestCommand` from `destroyed.length > 0` to "any validated event exists", keeping the `result === 'loss'` refusal.
- [ ] **Step 4:** Run focused tests plus `node --test packages/server/src/shim.test.ts` and confirm GREEN.
- [ ] **Step 5:** Run `pnpm test && pnpm typecheck && pnpm lint && node scripts/verify-command-catalogue.mjs` before committing.
- [ ] **Step 6:** Commit `feat(f): dispatch quest events by element trigger`.

### Task 2: Honest roadmap disposition

**Files:**
- Modify: `docs/ROADMAP.md`
- Modify: `docs/superpowers/plans/2026-11-20-quest-trigger-dispatch.md`

**Interfaces:**
- Consumes: Task 1.
- Produces: precise counts of resolvable vs unresolvable quests and a stable record of the remaining dependency.

- [ ] **Step 1:** Update the *Unimplemented layers* section with the current state: destroyAll, nearDeathAll and defendersClearedAll quests with scripted elements resolve; countersAtLeast/countersZero quests (weekly, hardcore, convoy, special ops, save villages, spy2) remain unresolvable without roster/counter data that must be extracted at build time from `villages/quest/<id>.json` and instrumented in the client. Do not tick the G4 quest item.
- [ ] **Step 2:** Add an amendment-log entry with the evidence.
- [ ] **Step 3:** Run the whole gate and commit `docs(roadmap): record trigger dispatch progress`.
