#!/usr/bin/env node
/**
 * Pull only the vendored upstream assets a build actually needs.
 *
 * The full vendored asset tree is 716.8 MB, of which 239.7 MB is the 57 archival
 * `Basesec_1.5.x.swf` client builds. A game build needs the sprite/FX/thumb/sound
 * art and the reference client, not the client history.
 *
 *   node scripts/pull-assets.mjs            # the default set (everything but the
 *                                           # archival client builds)
 *   node scripts/pull-assets.mjs --all      # every LFS object, including the
 *                                           # archival Basesec builds
 *   node scripts/pull-assets.mjs --check    # report what is present/missing only
 */
import { execFileSync } from 'node:child_process';
import { statSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const root = process.cwd();
const ASSETS = 'upstream/socialwarriors/assets';

/** The asset groups a normal build needs. */
const DEFAULT_INCLUDES = [
  `${ASSETS}/sprites/**`,
  `${ASSETS}/fx/**`,
  `${ASSETS}/thumbs/**`,
  `${ASSETS}/sounds/**`,
  `${ASSETS}/magic/**`,
  `${ASSETS}/characters_2/**`,
  `${ASSETS}/images/**`,
  `${ASSETS}/fonts/**`,
  `${ASSETS}/swf/**`,
  `${ASSETS}/externalized/**`,
  // The reference client used by the test oracle, and its loader.
  `${ASSETS}/flash/Basesec_1.5.4.swf`,
  `${ASSETS}/flash/SWLoader.swf`,
];

const ARCHIVAL_PREFIX = `${ASSETS}/flash/Basesec_1.4.`;

function git(args, opts = {}) {
  return execFileSync('git', args, { cwd: root, encoding: 'utf8', ...opts });
}

function lfsFiles() {
  const out = git(['lfs', 'ls-files', '-n']);
  return out.split('\n').map((l) => l.trim()).filter(Boolean);
}

const all = lfsFiles();
const archival = all.filter((f) => f.startsWith(ARCHIVAL_PREFIX));

console.log(`LFS objects in the repository : ${all.length}`);
console.log(`  archival Basesec builds      : ${archival.length}`);

if (process.argv.includes('--check')) {
  const missing = [];
  for (const f of all) {
    const abs = path.join(root, ...f.split('/'));
    try {
      if (statSync(abs).size === 0) missing.push(f);
    } catch {
      missing.push(f);
    }
  }
  console.log(`  missing from the worktree    : ${missing.length}`);
  for (const m of missing.slice(0, 10)) console.log(`    ${m}`);
  if (missing.length > 10) console.log(`    ... and ${missing.length - 10} more`);
  process.exit(missing.length ? 1 : 0);
}

if (process.argv.includes('--all')) {
  console.log('\npulling every LFS object (including the archival client builds)...');
  git(['lfs', 'pull']);
} else {
  console.log('\npulling the build set (excluding the archival client builds)...');
  const args = ['lfs', 'pull', '--include=' + DEFAULT_INCLUDES.join(' --include=')];
  git(args);
  console.log(`skipped ${archival.length} archival client builds.`);
  console.log('Fetch them with:  node scripts/pull-assets.mjs --all');
}

console.log('\ndone.');
