## Why

The asset registry (M4 slice 1) records every SWF as an opaque byte blob: path, hash, size, and default status. Conversion prioritization and tooling design need to know what is *inside* each SWF — frame counts, animation structure, symbol/export names, embedded bitmaps and sounds, and ActionScript presence — without executing anything. A static inspection slice fills exactly the registry fields that parsing makes knowable and tells the conversion slice which files are simple (static art) versus complex (scripted timelines, nested sprites).

## What Changes

- Add `tools/asset-registry/inspect_swf.py` (stdlib-only: `struct` + `zlib`, no new dependencies) that reads every registry `.swf` entry, parses headers (signature, version, declared/actual length, frame rect/size, frame rate, frame count) and walks tags (code inventory with counts, SymbolClass/ExportAssets names, DefineBits/JPEG and DefineSound IDs, DoABC/DoAction presence), and writes `tools/asset-registry/inspection.json` keyed by registry path plus a console/JSON report. Parse failures on real corpus files are validation failures, not skips.
- Validate: header well-formedness, tag-walk termination (End tag reached, no overrun), schema fields, and byte-identical reruns. Report version distribution, ActionScript-bearing files, and embedded-asset counts for conversion scoping.
- Leave all source SWFs, registry outputs, content, and behavior unchanged; write only `inspection.json` on success; claim no conversion, no rendering, no behavioral interpretation of timelines or scripts.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| SWF corpus under `assets/` | 1176 files, all `CWS` (zlib) signatures, versions 10 (659) / 11 (377) / 15 (124) / 17 (16), 0 unreadable; sizes 754 B – 7.0 MB |
| Parse approach | Proven on `assets/sprites/0001_house_1_m.swf` with stdlib only: header + RECT + rate/count + full tag walk to End (tags seen include FileAttributes, SymbolClass, Metadata, DefineScene/DoABC-range, shapes, Place/RemoveObject, DefineSprite, ShowFrame) |
| Declared-vs-actual length | Sample declares 10389 B for a 9484 B file: both recorded, mismatch never fails the build (known SWF field unreliability) |
| Execution boundary | Static byte reads and `zlib.decompress` only; no ActionScript execution, no rendering, no Flash runtime in any form |

## Capabilities

### New Capabilities

- `swf-static-inspection`: Static SWF header/tag/symbol inventory with builder/validator, inspection output, and manifest-grade determinism.

### Modified Capabilities

None.

## Impact

Adds `tools/asset-registry/inspect_swf.py` plus generated `inspection.json`, focused tests (hand-built synthetic SWFs plus read-only real-corpus spot checks), schema, and docs links. Uses Python 3.9 standard-library tooling with no dependency upgrade, no server import, no network, no browser, no Flash execution, no asset mutation, and no Godot code. Bitmap/sound extraction, timeline conversion, and converted buildings/units remain future M4 slices; Godot rendering verification belongs to M5/M6 and is not claimed here.
