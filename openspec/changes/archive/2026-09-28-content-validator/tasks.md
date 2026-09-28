# Tasks

## 1. Validator scaffold and package structure

- [x] 1.1 Create `packages/game-content/tools/validate_content.py` with the exit contract (0 success JSON report, 1 `validation-failed` report on stdout, 2 invalid input on stderr), deterministic report encoding, and problem records carrying (check family, file, entry `legacy_id`, field); verify with `python -B packages/game-content/tools/validate_content.py <bad-root>` exiting 2 on stderr and printing no validity report.
- [x] 1.2 Implement the structure/manifest-integrity family: manifest load with root + nine extension sections each recording `schema_version`/`result: success`/`policy`, schema-file structural validation (object schema, `required` ⊆ `properties`, `kind` const), two-directional set equality between `normalized/` and the manifest-recorded outputs, per-output byte count and SHA-256 verification, and the documented count-key mapping (file-verifiable counts only); verify with group-1 tests asserting each failure names its file/key and exits 1 (missing recorded output exits 2).
- [x] 1.3 Land group-1 tests in `packages/game-content/tests/test_validate_content.py`: happy structure on a disposable copy, unrecorded-file, tampered-bytes, count-drift, invalid-schema, and missing-file mutations plus a containment snapshot (package file set and bytes identical before/after); verify with `python -B -m unittest discover -s packages/game-content/tests -p test_validate_content.py -v` exiting 0.

## 2. Schema conformance

- [x] 2.1 Implement the documented-subset checker (required, type unions with bool-never-integer, const, enum, minimum, minItems/minProperties, propertyNames, additionalProperties false, nested object gates) and the output → schema mapping table covering all 21 schema-backed files; verify with a test that every committed entry of every schema-backed file passes (exit 0 path).
- [x] 2.2 Implement the schema-less special gates (`specials.json` exactly one entry, `legacy_id` `925`, `kind` special, exact recorded `special_note`); verify with tests that a second entry, a changed id, and a changed note each fail with exit 1 naming the deviation.
- [x] 2.3 Land group-2 tests including traceability-by-mutation: removing each schema-required field of every schema is caught, plus type/const/enum/minimum/propertyNames/unknown-property mutations per gate; verify with `python -B -m unittest discover -s packages/game-content/tests -p test_validate_content.py -v` exiting 0.

## 3. Dependency validation

- [x] 3.1 Implement identifier integrity: per-file `legacy_id` uniqueness, distinctness across the 900-entry items union, `upgrades_to`/`trains_ids` resolution excluding the `-1`/`0` sentinels, and `inventory_ids` object keys resolving against the inventory domain; verify with tests that a duplicate id, a cross-file duplicate, an unresolvable relation, and an unknown inventory key each fail with exit 1 naming the entry, field, and value.
- [x] 3.2 Implement derived-reference verification for every edge (collections `item_refs`/`prize_refs`, `level_ranking_reward.unit_refs`, `unit_collection_categories.unit_refs`, darts `item_refs`/`extra_ref`, offers `item_refs` with the shape traversal and both pinned anomalies, categories `sub` parents), taking each derivation rule and ordering from the owning builder's source; verify with tests that a resolvable-but-wrong reference fails (drift), an unresolvable reference fails, and either pinned anomaly changing fails.
- [x] 3.3 Land group-3 tests: one resolution mutation and one derivation-drift mutation per edge, sentinel handling, and the union-distinctness check; verify with `python -B -m unittest discover -s packages/game-content/tests -p test_validate_content.py -v` exiting 0.

## 4. Integration, containment, and documentation

- [x] 4.1 Land end-to-end CLI tests: subprocess exit 0 against the committed package, exit 1 on a mutated disposable copy, exit 2 on a missing/unparseable input, byte-identical reports across two runs, and full containment (no file created or modified outside the temp copies); verify with the suite exiting 0.
- [x] 4.2 Add the `content validator` extension section to `packages/game-content/README.md` (invocation, exit codes, evidence classification, containment) and run the documented command verbatim; verify the command's observed output and exit code match the documentation.
- [x] 4.3 Add the validator and suite commands to `AGENTS.md`'s verified-commands section; verify both documented commands execute successfully from the repository root.
- [x] 4.4 Run full discovery over the package suite set; verify `python -B -m unittest discover -s packages/game-content/tests -p "test_*.py"` exits 0 with all 11 suites passing (ten builders unaffected).

## 5. Verification and regression

- [x] 5.1 Re-run the prior verification batteries and guards; verify `powershell -File apps/client-godot/verify.ps1`, `powershell -File apps/client-godot/verify-boot.ps1`, `python -B apps/compat-api/guard_baseline.py verify`, and `python -B tools/hash-manifest/hash_manifest.py verify` all exit 0 with first-render and guard evidence unchanged.
- [x] 5.2 Validate the change against OpenSpec; verify `openspec validate content-validator --type change --strict` and `openspec validate --all --strict` both exit 0.
- [x] 5.3 Review the final diff; verify `git status`/`git diff --stat` show only the intended files (validator, suite, package README, AGENTS.md, change artifacts) and no normalized output, `manifest.json`, schema, legacy source, save, guarded, or M4/M5 evidence file changed.
