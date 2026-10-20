import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  NO_TUTORIAL,
  TUTORIAL_STATE_KEY,
  TUTORIAL_STEPS,
  advanceTutorial,
  finishTutorial,
  isTutorialStep,
  tutorialState,
} from './tutorial.ts';

describe("the tutorial's steps", () => {
  it('are the client own', () => {
    assert.equal(TUTORIAL_STEPS[0], 100);
    assert.ok(TUTORIAL_STEPS.includes(119));
    assert.ok(TUTORIAL_STEPS.includes(136));
    // The client declares 138 and skips 132.
    assert.ok(TUTORIAL_STEPS.includes(138));
    assert.equal(TUTORIAL_STEPS.includes(132), false);
  });

  it('are all numbers', () => {
    for (const step of TUTORIAL_STEPS) {
      assert.equal(typeof step, 'number');
      assert.ok(Number.isInteger(step));
    }
    assert.equal(new Set(TUTORIAL_STEPS).size, TUTORIAL_STEPS.length);
  });

  it('are recognised', () => {
    assert.equal(isTutorialStep(100), true);
    assert.equal(isTutorialStep(138), true);
    assert.equal(isTutorialStep(99), false);
    assert.equal(isTutorialStep(139), false);
  });
});

describe("the tutorial's progression", () => {
  it('starts at nothing', () => {
    assert.deepEqual(NO_TUTORIAL, { step: 0, complete: false });
  });

  it('records the step', () => {
    const result = advanceTutorial(NO_TUTORIAL, 101);
    assert.equal(result.ok, true);
    assert.ok(result.ok && result.state.step === 101);
  });

  it('refuses a step the tutorial does not have', () => {
    const result = advanceTutorial(NO_TUTORIAL, 999);
    assert.equal(result.ok, false);
    assert.equal(!result.ok && result.reason, 'unknown-step');
  });

  it('only ever goes FORWARDS', () => {
    // The client can walk back through the tutorial, and the furthest
    // step is the one that counts.
    const first = advanceTutorial(NO_TUTORIAL, 105);
    assert.ok(first.ok);
    const back = advanceTutorial(first.state, 102);
    assert.ok(back.ok);
    assert.equal(back.ok && back.state.step, 105);
  });

  it('is final once the tutorial is finished', () => {
    const finished = finishTutorial({ step: 138, complete: true });
    const result = advanceTutorial(finished, 100);
    assert.equal(result.ok, true);
    assert.ok(result.ok && result.state.complete);
    assert.ok(result.ok && result.state.step === 138);
  });
});

describe("the tutorial's state", () => {
  it('is read out of the private state', () => {
    const privateState = { [TUTORIAL_STATE_KEY]: { step: 110, complete: false } };
    assert.deepEqual(tutorialState(privateState), { step: 110, complete: false });
  });

  it('is nothing when the private state has nothing', () => {
    assert.deepEqual(tutorialState({}), NO_TUTORIAL);
    assert.deepEqual(tutorialState({ [TUTORIAL_STATE_KEY]: null }), NO_TUTORIAL);
    assert.deepEqual(tutorialState({ [TUTORIAL_STATE_KEY]: 'nonsense' }), NO_TUTORIAL);
  });

  it('is nothing when the state is nonsense', () => {
    assert.deepEqual(
      tutorialState({ [TUTORIAL_STATE_KEY]: { step: 'lots' } }),
      NO_TUTORIAL,
    );
    assert.deepEqual(
      tutorialState({ [TUTORIAL_STATE_KEY]: { step: -5 } }),
      NO_TUTORIAL,
    );
  });
});
