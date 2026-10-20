/**
 * The bonus cycles: the daily bonus, the weekly "Monday bonus" and the
 * alliance daily bonus.
 *
 * All three are **calendar** bonuses — they are claimed on a local day
 * boundary, not on a fixed interval — so a server-authoritative clone has
 * to know the player's time zone, or a bonus will be claimable twice or not
 * at all.
 */

/** The result of asking whether a bonus is ready. */
export interface BonusReadiness {
  /** Can the player claim it now? */
  ready: boolean;
  /** True when the streak restarts at day 1. */
  reset: boolean;
}

/**
 * Is the daily bonus ready?
 *
 * The client compares the day index of the last claim with the day index of
 * now, both in the player's local time:
 *
 * ```
 * floor((last  / 3600 + tz) / 24)   vs   floor((now / 3600 + tz) / 24)
 * ```
 *
 * `tz` is the player's time-zone offset **in hours**. The two are equal
 * when the bonus was already claimed today, and `reset` is true when the
 * player's streak has lapsed — in which case the next claim is day 1.
 */
export function dailyBonusReadiness(
  lastBonusAtSeconds: number,
  nowSeconds: number,
  tzOffsetHours: number,
): BonusReadiness {
  const lastDay = Math.floor((lastBonusAtSeconds / 3600 + tzOffsetHours) / 24);
  const nowDay = Math.floor((nowSeconds / 3600 + tzOffsetHours) / 24);
  if (lastDay === nowDay) return { ready: false, reset: false };
  return { ready: true, reset: lastDay < nowDay - 1 };
}

/** The daily bonus rewards: the gold for days 1-4, and 0 for day 5. */
export interface DailyBonusRules {
  /** One entry per day of the cycle. 0 means "a hero", not gold. */
  goldRewards: number[];
  /** The hero granted on the day with a 0 reward. */
  heroItemId: number;
}

/** The reward for a given day of the cycle, 1-based. */
export function dailyBonusReward(
  rules: DailyBonusRules,
  dayIndex: number,
): { gold: number; heroItemId: number | null } {
  const gold = rules.goldRewards[dayIndex - 1];
  if (gold === undefined) throw new RangeError(`no daily bonus for day ${dayIndex}`);
  return gold === 0 ? { gold: 0, heroItemId: rules.heroItemId } : { gold, heroItemId: null };
}

/** The day the player's streak is on, wrapping the cycle. */
export function nextDailyBonusDay(rules: DailyBonusRules, dayIndex: number): number {
  const length = rules.goldRewards.length;
  return (dayIndex % length) + 1;
}

/** A reward in the bonus tables. */
export interface BonusReward {
  /** `g` gold, `c` cash, `u` a unit. */
  type: string;
  /** The amount. For a unit reward, the list of possible units. */
  value: number | number[];
  /** For the alliance bonus, the member count this tier needs. */
  members?: number;
}

export interface MondayBonusRules {
  /** The three rewards of the outer cycle. */
  rewards: BonusReward[];
}

/**
 * The weekly reward.
 *
 * The outer cycle has **3** entries. The unit reward names 5 possible units,
 * and which one is given is chosen by `privateState.weeklyRewardIndex`.
 *
 * **The upstream server and the client disagree here.** The server computes
 * `weeklyRewardIndex = (weeklyRewardIndex + 1) % get_weekly_reward_length()`,
 * where the length is the longest list in the table (5), while the client
 * cycles the outer table every 3. The clone must pick one and record it;
 * the client behaviour is the specification.
 */
export function mondayBonusReward(
  rules: MondayBonusRules,
  outerIndex: number,
  unitIndex = 0,
): BonusReward {
  const reward = rules.rewards[outerIndex % rules.rewards.length];
  if (!reward) throw new RangeError(`no Monday bonus at index ${outerIndex}`);
  if (reward.type === 'u' && Array.isArray(reward.value)) {
    const unit = reward.value[unitIndex % reward.value.length];
    if (unit === undefined) throw new RangeError(`no unit at index ${unitIndex}`);
    return { type: reward.type, value: unit };
  }
  return reward;
}

/** The availability of the weekly bonus. */
export type MondayBonusState = 'hidden' | 'ready' | 'collected' | 'not-ready';

/** The days of the week, as the client's `Utils.getWeekDayFromTimeStamp` numbers them. */
export const WEEKDAY_SUNDAY = 0;
export const WEEKDAY_MONDAY = 1;

/**
 * The state of the weekly bonus.
 *
 * - **Monday** and not yet claimed today → `ready`
 * - **Monday** and already claimed today → `collected`
 * - **Sunday** → `not-ready`: visible, but not claimable
 * - any other day → `hidden`
 */
export function mondayBonusState(
  dayOfWeek: number,
  lastCollectedDay: number | null,
  today: number,
): MondayBonusState {
  if (dayOfWeek === WEEKDAY_SUNDAY) return 'not-ready';
  if (dayOfWeek !== WEEKDAY_MONDAY) return 'hidden';
  return lastCollectedDay === today ? 'collected' : 'ready';
}

/** The alliance daily bonus, which depends on the member count. */
export interface AllianceBonusRules {
  rewards: BonusReward[];
}

/**
 * The alliance daily bonus.
 *
 * The tiers are by member count: 0, 5, 25 and 45 members. The player gets
 * the **highest** tier they qualify for.
 */
export function allianceDailyBonus(
  rules: AllianceBonusRules,
  memberCount: number,
): BonusReward | null {
  let best: BonusReward | null = null;
  for (const reward of rules.rewards) {
    const required = reward.members ?? 0;
    if (memberCount >= required) best = reward;
  }
  return best;
}
