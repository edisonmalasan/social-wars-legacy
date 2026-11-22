/**
 * Tests for the independently authored neutral content seed.
 *
 * The seed is a sample, not the shipped bundle. These tests prove that it is
 * internally reproducible, that it carries no reference-derived tokens or
 * filenames, that the isolation guard fires, and that adding the seed has not
 * changed the bundle the shipped build consumes.
 */
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import { buildContent, canonicalise } from './build.ts';

const execFileAsync = promisify(execFile);

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const SEED = path.join(ROOT, 'content', 'neutral', 'v1');
const CHECK = path.join(ROOT, 'scripts', 'check-neutral-content.mjs');
const BUNDLE = path.join(ROOT, 'packages', 'content', 'dist', 'content-bundle.json');

interface BuildInput {
  readonly path: string;
  readonly sha256: string;
}

interface Provenance {
  readonly specVersion: string;
  readonly specRevision: string;
  readonly authoringMethod: string;
  readonly licence: string;
  readonly artGenerator: string;
  readonly statement: string;
  readonly buildInputs: readonly BuildInput[];
}

async function readJson<T>(file: string): Promise<T> {
  return JSON.parse(await readFile(file, 'utf8')) as T;
}

/** Files in a directory tree, with POSIX-style relative paths. */
async function filesUnder(dir: string, prefix = ''): Promise<string[]> {
  const out: string[] = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) out.push(...(await filesUnder(path.join(dir, entry.name), relative)));
    else if (entry.isFile()) out.push(relative);
  }
  return out;
}

test('the seed validates and validates deterministically', async () => {
  const first = await execFileAsync(process.execPath, [CHECK], { cwd: ROOT });
  const second = await execFileAsync(process.execPath, [CHECK], { cwd: ROOT });
  assert.equal(first.stderr, '');
  assert.equal(first.stdout, second.stdout);
  assert.match(first.stdout, /neutral content seed OK \(v1\)/);
  assert.match(first.stdout, /OK: validation passed/);
  assert.doesNotMatch(first.stdout, /not valid/);

  // The recorded per-file hashes and the spec revision are independently
  // recomputed here, not just trusted from the check script's own output.
  const provenance = await readJson<Provenance>(path.join(SEED, 'provenance.json'));
  assert.equal(provenance.specVersion, 'v1');
  assert.equal(provenance.authoringMethod, 'clean-room-authorship');
  assert.equal(provenance.licence, 'CC0-1.0');
  assert.equal(provenance.buildInputs.length, 5);
  const lines: string[] = [];
  for (const input of provenance.buildInputs) {
    const bytes = await readFile(path.join(SEED, input.path));
    const digest = createHash('sha256').update(bytes).digest('hex');
    assert.equal(digest, input.sha256, `${input.path} has drifted`);
    lines.push(`${input.path}:${input.sha256}`);
  }
  const revision = createHash('sha256').update(`${lines.sort().join('\n')}\n`).digest('hex');
  assert.equal(provenance.specRevision, revision);

  const notice = await readFile(path.join(SEED, 'LICENSE-CC0.txt'), 'utf8');
  assert.match(notice, /CC0 1\.0/i);
  assert.match(notice, /waiv/i);
});

test('the seed contains no proprietary tokens or upstream filenames', async () => {
  const forbidden: readonly RegExp[] = [
    /Basesec/i,
    /\.swf\b/i,
    /\.fla\b/i,
    /\.atlas\b/i,
    /\.(?:ttf|otf|mp3|ogg)\b/i,
    /\bmain\.json\b/i,
    /\bpatches\.txt\b/i,
    /\bitem-delegate-map\.json\b/i,
    /\bquests\.json\b/i,
    /BuildingWindow\.as\b/i,
    /Quest03DefendConvoyAuto\b/i,
    /\bZynga\b/i,
    /Arial[ _-]?Rounded|Komika/i,
    /upstream\s*[/\\]/i,
    /\bre\s*[/\\]\s*(?:docs|data|evidence)\b/i,
  ];
  const files = await filesUnder(SEED);
  assert.ok(files.length >= 6, `only ${files.length} seed files found`);
  for (const file of files) {
    const text = await readFile(path.join(SEED, file), 'utf8');
    for (const pattern of forbidden) {
      assert.ok(!pattern.test(text), `${file} contains a prohibited token: ${pattern}`);
    }
  }

  // The art keys are neutral motif names, never art filenames.
  const items = await readJson<ReadonlyArray<{ readonly name: string; readonly img_name: string }>>(
    path.join(SEED, 'items.json'),
  );
  assert.ok(items.length >= 12);
  for (const item of items) {
    assert.doesNotMatch(item.img_name, /[\\/]/, `${item.name} has a path-like art key`);
    assert.doesNotMatch(item.img_name, /\.(?:swf|png|jpe?g|svg)\b/i);
  }
});

test('the isolation guard refuses a planted reference-tree read', async () => {
  const planted = await execFileAsync(
    process.execPath,
    [CHECK, '--plant-prohibited-read'],
    { cwd: ROOT },
  );
  assert.match(planted.stdout, /planted prohibited read was refused by the guard/);
  assert.match(planted.stdout, /prohibited read of a reference tree during validation:/);
  assert.equal(planted.stderr, '');
});

test('the shipped bundle build remains unchanged by the seed', async () => {
  const { bundle, problems } = await buildContent();
  assert.deepEqual(problems, []);
  const canonical = canonicalise(bundle);
  // The build id hashes the bundle with its own id still blank, exactly as
  // packages/content/src/build.ts computes it.
  const computedId = createHash('sha256')
    .update(canonicalise({ ...bundle, buildId: '' }))
    .digest('hex');

  const shippedText = await readFile(BUNDLE, 'utf8');
  const shipped = JSON.parse(shippedText) as Record<string, unknown>;
  assert.equal(bundle.buildId, computedId);
  assert.equal(shipped['buildId'], bundle.buildId);
  assert.equal(shippedText, `${canonical}\n`);

  // The shipped bundle still carries the reference-derived provenance; the
  // neutral seed's provenance has not leaked into it.
  assert.equal(typeof shipped['upstreamCommit'], 'string');
  assert.ok(Array.isArray(shipped['patchesApplied']));
  assert.ok(!('specVersion' in shipped));
  assert.ok(!('authoringMethod' in shipped));
  assert.ok(!shippedText.includes('content/neutral/v1'));

  const shippedItems = shipped['items'] as ReadonlyArray<{ readonly name: string }>;
  assert.ok(!shippedItems.some((item) => item.name === 'Timber Yard'));

  // The reference-derived build does not import the neutral seed.
  const buildSource = await readFile(path.join(HERE, 'build.ts'), 'utf8');
  assert.ok(!/content[/\\]neutral/.test(buildSource));
});
