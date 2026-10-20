/**
 * A tiny assertion helper.
 *
 * The rules package is the **shared, platform-neutral core**: the server
 * runs it, and so would a browser, and so would a worker. `node:assert`
 * would tie it to Node, for no benefit — the checks it makes are five
 * comparisons and a deep comparison, and all they have to do is throw.
 *
 * So the checks are made here, with no dependency at all.
 */

/** The error a failed check throws. */
export class AssertionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AssertionError';
  }
}

/** Whether two values are deeply equal. */
export function deepEqual(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return false;
  if (typeof a !== 'object') return false;

  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length !== b.length) return false;
    return a.every((item, index) => deepEqual(item, b[index]));
  }

  if (a instanceof Date || b instanceof Date) {
    if (!(a instanceof Date) || !(b instanceof Date)) return false;
    return a.getTime() === b.getTime();
  }

  if (a instanceof Map || b instanceof Map) {
    if (!(a instanceof Map) || !(b instanceof Map)) return false;
    if (a.size !== b.size) return false;
    for (const [key, value] of a) {
      if (!b.has(key) || !deepEqual(value, b.get(key))) return false;
    }
    return true;
  }

  if (a instanceof Set || b instanceof Set) {
    if (!(a instanceof Set) || !(b instanceof Set)) return false;
    if (a.size !== b.size) return false;
    for (const value of a) {
      if (!b.has(value)) return false;
    }
    return true;
  }

  const aKeys = Object.keys(a as Record<string, unknown>);
  const bKeys = Object.keys(b as Record<string, unknown>);
  if (aKeys.length !== bKeys.length) return false;
  return aKeys.every(
    (key) =>
      Object.prototype.hasOwnProperty.call(b, key) &&
      deepEqual(
        (a as Record<string, unknown>)[key],
        (b as Record<string, unknown>)[key],
      ),
  );
}

/** A short description of a value, for the failure message. */
function describe(value: unknown): string {
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'bigint') return `${value}n`;
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value) ?? Object.prototype.toString.call(value);
    } catch {
      return Object.prototype.toString.call(value);
    }
  }
  return String(value);
}

/** The checks. */
export const assert = {
  /**
   * The value must be truthy.
   *
   * It is not an assertion *function* — it does not narrow the type — so
   * that it can be a method on an object literal.
   */
  ok(value: unknown, message?: string): void {
    if (!value) {
      throw new AssertionError(message ?? `expected a truthy value, got ${describe(value)}`);
    }
  },

  /** The two values must be equal. */
  equal<T>(actual: T, expected: T, message?: string): void {
    if (!Object.is(actual, expected)) {
      throw new AssertionError(
        message ?? `expected ${describe(actual)} to equal ${describe(expected)}`,
      );
    }
  },

  /** The two values must not be equal. */
  notEqual<T>(actual: T, expected: T, message?: string): void {
    if (Object.is(actual, expected)) {
      throw new AssertionError(
        message ?? `expected ${describe(actual)} not to equal ${describe(expected)}`,
      );
    }
  },

  /** The two values must be deeply equal. */
  deepEqual<T>(actual: T, expected: T, message?: string): void {
    if (!deepEqual(actual, expected)) {
      throw new AssertionError(
        message ?? `expected ${describe(actual)} to deeply equal ${describe(expected)}`,
      );
    }
  },

  /** The two values must not be deeply equal. */
  notDeepEqual<T>(actual: T, expected: T, message?: string): void {
    if (deepEqual(actual, expected)) {
      throw new AssertionError(
        message ?? `expected ${describe(actual)} not to deeply equal ${describe(expected)}`,
      );
    }
  },
};
