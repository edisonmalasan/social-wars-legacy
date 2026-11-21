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
  MAX_TEAM_SIZE,
  QUEST_ID_02_CENTRAL_NUCLEAR,
  QUEST_ID_03_DEFEND_CONVOY_AUTO,
  QUEST_ID_11_SAVE_VILLAGES,
  QUEST_ID_19_HARDCORE5,
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
  type QuestActionHelper,
  type QuestStartHelper,
  type ShimWorld,
} from '@swl/server';
import { REQUEST_ID_HEADER } from '@swl/server';

import { createApp, type AppRequest } from './app.ts';

const Q02 = QUEST_ID_02_CENTRAL_NUCLEAR;
const Q03 = QUEST_ID_03_DEFEND_CONVOY_AUTO;
const Q11 = QUEST_ID_11_SAVE_VILLAGES;
const Q19 = QUEST_ID_19_HARDCORE5;

const ITEMS = new Map<number, ApplierItem>([
  [1017, { id: 1017, name: 'goodBoy', type: 'u', life: 1 } as ApplierItem],
  [89, { id: 89, name: 'centralNuclear', type: 'b', life: 1 } as ApplierItem],
  [195, { id: 195, name: 'commandCenter', type: 'b', life: 1 } as ApplierItem],
  [1035, { id: 1035, name: 'truck', type: 'u', life: 1 } as ApplierItem],
]);
const EVENTS: Readonly<Record<string, ContentQuestEvent>> = {
  [Q03]: { questId: Q03, kind: 'truckArrivals', refs: ['item:1013'], count: 3 },
  [Q11]: {
    questId: Q11,
    kind: 'civilianEvacuations',
    refs: ['item:20', 'item:21', 'item:22'],
    count: 3,
  },
};

