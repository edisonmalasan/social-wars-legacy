# Desktop Distribution Plumbing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Tauri shell actually shippable on this host — real client in `frontendDist`, a built server sidecar, packaged builds using the sidecar instead of `node` + the repo — plus mock-tested updater/rollback logic. Attempt one unsigned Windows installer as evidence. Do not claim signing, macOS/Linux builds or a live update stream.

**Architecture:** Keep the desktop shell a thin window + server (ADR 5/6). Fix the documentation/code discrepancy (`build-desktop-server.mjs` missing; `lib.rs` always uses the development command). Add pure, injectable Rust seams for updater decisions/rollback and test them with `tempfile`/synthetic manifests. No new runtime dependency; the existing `cargo test`/`fmt` CI job proves the Rust half.

**Tech Stack:** Node scripts, Tauri v2 (Rust, tauri.conf.json), Node test runner, Cargo test.

**Spec:** `docs/GOAL.md` §D/§5, `docs/ROADMAP.md` Group H, `apps/desktop/src-tauri/server/README.md`, ADR 5/19.

## Global Constraints

- No signing key, notarization, macOS/Linux host, public endpoint or Flash asset. No false installer/platform/release claim.
- Packaged builds must not require `node` on PATH or the source repository; the sidecar path must be tested.
- Existing 20 Rust unit tests and CI's `cargo check --locked`, `cargo test --locked`, `cargo fmt --check` stay green.
- No new runtime dependency; no weakened check; 401-item roadmap accounting unchanged.
- The roadmap's "Installers are produced for Windows (.msi + .exe), macOS and Linux" stays open after an unsigned Windows attempt — it requires all platforms.

## Review Focus

- Does the packaged server target actually use the sidecar, and is that covered by a Rust test?
- Does `apps/desktop/dist` contain the real built client, not the 162-byte placeholder?
- Is the updater/rollback logic pure, mock-tested and honest about what it cannot verify (real signature/live endpoint)?
- Is an attempted installer an actual artifact with a recorded command/output, not an assumption?

---

### Task 1: Shippable frontend and server sidecar

**Files:** `scripts/build-desktop-server.mjs` (new), `scripts/prepare-desktop.mjs`, `apps/desktop/src-tauri/src/lib.rs`, `tauri.conf.json`, `server/README.md`, tests.

- [ ] Step 1: failing Rust tests: packaged target selection resolves to the sidecar (not the development `node` command); `to_command()` for the sidecar yields the configured binary; frontend `dist` contains the real client's index (script-level check).
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement `build-desktop-server.mjs` producing the server sidecar (Node single-file/bundle of `apps/server` + content bundle, using existing tooling where possible); make `prepare-desktop` copy the real built client into `apps/desktop/dist`; wire `bundle.externalBin` and `ServerCommand::Sidecar` for packaged builds while preserving the dev path.
- [ ] Step 4: focused tests, `pnpm test`, `pnpm typecheck`, `pnpm lint`, `cargo test --locked`, `cargo fmt --check`, `check-no-flash`, `check-licensing`.
- [ ] Step 5: commit `feat(desktop): ship the real client and a server sidecar`.

### Task 2: Mock-tested updater/rollback logic

**Files:** `apps/desktop/src-tauri/src/updater.rs` (new), `lib.rs`, `Cargo.toml` only if needed, tests.

- [ ] Step 1: failing Rust tests for manifest/version parsing, choosing an update, recording install attempts, and planning rollback to last-known-good on a failed install — using synthetic fixtures/no network.
- [ ] Step 2: confirm RED.
- [ ] Step 3: implement the pure seams and wire a `#[tauri::command]` shell only if needed by the existing UI; document that signature verification/live endpoints remain blocked.
- [ ] Step 4: `cargo test --locked`, `cargo fmt --check`, plus the workspace gates.
- [ ] Step 5: commit `feat(desktop): add mock-tested updater and rollback logic`.

### Task 3: Bounded installer attempt and documentation

**Files:** `docs/ROADMAP.md`, `docs/DEVELOPING.md` if needed, task report.

- [ ] Step 1: attempt ONE unsigned Windows NSIS `.exe` with the globally installed `tauri` CLI; record the exact command, output and artifact (or the precise blocker). Do not assume success; do not attempt MSI/macOS/Linux.
- [ ] Step 2: run all GOAL §7 gates; record exact results.
- [ ] Step 3: correct the stale Group H blocker row evidence (CLI present, NSIS cached, WiX auto-downloadable, hosts still absent) and record only verified outcomes outside Group headers; keep 401 accounting and prior history. Signing/notarization/live update/publication stay blocked.
- [ ] Step 4: commit `docs(roadmap): record desktop distribution progress`.
