# client-godot — first render in Godot

A minimal Godot 4.7 project that loads two committed `conversion-v1` packages
(`assets/converted/buildings/0001_house_1_m` and
`assets/converted/units/10033_wild_elephant`), resolves each package's
frame-1 placement closure, decodes the shape geometry, places one
`TextureRect` per bitmap-bearing shape at its decoded position, renders both
entities in a fixed 448×224 world, and captures PNG evidence compared
pixel-by-pixel against an independently composed reference.

Everything here is **runtime loading** — no editor import, no pre-generated
`.import`/`.godot/imported` artefacts, no editor-generated scene files.
No Flash/SWF execution, no Ruffle, no ActionScript, no browser, no network.
Rendering happens only in Godot.

OpenSpec change: `openspec/changes/first-render-in-godot`
(delta spec
`openspec/changes/first-render-in-godot/specs/first-render-in-godot/spec.md`).

## Pinned engine

Godot **4.7.2.stable** (official build `ed1daf0bf`, Windows x64), installed
via `winget install GodotEngine.GodotEngine`. The winget package creates no
`godot` PATH alias, so the executable is discovered by exact known paths,
then a bounded search of
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\GodotEngine.GodotEngine_*\`.

The exact executable verified on this machine (use it verbatim wherever
`godot` appears below):

```text
C:\Users\Edison\AppData\Local\Microsoft\WinGet\Packages\GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe\Godot_v4.7.2-stable_win64.exe
```

`godot --version` on that binary prints `4.7.2.stable.official.ed1daf0bf`.

Override the executable with `-GodotExe <path>` or the `GODOT_EXE`
environment variable.

## Verification

One command runs the whole pipeline — render → capture → compare → report →
exit (design D6), from the repository root:

```powershell
powershell -File apps/client-godot/verify.ps1
```

Exit code `0` means every stage passed; any failure exits non-zero. The run
needs a display session for the windowed capture; `-SkipWindowed` runs only
the headless stages and deliberately still exits non-zero (verification is
incomplete without capture).

Individual stages (all run from the repository root; `godot` below stands
for the pinned executable path shown above, `-headless` for the
script-only stages):

```bash
# Headless test suites
godot --headless --path apps/client-godot -s res://tests/test_package_loader.gd
godot --headless --path apps/client-godot -s res://tests/test_scene_build.gd
godot --headless --path apps/client-godot -s res://tests/test_project_scope.gd
godot --headless --path apps/client-godot -s res://tests/test_content_registry.gd
godot --headless --path apps/client-godot -s res://tests/test_asset_ids.gd

# Deliberate-failure scenarios (each must exit 1 with its marker)
godot --headless --path apps/client-godot -s res://tests/test_package_loader.gd -- --scenario=foreign-envelope
godot --headless --path apps/client-godot -s res://tests/test_package_loader.gd -- --scenario=broken-chain
godot --headless --path apps/client-godot -s res://tests/test_package_loader.gd -- --scenario=oracle-tamper

# Headless compare against committed evidence (provenance-insensitive)
godot --headless --path apps/client-godot -s res://scripts/run_compare.gd

# Deliberate-failure comparator self-test (must exit 1 with [selftest] DETECTED)
godot --headless --path apps/client-godot -s res://scripts/run_selftest.gd

# Windowed render + capture + compare + report (writes the evidence)
godot --path apps/client-godot res://scenes/first_render.tscn
```

### What verify.ps1 asserts

- Before any run: SHA-256 of both package directories (relative paths,
  ordinal-sorted, `sha256␠␠path\n`), of the three registry manifests, of
  `tools/asset-registry/asset_ids.json`, and of the canonical content
  package directory (`packages/game-content/`).
- Godot discovers and reports engine `4.7.2.stable` exactly.
- All five headless test suites exit 0 and print `[test] PASS`
  (observed check counts: loader 123, scene-build 36, project-scope 659,
  content-registry 52, asset-ids 50).
- The three deliberate-failure scenarios exit non-zero **and** print their
  `[test] EXPECTED-FAILURE` markers (no `UNEXPECTED-ACCEPT`).
- Headless compare exits 0 with `[compare] PASS`.
- Comparator self-test exits non-zero with `[selftest] DETECTED`, and its
  scratch report records `pass=false`, affected pixels > 0, and an injected
  `max_channel_abs.r >= 100`.
- Windowed run exits 0, writes `evidence/first-render/first-render.png`
  (448×224 RGBA) and `evidence/first-render/report.json`
  (`result: PASS`), and logs `[first-render] capture written:` +
  `[verify] comparison pass=true failures=[]`.
- No `SCRIPT ERROR` or `ERROR:` lines in any Godot log (Godot script errors
  do not affect exit codes by themselves).
- After every run: package and manifest digests unchanged (read-only
  evidence, design D9).
- `.godot/` (cache, shader cache, verify logs/reports) never shows up in
  `git status` — the root `.gitignore` entries exclude it.

## Evidence

| File | Meaning |
| --- | --- |
| `evidence/first-render/first-render.png` | 448×224 windowed capture: house left, elephant right |
| `evidence/first-render/report.json` | Deterministic comparison report (`schema: first-render-in-godot/report/v1`) |

The report is intentionally timestamp-free: re-running the capture and the
headless compare yields byte-identical reports apart from four provenance
fields (`mode`, `engine.renderer`, `engine.video_adapter`,
`engine.video_adapter_api`). In observed runs the PNG itself was also
byte-identical across both runs
(`da15d192a901d75c3dc0d394d7eef1f9066beca3423b58620645c7d613f2bae5`),
but that is not claimed as a guarantee.

### Observed metrics (committed report)

Capture 448×224 RGBA = 100,352 pixels. Entity rectangles: house (16,16)
216×144, elephant (248,16) 171×191 (the elephant's
`width_px`/`height_px` artefact, see below).

| Metric | Value |
| --- | --- |
| Visible entity pixels (reference, inside the two rectangles) | 38,416 |
| Of those, matched within tolerance | 38,416 → `entity_coverage` = 1.0 |
| Pixels with any channel difference | 2,794 (2.8 % of the canvas) |
| `max_abs_per_channel` r / g / b / a | 1 / 1 / 1 / 0 |
| `mean_abs_per_channel` r / g / b / a | 0.0167 / 0.0148 / 0.0197 / 0.0000 |
| Pixels over `max_channel_abs` (`> 2`) | 0 (ratio 0.0) |
| Worst pixel | (167,16), channel `g`, Δ 1 |
| Bounds↔bitmap oracle | house 216×144 error (0,0); elephant 171×191 error (0,0) |

Character of the residual, measured pixel by pixel against the reference:
every differing pixel sits inside one of the two entity rectangles, is fully
opaque in the reference, and is *brighter* than the reference by at most one
unit in a colour channel; the alpha channel never differs, and no partially
covered pixel differs at all. So the residual is a one-unit rounding between
the OpenGL3 canvas readback and the CPU reference — not a geometry,
placement, alpha or colour-model defect — but its exact source is not
proven, which is why the tolerance keeps one unit of headroom rather than
assuming a cause.

### Tolerances and why

| Tolerance | Value | Rationale |
| --- | --- | --- |
| `max_channel_abs` | 2 | Observed maximum deviation is 1 (the readback rounding above). 2 keeps exactly one unit of headroom for another GPU/driver without getting close to hiding a real defect: a geometry, placement, blend or colour-model mistake moves edge pixels by tens of units, as the self-test shows (Δ 191). |
| `mean_abs_max` | 0.5 | Catches a systematic channel shift spread over many pixels while staying ~30× above the observed 0.0167 worst-channel mean. |
| `max_pixels_over_tolerance_ratio` | 0.005 (5 ‰) | Observed 0 pixels over tolerance. Allows a handful of driver-specific outliers without accepting a widespread mismatch: the self-test's single 24×24 block already reaches 0.00574 and fails. |
| `min_entity_coverage` | 0.95 | Observed 1.0 (38,416 of 38,416 visible entity pixels). Tolerates edge pixels only; a displaced, clipped or missing shape collapses this — the perturbed self-test reference drops to 0.9852 while the other criteria fail. |

All four are AND-ed: the run fails if any is violated — `max_abs_per_channel`
against `max_channel_abs`, `mean_abs_per_channel` against `mean_abs_max`, the
over-tolerance pixel ratio, and entity coverage — and the report lists every
violated criterion under `failures`. The reference comparator never reads
the captured PNG — it re-decodes the package with its own file reads and
straight-alpha over-blend — so a green result cross-checks decoding, matrix
mapping and compositing. Placement resolution itself is shared between the
two paths and is cross-checked separately by the loader tests, the
bounds↔bitmap oracle, and verify.ps1's report assertions.

### Self-test (tolerance sensitivity)

`run_selftest.gd` perturbs a 24×24 block of the rendered frame with opaque
red before comparison. Measured outcome: exit `1`, `[selftest] DETECTED`,
`pixels_over_tolerance = 576` (= 24×24), `max_abs_per_channel.r = 191`,
and the five recorded failures
`mean_abs.r = 1.113 exceeds 0.5`,
`max_abs.r = 191 exceeds 2`,
`max_abs.g = 64 exceeds 2`,
`max_abs.b = 64 exceeds 2`, and
`failing pixel ratio 0.00574 (576 of 100352 pixels over +2 per channel)
exceeds 0.005` — proving the tolerances reject a local colour error even
though its entity coverage (0.9852) alone would still pass.

## Claim limits

Verified by this change:

- Runtime loading of two committed `conversion-v1` packages (envelope
  validation, frame-1 placement closure, matrix decode, shape/fill geometry,
  straight-alpha bitmap decode).
- Both entities render in Godot, and the rendered pixels match an
  independent reference compositor within the documented tolerances.

Not verified (explicitly out of scope):

- Live-Flash parity: the reference reads the same committed package bytes,
  so the comparison proves **source-bitmap/shape fidelity**, not equality
  with what the original Flash runtime drew.
- Editor-import rendering: `.import`/`.godot/imported` artefacts are never
  created and no editor-generated scene files exist.
- Sprite timelines, physics, pathfinding, gameplay, networking, audio,
  zoom/pan input.
- Package `width_px`/`height_px` as bounds: for non-zero shape origins those
  fields record `xmax//20 × ymax//20` of the *absolute* coordinate frame,
  not the signed rectangle extent (elephant shape 2: records 158×176, true
  extent 171×191). The bounds come from the decoded transform matrices; the
  package values are cross-checked only where a zero origin makes them
  meaningful.

