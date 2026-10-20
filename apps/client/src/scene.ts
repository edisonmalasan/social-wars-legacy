/**
 * The scene.
 *
 * The scene is what the renderer draws: every item on the map, where it
 * goes on the screen, how deep it is and which piece of art it uses.
 *
 * It is **pure**, and separate from the drawing, for two reasons. The
 * drawing needs a GPU, and a scene does not - so the scene can be
 * **tested** without one. And the scene is where the rules live: the
 * projection, the depth sort and the frame choice are the client's
 * behaviour, and they are easier to check as numbers than as pixels.
 *
 * ## The server's positions
 *
 * The item's tile comes from the **server's** save, not from the
 * client's guess: the server owns the world, and the client draws it.
 * The scene takes the tile as it is given and never invents one.
 */
import {
  animationFrame,
  type AnimationFrame,
} from '@swl/client';
import { tileToPixel, zIndex, type Viewport } from '@swl/client';
import type { AtlasIndex, FrameLocation } from '@swl/client';

/** An item on the map, as the scene sees it. */
export interface SceneItem {
  /** The item's reference id. */
  id: string;
  /** The tile x. */
  tx: number;
  /** The tile y. */
  ty: number;
  /** The item's width, in tiles. */
  width: number;
  /** Whether the item is walkable, so that it goes under the buildings. */
  walkable: boolean;
  /** The item's elevation, in pixels. */
  elevation: number;
  /** The SWF the art is in. */
  swf: string;
  /** The symbol within that SWF. */
  symbol: string;
  /** The orientation, for the frame choice. */
  orientation: number;
  /** The animation, for the frame choice. */
  animation: number;
}

/** One thing to draw. */
export interface SceneSprite {
  /** The item's reference id. */
  id: string;
  /** The screen x, of the item's **top corner**. */
  x: number;
  /** The screen y, of the item's top corner. */
  y: number;
  /** The depth: the sort key. */
  depth: number;
  /** Where the art is. */
  art: FrameLocation | null;
  /** The frame the art is for. */
  frame: AnimationFrame | null;
  /** The elevation, in pixels, which lifts the art off the ground. */
  elevation: number;
}

/**
 * The scene for a set of items.
 *
 * The items are sorted by their **depth**, which is the client's own
 * `Utils.assignZIndex`, so the renderer draws them back to front.
 */
export function buildScene(
  items: readonly SceneItem[],
  viewport: Viewport,
  atlas: AtlasIndex,
): SceneSprite[] {
  const sprites: SceneSprite[] = [];

  for (const item of items) {
    const position = tileToPixel(item.tx, item.ty, viewport);
    const depth = zIndex(item.tx, item.ty, item.width, item.walkable);
    const frame = animationFrame(item.animation, item.orientation);
    const art = atlas.lookup(item.swf, item.symbol, frame.frame);

    sprites.push({
      id: item.id,
      // The projection puts the item's **top corner** on the screen, which
      // is the client's own convention: its inverse projection is
      // calibrated to the top corner and not to the centre of the tile.
      x: position.x,
      y: position.y,
      depth,
      art,
      frame,
      elevation: item.elevation,
    });
  }

  // The depth sort, and it is stable, so two items at the same depth
  // keep the order they came in - or they would flicker.
  return sprites
    .map((sprite, index) => ({ sprite, index }))
    .sort((a, b) => a.sprite.depth - b.sprite.depth || a.index - b.index)
    .map(({ sprite }) => sprite);
}
