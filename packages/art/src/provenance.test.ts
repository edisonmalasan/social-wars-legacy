import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import nodePath from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { run } from './cli.ts';
import { recordingIO } from './testing.ts';

const SRC = fileURLToPath(new URL('.', import.meta.url));
const ROOT = nodePath.resolve('/virtual/original');

/** Patterns that would mean the generator was reading somebody else's art. */
const FORBIDDEN = [
  /upstream\s*[/\\]/i,
  /\bre\s*[/\\]\s*(?:docs|evidence|data)\b/i,
  /Basesec/i,
  /\.(?:swf|fla|atlas|png|jpe?g|mp3|ogg|ttf|otf)\b/i,
  /Date\s*\.\s*now\s*\(/,
  /Math\s*\.\s*random\s*\(/,
];

test('no generator source names a prohibited input or reads a file', async () => {
  const names = (await readdir(SRC)).filter((name) => name.endsWith('.ts') && !name.endsWith('.test.ts'));
  assert.ok(names.length >= 9, `only ${names.length} source modules found`);
  for (const name of names) {
    const source = await readFile(nodePath.join(SRC, name), 'utf8');
    for (const pattern of FORBIDDEN) {
      assert.ok(!pattern.test(source), `${name} contains a prohibited reference: ${pattern}`);
    }
    // io.ts is the only production module that may read; testing.ts is the
    // filesystem double the tests hand to it.
    if (name !== 'io.ts' && name !== 'testing.ts') {
      assert.ok(!source.includes('readFile('), `${name} reads a file`);
      assert.ok(!/from\s+['"]node:fs/.test(source), `${name} imports the filesystem`);
    }
  }
});

test('generation opens no input file at all', async () => {
  const recorded = recordingIO();
  assert.equal(await run([], recorded.io, ROOT), 0);
  assert.deepEqual(recorded.reads, []);
  assert.ok(recorded.writes.length >= 25);
  for (const write of recorded.writes) {
    const relative = nodePath.relative(ROOT, write.path);
    assert.ok(relative && !relative.startsWith('..') && !nodePath.isAbsolute(relative), write.path);
    assert.ok(!relative.toLowerCase().includes('upstream'), write.path);
    assert.ok(!/(^|[/\\])re([/\\]|$)/.test(relative), write.path);
  }
});

test('verification reads only the generator’s own output tree', async () => {
  const written = recordingIO();
  assert.equal(await run([], written.io, ROOT), 0);
  const files = new Map(written.writes.map((write) => [write.path, write.bytes]));
  const checked = recordingIO(files);
  assert.equal(await run(['--check'], checked.io, ROOT), 0);
  assert.equal(checked.reads.length, files.size);
  for (const path of checked.reads) {
    const relative = nodePath.relative(ROOT, path);
    assert.ok(relative && !relative.startsWith('..') && !nodePath.isAbsolute(relative), path);
    const lower = nodePath.resolve(path).toLowerCase();
    assert.ok(!lower.includes('upstream'), path);
    assert.ok(!lower.includes('evidence'), path);
    assert.ok(!lower.includes('docs'), path);
  }
});
