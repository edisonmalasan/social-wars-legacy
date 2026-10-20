import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { framePayload, SERVER_KEYS } from '@swl/protocol';

import {
  BUY_WORKER_ARGS,
  FORGED_WIN_QUEST_ID,
  STARTER_PACK_ID,
  cheatBattery,
  createCheatContext,
  findCheatAttack,
  questWithVictory,
  runCheatAttack,
  runCheatBattery,
  type CheatAttack,
  type CheatContext,
  type CheatId,
} from './cheatbattery.ts';

import { isQuestVictory } from './quest.ts';
import type { CostContent, CostItem, CostOfferPack } from './commandcost.ts';

// The shipped `command.php` surface lives in `@swl/server`, which depends on
// `@swl/rules` — so `@swl/rules` cannot depend on it back without a cycle.
// The battery therefore lives here and exercises the rules + protocol layer,
// and this block cross-checks the wire-level attacks against the shim that
// actually serves the original client. The relative import is deliberate:
// it is a test-only edge across a package boundary that cannot be a
// dependency.
import { applyBatch, handleCommandPhp, type ShimContext, type ShimWorld } from '../../server/src/shim.ts';
import { LegacyIdentityBridge } from '../../server/src/session.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

interface RawItem {
  id: number;
  name: string;
  costs: Record<string, number>;
  cost_unit_cash: number;
}

interface RawPack {
  id: number;
  name: string;
  cost_cash: number;
  gold: number;
  wood: number;
  oil: number;
  steel: number;
  mana: number;
  xp: number;
  items: number[];
}

async function content(): Promise<CostContent> {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as {
    items: RawItem[];
    offerPacks: RawPack[];
    globals: Record<string, unknown>;
    expansionPrices: { coins: number; cash: number }[];
  };
  const items = new Map<number, CostItem>(
    bundle.items.map((i) => [
      i.id,
      { id: i.id, name: i.name, costs: i.costs, costUnitCash: i.cost_unit_cash },
    ]),
  );
  const offerPacks = new Map<number, CostOfferPack>(
    bundle.offerPacks.map((p) => [p.id, p]),
  );
  return {
    items,
    offerPacks,
    globals: bundle.globals,
    expansionPrices: bundle.expansionPrices,
    marketSellPercentage: bundle.globals['MARKET_SELL_PERCENTAGE'] as number,
    marketMaxTrades: bundle.globals['MARKET_MAX_NUM_TRADES'] as number,
    marketIncrement: bundle.globals['MARKET_INCREMENT'] as number,
    marketBaseCosts: bundle.globals['MARKET_BASE_COSTS'] as Record<string, number>,
  };
}

/**
 * The attack under test.
 *
 * The assertion is deliberately narrow: the battery reports the attack as
 * caught, and the failure message carries the reason the defence broke. A
 * test that only asserted "the report says caught" would pass for the wrong
 * reasons; this one fails with the exact broken invariant.
 */
function caught(ctx: CheatContext, id: CheatId): void {
  const attack = findCheatAttack(ctx, id);
  assert.ok(attack, `the battery must contain the attack ${id}`);
  const result = runCheatAttack(ctx, attack);
  assert.equal(
    result.caught,
    true,
    `the attack "${id}" got through: ${result.failure ?? result.note}`,
  );
}

describe('the cheat battery', () => {
  let ctx: CheatContext;

  it('is set up', async () => {
    ctx = createCheatContext(await content());
    assert.ok(ctx.attacker);
  });

  it('covers exactly the eleven roadmap attacks', async () => {
    const c = createCheatContext(await content());
    const ids = cheatBattery(c).map((attack) => attack.id);
    assert.equal(ids.length, 11);
    assert.deepEqual(ids, [
      'inflated-res',
      'flash-debug',
      'replayed-daily-bonus',
      'self-completed-goal',
      'forged-end-attack',
      'free-offer-pack',
      'wrong-hmac',
      'foreign-userid',
      'malformed-framing',
      'forged-win',
      'over-collection',
    ]);
  });

  it('names every attack and describes it', async () => {
    const c = createCheatContext(await content());
    for (const attack of cheatBattery(c)) {
      assert.ok(attack.name.length > 0, `${attack.id} needs a name`);
      assert.ok(attack.description.length > 0, `${attack.id} needs a description`);
      assert.ok(
        attack.kind === 'behavioural' || attack.kind === 'structural',
        `${attack.id} needs a kind`,
      );
    }
  });

  it('reports every attack as caught', async () => {
    const c = createCheatContext(await content());
    const report = runCheatBattery(c);
    assert.deepEqual(
      report.uncaught,
      [],
      `uncaught attacks: ${report.uncaught
        .map((id) => `${id} (${report.results.find((r) => r.id === id)?.failure ?? '?'})`)
        .join('; ')}`,
    );
    assert.equal(report.caught.length, 11);
    assert.equal(report.results.length, 11);
  });

  it('is deterministic — the same report twice', async () => {
    const c = createCheatContext(await content());
    const first = runCheatBattery(c);
    const second = runCheatBattery(c);
    assert.deepEqual(first, second);
  });
});

