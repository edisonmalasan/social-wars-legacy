## 1. Survey data

- [x] 1.1 Create `docs/game-content/field-types.json` with schema version, policy, deterministic predicate definitions, and one entry per content source covering per-field encoding profiles for all 15 array-of-object keys and value-shape profiles for all 5 object keys of `config/main.json`, each with source references; verify by running the focused test suite and confirming all entries load

- [x] 1.2 Create `docs/game-content/field-types.md` presenting the same survey readably, distinguishing observed encodings from normalization decisions and labeling mixed-encoding keys explicitly; verify consistency against the JSON via the verifier cross-check

## 2. Offline verifier

- [x] 2.1 Implement `tools/field-survey/verify_fields.py` using standard-library structural profiling of `config/main.json` (exact recomputation, shared predicate functions, never import the legacy application) with exit codes 0/1/2 for agreement/drift/invalid; verify by running it against the current sources and confirming exit 0

- [x] 2.2 Add a README for the tool documenting the executable, invocation, exit codes, evidence classification, and containment limits; verify the documented invocation leaves repository bytes unchanged

## 3. Regression tests

- [x] 3.1 Add `tools/field-survey/test_field_survey.py` covering profile extraction, numeric-grammar and embedded-JSON predicate edge cases, drift detection (exit 1), unsupported shapes (exit 2), catalog/markdown consistency, and repository containment; verify with `python -B -m unittest discover -s tools/field-survey -p test_field_survey.py -v` exiting 0

## 4. Documentation and validation

- [x] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where field-survey checks belong; verify `openspec validate --strict` passes for the change
