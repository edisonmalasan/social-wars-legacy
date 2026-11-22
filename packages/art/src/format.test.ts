import assert from 'node:assert/strict';
import test from 'node:test';
import { buildArtifacts } from './artifacts.ts';
import { MOTIFS } from './icons.ts';
import { SOUND_SPECS } from './wav.ts';

const artifacts = buildArtifacts();
const text = (path: string): string => new TextDecoder().decode(artifactAt(path).bytes);
const artifactAt = (path: string) => {
  const found = artifacts.find((file) => file.path === path);
  assert.ok(found, `${path} was not generated`);
  return found;
};

test('a CC0 notice accompanies the generated files', () => {
  const notice = text('LICENSE');
  assert.ok(notice.startsWith('CC0 1.0 Universal\n'));
  assert.match(notice, /waived all copyright/);
  assert.match(notice, /creativecommons\.org\/publicdomain\/zero\/1\.0/);
});

test('sixteen distinct icon motifs and one sprite sheet are generated', () => {
  assert.equal(MOTIFS.length, 16);
  assert.equal(new Set(MOTIFS.map((m) => m.id)).size, 16);
  assert.equal(new Set(MOTIFS.map((m) => m.title)).size, 16);
  assert.equal(artifacts.filter((f) => /^icons\/foundry-.*\.svg$/.test(f.path)).length, 16);
  assert.ok(MOTIFS.some((m) => m.kind === 'ui'));
  assert.ok(MOTIFS.some((m) => m.kind === 'unit'));
  assert.ok(artifactAt('icons/sprite-sheet.svg'));
});

test('every SVG has a declaration, a namespaced root and a closing tag', () => {
  const svgs = artifacts.filter((f) => f.path.endsWith('.svg'));
  assert.equal(svgs.length, 46); // 16 icons + 1 sheet + 12 FX frames + 17 gameplay motifs
  for (const file of svgs) {
    const svg = new TextDecoder().decode(file.bytes);
    assert.ok(svg.startsWith('<?xml version="1.0" encoding="UTF-8"?>\n<svg'), file.path);
    assert.ok(svg.includes('xmlns="http://www.w3.org/2000/svg"'), file.path);
    assert.ok(svg.includes('<title id="swl-title">'), file.path);
    assert.ok(svg.includes('<desc id="swl-desc">'), file.path);
    assert.ok(svg.endsWith('</svg>\n'), file.path);
    const opens = (svg.match(/<(svg|g|defs|symbol)\b/g) ?? []).length;
    const closes = (svg.match(/<\/(svg|g|defs|symbol)>/g) ?? []).length;
    assert.equal(opens, closes, `${file.path} has unbalanced container tags`);
  }
});

test('each icon is drawn from primitives rather than an embedded bitmap', () => {
  for (const motif of MOTIFS) {
    const svg = text(`icons/${motif.id}.svg`);
    assert.ok(!svg.includes('<image'), motif.id);
    assert.ok(!svg.includes('data:'), motif.id);
    assert.ok(!svg.includes('<text'), motif.id);
    assert.ok(/<(rect|circle|ellipse|polygon|line|path|g)\b/.test(svg), motif.id);
  }
});

test('the sprite sheet references all sixteen symbols', () => {
  const sheet = text('icons/sprite-sheet.svg');
  for (const motif of MOTIFS) {
    assert.ok(sheet.includes(`<symbol id="swl-${motif.id}"`), motif.id);
    assert.ok(sheet.includes(`<use href="#swl-${motif.id}"`), motif.id);
  }
  assert.equal((sheet.match(/<use /g) ?? []).length, 16);
});

test('six original WAV effects have valid canonical headers', () => {
  assert.equal(SOUND_SPECS.length, 6);
  const waves = artifacts.filter((f) => f.path.endsWith('.wav'));
  assert.equal(waves.length, 6);
  for (const file of waves) {
    const bytes = file.bytes;
    const ascii = (start: number, value: string) =>
      String.fromCharCode(...bytes.subarray(start, start + value.length)) === value;
    assert.ok(bytes.byteLength >= 44, file.path);
    assert.ok(ascii(0, 'RIFF'), file.path);
    assert.ok(ascii(8, 'WAVE'), file.path);
    assert.ok(ascii(12, 'fmt '), file.path);
    assert.ok(ascii(36, 'data'), file.path);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const dataBytes = view.getUint32(40, true);
    assert.equal(view.getUint32(4, true), 36 + dataBytes, file.path);
    assert.equal(view.getUint32(16, true), 16, file.path);
    assert.equal(view.getUint16(20, true), 1, file.path); // PCM
    assert.equal(view.getUint16(22, true), 1, file.path); // mono
    assert.equal(view.getUint32(24, true), 22050, file.path);
    assert.equal(view.getUint16(34, true), 16, file.path);
    assert.equal(bytes.byteLength, 44 + dataBytes, file.path);
    assert.ok(dataBytes > 0 && dataBytes % 2 === 0, file.path);
    let nonzero = false;
    for (let i = 44; i < bytes.byteLength; i += 1) {
      if (bytes[i] !== 0) {
        nonzero = true;
        break;
      }
    }
    assert.ok(nonzero, `${file.path} is silent`);
  }
});
