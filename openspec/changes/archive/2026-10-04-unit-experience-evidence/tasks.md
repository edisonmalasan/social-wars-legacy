# Tasks

Each task names its own verification. Task boxes are ticked at **Archive**, not Apply.

## 1. Capture harness seam

- [x] 1.1 Add `seed_path: Path = FRESH_PLAYER_SAVE` to `build_disposable()` in `apps/compat-api/capture_legacy_fixtures.py` and read the seed from it instead of the module constant; verify `capture_legacy_fixtures.py` still compiles and its own `--help`/guard path runs
- [x] 1.2 Confirm **no existing call site changed** by running `git diff` and asserting the diff touches no `capture_*_fixture.py` other than none; verify `git diff --stat` lists exactly one file
- [x] 1.3 Add the structural pin that keeps the parameter defaulted: walk every `build_disposable(` occurrence under `apps/compat-api/` and fail if any passes a second argument; verify the pin passes today and **fails** when a second argument is temporarily added to one existing call site, then that the site is restored byte-identically

## 2. Executed-legacy capture

- [x] 2.1 Add `apps/compat-api/capture_unit_xp_fixture.py`, importing `build_disposable`, the request/signing helpers, and the containment digest from `capture_legacy_fixtures.py` rather than re-implementing any of them; verify it compiles
- [x] 2.2 Seed from `villages/AcidCaos.json` **by keyword argument**, read `playerInfo.pid` from the document, and record the seed digest; verify the disposable save is named from the document's pid and that the digest matches `docs/legacy-unit-xp.md`
- [x] 2.3 Set `PYTHONUNBUFFERED=1` in **this script's own** child environment only, leaving `child_environment()` untouched; verify the captured log contains the legacy server's request-time `print` lines
- [x] 2.4 Record the transaction set from `docs/legacy-unit-xp.md` §4: the increment arm, the assign arm, the missing row, the unclamped negative, the unbounded amount, the persisted float, the building row, the ignored third argument, and both failing-type cases; verify each recorded transaction carries request, HTTP status, response body, before-state, after-state, changed-leaf-path set, and stored resources before/after
- [x] 2.5 Compute the containment digest **before and after** the executed pass with one function over the same traversal recipe; verify the two are identical, `git status --porcelain` is empty, and no working-tree `saves/` exists
- [x] 2.6 Run the capture **at least three consecutive times** and require identical committed output; record the exit code and containment digest in the fixture README
- [x] 2.7 Add `tests/fixtures/godot-unit-experience/README.md` and the manifest, recording the seed digest, containment digest, exit code, established-versus-derived split, and the refusal (no award exists, no route is implied)

## 3. Fixture integrity guard (compat)

- [x] 3.1 Add `apps/compat-api/tests/test_unit_xp_fixture.py` asserting, per recorded transaction, that the changed-leaf set equals the leaf diff **recomputed** from its own before/after states; verify it passes and that deliberately corrupting one recorded leaf set makes it fail
- [x] 3.2 Assert that every neutral-vector transaction moves exactly the leaves it claims and **no** stored resource, and that the one transaction carrying a non-neutral vector is labelled as such; verify both
- [x] 3.3 Assert the fixture manifest's digests match the committed fixture bytes, and that the census it records still matches a fresh measurement over the committed save documents; verify both, and that changing one recorded figure makes the census assertion fail
- [x] 3.4 Assert the repository-wide census figures independently: the field's presence across **all** committed save documents, and that the recorded unit-definition spread, non-integral ratio, and zero overlap with stored player experience still hold; verify each figure is measured in the test, not copied
- [x] 3.5 Add the anti-invention guard: pin the `compat_service.py` route table and assert no unit-experience path is answered, and pin its whole `static`-function inventory so no award helper can appear; verify by **injecting** a route and then an award helper, confirming independent failures each time, and restoring from a byte-identical copy
- [x] 3.6 Run `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` and record the observed count against the 2,130 baseline; verify exit `0` and that no pre-existing test changed expectation

