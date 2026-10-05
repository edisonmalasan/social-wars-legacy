# Tasks

## 1. Executed-legacy fixture capture

- [x] 1.1 Add a capture script under `apps/compat-api/` that records the combat-resolution transaction against a committed village document, reusing the existing containment pattern (disposable tree, loopback only, no working-tree `saves/`) and verifying by re-running it that the containment digest is identical before and after and the committed corpus and prior fixtures are untouched
- [x] 1.2 Record in the fixture manifest the exact legacy row-count change, the exact ledger value written, the committed unit-row count of the corpus used, the eleven read keys with the seven that reach nothing, and the divergence between the legacy outcome and this capability's operation, verifying that the manifest names all five fields and that no row was manufactured
- [x] 1.3 Add a fixture-replay parity test under `apps/compat-api/tests/` covering the recorded transaction, and verify it fails when the recorded row-count change or ledger value is altered and passes against the committed manifest

## 2. Compatibility service operation

- [x] 2.1 Add the request envelope accepting only the player identifier and the lost unit identity, ignoring and refusing any client-supplied destruction count, `sent`/`survived` pair, or legacy payload key, verifying with envelope tests that the extra keys are refused with a named code and an empty payload and that no ignored value is echoed
- [x] 2.2 Implement the server-derived eligible-row selection and the removal of exactly one row, with the ledger increment written only when both ledger gates hold, verifying that two removed rows change only the addressed row plus the ledger and that every other placed row is byte-identical
- [x] 2.3 Order every structural and content validation ahead of the removal step, verifying that each refusal path leaves the whole recorded document byte-identical and that the delivered flow's static inventory is pinned whole
- [x] 2.4 Deliver the row-removal path as a command that never touches the ledger, and the item-keyed path as a proven no-op, verifying with a structural assertion that the ledger is unreferenced from the former and that the whole document is byte-identical after the latter
- [x] 2.5 Register the endpoint's route and evidence in `verify-boot.ps1` as a live phase, verifying the phase runs against a disposable corpus, tears the service down, releases the port, and asserts a disposable save mutated

## 3. Client projection and hermetic suite

- [x] 3.1 Add a typed read-only projection under `apps/client-godot/scripts/` carrying the request's field inventory, the validation ordering, the server-derived destruction set, the row-removal and item-keyed contracts, and the recorded divergence, failing closed on an unresolvable payload rather than defaulting it
- [x] 3.2 Add a hermetic suite under `apps/client-godot/tests/` that runs without a service, verifying it passes and that each refusal path is exercised over crafted in-memory input
- [x] 3.3 Add guards asserting the delivered code declares no helper capable of deriving a discarded value, damage, duration, honour, reward, or mission completion, and prove each guard by injecting an offending helper and confirming the suite fails with independent failures, then restoring the file byte-identically

## 4. Field-inventory drift guard and evidence report

- [x] 4.1 Re-derive the twelve read keys and the nine discarded ones from the preserved source on every verification run and compare them for exact identity, verifying that transcribing one key into the suite makes the suite fail
- [x] 4.2 Record the team asymmetry between the row-removal helper's truthy-team acceptance and the ledger helper's team-one requirement as an unexercised code fact, verifying the report states it is neither exercised nor refused and that no committed unit row is on a team other than one
- [x] 4.3 Write the deterministic report under `apps/client-godot/evidence/combat-actions/` from the suite itself so its tables derive from the live model, and verify it is byte-identical across three consecutive runs and carries every required field and non-claim
- [x] 4.4 Register the suite in `verify-boot.ps1`, verifying the hermetic-suite count rises by exactly one and the live-phase count rises by exactly one, with the guard digest identical before and after

## 5. Merged-record corrections

- [x] 5.1 Amend the `godot-unit-behaviors` suite so its corpus measurement records the repository-wide figures alongside the fresh-player figures, and regenerate its report, verifying the digest changes, that the corpus measurement is the only differing block, and that the "no unit row was manufactured" claim is retained unchanged
- [x] 5.2 Correct the four unscoped prose locations that state the corpus places no unit row, verifying by search that no unscoped occurrence remains and that the three correctly scoped occurrences are left byte-identical
- [x] 5.3 Record the second discrepancy as an annotation on the existing record rather than a rewrite, verifying the four unreproducible figures are marked unreproducible with the counting rules measured, that the record's conclusion is left intact, and that no figure was silently replaced

## 6. Integration verification

- [x] 6.1 Run both batteries in their final state, verifying `verify.ps1` and `verify-boot.ps1` each exit 0, that the hermetic and live counts match the increments recorded in 4.4, and that the log files carry no failure or engine-error lines
- [x] 6.2 Re-measure the suites whose counts rise with every added client source, verifying the reported counts are the measured ones rather than the pre-change figures
- [x] 6.3 Run the compatibility suite, the content validator, the preservation manifest verification, and strict OpenSpec validation, verifying the manifest stays at its recorded entry count, that no preserved byte changed, and that strict validation reports no issue