import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Random } from './random.ts';
import {
  QUESTS,
  QUEST_IDS,
  QUEST_ID_01_BAZOOKA,
  QUEST_ID_02_CENTRAL_NUCLEAR,
  QUEST_ID_03_DEFEND_CONVOY_AUTO,
  QUEST_ID_04_SUPERTANK,
  QUEST_ID_05_ASSAULT_CONVOY,
  QUEST_ID_06_AIRSTRIKE,
  QUEST_ID_07_SHIP,
  QUEST_ID_08_ROCKET,
  QUEST_ID_09_LABORATORIES,
  QUEST_ID_10_SPECIAL_OPS,
  QUEST_ID_13_TYRANNOSAURUS,
  QUEST_ID_15_HARDCORE1,
  QUEST_ID_22_HARDCORE9,
  QUEST_ID_23_HARDCORE10,
  QUEST_ID_WEEKLY_01,
  GROUP_TYPE_AIR_VEHICLE,
  LABORATORY_REFS,
  NUM_STORY_QUESTS,
  WEEKLY_CASH_PER_BOT,
  addQuestCounter,
  advanceSimpleChapter,
  applyQuestVar,
  awardQuest,
  chapterObjectivesComplete,
  clampQuestXp,
  createEmptyChapterStatus,
  defendersClearedQuestElement,
  difficultyEnemyCopies,
  emptyQuestProgress,
  finishQuest,
  getQuestSpec,
  isQuestDefeat,
  isQuestVictory,
  isUnitAllowedInQuest,
  killQuestElement,
  loadQuestMap,
  nearDeathQuestElement,
  prepareChapterStatus,
  prepareQuest,
  questConstantName,
  questPlayIndex,
  questRewards,
  questTitle,
  questVarCommand,
  recoverQuestUnits,
  recordActivatorCollected,
  recordChapterElementKilled,
  recordTreasureCollected,
  scaleEnemyRoster,
  setQuestCounter,
  setQuestDifficulty,
  startQuest,
  suppressQuestKills,
  tickQuest,
  type QuestElement,
  type QuestState,
} from './quest.ts';

/** A player unit that is worth 5 gold and 1 XP when it dies. */
function enemyUnit(ref: string, itemId = 1122): QuestElement {
  return { itemId, ref, affiliation: 'enemy', isUnit: true, attack: 10 };
}

/** A friendly unit. */
function friendlyUnit(ref: string, itemId = 1008): QuestElement {
  return { itemId, ref, affiliation: 'self', isUnit: true, attack: 10 };
}

/** A quest that is already under way, with a ten-unit army. */
function running(questId: string): QuestState {
  return startQuest(
    prepareQuest(questId, { army: [{ unitId: 1008, count: 10 }] }),
  );
}

