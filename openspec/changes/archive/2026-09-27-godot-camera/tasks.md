# Tasks

## 1. Camera scaffold

- [x] 1.1 Implement `apps/client-godot/scripts/camera_controls.gd` per design D1–D7: `extends Camera2D` with committed view state (default world position at creation, `zoom_level` 0–2 over `ZOOM_FACTORS = [1.0, 2.0, 4.0]`, `zoom_factor()` getter, node `zoom` kept equal to `Vector2(factor, factor)` on every committed change), fail-closed `zoom_in()` / `zoom_out()` returning `{ok, error}` with `zoom_maximum_reached` / `zoom_minimum_reached` leaving state untouched, fail-closed `pan_by(world_delta) -> {ok, error}` rejecting the zero vector (`pan_zero_delta`) and non-finite components (`pan_invalid_delta`) with the position untouched, `camera_panned(world_delta)` / `camera_zoomed(zoom_level)` signals emitted exactly once per successful change and silent otherwise, the public `handle_input(event) -> bool` consumption rules (wheel zoom, left-press drag start, motion-while-dragging pan by `-relative / zoom_factor()`, drag release, pass-through otherwise), and `_unhandled_input` delegating to it — the file contains no legacy-protocol or transport reference (covered by the project-scope scan of every allow-listed file: the scope `FORBIDDEN` and `RESTRICTED` lists own those tokens) and no wall-clock/time-service, persistence, content-loading, or other-script/autoload reference (direct source-contract scan of `res://scripts/camera_controls.gd` inside its own suite, 16 tokens).
- [x] 1.2 Update the `apps/client-godot/project.godot` header comment to record camera controls as a non-autoload foundation component — the `[autoload]` set stays exactly the four existing lines and no scene is added or changed.
- [x] 1.3 Add `apps/client-godot/tests/test_camera_controls.gd` with the scaffold and pointer scenarios (default view at creation; zoom-in/out across the table with both bound rejections leaving state unchanged; two cumulative pans committing exactly; zero/NaN/infinite pans rejected with state unchanged; change-only signal payloads for every success and silence for rejections and no-op motions; wheel up/down consumption with bound silence; content-follows-cursor drag at zoom levels 0 and 1 with release ending the drag; right-button, idle-motion, and key events passing through; `_unhandled_input` delegation observed through behavior) — verified `godot --headless --path apps/client-godot -s res://tests/test_camera_controls.gd` exits 0 with `[test] PASS checks=128`.

## 2. Suite wiring

- [x] 2.1 Add `test_camera_controls` to `apps/client-godot/verify-boot.ps1`'s hermetic suite list and header (seventh suite; the loop's endpoint argument is ignored by this suite) — verified `powershell -File apps/client-godot/verify-boot.ps1` exits 0 and records the suite (`test_camera_controls exits 0`, `test_camera_controls reports PASS` in `boot-report.json`, 50 assertions with `pass=true`).

## 3. Scope contract

- [x] 3.1 Update `apps/client-godot/tests/test_project_scope.gd` per design D9: `ALLOWED` += `scripts/camera_controls.gd` and `tests/test_camera_controls.gd` (39 → 41), `EXPECTED_AUTOLOADS` and `EXPECTED_SCENES` unchanged (four autoloads, two scenes), `FORBIDDEN` drops `"Camera2D"` and `"Camera3D"` with the count assertion 16 → 14, and the doc comments describe the camera-controls boundary — verified the suite exits 0 with `[test] PASS checks=589` headless (41 project files, 32 scanned sources) while still asserting every remaining forbidden token.

## 4. Documentation

- [x] 4.1 Update `AGENTS.md`'s verification-command prose to the actually executed seven-suite `verify-boot.ps1` wording (package loader, scene build, fake GameApi, boot scene, session, game clock, camera controls) — every documented command line matches a command executed green in group 5.
- [x] 4.2 Update `apps/client-godot/README.md` with the camera suite's purpose, invocation, and observed check count (128), the `verify-boot.ps1` seven-suite narrative, and the updated project-scope count (589) — recorded counts equal the `[test] PASS checks=N` lines observed in the final battery, and the provisional zoom values are labeled as such with the M6 parity binding noted.

## 5. Verification and records

- [x] 5.1 Full battery in the final state, all exit 0: `powershell -File apps/client-godot/verify.ps1`; `powershell -File apps/client-godot/verify-boot.ps1` (guard verify embedded pre/post, digests equal `6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348`); `git diff --check` (0); `openspec validate godot-camera --strict` (exit 0); `openspec validate --all --strict` (32 passed, 0 failed). Observed counts: loader 123, scene-build 36, project-scope 589, content-registry 52, asset-ids 50, game-api-fake 29, boot-scene 32/19/18, session 67, game clock 110, camera controls 128; `boot-report.json` 50 assertions, `pass=true`, first-render evidence byte-identical (`git status` shows no first-render or guarded-byte change).
- [x] 5.2 Scenario → executed-check mapping (below); every code row (1–12, 15–16) names a check that actually ran, and rows 13–14 record the docs and ledger work (row 13 reviewed with this change, row 14 executed at archive).
- [ ] 5.3 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): the camera controls delivered with evidence pointers, the M5 items that remain, and the change lifecycle state — executed at archive stage (see ledger).

### 5.2 Scenario → executed-check mapping

Rows 1–14 are the scenarios of the `godot-camera` delta; rows 15–16 are the
scenarios of the modified `first-render-in-godot` R1. Commands: G = `godot
--headless --path apps/client-godot -s res://tests/test_camera_controls.gd`,
V = `verify.ps1`, VB = `verify-boot.ps1`.

