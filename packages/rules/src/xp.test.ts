import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  bonusesForLevel,
  levelForXp,
  levelUpCost,
  maxLevel,
  parseXpTable,
  xpEarned,
  xpForLevel,
  xpForPaidLevelUp,
  type XpLevelRow,
} from './xp.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

/** The table from the shipped config, so the tests check the real data. */
async function shippedTable(): Promise<XpLevelRow[]> {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as { globals: Record<string, unknown> };
  return parseXpTable(bundle.globals.UNIT_XP_LEVELS_MULTIPLIERS_10);
}

describe('unit XP', () => {
  it('reads the shipped table', async () => {
    const table = await shippedTable();
    assert.equal(table.length, 10);
    assert.equal(maxLevel(table), 9);
    assert.deepEqual(table[1], { xpMultiplier: 5, flatAttack: 2, lifePercent: 20, cashDivisor: 50 });
    assert.deepEqual(table[9], { xpMultiplier: 200, flatAttack: 4, lifePercent: 25, cashDivisor: 1.5 });
  });

  it('needs a multiple of the base life for each level', async () => {
    const table = await shippedTable();
    // A Soldier has 50 life.
    assert.equal(xpForLevel(table, 50, 1), 250);
    assert.equal(xpForLevel(table, 50, 9), 10_000);
  });

  it('gives +30 attack and 3x life at the maximum level', async () => {
    const table = await shippedTable();
    const bonuses = bonusesForLevel(table, 50, maxLevel(table));
    assert.equal(bonuses.extraAttack, 30);
    assert.equal(bonuses.extraLifePercent, 200);
    assert.equal(bonuses.lifeMultiplier, 3);
  });

  it('accumulates the bonuses over the levels passed', async () => {
    const table = await shippedTable();
    assert.equal(bonusesForLevel(table, 50, 0).extraAttack, 0);
    assert.equal(bonusesForLevel(table, 50, 1).extraAttack, 2);
    assert.equal(bonusesForLevel(table, 50, 2).extraAttack, 4);
    assert.equal(bonusesForLevel(table, 50, 3).extraAttack, 7);
    assert.equal(bonusesForLevel(table, 50, 9).extraAttack, 30);
  });

  it('finds the level a given XP has earned', async () => {
    const table = await shippedTable();
    const life = 50;
    // The comparison is `xp <= required` to BREAK, so a unit needs one point
    // MORE than the threshold to advance. That is why a paid level-up grants
    // "the missing XP plus 1" (CmdPlaceStoredItem.as:38).
    assert.equal(levelForXp(table, life, 0), 0);
    assert.equal(levelForXp(table, life, 249), 0);
    assert.equal(levelForXp(table, life, 250), 0); // exactly the threshold: not yet
    assert.equal(levelForXp(table, life, 251), 1);
    assert.equal(levelForXp(table, life, 500), 1);
    assert.equal(levelForXp(table, life, 501), 2);
    // Level 9 is only reachable by paying: XP alone tops out at 8, because
    // the loop breaks at `xp <= required`.
    assert.equal(levelForXp(table, life, 10_000), 8);
    assert.equal(levelForXp(table, life, 10_001), 9);
    assert.equal(levelForXp(table, life, 999_999), 9);
  });

  it('costs ceil(life / divisor) to level up with cash', async () => {
    const table = await shippedTable();
    assert.equal(levelUpCost(table, 100, 1), 2); // ceil(100/50)
    assert.equal(levelUpCost(table, 100, 2), 4); // ceil(100/25)
    assert.equal(levelUpCost(table, 100, 3), 9); // ceil(100/12) = 8.33
    assert.equal(levelUpCost(table, 100, 9), 67); // ceil(100/1.5) = 66.67
  });

  it('grants the missing XP plus one on a paid level-up', async () => {
    const table = await shippedTable();
    const life = 50;
    assert.equal(xpForPaidLevelUp(table, life, 1), xpForLevel(table, life, 1) + 1);
    assert.equal(xpForPaidLevelUp(table, life, 9), xpForLevel(table, life, 9) + 1);
  });

  it('earns XP from damage to units only', () => {
    assert.equal(xpEarned(37, true), 37);
    assert.equal(xpEarned(37, false), 0);
  });
});
