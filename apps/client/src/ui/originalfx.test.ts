/**
 * Tests for the clean-room Original FX panel.
 *
 * The generator is pure and Node-loadable; the panel is JSX-free so the
 * native TypeScript stripper can load it here too. `react-dom/server`
 * renders the real component. No browser-only module enters this test's
 * import graph.
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
const CLIENT_ENTRY = resolvePath(ROOT, 'apps/client/src/main.ts');

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

const fx = await import('./originalfx.tsx');
const browser = await import('@swl/art/browser');

const DATA_PREFIX = 'data:image/svg+xml;charset=utf-8,';
const svgOf = (src: string): string => {
  assert.ok(src.startsWith(DATA_PREFIX), 'the frame is an inline SVG data URL');
  return decodeURIComponent(src.slice(DATA_PREFIX.length));
};
const markupOf = (close: () => void): string =>
  renderToStaticMarkup(React.createElement(fx.OriginalFxGallery, { onClose: close }));

/** Runtime import/export specifiers; type-only ones do not reach the browser. */
function importsOf(source: string): string[] {
  const found: string[] = [];
  for (const match of source.matchAll(
    /(?:^|\n)\s*(?:import|export)\s+(type\s+)?[^;]*?\s+from\s+['"]([^'"]+)['"]/g,
  )) {
    if (!match[1]) found.push(match[2] ?? '');
  }
  for (const match of source.matchAll(/(?:^|\n)\s*import\s+['"]([^'"]+)['"]/g)) {
    found.push(match[1] ?? '');
  }
  return found;
}

/** The file a runtime specifier resolves to, if it is one of ours. */
function resolveLocal(specifier: string, from: string): string | null {
  if (specifier.startsWith('.')) {
    const base = resolvePath(dirname(from), specifier);
    for (const candidate of [base, `${base}.ts`, `${base}.tsx`, resolvePath(base, 'index.ts')]) {
      try {
        if (readFileSync(candidate, 'utf8') && !candidate.includes('.test.')) return candidate;
      } catch {
        // not a file
      }
    }
    return null;
  }
  if (specifier.startsWith('node:')) return null;
  const workspace: Record<string, string> = {
    '@swl/client': 'packages/client/src/index.ts',
    '@swl/rules': 'packages/rules/src/index.ts',
    '@swl/protocol': 'packages/protocol/src/index.ts',
    '@swl/content': 'packages/content/src/index.ts',
    '@swl/art/browser': 'packages/art/browser.ts',
  };
  if (workspace[specifier]) return resolvePath(ROOT, workspace[specifier] ?? '');
  if (specifier.startsWith('@swl/')) {
    const parts = specifier.split('/');
    const name = (parts[0] ?? '').slice('@swl/'.length);
    const rest = parts.slice(1);
    for (const candidate of [
      resolvePath(ROOT, 'packages', name, 'src', ...rest, 'index.ts'),
      resolvePath(ROOT, 'packages', name, 'src', ...rest) + '.ts',
    ]) {
      try {
        if (readFileSync(candidate, 'utf8') && !candidate.includes('.test.')) return candidate;
      } catch {
        // not a file
      }
    }
  }
  return null;
}

/** Follow a runtime graph from `entry` and report any `node:` import. */
function graphOf(entry: string): { seen: Set<string>; offences: string[] } {
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
      const local = resolveLocal(specifier, file);
      if (local) visit(local);
    }
  };
  visit(entry);
  return { seen, offences };
}

