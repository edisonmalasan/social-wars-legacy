import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  MULTIPLIER_PEASANTS,
  canPlaceUnit,
  collect,
  currentPopulation,
  expansionPrice,
  maxPopulation,
  meetsLevelRequirement,
  regenerateEnergy,
  townPrice,
  type CollectPeriods,
  type EnergyRules,
  type PopulationRules,
  type PriceRow,
} from './economy.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

interface Bundle {
  globals: Record<string, unknown>;
  expansionPrices: PriceRow[];
  townPrices: PriceRow[];
}

async function bundle(): Promise<Bundle> {
  return JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as Bundle;
}

function periods(g: Record<string, unknown>): CollectPeriods {
  return {
    minutes: g['COLLECT_MINUTES'] as number[],
    multiplier: g['COLLECT_MULTIPLIER'] as number[],
  };
}

describe('collection', () => {
  it('uses the shipped collect periods', async () => {
    const { globals } = await bundle();
    const p = periods(globals);
    assert.deepEqual(p.minutes, [5, 60, 240, 480]);
    assert.deepEqual(p.multiplier, [0.25, 1, 2, 3]);
  });

  it('collects the base amount on the one-hour period', async () => {
    const { globals } = await bundle();
    const result = collect(
      { collect: 100, unitCapacity: 5, unitsInside: 0 },
      2,
      periods(globals),
    );
    assert.equal(result.amount, 100);
    assert.equal(result.hacked, false);
  });

  it('applies the period multiplier', async () => {
    const { globals } = await bundle();
    const p = periods(globals);
    const producer = { collect: 100, unitCapacity: 5, unitsInside: 0 };
    assert.equal(collect(producer, 1, p).amount, 25); // 5 min, x0.25
    assert.equal(collect(producer, 2, p).amount, 100); // 60 min, x1
    assert.equal(collect(producer, 3, p).amount, 200); // 240 min, x2
    assert.equal(collect(producer, 4, p).amount, 300); // 480 min, x3
  });

  it('adds 20% of the base for each extra worker', async () => {
    const { globals } = await bundle();
    const p = periods(globals);
    // The formula is (units - 1) * base * 0.2, so the first worker inside
    // adds nothing: it is the base worker, not an extra one.
    const one = collect({ collect: 100, unitCapacity: 5, unitsInside: 1 }, 2, p);
    assert.equal(one.amount, 100);
    // two workers -> 100 + 1*100*0.2 = 120
    const two = collect({ collect: 100, unitCapacity: 5, unitsInside: 2 }, 2, p);
    assert.equal(two.amount, 120);
    // three workers -> 100 + 2*100*0.2 = 140
    const three = collect({ collect: 100, unitCapacity: 5, unitsInside: 3 }, 2, p);
    assert.equal(three.amount, 140);
    assert.equal(MULTIPLIER_PEASANTS, 0.2);
  });

  it('multiplies the peasant bonus by the period', async () => {
    const { globals } = await bundle();
    const p = periods(globals);
    const result = collect({ collect: 100, unitCapacity: 5, unitsInside: 2 }, 3, p);
    assert.equal(result.amount, 240); // floor(120 * 2)
  });

  it('collects nothing when the building is over capacity', async () => {
    const { globals } = await bundle();
    const result = collect(
      { collect: 100, unitCapacity: 2, unitsInside: 3 },
      4,
      periods(globals),
    );
    assert.equal(result.amount, 0);
    assert.equal(result.hacked, true);
  });

  it('rejects a collect period that does not exist', async () => {
    const { globals } = await bundle();
    assert.throws(
      () => collect({ collect: 100, unitCapacity: 1, unitsInside: 0 }, 9, periods(globals)),
      RangeError,
    );
  });
});

