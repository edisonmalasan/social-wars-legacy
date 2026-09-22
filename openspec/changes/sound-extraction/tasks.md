## 1. MP3 extractor

- [ ] 1.1 Implement the stdlib-only DefineSound re-walker that validates format nibble 2 with sane characteristics, slices payloads from the first frame sync (uniform offset 9 asserted), writes one `.mp3` per character ID under `assets/converted/sounds/`, and writes `extraction.json` plus the `statuses.json` overlay only on success; verify the 27 real sounds extract with matching digests

- [ ] 1.2 Implement validator checks for format nibbles, sync uniformity, characteristics, schema fields, determinism, and registry-byte preservation; verify failures (non-MP3 format, shifted sync, corrupt input) exit non-zero with no writes

## 2. Regression tests and docs

- [ ] 2.1 Add focused tests covering synthetic DefineSound tags across format nibbles, real-file extraction with sync assertions, validation failures, byte-identical reruns, manifest-grade stability, and containment (exact read/write sets, no source mutation, no subprocess/network/Flash/decoding); verify the suite exits 0

- [ ] 2.2 Document the extractor in `tools/asset-registry/README.md` plus `docs/assets/registry.md` links (inputs, slicing rule, exit codes, evidence, containment, no-transcode boundary); verify the documented invocation leaves sources unchanged

## 3. Documentation and validation

- [ ] 3.1 Update the executed-check references in AGENTS.md where sound extraction checks belong; verify `openspec validate --strict` passes for the change
