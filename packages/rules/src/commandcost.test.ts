import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { costContentFrom } from '@swl/rules';

import {
  CONFIG,
  PRICED_COMMANDS,
  applyCommandCost,
  computeCommandCost,
  computeLevelUpCost,
  settleCommand,
  type CostContent,
  type CostItem,
  type CostOfferPack,
} from './commandcost.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

interface RawItem {
  id: number;
  name: string;
  costs: Record<string, number>;
  cost_unit_cash: number;
}

interface RawPack {
  id: number;
  name: string;
  cost_cash: number;
  gold: number;
  wood: number;
  oil: number;
  steel: number;
  mana: number;
  xp: number;
  items: number[];
}

async function content(): Promise<CostContent> {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as Parameters<typeof costContentFrom>[0];
  return costContentFrom(bundle);
}

describe('the priced commands', () => {
  it('lists the commands it prices', () => {
    assert.ok(PRICED_COMMANDS.includes('buy'));
    assert.ok(PRICED_COMMANDS.includes('attack_player'));
    assert.ok(PRICED_COMMANDS.includes('exchange_cash'));
  });

  it('does not price flash_debug at all', () => {
    // flash_debug must not exist in the server (non-negotiable 6).
    assert.ok(!PRICED_COMMANDS.includes('flash_debug' as never));
  });
});

describe('computing a cost', () => {
  it('prices a unit purchase from the item data', async () => {
    const c = await content();
    // The Soldier costs 30 gold and 60 steel.
    const cost = computeCommandCost(c, 'buy', [1, 1007, 0, 0, 1, 0, 0]);
    assert.deepEqual(cost?.cost, { g: 30, s: 60, c: 1 });
  });

  it('adds the building cash price for a unit', async () => {
    const c = await content();
    // The Soldier has cost_unit_cash 1.
    const cost = computeCommandCost(c, 'buy', [1, 1007, 0, 0, 1, 0, 0]);
    assert.equal(cost?.cost['c'], 1);
  });

  it('prices placing a building', async () => {
    const c = await content();
    // Academy I costs 125 wood.
    const cost = computeCommandCost(c, 'place_stored_item', [1, 30, 0, 0, 1]);
    assert.deepEqual(cost?.cost, { w: 125 });
  });

  it('pays 75% of the build cost when a stored item is sold', async () => {
    const c = await content();
    // 125 wood -> 94 gold (round(125 * 0.75) = 94).
    const cost = computeCommandCost(c, 'sell_stored_item', [1, 30]);
    assert.deepEqual(cost?.gain, { g: 94 });
    assert.deepEqual(cost?.cost, {});
  });

  it('prices the gold exchange', async () => {
    const c = await content();
    const cost = computeCommandCost(c, 'exchange_cash', []);
    assert.deepEqual(cost?.cost, { c: 5 });
    assert.deepEqual(cost?.gain, { g: 2500 });
  });

  it('prices an offer pack from the pack data', async () => {
    const c = await content();
    const pack = c.offerPacks.get(1)!;
    const cost = computeCommandCost(c, 'buy_offer_pack', [1, '[]']);
    assert.equal(cost?.cost['c'], pack.cost_cash);
    assert.equal(cost?.gain['g'], pack.gold);
  });

  it('prices a premium account from the package table', async () => {
    const c = await content();
    const cost = computeCommandCost(c, 'buy_premium_account', [0]);
    assert.equal(cost?.cost['c'], 800);
  });

  it('prices a paid darts shot', async () => {
    const c = await content();
    const cost = computeCommandCost(c, 'darts_shoot_balloon', [3, 0]);
    assert.deepEqual(cost?.cost, { c: 20 });
  });

  it('prices an expansion from the price table, not from the argument', async () => {
    const c = await content();
    // The fifth expansion costs 2500 gold and 5 cash.
    const cost = computeCommandCost(c, 'expand', [4, 999999, 0]);
    assert.deepEqual(cost?.cost, { g: 2500, c: 5 });
  });

  it('prices an attack at 30 energy and a spy at 15', async () => {
    const c = await content();
    assert.deepEqual(computeCommandCost(c, 'attack_player', [])?.cost, { e: 30 });
    assert.deepEqual(computeCommandCost(c, 'spy_player', [])?.cost, { e: 15 });
    assert.equal(CONFIG.costBuyAttack, 30);
    assert.equal(CONFIG.costBuySpyings, 15);
  });

  it('prices a resource pack from the store own table', async () => {
    const c = await content();
    // The first gold pack gives 5000 gold for 10 cash.
    const cost = computeCommandCost(c, 'buy_resources', ['g', 5000, 'c']);
    assert.deepEqual(cost?.cost, { c: 10 });
    assert.deepEqual(cost?.gain, { g: 5000 });
  });

  it('refuses a resource pack that is not in the table', async () => {
    const c = await content();
    assert.equal(computeCommandCost(c, 'buy_resources', ['g', 7, 'c']), null);
  });

  it('prices a premium upgrade from the new building own price', async () => {
    const c = await content();
    // Tank Academy V costs 20 cash as a premium upgrade.
    const cost = computeCommandCost(c, 'premium_upgrade', [1, 2, 151, -1]);
    assert.deepEqual(cost?.cost, { c: 20 });
  });

  it('refuses a premium upgrade to a building that has no price', async () => {
    const c = await content();
    assert.equal(computeCommandCost(c, 'premium_upgrade', [1, 2, 1007, -1]), null);
  });

  it('returns null for a command it does not price', async () => {
    const c = await content();
    assert.equal(computeCommandCost(c, 'move', [1, 2, 3]), null);
    assert.equal(computeCommandCost(c, 'flash_debug', [1, 2, 3]), null);
  });
});

