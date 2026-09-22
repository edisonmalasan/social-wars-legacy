## Context

M3 left every content asset reference as a recorded string with existence explicitly M4. Direct reads show the on-disk corpus (1176 SWF fully accounted across 9 asset dirs, plus jpg/png/mp3 sets) and four joinable reference domains with pre-measured match rates. No asset tooling exists yet under `tools/`. This design scopes the first M4 slice: observe and record only. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Deterministic `registry.json` (path, size, sha256, extension, directory class, status) plus `coverage.json` (per-domain resolved/missing, missing-name lists, unreferenced counts, corpus totals) with ordered keys and byte-identical reruns.
- Stdlib-only builder/validator with corpus-determinism, schema, join-rule, and exclusion guards; failure exits without writing.
- Focused regression tests for enumeration, joins, validation failures, round-trip determinism, and containment.
- Documentation of invocation, evidence limits, and the prioritization input for later slices.

**Non-Goals:**
- No SWF parsing, symbol/dimension/frame extraction, or conversion of any kind.
- No asset mutation, relocation, or conversion-status advancement beyond the default `registered`.
- No asset-existence claims beyond worktree presence (distinct from baseline Git-blob integrity, which `legacy-manifest.json` owns).
- No Godot project, scene, rendering, or visual verification of any kind.
- No claim of M4 exit; converted building/unit and Godot render belong to later slices/M5/M6.

## Decisions

- **Worktree walk with explicit exclusions, not Git plumbing.** The builder walks the worktree with `pathlib`, including only asset extensions and excluding `.git/`, `saves/`, `temp/`, `build/{bundle,dist,work}`, and `new_assets/`. Hashes identify worktree bytes (documented as distinct from the baseline-blob hashes in `legacy-manifest.json`). Rationale: no subprocess dependency, no network, deterministic on a clean tree; alternative `git ls-files` rejected to preserve the no-subprocess containment precedent.
- **Join rules are per-domain and tiered.** Sprites by stem, magic by stem under its own dir, sounds by stem plus `.mp3`, images by basename with missing recorded per tier. Unmatched names are data (missing lists), never errors — the report's purpose is to surface gaps for prioritization.
- **Registry schema anticipates §11.** Fields cover the roadmap's registry subset knowable without parsing (path, hash, size, extension, directory class, status, source); symbol/dimensions/frames/pivot fields are explicitly deferred to the SWF-parsing slice, not stubbed with nulls.
- **Reference extraction reads committed normalized outputs only.** The builder never parses raw `config/main.json`; it consumes the M3 package (buildings/units/specials `img_name`, magics `img_name`, sounds `file`, images paths), keeping one source of truth per layer.
- **Small domain module.** New `tools/asset-registry/` package mirroring the M3 tool/test/README pattern; no new dependencies.

## Risks / Trade-offs

- [Worktree sensitivity] → Registry reflects the worktree, not the immutable baseline; documentation states the distinction and reruns are byte-identical only on unchanged trees.
- [Basename collisions] → Images basename joins may collide; the builder records all candidate paths per key and counts collisions explicitly rather than picking winners.
- [Ignored-dir drift] → New ignored asset dirs must be added to the exclusion list deliberately; unknown top-level dirs are enumerated, not skipped, so growth is visible.
- [Schema/validator drift] → Traceability-style tests assert every registry/coverage required field has a validator check.

## Migration Plan

Not applicable: new additive tooling plus two generated JSON files; no legacy migration, no rollout, no rollback beyond reverting the new files.
