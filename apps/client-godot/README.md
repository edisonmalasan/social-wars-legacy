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
loopback smoke → the headless Godot suites (one per delivered line; the count
and the list live in `verify-boot.ps1`, and each line's own section below records
what *it* added) → the unreachable-endpoint scenario against a port with nothing
listening → the live phases (one per state-mutating deliver line, each against
the real Compatibility API) → guard baseline again →
`evidence/boot/boot-report.json`. Each
live phase is wrapped
by `compat_live_phase.py`, which starts `apps/compat-api/run.py`, waits for
`GET /v0/session`, runs exactly one Godot command, stops the service with
`CTRL_BREAK`, and asserts the service exited 0, the disposable corpus was
removed, no new `socialwars-compat-*` directory is left in temp, no
working-tree `saves/` exists, and the port is released. Every
save-mutating phase additionally passes
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
- storage is display-only *here*: this line moves an item **into** storage and
  nothing more. Placing from and selling out of storage are the separate
  `godot-stored-item-placement` deliver line, which is **delivered** — see
  "Stored-item placement" below;
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
- this line only moves a building *into* storage, so at the time of this line
  stored items were **not yet playable**: `place_stored_item` (storage to map)
  and `sell_stored_item` were open legacy commands. Both are **now delivered** by
  `godot-stored-item-placement` (see "Stored-item placement" below), and that
  line's `godot-building-store` carve-out is the only thing this bullet still
  constrains: nothing here renders a storage row as placeable, and nothing here
  was changed to make it so;
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

## Building construction

The construction slice (OpenSpec `building-construction`, milestone M7) closes the
loop the placement and upgrade lines left open: a purchased or upgraded building
arrives **under construction** - `engine.map_add_item` seeds
`attr = {"nc": 0}` for any player-owned item whose committed `clicks_to_build` is
greater than zero - and until now the client rendered that fact and then ignored
it forever. This line starts a build, records build clicks, completes a build,
and shows the progress and the countdown. Like the upgrade line, its contract was
established by investigation first; the record is committed as
`docs/legacy-construction-timing.md`.

### Flow

1. **Action** - a `Build` action beside the delivered `Move`, `Sell`, `Store`, and
   `Upgrade` actions, offered only while a placed building is selected and
   addressable; the five modes are mutually exclusive.
