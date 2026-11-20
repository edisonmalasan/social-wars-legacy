import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  buildingInfoView,
  finishView,
  trainingView,
  upgradeView,
} from './management.ts';

describe('a building\'s info view', () => {
  it('exists for a building that produces no resource', () => {
    const view = buildingInfoView({
      name: 'Command Center',
      nextName: null,
      nextMinLevel: null,
      playerLevel: 1,
      startedAt: 100,
      buildTime: 0,
      clicksToBuild: 0,
      now: 200,
    });
    assert.equal(view.name, 'Command Center');
    assert.equal(view.upgrade, null);
    assert.equal(view.finish, null);
  });
});

describe('the upgrade action', () => {
  it('names the next tier and its level requirement', () => {
    assert.deepEqual(upgradeView('Academy II', 3, 1), {
      nextName: 'Academy II',
      requirement: 'Requires level 3',
    });
  });

  it('is absent when the content has no next tier', () => {
    assert.equal(upgradeView(null, null, 1), null);
  });
});

describe('the hurry-up action', () => {
  it('shows the whole seconds left and the clicks the request carries', () => {
    assert.deepEqual(finishView(100, 30, 5, 115), {
      remainingSeconds: 15,
      clicksToBuild: 5,
    });
  });

  it('is absent once the build has finished', () => {
    assert.equal(finishView(100, 30, 5, 130), null);
  });
});

describe('the training queue', () => {
  it('reads the server attribute bag and marks a finished unit ready to take', () => {
    assert.deepEqual(trainingView({ nu: 2, ts: 100, ui: 1008 }, 20, 125), {
      queued: 2,
      unitItemId: 1008,
      remainingSeconds: 0,
      readyToTake: true,
    });
  });

  it('counts down while the current unit is still training', () => {
    assert.deepEqual(trainingView({ nu: 1, ts: 100, ui: 1008 }, 20, 110), {
      queued: 1,
      unitItemId: 1008,
      remainingSeconds: 10,
      readyToTake: false,
    });
  });

  it('never claims a ready unit when the start time is missing', () => {
    const view = trainingView({ nu: 1 }, 20, 100);
    assert.equal(view.queued, 1);
    assert.equal(view.remainingSeconds, 20);
    assert.equal(view.readyToTake, false);
  });

  it('is empty when the bag has no queue', () => {
    assert.deepEqual(trainingView(undefined, 20, 100), {
      queued: 0,
      unitItemId: 0,
      remainingSeconds: 0,
      readyToTake: false,
    });
  });
});
