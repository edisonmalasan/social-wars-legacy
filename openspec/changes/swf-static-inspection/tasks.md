## 1. Static inspector

- [ ] 1.1 Implement the stdlib-only SWF parser (FWS/CWS headers, RECT, rate/count, tag walk to End, SymbolClass/ExportAssets names, DefineBits/JPEG and DefineSound IDs, DoABC/DoAction flags) that inspects every registry `.swf` entry and writes `inspection.json` keyed by path only on success; verify against hand-built synthetic SWFs covering shapes, sprites, sounds, ABC, actions, and multi-frame timelines

- [ ] 1.2 Implement validator checks for header well-formedness, walk termination, non-`CWS` refusal, schema fields, and determinism, plus corpus statistics (version distribution, scripted-file counts, embedded-asset totals); verify failures exit non-zero with no writes and the sample file inspects as measured

## 2. Regression tests and docs

- [ ] 2.1 Add focused tests covering synthetic parse correctness per tag family, real-corpus spot checks (counts, versions, termination across all 1176 files), validation failures (truncation, bad signature, missing End, corrupt registry input), byte-identical reruns, manifest-grade output stability, and containment (exact read/write sets on fixtures, no asset mutation, no subprocess/network/Flash); verify the suite exits 0

- [ ] 2.2 Document the inspector in `tools/asset-registry/README.md` plus `docs/assets/registry.md` links (inputs, tag coverage, exit codes, evidence, containment, execution boundary); verify the documented invocation leaves assets and sources unchanged

## 3. Documentation and validation

- [ ] 3.1 Update the executed-check references in AGENTS.md where SWF inspection checks belong; verify `openspec validate --strict` passes for the change
