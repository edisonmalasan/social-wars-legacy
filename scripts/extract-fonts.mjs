#!/usr/bin/env node
/**
 * Group D — the fonts.
 *
 * The client embeds two fonts as SWF font libraries:
 *
 *   assets/fonts/en_ArialRoundedBold.swf   -> "Arial Rounded MT Bold"
 *   assets/fonts/en_KomikaAxis.swf         -> a Zynga display face
 *
 * Both are **proprietary**, and the roadmap requires them to be replaced
 * with permissively-licensed equivalents whose metrics are tuned to
 * match. Tuning needs the original metrics *measured*, so this script
 * extracts the embedded TrueType font and reads its metrics out.
 *
 * FFDec can export the font directly (`-export font` produces a TTF),
 * which is the only lossless way to get at the outlines and the
 * advance widths.
 *
 * Usage:
 *   node scripts/extract-fonts.mjs
 */
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { promisify } from 'node:util';

import { parseFont } from './lib/ttf.ts';

const execFileAsync = promisify(execFile);

const ROOT = process.cwd();
const FONT_DIR = path.join(ROOT, 'upstream/socialwarriors/assets/fonts');
const WORK = path.join(ROOT, '.work/fonts');
const OUT = path.join(ROOT, 're/data/fonts.json');

const DEFAULT_FFDEC =
  process.env.FF_DEC ||
  'C:/Users/Edison/AppData/Local/Temp/opencode/socialwarriors/tools/ffdec/ffdec-cli.exe';

/**
 * The open-licensed substitutes, and why.
 *
 * The substitute has to carry the same *feel*, so the metric tuning is
 * a scale factor rather than a redesign.
 */
const SUBSTITUTES = {
  'en_ArialRoundedBold.swf': {
    substitute: 'Nunito',
    licence: 'SIL Open Font License 1.1',
    url: 'https://fonts.google.com/specimen/Nunito',
    note:
      'A rounded, heavy geometric sans, the closest open-licensed match for ' +
      'Arial Rounded MT Bold. The substitute is scaled to match the original ' +
      "advance widths rather than used at its own size, so the game's text " +
      'fits the same boxes.',
  },
  'en_KomikaAxis.swf': {
    substitute: 'Rubik Mono One',
    licence: 'SIL Open Font License 1.1',
    url: 'https://fonts.google.com/specimen/Rubik+Mono+One',
    note:
      'A wide, display-oriented face, matching the game\'s title and heading ' +
      'style. The Komika Axis face is used only for headings and large ' +
      'labels, so the substitution affects a small part of the interface.',
  },
};

async function main() {
  if (!existsSync(DEFAULT_FFDEC)) {
    console.error(`FFDec not found at ${DEFAULT_FFDEC}`);
    console.error('Set FF_DEC to the path of ffdec-cli.exe.');
    process.exit(2);
  }
  await mkdir(WORK, { recursive: true });

  const sources = (await readdir(FONT_DIR)).filter((f) => f.endsWith('.swf'));
  const fonts = [];

  for (const source of sources) {
    const outDir = path.join(WORK, source.replace(/\.swf$/, ''));
    await rm(outDir, { recursive: true, force: true });
    await mkdir(outDir, { recursive: true });

    console.log(`extracting ${source} ...`);
    await execFileAsync(DEFAULT_FFDEC, ['-export', 'font', outDir, path.join(FONT_DIR, source)], {
      cwd: ROOT,
      timeout: 300_000,
      maxBuffer: 32 * 1024 * 1024,
    });

    const files = (await readdir(outDir)).filter((f) => f.toLowerCase().endsWith('.ttf'));
    if (files.length === 0) {
      console.warn(`  ! no font was extracted from ${source}`);
      continue;
    }

    for (const file of files) {
      const buffer = await readFile(path.join(outDir, file));
      const metrics = parseFont(buffer);
      const substitute = SUBSTITUTES[source] ?? null;

      fonts.push({
        source: `fonts/${source}`,
        extracted: file,
        bytes: buffer.length,
        sha256: createHash('sha256').update(buffer).digest('hex'),
        familyName: metrics.familyName,
        fullName: metrics.fullName,
        postScriptName: metrics.postScriptName,
        unitsPerEm: metrics.unitsPerEm,
        ascender: metrics.ascender,
        descender: metrics.descender,
        lineGap: metrics.lineGap,
        numGlyphs: metrics.numGlyphs,
        coveredCharacters: metrics.coveredCharacters.length,
        // The advance widths of the printable ASCII range, which is the bulk
        // of the game's text. They are the numbers the substitute has to be
        // tuned to match.
        asciiAdvances: Object.fromEntries(
          Array.from({ length: 95 }, (_, i) => {
            const char = String.fromCharCode(32 + i);
            return [char, metrics.advances.get(char) ?? 0];
          }),
        ),
        substitute,
      });

      console.log(
        `  ${metrics.familyName ?? file}: ${metrics.numGlyphs} glyphs, ` +
          `${metrics.coveredCharacters.length} characters covered, ` +
          `upem ${metrics.unitsPerEm}`,
      );
    }
  }

  const manifest = {
    note:
      'The client fonts, extracted and measured. The shipped fonts are ' +
      'proprietary, so each entry records the open-licensed substitute and ' +
      'the original advance widths the substitute has to be tuned to. ' +
      'Produced by scripts/extract-fonts.mjs.',
    counts: { fonts: fonts.length },
    fonts,
  };

  await writeFile(OUT, JSON.stringify(manifest, null, 1) + '\n', 'utf8');
  console.log(`\nwrote ${OUT}`);
  console.log(`extracted fonts: ${WORK}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