describe('the quest catalogue', () => {
  it('reproduces the client play order', () => {
    assert.deepEqual(
      [...QUEST_IDS],
      [
        '100000049',
        '100000001',
        '100000006',
        '100000003',
        '100000004',
        '100000005',
        '100000002',
        '100000007',
        '100000008',
        '100000009',
        '100000010',
        '100000011',
        '100000012',
        '100000013',
        '100000014',
        '100000017',
        '100000018',
        '100000019',
        '100000020',
        '100000021',
        '100000022',
        '100000026',
        '100000025',
      ],
    );
    // `Quest.numQuests` is `questIds.length - 1`: the weekly quest is index 0
    // and is not counted (quest/Quest.as:239-243).
    assert.equal(NUM_STORY_QUESTS, 22);
  });

  it('keeps the catalogue, the play order and the reward row in step', () => {
    assert.equal(QUESTS.length, QUEST_IDS.length);
    QUEST_IDS.forEach((id, index) => {
      const quest = getQuestSpec(id);
      assert.ok(quest, `missing quest ${id}`);
      assert.equal(quest.id, id);
      // The index is the reward-table index and the rank key.
      assert.equal(quest.playIndex, index);
      assert.equal(questPlayIndex(id), index);
    });
  });

  it('maps every quest id to the client constant name', () => {
    assert.equal(questConstantName(QUEST_ID_01_BAZOOKA), 'QUEST_01_BAZOOKA');
    assert.equal(questConstantName(QUEST_ID_02_CENTRAL_NUCLEAR), 'QUEST_02_CENTRAL_NUCLEAR');
    assert.equal(questConstantName(QUEST_ID_WEEKLY_01), 'QUEST_WEEKLY_01');
  });

  it('keeps the names the upstream constants.py loses to its duplicate keys', () => {
    // `upstream/socialwarriors/constants.py` lists 100000024, 100000025 and
    // 100000026 twice; Python keeps the last occurrence and reports
    // "QUEST: ISLA_RUBEN3D", "QUEST: ISLA_KASPAR" and "QUEST: ISLA_EGG2".
    // The client mapping is the correct one (re/docs/12-quest-system.md §1.2).
    assert.equal(questConstantName(QUEST_ID_22_HARDCORE9), 'QUEST_22_HARDCORE9');
    assert.equal(questConstantName(QUEST_ID_23_HARDCORE10), 'QUEST_23_HARDCORE10');
    assert.equal(getQuestSpec(QUEST_ID_22_HARDCORE9)?.className, 'Quest23HC');
    assert.equal(getQuestSpec(QUEST_ID_23_HARDCORE10)?.className, 'Quest24HC');
    // The map ids corroborate the mapping.
    assert.equal(getQuestSpec(QUEST_ID_22_HARDCORE9)?.mapId, 126);
    assert.equal(getQuestSpec(QUEST_ID_23_HARDCORE10)?.mapId, 125);
  });

  it('gives every quest but the weekly a static gold reward', () => {
    for (const quest of QUESTS) {
      if (quest.id === QUEST_ID_WEEKLY_01) {
        assert.deepEqual(quest.reward, {}, 'the weekly quest has no static row');
        continue;
      }
      assert.ok((quest.reward.g ?? 0) > 0, `${quest.id} has no gold reward`);
    }
  });

  it('keeps the static reward rows monotonic in gold', () => {
    // The rows are positional in the client; pinning them by id must not
    // change their order (re/docs/12-quest-system.md §1.2).
    const golds = QUESTS.map((quest) => quest.reward.g ?? 0);
    for (let index = 1; index < golds.length; index += 1) {
      assert.ok(
        (golds[index] ?? 0) >= (golds[index - 1] ?? 0),
        `reward row ${index} is not monotonic`,
      );
    }
    assert.equal(golds[1], 1500);
    assert.equal(golds[22], 24000);
  });

  it('carries the display title of every quest', () => {
    assert.equal(questTitle(QUEST_ID_01_BAZOOKA), 'DEFEAT THE ENEMY');
    assert.equal(questTitle(QUEST_ID_07_SHIP), 'V.I.P ENEMY');
    assert.equal(questTitle(QUEST_ID_WEEKLY_01), 'Weekly Mission!');
    assert.equal(questTitle(QUEST_ID_15_HARDCORE1), 'VIKINGS BEACHHEAD');
  });
});

