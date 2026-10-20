/**
 * The save-document migration.
 *
 * The upstream's save has 12 `playerInfo`, 28 `maps[]` and 47 `privateState`
 * fields, and its `privateState` is a record of what the **client** has
 * done — the daily bonus timestamp, the quest ranks, the goals in their
 * slots. It is trusted by the upstream, because the upstream trusts
 * everything.
 *
 * The new server keeps that record, because it is the client's own state
 * and it is the best starting point for a migration. It adds two things the
 * upstream never had:
 *
 * - the **production state of each building**. The upstream keeps none of
 *   it, because the client kept it: the client computes how much a factory
 *   has produced and declares the amount in the `res` vector. A server that
 *   does not trust the client has to keep the production itself.
 * - the **goal runtime state**. The upstream has no goal engine, so it has
 *   nothing to record.
 *
 * ## Forward only
 *
 * The migration only moves a save **forward**. A save from a newer version
 * is refused rather than guessed at, because guessing at a future format is
 * how a save gets silently corrupted. A save that cannot be migrated is an
 * error, not a partially-migrated document.
 */
import { createGoalState, emptyQuestProgress } from '@swl/rules';

import { GOAL_STATE_KEY, QUEST_PROGRESS_KEY } from './apply.ts';

/** The current save version. */
export const SAVE_VERSION = 1;

/**
 * The upstream's 47 `privateState` fields, with their upstream defaults.
 *
 * These come from the upstream's `villages/initial.json`, which is the
 * canonical new-player save. A field that is missing from an old save is
 * filled in from here, so a migrated save always has all 47.
 */
export const UPSTREAM_PRIVATE_STATE_DEFAULTS: Readonly<Record<string, unknown>> = {
  attacksPack: 0,
  attacksReceived: [],
  attacksSent: [],
  bestUnit: null,
  betWin: [],
  bonusNextId: 0,
  boughtUnits: [],
  collections: [],
  crossPromotionsFinished: [],
  dartsBalloonsShot: [],
  dartsGotExtra: false,
  dartsHasFree: false,
  dartsRandomSeed: 0,
  deadHeroes: {},
  energy: 50,
  firstTimeAlliance: null,
  friendsHelpedCoveredItem: null,
  goals: [null, null, null, null, null, null, null, null, null, null],
  helpMap: [],
  inventoryItems: {},
  lastUpgrades: [],
  magics: {},
  mana: 0,
  marketPlaceFirstTime: null,
  message: null,
  neighborAssists: {},
  publishedOpenGraphUnit: [],
  questsRank: {},
  researchItemNumber: [0, 0],
  researchStepNumber: [0, 0],
  spyings: [],
  spyingsPack: 0,
  strategy: 1,
  timeStampDartsNewFree: 0,
  timeStampDartsReset: 0,
  timeStampDoResearch: [0, 0],
  timeStampEndPremium: 0,
  timeStampMondayBonus: 0,
  timestampLastAllianceBonus: 0,
  timestampLastBonus: 0,
  tsAttacksReset: 0,
  tsSpyingsReset: 0,
  unitCollectionsCompleted: [],
  unlockedQuestIndex: 0,
  unlockedSkins: null,
  weeklyRewardIndex: 0,
  worldChange: 0,
};

/** The content item fields the migration needs. */
export interface MigrationItem {
  id: number;
  /** The base amount the building produces per cycle. */
  collect: number;
  /** Which resource it produces: `w`, `o`, `s`, `c` or `g`. */
  collect_type: string;
  /** How many units fit inside. */
  unit_capacity: number;
}

/** A migrated save. */
export interface SaveDocument {
  /** The save's version. */
  version: number;
  playerInfo: Record<string, unknown>;
  maps: Record<string, unknown>[];
  privateState: Record<string, unknown>;
}

/** What the migration needs. */
export interface MigrationOptions {
  /** The content items, by id. */
  items: Map<number, MigrationItem>;
}

/** The outcome of a migration. */
export interface MigrationResult {
  /** The migrated save. */
  save: SaveDocument;
  /** The version the save was at. */
  from: number;
  /** The version it is at now. */
  to: number;
  /** What the migration did, in order. */
  notes: string[];
}

/** The error a migration can fail with. */
export class MigrationError extends Error {
  /** Why the migration failed. */
  readonly reason: 'malformed-save' | 'future-version' | 'not-an-object';

  constructor(
    message: string,
    reason: 'malformed-save' | 'future-version' | 'not-an-object',
  ) {
    super(message);
    this.name = 'MigrationError';
    this.reason = reason;
  }
}

/** The version a save is at. An upstream save has no version field. */
function versionOf(save: Record<string, unknown>): number {
  const version = save['version'];
  if (version === undefined) return 0;
  if (typeof version !== 'number' || !Number.isInteger(version) || version < 0) {
    throw new MigrationError(`the save has a nonsense version: ${String(version)}`, 'malformed-save');
  }
  return version;
}

/** A shallow copy of a record, with the missing fields filled in. */
function withDefaults(
  source: Record<string, unknown>,
  defaults: Readonly<Record<string, unknown>>,
): { record: Record<string, unknown>; added: string[] } {
  const record: Record<string, unknown> = { ...source };
  const added: string[] = [];
  for (const [key, value] of Object.entries(defaults)) {
    if (!(key in record)) {
      record[key] = Array.isArray(value) ? [...value] : value;
      added.push(key);
    }
  }
  return { record, added };
}

