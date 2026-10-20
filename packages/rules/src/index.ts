/**
 * The rules engine: a pure, deterministic simulation.
 *
 * "Pure" means: no I/O, no wall clock, no unseeded randomness. Every function
 * takes the world state and a seed, and returns a new state. That is what makes
 * the golden-master differential test against the original Flash client
 * possible, and it is what lets the server re-simulate a battle the client
 * claims it won.
 */

export * from './random.ts';
export * from './resources.ts';
export * from './darts.ts';
export * from './combat.ts';
export * from './counters.ts';
export * from './economy.ts';
export * from './market.ts';
export * from './bonuses.ts';
export * from './building.ts';
export * from './damage.ts';
export * from './specialattacks.ts';
export * from './authority.ts';
export * from './goals.ts';
export * from './commandcost.ts';
export * from './quest.ts';
export * from './cheatbattery.ts';
