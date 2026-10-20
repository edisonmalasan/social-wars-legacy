#!/usr/bin/env node
/**
 * Verify the vendored upstream tree against its manifest, and the vendored
 * releases against theirs.
 *
 *   node scripts/verify-upstream.mjs            # verify only
 *   node scripts/verify-upstream.mjs --write    # regenerate the manifest, then verify
 *
 * Exits 0 when every file matches, 1 on any drift (changed, missing or extra).
 */
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import {
  UPSTREAM_DIR,
  SHA_MANIFEST,
  buildManifest,
  hashFile,
  listFiles,
  parseShaManifest,
  verifyReleases,
  writeManifest,
} from './lib/upstream-manifest.mjs';

const root = process.cwd();
const write = process.argv.includes('--write');

if (write) {
  process.stdout.write('regenerating manifest... ');
  const files = await buildManifest(root);
  await writeManifest(files, root);
  process.stdout.write(`${files.length} files\n`);
}

let expected;
try {
  expected = parseShaManifest(await readFile(path.join(root, SHA_MANIFEST), 'utf8'));
} catch (err) {
  console.error(`cannot read ${SHA_MANIFEST}: ${err.message}`);
  console.error('run `node scripts/verify-upstream.mjs --write` to generate it');
  process.exit(1);
}

const base = path.join(root, UPSTREAM_DIR);
const present = await listFiles(base);
const presentSet = new Set(present);
const expectedSet = new Set(expected.map((e) => e.path));

const missing = expected.filter((e) => !presentSet.has(e.path));
const extra = present.filter((p) => !expectedSet.has(p));

let mismatched = 0;
let checked = 0;
for (const entry of expected) {
  if (!presentSet.has(entry.path)) continue;
  const actual = await hashFile(path.join(base, ...entry.path.split('/')));
  checked += 1;
  if (actual !== entry.sha256) {
    if (mismatched < 20) {
      console.error(`  CHANGED  ${entry.path}\n            expected ${entry.sha256}\n            actual   ${actual}`);
    }
    mismatched += 1;
  }
}

const total = expected.length;
console.log(`upstream tree : ${UPSTREAM_DIR}`);
console.log(`files expected: ${total}`);
console.log(`files checked : ${checked}`);
console.log(`mismatched    : ${mismatched}`);
console.log(`missing       : ${missing.length}`);
console.log(`unexpected    : ${extra.length}`);

if (missing.length) {
  for (const m of missing.slice(0, 20)) console.error(`  MISSING    ${m.path}`);
  if (missing.length > 20) console.error(`  ... and ${missing.length - 20} more`);
}
if (extra.length) {
  for (const e of extra.slice(0, 20)) console.error(`  EXTRA      ${e}`);
  if (extra.length > 20) console.error(`  ... and ${extra.length - 20} more`);
}

if (mismatched || missing.length || extra.length) {
  console.error('\nFAIL: the vendored upstream tree has drifted from its manifest.');
  process.exit(1);
}
console.log('\nOK: the vendored upstream tree matches its manifest byte for byte.');

// --- the vendored releases --------------------------------------------------
console.log('\n--- the vendored releases ---');
let releasesOk = true;
try {
  const releases = await verifyReleases(root);
  for (const release of releases) {
    console.log(
      `release ${release.tag} : ${release.files} files, ${release.unique} unique, ` +
        `${release.checked} checked, ${release.mismatched} mismatched, ` +
        `${release.missing} missing, ${release.stray} stray, ${release.absent} absent`,
    );
    for (const problem of release.problems) console.error(problem);
    if (release.mismatched || release.missing || release.stray || release.absent) {
      releasesOk = false;
    }
  }
} catch (error) {
  console.error(`cannot read the releases manifest: ${error.message}`);
  releasesOk = false;
}

if (!releasesOk) {
  console.error('\nFAIL: a vendored release has drifted from its manifest.');
  process.exit(1);
}
console.log('\nOK: every vendored release is complete and matches its manifest.');
