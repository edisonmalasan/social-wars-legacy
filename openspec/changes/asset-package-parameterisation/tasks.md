# Tasks — asset package parameterisation

Binding investigation: `docs/legacy-m12-asset-parity.md` (merged `f7f9861`).
Binding design: `design.md` (decisions D1–D10).

**Ownership.** Task 1 is the only implementation task; task 2 is the only verification task. The
root orchestrator owns this file, the specs, the roadmap `Project Status` block, and acceptance. No
implementation subagent may edit `proposal.md`, `design.md`, `specs/`, or `tasks.md`.

**Scope guard.** This change delivers tooling, determinism, and a census. It does **not** attempt
any of the four building refusal classes (D7), does **not** convert the 587 available packages in
bulk (D8), and touches no client, Compatibility API, or legacy file (D3's manifest regeneration
excepted).

---

## 0. Preconditions, re-measured before anything is written

- [ ] 0.1 Re-measure from the working tree and record the figures this change was designed on:
      the hard-coded target sites (**10** in each converter); the candidate population (**452**
      buildings, **365** units); the per-domain verdict split (**365/365** units,
      **222/452** buildings); the four disjoint building refusal classes (**133 / 61 / 20 / 16**,
      summing to the **230** refused targets with one class each); and the two `fingerprint_inputs`
      file lists.
- [ ] 0.2 Re-measure the determinism finding before changing it: the committed `content_version`
      values (**`ddeca799…`**, **`9d8ad3b3…`**) against raw working-tree bytes **and** against
      LF-normalised bytes (**`c4e76e6d…`**, **`a0c3861f…`**); the CRLF counts on
      `inspection.json` (**170,096**) and `image_extraction.json` (**1,219,378**); and the CRLF
      deltas on `statuses.json` (**+1,054**), `conversions.json` (**+35**), and the unit
      `package.json` (**+1,790**). Record the raw and LF-normalised forms of **every** digest so no
      claim depends on a checkout form.
- [ ] 0.3 Confirm the oracle before touching it: both committed packages reproduce their recorded
      `package_sha256` (**`7de262e9…366b92a7`**, **`c40b754c…05d1c7`**) and `conversions.json` and
      `statuses.json` reproduce byte-identically, all **LF-normalised**.
- [ ] 0.4 Confirm the refuted hypotheses are still refuted, so the design is not built on a stale
      reading: a single-target run emits a **two**-package manifest with `counts.packages = 2`;
      and porting the unit converter's referenced-only `65535` rule converts **0** additional
      buildings and regresses **0**.
- [ ] 0.5 Record the baselines that must move or hold: preservation manifest (**3,258 entries /
      758,423,699 bytes**), `openspec validate --all --strict` composition (**72 main specs + 0
      changes** today), compat suite, validator (**23 files / 22 schemas / 604 references**), and
      the compatibility guard baseline digest.
- [ ] 0.6 Confirm containment: `auctions/` and `saves/` absent, `git status` clean apart from this
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

- [ ] 1.1 `convert_building.py`: make the target stem a **required** input (D1). Delete the
      module constant rather than defaulting it. Keep the existing `img_name`-based content
      resolution and its fail-closed uniqueness guard exactly as they are (D2). Verify all **10**
      former constant sites now read the passed target and that no other behaviour moved.
- [ ] 1.2 `convert_unit.py`: make the target stem **and** the content `legacy_id` required inputs
      (D1, D2). Keep the two-key (`legacy_id`, `img_name`) resolution and its uniqueness guard.
      Derive the source path from the stem at call time rather than from a module constant, and
      confirm the **10** former constant sites.
- [ ] 1.3 Both converters: compute `fingerprint_inputs` over **line-ending-normalised** bytes
      (D3). Assert the change mechanically — the fingerprint over CRLF-bearing inputs equals the
      fingerprint over the LF-normalised inputs — and do not merely pin the files.
- [ ] 1.4 `.gitattributes`: pin `tools/asset-registry/inspection.json`,
      `image_extraction.json`, `conversions.json`, `statuses.json` and the converted package
      `package.json` paths LF, following the existing `asset_ids.json` / `coverage.json` pins and
      the documented market-trade precedent. Record **why** in the file, as that precedent does.
- [ ] 1.5 Re-derive both committed packages under the deterministic digest. **Assert that the only
      field that changed is `content_version`**, and that `conversions.json`'s entries changed only
      in `package_sha256`. Any other difference is a defect in this change, not a consequence of
      D3, and must be investigated before proceeding.
