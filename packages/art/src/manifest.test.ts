import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { buildArtifacts } from './artifacts.ts';
import { equalBytes, sha256, type ProvenanceManifest } from './manifest.ts';
import { GENERATOR_VERSION, LICENCE, ORIGINAL_WORK_STATEMENT } from './version.ts';

const artifacts = buildArtifacts();
const manifestFile = artifacts.find((file) => file.path === 'manifest.json');
assert.ok(manifestFile);
const manifestBytes = manifestFile.bytes;
const manifest = JSON.parse(new TextDecoder().decode(manifestBytes)) as ProvenanceManifest;

test('the manifest carries the licence, the version and an original-work statement', () => {
  assert.equal(manifest.licence, LICENCE);
  assert.equal(manifest.licence, 'CC0-1.0');
  assert.equal(manifest.generatorVersion, GENERATOR_VERSION);
  assert.equal(manifest.statement, ORIGINAL_WORK_STATEMENT);
  assert.match(manifest.statement, /^Original work:/);
  assert.match(manifest.method, /No input file is read/);
});

test('every generated file has a complete provenance entry', () => {
  const files = artifacts.filter((file) => file.path !== 'manifest.json');
  assert.equal(manifest.files.length, files.length);
  assert.equal(manifest.files.length, 24); // 16 icons + 1 sheet + 6 sounds + the notice
  for (const file of files) {
    const entry = manifest.files.find((row) => row.path === file.path);
    assert.ok(entry, `${file.path} has no entry`);
    assert.equal(entry.bytes, file.bytes.byteLength, file.path);
    assert.equal(entry.sha256, sha256(file.bytes), file.path);
    assert.match(entry.sha256, /^[0-9a-f]{64}$/, file.path);
    assert.equal(entry.licence, 'CC0-1.0', file.path);
    assert.equal(entry.generatorVersion, GENERATOR_VERSION, file.path);
    assert.equal(entry.statement, ORIGINAL_WORK_STATEMENT, file.path);
    assert.ok(!nodePathIsAbsolute(entry.path), file.path);
  }
});

function nodePathIsAbsolute(path: string): boolean {
  return path.startsWith('/') || /^[A-Za-z]:[\\/]/.test(path);
}

test('every file has a distinct hash', () => {
  const hashes = manifest.files.map((entry) => entry.sha256);
  assert.equal(new Set(hashes).size, hashes.length);
});

test('the committed manifest is exactly what a fresh generation produces', async () => {
  const onDisk = await readFile(new URL('../../../assets/original/manifest.json', import.meta.url));
  assert.ok(equalBytes(new Uint8Array(onDisk), manifestBytes));
});
