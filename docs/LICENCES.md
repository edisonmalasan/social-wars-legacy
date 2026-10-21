# The third-party licences

Every dependency the project ships has a licence, and this file says
what each one is. It is **generated** by
`node scripts/build-licence-report.mjs`, so it cannot drift from the
manifests, and a dependency that is not classified **fails the build**.

See [`LICENSING.md`](LICENSING.md) for the position on the project's
own assets, and [`ATTRIBUTION.md`](ATTRIBUTION.md) for the notices the
original project asks for.

## The JavaScript and TypeScript

| The dependency | The version | The licence | Why it is here |
|---|---|---|---|
| `@electric-sql/pglite` | ^0.5.10 | Apache-2.0 | the database |
| `@types/node` | ^22.10.2 | MIT | the type definitions |
| `pixi.js` | ^8.22.0 | MIT | the client's renderer |
| `typescript` | ^5.7.2 | Apache-2.0 | the language |
| `vite` | ^6.0.0 | MIT | the client's build |

## The Rust

| The crate | The version | The licence | Why it is here |
|---|---|---|---|
| `tauri-build` | 2 | MIT OR Apache-2.0 | the shell's build |
| `tauri` | 2 | MIT OR Apache-2.0 | the desktop shell |
| `serde` | 1 | MIT OR Apache-2.0 | the serialisation |
| `serde_json` | 1 | MIT OR Apache-2.0 | the serialisation |
| `rustls` | 0.23 | Apache-2.0 OR ISC OR MIT | the shell's certificate check |
| `rustls-native-certs` | 0.7 | Apache-2.0 OR ISC OR MIT | the operating system's certificate roots |
| `rustls-pki-types` | 1 | MIT OR Apache-2.0 | the certificate's types |
| `ring` | 0.17 | Apache-2.0 AND ISC | the certificate's fingerprint |

The tree has **437** crates in total, pinned by
`Cargo.lock`. The direct ones are above; the rest are Tauri's, and
each carries its own licence.

## The fonts

| The face | The licence | Why |
|---|---|---|
| Nunito | SIL Open Font License 1.1 | the substitute for Arial Rounded MT Bold |
| Rubik Mono One | SIL Open Font License 1.1 | the substitute for Komika Axis |

The client's own faces are **proprietary** and are not shipped.

## The assets

There are none. The art, the sounds and the configuration are Zynga's,
they cannot be shipped, and the clone re-creates them. See
[`LICENSING.md`](LICENSING.md).
