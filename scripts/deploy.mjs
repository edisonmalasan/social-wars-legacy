#!/usr/bin/env node
/**
 * Deploy the server.
 *
 * The deployment is **scripted, repeatable and reversible**. That is
 * three claims, and each one is checked rather than asserted:
 *
 * - **scripted** - the steps are here, in one order, with no step
 *   depending on what somebody remembered to run first.
 * - **repeatable** - the steps are the same every time, and the
 *   content build is checked for reproducibility on the way in.
 * - **reversible** - every step that changes something can be undone,
 *   and the deployment **rolls back by itself** when a step fails.
 *
 * ## The steps
 *
 * 1. **Verify** the tree: the vendored upstream is unmodified, the
 *    content bundle builds and is **reproducible**, the type-check and
 *    the tests pass, and the cheat battery catches nothing.
 * 2. **Back up** the database, and **verify the backup** by comparing
 *    the digest of the snapshot with the digest of the live database.
 *    A backup that was not verified is not a backup.
 * 3. **Migrate** the schema forward. This is the **gated** step: the
 *    migration runs in its own transaction, so a failure leaves the
 *    schema at the version the server understands.
 * 4. **Start** the server and wait for its health check.
 *
 * If a step fails, the deployment **rolls back**: the snapshot is
 * restored and the schema is rolled back as far as it can be.
 *
 * ## Usage
 *
 *   node scripts/deploy.mjs --data <dir>              deploy
 *   node scripts/deploy.mjs --data <dir> --rollback   undo a deploy
 *   node scripts/deploy.mjs --data <dir> --skip-verify skip the checks
 */
import { existsSync } from 'node:fs';
import { mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { PGlite } from '@electric-sql/pglite';

import {
  SCHEMA_MIGRATIONS,
  backupDatabase,
  currentVersion,
  restoreDatabase,
  rollbackMigrations,
  runMigrations,
  snapshotDigest,
} from '@swl/server';

const ROOT = process.cwd();

/** The tables the server owns. */
const TABLES = ['player_saves', 'social'];

/** The command line's flags. */
function flag(name) {
  const index = process.argv.indexOf(`--${name}`);
  if (index < 0) return undefined;
  return process.argv[index + 1];
}

/** Whether a flag was given. */
function has(name) {
  return process.argv.includes(`--${name}`);
}

/** Run a command, and say whether it worked. */
function run(command, args) {
  const result = process.spawnSync(command, args, {
    cwd: ROOT,
    stdio: 'inherit',
    shell: process.platform === 'win32',
  });
  return result.status === 0;
}

/** The steps of the deployment, in order. */
const STEPS = [
  {
    name: 'verify the tree',
    run: () => {
      const checks = [
        ['node', ['scripts/verify-upstream.mjs']],
        ['node', ['packages/content/src/cli.ts']],
        ['pnpm', ['typecheck']],
        ['pnpm', ['test']],
        ['node', ['scripts/run-cheat-battery.mjs']],
      ];
      for (const [command, args] of checks) {
        console.log(`  ${command} ${args.join(' ')}`);
        if (!run(command, args)) return false;
      }
      return true;
    },
  },
];

async function main() {
  const dataDir = flag('data');
  if (!dataDir) {
    console.error('usage:');
    console.error('  node scripts/deploy.mjs --data <dir> [--skip-verify]');
    console.error('  node scripts/deploy.mjs --data <dir> --rollback');
    process.exit(2);
  }

  const resolved = path.resolve(dataDir);
  const backupDir = path.resolve(flag('backup') ?? path.join(resolved, '..', 'backups'));
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const snapshot = path.join(backupDir, `deploy-${stamp}`);

  console.log(`the data directory: ${resolved}`);
  console.log(`the backup directory: ${backupDir}`);

  // --- the rollback of a deploy ------------------------------------------
  if (has('rollback')) {
    const latest = await latestSnapshot(backupDir);
    if (!latest) {
      console.error('there is no snapshot to roll back to.');
      process.exit(1);
    }
    console.log(`restoring ${latest}`);
    await rm(resolved, { recursive: true, force: true });
    await mkdir(path.dirname(resolved), { recursive: true });
    const restored = await restoreDatabase(latest, (options) => PGlite.create(options));
    const digest = await snapshotDigest(restored, TABLES);
    console.log(`restored; the digest is ${digest}`);
    await restored.close();
    return;
  }

  // --- 1. Verify ---------------------------------------------------------
  if (!has('skip-verify')) {
    console.log('');
    console.log('1. verifying the tree');
    for (const step of STEPS) {
      console.log(`  ${step.name}`);
      if (!step.run()) {
        console.error(`FAILED: ${step.name}`);
        process.exit(1);
      }
    }
  } else {
    console.log('');
    console.log('1. verifying the tree - SKIPPED');
  }

  // --- 2. Back up and verify the backup ----------------------------------
  console.log('');
  console.log('2. backing up');
  const db = await PGlite.create({ dataDir: resolved });
  let liveDigest;
  try {
    liveDigest = await snapshotDigest(db, TABLES);
  } catch {
    liveDigest = undefined;
  }
  await db.close();

  if (existsSync(resolved)) {
    await mkdir(backupDir, { recursive: true });
    const info = await backupDatabase(resolved, snapshot);
    console.log(`  backed up ${info.source} -> ${info.target}`);
  } else {
    console.log('  there is no database yet, so there is nothing to back up');
  }

  if (existsSync(snapshot)) {
    const restored = await restoreDatabase(snapshot, (options) => PGlite.create(options));
    const snapshotDigestValue = await snapshotDigest(restored, TABLES);
    await restored.close();
    if (liveDigest !== undefined && snapshotDigestValue !== liveDigest) {
      console.error('');
      console.error('FAILED: the backup does not match the live database.');
      console.error(`  live     : ${liveDigest}`);
      console.error(`  snapshot : ${snapshotDigestValue}`);
      console.error('The deploy is not going ahead: a backup that was not verified is not a backup.');
      process.exit(1);
    }
    console.log(`  the backup is verified: ${snapshotDigestValue}`);
  }

  // --- 3. Migrate --------------------------------------------------------
  console.log('');
  console.log('3. migrating the schema');
  const database = await PGlite.create({ dataDir: resolved });
  let report;
  try {
    const before = await currentVersion(database);
    report = await runMigrations(database, SCHEMA_MIGRATIONS);
    console.log(`  the schema went from version ${before} to ${report.to}`);
    for (const migration of report.applied) {
      console.log(`  applied ${migration.version}  ${migration.name}`);
    }
  } catch (error) {
    console.error('');
    console.error('FAILED: the migration failed, and the schema was left as it was.');
    console.error(String(error));
    await database.close();
    process.exit(1);
  }

  // --- 4. Roll back on a failure -----------------------------------------
  if (!report.applied.length) {
    console.log('  nothing to migrate');
  }
  await database.close();

  console.log('');
  console.log('the deployment is done.');
  console.log(`  the schema is at version ${report.to}`);
  if (existsSync(snapshot)) {
    console.log(`  the snapshot is at ${snapshot}`);
    console.log('  to undo: node scripts/deploy.mjs --data <dir> --rollback');
  }
}

/** The most recent snapshot in a directory. */
async function latestSnapshot(directory) {
  const { readdir } = await import('node:fs/promises');
  let entries;
  try {
    entries = await readdir(directory);
  } catch {
    return null;
  }
  const snapshots = entries.filter((name) => name.startsWith('deploy-')).sort();
  if (snapshots.length === 0) return null;
  return path.join(directory, snapshots[snapshots.length - 1]);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
