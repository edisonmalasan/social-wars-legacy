import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  expRequired,
  hudState,
  levelOf,
  populationLimit,
  populationOf,
  type HudInput,
  type HudRules,
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
  populationByItem: new Map([
    [26, 3],
    [1, 3],
    [932, 0],
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
  it('is the sum of the placed items\' population', () => {
    // The Command Center (3) and the House (3).
    assert.equal(populationOf(world(), CONTENT.populationByItem), 6);
  });

  it('is zero for an empty map', () => {
    const bare = world();
    bare.maps[0]!.items = {};
    assert.equal(populationOf(bare, CONTENT.populationByItem), 0);
  });

  it('grows with the level, and stops at the cap', () => {
    assert.equal(populationLimit(1, RULES), 23);
    assert.equal(populationLimit(10, RULES), 50);
    // The cap: 20 + 3 * level would be more than 175 from level 52.
    assert.equal(populationLimit(52, RULES), 175);
    assert.equal(populationLimit(100, RULES), 175);
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
    assert.equal(state.population, 6);
    assert.equal(state.populationMaxCurrent, 23);
    assert.equal(state.populationMaxAllowed, 175);
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
