#!/usr/bin/env node
/**
 * Group D — the substitute fonts.
 *
 * The client's two faces are proprietary, so the clone substitutes
 * **Nunito** for Arial Rounded MT Bold and **Rubik Mono One** for Komika
 * Axis, both under the SIL Open Font License 1.1. This script:
 *
 *   1. downloads the substitutes from Google Fonts,
 *   2. measures their advance widths with the same parser the original
 *      fonts were measured with (`scripts/lib/ttf.ts`),
 *   3. computes the **scale** each substitute needs so that the text
 *      occupies the same width as it did in the original, and
 *   4. writes the scale where the client reads it.
 *
 * The scale is measured, not guessed, and it is measured against the
 * file that actually ships — which is why the download and the
 * measurement happen here rather than in the client.
 *
 * ## The failure is not fatal
 *
 * The client falls back to the platform's own UI font, so a failed
 * download leaves the game playable: the layout shifts and the text
 * still reads. The script therefore keeps whatever it already has and
 * writes a scale of 1 — the "not tuned yet" value the client's model
 * documents — rather than failing the build.
 *
 * Usage:
 *   node scripts/fetch-fonts.mjs
 */
import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { parseFont } from './lib/ttf.ts';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const WORK = path.join(ROOT, '.work/fonts');
const PUBLIC = path.join(ROOT, 'apps/client/public/fonts');
const SCALE_OUT = path.join(ROOT, 'apps/client/public/font-scale.json');
const ORIGINAL_METRICS = path.join(ROOT, 're/data/fonts.json');

/**
 * The substitutes.
 *
 * Each entry is the open-licensed face, the query that fetches it, the
 * weight to fetch, and the **original** it replaces. The original's
 * name is the one the extracted metrics file uses.
 */
const SUBSTITUTES = [
  {
    font: 'ArialRoundedBold',
    substitute: 'Nunito',
    family: 'Nunito',
    weight: 700,
    query: 'Nunito:wght@700',
    original: 'en_ArialRoundedBold',
  },
  {
    font: 'KomikaAxis',
    substitute: 'Rubik Mono One',
    family: 'Rubik Mono One',
    weight: 400,
    query: 'Rubik+Mono+One',
    original: 'en_KomikaAxis',
  },
];

/**
 * The user agent the download uses.
 *
 * Google Fonts serves **TrueType** to an ordinary client and **woff2**
 * to a browser. The build needs both: the TrueType file is what the
 * parser reads, and the woff2 is what the client downloads.
 */
const PLAIN_AGENT = 'social-wars-legacy/1.0 (font build)';
const BROWSER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

/** The file name the client's stylesheet asks for. */
function shippingName(substitute) {
  return `${substitute.substitute.replace(/\s+/g, '')}-${substitute.font}.woff2`;
}

/** The `@font-face` blocks of a stylesheet. */
function fontFaces(css) {
  const blocks = [];
  for (const match of css.matchAll(/@font-face\s*\{([^}]*)\}/g)) {
    const body = match[1];
    const url = /url\((https:[^)]+)\)/.exec(body)?.[1];
    if (!url) continue;
    const range = /unicode-range:\s*([^;]+);/.exec(body)?.[1] ?? '';
    blocks.push({ url, range });
  }
  return blocks;
}

/**
 * The URL of the **latin** subset.
 *
 * The stylesheet lists one URL per subset, and the game draws ASCII,
 * so the subset that covers the basic Latin range is the one to ship.
 */
function latinUrl(css) {
  const blocks = fontFaces(css);
  for (const block of blocks) {
    if (/U\+0000-00FF/i.test(block.range)) return block.url;
  }
  // Without a range, the last URL is the broadest subset.
  return blocks[blocks.length - 1]?.url ?? null;
}

/** The URL of the whole face, for the measurement. */
function plainUrl(css) {
  const blocks = fontFaces(css);
  return blocks[blocks.length - 1]?.url ?? null;
}

