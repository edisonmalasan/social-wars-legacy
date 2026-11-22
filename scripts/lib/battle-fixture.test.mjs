import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import {
  createBattleFixture,
  simulateFixture,
  DEFAULT_ARMY_SIZE,
  DEFAULT_SEED,
} from './battle-fixture.mjs';

/**
 * The real, committed content bundle — not a hand-written imitation. A fixture
 * built from it is therefore built from the repository's content, and any
 * change to the game's units changes the fixture too.
 */
const BUNDLE = path.join(process.cwd(), 'apps/client/public/content-bundle.json');
const content = JSON.parse(readFileSync(BUNDLE, 'utf8')).items;

describe('the large-battle fixture', () => {
  it('is deterministic for the same seed and content', () => {
    const a = createBattleFixture({ seed: 'repeatable', content, armySize: 12 });
    const b = createBattleFixture({ seed: 'repeatable', content, armySize: 12 });
    assert.deepEqual(b, a);
    assert.equal(a.fingerprint, b.fingerprint);
  });

  it('changes with the seed', () => {
    const a = createBattleFixture({ seed: 'one', content, armySize: 12 });
    const b = createBattleFixture({ seed: 'two', content, armySize: 12 });
    assert.notEqual(a.fingerprint, b.fingerprint);
    assert.notDeepEqual(b.battle.attackers, a.battle.attackers);
  });

  it('uses the default seed and builds a genuinely large battle', () => {
    const fixture = createBattleFixture({ content });
    assert.equal(fixture.seed, DEFAULT_SEED);
    assert.equal(fixture.armySize, DEFAULT_ARMY_SIZE);
    assert.ok(DEFAULT_ARMY_SIZE >= 100, 'the default must be a large battle');
    assert.equal(fixture.attackerCount, DEFAULT_ARMY_SIZE);
    assert.equal(fixture.defenderCount, DEFAULT_ARMY_SIZE);
    assert.equal(fixture.combatantCount, DEFAULT_ARMY_SIZE * 2);
  });

  it('takes every combatant stat from the real content', () => {
    const fixture = createBattleFixture({ content, armySize: 6 });
    const byId = new Map(content.map((item) => [item.id, item]));
    const elements = [...fixture.battle.attackers, ...fixture.battle.defenders];
    for (const element of elements) {
      const item = byId.get(element.itemId);
      assert.ok(item, `item ${element.itemId} is in the content`);
      assert.equal(item.type, 'u');
      assert.equal(element.attack, item.attack);
      assert.equal(element.defense, item.defense);
      assert.equal(element.life, item.life);
      assert.equal(element.attack_range, item.attack_range);
      assert.equal(element.attack_interval, item.attack_interval);
      assert.equal(element.subcatFunctional, item.subcat_functional);
      assert.deepEqual(element.properties, item.properties);
      assert.equal(element.best_against, item.best_against);
      assert.equal(element.best_against_mult, item.best_against_mult);
    }
  });

  it('builds valid simulation elements with seeded phases', () => {
    const fixture = createBattleFixture({ seed: 'phases', content, armySize: 20 });
    const elements = [...fixture.battle.attackers, ...fixture.battle.defenders];
    for (const element of elements) {
      assert.equal(element.kind, 'unit');
      assert.ok(Number.isInteger(element.phase) && element.phase >= 0 && element.phase <= 4);
      assert.equal(element.health, element.life);
      assert.equal(element.maxLife, element.life);
      for (const key of ['attack', 'defense', 'life', 'attack_range', 'attack_interval', 'tx', 'ty']) {
        assert.ok(Number.isFinite(element[key]), `${key} is finite`);
      }
      assert.ok(element.tx >= 0 && element.ty >= 0, 'positions are on the map');
    }
    assert.equal(new Set(elements.map((e) => e.id)).size, elements.length);
  });

  it('does not mutate the content it was given', () => {
    const before = JSON.stringify(content);
    createBattleFixture({ seed: 'pure', content, armySize: 10 });
    assert.equal(JSON.stringify(content), before);
  });

  it('produces a client-shaped world with one entry per combatant', () => {
    const fixture = createBattleFixture({ content, armySize: 8 });
    assert.equal(fixture.world.maps.length, 1);
    const items = fixture.world.maps[0].items;
    assert.equal(Object.keys(items).length, 16);
    for (const tuple of Object.values(items)) {
      assert.equal(tuple.length, 5);
      assert.ok(tuple.every((value) => Number.isFinite(value)));
      assert.ok(content.some((item) => item.id === tuple[0] && item.type === 'u'));
    }
    assert.ok(fixture.world.resources, 'the world has a wallet');
  });

  it('simulates deterministically through the rules engine', () => {
    const a = createBattleFixture({ seed: 'fight', content, armySize: 6 });
    const b = createBattleFixture({ seed: 'fight', content, armySize: 6 });
    const first = simulateFixture(a);
    const second = simulateFixture(b);
    assert.deepEqual(second, first);
    assert.ok(['attackers', 'defenders', 'draw'].includes(first.winner));
    assert.ok(first.events.length > 0, 'the adjacent front lines exchange shots');
    assert.equal(a.fingerprint, b.fingerprint);
  });

  it('leaves the fixture unchanged after a simulation', () => {
    const fixture = createBattleFixture({ seed: 'unchanged', content, armySize: 6 });
    const before = JSON.stringify(fixture);
    simulateFixture(fixture);
    assert.equal(JSON.stringify(fixture), before);
  });

  it('rejects content with no usable units', () => {
    assert.throws(() => createBattleFixture({ content: [] }), /no usable units/);
    assert.throws(
      () => createBattleFixture({ content: [{ id: 1, type: 'b', life: 10 }] }),
      /no usable units/,
    );
  });

  it('rejects an invalid army size', () => {
    for (const armySize of [0, -1, 1.5, 'many']) {
      assert.throws(() => createBattleFixture({ content, armySize }), /armySize/);
    }
  });
});
