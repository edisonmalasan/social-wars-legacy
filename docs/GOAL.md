# GOAL: Social Wars Legacy — G5.2 Gameplay Systems Completion & UI/UX Refinement

## Mission

Continue development of Social Wars Legacy from the successfully completed G5.1 milestone.

**Repository:** https://github.com/edisonmalasan/social-wars-legacy

**Baseline:** `main` at `7a584b8` — PR #21 merged.

**New milestone:** G5.2 — Gameplay Systems Completion & UI/UX Refinement.

Your responsibility is to complete the remaining high-priority P1 gameplay systems, improve the existing interface, and deliver a more complete playable alpha without breaking the functionality verified in G5.1.

This is an **implementation goal**, not a request for another analysis-only report.

Use the installed Superpowers workflow for repository exploration, specification, planning, implementation, testing, debugging, code review, and verification.

Work autonomously within the approved scope. Make justified implementation decisions using repository evidence, existing ADRs, and test results.

Do not stop after writing a plan. Continue through implementation and verification.

---

## 1. Establish the Current Baseline

Before changing code:

1. Read `docs/CONTEXT.md`, `docs/GOAL.md`, `docs/ROADMAP.md`, and `docs/DEVELOPING.md`.
2. Examine PR #21 and its resulting implementation.
3. Review `re/docs/14-ui-screen-inventory.md` and `re/data/ui-screens.json`.
4. Inspect the current React components, PixiJS renderer, pure view models, and native server endpoints.
5. Review relevant quest, production, economy, and army rules.
6. Inspect existing e2e tests and the CI configuration.
7. Verify the current branch, working-tree state, and latest commit.

Treat G5.1 as completed work.

Do not recreate components already implemented or replace working systems unnecessarily.

Identify the exact remaining gaps, their dependencies, and the smallest safe changes needed to close them.

Record a concise technical plan using the repository's existing Superpowers/SDD conventions.

---

## 2. Primary Objective

Complete the missing user-facing gameplay workflows:

**Base → Production → Collection Period → Recruitment → Army Management → Quest Team Selection → Combat → Victory/Defeat → Reward Details → Next Mission**

The player must be able to complete these interactions through the actual rendered interface.

Every gameplay operation must remain server-authoritative.

Success is not measured by how many new components exist. It is measured by whether real players can complete the workflows reliably without debug tools, manual requests, or fabricated game state.

---

## 3. P0 — Authoritative Reward Payloads and Result Screens

### Problem

G5.1 successfully pays quest rewards, but the actual native command outcome returns `kind: "none"`.

The existing `QuestResultView` already supports reward rows, but those rows are empty because the response does not contain the authoritative reward information.

### Required implementation

Trace the complete quest-reward flow:

- `packages/server/src/apply.ts`
- `apps/server/src/app.ts`
- `packages/protocol/src/commands.ts`
- `packages/client/src/questview.ts`
- `apps/client/src/main.ts`
- `apps/client/src/ui/quests.tsx`

Implement an authoritative, typed reward result from the successful server transaction.

The result should provide the actual awarded resource types and amounts.

Reuse the existing `CommandResult` rewards variant wherever appropriate.

### Requirements

1. The server computes and grants rewards.
2. The response reflects exactly what the server granted.
3. The client only formats and displays those results.
4. Failed quests never display granted rewards.
5. Duplicate completion attempts never issue additional rewards.
6. Retried requests remain idempotent.
7. Result information remains consistent with persisted player state.
8. Legacy protocol compatibility is preserved.

Do not calculate reward rows from client-side formulas, hardcoded reward tables, or guessed wallet differences.

Avoid introducing a second reward authority or a second reward-granting operation.

If displaying a reward after reconnecting requires retaining an authoritative receipt, design the smallest safe persisted representation rather than replaying a reward transaction.

### Result screen improvements

Implement dedicated presentations for:

- Quest victory.
- Quest defeat.
- Reward details.
- Mission completion confirmation.
- Next mission availability.
- Retry or return to base.

Use the existing shared accessible Dialog architecture.

