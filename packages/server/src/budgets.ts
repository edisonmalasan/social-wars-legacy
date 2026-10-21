/**
 * The performance budgets.
 *
 * A budget is a number the project holds itself to, and it is **written
 * down** so that "fast enough" is a decision rather than an impression.
 *
 * The budgets are stated at the **ninety-fifth percentile**, because a
 * budget on the mean says nothing about the players who are having a bad
 * time. And they are stated in terms of what the player experiences:
 *
 * | Budget | What it is | The floor |
 * |---|---|---|
 * | `request_latency_p95_ms` | how long a request takes | 200 ms |
 * | `simulation_tick_p95_ms` | how long the rules engine takes | 50 ms |
 * | `command_throughput` | how many commands a second the server applies | 50 |
 * | `error_rate` | the failed requests over all the requests | 0.01 |
 *
 * The **simulation tick** is the one that matters: it is the rules
 * engine, and the engine is the game. A request that takes a second
 * because the simulation took a second is a request the player feels.
 *
 * These are the floors for a **modest** machine: a preservation server
 * with a handful of players, not a fleet. They are not a benchmark of
 * the hardware, they are a promise the code keeps.
 */

/** A budget. */
export interface Budget {
  /** Its name. */
  name: string;
  /** What it measures. */
  measurement: string;
  /** The floor, or the ceiling. */
  limit: number;
  /** Which way the comparison goes. */
  comparison: 'above' | 'below';
  /** The unit the limit is in. */
  unit: 'ms' | 'ratio' | 'per_second';
  /** What it means when it is broken. */
  why: string;
}

/** The budgets. */
export const BUDGETS: readonly Budget[] = [
  {
    name: 'request_latency_p95_ms',
    measurement: 'latency_p95_ms',
    limit: 200,
    comparison: 'below',
    unit: 'ms',
    why: 'A request the player waits for is a request they feel.',
  },
  {
    name: 'simulation_tick_p95_ms',
    measurement: 'tick_p95_ms',
    limit: 50,
    comparison: 'below',
    unit: 'ms',
    why: 'The rules engine IS the game. A slow simulation is a slow game.',
  },
  {
    name: 'command_throughput',
    measurement: 'command_rate',
    limit: 50,
    comparison: 'above',
    unit: 'per_second',
    why: 'Below this the server cannot keep up with the players it has.',
  },
  {
    name: 'error_rate',
    measurement: 'error_rate',
    limit: 0.01,
    comparison: 'below',
    unit: 'ratio',
    why: 'One request in a hundred failing is already too many.',
  },
];

/** A budget that was broken. */
export interface BrokenBudget {
  /** The budget's name. */
  name: string;
  /** What it measured. */
  value: number;
  /** The limit it broke. */
  limit: number;
  /** What it means. */
  why: string;
}

/**
 * The budgets that were broken.
 *
 * A budget with the comparison `below` is a **ceiling**: it is broken
 * when the value is **over** the limit. A budget with the comparison
 * `above` is a **floor**: it is broken when the value is **under** it.
 *
 * @param measurements the measurements, by name
 */
export function brokenBudgets(
  measurements: Readonly<Record<string, number>>,
  budgets: readonly Budget[] = BUDGETS,
): BrokenBudget[] {
  const broken: BrokenBudget[] = [];
  for (const budget of budgets) {
    const value = measurements[budget.measurement];
    if (value === undefined) continue;
    const isBroken =
      budget.comparison === 'above' ? value < budget.limit : value > budget.limit;
    if (!isBroken) continue;
    broken.push({
      name: budget.name,
      value,
      limit: budget.limit,
      why: budget.why,
    });
  }
  return broken;
}
