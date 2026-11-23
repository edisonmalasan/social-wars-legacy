/**
 * Opt-in neutral content bundle build.
 *
 * Input   content/neutral/v1/**  (the independently authored CC0-1.0 seed)
 * Output  packages/content/dist/neutral/content-bundle.json
 *
 * This is NOT the shipped build. It never reads a vendored reference tree, the
 * decompiled client, a captured snapshot or the network. Every input path is
 * cleared by the isolation guard in `scripts/check-neutral-content.mjs` before
 * a single byte is read, and the seed itself is validated by that same guard's
 * `validateSeed()` before a bundle is assembled.
 *
 * The output is shape-compatible with `packages/content/src/schema.ts`: every
 * gameplay field is the type the runtime already consumes. The two
 * reference-tree provenance fields (`upstreamCommit`, `patchesApplied`) are
 * **absent** and replaced by the neutral provenance of CONTENT-REPLACEMENT.md
 * §5.4. The `formatVersion` is deliberately left at 1: changing it is a
 * separate, reviewed migration step, and this opt-in build never switches the
 * default bundle.
 *
 * Usage:
 *   node packages/content/src/neutral-cli.ts             # build and write
 *   node packages/content/src/neutral-cli.ts --check      # validate only
 *   node packages/content/src/neutral-cli.ts --out <file> # write somewhere else
 */

import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { gameplayArtPath } from '../../art/src/gameplay.ts';
import type { ContentBundle, ContentGoal, ContentItem } from './schema.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '../../..');

/** The only directory this build may read from. */
export const NEUTRAL_SEED = path.join(REPO_ROOT, 'content', 'neutral', 'v1');
/** Generated, ignored output lives beside the legacy bundle but never over it. */
export const NEUTRAL_OUT_DIR = path.join(REPO_ROOT, 'packages', 'content', 'dist', 'neutral');
export const NEUTRAL_BUNDLE_PATH = path.join(NEUTRAL_OUT_DIR, 'content-bundle.json');

/** The existing guard, loaded through the CJS bridge so the .mjs needs no .d.ts. */
const GUARD_PATH = path.join(REPO_ROOT, 'scripts', 'check-neutral-content.mjs');

interface NeutralGuard {
  assertAllowedRead(filePath: string): string;
  validateSeed(): Promise<string[]>;
}

const requireFromHere = createRequire(import.meta.url);
const guard = requireFromHere(GUARD_PATH) as NeutralGuard;

export interface NeutralBuildInput {
  readonly path: string;
  readonly sha256: string;
}

interface SeedProvenance {
  readonly specVersion: string;
  readonly specRevision: string;
  readonly authoringMethod: string;
  readonly licence: string;
  readonly artGenerator: string;
  readonly statement: string;
  readonly buildInputs: NeutralBuildInput[];
}

interface SeedVocabulary {
  readonly categories: Record<string, unknown>;
}

/**
 * The neutral bundle: the shipped `ContentBundle` minus the two fields that
 * describe copied data, plus the authored provenance that replaces them.
 */
export type NeutralBundle = Omit<ContentBundle, 'upstreamCommit' | 'patchesApplied'> & {
  specVersion: string;
  specRevision: string;
  authoringMethod: string;
  licence: string;
  artGenerator: string;
  buildInputs: NeutralBuildInput[];
  statement: string;
};

export class NeutralBuildError extends Error {
  readonly problems: string[];

  constructor(message: string, problems: string[] = []) {
    super(problems.length ? `${message}\n  - ${problems.join('\n  - ')}` : message);
    this.name = 'NeutralBuildError';
    this.problems = problems;
  }
}

/** Read text only after the shared guard has cleared the path. */
function guardedText(name: string): Promise<string> {
  return readFile(guard.assertAllowedRead(path.join(NEUTRAL_SEED, name)), 'utf8');
}

async function guardedJson<T>(name: string): Promise<T> {
  return JSON.parse(await guardedText(name)) as T;
}

/** Canonical JSON: sorted keys, no whitespace, stable array order. */
export function canonicaliseNeutral(value: unknown): string {
  const seen = new WeakSet<object>();
  const walk = (v: unknown): unknown => {
    if (v === null || typeof v !== 'object') return v;
    if (seen.has(v as object)) throw new Error('circular structure in the neutral bundle');
    seen.add(v as object);
    if (Array.isArray(v)) return v.map(walk);
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(v as Record<string, unknown>).sort()) {
      out[key] = walk((v as Record<string, unknown>)[key]);
    }
    return out;
  };
  return JSON.stringify(walk(value));
}

