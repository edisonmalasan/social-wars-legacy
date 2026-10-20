import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  dueAt,
  finishCycle,
  isDue,
  periodMultiplier,
  periodSeconds,
  secondsUntilDue,
  startCycle,
  type ProductionCycle,
} from './production.ts';
import type { CollectPeriods } from './economy.ts';

const PERIODS: CollectPeriods = {
  minutes: [5, 60, 240, 480],
  multiplier: [0.25, 1, 2, 3],
};

describe('the collect periods', () => {
  it('are the client four', () => {
    assert.equal(PERIODS.minutes.length, 4);
    assert.equal(PERIODS.multiplier.length, 4);
  });

  it('last as long as the client says', () => {
    assert.equal(periodSeconds(1, PERIODS), 5 * 60);
    assert.equal(periodSeconds(2, PERIODS), 60 * 60);
    assert.equal(periodSeconds(3, PERIODS), 240 * 60);
    assert.equal(periodSeconds(4, PERIODS), 480 * 60);
  });

  it('are worth the client multipliers', () => {
    assert.equal(periodMultiplier(1, PERIODS), 0.25);
    assert.equal(periodMultiplier(2, PERIODS), 1);
    assert.equal(periodMultiplier(3, PERIODS), 2);
    assert.equal(periodMultiplier(4, PERIODS), 3);
  });

  it('refuse a period that does not exist', () => {
    assert.throws(() => periodSeconds(5, PERIODS), RangeError);
    assert.throws(() => periodMultiplier(0, PERIODS), RangeError);
  });
});

describe('the production cycle', () => {
  const cycle: ProductionCycle = { period: 2, startedAt: 1_000 };

  it('becomes due after the period', () => {
    assert.equal(dueAt(cycle, PERIODS), 1_000 + 60 * 60);
    assert.equal(isDue(cycle, PERIODS, 1_000 + 60 * 60 - 1), false);
    assert.equal(isDue(cycle, PERIODS, 1_000 + 60 * 60), true);
    assert.equal(isDue(cycle, PERIODS, 1_000 + 60 * 60 + 1), true);
  });

  it('counts down the seconds left', () => {
    assert.equal(secondsUntilDue(cycle, PERIODS, 1_000), 60 * 60);
    assert.equal(secondsUntilDue(cycle, PERIODS, 1_000 + 30 * 60), 30 * 60);
    assert.equal(secondsUntilDue(cycle, PERIODS, 1_000 + 60 * 60), 0);
  });

  it('is due at once for a building that never started', () => {
    const fresh: ProductionCycle = { period: 4, startedAt: 0 };
    assert.equal(dueAt(fresh, PERIODS), 0);
    assert.equal(isDue(fresh, PERIODS, 1_000), true);
    assert.equal(secondsUntilDue(fresh, PERIODS, 1_000), 0);
  });

  it('starts the countdown when the player chooses a period', () => {
    const started = startCycle(3, 5_000);
    assert.equal(started.period, 3);
    assert.equal(started.startedAt, 5_000);
    assert.equal(isDue(started, PERIODS, 5_000), false);
    assert.equal(isDue(started, PERIODS, 5_000 + 240 * 60), true);
  });

  it('restarts the countdown when the production is collected', () => {
    const finished = finishCycle(cycle, 100_000);
    assert.equal(finished.startedAt, 100_000);
    // The next collection is due after another full period.
    assert.equal(isDue(finished, PERIODS, 100_000 + 60 * 60 - 1), false);
    assert.equal(isDue(finished, PERIODS, 100_000 + 60 * 60), true);
  });
});
