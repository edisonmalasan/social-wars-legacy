import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve as resolvePath } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import * as browser from '../browser.ts';
import { buildArtifacts } from './artifacts.ts';
import { run } from './cli.ts';
import {
  GAMEPLAY_CATEGORIES,
  GAMEPLAY_FALLBACK_KEY,
  buildGameplayArt,
  gameplayArtFor,
  gameplayArtPath,
  gameplayKey,
  gameplayKeys,
  type GameplayCategory,
  type GameplayContentProps,
} from './gameplay.ts';
import { equalBytes, sha256, type ProvenanceManifest } from './manifest.ts';
import { recordingIO } from './testing.ts';
import { LICENCE, ORIGINAL_WORK_STATEMENT } from './version.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const BROWSER_ENTRY = resolvePath(HERE, '../browser.ts');
const ROOT = '/virtual/original';

const decoder = new TextDecoder();
const artifacts = buildArtifacts();
const gameplayArtifacts = artifacts.filter((file) => file.path.startsWith('gameplay/'));
const manifestFile = artifacts.find((file) => file.path === 'manifest.json');
assert.ok(manifestFile);
const manifest = JSON.parse(decoder.decode(manifestFile.bytes)) as ProvenanceManifest;

test('there are at least ten distinct gameplay categories across every family', () => {
  const keys = gameplayKeys();
  assert.ok(keys.length >= 10, `only ${keys.length} categories`);
  assert.equal(keys.length, GAMEPLAY_CATEGORIES.length);
  assert.equal(new Set(keys).size, keys.length, 'keys are unique');
  assert.equal(new Set(GAMEPLAY_CATEGORIES.map((spec) => spec.title)).size, keys.length, 'titles are unique');
  const kinds = new Set(GAMEPLAY_CATEGORIES.map((spec) => spec.kind));
  for (const kind of ['terrain', 'building', 'unit', 'marker', 'fx']) {
    assert.ok(kinds.has(kind as never), `no ${kind} motifs`);
  }
  assert.ok(keys.includes(GAMEPLAY_FALLBACK_KEY));
  for (const spec of GAMEPLAY_CATEGORIES) {
    assert.ok(spec.width > 0 && spec.height > 0, spec.key);
    assert.ok(spec.description.length > 0, spec.key);
  }
});

test('every category has one distinct, stable generated path', () => {
  const paths = GAMEPLAY_CATEGORIES.map((spec) => gameplayArtPath(spec.key));
  assert.equal(new Set(paths).size, paths.length);
  assert.deepEqual(paths, gameplayArtifacts.map((file) => file.path));
  for (const path of paths) assert.match(path, /^gameplay\/[a-z-]+(?:\/[a-z-]+)?\.svg$/);
});

test('gameplay art is byte-for-byte deterministic', () => {
  for (const spec of GAMEPLAY_CATEGORIES) {
    const first = gameplayArtFor(spec.key);
    const second = gameplayArtFor(spec.key);
    assert.equal(first, second, `${spec.key} changed between calls`);
    const generated = gameplayArtifacts.find((file) => file.path === gameplayArtPath(spec.key));
    assert.ok(generated, spec.key);
    assert.equal(decoder.decode(generated.bytes), first, `${spec.key} differs from the CLI output`);
  }
  const first = buildGameplayArt();
  const second = buildGameplayArt();
  assert.deepEqual(first.map((file) => file.path), second.map((file) => file.path));
  for (let i = 0; i < first.length; i += 1) {
    assert.ok(equalBytes(first[i]!.bytes, second[i]!.bytes), `file ${i} changed`);
  }
});

