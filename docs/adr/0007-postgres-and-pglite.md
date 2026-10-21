# 7. PostgreSQL for the server, and the same schema over PGlite offline

**Status:** superseded

**Superseded by:** [ADR 19](./0019-pure-online.md) — the product is pure
online, so there is no offline mode for PGlite to serve in the browser.
The **database** decision stands: the server's database is PostgreSQL,
and PGlite is PostgreSQL compiled to WebAssembly, which is what the
development server and the integration tests use.

## Context

The server needs a real database. The offline mode needs a database
that runs *in the browser*, with no server at all.

## Decision

**PostgreSQL** for the server, and **PGlite** — PostgreSQL compiled to
WebAssembly — for the offline mode, over **the same schema** and the
same query layer.

## Alternatives

- **SQLite everywhere.** It is not PostgreSQL, so the server's and the
  offline mode's behaviour would differ in the corners that matter.
- **IndexedDB for the offline mode.** A different data model, a
  different query language and a different set of bugs.
- **A server for the offline mode.** That is not offline.

## Consequences

The offline mode's data is the server's data, so a save can move
between them. The cost is that PGlite is a large WebAssembly download,
and that the schema has to be one that both accept.