describe('the quest lifecycle', () => {
  it('moves through prepared, started and map-loaded', () => {
    const prepared = prepareQuest(QUEST_ID_01_BAZOOKA, {
      army: [{ unitId: 1008, count: 4 }],
    });
    assert.equal(prepared.phase, 'prepared');
    assert.equal(prepared.playerUnitsAlive, 4);
    assert.equal(prepared.gold, 0);
    assert.equal(prepared.xp, 0);

    const started = startQuest(prepared);
    assert.equal(started.phase, 'started');

    const loaded = loadQuestMap(started, [
      friendlyUnit('item:1008'),
      enemyUnit('item:1122'),
      enemyUnit('item:1123'),
    ]);
    assert.equal(loaded.phase, 'map-loaded');
    // The four-unit army plus the one friendly unit that stands on the map.
    assert.equal(loaded.playerUnitsAlive, 5);
    assert.equal(loaded.remainingFoes, 2);
  });

  it('marks the chapter visited when the player already has a rank', () => {
    const first = prepareQuest(QUEST_ID_01_BAZOOKA, { hasRank: true });
    assert.equal(first.chapter.visited, true);
    const fresh = prepareQuest(QUEST_ID_01_BAZOOKA);
    assert.equal(fresh.chapter.visited, false);
    // The quest's chapter is `new Chapter(-1)` (quest/AbstractQuest.as:97).
    assert.equal(fresh.chapter.id, -1);
  });

  it('starts the mission timer when the quest starts', () => {
    const prepared = prepareQuest(QUEST_ID_05_ASSAULT_CONVOY);
    assert.equal(prepared.timeRemaining, null);
    const started = startQuest(prepared);
    assert.equal(started.timeRemaining, 120);
  });

  it('arms the weekly quest timer in prepareInit', () => {
    // The weekly countdown is created in prepareInit, before the map loads
    // (quest/QuestWeekly01.as:83-86).
    const prepared = prepareQuest(QUEST_ID_WEEKLY_01);
    assert.equal(prepared.timeRemaining, 90);
    assert.equal(startQuest(prepared).timeRemaining, 90);
  });

  it('gives the player its own army in the weekly quest', () => {
    const weekly = prepareQuest(QUEST_ID_WEEKLY_01, {
      army: [{ unitId: 1008, count: 25 }],
    });
    // The player's army is discarded and the quest spawns four units.
    assert.equal(weekly.playerUnitsAlive, 4);
  });

  it('duplicates the enemies once per difficulty star', () => {
    assert.equal(difficultyEnemyCopies(QUEST_ID_15_HARDCORE1, 1), 0);
    assert.equal(difficultyEnemyCopies(QUEST_ID_15_HARDCORE1, 2), 1);
    assert.equal(difficultyEnemyCopies(QUEST_ID_15_HARDCORE1, 3), 2);

    const enemies = [
      { unitId: 1122, tile: { x: 1, y: 2 } },
      { unitId: 1123, tile: { x: 3, y: 4 } },
    ];
    const scaled = scaleEnemyRoster(QUEST_ID_15_HARDCORE1, 3, enemies);
    assert.equal(scaled.copiesPerEnemy, 2);
    assert.equal(scaled.copies.length, 4);
    assert.equal(scaleEnemyRoster(QUEST_ID_15_HARDCORE1, 1, enemies).copies.length, 0);
  });

  it('makes the difficulty a no-op in the dinosaur quest', () => {
    // Quest13Tyrannosaurus overrides the setter with a no-op
    // (quest/Quest13Tyrannosaurus.as:239-247).
    assert.equal(difficultyEnemyCopies(QUEST_ID_13_TYRANNOSAURUS, 2), 0);
    assert.equal(difficultyEnemyCopies(QUEST_ID_13_TYRANNOSAURUS, 3), 0);
    assert.equal(getQuestSpec(QUEST_ID_13_TYRANNOSAURUS)?.difficultyIsNoOp, true);
  });

  it('records the chosen difficulty on the state', () => {
    const prepared = prepareQuest(QUEST_ID_15_HARDCORE1);
    assert.equal(prepared.difficulty, 1);
    const chosen = setQuestDifficulty(prepared, 3);
    assert.equal(chosen.difficulty, 3);
    assert.equal(chosen.questId, QUEST_ID_15_HARDCORE1);
  });

  it('excludes air vehicles only from the three quests that say so', () => {
    for (const quest of QUESTS) {
      const excludes = quest.excludedUnitGroupTypes.includes(GROUP_TYPE_AIR_VEHICLE);
      assert.equal(
        excludes,
        quest.id === QUEST_ID_07_SHIP ||
          quest.id === QUEST_ID_08_ROCKET ||
          quest.id === QUEST_ID_09_LABORATORIES,
        `${quest.id} filters the army unexpectedly`,
      );
    }
    const ship = getQuestSpec(QUEST_ID_07_SHIP)!;
    assert.equal(isUnitAllowedInQuest(GROUP_TYPE_AIR_VEHICLE, ship), false);
    assert.equal(isUnitAllowedInQuest('LAND_VEHICLE', ship), true);
    // The convoy quest only *claims* the restriction in its description.
    const convoy = getQuestSpec(QUEST_ID_03_DEFEND_CONVOY_AUTO)!;
    assert.equal(isUnitAllowedInQuest(GROUP_TYPE_AIR_VEHICLE, convoy), true);
  });
});

