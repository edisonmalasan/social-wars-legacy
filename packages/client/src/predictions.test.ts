import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Predictions, renderState } from './predictions.ts';

describe('the predictions', () => {
  it('records a prediction and marks it outstanding', () => {
    const predictions = new Predictions<string>();
    predictions.send('r1', 'gold +10', 1000);
    assert.equal(predictions.size, 1);
    assert.equal(predictions.pending.length, 1);
    assert.equal(predictions.get('r1')?.state, 'pending');
  });

  it('confirms a prediction when the server agrees', () => {
    const predictions = new Predictions<string>();
    predictions.send('r1', 'gold +10', 1000);
    const settlement = predictions.settle('r1', true);
    assert.ok(settlement);
    assert.equal(settlement.confirmed, true);
    assert.equal(settlement.duplicate, false);
    assert.equal(predictions.get('r1')?.state, 'confirmed');
    assert.equal(predictions.pending.length, 0);
  });

  it('rejects a prediction when the server refuses', () => {
    const predictions = new Predictions<string>();
    predictions.send('r1', 'gold +10', 1000);
    const settlement = predictions.settle('r1', false);
    assert.ok(settlement);
    assert.equal(settlement.confirmed, false);
    assert.equal(predictions.get('r1')?.state, 'rejected');
  });

  it('reports a duplicate answer rather than settling it twice', () => {
    // The same answer arriving twice must not undo a confirmed outcome.
    const predictions = new Predictions<string>();
    predictions.send('r1', 'gold +10', 1000);
    predictions.settle('r1', true);
    const again = predictions.settle('r1', false);
    assert.ok(again);
    assert.equal(again.duplicate, true);
    // The state is unchanged: still confirmed.
    assert.equal(predictions.get('r1')?.state, 'confirmed');
  });

  it('ignores an answer for a prediction it does not have', () => {
    const predictions = new Predictions<string>();
    assert.equal(predictions.settle('nobody', true), null);
  });

  it('replaces a prediction when the same id is sent again', () => {
    // The retry of a request that was lost in flight is the same request.
    const predictions = new Predictions<string>();
    predictions.send('r1', 'gold +10', 1000);
    predictions.send('r1', 'gold +10', 2000);
    assert.equal(predictions.size, 1);
    assert.equal(predictions.get('r1')?.sentAt, 2000);
  });

  it('forgets the settled ones and keeps the outstanding ones', () => {
    const predictions = new Predictions<string>();
    predictions.send('r1', 'a', 1000);
    predictions.send('r2', 'b', 2000);
    predictions.settle('r1', true);
    predictions.forgetSettled();
    assert.equal(predictions.size, 1);
    assert.equal(predictions.get('r1'), undefined);
    assert.ok(predictions.get('r2'));
  });

  it('is bounded, and drops the settled ones first', () => {
    const predictions = new Predictions<string>(3);
    predictions.send('r1', 'a', 1000);
    predictions.settle('r1', true);
    predictions.send('r2', 'b', 2000);
    predictions.send('r3', 'c', 3000);
    predictions.send('r4', 'd', 4000);
    assert.ok(predictions.size <= 3);
    // The settled one went first.
    assert.equal(predictions.get('r1'), undefined);
  });
});

describe('what the renderer draws', () => {
  it('is the server state, with the predictions as a separate overlay', () => {
    const predictions = new Predictions<number>();
    predictions.send('r1', 10, 1000);
    predictions.send('r2', 20, 2000);

    const state = renderState(predictions, 100, (base, prediction) => base + prediction);
    assert.equal(state.confirmed, 100);
    assert.equal(state.unconfirmed.length, 2);
    // The overlay is the prediction's own value, never folded into the
    // confirmed state.
    assert.deepEqual(
      state.unconfirmed.map((prediction) => prediction.expected),
      [10, 20],
    );
  });

  it('is null before the first answer, so nothing is drawn as final', () => {
    const predictions = new Predictions<number>();
    predictions.send('r1', 10, 1000);
    const state = renderState(predictions, null, (base, prediction) => base + prediction);
    assert.equal(state.confirmed, null);
    assert.equal(state.unconfirmed.length, 1);
  });

  it('drops a rejected prediction from the overlay', () => {
    const predictions = new Predictions<number>();
    predictions.send('r1', 10, 1000);
    predictions.settle('r1', false);
    const state = renderState(predictions, 100, (base, prediction) => base + prediction);
    assert.equal(state.confirmed, 100);
    assert.equal(state.unconfirmed.length, 0);
  });

  it('drops a confirmed prediction from the overlay too', () => {
    // A confirmed prediction is in the server's state already.
    const predictions = new Predictions<number>();
    predictions.send('r1', 10, 1000);
    predictions.settle('r1', true);
    const state = renderState(predictions, 110, (base, prediction) => base + prediction);
    assert.equal(state.confirmed, 110);
    assert.equal(state.unconfirmed.length, 0);
  });

  it('orders the overlay oldest first', () => {
    const predictions = new Predictions<number>();
    predictions.send('r2', 20, 2000);
    predictions.send('r1', 10, 1000);
    const state = renderState(predictions, 0, (base, prediction) => base + prediction);
    assert.deepEqual(
      state.unconfirmed.map((prediction) => prediction.id),
      ['r1', 'r2'],
    );
  });
});
