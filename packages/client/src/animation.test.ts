import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  ANIMATION,
  FRAMES_PER_ANIMATION,
  ORIENTATION,
  animationFrame,
  directionFrom,
  idleFrame,
} from './animation.ts';

describe('the animation states', () => {
  it('are the client own', () => {
    // Constants.ANIMATION_*.
    assert.equal(ANIMATION.IDLE, 0);
    assert.equal(ANIMATION.WALKING, 1);
    assert.equal(ANIMATION.ATTACKING, 2);
    assert.equal(ANIMATION.DYING, 3);
    assert.equal(ANIMATION.HARVESTING, 4);
    assert.equal(ANIMATION.REPAIRING, 5);
    assert.equal(ANIMATION.ATTACKING_SPECIAL1, 6);
    assert.equal(ANIMATION.ATTACKING_SPECIAL8, 13);
  });

  it('shares a slot between the repairing, the strike and the oil harvesting', () => {
    // The client uses 5 for all three, and the special attacks start at 6.
    assert.equal(ANIMATION.REPAIRING, 5);
  });
});

describe('the orientations', () => {
  it('are the client own', () => {
    // Constants.ORIENTATION_*.
    assert.equal(ORIENTATION.UP, 1);
    assert.equal(ORIENTATION.UP_RIGHT, 2);
    assert.equal(ORIENTATION.RIGHT, 3);
    assert.equal(ORIENTATION.DOWN_RIGHT, 4);
    assert.equal(ORIENTATION.DOWN, 5);
    assert.equal(ORIENTATION.UP_LEFT, 6);
    assert.equal(ORIENTATION.LEFT, 7);
    assert.equal(ORIENTATION.DOWN_LEFT, 8);
  });
});

describe('the animation frame', () => {
  it('is the state times five plus the direction', () => {
    // IsoUnit.as:1436: frame = iAnimation * 5 + frameDirection.
    assert.equal(animationFrame(ANIMATION.IDLE, ORIENTATION.UP).frame, 1);
    assert.equal(animationFrame(ANIMATION.WALKING, ORIENTATION.RIGHT).frame, 1 * 5 + 3);
    assert.equal(animationFrame(ANIMATION.ATTACKING, ORIENTATION.DOWN).frame, 2 * 5 + 5);
    assert.equal(animationFrame(ANIMATION.DYING, ORIENTATION.UP).frame, 3 * 5 + 1);
  });

  it('uses a block of five frames per state', () => {
    assert.equal(FRAMES_PER_ANIMATION, 5);
    // The states do not overlap.
    const frames = [
      animationFrame(ANIMATION.IDLE, ORIENTATION.DOWN).frame,
      animationFrame(ANIMATION.WALKING, ORIENTATION.DOWN).frame,
    ];
    assert.ok(frames[0]! < frames[1]!);
  });

  it('mirrors the three LEFT-facing directions', () => {
    // IsoUnit.as:1424-1428: a direction over 5 becomes direction - 4 and
    // the sprite is flipped.
    const upLeft = animationFrame(ANIMATION.WALKING, ORIENTATION.UP_LEFT);
    const upRight = animationFrame(ANIMATION.WALKING, ORIENTATION.UP_RIGHT);
    assert.equal(upLeft.frame, upRight.frame);
    assert.equal(upLeft.mirrored, true);
    assert.equal(upRight.mirrored, false);

    assert.equal(animationFrame(0, ORIENTATION.LEFT).frame, animationFrame(0, ORIENTATION.RIGHT).frame);
    assert.equal(animationFrame(0, ORIENTATION.DOWN_LEFT).frame, animationFrame(0, ORIENTATION.DOWN_RIGHT).frame);
  });

  it('does not mirror the right-facing ones', () => {
    for (const orientation of [
      ORIENTATION.UP,
      ORIENTATION.UP_RIGHT,
      ORIENTATION.RIGHT,
      ORIENTATION.DOWN_RIGHT,
      ORIENTATION.DOWN,
    ]) {
      assert.equal(animationFrame(ANIMATION.IDLE, orientation).mirrored, false);
    }
  });

  it('covers every direction with only five slots', () => {
    // Eight directions, five slots: three of them are mirrored.
    const slots = new Set<number>();
    for (const orientation of Object.values(ORIENTATION)) {
      slots.add(animationFrame(ANIMATION.IDLE, orientation).frame);
    }
    assert.equal(slots.size, 5);
  });
});

describe('the idle frame', () => {
  it('is a random frame of the idle sub-clip', () => {
    assert.equal(idleFrame(() => 0, 10), 0);
    assert.equal(idleFrame(() => 0.99, 10), 9);
  });

  it('stays inside the sub-clip', () => {
    for (const value of [0, 0.25, 0.5, 0.75, 0.999]) {
      const frame = idleFrame(() => value, 6);
      assert.ok(frame >= 0 && frame < 6, `frame ${frame} is outside the clip`);
    }
  });

  it('copes with an empty sub-clip', () => {
    assert.equal(idleFrame(() => 0.5, 0), 0);
  });
});

describe('the direction from a movement', () => {
  it('follows the movement on both axes', () => {
    assert.equal(directionFrom(0, 0, 1, 1, ORIENTATION.UP), ORIENTATION.DOWN_RIGHT);
    assert.equal(directionFrom(0, 0, -1, 1, ORIENTATION.UP), ORIENTATION.DOWN_LEFT);
    assert.equal(directionFrom(0, 0, 1, -1, ORIENTATION.UP), ORIENTATION.UP_RIGHT);
    assert.equal(directionFrom(0, 0, -1, -1, ORIENTATION.UP), ORIENTATION.UP_LEFT);
  });

  it('follows one axis when only one moved', () => {
    assert.equal(directionFrom(0, 0, 1, 0, ORIENTATION.UP), ORIENTATION.RIGHT);
    assert.equal(directionFrom(0, 0, 0, 1, ORIENTATION.UP), ORIENTATION.DOWN);
    assert.equal(directionFrom(0, 0, 0, -1, ORIENTATION.UP), ORIENTATION.UP);
  });

  it('keeps the current direction when nothing moved', () => {
    assert.equal(directionFrom(5, 5, 5, 5, ORIENTATION.LEFT), ORIENTATION.LEFT);
  });
});
