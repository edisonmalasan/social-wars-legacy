/**
 * The rules engine: a pure, deterministic simulation.
 *
 * "Pure" means: no I/O, no wall clock, no unseeded randomness. Every function
 * takes the world state and a seed, and returns a new state. That is what makes
 * the golden-master differential test against the original Flash client
 * possible, and it is what lets the server re-simulate a battle the client
 * claims it won.
 */

export * from './random.js';
export * from './resources.js';
export * from './darts.js';
export * from './combat.js';
export * from './counters.js';
