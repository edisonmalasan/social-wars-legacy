#!/usr/bin/env node
/**
 * Group D — the atlas packer.
 *
 * Takes the frame manifest produced by `scripts/convert-assets.mjs` and packs
 * the distinct images into texture atlases, ready for the renderer.
 *
 * Two things happen here.
 *
 * 1. **Trim.** A frame exported from a SWF is the whole stage, so most of it
 *    is transparent padding. Every image is cut to its alpha bounding box and
 *    the offset is recorded, so the renderer can place the sprite and the
 *    atlas holds no empty space.
 *
 * 2. **Pack.** The trimmed images are packed into square atlases with a shelf
 *    packer (rows of images, sorted by height so the wasted space is small).
 *    The manifest records the region of every image inside its atlas.
 *
 * The atlases are the artefact the client ships; the manifest is the contract.
 *
 * Usage:
 *   node scripts/pack-atlases.mjs
 *   node scripts/pack-atlases.mjs --size 2048 --padding 2
 *
 * Requires the frame manifest (run scripts/convert-assets.mjs first).
 */
import { existsSync } from 'node:fs';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { alphaBounds, crop, decodePng, encodePng } from './lib/png.mjs';

const ROOT = process.cwd();
const STORE = path.join(ROOT, '.work/frames/store');
const ATLAS_DIR = path.join(ROOT, '.work/frames/atlases');

function parseArgs(argv) {
  const args = {
    manifest: path.join(ROOT, 're/data/frame-manifest.json'),
    size: 2048,
    padding: 2,
  };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--manifest') args.manifest = path.resolve(argv[++i]);
    else if (argv[i] === '--size') args.size = Number(argv[++i]);
    else if (argv[i] === '--padding') args.padding = Number(argv[++i]);
  }
  return args;
}

/**
 * A shelf packer.
 *
 * Images are placed in rows. A new row starts when the next image does not
 * fit in the current one. The images are sorted by height first, so the rows
 * are as uniform as possible and the wasted space is small.
 */
class ShelfPacker {
  constructor(size, padding) {
    this.size = size;
    this.padding = padding;
    this.x = 0;
    this.y = 0;
    this.rowHeight = 0;
  }

