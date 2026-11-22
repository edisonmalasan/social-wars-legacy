import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import {
  STORE_BUY_FOR,
  STORE_EARNINGS,
  STORE_LIMITED_OFFER,
  STORE_NO_PACKS,
  STORE_NO_WALLET,
  storeItemsPanel,
} from './state.ts';

/** A well-formed content offer pack, with the fields the store reads. */
function pack(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 1,
    name: 'starter pack',
    type: '',
    enabled: 1,
    position: 6,
    cost_cash: 25,
    gold: 5000,
    wood: 0,
    oil: 0,
    steel: 0,
    mana: 0,
    xp: 0,
    items: [1042, 84],
    ...over,
  };
}

function bundle(offerPacks: unknown): ContentBundle {
  return {
    globals: {},
    items: [],
    levels: [],
    categories: {},
    magics: [],
    offerPacks,
    collections: [],
    expansionPrices: [],
  } as unknown as ContentBundle;
}

/** A server answer with the wallet's cash slot written to the given value. */
function world(cash: unknown): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {} }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: cash, e: 0, x: 0, m: 0 },
    privateState: {},
  } as unknown as WorldSnapshot;
}

describe("the store front's item-button chrome", () => {
  it('takes affordability from the server wallet only', () => {
    const rows = [pack()];
    const rich = storeItemsPanel(bundle(rows), world(30));
    assert.equal(rich.cash, 30);
    assert.equal(rich.packs[0]!.affordable, true);

    const poor = storeItemsPanel(bundle(rows), world(10));
    assert.equal(poor.cash, 10);
    assert.equal(poor.packs[0]!.affordable, false);
    // The unaffordable pack is still shown so the player can see the cost;
    // it can still ask the server, which decides whether to accept.
    assert.ok(poor.packs[0]!.command);
  });

  it('shows only the content bundle\'s names, prices and amounts', () => {
    const view = storeItemsPanel(
      bundle([pack({ name: 'Warrior Crate', cost_cash: 42, gold: 900, wood: 30 })]),
      world(100),
    );
    assert.equal(view.packs.length, 1);
    assert.equal(view.packs[0]!.name, 'Warrior Crate');
    assert.equal(view.packs[0]!.price, 42);
    assert.deepEqual(view.packs[0]!.contents, [
      { key: 'gold', amount: 900 },
      { key: 'wood', amount: 30 },
    ]);

    const malformed = storeItemsPanel(
      bundle([pack({ gold: 'lots', wood: -2, oil: Number.NaN })]),
      world(100),
    );
    assert.deepEqual(malformed.packs[0]!.contents, []);
  });

  it('emits exactly one buy_offer_pack request from the catalogue', () => {
    const view = storeItemsPanel(bundle([pack()]), world(30));
    const command = view.packs[0]!.command!;
    assert.equal(command.map, 0);
    assert.equal(command.name, 'buy_offer_pack');
    assert.deepEqual(command.args, [1, '[1042,84]']);
  });

  it('sends a super pack\'s tier selection, never a computed price', () => {
    const rows = [pack({
      id: 19,
      type: 'super',
      items: [[1042], [1004, 1005], [1060, 1061, 1062, 1063]],
    })];
    const view = storeItemsPanel(bundle(rows), world(100));
    const superPack = view.packs[0]!;
    assert.equal(superPack.shape, 'super');
    assert.equal(superPack.command, null);
    assert.deepEqual(
      superPack.tiers.map((tier) => tier.command.args),
      [
        [19, '[1042]'],
        [19, '[1042,1004]'],
        [19, '[1042,1004,1005,1060]'],
      ],
    );
    for (const tier of superPack.tiers) {
      assert.equal(tier.command.name, 'buy_offer_pack');
      assert.equal(tier.command.map, 0);
    }
  });

  it('computes no grant, reward or payout of its own', () => {
    const view = storeItemsPanel(bundle([pack()]), world(30));
    assert.deepEqual(Object.keys(view).sort(), [
      'buyFor',
      'cash',
      'earnings',
      'emptyMessages',
      'limitedOffer',
      'packs',
    ]);
    const keys = [...Object.keys(view), ...Object.keys(view.packs[0]!)];
    assert.ok(
      keys.every((key) => !/grant|reward|payout|credited|award/i.test(key)),
      keys.join(', '),
    );
  });

  it('renders explicit empty states for absent or malformed content or wallet', () => {
    const noContent = storeItemsPanel(bundle([]), world(30));
    assert.deepEqual(noContent.packs, []);
    assert.ok(noContent.emptyMessages.includes(STORE_NO_PACKS));

    const noWallet = storeItemsPanel(bundle([pack()]), world('lots'));
    assert.equal(noWallet.cash, null);
    assert.deepEqual(noWallet.packs, []);
    assert.ok(noWallet.emptyMessages.includes(STORE_NO_WALLET));

    const notAnArray = storeItemsPanel(bundle('none'), world(30));
    assert.ok(notAnArray.emptyMessages.includes(STORE_NO_PACKS));
    assert.deepEqual(notAnArray.packs, []);
  });

  it('uses the client\'s own captions, never a server-written limit warning', () => {
    const view = storeItemsPanel(bundle([]), world(0));
    assert.equal(STORE_LIMITED_OFFER, 'Limited Offer');
    assert.equal(STORE_EARNINGS, 'EARNINGS:');
    assert.equal(STORE_BUY_FOR, 'BUY FOR:');
    assert.equal(view.limitedOffer, STORE_LIMITED_OFFER);
    assert.equal(view.earnings, STORE_EARNINGS);
    assert.equal(view.buyFor, STORE_BUY_FOR);
    assert.ok(
      !view.emptyMessages.some((message) => /limit reached/i.test(message)),
      'no server-owned limit exists, so no limit warning is drawn',
    );
  });

  it('draws the art from original inline geometry with no external references', async () => {
    const source = await readFile(new URL('./storeitems.tsx', import.meta.url), 'utf8');
    assert.match(source, /<svg\b/);
    assert.doesNotMatch(source, /xlink:href|<image\b|<img\b|\bhref\s*=|\bsrc\s*=|url\s*\(/i);
    assert.doesNotMatch(source, /\.(png|jpe?g|gif|webp|svg)\b/i);
    assert.doesNotMatch(source, /https?:\/\//i);
  });
});
