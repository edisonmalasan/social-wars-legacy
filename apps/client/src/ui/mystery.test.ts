import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import {
  MYSTERY_CONGRATULATIONS,
  MYSTERY_OK,
  MYSTERY_PROMPT,
  MYSTERY_TITLE,
  RARITY_COMMON,
  RARITY_RARE,
  RARITY_UNCOMMON,
  SUPER_ONLY_THIS_WEEK,
  SUPER_STORAGE,
  SUPER_TITLE,
  SUPER_VALUE,
  mysteryBoxes,
  mysteryBoxPanel,
  mysteryResultPanel,
  storeQuantities,
  type MysteryPurchase,
} from './state.ts';

/** A content bundle with just the items and packs these tests name. */
function bundle(packs: readonly unknown[]): ContentBundle {
  const names: readonly (readonly [number, string])[] = [
    [67, 'Rare relic'],
    [85, 'Uncommon relic'],
    [1046, 'Common relic'],
    [1037, 'Common charm'],
    [1210, 'Super rare'],
    [1223, 'Super uncommon'],
    [1238, 'Super common'],
  ];
  return {
    items: names.map(([id, name]) => ({ id, name, type: 'u' })),
    offerPacks: [...packs],
  } as unknown as ContentBundle;
}

/** The random pack, as the shipped content stores it (four id/threshold pairs). */
function randomPack(overrides: Record<string, unknown> = {}): unknown {
  return {
    id: 4,
    name: 'Mistery Box 1',
    type: '',
    enabled: 1,
    position: 1,
    cost_cash: 20,
    items: [[67, 35], [85, 70], [1046, 90], [1037, 100]],
    ...overrides,
  };
}

/** A super pack with one rare, one uncommon and one common row. */
function superPack(id = 44, overrides: Record<string, unknown> = {}): unknown {
  return {
    id,
    name: 'New Mistery Box',
    type: 'super',
    enabled: 1,
    position: 1,
    cost_cash: 60,
    // Four per row, so the four-item tier can be selected from the content.
    items: [
      [1210, 1211, 1212, 1213],
      [1223, 1224, 1225, 1226],
      [1238, 1239, 1240, 1241],
    ],
    ...overrides,
  };
}

/** A server world whose store holds these quantities. */
function world(store: Record<string, number> = {}): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {}, store }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState: {},
  } as unknown as WorldSnapshot;
}

function purchase(overrides: Partial<MysteryPurchase> = {}): MysteryPurchase {
  return {
    kind: 'mystery',
    packId: 4,
    title: MYSTERY_TITLE,
    price: 20,
    command: { map: 0, name: 'buy_offer_pack', args: [4, '[67]'] },
    ...overrides,
  };
}

