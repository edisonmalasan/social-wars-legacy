# GOAL: Social Wars Legacy — Autonomous Roadmap Execution Until Completion or Genuine Blockage

## Mission

You are the autonomous engineering orchestrator responsible for continuing the development of **Social Wars Legacy** toward its documented production-ready state.

**Repository:** https://github.com/edisonmalasan/social-wars-legacy

**Current verified baseline:** `main` at `1a6a89e` — PR #31 merged; see the live
checkpoint in section 12 below for the in-flight increment.

**Primary source of truth:** `docs/ROADMAP.md`

**Operating instructions:** `AGENTS.md`, especially **Autonomous Orchestration Mode**.

### Explicit Authorization

**ACTIVATE AUTONOMOUS ORCHESTRATION MODE.**

This instruction explicitly authorizes continuous, multi-task roadmap execution within the repository's existing engineering, security, Git, CI, and approval policies.

You are no longer operating under a single-milestone goal such as G5.1 or G5.2.

Your assignment is to continuously advance the entire approved roadmap.

**Do not stop merely because one milestone is finished, a PR is merged, or CI is green.**

A completed milestone is a checkpoint, not the end of the mission.

---

## 1. Mandatory Initialization

Begin by inspecting:

- `AGENTS.md`
- `docs/CONTEXT.md`
- `docs/ROADMAP.md`
- `docs/GOAL.md`
- `docs/DEVELOPING.md`
- `docs/RELEASE.md`
- `docs/LICENSING.md`
- Relevant architectural decision records
- The latest commits, pull requests, and repository test results

Verify the current branch, commit, working-tree status, and roadmap counts.

Do not blindly trust historical progress reports. Inspect code and evidence when necessary.

The earlier G5.1 and G5.2 milestones are completed. Preserve their historical documentation.

Treat `docs/ROADMAP.md` as the canonical source for requirements, priorities, exit criteria, verified outcomes, and outstanding dependencies.

If `docs/GOAL.md` still contains the finished G5.2 task, update it to reflect this persistent roadmap-execution objective while preserving useful historical records.

Do not rewrite the roadmap to manufacture completion.

---

## 2. Continuous Execution Loop

Follow this cycle:

**AUDIT → PRIORITIZE → PLAN → IMPLEMENT → TEST → REVIEW → PR → CI → MERGE → REASSESS → CONTINUE**

### Step A — Audit

Read the current roadmap and identify unfinished work.

Classify tasks into:

1. Actionable now.
2. Partially actionable.
3. Blocked by an external dependency.
4. Deferred by an approved decision.
5. Explicit non-goals.
6. Completed but requiring correction because evidence has become invalid.

Review related code, tests, contracts, and documentation before deciding.

### Step B — Prioritize

Select the highest-value eligible task using:

- Existing roadmap priorities and exit criteria.
- Dependencies and the critical path.
- Player-facing impact.
- Engineering risk.
- Security and correctness implications.
- Production-readiness impact.
- Availability of development resources.

Prefer tasks that unblock multiple downstream requirements.

Do not automatically choose the next unchecked checkbox without evaluating dependencies.

### Step C — Plan

For substantial work, use the installed Superpowers specification and planning workflows.

Define:

- The expected observable outcome.
- Existing implementation to reuse.
- Required changes.
- Security and compatibility risks.
- Test cases.
- Definition of Done.

Keep each implementation increment focused enough to review and verify.

### Step D — Implement

Use the appropriate Superpowers implementation workflow and subagents when supported.

Write tests for behavioral changes.

Implement actual functionality, not placeholders that merely satisfy documentation.

Reuse the established architecture.

### Step E — Verify

Run focused tests first, followed by the applicable repository verification gates.

Fix real regressions before proceeding.

Perform code review and address actionable findings.

### Step F — Integrate

Follow the Git workflow in `AGENTS.md`.

Create a feature branch, commit, push, open a PR, and confirm all required checks pass.

Merge only when branch protection, review requirements, and CI policies permit.

