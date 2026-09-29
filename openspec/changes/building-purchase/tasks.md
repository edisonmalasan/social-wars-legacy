# Tasks

## 1. Executed-legacy purchase fixture

- [x] 1.1 Implement the purchase capture tool under `apps/compat-api/` (disposable-copy harness shared with the boot/placement captures: pinned-interpreter and containment checks, seed from `tests/saves/fresh-player.json`, crafted `<64-hex>;<json>` `data` envelope for one `buy_stored_item_cash` command whose cash price is derived from the item's config `costs`, POST to `…/command.php`, sanitized `request.json`, full `before.json`/`after.json` saves, `response.body` + `response.meta.json`, `capture-manifest.json`, `README.md` with command, exit codes, and containment) with offline unit tests for the envelope construction and sanitization — verify: `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` passes with the new tests included.
- [x] 1.2 Run the capture, commit `tests/fixtures/godot-item-purchase/`, and confirm containment — verify: the capture exits 0, a rerun exits 0 and reproduces the committed fixture byte-identically except for the documented time-dependent fields (the recorded capture/envelope timestamps and the HTTP `Date` header, the `last_logged_in`/map-timestamp writes, and the digests derived from them), every working-tree legacy source/config/village/save hash is identical before and after, and the boot and placement fixtures with their manifests are untouched.

## 2. Purchase execution endpoint (Compatibility API v0)

- [x] 2.1 Implement `apps/compat-api/purchase_envelope.py`: the cash-only price vector from the raw config `costs` (documented `costs_not_cash` / `costs_invalid` failures) and `build_envelope(item_id, costs, ts=None)` producing the six-key batch envelope with one `buy_stored_item_cash` command, reusing the placement envelope's shared helpers unchanged (D6) — verify: new `test_purchase_envelope.py` covers the cash vector, both failure codes, the exact envelope shape (placeholders, argument list, single command), and the shared-helper round trip.
- [x] 2.2 Implement the `POST /v0/purchase` route: intent validation fail-closed (JSON object, resolvable save id, integer item id present in config, cash-only config price), derived legacy envelope, in-process execution of the unchanged `command()` dispatcher, corpus-only persistence, and the superset response (`result` + the persisted `store` mapping + `resources`) with structured errors for every unresolvable input — verify: new `test_purchase_endpoint.py` covers each derivation, every fail-closed path (structured error with the corpus save unchanged), the clamp-at-zero path on insufficient cash, and retained session/bootstrap byte-identity, all passing with no server.
- [x] 2.3 Implement the offline fixture-replay parity suite: the same envelope through the compat endpoint equals the captured legacy response and after-state for all stable fields with the documented time-dependent normalizations, plus assertions that working-tree saves are never written by any purchase execution — verify: `test_purchase_parity.py` passes with no network and `git status` shows no `saves/` or `tests/saves/` changes after the full compat test run.

## 3. GameApi purchase operation

- [x] 3.1 Add the typed `PurchaseResult` (and structured failure) types plus their parse functions to `scripts/gameapi/boot_data.gd`, and `purchase_item()` to `scripts/gameapi/game_api.gd` — verify: `test_game_api_fake.gd` extended for typed-shape, structured-failure, and unknown-item coverage passes headless.
- [x] 3.2 Implement `purchase_item()` in `fake_api.gd` as the documented deterministic in-memory double (cash price from the committed config fixture, legacy `max(…, 0)` clamp, storage increment, bought-units record, over the committed purchase fixture's before-state) — verify: the fake suite covers success, affordability clamp, and each fail-closed code with no process, server, or socket.
- [x] 3.3 Implement `purchase_item()` in `legacy_v0_api.gd` (loopback JSON POST to the endpoint, typed result mapping, structured-error passthrough, the endpoint named only inside the legacy-v0 implementation) with live coverage against a running Compatibility API v0 — verify: the live GameApi suite passes inside `verify-boot.ps1`'s live phases and produces the same typed shapes as the fake.

## 4. Client purchase flow

- [x] 4.1 Parse storage into the typed town state: `State.storage` from the default map's storage mapping with the fail-closed rules in D7 (absent → `missing`, present-but-invalid → reject naming the key, quantity `0` preserved, one parser reused by the purchase apply), covered by `tests/test_town_state.gd` — verify: the town-state suite passes headless with the new cases and no behavior change for existing payloads.
- [x] 4.2 Implement the pure shop flow helpers in a new `scripts/town/shop_flow.gd` (store-listed + level-eligible + cash-priced entry filter, price-against-cash text, and the refusal text for an unaffordable price) — verify: the helpers are unit-covered through the purchase suite and depend on no node, request, or clock.
- [x] 4.3 Implement the purchase flow in the town scene: the shop surface in its own UI-foundation slot over the same fail-closed catalog parse, entry selection, a purchase confirm sending exactly one `GameApi.purchase_item()` intent, client-side refusal with no request when the price exceeds current cash, success applying only the authoritative response (storage readout from the response's `store`, HUD resources from the response's `resources`, with a full rollback if the apply fails), and failure surfacing an explicit error with no state change — verify: the new `tests/test_town_purchase.gd` covers entry gating, one request per confirm, the unaffordable no-request case, storage and resource apply, transport and structured-failure rollback, and the malformed-catalog error state, while `test_town_placement.gd` still passes unchanged.
- [x] 4.4 Update the project-scope allow-list for every new script, suite, and evidence file — verify: `test_project_scope.gd` and `test_scene_build.gd` pass with the new entries and no forbidden token outside the legacy-v0 implementation.

## 5. Batteries, live phase, and evidence

- [x] 5.1 Register `test_town_purchase` in the hermetic suite list and add the `purchase-live` phase to `verify-boot.ps1` (start the Compatibility API over a disposable corpus, purchase once, assert the typed response, assert via `compat_live_phase.py --expect-save-mutation` that a corpus save mutated, tear down asserting port release and corpus cleanup with no working-tree `saves/`) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with every documented marker, including the new phase.
- [x] 5.2 Capture the windowed purchase evidence and the deterministic report into `apps/client-godot/evidence/purchase/` (fake-API windowed capture driving the shop flow and showing the purchased item in the storage readout; headless `purchase-report-v1` with inputs and digests, the intent, storage and resources before/after, request counts, and every non-claim from the delta including the fake-capture pointer) — verify: both files are committed, the report lists all required fields, and a rerun of the report step reproduces its committed bytes.
- [x] 5.3 Run the full preservation battery in the final state — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, `python -B apps/compat-api/guard_baseline.py verify` exits 0 with identical digests before and after, the committed M4/M6/placement evidence bytes are unchanged, and `git diff` shows no legacy/fixture/save byte changes beyond the sanctioned new fixture directory, new scripts/suites, and new evidence files.

## 6. Documentation and integration review

- [x] 6.1 Document the purchase slice in `apps/client-godot/README.md` and `apps/compat-api/README.md` (flow, endpoint contract, cash-only envelope derivation with derived-provisional status, storage typing, evidence paths, claim limits) and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one that was run successfully in this change, with its purpose and constraints stated.
- [x] 6.2 Perform the integration review: re-read the final diff against `proposal.md`/`specs/`/`design.md`, run `openspec validate building-purchase --strict` and both batteries once more, and record residual gaps (derived command choice and cash-only derivation, legacy clamping preserved, no progressed-player coverage, storage display-only, later storage commands still open) — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Integration review record (2026-09-29)

- `openspec validate building-purchase --strict` exited `0` ("Change
  'building-purchase' is valid"); `openspec validate --all --strict` reports
  39 passed / 0 failed.
- Orchestrator-run final-state battery (not an independent agent — the fallback
  recorded under Blocking issues, no dedicated OpenSpec verification workflow
  installed): `verify.ps1` exited `0` ("PASS all checks succeeded"),
  `verify-boot.ps1` exited `0` ("PASS all checks succeeded", 18 hermetic suites
  including `test_town_purchase`, five live phases including `purchase-live`
  with all four of its assertions green, guard digest
  `6978b9594f52b3f87ebe043b7d1ce0da67632d0a0537f0af7ea3d22f2e7ff348` identical
  pre=post, port released, no working-tree `saves/`), `hash_manifest.py verify`
  exited `0` (3,258 entries @ `e8c98a0`), and the compat discovery reported
  `Ran 157 tests ... OK` (exit `0`). The only regenerated file is
  `apps/client-godot/evidence/boot/boot-report.json` (per-run timestamp and
  commit), which is committed as the placement Apply did.
- Every requirement and scenario in both delta specs maps to a passing check:
  fixture capture/replay (`capture_purchase_fixture.py` + `test_purchase_parity`,
  offline; 157 compat tests OK), endpoint contract/clamp/fail-closed/
  corpus-only/loopback (`test_purchase_endpoint`, `test_purchase_envelope`),
  flow gating/no-request/apply/rollback/catalog-fail-closed
  (`test_town_purchase`, 213 checks), storage typing
  (`test_town_state` + the same parser reused by the apply), evidence and the
  byte-identical report rerun (`evidence/purchase/`, SHA-256
  `9510BE8409FE25E3…` across three runs), containment/batteries (both
  batteries + hash manifest + guard baseline), GameApi abstraction with
  `purchase_item()` on both implementations (`test_game_api_fake`,
  `test_game_api_live`, `purchase-live`), documented commands (AGENTS.md and
  both READMEs).
- Residual gaps recorded, all stated as claim limits in
  `apps/client-godot/README.md`, `apps/compat-api/README.md`, and
  `evidence/purchase/report.json`:
  1. the choice of `buy_stored_item_cash` as the purchase command, the
     **cash-only** price derivation, and the envelope placeholders
     (`accessToken`, `publishActions`, `tries`, `first_number`) are
     **derived-provisional** — never observed from the Flash client; the
     service therefore claims nothing about resource-priced storage purchases
     (`store_add_items` remains the candidate and is out of scope here);
  2. insufficient cash reproduces the legacy `max(…, 0)` clamp by design — the
     client refuses locally with no request, and rejection-style validation is
     deferred to Server v1 (M13);
  3. parity covers one recorded `buy_stored_item_cash` transaction against the
     fresh-player corpus — no progressed-player coverage and no other commands;
  4. storage is display-only in this change: nothing places from or sells out
     of storage (`place_stored_item`, `store_item`, `sell_stored_item` are the
     later *store*/*move*/*sell* deliver lines), and the shop layout, entry
     labels, and readout are documented placeholders;
  5. cosmetic, no regression: the shop panel and the build picker are both
     right-anchored, so opening both surfaces at once would overlap them; no
     player-facing trigger opens either surface yet (both are entered
     programmatically by the suites, captures, and reports), and presentation
     is provisional by design;
  6. the remaining M7 deliver lines (move, sell, store, upgrade, build timers,
     income, expansion, resources, XP) and M8+ are still open by scope.
