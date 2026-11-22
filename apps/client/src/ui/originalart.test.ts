/**
 * Tests for the clean-room Original art gallery.
 *
 * The generator is pure and Node-loadable; the gallery is JSX-free so the
 * native TypeScript stripper can load it here too. `react-dom/server` renders
 * the real component. No browser-only module enters this test's import graph.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve as resolvePath } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { registerHooks, stripTypeScriptTypes } from 'node:module';
import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import { uiCss } from './css.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolvePath(HERE, '../../../..');
const BROWSER_ENTRY = resolvePath(ROOT, 'packages/art/browser.ts');

// @swl/art is a workspace package the client does not depend on, so pnpm does
// not link it. Map the subpath the client uses straight at its browser entry.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === '@swl/art/browser') {
      return { url: pathToFileURL(BROWSER_ENTRY).href, shortCircuit: true };
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.endsWith('.tsx')) {
      const source = readFileSync(fileURLToPath(url), 'utf8');
      return { format: 'module', shortCircuit: true, source: stripTypeScriptTypes(source) };
    }
    return nextLoad(url, context);
  },
});

const art = await import('./originalart.tsx');
const browser = await import('@swl/art/browser');

const DATA_PREFIX = 'data:image/svg+xml;charset=utf-8,';
const svgOf = (src: string): string => {
  assert.ok(src.startsWith(DATA_PREFIX), 'the mark is an inline SVG data URL');
  return decodeURIComponent(src.slice(DATA_PREFIX.length));
};
const markupOf = (close: () => void): string =>
  renderToStaticMarkup(React.createElement(art.OriginalArtGallery, { onClose: close }));

/** Static import/export specifiers, including bare and type-only forms. */
function importsOf(source: string): string[] {
  const found: string[] = [];
  for (const match of source.matchAll(
    /(?:^|\n)\s*(?:import|export)\s+(?:type\s+)?[^;]*?\s+from\s+['"]([^'"]+)['"]/g,
  )) {
    found.push(match[1] ?? '');
  }
  for (const match of source.matchAll(/(?:^|\n)\s*import\s+['"]([^'"]+)['"]/g)) {
    found.push(match[1] ?? '');
  }
  return found;
}

/** Follow the browser entry's relative graph and report any `node:` import. */
function browserGraph(): { seen: Set<string>; offences: string[] } {
  const seen = new Set<string>();
  const offences: string[] = [];
  const visit = (file: string): void => {
    if (seen.has(file)) return;
    seen.add(file);
    const source = readFileSync(file, 'utf8');
    for (const specifier of importsOf(source)) {
      if (specifier.startsWith('node:')) {
        offences.push(`${file} imports ${specifier}`);
        continue;
      }
      if (!specifier.startsWith('.')) continue;
      const base = resolvePath(dirname(file), specifier);
      for (const candidate of [base, `${base}.ts`, `${base}.tsx`]) {
        if (candidate.endsWith('.tsx') && !candidate.endsWith('.test.tsx')) continue;
        try {
          if (readFileSync(candidate, 'utf8') && !candidate.includes('.test.')) {
            visit(candidate);
            break;
          }
        } catch {
          // not a file
        }
      }
    }
  };
  visit(BROWSER_ENTRY);
  return { seen, offences };
}

describe('the browser-safe art entry', () => {
  const graph = browserGraph();

  it('reaches the pure generator modules', () => {
    assert.ok(graph.seen.size >= 6, `only ${graph.seen.size} modules reached`);
    for (const name of ['version.ts', 'random.ts', 'svg.ts', 'icons.ts', 'wav.ts']) {
      assert.ok(
        [...graph.seen].some((file) => file.endsWith(name)),
        `${name} is not in the browser graph`,
      );
    }
  });

  it('has no node: import anywhere in its reachable graph', () => {
    assert.deepEqual(graph.offences, []);
  });

  it('does not reach the filesystem, digest or CLI modules', () => {
    for (const forbidden of ['io.ts', 'manifest.ts', 'artifacts.ts', 'cli.ts', 'index.ts']) {
      assert.ok(
        ![...graph.seen].some((file) => file.endsWith(forbidden)),
        `${forbidden} must not be reachable from the browser entry`,
      );
    }
  });

  it('exposes the generator constants the notice depends on', () => {
    assert.equal(browser.GENERATOR_NAME, '@swl/art');
    assert.equal(browser.GENERATOR_VERSION, '1.0.0');
    assert.equal(browser.LICENCE, 'CC0-1.0');
    assert.match(browser.CC0_NOTICE, /CC0 1\.0 Universal/);
    assert.match(browser.ORIGINAL_WORK_STATEMENT, /No file from the vendored upstream/);
  });
});

