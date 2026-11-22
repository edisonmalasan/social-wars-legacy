# Attribution

This project preserves a game that would otherwise be lost, and it
stands on the work of other people. This file carries the notices they
ask for.

## The game

**Social Wars** was made by **Zynga**. The game's code, art, audio,
configuration and trademarks are Zynga's property. This project is a
preservation and a study; it does not claim those assets, and it does not
redistribute the **original media or runtime files** — no SWF, sound file or
proprietary font face is present in the shipped trees, which
`scripts/check-licensing.mjs:34-38` checks. **Data derived** from the
proprietary configuration and art *does* ship with the client:
`apps/client/public/content-bundle.json` (1.19 MB, 900 items, built from the
upstream `config/main.json`, the five patches, quest snapshots and
decompiled-derived maps) and `apps/client/public/frame-manifest.json` (4 MB
of atlas regions measured from the client's SWFs). That derived data is not
rights-clean: the asset-licensing release gate stays open and no publication
is authorised. See [`LICENSING.md`](LICENSING.md).

The **preservation** was started by the **Social Warriors** team, whose
project this one follows:

- the upstream project: <https://github.com/AcidCaos/socialwarriors>
- the upstream's releases and bundles: the same repository's releases
- the upstream's contributors: <https://github.com/AcidCaos/socialwarriors/graphs/contributors>

The upstream project is **GPL v3**, and its tree is vendored here
**unmodified**, with its notices intact. The upstream's own README asks
for two things, and both are carried:

- the **contributors** are credited — the upstream's contributors list is
  the canonical one, and the upstream's `LICENSE` and `README` travel
  with the tree;
- the **Discord group** is where the upstream's bugs are reported — the
  upstream's README names it.

This project adds its own work on top: a rules engine reimplemented from
the client's observed behaviour, a modern server, a Flash-free client,
and a desktop shell. Those are this project's, under its own licence.

## The project's own art

The "Foundry" icons, sprite sheet and short effects in `assets/original/`
are original work generated from primitives by `packages/art` and dedicated
to **CC0-1.0**. They are not Zynga's art and were not traced, sampled or
copied from it; the manifest records a hash and an original-work statement
for every file. Zynga remains the author and owner of the original game's
art, audio and configuration; the original media files are not redistributed,
but data derived from them ships in the client's content bundle and frame
manifest (see above and [`LICENSING.md`](LICENSING.md)).

This is the first increment of a clean-room replacement, not the finished
set. It does not make the game distributable on its own — see
[`LICENSING.md`](LICENSING.md).

## The analysis

The reverse-engineering report set lives in `re/`. It is the project's
own analysis of the client's behaviour, and it is the reason the rules
engine can be trusted to match: every rule in it is traced to a place in
the client.

## The dependencies

The project's own dependencies keep their own licences, and the notice
file that ships with a release enumerates them. The ones with licences
that matter most to a user are:

| Dependency | Licence | Why |
| --- | --- | --- |
| [Nunito](https://fonts.google.com/specimen/Nunito) | SIL OFL 1.1 | The substitute for Arial Rounded MT Bold |
| [Rubik Mono One](https://fonts.google.com/specimen/Rubik+Mono+One) | SIL OFL 1.1 | The substitute for Komika Axis |
| [Tauri](https://tauri.app) | MIT / Apache-2.0 | The desktop shell |
| [rustls](https://github.com/rustls/rustls) | MIT / ISC / Apache-2.0 | The shell's certificate check |
| [PixiJS](https://pixijs.com) | MIT | The client's renderer |
| [PGlite](https://pglite.dev) | Apache-2.0 | The development server's database, and the tests' |
| [TypeScript](https://www.typescriptlang.org) | Apache-2.0 | The language |

The vendored upstream's own dependencies are listed in its
`requirements.txt`, and they are its business rather than this
project's — the shipped product does not run any of them.

## The fonts

The client's two faces are **proprietary**, and they are **replaced**:

- Arial Rounded MT Bold → **Nunito**, SIL Open Font License 1.1
- Komika Axis → **Rubik Mono One**, SIL Open Font License 1.1

The substitute is **scaled** so that the text occupies the same width as
the original, because the game's layout was sized for the original's
metrics. The scaling is measured against the real font files at build
time.

## A request

If you own the rights to anything here and you would like it changed,
removed or credited differently, please say so. This project exists to
preserve a game, and the people who made it deserve to be accurately
credited.

**Open a draft issue** in this repository, titled *Rights request*, and
say what you would like changed and what you own. You will get an
answer, and what was done is recorded.

The policy is [`CORRECTIONS.md`](CORRECTIONS.md): what can be asked
for, what happens next, and the log of every request and every answer.
