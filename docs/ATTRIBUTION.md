# Attribution

This project preserves a game that would otherwise be lost, and it
stands on the work of other people. This file carries the notices they
ask for.

## The game

**Social Wars** was made by **Zynga**. The game's code, art, audio,
configuration and trademarks are Zynga's property. This project is a
preservation and a study; it does not claim the game's assets and does
not redistribute them. See [`LICENSING.md`](LICENSING.md).

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
