# Tasks

## 1. Asset ID registry builder (§20)

- [x] 1.1 Implement `tools/asset-registry/build_asset_ids.py`: re-derive the four reference domains with the documented coverage join rules, classify every distinct reference into the closed status vocabulary from `registry.json` + `conversions.json` + `image_extraction.json`, and write `tools/asset-registry/asset_ids.json` deterministically — verify by running it with pinned CPython (`python -B tools/asset-registry/build_asset_ids.py` exits 0) and running it twice, byte-identical both times.
- [x] 1.2 Add `tools/asset-registry/tests/test_build_asset_ids.py` covering rebuild-to-temp byte equality against the committed file, evidence reconciliation (coverage resolved/missing counts, `converted` ⇔ conversion manifest packages, `extracted` ⇔ recorded bitmap directories, `missing_source` ⇔ coverage missing lists), source-preservation digests, and a tampered-input negative case — verify with `python -B -m unittest discover -s tools/asset-registry/tests -p test_build_asset_ids.py -v` exiting 0.
- [x] 1.3 Document the builder and its test commands in `tools/asset-registry/README.md` (purpose, invocation, evidence classification, containment) and add the verified-command block to `AGENTS.md` — verify the documented commands run exactly as written.

## 2. ContentRegistry autoload and resolution (§19)

- [x] 2.1 Implement `apps/client-godot/scripts/content_registry.gd`: manifest-driven inventory (root + nine extension sections, 22 outputs), byte-count and SHA-256 verification before parse, per-domain `str(legacy_id)` indexing with duplicate rejection, lazy explicit `load_content(base_dir := default)` returning `{ok, error}`, and the lookup API (`domains`/`has`/`get`/`count`/`content_fingerprint`) — verify with the real-package load assertions in `tests/test_content_registry.gd` (counts 470 buildings, 429 units, 91 quests, 607 images, 139 sounds, 105 globals) passing headless.
- [x] 2.2 Add fail-closed and read-only scenarios to `tests/test_content_registry.gd`: altered byte, missing file, unparseable content (invalid JSON with the copy manifest re-pointed so verification passes and the parse layer fails), and duplicate `legacy_id` against mutated copies under `.godot/` (never the source package), plus a `packages/game-content/` directory digest identical before and after — verify the suite exits 0 with `[test] PASS` headless and its failure scenarios are actually rejected.
- [x] 2.3 Implement asset resolution on the registry (load `asset_ids.json`, `resolve_asset(kind, ref)` per design D5) and add `tests/test_asset_ids.gd` covering vocabulary/count integrity, the converted-sprite and passthrough-sound scenarios, known-but-unavailable vs unknown-kind/unknown-reference errors — verify the suite exits 0 with `[test] PASS` headless.

## 3. Project scope and verification wiring

- [x] 3.1 Update `apps/client-godot/project.godot` (register `ContentRegistry` after `GameApi`) and `apps/client-godot/tests/test_project_scope.gd` (ALLOWED += `scripts/content_registry.gd`, `tests/test_content_registry.gd`, `tests/test_asset_ids.gd`; exactly two expected autoload lines; FORBIDDEN drops `ContentRegistry` with its count assertion 19 → 18; updated doc comments) — verify `tests/test_project_scope.gd` exits 0 with `[test] PASS` headless.
- [x] 3.2 Extend `apps/client-godot/verify.ps1`: invoke the two new headless suites after the project-scope suite, add `tools/asset-registry/asset_ids.json` to the guarded manifest digests, and add a pre/post directory digest over `packages/game-content/` — verify by running `powershell -File apps/client-godot/verify.ps1` (full battery) exiting 0 with the committed `evidence/first-render/report.json` and `first-render.png` byte-identical afterward. *(Verified: full run PASS exit 0, `[verify] ok content package bytes unchanged: packages/game-content` and `manifest bytes unchanged: .../asset_ids.json`, `git status --porcelain` empty afterward.)*
- [x] 3.3 Update `apps/client-godot/README.md` (suite list, ContentRegistry and asset-ID sections, exact commands, scope boundaries) and the `AGENTS.md` verify.ps1 description (the headless suite set it runs) — verify the documented commands run as written in task 4.

## 4. Full verification battery

