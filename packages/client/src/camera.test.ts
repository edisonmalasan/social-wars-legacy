import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  INIT_POS_X,
  INIT_POS_Y,
  MAX_TOP_X,
  MAX_TOP_Y,
  MAX_ZOOM,
  MIN_TOP_X,
  MIN_TOP_Y,
  MIN_ZOOM,
  SLIDER_ZOOM_STEP,
  ZOOM_STEP,
  initialCamera,
  pan,
  projectionViewport,
  recenter,
  sliderZoomIn,
  sliderZoomOut,
  viewportOf,
  wheelZoomIn,
  wheelZoomOut,
} from './camera.ts';

describe('the camera constants', () => {
  it('are the client own', () => {
    // Config.EI_INIT_POSX/Y, EI_MIN/MAX_TOPX/Y, Base.MIN/MAX_ZOOM,
    // Base.ZOOM_STEP, GUI/ZoomSlider's step.
    assert.equal(INIT_POS_X, -844);
    assert.equal(INIT_POS_Y, -2355);
    assert.equal(MIN_TOP_X, -7216);
    assert.equal(MAX_TOP_X, 7134);
    assert.equal(MIN_TOP_Y, -6479);
    assert.equal(MAX_TOP_Y, 871);
    assert.equal(MIN_ZOOM, 0.15);
    assert.equal(MAX_ZOOM, 1.4);
    assert.equal(ZOOM_STEP, 1.2);
    assert.equal(SLIDER_ZOOM_STEP, 0.2);
  });
});

describe('the camera at rest', () => {
  it('starts at the initial position', () => {
    const camera = initialCamera();
    assert.equal(camera.topX, INIT_POS_X);
    assert.equal(camera.topY, INIT_POS_Y);
    assert.equal(camera.zoom, 1);
  });

  it('re-centres on demand', () => {
    const moved = { topX: 100, topY: 200, zoom: 0.5 };
    const centred = recenter(moved);
    assert.equal(centred.topX, INIT_POS_X);
    assert.equal(centred.topY, INIT_POS_Y);
    // The zoom is not touched.
    assert.equal(centred.zoom, 0.5);
  });
});

describe('panning', () => {
  it('moves the camera by the raw delta', () => {
    const camera = initialCamera();
    const result = pan(camera, 100, 50);
    assert.ok(result.camera);
    assert.equal(result.camera.topX, INIT_POS_X + 100);
    assert.equal(result.camera.topY, INIT_POS_Y + 50);
  });

  it('moves the contents by the delta divided by the zoom', () => {
    const camera = { topX: 0, topY: 0, zoom: 2 };
    const result = pan(camera, 100, 50);
    assert.deepEqual(result.contentDelta, { dx: 50, dy: 25 });
  });

  it('refuses the WHOLE pan when it would pass a bound', () => {
    const atTheLeftEdge = { topX: MIN_TOP_X, topY: 0, zoom: 1 };
    const result = pan(atTheLeftEdge, -100, 0);
    assert.equal(result.camera, null);
    assert.deepEqual(result.contentDelta, { dx: 0, dy: 0 });
  });

  it('allows a move away from a bound', () => {
    const atTheLeftEdge = { topX: MIN_TOP_X, topY: 0, zoom: 1 };
    const result = pan(atTheLeftEdge, 100, 0);
    assert.ok(result.camera);
    assert.equal(result.camera.topX, MIN_TOP_X + 100);
  });

  it('refuses a pan past the right edge', () => {
    const camera = { topX: MAX_TOP_X, topY: 0, zoom: 1 };
    assert.equal(pan(camera, 100, 0).camera, null);
  });

  it('refuses a pan past the top edge', () => {
    const camera = { topX: 0, topY: MIN_TOP_Y, zoom: 1 };
    assert.equal(pan(camera, 0, -100).camera, null);
  });

  it('refuses a pan past the bottom edge', () => {
    const camera = { topX: 0, topY: MAX_TOP_Y, zoom: 1 };
    assert.equal(pan(camera, 0, 100).camera, null);
  });

  it('does nothing for a zero delta', () => {
    const camera = initialCamera();
    const result = pan(camera, 0, 0);
    assert.equal(result.camera, camera);
  });
});

describe('the mouse wheel zoom', () => {
  it('multiplies by the step', () => {
    const result = wheelZoomIn(initialCamera());
    assert.equal(result.zoom, ZOOM_STEP);
  });

  it('divides by the step', () => {
    const result = wheelZoomOut({ ...initialCamera(), zoom: 1.2 });
    assert.ok(Math.abs(result.zoom - 1) < 1e-9);
  });

  it('clamps at the top', () => {
    const result = wheelZoomIn({ ...initialCamera(), zoom: MAX_ZOOM });
    assert.equal(result.zoom, MAX_ZOOM);
    assert.equal(result.camera, null);
  });

  it('clamps at the bottom', () => {
    const result = wheelZoomOut({ ...initialCamera(), zoom: MIN_ZOOM });
    assert.equal(result.zoom, MIN_ZOOM);
    assert.equal(result.camera, null);
  });

  it('does not go past the top when zooming in', () => {
    const result = wheelZoomIn({ ...initialCamera(), zoom: 1.3 });
    assert.equal(result.zoom, MAX_ZOOM);
  });

  it('does not go past the bottom when zooming out', () => {
    const result = wheelZoomOut({ ...initialCamera(), zoom: 0.16 });
    assert.equal(result.zoom, MIN_ZOOM);
  });
});

describe('the slider zoom', () => {
  it('adds and subtracts a fifth', () => {
    assert.equal(sliderZoomIn(initialCamera()).zoom, 1 + SLIDER_ZOOM_STEP);
    assert.equal(sliderZoomOut(initialCamera()).zoom, 1 - SLIDER_ZOOM_STEP);
  });

  it('is not the same as the wheel', () => {
    // The wheel multiplies; the slider adds. They are different
    // behaviours, and the client has both. They happen to agree at a zoom
    // of 1, which is why the test uses another one.
    assert.equal(sliderZoomIn({ ...initialCamera(), zoom: 0.5 }).zoom, 0.7);
    assert.equal(wheelZoomIn({ ...initialCamera(), zoom: 0.5 }).zoom, 0.6);
  });

  it('clamps at both ends', () => {
    assert.equal(sliderZoomIn({ ...initialCamera(), zoom: MAX_ZOOM }).zoom, MAX_ZOOM);
    assert.equal(sliderZoomOut({ ...initialCamera(), zoom: MIN_ZOOM }).zoom, MIN_ZOOM);
  });
});

describe('the camera viewport', () => {
  it('is the camera position', () => {
    const camera = initialCamera();
    assert.deepEqual(viewportOf(camera), {
      topX: INIT_POS_X,
      topY: INIT_POS_Y,
      buildOutlineOffsetY: 54,
    });
  });

  it('takes the build outline offset off for the projection', () => {
    const camera = { topX: 100, topY: 200, zoom: 1 };
    assert.deepEqual(projectionViewport(camera, 54), {
      topX: 100,
      topY: 200,
      buildOutlineOffsetY: 54,
    });
  });
});
