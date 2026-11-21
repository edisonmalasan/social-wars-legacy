# Phone-Ready Shared Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the already-tested responsive stage model actually drive the running client at phone viewports, add touch-safe input/CSS, scaffold (without building) the Capacitor shell config, and prove it with emulated-phone CDP verification.

**Architecture:** One shared web client (ADR 6) — no second renderer and no platform-specific screen. `packages/client/src/stage.ts` remains the single layout model; the app feeds it the real viewport and applies its scale to the existing 760×600 stage. Touch conveniences stay in the shared client/CSS.

**Tech Stack:** TypeScript, React DOM, PixiJS v8, Node test runner, CDP emulation harness.

**Spec:** `docs/GOAL.md` (autonomous roadmap), `docs/ROADMAP.md` Group G5, ADR 6/ADR 19.

## Global Constraints

- No real-device or Android/iOS build claim: no SDK/device/emulator on this host, so the three device-dependent G5 boxes stay open.
- No second renderer, no platform-specific screen, no new runtime dependency, no proprietary art.
- The internal stage stays 760×600; scale is capped at 1 and whole where possible; `stage.ts` remains the source of truth.
- Keep the existing pointer path working; touch handling must not decide game outcomes.
- 401-item roadmap accounting unchanged; any new outcome recorded outside `## Group X` headers.
- All applicable GOAL §7 gates pass before any completion claim.

## Review Focus

- The computed transform scale at a phone viewport must equal the stage model's answer.
- Panels must stay inside the stage and not overlap; content must scroll, not clip.
- Touch input must not fire duplicate commands or break mouse input.
- Emulation results must be labelled as emulation, never as device verification.
- No false roadmap tick.

---

### Task 1: Viewport-driven stage scaling

**Files:** `apps/client/src/main.ts`, `apps/client/index.html`, `apps/client/src/ui/css.ts`, `packages/client/src/stage.ts` + tests.

- [ ] Step 1: failing tests for phone viewports (390×844 @dpr2, 360×640 landscape 640×360) asserting the stage model's scale/portrait/tooSmall and that the app passes the real viewport (not fixed clientWidth) to the fit path.
- [ ] Step 2: confirm RED.
- [ ] Step 3: feed `window.innerWidth/innerHeight` (or a tested wrapper) into the fit calculation; make the stage element scale from the model rather than the fixed 760 clientWidth; preserve whole-number/capped scale.
- [ ] Step 4: focused tests, `pnpm test`, typecheck, lint, client build.
- [ ] Step 5: commit `feat(g): drive stage scaling from the real viewport`.

### Task 2: Touch-safe shared client and Capacitor config scaffold

**Files:** `apps/client/index.html`, `css.ts`, `renderer.ts`, `apps/mobile/` (new config only), tests.

- [ ] Step 1: failing tests for any pure touch helper (dedupe/gesture guard) if introduced; verify no duplicate command from a touch.
- [ ] Step 2: implement `touch-action: none` on the canvas, double-tap/pinch suppression, scrollable panels, and a `apps/mobile/capacitor.config.ts` + `package.json` + README documenting exact prerequisites/commands. Do NOT `cap add`, generate native projects, or build Android/iOS.
- [ ] Step 3: run focused tests, full gate, client build.
- [ ] Step 4: commit `feat(g): add touch-safe input and Capacitor config scaffold`.

### Task 3: Emulated-phone CDP verification and documentation

**Files:** `scripts/e2e-mobile-layout.mjs` (new), `docs/ROADMAP.md`, tests.

- [ ] Step 1: write a CDP script using the existing `Page.send` harness with `Emulation.setDeviceMetricsOverride` and `setTouchEmulationEnabled`: assert status started, transform scale equals the stage model, panels inside bounds/no overlap, visible sprites, and a touch `pointerdown` selection. Report browsers run vs not run; never claim device verification.
- [ ] Step 2: run all GOAL §7 gates plus the new script; record exact results.
- [ ] Step 3: record partial G5 progress in the roadmap outside Group headers, keep 401 accounting, keep device boxes open, preserve G5.1/G5.2/expansion history.
- [ ] Step 4: commit `docs(roadmap): record phone-ready client work`.
