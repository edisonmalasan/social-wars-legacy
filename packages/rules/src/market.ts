/**
 * The market.
 *
 * Two markets exist: the player's own market, where they trade wood, oil
 * and steel for gold, and the allies market, where a friends' building
 * delivers a resource.
 *
 * The upstream Python server implements **neither** — it only counts the
 * trades (`command.py` handles `trade_resource` by incrementing a counter)
 * and applies whatever gold delta the client declared. A server-authoritative
 * clone has to price the trade itself.
 *
 * ## The own market
 *
 * ```
 * cost = round( base * (amount / 100) * (1 + trades[resource] * MARKET_INCREMENT) )
 * ```
 *
 * and on a **sell** the price is further reduced:
 *
 * ```
 * cost = round( cost * MARKET_SELL_PERCENTAGE )
 * ```
 *
 * `base` is the gold price of 100 units: 100 for wood, 100 for oil and 150
 * for steel. `MARKET_INCREMENT` is 2 %, so every trade already made in the
 * current period makes the next one 2 % dearer.
 *
 * There are at most `MARKET_MAX_NUM_TRADES` trades per
 * `MARKET_PERIOD_HOURS` hours, and the counter resets once
 * `now - timestampLastTrade` exceeds the period.
 */

/** The resources the own market trades, and gold, the currency. */
export type MarketResource = 'w' | 'o' | 's' | 'g';

export interface MarketRules {
  /** The gold price of 100 units, per resource. */
  baseCosts: Record<string, number>;
  /** The tradeable amounts. */
  amounts: number[];
  /** The percentage each prior trade adds to the price. */
  increment: number;
  /** The fraction of the price paid when selling. */
  sellPercentage: number;
  /** The most trades per period. */
  maxTrades: number;
  /** The length of the period, in hours. */
  periodHours: number;
}

/**
 * The price of a trade, in gold.
 *
 * @param tradesSoFar how many trades of this resource have been made in the
 *                     current period — each one makes the price 2 % higher
 * @param selling     true when the player is selling rather than buying
 */
export function marketPrice(
  rules: MarketRules,
  resource: string,
  amount: number,
  tradesSoFar: number,
  selling = false,
): number {
  const base = rules.baseCosts[resource];
  if (base === undefined) throw new RangeError(`the market does not trade ${resource}`);
  if (!rules.amounts.includes(amount)) {
    throw new RangeError(`the market does not trade ${amount} units`);
  }

  const marked = base * (amount / 100) * (1 + tradesSoFar * rules.increment);
  const cost = Math.round(marked);
  return selling ? Math.round(cost * rules.sellPercentage) : cost;
}

/** The state of the player's trade counter. */
export interface MarketPeriod {
  /** How many trades have been made in the current period. */
  trades: number;
  /** When the last trade was made, in seconds. */
  lastTradeAt: number;
}

/**
 * The trade counter, after a period boundary.
 *
 * The counter resets when more than `periodHours` have passed since the last
 * trade. The upstream `engine.py` resets *daily* instead, which disagrees
 * with the client's 20-hour period — a mismatch worth recording, because the
 * two disagree on exactly when a player may trade again.
 */
export function marketPeriod(
  rules: MarketRules,
  current: MarketPeriod,
  nowSeconds: number,
): MarketPeriod {
  const periodSeconds = 3600 * rules.periodHours;
  if (nowSeconds - current.lastTradeAt > periodSeconds) {
    return { trades: 0, lastTradeAt: current.lastTradeAt };
  }
  return current;
}

/** Can the player make another trade? */
export function canTrade(rules: MarketRules, current: MarketPeriod): boolean {
  return current.trades < rules.maxTrades;
}

/** The result of attempting a trade. */
export type TradeResult =
  | { ok: true; cost: number; trades: number }
  | { ok: false; reason: 'too-many-trades' | 'unknown-resource' | 'unknown-amount' };

/**
 * Make a trade.
 *
 * The counter is incremented for the resource traded, and the price is what
 * the player pays (or receives, when selling).
 */
export function trade(
  rules: MarketRules,
  current: MarketPeriod,
  resource: string,
  amount: number,
  selling = false,
): TradeResult {
  const period = marketPeriod(rules, current, current.lastTradeAt);
  if (!canTrade(rules, period)) {
    return { ok: false, reason: 'too-many-trades' };
  }
  try {
    const cost = marketPrice(rules, resource, amount, period.trades, selling);
    return { ok: true, cost, trades: period.trades + 1 };
  } catch (error) {
    const reason =
      error instanceof RangeError && String(error.message).includes('units')
        ? 'unknown-amount'
        : 'unknown-resource';
    return { ok: false, reason };
  }
}

export interface AlliesMarketRules {
  /** What the market delivers with no helpers. */
  initialCollect: Record<string, number>;
  /** What each additional helper adds. */
  incrementalCollect: Record<string, number>;
}

/**
 * What the allies market delivers.
 *
 * `Config.RESOURCES_MARKET_PER_ALLY = 125` — each additional helper adds
 * 125 units of whichever resource the market is currently offering.
 */
export function alliesMarketCollect(
  rules: AlliesMarketRules,
  resource: string,
  helpers: number,
): number {
  const initial = rules.initialCollect[resource];
  if (initial === undefined) return 0;
  const incremental = rules.incrementalCollect[resource] ?? 0;
  const extra = Math.max(0, helpers - 1);
  return initial + extra * incremental;
}