describe('population', () => {
  const rules: PopulationRules = {
    startMaxPopulation: 20,
    maxPopulationCap: 175,
    maxPopulationPerLevel: 3,
  };

  it('starts at 20', async () => {
    const { globals } = await bundle();
    assert.equal(rules.startMaxPopulation, globals['START_MAX_POPULATION']);
    assert.equal(rules.maxPopulationCap, globals['MAX_POPULATION_CAP']);
  });

  it('counts the units on the map and the ones being trained', () => {
    const state = {
      grantedByBuildings: 0,
      unitsOnMap: 12,
      beingTrained: 3,
      additionalPopulation: 0,
      level: 1,
    };
    assert.equal(currentPopulation(state), 15);
  });

  it('caps the ceiling and adds the extra population', () => {
    const base = {
      grantedByBuildings: 0,
      unitsOnMap: 0,
      beingTrained: 0,
      additionalPopulation: 0,
      level: 1,
    };
    assert.equal(maxPopulation(base, rules), 20);
    // The building grant raises the ceiling, but the hard cap still applies.
    assert.equal(
      maxPopulation({ ...base, grantedByBuildings: 50 }, rules),
      70,
    );
    assert.equal(
      maxPopulation({ ...base, grantedByBuildings: 1000 }, rules),
      175,
    );
    // The extra population is added to the HARD CAP, not to the starting
    // value, so it only makes a difference once the buildings have granted
    // more than the starting 20.
    assert.equal(
      maxPopulation({ ...base, additionalPopulation: 10 }, rules),
      20,
    );
    assert.equal(
      maxPopulation({ ...base, grantedByBuildings: 200, additionalPopulation: 10 }, rules),
      185,
    );
  });

  it('refuses a unit that would exceed the ceiling', () => {
    const state = {
      grantedByBuildings: 0,
      unitsOnMap: 18,
      beingTrained: 0,
      additionalPopulation: 0,
      level: 1,
    };
    assert.equal(canPlaceUnit(state, rules, 1), true);
    assert.equal(canPlaceUnit(state, rules, 3), false);
  });
});

describe('energy', () => {
  const rules: EnergyRules = {
    max: 30,
    regenIntervalMs: 300_000,
    constructionCost: 1,
    assistCost: 1,
  };

  it('uses the shipped values', async () => {
    const { globals } = await bundle();
    assert.equal(rules.max, globals['ENERGY_MAX_REGULAR_VALUE']);
    assert.equal(rules.regenIntervalMs, globals['ENERGY_INCREASE_ENERGY_INTERVAL']);
    assert.equal(rules.constructionCost, globals['ENERGY_CONSTRUCTION_COST']);
    assert.equal(rules.assistCost, globals['ENERGY_ASSIST_QTY']);
  });

  it('regenerates one point every five minutes', () => {
    assert.equal(regenerateEnergy(10, 0, rules), 10);
    assert.equal(regenerateEnergy(10, 299_999, rules), 10);
    assert.equal(regenerateEnergy(10, 300_000, rules), 11);
    assert.equal(regenerateEnergy(10, 900_000, rules), 13);
  });

  it('never goes above the free maximum', () => {
    assert.equal(regenerateEnergy(29, 3_600_000, rules), 30);
    assert.equal(regenerateEnergy(30, 3_600_000, rules), 30);
  });
});

describe('the price tables', () => {
  it('gives the first four expansions away', async () => {
    const { expansionPrices } = await bundle();
    for (let owned = 0; owned < 4; owned++) {
      const price = expansionPrice(expansionPrices, owned);
      assert.ok(price);
      assert.equal(price.coins, 0);
      assert.equal(price.cash, 0);
    }
    const fifth = expansionPrice(expansionPrices, 4);
    assert.equal(fifth?.coins, 2500);
    assert.equal(fifth?.cash, 5);
  });

  it('prices a new town', async () => {
    const { townPrices } = await bundle();
    const first = townPrice(townPrices, 0);
    assert.equal(first?.coins, 100_000);
    assert.equal(first?.cash, 20);
    assert.equal(first?.level, 15);
    assert.equal(townPrice(townPrices, 9), null);
  });

  it('checks the level requirement', async () => {
    const { townPrices } = await bundle();
    const first = townPrice(townPrices, 0)!;
    assert.equal(meetsLevelRequirement(first, 14), false);
    assert.equal(meetsLevelRequirement(first, 15), true);
  });
});