After merging:

1. Synchronize local `main`.
2. Verify the merged state.
3. Update the roadmap with verified evidence.
4. Record architectural decisions and remaining limitations.
5. Select the next eligible task.

**Immediately repeat the execution loop.**

Do not treat a successful merge as permission to terminate the mission.

---

## 3. Current Roadmap Priorities

The existing roadmap covers Groups A through I. The approved roadmap is the primary work queue.

At the current baseline, pay particular attention to these areas.

### A. Remaining Gameplay and Client Functionality

Investigate and complete eligible functionality including:

- Server-authoritative positional combat fidelity.
- Remaining quest-specific behavioral discrepancies.
- Q11 timer and army-wipe enforcement.
- Q08's documented unwinnable state.
- Expansion functionality and its missing server applier.
- Incomplete inventory, army, or gameplay interfaces.
- Remaining eligible B6 UI screens.
- Accurate end-to-end tests for higher-level gameplay.

Do not fabricate a winning quest outcome merely to make a test pass.

### B. Stronger End-to-End Coverage

Improve tests that currently cover only part of the behavior.

In particular:

- Non-zero production and collection rewards.
- High-level quests with team selection.
- Actual team validation and its impact on gameplay.
- Persistence across restart.
- Real browser interactions.
- Server-authoritative results.
- Failure and replay scenarios.

For difficult test prerequisites, investigate deterministic fixtures and supported test environments.

Do not bypass actual gameplay constraints in production code.

### C. Group G5 — Platform Clients

The roadmap still requires broader platform support.

Investigate what can be implemented without unavailable hardware.

Potential actionable tasks include:

- Capacitor mobile shell implementation.
- Android and iOS project configuration.
- Mobile-safe UI layout.
- Touch and gesture input.
- Automated responsive-layout tests.
- Firefox and WebKit browser automation.
- Development builds and CI configuration.

If a platform SDK is missing, determine whether it can safely be installed or provisioned through existing tooling.

Do not classify something as externally blocked merely because a tool is not preinstalled.

However, never claim real-device verification based only on emulation.

### D. Group H — Desktop Distribution

Continue eligible desktop release engineering:

- Unsigned development installers.
- Windows packaging.
- macOS build configuration.
- Linux packaging.
- Cross-platform CI where supported.
- Auto-update infrastructure and rollback tests.
- Reproducible build verification.

Code signing, notarization credentials, and production publication remain gated on their actual requirements.

### E. Group I — Production Readiness

Continue tasks involving:

- Reliability and security.
- Performance profiling.
- GPU-compatible benchmark fixtures.
- Monitoring and diagnostics.
- Deployment and rollback rehearsal.
- Documentation and release validation.
- Licensing and provenance safeguards.

Do not publish publicly while unresolved legal or licensing requirements remain.

---

## 4. Do Not Invent Milestones to Justify Stopping

G5.1 and G5.2 were useful development increments.

However, the execution model must no longer be:

"Complete G5.3 → Stop → Wait for next goal."

Instead:

"Complete the highest-priority eligible work → Verify → Merge → Continue to the next eligible work."

You may create internal implementation increments such as G5.3 if they help organize development.

But those labels are not execution boundaries.

Use the existing Groups A–I and the roadmap's actual unmet outcomes as the source of truth.

Do not expand the roadmap with artificial milestones merely to generate more work.

---

## 5. Blocker Resolution Protocol

An apparent blocker is not automatically a reason to stop.

When you encounter one:

**First:** Identify the exact missing dependency.

**Second:** Determine whether it can be resolved safely using available repository tools, test fixtures, standard SDKs, CI runners, or compatible alternatives.

**Third:** Implement any independently verifiable portion.

**Fourth:** Record the remaining blocked work with:

- The affected roadmap requirement.
- The precise blocker.
- What was attempted.
- What evidence was collected.
- What resource or decision would unblock it.

**Fifth:** Continue with another independent eligible task.

