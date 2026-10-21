#!/usr/bin/env node
/**
 * Check that the backups are being taken.
 *
 * A backup that is only taken when somebody remembers is not a backup,
 * and a schedule that has stopped is invisible until the day it is
 * needed. So the schedule is **monitored**: this fails when the newest
 * snapshot is too old, or when there are none at all.
 *
 * It is meant to be run by a monitor — a cron job, a CI schedule, an
 * uptime check — and it exits non-zero when the backups have stopped.
 *
 * Usage:
 *   node scripts/check-backups.mjs --out <dir> [--max-age <hours>]
 */
import path from 'node:path';
import process from 'node:process';

import {
  DEFAULT_MAX_AGE_HOURS,
  checkBackups,
} from '../packages/server/src/backups.ts';

const ROOT = process.cwd();

/** A command-line flag's value. */
function flag(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return fallback;
}

async function main() {
  const out = flag('out', path.join(ROOT, 'backups'));
  const maxAge = Number(flag('max-age', DEFAULT_MAX_AGE_HOURS));

  const result = await checkBackups(out, maxAge);
  if (result.problem) {
    console.error(`FAIL: ${result.problem}`);
    process.exit(1);
  }
  console.log(
    `OK: the newest backup is ${result.newest!.ageHours.toFixed(1)} hours old ` +
      `(${result.newest!.name}), and the limit is ${maxAge}.`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
