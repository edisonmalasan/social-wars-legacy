import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  ATTACK_PHASE_COUNT,
  FRAMES_PER_SECOND,
  attackFrames,
  attackPhase,
  buildingAttackDamage,
  buildingFiresOnFrame,
  countAttackFrames,
  shooterCount,
  unitFiresOnFrame,
  type Combatant,
} from './battle.ts';

const unit = (over: Partial<Combatant> = {}): Combatant => ({
  id: 'u1',
  kind: 'unit',
  itemId: 1007,
  attack: 8,
  defense: 1,
  life: 50,
  attackRange: 5,
  attackInterval: 35,
  phase: 0,
  properties: {},
  bestAgainst: null,
  bestAgainstMult: 1,
  ...over,
});

describe('the attack cadence', () => {
  it('runs at 30 frames per second', () => {
    assert.equal(FRAMES_PER_SECOND, 30);
  });

  it('gives a unit one of five phases', () => {
    assert.equal(ATTACK_PHASE_COUNT, 5);
    // IsoFightingElement.as:171 - Math.floor(Math.random() * 5)
    assert.equal(attackPhase(0), 0);
    assert.equal(attackPhase(0.1999), 0);
    assert.equal(attackPhase(0.2), 1);
    assert.equal(attackPhase(0.9999), 4);
  });

  it('fires a unit on (frame + phase) % interval', () => {
    assert.equal(unitFiresOnFrame(0, 0, 35), true);
    assert.equal(unitFiresOnFrame(35, 0, 35), true);
    assert.equal(unitFiresOnFrame(1, 0, 35), false);
    // With a phase, the unit fires on a different frame.
    assert.equal(unitFiresOnFrame(0, 3, 35), false);
    assert.equal(unitFiresOnFrame(32, 3, 35), true);
  });

  it('fires a building in global lockstep, with no phase', () => {
    assert.equal(buildingFiresOnFrame(0, 35), true);
    assert.equal(buildingFiresOnFrame(35, 35), true);
    assert.equal(buildingFiresOnFrame(1, 35), false);
  });

  it('never fires with a zero interval', () => {
    assert.equal(unitFiresOnFrame(0, 0, 0), false);
    assert.equal(buildingFiresOnFrame(0, 0), false);
  });

  it('desynchronises a group of units', () => {
    // Five units, one per phase, must not all fire on the same frame.
    const phases = [0, 1, 2, 3, 4];
    for (let frame = 0; frame < 35; frame++) {
      const firing = phases.filter((p) => unitFiresOnFrame(frame, p, 35)).length;
      assert.ok(firing <= 1, `frame ${frame} had ${firing} units firing`);
    }
  });

  it('yields the attack frames', () => {
    const frames = [...attackFrames(unit({ attackInterval: 10 }), 35)];
    assert.deepEqual(frames, [0, 10, 20, 30]);
    assert.equal(countAttackFrames(unit({ attackInterval: 10 }), 35), 4);
  });
});

describe('the shooters', () => {
  it('lets an ordinary building fire from every attack point', () => {
    const building = { attackPoints: 4, garrison: 0, isBunker: false };
    assert.equal(shooterCount(building), 4);
  });

  it('limits a bunker to its garrison', () => {
    const bunker = { attackPoints: 4, garrison: 3, isBunker: true };
    assert.equal(shooterCount(bunker), 3);
  });

  it('makes an empty bunker fire not at all', () => {
    const bunker = { attackPoints: 4, garrison: 0, isBunker: true };
    assert.equal(shooterCount(bunker), 0);
    assert.equal(buildingAttackDamage(bunker, 8), 0);
  });

  it('deals the building own attack per shot, not a garrison-scaled value', () => {
    // Bunker I: attack 8, unit_capacity 1. A bunker with three soldiers
    // fires three shots of 8, so 24 in a cycle - not 8 * 3/1.
    const bunker = { attackPoints: 4, garrison: 3, isBunker: true };
    assert.equal(buildingAttackDamage(bunker, 8), 24);
  });

  it('never fires more shots than it has attack points', () => {
    const bunker = { attackPoints: 2, garrison: 10, isBunker: true };
    assert.equal(shooterCount(bunker), 2);
  });
});
