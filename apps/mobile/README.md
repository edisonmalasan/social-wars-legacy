# Mobile shell — config only

This directory is the **config-only** Capacitor scaffold for the mobile
shell. It contains `capacitor.config.ts`, this `package.json` and this
README — nothing else.

There is **no native project here**. No `android/`, no `ios/`, no generated
Xcode or Gradle project, no signing and no build. Those are produced by the
`cap add` / `cap sync` commands below, on a machine that has the toolchains,
and are deliberately not run in this repository.

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
- A reachable **deployment of the game server**, and its HTTPS URL.
- At native-work time only: **Capacitor CLI and core** (exact commands below).
  They are not installed in this scaffold.
- For Android: a **JDK 17**, the **Android SDK** and **Android Studio**.
- For iOS: a **macOS host**, **Xcode** and **CocoaPods**.

None of the native tooling above exists in the environment where this
scaffold was added; the commands below are documented, not run.

## Commands

Run from the repository root. These generate native projects and require the
prerequisites above — they are intentionally not executed here.

```bash
pnpm install
pnpm --filter @swl/app-client build

# Install the Capacitor toolchain when native work starts.
pnpm --filter @swl/app-mobile add -D @capacitor/cli
pnpm --filter @swl/app-mobile add @capacitor/core

# Point server.url in capacitor.config.ts at the real deployment, then:
pnpm --filter @swl/app-mobile exec cap sync

# Generate the native projects (the first time only):
pnpm --filter @swl/app-mobile exec cap add android
pnpm --filter @swl/app-mobile exec cap add ios

# Open them in their IDEs to build and run on a device or emulator:
pnpm --filter @swl/app-mobile exec cap open android
pnpm --filter @swl/app-mobile exec cap open ios
```

## Scope and non-claims

- This is a **config scaffold**, not a mobile build. It does not produce an
  APK, an IPA, or anything installable.
- No Android or iOS project has been generated, compiled or run, and no
  device or emulator was used. The roadmap's device-dependent G5 boxes stay
  open.
- Touch convenience is a property of the one shared web client, not of this
  shell; this config only wires that client into a WebView.