describe('the mystery-box preview', () => {
  it('draws pack 4’s four candidates with the original’s rarity labels', () => {
    const view = mysteryBoxPanel(bundle([randomPack()]), 4, 100)!;
    assert.ok(view);
    assert.equal(view.kind, 'mystery');
    assert.equal(view.title, MYSTERY_TITLE);
    assert.equal(view.prompt, MYSTERY_PROMPT);
    assert.deepEqual(
      view.rows.map((row) => [row.label, row.items.map((entry) => entry.itemId)]),
      [
        [RARITY_RARE, [67]],
        [RARITY_UNCOMMON, [85]],
        [RARITY_COMMON, [1046]],
        [RARITY_COMMON, [1037]],
      ],
    );
    assert.equal(view.rows[0]!.items[0]!.name, 'Rare relic');
    assert.equal(view.banner, null);
    assert.equal(view.weekNote, null);
    assert.equal(view.tiers.length, 1);
    assert.equal(view.tiers[0]!.price, 20);
    assert.equal(view.tiers[0]!.affordable, true);
    assert.deepEqual(view.tiers[0]!.command.args, [4, '[67,85,1046,1037]']);
  });

  it('shows a hidden pack’s prizes but offers no buy the server would refuse', () => {
    const view = mysteryBoxPanel(
      bundle([randomPack({ enabled: 0, position: 0 })]),
      4,
      100,
    )!;
    assert.equal(view.rows.length, 4);
    assert.deepEqual(view.tiers, []);
  });

  it('draws a super pack’s three rows, tiers and content prices', () => {
    const view = mysteryBoxPanel(bundle([superPack(19, {
      name: 'New Mistery Box 12',
      cost_cash: 60,
    })]), 19, 100)!;
    assert.equal(view.kind, 'super');
    assert.equal(view.title, SUPER_TITLE);
    assert.equal(view.prompt, SUPER_STORAGE);
    assert.equal(view.banner, SUPER_VALUE);
    assert.equal(view.weekNote, SUPER_ONLY_THIS_WEEK);
    assert.deepEqual(view.rows.map((row) => row.label), [RARITY_RARE, RARITY_UNCOMMON, RARITY_COMMON]);
    // Pack 19's own price override, not the default [60, 100, 200].
    assert.deepEqual(view.tiers.map((tier) => [tier.count, tier.price]), [
      [1, 30],
      [2, 60],
      [4, 100],
    ]);
    assert.deepEqual(view.tiers[2]!.command.args, [19, '[1210,1211,1212,1213]']);
  });

  it('uses the default super prices for every other super pack', () => {
    const view = mysteryBoxPanel(bundle([superPack()]), 44, 100)!;
    assert.deepEqual(view.tiers.map((tier) => tier.price), [60, 100, 200]);
    assert.deepEqual(view.tiers.map((tier) => tier.count), [1, 2, 4]);
  });

  it('does not present a flat or premium pack as a mystery box', () => {
    const flat = { id: 1, name: 'starter pack', type: '', enabled: 1, position: 6, cost_cash: 25, items: [67, 85] };
    const premium = { id: 18, name: 'Premium Account', type: 'premium_account', enabled: 1, position: 2, cost_cash: 0, items: null };
    const content = bundle([flat, premium]);
    assert.equal(mysteryBoxPanel(content, 1, 100), null);
    assert.equal(mysteryBoxPanel(content, 18, 100), null);
    assert.equal(mysteryBoxPanel(content, 999, 100), null);
  });

  it('names the two box popups from the content, preferring an offered super pack', () => {
    const boxes = mysteryBoxes(bundle([
      superPack(6, { enabled: 0, position: 0 }),
      randomPack(),
      superPack(44),
    ]));
    assert.deepEqual(boxes.map((box) => [box.kind, box.packId]), [
      ['mystery', 4],
      ['super', 44],
    ]);
    assert.equal(boxes[0]!.title, MYSTERY_TITLE);
    assert.equal(boxes[1]!.title, SUPER_TITLE);
  });
});

describe('the mystery-box result', () => {
  it('reads only the quantities the server’s answer actually grew', () => {
    const before = { '67': 1, '85': 2 };
    const view = mysteryResultPanel(
      bundle([]),
      world({ '67': 1, '85': 3, '1046': 1 }),
      before,
      purchase(),
    )!;
    assert.ok(view);
    assert.equal(view.kind, 'mystery');
    assert.equal(view.price, 20);
    assert.equal(view.heading, null);
    assert.equal(view.ok, MYSTERY_OK);
    assert.deepEqual(view.items, [
      { itemId: 85, name: 'Uncommon relic', quantity: 1 },
      { itemId: 1046, name: 'Common relic', quantity: 1 },
    ]);
  });

  it('counts a doubled grant from the store delta, not from a client roll', () => {
    const view = mysteryResultPanel(
      bundle([]),
      world({ '67': 3 }),
      { '67': 1 },
      purchase(),
    )!;
    assert.deepEqual(view.items, [{ itemId: 67, name: 'Rare relic', quantity: 2 }]);
  });

  it('uses the super popup’s own congratulations text for a super result', () => {
    const view = mysteryResultPanel(
      bundle([]),
      world({ '1210': 1, '1223': 1 }),
      {},
      purchase({ kind: 'super', packId: 44, title: SUPER_TITLE, price: 200 }),
    )!;
    assert.equal(view.heading, MYSTERY_CONGRATULATIONS);
    assert.equal(view.message, SUPER_STORAGE);
    assert.equal(view.price, 200);
    assert.equal(view.items.length, 2);
  });

  it('draws no result for a refusal, a replay or a shrinking store', () => {
    assert.equal(
      mysteryResultPanel(bundle([]), world({ '67': 1 }), { '67': 1 }, purchase()),
      null,
    );
    assert.equal(mysteryResultPanel(bundle([]), world({}), {}, purchase()), null);
    assert.equal(
      mysteryResultPanel(bundle([]), world({ '67': 0 }), { '67': 1 }, purchase()),
      null,
    );
  });

  it('reads only numeric quantities, ignoring malformed store keys and values', () => {
    const raw = { '67': 2, '85': 'lots', bad: 5 } as unknown as Record<string, number>;
    const worldWithRaw = world();
    (worldWithRaw.maps[0] as { store?: unknown }).store = raw;
    assert.deepEqual(storeQuantities(worldWithRaw), { '67': 2 });
    const view = mysteryResultPanel(bundle([]), worldWithRaw, {}, purchase())!;
    assert.deepEqual(view.items, [{ itemId: 67, name: 'Rare relic', quantity: 2 }]);
  });
});
