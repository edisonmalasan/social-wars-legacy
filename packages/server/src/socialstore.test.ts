import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { PGlite } from '@electric-sql/pglite';

import { SocialStore } from './socialstore.ts';
import { AllianceService, type AllianceUser } from './alliance.ts';

const alice: AllianceUser = { id: 'alice', name: 'Alice', country: 'uk' };

/** An alliance, for the round trip. */
const ALLIANCE = {
  id: '1',
  title: 'The Brigade',
  description: 'We are the best',
  ownerId: 'alice',
  country: 'uk',
  members: [{ id: 'alice', name: 'Alice' }],
  joinRequests: [],
  dateCreated: 1_700_000_000,
};

describe('the social store', () => {
  it('starts empty', async () => {
    const db = await PGlite.create();
    const store = new SocialStore({ db });
    await store.init();
    assert.deepEqual(await store.loadAlliances(), []);
    assert.deepEqual(await store.loadMarketplace(), {});
    await db.close();
  });

  it('round-trips the alliances', async () => {
    const db = await PGlite.create();
    const store = new SocialStore({ db });
    await store.init();
    await store.saveAlliances([ALLIANCE]);
    const loaded = await store.loadAlliances();
    assert.equal(loaded.length, 1);
    assert.equal(loaded[0]!.title, 'The Brigade');
    assert.equal(loaded[0]!.members.length, 1);
    await db.close();
  });

  it('round-trips the marketplace state', async () => {
    const db = await PGlite.create();
    const store = new SocialStore({ db });
    await store.init();
    await store.saveMarketplace({
      'uuid-1': { uuid: 'uuid-1', idUnit: 1007, level: 3, beginDate: 1, endDate: 2, currentPrice: 100 },
    });
    const loaded = await store.loadMarketplace();
    assert.equal(Object.keys(loaded).length, 1);
    assert.equal((loaded['uuid-1'] as { level: number }).level, 3);
    await db.close();
  });

  it('overwrites rather than accumulating', async () => {
    const db = await PGlite.create();
    const store = new SocialStore({ db });
    await store.init();
    await store.saveAlliances([ALLIANCE]);
    await store.saveAlliances([]);
    assert.deepEqual(await store.loadAlliances(), []);
    assert.equal(await store.count(), 1);
    await db.close();
  });

  it('restores a service from the stored state', async () => {
    const db = await PGlite.create();
    const store = new SocialStore({ db });
    await store.init();

    // A service writes its state, the state is stored, and a NEW service is
    // built from what was stored.
    const first = new AllianceService([], [alice]);
    first.create({ user: alice, title: 'The Brigade' }, 1_700_000_000);
    await store.saveAlliances(first.all());

    const second = new AllianceService(await store.loadAlliances(), [alice]);
    const listed = second.list({ user: alice });
    assert.equal(listed.success, true);
    assert.equal(listed.alliances?.length, 1);
    assert.equal(listed.alliances?.[0]?.title, 'The Brigade');
    await db.close();
  });
});