| # | Scenario | Executed check | Run |
|---|---|---|---|
| 1 | Start at the default view | `test_camera_controls` default-view check: position, zoom level 0, factor 1.0, node zoom (1,1) | G |
| 2 | Zoom one level at a time, fail closed at the bounds | zoom walk to level 2 and back to 0 with both bound rejections (`zoom_maximum_reached` / `zoom_minimum_reached`), state unchanged, silent | G |
| 3 | Pan by a world delta | two cumulative `pan_by` calls committing exactly the requested deltas | G |
| 4 | Reject an invalid pan | zero vector / NaN / infinite components rejected with named errors, position unchanged, silent | G |
| 5 | Notify only on successful change | per-success signal payloads equal to the committed change, rejections and no-op motions emit nothing | G |
| 6 | Wheel zooms one level per notch | wheel-up/down through `handle_input`: consumed, level 0→1→0, factor and node zoom synced, one notification each | G |
| 7 | Wheel at a level bound is consumed and silent | wheel-up at level 2 and wheel-down at level 0: consumed, state unchanged, no notification | G |
| 8 | A drag pans the content under the cursor | press/motion/release: −100 world px at level 0 and −50 at level 1 for a 100 px drag, release ends the drag, later motion unconsumed | G |
| 9 | Unrelated events pass through | right press, idle motion, key event each return `false` with state unchanged | G |
| 10 | The node delegates input to the public handler | `_unhandled_input(wheel_up)` invoked in the tree advances the level | G |
| 11 | Scope enforces the new boundary | `test_project_scope`: 41-file inventory, exactly four autoloads, two scenes, 14 forbidden tokens over 32 sources (`checks=589`) | V |
| 12 | Keep prior verifications green | `verify.ps1` + `verify-boot.ps1` exit 0; guard pre=post `6978b959…`; committed first-render report/PNG byte-identical (guard baseline + `git status`, plus the verify assertions) | V, VB |
| 13 | Record the executed commands | `AGENTS.md` seven-suite prose; `README.md` suite purpose, invocation, observed counts | — (docs review) |
| 14 | Record the milestone progress | roadmap `Project Status` ledger entry (task 5.3, archive stage) | — (ledger) |
| 15 | (R1) Boot with the pinned engine | `test_project_scope` pinned-engine check (`find("4.7")`) + `test_boot_scene` ready-marker assertion (`contains("4.7.2")`) + boot-report `main-scene boot reported engine 4.7.2` + VB main-scene live phase | V, VB |
| 16 | (R1) Remain within the verification scope | `test_project_scope` (`checks=589`): allow-list, four autoloads, no UI/legacy/transport tokens, first-render scene and tests intact | V |

Disclosures: every specified branch is executed directly — both zoom-bound
rejections, all three pan rejections, every `handle_input` branch (wheel at
both bounds, press/motion/zero-motion/release, release without a drag,
right/idle/key/wheel-release pass-through), and the `_unhandled_input`
delegation. The source-scan early return on an unreadable file is a test
harness failure guard, not specified behavior.

### Verification record (2026-09-27)

Independent verifier subagent verdict: **PASS, 0 CRITICAL, 5 WARNINGs, 7 NOTEs**.

- W1 (spec scenarios 2/7 claim position unchanged, but
  `_assert_zoom_unchanged` asserted only level/factor/node zoom) →
  repaired: the helper takes an expected position and all four
  bound-rejection sites pass `Vector2.ZERO`; suite re-run green
  (`checks=128`, +4).
- W2 (a left release with no active drag had no check) → repaired: added
  to `_check_passthrough` (+1).
- W3 (task 1.1 attributed transport/legacy-protocol coverage to the
  suite's own scan) → repaired: reworded to the project-scope scan, which
  owns those tokens for every allow-listed file.
- W4 (design D9 risk claimed "both scenes are asserted unchanged"; only
  the scene *set* is asserted) → repaired: the risk sentence now states
  set equality over the two allow-listed paths, that this change edits no
  `.tscn`, and that per-scene contents remain governed by the scene-build
  suite's structural assertions.
- W5 (task 5.2 claimed every row names a check that ran; rows 13–14 are
  records work) → repaired: qualified to the code rows (1–12, 15–16) with
  rows 13–14 named as docs/ledger records, row 14 deferred to archive.
- NOTEs: N1 wheel-down sync now also asserts factor and node zoom (+2);
  N2 mapping row 15 cites the exact checks (`find("4.7")`,
  `contains("4.7.2")`, the boot-report engine line); N3 the suite's
  source-contract scan extended from 13 to 16 tokens
  (`OS.get_unix_time`, `DirAccess`, `ResourceSaver`, +3); N4 design D2
  wording now names the proposal/design/tasks/README plus the spec
  Purpose as the provisional framing; N5 the proposal's M5 delivered set
  corrected to "all except camera and UI foundation"; N7 mapping row 12
  attribution corrected (guard baseline + `git status`, plus verify
  assertions). N6 (spec-boundary audit) clean: only
  `first-render-in-godot` R1 required the MODIFIED delta and the
  verifier confirmed the precedent that per-change containment clauses in
  older living specs are historical records of their own boundary.
- Repairs re-verified in the final state: `test_camera_controls`
  `checks=128`, `test_project_scope` `checks=589` (41 files, 32
  sources); full battery re-run green (`verify.ps1` and `verify-boot.ps1`
  exit 0, guard pre=post `6978b959…`, `boot-report.json` 50 assertions
  `pass=true` with the camera suite recorded); `git diff --check` 0;
  `openspec validate godot-camera --strict` exit 0; `openspec validate
  --all --strict` 32/32.
