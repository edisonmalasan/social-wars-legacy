import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { buildContent } from './build.ts';

describe('the content bundle', () => {
  it('has no validation problems', async () => {
    const { problems } = await buildContent();
    assert.deepEqual(problems, []);
  });

  it('reproduces the upstream server post-patch counts', async () => {
    const { bundle } = await buildContent();
    assert.equal(bundle.items.length, 900);
    assert.equal(bundle.levels.length, 100);
    assert.equal(bundle.goals.length, 91);
    assert.equal(Object.keys(bundle.globals).length, 105);
    assert.equal(bundle.dartsItems.length, 27);
    assert.equal(Object.keys(bundle.propertyKeys).length, 41);
    assert.equal(Object.keys(bundle.subcatFunctionals).length, 24);
  });

  it('gives every item its build cost', async () => {
    // The config stores the whole item table as STRINGS, and `costs` is JSON
    // text inside a string. A parser that casts instead of parsing would
    // silently produce an empty cost for every item in the game.
    const { bundle } = await buildContent();
    const withCosts = bundle.items.filter((i) => Object.keys(i.costs).length > 0);
    assert.equal(withCosts.length, bundle.items.length);
  });

  it('resolves the upgrade chains', async () => {
    const { bundle } = await buildContent();
    const byId = new Map(bundle.items.map((i) => [i.id, i]));
    const upgraders = bundle.items.filter((i) => i.upgrades_to !== null);
    assert.ok(upgraders.length > 0);
    for (const item of upgraders) {
      const next = byId.get(item.upgrades_to!);
      assert.ok(next, `item ${item.id} upgrades to a missing item ${item.upgrades_to}`);
      // An upgrade is always a different, higher-tier item.
      assert.notEqual(next!.id, item.id);
    }
  });

  it('resolves the trained units', async () => {
    const { bundle } = await buildContent();
    const byId = new Set(bundle.items.map((i) => i.id));
    const trainers = bundle.items.filter((i) => i.trains_ids.length > 0);
    assert.ok(trainers.length > 0);
    for (const item of trainers) {
      for (const trained of item.trains_ids) {
        assert.ok(byId.has(trained), `item ${item.id} trains a missing unit ${trained}`);
      }
    }
  });

  it('keeps the fighting-type flags in the properties', async () => {
    const { bundle } = await buildContent();
    const soldier = bundle.items.find((i) => i.id === 1007);
    assert.ok(soldier);
    assert.equal(soldier!.properties['ft_ground'], 1);
    assert.equal(soldier!.best_against, 'ft_ground');
  });

  it('keeps the four real counters', async () => {
    const { bundle } = await buildContent();
    const counters = bundle.items
      .filter((i) => i.best_against_mult > 1 && i.best_against !== '-1')
      .map((i) => `${i.name} ${i.best_against_mult}x ${i.best_against}`)
      .sort();
    assert.deepEqual(counters, [
      'Antiaircraft battery 20x ft_flying',
      'B52 5x ft_building',
      'Demolition Tank 15x ft_building',
      'Mortar Thrower 10x ft_building',
    ]);
  });

  it('gives every building a footprint and a level', async () => {
    const { bundle } = await buildContent();
    for (const item of bundle.items) {
      assert.ok(item.width >= 1, `item ${item.id} has no width`);
      assert.ok(item.height >= 1, `item ${item.id} has no height`);
      assert.ok(item.min_level >= 0, `item ${item.id} has no min_level`);
    }
  });

  it('produces a stable build id', async () => {
    const first = await buildContent();
    const second = await buildContent();
    assert.equal(second.bundle.buildId, first.bundle.buildId);
    assert.match(first.bundle.buildId, /^[0-9a-f]{64}$/);
  });
});
