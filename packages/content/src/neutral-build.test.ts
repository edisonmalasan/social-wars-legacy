/**
 * Tests for the opt-in neutral bundle build.
 *
 * The neutral bundle is a separate artefact, not the shipped one. These tests
 * prove that the opt-in build is byte-reproducible, that it carries only the
 * neutral provenance, that all of its reads stay inside the CC0 seed (and that
 * the shared guard actually refuses a reference-tree read), and that the
 * reference-derived bundle the shipped tree consumes is untouched.
 */
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import { buildContent, canonicalise } from './build.ts';
import { buildNeutralBundle, DEFAULT_OUT, SEED_REL } from './neutral-cli.ts';

// The validator is a plain `.mjs` script with no declaration file.
// @ts-expect-error -- plain JS script, no declaration file
import { plantProhibitedRead } from '../../../scripts/check-neutral-content.mjs';

const execFileAsync = promisify(execFile);

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const CLI = path.join(HERE, 'neutral-cli.ts');
const VALIDATOR = path.join(ROOT, 'scripts/check-neutral-content.mjs');
const SEED = path.join(ROOT, SEED_REL);
const SHIPPED = path.join(ROOT, 'packages/content/dist/content-bundle.json');

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

function sha256(bytes: string | Buffer): string {
  return createHash('sha256').update(bytes).digest('hex');
}

test('the neutral build is byte-for-byte reproducible', async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), 'swl-neutral-'));
  try {
    const firstPath = path.join(temp, 'first.json');
    const secondPath = path.join(temp, 'second.json');
    const first = await execFileAsync(process.execPath, [CLI, '--out', firstPath], { cwd: ROOT });
    const second = await execFileAsync(process.execPath, [CLI, '--out', secondPath], { cwd: ROOT });
    assert.equal(first.stderr, '');
    assert.equal(second.stderr, '');
    assert.match(first.stdout, /guarded reads        : 5 \(all inside content\/neutral\/v1\)/);

    const firstBytes = await readFile(firstPath);
    const secondBytes = await readFile(secondPath);
    assert.deepEqual(firstBytes, secondBytes, 'two clean builds differ byte-for-byte');

    // The on-disk artefact is exactly the canonical bundle plus one newline,
    // and its build id is the SHA-256 of the canonical bytes with a blank id.
    const { bundle } = await buildNeutralBundle();
    const canonical = canonicalise(bundle);
    assert.equal(`${canonical}\n`, firstBytes.toString('utf8'));
    assert.equal(bundle.buildId, sha256(canonicalise({ ...bundle, buildId: '' })));
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});

