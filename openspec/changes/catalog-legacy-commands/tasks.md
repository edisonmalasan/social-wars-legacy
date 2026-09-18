## 1. Catalog data

- [ ] 1.1 Create `docs/legacy-protocol/commands.json` with schema version, policy, the envelope contract, and one entry per command covering all 64 named dispatcher branches plus the unhandled fallthrough, each with classification, domain, argument shapes, resource effects, state reads/writes, persistence effects, client-trust notes, source references, and migration status; verify by running the focused test suite and confirming all entries load

- [ ] 1.2 Create `docs/legacy-protocol/commands.md` presenting the same inventory readably, grouped by domain, distinguishing source inspection from executed evidence and labeling debug, time-manipulation, and unhandled paths explicitly; verify consistency against the JSON via the verifier cross-check

## 2. Offline verifier

- [ ] 2.1 Implement `tools/command-catalog/verify_commands.py` using inert AST analysis of `command.py` (literal command-name comparisons only, no import or execution) with exit codes 0/1/2 for agreement/drift/invalid; verify by running it against the current source and confirming exit 0

- [ ] 2.2 Add a README for the tool documenting the executable, invocation, exit codes, evidence classification, and containment limits; verify the documented invocation leaves repository bytes unchanged

## 3. Regression tests

- [ ] 3.1 Add `tools/command-catalog/test_command_catalog.py` covering branch extraction, drift detection (exit 1), unsupported syntax (exit 2), catalog/markdown consistency, and repository containment; verify with `python -B -m unittest discover -s tools/command-catalog -p test_command_catalog.py -v` exiting 0

## 4. Documentation and validation

- [ ] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where command-catalog checks belong; verify `openspec validate --strict` passes for the change
