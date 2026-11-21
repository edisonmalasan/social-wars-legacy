/**
 * The inventory panel.
 *
 * The items are the **server's** stored items, read from `maps[0].store`;
 * their names, wire types and categories are the content's. The panel offers
 * a Place gesture that begins a placement — it does not put anything on the
 * map itself. The tile the player clicks next becomes a `place_stored_item`
 * request, and the server decides whether the store really holds the item.
 *
 * The category tabs are a **reading** of two inputs: the server's store and
 * the content's categories. They filter what is drawn; no tab grants, spends
 * or owns anything. The pure grouping lives in `@swl/client`.
 */
import { useState } from 'react';

import {
  inventoryCategories,
  itemsForCategory,
  type InventoryCategoryDefinition,
  type StoredItemView,
  type ArmyUnitView,
} from '@swl/client';

import { Collections } from './collections.tsx';
import { useRoster } from './roster.tsx';
import type { CollectionsPanelView } from './state.ts';

/** The inventory panel's tabs: All, a content category, or the collections tab. */
type InventoryTab = number | 'collections' | null;

/** The inventory panel's props. */
export interface InventoryProps {
  /** The stored items, derived from the server's answer. */
  items: readonly StoredItemView[];
  /** The content's categories, which name the tabs. */
  categories: Readonly<Record<string, InventoryCategoryDefinition>>;
  /** The content's collections with the server's progress. */
  collections: CollectionsPanelView;
  /** The army the server's save accounts for, from the same reading. */
  army?: readonly ArmyUnitView[];
  /** The player picked an item to place. */
  onPlace?: (entry: StoredItemView) => void;
}

/** The stored items the player owns, or an empty panel. */
export function Inventory({
  items,
  categories,
  collections,
  army = [],
  onPlace,
}: InventoryProps): React.JSX.Element {
  // The content's categories that actually hold a stored item, in id order.
  // With fewer than two there is nothing to choose between, so no tabs show.
  const groups = inventoryCategories(items, categories);
  const [tab, setTab] = useState<InventoryTab>(null);
  // A later server answer can empty the selected category, removing its tab.
  // Fall back to All so an invisible filter never hides the remaining items.
  const active: InventoryTab =
    tab === 'collections'
      ? 'collections'
      : typeof tab === 'number' && groups.some((group) => group.id === tab)
        ? tab
        : null;
  const visible = itemsForCategory(items, typeof active === 'number' ? active : null);
  // The roster is a gesture that opens the one shared dialog from this head;
  // opening a panel never changes the world.
  const roster = useRoster();

  return (
    <div className="swl-inventory" aria-label="Stored items">
      <div className="swl-inventory-head">
        <div className="swl-inventory-title">Storage</div>
        {roster.open ? (
          <button
            type="button"
            className="swl-inventory-roster"
            data-swl-roster-open=""
            onClick={roster.open}
          >
            Roster
          </button>
        ) : null}
        {groups.length > 1 || collections.entries.length > 0 ? (
          <nav className="swl-inventory-tabs" aria-label="Storage categories">
            <button
              type="button"
              className={active === null ? 'swl-tab swl-tab-active' : 'swl-tab'}
              aria-pressed={active === null}
              onClick={() => setTab(null)}
            >
              All
            </button>
            {groups.map((group) => (
              <button
                key={group.id}
                type="button"
                className={active === group.id ? 'swl-tab swl-tab-active' : 'swl-tab'}
                aria-pressed={active === group.id}
                onClick={() => setTab(group.id)}
              >
                {group.name}
              </button>
            ))}
            {collections.entries.length > 0 ? (
              <button
                type="button"
                className={active === 'collections' ? 'swl-tab swl-tab-active' : 'swl-tab'}
                aria-pressed={active === 'collections'}
                onClick={() => setTab('collections')}
              >
                Collections
              </button>
            ) : null}
          </nav>
        ) : null}
      </div>
      <div className="swl-inventory-scroll">
        {active === 'collections' ? (
          <Collections view={collections} />
        ) : visible.length === 0 ? (
          <p className="swl-inventory-empty">Nothing in storage.</p>
        ) : (
          <ul className="swl-inventory-list">
            {visible.map((entry) => (
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
    </div>
  );
}
