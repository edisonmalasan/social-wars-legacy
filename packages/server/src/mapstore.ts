/**
 * The player's **item store**: the buildings and units bought but not yet
 * placed.
 *
 * The legacy save keeps it on the player's own map as
 * `map.store[itemId] = quantity`. The upstream's `remove_store_item` never
 * checks that the entry exists, so a client could place the same stored
 * building over and over. These helpers are the server's own accessors: a
 * placement must find a positive quantity and remove exactly one.
 *
 * Older saves may have no `store` at all, so every reader tolerates a missing
 * or malformed field. A writer preserves the other entries instead of
 * replacing the whole object with a filtered copy.
 */

/** The store's positive, whole-number quantities, keyed by item id. */
export type ItemStore = Record<string, number>;

function storeObject(map: Record<string, unknown> | undefined): Record<string, unknown> | null {
  const value = map?.['store'];
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function quantityOf(value: unknown): number {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return 0;
  return Math.trunc(number);
}

/** A copy of the map's item store, with malformed entries left out. */
export function mapStore(map: Record<string, unknown> | undefined): ItemStore {
  const raw = storeObject(map);
  if (raw === null) return {};
  const out: ItemStore = {};
  for (const [key, value] of Object.entries(raw)) {
    const quantity = quantityOf(value);
    if (quantity > 0) out[key] = quantity;
  }
  return out;
}

/** How many of an item the store holds. */
export function storeQuantity(
  map: Record<string, unknown> | undefined,
  itemId: number,
): number {
  const raw = storeObject(map);
  if (raw === null) return 0;
  return quantityOf(raw[String(itemId)]);
}

/** Add whole items to the store, creating the store if the save has none. */
export function addStoreItem(
  map: Record<string, unknown>,
  itemId: number,
  quantity = 1,
): void {
  if (!Number.isInteger(itemId) || itemId <= 0) return;
  const added = Math.trunc(quantity);
  if (!Number.isFinite(added) || added <= 0) return;

  const raw = storeObject(map) ?? {};
  const key = String(itemId);
  raw[key] = quantityOf(raw[key]) + added;
  map['store'] = raw;
}

/**
 * Remove whole items from the store.
 *
 * Returns false, and changes nothing, when the store holds fewer than the
 * requested quantity. That is the once-only guard a placement needs.
 */
export function removeStoreItem(
  map: Record<string, unknown> | undefined,
  itemId: number,
  quantity = 1,
): boolean {
  if (!Number.isInteger(itemId) || itemId <= 0) return false;
  const removed = Math.trunc(quantity);
  if (!Number.isFinite(removed) || removed <= 0) return false;

  if (map === undefined) return false;
  const raw = storeObject(map);
  if (raw === null) return false;
  const key = String(itemId);
  const current = quantityOf(raw[key]);
  if (current < removed) return false;

  const next = current - removed;
  if (next === 0) delete raw[key];
  else raw[key] = next;
  map['store'] = raw;
  return true;
}
