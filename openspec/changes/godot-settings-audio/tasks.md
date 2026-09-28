# Tasks

## 1. Settings and AudioManager autoloads

- [ ] 1.1 Implement `apps/client-godot/scripts/settings.gd` per design D1–D4: `extends Node` with committed state (exactly `music_enabled` / `sfx_enabled`, both `true` at startup), typed getters, fail-closed `set_music_enabled(enabled)` / `set_sfx_enabled(enabled) -> {ok, error}` rejecting an unchanged value (`setting_unchanged`) with committed state untouched and no notification, change-only `setting_changed(key, value)` emitted exactly once per committed change and silent otherwise, and explicit `load(path := "user://settings.cfg")` / `save(path)` persistence over `ConfigFile` returning `storage_file_missing` (absent file), `storage_read_failed` (any other load failure, engine code in the message detail), `storage_invalid_contents` (missing known key, non-`boolean` value, or unknown key — strict two-key schema, nothing dropped or half-applied), or `storage_write_failed`, with a failed load leaving committed state and notifications untouched, a successful load committing both keys and notifying only per actually-changed key, and no automatic load or save anywhere — the file contains no legacy-protocol or transport reference (covered by the project-scope scan of every allow-listed file) and no wall-clock/time-service, raw-persistence, content-loading, or other-dependency reference except the sanctioned `ConfigFile` mechanism (direct source-contract scan of `res://scripts/settings.gd` inside its own suite, 17 tokens: the established list minus `ConfigFile` and `load(`, plus `ResourceLoader`, `AudioManager`, `AudioServer`).
- [ ] 1.2 Implement `apps/client-godot/scripts/audio_manager.gd` per design D1, D5, D6: `extends Node` whose `_ready` idempotently ensures `Music` and `SFX` buses under `Master` (name lookup first) and binds to `/root/Settings` via `get_node_or_null` (connect `setting_changed` + apply current preferences change-only; fail-soft operational when absent; one-directional), committed state mirroring `music_enabled` / `sfx_enabled` (`true` at startup), fail-closed `set_music_enabled` / `set_sfx_enabled -> {ok, error}` rejecting unchanged values (`music_setting_unchanged` / `sfx_setting_unchanged`) and missing buses (`music_bus_missing` / `sfx_bus_missing`) with committed state untouched and no notification, successful requests committing and applying as bus mute only (volume never written, stays 0 dB) with change-only `music_enabled_changed(enabled)` / `sfx_enabled_changed(enabled)` signals, getters reflecting only committed state, and no playback, clock, persistence, content-loading, transport, or legacy reference (direct source-contract scan of `res://scripts/audio_manager.gd`, the established 16 tokens).
- [ ] 1.3 Register both autoloads in `apps/client-godot/project.godot` after `GameClock` (`Settings` before `AudioManager`, so registration order guarantees Settings exists when AudioManager binds) and update the header comment to record them — the scene set stays exactly two, no `.tscn` is added, and `[audio] driver="Dummy"` stays exactly as committed.

## 2. Suites

- [ ] 2.1 Add `apps/client-godot/tests/test_settings.gd` covering: startup defaults with no notification, commit-once with the `setting_changed` payload, unchanged rejection with untouched state and silence, getters, a save/load round trip over a temp file under `res://.godot/`, `storage_file_missing` for an absent file, `storage_invalid_contents` for the three schema violations (missing key, non-`boolean` value, unknown key), `storage_read_failed` for corrupt contents wrapped in `Engine.print_error_messages = false` and restored in the same block (probe-confirmed engine `ERROR:` output would trip the `^ERROR:` scan), change-only emission across a load, `storage_write_failed` for a save into a missing directory, and the 17-token source-contract scan — verified `godot --headless --path apps/client-godot -s res://tests/test_settings.gd` exits 0 with `[test] PASS checks=N` (count observed at run).
- [ ] 2.2 Add `apps/client-godot/tests/test_audio_manager.gd` covering: both buses ensured at startup under `Master` with unmuted defaults and default getters, the live Settings → AudioManager binding (signal payload plus bus mute state), each setter's commit with one change-only notification, unchanged rejection with untouched bus and committed state, `*_bus_missing` rejection with the bus removed and restored inside the suite, the initial apply of an already-false preference at binding (change-only), the fail-soft absent-Settings branch (autoload temporarily removed and restored with both asserted), and the 16-token source-contract scan — verified `godot --headless --path apps/client-godot -s res://tests/test_audio_manager.gd` exits 0 with `[test] PASS checks=N` (count observed at run).

