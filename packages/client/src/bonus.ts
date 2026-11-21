/**
 * The bonus screens' model: the daily cycle and the weekly Monday bonus.
 *
 * The reward, the claim day and the claim timestamps all belong to the
 * server. This module reads them and turns them into what the screen can say;
 * it never advances a cycle, grants a prize or decides that a claim is due.
 * Every time value is passed in, so the same save and the same clock always
 * give the same view — there is no clock of its own here.
 */
import { dailyBonusReadiness, mondayBonusState, type MondayBonusState } from '@swl/rules';

import { bonusState } from './featurestate.ts';
import type { WorldSnapshot } from './session.ts';

/** What the bonus screens can say about the server's cycles. */
export interface BonusPanelView {
  /** The 1-based day of the daily cycle the next claim belongs to. */
  readonly day: number;
  /** Whether the server would accept a daily claim now. */
  readonly ready: boolean;
  /** Whether the streak has lapsed, so the next claim restarts the cycle. */
  readonly reset: boolean;
  /** Whole seconds until the next local day boundary, for display only. */
  readonly secondsToNextDay: number;
  /** The weekly (Monday) bonus's presentation state. */
  readonly weekly: MondayBonusState;
}

/** The local day index, counted from the epoch in the player's offset. */
function localDay(at: number, tzOffsetHours: number): number {
  return Math.floor((at / 3600 + tzOffsetHours) / 24);
}

/**
 * The day of the week the client numbers the Monday bonus with: Sunday is 0,
 * Monday is 1. 1970-01-01 was a Thursday, hence the offset of four.
 */
function weekDay(at: number, tzOffsetHours: number): number {
  return (((localDay(at, tzOffsetHours) + 4) % 7) + 7) % 7;
}

/**
 * Read the bonus screens' state, or null when the save predates the cycles.
 *
 * `now` and `tzOffsetHours` are the caller's: the clock belongs to the host,
 * not to this model. A missing claim timestamp reads as "never claimed", and
 * a missing cycle id reads as the first day — the only day the server's own
 * default (`bonusNextId = 0`) can lead to.
 */
export function bonusPanel(
  world: WorldSnapshot,
  now: number,
  tzOffsetHours: number,
): BonusPanelView | null {
  const state = bonusState(world);
  if (!state) return null;

  const last = state.lastBonusAt ?? 0;
  const readiness = dailyBonusReadiness(last, now, tzOffsetHours);
  const stored = state.nextBonusId ?? 0;
  const hour = (((now / 3600 + tzOffsetHours) % 24) + 24) % 24;
  const lastWeeklyDay = state.mondayBonusAt && state.mondayBonusAt > 0
    ? localDay(state.mondayBonusAt, tzOffsetHours)
    : null;

  return {
    day: stored >= 5 ? 1 : stored + 1,
    ready: readiness.ready,
    reset: readiness.reset,
    secondsToNextDay: Math.ceil((24 - hour) * 3600),
    weekly: mondayBonusState(weekDay(now, tzOffsetHours), lastWeeklyDay, localDay(now, tzOffsetHours)),
  };
}
