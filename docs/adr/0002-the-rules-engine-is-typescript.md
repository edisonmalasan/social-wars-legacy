# 2. The rules engine is TypeScript, deterministic and seeded

**Status:** accepted

## Context

The client's 229 unit delegates are 1.32 MB of bespoke ActionScript. The
rules engine has to be iterated against them, thousands of times, and
every iteration needs a comparison against the original.

## Decision

The rules engine is TypeScript, in `packages/rules`, and it is
**deterministic and seeded**: the same seed and the same inputs produce
the same outcome, on any machine.

The generator is a xoshiro128** whose every operation is a 32-bit
integer operation, and the arithmetic is IEEE 754 double, which the
language specifies exactly. So the determinism is **provable by
construction**, not merely tested on two machines.

The same engine runs in Node, for the multiplayer server, and in a
browser worker, for offline play.

## Alternatives

- **Port the ActionScript to Rust** for speed. The iteration cost goes up
  sharply: every comparison against the original would need a bridge.
- **Keep the original's `Math.random()`.** The original's battles were
  never reproducible, so a server could not re-simulate one and claim
  the client's result was wrong. That is not a property worth keeping.

## Consequences

The engine can be run in either place without a second implementation.
The price is that the speed of the engine is the speed of a scripting
language's arithmetic, which is adequate for the simulation and is the
right trade for the iteration speed.

**Note (2026-10-21).** The reason for running the engine in a browser
has changed. There is no offline mode any more — see
[ADR 19](./0019-pure-online.md) — but the engine is still free of the
platform, because the client uses it to **predict** outcomes and to
generate the projectiles' random scatter. That use decides nothing:
the server decides every outcome, and the client's predictions are
only what it draws while it waits for the answer.