describe('the weekly quest', () => {
  it('is won when the fifth gun bot dies', () => {
    let state = running(QUEST_ID_WEEKLY_01);
    for (let bot = 1; bot <= 4; bot += 1) {
      const killed = killQuestElement(state, enemyUnit('item:1061', 1061));
      state = addQuestCounter(killed.state, 'botsKilled', 1);
      assert.equal(isQuestVictory(state), false, `won after only ${bot} bots`);
    }
    const killed = killQuestElement(state, enemyUnit('item:1061', 1061));
    state = addQuestCounter(killed.state, 'botsKilled', 1);
    assert.equal(state.script.counters['botsKilled'], 5);
    assert.equal(isQuestVictory(state), true);
  });

  it('is lost when the 90 second timer expires', () => {
    const state = running(QUEST_ID_WEEKLY_01);
    const expired = tickQuest(state, 90);
    assert.equal(expired.timeRemaining, 0);
    assert.equal(expired.result, 'loss');
    assert.equal(isQuestDefeat(expired), true);
  });

  it('is lost when the player army is wiped out', () => {
    let state = running(QUEST_ID_WEEKLY_01);
    state = addQuestCounter(state, 'questUnitsAlive', -4);
    assert.equal(state.script.counters['questUnitsAlive'], 0);
    assert.equal(isQuestDefeat(state), true);
  });

  it('pays one cash per gun bot killed', () => {
    let state = running(QUEST_ID_WEEKLY_01);
    for (let bot = 0; bot < 5; bot += 1) {
      const killed = killQuestElement(state, enemyUnit('item:1061', 1061));
      state = addQuestCounter(killed.state, 'botsKilled', 1);
    }
    const outcome = finishQuest(state, true, { expRequired: 100 });
    assert.equal(outcome.weeklyReason, 'allBotsKilled');
    const cash = outcome.rewards.find((reward) => reward.key === 'c');
    assert.equal(cash?.amount, 5 * WEEKLY_CASH_PER_BOT);
    // The static row of the weekly quest is empty.
    assert.deepEqual(getQuestSpec(QUEST_ID_WEEKLY_01)?.reward, {});
  });
});

