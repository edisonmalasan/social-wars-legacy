# 16. The upstream is vendored unmodified, and never linked into the product

**Status:** accepted

## Context

The upstream project is **GPL v3**, and it is the only surviving
description of the original protocol and of the original data. It is
also the only surviving **test oracle** for the rules.

## Decision

The upstream is vendored **byte for byte**, with a SHA-256 manifest that
`node scripts/verify-upstream.mjs` checks on every build, and it is
**never imported** by any package that ships.

It is a reference and a test fixture, not a runtime dependency.

## Alternatives

- **Rewrite the upstream in TypeScript** and use that.** The upstream's
  behaviour is not the specification (see ADR 9), so a faithful port
  would be a faithful port of the wrong thing.
- **Link the upstream.** The shipped product would become a derivative
  work of GPL v3 code, and would have to be distributed as GPL v3.

## Consequences

The shipped product carries no GPL code, and the vendored tree keeps
its notices. The cost is that the upstream's Python and the clone's
TypeScript are two implementations of the same protocol, and the golden
master's job is to compare them.
