import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  AREA_51_RESEARCH_ITEMS,
  RESEARCH_BUILDING_AREA_51,
  RESEARCH_BUILDING_ROBOTIC,
  RESEARCH_CASH_BIG,
  RESEARCH_CASH_SMALL,
  RESEARCH_FRIENDS_MULTIPLIER,
  RESEARCH_ITEM_COUNT,
  RESEARCH_STEP_SECONDS,
  RESEARCH_TOTAL_STEPS,
  RESEARCH_TYPE_AREA_51,
  RESEARCH_TYPE_ROBOTIC,
  ROBOTIC_RESEARCH_ITEMS,
  finishRoboticHelp,
  initialResearchState,
  nextResearchItem,
  nextResearchStep,
  researchBuyStepCash,
  researchCashCost,
  researchItemAt,
  researchItemsFor,
  researchTypeForBuilding,
  resetResearchItem,
} from './research.ts';

describe('the research tracks', () => {
  it('uses the client constants and building ids', () => {
    assert.equal(RESEARCH_TOTAL_STEPS, 10);
    assert.equal(RESEARCH_STEP_SECONDS, 6 * 3600);
    assert.equal(RESEARCH_FRIENDS_MULTIPLIER, 2);
    assert.equal(RESEARCH_ITEM_COUNT, 6);
    assert.equal(RESEARCH_TYPE_AREA_51, 0);
    assert.equal(RESEARCH_TYPE_ROBOTIC, 1);
    assert.equal(researchTypeForBuilding(RESEARCH_BUILDING_AREA_51), 0);
    assert.equal(researchTypeForBuilding(RESEARCH_BUILDING_ROBOTIC), 1);
    assert.equal(researchTypeForBuilding(999), null);
  });

  it('lists the six items and their cash prices in client order', () => {
    assert.deepEqual(
      ROBOTIC_RESEARCH_ITEMS.map((item) => [item.id, item.cash]),
      [[1062, 15], [1101, 3], [1075, 3], [1141, 3], [1085, 3], [1105, 3]],
    );
    assert.deepEqual(
      AREA_51_RESEARCH_ITEMS.map((item) => [item.id, item.cash]),
      [[1048, 3], [1096, 15], [1097, 3], [1099, 15], [1098, 3], [1100, 15]],
    );
    assert.equal(RESEARCH_CASH_SMALL, 3);
    assert.equal(RESEARCH_CASH_BIG, 15);
    assert.equal(researchItemsFor(1), ROBOTIC_RESEARCH_ITEMS);
    assert.equal(researchItemsFor(0), AREA_51_RESEARCH_ITEMS);
  });

  it('wraps an item slot at six', () => {
    assert.equal(researchItemAt(1, 0).id, 1062);
    assert.equal(researchItemAt(1, 5).id, 1105);
    assert.equal(researchItemAt(1, 6).id, 1062);
    assert.equal(researchItemAt(1, 11).id, 1105);
    assert.equal(researchItemAt(0, 6).id, 1048);
    assert.equal(researchCashCost(1, 0), 15);
    assert.equal(researchCashCost(1, 1), 3);
    assert.equal(researchCashCost(0, 1), 15);
    assert.equal(researchCashCost(0, 6), 3);
  });
});