## Scope

Only `apps/client-godot/**` and the Godot cache entries in the root
`.gitignore` were added/changed by this change. Package source bytes are
never written: the packages are opened read-only and the verify script
re-hashes them before and after every run. No `.godot/` cache, shader cache,
verify log, or scratch report is ever committed.

## Straight alpha (measured)

The evidence capture and the reference compositor both use straight
(non-premultiplied) alpha (design D5). The loader test measures the choice instead
of assuming it: the composite reproduces the decoded JPEG colour and the
decoded alpha PNG verbatim (0 mismatches across both packages), the house
composite is 13,753 opaque / 15,053 fully transparent of its 216×144 px, and
the elephant composite is 20,714 opaque / 9,665 fully transparent of its
171×191 px. A premultiplied interpretation (any channel `|rgb·α − rgb|` above
the test suite's 0.004 epsilon) would change 4,144 house pixels
(13.3 % of 31,104) and 2,409 elephant pixels (7.4 % of 32,661) — so the
choice is observable in the evidence, not a hidden assumption.

## Compatibility boot slice

Second OpenSpec change: `godot-compatibility-boot`, archived at
`openspec/changes/archive/2026-09-27-godot-compatibility-boot` (delta specs
synced to `openspec/specs/godot-compatibility-boot/spec.md` and the modified
R1 in `openspec/specs/first-render-in-godot/spec.md`).

This adds the client boot path on top of the first-render work: a `GameApi`
autoload with typed `list_sessions()` / `get_bootstrap(user_id)` operations,
two implementations behind one switch, and a boot scene as the project's main
scene. The boot scene lists saves, bootstraps one save, and displays engine
version, connection state, and the player summary (name, level, xp).

| Piece | Path |
| --- | --- |
| Autoload facade | `scripts/gameapi/game_api.gd` (registered as `GameApi`) |
| Typed boot data | `scripts/gameapi/boot_data.gd` |
| Offline implementation | `scripts/gameapi/fake_api.gd` (reads committed fixtures, no sockets) |
| Loopback implementation | `scripts/gameapi/legacy_v0_api.gd` (the only file allowed to name the endpoint or use the HTTP types) |
| Main scene | `scenes/boot.tscn` + `scripts/boot.gd` |
| Suites | `tests/test_game_api_fake.gd`, `tests/test_game_api_live.gd`, `tests/test_boot_scene.gd` |

### Implementation switch and endpoint override

Selection is a project setting, never a code change:

| What | Setting (`project.godot`) | Runtime override (after `--`) |
| --- | --- | --- |
| Implementation | `[gameapi] implementation` = `fake` (default) \| `legacy_v0` | `--gameapi=fake` / `--gameapi=legacy_v0` |
| Endpoint | `[gameapi] endpoint` = `http://127.0.0.1:5056` | `--gameapi-endpoint=<url>` |
| Save to boot | (first save of the list) | `--boot-user=<save id>` |

```powershell
# Headless main-scene boot against the real Compatibility API
godot --headless --path apps/client-godot -- --gameapi=legacy_v0 --gameapi-endpoint=http://127.0.0.1:5056

# Headless main-scene boot with the offline fixtures (default)
godot --headless --path apps/client-godot -- --gameapi=fake
```

Only `127.0.0.1` is ever dialed. `legacy_v0` speaks `GET /v0/session` and
`POST /v0/bootstrap` to the Compatibility API v0 service
(`python -B apps/compat-api/run.py`, port 5056, loopback-only, disposable
corpus under the system temp directory that is removed when the service
stops); `fake` reads the committed fixtures under
`tests/fixtures/godot-compatibility-boot/` and never opens a socket. The
project-scope test restricts `http://`, `HTTPRequest`, and `HTTPClient` to
`scripts/gameapi/legacy_v0_api.gd`, so no presentation or boot code can reach
a transport.

Headless runs print machine-readable markers and quit:

```text
[boot] state=ready engine="4.7.2-stable (official) ed1daf0bf" protocol=compat-v0 game_version="alpha 0.02"
[boot] summary user_id=00000000-0000-4000-8000-000000000001 name="Warrior" level=1 xp=4
[boot] state=error code=unreachable_endpoint message=...
```

Windowed runs stay open as the client entry point.

### Verification

One command, from the repository root, no display session required:

```powershell
powershell -File apps/client-godot/verify-boot.ps1
```

It runs, in order: guard baseline → Compatibility API unittest discovery +
loopback smoke → the seventeen headless Godot suites → the
unreachable-endpoint scenario against a port with nothing listening → four
live phases → guard baseline again → `evidence/boot/boot-report.json`. Each
live phase is wrapped
by `compat_live_phase.py`, which starts `apps/compat-api/run.py`, waits for
`GET /v0/session`, runs exactly one Godot command, stops the service with
`CTRL_BREAK`, and asserts the service exited 0, the disposable corpus was
removed, no new `socialwars-compat-*` directory is left in temp, no
working-tree `saves/` exists, and the port is released. The fourth live
phase (`placement-live`) additionally passes
`--expect-save-mutation`: the wrapper snapshots every file under the
running corpus's `saves/` after readiness and fails unless at least one
changed after the Godot run — proof that a live `POST /v0/place` persisted
through the legacy dispatcher into the disposable corpus. Exit code is `0`
only
when every check holds; per-step logs land in `.godot/verify-boot/` (ignored).

Individual steps:

```bash
# Hermetic (no service)
godot --headless --path apps/client-godot -s res://tests/test_game_api_fake.gd
godot --headless --path apps/client-godot -s res://tests/test_boot_scene.gd
# Session scaffold + boot integration (67 observed checks): needs the dead
# endpoint for its follow-up failing boot; verify-boot.ps1 passes it to
# every hermetic suite
godot --headless --path apps/client-godot -s res://tests/test_session.gd -- --gameapi-endpoint=http://127.0.0.1:5057
# Game clock scaffold + boot integration (110 observed checks): same dead
# endpoint for its follow-up failing boot that must clear the anchor
godot --headless --path apps/client-godot -s res://tests/test_game_clock.gd -- --gameapi-endpoint=http://127.0.0.1:5057
# Camera controls (128 observed checks): pure component, no API and no
# boot flow; the endpoint argument the loop passes is ignored
godot --headless --path apps/client-godot -s res://tests/test_camera_controls.gd
# UI foundation (84 observed checks): pure component, no API and no
# boot flow; the endpoint argument the loop passes is ignored
godot --headless --path apps/client-godot -s res://tests/test_ui_foundation.gd
# Settings (91 observed checks): pure service, no API and no boot flow;
# the endpoint argument the loop passes is ignored
godot --headless --path apps/client-godot -s res://tests/test_settings.gd
# Audio manager (107 observed checks): pure service, no API and no boot
# flow; the endpoint argument the loop passes is ignored
godot --headless --path apps/client-godot -s res://tests/test_audio_manager.gd
# Town vertical slice (seven suites; scene/content work, the endpoint
# argument the loop passes is ignored): isometric projection, town state,
# town scene + slice, HUD, selection, placement, and the no-Flash gate
godot --headless --path apps/client-godot --script res://tests/test_town_iso.gd
godot --headless --path apps/client-godot --script res://tests/test_town_state.gd
godot --headless --path apps/client-godot --script res://tests/test_town_scene.gd
godot --headless --path apps/client-godot --script res://tests/test_town_hud.gd
godot --headless --path apps/client-godot --script res://tests/test_town_selection.gd
godot --headless --path apps/client-godot --script res://tests/test_town_placement.gd
godot --headless --path apps/client-godot --script res://tests/test_town_gate.gd
# Failure path: the scene must enter the explicit error state (suite exits 0
# only when it observed it)
godot --headless --path apps/client-godot -s res://tests/test_boot_scene.gd -- --scenario=unreachable --gameapi-endpoint=http://127.0.0.1:5057
# Live phases (each starts and tears down the service itself)
python -B apps/client-godot/compat_live_phase.py --port 5056 --name live -- <godot> --headless --path apps/client-godot -s res://tests/test_game_api_live.gd
# Placement live phase (fourth): one intent through POST /v0/place with the
# disposable corpus save asserted mutated
python -B apps/client-godot/compat_live_phase.py --port 5056 --name placement-live --expect-save-mutation -- <godot> --headless --path apps/client-godot --script res://tests/test_town_placement.gd -- --scenario=live-placement --gameapi-endpoint=http://127.0.0.1:5056
# Project scope (asserts the allow-list, including this change's evidence)
godot --headless --path apps/client-godot -s res://tests/test_project_scope.gd
```

The session suite (OpenSpec `godot-session`) proves the `Session`
scaffold's fail-closed lifecycle — no implicit session at startup,
explicit activation/clearing with transition signals, invalid activation
leaving state untouched — plus the boot integration: at `state=ready` the
session names the bootstrapped save with a summary equal to the fixture
save, a failed boot leaves none behind, and a failing follow-up attempt
replaces a previously active session rather than keeping it. It is the
fifth hermetic suite `verify-boot.ps1` runs.

The game-clock suite (OpenSpec `godot-game-clock`) proves the `GameClock`
scaffold's fail-closed lifecycle — no implicit anchor at startup,
anchor-once to the fixture response epoch with invalid anchors rejected,
pause freezing reported time while resume continues it, manual advance
moving time by exactly the requested count only while paused, and clearing
back to unanchored under the transition-signal rules — plus the boot
integration: at `state=ready` the clock is anchored within a bounded
interval of the fixture response timestamp, a failed boot leaves no anchor
behind, and a failing follow-up attempt clears the previous anchor rather
than keeping it. It is the sixth hermetic suite `verify-boot.ps1` runs.

The camera suite (OpenSpec `godot-camera`) proves the camera controls
component — a `Camera2D`-based, non-autoload part instanced by scenes: the
default view at creation, discrete zoom levels 0–2 over the fixed factor
table `1.0 / 2.0 / 4.0` (provisional foundation values — authentic town
camera ranges and bounds bind at the M6 town slice, captured with evidence
first), both level-bound rejections failing closed with state untouched,
exact cumulative world-space pans with the zero vector and non-finite
deltas rejected, and change-only pan/zoom notifications whose payloads are
the committed change. Its pointer half maps wheel notches (consumed,
silent at a bound), a left drag that pans the content under the cursor by
the screen movement divided by the committed zoom factor (exact at two
levels), and pass-through for unrelated events, with the node's own
`_unhandled_input` delegation observed through behavior; a final source
scan covers the component's no-clock, no-persistence, no-loading, and
no-other-script clauses. It is the seventh hermetic suite
`verify-boot.ps1` runs, and it needs no endpoint, service, or boot flow
(128 observed checks).

The UI foundation suite (OpenSpec `godot-ui-foundation`) proves the UI
foundation component — a `CanvasLayer`-based, non-autoload part instanced
by scenes: the empty registry and committed layer index at creation, slot
registration in order with full-rect visible pass-through containers and
exactly one notification per registration, empty and duplicate
registrations rejected with the registry untouched, hide/show flipping
the committed visibility with one change-only notification per change,
and the unknown-slot and unchanged-value rejections failing closed with
state untouched; a final source scan covers the component's no-clock,
no-persistence, no-loading, and no-other-script clauses. It is the
eighth hermetic suite `verify-boot.ps1` runs, and it needs no endpoint,
service, or boot flow (84 observed checks). The slot structure is
provisional foundation (design D2): no legacy UI behavior has been
captured, so authentic slot taxonomy, stacking order, and HUD layout
bind later, with evidence, alongside the M6 HUD work.

The settings suite (OpenSpec `godot-settings-audio`) proves the
`Settings` autoload's provisional preference contract — both boolean
preferences start `true` and creation notifies nobody, a commit flips
exactly one preference with exactly one key-and-value notification, and
an unchanged request is rejected with `setting_unchanged`, committed
state untouched, and silence — plus its explicit `ConfigFile`
persistence: a save/load round trip over a temp file under the ignored
`.godot/` cache, an absent file (`storage_file_missing`), corrupt
contents (`storage_read_failed`, read inside an
`Engine.print_error_messages = false` window because the engine prints
an `ERROR:` line that `verify-boot.ps1` fails on), the three
strict-schema violations (`storage_invalid_contents`: missing key,
non-`boolean` value, unknown key), change-only emission across a load,
and an unwritable path (`storage_write_failed`); a final source scan
covers the service's no-clock, raw-persistence, content-loading, and
no-other-dependency clauses (`ConfigFile` and its `load(` are excluded
as the sanctioned storage mechanism; 17 tokens). It is the ninth
hermetic suite `verify-boot.ps1` runs, and it needs no endpoint,
service, or boot flow (91 observed checks). The contract is provisional
foundation (design D2): no legacy user-settings behavior exists to
capture, so authentic preference semantics bind later, with evidence —
and nothing persists a preference outside the suites yet (no settings
UI; `load`/`save` are wired by the M6 HUD work).

The audio-manager suite (OpenSpec `godot-settings-audio`) proves the
`AudioManager` autoload — the cross-cutting `Music`/`SFX` bus owner:
both buses ensured at startup under `Master` exactly once, unmuted at
0 dB with both outputs on and nobody notified, each setter committing
and applying as bus mute (muted if and only if the committed value is
`false`) with exactly one change-only notification, and the
unchanged-value and removed-bus rejections failing closed with their
named errors, committed state and the bus untouched, and silence (the
removed bus is restored in-suite) — plus the Settings binding: a live
follow of a committed preference onto the bus, the initial application
of an already-false preference at a fresh instance's bind (exactly one
notification), and the fail-soft branch with the Settings autoload
temporarily removed and restored, both branches asserted; a final
source scan covers the manager's no-clock, no-persistence, no-content,
and no-other-dependency clauses (16 tokens; its `/root/Settings`
binding is the sole allowed cross-service reference). It is the tenth
hermetic suite `verify-boot.ps1` runs, and it needs no endpoint,
service, or boot flow (107 observed checks). The contract is
provisional foundation (design D2): no legacy audio behavior has been
captured, no sound is played (playback and the committed
`driver="Dummy"` policy bind with the later sound-content work).

