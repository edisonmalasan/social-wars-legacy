# G5.1 Essential Gameplay UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a playable-alpha UI through which a player can register, build, train, fight a quest and claim rewards using only the interface, with every outcome decided by the existing authoritative server.

**Architecture:** React DOM stays the interface layer and PixiJS the world renderer. A shared accessible dialog primitive hosts briefing/combat/result screens. New React components consume existing pure state selectors and dispatch existing request builders through the client's single `run()` loop; no new command, no client-decided outcome. UI chrome is CSS/SVG only — the only shippable assets are the two OFL fonts.

**Tech Stack:** TypeScript, React DOM, PixiJS v8, Node's built-in test runner, CDP-based e2e harness.

**Spec:** `docs/GOAL.md` (G5.1) and `docs/adr/` (0003, 0004, 0006, 0009, 0011, 0017, 0019, 0020).

## Global Constraints

- Server authoritative: no client-computed combat result, resource cost, counter or reward. Reuse existing request builders and native quest endpoints.
- Preserve the 94-command catalogue and two-arg `set_quest_var`; no new command and no third argument.
- No runtime dependency on `upstream/`, no vendored file edited, no proprietary Zynga artwork in distributable output. UI chrome must be CSS/SVG; only Nunito and Rubik Mono One (OFL 1.1) may ship.
- Keep one web client for web/desktop/mobile; no platform-specific screen.
- No new runtime dependency; Node's built-in test runner only.
- `run()` remains the single command→world→redraw path; every UI action must produce observable feedback (success or typed server refusal).
- Update `re/data/ui-screens.json` only for screens with a real implemented model; never flip a screen merely to improve counts.
- Run all gates in `docs/GOAL.md` §7 before claiming G5.1 complete.

## Review Focus

- A player cannot register or start a quest without dev tools today.
- Selecting a unit from the build menu sends `type:'b'` (hardcoded at `main.ts:501`) — units would be bought as buildings.
- `run()` discards `NativeResponse.outcomes`, so server refusals are silent.
- Quest actions and results exist only on `window.__swl`; no React component consumes `activeQuestState`.
- No dialog primitive exists beyond the tutorial overlay; no Escape/focus/ARIA handling anywhere.
- Screen inventory has 131 `planned` screens; flipping decisions requires a real model path or `screens.test.ts` fails.

---

### Task 1: Shared UI foundation

**Files:** `apps/client/src/ui/dialog.tsx` (new), `apps/client/src/ui/feedback.tsx` (new), `apps/client/src/ui/css.ts`, `apps/client/src/ui/root.tsx`, `apps/client/src/ui/mount.tsx`, tests.

- [ ] Step 1: failing tests for a dialog model (open/close state, Escape key action, focus target) and a feedback model (server refusal vs success message) in `apps/client/src/ui/state.test.ts` or new `*.test.ts`.
- [ ] Step 2: run them, confirm RED.
- [ ] Step 3: implement one reusable `Dialog` (portal-free within `#ui`, `role="dialog"`, `aria-modal`, labelled heading, Escape+backdrop close, initial focus and focus restore, no duplicate open) and a `Feedback` toast region (`role="status"` / `role="alert"`). Add CSS with design tokens; no proprietary art.
- [ ] Step 4: confirm GREEN, run typecheck/lint.
- [ ] Step 5: commit `feat(g5): add an accessible dialog and feedback foundation`.

### Task 2: Building and recruitment through the UI

**Files:** `apps/client/src/ui/info.tsx`, `apps/client/src/ui/recruit.tsx` (new), `apps/client/src/ui/state.ts`, `apps/client/src/ui/root.tsx`, `apps/client/src/main.ts`, `packages/client/src/interaction.ts`, CSS, tests.

- [ ] Step 1: failing tests for: every selected building yields an info panel (not only producers); upgrade/finish actions are exposed with requirements; unit entries request `type:'u'`; a training-queue view model exposes queued unit and ready-to-take state from server data.
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement the panels and wiring: selection carries iso id and type; Upgrade → `upgrade`, Finish → `finishBuilding`, Train → `train`, Take → `takeTrainedUnit`; countdowns from server timestamps with a 1s tick; feedback from command outcomes.
- [ ] Step 4: confirm GREEN, run typecheck/lint.
- [ ] Step 5: commit `feat(g5): wire building management and recruitment into the UI`.

### Task 3: Quest interface on the real workflow

**Files:** `apps/client/src/ui/chapters.tsx`, `apps/client/src/ui/quests.tsx` (new), `apps/client/src/ui/combat.tsx` (new), `apps/client/src/ui/root.tsx`, `apps/client/src/main.ts`, CSS, tests.

- [ ] Step 1: failing tests for: an available quest slot opens a briefing; difficulty selection is passed to `/api/quest/start`; the active-quest view renders counters/roster HP from `activeQuestState`; each quest action type is dispatched correctly; a victory result opens a reward dialog; reconnection restores the active quest from `/api/world`.
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement clickable chapters → briefing dialog → start; active combat panel with strikes and event actions; two-arg kill reports; `end_quest` through the existing builder; result/reward dialog; recovery from server state after reload/restart. Never fabricate a win.
- [ ] Step 4: confirm GREEN, run typecheck/lint and the existing quest unit tests.
- [ ] Step 5: commit `feat(g5): integrate the authoritative quest workflow into the UI`.

### Task 4: Inventory, HUD completeness and registration

**Files:** `apps/client/src/ui/inventory.tsx` (new), `apps/client/src/ui/hud.tsx`, `apps/client/src/ui/state.ts`, `apps/client/src/main.ts`, CSS, tests.

- [ ] Step 1: failing tests for: stored-item entries and placement action; mana and XP progress derived from server state; a register/sign-in mode toggle that calls `POST /api/account` and `POST /api/session`.
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement the inventory panel (stored items → `placeStoredItem`), mana/XP HUD additions, daily-bonus button, and the registration form. All values from authoritative world state.
- [ ] Step 4: confirm GREEN, run typecheck/lint.
- [ ] Step 5: commit `feat(g5): complete inventory, HUD and registration UI`.

### Task 5: Verification, inventory decisions and roadmap

**Files:** `scripts/e2e-test.mjs`, `re/data/ui-screens.json`, `docs/ROADMAP.md`, `docs/DEVELOPING.md` (if needed).

- [ ] Step 1: extend `e2e-test.mjs` with real DOM assertions for the full loop: register, build, collect, train, start quest, fight, end quest, reward, reload, server restart. Assert server refusals are visible and no duplicate reward. Keep all existing assertions.
- [ ] Step 2: run every gate in `docs/GOAL.md` §7 and record results verbatim.
- [ ] Step 3: record P0/P1/P2 decisions for the relevant screens in `ui-screens.json` with real model paths; do not flip unfinished screens. Add a G5.1 section to `ROADMAP.md` **outside** `## Group X` headers so existing counters are unchanged; record verified outcomes and remaining gaps.
- [ ] Step 4: run `check-roadmap`, `check-report-sync`, `screens.test.ts` and the full gate again; commit `docs(roadmap): record the G5.1 playable alpha`.
- [ ] Step 5: prepare the PR with the evidence table and the eight final deliverables from `docs/GOAL.md` §11.
