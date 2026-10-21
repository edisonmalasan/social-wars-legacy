/**
 * A new player's world.
 *
 * A new player gets a **town**, not an empty map: the Command Center
 * stands at the middle of the map, and the rest of the town is the
 * player's to build.
 *
 * ## Why the Command Center and not the original's whole town
 *
 * The original's starting town also has a ring of walls and a pair of
 * turrets. This is a **known difference**, and it is deliberate: the
 * original's layout is a fact about the game that is only recorded in
 * the vendored upstream, which is GPL v3, and the shipped product does
 * not carry GPL data. So the clone starts with the one building every
 * town has — the Command Center, which is the content bundle's item
 * **26** — and the perimeter is the player's to build, from the same
 * store the original used.
 *
 * ## The tuple
 *
 * The item tuple is the **upstream's** shape, because the legacy client
 * and the legacy shim both speak it:
 *
 * `[itemId, x, y, timestamp, orientation, store, attrs, owner]`
 */
import type { MapItemTuple } from './apply.ts';
import type { ShimWorld } from './shim.ts';

/**
 * The content's id for the Command Center.
 *
 * It is the building that grants the population and that every town
 * has. The content bundle is the authority for it — the id **26** is
 * the bundle's own, and the bundle is the game's configuration.
 */
export const COMMAND_CENTER_ITEM_ID = 26;

/** The map's size, in tiles. The map is 100 by 100. */
export const MAP_SIZE = 100;

/**
 * Where the Command Center stands.
 *
 * The middle of the map, so that the town has room around it in every
 * direction.
 */
export const COMMAND_CENTER_TILE = {
  x: Math.floor(MAP_SIZE / 2) - 2,
  y: Math.floor(MAP_SIZE / 2) - 2,
};

/**
 * The starting town.
 *
 * The Command Center's attribute bag, which the server's own rules
 * read: the size, what it holds and when it was last collected.
 */
function commandCenterAttrs(): Record<string, unknown> {
  return {
    width: 4,
    height: 4,
    collect: 0,
    unitCapacity: 0,
    unitsInside: 0,
    collectType: '',
    cp: 1,
    lastAccruedAt: 0,
    clicked: 0,
  };
}

/** The items a new player's map holds. */
export function startingTown(): Record<string, MapItemTuple> {
  const tuple: MapItemTuple = [
    COMMAND_CENTER_ITEM_ID,
    COMMAND_CENTER_TILE.x,
    COMMAND_CENTER_TILE.y,
    0,
    0,
    [],
    commandCenterAttrs(),
    1,
  ];
  return { '1': tuple };
}

/**
 * A new player's world.
 *
 * The same shape the development player gets: a town, the starting
 * resources, and the command counter at the beginning.
 */
export function initialWorld(playerId: string): ShimWorld {
  return {
    save: {
      playerInfo: { pid: playerId, name: playerId },
      maps: [{ id: 0, items: startingTown() }],
      privateState: {},
    },
    resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}