Both new services return the foundation fail-closed envelope —
`{ok: true, error: ""}` on success, or
`{ok: false, error: "[<service>] <operation> rejected: <token>"}` — with
exactly these tokens:

| Service | Condition | Token |
| --- | --- | --- |
| `Settings` | any setter re-requests the committed value | `setting_unchanged` |
| `Settings` | `load` targets an absent file | `storage_file_missing` |
| `Settings` | `load` fails for any other reason (e.g. corrupt contents; the engine code rides in the message detail) | `storage_read_failed` |
| `Settings` | the file parses but violates the strict two-key schema (missing key, non-`boolean` value, or unknown key) | `storage_invalid_contents` |
| `Settings` | `save` cannot write the file | `storage_write_failed` |
| `AudioManager` | the music setter re-requests the committed value | `music_setting_unchanged` |
| `AudioManager` | the sfx setter re-requests the committed value | `sfx_setting_unchanged` |
| `AudioManager` | the music setter runs while `Music` is removed | `music_bus_missing` |
| `AudioManager` | the sfx setter runs while `SFX` is removed | `sfx_bus_missing` |

Notifications are change-only: `setting_changed(key, value)` on
`Settings`, and `music_enabled_changed(enabled)` /
`sfx_enabled_changed(enabled)` on `AudioManager`.

### Evidence

| File | Meaning |
| --- | --- |
| `evidence/boot/boot-report.json` | `schema: godot-compatibility-boot/verify-boot-v1`: every command with its exit code, every assertion, the pre/post guard digests, the switch/override contract, and the claim limits (`pass: true` only when everything passed) |

Unlike the first-render report this one carries a `generated_utc` timestamp
and the commit it was generated against, so re-running it changes the bytes;
it is regenerated evidence, not a deterministic artifact.