## 4. Fail-closed projection

- [x] 4.1 Add a single named classification helper and a `recorded_kind` field to `production_flow.gd::experience()` over a closed vocabulary, leaving every existing field's meaning unchanged; verify `experience()`'s existing callers still read the same keys
- [x] 4.2 Cover every vocabulary member, plus the non-dictionary attribute-bag rejection, the absent key, and a string and boolean recorded value, asserting no coercion, conversion, or comparison is applied; verify each case
- [x] 4.3 Add the structural guard that the module gained no arithmetic and no award helper, following the whole-`static`-inventory precedent; verify by injecting an invented award helper, confirming independent failures, and restoring from a byte-identical copy
- [x] 4.4 Add `apps/client-godot/tests/test_unit_experience.gd` and register it in `verify-boot.ps1`; verify it runs headless and exits `0`
- [x] 4.5 Have the suite write the deterministic `unit-experience-report-v1` report under `apps/client-godot/evidence/unit-experience/`, generated from the projection module's own data and the fixture's own recorded manifest; verify the digest is byte-identical across three consecutive runs

## 5. Reason correction

- [x] 5.1 Correct the two doc comments and the user-facing note string in `apps/client-godot/scripts/town/level_flow.gd`, retaining the corpus figure labelled as a corpus fact and correcting **both** halves of the composite note; verify the note's tutorial half still states that tutorial is delivered
- [x] 5.2 Correct the stale sentences in `AGENTS.md` and `apps/client-godot/README.md`; verify by re-reading each surrounding block and by `git diff` showing bounded hunks that touch no unrelated line
- [x] 5.3 Reword the over-broad assertion **message** in `apps/client-godot/tests/test_unit_production.gd` to name its 40-row scope, changing no assertion value, threshold, or intent; verify the suite's check count is unchanged apart from the message text
- [x] 5.4 Add the tree scan asserting no client source states the corpus-cannot-exercise reason for unit experience, pinning the expected hit count to zero so a change in either direction fails; verify it passes today and fails when a stale sentence is temporarily reintroduced, then that the file is restored byte-identically
- [x] 5.5 Verify every refusal is still present after the corrections by diffing the corrected text against its previous text and confirming the only changes are the reason and the added census

## 6. Integration verification

- [x] 6.1 Run `powershell -File apps/client-godot/verify.ps1`; record the observed exit code and the hermetic/live suite counts
- [x] 6.2 Run `powershell -File apps/client-godot/verify-boot.ps1`; record the observed exit code and the updated hermetic-suite and live-phase counts, and inspect every log for `[test] FAIL`, `^ERROR:`, and `SCRIPT ERROR` lines
- [x] 6.3 Run `python -B packages/game-content/tools/validate_content.py` and `python -B tools/hash-manifest/hash_manifest.py verify`; record both observed results
- [x] 6.4 Run `openspec validate --all --strict`; record the passed/failed counts
- [x] 6.5 Confirm by `git status` that no content package, conversion package, registry manifest, fixture, save, config, village, or legacy-source byte changed
- [x] 6.6 Record every flaky surface encountered and re-run before treating any failure as a regression; carry the five known flaky surfaces forward unchanged and add any newly observed one

## Verification record

Observed on 2026-10-04 against pinned CPython 3.9.13 and Godot 4.7.2.stable, Windows x64.

