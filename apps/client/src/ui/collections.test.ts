import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { WorldSnapshot } from '@swl/client';
import type { ContentBundle } from '@swl/content';

import { collectionsPanel } from './state.ts';

/** A content catalogue: the names and prize are the content's, not the client's. */
function bundle(): ContentBundle {
  return {
    items: [
      { id: 66, name: 'Draggy A' },
      { id: 67, name: 'Draggy B' },
      { id: 1085, name: 'Dragon' },
    ],
    collections: [
      {
        id: '1',
        name: 'Draggy Collection',
        description: 'collection description 1',
        cashPrice: '35',
        item_ids: '[66,67,68]',
        prize: '{"1085":1}',
      },
      { id: 'bad', name: 'Malformed', item_ids: 'not json', prize: '{"1085":1}' },
    ],
    expansionPrices: [],
    globals: {},
    categories: {},
  } as unknown as ContentBundle;
}

/** The store and completion state the server owns. */
function world(store: Record<string, number>, completed: unknown): WorldSnapshot {
  return {
    maps: [{ id: 0, items: {}, store }],
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    privateState: { collections: completed },
  } as unknown as WorldSnapshot;
}

describe('the collections tab', () => {
  it('reads the content rows and the server-held progress', () => {
    const view = collectionsPanel(bundle(), world({ 66: 2, 1085: 9 }, [1]));
    assert.equal(view.entries.length, 1);
    const entry = view.entries[0]!;
    assert.equal(entry.id, 1);
    assert.equal(entry.name, 'Draggy Collection');
    assert.equal(entry.description, 'collection description 1');
    assert.equal(entry.cashPrice, 35);
    assert.equal(entry.held, 1);
    assert.deepEqual(
      entry.items.map((item) => [item.itemId, item.name, item.quantity]),
      [
        [66, 'Draggy A', 2],
        [67, 'Draggy B', 0],
        [68, 'item 68', 0],
      ],
    );
    assert.equal(entry.completed, true);
    assert.equal(entry.prize, 'Dragon ×1');
    // Nothing in the view can grant the prize: it is text and readings only.
    assert.deepEqual(Object.keys(entry).sort(), [
      'cashPrice',
      'completed',
      'description',
      'held',
      'id',
      'items',
      'name',
      'prize',
    ]);
  });

  it('leaves a collection incomplete when the server did not name it', () => {
    const entry = collectionsPanel(bundle(), world({}, [2, '3'])).entries[0]!;
    assert.equal(entry.completed, false);
    assert.equal(entry.held, 0);
  });

  it('skips malformed content rows instead of inventing a collection', () => {
    assert.equal(collectionsPanel(bundle(), world({}, [])).entries.length, 1);
  });

  it('ignores non-positive store quantities', () => {
    const entry = collectionsPanel(bundle(), world({ 66: 0, 67: -4 }, [])).entries[0]!;
    assert.equal(entry.held, 0);
    assert.equal(entry.items[0]!.quantity, 0);
  });

  it('draws nothing when the content has no collections', () => {
    const empty = { ...bundle(), collections: [] } as ContentBundle;
    assert.deepEqual(collectionsPanel(empty, world({}, [])), { entries: [] });
  });
});
