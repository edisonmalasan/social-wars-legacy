import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { PGlite } from '@electric-sql/pglite';

import {
  BackupError,
  backupDatabase,
  restoreDatabase,
  snapshotDigest,
} from './backup.ts';

/** A scratch directory that is cleaned up afterwards. */
async function scratch(): Promise<string> {
  return mkdtemp(path.join(tmpdir(), 'swl-backup-'));
}

/** A database with something in it. */
async function populated(dataDir: string): Promise<PGlite> {
  const db = await PGlite.create({ dataDir });
  await db.exec(`
    CREATE TABLE player_saves (player_id TEXT PRIMARY KEY, doc JSONB NOT NULL);
    CREATE TABLE social (id TEXT PRIMARY KEY, doc JSONB NOT NULL);
  `);
  await db.query('INSERT INTO player_saves (player_id, doc) VALUES ($1, $2)', [
    'p1',
    JSON.stringify({ gold: 1000, level: 7 }),
  ]);
  await db.query('INSERT INTO social (id, doc) VALUES ($1, $2)', [
    'alliance-1',
    JSON.stringify({ title: 'The Brigade' }),
  ]);
  return db;
}

describe('a backup', () => {
  it('copies the database directory', async () => {
    const root = await scratch();
    try {
      const dataDir = path.join(root, 'db');
      const target = path.join(root, 'snapshots', '2026-10-20');
      const db = await populated(dataDir);
      await db.close();

      const info = await backupDatabase(dataDir, target, 1_700_000_000);
      assert.equal(info.source, dataDir);
      assert.equal(info.target, target);
      assert.ok(info.files > 0, 'nothing was copied');
      assert.ok(info.bytes > 0);
      assert.equal(info.takenAt, 1_700_000_000);

      const copied = await readdir(target);
      assert.ok(copied.includes('PG_VERSION'));
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it('refuses a database that is not there', async () => {
    const root = await scratch();
    try {
      await assert.rejects(
        backupDatabase(path.join(root, 'nope'), path.join(root, 'snap')),
        (error: unknown) => error instanceof BackupError && error.reason === 'no-source',
      );
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});

describe('a restore', () => {
  it('opens a snapshot and it has the same content', async () => {
    const root = await scratch();
    try {
      const dataDir = path.join(root, 'db');
      const target = path.join(root, 'snapshots', 'one');
      const db = await populated(dataDir);
      const before = await snapshotDigest(db, ['player_saves', 'social']);
      await db.close();

      await backupDatabase(dataDir, target, 1_700_000_000);

      const restored = await restoreDatabase(target, (options) =>
        PGlite.create(options as { dataDir: string }),
      );
      const after = await snapshotDigest(restored, ['player_saves', 'social']);
      assert.equal(after, before, 'the restored snapshot differs from the original');

      const rows = await restored.query('SELECT doc FROM player_saves WHERE player_id = $1', [
        'p1',
      ]);
      assert.deepEqual((rows.rows[0] as { doc: unknown }).doc, { gold: 1000, level: 7 });
      await restored.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it('restores a snapshot taken from a live database', async () => {
    // The realistic case: the server is running, the backup is taken, and
    // the database is then changed. The snapshot must still hold the old
    // state.
    const root = await scratch();
    try {
      const dataDir = path.join(root, 'db');
      const target = path.join(root, 'snapshots', 'live');
      const db = await populated(dataDir);

      await backupDatabase(dataDir, target, 1_700_000_000);

      // The database changes after the snapshot.
      await db.query('UPDATE player_saves SET doc = $2 WHERE player_id = $1', [
        'p1',
        JSON.stringify({ gold: 0, level: 1 }),
      ]);
      const current = await snapshotDigest(db, ['player_saves', 'social']);
      await db.close();

      const restored = await restoreDatabase(target, (options) =>
        PGlite.create(options as { dataDir: string }),
      );
      const restoredDigest = await snapshotDigest(restored, ['player_saves', 'social']);
      assert.notEqual(restoredDigest, current, 'the snapshot tracked the live changes');

      const rows = await restored.query('SELECT doc FROM player_saves WHERE player_id = $1', [
        'p1',
      ]);
      assert.deepEqual((rows.rows[0] as { doc: unknown }).doc, { gold: 1000, level: 7 });
      await restored.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it('refuses a snapshot that is not there', async () => {
    const root = await scratch();
    try {
      await assert.rejects(
        restoreDatabase(path.join(root, 'nope'), (options) =>
          PGlite.create(options as { dataDir: string }),
        ),
        (error: unknown) => error instanceof BackupError && error.reason === 'no-source',
      );
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});

describe('the snapshot digest', () => {
  it('is the same for the same rows', async () => {
    const root = await scratch();
    try {
      const db = await populated(path.join(root, 'db'));
      const first = await snapshotDigest(db, ['player_saves', 'social']);
      const second = await snapshotDigest(db, ['player_saves', 'social']);
      assert.equal(first, second);
      await db.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it('does not depend on the order of the tables', async () => {
    const root = await scratch();
    try {
      const db = await populated(path.join(root, 'db'));
      const one = await snapshotDigest(db, ['player_saves', 'social']);
      const other = await snapshotDigest(db, ['social', 'player_saves']);
      assert.equal(one, other);
      await db.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it('changes when the rows change', async () => {
    const root = await scratch();
    try {
      const db = await populated(path.join(root, 'db'));
      const before = await snapshotDigest(db, ['player_saves']);
      await db.query('UPDATE player_saves SET doc = $2 WHERE player_id = $1', [
        'p1',
        JSON.stringify({ gold: 1 }),
      ]);
      const after = await snapshotDigest(db, ['player_saves']);
      assert.notEqual(before, after);
      await db.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
