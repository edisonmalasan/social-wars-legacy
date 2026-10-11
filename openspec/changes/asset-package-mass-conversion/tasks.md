# Tasks — asset package mass conversion

Binding measurements: `proposal.md` §§1–5. Binding design: `design.md` (decisions D1–D10).

**Ownership.** The root orchestrator owns this file, the specs, `proposal.md`, `design.md`, the
roadmap `Project Status` block, and acceptance. **No implementation subagent may edit
`proposal.md`, `design.md`, `specs/`, or `tasks.md`.** Task 1 is the implementation task; task 2 is
the verification task.

**Scope guard.** This change converts the **290** census-convertible targets, changes package
output to **reference** rather than copy bitmaps, and updates whatever that moves. It does **not**
lift any refusal class (all **527** stay refused, D8), does **not** commit bitmap bytes (D1), does
**not** regenerate the preservation manifest (D7), and touches no legacy server, Compatibility API,
Flash, or network path.

**Corrections carried in from the Propose stage, recorded not tidied.** The predecessor line's
non-goal estimated *"roughly 15,000 files and a preservation-manifest regeneration"*; the first
figure is **8,805** and the second is **impossible** (D7, `proposal.md` §2). Both are corrected in
`proposal.md` rather than silently dropped.

---

## 0. Preconditions, re-measured before anything is written

- [ ] 0.1 Re-measure and record the figures this change was designed on: **290** census-convertible
      targets (**222** buildings, **68** units); **8,805** output files; **72,888,172** total bytes
      (**9,034,706** `package.json`, **63,853,466** bitmap); **7,275** distinct bitmap contents over
      **8,515** occurrences; duplication factor **1.11×**. Confirm every measured figure rather than
      quoting it, and record any that moved.
- [ ] 0.2 Re-measure the preservation-manifest finding: that it builds from a **pinned commit**
      (`hash_manifest.py:180-184`), that the committed manifest has **3,258** entries and **0**
      under `assets/converted`, and that it verifies at exit 0 **after** any conversion.
- [ ] 0.3 Record the containment baseline: `auctions/` and `saves/` absent, `git status` clean apart
      from this change's own paths, working tree otherwise unmodified. **Never run legacy Python
      that touches `auctions/` with the repository root as the working directory.**
- [ ] 0.4 Record the baselines that must move or hold: `openspec validate --all --strict`
      composition, compat suite count, content validator result (**23 files / 22 schemas / 604
      references**), compatibility guard baseline digest, and the pinned digests in
      `evidence/first-render/report.json`.

---

## 1. Implementation — reference-instead-of-copy, then convert 290

**Owned files:** `tools/asset-registry/convert_building.py`, `convert_unit.py`,
`conversion.schema.json`, a new mass-conversion tool, the generated
`tools/asset-registry/conversions.json` / `statuses.json`, and the committed
`assets/converted/{buildings,units}/*/package.json` manifests. Client files are owned **only** to
the extent task 1.1 measures they require.

- [ ] 1.1 **Measure how the client resolves `bitmaps[].file` today** (D4), before changing it.
      Read `package_paths.gd:33-38`, `package_loader.gd:481` and its bitmap validation at `:840-845`,
      and `verify.ps1:159,184-185`. Record whether `file` is joined onto the package directory or is
      already repository-relative. **Report the measurement**; do not proceed on an assumed answer.
      If it is already repository-relative, record that **no client change is required** and skip
      to task 1.5.
- [ ] 1.2 **Re-run the census** and record its digest and any delta against the committed
      `target_census.json` (Objective 2 recorded committed `84B11BEE…` vs tree `84B7D954…`, differing
      on **109** targets with one verdict change, and recording no input digests). If the delta
      changes which targets are convertible, **record it and reconcile the scope before converting** —
      do not convert a set the current census does not support.
- [ ] 1.3 **Change both converters to reference, not copy** (D1). Each `bitmaps[].file` records the
      extraction output path; the package directory receives no bitmap bytes. **Retain the digest
      verification** (D2): resolve each referenced path, hash its bytes, and fail validation on a
      mismatch or a missing file **before** any write. Remove the now-dead payload-copy loop rather
      than leaving it unreachable.
- [ ] 1.4 **Correct `output_bytes` semantics and its schema description** (D3). The field becomes
      the `package.json` byte total; `conversion.schema.json:72-74` no longer describes it as
      including copied bitmap bytes.
- [ ] 1.5 **Re-derive both committed packages** (`0001_house_1_m`, `10033_wild_elephant`) under
      D1–D3, so the corpus carries exactly **one** resolution convention (D5). Update every pin that
      moves in the same change: `test_package_loader.gd`'s content-version constants, the digests in
      `evidence/first-render/report.json`, and `verify.ps1` if task 1.1 found them affected.
- [ ] 1.6 **Write the mass-conversion tool.** It SHALL derive its target set from the committed
      census at run time (D8), convert exactly those targets, report per-target verdict agreement,
      and surface disagreements as a **distinct outcome** rather than accepting the run's own verdict.
      No target stem SHALL appear as a literal in its source.
- [ ] 1.7 **Run the conversion** over the census-convertible set into the repository, regenerating
      `conversions.json` and `statuses.json`. Record the resulting file count and byte total and
      compare them to task 0.1's prediction; a mismatch is reported, not reconciled silently.
- [ ] 1.8 **Record the MATRIX anomaly at line level** (D6) in the change's artifacts, quoting
      **2,869 / 2,869** and the cap of 11. **Add no per-package anomaly field** — the captured hex
      stays verbatim.

---

## 2. Verification — obligations V1–V7 from `design.md`

Each obligation is checked by inspecting the artefact, not by trusting the converter's exit code.

- [ ] 2.1 **V1/V2** — Every recorded bitmap reference resolves and hashes to its recorded SHA-256, and
      every committed package directory contains **exactly one** file, `package.json`. Verify by
      walking the committed tree, not by re-reading the conversion log.
- [ ] 2.2 **V3** — Run the conversion **three** consecutive times (D9) and confirm byte-identical
      output each time.
- [ ] 2.3 **V4** — Confirm the converted count equals the census's convertible count and that
      **zero** targets disagreed with the census verdict.
- [ ] 2.4 **V5** — Confirm every protected input is byte-identical to task 0.3, and that
      `git status` shows changes only under this change's owned paths.
- [ ] 2.5 **V6** — `openspec validate --all --strict` passes.
- [ ] 2.6 **V7** — The preservation manifest still verifies at **3,258** entries and
      **758,423,699** bytes (D7). **It must not move.** A movement is a defect, not a regeneration.
- [ ] 2.7 Run the committed checks that touch these artefacts and report actual results:
      the conversion and census unit suites, the content validator, the compatibility guard, and
      `verify.ps1` / `verify-boot.ps1` where the pins moved. **Record every check actually run, with
      its exit code. Do not record a check that was not run.**
- [ ] 2.8 Record the grep-based confirmation that **no bitmap file** was committed under
      `assets/converted/{buildings,units}/`, and that `assets/converted/images/` remains ignored.

---

## 3. Non-goals, verified

- [ ] 3.1 Confirm **no refusal class was lifted**: all **527** census-refused targets remain
      unconverted.
- [ ] 3.2 Confirm **no Flash, Ruffle, ActionScript, or browser executed** and no network was used.
- [ ] 3.3 Confirm no legacy server, Compatibility API, or client **scene** changed.