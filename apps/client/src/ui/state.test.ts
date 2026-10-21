import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { ContentBundle, ContentItem } from '@swl/content';

import {
  buildItems,
  categories,
  expRequiredByLevel,
  goalList,
  hudInput,
  hudRules,
  populationItems,
  questMinLevels,
  questRanks,
} from './state.ts';
import { QUEST_IDS } from '@swl/rules';

function item(overrides: Partial<ContentItem>): ContentItem {
  return {
    id: 1,
    name: 'House I',
    type: 'b',
    category_id: 1,
    subcategory_id: 11,
    subcat_functional: 0,
    img_name: '',
    attack: 0,
    defense: 0,
    life: 0,
    attack_range: 0,
    attack_interval: 0,
    population: 3,
    cost: 0,
    cost_type: null,
    costs: { w: 30 },
    properties: {},
    best_against: null,
    best_against_mult: 0,
    trains_ids: [],
    upgrades_to: null,
    unit_capacity: 0,
    building_limit_same_id: 0,
    building_limit_same_scf: 0,
    width: 2,
    height: 2,
    min_level: 1,
    display_order: 10,
    build_time: 5,
    clicks_to_build: 1,
    training_time: 0,
    xp: 0,
    activation: 0,
    collect: 0,
    ...overrides,
  } as ContentItem;
}

function bundle(overrides: Partial<ContentBundle> = {}): ContentBundle {
  return {
    items: [],
    levels: [],
    globals: {},
    categories: {},
    ...overrides,
  } as ContentBundle;
}

describe('the HUD\'s rules', () => {
  it('come from the content\'s own globals', () => {
    const rules = hudRules(
      bundle({
        globals: {
          BASE_RESOURCE_LIMITS: { g: 20000, w: 20000, o: 20000, s: 20000 },
          ENERGY_MAX_REGULAR_VALUE: 30,
          START_MAX_POPULATION: 20,
          MAX_POPULATION_CAP: 175,
          MAX_POPULATION_PER_LEVEL: 3,
        },
      }),
    );
    assert.equal(rules.maxEnergy, 30);
    assert.equal(rules.maxPopulationCap, 175);
    assert.equal(rules.baseResourceLimits['g'], 20000);
  });

  it('fall back to the game\'s own numbers when a global is missing', () => {
    const rules = hudRules(bundle());
    assert.equal(rules.maxEnergy, 30);
    assert.equal(rules.startMaxPopulation, 20);
    assert.equal(rules.maxPopulationCap, 175);
    assert.equal(rules.maxPopulationPerLevel, 3);
    assert.deepEqual(rules.baseResourceLimits, {});
  });
});

describe('the content\'s indexes', () => {
  it('know what each item does to the population', () => {
    const map = populationItems(
      bundle({
        items: [
          item({ id: 26, population: 3, properties: { grants_population: 1 } }),
          item({ id: 1001, type: 'u', population: 1 }),
        ],
      }),
    );
    assert.equal(map.get(26)?.population, 3);
    assert.equal(map.get(26)?.grants, true);
    assert.equal(map.get(26)?.type, 'b');
    assert.equal(map.get(1001)?.type, 'u');
    assert.equal(map.get(1001)?.grants, false);
  });

  it('know what each level\'s experience is', () => {
    const map = expRequiredByLevel(
      bundle({
        levels: [
          { index: 1, name: 'Servant', exp_required: 40, reward_type: 's', reward_amount: 250 },
          { index: 2, name: 'Peon', exp_required: 60, reward_type: 's', reward_amount: 250 },
        ],
      }),
    );
    assert.equal(map.get(2), 60);
  });
});

describe('the build menu\'s items', () => {
  it('are the content\'s buildings and units', () => {
    const items = buildItems(
      bundle({
        items: [
          item({ id: 1, name: 'House I', display_order: 10 }),
          item({ id: 1001, name: 'Soldier', type: 'u', display_order: 20 }),
        ],
      }),
    );
    assert.equal(items.length, 2);
    assert.equal(items[0]!.name, 'House I');
    assert.equal(items[0]!.categoryId, 1);
    assert.equal(items[0]!.subcategoryId, 11);
    assert.equal(items[0]!.minLevel, 1);
    assert.deepEqual(items[0]!.costs, { w: 30 });
    assert.equal(items[0]!.buildTime, 5);
    assert.equal(items[1]!.displayOrder, 20);
  });

  it('leave out the things the window does not sell', () => {
    const items = buildItems(bundle({ items: [item({ id: 900, type: 'd' })] }));
    assert.equal(items.length, 0);
  });
});