The project-scope test is intentionally **not** part of `verify-boot.ps1`:
it asserts that every allow-listed file — including this report — exists, so
it runs in `verify.ps1` after the report has been committed.

### Observed engine behavior (this machine)

Godot 4.7.2 never reports a refused loopback connection as `RESULT_CANT_CONNECT`;
against a closed port the request stays `STATUS_CONNECTING` and surfaces as
`RESULT_TIMEOUT` after the 30 s request timeout, even though the OS itself
refuses in ~2 s. The error state therefore names the endpoint and the timeout
(`endpoint unreachable (no response within 30 seconds): <url>`), and the
unreachable scenario costs ~30 s.

### Claim limits

Verified by this change (fresh-save corpus only):

- Boot through both implementations reaches `ready` with a summary equal to
  the committed fixture save (id, name, level, xp), the fixture game version,
  protocol `compat-v0`, and the pinned engine version.
- `legacy_v0` produces the same typed results as `fake` over loopback, and
  both failure paths — unreachable endpoint and structured API error — reach
  an explicit error state that names the failure.
- Guarded content (legacy sources, `config/`, both conversion packages, the
  three registry manifests, the committed first-render evidence, saves) is
  unchanged before and after the whole run under the guard's
  line-ending-invariant digests (`guard-baseline-v2`).

Explicitly **not** verified: gameplay parity, authentication security,
progressed-player coverage, served-byte equality for time-dependent fields,
and any Flash/Ruffle/ActionScript/browser execution (none runs; the network
is loopback only).

## Town vertical slice

The town slice renders a real legacy town in Godot without Flash: typed
town state from the existing bootstrap data, one isometric coordinate
space, the legacy terrain, saved town objects, an authoritative HUD,
selection, and a bounded camera. This section records the derived
geometry; the launch flow, visual hierarchy, slice-scene provenance,
verification commands, and claim limits are documented in the sections
that follow.

### Architecture

The view is a composition of focused parts, all reading one typed
`TownState` — presentation never sees a raw transport payload:

| Piece | Role |
| --- | --- |
| `scripts/town/town_state.gd` | fail-closed payload → typed state (eight-field placements verbatim, content resolution, resources/summary) |
| `scripts/town/iso.gd` | the single grid↔screen projection (constants below) |
| `scripts/town/town_terrain.gd` | legacy terrain over the world rectangle, resolved via ContentRegistry |
| `scripts/town/town_visuals.gd` | visual-source choice per placement (hierarchy below) |
| `scripts/town/town_object.gd` | per-placement node: metadata, footprint highlight |
| `scripts/town/town_hud.gd` | authoritative HUD values on the UI-foundation slot |
| `scripts/town/town.gd` + `scenes/town.tscn` | the view: terrain, depth-sorted objects, HUD, bounded camera, selection, fail-closed error state |
| `scripts/town/town_slice.gd` + `scenes/town_slice.tscn` | the same view over the preserved Scarlet village |
| `scripts/camera_controls.gd` | component with fail-closed optional world bounds |

`scripts/boot.gd` hands the already-validated bootstrap payload to this
stack in windowed runs — the flow below.

### Isometric projection constants

`scripts/town/iso.gd` commits the only coordinate space the town uses —
terrain, object footprints, selection hits, and camera bounds all consume
these constants (one geometry, no second source):

| Constant | Value | Meaning |
| --- | --- | --- |
| `TILE_WIDTH` | `TW=40` | tile width in world pixels (2:1 diamond) |
| `TILE_HEIGHT` | `TH=20` | tile height in world pixels |
| `GRID_EXTENT` | `100` | legacy grid: integer cells `0..99` on both axes |
| world rect | `4000x2000` | `Iso.world_rect()`; also the terrain rectangle |

**Derivation** (design D2; executed with committed data, no Flash and no
bytecode interpretation):

1. *Scale anchor from converted art* — the only size evidence tying pixels
   to cells is the converted package frames against content footprints:
   House I's frame (216x144) on a 2x2 footprint and Wild Elephant's frame
   (171x191) on a 1x1 footprint bound the candidate family; the 90x90
   thumbnails are fixed-size UI art and were excluded from scale selection.
2. *Viewable-town criterion* — at the legacy stage size 1400x600 a `TW=40`
   view spans 35x30 cells, which contains 29 of the 40 fresh-save
   placements (the densest such window), while thumbnails sit near their
   natural size against 2x2 footprints (80 px) and converted sprites stay
   at authentic native bounds (overhang over the footprint is accepted and
   recorded as provisional presentation; sprites are never scaled).
3. *Land-fit validation of alignment and orientation* — `mapa1.jpg`
   (701x514, resolved through ContentRegistry as `mapa1.jpg`, status
   `passthrough`) is classified land/water by blue-dominance (water iff
   `b8 - max(r8,g8) > 18`), and every placement's **saved-cell anchor** —
   the center of its 1x1 footprint rect — projects through the committed
   constants (pixel `int(world.x/4000*W)` truncation) into the image.
   Recorded residual: **fresh save 39/40 land** — the
   single water cell is bridge item 929 at (29,48), which lies over the
   crater lake and is semantically correct — and **Scarlet 549/576 land**,
   with the residuals concentrated at the grid's far shore/corner
   extremities plus bridge placements; **0 off-grid** in both. The check
   is scale-invariant (the terrain texture is stretched to the world
   rectangle: 5.7x horizontal, 3.9x vertical), so it validates
   alignment/orientation, not scale.

**Evidence basis:** legacy save coordinate extents (`0..99` across 20+
saves, placement format `[item, x, y, timestamp, orientation, store, attr,
player]`), content footprints (`width`/`height`), the two converted
sprite frames, the 90x90 thumbnail UI art, the Basesec stage (1400x600 at
30 fps), and the legacy client's static iso-engine identifiers
(`TILE_SIZE`, `EI_TILE_HEIGHT_PIXELS`, `core.isoengine.isoUtils`,
`gridWidth`, `gridHeight`, `numCols`, `numRows`).

**Evidence gap and status:** those ABC identifiers exist only as strings —
their numeric values were **never extracted** from the SWF bytecode. The
constants above are **derived and provisional**; pixel parity with the
legacy Flash client is not claimed, and the `x -> lower-right` orientation
is provisional presentation. Extracting `TILE_SIZE` /
`EI_TILE_HEIGHT_PIXELS` is recorded as a parity follow-up, not an
assumption.

### Launch flow: windowed boot to town

The main scene boots through `scenes/boot.tscn`: the `GameApi` facade
(fake or legacy-v0) lists saves, bootstraps exactly once, anchors the
session and game clock, and shows the summary. Windowed runs then hand the
already-validated payload to `TownState.parse` and attach
`scenes/town.tscn` (`transition_to_town`, deferred to idle so the tree is
free to attach it; a failure names itself on the boot view instead of
leaving a blank window). Headless boot keeps its exact marker and
exit-code contract — no town scene, one bootstrap request either way.

### Visual hierarchy

One placement renders through the most specific source available
(`town_visuals.gd`); authored art is never rescaled:

1. converted package sprite — authentic bounds at the saved cell
   (overhang beyond the footprint is provisional presentation);
2. keyed legacy thumbnail — scaled to the content footprint;
3. labeled footprint marker — content the package carries but no art for;
4. `?` placeholder — ids the content package does not resolve; the
   placement still renders and the town stays intact (unresolved ids are
   recorded, never dropped).

Draw order is depth `x+y` ascending with deterministic tie-breaks (depth,
grid y, grid x, save order), so every run draws identically.

### Slice-scene provenance

`scenes/town_slice.tscn` renders `villages/Scarlet.json` through the same
components as the player's town — one projection, terrain, object layer,
HUD, bounded camera, selection. The village file is read directly from
the preserved repository input (no server, no bootstrap); its path and
SHA-256 are recorded in the town report. The fresh save contains no unit
placements, so authentic unit rendering (the Wild Elephant sprite) and
that save's HUD values are proven only through this scene.

### Evidence capture (D10 three-step)

```bash
# 1. Windowed fake-API launch: boot -> town transition + player capture
#    (writes town-player.png at the legacy 1400x600 stage, exits 0)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --town-capture=<repo>/apps/client-godot/evidence/town/town-player.png

# 2. Windowed slice capture (writes town-slice.png, exits 0)
godot --path apps/client-godot res://scenes/town_slice.tscn -- --town-capture=<repo>/apps/client-godot/evidence/town/town-slice.png

# 3. Headless deterministic report (writes report.json; a rerun is
#    byte-identical; the bare --town-report flag defaults to
#    evidence/town/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --town-report=<repo>/apps/client-godot/evidence/town/report.json
```

The report records the input paths and digests, the projection constants
with their `derived-provisional` status, per-view object counts by visual
source, the observed HUD/selection/camera state, the bootstrap-request
count (exactly one), and both capture digests. It carries no timestamps
or run-varying provenance, so reruns reproduce its bytes.

