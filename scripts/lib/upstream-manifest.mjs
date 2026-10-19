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
 */
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';

export const UPSTREAM_DIR = 'upstream/socialwarriors';
export const MANIFEST_DIR = 'upstream';
export const SHA_MANIFEST = 'upstream/MANIFEST.sha256';
export const JSON_MANIFEST = 'upstream/MANIFEST.json';

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
