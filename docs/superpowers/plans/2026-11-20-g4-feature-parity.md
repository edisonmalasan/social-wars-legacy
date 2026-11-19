# G4 Feature Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the two open Group G4 roadmap items genuinely satisfiable — the six features (quests, goals, darts, market, premium, weekly bonus) functional, and social features visibly out of scope — without claiming a feature works when a layer is missing.

**Architecture:** The server stays authoritative. Where a command is priced but has no applier, add a server-side rule first; then add thin client request builders and read-only state selectors that read the server's save; then wire the one gesture that is already drawn (the goal button); finally record the social services as an out-of-scope decision using the project's existing ADR + screen-inventory + checked-test pattern.

**Tech Stack:** TypeScript, Node's built-in test runner, pnpm workspaces.

**Spec:** `docs/ROADMAP.md` (Group G4, Group F1, Group I7) and `AGENTS.md` § Architecture Non-Negotiables.

## Global Constraints

- The client is the specification; the server is authoritative. The client never decides an outcome and never sends a claimed result.
- The 8-slot resource vector is `[energy, xp, gold, wood, oil, steel, cash, mana]`.
- No `flash_debug`; no authentication inherited from upstream.
- The rules engine is pure: no `Date.now()`, no unseeded randomness, no I/O. The server owns the clock and issues the seed.
- Every command's cost is computed by the server from the content bundle, never accepted from the client; a refused command spends nothing.
- Command argument order comes from `packages/protocol/src/commands.ts`, which is the authority.
- "Functional" in this repository means rules model + server application + client request/model (the precedent set by the checked "Magic and tech are functional" item); a React panel is not required.
- A dropped/out-of-scope decision must be recorded with a reason, and checked by a test, not merely asserted.
- Add no runtime dependency; `pnpm test`, `pnpm typecheck`, `pnpm lint`, `node scripts/check-roadmap.mjs` and `node scripts/check-report-sync.mjs` must pass.

## Review Focus

- A darts command must not let the client name its prize: the board comes from the server's seed and the shot is resolved server-side.
- `trade_resource` must use the content's prices and the server's trade counter, never a client-declared price or amount.
- A refused command must spend nothing, in both the native endpoint and the legacy shim.
- A client selector must tolerate a save with no feature keys at all (a fresh world before migration) and must never fabricate state.
- A screen recorded as "dropped" must have a real reason; the social decision must not silently hide a feature that is still wanted.

---

### Task 1: Record social services as out of scope

**Files:**
- Create: `docs/adr/0020-social-services-server-only.md`
- Modify: `docs/adr/README.md` (or regenerate with `node scripts/check-adrs.mjs --index`)
- Modify: `re/data/ui-screens.json`
- Modify: `packages/client/src/screens.test.ts`
- Modify: `docs/ROADMAP.md` (the "Alliances and the social features..." item)

**Interfaces:**
- Consumes: `alliance.ts`, `marketplace.ts`, `socialstore.ts`, `apps/server/src/social.ts` (all present); the screen-inventory schema in `screens.test.ts`.
- Produces: ADR 20; a checked decision for the alliance/marketplace screens; the G4 social item closed with a pointer.

- [ ] **Step 1: Write the failing test in `packages/client/src/screens.test.ts`**

Add an assertion that every screen under `popups/alliances/`, `popups/marketplace/` and the alliance-centre asset is either `dropped` or `planned`, and that any `dropped` one has a reason beginning `Dropped: `. Use the existing `SCREENS` fixture and the file's existing assertion style.

- [ ] **Step 2: Run it to verify it fails**

Run: `node --test packages/client/src/screens.test.ts`
Expected: FAIL — those screens are currently marked `implemented` with model notes, not dropped decisions.

- [ ] **Step 3: Write ADR 20**

Create `docs/adr/0020-social-services-server-only.md` with the four required sections (status, context, decision, alternatives, consequences per `check-adrs.mjs`). Decision: the server keeps the 11 alliance variants, the 17 error codes and the auction subsystem, and serves them over HTTP; the web client intentionally does not surface them because there is no Facebook identity, no real-money settlement and no live third-party service. The neighbour strip is the one social surface that remains. Regenerate the index.