- [x] 4.1 Run the Compatibility API battery: `python -B apps/compat-api/guard_baseline.py verify` (exit 0, combined digest `6978b959…`), `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` (OK), `python -B apps/compat-api/tests/smoke_loopback.py` (PASS) — verify all three exit 0 under pinned CPython 3.9.13. *(All three ran and exited 0; guard digest `6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348` observed.)*
- [x] 4.2 Run `powershell -File apps/client-godot/verify-boot.ps1` (PASS exit 0 with guard pre=post) and `powershell -File apps/client-godot/verify.ps1` (PASS exit 0); restore or commit the boot-report provenance churn (`generated_utc`, `git_commit`) and confirm the M4 evidence and every guard baseline are byte-identical — verify `guard_baseline.py verify` still exits 0 afterward and `git diff --check` exits 0. *(Both PASS; churn committed as `test: refresh boot verification evidence for content registry`; guard re-verified OK afterward; `git diff --check` exit 0; hash-manifest `verify` exit 0 over 3,258 entries; first-render report/PNG byte-identical.)*
- [x] 4.3 Re-run the Python-side checks for this change end to end (`build_asset_ids.py` byte-identical rerun + its unittest) and confirm no working-tree `saves/`, no unintended files, and `git status` showing only the intended change files — verify with explicit `git status --porcelain` review. *(Builder rerun output hash equal before/after `1a04b2ce517a53d8…`; 19/19 unittest OK; `saves/` absent; `git status --porcelain` empty.)*

## 5. Records

- [x] 5.1 Append the scenario → executed-check mapping table for all scenarios of the `godot-content-registry` delta plus the scenarios of the modified R1 into `tasks.md`, marking each row with the command or assertion that actually ran and disclosing any gap — verify every row names a check executed in group 4 (or group 1–3 suites re-run there). *(Count correction during Apply: the committed delta carries 18 scenarios, not the 17 estimated here at proposal time; the table below covers all 18 + 2.)*

### 5.1 Scenario → executed-check mapping

Every row names a check executed during the group-4 battery, or a group 1–3
suite re-run inside it. Headless Godot suites all ran both directly and
inside `verify.ps1`; Python checks ran under pinned CPython 3.9.13.

#### `godot-content-registry` delta — ADDED (18 scenarios)

