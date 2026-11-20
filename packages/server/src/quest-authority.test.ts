/**
 * Task 2 — server-owned quest start and authoritative events.
 *
 * These tests pin the authority contract: a quest can only be started through
 * the server, a kill is only real once a server-owned ledger marks the element
 * dead, and the four event-driven quests move counters that only the server
 * seeds. Every refusal leaves the save untouched.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  QUEST_ID_01_BAZOOKA,
  QUEST_ID_02_CENTRAL_NUCLEAR,
  QUEST_ID_03_DEFEND_CONVOY_AUTO,
  QUEST_ID_10_SPECIAL_OPS,
  QUEST_ID_11_SAVE_VILLAGES,
  QUEST_ID_14_SPY_2,
} from '@swl/rules';

import {
  ACTIVE_QUEST_KEY,
  createApplier,
  createQuestHelpers,
  type ActiveQuestState,
  type ApplierDeps,
  type ApplierItem,
  type ContentQuestEvent,
  type QuestAction,
} from './apply.ts';
import { MemoryPlayerStore } from './store.ts';
import type { ShimWorld } from './shim.ts';

const Q02 = QUEST_ID_02_CENTRAL_NUCLEAR;
const Q03 = QUEST_ID_03_DEFEND_CONVOY_AUTO;
const Q10 = QUEST_ID_10_SPECIAL_OPS;
const Q11 = QUEST_ID_11_SAVE_VILLAGES;
const Q14 = QUEST_ID_14_SPY_2;

/** Content items, with the `life` the ledger seeds HP from. */
const ITEMS = new Map<number, ApplierItem>([
  [1017, { id: 1017, name: 'goodBoy', type: 'u', life: 4, subcatFunctional: 115 } as ApplierItem],
  [89, { id: 89, name: 'centralNuclear', type: 'b', life: 2, subcatFunctional: 112 } as ApplierItem],
  [195, { id: 195, name: 'commandCenter', type: 'b', life: 1, subcatFunctional: 113 } as ApplierItem],
  [1035, { id: 1035, name: 'truck', type: 'u', life: 3, subcatFunctional: 114 } as ApplierItem],
]);

/** Build-time event data, exactly the shape the bundle carries. */
const EVENTS: Readonly<Record<string, ContentQuestEvent>> = {
  [Q03]: { questId: Q03, kind: 'truckArrivals', refs: ['item:1013'], count: 3 },
  [Q10]: {
    questId: Q10,
    kind: 'eligibleEnemies',
    refs: ['item:10', 'item:11', 'item:12', 'item:13'],
    count: 3,
  },
  [Q11]: { questId: Q11, kind: 'civilianEvacuations', refs: ['item:20', 'item:21', 'item:22'], count: 3 },
  [Q14]: { questId: Q14, kind: 'eligibleEnemies', refs: ['item:30', 'item:31', 'item:32'], count: 3 },
};

function qdeps(over: Partial<ApplierDeps> = {}): ApplierDeps {
  return {
    now: () => 1000,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [5, 60], multiplier: [0.25, 1] },
    dailyBonus: { goldRewards: [0], heroItemId: 1 },
    items: ITEMS,
    questEvents: EVENTS,
    serverSeed: 'the-servers-own-seed',
    questExpRequired: 300,
    ...over,
  };
}

function freshWorld(): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, idCurrentMission: 1, currentQuestVars: {} }],
      privateState: {},
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

const active = (world: ShimWorld): ActiveQuestState =>
  world.save.privateState[ACTIVE_QUEST_KEY] as ActiveQuestState;

/** A `set_quest_var` killed write — two arguments, never a third. */
const killed = (refs: string[]) => ({
  name: 'set_quest_var',
  args: ['killed', JSON.stringify(refs)],
});

