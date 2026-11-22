/**
 * Server-authoritative Soul Mixer appliers.
 *
 * These tests pin the cheat-resistant parts: the client's declared output id
 * and cash delta are never trusted, the level-20 gate refuses the two gated
 * units, and every price comes from the server's rules/content.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  Random,
  SOUL_MIXER_LEVEL20_GATE_MESSAGE,
  SOUL_MIXER_POWERUPS,
  applyCommandCost,
  buildSoulMixerCatalog,
  computeCommandCost,
  costContentFrom,
  fuseWithPowerups,
  hashSeed,
  soulMixerSpeedupCost,
  soulMixerTrainingTime,
  type SoulMixerItemData,
} from '@swl/rules';

import {
  SOUL_MIXER_POWERUPS_KEY,
  createApplier,
  mapItems,
  type ApplierDeps,
  type ApplierItem,
  type MapItemTuple,
} from './apply.ts';
import { LegacyIdentityBridge } from './session.ts';
import { applyBatch, type ShimContext, type ShimWorld } from './shim.ts';

const NOW = 1_700_000_000;
const ISO = '7';
const MIXER = 302;
const SEED = 'fusion-test';

/**
 * Units with a breeding order equal to their id, so power == id. Forty rungs
 * keep the largest power-up increment from walking off the end of the catalog.
 */
function ladderItems(): ApplierItem[] {
  const ids = Array.from({ length: 40 }, (_, index) => (index + 1) * 10);
  ids.push(1226, 1263);
  return ids.map((id) => ({
    id,
    name: `unit-${id}`,
    costs: {},
    costUnitCash: 0,
    buildTime: 1,
    trainingTime: 60,
    clicksToBuild: 0,
    minLevel: 1,
    unitCapacity: 0,
    population: 0,
    buildingLimitSameId: -1,
    buildingLimitSameScf: -1,
    subcategoryId: 0,
    width: 1,
    height: 1,
    trainsIds: [],
    upgradesTo: null,
    premiumUpgradeCosts: {},
    type: 'u',
    multiCollectable: false,
    grantsPopulation: false,
    life: id * 20,
    breedingOrder: id,
  }));
}

function catalogData(): SoulMixerItemData[] {
  return ladderItems().map((item) => ({ id: item.id, breeding_order: item.breedingOrder! }));
}

function mixerItem(): ApplierItem {
  return {
    id: MIXER,
    name: 'Atom Fusion',
    costs: {},
    costUnitCash: 0,
    buildTime: 60,
    trainingTime: 60,
    clicksToBuild: 0,
    minLevel: 1,
    unitCapacity: 2,
    population: 0,
    buildingLimitSameId: 1,
    buildingLimitSameScf: 1,
    subcategoryId: 211,
    width: 3,
    height: 3,
    trainsIds: [],
    upgradesTo: null,
    premiumUpgradeCosts: {},
    type: 'b',
    multiCollectable: false,
    grantsPopulation: false,
  };
}

function contentItems(): Map<number, ApplierItem> {
  return new Map([
    [MIXER, mixerItem()],
    ...ladderItems().map((item) => [item.id, item] as const),
  ]);
}

function deps(over: Partial<ApplierDeps> = {}): ApplierDeps {
  return {
    now: () => NOW,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
    dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
    serverSeed: SEED,
    items: contentItems(),
    ...over,
  };
}

