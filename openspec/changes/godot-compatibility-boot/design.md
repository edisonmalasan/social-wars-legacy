# Design

## Context

M4 delivered `apps/client-godot/` as a render-verification-only project (its spec forbids `GameApi`, network, and backend integration) plus a verified capture/compare pipeline whose golden evidence must stay byte-identical. M5's exit criterion is "Client boots and communicates with Compatibility API," and the roadmap's Build-Now order is GameApi abstraction → Compatibility API v0 → town bootstrap. The legacy boot surface is fully source-mapped: `login` (session save list), `get_game_config.php` → `get_game_config()`, `get_player_info.php` → `get_player_info(USERID)` (returns player info + default map + private state + neighbors, and deliberately mutates `last_logged_in`/`reset_stuff` in memory), `sessions.save_info()/all_saves_info()/session()`, all plain importable modules; the endpoint catalog is source-inspection-only evidence (no executed endpoint-level evidence yet); `tests/saves/fresh-player.json` is the canonical fresh corpus; pinned CPython 3.9.13 + Flask 2.2.5 are the locked runtime; Godot 4.7.2 is installed.

## Goals / Non-Goals

**Goals:** read-only boot vertical slice satisfying the M5 exit criterion end-to-end; executed-legacy fixtures as the parity oracle; legacy code and files untouched; loopback-only containment; M4 verification and evidence untouched; every claim backed by a runnable command.

**Non-Goals:** gameplay/command execution (buy/move/attack — M7+), ContentRegistry (§19), asset ID registry (§20), GameClock, camera, UI foundation, Settings/AudioManager, authentication security, Server v1/PostgreSQL, external networking, progressed-player coverage, live-Flash parity, and any modification of legacy behavior or files.

## Decisions

