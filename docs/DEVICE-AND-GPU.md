# Real-device touch tests and GPU benchmarks — preparation

This page records **capability detection**, a **deterministic large-battle
fixture**, and an **optional frame-timing harness**. It is deliberately
explicit about what did and did not happen:

* **No real-device touch test was run.** No Android device or emulator is
  attached to this host. The detector reports this as `NO DEVICE` and exits
  successfully; it never invents a device and never claims touch input was
  injected.
* **One desktop GPU measurement was taken** on this host (see
  [Results actually obtained](#results-actually-obtained)). It is a
  requestAnimationFrame observation of the built client drawing 300 fixture
  sprites on an NVIDIA RTX 2060 SUPER. It is **not** a release performance
  result, a mobile result, or a pass/fail gate.
* No generated native output (APK, signing material, archives) was added to
  the repository, and nothing was published, distributed, signed or notarised.

## Exact detection commands

| Question | Command |
| --- | --- |
| Toolchain | `node --version` → `v26.10.0`; `pnpm --version` → `12.6.0` |
| Is `adb` installed? | `adb version` (also searched under `ADB`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, `%LOCALAPPDATA%\Android\Sdk\platform-tools`) |
| Is a device attached? | `adb devices -l` |
| Model / API level / touch features | `adb -s <serial> shell getprop ro.product.model`, `adb -s <serial> shell getprop ro.build.version.sdk`, `adb -s <serial> shell pm list features` (all driven by `scripts/device-check.mjs`) |
| Is an NVIDIA card present? | `nvidia-smi --query-gpu=name,driver_version --format=csv,noheader` |
| What video controllers does Windows see? | `Get-CimInstance Win32_VideoController \| Select-Object Name,DriverVersion \| Format-List` (the script also tries `wmic path win32_VideoController get name /value`) |
| Is the **browser** actually accelerated? | `scripts/gpu-benchmark.mjs` reads WebGL `WEBGL_debug_renderer_info.UNMASKED_RENDERER_WEBGL` in a real Chrome/Edge tab. This is the deciding check: a GPU in the machine is not evidence that WebGL uses it. |
| Is the built client available? | `apps/client/dist/index.html` must exist (built with `pnpm --filter @swl/app-client build`) |

Software renderer strings (SwiftShader, llvmpipe, softpipe, lavapipe, WARP,
"Microsoft Basic Render Driver", Mesa offscreen) are classified as
**not accelerated**. When that happens the benchmark skips **before** the
frame loop and prints `NOT A PERFORMANCE RESULT`.

## What was actually detected on this host

### `adb` installation and attached devices

Command: `& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" version`

```text
Android Debug Bridge version 1.0.41
Version 37.0.3-16887417
Installed as C:\Users\Edison\AppData\Local\Android\Sdk\platform-tools\adb.exe
```

Command: `& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices -l`

```text
List of devices attached

(exit=0)
```

There is no device line, so there is no serial, no model, no API level and no
touch feature list to report. `scripts/device-check.mjs --json` therefore
produced (verbatim):

```json
{
  "schemaVersion": 1,
  "tool": "scripts/device-check.mjs",
  "detected": false,
  "reason": "NO DEVICE",
  "adb": {
    "found": true,
    "path": "C:\\Users\\Edison\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe",
    "version": "Android Debug Bridge version 1.0.41",
    "tried": [
      { "path": "adb.exe", "ok": false },
      { "path": "C:\\Users\\Edison\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe", "ok": true }
    ]
  },
  "devices": [],
  "nonUsableDevices": [],
  "touchTests": {
    "performed": 0,
    "reason": "capability detection only; no touch input was injected by this script"
  },
  "apk": null,
  "warnings": [
    "adb answered but no device is in the \"device\" state"
  ]
}
```

The exit code was `0` — a negative result, not a failure.

### GPU hardware and the renderer the browser chose

Commands and output (verbatim):

```text
> nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
NVIDIA GeForce RTX 2060 SUPER, 617.42

> Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | Format-List
Name          : NVIDIA GeForce RTX 2060 SUPER
DriverVersion : 32.0.16.1742

Name          : AMD Radeon(TM) Graphics
DriverVersion : 31.0.21925.1001
```

The browser (not merely the driver) reported:

```text
ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 SUPER (0x00001F06) Direct3D11 vs_5_0 ps_5_0, D3D11)
```

with vendor `Google Inc. (NVIDIA)`, WebGL 2 available and an unmasked renderer
string — classified as `hardware`. Chrome was found at
`C:\Program Files\Google\Chrome\Application\chrome.exe`, version
`Chrome/158.0.8127.37`.

### Existing unsigned debug APK

There is no APK in this worktree. One **does** exist in a sibling worktree,
built there by the `chore/provision-android-sdk` branch. Passing that path to
`--apk` (inspection only — nothing was built, installed or copied) gave this
part of the report:

```json
"apk": {
  "path": "C:\\Users\\Edison\\.t3\\worktrees\\social-wars-legacy\\t3-a2a28f07-a485c3658c6ea931\\apps\\mobile\\android\\app\\build\\outputs\\apk\\debug\\app-debug.apk",
  "exists": true,
  "sizeBytes": 5437001,
  "note": "existing file only; this script did not build or install it"
}
```

With no device attached, the APK was **not installed**, so no touch test was
performed with it.

### The fixture tests

Command: `node --test scripts/lib/battle-fixture.test.mjs`

```text
✔ the large-battle fixture (68.4712ms)
ℹ tests 11
ℹ suites 1
ℹ pass 11
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
```

## How to run

```bash
# 1. Capability detection (no device => exit 0 with reason "NO DEVICE")
node scripts/device-check.mjs                 # human-readable + JSON block
node scripts/device-check.mjs --json          # machine-readable only
node scripts/device-check.mjs --out <file>    # write the report as JSON
node scripts/device-check.mjs --apk <path>    # inspect an EXISTING unsigned debug APK

# 2. The deterministic fixture, with no browser involved
node --test scripts/lib/battle-fixture.test.mjs
node scripts/gpu-benchmark.mjs --fixture-only

# 3. GPU benchmark (needs a hardware WebGL renderer AND the built client)
pnpm --filter @swl/app-client build
node scripts/gpu-benchmark.mjs
node scripts/gpu-benchmark.mjs --json --out <file>
node scripts/gpu-benchmark.mjs --seed repeatable --army-size 200 --frames 300
```

All report files are written only to the path passed with `--out`; the scripts
do not create reports inside the repository, and `device-check.mjs` never
builds or installs an APK.

## Results actually obtained

With the client built (`vite build` reported `✓ built in 12.14s`) and the
fixture's default seed `swl-large-battle-v1` (150 + 150 units, fingerprint
`ff8866c7`), the command

```bash
node scripts/gpu-benchmark.mjs --frames 180 --out <temp>/gpu-report.json
```

produced (verbatim):

```text
GPU benchmark
  nvidia-smi: NVIDIA GeForce RTX 2060 SUPER, 617.42
  system GPUs: NVIDIA GeForce RTX 2060 SUPER; AMD Radeon(TM) Graphics
  browser renderer: ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 SUPER (0x00001F06) Direct3D11 vs_5_0 ps_5_0, D3D11)
  accelerated: true
  frames: 180
  mean: 6.364 ms  median: 6.100 ms  p95: 6.600 ms
  fps (from mean): 157.14
  These are frame timings on this host only, not a release performance result.
  report written to <temp>/gpu-report.json
```

The report's `clientStatus` was `started|started: 300 sprites`: the built
client really constructed and drew all 300 fixture combatants; the renderer
was re-read inside the client page and was still hardware-accelerated before
any timing was collected. A second run with `--frames 120` gave a mean of
`6.313 ms` and `158.39 fps` — the same order of magnitude, as expected.

The skip path was exercised separately:

```text
> node scripts/gpu-benchmark.mjs --browser firefox
GPU benchmark
  nvidia-smi: NVIDIA GeForce RTX 2060 SUPER, 617.42
  system GPUs: NVIDIA GeForce RTX 2060 SUPER; AMD Radeon(TM) Graphics
  browser renderer: unavailable
  accelerated: false
  SKIPPED (NO_BROWSER)
  NOT A PERFORMANCE RESULT: no frame timing was measured.
  - no Chrome or Edge installation was found; WebGL cannot be probed
```

No frame loop was run in that case, and the JSON report had
`"status": "SKIPPED"`, `"performanceResult": false` and the note
`NOT A PERFORMANCE RESULT: no frame timing was measured.`

## Requirements that remain genuinely unavailable

1. **A real Android device or emulator.** `adb devices -l` lists nothing. No
   model, API level or touch-feature list exists to report, so
   `device-check.mjs` reports `NO DEVICE` and `touchTests.performed = 0`.
   Connecting a device (or starting an emulator) is the only way to make this
   available.
2. **A real-device touch test.** None was performed. Injecting touches into a
   device that does not exist would be fabricated evidence, so the scripts
   deliberately do not claim it.
3. **An unsigned debug APK in this worktree.** There is none here. One was
   built in a sibling worktree (`chore/provision-android-sdk`), and
   `device-check.mjs --apk` can inspect it, but there is no device to install
   it on. The script never builds an APK and never commits native output.
4. **A mobile-device GPU result.** The measured numbers are from a desktop
   NVIDIA GPU and a desktop browser. They say nothing about an Android GPU or
   touch latency.
5. **A full-art worst case.** `.work/frames/atlases` is absent on this host.
   The measurement covers scene construction and the render loop with 300
   sprites, but not the complete textured art set. Generating the atlases
   would require the LFS assets, which were not fetched here.
6. **A release performance verdict.** These are single-host, single-run
   observations, not a budget check or a certification. A proper verdict
   needs repeated runs on representative hardware with the release build and
   the full art set.
7. **Signing, notarisation or distribution.** Explicitly out of scope and
   prohibited for this task; nothing was signed, notarised or published.

## Notes on determinism

`scripts/lib/battle-fixture.mjs` imports the repository's own `Random`,
`attackPhase` and `simulateBattle`. It performs no I/O, calls no `Date.now()`
and uses no `Math.random()`; content is injected by the caller. The same
`(seed, content, armySize)` yields byte-identical fixtures and byte-identical
simulation outcomes. The committed content bundle
`apps/client/public/content-bundle.json` supplies the 429 real unit
definitions the pool is drawn from, so a content change changes the fixture.
