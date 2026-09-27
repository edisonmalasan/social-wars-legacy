# Tasks

## 1. Asset ID registry builder (§20)

- [x] 1.1 Implement `tools/asset-registry/build_asset_ids.py`: re-derive the four reference domains with the documented coverage join rules, classify every distinct reference into the closed status vocabulary from `registry.json` + `conversions.json` + `image_extraction.json`, and write `tools/asset-registry/asset_ids.json` deterministically — verify by running it with pinned CPython (`python -B tools/asset-registry/build_asset_ids.py` exits 0) and running it twice, byte-identical both times.
- [x] 1.2 Add `tools/asset-registry/tests/test_build_asset_ids.py` covering rebuild-to-temp byte equality against the committed file, evidence reconciliation (coverage resolved/missing counts, `converted` ⇔ conversion manifest packages, `extracted` ⇔ recorded bitmap directories, `missing_source` ⇔ coverage missing lists), source-preservation digests, and a tampered-input negative case — verify with `python -B -m unittest discover -s tools/asset-registry/tests -p test_build_asset_ids.py -v` exiting 0.
- [x] 1.3 Document the builder and its test commands in `tools/asset-registry/README.md` (purpose, invocation, evidence classification, containment) and add the verified-command block to `AGENTS.md` — verify the documented commands run exactly as written.

## 2. ContentRegistry autoload and resolution (§19)

- [x] 2.1 Implement `apps/client-godot/scripts/content_registry.gd`: manifest-driven inventory (root + nine extension sections, 22 outputs), byte-count and SHA-256 verification before parse, per-domain `str(legacy_id)` indexing with duplicate rejection, lazy explicit `load_content(base_dir := default)` returning `{ok, error}`, and the lookup API (`domains`/`has`/`get`/`count`/`content_fingerprint`) — verify with the real-package load assertions in `tests/test_content_registry.gd` (counts 470 buildings, 429 units, 91 quests, 607 images, 139 sounds, 105 globals) passing headless.
- [x] 2.2 Add fail-closed and read-only scenarios to `tests/test_content_registry.gd`: altered byte, missing file, and duplicate `legacy_id` against mutated copies under `.godot/` (never the source package), plus a `packages/game-content/` directory digest identical before and after — verify the suite exits 0 with `[test] PASS` headless and its failure scenarios are actually rejected.
- [x] 2.3 Implement asset resolution on the registry (load `asset_ids.json`, `resolve_asset(kind, ref)` per design D5) and add `tests/test_asset_ids.gd` covering vocabulary/count integrity, the converted-sprite and passthrough-sound scenarios, known-but-unavailable vs unknown-kind/unknown-reference errors — verify the suite exits 0 with `[test] PASS` headless.

## 3. Project scope and verification wiring

- [x] 3.1 Update `apps/client-godot/project.godot` (register `ContentRegistry` after `GameApi`) and `apps/client-godot/tests/test_project_scope.gd` (ALLOWED += `scripts/content_registry.gd`, `tests/test_content_registry.gd`, `tests/test_asset_ids.gd`; exactly two expected autoload lines; FORBIDDEN drops `ContentRegistry` with its count assertion 19 → 18; updated doc comments) — verify `tests/test_project_scope.gd` exits 0 with `[test] PASS` headless.
- [ ] 3.2 Extend `apps/client-godot/verify.ps1`: invoke the two new headless suites after the project-scope suite, add `tools/asset-registry/asset_ids.json` to the guarded manifest digests, and add a pre/post directory digest over `packages/game-content/` — verify by running `powershell -File apps/client-godot/verify.ps1` (full battery) exiting 0 with the committed `evidence/first-render/report.json` and `first-render.png` byte-identical afterward.
- [x] 3.3 Update `apps/client-godot/README.md` (suite list, ContentRegistry and asset-ID sections, exact commands, scope boundaries) and the `AGENTS.md` verify.ps1 description (the headless suite set it runs) — verify the documented commands run as written in task 4.

## 4. Full verification battery

- [ ] 4.1 Run the Compatibility API battery: `python -B apps/compat-api/guard_baseline.py verify` (exit 0, combined digest `6978b959…`), `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` (OK), `python -B apps/compat-api/tests/smoke_loopback.py` (PASS) — verify all three exit 0 under pinned CPython 3.9.13.
- [ ] 4.2 Run `powershell -File apps/client-godot/verify-boot.ps1` (PASS exit 0 with guard pre=post) and `powershell -File apps/client-godot/verify.ps1` (PASS exit 0); restore or commit the boot-report provenance churn (`generated_utc`, `git_commit`) and confirm the M4 evidence and every guard baseline are byte-identical — verify `guard_baseline.py verify` still exits 0 afterward and `git diff --check` exits 0.
- [ ] 4.3 Re-run the Python-side checks for this change end to end (`build_asset_ids.py` byte-identical rerun + its unittest) and confirm no working-tree `saves/`, no unintended files, and `git status` showing only the intended change files — verify with explicit `git status --porcelain` review.

## 5. Records

- [ ] 5.1 Append the scenario → executed-check mapping table for all 17 scenarios of the `godot-content-registry` delta plus the 2 scenarios of the modified R1 into `tasks.md`, marking each row with the command or assertion that actually ran and disclosing any gap — verify every row names a check executed in group 4 (or group 1–3 suites re-run there).
- [ ] 5.2 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): §19 and §20 delivered with evidence pointers, the M5 items that remain, and the change lifecycle state — verify the ledger text matches the committed evidence paths and PR chain.
