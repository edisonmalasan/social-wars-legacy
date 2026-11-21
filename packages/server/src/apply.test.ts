import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  GOALS,
  DART_COST_CASH,
  QUEST_ID_01_BAZOOKA,
  QUEST_ID_02_CENTRAL_NUCLEAR,
  QUEST_ID_03_DEFEND_CONVOY_AUTO,
  QUEST_ID_06_AIRSTRIKE,
  QUEST_ID_15_HARDCORE1,
  QUEST_ID_WEEKLY_01,
  WEEKLY_BOT_REFS,
  WEEKLY_CASH_PER_BOT,
  applyCommandCost,
  buildDartsBoard,
  createGoalState,
  currentDartsGame,
  getGoalDefinition,
  getQuestSpec,
  hashSeed,
  type QuestState,
} from '@swl/rules';

import {
  ACTIVE_QUEST_KEY,
  type ActiveQuestState,
  type ApplierItem,
  BUILDING_STATE_KEYS,
  GOAL_STATE_KEY,
  LAST_QUEST_REWARD_KEY,
  QUEST_PROGRESS_KEY,
  createApplier,
  createQuestHelpers,
  hasActivePremium,
  mapItems,
  questRoster,
  type ApplierDeps,
  type MapItemTuple,
} from './apply.ts';
import { storeQuantity } from './mapstore.ts';
import type { ShimWorld } from './shim.ts';

const NOW = 1_700_000_000;

const deps = (over: Partial<ApplierDeps> = {}): ApplierDeps => ({
  now: () => NOW,
  tzOffsetHours: 0,
  collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
  dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
  ...over,
});

/** A map with one producing building. */
function worldWithBuilding(
  attrs: Record<string, unknown>,
  over: Partial<ShimWorld> = {},
): ShimWorld {
  const tuple: MapItemTuple = [30, 0, 0, 0, 0, [], attrs, 1];
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, items: { '7': tuple }, store: { '30': 1 } }],
      privateState: {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
    ...over,
  };
}

/** A map with the given items on it. */
function worldWithItems(items: Record<string, MapItemTuple>): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, items, store: { '30': 1 } }],
      privateState: {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

/** A wallet with the given amount of cash. */
function wallet(cash: number): ShimWorld['resources'] {
  return { g: 0, w: 0, o: 0, s: 0, c: cash, e: 100, x: 0, m: 0 };
}

/** A wallet with the given resources. */
function purse(resources: Partial<ShimWorld['resources']>): ShimWorld['resources'] {
  return { g: 0, w: 0, o: 0, s: 0, c: 0, e: 100, x: 0, m: 0, ...resources };
}

/** A complete content item, for the applier. */
function item(over: Partial<ApplierItem> = {}): ApplierItem {
  return {
    id: 30,
    name: 'Academy I',
    costs: {},
    costUnitCash: 0,
    buildTime: 60,
    trainingTime: 60,
    clicksToBuild: 0,
    minLevel: 1,
    unitCapacity: 0,
    population: 0,
    buildingLimitSameId: -1,
    buildingLimitSameScf: -1,
    subcategoryId: 31,
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

describe('the map item accessor', () => {
  it('reads the items out of a map', () => {
    const items = mapItems({ items: { '7': [30, 0, 0, 0, 0, [], {}, 1] } });
    assert.equal(items['7']?.[0], 30);
  });

  it('returns nothing for a map with no items', () => {
    assert.deepEqual(mapItems(undefined), {});
    assert.deepEqual(mapItems({}), {});
  });
});

describe('placing a building', () => {
  it('places a building on a free tile', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    const world = worldWithBuilding({});
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, true);
    const items = mapItems(outcome.world.save.maps[0] as Record<string, unknown>);
    // The building is on the map at the tile it was placed on.
    const placed = Object.values(items).filter(
      (tuple) => tuple[0] === 30 && tuple[1] === 5 && tuple[2] === 6,
    );
    assert.equal(placed.length, 1);
    assert.equal(placed[0]![1], 5);
    assert.equal(placed[0]![2], 6);
  });

  it('refuses a building the player is too low a level for', () => {
    const applier = createApplier(
      deps({ items: new Map([[30, item({ minLevel: 10 })]]) }),
    );
    const world = worldWithBuilding({});
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'level');
  });

  it('refuses a tile that is already taken', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    // The map already has a building at (0, 0).
    const world = worldWithBuilding({ width: 1, height: 1 });
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 0, 0, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'tile-taken');
  });

  it('refuses a building whose whole footprint is free only in part', () => {
    const applier = createApplier(
      deps({ items: new Map([[30, item({ width: 2, height: 2 })]]) }),
    );
    const world = worldWithBuilding({ width: 1, height: 1 });
    // The existing building is at (0, 0); the new one is two tiles square
    // and starts at (0, 0), so it would cover the existing one.
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 0, 0, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'tile-taken');
  });

  it('refuses a building the player has too many of', () => {
    const applier = createApplier(
      deps({ items: new Map([[30, item({ buildingLimitSameId: 1 })]]) }),
    );
    const world = worldWithBuilding({});
    // There is already one Academy.
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'same-id-limit');
  });

  it('refuses a building that would break the population ceiling', () => {
    const applier = createApplier(
      deps({
        items: new Map([[30, item({ population: 50 })]]),
        populationRules: {
          startMaxPopulation: 20,
          maxPopulationCap: 175,
          maxPopulationPerLevel: 3,
        },
      }),
    );
    const world = worldWithBuilding({});
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'population');
  });

  it('raises the ceiling with the population the buildings grant', () => {
    // A House I grants 3 population, so the ceiling is 20 + 3 = 23.
    const applier = createApplier(
      deps({
        items: new Map([
          [1, item({ id: 1, population: 3, grantsPopulation: true })],
          [30, item({ id: 30, population: 24, grantsPopulation: true })],
        ]),
        populationRules: {
          startMaxPopulation: 20,
          maxPopulationCap: 175,
          maxPopulationPerLevel: 3,
        },
      }),
    );
    const world = worldWithItems({
      '7': [1, 0, 0, 0, 0, [], {}, 1],
    });
    // The building costs 24 population and the ceiling is 23.
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'population');
  });

  it('counts a unit\'s population as used, not as granted', () => {
    // A unit uses population, so it lowers what is left rather than
    // raising the ceiling.
    const applier = createApplier(
      deps({
        items: new Map([
          [1, item({ id: 1, population: 3, grantsPopulation: true })],
          [1001, item({ id: 1001, type: 'u', population: 19, grantsPopulation: false })],
          [30, item({ id: 30, population: 5, grantsPopulation: true })],
        ]),
        populationRules: {
          startMaxPopulation: 20,
          maxPopulationCap: 175,
          maxPopulationPerLevel: 3,
        },
      }),
    );
    const world = worldWithItems({
      '7': [1, 0, 0, 0, 0, [], {}, 1],
      '8': [1001, 1, 1, 0, 0, [], {}, 1],
    });
    // The ceiling is 23 and 19 are used, so a building that costs 5
    // does not fit.
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'population');
  });

  it('refuses an item the content does not have', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    const world = worldWithBuilding({});
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 999999, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'unknown-item');
  });

  it('buys and places a building', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    const world = worldWithBuilding({});
    const outcome = applier(world, {
      name: 'buy',
      args: [1, 30, 5, 6, 1, 0, 0, 'b'],
    });
    assert.equal(outcome.applied, true);
    const items = mapItems(outcome.world.save.maps[0] as Record<string, unknown>);
    assert.equal(
      Object.values(items).filter((tuple) => tuple[0] === 30 && tuple[1] === 5).length,
      1,
    );
  });

  it('gives each placement its own iso id and spends one stored item each', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    const world = worldWithBuilding({});
    const map = world.save.maps[0] as Record<string, unknown>;
    map['store'] = { '30': 2 };
    const first = applier(world, { name: 'place_stored_item', args: [1, 30, 5, 6, 1, 0, 0] });
    assert.equal(first.applied, true);
    const second = applier(first.world, {
      name: 'place_stored_item',
      args: [1, 30, 8, 9, 1, 0, 0],
    });
    assert.equal(second.applied, true);
    const items = mapItems(second.world.save.maps[0] as Record<string, unknown>);
    assert.equal(Object.keys(items).length, 3);
    assert.deepEqual((second.world.save.maps[0] as Record<string, unknown>)['store'], {});
  });

  it('refuses to place an item the store does not hold', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    const world = worldWithBuilding({});
    (world.save.maps[0] as Record<string, unknown>)['store'] = {};
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 30, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-stored');
  });

  it('does not place a stored unit as a building', () => {
    const applier = createApplier(
      deps({ items: new Map([[1001, item({ id: 1001, type: 'u' })]]) }),
    );
    const world = worldWithBuilding({});
    (world.save.maps[0] as Record<string, unknown>)['store'] = { '1001': 1 };
    const outcome = applier(world, {
      name: 'place_stored_item',
      args: [1, 1001, 5, 6, 1, 0, 0],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-a-building');
  });
});

describe('collecting', () => {
  it('computes the amount from the building own state', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({
      collect: 100,
      unitCapacity: 5,
      unitsInside: 0,
      collectType: 'w',
      cp: 2,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, true);
    // The base amount, times the period-2 multiplier of 1.
    assert.equal(outcome.world.resources['w'], 100);
    // The production is reset and the timer restamped.
    const attrs = mapItems(outcome.world.save.maps[0] as Record<string, unknown>)['7']?.[6] as Record<string, unknown>;
    assert.equal(attrs['collect'], 0);
    assert.equal(attrs['lastAccruedAt'], NOW);
  });

  it('applies the period multiplier', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({
      collect: 100,
      unitCapacity: 5,
      unitsInside: 0,
      collectType: 'w',
      cp: 4,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    // The period-4 multiplier is 3.
    assert.equal(outcome.world.resources['w'], 300);
  });

  it('refuses the over-capacity hack and collects nothing', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({
      collect: 100,
      unitCapacity: 2,
      unitsInside: 3,
      collectType: 'w',
      cp: 2,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'over-capacity');
    assert.equal(outcome.world.resources['w'], 0);
  });

  it('refuses a building that does not exist', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'collect', args: ['999'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'unknown-building');
  });

  it('uses the building own resource type', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({
      collect: 50,
      unitCapacity: 5,
      unitsInside: 0,
      collectType: 's',
      cp: 2,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.world.resources['s'], 50);
    assert.equal(outcome.world.resources['w'], 0);
  });

  it('names every production state key', () => {
    assert.equal(BUILDING_STATE_KEYS.length, 6);
    assert.ok(BUILDING_STATE_KEYS.includes('collect'));
    assert.ok(BUILDING_STATE_KEYS.includes('unitCapacity'));
  });
});

describe('the premium account', () => {
  const PACKAGES = [
    { price: 800, time: 360 },
    { price: 450, time: 180 },
    { price: 80, time: 30 },
    { price: 40, time: 7 },
    { price: 20, time: 3 },
    { price: 8, time: 1 },
  ];

  it('starts the premium fresh when it has lapsed', () => {
    const applier = createApplier(
      deps({ premiumPackages: PACKAGES, now: () => 1_700_000_000 }),
    );
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'buy_premium_account', args: [5] });
    assert.equal(outcome.applied, true);
    // One day from now.
    assert.equal(
      outcome.world.save.privateState['timeStampEndPremium'],
      1_700_000_000 + 86_400,
    );
  });

  it('EXTENDS a running premium', () => {
    const applier = createApplier(
      deps({ premiumPackages: PACKAGES, now: () => 1_700_000_000 }),
    );
    const world = worldWithBuilding({});
    world.save.privateState['timeStampEndPremium'] = 1_700_000_000 + 1000;
    const outcome = applier(world, { name: 'buy_premium_account', args: [3] });
    assert.equal(outcome.applied, true);
    // Seven more days on top of what was left.
    assert.equal(
      outcome.world.save.privateState['timeStampEndPremium'],
      1_700_000_000 + 1000 + 7 * 86_400,
    );
  });

  it('refuses a package that does not exist', () => {
    const applier = createApplier(
      deps({ premiumPackages: PACKAGES, now: () => 1_700_000_000 }),
    );
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'buy_premium_account', args: [99] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-such-package');
  });

  it('knows whether the premium is running', () => {
    const applier = createApplier(
      deps({ premiumPackages: PACKAGES, now: () => 1_700_000_000 }),
    );
    const world = worldWithBuilding({});
    world.save.privateState['timeStampEndPremium'] = 1_700_000_000 + 1000;
    assert.equal(hasActivePremium(world, 1_700_000_000), true);
    assert.equal(hasActivePremium(world, 1_700_000_000 + 2000), false);
  });
});

describe("the tutorial's progression", () => {
  it('records the step the client reached', () => {
    const applier = createApplier(deps({}));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'complete_tutorial', args: [101] });
    assert.equal(outcome.applied, true);
    const state = outcome.world.save.privateState['tutorial'] as {
      step: number;
      complete: boolean;
    };
    assert.equal(state.step, 101);
    assert.equal(state.complete, false);
  });

  it('refuses a step the tutorial does not have', () => {
    const applier = createApplier(deps({}));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'complete_tutorial', args: [999] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'unknown-step');
  });

  it('refuses a step that is not a number', () => {
    const applier = createApplier(deps({}));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'complete_tutorial', args: ['lots'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'bad-argument');
  });

  it('only ever goes FORWARDS', () => {
    // The client can walk back through the tutorial, and the furthest
    // step is the one that counts.
    const applier = createApplier(deps({}));
    let world = worldWithBuilding({});
    world = applier(world, { name: 'complete_tutorial', args: [105] }).world;
    world = applier(world, { name: 'complete_tutorial', args: [102] }).world;
    const state = world.save.privateState['tutorial'] as { step: number };
    assert.equal(state.step, 105);
  });
});

