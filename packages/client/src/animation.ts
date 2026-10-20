/**
 * The unit animation.
 *
 * A sprite's frame index is **not** a timeline: the client picks the frame
 * by number, out of a sheet that holds every drawing of every state.
 *
 * ## The frame number
 *
 * From `core/isoengine/IsoUnit.as:1414-1445`:
 *
 * ```as3
 * frame = this.iAnimation * 5 + frameDirection;
 * this.ghostBuilding.gotoAndStop(frame);
 * ```
 *
 * So the sheet is laid out in blocks of **five** frames per animation
 * state, and the direction picks the frame within the block. There are
 * eight directions and five slots, so the block has a spare slot.
 *
 * ## The mirroring
 *
 * ```as3
 * if (this.currentDirection > 5) {
 *   frameDirection -= 4;
 *   newScale = -1;
 * }
 * ```
 *
 * The three LEFT-facing directions (6, 7 and 8) are the right-facing
 * ones (2, 3 and 4) drawn **mirrored**, so the client flips the sprite
 * horizontally instead of drawing a second copy. That is why there are
 * only five slots and eight directions.
 *
 * ## The idle
 *
 * An idle unit does not sit on one frame: the client picks a **random**
 * frame of the idle's sub-clip and plays it.
 *
 * ```as3
 * subclip.gotoAndPlay(int(Math.random() * subclip.totalFrames));
 * ```
 *
 * The randomness is the client's, and a server-authoritative clone has to
 * make the same choice - so the random source is a parameter here, not a
 * call to `Math.random`.
 */

/** The animation states. `Constants.ANIMATION_*`. */
export const ANIMATION = {
  IDLE: 0,
  WALKING: 1,
  ATTACKING: 2,
  DYING: 3,
  HARVESTING: 4,
  /** The repairing, the strike and the oil-harvesting all share a slot. */
  REPAIRING: 5,
  ATTACKING_SPECIAL1: 6,
  ATTACKING_SPECIAL2: 7,
  ATTACKING_SPECIAL3: 8,
  ATTACKING_SPECIAL4: 9,
  ATTACKING_SPECIAL5: 10,
  ATTACKING_SPECIAL6: 11,
  ATTACKING_SPECIAL7: 12,
  ATTACKING_SPECIAL8: 13,
} as const;

/** The eight directions. `Constants.ORIENTATION_*`. */
export const ORIENTATION = {
  UP: 1,
  UP_RIGHT: 2,
  RIGHT: 3,
  DOWN_RIGHT: 4,
  DOWN: 5,
  UP_LEFT: 6,
  LEFT: 7,
  DOWN_LEFT: 8,
} as const;

/** How many frames each animation's block holds. */
export const FRAMES_PER_ANIMATION = 5;

/** The frame a state and a direction pick. */
export interface AnimationFrame {
  /** The frame number in the sprite's sheet. */
  frame: number;
  /** Whether the sprite has to be flipped horizontally. */
  mirrored: boolean;
}

/**
 * The frame for an animation state and a direction.
 *
 * The three LEFT-facing directions are the right-facing ones mirrored.
 */
export function animationFrame(animation: number, orientation: number): AnimationFrame {
  let frameDirection = orientation;
  let mirrored = false;
  if (orientation > 5) {
    frameDirection -= 4;
    mirrored = true;
  }
  return { frame: animation * FRAMES_PER_ANIMATION + frameDirection, mirrored };
}

/**
 * The frame an idle unit shows.
 *
 * The client picks a random frame of the idle's sub-clip, so the idle
 * varies from moment to moment. The random source is a parameter, so a
 * server-authoritative clone can make the same choice deterministically.
 */
export function idleFrame(random: () => number, totalFrames: number): number {
  if (totalFrames <= 0) return 0;
  const index = Math.floor(random() * totalFrames);
  return index < 0 ? 0 : index >= totalFrames ? totalFrames - 1 : index;
}

/**
 * The direction a unit is facing, from the movement.
 *
 * From `core/isoengine/IsoUnit.as:1380-1410`: the direction is chosen
 * from the sign of the movement on each axis, and a unit that is not
 * moving keeps the direction it had.
 */
export function directionFrom(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  current: number,
): number {
  if (fromX < toX) {
    if (fromY < toY) return ORIENTATION.DOWN_RIGHT;
    if (fromY > toY) return ORIENTATION.UP_RIGHT;
    return ORIENTATION.RIGHT;
  }
  if (fromX > toX) {
    if (fromY < toY) return ORIENTATION.DOWN_LEFT;
    if (fromY > toY) return ORIENTATION.UP_LEFT;
    return ORIENTATION.LEFT;
  }
  if (fromY < toY) return ORIENTATION.DOWN;
  if (fromY > toY) return ORIENTATION.UP;
  return current;
}
