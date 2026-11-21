# Expansion Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing `expand` command actually work — server-authoritative, correctly priced from owned-tile count, with a player-facing control and restart-safe state.

**Architecture:** Keep the 94-command catalogue. Remove the wrong upfront charge (`args[0]` is a tile id, not an owned ordinal) and charge inside a new applier from `map.expansions.length` and the content price table. Reuse the existing `expand()` builder, one Dialog/Feedback, and the native `/api/command` path.

**Tech Stack:** TypeScript, Node's built-in test runner, React DOM, CDP e2e.

**Spec:** `docs/ROADMAP.md` Group F/E and `docs/GOAL.md` (autonomous execution); `re/docs/03-commands-quests-economy.md` §expansion; vendored `config/main.json` `expansion_prices`.

## Global Constraints

- Server authoritative: price from server-owned owned-tile count and content; never from a client-declared price or type.
- 94-command catalogue unchanged; `expand` args stay `[tileId]`; legacy 3-arg form still accepted by the shim but ignored for price.
- Idempotent/replay-safe; a duplicate tile refused without state change; wallet restored on every refusal.
- No new runtime dependency, no upstream runtime access, no proprietary art; one Dialog; no weakened check.
- Do not claim neighbour (`neighbors`) or inventory (`inventory_qte`) gates — their inputs are not server-owned here; record them as deferred.
- Roadmap accounting stays 401; G5.2's deferred-expansion record preserved; any new outcome recorded honestly.

## Review Focus

- A client cannot choose the price or the owned ordinal.
- A replayed expansion cannot charge twice or append a duplicate tile.
- An unaffordable expansion changes nothing, in both native and legacy paths.
- A fresh save has the documented four owned tiles; an older save without `expansions` defaults safely.
- The UI shows the server-derived price and the server's refusal reason.

---

### Task 1: Authoritative expansion application

**Files:** `packages/rules/src/commandcost.ts`, `packages/server/src/apply.ts`, `apps/server/src/main.ts`, `packages/server/src/starttown.ts`, tests.

- [ ] Step 1: failing tests in `apply.test.ts` for: first purchase after four owned tiles charges 2500g+5c from content; owned count derived server-side; tile id not already owned; invalid tile id and ordinal overflow refused; unaffordable refused with unchanged wallet; replay/duplicate refused; missing `expansions` defaults to `[]`; persisted world still payable. Update `commandcost.test.ts` to assert no upfront charge.
- [ ] Step 2: run focused tests, confirm RED.
- [ ] Step 3: make `case 'expand'` in `commandcost.ts` return `NO_COST` (keep `PRICED_COMMANDS`); add `expandCommand` + `case 'expand'` in `apply.ts` with `ApplierDeps.expansionPrices`; wire `bundle.expansionPrices` in `main.ts`; seed `expansions: [35,36,45,46]` in `starttown.ts`.
- [ ] Step 4: run focused tests, `pnpm test`, typecheck, lint, catalogue, cheat battery.
- [ ] Step 5: commit `feat: apply expansion purchases authoritatively`.

### Task 2: Player-facing expansion UI and verification

**Files:** `packages/client/src/session.ts`, `featurestate.ts`, new UI panel, `apps/client/src/main.ts`, `scripts/e2e-test.mjs`, tests.

- [ ] Step 1: failing tests for an owned-expansion view from the server map; a price view from content at the server-owned ordinal; a control that emits `expand(tileId)` via `onCommand`.
- [ ] Step 2: confirm RED.
- [ ] Step 3: add typed `expansions` to `WorldSnapshot`, a pure selector, a small panel reusing the shared Dialog/Feedback, and the `ClientHandle.expand` hook for e2e.
- [ ] Step 4: run focused tests, `pnpm test`, typecheck, lint, client build, and the real Chrome+Edge e2e with a new expansion assertion that preserves all existing assertions.
- [ ] Step 5: commit `feat(g): expose expansion purchases in the interface`.

### Task 3: Documentation and gates

**Files:** `docs/ROADMAP.md`, `re/data/ui-screens.json`, maybe `docs/DEVELOPING.md`.

- [ ] Step 1: run every GOAL §7 gate and record exact results.
- [ ] Step 2: record the verified outcome and the deferred neighbour/inventory gates outside Group headers, preserving 401; mark only genuinely implemented screens with real model paths.
- [ ] Step 3: commit `docs(roadmap): record the authoritative expansion feature`.
