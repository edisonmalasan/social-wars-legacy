import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { STAGE_HEIGHT, STAGE_WIDTH } from './constants.ts';
import { MIN_READABLE_SCALE, stageLayout, stageScale } from './stage.ts';

describe('the stage', () => {
  it('is the client own size', () => {
    assert.equal(STAGE_WIDTH, 760);
    assert.equal(STAGE_HEIGHT, 600);
  });
});

describe('the stage scale', () => {
  it('is 1 when the window is big enough', () => {
    assert.equal(stageScale({ width: 800, height: 640 }), 1);
    assert.equal(stageScale({ width: 1920, height: 1080 }), 1);
  });

  it('shrinks to fit a window that is too small', () => {
    // Half the size: the stage is half as big.
    assert.equal(stageScale({ width: 380, height: 300 }), 0.5);
  });

  it('is limited by the narrower axis', () => {
    // Wide but short: the height decides.
    assert.equal(stageScale({ width: 2000, height: 300 }), 0.5);
  });

  it('is a whole number of hundredths, so the art stays sharp', () => {
    // 700 / 760 = 0.921..., which would blur the art.
    const scale = stageScale({ width: 700, height: 600 });
    assert.equal(scale, 0.92);
    assert.equal(Math.round(scale * 100) / 100, scale);
  });

  it('does not go below the readable scale', () => {
    // A very small window: the stage is floored, and the layout says the
    // text is too small rather than shipping unreadable text.
    const scale = stageScale({ width: 200, height: 150 });
    assert.equal(scale, MIN_READABLE_SCALE);
  });

  it('never goes above 1, because the layout is not fluid', () => {
    assert.equal(stageScale({ width: 4000, height: 3000 }), 1);
  });
});

describe('the stage layout', () => {
  it('centres the stage', () => {
    const layout = stageLayout({ width: 1000, height: 800 });
    assert.equal(layout.scale, 1);
    assert.equal(layout.x, (1000 - 760) / 2);
    assert.equal(layout.y, (800 - 600) / 2);
    assert.equal(layout.width, 760);
    assert.equal(layout.height, 600);
  });

  it('centres a scaled stage too', () => {
    const layout = stageLayout({ width: 380, height: 300 });
    assert.equal(layout.scale, 0.5);
    assert.equal(layout.width, 380);
    assert.equal(layout.height, 300);
    assert.equal(layout.x, 0);
    assert.equal(layout.y, 0);
  });

  it('knows when the window is in portrait', () => {
    assert.equal(stageLayout({ width: 400, height: 800 }).portrait, true);
    assert.equal(stageLayout({ width: 800, height: 400 }).portrait, false);
    assert.equal(stageLayout({ width: 800, height: 800 }).portrait, false);
  });

  it('says when the text is too small to read', () => {
    assert.equal(stageLayout({ width: 800, height: 600 }).tooSmall, false);
    assert.equal(stageLayout({ width: 200, height: 150 }).tooSmall, true);
  });
});
