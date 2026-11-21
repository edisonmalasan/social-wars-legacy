#!/usr/bin/env node
/**
 * Prepare the desktop shell's build inputs.
 *
 * It writes the shell's **icons** (Tauri needs them for a Windows build)
 * and copies the **built web client** into `frontendDist`, so the shell
 * ships the real game rather than an empty page.
 *
 * The icon is the project's own: a dark square with a lighter diagonal,
 * drawn here rather than shipped as a binary nobody can regenerate. The
 * Windows `.ico` is a container whose entry is a PNG, which is what
 * Vista and later read.
 *
 * `--icons-only` writes just the icons. CI uses it before it builds the
 * client, and calls this script again afterwards to copy the real page.
 *
 * Usage:
 *   node scripts/prepare-desktop.mjs [--icons-only]
 */
import { cp, mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { encodePng } from './lib/png.mjs';

const ROOT = process.cwd();
const ICONS = path.join(ROOT, 'apps/desktop/src-tauri/icons');
const DIST = path.join(ROOT, 'apps/desktop/dist');
const CLIENT_DIST = path.join(ROOT, 'apps/client/dist');
const ICONS_ONLY = process.argv.includes('--icons-only');

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

/** The real client's page, rather than the old placeholder. */
async function assertRealClient(index) {
  const html = await readFile(index, 'utf8');
  const problems = [];
  if (!/<script\b/i.test(html)) {
    problems.push('there is no script tag: this is the placeholder, not the built client');
  }
  if (!/src\s*=\s*["']\.?\/?assets\//i.test(html)) {
    problems.push('the page does not load the built client from ./assets/');
  }
  if (problems.length > 0) {
    throw new Error(
      `the copied client is not the built web client:\n  ${problems.join('\n  ')}\n` +
        'Run: pnpm --filter @swl/app-client build',
    );
  }
}

/** Replace the shell's frontend with the built client. */
async function copyClient() {
  const entry = path.join(CLIENT_DIST, 'index.html');
  let present = false;
  try {
    present = (await stat(entry)).isFile();
  } catch {
    present = false;
  }
  if (!present) {
    throw new Error(
      'the web client has not been built, so the shell would ship a placeholder.\n' +
        'Run: pnpm --filter @swl/app-client build',
    );
  }
  // A fresh copy, so a removed asset from an earlier build cannot ship.
  await rm(DIST, { recursive: true, force: true });
  await cp(CLIENT_DIST, DIST, { recursive: true });
  await assertRealClient(path.join(DIST, 'index.html'));
}

async function main() {
  await mkdir(ICONS, { recursive: true });

  await writeFile(path.join(ICONS, 'icon.png'), encodePng(icon(512)));
  await writeFile(path.join(ICONS, 'icon.ico'), ico(encodePng(icon(32)), 32));
  await writeFile(path.join(ICONS, '32x32.png'), encodePng(icon(32)));
  await writeFile(path.join(ICONS, '128x128.png'), encodePng(icon(128)));

  if (ICONS_ONLY) {
    // Tauri needs a frontendDist to compile even before the client is
    // built. This mode is for that early CI step only; the real copy
    // happens once the client exists.
    await mkdir(DIST, { recursive: true });
    console.log('wrote the desktop icons (client copy skipped)');
    return;
  }

  await copyClient();
  console.log('wrote the desktop icons and copied the built web client');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
