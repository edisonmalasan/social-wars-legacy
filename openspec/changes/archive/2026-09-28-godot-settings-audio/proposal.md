# Proposal

## Why

Roadmap M5 (Godot Foundation) was historically scoped as "GameApi/Session/ContentRegistry/GameClock/Settings/AudioManager + compatibility boot" (ledger as first recorded in `356cc83`), roadmap §17 lists `Settings` and `AudioManager` among the allowed potential autoloads, and AGENTS.md already sanctions both as example cross-cutting autoloads — but the M5 Deliver block enumerates eight items and omits them, so this change reconciles the block by adding the two lines. The roadmap ledger names Settings/AudioManager depth as the next eligible M5 objective: every other foundation autoload is delivered and archived, and nothing owns user preferences or audio output yet — `project.godot` has pinned `[audio] driver="Dummy"` since first-render (`569d2bb8`), the project owns no audio buses, and the M6 town slice ends with a HUD that will need both services. An evidence search is recorded: `config/main.json` contains no user-settings or audio-preference key (its 139-entry `sounds` key is content definitions `{id, file, max, loops, preload, description}` and its `volume` fields are building sizes), the save corpus contains no sound/music/audio/volume/settings/mute field, the legacy server (`command.py`, `engine.py`) has no sound/music/settings handler and no legacy root script references them, and the asset-registry SWF inspection across 1,176 SWFs exports only two audio-ish symbols (`AudioSheet`, `SpeakerBoxMC`) with no settings/volume/mute/options symbol — so no legacy user-settings behavior has been captured, and this change delivers the bounded, explicitly provisional M5 Settings/AudioManager services rather than an unevidenced parity claim.

## What Changes

- New `Settings` autoload (`apps/client-godot/scripts/settings.gd`): a `Node`-based cross-cutting service, script-only. Committed state = exactly two boolean preferences, `music_enabled` and `sfx_enabled`, both defaulting to `true`; fail-closed `{ok, error}` setters `set_music_enabled` / `set_sfx_enabled` that reject an unchanged value with `setting_unchanged` and leave committed state untouched; a change-only `setting_changed(key, value)` signal; getters reflect only committed state. Explicit persistence: `load(path)` / `save(path)` over `ConfigFile` (default `user://settings.cfg`) with fail-closed read errors `storage_file_missing`, `storage_read_failed`, `storage_invalid_contents` (missing key, non-boolean value, or unknown key — committed state stays untouched and no field is ever dropped) and write error `storage_write_failed`; a successful load emits `setting_changed` only per key that actually changed. No automatic load or save anywhere, no wall-clock, no transport, no content loading, no dependency on any other script or autoload.
- New `AudioManager` autoload (`apps/client-godot/scripts/audio_manager.gd`): a `Node`-based cross-cutting service, script-only. At `_ready` it idempotently ensures `Music` and `SFX` buses under `Master` and binds to the Settings autoload through a `/root/Settings` lookup (fail-soft when absent), applying the current preferences and following later `setting_changed` signals; committed state mirrors the two preferences; fail-closed `set_music_enabled` / `set_sfx_enabled` apply preferences as bus mute (`music_setting_unchanged` / `sfx_setting_unchanged` / `music_bus_missing` / `sfx_bus_missing`), leaving volume policy untouched at 0 dB; change-only `music_enabled_changed` / `sfx_enabled_changed` signals; getters. No playback, no content loading, no persistence, no wall-clock.
- New headless suites `tests/test_settings.gd` and `tests/test_audio_manager.gd`, the ninth and tenth hermetic suites in `verify-boot.ps1` (they use the real autoloads through `/root/` lookups, mirroring the session and game-clock suites, and are pure local behavior — no API, no boot flow; they ignore the loop's endpoint argument).
- `project.godot`: register both autoloads after `GameClock` (Settings before AudioManager so `_ready` order holds) and record them in the header comment; the scene set (two) stays unchanged — no `.tscn` is added; `[audio] driver="Dummy"` stays exactly as committed (audible output binds with the later sound-content work).
- Project scope grows: `test_project_scope.gd` allow-lists the four new files (43 → 47) and its `EXPECTED_AUTOLOADS` grows to the six registered autoloads (4 → 6); the forbidden tokens stay 13.
- `first-render-in-godot` requirement R1 MODIFIED: the settings and audio work joins the allow-listed foundation systems, and the scenario's list becomes the six allow-listed autoloads.
- Docs: `AGENTS.md` and the client README describe the actually executed ten-suite battery with observed counts; the `project.godot` header and the scope-test header comment record the new systems; the roadmap M5 Deliver block gains the `Settings` and `AudioManager` lines (reconciliation), and the Project Status ledger records the delivery at archive.

## Non-Goals

- No sound or music playback: the 27 extracted MP3s and the 139 `sounds` definitions stay untouched content, and no `AudioStreamPlayer`, streaming, or triggering API exists here; audible output also requires revisiting the pinned `driver="Dummy"` policy, which binds with the sound-content change.
- No settings UI: no widget, menu, button, or HUD wiring (M6 HUD task onward), and nothing calls `load`/`save` or the setters outside the suites yet — the tested APIs are the deliverable.
- No automatic persistence and no boot integration: the boot scene keeps its own status labels and its ready flow, session clearing, clock anchoring, and `state=ready` contract stay unchanged.
- No legacy-parity settings claim: no legacy user-settings behavior exists to capture (recorded above); authentic preference semantics bind later if evidence appears.
- No Compatibility API, GameApi, Session, ContentRegistry, GameClock, camera, or UI foundation behavior change; no M6 work.

## Capabilities

### New Capabilities

- `godot-settings`: the Settings autoload — committed boolean preference state, fail-closed setters, change-only notifications, explicit fail-closed `ConfigFile` persistence, containment, and documented commands.
- `godot-audio-manager`: the AudioManager autoload — the `Music`/`SFX` runtime bus structure, Settings binding and application as bus mute, fail-closed setters, change-only notifications, containment, and documented commands.

### Modified Capabilities

- `first-render-in-godot`: requirement R1 "Minimal render-verification Godot project" — the foundation allow-list grows to include the settings and audio work with their scripts and tests (47 files, exactly six allow-listed autoloads, two scenes, 13 forbidden tokens).

## Impact

- New files: `apps/client-godot/scripts/settings.gd`, `apps/client-godot/scripts/audio_manager.gd`, `apps/client-godot/tests/test_settings.gd`, `apps/client-godot/tests/test_audio_manager.gd`.
- Edited files: `apps/client-godot/project.godot` (autoload block + header comment), `apps/client-godot/tests/test_project_scope.gd` (allow-list, expected autoloads, count assertions), `apps/client-godot/verify-boot.ps1` (two hermetic suites, suite prose), `docs/DEVELOPMENT_ROADMAP.md` (M5 Deliver block reconciliation in this proposal; Project Status ledger at archive).
- Docs: `AGENTS.md`, `apps/client-godot/README.md`.
- Verification: `verify.ps1` and `verify-boot.ps1` both re-run to exit 0; `boot-report.json` grows by the new suites' assertions (regenerated, committed as `test:`); every guarded byte (guard baseline, first-render evidence, conversion packages, asset manifests, legacy sources, normalized content) stays byte-identical; no legacy or M4/M5 evidence file changes.
