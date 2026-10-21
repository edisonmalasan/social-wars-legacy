#!/usr/bin/env node
/**
 * Check that the build is reproducible.
 *
 * A build that produces different bytes each time cannot be trusted:
 * a release cannot be rebuilt, a change cannot be reviewed by
 * comparing the artefacts, and a bug cannot be tracked to a build.
 *
 * So the client's build is done **twice** and the two are compared -
 * the same files, with the same content, byte for byte.
 *
 * The content bundle's reproducibility is a property of the content
 * pipeline itself, and it is checked by the pipeline's own build id.
 *
 * Usage:
 *   node scripts/check-reproducible-build.mjs
 */
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readdir, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ROOT = process.cwd();

/** Every file under a directory, with its content's hash. */
async function digest(dir) {
  const files = new Map();
  const walk = async (current) => {
    for (const entry of await readdir(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(full);
        continue;
      }
      const bytes = await readFile(full);
      files.set(
        path.relative(dir, full).split(path.sep).join('/'),
        createHash('sha256').update(bytes).digest('hex'),
      );
    }
  };
  await walk(dir);
  return files;
}

/** Build the client into a directory. */
function build(outDir) {
  // Vite lives in the client's own node_modules, because the workspace
  // is pnpm's and the app is where the dependency is.
  const vite = path.join(
    ROOT,
    'apps/client/node_modules/vite/bin/vite.js',
  );
  if (!existsSync(vite)) {
    throw new Error('the client has no vite: run pnpm install');
  }
  const result = spawnSync(
    process.execPath,
    [vite, 'build', '--outDir', outDir, '--emptyOutDir'],
    {
      cwd: path.join(ROOT, 'apps/client'),
      encoding: 'utf8',
      env: { ...process.env },
    },
  );
  if (result.status !== 0) {
    console.error(result.stdout ?? '');
    console.error(result.stderr ?? '');
    throw new Error('the client did not build');
  }
}

async function main() {
  const first = path.join(ROOT, '.work/reproducible-a');
  const second = path.join(ROOT, '.work/reproducible-b');

  await rm(first, { recursive: true, force: true });
  await rm(second, { recursive: true, force: true });

  process.stdout.write('  building the client, once');
  build(first);
  process.stdout.write(' and again\n');
  build(second);

  const a = await digest(first);
  const b = await digest(second);

  const problems = [];

  for (const [file, hash] of a) {
    if (!b.has(file)) {
      problems.push(`${file} is in the first build and not the second`);
    } else if (b.get(file) !== hash) {
      problems.push(`${file} differs between the two builds`);
    }
  }
  for (const file of b.keys()) {
    if (!a.has(file)) {
      problems.push(`${file} is in the second build and not the first`);
    }
  }

  await rm(first, { recursive: true, force: true });
  await rm(second, { recursive: true, force: true });

  if (problems.length > 0) {
    console.error('the build is not reproducible:');
    for (const problem of problems) console.error(`  ${problem}`);
    process.exit(1);
  }

  console.log(`OK: the client's build is reproducible (${a.size} file(s), twice)`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
