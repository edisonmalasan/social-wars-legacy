import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { AtlasIndex, type FrameManifest } from '@swl/client';

import { buildScene, type SceneItem } from './scene.ts';

const VIEWPORT = { topX: 0, topY: 0, buildOutlineOffsetY: 0 };

/** A manifest with one symbol and one frame. */
const MANIFEST: FrameManifest = {
  images: {
    art0: {
      trim: { x: 2, y: 3, width: 10, height: 20 },
      atlas: { file: 'atlas-0000.png', x: 100, y: 200, width: 10, height: 20 },
    },
  },
  symbols: [
    {
      swf: 'assets.swf',
      symbol: 'DefineSprite_4',
      frameCount: 40,
      frames: [{ frame: 1, image: 'art0' }],
    },
  ],
  itemArt: {
    '1': { swf: 'assets.swf', symbol: 'DefineSprite_4' },
  },
} as unknown as FrameManifest;

function item(over: Partial<SceneItem> = {}): SceneItem {
  return {
    id: '7',
    itemId: 1,
    tx: 10,
    ty: 20,
    width: 1,
    walkable: false,
    elevation: 0,
    orientation: 0,
    animation: 0,
    ...over,
  };
}

describe('the scene', () => {
  it('places an item with the client own projection', () => {
    const scene = buildScene([item()], VIEWPORT, new AtlasIndex(MANIFEST));
    assert.equal(scene.length, 1);
    // The tile is 108 by 54, so the tile (10, 20) is at
    // `0 - 54 * 20 + 54 * 10` and `27 * 20 + 27 * 10 - 27`.
    assert.equal(scene[0]!.x, -54 * 20 + 54 * 10);
    assert.equal(scene[0]!.y, 27 * 20 + 27 * 10 - 27);
  });

  it('gives an item the client own depth', () => {
    const scene = buildScene([item()], VIEWPORT, new AtlasIndex(MANIFEST));
    // `20 000 + 100 * tx + ty * 100 - width * 100`, less 20 000 for a
    // walkable building.
    assert.equal(scene[0]!.depth, 20_000 + 100 * 10 + 20 * 100 - 100);
  });

  it('sorts the scene by depth, back to front', () => {
    const scene = buildScene(
      [
        item({ id: 'front', tx: 20, ty: 20 }),
        item({ id: 'back', tx: 10, ty: 20 }),
        item({ id: 'middle', tx: 15, ty: 20 }),
      ],
      VIEWPORT,
      new AtlasIndex(MANIFEST),
    );
    assert.deepEqual(
      scene.map((sprite) => sprite.id),
      ['back', 'middle', 'front'],
    );
  });

  it('is stable, so two items at the same depth keep their order', () => {
    const scene = buildScene(
      [item({ id: 'a', tx: 10, ty: 20 }), item({ id: 'b', tx: 10, ty: 20 })],
      VIEWPORT,
      new AtlasIndex(MANIFEST),
    );
    assert.deepEqual(
      scene.map((sprite) => sprite.id),
      ['a', 'b'],
    );
  });

  it('puts a walkable item behind everything', () => {
    const scene = buildScene(
      [item({ id: 'road', walkable: true }), item({ id: 'house', tx: 10, ty: 20 })],
      VIEWPORT,
      new AtlasIndex(MANIFEST),
    );
    assert.equal(scene[0]!.id, 'road');
  });

  it('finds the art for the frame', () => {
    const scene = buildScene([item()], VIEWPORT, new AtlasIndex(MANIFEST));
    assert.ok(scene[0]!.art);
    assert.equal(scene[0]!.art!.atlas.file, 'atlas-0000.png');
    assert.equal(scene[0]!.art!.atlas.x, 100);
    assert.equal(scene[0]!.art!.trim?.x, 2);
  });

  it('has no art for a frame the atlas does not have', () => {
    // The symbol has one frame, so frame 6 is not in it.
    const scene = buildScene(
      [item({ orientation: 5 })],
      VIEWPORT,
      new AtlasIndex(MANIFEST),
    );
    assert.equal(scene[0]!.art, null);
    // The frame is still chosen, so the scene knows what it wanted.
    assert.equal(scene[0]!.frame?.frame, 5);
  });

  it('looks the frame up ONE higher, because the manifest is one-based', () => {
    // The client picks the drawing with `gotoAndStop(frame + 1)`, and the
    // manifest's frames are one-based, so the lookup is one higher than
    // the frame the animation chose.
    const scene = buildScene([item()], VIEWPORT, new AtlasIndex(MANIFEST));
    assert.ok(scene[0]!.art, 'the art was not found');
  });

  it('mirrors the three left-facing directions', () => {
    const scene = buildScene(
      [item({ orientation: 6 })],
      VIEWPORT,
      new AtlasIndex(MANIFEST),
    );
    assert.equal(scene[0]!.frame?.mirrored, true);
  });

  it('carries the elevation', () => {
    const scene = buildScene(
      [item({ elevation: 12 })],
      VIEWPORT,
      new AtlasIndex(MANIFEST),
    );
    assert.equal(scene[0]!.elevation, 12);
  });
});