| check | observed |
|---|---|
| `capture_unit_xp_fixture.py` | exit `0`; 12 transactions, 12 disposables, 12 servers; containment digest `18e5e55b…a724` identical before and after; no working-tree `saves/`; all 17 prior fixtures byte-unchanged; loopback `127.0.0.1:5055` only; three consecutive runs byte-identical except the three documented time-dependent fields |
| compat suite | `Ran 2187 tests … OK`, exit `0`, against the 2,130 baseline (**+57**) |
| `test_unit_experience.gd` | **2,432 checks**, exit `0` (2,430 without `--report`) |
| report determinism | `unit-experience-report-v1`, **byte-identical across three consecutive runs** |
| `verify.ps1` | exit `0`, `PASS all checks succeeded`, zero `ERROR:` / `SCRIPT ERROR` markers |
| `verify-boot.ps1` | exit `0`, `PASS all checks succeeded`; guard digest `6978b959…ff348` identical pre/post; **636 log files inspected, zero** `ERROR:` / `SCRIPT ERROR` / `[test] FAIL`; port 5056 released; no working-tree `saves/` |
| `validate_content.py` | exit `0`, `result: valid`, 22 files / 21 schemas / 604 references |
| `hash_manifest.py verify` | exit `0`, 3,258 entries |
| `openspec validate --all --strict` | **61 passed / 0 failed** at Apply; **62 / 0** after Sync, the new capability being a new spec item |

**Every guard was proven by injection with a byte-identical restore**, not observed to pass:

| injection | result |
|---|---|
| `@app.post("/v0/unit_xp")` inside `create_app` | 2 failures, exit `1` |
| `def award_xp_for_level(level)` in the service | 1 failure, exit `1` |
| a second `build_disposable(…, SEED_SAVE)` argument | 1 failure, exit `1` |
| corrupt one recorded leaf path in a step `transaction.json` | 4 failures, exit `1` |
| corrupt one leaf path in `capture-manifest.json` | 1 failure, exit `1` |
| revert the fixture README inventory numbers | 1 failure, exit `1` |
| change a recorded census figure `36` → `35` | 1 failure, exit `1` |
| append a numeric-interpretation helper to `production_flow.gd` | 3 failures, exit `1` |
| reintroduce the stale corpus reason in `town.gd` | 2 failures, exit `1` |

## Newly observed surface (task 6.6)

The five known flaky surfaces carry forward unchanged. **One new surface was observed, and it
is a latent sensitivity in `test_project_scope.gd` rather than a defect this line introduced.**

`test_project_scope.gd` walks the Godot project tree and requires every file to be either
tracked-and-allow-listed or absent, and it does **not** honour `.gitignore`. A gitignored
`apps/client-godot/__pycache__/compat_live_phase.cpython-39.pyc` therefore failed the suite even
though nothing tracked had changed.

The obvious hypothesis — that `verify-boot.ps1` executes the committed helper without `-B` — is
**false, and was measured rather than assumed**: `verify-boot.ps1:847` passes `-B`, every documented
invocation in `apps/client-godot/README.md` passes `-B`, and after deleting the artifact a **full**
battery run did not recreate it. The bytecode therefore came from an ad-hoc invocation without `-B`
outside the battery.

The artifact was **deleted**, not worked around, and the suite was re-run to a pass (1,798 checks).
Weakening the suite to tolerate ignored bytecode would defeat the check. Recorded as a follow-up:
either have the scope walk skip `__pycache__`, or keep the rule that helpers are only ever run
under `-B`.

## Second observed surface (task 6.6) -- a guard this line shipped was wrong

This one is **not** flaky and it was **not** found during the line. It was found
during this line's own **Archive** stage, by a `git stash` round-trip, and it is
recorded here rather than in a fix commit because the archive is the change's
permanent record.

**Symptom.** `apps/compat-api/tests/test_unit_xp_fixture.py`'s
`test_the_readme_inventory_matches_the_bytes_on_disk` failed with
`AssertionError: '1465' != '1562'` while the fixture was **byte-for-byte
unchanged** and `git status` reported it clean.

**Cause.** The guard summed `path.stat().st_size` over the fixture directory.
`tests/fixtures/**` has **no** `.gitattributes` entry and the repository sets
`core.autocrlf=true`, so a working tree may hold LF or CRLF for identical
committed content. The Sync stage ran `git stash` and `git stash pop` to compare
`openspec validate` counts; the pop **re-checked-out all 79 fixture files as
CRLF**, moving the total by **99,282 bytes** with no content change at all. The
old guard passed on an LF checkout and failed on a CRLF one, so it was partly a
line-ending detector and said nothing reliable about the inventory it exists to
protect.

