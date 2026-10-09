# Tasks

## 1. Coverage tool: path-first join with a recorded fallback tier

- [x] 1.1 In `tools/asset-registry/build_registry.py`, attempt each image reference's own path under the committed web root before any basename match, and record path-resolved and fallback-resolved tiers in place of the `basename_single` / `basename_collision` fields; verify the images section reports 573 path-resolved, 2 fallback-resolved and 32 missing, totalling 607.
- [x] 1.2 Rewrite the images `rule` string the tool writes into `coverage.json` so the recorded evidence describes the path-first-then-fallback order it actually performs; verify the written `rule` field names the web root and the fallback.
- [x] 1.3 Record the fallback tier's members by name in the coverage output, not only as a count, and verify the two named members are exactly `/chapters/simple/arachnids_old.jpg` and `/chapters/simple/orcs_old.jpg`.
- [x] 1.4 Update `tools/asset-registry/tests/test_build_registry.py`: move the pinned images tier figures to the new measured values and add cases asserting the fallback tier's exact membership, the 32 refusals, and that no image entry is reported as a collision; verify the suite passes under the pinned CPython 3.9.13 interpreter with `python -B -m unittest discover -s tools/asset-registry/tests -p test_build_registry.py -v`.
- [x] 1.5 Add a case asserting the new join reproduces the corpus bijection: the **path-resolved tier** is exactly a bijection â€” 573 references to 573 distinct corpus files, that set being every file under the web root, so none is unreferenced â€” and all 575 identified references name 573 files, the only two shared targets being the mis-pathed fallback references aliasing their `chapters2` counterparts; verify the assertion passes rather than being tautological by also confirming it fails when the join is reverted to basename-only. (Amended during Apply: the task as originally written asked for distinctness over *all* resolved references, which the join does not have â€” see design.md "Corrections found during Apply", C1.)

## 2. Asset ID tool: same join, reconciled against coverage

- [x] 2.1 In `tools/asset-registry/build_asset_ids.py`, apply the same path-first attempt ahead of the existing basename candidates in `image_candidates` construction and `build_kind_entries`, and update `RULES["images"]` to match the string written by the coverage tool; verify both tools write byte-identical rule text for the images domain.
- [x] 2.2 Update the reconciliation against `coverage.json` (`basename_single` / `basename_collision` checks) to reconcile the new tier fields, and verify a deliberately mismatched coverage copy still fails closed with exit 1 rather than writing output.
- [x] 2.3 Verify the images status distribution in the rebuilt registry is 566 `passthrough`, 9 `extracted`, 32 `missing_source`, 0 `ambiguous`, totalling 607, and that the two fallback-resolved entries carry the same runtime path they resolve to today.
- [x] 2.4 Confirm `ambiguous` remains declarable in the status vocabulary and that the client-side runtime-path contract still rejects a runtime path on a non-runtime status; verify by constructing an in-memory ambiguous entry and asserting the builder's own validation and the client's contract both still reject the runtime claim.
- [x] 2.5 Update `tools/asset-registry/tests/test_build_asset_ids.py`: move the pinned tier and per-status figures to the new measured values, and add a case asserting the zero-disagreement property â€” for every image reference the previous basename-only join resolved, the new join resolves it to the same file; verify the suite passes and that the assertion compares each field against the join explicitly rather than through a membership test that could pass on two nulls.
- [x] 2.6 Add a case asserting all 32 absent references remain reported missing with no source and no runtime path, and that the run creates no file, placeholder or content edit for any of them; verify the working tree shows no change under `assets/` or `packages/game-content/` after a full run.

## 3. Regenerate committed output and inspect the diff

- [x] 3.1 Regenerate `tools/asset-registry/coverage.json` and `tools/asset-registry/asset_ids.json`, then re-run each builder once more and verify the second run's bytes are identical to the first.
- [x] 3.2 Inspect the regenerated diff rather than assuming it: verify every changed field is one of the images tier counts, the images `rule` string, the 50 entries' status/source/runtime/candidates fields, and the top-level counts â€” and that no other domain, no `item_sprites` / `magic_sprites` / `sounds` entry, and no input digest moved.
- [x] 3.3 Confirm the regenerated files are pure LF and record their byte counts and SHA-256 digests for the committed evidence.
- [x] 3.4 Document the coverage and asset-ID build commands, their observed results and their claim limits in `tools/asset-registry/README.md`, and record in `AGENTS.md` that the images join is now path-first with a recorded basename fallback and that `ambiguous` remains in the vocabulary; verify both documented command lines run as written.

## 4. Client: move the three pinned count figures only

- [x] 4.1 In `apps/client-godot/tests/test_asset_ids.gd`, update `EXPECTED_STATUS["images"]` to the new measured status figures and confirm no other assertion's value, threshold or intent changes; verify by diffing the file and confirming the only altered lines are the pinned figures.
- [x] 4.2 Verify the client still treats a non-runtime status as carrying no runtime path, and that the 50 entries that moved to a runtime-bearing status now resolve through the unchanged client contract with no client source edit; verify `godot --headless --path apps/client-godot --script res://tests/test_asset_ids.gd` exits 0.
- [x] 4.3 Confirm the committed registry file is byte-identical before and after the client suite runs, so the client continues to read the registry without writing it.

## 5. Integration verification

- [x] 5.1 Run the full asset-registry test discovery and verify it exits 0, recording the observed test count and comparing it against the pre-change count to account for the added cases.
- [x] 5.2 Run `powershell -File apps/client-godot/verify.ps1` and `powershell -File apps/client-godot/verify-boot.ps1` and verify both exit 0, that the guard digests are identical before and after, and that no log file carries a `[test] FAIL`, `^ERROR:` or `SCRIPT ERROR` line.
- [x] 5.3 Run `python -B tools/hash-manifest/hash_manifest.py verify` and verify the preservation manifest still verifies with its entry count and byte total unchanged, confirming no preserved input byte moved.
- [x] 5.4 Verify `openspec validate --all --strict` passes, that the registry totals still reconcile against `packages/game-content` and the conversion and extraction manifests, and that no Flash, Ruffle, ActionScript or browser executed and no non-loopback network call was made.