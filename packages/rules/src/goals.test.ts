import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  ACTION_MULTISELECT,
  ACTION_ZOOM,
  CLIENT_ONLY_GOAL_IDS,
  CONFIG_ONLY_GOAL_IDS,
  DEFAULT_GOAL_POLICY,
  GAME_MODE_NORMAL,
  GOALS,
  GOAL_TYPE_COUNTS,
  NUM_ACTIVE_GOALS,
  PLAYER_SELF,
  QUEST_01_BAZOOKA,
  REGISTERED_GOAL_IDS,
  TRANSLATION_ONLY_GOAL_IDS,
  activateGoals,
  activeGoalIds,
  applyGoalEvent,
  awardGoal,
  createGoalState,
  getGoalDefinition,
  goalProgress,
  goalProgressEntry,
  isGoalComplete,
  markVisited,
  type GoalDefinition,
  type GoalPolicy,
  type GoalRuntimeState,
  type GoalWorld,
} from './goals.ts';

/* ------------------------------------------------------------------------- *
 * The machine-readable companion: re/data/goals.json
 * ------------------------------------------------------------------------- */

interface SpecGoal {
  id: number;
  title: string;
  goalType: string;
  steps: number;
  params: Record<string, unknown>;
}

interface Spec {
  goals: SpecGoal[];
  reconciliation: {
    configGoalIds: number;
    clientRegisteredGoalIds: number;
    configOnly: number[];
    clientOnly: number[];
  };
}

/** The repository root, found by walking up to the workspace file. */
function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function loadSpec(): Promise<Spec> {
  const file = path.join(repoRoot(), 're/data/goals.json');
  return JSON.parse(await readFile(file, 'utf8')) as Spec;
}

/* ------------------------------------------------------------------------- *
 * Fixtures
 * ------------------------------------------------------------------------- */

/**
 * The item properties the goals match against.
 *
 * The ids are the real ones from the shipped content bundle
 * (`packages/content/dist/content-bundle.json`): 1 House I, 2 Wood Factory I,
 * 5 Gold Factory I, 18 Market I, 22 Turret I, 23 Wall I, 50 Bunker I,
 * 92 Apple tree (a decoration), 1001 Worker I, 1008 Bazooka, 901 Oil vein,
 * 905 Tree, 910 Steel vein, 914 Gold vein.
 */
const ITEM_PROPERTIES = new Map<number, readonly string[]>([
  [1, ['grants_population']],
  [2, ['depot']],
  [5, ['depot']],
  [18, ['ft_building']],
  [22, ['tower']],
  [23, ['wall']],
  [50, ['bunker']],
  [92, ['decoration']],
  [1001, ['worker']],
  [1008, ['ft_ground', 'human']],
  [901, ['resource']],
  [905, ['resource']],
  [910, ['resource']],
  [914, ['resource']],
]);

function world(overrides: Partial<GoalWorld> = {}): GoalWorld {
  return { itemProperties: ITEM_PROPERTIES, ...overrides };
}

/**
 * A state in which only the given goal is still incomplete, so it is the one
 * goal in the five-goal window that reacts to events.
 */
function onlyActive(goalId: number): GoalRuntimeState {
  const completed: Record<number, boolean> = {};
  for (const definition of GOALS) {
    if (definition.id !== goalId) completed[definition.id] = true;
  }
  return { ...createGoalState(), completed };
}

/** The params of a goal, in the shape the machine-readable spec uses. */
function comparableParams(definition: GoalDefinition): Record<string, unknown> {
  const params = definition.params;
  switch (params.type) {
    case 'GoalBuildId':
      return { itemIds: params.itemIds, updateOnActivate: params.updateOnActivate };
    case 'GoalBuildProperty':
      return { property: params.property, updateOnActivate: params.updateOnActivate };
    case 'GoalCollect':
      return { property: params.property, resource: params.resource };
    case 'GoalPushUnit':
    case 'GoalPopUnit':
      return {
        buildingIds: params.buildingIds,
        buildingProperty: params.buildingProperty,
        unitProperty: params.unitProperty,
      };
    case 'GoalSelectTime':
      return { buildingProperty: params.buildingProperty, resource: params.resource, timeIdx: params.timeIdx };
    case 'GoalAction':
      return { action: params.action };
    case 'GoalAttackPlayer':
      return { numAttacks: params.numAttacks, friends: params.friends, victoryNeeded: params.victoryNeeded };
    case 'GoalMarketTrade':
    case 'GoalAlliesMarketTrade':
      return { trades: params.trades };
    case 'GoalModifyPlayerStats':
      return { stats: params.stats };
    case 'GoalCompleteChapter':
      return { chapterId: params.chapterId, spawnChapter: params.spawnChapter };
    case 'GoalCompleteQuest':
      return { questId: params.questId, minDifficulty: params.minDifficulty, winRequired: params.winRequired };
    case 'GoalVisitNeighbour':
      return { friendIds: params.friendIds };
    case 'GoalDailyBouns':
      return { day: params.day };
    case 'GoalReachPopulation':
      return { population: params.population };
    case 'GoalOpenPopup':
      return { popup: params.popup };
    case 'GoalSocialBuildingOpened':
      return { buildingId: params.buildingId };
    case 'GoalStoreItem':
      return { property: params.property };
    case 'GoalMove':
      return { buildingProperty: params.buildingProperty };
    default:
      return {};
  }
}

