#!/usr/bin/env node
/**
 * Group D — the asset manifest.
 *
 * The SWF art is handled by `scripts/convert-assets.mjs` and
 * `scripts/pack-atlases.mjs`. This script handles everything else in the asset
 * tree, and answers the question the roadmap actually cares about:
 *
 *   does every content item resolve to an asset, and if not, which ones?
 *
 * It catalogues every JPG and MP3, then cross-references:
 *
 *   - the 900 content items' `img_name` against the sprite and thumbnail trees
 *   - the config's 139 sounds against `assets/sounds/`
 *   - the config's 607 localised images against `assets/images/`
 *
 * and reports both directions: what is referenced but missing, and what is
 * present but unreferenced.
 *
 * Usage:
 *   node scripts/build-asset-manifest.mjs
 */
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { jpegSize } from './lib/jpeg.mjs';
import { pngSize } from './lib/png.mjs';

const ROOT = process.cwd();
const ASSETS = path.join(ROOT, 'upstream/socialwarriors/assets');
const BUNDLE = path.join(ROOT, 'packages/content/dist/content-bundle.json');
const OUT = path.join(ROOT, 're/data/asset-manifest.json');
/**
 * The sounds baked into the runtime library.
 *
 * `dynamic2.swf` carries 28 of its own - the construction animations'
 * audio - and they are named nowhere in the config's sound list. The
 * extractor writes them here.
 */
const EMBEDDED_SOUNDS = path.join(ROOT, '.work/sounds');

async function listFiles(dir, ext, base = '') {
  const out = [];
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    const rel = base ? `${base}/${entry.name}` : entry.name;
    if (entry.isDirectory()) out.push(...(await listFiles(path.join(dir, entry.name), ext, rel)));
    else if (entry.name.toLowerCase().endsWith(ext)) out.push(rel);
  }
  return out;
}

