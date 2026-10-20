# The licensing position

**Status:** the position for the shipped product is settled. What is *not*
settled is the **release** of anything derived from Zynga's assets, and
this document says exactly where that line is.

This is the document the roadmap's "the asset licensing position is
settled and written down" asks for. It is written in terms of what the
repository actually contains, so it can be checked rather than believed.

## The short version

1. The **shipped product contains no Zynga asset and no Zynga code.**
   The client's art, its sounds, its fonts and its configuration are not
   in the shipped tree, and the shipped tree is scanned for them.
2. The **upstream project** — the Python server, which is GPL v3 — is
   vendored **unmodified**, as a reference and a test fixture. It is not
   linked into the shipped product, and it is not a runtime dependency
   of it.
3. The **game's rules** are reimplemented from the **decompiled client**,
   which is a specification, not an implementation. The client's code is
   proprietary, and none of it is copied into the shipped tree.
4. **The art and the audio are the open question.** The client's sprites
   and sounds are Zynga's. The clone needs art to be playable, and the
   art that exists is Zynga's. So the art must be **re-created** before
   any public release, or licensed.

## What is in the repository

| What | Where it is | Licence | In the shipped product? |
| --- | --- | --- | --- |
| The upstream server | `upstream/socialwarriors/` | **GPL v3** | **No** |
| The client's art, sounds and configuration | `upstream/socialwarriors/assets/` | **Zynga's, proprietary** | **No** |
| The decompiled client | `.work/as/` (not committed) | **Zynga's, proprietary** | **No** |
| The rules engine | `packages/rules/` | This project's | **Yes** |
| The server | `packages/server/`, `apps/server/` | This project's | **Yes** |
| The client | `packages/client/`, `apps/client/` | This project's | **Yes** |
| The substitute fonts | (fetched at build time) | **SIL OFL 1.1** | **Yes** |

## The upstream, and why it is vendored

The upstream project — <https://github.com/AcidCaos/socialwarriors> — is
the Python 3.9 / Flask 2.2.5 server the original game ran on. It is
**GPL v3**, and it is vendored here **byte for byte**, with a SHA-256
manifest that `node scripts/verify-upstream.mjs` checks on every build.

It is vendored for three reasons, none of which is to ship it:

- it is the only surviving description of the **original protocol**;
- it is the only surviving description of the **original data**;
- it is a **test oracle**: the golden-master corpus is built by running
  the upstream's own rules and comparing them with the clone's.

That last point is why it is a dependency of the *tests* and not of the
*product*. The upstream is never imported by `packages/rules`,
`packages/server` or `apps/server`, and the shipped product contains no
GPL code.

### The obligations that come with GPL v3

GPL v3 is a **copyleft** licence, and vendoring it puts obligations on
the *distribution of the vendored tree*:

- the tree keeps its `LICENSE` and its copyright notices, **unmodified**;
- the tree is not linked into the shipped product, so the shipped
  product is **not** a derivative work of it;
- if the vendored tree is redistributed, the **source** comes with it —
  which it does, because the whole tree is in the repository;
- the tree carries **no warranty**, and the repository says so.

`upstream/PROVENANCE.md` records where the tree came from, when, and
how it was verified.

## The client's assets

The client's art (751 MB of sprites, effects, sounds, fonts and the
configuration) is **Zynga's**, and the game was proprietary: there is
no open licence for it, and none is implied by the upstream's GPL v3.

So the clone **cannot ship it**. Three ways forward, and the project has
picked the third:

1. **Licence it.** Not available: Zynga's games were not licensed for
   redistribution.
2. **Ship it and rely on the upstream's licence.** Wrong: the assets are
   not covered by the upstream's GPL v3 grant.
3. **Re-create the art.** The clone's art is drawn from scratch, or
   generated, or replaced by a permissive stand-in. That is the path
   this project takes.

Until the art is re-created, the game is **playable in development**
against the vendored assets and **not distributable**.

### The fonts

The client's two faces — Arial Rounded MT Bold and Komika Axis — are
proprietary. They are **replaced** with Nunito and Rubik Mono One, both
under the **SIL Open Font License 1.1**, which permits redistribution
and embedding.

The replacement is not a swap: the substitute is **scaled** so that the
text occupies the same width as the original, because the game's
layout was sized for the original's metrics
(`packages/client/src/fonts.ts`).

The client ships fonts for English, Turkish and Greek; only the English
ones are distributed. The clone does the same, and falls back the same
way.

## The rules, and how they were derived

The rules engine is a **reimplementation from the client's behaviour**.
The client is the specification (the roadmap's non-negotiable 2): where
the upstream's Python and the client's ActionScript disagree, the client
wins, and every such disagreement is recorded.

That is a **clean-room reimplementation from observed behaviour**, not a
copy of the client's source. The decompiled ActionScript is used to
*understand* what the game does — the numbers, the order, the edge
cases — and the clone's code is written from that understanding.

The distinction matters legally and it is maintained deliberately:

- the clone's source contains **no copied ActionScript**;
- the clone's constants are **facts about the game** (a collect period
  is 5, 60, 240 or 480 minutes), which are not copyrightable;
- the clone's **test corpus** records inputs and expected outputs, which
  is the standard way to specify behaviour.

`scripts/verify-upstream.mjs` checks that the vendored tree is
unmodified, and the same discipline is applied to the client's assets:
the clone's own tree carries no `.swf` and no Zynga media, and
`node scripts/check-no-flash.mjs` scans everything that ships.

## What must happen before a public release

These are the gates, and none of them is optional:

1. **The art is re-created or licensed.** Every sprite, every effect
   and every sound. The clone's own art must be the game's art.
2. **The audio is re-created or licensed** on the same terms.
3. **The configuration is re-created.** The upstream's `config/main.json`
   is a data file describing the original's content; the clone's bundle
   is built from it, and a public release needs the bundle's content to
   be the project's own.
4. **The attribution and the preservation notices** the original project
   makes are carried — see the roadmap's item, which is separate from
   this one.
5. **The third-party licences** (the fonts, the audio libraries, the
   Rust and JavaScript dependencies) are enumerated, and the notice file
   is shipped with the artefact.

Until step 1 is done, this project is a **preservation and study**: the
code is free, the analysis is published, and the game itself is not
distributed.

## How the position is checked

`node scripts/check-licensing.mjs` checks the claims above, and it is
in the CI:

- the vendored upstream's licence **is** the GPL v3;
- **no package imports from the upstream** — so the shipped product is
  not a derivative work of it;
- the shipped tree carries **no SWF, no sound** and **none of the
  client's proprietary fonts**.

The font check is precise about what it forbids. The **identifier** the
client uses for a face — `ArialRoundedBold`, `KomikaAxis` — is not the
face: the client has to know the original's name to map it to a
substitute. What must not appear is a proprietary face being *asked for*,
so the check looks for a `font-family` that names one, and for a file
that *is* one.

The check is proven to fire: it fails on a stylesheet that asks for
Arial Rounded MT Bold, and on a `.swf` in a shipped tree.

## A note on what this document is not

It is not legal advice, and it does not make the position safe in every
jurisdiction. It records the position the project has taken, the
reasoning behind it, and the gates that remain. Anyone distributing a
build should take their own advice on the parts that need it.
