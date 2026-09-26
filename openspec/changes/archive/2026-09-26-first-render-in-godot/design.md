# Design

## Context

Two conversion-v1 packages exist as committed, schema-validated inputs (`assets/converted/buildings/0001_house_1_m/`, `assets/converted/units/10033_wild_elephant/`), and Godot 4.7.2.stable is installed and pinned in `AGENTS.md`. There is no Godot project yet; `apps/` does not exist. Grounding facts from the packages that shape this design:

- Every shape in both packages is a pure rectangle: house `straight=4, curved=0, lines=0`; all 28 elephant shapes likewise. Edge coordinates are intentionally absent (the converters' documented "no tessellation" boundary) — only `bounds`, `records` counts, and fills are stored.
- The house bitmap is exactly 216×144 px = its shape bounds in px (4320×2880 twips), so bitmap ↔ bounds are 1:1.
- Fills are raw SWF clipped-bitmap fills (`type: 65`) with the fill matrix preserved as hex (house: `d9400005000000`; elephant has longer matrices with translate), plus a `65535` placeholder for unreferenced fills selected around via `fill_refs`.
- The unit's `main` places sprite 63 (frame 1 → shapes); placements carry only `character_id`, `character_kind`, `depth`, `frame`, `move` — no transform fields, so frame-1 resolution uses identity transforms.
- Bitmaps are JPEG3 splits: `<id>.jpg` color + `<id>_alpha.png` alpha.
- No reference screenshots of the live Flash game exist in the repo, and Flash execution is forbidden — the verbatim-extracted, digest-verified bitmaps are the only available ground truth.

## Goals / Non-Goals

**Goals:**
- A minimal, reproducible Godot slice that renders the authentic house and elephant frame-1 output and proves it programmatically with committed evidence.
- A single documented verification command with a meaningful exit code (usable as a regression check later).
- Byte-identical preservation of every input before/after runs.

**Non-Goals:**
- M5 game systems (`GameApi`, `LegacyV0Api`, `ContentRegistry`, `Session`, `GameClock`, camera, UI), boot flow, or any backend/protocol work.
- Timeline/animation playback (frames > 1), interactive placement, or multi-entity scene management (M6).
- Vector edge decoding or tessellation — packages contain no edge data by preservation design; changing converters is out of scope.
- Pixel-parity claims against a live Flash render (unavailable by policy).

## Decisions

**D1 — Project location: new `apps/client-godot/`.**
Roadmap §15 already assigns `apps/client-godot/README.md` as the place to document the pinned version, so the exit slice and the eventual M5 project share one home. Alternatives: a throwaway project outside the repo (rejected: evidence and commands would not be reproducible from a clean clone) or `tools/` (rejected: it is not a tool).

**D2 — Asset access: runtime loading, not Godot resource import.**
Packages live outside the project directory (`assets/converted/...` at repo root), which `res://` import cannot reach without copying files into the project — copies would violate the read-only/byte-identity discipline. The loader reads `package.json` via `FileAccess` and decodes bitmaps via `Image.load_jpg_from_buffer` / `load_png_from_buffer`, resolving package paths from an explicit argument or from the project path (`ProjectSettings.globalize_path("res://")` + `../../assets/converted/...`). Consequence: no `.import` sidecars for these assets, and `--headless --import` is not a required step; Godot's generated `.godot/` cache stays ignored.

**D3 — Render primitive: bounds-quad with decoded fill matrix.**
Since every shape is a straight-only rectangle whose bitmap is 1:1 with its bounds, drawing the shape bounds as a textured quad is geometrically exact, with silhouette coming from the JPEG3 alpha — the same pixels Flash embedded. Alternatives: SWF edge tessellation (rejected: edge data is not in the packages and would require converter changes forbidden by this change's scope) or displaying raw JPEGs without geometry (rejected: it would bypass bounds, matrix, and placement resolution — the very things the exit criterion is about).

**D4 — Fill-matrix decode with an oracle.**
The hex matrices are raw SWF `Matrix` records (hasScale/hasRotate flags + fixed-point fields + translate). They are decoded per the SWF layout and validated by an explicit oracle: the matrix mapped over the shape bounds must equal the bitmap's pixel dimensions within 1 px (house: 4320×2880 twips → 216×144 px). The verification report records this check so a decode bug fails the run instead of silently shifting UVs. Assuming identity is rejected — elephant fills include translate components (`...0ac36d90`).

**D5 — Alpha: straight, composited in Godot `Image`.**
DefineBitsJPEG3 stores color and alpha independently (unlike Lossless2's premultiplied data), so the compositor writes `(jpg.rgb, alpha.png)` straight-alpha pixels into a texture. The comparison against the same source pair makes a premultiplied mistake visible as edge halos/metric failures; the empirical result is recorded in the README.

**D6 — Verification architecture: one Godot run = render → capture → compare → report → exit code.**
The scene builds house + elephant nodes, waits for a rendered frame, captures the viewport (`get_viewport().get_texture().get_image()`), composites the reference in-memory from the same source files, compares at 1:1 with a documented per-channel/alpha tolerance, writes `apps/client-godot/evidence/first-render/{first-render.png,report.json}`, and quits with 0/1. Godot is used because it natively decodes JPEG and PNG — a Python comparator would need a new dependency (stdlib cannot decode JPEG), which is out of policy. The comparator is a separate script so the self-test (perturbed reference → non-zero) can run headless without a display.

**D7 — Capture needs a real rendering context; comparison does not.**
Viewport capture requires an actual renderer, so the documented verify command runs a brief windowed session (small window, auto-quit after capture) on an interactive desktop. Comparison and self-test are CPU-side `Image` operations and run under `--headless`. If no display session exists, capture cannot run — documented as an environment constraint rather than hidden.

**D8 — Evidence handling.**
Committed: `first-render.png` (one screenshot, tens of KB) and `report.json` (metrics, tolerances, engine version, input digests) under `apps/client-godot/evidence/first-render/`, deliberately outside the ignored `assets/converted/images/` bulk path. Ignored: `.godot/`, editor caches. Determinism claim is "both runs pass with metrics inside tolerance," not byte-identical PNGs (GPU rasterization may vary by driver).

**D9 — Scope guard: pre/post digest check.**
The verification command (and its tests) computes SHA-256 of both package directories before and after, asserting equality — the same preservation discipline the converters use — so "read-only" is enforced mechanically, not by convention.

## Risks / Trade-offs

- [Windowed capture requires an interactive display; agents/CI without one cannot verify] → Comparison self-test runs headless; the display requirement is documented as an explicit environment constraint in README/AGENTS; the run auto-quits to keep the window transient.
- [SWF matrix decode error shifts UVs] → Bounds↔bitmap oracle (D4) recorded in `report.json`; failure exits non-zero; screenshot is reviewable by a human.
- [Alpha straight-vs-premultiplied assumption wrong] → Same-reference comparison exposes edge halos as metric failures; empirical finding recorded (D5).
- [GPU/AA nondeterminism across machines] → Tolerance-based metrics with failing-pixel counts instead of byte-identity; tolerance values documented with rationale (D8).
- [Godot editor generates files (`.uid`, `.godot/`) that churn] → `.godot/` ignored; any committed project files are added deliberately and reviewed in the PR diff; cache never enters evidence.
- [Scope creep toward M5] → The minimal-project requirement (spec R1) and the non-goals above bound it; game-system absence is asserted by a project-config check.
- ["Correctly" over-claimed] → The spec and README state exactly what is proven (authentic source-bitmap fidelity at authentic bounds/placement) and what is not (live-Flash screen parity).

## Migration Plan

Additive change: no deployment, no rollback concern. Removing `apps/client-godot/` plus its `.gitignore`/docs entries fully reverts it. Inputs are never modified, so no data migration exists.

## Open Questions

None blocking. The alpha convention (D5) and exact tolerance values are resolved empirically during implementation and recorded in the evidence/README without changing the specs, approach, or task breakdown.
