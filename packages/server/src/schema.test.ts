import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { PGlite } from '@electric-sql/pglite';

import {
  PLAYERS_TABLE,
  SCHEMA_MIGRATIONS,
  SCHEMA_VERSION,
  SERVER_TABLES,
  SOCIAL_TABLE,
} from './schema.ts';
import { MigrationError, currentVersion, rollbackMigrations, runMigrations } from './migrations.ts';

async function database(): Promise<PGlite> {
  return PGlite.create();
}

describe('the schema', () => {
  it('has migrations that all move forward one version', () => {
    const versions = SCHEMA_MIGRATIONS.map((migration) => migration.version);
    assert.deepEqual(versions, [...versions].sort((a, b) => a - b));
    assert.equal(new Set(versions).size, versions.length);
    assert.ok(versions.length > 0, 'the schema has no migrations');
  });

  it('ends at the version it says', () => {
    assert.equal(SCHEMA_VERSION, SCHEMA_MIGRATIONS[SCHEMA_MIGRATIONS.length - 1]!.version);
  });

  it('can be undone, so a rollback is possible', () => {
    for (const migration of SCHEMA_MIGRATIONS) {
      assert.ok(migration.down, `${migration.name} cannot be undone`);
    }
  });
});

describe('running the schema', () => {
  it('brings an empty database to the newest version', async () => {
    const db = await database();
    const report = await runMigrations(db, SCHEMA_MIGRATIONS);
    assert.equal(report.from, 0);
    assert.equal(report.to, SCHEMA_VERSION);
    assert.equal(report.applied.length, SCHEMA_MIGRATIONS.length);
    assert.equal(await currentVersion(db), SCHEMA_VERSION);
    await db.close();
  });

  it('creates the server tables', async () => {
    const db = await database();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    for (const table of SERVER_TABLES) {
      const result = await db.query<{ n: number }>(
        `SELECT count(*)::int AS n FROM information_schema.tables WHERE table_name = $1`,
        [table],
      );
      assert.equal(result.rows[0]?.n, 1, `the table ${table} is missing`);
    }
    await db.close();
  });

  it('is a no-op the second time', async () => {
    const db = await database();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    const second = await runMigrations(db, SCHEMA_MIGRATIONS);
    assert.equal(second.applied.length, 0);
    assert.equal(second.from, SCHEMA_VERSION);
    await db.close();
  });

  it('records the history', async () => {
    const db = await database();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    const result = await db.query<{ version: number; name: string }>(
      'SELECT version, name FROM schema_migrations ORDER BY version',
    );
    assert.equal(result.rows.length, SCHEMA_MIGRATIONS.length);
    assert.equal(result.rows[0]!.version, 1);
    await db.close();
  });

  it('refuses a database that is newer than the server', async () => {
    const db = await database();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    await assert.rejects(
      runMigrations(db, SCHEMA_MIGRATIONS.slice(0, 1)),
      (error: unknown) =>
        error instanceof MigrationError && error.reason === 'unknown-version',
    );
    await db.close();
  });
});

describe('rolling the schema back', () => {
  it('undoes the last migration', async () => {
    const db = await database();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    const report = await rollbackMigrations(db, SCHEMA_MIGRATIONS, 1);
    assert.equal(report.applied.length, 1);
    assert.equal(await currentVersion(db), SCHEMA_VERSION - 1);
    await db.close();
  });

  it('undoes the index and leaves the tables', async () => {
    const db = await database();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    await rollbackMigrations(db, SCHEMA_MIGRATIONS, 1);
    for (const table of SERVER_TABLES) {
      const result = await db.query<{ n: number }>(
        `SELECT count(*)::int AS n FROM information_schema.tables WHERE table_name = $1`,
        [table],
      );
      assert.equal(result.rows[0]?.n, 1, `the table ${table} is missing`);
    }
    await db.close();
  });

  it('stops at a migration that cannot be undone', async () => {
    const db = await database();
    const irreversible = {
      version: 99,
      name: 'a migration that cannot be undone',
      up: ['SELECT 1'],
    };
    await runMigrations(db, [...SCHEMA_MIGRATIONS, irreversible]);
    const report = await rollbackMigrations(db, [...SCHEMA_MIGRATIONS, irreversible], 1);
    assert.equal(report.applied.length, 0);
    assert.equal(report.notReversible.length, 1);
    assert.equal(report.notReversible[0]!.version, 99);
    await db.close();
  });
});

describe('the table names', () => {
  it('are the ones the stores use', () => {
    assert.equal(PLAYERS_TABLE, 'player_saves');
    assert.equal(SOCIAL_TABLE, 'social');
  });
});