### Town claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- no pixel-parity oracle against the legacy client exists;
- projection constants are derived and provisional;
- thumbnail presentation is provisional pending further conversions;
- authentic unit rendering is proven via the slice scene because the
  live fresh save contains no unit placements.

These non-claims are recorded verbatim in `evidence/town/report.json`.
Verification: the seven town suites (`test_town_iso`, `test_town_state`,
`test_town_scene`, `test_town_hud`, `test_town_selection`,
`test_town_placement`, `test_town_gate`) run inside `verify-boot.ps1`; the
scope suite enforces the 72-file boundary.

## Building placement

The placement slice (OpenSpec `building-placement`, milestone M7) closes the
loop the town render opened: a store-listed building an eligible player can
afford is picked in a build picker, previewed at an inverse-projected cell,
and placed with exactly one intent — executed on the v0 path by the unchanged
legacy `command()` dispatcher over the Compatibility API's disposable corpus.

### Flow

1. **Catalog** — `placement_catalog.gd` parses the bootstrap config payload
   already in hand (no second config request), fail-closed: entries are the
   store-listed buildings whose `min_level` ≤ the loaded level — 14 at level
   1 of the fresh save out of the 166 store-listed buildings (900 content
   items total). A parse failure leaves placement unavailable behind a named
   error; it never fails the town and never fabricates an entry.
2. **Picker** — the town's Build panel lists the entries (name, footprint,
   cost against the live resources); picking one arms the preview. Entering,
   picking, previewing, and cancelling are view operations with no request.
3. **Preview** — the pointer's world point inverse-projects to a grid cell;
   `placement_flow.gd` evaluates the target against the typed state: anchor
   in `0..99` (bounds), footprint free (occupancy), cost affordable
   (affordability). Invalid targets render marked with the reason and are
   never sent.
4. **Confirm** — exactly one `GameApi.place_building(user_id, item_id, x,
   y, orientation)` intent; only the authoritative response is applied (the
   persisted eight-field entry becomes a depth-sorted object; resources and
   XP take the response's values verbatim). A structured or transport
   failure surfaces its code and changes nothing.

### Endpoint contract and envelope derivations

`POST /v0/place` accepts only the intent `{user_id, item_id, x, y,
orientation}` — the full contract, response example, structured error codes,
validation split, and corpus-only persistence scope are documented in
`apps/compat-api/README.md`. The legacy batch envelope is derived
server-side and marked **derived-provisional** throughout: next free slot
(smallest positive integer absent from `maps[0].items`; the fresh save
occupies `1..40`, so the first placement takes `41`), the price vector
negated onto the legacy 8-slot `[unknown, xp, gold, wood, oil, steel, cash,
mana]` vector, team `1`, `unknown=0`, `reason=""`, and the placeholders
`accessToken=""`, `publishActions=[]`, `tries=1`, `first_number=0`. The
Flash client is never executed, so its exact envelope is unobservable —
these values are derived from the legacy server's own accepted input, not
observed from the client. Validation split (design D5): the client owns the
gameplay rules (grid display, occupancy, affordability) for a fail-fast
picker; the endpoint owns structural fail-closed input validity only, and
insufficient funds reproduce the legacy `max(…, 0)` clamp rather than a
rejection — authoritative server-side validation belongs to Server v1 (M13).

### Verification (commands actually executed)

```bash
# Placement fixture capture (one-shot, executed-legacy oracle): the exact
# command, exit codes, and containment are recorded in
# tests/fixtures/godot-building-placement/README.md
python -B apps/compat-api/capture_placement_fixture.py

# Placement envelope + endpoint + executed-legacy parity tests (inside the
# compat suite; observed: Ran 90 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic picker-flow suite standalone (observed: 284 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_placement.gd

# Full batteries in the final state (each embeds the placement suites and
# the placement-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_placement` suite (the
picker flow over the fake double — entry, gated offering, invalid targets
never sent, exactly one request, authoritative apply, failure paths, and a
transport-failure check against the dead endpoint) and a fourth live phase
`placement-live`, which starts the Compatibility API over a disposable
corpus, sends one intent through `POST /v0/place`, asserts the typed
response, and — via `compat_live_phase.py --expect-save-mutation` — asserts
a corpus save file actually mutated, then tears down asserting the port is
released, the corpus is removed, and no working-tree `saves/` exists.

### Evidence capture (D11 two-step)

```bash
# 1. Windowed fake-API launch: boot -> town, the picker flow confirms one
#    House I at (51, 39), then the frame is captured (writes placement.png
#    at the legacy 1400x600 stage, exits 0; a failed flow exits 1 with an
#    explicit [town] placement-capture state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --placement-capture=<repo>/apps/client-godot/evidence/placement/placement.png

# 2. Headless deterministic report (writes report.json; a rerun is
#    byte-identical — observed SHA-256 BF86CDD0B52B583F… across two
#    consecutive reruns; the bare --placement-report flag defaults to
#    evidence/placement/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --placement-report=<repo>/apps/client-godot/evidence/placement/report.json
```

The report (`schema placement-report-v1`) records the inputs and digests
(save-list and bootstrap fixtures, the executed-legacy placement fixture's
request/response/after-state, the terrain image, the committed capture), the
intent `{user_id, item_id: 1, x: 51, y: 39, orientation: 0}`, counts
before/after (placements and objects 40 → 41), resources before/after (wood
2000 → 1970, everything else unchanged), the projection constants pointer,
the bootstrap and placement request counts (exactly one each), and the
fake-capture pointer: the capture runs the fake implementation — a
deterministic test double, not a parity oracle — while real-execution parity
is established by the fixture-replay tests and the `placement-live` phase.

### Placement claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the price vector, envelope placeholders, and slot choice are derived,
  never observed from the Flash client;
- parity covers one recorded transaction against the fresh-player corpus,
  not progressed players;
- insufficient resources reproduce legacy clamping, not rejection;
- no pixel-parity oracle against the legacy client exists;
- occupancy and grid-bounds rules are derived (Flash-unobservable) and
  enforced client-side only;
- the committed capture runs the fake GameApi — a deterministic test
  double, not a parity oracle.

These non-claims are recorded verbatim in `evidence/placement/report.json`.

## Building purchase

The purchase slice (OpenSpec `building-purchase`, milestone M7) opens the other
half of the acquisition loop: a store-listed item the player can pay for in cash
is bought into the player's **storage** instead of onto the map, executed as one
typed intent by the unchanged legacy `buy_stored_item_cash` path inside
Compatibility API v0, with an executed-legacy purchase fixture as the parity
oracle. Placement still fuses payment with map placement (legacy `buy`), so both
acquisition paths coexist.

### Flow

1. **Catalog** — the same fail-closed `placement_catalog.gd` parse the picker
   already uses, handed to a second surface by the boot handoff (no second
   config request). `shop_flow.gd` filters it to store-listed entries the loaded
   level allows **and** whose config price is a cash price — 11 entries at level
   1 of the fresh save out of the 166 store-listed buildings. A missing or
   malformed catalog makes the surface unavailable behind a named error; it
   never fabricates an entry and never guesses a price.
2. **Shop surface** — its own UI-foundation slot beside the build picker
   (`Shop`, entry buttons showing the price against current cash, a status line,
   and a storage readout). Entering, picking, and cancelling are view
   operations with no request.
3. **Confirm** — exactly one `GameApi.purchase_item(user_id, item_id)` intent.
   The client owns the gameplay rules legacy never enforced: an entry whose
   price exceeds current cash is refused locally with the two numbers it
   compares and **no request is sent**; the endpoint would clamp instead, and
   server-authoritative validation belongs to Server v1 (M13).
4. **Apply** — only the authoritative response is applied: the response's
   **full** storage mapping replaces the typed storage through the same
   fail-closed parser the payload parse uses, and the HUD resources and XP take
   the response's values verbatim. A failed apply rolls every write back; a
   structured or transport failure surfaces its code and changes nothing.
5. **Storage readout** — `map["store"]` parsed into typed state: quantity `0`
   and ids the content package cannot resolve are preserved verbatim (real saves
   hold units and zeroes), a missing field is named rather than defaulted to an
   empty inventory, and a malformed field rejects the parse naming the key.

### Endpoint contract and envelope derivations

`POST /v0/purchase` accepts only the intent `{user_id, item_id}` — the full
contract, response example, structured error codes, validation split, and
corpus-only persistence scope are documented in `apps/compat-api/README.md`.
The legacy batch envelope is derived server-side and marked
**derived-provisional** throughout: the **cash-only** price (the item's config
`costs` must be exactly `{"c": <int>}`) negated onto the cash slot of the legacy
8-slot `[unknown, xp, gold, wood, oil, steel, cash, mana]` vector, one
`buy_stored_item_cash` command whose single argument is the item id, and the
placeholders `accessToken=""`, `publishActions=[]`, `tries=1`,
`first_number=0`. The Flash client is never executed, so neither the exact
envelope **nor the choice of this command for a shop purchase** is observed —
both are derived. An item priced in another resource fails closed with
`costs_not_cash`; the client never offers such an entry, and any-price storage
acquisition (`store_add_items`) is a later change.

### Verification (commands actually executed)

```bash
# Purchase fixture capture (one-shot, executed-legacy oracle): the exact
# command, exit codes, and containment are recorded in
# tests/fixtures/godot-item-purchase/README.md
python -B apps/compat-api/capture_purchase_fixture.py

# Purchase envelope + endpoint + executed-legacy parity tests (inside the
# compat suite; observed: Ran 157 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic purchase-flow suite standalone (observed: 213 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_purchase.gd

# Full batteries in the final state (each embeds the purchase suites and the
# purchase-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_purchase` suite (the shop
flow over the fake double — entry gating, exactly one request, the unaffordable
no-request case, the authoritative apply, failure rollback, catalog
fail-closed, and a transport-failure check against the dead endpoint) and a
fifth live phase `purchase-live`, which starts the Compatibility API over a
disposable corpus, sends one intent through `POST /v0/purchase`, asserts the
typed response, and — via `compat_live_phase.py --expect-save-mutation` —
asserts a corpus save file actually mutated, then tears down asserting the port
is released, the corpus is removed, and no working-tree `saves/` exists.

### Evidence capture (two-step, as the placement slice)

```bash
# 1. Windowed fake-API launch: boot -> town, the shop flow confirms one
#    Victory Arch (item 105, 5 cash), then the frame is captured (writes
#    purchase.png at the legacy 1400x600 stage, exits 0; a failed flow exits 1
#    with an explicit [town] purchase-capture state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --purchase-capture=<repo>/apps/client-godot/evidence/purchase/purchase.png

# 2. Headless deterministic report (writes report.json; a rerun is
#    byte-identical — observed SHA-256 9510BE8409FE25E3… across three
#    consecutive runs; the bare --purchase-report flag defaults to
#    evidence/purchase/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --purchase-report=<repo>/apps/client-godot/evidence/purchase/report.json
```

The report (`schema purchase-report-v1`) records the inputs and digests
(save-list and bootstrap fixtures, the executed-legacy purchase fixture's
request/response/after-state, the terrain image, the committed capture), the
intent `{user_id, item_id: 105}`, storage before/after (`{}` → `{"105": 1}`),
resources before/after (cash 5 → 0, everything else unchanged), the shop entry
count at the loaded level (11), the projection-constants pointer, the bootstrap
and purchase request counts (exactly one each), and the fake-capture pointer.

### Purchase claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the choice of `buy_stored_item_cash` and the cash-only price derivation are
  derived, never observed from the Flash client — the service therefore claims
  nothing about resource-priced storage purchases;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players;
- insufficient cash reproduces legacy clamping, not rejection, and the client
  refuses such a purchase without sending anything;
- storage is display-only here: nothing places from or sells out of storage
  (`place_stored_item` / `sell_stored_item` are the later *store* and *sell*
  deliver lines);
- no pixel-parity oracle against the legacy client exists, and the shop layout,
  entry labels, and readout are documented placeholders (no captured legacy
  shop layout exists);
- the committed capture runs the fake GameApi — a deterministic test double, not
  a parity oracle.

These non-claims are recorded verbatim in `evidence/purchase/report.json`.

## Building move

The move slice (OpenSpec `building-move`, milestone M7) makes a town the player
already owns rearrangeable: a placed building is selected, moved to a free cell,
and confirmed as one typed intent executed by the unchanged legacy `move` path
inside Compatibility API v0, with an executed-legacy move fixture as the parity
oracle. No purchase and no storage change is involved — the building is already
in the save, and a move rewrites only its coordinates.

### Flow

1. **Addressable placements** — `town_state.gd` parses each placement's legacy
   map key next to its item id, cell, and raw row, so the client can name the
   item a move targets. A key that is not a positive integer is recorded as
   having no addressable index and is **never coerced** (coercing to 0 would
   address a different row); moving such a placement is refused with an explicit
   reason.
2. **Arming** — selecting a placed building enables a `Move` action in the move
   surface's own UI-foundation slot (beside the build picker and the shop, both
   untouched). Pressing it arms the move with that building's current cell as
   the starting target.
