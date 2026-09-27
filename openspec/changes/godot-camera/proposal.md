# Proposal

## Why

Roadmap M5 (Godot Foundation) delivers the Godot project, GameApi, LegacyV0Api, ContentRegistry, Session, GameClock, **camera**, and basic UI foundation; the first four are delivered and archived, and the roadmap ledger names camera as the next eligible objective. `first-render-in-godot` requirement R1 still lists "camera controls" among the systems that SHALL remain absent until its own change adds it, so the project cannot host any camera code before this change. Later scheduled work needs the component: the M6 town vertical slice renders a real legacy town and its task list starts camera pan and zoom before terrain (roadmap §24 "Implement town camera — `feat: add town camera pan and zoom`"). An evidence search is recorded: `config/main.json` contains no camera/zoom/pan key, the save corpus and fixtures contain no camera field, and the asset-registry SWF inspection contains no camera symbol — so no legacy camera behavior has been captured yet, and this change delivers the bounded, explicitly provisional M5 camera foundation rather than an unevidenced parity claim.

## What Changes

- New camera controls (`apps/client-godot/scripts/camera_controls.gd`): a `Camera2D`-based component, deliberately **not** an autoload (AGENTS.md limits autoloads to cross-cutting services; the camera belongs to the scene that shows the world, and no world exists yet). Committed view state = world position plus discrete zoom levels 0–2 over the fixed factor table `1.0 / 2.0 / 4.0` with the node's own zoom kept in sync; fail-closed `{ok, error}` envelopes for `zoom_in()` / `zoom_out()` (bound errors) and `pan_by(world_delta)` (zero vector and non-finite components rejected); change-only `camera_panned(world_delta)` / `camera_zoomed(zoom_level)` signals; and a public `handle_input(event) -> bool` pointer mapping — wheel zooms a level, a left drag pans so the grabbed content follows the cursor (screen movement divided by the committed zoom factor), everything else passes through — with the node's `_unhandled_input` delegating to it. No wall-clock/time-service reads, no transport, no persistence, no content loading, no dependency on any other script or autoload.
- New headless suite `tests/test_camera_controls.gd`, the seventh hermetic suite in `verify-boot.ps1` (pure component: no API, no boot flow, ignores the loop's endpoint argument).
- `project.godot` header comment records the component; the autoload set (four) and the scene set (two) stay unchanged — no `.tscn` is added, the component is script-only and will be instanced by the M6 town scene.
- Project scope grows: `test_project_scope.gd` allow-lists the two new files (39 → 41) and drops the `Camera2D` / `Camera3D` forbidden tokens (16 → 14); UI foundation, legacy protocol, and non-loopback transport remain forbidden.
- `first-render-in-godot` requirement R1 MODIFIED: camera controls joins the allow-listed foundation work; the absent list narrows to UI foundation alone.
- Docs: `AGENTS.md` and the client README describe the actually executed seven-suite battery with observed counts; the roadmap Project Status ledger records the delivery at archive.

## Non-Goals

- No legacy-parity camera claim: authentic town camera behavior (bounds, zoom range, input feel) binds at the M6 town slice, where it will be captured with behavioral evidence first.
- No town bounds (roadmap task 25, M6), no keyboard or edge scrolling, no smoothing/inertia, no zoom-to-fit or minimap, no selection interaction.
- No boot integration — the boot scene has no world to look at; nothing instances the component in this change.
- No UI foundation, Settings, or AudioManager work; no Compatibility API, GameApi, Session, ContentRegistry, or GameClock behavior change.
