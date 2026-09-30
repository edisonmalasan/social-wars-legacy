# Tasks

## 1. Executed-legacy expand fixture

- [x] 1.1 Implement the expand capture tool under `apps/compat-api/` (disposable-copy harness shared with the eight delivered captures: pinned-interpreter and containment checks, seed from `tests/saves/fresh-player.json`, crafted `<64-hex>;<json>` `data` envelope for one `expand` command carrying the **content-derived** debit, POST to `…/command.php`, sanitized `request.json`, full `before.json`/`after.json` saves, `response.body` + `response.meta.json`, `capture-manifest.json`, `README.md`) with offline unit tests for the envelope construction and sanitization — verify: `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` passes with the new tests included.
- [x] 1.2 Run the capture, commit `tests/fixtures/godot-building-expand/`, and confirm containment — verify: the capture exits 0, a rerun exits 0 and reproduces the committed fixture byte-identically except the documented time-dependent fields, every working-tree legacy source/config/village/save hash is identical before and after, and the eight delivered fixture directories with their manifests are untouched.
- [x] 1.3 Record the fixture's intent and the guard evidence — verify: the request carries the zero-cost committed row for a free id (indexes 0–3 are the only purchasable entries on this corpus under the requirements rule), the row grows by exactly one appended id with the existing `[35, 36, 45, 46]` unchanged, in order, and not deduplicated, `items`/`level`/`map_sizes`/`store`/`privateState`/`playerInfo` are unchanged, and the manifest and README record both guard probes (out-of-range, duplicate, and negative ids accepted; a non-integer id raising an unhandled error) plus the clamp-reaching probe.

## 2. Expansion execution endpoint (Compatibility API v0)

- [x] 2.1 Implement `apps/compat-api/expand_envelope.py`: the committed schedule accessor pair, `price_for(expansion_id)` returning the committed row or `None` for out of range, `resource_vector_for(row)` producing the 8-slot debit (`[0, 0, -coins, 0, 0, 0, -cash, 0]`, all zeros for a zero-cost row, refusing a non-integer row or non-integer/negative costs), and `build_envelope(expansion_id, vector, ts=None)` producing the six-key batch envelope with exactly one `[0, "expand", [expansion_id], vector]` command. The module docstring MUST name all four decisions (D1 the id-space indexing as **derived**, D2 `coins`→gold as **established by committed client asset names** `expansion_gold.jpg` / `expansion_cash.jpg`, D3 the requirements refusal, D6 the affordability refusal over the clamp), reuse the placement envelope's shared helpers unchanged, and state that the vector is a debit and that no claim is made about any land, grid, or buildable-cell effect — verify: new `test_expand_envelope.py` covers a priced row, the free row, the all-zero vector, every slot that must stay zero, the out-of-range case, the refusal paths, the shared-helper round trip, and real-config/fixture cross-checks.
- [x] 2.2 Add the content accessors in `compat_legacy.py` (in the delivered accessor style, returning `None` for absent or unusable values rather than coercing): the committed expansion schedule length, a committed row by expansion id, and the map's owned-expansions list — verify: new tests in `test_expand_endpoint.py` cover a resolving id, an out-of-range id, and a malformed row against the real config.
- [x] 2.3 Implement the `POST /v0/expand` route: intent validation fail-closed (JSON object, resolvable save id, integer expansion id), read the pre-execution owned list and the pre-execution `resources`, refuse `unknown_expansion_id` (404) for an id outside the schedule and `already_expanded` (409) for an owned id, refuse `expansion_requirements_unmet` (409) when the committed row records a positive `neighbors` or `inventory_qte`, refuse `insufficient_resources` (409) when a balance is below the derived debit, build the derived envelope, execute the unchanged `command()` dispatcher in-process, the two-part post-execution proof (the list grew by **exactly one** entry equal to the sent id **at the end** with every existing entry unchanged and in order, **and** every stored resource changed by **exactly** the derived debit), corpus-only persistence, and the superset response (`result` + both lists + the derived debit + the committed row + `resources`) — verify: new `test_expand_endpoint.py` covers the successful expansion with **both** proof parts, the free zero-cost row, each of the four refusals with a byte-identical corpus, the out-of-range and duplicate paths, every fail-closed code, the ignored client keys, and retained session/bootstrap byte-identity, all passing with no server.
- [x] 2.4 Implement the offline fixture-replay parity suite: the same envelope through the compat endpoint equals the captured legacy response and after-state for all stable fields, plus assertions that working-tree saves are never written by any expansion execution — verify: `test_expand_parity.py` passes with no network and `git status` shows no `saves/` or `tests/saves/` changes after the full compat test run.

