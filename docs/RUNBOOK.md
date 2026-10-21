# The runbook

What to do when the server is unhappy. Each section is a **failure**,
what it looks like, and what to do about it.

The commands are in [`../AGENTS.md`](../AGENTS.md). The service's own
state is at **`/api/health`** and **`/dashboard`** — open the dashboard
first; it carries the versions in use, the measurements and the alerts
that are firing.

## Before anything else

```bash
node scripts/check-roadmap.mjs          # is the tree whole?
node scripts/golden-master.mjs          # does the rules still match the original?
node scripts/run-cheat-battery.mjs      # does the server still refuse the cheats?
```

A failure in any of those is a problem with the **build**, not with the
running server. Do not restart a server to fix a build.

## The deployment is stalled

**Looks like:** the deploy script has not finished, or the server is not
answering `/health`.

1. Open the dashboard. Is the schema at the version the server expects?
2. `node scripts/migrate.mjs --data <dir> --status` — the schema's
   version and what is pending.
3. The migration runs in its own transaction, so a failed migration
   leaves the schema at the version the server understands. Fix the
   migration and run it again; the server can be running the whole time.
4. `node scripts/deploy.mjs --data <dir> --rollback` puts the database
   back to the snapshot the deploy took.

**Do not** skip the migration by starting the server against an old
schema. The server refuses to serve a schema it does not understand,
and that is the point.

## The database has failed

**Looks like:** the server answers 500s, or not at all, and the
dashboard's error rate is at 1.

1. Is the database **there**? The database is a **directory**
   (`SWL_DATA_DIR`), and it is a PostgreSQL one — PGlite — so the
   directory is the whole database.
2. `node scripts/backup-server.mjs --data <dir> --out <dir> --verify`
   — a backup, and a verification that it matches the live database.
3. If the database is corrupt: restore the most recent snapshot.
   `node scripts/backup-server.mjs --restore <dir> --data <dir>`.
4. If there is no snapshot, the players' worlds are in the **upstream's**
   format and the migration will rebuild them — but their **credentials**
   are not, so they will have to register again.

## A player's state is corrupt

**Looks like:** one player cannot play, and the server's logs mention
that player's id.

1. The player's world is **one row** in `player_saves`. The migration
   is what reads it, and a document from a version the server does not
   understand is **refused**, not guessed at.
2. `node scripts/backup-server.mjs --data <dir> --out <dir>` — take a
   snapshot **before** touching anything.
3. Compare the player's row with the snapshot's. If the snapshot is
   good, restore it. If not, the player's world is rebuilt from the
   upstream's format by the migration, and their **progress** is lost —
   which is why the backup comes first.

## The server is slow

**Looks like:** the dashboard's latency percentile is over its budget,
or the alerts are firing.

1. The budget is **50 ms** for the simulation and **200 ms** for the
   request. The simulation is the rules engine, and the request's time
   also includes the database.
2. If the **simulation** is slow, the rules engine is the problem: a
   battle simulation that is not bounded, or a command that scans the
   whole world.
3. If the **request** is slow but the simulation is not, the database
   is. The store serialises a player's transactions, so one slow player
   blocks that player and nobody else.
4. `node scripts/load-test.mjs` reproduces the measurement without a
   player in the way.

## The alerts are firing

The alert rules are in `packages/server/src/budgets.ts` and
`packages/server/src/health.ts`, and each one says what to do about it.
The two that matter most:

- **`error-rate`** — a tenth of the requests are failing. Look at the
  log: it is a JSON line per request, with the request id. The request
  id is in the response's `x-request-id` header too, so a player can
  quote it.
- **`tick-time`** — the simulation is taking over half a second. The
  server cannot keep up, and the fix is in the rules engine.

## Rolling back

```bash
node scripts/deploy.mjs --data <dir> --rollback
```

It restores the most recent snapshot and prints the digest of the
restored database, so the restore can be checked.

The **rules** can be rolled back without touching the data: the rules
engine is a pure function of the save, so an older engine reading a
newer save is a different question from a newer engine reading an older
save. See [`HOTFIX.md`](HOTFIX.md).

## A player needs resetting

**Looks like:** one player's world is wrong in a way the migration
cannot fix — a building in a tile that is not walkable, a command
counter that is out of step, a resource total that makes no sense.

1. **Take a snapshot first.** Always.
   `node scripts/backup-server.mjs --data <dir> --out <dir>`.
2. The player's world is **one row** in `player_saves`, and the
   credential is **one row** in `credentials`.
3. To give a player a **clean start**, delete their world row. The
   server rebuilds it from the migration on the next sign-in: an empty
   town and the starting resources. The player's **credential** is
   untouched, so they sign in with the same name and password.
4. To **reset a player's password**, delete their credential row and let
   them register again. The password is a salt and a hash, so it cannot
   be recovered — it can only be replaced.
5. To **reset everyone** — the server is a preservation and the world is
   the content, so this is rare and it is destructive. Take a snapshot,
   delete the world rows, and let the migration rebuild them.

The commands are plain SQL against the database, and the database is a
directory, so it can also be opened with any PostgreSQL client.

## The backups

The backup is a **copy of the database directory**, and the database is
a directory, so a backup is a directory copy. The backup is **verified**
before it is trusted: the digest of the snapshot is compared with the
digest of the live database, and a backup that does not match is not a
backup.

```bash
node scripts/backup-server.mjs --data <dir> --out <dir> --verify
node scripts/backup-server.mjs --restore <dir> --data <dir>
```

## The server will not start

1. The schema. `node scripts/migrate.mjs --data <dir> --status`.
2. The content bundle. `pnpm build:content` — the server needs it, and
   a missing one is a missing bundle rather than a broken one.
3. The port. `PORT` is the environment variable, and the default is
   8080.
4. The log. The server writes one JSON line per request, and the
   startup lines say the schema's version and how many players can sign
   in.

## What to write down

When something goes wrong and is fixed, write it down here. The
runbook is only useful if it is **kept**, and a runbook that is
out of date is worse than none: it sends somebody down the wrong path
with confidence.
