import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  MigrationError,
  SAVE_VERSION,
  UPSTREAM_PRIVATE_STATE_DEFAULTS,
  migrateSave,
  needsMigration,
  type MigrationItem,
} from './migrate.ts';
import { GOAL_STATE_KEY, QUEST_PROGRESS_KEY } from './apply.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

/** The upstream's canonical new-player save. */
async function upstreamSave(): Promise<Record<string, unknown>> {
  const file = path.join(repoRoot(), 'upstream/socialwarriors/villages/initial.json');
  return JSON.parse(await readFile(file, 'utf8')) as Record<string, unknown>;
}

async function items(): Promise<Map<number, MigrationItem>> {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as {
    items: { id: number; collect: number; collect_type: string; unit_capacity: number }[];
  };
  return new Map(
    bundle.items.map((i) => [
      i.id,
      {
        id: i.id,
        collect: i.collect,
        collect_type: i.collect_type,
        unit_capacity: i.unit_capacity,
      },
    ]),
  );
}

describe('the upstream private state defaults', () => {
  it('has all 47 fields', () => {
    assert.equal(Object.keys(UPSTREAM_PRIVATE_STATE_DEFAULTS).length, 47);
  });

  it('has the fields the server depends on', () => {
    for (const key of [
      'timestampLastBonus',
      'timeStampMondayBonus',
      'timeStampEndPremium',
      'questsRank',
      'goals',
      'energy',
    ]) {
      assert.ok(key in UPSTREAM_PRIVATE_STATE_DEFAULTS, `${key} is missing`);
    }
  });
});

describe('migrating the upstream save', () => {
  it('migrates the upstream canonical save', async () => {
    const save = await upstreamSave();
    const result = migrateSave(save, { items: await items() });
    assert.equal(result.from, 0);
    assert.equal(result.to, SAVE_VERSION);
    assert.equal(result.save.version, SAVE_VERSION);
  });

  it('fills in every privateState field', async () => {
    const save = await upstreamSave();
    const result = migrateSave(save, { items: await items() });
    for (const key of Object.keys(UPSTREAM_PRIVATE_STATE_DEFAULTS)) {
      assert.ok(key in result.save.privateState, `${key} was not filled in`);
    }
  });

  it('adds the goal runtime state and the quest progress', async () => {
    const save = await upstreamSave();
    const result = migrateSave(save, { items: await items() });
    assert.ok(GOAL_STATE_KEY in result.save.privateState);
    assert.ok(QUEST_PROGRESS_KEY in result.save.privateState);
  });

  it('adds the production state of the producing buildings', async () => {
    const save = await upstreamSave();
    const result = migrateSave(save, { items: await items() });
    const items2 = result.save.maps[0]?.['items'] as Record<string, unknown[]>;
    const producers = Object.values(items2).filter((tuple) => {
      const attrs = tuple[6] as Record<string, unknown>;
      return typeof attrs?.['collect'] === 'number' && attrs['unitCapacity'] !== undefined;
    });
    assert.ok(producers.length > 0, 'no building got a production state');
    // The production starts at zero: the upstream never kept it, so the
    // server cannot know what was produced before the migration.
    for (const tuple of producers) {
      const attrs = tuple[6] as Record<string, unknown>;
      assert.equal(attrs['collect'], 0);
      assert.equal(typeof attrs['collectType'], 'string');
      assert.equal(typeof attrs['unitCapacity'], 'number');
    }
  });

  it('does not touch the player info or the map count', async () => {
    const save = await upstreamSave();
    const result = migrateSave(save, { items: await items() });
    assert.equal(
      Object.keys(result.save.playerInfo).length,
      Object.keys((save['playerInfo'] ?? {}) as Record<string, unknown>).length,
    );
    assert.equal(result.save.maps.length, (save['maps'] as unknown[]).length);
  });

  it('does not mutate the input', async () => {
    const save = await upstreamSave();
    const before = JSON.stringify(save);
    migrateSave(save, { items: await items() });
    assert.equal(JSON.stringify(save), before);
  });
});

describe('migrating a save that is already current', () => {
  it('is a no-op', async () => {
    const save = await upstreamSave();
    const options = { items: await items() };
    const once = migrateSave(save, options);
    const twice = migrateSave(once.save, options);
    assert.equal(twice.from, SAVE_VERSION);
    assert.equal(twice.to, SAVE_VERSION);
    assert.deepEqual(twice.notes, []);
    assert.deepEqual(twice.save, once.save);
  });

  it('says a current save needs no migration', async () => {
    const save = await upstreamSave();
    const options = { items: await items() };
    const once = migrateSave(save, options);
    assert.equal(needsMigration(once.save), false);
    assert.equal(needsMigration(save), true);
  });
});

describe('refusing a save the server cannot read', () => {
  it('refuses a save from a future version', async () => {
    const save = { version: SAVE_VERSION + 1 };
    assert.throws(
      () => migrateSave(save, { items: new Map() }),
      (error: unknown) =>
        error instanceof MigrationError && error.reason === 'future-version',
    );
  });

  it('refuses something that is not an object', async () => {
    assert.throws(
      () => migrateSave('nope', { items: new Map() }),
      (error: unknown) => error instanceof MigrationError && error.reason === 'not-an-object',
    );
    assert.throws(
      () => migrateSave([1, 2], { items: new Map() }),
      (error: unknown) => error instanceof MigrationError && error.reason === 'not-an-object',
    );
  });

  it('refuses a save with no private state', async () => {
    assert.throws(
      () => migrateSave({ maps: [] }, { items: new Map() }),
      (error: unknown) => error instanceof MigrationError && error.reason === 'malformed-save',
    );
  });

  it('refuses a save with no maps', async () => {
    assert.throws(
      () => migrateSave({ privateState: {} }, { items: new Map() }),
      (error: unknown) => error instanceof MigrationError && error.reason === 'malformed-save',
    );
  });

  it('refuses a nonsense version', async () => {
    assert.throws(
      () => migrateSave({ version: 'two', privateState: {}, maps: [] }, { items: new Map() }),
      (error: unknown) => error instanceof MigrationError && error.reason === 'malformed-save',
    );
  });
});
