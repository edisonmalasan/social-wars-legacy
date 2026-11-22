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
| `@types/react` | ^19.3.0 | MIT | the renderer types |
| `@types/react-dom` | ^19.3.0 | MIT | the renderer types |
| `@vitejs/plugin-react` | ^4.3.4 | MIT | the client's build |
| `pixi.js` | ^8.22.0 | MIT | the client's renderer |
| `react` | ^19.3.1 | MIT | the interface's renderer |
| `react-dom` | ^19.3.1 | MIT | the interface's renderer |
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

The original game's art, sounds and configuration are Zynga's and are not
shipped. The project's **own** replacement art is original work dedicated to
**CC0-1.0**:

| What | Where | Licence | Why |
| --- | --- | --- | --- |
| The clean-room generator | `packages/art/` | CC0-1.0 | deterministic SVG and WAV synthesis from primitives |
| The Foundry icon family and sprite sheet | `assets/original/icons/` | CC0-1.0 | sixteen original UI/unit motifs |
| The six short effects | `assets/original/sounds/` | CC0-1.0 | synthesised from a fixed sine table, not recorded |
| The dedication and provenance manifest | `assets/original/LICENSE`, `assets/original/manifest.json` | CC0-1.0 | per-file path, size, SHA-256 and generator version |

This is the first increment, not the finished set: it does not close the
licence gate and it is not yet wired into the client. See
[`LICENSING.md`](LICENSING.md).
