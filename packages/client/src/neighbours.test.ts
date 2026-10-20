import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  buildingsToHurryUp,
  isGeneral,
  isReadyToCollect,
  neighbourStrip,
  type Neighbour,
} from './neighbours.ts';

function neighbour(over: Partial<Neighbour> = {}): Neighbour {
  return {
    id: 'p2',
    name: 'Neighbour',
    level: 3,
    xp: 250,
    resources: { g: 100, w: 200, o: 50, s: 25, c: 10, e: 30, x: 250, m: 0 },
    static: false,
    ...over,
  };
}

describe('the neighbour strip', () => {
  it('keeps the server order', () => {
    const strip = neighbourStrip([
      neighbour({ id: 'a' }),
      neighbour({ id: 'b' }),
      neighbour({ id: 'c' }),
    ]);
    assert.deepEqual(
      strip.map((entry) => entry.neighbour.id),
      ['a', 'b', 'c'],
    );
  });

  it('shows a placeholder portrait, because the clone has no Facebook photo', () => {
    const strip = neighbourStrip([neighbour()]);
    assert.equal(strip[0]!.portrait, 'placeholder');
  });

  it('does not let the general be hurried up', () => {
    // The general, Mike, is not a neighbour anybody can hurry up.
    const strip = neighbourStrip(
      [neighbour({ id: '100000030' }), neighbour({ id: 'p2' })],
      { canHurryUp: true },
    );
    assert.equal(strip[0]!.canHurryUp, false);
    assert.equal(strip[1]!.canHurryUp, true);
  });

  it('recognises the general by his id', () => {
    assert.equal(isGeneral(neighbour({ id: '100000030' })), true);
    assert.equal(isGeneral(neighbour({ id: '100000031' })), true);
    assert.equal(isGeneral(neighbour({ id: 'p2' })), false);
  });

  it('cannot hurry anybody up when the town hall cannot be', () => {
    const strip = neighbourStrip([neighbour()], { canHurryUp: false });
    assert.equal(strip[0]!.canHurryUp, false);
  });
});

describe('the hurry-up rule', () => {
  it('is the client own: the countdown has finished', () => {
    assert.equal(
      isReadyToCollect({ id: '1', activation: 60, collectedAt: 59 }),
      false,
    );
    assert.equal(
      isReadyToCollect({ id: '1', activation: 60, collectedAt: 60 }),
      true,
    );
  });

  it('needs a building that collects at all', () => {
    // A building with no activation does not collect, so there is nothing
    // to hurry up.
    assert.equal(
      isReadyToCollect({ id: '1', activation: 0, collectedAt: 1000 }),
      false,
    );
  });

  it('picks out the buildings that are ready', () => {
    const ready = buildingsToHurryUp([
      { id: '1', activation: 60, collectedAt: 30 },
      { id: '2', activation: 60, collectedAt: 60 },
      { id: '3', activation: 0, collectedAt: 0 },
    ]);
    assert.deepEqual(
      ready.map((building) => building.id),
      ['2'],
    );
  });
});
