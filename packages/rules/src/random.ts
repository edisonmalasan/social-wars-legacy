/**
 * A deterministic pseudo-random number generator.
 *
 * The original client used `Math.random()`, so its battles were never
 * reproducible. A server-authoritative clone has to be reproducible, or it
 * cannot re-simulate a battle and claim the client's result was wrong.
 *
 * The generator is a 128-bit xorshift (xoshiro128**), seeded from a string
 * so a battle seed can be exchanged as text.
 *
 * Reference: the original client also ships a Park-Miller LCG in
 * `scripts/utils/RandomGenerator.as`, but it is used only for shuffles. Combat
 * used raw `Math.random()`, so there is no original behaviour to match here —
 * only a requirement to be deterministic.
 */

/** The 128-bit state of a xoshiro128** generator. */
export class Random {
  private s0: number;
  private s1: number;
  private s2: number;
  private s3: number;

  constructor(seed: number | string) {
    const numeric = typeof seed === 'number' ? seed >>> 0 : hashSeed(seed);
    // SplitMix32 to expand a single seed word into four state words.
    let x = numeric;
    const next = (): number => {
      x = (x + 0x9e3779b9) >>> 0;
      let z = x;
      z = Math.imul(z ^ (z >>> 16), 0x21f0aaad) >>> 0;
      z = Math.imul(z ^ (z >>> 15), 0x735a2d97) >>> 0;
      return (z ^ (z >>> 15)) >>> 0;
    };
    this.s0 = next();
    this.s1 = next();
    this.s2 = next();
    this.s3 = next();
  }

  /** The next value in [0, 1). */
  next(): number {
    const result = (Math.imul(this.s1, 5) >>> 0);
    const rot = (((result << 7) | (result >>> 25)) >>> 0);
    const out = Math.imul(rot, 9) >>> 0;

    const t = (this.s1 << 9) >>> 0;
    this.s2 = (this.s2 ^ this.s0) >>> 0;
    this.s3 = (this.s3 ^ this.s1) >>> 0;
    this.s1 = (this.s1 ^ this.s2) >>> 0;
    this.s0 = (this.s0 ^ this.s3) >>> 0;
    this.s2 = (this.s2 ^ t) >>> 0;
    this.s3 = (((this.s3 << 11) | (this.s3 >>> 21)) >>> 0);

    return out / 4294967296;
  }

  /** An integer in [min, max]. */
  int(min: number, max: number): number {
    if (max < min) throw new RangeError('max < min');
    return min + Math.floor(this.next() * (max - min + 1));
  }

  /** A float in [min, max). */
  float(min: number, max: number): number {
    return min + this.next() * (max - min);
  }

  /** True with probability p. */
  chance(p: number): boolean {
    return this.next() < p;
  }

  /** A uniformly chosen element. */
  pick<T>(items: readonly T[]): T {
    if (items.length === 0) throw new RangeError('cannot pick from an empty array');
    return items[this.int(0, items.length - 1)]!;
  }

  /** A shuffled copy. */
  shuffle<T>(items: readonly T[]): T[] {
    const out = items.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = this.int(0, i);
      const tmp = out[i]!;
      out[i] = out[j]!;
      out[j] = tmp;
    }
    return out;
  }
}

/** FNV-1a, used to turn a seed string into a 32-bit seed word. */
export function hashSeed(seed: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < seed.length; i++) {
    hash ^= seed.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}
