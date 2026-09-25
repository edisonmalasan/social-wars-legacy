## 1. Unit converter

- [x] 1.1 Implement the stdlib-only `convert_unit.py`: timeline inventory (depth-first `PlaceObject2` decode, `RemoveObject2`, `FrameLabel` frame indices, `DefineSprite`/`ShowFrame` counting, `SymbolClass` id-name pairs, `main` root entry), shape records via shared-parser import, package assembly (`package.json` with identity, unit definition ref, provenance, frame data, symbols, per-sprite animation states, shape records, bitmap digests; byte-identical bitmap copies), and `conversions.json` plus `converted` statuses merge only on success; verify against the measured elephant values (7 sprites, sprite 63 labels at frames 1/6/11/16/21, 28 shapes, 28 referenced bitmap ids) after running the documented extraction prerequisite

- [x] 1.2 Apply the shared style-array byte-alignment fix and the referenced-fill validation (unreferenced `65535` placeholders recorded verbatim, referenced fills must resolve); regenerate the house package and verify its `package_sha256` and bitmap digests are byte-identical, then verify the elephant parses 28 of 28 shapes

- [x] 1.3 Migrate the manifest envelope: `conversion.schema.json` const `conversion-v1` with per-entry `policy` and `output_bytes`, merge/preserve semantics in `convert_building.py` and `convert_unit.py` with the legacy fail-closed rules, regenerate the committed `conversions.json`, and verify both orders of the two converters yield byte-identical manifests

- [x] 1.4 Implement validator checks for animation-state coverage (sprite/label coverage, declared versus observed frame counts, character references), bitmap-fill resolution, content-ref uniqueness (unit 933), schema fields (`unit_package.schema.json`), and determinism; verify failures (unsupported timeline tag, unresolvable referenced fill, missing definition, legacy envelope under the unit converter) exit non-zero with no writes

## 2. Regression tests and docs

- [x] 2.1 Add focused tests covering synthetic sprite timelines (label frame indices, depth-first placements, removals, unsupported-tag rejection, frame-count mismatch), placeholder-fill handling, the real elephant file, validation failures, byte-identical reruns, manifest order-independence in both directions, legacy-envelope fail-closed paths, and containment (exact read/write sets, no source mutation, no subprocess/network/Flash/rendering); verify the suite exits 0

- [x] 2.2 Document the converter in `tools/asset-registry/README.md` plus `docs/assets/registry.md` links (inputs, extraction prerequisite, parsing boundary with depth-first placement order, label names-only rule, alignment rule, placeholder rule, envelope migration, exit codes, evidence, containment, no-rendering boundary); verify the documented invocation leaves sources unchanged

## 3. Documentation and validation

- [x] 3.1 Update the executed-check references in AGENTS.md where unit conversion checks belong; run the building and unit conversion suites plus `openspec validate --strict` for the change
