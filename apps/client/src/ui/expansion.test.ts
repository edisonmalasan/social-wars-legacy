import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import {
  EXPANSION_BUY_FOR,
  EXPANSION_CASH_PROMPT,
  EXPANSION_CELEBRATION_HEADING,
  EXPANSION_CELEBRATION_MESSAGE,
  EXPANSION_GOLD_PROMPT,
  EXPANSION_NEIGHBOURS_PROMPT,
  EXPANSION_RESULT_ID,
  expansionPanel,
  expansionResultPanel,
} from './state.ts';

const FREE = { coins: 0, cash: 0, neighbors: 0, inventory_qte: 0 };

/** A content bundle whose rows are placed at ordinal 3, after three free ones. */
function bundle(rows: readonly unknown[]): ContentBundle {
  return {
    items: [],
    collections: [],
    globals: {},
    categories: {},
    expansionPrices: [FREE, FREE, FREE, ...rows],
  } as unknown as ContentBundle;
}

/** A world whose owned tiles and wallet are the server's. */
function world(owned: number[], gold = 0, cash = 0): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {}, expansions: [...owned] }],
    resources: { g: gold, w: 0, o: 0, s: 0, c: cash, e: 0, x: 0, m: 0 },
    privateState: {},
  } as unknown as WorldSnapshot;
}

const ROW = { coins: 2500, cash: 5, neighbors: 1, inventory_qte: 0 };

describe('the expansion button prompt and messages', () => {
  it('reads the buy-for prompt and the price from the content row', () => {
    const view = expansionPanel(bundle([ROW]), world([35, 36, 45]))!;
    assert.equal(view.buyFor, EXPANSION_BUY_FOR);
    assert.equal(view.buyFor, 'buy for');
    assert.equal(view.coins, 2500);
    assert.equal(view.cash, 5);
    assert.equal(view.owned, 3);
    assert.equal(view.tileId, 46);
    assert.deepEqual(view.command, { map: 0, name: 'expand', args: [46] });
  });

  it('shows only the unmet requirements named by the content row', () => {
    const short = expansionPanel(bundle([ROW]), world([35, 36, 45], 100, 0), 0)!;
    assert.deepEqual(
      short.prompts.map((prompt) => prompt.kind),
      ['cash', 'gold', 'neighbours'],
    );
    assert.equal(short.prompts[0]!.needed, 5);
    assert.equal(short.prompts[0]!.have, 0);
    assert.equal(short.prompts[0]!.text, EXPANSION_CASH_PROMPT);
    assert.equal(short.prompts[1]!.text, EXPANSION_GOLD_PROMPT);
    assert.equal(short.prompts[2]!.text, EXPANSION_NEIGHBOURS_PROMPT);
  });

  it('shows no prompt when the server already owns enough', () => {
    const view = expansionPanel(bundle([ROW]), world([35, 36, 45], 3000, 50), 4)!;
    assert.deepEqual(view.prompts, []);
  });

  it('does not guess a neighbour count the host never fetched', () => {
    const view = expansionPanel(bundle([ROW]), world([35, 36, 45], 3000, 50))!;
    assert.deepEqual(view.prompts, []);
  });

  it('adds no prompt for a row that names no requirement', () => {
    const view = expansionPanel(
      bundle([{ coins: 0, cash: 0, neighbors: 0, inventory_qte: 0 }]),
      world([35, 36, 45]),
      0,
    )!;
    assert.deepEqual(view.prompts, []);
  });
});

describe('the post-purchase growth result', () => {
  it('is null when the server answered no growth', () => {
    const before = 3;
    const refused = world([35, 36, 45]);
    assert.equal(expansionResultPanel(bundle([ROW]), refused, before), null);
    assert.equal(expansionResultPanel(bundle([ROW]), refused, 4), null);
    assert.equal(expansionResultPanel(bundle([ROW]), refused, -1), null);
  });

  it('reads the new tile and the content price from the server answer', () => {
    const view = expansionResultPanel(bundle([ROW]), world([35, 36, 45, 46]), 3)!;
    assert.equal(view.before, 3);
    assert.equal(view.after, 4);
    assert.deepEqual(view.tiles, [46]);
    assert.equal(view.coins, 2500);
    assert.equal(view.cash, 5);
    assert.equal(view.heading, EXPANSION_CELEBRATION_HEADING);
    assert.equal(view.message, EXPANSION_CELEBRATION_MESSAGE);
    assert.equal(view.message, 'Your empire has GROWN!');
    assert.equal(EXPANSION_RESULT_ID, 'expansion-result');
  });

  it('drops a malformed new tile rather than claiming it', () => {
    assert.equal(expansionResultPanel(bundle([ROW]), world([35, 36, 45, 0]), 3), null);
    assert.equal(
      expansionResultPanel(bundle([ROW]), world([35, 36, 45, '47' as unknown as number]), 3),
      null,
    );
  });

  it('still reads growth when the content has no price row', () => {
    const view = expansionResultPanel(bundle([]), world([35, 36, 45, 47]), 3)!;
    assert.deepEqual(view.tiles, [47]);
    assert.equal(view.coins, null);
    assert.equal(view.cash, null);
  });
});
