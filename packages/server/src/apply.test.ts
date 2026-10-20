import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { GOALS, getGoalDefinition, createGoalState } from '@swl/rules';

import {
  type ApplierItem,
  BUILDING_STATE_KEYS,
  GOAL_STATE_KEY,
  createApplier,
  mapItems,
  type ApplierDeps,
  type MapItemTuple,
} from './apply.ts';
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
      maps: [{ id: 0, items: { '7': tuple } }],
      privateState: {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
    ...over,
  };
}

/** A wallet with the given amount of cash. */
function wallet(cash: number): ShimWorld['resources'] {
  return { g: 0, w: 0, o: 0, s: 0, c: cash, e: 100, x: 0, m: 0 };
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

  it('gives each placement its own iso id', () => {
    const applier = createApplier(deps({ items: new Map([[30, item()]]) }));
    const world = worldWithBuilding({});
    const first = applier(world, { name: 'place_stored_item', args: [1, 30, 5, 6, 1, 0, 0] });
    const second = applier(first.world, { name: 'place_stored_item', args: [1, 30, 8, 9, 1, 0, 0] });
    const items = mapItems(second.world.save.maps[0] as Record<string, unknown>);
    assert.equal(Object.keys(items).length, 3);
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

  it('refuses a claimed end_quest', () => {
    const applier = createApplier(deps());
    const world = worldWithBuilding({});
    const outcome = applier(world, { name: 'end_quest', args: [100000001, true] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'not-implemented');
    assert.equal(outcome.world.resources['g'], 0);
  });
});
