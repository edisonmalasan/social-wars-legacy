## 1. Census data

- [ ] 1.1 Create `docs/game-content/census.json` with schema version, policy, and one entry per content source covering all 20 top-level keys of `config/main.json` (container shape, entry count, ID scheme, asset-reference fields), the five ordered patches (file order, op counts, target paths), the mods pipeline status, the duplicate-cleaning behavior, and the dynamic-derivation boundary, each with source references; verify by running the focused test suite and confirming all entries load

- [ ] 1.2 Create `docs/game-content/census.md` presenting the same inventory readably, distinguishing stored sources from time-dependent served bytes and labeling the inactive mods pipeline explicitly; verify consistency against the JSON via the verifier cross-check

## 2. Offline verifier

- [ ] 2.1 Implement `tools/content-census/verify_content.py` using standard-library structural analysis of `config/main.json`, `config/patch/patches.txt`, patch files, and `mods/mods.txt` (parse only, never import the legacy application or apply patches) with exit codes 0/1/2 for agreement/drift/invalid; verify by running it against the current sources and confirming exit 0

- [ ] 2.2 Add a README for the tool documenting the executable, invocation, exit codes, evidence classification, and containment limits; verify the documented invocation leaves repository bytes unchanged

## 3. Regression tests

- [ ] 3.1 Add `tools/content-census/test_content_census.py` covering key extraction and counts, patch-order drift detection (exit 1), mods-status change (exit 1), unsupported shapes (exit 2), catalog/markdown consistency, and repository containment; verify with `python -B -m unittest discover -s tools/content-census -p test_content_census.py -v` exiting 0

## 4. Documentation and validation

- [ ] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where content-census checks belong; verify `openspec validate --strict` passes for the change
