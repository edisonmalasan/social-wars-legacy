import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  alliesMarketCollect,
  canTrade,
  marketPeriod,
  marketPrice,
  trade,
  type AlliesMarketRules,
  type MarketRules,
} from './market.ts';
import {
  allianceDailyBonus,
  dailyBonusReadiness,
  dailyBonusReward,
  mondayBonusReward,
  mondayBonusState,
  nextDailyBonusDay,
  WEEKDAY_MONDAY,
  WEEKDAY_SUNDAY,
  type AllianceBonusRules,
  type BonusReward,
  type DailyBonusRules,
  type MondayBonusRules,
} from './bonuses.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

/** A UTC timestamp from an ISO string, so the calendar tests read clearly. */
function at(iso: string): number {
  return Math.floor(Date.parse(iso) / 1000);
}
async function globals(): Promise<Record<string, unknown>> {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as { globals: Record<string, unknown> };
  return bundle.globals;
}

describe('the market', () => {
  const rules = (g: Record<string, unknown>): MarketRules => ({
    baseCosts: g['MARKET_BASE_COSTS'] as Record<string, number>,
    amounts: g['MARKET_AMOUNT_TRADE'] as number[],
    increment: g['MARKET_INCREMENT'] as number,
    sellPercentage: g['MARKET_SELL_PERCENTAGE'] as number,
    maxTrades: g['MARKET_MAX_NUM_TRADES'] as number,
    periodHours: g['MARKET_PERIOD_HOURS'] as number,
  });

  it('uses the shipped prices and limits', async () => {
    const g = await globals();
    const r = rules(g);
    assert.deepEqual(r.baseCosts, { o: 100, s: 150, w: 100 });
    assert.deepEqual(r.amounts, [100, 200, 300]);
    assert.equal(r.increment, 0.02);
    assert.equal(r.sellPercentage, 0.75);
    assert.equal(r.maxTrades, 20);
    assert.equal(r.periodHours, 20);
  });

  it('prices 100 units at the base cost', async () => {
    const r = rules(await globals());
    assert.equal(marketPrice(r, 'w', 100, 0), 100);
    assert.equal(marketPrice(r, 'o', 100, 0), 100);
    assert.equal(marketPrice(r, 's', 100, 0), 150);
  });

  it('scales the price with the amount', async () => {
    const r = rules(await globals());
    assert.equal(marketPrice(r, 'w', 200, 0), 200);
    assert.equal(marketPrice(r, 'w', 300, 0), 300);
    assert.equal(marketPrice(r, 's', 200, 0), 300);
  });

  it('adds 2% for every trade already made', async () => {
    const r = rules(await globals());
    assert.equal(marketPrice(r, 'w', 100, 1), 102);
    assert.equal(marketPrice(r, 'w', 100, 5), 110);
    assert.equal(marketPrice(r, 's', 100, 5), 165);
  });

  it('pays 75% when selling', async () => {
    const r = rules(await globals());
    assert.equal(marketPrice(r, 'w', 100, 0, true), 75);
    assert.equal(marketPrice(r, 's', 100, 0, true), 113); // round(150 * 0.75)
  });

  it('rejects an unknown resource or amount', async () => {
    const r = rules(await globals());
    assert.throws(() => marketPrice(r, 'x', 100, 0), RangeError);
    assert.throws(() => marketPrice(r, 'w', 500, 0), RangeError);
  });

  it('resets the counter after the 20-hour period', async () => {
    const r = rules(await globals());
    const now = 1_000_000;
    const current = { trades: 12, lastTradeAt: now };
    // Still inside the period.
    assert.equal(marketPeriod(r, current, now + 3600 * 19).trades, 12);
    // Past the period.
    assert.equal(marketPeriod(r, current, now + 3600 * 21).trades, 0);
  });

  it('stops at 20 trades', async () => {
    const r = rules(await globals());
    assert.equal(canTrade(r, { trades: 19, lastTradeAt: 0 }), true);
    assert.equal(canTrade(r, { trades: 20, lastTradeAt: 0 }), false);
    const result = trade(r, { trades: 20, lastTradeAt: 0 }, 'w', 100);
    assert.equal(result.ok, false);
  });

  it('counts the trade', async () => {
    const r = rules(await globals());
    const result = trade(r, { trades: 3, lastTradeAt: 0 }, 'w', 100);
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.equal(result.cost, 106);
      assert.equal(result.trades, 4);
    }
  });
});

describe('the allies market', () => {
  it('gives 125 with no helpers and 125 more per helper', async () => {
    const g = await globals();
    const rules: AlliesMarketRules = {
      initialCollect: g['ALLIES_MARKET_INITIAL_COLLECT'] as Record<string, number>,
      incrementalCollect: g['ALLIES_MARKET_INCREMENTAL_COLLECT'] as Record<string, number>,
    };
    assert.equal(alliesMarketCollect(rules, 'w', 0), 125);
    assert.equal(alliesMarketCollect(rules, 'w', 1), 125);
    assert.equal(alliesMarketCollect(rules, 'w', 2), 250);
    assert.equal(alliesMarketCollect(rules, 'w', 5), 625);
    assert.equal(alliesMarketCollect(rules, 'g', 3), 375);
  });
});

