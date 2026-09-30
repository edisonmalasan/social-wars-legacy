# Tasks

## 1. Compatibility API: no change required (recorded finding)

- [x] 1.1 **Finding: the stored energy value already reaches the client, so no accessor is needed.** The design assumed `engine.apply_resources` never writes energy and therefore that the value had to be added to the service. Apply established the premise was false: `TownState.RESOURCE_FIELDS` already maps `energy` to `privateState.energy`, the committed fresh-save payload already carries the value, and the windowed capture renders `Energy: 50` with no absent-field indicator. Verified: `grep` for `displayed("coins")` across `apps/client-godot` returns no matches, and the evidence capture shows every row sourced.
- [x] 1.2 **The shared `resources()` accessor is untouched**, so no compat test or response-shape change was required and all nine delivered endpoints' value-level proofs and their committed executed-legacy parity fixtures stay valid unchanged — confirmed by the compat suite's `Ran 947 tests ... OK` in the final state.
- [x] 1.3 **The `godot-compatibility-boot` delta was narrowed** to the `GameApi` projection requirement; the bootstrap-service modification describing an additive energy path was removed, because no such path exists or is needed. The compat READMEs require no update for this change, and no error-table row was added, removed, or reworded.

## 2. Client projection and readout

- [x] 2.1 Add a new pure `scripts/town/resource_projection.gd` as the single source of truth: one entry per displayed resource with its canonical name (as the server names it), its save location, its group (`resources` or `summary`), and its display label, plus helpers that render a row's value or the explicit absent-field indicator. It SHALL NOT name a resource with a field the server never produces, SHALL NOT display the same resource twice, and SHALL place `xp` in the summary group — verify: the new suite asserts every entry resolves to a real field, that no entry is keyed `coins`, and that `xp` is grouped as a summary.
- [x] 2.2 Correct `scripts/town/town_hud.gd` to project through that module, keying the primary currency row `gold` and sourcing `energy` under the save's own name, with **no new row, no removed row, and no reordering** — verify: the rendered row set is the delivered ten (seven resources plus `name`, `level`, `xp`), and the suite asserts no row renders an absent-field indicator against a payload carrying the resources the service produces.
- [x] 2.3 Correct `tests/test_town_hud.gd`: replace the fabricated `"coins"` / `"energy"` payload fields with the names the service actually produces, and add assertions that `gold` renders its real stored value, that no row is keyed `coins`, that `energy` renders its stored value, and that a genuinely absent resource still renders the explicit absent-field indicator without affecting other rows — verify: the suite passes and the review record lists exactly which assertions were replaced and why.
- [x] 2.4 Add `tests/test_town_resources.gd`: a hermetic suite over the projection and the readout covering every resource row, the summary group, both absent-field paths, the response-driven update path (values re-rendered after a delivered state-mutating response), and the assertion that **no** delivered line's semantics change — verify: the suite passes with no process, server, or socket.

## 3. Batteries and evidence

- [x] 3.1 Register `test_town_resources` in `verify-boot.ps1`'s hermetic suite list and confirm all nine delivered state-mutating suites and every other suite still pass unchanged — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 with every documented marker and the suite count increases by exactly one.
- [x] 3.2 Capture the evidence into `apps/client-godot/evidence/building-resources/` (a windowed capture of the readout with every row sourced, and a headless `resources-report-v1` report recording the canonical projection table — row, canonical name, save location, group — the observed stored values, the input digests, the request counts, the established-versus-derived provenance split, and every non-claim from the delta, including the energy regeneration gap) — verify: both files are committed, the report carries all required fields, and a rerun reproduces the committed bytes.
- [x] 3.3 Run the full preservation battery in the final state — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, `python -B apps/compat-api/guard_baseline.py verify` exits 0 with identical digests before and after, the committed M4/M6 and every delivered slice's evidence bytes are unchanged apart from the regenerated per-run battery report, and `git diff` shows no legacy/fixture/save byte change beyond the sanctioned new files.

## 4. Documentation and integration review

- [x] 4.1 Update `docs/legacy-resources.md` with the resolutions, document the slice in `apps/client-godot/README.md` and `apps/compat-api/README.md`, and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one that was run successfully in this change, the canonical projection is documented row by row, and the energy regeneration gap is recorded wherever the resource is described.
- [x] 4.2 Perform the integration review: re-read the final diff against `proposal.md`/`design.md`/`specs/` and the investigation record, run `openspec validate building-resources --strict` and both batteries once more, and record residual gaps (the readout claims to display what the save stores, never what the legacy client displayed; the energy regeneration rule is unclaimed; the labels and layout are the delivered provisional convention; the market and trade counters and item cost mapping are out of scope; no pixel-parity oracle exists) — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

Re-read the final diff against `proposal.md`, `design.md` D1-D7, the revised spec, and
the investigation record, then re-ran both batteries myself in the final state.

### Requirement-to-evidence map

