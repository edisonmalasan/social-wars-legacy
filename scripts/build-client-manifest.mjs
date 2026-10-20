#!/usr/bin/env node
/**
 * Build the client's manifest.
 *
 * The asset pipeline's manifest holds **every** image the client's SWFs
 * contain: 254 155 images and 41 198 symbols, 155 MB of JSON. The
 * browser does not need any of it - the game draws a few hundred items,
 * and the art for the other 40 000 symbols is never on screen.
 *
 * So the client gets its own manifest, holding only the symbols the
 * **content's items** refer to, and only the images those symbols'
 * frames use. The atlas regions are copied as they are, so the client
 * looks the art up exactly the way the pipeline recorded it.
 *
 * The saving is **measured**, not asserted: the script prints both sizes
 * and the ratio, and the test checks that the client's manifest is
 * smaller than the pipeline's by a wide margin.
 *
 * Usage:
 *   node scripts/build-client-manifest.mjs
 */
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();
const SOURCE = path.join(ROOT, 're/data/frame-manifest.json');
const CONTENT = path.join(ROOT, 'packages/content/dist/content-bundle.json');
const OUT = path.join(ROOT, 'apps/client/public/frame-manifest.json');

async function main() {
  if (!existsSync(SOURCE)) {
    console.error(`there is no manifest at ${SOURCE}`);
    console.error('Run the asset pipeline first.');
    process.exit(1);
  }

  const manifest = JSON.parse(await readFile(SOURCE, 'utf8'));
  const content = JSON.parse(await readFile(CONTENT, 'utf8'));

  // The names the content's items ask for.
  const wanted = new Set();
  for (const item of content.items ?? []) {
    if (item && typeof item.img_name === 'string' && item.img_name) {
      wanted.add(item.img_name);
    }
  }

  // The symbols whose SWF carries one of those names.
  const symbols = [];
  const images = {};
  let keptImages = 0;
  const seen = new Set();

  for (const symbol of manifest.symbols ?? []) {
    const swf = String(symbol.swf ?? '');
    const name = swf.slice(swf.lastIndexOf('/') + 1).replace(/\.swf$/, '');
    if (!wanted.has(name)) continue;
    // Only the **root** symbol of the SWF is needed.
    //
    // The client instantiates the sheet itself and picks the drawing by
    // its frame number:
    //
    // ```as3
    // // core/isoengine/IsoElement.as:906-916
    // this.currentSheet = new Base.Main.sheetDictionary[img_name]();
    // this.bmd = this.currentSheet;
    // this.bmd.gotoAndStop(buildingReference.frame + 1);
    // ```
    //
    // So the sheet is the SWF's root, and the other symbols in it - the
    // variants and the construction states - are never drawn.
    if (seen.has(swf)) continue;
    seen.add(swf);

    const frames = [];
    for (const frame of symbol.frames ?? []) {
      const image = manifest.images?.[frame.image];
      if (!image) continue;
      if (!Object.prototype.hasOwnProperty.call(images, frame.image)) {
        images[frame.image] = image;
        keptImages += 1;
      }
      frames.push(frame);
    }
    if (frames.length === 0) continue;

    symbols.push({
      swf: symbol.swf,
      symbol: symbol.symbol,
      frameCount: symbol.frameCount,
      uniqueFrames: symbol.uniqueFrames,
      frames,
    });
  }

  const trimmed = {
    note:
      "The client's manifest: only the symbols the content's items refer to, " +
      'and only the images those symbols use. Produced by ' +
      'scripts/build-client-manifest.mjs from the asset pipeline manifest.',
    counts: {
      symbols: symbols.length,
      images: keptImages,
    },
    images,
    symbols,
    atlases: manifest.atlases ?? null,
  };

  await writeFile(OUT, JSON.stringify(trimmed), 'utf8');

  // The content bundle travels with it: the client and the server then
  // agree on the content by construction, because there is one bundle.
  await writeFile(
    path.join(ROOT, 'apps/client/public/content-bundle.json'),
    JSON.stringify(content),
    'utf8',
  );

  const before = JSON.stringify(manifest).length;
  const after = JSON.stringify(trimmed).length;
  console.log(`wrote ${OUT}`);
  console.log(
    `  the symbols: ${manifest.symbols?.length ?? 0} -> ${symbols.length}`,
  );
  console.log(
    `  the images:  ${Object.keys(manifest.images ?? {}).length} -> ${keptImages}`,
  );
  console.log(
    `  the size:    ${(before / 1e6).toFixed(1)} MB -> ${(after / 1e6).toFixed(1)} MB ` +
      `(${(after / before * 100).toFixed(1)}%)`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