Do not repeatedly ask for resources that are unnecessary for the next independent task.

Do not claim all outstanding work is externally blocked without inspecting each requirement.

### Genuine Blockers

Examples include:

- Unavailable rights-holder permissions.
- Required code-signing credentials.
- Physical device testing that cannot be replicated.
- External Flash captures requiring unavailable accounts.
- Production publishing authorization.
- External infrastructure requiring paid access.

Never invent evidence to bypass these requirements.

---

## 6. Architecture and Security Boundaries

Preserve the repository's approved decisions:

1. TypeScript monorepo.
2. Deterministic rules engine.
3. Server-authoritative gameplay.
4. PixiJS world and React UI.
5. Existing protocol compatibility.
6. The 94-command catalogue unless explicitly authorized otherwise.
7. Strict two-argument `set_quest_var`.
8. Correct `end_quest` completion semantics.
9. Authenticated, transactional persistence.
10. Idempotent reward processing.
11. Read-only vendored upstream.
12. No Flash runtime dependency.
13. No unauthorized proprietary assets in distributable builds.
14. Pure-online architecture unless an approved ADR changes it.

Never weaken security, correctness, or compatibility simply to close roadmap items.

Document proposed architectural changes through the established ADR process.

Obtain explicit approval for irreversible, financially consequential, legally sensitive, or otherwise unauthorized external actions.

---

## 7. Autonomous Git and CI Workflow

Use the existing Git workflow in `AGENTS.md`.

For every independently reviewable increment:

1. Synchronize with the current `main`.
2. Create a task-specific branch.
3. Implement with tests.
4. Run appropriate local verification.
5. Commit and push.
6. Create a pull request.
7. Inspect CI results.
8. Fix failed checks.
9. Complete review requirements.
10. Merge when permitted.
11. Synchronize and continue.

Do not bypass branch protection or required reviews.

Never force-push or discard unrelated local changes without authorization.

Do not leave partially integrated work represented as completed.

### Required Verification

Use the appropriate existing scripts, including:

```bash
pnpm test
pnpm test:integration
pnpm typecheck
pnpm lint
pnpm build:content
pnpm check:content

node scripts/verify-command-catalogue.mjs
node scripts/check-roadmap.mjs
node scripts/check-report-sync.mjs
node scripts/run-cheat-battery.mjs
node scripts/golden-master.mjs
node scripts/check-coverage.mjs
node scripts/verify-upstream.mjs
node scripts/check-licensing.mjs
node scripts/check-no-flash.mjs
node scripts/e2e-test.mjs
```

Also execute applicable client, Tauri, performance, security, licensing, and platform-specific checks.

Use commands that actually exist in the repository.

A green local test suite does not replace required CI checks.

Maintain accurate distinctions between passed, failed, skipped, and unavailable tests.

---

## 8. Continuous Progress and State Preservation

After each completed task, update the relevant documentation.

Keep a concise execution record containing:

- Latest merged commit.
- Completed roadmap requirement.
- Verification evidence.
- Remaining applicable tasks.
- External dependencies.
- Next selected task.
- Active PR or branch, if any.

Use existing documentation conventions rather than creating unnecessary duplicate tracking systems.

The record must make it possible to resume after an interrupted session without restarting the investigation or losing decisions.

Do not claim work is continuing in the background if execution has actually stopped.

If the execution environment terminates, leave a precise checkpoint and continuation instructions.

When resumed under this same goal, continue from the last verified state.

---

## 9. Reporting Rules

Provide concise progress reports at meaningful checkpoints.

After each successful merge, report:

- What was completed.
- What tests passed.
- Which roadmap requirement changed.
- Which PR was merged.
- What task you selected next.

**A progress report is not a stopping condition.**

Avoid asking whether you should proceed after routine successful milestones.

Do not request a new user-authored goal for each G5.x increment.

If one task is blocked, explain the limitation and continue with another eligible task.

---

## 10. Actual Stopping Conditions

You may end autonomous roadmap execution only when one of these conditions applies:

