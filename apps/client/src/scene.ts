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
import {
  tileToPixel,
  zIndex,
  MAP_HEIGHT,
  MAP_WIDTH,
  STAGE_HEIGHT,
  STAGE_WIDTH,
  type Viewport,
} from '@swl/client';
import type { AtlasIndex, FrameLocation } from '@swl/client';

/** An item on the map, as the scene sees it. */
export interface SceneItem {
  /** The item's reference id. */
  id: string;
  /** The content item's id, for the art. */
  itemId?: number;
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
  /** The orientation, for the frame choice. */
  orientation: number;
  /** The animation, for the frame choice. */
  animation: number;
  /**
   * Neutral content properties, used **only** to choose gameplay art.
   *
   * These come from the content definition: the item's type, its group and
   * its numeric category/subcategory. They are the only properties allowed
   * to select a gameplay motif. Art-derived names — an image name, an SWF
   * symbol, an atlas frame or region — never take part in that choice.
   */
  type?: string;
  groupType?: string;
  categoryId?: number;
  subcategoryId?: number;
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
  /**
   * Neutral content properties, carried from the item so the renderer can
   * choose a gameplay motif. Art-derived names are deliberately absent.
   */
  type?: string;
  groupType?: string;
  categoryId?: number;
  subcategoryId?: number;
}

/**
 * The original game's field colour. The reference sets `bgcolor="#669C2C"`
 * (`play.html`), and green dominates the other two channels. The renderer
 * clears Pixi's background to this, so even the stage edges that no whole
 * tile's top corner reaches still read as green field.
 */
export const GROUND_COLOUR = '#669C2C';

/** A ground tile sits behind every item sprite. */
const GROUND_DEPTH = -1;

/**
 * The deterministic isometric ground layer.
 *
 * The tiles are bounded by the **server-owned map dimensions** (`MAP_WIDTH`
 * and `MAP_HEIGHT`, the client's mirror of `Config.EI_MAP_WIDTH/HEIGHT`) and
 * placed with the very same `tileToPixel()` projection the items use. The
 * viewport is derived from the camera, which the client centres on the
 * server's world, so the field follows the player's town without the client
 * inventing any gameplay. Only tiles whose projected top corner lands inside
 * the fixed stage are emitted; the result is a pure function of the viewport.
 */
export function buildGround(viewport: Viewport): SceneSprite[] {
  const ground: SceneSprite[] = [];
  const seen = new Set<string>();

  for (let tx = 0; tx < MAP_WIDTH; tx += 1) {
    for (let ty = 0; ty < MAP_HEIGHT; ty += 1) {
      const { x, y } = tileToPixel(tx, ty, viewport);
      if (x < 0 || x >= STAGE_WIDTH || y < 0 || y >= STAGE_HEIGHT) continue;
      const key = `${x},${y}`;
      if (seen.has(key)) continue;
      seen.add(key);
      ground.push({
        id: `ground:${tx}:${ty}`,
        x,
        y,
        depth: GROUND_DEPTH,
        art: null,
        frame: null,
        elevation: 0,
      });
    }
  }

  return ground;
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

    // The art comes from the manifest's **item** map, which names the
    // SWF and the symbol within it. The content's item gives the image's
    // name and the id, and the manifest resolves them - so the client
    // does not have to guess the SWF's group or the symbol's name.
    const art = item.itemId
      ? (() => {
          const entry = atlas.itemArt(item.itemId);
          if (!entry) return null;
          // The manifest's frames are **one-based**, and the client
          // picks the drawing with `gotoAndStop(frame + 1)`, so the
          // lookup is one higher than the frame the animation chose.
          return atlas.lookup(entry.swf, entry.symbol, frame.frame + 1);
        })()
      : null;

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
      // The neutral content properties travel with the sprite unchanged. The
      // renderer passes them to the art adapter, which is the only place a
      // gameplay motif is chosen; art-derived fields are not copied here.
      type: item.type,
      groupType: item.groupType,
      categoryId: item.categoryId,
      subcategoryId: item.subcategoryId,
    });
  }

  // The depth sort, and it is stable, so two items at the same depth
  // keep the order they came in - or they would flicker.
  return sprites
    .map((sprite, index) => ({ sprite, index }))
    .sort((a, b) => a.sprite.depth - b.sprite.depth || a.index - b.index)
    .map(({ sprite }) => sprite);
}