## 3. Suite wiring and scope contract

- [ ] 3.1 Add both suites to `apps/client-godot/verify-boot.ps1`'s hermetic suite list and header prose (ninth `test_settings`, tenth `test_audio_manager`; both ignore the loop's endpoint argument) — verified `powershell -File apps/client-godot/verify-boot.ps1` exits 0 and records both suites in `boot-report.json` (56 assertions expected, `pass=true`, failures 0).
- [ ] 3.2 Update `apps/client-godot/tests/test_project_scope.gd` per design D8: `ALLOWED` += the four new files (43 → 47), `EXPECTED_AUTOLOADS` += the `Settings` and `AudioManager` lines (4 → 6) with count/message assertions and header comment updated, `EXPECTED_SCENES` unchanged (two scenes), `FORBIDDEN` unchanged at 13 — verified the suite exits 0 with `[test] PASS checks=N` headless (count observed at run).

## 4. Documentation

- [ ] 4.1 Update `AGENTS.md`'s verification-command prose to the actually executed ten-suite `verify-boot.ps1` wording (package loader, scene build, fake GameApi, boot scene, session, game clock, camera controls, UI foundation, settings, audio manager) — every documented command line matches a command executed green in group 5.
- [ ] 4.2 Update `apps/client-godot/README.md` with both suites' purpose, invocation, and observed check counts, the `verify-boot.ps1` ten-suite narrative, the updated project-scope count, and the new envelopes/commands with the provisional (no legacy evidence) label — recorded counts equal the `[test] PASS checks=N` lines observed in the final battery.
- [x] 4.3 Add the `Settings` and `AudioManager` lines to the roadmap M5 Deliver block (`docs/DEVELOPMENT_ROADMAP.md`) — reconciliation of the milestone list with the historical M5 scope (`356cc83`) — executed in this proposal stage (verified: the block lists ten deliverables).

## 5. Verification and records

- [ ] 5.1 Full battery in the final state, all exit 0: `powershell -File apps/client-godot/verify.ps1` (render/content battery with observed counts recorded at run); `powershell -File apps/client-godot/verify-boot.ps1` (guard verify embedded pre/post with digests equal; all ten hermetic counts observed at run; `boot-report.json` 56 assertions, `pass=true`, failures 0); `git diff --check` (0); `openspec validate godot-settings-audio --type change --strict` (exit 0); `openspec validate --all --strict` (all passed, 0 failed). First-render evidence byte-identical (`git status` shows no first-render or guarded-byte change — only the regenerated `boot-report.json`).
- [ ] 5.2 Scenario → executed-check mapping (below); every code row names a check that actually ran, and the docs/ledger rows record the documentation work (docs rows reviewed with this change, ledger row executed at archive).
- [ ] 5.3 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): the Settings/AudioManager delivery with evidence pointers, the M5 items that remain, and the change lifecycle state — executed at archive stage.

### 5.2 Scenario → executed-check mapping

Rows 1–13 are the scenarios of the `godot-settings` delta; rows 14–24 are the
scenarios of the `godot-audio-manager` delta; rows 25–26 are the scenarios of
the modified `first-render-in-godot` R1. Commands: GS = `godot --headless
--path apps/client-godot -s res://tests/test_settings.gd`, GA = `godot
--headless --path apps/client-godot -s res://tests/test_audio_manager.gd`,
V = `verify.ps1`, VB = `verify-boot.ps1`.

