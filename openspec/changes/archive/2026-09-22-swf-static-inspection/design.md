## Context

The registry records 1176 SWFs as opaque blobs. Direct reads prove all are `CWS` v10/11/15/17 and that stdlib-only static parsing (header, RECT, rate/count, tag walk to End) works on real files. No SWF tooling exists yet. This design scopes the second M4 slice: parse and record only. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Deterministic `inspection.json` keyed by registry path with header fields (signature, version, declared/actual length, frame rect/size, rate, count), tag inventory with counts, symbol/export names, embedded image/sound ID lists, and ActionScript-presence flags.
- Stdlib-only inspector/validator with well-formedness, termination, schema, and determinism guards; unreadable or unparseable corpus files fail explicitly.
- Focused tests on hand-built synthetic SWFs (FWS/CWS, shapes, sprites, sounds, ABC, multi-frame) plus read-only real-corpus spot checks and determinism.
- Corpus statistics (version distribution, scripted-file counts, embedded-asset totals) for conversion scoping.

**Non-Goals:**
- No bitmap/sound extraction, no timeline interpretation, no conversion of any kind.
- No registry mutation: `registry.json`/`coverage.json` stay as slice 1 wrote them; the inspection output joins by path at read time.
- No ActionScript decompilation or behavioral analysis beyond presence/counts.
- No Godot code or rendering verification of any kind.
- No claim of M4 exit; converted building/unit belong to later slices.

## Decisions

- **Parse, never execute.** `struct` header/RECT/tag parsing plus `zlib.decompress` for `CWS` bodies; `FWS` (uncompressed) and hypothetical `ZWS` (LZMA, stdlib `lzma` available) handled or explicitly refused with a clear diagnostic — corpus measures show `CWS` only, so other signatures fail closed as drift rather than silently passing.
- **Tag walk terminates at End or fails.** Overrun, truncation, or missing End tag is a validation failure identifying the file; the sample walk reached End cleanly and the suite asserts the same for the full corpus.
- **Names recorded, never interpreted.** SymbolClass/ExportAssets names and embedded IDs are carried verbatim; timeline order, label semantics, and script behavior are explicitly out of scope.
- **Declared length recorded, never trusted.** The observed declared/actual mismatch is stored as two numbers with a manifest note; walks are bounded by actual bytes.
- **Small domain module.** New inspector beside the registry builder sharing the schemas/tests/README pattern; no new dependencies.

## Risks / Trade-offs

- [Malformed-but-original files] → Any corpus file that fails strict parsing fails the build with its path identified; if genuine legacy corruption is found it must be classified (not silently skipped) before proceeding.
- [Version-specific tags] → Unknown tag codes are recorded by number, never rejected; only structural violations fail.
- [Large-file memory] → Largest file is 7.0 MB (52 MB uncompressed worst case); whole-body parse is acceptable, chunked hashing already precedent; no streaming parser needed.
- [Schema/validator drift] → Tests assert every required inspection field has a validator check.

## Migration Plan

Not applicable: new additive tooling plus one generated JSON file; no legacy migration, no rollout, no rollback beyond reverting the new files.