/** Validate the seed through the guard, then assemble the reproducible bundle. */
export async function buildNeutralBundle(): Promise<NeutralBundle> {
  const problems = await guard.validateSeed();
  if (problems.length > 0) {
    throw new NeutralBuildError('the neutral content seed is not valid', problems);
  }

  const provenance = await guardedJson<SeedProvenance>('provenance.json');
  const vocabulary = await guardedJson<SeedVocabulary>('vocabulary.json');
  const items = await guardedJson<ContentItem[]>('items.json');
  const goals = await guardedJson<ContentGoal[]>('goals.json');
  const globals = await guardedJson<Record<string, unknown>>('globals.json');

  // Array order is authored, but sorting by id makes the bytes independent of
  // the order a file happens to list its rows in.
  items.sort((a, b) => a.id - b.id);
  goals.sort((a, b) => a.id - b.id);

  const propertyKeys: Record<string, number> = {};
  const subcatFunctionals: Record<string, number> = {};
  const images: Record<string, string> = {};
  for (const item of items) {
    for (const key of Object.keys(item.properties)) {
      propertyKeys[key] = (propertyKeys[key] ?? 0) + 1;
    }
    const scf = String(item.subcat_functional);
    subcatFunctionals[scf] = (subcatFunctionals[scf] ?? 0) + 1;
    for (const artKey of item.img_name.split(',').map((v) => v.trim()).filter(Boolean)) {
      // The guard has already proved this key resolves to a manifested
      // @swl/art artefact; this stores only its relative, deterministic path.
      images[artKey] = gameplayArtPath(artKey);
    }
  }

  const bundle: NeutralBundle = {
    formatVersion: 1,
    buildId: '',
    specVersion: provenance.specVersion,
    specRevision: provenance.specRevision,
    authoringMethod: provenance.authoringMethod,
    licence: provenance.licence,
    artGenerator: provenance.artGenerator,
    buildInputs: provenance.buildInputs,
    statement: provenance.statement,
    items,
    levels: [],
    goals,
    questRosters: [],
    questEvents: {},
    globals,
    collections: [],
    inventoryItems: {},
    offerPacks: [],
    socialItems: [],
    images,
    sounds: [],
    dartsItems: [],
    unitCollectionCategories: {},
    magics: [],
    expansionPrices: [],
    neighborAssists: [],
    townPrices: [],
    mapPrices: [],
    findableItems: [],
    levelRankingReward: [],
    categories: vocabulary.categories,
    clientOnlyItemIds: [],
    assetlessItemIds: [],
    propertyKeys,
    subcatFunctionals,
  };

  bundle.buildId = createHash('sha256')
    .update(canonicaliseNeutral({ ...bundle, buildId: '' }))
    .digest('hex');
  return bundle;
}

/** Write the canonical bundle bytes (with a trailing newline, like the legacy build). */
export async function writeNeutralBundle(
  bundle: NeutralBundle,
  outFile: string = NEUTRAL_BUNDLE_PATH,
): Promise<string> {
  await mkdir(path.dirname(outFile), { recursive: true });
  await writeFile(outFile, `${canonicaliseNeutral(bundle)}\n`, 'utf8');
  return outFile;
}

/** The summary prints only neutral provenance, never the removed fields. */
export function neutralSummary(bundle: NeutralBundle): string[] {
  return [
    `spec version       : ${bundle.specVersion}`,
    `spec revision      : ${bundle.specRevision}`,
    `authoring method   : ${bundle.authoringMethod}`,
    `licence            : ${bundle.licence}`,
    `art generator      : ${bundle.artGenerator}`,
    `build inputs       : ${bundle.buildInputs.length}`,
    `items              : ${bundle.items.length}`,
    `goals              : ${bundle.goals.length}`,
    `globals            : ${Object.keys(bundle.globals).length}`,
    `neutral art keys   : ${Object.keys(bundle.images).length}`,
    `property keys      : ${Object.keys(bundle.propertyKeys).length}`,
    `build id           : ${bundle.buildId}`,
  ];
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const check = args.includes('--check');
  const outIndex = args.indexOf('--out');
  const outFile =
    outIndex >= 0 && args[outIndex + 1]
      ? path.resolve(args[outIndex + 1]!)
      : NEUTRAL_BUNDLE_PATH;

  const bundle = await buildNeutralBundle();
  for (const line of neutralSummary(bundle)) console.log(line);

  if (!check) {
    const file = await writeNeutralBundle(bundle, outFile);
    console.log(`\nwrote ${file}`);
  }
}

const invokedDirectly = process.argv[1]
  ? path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
  : false;

if (invokedDirectly) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