## 3. GameApi expansion operation

- [x] 3.1 Add the typed `ExpandResult` (the pre-execution and post-execution owned lists, the derived debit, the committed row, `resources`, and the shared protocol/version/server-time/result fields with structured-failure fields) and its parse functions to `scripts/gameapi/boot_data.gd`, and `expand_town(user_id, expansion_id)` to `scripts/gameapi/game_api.gd` — verify: `test_game_api_fake.gd` extended for typed-shape, debit-parse, structured-failure, and out-of-range coverage passes headless.
- [x] 3.2 Implement `expand_town()` in `fake_api.gd` as the documented deterministic in-memory double over the committed expand fixture (derive the debit from the **fixture's own** committed schedule and the player's committed owned list, append the id to the end, apply the debit to exactly the named slots under `max(current + delta, 0)`, mirror the endpoint's refusal codes, and change nothing else) — verify: the fake suite covers a successful expansion, the free row, the out-of-range id, the duplicate id, the requirements refusal, the affordability refusal, and each fail-closed code with no process, server, or socket.
- [x] 3.3 Implement `expand_town()` in `legacy_v0_api.gd` (loopback JSON POST to the endpoint, typed result mapping, structured-error passthrough, the endpoint named only inside the legacy-v0 implementation) with live coverage against a running Compatibility API v0 — verify: the live GameApi suite passes inside `verify-boot.ps1`'s live phases and produces the same typed shapes as the fake.

## 4. Client expansion flow

- [x] 4.1 Add the typed owned-expansions list to the client's map state (read from the bootstrap's map record, never reordered, never deduplicated, fail-closed parsing in the shared parser), so the flow reads the authoritative list rather than tracking its own — verify: `tests/test_town_state.gd` extended for a present list, an absent list, a non-list value, and a list containing ids the schedule does not cover.
- [x] 4.2 Implement the pure expansion helpers in a new `scripts/town/expand_flow.gd` mirroring `collection_flow.gd` and `construction_flow.gd` (no node, request, or clock): the committed schedule rows, `is_purchasable(id, owned)` covering out-of-range / already-owned / requirement-blocked, `can_afford(debit, resources)`, the derived debit preview, the refusal reasons (`not_a_purchasable_expansion`, `already_expanded`, `expansion_requirements_unmet`, `insufficient_resources`), and the display text — verify: the helpers are unit-covered through the new suite across free, priced, owned, blocked, and unaffordable entries, and depend on no node, request, or clock.
- [x] 4.3 Implement the flow in the town scene: an expansion readout (the committed schedule, the owned ids, the next purchasable entry with its derived cost and affordability), an `Expand` action mutually exclusive with the six delivered modes, a confirm naming the **derived** debit as derived, exactly one `GameApi.expand_town()` intent, local refusals with no request, and success applying only the authoritative response (the owned list, the HUD balances, and the readout taken from the **response**) with a full snapshot-and-rollback — verify: the new `tests/test_town_expand.gd` covers the readout for every ownership and affordability state, the action gating, every refusal, one request per confirm, cancellation with a byte-identical town, mutual exclusion with all six delivered modes, the authoritative apply including the response-wins rule when the client's own debit differs, transport and structured-failure rollback, and the assertion that **no** terrain, grid, buildable-cell, or placement-bound behavior exists, while `test_town_collect.gd`, `test_town_construction.gd`, `test_town_upgrade.gd`, `test_town_store.gd`, `test_town_sell.gd`, `test_town_move.gd`, `test_town_purchase.gd`, `test_town_placement.gd`, and `test_town_selection.gd` still pass unchanged.
- [x] 4.4 Update the project-scope allow-list for the new script, suite, and evidence files — verify: `test_project_scope.gd` and `test_scene_build.gd` pass with the new entries and no forbidden token outside the legacy-v0 implementation.

## 5. Batteries, live phase, and evidence

