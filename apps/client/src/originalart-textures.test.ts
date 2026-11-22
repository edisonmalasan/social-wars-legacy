/**
 * Tests for the original-art texture adapter.
 *
 * The adapter is JSX-free and imports only `@swl/art/browser`, so Node's
 * native TypeScript stripper can load it here. `@swl/art` is intentionally
 * not a declared dependency of the client (Vite aliases the subpath), so the
 * same resolve hook the gallery's test uses maps it to the browser entry.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve as resolvePath } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { registerHooks } from 'node:module';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolvePath(HERE, '../../..');
const BROWSER_ENTRY = resolvePath(ROOT, 'packages/art/browser.ts');

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === '@swl/art/browser') {
      return { url: pathToFileURL(BROWSER_ENTRY).href, shortCircuit: true };
    }
    return nextResolve(specifier, context);
  },
});

const art = await import('./originalart-textures.ts');

const svgOf = (src: string): string => {
  assert.ok(src.startsWith(art.SVG_DATA_PREFIX), 'the motif is an inline SVG data URL');
  return decodeURIComponent(src.slice(art.SVG_DATA_PREFIX.length));
};

describe('the original-art adapter', () => {
  it('carries the generator CC0 constants', () => {
    assert.equal(art.ORIGINAL_ART_LICENCE, 'CC0-1.0');
    assert.equal(art.SVG_DATA_PREFIX, 'data:image/svg+xml;charset=utf-8,');
    assert.ok(art.DEFAULT_MOTIFS.length > 0);
    for (const motif of art.DEFAULT_MOTIFS) {
      assert.equal(motif.licence, 'CC0-1.0');
      assert.ok(motif.id.length > 0);
    }
    assert.equal(new Set(art.DEFAULT_MOTIFS.map((m) => m.id)).size, art.DEFAULT_MOTIFS.length);
  });

  it('encodes SVG as a data URL with no raw markup or external file', () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>';
    const uri = art.svgDataUri(svg);
    assert.ok(uri.startsWith(art.SVG_DATA_PREFIX));
    assert.equal(decodeURIComponent(uri.slice(art.SVG_DATA_PREFIX.length)), svg);
    assert.ok(!uri.includes('<'), 'markup is escaped, not embedded raw');
    assert.ok(!uri.includes(' '), 'whitespace is encoded');
  });

  it('maps an identity deterministically', () => {
    const identity = { itemId: 42, swfName: 'assets.swf', symbol: 'DefineSprite_4', frame: 3 };
    const first = art.motifFor(identity);
    assert.ok(first, 'the default catalogue is not empty');
    assert.deepEqual(art.motifFor(identity), first, 'the same identity gives the same motif');
    // Field order is not part of the identity.
    const reordered = { frame: 3, symbol: 'DefineSprite_4', swfName: 'assets.swf', itemId: 42 };
    assert.deepEqual(art.motifFor(reordered), first);
    // Every motif the identity can reach is a default motif.
    assert.ok(art.DEFAULT_MOTIFS.includes(first));
  });

  it('accepts a richer catalogue without changing the contract', () => {
    const later = {
      id: 'later-castle',
      svg: '<svg/>',
      src: art.svgDataUri('<svg/>'),
      licence: 'CC0-1.0' as const,
    };
    const map = art.createMotifMapper([later]);
    assert.deepEqual(map({ itemId: 1 }), later);
    assert.deepEqual(map({ id: 'anything', frame: 7 }), later);
    assert.equal(art.createMotifMapper([])({ itemId: 1 }), null);
  });

  it('produces motifs with no external references', () => {
    for (const motif of art.DEFAULT_MOTIFS) {
      const svg = svgOf(motif.src);
      assert.equal(svg, motif.svg);
      assert.match(svg, /^<\?xml version="1\.0" encoding="UTF-8"\?>\n<svg\b/);
      assert.match(svg, /xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
      for (const external of [
        /<image\b/i, /<foreignObject\b/i, /\bhref\s*=/i, /\bxlink:/i,
        /\burl\s*\(/i, /@import/i, /\bhttps?:\/\/(?!www\.w3\.org\/2000\/svg)/i,
        /\/atlases\//i, /\.png\b/i, /\.jpe?g\b/i, /\.gif\b/i, /\.swf\b/i,
      ]) {
        assert.ok(!external.test(svg), `${motif.id} references an external resource: ${external}`);
      }
    }
  });

  it('reads the art mode from art-mode.json without probing an atlas', () => {
    assert.equal(art.resolveArtMode({ mode: 'original', licence: 'CC0-1.0' }), 'original');
    assert.equal(art.resolveArtMode({ mode: 'atlas', licence: 'CC0-1.0' }), 'atlas');
    assert.equal(art.resolveArtMode(null), 'atlas', 'a missing file keeps the atlas path');
    assert.equal(art.resolveArtMode(undefined), 'atlas');
    assert.equal(art.resolveArtMode({}), 'atlas');
    assert.equal(art.resolveArtMode({ mode: 'ORIGINAL' }), 'atlas');
  });

  it('still requests atlas pages when art-mode.json says atlas', () => {
    // This is the atlas-mode half of the mode contract: a config that says
    // `atlas` selects a mode in which the renderer's page request is allowed.
    const mode = art.resolveArtMode({ mode: 'atlas', licence: 'CC0-1.0' });
    assert.equal(mode, 'atlas');
    assert.equal(art.atlasPageRequest(mode, 'atlas-0000.png', new Set()), 'atlas-0000.png');
    assert.equal(
      art.atlasPageRequest(mode, 'atlas-0000.png', new Set(['atlas-0000.png'])),
      null,
      'a page already loaded, pending or missing is not requested twice',
    );
    // Original art mode never allows a page request, so it cannot 404.
    assert.equal(art.atlasPageRequest('original', 'atlas-0000.png', new Set()), null);
  });

  it('is inert: no clock, no roll, no fetch and no platform import', () => {
    const source = readFileSync(
      fileURLToPath(new URL('./originalart-textures.ts', import.meta.url)),
      'utf8',
    );
    for (const forbidden of [
      /\bfrom\s*['"]node:/, /\bimport\s*['"]node:/,
      /\bMath\.random\b/, /\bDate\.now\b/, /\bfetch\s*\(/,
      /\bdocument\b/, /\bwindow\b/, /\.swf\b/i,
    ]) {
      assert.ok(!forbidden.test(source), `${forbidden} must not appear in the adapter`);
    }
  });
});
