# Social Wars Legacy — G5.1: Essential Gameplay UI & Playable Alpha

## Role

Act as a senior full-stack game developer, game UI/UX engineer, and software architect responsible for advancing Social Wars Legacy toward a complete, production-quality, cross-platform game.

Repository: https://github.com/edisonmalasan/social-wars-legacy

Current baseline: `main` at `ba2667c` (PR #19 and PR #20 merged).

Your objective is to implement the next milestone, **G5.1 — Essential Gameplay UI & Playable Alpha**, using the project's established architecture, specifications, and development practices.

Work autonomously within the approved scope. Do not stop after analysis or documentation. Implement, test, verify, and prepare the changes for review.

## 1. Mandatory Repository Analysis

Before making changes:

1. Read `README.md`, `docs/CONTEXT.md`, `docs/ROADMAP.md`, and `docs/DEVELOPING.md`.
2. Review the existing ADRs and architectural constraints.
3. Examine the existing React UI, PixiJS renderer, server endpoints, client request builders, and game-state models.
4. Review `re/docs/14-ui-screen-inventory.md` and `re/data/ui-screens.json`.
5. Inspect the current G4 quest workflow and its existing tests.
6. Review the asset licensing restrictions in `docs/LICENSING.md`.
7. Identify which essential screens already exist, which are partially implemented, and which are missing.

Do not assume a feature is absent merely because it is unchecked in the roadmap. Verify the actual implementation first.

Produce a concise implementation plan grounded in the repository.

## 2. Primary Objective

Build a coherent, functional, polished gameplay interface that allows players to perform essential Social Wars actions without relying on developer tools or direct API calls.

The target gameplay loop is:

**Register/Login → Load Base → Construct Buildings → Train Units → Manage Army → Start Quest → Fight → Complete Quest → Claim Rewards → Return to Base**

Every implemented interface must use actual game data and communicate with the existing server-authoritative backend.

A working component with disconnected buttons or mocked gameplay is not considered complete.

## 3. Essential UI Implementation

### A. Building Management

Implement or complete:

- Building selection and information panels.
- Construction and placement interfaces.
- Upgrade actions and requirements.
- Resource collection controls.
- Construction and production countdowns.
- Clear error and success feedback.

Reuse existing models, APIs, and React components wherever possible.

### B. Recruitment and Army Management

Implement or complete:

- Unit recruitment panels.
- Unit statistics and requirements.
- Training queues and countdowns.
- Available army and unit counts.
- Unit selection for quests or battles.
- Clear insufficient-resource and unavailable-unit states.

Never allow the client to determine authoritative army or resource changes.

### C. Quest Interface

Integrate the completed G4 quest workflow into the actual gameplay UI.

Include:

- Quest selection and availability.
- Quest briefing and difficulty selection.
- Army selection where supported.
- Quest loading and active-state display.
- Combat actions connected to the native quest workflow.
- Progress indicators and objective counters.
- Victory, defeat, and reward screens.
- Safe recovery after reconnection or application restart.

Use the existing native quest-start and action APIs. Preserve the two-argument `set_quest_var` contract and the existing `end_quest` semantics.

Do not simulate victories using fabricated client-side outcomes.

### D. Inventory and Player Information

Implement or complete:

- Inventory navigation.
- Item categories and selection.
- Relevant item actions.
- Resource and currency displays.
- Player level and experience information.
- Selected-unit and selected-building details.

All displayed player-owned values must come from authoritative state.

### E. Core Popups and Navigation

Implement a reusable popup/dialog system that supports:

- Opening and closing dialogs.
- Keyboard navigation and Escape handling.
- Focus management.
- Accessible labels and controls.
- Loading, empty, and error states.
- Responsive layouts.
- Prevention of duplicate requests during pending actions.

Do not create multiple incompatible popup implementations.

## 4. UI/UX Quality Standards

The interface must feel like a cohesive strategy game rather than disconnected administrative panels.

Requirements:

- Maintain a consistent visual design system.
- Establish reusable colors, typography, spacing, and component styles.
- Preserve the original game's gameplay identity without copying proprietary interface artwork.
- Use smooth, purposeful transitions where appropriate.
- Maintain readable information hierarchy.
- Avoid unnecessary visual effects that impair performance.
- Support common desktop resolutions and reasonable responsive layouts.
- Preserve PixiJS as the world renderer and React as the interface layer.

Use original, properly licensed, or clearly temporary assets for any missing artwork.

Do not embed proprietary Zynga media into distributable builds.

Do not expand this milestone into a complete recreation of every historical popup.

## 5. Architecture and Engineering Constraints

Preserve all approved architectural decisions.

In particular:

1. Maintain the TypeScript monorepo.
2. Preserve the existing PixiJS v8 + React architecture.
3. Keep the server authoritative for combat, resources, progression, and rewards.
4. Preserve the existing 94-command catalogue and protocol compatibility.
5. Do not introduce runtime dependencies on `upstream/`.
6. Do not modify vendored upstream files.
7. Reuse existing client request builders, state models, and server endpoints.
8. Avoid duplicating business logic between client and server.
9. Avoid adding dependencies unless there is a justified need.
10. Keep the implementation compatible with future Tauri and Capacitor integrations.

If an architectural change is genuinely necessary, document its rationale and consequences before implementing it.

## 6. Scope Control

Prioritize a complete vertical slice over broad but shallow feature coverage.

Classify UI screens into:

- **P0:** Essential for completing the playable alpha.
- **P1:** Important for improving the gameplay experience.
- **P2:** Optional, historical, or future features.

Complete P0 first.

Do not automatically implement all 131 planned screens.

For each screen, record whether it is implemented, partially implemented, deferred, or intentionally excluded, together with supporting evidence.

Do not mark unfinished screens as complete merely to improve roadmap statistics.

## 7. Testing and Verification

Create meaningful tests covering the complete user workflow.

At minimum, verify:

- Building purchase, placement, and collection.
- Insufficient-resource behavior.
- Training queue interactions.
- Quest start and objective progression.
- Quest victory and defeat interfaces.
- Reward claiming without duplication.
- Reconnection and persisted game state.
- Server refusals and error handling.
- Popup accessibility and keyboard behavior.
- Existing G4 quest behavior remaining intact.

Use existing testing conventions and the project's end-to-end infrastructure.

Run all applicable verification gates, including:

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
node scripts/e2e-test.mjs
```

Also run the existing client build, licensing checks, and relevant repository verification scripts.

Do not report tests as passing unless they were actually executed successfully.

If a test requires unavailable hardware or external resources, report the exact limitation and complete every locally verifiable portion.

## 8. Documentation and Roadmap

After implementation:

1. Update `docs/ROADMAP.md` with the verified outcomes.
2. Record G5.1 as a proposed or approved milestone without corrupting existing roadmap counters.
3. Preserve the distinction between incomplete implementation, external blockers, non-goals, and deferred work.
4. Update developer documentation if component architecture or workflows change.
5. Record any remaining gaps honestly.
6. Keep licensing restrictions visible.

Do not mark G5.1 complete until the core gameplay loop is verified end-to-end.

## 9. Git and Pull Request Workflow

Use a dedicated feature branch:

`feat/g5-essential-gameplay-ui`

Follow the repository's established development workflow.

- Make logically grouped commits.
- Keep unrelated refactoring outside this milestone.
- Review the complete diff.
- Resolve test failures before submitting.
- Prepare a pull request with a clear description and verification evidence.
- Do not merge without the required checks and review approval.

## 10. Definition of Done

G5.1 is considered complete only when:

- A player can access the core gameplay through the actual UI.
- Essential building, recruitment, inventory, and quest workflows function.
- The client communicates with the existing authoritative server.
- Victory and reward progression cannot be forged by client-only changes.
- Essential UI interactions are responsive and accessible.
- The gameplay loop survives a client restart and server restart where supported.
- Relevant automated tests and repository gates pass.
- No proprietary assets are introduced into distributable output.
- The roadmap accurately describes what is complete and what remains.

## 11. Final Deliverables

Provide:

1. A summary of implemented features.
2. A list of new and modified components.
3. The completed P0/P1/P2 screen inventory.
4. Testing results and verification evidence.
5. Architectural decisions and trade-offs.
6. Known limitations and remaining blockers.
7. Pull request information.
8. A recommended next milestone.

## Execution Instructions

Begin by auditing the repository, then create an implementation plan and execute it incrementally.

Do not ask for confirmation on routine implementation decisions covered by this specification.

Do not introduce unnecessary protocol changes, weaken authority checks, or bypass licensing restrictions.

If a specific feature cannot be completed, implement the safely achievable portion, document the blocker, and continue with other approved work.

**Primary success criterion: A player can experience a complete and functional Social Wars Legacy gameplay loop through a polished interface, without using developer tools, manual API requests, or fabricated client-side outcomes.**