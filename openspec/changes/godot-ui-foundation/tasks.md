# Tasks

## 1. UI foundation scaffold

- [x] 1.1 Implement `apps/client-godot/scripts/ui_foundation.gd` per design D1–D6: `extends CanvasLayer` with committed state (`UI_LAYER_INDEX` constant with the node's own `layer` set from it at creation and always in agreement, empty slot registry at creation), fail-closed `register_slot(slot_name) -> {ok, error}` rejecting the empty name (`slot_empty_name`) and a duplicate name (`slot_already_registered`) with the registry untouched, a successful registration appending a full-rect visible `Control` container with pointer pass-through (`mouse_filter` `IGNORE`) in registration order, fail-closed `set_slot_visible(slot_name, visible) -> {ok, error}` rejecting an unknown slot (`slot_not_registered`) and an unchanged value (`slot_visibility_unchanged`) with committed visibility untouched, change-only `slot_registered(slot_name)` / `slot_visibility_changed(slot_name, visible)` signals emitted exactly once per committed change and silent otherwise, and getters (`has_slot`, `slot_root`, `slot_names`, `is_slot_visible`) reflecting only committed state — the file contains no legacy-protocol or transport reference (covered by the project-scope scan of every allow-listed file: the scope `FORBIDDEN` and `RESTRICTED` lists own those tokens) and no wall-clock/time-service, persistence, content-loading, or other-script/autoload reference (direct source-contract scan of `res://scripts/ui_foundation.gd` inside its own suite, 16 tokens).
- [x] 1.2 Update the `apps/client-godot/project.godot` header comment to record the UI foundation as a non-autoload foundation component and retire the "only game system still deferred to its own change" line — the `[autoload]` set stays exactly the four existing lines and no scene is added or changed.
- [x] 1.3 Add `apps/client-godot/tests/test_ui_foundation.gd` with the scaffold and visibility scenarios (empty start with layer-index agreement and no notification; registration appending in order with a full-rect visible pass-through container and exactly one notification; empty and duplicate registrations rejected with named errors, registry unchanged, silent; hide/show flipping exactly with one change-only notification per change; unknown-slot and unchanged-value rejections with state unchanged, silent; direct source-contract token scan) — verified `godot --headless --path apps/client-godot -s res://tests/test_ui_foundation.gd` exits 0 with `[test] PASS checks=84`.

## 2. Suite wiring

- [x] 2.1 Add `test_ui_foundation` to `apps/client-godot/verify-boot.ps1`'s hermetic suite list and header prose (eighth suite; the loop's endpoint argument is ignored by this suite) — verified `powershell -File apps/client-godot/verify-boot.ps1` exits 0 and records the suite (`test_ui_foundation exits 0`, `test_ui_foundation reports PASS` in `boot-report.json` with 52 assertions, `pass=true`, failures 0).

## 3. Scope contract

- [x] 3.1 Update `apps/client-godot/tests/test_project_scope.gd` per design D8: `ALLOWED` += `scripts/ui_foundation.gd` and `tests/test_ui_foundation.gd` (41 → 43), `EXPECTED_AUTOLOADS` and `EXPECTED_SCENES` unchanged (four autoloads, two scenes), `FORBIDDEN` drops `"UiFoundation"` with the count assertion 14 → 13, and the doc comments describe the UI-foundation boundary — verified the suite exits 0 with `[test] PASS checks=591` headless (43 project files, 34 scanned sources) while still asserting every remaining forbidden token.

## 4. Documentation

- [x] 4.1 Update `AGENTS.md`'s verification-command prose to the actually executed eight-suite `verify-boot.ps1` wording (package loader, scene build, fake GameApi, boot scene, session, game clock, camera controls, UI foundation) — every documented command line matches a command executed green in group 5.
- [x] 4.2 Update `apps/client-godot/README.md` with the UI foundation suite's purpose, invocation, and observed check count, the `verify-boot.ps1` eight-suite narrative, and the updated project-scope count — recorded counts equal the `[test] PASS checks=N` lines observed in the final battery (UI foundation 84, project scope 591), and the provisional slot structure is labeled as such with the later parity binding noted.