3. **Preview** — the pointer's world point inverse-projects to a grid cell
   through the same iso projection the placement flow uses, and the existing
   footprint preview shows the footprint with the moving building's **own cells
   excluded** from occupancy. A target is marked invalid — and never sent — when
   the anchor is outside the `0..99` grid (`out_of_grid`), when the footprint
   covers another placement (`occupied`), or when it is the cell the building
   already occupies (`same_cell`).
4. **Confirm** — exactly one `GameApi.move_building(user_id, item_index, x, y)`
   intent. On success only the authoritative response is applied: the typed row
   is replaced by the response's persisted entry, the same rendered object
   repositions at the new cell and is re-sorted with the existing depth
   comparator, and HUD resources and XP take the response values. A failed
   apply rolls every write back; a structured or transport failure surfaces its
   code and moves nothing.

### Endpoint contract and envelope derivations

`POST /v0/move` accepts only the intent `{user_id, item_index, x, y}` — the
full contract, response example, structured error codes, validation split, and
corpus-only persistence scope are documented in `apps/compat-api/README.md`. The
endpoint resolves `item_index` against the save before executing (legacy's
missing-item path is a silent early return that would otherwise be reported as
success), and the legacy batch envelope is derived server-side and marked
**derived-provisional**: one `move` command with arguments
`[item_index, x, y, frame, string]`, the `frame`/`string` placeholders legacy
reads and discards, and a **neutral** all-zero resource vector, plus the shared
placeholders `accessToken=""`, `publishActions=[]`, `tries=1`,
`first_number=0`. The config records no move price anywhere (item `cost` and
`cost_type` are dead fields over all 778 items, `costs` prices the purchase
only, and no global holds a move cost), so no price is derivable and a
client-sent one is never accepted — the service claims neither that moving is
free in the legacy client nor that it costs anything. Validation split (design
D5): the client owns the gameplay rules (bounds, occupancy, no-op) and the
endpoint owns structural fail-closed input validity only; authoritative
validation belongs to Server v1 (M13). The response reuses the placement
superset shape (`result` + the persisted eight-field `placement` entry +
`resources`), so the typed result and its parser are shared with `/v0/place`.

### Verification (commands actually executed)

```bash
# Move fixture capture (one-shot, executed-legacy oracle): the exact command,
# exit codes, and containment are recorded in
# tests/fixtures/godot-building-move/README.md
python -B apps/compat-api/capture_move_fixture.py

# Move envelope + endpoint + executed-legacy parity tests (inside the compat
# suite; observed: Ran 227 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic move-flow suite standalone (observed: 288 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_move.gd

# Full batteries in the final state (each embeds the move suites and the
# move-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_move` suite (the move flow
over the fake double — arming from a selection, an unaddressable-placement
refusal, one request per confirm, every invalid-target refusal, the
authoritative apply, and transport/structured-failure rollback) and a sixth live
phase `move-live`, which starts the Compatibility API over a disposable corpus,
sends one intent through `POST /v0/move`, asserts the typed response, and — via
`compat_live_phase.py --expect-save-mutation` — asserts a corpus save file
actually mutated, then tears down asserting the port is released, the corpus is
removed, and no working-tree `saves/` exists.

### Evidence capture (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API launch: boot -> town, select the Turret I at slot 11,
#    arm the move, preview (58, 47), confirm, then capture the frame (writes
#    building-move.png at the legacy 1400x600 stage, exits 0; a failed flow
#    exits 1 with an explicit [town] move-capture state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --move-capture=<repo>/apps/client-godot/evidence/building-move/building-move.png

