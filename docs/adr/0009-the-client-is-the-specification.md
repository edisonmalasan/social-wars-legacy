# 9. The client is the specification

**Status:** accepted

## Context

The upstream's Python server and the original Flash client **disagree**
about how the game works. Where they disagree, one of them is a bug in
the original: the upstream's trade counter resets daily when the client
resets it every 20 hours, and the upstream's Monday reward cycle wraps
at five entries when the client's has three.

## Decision

**The client wins, every time.** The upstream is a description of the
protocol and of the data, and it is a test oracle, but it is not the
specification of the *behaviour*.

Every disagreement is recorded, with the client's behaviour and the
reason.

## Alternatives

- **The upstream wins.** It is the code that actually ran the game, so
  it has the stronger claim — but the discrepancies are the upstream's
  bugs, and reproducing a bug is not the point of a preservation.
- **Pick per case.** That is what happens in practice, and it is what
  makes the rule necessary: a per-case decision with no principle
  becomes an argument every time.

## Consequences

The rules engine matches the game the players played, not the server
that served it. The cost is that the upstream cannot be trusted as an
oracle for behaviour, only for the protocol.
