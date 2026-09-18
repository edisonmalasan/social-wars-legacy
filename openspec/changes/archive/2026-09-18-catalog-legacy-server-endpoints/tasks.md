## 1. Catalog data

- [x] 1.1 Create `docs/legacy-protocol/endpoints.json` with schema version, policy, and one entry per endpoint covering 15 explicit active routes, the implicit Flask static registration, and three commented-out auction declarations, each with classification, declared/effective methods, inputs, response branches, state effects, and source references; verify by running the focused test suite and confirming all 19 entries load

- [x] 1.2 Create `docs/legacy-protocol/endpoints.md` presenting the same inventory readably, distinguishing source inspection from executed evidence and labeling the alliance placeholder as not implemented; verify consistency against the JSON via the verifier cross-check

## 2. Offline verifier

- [x] 2.1 Implement `tools/endpoint-catalog/verify_endpoints.py` using inert AST analysis of `server.py` (constants and string concatenation only, no import or execution) with exit codes 0/1/2 for agreement/drift/invalid; verify by running it against the current source and confirming exit 0

- [x] 2.2 Add a README for the tool documenting the executable, invocation, exit codes, evidence classification, and containment limits; verify the documented invocation leaves repository bytes unchanged

## 3. Regression tests

- [x] 3.1 Add `tools/endpoint-catalog/test_endpoint_catalog.py` covering route extraction, drift detection (exit 1), unsupported syntax (exit 2), catalog/markdown consistency, and repository containment; verify with `python -B -m unittest discover -s tools/endpoint-catalog -p test_endpoint_catalog.py -v` exiting 0

## 4. Documentation and validation

- [x] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where endpoint-catalog checks belong; verify `openspec validate --strict` passes for the change