## 5. Verification and records

- [x] 5.1 Full battery in the final state, all exit 0: `powershell -File apps/client-godot/verify.ps1` (observed `[test] PASS` counts: loader 123, scene-build 36, project-scope 591, content-registry 52, asset-ids 50; compare PASS; self-test DETECTED); `powershell -File apps/client-godot/verify-boot.ps1` (guard verify embedded pre/post with digests equal `6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348`; observed hermetic counts: package loader 123, scene build 36, fake GameApi 29, boot scene 32, session 67, game clock 110, camera controls 128, UI foundation 84; `boot-report.json` 52 assertions, `pass=true`, failures 0); `git diff --check` (0); `openspec validate godot-ui-foundation --strict` (exit 0); `openspec validate --all --strict` (all passed, 0 failed). First-render evidence byte-identical (`git status` shows no first-render or guarded-byte change — only the regenerated `boot-report.json`).
- [x] 5.2 Scenario → executed-check mapping (below); every code row (1–8, 11–12) names a check that actually ran, and rows 9–10 record the docs and ledger work (row 9 reviewed with this change, row 10 executed at archive).
- [ ] 5.3 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): the UI foundation delivered with evidence pointers, the M5 items that remain, and the change lifecycle state — executed at archive stage (see ledger).

### 5.2 Scenario → executed-check mapping

Rows 1–10 are the scenarios of the `godot-ui-foundation` delta; rows 11–12 are
the scenarios of the modified `first-render-in-godot` R1. Commands: G = `godot
--headless --path apps/client-godot -s res://tests/test_ui_foundation.gd`,
V = `verify.ps1`, VB = `verify-boot.ps1`.

| # | Scenario | Executed check | Run |
|---|---|---|---|
| 1 | Start with an empty registry | `test_ui_foundation` empty-start checks: empty slot list, layer equals `UI_LAYER_INDEX`, no notification | G |
| 2 | Register a slot | registration succeeds, slot appended last with a full-rect visible pass-through container, exactly one `slot_registered` payload | G |
| 3 | Reject an invalid registration | empty and duplicate registrations rejected (`slot_empty_name` / `slot_already_registered`), registry unchanged, silent | G |
| 4 | Hide and show a registered slot | hide then show: each succeeds, committed visibility flips exactly, one change-only notification per change | G |
| 5 | Reject an unknown slot | unknown-slot write rejected (`slot_not_registered`), registry and visibilities unchanged, silent | G |
| 6 | Reject an unchanged value | unchanged-value request rejected (`slot_visibility_unchanged`), committed visibility unchanged, silent | G |
| 7 | Scope enforces the new boundary | `test_project_scope`: 43-file inventory, exactly four autoloads, two scenes, 13 forbidden tokens over the scanned sources | V |
| 8 | Keep prior verifications green | `verify.ps1` + `verify-boot.ps1` exit 0; guard pre=post; committed first-render report/PNG byte-identical (guard baseline + `git status`, plus the verify assertions) | V, VB |
| 9 | Record the executed commands | `AGENTS.md` eight-suite prose; `README.md` suite purpose, invocation, observed counts | — (docs review) |
| 10 | Record the milestone progress | roadmap `Project Status` ledger entry (task 5.3, archive stage) | — (ledger) |
| 11 | (R1) Boot with the pinned engine | `test_project_scope` pinned-engine check (`find("4.7")`) + `test_boot_scene` ready-marker assertion (`contains("4.7.2")`) + boot-report `main-scene boot reported engine 4.7.2` + VB main-scene live phase | V, VB |
| 12 | (R1) Remain within the verification scope | `test_project_scope`: allow-list, four autoloads, no system outside the allow-list, no legacy protocol token, first-render scene and tests intact | V |

Disclosures: every specified branch is executed directly — both registration
rejections, all three visibility branches (change, unknown, unchanged), and
every getter's committed-state read. The source-scan early return on an
unreadable file is a test harness failure guard, not specified behavior.