describe('the generated marks', () => {
  const marks = art.originalArtMarks();

  it('are the generator\'s own icon artefacts, byte for byte', () => {
    const icons = browser.buildIcons().filter(
      (file) => file.path.startsWith('icons/') && file.path !== 'icons/sprite-sheet.svg',
    );
    assert.equal(marks.length, icons.length);
    const decoder = new TextDecoder();
    marks.forEach((mark, index) => {
      assert.equal(mark.path, icons[index]?.path);
      assert.equal(svgOf(mark.src), decoder.decode(icons[index]!.bytes));
    });
  });

  it('are valid standalone SVG documents with a title and description', () => {
    for (const mark of marks) {
      const svg = svgOf(mark.src);
      assert.match(svg, /^<\?xml version="1\.0" encoding="UTF-8"\?>\n<svg\b/);
      assert.match(svg, /xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
      assert.match(svg, /viewBox="0 0 64 64"/);
      assert.match(svg, /<title\b/);
      assert.match(svg, /<desc\b/);
      assert.equal((svg.match(/<svg\b/g) ?? []).length, 1);
      assert.equal((svg.match(/<\/svg>/g) ?? []).length, 1);
      assert.ok(svg.trimEnd().endsWith('</svg>'));
      assert.ok(mark.title.length > 0);
    }
  });

  it('are deterministic and distinct', () => {
    assert.deepEqual(art.originalArtMarks(), marks, 'the same generator gives the same marks');
    assert.equal(new Set(marks.map((mark) => mark.id)).size, marks.length, 'ids are unique');
    assert.equal(new Set(marks.map((mark) => mark.path)).size, marks.length, 'paths are unique');
    assert.equal(new Set(marks.map((mark) => mark.src)).size, marks.length, 'artwork is unique');
    assert.equal(marks.length, browser.MOTIFS.length, 'one mark per motif');
  });

  it('carry CC0 provenance through the data model', () => {
    for (const mark of marks) {
      assert.match(mark.path, /^icons\/foundry-[a-z]+\.svg$/);
      assert.ok(svgOf(mark.src).includes(art.ORIGINAL_ART_CC0_LINE.split(' · ')[0] ?? 'CC0-1.0') === false,
        'the notice is shown in the gallery chrome, not injected into the artwork');
    }
    assert.match(art.ORIGINAL_ART_CC0_LINE, /^CC0-1\.0 · @swl\/art 1\.0\.0/);
  });
});

describe('the gallery', () => {
  const markup = markupOf(() => {});
  const marks = art.originalArtMarks();

  it('opens as its own descriptor in the one shared dialog', () => {
    assert.deepEqual(art.originalArtDialog(), {
      id: 'original-art',
      kind: 'alert',
      title: 'Original art',
    });
    assert.equal(art.ORIGINAL_ART_DIALOG_ID, 'original-art');
  });

  it('draws only generated inline data, never an external asset', () => {
    const sources = [...markup.matchAll(/\ssrc="([^"]*)"/g)].map((match) => match[1] ?? '');
    assert.equal(sources.length, art.ORIGINAL_ART_MARK_LIMIT);
    assert.deepEqual(
      sources,
      marks.slice(0, art.ORIGINAL_ART_MARK_LIMIT).map((mark) => mark.src),
    );
    assert.ok(sources.every((src) => src.startsWith(DATA_PREFIX)));
    assert.deepEqual([...markup.matchAll(/\shref="([^"]*)"/g)].map((m) => m[1]), []);
    assert.ok(!/(?:src|href)\s*=\s*"https?:/i.test(markup), 'no URL is used as a resource');
    assert.ok(!/url\s*\(/i.test(markup), 'no CSS url() reaches a file');
    for (const forbidden of [
      /\.swf\b/i, /\.png\b/i, /\.jpe?g\b/i, /\.gif\b/i, /\.webp\b/i,
      /upstream\//i, /atlas\//i, /flash\b/i, /shockwave\b/i,
    ]) {
      assert.ok(!forbidden.test(markup), `the gallery must not reference ${forbidden}`);
    }
  });

  it('shows the CC0 notice and the generator provenance', () => {
    assert.match(markup, /data-swl-original-art="gallery"/);
    assert.match(markup, /Original art/);
    assert.match(markup, /data-swl-art-licence="CC0-1\.0"/);
    assert.ok(markup.includes(art.ORIGINAL_ART_CC0_LINE));
    assert.ok(markup.includes('CC0 1.0 Universal'), 'the full CC0 notice is available');
    assert.ok(markup.includes('No file from the vendored upstream'), 'the statement is shown');
    assert.equal(
      [...markup.matchAll(/data-swl-art-generated="true"/g)].length,
      art.ORIGINAL_ART_MARK_LIMIT,
    );
  });

  it('has a launcher that only publishes an open gesture', () => {
    const launcher = renderToStaticMarkup(
      React.createElement(art.OriginalArtLauncher, { onOpen: () => {} }),
    );
    assert.match(launcher, /data-swl-original-art="launcher"/);
    assert.ok(launcher.includes('Original art'));
    assert.ok(launcher.includes(String(browser.MOTIFS.length)));
    assert.ok(!/(?:src|href)\s*=/i.test(launcher), 'the launcher loads no asset');
  });

  it('is inert: no clock, no roll, no fetch and no command', () => {
    const source = readFileSync(
      fileURLToPath(new URL('./originalart.tsx', import.meta.url)),
      'utf8',
    );
    for (const forbidden of [
      /Math\.random/, /Date\.now/, /\bfetch\s*\(/, /\bdispatch\s*\(/,
      /node:/, /react-dom\/client/, /from ['"]\.\/state\.ts['"]/,
    ]) {
      assert.ok(!forbidden.test(source), `${forbidden} must not appear in the gallery`);
    }
    assert.equal(markupOf(() => {}), markupOf(() => {}), 'the same generator draws the same gallery');
  });

  it('has stylesheet rules for every class it emits', () => {
    const css = uiCss();
    for (const className of [
      'swl-original-art-launcher',
      'swl-original-art-grid',
      'swl-original-art-mark',
      'swl-original-art-img',
      'swl-original-art-licence',
      'swl-original-art-details',
      'swl-original-art-close',
    ]) {
      assert.ok(css.includes(`.${className}`), `${className} has no stylesheet rule`);
    }
  });
});