Do not introduce another unrelated modal system.

The next-mission action must respect actual server-side quest progression and unlock restrictions.

**Acceptance criteria:** A player completes a quest and sees exactly the rewards granted by the server. Replay, failure, and restart cases cannot produce incorrect reward displays or duplicate payments.

---

## 4. P0 — Resource Collection Period Selection

### Problem

G5.1 supports building production and resource collection, but it does not provide the original collection-period chooser.

The existing protocol already defines the `activate` command. Verify whether its server-side application is complete before implementing the UI.

### Required implementation

Implement an interactive production-period selector using the documented collection periods:

- 5 minutes
- 60 minutes
- 240 minutes
- 480 minutes

The existing rules describe corresponding production multipliers of 0.25×, 1×, 2×, and 3×. Verify all indices, eligible buildings, costs, and constraints against the actual rules before using them.

### Required behavior

1. Select a supported resource-producing building.
2. Open its production settings.
3. Display available collection periods.
4. Show the server/content-derived production details.
5. Select and activate a period.
6. Display the active production cycle and countdown.
7. Collect resources after the server confirms readiness.
8. Update the interface from the returned world state.

Validate eligibility, period indices, resource capacity, timestamps, and duplicate requests server-side.

Do not allow users to bypass timers by modifying the client clock.

Do not permit arbitrary production multipliers.

Use the current shared dialog and feedback components.

**Acceptance criteria:** A player selects a production period, waits for the authoritative completion condition, collects the correct resources, and sees the next production state.

---

## 5. P0 — Army Management and Team Selection

### Problem

G5.1 implements recruitment and training queues, but full army roster management and team selection remain deferred.

### Required implementation

Create a functional army-management interface that supports:

- Viewing owned units.
- Unit names and appropriate statistics.
- Available unit quantities.
- Units currently training.
- Unit selection and deselection.
- Selected army composition.
- Relevant population or capacity restrictions.
- Quest-specific eligibility rules.
- Clear validation and error feedback.

Use existing content and server-owned player inventory.

Do not manufacture unit ownership or availability.

### Team selection

Implement team selection for quest workflows where the original game requires it.

Review `re/docs/12-quest-system.md` and the original `QUESTS_WITH_TEAMS` behavior. The documented team-selection quests include the four higher-level quests.

Do not incorrectly force every quest to use the same selection workflow.

For supported quests:

1. Display the player's available army.
2. Allow selection of eligible units.
3. Validate availability and restrictions.
4. Submit the selected composition to the authoritative server.
5. Persist or bind the accepted composition to the correct active quest.
6. Reject forged, unavailable, excessive, or disallowed selections.

First determine whether the current quest-start endpoint accepts team composition.

If additional native endpoint fields are necessary, make the smallest backward-compatible change with server validation and tests. Do not change the 94-command catalogue simply to add a selection interface.

The selected team must matter to the authoritative gameplay state. A cosmetic team selector that is ignored by the server is not complete.

If full team-to-combat integration exposes a larger missing simulator dependency, implement the safely supported portion, document the precise limitation, and do not claim full team-selection fidelity.

**Acceptance criteria:** Players can manage owned units and, for applicable quests, select a team whose composition the server validates and actually uses.

---

## 6. P1 — Remaining Gameplay Interface Improvements

After the three P0 goals are complete, continue with the remaining achievable P1 work.

### Building and inventory improvements

- Improve building information and production feedback.
- Implement item-category tabs using existing inventory data.
- Improve building upgrade and collection confirmations.
- Implement expansion UI if the existing authoritative server operation supports it.
- Show requirements, costs, and refusal reasons clearly.

### Quest navigation improvements

- Add a coherent next-mission flow.
- Improve mission progression indicators.
- Improve difficulty and team-selection presentation.
- Preserve progress correctly when a dialog closes or the client reloads.

### General interaction improvements

- Prevent duplicate submissions.
- Provide consistent loading and disabled states.
- Restore focus when dialogs close.
- Improve handling of long content and small viewports.
- Ensure server refusals are displayed meaningfully.
- Keep the interface navigable without a mouse where practical.

