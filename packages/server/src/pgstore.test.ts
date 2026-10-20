import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { PGlite } from '@electric-sql/pglite';

import { PostgresPlayerStore } from './pgstore.ts';
import { GOAL_STATE_KEY, QUEST_PROGRESS_KEY } from './apply.ts';
import { cloneWorld, type PlayerSave } from './store.ts';
import type { ShimWorld } from './shim.ts';

/** A world with something in it. */
function world(over: Partial<ShimWorld> = {}): ShimWorld {
  return {
    save: {
      playerInfo: { name: 'me' },
      maps: [{ id: 0, items: {} }],
      privateState: { energy: 30 },
    },
    resources: { g: 1000, w: 500, o: 0, s: 0, c: 10, e: 50, x: 0, m: 0 },
    nextCommandNumber: 1,
    ...over,
  };
}

/** A store on a fresh in-memory database. */
async function store(): Promise<PostgresPlayerStore> {
  const db = await PGlite.create();
  const created = new PostgresPlayerStore({ db, table: 'saves' });
  await created.init();
  return created;
}

describe('the PostgreSQL store', () => {
  it('starts empty', async () => {
    const saves = await store();
    assert.equal(saves.size, 0);
    assert.equal(await saves.get('nobody'), null);
    assert.equal(await saves.has('nobody'), false);
  });

  it('stores a player', async () => {
    const saves = await store();
    await saves.add('p1', world());
    assert.equal(await saves.has('p1'), true);
    const save = await saves.get('p1');
    assert.ok(save);
    assert.equal(save.playerId, 'p1');
    assert.equal(save.world.resources['g'], 1000);
    assert.equal(save.world.save.privateState['energy'], 30);
  });

  it('applies a transaction', async () => {
    const saves = await store();
    await saves.add('p1', world());
    const saved = await saves.transact('p1', (current) => ({
      ...current,
      resources: { ...current.resources, g: 10 },
    }));
    assert.ok(saved);
    assert.equal(saved.world.resources['g'], 10);
    assert.equal((await saves.get('p1'))!.world.resources['g'], 10);
  });

  it('returns null for a player that does not exist', async () => {
    const saves = await store();
    const saved = await saves.transact('nobody', (current) => current);
    assert.equal(saved, null);
  });

  it('leaves the save untouched when a transaction throws', async () => {
    const saves = await store();
    await saves.add('p1', world());
    await assert.rejects(
      saves.transact('p1', (current) => {
        current.resources['g'] = 0;
        throw new Error('boom');
      }),
    );
    // The rollback put the row back exactly as it was.
    assert.equal((await saves.get('p1'))!.world.resources['g'], 1000);
  });

  it('serialises two transactions on the same player', async () => {
    const saves = await store();
    await saves.add('p1', world());

    // Two changes that each read the current value and add to it. Without
    // the row lock they would interleave and one would be lost.
    const read = async (): Promise<number> =>
      (await saves.get('p1'))!.world.resources['g'] ?? 0;
    const first = saves.transact('p1', async (current) => {
      const value = current.resources['g'] ?? 0;
      await new Promise((resolve) => setTimeout(resolve, 20));
      return { ...current, resources: { ...current.resources, g: value + 1 } };
    });
    const second = saves.transact('p1', async (current) => {
      const value = current.resources['g'] ?? 0;
      await new Promise((resolve) => setTimeout(resolve, 20));
      return { ...current, resources: { ...current.resources, g: value + 1 } };
    });
    await Promise.all([first, second]);

    // Both changes landed: 1000 + 1 + 1.
    assert.equal(await read(), 1002);
  });

  it('keeps the players apart', async () => {
    const saves = await store();
    await saves.add('p1', world());
    await saves.add('p2', world({ resources: { g: 50, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 } }));
    await saves.transact('p1', (current) => ({
      ...current,
      resources: { ...current.resources, g: 7 },
    }));
    assert.equal((await saves.get('p1'))!.world.resources['g'], 7);
    assert.equal((await saves.get('p2'))!.world.resources['g'], 50);
  });

  it('overwrites a player that is added twice', async () => {
    const saves = await store();
    await saves.add('p1', world());
    await saves.add('p1', world({ resources: { g: 3, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 } }));
    assert.equal((await saves.get('p1'))!.world.resources['g'], 3);
  });

  it('survives the world being a document with any shape', async () => {
    const saves = await store();
    const odd = world();
    odd.save.privateState['somethingOdd'] = { nested: [1, 2, { deep: true }] };
    await saves.add('p1', odd);
    const save = await saves.get('p1');
    assert.deepEqual(
      (save!.world.save.privateState['somethingOdd'] as unknown),
      { nested: [1, 2, { deep: true }] },
    );
  });
});

describe('the store migration', () => {
  /** The content items the migration needs. */
  const items = new Map([
    [
      30,
      {
        id: 30,
        name: 'Academy I',
        costs: { w: 125 },
        collect: 0,
        collect_type: 'w',
        unit_capacity: 0,
      },
    ],
  ]);

  /** A store that migrates. */
  async function migrating(): Promise<PostgresPlayerStore> {
    const db = await PGlite.create();
    const created = new PostgresPlayerStore({ db, table: 'saves', items });
    await created.init();
    return created;
  }

  it('migrates an upstream save, which has no version', async () => {
    const saves = await migrating();
    // An upstream save: no version, and none of the server's additions.
    const upstream = {
      playerInfo: { name: 'Warrior' },
      maps: [{ id: 0, items: {} }],
      privateState: { energy: 50 },
    };
    // An upstream save is imported verbatim, and migrated when it is read.
    await saves.addRaw('p1', upstream);

    const save = await saves.get('p1');
    assert.ok(save);
    // The migrated document has the server's additions.
    assert.ok(
      GOAL_STATE_KEY in save.world.save.privateState,
      'the goal state was not added',
    );
    assert.ok(
      QUEST_PROGRESS_KEY in save.world.save.privateState,
      'the quest progress was not added',
    );
  });

  it('refuses a save from a version it does not understand', async () => {
    const saves = await migrating();
    await saves.addRaw('p1', {
      version: 99,
      playerInfo: {},
      maps: [],
      privateState: {},
    });
    // A save from the future is refused, not guessed at.
    assert.equal(await saves.get('p1'), null);
  });

  it('leaves a current save alone', async () => {
    const saves = await migrating();
    await saves.add('p1', world());
    const save = await saves.get('p1');
    assert.ok(save);
    assert.equal(save.world.resources['g'], 1000);
    assert.equal(save.world.save.privateState['energy'], 30);
  });
});

describe('the world clone', () => {
  it('does not share the resources', () => {
    const original = world();
    const copy = cloneWorld(original);
    copy.resources['g'] = 0;
    assert.equal(original.resources['g'], 1000);
  });
});
