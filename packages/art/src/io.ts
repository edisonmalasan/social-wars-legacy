/**
 * The only module in the generator that touches the filesystem.
 *
 * The filesystem is passed in as an object so tests can observe every path
 * the generator reads or writes and prove that none of them is under the
 * vendored upstream or the reverse-engineering tree.
 */
import nodeFs from 'node:fs/promises';
import nodePath from 'node:path';
import { equalBytes, type Artifact } from './manifest.ts';

export interface FileIO {
  mkdir(directory: string, options: { recursive: boolean }): Promise<unknown>;
  writeFile(file: string, data: Uint8Array): Promise<void>;
  readFile(file: string): Promise<Uint8Array>;
}

/** The real filesystem. Named so a test can pass a recording fake instead. */
export const nodeIO: FileIO = {
  mkdir(directory, options) {
    return nodeFs.mkdir(directory, options);
  },
  async writeFile(file, data) {
    await nodeFs.writeFile(file, data);
  },
  async readFile(file) {
    return await nodeFs.readFile(file);
  },
};

/** Write the generated tree under `root`. */
export async function writeArtifacts(
  root: string,
  artifacts: readonly Artifact[],
  io: FileIO = nodeIO,
): Promise<void> {
  for (const artifact of artifacts) {
    const target = nodePath.join(root, ...artifact.path.split('/'));
    await io.mkdir(nodePath.dirname(target), { recursive: true });
    await io.writeFile(target, artifact.bytes);
  }
}

/** Compare the files under `root` with a fresh generation. */
export async function checkArtifacts(
  root: string,
  artifacts: readonly Artifact[],
  io: FileIO = nodeIO,
): Promise<string[]> {
  const problems: string[] = [];
  for (const artifact of artifacts) {
    const target = nodePath.join(root, ...artifact.path.split('/'));
    let actual: Uint8Array;
    try {
      actual = await io.readFile(target);
    } catch {
      problems.push(`${artifact.path}: missing`);
      continue;
    }
    if (!equalBytes(actual, artifact.bytes)) problems.push(`${artifact.path}: differs`);
  }
  return problems;
}
