# Tasks

## 1. Clock scaffold

- [ ] 1.1 Implement `apps/client-godot/scripts/game_clock.gd` per design D1–D5: unanchored and running at startup with a zero epoch, `anchor(server_time) -> {ok, error}` with fail-closed validation (positive timestamp, unanchored), `clear()` returning to unanchored with zero elapsed, independent `pause()` / `resume()` / `advance(msec)` controls with fail-closed advance (positive count, paused), getters reflecting only committed state (`is_anchored`, `is_paused`, `server_time`, `elapsed_msec`, `now_epoch_sec`), and `clock_anchored` / `clock_cleared` / `clock_paused_changed` / `clock_ticked` signals with the specified emission rules — verify the file contains no forbidden token (camera, UI foundation, legacy protocol, transport) and reads no wall clock by the scope scan once registered.
- [ ] 1.2 Register the `GameClock` autoload in `apps/client-godot/project.godot` (fourth line, after `Session`) and update the `[autoload]` header comment to the four-autoload boundary.
- [ ] 1.3 Add `apps/client-godot/tests/test_game_clock.gd` with the scaffold and notification scenarios (no implicit anchor at startup; anchor-once success with getter/signal assertions; invalid anchors rejected with state unchanged; pause freezes across frames and resume continues with exactly one notification each; advance exact and fail-closed for zero/negative/while-running; clear semantics including the silent repeated clear; tick payloads equal the elapsed time and never regress within a base) — verify `godot --headless --path apps/client-godot -s res://tests/test_game_clock.gd` exits 0 with `[test] PASS`.

## 2. Boot integration

- [ ] 2.1 Modify `apps/client-godot/scripts/boot.gd` per design D6: guard the `GameClock` autoload (`gameclock_missing`), clear any previous anchor on `_boot()` entry, anchor with `save_list.server_time` immediately before `Session.activate`, and fail closed with `gameclock_anchor` if anchoring unexpectedly fails — extend `tests/test_game_clock.gd` with the boot-integration pair (successful fake boot anchors the clock to the fixture epoch with one `clock_anchored`; a failing follow-up attempt clears the previous anchor on entry and leaves the clock unanchored) using the fake implementation and a loopback endpoint with nothing listening — verify the suite exits 0 with `[test] PASS` headless.
- [ ] 2.2 Extend `apps/client-godot/tests/test_boot_scene.gd` with clock assertions: at ready the clock is anchored and its epoch is at or ahead of the fixture response timestamp within a bounded post-anchor interval; in both the `unreachable` and `api-error` scenarios the clock is unanchored with a zero epoch — verify the hermetic fake run exits 0 with `[test] PASS` headless and the assertions also execute under `verify-boot.ps1`'s failure phases.
- [ ] 2.3 Add `test_game_clock` to `apps/client-godot/verify-boot.ps1`'s hermetic suite list and any report wiring the boot report needs for the sixth suite — verify `powershell -File apps/client-godot/verify-boot.ps1` exits 0 and records the suite.

## 3. Scope contract

- [ ] 3.1 Update `apps/client-godot/tests/test_project_scope.gd` per design D9: `ALLOWED` += `scripts/game_clock.gd` and `tests/test_game_clock.gd`, `EXPECTED_AUTOLOADS` = exactly the four autoload lines in project order, `FORBIDDEN` drops `"GameClock"` with the count assertion 17 → 16, and the doc comments describe the four-autoload boundary — verify `tests/test_project_scope.gd` exits 0 with `[test] PASS checks=<observed>` headless while still asserting every remaining forbidden token.

## 4. Documentation

- [ ] 4.1 Update `AGENTS.md`'s verification-command prose to the actually executed six-suite `verify-boot.ps1` wording (package loader, scene build, fake GameApi, boot scene, session, game clock) — verify each documented command line matches a command executed green in group 5.
- [ ] 4.2 Update `apps/client-godot/README.md` with the game-clock suite's purpose, invocation, and observed check count, and the `verify-boot.ps1` suite list — verify the recorded counts equal the `[test] PASS checks=N` lines observed in the final battery.

## 5. Verification and records

- [ ] 5.1 Run the full battery in the final state and record commands with exit codes: `powershell -File apps/client-godot/verify.ps1`, `powershell -File apps/client-godot/verify-boot.ps1`, the Compatibility API guard verify before and after, `git diff --check`, and `openspec validate godot-game-clock --strict` plus `openspec validate --all --strict` — verify all exit 0 and the committed first-render evidence is byte-identical (`git status` clean before/after).
- [ ] 5.2 Append the scenario → executed-check mapping table for all scenarios of the `godot-game-clock` delta plus the scenarios of the modified R1 into `tasks.md`, marking each row with the command or assertion that actually ran and disclosing any gap — verify every row names a check executed in group 5 (or group 1–3 suites re-run there).
- [ ] 5.3 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): the GameClock scaffold delivered with evidence pointers, the M5 items that remain, and the change lifecycle state — verify the ledger text matches the committed evidence paths and PR chain (executed at archive stage).
