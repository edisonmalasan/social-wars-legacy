import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { CommandOutcome, Reward } from '@swl/protocol';
import { QUEST_IDS, getQuestSpec } from '@swl/rules';

import {
  activeQuestFromWorld,
  activeQuestView,
  briefingDialog,
  briefingView,
  combatDialog,
  questActions,
  questChoice,
  questChoices,
  questDialogId,
  questDifficulty,
  questResultActionChoice,
  questResultFromReceipt,
  questResultView,
  resultDialog,
} from './questview.ts';
import { lastQuestReward } from './featurestate.ts';
import type { ActiveQuestStateView } from './featurestate.ts';
import type { WorldSnapshot } from './session.ts';

/** The story quest ids the UI drives. */
const Q03 = '100000003';
const Q02 = '100000002';

/** The index of a quest in the client's play order. */
const indexOf = (id: string): number => QUEST_IDS.indexOf(id) + 1;

/** A world with only the fields every world has. */
function world(privateState: Record<string, unknown> = {}): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {} }],
    privateState,
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
  };
}

/** A server-owned active quest view. */
function active(
  questId: string | null,
  overrides: Partial<ActiveQuestStateView> = {},
): ActiveQuestStateView {
  return {
    questId,
    counters: {},
    elements: {},
    events: [],
    ...overrides,
  };
}

/** The shape the server actually writes into `privateState.activeQuest`. */
function stored(activeState: ActiveQuestStateView): Record<string, unknown> {
  return {
    questId: activeState.questId,
    script: { counters: activeState.counters },
    ledger: { elements: activeState.elements, events: activeState.events },
  };
}

describe('quest choices', () => {
  it('turns a ranked server slot into an available quest with the rules title', () => {
    // Three ranked quests put the next unranked one (Q03) in progress.
    const ranks = { 1: 1, 2: 2, 3: 3 };
    const choices = questChoices(ranks, {}, 1);
    const convoy = choices.find((choice) => choice.questId === Q03)!;
    assert.deepEqual(convoy, {
      index: indexOf(Q03),
      questId: Q03,
      title: 'DEFEND THE CONVOY',
      rank: 0,
      levelUnlock: 0,
      locked: false,
      unlocked: true,
      active: false,
    });
  });

  it('locks a slot whose min level is above the player level', () => {
    const index = indexOf(Q03);
    const choices = questChoices({ 1: 1, 2: 2, 3: 3 }, { [index]: 7 }, 4);
    const convoy = choices.find((choice) => choice.questId === Q03)!;
    assert.equal(convoy.levelUnlock, 7);
    assert.equal(convoy.locked, true);
    assert.equal(convoy.unlocked, false);
  });

  it('marks the server active quest, and has no choice for a filler slot', () => {
    const choices = questChoices({}, {}, 1, Q02);
    assert.equal(choices.find((choice) => choice.questId === Q02)!.active, true);
    assert.equal(choices.find((choice) => choice.questId === Q03)!.active, false);
    assert.equal(
      questChoice({ index: 24, rank: 0, locked: true, levelUnlock: 0 }, 1),
      null,
    );
  });
});

describe('briefing view', () => {
  const ranks = Object.fromEntries(
    Array.from({ length: indexOf(Q02) - 1 }, (_, index) => [index + 1, 1]),
  );
  const choice = questChoices(ranks, {}, 1).find((entry) => entry.questId === Q02)!;

  it('carries the quest id, the rules subtitle and a difficulty', () => {
    const briefing = briefingView(choice, 2);
    assert.deepEqual(briefing, {
      questId: Q02,
      title: 'BLOW THE POWER PLANT',
      subtitle: 'Blow up the Nuclear Plant and then the Command Center!',
      difficulty: 2,
      canStart: true,
    });
  });

  it('normalises difficulty to the client\'s 1-3 stars', () => {
    assert.equal(questDifficulty(0), 1);
    assert.equal(questDifficulty(9), 3);
    assert.equal(questDifficulty('2'), 1);
    assert.equal(briefingView(choice, 9).difficulty, 3);
  });

  it('cannot start a locked slot or the already active quest', () => {
    const locked = { ...choice, locked: true, unlocked: false };
    assert.equal(briefingView(locked, 1).canStart, false);
    assert.equal(briefingView({ ...choice, active: true }, 1).canStart, false);
  });
});