- [x] 5.1 Register `test_town_expand` in the hermetic suite list and add the `expand-live` phase to `verify-boot.ps1` (start the Compatibility API over a disposable corpus, expand once, assert the typed response and its two-part value-level post-state proof, assert that a refused expansion left the corpus byte-identical, assert via `compat_live_phase.py --expect-save-mutation` that a corpus save mutated, tear down asserting port release and corpus cleanup with no working-tree `saves/`) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with every documented marker, including the new phase.
- [x] 5.2 Capture the windowed expand evidence and the deterministic report into `apps/client-godot/evidence/building-expand/` (fake-API windowed capture of the town with the expansion readout; headless `expand-report-v1` with inputs and digests, the intent, both owned lists, the derived debit, the committed schedule row used, the projection-constants pointer, the established-versus-derived provenance split, and every non-claim from the delta — including the land gap and the corpus consequence) — verify: both files are committed, the report lists all required fields, and a rerun of the report step reproduces its committed bytes.
- [x] 5.3 Run the full preservation battery in the final state — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, `python -B apps/compat-api/guard_baseline.py verify` exits 0 with identical digests before and after, the committed M4/M6 and every delivered slice's evidence bytes are unchanged, and `git diff` shows no legacy/fixture/save byte changes beyond the sanctioned new fixture directory, new script and suite, and new evidence files.

## 6. Documentation and integration review

