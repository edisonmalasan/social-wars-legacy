import assert from 'node:assert/strict';
import test from 'node:test';
import { buildArtifacts } from './artifacts.ts';
import { run } from './cli.ts';
import { equalBytes } from './manifest.ts';
import { recordingIO } from './testing.ts';

const ROOT = '/virtual/assets/original';

test('two generations give the same paths and the same bytes', () => {
  const first = buildArtifacts();
  const second = buildArtifacts();
  assert.deepEqual(
    first.map((file) => file.path),
    second.map((file) => file.path),
  );
  assert.equal(first.length, 54); // 46 SVG + 6 WAV + the notice + the manifest
  for (let i = 0; i < first.length; i += 1) {
    const a = first[i];
    const b = second[i];
    assert.ok(a && b);
    assert.ok(equalBytes(a.bytes, b.bytes), `${a.path} changed between generations`);
  }
});

test('two CLI writes produce byte-identical trees', async () => {
  const first = recordingIO();
  const second = recordingIO();
  assert.equal(await run([], first.io, ROOT), 0);
  assert.equal(await run([], second.io, ROOT), 0);
  assert.deepEqual(first.writes.map((w) => w.path), second.writes.map((w) => w.path));
  for (let i = 0; i < first.writes.length; i += 1) {
    const a = first.writes[i];
    const b = second.writes[i];
    assert.ok(a && b);
    assert.ok(equalBytes(a.bytes, b.bytes), `${a.path} changed between writes`);
  }
});

test('the CLI check accepts a tree it has just written', async () => {
  const written = recordingIO();
  assert.equal(await run([], written.io, ROOT), 0);
  const files = new Map(written.writes.map((w) => [w.path, w.bytes]));
  const checked = recordingIO(files);
  assert.equal(await run(['--check'], checked.io, ROOT), 0);
  assert.deepEqual(checked.reads, [...files.keys()]);
  assert.deepEqual(checked.writes, []);
});

test('the CLI check refuses a tree with a changed byte', async () => {
  const written = recordingIO();
  await run([], written.io, ROOT);
  const files = new Map(written.writes.map((w) => [w.path, w.bytes]));
  const first = written.writes[0];
  assert.ok(first);
  files.set(first.path, new Uint8Array([...first.bytes, 0]));
  const checked = recordingIO(files);
  assert.equal(await run(['--check'], checked.io, ROOT), 1);
});