describe('active quest view', () => {
  const state = active(Q02, {
    counters: { trucksArrived: 1, bastardsAlive: 0 },
    elements: {
      goodBoy: { hp: 3, alive: true },
      commandCenter: { hp: 2, alive: false },
    },
    events: ['arrival:item:1013:1'],
  });

  it('reads the server state verbatim, with stable ordering', () => {
    const view = activeQuestView(state, { keyRefs: ['goodBoy'] })!;
    assert.equal(view.questId, Q02);
    assert.equal(view.title, 'BLOW THE POWER PLANT');
    assert.deepEqual(view.counters, [
      { name: 'bastardsAlive', value: 0 },
      { name: 'trucksArrived', value: 1 },
    ]);
    assert.deepEqual(view.elements, [
      { ref: 'commandCenter', hp: 2, alive: false, key: false, label: 'commandCenter' },
      { ref: 'goodBoy', hp: 3, alive: true, key: true, label: 'goodBoy' },
    ]);
    assert.deepEqual(view.events, ['arrival:item:1013:1']);
  });

  it('never invents a quest from a bare seed', () => {
    assert.equal(activeQuestView(active(null)), null);
  });

  it('offers strikes, a two-argument kill report and an end action for a kill quest', () => {
    const view = activeQuestView(state, { keyRefs: ['goodBoy'] })!;
    const strikes = view.actions.filter((action) => action.kind === 'strike');
    // Neither a live key element (striking it loses the quest) nor a dead one
    // is offered as a strike. A dead one gets the two-argument kill report.
    assert.deepEqual(strikes, []);
    const live = activeQuestView(
      active(Q02, { elements: { goodBoy: { hp: 3, alive: true }, commandCenter: { hp: 2, alive: true } } }),
      { keyRefs: ['goodBoy'] },
    )!;
    assert.deepEqual(
      live.actions.filter((action) => action.kind === 'strike'),
      [{ kind: 'strike', ref: 'commandCenter', label: 'Strike commandCenter', enabled: true }],
    );
    assert.deepEqual(
      view.actions.filter((action) => action.kind === 'kill-report'),
      [
        {
          kind: 'kill-report',
          ref: 'commandCenter',
          label: 'Report kill: commandCenter',
          enabled: true,
        },
      ],
    );
    assert.deepEqual(view.actions.filter((action) => action.kind === 'end'), [
      { kind: 'end', label: 'Finish quest', enabled: true },
    ]);
  });

  it('offers a truck arrival while the server counter is short, then no more', () => {
    const event = { kind: 'truckArrivals' as const, refs: ['item:1013'], count: 3 };
    const options = { event, keyRefs: ['colonel'] };
    const before = questActions(
      active(Q03, { counters: { trucksArrived: 1 }, elements: { colonel: { hp: 2, alive: true } } }),
      options,
    );
    assert.deepEqual(before.find((action) => action.kind === 'event'), {
      kind: 'event',
      action: 'truck-arrival',
      ref: 'item:1013',
      label: 'Arrive truck (item:1013)',
      enabled: true,
    });
    assert.equal(before.some((action) => action.kind === 'strike'), false);

    const done = questActions(active(Q03, { counters: { trucksArrived: 3 } }), options);
    assert.equal(done.find((action) => action.kind === 'event')!.enabled, false);
  });

  it('does not offer an event whose dedupe key the server already saw', () => {
    const event = { kind: 'eligibleEnemies' as const, refs: ['item:42'], count: 1 };
    const done = questActions(
      active('100000010', {
        counters: { bastardsAlive: 1 },
        events: ['eligible:item:42'],
      }),
      { event },
    );
    assert.equal(done.find((action) => action.kind === 'event')!.enabled, false);
  });
});

