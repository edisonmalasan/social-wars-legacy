/**
 * @swl/art — the **browser-safe** entry point.
 *
 * This module re-exports only the generator's pure, platform-free modules:
 * the version constants, the seeded random generator, the SVG primitives,
 * the Foundry motifs and the WAV synthesiser. Every one of them is a pure
 * function of its arguments, uses only web-standard globals (`Math`,
 * `TextEncoder`, `DataView`, `Int16Array`) and imports nothing from `node:`.
 *
 * The package's other modules are deliberately **not** re-exported here:
 *
 * - `io.ts` uses `node:fs` to write the generated tree to disk.
 * - `manifest.ts` uses `node:crypto` for SHA-256 provenance digests.
 * - `artifacts.ts` composes `manifest.ts`, so it inherits `node:crypto`.
 *
 * Those remain available from the package root for the CLI and the tests.
 * The web, desktop and mobile clients import this entry instead, so the
 * browser's module graph never reaches a platform built-in. The Node test
 * suite walks this graph and asserts that no `node:` import is reachable.
 */
export * from './src/version.ts';
export * from './src/random.ts';
export * from './src/svg.ts';
export * from './src/icons.ts';
export * from './src/wav.ts';