describe('the browser-safe art entry', () => {
  const graph = graphOf(BROWSER_ENTRY);

  it('reaches the pure FX generator alongside the other pure modules', () => {
    assert.ok(graph.seen.size >= 7, `only ${graph.seen.size} modules reached`);
    for (const name of ['version.ts', 'random.ts', 'svg.ts', 'icons.ts', 'fx.ts', 'wav.ts']) {
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
    assert.equal(browser.FX_SEQUENCES.length, 2);
  });
});

describe('the built client graph', () => {
  it('is the graph pnpm lint checks and stays Node-free with FX included', () => {
    const lint = readFileSync(resolvePath(ROOT, 'scripts/lint-project.mjs'), 'utf8');
    assert.match(lint, /'apps\/client\/src\/main\.ts'/, 'pnpm lint checks the client entry');
    const graph = graphOf(CLIENT_ENTRY);
    assert.deepEqual(graph.offences, [], 'the built client must not reach a node: import');
    assert.ok(graph.seen.size > 40, `only ${graph.seen.size} modules reached`);
    assert.ok([...graph.seen].some((file) => file.endsWith('originalfx.tsx')));
    assert.ok([...graph.seen].some((file) => file.endsWith('browser.ts')));
    assert.ok([...graph.seen].some((file) => file.endsWith('fx.ts')));
  });
});

describe('the generated FX frames', () => {
  const sequences = fx.originalFxSequences();
  const frames = sequences.flatMap((sequence) => sequence.frames);

  it('are the generator\'s own frame bytes, byte for byte', () => {
    assert.equal(sequences.length, browser.FX_SEQUENCES.length);
    const decoder = new TextDecoder();
    sequences.forEach((sequence, sequenceIndex) => {
      const spec = browser.FX_SEQUENCES[sequenceIndex];
      assert.ok(spec);
      assert.equal(sequence.id, spec.id);
      assert.equal(sequence.title, spec.title);
      assert.equal(sequence.frameMs, spec.frameMs);
      assert.equal(sequence.frames.length, spec.frames);
      sequence.frames.forEach((frame, index) => {
        assert.equal(frame.index, index);
        assert.equal(frame.path, browser.fxFramePath(sequence.id, index));
        assert.equal(svgOf(frame.src), decoder.decode(new TextEncoder().encode(browser.fxFrameSvg(sequence.id, index))));
      });
    });
  });

  it('are valid standalone SVG documents with a title and description', () => {
    for (const frame of frames) {
      const svg = svgOf(frame.src);
      assert.match(svg, /^<\?xml version="1\.0" encoding="UTF-8"\?>\n<svg\b/);
      assert.match(svg, /xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
      assert.match(svg, /viewBox="0 0 64 64"/);
      assert.match(svg, /<title\b/);
      assert.match(svg, /<desc\b/);
      assert.equal((svg.match(/<svg\b/g) ?? []).length, 1);
      assert.equal((svg.match(/<\/svg>/g) ?? []).length, 1);
      assert.ok(svg.trimEnd().endsWith('</svg>'));
      assert.ok(!svg.includes('<image'));
      assert.ok(!svg.includes('href='));
    }
  });

  it('are deterministic and distinct', () => {
    assert.deepEqual(fx.originalFxSequences(), sequences, 'the same generator gives the same frames');
    assert.equal(new Set(frames.map((frame) => frame.path)).size, frames.length, 'paths are unique');
    assert.equal(new Set(frames.map((frame) => frame.src)).size, frames.length, 'frames are unique');
    for (const sequence of sequences) {
      assert.ok(sequence.frames.length >= 4);
      assert.equal(new Set(sequence.frames.map((frame) => frame.src)).size, sequence.frames.length);
    }
  });

  it('carry CC0 provenance through the data model', () => {
    for (const frame of frames) {
      assert.match(frame.path, /^fx\/[a-z-]+\/frame-\d\d\.svg$/);
    }
    assert.match(fx.ORIGINAL_FX_CC0_LINE, /^CC0-1\.0 · @swl\/art 1\.0\.0/);
  });
});

describe('the FX panel', () => {
  const markup = markupOf(() => {});
  const sequences = fx.originalFxSequences();
  const frames = sequences.flatMap((sequence) => sequence.frames);

  it('opens as its own descriptor in the one shared dialog', () => {
    assert.deepEqual(fx.originalFxDialog(), {
      id: 'original-fx',
      kind: 'alert',
      title: 'Original FX',
    });
    assert.equal(fx.ORIGINAL_FX_DIALOG_ID, 'original-fx');
  });

  it('renders a real frame-cycling CSS animation of generated data', () => {
    assert.match(markup, /data-swl-original-fx="gallery"/);
    assert.equal([...markup.matchAll(/data-swl-fx-stage=/g)].length, sequences.length);
    assert.equal([...markup.matchAll(/data-swl-fx-frame="/g)].length, frames.length);
    assert.equal([...markup.matchAll(/class="swl-original-fx-frame"/g)].length, frames.length);
    assert.equal([...markup.matchAll(/data-swl-fx-first="true"/g)].length, sequences.length);
    for (let index = 0; index < browser.FX_FRAME_COUNT; index += 1) {
      assert.equal([...markup.matchAll(new RegExp(`data-swl-fx-frame="${index}"`, 'g'))].length, 2);
    }
    const css = uiCss();
    assert.match(css, /@keyframes swl-original-fx-cycle/);
    assert.match(css, /animation: swl-original-fx-cycle 1\.2s steps\(1, end\) infinite/);
    assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
    assert.match(css, /\.swl-original-fx-frame\[data-swl-fx-first='true'\] \{ opacity: 1; \}/);
  });

  it('draws only generated inline data, never an external asset', () => {
    const sources = [...markup.matchAll(/\ssrc="([^"]*)"/g)].map((match) => match[1] ?? '');
    assert.equal(sources.length, frames.length);
    assert.deepEqual(sources, frames.map((frame) => frame.src));
    assert.ok(sources.every((src) => src.startsWith(DATA_PREFIX)));
    assert.deepEqual([...markup.matchAll(/\shref="([^"]*)"/g)].map((m) => m[1]), []);
    assert.ok(!/(?:src|href)\s*=\s*"https?:/i.test(markup), 'no URL is used as a resource');
    assert.ok(!/url\s*\(/i.test(markup), 'no CSS url() reaches a file');
    for (const forbidden of [
      /\.swf\b/i, /\.png\b/i, /\.jpe?g\b/i, /\.gif\b/i, /\.webp\b/i,
      /upstream\//i, /atlas\//i, /flash\b/i, /shockwave\b/i,
    ]) {
      assert.ok(!forbidden.test(markup), `the panel must not reference ${forbidden}`);
    }
  });

  it('shows the CC0 notice and the generator provenance', () => {
    assert.match(markup, /Original FX/);
    assert.match(markup, /data-swl-fx-licence="CC0-1\.0"/);
    assert.ok(markup.includes(fx.ORIGINAL_FX_CC0_LINE));
    assert.ok(markup.includes('CC0 1.0 Universal'), 'the full CC0 notice is available');
    assert.ok(markup.includes('No file from the vendored upstream'), 'the statement is shown');
    assert.equal(
      [...markup.matchAll(/data-swl-art-generated="true"/g)].length,
      frames.length,
    );
  });

  it('has a launcher that only publishes an open gesture', () => {
    const launcher = renderToStaticMarkup(
      React.createElement(fx.OriginalFxLauncher, { onOpen: () => {} }),
    );
    assert.match(launcher, /data-swl-original-fx="launcher"/);
    assert.ok(launcher.includes('Original FX'));
    assert.ok(launcher.includes(String(browser.FX_SEQUENCES.length)));
    assert.ok(!/(?:src|href)\s*=/i.test(launcher), 'the launcher loads no asset');
  });

  it('is inert: no clock, no roll, no fetch and no command', () => {
    const source = readFileSync(
      fileURLToPath(new URL('./originalfx.tsx', import.meta.url)),
      'utf8',
    );
    for (const forbidden of [
      /Math\.random/, /Date\.now/, /\bfetch\s*\(/, /\bdispatch\s*\(/,
      /node:/, /react-dom\/client/, /from ['"]\.\/state\.ts['"]/,
    ]) {
      assert.ok(!forbidden.test(source), `${forbidden} must not appear in the panel`);
    }
    assert.equal(markupOf(() => {}), markupOf(() => {}), 'the same generator draws the same panel');
  });

  it('has stylesheet rules for every class it emits', () => {
    const css = uiCss();
    for (const className of [
      'swl-original-fx-launcher',
      'swl-original-fx-launcher-count',
      'swl-original-fx-list',
      'swl-original-fx-sequence',
      'swl-original-fx-stage',
      'swl-original-fx-frame',
      'swl-original-fx-name',
      'swl-original-fx-detail',
      'swl-original-fx-licence',
      'swl-original-fx-details',
      'swl-original-fx-close',
    ]) {
      assert.ok(css.includes(`.${className}`), `${className} has no stylesheet rule`);
    }
  });
});