- [ ] 1.6 `census_targets.py` (new, D5/D6): derive the candidate set from the committed asset-ID
      registry and normalized content (never transcribed); require `--out-root` with no default;
      run each converter into a per-target directory beneath it; record domain, stem, content
      `legacy_id`, verdict, and on refusal the class and distinct problem strings; write
      `target_census.json` deterministically with **no** timestamp, host, or iteration-order field.
      Continue past a refused target; exit non-zero only on a genuine tool failure.
- [ ] 1.7 Run the census and commit `target_census.json`. Confirm it reproduces byte-identically
      across at least three consecutive runs, and that the report's counts match task 0.1's
      figures — including **365/365** units and **222/452** buildings.
- [ ] 1.8 Regenerate `tests/fixtures/godot-compatibility-boot/guard-baseline.json` **because** the
      packages and manifests changed (D3). Record the old and new digests and confirm the only
      changed groups are `conversion_packages` and `registry_manifests`.

---

## 2. Verification

- [ ] 2.1 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_convert_building.py" -v`
      — exit 0, and the recorded-byte scenario now runs against the re-derived package.
- [ ] 2.2 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_convert_unit.py" -v`
      — exit 0.
- [ ] 2.3 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_census_targets.py" -v`
      — new; covers candidate derivation, containment, disjoint refusal classes, refusal
      non-fatality, genuine-failure exit, and report determinism.
- [ ] 2.4 `python -B -m unittest discover -s tools/asset-registry/tests -p "test_*.py" -v` — exit 0.
- [ ] 2.5 Anti-invention probes, each with a **byte-identical restore verified by sha256**, each
      probe's **failure count measured** rather than estimated, and all re-measured against the
      **final** delivered bytes: (a) reinstate a default target constant — must fail; (b) make the
      target optional — must fail; (c) hash raw bytes in `fingerprint_inputs` — must fail;
      (d) drop the unit's `legacy_id` parameter and derive it from the stem — must fail; (e) remove
      a content-uniqueness guard — must fail; (f) let the census abort on the first refusal — must
      fail; (g) give the census a default `--out-root` — must fail; (h) add a timestamp to the
      report — must fail; (i) widen a refusal class to cover a two-class target — must fail.
- [ ] 2.6 Containment proof: run the census with an output root outside the repository and confirm
      `git status --short` and `git diff --numstat` are unchanged, that no converted package
      directory or registry manifest in the repository was created or replaced, and that `auctions/`
      and `saves/` remain absent.
- [ ] 2.7 Preservation: `python -B tools/hash-manifest/hash_manifest.py verify` — exit 0, and the
      **3,258 entries / 758,423,699 bytes** baseline reconciled against the regenerated manifest,
      with every changed path enumerated and each justified by D3 or D8.
- [ ] 2.8 `python -B apps/compat-api/guard_baseline.py verify` — exit 0, with the regenerated
      baseline.
- [ ] 2.9 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` — exit 0. The
      suite touches `conversions.json` through `build_asset_ids.py`, so this is a real gate, not a
      formality. **Re-run before treating a `test_no_server_is_running` port assertion as a
      regression** — that is a recorded flaky surface.
- [ ] 2.10 `python -B packages/game-content/tools/validate_content.py` — exit 0, `result: valid`,
      **23 files / 22 schemas / 604 references** unchanged.
- [ ] 2.11 `openspec validate --all --strict` — **0 failed**, and record the **composition**
      (**71 main specs + 1 change** during the change), never the bare total.
- [ ] 2.12 `powershell -File apps/client-godot/verify.ps1` and
      `powershell -File apps/client-godot/verify-boot.ps1` — each exit 0. This change touches no
      client file, so any client failure is either the recorded flaky surfaces or an
      unrecorded regression; **re-run before concluding either**.
- [ ] 2.13 Record the `Project Status` transition in `docs/DEVELOPMENT_ROADMAP.md` and re-verify
      that the M11 ARCHIVED entries were **not** overwritten.

---

## 3. Follow-ups this change records but does not perform

- [ ] 3.1 Record in the roadmap that the **four** building refusal classes need their own
      investigation lines, with **133 / 61 / 20 / 16** as the measured starting figures and the
      sentinel class explicitly **unestablished** (D7), carrying both contradictory measurements.
- [ ] 3.2 Record the mass-conversion line: **587** available packages, roughly 30,000 files, a
      preservation-manifest regeneration, and no client-visible progress while `package_paths.gd`
      pins two packages (D8).
- [ ] 3.3 Record the `legacy_id`-carries-the-stem naming defect as **not** fixed here (D9).
- [ ] 3.4 Record this as the **fourth** instance of the LF-defect class, noting that unlike the
      first three it lands on a *provenance field* rather than on a comparison, and that the fix
      generalises the guard's existing line-ending-invariant precedent.