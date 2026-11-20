import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  activeQuestState,
  bonusState,
  dartsState,
  marketState,
  premiumState,
  productionState,
  questState,
} from './featurestate.ts';
import type { WorldSnapshot } from './session.ts';

/** A save with only the fields every world has — none of the feature keys. */
function world(
  privateState: Record<string, unknown> = {},
  map: Record<string, unknown> = {},
): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {}, ...map }],
    privateState,
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
  };
}

describe('dartsState', () => {
  const SAVE = {
    dartsRandomSeed: 4242,
    dartsBalloonsShot: [0, 7, 24],
    dartsHasFree: false,
    dartsGotExtra: true,
    timeStampDartsReset: 1_700_000_000,
    timeStampDartsNewFree: 1_700_003_600,
  };

  it('reads the server darts fields verbatim', () => {
    assert.deepEqual(dartsState(world(SAVE)), {
      randomSeed: 4242,
      balloonsShot: [0, 7, 24],
      hasFree: false,
      gotExtra: true,
      resetAt: 1_700_000_000,
      newFreeAt: 1_700_003_600,
    });
  });

  it('is null when the save has no darts keys', () => {
    assert.equal(dartsState(world()), null);
  });

  it('never fabricates a board, a prize or a timestamp', () => {
    const state = dartsState(world({ dartsRandomSeed: 5 }))!;
    assert.deepEqual(state.balloonsShot, []);
    assert.equal(state.balloonsShot.length, 0);
    assert.equal(state.hasFree, false);
    assert.equal(state.gotExtra, false);
    assert.equal(state.resetAt, null);
    assert.equal(state.newFreeAt, null);
  });

  it('ignores malformed values rather than guessing', () => {
    const state = dartsState(world({
      dartsRandomSeed: Number.NaN,
      dartsBalloonsShot: [1, 'x', Number.NaN, 3],
      dartsHasFree: 'yes',
      dartsGotExtra: 1,
      timeStampDartsReset: Number.POSITIVE_INFINITY,
      timeStampDartsNewFree: 'now',
    }))!;
    assert.equal(state.randomSeed, null);
    assert.deepEqual(state.balloonsShot, [1, 3]);
    assert.equal(state.hasFree, false);
    assert.equal(state.gotExtra, false);
    assert.equal(state.resetAt, null);
    assert.equal(state.newFreeAt, null);
  });
});

describe('marketState', () => {
  it('reads the server market counters and first-time flag', () => {
    const state = marketState(
      world(
        { marketPlaceFirstTime: true },
        {
          numTradesDone: 6,
          resourcesTraded: { w: 200, o: 50 },
          timestampLastTrade: 1_700_000_000,
        },
      ),
    );
    assert.deepEqual(state, {
      tradesDone: 6,
      resourcesTraded: { w: 200, o: 50 },
      lastTradeAt: 1_700_000_000,
      firstTime: true,
    });
  });

  it('is null when the save has no market keys', () => {
    assert.equal(marketState(world()), null);
  });

  it('never invents a price and reads only own, finite traded amounts', () => {
    const traded: Record<string, unknown> = Object.create({ cash: 999 });
    traded['w'] = 10;
    traded['o'] = Number.NaN;
    const state = marketState(world({}, { resourcesTraded: traded }))!;
    assert.deepEqual(state.resourcesTraded, { w: 10 });
    assert.equal(state.tradesDone, null);
    assert.equal(state.lastTradeAt, null);
    assert.equal(state.firstTime, null);
  });
});

describe('premiumState', () => {
  it('reads the server premium expiry', () => {
    assert.deepEqual(premiumState(world({ timeStampEndPremium: 1_700_000_000 })), {
      endsAt: 1_700_000_000,
    });
  });

  it('is null when the save has no premium key', () => {
    assert.equal(premiumState(world()), null);
  });

  it('never fabricates an expiry', () => {
    assert.equal(premiumState(world({ timeStampEndPremium: Number.NaN })), null);
    assert.equal(premiumState(world({ timeStampEndPremium: 'later' })), null);
  });
});

