# Tasks

## 1. Executed-legacy collect fixture

- [x] 1.1 Implement the collect capture tool under `apps/compat-api/` (disposable-copy harness shared with the seven delivered captures: pinned-interpreter and containment checks, seed from `tests/saves/fresh-player.json`, crafted `<64-hex>;<json>` `data` envelope for one `collect` command carrying the **content-derived** payout, POST to `…/command.php`, sanitized `request.json`, full `before.json`/`after.json` saves, `response.body` + `response.meta.json`, `capture-manifest.json`, `README.md`) with offline unit tests for the envelope construction and sanitization — verify: `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` passes with the new tests included.
- [x] 1.2 Run the capture, commit `tests/fixtures/godot-building-collect/`, and confirm containment — verify: the capture exits 0, a rerun exits 0 and reproduces the committed fixture byte-identically except for the documented time-dependent fields (including the row's re-stamped collection instant), every working-tree legacy source/config/village/save hash is identical before and after, and the seven delivered fixture directories with their manifests are untouched.
- [x] 1.3 Record the two probes that shaped this line in the fixture README and the manifest — verify: they state that `collect` writes only the collection instant and applies the client-sent vector verbatim (probe 1), and that a collection on a just-started construction overwrites the build's start instant while the countdown survives while the legacy server answers success (probe 2, the evidence for the `item[3]` overlap refusal).

## 2. Collection execution endpoint (Compatibility API v0)

- [x] 2.1 Implement `apps/compat-api/collect_envelope.py`: the closed resource-type vocabulary, the paired ladder accessors, `tier_for(elapsed_seconds)` (highest committed rung reached, clamped at the top), `payout_for(item_fields, tier)` producing the derived 8-slot vector (`[0, xp × mult, amount × mult in the collect_type slot, 0, 0, 0, 0]` with the unread slot and the mana slot always zero), and `build_envelope(item_index, vector, ts=None)` producing the six-key batch envelope with exactly one `collect` command — every rung and rule marked derived-provisional in the docstring, with the six decisions named (D1 amount formula, D2 experience scaling, D3 sub-first-rung refusal, D4 cap refusal, D5 shared-field refusal, D6 cash/mana mapping) and fail-closed `EnvelopeError`s for non-integer input, an unknown resource type, a non-integer or negative vector entry, and a bad timestamp, reusing the placement envelope's shared helpers unchanged — verify: new `test_collect_envelope.py` covers each rung including the top-clamp case, each resource-type mapping, the zero slots, the shared-helper round trip, and real-config/fixture cross-checks.
- [x] 2.2 Add the content accessors in `compat_legacy.py` (mirroring the delivered `item_upgrade_to` / `item_build_time` patterns and their `LegacyBootError` style): the item's committed collection amount, collection type, collection experience, and collection cap, each returning `None` for an absent or unusable value rather than coercing, plus the paired ladder accessors — verify: new tests in `test_collect_endpoint.py` cover a resolving item, an absent field, a non-integer field, and a cap-bearing item against the real config.
- [x] 2.3 Implement the `POST /v0/collect` route: intent validation fail-closed (JSON object, resolvable save id, integer item index present in the save's placements), pre-execution row read, the content refusals (`capped_collection` 409 for a non-zero cap, `unknown_collect_type` 409, `no_income` 409 for a zero amount), the `construction_in_progress` 409 refusal for a row whose attribute bag carries a countdown or a click counter, the `too_early` 409 refusal when no committed rung is reached, the derived envelope, in-process execution of the unchanged `command()` dispatcher, the two-part post-execution proof (the row still exists, its collection instant moved **forward**, and **every** stored resource changed by exactly the derived delta), corpus-only persistence, and the superset response (`result` + both rows + the derived payout with its rung + the reference instant + `resources`) — verify: new `test_collect_endpoint.py` covers the successful collection with its value-level proof, each content refusal, the construction-state refusal with a byte-identical corpus, the unknown-index path, every fail-closed code, the neutral-slot assertions, the ignored client keys, and retained session/bootstrap byte-identity, all passing with no server.
- [x] 2.4 Implement the offline fixture-replay parity suite: the same envelope through the compat endpoint equals the captured legacy response and after-state for all stable fields with the documented time-dependent normalizations, plus assertions that working-tree saves are never written by any collection execution — verify: `test_collect_parity.py` passes with no network and `git status` shows no `saves/` or `tests/saves/` changes after the full compat test run.

## 3. GameApi collection operation

- [x] 3.1 Add the typed `CollectResult` (the pre-execution `previous` row and the post-execution `row`, both reusing the existing typed placement entry shape, plus the derived payout with its rung, the reference instant, `resources`, and the shared protocol/version/server-time/result fields with structured-failure fields) and its parse functions to `scripts/gameapi/boot_data.gd`, and `collect_income(user_id, item_index)` to `scripts/gameapi/game_api.gd` — verify: `test_game_api_fake.gd` extended for typed-shape, payout-parse, structured-failure, and unknown-index coverage passes headless.
- [x] 3.2 Implement `collect_income()` in `fake_api.gd` as the documented deterministic in-memory double over the committed collect fixture (derive the payout from the **fixture's own** committed content and the row's pre-execution instant, apply it to exactly the named resource slot and the experience, re-stamp the row's collection instant, change nothing else, and return the same envelope shape the service returns) — verify: the fake suite covers a successful collection, the construction-state refusal, a capped item, an unmappable type, a stale index, an unknown index, and each fail-closed code with no process, server, or socket.
- [x] 3.3 Implement `collect_income()` in `legacy_v0_api.gd` (loopback JSON POST to the endpoint, typed result mapping, structured-error passthrough, the endpoint named only inside the legacy-v0 implementation) with live coverage against a running Compatibility API v0 — verify: the live GameApi suite passes inside `verify-boot.ps1`'s live phases and produces the same typed shapes as the fake.

## 4. Client collection flow

- [x] 4.1 Add the typed collection clock to the client's placement (the row's recorded collection instant, distinct from the construction start instant the delivered construction line already reads) with fail-closed parsing in the shared placement parser, so one rule set reads the row's shared field — verify: `tests/test_town_state.gd` extended for a row with no collection state, a row with a re-stamped instant, and a row carrying construction state.
- [x] 4.2 Implement the pure collection helpers in a new `scripts/town/collection_flow.gd` mirroring `construction_flow.gd` and `move_flow.gd` (no node, request, or clock): the committed ladder, the reached rung and the next rung's remaining time for a supplied instant, the derived payout preview, the refusal reasons (`no_income`, `not_addressable`, `too_early`, `construction_in_progress`, `capped`), and the display text — verify: the helpers are unit-covered through the new suite across every rung and every refusal, and depend on no node, request, or clock.
- [x] 4.3 Implement the flow in the town scene: a collection readout for a selected income-bearing building (yield, resource, rungs, next-rung countdown), a `Collect` action mutually exclusive with the five delivered modes, a confirm naming the **derived** payout, exactly one `GameApi.collect_income()` intent, local refusals with no request, and success applying only the authoritative response (the typed row replaced from the response's post-execution row, the same object retained in depth order, and the HUD balances, experience, and readout taken from the **response** rather than from the client's arithmetic) with a full snapshot-and-rollback — verify: the new `tests/test_town_collect.gd` covers the readout for every construction/income state, the action gating, every refusal, one request per confirm, cancellation with a byte-identical town, the authoritative apply including the response-wins rule when the client's own payout differs, transport and structured-failure rollback, and the construction-state refusal, while `test_town_construction.gd`, `test_town_upgrade.gd`, `test_town_store.gd`, `test_town_sell.gd`, `test_town_move.gd`, `test_town_purchase.gd`, `test_town_placement.gd`, and `test_town_selection.gd` still pass unchanged.
- [x] 4.4 Update the project-scope allow-list for the new script, suite, and evidence files — verify: `test_project_scope.gd` and `test_scene_build.gd` pass with the new entries and no forbidden token outside the legacy-v0 implementation.

## 5. Batteries, live phase, and evidence

- [x] 5.1 Register `test_town_collect` in the hermetic suite list and add the `collect-live` phase to `verify-boot.ps1` (start the Compatibility API over a disposable corpus, collect once, assert the typed response, its value-level post-state proof, and that the construction timers of a refused row were left untouched, assert via `compat_live_phase.py --expect-save-mutation` that a corpus save mutated, tear down asserting port release and corpus cleanup with no working-tree `saves/`) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with every documented marker, including the new phase.
- [x] 5.2 Capture the windowed collect evidence and the deterministic report into `apps/client-godot/evidence/building-collect/` (fake-API windowed capture of the town with the collection readout; headless `collect-report-v1` with inputs and digests, the intent, both rows, the derived payout and rung, the committed ladder, the next-rung countdown, the resource movement, the projection-constants pointer, the established-versus-derived split, and every non-claim from the delta) — verify: both files are committed, the report lists all required fields, and a rerun of the report step reproduces its committed bytes.
- [x] 5.3 Run the full preservation battery in the final state — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, `python -B apps/compat-api/guard_baseline.py verify` exits 0 with identical digests before and after, the committed M4/M6 and every delivered slice's evidence bytes are unchanged, and `git diff` shows no legacy/fixture/save byte changes beyond the sanctioned new fixture directory, new script and suite, and new evidence files.

## 6. Documentation and integration review

- [x] 6.1 Update `docs/legacy-collect-income.md` with the six decisions as resolved (amount formula, experience scaling, sub-first-rung refusal, cap refusal, the shared-field refusal with the probe that forced it, and the cash/experience mapping) and record the second probe's result; document the collect slice in `apps/client-godot/README.md` and `apps/compat-api/README.md` (the content-derived payout, the value-level post-state proof, the construction-state refusal, the readout, evidence paths, claim limits) and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one that was run successfully in this change, with its purpose and constraints stated, and every one of the six decisions is marked derived-provisional wherever it is recorded.
- [x] 6.2 Perform the integration review: re-read the final diff against `proposal.md`/`specs/`/`design.md` and the investigation record, run `openspec validate building-collect --strict` and both batteries once more, and record residual gaps (every payout number derived, the cap and sub-first-rung refusals stub-only, the clamp not exercised by the fixture, decorations-only corpus, the shared-field refusal as the safest evidence-supported rule, one recorded transaction) — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

Re-read the final diff against `proposal.md`, `design.md` D1-D10, and
`specs/godot-building-collect/spec.md`, then re-ran the batteries.

### Requirement-to-evidence map

| Spec requirement | Evidence |
| --- | --- |
| Executed-legacy collect fixture | `tests/fixtures/godot-building-collect/` - `request.json` carries `[[0,"collect",[2],[0,3,0,60,0,0,0,0]]]`; `before.json` row 2 `[905, 53, 39, 0, 0, [], {}, 1]` -> `after.json` row 2 `[905, 53, 39, 1790705901, 0, [], {}, 1]`; `xp 4 -> 7`, `wood 2000 -> 2060`; the other five resources, all 39 other rows, `store {}`, `privateState`, and `playerInfo` byte-identical; 40 -> 40 placements; `response.body` `{"result":"success"}`. Verified directly from the committed files. |
| Collection payout derivation | `apps/compat-api/collect_envelope.py` (`tier_for` clamped at the top, `payout_for` with slots 0 and 7 always zero) + `compat_legacy.py`'s five accessors; `test_collect_envelope.py` covers every rung, every mapping, and the minutes-to-seconds boundaries from both sides; the two refusals are covered in `test_collect_endpoint.py`. |
| Collection execution endpoint | `POST /v0/collect` in `compat_service.py`; `test_collect_endpoint.py` (57 tests) covers the success with **both** proof parts, all twelve fail-closed codes, the ignored client keys, and retained session/bootstrap byte-identity. |
| Refusal on a row under construction | `construction_in_progress` is checked before the dispatcher; the test asserts the corpus is byte-identical; the client side is `collection_flow.gd` + the `Collect` action's gating in `town.gd`, covered by `test_town_collect.gd`; the evidence is executed probe 2, recorded in the fixture manifest, the investigation note, and the report's `provenance.established`. |
| Collection flow | `GameApi.collect_income()` on both implementations; `collection_flow.gd`; the sixth mutually exclusive mode in `town.gd`; `test_town_collect.gd` (379 checks) including the response-wins rule when the client's own payout differs, one request per confirm, cancellation byte-identity, and rollback. |
| Evidence, provenance, claim limits | `evidence/building-collect/building-collect.png` + `report.json` (`collect-report-v1`, 13 non-claims, a `provenance` section splitting 6 established facts from 7 derived ones including the report's own provenance). |
| Containment and preservation | See the verification list below. |
| Documented commands and assessment | `AGENTS.md` ("Verified building-collect commands"), both application READMEs, and the updated `docs/legacy-collect-income.md`. |

### Verification actually run in the final state

| Check | Result |
| --- | --- |
| `capture_collect_fixture.py` (twice) | exit 0, byte-identical rerun except the documented time-dependent leaves |
| `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py"` | `Ran 768 tests ... OK`, exit 0 (616 before this change) |
| `godot --headless ... res://tests/test_town_collect.gd` | 379 checks, PASS |
| `powershell -File apps/client-godot/verify.ps1` | exit 0 - `PASS all checks succeeded` |
| `powershell -File apps/client-godot/verify-boot.ps1` | exit 0 - 24 hermetic suites, 11 live phases including `collect-live` |
| `python -B tools/hash-manifest/hash_manifest.py verify` | exit 0 - 3,258 entries |
| guard digest before/after `verify-boot.ps1` | `6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348` both times |
| `openspec validate building-collect --strict` | exit 0 |

### Corrections made during the Apply stage

- **A unit bug the design itself contained.** `COLLECT_MINUTES` is committed in
  **minutes** while both row instants are Unix **seconds**. The design's D1
  compared the two directly, and the compat worker's first implementation did
  too, which would have paid the top rung within five seconds. Corrected in D1
  and carried into the endpoint, the client helper, the report, all three
  application documents, and the ladder's boundary tests at 299/300,
  3599/3600, 14399/14400, and 28799/28800.
- **A route-ordering bug in the new endpoint**, caught by the compat worker
  itself: a guard read state before that state was loaded.

### Accepted worker deviations

- `test_town_construction.gd` (outside the client worker's ownership) was edited
  to add one entry to the shared surface's button-list assertion, because that
  surface now carries a sixth mode. Reviewed: the added entry is a list item
  plus a comment; the assertion still proves the same thing (the four delivered
  actions, the build action, the collect action, one confirm, one cancel).
- The `collect-live` phase drives map key 21 rather than key 2, because the
  earlier `store-live` phase pops key 2 from its disposable corpus. Same class
  of decision as the delivered `no_upgrade_path` live check.

### Residual gaps (all recorded as claim limits, none blocking)

- Every payout number is derived; no legacy client was ever observed sending one.
- The `capped_collection`, `unknown_collect_type`, and `too_early` refusals are
  stub-covered, because no corpus row can reach them.
- The clamp is never exercised - a derived payout never drives a balance below zero.
- The corpus's only income-bearing rows are decorations; no factory is placed.
- The shared-field question is closed by a two-layer **refusal**, not by
  modelling what the legacy client would have done.
- The lower ladder rungs are pure-helper covered, never against a live clock.

