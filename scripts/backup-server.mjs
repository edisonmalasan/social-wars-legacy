#!/usr/bin/env node
/**
 * Back up and restore the server's database.
 *
 * The database is a PostgreSQL one; in the offline (PGlite) mode it is a
 * **directory**, so a backup is a copy of that directory and a restore is
 * opening the copy.
 *
 *   node scripts/backup-server.mjs --data <dir> --out <dir>
 *   node scripts/backup-server.mjs --data <dir> --out <dir> --verify
 *   node scripts/backup-server.mjs --restore <dir> --data <dir>
 *
 * `--verify` opens the snapshot and compares its contents with the live
 * database's, so a backup that cannot be read back is caught at the time it
 * is taken rather than at the time it is needed.
 */
import { mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { PGlite } from '@electric-sql/pglite';

import { backupDatabase, restoreDatabase, snapshotDigest } from '../packages/server/src/backup.ts';

/** The tables the digest covers. */
const TABLES = ['player_saves', 'social'];

/** A command-line flag's value. */
function flag(name) {
  const index = process.argv.indexOf(`--${name}`);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return undefined;
}

/** Whether a flag is present. */
function has(name) {
  return process.argv.includes(`--${name}`);
}

async function main() {
  const dataDir = flag('data');
  const out = flag('out');
  const restore = flag('restore');

  if (restore) {
    if (!dataDir) {
      console.error('--restore needs --data <dir> to restore into');
      process.exit(2);
    }
    // The restore replaces the live directory.
    await rm(dataDir, { recursive: true, force: true });
    await mkdir(path.dirname(dataDir), { recursive: true });
    const restored = await restoreDatabase(restore, (options) =>
      PGlite.create(options),
    );
    const digest = await snapshotDigest(restored, TABLES);
    console.log(`restored ${restore} into ${dataDir}`);
    console.log(`  digest: ${digest}`);
    await restored.close();
    return;
  }

  if (!dataDir || !out) {
    console.error('usage:');
    console.error('  node scripts/backup-server.mjs --data <dir> --out <dir> [--verify]');
    console.error('  node scripts/backup-server.mjs --restore <dir> --data <dir>');
    process.exit(2);
  }

  const info = await backupDatabase(dataDir, out);
  console.log(`backed up ${info.source} -> ${info.target}`);
  console.log(`  ${info.files} files, ${info.bytes} bytes`);

  if (has('verify')) {
    const live = await PGlite.create({ dataDir });
    const restored = await restoreDatabase(out, (options) =>
      PGlite.create(options),
    );
    const liveDigest = await snapshotDigest(live, TABLES);
    const restoredDigest = await snapshotDigest(restored, TABLES);
    await live.close();
    await restored.close();
    if (liveDigest !== restoredDigest) {
      console.error(`\nFAIL: the snapshot does not match the live database.`);
      console.error(`  live     : ${liveDigest}`);
      console.error(`  snapshot : ${restoredDigest}`);
      process.exit(1);
    }
    console.log(`  digest: ${liveDigest} (the snapshot matches)`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
