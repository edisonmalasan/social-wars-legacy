import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { CostOfferPack } from '@swl/rules';

import { createApplier, type ApplierDeps, type ApplierItem } from './apply.ts';
import { mapStore } from './mapstore.ts';
import type { ShimWorld } from './shim.ts';

const NOW = 1_700_000_000;

const deps = (over: Partial<ApplierDeps> = {}): ApplierDeps => ({
  now: () => NOW,
  tzOffsetHours: 0,
  collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
  dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
  ...over,
});

function item(id: number, over: Partial<ApplierItem> = {}): ApplierItem {
  return {
    id,
    name: `Item ${id}`,
    costs: {},
    costUnitCash: 0,
    buildTime: 0,
    trainingTime: 0,
    clicksToBuild: 0,
    minLevel: 1,
    unitCapacity: 0,
    population: 0,
    buildingLimitSameId: -1,
    buildingLimitSameScf: -1,
    subcategoryId: 1,
    width: 1,
    height: 1,
    trainsIds: [],
    upgradesTo: null,
    premiumUpgradeCosts: {},
    type: 'b',
    multiCollectable: false,
    grantsPopulation: false,
    ...over,
  };
}

const ITEMS = new Map(
  [10, 11, 12, 13, 14, 1001].map((id) => [
    id,
    item(id, id === 1001 ? { type: 'u' } : {}),
  ]),
);

function world(): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, items: {}, store: {} }],
      privateState: {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 1000, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

function pack(over: Partial<CostOfferPack> & Pick<CostOfferPack, 'id'>): CostOfferPack {
  return {
    name: `Pack ${over.id}`,
    type: '',
    enabled: 1,
    position: 1,
    cost_cash: 25,
    gold: 0,
    wood: 0,
    oil: 0,
    steel: 0,
    mana: 0,
    xp: 0,
    items: [],
    ...over,
  };
}

const FLAT = pack({ id: 1, items: [10, 11] });
const RANDOM = pack({
  id: 4,
  items: [
    [10, 35],
    [11, 70],
    [12, 100],
  ],
});
const SUPER = pack({
  id: 44,
  type: 'super',
  items: [[10], [11, 12], [13, 14]],
});

function applierFor(...packs: CostOfferPack[]) {
  return createApplier(
    deps({
      items: ITEMS,
      offerPacks: new Map(packs.map((candidate) => [candidate.id, candidate])),
    }),
  );
}

function stored(outcome: ReturnType<ReturnType<typeof createApplier>>): Record<string, number> {
  return mapStore(outcome.world.save.maps[0] as Record<string, unknown>);
}

describe('buying an offer pack', () => {
  it('grants every item of a flat pack and ignores the client list', () => {
    const applier = applierFor(FLAT);
    const outcome = applier(world(), {
      name: 'buy_offer_pack',
      args: [1, '["12"]'],
    });
    assert.equal(outcome.applied, true);
    assert.deepEqual(stored(outcome), { '10': 1, '11': 1 });
    assert.equal(outcome.world.save.privateState['offerPackRolls'], undefined);
  });

  it('rolls a random pack itself instead of granting the client list', () => {
    const applier = applierFor(RANDOM);
    const outcome = applier(world(), {
      name: 'buy_offer_pack',
      args: [4, '["10","11","12"]'],
    });
    assert.equal(outcome.applied, true);
    const items = stored(outcome);
    assert.equal(Object.values(items).reduce((sum, quantity) => sum + quantity, 0), 1);
    assert.ok(Object.keys(items).every((id) => ['10', '11', '12'].includes(id)));
    assert.equal(outcome.world.save.privateState['offerPackRolls'], 1);
  });

  it('uses the selected-item count only to choose a super tier', () => {
    const applier = applierFor(SUPER);

    const tier0 = applier(world(), { name: 'buy_offer_pack', args: [44, '["10"]'] });
    assert.equal(tier0.applied, true);
    assert.equal(Object.values(stored(tier0)).reduce((sum, n) => sum + n, 0), 1);
    assert.equal(stored(tier0)['10'], undefined);

    const tier1 = applier(world(), {
      name: 'buy_offer_pack',
      args: [44, '["10","10"]'],
    });
    assert.equal(tier1.applied, true);
    assert.equal(Object.values(stored(tier1)).reduce((sum, n) => sum + n, 0), 2);

    const tier2 = applier(world(), {
      name: 'buy_offer_pack',
      args: [44, '["10","10","10","10"]'],
    });
    assert.equal(tier2.applied, true);
    assert.equal(Object.values(stored(tier2)).reduce((sum, n) => sum + n, 0), 4);
    // Tier two always includes one item from the rare row.
    assert.ok((stored(tier2)['10'] ?? 0) >= 1);
  });

  it('refuses the premium pack entry', () => {
    const premium = pack({ id: 18, type: 'premium_account', items: null });
    const outcome = applierFor(premium)(world(), {
      name: 'buy_offer_pack',
      args: [18, '[]'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'premium-not-a-pack');
    assert.deepEqual(stored(outcome), {});
  });

  it('refuses a hidden or disabled pack', () => {
    const hidden = pack({ id: 4, enabled: 0, position: 0, items: [10] });
    const outcome = applierFor(hidden)(world(), {
      name: 'buy_offer_pack',
      args: [4, '[]'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'pack-unavailable');
    assert.deepEqual(stored(outcome), {});
  });

  it('refuses a malformed item id instead of storing it', () => {
    const malformed = pack({
      id: 35,
      type: 'super',
      items: [[10], [11], [1072.1224]],
    });
    const outcome = applierFor(malformed)(world(), {
      name: 'buy_offer_pack',
      args: [35, '["10","10","10","10"]'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'bad-pack-item');
    assert.deepEqual(stored(outcome), {});
  });

  it('refuses an item the content does not have', () => {
    const unknown = pack({ id: 50, items: [99] });
    const outcome = applierFor(unknown)(world(), {
      name: 'buy_offer_pack',
      args: [50, '[]'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'unknown-pack-item');
    assert.deepEqual(stored(outcome), {});
  });

  it('refuses a bad tier, a bad selection or an unknown pack', () => {
    const applier = applierFor(SUPER);
    assert.equal(
      applier(world(), { name: 'buy_offer_pack', args: [44, '["10","10","10"]'] }).refused,
      'bad-tier',
    );
    assert.equal(
      applier(world(), { name: 'buy_offer_pack', args: [44, 'not json'] }).refused,
      'bad-argument',
    );
    assert.equal(
      applier(world(), { name: 'buy_offer_pack', args: [999, '[]'] }).refused,
      'unknown-pack',
    );
  });

  it('lets a purchased building be placed exactly once', () => {
    const applier = applierFor(FLAT);
    const bought = applier(world(), { name: 'buy_offer_pack', args: [1, '[]'] });
    assert.equal(bought.applied, true);

    const first = applier(bought.world, {
      name: 'place_stored_item',
      args: [1, 10, 5, 6, 1, 0, 0],
    });
    assert.equal(first.applied, true);
    assert.deepEqual(stored(first), { '11': 1 });

    const second = applier(first.world, {
      name: 'place_stored_item',
      args: [1, 10, 8, 9, 1, 0, 0],
    });
    assert.equal(second.applied, false);
    assert.equal(second.refused, 'not-stored');
  });
});
