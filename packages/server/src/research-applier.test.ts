/**
 * Server-authoritative research appliers (Area 51 / Robotic Center).
 *
 * The client's cashCost argument is never trusted, the state is server-owned,
 * and the friend-help ledger de-duplicates so a replay grants nothing twice.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  RESEARCH_STEP_SECONDS,
  RESEARCH_TOTAL_STEPS,
  costContentFrom,
  initialResearchState,
  researchCashCost,
  type ResearchState,
} from '@swl/rules';

import {
  RESEARCH_STATE_KEY,
  ROBOTIC_HELP_CONSUMED_KEY,
  createApplier,
  type ApplierDeps,
} from './apply.ts';
import { LegacyIdentityBridge } from './session.ts';
import { applyBatch, type ShimContext, type ShimWorld } from './shim.ts';

const NOW = 1_700_000_000;

function deps(over: Partial<ApplierDeps> = {}): ApplierDeps {
  return {
    now: () => NOW,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
    dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
    ...over,
  };
}

function world(
  state?: ResearchState,
  over: Partial<ShimWorld> = {},
): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, items: {}, store: {} }],
      privateState: state ? { [RESEARCH_STATE_KEY]: state } : {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 100, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
    ...over,
  };
}

function stateOf(w: ShimWorld): ResearchState {
  return w.save.privateState[RESEARCH_STATE_KEY] as ResearchState;
}

function mapOf(w: ShimWorld): Record<string, unknown> {
  return w.save.maps[0] as Record<string, unknown>;
}

describe('next_research_step', () => {
  it('increments the step and restarts the six-hour timer only when asked', () => {
    assert.equal(RESEARCH_STEP_SECONDS, 6 * 60 * 60);
    const applier = createApplier(deps({ now: () => 9000 }));
    const first = applier(world(), { name: 'next_research_step', args: [1, true] });
    assert.equal(first.applied, true);
    assert.deepEqual(stateOf(first.world).stepNumber, [0, 1]);
    assert.deepEqual(stateOf(first.world).timestamp, [0, 9000]);

    const second = createApplier(deps({ now: () => 999999 }))(first.world, {
      name: 'next_research_step',
      args: [1, false],
    });
    assert.equal(second.applied, true);
    assert.deepEqual(stateOf(second.world).stepNumber, [0, 2]);
    // Friend-help style steps move progress but leave the timer alone.
    assert.deepEqual(stateOf(second.world).timestamp, [0, 9000]);
  });

  it('refuses an unknown type and leaves state unchanged', () => {
    const w = world();
    const before = JSON.stringify(w);
    const outcome = createApplier(deps())(w, {
      name: 'next_research_step',
      args: [7, true],
    });
    assert.equal(outcome.applied, false);
    assert.equal(JSON.stringify(w), before);
  });
});

describe('research_buy_step_cash', () => {
  it('ignores the client cashCost and charges the content price', () => {
    const state = initialResearchState();
    state.itemNumber[1] = 0;
    state.stepNumber[1] = 4;
    state.timestamp[1] = 777;
    const expected = researchCashCost(1, 0);
    assert.equal(expected, 15);

    const outcome = createApplier(deps())(world(state), {
      name: 'research_buy_step_cash',
      args: [1, 1],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 100 - expected);
    assert.deepEqual(stateOf(outcome.world).stepNumber, [0, 4]);
    assert.deepEqual(stateOf(outcome.world).timestamp, [0, 0]);
  });

  it('prices area 51 from its own track, not the client number', () => {
    const state = initialResearchState();
    state.itemNumber[0] = 1;
    const outcome = createApplier(deps())(world(state), {
      name: 'research_buy_step_cash',
      args: [999, 0],
    });
    assert.equal(outcome.applied, true);
    assert.equal(outcome.world.resources['c'], 100 - researchCashCost(0, 1));
    assert.equal(researchCashCost(0, 1), 15);
  });

  it('ignores the client-declared cash delta in the legacy batch', () => {
    const state = initialResearchState();
    state.itemNumber[1] = 0;
    const w = world(state, { resources: { g: 0, w: 0, o: 0, s: 0, c: 100, e: 0, x: 0, m: 0 } });
    const content = costContentFrom({
      items: [],
      offerPacks: [],
      globals: {},
      expansionPrices: [],
    });
    const context: ShimContext = {
      world: w,
      content,
      now: NOW,
      identity: new LegacyIdentityBridge(),
      applyCommand: createApplier(deps()),
    };
    // The client claims a 1-cash step and a +999 delta; neither is read.
    const outcome = applyBatch(
      {
        first_number: 1,
        commands: [['0', 'research_buy_step_cash', [1, 1], [0, 0, 0, 0, 0, 0, 999, 0]]],
      },
      context,
    );
    assert.deepEqual(outcome.refused, []);
    assert.equal(outcome.world.resources['c'], 100 - researchCashCost(1, 0));
    assert.equal(researchCashCost(1, 0), 15);
  });

  it('leaves state unchanged when the wallet cannot afford it', () => {
    const state = initialResearchState();
    state.timestamp[1] = 777;
    const w = world(state, { resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 } });
    const before = JSON.stringify(w);
    const outcome = createApplier(deps())(w, {
      name: 'research_buy_step_cash',
      args: [1, 1],
    });
    assert.equal(outcome.applied, false);
    assert.equal(JSON.stringify(w), before);
  });
});

describe('next_research_item', () => {
  it('grants on the tenth step and rolls the item number over modulo six', () => {
    const state = initialResearchState();
    state.itemNumber[1] = 5;
    state.stepNumber[1] = RESEARCH_TOTAL_STEPS;
    state.timestamp[1] = NOW - RESEARCH_STEP_SECONDS;
    const outcome = createApplier(deps())(world(state), {
      name: 'next_research_item',
      args: [1],
    });
    assert.equal(outcome.applied, true);
    assert.equal((mapOf(outcome.world)['store'] as Record<string, number>)['1105'], 1);
    assert.deepEqual(stateOf(outcome.world).itemNumber, [0, 0]);
    assert.deepEqual(stateOf(outcome.world).stepNumber, [0, 0]);
    assert.deepEqual(stateOf(outcome.world).timestamp, [0, 0]);
  });

  it('does nothing before the tenth step', () => {
    const state = initialResearchState();
    state.stepNumber[0] = RESEARCH_TOTAL_STEPS - 1;
    const w = world(state);
    const before = JSON.stringify(w);
    const outcome = createApplier(deps())(w, { name: 'next_research_item', args: [0] });
    assert.equal(outcome.applied, true);
    assert.equal(JSON.stringify(outcome.world), before);
  });
});

describe('reset_research_item', () => {
  it('zeroes only the named type', () => {
    const state = initialResearchState();
    state.itemNumber = [3, 2];
    state.stepNumber = [7, 9];
    state.timestamp = [555, 666];
    const outcome = createApplier(deps())(world(state), {
      name: 'reset_research_item',
      args: [0],
    });
    assert.equal(outcome.applied, true);
    assert.deepEqual(stateOf(outcome.world).itemNumber, [0, 2]);
    assert.deepEqual(stateOf(outcome.world).stepNumber, [0, 9]);
    assert.deepEqual(stateOf(outcome.world).timestamp, [0, 666]);
  });
});

describe('finish_robotic_help', () => {
  it('grants two steps per friend, capped at ten, and consumes the help list', () => {
    const state = initialResearchState();
    state.stepNumber[1] = 1;
    state.timestamp[1] = 4321;
    const outcome = createApplier(deps())(world(state), {
      name: 'finish_robotic_help',
      args: [JSON.stringify(['a', 'b', 'c'])],
    });
    assert.equal(outcome.applied, true);
    assert.deepEqual(stateOf(outcome.world).stepNumber, [0, 7]);
    // 1 + 3 * 2 = 7; the countdown is untouched below the cap.
    assert.deepEqual(stateOf(outcome.world).timestamp, [0, 4321]);

    const again = createApplier(deps())(outcome.world, {
      name: 'finish_robotic_help',
      args: [JSON.stringify(['a', 'b', 'c'])],
    });
    assert.equal(again.applied, true);
    assert.deepEqual(stateOf(again.world).stepNumber, [0, 7]);
    assert.deepEqual(
      again.world.save.privateState[ROBOTIC_HELP_CONSUMED_KEY],
      ['a', 'b', 'c'],
    );
  });

  it('caps at ten steps and clears the timer when the cap is reached', () => {
    const state = initialResearchState();
    state.stepNumber[1] = 7;
    state.timestamp[1] = 4321;
    const outcome = createApplier(deps())(world(state), {
      name: 'finish_robotic_help',
      args: [JSON.stringify(['a', 'b', 'c', 'd', 'e'])],
    });
    assert.equal(outcome.applied, true);
    assert.deepEqual(stateOf(outcome.world).stepNumber, [0, RESEARCH_TOTAL_STEPS]);
    assert.deepEqual(stateOf(outcome.world).timestamp, [0, 0]);
  });

  it('ignores duplicate friend ids in one request', () => {
    const outcome = createApplier(deps())(world(), {
      name: 'finish_robotic_help',
      args: [JSON.stringify(['a', 'a', 'a'])],
    });
    assert.equal(outcome.applied, true);
    assert.deepEqual(stateOf(outcome.world).stepNumber, [0, 2]);
  });

  it('refuses a malformed friend list and leaves state unchanged', () => {
    const w = world();
    const before = JSON.stringify(w);
    const outcome = createApplier(deps())(w, {
      name: 'finish_robotic_help',
      args: ['not json'],
    });
    assert.equal(outcome.applied, false);
    assert.equal(JSON.stringify(w), before);
  });
});
