/**
 * The player's item store, read from the server's answer.
 *
 * The save keeps bought-but-unplaced items on the player's own map as
 * `map.store[itemId] = quantity` (see `packages/server/src/mapstore.ts`).
 * The world endpoint sends that map verbatim, so the inventory is a **reading**
 * of the server's state: no item and no quantity is invented here. An entry
 * whose id the content does not name, or whose quantity is not a positive
 * whole number, is left out rather than guessed at.
 *
 * Placing one is a gesture that becomes the `place_stored_item` request. The
 * client names only the item and the tile; the server checks the store and
 * removes exactly one.
 */
import { itemType, type ItemType } from './buildmenu.ts';
import { placeStoredItem, type NativeCommand } from './requests.ts';
import type { WorldSnapshot } from './session.ts';

/** The part of a content item the inventory needs to name an entry. */
export interface StoredItemDefinition {
  /** The item's id in the content bundle. */
  readonly id: number;
  /** The name the content gives it. */
  readonly name: string;
  /** The content's type letter ('b' building, 'u' unit). */
  readonly type: string;
  /** The content's category id, which names the inventory's tab. */
  readonly categoryId?: number;
}

/** One stored item, as the inventory draws it. */
export interface StoredItemView {
  /** The content id of the stored item. */
  readonly itemId: number;
  /** How many the server's store holds. */
  readonly quantity: number;
  /** The name from the content, not a client label. */
  readonly name: string;
  /** The wire type the placement must carry. */
  readonly type: ItemType;
  /** The content's category id, or null when the content names none. */
  readonly categoryId: number | null;
}

/**
 * The stored items, in the order the server's store gives them.
 *
 * A missing store reads as an empty one; it is not a reason to fabricate an
 * entry. The quantity is the server's own whole number, never a rounded guess.
 */
export function storedItems(
  world: WorldSnapshot,
  definitions: readonly StoredItemDefinition[],
): StoredItemView[] {
  const store = world.maps[0]?.store;
  if (!store || typeof store !== 'object' || Array.isArray(store)) return [];

  const byId = new Map<number, StoredItemDefinition>();
  for (const definition of definitions) {
    if (Number.isInteger(definition.id) && definition.id > 0) {
      byId.set(definition.id, definition);
    }
  }

  const out: StoredItemView[] = [];
  for (const [key, value] of Object.entries(store)) {
    const itemId = Number(key);
    const definition = byId.get(itemId);
    if (!definition) continue;
    const quantity = Number(value);
    if (!Number.isInteger(quantity) || quantity <= 0) continue;
    out.push({
      itemId,
      quantity,
      name: definition.name,
      type: itemType(definition.type),
      categoryId:
        typeof definition.categoryId === 'number' && Number.isInteger(definition.categoryId)
          ? definition.categoryId
          : null,
    });
  }
  return out;
}

/** The shape of a content category the inventory needs to name a tab. */
export interface InventoryCategoryDefinition {
  readonly id: number;
  readonly name: string;
}

/** One inventory tab: a content category and the stored items in it. */
export interface InventoryCategory {
  /** The content's category id. */
  readonly id: number;
  /** The content's name of the category, not a client label. */
  readonly name: string;
  /** The stored items whose content item belongs to this category. */
  readonly items: readonly StoredItemView[];
}

/**
 * The stored items grouped under the content's categories.
 *
 * The tabs are the **content's** (`categories` in the bundle), and the items
 * are the **server's** (`storedItems`). Only a category that actually holds a
 * stored item becomes a tab, so the panel does not offer dozens of empty ones;
 * tabs come in content id order. An item whose category the content does not
 * name appears in no tab here, but is still listed by the "All" view.
 *
 * This reads two inputs; it neither owns a store nor decides ownership. It is
 * pure: the same store and the same content always give the same tabs.
 */
export function inventoryCategories(
  items: readonly StoredItemView[],
  categories: Readonly<Record<string, InventoryCategoryDefinition>>,
): InventoryCategory[] {
  const names = new Map<number, string>();
  for (const category of Object.values(categories)) {
    if (!category || typeof category !== 'object') continue;
    if (!Number.isInteger(category.id) || typeof category.name !== 'string') continue;
    names.set(category.id, category.name);
  }

  const grouped = new Map<number, StoredItemView[]>();
  for (const item of items) {
    if (item.categoryId === null || !names.has(item.categoryId)) continue;
    const bucket = grouped.get(item.categoryId) ?? [];
    bucket.push(item);
    grouped.set(item.categoryId, bucket);
  }

  return [...grouped.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([id, bucket]) => ({ id, name: names.get(id)!, items: bucket }));
}

/**
 * The stored items the active tab draws. A null id is the "All" tab: every
 * stored item, including one whose category the content does not name, stays
 * visible there. Nothing is reordered or invented.
 */
export function itemsForCategory(
  items: readonly StoredItemView[],
  categoryId: number | null,
): readonly StoredItemView[] {
  if (categoryId === null) return items;
  return items.filter((item) => item.categoryId === categoryId);
}

/**
 * The placement an inventory row offers, or null when there is nothing to
 * place. The command is the client's existing request builder; it carries no
 * price, quantity or reward of the client's own.
 */
export function storedPlacement(
  entry: StoredItemView,
  tx: number,
  ty: number,
): NativeCommand | null {
  if (!Number.isInteger(entry.itemId) || entry.itemId <= 0) return null;
  if (!Number.isInteger(entry.quantity) || entry.quantity <= 0) return null;
  if (!Number.isFinite(tx) || !Number.isFinite(ty)) return null;
  return placeStoredItem(entry.itemId, tx, ty);
}
