import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { completeGoal, expand, type WorldSnapshot } from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';

import {
  armyPanel,
  buildingInfo,
  buildItems,
  categories,
  expRequiredByLevel,
  expansionPanel,
  goalList,
  hudInput,
  hudRules,
  infoPanel,
  inventoryItems,
  magicLabPanel,
  populationItems,
  productionPanel,
  questMinLevels,
  questRanks,
  recruitView,
  unitInfoPanel,
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

  it('carry a claim for a drawn, incomplete goal the server has not awarded', () => {
    // A goal the server has not completed is exactly the goal drawn in a
    // slot with a "CLICK HERE!" badge. Its click must still send the
    // claim: the server checks its own progress in awardGoal(), not the
    // client's completed flag. This is the dead-gesture regression.
    const goals = goalList(
      bundle({
        goals: [
          { id: 100000001, title: 'Build a house', description: '', hint: '', reward: {} },
        ],
      }),
      {
        maps: [],
        resources: {},
        privateState: {
          goalState: {
            visited: { '100000001': false },
            completed: {},
            awarded: {},
          },
        },
      },
    );
    assert.equal(goals[0]!.completed, false);
    assert.equal(goals[0]!.visited, false);
    assert.deepEqual(goals[0]!.command, completeGoal(100000001));
  });

  it('do not carry a claim for a goal already awarded locally', () => {
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
            // A completed goal is still claimable until its award has
            // been recorded; re-claiming a paid goal earns a refusal.
            completed: { '100000002': true },
            awarded: { '100000001': true },
          },
        },
      },
    );
    assert.equal(goals[0]!.command, null);
    assert.deepEqual(goals[1]!.command, completeGoal(100000002));
  });

  it('do not carry a claim for a goal with no valid numeric id', () => {
    const goals = goalList(
      bundle({
        goals: [
          { id: Number.NaN, title: 'No id', description: '', hint: '', reward: {} },
          { id: Number.POSITIVE_INFINITY, title: 'No finite id', description: '', hint: '', reward: {} },
        ],
      }),
      { maps: [], resources: {}, privateState: {} },
    );
    assert.equal(goals[0]!.command, null);
    assert.equal(goals[1]!.command, null);
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
    assert.deepEqual(goals[0]!.command, completeGoal(1));
  });
});

describe('the info panel', () => {
  it('is the resource panel of the selected building', () => {
    const panel = infoPanel(
      bundle({
        items: [
          item({ id: 200, name: 'Farm', collect_type: 'w', collect: 5 }),
          item({ id: 201, name: 'House I', collect_type: '', collect: 0 }),
        ],
      }),
      200,
    );
    assert.equal(panel?.kind, 'resource');
    assert.equal(panel?.name, 'Farm');
    assert.equal(panel?.resource, 'w');
    assert.equal(panel?.earns, 5);
  });

  it('is nothing when the building produces nothing', () => {
    const items = bundle({ items: [item({ id: 201, name: 'House I' })] });
    assert.equal(infoPanel(items, 201), null);
    assert.equal(infoPanel(items, null), null);
    assert.equal(infoPanel(items, 9999), null);
  });
});

describe('the unit panel', () => {
  it('is the unit\'s own statistics', () => {
    const panel = unitInfoPanel(
      bundle({
        items: [
          item({
            id: 1001,
            name: 'Worker I',
            type: 'u',
            attack: 6,
            life: 25,
            attack_interval: 35,
            attack_range: 1,
            velocity: 5,
            population: 1,
          }),
        ],
      }),
      1001,
    );
    assert.equal(panel?.kind, 'unit');
    assert.equal(panel?.name, 'Worker I');
    assert.equal(panel?.attack, 6);
    assert.equal(panel?.life, 25);
    assert.equal(panel?.attackInterval, 35);
    assert.equal(panel?.attackRange, 1);
    assert.equal(panel?.velocity, 5);
    assert.equal(panel?.population, 1);
  });

  it('is nothing for a building', () => {
    const items = bundle({ items: [item({ id: 201, name: 'House I' })] });
    assert.equal(unitInfoPanel(items, 201), null);
    assert.equal(unitInfoPanel(items, null), null);
  });
});

