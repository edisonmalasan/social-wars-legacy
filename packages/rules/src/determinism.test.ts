import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Random, hashSeed } from './random.ts';
import { resolveDamage } from './combat.ts';
import { simulateBattle, type SimElement } from './simulate.ts';

/**
 * The reference vectors.
 *
 * The generator is a xoshiro128** whose every operation is a **32-bit
 * integer** operation — `>>> 0` and `Math.imul` — and those are defined
 * exactly by the language, not approximately by the platform. So the same
 * seed gives the same sequence **on any machine**, and these vectors are
 * what pins that.
 *
 * If one of these changes, the generator changed, and every battle that
 * was ever re-simulated changes with it. That is why they are here rather
 * than a round-trip check.
 */
const VECTORS: { seed: string | number; values: number[] }[] = [
  {
    seed: 'battle-1',
    values: [
      0.032406951999, 0.515984114492, 0.922267566901,
      0.536239486653, 0.157637045253, 0.508655170212,
    ],
  },
  {
    seed: 'golden',
    values: [
      0.781900495756, 0.691770192236, 0.963170068106,
      0.037099028472, 0.294863156043, 0.045409314102,
    ],
  },
  {
    seed: 12345,
    values: [
      0.254547816468, 0.047265402274, 0.871101760538,
      0.885623776820, 0.972938411869, 0.188650433673,
    ],
  },
];

describe('the generator is reproducible', () => {
  it('gives the reference sequence for a text seed', () => {
    for (const { seed, values } of VECTORS) {
      const random = new Random(seed);
      const actual = values.map(() => random.next());
      for (let index = 0; index < values.length; index++) {
        assert.ok(
          Math.abs(actual[index]! - values[index]!) < 1e-12,
          `${JSON.stringify(seed)} value ${index} is ${actual[index]}, not ${values[index]}`,
        );
      }
    }
  });

  it('gives the reference sequence for a number seed', () => {
    const random = new Random(7);
    assert.deepEqual(
      Array.from({ length: 6 }, () => random.int(0, 100)),
      [4, 16, 93, 96, 40, 64],
    );
  });

  it('gives the reference sequence for chance', () => {
    const random = new Random(7);
    assert.deepEqual(
      Array.from({ length: 6 }, () => random.chance(0.5)),
      [true, true, false, false, true, false],
    );
  });

  it('gives the reference sequence for float', () => {
    const random = new Random(7);
    const values = Array.from({ length: 6 }, () => random.float(1, 2));
    const expected = [
      1.049009593902, 1.165562353097, 1.929853208363,
      1.952130623627, 1.397236564895, 1.639358178247,
    ];
    for (let index = 0; index < expected.length; index++) {
      assert.ok(Math.abs(values[index]! - expected[index]!) < 1e-12);
    }
  });

  it('hashes a text seed to the reference value', () => {
    assert.equal(hashSeed('battle-1'), 1855738637);
    assert.equal(hashSeed('golden'), 386248004);
  });

  it('gives the same sequence from the same seed, every time', () => {
    const first = new Random('battle-1');
    const second = new Random('battle-1');
    for (let index = 0; index < 32; index++) {
      assert.equal(first.next(), second.next());
    }
  });
});

describe('the damage pipeline is reproducible', () => {
  const attacker = {
    attack: 40,
    defense: 1,
    life: 50,
    attack_range: 5,
    attack_interval: 35,
    best_against: 'ft_ground',
    best_against_mult: 1,
    properties: { ft_ground: 1 },
  };
  const defender = {
    attack: 0,
    defense: 1,
    life: 50,
    attack_range: 5,
    attack_interval: 35,
    best_against: 'ft_ground',
    best_against_mult: 1,
    properties: { ft_ground: 1 },
  };

  it('gives the same damage for the same seed', () => {
    const first = resolveDamage(attacker, defender, new Random('battle-1'), {}, { variance: 0 });
    const second = resolveDamage(attacker, defender, new Random('battle-1'), {}, { variance: 0 });
    assert.equal(first.damage, second.damage);
    assert.equal(first.crit, second.crit);
    assert.deepEqual(first.stages, second.stages);
  });

  it('gives the same damage on a second run of the whole thing', () => {
    const run = (): number =>
      resolveDamage(attacker, defender, new Random('battle-1'), {}, { variance: 0 }).damage;
    assert.equal(run(), run());
  });
});

describe('the battle simulation is reproducible', () => {
  function unit(id: string, over: Partial<SimElement> = {}): SimElement {
    return {
      id,
      itemId: 1007,
      attack: 20,
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

  it('gives the same battle for the same seed', () => {
    const input = {
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0 })],
      defenders: [unit('d1', { tx: 3, ty: 0 })],
    };
    const first = simulateBattle(input);
    const second = simulateBattle(input);
    assert.deepEqual(first, second);
  });

  it('gives the same battle when the input is rebuilt', () => {
    const build = () => ({
      seed: 'battle-1',
      attackers: [unit('a1', { tx: 0, ty: 0 })],
      defenders: [unit('d1', { tx: 3, ty: 0 })],
    });
    assert.deepEqual(simulateBattle(build()), simulateBattle(build()));
  });

  it('does not modify the armies it was given', () => {
    const attackers = [unit('a1')];
    const defenders = [unit('d1', { tx: 3 })];
    simulateBattle({ seed: 'battle-1', attackers, defenders });
    assert.equal(attackers[0]!.health, 50);
    assert.equal(defenders[0]!.health, 50);
  });
});
