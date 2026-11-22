import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import {
  MARKET_BUY,
  MARKET_EXHAUSTED,
  MARKET_NO_AMOUNTS,
  MARKET_NO_COUNTERS,
  MARKET_NO_WALLET,
  MARKET_SELL,
  MARKET_TITLE,
  marketDialog,
  marketPanel,
} from './state.ts';

/** The globals the original's own market reads. */
function globals(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    MARKET_BASE_COSTS: { o: 100, s: 150, w: 100 },
    MARKET_AMOUNT_TRADE: [100, 200, 300],
    MARKET_INCREMENT: 0.02,
    MARKET_SELL_PERCENTAGE: 0.75,
    MARKET_MAX_NUM_TRADES: 20,
    MARKET_PERIOD_HOURS: 20,
    ...overrides,
  };
}

function bundle(content: Record<string, unknown> = {}): ContentBundle {
  return {
    globals: globals(),
    items: [],
    levels: [],
    categories: {},
    magics: [],
    offerPacks: [],
    collections: [],
    expansionPrices: [],
    ...content,
  } as unknown as ContentBundle;
}

/** A server answer with the market's own keys written in the map and save. */
function world(
  map: Record<string, unknown> | null = null,
  resources: Record<string, unknown> = {},
  privateState: Record<string, unknown> = {},
): WorldSnapshot {
  const first: Record<string, unknown> = { id: 0, items: {} };
  if (map) Object.assign(first, map);
  return {
    maps: [first],
    resources: { g: 50, w: 10, o: 20, s: 30, c: 0, e: 0, x: 0, m: 0, ...resources },
    privateState,
  } as unknown as WorldSnapshot;
}

describe('the player-owned resource market', () => {
  it('renders an explicit empty state when the server published no counters', () => {
    const view = marketPanel(bundle(), world());
    assert.equal(view.counters, null);
    assert.ok(view.emptyMessages.includes(MARKET_NO_COUNTERS));
    // The wallet is still the server's; an absent counter invents no number.
    assert.deepEqual(view.wallet, { gold: 50, wood: 10, oil: 20, steel: 30 });
  });

  it('renders an explicit empty state for malformed server counters', () => {
    const view = marketPanel(
      bundle(),
      world(
        { numTradesDone: 'many', resourcesTraded: [], timestampLastTrade: 'never' },
        {},
        { marketPlaceFirstTime: true },
      ),
    );
    assert.equal(view.counters, null);
    assert.ok(view.emptyMessages.includes(MARKET_NO_COUNTERS));
  });

  it('renders an explicit empty state for a malformed server wallet', () => {
    const view = marketPanel(bundle(), world(null, { g: 'lots', w: -1 }));
    assert.equal(view.wallet, null);
    assert.ok(view.emptyMessages.includes(MARKET_NO_WALLET));
  });

  it('displays only the counters and wallet the server actually published', () => {
    const view = marketPanel(
      bundle(),
      world(
        {
          numTradesDone: 7,
          resourcesTraded: { w: 3, o: 2 },
          timestampLastTrade: 1_700_000_000,
        },
        { g: 999, w: 40, o: 41, s: 42 },
        { marketPlaceFirstTime: 'yes' },
      ),
    );
    assert.deepEqual(view.counters, {
      tradesDone: 7,
      resourcesTraded: { w: 3, o: 2 },
      lastTradeAt: 1_700_000_000,
      firstTime: 'yes',
    });
    assert.deepEqual(view.wallet, { gold: 999, wood: 40, oil: 41, steel: 42 });
  });

  it('does not compute a gold grant or any other client-side price', () => {
    const view = marketPanel(
      bundle({ globals: globals({ MARKET_BASE_COSTS: { w: 100 } }) }),
      world(null, { g: 7 }),
    );
    // The wallet is the server's number verbatim, never the content price
    // multiplied by an amount or by the number of trades.
    assert.equal(view.wallet?.gold, 7);
    // No field of the view is a computed cost, payout or grant. The only
    // price-like values are the content's raw numbers under `display`.
    assert.deepEqual(Object.keys(view).sort(), [
      'buyLabel',
      'counters',
      'display',
      'emptyMessages',
      'exhausted',
      'exhaustion',
      'resources',
      'sellLabel',
      'title',
      'wallet',
    ]);
    assert.deepEqual(view.display.baseCosts, { w: 100 });
    assert.equal(view.display.periodHours, 20);
    assert.equal(view.display.maxTrades, 20);
  });

  it('emits the catalogue buy command with the exact three-argument shape', () => {
    const view = marketPanel(bundle(), world());
    const wood = view.resources.find((entry) => entry.resource === 'w')!;
    assert.deepEqual(wood.buy.map((command) => command.args), [
      ['w', 0, 100],
      ['w', 0, 200],
      ['w', 0, 300],
    ]);
    for (const command of wood.buy) {
      assert.equal(command.name, 'trade_resource');
      assert.equal(command.map, 0);
    }
  });

  it('emits a sell command with 1, never the upstream comment’s 2', () => {
    const view = marketPanel(bundle(), world());
    const steel = view.resources.find((entry) => entry.resource === 's')!;
    assert.deepEqual(steel.sell.map((command) => command.args), [
      ['s', 1, 100],
      ['s', 1, 200],
      ['s', 1, 300],
    ]);
    for (const command of steel.sell) {
      assert.equal(command.name, 'trade_resource');
    }
  });

  it('keeps the exhaustion caption display-only and never blocks a request', () => {
    const view = marketPanel(
      bundle(),
      world({ numTradesDone: 20, resourcesTraded: { w: 20 }, timestampLastTrade: 1 }),
    );
    assert.equal(view.exhausted, true);
    assert.equal(view.exhaustion, MARKET_EXHAUSTED);
    // The caption is a sentence, not a gate: the buttons are still sent.
    assert.equal(view.resources.length, 3);
    for (const entry of view.resources) {
      assert.ok(entry.buy.length > 0);
      assert.ok(entry.sell.length > 0);
      assert.deepEqual(entry.buy[0]!.args, [entry.resource, 0, 100]);
      assert.deepEqual(entry.sell[0]!.args, [entry.resource, 1, 100]);
    }
    assert.ok(!('disabled' in view));
    assert.ok(!('blocked' in view));
  });

  it('offers no trade controls when the content lists no trade amounts', () => {
    const view = marketPanel(
      bundle({ globals: globals({ MARKET_AMOUNT_TRADE: 'none' }) }),
      world(),
    );
    assert.ok(view.emptyMessages.includes(MARKET_NO_AMOUNTS));
    assert.ok(view.resources.every((entry) => entry.buy.length === 0 && entry.sell.length === 0));
  });

  it('uses the client’s own literals and the one shared dialog slot', () => {
    assert.equal(MARKET_BUY, 'Buy');
    assert.equal(MARKET_SELL, 'sell');
    assert.deepEqual(marketDialog(), {
      id: 'market-panel',
      kind: 'alert',
      title: MARKET_TITLE,
    });
  });
});
