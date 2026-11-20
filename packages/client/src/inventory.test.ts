import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  inventoryCategories,
  itemsForCategory,
  storedItems,
  storedPlacement,
} from './inventory.ts';
import type { WorldSnapshot } from './session.ts';

/** The item definitions the inventory needs, as the content bundle gives them. */
const DEFINITIONS = [
  { id: 1, name: 'House I', type: 'b', categoryId: 1 },
  { id: 26, name: 'Command Center', type: 'b', categoryId: 1 },
  { id: 1001, name: 'Soldier', type: 'u', categoryId: 2 },
];

/** The content's categories, which name the inventory's tabs. */
const CATEGORIES = {
  '1': { id: 1, name: 'Buildings' },
  '2': { id: 2, name: 'Units' },
  '3': { id: 3, name: 'Decorations' },
};

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
      { itemId: 1, quantity: 3, name: 'House I', type: 'b', categoryId: 1 },
      { itemId: 1001, quantity: 2, name: 'Soldier', type: 'u', categoryId: 2 },
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
    assert.deepEqual(view, [{ itemId: 1, quantity: 2, name: 'House I', type: 'b', categoryId: 1 }]);
  });
});

describe('placing a stored item', () => {
  const entry = { itemId: 1, quantity: 3, name: 'House I', type: 'b' as const, categoryId: 1 };

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

describe('inventory categories', () => {
  // The store's integer-like keys come back in ascending numeric order.
  const items = storedItems(world({ '1': 3, '1001': 2, '26': 1 }), DEFINITIONS);

  it('groups stored items under the content category, in category id order', () => {
    const groups = inventoryCategories(items, CATEGORIES);
    assert.deepEqual(
      groups.map((group) => [group.id, group.name]),
      [
        [1, 'Buildings'],
        [2, 'Units'],
      ],
    );
    assert.deepEqual(groups[0]!.items.map((entry) => entry.itemId), [1, 26]);
    assert.deepEqual(groups[1]!.items.map((entry) => entry.itemId), [1001]);
  });

  it('offers no tab for a content category that holds no stored item', () => {
    const groups = inventoryCategories(items, {
      ...CATEGORIES,
      '9': { id: 9, name: 'Empty' },
    });
    assert.deepEqual(groups.map((group) => group.id), [1, 2]);
  });

  it('reads no tabs from a content with no usable categories', () => {
    assert.deepEqual(inventoryCategories(items, {}), []);
    assert.deepEqual(
      inventoryCategories(items, { 'x': { name: 'No id' } } as unknown as typeof CATEGORIES),
      [],
    );
  });

  it('leaves an item with an unknown or missing category out of every tab, but not out of All', () => {
    const orphan = {
      itemId: 7,
      quantity: 1,
      name: 'Unknown',
      type: 'b' as const,
      categoryId: null,
    };
    const withOrphan = [...items, orphan];
    assert.deepEqual(inventoryCategories(withOrphan, CATEGORIES).map((g) => g.id), [1, 2]);
    assert.deepEqual(
      itemsForCategory(withOrphan, null).map((entry) => entry.itemId),
      [1, 26, 1001, 7],
    );
  });

  it('filters by the active category, with a null id meaning All', () => {
    assert.deepEqual(itemsForCategory(items, 2).map((entry) => entry.itemId), [1001]);
    assert.deepEqual(itemsForCategory(items, 1).map((entry) => entry.itemId), [1, 26]);
    assert.deepEqual(itemsForCategory(items, 999), []);
    assert.deepEqual(itemsForCategory(items, null), items);
  });

  it('does not mutate the stored items it groups', () => {
    const before = [...items];
    inventoryCategories(before, CATEGORIES);
    itemsForCategory(before, 1);
    assert.deepEqual(before, items);
  });
});
