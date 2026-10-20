# 15. The schema is versioned, and the migrations run as part of the deploy

**Status:** accepted

## Context

The stores created their tables with `CREATE TABLE IF NOT EXISTS`. That
form can only ever **add** a table, and it says nothing about what
happened to the ones that were already there: a column a new server
needs would be added by hand, and the hand-added column would be in no
migration's history.

## Decision

The schema is a list of **migrations**, each of which moves the schema
one version forward. Every migration that runs is recorded in the
database. A migration may declare a `down`; one that cannot be undone
safely declares no `down`, and the runner **refuses** to roll it back
rather than pretending it can.

The migrations run **before the server serves**, so a deploy cannot
start a server against a schema it does not understand.

## Alternatives

- **A schema file that is applied wholesale.** That is a migration with
  no history, and it cannot be rolled back.
- **The ORM's own migration tool.** The project chose the queries itself,
  and a tool that wants to own the schema is a tool that has to be
  trusted with the players' saves.

## Consequences

The schema's history is in the database. The cost is that a migration
is a piece of code that has to be written and tested, and that the
runner has to be trusted.
