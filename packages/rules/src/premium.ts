/**
 * The premium account.
 *
 * The premium is a **timestamp**, not a flag: the private state's
 * `timeStampEndPremium`. It is active while the server's clock is before
 * it, and the client checks that on every load
 * (`managers/PlayerStatus.as`: `premiumAccountTimeExpire =
 * privateState.timeStampEndPremium`).
 *
 * The packages are the content's `PREMIUM_ACCOUNTS`:
 *
 * ```json
 * [{ "price": 800, "time": 360 }, { "price": 450, "time": 180 }, ...]
 * ```
 *
 * The `time` is in **days** — a year, a half-year, a month, a week,
 * three days and a day.
 *
 * ## Buying
 *
 * The upstream's rule, which is the right one:
 *
 * ```python
 * if time_now >= ts_premium:
 *     privateState["timeStampEndPremium"] = time_now + days * 86400
 * else:
 *     privateState["timeStampEndPremium"] += days * 86400
 * ```
 *
 * So buying while the premium is still running **extends** it, and
 * buying after it has lapsed **starts it fresh**. The client does the same
 * with `premiumAccountTimeExpire` (`commands/CmdBuyPremiumAccount.as:13-23`).
 */

/** A premium package. */
export interface PremiumPackage {
  /** The cash price. */
  price: number;
  /** How many days the package grants. */
  time: number;
}

/** How many seconds a day is. */
export const SECONDS_PER_DAY = 86_400;

/** How many days a package grants. */
export function premiumDays(packages: readonly PremiumPackage[], index: number): number {
  const pack = packages[index];
  if (!pack) throw new RangeError(`no premium package ${index}`);
  return pack.time;
}

/**
 * When the premium expires, after buying a package.
 *
 * A purchase while the premium is still running **extends** it, and one
 * after it has lapsed **starts it fresh**.
 */
export function premiumExpiry(
  packages: readonly PremiumPackage[],
  index: number,
  now: number,
  currentExpiry = 0,
): number {
  const days = premiumDays(packages, index);
  if (currentExpiry > now) {
    // Still running: extend it.
    return currentExpiry + days * SECONDS_PER_DAY;
  }
  // Lapsed, or never bought: start it fresh.
  return now + days * SECONDS_PER_DAY;
}

/** Whether the premium is active. */
export function isPremiumActive(expiry: number, now: number): boolean {
  return expiry > now;
}

/** How many seconds are left before the premium lapses. */
export function secondsUntilPremiumExpiry(expiry: number, now: number): number {
  return Math.max(0, expiry - now);
}

/**
 * The premium's perks.
 *
 * The client checks `isPremiumUser` in several places, and each one is a
 * perk:
 *
 * - the **attacks a day**: 3 instead of 1
 *   (`GUI/GuiManager.as:244`)
 * - the **quest reward**: the premium share is paid in cash as well as the
 *   normal currency (`commands/CmdEndQuest.as:25`)
 * - the **assault reward**: the premium share on both sides
 *   (`commands/CmdEndAttack.as:18`)
 * - the **collection**: the premium share of the collected resource
 *   (`commands/CmdCollect.as:67`)
 *
 * They are listed here so the perks are named rather than scattered
 * through the client.
 */
export interface PremiumPerks {
  /** How many attacks a member may make a day. */
  attacksADay: number;
  /** The fraction of the reward the premium adds. */
  rewardShare: number;
}

/** The perks, and the plain ones for comparison. */
export const PREMIUM_PERKS: PremiumPerks = {
  attacksADay: 3,
  rewardShare: 0.5,
};

/** The perks without a premium. */
export const PLAIN_PERKS: PremiumPerks = {
  attacksADay: 1,
  rewardShare: 0,
};

/** The perks a player has. */
export function perksFor(expiry: number, now: number): PremiumPerks {
  return isPremiumActive(expiry, now) ? PREMIUM_PERKS : PLAIN_PERKS;
}
