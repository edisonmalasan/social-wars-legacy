import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  atlasUrl,
  drawPosition,
  imageUrl,
  isUsable,
  soundUrl,
  spriteOf,
  type AssetBundle,
} from './assets.ts';

const BUNDLE: AssetBundle = {
  buildId: 'a'.repeat(64),
  counts: { images: 1, sounds: 1, sprites: 1, atlases: 1 },
  images: {
    img1: { path: 'images/house.png', bytes: 100, sha256: 'img1' },
  },
  sounds: {
    snd1: { path: 'sounds/boom.mp3', bytes: 50, sha256: 'snd1' },
  },
  sprites: {
    '0001_house_1_m': {
      hash: 'img1',
      file: 'atlas-0000.png',
      x: 512,
      y: 0,
      width: 40,
      height: 50,
      trim: { x: 12, y: 30, width: 40, height: 50 },
      frames: 170,
    },
  },
  atlases: {
    'atlas-0000.png': { file: 'atlas-0000.png', x: 512, y: 0, width: 40, height: 50 },
  },
};

describe('the asset bundle', () => {
  it('gives every URL the build id, so a stale cache is impossible', () => {
    const url = atlasUrl(BUNDLE, 'atlas-0000.png');
    assert.ok(url.includes(BUNDLE.buildId), `the build id is missing from ${url}`);
    assert.ok(url.startsWith('/assets/atlases/atlas-0000.png'));
  });

  it('gives the sounds and the images the build id too', () => {
    assert.ok(soundUrl(BUNDLE, 'snd1')!.includes(BUNDLE.buildId));
    assert.ok(imageUrl(BUNDLE, 'img1')!.includes(BUNDLE.buildId));
  });

  it('has no URL for an asset it does not hold', () => {
    assert.equal(soundUrl(BUNDLE, 'nope'), null);
    assert.equal(imageUrl(BUNDLE, 'nope'), null);
  });

  it('finds a sprite and its region', () => {
    const region = spriteOf(BUNDLE, '0001_house_1_m');
    assert.ok(region);
    assert.equal(region.file, 'atlas-0000.png');
    assert.equal(region.x, 512);
    assert.equal(region.frames, 170);
  });

  it('has no region for a sprite it does not hold', () => {
    assert.equal(spriteOf(BUNDLE, 'nope'), null);
  });

  it('draws the art at the tile position, less the trim offset', () => {
    const region = spriteOf(BUNDLE, '0001_house_1_m')!;
    assert.deepEqual(drawPosition(region, 100, 200), { x: 88, y: 170 });
  });

  it('refuses a bundle with no build id', () => {
    assert.equal(isUsable(null), false);
    assert.equal(isUsable(undefined), false);
    assert.equal(isUsable({ ...BUNDLE, buildId: '' }), false);
    assert.equal(isUsable({ ...BUNDLE, buildId: 'short' }), false);
    assert.equal(isUsable(BUNDLE), true);
  });

  it('uses the base path it is given', () => {
    assert.ok(atlasUrl(BUNDLE, 'atlas-0000.png', '/cdn/assets/').startsWith('/cdn/assets/atlases/'));
  });
});
