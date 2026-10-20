# 11. The resource vector's order is preserved exactly

**Status:** accepted

## Context

The command tuple is `[map_id, cmd, args[], res[8]]`, and the resource
vector's slots are ordered **`[energy, xp, gold, wood, oil, steel, cash,
mana]`** — verified live by watching the interface's counters move.

## Decision

Every reimplementation of the wire format preserves that order exactly.
The protocol package holds it as a single type, so the order is stated
once.

## Alternatives

- **A named object** for the resource vector. It would be clearer, and
  it would break the wire format: the original client sends eight
  numbers in a fixed order, and the shim has to read them.

## Consequences

The order cannot drift, because there is one type and one constant. The
cost is that a reader of the protocol has to know the order, which is
why the constant is named and the finding is written down.
