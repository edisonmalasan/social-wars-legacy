## 1. Normalized package

- [x] 1.1 Create `packages/game-content/normalized/buildings.json` (470 definitions) and `units.json` (429 definitions) with one definition per loaded items entry — stored 778 split `b` 469 / `u` 308 / `l` 1 plus patch-appended `b` 1 (id `302`) and `u` 121, all 900 ids distinct — each preserving `legacy_id`, source, content version, asset references, coerced costs, and resolved relations, plus a documented special for id `925`; verify via the round-trip diff against loaded legacy content

- [x] 1.2 Create `packages/game-content/schemas/building.schema.json` and `unit.schema.json` specifying required fields, types, cost maps, and reference shapes; verify every schema-required field has a validator check via the traceability test

- [x] 1.3 Create `packages/game-content/manifest.json` recording input sources with versions, layering order, coercion ruleset version, definition counts, and builder outcome; verify the manifest matches the produced output on every build

## 2. Builder and validator

- [x] 2.1 Implement the stdlib-only builder/validator that loads `config/main.json`, mirrors legacy layering without importing it (ordered patch application for observed ops, keep-later dedup), classifies, coerces per documented rules, validates (duplicates, `upgrades_to`/`trains_ids`/item-id resolution, cost keys/amounts, required fields), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [x] 2.2 Add a README for the package documenting inputs, layering, coercion rules, validation gates, exit codes, evidence classification, and containment; verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [x] 3.1 Add focused tests covering classification counts (469/308/1), coercion rules, validation failures (duplicate ID, unresolvable reference, bad cost, missing field), schema-validator traceability, round-trip fidelity modulo documented coercions, manifest consistency, and containment; verify the suite exits 0

## 4. Documentation and validation

- [x] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where normalization checks belong; verify `openspec validate --strict` passes for the change