/* ------------------------------------------------------------------------- *
 * The goal table
 * ------------------------------------------------------------------------- */

describe('the goal table', () => {
  it('registers exactly the 134 goals the client registers', () => {
    assert.equal(GOALS.length, 134);
    assert.equal(new Set(REGISTERED_GOAL_IDS).size, 134, 'every goal id is unique');
  });

  it('matches the machine-readable spec, in registration order', async () => {
    const spec = await loadSpec();
    assert.equal(spec.goals.length, GOALS.length);

    for (const [index, specGoal] of spec.goals.entries()) {
      const definition = GOALS[index];
      assert.ok(definition, `goal ${specGoal.id} is registered`);
      assert.equal(definition.id, specGoal.id, 'registration order');
      assert.equal(definition.title, specGoal.title, `goal ${specGoal.id}: title`);
      assert.equal(definition.params.type, specGoal.goalType, `goal ${specGoal.id}: type`);
      assert.equal(definition.steps, specGoal.steps, `goal ${specGoal.id}: steps`);

      const params = comparableParams(definition);
      for (const [key, value] of Object.entries(params)) {
        if (value === undefined) continue;
        assert.deepEqual(value, specGoal.params[key], `goal ${specGoal.id}: ${key}`);
      }
    }
  });

  it('reconciles the id space with the config goal table', async () => {
    const spec = await loadSpec();
    assert.equal(spec.reconciliation.clientRegisteredGoalIds, GOALS.length);
    assert.equal(spec.reconciliation.configGoalIds, 91);
    assert.deepEqual(spec.reconciliation.configOnly, [...CONFIG_ONLY_GOAL_IDS]);
    assert.deepEqual(spec.reconciliation.clientOnly, [...CLIENT_ONLY_GOAL_IDS]);

    // The 12 config-only ids are exactly the ids the client never implemented.
    for (const goalId of CONFIG_ONLY_GOAL_IDS) {
      assert.equal(getGoalDefinition(goalId), undefined, `goal ${goalId} is not registered`);
    }
    // The 55 client-only ids are all registered.
    for (const goalId of CLIENT_ONLY_GOAL_IDS) {
      assert.ok(getGoalDefinition(goalId), `goal ${goalId} is registered`);
    }
    // 91 config ids - 12 config-only = 79 shared ids.
    assert.equal(REGISTERED_GOAL_IDS.filter((goalId) => goalId <= 91).length, 79);
  });

  it('has six text-only ids that are never registered', () => {
    assert.equal(TRANSLATION_ONLY_GOAL_IDS.length, 6);
    for (const goalId of TRANSLATION_ONLY_GOAL_IDS) {
      assert.equal(getGoalDefinition(goalId), undefined, `goal ${goalId} is not registered`);
      assert.ok(!CONFIG_ONLY_GOAL_IDS.includes(goalId), `goal ${goalId} is not a config id`);
    }
  });

  it('rewards 10 gold for every goal', () => {
    for (const definition of GOALS) {
      assert.deepEqual(definition.reward, { resource: 'g', amount: 10 }, `goal ${definition.id}`);
    }
  });

  it('registers the same number of goals per type as the client', () => {
    assert.equal(GOAL_TYPE_COUNTS.GoalBuildId, 68);
    assert.equal(GOAL_TYPE_COUNTS.GoalCompleteQuest, 11);
    assert.equal(GOAL_TYPE_COUNTS.GoalCollect, 9);
    assert.equal(GOAL_TYPE_COUNTS.GoalCompleteChapter, 8);
    assert.equal(GOAL_TYPE_COUNTS.GoalPushUnit, 6);
    assert.equal(GOAL_TYPE_COUNTS.GoalBuildProperty, 5);
    assert.equal(GOAL_TYPE_COUNTS.GoalAttackPlayer, 3);
    assert.equal(GOAL_TYPE_COUNTS.GoalMarketTrade, 3);
    assert.equal(GOAL_TYPE_COUNTS.GoalSelectTime, 3);
    assert.equal(GOAL_TYPE_COUNTS.GoalOpenPopup, 2);
    assert.equal(
      Object.values(GOAL_TYPE_COUNTS).filter((count) => count === 1).length,
      16,
      'sixteen types have exactly one goal',
    );
    assert.equal(
      Object.values(GOAL_TYPE_COUNTS).reduce((total, count) => total + count, 0),
      GOALS.length,
    );
  });
});