describe('result view', () => {
  const rewards: readonly Reward[] = [{ resource: 'gold', amount: 4000 }];

  it('derives a win and its rewards from the server outcome', () => {
    const outcome: CommandOutcome = {
      index: 0,
      ok: true,
      result: { kind: 'rewards', rewards },
    };
    assert.deepEqual(questResultView(Q02, outcome), {
      questId: Q02,
      won: true,
      title: 'Quest complete',
      message: 'The server completed BLOW THE POWER PLANT.',
      kind: 'reward',
      rewards,
      missionComplete: true,
      rank: null,
      next: null,
    });
  });

  it('derives a refusal from the server error, never from client state', () => {
    const outcome: CommandOutcome = {
      index: 0,
      ok: false,
      error: { code: 'command-failed', message: 'no-victory', status: 409 },
    };
    assert.deepEqual(questResultView(Q02, outcome), {
      questId: Q02,
      won: false,
      title: 'Quest not finished',
      message: 'command-failed: no-victory',
      kind: 'result',
      rewards: [],
      missionComplete: false,
      rank: null,
      next: null,
    });
  });

  it('does not claim a win when there was no server answer', () => {
    const view = questResultView(Q02, null, 'The request failed (network).');
    assert.equal(view.won, false);
    assert.equal(view.message, 'The request failed (network).');
    assert.deepEqual(view.rewards, []);
  });

  it('reads the rank the server recorded for the completed mission', () => {
    const outcome: CommandOutcome = {
      index: 0,
      ok: true,
      result: { kind: 'rewards', rewards },
    };
    const view = questResultView(Q02, outcome, undefined, {
      ranks: { [getQuestSpec(Q02)!.playIndex]: 2 },
    });
    assert.equal(view.missionComplete, true);
    assert.equal(view.rank, 2);
  });

  it('offers the next mission only where the server rank and unlock allow it', () => {
    const outcome: CommandOutcome = {
      index: 0,
      ok: true,
      result: { kind: 'rewards', rewards },
    };
    const playIndex = getQuestSpec(Q02)!.playIndex;
    const nextIndex = playIndex + 1;
    const nextId = QUEST_IDS[nextIndex]!;
    const options = {
      ranks: { [playIndex]: 1 },
      playerLevel: 1,
      numQuests: QUEST_IDS.length - 1,
    };
    const open = questResultView(Q02, outcome, undefined, options);
    assert.equal(open.next?.questId, nextId);
    assert.equal(open.next?.index, nextIndex);
    assert.equal(open.next?.available, true);

    const locked = questResultView(Q02, outcome, undefined, {
      ...options,
      minLevels: { [nextIndex]: 10 },
    });
    assert.equal(locked.next?.available, false);
  });

  it('offers no next mission and no rewards on a defeat', () => {
    const outcome: CommandOutcome = {
      index: 0,
      ok: false,
      error: { code: 'command-failed', message: 'no-victory', status: 409 },
    };
    const view = questResultView(Q02, outcome, undefined, {
      ranks: { [getQuestSpec(Q02)!.playIndex]: 1 },
      playerLevel: 1,
    });
    assert.equal(view.next, null);
    assert.deepEqual(view.rewards, []);
    assert.equal(view.missionComplete, false);
  });

  it('rebuilds a result from the persisted server receipt, never a replay', () => {
    const receipt = {
      questId: Q02,
      rank: 2,
      rewards: [
        { resource: 'gold' as const, amount: 4000 },
        { resource: 'xp' as const, amount: 100 },
      ],
    };
    assert.deepEqual(lastQuestReward(world({ lastQuestReward: receipt })), receipt);
    assert.equal(lastQuestReward(world()), null);
    const view = questResultFromReceipt(receipt, {
      ranks: { [getQuestSpec(Q02)!.playIndex]: 2 },
    });
    assert.equal(view.won, true);
    assert.equal(view.rank, 2);
    assert.equal(view.missionComplete, true);
    assert.deepEqual(view.rewards, receipt.rewards);
  });

  // Host-level: the exact gate the dialog's Next button goes through before
  // it calls openQuestSlot. A first-time unlock must open QUEST_IDS[p+1],
  // not be refused by the one-based chapter-slot lookup.
  it('opens the freshly unlocked next mission from the server play index', () => {
    const playIndex = getQuestSpec(Q02)!.playIndex;
    const ranks = { [playIndex]: 1 };
    const options = {
      ranks,
      minLevels: {},
      playerLevel: 1,
      numQuests: QUEST_IDS.length - 1,
    };
    const won = questResultView(
      Q02,
      { index: 0, ok: true, result: { kind: 'rewards', rewards } },
      undefined,
      options,
    );
    const nextId = QUEST_IDS[playIndex + 1]!;
    assert.equal(won.next?.questId, nextId);
    assert.equal(won.next?.available, true);

    const choice = questResultActionChoice(won, nextId, 'next', options);
    assert.ok(choice, 'the Next gesture must not be refused');
    assert.equal(choice.questId, nextId);
    assert.equal(choice.index, playIndex + 2);
    assert.equal(choice.rank, 0, 'the first-time unlock is not ranked yet');
    assert.equal(choice.unlocked, true);
    assert.equal(choice.locked, false);
    assert.equal(choice.active, false);
  });

  it('fails closed when the server has not unlocked the next mission', () => {
    const playIndex = getQuestSpec(Q02)!.playIndex;
    const nextIndex = playIndex + 1;
    const options = {
      ranks: { [playIndex]: 1 },
      minLevels: { [nextIndex]: 99 },
      playerLevel: 1,
      numQuests: QUEST_IDS.length - 1,
    };
    const won = questResultView(
      Q02,
      { index: 0, ok: true, result: { kind: 'rewards', rewards } },
      undefined,
      options,
    );
    assert.equal(won.next?.available, false);
    assert.equal(
      questResultActionChoice(won, QUEST_IDS[nextIndex]!, 'next', options),
      null,
    );
  });

  it('still allows a retry of the ranked mission the server completed', () => {
    const playIndex = getQuestSpec(Q02)!.playIndex;
    const options = { ranks: { [playIndex]: 1 }, minLevels: {}, playerLevel: 1 };
    const won = questResultView(
      Q02,
      { index: 0, ok: true, result: { kind: 'rewards', rewards } },
      undefined,
      options,
    );
    const choice = questResultActionChoice(won, Q02, 'retry', options);
    assert.ok(choice);
    assert.equal(choice.questId, Q02);
    assert.equal(choice.rank, 1);
    assert.equal(choice.unlocked, true);
  });
});

