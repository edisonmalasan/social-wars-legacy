/**
 * The last two GUI panels that are pure presentation.
 *
 * - `InventoryGridCells` is `GUI/InventoryItem.as`: every server-owned stored
 *   item is one cell, laid out in a grid, and dragging a cell onto another
 *   slot calls the cell's `setPos`. The **Place** button is the unchanged
 *   gesture — it still asks the host for `place_stored_item`, and the server
 *   decides whether the store really holds the item. The arrangement is UI
 *   state and is never saved.
 * - `InfoPopupBody` is `GUI/InfoPopup.as`: the HUD's own `Popover` shown with
 *   the original's display timer and `reposition` behaviour. It invents no
 *   readout: both lines come from `packages/client/src/hud.ts`, verbatim.
 *
 * Both are inline in the panels that already own those readouts. There is no
 * second modal, no server field of our own and no client-side outcome. The
 * original's cell and popup artwork stays excluded; only the behaviour is
 * drawn, with text and CSS.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react';

import type { Popover, StoredItemView } from '@swl/client';

import {
  inventoryCells,
  openInfoPopup,
  repositionInfoPopup,
  setInventoryCellPos,
  tickInfoPopup,
  type InfoPopupAnchor,
  type InfoPopupState,
  type InventoryCellView,
  type InventoryGridState,
} from './state.ts';

/** The inventory grid's props. */
export interface InventoryGridCellsProps {
  /** The stored items, derived from the server's answer. */
  readonly items: readonly StoredItemView[];
  /** The UI-only arrangement of those items. */
  readonly grid: InventoryGridState;
  /** The player dropped a cell onto another slot; replace the layout. */
  readonly onGrid: (grid: InventoryGridState) => void;
  /** The player picked an item to place; the host sends the request. */
  readonly onPlace?: (entry: StoredItemView) => void;
}

/**
 * The stored items as draggable grid cells.
 *
 * Each cell carries its own `setPos` result in inline CSS grid coordinates.
 * A drop onto another cell swaps the two entries through `setInventoryCellPos`;
 * nothing here changes an item id, a quantity or the map.
 */
export function InventoryGridCells({
  items,
  grid,
  onGrid,
  onPlace,
}: InventoryGridCellsProps): React.JSX.Element {
  const cells: readonly InventoryCellView[] = inventoryCells(items, grid);
  const dragged = useRef<number | null>(null);

  return (
    <ul className="swl-inventory-grid" data-swl-inventory-grid="" aria-label="Storage cells">
      {cells.map((cell) => (
        <li
          key={cell.itemId}
          className="swl-inventory-cell"
          data-swl-cell={cell.itemId}
          style={{ gridColumn: cell.col + 1, gridRow: cell.row + 1 }}
          draggable
          onDragStart={() => {
            dragged.current = cell.itemId;
          }}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            const itemId = dragged.current;
            dragged.current = null;
            if (itemId === null) return;
            onGrid(setInventoryCellPos(grid, itemId, cell.col, cell.row));
          }}
          onDragEnd={() => {
            dragged.current = null;
          }}
        >
          <span className="swl-inventory-cell-name" title={cell.name}>
            {cell.name}
          </span>
          <span className="swl-inventory-cell-qty">×{cell.quantity}</span>
          <button
            type="button"
            className="swl-inventory-place"
            onClick={() => onPlace?.(cell)}
          >
            Place
          </button>
        </li>
      ))}
    </ul>
  );
}

/** The info popup's props. */
export interface InfoPopupBodyProps {
  /** The HUD's own readout explanation, never a value invented here. */
  readonly popover: Popover;
  /** Where the readout was when the popup opened. */
  readonly anchor: InfoPopupAnchor;
  /** The host closes its readout's popover when the timer runs out. */
  readonly onExpire?: () => void;
}

/**
 * A timed, repositioned HUD popover.
 *
 * The timer is the client's own display lifetime and `reposition` is pure
 * geometry over the measured box and the viewport. When the lifetime is
 * spent the host is asked to close the readout's popover, so a second popup
 * never outlives the readout that owns it.
 */
export function InfoPopupBody({
  popover,
  anchor,
  onExpire,
}: InfoPopupBodyProps): React.JSX.Element | null {
  const [state, setState] = useState<InfoPopupState>(() => openInfoPopup(anchor));
  const [position, setPosition] = useState({ x: anchor.x, y: anchor.y + 8 });
  const box = useRef<HTMLDivElement>(null);
  const expire = useRef(onExpire);
  expire.current = onExpire;

  // A different readout owns a fresh popup with a fresh lifetime.
  useEffect(() => {
    setState(openInfoPopup(anchor));
  }, [anchor]);

  // The original's timer: one display second at a time.
  useEffect(() => {
    const timer = window.setInterval(() => {
      setState((current) => tickInfoPopup(current, 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  // The original's reposition: measure, then keep the box on screen.
  useLayoutEffect(() => {
    const rect = box.current?.getBoundingClientRect();
    setPosition(
      repositionInfoPopup(anchor, {
        width: window.innerWidth,
        height: window.innerHeight,
        popupWidth: rect?.width ?? 200,
        popupHeight: rect?.height ?? 60,
      }),
    );
  }, [anchor, popover.firstLine, popover.warningLine]);

  useEffect(() => {
    if (!state.anchor) expire.current?.();
  }, [state.anchor]);

  if (!state.anchor) return null;
  return (
    <div
      ref={box}
      className="swl-popover swl-info-popup"
      data-swl-info-popup={anchor.id}
      role="tooltip"
      style={{ left: position.x, top: position.y }}
    >
      <p className="swl-popover-first">{popover.firstLine}</p>
      {popover.warningLine ? (
        <p className="swl-popover-warning">{popover.warningLine}</p>
      ) : null}
    </div>
  );
}