  /** @returns {{x: number, y: number} | null} null when the image does not fit */
  place(width, height) {
    if (width > this.size || height > this.size) return null;
    if (this.x + width + this.padding > this.size) {
      // Start a new row.
      this.y += this.rowHeight + this.padding;
      this.x = 0;
      this.rowHeight = 0;
    }
    if (this.y + height + this.padding > this.size) return null;
    const spot = { x: this.x, y: this.y };
    this.x += width + this.padding;
    if (height > this.rowHeight) this.rowHeight = height;
    return spot;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (!existsSync(args.manifest)) {
    console.error(`no frame manifest at ${args.manifest}`);
    console.error('run: node scripts/convert-assets.mjs');
    process.exit(1);
  }
  await mkdir(ATLAS_DIR, { recursive: true });

  const manifest = JSON.parse(await readFile(args.manifest, 'utf8'));
  const images = Object.entries(manifest.images ?? {});
  console.log(`packing ${images.length} distinct images into ${args.size}x${args.size} atlases`);

  // 1. Decode and trim every image, and measure it.
  /** The measurement cache: each image's trimmed size and bounds. */
  const BOUNDS_CACHE = path.join(ROOT, '.work/frames/bounds.json');

  const measured = [];
  let rawPixels = 0;
  let trimmedPixels = 0;
  let fullyTransparent = 0;
  let missing = 0;
  let oversize = 0;

  // The measurement cache. The measuring pass is the expensive one - it
  // decodes every image - and it is pure, so its result is worth keeping.
  let cache = {};
  try {
    cache = JSON.parse(await readFile(BOUNDS_CACHE, 'utf8'));
  } catch {
    cache = {};
  }
  let measuredNow = 0;

  for (const [hash, image] of images) {
    const file = path.join(STORE, image.file);
    if (!existsSync(file)) {
      missing += 1;
      continue;
    }
    const known = cache[hash];
    if (known) {
      // Already measured: the bounds do not change.
      if (known.b) {
        trimmedPixels += known.w * known.h;
        measured.push({
          hash,
          image,
          width: known.w,
          height: known.h,
          bounds: known.b,
        });
      } else {
        fullyTransparent += 1;
        measured.push({ hash, image, width: 0, height: 0, bounds: null });
      }
      continue;
    }
    const decoded = decodePng(await readFile(file));
    rawPixels += decoded.width * decoded.height;
    const bounds = alphaBounds(decoded);
    measuredNow += 1;
    if (!bounds) {
      fullyTransparent += 1;
      // The PIXELS ARE THROWN AWAY here. Keeping every decoded image is
      // what ran the packer out of memory; the pixels are decoded again,
      // one atlas at a time, in the render pass below.
      cache[hash] = { w: 0, h: 0, b: null };
      measured.push({ hash, image, width: 0, height: 0, bounds: null });
      continue;
    }
    trimmedPixels += bounds.width * bounds.height;
    cache[hash] = { w: bounds.width, h: bounds.height, b: bounds };
    measured.push({ hash, image, width: bounds.width, height: bounds.height, bounds });
  }

  // The cache is written before the long render, so a death in the render
  // does not cost the measuring again.
  await writeFile(BOUNDS_CACHE, JSON.stringify(cache), 'utf8');
  console.log(`  ${measuredNow} images measured, ${measured.length - measuredNow} from the cache`);

  console.log(
    `  ${measured.length} images, ${fullyTransparent} fully transparent, ${missing} missing from the store`,
  );
  if (oversize > 0) {
    console.warn(
      `  ! ${oversize} image(s) are bigger than a whole ${args.size}x${args.size} atlas ` +
        'and could not be given a region. They are recorded with a null atlas.',
    );
  }
  console.log(
    `  pixels: ${(rawPixels / 1e6).toFixed(1)}M raw -> ${(trimmedPixels / 1e6).toFixed(1)}M trimmed ` +
      `(${((1 - trimmedPixels / Math.max(1, rawPixels)) * 100).toFixed(1)}% was padding)`,
  );

  // 2. Pack, tallest first.
  measured.sort((a, b) => b.height - a.height || b.width - a.width);

  const packer = new ShelfPacker(args.size, args.padding);
  const sheets = [];
  // The sheet being filled. It is created up front, because the very first
  // image usually fits and would otherwise find no sheet to go into.
  let current = { images: [], used: 0 };

  for (const entry of measured) {
    if (entry.width === 0) {
      // Nothing to draw; it keeps a zero-sized region in its atlas.
      entry.atlas = null;
      continue;
    }
    let spot = packer.place(entry.width, entry.height);
    if (!spot) {
      // The current atlas is full: start a new one.
      if (current) sheets.push(current);
      current = { images: [], used: 0 };
      packer.x = 0;
      packer.y = 0;
      packer.rowHeight = 0;
      spot = packer.place(entry.width, entry.height);
      if (!spot) {
        // An image bigger than the whole atlas cannot be given a region.
        // It is counted and reported rather than dropped silently, and the
        // manifest records it with a null atlas.
        oversize += 1;
        entry.atlas = null;
        entry.oversize = true;
        continue;
      }
    }
    entry.atlas = spot;
    current.images.push(entry);
    current.used += entry.width * entry.height;
  }
  if (current) sheets.push(current);

  // 3. Render the atlases.
  const atlasInfo = [];
  for (let index = 0; index < sheets.length; index++) {
    const sheet = sheets[index];
    const canvas = { width: args.size, height: args.size, data: Buffer.alloc(args.size * args.size * 4) };

    for (const entry of sheet.images) {
      // The image is decoded AGAIN, here, so that only one atlas's worth of
      // pixels is ever in memory.
      const file = path.join(STORE, entry.image.file);
      if (!existsSync(file)) continue;
      const decoded = decodePng(await readFile(file));
      const trimmed = crop(decoded, entry.bounds);
      for (let y = 0; y < trimmed.height; y++) {
        const from = y * trimmed.width * 4;
        trimmed.data.copy(
          canvas.data,
          ((entry.atlas.y + y) * args.size + entry.atlas.x) * 4,
          from,
          from + trimmed.width * 4,
        );
      }
    }

    const file = `atlas-${String(index).padStart(4, '0')}.png`;
    const target = path.join(ATLAS_DIR, file);
    if (existsSync(target)) {
      // The sheet is already on disk. The packing is deterministic, so it
      // is the right sheet, and rendering it again would cost an hour.
      const info = await stat(target);
      atlasInfo.push({
        file,
        width: args.size,
        height: args.size,
        images: sheet.images.length,
        usedPixels: sheet.used,
        bytes: info.size,
      });
      if ((index + 1) % 10 === 0 || index === sheets.length - 1) {
        console.log(`  atlas ${index + 1}/${sheets.length}`);
      }
      continue;
    }
    const bytes = encodePng(canvas);
    await writeFile(target, bytes);
    atlasInfo.push({
      file,
      width: args.size,
      height: args.size,
      images: sheet.images.length,
      usedPixels: sheet.used,
      bytes: bytes.length,
    });

    if ((index + 1) % 10 === 0 || index === sheets.length - 1) {
      console.log(`  atlas ${index + 1}/${sheets.length}`);
    }
  }

  // 4. Record the regions in the manifest.
  const outImages = {};
  for (const entry of measured) {
    const image = { ...entry.image };
    if (entry.atlas && entry.bounds) {
      image.trim = {
        x: entry.bounds.x,
        y: entry.bounds.y,
        width: entry.bounds.width,
        height: entry.bounds.height,
      };
    } else {
      image.trim = null;
    }
    outImages[entry.hash] = image;
  }
  // The atlas index per image, looked up from the sheets.
  const atlasOf = new Map();
  for (let index = 0; index < sheets.length; index++) {
    for (const entry of sheets[index].images) {
      atlasOf.set(entry.hash, {
        file: atlasInfo[index].file,
        x: entry.atlas.x,
        y: entry.atlas.y,
        width: entry.width,
        height: entry.height,
      });
    }
  }
  for (const [hash, image] of Object.entries(outImages)) {
    image.atlas = atlasOf.get(hash) ?? null;
  }

  const totalAtlasBytes = atlasInfo.reduce((n, a) => n + a.bytes, 0);
  const totalAtlasPixels = atlasInfo.length * args.size * args.size;
  manifest.images = outImages;
  manifest.atlases = {
    note:
      'The packed texture atlases. Every image in `images` carries the region it ' +
      'occupies in its atlas, and the `trim` offset it was cut from. The atlas ' +
      'files themselves are a build artefact.',
    size: args.size,
    padding: args.padding,
    count: atlasInfo.length,
    totalBytes: totalAtlasBytes,
    occupancy: totalAtlasPixels ? Number((trimmedPixels / totalAtlasPixels).toFixed(4)) : 0,
    sheets: atlasInfo,
  };

  await writeFile(args.manifest, JSON.stringify(manifest, null, 1) + '\n', 'utf8');

  console.log('');
  console.log(`atlases             : ${atlasInfo.length} x ${args.size}px`);
  console.log(`atlas bytes         : ${(totalAtlasBytes / 1048576).toFixed(1)} MB`);
  console.log(`atlas occupancy     : ${(manifest.atlases.occupancy * 100).toFixed(1)}%`);
  console.log(`\nwrote ${args.manifest}`);
  console.log(`atlas files: ${ATLAS_DIR}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
