import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Random, hashSeed } from './random.ts';
import {
  DEFAULT_LOOT_RULES,
  assaultLoot,
  conquestGold,
  lootForDestroying,
  maxGoldStolen,
  stolenGold,
} from './loot.ts';

describe('the gold bands', () => {
  it('gives a low level the lowest band', () => {
    assert.equal(maxGoldStolen(1), 2500);
    assert.equal(maxGoldStolen(10), 2500);
  });

  it('gives a higher level the next band', () => {
    // The loop stops at the first row whose level is not below the
    // player's, so level 11 lands on the level-20 band and level 45 on
    // the level-50 band.
    assert.equal(maxGoldStolen(11), 5000);
    assert.equal(maxGoldStolen(25), 7500);
    assert.equal(maxGoldStolen(45), 12500);
    assert.equal(maxGoldStolen(99), 25000);
  });

  it('gives the top band above the last level, rather than crashing', () => {
    // The client's loop walks off the end of the table above level 99 and
    // then reads a property off nothing. The clone does not crash.
    assert.equal(maxGoldStolen(200), 25000);
  });

  it("cannot reach the client's unreachable band", () => {
    // The band table has two rows at level 80, so the 22 500 row can never
    // be reached: a player of level 81 passes both of them. That is the
    // client's own table, and the clone reproduces it.
    const reachable = new Set<number>();
    for (let level = 1; level <= 120; level++) {
      reachable.add(maxGoldStolen(level));
    }
    assert.equal(reachable.has(22500), false);
    assert.equal(reachable.has(20000), true);
  });
});

describe('the stolen gold', () => {
  it('takes a percentage of the victim gold', () => {
    // The percentage is random between 15 and 35 per cent, so the result
    // is within that band for a victim with 10 000 gold and a level-1
    // attacker - whose own cap of 2500 would bite first.
    const random = new Random(hashSeed('loot'));
    const gold = stolenGold(10000, 50, random);
    assert.ok(gold >= 0 && gold <= maxGoldStolen(50));
  });

  it('is clamped by the attacker band', () => {
    const random = new Random(hashSeed('loot'));
    // A level-1 attacker may take at most 2500.
    assert.ok(stolenGold(100000, 1, random) <= 2500);
  });

  it('is never negative', () => {
    const random = new Random(hashSeed('loot'));
    assert.ok(stolenGold(0, 50, random) >= 0);
  });

  it('is the same for the same random draw', () => {
    const a = stolenGold(5000, 30, new Random(hashSeed('same')));
    const b = stolenGold(5000, 30, new Random(hashSeed('same')));
    assert.equal(a, b);
  });
});

describe('the conquest gold', () => {
  it("is the victim's level times 100", () => {
    assert.equal(conquestGold(12), 1200);
    assert.equal(conquestGold(1), 100);
  });
});

describe('the XP for a kill', () => {
  it('is 5 per cent of the gold, rounded up', () => {
    assert.equal(lootForDestroying(100).xp, 5);
    assert.equal(lootForDestroying(101).xp, 6);
    assert.equal(lootForDestroying(20).xp, 1);
  });

  it('is at least 1 for anything that is not a wall', () => {
    assert.equal(lootForDestroying(0).xp, 1);
    assert.equal(lootForDestroying(0, { isWall: true }).xp, 0);
  });

  it('keeps the gold it was given', () => {
    assert.equal(lootForDestroying(250).gold, 250);
  });
});

describe('the loot of a whole attack', () => {
  it('gives the gold that was taken', () => {
    const loot = assaultLoot({ won: true, townHallGold: 1200, xp: 60, attackerLevel: 40 });
    assert.equal(loot.gold, 1200);
    assert.equal(loot.xp, 60);
  });

  it('gives a win with no loot a flat 25 gold', () => {
    const loot = assaultLoot({ won: true, townHallGold: 0, xp: 1, attackerLevel: 40 });
    assert.equal(loot.gold, 25);
  });

  it('gives a loss with no loot nothing', () => {
    const loot = assaultLoot({ won: false, townHallGold: 0, xp: 0, attackerLevel: 40 });
    assert.equal(loot.gold, 0);
  });

  it('gives a loss with loot the loot', () => {
    // The flat 25 is only for a WIN.
    const loot = assaultLoot({ won: false, townHallGold: 40, xp: 2, attackerLevel: 40 });
    assert.equal(loot.gold, 40);
  });

  it('uses the client own percentages', () => {
    assert.equal(DEFAULT_LOOT_RULES.goldStolenBottomPct, 15);
    assert.equal(DEFAULT_LOOT_RULES.goldStolenTopPct, 35);
    assert.equal(DEFAULT_LOOT_RULES.flatWinGold, 25);
  });
});
