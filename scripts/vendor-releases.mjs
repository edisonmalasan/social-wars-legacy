#!/usr/bin/env node
/**
 * Vendor the upstream's RELEASE TAGS.
 *
 * The vendored tree is the upstream's working tree at `main`, and it is
 * complete. What it does not carry is the upstream's history — and with it
 * the two release tags, which are earlier builds of the game.
 *
 * The upstream's `.git` is 655 MB, most of it the many versions of the
 * game's art across 198 commits. Vendoring all of it would triple the
 * repository for a history that is public.
 *
 * So the releases are captured the way the tree was, but as an **overlay**:
 *
 *   upstream/releases/<tag>/   the files that release has and `main` does
 *                               not - the ones that were MODIFIED, rather
 *                               than added, between the two
 *   upstream/RELEASES.json      the release's COMPLETE record: every file
 *                               in that release's tree, with its hash, and
 *                               whether its bytes live in the overlay or
 *                               are shared with `main`
 *
 * With both, every release of the game is reconstructible from this
 * repository alone: a file's bytes are in the overlay if it was modified,
 * and in `main` if it was not.
 *
 * Usage:
 *   node scripts/vendor-releases.mjs --source <path to the upstream checkout>
 */
import { execFile } from 'node:child_process';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { promisify } from 'node:util';

import { hashFile } from './lib/upstream-manifest.mjs';

const execFileAsync = promisify(execFile);

const root = process.cwd();
const RELEASES_DIR = 'upstream/releases';
const RELEASES_MANIFEST = 'upstream/RELEASES.json';

/** The upstream's checkout, with its .git. */
function sourcePath() {
  const index = process.argv.indexOf('--source');
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return 'C:/Users/Edison/Desktop/socialwarriors';
}

/** Run git in the upstream checkout. */
async function git(args, binary = false) {
  const { stdout } = await execFileAsync('git', ['-C', sourcePath(), ...args], {
    encoding: binary ? 'buffer' : 'utf8',
    maxBuffer: 256 * 1024 * 1024,
  });
  return stdout;
}

/** The release tags, oldest first. */
async function releaseTags() {
  const out = await git(['tag', '--sort=creatordate']);
  return out
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

/** The files in a ref's tree, with their blob ids. */
async function treeFiles(ref) {
  const out = await git(['ls-tree', '-r', '-z', ref]);
  const entries = [];
  for (const record of out.split('\0')) {
    if (!record) continue;
    const tab = record.indexOf('\t');
    if (tab < 0) continue;
    const meta = record.slice(0, tab).split(/\s+/);
    const filePath = record.slice(tab + 1);
    entries.push({ mode: meta[0], type: meta[1], blob: meta[2], path: filePath });
  }
  return entries;
}

/** A blob's raw bytes. */
async function blobBytes(blob) {
  return Buffer.from(await git(['cat-file', 'blob', blob], true));
}

async function main() {
  const source = sourcePath();
  console.log(`the upstream checkout: ${source}`);

  const mainTree = new Map();
  for (const entry of await treeFiles('HEAD')) {
    mainTree.set(entry.path, entry.blob);
  }
  console.log(`main: ${mainTree.size} files`);

  const tags = await releaseTags();
  console.log(`the release tags: ${tags.join(', ')}`);

  const releases = [];
  for (const tag of tags) {
    const commit = (await git(['rev-list', '-n', '1', tag])).trim();
    const date = (await git(['show', '-s', '--format=%cI', commit])).trim();
    const message = (await git(['show', '-s', '--format=%s', commit])).trim();

    const tree = await treeFiles(tag);
    const overlay = [];
    const files = [];

    for (const entry of tree) {
      const mainBlob = mainTree.get(entry.path);
      if (mainBlob === entry.blob) {
        // The same bytes as `main`: the file is shared, and the overlay
        // does not need it.
        files.push({
          path: entry.path,
          sha256: null,
          bytes: null,
          inOverlay: false,
          blob: entry.blob,
        });
        continue;
      }
      const bytes = await blobBytes(entry.blob);
      overlay.push({ path: entry.path, bytes });
      files.push({
        path: entry.path,
        sha256: null,
        bytes: bytes.length,
        inOverlay: true,
        blob: entry.blob,
      });
    }

    console.log(`  ${tag}: ${tree.length} files, ${overlay.length} unique`);

    // Write the overlay.
    const overlayDir = path.join(root, RELEASES_DIR, tag);
    await rm(overlayDir, { recursive: true, force: true });
    for (const file of overlay) {
      const target = path.join(overlayDir, ...file.path.split('/'));
      await mkdir(path.dirname(target), { recursive: true });
      await writeFile(target, file.bytes);
    }

    // Hash the overlay's files, and the shared ones from the vendored tree.
    const base = path.join(root, 'upstream/socialwarriors');
    for (const file of files) {
      const source = file.inOverlay
        ? path.join(overlayDir, ...file.path.split('/'))
        : path.join(base, ...file.path.split('/'));
      file.sha256 = await hashFile(source);
      if (file.bytes === null) {
        const { stat } = await import('node:fs/promises');
        file.bytes = (await stat(source)).size;
      }
    }

    releases.push({
      tag,
      commit,
      date,
      message,
      overlay: `${RELEASES_DIR}/${tag}`,
      totals: {
        files: files.length,
        unique: overlay.length,
        bytes: files.reduce((n, f) => n + (f.bytes ?? 0), 0),
      },
      files: files.map(({ path: filePath, sha256, bytes, inOverlay }) => ({
        path: filePath,
        sha256,
        bytes,
        inOverlay,
      })),
    });
  }

  const manifest = {
    note:
      'The upstream release tags. The vendored tree is the working tree at `main`, ' +
      'and the upstream .git directory is excluded; these are the two releases ' +
      'that the tree does not carry. Each release is complete: a file\'s bytes are ' +
      'in the overlay when it was MODIFIED between the release and `main`, and in ' +
      '`main` when it was not. So every release is reconstructible from this ' +
      'repository alone.',
    upstream: 'https://github.com/AcidCaos/socialwarriors.git',
    mainCommit: (await git(['rev-parse', 'HEAD'])).trim(),
    releases,
  };

  await writeFile(
    path.join(root, RELEASES_MANIFEST),
    JSON.stringify(manifest, null, 1) + '\n',
    'utf8',
  );
  console.log(`\nwrote ${RELEASES_MANIFEST}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
