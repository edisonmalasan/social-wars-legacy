# Tasks — asset package parameterisation

Binding investigation: `docs/legacy-m12-asset-parity.md` (merged `f7f9861`).
Binding design: `design.md` (decisions D1–D10).

**Ownership.** Task 1 is the only implementation task; task 2 is the only verification task. The
root orchestrator owns this file, the specs, the roadmap `Project Status` block, and acceptance. No
implementation subagent may edit `proposal.md`, `design.md`, `specs/`, or `tasks.md`.

**Scope guard.** This change delivers tooling, determinism, and a census. It does **not** attempt
any refusal class in either domain (D7), does **not** convert the 290 available packages in
bulk (D8), and touches no Compatibility API or legacy file (D3's manifest regeneration excepted).

**Correction to that guard (Apply stage).** It originally also claimed this change "touches no client
file". That was **false, and D3 falsified it**: the client pins both packages' `content_version` in
`apps/client-godot/tests/test_package_loader.gd` (`HOUSE_CONTENT_VERSION`, `ELEPHANT_CONTENT_VERSION`),
and D3 changes both values by design. Two constants moved to the digests D3 produces, and
`verify.ps1` failed on `loader test exits 0` / `loader test reports PASS` until they did. No other
client source references either digest — checked across every `*.gd`, `*.py`, `*.json`, `*.md` and
`*.ps1` outside `evidence/` and `.godot/`, where the only remaining hits are historical prose in the
roadmap, an archived change, and this change's own re-measurement task 0.2. Two pins in a test file
moving with the artifact they pin is the consequence D3 predicts; it is recorded here rather than
left for a reader to discover from a failing battery.

---

## 0. Preconditions, re-measured before anything is written

- [x] 0.1 Re-measure from the working tree and record the figures this change was designed on:
      the hard-coded target sites (**10** in each converter); the candidate population (**452**
      buildings, **365** units); the per-domain verdict split; the disjoint refusal classes per
      domain; and the two `fingerprint_inputs` file lists.
      **RE-MEASURED (Apply stage) — and the unit half of the original figure was falsified.** The
      candidate population (**452** + **365** = **817**), the hard-coded site counts (**10** each),
      and the building split (**222/452**) all **re-confirmed**. The recorded **365/365 (100%)** unit
      figure was **false**: the Propose-stage instrument reassigned `TARGET_STEM`/`TARGET_LEGACY_ID`
      but not `SOURCE = "assets/sprites/" + TARGET_STEM + ".swf"`, which is computed at *import*
      time and so never moved — every unit target was parsed from the same elephant SWF. Correct
      figure: **68/365** units. Building refusal classes re-confirmed as **133 / 61 / 20 / 14+2**
      = **230**, one class each; units add **seven** classes over **297** targets
      (**90 / 76 / 57 / 44 / 18 / 11 / 1**), one class each. Total **290** converted, **527** refused,
      **8** classes, **0** targets in several classes. See `proposal.md` §2.
- [x] 0.2 Re-measure the determinism finding before changing it: the committed `content_version`
      values (**`ddeca799…`**, **`9d8ad3b3…`**) against raw working-tree bytes **and** against
      LF-normalised bytes (**`c4e76e6d…`**, **`a0c3861f…`**); the CRLF counts on
      `inspection.json` (**170,096**) and `image_extraction.json` (**1,219,378**); and the CRLF
      deltas on `statuses.json` (**+1,054**), `conversions.json` (**+35**), and the unit
      `package.json` (**+1,790**). Record the raw and LF-normalised forms of **every** digest so no
      claim depends on a checkout form.
- [x] 0.3 Confirm the oracle before touching it: both committed packages reproduce their recorded
      `package_sha256` (**`7de262e9…366b92a7`**, **`c40b754c…05d1c7`**) and `conversions.json` and
      `statuses.json` reproduce byte-identically, all **LF-normalised**.
- [x] 0.4 Confirm the refuted hypotheses are still refuted, so the design is not built on a stale
      reading: a single-target run emits a **two**-package manifest with `counts.packages = 2`;
      and porting the unit converter's referenced-only `65535` rule converts **0** additional
      buildings and regresses **0**.
- [x] 0.5 Record the baselines that must move or hold: preservation manifest (**3,258 entries /
      758,423,699 bytes**), `openspec validate --all --strict` composition (**72 main specs + 0
      changes** today), compat suite, validator (**23 files / 22 schemas / 604 references**), and
      the compatibility guard baseline digest.
- [x] 0.6 Confirm containment: `auctions/` and `saves/` absent, `git status` clean apart from this
      change's own paths. **Never run legacy Python that touches `auctions/` with the repository
      root as the working directory.**

---

## 1. Implementation — parameterised converters, deterministic digest, census tool

**Owned files (this task's entire write surface):**

- `tools/asset-registry/convert_building.py`
- `tools/asset-registry/convert_unit.py`
- `tools/asset-registry/census_targets.py` (new)
- `tools/asset-registry/target_census.json` (new, written by the tool)
- `.gitattributes`
- `tools/asset-registry/conversions.json`, `tools/asset-registry/statuses.json` (re-derived only)
- `assets/converted/buildings/0001_house_1_m/`, `assets/converted/units/10033_wild_elephant/`
  (re-derived; **`content_version` only**)
- `tests/fixtures/godot-compatibility-boot/guard-baseline.json` (regenerated — D3)

- [x] 1.1 `convert_building.py`: make the target stem a **required** input (D1). Delete the
      module constant rather than defaulting it. Keep the existing `img_name`-based content
      resolution and its fail-closed uniqueness guard exactly as they are (D2). Verify all **10**
      former constant sites now read the passed target and that no other behaviour moved.
- [x] 1.2 `convert_unit.py`: make the target stem **and** the content `legacy_id` required inputs
      (D1, D2). Keep the two-key (`legacy_id`, `img_name`) resolution and its uniqueness guard.
      Derive the source path from the stem at call time rather than from a module constant, and
      confirm the **10** former constant sites.
- [x] 1.3 Both converters: compute `fingerprint_inputs` over **line-ending-normalised** bytes
      (D3). Assert the change mechanically — the fingerprint over CRLF-bearing inputs equals the
      fingerprint over the LF-normalised inputs — and do not merely pin the files.
- [x] 1.4 `.gitattributes`: pin `tools/asset-registry/inspection.json`,
      `image_extraction.json`, `conversions.json`, `statuses.json` and the converted package
      `package.json` paths LF, following the existing `asset_ids.json` / `coverage.json` pins and
      the documented market-trade precedent. Record **why** in the file, as that precedent does.
- [x] 1.5 Re-derive both committed packages under the deterministic digest. **Assert that the only
      field that changed is `content_version`**, and that `conversions.json`'s entries changed only
      in `package_sha256`. Any other difference is a defect in this change, not a consequence of
      D3, and must be investigated before proceeding.
- [x] 1.6 `census_targets.py` (new, D5/D6): derive the candidate set from the committed asset-ID
      registry and normalized content (never transcribed); require `--out-root` with no default;
      run each converter into a per-target directory beneath it; record domain, stem, content
      `legacy_id`, verdict, and on refusal the class and distinct problem strings; write
      `target_census.json` deterministically with **no** timestamp, host, or iteration-order field.
      Continue past a refused target; exit non-zero only on a genuine tool failure.
- [x] 1.7 Run the census and commit `target_census.json`. Confirm it reproduces byte-identically
      across at least three consecutive runs, and that the report's counts match task 0.1's
      **re-measured** figures — **68/365** units and **222/452** buildings, **817** candidates,
      **290** converted, **527** refused, **8** classes, **0** targets in several classes.
      **This task is the reason the false unit figure was caught**: the census drove the converters
      through their own CLI-equivalent entry points rather than by reassigning module constants,
      which is what the Propose-stage measurement did wrong.
      **DONE.** Three consecutive runs, exit 0 each, **one** distinct digest:
      `84b11bee888a8fe93efd0d783e5cfd605919798e0bbad5e30259ccde0baa8868`, **354,636 bytes** each,
      which is also the committed report's exact digest. Counts re-read from the committed document
      agree with task 0.1 on every figure, and the report carries **no** timestamp, host, or
      iteration-order field. Two process defects were found and corrected while producing this
      evidence, both recorded because each would have produced a *false* determinism claim: the
      first run loop **deleted each output root after its run**, destroying runs 2 and 3 before their
      digests were captured (so the digest is now captured before cleanup), and the probe work was
      initially run **concurrently** with the determinism runs, which was a live contamination risk
      because each census run is a fresh subprocess that re-imports all three modules at its start.
      The determinism runs were killed and re-run with no concurrent mutation; run 2 was provably
      unaffected (its process imported at 09:54:38, before the first mutation), but the claim rests
      on the clean re-run rather than on that argument.
- [x] 1.8 Regenerate `tests/fixtures/godot-compatibility-boot/guard-baseline.json` **because** the
      packages and manifests changed (D3). Record the old and new digests and confirm the only
      changed groups are `conversion_packages` and `registry_manifests`.
      **DONE — and the recorded expectation was wrong twice, both times corrected by measurement.**
      Combined digest **`6978b959…ff348` → `13b2ccca…2ad1`**; `guard_baseline.py verify` exit 0.
      First error: **three** groups moved, not two — `conversion_packages` (both `package.json`),
      `registry_manifests` (`conversions.json`), **and `m4_evidence`**
      (`apps/client-godot/evidence/first-render/report.json`), because that report is *regenerated
      evidence* whose recorded `/inputs/manifests/0` and two `/inputs/packages/*/directory_sha256`
      digests necessarily move when the packages and manifest do. Second error, and the more
      interesting one: the baseline had to be regenerated **twice**, and the first regeneration
      produced a **false green**. It was taken before `verify.ps1` had run, so `m4_evidence` still
      held the pre-D3 digest; `verify-boot.ps1` then failed with `guard baseline verify exits 0`
      (before and after) and `guarded bytes are identical before and after (pre= post=)`. The lesson
      is ordering, not arithmetic: **regenerating a digest baseline before the artifacts it covers
      have settled produces a baseline that is wrong in a way `verify` cannot detect, because
      `verify` only compares the baseline to whatever is on disk at that moment.** Regenerating after
      `verify.ps1` gave exit 0 and a stable digest.

---

## 2. Verification

- [x] 2.1 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_convert_building.py" -v`
      — exit 0, and the recorded-byte scenario now runs against the re-derived package.
      **Observed: `Ran 26 tests`, OK, exit 0.**
- [x] 2.2 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_convert_unit.py" -v`
      — exit 0. **Observed: `Ran 55 tests`, OK, exit 0.**
- [x] 2.3 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_census_targets.py" -v`
      — new; covers candidate derivation, containment, disjoint refusal classes, refusal
      non-fatality, genuine-failure exit, and report determinism.
      **Observed: `Ran 25 tests`, OK, exit 0**, and **zero skips** — the three committed-report
      tests now execute because `target_census.json` exists, where the pre-commit state skipped them.
- [x] 2.4 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_*.py" -v` — exit 0.
      **Observed: `Ran 206 tests in 85.180s`, OK, exit 0**, no `FAIL:`/`ERROR:` line and no skip
      (up from the recorded 205-with-3-skips: +1 for the fresh-report timestamp guard added under
      2.5, and the three committed-report tests now run instead of skipping).
- [x] 2.5 Anti-invention probes, each with a **byte-identical restore verified by sha256**, each
      probe's **failure count measured** rather than estimated, and all re-measured against the
      **final** delivered bytes: (a) reinstate a default target constant — must fail; (b) make the
      target optional — must fail; (c) hash raw bytes in `fingerprint_inputs` — must fail;
      (d) drop the unit's `legacy_id` parameter and derive it from the stem — must fail; (e) remove
      a content-uniqueness guard — must fail; (f) let the census abort on the first refusal — must
      fail; (g) give the census a default `--out-root` — must fail; (h) add a timestamp to the
      report — must fail; (i) widen a refusal class to cover a two-class target — must fail.
      **DONE — 11 of 11 probes detected, 16 failures total**, every restore sha256-verified and
      asserted free of NUL bytes, with the baseline suite green before *and* after the set and
      `git diff --numstat --ignore-cr-at-eol` + `git status --short` equal to their pre-probe values.
      Measured, in probe order: **a=1, b=2, c=2, d=2, e=1, f=1, g=1, h=1, i=3, j=1, k=1**
      (j and k are supplementary, labelled as such, and are not in the list above).
      The guards that fired are named in the probe record rather than assumed: (a)
      `test_no_target_stem_constant_exists`; (b) `test_invoking_without_a_target_exits_non_zero` and
      `_writes_nothing`; (c) **`test_regenerated_package_matches_committed_bytes`** and
      `test_fingerprint_bytes_normalises_text` — the first is the strongest single result in the set,
      because it shows the D3 fix is load-bearing for the committed artifact and not merely for a
      unit-level helper; (d) `test_content_ref_not_unique` and
      `test_a_mismatched_legacy_id_fails_closed`; (e)
      `test_the_candidate_set_is_derived_not_transcribed`; (f)
      `test_a_refused_target_does_not_end_the_run`; (g)
      `test_the_output_root_is_required`; (h) `test_a_fresh_report_names_no_timestamp`; (i) three
      guards, including `test_a_refusal_pattern_does_not_invent_a_category`.

      **TWO DEFECTS IN MY OWN GUARDS WERE FOUND BY INJECTION, and both are recorded rather than
      quietly fixed.** (1) **Probe (g) initially detected nothing**, and the harness's
      abort-on-zero-failures rule turned a silently useless test into a visible defect — the same
      rule that earlier stopped a parse error from being counted as a detection. The cause was a
      **tautological assertion**: the test asserted `"--out-root" in stderr`, but argparse's
      **usage line lists every option name, required or not**, so the assertion passed with
      `required=True` removed. It now passes the *other* required argument so only `--out-root` is
      missing, asserts `code == 2`, and asserts on argparse's **error** text
      (`the following arguments are required: --out-root`). Dropping `required=True` now surfaces as
      a `TypeError` from `Path(None)` instead of a clean usage error, which is itself the honest
      consequence. (2) The **fresh-report** timestamp guard was **added**, because the existing
      `test_the_committed_report_names_no_timestamp` reads the *committed artifact* and therefore
      **cannot see a timestamp the tool has started writing**. A *varying* timestamp is caught by the
      rerun-determinism guard, but a **constant** fake one is stable across runs by definition and
      slipped through; the new guard scans what the tool actually writes, and was proven necessary by
      injecting exactly that constant and observing the determinism guard stay silent.

      **THREE DEFECTS IN THE PROBE HARNESS ITSELF were found and corrected**, recorded because each
      would have misreported a result rather than merely failing: (i) it counted `[test] FAIL` lines,
      which is the **Godot** suites' convention — these are plain `unittest.main()` suites and emit
      `FAIL:`/`ERROR:` with a summary, so probe (a) reported **0 failures** while the guard was in
      fact firing (reproduced by hand: `AssertionError: True is not false`); (ii) one probe anchor had
      the wrong indentation; (iii) the summary regex was fixed **twice** and was wrong twice — first
      requiring an `errors=` clause that unittest omits when zero, then embedding a literal `", "`
      before `errors=` so that the **errors-only** form `FAILED (errors=1)` could not match at all,
      which is exactly the form probe (g) produces. It now parses the clause list
      (`failures=`/`errors=` pairs) rather than pattern-matching the summary string, and asserts the
      parse is non-empty. A universal-trailing-newline restore rule was deliberately **not** adopted,
      per the `construction-assist` precedent.
- [x] 2.6 Containment proof: run the census with an output root outside the repository and confirm
      `git status --short` and `git diff --numstat` are unchanged, that no converted package
      directory or registry manifest in the repository was created or replaced, and that `auctions/`
      and `saves/` remain absent.
      **Observed:** a full census run with `--out-root` and `--report` both outside the repository
      exited 0 in 416 s; `git status --short` and `git diff --numstat` were **byte-identical before
      and after**; `auctions/` and `saves/` were absent before and after; `assets/converted` showed
      no new or replaced path; the report landed outside the repository. The run was driven with the
      pinned interpreter from the repository root and never invoked legacy Python.
- [x] 2.7 Preservation: `python -B tools/hash-manifest/hash_manifest.py verify` — exit 0, and the
      **3,258 entries / 758,423,699 bytes** baseline reconciled against the regenerated manifest,
      with every changed path enumerated and each justified by D3 or D8.
      **Observed: `verify: 3258 entries, 758423699 bytes`, exit 0**, unchanged from the recorded
      baseline — the manifest covers the immutable corpus, not the tooling this change rewrites.
      The two `package.json` files are justified by D3 and change in exactly one field each
      (`content_version`), which was asserted rather than assumed (task 1.5).
- [x] 2.8 `python -B apps/compat-api/guard_baseline.py verify` — exit 0, with the regenerated
      baseline. **Observed: exit 0**, 6 groups, combined
      **`13b2ccca56bfd7ea8d42e9ca3f0ac066aa6a5aae15c7a3dee99703ca972bcad1`**. See task 1.8 for why
      this required a **second** regeneration after the `m4_evidence` group settled.

      **A "CHECKOUT-FORM DEFECT" WAS REPORTED HERE AND THEN FALSIFIED — recorded because the
      correction is the finding.** I read `guard_baseline.py` as hashing **raw working-tree
      bytes**, measured a CRLF checkout of `evidence/first-render/report.json` against its recorded
      digest (`git checkout-index` gave **183 CRLF pairs / 4,832 bytes**, `sha256 a9d3d763…`,
      versus the recorded `9eda9d83…`), concluded that `verify` **fails on a fresh default Windows
      checkout**, established it as pre-existing by replaying the measurement against the
      pre-change baseline from `HEAD`, and committed a `.gitattributes` pin justified by it.
      **The conclusion was wrong, and the error was in my instrument, not the repository.**
      `guard_baseline.py`'s `guarded_bytes()` (line 128) decodes each file as UTF-8, returns the
      exact bytes when that decode fails or a NUL is present — which is the case for the
      `first-render` PNG — and otherwise replaces CRLF with LF **before** hashing. So the recorded
      digest is over *normalised* bytes, and I was comparing it against `sha256` of *raw* bytes: a
      mismatch that was guaranteed to appear and carried no information. Re-measured correctly, **all
      91 recorded per-file digests reproduce under that normalisation**, so the baseline is
      **already** line-ending invariant and needed no pin to verify on a CRLF checkout. The pin is
      retained, for the honest and much weaker reason that this is regenerated evidence whose own
      recorded digests should stay comparable across checkout forms (the `market-trade`
      precedent); the `.gitattributes` comment records that it is **not** required by
      `guard_baseline.py`.
      **The generalisable lesson, and the reason this is not merely tidying:** a mismatch is only
      evidence once the *expected* value's own algorithm has been read. I had already been told
      this change's fingerprint fix "generalises the guard's existing line-ending-invariant
      precedent" (task 3.4) — the precedent was named in the task text and I still did not check
      it before building a conclusion on top of the assumption. A fresh-checkout reproduction was
      the right instinct; it was the wrong measurement, and had it not been re-run against a real
      `checkout-index` copy **after** the commit, a false claim would have shipped in a green,
      passing PR.
      `hash_manifest.py verify` is unaffected (**3,258 entries / 758,423,699 bytes**, exit 0): the
      manifest covers the immutable corpus, and `.gitattributes` is not itself a manifest entry.
- [x] 2.9 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` — exit 0. The
      suite touches `conversions.json` through `build_asset_ids.py`, so this is a real gate, not a
      formality. **Re-run before treating a `test_no_server_is_running` port assertion as a
      regression** — that is a recorded flaky surface.
      **Observed: `Ran 3077 tests in 80.634s`, OK, exit 0**, zero `FAIL:`/`ERROR:` lines, the
      recorded baseline reproduced. The suite did **not** trip the recorded port flakiness.
- [x] 2.10 `python -B packages/game-content/tools/validate_content.py` — exit 0, `result: valid`,
      **23 files / 22 schemas / 604 references** unchanged.
      **Observed: `result: valid`, `files_verified: 23`, `schemas_verified: 22`,
      `references_checked: 604`, exit 0.**
- [x] 2.11 `openspec validate --all --strict` — **0 failed**, and record the **composition**
      (**71 main specs + 1 change** during the change), never the bare total.
      **Observed: `Totals: 73 passed, 0 failed`, exit 0.** Composition re-measured as
      **72 main specs + 1 active change = 73**, not the "71 + 1" this task's own text predicted.
      The task text is corrected here rather than left to be read as a reproduced figure: a spec was
      added after the task was written, and the total alone never says which stage is done.
- [x] 2.12 `powershell -File apps/client-godot/verify.ps1` and
      `powershell -File apps/client-godot/verify-boot.ps1` - each exit 0. **This task's own premise
      was wrong and is corrected rather than left standing**: it read "This change touches no client
      file", which D3 falsified, because the client pins both packages' `content_version` in
      `apps/client-godot/tests/test_package_loader.gd` (see the scope-guard correction at the top of
      this file). So a client failure here may be the **direct consequence of this change's own
      regeneration** and not a flaky surface at all — `verify.ps1` in fact failed twice on
      `loader test exits 0` / `loader test reports PASS` before those two constants were updated.
      Any *further* client failure is either the recorded flaky surfaces or an unrecorded
      regression; **re-run before concluding either**.
      **Observed, both in the final state and re-run after every edit to this file:**
      `verify.ps1` **exit 0**, `PASS all checks succeeded`, **62** `ok` assertions and **0** `FAIL`,
      including `package bytes unchanged` for both converted packages and `manifest bytes
      unchanged` for all four registry manifests — which is this change's real parity claim stated
      as a gate. `verify-boot.ps1` **exit 0**, `PASS all checks succeeded`, **230** `ok` assertions
      and **0** `FAIL`, **1,144** log files carrying **zero** `[test] FAIL`, `^ERROR:` or
      `SCRIPT ERROR` lines. **No recorded flaky surface fired**, so nothing here needed the
      re-run this task asks for — and that is reported as an observation, not as proof the surfaces
      are gone.
      **The ordering trap from task 1.8 was checked rather than assumed**: `verify.ps1` rewrites
      `evidence/first-render/report.json`, so the battery can invalidate the baseline *after* it
      was regenerated. Re-checked in the final state — the file's `sha256` still **matches** the
      regenerated `m4_evidence` record, as does `first-render.png`, and
      `guard_baseline.py verify` still exits 0 with combined **`13b2ccca…2ad1`**. The regenerated
      evidence is therefore **reproducible**, not merely green once.
      Containment re-confirmed after both batteries: port **5056 free** — the 133 residual entries
      are all `TIME_WAIT` with no owning process, which is why the raw listener count looks alarming
      and is not a leak; **no working-tree `saves/`**; **`auctions/`** still absent; and
      `assets/converted/` still holds exactly the one building and one unit package the repository
      started with, so neither battery created a package.
- [x] 2.13 Record the `Project Status` transition in `docs/DEVELOPMENT_ROADMAP.md` and re-verify
      that the M11 ARCHIVED entries were **not** overwritten.
      **Observed.** Six new `Project Status` bullets were **prepended** (current milestone, active
      change, lifecycle stage, roadmap cursor, next eligible objective, last OpenSpec validation),
      each pushing the prior bullet down and relabelling it `…, before this entry, retained in full`
      — the block's established convention, so the ledger stays append-only in substance.
      Verified: `retained in full` markers rise **56 → 63**, and every prior milestone's change name
      still appears (`market-trade` 18, `darts` 19, `social-state` 28, `construction-assist` 6,
      `friends` 29, `unit-experience` 7, `stored-item-placement` 7). The file diff reads
      **18 insertions / 6 deletions**, and all six "deletions" are the relabel rewrites
      (`- **X:**` → `- **X, before this entry, retained in full:**`) — **zero** prior content
      removed, checked rather than assumed.

---

## 3. Follow-ups this change records but does not perform

- [x] 3.1 Record in the roadmap that the refusal classes need their own investigation lines. The
      building figures are re-confirmed (**133 / 61 / 20 / 14+2** = **230**) with the sentinel class
      explicitly **unestablished** (D7), carrying both contradictory measurements. **This
      follow-up is now larger than recorded:** the census also measured **seven** unit classes over
      **297** unit targets (**90 / 76 / 57 / 44 / 18 / 11 / 1**), which were unknown when this task
      was written because the unit domain was believed to convert at 100%. `unknown fill style` and
      `unsupported shape tag: 83` span both domains.
      **Recorded** in the roadmap's *Next eligible objective* entry as **twelve** class-domains
      (five building, seven unit, two spanning both), together with the measurement that makes the
      question answerable at all.
- [x] 3.2 Record the mass-conversion line: **290** available packages (222 buildings + 68 units),
      roughly 15,000 files, a preservation-manifest regeneration, and no client-visible progress
      while `package_paths.gd` pins two packages (D8). Record that **no domain is 100%
      convertible**, so this line cannot be scoped by domain and depends on 3.1 first.
      **Recorded** in the roadmap as an explicit open **decision** — whether mass conversion is
      worth doing before FX replacement and animation gaps — with the ~15,000-file cost and the
      no-client-visible-progress caveat stated rather than assumed away. The roadmap also states
      plainly that this line's exit criterion is **not** met and must not be read as met.
- [x] 3.3 Record the `legacy_id`-carries-the-stem naming defect as **not** fixed here (D9).
      **Recorded** as unchanged and uncorrected; the census reports `legacy_id` per target without
      treating the stem-derived value as a naming fix.
- [x] 3.4 Record this as the **fourth** instance of the LF-defect class, noting that unlike the
      first three it lands on a *provenance field* rather than on a comparison, and that the fix
      generalises the guard's existing line-ending-invariant precedent.
      **Recorded — and CORRECTED, because the second bullet below is false and was itself a
      miscount of this defect class.** What is recorded now:
      - The `fingerprint_inputs` occurrence (fourth as written): fixed at the cause by
        `fingerprint_bytes`, with pins recorded so raw and normalised bytes agree.
      - **Withdrawn: a claimed fifth instance in `guard_baseline.py`'s `m4_evidence` group.** I
        asserted that `guard_baseline.py` hashes raw working-tree bytes and therefore that its
        baseline fails on a CRLF checkout, and added a `.gitattributes` pin on that basis. **That
        was wrong**: `guarded_bytes()` normalises CRLF to LF before hashing for every UTF-8,
        NUL-free file, and all **91** recorded digests reproduce under that normalisation. See
        task 2.8 for the full instrument error. The pin survives on the much weaker and honest
        ground that it is regenerated evidence whose recorded digests should stay comparable
        across checkout forms, which is a **convention**, not a defect instance. So the count is
        **four**, as originally written — and the count is unchanged by this correction, which is
        itself worth stating plainly rather than presenting a withdrawn finding as a fifth member.
      - The transferable point is not a tally but a check: `guard_baseline.py` was **already
        line-ending invariant before this change**, and task 3.4's own text said the new fix
        "generalises the guard's existing line-ending-invariant precedent". The precedent was
        available to read and I built a claim on the assumption that contradicted it.