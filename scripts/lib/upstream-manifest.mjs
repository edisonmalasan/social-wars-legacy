/**
 * Shared helpers for the vendored upstream tree.
 *
 * The upstream project is vendored under `upstream/socialwarriors/`, byte for byte,
 * at a pinned commit. Two artefacts describe it:
 *
 *   upstream/MANIFEST.sha256  - GNU sha256sum format, sorted by path. Verifiable
 *                               with `sha256sum -c` on any POSIX system.
 *   upstream/MANIFEST.json    - the same data plus byte sizes, for tooling.
 *
 * The upstream `.git` directory is deliberately NOT vendored: it is VCS metadata, not
 * project content. The manifest covers the 3292 working-tree files only.
 *
 * The upstream's two RELEASE TAGS are a different matter: they are earlier builds of
 * the game, so their content IS project content. They are captured as an overlay:
 *
 *   upstream/releases/<tag>/  the files that release has and `main` does not
 *   upstream/RELEASES.json     every release's COMPLETE record, with each file's hash
 *                              and whether its bytes live in the overlay or are shared
 *                              with `main`
 *
 * With both, every release is reconstructible from this repository alone.
 */
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';

export const UPSTREAM_DIR = 'upstream/socialwarriors';
export const MANIFEST_DIR = 'upstream';
export const SHA_MANIFEST = 'upstream/MANIFEST.sha256';
export const JSON_MANIFEST = 'upstream/MANIFEST.json';
export const RELEASES_DIR = 'upstream/releases';
export const RELEASES_MANIFEST = 'upstream/RELEASES.json';

/** Recursively list every file under `dir`, as POSIX-style relative paths, sorted. */
export async function listFiles(dir, prefix = '') {
  const out = [];
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      out.push(...(await listFiles(path.join(dir, entry.name), rel)));
    } else if (entry.isFile()) {
      out.push(rel);
    }
  }
  return out.sort();
}

/** SHA-256 of one file, streamed so a 60 MB SWF does not have to fit in memory. */
export async function hashFile(filePath) {
  const hash = createHash('sha256');
  await new Promise((resolve, reject) => {
    createReadStream(filePath)
      .on('data', (chunk) => hash.update(chunk))
      .on('end', resolve)
      .on('error', reject);
  });
  return hash.digest('hex');
}

/** Build the full manifest for the vendored tree. */
export async function buildManifest(root = process.cwd()) {
  const base = path.join(root, UPSTREAM_DIR);
  const rels = await listFiles(base);
  const files = [];
  for (const rel of rels) {
    const abs = path.join(base, ...rel.split('/'));
    const info = await stat(abs);
    files.push({ path: rel, sha256: await hashFile(abs), bytes: info.size });
  }
  return files;
}

/** Write both manifest artefacts. */
export async function writeManifest(files, root = process.cwd()) {
  await writeFile(
    path.join(root, SHA_MANIFEST),
    files.map((f) => `${f.sha256}  ${f.path}`).join('\n') + '\n',
    'utf8',
  );
  const byDir = {};
  for (const f of files) {
    const dir = f.path.includes('/') ? f.path.slice(0, f.path.lastIndexOf('/')) : '.';
    byDir[dir] = byDir[dir] || { files: 0, bytes: 0 };
    byDir[dir].files += 1;
    byDir[dir].bytes += f.bytes;
  }
  await writeFile(
    path.join(root, JSON_MANIFEST),
    JSON.stringify(
      {
        note: 'Vendored upstream working tree. The upstream .git directory is excluded.',
        upstream: 'https://github.com/AcidCaos/socialwarriors.git',
        commit: 'c3fceeb1f8e93734a293b9bc25ae6025656f6822',
        totals: {
          files: files.length,
          bytes: files.reduce((n, f) => n + f.bytes, 0),
        },
        byDirectory: byDir,
        files,
      },
      null,
      1,
    ) + '\n',
    'utf8',
  );
}

/** Parse a sha256sum-format manifest. */
export function parseShaManifest(text) {
  const out = [];
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    const m = /^([0-9a-f]{64})\s\s(.+)$/.exec(line);
    if (!m) throw new Error(`unparsable manifest line: ${line.slice(0, 80)}`);
    out.push({ sha256: m[1], path: m[2] });
  }
  return out;
}

/**
 * Verify the vendored releases.
 *
 * Each release's file list is checked against **this repository**: a file
 * marked `inOverlay` is hashed in the overlay, and one that is not is
 * hashed in the vendored tree. So a release is proven reconstructible from
 * the repository alone, without the upstream's git history.
 *
 * The overlay directory is also checked to hold exactly the files it
 * claims, so a stray or a missing file is caught.
 */
export async function verifyReleases(root = process.cwd()) {
  const manifestPath = path.join(root, RELEASES_MANIFEST);
  const manifest = JSON.parse(await (await import('node:fs/promises')).readFile(manifestPath, 'utf8'));
  const base = path.join(root, UPSTREAM_DIR);
  const report = [];

  for (const release of manifest.releases) {
    const overlayDir = path.join(root, release.overlay);
    let checked = 0;
    let mismatched = 0;
    let missing = 0;
    const problems = [];

    for (const file of release.files) {
      const source = file.inOverlay
        ? path.join(overlayDir, ...file.path.split('/'))
        : path.join(base, ...file.path.split('/'));
      let actual;
      try {
        actual = await hashFile(source);
      } catch {
        missing += 1;
        if (problems.length < 20) problems.push(`  MISSING    ${file.path}`);
        continue;
      }
      checked += 1;
      if (actual !== file.sha256) {
        mismatched += 1;
        if (problems.length < 20) {
          problems.push(`  CHANGED   ${file.path}\n            expected ${file.sha256}\n            actual   ${actual}`);
        }
      }
    }

    // The overlay holds exactly the files it claims.
    let present = [];
    try {
      present = await listFiles(overlayDir);
    } catch {
      present = [];
    }
    const expected = release.files.filter((file) => file.inOverlay).map((file) => file.path).sort();
    const stray = present.filter((file) => !expected.includes(file));
    const absent = expected.filter((file) => !present.includes(file));

    report.push({
      tag: release.tag,
      commit: release.commit,
      files: release.files.length,
      unique: expected.length,
      checked,
      mismatched,
      missing,
      stray: stray.length,
      absent: absent.length,
      problems,
    });
  }

  return report;
}