/**
 * Migrate a save forward to the current version.
 *
 * A save that is already current is returned unchanged, apart from the
 * normalisation the current version guarantees.
 */
export function migrateSave(input: unknown, options: MigrationOptions): MigrationResult {
  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    throw new MigrationError('the save is not an object', 'not-an-object');
  }
  const raw = input as Record<string, unknown>;
  const from = versionOf(raw);

  if (from > SAVE_VERSION) {
    throw new MigrationError(
      `the save is at version ${from}, and this server only understands up to ${SAVE_VERSION}`,
      'future-version',
    );
  }

  const notes: string[] = [];
  let version = from;

  // --- the private state ------------------------------------------------
  const rawPrivate = raw['privateState'];
  if (typeof rawPrivate !== 'object' || rawPrivate === null || Array.isArray(rawPrivate)) {
    throw new MigrationError('the save has no privateState', 'malformed-save');
  }
  const { record: privateState, added } = withDefaults(
    rawPrivate as Record<string, unknown>,
    UPSTREAM_PRIVATE_STATE_DEFAULTS,
  );
  if (added.length > 0) {
    notes.push(`filled in ${added.length} missing privateState fields`);
  }

  // --- the maps ----------------------------------------------------------
  const rawMaps = raw['maps'];
  if (!Array.isArray(rawMaps)) {
    throw new MigrationError('the save has no maps', 'malformed-save');
  }
  const maps: Record<string, unknown>[] = [];
  for (const map of rawMaps) {
    if (typeof map !== 'object' || map === null || Array.isArray(map)) {
      throw new MigrationError('a map is not an object', 'malformed-save');
    }
    // The map is copied **deeply enough** that the migration cannot write
    // into the caller's tuples. A store may hand it a live object, and a
    // migration that mutates its input is a migration that corrupts a save
    // when it fails half way through.
    const copy: Record<string, unknown> = { ...(map as Record<string, unknown>) };
    const items = copy['items'];
    if (items && typeof items === 'object' && !Array.isArray(items)) {
      const copied: Record<string, unknown> = {};
      for (const [key, tuple] of Object.entries(items as Record<string, unknown>)) {
        if (Array.isArray(tuple)) {
          const newTuple = [...tuple];
          if (newTuple[6] && typeof newTuple[6] === 'object' && !Array.isArray(newTuple[6])) {
            newTuple[6] = { ...(newTuple[6] as Record<string, unknown>) };
          }
          if (Array.isArray(newTuple[5])) newTuple[5] = [...newTuple[5]];
          copied[key] = newTuple;
        } else {
          copied[key] = tuple;
        }
      }
      copy['items'] = copied;
    }
    maps.push(copy);
  }

  // --- version 0 -> 1 ----------------------------------------------------
  if (version === 0) {
    version = 1;

    // The goal runtime state and the quest progress did not exist.
    if (!(GOAL_STATE_KEY in privateState)) {
      privateState[GOAL_STATE_KEY] = createGoalState();
      notes.push('added the goal runtime state');
    }
    if (!(QUEST_PROGRESS_KEY in privateState)) {
      privateState[QUEST_PROGRESS_KEY] = emptyQuestProgress();
      notes.push('added the quest progress');
    }

    // The production state of each building did not exist.
    let producers = 0;
    for (const map of maps) {
      const items = map['items'];
      if (!items || typeof items !== 'object') continue;
      for (const tuple of Object.values(items as Record<string, unknown>)) {
        if (!Array.isArray(tuple) || tuple.length < 7) continue;
        const itemId = tuple[0];
        const attrs = tuple[6];
        if (typeof itemId !== 'number' || typeof attrs !== 'object' || attrs === null) continue;
        const item = options.items.get(itemId);
        if (!item || item.collect <= 0) continue;
        const bag = attrs as Record<string, unknown>;
        if ('collect' in bag && 'unitCapacity' in bag) continue;
        const store = Array.isArray(tuple[5]) ? tuple[5] : [];
        bag['collect'] = 0;
        bag['unitCapacity'] = item.unit_capacity;
        bag['unitsInside'] = store.length;
        bag['collectType'] = item.collect_type;
        bag['cp'] = 1;
        bag['lastAccruedAt'] = typeof map['timestamp'] === 'number' ? map['timestamp'] : 0;
        producers += 1;
      }
    }
    if (producers > 0) {
      notes.push(`added the production state of ${producers} buildings`);
    }
  }

  const save: SaveDocument = {
    version,
    playerInfo: (raw['playerInfo'] ?? {}) as Record<string, unknown>,
    maps,
    privateState,
  };

  return { save, from, to: version, notes };
}

/**
 * Whether a save needs migrating.
 *
 * A cheap check, for the store's hot path: a save that is already current
 * is not copied and not rewritten.
 */
export function needsMigration(input: unknown): boolean {
  if (typeof input !== 'object' || input === null) return true;
  const version = (input as Record<string, unknown>)['version'];
  return version !== SAVE_VERSION;
}