- [x] 6.1 Update `docs/legacy-town-expansion.md` with the four questions as resolved (the id-space indexing as derived, `coins`→gold as established by the committed client asset names, the requirements refusal, the land-shape gap), record the two new committed-evidence findings (`expansion_gold.jpg` / `expansion_cash.jpg`; `PopupExpandMC` / `btnBuyExpandTileMC` / `expansion.png`) and the two new probe results (the server accepts out-of-range/duplicate/negative ids and raises on a non-integer; the clamp lands on zero); document the expand slice in `apps/client-godot/README.md` and `apps/compat-api/README.md` and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one that was run successfully in this change, and every derived rule is marked derived wherever it is recorded.
- [x] 6.2 Correct the roadmap Project Status ledger: record the `building-collect` archive PR #187 as merged as `7e54216` (it was written as pending at commit time), and clarify that the expansion-to-land mapping is a **known evidence gap bounding visual land growth**, not a blocker to the evidence-supported unlock-ledger slice, so the next eligible objectives remain resources and XP basics.
- [x] 6.3 Perform the integration review: re-read the final diff against `proposal.md`/`specs/`/`design.md` and the investigation record, run `openspec validate building-expand --strict` and both batteries once more, and record residual gaps (the id-space indexing derived; the corpus's owned ids incoherent and unboughtable under the requirements rule so the end-to-end transaction uses a free row; the clamp not exercised by the fixture; the affordability refusal preferred over reproducing the clamp; no land effect; one recorded transaction) — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

Re-read the final diff against `proposal.md`, `design.md` D1-D8, and
`specs/godot-building-expand/spec.md`, then re-ran both batteries in the final
state.

### Requirement-to-evidence map

| Spec requirement | Evidence |
| --- | --- |
| Executed-legacy expand fixture | `tests/fixtures/godot-building-expand/` - the request carries `[[0,"expand",[0],[0,0,0,0,0,0,0,0]]]`; root re-read the committed bytes: `expansions [35, 36, 45, 46]` -> `[35, 36, 45, 46, 0]`, grew by exactly one entry **at the end**, existing four unchanged and in order and **not** deduplicated; 40 items byte-identical; `level`, `increasedPopulation`, `store`, `race`, `skin`, `id`, `world_id` unchanged; `map_sizes` **absent before and after** (it lives in `playerInfo`); `privateState` and `playerInfo` byte-identical; all seven resources unchanged; `{"result":"success"}`; the login step leaves the save byte-identical. **No time-dependent field**, so a rerun reproduces the committed bytes exactly. |
| Expansion price derivation | `expand_envelope.py` (`price_for`, `resource_vector_for`) + the three `compat_legacy.py` accessors; `test_expand_envelope.py` (88 tests) covers a priced row, the free zero-cost row, the all-zero vector, every slot that must stay zero, out-of-range, the refusal paths, the shared-helper round trip, real-config cross-checks, and **AST checks that no land logic exists**. |
| Expansion execution endpoint | `POST /v0/expand` in `compat_service.py`; `test_expand_endpoint.py` (70 tests) covers the free success with **both** proof parts, a priced success via a stubbed purchasable row, all four refusals with a byte-identical corpus, the out-of-range and duplicate paths, every fail-closed code, the ignored client keys, and retained session/bootstrap byte-identity. |
| Expansion flow | `GameApi.expand_town()` on both implementations; `expand_flow.gd`; `test_town_expand.gd` (**615 checks**) including the response-wins rule on balances, the fail-closed ledger-divergence apply, one request per confirm, cancellation byte-identity, and symmetric mutual exclusion with all six delivered modes. |
| Land effect is a recorded gap | No terrain/grid/cell/placement-bound code exists: asserted at runtime (placements, objects, draw order, cells byte-identical) and by a structural token scan of `expand_flow.gd`'s non-comment lines. Recorded in the delta, both READMEs, the report's non-claims, `docs/legacy-town-expansion.md`, and the ledger. |
| Evidence, provenance, claim limits | `evidence/building-expand/building-expand.png` + `report.json` (`expand-report-v1`, 17 keys, 13 non-claims, a `provenance` section splitting 11 established facts from 5 derived ones). |
| Containment and preservation | See below. |
| Documented commands and assessment | `AGENTS.md` ("Verified building-expand commands"), both application READMEs, the updated `docs/legacy-town-expansion.md`, and the ledger correction of task 6.2. |

### Verification actually run in the final state

| Check | Result |
| --- | --- |
| `capture_expand_fixture.py` (worker ran it 3x) | exit 0 each time; containment digest identical each run; rerun diff exactly the 8 documented file+pointer paths, none in the state or the response |
| `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py"` | `Ran 947 tests ... OK`, exit 0 (768 before this change) |
| `godot --headless ... res://tests/test_town_expand.gd` | 615 checks, PASS |
| `powershell -File apps/client-godot/verify.ps1` | exit 0 - `PASS all checks succeeded` |
| `powershell -File apps/client-godot/verify-boot.ps1` | exit 0 - 25 hermetic suites, 12 live phases including `expand-live` |
| `python -B tools/hash-manifest/hash_manifest.py verify` | exit 0 - 3,258 entries |
| `python -B apps/compat-api/guard_baseline.py verify` | exit 0 - combined `6978b959...f7ff348`, identical pre=post |
| `openspec validate building-expand --strict` | exit 0 |

The root ran the batteries itself after both workers reported, and independently
re-read the fixture bytes, the request envelope, the report's provenance and
non-claims, and the diff scope (`git status --porcelain` shows no path under
`config/`, `villages/`, `tests/saves/`, `assets/`, or any legacy source).

### Corrections made during the Apply stage

- **The investigation record's saturation index was wrong.** It said the price
  "saturates from index 34"; computed per field from the real table, saturation
  begins at `cash` 11, `coins` 14, `neighbors` 18, and `inventory_qte` 33, with the
  whole row `100000/20/15/30` from 33 to 97. The capture manifest now records the
  computed census and the `34` claim was not carried into any implementation or
  document.
- **The investigation record misfiled `map_sizes` as a map field.** It lives in
  `playerInfo`; the corpus map record has no `map_sizes` at all, and the capture
  confirms it absent before and after. Corrected in the record.
- **A negative `expansion_id` is refused `invalid_expansion_id` (400), not
  `unknown_expansion_id` (404).** Structurally necessary: Python resolves
  `schedule[-1]` to the *last* row, so a negative id would otherwise be priced
  from a positive one.
- **`expansion_price` returns a shallow copy** of the committed row so a caller
  cannot mutate the loaded legacy configuration.

### Accepted worker deviations

- **The `Expand` action lives in its own UI-foundation slot**, not as a seventh
  button in the delivered building panel. Two delivered suites assert that panel's
  exact button list and are not this change's to edit, and the placement is
  architecturally correct: an expansion names **no placement**, so a
  building-targeted row would imply a target that does not exist. Mutual exclusion
  is symmetric - all six delivered modes gained an `expand_already_active` guard.
- `arm_expand`'s refusals reuse the delivered modes' own codes
  (`sell_already_active`, `construction_already_active`, ...) so both exclusion
  directions name the same condition.
- The priced path and `insufficient_resources` are reachable only through stubbed
  schedule rows (in the fake double, restored in memory afterwards) - the same
  documented mechanism the collect suite uses for `capped_collection`.

### Residual gaps (all recorded as claim limits, none blocking)

- The id-space indexing is derived; no legacy client was ever observed buying an
  expansion, and the corpus's own four owned ids are recorded as incoherent.
- The delivered transaction is a **zero-cost** expansion: 94 of 98 rows are
  requirement-blocked and every id the corpus owns is among them, so no balance
  moves and the value-level proof is exercised in its strictest but least
  discriminating form.
- **No land, grid, buildable-cell, or placement-bound behavior.** Closing the
  tile-to-cell gap needs new evidence, not a derivation.
- The clamp is not exercised by the fixture; the endpoint refuses an insufficient
  balance instead of absorbing it.
- Parity covers one recorded transaction against the fresh-player corpus.