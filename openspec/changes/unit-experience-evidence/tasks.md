# Tasks

Each task names its own verification. Task boxes are ticked at **Archive**, not Apply.

## 1. Capture harness seam

- [ ] 1.1 Add `seed_path: Path = FRESH_PLAYER_SAVE` to `build_disposable()` in `apps/compat-api/capture_legacy_fixtures.py` and read the seed from it instead of the module constant; verify `capture_legacy_fixtures.py` still compiles and its own `--help`/guard path runs
- [ ] 1.2 Confirm **no existing call site changed** by running `git diff` and asserting the diff touches no `capture_*_fixture.py` other than none; verify `git diff --stat` lists exactly one file
- [ ] 1.3 Add the structural pin that keeps the parameter defaulted: walk every `build_disposable(` occurrence under `apps/compat-api/` and fail if any passes a second argument; verify the pin passes today and **fails** when a second argument is temporarily added to one existing call site, then that the site is restored byte-identically

## 2. Executed-legacy capture

- [ ] 2.1 Add `apps/compat-api/capture_unit_xp_fixture.py`, importing `build_disposable`, the request/signing helpers, and the containment digest from `capture_legacy_fixtures.py` rather than re-implementing any of them; verify it compiles
- [ ] 2.2 Seed from `villages/AcidCaos.json` **by keyword argument**, read `playerInfo.pid` from the document, and record the seed digest; verify the disposable save is named from the document's pid and that the digest matches `docs/legacy-unit-xp.md`
- [ ] 2.3 Set `PYTHONUNBUFFERED=1` in **this script's own** child environment only, leaving `child_environment()` untouched; verify the captured log contains the legacy server's request-time `print` lines
- [ ] 2.4 Record the transaction set from `docs/legacy-unit-xp.md` §4: the increment arm, the assign arm, the missing row, the unclamped negative, the unbounded amount, the persisted float, the building row, the ignored third argument, and both failing-type cases; verify each recorded transaction carries request, HTTP status, response body, before-state, after-state, changed-leaf-path set, and stored resources before/after
- [ ] 2.5 Compute the containment digest **before and after** the executed pass with one function over the same traversal recipe; verify the two are identical, `git status --porcelain` is empty, and no working-tree `saves/` exists
- [ ] 2.6 Run the capture **at least three consecutive times** and require identical committed output; record the exit code and containment digest in the fixture README
- [ ] 2.7 Add `tests/fixtures/godot-unit-experience/README.md` and the manifest, recording the seed digest, containment digest, exit code, established-versus-derived split, and the refusal (no award exists, no route is implied)

## 3. Fixture integrity guard (compat)

- [ ] 3.1 Add `apps/compat-api/tests/test_unit_xp_fixture.py` asserting, per recorded transaction, that the changed-leaf set equals the leaf diff **recomputed** from its own before/after states; verify it passes and that deliberately corrupting one recorded leaf set makes it fail
- [ ] 3.2 Assert that every neutral-vector transaction moves exactly the leaves it claims and **no** stored resource, and that the one transaction carrying a non-neutral vector is labelled as such; verify both
- [ ] 3.3 Assert the fixture manifest's digests match the committed fixture bytes, and that the census it records still matches a fresh measurement over the committed save documents; verify both, and that changing one recorded figure makes the census assertion fail
- [ ] 3.4 Assert the repository-wide census figures independently: the field's presence across **all** committed save documents, and that the recorded unit-definition spread, non-integral ratio, and zero overlap with stored player experience still hold; verify each figure is measured in the test, not copied
- [ ] 3.5 Add the anti-invention guard: pin the `compat_service.py` route table and assert no unit-experience path is answered, and pin its whole `static`-function inventory so no award helper can appear; verify by **injecting** a route and then an award helper, confirming independent failures each time, and restoring from a byte-identical copy
- [ ] 3.6 Run `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` and record the observed count against the 2,130 baseline; verify exit `0` and that no pre-existing test changed expectation

## 4. Fail-closed projection

- [ ] 4.1 Add a single named classification helper and a `recorded_kind` field to `production_flow.gd::experience()` over a closed vocabulary, leaving every existing field's meaning unchanged; verify `experience()`'s existing callers still read the same keys
- [ ] 4.2 Cover every vocabulary member, plus the non-dictionary attribute-bag rejection, the absent key, and a string and boolean recorded value, asserting no coercion, conversion, or comparison is applied; verify each case
- [ ] 4.3 Add the structural guard that the module gained no arithmetic and no award helper, following the whole-`static`-inventory precedent; verify by injecting an invented award helper, confirming independent failures, and restoring from a byte-identical copy
- [ ] 4.4 Add `apps/client-godot/tests/test_unit_experience.gd` and register it in `verify-boot.ps1`; verify it runs headless and exits `0`
- [ ] 4.5 Have the suite write the deterministic `unit-experience-report-v1` report under `apps/client-godot/evidence/unit-experience/`, generated from the projection module's own data and the fixture's own recorded manifest; verify the digest is byte-identical across three consecutive runs

## 5. Reason correction

- [ ] 5.1 Correct the two doc comments and the user-facing note string in `apps/client-godot/scripts/town/level_flow.gd`, retaining the corpus figure labelled as a corpus fact and correcting **both** halves of the composite note; verify the note's tutorial half still states that tutorial is delivered
- [ ] 5.2 Correct the stale sentences in `AGENTS.md` and `apps/client-godot/README.md`; verify by re-reading each surrounding block and by `git diff` showing bounded hunks that touch no unrelated line
- [ ] 5.3 Reword the over-broad assertion **message** in `apps/client-godot/tests/test_unit_production.gd` to name its 40-row scope, changing no assertion value, threshold, or intent; verify the suite's check count is unchanged apart from the message text
- [ ] 5.4 Add the tree scan asserting no client source states the corpus-cannot-exercise reason for unit experience, pinning the expected hit count to zero so a change in either direction fails; verify it passes today and fails when a stale sentence is temporarily reintroduced, then that the file is restored byte-identically
- [ ] 5.5 Verify every refusal is still present after the corrections by diffing the corrected text against its previous text and confirming the only changes are the reason and the added census

## 6. Integration verification

- [ ] 6.1 Run `powershell -File apps/client-godot/verify.ps1`; record the observed exit code and the hermetic/live suite counts
- [ ] 6.2 Run `powershell -File apps/client-godot/verify-boot.ps1`; record the observed exit code and the updated hermetic-suite and live-phase counts, and inspect every log for `[test] FAIL`, `^ERROR:`, and `SCRIPT ERROR` lines
- [ ] 6.3 Run `python -B packages/game-content/tools/validate_content.py` and `python -B tools/hash-manifest/hash_manifest.py verify`; record both observed results
- [ ] 6.4 Run `openspec validate --all --strict`; record the passed/failed counts
- [ ] 6.5 Confirm by `git status` that no content package, conversion package, registry manifest, fixture, save, config, village, or legacy-source byte changed
- [ ] 6.6 Record every flaky surface encountered and re-run before treating any failure as a regression; carry the five known flaky surfaces forward unchanged and add any newly observed one