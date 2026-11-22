/**
 * The provenance manifest.
 *
 * Every emitted file gets a relative path, its byte size, its SHA-256, the
 * generator version and an explicit original-work statement. The manifest
 * is itself the last artefact, so a consumer can verify the whole tree from
 * one file without trusting the generator's output on faith.
 */
import { createHash } from 'node:crypto';
import { GENERATOR_NAME, GENERATOR_VERSION, LICENCE, ORIGINAL_WORK_STATEMENT } from './version.ts';

export interface Artifact {
  /** POSIX-style path, relative to `assets/original/`. */
  readonly path: string;
  readonly bytes: Uint8Array;
}

export interface ProvenanceEntry {
  readonly path: string;
  readonly bytes: number;
  readonly sha256: string;
  readonly generator: string;
  readonly generatorVersion: string;
  readonly licence: string;
  readonly statement: string;
}

export interface ProvenanceManifest {
  readonly name: string;
  readonly generator: string;
  readonly generatorVersion: string;
  readonly licence: string;
  readonly statement: string;
  readonly method: string;
  readonly files: readonly ProvenanceEntry[];
}

/** SHA-256 of the exact bytes that are written to disk. */
export function sha256(bytes: Uint8Array): string {
  return createHash('sha256').update(bytes).digest('hex');
}

export function manifestFor(files: readonly Artifact[]): ProvenanceManifest {
  return {
    name: 'Social Wars Legacy original assets',
    generator: GENERATOR_NAME,
    generatorVersion: GENERATOR_VERSION,
    licence: LICENCE,
    statement: ORIGINAL_WORK_STATEMENT,
    method:
      'SVG geometry is assembled from fixed integer coordinate tables and WAV samples ' +
      'are synthesised from a seeded 32-bit generator. No input file is read.',
    files: files.map((file) => ({
      path: file.path,
      bytes: file.bytes.byteLength,
      sha256: sha256(file.bytes),
      generator: GENERATOR_NAME,
      generatorVersion: GENERATOR_VERSION,
      licence: LICENCE,
      statement: ORIGINAL_WORK_STATEMENT,
    })),
  };
}

/** Stable JSON: two generations of the same files give the same bytes. */
export function manifestBytes(manifest: ProvenanceManifest): Uint8Array {
  return new TextEncoder().encode(`${JSON.stringify(manifest, null, 2)}\n`);
}

/** Bytewise equality, used by the CLI's `--check` mode. */
export function equalBytes(a: Uint8Array, b: Uint8Array): boolean {
  if (a.byteLength !== b.byteLength) return false;
  for (let i = 0; i < a.byteLength; i += 1) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}
