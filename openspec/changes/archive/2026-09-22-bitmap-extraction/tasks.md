## 1. Image extractor

- [x] 1.1 Implement the stdlib-only bitmap re-walker with JPEG verbatim-plus-conditional-splice, JPEG3 alpha decode to grayscale PNG, lossless ARGB/colormap to RGBA PNG via the hand-rolled encoder, outputs under ignored `assets/converted/images/<swf-stem>/`, and `image_extraction.json` plus `statuses.json` merge only on success; verify format distribution and digest recomputation

- [x] 1.2 Implement validator checks for payload structure, zlib integrity, alpha dimension match, PNG re-parse, JPEG SOI, unknown-format refusal, schema fields, and determinism; verify failures exit non-zero with no writes

## 2. Regression tests and docs

- [x] 2.1 Add focused tests covering synthetic payloads per family and failure (including dormant splice path and colormap expansion), real spot checks with JPG/PNG re-parse, byte-identical reruns, regeneration from manifest digests, manifest-grade stability, and containment (read/write sets with ignored outputs, no source mutation, no subprocess/network/Flash/rendering); verify the suite exits 0

- [x] 2.2 Document the extractor in `tools/asset-registry/README.md` plus `docs/assets/registry.md` links (inputs, per-family rules, committed-vs-ignored output split, exit codes, evidence, containment); verify the documented invocation leaves sources unchanged

## 3. Documentation and validation

- [x] 3.1 Update `.gitignore` for bulk image outputs plus the executed-check references in AGENTS.md where bitmap extraction checks belong; verify `openspec validate --strict` passes for the change
