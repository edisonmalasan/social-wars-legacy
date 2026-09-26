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
  ordinal-sorted, `sha256␠␠path\n`) and of the three manifest files.
- Godot discovers and reports engine `4.7.2.stable` exactly.
- All three headless test suites exit 0 and print `[test] PASS`
  (observed check counts: loader 123, scene-build 36, project-scope 291).
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

All four are AND-ed: the run fails if any is violated, and the report lists
every violated criterion under `failures`. The reference comparator never
reads the captured PNG — it re-decodes the package with its own file reads
and straight-alpha over-blend — so a green result is a real cross-check.

### Self-test (tolerance sensitivity)

`run_selftest.gd` perturbs a 24×24 block of the rendered frame with opaque
red before comparison. Measured outcome: exit `1`, `[selftest] DETECTED`,
`pixels_over_tolerance = 576` (= 24×24), `max_abs_per_channel.r = 191`,
and the two recorded failures
`mean_abs.r = 1.113 exceeds 0.5` and
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