- **D1 — Slice = roadmap §16+§17+§18, read-only.** The smallest coherent M5 objective is the bootstrap vertical slice: `GameApi` (bootstrap operations), Compatibility API v0 (session + bootstrap endpoints), boot scene. It is exactly the milestone's exit criterion; everything else in M5 (ContentRegistry, asset ID registry, camera, UI, clock) is recorded as subsequent objectives rather than smuggled in.
- **D2 — In-process adapter, not an HTTP proxy.** The Compatibility API is a separate Flask app that imports the legacy boot modules (`get_game_config`, `get_player_info`, `sessions`, `engine`, `version`, `bundle`) unchanged and initializes legacy state exactly as `server.py` does (`load_saves`, `load_static_villages`, `load_quests`). Rationale: no legacy file is modified (preservation rule), no fragile `play.html`/FlashVars scraping, no double-server orchestration; the legacy HTTP endpoints remain the *reference oracle* via captured fixtures, so the adapter still proves parity against executed legacy behavior. Legacy dynamic endpoints need no template/static assets.
- **D3 — v0 surface.** `GET /v0/session` → `{protocol, ok, game_version, server_time, saves:[{id,name,xp,level}]}` (mirrors the legacy login save list); `POST /v0/bootstrap` with JSON `{user_id}` → `{protocol, ok, game_version, server_time, config, player_info}` (mirrors `get_game_config.php` + `get_player_info.php`). POST for bootstrap matches the legacy POST semantics and the in-memory boot mutation it performs. Loopback `127.0.0.1:5056` (legacy stays on 5055). Structured JSON errors: 400 missing field, 404 unknown user. Flask 2.2.5 from the existing lock — no new dependencies. The service never calls `save_session`: disk never changes.
- **D4 — Fixtures are the oracle, captured by execution.** Before service code exists, a capture command runs the *real legacy Flask server* in a disposable copy (pinned interpreter), records request / before-hash / response / after-hash for both dynamic endpoints against `fresh-player.json`, and stops it. Compat parity tests then replay offline: stable fields must equal the fixtures; time-dependent fields (timestamps, time-derived config) are listed in a field-stability record and compared under documented normalization. This yields executed endpoint-level evidence for the first time without claiming general endpoint parity.
- **D5 — GameApi surface is the roadmap's boot subset.** Autoload `GameApi` with typed `list_sessions()` and `get_bootstrap(user_id)` (roadmap's `get_player()`/`get_town()`/action verbs arrive with their milestones); implementations selected by project setting (`gameapi/implementation`: `legacy_v0` | `fake`), default `fake` so tests are hermetic and the boot verification selects `legacy_v0` explicitly. Typed boot data (Dictionary → typed GDScript classes) crosses the API boundary; raw transport dictionaries never reach presentation code.
- **D6 — Boot scene becomes the main scene; first-render retargeted.** `project.godot` main scene switches to the boot scene (it is the client's entry point). The M4 windowed capture step in `verify.ps1` is changed to run `res://scenes/first_render.tscn` explicitly; the golden PNG/report must remain byte-identical (guard digests pre/post), proving the retarget is behavior-preserving.
- **D7 — Scope-test evolution implements the R1 modification.** The allow-list grows to the M5 foundation boundary (GameApi/`LegacyV0Api`/`FakeApi`/boot data/boot scene/boot evidence), the "exactly one `.tscn`" assertion becomes set equality over `{boot.tscn, first_render.tscn}`, the autoload assertion becomes "exactly `GameApi`", Flash/legacy-protocol tokens stay forbidden, and camera/UI/`ContentRegistry`/`GameClock` tokens stay forbidden for their future changes. The first-render loader/comparator/scene tests are untouched and must stay green.
- **D8 — Headless-first, one-command verification.** `apps/client-godot/verify-boot.ps1` orchestrates: pinned-python compat + parity + containment tests → start Compatibility API on 5056 with a disposable corpus → Godot headless boot run asserting session/bootstrap/summary → teardown → SHA-256 guards (legacy sources, packages, manifests, M4 evidence, on-disk saves) → write `apps/client-godot/evidence/boot/boot-report.json` (committed). M4 `verify.ps1` remains a separate green command. Fake-based Godot tests need no server at all.
- **D9 — Containment.** Only `127.0.0.1` is ever dialed (documented limit: code-path containment, not OS-level egress proof); all Python under pinned CPython 3.9.13 with `-B`; every executed run (capture, compat tests, boot verification) uses disposable copies of the corpus (protocol-replay precedent) so the working `saves/` never changes; no Flash/Ruffle/ActionScript/browser anywhere.
- **D10 — Claim limits.** v0 proves read-only bootstrap parity for the fresh-save corpus against executed fixtures. It does not prove gameplay parity, authentication security, progressed-player coverage, or any behavior of the 63 `command.php` branches; the READMEs and ledger say so verbatim.

## Risks / Trade-offs

- **Legacy module import side effects** (prints, `os.system("color")` only in `server.py` — the boot modules avoid it; `load_*` print): acceptable — compat imports the modules, not `server.py`, and any surprise fails the tests loudly.
- **Time-dependent fixture fields** reduce strictness: mitigated by the explicit field-stability record instead of blanket fuzzy matching.
- **`get_player_info`'s mutation quirk**: preserved (legacy evidence) and made safe by disposable corpora + on-disk hash guards; no persistence path exists in compat.
- **Two verify scripts** (`verify.ps1`, `verify-boot.ps1`) could drift: both are documented in `AGENTS.md`, both must be green before merge; M4's stays byte-stable as its own regression guard.
- **MODIFIED first-render R1** weakens the M4 freeze by design: the allow-list narrows what M4 forbade to exactly this change's files, and everything M4 actually protected (evidence bytes, verification green, no Flash tokens, no game systems beyond the allow-list) is retained as scenarios.

## Migration Plan

1. Capture executed-legacy fixtures (disposable, pinned) — no service code yet.
2. Compatibility API v0 + offline parity/containment tests.
3. `GameApi` + `FakeApi` tests (hermetic) → `LegacyV0Api` + boot scene + scope-test evolution → first-render retarget.
4. `verify-boot.ps1` end-to-end + full battery (compat tests, Godot suites, M4 `verify.ps1`, strict validation).
5. Docs (AGENTS/READMEs) + evidence + ledger; then Verify → Sync → Archive stages.

## Open Questions

None blocking: port (5056), fixture path (`tests/fixtures/godot-compatibility-boot/`), implementation-switch mechanism (project setting), and evidence path (`apps/client-godot/evidence/boot/`) are fixed above; exact file layout inside `apps/compat-api/` is left to implementation provided the executed commands are documented.