describe('bonusState', () => {
  const SAVE = {
    weeklyRewardIndex: 3,
    timeStampMondayBonus: 1_700_000_000,
    bonusNextId: 4,
    timestampLastBonus: 1_700_003_600,
  };

  it('reads the server bonus fields', () => {
    assert.deepEqual(bonusState(world(SAVE)), {
      weeklyIndex: 3,
      mondayBonusAt: 1_700_000_000,
      nextBonusId: 4,
      lastBonusAt: 1_700_003_600,
    });
  });

  it('is null when the save has no bonus keys', () => {
    assert.equal(bonusState(world()), null);
  });

  it('never invents a prize or a timestamp', () => {
    const state = bonusState(world({ bonusNextId: 2 }))!;
    assert.equal(state.weeklyIndex, null);
    assert.equal(state.mondayBonusAt, null);
    assert.equal(state.lastBonusAt, null);
    assert.equal(state.nextBonusId, 2);
  });
});

describe('questState', () => {
  const SAVE = {
    questProgress: {
      ranks: { '1': 2, '3': 1 },
      awarded: ['2', '4'],
    },
    unlockedQuestIndex: 5,
    // The server writes questsRank to privateState, not to maps[0].
    questsRank: { '7': 3 },
  };
  const MAP = {
    questTimes: { '1': 1_700_000_000 },
    idCurrentMission: 700_001,
    currentQuestVars: { chapter: 2 },
  };

  it('reads each quest field from where the server actually writes it', () => {
    const state = questState(world(SAVE, MAP))!;
    assert.deepEqual(state.progress, {
      ranks: { '1': 2, '3': 1 },
      awarded: ['2', '4'],
    });
    assert.equal(state.unlockedIndex, 5);
    assert.deepEqual(state.ranks, { '7': 3 });
    assert.deepEqual(state.times, { '1': 1_700_000_000 });
    assert.equal(state.currentMissionId, 700_001);
    assert.deepEqual(state.currentQuestVars, { chapter: 2 });
  });

  it('is null when the save has no quest keys', () => {
    assert.equal(questState(world()), null);
  });

  it('never invents a rank, a chapter or a timestamp', () => {
    const state = questState(world({ questProgress: {} }))!;
    assert.deepEqual(state.progress, { ranks: {}, awarded: [] });
    assert.equal(state.unlockedIndex, null);
    assert.deepEqual(state.ranks, {});
    assert.deepEqual(state.times, {});
    assert.equal(state.currentMissionId, null);
    assert.equal(state.currentQuestVars, null);
  });

  it('does not read questsRank from the map, where the server never writes it', () => {
    // A map-level questsRank is not a key the server writes, so a save with
    // only that field has none of the quest keys and reads as null.
    assert.equal(questState(world({}, { questsRank: { '7': 3 } })), null);
  });

  it('ignores malformed progress, times and ranks', () => {
    const state = questState(
      world(
        {
          questProgress: { ranks: { a: 1, b: 'x' }, awarded: ['1', 2, null] },
          questsRank: { a: 'x', b: 2 },
          unlockedQuestIndex: Number.POSITIVE_INFINITY,
        },
        {
          questTimes: { a: 1, b: 'x' },
          idCurrentMission: Number.NaN,
          currentQuestVars: [1, 2],
        },
      ),
    )!;
    assert.deepEqual(state.progress, { ranks: { a: 1 }, awarded: ['1'] });
    assert.deepEqual(state.ranks, { b: 2 });
    assert.deepEqual(state.times, { a: 1 });
    assert.equal(state.currentMissionId, null);
    assert.equal(state.unlockedIndex, null);
    assert.equal(state.currentQuestVars, null);
  });
});

