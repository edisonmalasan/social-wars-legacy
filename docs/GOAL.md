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

- **Last verified `main`:** `911057e` — PR #60
  (`feat/soulmixer-help-turbina`, the soul-mixer help and turbine drawn from
  recovered state, 3 screens) merged. The chain from the prior verified
  checkpoint (`27f1dab`, PR #57 — inventory cells and the HUD info popup,
  2 screens) is PR #58 (`7cda30e`, docs: correct the verified screen counts),
  PR #59 (`96a2ca8`, mystery-box screens, 4 screens) and PR #60 (`f0658fb`,
  soul-mixer help and turbine, 3 screens). The verified screen inventory is
  **150 implemented / 52 dropped / 58 planned**; `node scripts/check-roadmap.mjs`
  reports 401 items and 22 open (A 9/0, B 42/4, C 14/0, D 32/0, E 37/1,
  F 54/0, G 78/8, H 14/4, I 99/5), and
  `node scripts/check-report-sync.mjs` agrees with the implementation (4 claims)
  after `pnpm build:content`. The honest scope of each family, including what
  stays planned behind the art gate, the corrected robot-research gate and the
  confirmed fusion blocker, is recorded in *Final screen-family refresh* in
  `docs/ROADMAP.md`. This checkpoint is a documentation-only increment; only
  the orchestrator merges branches.
- **Previously verified `main`:** `27f1dab` — PR #57
  (`feat/add-remaining-screens`, the sixth screen-family increment: inventory
  cells and the HUD info popup, 2 screens) merged. The chain from the earlier
  checkpoint (`4551edd`) was PR #56 (`47f0d48`, docs: refresh the verified
  screen-family state after PRs #51–#55) and PR #57 (`27f1dab`, inventory cells
  and the timed info popup). The inventory at that checkpoint is preserved in
  *Final screen-family refresh* in `docs/ROADMAP.md`; PRs #58–#60 superseded it.
- **The six delivered families (checked, honest scope):** onboarding and
  confirmation panels live in the one shared dialog (the cosmetic loading
  animation and the art-gated parent popups stay planned); roster, team
  thumbnails and unit XP come from server state (portrait art stays planned);
  the reusable chrome primitives add no second modal (artwork-gated icons and
  portraits stay planned); expansion growth, buy-for prompts and the collections
  tab are drawn from server/content state, with `neighbors`/`inventory_qte`
  display-only prompts and the Share! popup and art excluded; hospital
  recovery and the attack-symbol legend use server data and the rules'
  vocabulary, with the gender choice planned because the save has no
  character-setup field and no command exists; and `GUI/InventoryItem.as` and
  `GUI/InfoPopup.as` are drawn in `apps/client/src/ui/detailpanels.tsx` —
  inventory cells with UI-only drag/grid layout (the Place gesture is unchanged
  and still sends `place_stored_item`), and a HUD popover with a display timer
  and anchor-relative `reposition`, with each readout's lines coming from
  `packages/client/src/hud.ts` and the original art excluded.
- **The two latest families (checked, honest scope):** the mystery-box screens
  draw pack 4's four candidates and a super pack's priced rarity rows from
  content and the popups' own literals; Buy only sends a request and the panel
  renders what the server actually granted into its store, never a local roll.
  Pack 4 is disabled in the shipped content, so its preview is drawn but Buy is
  withheld, and the original box art stays excluded. The soul-mixer help and
  turbine render the recovered four-step copy verbatim and read turbine state
  from the server-owned save only when it is well-formed, otherwise a labelled
  placeholder with no fabricated countdown; they offer no Powerup, Speedup or
  Fusion gesture — those words are help text, not working controls. The
  read-only audit's **confirmed fusion blocker** — no applier cases for
  `buy_powerups` / `soulmixer_speedup` / research commands, no recovered
  `(inputA, inputB, powerupLevel) -> output` rule (raw AS3 absent), unpriced
  `soulmixer_speedup`, and breeding only as `PopupSoulMixer`'s art shell —
  keeps the fusion and breeding screens planned.
- **Corrected research-centre gate:** the old note on `PopupResearchCenterMC.as`
  falsely called it the magic tech tree. It is really the late-era AREA 51 /
  ROBOTIC CENTER robot-research screen (Zynga build-process art, a 6-hour cycle,
  an ADR-20 social "Hire friends" gesture). The new server only stores
  `researchItemNumber`/`researchStepNumber`/`timeStampDoResearch` and applies
  **none** of `next_research_item`, `next_research_step`,
  `research_buy_step_cash`, `reset_research_item` or `finish_robotic_help`, so
  its gestures have no authoritative answer. Both research-centre screens stay
  planned; no parity is claimed and the magic tech tree is not a substitute.
