# 12. The production cycle belongs to the server

**Status:** accepted

## Context

A resource building's production is a **period the player chooses**:
five minutes at 0.25, sixty at 1, 240 at 2 and 480 at 3. The upstream
never checks that the player waited — its `collect` handler resets the
timestamp and believes whatever the client sends.

## Decision

The **server owns the clock**. The building's period and the moment its
countdown started are in its own state, and a collection is refused
until the period has elapsed.

## Alternatives

- **Trust the client's claim, as the upstream does.** Then a player can
  claim a factory's output as often as they like.
- **A fixed period.** The period is the player's choice, and the choice
  is part of the game.

## Consequences

The rules engine models the cycle (`packages/rules/src/production.ts`)
and the applier enforces it. The cost is that the client has to show
the countdown honestly, which it already does.
