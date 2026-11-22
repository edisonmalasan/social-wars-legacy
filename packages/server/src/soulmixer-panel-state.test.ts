/**
 * The Atom Fusion panel's server-published state.
 *
 * The client's selectors read `privateState.soulMixer`. These tests pin that
 * the record is derived only from the server's own save, its own fuse roll and
 * an already-validated building key — never from the client's declared output
 * id, cash delta or power. They also cover malformed saves and the rule that a
 * fresh save publishes no record at all.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  Random,
  buildSoulMixerCatalog,
  fuseWithPowerups,
  hashSeed,
  type SoulMixerItemData,
} from '@swl/rules';

import {
  SOUL_MIXER_PANEL_KEY,
  SOUL_MIXER_POWERUPS_KEY,
  createApplier,
  type ApplierDeps,
  type ApplierItem,
  type MapItemTuple,
} from './apply.ts';
import type { ShimWorld } from './shim.ts';

const NOW = 1_700_000_000;
const ISO = '7';
const MIXER = 302;
const SEED = 'fusion-test';

/** Units whose breeding order equals their id, so power == id. */
function ladderItems(): ApplierItem[] {
  const ids = Array.from({ length: 40 }, (_, index) => (index + 1) * 10);
  ids.push(1226, 1263);
  return ids.map((id) => ({
    id,
    name: `unit-${id}`,
    costs: {},
    costUnitCash: 0,
    buildTime: 1,
    trainingTime: 60,
    clicksToBuild: 0,
    minLevel: 1,
    unitCapacity: 0,
    population: 0,
    buildingLimitSameId: -1,
    buildingLimitSameScf: -1,
    subcategoryId: 0,
    width: 1,
    height: 1,
    trainsIds: [],
    upgradesTo: null,
    premiumUpgradeCosts: {},
    type: 'u',
    multiCollectable: false,
    grantsPopulation: false,
    life: id * 20,
    breedingOrder: id,
  }));
}

function mixerItem(): ApplierItem {
  return {
    id: MIXER,
    name: 'Atom Fusion',
    costs: {},
    costUnitCash: 0,
    buildTime: 60,
    trainingTime: 60,
    clicksToBuild: 0,
    minLevel: 1,
    unitCapacity: 2,
    population: 0,
    buildingLimitSameId: 1,
    buildingLimitSameScf: 1,
    subcategoryId: 211,
    width: 3,
    height: 3,
    trainsIds: [],
    upgradesTo: null,
    premiumUpgradeCosts: {},
    type: 'b',
    multiCollectable: false,
    grantsPopulation: false,
  };
}

function deps(): ApplierDeps {
  return {
    now: () => NOW,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
    dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
    serverSeed: SEED,
    items: new Map([
      [MIXER, mixerItem()],
      ...ladderItems().map((item) => [item.id, item] as const),
    ]),
  };
}

