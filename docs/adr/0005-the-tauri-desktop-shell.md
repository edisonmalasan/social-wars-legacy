# 5. The desktop shell is Tauri v2

**Status:** accepted

## Context

The game has to run on Windows, macOS and Linux as a standalone
executable, with a local server, and without Flash.

## Decision

A **Tauri v2** shell that wraps the same web client, with a Rust
backend that starts the local server and points a web view at it.

## Alternatives

- **Electron.** It bundles a Chromium, so the installer is large and the
  browser version drifts with the build. Tauri uses the operating
  system's own web view.
- **A native UI.** It would be a second implementation of the client.
- **A browser tab.** It is not a standalone application, and it cannot
  start a local server.

## Consequences

The installer is small and the web view is the platform's own. The
fallback is Electron, if WebView2 or WebGL2 proves problematic on a
target platform. The shell is a library with a thin binary, so its
logic is testable without opening a window.
