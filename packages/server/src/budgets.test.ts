import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { BUDGETS, brokenBudgets } from './budgets.ts';

describe('the performance budgets', () => {
  it('are written down', () => {
    assert.ok(BUDGETS.length > 0);
    for (const budget of BUDGETS) {
      assert.ok(budget.name.length > 0);
      assert.ok(budget.measurement.length > 0);
      assert.equal(typeof budget.limit, 'number');
      assert.ok(['above', 'below'].includes(budget.comparison));
      assert.ok(budget.why.length > 10, `${budget.name} says nothing`);
    }
  });

  it('cover the things a player feels', () => {
    const names = BUDGETS.map((budget) => budget.name);
    assert.ok(names.includes('request_latency_p95_ms'));
    assert.ok(names.includes('simulation_tick_p95_ms'));
    assert.ok(names.includes('command_throughput'));
    assert.ok(names.includes('error_rate'));
    assert.ok(names.includes('input_to_render_p95_ms'));
  });

  it('budget the input-to-render latency', () => {
    const budget = BUDGETS.find((entry) => entry.name === 'input_to_render_p95_ms');
    assert.ok(budget);
    assert.equal(budget!.measurement, 'input_to_render_p95_ms');
    assert.equal(budget!.limit, 250);
    assert.equal(budget!.comparison, 'below');
  });

  it('are not broken by a healthy server', () => {
    const broken = brokenBudgets({
      latency_p95_ms: 12,
      tick_p95_ms: 4,
      command_rate: 200,
      error_rate: 0,
    });
    assert.deepEqual(broken, []);
  });

  it('are broken by a slow request', () => {
    const broken = brokenBudgets({ latency_p95_ms: 900 });
    assert.equal(broken.length, 1);
    assert.equal(broken[0]!.name, 'request_latency_p95_ms');
    assert.equal(broken[0]!.value, 900);
  });

  it('are broken by a slow simulation', () => {
    const broken = brokenBudgets({ tick_p95_ms: 200 });
    assert.equal(broken[0]!.name, 'simulation_tick_p95_ms');
  });

  it('are broken by a slow server', () => {
    // The throughput is a **floor**, so it is broken by being too low.
    const broken = brokenBudgets({ command_rate: 2 });
    assert.equal(broken[0]!.name, 'command_throughput');
  });

  it('are broken by the errors', () => {
    const broken = brokenBudgets({ error_rate: 0.2 });
    assert.equal(broken[0]!.name, 'error_rate');
  });

  it('breaks on a slow input-to-render', () => {
    const broken = brokenBudgets({ input_to_render_p95_ms: 900 });
    assert.equal(broken[0]!.name, 'input_to_render_p95_ms');
    assert.equal(broken[0]!.limit, 250);
  });

  it('ignore a measurement they do not watch', () => {
    assert.deepEqual(brokenBudgets({ something_else: 9999 }), []);
  });
});