| # | Scenario | Executed check | Run |
|---|---|---|---|
| 1 | Start with default preferences | `test_settings` defaults: both getters `true`, no notification at creation | GS |
| 2 | Commit a preference change | setter success, getter flips, exactly one `setting_changed` payload with key and value | GS |
| 3 | Reject an unchanged preference | unchanged request rejected (`setting_unchanged`), committed state unchanged, silent | GS |
| 4 | Round trip through storage | set both `false` → save → reset → load → both getters `false`, save/load succeed | GS |
| 5 | Reject an absent file | `load` on a missing temp path rejected (`storage_file_missing`), state unchanged, silent | GS |
| 6 | Reject unreadable contents | corrupt temp file rejected (`storage_read_failed`) inside the `Engine.print_error_messages` window, state unchanged, silent | GS |
| 7 | Reject invalid contents | three schema violations (missing key, non-`boolean`, unknown key) each rejected (`storage_invalid_contents`), state unchanged, silent | GS |
| 8 | Apply a load change-only | one-key-differs load succeeds with exactly one notification for that key | GS |
| 9 | Report a storage write failure | save into a missing directory rejected (`storage_write_failed`), committed state unchanged | GS |
| 10 | Scope enforces the new boundary | `test_project_scope`: 47-file inventory, exactly six autoloads, two scenes, 13 forbidden tokens | V |
| 11 | Keep prior verifications green | `verify.ps1` + `verify-boot.ps1` exit 0; guard pre=post; first-render report/PNG byte-identical | V, VB |
| 12 | Record the executed commands | `AGENTS.md` ten-suite prose; `README.md` suite purpose, invocation, observed counts | — (docs review) |
| 13 | Record the milestone progress | roadmap `Project Status` ledger entry (task 5.3, archive stage) | — (ledger) |
| 14 | Start with both buses ready | `test_audio_manager` startup: both buses under `Master`, getters `true`, unmuted at 0 dB, no notification | GA |
| 15 | Apply a music toggle | setter success, getter flips, `Music` mute matches, exactly one `music_enabled_changed` payload | GA |
| 16 | Reject an unchanged toggle | unchanged request rejected (`music_setting_unchanged` / `sfx_setting_unchanged`), bus and committed state unchanged, silent | GA |
| 17 | Reject when the bus is missing | bus removed → setter rejected (`*_bus_missing`), committed state unchanged, silent; bus restored | GA |
| 18 | Follow a Settings change | Settings commits `music_enabled=false` → AudioManager commits, `Music` muted, one `music_enabled_changed` payload | GA |
| 19 | Bind to current preferences | preference already `false` before a manager instance starts → instance binds, state and bus match, exactly one notification | GA |
| 20 | Start without Settings | autoload removed → fresh instance starts without error, buses ensured, direct setters work; autoload restored and asserted | GA |
| 21 | Scope enforces the new boundary | `test_project_scope`: 47-file inventory, exactly six autoloads, two scenes, 13 forbidden tokens | V |
| 22 | Keep prior verifications green | `verify.ps1` + `verify-boot.ps1` exit 0; guard pre=post; first-render report/PNG byte-identical | V, VB |
| 23 | Record the executed commands | `AGENTS.md` ten-suite prose; `README.md` suite purpose, invocation, observed counts | — (docs review) |
| 24 | Record the milestone progress | roadmap `Project Status` ledger entry (task 5.3, archive stage) | — (ledger) |
| 25 | (R1) Boot with the pinned engine | `test_project_scope` pinned-engine check (`find("4.7")`) + `test_boot_scene` ready-marker assertion (`contains("4.7.2")`) + boot-report `main-scene boot reported engine 4.7.2` + VB main-scene live phase | V, VB |
| 26 | (R1) Remain within the verification scope | `test_project_scope`: allow-list, six autoloads, no system outside the allow-list, no legacy protocol token, first-render scene and tests intact | V |

Disclosures: every specified branch is executed directly — both schema-violation
rejections plus the corrupt-file read failure, both categories of unchanged
rejection, the bus-missing branch with in-suite restoration, both binding
branches with the Settings removal/restoration asserted, and every getter's
committed-state read. The source-scan early return on an unreadable file is a
test harness failure guard, not specified behavior.
