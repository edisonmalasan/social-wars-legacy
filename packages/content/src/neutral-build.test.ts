/**
 * Tests for the opt-in neutral content bundle build.
 *
 * These prove four things, and nothing about publication or the licensing
 * gate: the neutral bundle is byte-stable; it carries only neutral provenance;
 * building it never reads a vendored reference tree; and the default, shipped
 * build is untouched by its existence.
 */
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { access, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

import { buildContent, canonicalise } from './build.ts';
import {
  buildNeutralBundle,
  canonicaliseNeutral,
  writeNeutralBundle,
} from './neutral-cli.ts';

const execFileAsync = promisify(execFile);

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const CLI = path.join(HERE, 'neutral-cli.ts');
const CHECK = path.join(ROOT, 'scripts', 'check-neutral-content.mjs');
const SHIPPED_BUNDLE = path.join(ROOT, 'packages', 'content', 'dist', 'content-bundle.json');
const SENTINEL = 'NEUTRAL_PROHIBITED_READ';

interface RunResult {
  readonly stdout: string;
  readonly stderr: string;
  readonly code: number;
}

async function runNode(args: readonly string[]): Promise<RunResult> {
  try {
    const { stdout, stderr } = await execFileAsync(process.execPath, [...args], {
      cwd: ROOT,
      maxBuffer: 8 * 1024 * 1024,
    });
    return { stdout, stderr, code: 0 };
  } catch (error) {
    const failure = error as { stdout?: string; stderr?: string; code?: number };
    return { stdout: failure.stdout ?? '', stderr: failure.stderr ?? '', code: failure.code ?? -1 };
  }
}

async function withTempDir<T>(fn: (dir: string) => Promise<T>): Promise<T> {
  const dir = await mkdtemp(path.join(tmpdir(), 'swl-neutral-build-'));
  try {
    return await fn(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

/**
 * An ESM preload that wraps the filesystem read entry points before the CLI
 * (and the guard it loads) are evaluated. It records any path containing an
 * `upstream` or `re` segment and reports it on the sentinel line at exit.
 * `String.raw` keeps the generated JavaScript's backslashes literal.
 */
const FS_PRELOAD = String.raw`
import fs from 'node:fs';

const violations = [];
function check(pathArg) {
  let value = pathArg && typeof pathArg === 'object' && 'path' in pathArg
    ? pathArg.path
    : pathArg;
  if (typeof value !== 'string') return;
  value = value.replaceAll('\\', '/');
  const parts = value.split('/');
  if (parts.includes('upstream') || parts.includes('re')) violations.push(String(pathArg));
}

const promisesFs = fs.promises;
for (const name of ['readFile', 'readdir', 'access']) {
  const original = promisesFs[name];
  if (typeof original === 'function') {
    promisesFs[name] = function (...args) {
      check(args[0]);
      return original.apply(this, args);
    };
  }
}
for (const name of ['readFileSync', 'readdirSync', 'accessSync']) {
  const original = fs[name];
  if (typeof original === 'function') {
    fs[name] = function (...args) {
      check(args[0]);
      return original.apply(this, args);
    };
  }
}

process.on('exit', () => {
  if (violations.length > 0) {
    process.stderr.write('NEUTRAL_PROHIBITED_READ ' + JSON.stringify(violations) + '\n');
  }
});
`;

async function withFsProbe<T>(fn: (preloadUrl: string) => Promise<T>): Promise<T> {
  return withTempDir(async (dir) => {
    const preload = path.join(dir, 'fs-probe.mjs');
    await writeFile(preload, FS_PRELOAD, 'utf8');
    return fn(pathToFileURL(preload).href);
  });
}

test('the neutral bundle is byte-stable across builds and processes', async () => {
  const first = await buildNeutralBundle();
  const second = await buildNeutralBundle();
  assert.equal(canonicaliseNeutral(first), canonicaliseNeutral(second));
  assert.equal(first.buildId, second.buildId);
  assert.match(first.buildId, /^[0-9a-f]{64}$/);

  // The build id hashes the canonical bundle with its own id still blank.
  const recomputed = createHash('sha256')
    .update(canonicaliseNeutral({ ...first, buildId: '' }))
    .digest('hex');
  assert.equal(first.buildId, recomputed);

  await withTempDir(async (dir) => {
    const a = path.join(dir, 'a.json');
    const b = path.join(dir, 'b.json');
    const runA = await runNode([CLI, '--out', a]);
    const runB = await runNode([CLI, '--out', b]);
    assert.equal(runA.code, 0, runA.stderr);
    assert.equal(runB.code, 0, runB.stderr);
    assert.equal(await readFile(a, 'utf8'), await readFile(b, 'utf8'));
    assert.match(await readFile(a, 'utf8'), /"buildId":"62ca5aab/);
  });
});

test('the neutral bundle carries no reference-tree provenance or proprietary token', async () => {
  const bundle = await buildNeutralBundle();
  const text = `${canonicaliseNeutral(bundle)}\n`;

  assert.ok(!('upstreamCommit' in bundle));
  assert.ok(!('patchesApplied' in bundle));
  assert.equal(bundle.specVersion, 'v1');
  assert.equal(bundle.authoringMethod, 'clean-room-authorship');
  assert.equal(bundle.licence, 'CC0-1.0');
  assert.match(bundle.artGenerator, /^@swl\/art@\d+\.\d+\.\d+$/);
  assert.equal(bundle.buildInputs.length, 5);
  assert.ok(bundle.items.length >= 12);
  assert.deepEqual(bundle.clientOnlyItemIds, []);
  assert.deepEqual(bundle.assetlessItemIds, []);

  const forbidden: readonly RegExp[] = [
    /upstreamCommit/,
    /patchesApplied/,
    /c3fceeb1f8e93734a293b9bc25ae6025656f6822/i,
    /Basesec/i,
    /\.swf\b/i,
    /\.fla\b/i,
    /\bpatches\.txt\b/i,
    /\bmain\.json\b/i,
    /\bitem-delegate-map\.json\b/i,
    /\bZynga\b/i,
    /ft_ground|LONG_RANGE|SHORT_RANGE|LAND_VEHICLE/,
    /BuildingWindow\.as\b/i,
  ];
  for (const pattern of forbidden) {
    assert.ok(!pattern.test(text), `the neutral bundle carries a prohibited token: ${pattern}`);
  }

  // The summary prints the new provenance, never the removed fields.
  const run = await runNode([CLI, '--check']);
  assert.equal(run.code, 0, run.stderr);
  assert.match(run.stdout, /spec revision      : [0-9a-f]{64}/);
  assert.match(run.stdout, /licence            : CC0-1\.0/);
  assert.doesNotMatch(run.stdout, /upstream|patches applied/i);
});

test('building the neutral bundle never reads a reference tree', async () => {
  await withFsProbe(async (preloadUrl) => {
    // First prove the instrumentation itself is live: a deliberate read of a
    // path with an `upstream` segment must be observed.
    const probe = await runNode([
      '--import', preloadUrl,
      '--input-type=module',
      '-e',
      "import { readFile } from 'node:fs/promises'; await readFile('probe/upstream/x.txt').catch(() => {});",
    ]);
    assert.ok(probe.stderr.includes(SENTINEL), 'the fs instrumentation must observe reads');

    // Now the real build under the same instrumentation.
    const out = path.join(path.dirname(fileURLToPath(preloadUrl)), 'out.json');
    const run = await runNode(['--import', preloadUrl, CLI, '--out', out]);
    assert.equal(run.code, 0, run.stderr);
    assert.ok(!run.stderr.includes(SENTINEL), run.stderr);
    assert.match(run.stdout, /build id           : [0-9a-f]{64}/);

    // The guard still refuses a planted reference-tree read.
    const planted = await runNode([CHECK, '--plant-prohibited-read']);
    assert.equal(planted.code, 0, planted.stderr);
    assert.match(planted.stdout, /planted prohibited read was refused by the guard/);
    assert.match(planted.stdout, /prohibited read of a reference tree during validation:/);
  });

  // Static backstop: the CLI neither constructs nor opens a reference path.
  const source = await readFile(CLI, 'utf8');
  assert.doesNotMatch(source, /upstream[\\/]/);
  assert.doesNotMatch(source, /\bre[\\/]/);
  assert.doesNotMatch(source, /villages[\\/]quest/);
  assert.doesNotMatch(source, /config[\\/]patch/);
});

test('the default legacy build and its shipped bundle remain unchanged', async () => {
  // `pnpm test` builds first; running this file directly needs the same input.
  try {
    await access(SHIPPED_BUNDLE);
  } catch {
    const built = await runNode([path.join(HERE, 'cli.ts')]);
    assert.equal(built.code, 0, built.stderr);
  }
  const shippedBefore = await readFile(SHIPPED_BUNDLE, 'utf8');

  await withTempDir(async (dir) => {
    const neutral = await buildNeutralBundle();
    const out = path.join(dir, 'neutral.json');
    await writeNeutralBundle(neutral, out);
    assert.equal(await readFile(SHIPPED_BUNDLE, 'utf8'), shippedBefore);
  });

  const { bundle: legacy, problems } = await buildContent();
  assert.deepEqual(problems, []);
  const legacyText = canonicalise(legacy);
  const shipped = JSON.parse(shippedBefore) as Record<string, unknown>;
  assert.equal(shipped['buildId'], legacy.buildId);
  assert.equal(shippedBefore, `${legacyText}\n`);
  assert.equal(typeof shipped['upstreamCommit'], 'string');
  assert.ok(Array.isArray(shipped['patchesApplied']));

  const neutral = await buildNeutralBundle();
  assert.notEqual(neutral.buildId, legacy.buildId);
  assert.ok(!('specVersion' in shipped));
  assert.ok(!('authoringMethod' in shipped));
  assert.ok(!shippedBefore.includes('content/neutral/v1'));

  // The reference-derived build does not import the neutral CLI or seed.
  const buildSource = await readFile(path.join(HERE, 'build.ts'), 'utf8');
  assert.doesNotMatch(buildSource, /neutral-cli|content[/\\]neutral/);
});
