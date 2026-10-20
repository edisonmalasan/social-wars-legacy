# 3. The server is authoritative

**Status:** accepted

## Context

The original server is not. The 8-slot `res` vector is **client-declared**
and the upstream applies it verbatim. Combat is 100 % client-side, and
`end_quest` and `end_attack` carry the entire outcome. `flash_debug`
overwrites the whole wallet from client arguments.

## Decision

The new server decides every outcome: combat outcomes, resource costs,
goal completion and reward grants. The client **requests and renders**;
it never decides.

The native protocol has no field for a client-claimed result at all,
rather than having one that is ignored. A command that is not priced by
the cost table is treated as free, not as "whatever the client says".

## Alternatives

- **Trust the client and validate loosely.** That is the original's
  design, and it is why the cheat battery exists.
- **Keep the claimed result but re-simulate and compare.** A useful
  diagnostic, and the shim does it for the legacy dialect. But the
  claimed result must not *decide* anything.

## Consequences

The cheat battery exists to prove the property, and it is
mutation-tested so that a passing battery is evidence rather than a
formality. The cost is that the server has to re-simulate every battle,
which is the work the client used to do for free.
