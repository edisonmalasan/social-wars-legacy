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

  it('builds a CC0 gameplay catalogue with distinct, prefixed ids', () => {
    assert.ok(art.GAMEPLAY_MOTIFS.length >= 10);
    const ids = art.GAMEPLAY_MOTIFS.map((motif) => motif.id);
    assert.equal(new Set(ids).size, ids.length, 'gameplay ids are unique');
    const svgs = art.GAMEPLAY_MOTIFS.map((motif) => motif.svg);
    assert.equal(new Set(svgs).size, svgs.length, 'each gameplay category has its own motif');
    const galleryIds = new Set(art.DEFAULT_MOTIFS.map((motif) => motif.id));
    for (const motif of art.GAMEPLAY_MOTIFS) {
      assert.equal(motif.licence, 'CC0-1.0');
      assert.ok(motif.id.startsWith(art.GAMEPLAY_MOTIF_PREFIX));
      assert.ok(!galleryIds.has(motif.id), 'a gameplay motif cannot shadow a gallery icon id');
      assert.ok(motif.src.startsWith(art.SVG_DATA_PREFIX));
      assert.equal(svgOf(motif.src), motif.svg);
    }
    assert.equal(art.GAMEPLAY_MOTIFS.length, 17, 'all 17 gameplay categories are exposed');
  });

  it('maps sample gameplay content to the expected motif families', () => {
    const cases = [
      [{ key: 'terrain.grass' }, 'gameplay:terrain.grass'],
      [{ key: 'terrain/water' }, 'gameplay:terrain.water'],
      [{ key: 'gameplay:terrain.path' }, 'gameplay:terrain.path'],
      [{ key: 'marker.selection' }, 'gameplay:marker.selection'],
      [{ key: 'marker.highlight' }, 'gameplay:marker.highlight'],
      [{ key: 'fx.impact' }, 'gameplay:fx.impact'],
      [{ groupType: 'HOUSING' }, 'gameplay:building.housing'],
      [{ groupType: 'WOOD_FACTORY' }, 'gameplay:building.workshop'],
      [{ type: 'b', groupType: 'FARM' }, 'gameplay:building.farm'],
      [{ type: 'b', subcategoryId: 14 }, 'gameplay:building.storage'],
      [{ type: 'b', subcategoryId: 15 }, 'gameplay:building.tower'],
      [{ type: 'u', groupType: 'CAVALRY' }, 'gameplay:unit.mounted'],
      [{ type: 'u', groupType: 'ARCHER' }, 'gameplay:unit.ranged'],
      [{ type: 'u', subcategoryId: 34 }, 'gameplay:unit.worker'],
      [{ type: 'u', categoryId: 2 }, 'gameplay:unit.infantry'],
    ] as const;
    for (const [identity, expectedId] of cases) {
      const motif = art.motifFor(identity);
      assert.ok(motif, JSON.stringify(identity));
      assert.equal(motif.id, expectedId, JSON.stringify(identity));
      assert.equal(motif.licence, 'CC0-1.0');
      assert.ok(motif.src.startsWith(art.SVG_DATA_PREFIX));
      assert.deepEqual(art.motifFor(identity), motif, 'a repeat lookup is identical');
    }
  });

  it('selects gameplay motifs from neutral properties, never art-derived names', () => {
    const neutral = { type: 'b', groupType: 'HOUSING' };
    const withArtNames = {
      ...neutral,
      id: 'map-element-7',
      itemId: 99,
      frame: 'frame_12',
      swfName: 'presentation.swf',
      symbol: 'DefineSprite_4',
      atlasX: 128,
      atlasY: 256,
    };
    const first = art.motifFor(neutral);
    const second = art.motifFor(withArtNames);
    assert.ok(first && second);
    assert.equal(second.id, first.id);
    assert.equal(second.id, 'gameplay:building.housing');

    // The renderer's current identity (id/frame/atlas only) has no neutral
    // properties, so it stays on the gallery fallback and still rasterises.
    const artOnly = { id: 'x', frame: 'f', swfName: 's', symbol: 'y', atlasX: 1, atlasY: 2 };
    const fallback = art.motifFor(artOnly);
    assert.ok(fallback);
    assert.ok(art.DEFAULT_MOTIFS.includes(fallback), 'no gameplay motif is chosen from art names');
    assert.deepEqual(art.motifFor(artOnly), fallback);
  });

  it('keeps unknown identities on the deterministic seeded fallback', () => {
    const mapper = art.createMotifMapper(art.DEFAULT_MOTIFS);
    const unknowns = [
      {},
      { id: 42, frame: 3 },
      { key: 'nonsense' },
      { key: 'swf:something', groupType: 'MADE_UP' },
      { id: 'a', atlasX: 4, atlasY: 9 },
    ];
    for (const identity of unknowns) {
      const motif = art.motifFor(identity);
      assert.ok(motif);
      assert.equal(motif.id, mapper(identity)?.id, 'the FNV fallback is unchanged');
      assert.ok(art.DEFAULT_MOTIFS.includes(motif));
      assert.deepEqual(art.motifFor(identity), motif);
    }
    // Field order is not part of the fallback identity.
    const a = { itemId: 1, frame: 2, swfName: 'p', symbol: 'q' };
    const b = { symbol: 'q', frame: 2, itemId: 1, swfName: 'p' };
    assert.equal(art.motifFor(a)?.id, art.motifFor(b)?.id);
  });

  it('exposes a pure gameplay selector with a null fallback', () => {
    const byProps = art.gameplayMotifFor({ type: 'u', groupType: 'CAVALRY' });
    assert.equal(byProps?.id, 'gameplay:unit.mounted');
    assert.deepEqual(art.gameplayMotifFor({ type: 'u', groupType: 'CAVALRY' }), byProps);
    assert.equal(art.gameplayMotifFor('terrain.stone')?.id, 'gameplay:terrain.stone');
    assert.equal(art.gameplayMotifFor('fallback'), null);
    assert.equal(art.gameplayMotifFor({}), null);
    assert.equal(art.gameplayMotifFor(null), null);
    assert.equal(art.gameplayMotifFor(undefined), null);
    for (const motif of art.GAMEPLAY_MOTIFS) {
      const key = motif.id.slice(art.GAMEPLAY_MOTIF_PREFIX.length);
      if (key === 'fallback') continue;
      assert.deepEqual(art.gameplayMotifFor(key), motif);
    }
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
    for (const motif of [...art.DEFAULT_MOTIFS, ...art.GAMEPLAY_MOTIFS]) {
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
