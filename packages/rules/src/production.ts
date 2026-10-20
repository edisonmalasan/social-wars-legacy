/**
 * The production cycle.
 *
 * A resource building does not produce on a timer the server sets. The
 * **player chooses** how long to wait, and the building then fills up:
 *
 * ```as3
 * // GUI/PopupCollect.as:59-61
 * txTime    = dhms3(COLLECT_MINUTES[i] * 60);
 * txCollect = floor(params.collect * COLLECT_MULTIPLIER[i]);
 * ```
 *
 * Four options: **5 minutes at 0.25**, **60 at 1**, **240 at 2** and
 * **480 at 3**. The multiplier is how many cycles' worth of the base
 * production the wait is worth, so waiting eight hours gives three times
 * the base amount.
 *
 * Choosing an option starts the countdown
 * (`IsoElement.initCollectTimer`, `core/isoengine/IsoElement.as:1034`),
 * and the collection happens when it fires.
 *
 * **The upstream never checks that the player waited.** Its `collect`
 * handler resets the timestamp and believes whatever the client sends.
 * The server has to own the clock, so this module decides whether a
 * collection is due.
 */
import type { CollectPeriods } from './economy.ts';

/** A building's production cycle. */
export interface ProductionCycle {
  /**
   * The period the player chose, **1-based**.
   *
   * It is the building's `cp` attribute.
   */
  period: number;
  /**
   * When the countdown started, in seconds.
   *
   * Zero means the building has never been started, and every period is
   * due immediately: a fresh building can be collected at once.
   */
  startedAt: number;
}

/** How long a period takes, in seconds. */
export function periodSeconds(period: number, periods: CollectPeriods): number {
  const minutes = periods.minutes[period - 1];
  if (minutes === undefined) {
    throw new RangeError(`no collect period ${period}`);
  }
  return minutes * 60;
}

/** The multiplier a period is worth. */
export function periodMultiplier(period: number, periods: CollectPeriods): number {
  const multiplier = periods.multiplier[period - 1];
  if (multiplier === undefined) {
    throw new RangeError(`no collect period ${period}`);
  }
  return multiplier;
}

/** When the production becomes due, in seconds. */
export function dueAt(cycle: ProductionCycle, periods: CollectPeriods): number {
  if (cycle.startedAt <= 0) return 0;
  return cycle.startedAt + periodSeconds(cycle.period, periods);
}

/** Whether the production is due at `now`. */
export function isDue(
  cycle: ProductionCycle,
  periods: CollectPeriods,
  now: number,
): boolean {
  return now >= dueAt(cycle, periods);
}

/** How many seconds are left before the production is due. */
export function secondsUntilDue(
  cycle: ProductionCycle,
  periods: CollectPeriods,
  now: number,
): number {
  const due = dueAt(cycle, periods);
  if (due <= 0) return 0;
  return Math.max(0, due - now);
}

/**
 * Start a production cycle.
 *
 * This is what choosing a period does: the countdown starts now.
 */
export function startCycle(period: number, now: number): ProductionCycle {
  return { period, startedAt: now };
}

/**
 * Finish a production cycle.
 *
 * The countdown restarts, and the next collection is due after another
 * full period.
 */
export function finishCycle(cycle: ProductionCycle, now: number): ProductionCycle {
  return { period: cycle.period, startedAt: now };
}
