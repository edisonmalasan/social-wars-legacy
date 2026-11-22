#!/usr/bin/env node
/**
 * Generate, or verify, `assets/original/`.
 *
 *   node packages/art/src/cli.ts            write the generated tree
 *   node packages/art/src/cli.ts --check    compare it with a fresh generation
 */
import nodePath from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { buildArtifacts } from './artifacts.ts';
import { checkArtifacts, nodeIO, writeArtifacts, type FileIO } from './io.ts';

const DEFAULT_ROOT = nodePath.resolve(process.cwd(), 'assets/original');

/** Run the command. Returns the process exit code. */
export async function run(
  argv: readonly string[],
  io: FileIO = nodeIO,
  root: string = DEFAULT_ROOT,
): Promise<number> {
  const artifacts = buildArtifacts();
  if (argv.includes('--check')) {
    const problems = await checkArtifacts(root, artifacts, io);
    if (problems.length > 0) {
      console.error('the generated assets are not current:');
      for (const problem of problems) console.error(`  ${problem}`);
      return 1;
    }
    console.log(`the generated assets are current (${artifacts.length} files)`);
    return 0;
  }
  await writeArtifacts(root, artifacts, io);
  console.log(`wrote ${artifacts.length} file(s) to ${nodePath.relative(process.cwd(), root)}`);
  return 0;
}

const invokedDirectly = process.argv[1]
  ? nodePath.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
  : false;

if (invokedDirectly) {
  run(process.argv.slice(2))
    .then((code) => {
      process.exitCode = code;
    })
    .catch((error: unknown) => {
      console.error(error);
      process.exitCode = 1;
    });
}
