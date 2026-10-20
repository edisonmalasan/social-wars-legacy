import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  DIVISOR_SELL,
  buildCost,
  buildDurationMs,
  canPlaceBuilding,
  canUpgrade,
  clicksToBuild,
  premiumUpgradeCost,
  speedUpCost,
  trainingDurationMs,
  upgradeCost,
  type BuildingData,
  type PlacementState,
  type SpeedupRules,
  type UpgradeSpeedupPricing,
} from './building.ts';

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
  build_time: number;
  training_time: number;
  clicks_to_build: number;
  min_level: number;
  upgrades_to: number | null;
  unit_capacity: number;
  population: number;
  building_limit_same_id: number;
  building_limit_same_scf: number;
  premium_upgrade_costs: Record<string, number>;
  subcategory_id: number;
}

async function items(): Promise<Map<number, RawItem>> {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as { items: RawItem[] };
  return new Map(bundle.items.map((i) => [i.id, i]));
}

function asBuilding(raw: RawItem): BuildingData {
  return {
    id: raw.id,
    name: raw.name,
    costs: raw.costs,
    costUnitCash: raw.cost_unit_cash,
    buildTime: raw.build_time,
    trainingTime: raw.training_time,
    clicksToBuild: raw.clicks_to_build,
    minLevel: raw.min_level,
    upgradesTo: raw.upgrades_to,
    unitCapacity: raw.unit_capacity,
    population: raw.population,
    buildingLimitSameId: raw.building_limit_same_id,
    buildingLimitSameScf: raw.building_limit_same_scf,
    premiumUpgradeCosts: raw.premium_upgrade_costs,
  };
}

describe('building costs and durations', () => {
  it('reads the real costs', async () => {
    const map = await items();
    const academy = asBuilding(map.get(30)!);
    assert.deepEqual(buildCost(academy), { w: 125 });
    assert.equal(buildDurationMs(academy), 5000);
    assert.equal(trainingDurationMs(academy), 5000);
    assert.equal(clicksToBuild(academy), 1);
  });

  it('gives a unit its build cost too', async () => {
    const map = await items();
    const soldier = asBuilding(map.get(1007)!);
    assert.deepEqual(buildCost(soldier), { g: 30, s: 60 });
  });

  it('gives a building with no time an instant build', async () => {
    const map = await items();
    const worker = asBuilding(map.get(1001)!);
    assert.equal(buildDurationMs(worker), 0);
    assert.equal(clicksToBuild(worker), 0);
  });
});

describe('upgrades', () => {
  it('charges the new cost and refunds a twentieth of the old', async () => {
    const map = await items();
    const academyI = asBuilding(map.get(30)!); // w: 125
    const academyII = asBuilding(map.get(41)!);
    const cost = upgradeCost(academyI, academyII);
    // The refund is floor(125 / 20) = 6.
    assert.equal(cost['w'], academyII.costs['w']! - 6);
    assert.equal(DIVISOR_SELL, 20);
  });

  it('never goes below zero', async () => {
    const map = await items();
    const academyI = asBuilding(map.get(30)!);
    const cheap = asBuilding(map.get(25)!); // Wall III, s: 30
    const cost = upgradeCost(cheap, { ...cheap, costs: { s: 0 } });
    assert.equal(cost['s'], 0);
  });

  it('prices a premium upgrade by the build time', async () => {
    const map = await items();
    const commandCenter = asBuilding(map.get(60)!); // build_time 32400 s
    const pricing: UpgradeSpeedupPricing = { minutesPerUnit: 5, cashPerUnit: 1 };
    // 32400 s = 540 minutes, at one cash per 5 minutes.
    assert.equal(premiumUpgradeCost(commandCenter, pricing), 108);
  });

  it('checks the target level and a free tile', async () => {
    const map = await items();
    const academyII = asBuilding(map.get(41)!);
    assert.deepEqual(canUpgrade(academyII, academyII.minLevel, true), { ok: true });
    assert.deepEqual(canUpgrade(academyII, 0, true), { ok: false, reason: 'level' });
    assert.deepEqual(canUpgrade(academyII, 99, false), {
      ok: false,
      reason: 'no-free-tile',
    });
  });
});

describe('the speed-up', () => {
  const rules: SpeedupRules = { minRemainingMs: 10_000, cost: 2 };

  it('is refused when too little time is left', () => {
    assert.equal(speedUpCost(9_999, rules), null);
    assert.equal(speedUpCost(10_000, rules), 2);
    assert.equal(speedUpCost(60_000, rules), 2);
  });
});

describe('placement', () => {
  const state: PlacementState = {
    level: 10,
    populationUsed: 0,
    populationMax: 20,
    sameIdCounts: {},
    sameGroupCounts: {},
    subcategoryId: 31,
    hasFreeTile: true,
  };

  it('refuses a building above the player level', async () => {
    const map = await items();
    const wallIII = asBuilding(map.get(25)!); // min_level 17
    assert.deepEqual(canPlaceBuilding(wallIII, state), { ok: false, reason: 'level' });
    assert.deepEqual(canPlaceBuilding(wallIII, { ...state, level: 20 }), { ok: true });
  });

  it('refuses a building over the population', async () => {
    const map = await items();
    const commandCenter = asBuilding(map.get(60)!); // population 5, min_level 35
    // The level is checked first, so the state has to be at the right level
    // for the population refusal to be the one that fires.
    assert.deepEqual(
      canPlaceBuilding(commandCenter, { ...state, level: 35, populationUsed: 18 }),
      { ok: false, reason: 'population' },
    );
    assert.deepEqual(
      canPlaceBuilding(commandCenter, { ...state, level: 35, populationUsed: 10 }),
      { ok: true },
    );
  });

  it('refuses a building over its per-id limit', async () => {
    const map = await items();
    const academy = asBuilding(map.get(30)!);
    const limit = academy.buildingLimitSameId;
    if (limit >= 0) {
      assert.deepEqual(
        canPlaceBuilding(academy, {
          ...state,
          sameIdCounts: { [String(academy.id)]: limit },
        }),
        { ok: false, reason: 'same-id-limit' },
      );
    }
  });

  it('refuses when there is no free tile', async () => {
    const map = await items();
    const academy = asBuilding(map.get(30)!);
    assert.deepEqual(canPlaceBuilding(academy, { ...state, hasFreeTile: false }), {
      ok: false,
      reason: 'no-free-tile',
    });
  });
});
