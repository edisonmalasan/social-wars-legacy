# Visual Fidelity Recovery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the original Social Wars presentation — a green isometric town with
integrated chrome — inside the existing TypeScript/PixiJS/React client and authoritative
server, without changing gameplay, commands, rules or the Tauri architecture.

**Architecture:** Three disjoint ownership lanes: (1) world/renderer ground layer,
(2) game-chrome theme and tutorial presentation, (3) at-rest visibility and bottom
navigation state. Each lane lands as its own PR with rendered-screenshot evidence; the
orchestrator merges in that order. The desktop shell needs no UI work — it wraps the same
built client.

**Tech Stack:** TypeScript 5.9, PixiJS v8 (WebGL2), React DOM, Tauri v2, Node 26,
pnpm workspaces, headless Chrome + CDP for screenshots.

**Spec:** [`../GOAL.md`](../GOAL.md), [`AGENTS.md`](../../AGENTS.md), ADR 19/20/21.

**Status:** Phase 0 complete and approved by the owner on 2026-11-24. Phase 1 is authorised.

---

## Global Constraints

- Keep the 94-command catalogue and strict two-argument `set_quest_var`.
- Server-authoritative outcomes; deterministic, pure rules engine; no client-owned save.
- Never edit `upstream/` or the read-only reference at `C:\Users\Edison\Desktop\socialwarriors`.
- No Flash, SWF runtime, proprietary sprite/audio/font in any shipped or CI artifact.
- No new content migration, no mass asset generation, no new command types.
- Do not edit `main` directly; one branch/PR per task; four required CI checks must pass.
- No weakening of licensing, no-Flash, report-sync or roadmap checks.
- Baseline for rollback: `a3b203cf015e213d49bf98f1513a70a5a4f2d95c`.

---

## Review Focus

- **At-rest fresh player:** only HUD, neighbour strip, build control and (if unfinished)
  tutorial are visible; storage/store/missions/build list never appear unasked.
- **World visibility:** green ground covers ≥60% of the 760×600 stage; at least the starting
  building is visible; `window.__swl.drawnSprites() ≥ 3`.
- **Bottom navigation:** neighbour strip and build menu rects do not intersect at rest.
- **Tutorial:** white bubble, blue bold title, tail, reachable Next/Skip; step gating still
  comes from the server's saved progress.
- **Click-through:** `document.elementFromPoint(380,300)` returns the canvas when no overlay
  is active, so world interactions remain reachable.

---

## 1. Phase 0 audit findings

### 1.1 Method and evidence

- Three isolated read-only worktree workers on `opencode/hy4-flash-free` high audited
  (a) client UI/renderer, (b) Tauri desktop/sidecar, (c) original reference/docs/licensing.
- The modern client was rendered for real in headless Chrome with a fresh server-owned
  player (`phase0-audit`) at 760×600 via CDP. Artifacts (local temp, not tracked):
  `baseline-760x600.png` (cover), `baseline-game-760x600.png` (in-game),
  `world-only-760x600.png` (overlays stripped), `world-swiftshader.png`.
- Rendered probe: `status: started: original art mode - 1 sprites (CC0-1.0)`,
  `art: original`, `visible: 1`, `drawn: 1`, WebGL2 live, canvas and stage both 760×600.
  Stripping every overlay still left a flat dark canvas — the world is genuinely empty,
  not merely covered.

### 1.2 Reference map

| Region | Reference A (original) | Reference B (rendered baseline) |
|---|---|---|
| Session header | "Welcome Warrior! Level 1 (Log Out)", from `play.html:14-18` | absent |
| Game bar | olive `rgb(97,104,7)`, selected `rgb(233,221,81)`, `play.html:21-81` | dark slate HUD at y≈0-8% |
| Resource HUD | gold/olive resource strip across the top, inside SWF | tiny uppercase labels, top 5% |
| World | green isometric field (`bgcolor="#669C2C"`, `play.html:86`), building + foliage | `#10131a`, 1 sprite, no ground |
| Tutorial | white speech bubble, blue "WELCOME, SOLDIER!", character at right, NEXT | dark text panel, arrow/ring, no character |
| Bottom nav | neighbour cards + BUILD/WORLD controls, bottom of stage | build list covers neighbours, same corner |
| Panels | contextual, single priority-ordered modal (`re/docs/14:105-113`) | ~20 panels mounted at once, z 12→40 |