| Requirement | Evidence |
| --- | --- |
| Canonical resource projection | `scripts/town/resource_projection.gd` — 10 rows, each with canonical name, save location, group, label, typed-state field, and legacy vector slot; `test_town_resources.gd` asserts every entry resolves to a real field, that **no entry is keyed `coins`**, and that `xp` is grouped as a summary. `gold` → `map.gold`, slot 2. |
| Resource readout completeness | `town_hud.gd` projects through the module (its `FIELDS` const is gone). Root re-read the committed report: `readout.absent_rows == []`, `row_count == 10`, `displayed_values_are_the_stored_values: true`, `no_field_is_computed_or_substituted: true`, and `displayed` = `gold 2000, wood 2000, steel 2000, oil 2000, cash 5, energy 50, mana 0, name Warrior, level 1, xp 4`. A root grep for `displayed("coins")` across `apps/client-godot` returns **no matches**. |
| Eighth resource displayed, gap recorded | `energy` → `privateState.energy`, `vector_slot -1` in the report's table; the report's `energy_gap` records that `apply_resources` never writes it, the vector has no slot, no legacy branch touches it, and no regeneration rule is claimed. |
| No state-mutating surface changes | Compat suite **unchanged** at `Ran 947 tests ... OK`. Root confirmed `git status --porcelain` lists **no** path under `apps/compat-api/`, `config/`, `villages/`, `tests/saves/`, or any legacy source. |
| Evidence, provenance, claim limits | `evidence/building-resources/{resources.png,report.json}` (`resources-report-v1`, 14 keys, 8 non-claims, provenance splitting 6 established from 2 derived); digest `8ede5a64…892b2`, byte-identical across three runs including the explicit-path form. |
| Containment and preservation | See below. |
| Documented commands and assessment | `AGENTS.md` ("Verified building-resource commands"), both application READMEs, the updated `docs/legacy-resources.md`. |

### Verification actually run in the final state (orchestrator, not the worker)

| Check | Result |
| --- | --- |
| `res://tests/test_town_resources.gd` | 101 checks, PASS |
| `res://tests/test_town_hud.gd` | 38 checks, PASS (was 28) |
| `powershell -File apps/client-godot/verify.ps1` | exit 0 — `PASS all checks succeeded` |
| `powershell -File apps/client-godot/verify-boot.ps1` | exit 0 — `PASS all checks succeeded`; `test_town_resources exits 0`; guard digest `6978b959…ff348` pre=post |
| `python -B -m unittest discover -s apps/compat-api/tests` | `Ran 947 tests ... OK`, exit 0 — **unchanged** |
| `python -B tools/hash-manifest/hash_manifest.py verify` | exit 0 — 3,258 entries |
| `openspec validate building-resources --strict` | exit 0 |

### Correction made during the Apply stage — the design's own premise was wrong

The design assumed the stored energy value had to be **added to the service**, because
`engine.apply_resources` never writes it and no accessor exposed it. **Apply established
that premise was false**: `TownState.RESOURCE_FIELDS` already maps `energy` to
`privateState.energy`, the delivered payload already carries the value, and the capture
renders `Energy: 50` — the row was only ever unsourced *in the display table*, never
absent from the data. Root verified both halves before acting (`RESOURCE_FIELDS` line
111; the report's `absent_rows == []`).

The change was **narrowed rather than implemented as designed**, and the artifacts were
revised in the same commit: the spec's service-side *expose* requirement became a
requirement to display what the payload already carries; the `godot-compatibility-boot`
delta keeps only the `GameApi` requirement and its bootstrap-service modification was
**removed**; design D4 keeps the narrowing reasoning as the reason the shared `resources`
accessor stays untouched; tasks 1.1–1.3 became the recorded finding. **Net effect: the
Compatibility API is not modified at all.**

### Accepted worker deviations

- **`resources.png` reused the existing `--town-capture` flag** rather than a new
  `--resources-capture=`, for the same reason the report writer needed `town.gd`: adding
  a flag branch there is a view-file change outside the first worker's ownership. Same
  scene, same fake API, same boot→town handoff, same 1400×600 stage, same failure markers,
  byte-reproducible.
- Five suites said `"renders the authoritative coins"` rather than `"renders coins
  verbatim"`, so the same rename was applied to that phrase; `test_town_expand` needed no
  message change because it already read `gold`. All eleven edits are a queried-key or
  message change only — root confirmed via `git diff` that no assertion value, threshold,
  or intent moved.
- `TownState.Resources` still declares an internal `var coins` aliasing `map.gold`. **No
  readout row is keyed by it**; retiring it touches nine further `state.resources.coins`
  sites plus `state.missing`, so it is recorded as a separate correction rather than
  folded in.
- The resources report carries a hand-maintained `stored_values` constant (the committed
  fresh-save values) as a second assertion surface against the projection, documented
  in place.

### Evidence consequence, sanctioned and bounded

`evidence/town/town-player.png` and `evidence/town/report.json` were **regenerated**,
because `report.json`'s `hud` block comes from `hud.displayed_fields()` and the label
correction invalidated their bytes. Root verified the diff is confined to the two `hud`
blocks, where the key moves from `coins` to `gold` in both the fresh and slice views — no
count, digest, projection constant, camera, or selection block changed. Regeneration was
sanctioned by the spec for exactly this case; leaving the artifacts stale would have
broken the M6 deliverable's claim that rerunning the report reproduces its bytes.

### Residual gaps (all recorded as claim limits, none blocking)

- The readout claims to display **what the save stores**, never what the legacy client
  displayed; no pixel-parity oracle exists.
- **No rule is claimed for how `privateState.energy` changes over time.**
- Labels and layout are the delivered provisional convention; the shared panel clips long
  labels (pre-existing cosmetic note).
- Market/trade counters and item-cost mapping are out of scope; `TownState`'s internal
  `coins` alias remains.
- The report pins the projection and readout module digests, so editing either makes it
  stale — the same coupling the sibling reports have.
- Two environment flakes were observed by the first worker and are **not** caused by this
  change: one compat loopback smoke timeout with zero output (passes standalone), and one
  engine `CrashHandlerException: signal 11` in `test_town_store`. Neither recurred in the
  final runs.