function deps(over: Partial<ApplierDeps> = {}): ApplierDeps {
  return {
    now: () => 1000,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [60], multiplier: [1] },
    dailyBonus: { goldRewards: [0], heroItemId: 1 },
    items: ITEMS,
    questEvents: EVENTS,
    serverSeed: 'endpoint-test-seed',
    questExpRequired: 300,
    ...over,
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

/** A world where the server's own store really holds two unit types. */
function teamWorld(): ShimWorld {
  const world = freshWorld();
  (world.save.maps[0] as Record<string, unknown>)['store'] = { '1017': 4, '1035': 2 };
  return world;
}

function harness(
  over: {
    store?: MemoryPlayerStore;
    world?: ShimWorld;
    /** Counts helper calls, so a replayed id can be seen reaching the applier. */
    actions?: { value: number };
    starts?: { value: number };
    /** A mutable server clock, shared by the helpers and the command applier. */
    clock?: { value: number };
  } = {},
) {
  const sessions = new SessionStore();
  sessions.addPlayer('p1', 'pw');
  const identity = new LegacyIdentityBridge();
  const store =
    over.store ?? new MemoryPlayerStore([{ playerId: 'p1', world: over.world ?? freshWorld() }]);
  // One clock for the quest helpers, the command applier and the app itself,
  // so advancing it in a test moves every authoritative tick together.
  const now = () => over.clock?.value ?? 1000;
  const clockDeps = deps({ now });
  const helpers = createQuestHelpers(clockDeps);
  const issued = sessions.authenticate('p1', 'pw', 1000);
  if (!issued.ok) throw new Error('could not authenticate the test player');
  const beginQuest: QuestStartHelper = (world, questId, difficulty, army) => {
    if (over.starts) over.starts.value += 1;
    return helpers.beginQuest(world, questId, difficulty, army);
  };
  const applyQuestAction: QuestActionHelper = (world, questId, action) => {
    if (over.actions) over.actions.value += 1;
    return helpers.applyQuestAction(world, questId, action);
  };
  const handle = createApp({
    store,
    sessions,
    identity,
    content: costContentFrom({ items: [], offerPacks: [], globals: {}, expansionPrices: [] }),
    contentBundle: {},
    now,
    applyCommand: createApplier(clockDeps),
    beginQuest,
    applyQuestAction,
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

  it('does not start twice for concurrent identical request ids', async () => {
    const starts = { value: 0 };
    const { handle, store, token } = harness({ starts });
    const [first, second] = await Promise.all([
      handle(request('POST', '/api/quest/start', { questId: Q02 }, token, 'concurrent-start')),
      handle(request('POST', '/api/quest/start', { questId: Q02 }, token, 'concurrent-start')),
    ]);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    assert.equal(second.body, first.body);
    // Only the first request may reach the applier; the second is a replay.
    assert.equal(starts.value, 1);
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

  it('does not apply a concurrently replayed request id twice', async () => {
    const actions = { value: 0 };
    const { handle, store, token } = harness({ actions });
    await handle(request('POST', '/api/quest/start', { questId: Q03 }, token));
    const body = { questId: Q03, action: { type: 'truck-arrival', ref: 'item:1013' } };
    // Both requests are in flight together: neither can see the other's memo
    // entry yet, so the check-and-claim must be serialised per player.
    const [first, second] = await Promise.all([
      handle(request('POST', '/api/quest/action', body, token, 'concurrent-1')),
      handle(request('POST', '/api/quest/action', body, token, 'concurrent-1')),
    ]);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    assert.equal(second.body, first.body);
    // A replay must be answered from the memo, never applied a second time.
    assert.equal(actions.value, 1);
    const saved = (await store.get('p1'))!;
    const active = saved.world.save.privateState['activeQuest'] as {
      script: { counters: Record<string, number> };
    };
    assert.equal(active.script.counters['trucksArrived'], 1);
  });
});

describe('POST /api/quest/start with a team', () => {
  const team = [
    { unitId: 1017, count: 2 },
    { unitId: 1035, count: 1 },
  ];

  it('accepts an owned team, persists it bound to the quest and derives playerUnitsAlive', async () => {
    const { handle, store, token } = harness({ world: teamWorld() });
    const response = await handle(
      request('POST', '/api/quest/start', { questId: Q19, team }, token),
    );
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body) as {
      questId: string;
      started: boolean;
      team: typeof team;
    };
    assert.deepEqual(body, { questId: Q19, started: true, team });
    const saved = (await store.get('p1'))!;
    const active = saved.world.save.privateState['activeQuest'] as {
      questId: string;
      team: typeof team;
      playerUnitsAlive: number;
    };
    assert.equal(active.questId, Q19);
    assert.deepEqual(active.team, team);
    assert.equal(active.playerUnitsAlive, 3);
  });

  it('refuses a forged unit with a typed 400 and writes no active quest', async () => {
    const { handle, store, token } = harness({ world: teamWorld() });
    const response = await handle(
      request('POST', '/api/quest/start', {
        questId: Q19,
        team: [{ unitId: 9999, count: 1 }],
      }, token),
    );
    assert.equal(response.status, 400);
    assert.equal((JSON.parse(response.body) as { error: string }).error, 'quest-team-unit-unavailable');
    const saved = (await store.get('p1'))!;
    assert.equal(saved.world.save.privateState['activeQuest'], undefined);
  });

  it('refuses a unit beyond the server-owned quantity with a typed 400', async () => {
    const { handle, store, token } = harness({ world: teamWorld() });
    const response = await handle(
      request('POST', '/api/quest/start', {
        questId: Q19,
        team: [{ unitId: 1017, count: 5 }],
      }, token),
    );
    assert.equal(response.status, 400);
    assert.equal((JSON.parse(response.body) as { error: string }).error, 'quest-team-unit-unavailable');
    assert.equal((await store.get('p1'))!.world.save.privateState['activeQuest'], undefined);
  });

  it('refuses excessive, duplicate and malformed teams with a typed 400', async () => {
    for (const submitted of [
      [{ unitId: 1017, count: MAX_TEAM_SIZE + 1 }],
      [{ unitId: 1017, count: 1 }, { unitId: 1017, count: 2 }],
      'not-an-array',
      [{ unitId: 1017, count: -1 }],
    ]) {
      const { handle, store, token } = harness({ world: teamWorld() });
      const response = await handle(
        request('POST', '/api/quest/start', { questId: Q19, team: submitted }, token),
      );
      assert.equal(response.status, 400, JSON.stringify(submitted));
      assert.equal(
        (JSON.parse(response.body) as { error: string }).error,
        'quest-team-invalid',
      );
      assert.equal((await store.get('p1'))!.world.save.privateState['activeQuest'], undefined);
    }
  });

  it('refuses a team on a quest with no team selection', async () => {
    const { handle, store, token } = harness({ world: teamWorld() });
    const response = await handle(
      request('POST', '/api/quest/start', { questId: Q02, team }, token),
    );
    assert.equal(response.status, 400);
    assert.equal((JSON.parse(response.body) as { error: string }).error, 'quest-team-not-supported');
    assert.equal((await store.get('p1'))!.world.save.privateState['activeQuest'], undefined);
  });

  it('replays a team request id once, echoing the first accepted team', async () => {
    const starts = { value: 0 };
    const { handle, store, token } = harness({ world: teamWorld(), starts });
    const first = await handle(
      request('POST', '/api/quest/start', { questId: Q19, team }, token, 'team-start'),
    );
    const replay = await handle(
      request('POST', '/api/quest/start', {
        questId: Q19,
        team: [{ unitId: 1017, count: 1 }],
      }, token, 'team-start'),
    );
    assert.equal(first.status, 200);
    assert.equal(replay.status, 200);
    assert.equal(replay.body, first.body);
    // The replay never reaches the applier, so only one start was attempted.
    assert.equal(starts.value, 1);
    const active = (await store.get('p1'))!.world.save.privateState['activeQuest'] as {
      team: typeof team;
    };
    assert.deepEqual(active.team, team);
  });

  it('refuses a second start with a different team and keeps the first', async () => {
    const { handle, store, token } = harness({ world: teamWorld() });
    const first = await handle(
      request('POST', '/api/quest/start', { questId: Q19, team }, token),
    );
    const second = await handle(
      request('POST', '/api/quest/start', {
        questId: Q19,
        team: [{ unitId: 1017, count: 1 }],
      }, token),
    );
    assert.equal(first.status, 200);
    assert.equal(second.status, 409);
    assert.equal((JSON.parse(second.body) as { error: string }).error, 'quest-already-active');
    const active = (await store.get('p1'))!.world.save.privateState['activeQuest'] as {
      team: typeof team;
    };
    assert.deepEqual(active.team, team);
  });

  it('keeps the old behaviour when a client omits the team', async () => {
    const { handle, store, token } = harness();
    const response = await handle(request('POST', '/api/quest/start', { questId: Q02 }, token));
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.body), { questId: Q02, started: true });
    const active = (await store.get('p1'))!.world.save.privateState['activeQuest'] as {
      team?: unknown;
    };
    assert.equal(active.team, undefined);
  });
});

describe('Q11 timer enforcement over HTTP', () => {
  it('refuses a quest action after the server clock passes 240s with a typed 409', async () => {
    const clock = { value: 1000 };
    const { handle, store, token } = harness({ clock });
    const started = await handle(request('POST', '/api/quest/start', { questId: Q11 }, token));
    assert.equal(started.status, 200, started.body);

    clock.value = 1000 + 241;
    const savedBefore = structuredClone((await store.get('p1'))!.world);
    const response = await handle(
      request(
        'POST',
        '/api/quest/action',
        { questId: Q11, action: { type: 'civilian-evacuation', ref: 'item:20' } },
        token,
      ),
    );
    assert.equal(response.status, 409);
    assert.equal((JSON.parse(response.body) as { error: string }).error, 'quest-lost');
    // The refused action reached neither the ledger nor the wallet.
    assert.deepEqual((await store.get('p1'))!.world, savedBefore);
  });

  it('refuses end_quest after the timer expires and pays no reward', async () => {
    const clock = { value: 1000 };
    const { handle, token } = harness({ clock });
    const started = await handle(request('POST', '/api/quest/start', { questId: Q11 }, token));
    assert.equal(started.status, 200, started.body);
    // A genuine, fully earned win — still inside the window.
    for (const ref of ['item:20', 'item:21', 'item:22']) {
      const step = await handle(
        request(
          'POST',
          '/api/quest/action',
          { questId: Q11, action: { type: 'civilian-evacuation', ref } },
          token,
        ),
      );
      assert.equal(step.status, 200, `${ref}: ${step.body}`);
    }

    clock.value = 1000 + 241;
    const response = await handle(
      request(
        'POST',
        '/api/command',
        {
          v: 1,
          id: 'expired-end',
          token,
          commands: [{ map: 0, name: 'end_quest', args: [Q11, 1] }],
        },
        token,
      ),
    );
    assert.equal(response.status, 200, response.body);
    const body = JSON.parse(response.body) as {
      ok: boolean;
      outcomes: Array<{ ok: boolean; error?: { code: string; message: string } }>;
    };
    assert.equal(body.ok, false);
    assert.equal(body.outcomes.length, 1);
    assert.equal(body.outcomes[0]!.ok, false);
    assert.equal(body.outcomes[0]!.error?.code, 'command-failed');
    assert.equal(body.outcomes[0]!.error?.message, 'quest-lost');
  });
});
