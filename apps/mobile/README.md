# Mobile shell — config scaffold, with a verified Android debug build

This directory holds the **committed configuration** for the mobile shell:
`capacitor.config.ts`, `package.json`, this README and `.gitignore`. The
Capacitor toolchain is installed at native-work time and the generated native
project (`android/`) and installed dependencies (`node_modules/`) are
gitignored. They are regenerated from the config by the commands below.

## Why it looks like this

There is **one client** (ADR 6): the web build, the desktop shell and this
mobile shell all wrap the same `apps/client` application. Touch handling and
the viewport-safe styling live in that shared client — `renderer.ts`,
`touch.ts`, `ui/css.ts` and `index.html` — so there is no second renderer or
platform-specific screen to maintain.

The product is **pure online** (ADR 19), so the WebView loads the client from
the **same remote server** the browser and the desktop shell use, and every
command goes back to that server. The app does **not** bundle a Node server:
`server.url` in `capacitor.config.ts` points at a deployment of the real
server, and `cleartext` stays `false`.

## Prerequisites

From the repository root:

- **Node.js >= 22** (the workspace's `engines.node`) and **pnpm 12.6.0** (the
  workspace's `packageManager`).
- The shared client built, so `webDir` (`../client/dist`) exists:
  `pnpm --filter @swl/app-client build`.
- **Capacitor CLI, core and Android** at the same version, installed into
  `@swl/app-mobile` at native-work time (not committed, so CI's
  `pnpm install --frozen-lockfile` stays reproducible).
- For Android: a **JDK 21** and an Android SDK with a platform and build-tools
  matching Capacitor's generated Gradle project (API 36 for Capacitor 8).
  No Android Studio IDE is needed for a command-line build.
- For iOS: a **macOS host**, **Xcode** and (optionally) **CocoaPods**.

## Verified Android debug build (Windows, 2026-11-22)

Provisioning used only non-interactive, reversible commands. The SDK lives
outside the repository at `%LOCALAPPDATA%\Android\Sdk` and can be removed by
deleting that directory.

```powershell
# 1. Command-line tools (official Google zip, no credentials or payment).
curl.exe -L --retry 3 --max-time 900 -o "$env:TEMP\commandlinetools-win-11076708_latest.zip" `
  "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
# HTTP 200; 153,583,359 bytes; curl exit 0.

# 2. Extract into the SDK root as cmdline-tools/latest.
$root = "$env:LOCALAPPDATA\Android\Sdk"
New-Item -ItemType Directory -Force -Path "$root\cmdline-tools\latest" | Out-Null
tar.exe -xf "$env:TEMP\commandlinetools-win-11076708_latest.zip" -C $env:TEMP
Move-Item -Force "$env:TEMP\cmdline-tools" "$root\cmdline-tools\latest"
# sdkmanager --version -> 12.0, exit 0.

# 3. Accept licenses non-interactively and install one platform + tools.
$env:ANDROID_HOME = $root; $env:ANDROID_SDK_ROOT = $root
$sm = "$root\cmdline-tools\latest\bin\sdkmanager.bat"
("y`n" * 50) | & $sm --licenses
& $sm "--sdk_root=$root" "platform-tools" `
  "platforms;android-36" "build-tools;36.0.0" `
  "platforms;android-35" "build-tools;35.0.0"
# Both exited 0; "All SDK package licenses accepted".
```

Building the app itself:

```powershell
# From the repository root, with JAVA_HOME set to the installed JDK 21.
pnpm install
pnpm --filter @swl/app-mobile add @capacitor/core@8.6.2 @capacitor/android@8.6.2
pnpm --filter @swl/app-mobile add -D @capacitor/cli@8.6.2
pnpm --filter @swl/app-client build
pnpm --filter @swl/app-mobile exec cap add android

Set-Location apps/mobile/android
& .\gradlew.bat assembleDebug --no-daemon
```

Observed results:

- `cap add android` — exit 0; generated project targets `compileSdkVersion 36`,
  `targetSdkVersion 36`, `minSdkVersion 24`, Gradle wrapper 8.14.3.
- `gradlew.bat assembleDebug --no-daemon` — exit 0,
  `BUILD SUCCESSFUL in 5m 32s`, 93 tasks executed.
- APK: `apps/mobile/android/app/build/outputs/apk/debug/app-debug.apk`,
  **5,437,001 bytes (5.19 MB)**. It contains `classes*.dex`,
  `assets/public` (the built shared client) and Capacitor's native bridge.
  `apksigner verify --print-certs` exits 0 and reports the standard
  auto-generated `CN=Android Debug` certificate — no release signing key.

`node scripts/check-mobile-config.mjs` still validates the committed config
independently of any installed toolchain; it tolerates a locally generated
`android/` and locally installed Capacitor packages, and reports what is and
is not verified.

## Commands for a fresh checkout

```bash
pnpm install
pnpm --filter @swl/app-client build

# Install the toolchain when native work starts (not committed):
pnpm --filter @swl/app-mobile add -D @capacitor/cli
pnpm --filter @swl/app-mobile add @capacitor/core @capacitor/android

# Point server.url in capacitor.config.ts at the real deployment, then:
pnpm --filter @swl/app-mobile exec cap sync
pnpm --filter @swl/app-mobile exec cap add android

# Build the unsigned/debug APK:
cd apps/mobile/android
./gradlew assembleDebug          # Windows: gradlew.bat assembleDebug
```

For iOS (not attempted here): `pnpm --filter @swl/app-mobile exec cap add ios`
on a macOS host with Xcode, then build in Xcode.

## Scope and non-claims

- The committed tree is still a **config scaffold**, not a checked-in native
  project: `android/` and `node_modules/` are gitignored and regenerable.
- The Android **debug APK build is verified**; no release APK or signed
  distributable was produced, and no release signing material exists here.
- **No device or emulator** was used. Loading the APK at runtime would also
  require replacing the placeholder `server.url` with a real deployment; the
  placeholder is deliberately left in the committed config.
- iOS was **not built** — no macOS host or Xcode is available here.
- Touch convenience is a property of the one shared web client, not of this
  shell; this config only wires that client into a WebView.
