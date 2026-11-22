#!/usr/bin/env node
/**
 * Validate the v1 neutral content seed.
 *
 * The seed under `content/neutral/v1/` is an independently authored, CC0-1.0
 * content sample. It is NOT the shipped bundle and it does NOT switch the
 * build. This check proves that the seed is internally consistent and that it
 * stays isolated from the reference trees:
 *
 *   - the CC0 notice and the provenance manifest are present;
 *   - every declared input hashes to its recorded SHA-256, and the input list
 *     is closed (no undeclared file, no omitted file);
 *   - `specRevision` matches the canonical concatenation of those inputs;
 *   - ids, slugs and categories are unique and in the v1 namespace;
 *   - every item has the exact `ContentItem` shape with neutral values, and
 *     every `img_name` key resolves to an @swl/art gameplay motif that has a
 *     generated artefact with a manifest entry;
 *   - no reference-tree provenance field survives in the authored data;
 *   - and every read the validator performs is refused unless it resolves
 *     inside the seed root. A read under `upstream/` or `re/` is a hard fail.
 *
 * Usage:
 *   node scripts/check-neutral-content.mjs
 *   node scripts/check-neutral-content.mjs --plant-prohibited-read
 */
import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { gameplayArtPath, gameplayKeys } from '../packages/art/src/gameplay.ts';
import { buildArtifacts } from '../packages/art/src/artifacts.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SEED = path.join(ROOT, 'content', 'neutral', 'v1');
const SEED_REL = 'content/neutral/v1';
const MANIFEST = 'provenance.json';
const NOTICE = 'LICENSE-CC0.txt';

/** First path segment under the repo root that the seed must never read. */
const PROHIBITED_ROOTS = new Set(['upstream', 're']);
/** Reads performed through the guarded helpers, for the final assertion. */
const reads = [];

/** Refuse (and record) any path outside the neutral seed root. */
export function assertAllowedRead(filePath) {
  const resolved = path.resolve(filePath);
  const relative = path.relative(ROOT, resolved).split(path.sep).join('/');
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`the seed guard refused a path outside the repository: ${filePath}`);
  }
  const first = relative.split('/')[0] ?? '';
  if (PROHIBITED_ROOTS.has(first)) {
    throw new Error(`prohibited read of a reference tree during validation: ${relative}`);
  }
  if (relative !== SEED_REL && !relative.startsWith(`${SEED_REL}/`)) {
    throw new Error(`the seed guard refused a path outside the seed root: ${relative}`);
  }
  reads.push(relative);
  return resolved;
}

/** Read bytes only after the path has cleared the guard. */
async function guardedBytes(filePath) {
  return readFile(assertAllowedRead(filePath));
}

/** Read text only after the path has cleared the guard. */
async function guardedText(filePath) {
  return readFile(assertAllowedRead(filePath), 'utf8');
}

