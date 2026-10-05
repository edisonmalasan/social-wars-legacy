# Tasks

## 1. Executed-legacy fixture capture

- [ ] 1.1 Add a capture script under `apps/compat-api/` that records the magic-counter transactions against `villages/Neutral.json`, the only committed corpus with a non-empty magics ledger, reusing the existing containment pattern (disposable tree, loopback only, no working-tree `saves/`) and verifying by re-running it that the containment digest is identical before and after and that no committed corpus or prior fixture byte changed
- [ ] 1.2 Record in the fixture manifest the twelve transactions, the per-step ledger before and after, the 8-slot resource comparison, the step that crosses the cap, the step that destroys charges, the accepted out-of-table identity, and the float-key hazard, verifying that the manifest names all of them and that no ledger entry was fabricated into the seed
- [ ] 1.3 Add a fixture-replay parity test under `apps/compat-api/tests/` covering the recorded transactions, and verify it fails when a recorded ledger transition or a resource-comparison result is altered and passes against the committed manifest

## 2. Compatibility service operation

- [ ] 2.1 Add the request envelope accepting only the player identifier, the action, and the magic identity, ignoring and refusing any client-supplied count, delta, or resulting value, verifying with envelope tests that the extra keys are refused with a named code and an empty payload and that no ignored value is echoed
- [ ] 2.2 Implement the identity validation against the committed magic table, refusing an identity absent from it and refusing a non-canonical identity form rather than coercing it, verifying that each refusal leaves the document byte-identical
- [ ] 2.3 Implement the server-derived counter transition applying the recorded literal cap to both actions, verifying that repeated application stops at the cap, that a counter at the cap is never reduced, and that the two legacy asymmetries are refused rather than reproduced
- [ ] 2.4 Implement the two-part post-execution proof over the complete eight-slot stored resource set, verifying that a changed resource fails the proof and that the mana and private-state energy slots are included rather than a seven-slot subset
- [ ] 2.5 Order every validation ahead of the ledger write, verifying that each refusal path leaves the whole recorded document byte-identical and that the delivered operation's function inventory is pinned whole
- [ ] 2.6 Register the endpoint's route and evidence in `verify-boot.ps1` as a live phase, verifying the phase runs against a disposable corpus, tears the service down, releases the port, and asserts a disposable save mutated

## 3. Client projection and hermetic suite

- [ ] 3.1 Add a typed read-only projection under `apps/client-godot/scripts/` carrying the committed magic content verbatim, the server-derived transition, the recorded literal cap, the rejected content-derivation alternative, the three recorded divergences, and the reported-but-unused damage vocabulary, failing closed on an unresolvable payload rather than defaulting it
- [ ] 3.2 Add a hermetic suite under `apps/client-godot/tests/` that runs without a service, verifying it passes and that each refusal path and each reported absence is exercised over crafted in-memory input
- [ ] 3.3 Add the structural guard asserting the delivered code declares no helper capable of computing a damage amount, a hit-point value, attack or defense arithmetic, a multiplier, a mitigation, or a combat outcome, and prove the guard by injecting an offending helper and confirming the suite fails with independent failures, then restoring the file byte-identically
- [ ] 3.4 Add guards asserting no delivered code reads the reported damage vocabulary to compute a value, gate an operation, or derive a limit, and that no magnitude is synthesized for the committed entry whose description promises an effect magnitude the commit never made
- [ ] 3.5 Add the source re-derivation from `command.py` bytes on every run for the two branch names and spans, the dispatcher branch count, the 8-slot row shape, the complete attribute-bag key union, and the absence of any damage-shaped key, cross-checking the branch count against the project's own command-catalog tool rather than a regex
- [ ] 3.6 Verify the guard against the vacuous-measurement failure mode recorded in this project: assert that the re-derivation actually counted the sources it claims, and prove it by perturbing a counted input and confirming the suite fails

## 4. Evidence and verification

- [ ] 4.1 Run the capture and verify its exit code and containment, and verify the committed corpus and every prior fixture are untouched by comparing before and after
- [ ] 4.2 Generate the deterministic `damage-report-v1` report from the suite itself so its tables are derived from the live model and cannot drift from the code they document, and verify it is byte-identical across repeated runs
- [ ] 4.3 Run the compatibility suite, the hermetic client suite, `verify.ps1`, `verify-boot.ps1`, the content validator, the preservation manifest, and `openspec validate --all --strict`, recording the observed results and any flaky surface
- [ ] 4.4 Verify no windowed capture and no pixel-parity oracle is claimed, since nothing is rendered, and record that as a claim limit

## 5. Ownership and boundaries

- [ ] 5.1 Assert the boundary against the capabilities that own the neighbouring surfaces — combat actions, mission vocabulary, unit behaviors, unit queues, building construction, unit instances, and unit experience — verifying that the delivered code declares no duplicate of any of them and that the owners really do project the surfaces they claim
- [ ] 5.2 Record in the report the coverage limit carried from the investigation: one of ten committed magics was driven, the other nine ledger keys were observed but not driven, and no per-magic behaviour is claimed because none exists to claim