describe('beginQuest', () => {
  it('creates an active state with a server-owned ledger and seeded counters', () => {
    const result = createQuestHelpers(qdeps()).beginQuest(freshWorld(), Q02);
    assert.equal(result.ok, true, result.ok ? '' : result.reason);
    if (!result.ok) return;
    const state = active(result.world);
    assert.equal(state.questId, Q02);
    assert.equal(state.phase, 'map-loaded');
    assert.deepEqual(
      Object.keys(state.ledger.elements).sort(),
      ['centralNuclear', 'commandCenter', 'goodBoy', 'truck'],
    );
    // HP comes from content `life`; every element starts alive.
    for (const element of Object.values(state.ledger.elements)) {
      assert.equal(element.alive, true);
      assert.ok(element.hp > 0);
    }
    // The ledger's HP is an abstract encounter budget derived from content,
    // not the original client's combat HP. It is bounded so a kill can always
    // be proven in at most four authoritative strikes.
    assert.equal(state.ledger.elements['commandCenter']!.hp, 1);
    assert.equal(state.ledger.elements['centralNuclear']!.hp, 1);
    for (const element of Object.values(state.ledger.elements)) {
      assert.ok(element.hp >= 1 && element.hp <= 4);
    }
    assert.deepEqual(state.ledger.events, []);
  });

  it('derives at most four strikes of encounter HP from the content life', () => {
    // The values are the server's own, scaled from the item's `life`, and a
    // missing or invalid life falls back to a single strike. No client input
    // reaches this calculation.
    const items = new Map<number, ApplierItem>([
      [1017, { id: 1017, name: 'goodBoy', type: 'u', life: 1, subcatFunctional: 115 } as ApplierItem],
      [89, { id: 89, name: 'centralNuclear', type: 'b', life: 401, subcatFunctional: 112 } as ApplierItem],
      [195, { id: 195, name: 'commandCenter', type: 'b', life: 2000, subcatFunctional: 113 } as ApplierItem],
      // 1035 is absent: the fallback must be one strike.
    ]);
    const result = createQuestHelpers(qdeps({ items })).beginQuest(freshWorld(), Q02);
    assert.equal(result.ok, true, result.ok ? '' : result.reason);
    if (!result.ok) return;
    const elements = active(result.world).ledger.elements;
    assert.deepEqual(
      Object.fromEntries(Object.entries(elements).map(([ref, element]) => [ref, element.hp])),
      { goodBoy: 1, centralNuclear: 2, commandCenter: 4, truck: 1 },
    );
  });

  it('seeds the four event quests with server-owned counters', () => {
    const helpers = createQuestHelpers(qdeps());
    const cases: [string, string, number][] = [
      [Q03, 'trucksArrived', 0],
      [Q10, 'bastardsAlive', 3],
      [Q11, 'workersInVillages', 3],
      [Q14, 'bastardsAlive', 3],
    ];
    for (const [questId, counter, value] of cases) {
      const result = helpers.beginQuest(freshWorld(), questId);
      assert.equal(result.ok, true, `${questId}: ${result.ok ? '' : result.reason}`);
      if (!result.ok) continue;
      assert.equal(active(result.world).script.counters[counter], value, questId);
    }
  });

  it('refuses an unknown quest id without changing the save', () => {
    const world = freshWorld();
    const before = structuredClone(world);
    const result = createQuestHelpers(qdeps()).beginQuest(world, '999999999');
    assert.equal(result.ok, false);
    if (result.ok) return;
    assert.equal(result.reason, 'unknown-quest');
    assert.deepEqual(result.world, before);
  });

  it('refuses a second start while a quest is active', () => {
    const first = createQuestHelpers(qdeps()).beginQuest(freshWorld(), Q02);
    assert.equal(first.ok, true);
    if (!first.ok) return;
    const before = structuredClone(first.world);
    const second = createQuestHelpers(qdeps()).beginQuest(first.world, Q10);
    assert.equal(second.ok, false);
    if (second.ok) return;
    assert.equal(second.reason, 'active-quest-exists');
    assert.deepEqual(second.world, before);
  });

  it('replaces a bare `{ questId }` seed on an explicit start', () => {
    const world = freshWorld();
    world.save.privateState[ACTIVE_QUEST_KEY] = { questId: Q10 };
    const result = createQuestHelpers(qdeps()).beginQuest(world, Q02);
    assert.equal(result.ok, true, result.ok ? '' : result.reason);
    if (!result.ok) return;
    const state = active(result.world);
    assert.equal(state.questId, Q02);
    assert.ok(Object.keys(state.ledger.elements).length > 0);
  });

  it('persists the active state through the store', async () => {
    const store = new MemoryPlayerStore([{ playerId: 'p1', world: freshWorld() }]);
    await store.transact('p1', (world) => {
      const result = createQuestHelpers(qdeps()).beginQuest(world, Q02);
      assert.equal(result.ok, true);
      return result.ok ? result.world : world;
    });
    const saved = (await store.get('p1'))!;
    assert.equal(active(saved.world).questId, Q02);
    assert.ok(Object.keys(active(saved.world).ledger.elements).length > 0);
  });
});

