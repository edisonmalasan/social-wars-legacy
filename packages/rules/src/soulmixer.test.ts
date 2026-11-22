import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Random } from './random.ts';
import {
  SOUL_MIXER_POWERUPS,
  SOUL_MIXER_HIGH_POWER,
  SOUL_MIXER_LEVEL20_GATE_MESSAGE,
  ID_UNIT_METALLIC_RED_DRAGON,
  ID_UNIT_SPARTAN_MECH,
  breedingOrderFromLife,
  applySoulMixerPowerup,
  buildSoulMixerCatalog,
  checkSoulMixerLevel20Gate,
  fuseWithPowerups,
  getUnitIndexByPower,
  mixUnits,
  soulMixerCashCost,
  soulMixerResultPower,
  soulMixerSpeedupCost,
  soulMixerTrainingTime,
  type SoulMixerItemData,
  type SoulMixerRandom,
} from './soulmixer.ts';

/** A random source with a fixed script, consuming one value per draw. */
function scripted(...values: number[]): SoulMixerRandom {
  let index = 0;
  return { next: () => values[index++ % values.length]! };
}

/** Powers 10, 20, ... 400, with the id equal to the power. */
function ladder(): ReturnType<typeof buildSoulMixerCatalog> {
  const items: SoulMixerItemData[] = Array.from({ length: 40 }, (_, index) => ({
    id: (index + 1) * 10,
    breeding_order: (index + 1) * 10,
  }));
  return buildSoulMixerCatalog(items);
}

describe('the soul mixer catalog', () => {
  it('keeps only positive breeding orders and sorts by ascending power', () => {
    const catalog = buildSoulMixerCatalog([
      { id: 3, breeding_order: 30 },
      { id: 1, breeding_order: 0 },
      { id: 4, breeding_order: '40' },
      { id: 2, breeding_order: -5 },
      { id: 5, breeding_order: 20 },
    ]);
    assert.deepEqual(catalog.candidates, [
      { id: 5, power: 20 },
      { id: 3, power: 30 },
      { id: 4, power: 40 },
    ]);
    assert.equal(catalog.maxPower, 40);
    assert.equal(catalog.powerById.get(3), 30);
    assert.equal(catalog.powerById.has(1), false);
  });

  it('derives breeding order and training time from life', () => {
    assert.equal(breedingOrderFromLife(100), 5);
    assert.equal(breedingOrderFromLife(4800), 240);
    assert.equal(breedingOrderFromLife(100000), 240);
    assert.equal(soulMixerTrainingTime(5), 10000);
    assert.equal(soulMixerTrainingTime(240), 480000);
  });
});

describe('the fusion power', () => {
  it('clamps to a minimum of 10', () => {
    // ceil(1 * 0.3 + 2 * 0.7) = 2, below the client's floor of 10.
    assert.equal(soulMixerResultPower(1, 2, 220, scripted(0)), 10);
  });

  it('increments when the roll lands exactly on the higher input', () => {
    // ceil(100 * 0.3 + 100 * 0.7) = 100, and the zero roll leaves it at 100.
    assert.equal(soulMixerResultPower(100, 100, 240, scripted(0)), 101);
  });

  it('redraws over [220, maxPower] above 220', () => {
    // 220 + 0 -> 220, equal to the higher input -> 221, then the redraw:
    // floor(0.5 * (240 - 220 + 1) + 220) = 230.
    assert.equal(soulMixerResultPower(220, 220, 240, scripted(0, 0.5)), 230);
    assert.equal(SOUL_MIXER_HIGH_POWER, 220);
  });

  it('pins the reference vector from the seeded PRNG', () => {
    assert.equal(soulMixerResultPower(100, 100, 240, new Random('fusion-1')), 112);
  });
});

describe('candidate selection', () => {
  it('takes the first non-excluded candidate at or above the power', () => {
    const { candidates } = ladder();
    assert.equal(getUnitIndexByPower(candidates, 35, new Set()), 3);
    assert.equal(getUnitIndexByPower(candidates, 35, new Set([40])), 4);
  });

  it('falls back to the last index when none qualifies', () => {
    const { candidates } = ladder();
    assert.equal(getUnitIndexByPower(candidates, 999, new Set()), 39);
    assert.equal(getUnitIndexByPower(candidates, 10, new Set(candidates.map((c) => c.id))), 39);
  });

  it('never returns an input or a previously produced result', () => {
    const catalog = ladder();
    // ceil(10 * 0.3 + 20 * 0.7) = 17, so an unfiltered pick would be 20.
    const first = mixUnits(catalog, 10, 20, scripted(0));
    assert.deepEqual(first, { index: 2, id: 30, power: 30 });
    const second = mixUnits(catalog, 10, 20, scripted(0), [30]);
    assert.deepEqual(second, { index: 3, id: 40, power: 40 });
  });

  it('pins the seeded mix and full power-up chain', () => {
    const catalog = ladder();
    assert.deepEqual(mixUnits(catalog, 10, 20, new Random('fusion-2')), {
      index: 2,
      id: 30,
      power: 30,
    });
    assert.deepEqual(mixUnits(catalog, 10, 20, new Random('fusion-2'), [30]), {
      index: 3,
      id: 40,
      power: 40,
    });
    assert.deepEqual(fuseWithPowerups(catalog, 10, 20, [0, 1, 2, 3, 4, 5], new Random('fusion-3')), {
      result: { index: 2, id: 30, power: 30 },
      powerups: [
        { index: 4, id: 50, power: 50 },
        { index: 7, id: 80, power: 80 },
        { index: 12, id: 130, power: 130 },
        { index: 21, id: 220, power: 220 },
        { index: 32, id: 330, power: 330 },
        { index: 39, id: 400, power: 400 },
      ],
      excludedIds: [10, 20, 30, 50, 80, 130, 220, 330, 400],
    });
  });
});

