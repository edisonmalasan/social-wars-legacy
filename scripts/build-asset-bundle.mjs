#!/usr/bin/env node
/**
 * Build the content-hashed asset bundle.
 *
 * The client must never load a stale asset. A cache keyed by the URL
 * alone cannot promise that: change a PNG and the URL does not change,
 * so the browser serves the old one.
 *
 * The bundle solves it the usual way: every asset's content hash is
 * recorded, and ONE hash over the whole set becomes the bundle's build
 * id. The client appends that id to every asset URL, so a changed asset
 * means a changed URL, and the cache cannot be stale.
 *
 * The bundle is also the client's **index**: which atlas page each sprite
 * is on, and where in it. The renderer should not have to know how the
 * atlases are laid out.
 *
 * Usage:
 *   node scripts/build-asset-bundle.mjs
 */
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const ASSET_MANIFEST = path.join(ROOT, 're/data/asset-manifest.json');
const FRAME_MANIFEST = path.join(ROOT, 're/data/frame-manifest.json');
const OUT = path.join(ROOT, 're/data/asset-bundle.json');

/** The hash of a set of content hashes: one number for the whole bundle. */
function bundleHash(entries) {
  const hash = createHash('sha256');
  for (const entry of [...entries].sort()) {
    hash.update(entry);
    hash.update('\n');
  }
  return hash.digest('hex');
}

async function main() {
  if (!existsSync(ASSET_MANIFEST)) {
    console.error(`no asset manifest at ${ASSET_MANIFEST}`);
    console.error('run: node scripts/build-asset-manifest.mjs');
    process.exit(1);
  }

  const assets = JSON.parse(await readFile(ASSET_MANIFEST, 'utf8'));

  let frames = null;
  try {
    frames = JSON.parse(await readFile(FRAME_MANIFEST, 'utf8'));
  } catch {
    console.warn('  the frame manifest is not there yet: the bundle has no atlases.');
  }

  // --- the images and the sounds ------------------------------------------
  const images = {};
  for (const image of assets.images ?? []) {
    images[image.sha256] = {
      path: image.path,
      bytes: image.bytes,
      sha256: image.sha256,
    };
  }
  const sounds = {};
  for (const sound of assets.sounds ?? []) {
    sounds[sound.sha256] = {
      path: sound.path,
      bytes: sound.bytes,
      sha256: sound.sha256,
      embedded: sound.embedded === true,
      ...(sound.source ? { source: sound.source } : {}),
    };
  }

  // --- the sprites ---------------------------------------------------------
  // Each sprite is looked up by name, and points at the atlas region its
  // first frame occupies. The renderer needs the region, not the layout.
  const sprites = {};
  const atlases = {};
  if (frames) {
    const byHash = frames.images ?? {};
    for (const symbol of frames.symbols ?? []) {
      const swf = symbol.swf ?? '';
      if (!swf.startsWith('sprites/')) continue;
      const name = swf.slice('sprites/'.length).replace(/\.swf$/, '');
      const frame = (symbol.frames ?? [])[0];
      if (!frame) continue;
      const image = byHash[frame.image];
      if (!image || !image.atlas) continue;
      const atlas = image.atlas;
      atlases[atlas.file] = atlas;
      sprites[name] = {
        /** The content hash of the image, which is the sprite's identity. */
        hash: frame.image,
        /** The atlas page. */
        file: atlas.file,
        x: atlas.x,
        y: atlas.y,
        width: atlas.width,
        height: atlas.height,
        /** Where the art was cut from, so it can be placed correctly. */
        trim: image.trim ?? null,
        /** How many frames the sprite has. */
        frames: symbol.frameCount ?? 0,
      };
    }
  }

  // --- the build id --------------------------------------------------------
  // One hash over every content hash in the bundle, so any change to any
  // asset changes the id.
  const everything = [
    ...Object.keys(images).map((hash) => `i:${hash}`),
    ...Object.keys(sounds).map((hash) => `s:${hash}`),
    ...Object.keys(sprites).map((name) => `p:${name}:${sprites[name].hash}`),
  ];
  const buildId = bundleHash(everything);

  const bundle = {
    note:
      'The content-hashed asset bundle. The build id is one hash over every ' +
      "asset's content hash, so any change to any asset changes the id, and " +
      'the client appends it to every asset URL. A stale cache is then ' +
      'impossible rather than unlikely.',
    buildId,
    counts: {
      images: Object.keys(images).length,
      sounds: Object.keys(sounds).length,
      sprites: Object.keys(sprites).length,
      atlases: Object.keys(atlases).length,
    },
    images,
    sounds,
    sprites,
    atlases,
  };

  await writeFile(OUT, JSON.stringify(bundle, null, 1) + '\n', 'utf8');
  console.log(`wrote ${OUT}`);
  console.log(`  build id: ${buildId}`);
  console.log(
    `  ${bundle.counts.images} images, ${bundle.counts.sounds} sounds, ` +
      `${bundle.counts.sprites} sprites, ${bundle.counts.atlases} atlas pages`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