describe('the daily bonus', () => {
  const rules: DailyBonusRules = { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1055 };

  it('uses the shipped 5-day cycle', async () => {
    const g = await globals();
    assert.deepEqual(g['DAILY_GOLD_REWARDS'], [100, 250, 500, 1000, 0]);
  });

  it('gives gold on days 1-4 and a hero on day 5', () => {
    assert.deepEqual(dailyBonusReward(rules, 1), { gold: 100, heroItemId: null });
    assert.deepEqual(dailyBonusReward(rules, 4), { gold: 1000, heroItemId: null });
    assert.deepEqual(dailyBonusReward(rules, 5), { gold: 0, heroItemId: 1055 });
  });

  it('wraps the cycle', () => {
    assert.equal(nextDailyBonusDay(rules, 1), 2);
    assert.equal(nextDailyBonusDay(rules, 4), 5);
    assert.equal(nextDailyBonusDay(rules, 5), 1);
  });

  it('is not ready twice on the same local day', () => {
    const now = at('2026-01-02T12:00:00Z');
    assert.deepEqual(dailyBonusReadiness(now, now + 3600, 0), {
      ready: false,
      reset: false,
    });
    // A day later it is ready again.
    assert.deepEqual(dailyBonusReadiness(now, now + 86_400, 0), {
      ready: true,
      reset: false,
    });
  });

  it('restarts the streak when a day was missed', () => {
    const now = at('2026-01-02T12:00:00Z');
    // Two days later: the streak lapsed.
    assert.deepEqual(dailyBonusReadiness(now, now + 2 * 86_400, 0), {
      ready: true,
      reset: true,
    });
  });

  it('respects the time zone', () => {
    // The last claim was at 23:00 UTC on the 2nd; now is 00:00 UTC on the 3rd.
    const last = at('2026-01-02T23:00:00Z');
    const now = at('2026-01-03T00:00:00Z');
    // In UTC the local day rolled over, so the bonus is ready.
    assert.equal(dailyBonusReadiness(last, now, 0).ready, true);
    // At UTC-3 it is still 21:00 on the same local day, so it is not ready.
    assert.equal(dailyBonusReadiness(last, now, -3).ready, false);
    // At UTC+3 the last claim was already tomorrow, so the day has not rolled.
    assert.equal(dailyBonusReadiness(last, now, 3).ready, false);
  });
});

describe('the Monday bonus', () => {
  const rules: MondayBonusRules = {
    rewards: [
      { type: 'g', value: 2500 },
      { type: 'u', value: [1055, 1033, 1046, 1063, 1198] },
      { type: 'c', value: 5 },
    ] as BonusReward[],
  };

  it('cycles the outer table every three', async () => {
    const g = await globals();
    assert.equal((g['MONDAY_BONUS_REWARDS'] as unknown[]).length, 3);
    assert.deepEqual(mondayBonusReward(rules, 0).value, 2500);
    assert.deepEqual(mondayBonusReward(rules, 2).value, 5);
    assert.deepEqual(mondayBonusReward(rules, 3).value, 2500);
  });

  it('picks the unit from the five', () => {
    assert.deepEqual(mondayBonusReward(rules, 1, 0).value, 1055);
    assert.deepEqual(mondayBonusReward(rules, 1, 4).value, 1198);
    assert.deepEqual(mondayBonusReward(rules, 1, 5).value, 1055); // wraps
  });

  it('is hidden except on Sunday and Monday', () => {
    assert.equal(mondayBonusState(WEEKDAY_MONDAY, null, 1), 'ready');
    assert.equal(mondayBonusState(WEEKDAY_MONDAY, 1, 1), 'collected');
    assert.equal(mondayBonusState(WEEKDAY_SUNDAY, null, 0), 'not-ready');
    assert.equal(mondayBonusState(3, null, 3), 'hidden');
  });
});

describe('the alliance daily bonus', () => {
  it('gives the highest tier the member count qualifies for', async () => {
    const g = await globals();
    const rules: AllianceBonusRules = {
      rewards: g['ALLIANCE_DAILY_BONUS_REWARDS'] as BonusReward[],
    };
    assert.deepEqual(allianceDailyBonus(rules, 0)?.value, 150);
    assert.deepEqual(allianceDailyBonus(rules, 4)?.value, 150);
    assert.deepEqual(allianceDailyBonus(rules, 5)?.value, 1500);
    assert.deepEqual(allianceDailyBonus(rules, 25)?.value, 5000);
    assert.deepEqual(allianceDailyBonus(rules, 45)?.value, 1);
    assert.deepEqual(allianceDailyBonus(rules, 100)?.value, 1);
  });
});