/* ------------------------------------------------------------------------- *
 * The five-goal window
 * ------------------------------------------------------------------------- */

describe('the five-goal window', () => {
  it('activates the first five registered goals', () => {
    assert.equal(NUM_ACTIVE_GOALS, 5);
    assert.deepEqual([...activeGoalIds(createGoalState())], [1, 18, 6, 8, 20]);
  });

  it('slides forward when a goal completes', () => {
    const result = applyGoalEvent(
      createGoalState(),
      { type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF },
      world(),
    );
    assert.deepEqual(
      result.completions.map((completion) => completion.goalId),
      [1],
    );
    assert.deepEqual([...activeGoalIds(result.state)], [18, 6, 8, 20, 11]);
  });

  it('ignores events for goals outside the window', () => {
    // Goal 23 is registered seventh, so it is not listening yet.
    const collect = { type: 'elemCollected', itemId: 914, collectType: 'g' } as const;
    const first = applyGoalEvent(createGoalState(), collect, world());
    assert.equal(goalProgress(first.state, 23), 0);

    let state = applyGoalEvent(
      first.state,
      { type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF },
      world(),
    ).state;
    state = applyGoalEvent(state, { type: 'elementBuilt', itemId: 2, playerId: PLAYER_SELF }, world()).state;
    assert.ok(activeGoalIds(state).includes(23), 'goal 23 has entered the window');

    const after = applyGoalEvent(state, collect, world());
    assert.equal(goalProgress(after.state, 23), 1);
  });

  it('never keeps more than five goals active', () => {
    let state = createGoalState();
    const completed: number[] = [];
    const step = (event: Parameters<typeof applyGoalEvent>[1]): void => {
      const result = applyGoalEvent(state, event, world());
      state = result.state;
      assert.equal(activeGoalIds(state).length, NUM_ACTIVE_GOALS);
      for (const completion of result.completions) completed.push(completion.goalId);
    };

    // The first five registered goals, completed in order: build a house,
    // build a wood factory, zoom eight times, train two workers and send a
    // worker to the wood factory.
    step({ type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF });
    step({ type: 'elementBuilt', itemId: 2, playerId: PLAYER_SELF });
    for (let i = 0; i < 8; i++) step({ type: 'actionTriggered', action: ACTION_ZOOM });
    step({ type: 'elementBuilt', itemId: 1001, playerId: PLAYER_SELF });
    step({ type: 'elementBuilt', itemId: 1001, playerId: PLAYER_SELF });
    step({
      type: 'unitPushed',
      buildingItemId: 2,
      buildingPlayerId: PLAYER_SELF,
      unitItemId: 1001,
      unitPlayerId: PLAYER_SELF,
    });

    assert.deepEqual(completed, [1, 18, 6, 8, 20]);
    assert.deepEqual([...activeGoalIds(state)], [11, 23, 9, 10, 87]);
  });
});

/* ------------------------------------------------------------------------- *
 * The once-only award
 * ------------------------------------------------------------------------- */