# 2. Headless deterministic report (writes report.json; a rerun is
#    byte-identical; the bare --move-report flag defaults to
#    evidence/building-move/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --move-report=<repo>/apps/client-godot/evidence/building-move/report.json
```

The report (`schema move-report-v1`) records the inputs and digests, the intent
`{user_id, item_index: 11, x: 58, y: 47}`, the moved building (Turret I, slot
11) with its cell `(58, 48)` → `(58, 47)` and its row before and after, counts
before/after (40 placements and objects — a move never changes how many
buildings a town has), resources before/after (unchanged), the
projection-constants pointer, the bootstrap and move request counts (exactly one
each), and the fake-capture pointer.

### Move claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the move command's argument values, the `frame`/`string` arguments legacy
  discards, and the neutral price vector are derived, never observed from the
  Flash client — no claim is made about what moving costs in the legacy client;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players and no other row;
- occupancy, the no-op cell, and grid bounds are client-side display rules only;
  the endpoint enforces structural validity and there is no server-authoritative
  validation;
- an unaddressable legacy key is never coerced, so such a placement cannot be
  moved through this flow;
- no pixel-parity oracle against the legacy client exists, and the move surface's
  layout and labels are documented placeholders;
- the committed capture runs the fake GameApi — a deterministic test double, not
  a parity oracle.

These non-claims are recorded verbatim in
`evidence/building-move/report.json`.

## Building sell

The sell slice (OpenSpec `building-sell`, milestone M7) is the disposal
counterpart to the move line: a placed building the player no longer wants is
sold, executed as one typed intent by the unchanged legacy `sell` path inside
Compatibility API v0, with an executed-legacy sell fixture as the parity oracle.
Nothing is placed, nothing touches storage, and the legacy combat reason is
never reached.

### Flow

1. **Action** — the delivered selection-driven surface gains a `Sell` action
   beside `Move`, offered only while a placed building is selected **and** that
   building's legacy map key is addressable; an unaddressable key is refused
   with the same explicit reason the move flow already uses, never coerced.
2. **Confirm** — the sell confirm names the building and has no target (a sale
   occupies no grid cell). Confirming sends exactly one
   `GameApi.sell_building(user_id, item_index)` intent; cancelling sends
   nothing and leaves the town byte-identical; a pointer press that changes the
   selection while the confirm is armed is refused with no request, so a sale
   can never be silently re-targeted.
3. **Apply** — only the authoritative response is applied: the building's
   rendered object is freed, its typed placement is removed while the remaining
   buildings keep the committed depth order, and HUD resources and XP take the
   response values. The apply snapshots the placement, its index, the object,
   and the resource bag first, so any failure restores everything and the
   building stays on the map. A structured or transport failure surfaces its
   code and removes nothing.

### Endpoint contract and envelope derivations

`POST /v0/sell` accepts only the intent `{user_id, item_index}` — the full
contract, response example, structured error codes, validation split, and
corpus-only persistence scope are documented in `apps/compat-api/README.md`.
The endpoint resolves `item_index` against the save's own placements and reads
that row **before** executing (legacy's missing-item path is a silent early
return that would otherwise be reported as success), then proves afterwards
that the key is gone from the persisted save. The legacy batch envelope is
derived server-side and marked **derived-provisional**: one `sell` command with
arguments `[item_index, reason]`, the reason **derived** as the empty string
legacy compares against `"KILL"` and otherwise uses as a log label, a **neutral**
all-zero resource vector, and the shared placeholders `accessToken=""`,
`publishActions=[]`, `tries=1`, `first_number=0`. **No reason is accepted from
the client**, so the combat reason that would route a row through
`push_dead_unit` is unreachable through this surface.

**No refund is claimed.** The committed configuration records no building-sale
refund rule — item `cost` and `cost_type` are dead fields over all 778 items,
`costs` prices the purchase only, and `MARKET_SELL_PERCENTAGE` governs the
*resource* market — while the legacy refund travels only in client-sent deltas
this contract refuses. A sale therefore removes the building and changes no
balance, and refund economics belong to Server v1 (M13) and the later
*resources* deliver line.

### Verification (commands actually executed)

```bash
# Sell fixture capture (one-shot, executed-legacy oracle): the exact command,
# exit codes, and containment are recorded in
# tests/fixtures/godot-building-sell/README.md
python -B apps/compat-api/capture_sell_fixture.py

# Sell envelope + endpoint + executed-legacy parity tests (inside the compat
# suite; observed: Ran 306 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic sell-flow suite standalone (observed: 169 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_sell.gd

# Full batteries in the final state (each embeds the sell suites and the
# sell-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_sell` suite (the sell flow
over the fake double — action gating, the unaddressable refusal, one request per
confirm, cancellation, the authoritative apply, and transport/structured-failure
rollback) and a seventh live phase `sell-live`, which starts the Compatibility
API over a disposable corpus, sends one intent through `POST /v0/sell`, asserts
the typed response, and — via `compat_live_phase.py --expect-save-mutation` —
asserts a corpus save file actually mutated, then tears down asserting the port
is released, the corpus is removed, and no working-tree `saves/` exists.

### Evidence capture (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API launch: boot -> town, select the Turret I at slot 20,
#    sell, confirm, then capture the frame (writes building-sell.png at the
#    legacy 1400x600 stage, exits 0; a failed flow exits 1 with an explicit
#    [town] sell-capture state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --sell-capture=<repo>/apps/client-godot/evidence/building-sell/building-sell.png

# 2. Headless deterministic report (writes report.json; a rerun is
#    byte-identical; the bare --sell-report flag defaults to
#    evidence/building-sell/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --sell-report=<repo>/apps/client-godot/evidence/building-sell/report.json
```

The report (`schema sell-report-v1`) records the inputs and digests, the intent
`{user_id, item_index: 20}`, the sold building (Turret I, slot 20) with its row
`[22, 41, 48, 0, 0, [], {}, 1]` and cell `(41, 48)`, counts before/after (40 ->
39 placements and objects), resources before/after (unchanged), the
projection-constants pointer, the bootstrap and sell request counts (exactly one
each), and the fake-capture pointer.

### Sell claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the derived sell reason and the neutral price vector are derived, never
  observed from the Flash client;
- **no refund is claimed** — the committed configuration records no
  building-sale refund rule and the legacy refund travels in client-sent deltas
  this contract refuses, so a sale removes the building and changes no balance;
- the legacy combat `KILL` reason is never reached, because no reason is
  accepted from the client;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players;
- sellability and addressability are client-side rules only; the endpoint
  enforces structural input validity and no server-authoritative validation
  exists;
- no pixel-parity oracle against the legacy client exists, and the surface's
  layout and labels are documented placeholders;
- the committed capture runs the fake GameApi — a deterministic test double, not
  a parity oracle.

These non-claims are recorded verbatim in
`evidence/building-sell/report.json`.

## Building store

The store slice (OpenSpec `building-store`, milestone M7) closes the loop the
purchase line left open: a building the player owns can be put into their
**storage**, executed as one typed intent by the unchanged legacy `store_item`
path inside Compatibility API v0, with an executed-legacy store fixture as the
parity oracle. It is the `btPutInStorage` affordance the legacy client's
building panel already had, reproduced on the selection-driven surface this
client already has.

### Flow

1. **Action** — a `Store` action beside the delivered `Move` and `Sell`
   actions, offered only while a placed building is selected **and** addressable
   (an unaddressable legacy key is refused with the same explicit reason the
   move and sell flows use, never coerced). The three modes are mutually
   exclusive: arming one refuses the others.
2. **Confirm** — targetless, like a sale: it names the building and reports
   where it will land. Confirming sends exactly one
   `GameApi.store_building(user_id, item_index)` intent; cancelling, or a
   pointer press that changes the selection, sends nothing.
3. **Apply** — only the authoritative response is applied: the building's
   object is freed, its typed placement is removed while the remaining
   buildings keep the committed depth order, the typed storage is replaced
   through the **same fail-closed parser** the payload parse and the purchase
   apply use, the storage readout re-renders from it, and HUD resources and XP
   take the response values. The apply snapshots every field it touches first,
   so any failure restores the building, the previous storage view, the readout,
   and the HUD — a store is never half-applied.

### Endpoint contract and envelope derivations

`POST /v0/store` accepts only the intent `{user_id, item_index}` — the full
contract, response example, structured error codes, validation split, and
corpus-only persistence scope are documented in `apps/compat-api/README.md`.
The endpoint resolves the index against the save and reads the row **before**
executing, then proves afterwards that the row is gone and the storage entry
landed. The legacy batch envelope is derived server-side and marked
**derived-provisional**: one `store_item` command whose single argument is the
item index, a **neutral** all-zero resource vector, and the shared placeholders
`accessToken=""`, `publishActions=[]`, `tries=1`, `first_number=0`. The
response carries both sides of the move — the pre-execution eight-field
`removed` row and the full post-execution `store` mapping — so the client needs
no arithmetic for pre-existing contents.

**No storing cost and no capacity rule are claimed**: the committed
configuration records no price for storing (item `cost`/`cost_type` are dead
fields, `costs` prices the purchase only) and the legacy server performs no
capacity check. Validation split (design D5): the client owns the gameplay
rules and the endpoint owns structural fail-closed input validity only;
authoritative validation belongs to Server v1 (M13). The legacy branch does not
write the bought-units list, and this line reproduces that exactly.

### Verification (commands actually executed)

```bash
# Store fixture capture (one-shot, executed-legacy oracle): the exact command,
# exit codes, and containment are recorded in
# tests/fixtures/godot-building-store/README.md
python -B apps/compat-api/capture_store_fixture.py

# Store envelope + endpoint + executed-legacy parity tests (inside the compat
# suite; observed: Ran 390 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic store-flow suite standalone
godot --headless --path apps/client-godot --script res://tests/test_town_store.gd