describe('the production clock', () => {
  it('refuses a collection that is not due yet', () => {
    // The building started its countdown a moment ago, on the one-hour
    // period, so collecting now is too early.
    const applier = createApplier(deps({ now: () => 1_700_000_000 }));
    const world = worldWithBuilding({
      cp: 2,
      lastAccruedAt: 1_700_000_000,
      collectType: 'w',
      collect: 100,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-due');
    assert.equal(outcome.world.resources['w'], 0);
  });

  it('allows a collection once the period has elapsed', () => {
    const applier = createApplier(deps({ now: () => 1_700_000_000 + 60 * 60 }));
    const world = worldWithBuilding({
      cp: 2,
      lastAccruedAt: 1_700_000_000,
      collectType: 'w',
      collect: 100,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, true);
    // The one-hour period is worth the base amount.
    assert.equal(outcome.world.resources['w'], 100);
  });

  it('starts the countdown again after a collection', () => {
    const applier = createApplier(deps({ now: () => 1_700_000_000 + 60 * 60 }));
    const world = worldWithBuilding({
      cp: 2,
      lastAccruedAt: 1_700_000_000,
      collectType: 'w',
      collect: 100,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, true);
    // The next collection is another hour away.
    const attrs = mapItems(outcome.world.save.maps[0] as Record<string, unknown>)[
      '7'
    ]![6] as Record<string, unknown>;
    assert.equal(attrs['lastAccruedAt'], 1_700_000_000 + 60 * 60);
  });

  it('collects a fresh building at once', () => {
    // A building that has never been collected from is due immediately.
    const applier = createApplier(deps({ now: () => 1_700_000_000 }));
    const world = worldWithBuilding({
      cp: 2,
      lastAccruedAt: 0,
      collectType: 'w',
      collect: 100,
    });
    const outcome = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['w'], 100);
  });

  it('uses the one-hour period for a building with no choice', () => {
    // The client's own multiplier for a building that is not
    // "multi-collectable" is 1, which is the one-hour period.
    const applier = createApplier(deps({ now: () => 1_700_000_000 }));
    const world = worldWithBuilding({
      cp: 0,
      lastAccruedAt: 1_700_000_000,
      collectType: 'w',
      collect: 100,
    });
    const early = applier(world, { name: 'collect', args: ['7'] });
    assert.equal(early.refused, 'not-due');

    const later = createApplier(deps({ now: () => 1_700_000_000 + 60 * 60 }));
    const outcome = later(world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, true);
  });
});

/* -------------------------------------------------------------------------
 * Choosing a collection period
 * ---------------------------------------------------------------------- */

const ACTIVATE_START = 1_700_000_000;

/** A multi-collectable producer, the only building that may choose a period. */
function producer(over: Partial<ApplierItem> = {}): ApplierItem {
  return item({ multiCollectable: true, buildTime: 60, ...over });
}

/** Applier deps with the given content items and a given server clock. */
function activateDeps(items: ApplierItem[], clock = ACTIVATE_START): ApplierDeps {
  return deps({ now: () => clock, items: new Map(items.map((entry) => [entry.id, entry])) });
}

/** A producer with the given attribute bag and build timestamp. */
function producerWorld(
  attrs: Record<string, unknown>,
  startedAt = 0,
  itemId = 30,
): ShimWorld {
  return worldWithItems({ '7': [itemId, 0, 0, startedAt, 0, [], attrs, 1] });
}

/** A producer's attribute bag from a world. */
function producerAttrs(world: ShimWorld): Record<string, unknown> {
  const tuple = mapItems(world.save.maps[0] as Record<string, unknown>)['7']!;
  return tuple[6] as Record<string, unknown>;
}

describe('choosing a collection period', () => {
  it('stores all four periods from the server clock, leaving the wallet and build time alone', () => {
    for (const period of [1, 2, 3, 4]) {
      const clock = ACTIVATE_START + period;
      const applier = createApplier(activateDeps([producer()], clock));
      const world = producerWorld({ collect: 100, unitCapacity: 5, collectType: 'w' });
      const outcome = applier(world, { name: 'activate', args: ['7', period] });
      assert.equal(outcome.applied, true, `period ${period} was refused`);
      const attrs = producerAttrs(outcome.world);
      assert.equal(attrs['cp'], period, `period ${period} was not stored`);
      assert.equal(attrs['lastAccruedAt'], clock, `period ${period} used a wrong clock`);
      assert.equal(outcome.world.resources['w'], 0, 'activate changed the wallet');
      assert.equal(
        mapItems(outcome.world.save.maps[0] as Record<string, unknown>)['7']![3],
        0,
        'activate overwrote the build timestamp',
      );
    }
  });

  it('credits floor(collect x multiplier) once the content minutes have elapsed', () => {
    const minutes = [5, 60, 240, 480];
    const expected = [25, 100, 200, 300];
    for (const [index, period] of [1, 2, 3, 4].entries()) {
      const activate = createApplier(activateDeps([producer()]));
      const started = activate(
        producerWorld({ collect: 100, unitCapacity: 5, unitsInside: 0, collectType: 'w' }),
        { name: 'activate', args: ['7', period] },
      );
      assert.equal(started.applied, true);
      const collect = createApplier(
        activateDeps([producer()], ACTIVATE_START + minutes[index]! * 60),
      );
      const due = collect(started.world, { name: 'collect', args: ['7'] });
      assert.equal(due.applied, true, `period ${period} was not due at its minutes`);
      assert.equal(due.world.resources['w'], expected[index], `period ${period} paid wrong`);
    }
  });

  it('refuses a collection before the chosen period has elapsed', () => {
    const activate = createApplier(activateDeps([producer()]));
    const started = activate(
      producerWorld({ collect: 100, unitCapacity: 5, collectType: 'w' }),
      { name: 'activate', args: ['7', 1] },
    );
    const early = createApplier(activateDeps([producer()], ACTIVATE_START + 5 * 60 - 1));
    const outcome = early(started.world, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-due');
    assert.equal(outcome.world.resources['w'], 0);
  });

  it('refuses invalid periods and leaves the world unchanged', () => {
    for (const bad of [0, 5, -1, 1.5, '2', Number.NaN]) {
      const applier = createApplier(activateDeps([producer()]));
      const world = producerWorld({ collect: 100, unitCapacity: 5, collectType: 'w' });
      const before = JSON.stringify(world);
      const outcome = applier(world, { name: 'activate', args: ['7', bad] });
      assert.equal(outcome.applied, false, `period ${String(bad)} was accepted`);
      assert.equal(outcome.refused, 'bad-argument');
      assert.equal(JSON.stringify(outcome.world), before, `period ${String(bad)} wrote state`);
    }
  });

  it('refuses an unknown building, an unknown item, a unit and an ineligible building', () => {
    const world = producerWorld({});
    const outcomes = [
      createApplier(activateDeps([producer()]))(world, {
        name: 'activate', args: ['999', 1],
      }),
      createApplier(activateDeps([producer()]))(producerWorld({}, 0, 999), {
        name: 'activate', args: ['7', 1],
      }),
      createApplier(activateDeps([producer({ type: 'u' })]))(world, {
        name: 'activate', args: ['7', 1],
      }),
      createApplier(activateDeps([producer({ multiCollectable: false })]))(world, {
        name: 'activate', args: ['7', 1],
      }),
    ];
    const refusals = [
      'unknown-building',
      'unknown-item',
      'not-a-building',
      'not-multi-collectable',
    ];
    outcomes.forEach((outcome, index) => {
      assert.equal(outcome.applied, false);
      assert.equal(outcome.refused, refusals[index]);
    });
  });

  it('refuses an over-capacity building', () => {
    const applier = createApplier(activateDeps([producer()]));
    const world = producerWorld({
      collect: 100,
      unitCapacity: 2,
      unitsInside: 3,
      collectType: 'w',
    });
    const before = JSON.stringify(world);
    const outcome = applier(world, { name: 'activate', args: ['7', 4] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'over-capacity');
    assert.equal(JSON.stringify(outcome.world), before);
  });

  it('refuses a building whose construction is still in progress', () => {
    const applier = createApplier(activateDeps([producer()]));
    const world = producerWorld({ collect: 100, unitCapacity: 5 }, ACTIVATE_START - 10);
    const outcome = applier(world, { name: 'activate', args: ['7', 4] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'under-construction');
    assert.equal(producerAttrs(outcome.world)['cp'], undefined);
  });

  it('does not restamp on a duplicate, but does when the period changes', () => {
    const activate = createApplier(activateDeps([producer()]));
    const started = activate(
      producerWorld({ collect: 100, unitCapacity: 5, collectType: 'w' }),
      { name: 'activate', args: ['7', 3] },
    );
    assert.equal(producerAttrs(started.world)['lastAccruedAt'], ACTIVATE_START);

    const later = createApplier(activateDeps([producer()], ACTIVATE_START + 30));
    const duplicate = later(started.world, { name: 'activate', args: ['7', 3] });
    assert.equal(duplicate.applied, true, 'a repeat of the same period was refused');
    assert.equal(producerAttrs(duplicate.world)['lastAccruedAt'], ACTIVATE_START);

    const switched = later(duplicate.world, { name: 'activate', args: ['7', 4] });
    assert.equal(switched.applied, true);
    assert.equal(producerAttrs(switched.world)['cp'], 4);
    assert.equal(producerAttrs(switched.world)['lastAccruedAt'], ACTIVATE_START + 30);
  });

  it('restamps a fresh building that has never accrued, even on the same period', () => {
    const activate = createApplier(activateDeps([producer()]));
    const world = producerWorld({ cp: 4, lastAccruedAt: 0, collect: 100, unitCapacity: 5 });
    const outcome = activate(world, { name: 'activate', args: ['7', 4] });
    assert.equal(outcome.applied, true);
    assert.equal(producerAttrs(outcome.world)['lastAccruedAt'], ACTIVATE_START);
  });

  it('survives a serialised world and a rebuilt applier', () => {
    const activate = createApplier(activateDeps([producer()]));
    const started = activate(
      producerWorld({ collect: 100, unitCapacity: 5, unitsInside: 0, collectType: 'w' }),
      { name: 'activate', args: ['7', 4] },
    );
    const restored = JSON.parse(JSON.stringify(started.world)) as ShimWorld;
    const collect = createApplier(
      activateDeps([producer()], ACTIVATE_START + 480 * 60),
    );
    const outcome = collect(restored, { name: 'collect', args: ['7'] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['w'], 300);
    assert.equal(producerAttrs(outcome.world)['cp'], 4);
  });
});

describe('completing a goal', () => {
  it('refuses a goal the server has not completed', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'complete_goal', args: [30] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-completed');
    assert.equal(outcome.world.resources['g'], 0);
  });

  it('grants a goal the server has completed, exactly once', () => {
    const applier = createApplier(deps());
    // A goal with a single step, completed by the server's own state.
    const goal = GOALS.find((g) => g.steps === 1) ?? GOALS[0]!;
    const world = worldWithBuilding({});
    const state = createGoalState();
    // The state is readonly, so the server's own state is built as a copy.
    world.save.privateState[GOAL_STATE_KEY] = {
      ...state,
      completed: { ...state.completed, [goal.id]: true },
    };

    const first = applier(world, { name: 'complete_goal', args: [goal.id] });
    assert.equal(first.applied, true);
    assert.equal(first.world.resources['g'], 10);

    // The replay is refused: the award is once-only.
    const second = applier(first.world, { name: 'complete_goal', args: [goal.id] });
    assert.equal(second.applied, false);
    assert.equal(second.refused, 'already-awarded');
    assert.equal(second.world.resources['g'], 10);
  });

  it('refuses a goal that does not exist', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'complete_goal', args: [999999] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'unknown-goal');
  });

  it('has a real goal to complete', () => {
    const goal = getGoalDefinition(30);
    assert.ok(goal);
  });
});

describe('the daily bonus', () => {
  it('grants the server own bonus for the day', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    // The last bonus was yesterday.
    world.save.privateState['timestampLastBonus'] = NOW - 86_400;
    world.save.privateState['bonusNextId'] = 0;

    const outcome = applier(world, { name: 'win_daily_bonus', args: [1001, 0] });
    assert.equal(outcome.applied, true);
    // Day 1 of the cycle is 100 gold.
    assert.equal(outcome.world.resources['g'], 100);
    assert.equal(outcome.world.save.privateState['bonusNextId'], 1);
    assert.equal(outcome.world.save.privateState['timestampLastBonus'], NOW);
  });

  it('refuses a replay on the same day', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    world.save.privateState['timestampLastBonus'] = NOW;

    const outcome = applier(world, { name: 'win_daily_bonus', args: [1001, 0] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-ready');
    assert.equal(outcome.world.resources['g'], 0);
  });

  it('ignores the bonus index the client claims', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    world.save.privateState['timestampLastBonus'] = NOW - 86_400;
    world.save.privateState['bonusNextId'] = 0;

    // The client claims day 5, which would be a hero.
    const outcome = applier(world, { name: 'win_daily_bonus', args: [1042, 4] });
    assert.equal(outcome.applied, true);
    // The server's own day 1 is 100 gold, not a hero.
    assert.equal(outcome.world.resources['g'], 100);
    assert.equal(outcome.world.save.privateState['bonusNextId'], 1);
  });

  it('advances the cycle and wraps it', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    world.save.privateState['bonusNextId'] = 5;
    world.save.privateState['timestampLastBonus'] = NOW - 86_400;
    const outcome = applier(world, { name: 'win_daily_bonus', args: [] });
    assert.equal(outcome.world.save.privateState['bonusNextId'], 1);
  });
});

describe('the commands whose cost the server computes', () => {
  it('charges the reactivation price, not the one the client declares', () => {
    const applier = createApplier(
      deps({
        items: new Map([[30, item({ costs: { c: 20 } })]]),
        reactivateWonderDiscount: 0.5,
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(1000) });
    const outcome = applier(world, { name: 'reset_collect', args: ['7'] });
    assert.equal(outcome.applied, true);
    // 20 cash, halved by the discount: 10.
    assert.equal(outcome.world.resources['c'], 1000 - 10);
  });

  it('refuses a reactivation the player cannot afford', () => {
    const applier = createApplier(
      deps({
        items: new Map([[30, item({ costs: { c: 20 } })]]),
        reactivateWonderDiscount: 0.5,
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(1) });
    const outcome = applier(world, { name: 'reset_collect', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'insufficient-resources');
    assert.equal(outcome.world.resources['c'], 1);
  });

  it('charges the speed-up price for hurrying a build up', () => {
    const applier = createApplier(
      deps({
        items: new Map([[30, item({ buildTime: 600 })]]),
        speedup: { minRemainingMs: 10_000, cost: 2 },
      }),
    );
    // The build started now, so ten minutes remain: a speed-up is allowed.
    const world = worldWithBuilding({}, { resources: wallet(1000) });
    const tuple = (world.save.maps[0] as Record<string, unknown>)[
      'items'
    ] as Record<string, unknown[]>;
    tuple['7']![3] = NOW;
    const outcome = applier(world, { name: 'finish_building', args: ['7', -1] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 1000 - 2);
  });

  it('refuses a speed-up when the build is nearly done', () => {
    const applier = createApplier(
      deps({
        items: new Map([[30, item({ buildTime: 600 })]]),
        speedup: { minRemainingMs: 10_000, cost: 2 },
      }),
    );
    const world = worldWithBuilding({});
    // The build started five minutes ago, so five minutes remain - which is
    // more than the minimum, so this one IS allowed. Start it later.
    const late = worldWithBuilding({}, { resources: wallet(1000) });
    const tuple = (late.save.maps[0] as Record<string, unknown>)['items'] as Record<string, unknown[]>;
    tuple['7']![3] = NOW - 599;
    const outcome = applier(late, { name: 'finish_building', args: ['7', -1] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'too-late-to-speed-up');
    assert.equal(outcome.world.resources['c'], 1000);
  });
});

describe('expanding the town', () => {
  // The content's expansion price table: the first four tiles are free, the
  // fifth costs 2500 gold + 5 cash, the sixth 5000 + 8. The neighbours and
  // inventory columns exist in the content but their inputs are not
  // server-owned here, so the applier must not enforce them.
  const prices = [
    { coins: 0, cash: 0, neighbors: 0, inventory_qte: 0 },
    { coins: 0, cash: 0, neighbors: 0, inventory_qte: 0 },
    { coins: 0, cash: 0, neighbors: 0, inventory_qte: 0 },
    { coins: 0, cash: 0, neighbors: 0, inventory_qte: 0 },
    { coins: 2500, cash: 5, neighbors: 1, inventory_qte: 1 },
    { coins: 5000, cash: 8, neighbors: 2, inventory_qte: 2 },
  ];
  const expansionDeps = (over: Partial<ApplierDeps> = {}): ApplierDeps =>
    deps({ expansionPrices: prices, ...over });
  const rich = (): ShimWorld['resources'] => purse({ g: 100_000, c: 100_000 });

  /** A save with the given owned tiles; omitting them models an older save. */
  function expansionWorld(
    expansions?: number[],
    resources: ShimWorld['resources'] = rich(),
  ): ShimWorld {
    const map: Record<string, unknown> = { id: 0, items: {}, store: {} };
    if (expansions !== undefined) map['expansions'] = [...expansions];
    return {
      save: { playerInfo: {}, maps: [map], privateState: {} },
      resources,
      nextCommandNumber: 1,
    };
  }
  const owned = (world: ShimWorld): unknown =>
    (world.save.maps[0] as Record<string, unknown>)['expansions'];

  it('charges the content price at the owned ordinal, ignoring declared values', () => {
    const applier = createApplier(expansionDeps());
    // Four tiles are already owned, so this is the fifth: 2500g + 5c. The
    // client's price and type arguments are claims and change nothing.
    const outcome = applier(expansionWorld([35, 36, 45, 46]), {
      name: 'expand',
      args: [47, 1, 'free'],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 100_000 - 2500);
    assert.equal(outcome.world.resources['c'], 100_000 - 5);
    assert.deepEqual(owned(outcome.world), [35, 36, 45, 46, 47]);
  });

  it('prices the next tile by the owned count, not by the tile id', () => {
    const applier = createApplier(expansionDeps());
    const first = applier(expansionWorld([35, 36, 45, 46]), {
      name: 'expand',
      args: [999],
    });
    assert.equal(first.applied, true);
    assert.equal(first.world.resources['g'], 100_000 - 2500);
    assert.equal(first.world.resources['c'], 100_000 - 5);

    // Now five tiles are owned: the next is ordinal 5, whatever its tile id.
    const second = applier(first.world, { name: 'expand', args: [123] });
    assert.equal(second.applied, true);
    assert.equal(second.world.resources['g'], 100_000 - 2500 - 5000);
    assert.equal(second.world.resources['c'], 100_000 - 5 - 8);
    assert.deepEqual(owned(second.world), [35, 36, 45, 46, 999, 123]);
  });

  it('refuses a tile id that is not a positive integer', () => {
    const applier = createApplier(expansionDeps());
    for (const bad of [0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, 'abc', undefined]) {
      const outcome = applier(expansionWorld([35, 36, 45, 46]), {
        name: 'expand',
        args: [bad],
      });
      assert.equal(outcome.applied, false, `tile ${String(bad)}`);
      assert.equal(outcome.refused, 'bad-argument', `tile ${String(bad)}`);
      assert.equal(outcome.world.resources['g'], 100_000);
      assert.deepEqual(owned(outcome.world), [35, 36, 45, 46]);
    }
  });

  it('refuses a tile that is already owned', () => {
    const applier = createApplier(expansionDeps());
    const outcome = applier(expansionWorld([35, 36, 45, 46]), {
      name: 'expand',
      args: [36],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'already-owned');
    assert.equal(outcome.world.resources['g'], 100_000);
    assert.deepEqual(owned(outcome.world), [35, 36, 45, 46]);
  });

  it('refuses an expansion past the end of the content table', () => {
    const applier = createApplier(expansionDeps());
    // Six owned tiles; ordinal 6 is past the six-row table.
    const outcome = applier(expansionWorld([35, 36, 45, 46, 47, 48]), {
      name: 'expand',
      args: [49],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'expansion-limit');
    assert.equal(outcome.world.resources['g'], 100_000);
    assert.deepEqual(owned(outcome.world), [35, 36, 45, 46, 47, 48]);
  });

  it('refuses an unaffordable expansion without touching the wallet or the save', () => {
    const applier = createApplier(expansionDeps());
    const outcome = applier(
      expansionWorld([35, 36, 45, 46], purse({ g: 2499, c: 100 })),
      { name: 'expand', args: [47] },
    );
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'insufficient-resources');
    assert.equal(outcome.world.resources['g'], 2499);
    assert.equal(outcome.world.resources['c'], 100);
    assert.deepEqual(owned(outcome.world), [35, 36, 45, 46]);
  });

  it('defaults to no owned tiles when the save has no expansions field', () => {
    const applier = createApplier(expansionDeps());
    const outcome = applier(expansionWorld(), { name: 'expand', args: [47] });
    assert.equal(outcome.applied, true);
    // Ordinal 0 is free in the content table; no charge, no crash.
    assert.equal(outcome.world.resources['g'], 100_000);
    assert.equal(outcome.world.resources['c'], 100_000);
    assert.deepEqual(owned(outcome.world), [47]);
  });

  it('refuses a replayed tile without charging twice or appending twice', () => {
    const applier = createApplier(expansionDeps());
    const first = applier(expansionWorld([35, 36, 45, 46]), {
      name: 'expand',
      args: [47],
    });
    assert.equal(first.applied, true);
    const goldAfterFirst = first.world.resources['g'];
    const replay = applier(first.world, { name: 'expand', args: [47] });
    assert.equal(replay.applied, false);
    assert.equal(replay.refused, 'already-owned');
    assert.equal(replay.world.resources['g'], goldAfterFirst);
    assert.deepEqual(owned(replay.world), [35, 36, 45, 46, 47]);
  });

  it('stays payable after the world is serialized and restored', () => {
    const applier = createApplier(expansionDeps());
    const first = applier(expansionWorld([35, 36, 45, 46]), {
      name: 'expand',
      args: [47],
    });
    const restored = JSON.parse(JSON.stringify(first.world)) as ShimWorld;
    const second = applier(restored, { name: 'expand', args: [48] });
    assert.equal(second.applied, true);
    assert.equal(second.world.resources['g'], 100_000 - 2500 - 5000);
    assert.equal(second.world.resources['c'], 100_000 - 5 - 8);
    assert.deepEqual(owned(second.world), [35, 36, 45, 46, 47, 48]);
  });
});

describe('the training queue', () => {
  const academy = () => item({ id: 30, trainsIds: [1007], trainingTime: 60 });
  const soldier = () =>
    item({ id: 1007, name: 'Soldier', costs: { g: 30, s: 60 }, trainingTime: 60 });

  it('starts training a unit and charges for it', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, academy()],
          [1007, soldier()],
        ]),
      }),
    );
    const world = worldWithBuilding({}, { resources: purse({ g: 1000, s: 1000 }) });
    const outcome = applier(world, { name: 'push_queue_unit', args: ['7'] });
    assert.equal(outcome.applied, true);
    // The Soldier costs 30 gold and 60 steel.
    assert.equal(outcome.world.resources['g'], 1000 - 30);
    assert.equal(outcome.world.resources['s'], 1000 - 60);
    // The queue holds one unit, and it started now.
    const attrs = mapItems(outcome.world.save.maps[0] as Record<string, unknown>)[
      '7'
    ]![6] as Record<string, unknown>;
    assert.equal(attrs['nu'], 1);
    assert.equal(attrs['ts'], NOW);
    assert.equal(attrs['ui'], 1007);
  });

  it('refuses a training the player cannot afford', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, academy()],
          [1007, soldier()],
        ]),
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'push_queue_unit', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'insufficient-resources');
  });

  it('refuses a building that trains nothing', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'push_queue_unit', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'nothing-to-train');
  });

  it('trains the unit the client names', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, academy()],
          [1007, soldier()],
          [1008, item({ id: 1008, name: 'Worker', costs: { g: 10 }, trainingTime: 30 })],
        ]),
      }),
    );
    const world = worldWithBuilding({}, { resources: purse({ g: 1000, s: 1000 }) });
    const outcome = applier(world, { name: 'push_queue_unit2', args: ['7', 1008] });
    assert.equal(outcome.applied, true);
    const attrs = mapItems(outcome.world.save.maps[0] as Record<string, unknown>)[
      '7'
    ]![6] as Record<string, unknown>;
    assert.equal(attrs['ui'], 1008);
    assert.equal(outcome.world.resources['g'], 1000 - 10);
  });

  it('refuses to pop a unit that is still training', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, academy()],
          [1007, soldier()],
        ]),
      }),
    );
    const world = worldWithBuilding({}, { resources: purse({ g: 1000, s: 1000 }) });
    const queued = applier(world, { name: 'push_queue_unit', args: ['7'] });
    const popped = applier(queued.world, { name: 'pop_queue_unit', args: ['7'] });
    assert.equal(popped.applied, false);
    assert.equal(popped.refused, 'still-training');
  });

  it('pops a unit that has finished training', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, academy()],
          [1007, soldier()],
        ]),
        now: () => NOW + 120,
      }),
    );
    const world = worldWithBuilding({}, { resources: purse({ g: 1000, s: 1000 }) });
    const queued = applier(world, { name: 'push_queue_unit', args: ['7'] });
    // Two minutes later the unit is done.
    const later = { ...queued.world };
    const attrs = mapItems(later.save.maps[0] as Record<string, unknown>)[
      '7'
    ]![6] as Record<string, unknown>;
    attrs['ts'] = NOW - 120;
    const popped = applier(later, { name: 'pop_queue_unit', args: ['7'] });
    assert.equal(popped.applied, true);
    const after = mapItems(popped.world.save.maps[0] as Record<string, unknown>)[
      '7'
    ]![6] as Record<string, unknown>;
    assert.equal(after['nu'], undefined);
    assert.equal(after['ts'], undefined);
  });

  it('keeps the rest of the queue waiting', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, academy()],
          [1007, soldier()],
        ]),
      }),
    );
    const world = worldWithBuilding({}, { resources: purse({ g: 1000, s: 1000 }) });
    const first = applier(world, { name: 'push_queue_unit', args: ['7'] });
    const second = applier(first.world, { name: 'push_queue_unit', args: ['7'] });
    const attrs = mapItems(second.world.save.maps[0] as Record<string, unknown>)[
      '7'
    ]![6] as Record<string, unknown>;
    assert.equal(attrs['nu'], 2);
    // The first unit is still the one training.
    assert.equal(attrs['ts'], NOW);
  });

  it('refuses to pop an empty queue', () => {
    const applier = createApplier(deps({ items: new Map([[30, academy()]]) }));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'pop_queue_unit', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'queue-empty');
  });
});