describe('a story quest', () => {
  it('is won by taking the ship and destroying the command centre', () => {
    let state = running(QUEST_ID_07_SHIP);
    state = defendersClearedQuestElement(state, 'harbour');
    // Taking the ship alone is not the win.
    assert.equal(isQuestVictory(state), false);

    const killed = killQuestElement(state, {
      itemId: 195,
      ref: 'commandCenter',
      affiliation: 'enemy',
      isUnit: false,
      attack: 0,
    });
    state = killed.state;
    assert.equal(isQuestVictory(state), true);
    assert.equal(isQuestDefeat(state), false);
  });

  it('is lost when the ship is destroyed', () => {
    let state = running(QUEST_ID_07_SHIP);
    state = defendersClearedQuestElement(state, 'harbour');
    const killed = killQuestElement(state, {
      itemId: 1019,
      ref: 'ship',
      affiliation: 'neutral',
      isUnit: true,
    });
    state = killed.state;
    // The ship is a key element: destroying it calls defeat().
    assert.equal(state.result, 'loss');
    assert.equal(isQuestDefeat(state), true);
  });

  it('is won when three trucks reach the exit', () => {
    let state = running(QUEST_ID_03_DEFEND_CONVOY_AUTO);
    state = addQuestCounter(state, 'trucksArrived', 2);
    assert.equal(isQuestVictory(state), false);
    state = addQuestCounter(state, 'trucksArrived', 1);
    assert.equal(isQuestVictory(state), true);
  });

  it('is lost when a convoy truck is destroyed', () => {
    let state = running(QUEST_ID_03_DEFEND_CONVOY_AUTO);
    const killed = killQuestElement(state, {
      itemId: 1013,
      ref: 'item:1013',
      affiliation: 'self',
      isUnit: true,
    });
    state = killed.state;
    assert.equal(state.result, 'loss');
    assert.equal(isQuestDefeat(state), true);
  });

  it('does not lose a quest with key elements when the army is wiped out', () => {
    // `AbstractQuest.prepareQuestEnd` returns early when `keyIds` is not
    // empty and `alwaysEndIfMyUnitsDie` is false
    // (quest/AbstractQuest.as:284-304).
    let state = prepareQuest(QUEST_ID_01_BAZOOKA, { army: [{ unitId: 1008, count: 1 }] });
    const killed = killQuestElement(state, friendlyUnit('item:1008'));
    state = killed.state;
    assert.equal(state.playerUnitsAlive, 0);
    assert.equal(state.armyWipedOut, true);
    assert.equal(state.result, null);
    assert.equal(isQuestDefeat(state), false);
    assert.equal(state.lossArmedAt, null);
  });

  it('does lose a quest that sets alwaysEndIfMyUnitsDie', () => {
    // Only Quest07Ship sets it (quest/Quest07Ship.as:178).
    let state = prepareQuest(QUEST_ID_07_SHIP, { army: [{ unitId: 1008, count: 1 }] });
    const killed = killQuestElement(state, friendlyUnit('item:1008'));
    state = killed.state;
    assert.equal(isQuestDefeat(state), true);
    // The client's loss runs on a 3-second timer.
    assert.equal(state.lossArmedAt, 3);
    const expired = tickQuest(state, 3);
    assert.equal(expired.result, 'loss');
  });

  it('wins the nuclear quest by destroying the command centre alone', () => {
    // The spec claims a strict order (plant first). The client has no such
    // gate: the plant's onKill only turns the towers off
    // (quest/Quest02CentralNuclear.as:156-165, 178-196).
    let state = running(QUEST_ID_02_CENTRAL_NUCLEAR);
    assert.equal(isQuestVictory(state), false);
    const killed = killQuestElement(state, {
      itemId: 195,
      ref: 'commandCenter',
      affiliation: 'enemy',
      isUnit: false,
      attack: 0,
    });
    assert.equal(isQuestVictory(killed.state), true);
  });

  it('wins the supertank quest only after both ammo pieces and the boss', () => {
    let state = running(QUEST_ID_04_SUPERTANK);
    state = nearDeathQuestElement(state, 'piece_1');
    state = nearDeathQuestElement(state, 'piece_2');
    assert.equal(isQuestVictory(state), false, 'the boss is still alive');
    state = nearDeathQuestElement(state, 'boss');
    assert.equal(isQuestVictory(state), true);
  });

  it('loses the supertank quest when the fake tank is attacked', () => {
    let state = running(QUEST_ID_04_SUPERTANK);
    state = nearDeathQuestElement(state, 'disabledTank');
    assert.equal(isQuestDefeat(state), true);
    // With both pieces gone the trap does not fire.
    let progressed = running(QUEST_ID_04_SUPERTANK);
    progressed = nearDeathQuestElement(progressed, 'piece_1');
    progressed = nearDeathQuestElement(progressed, 'piece_2');
    progressed = nearDeathQuestElement(progressed, 'disabledTank');
    assert.equal(isQuestDefeat(progressed), false);
  });

  it('wins the stealth quest when the last bastard dies', () => {
    // The spec says "all dead AND the commando at the computer"; the client
    // only requires all dead (quest/Quest10SpecialOps.as:520-534, 545-559).
    let state = running(QUEST_ID_10_SPECIAL_OPS);
    state = setQuestCounter(state, 'bastardsAlive', 2);
    assert.equal(isQuestVictory(state), false);
    state = addQuestCounter(state, 'bastardsAlive', -1);
    assert.equal(isQuestVictory(state), false);
    state = addQuestCounter(state, 'bastardsAlive', -1);
    assert.equal(isQuestVictory(state), true);
  });

  it('marks the rocket quest as unwinnable by the client code', () => {
    // The objective is declared `canDie: false`, so its `onKill` victory
    // callback can never fire (re/docs/12-quest-system.md §7 item #3).
    const rocket = getQuestSpec(QUEST_ID_08_ROCKET)!;
    assert.equal(rocket.victoryReachable, false);
    const launcher = rocket.elements.find((element) => element.ref === 'commandCenter');
    assert.equal(launcher?.canDie, false);
  });

  it('needs the radio station and all five labs in the laboratory quest', () => {
    let state = running(QUEST_ID_09_LABORATORIES);
    state = defendersClearedQuestElement(state, 'radioStation');
    for (const lab of LABORATORY_REFS) {
      assert.equal(isQuestVictory(state), false);
      const killed = killQuestElement(state, {
        itemId: 118,
        ref: lab,
        affiliation: 'neutral',
        isUnit: false,
        attack: 0,
      });
      state = killed.state;
    }
    assert.equal(isQuestVictory(state), true);
  });
});