describe('computing a magic cost', () => {
  it('prices a spell from the magics table, not from the argument', async () => {
    const c = await content();
    // AirStrike: 30 000 gold or 50 cash. The command's own amount is not
    // even part of the native arguments.
    assert.deepEqual(computeCommandCost(c, 'buy_magic', [1, 'g'])?.cost, { g: 30_000 });
    assert.deepEqual(computeCommandCost(c, 'buy_magic', [1, 'c'])?.cost, { c: 50 });
  });

  it('refuses an unknown spell or an unknown payment resource', async () => {
    const c = await content();
    assert.equal(computeCommandCost(c, 'buy_magic', [999, 'g']), null);
    assert.equal(computeCommandCost(c, 'buy_magic', [1, 'x']), null);
    assert.equal(computeCommandCost(c, 'buy_magic', [1]), null);
  });

  it('prices the fixed mana pack from the globals', async () => {
    const c = await content();
    assert.deepEqual(computeCommandCost(c, 'buy_mana_new', [5, 'c'])?.cost, { c: 1 });
    assert.deepEqual(computeCommandCost(c, 'buy_mana_new', [5, 'g'])?.cost, { g: 10_000 });
  });

  it('refuses a mana amount that is not the one pack', async () => {
    const c = await content();
    assert.equal(computeCommandCost(c, 'buy_mana_new', [4, 'c']), null);
    assert.equal(computeCommandCost(c, 'buy_mana_new', [6, 'g']), null);
  });

  it('prices a cast at the spell mana cost', async () => {
    const c = await content();
    assert.deepEqual(computeCommandCost(c, 'use_magic', [1])?.cost, { m: 8 });
    assert.equal(computeCommandCost(c, 'use_magic', [999]), null);
  });

  it('lists the magic commands as priced', () => {
    assert.ok(PRICED_COMMANDS.includes('buy_magic'));
    assert.ok(PRICED_COMMANDS.includes('buy_mana_new'));
    assert.ok(PRICED_COMMANDS.includes('use_magic'));
  });
});

describe('applying a cost', () => {
  it('subtracts the cost and adds the gain', async () => {
    const c = await content();
    const result = applyCommandCost({ g: 1000, w: 0, s: 100 }, {
      cost: { g: 30, s: 60 },
      gain: { g: 5 },
    });
    assert.equal(result.ok, true);
    assert.deepEqual(result.resources, { g: 975, w: 0, s: 40 });
  });

  it('refuses when the player cannot afford it, and changes nothing', async () => {
    const result = applyCommandCost({ g: 10, s: 0 }, { cost: { g: 30, s: 60 }, gain: {} });
    assert.equal(result.ok, false);
    assert.equal(result.reason, 'insufficient-resources');
    assert.deepEqual(result.resources, { g: 10, s: 0 });
  });

  it('treats an unpriced command as free, never as "accept the claim"', async () => {
    const result = applyCommandCost({ g: 10 }, null);
    assert.equal(result.ok, true);
    assert.deepEqual(result.resources, { g: 10 });
  });
});

describe('settling a command', () => {
  it('computes the cost itself and ignores any client claim', async () => {
    const c = await content();
    const wallet = { g: 100, s: 100, w: 100, c: 100, e: 100 };
    const result = settleCommand(c, wallet, 'buy', [1, 1007, 0, 0, 1, 0, 0]);
    assert.equal(result.ok, true);
    // 30 gold and 60 steel spent, 1 cash spent.
    assert.equal(result.resources['g'], 70);
    assert.equal(result.resources['s'], 40);
    assert.equal(result.resources['c'], 99);
  });

  it('refuses a purchase the player cannot afford', async () => {
    const c = await content();
    const result = settleCommand(c, { g: 1, s: 1 }, 'buy', [1, 1007, 0, 0, 1, 0, 0]);
    assert.equal(result.ok, false);
    assert.equal(result.reason, 'insufficient-resources');
  });
});

describe('levelling a unit up', () => {
  it('costs ceil(life / divisor)', () => {
    const table = [
      { cashDivisor: 0 },
      { cashDivisor: 50 },
      { cashDivisor: 25 },
      { cashDivisor: 12 },
    ];
    assert.equal(computeLevelUpCost(table, 100, 1), 2);
    assert.equal(computeLevelUpCost(table, 100, 2), 4);
    assert.equal(computeLevelUpCost(table, 100, 3), 9);
  });
});