describe('authoritative strikes and killed writes', () => {
  it('accepts a killed ref only once the ledger marks it dead', () => {
    const applier = createApplier(qdeps());
    const helpers = createQuestHelpers(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q02);
    assert.equal(started.ok, true);
    if (!started.ok) return;

    // Roster membership alone is not a kill: the client's killed write is
    // refused while the server's ledger still says the element is alive.
    const early = applier(started.world, killed(['commandCenter']));
    assert.equal(early.applied, false);
    assert.equal(early.refused, 'element-not-killed');
    // A refused write leaves the whole save untouched, not just the wallet.
    assert.deepEqual(early.world, started.world);
    assert.deepEqual(active(early.world).script.destroyed, []);

    // The server's own strike damages the element deterministically.
    const struck = helpers.applyQuestAction(started.world, Q02, {
      type: 'strike',
      ref: 'commandCenter',
    });
    assert.equal(struck.ok, true, struck.ok ? '' : struck.reason);
    if (!struck.ok) return;
    assert.equal(active(struck.world).ledger.elements['commandCenter']!.alive, false);

    const beforeAccepted = structuredClone(struck.world);
    const accepted = applier(struck.world, killed(['commandCenter']));
    assert.equal(accepted.applied, true);
    assert.deepEqual(active(accepted.world).script.destroyed, ['commandCenter']);
    // The accepted write advances the server's quest state, and it does so
    // without claiming a reward or any client-declared counter.
    assert.notDeepEqual(accepted.world, beforeAccepted);
    assert.deepEqual(active(accepted.world).ledger, active(beforeAccepted).ledger);
  });

  it('kills a high-life element in at most four server strikes', () => {
    // Even a building whose content life is 2000 is an encounter that a real
    // client can finish through the workflow: its ledger HP is bounded.
    const items = new Map<number, ApplierItem>([
      [89, { id: 89, name: 'centralNuclear', type: 'b', life: 2, subcatFunctional: 112 } as ApplierItem],
      [195, { id: 195, name: 'commandCenter', type: 'b', life: 2000, subcatFunctional: 113 } as ApplierItem],
    ]);
    const helpers = createQuestHelpers(qdeps({ items }));
    const started = helpers.beginQuest(freshWorld(), Q02);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    assert.equal(active(started.world).ledger.elements['commandCenter']!.hp, 4);

    let world = started.world;
    let strikes = 0;
    while (active(world).ledger.elements['commandCenter']!.alive && strikes < 4) {
      const next = helpers.applyQuestAction(world, Q02, {
        type: 'strike',
        ref: 'commandCenter',
      });
      assert.equal(next.ok, true, next.ok ? '' : next.reason);
      if (!next.ok) return;
      world = next.world;
      strikes += 1;
    }
    assert.equal(active(world).ledger.elements['commandCenter']!.alive, false);
    assert.ok(strikes >= 1 && strikes <= 4, `the kill took ${strikes} strikes`);

    // The same strictly two-argument write that was refused before is now
    // accepted because the server's ledger proves the kill.
    const before = structuredClone(world);
    const killedWrite = createApplier(qdeps({ items }))(world, killed(['commandCenter']));
    assert.equal(killedWrite.applied, true);
    assert.deepEqual(active(killedWrite.world).script.destroyed, ['commandCenter']);
    assert.notDeepEqual(killedWrite.world, before);
  });

  it('damages from the server seed and refuses a strike on a dead element', () => {
    const helpers = createQuestHelpers(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q02);
    assert.equal(started.ok, true);
    if (!started.ok) return;

    // `centralNuclear` has life 2, so a single strike need not be fatal — but
    // enough deterministic strikes always are, and the outcome is stable.
    let world = started.world;
    let strikes = 0;
    while (active(world).ledger.elements['centralNuclear']!.alive && strikes < 20) {
      const next = helpers.applyQuestAction(world, Q02, {
        type: 'strike',
        ref: 'centralNuclear',
      });
      assert.equal(next.ok, true, next.ok ? '' : next.reason);
      if (!next.ok) break;
      world = next.world;
      strikes += 1;
    }
    assert.equal(active(world).ledger.elements['centralNuclear']!.alive, false);
    const before = structuredClone(world);
    const again = helpers.applyQuestAction(world, Q02, { type: 'strike', ref: 'centralNuclear' });
    assert.equal(again.ok, false);
    if (again.ok) return;
    assert.equal(again.reason, 'element-already-dead');
    assert.deepEqual(again.world, before);
  });

  it('refuses strikes and killed writes that name a different quest', () => {
    const helpers = createQuestHelpers(qdeps());
    const applier = createApplier(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q02);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    const before = structuredClone(started.world);

    const strike = helpers.applyQuestAction(started.world, Q10, {
      type: 'strike',
      ref: 'commandCenter',
    });
    assert.equal(strike.ok, false);
    if (strike.ok) return;
    assert.equal(strike.reason, 'quest-mismatch');
    assert.deepEqual(strike.world, before);

    // There is no third argument any more: a killed write cannot name a quest.
    const forged = applier(started.world, {
      name: 'set_quest_var',
      args: ['killed', JSON.stringify(['commandCenter']), Q10],
    });
    assert.equal(forged.applied, false);
    assert.equal(forged.refused, 'element-not-killed');
  });

  it('refuses actions without an active quest or after the quest has finished', () => {
    const helpers = createQuestHelpers(qdeps());
    const none = helpers.applyQuestAction(freshWorld(), Q02, {
      type: 'strike',
      ref: 'commandCenter',
    });
    assert.equal(none.ok, false);
    if (none.ok) return;
    assert.equal(none.reason, 'no-active-quest');

    const started = helpers.beginQuest(freshWorld(), Q02);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    const finished = structuredClone(started.world);
    (active(finished) as { phase: string }).phase = 'finished';
    const late = helpers.applyQuestAction(finished, Q02, {
      type: 'strike',
      ref: 'commandCenter',
    });
    assert.equal(late.ok, false);
    if (late.ok) return;
    assert.equal(late.reason, 'invalid-phase');
  });
});