describe('the hardcore quests', () => {
  it('is won when the last enemy unit dies', () => {
    let state = startQuest(
      prepareQuest(QUEST_ID_15_HARDCORE1, { army: [{ unitId: 1008, count: 10 }] }),
    );
    state = loadQuestMap(state, [enemyUnit('item:1122'), enemyUnit('item:1123')]);
    assert.equal(state.script.counters['enemiesAlive'], 2);
    assert.equal(isQuestVictory(state), false);

    const first = killQuestElement(state, enemyUnit('item:1122'));
    state = first.state;
    assert.equal(state.script.counters['enemiesAlive'], 1);
    assert.equal(isQuestVictory(state), false);

    const second = killQuestElement(state, enemyUnit('item:1123'));
    state = second.state;
    assert.equal(state.script.counters['enemiesAlive'], 0);
    assert.equal(isQuestVictory(state), true);
    assert.equal(isQuestDefeat(state), false);
  });

  it('is lost when the army is wiped out', () => {
    let state = startQuest(
      prepareQuest(QUEST_ID_15_HARDCORE1, { army: [{ unitId: 1008, count: 1 }] }),
    );
    state = loadQuestMap(state, [enemyUnit('item:1122')]);
    const killed = killQuestElement(state, friendlyUnit('item:1008'));
    state = killed.state;
    assert.equal(state.playerUnitsAlive, 0);
    assert.equal(isQuestDefeat(state), true);
  });
});

describe('the kill economy', () => {
  it('awards 5 gold and 1 xp for an attacking enemy unit', () => {
    const state = running(QUEST_ID_15_HARDCORE1);
    const killed = killQuestElement(state, enemyUnit('item:1122'));
    assert.equal(killed.gold, 5);
    assert.equal(killed.xp, 1);
    assert.equal(killed.state.gold, 5);
    assert.equal(killed.state.xp, 1);
  });

  it('awards nothing for a wall', () => {
    const state = running(QUEST_ID_15_HARDCORE1);
    const killed = killQuestElement(state, {
      itemId: 23,
      ref: 'item:23',
      affiliation: 'enemy',
      isUnit: false,
      attack: 0,
      subcatFunctional: 221,
    });
    assert.equal(killed.gold, 0);
    assert.equal(killed.xp, 0);
  });

  it('awards 1 xp for a building that cannot attack', () => {
    const state = running(QUEST_ID_15_HARDCORE1);
    const killed = killQuestElement(state, {
      itemId: 1,
      ref: 'item:1',
      affiliation: 'enemy',
      isUnit: false,
      attack: 0,
      subcatFunctional: 111,
    });
    assert.equal(killed.gold, 0);
    assert.equal(killed.xp, 1);
  });

  it('awards nothing for a summoned element', () => {
    const state = running(QUEST_ID_15_HARDCORE1);
    const killed = killQuestElement(state, {
      ...enemyUnit('item:1122'),
      summoned: true,
    });
    assert.equal(killed.gold, 0);
    assert.equal(killed.xp, 0);
    assert.equal(killed.state.gold, 0);
    // The chapter's `onKill` still fires, so the objective advances.
    assert.deepEqual(killed.state.script.destroyed, ['item:1122']);
  });

  it('awards nothing while a scripted airstrike runs', () => {
    // The airstrike quests override `elementKilled` for exactly this
    // (quest/Quest06Airstrike.as:386-393).
    let state = running(QUEST_ID_06_AIRSTRIKE);
    state = loadQuestMap(state, [enemyUnit('item:1122')]);
    state = suppressQuestKills(state, true);
    const killed = killQuestElement(state, enemyUnit('item:1122'));
    assert.equal(killed.gold, 0);
    assert.equal(killed.xp, 0);
    assert.equal(killed.state.remainingFoes, state.remainingFoes);
    assert.equal(killed.state.gold, 0);
  });

  it('clamps the xp to half the gold when the quest ends', () => {
    // quest/Quest.as:412-415
    assert.equal(clampQuestXp(10, 9), 5);
    assert.equal(clampQuestXp(10, 3), 3);
    assert.equal(clampQuestXp(11, 9), 5);
  });
});