Avoid adding decorative components that do not improve the player's ability to understand or operate the game.

---

## 7. UI/UX Standards

The existing G5.1 UI is the foundation.

Refine it rather than rebuilding it.

Maintain:

- PixiJS v8 for the game world.
- React for interface panels.
- The existing shared Dialog.
- The existing Feedback system.
- The established typography and styling conventions.
- Server-driven state models.
- Reusable UI elements and consistent spacing.

Improve the interface so that it feels like an integrated strategy game rather than a collection of development tools.

Prioritize usability, readable resource information, understandable unit statistics, and clear gameplay feedback.

Use purposeful animation where it helps convey changes.

Do not invent unrelated features, promotional sections, filler text, or unnecessary UI elements.

### Asset restrictions

Do not introduce proprietary Zynga artwork, audio, or fonts into distributable outputs.

Use existing CSS/SVG primitives and appropriately licensed assets.

Do not let unavailable original art stop implementation of functional UI elements.

---

## 8. Non-Negotiable Architecture

Preserve these decisions:

1. Server-authoritative gameplay, economy, and rewards.
2. Shared TypeScript rules and protocol types.
3. PixiJS world renderer and React DOM interface.
4. Existing 94-command catalogue and legacy compatibility.
5. Two-argument `set_quest_var`.
6. Explicit quest-start semantics.
7. `end_quest` as completion, never implicit initialization.
8. Transactional and idempotent reward processing.
9. No runtime dependency on `upstream/`.
10. No modification of vendored source files.
11. No Flash dependency in shipped applications.
12. No unauthorized proprietary assets in release builds.

Where a native API enhancement is genuinely needed, document and test it instead of silently changing the wire contract.

---

## 9. Testing Strategy

Follow test-driven development where practical.

Add unit tests, integration tests, and actual browser e2e coverage for the new features.

### Reward tests

Verify:

- Successful quest returns exact awarded reward rows.
- Client displays authoritative amounts.
- Failure grants and displays nothing.
- Duplicate completion cannot pay twice.
- Request retries produce consistent results.
- Server restart preserves rewards and relevant receipts.

### Collection-period tests

Verify:

- Every supported period.
- Correct period validation.
- Production not ready.
- Production ready.
- Duplicate collection.
- Insufficient capacity.
- Invalid building and invalid period.
- Persistence across reload/restart.

### Army tests

Verify:

- Correct owned-unit counts.
- Selection and deselection.
- Unavailable units.
- Exceeded quantities.
- Quest restrictions.
- Server-side acceptance or refusal.
- Correct binding to the active quest.
- No client-forged unit availability.

### UI tests

Verify:

- Opening and closing dialogs.
- Keyboard and focus behavior.
- Responsive layouts.
- Accurate loading and refusal states.
- No duplicate actions.
- Correct result and reward presentation.

### End-to-end requirements

Extend the actual G5.1 Chrome and Edge e2e tests.

The browser must interact with rendered controls, not merely call internal request builders.

Test the complete enhanced gameplay loop, including production-period selection, army selection where supported, quest completion, reward presentation, reload, and server restart.

Use deterministic clocks and fixtures where required. Do not introduce arbitrary sleeps or weaken assertions to make tests pass.

Fix failing tests at their cause, not by skipping them.

---

## 10. Verification Gates

Run all applicable existing project gates, including:

```bash
pnpm test
pnpm test:integration
pnpm typecheck
pnpm lint
pnpm build:content

node scripts/verify-command-catalogue.mjs
node scripts/check-roadmap.mjs
node scripts/check-report-sync.mjs
node scripts/run-cheat-battery.mjs
node scripts/golden-master.mjs
node scripts/check-coverage.mjs
node scripts/e2e-test.mjs
```

Also run the client build, relevant security checks, licensing checks, and CI-defined validation steps.

G5.1 recorded false positives when running certain licensing/no-Flash checks after generating `dist` artefacts. Investigate those precisely, distinguish legitimate assets from harmless identifiers, and make any checker correction narrowly scoped and tested.