/** A world holding one mixer building with the two given inputs inside. */
function mixerWorld(inputs: number[], privateState: Record<string, unknown> = {}): ShimWorld {
  const attrs: Record<string, unknown> = { width: 3, height: 3, clicked: 0 };
  const tuple: MapItemTuple = [MIXER, 0, 0, 0, 0, inputs.map((id) => [id, 0, 0]), attrs, 1];
  return {
    save: {
      playerInfo: {},
      maps: [{ id: 0, items: { [ISO]: tuple }, store: {}, level: 20 }],
      privateState,
    },
    resources: { g: 0, w: 0, o: 0, s: 0, c: 1000, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

function panelOf(world: ShimWorld): Record<string, unknown> | undefined {
  const value = world.save.privateState[SOUL_MIXER_PANEL_KEY];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

/** The same roll the applier makes, so the published values can be pinned. */
function expectedFusion(inputs: [number, number], powerups: number[] = []) {
  const data: SoulMixerItemData[] = ladderItems().map((item) => ({
    id: item.id,
    breeding_order: item.breedingOrder!,
  }));
  return fuseWithPowerups(
    buildSoulMixerCatalog(data),
    inputs[0],
    inputs[1],
    powerups,
    new Random(hashSeed(`${SEED}:soulmixer:${ISO}:1`)),
  );
}

const FUSE: { name: string; args: unknown[] } = { name: 'push_queue_unit2', args: [Number(ISO)] };

describe('the server-published Atom Fusion record', () => {
  it('publishes nothing on a fresh save', () => {
    const world = mixerWorld([10, 20]);
    assert.equal(world.save.privateState[SOUL_MIXER_PANEL_KEY], undefined);
    const untouched = createApplier(deps())(world, {
      name: 'set_quest_var',
      args: ['playerLevel', 20],
    });
    assert.equal(untouched.applied, true);
    assert.equal(untouched.world.save.privateState[SOUL_MIXER_PANEL_KEY], undefined);
  });

  it('equals the deterministic server roll under a fixed seed', () => {
    const outcome = createApplier(deps())(mixerWorld([10, 20]), FUSE);
    assert.equal(outcome.applied, true);
    const expected = expectedFusion([10, 20]);
    assert.deepEqual(panelOf(outcome.world), {
      inputA: 10,
      inputB: 20,
      resultItemId: expected.result.id,
      resultPower: expected.result.power,
      powerUpLevel: 0,
      isoId: Number(ISO),
    });
  });

  it('reflects a paid power-up level from the server ledger, not the client price', () => {
    const applier = createApplier(deps());
    const bought = applier(mixerWorld([10, 20]), { name: 'buy_powerups', args: [3, 1] });
    assert.equal(bought.applied, true);
    assert.equal(panelOf(bought.world)?.['powerUpLevel'], 3);
    assert.equal(panelOf(bought.world)?.['resultItemId'], undefined);

    const outcome = applier(bought.world, FUSE);
    assert.equal(outcome.applied, true);
    const expected = expectedFusion([10, 20], [3]);
    assert.equal(panelOf(outcome.world)?.['resultItemId'], expected.result.id);
    assert.equal(panelOf(outcome.world)?.['resultPower'], expected.result.power);
    assert.deepEqual(outcome.world.save.privateState[SOUL_MIXER_POWERUPS_KEY], []);
  });

  it('never publishes a client-declared result id, power, price or iso', () => {
    const outcome = createApplier(deps())(mixerWorld([10, 20]), {
      name: 'push_queue_unit2',
      args: [Number(ISO), 999999, 12345, -500],
    });
    assert.equal(outcome.applied, true);
    const published = panelOf(outcome.world)!;
    const expected = expectedFusion([10, 20]);
    assert.equal(published['resultItemId'], expected.result.id);
    assert.notEqual(published['resultItemId'], 999999);
    assert.equal(published['resultPower'], expected.result.power);
    assert.notEqual(published['resultPower'], 12345);
    assert.equal(published['isoId'], Number(ISO));
    assert.notEqual(published['isoId'], 12345);
    assert.deepEqual(Object.keys(published).sort(), [
      'inputA',
      'inputB',
      'isoId',
      'powerUpLevel',
      'resultItemId',
      'resultPower',
    ]);
  });

  it('ignores the client cash delta in the speedup and keeps the validated iso', () => {
    const world = mixerWorld([10, 20], {
      [SOUL_MIXER_PANEL_KEY]: { isoId: 999, cash: 500, resultItemId: 111 },
    });
    const attrs = (world.save.maps[0]!['items'] as Record<string, MapItemTuple>)[ISO]![6]!;
    attrs['nu'] = 1;
    attrs['ts'] = NOW - 100;
    attrs['ui'] = 30;
    attrs['smTrainingTime'] = 1000;
    const outcome = createApplier(deps())(world, {
      name: 'soulmixer_speedup',
      args: [Number(ISO), -999],
    });
    assert.equal(outcome.applied, true);
    assert.equal(panelOf(outcome.world)?.['isoId'], Number(ISO));
    assert.equal(panelOf(outcome.world)?.['cash'], undefined);
    // The legitimate server-published result stays until the unit is popped.
    assert.equal(panelOf(outcome.world)?.['resultItemId'], 111);
  });

  it('clears a collected result only for the building the server published', () => {
    const applier = createApplier(deps());
    const fused = applier(mixerWorld([10, 20]), FUSE);
    const attrs = (fused.world.save.maps[0]!['items'] as Record<string, MapItemTuple>)[ISO]![6]!;
    // The unit is finished from the applier's point of view.
    attrs['ts'] = 0;
    assert.ok(panelOf(fused.world)!['resultItemId'] !== undefined);

    const popped = applier(fused.world, { name: 'pop_queue_unit', args: [Number(ISO)] });
    assert.equal(popped.applied, true);
    assert.equal(panelOf(popped.world)?.['resultItemId'], undefined);
    assert.equal(panelOf(popped.world)?.['resultPower'], undefined);
    assert.equal(panelOf(popped.world)?.['inputA'], 10);
  });

  it('degrades malformed and legacy saves to a clean server record', () => {
    for (const raw of ['garbage', 42, [], { resultItemId: -5, cash: 999, inputA: 'soon' }]) {
      const outcome = createApplier(deps())(mixerWorld([10, 20], {
        [SOUL_MIXER_PANEL_KEY]: raw,
      }), FUSE);
      assert.equal(outcome.applied, true);
      const published = panelOf(outcome.world)!;
      assert.equal(published['inputA'], 10);
      assert.equal(published['inputB'], 20);
      assert.equal(typeof published['resultItemId'], 'number');
      assert.equal(published['cash'], undefined);
    }
  });

  it('refuses a fake iso without publishing a record', () => {
    const outcome = createApplier(deps())(mixerWorld([10, 20]), {
      name: 'push_queue_unit2',
      args: [999, 999999],
    });
    assert.equal(outcome.applied, false);
    assert.equal(panelOf(outcome.world), undefined);
  });
});