describe('Q03 truck arrivals', () => {
  const arrival: QuestAction = { type: 'truck-arrival', ref: 'item:1013' };

  it('requires the truck ref and increments at most three times', () => {
    const helpers = createQuestHelpers(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q03);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    assert.equal(active(started.world).script.counters['trucksArrived'], 0);

    const offRoster = helpers.applyQuestAction(started.world, Q03, {
      type: 'truck-arrival',
      ref: 'item:999',
    });
    assert.equal(offRoster.ok, false);
    if (offRoster.ok) return;
    assert.equal(offRoster.reason, 'unknown-event-ref');

    let world = started.world;
    for (let expected = 1; expected <= 3; expected += 1) {
      const next = helpers.applyQuestAction(world, Q03, arrival);
      assert.equal(next.ok, true, next.ok ? '' : next.reason);
      if (!next.ok) return;
      world = next.world;
      assert.equal(active(world).script.counters['trucksArrived'], expected);
    }
    // A fourth truck is a duplicate/excess event: refused, save unchanged.
    const before = structuredClone(world);
    const fourth = helpers.applyQuestAction(world, Q03, arrival);
    assert.equal(fourth.ok, false);
    if (fourth.ok) return;
    assert.equal(fourth.reason, 'event-limit-reached');
    assert.deepEqual(fourth.world, before);
  });

  it('refuses an arrival whose dedupe key is already in the ledger', () => {
    const helpers = createQuestHelpers(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q03);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    // The first arrival's key has already been recorded — for example by a
    // retry that reached the applier — so the counter must not move again.
    const world = structuredClone(started.world);
    active(world).ledger.events.push('arrival:item:1013:1');
    const before = structuredClone(world);
    const replayed = helpers.applyQuestAction(world, Q03, arrival);
    assert.equal(replayed.ok, false);
    if (replayed.ok) return;
    assert.equal(replayed.reason, 'event-already-seen');
    assert.equal(active(replayed.world).script.counters['trucksArrived'], 0);
    assert.deepEqual(replayed.world, before);
  });

  it('the action kind must match the quest event channel', () => {
    const helpers = createQuestHelpers(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q03);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    const wrong = helpers.applyQuestAction(started.world, Q03, {
      type: 'civilian-evacuation',
      ref: 'item:1013',
    });
    assert.equal(wrong.ok, false);
    if (wrong.ok) return;
    assert.equal(wrong.reason, 'wrong-event-kind');
  });
});