### 1.3 Confirmed defects

| ID | Defect | Source |
|---|---|---|
| D1 | No ground/terrain layer. `buildScene()` iterates only `world.maps[0].items`; renderer draws only those sprites; clear colour `#10131a`. | `apps/client/src/scene.ts:92-99`, `renderer.ts:161,255` |
| D2 | Dark-slate theme (`#131a24`, `#1d2430`, `#000a`) instead of olive/gold. | `apps/client/src/ui/css.ts:19-30,90` |
| D3 | ~20 panels mounted unconditionally with fixed absolute positions and z 12→40. | `apps/client/src/ui/root.tsx:401-449`, `css.ts:33-41` |
| D4 | Neighbour strip and build menu both `left:8px; bottom:8px`; build menu paints over neighbours. | `css.ts:1216,1257` |
| D5 | Dialog backdrop `inset:0`, `#000a`, z 40 blacks out the world. | `css.ts:1439` |
| D6 | Tutorial is a dark text panel; no bubble silhouette, no character. | `ui/tutorial.tsx:63,109-132`, `css.ts:1375` |
| D7 | Base font 13px, readouts 10px; `font-scale.json` generated but untracked, so metrics vary by environment. | `css.ts:39,142` |
| D8 | E2E closes the tutorial first and checks only hud/goals/inventory/chapters; no screenshot harness. | `scripts/e2e-test.mjs:666-720`, `e2e-mobile-layout.mjs:427-519` |
| D9 | Desktop: no `SWL_DATA_DIR` passed to sidecar (no save survives restart); `--port` changes probe URL but not server bind; startup errors invisible in windowed build; Windows bundling manual, not CI. | `apps/desktop/src-tauri/src/lib.rs:134-174`, `scripts/build-desktop-server.mjs:113-122` |

### 1.4 What already exists (do not rebuild)

760×600 stage with whole-number scaling; HUD; 33-step tutorial with server-owned progress;
neighbour strip; build menu with original category order; one priority dialog; chapters,
goals, store, inventory, quest and combat panels; 94 commands; deterministic rules; Tauri
shell with loopback server, health wait and sidecar build. Inventory: 170 implemented /
52 dropped / 38 planned screens — the 38 are gated by missing contracts, not by art.

### 1.5 Desktop feasibility (static, no runtime claim)

Already coherent in code: 760×600 centred window, self-contained sidecar build, loopback
binding, `/health` readiness polling, kill-on-exit, placeholder/no-Flash gates. Gaps for
Phase 3: persistence directory (D9a), `--port` propagation (D9b), visible startup errors
(D9c), informational Windows bundling job (D9d), and a real human launch test. No
desktop-specific UI change is needed: ADR 6 makes the web client the only presentation.

### 1.6 Constraints and decisions

ADR 19 (pure online): desktop starts a local authoritative server; no browser-side save.
ADR 20 (social services server-only): the neighbour strip stays; do not revive social popups.
ADR 21 (clean-room CC0): shipped art stays CC0 with provenance; private read-only comparison
of original material is allowed, copying it into tracked/distributable builds is not.

Owner decisions for Phase 1 (approved 2026-11-24): Approach B; canonical 760×600 stage;
tutorial character deferred to Phase 4; olive bar's social tabs omitted/inert.

---

## 2. Visual acceptance criteria (measurable, 760×600)

- `#game` canvas and `#stage` bounding rect exactly **760×600**, scale 1 on a 760×600 window.
- Stage pixel at (10,300) is green (≈`#669C2C`: G > R×1.4, G > B×1.6); ≥60% of stage pixels
  are ground, not `#10131a`.
- At rest no UI element besides HUD intersects y∈[0,44]; `document.elementFromPoint(380,300)`
  returns the canvas when the tutorial is closed.