- [ ] **Step 4: Change the screen decisions**

In `re/data/ui-screens.json`, set the alliance, marketplace, friends/gifts and premium purchase screens to `dropped` with `Dropped: ` reasons pointing at ADR 20, or leave `planned` where a future in-game UI is still promised. Recompute `counts.byDecision` from the file. Do not relabel a screen `implemented` unless a client model actually exists.

- [ ] **Step 5: Run the test to verify it passes**

Run: `node --test packages/client/src/screens.test.ts && node scripts/check-adrs.mjs && node scripts/check-report-sync.mjs`
Expected: PASS.

- [ ] **Step 6: Close the roadmap item**

Change the "Alliances and the social features are functional, or visibly out of scope" checkbox to `[x]`, naming ADR 20 and the checked test.

- [ ] **Step 7: Commit**

```bash
git add docs/adr re/data/ui-screens.json packages/client/src/screens.test.ts docs/ROADMAP.md
git commit -m "docs(g4): record social services as server-only and out of scope"
```

---

### Task 2: Server appliers for the priced-but-unapplied commands

**Files:**
- Modify: `packages/server/src/apply.ts`
- Test: `packages/server/src/apply.test.ts`

**Interfaces:**
- Consumes: `packages/rules/src/darts.ts`, `dartsboard.ts`, `market.ts`, `quest.ts`; `ApplierDeps`, `CommandOutcome`, `ShimWorld` from `apply.ts`.
- Produces: applier cases for `darts_shoot_balloon`, `darts_new_free`, `darts_reset`, `trade_resource` and `end_quest`, so a client command changes server state through the server's own rules.

- [ ] **Step 1: Write failing tests in `packages/server/src/apply.test.ts`**

For each command, assert the server-side effect and that a client-supplied claim is ignored:
  - `darts_shoot_balloon [targetIndex, wonExtra]`: the target is recorded as shot in `privateState.dartsBalloonsShot` and the client's `wonExtra` is not trusted for the prize.
  - `darts_new_free []`: `dartsHasFree`/`timeStampDartsNewFree` are reset by the server.
  - `darts_reset [seed]`: the board is derived from the server's seed, not accepted from a client-supplied board.
  - `trade_resource [resource, selling, amount]`: gold changes by the content price for that amount and the map's `numTradesDone` advances; an amount the content does not allow is refused and spends nothing.
  - `end_quest [questId, difficulty]`: refused when the server has no quest result, or granted only from server state — never from a client claim.

- [ ] **Step 2: Run them to verify they fail**

Run: `node --test packages/server/src/apply.test.ts`
Expected: FAIL — the commands currently fall through to `no-grant`.

- [ ] **Step 3: Implement the appliers**

