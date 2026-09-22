## Context

Sound extraction proved the extract-to-`converted/` pipeline for one format in one file. Direct reads characterize all bitmap subformats: JPEG3 with clean zlib alphas, self-contained JPEGs, lossless ARGB and colormap payloads. No image tooling exists yet. This design scopes the fourth M4 slice: bytes in, standard image files out, structure validated. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Per-bitmap outputs: `.jpg` verbatim (with conditional table splice), `_alpha.png` grayscale from decoded alpha, `.png` RGBA from lossless ARGB/colormap via hand-rolled encoder.
- `image_extraction.json` with per-bitmap source tag, family, format, dimensions, output digests, and byte counts; `statuses.json` merge advancing extracted files.
- Stdlib-only extractor/validator with structural, dimensional, re-parse, schema, and determinism guards; unknown formats fail closed.
- Focused tests on synthetic payloads per family and failure, plus real spot checks (JPEG SOI, alpha dims, PNG IHDR re-parse) and determinism.

**Non-Goals:**
- No vector shape conversion, no timeline assembly, no sprite compositing.
- No JPEG decoding to pixels (stdlib has no decoder): JPEG bytes stay verbatim; only the alpha channel and lossless data become PNGs through direct byte mapping.
- No quality judgment, resizing, or re-encoding of JPEG data.
- No registry/coverage/inspection mutation.
- No Godot code or rendering verification of any kind.
- No claim of M4 exit; converted building/unit belong to later slices.

## Decisions

- **Bulk outputs are ignored build artifacts.** `assets/converted/images/` joins `assets/converted/sounds/`' exception: sounds (190 KB, 27 files) stay committed as reviewable evidence while 61k image outputs (~500 MB+) are regenerated deterministically. The committed manifest with per-output digests is the permanent record. Rationale: reviewability and repo size; alternative full commit rejected.
- **Hand-rolled PNG writer, minimal scope.** 8-bit RGBA or grayscale, filter type 0 per scanline, single IDAT; CRC32 via `zlib`. Sufficient for verbatim pixel transport; no ancillary chunks, no interlacing, no palette mode (colormap expanded to RGBA).
- **Alpha validated by dimensions.** Decoded alpha length must equal width×height exactly; JPEG SOI asserted at payload start; PNG outputs re-parsed for signature plus IHDR width/height/type before manifesting.
- **JPEGTables splice implemented but dormant.** Applied only when a JPEG payload lacks SOI; corpus never triggers it, synthetic tests prove it, manifest records splice counts (expected zero).
- **Small domain module.** New extractor beside the registry tools sharing the schemas/tests/README pattern; no new dependencies.

## Risks / Trade-offs

- [Ignored-output drift] → Outputs are reproducible from committed manifest digests; determinism tests plus digest re-verification make silent drift fail closed on rebuild.
- [Colormap fidelity] → Palette expansion to RGBA preserves colors exactly; palette-mode PNGs are deliberately not produced (decoder simplicity over file size).
- [Unknown bitmap formats] → Any format outside {5, 3} lossless or JPEG families fails the build until the slice is extended.
- [Schema/validator drift] → Tests assert every required extraction field has a validator check.

## Migration Plan

Not applicable: new additive tooling plus generated manifest; bulk outputs ignored; no legacy migration, no rollout, no rollback beyond reverting the new files.