describe('the quest progress', () => {
  it('is the player\'s privateState.questsRank field', () => {
    const ranks = questRanks({
      maps: [{ id: 0, items: {} }],
      resources: {},
      privateState: { questsRank: { '1': 3, '2': 1 } },
    });
    assert.deepEqual(ranks, { 1: 3, 2: 1 });
  });

  it('does not read a map-level questsRank, which the server never writes', () => {
    const ranks = questRanks({
      maps: [{ id: 0, items: {}, questsRank: { '1': 3, '2': 1 } }],
      resources: {},
      privateState: {},
    });
    assert.deepEqual(ranks, {});
  });

  it('is empty when the server has no ranks', () => {
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

describe('building management views', () => {
  it('shows a building that produces nothing, so the panel is not empty', () => {
    const b = bundle({ items: [item({ id: 26, name: 'Command Center' })] });
    const w = {
      maps: [{ id: 0, items: { '7': [26, 1, 2, 0, 0, 0, {}, 1] }, level: 1 }],
      resources: {},
      privateState: {},
    } as unknown as WorldSnapshot;
    const view = buildingInfo(b, w, 7, 100);
    assert.equal(view?.name, 'Command Center');
    assert.equal(view?.upgrade, null);
    assert.equal(view?.finish, null);
  });

  it('reads a training queue from the server attribute bag', () => {
    const b = bundle({
      items: [
        item({ id: 50, name: 'Barracks', trains_ids: [1008], training_time: 20 }),
        item({ id: 1008, name: 'Rifleman', type: 'u' }),
      ],
    });
    const w = {
      maps: [{
        id: 0,
        items: { '9': [50, 1, 2, 0, 0, 0, { nu: 1, ts: 80, ui: 1008 }, 1] },
        level: 1,
      }],
      resources: {},
      privateState: {},
    } as unknown as WorldSnapshot;
    const view = recruitView(b, w, 9, 95);
    assert.equal(view?.buildingName, 'Barracks');
    assert.deepEqual(view?.units, [{ itemId: 1008, name: 'Rifleman' }]);
    assert.equal(view?.queue.remainingSeconds, 5);
    assert.equal(view?.queue.readyToTake, false);
  });
});

describe('the production selector', () => {
  const producer = item({
    id: 2,
    name: 'Wood Factory I',
    collect: 100,
    collect_type: 'w',
    properties: { multiCollectable: 1 },
  });
  const bundleWithPeriods = (items: ContentItem[] = [producer]): ContentBundle =>
    bundle({
      items,
      globals: {
        COLLECT_MINUTES: [5, 60, 240, 480],
        COLLECT_MULTIPLIER: [0.25, 1, 2, 3],
      },
    });
  const worldFor = (
    attrs: unknown,
    itemId = 2,
  ): WorldSnapshot =>
    ({
      maps: [{ id: 0, items: { '7': [itemId, 0, 0, 0, 0, [], attrs, 1] } }],
      resources: {},
      privateState: {},
    }) as unknown as WorldSnapshot;

  it('offers the four content periods with their content multipliers', () => {
    const view = productionPanel(
      bundleWithPeriods(),
      worldFor({ cp: 4, lastAccruedAt: 1000 }),
      7,
      1000,
    )!;
    assert.deepEqual(
      view.options.map((option) => [
        option.period,
        option.minutes,
        option.multiplier,
        option.amount,
      ]),
      [
        [1, 5, 0.25, 25],
        [2, 60, 1, 100],
        [3, 240, 2, 200],
        [4, 480, 3, 300],
      ],
    );
    assert.equal(view.period, 4);
    assert.equal(view.options.find((option) => option.active)?.period, 4);
    assert.equal(view.resource, 'w');
  });

  it('predicts the server payout from stored production state, including the peasant bonus', () => {
    const withPeasants = productionPanel(
      bundleWithPeriods(),
      worldFor({ cp: 4, collect: 100, unitsInside: 3, unitCapacity: 5 }),
      7,
      1000,
    )!;
    // 100 + 2 * 100 * 0.2 = 140; floor(140 * 3) = 420.
    assert.equal(withPeasants.options[3]!.amount, 420);

    const stored = productionPanel(
      bundleWithPeriods(),
      worldFor({ cp: 4, collect: 150, unitsInside: 1, unitCapacity: 5 }),
      7,
      1000,
    )!;
    assert.equal(stored.options[3]!.amount, 450);

    const capacityOne = productionPanel(
      bundleWithPeriods(),
      worldFor({ cp: 4, collect: 100, unitsInside: 3, unitCapacity: 1 }),
      7,
      1000,
    )!;
    assert.equal(capacityOne.options[3]!.amount, 300);
  });

  it('counts down from the server timestamp and treats a fresh cycle as due', () => {
    const started = worldFor({ cp: 3, lastAccruedAt: 1000 });
    const early = productionPanel(bundleWithPeriods(), started, 7, 1060)!;
    assert.equal(early.secondsRemaining, 240 * 60 - 60);
    assert.equal(early.due, false);
    const due = productionPanel(bundleWithPeriods(), started, 7, 1000 + 240 * 60)!;
    assert.equal(due.secondsRemaining, 0);
    assert.equal(due.due, true);
    const fresh = productionPanel(bundleWithPeriods(), worldFor({}), 7, 1060)!;
    assert.equal(fresh.startedAt, 0);
    assert.equal(fresh.due, true);
  });

  it('matches the server default until a period has been chosen', () => {
    const view = productionPanel(
      bundleWithPeriods(),
      worldFor({ cp: 0, lastAccruedAt: 0 }),
      7,
      1000,
    )!;
    // buildingState() defaults cp to 1, so the server collects on the 5-minute
    // cycle until the player explicitly chooses a period.
    assert.equal(view.period, 1);
    assert.equal(view.options.find((option) => option.active)?.period, 1);
  });

  it('is null for a building that cannot choose a period', () => {
    const plain = item({ id: 3, name: 'House', collect: 10, collect_type: 'w' });
    const unit = item({
      id: 4,
      type: 'u',
      collect: 10,
      collect_type: 'w',
      properties: { multiCollectable: 1 },
    });
    assert.equal(
      productionPanel(bundleWithPeriods([plain]), worldFor({}, 3), 7, 1000),
      null,
    );
    assert.equal(
      productionPanel(bundleWithPeriods([unit]), worldFor({}, 4), 7, 1000),
      null,
    );
    assert.equal(productionPanel(bundleWithPeriods(), worldFor({}, 2), 99, 1000), null);
  });
});

describe('the inventory panel', () => {
  it('lists the server\'s stored items, named by the content', () => {
    const b = bundle({ items: [item({ id: 1, name: 'House I' })] });
    const w = {
      maps: [{ id: 0, items: {}, store: { '1': 2 } }],
      resources: {},
      privateState: {},
    } as WorldSnapshot;
    assert.deepEqual(inventoryItems(b, w), [
      { itemId: 1, quantity: 2, name: 'House I', type: 'b', categoryId: 1 },
    ]);
  });

  it('is empty when the save has no store', () => {
    const w = {
      maps: [{ id: 0, items: {} }],
      resources: {},
      privateState: {},
    } as WorldSnapshot;
    assert.deepEqual(inventoryItems(bundle(), w), []);
  });
});

describe('the army panel', () => {
  it('bridges the server-owned units and the content names and group types', () => {
    const w = {
      maps: [{ id: 0, items: {}, store: { '1001': 2 } }],
      resources: {},
      privateState: { boughtUnits: [1001] },
    } as WorldSnapshot;
    const content = bundle({
      items: [item({ id: 1001, name: 'Soldier', type: 'u', group_type: 'INFANTRY' })],
    });
    assert.deepEqual(armyPanel(content, w, 0), [
      { itemId: 1001, name: 'Soldier', groupType: 'INFANTRY', available: 2, allowed: true },
    ]);
  });
});

describe('the expansion panel', () => {
  // The four tiles a fresh save owns, as the server sends them.
  const fourOwned = {
    maps: [{ id: 0, items: {}, expansions: [35, 36, 45, 46] }],
    resources: {},
    privateState: {},
  } as WorldSnapshot;
  const prices = (rows: unknown[]): ContentBundle => bundle({ expansionPrices: rows });

  it('prices from the content row at the server-owned ordinal', () => {
    const view = expansionPanel(
      prices([
        { coins: 0, cash: 0 },
        { coins: 0, cash: 0 },
        { coins: 0, cash: 0 },
        { coins: 0, cash: 0 },
        { coins: 2500, cash: 5 },
      ]),
      fourOwned,
    )!;
    assert.equal(view.owned, 4);
    assert.equal(view.coins, 2500);
    assert.equal(view.cash, 5);
  });

  it('uses the first content row when the server owns no tiles yet', () => {
    const view = expansionPanel(
      prices([{ coins: 0, cash: 0 }, { coins: 2500, cash: 5 }]),
      { maps: [{ id: 0, items: {}, expansions: [] }], resources: {}, privateState: {} } as WorldSnapshot,
    )!;
    assert.equal(view.owned, 0);
    assert.equal(view.coins, 0);
    assert.equal(view.cash, 0);
  });

  it('carries an expand command for a deterministic, unowned tile id', () => {
    const view = expansionPanel(
      prices([
        { coins: 0, cash: 0 },
        { coins: 0, cash: 0 },
        { coins: 0, cash: 0 },
        { coins: 0, cash: 0 },
        { coins: 2500, cash: 5 },
      ]),
      fourOwned,
    )!;
    assert.equal(view.tileId, 47);
    assert.deepEqual(view.command, expand(47));
  });

  it('is null when the content has no row at the owned ordinal', () => {
    assert.equal(expansionPanel(prices([{ coins: 0, cash: 0 }]), fourOwned), null);
  });

  it('is null for a present row with a non-finite price, not a fake 0/0', () => {
    const noneOwned = {
      maps: [{ id: 0, items: {}, expansions: [] }],
      resources: {},
      privateState: {},
    } as WorldSnapshot;
    for (const row of [
      { coins: Number.NaN, cash: 5 },
      { coins: 2500, cash: Number.POSITIVE_INFINITY },
      { coins: '2500', cash: 5 },
      { cash: 5 },
    ]) {
      assert.equal(expansionPanel(prices([row]), noneOwned), null, JSON.stringify(row));
    }
  });
});

describe('the Research LAB panel', () => {
  const spells = Array.from({ length: 7 }, (_, i) => ({
    id: i + 1,
    name: `Spell ${i + 1}`,
    description: 'does a thing',
    mana: 10,
    // Deliberately the reverse of the content order to prove the model sorts.
    level: 7 - i,
    gold: 100,
    cash: 5,
    area: [1, 2, 3],
    target: 2,
    imgName: `spell${i + 1}`,
  }));
  const withSpells = bundle({
    magics: spells,
    globals: { MANA_PER_PURCHASE: 5, COST_MANA_CASH: 2, COST_MANA_GOLD: 500 },
  });
  const world7 = {
    maps: [{ id: 0, items: {}, level: 7 }],
    resources: { g: 1000, c: 20, w: 0, o: 0, s: 0, e: 30, x: 0, m: 0 },
    privateState: { mana: 12 },
  } as unknown as WorldSnapshot;

  it('pages the content spells by unlock level and reads the server-owned mana', () => {
    const first = magicLabPanel(withSpells, world7, 0);
    assert.equal(first.pageCount, 2);
    assert.equal(first.items.length, 6);
    assert.deepEqual(first.items.map((entry) => entry.unlockLevel), [1, 2, 3, 4, 5, 6]);
    assert.equal(first.mana, 12);
    assert.equal(first.canNext, true);
    assert.equal(first.canPrev, false);
    const second = magicLabPanel(withSpells, world7, 1);
    assert.equal(second.items.length, 1);
    assert.equal(second.items[0]!.unlockLevel, 7);
  });

  it('hides the gold mana price the wallet cannot pay', () => {
    const view = magicLabPanel(withSpells, world7, 0);
    assert.deepEqual(view.pack, { amount: 5, price: { c: 2, g: 500 } });
    assert.deepEqual(view.canBuyMana, { c: true, g: true });
    const poor = magicLabPanel(withSpells, { ...world7, resources: { ...world7.resources, c: 0, g: 0 } }, 0);
    assert.deepEqual(poor.canBuyMana, { c: false, g: false });
  });
});
