import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { Random } from './random.ts';
import {
  resolveDamage,
  effectiveRange,
  scoreTarget,
  selectTarget,
  AGGRO_RANGE,
  SUBCATFUNC_BUILDING_TOWNHALL,
} from './combat.ts';
import { applyDelta, describeResources } from './resources.ts';
import { rotateDartsSchedule } from './darts.ts';

describe('Random', () => {
  it('is deterministic for a given seed', () => {
    const a = new Random('battle-seed-1');
    const b = new Random('battle-seed-1');
    const left = Array.from({ length: 32 }, () => a.next());
    const right = Array.from({ length: 32 }, () => b.next());
    assert.deepEqual(left, right);
  });

  it('produces different streams for different seeds', () => {
    const a = Array.from({ length: 16 }, ((r) => () => r.next())(new Random('a')));
    const b = Array.from({ length: 16 }, ((r) => () => r.next())(new Random('b')));
    assert.notDeepEqual(a, b);
  });

  it('stays inside [0, 1)', () => {
    const random = new Random(12345);
    for (let i = 0; i < 5_000; i++) {
      const value = random.next();
      assert.ok(value >= 0 && value < 1, `value out of range: ${value}`);
    }
  });

  it('shuffles deterministically', () => {
    const items = [1, 2, 3, 4, 5, 6, 7, 8];
    assert.deepEqual(new Random('s').shuffle(items), new Random('s').shuffle(items));
  });
});

describe('the damage pipeline', () => {
  const soldier = {
    attack: 8,
    defense: 1,
    life: 50,
    attack_range: 5,
    attack_interval: 35,
    best_against: null,
    best_against_mult: 1,
    properties: {} as Record<string, unknown>,
  };

  const antiAircraft = {
    ...soldier,
    attack: 20,
    best_against: 'ft_flying',
    best_against_mult: 20,
  };

  const flyer = { ...soldier, properties: { ft_flying: 1 } };

  it('never deals less than one damage', () => {
    const result = resolveDamage(
      { ...soldier, attack: 0 },
      { ...soldier, defense: 999 },
      new Random('weak'),
    );
    assert.equal(result.damage, 1);
  });

  it('applies the counter multiplier only when the target carries the key', () => {
    const random = new Random('counter');
    const countered = resolveDamage(antiAircraft, flyer, random, {}, { variance: 0 });
    const uncountered = resolveDamage(antiAircraft, soldier, random, {}, { variance: 0 });
    assert.equal(countered.counterMultiplier, 20);
    assert.equal(uncountered.counterMultiplier, 1);
    assert.ok(countered.damage > uncountered.damage);
  });

  it('reports every stage in order', () => {
    const result = resolveDamage(soldier, soldier, new Random('stages'), {}, { variance: 0 });
    assert.deepEqual(
      result.stages.map((s) => s.name),
      ['attack', 'afterCounter', 'afterCrit', 'afterDefense', 'afterRound', 'final'],
    );
  });

  it('is reproducible for the same seed and variance', () => {
    const a = resolveDamage(soldier, flyer, new Random('r'), {}, { variance: 2 });
    const b = resolveDamage(soldier, flyer, new Random('r'), {}, { variance: 2 });
    assert.equal(a.damage, b.damage);
    assert.equal(a.crit, b.crit);
  });
});

describe('range and targeting', () => {
  it('gives units a widened range and buildings an exact one', () => {
    const stats = { attack_range: 5 };
    assert.equal(effectiveRange(stats, 20, 'unit'), 15);
    assert.equal(effectiveRange(stats, 20, 'building'), 5);
    assert.equal(effectiveRange(stats, 4, 'unit'), 5);
  });

  it('scores a target as 1000 minus its distance, plus one bonus', () => {
    // Ported from IsoEngine.getElementScore. The bonuses are an else-if
    // chain, so a building gets AT MOST ONE of them.
    assert.equal(scoreTarget({ kind: 'unit', distance: 10 }).score, 990 + 150);
    assert.equal(
      scoreTarget({ kind: 'building', distance: 10, subcatFunctional: SUBCATFUNC_BUILDING_TOWNHALL })
        .score,
      990 + 100,
    );
    assert.equal(scoreTarget({ kind: 'building', distance: 10, collect: 5 }).score, 990 + 75);
    assert.equal(scoreTarget({ kind: 'building', distance: 10, uiAttack: 3 }).score, 990 + 50);
  });

  it('marks a target that is none of those as untargetable', () => {
    const scored = scoreTarget({ kind: 'building', distance: 10 });
    assert.equal(scored.score, -1);
  });

  it('treats a passive building as further away', () => {
    const passive = scoreTarget({ kind: 'building', distance: 10, uiAttack: 3, passive: true });
    const active = scoreTarget({ kind: 'building', distance: 10, uiAttack: 3 });
    assert.equal(passive.effectiveDistance, 10 + AGGRO_RANGE);
    assert.equal(active.effectiveDistance, 10);
    assert.ok(passive.score < active.score);
  });

  it('prefers the highest score, and the closest on a tie', () => {
    const unit = { kind: 'unit' as const, distance: 40, handle: 'unit' };
    const hall = {
      kind: 'building' as const,
      distance: 10,
      subcatFunctional: SUBCATFUNC_BUILDING_TOWNHALL,
      handle: 'hall',
    };
    // The unit scores 1000-40+150 = 1110; the hall 1000-10+100 = 1090.
    assert.equal(selectTarget([hall, unit])?.handle, 'unit');

    const near = { kind: 'unit' as const, distance: 20, handle: 'near' };
    const far = { kind: 'unit' as const, distance: 25, handle: 'far' };
    assert.equal(selectTarget([far, near])?.handle, 'near');
  });

  it('skips untargetable candidates', () => {
    const wall = { kind: 'building' as const, distance: 1, handle: 'wall' };
    const unit = { kind: 'unit' as const, distance: 90, handle: 'unit' };
    assert.equal(selectTarget([wall, unit])?.handle, 'unit');
    assert.equal(selectTarget([wall]), null);
  });
});

describe('resources', () => {
  it('clamps at zero', () => {
    assert.deepEqual(
      applyDelta([0, 0, 100, 0, 0, 0, 0, 0], [0, 0, -500, 0, 0, 0, 0, 0]),
      [0, 0, 0, 0, 0, 0, 0, 0],
    );
  });

  it('describes only the non-zero slots', () => {
    assert.equal(describeResources([0, 5, -10, 0, 0, 0, 0, 0]), 'xp +5, gold -10');
  });
});

describe('the darts schedule', () => {
  const games = [
    { id: 1, start_date: '2012-06-11 00:00:00', extra_item: 1, items: [1] },
    { id: 2, start_date: '2012-06-18 00:00:00', extra_item: 2, items: [2] },
  ];

  it('rotates onto Mondays', () => {
    const rotated = rotateDartsSchedule(games, new Date(2026, 9, 21));
    for (const game of rotated) {
      const date = new Date(game.start_date.replace(' ', 'T'));
      assert.equal(date.getDay(), 1, `${game.start_date} is not a Monday`);
    }
  });

  it('keeps the games seven days apart', () => {
    const rotated = rotateDartsSchedule(games, new Date(2026, 9, 21));
    const first = new Date(rotated[0]!.start_date.replace(' ', 'T')).getTime();
    const second = new Date(rotated[1]!.start_date.replace(' ', 'T')).getTime();
    assert.equal(second - first, 604_800_000);
  });
});
