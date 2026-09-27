# Tasks

## 1. Session scaffold

- [x] 1.1 Implement `apps/client-godot/scripts/session.gd` per design D1–D5: inactive at startup, `activate(user_id, summary) -> {ok, error}` with the fail-closed validation set (non-empty id, non-null summary, summary names the same id), `clear()` returning to inactive, getters reflecting only committed state, and `session_activated` / `session_cleared` signals with the specified emission rules — verify the file contains no forbidden token (GameClock, camera, legacy protocol, transport) by the scope scan once registered.
- [x] 1.2 Register the `Session` autoload in `apps/client-godot/project.godot` (third line, after `ContentRegistry`) and add `apps/client-godot/tests/test_session.gd` with the four scaffold scenarios (no implicit session at startup, successful activation with getter/signal assertions, invalid activation rejected with state unchanged, clear semantics including the silent repeated clear) — verify `godot --headless --path apps/client-godot -s res://tests/test_session.gd` exits 0 with `[test] PASS`.

## 2. Boot integration

- [x] 2.1 Modify `apps/client-godot/scripts/boot.gd` per design D6: clear the session on `_boot()` entry, activate it with `boot_user_id` + `summary` immediately before `_complete()`, and fail closed with `session_activate` if activation unexpectedly fails — extend `tests/test_session.gd` with the three boot-integration scenarios (session active at ready with fixture equality; failed boot leaves no session; a failing follow-up attempt replaces a previously active session) using the fake implementation and a loopback endpoint with nothing listening — verify the suite exits 0 with `[test] PASS` headless.
- [x] 2.2 Extend `apps/client-godot/tests/test_boot_scene.gd` with session assertions: at ready the session is active, names the bootstrapped save, and its summary equals the fixture save; in both the `unreachable` and `api-error` scenarios the session is inactive — verify the hermetic fake run exits 0 with `[test] PASS` headless and the assertions also execute under `verify-boot.ps1`'s failure phases.
- [x] 2.3 Add `test_session` to `apps/client-godot/verify-boot.ps1`'s hermetic suite list and any report wiring the boot report needs for the fifth suite — verify `powershell -File apps/client-godot/verify-boot.ps1` exits 0 and records the suite.

## 3. Scope contract

- [x] 3.1 Update `apps/client-godot/tests/test_project_scope.gd` per design D8: `ALLOWED` += `scripts/session.gd` and `tests/test_session.gd`, `EXPECTED_AUTOLOADS` = exactly the three autoload lines in project order, `FORBIDDEN` drops `"Session"` with the count assertion 18 → 17, and the doc comments describe the three-autoload boundary — verify `tests/test_project_scope.gd` exits 0 with `[test] PASS checks=<observed>` headless while still asserting every remaining forbidden token.

## 4. Documentation

- [ ] 4.1 Update `AGENTS.md`'s verification-command prose to the actually executed five-suite `verify-boot.ps1` wording (package loader, scene build, fake GameApi, boot scene, session) — verify each documented command line matches a command executed green in group 5.
- [ ] 4.2 Update `apps/client-godot/README.md` with the session suite's purpose, invocation, and observed check count, and the `verify-boot.ps1` suite list — verify the recorded counts equal the `[test] PASS checks=N` lines observed in the final battery.

## 5. Verification and records

- [ ] 5.1 Run the full battery in the final state and record commands with exit codes: `powershell -File apps/client-godot/verify.ps1`, `powershell -File apps/client-godot/verify-boot.ps1`, the Compatibility API guard verify before and after, `git diff --check`, and `openspec validate godot-session --strict` plus `openspec validate --all --strict` — verify all exit 0 and the committed first-render evidence is byte-identical (`git status` clean before/after).
- [ ] 5.2 Append the scenario → executed-check mapping table for all scenarios of the `godot-session` delta plus the scenarios of the modified R1 into `tasks.md`, marking each row with the command or assertion that actually ran and disclosing any gap — verify every row names a check executed in group 5 (or group 1–3 suites re-run there).
- [ ] 5.3 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): the Session scaffold delivered with evidence pointers, the M5 items that remain, and the change lifecycle state — verify the ledger text matches the committed evidence paths and PR chain (executed at archive stage).
