# Tasks

Task boxes are ticked at **Archive**, not at Apply. An unticked box is not a
statement that a task is incomplete; it is the applied diff's honest state.

## 1. Executed-legacy fixture

- [ ] 1.1 Add `apps/compat-api/capture_stored_placement_fixture.py` using the shared `capture_legacy_fixtures` harness, recording three transactions against a disposable corpus over `127.0.0.1:5055`: `login_post`, the content-derived seed (`complete_collection` with id `1`, whose committed prize is exactly `{"1085": 1}`), and the placement itself (slot `41`, cell `(58, 47)`, neutral vector) — asserting the placement changes **exactly two leaves**, the new row and the store key, with every stored resource, every other row, the rest of `privateState`, and the player info byte-identical. Record a fourth transaction, the sale of a second stored item, asserting **exactly one** changed leaf, the store key, and no resource credit. Verify the capture exits `0`, that working-tree containment is reported UNCHANGED, that the port is released, and that the disposable copy is removed.
- [ ] 1.2 Record the **four executed probes** from `docs/legacy-stored-unit-placement.md` §3 in the same run, distinguished from recorded transactions: placing an item that was never stored, placing onto an occupied index, placing an id absent from every normalized table, and placing at `(250, -3)`. Each probe records its observed response and changed-state facts and is marked a **divergence**, never parity. Verify each probe's recorded facts match the investigation's §3.3, §3.4, §3.10, and §3.11 exactly.
- [ ] 1.3 Write `tests/fixtures/godot-stored-item-placement/` with the request/response/before/after for all four transactions plus the four probes, and a README recording the containment, the exit code, the measured changed-leaf sets, the **volatile** wall-clock row instant, and the claim limits. Verify the manifest is byte-identical across two consecutive runs **except** for the documented instant, and that the README names that exception rather than hiding it.
- [ ] 1.4 Add executed-legacy parity tests replaying both recorded transactions against the shared derivation, asserting the placement's two-leaf change with the derived `attr` and `player`, and the sale's one-leaf change with every resource unchanged. Verify `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` exits `0`.

## 2. Compatibility API endpoints

- [ ] 2.1 Add `apps/compat-api/stored_placement_envelope.py` holding one derivation imported by **both** the capture and the endpoints, so parity is checked against a single source: the map slot as the smallest positive absent integer (reusing `placement_envelope.next_free_slot`), the row's `timestamp` as the server clock, `store` always `[]`, `player` always `1`, and `attr` as a pure function of the committed `clicks_to_build` and `properties.friend_assistable`. Add a named inverse and assert the slot derivation round-trips across the committed corpus and that the `attr` derivation matches the legacy `engine.map_add_item` `player == 1` block for **all 900** normalized items. Verify unit tests cover both.
- [ ] 2.2 Add `POST /v0/place_stored` to `compat_service.py` accepting `{user_id, item_id, x, y}` plus an optional `orientation`, deriving the slot server-side, resolving the item against committed content, and refusing `not_in_storage`, `slot_occupied`, `unknown_item_id`, and `item_not_placeable` with named codes, 409, and no state change. Carry the **two-part** post-execution proof: the stored count decremented by exactly one **and** the row present at the derived slot with the derived `attr` and `player`, plus the ledger assertion that it gained the id only if newly present. Verify unit tests cover the accepting case, all four refusals, and that the proof fails when a resource does move.
- [ ] 2.3 Add `POST /v0/sell_stored` accepting `{user_id, item_id}`, decrementing stock by exactly one, touching no placement, no ledger entry, and no stored resource, and refusing an absent id with a named code. Carry the post-execution proof that every stored resource is unchanged. Verify unit tests cover the accepting case, the refusal, and that the proof fails if any resource moves.
- [ ] 2.4 Add tests asserting **no** request field other than the item id, cell, and orientation influences the result — specifically that a client-supplied slot, row, attribute bag, player team, quantity, or price is ignored — and that the service exposes no bounds helper, so the recorded geometry gap is mechanical rather than an oversight. Verify each test fails if such a field is honoured or such a helper exists, then restore and re-run.
- [ ] 2.5 Prove the `slot_occupied` refusal is reachable despite the derived index by exercising it against an in-memory corpus with an injected conflict, and record in the change that the typed client cannot otherwise reach it. Verify the test covers the injected conflict and the ordinary derivation.

## 3. Godot storage projection and flow

