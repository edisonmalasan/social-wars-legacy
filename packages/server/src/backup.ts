/**
 * Backup and restore.
 *
 * The server's state is a PostgreSQL database, and in the offline
 * (PGlite) mode that database is a **directory**. So a backup is a copy of
 * that directory, and a restore is opening the copy.
 *
 * That is deliberately simple. A backup format that has to be
 * re-implemented is a backup format that will eventually fail to restore,
 * and the whole point of a backup is that it can be read back.
 *
 * The procedure is **exercised against a real snapshot** in the tests: a
 * database is written, backed up, restored, and the restored copy's contents
 * are compared with the original's.
 */
import { cp, mkdir, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';

/** What a backup produced. */
export interface BackupInfo {
  /** The directory the database was in. */
  source: string;
  /** The directory the snapshot was written to. */
  target: string;
  /** How many files were copied. */
  files: number;
  /** How many bytes were copied. */
  bytes: number;
  /** When the snapshot was taken, in milliseconds. */
  takenAt: number;
}

/** The error a backup or restore can fail with. */
export class BackupError extends Error {
  readonly reason: 'no-source' | 'no-target' | 'not-a-directory';

  constructor(message: string, reason: 'no-source' | 'no-target' | 'not-a-directory') {
    super(message);
    this.name = 'BackupError';
    this.reason = reason;
  }
}

/**
 * Copy a database's directory into a snapshot.
 *
 * The target is **replaced**, not merged: a snapshot is a point in time, and
 * a half-old half-new directory is worse than no snapshot at all.
 */
export async function backupDatabase(
  dataDir: string,
  targetDir: string,
  now: number = Date.now(),
): Promise<BackupInfo> {
  let source;
  try {
    source = await stat(dataDir);
  } catch {
    throw new BackupError(`there is no database at ${dataDir}`, 'no-source');
  }
  if (!source.isDirectory()) {
    throw new BackupError(`${dataDir} is not a directory`, 'not-a-directory');
  }

  await mkdir(path.dirname(targetDir), { recursive: true });
  await cp(dataDir, targetDir, { recursive: true, force: true });

  let files = 0;
  let bytes = 0;
  for (const entry of await readdir(targetDir, { withFileTypes: true })) {
    if (!entry.isFile()) continue;
    files += 1;
    bytes += (await stat(path.join(targetDir, entry.name))).size;
  }

  // A note beside the snapshot, so a snapshot found on its own says what it
  // is and when it was taken.
  await writeFile(
    path.join(targetDir, 'BACKUP.json'),
    JSON.stringify(
      {
        note:
          'A snapshot of the server database. Restore it by opening this ' +
          'directory as the database data directory.',
        source: dataDir,
        takenAt: now,
        files,
        bytes,
      },
      null,
      1,
    ) + '\n',
    'utf8',
  );

  return { source: dataDir, target: targetDir, files, bytes, takenAt: now };
}

/**
 * Open a snapshot as a database.
 *
 * The caller gets the PGlite instance, so it can be opened and queried
 * exactly like the original.
 */
export async function restoreDatabase<T>(dataDir: string, create: (options: unknown) => Promise<T>): Promise<T> {
  let source;
  try {
    source = await stat(dataDir);
  } catch {
    throw new BackupError(`there is no snapshot at ${dataDir}`, 'no-source');
  }
  if (!source.isDirectory()) {
    throw new BackupError(`${dataDir} is not a directory`, 'not-a-directory');
  }
  return create({ dataDir });
}

/**
 * A digest of a database's tables.
 *
 * It is how a restored snapshot is compared with the original: the same
 * rows in the same tables give the same digest.
 */
export async function snapshotDigest(
  db: unknown,
  tables: readonly string[],
): Promise<string> {
  const { createHash } = await import('node:crypto');
  // The database is taken loosely and narrowed once, here: PGlite's `query`
  // has a generic signature that satisfies no structural type.
  const query = (
    db as { query: (sql: string) => Promise<{ rows: unknown[] }> }
  ).query.bind(db);
  const hash = createHash('sha256');
  for (const table of [...tables].sort()) {
    const result = await query(`SELECT * FROM ${table}`);
    hash.update(table);
    hash.update('\n');
    for (const row of result.rows) {
      // The columns are sorted, so two rows with the same data in a
      // different column order give the same digest.
      const record = row as Record<string, unknown>;
      for (const key of Object.keys(record).sort()) {
        hash.update(key);
        hash.update('=');
        hash.update(JSON.stringify(record[key] ?? null));
        hash.update(';');
      }
      hash.update('\n');
    }
  }
  return hash.digest('hex');
}
