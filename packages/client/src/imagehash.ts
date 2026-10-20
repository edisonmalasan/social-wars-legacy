/**
 * The content hash of a piece of art.
 *
 * The asset pipeline hashes the PNG's **pixels**, not its file, so that
 * two files with the same picture share one entry. This reproduces that
 * hash from the pixels.
 *
 * It lives in its own module because it needs `node:crypto`, and the
 * client package runs **in a browser**: a runtime module that imported
 * `node:crypto` would break the web build. Nothing at runtime needs
 * this - the client reads the manifest - so it is only used by the asset
 * pipeline and by the test that proves the two agree.
 */
import { createHash } from 'node:crypto';

/** The hash of a piece of art, from its pixels. */
export function imageHash(width: number, height: number, rgba: Uint8Array): string {
  const hash = createHash('sha256');
  // The dimensions are part of the hash, so a 4x4 image and an 8x2 image
  // with the same bytes are different.
  hash.update(String(width));
  hash.update('x');
  hash.update(String(height));
  hash.update(':');
  hash.update(rgba);
  return hash.digest('hex');
}