describe('the categories', () => {
  it('are the content\'s own, with their sub-categories', () => {
    const tabs = categories(
      bundle({
        categories: {
          '1': { id: 1, name: 'Village', sub: [{ id: 11, name: 'Houses', parent: 1 }] },
          '2': { id: 2, name: 'Defense', sub: [] },
        },
      }),
    );
    assert.equal(tabs['1']!.name, 'Village');
    assert.equal(tabs['1']!.sub![0]!.name, 'Houses');
    assert.equal(tabs['2']!.name, 'Defense');
  });

  it('leave out a category that is not one', () => {
    const tabs = categories(bundle({ categories: { '1': { name: 'No id' } } }));
    assert.deepEqual(tabs, {});
  });
});

describe('the player\'s goals', () => {
  it('are the content\'s goals, with the server\'s progress', () => {
    const goals = goalList(
      bundle({
        goals: [
          { id: 100000001, title: 'Build a house', description: '', hint: '', reward: {} },
          { id: 100000002, title: 'Reach level 2', description: '', hint: '', reward: {} },
        ],
      }),
      {
        maps: [],
        resources: {},
        privateState: {
          goalState: {
            visited: { '100000001': true },
            completed: { '100000002': true },
          },
        },
      },
    );
    assert.equal(goals.length, 2);
    assert.equal(goals[0]!.index, 0);
    assert.equal(goals[0]!.title, 'Build a house');
    assert.equal(goals[0]!.visited, true);
    assert.equal(goals[0]!.completed, false);
    assert.equal(goals[1]!.completed, true);
  });

  it('are all unvisited when the server has no goal state', () => {
    const goals = goalList(
      bundle({
        goals: [{ id: 1, title: 'One', description: '', hint: '', reward: {} }],
      }),
      { maps: [], resources: {}, privateState: {} },
    );
    assert.equal(goals[0]!.visited, false);
    assert.equal(goals[0]!.completed, false);
  });
});

describe('the quest progress', () => {
  it('is the map\'s own field', () => {
    const ranks = questRanks({
      maps: [{ id: 0, items: {}, questsRank: { '1': 3, '2': 1 } }],
      resources: {},
      privateState: {},
    });
    assert.deepEqual(ranks, { 1: 3, 2: 1 });
  });

  it('is empty when the map has no ranks', () => {
    assert.deepEqual(questRanks({ maps: [], resources: {}, privateState: {} }), {});
  });

  it('knows the level each quest unlocks at', () => {
    // The global is keyed by the quest's id, and the levels are read by
    // the quest's index.
    const levels = questMinLevels(
      bundle({ globals: { QUESTS_MIN_LEVELS: { '100000021': 40 } } }),
    );
    assert.equal(levels[QUEST_IDS.indexOf('100000021')], 40);
    // The weekly quest is at the front of the list and is not a story
    // quest, so it has no level.
    assert.equal(levels[0], undefined);
  });
});

describe('the HUD\'s input', () => {
  it('is the world and the content', () => {
    const world = {
      maps: [{ id: 0, items: { '1': [26, 48, 48, 0, 0, 0, 0, 1] }, level: 1, xp: 4 }],
      resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 0, e: 30, x: 0, m: 0 },
      privateState: {},
    };
    const input = hudInput(
      bundle({
        items: [item({ id: 26, population: 3 })],
        globals: { ENERGY_MAX_REGULAR_VALUE: 30, BASE_RESOURCE_LIMITS: { g: 20000 } },
      }),
      world,
    );
    assert.equal(input.world, world);
    assert.equal(input.items.get(26)?.population, 3);
    assert.equal(input.rules.maxEnergy, 30);
  });
});
