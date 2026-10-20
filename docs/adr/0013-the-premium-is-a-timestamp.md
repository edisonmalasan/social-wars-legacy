# 13. The premium is a timestamp the server owns

**Status:** accepted

## Context

The premium account is the private state's `timeStampEndPremium`. It is
active while the server's clock is before it.

## Decision

The server owns it. Buying while the premium is still running
**extends** it, and buying after it has lapsed **starts it fresh** — the
upstream's rule, and the client's.

The perks are the client's: three attacks a day instead of one, and a
share of the rewards in cash.

## Alternatives

- **A boolean flag.** Then the expiry has to be computed somewhere else,
  and the two would disagree.
- **A server-side entitlement service.** The premium is in the save,
  and the save is the server's.

## Consequences

The expiry is evaluated server-side and needs no scheduler, because it
is a comparison rather than an event. The cost is that a player whose
clock is wrong sees the wrong expiry, which is why the server's clock
is the one that counts.
