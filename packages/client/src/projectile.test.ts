import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_DEFINITION,
  distance,
  launchProjectile,
  seededRandom,
  tickProjectile,
  type ProjectileDefinition,
} from './projectile.ts';

/**
 * The projectiles.
 *
 * The model is a port of the client's own, so the tests are about the
 * client's behaviour: the number of steps, the scatter, the arc and
 * the landing.
 */

/** A definition with the client's defaults, changed as the test needs. */
function definition(over: Partial<ProjectileDefinition> = {}): ProjectileDefinition {
  return { ...DEFAULT_DEFINITION, ...over };
}

/** A random source that always gives the same number. */
function fixed(value: number): () => number {
  return () => value;
}

describe('the definition', () => {
  it('has the client\'s defaults', () => {
    assert.equal(DEFAULT_DEFINITION.speed, 10);
    assert.equal(DEFAULT_DEFINITION.curve, 0);
    assert.equal(DEFAULT_DEFINITION.randomOffset, 20);
    assert.equal(DEFAULT_DEFINITION.verticalOffset, 0.5);
    assert.equal(DEFAULT_DEFINITION.easing, null);
    assert.equal(DEFAULT_DEFINITION.blastRadius, 100);
    assert.equal(DEFAULT_DEFINITION.trailsPerStep, 3);
  });
});

describe('a projectile', () => {
  it('takes one step per unit of speed', () => {
    // The distance is 100 and the speed is 10, so there are ten steps.
    const projectile = launchProjectile(
      definition({ randomOffset: 0, speed: 10 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    assert.equal(projectile.steps, 10);
    assert.equal(projectile.delta.x, 10);
    assert.equal(projectile.delta.y, 0);
  });

  it('never takes less than one step', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0 }),
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      fixed(0.5),
    );
    assert.equal(projectile.steps, 1);
  });

  it('scatters the landing point by the random offset', () => {
    // The offset is 20, and the random source gives 1, so the landing
    // point is moved by 1 * 20 - 10 = 10 on **both** axes.
    const projectile = launchProjectile(
      definition({ randomOffset: 20 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(1),
    );
    // The landing point is now at (110, 10), so the flight is longer
    // than it was.
    assert.ok(projectile.steps > 10);
    assert.ok(projectile.steps < 12);
  });

  it('scatters nothing when the random source gives half', () => {
    // Half is the middle, so the offset is 0.5 * 20 - 10 = 0.
    const projectile = launchProjectile(
      definition({ randomOffset: 20 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    assert.equal(projectile.steps, 10);
  });

  it('scatters the start by the start offset', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0, startOffset: 20 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    // The start moved to 0.5 * 20 - 10 = 0, and the target did not
    // move, so the distance is 100.
    assert.equal(projectile.start.x, 0);
    assert.equal(projectile.steps, 10);
  });

  it('begins a little way along the flight', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    // The step BEGINS at 0.5 * 0.94 + 0.05 = 0.52, and the launch
    // ticks once - the client's `init` ends with `tick()` - so the step
    // has already moved on by one.
    assert.ok(projectile.step > 1.5);
    assert.ok(projectile.step < 1.55);
  });

  it('points the way it is going', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0 }),
      { x: 0, y: 0 },
      { x: 0, y: 100 },
      fixed(0.5),
    );
    // Straight down, which is ninety degrees.
    assert.ok(Math.abs(projectile.rotation - 90) < 0.001);
  });

  it('lands on the target', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    for (let i = 0; i < 20 && !projectile.finished; i += 1) {
      tickProjectile(projectile, fixed(0.5));
    }
    assert.ok(projectile.landed);
    assert.ok(projectile.finished);
    assert.ok(Math.abs(projectile.x - 100) < 0.001);
    assert.ok(Math.abs(projectile.y - 0) < 0.001);
  });

  it('flies in a straight line when there is no curve', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0, curve: 0 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    assert.equal(projectile.curve, 0);
    assert.ok(Math.abs(projectile.y) < 0.001);
  });

  it('flies over the top when there is a curve', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0, curve: 1 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    // The arc's height is four steps' worth of the curve.
    assert.equal(projectile.curve, projectile.steps * 4);
    // The first tick is at the start, and the arc lifts it.
    assert.ok(projectile.y < 0);
  });

  it('the grenade flies a different arc', () => {
    const parabolic = launchProjectile(
      definition({ randomOffset: 0, curve: 1 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    const grenade = launchProjectile(
      definition({ randomOffset: 0, curve: 1 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
      'grenade',
    );
    // The same start, and the grenade's arc is the other one.
    assert.notEqual(grenade.y, parabolic.y);
  });

  it('the movie model takes its length from the clip', () => {
    const projectile = launchProjectile(
      definition({ randomOffset: 0 }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
      'movie',
      7,
    );
    assert.equal(projectile.steps, 7);
    assert.equal(projectile.rotation, 0);
  });

  it('uses the easing when there is one', () => {
    const projectile = launchProjectile(
      definition({
        randomOffset: 0,
        easing: (step, start, range) => start + range * (step / 10),
      }),
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      fixed(0.5),
    );
    // The easing's own arithmetic, not the linear one. The position
    // was computed at the step BEFORE the launch's tick, so that is the
    // step the easing saw.
    const used = projectile.step - projectile.stepIncrement;
    const expected = 0 + 100 * (used / 10);
    assert.ok(Math.abs(projectile.x - expected) < 0.0001);
  });
});

describe('the random source', () => {
  it('is the rules engine\'s, so a seed gives the same flight', () => {
    const first = launchProjectile(
      definition(),
      { x: 10, y: 20 },
      { x: 90, y: 80 },
      seededRandom('a-seed'),
    );
    const second = launchProjectile(
      definition(),
      { x: 10, y: 20 },
      { x: 90, y: 80 },
      seededRandom('a-seed'),
    );
    assert.equal(first.x, second.x);
    assert.equal(first.y, second.y);
    assert.equal(first.steps, second.steps);
  });

  it('gives a different flight for a different seed', () => {
    const first = launchProjectile(
      definition(),
      { x: 10, y: 20 },
      { x: 90, y: 80 },
      seededRandom('one'),
    );
    const second = launchProjectile(
      definition(),
      { x: 10, y: 20 },
      { x: 90, y: 80 },
      seededRandom('two'),
    );
    assert.notEqual(first.steps, second.steps);
  });
});

describe('the distance', () => {
  it('is the distance between two points', () => {
    assert.equal(distance({ x: 0, y: 0 }, { x: 3, y: 4 }), 5);
  });
});
