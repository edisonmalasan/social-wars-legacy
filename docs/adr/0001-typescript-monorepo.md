# 1. A TypeScript monorepo, with pnpm workspaces

**Status:** accepted

## Context

The project has four things to build that must agree with each other
exactly: a rules engine, a server, a client and a desktop shell. The
rules engine's types are the server's types are the client's types, and
a drift between them is a bug that only shows up at runtime.

## Decision

One repository, one language, and pnpm workspaces: `packages/protocol`,
`packages/content`, `packages/rules`, `packages/client`, `packages/server`
and the `apps/*` that consume them.

The protocol package holds the wire types, and both the client and the
server import them. There is no second copy of a type and no generated
client.

## Alternatives

- **Separate repositories.** A network hop between the client and the
  protocol package on every build, and a version to keep in step. The
  drift risk is the same; the friction is added.
- **Code generation** from a schema, as protobuf or OpenAPI do. It
  solves the drift, but the generated types are not the types the code
  reads, and a generator is another thing to maintain.
- **A single package.** One `package.json` for the whole thing. The
  client would drag the server's dependencies into the browser's bundle.

## Consequences

The shared types cannot drift, because there is only one of them. The
cost is that the repository is a monorepo, and every tool has to
understand that.
