import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { alphaBounds, crop, decodePng, encodePng, pngSize } from './png.mjs';

const STORE = path.join(process.cwd(), '.work/frames/store');

/** A PNG with a known shape: an opaque 4x4 square in the middle of 16x16. */
function makeTestImage() {
  const width = 16;
  const height = 16;
  const data = Buffer.alloc(width * height * 4);
  for (let y = 6; y < 10; y++) {
    for (let x = 5; x < 9; x++) {
      const i = (y * width + x) * 4;
      data[i] = 200;
      data[i + 1] = 100;
      data[i + 2] = 50;
      data[i + 3] = 255;
    }
  }
  return { width, height, data };
}

describe('the PNG codec', () => {
  it('round-trips an image without changing a pixel', () => {
    const original = makeTestImage();
    const encoded = encodePng(original);
    const decoded = decodePng(encoded);

    assert.equal(decoded.width, original.width);
    assert.equal(decoded.height, original.height);
    assert.deepEqual(decoded.data, original.data);
  });

  it('reads the size without decoding', () => {
    const encoded = encodePng(makeTestImage());
    assert.deepEqual(pngSize(encoded), { width: 16, height: 16 });
  });

  it('finds the alpha bounding box', () => {
    const bounds = alphaBounds(makeTestImage());
    assert.deepEqual(bounds, { x: 5, y: 6, width: 4, height: 4 });
  });

  it('reports a fully transparent image as having no bounds', () => {
    const blank = { width: 8, height: 8, data: Buffer.alloc(8 * 8 * 4) };
    assert.equal(alphaBounds(blank), null);
  });

  it('crops to a rectangle', () => {
    const cropped = crop(makeTestImage(), { x: 5, y: 6, width: 4, height: 4 });
    assert.equal(cropped.width, 4);
    assert.equal(cropped.height, 4);
    // Every pixel of the crop is the opaque square.
    for (let i = 0; i < 16; i++) {
      assert.equal(cropped.data[i * 4 + 3], 255);
    }
  });

  it('decodes a real exported frame', async () => {
    const { readdir } = await import('node:fs/promises');
    const files = (await readdir(STORE)).filter((f) => f.endsWith('.png'));
    if (files.length === 0) return; // nothing converted yet

    const decoded = decodePng(await readFile(path.join(STORE, files[0])));
    assert.ok(decoded.width > 0);
    assert.ok(decoded.height > 0);
    assert.equal(decoded.data.length, decoded.width * decoded.height * 4);
  });
});
