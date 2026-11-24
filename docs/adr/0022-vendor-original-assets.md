# 0022. Vendor original game assets

**Status:** accepted
**Date:** 2026-11-24
**Owner decision:** the owner rejected the clean-room CC0 motifs as visually inadequate
and directed that the original assets at `C:\Users\Edison\Desktop\socialwarriors` be
retained and used, with a Windows `.exe` as the delivery target.

## Context

[ADR 0021](0021-clean-room-assets.md) chose generated CC0 art and remains accepted for
distributable builds. The owner now wants the original look for a private desktop build.
The original checkout is read-only and was not modified. Its `assets/` tree is 716.8 MB,
of which 620.6 MB is 1,176 Flash `.swf` files; the full converted atlas set is ~32 GB.
Shipping any of that is a rights decision the owner has explicitly made here.

## Decision

1. Vendor a **bounded subset of converted PNG atlas sheets** into
   `apps/client/public/atlases/` (21 sheets, ~84 MB). No SWF, audio or proprietary
   configuration is vendored; no Flash runtime is shipped. The source is the Group D
   conversion of the read-only original checkout; provenance is in the directory README.
2. `apps/client/public/art-mode.json` selects `atlas` mode for this build. The client's
   `frame-manifest.json` already maps items to those sheets, so original art renders
   from server-owned scene state. The renderer anchors and scales converted frames to
   the fixed 760×600 stage.
3. This is a **private-use** build. `docs/LICENSING.md` and the release gate remain in
   force; public redistribution of the proprietary media is not authorised by this ADR.
4. The deliverable is a fresh unsigned Windows NSIS `.exe` built from the existing Tauri
   shell and the bundled authoritative server sidecar. No Flash, no Flask, no browser
   install is required to play.

## Consequences

- The repository now contains Zynga media. GPL v3 on the upstream server code does not
  license it; only the owner accepted that risk.
- Only item ids 1–5 and the starting Command Center have original atlas art. Other items
  may render with missing art until more sheets are vendored.
- The no-Flash gate still holds (converted PNGs are not Flash); the licensing gate stays
  open for public release.
- The default content bundle is unchanged and the server remains authoritative.

## Alternatives

- **CC0-only (ADR 0021):** visually rejected by the owner; still the safe distributable
  default.
- **External path only:** no proprietary bytes in the public repo, but does not produce
  a self-contained `.exe`, which the owner explicitly requested.
- **Full 32 GB atlas set:** exact fidelity but impractical for a desktop installer.