- [ ] 3.1 Add `apps/client-godot/scripts/units/stored_item_flow.gd` as a typed read-only projection over `maps[0]["store"]` and `privateState.boughtUnits`, reporting committed counts and the ledger verbatim, failing closed on a non-mapping store, a non-integer count, or a non-list ledger, and deriving no capacity, expiry, value, or price. Verify the suite exercises every path including both absent-field cases.
- [ ] 3.2 Add the named `attr` mirror in the flow module with a named inverse and assert it agrees with the compatibility derivation across all 900 normalized items. Verify the suite fails on any disagreement, then restore.
- [ ] 3.3 Add `apps/client-godot/tests/test_stored_item_placement.gd` as the new hermetic suite, including a guard that it builds no request body, the anti-invention pin on the module's whole static-function inventory, and an assertion that **no** delivered helper accepts an `attr` or `player` parameter — making "the client cannot dictate the row's bag or team" mechanical. Verify the suite exits `0` and that injecting one invented helper produces independent failures, after which the byte-identical restore returns it to `0`.
- [ ] 3.4 Add the storage placement and sale flows over the delivered `building-store` projection and the `unit-instances` row typing, reporting the ledger as distinct ids and presenting a sale as crediting nothing. Verify the scope suite still passes and no forbidden legacy transport token appears outside the legacy-v0 implementation.

## 4. Client transport and live phase

- [ ] 4.1 Add the `place_stored_item_town(item_id, x, y, orientation)` and `sell_stored_item_town(item_id)` forwarders to `apps/client-godot/scripts/gameapi/game_api.gd` in the exact shape of the existing forwarders, plus both implementations' behaviour in `legacy_v0_api.gd` and `fake_api.gd`. Verify `test_game_api_fake.gd` and `test_project_scope.gd` still pass.
- [ ] 4.2 Add the `stored-placement-live` phase to `apps/client-godot/verify-boot.ps1`, driving one placement and then one sale against the loopback service with their typed responses and post-state proofs, asserting the refused placement left the corpus byte-identical, and asserting a disposable corpus save mutated. Register the new hermetic suite in the same script and update the recorded suite and phase counts. Verify the script exits `0`.
- [ ] 4.3 Run `powershell -File apps/client-godot/verify.ps1` and `powershell -File apps/client-godot/verify-boot.ps1`, then inspect the whole verify log and every `verify-boot/*.err.txt` for `[test] FAIL`, `^ERROR:`, and `SCRIPT ERROR` lines, re-running before treating any failure as a regression given the recorded flaky surfaces. Verify both scripts exit `0`.

## 5. Documentation and integration checks

- [ ] 5.1 Document the storage-placement deliver line in `apps/client-godot/README.md` following the existing "Building collection" and "Level progression" sections, including the evidence steps, the content-derived seed, the four refusals as deliberate divergences, the recorded-not-refused geometry gap, and the claim limits. Verify the documented commands are exactly the ones executed.
- [ ] 5.2 Run the content validator and the preservation manifest, and confirm `git status` shows no legacy, config, save, village, content-package, conversion-package, registry-manifest, or prior-fixture byte changed. Verify `python -B packages/game-content/tools/validate_content.py` exits `0` and `python -B tools/hash-manifest/hash_manifest.py verify` exits `0`.
- [ ] 5.3 Run `openspec validate stored-item-placement --strict` and confirm the change validates with no warning that Archive would refuse, then review the full diff against `docs/legacy-stored-unit-placement.md`.
- [ ] 5.4 Update the roadmap `## Project Status` ledger and `### Resume point`, and record that the `unit-collection` line's carried follow-up is closed by executed evidence.

## Deferred, with reasons

- **`store_add_items`** — an unvalidated client-sent item list. `unit-production`
  already recorded it as an acquisition anti-pattern; it is used in the probes
  only, never as a delivered route.
- **Grid bounds and cell occupancy** — the already-recorded M6 tile-to-cell
  geometry gap. Requires new evidence, not a derivation.
- **Footprint-aware cell derivation** — needed for the 2×2 General Sculpture and
  3×3 Fountain prizes; blocked on the same gap. The line ships on the 1×1 Metal
  Draggy prize and records the rest.
- **`place_unit_from_store`** — a separate legacy branch named by
  `godot-unit-movement`'s recorded "type-agnostic move" finding; not this line.
- **Acceptance tests and any sale value** — the legacy server has neither and
  authoring one would invent a rule.