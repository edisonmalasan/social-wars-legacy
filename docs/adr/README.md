# The architecture decision records

Each record states a decision, the alternatives that were considered, and the
reasoning. A decision without a rationale is a decision somebody will quietly
reverse, so the alternatives and the consequences are the parts that matter.

The roadmap's "Locked Decisions" section is the summary; these are the whole
reasoning.

| # | Decision | Status |
| --- | --- | --- |
| 1 | [A TypeScript monorepo, with pnpm workspaces](./0001-typescript-monorepo.md) | accepted |
| 2 | [The rules engine is TypeScript, deterministic and seeded](./0002-the-rules-engine-is-typescript.md) | accepted |
| 3 | [The server is authoritative](./0003-the-server-is-authoritative.md) | accepted |
| 4 | [The client is a PixiJS v8 world with a React DOM interface](./0004-pixijs-and-react.md) | accepted |
| 5 | [The desktop shell is Tauri v2](./0005-the-tauri-desktop-shell.md) | accepted |
| 6 | [One web client, for the web, the desktop and the mobile](./0006-one-web-client.md) | accepted |
| 7 | [PostgreSQL for the server, and the same schema over PGlite offline](./0007-postgres-and-pglite.md) | accepted |
| 8 | [Git LFS for the binary assets](./0008-git-lfs-for-the-assets.md) | accepted |
| 9 | [The client is the specification](./0009-the-client-is-the-specification.md) | accepted |
| 10 | [The compatibility shim accepts both server keys](./0010-both-server-keys.md) | accepted |
| 11 | [The resource vector's order is preserved exactly](./0011-the-resource-vector-order.md) | accepted |
| 12 | [The production cycle belongs to the server](./0012-the-production-cycle-is-the-server's.md) | accepted |
| 13 | [The premium is a timestamp the server owns](./0013-the-premium-is-a-timestamp.md) | accepted |
| 14 | [The determinism is provable by construction](./0014-determinism-by-construction.md) | accepted |
| 15 | [The schema is versioned, and the migrations run as part of the deploy](./0015-the-schema-is-versioned.md) | accepted |
| 16 | [The upstream is vendored unmodified, and never linked into the product](./0016-the-upstream-is-vendored-not-linked.md) | accepted |
| 17 | [The substitute fonts are scaled to the original's metrics](./0017-the-substitute-fonts-are-scaled.md) | accepted |
| 18 | [The roadmap's item counts are checked](./0018-the-roadmaps-item-counts-are-checked.md) | accepted |
