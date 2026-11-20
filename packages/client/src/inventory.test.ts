import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { storedItems, storedPlacement } from './inventory.ts';
import type { WorldSnapshot } from './session.ts';

/** The item definitions the inventory needs, as the content bundle gives them. */
const DEFINITIONS = [
  { id: 1, name: 'House I', type: 'b' },
  { id: 26, name: 'Command Center', type: 'b' },
  { id: 1001, name: 'Soldier', type: 'u' },
];

function world(store?: Record<string, number>): WorldSnapshot {
  return {
    maps: [
      {
        id: 0,
        items: {},
        ...(store === undefined ? {} : { store }),
        level: 1,
      },
    ],
    privateState: {},
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
  };
}

describe('the stored items', () => {
  it('reads the quantities out of the server\'s own store', () => {
    const view = storedItems(world({ '1': 3, '1001': 2 }), DEFINITIONS);
    assert.deepEqual(view, [
      { itemId: 1, quantity: 3, name: 'House I', type: 'b' },
      { itemId: 1001, quantity: 2, name: 'Soldier', type: 'u' },
    ]);
  });

  it('reads nothing from a save with no store, without inventing any', () => {
    assert.deepEqual(storedItems(world(), DEFINITIONS), []);
    assert.deepEqual(storedItems(world({}), DEFINITIONS), []);
    assert.deepEqual(storedItems({ ...world(), maps: [] }, DEFINITIONS), []);
  });

  it('leaves out malformed quantities and ids the content does not name', () => {
    const view = storedItems(
      world({ '1': 2, '26': 0, '99': 4, '1001': -1, '1002': 1.5 }),
      DEFINITIONS,
    );
    assert.deepEqual(view, [{ itemId: 1, quantity: 2, name: 'House I', type: 'b' }]);
  });
});

describe('placing a stored item', () => {
  const entry = { itemId: 1, quantity: 3, name: 'House I', type: 'b' as const };

  it('is the place_stored_item command, with no price or quantity of the client\'s own', () => {
    const command = storedPlacement(entry, 12, 34);
    assert.deepEqual(command, {
      map: 0,
      name: 'place_stored_item',
      args: [0, 1, 12, 34, 1, 0, 0, 0],
    });
  });

  it('offers no action for an entry with nothing to place', () => {
    assert.equal(storedPlacement({ ...entry, quantity: 0 }, 12, 34), null);
    assert.equal(storedPlacement({ ...entry, quantity: -1 }, 12, 34), null);
  });

  it('offers no action for a tile that cannot be named', () => {
    assert.equal(storedPlacement(entry, Number.NaN, 34), null);
    assert.equal(storedPlacement(entry, 12, Number.POSITIVE_INFINITY), null);
  });
});
