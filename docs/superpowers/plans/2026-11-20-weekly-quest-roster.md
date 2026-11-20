# Weekly Quest Roster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the weekly quest resolvable from validated kill events derived from the client's five fixed gun-bot positions, without adding commands or trusting a client win flag.

**Architecture:** Add the five bots as elements of the weekly quest spec (refs derived from the documented tile coordinates). The applier increments the spec's `botsKilled` counter for each validated bot kill, so `isQuestVictory` becomes true only after five real events. The existing zero-event guard and once-only award remain.

**Tech Stack:** TypeScript, Node's built-in test runner, pnpm workspaces.

**Spec:** `re/data/quests.json` (weekly bot positions) and `upstream/socialwarriors/villages/quest/100000049.json` (five unit id 1061), as reconstructed client behaviour — never a runtime dependency.

## Global Constraints

- `upstream/` is read-only and never a runtime dependency; derive constants from documented client behaviour only.
- No new protocol commands; catalogue stays 94/94/94.
- The server owns the win and reward; a client win flag, loot or rank is never trusted.
- Five validated kills required; fewer must be refused. Zero events must remain refused.
- No runtime dependency; pnpm test, typecheck, lint, check-roadmap, check-report-sync and verify-command-catalogue must pass.

## Review Focus

- A client cannot win by sending the same bot ref five times (dedupe).
- A client cannot win by sending an off-roster ref.
- Four kills must not pay; five must pay exactly once.
- The weekly timer/defeat rules are unchanged.

---

### Task 1: Weekly roster and counter increments

**Files:**
- Modify: `packages/rules/src/quest.ts`
- Modify: `packages/server/src/apply.ts`
- Test: `packages/rules/src/quest.test.ts`, `packages/server/src/apply.test.ts`

- [ ] **Step 1: Write failing tests** for: weekly spec has five bot elements with refs derived from the documented positions; `killQuestElement` on each bot increments the server's `botsKilled` counter through the applier; five kills allow `end_quest` to pay the weekly cash reward; four kills are refused; a repeated ref is idempotent; an off-roster ref is refused.
- [ ] **Step 2:** Run the focused tests and confirm RED.
- [ ] **Step 3:** Add the five elements to the weekly `QuestSpec` using the client's item id 1063 and refs derived from the five positions. In `applyQuestEvents`, for a quest whose win is `countersAtLeast` on `botsKilled`, increment that counter once per distinct validated bot kill (derive the counter name from the spec, not from client input).
- [ ] **Step 4:** Run the focused tests plus shim tests and confirm GREEN.
- [ ] **Step 5:** Run the whole gate before committing.
- [ ] **Step 6:** Commit `feat(f): make the weekly quest resolvable from validated bot kills`.

### Task 2: Roadmap disposition

**Files:** Modify `docs/ROADMAP.md`.

- [ ] **Step 1:** Update *Unimplemented layers* to record that the weekly quest now resolves; the eight hardcore quests and the counter quests without event sources remain, needing build-time roster extraction and client instrumentation.
- [ ] **Step 2:** Add an amendment-log entry. Do not tick the G4 quest item unless every remaining sub-feature is genuinely supported (it is not).
- [ ] **Step 3:** Run the whole gate and commit `docs(roadmap): record weekly quest resolution`.