2. **Confirm** - one primary step, and which step it is follows the row's own
   state: no construction state -> `Start build` (the countdown is derived from
   the item's committed build time and shown); a click counter below the item's
   requirement -> `Add build click (n / required)`; a counter that has reached it
   -> `Complete build`; a countdown running with the counter already consumed ->
   nothing to do. Cancelling sends nothing, and **no step anywhere clears the
   building's construction state** - the one legacy command that would also
   destroys the click counter and any friend-assistance state, so it is never sent.
3. **Apply** - only the authoritative response is applied: the typed row is
   replaced by the response's post-execution row, the same object is retained in
   depth order, and the construction readout and HUD take the response values. The
   apply snapshots everything it touches first and rolls all of it back on failure.
4. **Readout** - any selected placement carrying construction state shows its
   click progress against the item's committed click requirement and, when a
   countdown is recorded, its remaining time derived from that countdown and the
   row's recorded start instant.

### Endpoint contract, envelope, and provenance

`POST /v0/construction` accepts only the intent
`{user_id, item_index, action}` with `action` in `{start, click, finish}` - the
full contract, response example, structured error codes, per-action
post-execution proof, validation split, and corpus-only persistence scope are
documented in `apps/compat-api/README.md`. The endpoint derives the legacy command
and every argument: a `start` derives its countdown from the item's committed
`build_time`, so **no client value can influence it**; a missing, non-integer, or
non-positive committed build time fails closed rather than being coerced. Each
action carries a neutral derived vector and a per-action post-condition the service
proves before it reports success.

*Established from committed legacy source and executed-legacy capture:* the three
commands' argument shapes and effects; that they write only the row's timestamp and
attribute bag; that the click counter is seeded by the **purchase** half; the
countdown's recorded shape; and that **no server-side completion rule exists** - no
branch compares the counter with the item's click requirement.

*Derived, never observed from the Flash client:* that a real construction sends
these commands, and that the duration is the item's committed `build_time` rather
than its `activation` field or a speedup-adjusted figure.

*Why the post-execution proof is load-bearing:* the upgrade line established that
legacy answers `{"result":"success"}` for a batch that destroys the row, so a
success status is not by itself evidence that a construction step did what it
promised.

### Verification (commands actually executed)

```bash
# Construction fixture capture (one-shot, executed-legacy oracle): the exact
# command, exit codes, containment, and why the completing command is recorded
# but not captured are in tests/fixtures/godot-building-construction/README.md
python -B apps/compat-api/capture_construction_fixture.py

# Construction envelope + endpoint + executed-legacy parity tests (inside the
# compat suite; observed: Ran 616 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic construction-flow suite standalone (observed: 363 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_construction.gd

# Full batteries in the final state (each embeds the construction suite and the
# construction-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_construction` suite and a tenth
live phase `construction-live`, which starts the Compatibility API over a
disposable corpus, walks one row through `start`, `click`, and `finish` against
`POST /v0/construction`, asserts each typed response and its post-condition,
asserts via `compat_live_phase.py --expect-save-mutation` that a corpus save file
actually mutated, then tears down asserting the port is released, the corpus is
removed, and no working-tree `saves/` exists.

### Evidence capture (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API launch: boot -> town, select the Turret I at slot 11,
#    build, and confirm each step in turn, then capture the frame (writes
#    building-construction.png at the legacy 1400x600 stage; a failed flow exits
#    1 with an explicit [town] construction-capture state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --construction-capture=<repo>/apps/client-godot/evidence/building-construction/building-construction.png

# 2. Headless deterministic report (writes report.json; a rerun is
#    byte-identical; the bare --construction-report flag defaults to
#    evidence/building-construction/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --construction-report=<repo>/apps/client-godot/evidence/building-construction/report.json
```

The report (`schema construction-report-v1`) records the inputs and digests, the
intent and its resolved action, the derived duration and the committed field it
came from (`build_time`), both rows, the click counter, the countdown and the
displayed remaining time, the step offered after each action, counts and resources
before/after (unchanged), the **established-versus-derived provenance split** as its
own section, the bootstrap and construction request counts, and the non-claims.

### Construction claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the three commands and the start duration are **derived** - never observed from
  the Flash client - while their shapes, effects, and recorded result are
  **established** by committed source and executed-legacy capture;
- **no building cost is claimed**: every action carries the neutral derived vector,
  no configuration field prices a build, and the speedup prices
  (`BUILD_SPEEDUP_PRICING`, `BUILD_SPEEDUP_MIN_TIME`, `UPGRADE_SPEEDUP_PRICING`) are
  out of scope;
- the click threshold and the remaining time are **client-side derivations** with no
  server enforcement, and the steps are player-triggered; nothing is claimed about
  the legacy client's automatic construction loop;
- the fixture's completing command is **recorded but not captured** - its effect
  rests on the earlier investigation probe plus the endpoint's `finish`
  post-execution proof;
- **friend assistance is out of scope**: no friend can be hired or finished here,
  and the `attr["si"]` bag is never written by this contract;
- the legacy command that clears the whole attribute bag is never used as a cancel,
  and this flow offers no cancel at all;
- a row whose recorded countdown is running with the counter consumed is
  **indistinguishable from a freshly started build** - the row itself cannot tell
  them apart - so the flow records what it completed in-session and offers no step;
  after a view rebuild a finished build can be clicked again, which is what the
  legacy `add_click` command permits whenever the counter is absent;
- the `no_build_time` refusal is exercised through an in-memory row, because no
  placed building in the committed corpus has a non-positive committed build time;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players;
- buildability and addressability are client-side rules only; the endpoint enforces
  structural input validity and the per-action proof, and no server-authoritative
  validation exists;
- no pixel-parity oracle against the legacy client exists, and the surface's layout
  and labels are documented placeholders (the panel is the delivered shared
  presentation, so long labels clip at its right edge);
- the committed capture runs the fake GameApi - a deterministic test double, not a
  parity oracle.

These non-claims are recorded verbatim in
`evidence/building-construction/report.json`.

## Building collection

The collection slice (OpenSpec `building-collect`, milestone M7) closes the loop:
every delivered line derives a **neutral** resource vector on purpose, because the
committed configuration records no price for building, buying, moving, selling,
storing, upgrading, or starting a build. This is the first line whose vector is
**derived from committed content** - the amount, resource, experience, and the
four-rung ladder all come from the config - so a town finally produces something.

### Flow

1. **Readout** - a selected income-bearing building shows what its next collection
   would yield, which resource it would be paid in, the committed rungs, and how
   long until the next one. The countdown is computed against the **response's**
   reference instant, not a local clock, so it is stable and reviewable.
2. **Action** - a `Collect` action beside the delivered `Move`, `Sell`, `Store`,
   `Upgrade`, and `Build` actions, offered only for a selected addressable
   building with committed income that has reached a rung; the six modes are
   mutually exclusive.
3. **Confirm** - names the **derived** payout, labelled as derived rather than
   authoritative, and sends exactly one `GameApi.collect_income(user_id,
   item_index)` intent. Cancelling sends nothing.
4. **Apply** - only the authoritative response is applied: the typed row is
   replaced from the response's post-execution row, the same object is retained in
   depth order, and the HUD balances, experience, and readout are taken **from the
   response** - if the client's own arithmetic disagrees with the server's payout,
   the server's numbers win and the client's are discarded rather than added. The
   apply snapshots everything it touches first and rolls all of it back on failure.

### Endpoint contract, derivation, and provenance

`POST /v0/collect` accepts only the intent `{user_id, item_index}` - the full
contract, response example, the five 409 refusals, the two-part post-execution
proof, and corpus-only persistence are documented in `apps/compat-api/README.md`.
The service derives the payout from the item's committed `collect`,
`collect_type`, and `collect_xp`, scaled by the committed
`COLLECT_MINUTES` / `COLLECT_MULTIPLIER` rung the row has reached.

*One conversion matters:* the committed ladder is in **minutes** while both row
instants are Unix **seconds**, so the comparison goes through a single named
constant (300 / 3 600 / 14 400 / 28 800 seconds) with every boundary covered from
both sides. Comparing the units directly would pay the top rung within five
seconds - that bug was found and corrected during implementation.

*Established:* `collect` writes only the collection instant, the vector is applied
verbatim per resource under the documented clamp, and a collection on a
just-started construction overwrites the build's start instant while the countdown
survives, with the legacy server answering success. *Derived, never observed from
the Flash client - all six:* the amount formula, the experience scaling, the
sub-first-rung refusal, the cap refusal, the shared-field refusal, and the
cash/experience mapping.

### Verification (commands actually executed)

```bash
# Collect fixture capture (one-shot, executed-legacy oracle): the exact command,
# exit codes, containment, both recorded probes, and the six derived decisions
# are in tests/fixtures/godot-building-collect/README.md
python -B apps/compat-api/capture_collect_fixture.py

# Collect envelope + endpoint + executed-legacy parity tests (inside the compat
# suite; observed: Ran 768 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic collection-flow suite standalone (observed: 379 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_collect.gd

# Full batteries in the final state (each embeds the collect suite and the
# collect-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_collect` suite and an eleventh
live phase `collect-live`, which starts the Compatibility API over a disposable
corpus, drives one content-derived collection against `POST /v0/collect`, asserts
the typed response and its value-level post-state proof, asserts that a refused
collection left a construction's timers untouched, asserts via
`compat_live_phase.py --expect-save-mutation` that a corpus save file actually
mutated, then tears down asserting the port is released, the corpus is removed,
and no working-tree `saves/` exists.

### Evidence capture (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API launch: boot -> town, select the Tree at slot 2, collect,
#    confirm, then capture the frame (writes building-collect.png at the legacy
#    1400x600 stage; a failed flow exits 1 with an explicit [town] collect-capture
#    state=error marker)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --collect-capture=<repo>/apps/client-godot/evidence/building-collect/building-collect.png

# 2. Headless deterministic report (writes report.json; a rerun is byte-identical;
#    the bare --collect-report flag defaults to
#    evidence/building-collect/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --collect-report=<repo>/apps/client-godot/evidence/building-collect/report.json
```

The report (`schema collect-report-v1`) records the inputs and digests, the intent,
both rows, the derived payout and the rung it came from, the committed ladder **in
both minutes and seconds**, the next-rung countdown against the response's
reference instant, the resource movement before/after, the
established-versus-derived provenance split as its own section, the bootstrap and
collect request counts, and the non-claims.

### Collection claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- **every payout number is derived**, never observed: the claim is that a payout
  grows in four committed rungs derived from the item's committed income fields,
  never any specific amount the legacy client pays;
- the **clamp is never exercised** by the fixture, because a derived payout never
  drives a balance below zero;
- the corpus's only income-bearing rows are **decorations** - the Tree and the
  tree clusters - because the real factories are not placed, so the fixture
  exercises a decoration's payout, not a factory's;
- **no cap semantics are implemented**: an item with a non-zero committed cap is
  refused rather than paid under a guessed reading of the cap;
- a collection is **refused on a row under construction, in both layers** - the
  client offers no action and the service fails closed - because executing one
  overwrites the build's start instant while the countdown survives; the legacy
  client's own behavior is still unobserved;
- below the first committed rung no collection is offered and none is executed, so
  no sub-rung amount is ever derived;
- the unobservable resource-type refusal is covered at the helper and double level
  rather than through the town view, because the committed package records only
  the five known types;
- the lower ladder rungs are covered at the pure-helper level; a live wall clock
  only ever reaches the top rung on this corpus, since every row has never been
  collected;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players;
- collectability and addressability are client-side rules only; the endpoint
  enforces structural input validity, the content refusals, and the two-part
  proof, and no server-authoritative validation exists;
- no pixel-parity oracle against the legacy client exists, and the surface's
  layout and labels are documented placeholders;
- the committed capture runs the fake GameApi - a deterministic test double, not
  a parity oracle.

## Town expansion

The expansion slice (OpenSpec `building-expand`, milestone M7) delivers the
**unlock ledger**: read the committed expansion schedule, refuse what the evidence
does not support, send one intent, and prove the committed list grew by exactly the
sent id.

### Flow

1. **Readout** - the committed schedule summary, the player's owned expansion ids,
   and the next purchasable entry with its derived cost and affordability.
2. **Action** - an `Expand` action mutually exclusive with the delivered `Move`,
   `Sell`, `Store`, `Upgrade`, `Build`, and `Collect` modes. It lives in its own
   UI-foundation slot rather than as a seventh button in the building panel:
   an expansion names **no placement**, so a building-targeted row would imply a
   target that does not exist.
3. **Confirm** - names the **derived** debit, labelled as derived, and sends
   exactly one `GameApi.expand_town(user_id, expansion_id)` intent. Cancelling
   sends nothing.
4. **Apply** - only the authoritative response is applied: the owned list and the
   HUD balances come **from the response**, and if the client's own arithmetic
   disagrees the server's numbers win. The apply also **fails closed** when the
   client's ledger view differs from the service's, leaving the state
   byte-identical.

### The schedule the readout mirrors

`expansion_prices` is **98 positional entries with no stable id** - the index *is*
the id, range 0..97. **Only indexes 0..3 are purchasable**, because 94 of 98 rows
record a positive `neighbors` or `inventory_qte` requirement that nothing the
delivered stack can evaluate. All four ids the corpus owns (`35, 36, 45, 46`) are
in that refused set, so they read as **owned and not repurchasable** rather than as
offered. A row priced `coins C, cash K` derives the debit
`[0, 0, -C, 0, 0, 0, -K, 0]`; six of the eight slots are always zero.

### The land gap

**No terrain, grid, buildable-cell, or placement-bound behavior is claimed or
implemented.** The committed evidence establishes the *vocabulary* - the SWF
symbols `PopupExpandMC` and `btnBuyExpandTileMC` and `expansion.png` show an
expansion is a purchasable **tile**, and `expansion_gold.jpg` /
`expansion_cash.jpg` are its two price components - but nothing preserved maps a
tile to a cell, because the committed SWF inspection is symbols-and-tags only and
its own scope statement disclaims timeline semantics, script behavior, and
rendering. **Closing that gap requires new evidence, not a derivation.** The
absence is asserted at runtime (placements, objects, draw order, and cells are
byte-identical after an expansion) and by a structural token scan.

### Verification (commands actually executed)

```bash
# Expand fixture capture (one-shot, executed-legacy oracle): the exact command,
# exit codes, containment, the three recorded probes, and the four resolved
# decisions are in tests/fixtures/godot-building-expand/README.md
python -B apps/compat-api/capture_expand_fixture.py

# Expand envelope + endpoint + executed-legacy parity tests (inside the compat
# suite; observed: Ran 947 tests ... OK, exit 0)
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v

# The hermetic expansion-flow suite standalone (observed: 615 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_expand.gd

# Full batteries in the final state (each embeds the expand suite and the
# expand-live phase; both observed exit 0)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

`verify-boot.ps1` includes the hermetic `test_town_expand` suite and a twelfth live
phase `expand-live`, which starts the Compatibility API over a disposable corpus,
drives one expansion against `POST /v0/expand`, asserts the typed response and its
**two-part** post-state proof, asserts that a refused expansion left the corpus
byte-identical, asserts via `compat_live_phase.py --expect-save-mutation` that a
corpus save file actually mutated, then tears down asserting the port is released,
the corpus is removed, and no working-tree `saves/` exists.

### Evidence capture (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API launch: boot -> town -> expand -> confirm, then capture
#    the frame (writes building-expand.png at the legacy 1400x600 stage)
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --expand-capture=<repo>/apps/client-godot/evidence/building-expand/building-expand.png

# 2. Headless deterministic report (writes report.json; a rerun is byte-identical;
#    the bare --expand-report flag defaults to
#    evidence/building-expand/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --expand-report=<repo>/apps/client-godot/evidence/building-expand/report.json
```

The report (`schema expand-report-v1`) records the inputs and digests, the intent,
both owned lists, the derived debit, the committed schedule row used, the schedule
summary, the established-versus-derived provenance split as its own section, the
request counts, and the non-claims.

### Expansion claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- **the id-space indexing is derived**, never observed: the legacy server accepted
  `expand(999)`, a duplicate, and `expand(-1)` alike, so it cannot arbitrate. The
  claim is that the debit is the one the committed positional table assigns to that
  id, never the price a coherent player pays. The corpus's own four owned ids are
  recorded as incoherent under the chosen schedule and tolerated verbatim;
- **the delivered transaction is a zero-cost expansion**: 94 of 98 rows are
  requirement-blocked and every id the corpus owns is among them, so the derived
  debit is the all-zero vector and **no balance moves**. The value-level proof is
  therefore the strictest form but the least discriminating about a non-zero price,
  and the priced path and the affordability refusal are covered only through
  stubbed schedule rows;
- **no land, grid, buildable-cell, or placement-bound behavior** - see the land gap
  above;
- the clamp is **not exercised** by this fixture, and the endpoint refuses an
  insufficient balance rather than absorbing it;
- parity covers one recorded transaction against the fresh-player corpus, not
  progressed players;
- expandability and addressability are client-side rules only; the endpoint
  enforces structural input validity, the two guards, the requirements and
  affordability refusals, and the two-part proof, and no server-authoritative
  validation exists;
- no pixel-parity oracle against the legacy client exists, and the presentation is
  the delivered provisional convention;
- the committed capture runs the fake GameApi - a deterministic test double, not a
  parity oracle.

## Resource readout

The resource slice (OpenSpec `building-resources`, milestone M7) fixes the other half of
what every earlier line proves. Those lines move resources correctly **server-side** —
the unchanged legacy `apply_resources` applies the 8-slot vector verbatim per resource
under the documented clamp, collect derives its payout from committed content, and
expand derives its debit and proves the balances by value. This line makes them
**readable**, and it found that the primary currency was not.

### The defect

`town_hud.gd` keyed its first resource row **`coins`, a field nothing produces**. The
server's field is `gold` (`maps[0]` has `gold` and no `coins`), and the Compatibility
API's only occurrences of the word are *comments about the expansion price schedule*.
Because the readout is fail-closed by design and renders an explicit
`[missing: <field>]` indicator, **the player's primary currency was displayed as missing
and its real value never appeared on screen.** The existing HUD suite *pinned* the
defect by supplying `"coins": "2000"` and `"energy": "50"` in a crafted payload shape
nothing real produces.

The fix is minimal because the table was never mis-shaped: its own header named the
intended set as "coins, wood, steel, oil, cash, energy, mana", which is exactly its
ten-row shape (seven resource rows plus `name`, `level`, `xp`). **One key was
misnamed.** No row was added, removed, or reordered.

### The projection

`scripts/town/resource_projection.gd` is the single source of truth: one entry per
displayed row carrying its canonical name **as the server names it**, its save
location, its group, its label, its typed-state field, and its legacy vector slot. The
readout projects through it, so a row can neither claim a field the server does not
produce nor display the same resource twice.

| Row | Canonical name | Save location | Group | Vector slot |
| --- | --- | --- | --- | --- |
| 0 | `gold` | `map.gold` | resources | 2 |
| 1 | `wood` | `map.wood` | resources | 3 |
| 2 | `steel` | `map.steel` | resources | 5 |
| 3 | `oil` | `map.oil` | resources | 4 |
| 4 | `cash` | `playerInfo.cash` | resources | 6 |
| 5 | `energy` | `privateState.energy` | resources | none (`-1`) |
| 6 | `mana` | `privateState.mana` | resources | 7 |
| 7 | `name` | `playerInfo.name` | summary | none |
| 8 | `level` | `map.level` | summary | none |
| 9 | `xp` | `map.xp` | summary | 1 |

`xp` is grouped with the summary because it is the experience counter, not a spendable
currency — nothing spends it.

### `energy`, and the gap that stays open

`energy` is a real eighth resource in the save (`privateState.energy = 50` in the
corpus; `COST_ENERGY = "e"` at `constants.py:899`; `TOKEN_ENERGY = 7`;
`CAT_ENERGY = 8`) and `items[].costs` may name it. **The change's design assumed it had
to be added to the service; Apply proved that wrong** — `TownState.RESOURCE_FIELDS`
already maps it to `privateState.energy` and the payload already carries it, so **the
Compatibility API is not modified at all**. The regeneration rule stays a recorded gap:
`apply_resources` never writes it, the eight-slot mutation vector has no slot for it,
no legacy branch touches it, and **no committed source records how it changes**.

### Verification (commands actually executed)

```bash
# The hermetic projection/readout suite (observed: 101 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_resources.gd

# The corrected HUD suite (observed: 38 checks, PASS, was 28)
godot --headless --path apps/client-godot --script res://tests/test_town_hud.gd

# Full batteries in the final state (both observed exit 0; verify-boot.ps1 now runs
# 26 hermetic suites and 12 live phases)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

### Evidence (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API capture of the readout with every row sourced
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --town-capture=<repo>/apps/client-godot/evidence/building-resources/resources.png

# 2. Headless deterministic report (bare --resources-report defaults to
#    evidence/building-resources/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --resources-report=<repo>/apps/client-godot/evidence/building-resources/report.json
```

The report (`resources-report-v1`) records the projection table from the module's own
data, the observed stored values, the input digests, the request counts, the
established-versus-derived split, and the non-claims.

### Resource readout claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- the readout claims to display **what the save stores**, never what the legacy client
  displayed, and no pixel-parity oracle against it exists;
- **no rule is claimed for how the stored energy value changes over time**;
- labels and layout are the delivered provisional convention, and the shared 300px
  panel clips long labels — a pre-existing cosmetic note;
- the market and trade counters and item-cost mapping onto the resource vocabulary are
  **out of scope** (`trade_resource`'s arguments are recorded as *read but unused*, so
  its resource movement is client-sent — the untrusted pattern collect and expand already
  refuse);
- `TownState.Resources` still declares an internal `coins` field aliasing `map.gold`;
  **no readout row is keyed by it**, and retiring that internal name is a separate
  correction;
- the report pins the projection and readout modules' digests, so editing either one
  makes it stale and it must be regenerated — the same coupling the sibling reports have;
- the committed capture runs the fake GameApi, a deterministic test double.

Two committed M6 artifacts (`evidence/town/town-player.png` and
`evidence/town/report.json`) were regenerated because the label correction invalidated
their bytes; the town report differs **only** in the two `hud` blocks.
## Level progression

The level slice (OpenSpec `building-xp`, milestone M7) is the **eleventh and final**
M7 deliver line. It closes the loop's progression: the town carries `xp` and `level`,
the readout shows both as bare numbers, and this line connects experience to a level.

### The curve, and the one decision that mattered

`config/main.json`'s `levels` has **100 entries** with `exp_required` **strictly
increasing**, no duplicates and no non-positive gap (`0, 40, 60, 100, 200, 350, 550, 800,
…` to `2016089205`). **Nothing in the legacy server reads it** — zero references across
`command.py`, `engine.py`, `sessions.py`, `server.py`, `constants.py` — so the curve is
content the client owns entirely. The legacy `level_up` branch writes
`map["level"] = new_level` from a **client integer with no range check and no XP
validation**.

Two index readings were possible and they disagree by one level. **The committed corpus
decides, and zero-based is contradicted:**

```
corpus xp = 4 | stored level = 1 | level the zero-based curve implies = 0
```

At 4 experience the zero-based curve implies level 0, while the save records level 1 —
a direct contradiction, since the curve says level 1 begins at 40 experience. **One-based**
maps level 1 to `entries[0]` (`"Slave"`, `exp_required` 0) and `4 >= 0` holds. Guessing
zero-based would shift **every** level in the game by one, invisibly, until a player saw
the wrong level name.

So the interpretation is **derived-provisional everywhere it is recorded, with the rejected
zero-based alternative retained**, and the conversion lives in **exactly one named
function per layer** — `LevelFlow.entry_index_for_level` here, mirroring
`level_envelope.entry_index_for_level` on the service side, each with a named inverse and
a round-trip assertion across all 100 entries. `town.gd` contains no curve indexing of its
own. The compat slice then confirmed it empirically: the derivation returns **level 1** for
the corpus's `xp 4`, matching the recorded level.

### The readout, and honest disagreement

The readout shows the derived level, its committed name, the stored experience, the next
threshold and the remaining experience — and an **explicit agreement or disagreement
line**. Because the recorded level comes from a client integer with no validation, it is
**unverified against the curve**, so when the two disagree the readout **names both values
and the experience that separates them**. It never silently prefers either, never
reconciles them, and never rewrites the save: with no authoritative level to apply, hiding
the conflict would be inventing authority.

`name` is a **label, not an identifier** — 44 distinct names across 100 entries, every entry
from one-based level 45 onward being `"Conqueror"`. Above the final threshold the derived
level is 100 and there is no next level, reported as `null` rather than raised.

### The guarded intent

`level_up_town(user_id)` sends exactly one intent and **no level**: the service derives
the allowed target from the stored experience, and a client-supplied level is ignored
exactly as a client-supplied amount or price is ignored elsewhere. The post-state is proved
twice — the recorded level equals the derived level **and every stored resource is
unchanged** — which forecloses vector smuggling through a command dispatched like any
other with a client-sent resource vector. This is the family's third proof form, alongside
the collect line's "moved by exactly a derived delta" and the expand line's "moved by
exactly a derived debit".

### Verification (commands actually executed)

```bash
# The hermetic progression suite (observed: 767 checks, PASS)
godot --headless --path apps/client-godot --script res://tests/test_town_xp.gd

# Full batteries in the final state (both observed exit 0; verify-boot.ps1 now runs
# 27 hermetic suites and 13 live phases)
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

The `level-up-live` phase **deliberately does not** assert a corpus save mutation: the
committed corpus already records the level the curve derives for its experience, so the
endpoint refuses `level_already_current` before the dispatcher runs and no corpus save can
change. The phase asserts the refusal, its code, its empty payload and the corpus's
byte-identity, and `verify-boot.ps1` carries a marker recording the deliberate absence. The
success path rests on the fake double and the hermetic flow over an in-memory experience.

### Evidence (two-step, as the delivered slices)

```bash
# 1. Windowed fake-API capture of the level readout
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --level-capture=<repo>/apps/client-godot/evidence/building-xp/level-up.png

# 2. Headless deterministic report (bare --xp-report defaults to
#    evidence/building-xp/report.json)
godot --headless --path apps/client-godot res://scenes/town.tscn -- --xp-report=<repo>/apps/client-godot/evidence/building-xp/report.json
```

### Level progression claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- **the level is the one the committed curve implies for the stored experience**, never one
  observed from the Flash client; the one-based index is **derived-provisional from one
  corpus data point**, with the rejected zero-based alternative quoted in the report;
- **no level reward is paid and none displayed** — `reward_type` and `reward_amount` are
  committed on every entry and consumed by no legacy branch, so paying one would invent an
  economy;
- **unit XP and tutorial progression were out of scope for M7, and the reason recorded for
  unit XP was false as a general claim** — the fresh-player corpus carries `attr["xp"]` on 0 of
  40 placed rows and holds no unit row at all, which are facts about *that* corpus, while 171
  of 12,954 placed rows across 5 of the 31 committed save documents carry it — every one of them
  a committed unit row — so the branch was always exercisable; it is now owned by
  `godot-unit-experience`, and the tutorial by `godot-tutorial`;
- the committed thresholds are **preserved verbatim**; nothing is rebalanced;
- the disagreement reporting deliberately **does not reconcile** — it surfaces the conflict;
- a **successful live level-up is unproven** (unreachable from the committed corpus); parity
  covers one recorded transaction against the fresh-player corpus, not progressed players;
- no pixel-parity oracle exists, the presentation is the delivered provisional convention,
  and the committed capture shows the refused path and runs the fake double.

**All eleven M7 deliver lines are now delivered** — placement, purchase, move, sell, store,
upgrade, construction, collect income, town expansion, resources, and level progression.

---

## Unit definitions (M8 line 1)

The first M8 deliver line, and the first M8 change that is **not** a legacy-behaviour
derivation: everything it delivers is committed content that the client already verifies.

### What is committed

`packages/game-content/normalized/units.json` is a committed, manifest-verified M3 output: a
bare list of **429 rows**, every one carrying `kind: "unit"` and `type: "u"`, a **distinct
string `legacy_id`** spanning `923`..`1431`, and **58 committed fields** — 56 on every row,
plus `breeding_order` and `sm_training_time` on 300 of 429 each. The committed
`packages/game-content/schemas/unit.schema.json` declares exactly those 58 properties and 56
required, and data and schema agree with no field in one and absent from the other.
`ContentRegistry` verifies every output's byte count and SHA-256 **before** parsing and indexes
each domain by `str(legacy_id)`, so `units` was already a loaded, verified domain before this
change.

### The model

`scripts/units/unit_definition.gd` is a static, read-only, typed `UnitDefinition` parsed from
one verified registry entry in five named field groups:

| Group | Fields |
| --- | --- |
| identity and presentation | `legacy_id`, `name`, `img_name`, `type`, `kind`, `race`, `display_order` |
| footprint and placement | `width`, `height`, `elevation`, `population`, `volume`, `max_elem_vol`, `max_frame` |
| statistics | `attack`, `defense`, `life`, `attack_interval`, `attack_range`, `velocity`, `expiration`, `best_against`, `best_against_mult` |
| economy | `costs`, `cost`, `cost_unit_cash`, `collect`, `collect_type`, `collect_xp`, `xp`, `unit_capacity` |
| training and upgrade | `training_time`, `sm_training_time`, `breeding_order`, `upgrades_to`, `syringes`, `min_level`, `activation`, `clicks_to_build`, `build_time` |

43 committed fields are typed and 15 stay reachable through the catalog's one documented
`raw_entry()` escape hatch, so a new committed content field needs no model change and nothing
is silently dropped. Parsing **fails closed** on any malformed field — the error names the
offending definition and the field and produces no definition; nothing is guessed, defaulted,
or coerced into a meaningful value. A conditionally-present or nullable field is recorded as
**absent** behind its own `has_*` flag, never as zero, so an absent field stays
distinguishable from a committed zero (the committed rows carry `committed_zero_present: 0` for
all four, so the two cases never collide).

`scripts/units/unit_catalog.gd` resolves everything **only** through `ContentRegistry`:
`build()`, `lookup()`/`find()` by the committed string legacy ID, `has()`, `count()`,
`legacy_ids()` in committed order, `find_by_name()`, `raw_entry()`, and `sprite_linkage()`. An
unloaded registry, a registry with no `units` domain, a zero-entry domain, or an enumeration
that disagrees with the registry's own `count()` all **fail closed** — never an empty catalog
presented as a loaded one.

### Two corrections the Apply stage forced

Both were errors in the change's own planning artifacts, found by executing against the
committed package rather than reading it, and both are recorded in the design:

1. **`costs` and `properties` are committed objects, not embedded-JSON strings.** Content rule
   R2 coerces them at build time, and the committed schema declares both `"type": "object"`
   (with `costs` restricting `propertyNames` to `o/s/g/w/c`). The object form is the required
   input; a JSON string is accepted only as the same transport tolerance the delivered
   `placement_catalog.gd` applies to the served bootstrap payload, and both forms fail closed
   identically. The `costs` letter vocabulary is **aliased** from `placement_catalog.gd`, never
   restated, so a unit definition cannot disagree with what the unit would actually cost.
2. **The field count is 58, not 53** (56 on every row, 2 optional). Independently re-verified
   against both the data and the schema.

### The public enumeration accessor

The registry exposed no public id enumeration, so enumerating the 429 definitions would have
required either re-reading `units.json` behind the registry's back — bypassing the digest gate
that is the whole point of the registry — or reaching into its private index. Both were
rejected. This change therefore adds a small public `ContentRegistry.legacy_ids(domain)`
accessor returning the ids of the index the registry built during its verified load, and the
catalog enumerates through it, cross-checking against the public `count()` and failing closed on
disagreement. The `godot-content-registry` "Domain indexing and lookup" requirement gains the
corresponding scenario, so it is a specified capability rather than an undocumented escape
hatch. The accessor reports the **committed index order**, not a collation of the digit strings
— the suite pins this with `units`, whose committed first id is `923` while a lexicographic
sort of the same ids would begin `1001`.

### Verification (commands actually executed)

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_definitions.gd
godot --headless --path apps/client-godot --script res://tests/test_content_registry.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
godot --headless --path apps/client-godot --script res://tests/test_scene_build.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

Observed 2026-10-01: `test_unit_definitions` **204 checks** (207 with `--report`), registered as
the 28th hermetic suite; `test_content_registry` **87 checks** (was 52, +35 for the
enumeration); `test_project_scope` **1339**; `test_scene_build` **36**; both batteries exit 0.
No new live phase: this line has no endpoint and mutates nothing.

### Evidence

`evidence/unit-definitions/report.json`, schema `unit-definitions-report-v1`, written by the
suite itself via `--report=<path>` (bare `--report` defaults to that path) so its tables are
derived from the live model and registry and cannot drift from the code they document. It
records the committed counts, the 58/56 field inventory, the legacy-ID range and distinctness,
the content fingerprint and the `units.json` manifest digest, the per-group parsed fields, the
absent-field coverage, the raw-entry escape hatch, the asset-linkage statuses, the
static/instance boundary, the established-versus-derived provenance split, and every non-claim.
Digest `f997eb2d…66d5`, byte-identical across reruns.

### Unit definitions claim limits

- no Flash, Ruffle, ActionScript, or browser executed;
- **no unit is rendered, animated, or played** by this change;
- **no unit instance, queue, production, collection, movement, animation, or behaviour is
  implemented** — each is a separate later M8 deliver line (`unit instances` → `queues` →
  `production` → `collection` → `movement` → `animations` → `basic behaviors`);
- **no gameplay semantics are attached to any parsed statistic.** `attack: 10` is a committed
  number, not a damage rule; there is deliberately no `damage()`, `can_defend()`, `speed()`,
  `lifetime()`, or `next_attack()` helper on the model or the catalog, and the suite asserts
  their absence;
- the definitions are the committed normalized rows **verbatim** — no tuning, balancing,
  scaling, rounding, or interpolation;
- **asset linkage is reported and nothing more**: whether the committed `img_name` resolves
  through the committed asset-ID registry and with which recorded status. No rendering
  correctness, no animation correctness, no visual fidelity. (424 of 429 whole references
  resolve — 419 `extracted`, 1 `converted`, 1 `missing_source`, 3 `pending`; the 5 rows naming
  a comma-joined list resolve per part, 446 of 446);
- the committed fresh-player corpus has **no unit placements at all**, so no instance behaviour
  is evidenced here and nothing in this line speaks for a placed unit;
- **no windowed capture is claimed** — this change alters nothing visual, so a capture would
  assert nothing;
- the committed `name` values are **not unique** (six are shared by two rows each), so
  `find_by_name()` returns every match and never picks one;
- the upgrade chain's committed `-1` is reproduced verbatim and the schema's "-1 and 0 mean
  none" note is **not** interpreted; the `properties` flag bag is reproduced without
  interpreting any key as a capability;
- `best_against` is a string on all 429 rows while the schema also permits an integer code, so
  the field is a variant and accepts either;
- no pixel-parity oracle exists, and the committed definitions say nothing about what the Flash
  client read.

---

## Production queues (M8 line 3)

The first M8 line that is behaviour-bearing, and the **first to own a real executed-legacy
unit fixture** — scoped by the committed investigation `docs/legacy-production-queues.md`.

### What a queue actually is

Not a collection. A production queue is **three keys in a placed row's `attr` bag** (slot 6):

| Key | Meaning | Written by |
| --- | --- | --- |
| `nu` | the **count** | `push_queue_unit`, `push_queue_unit2`, `pop_queue_unit` |
| `ts` | the **start instant** | the same three |
| `ui` | the **optional queued unit id** | `push_queue_unit2` only (the atom-fusion path) |

`pop_queue_unit` **deletes all three together** when the count reaches zero
(`engine.py:191-205`). `scripts/units/unit_queue.gd` projects exactly that as a typed
read-only `Queue` — values verbatim, an absent queue reported as **absent** (never a count of
zero paired with a zero instant), and a malformed value per key failing closed. A queued `ui`
is resolved through the registry's `units` domain, and one that does not resolve is reported
**with its recorded value intact** — never dropped, never coerced, because the id comes from a
client-supplied argument.

### What is deliberately absent, and why

**Every `attr["ts"]` use in the legacy source is a write or a deletion.** Nothing reads a
queue's start instant to evaluate elapsed time. So this line implements **no** readiness,
**no** remaining time, **no** progress ratio, and **no** completion — a queue can never be
shown to finish, because the legacy server has no rule that would finish it. That absence is
a **recorded property of the legacy contract, stated as a spec requirement**, not a missing
feature, so the `production` line inherits a named gap instead of discovering one.

Three more refusals, each stated in the spec so a later line cannot read a documented absence
as a rule:

- **No cost** — `do_command` calls `apply_resources` with the request's per-command vector
  *before* dispatch, so any queueing cost is a client-sent delta.
- **No duration semantics** — a building's `training_time` is read by no queue branch, and
  `sm_training_time` is present on only **300 of 429** units and **0 of 470** buildings, so it
  is a *soul mixer* field, not a general training duration.
- **No bound on the count** — the engine sets none, and a documented absence is not permission
  to invent a cap.

### `soulmixer_speedup`: recorded verbatim, implemented not at all

The only branch that reads `ts` back, and the legacy author's own comment on its calculation
is *"Quite useless cost calculation for understanding it"*. Recorded: it needs **both** `ts`
and `ui` (so it raises `KeyError` on a fresh row — the client **refuses** with a named error
instead), it reads the duration from the **queued unit** rather than the building, it treats
the value as **seconds** (`ceil(remaining / 3600)`), it **charges nothing** (it only *prints*
the cost), and it clears the start instant. Implemented: **no cost, no timer, no speedup**.
Reproducing a formula the legacy source itself labels useless, and which never charges
anything, would invent an economy.

### The executed-legacy fixture

The committed corpus places **id 26, Command Center, at map key 1** with `training_time` 5,
`min_level` 1`, and an **empty `attr` bag** — a real placed training producer, so `push` and
`pop` are exercisable **without fabricating a player state**. Read from the committed capture:

| Step | Command Center `attr` | Stored resources |
| --- | --- | --- |
| login | `{}` | gold 2000, wood 2000, steel 2000, oil 2000, xp 4, energy 50, mana 0 |
| **push** | `{'nu': 1, 'ts': <instant>}` | **byte-identical** |
| **pop** | `{}` — both keys removed together | **byte-identical** |

That is what makes the endpoint's *"no resource moved"* proof **non-tautological**: the
transaction really happened while no balance moved, foreclosing the client-sent
`apply_resources` path for a command that must not move a balance. The manifest records that
a push and a pop were captured, that **no completion was captured**, and that **no completion
command exists**.

### Verification (commands actually executed)

```bash
python -B apps/compat-api/capture_queue_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_unit_queues.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

Observed 2026-10-01: `test_unit_queues` **411 checks** (423 with `--report`), the 30th
hermetic suite; the **grown** compat suite `Ran 1257 tests ... OK` (from 1109, **+148** — this
line adds an endpoint); `verify-boot.ps1` exit 0 with **30 hermetic suites and 14 live
phases**, guard digest identical pre/post. The recorded wall-clock instant is **read from the
committed capture** rather than re-pinned as a literal, so a re-capture cannot silently
desynchronize the double and the suite.

### Production queue claim limits

- **A queue can never be shown to finish.** No completion, no elapsed-time evaluation, because
  the legacy server has neither.
- **No cost, no timer, no speedup cost, and no count bound** are implemented, for the reasons
  above.
- **No unit is produced, trained, or placed**, and **no acquisition is claimed** — no committed
  unit is store-listed, and the real sources are the later-milestone `offer_packs` and
  `darts_items`.
- `sm_training_time` is **absent from 129 units and all 470 buildings**.
- Parity covers **one recorded push/pop transaction** against the fresh-player corpus, which
  places only one training producer; no progressed-player save is available.
- Production, collection, movement, animations, and basic behaviors remain undelivered.
- No pixel-parity oracle exists, and nothing here speaks for what the Flash client displayed.

**Known-flaky guard:** `verify-boot.ps1` treats any `^ERROR:` line as a script error, so a
nondeterministic engine-shutdown RID-leak warning can fail the battery even though the suite
exits 0. Observed once on `test_town_xp`; two reruns passed clean. **Re-run before treating
such a failure as a regression.**

---

## Unit production (M8 line 4)

A **refusal made a capability**, not a mechanism — because the committed investigation
`docs/legacy-unit-production.md` established that **the legacy server cannot produce a unit at
all**.

### The finding

**All five branches that can place a row on the map take the item id from the client.**

| Branch | Where the `item_id` comes from |
| --- | --- |
| `buy` | **client `args[1]`** |
| `place_stored_item` | **client `args[1]`** |
| `weekly_reward` | **client `args[1]`** |
| `pop_unit` | client `args[2]` — **and it overwrites the garrison row's item with it** (`unit[0] = item_id`) |
| `resurrect_hero` | **client `args[1]`** |

Not one derives an id from a completed queue, from a duration, or from committed production
content.

**`training_time` has zero legacy consumers.** The only matches of the substring are the
*distinct* field `sm_training_time` inside `soulmixer_speedup` — **three occurrences on two
lines**, all in that one branch. This is the **third** committed content field with no legacy
consumer, after `unit_capacity` (M8 line 2) and the level curve's `reward_type`/`reward_amount`
(M7's XP line). The precedent, established twice: **record the field, refuse to invent a rule.**

**The acquisition routes are unvalidated client-sent item lists.** `buy_offer_pack` reads
`package_id` — and then never uses it — `json.loads` a client-sent array, and stores every id
with **no lookup into the committed `offer_packs` table**. So the committed `offer_packs` and
`darts_items` tables are read by no **command branch** and **no acquisition is derived from
either**. (`darts_items` *is* walked at module level by `get_game_config.py`'s `make_dynamic` to
rewrite each entry's `start_date` — a content-freshness concern, not an acquisition path.)

`add_xp_unit` **creates nothing**: it adds a **client-sent** `attr["xp"]` to a placed row, with a
client-sent level used only in a print.

### What the module delivers

`scripts/units/production_flow.gd` is a pure module that projects that a queue exists and records
its start instant **while stating the server cannot say whether it is ready**, and exposes **no**
`is_complete`, `remaining`, `progress`, duration, or award helper at all. It records:

- the **row-entry inventory** with each id's source and classification, and the finding that no
  path derives a unit from a queue;
- the **`training_time` refusal** — reportable as content only, with the zero-consumer fact;
- the **`add_xp_unit` refusal** — a recorded `attr["xp"]` is readable as content, never awarded;
- the **acquisition finding** — recorded, with no mechanism and no request.

### The guard is tested, not trusted

The suite **asserts the absence** of any readiness, duration, or award helper, and re-derives
the recorded legacy facts from the source rather than trusting prose. Injecting a single
`static func is_complete` into the module makes the suite **fail with four independent
failures**; restoring it passes. A later line that adds a readiness helper therefore **fails the
delivered suite** rather than quietly reintroducing an invented rule.

### Verification (commands actually executed)

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_production.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

Observed 2026-10-01: `test_unit_production` **568 checks** (581 with `--report`), the 31st
hermetic suite; compat **unchanged** at `Ran 1257 tests ... OK` — this line adds **no endpoint**;
`verify-boot.ps1` exit 0 with **31 hermetic suites and 14 live phases**, guard digest identical
pre/post.

### Unit production claim limits

- **No production mechanism, completion, or readiness is implemented**, because the legacy server
  has none to reproduce.
- **No unit is created, trained, or placed**, and **no acquisition is implemented or claimed**.
- **No duration is derived** from the committed `training_time`.
- **No experience is awarded** from the recorded `attr["xp"]`.
- **No executed-legacy fixture** — and the reason is stronger than a corpus limitation: there is
  **no production behaviour to capture**.
- Death and resurrection are unreachable from the delivered client and unimplemented.
- `collection`, `movement`, `animations`, and `basic behaviors` remain undelivered.
- No windowed capture, no production endpoint, and no pixel-parity oracle.

---

## Unit collection (M8 line 5)

The first M8 line with a **server-derived, content-backed grant** — and therefore the first with a
genuinely capturable unit transaction. Scoped by `docs/legacy-unit-collection.md`.

### The project's first content-derived, server-authoritative unit acquisition

`complete_collection` takes a collection id, calls `get_collection_prize`, and grants the
**committed** prize bag into `map["store"]`:

```python
def get_collection_prize(collection: int):
    index = max(0, collection - 1)
    collections = __game_config["collections"]
    if index < len(collections):
        return json.loads(collections[index]["prize"])
    return None
```

**Six of the ten committed collections grant a unit:**

| `collection_id` | Name | Committed prize |
| --- | --- | --- |
| 1 | Draggy Collection | **unit 1085 Metal Draggy** |
| 2 | Transformer Collection | **unit 1062 MegaBot** |
| 3 | Plane Collection | **unit 1096 F-117** |
| 4 | Defense Collection | building 164 |
| 5 | Gun Collection | **unit 1073 Erradicator** |
| 6 | Tank Collection | **unit 1010 APC** |
| 7 | Launcher Collection | building 45 |
| 8 | Soldier Awards Collection | building 136 |
| 9 | Relaxing Time Collection | building 106 |
| 10 | Animal Collection | **unit 1056 Elephant rider** |

**The client sends a collection id, never what it receives.** Read from the captured fixture bytes:
collection 1's committed prize is exactly `{"1085": 1}`, the corpus's empty store became exactly
`{"1085": 1}`, and the ledger went `[]` → `[1]` — the grant matching the **committed bag exactly**,
the ledger growing by **exactly one appended id**, and **no player state fabricated**.

### What this corrected

The `production` line recorded that `buy_offer_pack` and `buy_stored_item_cash` are unvalidated
client-sent item lists, which reads as *no committed unit is obtainable*. That is true of **those
routes** and false of the server — so `godot-unit-production` now **completes** that finding with
this as the **sole content-derived** route, rather than amending it.

### Two authority gaps, recorded not smoothed over

- **Nothing verifies a collection was earned** — a caller may name any of the ten.
- **The one-based index makes ids 0 and 1 alias** (`max(0, collection - 1)`), and
  `collection_prize.gd` reports that rather than presenting them as distinct. The one-based reading
  is **derived-provisional**, corroborated by the committed `id` column running `1..10` against
  `legacy_id` `0..9`, with the rejected zero-based alternative retained.

### Three refusals

| | Why |
| --- | --- |
| No unit income | **0 of 429** units carry a positive `collect`; `collect`, `collect_type`, `collect_xp`, `max_collects`, `max_elem_vol` all have **zero** legacy reads |
| No cap semantics | `max_collects` is **0 on every unit** — the cap `building-collect` refused has **no unit analogue** |
| No experience award | `collect_xp` is never read and its only writer is **client-sent**, which `unit-production` already refuses |

(`harvester` is **not** a top-level committed field — it is a `properties` flag key on 5 Worker
units, all with `collect` 0 — and it is likewise never read.)

### Verification (commands actually executed)

```bash
python -B apps/compat-api/capture_collection_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_unit_collection.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

Observed 2026-10-01: `test_unit_collection` **1793 checks** (1805 with `--report`), the 32nd
hermetic suite; compat **grown** to `Ran 1352 tests ... OK` (from 1257, **+95**);
`verify-boot.ps1` exit 0 with **32 hermetic suites and 15 live phases**, and `collection-live`
drove one completion with its content-derived two-part proof.

### Unit collection claim limits

- **No unit income, payout, cap semantics, or experience award** is implemented.
- **No collection eligibility is checked** — a caller may name any committed collection. A
  server-authority gap for M13.
- **Collection ids 0 and 1 alias**, and the projection reports it.
- **The stored-item placement step was not delivered by this line** — and is now delivered separately.
  This fixture still evidences the grant **into storage**, not a unit placed on the map; the second half
  is `godot-stored-item-placement` (see "Stored-item placement" below), which captures and delivers
  exactly that round trip. This bullet is retained rather than deleted because the *evidence* stays
  here: nothing in this fixture was regenerated to fold the placement in, and its own README records
  that it is the first half only.
- The committed collections' `item_ids` completion requirements are unchecked by the server.
- `production`, `movement`, `animations`, and `basic behaviors` remain undelivered. No windowed
  capture and no pixel-parity oracle.

## Unit movement (M8 line 6)

The legacy server has **no movement rule**, and the one command that moves a row **already ships**.
Scoped by `docs/legacy-unit-movement.md`.

### The finding

`move` rewrites the row's two coordinate slots from client arguments and does nothing else:

- **no** type check, **no** occupancy check, **no** bounds check, **no** terrain check, **no** speed
- `frame` and `string` are read and **unused** — already recorded by the delivered `building-move`

**`move` is type-agnostic**, so it rewrites a unit row exactly as it rewrites a building's, and the
command **ships as M7's `godot-building-move`**. Across the seven legacy modules there are only
**five** writes to a row's slots 0–2, and exactly **two** branches write coordinates: `move`, and
`pop_unit` releasing a garrison row at client-supplied coordinates with the item id overwritten.
`orient` is a plain client-supplied slot write. There is therefore **no new server behaviour** for
this line to add.

**`velocity` is the sharpest zero-consumer field in the project** — positive on **all 429**
committed unit definitions and on 145 of 470 buildings, and **read by no legacy branch**. That is
the **sixth** committed content field with no legacy consumer, after `unit_capacity`,
`training_time`, the level curve's reward fields, and the `collect` family. `elevation`,
`width`, and `height` additionally **cannot** yield terrain-aware movement: the legacy SWF's tile
geometry was never extracted, the recorded M6 evidence gap.

`fast_forward` subtracts a **client-supplied** `seconds` from every row's recorded instant, from
every row's queue start instant, and from **eleven** further map, private-state, research, and
quest instants. It has **no observable effect** — precisely because nothing evaluates elapsed time —
and it is named because it is the **client-writable instant** a client-side readiness check would
trust.

### What the module delivers

`scripts/units/unit_movement.gd` is a typed, read-only **placement projection**. It reports the
committed cell coordinates, orientation, `width`, `height`, `elevation`, and `velocity` **verbatim**
and **derives nothing** from any of them, and it fails **closed**: a row whose coordinates are
absent or malformed is reported unresolvable with its **recorded slots travelling untouched** beside
the refusal, so a caller can never read a defaulted origin as a resolved cell.

Alongside it the module records the **movement-command inventory** — `move`, `orient`, `pop_unit`,
and `fast_forward`, each with what it *checks* and what it does **not** — and **eighteen** named
absent helpers, each with the reason it is absent.

**The placement view has one owner.** `godot-unit-instances` keeps ownership of the row and
**delegates** the placement reading here, so the two cannot drift.

### The guard is tested, not trusted

The anti-invention guard is **structural**: the module's whole function inventory is compared
against a pinned list. Injecting one deliberately invented

```gdscript
static func travel_time(from_cell: Variant, to_cell: Variant, velocity: Variant) -> float:
	return Vector2(float(from_cell[0]), float(from_cell[1])).distance_to(
		Vector2(float(to_cell[0]), float(to_cell[1]))) / maxf(1.0, float(velocity))
```

produced **two independent failures** — the pinned-inventory check and the per-helper absence check
— and restoring the file returned the suite to its passing state and **exit 0**.

### Two implementation defects this line found and corrected

**The investigation's own write count.** It first recorded **six** writes to a row's slots 0–2,
counting `engine.py:62` as `item[0] = ...`. That line is in fact `if item[0] == item_id:` — a
**comparison** inside `pop_unit`'s garrison scan. Measured with a pattern that excludes `==`, the
count is **five**. The conclusion was unaffected and independently re-measured: exactly **two**
branches write coordinates. `docs/legacy-unit-movement.md` carries the correction.

**A GDScript truthiness trap in the suite's own measurement.** The normalized package stores the
`properties` flags as **strings** (`"1"` / `"0"`) and leaves most **absent**, so a flag read as
`int(props.get("ft_flying", 0) or 0) > 0` counts a non-empty String as truthy, collapses the
committed `"0"` to `true`, and `int(true)` is 1. That reported `ft_flying` as set on **137** units
where the content says **135** — ids 1357 and 1369 are the two the package marks `"0"`. Verified
by probe that `int("0")` is 0, so **135** is correct; the flags are now read through one named
helper that converts each representation explicitly, and the encoding is recorded in the report.

### Verification (commands actually executed)

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_movement.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_movement.gd -- --report
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Observed 2026-10-01: `test_unit_movement` **245 checks** (246 with `--report`), the 33rd hermetic
suite; `verify.ps1` exit 0; `verify-boot.ps1` exit 0 with **33 hermetic suites and 15 live phases**
and **no new live phase**, because this line adds no server operation; the compat suite
**unchanged** at `Ran 1352 tests ... OK`; the content validator `result: valid` across 21 schemas;
and the preservation manifest 3,258 entries. The evidence is the deterministic
`unit-movement-report-v1` report at `evidence/unit-movement/report.json`, digest
`785B0482…9165E`, byte-identical across three consecutive runs.

*One flake worth recording:* the first `verify-boot.ps1` run reported the compat discovery exiting 1
while the suite itself reported `OK`; the suite passed standalone (`Ran 1352 tests ... OK`, exit 0)
and the battery passed on rerun. Consistent with the recorded guard-narrowing follow-up, and no
`apps/compat-api/**` byte changed.

### Unit movement claim limits

- **No velocity-based travel time, path, terrain or elevation interaction, occupancy, bounds,
  readiness, or interpolation is implemented.** Each is a recorded refusal with its reason, not an
  omission — the eighteen `ABSENT_HELPERS` entries are the contract.
- **The committed movement fields are read by no legacy branch** and are reported as content only.
- **No unit-specific movement command exists in the legacy source and none was invented.** Exactly
  two branches write coordinates, and the one that moves an existing row is type-agnostic, already
  delivered, and checks nothing.
- **No unit is placed or moved**, and the committed corpus holds no unit row (40 placements, 11
  distinct ids, every committed `type` `b`).
- **No executed-legacy fixture was captured**, because there is **no unit-specific movement
  behaviour to capture** — a stronger statement than the corpus's missing unit row, which is
  recorded as a second and independent reason. The type-agnostic move command already has its own
  executed-legacy fixture under `godot-building-move`.
- **No animation or playback is implemented.** M4's converted unit package establishes asset and
  timeline **linkage** only, never playback correctness or gameplay behaviour.
- **No pixel parity is claimed**, and the M6 tile-geometry gap remains a recorded gap. **No windowed
  capture is claimed**: nothing is rendered and no unit exists to render.
- `animations` and `basic behaviors` remain undelivered.

## Unit animation (M8 line 7)

The legacy server has **no animation rule and no animation command**. Scoped by
`docs/legacy-unit-animations.md`, which was itself scoped by an instruction **not** to infer
animation semantics from M4's converted unit package. That caution proved load-bearing: the single
most tempting reading of the evidence is **wrong**, and the package itself refutes it.

### The finding

Of the **63** named `command.py` branches, five contain animation vocabulary as a *substring*, and
every one is an artifact:

| Branch | Class | Why it is not an animation command |
| --- | --- | --- |
| `move`, `orient` | whole `_`-token | already owned by `godot-unit-movement` |
| `end_attack` | whole `_`-token | combat termination |
| `batch_remove`, `remove_inventory_item` | pure substring | contain the letters of "move" inside "re**move**" |

**No branch starts, stops, advances, loops, or selects an animation**, and **six animation-adjacent
committed fields have zero legacy consumers** across the seven modules: `max_frame`, `img_name`,
`attack`, `attack_interval`, `attack_range`, and `velocity`, plus the `animal` `properties` flag.
**`max_frame` is the seventh zero-consumer committed field in this project**, and it is a
near-constant: **`5` on 427 of the 429** units, `2` on exactly ids **923** and **933**, and over the
470 buildings `2` on **446** and `1` on **24**.

### The states exist, in the asset rather than in the content or the server

The one committed converted unit package parsed `10033_wild_elephant.swf` and recorded **sprite 63
with 29 frames and five named labels**:

| Label | Frame |
| --- | --- |
| `QUIETO` | 1 |
| `ANDAR` | 6 |
| `ATAQUE` | 11 |
| `MUERTE` | 16 |
| `PICAR` | 21 |

**Established:** the labels and their frame positions. **Not established:** any playback — M4's own
recorded limit is *no tessellation, no playback semantics, labels names-only*, so there is no
recorded loop, state machine, transition, priority, interrupt, per-state duration, or mapping from
any server event to any state. `MUERTE` is a state the delivered `production` line already found
**unreachable**, since no legacy command produces a unit and none kills one.

**The label names are reported verbatim in Portuguese and are deliberately NOT translated** into
English state words: nothing selects a state, so there is nothing for a translation to name, and a
translation would import a state model the evidence does not support. A later line wanting those
readings must re-derive them.

### The measured contradiction that settled the scope

| Quantity | Value | What it is |
| --- | --- | --- |
| committed `max_frame` | **2** | a per-unit **content** field on the definition |
| parsed root `frame_count` | **1** | a static parse of that asset's root timeline |
| parsed sprite 63 `frame_count` | **29** | the timeline that actually holds the five labels |

The content's `img_name` equals the converted package's `legacy_id`, so all three describe the same
unit and **disagree**. **`max_frame` is therefore not the asset's frame count**, and a line that
adopted it as one would be wrong.

That is **one data point**, recorded as derived-provisional: enough to **refuse adopting** `max_frame`,
not enough to claim what it means, and not a measurement of any other unit — only **one** converted
unit package and **one** building package are committed, so no distribution is measurable.

The refusal is enforced *structurally*: the suite asserts that **no code identifier in the module is
named after the committed field**, which is what forced the public accessor to be named
`non_equivalence_record()` rather than after the field it reports on.

### What the module delivers

`scripts/units/unit_animations.gd` is a typed, read-only **linkage** projection. It reports the
recorded labels, each label's recorded frame position, the per-sprite recorded frame counts, and the
recorded frame rate **verbatim**, deriving **nothing** from them — the module's code contains **zero**
multiplication or division lines, so the no-derivation claim is mechanically true rather than
asserted. It fails **closed**: an asset that is absent, unreadable, or **label-less** is reported
unresolvable with its recorded state intact, never defaulted to an empty, nominal, or single-frame
animation.

**The reading has one owner.** `godot-unit-definitions` keeps ownership of whether the committed
sprite reference *resolves*, and this capability owns what the asset's recorded timeline *contains*.

### The guard is tested, not trusted

The anti-invention guard is **structural**: the module's whole function inventory is compared against
a pinned list. Injecting one deliberately invented

```gdscript
static func frame_duration(frame_count: Variant, rate: Variant) -> float:
	return float(frame_count) / float(rate)
```

produced **two independent failures** — the per-helper absence check and the pinned-inventory check —
and restoring the file from a byte-identical copy returned the suite to its passing state.

### Verification (commands actually executed)

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_animations.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_animations.gd -- --report
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Observed 2026-10-02: `test_unit_animations` **628 checks** (629 with `--report`), the 34th hermetic
suite; `verify.ps1` exit 0; `verify-boot.ps1` exit 0 with **34 hermetic suites and 15 live phases** and
**no new live phase**; the compat suite **unchanged** at `Ran 1352 tests ... OK`; the content validator
`result: valid` across 21 schemas; the preservation manifest 3,258 entries; and
`openspec validate --all --strict` green. The evidence is the deterministic
`unit-animations-report-v1` report at `evidence/unit-animations/report.json`, digest
`f06784cb…d8556`, 46,703 bytes, byte-identical across three consecutive runs.

**Two corrections made to prior records while this line was verified:**

- `test_project_scope.gd` listed `tests/test_unit_movement.gd` and
  `evidence/unit-movement/report.json` **twice** in `ALLOWED` — a defect introduced on the movement
  line, which the permissive allow-list did not catch, so it would have shipped silently. Both
  duplicates are removed. (The four `scenes/*.tscn` duplicates are **intentional**: `ALLOWED` lists
  them and `EXPECTED_SCENES` checks them separately.)
- `AGENTS.md` recorded the collection suite at **1793 checks**, measured on the unmodified suite at
  **1845** (1857 with `--report`). The recorded figure was stale and is now corrected in place.

### Unit animation claim limits

- **No frame duration, loop count, state machine, transition, priority, interrupt, playback order,
  per-state timing, animation trigger, or event-to-state mapping is implemented.** The recorded
  `ABSENT_HELPERS` are the contract, not omissions.
- **The committed animation fields are read by no legacy branch** and are reported as content only.
- **`max_frame` is adopted nowhere** as a frame count, duration, or loop bound, and **what it means is
  not claimed** — the measurement is one data point.
- **No legacy branch selects an animation**, and none was invented.
- **No animation is played, animated, or rendered.** The converted unit package establishes asset and
  timeline **linkage** only, never playback correctness.
- **No claim is made for any unit other than the one committed converted package** — coverage is
  **1 of 429**, with every other path exercised over crafted in-memory packages. Closing this needs a
  new conversion, not a derivation.
- **No executed-legacy fixture was captured**, because there is **no animation behaviour for the
  legacy server to have** — a stronger statement than any corpus limitation.
- **No pixel parity is claimed** and **no windowed capture is claimed**, because nothing is rendered.
- **No executed-legacy fixture was captured for `basic behaviors`** (M8 line 8, the
  milestone's final line) — see "Unit behaviors" for the specific cause, which is unlike
  this line's: a corpus limitation, not an absence of behaviour.

## Unit behaviors (M8 line 8)

The **final M8 deliver line**, and **the first M8 line that is not a refusal**. Its investigation
(`docs/legacy-unit-behaviors.md`) was explicitly told to *measure its own fields* rather than assume
the pattern that `production`, `movement`, and `animations` all followed, and that instruction is why
this line has a mechanism: of **twenty-three** behavioural committed fields, **twenty-one** measure
**zero** legacy consumers across the seven legacy modules — but **two** do not, and one is the
**first committed field in this project whose legacy consumer is a mutation of private state rather
than a read**.

| Field | Present | Legacy reads |
| --- | --- | --- |
| `resurrectable` (`properties`) | **carried by 426 of 429 units**, **0 of 470 buildings** | **2** — `engine.py:159,162` |
| `clicks_to_build` | 429 of 429 units | **1** — `engine.py:26`, seeds `attr["nc"] = 0` |

**The eighth zero-consumer candidate is not one.**

### What it delivers

- **`scripts/units/unit_behaviors.gd`** — a typed, read-only projection of
  `privateState["deadHeroes"]`: every recorded item id and count **verbatim**, the increment and
  decrement shapes, the **delete-at-zero** rule, and **both** legacy gates named with their source
  lines — the row on **player team 1** and the committed `resurrectable > 0` — with **no third gate
  invented**. It **fails closed** on an absent ledger, a non-object ledger, a non-string key, or a
  non-integer count, reporting **unresolvable** rather than presenting an empty ledger as resolved.
- **The three-door inventory.** Of the 63 dispatcher branches, three reach or bypass the ledger and
  each behaves differently:

  | Command | Effect on the ledger |
  | --- | --- |
  | `kill(index, reason)` | deletes the row and **never** touches it |
  | `sell(index, reason)` | deletes the row; calls the `push_dead_unit` **engine helper** (not a branch) **only** behind the combat-reason guard |
  | `resurrect_hero(index, item_id, x, y, used_syringe)` | decrements, **deletes the key at zero**, then re-places the row at **client-supplied** coordinates |

- **`POST /v0/resurrect`** (`apps/compat-api/behavior_envelope.py`) — accepting **only** a player
  identifier and a cell. The **item id, the map key, and the resulting ledger state are derived
  server-side**, and any client-supplied syringe count is **ignored and never echoed**, exactly as a
  client-sent prize is discarded by `complete_collection_town(collection_id)`. Two refusals with named
  codes, empty payloads, and no ledger change: a cell that resolves to no recorded entry, and one
  whose resolved entry's committed `resurrectable` is not positive.
- **A two-part post-execution proof**: the ledger entry is **gone** after a revival that reaches
  zero, **and every stored resource is unchanged**. The second half is what makes the
  no-syringe-cost claim non-tautological — the same proof form the `level_up` line established for
  that reason.
- **`scripts/units/behavior_flow.gd`** and typed `resurrect_hero_town()` on **both** GameApi
  implementations, sending intent only.

### Verification actually run (2026-10-02)

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_behaviors.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_behaviors.gd -- --report
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
```

- the hermetic suite: **573 checks** (587 with `--report`); **the 35th hermetic suite**
- `verify.ps1` exit **0**
- `verify-boot.ps1` exit **0** with **35 hermetic suites and 16 live phases** (the new
  **`behavior-live`** phase drives one revival through the real v0 endpoint against a disposable
  corpus seeded with a resurrectable ledger entry, and proves the disposable save mutated)
- the compat suite **grew** to **`Ran 1444 tests ... OK`** — up from 1352 by **+92**, because this
  line adds a state-mutating endpoint, the first M8 line since `collection` to do so
- evidence: `evidence/unit-behaviors/report.json`, deterministic `unit-behaviors-report-v1`,
  digest `0FE80C47…8F59`, **byte-identical across three consecutive runs**

The report is written by the suite itself via `--report=<path>`, so its tables are derived from the
live module and cannot drift from the code they document.

### Refusals

- **No syringe cost, and no resource moves.** `used_syringe` is read from `args[4]` and **discarded**,
  while the committed `syringes` field — its obvious counterpart, with **zero** consumers — sits
  unread. Charging one would invent an economy no legacy branch implements.
- **No combat is resolved.** `attack`, `defense`, `life`, `attack_interval`, `attack_range`,
  `best_against`, and `best_against_mult` all measure **zero** consumers, so the committed numbers
  are content, never rules.
- **No occupancy, bounds, type, or terrain validation** is added to the revived placement. The
  legacy branch checks none; authoritative validation belongs to Server v1 / M13, and inventing a
  check here would make the modern client *stricter* than the legacy server.
- **`clicks_to_build` is referenced and not reimplemented.** Its single consumer is the
  construction-click counter owned by `godot-building-construction`.
- **The anti-invention guard is structural and was tested by injection**: the module's whole
  static-function inventory is compared against a pinned list, and injecting one invented
  `static func syringe_cost(syringes)` produced **five independent failures**. Restoring the file
  from a byte-identical copy returned the suite to its passing state. A guard that is only asserted
  is not evidence.

### Claim limits

- **No executed-legacy fixture**, and the cause is **specific**, not the refusal lines' "no behaviour
  exists": `resurrectable` is **unit-only**, the committed corpus places **only buildings** and **no
  unit row**, and its ledger is present and `{}`. Manufacturing a unit row to make one capturable is
  refused, exactly as `godot-unit-instances` refused. Unlike the refusal lines, the cause is the
  **absence of a resurrectable row**, not the absence of a mechanism.
- **The death/resurrection pairing is derived.** The two functions are complementary and share the
  ledger, but no comment or dispatch path asserts the pairing, so it is never presented as a server
  guarantee.
- **The committed corpus is not all team 1.** Keys 1–20 are team 1 and **21–40 are team 3**. Gate one
  alone does not need that fact, but any future claim that scans the corpus must respect it.
- **No pixel parity is claimed** and **no windowed capture is claimed**: a revived unit needs a unit
  row, and the corpus has none, so nothing would be rendered that is not already rendered.
- **Five figures in the investigation record were asserted rather than measured** and were corrected
  by the Apply stage after independent re-verification — the zero-consumer count (twenty-one, and a
  total of twenty-three), four source lines (each off by one), `resurrectable` being *carried* by 426
  units with the key **absent entirely** on ids 923/933/1176 rather than set to zero,
  `clicks_to_build` taking **two** distinct unit values rather than three, and `collect_type` taking
  **two** over the units with the five-value spread belonging to the *buildings*.
  `docs/legacy-unit-behaviors.md` carries a corrections section rather than quiet edits; **none
  changes the conclusion**.

With this line, **M8 is complete**: eight deliver lines, of which three carried real mechanisms
(`queues`, `collection`, `behaviors`) and five delivered projections plus refusals — in every case
because the committed content or the committed corpus had nothing more to reproduce.
## Unit research (M9 line 1)

**M9 — Progression's first deliver line**, on the committed contract in
`docs/legacy-m9-progression.md` (PR #250) extended by PR #252. This line is the first M9 work of any
kind, and it is **not** a refusal line: the counters genuinely mutate and the committed corpus genuinely
exercises them.

### The contract

Four dispatcher branches over two tracks (`0: TYPE_AREA_51`, `1: TYPE_ROBOTIC`):

| Branch | `command.py` | step | item | instant |
| --- | --- | --- | --- | --- |
| `next_research_step(_type)` | 268–274 | `+= 1` | — | `= time_now` |
| `research_buy_step_cash(cash, _type)` | 276–282 | — | — | `= 0` |
| `next_research_item(_type)` | 284–291 | `= 0` | `+= 1` | `= 0` |
| `reset_research_item(_type)` | 293–300 | `= 0` | `= 0` | `= 0` |

### The finding: the three counters are **write-only**

`researchStepNumber` has **3** sites and `researchItemNumber` **2**, every one a write.
`timeStampDoResearch` has **5** — the four branch writes plus **one read at `command.py:923` that is
itself a write**, because it sits inside `fast_forward` and subtracts a **client-supplied** number of
seconds, clamped at zero (`seconds = args[0]` at `command.py:906`).

**Nothing anywhere reads a research counter to decide anything.** A guard audit of all four branches finds
**no** bounds check, numeric clamp, membership test, exception guard, or existence check. `fast_forward`
is therefore recorded as a **fourth writer**, and it makes the research instant **client-writable** —
and because no readiness check exists anywhere, an instant trusted by nothing is the only elapsed-time
input the research system has. It is **recorded, never delivered**.

`research_buy_step_cash` reads a **client-supplied cash value and discards it** — structurally identical
to M8 line 8's `used_syringe` — so **no research price is charged**.

### What it delivers

- **`scripts/units/research_flow.gd`** — a typed, read-only projection of **both** tracks and **all three**
  counters, reported **verbatim** with no value derived from another, and **failing closed** on an absent
  vector, a non-list, a wrong length, a non-integer element, and a negative element.
- **The four branch effects recorded as data**, including that the item branch resets the step counter
  **and** the research instant **together**, and that the cash branch charges nothing.
- **The track inventory** reporting the committed building ids `ID_BUILDING_AREA_51 = 139` and
  `ID_BUILDING_ROBOTIC_CENTER = 86` — and the suite asserts **no delivered code identifier is named after
  `TYPE_AREA_51` or `TYPE_ROBOTIC`**, so the "reported, never used" claim is *mechanical* rather than a
  promise.
- **`POST /v0/research`** — **intent-only**: the client sends a player identifier and a track and nothing
  else; the service derives every counter value and every research instant itself and discards any
  client-supplied counter, timestamp, or cash value.
- **Executed-legacy fixtures** — eight branch-track transactions, because the corpus holds every counter
  at `[0, 0]`.

### Verification actually run (2026-10-02)

```bash
python -B apps/compat-api/capture_research_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_research.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

- fixture capture: exit **0**, **re-runnable across three runs**, eight branch-track steps recorded
- the hermetic suite: **1024 checks** (1038 with `--report`) — the **36th** hermetic suite
- `verify.ps1` exit **0**; `verify-boot.ps1` exit **0** with **36 hermetic suites and 17 live phases**,
  and **221** log files inspected with **zero** `^ERROR:`/`SCRIPT ERROR` lines
- compat suite **grew** to **`Ran 1572 tests ... OK`** — up from 1444 by **+128**
- evidence: `evidence/research/report.json`, `research-report-v1`, digest **`e62f2666…c86`**, byte-identical
  across **four** runs

The report is written by the suite itself via `--report=<path>`, so its tables derive from the live module
and cannot drift from the code they document.

### The anti-invention guard was tested, not trusted

Injecting one invented `static func research_price(track, step)` produced **four independent failures**
against a pinned whole static-function inventory — the suite exits **1** with `failures=4`. Restoring the
file from a byte-identical copy (identical SHA-256) returned it to exit **0** with **1024 checks**. A guard
that is only asserted is not evidence.

### A cross-milestone correction

`godot-unit-behaviors` claimed **three** doors into the dead-hero ledger. Measurement makes it **four**:
`map_lose_item` (`engine.py:215-228`) calls `push_dead_unit` at line **223**, and its only **two** callers
are `command.py:796` inside **`end_quest`** and `command.py:872` inside **`end_attack`**. So the fourth door
is reached from **two** branches — the quest path and the attack path — which **strengthens** the
correction rather than weakening it.

**One tool constraint was measured rather than worked around:** a MODIFIED delta resolves its header
against the existing requirement name and Archive **refuses a renamed heading**, so that requirement's
"three-door" heading is retained as a documented **superseded label** with the four-door correction in
its body. No archived change uses `RENAMED Requirements` and the CLI does not document the form.

### Claim limits

The delivered feature means **these counter transitions and nothing more**, because the counters have
**no in-game consumer**. **No price is charged** and **no stored resource moves** — proved by every
action's post-execution check that the **complete** stored resource set is unchanged. **No completion,
readiness, remaining-time, or unlock semantics.** **No counter bound, membership rule, or clamp** is
added; a client could still send track `7` or `999`, and that is a recorded **Server v1 / M13** gap.
**No reward** is paid. **No committed research content is invented**, because none exists to invent from:
`research` appears in the content **only** as asset names and one building's display name, never as a
schedule, price, gate, or reward. **No fast-forward operation is delivered.** Fixture parity covers
**eight** transactions against the fresh-player corpus only, and the item branch's instant half is a
recorded **0→0** transition because the capture order had already zeroed both instants — the pairing is
established instead by `command.py:288-289`. **No pixel parity** and **no windowed capture**, because
nothing is rendered and the corpus places neither research building.

**Corrections to the committed investigation.** Three figures were asserted rather than measured and
**overstated** the absence of committed research content; all three were corrected after independent
re-verification, and the record carries a corrections section rather than quiet edits. `research` appears
in **two** normalized files (`buildings.json` **1**, `images.json` **6** from three popup-asset rows), not
one; `config/main.json` **does** have **three** nested keys containing it, all in the `/images` asset
namespace, so "no key at any depth" is **false** — though no *top-level* key contains it; and the
building's `legacy_id` is the **string** `"256"`, since every `legacy_id` in `buildings.json` is a string.
**The conclusion is unchanged**, but the refusal now rests on a correctly measured basis.
## Quest progression (M9 line 2)

**M9 — Progression's second deliver line** and its **largest surface**: six undelivered branches, on the
committed contract in `docs/legacy-m9-quests.md` (PR #258).

## Only TWO committed quest fields are read by anything

Measured as **quoted** occurrences across the seven legacy modules, so comments cannot contribute:

| Committed field | Quoted legacy occurrences |
| --- | --- |
| `id` | **8** |
| `title` | **2** — the two `print` statements |
| **`reward`** | **0** |
| `hint`, `description`, `kind`, `legacy_id`, `source_file`, `source_layer`, `content_version` | **0** each |

`reward` is committed on all **91** entries and is **uniformly the value `10`** — so it carries **no
information even if it were read**. **There is therefore no quest reward, cost, or price to derive**, and
none is.

## `complete_goal` mutates nothing

The executed fixture proves it: the captured transaction changed **no** `privateState` key and **no**
`maps[0]` key. A goal "completes" by being narrated in a `print` statement, so a line that wrote a
completion flag, ledger, or reward would invent a mechanic that does not exist.

## The divergence is **measured**, not asserted

Probe 4 sends `end_quest` with `units = [[26, 0, 1, 0]]`, so the legacy branch's **client-computed**
`lost = max(0, unit[2] - unit[3])` is **1**:

- the **legacy server destroyed a placed row, 40 → 39**;
- the modern endpoint derives `units: []`, destroys nothing, and leaves **all 40 rows byte-identical**.

Recorded as a **divergence**, not as parity. Reproducing a client-dictated destruction count would be
exactly the anti-pattern `AGENTS.md` names as "Bad". The manifest also records separately that the
*captured transaction's* rows were byte-identical, because that step carried no lossy tuple — the worker
distinguished the two rather than letting the probe stand in for the transaction.

## Three probes establish the refusals with executed evidence

- `set_goals([500, "[0,0]"])` grew the list from **151 to 501** — **350** entries appended from one
  client-sent id, **no upper bound** — so the endpoint **reproduces** the unbounded growth rather than
  closing it.
- `set_quest_var(["idSimpleChapter", 5])` wrote **nothing** (the branch returns at `command.py:95` before
  any write) while an invented key **was** accepted — so exactly **one** key is refused, and it is the one
  the legacy branch itself ignores.
- `collect_mission([150])` **wrapped to `1`** at bound `99`, stored as a **`str`** against a corpus
  recording an **integer** `0`.

## Five cross-layer defects the hermetic suite **structurally could not catch**

This is the most important verification finding of the line. The offline suite builds its own response
envelope, so **1223 hermetic checks passed while the live phase failed five separate times**. Each was
found only by `quests-live`:

1. the transport sent every action's addressing under a fixed `addressing` key while the service reads the
   **per-action** key;
2. `project_quests()` never emitted the `resolvable` flag the typed parser requires, so **all six** live
   responses were refused `bad_response`;
3. the parser demanded `end_quest_blob` unconditionally while the service sends `null` for the other five;
4. `int()` on a recorded null goal is a **nonexistent constructor** in Godot 4;
5. **Godot decodes every JSON number as a `float`**, so `[0,0]` arrives as `[0.0,0.0]`.

New guards were added for the class: the request's third key is asserted equal to
`ACTION_ADDRESSING_KEY[action]`, the transport must call `wire_key()` and must contain no hardcoded
`"addressing":`, and the suite **asserts the double builds no body at all**, recording *why* it could not
catch any of the five.

## Verification actually run (2026-10-03)

```bash
python -B apps/compat-api/capture_quest_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_quests.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
```

- fixture capture: exit **0**, six branch transactions plus login and **five** probes
- the hermetic suite: **1223 checks** (1238 with `--report`) — the **37th** hermetic suite
- `verify.ps1` exit **0**; `verify-boot.ps1` exit **0** with **37 hermetic suites and 18 live phases**,
  guard digest `6978b959…ff348` identical pre/post
- **484** log files inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines
- compat suite **grown** to **`Ran 1751 tests ... OK`** — up from 1572 by **+179**
- evidence: `evidence/quests/report.json`, `quests-report-v1`, digest **`412dd271…6019`**, byte-identical
  across **three** runs

**Two anti-invention guards, both tested by injection rather than trusted.** Injecting `quest_reward`
produced **4 independent failures** and exit 1; injecting `mark_goal_complete` produced **4 independent
failures** and exit 1; restoring the byte-identical file (SHA-256 `631a564d…fa12`) returned the suite to exit
**0** with **1223 checks**.

### Claim limits

**No quest reward is paid** and **no stored resource moves**, and the uniform `10` is recorded as **not** a
payout · **the `end_quest` destruction count is refused** as a divergence, not parity · **no bound is added**
to the on-demand goals list and **no membership test** to the quest-variable writer, both absences being
Server v1 / M13 gaps deliberately not filled · **no completion state exists** · `unlockedQuestIndex` is
reported and **never written**, having **zero** legacy sites — the ninth such field in this project ·
**no fast-forward operation is delivered**, though `command.py:942-944` and `911` are recorded as
quest-state writers making quest timing client-writable, and `version.py:38-44` as a **migration** rather
than gameplay · the committed content is **reported and never used**, with no delivered identifier named
after the reward field · parity covers **six** transactions and five probes against the fresh-player corpus
only · the five **missing-key** refusals are **structurally unreachable through the typed client** and the
live phase proves this rather than asserting it · the hermetic suite **cannot** detect envelope or wire
drift by construction, so `quests-live` is the only guard for that class · **no pixel parity** and **no
windowed capture**, because nothing is rendered.

**A third recorded flaky surface:** `verify.ps1` returned **-1** on one of two runs and **0** with
`PASS all checks succeeded` on the second, because its windowed-capture step is display-sensitive.

---

## Tutorial progression (M9 line 3)

M9's third line, and the first **not** to be a refusal line. The contract is committed in
`docs/legacy-m9-tutorial.md` (PR #264, merged `2dbf715`), and the field it delivers has **zero legacy
readers** — which is exactly why the previous two M8 lines' investigation instructions to "measure your own
fields rather than assume the refusal pattern repeats" were load-bearing here.

### The finding: one branch, one write, one stored field, and **three** reachable verdicts

`command.py:60-66` is the entire tutorial system:

```python
if command == "complete_tutorial":
    tutorial_step = args[0]                                              # :61  a LOCAL
    print("Tutorial step", tutorial_step)                                 # :62  a log line
    if tutorial_step >= 25 or tutorial_step == 15:                        # :63  the gate
        save["playerInfo"]["completed_tutorial"] = 1                      # :65  the write
```

Measured across the eleven legacy root modules: `completed_tutorial` occurs **once**, on **one** line, and
that line is the **write** — **zero** readers, making it the **tenth** committed field in this project with no
legacy consumer (after `unit_capacity`, the level curve's unread reward fields, `training_time`, `velocity`,
`max_frame`, `resurrectable`'s siblings, `unlockedQuestIndex`, and the quest `reward`). `tutorial_step` occurs
**4** times over **3** lines; `complete_tutorial` occurs **once**.

The gate has **no lower bound, no upper bound, and no type check**. It completes at
`15, 25, 26, 100, 1000000, 1000000000` and declines at `-1000000000, -5, -1, 0, 1, 14, 16..24` — so the
**hole is exactly `16..24`**, nine steps wide, between the two arms. `tutorial_step` is a **local** and is
**never persisted**, so there is **no stored step** and therefore nothing to resume from.

### Three verdicts, and the ORDER they are reachable in

The endpoint checks the **flag before the gate**, so once a tutorial completes, every later step answers
`already_completed` and `gate_declined` is unreachable for the rest of that save's life. The committed corpus
starts at the seed value, so the hole step must go **first**. The `tutorial-live` phase is written in exactly
that order and says so in its own comment, because any other order would silently prove only the third verdict
while reading as full coverage.

- `gate_declined` — a hole step. **200**, `{"result": "success"}`, nothing written. Not an error: legacy
  answers success and changes nothing.
- *(dispatch)* — a completing step. Exactly **one** changed leaf, `/playerInfo/completed_tutorial`, and
  **no** stored resource moves.
- `already_completed` — **200**, nothing written.

Both no-ops answer **200 rather than an error**, and that was a deliberate decision: legacy answers
`{"result": "success"}` and changes nothing in both, so an error would be a divergence the evidence does not
support.

### The ONE divergence, confined to failure handling

Legacy answers an unhandled **HTTP 500** for a string, missing, or null step. Those three shapes get **named
refusal codes** here (HTTP 400, empty payload) and the legacy 500 is **not reproduced** — a crash is not a
behaviour. Coercing a malformed step to `0` so it merely declines was rejected for the same reason. Legacy
*state transitions* for accepted steps are reproduced exactly; only failure handling diverges, and the
committed save state is identical either way.

**Float steps are measured, not reproduced.** Legacy **completes** on `15.0`; this client refuses a float
step in `evaluate()` *and* the endpoint refuses it in `validate_step()`. That is recorded as
`LEGACY_ACCEPTS_FLOAT_STEP := true` — a divergence stated, not hidden.

### The deliberate strictness asymmetry

`_strict_int()` governs the **outgoing** step (accepts only `int`; refuses bool and float, matching the
endpoint's `validate_step`). `_integer()` governs every **incoming** value and accepts integral floats,
because Godot decodes every JSON number as a `float` — without that, the client could not read its own
save. Both are in the pinned `STATIC_FUNCTIONS` inventory.

Gate-record comparison uses `_gate_field_equal()` and **never `str()`**: the service's `25` arrives as `25.0`
and the manifest's `hole_low` as `16.0`, so a textual comparison would fail on values that are equal. Bools
compare by identity, never as `0`/`1`.

### `/v0/tutorial` route placement is load-bearing, and pinned

The route is declared **FIRST**, ahead of every other route. Every delivered suite slices
`def vN_x():` up to the next `@app.<method>(...)` decorator and `textwrap.dedent` is a no-op on such a
slice, so a route inserted at indent 4 after a body at indent 8 raises `IndentationError` inside the
*previous* route's slice. The only slot no slice reaches is ahead of the first route. `test_tutorial_endpoint.py`
pins this with a dedicated `RoutePlacementTests` class, and the placement guard was **proven by injection**:
moving the route produced **3 independent failures** with exit 1 while the file still compiled, and restoring
it byte-identically (SHA-256 `D75BF31C…D6D0`) returned the suite to green.

### Two disposable rounds, because the flag is not reusable

The flag is `0` in the seed and `1` after any completing step, so step records live under
`steps/<round>/<name>` — the one layout deviation in this project's fixtures. Round 1 (`neutral`) is the
**parity** transaction; round 2 (`minting`) is the **anchor**: one legacy request with the client ladder
`[101, 3, 7, 11, 13, 17, 19, 23]` — read out of the committed `request.json` by the suite rather than
restated from memory — moved all seven stored resources **plus** the flag, 8 leaves. The endpoint's
`validate_vector`/`build_envelope` **refuse** that ladder, which is what makes its "no stored resource moved"
proof half **non-tautological**.

### The only progressed evidence is the villages

`config/main.json` and `packages/game-content/normalized/*.json` contain **zero** occurrences of `tutorial`
— no step list, no count, no gate definition, no tutorial text. The **eight committed village saves** are the
only progressed evidence for the field: seven record `1`, and one — `initial.json`, the seed, whose `pid` is
absent — records `0`. Both states are therefore observable in committed data. *(The fixture README originally
asserted "31 village saves, 30 recording `1`"; that was an assertion rather than a measurement, is wrong on
both counts, and is corrected there with the measurement recorded — this suite asserts 8 / 7 / 1.)*

The flag reaches the client only because `get_player_info.py:15` includes the **whole** `playerInfo` dict
wholesale; the endpoint names no field, which is why the projection reads the record rather than a selected key.

### The offline double mutates its in-memory flag

A dispatch flips the double's own flag (monotonically), so `already_completed` is **reachable offline** and
its no-op-ness is **demonstrated** rather than asserted.

### Verification actually run (2026-10-03)

```bash
python -B apps/compat-api/capture_tutorial_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_tutorial.gd
godot --headless --path apps/client-godot --script res://tests/test_tutorial.gd -- --report=<repo>/apps/client-godot/evidence/tutorial/report.json
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
openspec validate tutorial --strict
```

- fixture capture: exit **0**, containment **UNCHANGED**, on **five** consecutive runs; the committed fixture
  is 2 rounds / 3 recorded steps / 1 executed probe, and its re-runnability was verified by diffing two runs
  field by field — only `executed_at_utc`, `captured_at_utc`, the `Date` header, and the signed `form.data`
  (which embeds a wall-clock `ts`) differ. The **40** executed-legacy probe transactions are the
  *investigation's*, recorded in `docs/legacy-m9-tutorial.md`, not this fixture's.
- the hermetic suite: **639 checks** (642 with `--report`) — the **38th** hermetic suite
- `verify.ps1` exit **0**; `verify-boot.ps1` exit **0** with **38 hermetic suites and 19 live phases**, guard
  digest `6978b959…ff348` identical pre/post
- **264** log files inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines
- compat suite **`Ran 1912 tests ... OK`**, exit 0
- content validator exit **0**, `result: valid`, 21 schemas; preservation manifest **3,258 entries**, exit 0
- evidence: `evidence/tutorial/report.json`, `tutorial-report-v1`, digest **`05f7b12d…c38b`**, 10,634 bytes,
  byte-identical across **three** consecutive runs

**The anti-invention guard is structural and was tested rather than trusted.** Injecting one invented
`static func tutorial_total_steps() -> int` produced **3 independent failures** and exit 1; restoring the file
from a byte-identical copy (SHA-256 `9ea3ff1b…0d6`) returned the suite to its 637-check passing state.

### Claim limits

**No stored step** and **no un-complete path** — `tutorial_step` is a local, so nothing resumes · **no reward**
is paid and **no progress display, step count, ratio, or remaining time** is implemented · **no gate bounds,
no membership test, and no exception guard** are added, the legacy branch having none, so a client can still
send a negative or enormous step; that is a recorded **Server v1 / M13** gap · **no pixel parity** and **no
windowed capture**, because nothing is rendered · **the float-step and raising-shape divergences are recorded,
not reproduced** · **the offline double is not the endpoint** — it exists so the no-op verdicts are
demonstrable without a service · **parity covers three recorded transactions against the fresh-player corpus
only**, and no progressed-player save exists beyond the eight villages · the tutorial is **not rendered as
tutorial**, only as a readout and a confirm line.

## Stored-item placement (`godot-stored-item-placement`)

M9's fourth deliver line, and the **first working round trip** in the M8/M9
sequence — every prior line after M7 either recorded a refusal or moved only
counters. The contract is committed in `docs/legacy-stored-unit-placement.md`
(PR #271, merged `6bb7a46`) and the approved artifacts are
`openspec/changes/2026-10-03-stored-item-placement/`.

### The finding: `place_stored_item` is **not** a refusal line

The investigation was told to measure rather than assume, and the assumption
would have been wrong. `place_stored_item` and `sell_stored_item` are two
`command.py` branches (`command.py:233-256`) that **place a row on the map** and
**remove a storage entry**, both **unguarded**, both **type-agnostic** (no
building/unit distinction), and both charging **nothing**. **24 executed probe
transactions** established the contract rather than one recorded transaction
guessing at it.

Legacy argument shapes, confirmed at `command.py:233-248`:

| slot | meaning | source |
| --- | --- | --- |
| `args[0]` | `item_index` — **client-sent**, and the map key it becomes | 233 |
| `args[1]` | `item_id` — client-sent | 234 |
| `args[2]`, `args[3]` | `x`, `y` — client-sent, stored verbatim | 235–236 |
| `args[4]` | `playerID` | 238 |
| `args[5]` | `orientation` | 239, passed at 245 |
| `args[6]` | `unknown_autoactivable_bool` | 240 |
| `args[7]` | `unknown_imgIndex` | 241 |

*"appears on exactly one line"* is true only **branch-scoped** for `playerID`
and `orientation` (whole-file: `args[4]`×7, `args[5]`×4, `args[6]`×4,
`args[7]`×2) and **globally unique** only for `unknown_autoactivable_bool` and
`unknown_imgIndex`. The suite asserts **both** scopes separately, because the
first draft of the suite asserted the stronger one and it was false.

### Five of eight row slots are server-derived, and three are not

`engine.map_add_item` (`engine.py:31`) is a bare assignment, and the storage
removal at `engine.py:78` is conditional on the count reaching zero. So a placed
row's slots 0, 1, 2 come from the client while **3 (server clock), 4
(orientation), 5 (garrison), 6 (attr), and 7 (team)** are derived — and the
attribute bag is derived from **committed content**, which makes this the
project's second content-derived, server-authoritative write.

### The capture seeds itself through committed content

The committed corpus's `maps[0]["store"]` is `{}`, so there is nothing to place.
The only content-derived seeding route is `complete_collection(1)`, whose prize
is **exactly** `{"1085": 1}` — so the recorded transaction chain is
`login_post` → `complete_collection(1)` → `place_stored_item` →
`complete_collection(1)` → `sell_stored_item`, with **no fabricated player state
and no client-sent item list anywhere**.

Verified fixture facts: the placement changed exactly **3** top-level paths
(`maps[0].items.41`, `maps[0].store.1085`, `privateState.boughtUnits`) = 8
leaves, with the placement count 40 → 41; the sale changed exactly **1** leaf
(`maps[0].store.1062` **removed**) and **no** refund; `login_post` changed **0**
leaves; and **all seven stored resources are byte-identical in all five steps**,
which is what makes every "charges nothing" claim non-tautological.

### Four unguarded behaviours: three refused, one recorded

The endpoints refuse `unknown_item_id`, `item_not_placeable`, and
`not_in_storage`, in that **order** (pinned to `compat_service.py:1562`, `:1570`,
`:1596`). The **fourth** unguarded behaviour — accepting an out-of-grid cell — is
the **already-recorded M6 tile-to-cell geometry gap**, so it is *recorded and
reported* rather than refused: inventing a bound would fabricate a rule the
oracle does not have, and closing the gap needs new **evidence**, not a
derivation. `slot_occupied` is not a contradiction of this — it destroys an
**existing** row and is invisible to any count-based check.

### The seam in `test_unit_collection.gd` had to be amended, not deleted

That suite's `_check_boundary()` asserted `place_stored_item` was absent from
**every** client source. That claim became **false** the moment this line landed,
and asserting it would assert something untrue at exactly the moment it stopped
being true. The whole-tree absence was replaced by an **ownership claim** — and
because two suites scanning the same tree for the same token with two
hand-maintained owner lists is drift waiting to happen, the *owner* list lives
only here (`STORAGE_OWNERS`) while the collection suite asserts the hand-off's
**recipient exists and asserts it**. `BEHAVIOUR_NEEDLES` lost the token; the two
collection modules are now asserted to declare **no** storage command, which is
the absence that is still this line's own.

### Four defects the hermetic suite structurally could not catch

The offline suite builds its own envelope, so **544 hermetic checks passed while
the live phase failed four separate times**. All four were found only by
`stored-placement-live`:

- the bootstrap payload is keyed `map` (singular) — it is the legacy
  `get_player_info()` body verbatim — while the recorded **fixture** documents are
  keyed `maps[0]`. Reading one with the other's accessor returns `{}` silently,
  so the pre-seed storage check passed **for the wrong reason** and the
  post-seed one failed. Both accessors are now separately named;
- `CollectionResult` has **no** `count_after`, so a whole-function abort left
  steps D and the refusals never executed;
- the service's and the client's copies of the recorded geometry and quantity
  notes are **deliberately not identical** (the service cites source lines and
  probe numbers; the client's copy is the readout string). The suite had asserted
  byte-equality and claimed "verbatim" — a claim **stronger than anything true**,
  which failed honestly. It is now a **clause** check over the identifying text,
  which is what the client actually depends on;
- the sale's ledger append is **if-absent**, so a repeat completion grants the
  prize again while the collection ledger **stands still** — the opposite of what
  the first draft asserted, and the fact that makes step D possible at all.

### The by-name guard was weaker than it looked, and was found by injection

Injecting `static func refund_for(item_id: int) -> int` tripped the
whole-inventory pin and **nothing else**, because the by-name guard matched only
the exact name `refund`. That is the same helper wearing a disguise, so a
substring check was added — and the finding is recorded in the suite rather than
quietly fixed, because the whole-inventory pin is the real gate and the
by-name guard is the belt.

### Verification actually run (2026-10-03/04)

```bash
python -B apps/compat-api/capture_stored_placement_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_stored_item_placement.gd
godot --headless --path apps/client-godot --script res://tests/test_stored_item_placement.gd -- --report=<repo>/apps/client-godot/evidence/stored-placement/report.json
godot --headless --path apps/client-godot --script res://tests/test_unit_collection.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
openspec validate --all --strict
```

- fixture capture: exit **0** on **four** consecutive runs, containment **UNCHANGED**
  (`18e5e55b…a724`). Re-runnability was **measured**, not assumed: every byte is
  reproducible except `captured_at_utc`, `executed_at_utc`, the `Date` header,
  and the signed envelope `ts` (which drags its own digest and the save digests of
  the documents containing the placed row with it). Normalizing exactly those
  four kinds made the whole directory byte-identical; not normalizing them made
  every file carrying one differ. The full list is pinned in the manifest under
  `time_dependent_fields.leaves`.
- compat suite **`Ran 2130 tests ... OK`**, exit 0 — **+216** over the 1,914
  baseline, because this line adds two state-mutating routes, the envelope
  module, and three test modules.
- the hermetic suite: **544 checks** — the **39th** hermetic suite
- `verify.ps1` exit **0**; `verify-boot.ps1` exit **0** with **39 hermetic suites
  and 20 live phases**, guard digest `6978b959…ff348` identical pre/post
- `test_unit_collection.gd` **1,894** (the amended boundary), `test_project_scope.gd`
  **1,781**, `test_game_api_fake.gd` **1,322**, `test_unit_production.gd` **568**,
  `test_unit_animations.gd` **628**, `test_unit_behaviors.gd` **573**,
  `test_research.gd` **1,024**, `test_quests.gd` **1,223**, `test_tutorial.gd`
  **639**, `test_scene_build.gd` **36**, `test_content_registry.gd` **87**
- content validator exit **0**, `result: valid`, 21 schemas; preservation manifest
  **3,258 entries**, exit 0; `openspec validate --all --strict` **60 passed / 0 failed**
- evidence: `evidence/stored-placement/report.json`, `stored-placement-report-v1`,
  digest **`c5bea9dd…8d18`**, 13,618 bytes, byte-identical across **four**
  consecutive runs. **No windowed capture is committed, because this line renders
  nothing** — the four M7 buildings' PNGs are the only windowed evidence in the
  tree and this line adds none.

**Two anti-invention guards, both proven by injection.** Injecting
`static func cell_is_free(from_cell: int, to_cell: int) -> bool` produced **3
independent failures** and exit 1; injecting `static func refund_for(item_id: int)
-> int` produced **2** after the substring guard was added and **1** before it;
restoring the byte-identical module (SHA-256 `0b437e5d…0edbd`) returned the suite
to its 544-check passing state and exit 0 both times.

### One pre-existing flake was found by this battery and fixed

`verify-boot.ps1` failed its compat step once with
`test_collection_endpoint.ContainmentTests.test_session_stays_byte_identical…`
reporting `server_time` **1791066504** against **1791066505** and every other
field identical; three immediate reruns passed. `/v0/session` stamps the current
time on every response, so two calls that straddle a second boundary were always
going to fail a whole-document equality — the assertion was **testing the clock,
not the session list**. The fix was then found to be wrong in the **other**
direction, by running that file alone: when both calls land inside one second the
clock does *not* differ, so demanding a difference fails. The assertion is
therefore that the differing-field set is a **subset** of the documented volatile
field — `[]` or `["server_time"]`, never anything else — which is the only claim
true in both cases and exactly as strict about every other field as the
whole-document equality was. That guard was made to fail rather than trusted:
injecting a real session-list change (`after_list["saves"] = []`) produced
`AssertionError: {'saves'} not less than or equal to {'server_time'}`, and
restoring the byte-identical file (SHA-256 `8efd62d8…7ab6`) returned it to 36
tests and `OK`.

### Claim limits

**The round trip only** — storage to map and storage to gone, with no
intermediate step · **no price in either direction**: a placement is free and a
sale credits nothing, because the legacy refund travels in **client-sent deltas**
this contract refuses · **no capacity, expiry, value, or price rule** — the
committed configuration records none and the legacy server has none · **no bounds
and no occupancy check** — the M6 geometry gap is recorded and reported, never
refused · **no refund is claimed** and none is paid · **`store_add_items` is out
of scope** — it is an unvalidated client-sent grant and is probe-only here ·
**placement is type-agnostic**, exactly as the legacy branch is, so a building
prize is placed through the same route · **four of the ten committed collection
prizes are buildings**, and because occupancy is unchecked this line cannot give
any 2×2 or 3×3 prize a correct cell; it ships on the 1×1 Metal Draggy prize and
records the rest · **nothing is rendered**: there is no windowed capture and no
pixel-parity oracle, and storage remains a readout · **no unit is moved, trained,
or animated**, and `production`, `movement`, `animations`, and `basic behaviors`
remain undelivered · **parity covers five recorded transactions against the
fresh-player corpus only**, and no progressed-player save exists · the
**committed capture's two stored resources** are the fake's fixture, so
real-execution parity rests on the fixture-replay tests and the live phase ·
No Flash, Ruffle, ActionScript, or browser executes in any of these commands, and
every network call is loopback.