describe('the reward', () => {
  it('is granted exactly once', () => {
    const result = applyGoalEvent(
      createGoalState(),
      { type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF },
      world(),
    );
    assert.deepEqual(result.completions[0]?.reward, { resource: 'g', amount: 10 });

    const first = awardGoal(result.state, 1);
    assert.equal(first.ok, true);
    assert.deepEqual(first.ok ? first.reward : null, { resource: 'g', amount: 10 });

    const second = awardGoal(first.ok ? first.state : result.state, 1);
    assert.equal(second.ok, false);
    assert.equal(second.ok ? '' : second.reason, 'already-awarded');
  });

  it('is refused for a goal that has not completed', () => {
    const result = awardGoal(createGoalState(), 1);
    assert.equal(result.ok, false);
    assert.equal(result.ok ? '' : result.reason, 'not-completed');
  });

  it('is refused for a goal that does not exist', () => {
    const result = awardGoal(createGoalState(), 9999);
    assert.equal(result.ok, false);
    assert.equal(result.ok ? '' : result.reason, 'unknown-goal');
  });

  it('never completes the same goal twice', () => {
    const first = applyGoalEvent(
      createGoalState(),
      { type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF },
      world(),
    );
    const second = applyGoalEvent(
      first.state,
      { type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF },
      world(),
    );
    assert.deepEqual(
      second.completions.filter((completion) => completion.goalId === 1),
      [],
    );
  });
});

/* ------------------------------------------------------------------------- *
 * The goal types
 * ------------------------------------------------------------------------- */

