import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { costContentFrom } from '@swl/rules';

import { framePayload, SERVER_KEYS } from '@swl/protocol/commandphp';
import { COUNTERS } from '@swl/rules';

import { LegacyIdentityBridge, SessionStore } from './session.ts';
import {
  applyBatch,
  handleCommandPhp,
  handleGetGameConfig,
  handleGetPlayerInfo,
  type ShimContext,
  type ShimWorld,
} from './shim.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function costContent() {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as Parameters<typeof costContentFrom>[0];
  return costContentFrom(bundle);
}

function world(over: Partial<ShimWorld> = {}): ShimWorld {
  return {
    save: { playerInfo: {}, maps: [{}], privateState: {} },
    resources: { g: 1000, w: 1000, o: 1000, s: 1000, c: 1000, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
    ...over,
  };
}

/** The legacy `USERID` the shim's bridge is bound to, and the player it means. */
const LEGACY_USER_ID = 'e53386db-e42c-43c4-8c5c-9ace9c81ad91';
const PLAYER_ID = 'player-1';

async function context(over: Partial<ShimContext> = {}): Promise<ShimContext> {
  const applied: string[] = [];
  const identity = new LegacyIdentityBridge();
  identity.allowLegacyIdentity();
  identity.bind(LEGACY_USER_ID, PLAYER_ID);
  const base: ShimContext = {
    world: world(),
    content: await costContent(),
    now: 1_700_000_000,
    identity,
    applyCommand: (w, command) => {
      applied.push(command.name);
      return { applied: true, world: w };
    },
    ...over,
  };
  return base;
}

/** An authenticated request. */
const authed = (fields: Record<string, string | undefined> = {}) => ({
  path: '/command.php',
  fields: { USERID: LEGACY_USER_ID, ...fields },
});

describe('sessions', () => {
  it('issues a token for a correct credential', () => {
    const store = new SessionStore();
    store.addPlayer('p1', 'correct horse');
    const result = store.authenticate('p1', 'correct horse', 1000);
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.ok(result.session.token.length > 32);
      assert.equal(result.session.playerId, 'p1');
    }
  });

  it('refuses a wrong password', () => {
    const store = new SessionStore();
    store.addPlayer('p1', 'correct horse');
    const result = store.authenticate('p1', 'wrong', 1000);
    assert.equal(result.ok, false);
    if (!result.ok) assert.equal(result.reason, 'bad-credential');
  });

  it('refuses an unknown player', () => {
    const store = new SessionStore();
    const result = store.authenticate('nobody', 'x', 1000);
    assert.equal(result.ok, false);
    if (!result.ok) assert.equal(result.reason, 'unknown-player');
  });

  it('resolves a live token and refuses an expired one', () => {
    const store = new SessionStore();
    store.addPlayer('p1', 'pw');
    const issued = store.authenticate('p1', 'pw', 1000);
    assert.equal(issued.ok, true);
    if (!issued.ok) return;
    assert.ok(store.resolve(issued.session.token, 1001));
    assert.equal(store.resolve(issued.session.token, 99_999_999), null);
  });

  it('revokes a token immediately', () => {
    const store = new SessionStore();
    store.addPlayer('p1', 'pw');
    const issued = store.authenticate('p1', 'pw', 1000);
    assert.equal(issued.ok, true);
    if (!issued.ok) return;
    assert.ok(store.resolve(issued.session.token, 1001));
    assert.equal(store.revoke(issued.session.token), true);
    assert.equal(store.resolve(issued.session.token, 1001), null);
  });

  it('revokes every session of a player', () => {
    const store = new SessionStore();
    store.addPlayer('p1', 'pw');
    store.authenticate('p1', 'pw', 1000);
    store.authenticate('p1', 'pw', 1001);
    assert.equal(store.size, 2);
    assert.equal(store.revokeAllFor('p1'), 2);
    assert.equal(store.size, 0);
  });
});