Add cases in `createApplier`'s switch that call small pure helpers beside the existing ones in `apply.ts`. Use the existing `Random`/`hashSeed` pattern for the darts seed, the existing `market` rules for pricing, and the existing quest state keys (`QUEST_PROGRESS_KEY`). Every helper returns `{ applied, refused?, world }`; a refusal leaves the world's wallet untouched. Do not trust any client argument beyond a selection index or amount that the rules validate.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test packages/server/src/apply.test.ts && node --test packages/server/src/shim.test.ts`
Expected: PASS, and the shim still refunds a refused priced command.

- [ ] **Step 5: Commit**

```bash
git add packages/server/src/apply.ts packages/server/src/apply.test.ts
git commit -m "feat(f): apply darts, trade and quest commands server-side"
```

---

### Task 3: Client request builders and state selectors

**Files:**
- Modify: `packages/client/src/requests.ts`
- Modify: `packages/client/src/requests.test.ts`
- Create: `packages/client/src/featurestate.ts`
- Create: `packages/client/src/featurestate.test.ts`
- Modify: `packages/client/src/index.ts`

**Interfaces:**
- Consumes: the command table in `packages/protocol/src/commands.ts`; `WorldSnapshot` in `session.ts`; the server state keys named in `protocol/src/index.ts` and `server/src/migrate.ts`.
- Produces: `claimFreeDarts()`, `resetDarts(seed)`, `shootBalloon(targetIndex, wonExtra)`, `buyOfferPack(packId, itemIds)`, `buyPremium(packageIndex)`, `premiumUpgrade(...)`, `collectMission(nextChapterId)`, `buyResources(...)`, `exchangeCash()`; and `dartsState`, `marketState`, `premiumState`, `bonusState`, `questState`.

- [ ] **Step 1: Write failing tests**

In `requests.test.ts`, add each new builder to the `BUILDERS` table and assert its exact `args` against the command table. In `featurestate.test.ts`, assert each selector returns the server's values for a populated save and `null`/empty defaults for a save with none of the keys, and that it never invents a board or a prize.

- [ ] **Step 2: Run them to verify they fail**

Run: `node --test packages/client/src/requests.test.ts packages/client/src/featurestate.test.ts`
Expected: FAIL — the builders and the module do not exist.

- [ ] **Step 3: Implement the builders and selectors**

Add thin builders in `requests.ts` using the existing `command()` helper; add `featurestate.ts` mirroring `state.ts`'s `recordOrNull` style, reading only the keys named in the Interfaces block. Export from `index.ts`.

- [ ] **Step 4: Run them to verify they pass**

Run: `node --test packages/client/src/requests.test.ts packages/client/src/featurestate.test.ts && node scripts/verify-command-catalogue.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/client/src
git commit -m "feat(g): add feature request builders and server-state selectors"
```

---

### Task 4: Make the drawn goal gesture send a command

**Files:**
- Modify: `apps/client/src/ui/goals.tsx`
- Modify: `apps/client/src/ui/state.ts`
- Modify: `apps/client/src/ui/root.tsx`
- Modify: `apps/client/src/ui/mount.tsx`
- Modify: `apps/client/src/main.ts`
- Test: `apps/client/src/ui/state.test.ts`

**Interfaces:**
- Consumes: `completeGoal(goalId)` from `requests.ts`; `goalList()` from `ui/state.ts`; the `onCommand` plumbing already used by `run()` in `main.ts`.
- Produces: a goal title click that sends `complete_goal` instead of only hiding a badge.

- [ ] **Step 1: Write a failing test in `apps/client/src/ui/state.test.ts`**

Assert that the goal entry exposed to the UI carries the command the click should send, and that clicking a goal whose completion the server has not approved cannot send anything.

- [ ] **Step 2: Run it to verify it fails**

Run: `node --test apps/client/src/ui/state.test.ts`
Expected: FAIL — the entry has no command.

- [ ] **Step 3: Implement the wiring**

Add an `onCommand` prop to `Goals` and thread it through `root.tsx` → `mount.tsx` → `main.ts`. The click sends `completeGoal(goal.id)`; the server decides whether the goal is actually complete. Keep the badge-suppression behaviour.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm --filter @swl/app-client build && node --test apps/client/src/ui/state.test.ts`
Expected: PASS; the client still builds for the browser.

- [ ] **Step 5: Commit**

```bash
git add apps/client/src
git commit -m "feat(g): send complete_goal from the goal panel"
```

---

### Task 5: Close the G4 feature-parity item

**Files:**
- Modify: `docs/ROADMAP.md`
- Modify: `docs/superpowers/plans/2026-11-20-g4-feature-parity.md` (mark tasks done)

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: the "Quests, goals, the darts minigame, the marketplace, premium and the weekly bonus are functional" item closed with pointers to the appliers, builders and selectors that make each one real.

- [ ] **Step 1: Verify every sub-feature has all three layers**

For each of quests, goals, darts, market, premium and the weekly bonus, name the rules module, the server applier and the client builder/selector. If any layer is missing, add the smallest honest piece rather than ticking the box.

- [ ] **Step 2: Close the checkbox with evidence**

Change the G4 item to `[x]`, listing what was added and naming the tests. Leave the blocker register's art/GPU/device rows untouched — they are separate outcomes.

- [ ] **Step 3: Run the whole gate**

Run: `pnpm test && pnpm typecheck && pnpm lint && node scripts/check-roadmap.mjs && node scripts/check-report-sync.mjs`
Expected: PASS, 0 failures.

- [ ] **Step 4: Commit and finish the branch per `finishing-a-development-branch`**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): close G4 feature parity with evidence"
```
