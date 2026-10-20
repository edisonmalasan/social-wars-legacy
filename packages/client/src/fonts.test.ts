import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  CLIENT_FONTS,
  CLIENT_FONT_LANGUAGES,
  FONT_LANGUAGES,
  FONT_SUBSTITUTES,
  hasFontsFor,
  loadedFonts,
  measure,
  measurePixels,
  scaleFor,
  type OriginalFontMetrics,
} from './fonts.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function originalMetrics(): Promise<OriginalFontMetrics> {
  const manifest = JSON.parse(
    await readFile(path.join(repoRoot(), 're/data/fonts.json'), 'utf8'),
  ) as {
    fonts: {
      source: string;
      familyName: string;
      unitsPerEm: number;
      ascender: number;
      descender: number;
      asciiAdvances: Record<string, number>;
    }[];
  };
  const out: OriginalFontMetrics = {};
  for (const font of manifest.fonts ?? []) {
    const name = font.source.replace(/^fonts\//, '').replace(/\.swf$/, '');
    out[name] = {
      family: font.familyName,
      unitsPerEm: font.unitsPerEm,
      ascender: font.ascender,
      descender: font.descender,
      advances: font.asciiAdvances,
    };
  }
  return out;
}

describe('the font substitutes', () => {
  it('cover every client font', () => {
    for (const font of CLIENT_FONTS) {
      const substitute = FONT_SUBSTITUTES[font];
      assert.ok(substitute, `${font} has no substitute`);
      assert.ok(substitute.licence.includes('Open Font License'));
      assert.ok(substitute.url.startsWith('https://'));
    }
  });

  it('are the two the roadmap chose', () => {
    assert.equal(FONT_SUBSTITUTES.ArialRoundedBold.name, 'Nunito');
    assert.equal(FONT_SUBSTITUTES.KomikaAxis.name, 'Rubik Mono One');
  });

  it('are served under the names the client asks for', () => {
    const fonts = loadedFonts();
    assert.equal(fonts.length, CLIENT_FONTS.length);
    for (const font of fonts) {
      assert.ok(font.file.includes(font.name));
      assert.ok(font.file.endsWith('.woff2'));
    }
  });
});

describe('the languages', () => {
  it('are the three the client loads fonts for', () => {
    assert.deepEqual([...CLIENT_FONT_LANGUAGES], ['en', 'tr', 'el']);
  });

  it('ship only the English ones, as the original does', () => {
    assert.deepEqual([...FONT_LANGUAGES], ['en']);
    assert.equal(hasFontsFor('en'), true);
    assert.equal(hasFontsFor('tr'), false);
    assert.equal(hasFontsFor('el'), false);
  });
});

describe('the measurement', () => {
  it('adds the advance widths', async () => {
    const metrics = await originalMetrics();
    const arial = metrics['en_ArialRoundedBold']!;
    const one = measure(arial, 'A');
    const two = measure(arial, 'AA');
    assert.equal(two, one * 2);
    assert.ok(one > 0);
  });

  it('counts a character the font does not cover as zero', async () => {
    const metrics = await originalMetrics();
    const arial = metrics['en_ArialRoundedBold']!;
    assert.equal(measure(arial, '中'), 0);
  });

  it('scales the width', async () => {
    const metrics = await originalMetrics();
    const arial = metrics['en_ArialRoundedBold']!;
    const plain = measure(arial, 'Hello');
    assert.equal(measure(arial, 'Hello', 2), plain * 2);
  });

  it('turns the design units into pixels at a size', async () => {
    const metrics = await originalMetrics();
    const arial = metrics['en_ArialRoundedBold']!;
    const units = measure(arial, 'Hello');
    const pixels = measurePixels(arial, 'Hello', 12);
    assert.equal(pixels, (units * 12) / arial.unitsPerEm);
  });

  it('computes the scale a substitute needs', () => {
    // The substitute is 600 units wide where the original is 500, so it has
    // to be scaled by 500/600 to occupy the same space.
    assert.equal(scaleFor(500, 600), 500 / 600);
    // A zero width cannot be scaled, so the scale is 1.
    assert.equal(scaleFor(0, 600), 1);
  });
});

describe('the real metrics', () => {
  it('cover the printable ASCII range for both faces', async () => {
    const metrics = await originalMetrics();
    const arial = metrics['en_ArialRoundedBold'];
    const komika = metrics['en_KomikaAxis'];
    assert.ok(arial, 'the Arial metrics are missing');
    assert.ok(komika, 'the Komika metrics are missing');
    for (const [name, font] of Object.entries(metrics)) {
      assert.ok(font.unitsPerEm > 0, `${name} has no units per em`);
      assert.ok((font.advances[' '] ?? 0) > 0, `${name} has no space`);
      assert.ok((font.advances['A'] ?? 0) > 0, `${name} has no A`);
      assert.ok(
        (font.advances['W'] ?? 0) > (font.advances['i'] ?? 0),
        `${name}'s widths look wrong`,
      );
    }
  });
});