describe('recovery and dialog hosting', () => {
  it('restores the active panel from /api/world after a reload', () => {
    const state = active(Q03, {
      counters: { trucksArrived: 2 },
      elements: { colonel: { hp: 1, alive: true } },
    });
    const view = activeQuestFromWorld(world({ activeQuest: stored(state) }), {
      event: { kind: 'truckArrivals', refs: ['item:1013'], count: 3 },
    })!;
    assert.equal(view.questId, Q03);
    assert.deepEqual(view.elements[0], {
      ref: 'colonel',
      hp: 1,
      alive: true,
      key: false,
      label: 'colonel',
    });
    assert.equal(activeQuestFromWorld(world()), null);
  });

  it('opens briefing, combat and result in the one shared dialog', () => {
    const briefing = briefingView(questChoices({}, {}, 1)[0]!, 1);
    assert.deepEqual(briefingDialog(briefing), {
      id: questDialogId('briefing', QUEST_IDS[0]!),
      kind: 'briefing',
      title: briefing.title,
    });
    assert.deepEqual(combatDialog(Q02), {
      id: questDialogId('combat', Q02),
      kind: 'combat',
      title: 'BLOW THE POWER PLANT',
    });
    const result = questResultView(Q02, {
      index: 0,
      ok: true,
      result: { kind: 'none' },
    });
    assert.deepEqual(resultDialog(Q02, result), {
      id: questDialogId('result', Q02),
      kind: 'reward',
      title: 'Quest complete',
    });
  });
});
