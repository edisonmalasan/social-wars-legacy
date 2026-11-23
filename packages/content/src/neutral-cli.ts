/**
 * Explicit opt-in build of the **neutral** content bundle.
 *
 * This is NOT the shipped bundle. It is a separate, verifiable artefact built
 * from the independently authored, CC0-1.0 seed under `content/neutral/v1/`
 * and nothing else. Switching the shipped tree to this bundle is a deliberate
 * later migration step; this CLI does not do it and closes no release gate.
 *
 * Usage:
 *   node packages/content/src/neutral-cli.ts [--check] [--out <file>]
 *
 *   --check       validate the seed and the derived bundle without writing
 *   --out <file>  write somewhere other than dist/neutral/content-bundle.json
 *
 * Isolation is enforced, not asserted: every byte this module reads goes
 * through the guard exported by `scripts/check-neutral-content.mjs`, which
 * refuses anything outside the seed root and hard-fails on `upstream/` or
 * `re/`. `validateSeed()` (the same existing guard) is run before any bundle
 * is assembled. The summary prints only the neutral provenance fields; the
 * reference-tree provenance fields are deliberately absent.
 */
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { canonicalise } from './build.ts';
import type { ContentBundle, ContentGoal, ContentItem } from './schema.ts';

// The validator is a plain, dependency-free `.mjs` script with no type
// declarations. Its API is checked at runtime by this build and by its tests.
// @ts-expect-error -- plain JS script, no declaration file
import { assertAllowedRead, validateSeed } from '../../../scripts/check-neutral-content.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '../../..');
const SEED_REL = 'content/neutral/v1';
const SEED = path.join(REPO_ROOT, SEED_REL);
const OUT_DIR = path.join(REPO_ROOT, 'packages/content/dist/neutral');
const DEFAULT_OUT = path.join(OUT_DIR, 'content-bundle.json');

/** A neutral build input, relative to the seed root. */
export interface NeutralBuildInput {
  readonly path: string;
  readonly sha256: string;
}

/** The neutral replacement for the reference-tree provenance fields. */
export interface NeutralProvenance {
  readonly specVersion: string;
  readonly specRevision: string;
  readonly authoringMethod: string;
  readonly licence: string;
  readonly artGenerator: string;
  readonly buildInputs: readonly NeutralBuildInput[];
  readonly statement: string;
}

/**
 * Shape-compatible with `ContentBundle`, with the two reference-tree
 * provenance fields replaced by the neutral ones. `formatVersion` stays 1:
 * a deliberate schema migration is a separate, reviewed step and is not a
 * side effect of this opt-in build.
 */
export type NeutralBundle = Omit<ContentBundle, 'upstreamCommit' | 'patchesApplied'> &
  NeutralProvenance;

/** The result of a neutral build, including the proof of which reads it made. */
export interface NeutralBuildResult {
  readonly bundle: NeutralBundle;
  /** Every path read, relative to the repo root, in read order. */
  readonly reads: readonly string[];
}

export class NeutralBuildError extends Error {
  readonly problems: readonly string[];

  constructor(message: string, problems: readonly string[] = []) {
    super(problems.length ? `${message}\n  - ${problems.join('\n  - ')}` : message);
    this.name = 'NeutralBuildError';
    this.problems = problems;
  }
}

/** Paths this build records, so a caller can prove it stayed inside the seed. */
const reads: string[] = [];

