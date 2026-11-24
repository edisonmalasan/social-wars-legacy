# 0022. Vendor original game assets (DRAFT — requires owner approval)

**Status:** proposed — NOT accepted. Supersedes nothing until accepted.
**Date:** 2026-11-24
**Owner decision that prompted this draft:** the owner rejected the clean-room CC0
motifs as visually inadequate and chose "Vendor into the repo" for the original assets at
`C:\Users\Edison\Desktop\socialwarriors`.

## Context

The owner wants the rebuilt game to use the original game's art rather than the CC0
replacements. That is a material change to
[ADR 0021](0021-clean-room-assets.md) (accepted) and to the licensing/no-Flash constraints
in `AGENTS.md` and `docs/GOAL.md`. GOAL.md §Authority requires a written proposal and
owner approval before a locked decision is changed; this document is that proposal.

Measured inventory of the read-only reference at `C:\Users\Edison\Desktop\socialwarriors`:

| Content | Files | Size | Notes |
|---|---:|---:|---|
| `assets/` | 3,199 | 716.8 MB | 1,176 `.swf` (620.6 MB), 1,756 `.jpg` (84.0 MB), 143 `.png` (7.4 MB), 140 `.mp3` (5.5 MB) |
| `config/` | 42 | 6.1 MB | proprietary game configuration |
| `templates/`, `villages/`, `build/`, other | — | ~3.5 MB | HTML/CSS chrome and save fixtures |

No single file exceeds GitHub's 100 MB limit, but the tree is ~726 MB.

## Decision (proposed)

If accepted:

1. Vendor a **declared subset** of the original media into a tracked, clearly named
   directory (e.g. `assets/original-proprietary/`), with a provenance manifest recording
   source path, SHA-256, and the owner's authorisation.
2. Add an explicit opt-in runtime art mode that selects that media **only** for the owner's
   private desktop experiments. The default shipped mode stays CC0; no original file is
   fetched or read unless the mode is enabled.
3. Amend `docs/LICENSING.md` to state plainly that the repository contains Zynga media,
   that it is not licensed for redistribution, and that public release remains blocked.
4. Amend the `check-no-flash`/licensing gates so they **detect and report** the new
   directory rather than being weakened: shipped builds must still contain no Flash
   runtime or proprietary media; the vendored tree is a private test fixture only.

## Consequences

- The repository becomes a public distribution of proprietary Zynga art. GPL v3 on the
  upstream **server code** does not grant this right; only the owner can accept that risk.
- Raw `.swf` files are not renderable by PixiJS. A conversion and atlas-packing step would
  still be required for the original look — the existing Group D pipeline can do this for
  a bounded subset, but earlier analysis measured thousands of atlas pages, so a bounded
  subset must be chosen explicitly.
- CI gates must remain honest: they must fail if proprietary media leaks into a shipped
  bundle. Silently disabling them is not acceptable.

## Alternatives

- **External path, private only (not chosen):** keep everything in
  `C:\Users\Edison\Desktop\socialwarriors` and point a private desktop build at it. No
  proprietary bytes in the public repo; smaller legal exposure; still needs an ADR.
- **Converted PNG frames only:** vendor no `.swf`, only converted atlas images for a small
  screen set. Less Flash-surface area but still proprietary media.

## Open questions for the owner

1. Which subset: all ~726 MB, or only the converted frames needed for the main town view?
2. Should the opt-in mode be desktop-only, or also available to the local dev web client?
3. Confirm acceptance of publishing proprietary media in a public GitHub repository.

This draft changes no code, no ADR status, and no CI gate. It must be approved before any
vendoring begins.
