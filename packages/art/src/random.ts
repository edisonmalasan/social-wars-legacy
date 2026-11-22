/**
 * A seeded generator built only from 32-bit integer operations.
 *
 * Every operation here is fixed by the language specification, so the same
 * seed and the same stream of calls give the same numbers on every machine.
 * There is no wall clock and no platform randomness anywhere in this package.
 */

export interface Random {
  /** The next number in [0, 1). */
  next(): number;
  /** The next integer in [min, max], both inclusive. */
  int(min: number, max: number): number;
}

/** mulberry32: a small, fully specified 32-bit generator. */
export function makeRandom(seed: number): Random {
  let state = seed >>> 0;
  const next = (): number => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    next,
    int(min: number, max: number): number {
      return min + Math.floor(next() * (max - min + 1));
    },
  };
}

/** A stable 32-bit seed from a name, so each motif has its own stream. */
export function seedFor(name: string): number {
  let hash = 2166136261; // FNV-1a, 32-bit
  for (let i = 0; i < name.length; i += 1) {
    hash ^= name.charCodeAt(i);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}
