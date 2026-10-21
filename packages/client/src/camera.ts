/**
 * The camera.
 *
 * The client's camera is three numbers: where the map's origin is on the
 * screen (`topX`, `topY`) and the zoom. Everything else - the panning, the
 * zooming, the re-centring - follows from them.
 *
 * ## The panning
 *
 * From `core/Base.as:7021-7040`:
 *
 * ```as3
 * newTopX = topX + dx;
 * newTopY = topY + dy;
 * if ((dx < 0 && newTopX < EI_MIN_TOPX) || (dx > 0 && newTopX > EI_MAX_TOPX) ||
 *     (dy < 0 && newTopY < EI_MIN_TOPY) || (dy > 0 && newTopY > EI_MAX_TOPY)) {
 *   return;   // the whole pan is refused
 * }
 * ```
 *
 * Two details matter. The bounds are checked **in the direction of the
 * movement**, so the camera can be at a bound and still move away from it.
 * And the whole pan is refused, not clamped: the camera stops dead at
 * the edge rather than sliding along it.
 *
 * The camera's own origin moves by the **raw** delta, while the map's
 * contents move by the delta **divided by the zoom**. That is what makes
 * the map pan faster at a low zoom, exactly as the original does.
 *
 * ## The zooming
 *
 * Two different behaviours, and they are not the same:
 *
 * - the **mouse wheel** multiplies or divides by `ZOOM_STEP` (1.2)
 * - the **slider buttons** add or subtract 0.2
 *
 * Both are clamped to `[MIN_ZOOM, MAX_ZOOM]`.
 */
import type { Viewport } from './iso.ts';
import { TILE_HEIGHT_PIXELS } from './iso.ts';
import { STAGE_HEIGHT, STAGE_WIDTH } from './constants.ts';

/** The map's origin when the client opens. `Config.EI_INIT_POSX`. */
export const INIT_POS_X = -844;
/** The map's origin when the client opens. `Config.EI_INIT_POSY`. */
export const INIT_POS_Y = -2355;

/** How far the camera may pan left. `Config.EI_MIN_TOPX`. */
export const MIN_TOP_X = -7216;
/** How far the camera may pan right. `Config.EI_MAX_TOPX`. */
export const MAX_TOP_X = 7134;
/** How far the camera may pan up. `Config.EI_MIN_TOPY`. */
export const MIN_TOP_Y = -6479;
/** How far the camera may pan down. `Config.EI_MAX_TOPY`. */
export const MAX_TOP_Y = 871;

/** The smallest zoom. `Base.MIN_ZOOM`. */
export const MIN_ZOOM = 0.15;
/** The largest zoom. `Base.MAX_ZOOM`. */
export const MAX_ZOOM = 1.4;
/** The mouse wheel's multiplier. `Base.ZOOM_STEP`. */
export const ZOOM_STEP = 1.2;
/** The slider buttons' step. `GUI/ZoomSlider.as`. */
export const SLIDER_ZOOM_STEP = 0.2;

/** The camera's state. */
export interface CameraState {
  /** The map's origin on the screen. */
  topX: number;
  /** The map's origin on the screen. */
  topY: number;
  /** The zoom. */
  zoom: number;
}

/** The camera at its initial position. */
export function initialCamera(): CameraState {
  return { topX: INIT_POS_X, topY: INIT_POS_Y, zoom: 1 };
}

/** The result of a pan. */
export interface PanResult {
  /** The camera after the pan, or null when the pan was refused. */
  camera: CameraState | null;
  /** How far the map's CONTENTS moved, which is the delta divided by the zoom. */
  contentDelta: { dx: number; dy: number };
}

/**
 * Pan the camera.
 *
 * The pan is refused whole when it would take the camera past a bound in
 * the direction of the movement.
 */
export function pan(camera: CameraState, dx: number, dy: number): PanResult {
  if (dx === 0 && dy === 0) {
    return { camera, contentDelta: { dx: 0, dy: 0 } };
  }

  const newTopX = camera.topX + dx;
  const newTopY = camera.topY + dy;

  const pastX = (dx < 0 && newTopX < MIN_TOP_X) || (dx > 0 && newTopX > MAX_TOP_X);
  const pastY = (dy < 0 && newTopY < MIN_TOP_Y) || (dy > 0 && newTopY > MAX_TOP_Y);
  if (pastX || pastY) {
    return { camera: null, contentDelta: { dx: 0, dy: 0 } };
  }

  return {
    camera: { ...camera, topX: newTopX, topY: newTopY },
    contentDelta: { dx: dx / camera.zoom, dy: dy / camera.zoom },
  };
}

