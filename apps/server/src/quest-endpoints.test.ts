/**
 * Task 2 — the native quest endpoints.
 *
 * Both endpoints are authenticated, typed on refusal, idempotent by request
 * id, and persist through the real store. The applier helpers are the same
 * bound helpers the production server wires in.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  costContentFrom,
  QUEST_ID_02_CENTRAL_NUCLEAR,
  QUEST_ID_03_DEFEND_CONVOY_AUTO,
} from '@swl/rules';
import {
  createApplier,
  createQuestHelpers,
  LegacyIdentityBridge,
  MemoryPlayerStore,
  SessionStore,
  type ApplierDeps,
  type ApplierItem,
  type ContentQuestEvent,
  type ShimWorld,
} from '@swl/server';
import { REQUEST_ID_HEADER } from '@swl/server';

import { createApp, type AppRequest } from './app.ts';

const Q02 = QUEST_ID_02_CENTRAL_NUCLEAR;
const Q03 = QUEST_ID_03_DEFEND_CONVOY_AUTO;

const ITEMS = new Map<number, ApplierItem>([
  [1017, { id: 1017, name: 'goodBoy', type: 'u', life: 1 } as ApplierItem],
  [89, { id: 89, name: 'centralNuclear', type: 'b', life: 1 } as ApplierItem],
  [195, { id: 195, name: 'commandCenter', type: 'b', life: 1 } as ApplierItem],
  [1035, { id: 1035, name: 'truck', type: 'u', life: 1 } as ApplierItem],
]);
const EVENTS: Readonly<Record<string, ContentQuestEvent>> = {
  [Q03]: { questId: Q03, kind: 'truckArrivals', refs: ['item:1013'], count: 3 },
};

function deps(): ApplierDeps {
  return {
    now: () => 1000,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [60], multiplier: [1] },
    dailyBonus: { goldRewards: [0], heroItemId: 1 },
    items: ITEMS,
    questEvents: EVENTS,
    serverSeed: 'endpoint-test-seed',
    questExpRequired: 300,
  };
}

function freshWorld(): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, currentQuestVars: {}, idCurrentMission: 1 }],
      privateState: {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

function harness(over: { store?: MemoryPlayerStore } = {}) {
  const sessions = new SessionStore();
  sessions.addPlayer('p1', 'pw');
  const identity = new LegacyIdentityBridge();
  const store = over.store ?? new MemoryPlayerStore([{ playerId: 'p1', world: freshWorld() }]);
  const helpers = createQuestHelpers(deps());
  const issued = sessions.authenticate('p1', 'pw', 1000);
  if (!issued.ok) throw new Error('could not authenticate the test player');
  const handle = createApp({
    store,
    sessions,
    identity,
    content: costContentFrom({ items: [], offerPacks: [], globals: {}, expansionPrices: [] }),
    contentBundle: {},
    now: () => 1000,
    applyCommand: createApplier(deps()),
    beginQuest: helpers.beginQuest,
    applyQuestAction: helpers.applyQuestAction,
  });
  return { handle, store, token: issued.session.token };
}

function request(
  method: string,
  path: string,
  body: unknown,
  token?: string,
  requestId?: string,
): AppRequest {
  const headers: Record<string, string | undefined> = { 'content-type': 'application/json' };
  if (token) headers['authorization'] = `Bearer ${token}`;
  if (requestId) headers[REQUEST_ID_HEADER] = requestId;
  return { method, path, headers, body: JSON.stringify(body) };
}

describe('POST /api/quest/start', () => {
  it('requires authentication', async () => {
    const { handle } = harness();
    const response = await handle(request('POST', '/api/quest/start', { questId: Q02 }));
    assert.equal(response.status, 401);
  });

  it('starts a quest and persists the active state through the store', async () => {
    const { handle, store, token } = harness();
    const response = await handle(request('POST', '/api/quest/start', { questId: Q02 }, token));
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body) as { questId: string; started: boolean };
    assert.deepEqual(body, { questId: Q02, started: true });
    const saved = (await store.get('p1'))!;
    const active = saved.world.save.privateState['activeQuest'] as { questId: string };
    assert.equal(active.questId, Q02);
  });

  it('returns a typed 400 for an unknown quest', async () => {
    const { handle, token } = harness();
    const response = await handle(
      request('POST', '/api/quest/start', { questId: '999999999' }, token),
    );
    assert.equal(response.status, 400);
    const body = JSON.parse(response.body) as { error: string };
    assert.equal(body.error, 'quest-unknown');
  });

  it('returns a typed 409 for a second start', async () => {
    const { handle, token } = harness();
    const first = await handle(request('POST', '/api/quest/start', { questId: Q02 }, token));
    assert.equal(first.status, 200);
    const second = await handle(request('POST', '/api/quest/start', { questId: Q03 }, token));
    assert.equal(second.status, 409);
    assert.equal((JSON.parse(second.body) as { error: string }).error, 'quest-already-active');
  });

  it('returns a typed 400 for malformed JSON', async () => {
    const { handle, token } = harness();
    const response = await handle({
      method: 'POST',
      path: '/api/quest/start',
      headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
      body: '{',
    });
    assert.equal(response.status, 400);
    assert.equal((JSON.parse(response.body) as { error: string }).error, 'malformed-json');
  });

  it('replays a request id without starting twice', async () => {
    const { handle, store, token } = harness();
    const first = await handle(
      request('POST', '/api/quest/start', { questId: Q02 }, token, 'req-1'),
    );
    const replay = await handle(
      request('POST', '/api/quest/start', { questId: Q03 }, token, 'req-1'),
    );
    assert.equal(first.status, 200);
    assert.equal(replay.status, 200);
    assert.equal(replay.body, first.body);
    const saved = (await store.get('p1'))!;
    const active = saved.world.save.privateState['activeQuest'] as { questId: string };
    assert.equal(active.questId, Q02);
  });
});

describe('POST /api/quest/action', () => {
  it('requires authentication', async () => {
    const { handle } = harness();
    const response = await handle(
      request('POST', '/api/quest/action', { questId: Q02, action: { type: 'strike', ref: 'x' } }),
    );
    assert.equal(response.status, 401);
  });

  it('applies a server-owned event and persists the counter', async () => {
    const { handle, store, token } = harness();
    const started = await handle(request('POST', '/api/quest/start', { questId: Q03 }, token));
    assert.equal(started.status, 200);
    const response = await handle(
      request(
        'POST',
        '/api/quest/action',
        { questId: Q03, action: { type: 'truck-arrival', ref: 'item:1013' } },
        token,
      ),
    );
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body) as { counters: Record<string, number> };
    assert.equal(body.counters['trucksArrived'], 1);
    const saved = (await store.get('p1'))!;
    const active = saved.world.save.privateState['activeQuest'] as {
      script: { counters: Record<string, number> };
    };
    assert.equal(active.script.counters['trucksArrived'], 1);
  });

  it('returns typed 409s for a wrong quest and a refused action', async () => {
    const { handle, token } = harness();
    await handle(request('POST', '/api/quest/start', { questId: Q03 }, token));
    const wrong = await handle(
      request(
        'POST',
        '/api/quest/action',
        { questId: Q02, action: { type: 'truck-arrival', ref: 'item:1013' } },
        token,
      ),
    );
    assert.equal(wrong.status, 409);
    assert.equal((JSON.parse(wrong.body) as { error: string }).error, 'quest-not-active');

    const refused = await handle(
      request(
        'POST',
        '/api/quest/action',
        { questId: Q03, action: { type: 'truck-arrival', ref: 'item:999' } },
        token,
      ),
    );
    assert.equal(refused.status, 409);
    assert.equal((JSON.parse(refused.body) as { error: string }).error, 'quest-refused');
  });

  it('replays a request id without applying the action twice', async () => {
    const { handle, store, token } = harness();
    await handle(request('POST', '/api/quest/start', { questId: Q03 }, token));
    const body = { questId: Q03, action: { type: 'truck-arrival', ref: 'item:1013' } };
    const first = await handle(request('POST', '/api/quest/action', body, token, 'act-1'));
    const replay = await handle(request('POST', '/api/quest/action', body, token, 'act-1'));
    assert.equal(first.status, 200);
    assert.equal(replay.status, 200);
    assert.equal(replay.body, first.body);
    const saved = (await store.get('p1'))!;
    const active = saved.world.save.privateState['activeQuest'] as {
      script: { counters: Record<string, number> };
    };
    assert.equal(active.script.counters['trucksArrived'], 1);
  });
});