async function guardedText(file: string): Promise<string> {
  const resolved = assertAllowedRead(file) as string;
  const relative = path.relative(REPO_ROOT, resolved).split(path.sep).join('/');
  reads.push(relative);
  return readFile(resolved, 'utf8');
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

/**
 * Tokens that must never appear in a neutral bundle. The first two are the
 * removed provenance fields; the rest are filenames and markers of the
 * reference trees, the SWF client and proprietary media.
 */
const FORBIDDEN_TOKENS: readonly RegExp[] = [
  /upstreamCommit/,
  /patchesApplied/,
  /Basesec/i,
  /\.swf\b/i,
  /\.fla\b/i,
  /\.atlas\b/i,
  /\.(?:ttf|otf|mp3|ogg)\b/i,
  /\bmain\.json\b/i,
  /\bpatches\.txt\b/i,
  /\bitem-delegate-map\.json\b/i,
  /\bquests\.json\b/i,
  /BuildingWindow\.as\b/i,
  /Quest03DefendConvoyAuto\b/i,
  /\bZynga\b/i,
  /Arial[ _-]?Rounded|Komika/i,
];

/** Build the neutral bundle from the seed. Throws on any validation problem. */
export async function buildNeutralBundle(): Promise<NeutralBuildResult> {
  reads.length = 0;
  const problems: string[] = [];

  // 1. The existing guard validates the whole seed before anything is built:
  //    closed inputs, hashes, specRevision, ids, refs, art keys and provenance.
  problems.push(...(await validateSeed()));
  if (problems.length > 0) throw new NeutralBuildError('the neutral seed is not valid', problems);

  // 2. Read the authored sources, all through the same path guard.
  const provenance = JSON.parse(await guardedText(path.join(SEED, 'provenance.json'))) as unknown;
  const vocabulary = JSON.parse(await guardedText(path.join(SEED, 'vocabulary.json'))) as unknown;
  const rawItems = JSON.parse(await guardedText(path.join(SEED, 'items.json'))) as unknown;
  const globals = JSON.parse(await guardedText(path.join(SEED, 'globals.json'))) as unknown;
  const rawGoals = JSON.parse(await guardedText(path.join(SEED, 'goals.json'))) as unknown;

  if (!isObject(provenance)) throw new NeutralBuildError('provenance.json is not an object');
  if (!isObject(vocabulary)) throw new NeutralBuildError('vocabulary.json is not an object');
  if (!Array.isArray(rawItems)) throw new NeutralBuildError('items.json is not an array');
  if (!isObject(globals)) throw new NeutralBuildError('globals.json is not an object');
  if (!Array.isArray(rawGoals)) throw new NeutralBuildError('goals.json is not an array');

  const neutralProvenance: NeutralProvenance = {
    specVersion: asString(provenance['specVersion']),
    specRevision: asString(provenance['specRevision']),
    authoringMethod: asString(provenance['authoringMethod']),
    licence: asString(provenance['licence']),
    artGenerator: asString(provenance['artGenerator']),
    buildInputs: (Array.isArray(provenance['buildInputs'])
      ? provenance['buildInputs']
      : []
    ).map((entry) => ({
      path: asString(isObject(entry) ? entry['path'] : undefined),
      sha256: asString(isObject(entry) ? entry['sha256'] : undefined),
    })),
    statement: asString(provenance['statement']),
  };

  // 3. Items and goals are already in the exact schema shape; the validator
  //    checked that. Sort by id so a reordered source file cannot change bytes.
  const items = [...rawItems].sort(
    (a: ContentItem, b: ContentItem) => a.id - b.id,
  ) as ContentItem[];
  const goals = [...rawGoals].sort(
    (a: ContentGoal, b: ContentGoal) => a.id - b.id,
  ) as ContentGoal[];

  const seenIds = new Set<number>();
  for (const item of items) {
    if (seenIds.has(item.id)) problems.push(`duplicate item id: ${item.id}`);
    seenIds.add(item.id);
  }
  for (const item of items) {
    for (const trained of item.trains_ids) {
      if (!seenIds.has(trained)) problems.push(`item ${item.id} trains missing unit ${trained}`);
    }
    if (item.upgrades_to !== null && !seenIds.has(item.upgrades_to)) {
      problems.push(`item ${item.id} upgrades to a missing item ${item.upgrades_to}`);
    }
  }

  // 4. Derived, deterministic summaries - never typed by hand.
  const propertyKeys: Record<string, number> = {};
  const subcatFunctionals: Record<string, number> = {};
  for (const item of items) {
    for (const key of Object.keys(item.properties)) {
      propertyKeys[key] = (propertyKeys[key] ?? 0) + 1;
    }
    const scf = String(item.subcat_functional);
    subcatFunctionals[scf] = (subcatFunctionals[scf] ?? 0) + 1;
  }

  const categories: Record<string, unknown> = {};
  if (isObject(vocabulary['categories'])) {
    for (const [key, value] of Object.entries(vocabulary['categories'])) {
      categories[key] = value;
    }
  }

  // The seed authors items, globals, goals and vocabulary only. Every other
  // container stays empty here rather than being filled from a reference tree.
  // `clientOnlyItemIds` is empty by construction and `assetlessItemIds` is
  // empty because the guard resolved every art key to an @swl/art motif.
  const bundle: NeutralBundle = {
    formatVersion: 1,
    buildId: '',
    specVersion: neutralProvenance.specVersion,
    specRevision: neutralProvenance.specRevision,
    authoringMethod: neutralProvenance.authoringMethod,
    licence: neutralProvenance.licence,
    artGenerator: neutralProvenance.artGenerator,
    buildInputs: neutralProvenance.buildInputs,
    statement: neutralProvenance.statement,
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
    images: {},
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
    categories,
    clientOnlyItemIds: [],
    assetlessItemIds: [],
    propertyKeys,
    subcatFunctionals,
  };

  // 5. Self-enforcing output check: the bundle must not carry a reference-tree
  //    provenance field or any prohibited token, and every declared input must
  //    stay relative to the seed root.
  const bytes = canonicalise(bundle);
  for (const token of FORBIDDEN_TOKENS) {
    if (token.test(bytes)) problems.push(`the neutral bundle contains a prohibited token: ${token}`);
  }
  for (const input of neutralProvenance.buildInputs) {
    if (input.path === '' || input.path.includes('/') || input.path.includes('\\') || input.path === '..') {
      problems.push(`buildInputs is not a neutral, seed-relative file: ${input.path}`);
    }
  }
  if (problems.length > 0) throw new NeutralBuildError('the neutral bundle is not valid', problems);

  bundle.buildId = createHash('sha256').update(canonicalise(bundle)).digest('hex');
  return { bundle, reads: [...reads] };
}

/** Write a neutral bundle as canonical bytes with a trailing newline. */
export async function writeNeutralBundle(bundle: NeutralBundle, outFile = DEFAULT_OUT): Promise<string> {
  await mkdir(path.dirname(outFile), { recursive: true });
  await writeFile(outFile, canonicalise(bundle) + '\n', 'utf8');
  return outFile;
}

export { DEFAULT_OUT, OUT_DIR, REPO_ROOT, SEED, SEED_REL };

const invokedDirectly = process.argv[1]
  ? path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
  : false;

if (invokedDirectly) {
  const args = process.argv.slice(2);
  const check = args.includes('--check');
  const outIndex = args.indexOf('--out');
  const outFile =
    outIndex >= 0 && args[outIndex + 1]
      ? path.resolve(args[outIndex + 1]!)
      : DEFAULT_OUT;

  buildNeutralBundle()
    .then(async ({ bundle, reads: usedReads }) => {
      console.log(`spec version         : ${bundle.specVersion}`);
      console.log(`spec revision        : ${bundle.specRevision}`);
      console.log(`authoring method     : ${bundle.authoringMethod}`);
      console.log(`licence              : ${bundle.licence}`);
      console.log(`art generator        : ${bundle.artGenerator}`);
      console.log(`declared inputs      : ${bundle.buildInputs.length}`);
      console.log(`items                : ${bundle.items.length}`);
      console.log(`goals                : ${bundle.goals.length}`);
      console.log(`property keys        : ${Object.keys(bundle.propertyKeys).length}`);
      console.log(`subcat_functionals   : ${Object.keys(bundle.subcatFunctionals).length}`);
      console.log(`build id             : ${bundle.buildId}`);
      console.log(`guarded reads        : ${usedReads.length} (all inside ${SEED_REL})`);
      if (!check) {
        const file = await writeNeutralBundle(bundle, outFile);
        console.log(`\nwrote ${file}`);
      }
    })
    .catch((error: unknown) => {
      console.error(error instanceof Error ? error.message : error);
      process.exit(1);
    });
}
