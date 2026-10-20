import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  DAMAGE_CLASSES,
  areaDamage,
  bleedingDamage,
  canApplyDamage,
  delayedDamage,
  damageOverTime,
  directKillDamage,
  dizzyDamage,
  incinerateDamage,
  pushInAirDamage,
  sequencedDamage,
  simpleDamage,
  type DamageContext,
  type DamageTarget,
} from './damage.ts';

const context = (numTargets = 1): DamageContext => ({
  attackerId: 'a1',
  numTargets,
});

const unit = (over: Partial<DamageTarget> = {}): DamageTarget => ({
  id: 'u1',
  isUnit: true,
  isDead: false,
  health: 100,
  maxLife: 100,
  x: 0,
  y: 0,
  effects: [],
  ...over,
});

describe('the damage guard', () => {
  it('refuses a null, dead or non-unit target', () => {
    assert.equal(canApplyDamage(null), false);
    assert.equal(canApplyDamage(unit({ isDead: true })), false);
    assert.equal(canApplyDamage(unit({ isUnit: false })), false);
    assert.equal(canApplyDamage(unit()), true);
  });

  it('honours the filter function', () => {
    assert.equal(canApplyDamage(unit(), () => false), false);
    assert.equal(canApplyDamage(unit(), () => true), true);
  });
});

describe('simple damage', () => {
  it('takes health off immediately', () => {
    const r = simpleDamage(unit({ health: 50 }), 30, context());
    assert.equal(r.applied, true);
    assert.equal(r.damage, 30);
    assert.equal(r.health, 20);
    assert.equal(r.dead, false);
  });

  it('kills at zero health', () => {
    const r = simpleDamage(unit({ health: 20 }), 30, context());
    assert.equal(r.health, 0);
    assert.equal(r.dead, true);
  });

  it('shares the damage across the targets', () => {
    const r = simpleDamage(unit(), 30, context(3));
    assert.equal(r.damage, 10);
  });
});

describe('damage over time', () => {
  it('spreads the total over the ticks', () => {
    const r = damageOverTime(unit(), 100, 10, 1000, context());
    assert.equal(r.damage, 0);
    const effect = r.effects.at(-1);
    assert.deepEqual(effect, {
      kind: 'burn',
      damagePerTick: 10,
      ticksRemaining: 10,
      intervalMs: 1000,
    });
  });
});

describe('bleeding damage', () => {
  it('expresses the damage as damage per second', () => {
    // The client: damage / numTargets / (time / 1000) per second.
    const r = bleedingDamage(unit(), 100, 2000, context());
    const effect = r.effects.at(-1);
    assert.deepEqual(effect, { kind: 'bleed', damagePerSecond: 50, secondsRemaining: 2 });
  });
});

describe('incinerate damage', () => {
  it('adds a burn effect', () => {
    const r = incinerateDamage(unit(), 5, 4, 500, context());
    assert.deepEqual(r.effects.at(-1), {
      kind: 'incinerate',
      damagePerTick: 5,
      ticksRemaining: 4,
      intervalMs: 500,
    });
  });
});

describe('dizzy damage', () => {
  it('splits the damage over the ticks and stuns', () => {
    const r = dizzyDamage(unit(), 50, 6000, 5, context());
    assert.deepEqual(r.effects.at(-1), {
      kind: 'dizzy',
      damagePerTick: 10,
      ticksRemaining: 5,
      intervalMs: 1000,
      durationMs: 6000,
    });
  });
});

describe('push in air damage', () => {
  it('damages and pushes', () => {
    const r = pushInAirDamage(unit(), 20, 3, context());
    assert.equal(r.damage, 20);
    assert.deepEqual(r.effects.at(-1), { kind: 'pushed', tiles: 3 });
  });
});

describe('direct kill damage', () => {
  it('kills a target at or below the threshold', () => {
    const r = directKillDamage(unit({ health: 40 }), 50, context());
    assert.equal(r.applied, true);
    assert.equal(r.dead, true);
    assert.deepEqual(r.effects.at(-1), { kind: 'incapacitated' });
  });

  it('does nothing above the threshold', () => {
    const r = directKillDamage(unit({ health: 80 }), 50, context());
    assert.equal(r.applied, false);
    assert.equal(r.damage, 0);
    assert.equal(r.health, 80);
    assert.equal(r.dead, false);
  });
});

describe('delayed damage', () => {
  it('schedules the damage instead of applying it', () => {
    const r = delayedDamage(unit(), 40, 1500, context());
    assert.equal(r.damage, 0);
    assert.deepEqual(r.effects.at(-1), {
      kind: 'delayed',
      delayMs: 1500,
      damage: 40,
      kindInner: 'simple',
    });
  });
});

describe('sequenced damage', () => {
  it('applies every damage in the sequence', () => {
    const r = sequencedDamage(unit(), [10, 20, 30], context());
    assert.equal(r.damage, 60);
    assert.equal(r.health, 40);
  });
});

describe('area damage', () => {
  it('shares the damage across the units it caught', () => {
    const r = areaDamage(unit(), 90, 3, context(3));
    assert.equal(r.damage, 30);
  });

  it('caps the number of units it spreads across', () => {
    // The area caught 3 units but may only hit 2, so the damage is shared
    // across 2, not 3.
    const r = areaDamage(unit(), 90, 2, context(3));
    assert.equal(r.damage, 45);
  });
});

describe('the damage class list', () => {
  it('has the ten classes', () => {
    assert.equal(DAMAGE_CLASSES.length, 10);
    assert.ok(DAMAGE_CLASSES.includes('AreaDamageSpecialAttack'));
    assert.ok(DAMAGE_CLASSES.includes('SequencedDamage'));
  });
});