/** List a directory only after the path has cleared the guard. */
async function guardedNames(dir) {
  return readdir(assertAllowedRead(dir));
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

/** Canonical JSON: sorted keys, no whitespace. Mirrors the content build. */
function canonical(value) {
  const seen = new WeakSet();
  const walk = (v) => {
    if (v === null || typeof v !== 'object') return v;
    if (seen.has(v)) throw new Error('circular structure in the neutral seed');
    seen.add(v);
    if (Array.isArray(v)) return v.map(walk);
    const out = {};
    for (const key of Object.keys(v).sort()) out[key] = walk(v[key]);
    return out;
  };
  return JSON.stringify(walk(value));
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isInt(value) {
  return Number.isInteger(value);
}

function parseJson(text, where, problems) {
  try {
    return JSON.parse(text);
  } catch (error) {
    problems.push(`${where} is not valid JSON: ${error.message}`);
    return null;
  }
}

/** The exact field set of `ContentItem` in packages/content/src/schema.ts. */
const ITEM_FIELDS = [
  'id', 'name', 'type', 'category_id', 'subcategory_id', 'subcat_functional',
  'img_name', 'attack', 'defense', 'life', 'attack_range', 'attack_interval',
  'velocity', 'population', 'cost', 'cost_type', 'costs', 'properties',
  'best_against', 'best_against_mult', 'trains_ids', 'upgrades_to',
  'unit_capacity', 'building_limit_same_id', 'building_limit_same_scf',
  'width', 'height', 'min_level', 'display_order', 'build_time',
  'clicks_to_build', 'training_time', 'xp', 'activation', 'collect',
  'collect_type', 'collect_xp', 'max_collects', 'group_type', 'race',
  'in_store', 'giftable', 'gift_level', 'cost_unit_cash', 'volume',
  'max_elem_vol', 'inventory_ids', 'premium_upgrade_costs', 'properties_raw',
  'extra',
];

const INT_FIELDS = [
  'id', 'category_id', 'subcategory_id', 'subcat_functional', 'attack',
  'defense', 'life', 'attack_range', 'attack_interval', 'velocity',
  'population', 'cost', 'best_against_mult', 'unit_capacity',
  'building_limit_same_id', 'building_limit_same_scf', 'width', 'height',
  'min_level', 'display_order', 'build_time', 'clicks_to_build',
  'training_time', 'xp', 'activation', 'collect', 'collect_xp',
  'max_collects', 'gift_level', 'cost_unit_cash', 'volume', 'max_elem_vol',
];
const STRING_FIELDS = [
  'name', 'type', 'img_name', 'collect_type', 'group_type', 'race',
  'properties_raw',
];
const BOOL_FIELDS = ['in_store', 'giftable'];
const NUMBER_RECORDS = ['costs', 'inventory_ids', 'premium_upgrade_costs'];

/** Any object carrying a reference-tree provenance field is a hard failure. */
function scanForbiddenProvenance(value, where, problems) {
  if (Array.isArray(value)) {
    value.forEach((entry, i) => scanForbiddenProvenance(entry, `${where}[${i}]`, problems));
    return;
  }
  if (!isObject(value)) return;
  for (const [key, child] of Object.entries(value)) {
    if (key === 'upstreamCommit' || key === 'patchesApplied') {
      problems.push(`${where} carries a reference-tree provenance field: ${key}`);
    }
    scanForbiddenProvenance(child, `${where}.${key}`, problems);
  }
}

/** Check one item against the exact schema shape. */
function checkItemShape(item, where, problems) {
  if (!isObject(item)) {
    problems.push(`${where} is not an object`);
    return;
  }
  const keys = Object.keys(item).sort().join(',');
  const expected = [...ITEM_FIELDS].sort().join(',');
  if (keys !== expected) {
    const missing = ITEM_FIELDS.filter((f) => !(f in item));
    const unknown = Object.keys(item).filter((f) => !ITEM_FIELDS.includes(f));
    problems.push(
      `${where} does not match the ContentItem shape (missing: ${missing.join(', ') || 'none'}; ` +
        `unknown: ${unknown.join(', ') || 'none'})`,
    );
  }
  for (const field of INT_FIELDS) {
    if (!isInt(item[field])) problems.push(`${where}.${field} must be an integer`);
  }
  for (const field of STRING_FIELDS) {
    if (typeof item[field] !== 'string') problems.push(`${where}.${field} must be a string`);
  }
  for (const field of BOOL_FIELDS) {
    if (typeof item[field] !== 'boolean') problems.push(`${where}.${field} must be a boolean`);
  }
  if (item.cost_type !== null) problems.push(`${where}.cost_type must be null`);
  if (item.best_against !== null && typeof item.best_against !== 'string') {
    problems.push(`${where}.best_against must be null or a string`);
  }
  if (item.upgrades_to !== null && !isInt(item.upgrades_to)) {
    problems.push(`${where}.upgrades_to must be null or an integer`);
  }
  for (const field of NUMBER_RECORDS) {
    if (!isObject(item[field])) {
      problems.push(`${where}.${field} must be an object of numbers`);
      continue;
    }
    for (const [key, value] of Object.entries(item[field])) {
      if (!isInt(value)) problems.push(`${where}.${field}.${key} must be an integer`);
    }
  }
  if (!isObject(item.properties)) problems.push(`${where}.properties must be an object`);
  if (!isObject(item.extra) || Object.keys(item.extra).length !== 0) {
    problems.push(`${where}.extra must be an empty object in v1`);
  }
  if (!Array.isArray(item.trains_ids) || !item.trains_ids.every(isInt)) {
    problems.push(`${where}.trains_ids must be an array of integers`);
  }
}

/** Detect a self-referential upgrade chain, not just a direct self-reference. */
function checkUpgradeCycles(items, problems) {
  const byId = new Map(items.map((item) => [item.id, item]));
  for (const item of items) {
    const seen = new Set([item.id]);
    let next = item.upgrades_to;
    while (next !== null) {
      if (seen.has(next)) {
        problems.push(`item ${item.id} has a self-referential upgrade chain`);
        break;
      }
      seen.add(next);
      next = byId.get(next)?.upgrades_to ?? null;
    }
  }
}

/** Run every check and return the list of problems (empty means valid). */
export async function validateSeed() {
  const problems = [];
  reads.length = 0;

  // --- 1. The closed input set and its hashes ------------------------------
  const manifestText = await guardedText(path.join(SEED, MANIFEST));
  const manifest = parseJson(manifestText, MANIFEST, problems);
  if (manifest === null) return problems;

  if (manifest.specVersion !== 'v1') problems.push('specVersion must be "v1"');
  if (manifest.authoringMethod !== 'clean-room-authorship') {
    problems.push('authoringMethod must be "clean-room-authorship"');
  }
  if (manifest.licence !== 'CC0-1.0') problems.push('licence must be "CC0-1.0"');
  if (typeof manifest.artGenerator !== 'string' || !/^@swl\/art@\d+\.\d+\.\d+$/.test(manifest.artGenerator)) {
    problems.push('artGenerator must identify @swl/art and its version');
  }
  if (
    typeof manifest.statement !== 'string' ||
    !/^Original work:/.test(manifest.statement) ||
    !/No file from the reference trees/.test(manifest.statement)
  ) {
    problems.push('the original-work statement is missing or incomplete');
  }

  const notice = await guardedText(path.join(SEED, NOTICE));
  if (!/CC0\s*1\.0/i.test(notice) || !/waiv/i.test(notice)) {
    problems.push('the CC0 notice is missing or incomplete');
  }

  if (!Array.isArray(manifest.buildInputs) || manifest.buildInputs.length < 2) {
    problems.push('buildInputs must be a non-trivial list');
  } else {
    const actual = (await guardedNames(SEED))
      .filter((name) => name !== MANIFEST)
      .sort();
    const listed = manifest.buildInputs.map((entry) => entry?.path).sort();
    if (listed.join('\n') !== actual.join('\n')) {
      problems.push(
        `buildInputs is not closed (listed: ${listed.join(', ')}; on disk: ${actual.join(', ')})`,
      );
    }
    const hashes = new Map();
    for (const entry of manifest.buildInputs) {
      if (
        !isObject(entry) ||
        typeof entry.path !== 'string' ||
        !/^[A-Za-z0-9._-]+$/.test(entry.path) ||
        typeof entry.sha256 !== 'string' ||
        !/^[0-9a-f]{64}$/.test(entry.sha256)
      ) {
        problems.push(`malformed buildInput entry: ${JSON.stringify(entry)}`);
        continue;
      }
      if (hashes.has(entry.path)) problems.push(`duplicate buildInput: ${entry.path}`);
      const bytes = await guardedBytes(path.join(SEED, entry.path));
      const actualHash = sha256(bytes);
      if (actualHash !== entry.sha256) {
        problems.push(`hash mismatch for ${entry.path}: recorded ${entry.sha256}, got ${actualHash}`);
      }
      hashes.set(entry.path, entry.sha256);
    }
    const lines = [...hashes.entries()].map(([p, h]) => `${p}:${h}`).sort();
    const revision = sha256(Buffer.from(`${lines.join('\n')}\n`, 'utf8'));
    if (manifest.specRevision !== revision) {
      problems.push(`specRevision mismatch: recorded ${manifest.specRevision}, computed ${revision}`);
    }
  }

  // --- 2. Vocabulary and the v1 id namespace -------------------------------
  const vocab = parseJson(await guardedText(path.join(SEED, 'vocabulary.json')), 'vocabulary.json', problems);
  if (vocab === null) return problems;
  if (vocab.namespace !== 'v1') problems.push('vocabulary.namespace must be "v1"');
  const categories = vocab.categories;
  const categoryIds = new Set();
  if (!isObject(categories) || Object.keys(categories).length < 5) {
    problems.push('vocabulary.categories must define all five neutral groups');
  } else {
    for (const [key, value] of Object.entries(categories)) {
      if (!isObject(value) || !isInt(value.id) || typeof value.name !== 'string') {
        problems.push(`malformed category ${key}`);
        continue;
      }
      if (categoryIds.has(value.id)) problems.push(`duplicate category id: ${value.id}`);
      categoryIds.add(value.id);
    }
  }
  for (const expected of ['production', 'defense', 'army', 'support', 'decoration']) {
    if (!Object.hasOwn(categories ?? {}, expected)) problems.push(`missing category: ${expected}`);
  }
  const categoryKeyById = new Map(
    Object.entries(isObject(categories) ? categories : {}).map(([key, value]) => [value?.id, key]),
  );

  const allocation = vocab.allocation;
  const slugById = new Map();
  if (!Array.isArray(allocation) || allocation.length < 12) {
    problems.push('vocabulary.allocation must reserve at least 12 ids');
  } else {
    const slugs = new Set();
    for (const entry of allocation) {
      if (
        !isObject(entry) ||
        typeof entry.slug !== 'string' ||
        !/^(production|defense|army|support|decoration)\.[a-z0-9]+(?:\.[a-z0-9]+)?$/.test(entry.slug) ||
        !isInt(entry.id) ||
        entry.id < vocab.idRange?.start ||
        entry.id > vocab.idRange?.end
      ) {
        problems.push(`malformed allocation entry: ${JSON.stringify(entry)}`);
        continue;
      }
      if (slugs.has(entry.slug)) problems.push(`duplicate slug: ${entry.slug}`);
      if (slugById.has(entry.id)) problems.push(`duplicate allocated id: ${entry.id}`);
      slugs.add(entry.slug);
      slugById.set(entry.id, entry.slug);
    }
  }

  const resourceKeys = new Set(Object.values(vocab.resources ?? {}));
  if (resourceKeys.size === 0) problems.push('vocabulary.resources is empty');
  const subcategoryValues = new Set(Object.values(vocab.subcategories ?? {}));
  const roleValues = new Set(Object.values(vocab.functionalRoles ?? {}));
  const counterClasses = new Set(vocab.counterClasses ?? []);
  const propertyKeys = new Set(vocab.propertyKeys ?? []);
  const factions = new Set(Object.values(vocab.factions ?? {}));
  if (!isObject(vocab.keyMap)) problems.push('vocabulary.keyMap must be an object');

  // --- 3. Items -------------------------------------------------------------
  const items = parseJson(await guardedText(path.join(SEED, 'items.json')), 'items.json', problems);
  if (!Array.isArray(items)) {
    problems.push('items.json must contain an array');
    return problems;
  }
  if (items.length < 12) problems.push(`only ${items.length} items; at least 12 are required`);

  const motifKeys = new Set(gameplayKeys());
  const artPaths = new Set(buildArtifacts().map((artifact) => artifact.path));
  const itemIds = new Set();
  const covered = new Set();
  for (const [index, item] of items.entries()) {
    const where = `items[${index}]`;
    checkItemShape(item, where, problems);
    if (!isObject(item)) continue;
    if (itemIds.has(item.id)) problems.push(`duplicate item id: ${item.id}`);
    itemIds.add(item.id);
    if (!slugById.has(item.id)) problems.push(`${where} uses an id outside the allocation table: ${item.id}`);
    const slug = slugById.get(item.id);
    const categoryKey = categoryKeyById.get(item.category_id);
    if (slug !== undefined && categoryKey !== undefined && !slug.startsWith(`${categoryKey}.`)) {
      problems.push(`${where} id ${item.id} has a slug in a different category`);
    }
    if (!categoryIds.has(item.category_id)) problems.push(`${where} has an unknown category_id: ${item.category_id}`);
    else covered.add(item.category_id);
    if (!subcategoryValues.has(item.subcategory_id)) problems.push(`${where} has an unknown subcategory_id: ${item.subcategory_id}`);
    if (!roleValues.has(item.subcat_functional)) problems.push(`${where} has an unknown subcat_functional: ${item.subcat_functional}`);
    if (typeof item.name !== 'string' || item.name.trim() === '' || item.name.length > 40) {
      problems.push(`${where} has an invalid authored name`);
    }
    if (item.type !== 'b' && item.type !== 'u') problems.push(`${where} has an unknown type: ${item.type}`);
    if (!factions.has(item.race)) problems.push(`${where} has an unknown faction: ${item.race}`);

    // Art keys are neutral @swl/art gameplay motifs, never SWF or symbol names.
    if (typeof item.img_name === 'string') {
      for (const key of item.img_name.split(',').map((v) => v.trim()).filter(Boolean)) {
        if (/[\\/]|\.(?:swf|fla|atlas|png|jpe?g|svg)\b/i.test(key)) {
          problems.push(`${where}.img_name is a filename or path, not a neutral art key: ${key}`);
        } else if (!motifKeys.has(key)) {
          problems.push(`${where}.img_name is not a known @swl/art gameplay motif: ${key}`);
        } else if (!artPaths.has(gameplayArtPath(key))) {
          problems.push(`${where}.img_name has no @swl/art manifest entry: ${key}`);
        }
      }
    }

    if (isObject(item.costs)) {
      for (const [key, value] of Object.entries(item.costs)) {
        if (!resourceKeys.has(key) || value <= 0) problems.push(`${where}.costs has an invalid entry: ${key}=${value}`);
      }
    }
    if (item.collect_type !== '' && !resourceKeys.has(item.collect_type)) {
      problems.push(`${where}.collect_type is not a neutral resource key: ${item.collect_type}`);
    }
    if (item.collect > 0 && !resourceKeys.has(item.collect_type)) {
      problems.push(`${where} collects without a resource key`);
    }
    if (isObject(item.properties)) {
      for (const key of Object.keys(item.properties)) {
        if (!propertyKeys.has(key)) problems.push(`${where}.properties has an unknown neutral key: ${key}`);
      }
      const serialized = canonical(item.properties);
      if (item.properties_raw !== serialized) {
        problems.push(`${where}.properties_raw is not the canonical form of its properties`);
      }
    }
    if (item.best_against !== null && !counterClasses.has(item.best_against)) {
      problems.push(`${where}.best_against is not a neutral counter class: ${item.best_against}`);
    }
    if (item.best_against_mult < 1) problems.push(`${where}.best_against_mult must be at least 1`);
    if (item.width < 1 || item.height < 1) problems.push(`${where} has an invalid footprint`);
  }

  for (const expectedId of categoryIds) {
    if (!covered.has(expectedId)) problems.push(`category ${expectedId} has no authored item`);
  }
  for (const item of items) {
    if (!isObject(item) || !Array.isArray(item.trains_ids)) continue;
    for (const trained of item.trains_ids) {
      if (!itemIds.has(trained)) problems.push(`item ${item.id} trains missing unit ${trained}`);
    }
    if (item.upgrades_to !== null && !itemIds.has(item.upgrades_to)) {
      problems.push(`item ${item.id} upgrades to a missing item ${item.upgrades_to}`);
    }
  }
  checkUpgradeCycles(items.filter(isObject), problems);

  // --- 4. Globals and goals -------------------------------------------------
  const globals = parseJson(await guardedText(path.join(SEED, 'globals.json')), 'globals.json', problems);
  if (!isObject(globals) || Object.keys(globals).length === 0) {
    problems.push('globals.json must be a non-empty authored object');
  } else {
    scanForbiddenProvenance(globals, 'globals', problems);
  }
  const goals = parseJson(await guardedText(path.join(SEED, 'goals.json')), 'goals.json', problems);
  if (!Array.isArray(goals) || goals.length === 0) {
    problems.push('goals.json must be a non-empty authored array');
  } else {
    const goalIds = new Set();
    for (const [index, goal] of goals.entries()) {
      const where = `goals[${index}]`;
      if (
        !isObject(goal) ||
        !isInt(goal.id) ||
        typeof goal.title !== 'string' ||
        typeof goal.description !== 'string' ||
        typeof goal.hint !== 'string' ||
        !isObject(goal.reward)
      ) {
        problems.push(`${where} does not match the ContentGoal shape`);
        continue;
      }
      if (goalIds.has(goal.id)) problems.push(`duplicate goal id: ${goal.id}`);
      goalIds.add(goal.id);
      scanForbiddenProvenance(goal.reward, `${where}.reward`, problems);
    }
  }

  // --- 5. The isolation guard itself ---------------------------------------
  for (const read of reads) {
    const first = read.split('/')[0] ?? '';
    if (PROHIBITED_ROOTS.has(first) || (read !== SEED_REL && !read.startsWith(`${SEED_REL}/`))) {
      problems.push(`the validator read outside the seed root: ${read}`);
    }
  }

  return problems;
}

/** The planted-read check: the guard must refuse a reference-tree path. */
export function plantProhibitedRead() {
  let message = '';
  let refused = false;
  try {
    assertAllowedRead(path.join(ROOT, 'upstream', 'socialwarriors', 'config', 'main.json'));
  } catch (error) {
    refused = /prohibited read of a reference tree/.test(error.message);
    message = error.message;
  }
  return { refused, message };
}

const invokedDirectly = process.argv[1]
  ? path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
  : false;

if (invokedDirectly) {
  if (process.argv.includes('--plant-prohibited-read')) {
    const result = plantProhibitedRead();
    if (!result.refused) {
      console.error('the isolation guard did not refuse the planted read');
      process.exit(1);
    }
    console.log(`planted prohibited read was refused by the guard: ${result.message}`);
    process.exit(0);
  }
  validateSeed()
    .then((problems) => {
      if (problems.length > 0) {
        console.error('the neutral content seed is not valid:');
        for (const problem of problems) console.error(`  ${problem}`);
        process.exit(1);
      }
      console.log('neutral content seed OK (v1)');
      console.log('  CC0 notice and provenance manifest present');
      console.log(`  ${reads.length} guarded reads, all inside content/neutral/v1`);
      console.log(`  ${gameplayKeys().length} @swl/art gameplay motifs available for art-key resolution`);
      console.log('  OK: validation passed');
    })
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}
