# Phase 4 — Art Fidelity Assessment (read-only)

**Status:** assessment only. No art was generated, copied, imported or changed for this
document. Any move to ship different art remains a separate, explicitly approved change.

## 1. What is actually available

| Source | Evidence | Distributable? |
|---|---|---|
| Shipped art mode | `apps/client/public/art-mode.json` = `{"mode":"original","licence":"CC0-1.0"}` | Yes — this is clean-room generated art |
| Clean-room asset library | `assets/original/manifest.json` — generator `@swl/art`, licence `CC0-1.0`, statement that no upstream/atlas/proprietary font file was read, traced or copied; **53 files** with SHA-256 digests | Yes |
| Atlas pages from the original game | `apps/client/public/` contains **0** `atlases/` directories; the atlas code path remains functional but unshipped | No — Zynga media |
| Original reference at `C:\Users\Edison\Desktop\socialwarriors` | inspected read-only in Phase 0; contains the original SWF and proprietary config/media | No — private evaluation only |
| Upstream GPL v3 code | vendored, read-only, test fixture | No as runtime; GPL does **not** cover Zynga's sprites, audio or config |

## 2. Application of ADR 21 and the licensing gate

[ADR 0021](../adr/0021-clean-room-assets.md) is **accepted** and requires generated or
dedicated CC0 art with provenance. [`LICENSING.md`](../LICENSING.md) records that the
release gate is still open: "the shipped product contains no Zynga media or runtime files,
and no Zynga code" is a hard condition, and the Zynga art/audio/config must be re-created.
Consequently, **exact sprite fidelity cannot be claimed for any shipped build** without a
new rights decision. The upstream GPL licence is not a licence for the original media.

## 3. Two separate approaches

**Private reference testing (not distributable).** For local, private evaluation only, the
original SWF/atlas material may be used as a visual oracle — the same role the vendored
upstream already has as a test fixture. Nothing from it may be copied into tracked source,
`apps/client/public/`, CI artifacts or any installer. This path can answer "how close is the
composition?" but cannot make a build publishable.

**Distributable art (safe default).** Keep `original` mode and extend the CC0 library only
with deterministic `@swl/art` generators that have provenance entries. Any new motif must be
shown as a visual sample and approved before adoption. No mass generation of unrelated
decorative assets.

## 4. What Phase 1/2 changed and what it did not

Phase 1/2 restored *composition and presentation* — olive/gold chrome, white tutorial bubble,
bottom navigation, one active surface, green isometric ground — using code-generated textures
and existing CC0 motifs. It did **not** copy, trace or import original art, and it does not
close the art/audio/config release gate. Visual fidelity is measured against the reference's
geometry and hierarchy, not against proprietary pixels.

## 5. Recommendation and approval needed

1. Keep the shipped product on CC0-only art (recommended; no change to `art-mode.json`).
2. Defer any new character illustration (the original tutorial character) to a separate
   sample-and-approval step; do not generate it as part of a UI milestone.
3. If exact original art is ever wanted, treat it as a rights decision first: a verified
   licence from the rights holder, plus a new ADR proposal. Do not infer permission from
   the GPL-v3 upstream or from local possession of the SWF.

No visual samples are included in this assessment because none were requested or approved.