Never disable a security or licensing check just to get a green result.

Do not claim that a platform or test passed unless it actually ran.

---

## 11. Documentation and Milestone Tracking

Update the appropriate documentation:

- `docs/ROADMAP.md`
- `docs/GOAL.md` or the repository's established milestone history
- Relevant developer documentation
- `re/data/ui-screens.json`
- Architectural decisions, where applicable

Preserve G5.1's historical completion record.

Record G5.2 separately without corrupting the established 401-item roadmap accounting.

Use evidence-based screen classifications.

Do not label a partially implemented feature complete.

Maintain the distinction between:

- Implemented and verified.
- Partially implemented.
- Deferred.
- Externally blocked.
- Explicit non-goals.

Do not claim that the full positional combat simulator, original artwork, mobile builds, or production release have been completed as part of G5.2.

---

## 12. Development Workflow

Use the installed Superpowers skills and established repository practices.

Suggested workflow:

1. Inspect the current implementation.
2. Produce a scoped implementation plan.
3. Write failing tests.
4. Implement authoritative reward responses.
5. Implement resource-period selection.
6. Implement army management and team selection.
7. Complete achievable P1 improvements.
8. Run focused tests after each increment.
9. Run the full verification gate.
10. Perform code review and fix actual findings.
11. Update documentation and the milestone ledger.
12. Prepare the completed pull request.

Suggested branch:

`feat/g5-2-gameplay-systems`

Suggested PR title:

`feat(g5.2): complete gameplay systems and reward UI`

Keep commits logically organized.

Do not include unrelated refactoring.

Follow repository branch protection and review requirements. Do not bypass required checks.

---

## 13. Definition of Done

G5.2 is complete when:

- [ ] The native quest response returns authoritative reward details.
- [ ] Dedicated result/reward dialogs show the correct outcomes.
- [ ] Failed and replayed quests cannot generate duplicate rewards.
- [ ] Players can select valid production periods through the UI.
- [ ] Collection timers, requirements, and rewards remain server-authoritative.
- [ ] Army management displays real player-owned units.
- [ ] Team selection is implemented and server-enforced for supported quests.
- [ ] Quest navigation and next-mission interactions work correctly.
- [ ] The existing G5.1 gameplay loop remains functional.
- [ ] The shared dialog and feedback architecture is preserved.
- [ ] Chrome and Edge e2e tests verify the enhanced gameplay loop.
- [ ] All applicable CI, security, protocol, and licensing checks pass.
- [ ] Documentation accurately records completed and unfinished work.

A visually polished interface with disconnected actions does not satisfy this definition.

An API that works but cannot be used through the actual game interface also does not satisfy it.

---

## 14. Final Report

When implementation and verification are complete, provide:

1. Implemented features and their player-facing behavior.
2. Files and modules changed.
3. New or modified server/API contracts.
4. Exact automated test results.
5. Chrome/Edge e2e verification evidence.
6. Compatibility and security verification.
7. Architectural decisions and trade-offs.
8. Remaining blockers and fidelity gaps.
9. Pull request and merge status.
10. Recommended next milestone, G5.3.

Do not represent unmerged work as merged or partially tested features as verified.

---

## Final Execution Directive

**Continue Social Wars Legacy from G5.1 to G5.2.**

Do not restart the project, replace the established architecture, or spend the milestone rebuilding features already completed.

Focus on closing the actual gameplay gaps identified in G5.1:

**Reward payloads → Collection-period chooser → Army management/team selection → Result and mission navigation → Integrated gameplay verification.**

Execute the work, verify it, resolve regressions, and deliver a reviewable implementation.

Make routine technical decisions autonomously using repository evidence.

Escalate only decisions that would alter approved architecture, introduce licensing risks, weaken security, or materially expand scope.

**Success criterion: G5.2 delivers a complete, coherent, and server-authoritative gameplay experience that meaningfully extends G5.1 rather than simply adding more screens.**