describe('power-ups', () => {
  it('has the six shipped cash costs and order increments', () => {
    assert.deepEqual(SOUL_MIXER_POWERUPS, [
      { cash_cost: 1, order_increment: 1 },
      { cash_cost: 2, order_increment: 2 },
      { cash_cost: 4, order_increment: 4 },
      { cash_cost: 8, order_increment: 8 },
      { cash_cost: 15, order_increment: 15 },
      { cash_cost: 20, order_increment: 20 },
    ]);
    assert.deepEqual([0, 1, 2, 3, 4, 5].map(soulMixerCashCost), [1, 2, 4, 8, 15, 20]);
    assert.equal(soulMixerCashCost(99), 20);
  });

  it('advances by every order increment below 220', () => {
    const catalog = ladder();
    const current = catalog.candidates.find((candidate) => candidate.id === 100)!;
    const picks = [0, 1, 2, 3, 4, 5].map((level) =>
      applySoulMixerPowerup(catalog, current, level, scripted(0)),
    );
    assert.deepEqual(picks.map((pick) => pick.index), [11, 12, 14, 18, 25, 30]);
    assert.deepEqual(picks.map((pick) => pick.id), [120, 130, 150, 190, 260, 310]);
  });

  it('redraws over [220, maxPower] at or above 220', () => {
    const catalog = ladder();
    const current = catalog.candidates.find((candidate) => candidate.id === 240)!;
    assert.deepEqual(applySoulMixerPowerup(catalog, current, 0, scripted(0)), {
      index: 21,
      id: 220,
      power: 220,
    });
    assert.deepEqual(applySoulMixerPowerup(catalog, current, 0, scripted(0.5)), {
      index: 30,
      id: 310,
      power: 310,
    });
  });

  it('skips the current unit and prior results', () => {
    const catalog = ladder();
    const current = catalog.candidates.find((candidate) => candidate.id === 100)!;
    // Without the extra exclusion the base index is 10 (power 110); with it,
    // the walk moves to 11 (power 120) before adding increment 1.
    assert.deepEqual(applySoulMixerPowerup(catalog, current, 0, scripted(0)), {
      index: 11,
      id: 120,
      power: 120,
    });
    assert.deepEqual(applySoulMixerPowerup(catalog, current, 0, scripted(0), [110]), {
      index: 12,
      id: 130,
      power: 130,
    });
  });
});

describe('the level-20 gate', () => {
  it('refuses either gated unit below level 20 with the client message', () => {
    for (const id of [ID_UNIT_METALLIC_RED_DRAGON, ID_UNIT_SPARTAN_MECH]) {
      assert.deepEqual(checkSoulMixerLevel20Gate(19, id, 100), {
        allowed: false,
        message: SOUL_MIXER_LEVEL20_GATE_MESSAGE,
      });
      assert.deepEqual(checkSoulMixerLevel20Gate(19, 100, id), {
        allowed: false,
        message: SOUL_MIXER_LEVEL20_GATE_MESSAGE,
      });
    }
    assert.equal(
      SOUL_MIXER_LEVEL20_GATE_MESSAGE,
      "Neither Spartan Mech or Red Metallic Dragon can't be mixed before you reach level 20",
    );
  });

  it('allows them at level 20 and allows ordinary units below it', () => {
    for (const id of [ID_UNIT_METALLIC_RED_DRAGON, ID_UNIT_SPARTAN_MECH]) {
      assert.deepEqual(checkSoulMixerLevel20Gate(20, id, 100), { allowed: true, message: null });
    }
    assert.deepEqual(checkSoulMixerLevel20Gate(19, 100, 200), { allowed: true, message: null });
  });
});

describe('speed-up', () => {
  it('charges ceil of the remaining hours, never negative', () => {
    assert.equal(soulMixerSpeedupCost(10000, 0), 3);
    assert.equal(soulMixerSpeedupCost(10000, 1), 3);
    assert.equal(soulMixerSpeedupCost(10000, 6400), 1);
    assert.equal(soulMixerSpeedupCost(10000, 10000), 0);
    assert.equal(soulMixerSpeedupCost(10000, 12000), 0);
  });
});