1. Every authorized and actionable roadmap requirement has been completed and verified.
2. All remaining work is genuinely blocked, deferred, or explicitly excluded, and no useful independent implementation can proceed.
3. Required authorization or a material architectural decision prevents further safe progress, with no independent work available.
4. The environment cannot continue execution because of an unrecoverable technical limit.
5. The user explicitly instructs you to stop.

A green CI pipeline, a merged PR, or a completed G5.x milestone is **not** a valid stopping condition by itself.

Do not claim roadmap completion merely because every easily accessible checkbox has been addressed.

---

## 11. Final Project Objective

The long-term objective remains the outcome specified by `docs/ROADMAP.md`:

A playable, tested, maintainable Social Wars Legacy implementation with:

- An authoritative server.
- Faithful and deterministic gameplay.
- A functional modern interface.
- Supported web, desktop, and mobile clients.
- Appropriate testing and security.
- Reproducible distribution artefacts.
- Proper licensing and attribution.
- A release process that can be safely exercised.

Public distribution must remain gated by licensing and other release requirements.

Prioritize actual software quality and verified player-facing functionality over artificially completing checklist items.

---

# EXECUTION DIRECTIVE

**Activate Autonomous Orchestration Mode now.**

Start from the latest `main`, inspect the roadmap, and choose the highest-priority eligible task.

Create the first implementation plan and execute it.

After successful verification and merge, **automatically select and execute the next eligible roadmap task**.

Repeat that cycle within the available execution session.

Do not stop after G5.3, G5.4, or any other individual milestone.

Do not stop solely to present a completion summary.

Do not ask for routine continuation permission.

If a task is blocked, continue independent work.

Preserve a verifiable checkpoint if execution must be interrupted.

**Your assignment is continuous, evidence-driven advancement of Social Wars Legacy's approved roadmap—not completion of one isolated milestone.**

---

## 12. Execution checkpoint (maintained as work proceeds)

This is the resume point for an interrupted session. It is updated at each
verified checkpoint, not at every tool call.

- **Last verified `main:** `d303cba` — PR #32 (`feat: model the bonus screens and
  honour a lapsed streak`) merged with all four CI checks green. The prior
  `social-wars-legacy-main` session ended at `1a6a89e` (PR #31) when its context
  filled during compaction, not because the roadmap was finished.
- **Where that session stopped:** it had merged nine increments (#23–#31) and
  classified the remaining open items. Most are genuine blockers (Flash live
  captures, licence-gated art, missing platform hosts/devices, rights-holder
  response, signing credentials, production release). The one actionable area
  it identified is Group B3/G3's screen backlog, which it left at 90 implemented
  / 52 dropped / 118 planned.
- **Completed this session:** the daily/Monday bonus screens (PR #32, merged).
- **Next task selected:** the offer-pack store screens, because their prices,
  shapes, tiers and rewards are already modelled in `@swl/rules` and the only
  recorded deferral was a missing pack-picker surface.
- **Active branch / PR:** the offer-pack store increment adds a pure model in
  `packages/client/src/store.ts`, a store panel in the interface, and closes the
  four pack screens (now **98 implemented / 52 dropped / 110 planned**). Locally
  verified: `pnpm test` 1762/1762, `pnpm typecheck` clean, report sync, roadmap
  check and the real-browser e2e in Chrome and Edge — all passed.
- **Verification run for PR #32:** 1754/1754 tests, clean typecheck, golden master
  50/50 with 0 differences, cheat battery 11/11, report sync, roadmap check, and
  the real-browser e2e in Chrome and Edge — all passed; CI's four checks passed.
- **Remaining applicable tasks:** continue reducing the 114 planned screens in
  coherent, player-facing families; re-audit the blockers in section 5 before
  treating any as final; do not claim the frame-rate, platform or release items
  without their actual evidence.
- **On resume:** re-read this file and `docs/ROADMAP.md`, check `git status` and
  `gh pr checks`, then continue from PR #32's outcome.