describe('attack 1 — inflated `res`', () => {
  it('does not let the declared delta reach the wallet', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'inflated-res');
  });
});

describe('attack 2 — forged `flash_debug`', () => {
  it('does not overwrite the wallet', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'flash-debug');
  });
});

describe('attack 3 — replayed `win_daily_bonus`', () => {
  it('pays the daily bonus once', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'replayed-daily-bonus');
  });
});

describe('attack 4 — self-completed goals', () => {
  it('pays a goal the player never finished', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'self-completed-goal');
  });
});

describe('attack 5 — forged `end_attack`', () => {
  it('pays the loot of a battle the server says was lost', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'forged-end-attack');
  });
});

describe('attack 6 — free `buy_offer_pack`', () => {
  it('grants an offer pack without payment', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'free-offer-pack');
  });
});

describe('attack 7 — wrong HMAC', () => {
  it('accepts a request signed with the wrong key', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'wrong-hmac');
  });
});

describe('attack 8 — another player\'s `USERID`', () => {
  it('acts on the player the body names', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'foreign-userid');
  });
});

describe('attack 9 — malformed framing', () => {
  it('accepts a body that is not `<64 hex>;<json>`', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'malformed-framing');
  });
});

describe('attack 10 — forged `win`', () => {
  it('grants the reward of a quest the server says was lost', async () => {
    const ctx = createCheatContext(await content());
    caught(ctx, 'forged-win');
  });
});

describe('the controls', () => {
  it('grants the quest reward when the server\'s own state says the quest was won', async () => {
    // The counterpart of attack 10: the decision comes from the server's
    // state, not from the client's flag. Without this control the attack
    // could pass for the wrong reason.
    const ctx = createCheatContext(await content());
    const won = questWithVictory(ctx);
    assert.equal(isQuestVictory(ctx.quest), false, 'the untouched quest must not be won');
    assert.equal(isQuestVictory(won), true, 'the completed quest must be won');
  });

  it('lets the attacker afford the worker the inflated-res attack buys', async () => {
    const ctx = createCheatContext(await content());
    assert.ok((ctx.attacker['g'] ?? 0) > 10, 'the fixture must be able to buy a Worker I');
    assert.equal(BUY_WORKER_ARGS[1], 1001, 'the fixture buys a Worker I');
  });

  it('has the offer pack the free-pack attack targets', async () => {
    const ctx = createCheatContext(await content());
    const pack = ctx.content.offerPacks.get(STARTER_PACK_ID);
    assert.ok(pack, 'the starter pack must exist');
    assert.ok(pack.cost_cash > 0, 'the starter pack must cost cash');
  });

  it('targets a quest the player has not won', async () => {
    const ctx = createCheatContext(await content());
    assert.equal(ctx.quest.questId, FORGED_WIN_QUEST_ID);
    assert.equal(isQuestVictory(ctx.quest), false);
  });
});

describe('the runner', () => {
  it('reports an attack as caught only when its verification passes', async () => {
    const ctx = createCheatContext(await content());
    // A rigged attack whose verification fails must be reported as NOT
    // caught — the battery never claims a defence it cannot show.
    const rigged: CheatAttack = {
      id: 'inflated-res',
      name: 'rigged',
      description: 'an attack whose verification fails',
      kind: 'behavioural',
      attempt: () => ({ succeeded: true, note: 'the cheat worked' }),
      verify: () => {
        throw new Error('the defence is broken');
      },
    };
    const result = runCheatAttack(ctx, rigged);
    assert.equal(result.caught, false);
    assert.equal(result.failure, 'the defence is broken');
  });

  it('reports an attack whose attempt throws as not caught', async () => {
    const ctx = createCheatContext(await content());
    const rigged: CheatAttack = {
      id: 'inflated-res',
      name: 'rigged',
      description: 'an attack that cannot even run',
      kind: 'behavioural',
      attempt: () => {
        throw new Error('the attempt blew up');
      },
      verify: () => {},
    };
    const result = runCheatAttack(ctx, rigged);
    assert.equal(result.caught, false);
    assert.equal(result.failure, 'the attempt blew up');
  });
});

/* ------------------------------------------------------------------------- *
 * The shipped command.php surface
 *
 * `@swl/rules` cannot depend on `@swl/server` (the server depends on the
 * rules), so the battery above exercises the rules + protocol layer. These
 * checks aim the same attacks at the shim that actually serves the original
 * client, so a defence that exists only in one of the two layers is visible.
 * ------------------------------------------------------------------------- */