describe('levelling the player up', () => {
  const levels = [
    { index: 0, exp_required: 0, reward_amount: 50, reward_type: 's' },
    { index: 1, exp_required: 40, reward_amount: 250, reward_type: 'w' },
    { index: 2, exp_required: 60, reward_amount: 250, reward_type: 's' },
  ];

  it('raises the level and grants the reward', () => {
    const applier = createApplier(deps({ levels }));
    const world = worldWithBuilding({});
    const map = world.save.maps[0] as Record<string, unknown>;
    map['level'] = 0;
    map['xp'] = 100;
    const outcome = applier(world, { name: 'level_up', args: [1] });
    assert.equal(outcome.applied, true);
    assert.equal(map['level'], 1);
    // The reward for level 1 is 250 wood.
    assert.equal(outcome.world.resources['w'], 250);
  });

  it('refuses a level the player has not the XP for', () => {
    const applier = createApplier(deps({ levels }));
    const world = worldWithBuilding({});
    const map = world.save.maps[0] as Record<string, unknown>;
    map['level'] = 0;
    map['xp'] = 10;
    const outcome = applier(world, { name: 'level_up', args: [1] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-enough-xp');
    assert.equal(map['level'], 0);
  });

  it('refuses a level that is not the next one', () => {
    const applier = createApplier(deps({ levels }));
    const world = worldWithBuilding({});
    const map = world.save.maps[0] as Record<string, unknown>;
    map['level'] = 0;
    map['xp'] = 1000;
    const outcome = applier(world, { name: 'level_up', args: [2] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-the-next-level');
  });

  it('refuses a level that does not exist', () => {
    const applier = createApplier(deps({ levels }));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'level_up', args: [99] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-such-level');
  });
});

describe('magic and tech', () => {
  const MAGIC: NonNullable<ApplierDeps['magic']> = {
    spells: new Map([
      [
        1,
        {
          id: 1,
          name: 'AirStrike',
          description: 'Aircraft bomb the zone.',
          mana: 8,
          level: 38,
          gold: 30_000,
          cash: 50,
          area: [5, 7, 9],
          target: 2,
          imgName: 'tech_airstrike',
        },
      ],
    ]),
    globals: {
      MANA_PER_PURCHASE: 5,
      COST_MANA_CASH: 1,
      COST_MANA_GOLD: 10_000,
      NUM_SPELL_USES_LVL2: 25,
      NUM_SPELL_USES_LVL3: 50,
      MANA_REWARD_PER_LEVEL: 2,
    },
  };

  /** A world at the given level, with the price already settled by the cost table. */
  function magicWorld(level: number): ShimWorld {
    const world = worldWithBuilding({}, { resources: purse({ m: 0 }) });
    const map = world.save.maps[0] as Record<string, unknown>;
    map['level'] = level;
    return world;
  }

  it('learns a spell with gold and grants its mana cost', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = magicWorld(38);
    const outcome = applier(world, { name: 'buy_magic', args: [1, 'g'] });
    assert.equal(outcome.applied, true);
    assert.deepEqual(outcome.world.save.privateState['magics'], { '1': 0 });
    assert.equal(outcome.world.resources['m'], 8);
    assert.equal(outcome.world.save.privateState['mana'], 8);
  });

  it('lets cash buy a spell below its unlock level', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = magicWorld(1);
    const outcome = applier(world, { name: 'buy_magic', args: [1, 'c'] });
    assert.equal(outcome.applied, true);
    assert.deepEqual(outcome.world.save.privateState['magics'], { '1': 0 });
    assert.equal(outcome.world.resources['m'], 8);
  });

  it('does not let gold buy a spell below its unlock level', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = magicWorld(37);
    const outcome = applier(world, { name: 'buy_magic', args: [1, 'g'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'level');
    assert.equal(outcome.world.save.privateState['magics'], undefined);
    assert.equal(outcome.world.resources['m'], 0);
  });

  it('refuses a spell that is already learned', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = magicWorld(38);
    world.save.privateState['magics'] = { '1': 3 };
    const outcome = applier(world, { name: 'buy_magic', args: [1, 'g'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'already-learned');
    assert.deepEqual(outcome.world.save.privateState['magics'], { '1': 3 });
    assert.equal(outcome.world.resources['m'], 0);
  });

  it('refuses an unknown spell, a bad payment resource and a missing spell id', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    assert.equal(
      applier(magicWorld(38), { name: 'buy_magic', args: [2, 'g'] }).refused,
      'unknown-spell',
    );
    assert.equal(
      applier(magicWorld(38), { name: 'buy_magic', args: [1, 'x'] }).refused,
      'bad-payment',
    );
    assert.equal(
      applier(magicWorld(38), { name: 'buy_magic', args: ['x', 'g'] }).refused,
      'bad-argument',
    );
  });

  it('buys the fixed mana pack and updates the client copy', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = worldWithBuilding({}, { resources: purse({ m: 10 }) });
    const outcome = applier(world, { name: 'buy_mana_new', args: [5, 'c'] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['m'], 15);
    assert.equal(outcome.world.save.privateState['mana'], 15);
  });

  it('refuses a mana amount that is not the fixed pack', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'buy_mana_new', args: [10, 'c'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'unknown-mana-pack');
    assert.equal(outcome.world.resources['m'], 0);
  });

  it('uses a learned spell and raises its counter', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = worldWithBuilding({}, { resources: purse({ m: 0 }) });
    world.save.privateState['magics'] = { '1': 24 };
    const outcome = applier(world, { name: 'use_magic', args: [1] });
    assert.equal(outcome.applied, true);
    assert.deepEqual(outcome.world.save.privateState['magics'], { '1': 25 });
    assert.equal(outcome.world.save.privateState['mana'], 0);
  });

  it('refuses a spell the player has not learned', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = worldWithBuilding({}, { resources: purse({ m: 0 }) });
    const outcome = applier(world, { name: 'use_magic', args: [1] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-learned');
    assert.equal(outcome.world.save.privateState['magics'], undefined);
  });

  it('stops the counter at the third spell level', () => {
    const applier = createApplier(deps({ magic: MAGIC }));
    const world = worldWithBuilding({}, { resources: purse({ m: 0 }) });
    world.save.privateState['magics'] = { '1': 50 };
    const outcome = applier(world, { name: 'use_magic', args: [1] });
    assert.equal(outcome.applied, true);
    assert.deepEqual(outcome.world.save.privateState['magics'], { '1': 50 });
  });

  it('grants dark matter when the player levels up', () => {
    const levels = [
      { index: 0, exp_required: 0, reward_amount: 50, reward_type: 's' },
      { index: 1, exp_required: 40, reward_amount: 250, reward_type: 'w' },
    ];
    const applier = createApplier(deps({ levels, magic: MAGIC }));
    const world = magicWorld(0);
    const map = world.save.maps[0] as Record<string, unknown>;
    map['xp'] = 100;
    const outcome = applier(world, { name: 'level_up', args: [1] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['m'], 2);
    assert.equal(outcome.world.save.privateState['mana'], 2);
  });
});

describe('upgrading a building', () => {
  it('replaces it with the next tier and charges the difference', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, item({ id: 30, costs: { w: 125 }, upgradesTo: 41 })],
          [41, item({ id: 41, costs: { w: 300 }, width: 2, height: 2 })],
        ]),
      }),
    );
    const world = worldWithBuilding({}, { resources: purse({ w: 1000 }) });
    const outcome = applier(world, { name: 'upgrade', args: ['7'] });
    assert.equal(outcome.applied, true);
    // 300 wood for the new tier, less a twentieth of the old one's 125.
    assert.equal(outcome.world.resources['w'], 1000 - 300 + Math.floor(125 / 20));
    const tuple = mapItems(outcome.world.save.maps[0] as Record<string, unknown>)['7']!;
    assert.equal(tuple[0], 41);
  });

  it('refuses a building with no next tier', () => {
    const applier = createApplier(deps({ items: new Map([[30, item({ id: 30 })]]) }));
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'upgrade', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-upgrade');
  });

  it('refuses an upgrade the player cannot afford', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, item({ id: 30, costs: { w: 125 }, upgradesTo: 41 })],
          [41, item({ id: 41, costs: { w: 300 } })],
        ]),
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'upgrade', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'insufficient-resources');
  });

  it('refuses an upgrade that would not fit', () => {
    const applier = createApplier(
      deps({
        items: new Map([
          [30, item({ id: 30, upgradesTo: 41 })],
          [41, item({ id: 41, width: 3, height: 3 })],
        ]),
      }),
    );
    // The building to upgrade is at (0, 0) and is one tile square. A
    // three-tile-square building already stands at (2, 2), so the upgrade
    // would overlap it. The old building's own tiles are free for its own
    // upgrade, but the neighbour's are not.
    const world = worldWithBuilding({ width: 1, height: 1 });
    const items = mapItems(world.save.maps[0] as Record<string, unknown>);
    items['9'] = [30, 2, 2, 0, 0, [], { width: 1, height: 1 }, 1];
    const outcome = applier(world, { name: 'upgrade', args: ['7'] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-free-tile');
  });
});