| # | Scenario | Executed check | Observed result |
|---|----------|----------------|-----------------|
| 1 | Load the canonical package | `verify.ps1` → `test_content_registry.gd` real-package load: all 22 outputs verified against recorded byte counts/SHA-256, counts 470 buildings / 429 units / 91 quests / 607 images / 139 sounds / 105 globals, package digest pre/post | `[test] PASS checks=52`; `[verify] ok content package bytes unchanged` |
| 2 | Fail closed on altered content | Same suite, four fault classes against mutated copies under `.godot/verify/content/`: Fault A (same-length byte flip) → SHA-256 error naming `buildings.json`; Fault B (deleted `quests.json`) → explicit missing-file error; Fault D (invalid JSON in `sounds.json` with the copy manifest re-pointed so verification passes) → parse error naming `sounds.json` with no partial package served; Fault C (duplicate `legacy_id`) → rejected by domain — `{ok:false}` throughout, registry never marked loaded | Covered by PASS 52 (each failure asserted) |
| 3 | Read-only containment | Same suite: `packages/game-content/` directory digest before/after identical; `verify.ps1` independent pre/post guard; `test_project_scope.gd` forbidden-token scan over all `.gd`/`.tscn` sources | pre=post `787061adc3c8aa54…` over 65 files; 26 sources scanned, no hits |
| 4 | Look up known definitions | Same suite: building `legacy_id 1`, the first quest, and the first sound each return `found` with JSON round-trip equality against their exact stored file entries; reported counts match manifest-verified totals | Covered by PASS 52 |
| 5 | Report unknown references explicitly | Same suite: unknown domain and unknown `legacy_id` → explicit not-found result, registry state unchanged | Covered by PASS 52 |
| 6 | Reject duplicate identifiers | Same suite: Fault C (duplicate `legacy_id` in `categories.json` copy + copy manifest repointed) → load fails, error names the domain, no partial index | Covered by PASS 52 |
| 7 | Map every reference | `python -B tools/asset-registry/build_asset_ids.py` (exit 0) + `python -B -m unittest discover -s tools/asset-registry/tests -p test_build_asset_ids.py -v` incl. `test_pinned_status_counts` over 1,627 entries (converted 2, extracted 872, passthrough 654, pending 7, ambiguous 50, missing_source 42) | builder exit 0; 19/19 OK |
| 8 | Rerun determinism | Builder run twice with equal output SHA-256 `1a04b2ce517a53d8…`; unittest `test_rerun_is_byte_identical`, `test_rebuild_matches_committed_bytes` | same=True; 19/19 OK |
| 9 | Reconcile with committed evidence | Unittest `test_counts_reconcile_with_coverage`, `test_converted_entries_equal_conversion_packages`, `test_extracted_entries_derive_from_extraction_manifest`, `test_missing_lists_equal_coverage_missing_lists`, `test_reference_counts_sum_to_coverage_references`, `test_rules_match_coverage_rules` | 19/19 OK |
| 10 | Build without side effects | Unittest `test_sources_unchanged_by_build`, `test_output_file_is_the_only_write`, failure cases `test_tampered_coverage_fails_without_writing` / `test_missing_conversions_exits_2_without_writing` / `test_tampered_normalized_reference_exits_2_without_writing` | 19/19 OK |
| 11 | Resolve a converted sprite | `verify.ps1` → `test_asset_ids.gd`: `0001_house_1_m` → status `converted`, package path recorded and exists on disk | `[test] PASS checks=50` |
| 12 | Resolve a passthrough sound | Same suite: passthrough sound → corpus MP3 path, `source` equals the runtime path, and the file's own SHA-256 (`Paths.file_sha256`) equals the entry's recorded `source_sha256` | Covered by PASS 50 |
| 13 | Distinguish unavailable from unknown | Same suite: known `missing_source` sprite reports status with no runtime path; unknown kind and absent reference produce explicit errors | Covered by PASS 50 |
| 14 | Scope enforces the new boundary | `verify.ps1` → `test_project_scope.gd`: 35 files allow-listed, exactly `GameApi` + `ContentRegistry` autoload lines, 18 forbidden tokens absent (incl. `GameClock`, `Session`, camera, UI foundation, legacy protocol, non-loopback) | `[test] PASS checks=585` |
| 15 | Keep M4 and M5 green | `powershell -File apps/client-godot/verify-boot.ps1` and `powershell -File apps/client-godot/verify.ps1` full runs; first-render `report.json`/`first-render.png` byte-identical after (`git status --porcelain` empty) | both PASS exit 0; guard pre=post `6978b959…` |
| 16 | No guarded bytes move | `guard_baseline.py verify` before and after the battery; `hash_manifest.py verify`; `verify.ps1` pre/post guards over both conversion packages, `conversions.json`/`inspection.json`/`image_extraction.json`, `asset_ids.json`, and `packages/game-content/`; builder preservation tests | all exit 0; all guards report unchanged |
| 17 | Record the executed commands | Docs committed in this change: `AGENTS.md` verified-command blocks (asset-ID registry + updated `verify.ps1` description), `tools/asset-registry/README.md` asset-ID section, `apps/client-godot/README.md` (five-suite list with observed counts) — each command listed is one executed above | docs committed; commands executed as written |
| 18 | Record the milestone progress | **GAP (deferred by design):** the roadmap Project Status ledger update is task 5.2 and executes in the Archive stage, after this verification; this row is discharged by the archive PR's ledger text | deferred to Archive (disclosed) |

#### `first-render-in-godot` — R1 MODIFIED (2 scenarios)

| # | Scenario | Executed check | Observed result |
|---|----------|----------------|-----------------|
| 19 | Boot with the pinned engine | `verify.ps1` windowed run with pinned `4.7.2.stable` (report/PNG written, compare PASS) + `verify-boot.ps1` main-scene boot reporting `state=ready`, engine `4.7.2`, protocol `compat-v0` | both PASS exit 0 |
| 20 | Remain within the verification scope | `test_project_scope.gd` (allow-list incl. the new content-registry files, exactly the two autoloads, no camera/UI/clock, no legacy tokens, first-render scene/tests intact) + `verify.ps1` comparator self-test and headless compare | `[test] PASS checks=585`; self-test DETECTED as expected; compare PASS |
- [ ] 5.2 Update the roadmap Project Status ledger (`docs/DEVELOPMENT_ROADMAP.md`, root-orchestrator-owned): §19 and §20 delivered with evidence pointers, the M5 items that remain, and the change lifecycle state — verify the ledger text matches the committed evidence paths and PR chain.
