# The release checklist

**This is the list that is followed for a production release.** Every step
names the command that does it, so a step cannot be done from memory and
cannot be done differently each time.

The checklist is **checked** by `node scripts/check-release.mjs`: it fails
if a command here does not exist, and it fails if the CI's gate has a
step the checklist does not mention. A checklist that names a command
that no longer exists is a checklist that fails at the worst possible
moment.

## Before anything: the gate

The release does not start until the whole gate is green, on the
commit that is being released. These are the CI's **Verify** job, and
each one is also a step of this checklist.

| The step | The command |
|---|---|
| The vendored upstream tree is unmodified | `node scripts/verify-upstream.mjs` |
| The types are sound | `pnpm typecheck` |
| The project's own rules hold | `pnpm lint` |
| The unit tests pass | `pnpm test` |
| The integration tests pass | `pnpm test:integration` |
| The coverage is above the floors | `node scripts/check-coverage.mjs` |
| The golden-master corpus matches | `node scripts/golden-master.mjs` |
| The server does not leak under a soak | `node --expose-gc scripts/soak-server.mjs --batches 2000 --players 4` |
| The load test meets the budgets | `node scripts/load-test.mjs --players 8 --rounds 20` |
| The content bundle builds and validates | `pnpm build:content` |
| The content build is reproducible | `pnpm build:content` (twice, same build id) |
| The command catalogue agrees with the client | `node scripts/verify-command-catalogue.mjs` |
| The roadmap has not lost an item | `node scripts/check-roadmap.mjs` |
| The cheat battery has no effect | `node scripts/run-cheat-battery.mjs` |
| Nothing that ships needs Flash | `node scripts/check-no-flash.mjs` |
| The licensing position holds | `node scripts/check-licensing.mjs` |
| The licences are classified | `node scripts/build-licence-report.mjs --check` |
| The decision records are well formed | `node scripts/check-adrs.mjs` |
| The security review's claims are covered | `node scripts/check-security-review.mjs` |
| The corrections policy is in order | `node scripts/check-corrections.mjs` |
| The report set agrees with the implementation | `node scripts/check-report-sync.mjs` |
| The web client builds | `pnpm --filter @swl/app-client build` |
| The web client's build is reproducible | `node scripts/check-reproducible-build.mjs` |
| The web client starts in a browser | `node scripts/smoke-test-client.mjs` |
| The end-to-end session works | `node scripts/e2e-test.mjs` |
| The desktop shell compiles and its tests pass | `cargo test` in `apps/desktop/src-tauri` |

## The licence gate — the one that can stop everything

**A public release is blocked until the art and the audio are licensed
or re-created.** The client's sprites, sounds and fonts are Zynga's, and
the shipped tree carries none of them; the position is in
[`LICENSING.md`](LICENSING.md) and it is checked by
`node scripts/check-licensing.mjs`.

Until that is settled the project is **a preservation and a study**: the
code is free, the analysis is published, and the game itself is not
distributed. A release that ignores this is not a release; it is a
distribution of somebody else's art.

## The release itself

1. **The version.** The version is in the root `package.json` and in
   the client's and the server's. The tag is `v<version>`.
2. **The build.** `pnpm build:content` and `pnpm --filter
   @swl/app-client build`. The content bundle's **build id** is
   recorded with the release, so an artefact can be traced to the
   content it was built from.
3. **The artefacts.** The content bundle, the client's manifest and the
   desktop build. The release workflow
   (`.github/workflows/release.yml`) collects them and publishes them
   against the tag, and it runs the whole gate first.
4. **The deploy.** `node scripts/deploy.mjs --data <dir>`. The deploy
   runs the **migrations before it serves anything** — the same
   `SCHEMA_MIGRATIONS` the development server uses, and the same code
   as `node scripts/migrate.mjs --data <dir>` — so a server cannot start
   against a schema it does not understand. The schema's version is
   recorded in the release notes.
5. **The rollback.** `node scripts/deploy.mjs --data <dir> --rollback`
   puts the previous release back. It is exercised in the rehearsal
   below, not assumed.

## After the release

1. **The health.** `http://<host>/api/health` and
   `http://<host>/dashboard`. The dashboard carries the versions in
   use, the measurements and the alerts that are firing.
2. **The metrics.** `http://<host>/metrics`, in the Prometheus text
   format, so a time-series database can scrape it. The JSON is at
   `/api/metrics`.
3. **The alerts.** The webhook is `SWL_ALERT_WEBHOOK`. An alert that
   cannot be seen is not an alert.
4. **The backups.** `node scripts/check-backups.mjs --out <dir>` fails
   when the newest backup is too old. The backups are taken on a
   schedule, and the monitor is what says they are still happening.
5. **The session.** A player registers, signs in, plays and signs in
   again after a restart — the end-to-end test against the **deployed**
   server, not against a local one.

## The rehearsal

Before the first production release, the whole of the above is
rehearsed against a **copy** of the production data:

1. The deploy runs, and the migrations apply.
2. The health, the dashboard, the metrics and the alerts are checked.
3. A player registers, signs in, plays and signs in again.
4. The **rollback** runs, and the previous release serves again.
5. The backups are taken, and the monitor sees them.

A release that has not been rolled back is a release whose rollback
path is a hope.
