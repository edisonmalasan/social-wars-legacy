import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { fitStage, fitViewport } from './viewport.ts';

/**
 * The `#stage` element is fixed at 760x600 by the stylesheet, so its own
 * clientWidth/clientHeight describe the stage, not the window. These are the
 * numbers the old `renderer.fit()` read — which is why its scale was always 1.
 */
const STAGE = { clientWidth: 760, clientHeight: 600 };

describe('fitting the stage to the real viewport', () => {
  it('uses the window, not the fixed 760x600 stage element', () => {
    // With a 390x844 window the stage must scale to 0.51. Reading the
    // element's 760 clientWidth would instead give a scale of 1.
    assert.deepEqual(fitViewport(STAGE, { width: 390, height: 844 }), {
      width: 390,
      height: 844,
    });
    assert.equal(fitStage(STAGE, { width: 390, height: 844 }).scale, 0.51);
    assert.equal(fitStage(STAGE, { width: 360, height: 640 }).scale, 0.5);
    assert.equal(fitStage(STAGE, { width: 640, height: 360 }).scale, 0.6);
  });

  it('keeps the desktop 760x600 window at scale 1', () => {
    const layout = fitStage(STAGE, { width: 760, height: 600 });
    assert.equal(layout.scale, 1);
    assert.equal(layout.x, 0);
    assert.equal(layout.y, 0);
    assert.equal(layout.width, 760);
    assert.equal(layout.height, 600);
  });

  it('reports portrait and unreadable text from the real window', () => {
    const portrait = fitStage(STAGE, { width: 360, height: 640 });
    assert.equal(portrait.portrait, true);
    assert.equal(portrait.tooSmall, true);
    assert.equal(fitStage(STAGE, { width: 640, height: 360 }).portrait, false);
  });

  it('falls back to the element only when the window reports no size', () => {
    assert.deepEqual(fitViewport(STAGE, { width: 0, height: 0 }), { width: 760, height: 600 });
  });
});