describe('the legacy identity bridge', () => {
  it('is off by default', () => {
    const bridge = new LegacyIdentityBridge();
    bridge.bind('legacy-1', 'p1');
    assert.equal(bridge.resolve('legacy-1'), null);
  });

  it('resolves a bound value once it is enabled', () => {
    const bridge = new LegacyIdentityBridge();
    bridge.bind('legacy-1', 'p1');
    bridge.allowLegacyIdentity();
    assert.equal(bridge.resolve('legacy-1'), 'p1');
  });

  it('cannot invent a player', () => {
    const bridge = new LegacyIdentityBridge();
    bridge.allowLegacyIdentity();
    assert.equal(bridge.resolve('never-bound'), null);
  });
});

describe('the command.php shim', () => {
  it('rejects a body that is not framed', async () => {
    const ctx = await context();
    const response = handleCommandPhp(authed({ data: '{"commands":[]}' }), ctx);
    assert.equal(response.status, 400);
    assert.match(response.body, /malformed-framing/);
  });

  it('rejects a body signed with the wrong key', async () => {
    const ctx = await context();
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const frame = framePayload(payload, 'not-a-real-key');
    const response = handleCommandPhp(authed({ data: frame }), ctx);
    assert.equal(response.status, 403);
    assert.match(response.body, /bad-signature/);
  });

  it('accepts a body signed with either key', async () => {
    for (const key of [SERVER_KEYS.current, SERVER_KEYS.legacy]) {
      const ctx = await context();
      const payload = JSON.stringify({ first_number: 1, commands: [] });
      const response = handleCommandPhp(
        authed({ data: framePayload(payload, key) }),
        ctx,
      );
      assert.equal(response.status, 200);
    }
  });

  it('answers with the shape the client expects', async () => {
    const ctx = await context();
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const response = handleCommandPhp(
      authed({ data: framePayload(payload, SERVER_KEYS.current) }),
      ctx,
    );
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.body), { result: 'success' });
  });

  it('does not apply a replayed batch twice', async () => {
    const applied: string[] = [];
    const ctx = await context({
      applyCommand: (w, command) => {
        applied.push(command.name);
        return { applied: true, world: w };
      },
    });
    const payload = {
      first_number: 1,
      commands: [[1, 'move', [1, 2, 3], [0, 0, 0, 0, 0, 0, 0, 0]]],
    };
    const first = applyBatch(payload, ctx);
    assert.equal(applied.length, 1);
    assert.equal(first.replay, false);

    // The client re-sends the SAME packet when it gets no answer.
    const second = applyBatch(payload, { ...ctx, world: first.world });
    assert.equal(applied.length, 1, 'the replay applied the command again');
    assert.equal(second.replay, true);
  });

  it('tolerates a gap in the command index', async () => {
    const ctx = await context();
    const payload = {
      first_number: 50,
      commands: [[1, 'move', [1, 2, 3], [0, 0, 0, 0, 0, 0, 0, 0]]],
    };
    const outcome = applyBatch(payload, ctx);
    assert.equal(outcome.gap, true);
    assert.equal(outcome.world.nextCommandNumber, 51);
  });

  it('refuses flash_debug outright', async () => {
    const ctx = await context();
    const payload = {
      first_number: 1,
      commands: [[1, 'flash_debug', [1, 2, 3], [0, 0, 999999, 0, 0, 0, 0, 0]]],
    };
    const outcome = applyBatch(payload, ctx);
    assert.equal(outcome.refused.length, 1);
    assert.equal(outcome.refused[0]!.name, 'flash_debug');
    // The wallet is untouched.
    assert.equal(outcome.world.resources['g'], 1000);
  });

  it('computes the cost itself and ignores the declared delta', async () => {
    const ctx = await context();
    // A buy of a Soldier costs 30 gold and 60 steel. The client claims it
    // cost nothing.
    const payload = {
      first_number: 1,
      commands: [[1, 'buy', [1, 1007, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]]],
    };
    const outcome = applyBatch(payload, ctx);
    assert.equal(outcome.refused.length, 0);
    assert.equal(outcome.world.resources['g'], 1000 - 30);
    assert.equal(outcome.world.resources['s'], 1000 - 60);
  });

  it('refuses a purchase the player cannot afford', async () => {
    const ctx = await context({ world: world({ resources: { g: 1, s: 1 } }) });
    const payload = {
      first_number: 1,
      commands: [[1, 'buy', [1, 1007, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]]],
    };
    const outcome = applyBatch(payload, ctx);
    assert.equal(outcome.refused.length, 1);
    assert.equal(outcome.refused[0]!.reason, 'insufficient-resources');
  });

  it('carries the four counters into the cost', async () => {
    // The Antiaircraft battery is 20x against ft_flying.
    assert.equal(COUNTERS.length, 4);
    const antiaircraft = COUNTERS.find((c) => c.name === 'Antiaircraft battery');
    assert.equal(antiaircraft?.multiplier, 20);
    assert.equal(antiaircraft?.bestAgainst, 'ft_flying');
  });
});