describe('the goal types', () => {
  it('GoalBuildId: counts the elements the player built', () => {
    const state = onlyActive(1);
    const built = applyGoalEvent(state, { type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF }, world());
    assert.equal(goalProgress(built.state, 1), 1);
    assert.deepEqual(
      built.completions.map((completion) => completion.goalId),
      [1],
    );

    const other = applyGoalEvent(state, { type: 'elementBuilt', itemId: 2, playerId: PLAYER_SELF }, world());
    assert.equal(goalProgress(other.state, 1), 0, 'a wood factory is not a house');

    const notMine = applyGoalEvent(state, { type: 'elementBuilt', itemId: 1, playerId: 2 }, world());
    assert.equal(goalProgress(notMine.state, 1), 0, 'the owner has to be the player');
  });

  it('GoalBuildProperty: counts the elements that carry the property', () => {
    const state = onlyActive(8);
    const worker = applyGoalEvent(state, { type: 'elementBuilt', itemId: 1001, playerId: PLAYER_SELF }, world());
    assert.equal(goalProgress(worker.state, 8), 1);

    const house = applyGoalEvent(state, { type: 'elementBuilt', itemId: 1, playerId: PLAYER_SELF }, world());
    assert.equal(goalProgress(house.state, 8), 0);
  });

  it('GoalCollect: matches the property and the collect type', () => {
    const state = onlyActive(23);
    const gold = applyGoalEvent(state, { type: 'elemCollected', itemId: 914, collectType: 'g' }, world());
    assert.equal(goalProgress(gold.state, 23), 1);

    const tree = applyGoalEvent(state, { type: 'elemCollected', itemId: 905, collectType: 'w' }, world());
    assert.equal(goalProgress(tree.state, 23), 0, 'a tree gives wood, not gold');

    const factory = applyGoalEvent(state, { type: 'elemCollected', itemId: 5, collectType: 'g' }, world());
    assert.equal(goalProgress(factory.state, 23), 0, 'a depot is not a resource node');
  });

  it('GoalPushUnit: matches the building and the unit', () => {
    const state = onlyActive(20);
    const pushed = applyGoalEvent(
      state,
      {
        type: 'unitPushed',
        buildingItemId: 2,
        buildingPlayerId: PLAYER_SELF,
        unitItemId: 1001,
        unitPlayerId: PLAYER_SELF,
      },
      world(),
    );
    assert.equal(goalProgress(pushed.state, 20), 1);

    const wrongBuilding = applyGoalEvent(
      state,
      {
        type: 'unitPushed',
        buildingItemId: 5,
        buildingPlayerId: PLAYER_SELF,
        unitItemId: 1001,
        unitPlayerId: PLAYER_SELF,
      },
      world(),
    );
    assert.equal(goalProgress(wrongBuilding.state, 20), 0, 'a gold factory is not a wood factory');

    const wrongUnit = applyGoalEvent(
      state,
      {
        type: 'unitPushed',
        buildingItemId: 2,
        buildingPlayerId: PLAYER_SELF,
        unitItemId: 1008,
        unitPlayerId: PLAYER_SELF,
      },
      world(),
    );
    assert.equal(goalProgress(wrongUnit.state, 20), 0, 'a bazooka is not a worker');

    const notMine = applyGoalEvent(
      state,
      {
        type: 'unitPushed',
        buildingItemId: 2,
        buildingPlayerId: 2,
        unitItemId: 1001,
        unitPlayerId: PLAYER_SELF,
      },
      world(),
    );
    assert.equal(goalProgress(notMine.state, 20), 0, 'the owner has to be the player');
  });

  it('GoalPopUnit: matches the building and the unit', () => {
    const state = onlyActive(13);
    const popped = applyGoalEvent(
      state,
      {
        type: 'unitPopped',
        buildingItemId: 5,
        buildingPlayerId: PLAYER_SELF,
        unitItemId: 1001,
        unitPlayerId: PLAYER_SELF,
      },
      world(),
    );
    assert.equal(goalProgress(popped.state, 13), 1);

    const wrongBuilding = applyGoalEvent(
      state,
      {
        type: 'unitPopped',
        buildingItemId: 2,
        buildingPlayerId: PLAYER_SELF,
        unitItemId: 1001,
        unitPlayerId: PLAYER_SELF,
      },
      world(),
    );
    assert.equal(goalProgress(wrongBuilding.state, 13), 0);
  });

  it('GoalSelectTime: checks the owner, the property, the resource and the slot', () => {
    const state = onlyActive(11);
    const selected = applyGoalEvent(
      state,
      { type: 'timeSelected', itemId: 2, playerId: PLAYER_SELF, collectType: 'w', collectPeriod: 0 },
      world(),
    );
    assert.equal(goalProgress(selected.state, 11), 1);

    const notMine = applyGoalEvent(
      state,
      { type: 'timeSelected', itemId: 2, playerId: 2, collectType: 'w', collectPeriod: 0 },
      world(),
    );
    assert.equal(goalProgress(notMine.state, 11), 0, 'the client checks the owner');

    const wrongResource = applyGoalEvent(
      state,
      { type: 'timeSelected', itemId: 2, playerId: PLAYER_SELF, collectType: 'g', collectPeriod: 0 },
      world(),
    );
    assert.equal(goalProgress(wrongResource.state, 11), 0);

    const wrongSlot = applyGoalEvent(
      state,
      { type: 'timeSelected', itemId: 2, playerId: PLAYER_SELF, collectType: 'w', collectPeriod: -1 },
      world(),
    );
    assert.equal(goalProgress(wrongSlot.state, 11), 0, 'the slot index has to be at least timeIdx');
  });

  it('GoalMarketTrade: needs the requested amount, in the right direction', () => {
    const state = onlyActive(56);
    const half = applyGoalEvent(state, { type: 'marketTrade', volumes: { w: 60 } }, world());
    assert.equal(goalProgress(half.state, 56), 0);

    const rest = applyGoalEvent(half.state, { type: 'marketTrade', volumes: { w: 40 } }, world());
    assert.deepEqual(
      rest.completions.map((completion) => completion.goalId),
      [56],
    );
  });

  it('GoalMarketTrade: a sale does not count towards a purchase', () => {
    const state = onlyActive(56);
    const sold = applyGoalEvent(state, { type: 'marketTrade', volumes: { w: -100 } }, world());
    assert.equal(goalProgress(sold.state, 56), 0);
  });

  it('GoalModifyPlayerStats: needs the delta, in the right direction', () => {
    const state = onlyActive(45);
    const earned = applyGoalEvent(state, { type: 'playerStatsModified', volumes: { c: 5 } }, world());
    assert.equal(goalProgress(earned.state, 45), 0, 'the goal asks the player to *spend* cash');

    const spent = applyGoalEvent(state, { type: 'playerStatsModified', volumes: { c: -1 } }, world());
    assert.deepEqual(
      spent.completions.map((completion) => completion.goalId),
      [45],
    );
  });

  it('GoalAttackPlayer: skips aborted assaults and losses', () => {
    const state = onlyActive(65);
    const aborted = applyGoalEvent(
      state,
      { type: 'attackEnd', win: true, opponentId: 'a', voluntary: true },
      world(),
    );
    assert.equal(goalProgress(aborted.state, 65), 0, 'an assault the player aborted never counts');

    const lost = applyGoalEvent(
      state,
      { type: 'attackEnd', win: false, opponentId: 'a', voluntary: false },
      world(),
    );
    assert.equal(goalProgress(lost.state, 65), 0, 'this goal needs a victory');

    const won = applyGoalEvent(
      state,
      { type: 'attackEnd', win: true, opponentId: 'a', voluntary: false },
      world(),
    );
    assert.equal(goalProgress(won.state, 65), 1);
  });

  it('GoalAttackPlayer: the friend goal only counts friends', () => {
    const state = onlyActive(57);
    const stranger = applyGoalEvent(
      state,
      { type: 'attackEnd', win: true, opponentId: 'someone-else', voluntary: false },
      world(),
    );
    assert.equal(goalProgress(stranger.state, 57), 0);

    const friend = applyGoalEvent(
      state,
      { type: 'attackEnd', win: true, opponentId: 'friend-1', voluntary: false },
      world({ friendIds: ['friend-1'] }),
    );
    assert.deepEqual(
      friend.completions.map((completion) => completion.goalId),
      [57],
    );
  });

  it('GoalCompleteQuest: matches the quest, the win and the difficulty', () => {
    const state = onlyActive(110);
    const other = applyGoalEvent(
      state,
      { type: 'questEnd', questId: '100000002', win: true, difficulty: 1 },
      world(),
    );
    assert.equal(goalProgress(other.state, 110), 0);

    const lost = applyGoalEvent(
      state,
      { type: 'questEnd', questId: '100000006', win: false, difficulty: 1 },
      world(),
    );
    assert.equal(goalProgress(lost.state, 110), 0, 'the goal requires a win');

    const won = applyGoalEvent(
      state,
      { type: 'questEnd', questId: '100000006', win: true, difficulty: 1 },
      world(),
    );
    assert.deepEqual(
      won.completions.map((completion) => completion.goalId),
      [110],
    );
  });

  it('GoalCompleteChapter: matches the chapter the goal is bound to', () => {
    const state = onlyActive(17);
    const other = applyGoalEvent(state, { type: 'chapterFinished', chapterId: 2 }, world());
    assert.equal(goalProgress(other.state, 17), 0);

    const right = applyGoalEvent(state, { type: 'chapterFinished', chapterId: 1 }, world());
    assert.deepEqual(
      right.completions.map((completion) => completion.goalId),
      [17],
    );
  });

  it('GoalReachPopulation: tracks the absolute population, in the normal game mode only', () => {
    const state = onlyActive(49);
    const visiting = applyGoalEvent(
      state,
      { type: 'populationModified', population: 50, gameMode: 2 },
      world(),
    );
    assert.equal(goalProgress(visiting.state, 49), 0, 'only GAME_MODE_NORMAL counts');

    const normal = applyGoalEvent(
      state,
      { type: 'populationModified', population: 39, gameMode: GAME_MODE_NORMAL },
      world(),
    );
    assert.equal(goalProgress(normal.state, 49), 39);

    const reached = applyGoalEvent(
      state,
      { type: 'populationModified', population: 40, gameMode: GAME_MODE_NORMAL },
      world(),
    );
    assert.deepEqual(
      reached.completions.map((completion) => completion.goalId),
      [49],
    );
  });

  it('GoalVisitNeighbour: only the listed friends count', () => {
    const state = onlyActive(40);
    const other = applyGoalEvent(state, { type: 'neighbourVisited', friendId: '999' }, world());
    assert.equal(goalProgress(other.state, 40), 0);

    const general = applyGoalEvent(state, { type: 'neighbourVisited', friendId: '100000030' }, world());
    assert.deepEqual(
      general.completions.map((completion) => completion.goalId),
      [40],
    );
  });

  it('GoalAction: counts only the matching action', () => {
    const state = onlyActive(6);
    const multi = applyGoalEvent(state, { type: 'actionTriggered', action: ACTION_MULTISELECT }, world());
    assert.equal(goalProgress(multi.state, 6), 0);

    const zoom = applyGoalEvent(state, { type: 'actionTriggered', action: ACTION_ZOOM }, world());
    assert.equal(goalProgress(zoom.state, 6), 1);
  });

  it('GoalExpand: counts bought tiles', () => {
    const state = onlyActive(63);
    const result = applyGoalEvent(state, { type: 'tilePurchased' }, world());
    assert.deepEqual(
      result.completions.map((completion) => completion.goalId),
      [63],
    );
  });

  it('GoalDoubleClick: counts double-clicks', () => {
    const state = onlyActive(16);
    const result = applyGoalEvent(state, { type: 'doubleClick' }, world());
    assert.deepEqual(
      result.completions.map((completion) => completion.goalId),
      [16],
    );
  });

  it('GoalAssistNeighbourBuilding: counts assists', () => {
    const state = onlyActive(81);
    const result = applyGoalEvent(state, { type: 'neighbourBuildingAssisted' }, world());
    assert.equal(goalProgress(result.state, 81), 1);
  });

  it('GoalStoreItem: matches the property of the stored item', () => {
    const state = onlyActive(60);
    const stored = applyGoalEvent(state, { type: 'itemStored', itemId: 92 }, world());
    assert.deepEqual(
      stored.completions.map((completion) => completion.goalId),
      [60],
    );

    const notADecoration = applyGoalEvent(state, { type: 'itemStored', itemId: 1 }, world());
    assert.equal(goalProgress(notADecoration.state, 60), 0);
  });

  it('GoalSocialBuildingOpened: matches the building id', () => {
    const state = onlyActive(71);
    const other = applyGoalEvent(state, { type: 'socialBuildingOpened', itemId: 74 }, world());
    assert.equal(goalProgress(other.state, 71), 0);

    const allies = applyGoalEvent(state, { type: 'socialBuildingOpened', itemId: 61 }, world());
    assert.deepEqual(
      allies.completions.map((completion) => completion.goalId),
      [71],
    );
  });

  it('GoalOpenPopup: matches the popup class', () => {
    const state = onlyActive(47);
    const other = applyGoalEvent(state, { type: 'popupOpened', popup: 'PopupAssaultHistory' }, world());
    assert.equal(goalProgress(other.state, 47), 0);

    const inventory = applyGoalEvent(state, { type: 'popupOpened', popup: 'PopupInventory' }, world());
    assert.deepEqual(
      inventory.completions.map((completion) => completion.goalId),
      [47],
    );
  });

  it('GoalSpy: counts completed spy operations', () => {
    const state = onlyActive(64);
    const result = applyGoalEvent(state, { type: 'spyEnd' }, world());
    assert.deepEqual(
      result.completions.map((completion) => completion.goalId),
      [64],
    );
  });

  it('GoalMove: matches the owner and the property', () => {
    const state = onlyActive(32);
    const moved = applyGoalEvent(state, { type: 'buildingMoved', itemId: 23, playerId: PLAYER_SELF }, world());
    assert.deepEqual(
      moved.completions.map((completion) => completion.goalId),
      [32],
    );

    const notAWall = applyGoalEvent(state, { type: 'buildingMoved', itemId: 1, playerId: PLAYER_SELF }, world());
    assert.equal(goalProgress(notAWall.state, 32), 0);

    const notMine = applyGoalEvent(state, { type: 'buildingMoved', itemId: 23, playerId: 2 }, world());
    assert.equal(goalProgress(notMine.state, 32), 0);
  });

  it('GoalAddAllies: completes when the goal-info popup is closed', () => {
    const state = onlyActive(85);
    const result = applyGoalEvent(state, { type: 'goalPopupClosed' }, world());
    assert.deepEqual(
      result.completions.map((completion) => completion.goalId),
      [85],
    );
  });
});

