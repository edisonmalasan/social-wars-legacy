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
    });
  }
  return out;
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
