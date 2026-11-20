/**
 * Task 3 — the player's army, as a reading of the server's own save.
 *
 * Nothing here grants a unit. Counts come from the server's store, its placed
 * map items and its finished training queues; names and group types come from
 * the content. An in-progress queue is not a unit the player may field yet.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { MAX_TEAM_SIZE } from '@swl/rules';

import { chooseArmyCount, initialArmySelection, armyView, type ArmyItemDefinition } from './army.ts';
import type { WorldSnapshot } from './session.ts';

const DEFINITIONS: readonly ArmyItemDefinition[] = [
  { id: 1017, name: 'Good Boy', type: 'u', groupType: 'INFANTRY', trainingTime: 60 },
  { id: 1035, name: 'Truck', type: 'u', groupType: 'VEHICLE', trainingTime: 30 },
  { id: 89, name: 'Nuclear plant', type: 'b', groupType: 'BUILDING', trainingTime: 0 },
];

function world(map: Record<string, unknown>, second?: Record<string, unknown>): WorldSnapshot {
  return {
    maps: [map, ...(second ? [second] : [])],
    privateState: { boughtUnits: [1017, 1035] },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 0, e: 0, x: 0, m: 0 },
  } as unknown as WorldSnapshot;
}

const tile = (id: number, attrs?: Record<string, unknown>): unknown[] => [
  id, 1, 1, 0, 0, 0, attrs ?? {},
];

describe('armyView', () => {
  it('reads stored, placed and finished units, never a building or an unfinished queue', () => {
    const view = armyView(
      world({
        store: { '1017': 1, '89': 4, '1035': -1, '9999': 9 },
        items: {
          '1': tile(1017),
          '2': tile(30, { nu: 2, ui: 1017, ts: 100 }),
          '3': tile(31, { nu: 5, ui: 1035, ts: 190 }),
        },
      }),
      DEFINITIONS,
      200,
    );
    assert.deepEqual(view, [
      { itemId: 1017, name: 'Good Boy', groupType: 'INFANTRY', available: 4, allowed: true },
    ]);
  });

  it('ignores other maps, malformed stores and unknown content ids', () => {
    const view = armyView(
      world(
        { store: 'broken', items: { '1': tile(1017) } },
        { store: { '1035': 99 }, items: { '1': tile(1035) } },
      ),
      DEFINITIONS,
      200,
    );
    assert.deepEqual(view, [
      { itemId: 1017, name: 'Good Boy', groupType: 'INFANTRY', available: 1, allowed: true },
    ]);
  });

  it('marks a group type a quest excludes as not allowed', () => {
    const view = armyView(
      world({ store: { '1017': 1 }, items: {} }),
      DEFINITIONS,
      200,
      ['INFANTRY'],
    );
    assert.deepEqual(view, [
      { itemId: 1017, name: 'Good Boy', groupType: 'INFANTRY', available: 1, allowed: false },
    ]);
  });

  it('reads an empty army when there is no map or no owned unit', () => {
    assert.deepEqual(armyView({ ...world({}), maps: [] }, DEFINITIONS, 200), []);
    assert.deepEqual(armyView(world({}), DEFINITIONS, 200), []);
  });
});

describe('team selection budget', () => {
  const army = [
    { itemId: 1017, name: 'Good Boy', groupType: 'INFANTRY', available: 15, allowed: true },
    { itemId: 1035, name: 'Truck', groupType: 'VEHICLE', available: 15, allowed: true },
  ];
  const total = (counts: Record<number, number>): number =>
    Object.values(counts).reduce((sum, count) => sum + count, 0);

  it('starts within the shared cap across more than one unit', () => {
    assert.deepEqual(initialArmySelection(army), { 1017: 15, 1035: 5 });
    assert.equal(total(initialArmySelection(army)), MAX_TEAM_SIZE);
  });

  it('clamps a later selection to the remaining team-size budget', () => {
    let counts = chooseArmyCount({}, 1017, 15, 15);
    assert.deepEqual(counts, { 1017: 15 });
    counts = chooseArmyCount(counts, 1035, 15, 15);
    assert.deepEqual(counts, { 1017: 15, 1035: 5 });
    assert.equal(total(counts), MAX_TEAM_SIZE);

    // An oversized input cannot push the team past the server's cap.
    counts = chooseArmyCount(counts, 1017, 99, 15);
    assert.deepEqual(counts, { 1017: 15, 1035: 5 });

    // Freeing slots lets another unit take exactly those slots.
    counts = chooseArmyCount(counts, 1017, 2, 15);
    assert.deepEqual(counts, { 1017: 2, 1035: 5 });
    counts = chooseArmyCount(counts, 1035, 15, 15);
    assert.deepEqual(counts, { 1017: 2, 1035: 15 });
    assert.equal(total(counts), 17);
  });
});
