import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  DART_COST_CASH,
  NUM_PRIZES,
  NUM_TARGETS,
  PRIZE_TARGET_COUNTS,
  allDiscovered,
  buildDartsBoard,
  dartsShotCost,
  newDartsState,
  shootDarts,
} from './dartsboard.ts';

const ITEMS = [1061, 1073, 1071, 1031, 1058, 1045];
const EXTRA = 1152;

describe('the darts board', () => {
  it('has 25 targets and 6 prizes', () => {
    assert.equal(NUM_TARGETS, 25);
    assert.equal(NUM_PRIZES, 6);
  });

  it('spreads the prizes 1, 1, 4, 4, 7, 8', () => {
    // The client's initTargetItems, in its order.
    assert.deepEqual([...PRIZE_TARGET_COUNTS], [1, 1, 4, 4, 7, 8]);
    assert.equal(PRIZE_TARGET_COUNTS.reduce((a, b) => a + b, 0), NUM_TARGETS);
  });

  it('gives every prize its share of the targets', () => {
    const board = buildDartsBoard(12345);
    assert.equal(board.length, NUM_TARGETS);
    for (let prize = 0; prize < PRIZE_TARGET_COUNTS.length; prize++) {
      const count = board.filter((index) => index === prize).length;
      assert.equal(count, PRIZE_TARGET_COUNTS[prize], `prize ${prize}`);
    }
  });

  it('is the same board for the same seed', () => {
    assert.deepEqual(buildDartsBoard(999), buildDartsBoard(999));
  });

  it('is a different board for a different seed', () => {
    assert.notDeepEqual(buildDartsBoard(1), buildDartsBoard(2));
  });
});

describe('shooting a balloon', () => {
  it('discovers the prize the target carried', () => {
    const state = newDartsState(4242);
    const shot = shootDarts(state, 0, ITEMS, EXTRA);
    assert.ok(shot.prizeIndex !== null);
    assert.equal(shot.prizeItemId, ITEMS[shot.prizeIndex!]);
    assert.equal(shot.state.discovered[shot.prizeIndex!], true);
  });

  it('records the target as shot', () => {
    const state = newDartsState(4242);
    const shot = shootDarts(state, 3, ITEMS, EXTRA);
    assert.deepEqual(shot.state.shot, [3]);
  });

  it('refuses a target that was already shot', () => {
    const state = newDartsState(4242);
    const first = shootDarts(state, 3, ITEMS, EXTRA);
    const second = shootDarts(first.state, 3, ITEMS, EXTRA);
    assert.equal(second.prizeIndex, null);
    assert.equal(second.prizeItemId, null);
  });

  it('refuses a target that does not exist', () => {
    const state = newDartsState(4242);
    assert.equal(shootDarts(state, 99, ITEMS, EXTRA).prizeIndex, null);
    assert.equal(shootDarts(state, -1, ITEMS, EXTRA).prizeIndex, null);
  });

  it('the first shot is free and the rest cost 20 cash', () => {
    const state = newDartsState(4242);
    assert.equal(state.hasFree, true);
    assert.equal(dartsShotCost(state), 0);

    const shot = shootDarts(state, 0, ITEMS, EXTRA);
    assert.equal(shot.free, true);
    assert.equal(dartsShotCost(shot.state), DART_COST_CASH);
    assert.equal(DART_COST_CASH, 20);
  });
});

describe('the extra prize', () => {
  it('is won when every prize has been discovered', () => {
    // Find a target for each of the six prizes and shoot them all.
    let state = newDartsState(4242);
    const shotTargets = new Map<number, number>();
    state.board.forEach((prize, target) => {
      if (!shotTargets.has(prize)) shotTargets.set(prize, target);
    });
    assert.equal(shotTargets.size, 6);

    let wonExtra = false;
    for (const target of shotTargets.values()) {
      const shot = shootDarts(state, target, ITEMS, EXTRA);
      state = shot.state;
      wonExtra = wonExtra || shot.wonExtra;
    }
    assert.equal(wonExtra, true);
    assert.equal(state.gotExtra, true);
    assert.equal(allDiscovered(state), true);
  });

  it('is not won before every prize is discovered', () => {
    const state = newDartsState(4242);
    const shot = shootDarts(state, 0, ITEMS, EXTRA);
    assert.equal(shot.wonExtra, false);
    assert.equal(allDiscovered(shot.state), false);
  });

  it('is won only once', () => {
    // Discover everything, then shoot another target: the extra must not be
    // won twice.
    let state = newDartsState(4242);
    const shotTargets = new Map<number, number>();
    state.board.forEach((prize, target) => {
      if (!shotTargets.has(prize)) shotTargets.set(prize, target);
    });
    for (const target of shotTargets.values()) {
      state = shootDarts(state, target, ITEMS, EXTRA).state;
    }
    assert.equal(state.gotExtra, true);

    // Any target that has not been shot yet.
    const spare = state.board.findIndex((_, target) => !state.shot.includes(target));
    assert.ok(spare >= 0, 'every target was shot');
    const shot = shootDarts(state, spare, ITEMS, EXTRA);
    assert.equal(shot.wonExtra, false);
    assert.equal(shot.state.gotExtra, true);
  });
});
