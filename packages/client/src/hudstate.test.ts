import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  additionalPopulation,
  expRequired,
  hudState,
  levelOf,
  populationLimit,
  populationOf,
  type HudInput,
  type HudRules,
  type ItemPopulation,
} from './hudstate.ts';
import type { WorldSnapshot } from './session.ts';

const RULES: HudRules = {
  baseResourceLimits: { g: 20000, o: 20000, s: 20000, w: 20000 },
  maxEnergy: 30,
  startMaxPopulation: 20,
  maxPopulationCap: 175,
  maxPopulationPerLevel: 3,
};

const CONTENT = {
  items: new Map<number, ItemPopulation>([
    // The Command Center grants nothing.
    [26, { population: 0, type: 'b', grants: true }],
    // A House I grants 3.
    [1, { population: 3, type: 'b', grants: true }],
    // A Soldier uses 1.
    [1001, { population: 1, type: 'u', grants: false }],
  ]),
  rules: RULES,
  expRequiredByLevel: new Map([
    [1, 40],
    [2, 60],
    [3, 100],
  ]),
};

function world(overrides: Partial<WorldSnapshot> = {}): WorldSnapshot {
  return {
    maps: [
      {
        id: 0,
        items: {
          '1': [26, 48, 48, 0, 0, 0, 0, 1],
          '2': [1, 10, 10, 0, 0, 0, 0, 1],
        },
        level: 1,
        xp: 4,
      },
    ],
    resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 50, e: 30, x: 4, m: 0 },
    privateState: {},
    ...overrides,
  };
}

function input(overrides: Partial<HudInput> = {}): HudInput {
  return { world: world(), ...CONTENT, ...overrides };
}

describe('the level', () => {
  it('is the map\'s own field', () => {
    assert.equal(levelOf(world()), 1);
    const higher = world();
    higher.maps[0]!.level = 7;
    assert.equal(levelOf(higher), 7);
  });

  it('is the first level when the map has none', () => {
    const bare = world();
    delete bare.maps[0]!.level;
    assert.equal(levelOf(bare), 1);
  });

  it('is never below the first level', () => {
    const broken = world();
    broken.maps[0]!.level = 0;
    assert.equal(levelOf(broken), 1);
  });
});

describe('the population', () => {
  it('is used by the units and granted by the buildings', () => {
    // The Command Center grants 0 and the House grants 3.
    const population = populationOf(world(), CONTENT.items);
    assert.equal(population.used, 0);
    assert.equal(population.granted, 3);
  });

  it('counts a unit\'s population as used', () => {
    const withUnit = world();
    withUnit.maps[0]!.items['3'] = [1001, 20, 20, 0, 0, 0, 0, 1];
    const population = populationOf(withUnit, CONTENT.items);
    assert.equal(population.used, 1);
    assert.equal(population.granted, 3);
  });

  it('is zero for an empty map', () => {
    const bare = world();
    bare.maps[0]!.items = {};
    assert.deepEqual(populationOf(bare, CONTENT.items), { used: 0, granted: 0 });
  });

  it('is 20 for a player with no houses, whatever their level', () => {
    // The level does not raise the ceiling: the buildings do.
    assert.equal(populationLimit(0, RULES), 20);
    assert.equal(populationLimit(0, RULES, 0), 20);
    assert.equal(populationLimit(3, RULES), 23);
  });

  it('stops at the cap', () => {
    assert.equal(populationLimit(200, RULES), 175);
  });

  it('counts the map\'s own extra population', () => {
    const expanded = world();
    expanded.maps[0]!.increasedPopulation = 10;
    assert.equal(additionalPopulation(expanded), 10);
    assert.equal(additionalPopulation(world()), 0);
    // The extra population raises the hard cap, not the soft one.
    assert.equal(populationLimit(0, RULES, 10), 20);
  });
});

describe('the experience', () => {
  it('is what the next level asks for', () => {
    assert.equal(expRequired(input(), 1), 60);
    assert.equal(expRequired(input(), 2), 100);
  });

  it('is what the player has when the content has no more levels', () => {
    const bare = input({ expRequiredByLevel: new Map() });
    assert.equal(expRequired(bare, 1), 4);
  });
});

describe('the HUD\'s state', () => {
  it('reads the resources out of the server\'s answer', () => {
    const state = hudState(input());
    assert.equal(state.gold, 2000);
    assert.equal(state.wood, 2000);
    assert.equal(state.oil, 2000);
    assert.equal(state.steel, 2000);
    assert.equal(state.cash, 50);
    assert.equal(state.energy, 30);
  });

  it('uses the content\'s own storage limits', () => {
    const state = hudState(input());
    assert.equal(state.maxGold, 20000);
    assert.equal(state.maxWood, 20000);
    assert.equal(state.maxOil, 20000);
    assert.equal(state.maxSteel, 20000);
  });

  it('uses the content\'s own energy cap', () => {
    assert.equal(hudState(input()).maxEnergy, 30);
  });

  it('counts the population and the limit', () => {
    const state = hudState(input());
    assert.equal(state.population, 0);
    assert.equal(state.populationMaxCurrent, 23);
    assert.equal(state.populationMaxAllowed, 175);
  });

  it('shows 20 of 20 for a player with only a Command Center', () => {
    const bare = world();
    bare.maps[0]!.items = { '1': [26, 48, 48, 0, 0, 0, 0, 1] };
    const state = hudState(input({ world: bare }));
    assert.equal(state.population, 0);
    assert.equal(state.populationMaxCurrent, 20);
  });

  it('carries the level and the experience', () => {
    const state = hudState(input());
    assert.equal(state.level, 1);
    assert.equal(state.experience, 4);
    assert.equal(state.expRequired, 60);
  });

  it('survives a world that answers nothing', () => {
    const bare = world({ maps: [], resources: {} });
    const state = hudState(input({ world: bare }));
    assert.equal(state.gold, 0);
    assert.equal(state.population, 0);
    assert.equal(state.level, 1);
    assert.equal(state.experience, 0);
  });
});
