# 10. The compatibility shim accepts both server keys

**Status:** accepted

## Context

The original server's signing key is a compile-time constant that
**rotated once**: `3m0d3pwiupoetn7ysa02` for client builds 1.4.5 to
1.4.27, and `4vVSD8dftv6hdfb1Hnk9` for 1.4.28 to 1.5.4. The
live-verified key is the rotated one.

## Decision

The shim accepts **both**. The framing is verified against the captured
traffic of both eras.

## Alternatives

- **The live key only.** It would reject every unmodified client of the
  earlier era, and the point of the shim is to serve those clients.
- **The old key only.** The live traffic would not verify.

## Consequences

The shim serves the clients of both eras, and the framing is checked
against real captured traffic rather than against a description of it.
