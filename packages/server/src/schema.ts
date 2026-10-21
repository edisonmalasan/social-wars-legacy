/**
 * The server's own schema.
 *
 * The server's tables are **versioned**, and they move by **migration**
 * rather than by a `CREATE TABLE IF NOT EXISTS` at startup. An
 * `IF NOT EXISTS` can only ever add a table, and it says nothing about
 * what happened to the ones that were already there: a column that a new
 * server needs would be added by hand, and the hand-added column would be
 * in no migration's history.
 *
 * So the schema is a list of migrations, each of which brings the schema
 * from one version to the next:
 *
 * - **Forward only.** A migration moves the schema from version *n* to
 *   version *n + 1*. There is no "migrate everything at once" step, so a
 *   deploy that is interrupted leaves the schema at a version the server
 *   understands.
 * - **Reversible where safe.** A migration may declare a `down`, and then
 *   it can be rolled back. One that cannot be undone safely declares no
 *   `down`, and the runner refuses to roll it back rather than pretending
 *   it can.
 * - **Recorded.** Every migration that runs is written to the history
 *   table with its version, its name and the time it ran, so the schema's
 *   history is in the database rather than in a log file.
 * - **Checked.** The runner refuses to run against a schema whose version
 *   it does not know, in either direction.
 *
 * The runner itself is in `migrations.ts`.
 */
import type { Migration } from './migrations.ts';

/** The table the players' saves live in. */
export const PLAYERS_TABLE = 'player_saves';

/** The table the social documents live in. */
export const SOCIAL_TABLE = 'social';

/** The table the players' credentials live in. */
export const CREDENTIALS_TABLE = 'credentials';

/** The schema's migrations, in order. */
export const SCHEMA_MIGRATIONS: readonly Migration[] = [
  {
    version: 1,
    name: 'create the players table',
    up: [
      `CREATE TABLE IF NOT EXISTS ${PLAYERS_TABLE} (
        player_id TEXT PRIMARY KEY,
        doc       JSONB NOT NULL,
        updated   TIMESTAMPTZ NOT NULL DEFAULT now()
      )`,
    ],
    down: [`DROP TABLE IF EXISTS ${PLAYERS_TABLE}`],
  },
  {
    version: 2,
    name: 'create the social table',
    up: [
      `CREATE TABLE IF NOT EXISTS ${SOCIAL_TABLE} (
        kind    TEXT PRIMARY KEY,
        doc     JSONB NOT NULL,
        updated TIMESTAMPTZ NOT NULL DEFAULT now()
      )`,
    ],
    down: [`DROP TABLE IF EXISTS ${SOCIAL_TABLE}`],
  },
  {
    version: 3,
    name: 'index the players table by its update time',
    up: [`CREATE INDEX IF NOT EXISTS ${PLAYERS_TABLE}_updated_idx
          ON ${PLAYERS_TABLE} (updated DESC)`],
    down: [`DROP INDEX IF EXISTS ${PLAYERS_TABLE}_updated_idx`],
  },
  {
    version: 4,
    name: 'create the credentials table',
    up: [
      `CREATE TABLE IF NOT EXISTS ${CREDENTIALS_TABLE} (
        player_id     TEXT PRIMARY KEY,
        salt          TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
      )`,
    ],
    down: [`DROP TABLE IF EXISTS ${CREDENTIALS_TABLE}`],
  },
];

/** The version the schema is at when everything has run. */
export const SCHEMA_VERSION = SCHEMA_MIGRATIONS[SCHEMA_MIGRATIONS.length - 1]!.version;

/** The tables the server owns, for a backup. */
export const SERVER_TABLES = [PLAYERS_TABLE, SOCIAL_TABLE] as const;
