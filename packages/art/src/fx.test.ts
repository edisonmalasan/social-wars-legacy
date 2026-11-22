/**
 * Tests for the original FX generator.
 *
 * Everything here reads the generator's own bytes: SVG validity,
 * determinism, distinctness and CC0 provenance. No image library and no
 * browser is needed, and no input art is consulted.
 */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { buildArtifacts } from './artifacts.ts';
import {
  buildFxFrames,
  FX_FRAME_COUNT,
  FX_FRAME_MS,
  FX_SEQUENCES,
  fxFramePath,
  fxFrameSvg,
  fxSequence,
} from './fx.ts';
import { sha256, type ProvenanceManifest } from './manifest.ts';
import { GENERATOR_VERSION, LICENCE, ORIGINAL_WORK_STATEMENT } from './version.ts';

const frameSvgs = (): string[] =>
  FX_SEQUENCES.flatMap((sequence) =>
    Array.from({ length: sequence.frames }, (_, index) => fxFrameSvg(sequence.id, index)),
  );

test('two original sequences of at least four deterministic frames exist', () => {
  assert.ok(FX_SEQUENCES.length >= 2);
  assert.equal(new Set(FX_SEQUENCES.map((sequence) => sequence.id)).size, FX_SEQUENCES.length);
  assert.equal(new Set(FX_SEQUENCES.map((sequence) => sequence.title)).size, FX_SEQUENCES.length);
  for (const sequence of FX_SEQUENCES) {
    assert.equal(sequence.frames, FX_FRAME_COUNT);
    assert.ok(sequence.frames >= 4, `${sequence.id} has too few frames`);
    assert.equal(sequence.frameMs, FX_FRAME_MS);
    assert.ok(sequence.frameMs > 0);
    assert.ok(sequence.title.length > 0 && sequence.description.length > 0);
    assert.equal(fxSequence(sequence.id), sequence);
  }
});

test('every frame is a valid standalone SVG document from original geometry', () => {
  for (const sequence of FX_SEQUENCES) {
    for (let index = 0; index < sequence.frames; index += 1) {
      const svg = fxFrameSvg(sequence.id, index);
      const where = `${sequence.id} frame ${index}`;
      assert.ok(svg.startsWith('<?xml version="1.0" encoding="UTF-8"?>\n<svg'), where);
      assert.ok(svg.includes('xmlns="http://www.w3.org/2000/svg"'), where);
      assert.ok(svg.includes('viewBox="0 0 64 64"'), where);
      assert.ok(svg.includes('<title id="swl-title">'), where);
      assert.ok(svg.includes('<desc id="swl-desc">'), where);
      assert.ok(svg.includes(`${sequence.title} — frame ${index + 1} of ${sequence.frames}`), where);
      assert.ok(svg.endsWith('</svg>\n'), where);
      assert.equal((svg.match(/<svg\b/g) ?? []).length, 1, where);
      assert.equal((svg.match(/<\/svg>/g) ?? []).length, 1, where);
      const opens = (svg.match(/<(svg|g|defs|symbol)\b/g) ?? []).length;
      const closes = (svg.match(/<\/(svg|g|defs|symbol)>/g) ?? []).length;
      assert.equal(opens, closes, `${where} has unbalanced container tags`);
      assert.match(svg, /<(circle|polygon|line|rect|path)\b/, where);
      for (const forbidden of ['<image', 'data:', '<text', 'href=', '<use', '<script']) {
        assert.ok(!svg.includes(forbidden), `${where} contains ${forbidden}`);
      }
    }
  }
});

test('a frame is reproducible on its own, under the seed', () => {
  for (const sequence of FX_SEQUENCES) {
    for (let index = 0; index < sequence.frames; index += 1) {
      assert.equal(fxFrameSvg(sequence.id, index), fxFrameSvg(sequence.id, index));
    }
  }
  const first = buildFxFrames();
  const second = buildFxFrames();
  assert.deepEqual(first.map((file) => file.path), second.map((file) => file.path));
  for (let i = 0; i < first.length; i += 1) {
    assert.deepEqual(first[i]?.bytes, second[i]?.bytes);
  }
});

test('every frame and every sequence is visually distinct', () => {
  const frames = frameSvgs();
  assert.equal(frames.length, FX_SEQUENCES.length * FX_FRAME_COUNT);
  assert.equal(new Set(frames).size, frames.length, 'two frames are identical');
  for (const sequence of FX_SEQUENCES) {
    const own = Array.from({ length: sequence.frames }, (_, i) => fxFrameSvg(sequence.id, i));
    assert.equal(new Set(own).size, own.length, `${sequence.id} repeats a frame`);
  }
  const bySequence = FX_SEQUENCES.map((sequence) =>
    new Set(Array.from({ length: sequence.frames }, (_, i) => fxFrameSvg(sequence.id, i))),
  );
  for (let i = 0; i < bySequence.length; i += 1) {
    for (let j = i + 1; j < bySequence.length; j += 1) {
      for (const svg of bySequence[i] ?? []) {
        assert.ok(!(bySequence[j] ?? new Set()).has(svg), 'sequences share a frame');
      }
    }
  }
});

test('bad sequence ids and frame indices fail loudly', () => {
  assert.throws(() => fxSequence('not-a-sequence'), /unknown FX sequence/);
  assert.throws(() => fxFrameSvg(FX_SEQUENCES[0]!.id, -1), /FX frame out of range/);
  assert.throws(() => fxFrameSvg(FX_SEQUENCES[0]!.id, FX_FRAME_COUNT), /FX frame out of range/);
});

test('FX frames are generated artefacts with CC0 provenance', () => {
  const artifacts = buildArtifacts();
  const manifestFile = artifacts.find((file) => file.path === 'manifest.json');
  assert.ok(manifestFile);
  const manifest = JSON.parse(new TextDecoder().decode(manifestFile.bytes)) as ProvenanceManifest;
  assert.equal(manifest.licence, LICENCE);

  const frames = buildFxFrames();
  assert.equal(frames.length, FX_SEQUENCES.length * FX_FRAME_COUNT);
  for (const frame of frames) {
    assert.match(frame.path, /^fx\/[a-z-]+\/frame-\d\d\.svg$/);
    const artifact = artifacts.find((file) => file.path === frame.path);
    assert.ok(artifact, `${frame.path} is not a generated artefact`);
    assert.deepEqual(artifact.bytes, frame.bytes);
    const entry = manifest.files.find((row) => row.path === frame.path);
    assert.ok(entry, `${frame.path} has no manifest entry`);
    assert.equal(entry.bytes, frame.bytes.byteLength);
    assert.equal(entry.sha256, sha256(frame.bytes));
    assert.match(entry.sha256, /^[0-9a-f]{64}$/);
    assert.equal(entry.licence, 'CC0-1.0');
    assert.equal(entry.generatorVersion, GENERATOR_VERSION);
    assert.equal(entry.statement, ORIGINAL_WORK_STATEMENT);
  }
});

test('the committed manifest lists every generated FX frame', async () => {
  const onDisk = await readFile(new URL('../../../assets/original/manifest.json', import.meta.url));
  const manifest = JSON.parse(new TextDecoder().decode(onDisk)) as ProvenanceManifest;
  const listed = new Set(manifest.files.map((entry) => entry.path));
  for (const frame of buildFxFrames()) {
    assert.ok(listed.has(frame.path), `${frame.path} is missing from the committed manifest`);
  }
});
