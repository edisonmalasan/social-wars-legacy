# Tasks

## 1. Executed-legacy boot fixtures

- [x] 1.1 Write the fixture capture command that starts the real legacy Flask server in a disposable copy (pinned CPython 3.9.13, `-B`, temporary corpus seeded from `tests/saves/fresh-player.json`), performs the legacy login/session save-list request plus `get_game_config.php` and `get_player_info.php` requests with exact request parameters, records before-hashes, responses, and after-hashes, and stops the server within the run.
- [x] 1.2 Execute the capture; commit the captured request/before/response/after fixtures under `tests/fixtures/godot-compatibility-boot/` with a README naming the executable, invocation, exit code, and containment (no working-tree save touched, disposable copy discarded).
- [x] 1.3 Commit the field-stability record separating stable fields from time-dependent fields (timestamps, time-derived config) with the documented normalization for each time-dependent field, derived from two captures or code inspection as appropriate.
- [x] 1.4 Define the SHA-256 guard set (legacy sources, `config/`, both conversion packages, the three registry manifests, committed M4 evidence, on-disk saves) and capture the pre-change baseline digests.

## 2. Compatibility API v0 service

- [x] 2.1 Add `apps/compat-api/` with a Flask service skeleton using only the existing locked dependencies: loopback `127.0.0.1` binding at port 5056, legacy state initialization matching `server.py` (`load_saves`, `load_static_villages`, `load_quests`) by importing the legacy boot modules unchanged, and a documented start command.
- [x] 2.2 Implement `GET /v0/session` (legacy `all_saves_info()` + game version + server time in the documented envelope) and `POST /v0/bootstrap` (legacy `get_game_config()` + `get_player_info()` payloads), with structured JSON errors: 400 missing `user_id`, 404 unknown save, non-2xx, no partial payload.
- [x] 2.3 Guarantee no persistence: the service never calls `save_session` or writes any file; add a test asserting pre/post SHA-256 identity of every save in the corpus after session + bootstrap calls (including the in-memory `last_logged_in`/`reset_stuff` semantics being exercised).
- [x] 2.4 Add offline parity tests: Compatibility API outputs replayed against the committed legacy fixtures field-by-field for stable fields and under the documented normalization for time-dependent fields, with no server and no network running.

## 3. GameApi abstraction and boot scene

- [ ] 3.1 Add the `GameApi` autoload with typed `list_sessions()` and `get_bootstrap(user_id)` operations, typed boot-data classes, and the implementation switch (`gameapi/implementation`: `legacy_v0` | `fake`, default `fake`).
- [ ] 3.2 Implement `FakeApi` reading the committed v0/fixture data with no sockets; add headless Godot tests asserting the typed shapes and that no process or network is needed.
- [ ] 3.3 Implement `LegacyV0Api` as the loopback HTTP client to port 5056 (built-in `HTTPRequest` only), and add headless tests against a running Compatibility API asserting it yields the same typed shapes as `FakeApi`.
- [ ] 3.4 Add the boot scene as the main scene: session init → bootstrap → player summary (name, level, xp) plus engine version and connection state; explicit error states for unreachable endpoint (connection refused) and structured API errors, each naming the failure; headless assertions for the failure paths.
- [ ] 3.5 Switch `project.godot` to the boot main scene and add the `GameApi` autoload; retarget the M4 windowed capture in `verify.ps1` to `res://scenes/first_render.tscn` explicitly and prove the committed `first-render.png`/`report.json` remain byte-identical after a full `verify.ps1` run.
- [ ] 3.6 Evolve the project-scope test per the modified R1: allow-list grows to exactly the foundation files this change adds (GameApi, `LegacyV0Api`, `FakeApi`, boot data, boot scene, boot evidence), scene assertion becomes set equality over `{boot.tscn, first_render.tscn}`, autoload assertion becomes exactly `GameApi`, legacy protocol tokens and camera/UI/`ContentRegistry`/`GameClock` tokens stay forbidden; all first-render loader/comparator/scene suites stay green.

## 4. End-to-end verification and evidence

- [ ] 4.1 Add `apps/client-godot/verify-boot.ps1`: pinned-python compat + parity + containment tests → start Compatibility API on 5056 with a disposable corpus → headless boot run asserting session list, bootstrap summary fields equal to the fixture save, and error-path behavior → teardown → SHA-256 guard set verified → committed `apps/client-godot/evidence/boot/boot-report.json` written; non-zero exit on any failure.
- [ ] 4.2 Run the full battery in the final state: Compatibility API tests, all four Godot test suites, `verify-boot.ps1`, M4 `verify.ps1` (evidence byte-identical), pinned `git diff --check`, and `openspec validate --specs --strict`.
- [ ] 4.3 Review the complete diff against the spec delta scenarios; confirm every scenario maps to an executed check and record any executed-check gaps honestly in the ledger.

## 5. Documentation, commands, and records

- [ ] 5.1 Update `AGENTS.md`: document the actually-executed fixture capture, Compatibility API test, boot verification, and retained first-render verification commands with their constraints; correct the stale "no Godot project exists yet" note.
- [ ] 5.2 Add `apps/compat-api/README.md` and extend `apps/client-godot/README.md`: port/loopback contract, fixture paths, evidence paths, disposable-corpus mechanics, and the v0 claim limits (read-only bootstrap parity for the fresh-save corpus — not gameplay parity, not authentication security, not progressed-player coverage).
- [ ] 5.3 Update the roadmap Project Status ledger: M5 §16/§17/§18 delivered with evidence pointers, remaining M5 items (ContentRegistry §19, asset ID registry §20, GameClock, camera, UI foundation, Settings/AudioManager depth), verification results actually observed, and the next eligible objective.
