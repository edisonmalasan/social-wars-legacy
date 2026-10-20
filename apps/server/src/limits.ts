/**
 * The request limits.
 *
 * Every endpoint in the server needs a request-size limit, a rate limit and a
 * timeout (roadmap F4). They are collected here so the numbers are stated
 * once and can be read in one place.
 */

/** The default limits. */
export interface Limits {
  /** The largest request body the server will read, in bytes. */
  maxBodyBytes: number;
  /** How many requests one player may make in a window. */
  requestsPerWindow: number;
  /** The window the rate limit is measured over, in seconds. */
  windowSeconds: number;
  /** How long a command may take, in milliseconds. */
  commandTimeoutMs: number;
  /** The largest number of commands one batch may carry. */
  maxCommandsPerBatch: number;
}

/** The limits the server runs with. */
export const DEFAULT_LIMITS: Limits = {
  // The client's biggest legitimate batch is a few hundred commands of a few
  // hundred bytes each. A megabyte is generous, and anything larger is a
  // mistake or an attack.
  maxBodyBytes: 1024 * 1024,
  // The client batches its commands, so a normal player makes far fewer
  // requests than this. It is a ceiling, not a target.
  requestsPerWindow: 120,
  windowSeconds: 60,
  // A command batch is pure computation over a small world state. A second is
  // already absurdly generous.
  commandTimeoutMs: 5_000,
  maxCommandsPerBatch: 512,
};

/** The reason a request was refused. */
export type LimitViolation =
  | { kind: 'body-too-large'; limit: number }
  | { kind: 'too-many-commands'; limit: number }
  | { kind: 'rate-limited'; limit: number; retryAfterSeconds: number };

/**
 * A rate limiter.
 *
 * A simple fixed window: the count resets when the window rolls over. It is
 * not the most precise limiter, but it is exact enough to stop a runaway
 * client and it needs no background timer.
 */
export class RateLimiter {
  private readonly hits = new Map<string, { count: number; windowStart: number }>();
  private readonly limits: Limits;

  constructor(limits: Limits = DEFAULT_LIMITS) {
    this.limits = limits;
  }

  /**
   * Record a request and say whether it is allowed.
   *
   * Returns the number of seconds the caller should wait, or 0 when the
   * request is allowed.
   */
  check(key: string, now: number): number {
    const entry = this.hits.get(key);
    if (!entry || now - entry.windowStart >= this.limits.windowSeconds) {
      this.hits.set(key, { count: 1, windowStart: now });
      return 0;
    }
    entry.count += 1;
    if (entry.count > this.limits.requestsPerWindow) {
      const elapsed = now - entry.windowStart;
      return Math.max(1, Math.ceil(this.limits.windowSeconds - elapsed));
    }
    return 0;
  }

  /** Forget a key. */
  forget(key: string): void {
    this.hits.delete(key);
  }

  /** How many keys are being tracked. */
  get size(): number {
    return this.hits.size;
  }
}

/**
 * Parse a form-encoded body into fields.
 *
 * The legacy endpoints are `application/x-www-form-urlencoded`. The native
 * API is JSON. Both are handled by the router, so the parser here is only
 * for the form case.
 */
export function parseForm(body: string): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const pair of body.split('&')) {
    if (pair === '') continue;
    const at = pair.indexOf('=');
    const rawKey = at < 0 ? pair : pair.slice(0, at);
    const rawValue = at < 0 ? '' : pair.slice(at + 1);
    try {
      fields[decodeURIComponent(rawKey.replace(/\+/g, ' '))] = decodeURIComponent(
        rawValue.replace(/\+/g, ' '),
      );
    } catch {
      // A malformed escape is not worth a 500; keep the raw text.
      fields[rawKey] = rawValue;
    }
  }
  return fields;
}
