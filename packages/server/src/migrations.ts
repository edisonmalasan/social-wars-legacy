/**
 * The schema migrations.
 *
 * The server's own schema has to move as the game does, and it has to move
 * **safely**: a deploy must never leave a player with a save the server
 * cannot read, and it must never silently rewrite one.
 *
 * ## The rules
 *
 * - **Forward only.** A migration moves the schema from version *n* to
 *   version *n + 1*. There is no "migrate everything at once" step, so a
 *   deploy that is interrupted leaves the schema at a version the server
 *   understands.
 * - **Reversible where safe.** A migration may declare a `down`, and then
 *   it can be rolled back. A migration that cannot be undone safely -
 *   one that drops data, say - declares no `down`, and the runner refuses
 *   to roll it back rather than pretending it can.
 * - **Recorded.** Every migration that runs is written to a
 *   `schema_migrations` table with its version, its name and the time it
 *   ran. So the schema's history is in the database, not in a log file
 *   that gets rotated away.
 * - **Checked.** The runner refuses to run against a schema whose version
 *   it does not know, in either direction: a database that is newer than
 *   the server, or one whose history does not match the migrations, is a
 *   failure and not something to guess at.
 */
import type { Database } from './pgstore.ts';

/** One migration. */
export interface Migration {
  /** The version this migration brings the schema TO. */
  version: number;
  /** What it does, for the record. */
  name: string;
  /** The statements that bring the schema forward. */
  up: readonly string[];
  /**
   * The statements that undo it.
   *
   * Absent when the migration cannot be undone safely, and the runner then
   * refuses to roll it back.
   */
  down?: readonly string[];
}

/** The table the history is kept in. */
export const MIGRATIONS_TABLE = 'schema_migrations';

/** The outcome of a migration run. */
export interface MigrationReport {
  /** The version before the run. */
  from: number;
  /** The version after the run. */
  to: number;
  /** The migrations that ran, in order. */
  applied: { version: number; name: string }[];
  /** The migrations that could not be rolled back, if a rollback was asked for. */
  notReversible: { version: number; name: string }[];
}

/** The error a migration run can fail with. */
export class MigrationError extends Error {
  readonly reason:
    | 'unknown-version'
    | 'history-mismatch'
    | 'not-reversible'
    | 'no-down';

  constructor(
    message: string,
    reason: 'unknown-version' | 'history-mismatch' | 'not-reversible' | 'no-down',
  ) {
    super(message);
    this.name = 'MigrationError';
    this.reason = reason;
  }
}

/** The migrations, in order. */
export function ordered(migrations: readonly Migration[]): Migration[] {
  const sorted = [...migrations].sort((a, b) => a.version - b.version);
  for (let index = 1; index < sorted.length; index++) {
    if (sorted[index]!.version === sorted[index - 1]!.version) {
      throw new MigrationError(
        `two migrations claim version ${sorted[index]!.version}`,
        'history-mismatch',
      );
    }
  }
  return sorted;
}

/** Create the history table. */
export async function ensureHistoryTable(db: Database): Promise<void> {
  await db.exec(`
    CREATE TABLE IF NOT EXISTS ${MIGRATIONS_TABLE} (
      version    INTEGER PRIMARY KEY,
      name       TEXT NOT NULL,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `);
}

/**
 * The schema's current version.
 *
 * A schema with no history is at version 0: it has never been migrated.
 */
export async function currentVersion(db: Database): Promise<number> {
  await ensureHistoryTable(db);
  const result = await db.query<{ version: number }>(
    `SELECT max(version)::int AS version FROM ${MIGRATIONS_TABLE}`,
  );
  return result.rows[0]?.version ?? 0;
}

/**
 * Run the migrations.
 *
 * Every migration between the schema's current version and the newest one
 * runs, in order, each in its own transaction, and each is recorded.
 */
