import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  floorFor,
  groupCounts,
  groupsBelowFloor,
} from './roadmap.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function roadmap(): Promise<string> {
  return readFile(path.join(repoRoot(), 'docs/ROADMAP.md'), 'utf8');
}

async function floor(): Promise<Record<string, number>> {
  return JSON.parse(
    await readFile(path.join(repoRoot(), 'docs/roadmap-baseline.json'), 'utf8'),
  ) as Record<string, number>;
}

describe('the roadmap', () => {
  it('has not lost an item', async () => {
    // An item that is silently swallowed is worse than one that is
    // visibly unfinished, and it happened here. The floor is the number
    // of items each group had the last time somebody looked.
    const below = groupsBelowFloor(await roadmap(), await floor());
    assert.deepEqual(
      below,
      [],
      below
        .map(
          (entry) =>
            `Group ${entry.group}: ${entry.actual} items, the floor is ${entry.minimum}`,
        )
        .join('\n'),
    );
  });

  it('has an item for every group', async () => {
    const counts = groupCounts(await roadmap());
    for (const group of 'ABCDEFGHI') {
      assert.ok(counts[group], `Group ${group} has no items`);
      assert.ok(counts[group]!.items > 0, `Group ${group} has no items`);
    }
  });

  it('counts the done and the open items', async () => {
    const counts = groupCounts(await roadmap());
    for (const [group, count] of Object.entries(counts)) {
      assert.equal(
        count.items,
        count.done + count.open,
        `Group ${group} does not add up`,
      );
    }
  });

  it('records the floor it is checked against', async () => {
    const recorded = await floor();
    const counts = groupCounts(await roadmap());
    for (const group of Object.keys(counts)) {
      assert.equal(
        typeof recorded[group],
        'number',
        `Group ${group} has no recorded floor`,
      );
    }
  });

  it('has a floor that is what the counts say it is', async () => {
    // The floor is a floor, not a copy: it may be lower than the current
    // count, but never higher.
    const recorded = await floor();
    const counts = groupCounts(await roadmap());
    for (const [group, minimum] of Object.entries(recorded)) {
      assert.ok(
        minimum <= (counts[group]?.items ?? 0),
        `Group ${group}'s floor is ${minimum}, and it has ${counts[group]?.items ?? 0}`,
      );
    }
  });

  it('computes the floor from the counts', async () => {
    const text = await roadmap();
    const recorded = await floor();
    const computed = floorFor(text);
    for (const [group, count] of Object.entries(computed)) {
      assert.ok(
        (recorded[group] ?? 0) <= count,
        `Group ${group}'s floor is above its count`,
      );
    }
  });
});
