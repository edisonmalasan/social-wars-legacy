#!/usr/bin/env node
/**
 * Check the roadmap's item counts.
 *
 * The roadmap is a list of items, and an item that is silently
 * swallowed is worse than one that is visibly unfinished. That happened
 * here, so each group's item count is now checked against a **floor** -
 * the number of items it had the last time somebody looked.
 *
 * A group with fewer items than its floor is a failure.
 *
 * Usage:
 *   node scripts/check-roadmap.mjs            check the roadmap
 *   node scripts/check-roadmap.mjs --record   record the current counts
 *                                              as the new floor
 */
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { floorFor, groupCounts, groupsBelowFloor } from '../packages/client/src/roadmap.ts';

const ROOT = process.cwd();
const ROADMAP = path.join(ROOT, 'docs/ROADMAP.md');
const FLOOR = path.join(ROOT, 'docs/roadmap-baseline.json');

async function main() {
  const text = await readFile(ROADMAP, 'utf8');

  if (process.argv.includes('--record')) {
    const floor = floorFor(text);
    await writeFile(FLOOR, JSON.stringify(floor, null, 1) + '\n', 'utf8');
    console.log(`recorded the floor: ${JSON.stringify(floor)}`);
    return;
  }

  let floor;
  try {
    floor = JSON.parse(await readFile(FLOOR, 'utf8'));
  } catch {
    console.error(
      'there is no floor to check against. Run:\n' +
        '  node scripts/check-roadmap.mjs --record',
    );
    process.exit(2);
  }

  const below = groupsBelowFloor(text, floor);
  if (below.length > 0) {
    console.error('the roadmap has lost items:\n');
    for (const entry of below) {
      console.error(
        `  Group ${entry.group}: ${entry.actual} items, the floor is ${entry.minimum} ` +
          `(${entry.missing} missing)`,
      );
    }
    console.error(
      '\nAn item was swallowed. Put it back, or lower the floor deliberately:\n' +
        '  node scripts/check-roadmap.mjs --record',
    );
    process.exit(1);
  }

  const counts = groupCounts(text);
  let total = 0;
  for (const group of Object.keys(counts).sort()) {
    const count = counts[group];
    total += count.items;
    console.log(
      `  Group ${group}: ${String(count.items).padStart(3)} items ` +
        `(${count.done} done, ${count.open} open)`,
    );
  }
  console.log(`  ${total} items in all`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
