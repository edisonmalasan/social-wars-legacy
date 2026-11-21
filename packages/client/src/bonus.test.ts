import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { bonusPanel } from './bonus.ts';
import type { WorldSnapshot } from './session.ts';

/** A save with only the fields every world has. */
function world(privateState: Record<string, unknown> = {}): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {} }],
    privateState,
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
  };
}

/** 2023-11-14 22:00 UTC — a Tuesday, exactly on an hour boundary. */
const NOW = 1_699_999_200;
const DAY = 86_400;

describe('bonusPanel', () => {
  it('reads the server-owned daily cycle without claiming anything', () => {
    const view = bonusPanel(
      world({
        bonusNextId: 3,
        timestampLastBonus: NOW - 60,
        weeklyRewardIndex: 2,
        timeStampMondayBonus: NOW - 7 * DAY,
      }),
      NOW,
      0,
    );
    assert.deepEqual(view, {
      day: 4,
      ready: false,
      reset: false,
      secondsToNextDay: 7_200,
      weekly: 'hidden',
    });
  });

  it('reports the daily bonus ready after the local day boundary', () => {
    const view = bonusPanel(world({ bonusNextId: 1, timestampLastBonus: NOW - DAY }), NOW, 0)!;
    assert.equal(view.ready, true);
    assert.equal(view.reset, false);
    assert.equal(view.day, 2);
  });

  it('flags a lapsed streak so the next claim restarts the cycle', () => {
    const view = bonusPanel(world({ bonusNextId: 4, timestampLastBonus: NOW - 3 * DAY }), NOW, 0)!;
    assert.equal(view.ready, true);
    assert.equal(view.reset, true);
  });

  it('wraps the next reward day after the fifth', () => {
    const view = bonusPanel(world({ bonusNextId: 5, timestampLastBonus: NOW - DAY }), NOW, 0)!;
    assert.equal(view.day, 1);
  });

  it('reads the weekly bonus as ready on Monday and collected after a claim', () => {
    const monday = NOW - DAY; // the day before the fixture's Tuesday
    const ready = bonusPanel(
      world({ timeStampMondayBonus: NOW - 8 * DAY, weeklyRewardIndex: 1 }),
      monday,
      0,
    )!;
    assert.equal(ready.weekly, 'ready');
    const collected = bonusPanel(world({ timeStampMondayBonus: monday }), monday, 0)!;
    assert.equal(collected.weekly, 'collected');
  });

  it('keeps the weekly bonus visible but not claimable on Sunday', () => {
    const sunday = NOW - 2 * DAY;
    const view = bonusPanel(world({ timeStampMondayBonus: NOW - 9 * DAY }), sunday, 0)!;
    assert.equal(view.weekly, 'not-ready');
  });

  it('uses the player offset for the local day and countdown', () => {
    // Two hours ahead puts the same instant on the next local day.
    const view = bonusPanel(world({ bonusNextId: 2, timestampLastBonus: NOW - 60 }), NOW, 2)!;
    assert.equal(view.ready, true);
    assert.equal(view.secondsToNextDay, 86_400);
  });

  it('is null when the save has no bonus keys', () => {
    assert.equal(bonusPanel(world(), NOW, 0), null);
  });

  it('never invents a reward day from a missing id', () => {
    const view = bonusPanel(world({ timestampLastBonus: NOW - DAY }), NOW, 0)!;
    assert.equal(view.day, 1);
  });
});
