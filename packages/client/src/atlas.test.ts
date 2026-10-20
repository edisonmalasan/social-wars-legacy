import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { AtlasIndex, type FrameManifest } from './atlas.ts';
import { imageHash } from './imagehash.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

/** A small manifest, in the shape the asset pipeline writes. */
const MANIFEST: FrameManifest = {
  symbols: [
    {
      swf: 'sprites/0001_house_1_m.swf',
      symbol: 'DefineSprite_4',
      frameCount: 3,
      uniqueFrames: 2,
      frames: [
        { frame: 1, image: 'aaa' },
        { frame: 2, image: 'bbb' },
        { frame: 3, image: 'aaa' },
      ],
    },
    {
      swf: 'sprites/0002_depot_wood_1_m.swf',
      symbol: 'DefineSprite_4',
      frameCount: 1,
      uniqueFrames: 1,
      frames: [{ frame: 1, image: 'ccc' }],
    },
  ],
  images: {
    aaa: {
      trim: { x: 12, y: 30, width: 40, height: 50 },
      atlas: { file: 'atlas-0000.png', x: 512, y: 0, width: 40, height: 50 },
    },
    bbb: {
      trim: { x: 0, y: 0, width: 40, height: 50 },
      atlas: { file: 'atlas-0000.png', x: 552, y: 0, width: 40, height: 50 },
    },
    ccc: {
      trim: null,
      atlas: { file: 'atlas-0001.png', x: 0, y: 0, width: 60, height: 60 },
    },
  },
};

describe('the atlas index', () => {
  it('finds a frame art', () => {
    const index = new AtlasIndex(MANIFEST);
    const location = index.lookup('sprites/0001_house_1_m.swf', 'DefineSprite_4', 1);
    assert.ok(location);
    assert.equal(location.atlas.file, 'atlas-0000.png');
    assert.equal(location.atlas.x, 512);
    assert.deepEqual(location.trim, { x: 12, y: 30, width: 40, height: 50 });
  });

  it('finds the art of every frame of a symbol', () => {
    const index = new AtlasIndex(MANIFEST);
    for (const frame of [1, 2, 3]) {
      assert.ok(index.lookup('sprites/0001_house_1_m.swf', 'DefineSprite_4', frame), `frame ${frame}`);
    }
  });

  it('shares one atlas region between the frames that are the same picture', () => {
    const index = new AtlasIndex(MANIFEST);
    const first = index.lookup('sprites/0001_house_1_m.swf', 'DefineSprite_4', 1);
    const third = index.lookup('sprites/0001_house_1_m.swf', 'DefineSprite_4', 3);
    assert.deepEqual(first, third);
  });

  it('returns null for a frame that does not exist', () => {
    const index = new AtlasIndex(MANIFEST);
    assert.equal(index.lookup('sprites/0001_house_1_m.swf', 'DefineSprite_4', 99), null);
  });

  it('returns null for a symbol that does not exist', () => {
    const index = new AtlasIndex(MANIFEST);
    assert.equal(index.lookup('sprites/nope.swf', 'DefineSprite_4', 1), null);
  });

  it('returns null for an image that has not been packed yet', () => {
    const index = new AtlasIndex({
      symbols: [
        { swf: 'a.swf', symbol: 'S', frameCount: 1, uniqueFrames: 1, frames: [{ frame: 1, image: 'x' }] },
      ],
      images: { x: { trim: null, atlas: null } },
    });
    assert.equal(index.lookup('a.swf', 'S', 1), null);
  });

  it('counts the frames of a symbol', () => {
    const index = new AtlasIndex(MANIFEST);
    assert.equal(index.frameCount('sprites/0001_house_1_m.swf', 'DefineSprite_4'), 3);
    assert.equal(index.frameCount('sprites/nope.swf', 'DefineSprite_4'), 0);
  });

  it('counts what it holds', () => {
    const index = new AtlasIndex(MANIFEST);
    assert.equal(index.symbolCount, 2);
    assert.equal(index.imageCount, 3);
  });

  it('draws the art at the tile position, less the trim offset', () => {
    const index = new AtlasIndex(MANIFEST);
    const location = index.lookup('sprites/0001_house_1_m.swf', 'DefineSprite_4', 1)!;
    // The trimmed region's top-left is the art's own corner, so it is drawn
    // 12 to the left and 30 above the tile's position.
    assert.deepEqual(index.drawPosition(location, 100, 200), { x: 88, y: 170 });
  });

  it('draws untrimmed art exactly at the tile position', () => {
    const index = new AtlasIndex(MANIFEST);
    const location = index.lookup('sprites/0002_depot_wood_1_m.swf', 'DefineSprite_4', 1)!;
    assert.deepEqual(index.drawPosition(location, 100, 200), { x: 100, y: 200 });
  });
});

describe('the content hash', () => {
  it('is stable', () => {
    const pixels = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
    assert.equal(imageHash(2, 1, pixels), imageHash(2, 1, pixels));
  });

  it('changes when the pixels change', () => {
    const a = new Uint8Array([1, 2, 3, 4]);
    const b = new Uint8Array([1, 2, 3, 5]);
    assert.notEqual(imageHash(1, 1, a), imageHash(1, 1, b));
  });

  it('changes when the dimensions change', () => {
    const pixels = new Uint8Array([1, 2, 3, 4]);
    assert.notEqual(imageHash(2, 1, pixels), imageHash(1, 2, pixels));
  });
});

describe('the real frame manifest', () => {
  it('has symbols and images', async () => {
    const file = path.join(repoRoot(), 're/data/frame-manifest.json');
    // The manifest is a large file that the asset pipeline rewrites, so it
    // is read with a retry: the pipeline now writes it atomically, but a
    // reader that starts mid-rename should not fail the suite.
    let manifest: FrameManifest | undefined;
    for (let attempt = 0; attempt < 3 && !manifest; attempt++) {
      try {
        manifest = JSON.parse(await readFile(file, 'utf8')) as FrameManifest;
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }
    assert.ok(manifest, 'the frame manifest could not be read');

    const index = new AtlasIndex(manifest);
    assert.ok(index.symbolCount > 1000, `only ${index.symbolCount} symbols`);
    assert.ok(index.imageCount > 1000, `only ${index.imageCount} images`);

    // Every symbol's frames must point at images the manifest knows.
    const sample = manifest.symbols.slice(0, 200);
    for (const symbol of sample) {
      for (const frame of symbol.frames) {
        assert.ok(
          manifest.images[frame.image] !== undefined,
          `${symbol.swf} ${symbol.symbol} frame ${frame.frame} points at an unknown image`,
        );
      }
    }
  });
});
