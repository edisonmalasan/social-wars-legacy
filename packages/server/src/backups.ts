/**
 * Whether the backups are being taken.
 *
 * A backup that is only taken when somebody remembers is not a backup,
 * and a schedule that has stopped is invisible until the day it is
 * needed. So the schedule is **monitored**: this fails when the newest
 * snapshot is too old, or when there are none at all.
 *
 * It is meant to be run by a monitor — a cron job, a CI schedule, an
 * uptime check — and it exits non-zero when the backups have stopped.
 */
import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';

/** How old a snapshot may be, in hours. */
export const DEFAULT_MAX_AGE_HOURS = 26;

/** One snapshot. */
export interface Snapshot {
  /** Its name. */
  name: string;
  /** How old it is, in hours. */
  ageHours: number;
}

/**
 * The snapshots in a directory, newest first.
 */
export async function snapshots(out: string): Promise<Snapshot[]> {
  let entries;
  try {
    entries = await readdir(out, { withFileTypes: true });
  } catch {
    return [];
  }
  const found: Snapshot[] = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || !entry.name.startsWith('backup-')) continue;
    const full = path.join(out, entry.name);
    let info;
    try {
      info = await stat(full);
    } catch {
      continue;
    }
    found.push({
      name: entry.name,
      ageHours: (Date.now() - info.mtimeMs) / (60 * 60 * 1000),
    });
  }
  return found.sort((a, b) => a.ageHours - b.ageHours);
}

/** The outcome of a check. */
export interface BackupCheck {
  /** What is wrong, or null when nothing is. */
  problem: string | null;
  /** The newest snapshot, when there is one. */
  newest: Snapshot | null;
}

/**
 * Whether the backups are current.
 */
export async function checkBackups(
  out: string,
  maxAgeHours: number = DEFAULT_MAX_AGE_HOURS,
): Promise<BackupCheck> {
  const found = await snapshots(out);
  if (found.length === 0) {
    return { problem: `there are no backups in ${out}`, newest: null };
  }
  const newest = found[0]!;
  if (newest.ageHours > maxAgeHours) {
    return {
      problem:
        `the newest backup is ${newest.ageHours.toFixed(1)} hours old, ` +
        `and the limit is ${maxAgeHours}`,
      newest,
    };
  }
  return { problem: null, newest };
}