# Full batteries in the final state (each embeds the store suite and the
# store-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_store` suite and an eighth
live phase `store-live`, which starts the Compatibility API over a disposable
corpus, sends one intent through `POST /v0/store`, asserts the typed response,
and — via `compat_live_phase.py --expect-save-mutation` — asserts a corpus save
file actually mutated, then tears down asserting the port is released, the
corpus is removed, and no working-tree `saves/` exists.

### Evidence capture (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API launch: boot → town, select the Tree at slot 2, store,
#    confirm, then capture the frame (writes building-store.png at the legacy
#    1400x600 stage; a failed flow exits 1 with an explicit [town]
#    store-capture state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --store-capture=<repo>/apps/client-godot/evidence/building-store/building-store.png

# 2. Headless deterministic report (writes report.json; a rerun is
#    byte-identical; the bare --store-report flag defaults to
#    evidence/building-store/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --store-report=<repo>/apps/client-godot/evidence/building-store/report.json
```

The report (`schema store-report-v1`) records the inputs and digests, the
intent `{user_id, item_index: 2}`, the stored building (Tree, slot 2) with its
row `[905, 53, 39, 0, 0, [], {}, 1]` and cell `(53, 39)`, the storage mapping
before/after (`{}` to `{"905": 1}`) and its readout line, counts before/after
(40 to 39 placements and objects), resources before/after (unchanged), the
projection-constants pointer, the bootstrap and store request counts (exactly
one each), and the fake-capture pointer.

### Store claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the command's argument value and the neutral price vector are derived, never
  observed from the Flash client;
- **no storing cost and no capacity rule are claimed** — the committed
  configuration records neither and the legacy server has no capacity check;
- the bought-units list is deliberately not written by the legacy branch, and
  this line does not change that;
- this line only moves a building *into* storage, so stored items are **not yet
  playable**: `place_stored_item` (storage to map) and `sell_stored_item` remain
  open legacy commands;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players;
- storability and addressability are client-side rules only; the endpoint
  enforces structural input validity and no server-authoritative validation
  exists;
- no pixel-parity oracle against the legacy client exists, and the surface's
  layout and labels are documented placeholders;
- the committed capture runs the fake GameApi — a deterministic test double, not
  a parity oracle.

These non-claims are recorded verbatim in
`evidence/building-store/report.json`.

## Building upgrade

The upgrade slice (OpenSpec `building-upgrade`, milestone M7) is the first line
in this family whose legacy contract was **established by investigation** before
any code was written. It is also the only one that sends **two** legacy commands
for one player action: the dispatcher has no upgrade command, so an upgrade is a
`sell` with the committed `UPGR` reason followed by a `buy` of the next tier that
reuses the same map key and cell.

### Flow

1. **Action** - an `Upgrade` action beside the delivered `Move`, `Sell`, and
   `Store` actions, offered only while a placed building is selected, addressable,
   **and** has a resolvable next tier in the typed catalog; the four modes are
   mutually exclusive. A building with no upgrade path (a Tree, a Bridge) shows
   the action disabled and any attempt is refused with an explicit reason.
2. **Confirm** - names the current tier and the target tier. Confirming sends
   exactly one `GameApi.upgrade_building(user_id, item_index)` intent; cancelling,
   or a pointer press that changes the selection, sends nothing.
3. **Apply** - only the authoritative response is applied: the **same object**
   now carrying the target tier at the **same cell and key**, in the same depth
   position, with the typed row replaced by the response's post-execution row and
   HUD resources and XP taken from the response. The storage view and readout are
   left untouched. The apply snapshots everything it touches first, and it even
   refuses **before** any mutation if a response ever moved the building, which
   this contract never does.

### Endpoint contract, envelope, and provenance

`POST /v0/upgrade` accepts only the intent `{user_id, item_index}` - the full
contract, response example, structured error codes, validation split, and
corpus-only persistence scope are documented in `apps/compat-api/README.md`. The
endpoint derives everything else: the target tier from the committed
`upgrades_to` reference, the reason from `constants.py:970`
`SELL_REASON_UPGRADE = "UPGR"`, and the cell, orientation, and player from the row
being replaced; both commands carry a **neutral** resource vector.

*Established from committed legacy source and executed-legacy capture:* there is no
`upgrade` command among the 63 named branches; the `UPGR` constant; `buy` taking a
**client-supplied** map key and cell (`command.py:42-58` -> `map_add_item`); the
fresh row `map_add_item` writes (a new wall-clock `timestamp`, `store: []`, and the
`{"nc": 0}` construction seed for items with `clicks_to_build > 0`); the
`bought_unit_add` record, which appends the tier only when it is not already listed
(`engine.py:86-89`); that the order is forced; and the resulting state.

*Derived, never observed from the Flash client:* that the client sends exactly this
pair; the buy half's `orientation`, `playerID`, `unknown`, and `reason` arguments;
and the price vector.

*Why the endpoint proves the post-state:* legacy answers `{"result":"success"}`
for the **reverse** order too, and that batch leaves the key absent (40 -> 39
placements). The service therefore requires three facts before reporting success -
the key still exists, its item id equals the derived target tier, and its cell
equals the pre-execution cell - and fails closed otherwise.

### Verification (commands actually executed)

```bash
# Upgrade fixture capture (one-shot, executed-legacy oracle; the request carries
# the two-command batch): the exact command, exit codes, containment, and the
# reverse-order negative oracle are recorded in
# tests/fixtures/godot-building-upgrade/README.md
python -B apps/compat-api/capture_upgrade_fixture.py

# Upgrade envelope + endpoint + executed-legacy parity tests (inside the compat
# suite; observed: Ran 491 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic upgrade-flow suite standalone (observed: 272 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_upgrade.gd

# Full batteries in the final state (each embeds the upgrade suite and the
# upgrade-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_upgrade` suite and a ninth live
phase `upgrade-live`, which starts the Compatibility API over a disposable corpus,
sends one intent through `POST /v0/upgrade`, asserts the typed response **and that
the response reuses the pre-request key and cell**, asserts via
`compat_live_phase.py --expect-save-mutation` that a corpus save file actually
mutated, then tears down asserting the port is released, the corpus is removed, and
no working-tree `saves/` exists.

### Evidence capture (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API launch: boot -> town, select the Wall I at slot 12,
#    upgrade, confirm, then capture the frame (writes building-upgrade.png at the
#    legacy 1400x600 stage; a failed flow exits 1 with an explicit [town]
#    upgrade-capture state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --upgrade-capture=<repo>/apps/client-godot/evidence/building-upgrade/building-upgrade.png

# 2. Headless deterministic report (writes report.json; a rerun is
#    byte-identical; the bare --upgrade-report flag defaults to
#    evidence/building-upgrade/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --upgrade-report=<repo>/apps/client-godot/evidence/building-upgrade/report.json
```

The report (`schema upgrade-report-v1`) records the inputs and digests, the intent
`{user_id, item_index: 12}`, the upgrade (Wall I `23` -> Wall II `24`, slot 12, cell
`(45, 49)` before and after, both rows), the bought-units change (`[]` -> `[24]`,
with a note that the list is not carried by the typed state), counts before/after
(40 -> 40 placements and objects - the key is reused), resources before/after
(unchanged), the **established-versus-derived provenance split** as its own
section, the projection-constants pointer, the bootstrap and upgrade request counts
(exactly one each), and ten non-claims.

### Upgrade claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the composed two-command pair is **derived** - that the Flash client sends
  exactly this batch is never observed - while its shape, reason, ordering, and
  result are **established** by committed source and executed-legacy capture;
- **no upgrade cost is claimed**: the config prices no upgrade, both commands carry
  the neutral derived vector, and the 139 `premium_upgrade_costs` entries (the
  premium path) are not used;
- the `{"nc": 0}` construction counter the purchase half seeds is reported but
  deliberately **not consumed** - the construction timers belong to the next M7
  deliver line;
- the legacy client's **level gate**, **daily-upgrade limit**, and **space check**
  are known to exist (static SWF text and fields) and are deliberately **not
  implemented** here; the level gate in particular cannot be enforced on the
  committed corpus, where `maps[0].level` is 1 and no *placed* building's next tier
  is reachable at that level, and enforcing it would make this line unreachable on
  the corpus the project preserves;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players;
- upgradability and addressability are client-side rules only; the endpoint
  enforces structural input validity and the post-state proof, and no
  server-authoritative validation exists;
- no pixel-parity oracle against the legacy client exists, and the surface's
  layout and labels are documented placeholders (the panel is the delivered shared
  presentation, so long tier names clip at its right edge);
- the committed capture runs the fake GameApi - a deterministic test double, not a
  parity oracle.

These non-claims are recorded verbatim in
`evidence/building-upgrade/report.json`.
Remaining deliver lines of M7 (separate changes): construction timers, collect
income, town expansion, resources, and XP.