- **Previously verified `main`:** `e11cbca` — PR #49
  (`feat/check-mobile-capacitor-config`, the read-only mobile-config check)
  merged. The merge chain since the prior checkpoint (`6954a19`) is PR #47
  (`f4b4e69`, docs: update the verified state), PR #48 (`608d940`, read-only
  Flash-differential evidence audit) and PR #49 (`e11cbca`, mobile Capacitor
  config check with a 10-case tamper self-test). Before that, the chain ending
  at `6954a19` was PR #32 (`d303cba`), PR #33 (`2d273be`), PR #34 (`3228d0e`),
  PR #35 (`b4aea12`), PR #36 (`1689882`), PR #10 (`a0befef`), PR #37 (`6e084e7`),
  PR #38 (`31b6834`), PR #39 (`9026017`), PR #40 (`0053306`, unsigned Linux CI
  bundles), PR #41 (`fa92150`, WebKit evidence + checkpoint), PR #42
  (`cf9941d`, multi-resolution phone matrix), PR #43 (`8de433a`, assault
  result/history/HUD selectors and panels), PR #44 (`013d57c`, mounting those
  panels in the one shared dialog), PR #45 (`bbb7ff9`, docs: record the #40–#44
  batch and refresh the checkpoint) and PR #46 (`6954a19`, test: pin the
  rollback decision path with a test-side executor seam — test coverage only,
  no real executor or installer hook). The prior `social-wars-legacy-main`
  session ended at `1a6a89e` (PR #31) when its context filled during compaction,
  not because the roadmap was finished.
- **Where that earlier session stopped:** it had merged nine increments (#23–#31)
  and classified the remaining open items. Most are genuine blockers (Flash live
  captures, licence-gated art, missing platform hosts/devices, rights-holder
  response, signing credentials, production release). The one actionable area
  it identified is Group B3/G3's screen backlog, which it left at 90 implemented
  / 52 dropped / 118 planned. That historical classification is preserved here;
  the blockers in section 5 are not rewritten or assumed resolved.
- **Completed this session:** the daily/Monday bonus screens (PR #32), the
  offer-pack store screens (PR #33), the Research LAB interface (PR #34), and
  the battle spell book (PR #35) — all merged with green CI. The spell book draws
  the learned-only, three-to-a-page model from `magic.ts` with spell levels,
  mana state and a cast button, without changing the screen counts (those
  screens were already `implemented` as models). Since the `b4aea12` checkpoint
  the session also merged: the refreshed checkpoint (PR #36); the B7 premium and
  offer-pack purchase-flow specification in
  `re/docs/03-commands-quests-economy.md` (PR #10); the **server-owned mission
  countdown** (PR #37), which is the landed form of the preserved mission-timer
  WIP below; the **full WebKit (Playwright) end-to-end session** (PR #38) —
  `scripts/e2e-test-webkit.py` driving the shared harness parameterised into an
  `ENGINES` config, with player `e2e-ui-webkit`, data prefix `swl-wk-e2e-` and
  its own screenshot, exit 0, no console errors and no `window.__swl` commands;
  and the roadmap-drift corrections (PR #39). Firefox was re-run after the
  shared-harness change and stayed green (`browsers run: firefox (Playwright,
  Gecko)`, exit 0, no console errors).
  Since `9026017` the session also merged: PR #40's **informational,
  non-required `linux-bundle` CI job** (`ubuntu-latest`, unsigned `.deb` and
  `.AppImage`, green on its first real run; the four protected checks are
  unchanged); PR #41's **WebKit end-to-end evidence and checkpoint record**
  (already on `main`, not repeated here); PR #42's **five-viewport emulated-phone
  matrix** in `scripts/e2e-mobile-layout.mjs` (390x844@dpr2, 360x640@dpr2,
  414x896@dpr3, 320x568@dpr2, 760x600@dpr1, free ports, all original assertions,
  explicit `EMULATION` output — no device claim); PR #43's **pure server-owned
  assault selectors** in `packages/client/src/featurestate.ts` and panels in
  `apps/client/src/ui/assault.tsx`; and PR #44's mounting of those panels in the
  one shared `Dialog` via `showAssaultPanel(kind)` (31/31 focused tests,
  1786/1786 serial full suite, typecheck, e2e in Chrome and Edge). Nine screens
  were honestly reclassified as implemented in that batch; after PRs #51–#55,
  #57, #59 and #60 the inventory now reads **150 implemented / 52 dropped /
  58 planned**, with art-licence-blocked screens still planned. Three further
  increments are on `main`: PR #47
  (`f4b4e69`) refreshed the verified-state documentation for the `6954a19`
  checkpoint; PR #48 (`608d940`) added `scripts/flash-differential.mjs`, a
  read-only evidence audit of the sole captured `end_quest` payload — it exits
  0 with `insufficient evidence — E4 stays blocked` because that capture has no
  seed, roster, wallet snapshot, clock or authoritative outcome, so no Flash
  parity is claimed, the E4 box stays open and the golden-master corpus remains
  50 scenarios, 0 differences; PR #49 (`e11cbca`) added
  `scripts/check-mobile-config.mjs`, which independently validates
  `capacitor.config.ts` against the `apps/client` build output with a 10-case
  tamper self-test and reports `native Android/iOS builds NOT RUN — no
  JDK/Android SDK/Xcode` — the config is coherent, but no native build or device
  run was performed. Neither script changes the item accounting.
- **Verified roadmap state:** `node scripts/check-roadmap.mjs` reports 401 items,
  22 open (B 4, E 1, G 8, H 4, I 5); screen inventory is **150 implemented /
  52 dropped / 58 planned**. The Status Summary still reads G 78/8. The G5
  blocker row records Firefox and WebKit as verified, with branded Safari and
  real devices the only unrun browsers; the desktop and installer rows now
  record **Linux bundling in CI, unsigned** while staying open for macOS and
  signing. This checkpoint refresh records that state: the accompanying
  documentation increment updates `docs/ROADMAP.md` to the same verified counts
  and does not touch `re/data/ui-screens.json` or any code.
- **Preserved WIP (mission timer):** the in-flight mission-timer changes are not
  lost, and have now landed. They were saved as a patch at
  `C:\Users\Edison\AppData\Local\Temp\opencode\mission-timer.patch` (13,682 bytes,
  10 files), verified to apply cleanly to `b4aea12` with `git apply --3way` in a
  throwaway worktree, and remained as `stash@{0}` on the orchestrator checkout.
  The work was owned by worker thread [Mission timer wiring](t3-thread://v2/1e103b76-04b0-4a8b-906e-1586e707da69/thread:delegated-task:command%3Amcp%3A7440c1fc-8080-43e5-8030-33e464b7a159%3Adelegate-task%3A92be84c0-9e0e-4b83-9c94-73ee93c16f59)
  on branch `feat/server-mission-countdown` and merged as PR #37 (`6e084e7`),
  drawing the server-owned mission countdown. The patch history is preserved
  here for audit.
- **Worker threads:** the three threads carried over from the prior checkpoint
  have all delivered on `main`: [Mission timer wiring](t3-thread://v2/1e103b76-04b0-4a8b-906e-1586e707da69/thread:delegated-task:command%3Amcp%3A7440c1fc-8080-43e5-8030-33e464b7a159%3Adelegate-task%3A92be84c0-9e0e-4b83-9c94-73ee93c16f59)
  → PR #37; the blocker audit ([audit thread](t3-thread://v2/1e103b76-04b0-4a8b-906e-1586e707da69/thread:delegated-task:command%3Amcp%3A7440c1fc-8080-43e5-8030-33e464b7a159%3Adelegate-task%3A90c92235-6012-460e-b7da-091c18c88911))
  → the count and blocker corrections in PR #39; and the read-only review of
  stale PR #10 → PR #10. The later increments were delivered on their own
  branches too — `ci/add-linux-desktop-bundles` (#40),
  `docs/webkit-e2e-checkpoint` (#41), `feat/mobile-layout-matrix` (#42),
  `feat/assault-history-hud` (#43) and `feat/mount-assault-panels` (#44) — and
  all five are on `main`; no new thread links were recorded for them. Only the
  orchestrator merges; no worker merges its own branch. This checkpoint refresh
  is a documentation-only increment prepared on its own task branch for review,
  not a merge.
- **Next, from the audit ranking:** re-audit the section 5 blockers before
  treating any as final, and keep reducing the 58 planned B6 screens in
  coherent, player-facing families — the six families in PRs #51–#55 and #57 are
  the latest, and the screens that need Zynga's art stay planned behind the licence
  gate. The gender/character-setup choice also stays planned: the save has no
  character-setup field and no command exists. The
  remaining platform and release items should be advanced only with evidence:
  branded Safari and real devices, signed installers and a macOS runner (Linux
  bundling is now in CI but unsigned and informational), the Flash live captures
  and the differential test. Do not claim frame-rate, platform or release items
  without evidence, and do not reopen the Firefox/WebKit verdicts recorded in
  `docs/ROADMAP.md`.
- **Environment note (historical):** `node scripts/check-no-flash.mjs` failed
  locally during the PR #32 verification on stale built `dist/content-bundle.json`
  and `dist/frame-manifest.json` files (SWF string references); this was a local
  build-artefact condition, not a source change. CI's Scan check passed.
- **On resume:** re-read this file and `docs/ROADMAP.md`, check `git status`,
  `git stash list`, `git worktree list` and `gh pr checks`, then continue from the
  verified `911057e` state and the worker results above.