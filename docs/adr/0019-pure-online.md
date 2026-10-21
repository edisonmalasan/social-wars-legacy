# 19. The product is pure online

**Status:** accepted

## Context

The roadmap originally had an **offline single-player mode**: the rules
engine and the database, both running in the browser, so that the game
could be played with no server at all. It was built and proved — the
same applier, over the same schema, against PostgreSQL compiled to
WebAssembly in IndexedDB, and the end-to-end test played a command
through it in a real browser.

It is a large piece of work for a mode the game does not need. The
original game had no offline mode: it was a server game, and its
client was a thin renderer over a server that decided everything.

There is also a **cost** that is easy to underrate. The offline mode
puts the whole authority in the browser, and the browser is the one
place the project cannot keep a secret in:

- The rules engine in the browser is **readable** by anyone who loads
  the page. That is fine — the rules are the specification and they
  are meant to be legible — but it means every rule that a cheat
  would want to bend is in the player's hands, and the cheat battery's
  guarantee ("the server computes the costs and the server
  re-simulates the outcomes") becomes a claim about a server that
  happens to also run elsewhere.
- The offline mode's database is a **local file** the player owns, and
  a player who owns the save owns the wallet. The server's authority
  is the whole point of the project, and an offline save is a
  wallet that the player can edit.
- The offline mode is a **second place** for the schema, the applier
  and the rules to be right in. The server's own claim — one
  authority, one place — is worth more than the mode.

## Decision

**The product is pure online.** The client never decides an outcome,
never keeps a world of its own, and never runs the rules engine to
settle a battle. Every command goes to the server, and the server's
answer is what is drawn.

The offline mode is **not** a shipped feature. It is not built, not
maintained and not promised. The roadmap records it as dropped, with
this record as the reason.

This supersedes the offline half of [ADR 7](./0007-postgres-and-pglite.md)
and corrects the reason given in [ADR 2](./0002-the-rules-engine-is-typescript.md)
for running the engine in a browser. The **decisions** in both stand:
the rules engine is TypeScript, deterministic and seeded, and the
database is PostgreSQL.

## Alternatives

- **Ship the offline mode as it is.** It works, and it is proved. The
  objection is not that it is broken but that it puts the authority
  somewhere it should not be, and that it is a second place for the
  rules to be right in.
- **Ship the offline mode but never trust it.** The client would keep
  the local save for convenience and the server would still decide
  every outcome. That is a cache, not an offline mode, and it would
  still be a second implementation of the world's state.
- **Keep the mode as a preservation feature.** The original had none,
  so preserving it means preserving something that never existed.
- **Make the offline mode the only mode.** That would throw away the
  server's authority, which is the one property the project is
  actually about.

## Consequences

- The client bundle carries **no database** and no WebAssembly
  PostgreSQL: it is the game and the renderer, and nothing else.
- There is **one** place where an outcome is decided, and it is the
  server. The cheat battery's guarantee is a guarantee about the
  only authority there is.
- The rules engine is still free of the platform, because the client
  uses it to **predict** outcomes and to generate the projectiles'
  random scatter. That is a read-only use, and it decides nothing.
- A player with **no server** cannot play. That is the original
  game's position, and the roadmap's out-of-scope section now says so
  plainly.
- The client's manifest, its atlas pages and its build are smaller,
  and the web client's first load is quicker.
