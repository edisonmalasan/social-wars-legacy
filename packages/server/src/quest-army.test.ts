/**
 * Task 3 — the server-owned army.
 *
 * The team a client submits is only a request. These tests pin the pure
 * helpers that turn the server's own save into an availability map, parse an
 * untrusted body, and validate it before any active quest is written.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  QUEST_ID_07_SHIP,
  QUEST_ID_19_HARDCORE5,
  getQuestSpec,
  MAX_TEAM_SIZE,
} from '@swl/rules';

import {
  ownedArmy,
  parseQuestArmy,
  validateQuestArmy,
  type ApplierItem,
  type ShimWorld,
} from './apply.ts';

function item(over: Partial<ApplierItem> = {}): ApplierItem {
  return {
    id: 1017,
    name: 'goodBoy',
    type: 'u',
    costs: {},
    costUnitCash: 0,
    buildTime: 0,
    trainingTime: 60,
    clicksToBuild: 0,
    minLevel: 1,
    unitCapacity: 0,
    population: 1,
    buildingLimitSameId: -1,
    buildingLimitSameScf: -1,
    subcategoryId: 0,
    multiCollectable: false,
    grantsPopulation: false,
    width: 1,
    height: 1,
    trainsIds: [],
    upgradesTo: null,
    premiumUpgradeCosts: {},
    ...over,
  };
}

const ITEMS = new Map<number, ApplierItem>([
  [1017, item({ id: 1017, name: 'goodBoy' })],
  [1035, item({ id: 1035, name: 'truck' })],
  [89, item({ id: 89, name: 'nuclearPlant', type: 'b' })],
  [2001, item({ id: 2001, name: 'flyer', groupType: 'AIR_VEHICLE' })],
]);

function world(map: Record<string, unknown>, second?: Record<string, unknown>): ShimWorld {
  return {
    save: {
      playerInfo: {},
      maps: [map, ...(second ? [second] : [])],
      privateState: { boughtUnits: [1017, 1035, 2001] },
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
    nextCommandNumber: 1,
  } as ShimWorld;
}

function tuple(id: number, attrs?: Record<string, unknown>): unknown[] {
  return [id, 1, 1, 0, 0, 0, attrs ?? {}];
}

describe('parseQuestArmy', () => {
  it('accepts a small, whole, unique army', () => {
    const parsed = parseQuestArmy([{ unitId: 1017, count: 2 }, { unitId: 1035, count: 1 }]);
    assert.deepEqual(parsed, {
      ok: true,
      army: [{ unitId: 1017, count: 2 }, { unitId: 1035, count: 1 }],
    });
  });

  it('rejects malformed, duplicated and excessive input without trusting it', () => {
    assert.equal(parseQuestArmy('nope').ok, false);
    assert.equal(parseQuestArmy({ unitId: 1017, count: 1 }).ok, false);
    assert.equal(parseQuestArmy([{ unitId: 1017, count: 0 }]).ok, false);
    assert.equal(parseQuestArmy([{ unitId: 1.5, count: 1 }]).ok, false);
    assert.equal(parseQuestArmy([{ unitId: 1017, count: '2' }]).ok, false);
    assert.equal(parseQuestArmy([]).ok, false);
    const duplicate = parseQuestArmy([{ unitId: 1017, count: 1 }, { unitId: 1017, count: 2 }]);
    assert.deepEqual(duplicate, { ok: false, reason: 'team-duplicate' });
    const excessive = parseQuestArmy([{ unitId: 1017, count: MAX_TEAM_SIZE + 1 }]);
    assert.deepEqual(excessive, { ok: false, reason: 'team-too-large' });
  });
});

describe('ownedArmy', () => {
  it('reads only the player map store, placed units and finished training', () => {
    const map = {
      store: { '1017': 2, '89': 5, '1035': -1, '9999': 3 },
      items: {
        '1': tuple(1017),
        '2': tuple(1035),
        '3': tuple(30, { nu: 2, ui: 1017, ts: 100 }),
        '4': tuple(31, { nu: 5, ui: 1035, ts: 190 }),
        '5': tuple(32, { nu: 3, ui: 2001, ts: 'not-a-time' }),
      },
    };
    const second = { store: { '1035': 99 }, items: { '1': tuple(1035) } };
    // now = 200: the first queue (started at 100) has finished; the second
    // (started at 190) has not; the malformed timestamp proves nothing.
    assert.deepEqual([...ownedArmy(world(map, second), ITEMS, 200)].sort(), [
      [1017, 5], // 2 stored + 1 placed + 2 finished
      [1035, 1], // 1 placed; the negative store entry and other map are ignored
    ]);
  });
});

describe('validateQuestArmy', () => {
  const owned = new Map<number, number>([[1017, 3], [2001, 2]]);

  it('accepts an owned, allowed army and returns the server own copy', () => {
    const army = [{ unitId: 1017, count: 2 }];
    assert.deepEqual(
      validateQuestArmy(army, QUEST_ID_19_HARDCORE5, owned, ITEMS),
      { ok: true, army: [{ unitId: 1017, count: 2 }] },
    );
  });

  it('refuses a team on a quest that has no team selection', () => {
    assert.deepEqual(
      validateQuestArmy([{ unitId: 1017, count: 1 }], QUEST_ID_07_SHIP, owned, ITEMS),
      { ok: false, reason: 'team-not-supported' },
    );
  });

  it('refuses a unit that is not owned in the server state', () => {
    assert.deepEqual(
      validateQuestArmy([{ unitId: 1035, count: 1 }], QUEST_ID_19_HARDCORE5, owned, ITEMS),
      { ok: false, reason: 'team-unit-unavailable' },
    );
    assert.deepEqual(
      validateQuestArmy([{ unitId: 1017, count: 4 }], QUEST_ID_19_HARDCORE5, owned, ITEMS),
      { ok: false, reason: 'team-unit-unavailable' },
    );
    // A content id the server cannot name is not evidence of ownership.
    assert.deepEqual(
      validateQuestArmy([{ unitId: 9999, count: 1 }], QUEST_ID_19_HARDCORE5, owned, ITEMS),
      { ok: false, reason: 'team-unit-unavailable' },
    );
  });

  it('refuses a unit the quest excludes by its content group_type', () => {
    // Team quests exclude nothing in the shipped content. A synthetic spec
    // proves the group_type gate is actually wired, rather than only claimed.
    const spec = {
      ...getQuestSpec(QUEST_ID_19_HARDCORE5)!,
      excludedUnitGroupTypes: ['AIR_VEHICLE'],
    };
    assert.deepEqual(
      validateQuestArmy([{ unitId: 2001, count: 1 }], QUEST_ID_19_HARDCORE5, owned, ITEMS, spec),
      { ok: false, reason: 'team-unit-not-allowed' },
    );
  });
});
