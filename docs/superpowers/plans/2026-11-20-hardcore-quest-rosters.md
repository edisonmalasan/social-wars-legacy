# Hardcore Quest Rosters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the eight hardcore quest rosters at build time into the content bundle and load them in the authoritative applier so those quests resolve from validated kill events.

**Architecture:** The content pipeline already reads `upstream/socialwarriors/config` at build time; extend it to read `villages/quest/<id>.json` map snapshots, filter unit-typed items into `item:<isoId>` refs, and emit a `questRosters` bundle field. The applier merges an extracted roster into `questRoster()` for empty-element quests; the rules engine is unchanged.

**Tech Stack:** TypeScript, Node's built-in test runner, pnpm workspaces.

**Spec:** `re/docs/01-network-protocol.md` §3.5 (item tuple shape) and the recorded per-quest counts: HC1 79 units, HC2 122, HC3 114, HC4 45, HC5 84, HC6 153, HC9 138, HC10 46.

## Global Constraints

- `upstream/` is read-only and never a **runtime** dependency; build-time extraction into the content bundle is the established pattern.
- No new commands; catalogue stays 94/94/94. The client cannot send an item id or a win flag; it sends only validated refs.
- The zero-event guard and loss refusal remain. A hardcore quest pays only after its roster's units are reported killed.
- The content build stays reproducible: `buildId` is the SHA-256 of the canonical bundle, so extraction must be deterministic.
- No runtime dependency; pnpm test, typecheck, lint, build:content, check-roadmap, check-report-sync and verify-command-catalogue must pass.

## Review Focus

- All eight rosters extracted with the exact unit counts; refs are `item:<isoId>` and unique.
- `player` field cannot identify enemies in these snapshots (all are 1); filter by content item `type === 'u'` only.
- An off-roster ref is refused; a zero-event hardcore `end_quest` remains refused (no vacuous win).
- A full roster of validated kills pays exactly once; a partial roster does not.
- Extraction is deterministic and does not change the other bundle counts.

---

### Task 1: Build-time roster extraction

**Files:** `packages/content/src/build.ts`, `packages/content/src/schema.ts`, `packages/content/src/build.test.ts`

- [ ] **Step 1: Write failing tests** asserting `questRosters` has eight entries keyed by quest id, the unit counts above, unique `item:<isoId>` refs, and a stable `buildId` across two builds.
- [ ] **Step 2:** Run `pnpm --filter content test` and confirm RED.
- [ ] **Step 3:** Add a `QUEST_DIR` constant and an extraction helper that reads `upstream/socialwarriors/villages/quest/<id>.json`, filters `maps[0].items` by content `type === 'u'`, and emits `{ questId, items: [{ ref, itemId, subcatFunctional }] }`. Add `questRosters` to `ContentBundle` and assign it in `buildContent()`. Do not touch `KNOWN_SECTIONS`.
- [ ] **Step 4:** Run the content tests, `pnpm build:content` and a second build to confirm GREEN and an unchanged build id.
- [ ] **Step 5:** Commit `feat(content): extract hardcore quest rosters at build time`.

### Task 2: Applier and server wiring

**Files:** `packages/server/src/apply.ts`, `apps/server/src/main.ts`, `packages/server/src/apply.test.ts`

- [ ] **Step 1: Write failing tests** for one hardcore quest: a full set of roster kills makes `end_quest` pay exactly once; a partial roster is refused; an off-roster ref is refused; zero events remain refused.
- [ ] **Step 2:** Run focused tests and confirm RED.
- [ ] **Step 3:** Add `questRosters` to `ApplierDeps`; merge extracted entries into `questRoster()` when the spec's `elements` is empty; pass `bundle.questRosters` from `main.ts`.
- [ ] **Step 4:** Run focused tests plus shim tests and confirm GREEN.
- [ ] **Step 5:** Run the whole gate including `node scripts/verify-command-catalogue.mjs` before committing.
- [ ] **Step 6:** Commit `feat(f): load hardcore quest rosters from the content bundle`.

### Task 3: Honest roadmap disposition

**Files:** `docs/ROADMAP.md`

- [ ] **Step 1:** Record that the eight hardcore quests now resolve from build-time-extracted rosters; state what remains (convoy `trucksArrived`, special ops/save villages/spy2 counters, and the client per-kill request builder, which needs a 2-arg-first design decision).
- [ ] **Step 2:** Add an amendment-log entry. Do not tick the G4 quest item unless every remaining sub-feature is supported.
- [ ] **Step 3:** Run the whole gate and commit `docs(roadmap): record hardcore roster resolution`.
