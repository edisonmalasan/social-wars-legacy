import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  PLAIN_PERKS,
  PREMIUM_PERKS,
  SECONDS_PER_DAY,
  isPremiumActive,
  perksFor,
  premiumDays,
  premiumExpiry,
  secondsUntilPremiumExpiry,
  type PremiumPackage,
} from './premium.ts';

const PACKAGES: PremiumPackage[] = [
  { price: 800, time: 360 },
  { price: 450, time: 180 },
  { price: 80, time: 30 },
  { price: 40, time: 7 },
  { price: 20, time: 3 },
  { price: 8, time: 1 },
];

describe('the premium packages', () => {
  it('grant the days the content says', () => {
    assert.equal(premiumDays(PACKAGES, 0), 360);
    assert.equal(premiumDays(PACKAGES, 1), 180);
    assert.equal(premiumDays(PACKAGES, 5), 1);
  });

  it('refuse a package that does not exist', () => {
    assert.throws(() => premiumDays(PACKAGES, 9), RangeError);
  });
});

describe('buying the premium', () => {
  it('starts it fresh when the premium has lapsed', () => {
    const now = 1_700_000_000;
    const expiry = premiumExpiry(PACKAGES, 5, now, 0);
    assert.equal(expiry, now + 1 * SECONDS_PER_DAY);
  });

  it('starts it fresh when the premium has lapsed', () => {
    const now = 1_700_000_000;
    const lapsed = now - 100;
    const expiry = premiumExpiry(PACKAGES, 5, now, lapsed);
    assert.equal(expiry, now + 1 * SECONDS_PER_DAY);
  });

  it('EXTENDS it when the premium is still running', () => {
    const now = 1_700_000_000;
    const running = now + 1000;
    const expiry = premiumExpiry(PACKAGES, 3, now, running);
    // Seven more days on top of what was left.
    assert.equal(expiry, running + 7 * SECONDS_PER_DAY);
  });

  it('does not lose the remaining time when it extends', () => {
    const now = 1_700_000_000;
    const running = now + 1000;
    const expiry = premiumExpiry(PACKAGES, 3, now, running);
    assert.ok(expiry > running);
  });
});

describe('the premium being active', () => {
  it('is a comparison against the clock', () => {
    assert.equal(isPremiumActive(100, 99), true);
    assert.equal(isPremiumActive(100, 100), false);
    assert.equal(isPremiumActive(0, 1_700_000_000), false);
  });

  it('counts down the seconds left', () => {
    assert.equal(secondsUntilPremiumExpiry(100, 40), 60);
    assert.equal(secondsUntilPremiumExpiry(100, 200), 0);
  });
});

describe('the perks', () => {
  it('are the premium ones while it runs', () => {
    assert.deepEqual(perksFor(100, 50), PREMIUM_PERKS);
    assert.equal(PREMIUM_PERKS.attacksADay, 3);
  });

  it('are the plain ones once it has lapsed', () => {
    assert.deepEqual(perksFor(100, 200), PLAIN_PERKS);
    assert.equal(PLAIN_PERKS.attacksADay, 1);
  });
});
