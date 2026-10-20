#!/usr/bin/env node
/**
 * Run the server's schema migrations.
 *
 * The schema is **versioned**: it moves by migration, one version at a
 * time, and every migration that runs is recorded in the database. This
 * is the deploy-time entry point for that, so a deploy brings the schema
 * forward before the new server starts serving.
 *
 * It is **forward only** by default. A rollback needs `--rollback`, and it
 * stops at the first migration that cannot be undone safely rather than
 * pretending it can.
 *
 * Usage:
 *   node scripts/migrate.mjs --data <dir>            bring the schema forward
 *   node scripts/migrate.mjs --data <dir> --status   what version it is at
 *   node scripts/migrate.mjs --data <dir> --rollback  roll one migration back
 *   node scripts/migrate.mjs --data <dir> --rollback 3
 *
 * The database is a PGlite one, which is a **directory**: the same
 * `--data` directory the server uses.
 */
import path from 'node:path';
import process from 'node:process';

import { PGlite } from '@electric-sql/pglite';

import {
  SCHEMA_MIGRATIONS,
  SCHEMA_VERSION,
  currentVersion,
  rollbackMigrations,
  runMigrations,
} from '@swl/server';

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

async function main() {
  const data = flag('data');
  if (!data) {
    console.error('usage:');
    console.error('  node scripts/migrate.mjs --data <dir> [--status]');
    console.error('  node scripts/migrate.mjs --data <dir> --rollback [steps]');
    process.exit(2);
  }

  const db = await PGlite.create({ dataDir: path.resolve(data) });
  try {
    const version = await currentVersion(db);

    if (has('status')) {
      const pending = SCHEMA_MIGRATIONS.filter(
        (migration) => migration.version > version,
      );
      console.log(
        `the schema is at version ${version} (the newest is ${SCHEMA_VERSION})`,
      );
      for (const migration of SCHEMA_MIGRATIONS) {
        const state =
          migration.version <= version
            ? 'applied'
            : migration.down
              ? 'pending'
              : 'pending (not reversible)';
        console.log(`  ${migration.version}  ${migration.name}  [${state}]`);
      }
      console.log(`  ${pending.length} migration(s) pending`);
      return;
    }

    if (has('rollback')) {
      const steps = Number(flag('rollback') ?? 1);
      const report = await rollbackMigrations(db, SCHEMA_MIGRATIONS, steps);
      for (const migration of report.applied) {
        console.log(`rolled back ${migration.version}  ${migration.name}`);
      }
      for (const migration of report.notReversible) {
        console.error(
          `STOPPED: ${migration.version} ${migration.name} cannot be undone safely, ` +
            'and rolling back past it would leave the schema in a state nobody has tested.',
        );
      }
      console.log(`the schema is at version ${report.to}`);
      return;
    }

    const report = await runMigrations(db, SCHEMA_MIGRATIONS);
    for (const migration of report.applied) {
      console.log(`applied ${migration.version}  ${migration.name}`);
    }
    console.log(
      `the schema is at version ${report.to} (was ${report.from}), ` +
        `${report.applied.length} migration(s) applied`,
    );
  } finally {
    await db.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
