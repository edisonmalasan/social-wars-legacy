/**
 * The stage's layout.
 *
 * The game was built for a **760 by 600** stage, and its layout is not
 * fluid: the panels are at fixed positions, and reflowing them would put
 * them on top of each other. So the stage keeps its size and is
 * **scaled** to fit the window.
 *
 * That is the same decision the desktop shell makes, and the same one
 * the client's own `TutorialMain` records: `PRIOR_STAGE_WIDTH` and
 * `PRIOR_STAGE_HEIGHT` are 760 and 600.
 *
 * ## The scale
 *
 * The scale is the largest that fits, **capped** so that the text stays
 * readable. A phone in portrait is narrower than the stage, so the scale
 * goes below 1 — and below a certain point the text is too small to
 * read, which is worth saying rather than discovering.
 *
 * The scale is a **whole number** where it can be, so the pixel art
 * stays sharp. A fractional scale on pixel art is blurred art.
 */
import { STAGE_HEIGHT, STAGE_WIDTH } from './constants.ts';

/** The scale below which the text is too small to read. */
export const MIN_READABLE_SCALE = 0.5;

/** The window's size, in pixels. */
export interface ViewportSize {
  width: number;
  height: number;
}

/** How the stage sits in the window. */
export interface StageLayout {
  /** The scale the stage is drawn at. */
  scale: number;
  /** The stage's left edge, in the window's pixels. */
  x: number;
  /** The stage's top edge, in the window's pixels. */
  y: number;
  /** The stage's width, in the window's pixels. */
  width: number;
  /** The stage's height, in the window's pixels. */
  height: number;
  /** Whether the window is in portrait. */
  portrait: boolean;
  /**
   * Whether the text is too small to read at this scale.
   *
   * It is better to say so than to ship a game nobody can read.
   */
  tooSmall: boolean;
}

/**
 * The scale the stage is drawn at.
 *
 * The largest that fits, capped at 1 — a bigger window does not make
 * the game bigger, because the layout is not fluid — and floored at the
 * readable scale.
 */
export function stageScale(size: ViewportSize): number {
  const fits = Math.min(size.width / STAGE_WIDTH, size.height / STAGE_HEIGHT);
  const scale = Math.min(1, Math.max(MIN_READABLE_SCALE, fits));
  // A whole number where it can be, so the pixel art stays sharp.
  return Math.floor(scale * 100) / 100;
}

/** How the stage sits in the window. */
export function stageLayout(size: ViewportSize): StageLayout {
  const scale = stageScale(size);
  const width = STAGE_WIDTH * scale;
  const height = STAGE_HEIGHT * scale;
  // Whether the text is too small is judged on the scale that **fits**,
  // not on the one that is used: the used scale is floored, so asking
  // about it would never find anything.
  const fits = Math.min(size.width / STAGE_WIDTH, size.height / STAGE_HEIGHT);
  return {
    scale,
    x: Math.round((size.width - width) / 2),
    y: Math.round((size.height - height) / 2),
    width,
    height,
    portrait: size.height > size.width,
    tooSmall: fits < MIN_READABLE_SCALE,
  };
}