async function download(url, agent) {
  const response = await fetch(url, { headers: { 'user-agent': agent } });
  if (!response.ok) throw new Error(`${url} answered ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}

/** The original's advance widths, by the font's name. */
async function originalAdvances() {
  const manifest = JSON.parse(await readFile(ORIGINAL_METRICS, 'utf8'));
  const out = new Map();
  for (const font of manifest.fonts ?? []) {
    const name = font.source.replace(/^fonts\//, '').replace(/\.swf$/, '');
    out.set(name, {
      unitsPerEm: font.unitsPerEm,
      advances: new Map(Object.entries(font.asciiAdvances ?? {})),
    });
  }
  return out;
}

/**
 * The scale a substitute needs.
 *
 * It is the ratio of the two faces' widths over the em, measured over
 * the characters both of them cover. The model's own function does the
 * arithmetic; the script only gathers the numbers.
 */
function scaleOf(original, substitute) {
  let originalTotal = 0;
  let substituteTotal = 0;
  let shared = 0;
  for (const [char, width] of original.advances) {
    const other = substitute.advances.get(char);
    if (other === undefined) continue;
    originalTotal += width;
    substituteTotal += other;
    shared += 1;
  }
  if (shared === 0) return 1;
  const originalEm = originalTotal / original.unitsPerEm;
  const substituteEm = substituteTotal / substitute.unitsPerEm;
  if (substituteEm === 0) return 1;
  const scale = originalEm / substituteEm;
  return Number.isFinite(scale) && scale > 0 ? scale : 1;
}

async function main() {
  await mkdir(WORK, { recursive: true });
  await mkdir(PUBLIC, { recursive: true });

  const originals = await originalAdvances();
  const scales = {};

  for (const substitute of SUBSTITUTES) {
    const shipping = path.join(PUBLIC, shippingName(substitute));
    const measured = path.join(WORK, `${substitute.family.replace(/\s+/g, '')}.ttf`);

    try {
      const css = await (
        await fetch(`https://fonts.googleapis.com/css2?family=${substitute.query}`, {
          headers: { 'user-agent': PLAIN_AGENT },
        })
      ).text();

      const plain = plainUrl(css);
      if (!plain) throw new Error('the stylesheet had no font');
      await writeFile(measured, await download(plain, PLAIN_AGENT));

      const browserCss = await (
        await fetch(`https://fonts.googleapis.com/css2?family=${substitute.query}`, {
          headers: { 'user-agent': BROWSER_AGENT },
        })
      ).text();
      const latin = latinUrl(browserCss);
      if (latin) {
        await writeFile(shipping, await download(latin, BROWSER_AGENT));
      }
    } catch (error) {
      // The client falls back to the platform's own font, so a failed
      // download is not fatal. What matters is whether the file is
      // already there.
      if (!existsSync(shipping) || !existsSync(measured)) {
        console.warn(
          `  ! ${substitute.substitute} could not be fetched: ${String(error).slice(0, 120)}`,
        );
        console.warn('    the client falls back to the platform font.');
        scales[substitute.font] = 1;
        continue;
      }
      console.log(`  ${substitute.substitute}: kept the files already here`);
    }

    const metrics = parseFont(await readFile(measured));
    const original = originals.get(substitute.original);
    if (!original) {
      console.warn(`  ! the original ${substitute.original} has no measured metrics`);
      scales[substitute.font] = 1;
      continue;
    }

    const scale = scaleOf(original, {
      unitsPerEm: metrics.unitsPerEm,
      advances: metrics.advances,
    });
    scales[substitute.font] = Number(scale.toFixed(4));

    console.log(
      `  ${substitute.substitute} replaces ${substitute.original}: ` +
        `the scale is ${scales[substitute.font]}`,
    );
  }

  await writeFile(
    SCALE_OUT,
    JSON.stringify(
      {
        note:
          'The scale each substitute needs, measured against the original ' +
          "font's advance widths. Produced by scripts/fetch-fonts.mjs.",
        scales,
      },
      null,
      1,
    ) + '\n',
    'utf8',
  );
  console.log(`wrote ${SCALE_OUT}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