test('every motif is a valid standalone SVG with inherent size and no external references', () => {
  for (const spec of GAMEPLAY_CATEGORIES) {
    const svg = gameplayArtFor(spec.key);
    assert.ok(svg.startsWith('<?xml version="1.0" encoding="UTF-8"?>\n<svg'), spec.key);
    assert.ok(svg.includes('xmlns="http://www.w3.org/2000/svg"'), spec.key);
    assert.ok(svg.includes(`viewBox="0 0 ${spec.width} ${spec.height}"`), spec.key);
    assert.ok(svg.includes(`width="${spec.width}" height="${spec.height}"`), spec.key);
    assert.ok(svg.includes('<title id="swl-title">'), spec.key);
    assert.ok(svg.includes('<desc id="swl-desc">'), spec.key);
    assert.ok(svg.endsWith('</svg>\n'), spec.key);
    assert.equal((svg.match(/<svg\b/g) ?? []).length, 1, spec.key);
    assert.equal((svg.match(/<\/svg>/g) ?? []).length, 1, spec.key);
    assert.equal((svg.match(/<g\b/g) ?? []).length, (svg.match(/<\/g>/g) ?? []).length, spec.key);
    assert.ok(/<(rect|circle|ellipse|polygon|line|path|g)\b/.test(svg), spec.key);
    for (const forbidden of [/\bhref\s*=/i, /url\s*\(/i, /<image\b/i, /data:/i, /<text\b/i, /xlink/i]) {
      assert.ok(!forbidden.test(svg), `${spec.key} has an external reference or embedded media: ${forbidden}`);
    }
    if (spec.tileable) {
      assert.ok(spec.background, spec.key);
      assert.ok(svg.includes(`x="0" y="0" width="${spec.width}" height="${spec.height}"`), spec.key);
      assert.equal((svg.match(/<g\b/g) ?? []).length, 9, `${spec.key} must wrap to all eight neighbours`);
    } else {
      assert.ok(
        !svg.includes(`x="0" y="0" width="${spec.width}" height="${spec.height}"`),
        `${spec.key} must have a transparent background`,
      );
    }
  }
});

test('all motifs are distinct from one another', () => {
  const svgs = GAMEPLAY_CATEGORIES.map((spec) => gameplayArtFor(spec.key));
  assert.equal(new Set(svgs).size, svgs.length);
});

test('neutral content properties, not art names, select a motif', () => {
  const cases: ReadonlyArray<readonly [GameplayContentProps, GameplayCategory]> = [
    [{ groupType: 'HOUSING' }, 'building.housing'],
    [{ groupType: 'WOOD_FACTORY' }, 'building.workshop'],
    [{ groupType: 'wood factory' }, 'building.workshop'],
    [{ type: 'b', subcategoryId: 11 }, 'building.housing'],
    [{ type: 'b', subcategoryId: 12 }, 'building.workshop'],
    [{ type: 'b', groupType: 'FARM' }, 'building.farm'],
    [{ type: 'u', groupType: 'CAVALRY' }, 'unit.mounted'],
    [{ type: 'u', subcategoryId: 32 }, 'unit.ranged'],
    [{ type: 'u' }, 'unit.infantry'],
    [{ type: 'b' }, 'building.housing'],
    [{ type: 'b', subcategoryId: 32 }, 'building.housing'],
    [{ type: 'u', subcategoryId: 12 }, 'unit.infantry'],
    [{ categoryId: 1 }, 'building.housing'],
    [{ categoryId: 2 }, 'unit.infantry'],
    [{ categoryId: 99 }, GAMEPLAY_FALLBACK_KEY],
    [{ key: 'terrain/water' }, 'terrain.water'],
    [{ key: 'gameplay:building.tower' }, 'building.tower'],
    [{ key: 'wood.factory' }, 'building.workshop'],
    [{ key: 'marker.selection' }, 'marker.selection'],
  ];
  for (const [props, expected] of cases) {
    assert.equal(gameplayKey(props), expected, JSON.stringify(props));
  }
  // The object form is the renderer's direct entry point for content items.
  assert.equal(gameplayArtFor({ groupType: 'HOUSING' }), gameplayArtFor('building.housing'));
  assert.equal(gameplayArtPath({ type: 'u', groupType: 'ARCHER' }), 'gameplay/unit/ranged.svg');
});

test('an unknown or empty key falls back to the neutral badge, never throws', () => {
  for (const key of ['', '   ', 'nonsense', 'art-derived-name', 'swf:something']) {
    assert.equal(gameplayKey({ key }), GAMEPLAY_FALLBACK_KEY, JSON.stringify(key));
    assert.equal(gameplayArtFor(key), gameplayArtFor(GAMEPLAY_FALLBACK_KEY));
  }
  assert.equal(gameplayKey({}), GAMEPLAY_FALLBACK_KEY);
  assert.equal(gameplayArtFor({}), gameplayArtFor('fallback'));
  assert.equal(gameplayArtFor({ groupType: 'MADE_UP' }), gameplayArtFor('fallback'));
});

test('the generator reads no input file and writes only inside its own tree', async () => {
  const recorded = recordingIO();
  assert.equal(await run([], recorded.io, ROOT), 0);
  assert.deepEqual(recorded.reads, []);
  for (const write of recorded.writes) {
    const relative = write.path.slice(ROOT.length + 1).replace(/\\/g, '/');
    assert.ok(!relative.startsWith('..'), write.path);
    assert.ok(!/(^|\/)upstream(\/|$)/i.test(relative), write.path);
    assert.ok(!/(^|\/)re(\/|$)/i.test(relative), write.path);
  }
});

test('every gameplay file has a CC0-1.0 provenance entry with the right digest', () => {
  assert.equal(gameplayArtifacts.length, GAMEPLAY_CATEGORIES.length);
  for (const file of gameplayArtifacts) {
    const entry = manifest.files.find((row) => row.path === file.path);
    assert.ok(entry, `${file.path} has no manifest entry`);
    assert.equal(entry.licence, LICENCE, file.path);
    assert.equal(entry.licence, 'CC0-1.0', file.path);
    assert.equal(entry.statement, ORIGINAL_WORK_STATEMENT, file.path);
    assert.equal(entry.bytes, file.bytes.byteLength, file.path);
    assert.equal(entry.sha256, sha256(file.bytes), file.path);
    assert.match(entry.sha256, /^[0-9a-f]{64}$/, file.path);
  }
});

/** Static import/export specifiers, including the browser entry's star exports. */
function specifiersOf(source: string): string[] {
  const found: string[] = [];
  for (const match of source.matchAll(
    /(?:^|\n)\s*(?:import|export)\s+[^;]*?\s+from\s+['"]([^'"]+)['"]/g,
  )) {
    found.push(match[1] ?? '');
  }
  return found;
}

test('the browser entry exposes the gameplay API without pulling in a node: module', () => {
  const seen = new Set<string>();
  const offences: string[] = [];
  const visit = (file: string): void => {
    if (seen.has(file)) return;
    seen.add(file);
    for (const specifier of specifiersOf(readFileSync(file, 'utf8'))) {
      if (specifier.startsWith('node:')) {
        offences.push(`${file} imports ${specifier}`);
        continue;
      }
      if (specifier.startsWith('.')) visit(resolvePath(dirname(file), specifier));
    }
  };
  visit(BROWSER_ENTRY);

  assert.deepEqual(offences, []);
  assert.ok([...seen].some((file) => file.endsWith('gameplay.ts')), 'gameplay.ts is not in the browser graph');
  for (const forbidden of ['io.ts', 'manifest.ts', 'artifacts.ts', 'cli.ts', 'index.ts']) {
    assert.ok(![...seen].some((file) => file.endsWith(forbidden)), `${forbidden} must not be reachable`);
  }
  assert.equal(browser.GAMEPLAY_FALLBACK_KEY, GAMEPLAY_FALLBACK_KEY);
  assert.deepEqual(browser.gameplayKeys(), gameplayKeys());
  assert.equal(browser.gameplayArtFor('terrain.grass'), gameplayArtFor('terrain.grass'));
});

test('the gameplay module itself has no node import or prohibited input reference', () => {
  const source = readFileSync(resolvePath(HERE, 'gameplay.ts'), 'utf8');
  for (const forbidden of [
    /node:/,
    /Date\s*\.\s*now\s*\(/,
    /Math\s*\.\s*random\s*\(/,
    /readFile\s*\(/,
    /img[_-]?name/i,
    /\bswf\b/i,
    /\batlas\b/i,
  ]) {
    assert.ok(!forbidden.test(source), `gameplay.ts contains ${forbidden}`);
  }
});