async function main() {
  if (!existsSync(BUNDLE)) {
    console.error(`no content bundle at ${BUNDLE}`);
    console.error('run: pnpm build:content');
    process.exit(1);
  }
  const bundle = JSON.parse(await readFile(BUNDLE, 'utf8'));

  // 1. Catalogue every image and every MP3. The image tree holds JPGs, PNGs
  //    and a few SWFs, and the config references all three.
  console.log('cataloguing the image and audio assets...');

  const images = [];
  for (const rel of await listFiles(path.join(ASSETS, 'images'), '.jpg')) {
    const buffer = await readFile(path.join(ASSETS, 'images', rel));
    const size = jpegSize(buffer);
    images.push({
      path: `images/${rel}`,
      kind: 'jpg',
      bytes: buffer.length,
      width: size?.width ?? 0,
      height: size?.height ?? 0,
      sha256: createHash('sha256').update(buffer).digest('hex'),
    });
  }
  for (const rel of await listFiles(path.join(ASSETS, 'images'), '.png')) {
    const buffer = await readFile(path.join(ASSETS, 'images', rel));
    images.push({
      path: `images/${rel}`,
      kind: 'png',
      bytes: buffer.length,
      width: pngSize(buffer)?.width ?? 0,
      height: pngSize(buffer)?.height ?? 0,
      sha256: createHash('sha256').update(buffer).digest('hex'),
    });
  }
  for (const rel of await listFiles(path.join(ASSETS, 'images'), '.swf')) {
    const buffer = await readFile(path.join(ASSETS, 'images', rel));
    images.push({
      path: `images/${rel}`,
      kind: 'swf',
      bytes: buffer.length,
      width: 0,
      height: 0,
      sha256: createHash('sha256').update(buffer).digest('hex'),
    });
  }
  for (const rel of await listFiles(path.join(ASSETS, 'thumbs'), '.jpg')) {
    const buffer = await readFile(path.join(ASSETS, 'thumbs', rel));
    const size = jpegSize(buffer);
    images.push({
      path: `thumbs/${rel}`,
      kind: 'jpg',
      bytes: buffer.length,
      width: size?.width ?? 0,
      height: size?.height ?? 0,
      sha256: createHash('sha256').update(buffer).digest('hex'),
    });
  }

  const sounds = [];
  for (const rel of await listFiles(path.join(ASSETS, 'sounds'), '.mp3')) {
    const buffer = await readFile(path.join(ASSETS, 'sounds', rel));
    sounds.push({
      path: `sounds/${rel}`,
      bytes: buffer.length,
      sha256: createHash('sha256').update(buffer).digest('hex'),
      embedded: false,
    });
  }

  // The sounds baked into the runtime library. They are part of the audio
  // set the client loads, so they are listed with it - marked as embedded,
  // because their bytes live in a SWF rather than in a standalone file.
  let embeddedSounds = 0;
  for (const rel of await listFiles(EMBEDDED_SOUNDS, '.mp3')) {
    const buffer = await readFile(path.join(EMBEDDED_SOUNDS, rel));
    sounds.push({
      path: `embedded/${rel}`,
      bytes: buffer.length,
      sha256: createHash('sha256').update(buffer).digest('hex'),
      embedded: true,
      source: 'swf/dynamic2.swf',
    });
    embeddedSounds += 1;
  }
  for (const rel of await listFiles(EMBEDDED_SOUNDS, '.wav')) {
    const buffer = await readFile(path.join(EMBEDDED_SOUNDS, rel));
    sounds.push({
      path: `embedded/${rel}`,
      bytes: buffer.length,
      sha256: createHash('sha256').update(buffer).digest('hex'),
      embedded: true,
      source: 'swf/dynamic2.swf',
    });
    embeddedSounds += 1;
  }

  console.log(
    `  ${images.length} images, ${sounds.length} sounds ` +
      `(${embeddedSounds} embedded in the runtime library)`,
  );

  // 2. The sprite names that exist, for the items' img_name.
  const spriteNames = new Set();
  for (const rel of await listFiles(path.join(ASSETS, 'sprites'), '.swf')) {
    spriteNames.add(rel.replace(/\.swf$/, ''));
  }
  const thumbNames = new Set();
  for (const rel of await listFiles(path.join(ASSETS, 'thumbs'), '.jpg')) {
    thumbNames.add(rel.replace(/\.jpg$/, ''));
  }

  // 3. Which content items resolve to an asset?
  const itemAssets = [];
  const missingSprite = [];
  const missingThumb = [];
  const referencedThumbs = new Set();
  const referencedImages = new Set();

  for (const item of bundle.items) {
    const variants = item.img_name
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean);
    const sprites = variants.filter((v) => spriteNames.has(v));
    const thumbs = variants.filter((v) => thumbNames.has(v));
    for (const t of thumbs) referencedThumbs.add(t);

    if (sprites.length === 0) missingSprite.push({ id: item.id, name: item.name, imgName: item.img_name });
    if (thumbs.length === 0) missingThumb.push({ id: item.id, name: item.name, imgName: item.img_name });

    itemAssets.push({
      id: item.id,
      name: item.name,
      imgName: item.img_name,
      sprites,
      thumbs,
      resolved: sprites.length > 0 || thumbs.length > 0,
    });
  }

  // 4. The config's sounds and localised images.
  const config = JSON.parse(
    await readFile(path.join(ROOT, 'upstream/socialwarriors/config/main.json'), 'utf8'),
  );
  const soundFiles = new Set(sounds.map((s) => path.basename(s.path).replace(/\.mp3$/, '')));

  const soundRefs = [];
  const missingSounds = [];
  for (const sound of config.sounds ?? []) {
    const resolved = soundFiles.has(sound.file);
    soundRefs.push({ id: sound.id, file: sound.file, resolved, description: sound.description });
    if (!resolved) missingSounds.push(sound);
  }

  const imagePaths = new Set(images.map((i) => i.path));
  const imageRefs = [];
  const missingImages = [];
  for (const [imagePath, language] of Object.entries(config.images ?? {})) {
    // The config stores a language-relative path ("/chapters/chapter_1.jpg") and
    // the language beside it; the file on disk is assets/images/<lang>/<path>.
    const relative = imagePath.startsWith('/') ? imagePath.slice(1) : imagePath;
    const candidates = [
      `images/${language}/${relative}`,
      `images/${relative}`,
    ];
    const resolvedPath = candidates.find((c) => imagePaths.has(c)) ?? null;
    imageRefs.push({ path: relative, language, resolved: resolvedPath !== null, file: resolvedPath });
    if (resolvedPath) referencedImages.add(resolvedPath);
    else missingImages.push({ path: relative, language });
  }

  // 5. What is present but unreferenced?
  const unreferencedThumbs = [...thumbNames].filter((n) => !referencedThumbs.has(n)).sort();
  const unreferencedImages = images
    .map((i) => i.path)
    .filter((p) => p.startsWith('images/') && !referencedImages.has(p))
    .sort();
  const unreferencedSounds = sounds
    .map((s) => path.basename(s.path).replace(/\.mp3$/, ''))
    .filter((n) => !soundFiles.has(n) || !config.sounds?.some((s) => s.file === n))
    .sort();

  // The sprites the content never names. These are either alternate poses
  // (the `_m`, `_w`, `_old` variants) or art the config simply does not use.
  const referencedSprites = new Set();
  for (const entry of itemAssets) {
    for (const sprite of entry.sprites) referencedSprites.add(sprite);
  }
  const unreferencedSprites = [...spriteNames].filter((n) => !referencedSprites.has(n)).sort();

  const manifest = {
    note:
      'The non-SWF asset manifest. Every image and sound in the vendored tree, ' +
      'cross-referenced against the content bundle, so the missing and the ' +
      'unreferenced are both explicit. Produced by scripts/build-asset-manifest.mjs.',
    counts: {
      images: images.length,
      sounds: sounds.length,
      contentItems: bundle.items.length,
      itemsWithASprite: bundle.items.length - missingSprite.length,
      itemsWithAThumbnail: bundle.items.length - missingThumb.length,
      itemsFullyResolved: itemAssets.filter((i) => i.resolved).length,
      configSoundRefs: soundRefs.length,
      configImageRefs: imageRefs.length,
      missingSprites: missingSprite.length,
      missingThumbnails: missingThumb.length,
      missingSounds: missingSounds.length,
      missingImages: missingImages.length,
      unreferencedThumbnails: unreferencedThumbs.length,
      unreferencedImages: unreferencedImages.length,
      unreferencedSounds: unreferencedSounds.length,
      unreferencedSprites: unreferencedSprites.length,
      missingReferences: missingSprite.length + missingThumb.length + missingSounds.length + missingImages.length,
    },
    images,
    sounds,
    itemAssets,
    soundRefs,
    imageRefs,
    missing: { sprites: missingSprite, thumbnails: missingThumb, sounds: missingSounds, images: missingImages },
    unreferenced: { sprites: unreferencedSprites, thumbnails: unreferencedThumbs, images: unreferencedImages, sounds: unreferencedSounds },
  };

  await writeFile(OUT, JSON.stringify(manifest, null, 1) + '\n', 'utf8');

  console.log('');
  console.log(`content items       : ${manifest.counts.contentItems}`);
  console.log(`  with a sprite     : ${manifest.counts.itemsWithASprite}`);
  console.log(`  with a thumbnail  : ${manifest.counts.itemsWithAThumbnail}`);
  console.log(`  fully resolved    : ${manifest.counts.itemsFullyResolved}`);
  console.log(`missing sprites     : ${missingSprite.length}`);
  console.log(`missing thumbnails  : ${missingThumb.length}`);
  console.log(`missing sounds      : ${missingSounds.length} of ${soundRefs.length}`);
  console.log(`missing images      : ${missingImages.length} of ${imageRefs.length}`);
  console.log(`unreferenced thumbs : ${unreferencedThumbs.length}`);
  console.log(`unreferenced images : ${unreferencedImages.length}`);
  console.log(`unreferenced sounds : ${unreferencedSounds.length}`);
  console.log(`\nwrote ${OUT}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
