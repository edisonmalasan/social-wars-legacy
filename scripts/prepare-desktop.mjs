#!/usr/bin/env node
/**
 * Prepare the desktop shell's build inputs.
 *
 * It writes the shell's **icons** and the **placeholder** the web view
 * loads in development, because Tauri's build needs a `frontendDist` to
 * exist before it will compile, and a Windows build needs an `.ico`
 * besides the `.png`.
 *
 * The icon is the project's own: a dark square with a lighter diagonal,
 * drawn here rather than shipped as a binary nobody can regenerate. The
 * Windows `.ico` is a container whose entry is a PNG, which is what
 * Vista and later read.
 *
 * Usage:
 *   node scripts/prepare-desktop.mjs
 */
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { encodePng } from './lib/png.mjs';

const ROOT = process.cwd();
const ICONS = path.join(ROOT, 'apps/desktop/src-tauri/icons');
const DIST = path.join(ROOT, 'apps/desktop/dist');

/** The icon, at a size. */
function icon(size) {
  const data = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const offset = (y * size + x) * 4;
      // A dark slate field with a lighter diagonal band across it.
      const onBand = Math.abs(x - y) < size * 0.18;
      const edge = x < 2 || y < 2 || x >= size - 2 || y >= size - 2;
      if (edge) {
        data[offset] = 0x1b;
        data[offset + 1] = 0x22;
        data[offset + 2] = 0x30;
        data[offset + 3] = 0xff;
      } else if (onBand) {
        data[offset] = 0xd8;
        data[offset + 1] = 0xa6;
        data[offset + 2] = 0x3c;
        data[offset + 3] = 0xff;
      } else {
        data[offset] = 0x27;
        data[offset + 1] = 0x33;
        data[offset + 2] = 0x44;
        data[offset + 3] = 0xff;
      }
    }
  }
  return { width: size, height: size, data };
}

/** A Windows `.ico` whose single entry is a PNG. */
function ico(png, size) {
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0); // reserved
  header.writeUInt16LE(1, 2); // type: icon
  header.writeUInt16LE(1, 4); // one entry

  const entry = Buffer.alloc(16);
  entry.writeUInt8(size >= 256 ? 0 : size, 0); // width
  entry.writeUInt8(size >= 256 ? 0 : size, 1); // height
  entry.writeUInt8(0, 2); // colours
  entry.writeUInt8(0, 3); // reserved
  entry.writeUInt16LE(1, 4); // planes
  entry.writeUInt16LE(32, 6); // bits per pixel
  entry.writeUInt32LE(png.length, 8); // the size
  entry.writeUInt32LE(header.length + entry.length, 12); // the offset

  return Buffer.concat([header, entry, png]);
}

async function main() {
  await mkdir(ICONS, { recursive: true });

  await writeFile(path.join(ICONS, 'icon.png'), encodePng(icon(512)));
  await writeFile(path.join(ICONS, 'icon.ico'), ico(encodePng(icon(32)), 32));
  await writeFile(path.join(ICONS, '32x32.png'), encodePng(icon(32)));
  await writeFile(path.join(ICONS, '128x128.png'), encodePng(icon(128)));

  // The placeholder the web view loads until the client is built. The
  // real client replaces it.
  await mkdir(DIST, { recursive: true });
  await writeFile(
    path.join(DIST, 'index.html'),
    [
      '<!doctype html>',
      '<html>',
      '  <head>',
      '    <meta charset="utf-8" />',
      '    <title>Social Wars Legacy</title>',
      '  </head>',
      '  <body>',
      '    <div id="game"></div>',
      '  </body>',
      '</html>',
      '',
    ].join('\n'),
    'utf8',
  );

  console.log('wrote the desktop icons and the placeholder');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
