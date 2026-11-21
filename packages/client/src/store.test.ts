import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { storePacks } from './store.ts';

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

describe('storePacks', () => {
  it('lists available packs with the content price and the player cash', () => {
    const views = storePacks([pack(), pack({ id: 2, enabled: 0, position: 5 })], 30);
    assert.equal(views.length, 1);
    assert.equal(views[0]!.id, 1);
    assert.equal(views[0]!.price, 25);
    assert.equal(views[0]!.affordable, true);
    assert.equal(views[0]!.command?.name, 'buy_offer_pack');
    assert.deepEqual(views[0]!.command?.args, [1, '[1042,84]']);
  });

  it('keeps an unaffordable pack visible but not buyable', () => {
    const views = storePacks([pack()], 10);
    assert.equal(views[0]!.affordable, false);
    assert.ok(views[0]!.command);
  });

  it('never offers the premium pack, which opens a real-money flow', () => {
    assert.deepEqual(storePacks([pack({ type: 'premium_account' })], 10_000), []);
  });

  it('prices a super pack by the selected-item tier with the pack override', () => {
    const views = storePacks(
      [pack({ id: 19, type: 'super', items: [[1042], [1004, 1005], [1060, 1061, 1062, 1063]] })],
      100,
    );
    assert.equal(views[0]!.shape, 'super');
    assert.deepEqual(
      views[0]!.tiers.map((tier) => [tier.count, tier.price, tier.affordable]),
      [
        [1, 30, true],
        [2, 60, true],
        [4, 100, true],
      ],
    );
    assert.deepEqual(views[0]!.tiers[1]!.command.args[1], '[1042,1004]');
  });

  it('omits super tiers when the selection cannot be built', () => {
    const views = storePacks([pack({ id: 19, type: 'super', items: [[1042]] })], 100);
    assert.deepEqual(views[0]!.tiers, []);
  });

  it('ignores malformed rows without inventing a pack', () => {
    const views = storePacks(
      [null, 42, {}, pack({ id: 'x' }), pack({ cost_cash: Number.NaN }), pack()],
      30,
    );
    assert.equal(views.length, 1);
    assert.equal(views[0]!.id, 1);
  });

  it('accepts an empty list', () => {
    assert.deepEqual(storePacks([], 0), []);
  });
});