describe('the shim identity', () => {
  it('refuses a request with no identity at all', async () => {
    const ctx = await context();
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const response = handleCommandPhp(
      { path: '/command.php', fields: { data: framePayload(payload, SERVER_KEYS.current) } },
      ctx,
    );
    assert.equal(response.status, 401);
    assert.match(response.body, /unauthenticated/);
  });

  it('refuses a request whose legacy USERID is not bound', async () => {
    const ctx = await context();
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const response = handleCommandPhp(
      {
        path: '/command.php',
        fields: {
          USERID: 'someone-elses-id',
          data: framePayload(payload, SERVER_KEYS.current),
        },
      },
      ctx,
    );
    assert.equal(response.status, 401);
  });

  it('refuses a request whose legacy bridge is off', async () => {
    const identity = new LegacyIdentityBridge();
    identity.bind(LEGACY_USER_ID, PLAYER_ID);
    // The bridge is NOT enabled.
    const ctx = await context({ identity });
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const response = handleCommandPhp(authed({ data: framePayload(payload, SERVER_KEYS.current) }), ctx);
    assert.equal(response.status, 401);
  });

  it('accepts a request carrying a valid session token', async () => {
    const ctx = await context({ resolveToken: (token) => (token === 'good' ? PLAYER_ID : null) });
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const response = handleCommandPhp(
      {
        path: '/command.php',
        fields: { token: 'good', data: framePayload(payload, SERVER_KEYS.current) },
      },
      ctx,
    );
    assert.equal(response.status, 200);
  });

  it('refuses a request carrying an invalid session token', async () => {
    const ctx = await context({ resolveToken: (token) => (token === 'good' ? PLAYER_ID : null) });
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const response = handleCommandPhp(
      {
        path: '/command.php',
        fields: { token: 'bad', data: framePayload(payload, SERVER_KEYS.current) },
      },
      ctx,
    );
    assert.equal(response.status, 401);
    assert.match(response.body, /invalid-session/);
  });

  it('uses the identity to choose which save is touched', async () => {
    const victim = world({ resources: { g: 5 } });
    const attacker = world({ resources: { g: 9999 } });
    const ctx = await context({
      worldFor: (playerId) => (playerId === 'player-victim' ? victim : attacker),
    });
    const payload = JSON.stringify({
      first_number: 1,
      commands: [[1, 'buy', [1, 1007, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]]],
    });
    // The attacker claims to be the victim.
    const identity = new LegacyIdentityBridge();
    identity.allowLegacyIdentity();
    identity.bind('attacker-id', 'player-attacker');
    identity.bind('victim-id', 'player-victim');
    ctx.identity = identity;

    handleCommandPhp(
      {
        path: '/command.php',
        fields: {
          USERID: 'victim-id',
          data: framePayload(payload, SERVER_KEYS.current),
        },
      },
      ctx,
    );
    // The victim's save was touched, and it could not afford the Soldier.
    assert.equal(victim.resources['g'], 5);
    assert.equal(attacker.resources['g'], 9999);
  });
});

