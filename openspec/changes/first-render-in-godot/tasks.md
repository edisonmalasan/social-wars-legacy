# Tasks

## 1. Godot project scaffolding

- [x] 1.1 Create `apps/client-godot/` with a minimal `project.godot` for Godot 4.7.2 and a placeholder main scene, then verify `& $godot --headless --path apps/client-godot --quit` exits 0 (boot smoke) and record how the installed executable is located (no `godot` PATH alias exists).
- [x] 1.2 Add ignore rules so Godot's generated cache never commits, then run one editor/headless invocation and verify `git status` reports no `.godot/` or cache files as untracked.
- [x] 1.3 Write `apps/client-godot/README.md` with the pinned engine version (roadmap §15 requirement), project scope boundaries (verification-only, no M5 systems), and how to locate the Godot executable; verify the version string matches `Godot_v4.7.2-stable_win64.exe --version` output `4.7.2.stable.official.ed1daf0bf`.

## 2. Conversion-v1 package loader (GDScript)

- [x] 2.1 Implement envelope parsing with `kind` dispatch and fail-closed errors, and land a headless test (`godot --headless --path apps/client-godot --script res://tests/test_package_loader.gd`) that passes on both real packages (asserting `converted_building`/`converted_unit`, legacy ids, content_version, bitmap file resolution) and exits non-zero on a mutated/foreign envelope with an error naming the package.
- [x] 2.2 Implement frame-1 placement resolution (`main` → sprites → shapes, `fill_refs` selection, missing-`character_id` failure), and extend the headless test to assert the house resolves to its single 216×144 shape, the elephant resolves its frame-1 chain from sprite 63 with every `65535` placeholder excluded, and a package with a broken placement chain fails naming sprite and character id.
- [x] 2.3 Implement raw SWF fill-matrix decoding with the bounds↔bitmap oracle, and extend the headless test to assert the house matrix maps 4320×2880 twips onto 216×144 px within 1 px and that elephant matrices with translate components decode to non-zero translation; a decode that breaks the oracle must fail the test.
- [x] 2.4 Implement JPEG + alpha-PNG compositing into a straight-alpha Godot `Image`, and extend the headless test to assert composite dimensions equal the source JPEG dimensions and the alpha channel is honored; record the empirical straight-vs-premultiplied finding in `apps/client-godot/README.md`.
- [x] 2.5 Add SHA-256 pre/post digest capture for both package directories around loader operations, and verify the test run reports identical digests before and after (read-only guarantee).

## 3. Render scene and capture

- [x] 3.1 Build the verification scene (neutral background, house and elephant nodes constructed from the loader at authentic bounds), and land a headless scene-build test asserting both packages build, node bounds match package bounds, and textures load at authentic dimensions without any display.
- [x] 3.2 Implement viewport capture to `apps/client-godot/evidence/first-render/first-render.png`, then run the scene windowed and verify the PNG exists, has the expected scene dimensions, and visibly shows both entities; confirm the window auto-quits.

## 4. Comparison, report, and evidence

- [x] 4.1 Implement the independent reference compositor and 1:1 comparator writing `evidence/first-render/report.json` (per-channel metrics, alpha metrics, failing-pixel counts, engine version, input digests, tolerance), and verify a headless compare of the committed capture against the source-composite reference exits 0.
- [x] 4.2 Land the comparator self-test with a deliberately perturbed reference, and verify it runs headless, exits non-zero, and records the deviation and affected pixels in its report.
- [x] 4.3 Calibrate the documented tolerance from real capture metrics (AA/rasterization rationale), then verify the real report passes within it and the tolerance values plus rationale are written into `apps/client-godot/README.md`.
- [x] 4.4 Verify a full verification run leaves every package/manifest digest unchanged (pre/post equality asserted by the command itself, not manually).

## 5. Integration, commands, and records

- [x] 5.1 Provide the single documented verification command `powershell -File apps/client-godot/verify.ps1` (locate Godot → pre-digests → capture run → self-test → compare → post-digests → exit code) and verify it exits 0 twice in a row on the same machine (reproducibility scenario).
- [x] 5.2 Land a project-scope check asserting no game-system autoload/scene/script exists in `apps/client-godot/`, and verify it runs as part of the verification command.
- [x] 5.3 Update `AGENTS.md` with the Godot commands actually executed and evidence paths, complete `apps/client-godot/README.md` (evidence locations, correctness-claim limits — source-bitmap fidelity, not live-Flash parity — display-session constraint), and verify both documents' commands run exactly as written from a clean state.
- [x] 5.4 Commit the evidence (`first-render.png`, `report.json`), run every test added by this change plus the full existing asset-registry suite under pinned CPython 3.9.13, and verify all pass, `git diff --check` is clean, and no source/package bytes changed.
- [ ] 5.5 Update the roadmap Project Status ledger with the M4 exit assessment result and pointers to the committed evidence; verify the ledger statement matches the actual report contents.