/** The result of a zoom. */
export interface ZoomResult {
  /** The camera after the zoom, or null when nothing changed. */
  camera: CameraState | null;
  /** The zoom, which is clamped even when nothing changed. */
  zoom: number;
}

/** The zoom after a wheel scroll in, clamped. */
export function wheelZoomIn(camera: CameraState): ZoomResult {
  if (camera.zoom >= MAX_ZOOM) return { camera: null, zoom: MAX_ZOOM };
  const next = Math.min(MAX_ZOOM, camera.zoom * ZOOM_STEP);
  return { camera: { ...camera, zoom: next }, zoom: next };
}

/** The zoom after a wheel scroll out, clamped. */
export function wheelZoomOut(camera: CameraState): ZoomResult {
  if (camera.zoom <= MIN_ZOOM) return { camera: null, zoom: MIN_ZOOM };
  const next = Math.max(MIN_ZOOM, camera.zoom / ZOOM_STEP);
  return { camera: { ...camera, zoom: next }, zoom: next };
}

/** The zoom after the slider's plus button, clamped. */
export function sliderZoomIn(camera: CameraState): ZoomResult {
  if (camera.zoom >= MAX_ZOOM) return { camera: null, zoom: MAX_ZOOM };
  const next = Math.min(MAX_ZOOM, camera.zoom + SLIDER_ZOOM_STEP);
  return { camera: { ...camera, zoom: next }, zoom: next };
}

/** The zoom after the slider's minus button, clamped. */
export function sliderZoomOut(camera: CameraState): ZoomResult {
  if (camera.zoom <= MIN_ZOOM) return { camera: null, zoom: MIN_ZOOM };
  const next = Math.max(MIN_ZOOM, camera.zoom - SLIDER_ZOOM_STEP);
  return { camera: { ...camera, zoom: next }, zoom: next };
}

/**
 * Re-centre the camera.
 *
 * The client does this when it loads a map and when it leaves an
 * assault (`core/Base.as:6928-6929`).
 */
export function recenter(camera: CameraState): CameraState {
  return { ...camera, topX: INIT_POS_X, topY: INIT_POS_Y };
}

/**
 * The build outline offset, which is the client's own default.
 *
 * `Base.Main.offsetBuildOutlineY` is 54, and the client's projection uses
 * `topY` less it.
 */
export const BUILD_OUTLINE_OFFSET_Y = 54;

/** The camera's viewport, for the projection. */
export function viewportOf(camera: CameraState): Viewport {
  return projectionViewport(camera, BUILD_OUTLINE_OFFSET_Y);
}

/**
 * The camera that centres a tile.
 *
 * The original opens on a **fixed** position (`Config.EI_INIT_POSX`),
 * which frames the original's starting town. The clone's town is
 * wherever the server put it, so the camera is **computed**: the tile's
 * top corner goes to the middle of the stage.
 *
 * The arithmetic is the projection's, inverted (`Utils.TileToPixel`):
 *
 * ```
 * x = topX - h*ty + h*tx
 * y = topY - offset + h/2*ty + h/2*tx - h/2
 * ```
 */
export function cameraCentredOn(
  tx: number,
  ty: number,
  stageWidth = STAGE_WIDTH,
  stageHeight = STAGE_HEIGHT,
): CameraState {
  const height = TILE_HEIGHT_PIXELS;
  const topX = stageWidth / 2 + height * (ty - tx);
  const topY =
    stageHeight / 2 +
    BUILD_OUTLINE_OFFSET_Y -
    (height / 2) * (tx + ty) +
    height / 2;
  return { topX, topY, zoom: 1 };
}

/**
 * The camera's state for the projection.
 *
 * The projection uses `topY` less the build outline offset
 * (`Base.offsetBuildOutlineY`, 54), which is the same number as the tile
 * height.
 */
export function projectionViewport(camera: CameraState, offsetBuildOutlineY: number): Viewport {
  return {
    topX: camera.topX,
    topY: camera.topY,
    buildOutlineOffsetY: offsetBuildOutlineY,
  };
}
