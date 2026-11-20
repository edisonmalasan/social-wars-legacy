/**
 * The inventory panel.
 *
 * The items are the **server's** stored items, read from `maps[0].store`;
 * their names and wire types are the content's. The panel offers a Place
 * gesture that begins a placement — it does not put anything on the map
 * itself. The tile the player clicks next becomes a `place_stored_item`
 * request, and the server decides whether the store really holds the item.
 */
import type { ArmyUnitView, StoredItemView } from '@swl/client';

/** The inventory panel's props. */
export interface InventoryProps {
  /** The stored items, derived from the server's answer. */
  items: readonly StoredItemView[];
  /** The army the server's save accounts for, from the same reading. */
  army?: readonly ArmyUnitView[];
  /** The player picked an item to place. */
  onPlace?: (entry: StoredItemView) => void;
}

/** The stored items the player owns, or an empty panel. */
export function Inventory({ items, army = [], onPlace }: InventoryProps): React.JSX.Element {
  return (
    <div className="swl-inventory" aria-label="Stored items">
      <div className="swl-inventory-title">Storage</div>
      {items.length === 0 ? (
        <p className="swl-inventory-empty">Nothing in storage.</p>
      ) : (
        <ul className="swl-inventory-list">
          {items.map((entry) => (
            <li className="swl-inventory-item" key={entry.itemId}>
              <span className="swl-inventory-name">{entry.name}</span>
              <span className="swl-inventory-qty">×{entry.quantity}</span>
              <button
                type="button"
                className="swl-inventory-place"
                onClick={() => onPlace?.(entry)}
              >
                Place
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="swl-inventory-title">Army</div>
      {army.length === 0 ? (
        <p className="swl-inventory-empty">No units available.</p>
      ) : (
        <ul className="swl-inventory-list" data-swl-army="">
          {army.map((unit) => (
            <li className="swl-inventory-item" key={unit.itemId}>
              <span className="swl-inventory-name">{unit.name}</span>
              <span className="swl-inventory-qty">×{unit.available}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
