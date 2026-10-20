import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { PGlite } from '@electric-sql/pglite';

import {
  MIGRATIONS_TABLE,
  MigrationError,
  checkHistory,
  currentVersion,
  rollbackMigrations,
  runMigrations,
  type Migration,
} from './migrations.ts';

const FIRST: Migration = {
  version: 1,
  name: 'the player saves',
  up: ['CREATE TABLE player_saves (player_id TEXT PRIMARY KEY, doc JSONB NOT NULL)'],
  down: ['DROP TABLE player_saves'],
};

const SECOND: Migration = {
  version: 2,
  name: 'the social state',
  up: ['CREATE TABLE social (id TEXT PRIMARY KEY, doc JSONB NOT NULL)'],
  down: ['DROP TABLE social'],
};

/**
 * A migration that cannot be undone safely: it drops a column, so there is
 * no way back.
 */
const IRREVERSIBLE: Migration = {
  version: 3,
  name: 'the dropped column',
  up: ['ALTER TABLE player_saves ADD COLUMN legacy TEXT', 'ALTER TABLE player_saves DROP COLUMN legacy'],
};

async function database(): Promise<PGlite> {
  return PGlite.create();
}

describe('the migration runner', () => {
  it('starts at version 0', async () => {
    const db = await database();
    assert.equal(await currentVersion(db), 0);
  });

  it('runs the migrations in order', async () => {
    const db = await database();
    const report = await runMigrations(db, [FIRST, SECOND]);
    assert.equal(report.from, 0);
    assert.equal(report.to, 2);
    assert.deepEqual(
      report.applied.map((migration) => migration.version),
      [1, 2],
    );
    assert.equal(await currentVersion(db), 2);
  });

  it('records what it ran', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND]);
    const rows = await db.query<{ version: number; name: string }>(
      `SELECT version, name FROM ${MIGRATIONS_TABLE} ORDER BY version`,
    );
    assert.equal(rows.rows.length, 2);
    assert.equal(rows.rows[0]!.name, 'the player saves');
    assert.equal(rows.rows[1]!.name, 'the social state');
  });

  it('is idempotent', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND]);
    const second = await runMigrations(db, [FIRST, SECOND]);
    assert.deepEqual(second.applied, []);
    assert.equal(second.from, 2);
  });

  it('runs only the migrations that are missing', async () => {
    const db = await database();
    await runMigrations(db, [FIRST]);
    const report = await runMigrations(db, [FIRST, SECOND]);
    assert.deepEqual(
      report.applied.map((migration) => migration.version),
      [2],
    );
  });

  it('rolls a migration back', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND]);
    const report = await rollbackMigrations(db, [FIRST, SECOND]);
    assert.equal(report.applied.length, 1);
    assert.equal(report.applied[0]!.version, 2);
    assert.equal(await currentVersion(db), 1);
  });

  it('refuses to roll back a migration that cannot be undone', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND, IRREVERSIBLE]);
    const report = await rollbackMigrations(db, [FIRST, SECOND, IRREVERSIBLE]);
    assert.equal(report.notReversible.length, 1);
    assert.equal(report.notReversible[0]!.version, 3);
    // The schema is where it was: the run stopped rather than skipping it.
    assert.equal(await currentVersion(db), 3);
  });

  it('refuses a schema that is newer than the server', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND]);
    await assert.rejects(
      runMigrations(db, [FIRST]),
      (error: unknown) =>
        error instanceof MigrationError && error.reason === 'unknown-version',
    );
  });

  it('refuses two migrations with the same version', async () => {
    const db = await database();
    await assert.rejects(
      runMigrations(db, [FIRST, { ...FIRST, name: 'another' }]),
      (error: unknown) =>
        error instanceof MigrationError && error.reason === 'history-mismatch',
    );
  });

  it('checks the history against the migrations', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND]);
    const check = await checkHistory(db, [FIRST, SECOND]);
    assert.equal(check.ok, true);
    assert.deepEqual(check.problems, []);
  });

  it('spots a migration that was renamed after it ran', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND]);
    const check = await checkHistory(db, [FIRST, { ...SECOND, name: 'renamed' }]);
    assert.equal(check.ok, false);
    assert.equal(check.problems.length, 1);
  });

  it('spots a migration the server does not know', async () => {
    const db = await database();
    await runMigrations(db, [FIRST, SECOND]);
    const check = await checkHistory(db, [FIRST]);
    assert.equal(check.ok, false);
  });

  it('leaves the schema alone when a migration fails', async () => {
    const db = await database();
    const broken: Migration = {
      version: 1,
      name: 'broken',
      up: ['CREATE TABLE ok_table (a INT)', 'THIS IS NOT SQL'],
    };
    await assert.rejects(runMigrations(db, [broken]));
    // The transaction was rolled back, so the first statement's table is
    // not there either.
    const result = await db.query<{ n: number }>(
      `SELECT count(*)::int AS n FROM information_schema.tables
       WHERE table_name = 'ok_table'`,
    );
    assert.equal(result.rows[0]!.n, 0);
    // And the history is empty.
    assert.equal(await currentVersion(db), 0);
  });
});
