# G5.2 Gameplay Systems Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three G5.1 P0 gameplay gaps — authoritative reward rows, collection-period selection, and army management with server-enforced team selection — then complete achievable P1 polish, without breaking the verified G5.1 loop.

**Architecture:** Extend the existing native surfaces, never the 94-command catalogue. The applier's outcome gains one optional typed `result`, forwarded by `/api/command`; `activate` gains a real server applier; `/api/quest/start` gains an optional validated `team`. React reuses the one Dialog and Feedback channel. All new state is server-owned and persisted in the existing save document.

**Tech Stack:** TypeScript, Node's built-in test runner, pnpm workspaces, CDP e2e harness.

**Spec:** `docs/GOAL.md` (G5.2) and the reverse-engineering docs for periods and team quests.

## Global Constraints

- Server authoritative for rewards, production, army and quests. No client-computed amount, eligibility, timer or outcome.
- 94-command catalogue and legacy framing unchanged; `set_quest_var` stays two-arg; `end_quest` stays completion-only.
- Native API additions are backward compatible and tested; existing clients omitting new fields keep working.
- One persisted reward/team representation in the save document; no second reward authority or granting operation.
- No runtime `upstream/`, no vendored edits, no proprietary art, no new runtime dependency.
- Roadmap G5.2 recorded outside `## Group X` so the 401-item accounting is unchanged.
- All gates in `docs/GOAL.md` §10 pass before any completion claim.

## Design decisions (from repository evidence)

1. **Reward rows:** `CommandResult` and `Reward` already exist in `@swl/protocol`; `end_quest` already declares `result:'rewards'`. Add an optional `result?: CommandResult` to the server applier's `CommandOutcome` (`shim.ts`), populate it in `endQuestCommand` from the exact `awardQuest` rows (mapping short keys to `ResourceName`, applying the same `Math.round` for XP that mutates the wallet), and forward `outcome.result ?? {kind:'none'}` at the single conversion point in `app.ts`. Legacy `applyBatch` ignores the field. Persist a minimal `lastQuestReward` receipt in `privateState` for reconnect display.
2. **Collection periods:** the protocol's `activate` enum `[0,1,2,3]` conflicts with the rules' 1-based periods `[1,2,3,4]`. Align the protocol to `[1,2,3,4]` and its sample args; translate nowhere else. Implement `activateCommand` with building existence, `multiCollectable` eligibility, period range, capacity and construction checks; write only `cp` and `lastAccruedAt` from `deps.now()`; make a same-period repeat a no-op that does not restamp. Derive `collectPeriods` from content globals in `main.ts`.
3. **Team selection:** add `QUESTS_WITH_TEAMS` to `@swl/rules` for the four documented hardcore ids (`100000021`, `100000022`, `100000025`, `100000026`). Extend `/api/quest/start` with optional `team`; validate ownership from server inventory, `isUnitAllowedInQuest` eligibility, dedupe and cap; store it on `ActiveQuestState`; seed `prepareQuest({army})` so `playerUnitsAlive` is server-derived; echo it in the ledger summary. Document that per-unit combat fidelity needs the absent positional simulator.

## Review Focus

- A forged/duplicated/excessive team must be refused without writing an active quest.
- A repeated `activate` must not extend the countdown; an invalid period must be refused.
- Reward rows must equal what the wallet actually received, including rounded XP and weekly cash; failure and replay must show none.
- Legacy `/command.php` body must remain exactly `{result:'success'}` with both HMAC keys accepted.
- Dialog focus/ARIA and duplicate-request guards from G5.1 remain intact.

---

### Task 1: Authoritative reward payloads and result screens

**Files:** `packages/server/src/shim.ts`, `apply.ts`, `apps/server/src/app.ts`, `packages/content` none, `apps/client/src/ui/quests.tsx`, `packages/client/src/questview.ts`, `scripts/e2e-test.mjs`, tests.

- [ ] Step 1: failing tests — successful `end_quest` returns exact rows; failure returns none; replay pays zero and repeats rows; receipt survives a restart; legacy body unchanged.
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement the optional `result`, `endQuestCommand` mapping + `lastQuestReward` receipt, single forwarding point, result-dialog improvements (victory, defeat, reward rows, mission completion, next-mission availability respecting server rank, retry/return to base).
- [ ] Step 4: run focused tests, full gate, confirm GREEN.
- [ ] Step 5: commit `feat(g5.2): return authoritative quest rewards and result screens`.

### Task 2: Collection-period selection

**Files:** `packages/protocol/src/commands.ts` + test, `packages/server/src/apply.ts` + tests, `apps/server/src/main.ts`, `packages/client/src/requests.ts`, `featurestate.ts`/`management.ts`, `apps/client/src/ui/info.tsx`, CSS, tests.

- [ ] Step 1: failing tests for all four periods, invalid period, non-eligible building, over-capacity, duplicate no-op, server-clock readiness, persistence.
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement `activateCommand`, content-derived periods, client builder, production view model, and four period buttons with countdown in the info panel using Dialog/Feedback.
- [ ] Step 4: run focused tests, full gate, confirm GREEN.
- [ ] Step 5: commit `feat(g5.2): add authoritative collection-period selection`.

### Task 3: Army management and team selection

**Files:** `packages/rules/src/quest.ts`, `packages/server/src/apply.ts`, `apps/server/src/app.ts`, `packages/client/src/requests.ts`, `featurestate.ts`, new army model, `apps/client/src/ui/quests.tsx`, new army UI, tests.

- [ ] Step 1: failing tests for owned-unit view, team validation (forged/unavailable/excessive/disallowed/duplicate), binding to active quest, `playerUnitsAlive` sensitivity, idempotent start.
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement `QUESTS_WITH_TEAMS`, optional start `team` with server validation and persistence, client army selector in the briefing dialog, and owned-unit management display.
- [ ] Step 4: run focused tests, full gate, confirm GREEN.
- [ ] Step 5: commit `feat(g5.2): add server-enforced army and team selection`.

### Task 4: Achievable P1 polish

**Files:** UI components, `ui-screens.json`, tests.

- [ ] Step 1: identify from the audits which P1 items are genuinely supported (item-category tabs, expansion UI if the server op exists, next-mission flow, loading/disabled states, focus restore, small-viewport handling).
- [ ] Step 2: implement only supported items with tests; do not add decorative components.
- [ ] Step 3: commit `feat(g5.2): refine gameplay UI and navigation`.

### Task 5: Full verification, e2e and documentation

**Files:** `scripts/e2e-test.mjs`, `docs/ROADMAP.md`, `re/data/ui-screens.json`, task report.

- [ ] Step 1: extend the Chrome+Edge e2e with reward rows, period selection, army/team where supported, reload and restart; keep all G5.1 assertions.
- [ ] Step 2: run every gate in `docs/GOAL.md` §10 and record exact results; investigate the licensing/no-flash ordering quirk narrowly and test any checker correction without disabling checks.
- [ ] Step 3: record G5.2 outside Group headers with evidence-based screen decisions and honest gaps; do not corrupt 401-item accounting.
- [ ] Step 4: commit `docs(roadmap): record the G5.2 milestone` and prepare the PR with the §14 deliverables.