describe('get_game_config.php', () => {
  const GAMES = [
    { id: 1, start_date: '2012-03-02 23:00:00', extra_item: 1152, items: [1, 2, 3, 4, 5, 6] },
    { id: 2, start_date: '2012-03-09 23:00:00', extra_item: 1150, items: [1, 2, 3, 4, 5, 6] },
  ];

  it('serves the darts schedule rotated to the current week', () => {
    // The upstream rotates the schedule on every boot, because the
    // client's board is built from it: a player who loads the config on a
    // different day must not see a different board.
    const before = handleGetGameConfig(
      { path: '/get_game_config.php', fields: {} },
      { content: { dartsItems: GAMES }, now: Date.UTC(2026, 9, 20) / 1000 },
    );
    const body = JSON.parse(before.body);
    assert.ok(Array.isArray(body.dartsItems));
    assert.equal(body.dartsItems.length, 2);
    // The dates are NOT the 2012 ones any more.
    assert.ok(
      !body.dartsItems[0].start_date.startsWith('2012-03-02'),
      `the schedule was not rotated: ${body.dartsItems[0].start_date}`,
    );
    // The second game is still a week after the first.
    assert.notEqual(body.dartsItems[0].start_date, body.dartsItems[1].start_date);
    // And the prizes are untouched.
    assert.deepEqual(body.dartsItems[0].items, [1, 2, 3, 4, 5, 6]);
  });

  it('serves the same schedule within one week', () => {
    const monday = Date.UTC(2026, 9, 19) / 1000;
    const first = handleGetGameConfig(
      { path: '/get_game_config.php', fields: {} },
      { content: { dartsItems: GAMES }, now: monday },
    );
    const later = handleGetGameConfig(
      { path: '/get_game_config.php', fields: {} },
      { content: { dartsItems: GAMES }, now: monday + 3 * 86400 },
    );
    assert.deepEqual(
      JSON.parse(first.body).dartsItems,
      JSON.parse(later.body).dartsItems,
    );
  });

  it('leaves the content alone when there are no darts', () => {
    const response = handleGetGameConfig(
      { path: '/get_game_config.php', fields: {} },
      { content: { items: [] }, now: 1_700_000_000 },
    );
    assert.deepEqual(JSON.parse(response.body), { items: [] });
  });
});

describe('get_player_info.php', () => {
  const own = {
    playerInfo: { name: 'me' },
    map: { id: 1 },
    privateState: { energy: 30 },
    neighbors: [{ id: 2 }],
  };
  const neighbours = {
    '100000030': {
      playerInfo: { name: 'mike' },
      maps: [{ id: 9 }],
      privateState: {},
    },
  };

  it('answers with the player own info when no user is given', async () => {
    const response = handleGetPlayerInfo(
      { path: '/get_player_info.php', fields: {} },
      { own, neighbours, now: 1000 },
    );
    const body = JSON.parse(response.body);
    assert.equal(body.result, 'ok');
    assert.deepEqual(body.playerInfo, { name: 'me' });
    assert.deepEqual(body.neighbors, [{ id: 2 }]);
  });

  it('answers with a neighbour for a quest or general mike', async () => {
    const response = handleGetPlayerInfo(
      { path: '/get_player_info.php', fields: { user: '100000030' } },
      { own, neighbours, now: 1000 },
    );
    const body = JSON.parse(response.body);
    assert.deepEqual(body.playerInfo, { name: 'mike' });
    assert.deepEqual(body.map, { id: 9 });
  });

  it('answers with an empty body for an unknown neighbour', async () => {
    const response = handleGetPlayerInfo(
      { path: '/get_player_info.php', fields: { user: 'nobody' } },
      { own, neighbours, now: 1000 },
    );
    assert.equal(response.body, '');
  });
});
