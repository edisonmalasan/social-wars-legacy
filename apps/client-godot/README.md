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
loopback smoke → the ten headless Godot suites → the unreachable-endpoint
scenario against a port with nothing listening → three live phases → guard
baseline again → `evidence/boot/boot-report.json`. Each live phase is wrapped
by `compat_live_phase.py`, which starts `apps/compat-api/run.py`, waits for
`GET /v0/session`, runs exactly one Godot command, stops the service with
`CTRL_BREAK`, and asserts the service exited 0, the disposable corpus was
removed, no new `socialwars-compat-*` directory is left in temp, no
working-tree `saves/` exists, and the port is released. Exit code is `0` only
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
# Failure path: the scene must enter the explicit error state (suite exits 0
# only when it observed it)
godot --headless --path apps/client-godot -s res://tests/test_boot_scene.gd -- --scenario=unreachable --gameapi-endpoint=http://127.0.0.1:5057
# Live phases (each starts and tears down the service itself)
python -B apps/client-godot/compat_live_phase.py --port 5056 --name live -- <godot> --headless --path apps/client-godot -s res://tests/test_game_api_live.gd
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
