# Proposal

## Why

M4's exit criterion is "at least one authentic building and unit render correctly in Godot," but the repository has no Godot project at all: the asset pipeline produced two validated conversion-v1 packages (`0001_house_1_m`, `10033_wild_elephant`) whose purpose statements explicitly say they exist "so Godot import/rendering work can start from validated inputs." The engine prerequisite (Godot 4.7.2.stable, winget) was installed and pinned in `AGENTS.md` on 2026-09-26, so the only remaining blocker is the minimal render-verification client slice this change creates.

## What Changes

- Create the first Godot project at `apps/client-godot/` (roadmap §15 location): a minimal `project.godot` pinned to Godot 4.7.2, its `README.md` documenting the pinned version, and ignore rules for Godot's generated cache — render verification only, none of M5's game systems (`GameApi`, `LegacyV0Api`, `ContentRegistry`, `Session`, `GameClock`, camera, UI).
- Add a GDScript conversion-v1 package loader that consumes the existing packages **read-only**: envelope/`kind` dispatch, `main` → sprite → shape frame-1 placement walk, `fill_refs` resolution (skipping `65535` placeholders), raw SWF fill-matrix decoding, and JPEG + alpha-PNG compositing into a Godot texture.
- Add a verification scene that renders the house and the elephant side by side on a neutral background, captures the viewport to a PNG, and compares the capture against an independently composited reference built from the package's source bitmaps (dimensions, alpha, pixels within a documented tolerance), exiting non-zero on mismatch.
- Commit the rendered screenshot evidence and comparison report as golden artifacts, and document the actually-executed Godot commands in `AGENTS.md`; update the roadmap Project Status ledger with the M4 exit assessment result.
- Definition of "renders correctly" for this change: the digest-verified legacy bitmaps (verbatim SWF extracts) appear at their authentic package bounds with correct alpha compositing and frame-1 placement resolution, proven by pixel comparison against those source bitmaps. No Flash reference render exists or may be produced (Flash execution is forbidden), so this is explicitly not a claim of pixel parity against a live Flash screen.

## Capabilities

### New Capabilities
- `first-render-in-godot`: loading the two converted conversion-v1 packages in Godot and rendering the authentic building and unit frame-1 output with captured, programmatically compared evidence — the M4 exit slice, without any game systems.

### Modified Capabilities
<!-- none: existing conversion/extraction specs only prohibit rendering and define package outputs; their requirements do not change -->

## Impact

- **Adds**: `apps/client-godot/` (project file, GDScript loader/renderer/verifier, scene, README, evidence outputs), root `.gitignore` entries for Godot-generated caches, `AGENTS.md` commands, roadmap ledger update.
- **Consumes read-only**: `assets/converted/buildings/0001_house_1_m/` and `assets/converted/units/10033_wild_elephant/` (packages are inputs; byte-identity must hold before/after).
- **Requires**: local Godot 4.7.2 binary (already installed and pinned; verification runs a short windowed capture then quits — no network, no server, no Flash/Ruffle/ActionScript).
- **Unchanged**: legacy server, saves, protocol, converters, extraction/inspection manifests, normalized content, existing specs and tests.
- **Dependencies**: no new Python or npm dependencies; comparison logic lives in GDScript using Godot's built-in image decode.
