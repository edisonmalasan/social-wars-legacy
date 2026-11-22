/**
 * Tests for the two presentation-only GUI panels: the inventory cell grid
 * (`GUI/InventoryItem.as`) and the timed info popup (`GUI/InfoPopup.as`).
 *
 * These are client-only arrangements and timers. They read the server's
 * stored items / the HUD's own popover, and they must never produce a command,
 * a resource or an outcome of their own.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { StoredItemView } from '@swl/client';

import { uiCss } from './css.ts';
import {
  CLOSED_INFO_POPUP,
  INFO_POPUP_LIFETIME_SECONDS,
  inventoryCellAt,
  inventoryCells,
  inventoryGrid,
  openInfoPopup,
  reconcileInventoryGrid,
  repositionInfoPopup,
  setInventoryCellPos,
  tickInfoPopup,
} from './state.ts';

function stored(id: number, quantity = 1): StoredItemView {
  return {
    itemId: id,
    quantity,
    name: `Item ${id}`,
    type: 'b',
    categoryId: 1,
  };
}

describe('the inventory cell grid', () => {
  it('seeds cell order from the server-owned stored items', () => {
    const items = [stored(7, 2), stored(3), stored(11, 4)];
    const grid = inventoryGrid(items);
    assert.deepEqual(grid.order, [7, 3, 11]);
    assert.deepEqual(
      inventoryCells(items, grid).map((cell) => ({
        itemId: cell.itemId,
        col: cell.col,
        row: cell.row,
      })),
      [
        { itemId: 7, col: 0, row: 0 },
        { itemId: 3, col: 1, row: 0 },
        { itemId: 11, col: 0, row: 1 },
      ],
    );
  });

  it('skips duplicate and non-integer ids instead of inventing a cell', () => {
    const grid = inventoryGrid([stored(4), stored(4), stored(Number.NaN)]);
    assert.deepEqual(grid.order, [4]);
  });

  it('moves one cell onto another slot, swapping the two items', () => {
    const items = [stored(7), stored(3), stored(11), stored(5)];
    const grid = inventoryGrid(items);
    const moved = setInventoryCellPos(grid, 7, 1, 1);
    assert.deepEqual(moved.order, [5, 3, 11, 7]);
    assert.deepEqual(inventoryCellAt(moved, 7), { index: 3, col: 1, row: 1 });
    // The original layout is untouched: setPos returns a new UI state.
    assert.deepEqual(grid.order, [7, 3, 11, 5]);
  });

  it('clamps a drag to the filled grid and ignores a no-op or unknown cell', () => {
    const grid = inventoryGrid([stored(7), stored(3), stored(11)]);
    assert.equal(setInventoryCellPos(grid, 7, 0, 0), grid);
    assert.equal(setInventoryCellPos(grid, 999, 1, 0), grid);
    // A malformed column falls back to the cell's own column, then still
    // clamps to the grid; it never fabricates a position outside it.
    const fallback = setInventoryCellPos(grid, 7, Number.NaN, 1);
    assert.deepEqual(fallback.order, [11, 3, 7]);
    const clamped = setInventoryCellPos(grid, 7, 99, 99);
    assert.deepEqual(clamped.order, [11, 3, 7]);
  });

  it('keeps a layout across a new server answer', () => {
    const grid = inventoryGrid([stored(7), stored(3), stored(11)]);
    const rearranged = setInventoryCellPos(grid, 11, 0, 0);
    const reconciled = reconcileInventoryGrid(
      rearranged,
      [stored(3), stored(7), stored(11), stored(20)],
    );
    assert.deepEqual(reconciled.order, [11, 3, 7, 20]);
    assert.deepEqual(reconciled.columns, grid.columns);
  });

  it('never builds a command: the layout holds ids and positions only', () => {
    const grid = inventoryGrid([stored(7), stored(3)]);
    const cell = inventoryCells([stored(7), stored(3)], grid)[0]!;
    assert.deepEqual(Object.keys(cell).sort(), [
      'categoryId', 'col', 'index', 'itemId', 'name', 'quantity', 'row', 'type',
    ]);
    assert.ok(!('command' in cell));
  });
});

const anchor = { id: 'Gold', x: 120, y: 40 };

describe('the timed info popup', () => {
  it('opens a HUD readout with its full display lifetime', () => {
    const state = openInfoPopup(anchor);
    assert.deepEqual(state.anchor, anchor);
    assert.equal(state.secondsRemaining, INFO_POPUP_LIFETIME_SECONDS);
  });

  it('ticks the timer down and closes when it runs out', () => {
    const opened = openInfoPopup(anchor, 3);
    assert.equal(tickInfoPopup(opened, 1).secondsRemaining, 2);
    assert.deepEqual(tickInfoPopup(opened, 5), CLOSED_INFO_POPUP);
    assert.deepEqual(tickInfoPopup(CLOSED_INFO_POPUP, 1), CLOSED_INFO_POPUP);
  });

  it('ignores a malformed anchor or elapsed time', () => {
    assert.deepEqual(openInfoPopup({ id: '', x: 1, y: 2 }), CLOSED_INFO_POPUP);
    assert.deepEqual(openInfoPopup({ id: 'Gold', x: Number.NaN, y: 2 }), CLOSED_INFO_POPUP);
    assert.equal(tickInfoPopup(openInfoPopup(anchor, 3), Number.NaN).secondsRemaining, 3);
  });

  it('repositions on the anchor and keeps the box inside the viewport', () => {
    // A box that fits below sits centred under the readout.
    assert.deepEqual(
      repositionInfoPopup(anchor, { width: 800, height: 600, popupWidth: 200, popupHeight: 60 }),
      { x: 20, y: 48 },
    );
    // Near the right edge it is pulled back in, never clipped.
    assert.deepEqual(
      repositionInfoPopup(
        { id: 'Gold', x: 790, y: 40 },
        { width: 800, height: 600, popupWidth: 200, popupHeight: 60 },
      ),
      { x: 592, y: 48 },
    );
    // Near the bottom it flips above the readout.
    assert.deepEqual(
      repositionInfoPopup(
        { id: 'Gold', x: 120, y: 580 },
        { width: 800, height: 600, popupWidth: 200, popupHeight: 60 },
      ),
      { x: 20, y: 512 },
    );
  });
});

describe('the detail panels stylesheet', () => {
  it('draws both panels with their own classes', () => {
    const css = uiCss();
    for (const className of [
      'swl-info-popup',
      'swl-inventory-grid',
      'swl-inventory-cell',
      'swl-inventory-cell-name',
    ]) {
      assert.ok(css.includes(`.${className}`), `${className} has no stylesheet rule`);
    }
  });
});
