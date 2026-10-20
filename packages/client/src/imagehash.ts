/**
 * The content hash of a piece of art.
 *
 * The asset pipeline keys the store by the SHA-256 of the image's
 * **file bytes**, so this reproduces that hash exactly.
 *
 * It lives in its own module because it needs `node:crypto`, and the
 * client package runs **in a browser**: a runtime module that imported
 * `node:crypto` would break the web build. Nothing at runtime needs
 * this - the client reads the manifest, which already carries the
 * hashes - so it is only used by the asset pipeline and by the test that
 * proves the two agree.
 */
import { createHash } from 'node:crypto';

/**
 * The hash of a piece of art, from its file's bytes.
 *
 * The bytes are the PNG's, exactly as the pipeline hashed them.
 */
export function imageHash(bytes: Uint8Array): string {
  return createHash('sha256').update(bytes).digest('hex');
}