export async function runMigrations(
  db: Database,
  migrations: readonly Migration[],
): Promise<MigrationReport> {
  const sorted = ordered(migrations);
  await ensureHistoryTable(db);

  const from = await currentVersion(db);
  const newest = sorted.length > 0 ? sorted[sorted.length - 1]!.version : 0;

  if (from > newest) {
    throw new MigrationError(
      `the schema is at version ${from}, and the server only knows up to ${newest}`,
      'unknown-version',
    );
  }

  const applied: { version: number; name: string }[] = [];
  for (const migration of sorted) {
    if (migration.version <= from) continue;
    await db.exec('BEGIN');
    try {
      for (const statement of migration.up) {
        await db.exec(statement);
      }
      await db.query(
        `INSERT INTO ${MIGRATIONS_TABLE} (version, name) VALUES ($1, $2)`,
        [migration.version, migration.name],
      );
      await db.exec('COMMIT');
      applied.push({ version: migration.version, name: migration.name });
    } catch (error) {
      await db.exec('ROLLBACK');
      throw error;
    }
  }

  return { from, to: newest, applied, notReversible: [] };
}

/**
 * Roll the schema back.
 *
 * Only the migrations that declare a `down` can be undone. A migration
 * that does not is reported rather than silently skipped, and the run
 * stops there: rolling back past a migration that cannot be undone would
 * leave the schema in a state nobody has tested.
 */
export async function rollbackMigrations(
  db: Database,
  migrations: readonly Migration[],
  steps = 1,
): Promise<MigrationReport> {
  const sorted = ordered(migrations);
  await ensureHistoryTable(db);

  const from = await currentVersion(db);
  const applied: { version: number; name: string }[] = [];
  const notReversible: { version: number; name: string }[] = [];

  let target = from;
  for (const migration of [...sorted].reverse()) {
    if (migration.version > from) continue;
    if (applied.length >= steps) break;
    if (!migration.down) {
      notReversible.push({ version: migration.version, name: migration.name });
      break;
    }
    await db.exec('BEGIN');
    try {
      for (const statement of migration.down) {
        await db.exec(statement);
      }
      await db.query(`DELETE FROM ${MIGRATIONS_TABLE} WHERE version = $1`, [
        migration.version,
      ]);
      await db.exec('COMMIT');
      applied.push({ version: migration.version, name: migration.name });
      target = migration.version - 1;
    } catch (error) {
      await db.exec('ROLLBACK');
      throw error;
    }
  }

  return { from, to: target, applied, notReversible };
}

/**
 * Check that the schema's history matches the migrations.
 *
 * A mismatch means the database was migrated by a DIFFERENT set of
 * migrations than the server has - a branch was deployed, or a migration
 * was edited after it ran. Either way the server must not touch it.
 */
export async function checkHistory(
  db: Database,
  migrations: readonly Migration[],
): Promise<{ ok: boolean; problems: string[] }> {
  const sorted = ordered(migrations);
  await ensureHistoryTable(db);

  const result = await db.query<{ version: number; name: string }>(
    `SELECT version, name FROM ${MIGRATIONS_TABLE} ORDER BY version`,
  );

  const problems: string[] = [];
  const known = new Map(sorted.map((migration) => [migration.version, migration.name]));

  for (const row of result.rows) {
    const expected = known.get(row.version);
    if (expected === undefined) {
      problems.push(`the schema has a migration the server does not know: ${row.version}`);
    } else if (expected !== row.name) {
      problems.push(
        `migration ${row.version} is "${row.name}" in the schema and "${expected}" in the server`,
      );
    }
  }

  const version = result.rows.length > 0 ? Math.max(...result.rows.map((row) => row.version)) : 0;
  if (version > (sorted.length > 0 ? sorted[sorted.length - 1]!.version : 0)) {
    problems.push(`the schema is at version ${version}, and the server knows less`);
  }

  return { ok: problems.length === 0, problems };
}