function shimWorld(over: Partial<ShimWorld> = {}): ShimWorld {
  return {
    save: { playerInfo: {}, maps: [{}], privateState: {} },
    resources: { g: 1000, w: 1000, o: 1000, s: 1000, c: 1000, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
    ...over,
  };
}

async function shimContext(over: Partial<ShimContext> = {}): Promise<ShimContext> {
  return {
    world: shimWorld(),
    content: await content(),
    now: 1_700_000_000,
    identity: new LegacyIdentityBridge(),
    applyCommand: (world, command) => ({ applied: true, world }),
    ...over,
  };
}

describe('the shipped command.php shim', () => {
  it('refuses a body signed with the wrong key', async () => {
    const ctx = await shimContext();
    const payload = JSON.stringify({ first_number: 1, commands: [] });
    const response = handleCommandPhp(
      { path: '/command.php', fields: { data: framePayload(payload, 'not-a-real-key') } },
      ctx,
    );
    assert.equal(response.status, 403);
    assert.match(response.body, /bad-signature/);
  });

  it('refuses a body that is not framed', async () => {
    const ctx = await shimContext();
    const response = handleCommandPhp(
      { path: '/command.php', fields: { data: '{"commands":[]}' } },
      ctx,
    );
    assert.equal(response.status, 400);
    assert.match(response.body, /malformed-framing/);
  });

  it('refuses flash_debug outright and leaves the wallet alone', async () => {
    const ctx = await shimContext();
    const outcome = applyBatch(
      {
        first_number: 1,
        commands: [[1, 'flash_debug', [999_999, 999_999, 999_999, 999_999, 999_999, 999_999, 999_999], [0, 0, 999_999, 0, 0, 0, 0, 0]]],
      },
      ctx,
    );
    assert.equal(outcome.refused.length, 1);
    assert.equal(outcome.refused[0]?.name, 'flash_debug');
    assert.deepEqual(outcome.world.resources, shimWorld().resources);
  });

  it('ignores the declared resource delta', async () => {
    const ctx = await shimContext();
    const outcome = applyBatch(
      {
        first_number: 1,
        // A Worker I costs 10 gold; the client claims a million.
        commands: [[1, 'buy', BUY_WORKER_ARGS, [0, 0, 1_000_000, 0, 0, 0, 0, 0]]],
      },
      ctx,
    );
    assert.equal(outcome.refused.length, 0);
    assert.equal(outcome.world.resources['g'], 1000 - 10);
  });

  it('refuses an offer pack the player cannot afford', async () => {
    const ctx = await shimContext({
      world: shimWorld({ resources: { g: 1000, w: 0, o: 0, s: 0, c: 0, e: 100, x: 0, m: 0 } }),
    });
    const outcome = applyBatch(
      {
        first_number: 1,
        commands: [[1, 'buy_offer_pack', [STARTER_PACK_ID, '[]'], [0, 0, 5000, 5000, 5000, 5000, 0, 0]]],
      },
      ctx,
    );
    assert.equal(outcome.refused.length, 1);
    assert.equal(outcome.refused[0]?.reason, 'insufficient-resources');
    assert.equal(outcome.world.resources['g'], 1000);
  });

  it('binds the player from the request through the shim entry point', async () => {
    // The shim now resolves the player, which is what the tripwire was
    // waiting for. The resolution lives in `handleCommandPhp`, the HTTP
    // entry point; `applyBatch` stays a pure function over a world that has
    // already been identified.
    let consulted = 0;
    class CountingBridge extends LegacyIdentityBridge {
      override resolve(legacyUserId: string | null | undefined): string | null {
        consulted += 1;
        return super.resolve(legacyUserId);
      }
    }
    const bridge = new CountingBridge();
    bridge.allowLegacyIdentity();
    bridge.bind('e53386db-e42c-43c4-8c5c-9ace9c81ad91', 'player-victim');
    const ctx = await shimContext({ identity: bridge });

    // The pure function does not identify anybody.
    applyBatch(
      {
        first_number: 1,
        commands: [[1, 'buy', BUY_WORKER_ARGS, [0, 0, 0, 0, 0, 0, 0, 0]]],
      },
      ctx,
    );
    assert.equal(consulted, 0, 'applyBatch must stay pure over an identified world');

    // The entry point does, and it refuses a body that names a player the
    // server has not bound.
    const payload = JSON.stringify({
      first_number: 1,
      commands: [[1, 'buy', BUY_WORKER_ARGS, [0, 0, 0, 0, 0, 0, 0, 0]]],
    });
    const frame = framePayload(payload, SERVER_KEYS.current);
    const refused = handleCommandPhp(
      {
        path: '/command.php',
        fields: { USERID: 'someone-elses-id', data: frame },
      },
      ctx,
    );
    assert.equal(consulted, 1, 'the shim must consult the identity bridge');
    assert.equal(refused.status, 401, 'an unbound USERID must be refused');

    // The bound identity is accepted.
    const accepted = handleCommandPhp(
      {
        path: '/command.php',
        fields: { USERID: 'e53386db-e42c-43c4-8c5c-9ace9c81ad91', data: frame },
      },
      { ...ctx, world: { ...ctx.world, nextCommandNumber: 1 } },
    );
    assert.equal(accepted.status, 200);
  });
});