describe('research steps', () => {
  it('increments the step and restarts the timestamp only when asked', () => {
    const start = initialResearchState();
    const clientStep = nextResearchStep(start, 1, true, 1000);
    assert.deepEqual(clientStep, {
      itemNumber: [0, 0],
      stepNumber: [0, 1],
      timestamp: [0, 1000],
      roboticSocialHelp: [],
    });
    // Friend help calls goNextStep(false): progress, but no new timer.
    const helped = nextResearchStep(clientStep, 1, false, 9999);
    assert.deepEqual(helped.stepNumber, [0, 2]);
    assert.deepEqual(helped.timestamp, [0, 1000]);
    // The input was not modified.
    assert.deepEqual(clientStep.stepNumber, [0, 1]);
  });

  it('buys a step by clearing the timer, without incrementing progress', () => {
    const state = initialResearchState();
    state.itemNumber[0] = 1;
    state.stepNumber[0] = 4;
    state.timestamp[0] = 777;
    const result = researchBuyStepCash(state, 0);
    assert.deepEqual(result.state.stepNumber, [4, 0]);
    assert.deepEqual(result.state.timestamp, [0, 0]);
    assert.equal(result.cashCost, 15);
    assert.equal(state.timestamp[0], 777);
    assert.equal(researchBuyStepCash(state, 1).cashCost, 15);
  });
});

describe('research items', () => {
  it('grants on the tenth step and rolls the item number over modulo six', () => {
    const cases: [number, number, number][] = [
      [0, 1, 1062],
      [4, 5, 1085],
      [5, 0, 1105],
    ];
    for (const [itemNumber, expectedNext, expectedId] of cases) {
      const state = initialResearchState();
      state.itemNumber[1] = itemNumber;
      state.stepNumber[1] = RESEARCH_TOTAL_STEPS;
      state.timestamp[1] = 1234;
      const result = nextResearchItem(state, 1);
      assert.equal(result.grantedItemId, expectedId);
      assert.deepEqual(result.state.itemNumber, [0, expectedNext]);
      assert.deepEqual(result.state.stepNumber, [0, 0]);
      assert.deepEqual(result.state.timestamp, [0, 0]);
    }
  });

  it('does nothing before the tenth step', () => {
    const state = initialResearchState();
    state.stepNumber[0] = 9;
    const result = nextResearchItem(state, 0);
    assert.equal(result.grantedItemId, null);
    assert.equal(result.state, state);
  });

  it('resets the three arrays for one type only', () => {
    const state = initialResearchState();
    state.itemNumber = [3, 2];
    state.stepNumber = [7, 9];
    state.timestamp = [555, 666];
    const result = resetResearchItem(state, 0);
    assert.deepEqual(result.itemNumber, [0, 2]);
    assert.deepEqual(result.stepNumber, [0, 9]);
    assert.deepEqual(result.timestamp, [0, 666]);
    assert.deepEqual(state.itemNumber, [3, 2]);
  });
});

describe('robotic friend help', () => {
  it('grants two steps per friend and consumes the help list', () => {
    const state = initialResearchState();
    state.stepNumber[1] = 1;
    state.timestamp[1] = 4321;
    state.roboticSocialHelp = ['a', 'b', 'c'];
    const result = finishRoboticHelp(state);
    assert.equal(result.friendCount, 3);
    assert.equal(result.stepsGranted, 6);
    assert.deepEqual(result.state.stepNumber, [0, 7]);
    assert.deepEqual(result.state.timestamp, [0, 4321]);
    assert.deepEqual(result.state.roboticSocialHelp, []);
    const again = finishRoboticHelp(result.state);
    assert.equal(again.stepsGranted, 0);
    assert.deepEqual(again.state.stepNumber, [0, 7]);
  });

  it('caps at ten steps and clears the timer when the cap is reached', () => {
    const state = initialResearchState();
    state.stepNumber[1] = 7;
    state.timestamp[1] = 4321;
    state.roboticSocialHelp = ['a', 'b', 'c'];
    const result = finishRoboticHelp(state);
    assert.equal(result.stepsGranted, 3);
    assert.deepEqual(result.state.stepNumber, [0, RESEARCH_TOTAL_STEPS]);
    assert.deepEqual(result.state.timestamp, [0, 0]);
  });

  it('grants exactly one multiplier of two for a single friend', () => {
    const state = initialResearchState();
    state.roboticSocialHelp = ['a'];
    assert.equal(finishRoboticHelp(state).stepsGranted, RESEARCH_FRIENDS_MULTIPLIER);
  });
});
