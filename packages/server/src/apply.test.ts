import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { GOALS, getGoalDefinition, createGoalState } from '@swl/rules';

import {
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
