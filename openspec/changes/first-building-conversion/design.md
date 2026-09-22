## Context

Extraction slices produce loose bitmap files; nothing yet assembles a per-definition converted package or links shapes to bitmaps. Direct reads show the house file needs only bounds-plus-styles parsing (no tessellation) to become packageable. This design scopes the fifth M4 slice: one building, assembled and linked, rendering deferred. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Converted package `assets/converted/buildings/0001_house_1_m/` with `package.json` (identity, content ref, source provenance, frame data, symbols, shape bounds/style/bitmap-ref records, bitmap outputs with digests, placement tiles) plus bitmap files.
- Stdlib-only shape-style parser (bounds RECT, fill/line arrays, bitmap-fill IDs, raw matrices) with fail-closed version/layout guards.
- `conversions.json` manifest plus `converted` statuses for the source path; bitmap-fill references resolved against extraction outputs.
- Focused tests on synthetic shape records and the real file, plus determinism and containment.

**Non-Goals:**
- No edge-record tessellation, no curve flattening, no rasterization.
- No matrix interpretation (recorded as raw bytes for M5/M6).
- No footprint/collision semantics beyond recording content tile values.
- No unit conversion (separate slice).
- No registry/coverage/inspection/extraction-manifest mutation.
- No Godot code or rendering verification of any kind.
- No claim of M4 exit; the unit counterpart and render verification remain.

## Decisions

- **Package by directory, manifest globally.** Per-building directory holds `package.json` plus bitmap copies (small: one JPEG plus alpha); `conversions.json` at the registry root records every converted package with digests. Rationale: Godot imports directories, reviewers read manifests.
- **Bitmap copies, not references.** The package is self-contained for future Godot import; digests must match extraction outputs byte-for-byte, enforced by the builder.
- **Styles parsed, edges preserved as counts.** Fill/line style arrays fully decoded (types, colors, bitmap IDs, gradient stubs recorded); edge records counted but not tessellated — tessellation is the largest conversion risk and belongs to a needs-driven slice.
- **Content linkage validated, never rebalanced.** The `img_name` lookup must resolve to exactly one normalized building definition; costs/tiles recorded verbatim.
- **Small domain module.** New converter beside the registry tools sharing the schemas/tests/README pattern; no new dependencies.

## Risks / Trade-offs

- [ABC presence] → The house carries ActionScript; scripts are recorded as present (inspection data) and never interpreted — conversion covers static presentation only.
- [Single-frame simplicity] → Multi-frame buildings will need timeline assembly later; this slice proves the package shape, not the general case.
- [Copied bitmap bytes] → Duplication vs extraction outputs is intentional for package self-containment; digest equality enforced.
- [Schema/validator drift] → Tests assert every required package field has a validator check.

## Migration Plan

Not applicable: new additive tooling plus generated package; no legacy migration, no rollout, no rollback beyond reverting the new files.