/* ------------------------------------------------------------------------- *
 * Activation
 * ------------------------------------------------------------------------- */

describe('activation', () => {
  it('sweeps the buildings already on the map when the goal wants a depot', () => {
    // Goal 18 wants a wood factory, which is a depot, so it re-scans the map
    // even though the flag is false (core/goals/GoalBuildId.as:48-55).
    const activated = activateGoals(onlyActive(18), world({ playerBuildings: [2, 2, 1] }));
    assert.equal(goalProgress(activated.state, 18), 2);
    assert.deepEqual(
      activated.completions.map((completion) => completion.goalId),
      [18],
    );
  });

  it('does not sweep a goal whose items are neither a depot nor an HQ', () => {
    const activated = activateGoals(onlyActive(1), world({ playerBuildings: [1, 1, 1] }));
    assert.equal(goalProgress(activated.state, 1), 0);
  });

  it('sweeps a goal that asks for it explicitly', () => {
    const activated = activateGoals(onlyActive(44), world({ playerBuildings: [18] }));
    assert.equal(goalProgress(activated.state, 44), 1);
  });

  it('sweeps only once, however often the goals are activated', () => {
    const activated = activateGoals(onlyActive(18), world({ playerBuildings: [2] }));
    const again = activateGoals(activated.state, world({ playerBuildings: [2] }));
    assert.equal(goalProgress(again.state, 18), 1);
  });

  it('completes a chapter goal whose chapter is behind the player', () => {
    const activated = activateGoals(onlyActive(17), world({ currentQuestId: 3 }));
    assert.deepEqual(
      activated.completions.map((completion) => completion.goalId),
      [17],
    );
  });

  it('completes a quest goal whose quest is already finished', () => {
    const activated = activateGoals(onlyActive(110), world({ completedQuests: new Set(['100000006']) }));
    assert.deepEqual(
      activated.completions.map((completion) => completion.goalId),
      [110],
    );
  });

  it('completes the harbour goal when its quest is already finished', () => {
    const activated = activateGoals(onlyActive(26), world({ completedQuests: new Set([QUEST_01_BAZOOKA]) }));
    assert.deepEqual(
      activated.completions.map((completion) => completion.goalId),
      [26],
    );
  });

  it('seeds the daily-bonus goal at one claim', () => {
    const activated = activateGoals(onlyActive(48), world());
    assert.equal(goalProgress(activated.state, 48), 1);

    const claim = applyGoalEvent(onlyActive(48), { type: 'dailyBonusWon' }, world());
    assert.equal(goalProgress(claim.state, 48), 2);
  });
});

