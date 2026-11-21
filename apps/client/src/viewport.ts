/**
 * Fitting the fixed stage to the real window.
 *
 * The `#stage` element is 760x600 by design, so its own `clientWidth` and
 * `clientHeight` describe the **stage**, not the window. Fitting to them gives
 * a scale of 1 at every viewport, which is why the stage model was tested but
 * never actually driven by the window. The window's own size is what the game
 * has to fit into, and that is what is used here.
 *
 * This is a small pure seam so the choice is testable without a browser: the
 * renderer only needs to apply the resulting scale to the element.
 */
import { stageLayout, type StageLayout, type ViewportSize } from '@swl/client';

/** The stage element's own metrics, which are fixed at 760x600. */
export interface StageElementSize {
  readonly clientWidth: number;
  readonly clientHeight: number;
}

/**
 * The size to fit the stage to.
 *
 * A real browser always reports a positive window size. The element is only
 * a fallback for the odd case where the window reports nothing at all.
 */
export function fitViewport(
  stage: StageElementSize,
  window: ViewportSize,
): ViewportSize {
  if (window.width > 0 && window.height > 0) {
    return { width: window.width, height: window.height };
  }
  return { width: stage.clientWidth, height: stage.clientHeight };
}

/** The stage layout for the real window, rather than the fixed element. */
export function fitStage(stage: StageElementSize, window: ViewportSize): StageLayout {
  return stageLayout(fitViewport(stage, window));
}
