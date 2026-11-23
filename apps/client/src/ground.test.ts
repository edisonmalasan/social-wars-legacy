import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';
import { dirname, resolve as resolvePath } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { STAGE_HEIGHT, STAGE_WIDTH, type Viewport } from '@swl/client';
import { Container, Texture, type Sprite } from 'pixi.js';

import {
  buildGround,
  GROUND_COLOUR,
  GROUND_TONES,
  groundToneFor,
} from './scene.ts';

// @swl/art is aliased by Vite, so Node needs the same subpath mapping the
// other client tests use to load the renderer that owns the ground layer.
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolvePath(HERE, '../../..');
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === '@swl/art/browser') {
      return {
        url: pathToFileURL(resolvePath(ROOT, 'packages/art/browser.ts')).href,
        shortCircuit: true,
      };
    }
    return nextResolve(specifier, context);
  },
});
const { GroundLayer } = await import('./renderer.ts');

const VIEWPORT: Viewport = { topX: 0, topY: 0, buildOutlineOffsetY: 0 };

/** Parse a `#RRGGBB` colour into its channels. */
function channels(colour: string): { r: number; g: number; b: number } {
  const match = /^#([0-9a-fA-F]{6})$/.exec(colour);
  assert.ok(match, `a ground colour must be a #RRGGBB hex colour, got ${colour}`);
  const value = Number.parseInt(match![1]!, 16);
  return {
    r: (value >> 16) & 0xff,
    g: (value >> 8) & 0xff,
    b: value & 0xff,
  };
}

/** A relative brightness, used only to bound how subtle the shading is. */
function brightness(colour: string): number {
  const { r, g, b } = channels(colour);
  return r + g + b;
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

  it('generates two distinct green shades for the diamond textures', () => {
    assert.ok(Array.isArray(GROUND_TONES), 'GROUND_TONES must be an array');
    assert.ok(GROUND_TONES.length >= 2, `expected at least 2 tones, got ${GROUND_TONES.length}`);
    assert.equal(
      new Set(GROUND_TONES).size,
      GROUND_TONES.length,
      'the generated ground tones must be distinct',
    );
    for (const tone of GROUND_TONES) {
      const { r, g, b } = channels(tone);
      assert.ok(g > r * 1.4, `${tone}: green ${g} must exceed red ${r} * 1.4`);
      assert.ok(g > b * 1.6, `${tone}: green ${g} must exceed blue ${b} * 1.6`);
    }
  });

  it('alternates the two shades subtly so the isometric grid reads', () => {
    const [light, dark] = GROUND_TONES;
    const delta = Math.abs(brightness(light) - brightness(dark));
    assert.ok(delta >= 12, `the tones differ by only ${delta} - the grid would not read`);
    assert.ok(delta <= 90, `the tones differ by ${delta} - that is not subtle shading`);

    assert.notEqual(groundToneFor(0, 0), groundToneFor(1, 0));
    assert.equal(groundToneFor(0, 0), groundToneFor(2, 0));
    assert.equal(groundToneFor(0, 0), groundToneFor(0, 2));

    for (const tile of buildGround(VIEWPORT)) {
      assert.ok(
        tile.tone === GROUND_TONES[0] || tile.tone === GROUND_TONES[1],
        `tile ${tile.id} has no generated ground tone`,
      );
    }
  });
});

describe('the reusable ground layer', () => {
  /** A layer with one shared test texture, so no canvas or GPU is needed. */
  function layer(): { container: Container; ground: InstanceType<typeof GroundLayer> } {
    const container = new Container();
    const texture = Texture.WHITE;
    return { container, ground: new GroundLayer(container, () => texture) };
  }

  it('reuses the very same tile sprites when the viewport has not changed', () => {
    const { container, ground } = layer();
    ground.sync(VIEWPORT);
    const first = [...container.children] as Sprite[];
    assert.ok(first.length >= 100, `expected >= 100 ground sprites, got ${first.length}`);

    ground.sync(VIEWPORT);
    const second = [...container.children] as Sprite[];
    assert.equal(second.length, first.length, 'the tile count must not change');
    for (let i = 0; i < first.length; i += 1) {
      assert.strictEqual(second[i], first[i], `tile sprite ${i} was reallocated`);
    }
  });

  it('moves the reused sprites when the camera pans', () => {
    const { container, ground } = layer();
    ground.sync(VIEWPORT);
    const first = [...container.children] as Sprite[];
    // Snapshot the positions: the sprites are mutated in place, so keeping
    // only their references would compare each sprite's new x to itself.
    const before = first.map((sprite) => ({ sprite, x: sprite.x, y: sprite.y }));

    // A small pan keeps the same tiles on the stage (one edge column leaves),
    // so every remaining sprite must be a reused object with a new position.
    ground.sync({ ...VIEWPORT, topX: VIEWPORT.topX + 5 });
    const second = [...container.children] as Sprite[];
    assert.ok(second.length >= 100, `expected >= 100 ground sprites, got ${second.length}`);
    for (const sprite of second) {
      assert.ok(first.includes(sprite), 'every sprite after a pan must be a reused object');
    }
    assert.ok(
      second.some((sprite) => {
        const old = before.find((entry) => entry.sprite === sprite);
        return !!old && (old.x !== sprite.x || old.y !== sprite.y);
      }),
      'the reused sprites must be moved to the new tile positions',
    );
  });
});
