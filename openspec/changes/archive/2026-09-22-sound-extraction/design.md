## Context

Inspection inventoried 27 DefineSound tags, all MP3 in `assets/swf/dynamic2.swf`; direct reads confirm the tag layout (ID + characteristics byte + 6 header bytes + frames from the first `FF Ex` sync at payload offset 9, uniform across all 27) with varying rates (5.5–44 kHz nibbles), sizes, and mono/stereo types. No extraction tooling exists yet. This design scopes the third M4 slice: slice MP3 frames verbatim. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- 27 verbatim `.mp3` outputs under `assets/converted/sounds/` named by character ID, each sliced from its tag's first frame sync to payload end.
- `extraction.json` with per-sound source tag, characteristics (format/rate/size/type nibbles), sync offset, output digest, and byte counts; `statuses.json` overlay advancing the 27 registry paths to `extracted`.
- Stdlib-only extractor/validator with format, sync-offset, characteristic, schema, and determinism guards; non-MP3 formats fail closed.
- Focused tests on synthetic DefineSound tags (MP3 plus every other format nibble) and the real file, plus determinism and containment.

**Non-Goals:**
- No transcoding, resampling, or re-encoding: MP3 stays MP3.
- No sample decoding or playback of any kind.
- No registry/coverage/inspection mutation: outputs join by path at read time; the overlay carries status.
- No bitmap extraction or timeline work.
- No Godot code or rendering verification of any kind.
- No claim of M4 exit; converted building/unit belong to later slices.

## Decisions

- **Slice from first sync, validate uniformity.** Payload bytes before the first `FF Ex` sync (seek/header area) are dropped; the sync offset must be 9 for every sound — any deviation fails as drift, since uniformity is the measured invariant.
- **Characteristics recorded, never normalized.** Rate/size/type nibbles are stored per sound; no conversion to Hz labels beyond the documented nibble table, no audio interpretation.
- **Converted outputs are committed evidence.** 27 small MP3s (total under 200 KB) live under `assets/converted/sounds/` like M3 normalized outputs; raw sources stay byte-identical per AGENTS.md separation rules.
- **Overlay, not registry rewrite.** `statuses.json` maps registry paths to `extracted`; the registry file keeps its slice-1 bytes so its determinism tests stay green.
- **Small domain module.** New extractor beside the registry tools sharing the schemas/tests/README pattern; no new dependencies.

## Risks / Trade-offs

- [Sync heuristic] → Slicing from the first sync assumes no false `FF Ex` in the 6 header bytes; the fixed-offset-9 assertion plus per-file sync scan makes deviation fail closed rather than silently shift.
- [Rate nibble semantics] → Nibble-to-Hz mapping is recorded as observed codes with the standard table cited, not derived by playback.
- [Future non-MP3 sounds] → Any DefineSound with format nibble other than 2 fails the build until the slice is extended.
- [Schema/validator drift] → Tests assert every required extraction field has a validator check.

## Migration Plan

Not applicable: new additive tooling plus generated outputs; no legacy migration, no rollout, no rollback beyond reverting the new files.
