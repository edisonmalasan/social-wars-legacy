# 21. Clean-room original assets, generated and dedicated CC0-1.0

**Status:** accepted

## Context

The decompiled client is the specification for behaviour, but its sprites,
effects, sounds, fonts and configuration are Zynga's proprietary content.
The upstream project's GPL v3 covers its Python code only, not that content.
The licensing position (`docs/LICENSING.md`) therefore blocks a public
release until the art and the audio are re-created or licensed, and the
roadmap keeps that gate open.

The project needs a supply of art that can be redistributed without a rights
dispute. Licensing the originals is not available, and leaving the art out
forever leaves the game unplayable. The replacement must have provenance a
reviewer can check, not just an assertion that it is "original".

## Decision

New art and audio are **created in the clear room** by `@swl/art`: a pure,
deterministic TypeScript generator that assembles SVG motifs from integer
coordinate tables and synthesises WAV effects from a fixed sine table and a
seeded 32-bit generator. It is a dependency of neither the client nor the
server; it emits files into `assets/original/`.

Every emitted file is dedicated to **CC0-1.0**, with a notice beside the
files and a provenance manifest recording path, byte size, SHA-256,
generator version, licence and an explicit original-work statement per file.
The generator reads no input file; only its own output tree is read back by
its `--check` mode. Tests prove byte-identical regeneration, valid SVG and
WAV headers, distinct hashes, the licence field, and the absence of any
read from the vendored upstream or the reverse-engineering tree.

The first increment is a coherent family of sixteen UI/unit motifs, a sprite
sheet and six short effects. It is **not** a replacement for the game's
asset set: it does not claim that any screen is implemented, it does not
close the licensing gate, and it is not wired into the client by this
decision. Integration and the remaining motifs are later work.

**The proprietary configuration is handled separately.** `config/main.json`
and its deltas are data describing the original game's content; the content
bundle is derived from them today. A clean-room replacement for that data is
its own task and is not achieved by generating art. Nothing in this decision
changes the rules engine, the 94-command catalogue, the two-argument
`set_quest_var` contract or server authority.

## Alternatives

- **Licence Zynga's art and audio.** There is no licence on offer for these
  assets, and the upstream's GPL v3 does not cover them. Treating the
  upstream's grant as permission would be a legal error, so this is not an
  available option.
- **Ship the original assets and rely on the upstream's licence.** The
  sprites, sounds and configuration are not covered by that licence. This
  would distribute proprietary content and is rejected.
- **Leave the art excluded indefinitely.** This keeps the repository safe
  but the game stays unplayable. It remains the state until enough original
  art exists; it is a fallback, not a plan for the whole project.
- **Commission hand-drawn or third-party stock art.** Both can work, but
  each needs its own provenance and licence review, and neither is
  reproducible from the repository. A deterministic generator gives the
  same bytes on every machine and a manifest that can be verified in CI.

## Consequences

The project now has a legally usable, verifiable art source that can grow
incrementally without touching the vendored tree. Reviewers can check the
manifest and rerun the generator; a change to a motif shows up as a different
hash and a different byte-for-byte generation.

The cost is that generated art is stylistically simpler than the original
and that the family has to be extended before it covers the game. The
licensing gate stays **open** until the whole shipped set is original and
integrated, and no release artefact may be published on the strength of this
decision alone.
