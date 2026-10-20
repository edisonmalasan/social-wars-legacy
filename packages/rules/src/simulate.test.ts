import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_MAX_FRAMES,
  distanceBetween,
  firesOnFrame,
  shotsOf,
  simulateBattle,
  type SimElement,
} from './simulate.ts';

/** A unit, with the defaults the tests want. */
function unit(id: string, over: Partial<SimElement> = {}): SimElement {
  return {
    id,
    itemId: 1007,
    attack: 8,
    defense: 1,
    life: 50,
    health: 50,
    maxLife: 50,
    attack_range: 5,
    attack_interval: 35,
    best_against: 'ft_ground',
    best_against_mult: 1,
    properties: { ft_ground: 1 },
    tx: 0,
    ty: 0,
    width: 1,
    height: 1,
    phase: 0,
    subcatFunctional: 0,
    kind: 'unit',
    ...over,
  };
}

/** A building. */
function building(id: string, over: Partial<SimElement> = {}): SimElement {
  return {
    id,
    itemId: 1,
    attack: 0,
    defense: 0,
    life: 100,
    health: 100,
    maxLife: 100,
    attack_range: 6,
    attack_interval: 35,
    best_against: null,
    best_against_mult: 1,
    properties: {},
    tx: 0,
    ty: 0,
    width: 1,
    height: 1,
    phase: 0,
    subcatFunctional: 111,
    kind: 'building',
    attackPoints: 0,
    ...over,
  };
}

describe('the distance', () => {
  it('is the euclidean distance between the centres', () => {
    const a = unit('a', { tx: 0, ty: 0 });
    const b = unit('b', { tx: 3, ty: 4 });
    assert.equal(distanceBetween(a, b), 5);
  });

  it('is truncated to an integer', () => {
    const a = unit('a', { tx: 0, ty: 0 });
    const b = unit('b', { tx: 1, ty: 1 });
    // sqrt(2) is 1.414, so the distance is 1.
    assert.equal(distanceBetween(a, b), 1);
  });

  it('offsets the centre by half the footprint', () => {
    // A 3-wide building's centre is one tile left of its anchor.
    const wide = building('w', { tx: 10, ty: 10, width: 3, height: 3 });
    const point = unit('p', { tx: 10, ty: 10 });
    assert.equal(distanceBetween(wide, point), 1);
  });

  it('is zero for an element against itself', () => {
    const a = unit('a');
    assert.equal(distanceBetween(a, a), 0);
  });
});

describe('the firing cadence', () => {
  it('fires a unit on its phase', () => {
    const u = unit('u', { phase: 0, attack_interval: 35 });
    assert.equal(firesOnFrame(u, 0), true);
    assert.equal(firesOnFrame(u, 35), true);
    assert.equal(firesOnFrame(u, 1), false);
  });

  it('fires a building in lockstep', () => {
    const b = building('b', { attack_interval: 35 });
    assert.equal(firesOnFrame(b, 0), true);
    assert.equal(firesOnFrame(b, 35), true);
    assert.equal(firesOnFrame(b, 1), false);
  });

  it('counts a building shots', () => {
    assert.equal(shotsOf(unit('u')), 1);
    assert.equal(shotsOf(building('b', { attackPoints: 4 })), 4);
  });
});

describe('the battle simulation', () => {
  it('is deterministic for the same seed and the same armies', () => {
    const input = {
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0 })],
      defenders: [unit('d1', { tx: 3, ty: 0 })],
    };
    const first = simulateBattle(input);
    const second = simulateBattle(input);
    assert.deepEqual(first, second);
  });

  it('gives a different result for a different seed', () => {
    const attackers = [unit('a1', { tx: 0, ty: 0 })];
    const defenders = [unit('d1', { tx: 3, ty: 0 })];
    const first = simulateBattle({ seed: 'battle-1', attackers, defenders });
    const second = simulateBattle({ seed: 'battle-2', attackers, defenders });
    // The seeds are recorded and the streams differ; the rolls may coincide.
    assert.notEqual(
      JSON.stringify(first.events),
      JSON.stringify(second.events),
      'two different seeds produced an identical fight',
    );
  });

  it('does not modify the armies it was given', () => {
    const attackers = [unit('a1', { tx: 0, ty: 0 })];
    const defenders = [unit('d1', { tx: 3, ty: 0 })];
    simulateBattle({ seed: 'battle-1', attackers, defenders });
    assert.equal(attackers[0]!.health, 50);
    assert.equal(defenders[0]!.health, 50);
  });

  it('kills the weaker side', () => {
    const outcome = simulateBattle({
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0, attack: 100 })],
      defenders: [unit('d1', { tx: 2, ty: 0, life: 20, health: 20, maxLife: 20 })],
    });
    assert.equal(outcome.winner, 'attackers');
    assert.deepEqual(outcome.defenderLosses, ['d1']);
    assert.equal(outcome.attackerLosses.length, 0);
  });

  it('records every shot', () => {
    const outcome = simulateBattle({
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0 })],
      defenders: [unit('d1', { tx: 2, ty: 0 })],
    });
    assert.ok(outcome.events.length > 0, 'no shots were fired');
    for (const event of outcome.events) {
      // Both sides shoot, so a shot is by one and at the other.
      assert.ok(
        (event.attacker === 'a1' && event.target === 'd1') ||
          (event.attacker === 'd1' && event.target === 'a1'),
        `unexpected shot: ${JSON.stringify(event)}`,
      );
      assert.ok(event.damage >= 0);
    }
    // The frames are non-decreasing.
    for (let i = 1; i < outcome.events.length; i++) {
      assert.ok(outcome.events[i]!.frame >= outcome.events[i - 1]!.frame);
    }
  });

  it('never shoots at something out of range', () => {
    const outcome = simulateBattle({
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0, attack_range: 2 })],
      defenders: [unit('d1', { tx: 40, ty: 0, attack_range: 2 })],
    });
    assert.equal(outcome.events.length, 0);
    assert.equal(outcome.winner, 'draw');
  });

  it('stops when the frames run out', () => {
    const outcome = simulateBattle({
      seed: 'battle-1',
      maxFrames: 10,
      attackers: [unit('a1', { tx: 0, ty: 0 })],
      defenders: [unit('d1', { tx: 2, ty: 0 })],
    });
    assert.ok(outcome.frames <= 10);
  });

  it('has a default frame limit', () => {
    assert.equal(DEFAULT_MAX_FRAMES, 300);
  });

  it('a draw when neither side can reach the other', () => {
    const outcome = simulateBattle({
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0 })],
      defenders: [unit('d1', { tx: 60, ty: 0 })],
    });
    assert.equal(outcome.winner, 'draw');
    assert.equal(outcome.attackerDamage, 0);
    assert.equal(outcome.defenderDamage, 0);
  });

  it('prefers a unit over a building', () => {
    // The client scores a unit 150 higher than a building, so a unit is
    // shot even when the building is nearer.
    const outcome = simulateBattle({
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0, attack_range: 20 })],
      defenders: [
        building('b1', { tx: 1, ty: 0 }),
        unit('d1', { tx: 10, ty: 0, life: 500, health: 500, maxLife: 500 }),
      ],
    });
    assert.ok(outcome.events.length > 0);
    assert.equal(outcome.events[0]!.target, 'd1');
  });

  it('lets a defensive building shoot back', () => {
    const outcome = simulateBattle({
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0 })],
      defenders: [building('b1', { tx: 3, ty: 0, attack: 50, attackPoints: 1 })],
    });
    assert.ok(outcome.defenderDamage > 0, 'the building never fired');
    assert.ok(outcome.attackerLosses.includes('a1'));
  });
});