describe('activeQuestState', () => {
  const ACTIVE = {
    questId: '100000002',
    phase: 'started',
    // The counters live under `script` in the save; the endpoint's summary
    // flattens them. The selector reads where the save actually writes them.
    script: {
      counters: { enemiesAlive: 3, trucksArrived: 0 },
      destroyed: ['commandCenter'],
    },
    ledger: {
      elements: {
        commandCenter: { hp: 0, alive: false },
        goodBoy: { hp: 4, alive: true },
      },
      events: ['strike:commandCenter:3'],
      strikes: { commandCenter: 3 },
    },
  };

  it('reads the quest id, the server-owned counters and the ledger verbatim', () => {
    assert.deepEqual(activeQuestState(world({ activeQuest: ACTIVE })), {
      questId: '100000002',
      counters: { enemiesAlive: 3, trucksArrived: 0 },
      elements: {
        commandCenter: { hp: 0, alive: false },
        goodBoy: { hp: 4, alive: true },
      },
      events: ['strike:commandCenter:3'],
    });
  });

  it('is null when the save has no active quest', () => {
    assert.equal(activeQuestState(world()), null);
  });

  it('does not fabricate a counter, an element or an event', () => {
    const state = activeQuestState(world({ activeQuest: { questId: '100000002' } }))!;
    assert.equal(state.questId, '100000002');
    assert.deepEqual(state.counters, {});
    assert.deepEqual(state.elements, {});
    assert.deepEqual(state.events, []);
  });

  it('ignores malformed values rather than guessing a ledger', () => {
    const state = activeQuestState(world({ activeQuest: {
      questId: 42,
      script: { counters: { good: 1, bad: 'x' } },
      ledger: {
        elements: {
          ok: { hp: 2, alive: true },
          noHp: { alive: false },
          noRecord: 'x',
        },
        events: ['one', 2, null],
      },
    } }))!;
    assert.equal(state.questId, null);
    assert.deepEqual(state.counters, { good: 1 });
    assert.deepEqual(state.elements, { ok: { hp: 2, alive: true } });
    assert.deepEqual(state.events, ['one']);
  });

  it('treats a bare { questId } seed as an incomplete, non-authoritative quest', () => {
    // A legacy seed carries no ledger, so there are no elements to act on.
    const state = activeQuestState(world({ activeQuest: { questId: '100000002' } }));
    assert.ok(state);
    assert.equal(Object.keys(state!.elements).length, 0);
  });
});

describe('productionState', () => {
  const ATTRS = {
    cp: 3,
    lastAccruedAt: 1_700_000_000,
    collect: 100,
    unitCapacity: 5,
    unitsInside: 2,
    collectType: 'w',
  };

  function withAttrs(attrs: unknown): WorldSnapshot {
    return world({}, { items: { '7': [2, 0, 0, 0, 0, [], attrs, 1] } });
  }

  it('reads the server-owned production attributes verbatim', () => {
    assert.deepEqual(productionState(withAttrs(ATTRS), 7), {
      period: 3,
      startedAt: 1_700_000_000,
      collect: 100,
      unitCapacity: 5,
      unitsInside: 2,
      collectType: 'w',
    });
  });

  it('reads an empty attribute bag as unset, never as an invented cycle', () => {
    assert.deepEqual(productionState(withAttrs({}), 7), {
      period: null,
      startedAt: null,
      collect: null,
      unitCapacity: null,
      unitsInside: null,
      collectType: null,
    });
  });

  it('ignores malformed attributes', () => {
    assert.deepEqual(
      productionState(
        withAttrs({
          cp: '4',
          lastAccruedAt: Number.NaN,
          collect: 'x',
          unitCapacity: Number.POSITIVE_INFINITY,
          unitsInside: '2',
          collectType: 7,
        }),
        7,
      ),
      {
        period: null,
        startedAt: null,
        collect: null,
        unitCapacity: null,
        unitsInside: null,
        collectType: null,
      },
    );
  });

  it('is null when there is no selection or no such map item', () => {
    assert.equal(productionState(world(), 7), null);
    assert.equal(productionState(world(), null), null);
  });
});
