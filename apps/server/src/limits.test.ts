import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { DEFAULT_LIMITS, RateLimiter } from './limits.ts';

describe('the rate limiter', () => {
  it('allows a request up to the limit', () => {
    const limiter = new RateLimiter({ ...DEFAULT_LIMITS, requestsPerWindow: 3 });
    assert.equal(limiter.check('a', 1_000), 0);
    assert.equal(limiter.check('a', 1_001), 0);
    assert.equal(limiter.check('a', 1_002), 0);
  });

  it('refuses the one after it', () => {
    const limiter = new RateLimiter({ ...DEFAULT_LIMITS, requestsPerWindow: 3 });
    limiter.check('a', 1_000);
    limiter.check('a', 1_001);
    limiter.check('a', 1_002);
    const wait = limiter.check('a', 1_003);
    assert.ok(wait > 0, 'the fourth request was allowed');
  });

  it('says how long to wait', () => {
    const limiter = new RateLimiter({
      ...DEFAULT_LIMITS,
      requestsPerWindow: 1,
      windowSeconds: 60,
    });
    limiter.check('a', 1_000);
    // The window rolls over in 60 seconds, so the caller waits the rest.
    assert.equal(limiter.check('a', 1_010), 50);
  });

  it('counts each client separately', () => {
    const limiter = new RateLimiter({ ...DEFAULT_LIMITS, requestsPerWindow: 1 });
    assert.equal(limiter.check('a', 1_000), 0);
    // A different client is not affected by the first one's requests.
    assert.equal(limiter.check('b', 1_000), 0);
    assert.ok(limiter.check('a', 1_001) > 0);
  });

  it('resets when the window rolls over', () => {
    const limiter = new RateLimiter({
      ...DEFAULT_LIMITS,
      requestsPerWindow: 1,
      windowSeconds: 60,
    });
    limiter.check('a', 1_000);
    assert.ok(limiter.check('a', 1_001) > 0);
    // A minute later the window is over.
    assert.equal(limiter.check('a', 1_060), 0);
  });

  it('forgets a client on request', () => {
    const limiter = new RateLimiter({ ...DEFAULT_LIMITS, requestsPerWindow: 1 });
    limiter.check('a', 1_000);
    assert.equal(limiter.size, 1);
    limiter.forget('a');
    assert.equal(limiter.size, 0);
    assert.equal(limiter.check('a', 1_001), 0);
  });
});

describe('the limits', () => {
  it('cap the body', () => {
    assert.ok(DEFAULT_LIMITS.maxBodyBytes > 0);
  });

  it('cap the number of commands in a batch', () => {
    assert.ok(DEFAULT_LIMITS.maxCommandsPerBatch > 0);
  });

  it('bound how long a command may take', () => {
    assert.ok(DEFAULT_LIMITS.commandTimeoutMs > 0);
  });

  it('allow a reasonable number of requests a minute', () => {
    assert.ok(DEFAULT_LIMITS.requestsPerWindow > 0);
    assert.ok(DEFAULT_LIMITS.windowSeconds > 0);
  });
});
