/**
 * Resource arithmetic.
 *
 * The order of the eight slots is load-bearing and was verified live against a
 * real client session (re/docs/06-LIVE-SESSION-PROTOCOL.md). It is defined
 * once, in `@swl/protocol`, and re-exported here so the rules engine has a
 * single source of truth.
 */

export {
  RESOURCE_ORDER,
  RESOURCE_INDEX,
  ZERO_RESOURCES,
  readResource,
  addResources,
  type ResourceName,
  type ResourceVector,
} from '@swl/protocol';

import {
  RESOURCE_ORDER,
  type ResourceVector,
} from '@swl/protocol';

/**
 * Apply a delta and clamp the result at zero.
 *
 * The upstream server does exactly this and nothing else: `max(x + d, 0)`. It has
 * no upper bound, which is why a client could grant itself a billion gold.
 * The new server must bound the *cost* instead of trusting the delta; this
 * helper is the shape of the operation, not the policy.
 */
export function applyDelta(
  current: ResourceVector,
  delta: ResourceVector,
): ResourceVector {
  return current.map((value, index) => Math.max(0, value + delta[index]!)) as unknown as ResourceVector;
}

/** A human-readable rendering of a resource vector, for logs and the UI. */
export function describeResources(vector: ResourceVector): string {
  return RESOURCE_ORDER.map((name, index) => {
    const value = vector[index]!;
    return value === 0 ? null : `${name} ${value > 0 ? '+' : ''}${value}`;
  })
    .filter((part): part is string => part !== null)
    .join(', ');
}
