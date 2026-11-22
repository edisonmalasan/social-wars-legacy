/**
 * @swl/art — deterministic, clean-room original art and audio.
 *
 * The core is pure: `buildArtifacts()` returns bytes and reads nothing.
 * Only `io.ts` touches the filesystem, and the CLI composes the two.
 */
export * from './version.ts';
export * from './random.ts';
export * from './svg.ts';
export * from './icons.ts';
export * from './wav.ts';
export * from './manifest.ts';
export * from './artifacts.ts';
export * from './io.ts';
