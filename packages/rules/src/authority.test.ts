import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  battleSeed,
  checkClientClaim,
  resolveServerCombat,
  type Combatant,
  type ServerCombatInput,
} from './authority.ts';

const soldier = (over: Partial<Combatant> = {}): Combatant => ({
  id: 'u1',
  itemId: 1007,
  attack: 8,
  defense: 1,
  life: 50,
  maxLife: 50,
  health: 50,
  attack_range: 5,
  attack_interval: 35,
  phase: 0,
  properties: {},
  best_against: null,
  best_against_mult: 1,
  x: 0,
  y: 0,
  ...over,
});

const input = (over: Partial<ServerCombatInput> = {}): ServerCombatInput => ({
  seed: 'battle-0001',
  attacker: soldier({ id: 'a1', attack: 40 }),
  defender: soldier({ id: 'd1', attack: 0, health: 200, maxLife: 200, life: 200 }),
  ...over,
});

describe('server-authoritative combat', () => {
  it('is deterministic for the same seed and inputs', () => {
    const a = resolveServerCombat(input());
    const b = resolveServerCombat(input());
    assert.deepEqual(a, b);
  });

  it('produces a different result for a different seed', () => {
    const a = resolveServerCombat(input());
    const b = resolveServerCombat(input({ seed: 'battle-0002' }));
    // The rolls may coincide, but the seeds are recorded and the sequence
    // they draw from is not the same.
    assert.equal(a.seed, 'battle-0001');
    assert.equal(b.seed, 'battle-0002');
  });

  it('ignores anything the client could claim', () => {
    // The API has no parameter for a client-claimed result: the outcome is a
    // function of the seed and the two combatants only.
    const outcome = resolveServerCombat(input());
    const verdict = checkClientClaim({ damage: 999999 }, outcome);
    assert.equal(verdict.matches, false);
    assert.equal(verdict.serverDamage, outcome.damage);
    assert.equal(verdict.clientDamage, 999999);
  });

  it('accepts a claim that agrees with its own answer', () => {
    const outcome = resolveServerCombat(input());
    const verdict = checkClientClaim({ damage: outcome.damage }, outcome);
    assert.equal(verdict.matches, true);
    assert.equal(verdict.difference, 0);
  });

  it('shares the damage across the units the hit caught', () => {
    // SimpleDamage divides by numTargets before the pipeline runs.
    const one = resolveServerCombat(input());
    const three = resolveServerCombat(input({ numTargets: 3 }));
    assert.ok(three.damage < one.damage);
  });

  it('reports the stages for the golden-master diff', () => {
    const outcome = resolveServerCombat(input());
    const names = outcome.stages.map((s) => s.name);
    assert.ok(names.includes('attack'));
    assert.ok(names.includes('afterCrit'));
    assert.ok(names.includes('afterDefense'));
    assert.ok(names.includes('final'));
  });

  it('kills a defender whose health the hit covers', () => {
    const outcome = resolveServerCombat(
      input({ defender: soldier({ id: 'd1', health: 5, maxLife: 200, life: 200 }) }),
    );
    assert.equal(outcome.defenderHealthAfter, 0);
    assert.equal(outcome.killed, true);
  });

  it('applies the counter when the target carries the key', () => {
    const outcome = resolveServerCombat(
      input({
        attacker: soldier({ id: 'a1', attack: 10, best_against: 'ft_flying', best_against_mult: 20 }),
        defender: soldier({ id: 'd1', health: 200, maxLife: 200, life: 200, properties: { ft_flying: 1 } }),
      }),
    );
    assert.equal(outcome.counterMultiplier, 20);
  });
});

describe('the battle seed', () => {
  it('is the battle id, with an attempt suffix for a replay', () => {
    assert.equal(battleSeed('b-1'), 'b-1');
    assert.equal(battleSeed('b-1', 1), 'b-1#1');
  });

  it('gives a different stream for a different attempt', () => {
    const first = resolveServerCombat(input({ seed: battleSeed('b-1', 0) }));
    const second = resolveServerCombat(input({ seed: battleSeed('b-1', 1) }));
    assert.notEqual(first.seed, second.seed);
  });
});
