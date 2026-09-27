# Proposal

## Why

The M5 bootstrap slice (§16–§18) is archived, but the Godot client still has no way to read the canonical normalized content package (`packages/game-content/`, all 20 census keys normalized with schemas, manifest, and fingerprints) and no mapping from content asset references to the modern runtime assets produced by the M4 pipeline. Roadmap objectives §19 (ContentRegistry) and §20 (asset ID registry) are the next bounded M5 items: without them the client cannot resolve a building, quest, image, or sound definition to the bytes it should display, and the conversion pipeline's outputs remain invisible to the runtime.

## What Changes

- Add a `ContentRegistry` autoload to `apps/client-godot/` that loads the committed normalized content package read-only from the repository root, driven by `packages/game-content/manifest.json` (22 output files across 10 sections, each with recorded byte count and SHA-256), verifies every file against the manifest before use, indexes each domain by `legacy_id`, and fails closed with an explicit error naming the offending file or domain.
- Add a lookup API on the registry (`domains` / `has` / `get` / `count` / `content_fingerprint`) with explicit not-found results and duplicate-`legacy_id` rejection; no network, transport, or Flash-related reference in any registry code.
- Add an offline builder `tools/asset-registry/build_asset_ids.py` that joins the four content asset-reference domains (images, item sprites, magic sprites, sounds) with the corpus registry and the M4 conversion/extraction evidence, and writes a committed `tools/asset-registry/asset_ids.json` mapping every distinct reference to a runtime status (`converted`, `extracted`, `passthrough`, `pending`, `ambiguous`, `missing_source`) with its runtime path where one truthfully exists.
- Extend the client with asset resolution: the registry loads `asset_ids.json` and answers `resolve_asset(kind, ref)` with the status and runtime path, distinguishing a known-but-unavailable asset from an unknown reference.
- Update the project-scope contract: the allow-list grows by the content-registry script, its tests, and the boot-verification evidence already present; the autoload set becomes exactly `GameApi` + `ContentRegistry`; the forbidden-token list retires `ContentRegistry` while `GameClock`, `Session`, camera, and UI-foundation tokens stay forbidden.
- Extend `verify.ps1` with the two new headless suites and add `asset_ids.json` to its pre/post manifest digests; document the executed commands in `AGENTS.md` and `apps/client-godot/README.md`.
- No changes to the normalized content package, legacy sources, the Compatibility API, its fixtures/guards, the boot scene, the M4 evidence, or any existing asset-registry tool output.

## Capabilities

### New Capabilities

- `godot-content-registry`: the client's canonical content registry — read-only manifest-verified loading of the normalized package, `legacy_id` indexing and lookup semantics, the deterministic asset ID registry that maps content asset references to modern runtime assets, and client-side asset resolution.

### Modified Capabilities

- `first-render-in-godot`: requirement R1 "Minimal render-verification Godot project" — the foundation allow-list grows to include the `ContentRegistry` autoload with its script and tests (and the asset ID registry it loads), the forbidden enumeration drops "content registry" while `GameClock`, camera controls, and UI foundation remain absent, and the project declares exactly two autoloads.

## Impact

- New files: `apps/client-godot/scripts/content_registry.gd`, `apps/client-godot/tests/test_content_registry.gd`, `apps/client-godot/tests/test_asset_ids.gd`, `tools/asset-registry/build_asset_ids.py`, `tools/asset-registry/tests/test_build_asset_ids.py`, `tools/asset-registry/asset_ids.json`.
- Modified files: `apps/client-godot/project.godot` (second autoload), `apps/client-godot/tests/test_project_scope.gd` (allow-list, autoload expectation, forbidden-token list), `apps/client-godot/verify.ps1` (two suite invocations, one guarded manifest, content-package pre/post digest), `apps/client-godot/README.md`, `AGENTS.md`, `tools/asset-registry/README.md` (builder section), `.gitattributes` (worktree-form pins per design D8: the content package in LF, plus `asset_ids.json` and `coverage.json`), `apps/client-godot/evidence/boot/boot-report.json` (provenance refresh from the verification run), and the roadmap Project Status ledger at archive time.
- Read-only inputs: `packages/game-content/` (22 normalized files + `manifest.json`), `tools/asset-registry/{registry,coverage,conversions,image_extraction}.json`, `assets/converted/**`, legacy sources and M4/M5 evidence (SHA-256 guards unchanged).
- Verification: pinned CPython 3.9.13 for the builder and its unittest, headless Godot suites under the pinned 4.7.2.stable engine, `powershell -File apps/client-godot/verify.ps1`, `powershell -File apps/client-godot/verify-boot.ps1`, and `apps/compat-api/guard_baseline.py verify` — all must exit 0 with prior evidence byte-identical.