- Neighbour strip and build-control rects do not intersect at rest; build menu opens only
  on request.
- Exactly one overlay active at rest (tutorial if unfinished, else none).
- `window.__swl.visibleSprites() ≥ 3` and `drawnSprites() ≥ 3` for a fresh town; zero
  `/atlases/` requests; zero console/page errors.
- Tutorial bubble near-white, blue bold title, visible tail, Next/Skip inside the stage.
- Five reviewed screenshot checkpoints: (a) initial town, (b) tutorial, (c) build open,
  (d) quest dialog, (e) desktop window. Baselines are explicit and never auto-overwritten.

---

## 3. Task decomposition

Each task is independently testable and lands as its own PR. Lanes own disjoint files.

### Task 1 — Ground layer and green world (lane: world)

**Files:**
- Modify: `apps/client/src/scene.ts` (add ground sprite generation from server map state)
- Modify: `apps/client/src/renderer.ts:158-169,255` (clear colour + ground draw pass)
- Test: `apps/client/src/scene.test.ts`, `apps/client/src/ground.test.ts` (new)

**Interfaces:**
- Consumes: `SceneItem`, `Viewport`, `STAGE_WIDTH/HEIGHT`, `tileToPixel()` from `scene.ts`;
  `world.maps[0]` size from `WorldSnapshot`.
- Produces: `buildGround(viewport: Viewport): SceneSprite[]` — deterministic diamond tiles
  covering the stage in the original green palette; `GROUND_COLOUR` export.

- [ ] **Step 1: Write the failing test** in `apps/client/src/ground.test.ts` asserting
  `buildGround(viewport)` returns ≥100 sprites, all with distinct `(x,y)` inside the stage,
  and that `GROUND_COLOUR` has G > R×1.4 and G > B×1.6.
- [ ] **Step 2:** Run `node --test apps/client/src/ground.test.ts`; expect FAIL (module missing).
- [ ] **Step 3:** Implement `buildGround()` using the existing `tileToPixel()` projection and
  a CC0 solid-colour texture generated in code (no file asset, no fetch). Change the Pixi
  background to `GROUND_COLOUR` and draw ground before item sprites.
- [ ] **Step 4:** Run `node --test apps/client/src/ground.test.ts` and
  `node --test apps/client/src/scene.test.ts`; expect PASS.
- [ ] **Step 5:** Render the 760×600 baseline with the CDP harness; confirm green ≥60% and
  `drawnSprites() ≥ 3`; attach the screenshot to the PR.
- [ ] **Step 6:** Commit: `git commit -m "feat(client): draw green isometric ground"`.

### Task 2 — Olive/gold game chrome and tutorial bubble (lane: chrome)

**Files:**
- Modify: `apps/client/src/ui/css.ts` (tokens, HUD, bubble, panel surfaces)
- Modify: `apps/client/src/ui/tutorial.tsx` (bubble markup/tail, keep step logic)
- Test: `apps/client/src/ui/chrome.test.ts`, `apps/client/src/ui/tutorial.test.ts`

**Interfaces:**
- Consumes: `--swl-font-body`, existing `TutorialOverlay` props and `tutorial-steps.json`.
- Produces: `--swl-game-*`, `--swl-ochre`, `--swl-olive`, `--swl-bubble` CSS tokens;
  unchanged `TutorialOverlay` props and server-driven step gating.

- [ ] **Step 1:** Write failing tests asserting the new token values and a `.swl-tutorial-bubble`
  rule with white fill and a tail pseudo-element; keep existing tutorial tests unchanged.
- [ ] **Step 2:** Run the two test files; expect FAIL.
- [ ] **Step 3:** Add the tokens and apply them to HUD, nav and at-rest chrome; restyle the
  tutorial box into a bubble. Do not change layout geometry, z-order or component props.
- [ ] **Step 4:** Run both test files and `pnpm typecheck`; expect PASS.
- [ ] **Step 5:** Render checkpoint (b) tutorial and (a) town; confirm bubble/title/tail and
  no clipping; attach both screenshots.
