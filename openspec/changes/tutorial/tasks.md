# Tasks

## 1. Executed-legacy fixture

- [ ] 1.1 Add `apps/compat-api/capture_tutorial_fixture.py` using the shared `capture_legacy_fixtures` harness, recording two transactions against a disposable corpus over `127.0.0.1:5055`: the completing transition (step `15`, neutral vector, flag `0 -> 1` with exactly one changed field) and the minting transaction (step `15`, ladder `[101,3,7,11,13,17,19,23]`, flag `0 -> 1` with all seven stored resources moved). Verify the capture exits `0`, that working-tree containment is reported UNCHANGED, that the port is released, and that the disposable copy is removed.
- [ ] 1.2 Write `tests/fixtures/godot-tutorial/` with the request/response/before/after for both transactions and a README recording the containment, the exit code, the measured changed-field sets, and the claim limits; verify the fixture manifest's digests are byte-identical across two consecutive runs.
- [ ] 1.3 Add executed-legacy parity tests that replay both fixture transactions against the legacy derivation, asserting the completing case moves the flag and nothing else and the minting case moves all seven resources. Verify `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` exits `0`.

## 2. Compatibility API endpoint

- [ ] 2.1 Add `apps/compat-api/tutorial_envelope.py` with the intent-only envelope and the gate derivation: one named gate predicate over the committed disjunction (`>= 25` or `== 15`), a named record of the nine-value hole, the absent bounds, and the three refused input shapes, plus the envelope builder that emits **only** the step and no outcome, flag, or resource vector. Verify unit tests cover the gate across the whole boundary table, both accepted arms, the nine hole values, a float, a bool, and each refused shape.
- [ ] 2.2 Add the `/v0/tutorial` endpoint to `compat_service.py` accepting `{user_id, step}`, deriving completion server-side, refusing a non-numeric, missing, or null step with a named code, an empty payload, and no state change, and carrying the post-execution proof that every stored resource is unchanged. Verify unit tests cover the accepting case, all three refusals, the already-complete no-op, and that the proof fails when a resource does move.
- [ ] 2.3 Add a test asserting the endpoint refuses any request carrying an outcome, a stored flag, or a resource vector, and that no request field other than the step influences the result. Verify the test fails if such a field is honoured, then restore and re-run.

## 3. Godot tutorial state projection

- [ ] 3.1 Add `apps/client-godot/scripts/progression/tutorial_flow.gd` as a typed read-only projection carrying the recorded completion flag verbatim from the save-level `playerInfo`, failing closed on an absent or wrongly-typed `playerInfo`, deriving no step, ratio, remaining time, or completion, and reporting no `playerInfo` field as belonging to a map. Verify the delivered suite exercises every path.
- [ ] 3.2 Add the named gate mirror in the flow module with a named inverse and assert it agrees with the compatibility gate across the whole boundary table. Verify the suite fails on any disagreement, then restore.
- [ ] 3.3 Add `apps/client-godot/tests/test_tutorial.gd` as the new hermetic suite, including the guard that it builds no request body and the anti-invention pin on the module's whole static-function inventory. Verify the suite exits `0` and that injecting one invented helper produces independent failures, after which the byte-identical restore returns it to `0`.

## 4. Client transport and live phase

- [ ] 4.1 Add the `complete_tutorial_town(step)` forwarder to `apps/client-godot/scripts/gameapi/game_api.gd` in the exact shape of the existing forwarders, plus the fake implementation's behaviour in `fake_api.gd`. Verify `test_game_api_fake.gd` and `test_project_scope.gd` still pass.
- [ ] 4.2 Add the `tutorial-live` phase to `apps/client-godot/verify-boot.ps1`, driving one accepted tutorial completion against the loopback service with its typed response and post-state proof, and asserting a disposable corpus save mutated. Register the new hermetic suite in the same script and update the recorded suite and phase counts. Verify the script exits `0`.
- [ ] 4.3 Run `powershell -File apps/client-godot/verify.ps1` and `powershell -File apps/client-godot/verify-boot.ps1`, then inspect the whole verify log and every `verify-boot/*.err.txt` for `[test] FAIL`, `^ERROR:`, and `SCRIPT ERROR` lines, re-running before treating any failure as a regression given the three recorded flaky surfaces. Verify both scripts exit `0`.

## 5. Documentation and integration checks

- [ ] 5.1 Document the tutorial deliver line in `apps/client-godot/README.md` following the existing "Building collection"/"Level progression" sections, including the evidence steps, the claim limits, and the deliberate input-shape divergence. Verify the documented commands are exactly the ones executed.
- [ ] 5.2 Run the content validator and the preservation manifest, and confirm `git status` shows no legacy, config, save, village, content-package, conversion-package, registry-manifest, or prior-fixture byte changed. Verify `python -B packages/game-content/tools/validate_content.py` exits `0` and `python -B tools/hash-manifest/hash_manifest.py verify` exits `0`.
- [ ] 5.3 Run `openspec validate tutorial --strict` and confirm the change validates with no warning that Archive would refuse, then review the full diff against the committed investigation record.