describe('the weekly bonus', () => {
  // 2026-10-19 is a Monday.
  const MONDAY = Date.UTC(2026, 9, 19) / 1000;
  const TUESDAY = MONDAY + 86400;
  const NEXT_MONDAY = MONDAY + 7 * 86400;

  const RULES = {
    rewards: [
      { type: 'g', value: 1000 },
      { type: 'g', value: 2000 },
      { type: 'g', value: 3000 },
    ],
  };

  it('is granted on a Monday', () => {
    const applier = createApplier(deps({ mondayBonus: RULES, now: () => MONDAY }));
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'weekly_reward', args: [] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 1000);
    // The index advances, so the next week is a different reward.
    assert.equal(outcome.world.save.privateState['weeklyRewardIndex'], 1);
  });

  it('is refused on any day but Monday', () => {
    const applier = createApplier(deps({ mondayBonus: RULES, now: () => TUESDAY }));
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'weekly_reward', args: [] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.world.resources['g'], 0);
  });

  it('is granted only once a week', () => {
    const applier = createApplier(deps({ mondayBonus: RULES, now: () => MONDAY }));
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const first = applier(world, { name: 'weekly_reward', args: [] });
    assert.equal(first.applied, true);
    // The same Monday, again.
    const second = applier(first.world, { name: 'weekly_reward', args: [] });
    assert.equal(second.applied, false);
    assert.equal(second.world.resources['g'], 1000);
  });

  it('is granted again the next Monday', () => {
    const applier = createApplier(deps({ mondayBonus: RULES, now: () => MONDAY }));
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const first = applier(world, { name: 'weekly_reward', args: [] });
    // The next week: the applier's clock has moved on.
    const next = createApplier(deps({ mondayBonus: RULES, now: () => NEXT_MONDAY }));
    const second = next(first.world, { name: 'weekly_reward', args: [] });
    assert.equal(second.applied, true);
    // The second week's reward: the cycle's next entry.
    assert.equal(second.world.resources['g'], 1000 + 2000);
  });

  it('uses the player local day, not UTC', () => {
    // 2026-10-19 23:30 UTC is already Tuesday in Auckland, and still
    // Monday in London. The client's week day is the LOCAL one.
    const lateMonday = Date.UTC(2026, 9, 19, 23, 30) / 1000;
    const london = createApplier(deps({ mondayBonus: RULES, now: () => lateMonday, tzOffsetHours: 0 }));
    const auckland = createApplier(
      deps({ mondayBonus: RULES, now: () => lateMonday, tzOffsetHours: 12 }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    assert.equal(london(world, { name: 'weekly_reward', args: [] }).applied, true);
    assert.equal(auckland(world, { name: 'weekly_reward', args: [] }).applied, false);
  });
});