**Measured, not assumed.** Committed blob bytes were compared against both
measurements for all 79 tracked files:

| measurement | bytes | KB |
|---|---|---|
| `git cat-file -p HEAD:<path>`, summed | 1,500,328 | **1,465** |
| LF-normalized on disk, summed | 1,500,328 | **1,465** |
| raw `st_size` on disk, summed | 1,599,610 | 1,562 |

Blob bytes equal LF-normalized bytes **for every one of the 79 files**, so the
README's `**1,465 KB** across 79 files` was correct from the start and only the
*measurement* was wrong. The root's earlier correction of that README was right
and needed no further change.

**Fix.** The guard now counts LF-normalized bytes, so it measures what git
stores. It shipped as its **own** `fix/` PR (#280, `dae7705`) rather than inside
this archive commit, because a code change does not belong in a docs stage and
`AGENTS.md` keeps one coherent stage per branch.

Proven end to end on a **fresh CRLF checkout** of `main` in a scratch worktree,
which is the environment that reproduced the failure: the pristine file from the
`main` blob fails with `AssertionError: '1465' != '1562'` and exit `1`, the
fixed file gives `Ran 1 test ... OK`, and the full compat suite on that same
CRLF checkout gives **`Ran 2187 tests ... OK`**. It is invariant across both checkout states, which was **proven rather
than asserted** by measuring two full copies of the fixture:

| tree state | CRLF in | normalized | naive `st_size` |
|---|---|---|---|
| all-LF | 0 / 79 files | 1,500,328 (1,465 KB) | 1,500,328 (1,465 KB) |
| all-CRLF | 79 / 79 files | 1,500,328 (1,465 KB) | 1,599,610 (1,562 KB) |

The first attempt at that proof was **itself defective** and was caught rather
than shipped: `shutil.copytree` copied the CRLF working tree, so the "all-LF"
copy was never converted to LF and the naive-measurement delta came out `0`. A
measured `CRLF in N/79 files` column was added so the premise is checked instead
of assumed, and the corrected run shows the real 99,282-byte divergence.

**The guard was then re-proven against real drift**, since a guard that counts
nothing passes everything. Three injections, each producing an independent
failure with its own message, the README restored byte-identically
(`d72009c21b2d`) and the suite passing again afterwards:

| injection | result |
|---|---|
| stated size `1,465 KB` -> `1,464 KB` | caught, exit `1` |
| stated file count `79` -> `78` | caught, exit `1` |
| stated copy count `26 copies` -> `25` | caught, exit `1` |

**Scope of the defect class, measured.** This was the **only** instance in the
repository, not a pattern repeated across lines:

- `capture_legacy_fixtures.py`, `build_registry.py` also call `st_size`, but only
  to **record** a manifest field; **no test anywhere asserts a recorded `bytes`
  value against disk**, so those manifests cannot be tripped this way.
- `replay_child.py` and `state_diff.py` use size as an upper **limit**, which is
  insensitive to line endings in the direction that matters.
- Every prior line's fixture integrity check verifies by **sha256 digest**, which
  is line-ending invariant, which is why seventeen committed fixtures were never
  exposed to this.

**Deliberately not done here.** The alternative fix is a
`/tests/fixtures/** text eol=lf` entry in `.gitattributes`, which would pin every
fixture's working-tree form. That is **not** done in this change: it would
reform the working tree of **all seventeen** prior fixtures for no committed-byte
change, it is unrelated to this line's deliverable, and the digest-based checks
were already correct. Recorded as a follow-up: either pin
`tests/fixtures/**` to `eol=lf`, or keep the rule that fixture-size assertions
normalize line endings before counting. This is the **second** recorded surface
in this project closed by fixing the guard rather than re-running it, and the
**first** found by a later stage of the same line rather than during it.
