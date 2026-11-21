import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { DOUBLE_TAP_MS, TAP_SLOP_PX, TouchGestureGuard } from './touch.ts';
import { uiCss } from './ui/css.ts';

const P = (x: number, y: number) => ({ x, y });

describe('the touch gesture guard', () => {
  it('fires exactly one command for a single tap', () => {
    const guard = new TouchGestureGuard();
    guard.down(1, P(100, 100));
    assert.equal(guard.up(1, 1050, P(100, 100)), true);
  });

  it('suppresses the second tap of a double tap', () => {
    const guard = new TouchGestureGuard();
    guard.down(1, P(100, 100));
    assert.equal(guard.up(1, 1020, P(100, 100)), true);
    guard.down(2, P(101, 100));
    assert.equal(guard.up(2, 1120, P(101, 100)), false);
  });

  it('accepts a later tap once the double-tap window has passed', () => {
    const guard = new TouchGestureGuard();
    guard.down(1, P(100, 100));
    assert.equal(guard.up(1, 1020, P(100, 100)), true);
    const later = 1000 + DOUBLE_TAP_MS + 1;
    guard.down(2, P(100, 100));
    assert.equal(guard.up(2, later + 20, P(100, 100)), true);
  });

  it('accepts two quick taps at different places', () => {
    const guard = new TouchGestureGuard();
    guard.down(1, P(100, 100));
    assert.equal(guard.up(1, 1020, P(100, 100)), true);
    guard.down(2, P(400, 300));
    assert.equal(guard.up(2, 1120, P(400, 300)), true);
  });

  it('fires nothing for a pinch and recovers for the next single tap', () => {
    const guard = new TouchGestureGuard();
    guard.down(1, P(100, 100));
    guard.down(2, P(200, 100));
    assert.equal(guard.up(1, 1040, P(100, 100)), false);
    assert.equal(guard.up(2, 1050, P(200, 100)), false);
    guard.down(3, P(150, 150));
    assert.equal(guard.up(3, 2020, P(150, 150)), true);
  });

  it('fires nothing when the finger drags beyond the tap slop', () => {
    const guard = new TouchGestureGuard();
    guard.down(1, P(100, 100));
    const dragged = P(100 + TAP_SLOP_PX + 1, 100);
    guard.move(1, dragged);
    assert.equal(guard.up(1, 1050, dragged), false);
  });

  it('ignores an up without a down, and cancel clears an unfinished gesture', () => {
    const guard = new TouchGestureGuard();
    assert.equal(guard.up(1, 1000, P(0, 0)), false);
    guard.down(2, P(10, 10));
    guard.cancel();
    assert.equal(guard.up(2, 1010, P(10, 10)), false);
  });
});

describe('touch-safe styles in the one shared client', () => {
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');

  it('disables the browser pan and zoom gesture on the canvas', () => {
    const rule = html.match(/#game canvas\s*\{([^}]*)\}/)?.[1] ?? '';
    assert.match(rule, /touch-action:\s*none/);
  });

  it('keeps the panels scrollable inside the stage and the font scales intact', () => {
    const css = uiCss();
    assert.match(css, /touch-action:\s*pan-y/);
    assert.match(css, /-webkit-overflow-scrolling:\s*touch/);
    assert.match(css, /--swl-font-scale-body/);
    assert.match(css, /--swl-font-scale-display/);
  });
});
