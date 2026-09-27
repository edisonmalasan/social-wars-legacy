# Design

## Context

The M5 foundation so far: `GameApi` (typed calls over `LegacyV0Api` or `FakeApi`), the Compatibility API v0 on loopback, the boot scene as main scene, the `ContentRegistry`, `Session`, and `GameClock` autoloads — all delivered and archived. Roadmap M5 lists `camera` next (then basic UI foundation), and `first-render-in-godot` R1 currently forbids camera controls in the project until its own change adds it. Constraints: no new dependencies, loopback-only, pinned engine/interpreter, guard-verified read-only inputs — see proposal.md for motivation and the `godot-camera` delta for the behavior contract. An evidence search (config keys, save corpus, fixtures, SWF inspection symbols) found no legacy camera behavior to reproduce, which shapes D2.

## Goals / Non-Goals

**Goals:**
- One reusable camera-controls component with explicit committed view state (world position + discrete zoom level), fail-closed control envelopes, change-only signals, and a public input handler — the piece the M6 town scene will instance.
- Deterministic, hermetic proof of the component in its own suite; the existing scope test enforces the grown boundary.
- A clean spec boundary: R1 remains the single living allow-list clause and moves camera controls from the absent list to the allow-listed work.

**Non-Goals:**
- No legacy-parity camera behavior (bounds, ranges, feel) — no evidence exists, and capturing it belongs to the M6 town slice before any parity claim.
- No town bounds, keyboard/edge scroll, smoothing, inertia, zoom-to-fit, selection, or minimap.
- No boot/scene integration (no world yet), no autoload changes, no API/compatibility changes, no UI foundation or Settings/AudioManager work.

## Decisions

**D1 — A `Camera2D` scene-node component, not an autoload.** `scripts/camera_controls.gd` extends `Camera2D`; it is script-only (no new scene file) and instantiated where a world exists — the M6 town scene. *Rationale:* AGENTS.md limits autoloads to cross-cutting services (`GameApi`, `Session`, `ContentRegistry`, `GameClock`, `Settings`, `AudioManager`); a camera is view state owned by the scene that renders the world, and boot has nothing to frame. Consequence: this is the first M5 change that does not grow the autoload set (stays exactly four) or the scene set (stays exactly two). *Alternatives:* fifth autoload (rejected — camera is not cross-cutting and would be dead at startup), a `.tscn` scene file (rejected — nothing would place it, and it would grow the scene contract for no runtime benefit; the town change can wrap the script if editor placement is wanted).

**D2 — Explicitly provisional contract; no legacy claim.** The proposal records the negative evidence search (no camera key in `config/main.json`, no camera field in saves/fixtures, no camera symbol in the SWF inspection). The component therefore specifies a neutral, testable foundation — zoom factors `1.0 / 2.0 / 4.0`, world-space panning with no bounds — and the proposal, design, tasks, and client README mark these values provisional while the spec's Purpose explicitly disclaims legacy-parity camera behavior. *Rationale:* preservation-first rules forbid inventing legacy behavior; M6 captures authentic camera evidence before binding parity. The roadmap keeps camera in M6 as well ("pan camera, zoom camera", "camera works"), which is where that binding happens.