describe('the rewards', () => {
  it('grants the static row only on a win', () => {
    const spec = getQuestSpec(QUEST_ID_01_BAZOOKA)!;
    const lost = questRewards(spec, 120, 40, false, { expRequired: 300 });
    assert.deepEqual(lost, [
      { key: 'g', amount: 120 },
      { key: 'x', amount: 40 },
    ]);

    const won = questRewards(spec, 120, 40, true, { expRequired: 300 });
    assert.deepEqual(won, [
      { key: 'g', amount: 120 },
      { key: 'x', amount: 40 },
      // The extra XP of the gold row: min(round(1500 / 4), 300 / 3).
      { key: 'x', amount: 100 },
      { key: 'g', amount: 1500 },
      { key: 'w', amount: 400 },
    ]);
  });

  it('builds the outcome of a finished quest', () => {
    let state = running(QUEST_ID_01_BAZOOKA);
    const killed = killQuestElement(state, enemyUnit('item:1108'));
    state = killed.state;
    const outcome = finishQuest(state, true, { expRequired: 300 });
    assert.equal(outcome.questId, QUEST_ID_01_BAZOOKA);
    assert.equal(outcome.win, true);
    assert.equal(outcome.difficulty, 1);
    assert.equal(outcome.gold, 5);
    assert.equal(outcome.xp, 1, 'the earned xp survives the clamp');
  });
});

describe('the unit recovery', () => {
  it('recovers 60 per cent of the killed units', () => {
    const army = [
      { unitId: 1008, sent: 10, killed: 4, recovered: 0 },
      { unitId: 1009, sent: 6, killed: 6, recovered: 0 },
    ];
    const result = recoverQuestUnits(army, 60, new Random('quest-seed'));
    // 10 units died; 60 per cent come back, so 4 are lost.
    assert.equal(result.recovered, 6);
    assert.equal(result.lost, 4);
    assert.equal(
      result.army.reduce((sum, entry) => sum + entry.recovered, 0),
      6,
    );
  });

  it('recovers everything when the player lost nothing', () => {
    const army = [{ unitId: 1008, sent: 10, killed: 0, recovered: 0 }];
    const result = recoverQuestUnits(army, 60, new Random('quest-seed'));
    assert.equal(result.lost, 0);
    assert.equal(result.recovered, 0);
  });

  it('is reproducible from the seed', () => {
    const army = Array.from({ length: 8 }, (_, index) => ({
      unitId: 1000 + index,
      sent: 5,
      killed: 5,
      recovered: 0,
    }));
    const first = recoverQuestUnits(army, 60, new Random('same-seed'));
    const second = recoverQuestUnits(army, 60, new Random('same-seed'));
    assert.deepEqual(first.army, second.army);
    const other = recoverQuestUnits(army, 60, new Random('other-seed'));
    assert.notDeepEqual(first.army, other.army);
  });

  it('never removes more than fifty units', () => {
    // The client's loop gives up after 50 attempts
    // (quest/Quest.as:471-480), so a huge army keeps more units than the
    // percentage asks for.
    const army = [{ unitId: 1008, sent: 500, killed: 500, recovered: 0 }];
    const result = recoverQuestUnits(army, 60, new Random('quest-seed'));
    assert.equal(result.lost, 50);
    assert.equal(result.recovered, 450);
  });
});

describe('the once-only award', () => {
  it('grants the reward once and keeps the best rank', () => {
    let state = running(QUEST_ID_01_BAZOOKA);
    const killed = killQuestElement(state, enemyUnit('item:1108'));
    state = killed.state;
    const outcome = finishQuest(state, true, { expRequired: 300 });

    const first = awardQuest(emptyQuestProgress(), outcome);
    assert.equal(first.award.awarded, true);
    assert.ok(first.award.rewards.length > 0);
    assert.equal(first.award.rank, 1);
    // The rank is keyed by the quest's play index.
    assert.equal(first.progress.ranks['1'], 1);
    assert.deepEqual(first.progress.awarded, [QUEST_ID_01_BAZOOKA]);

    const second = awardQuest(first.progress, outcome);
    assert.equal(second.award.awarded, false);
    assert.deepEqual(second.award.rewards, []);
    // The rank survives the replay.
    assert.equal(second.award.rank, 1);
  });

  it('keeps the highest difficulty as the rank', () => {
    const state = running(QUEST_ID_01_BAZOOKA);
    const outcome = finishQuest(state, true, { expRequired: 300 });
    const hard = { ...outcome, difficulty: 3 as const };
    const awarded = awardQuest(emptyQuestProgress(), hard);
    assert.equal(awarded.award.rank, 3);
    const replay = awardQuest(awarded.progress, { ...outcome, difficulty: 2 });
    assert.equal(replay.award.rank, 3);
  });

  it('does not raise the rank on a loss', () => {
    const state = running(QUEST_ID_01_BAZOOKA);
    const outcome = finishQuest(state, false, { expRequired: 300 });
    const awarded = awardQuest(emptyQuestProgress(), outcome);
    assert.equal(awarded.award.rank, 0);
    assert.equal(awarded.progress.ranks['1'], 0);
  });
});

