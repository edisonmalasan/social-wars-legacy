## 1. Building converter

- [x] 1.1 Implement the stdlib-only shape-style parser (bounds RECT, fill/line arrays, bitmap-fill IDs, raw matrices, edge counts) plus package assembly (package.json with identity, content ref, provenance, frame data, symbols, shape records, bitmap digests, placement tiles; byte-identical bitmap copies) and `conversions.json` plus `converted` statuses merge only on success; verify the house package against measured values

- [x] 1.2 Implement validator checks for bounds presence, bitmap-fill resolution, content-ref uniqueness, schema fields, and determinism; verify failures (unexpected shape, unresolvable fill, missing definition) exit non-zero with no writes

## 2. Regression tests and docs

- [x] 2.1 Add focused tests covering synthetic shape records per style type, the real house file, validation failures, byte-identical reruns, manifest-grade stability, and containment (exact read/write sets, no source mutation, no subprocess/network/Flash/rendering); verify the suite exits 0

- [x] 2.2 Document the converter in `tools/asset-registry/README.md` plus `docs/assets/registry.md` links (inputs, parsing boundary, exit codes, evidence, containment, no-rendering boundary); verify the documented invocation leaves sources unchanged

## 3. Documentation and validation

- [x] 3.1 Update the executed-check references in AGENTS.md where building conversion checks belong; verify `openspec validate --strict` passes for the change