test('the neutral bundle carries neutral provenance and no reference-tree token', async () => {
  // Produce the artefact first so this test is self-contained on a fresh clone.
  await execFileAsync(process.execPath, [CLI], { cwd: ROOT });
  const { bundle } = await buildNeutralBundle();
  const text = await readFile(DEFAULT_OUT, 'utf8');

  const forbidden: readonly RegExp[] = [
    /upstreamCommit/,
    /patchesApplied/,
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
    /[A-Za-z]:[/\\]/,
  ];
  for (const pattern of forbidden) {
    assert.ok(!pattern.test(text), `the neutral bundle contains a prohibited token: ${pattern}`);
  }
  const parsed = JSON.parse(text) as Record<string, unknown>;
  assert.ok(!('upstreamCommit' in parsed));
  assert.ok(!('patchesApplied' in parsed));

  // Every provenance value is the authored one, not a generated placeholder.
  const provenance = await readJson<Provenance>(path.join(SEED, 'provenance.json'));
  for (const key of [
    'specVersion', 'specRevision', 'authoringMethod', 'licence', 'artGenerator', 'statement',
  ] as const) {
    assert.equal(bundle[key], provenance[key], `${key} does not come from the seed`);
    assert.equal(parsed[key], provenance[key]);
  }
  assert.deepEqual(bundle.buildInputs, provenance.buildInputs.map((input) => ({ ...input })));
  for (const input of bundle.buildInputs) {
    assert.match(input.path, /^[A-Za-z0-9._-]+$/);
  }

  // The inputs hash to the recorded specRevision, independently recomputed.
  const lines = bundle.buildInputs.map((input) => `${input.path}:${input.sha256}`).sort();
  assert.equal(provenance.specRevision, sha256(`${lines.join('\n')}\n`));

  // Ids and art keys come from the seed's neutral namespace and vocabulary.
  const vocabulary = await readJson<{
    readonly idRange: { readonly start: number; readonly end: number };
    readonly allocation: readonly { readonly slug: string; readonly id: number }[];
  }>(path.join(SEED, 'vocabulary.json'));
  const allocated = new Set(vocabulary.allocation.map((entry) => entry.id));
  assert.ok(bundle.items.length >= 12);
  for (const item of bundle.items) {
    assert.ok(allocated.has(item.id), `${item.id} is not in the neutral allocation table`);
    assert.ok(item.id >= vocabulary.idRange.start && item.id <= vocabulary.idRange.end);
    for (const key of item.img_name.split(',').map((v) => v.trim()).filter(Boolean)) {
      assert.doesNotMatch(key, /[\\/]/);
      assert.doesNotMatch(key, /\.(?:swf|png|jpe?g|svg)\b/i);
    }
  }
});

test('the neutral build only reads the seed and the guard refuses planted reads', async () => {
  const { reads } = await buildNeutralBundle();
  assert.ok(reads.length > 0);
  for (const read of reads) {
    assert.ok(read.startsWith(`${SEED_REL}/`), `the neutral build read outside the seed: ${read}`);
    const segments = read.split('/');
    assert.ok(!segments.includes('upstream'));
    assert.ok(!segments.includes('re'));
  }
  assert.deepEqual(
    [...reads].sort(),
    ['globals.json', 'goals.json', 'items.json', 'provenance.json', 'vocabulary.json']
      .map((name) => `${SEED_REL}/${name}`)
      .sort(),
  );

  // The validator used by the build performs its own guarded reads; its
  // summary must confirm those stayed inside the seed too.
  const checked = await execFileAsync(process.execPath, [VALIDATOR], { cwd: ROOT });
  assert.match(checked.stdout, /guarded reads, all inside content\/neutral\/v1/);
  assert.match(checked.stdout, /OK: validation passed/);

  // The guard must be shown to fire, not merely trusted.
  const planted = plantProhibitedRead() as { refused: boolean; message: string };
  assert.equal(planted.refused, true);
  assert.match(planted.message, /prohibited read of a reference tree/);
});

test('the shipped, reference-derived bundle is unchanged', async () => {
  const before = await readFile(SHIPPED);
  const { bundle, problems } = await buildContent();
  assert.deepEqual(problems, []);
  assert.equal(bundle.buildId, sha256(canonicalise({ ...bundle, buildId: '' })));
  assert.equal(before.toString('utf8'), `${canonicalise(bundle)}\n`);

  assert.equal(typeof bundle.upstreamCommit, 'string');
  assert.ok(Array.isArray(bundle.patchesApplied));
  assert.ok(!('specVersion' in bundle));
  assert.ok(!('specRevision' in bundle));
  assert.ok(!('authoringMethod' in bundle));
  assert.ok(!before.toString('utf8').includes(SEED_REL));

  // Running the opt-in build must not rewrite the shipped bundle.
  await execFileAsync(process.execPath, [CLI], { cwd: ROOT });
  const after = await readFile(SHIPPED);
  assert.deepEqual(after, before, 'the neutral build changed the shipped bundle');
  assert.deepEqual(await readFile(DEFAULT_OUT), Buffer.from(`${canonicalise(
    (await buildNeutralBundle()).bundle,
  )}\n`));
});