/* ------------------------------------------------------------------------- *
 * The client defects
 * ------------------------------------------------------------------------- */

describe('the client defects', () => {
  it('fixes the allies-market defect: the goal needs the requested amount', () => {
    const state = onlyActive(84);
    const first = applyGoalEvent(state, { type: 'alliesMarketTrade', volumes: { w: 10 } }, world());
    assert.equal(goalProgress(first.state, 84), 0, '10 wood is not the 500 the goal asks for');
    assert.deepEqual(first.completions, []);

    let next = first.state;
    for (let i = 0; i < 49; i++) {
      next = applyGoalEvent(next, { type: 'alliesMarketTrade', volumes: { w: 10 } }, world()).state;
    }
    assert.equal(goalProgress(next, 84), 1);
    assert.ok(isGoalComplete(next, 84));
  });

  it('reproduces the allies-market defect when the policy asks for it', () => {
    const legacy: GoalPolicy = { ...DEFAULT_GOAL_POLICY, alliesMarketTradeCompletesOnFirstCollect: true };
    const result = applyGoalEvent(
      onlyActive(84),
      { type: 'alliesMarketTrade', volumes: { w: 1 } },
      world(),
      legacy,
    );
    assert.deepEqual(
      result.completions.map((completion) => completion.goalId),
      [84],
    );
  });

  it('fixes the harbour defect: only its own quest completes it', () => {
    const state = onlyActive(26);
    const other = applyGoalEvent(
      state,
      { type: 'questEnd', questId: '100000002', win: true, difficulty: 1 },
      world(),
    );
    assert.equal(goalProgress(other.state, 26), 0);

    const right = applyGoalEvent(
      state,
      { type: 'questEnd', questId: QUEST_01_BAZOOKA, win: true, difficulty: 1 },
      world(),
    );
    assert.deepEqual(
      right.completions.map((completion) => completion.goalId),
      [26],
    );
  });

  it('reproduces the harbour defect when the policy asks for it', () => {
    const legacy: GoalPolicy = { ...DEFAULT_GOAL_POLICY, harborCompletesOnAnyQuest: true };
    const result = applyGoalEvent(
      onlyActive(26),
      { type: 'questEnd', questId: '100000002', win: true, difficulty: 1 },
      world(),
      legacy,
    );
    assert.deepEqual(
      result.completions.map((completion) => completion.goalId),
      [26],
    );
  });

  it('keeps the chapter goals bound to the chapter key, not to the text', () => {
    // Defect 5: the text of goal 130 says "CHAPTER 9" but the goal is bound to
    // CHAPTER_05_SIEGE_CONVENTIONAL. The code wins.
    const definition = getGoalDefinition(130);
    assert.ok(definition);
    assert.equal(definition.params.type, 'GoalCompleteChapter');
    assert.equal(definition.params.type === 'GoalCompleteChapter' ? definition.params.chapterId : 0, 5);
    assert.match(definition.title, /CHAPTER 9/);
  });
});

/* ------------------------------------------------------------------------- *
 * The wire payload
 * ------------------------------------------------------------------------- */

describe('the set_goals payload', () => {
  it('is [visited, currentStep]', () => {
    let state = markVisited(createGoalState(), 6);
    state = applyGoalEvent(state, { type: 'actionTriggered', action: ACTION_ZOOM }, world()).state;
    assert.deepEqual(goalProgressEntry(state, 6), [1, 1]);
  });

  it('is [0, 0] for a goal that was never touched', () => {
    assert.deepEqual(goalProgressEntry(createGoalState(), 1), [0, 0]);
  });
});