describe('the alliance daily bonus', () => {
  const MONDAY = Date.UTC(2026, 9, 19) / 1000;
  const RULES = {
    rewards: [
      { members: 0, type: 'g', value: 150 },
      { members: 5, type: 'g', value: 1500 },
      { members: 25, type: 'g', value: 5000 },
      { members: 45, type: 'c', value: 1 },
    ],
  };

  it('grants the tier the member count qualifies for', () => {
    const applier = createApplier(
      deps({ allianceBonus: RULES, allianceMemberCount: 6, now: () => MONDAY }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'win_alliance_daily_bonus', args: [] });
    assert.equal(outcome.applied, true);
    // Six members qualifies for the five-member tier, and not the 25 one.
    assert.equal(outcome.world.resources['g'], 1500);
  });

  it('grants the cash tier at the top', () => {
    const applier = createApplier(
      deps({ allianceBonus: RULES, allianceMemberCount: 50, now: () => MONDAY }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'win_alliance_daily_bonus', args: [] });
    assert.equal(outcome.world.resources['c'], 1);
    assert.equal(outcome.world.resources['g'], 0);
  });

  it('is granted only once a day', () => {
    const applier = createApplier(
      deps({ allianceBonus: RULES, allianceMemberCount: 6, now: () => MONDAY }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const first = applier(world, { name: 'win_alliance_daily_bonus', args: [] });
    assert.equal(first.applied, true);
    // The upstream credits the bonus but never sets the timer, so the
    // upstream pays it over and over. The server does not.
    const second = applier(first.world, { name: 'win_alliance_daily_bonus', args: [] });
    assert.equal(second.applied, false);
    assert.equal(second.world.resources['g'], 1500);
  });

  it('is granted again the next day', () => {
    const applier = createApplier(
      deps({ allianceBonus: RULES, allianceMemberCount: 6, now: () => MONDAY }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const first = applier(world, { name: 'win_alliance_daily_bonus', args: [] });
    const next = createApplier(
      deps({ allianceBonus: RULES, allianceMemberCount: 6, now: () => MONDAY + 86400 }),
    );
    const second = next(first.world, { name: 'win_alliance_daily_bonus', args: [] });
    assert.equal(second.applied, true);
    assert.equal(second.world.resources['g'], 3000);
  });
});

describe('the server own answer to a finished battle', () => {
  it('refuses the claim when there is no server simulation', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    const outcome = applier(world, {
      name: 'end_attack',
      args: [JSON.stringify({ win: 1, resources: { g: 100000 } }), '0'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-implemented');
    assert.equal(outcome.world.resources['g'], 0);
  });

  it('grants the loot the server simulation says, not the client claim', () => {
    const applier = createApplier(
      deps({
        resolveBattle: () => ({
          won: true,
          victimTownHallGold: 1000,
          victimLevel: 12,
          attackerLevel: 40,
          conquest: false,
          xp: 50,
        }),
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    // The client claims a million gold and a win.
    const outcome = applier(world, {
      name: 'end_attack',
      args: [JSON.stringify({ win: 1, resources: { g: 1000000, x: 999 } }), '0'],
    });
    assert.equal(outcome.applied, true);
    // The server's own loot: 15 to 35 per cent of 1000, capped at the
    // level-40 band of 10000, so between 150 and 350.
    assert.ok(outcome.world.resources['g']! >= 150, `gold was ${outcome.world.resources['g']}`);
    assert.ok(outcome.world.resources['g']! <= 350, `gold was ${outcome.world.resources['g']}`);
    // The XP is the server's own, not the client's.
    assert.equal(outcome.world.resources['x'], 50);
  });

  it('grants nothing when the server simulation says the attack was lost', () => {
    const applier = createApplier(
      deps({
        resolveBattle: () => ({
          won: false,
          victimTownHallGold: 1000,
          victimLevel: 12,
          attackerLevel: 40,
          conquest: false,
          xp: 0,
        }),
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, {
      name: 'end_attack',
      args: [JSON.stringify({ win: 1, resources: { g: 1000000 } }), '0'],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 0);
    assert.equal(outcome.world.resources['x'], 0);
    assert.equal(outcome.world.save.privateState['lastAssaultWon'], false);
  });

  it('gives a conquest its fixed gold', () => {
    const applier = createApplier(
      deps({
        resolveBattle: () => ({
          won: true,
          victimTownHallGold: 0,
          victimLevel: 12,
          attackerLevel: 40,
          conquest: true,
          xp: 5,
        }),
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'end_attack', args: ['{}'] });
    // The victim's level times 100.
    assert.equal(outcome.world.resources['g'], 1200);
  });

  it('gives a win with no loot a flat 25 gold', () => {
    const applier = createApplier(
      deps({
        resolveBattle: () => ({
          won: true,
          victimTownHallGold: 0,
          victimLevel: 12,
          attackerLevel: 40,
          conquest: false,
          xp: 1,
        }),
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'end_attack', args: ['{}'] });
    assert.equal(outcome.world.resources['g'], 25);
  });

  it('survives a malformed claim', () => {
    const applier = createApplier(
      deps({
        resolveBattle: () => ({
          won: true,
          victimTownHallGold: 100,
          victimLevel: 12,
          attackerLevel: 10,
          conquest: false,
          xp: 1,
        }),
      }),
    );
    const world = worldWithBuilding({}, { resources: wallet(0) });
    const outcome = applier(world, { name: 'end_attack', args: ['not json'] });
    assert.equal(outcome.applied, true);
  });
});

describe('the claims the server does not honour', () => {
  it('refuses a claimed end_attack', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    const outcome = applier(world, {
      name: 'end_attack',
      args: [JSON.stringify({ win: true, resources: { g: 100000 } }), '0'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-implemented');
    assert.equal(outcome.world.resources['g'], 0);
  });

  it('refuses a claimed end_quest with no server-recorded kills', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'end_quest', args: [100000001, true] });
    assert.equal(outcome.applied, false);
    // The claimed win is never read: there is no active server quest to resolve.
    assert.equal(outcome.refused, 'no-active-quest');
    assert.equal(outcome.world.resources['g'], 0);
  });
});

/** A darts schedule; the rules engine picks the game live at NOW. */
const DARTS_GAMES = [
  {
    id: 1,
    start_date: '2012-03-02 23:00:00',
    items: [101, 102, 103, 104, 105, 106],
    extra_item: 997,
  },
  {
    id: 2,
    start_date: '2012-03-09 23:00:00',
    items: [201, 202, 203, 204, 205, 206],
    extra_item: 998,
  },
];

/** The market rules the content ships. */
const MARKET = {
  baseCosts: { w: 100, o: 100, s: 150 },
  amounts: [100, 200, 300],
  increment: 0.02,
  sellPercentage: 0.75,
  maxTrades: 20,
  periodHours: 20,
};

/** The game the server's rules make live at NOW. */
const LIVE_GAME = currentDartsGame(DARTS_GAMES, new Date(NOW * 1000))!;

const featureDeps = (over: Partial<ApplierDeps> = {}): ApplierDeps =>
  deps({ dartsItems: DARTS_GAMES, market: MARKET, ...over });

/** A save with a darts board in progress. */
function dartsWorld(
  privateState: Record<string, unknown> = {},
  resources = wallet(1000),
): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, items: {}, store: {} }],
      privateState: {
        dartsRandomSeed: 1234,
        dartsBalloonsShot: [],
        dartsHasFree: true,
        dartsGotExtra: false,
        timeStampDartsReset: NOW,
        timeStampDartsNewFree: 0,
        ...privateState,
      },
    },
    resources,
    nextCommandNumber: 1,
  };
}

/** A save with a market counter. */
function marketWorld(
  resources: ShimWorld['resources'],
  map: Record<string, unknown> = {},
): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [
        {
          id: 0,
          items: {},
          store: {},
          numTradesDone: 0,
          resourcesTraded: {},
          timestampLastTrade: 0,
          ...map,
        },
      ],
      privateState: {},
    },
    resources,
    nextCommandNumber: 1,
  };
}

/** The wallet after the cost table has charged the traded resource's base price. */
function settledPurse(
  resources: Partial<ShimWorld['resources']>,
  resource: keyof typeof MARKET.baseCosts = 'w',
): ShimWorld['resources'] {
  const before = purse(resources);
  const charge = MARKET.baseCosts[resource] ?? 100;
  return applyCommandCost(before, { cost: { g: charge }, gain: {} }).resources;
}

describe('the darts appliers', () => {
  it('records a valid shot and stores the prize from the live schedule', () => {
    const applier = createApplier(featureDeps());
    const world = dartsWorld();
    const outcome = applier(world, { name: 'darts_shoot_balloon', args: [0, 0] });

    assert.equal(outcome.applied, true);
    const state = outcome.world.save.privateState;
    assert.deepEqual(state['dartsBalloonsShot'], [0]);
    assert.equal(state['dartsHasFree'], false);
    assert.equal(state['dartsGotExtra'], false);
    // The prize comes from the board and the rotated schedule, not the client.
    const prize = LIVE_GAME.items[buildDartsBoard(1234)[0]!]!;
    assert.equal(storeQuantity(outcome.world.save.maps[0], prize), 1);
    assert.equal(storeQuantity(outcome.world.save.maps[0], LIVE_GAME.extra_item), 0);
  });

  it('charges cash for a paid shot, but never for the free first shot', () => {
    const applier = createApplier(featureDeps());
    const free = applier(dartsWorld({}, wallet(100)), {
      name: 'darts_shoot_balloon',
      args: [0, 0],
    });
    assert.equal(free.applied, true);
    assert.equal(free.world.save.privateState['dartsHasFree'], false);
    assert.equal(free.world.resources['c'], 100, 'the free shot costs nothing');

    const paid = applier(dartsWorld({ dartsHasFree: false }, wallet(100)), {
      name: 'darts_shoot_balloon',
      args: [1, 0],
    });
    assert.equal(paid.applied, true);
    assert.equal(paid.world.resources['c'], 100 - DART_COST_CASH);
  });

  it('lets a cashless player take the free shot', () => {
    const applier = createApplier(featureDeps());
    const outcome = applier(dartsWorld({}, wallet(0)), {
      name: 'darts_shoot_balloon',
      args: [0, 0],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 0, 'a free shot spends no cash');
  });

  it('refuses a paid shot to a cashless player without spending anything', () => {
    const applier = createApplier(featureDeps());
    const world = dartsWorld({ dartsHasFree: false }, wallet(0));
    const before = { ...world.save.privateState };
    const outcome = applier(world, { name: 'darts_shoot_balloon', args: [0, 0] });

    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'insufficient-resources');
    assert.deepEqual(outcome.world.resources, world.resources);
    assert.deepEqual(outcome.world.save.privateState, before);
  });

  it('refuses a target already shot without changing the save or spending cash', () => {
    const applier = createApplier(featureDeps());
    const first = applier(dartsWorld(), {
      name: 'darts_shoot_balloon',
      args: [0, 0],
    });
    const before = first.world.save.privateState;
    const resources = { ...first.world.resources };
    const again = applier(first.world, { name: 'darts_shoot_balloon', args: [0, 0] });

    assert.equal(again.applied, false);
    assert.equal(again.refused, 'already-shot');
    assert.deepEqual(again.world.save.privateState, before);
    assert.deepEqual(again.world.resources, resources);
  });

  it('refuses a target outside the board without spending anything', () => {
    const applier = createApplier(featureDeps());
    for (const index of [-1, 25, 1.5, Number.NaN]) {
      const world = dartsWorld();
      const before = { ...world.save.privateState };
      const outcome = applier(world, { name: 'darts_shoot_balloon', args: [index, 0] });
      assert.equal(outcome.applied, false, `index ${index}`);
      assert.equal(outcome.refused, 'bad-target', `index ${index}`);
      assert.deepEqual(outcome.world.save.privateState, before);
      assert.deepEqual(outcome.world.resources, world.resources);
    }
  });

  it('does not grant the extra prize just because the client claims it', () => {
    const applier = createApplier(featureDeps());
    const outcome = applier(dartsWorld(), {
      name: 'darts_shoot_balloon',
      args: [0, 1],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.save.privateState['dartsGotExtra'], false);
    assert.equal(storeQuantity(outcome.world.save.maps[0], LIVE_GAME.extra_item), 0);
  });

  it('grants the extra prize when the server sees every prize discovered', () => {
    const applier = createApplier(featureDeps());
    const board = buildDartsBoard(1234);
    let world = dartsWorld();
    // One target for each prize, with the client claiming NO extra prize.
    for (let prize = 0; prize < 6; prize++) {
      const target = board.indexOf(prize);
      const outcome = applier(world, {
        name: 'darts_shoot_balloon',
        args: [target, 0],
      });
      assert.equal(outcome.applied, true, `prize ${prize}`);
      world = outcome.world;
    }

    assert.equal(world.save.privateState['dartsGotExtra'], true);
    assert.equal((world.save.privateState['dartsBalloonsShot'] as number[]).length, 6);
    assert.equal(storeQuantity(world.save.maps[0], LIVE_GAME.extra_item), 1);
    // A further shot must not grant a second extra prize.
    const alreadyShot = new Set(world.save.privateState['dartsBalloonsShot'] as number[]);
    const unshot = board.findIndex((_prize, index) => !alreadyShot.has(index));
    const next = applier(world, { name: 'darts_shoot_balloon', args: [unshot, 1] });
    assert.equal(next.applied, true, `unshot target ${unshot}`);
    assert.equal(storeQuantity(next.world.save.maps[0], LIVE_GAME.extra_item), 1);
  });

  it('resets the free-shot flag and timestamp, once per day', () => {
    const applier = createApplier(featureDeps());
    const world = dartsWorld({
      dartsHasFree: false,
      timeStampDartsNewFree: NOW - 86400,
    });
    const outcome = applier(world, { name: 'darts_new_free', args: [] });

    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.save.privateState['dartsHasFree'], true);
    assert.equal(outcome.world.save.privateState['timeStampDartsNewFree'], NOW);

    const again = applier(outcome.world, { name: 'darts_new_free', args: [] });
    assert.equal(again.applied, false);
    assert.equal(again.refused, 'already-free');
    assert.deepEqual(again.world.save.privateState, outcome.world.save.privateState);
  });

  it('rebuilds a fresh board from the server seed, not a client-supplied one', () => {
    const applier = createApplier(featureDeps());
    const world = dartsWorld({
      dartsBalloonsShot: [3, 7],
      dartsHasFree: false,
      dartsGotExtra: true,
      timeStampDartsReset: 0,
    });
    const outcome = applier(world, { name: 'darts_reset', args: [99999, [1, 1, 1, 1, 1, 1]] });

    assert.equal(outcome.applied, true);
    const state = outcome.world.save.privateState;
    assert.equal(state['dartsRandomSeed'], hashSeed(`darts:${NOW}:1`));
    assert.notEqual(state['dartsRandomSeed'], 99999);
    assert.deepEqual(state['dartsBalloonsShot'], []);
    assert.equal(state['dartsHasFree'], true);
    assert.equal(state['dartsGotExtra'], false);
    assert.equal(state['timeStampDartsReset'], NOW);
    assert.equal(state['timeStampDartsNewFree'], NOW);
    assert.equal(buildDartsBoard(state['dartsRandomSeed'] as number).length, 25);
  });

  it('refuses a second reset in the same weekly window', () => {
    const applier = createApplier(featureDeps());
    const first = applier(dartsWorld({ timeStampDartsReset: 0 }), {
      name: 'darts_reset',
      args: [],
    });
    assert.equal(first.applied, true);

    const before = { ...first.world.save.privateState };
    const again = applier(first.world, { name: 'darts_reset', args: [] });
    assert.equal(again.applied, false);
    assert.equal(again.refused, 'too-soon');
    assert.deepEqual(again.world.save.privateState, before);
  });

  it('allows a reset once the weekly window has elapsed', () => {
    const applier = createApplier(featureDeps());
    const world = dartsWorld({
      timeStampDartsReset: NOW - 7 * 86400,
      dartsBalloonsShot: [3, 7],
      dartsHasFree: false,
      dartsGotExtra: true,
    });
    const outcome = applier(world, { name: 'darts_reset', args: [] });

    assert.equal(outcome.applied, true);
    const state = outcome.world.save.privateState;
    assert.deepEqual(state['dartsBalloonsShot'], []);
    assert.equal(state['dartsHasFree'], true);
    assert.equal(state['dartsGotExtra'], false);
    assert.equal(state['timeStampDartsReset'], NOW);
  });
});

describe('the trade applier', () => {
  it('buys at the server-computed price and advances the trade counter', () => {
    const applier = createApplier(featureDeps());
    const before = purse({ g: 1000 });
    // The cost table has already charged the standard 100-unit price.
    const world = marketWorld(settledPurse({ g: 1000 }));

    const outcome = applier(world, { name: 'trade_resource', args: ['w', 0, 200] });
    assert.equal(outcome.applied, true);
    // 100 * (200/100) * (1 + 0*0.02) = 200 gold, net of the settled price.
    assert.equal(outcome.world.resources['g'], before['g']! - 200);
    assert.equal(outcome.world.resources['w'], 200);
    const map = outcome.world.save.maps[0]!;
    assert.equal(map['numTradesDone'], 1);
    assert.equal(map['timestampLastTrade'], NOW);
    assert.deepEqual(map['resourcesTraded'], { w: 200 });
  });

  it('sells at the server-computed price and debits the resource', () => {
    const applier = createApplier(featureDeps());
    const before = purse({ g: 1000, w: 100 });
    // A sell is not charged up front by the cost table, so the wallet arrives
    // intact and the applier only adds the sell price.
    const world = marketWorld(purse({ g: 1000, w: 100 }));

    const outcome = applier(world, { name: 'trade_resource', args: ['w', 1, 100] });
    assert.equal(outcome.applied, true);
    // round(100 * 1 * 1) * 0.75 = 75 gold received.
    assert.equal(outcome.world.resources['g'], before['g']! + 75);
    assert.equal(outcome.world.resources['w'], 0);
  });

  it('lets a player with no gold sell at the market', () => {
    const applier = createApplier(featureDeps());
    const world = marketWorld(purse({ g: 0, w: 100 }));

    const outcome = applier(world, { name: 'trade_resource', args: ['w', 1, 100] });
    assert.equal(outcome.applied, true);
    // round(100 * 1 * 1) * 0.75 = 75 gold received, with no up-front charge.
    assert.equal(outcome.world.resources['g'], 75);
    assert.equal(outcome.world.resources['w'], 0);
    const map = outcome.world.save.maps[0]!;
    assert.equal(map['numTradesDone'], 1);
    assert.deepEqual(map['resourcesTraded'], { w: 100 });
  });

  it('uses the price after the trades already made this period', () => {
    const applier = createApplier(featureDeps());
    const world = marketWorld(settledPurse({ g: 1000 }, 's'), {
      numTradesDone: 5,
      timestampLastTrade: NOW - 3600,
    });
    const outcome = applier(world, { name: 'trade_resource', args: ['s', 0, 100] });
    assert.equal(outcome.applied, true);
    // round(150 * 1 * (1 + 5*0.02)) = 165 gold.
    assert.equal(outcome.world.resources['g'], 1000 - 165);
    assert.equal((outcome.world.save.maps[0]!['numTradesDone'] as number), 6);
  });

  it('refuses an amount or resource the content does not allow, spending nothing', () => {
    const applier = createApplier(featureDeps());
    for (const [args, reason] of [
      [['w', 0, 150], 'unknown-amount'],
      [['x', 0, 100], 'unknown-resource'],
    ] as const) {
      const world = marketWorld(settledPurse({ g: 1000 }));
      const resources = { ...world.resources };
      const outcome = applier(world, { name: 'trade_resource', args: [...args] });
      assert.equal(outcome.applied, false);
      assert.equal(outcome.refused, reason);
      assert.deepEqual(outcome.world.resources, resources);
      const map = outcome.world.save.maps[0]!;
      assert.equal(map['numTradesDone'], 0);
      assert.equal(map['timestampLastTrade'], 0);
      assert.deepEqual(map['resourcesTraded'], {});
    }
  });

  it('refuses prototype-key resources without producing NaN gold', () => {
    const applier = createApplier(featureDeps());
    for (const resource of ['__proto__', 'constructor', 'toString']) {
      const world = marketWorld(settledPurse({ g: 1000 }));
      const before = { ...world.resources };
      const outcome = applier(world, {
        name: 'trade_resource',
        args: [resource, 0, 100],
      });
      assert.equal(outcome.applied, false, resource);
      assert.equal(outcome.refused, 'unknown-resource', resource);
      assert.deepEqual(outcome.world.resources, before, resource);
      assert.equal(Number.isNaN(outcome.world.resources['g']), false, resource);
    }
  });

  it('enforces the 20-trade limit from the server counter', () => {
    const applier = createApplier(featureDeps());
    const world = marketWorld(settledPurse({ g: 1000 }), {
      numTradesDone: 20,
      timestampLastTrade: NOW - 3600,
    });
    const resources = { ...world.resources };
    const outcome = applier(world, { name: 'trade_resource', args: ['w', 0, 100] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'too-many-trades');
    assert.deepEqual(outcome.world.resources, resources);
    assert.equal(outcome.world.save.maps[0]!['numTradesDone'], 20);
  });

  it('reopens the market after the content period has passed', () => {
    const applier = createApplier(featureDeps());
    const world = marketWorld(settledPurse({ g: 1000 }), {
      numTradesDone: 20,
      timestampLastTrade: NOW - 25 * 3600,
    });
    const outcome = applier(world, { name: 'trade_resource', args: ['w', 0, 100] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.save.maps[0]!['numTradesDone'], 1);
    assert.equal(outcome.world.resources['g'], 1000 - 100);
  });
});

/** The content's REWARDS_CHAPTERS global, which the server pays from. */
const CHAPTER_REWARDS = {
  1: { g: 250, w: 200 },
  2: { g: 500, o: 400 },
  99: { g: 3000, s: 2400 },
};

const chapterDeps = (over: Partial<ApplierDeps> = {}): ApplierDeps =>
  deps({ chapterRewards: CHAPTER_REWARDS, ...over });

/** A player's own map with a chapter status in `currentQuestVars`. */
function chapterWorld(
  vars: Record<string, unknown> = {},
  over: {
    resources?: ShimWorld['resources'];
    privateState?: Record<string, unknown>;
  } = {},
): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [
        {
          id: 0,
          idCurrentMission: 1,
          timestampLastChapter: 0,
          currentQuestVars: { ...vars },
        },
      ],
      privateState: { ...(over.privateState ?? {}) },
    },
    resources: over.resources ?? purse({}),
    nextCommandNumber: 1,
  };
}

const chapterVars = (world: ShimWorld): Record<string, unknown> =>
  world.save.maps[0]!['currentQuestVars'] as Record<string, unknown>;

describe('set_quest_var', () => {
  it('refuses a key outside the chapter-status whitelist', () => {
    const applier = createApplier(chapterDeps());
    const world = chapterWorld({ id: 1 });
    const outcome = applier(world, {
      name: 'set_quest_var',
      args: ['hacked', JSON.stringify(1)],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'unknown-quest-var');
    assert.deepEqual(chapterVars(outcome.world), { id: 1 });
    assert.equal(outcome.world.save.maps[0]!['idCurrentMission'], 1);
  });

  it('refuses malformed value shapes without touching the saved state', () => {
    const applier = createApplier(chapterDeps());
    const badValues: [string, unknown][] = [
      ['spawned', 1],
      ['ended', 'true'],
      ['visited', {}],
      ['activators', [1, 'x']],
      ['boss', {}],
      ['treasure', [null]],
      ['killed', [1, 2]],
      ['id', 1.5],
    ];
    for (const [key, value] of badValues) {
      const world = chapterWorld({ id: 1, spawned: true });
      const outcome = applier(world, {
        name: 'set_quest_var',
        args: [key, JSON.stringify(value)],
      });
      assert.equal(outcome.applied, false, key);
      assert.equal(outcome.refused, 'bad-quest-var-value', key);
      assert.deepEqual(chapterVars(outcome.world), { id: 1, spawned: true }, key);
      assert.equal(outcome.world.save.maps[0]!['idCurrentMission'], 1, key);
    }
  });

  it('ignores idSimpleChapter as the upstream does', () => {
    const applier = createApplier(chapterDeps());
    const outcome = applier(chapterWorld({ id: 1 }), {
      name: 'set_quest_var',
      args: ['idSimpleChapter', JSON.stringify(12)],
    });
    assert.equal(outcome.applied, true);
    assert.deepEqual(chapterVars(outcome.world), { id: 1 });
    assert.equal(outcome.world.save.maps[0]!['idCurrentMission'], 1);
  });

  it('mirrors an id write into the map current mission', () => {
    const applier = createApplier(chapterDeps());
    const outcome = applier(chapterWorld({ id: 1 }), {
      name: 'set_quest_var',
      args: ['id', JSON.stringify(4)],
    });
    assert.equal(outcome.applied, true);
    assert.equal(chapterVars(outcome.world)['id'], 4);
    assert.equal(outcome.world.save.maps[0]!['idCurrentMission'], 4);
  });

  it('refuses ended without a spawned chapter', () => {
    const applier = createApplier(chapterDeps());
    const outcome = applier(chapterWorld({ id: 1 }), {
      name: 'set_quest_var',
      args: ['ended', 'true'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'chapter-not-spawned');
    assert.deepEqual(chapterVars(outcome.world), { id: 1 });
  });

  it('stores a valid write in currentQuestVars', () => {
    const applier = createApplier(chapterDeps());
    const world = chapterWorld({ id: 1 });
    // A `killed` write is only honoured for refs the ledger marks dead.
    world.save.privateState[ACTIVE_QUEST_KEY] = {
      questId: QUEST_ID_02_CENTRAL_NUCLEAR,
      phase: 'map-loaded',
      script: { destroyed: [], nearDeath: [], defendersCleared: [], keyElementsLost: [], counters: {}, suppressed: false },
      ledger: {
        elements: {
          centralNuclear: { hp: 0, alive: false },
          commandCenter: { hp: 0, alive: false },
        },
        events: [],
        strikes: {},
      },
    };
    const spawned = applier(world, {
      name: 'set_quest_var',
      args: ['spawned', 'true'],
    });
    assert.equal(spawned.applied, true);
    assert.equal(chapterVars(spawned.world)['spawned'], true);
    const killed = applier(spawned.world, {
      name: 'set_quest_var',
      args: ['killed', JSON.stringify(['centralNuclear', 'commandCenter'])],
    });
    assert.equal(killed.applied, true);
    assert.deepEqual(chapterVars(killed.world)['killed'], ['centralNuclear', 'commandCenter']);
    const ended = applier(killed.world, { name: 'set_quest_var', args: ['ended', 'true'] });
    assert.equal(ended.applied, true);
    assert.equal(chapterVars(ended.world)['ended'], true);
  });
});

describe('collect_mission', () => {
  const endedChapter = (id = 1): ShimWorld =>
    chapterWorld({ id, spawned: true, ended: true }, { resources: purse({ g: 100, w: 50 }) });

  it('refuses a chapter with no objective record, spending nothing', () => {
    const applier = createApplier(chapterDeps());
    const world = chapterWorld({}, { resources: purse({ g: 100, w: 50 }) });
    const outcome = applier(world, { name: 'collect_mission', args: [2] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-chapter');
    assert.deepEqual(outcome.world.resources, world.resources);
    assert.deepEqual(chapterVars(outcome.world), {});
  });

  it('refuses a chapter that has not ended, spending nothing', () => {
    const applier = createApplier(chapterDeps());
    const world = chapterWorld(
      { id: 1, spawned: true, ended: false },
      { resources: purse({ g: 100, w: 50 }) },
    );
    const outcome = applier(world, { name: 'collect_mission', args: [2] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'chapter-not-ended');
    assert.deepEqual(outcome.world.resources, world.resources);
    assert.equal(outcome.world.save.maps[0]!['idCurrentMission'], 1);
    assert.equal(outcome.world.save.maps[0]!['timestampLastChapter'], 0);
    assert.deepEqual(chapterVars(outcome.world), { id: 1, spawned: true, ended: false });
  });

  it('refuses a chapter that was never spawned', () => {
    const applier = createApplier(chapterDeps());
    const world = chapterWorld({ id: 1, ended: true });
    const outcome = applier(world, { name: 'collect_mission', args: [2] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'chapter-not-spawned');
    assert.deepEqual(outcome.world.resources, world.resources);
    assert.deepEqual(chapterVars(outcome.world), { id: 1, ended: true });
  });

  it('grants exactly the content reward and advances the chapter', () => {
    const applier = createApplier(chapterDeps());
    const outcome = applier(endedChapter(), { name: 'collect_mission', args: [2] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 350);
    assert.equal(outcome.world.resources['w'], 250);
    assert.equal(outcome.world.resources['o'], 0);
    const map = outcome.world.save.maps[0]!;
    assert.equal(map['idCurrentMission'], '2');
    assert.equal(map['timestampLastChapter'], NOW);
    assert.deepEqual(map['currentQuestVars'], {});
    const awards = outcome.world.save.privateState['chapterAwards'] as
      | Record<string, number>
      | undefined;
    assert.equal(awards?.['1'], NOW);
  });

  it('wraps a next chapter above 99 back to 1', () => {
    const applier = createApplier(chapterDeps());
    const outcome = applier(endedChapter(99), { name: 'collect_mission', args: [100] });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.save.maps[0]!['idCurrentMission'], '1');
    assert.equal(outcome.world.resources['g'], 3100);
  });

  it('pays nothing on a replay, even after the vars are rewritten', () => {
    const applier = createApplier(chapterDeps());
    const first = applier(endedChapter(), { name: 'collect_mission', args: [2] });
    assert.equal(first.applied, true);
    const replayWorld = chapterWorld(
      { id: 1, spawned: true, ended: true },
      { resources: first.world.resources, privateState: first.world.save.privateState },
    );
    const second = applier(replayWorld, { name: 'collect_mission', args: [2] });
    assert.equal(second.applied, false);
    assert.equal(second.refused, 'already-awarded');
    assert.deepEqual(second.world.resources, first.world.resources);
  });

  it('ignores a client reward delta', () => {
    const applier = createApplier(chapterDeps());
    const outcome = applier(endedChapter(), {
      name: 'collect_mission',
      args: [2, { g: 1_000_000, w: 1_000_000, o: 1_000_000 }],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 350);
    assert.equal(outcome.world.resources['w'], 250);
    assert.equal(outcome.world.resources['o'], 0);
  });

  it('refuses a chapter with no content reward', () => {
    const applier = createApplier(chapterDeps());
    const world = endedChapter(500);
    const outcome = applier(world, { name: 'collect_mission', args: [501] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-chapter-reward');
    assert.deepEqual(outcome.world.resources, world.resources);
    assert.deepEqual(chapterVars(outcome.world), { id: 500, spawned: true, ended: true });
  });
});

describe('admin_set_quest_rank', () => {
  it('is accepted for the client flow but never overwrites the server ranks', () => {
    const applier = createApplier(chapterDeps());
    const world = chapterWorld({}, { privateState: { questsRank: { '7': 2 } } });
    const outcome = applier(world, { name: 'admin_set_quest_rank', args: ['7', '3'] });
    assert.equal(outcome.applied, true);
    assert.deepEqual(outcome.world.save.privateState['questsRank'], { '7': 2 });
    assert.deepEqual(outcome.world.resources, world.resources);
    assert.deepEqual(outcome.world.save.privateState['chapterAwards'], undefined);
  });

  it('does not create a rank when none is stored', () => {
    const applier = createApplier(chapterDeps());
    const world = chapterWorld();
    const outcome = applier(world, { name: 'admin_set_quest_rank', args: ['7', '3'] });
    assert.equal(outcome.applied, true);
    assert.equal('questsRank' in outcome.world.save.privateState, false);
  });
});

// ---------------------------------------------------------------------------
// Assault quests — the server-owned QuestState and end_quest
// ---------------------------------------------------------------------------

/** QUEST_02's elements, as the content supplies them. */
const QUEST_ITEMS = new Map<number, ApplierItem>([
  [1017, item({ id: 1017, type: 'u', subcatFunctional: 111 })], // Good Boy (key element)
  [89, item({ id: 89, type: 'b', subcatFunctional: 112 })], // nuclear plant
  [195, item({ id: 195, type: 'b', subcatFunctional: 113 })], // command centre
  [1035, item({ id: 1035, type: 'u', subcatFunctional: 114 })], // truck (ITEM.truck2)
  [1063, item({ id: 1063, type: 'u', subcatFunctional: 115 })], // gun bot (weekly quest)
]);

const questDeps = (over: Partial<ApplierDeps> = {}): ApplierDeps =>
  chapterDeps({ items: QUEST_ITEMS, questExpRequired: 300, ...over });

/**
 * A player's own map with a fully started quest.
 *
 * The quest is started through the authoritative helper, and the ledger is
 * then marked dead for every roster element. These tests are about the
 * command semantics (triggers, rewards, dedupe) — the strike/authority path
 * itself is covered in `quest-authority.test.ts`.
 */
function questWorld(
  over: {
    questId?: string;
    vars?: Record<string, unknown>;
    privateState?: Record<string, unknown>;
    resources?: ShimWorld['resources'];
    deps?: ApplierDeps;
  } = {},
): ShimWorld {
  const world: ShimWorld = {
    save: {
      playerInfo: {},
      maps: [
        {
          id: 0,
          idCurrentMission: 1,
          currentQuestVars: { ...(over.vars ?? {}) },
        },
      ],
      privateState: { ...(over.privateState ?? {}) },
    },
    resources: over.resources ?? purse({}),
    nextCommandNumber: 1,
  };
  if (!(ACTIVE_QUEST_KEY in world.save.privateState)) {
    const questId = over.questId ?? QUEST_ID_02_CENTRAL_NUCLEAR;
    const started = createQuestHelpers(over.deps ?? questDeps()).beginQuest(world, questId);
    if (started.ok) {
      const state = started.world.save.privateState[ACTIVE_QUEST_KEY] as ActiveQuestState;
      // Simulate the server's strikes having already killed each element.
      for (const element of Object.values(state.ledger.elements)) {
        element.hp = 0;
        element.alive = false;
      }
      world.save.privateState[ACTIVE_QUEST_KEY] = state;
    }
  }
  return world;
}

const activeState = (world: ShimWorld): ActiveQuestState =>
  world.save.privateState[ACTIVE_QUEST_KEY] as ActiveQuestState;

/**
 * A two-argument `set_quest_var` killed write.
 *
 * The optional second parameter is accepted only so older call sites still
 * type-check; it is deliberately ignored — there is no third wire argument.
 */
const killedWrite = (refs: string[], _ignoredQuestId?: string) => ({
  name: 'set_quest_var',
  args: ['killed', JSON.stringify(refs)] as unknown[],
});

describe('the active assault quest', () => {
  it('derives the roster from the quest spec and the content items', () => {
    const spec = getQuestSpec(QUEST_ID_02_CENTRAL_NUCLEAR)!;
    const roster = questRoster(spec, QUEST_ITEMS);
    assert.deepEqual(
      roster.map((element) => [element.ref, element.itemId, element.affiliation, element.isUnit]),
      [
        ['goodBoy', 1017, 'self', true],
        ['centralNuclear', 89, 'enemy', false],
        ['commandCenter', 195, 'enemy', false],
        ['truck', 1035, 'enemy', true],
      ],
    );
    assert.equal(roster[2]?.subcatFunctional, 113);
    assert.deepEqual(questRoster(spec).map((element) => element.isUnit), [
      false,
      false,
      false,
      false,
    ]);
  });

  it('initialises activeQuest from the roster on the first validated killed write', () => {
    const applier = createApplier(questDeps());
    const outcome = applier(questWorld(), killedWrite(['commandCenter']));
    assert.equal(outcome.applied, true);
    const state = activeState(outcome.world);
    assert.equal(state.questId, QUEST_ID_02_CENTRAL_NUCLEAR);
    assert.equal(state.phase, 'map-loaded');
    assert.deepEqual(state.script.destroyed, ['commandCenter']);
    // loadQuestMap derived the enemy count from the roster.
    assert.equal(state.remainingFoes, 1);
    assert.deepEqual(chapterVars(outcome.world)['killed'], ['commandCenter']);
  });

  it('refuses a killed write with no active quest, whatever the third argument', () => {
    const applier = createApplier(questDeps());
    const world = questWorld();
    delete world.save.privateState[ACTIVE_QUEST_KEY];
    const before = structuredClone(world);
    const outcome = applier(world, {
      name: 'set_quest_var',
      args: ['killed', JSON.stringify(['centralNuclear']), QUEST_ID_02_CENTRAL_NUCLEAR],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-active-quest');
    assert.deepEqual(outcome.world, before);
  });

  it('refuses a killed ref that the ledger does not mark dead', () => {
    const applier = createApplier(questDeps());
    const world = questWorld();
    const before = structuredClone(world);
    const outcome = applier(world, killedWrite(['notAnElement']));
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'element-not-killed');
    assert.deepEqual(outcome.world, before);
  });

  it('ignores a third argument but keeps end_quest scoped to the active quest', () => {
    const applier = createApplier(questDeps());
    // A third argument is no longer read. The killed write applies to the
    // active quest's own state, never to the named quest.
    const forged = applier(questWorld(), {
      name: 'set_quest_var',
      args: ['killed', JSON.stringify(['commandCenter']), QUEST_ID_01_BAZOOKA],
    });
    assert.equal(forged.applied, true);
    assert.deepEqual(activeState(forged.world).script.destroyed, ['commandCenter']);

    // A different quest cannot pay out the active quest's reward.
    const beforeEnd = structuredClone(forged.world);
    const switchedEnd = applier(forged.world, {
      name: 'end_quest',
      args: [QUEST_ID_01_BAZOOKA, 1],
    });
    assert.equal(switchedEnd.applied, false);
    assert.equal(switchedEnd.refused, 'quest-mismatch');
    assert.deepEqual(switchedEnd.world, beforeEnd);
  });

  it('refuses a claimed win with no server kills', () => {
    const applier = createApplier(questDeps());
    const world = questWorld({ vars: {} });
    const outcome = applier(world, {
      name: 'end_quest',
      args: [
        JSON.stringify({
          quest_id: QUEST_ID_02_CENTRAL_NUCLEAR,
          win: true,
          units: [[1017, 1, 0, 0]],
          loot: { g: 1_000_000 },
        }),
      ],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.deepEqual(outcome.world.resources, world.resources);
    assert.ok(ACTIVE_QUEST_KEY in outcome.world.save.privateState);
  });

  it('grants the content-derived reward, sets the rank and clears the state on a win', () => {
    const applier = createApplier(questDeps());
    let world = questWorld();
    const kill = applier(world, killedWrite(['commandCenter']));
    assert.equal(kill.applied, true);
    world = kill.world;
    const outcome = applier(world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
    assert.equal(outcome.applied, true);
    // REWARDS_QUESTS[6] = { g: 4000, o: 1400 }; expRequired 300 gives 100 XP
    // for the gold row. Kill XP is clamped to half the (zero) kill gold.
    assert.equal(outcome.world.resources['g'], 4000);
    assert.equal(outcome.world.resources['o'], 1400);
    assert.equal(outcome.world.resources['x'], 100);
    assert.deepEqual(outcome.world.save.privateState['questsRank'], { '6': 1 });
    const progress = outcome.world.save.privateState[QUEST_PROGRESS_KEY] as {
      ranks: Record<string, number>;
      awarded: string[];
    };
    assert.equal(progress.ranks['6'], 1);
    assert.deepEqual(progress.awarded, [QUEST_ID_02_CENTRAL_NUCLEAR]);
    assert.equal(ACTIVE_QUEST_KEY in outcome.world.save.privateState, false);
  });

  it('pays nothing on a replay', () => {
    const applier = createApplier(questDeps());
    const killed = applier(questWorld(), killedWrite(['commandCenter']));
    const first = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
    assert.equal(first.applied, true);
    const replay = applier(first.world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
    assert.equal(replay.applied, false);
    // The win cleared the active state, so a replay has no quest to resolve —
    // and the award log still guarantees the reward cannot be paid twice.
    assert.equal(replay.refused, 'no-active-quest');
    assert.deepEqual(replay.world.resources, first.world.resources);
  });

  it('ignores a legacy blob\'s win, units and loot', () => {
    const applier = createApplier(questDeps());
    const killed = applier(questWorld(), killedWrite(['commandCenter']));
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [
        JSON.stringify({
          quest_id: QUEST_ID_02_CENTRAL_NUCLEAR,
          win: false, // the win comes from the server's kills, not the claim
          units: [[1017, 10, 10, 0]],
          loot: { g: 1_000_000, o: 1_000_000 },
          difficulty: 3,
        }),
      ],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 4000);
    assert.equal(outcome.world.resources['o'], 1400);
    assert.deepEqual(outcome.world.save.privateState['questsRank'], { '6': 1 });
  });

  it('does not let a claimed difficulty set the rank', () => {
    const applier = createApplier(questDeps());
    const killed = applier(questWorld(), killedWrite(['commandCenter']));
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 3],
    });
    assert.equal(outcome.applied, true);
    assert.deepEqual(outcome.world.save.privateState['questsRank'], { '6': 1 });
  });

  it('does not implicitly start a quest from the legacy chapter status', () => {
    const applier = createApplier(questDeps());
    const world = questWorld({ vars: { killed: ['commandCenter'] } });
    delete world.save.privateState[ACTIVE_QUEST_KEY];
    const before = structuredClone(world);
    const outcome = applier(world, {
      name: 'end_quest',
      args: [JSON.stringify({ quest_id: QUEST_ID_02_CENTRAL_NUCLEAR })],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-active-quest');
    assert.deepEqual(outcome.world, before);
  });

  it('refuses an empty-roster hardcore quest with no server kills', () => {
    const applier = createApplier(questDeps());
    // The hardcore quests have no scripted elements: loadQuestMap seeds
    // enemiesAlive = 0, so isQuestVictory would be true with zero events and
    // end_quest would mint 10k gold plus steel. A win needs a server kill.
    const world = questWorld({ questId: QUEST_ID_15_HARDCORE1 });
    const before = structuredClone(world);
    const outcome = applier(world, {
      name: 'end_quest',
      args: [QUEST_ID_15_HARDCORE1, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.deepEqual(outcome.world, before);
  });

  it('grants whole XP when a reward row is fractional', () => {
    // 301 / 3 is fractional, so the gold row's extra XP (min(gold / 4, 301/3))
    // is 100.333…; a whole-resource wallet must not persist that fraction.
    const applier = createApplier(questDeps({ questExpRequired: 301 }));
    const killed = applier(questWorld(), killedWrite(['commandCenter']));
    assert.equal(killed.applied, true);
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
    assert.equal(outcome.applied, true);
    assert.ok(
      Number.isInteger(outcome.world.resources['x']),
      `fractional XP persisted: ${outcome.world.resources['x']}`,
    );
  });

  it('never pays from stale chapter refs without an active quest', () => {
    const applier = createApplier(questDeps());
    // A half-finished chapter leaves chapter refs beside quest refs in
    // currentQuestVars.killed. Those are chapter state, not proof of a kill.
    const world = questWorld({ vars: { killed: ['chapter-3-boss', 'commandCenter'] } });
    delete world.save.privateState[ACTIVE_QUEST_KEY];
    const before = structuredClone(world);
    const outcome = applier(world, {
      name: 'end_quest',
      args: [JSON.stringify({ quest_id: QUEST_ID_02_CENTRAL_NUCLEAR })],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-active-quest');
    assert.deepEqual(outcome.world, before);
  });

  it('refuses to pay a quest already recorded as a loss', () => {
    const applier = createApplier(questDeps());
    const killed = applier(questWorld(), killedWrite(['commandCenter']));
    assert.equal(killed.applied, true);
    // A genuine victory state, but the server recorded a loss before payout.
    const world = killed.world;
    world.save.privateState[ACTIVE_QUEST_KEY] = { ...activeState(world), result: 'loss' };
    const before = structuredClone(world);
    const outcome = applier(world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.deepEqual(outcome.world, before);
  });

  it('resolves a nearDeath quest from validated killed refs without recording kills', () => {
    const applier = createApplier(questDeps());
    const killed = applier(
      questWorld({ questId: QUEST_ID_01_BAZOOKA }),
      killedWrite(['boss1', 'jeep'], QUEST_ID_01_BAZOOKA),
    );
    assert.equal(killed.applied, true);
    const state = activeState(killed.world);
    assert.deepEqual(state.script.nearDeath, ['boss1', 'jeep']);
    // A nearDeath event must reach the nearDeath channel only, never
    // script.destroyed (which would let a destroy-only quest win by proxy).
    assert.deepEqual(state.script.destroyed, []);
    assert.deepEqual(state.script.defendersCleared, []);
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_01_BAZOOKA, 1],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 1500);
    assert.equal(outcome.world.resources['w'], 400);
  });

  it('does not double-apply a re-sent trigger ref', () => {
    const applier = createApplier(questDeps());
    const first = applier(
      questWorld({ questId: QUEST_ID_01_BAZOOKA }),
      killedWrite(['boss1', 'jeep'], QUEST_ID_01_BAZOOKA),
    );
    assert.equal(first.applied, true);
    const second = applier(first.world, killedWrite(['boss1', 'jeep'], QUEST_ID_01_BAZOOKA));
    assert.equal(second.applied, true);
    assert.deepEqual(activeState(second.world).script.nearDeath, ['boss1', 'jeep']);
    assert.deepEqual(activeState(second.world).script.destroyed, []);
  });

  it('refuses a nearDeath win when the key element was also destroyed', () => {
    const applier = createApplier(questDeps());
    const killed = applier(
      questWorld({ questId: QUEST_ID_01_BAZOOKA }),
      killedWrite(['boss1', 'jeep', 'general'], QUEST_ID_01_BAZOOKA),
    );
    assert.equal(killed.applied, true);
    assert.equal(activeState(killed.world).result, 'loss');
    assert.deepEqual(activeState(killed.world).script.keyElementsLost, ['general']);
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_01_BAZOOKA, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
  });

  it('does not pay a nearDeath quest replayed from the chapter status', () => {
    const applier = createApplier(questDeps());
    const world = questWorld({ vars: { killed: ['boss1', 'jeep'] } });
    delete world.save.privateState[ACTIVE_QUEST_KEY];
    const before = structuredClone(world);
    const outcome = applier(world, {
      name: 'end_quest',
      args: [JSON.stringify({ quest_id: QUEST_ID_01_BAZOOKA })],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-active-quest');
    assert.deepEqual(outcome.world, before);
  });

  it('resolves a quest that mixes defendersCleared and destroy events', () => {
    const applier = createApplier(questDeps());
    const killed = applier(
      questWorld({ questId: QUEST_ID_06_AIRSTRIKE }),
      killedWrite(['radioStation', 'enemyCommandCenter'], QUEST_ID_06_AIRSTRIKE),
    );
    assert.equal(killed.applied, true);
    const state = activeState(killed.world);
    assert.deepEqual(state.script.defendersCleared, ['radioStation']);
    assert.deepEqual(state.script.destroyed, ['enemyCommandCenter']);
    assert.deepEqual(state.script.nearDeath, []);
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_06_AIRSTRIKE, 1],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['g'], 2000);
    assert.equal(outcome.world.resources['w'], 600);
  });

  it('requires both events for the mixed defender/destroy quest', () => {
    const applier = createApplier(questDeps());
    const killed = applier(
      questWorld({ questId: QUEST_ID_06_AIRSTRIKE }),
      killedWrite(['radioStation'], QUEST_ID_06_AIRSTRIKE),
    );
    assert.equal(killed.applied, true);
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_06_AIRSTRIKE, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
  });
});

describe('the authoritative quest reward result', () => {
  // REWARDS_QUESTS[6] = { g: 4000, o: 1400 }; expRequired 300 gives 100 XP
  // for the gold row. The exact rows the applier reports must equal what it
  // writes into the wallet, including the rounding of the fractional XP.
  const exactRows = [
    { resource: 'gold', amount: 0 },
    { resource: 'xp', amount: 0 },
    { resource: 'xp', amount: 100 },
    { resource: 'gold', amount: 4000 },
    { resource: 'oil', amount: 1400 },
  ];

  function winningOutcome() {
    const applier = createApplier(questDeps());
    const killed = applier(questWorld(), killedWrite(['commandCenter']));
    return applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
  }

  it('returns the exact awarded rows, mapped to resource names', () => {
    const outcome = winningOutcome();
    assert.equal(outcome.applied, true);
    assert.deepEqual(outcome.result, { kind: 'rewards', rewards: exactRows });
  });

  it('reports the same amounts it actually paid into the wallet', () => {
    const outcome = winningOutcome();
    const paid: Record<string, number> = {};
    for (const row of exactRows) {
      paid[row.resource] = (paid[row.resource] ?? 0) + row.amount;
    }
    assert.equal(outcome.world.resources['g'], paid['gold']);
    assert.equal(outcome.world.resources['x'], paid['xp']);
    assert.equal(outcome.world.resources['o'], paid['oil']);
  });

  it('returns no result when the server refuses the quest', () => {
    const applier = createApplier(questDeps());
    const outcome = applier(questWorld(), {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.equal(outcome.result, undefined);
    assert.equal(LAST_QUEST_REWARD_KEY in outcome.world.save.privateState, false);
  });

  it('returns no result on an already-awarded replay', () => {
    const applier = createApplier(questDeps());
    const killed = applier(questWorld(), killedWrite(['commandCenter']));
    killed.world.save.privateState[QUEST_PROGRESS_KEY] = {
      ranks: {},
      awarded: [QUEST_ID_02_CENTRAL_NUCLEAR],
    };
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_02_CENTRAL_NUCLEAR, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'already-awarded');
    assert.equal(outcome.result, undefined);
  });

  it('persists a minimal reward receipt with the quest id, rows and rank', () => {
    const outcome = winningOutcome();
    assert.deepEqual(outcome.world.save.privateState[LAST_QUEST_REWARD_KEY], {
      questId: QUEST_ID_02_CENTRAL_NUCLEAR,
      rank: 1,
      rewards: exactRows,
    });
  });
});

describe('hardcore quests with extracted rosters', () => {
  // The real bundle supplies 79..153 units per hardcore quest. A small roster
  // exercises the same `enemiesAlive` accounting without a giant kill list.
  const HC = QUEST_ID_15_HARDCORE1;
  const ROSTER = [
    { ref: 'item:101', itemId: 1017, subcatFunctional: 111 },
    { ref: 'item:102', itemId: 1035, subcatFunctional: 114 },
    { ref: 'item:103', itemId: 1063, subcatFunctional: 115 },
  ];
  const REFS = ROSTER.map((entry) => entry.ref);
  const hardcoreDeps = (over: Partial<ApplierDeps> = {}): ApplierDeps =>
    questDeps({ questRosters: [{ questId: HC, items: ROSTER }], ...over });

  it('merges extracted entries into the roster of an empty-element quest', () => {
    const spec = getQuestSpec(HC)!;
    assert.deepEqual(spec.elements, []);
    // Without the bundle there is no roster: the safe default stays empty.
    assert.deepEqual(questRoster(spec, QUEST_ITEMS), []);
    assert.deepEqual(
      questRoster(spec, QUEST_ITEMS, [{ questId: HC, items: ROSTER }]).map((element) => [
        element.ref,
        element.itemId,
        element.affiliation,
        element.isUnit,
        element.subcatFunctional,
      ]),
      [
        ['item:101', 1017, 'enemy', true, 111],
        ['item:102', 1035, 'enemy', true, 114],
        ['item:103', 1063, 'enemy', true, 115],
      ],
    );
  });

  it('pays exactly once after the whole roster is killed', () => {
    const applier = createApplier(hardcoreDeps());
    const killed = applier(questWorld({ questId: HC, deps: hardcoreDeps() }), killedWrite(REFS));
    assert.equal(killed.applied, true);
    const state = activeState(killed.world);
    assert.equal(state.script.counters['enemiesAlive'], 0);
    assert.deepEqual(state.script.destroyed, REFS);
    const end = applier(killed.world, { name: 'end_quest', args: [HC, 1] });
    assert.equal(end.applied, true);
    // QUEST_15's content reward is { g: 10000, s: 3200 }.
    assert.equal(end.world.resources['g'], 10000);
    assert.equal(end.world.resources['s'], 3200);
    const replay = applier(end.world, { name: 'end_quest', args: [HC, 1] });
    assert.equal(replay.applied, false);
    assert.equal(replay.refused, 'no-active-quest');
    assert.deepEqual(replay.world.resources, end.world.resources);
  });

  it('refuses a partial roster', () => {
    const applier = createApplier(hardcoreDeps());
    const before = structuredClone(questWorld({ questId: HC, deps: hardcoreDeps() }));
    const killed = applier(questWorld({ questId: HC, deps: hardcoreDeps() }), killedWrite(REFS.slice(0, 2)));
    assert.equal(killed.applied, true);
    assert.equal(activeState(killed.world).script.counters['enemiesAlive'], 1);
    const end = applier(killed.world, { name: 'end_quest', args: [HC, 1] });
    assert.equal(end.applied, false);
    assert.equal(end.refused, 'no-victory');
    assert.deepEqual(end.world.resources, before.resources);
  });

  it('refuses an off-roster ref without mutating the save', () => {
    const applier = createApplier(hardcoreDeps());
    const world = questWorld({ questId: HC, deps: hardcoreDeps() });
    const before = structuredClone(world);
    const outcome = applier(world, killedWrite(['item:999']));
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'element-not-killed');
    assert.deepEqual(outcome.world, before);
  });

  it('refuses a zero-event hardcore end_quest even with a full roster available', () => {
    const applier = createApplier(hardcoreDeps());
    const world = questWorld({ questId: HC, deps: hardcoreDeps() });
    const before = structuredClone(world);
    const outcome = applier(world, { name: 'end_quest', args: [HC, 1] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.deepEqual(outcome.world, before);
  });

  it('refuses a hardcore quest recorded as a loss', () => {
    const applier = createApplier(hardcoreDeps());
    const killed = applier(questWorld({ questId: HC, deps: hardcoreDeps() }), killedWrite(REFS));
    assert.equal(killed.applied, true);
    const world = killed.world;
    world.save.privateState[ACTIVE_QUEST_KEY] = { ...activeState(world), result: 'loss' };
    const outcome = applier(world, { name: 'end_quest', args: [HC, 1] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
  });
});

describe('the weekly quest', () => {
  /** Kill the named roster bots one `set_quest_var` write at a time. */
  const killBots = (refs: readonly string[], questId = QUEST_ID_WEEKLY_01) => {
    const applier = createApplier(questDeps());
    let world = questWorld({ questId });
    for (const ref of refs) {
      const killed = applier(world, killedWrite([ref], questId));
      assert.equal(killed.applied, true, `kill ${ref} was refused: ${killed.refused}`);
      world = killed.world;
    }
    return world;
  };

  const endWeekly = (world: ShimWorld) =>
    createApplier(questDeps())(world, {
      name: 'end_quest',
      args: [QUEST_ID_WEEKLY_01, 1],
    });

  it('pays the weekly cash after five distinct validated bot kills', () => {
    const world = killBots(WEEKLY_BOT_REFS);
    const state = activeState(world);
    assert.deepEqual(state.script.destroyed, [...WEEKLY_BOT_REFS]);
    assert.equal(state.script.counters['botsKilled'], 5);

    const outcome = endWeekly(world);
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 5 * WEEKLY_CASH_PER_BOT);
    assert.equal(ACTIVE_QUEST_KEY in outcome.world.save.privateState, false);
  });

  it('refuses four kills with no reward', () => {
    const world = killBots(WEEKLY_BOT_REFS.slice(0, 4));
    assert.equal(activeState(world).script.counters['botsKilled'], 4);
    const outcome = endWeekly(world);
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.equal(outcome.world.resources['c'], 0);
    assert.equal(ACTIVE_QUEST_KEY in outcome.world.save.privateState, true);
  });

  it('counts a repeated ref once, however many times it is re-sent', () => {
    const world = killBots(Array(5).fill(WEEKLY_BOT_REFS[0]));
    const state = activeState(world);
    assert.deepEqual(state.script.destroyed, [WEEKLY_BOT_REFS[0]]);
    assert.equal(state.script.counters['botsKilled'], 1);
    const outcome = endWeekly(world);
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.equal(outcome.world.resources['c'], 0);
  });

  it('a replayed kill does not double-count and pays exactly once', () => {
    const won = killBots(WEEKLY_BOT_REFS);
    const replayed = createApplier(questDeps())(
      won,
      killedWrite([WEEKLY_BOT_REFS[4]!], QUEST_ID_WEEKLY_01),
    );
    assert.equal(replayed.applied, true);
    assert.equal(activeState(replayed.world).script.counters['botsKilled'], 5);
    const outcome = endWeekly(replayed.world);
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 5 * WEEKLY_CASH_PER_BOT);

    // The active state is cleared on award, so a second claim has no quest to
    // resolve (and the award log still forbids a second payment).
    const second = endWeekly(outcome.world);
    assert.equal(second.applied, false);
    assert.equal(second.refused, 'no-active-quest');
    assert.equal(second.world.resources['c'], 5 * WEEKLY_CASH_PER_BOT);
  });

  it('refuses a kill ref outside the weekly roster', () => {
    const applier = createApplier(questDeps());
    const world = questWorld({ questId: QUEST_ID_WEEKLY_01 });
    const before = structuredClone(world);
    const outcome = applier(world, killedWrite(['item:1063'], QUEST_ID_WEEKLY_01));
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'element-not-killed');
    assert.deepEqual(outcome.world, before);
  });

  it('refuses an end_quest with no validated kills', () => {
    const world = questWorld({ questId: QUEST_ID_WEEKLY_01 });
    const before = structuredClone(world);
    const outcome = endWeekly(world);
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
    assert.deepEqual(outcome.world, before);
  });

  it('does not pay the weekly quest from chapter status alone', () => {
    const world = questWorld({ vars: { killed: [...WEEKLY_BOT_REFS] } });
    delete world.save.privateState[ACTIVE_QUEST_KEY];
    const before = structuredClone(world);
    const outcome = endWeekly(world);
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-active-quest');
    assert.deepEqual(outcome.world, before);
  });

  it('never moves another quest\'s counter from a kill', () => {
    // The convoy's `trucksArrived` counts trucks reaching the exit, not
    // kills. A kill-driven counter must stay scoped to the weekly quest.
    const applier = createApplier(questDeps());
    const killed = applier(
      questWorld({ questId: QUEST_ID_03_DEFEND_CONVOY_AUTO }),
      killedWrite(['colonel'], QUEST_ID_03_DEFEND_CONVOY_AUTO),
    );
    assert.equal(killed.applied, true);
    assert.equal(activeState(killed.world).script.counters['trucksArrived'], undefined);
    const outcome = applier(killed.world, {
      name: 'end_quest',
      args: [QUEST_ID_03_DEFEND_CONVOY_AUTO, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-victory');
  });
});

describe('quest timing from the injected server clock', () => {
  /** A bare world, started through the authoritative helper. */
  function timedWorld(clockDeps: ApplierDeps): { ok: true; world: ShimWorld } | { ok: false } {
    const world: ShimWorld = {
      save: {
        playerInfo: {},
        maps: [{ id: 0, idCurrentMission: 1, currentQuestVars: {} }],
        privateState: {},
      },
      resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
      nextCommandNumber: 1,
    };
    const started = createQuestHelpers(clockDeps).beginQuest(world, QUEST_ID_WEEKLY_01);
    return started.ok ? { ok: true, world: started.world } : { ok: false };
  }

  it('stamps the start and refuses end_quest once the clock passes the mission timer', () => {
    const clock = { value: NOW };
    const clockDeps = questDeps({ now: () => clock.value });
    const started = timedWorld(clockDeps);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    const state = activeState(started.world);
    assert.equal(state.startedAt, NOW);
    assert.equal(state.lastTickAt, NOW);
    assert.equal(state.timeRemaining, 90);

    clock.value = NOW + 91;
    const before = structuredClone(started.world);
    const outcome = createApplier(clockDeps)(started.world, {
      name: 'end_quest',
      args: [QUEST_ID_WEEKLY_01, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'quest-lost');
    assert.deepEqual(outcome.world, before);
    assert.deepEqual(outcome.world.resources, before.resources);
  });

  it('ticks timeRemaining by exactly the injected clock delta, once per action', () => {
    const clock = { value: NOW };
    const clockDeps = questDeps({ now: () => clock.value });
    const helpers = createQuestHelpers(clockDeps);
    const started = timedWorld(clockDeps);
    assert.equal(started.ok, true);
    if (!started.ok) return;

    clock.value = NOW + 30;
    const first = helpers.applyQuestAction(started.world, QUEST_ID_WEEKLY_01, {
      type: 'strike',
      ref: WEEKLY_BOT_REFS[0]!,
    });
    assert.equal(first.ok, true, first.ok ? '' : first.reason);
    if (!first.ok) return;
    assert.equal(activeState(first.world).timeRemaining, 60);
    assert.equal(activeState(first.world).lastTickAt, NOW + 30);

    clock.value = NOW + 50;
    const second = helpers.applyQuestAction(first.world, QUEST_ID_WEEKLY_01, {
      type: 'strike',
      ref: WEEKLY_BOT_REFS[1]!,
    });
    assert.equal(second.ok, true, second.ok ? '' : second.reason);
    if (!second.ok) return;
    assert.equal(activeState(second.world).timeRemaining, 40);
    assert.equal(activeState(second.world).lastTickAt, NOW + 50);
  });
});
