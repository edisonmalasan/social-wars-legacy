import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  SPECIAL_ATTACKS,
  SPECIAL_ATTACK_CLASSES,
  minionDeathDamage,
  resolveSpecialAttack,
  vortexAbsorbed,
  type SpecialAttackConfig,
} from './specialattacks.ts';

const config = (over: Partial<SpecialAttackConfig> = {}): SpecialAttackConfig => ({
  attack: 100,
  ...over,
});

describe('the special attack classes', () => {
  it('has the fifteen classes', () => {
    assert.equal(SPECIAL_ATTACK_CLASSES.length, 15);
  });

  it('describes every class', () => {
    for (const name of SPECIAL_ATTACK_CLASSES) {
      const spec = SPECIAL_ATTACKS[name];
      assert.ok(spec, `${name} has no spec`);
      assert.equal(spec.class, name);
    }
  });
});

describe('resolving a special attack', () => {
  it('divides a regular shot by its frames and muzzle points', () => {
    const outcome = resolveSpecialAttack(
      SPECIAL_ATTACKS.RegularShootSpecialAttack,
      config({ frames: 4, points: 2 }),
    );
    assert.equal(outcome.damagePerTarget, 100 / 4 / 2);
    assert.equal(outcome.targets, 2);
    assert.equal(outcome.totalDamage, 25);
  });

  it('divides a melee attack by its frames', () => {
    const outcome = resolveSpecialAttack(
      SPECIAL_ATTACKS.MeleeSpecialAttack,
      config({ frames: 5 }),
    );
    assert.equal(outcome.damagePerTarget, 20);
  });

  it('shares an area attack across the units it caught', () => {
    const outcome = resolveSpecialAttack(
      SPECIAL_ATTACKS.AreaDamageSpecialAttack,
      config({ numUnits: 4 }),
    );
    assert.equal(outcome.damagePerTarget, 25);
    assert.equal(outcome.targets, 4);
    assert.equal(outcome.totalDamage, 100);
  });

  it('moves the attacker without dealing damage of its own', () => {
    const spec = SPECIAL_ATTACKS.GoEnemyAndComeBackSpecialAttack;
    const outcome = resolveSpecialAttack(spec, config({ range: 6 }));
    assert.equal(outcome.damagePerTarget, 0);
    assert.equal(outcome.attackerMovesTiles, 6);
    assert.equal(spec.dealsDamage, false);
    assert.equal(spec.movesAttacker, true);
  });

  it('spawns drones and mines', () => {
    assert.equal(
      resolveSpecialAttack(SPECIAL_ATTACKS.SpawnDroneSpecialAttack, config({ maxMinions: 4 })).spawns,
      4,
    );
    assert.equal(
      resolveSpecialAttack(SPECIAL_ATTACKS.DeployMineSpecialAttack, config({ maxNumMines: 3 })).spawns,
      3,
    );
  });

  it('consumes the target and deals the attacker own max life', () => {
    const outcome = resolveSpecialAttack(
      SPECIAL_ATTACKS.EatSpecialAttack,
      config({ maxLife: 500 }),
    );
    assert.equal(outcome.damagePerTarget, 500);
    assert.equal(outcome.consumesTarget, true);
  });

  it('hits several units with a laser', () => {
    const outcome = resolveSpecialAttack(
      SPECIAL_ATTACKS.MultiLaserSpecialAttack,
      config({ unitsPerShot: 3 }),
    );
    assert.equal(outcome.targets, 3);
    assert.equal(outcome.damagePerTarget, 100);
  });

  it('bleeds 30% of the attack with a vortex', () => {
    const outcome = resolveSpecialAttack(
      SPECIAL_ATTACKS.VortexSpecialAttack,
      config({ numKills: 2 }),
    );
    assert.equal(outcome.damagePerTarget, 30);
  });

  it('divides a whirlwind by its ticks', () => {
    const outcome = resolveSpecialAttack(
      SPECIAL_ATTACKS.WhirlwindSpecialAttack,
      config({ ticks: 4 }),
    );
    assert.equal(outcome.damagePerTarget, 25);
  });
});

describe('the vortex', () => {
  it('deletes only the weakest enemies, and only up to its kill count', () => {
    assert.equal(vortexAbsorbed(50, 100, 3), true);
    assert.equal(vortexAbsorbed(150, 100, 3), false);
    assert.equal(vortexAbsorbed(50, 100, 0), false);
  });
});

describe('the minion death damage', () => {
  it('is a percentage of the minion own life', () => {
    assert.equal(minionDeathDamage(200, 50), 100);
    assert.equal(minionDeathDamage(200, 25), 50);
  });
});