describe('Q10/Q14 eligible enemies', () => {
  for (const [questId, refs] of [
    [Q10, ['item:10', 'item:11', 'item:12', 'item:13']],
    [Q14, ['item:30', 'item:31', 'item:32']],
  ] as const) {
    it(`decrements bastardsAlive, refuses off-roster and never goes negative (${questId})`, () => {
      const helpers = createQuestHelpers(qdeps());
      const started = helpers.beginQuest(freshWorld(), questId);
      assert.equal(started.ok, true);
      if (!started.ok) return;
      assert.equal(active(started.world).script.counters['bastardsAlive'], 3);

      const offRoster = helpers.applyQuestAction(started.world, questId, {
        type: 'eligible-enemy',
        ref: 'item:999',
      });
      assert.equal(offRoster.ok, false);
      if (offRoster.ok) return;
      assert.equal(offRoster.reason, 'unknown-event-ref');

      let world = started.world;
      // The refs outnumber the seeded counter: once it reaches zero, one
      // more valid ref cannot make it negative.
      for (const ref of refs) {
        const next = helpers.applyQuestAction(world, questId, {
          type: 'eligible-enemy',
          ref,
        });
        assert.equal(next.ok, true, `${ref}: ${next.ok ? '' : next.reason}`);
        if (!next.ok) return;
        world = next.world;
        assert.ok(active(world).script.counters['bastardsAlive']! >= 0);
      }
      assert.equal(active(world).script.counters['bastardsAlive'], 0);

      const before = structuredClone(world);
      const replayed = helpers.applyQuestAction(world, questId, {
        type: 'eligible-enemy',
        ref: refs[0]!,
      });
      assert.equal(replayed.ok, false);
      if (replayed.ok) return;
      assert.equal(replayed.reason, 'event-already-seen');
      assert.deepEqual(replayed.world, before);
    });
  }
});

describe('Q11 civilian evacuations', () => {
  it('decrements workersInVillages and refuses a duplicated civilian', () => {
    const helpers = createQuestHelpers(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q11);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    assert.equal(active(started.world).script.counters['workersInVillages'], 3);

    const first = helpers.applyQuestAction(started.world, Q11, {
      type: 'civilian-evacuation',
      ref: 'item:20',
    });
    assert.equal(first.ok, true, first.ok ? '' : first.reason);
    if (!first.ok) return;
    assert.equal(active(first.world).script.counters['workersInVillages'], 2);

    const before = structuredClone(first.world);
    const duplicate = helpers.applyQuestAction(first.world, Q11, {
      type: 'civilian-evacuation',
      ref: 'item:20',
    });
    assert.equal(duplicate.ok, false);
    if (duplicate.ok) return;
    assert.equal(duplicate.reason, 'event-already-seen');
    assert.deepEqual(duplicate.world, before);
  });
});

describe('end_quest after an explicit start', () => {
  const applier = () => createApplier(qdeps());

  it('refuses a win with no active quest, leaving the save unchanged', () => {
    const world = freshWorld();
    const before = structuredClone(world);
    const outcome = applier()(world, { name: 'end_quest', args: [Q02, 1] });
    assert.equal(outcome.applied, false);
    assert.equal(outcome.refused, 'no-active-quest');
    assert.deepEqual(outcome.world, before);
  });

  it('pays the content reward once, pays nothing on a replay and leaves chapter state alone', () => {
    const helpers = createQuestHelpers(qdeps());
    const started = helpers.beginQuest(freshWorld(), Q02);
    assert.equal(started.ok, true);
    if (!started.ok) return;
    const struck = helpers.applyQuestAction(started.world, Q02, {
      type: 'strike',
      ref: 'commandCenter',
    });
    assert.equal(struck.ok, true);
    if (!struck.ok) return;
    const killedWrite = applier()(struck.world, killed(['commandCenter']));
    assert.equal(killedWrite.applied, true);

    const chapterBefore = structuredClone(killedWrite.world.save.maps[0]);
    const first = applier()(killedWrite.world, { name: 'end_quest', args: [Q02, 1] });
    assert.equal(first.applied, true);
    assert.equal(first.world.resources['g'], 4000);
    assert.equal(first.world.resources['o'], 1400);
    assert.deepEqual(first.world.save.maps[0], chapterBefore);
    assert.equal(ACTIVE_QUEST_KEY in first.world.save.privateState, false);

    const replay = applier()(first.world, { name: 'end_quest', args: [Q02, 1] });
    assert.equal(replay.applied, false);
    assert.deepEqual(replay.world.resources, first.world.resources);
  });

  it('resolves an event quest from its server-seeded counters', () => {
    const helpers = createQuestHelpers(qdeps());
    let world = helpers.beginQuest(freshWorld(), Q03);
    assert.equal(world.ok, true);
    if (!world.ok) return;
    let result = world;
    for (let i = 0; i < 3; i += 1) {
      const next = helpers.applyQuestAction(result.world, Q03, {
        type: 'truck-arrival',
        ref: 'item:1013',
      });
      assert.equal(next.ok, true, next.ok ? '' : next.reason);
      if (!next.ok) return;
      result = next;
    }
    const outcome = applier()(result.world, { name: 'end_quest', args: [Q03, 1] });
    assert.equal(outcome.applied, true, outcome.refused ?? '');
    assert.equal(outcome.world.resources['g'], 2500);
    assert.equal(outcome.world.resources['o'], 800);
  });
});