- [ ] **Step 6:** Commit: `git commit -m "feat(ui): restore olive/gold chrome and tutorial bubble"`.

### Task 3 — One active surface and corrected bottom nav (lane: state)

**Files:**
- Modify: `apps/client/src/ui/root.tsx` (gate non-essential panels on a single focus state)
- Modify: `apps/client/src/main.ts` (focus state, bottom-nav toggle wiring)
- Modify: `apps/client/src/ui/css.ts` only by adding `.swl-focus-hidden` (no token edits —
  chrome lane owns the rest of that file)
- Test: `apps/client/src/ui/root.test.ts`, `scripts/e2e-test.mjs` additions

**Interfaces:**
- Consumes: existing `DialogState`, `onboarding`, `storeView`, `neighbours` props.
- Produces: `type ActiveSurface = 'none' | 'build' | 'store' | 'inventory' | ...` and
  `setActiveSurface` passed to `Root`; at most one non-null surface at a time.

- [ ] **Step 1:** Write failing tests: at rest, `Root` renders HUD/neighbours/build control and
  no storage/store/missions/build-list; opening build renders the build list and hides neighbours.
- [ ] **Step 2:** Run them; expect FAIL.
- [ ] **Step 3:** Add the focus state and gate panels; move build control to bottom-right and
  keep neighbours bottom-left; keep the dialog stack unchanged for priority.
- [ ] **Step 4:** Run unit tests plus `node scripts/e2e-test.mjs`; expect PASS with no new
  overlap; `document.elementFromPoint(380,300)` returns the canvas at rest.
- [ ] **Step 5:** Render checkpoints (c) build open and (d) quest dialog; attach screenshots.
- [ ] **Step 6:** Commit: `git commit -m "fix(ui): one active surface and non-overlapping bottom nav"`.

### Task 4 — Screenshot regression harness (lane: test)

**Files:**
- Create: `scripts/capture-ui.mjs` — reusable CDP capture of the five checkpoints at 760×600
  from a fresh dev player; writes reviewed baselines under `test/baselines/ui/`.
- Modify: `scripts/e2e-test.mjs` to assert green coverage, at-rest visible-surface count,
  neighbour/build non-intersection and canvas click-through.

**Interfaces:**
- Consumes: `window.__swl.drawnSprites()`, `#stage`, `GET /health`.
- Produces: `node scripts/capture-ui.mjs` with exit 0 and five PNGs; baseline diff command.

- [ ] **Step 1:** Write the harness first; run it against the current build and confirm it
  fails the new visual assertions (red/green ratio, at-rest surface count).
- [ ] **Step 2:** Implement capture + assertions; store reviewed baselines explicitly.
- [ ] **Step 3:** Run the harness and `pnpm test`; expect PASS. Baselines are never
  overwritten automatically.
- [ ] **Step 4:** Commit: `git commit -m "test(ui): add 760x600 visual checkpoint harness"`.

### Task 5 — Phase 3 private desktop gaps (after Phase 1 accepted; separate plan)

Shell-only: pass `SWL_DATA_DIR` to the sidecar from a user-data directory; propagate `--port`
to the spawned server; surface startup/certificate errors in-window; add an informational
Windows bundling job; then a human launch/uninstall test producing logs and an artifact path.
No UI change, no Flash, no client-owned save. Signed/notarised artifacts and auto-update stay
externally blocked and are not claimed.

### Task 6 — Optional Phase 4 art fidelity (separate approval)

Compare atlas mode and CC0 motifs read-only, show visual samples, obtain a rights decision.
No proprietary media in tracked or distributable builds; no mass generation.

---

## 4. Dependency order and rollback

1. Task 1 → rendered green world (highest visual impact, independent of UI lanes).
2. Task 2 → chrome/tutorial theme on top of the green world.
3. Task 3 → at-rest visibility and bottom nav.
4. Task 4 → screenshot harness guards the whole slice.
5. Owner visually approves Phase 1 before Phase 2/3 work starts.
6. Rollback: revert one merge; baseline `a3b203c`; never reset `main`.
