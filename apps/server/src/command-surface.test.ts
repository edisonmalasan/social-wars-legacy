import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { PGlite } from '@electric-sql/pglite';

import {
  commandNames,
  getCommandSpec,
  type ArgSpec,
  type CommandSpec,
} from '@swl/protocol';
import { costContentFrom } from '@swl/rules';
import {
  LegacyIdentityBridge,
  PostgresPlayerStore,
  SessionStore,
  createApplier,
} from '@swl/server';

import { createApp, type AppOptions, type AppRequest } from './app.ts';
import { DEFAULT_LIMITS } from './limits.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

/**
 * A plausible argument for one argument of a command.
 *
 * The point is not to make the command *succeed* — most of them will be
 * refused, because the world does not have the building they name — but
 * to make the server **handle** them. A command that throws, or that
 * answers with a 500, is a bug; a command that answers with a typed
 * refusal is the server working.
 */
function argumentFor(arg: ArgSpec): unknown {
  if (arg.values && arg.values.length > 0) return arg.values[0];
  switch (arg.type) {
    case 'int':
    case 'uint':
    case 'number':
      return 0;
    case 'boolean':
      return false;
    case 'json':
      return {};
    case 'array':
      return [];
    default:
      return '';
  }
}

/** Every command in the table, with its own specification. */
function specs(): CommandSpec[] {
  return commandNames().map((name) => {
    const spec = getCommandSpec(name);
    if (!spec) throw new Error('the table has no spec for ' + name);
    return spec;
  });
}

/** The arguments a command takes, from its own specification. */
function argumentsFor(spec: CommandSpec): unknown[] {
  return spec.args.map(argumentFor);
}

describe('the whole command surface, against a real database', () => {
  it('answers every command with a typed result and never a 500', async () => {
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as Parameters<typeof costContentFrom>[0];
    const content = costContentFrom(bundle);

    // A real database, not a stub.
    const db = await PGlite.create();
    const store = new PostgresPlayerStore({ db });
    await store.init();

    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'correct horse');
    const identity = new LegacyIdentityBridge();

    // The player needs a save: a command against a player who has none is
    // refused before it reaches the applier.
    await db.query(
      'INSERT INTO player_saves (player_id, doc) VALUES ($1, $2)',
      [
        'p1',
        JSON.stringify({
          save: {
            playerInfo: { pid: 'p1', name: 'Player' },
            maps: [{ id: 0, items: {} }],
            privateState: {},
          },
          resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
          nextCommandNumber: 1,
        }),
      ],
    );

    const options: AppOptions = {
      store,
      sessions,
      identity,
      content,
      contentBundle: bundle,
      now: () => 1_700_000_000,
      nowMs: () => 1_700_000_000_000,
      applyCommand: createApplier({
        now: () => 1_700_000_000,
        tzOffsetHours: 0,
        collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
        dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
      }),
      limits: { ...DEFAULT_LIMITS, requestsPerWindow: 10_000 },
    };
    const handle = createApp(options);

    // A session, so the commands are not all refused for the token.
    const session = await handle({
      method: 'POST',
      path: '/api/session',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });
    assert.equal(session.status, 200);
    const token = (JSON.parse(session.body) as { token: string }).token;

    const failures: string[] = [];
    let applied = 0;
    let refused = 0;
    let unspecified = 0;

    for (const spec of specs()) {
      const response = await handle({
        method: 'POST',
        path: '/api/command',
        headers: { authorization: `Bearer ${token}` },
        body: JSON.stringify({
          v: 1,
          id: `request-${spec.name}`,
          token,
          commands: [{ map: 0, name: spec.name, args: argumentsFor(spec) }],
        }),
      });

      // Never a 500: a command the server cannot make sense of is a
      // typed refusal, not a crash.
      if (response.status >= 500) {
        failures.push(`${spec.name}: the server answered ${response.status}`);
        continue;
      }

      if (response.status === 400) {
        // The protocol refuses a command whose argument shape is not
        // known, rather than accepting it with guessed arguments.
        const body = JSON.parse(response.body) as {
          ok: boolean;
          errors?: { code?: string }[];
        };
        if (!body.errors?.length) {
          failures.push(`${spec.name}: the refusal says nothing`);
        }
        unspecified += 1;
        continue;
      }

      if (response.status !== 200) {
        failures.push(`${spec.name}: the server answered ${response.status}`);
        continue;
      }

      const body = JSON.parse(response.body) as {
        ok: boolean;
        outcomes: { ok: boolean; error?: { code?: string } }[];
      };
      if (!Array.isArray(body.outcomes) || body.outcomes.length !== 1) {
        failures.push(`${spec.name}: the answer has no outcome`);
        continue;
      }
      const outcome = body.outcomes[0]!;
      if (outcome.ok) {
        applied += 1;
      } else {
        refused += 1;
        // A refusal has to say why.
        if (!outcome.error?.code) {
          failures.push(`${spec.name}: the refusal says nothing`);
        }
      }
    }

    assert.deepEqual(
      failures,
      [],
      `the command surface:\n  ${failures.join('\n  ')}`,
    );
    assert.equal(applied + refused + unspecified, specs().length);
    // The test is only worth anything if the commands really were
    // exercised, so the surface is checked against the catalogue.
    assert.equal(specs().length, 94);
    // Most of the commands must have reached the applier: a surface
    // that is mostly "shape not known" would not be testing anything.
    assert.ok(
      applied + refused > specs().length / 2,
      `only ${applied + refused} of ${specs().length} commands reached the applier`,
    );

    await db.close();
  });

  it('leaves the player in a readable state after every command', async () => {
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as Parameters<typeof costContentFrom>[0];
    const content = costContentFrom(bundle);

    const db = await PGlite.create();
    const store = new PostgresPlayerStore({ db });
    await store.init();

    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'correct horse');
    const identity = new LegacyIdentityBridge();

    // The player needs a save: a command against a player who has none is
    // refused before it reaches the applier.
    await db.query(
      'INSERT INTO player_saves (player_id, doc) VALUES ($1, $2)',
      [
        'p1',
        JSON.stringify({
          save: {
            playerInfo: { pid: 'p1', name: 'Player' },
            maps: [{ id: 0, items: {} }],
            privateState: {},
          },
          resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
          nextCommandNumber: 1,
        }),
      ],
    );

    const handle = createApp({
      store,
      sessions,
      identity,
      content,
      contentBundle: bundle,
      now: () => 1_700_000_000,
      nowMs: () => 1_700_000_000_000,
      applyCommand: createApplier({
        now: () => 1_700_000_000,
        tzOffsetHours: 0,
        collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
        dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
      }),
      limits: { ...DEFAULT_LIMITS, requestsPerWindow: 10_000 },
    });

    const session = await handle({
      method: 'POST',
      path: '/api/session',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });
    const token = (JSON.parse(session.body) as { token: string }).token;

    for (const spec of specs()) {
      await handle({
        method: 'POST',
        path: '/api/command',
        headers: { authorization: `Bearer ${token}` },
        body: JSON.stringify({
          v: 1,
          id: `request-${spec.name}`,
          token,
          commands: [{ map: 0, name: spec.name, args: argumentsFor(spec) }],
        }),
      });

      // The save is still readable, and it is still the player's.
      const saved = await store.get('p1');
      assert.ok(saved, 'the player vanished');
      assert.equal(saved!.playerId, 'p1');
      assert.ok(saved!.world.save, 'the save has no document');
    }

    await db.close();
  });
});
