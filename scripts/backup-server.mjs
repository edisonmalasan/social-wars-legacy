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
 *   node scripts/backup-server.mjs --data <dir> --out <dir> --every 6
 *   node scripts/backup-server.mjs --restore <dir> --data <dir>
 *
 * `--verify` opens the snapshot and compares its contents with the live
 * database's, so a backup that cannot be read back is caught at the time it
 * is taken rather than at the time it is needed.
 *
 * `--every <hours>` takes the backup **repeatedly**, which is what a
 * server does rather than what a person does. The snapshots are pruned to
 * the newest few, because a backup nobody can delete is a disk full
 * rather than a backup.
 *
 * The schedule is **monitored** by `scripts/check-backups.mjs`, which
 * fails when the newest snapshot is too old.
 */
import { mkdir, readdir, rm } from 'node:fs/promises';
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

/**
 * Take one backup, verify it, and prune the old ones.
 *
 * The pruning keeps the newest `keep` snapshots, so a scheduled backup
 * does not fill the disk: a server that runs out of space is a server
 * that is not serving anybody.
 */
async function takeBackup(dataDir, out, verify, keep) {
  const info = await backupDatabase(dataDir, out);
  console.log(`backed up ${info.source} -> ${info.target}`);

  if (verify) {
    const live = await PGlite.create({ dataDir: path.resolve(dataDir) });
    const liveDigest = await snapshotDigest(live, TABLES);
    await live.close();
    const restored = await restoreDatabase(info.target, (options) =>
      PGlite.create(options),
    );
    const snapshotDigestValue = await snapshotDigest(restored, TABLES);
    await restored.close();
    if (liveDigest !== snapshotDigestValue) {
      console.error(
        `FAIL: the backup does not match the live database.\n` +
          `  live     : ${liveDigest}\n` +
          `  snapshot : ${snapshotDigestValue}`,
      );
      process.exit(1);
    }
    console.log(`  the backup is verified: ${snapshotDigestValue}`);
  }

  await prune(out, keep);
}

/** The newest snapshots are kept and the rest are removed. */
async function prune(out, keep) {
  let entries;
  try {
    entries = await readdir(out, { withFileTypes: true });
  } catch {
    return;
  }
  const snapshots = entries
    .filter((entry) => entry.isDirectory() && entry.name.startsWith('backup-'))
    .map((entry) => entry.name)
    .sort();
  const extra = snapshots.length - keep;
  for (let index = 0; index < extra; index += 1) {
    const name = snapshots[index];
    await rm(path.join(out, name), { recursive: true, force: true });
    console.log(`  pruned the old snapshot ${name}`);
  }
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

  const every = flag('every');

  if (!dataDir || !out) {
    console.error('usage:');
    console.error('  node scripts/backup-server.mjs --data <dir> --out <dir> [--verify]');
    console.error('  node scripts/backup-server.mjs --data <dir> --out <dir> --every <hours>');
    console.error('  node scripts/backup-server.mjs --restore <dir> --data <dir>');
    process.exit(2);
  }

  if (every) {
    // The scheduled mode: take the backup, wait, take it again. The
    // snapshots are pruned, so the loop does not fill the disk.
    const hours = Number(every);
    if (!Number.isFinite(hours) || hours <= 0) {
      console.error(`--every needs a number of hours, not "${every}"`);
      process.exit(2);
    }
    const keep = Number(flag('keep', 24));
    const intervalMs = hours * 60 * 60 * 1000;

    for (;;) {
      await takeBackup(dataDir, out, has('verify'), keep);
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
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
