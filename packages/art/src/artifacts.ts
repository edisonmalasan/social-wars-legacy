/**
 * The whole generated tree, in memory. Nothing in this module performs I/O.
 */
import { buildFxFrames } from './fx.ts';
import { buildIcons } from './icons.ts';
import { manifestBytes, manifestFor, type Artifact } from './manifest.ts';
import { CC0_NOTICE } from './version.ts';
import { buildSounds } from './wav.ts';

export type { Artifact } from './manifest.ts';

/** Build every file the generator owns, including its notice and manifest. */
export function buildArtifacts(): Artifact[] {
  const files: Artifact[] = [...buildIcons(), ...buildFxFrames(), ...buildSounds()];
  files.push({ path: 'LICENSE', bytes: new TextEncoder().encode(CC0_NOTICE) });
  files.push({ path: 'manifest.json', bytes: manifestBytes(manifestFor(files)) });
  return files;
}
