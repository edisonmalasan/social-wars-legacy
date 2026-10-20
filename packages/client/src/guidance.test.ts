import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  CLICK_HERE_LABEL,
  MARKER_SLOTS,
  activeGoals,
  markedGoals,
  markerSlots,
  type GuidanceGoal,
} from './guidance.ts';

function goal(
  index: number,
  over: Partial<GuidanceGoal> = {},
): GuidanceGoal {
  return { index, visited: false, completed: false, ...over };
}

describe('the active goals', () => {
  const goals = [
    goal(0),
    goal(1, { completed: true }),
    goal(2),
    goal(3, { completed: true }),
    goal(4),
  ];

  it('are the ones that are not completed', () => {
    assert.deepEqual(
      activeGoals(goals).map((entry) => entry.index),
      [0, 2, 4],
    );
  });

  it('are counted from an offset', () => {
    assert.deepEqual(
      activeGoals(goals, 1).map((entry) => entry.index),
      [2, 4],
    );
    assert.deepEqual(
      activeGoals(goals, 2).map((entry) => entry.index),
      [4],
    );
  });

  it('are limited to a count', () => {
    assert.deepEqual(
      activeGoals(goals, 0, 3).map((entry) => entry.index),
      [0, 2, 4],
    );
    assert.deepEqual(
      activeGoals(goals, 0, 2).map((entry) => entry.index),
      [0, 2],
    );
  });

  it('skip a completed goal without taking up a slot', () => {
    // The offset counts the incomplete goals only.
    assert.deepEqual(
      activeGoals(goals, 1, 1).map((entry) => entry.index),
      [2],
    );
  });
});

describe('the click here markers', () => {
  it('are on the goals the player has not visited', () => {
    const slots = markerSlots([goal(0), goal(1, { visited: true }), goal(2)]);
    assert.deepEqual(slots, [true, false, true]);
  });

  it('are off while the tutorial is running', () => {
    const slots = markerSlots([goal(0), goal(1), goal(2)], {
      tutorialMode: true,
    });
    assert.deepEqual(slots, [false, false, false]);
  });

  it('are off once the FIRST one has been clicked', () => {
    // The client's quirk: the check reads `bClicked1` for all three
    // markers, even though it keeps three separate flags.
    const slots = markerSlots([goal(0), goal(1), goal(2)], {
      firstMarkerClicked: true,
    });
    assert.deepEqual(slots, [false, false, false]);
  });

  it('leave the unused slots empty', () => {
    const slots = markerSlots([goal(0)]);
    assert.equal(slots.length, MARKER_SLOTS);
    assert.deepEqual(slots, [true, false, false]);
  });

  it('carry the client own label', () => {
    assert.equal(CLICK_HERE_LABEL, 'CLICK HERE!');
  });
});

describe('the marked goals', () => {
  it('name the slot and the goal', () => {
    const marked = markedGoals([goal(0), goal(1, { visited: true }), goal(2)]);
    assert.deepEqual(marked.map((entry) => entry.slot), [0, 2]);
    assert.deepEqual(marked.map((entry) => entry.goal.index), [0, 2]);
  });

  it('are none while the tutorial is running', () => {
    const marked = markedGoals([goal(0), goal(1)], { tutorialMode: true });
    assert.deepEqual(marked, []);
  });

  it('are the first three active goals', () => {
    const goals = [goal(0), goal(1), goal(2), goal(3), goal(4)];
    const marked = markedGoals(goals);
    assert.equal(marked.length, 3);
    assert.deepEqual(marked.map((entry) => entry.goal.index), [0, 1, 2]);
  });
});