describe('the chapter state machine', () => {
  it('creates the canonical empty status', () => {
    assert.deepEqual(createEmptyChapterStatus(9), {
      id: 9,
      spawned: false,
      ended: false,
      visited: false,
      activators: [],
      boss: [],
      treasure: [],
      killed: [],
    });
  });

  it('reuses the stored status only for the same unfinished chapter', () => {
    const stored = { ...createEmptyChapterStatus(9), spawned: true };
    assert.equal(prepareChapterStatus(stored, 9).spawned, true);
    // A different chapter starts from scratch.
    assert.equal(prepareChapterStatus(stored, 10).spawned, false);
    // An ended chapter starts from scratch too.
    assert.equal(prepareChapterStatus({ ...stored, ended: true }, 9).spawned, false);
    assert.equal(prepareChapterStatus(null, 9).spawned, false);
  });

  it('records a killed element only once', () => {
    const status = createEmptyChapterStatus(9);
    const first = recordChapterElementKilled(status, 'boss1');
    assert.equal(first.newlyKilled, true);
    assert.deepEqual(first.status.killed, ['boss1']);
    const second = recordChapterElementKilled(first.status, 'boss1');
    assert.equal(second.newlyKilled, false);
    assert.deepEqual(second.status.killed, ['boss1']);
  });

  it('records the activators and the treasures', () => {
    let status = createEmptyChapterStatus(9);
    status = recordActivatorCollected(status, 3);
    status = recordActivatorCollected(status, 3);
    assert.deepEqual(status.activators, [3]);
    status = recordTreasureCollected(status, 0);
    assert.deepEqual(status.treasure, [0]);
  });

  it('completes the chapter when every objective is done', () => {
    let status = createEmptyChapterStatus(9);
    const objectives = { numActivators: 1, numTreasures: 1, numBosses: 0 };
    assert.equal(chapterObjectivesComplete(status, objectives), false);
    status = recordActivatorCollected(status, 1);
    assert.equal(chapterObjectivesComplete(status, objectives), false);
    status = recordTreasureCollected(status, 0);
    assert.equal(chapterObjectivesComplete(status, objectives), true);
  });

  it('stores the identity of the simple chapter', () => {
    const status = advanceSimpleChapter(createEmptyChapterStatus(9), {
      chapterId: 12,
      playerLevel: 30,
      startTile: { x: 41, y: 42 },
    });
    assert.equal(status.idSimpleChapter, 12);
    assert.equal(status.playerLevel, 30);
    assert.deepEqual(status.startTile, { x: 41, y: 42 });
  });
});

describe('the set_quest_var command', () => {
  it('rejects a key the client is not allowed to write', () => {
    const result = applyQuestVar({}, 'hacked', 1);
    assert.equal(result.rejected, true);
    assert.deepEqual(result.vars, {});
  });

  it('stores the current mission id', () => {
    const result = applyQuestVar({}, 'id', 4);
    assert.equal(result.rejected, false);
    assert.equal(result.currentMissionId, 4);
    assert.equal(result.vars['id'], 4);
  });

  it('ignores idSimpleChapter like the upstream server does', () => {
    // upstream/socialwarriors/command.py:91-95
    const ignored = applyQuestVar({}, 'idSimpleChapter', 12);
    assert.equal(ignored.ignored, true);
    assert.deepEqual(ignored.vars, {});

    const honoured = applyQuestVar({}, 'idSimpleChapter', 12, { honourSimpleChapter: true });
    assert.equal(honoured.ignored, false);
    assert.equal(honoured.vars['idSimpleChapter'], 12);
  });

  it('builds the wire command', () => {
    assert.deepEqual(questVarCommand('killed', ['boss1']), {
      command: 'set_quest_var',
      args: ['killed', '["boss1"]'],
    });
  });
});
