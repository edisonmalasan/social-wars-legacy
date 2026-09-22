## 1. Registry builder

- [x] 1.1 Implement the stdlib-only asset enumerator that walks the worktree with asset-extension includes and documented exclusions, records path/size/sha256/extension/directory-class/status per file in sorted POSIX order, and writes `registry.json` only on success; verify with byte-identical reruns and exclusion tests

- [x] 1.2 Implement the content reference extractor (item `img_name` parts, magic `img_name`, sound `file`, images paths from committed normalized outputs) plus the per-domain join rules, and write `coverage.json` with resolved/missing counts, missing-name lists, unreferenced counts, and corpus totals; verify the measured joins (sprites 862/872 + 10 missing, magic 10/10, sounds 138/138, images basename tiers)

- [x] 1.3 Add registry/coverage JSON schemas (or schema-equivalent required-field contracts enforced by the validator) plus validator checks for determinism, schema fields, join conformity, and exclusion integrity; verify every required field has a validator check and failures exit non-zero with no writes

## 2. Regression tests and docs

- [x] 2.1 Add focused tests covering enumeration counts, join match rates, validation failures (excluded leakage, drifted locale analogue, missing ref file, corrupt input), round-trip determinism, manifest-grade output stability, and containment (reads/writes sets, no asset mutation, no subprocess/network/Flash); verify the suite exits 0

- [x] 2.2 Document the registry extension in `tools/asset-registry/README.md` plus `docs/assets/registry.md` links (inputs, rules, exit codes, evidence, containment, worktree-vs-baseline distinction, prioritization use); verify the documented invocation leaves assets and sources unchanged

## 3. Documentation and validation

- [x] 3.1 Update the executed-check references in AGENTS.md where asset-registry checks belong; verify `openspec validate --strict` passes for the change
