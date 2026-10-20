/**
 * The isometric projection and the depth sort.
 *
 * These are the two pieces of the original engine that every other piece
 * depends on: where a tile is on the screen, and what is drawn in front of
 * what. Both are ported **exactly**, because a client that draws the map
 * even slightly differently is a client that does not look like the game.
 *
 * ## The projection
 *
 * From `core/Utils.as:88-102`:
 *
 * ```as3
 * _loc3_ = _loc5_ - _loc7_ * param2 + _loc7_ * param1;
 * _loc4_ = _loc6_ + _loc7_ * 0.5 * param2 + _loc7_ * 0.5 * param1;
 * return { x: _loc3_, y: _loc4_ - 27 };
 * ```
 *
 * with `_loc5_` the map's left edge, `_loc6_` the map's top edge less the
 * build-outline offset, and `_loc7_` the tile height in pixels.
 *
 * The `- 27` is half a tile: it moves the origin from the tile's *centre*
 * to its top corner, so a building's art hangs below the point it stands
 * on.
 *
 * ## The depth sort
 *
 * From `core/Utils.as:395-407`:
 *
 * ```as3
 * _loc2_ = 20000 + Config.EI_MAP_WIDTH * param1.tx + param1.ty * Config.EI_MAP_WIDTH
 *          - param1.building.width * Config.EI_MAP_WIDTH;
 * if (the building is walkable) _loc2_ -= 20000;
 * ```
 *
 * Two details matter and are easy to lose:
 *
 * - the building's own **width** shifts it back, so a wide building's art
 *   is drawn behind a narrow one further up the map;
 * - a **walkable** building - a road or a plaza - goes 20 000 *behind*
 *   everything else, so the paths are always under the buildings standing
 *   on them.
 */

/** The width of a tile's diamond, in pixels. `Config.EI_TILE_WIDTH_PIXELS`. */
export const TILE_WIDTH_PIXELS = 108;

/** The height of a tile's diamond, in pixels. `Config.EI_TILE_HEIGHT_PIXELS`. */
export const TILE_HEIGHT_PIXELS = 54;

/** The map's width, in tiles. `Config.EI_MAP_WIDTH`. */
export const MAP_WIDTH = 100;

/** The map's height, in tiles. `Config.EI_MAP_HEIGHT`. */
export const MAP_HEIGHT = 100;

/** The property that makes a building walkable. `PropertyManager.WALKABLE`. */
export const WALKABLE_PROPERTY = 'walkable';

/**
 * The offset the walkable buildings are pushed behind everything else.
 *
 * It is large enough that no ordinary z-index can cancel it, and small
 * enough that it cannot overflow a 32-bit integer over the map's range.
 */
export const WALKABLE_OFFSET = 20_000;

/** Where the map's origin is on the screen. */
export interface Viewport {
  /** The screen x of the map's left edge. `Base.Main.topX`. */
  topX: number;
  /** The screen y of the map's top edge, less the build outline offset. */
  topY: number;
}

/** A position on the map, in tiles. */
export interface TilePosition {
  tx: number;
  ty: number;
}

/** A position on the screen, in pixels. */
export interface ScreenPosition {
  x: number;
  y: number;
}

/**
 * Where a tile is on the screen.
 *
 * Ported from `Utils.TileToPixel` (core/Utils.as:88-102).
 */
export function tileToPixel(tx: number, ty: number, viewport: Viewport): ScreenPosition {
  const height = TILE_HEIGHT_PIXELS;
  return {
    x: viewport.topX - height * ty + height * tx,
    y:
      viewport.topY +
      height * 0.5 * ty +
      height * 0.5 * tx -
      TILE_HEIGHT_PIXELS / 2,
  };
}

/**
 * Which tile a screen position is over.
 *
 * Ported from `Utils.PixelToTile` (core/Utils.as:73-87). The client's
 * version returns fractional tile coordinates unless the third argument
 * asks for whole ones; this always returns whole tiles, which is what a
 * pointer event needs.
 *
 * **The two functions are only inverses of each other at a tile's top
 * corner**, which is what `tileToPixel` returns. Given the *centre* of a
 * tile's diamond, the client's formula answers the tile one step further
 * along on both axes. That is the client's own behaviour, and it is why
 * the client's own unit code passes a unit's top-corner position
 * (core/isoengine/IsoUnit.as:914).
 */
export function pixelToTile(x: number, y: number, viewport: Viewport): TilePosition {
  const height = TILE_HEIGHT_PIXELS;
  const diagonal = (2 * (y - viewport.topY) - x + viewport.topX) / (2 * height);
  return {
    tx: Math.floor((x - viewport.topX + height * diagonal) / height + 1),
    ty: Math.floor(diagonal + 1),
  };
}

/**
 * The depth of an element on the map.
 *
 * Ported from `Utils.assignZIndex` (core/Utils.as:395-407).
 *
 * @param tx the element's tile x
 * @param ty the element's tile y
 * @param width the element's width **in tiles** - the content's `width`
 * @param walkable whether the element is walkable, so that it belongs under
 *   everything else
 */
export function zIndex(tx: number, ty: number, width: number, walkable: boolean): number {
  let index =
    WALKABLE_OFFSET +
    MAP_WIDTH * tx +
    ty * MAP_WIDTH -
    width * MAP_WIDTH;
  if (walkable) {
    index -= WALKABLE_OFFSET;
  }
  return index;
}

/** Something that can be drawn, and therefore ordered. */
export interface Drawable {
  /** The element's tile x. */
  tx: number;
  /** The element's tile y. */
  ty: number;
  /** The element's width in tiles. */
  width: number;
  /** Whether the element is walkable. */
  walkable: boolean;
}

/**
 * The depth of a drawable.
 */
export function depthOf(drawable: Drawable): number {
  return zIndex(drawable.tx, drawable.ty, drawable.width, drawable.walkable);
}

/**
 * Compare two drawables by depth.
 *
 * The client sorts the building array by `zIndex` ascending
 * (core/Base.as:2657, core/Base.as:6108, core/isoengine/IsoUnit.as:1318),
 * so a larger z-index is drawn *later* and therefore in front.
 *
 * The sort must be **stable** for equal depths, or the order of two
 * overlapping elements would change between frames and they would flicker.
 * `Array.prototype.sort` is stable in every modern engine, and so is
 * `Array.prototype.sort` in JavaScript, so a plain comparison is enough.
 */
export function compareDepth(a: Drawable, b: Drawable): number {
  return depthOf(a) - depthOf(b);
}

/**
 * Sort a list of drawables into drawing order.
 *
 * The list is not modified: the caller decides whether to keep the copy.
 */
export function sortByDepth<T extends Drawable>(drawables: readonly T[]): T[] {
  return [...drawables].sort(compareDepth);
}

/**
 * Whether a tile is on the map.
 *
 * The map is 100 by 100, and the client never draws outside it.
 */
export function isOnMap(tx: number, ty: number): boolean {
  return tx >= 0 && tx < MAP_WIDTH && ty >= 0 && ty < MAP_HEIGHT;
}
