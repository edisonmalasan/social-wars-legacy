# Proposal

## Why

M5 — Godot Foundation — starts from the roadmap's "Build Now" order: Godot initialization (done by M4's `apps/client-godot/`) → **GameApi abstraction** → **Compatibility API v0** → town bootstrap. The M4 change deliberately froze the project at render verification ("no `GameApi`, no network, no backend integration"), so the client still cannot talk to anything: there is no API abstraction, no modern-facing surface in front of the legacy server, and no boot path. M5's exit criterion is "Client boots and communicates with Compatibility API," and the migration order puts Boot/Content first. The legacy server already exposes exactly the boot surface the Flash client used — `login`/session save list, `get_game_config.php`, `get_player_info.php` — as plain importable Python modules (`get_game_config.py`, `get_player_info.py`, `sessions.py`) with a source-grounded endpoint catalog and a canonical fresh-player save (`tests/saves/fresh-player.json`). The smallest coherent next step is therefore the read-only bootstrap slice: roadmap §16 (GameApi abstraction) + §17 (Compatibility API v0) + §18 (bootstrap loading).

## What Changes

- **Compatibility API v0** (`apps/compat-api/`): a small loopback-only JSON service that adapts the *unchanged* legacy boot modules in-process — `GET /v0/session` (save list + game version + server time, mirroring the legacy login surface) and `POST /v0/bootstrap` (legacy `get_game_config()` + `get_player_info()` payloads in a documented envelope). Fail-closed structured errors for missing/unknown user ids; bound to `127.0.0.1` at an explicit port; **never persists** (the legacy in-memory boot effects are preserved, disk writes are not).
- **Golden legacy fixtures captured from the executed legacy endpoints** (contained run in a disposable copy under pinned CPython 3.9.13): request / before-state / response / after-state for `get_game_config.php` and `get_player_info.php`, plus a field-stability record separating stable fields from time-dependent ones. Compat tests replay these offline as the parity oracle.
- **`GameApi` abstraction in Godot** (roadmap §16): an autoload with typed `list_sessions()` / `get_bootstrap()` operations and two interchangeable implementations — `LegacyV0Api` (JSON over loopback HTTP to the Compatibility API) and `FakeApi` (committed fixtures, zero sockets) — so boot/presentation code never touches `command.php`, AMF, FlashVars, or legacy form encoding.
- **Boot scene as the new main scene** (roadmap §18): session init → bootstrap → player summary (name/level/xp) with explicit error states for unreachable endpoints and structured API failures. The first-render verification is retargeted to its own scene explicitly so the M4 golden evidence stays byte-identical.
- **Evolves the first-render project-scope requirement** (MODIFIED, see Capabilities): the M4 "render-verification only, no M5 systems" freeze gives way to an enforced allow-list that permits exactly the foundation files this change adds, keeps render verification green, and continues to forbid camera/UI/`ContentRegistry`/`GameClock` until their own changes.
- **Records**: executed commands in `AGENTS.md` and READMEs (including the stale "no Godot project exists yet" note being corrected), evidence under `apps/client-godot/evidence/boot/`, and M5 §16–18 progress in the roadmap Project Status ledger.
- **Claim boundary**: read-only bootstrap parity for the fresh-save corpus, proven against executed legacy fixtures — explicitly *not* gameplay parity, not authentication security, not progressed-player coverage, and no Flash/Ruffle/ActionScript/browser/external network anywhere (127.0.0.1 only).

## Capabilities

### New Capabilities
- `godot-compatibility-boot`: the read-only boot vertical slice — Compatibility API v0 bootstrap service over unchanged legacy modules, fixture-captured legacy parity, `GameApi` with interchangeable implementations, boot scene evidence, loopback containment, and the documented command/assessment records.

### Modified Capabilities
- `first-render-in-godot`: requirement "Minimal render-verification Godot project" (R1) evolves from the M4 freeze (project contains *only* render-verification content, no M5 systems) to the M5 foundation boundary (allow-listed `GameApi`/`LegacyV0Api`/`FakeApi`/boot scene permitted; render-verification content intact and its checks green; `ContentRegistry`/`GameClock`/camera/UI still excluded; no Flash-related runtime or legacy protocol token). Rationale: the project graduates from verification harness to client foundation; leaving R1 unmodified would make every boot file a spec violation. The M4 exit assessment, its committed evidence, and the other six first-render requirements are unchanged.

## Impact

- **Adds**: `apps/compat-api/` (service, tests, README), `tests/fixtures/godot-compatibility-boot/` (captured legacy responses + stability record), Godot `GameApi`/`LegacyV0Api`/`FakeApi`/boot-data scripts, boot scene, `apps/client-godot/verify-boot.ps1`, boot evidence, AGENTS/README command docs, roadmap ledger update.
- **Modifies**: `apps/client-godot/project.godot` (add `GameApi` autoload, main scene → boot), `apps/client-godot/verify.ps1` (windowed capture targets `res://scenes/first_render.tscn` explicitly), the project-scope test (allow-list evolves with R1), the first-render delta spec (R1 MODIFIED).
- **Consumes read-only**: legacy boot modules and config/mods (imported and executed unchanged), `tests/saves/fresh-player.json` (copied into disposable runs), the first-render scene/scripts (behavior unchanged; M4 evidence must remain byte-identical).
- **Requires**: pinned CPython 3.9.13 with the existing locked dependencies (Flask 2.2.5 — no new packages), installed Godot 4.7.2, loopback-only HTTP between client and Compatibility API (port 5056), disposable copies for every executed run.
- **Unchanged**: legacy server code and endpoints, on-disk saves (compat never persists), conversion packages, all preservation manifests, normalized content, M4 evidence bytes.