**D3 — Fail-closed `{ok, error}` control envelopes.** `zoom_in()` / `zoom_out()` fail with `zoom_maximum_reached` / `zoom_minimum_reached` at the table extremes; `pan_by()` fails with `pan_zero_delta` for the zero vector and `pan_invalid_delta` for non-finite components; every failure leaves committed state untouched and is silent. *Rationale:* mirrors `ContentRegistry.load_content()` / `Session.activate()` / `GameClock.anchor()` so callers handle failure uniformly; rejection silence matches the house notification discipline. *Alternative:* silent clamping at zoom bounds (rejected — callers could not distinguish "zoomed to the edge" from "zoomed by one", and the fail-closed envelope is this project's established pattern).

**D4 — Discrete integer zoom levels over a fixed factor table.** `zoom_level: int` in 0..2 indexes `ZOOM_FACTORS = [1.0, 2.0, 4.0]`; `zoom_factor()` returns the table value; `Camera2D.zoom` is set to `Vector2(f, f)` on every committed change; start is level 0 (factor 1.0, the `Camera2D` default). *Rationale:* integer states make every assertion exact (no float-epsilons, no accumulation drift), and integer factors keep raster town art texel-aligned when M6 renders it. The two-way state (`zoom_level` + node `zoom`) is asserted to stay in sync, so getters reflect only committed state.

**D5 — World-space pan; screen drag converted by the inverse zoom.** `pan_by(world_delta)` commits `position += world_delta` with no bounds (town bounds are roadmap task 25, M6). A drag motion computes `world_delta = -event.relative / zoom_factor()`: dividing by the zoom keeps the content under the cursor glued to it (a 100 px drag moves content exactly 100 px on screen at any level), and the sign makes the grabbed content follow the cursor. *Rationale:* the mapping is the classic "grab the map" transform and is asserted exactly at two zoom levels.

**D6 — Two change-only signals.** `camera_panned(world_delta)` once per successful nonzero pan with the committed delta as payload; `camera_zoomed(zoom_level)` once per committed level change with the new level as payload. Rejected requests, no-op motions (zero relative while dragging), and wheel events at a bound are silent. *Rationale:* the house transition/advance discipline (`clock_anchored`, `session_activated`) lets later systems (HUD, minimap) subscribe without polling.

**D7 — Public `handle_input(event) -> bool` is the tested contract; `_unhandled_input` delegates.** Consumption: wheel-up/down always consumed (a camera gesture, silent at a bound); left press begins and consumes a drag; motion while dragging is consumed (panning only when `relative` is nonzero); left release ends and consumes the drag; everything else returns `false` (future selection/UI keeps its events). The suite calls `handle_input` directly for deterministic state assertions and proves the `_unhandled_input` delegation behaviorally by invoking it with a wheel event and observing the level change. *Alternative:* synthesizing OS input through `Input.parse_input_event` (rejected — display-driver dependent and flaky headless; the delegation is one line, but the behavioral proof still exercises it).

**D8 — Seventh hermetic suite in `verify-boot.ps1`; no boot integration.** `tests/test_camera_controls.gd` needs no API, no service, and no boot flow; it joins the hermetic loop (which passes the endpoint argument that this suite ignores), growing that list from six to seven and `boot-report.json` by the suite's two assertions. It does not join `verify.ps1`, which remains the render/content battery. *Rationale:* `godot-session` D7 / `godot-game-clock` D7 established that bootstrap-domain suites live in `verify-boot.ps1`; the camera is a client component verified alongside them, and boot-scene assertions are untouched because nothing in the boot flow changes.

**D9 — Scope contract growth and spec-boundary ownership.** `test_project_scope.gd`: `ALLOWED` += `scripts/camera_controls.gd`, `tests/test_camera_controls.gd` (39 → 41); `EXPECTED_AUTOLOADS` unchanged at the four lines; `EXPECTED_SCENES` unchanged at `boot.tscn` + `first_render.tscn`; `FORBIDDEN` drops `"Camera2D"` and `"Camera3D"` together (count assertion 16 → 14) — both tokens retire because the camera-controls system now exists in the project (same precedent as the `GameClock` token drop: the token stops marking a deferred system, and the file inventory bounds where camera code can live), while `UiFoundation`, the legacy-protocol tokens, and the non-loopback transport tokens remain. Spec boundary: `first-render-in-godot` R1 is the single living allow-list statement and is MODIFIED here (camera controls joins the allow-listed work; absent list becomes UI foundation alone); the per-change containment requirements of earlier capabilities record their own change's boundary and remain historical, as established by `godot-session` and `godot-game-clock` before it.

## Risks / Trade-offs

- [`Camera2D`/`Camera3D` retirement weakens the forbidden list] → the remaining 14 tokens still exclude every not-yet-built system (`UiFoundation`) and all legacy/transport primitives; the `ALLOWED` inventory still bounds where camera code can live (only `scripts/camera_controls.gd` and its suite); the scene set is enforced by set equality over the two allow-listed paths with no `.tscn` added or edited by this change; per-scene contents remain governed by the scene-build suite's structural assertions, so the residual risk of a camera node inside an existing scene is bounded by this change's diff rather than by a dedicated scene-content scan.
- [Provisional zoom factors mistaken for parity] → proposal, design, spec, and README all label the values provisional and bind authentic ranges to the M6 town slice; no scenario claims legacy behavior.
- [Component delivered but unused at M5] → deliberate and disclosed: no world exists; the suite is the executable proof, and M6 instances the component into the town scene; the M5 exit criterion ("Client boots and communicates with Compatibility API") does not depend on it.
- [Input tested without the OS input system] → `handle_input` is the public contract and `_unhandled_input` is proved by direct behavioral invocation; the one-line delegation is exercised, not assumed.
- [Boot-report/evidence churn] → regenerated by the verification run and committed as `test:` with provenance noted; first-render evidence and all guarded bytes stay byte-identical (they are not inputs to this change).

## Migration Plan

Additive only — no state to migrate, no rollback beyond removing the two allow-listed files, restoring the two forbidden tokens, and reverting the doc prose. No OpenSpec-unspecified behavior changes.

## Open Questions

None.
