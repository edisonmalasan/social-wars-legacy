# The bundled server

The desktop shell ships the project's own server, so a player needs
nothing installed — not Node, and not this repository.

Build the sidecar before packaging the shell:

```console
node scripts/build-desktop-server.mjs
```

Run from the repository root, after `pnpm install` and `pnpm build:content`.

## What the build produces

Two things, both **generated** (neither is committed):

1. `src-tauri/binaries/swl-server-<target-triple>[.exe]` — a copy of the
   Node binary that ran the build. Tauri's `bundle.externalBin` places it
   beside the application's executable. `TAURI_ENV_TARGET_TRIPLE` selects
   the triple; otherwise it is derived from the build machine's platform
   and architecture, so a cross-build must set the variable.

2. `src-tauri/server/runtime/` — a self-contained copy of the server:
   - `start.mjs`, which makes the runtime directory the working directory
     for relative data paths and imports the server entry. Content is **not**
     read from `process.cwd()`: the server resolves the bundle from its own
     module URL (`contentPathFrom(import.meta.url)` in
     `apps/server/src/content-path.ts`), so the working directory no longer
     decides where content comes from;
   - `apps/server/src/` and `node_modules/@swl/{protocol,rules,server}/`,
     the server and the three workspace packages it imports, with their
     `.ts` files stripped to `.mjs` by Node's own `stripTypeScriptTypes`
     and their relative imports rewritten to match (tests excluded);
   - `package.json` manifests in each `@swl` package preserving the
     subpath exports (`@swl/server/apply`, and so on);
   - `packages/content/dist/content-bundle.json`, the same bundle the web
     client and the authority use;
   - `node_modules/@electric-sql/pglite/`, the server's only external
     dependency (Apache-2.0, plain files and WASM, no native addon).

The transform is a straight type strip, so the sidecar runs the same code
as the repository server; it happens at build time because Node does not
strip types from files under `node_modules`. Nothing is downloaded and no
new dependency is introduced: every file comes from this workspace.
`node scripts/build-desktop-server.mjs` is safe to run again — the
generated tree is replaced, not patched.

## How the shell starts it

`ServerCommand::Sidecar` runs the binary Tauri placed beside the
executable, passing it the absolute path to `runtime/start.mjs`. In
development the shell still runs `node apps/server/src/main.ts` from the
repository, so both paths are exercised by the same code with different
commands. The choice is `!tauri::is_dev()`, which is the packaged build's
`custom-protocol` feature rather than a build-profile guess.

Either way the shell starts the child with two environment variables:

- `PORT` — the port selected by `--port` (default `8080`). Without this the
  server would keep its own default while the web view and the health check
  looked at the flag's port. The server's `HOST` is left alone, so it still
  binds only `127.0.0.1`.
- `SWL_DATA_DIR` — a writable `server-data/` directory under the current
  user's application data directory (`app.path().app_data_dir()`). The
  server keeps its PGlite database, saves and credentials there, so they
  survive a restart. The shell only chooses the location; the server stays
  authoritative and no client writes the save (ADR 19).

A missing or stale sidecar is not hidden: the shell waits for the server's
health check and reports a clear error instead of pointing the window at
an empty page. The frontend is checked separately by
`node scripts/check-desktop-dist.mjs`.
