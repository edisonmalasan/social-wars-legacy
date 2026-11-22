# `@swl/art`

A deterministic, clean-room generator for the project's **own** art and
audio. It produces the "Foundry" family of sixteen SVG icons, one sprite
sheet, six short WAV effects, a CC0 notice and a provenance manifest.

Run from the repository root:

```sh
node packages/art/src/cli.ts           # (re)write assets/original/
node packages/art/src/cli.ts --check   # fail if they differ
node --test "packages/art/src/**/*.test.ts"
```

## What makes it clean-room

- The geometry is assembled from integer coordinate tables and the SVG
  primitives in `src/svg.ts`. No image, SWF, atlas or font file is opened.
- The audio is synthesised from a fixed sine table and integer envelopes
  driven by the seeded generator in `src/random.ts`. No recording is used.
- Every motif has its own seed derived from its id, so the output does not
  depend on generation order, the wall clock or platform randomness.
- Only `src/io.ts` touches the filesystem, and only to write the output tree
  or read it back for `--check`. The tests record every path and assert that
  none lies under the vendored upstream or the reverse-engineering tree.

## Provenance

`assets/original/manifest.json` lists every emitted file with its relative
path, byte size, SHA-256, generator version, licence (`CC0-1.0`) and an
explicit original-work statement. `assets/original/LICENSE` carries the CC0
dedication alongside the files themselves.

This package does not replace the original game's art in the client. It is
the first, legally usable increment; integration and the remaining assets
are separate work. See [ADR 0021](../../docs/adr/0021-clean-room-assets.md)
and [`docs/LICENSING.md`](../../docs/LICENSING.md).
