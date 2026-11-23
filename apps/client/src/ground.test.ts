import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { STAGE_HEIGHT, STAGE_WIDTH, type Viewport } from '@swl/client';

import { buildGround, GROUND_COLOUR } from './scene.ts';

const VIEWPORT: Viewport = { topX: 0, topY: 0, buildOutlineOffsetY: 0 };

/** Parse a `#RRGGBB` colour into its channels. */
function channels(colour: string): { r: number; g: number; b: number } {
  const match = /^#([0-9a-fA-F]{6})$/.exec(colour);
  assert.ok(match, `GROUND_COLOUR must be a #RRGGBB hex colour, got ${colour}`);
  const value = Number.parseInt(match![1]!, 16);
  return {
    r: (value >> 16) & 0xff,
    g: (value >> 8) & 0xff,
    b: value & 0xff,
  };
}

describe('the ground layer', () => {
  it('uses the original green field colour', () => {
    const { r, g, b } = channels(GROUND_COLOUR);
    // The reference is #669C2C (play.html bgcolor); green must dominate.
    assert.ok(g > r * 1.4, `green ${g} must exceed red ${r} * 1.4`);
    assert.ok(g > b * 1.6, `green ${g} must exceed blue ${b} * 1.6`);
  });

  it('produces at least 100 diamond tiles covering the stage', () => {
    const ground = buildGround(VIEWPORT);
    assert.ok(ground.length >= 100, `expected >= 100 tiles, got ${ground.length}`);
  });

  it('places every tile at a distinct position inside the stage', () => {
    const ground = buildGround(VIEWPORT);
    const seen = new Set<string>();
    for (const tile of ground) {
      assert.ok(
        tile.x >= 0 && tile.x < STAGE_WIDTH,
        `tile x ${tile.x} outside [0, ${STAGE_WIDTH})`,
      );
      assert.ok(
        tile.y >= 0 && tile.y < STAGE_HEIGHT,
        `tile y ${tile.y} outside [0, ${STAGE_HEIGHT})`,
      );
      const key = `${tile.x},${tile.y}`;
      assert.ok(!seen.has(key), `duplicate tile position ${key}`);
      seen.add(key);
    }
  });

  it('is deterministic for the same viewport', () => {
    const first = buildGround(VIEWPORT).map((tile) => `${tile.x},${tile.y}`);
    const second = buildGround(VIEWPORT).map((tile) => `${tile.x},${tile.y}`);
    assert.deepEqual(second, first);
  });
});