function mixerWorld(
  inputs: number[],
  over: { level?: number; attrs?: Record<string, unknown>; cash?: number } = {},
): ShimWorld {
  const attrs: Record<string, unknown> = { width: 3, height: 3, clicked: 0, ...over.attrs };
  const tuple: MapItemTuple = [MIXER, 0, 0, 0, 0, inputs.map((id) => [id, 0, 0]), attrs, 1];
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, items: { [ISO]: tuple }, store: {}, level: over.level ?? 20 }],
      privateState: {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: over.cash ?? 1000, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

function attrs(world: ShimWorld): Record<string, unknown> {
  return mapItems(world.save.maps[0])[ISO]![6] as Record<string, unknown>;
}

function expectedFusion(inputs: [number, number], powerups: number[] = []) {
  return fuseWithPowerups(
    buildSoulMixerCatalog(catalogData()),
    inputs[0],
    inputs[1],
    powerups,
    new Random(hashSeed(`${SEED}:soulmixer:${ISO}:1`)),
  );
}

describe('push_queue_unit2 (the soul mixer)', () => {
  it('ignores the client-declared output id and derives it from server state', () => {
    const outcome = createApplier(deps())(mixerWorld([10, 20]), {
      name: 'push_queue_unit2',
      args: [Number(ISO), 999999],
    });
    assert.equal(outcome.applied, true);
    const expected = expectedFusion([10, 20]);
    assert.equal(attrs(outcome.world)['ui'], expected.result.id);
    assert.notEqual(attrs(outcome.world)['ui'], 999999);
    assert.equal(attrs(outcome.world)['nu'], 1);
    assert.equal(attrs(outcome.world)['smTrainingTime'], soulMixerTrainingTime(expected.result.power));
  });

  it('applies server-recorded powerups instead of trusting the client', () => {
    const applier = createApplier(deps());
    const bought = applier(mixerWorld([10, 20]), { name: 'buy_powerups', args: [3] });
    assert.equal(bought.applied, true);
    assert.deepEqual(bought.world.save.privateState[SOUL_MIXER_POWERUPS_KEY], [3]);
    const outcome = applier(bought.world, {
      name: 'push_queue_unit2',
      args: [Number(ISO), 999999],
    });
    assert.equal(outcome.applied, true);
    assert.equal(attrs(outcome.world)['ui'], expectedFusion([10, 20], [3]).result.id);
    assert.deepEqual(outcome.world.save.privateState[SOUL_MIXER_POWERUPS_KEY], []);
  });

  it('refuses the two gated units below level 20 and changes nothing', () => {
    for (const id of [1226, 1263]) {
      const world = mixerWorld([id, 100], { level: 19, cash: 500 });
      const before = JSON.stringify(world);
      const outcome = createApplier(deps())(world, {
        name: 'push_queue_unit2',
        args: [Number(ISO), 12345],
      });
      assert.equal(outcome.applied, false);
      assert.equal(outcome.refused, SOUL_MIXER_LEVEL20_GATE_MESSAGE);
      assert.equal(JSON.stringify(world), before);
    }
  });

  it('allows the gated units at level 20', () => {
    const outcome = createApplier(deps())(mixerWorld([1226, 100], { level: 20 }), {
      name: 'push_queue_unit2',
      args: [Number(ISO), 12345],
    });
    assert.equal(outcome.applied, true);
  });

  it('refuses an unknown building without touching the wallet', () => {
    const world = mixerWorld([10, 20], { cash: 500 });
    const before = JSON.stringify(world.resources);
    const outcome = createApplier(deps())(world, {
      name: 'push_queue_unit2',
      args: [999, 10],
    });
    assert.equal(outcome.applied, false);
    assert.equal(JSON.stringify(outcome.world.resources), before);
  });
});

describe('buy_powerups pricing', () => {
  it('charges the content cash cost, never a client-declared price', () => {
    const content = costContentFrom({
      items: [],
      offerPacks: [],
      globals: { SOUL_MIXER_POWERUPS_LEVELS: SOUL_MIXER_POWERUPS },
      expansionPrices: [],
    });
    const cost = computeCommandCost(content, 'buy_powerups', [3]);
    assert.equal(cost?.cost['c'], 8);
    const world = mixerWorld([10, 20], { cash: 100 });
    const settled = applyCommandCost(world.resources, cost);
    assert.equal(settled.ok, true);
    const outcome = createApplier(deps())({ ...world, resources: settled.resources }, {
      name: 'buy_powerups',
      args: [3, 1],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 92);
    assert.deepEqual(outcome.world.save.privateState[SOUL_MIXER_POWERUPS_KEY], [3]);
  });

  it('refuses a level outside the six shipped tiers', () => {
    const world = mixerWorld([10, 20]);
    const before = JSON.stringify(world);
    const outcome = createApplier(deps())(world, { name: 'buy_powerups', args: [99] });
    assert.equal(outcome.applied, false);
    assert.equal(JSON.stringify(world), before);
  });
});

describe('soulmixer_speedup', () => {
  it('charges the rules price and finishes the training', () => {
    const trainingTime = 10000;
    const elapsed = 6400;
    const world = mixerWorld([10, 20], {
      attrs: { nu: 1, ts: NOW - elapsed, ui: 30, smTrainingTime: trainingTime },
      cash: 100,
    });
    const outcome = createApplier(deps())(world, {
      name: 'soulmixer_speedup',
      args: [Number(ISO), -999],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 100 - soulMixerSpeedupCost(trainingTime, elapsed));
    assert.equal(attrs(outcome.world)['ts'], 0);
  });

  it('refuses an unaffordable speed-up and leaves state unchanged', () => {
    const world = mixerWorld([10, 20], {
      attrs: { nu: 1, ts: NOW, ui: 30, smTrainingTime: 10000 },
      cash: 0,
    });
    const before = JSON.stringify(world);
    const outcome = createApplier(deps())(world, {
      name: 'soulmixer_speedup',
      args: [Number(ISO)],
    });
    assert.equal(outcome.applied, false);
    assert.equal(JSON.stringify(world), before);
  });

  it('refuses a speed-up with no training in progress', () => {
    const world = mixerWorld([10, 20], { cash: 100 });
    const before = JSON.stringify(world);
    const outcome = createApplier(deps())(world, {
      name: 'soulmixer_speedup',
      args: [Number(ISO)],
    });
    assert.equal(outcome.applied, false);
    assert.equal(JSON.stringify(world), before);
  });

  it('ignores the client-declared cash delta in the legacy batch', () => {
    const trainingTime = 10000;
    const elapsed = 6400;
    const world = mixerWorld([10, 20], {
      attrs: { nu: 1, ts: NOW - elapsed, ui: 30, smTrainingTime: trainingTime },
      cash: 100,
    });
    const content = costContentFrom({
      items: [],
      offerPacks: [],
      globals: { SOUL_MIXER_POWERUPS_LEVELS: SOUL_MIXER_POWERUPS },
      expansionPrices: [],
    });
    const context: ShimContext = {
      world,
      content,
      now: NOW,
      identity: new LegacyIdentityBridge(),
      applyCommand: createApplier(deps()),
    };
    // slot 6 of the 8-slot vector is cash; the client claims +999.
    const outcome = applyBatch(
      {
        first_number: 1,
        commands: [['0', 'soulmixer_speedup', [Number(ISO)], [0, 0, 0, 0, 0, 0, 999, 0]]],
      },
      context,
    );
    assert.deepEqual(outcome.refused, []);
    assert.equal(outcome.world.resources['c'], 100 - soulMixerSpeedupCost(trainingTime, elapsed));
    assert.equal(attrs(outcome.world)['ts'], 0);
  });
});
