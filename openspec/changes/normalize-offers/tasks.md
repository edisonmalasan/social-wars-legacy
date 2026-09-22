## 1. Normalized package

- [ ] 1.1 Create `packages/game-content/normalized/offer_packs.json` (44 definitions, one per stored entry) with `legacy_id`, source, content version, verbatim scalars, verbatim item shapes with shape classes, resolved references, and pinned anomaly notes in stored order; verify via the round-trip diff against stored content

- [ ] 1.2 Create `packages/game-content/schemas/offer_pack.schema.json` specifying required fields, types, and shapes; verify every schema-required field has a validator check via the traceability test

- [ ] 1.3 Extend `packages/game-content/manifest.json` building with offers inputs, coercion ruleset reference, definition counts, shape distribution, anomaly allowlist, reference-edge counts, and builder outcome; verify the manifest matches the produced output on every build while prior keys survive the merge untouched

## 2. Builder and validator

- [ ] 2.1 Implement the stdlib-only offers builder/validator that loads stored packs, preserves shapes verbatim, validates (id uniqueness, ref resolution outside the exact-match allowlist, structural conformity, required fields), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [ ] 2.2 Document the offers extension in the package README (inputs, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [ ] 3.1 Add focused tests covering classification counts (44) and shape classes, verbatim fidelity, validation failures (duplicate id, non-allowlisted anomaly, missing field), schema-validator traceability, exact round-trip including the float artifact, manifest consistency and merge preservation, and containment; verify the suite exits 0

## 4. Documentation and validation

- [ ] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where offers normalization checks belong; verify `openspec validate --strict` passes for the change
