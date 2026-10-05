# Tasks

## 1. Executed-legacy fixture capture

- [x] 1.1 Add a capture script under `apps/compat-api/` that records the magic-counter transactions against `villages/Neutral.json`, the only committed corpus with a non-empty magics ledger, reusing the existing containment pattern (disposable tree, loopback only, no working-tree `saves/`) and verifying by re-running it that the containment digest is identical before and after and that no committed corpus or prior fixture byte changed
- [x] 1.2 Record in the fixture manifest the twelve transactions, the per-step ledger before and after, the 8-slot resource comparison, the step that crosses the cap, the step that destroys charges, the accepted out-of-table identity, and the float-key hazard, verifying that the manifest names all of them and that no ledger entry was fabricated into the seed
- [x] 1.3 Add a fixture-replay parity test under `apps/compat-api/tests/` covering the recorded transactions, and verify it fails when a recorded ledger transition or a resource-comparison result is altered and passes against the committed manifest

## 2. Compatibility service operation

- [x] 2.1 Add the request envelope accepting only the player identifier, the action, and the magic identity, ignoring and refusing any client-supplied count, delta, or resulting value, verifying with envelope tests that the extra keys are refused with a named code and an empty payload and that no ignored value is echoed
- [x] 2.2 Implement the identity validation against the committed magic table, refusing an identity absent from it and refusing a non-canonical identity form rather than coercing it, verifying that each refusal leaves the document byte-identical
- [x] 2.3 Implement the server-derived counter transition applying the recorded literal cap to both actions, verifying that repeated application stops at the cap, that a counter at the cap is never reduced, and that the two legacy asymmetries are refused rather than reproduced
- [x] 2.4 Implement the two-part post-execution proof over the complete eight-slot stored resource set, verifying that a changed resource fails the proof and that the mana and private-state energy slots are included rather than a seven-slot subset
- [x] 2.5 Order every validation ahead of the ledger write, verifying that each refusal path leaves the whole recorded document byte-identical and that the delivered operation's function inventory is pinned whole
- [x] 2.6 Register the endpoint's route and evidence in `verify-boot.ps1` as a live phase, verifying the phase runs against a disposable corpus, tears the service down, releases the port, and asserts a disposable save mutated

## 3. Client projection and hermetic suite

- [x] 3.1 Add a typed read-only projection under `apps/client-godot/scripts/` carrying the committed magic content verbatim, the server-derived transition, the recorded literal cap, the rejected content-derivation alternative, the three recorded divergences, and the reported-but-unused damage vocabulary, failing closed on an unresolvable payload rather than defaulting it
- [x] 3.2 Add a hermetic suite under `apps/client-godot/tests/` that runs without a service, verifying it passes and that each refusal path and each reported absence is exercised over crafted in-memory input
- [x] 3.3 Add the structural guard asserting the delivered code declares no helper capable of computing a damage amount, a hit-point value, attack or defense arithmetic, a multiplier, a mitigation, or a combat outcome, and prove the guard by injecting an offending helper and confirming the suite fails with independent failures, then restoring the file byte-identically
- [x] 3.4 Add guards asserting no delivered code reads the reported damage vocabulary to compute a value, gate an operation, or derive a limit, and that no magnitude is synthesized for the committed entry whose description promises an effect magnitude the commit never made
- [x] 3.5 Add the source re-derivation from `command.py` bytes on every run for the two branch names and spans, the dispatcher branch count, the 8-slot row shape, the complete attribute-bag key union, and the absence of any damage-shaped key, cross-checking the branch count against the project's own command-catalog tool rather than a regex
- [x] 3.6 Verify the guard against the vacuous-measurement failure mode recorded in this project: assert that the re-derivation actually counted the sources it claims, and prove it by perturbing a counted input and confirming the suite fails

## 4. Evidence and verification

- [x] 4.1 Run the capture and verify its exit code and containment, and verify the committed corpus and every prior fixture are untouched by comparing before and after
- [x] 4.2 Generate the deterministic `damage-report-v1` report from the suite itself so its tables are derived from the live model and cannot drift from the code they document, and verify it is byte-identical across repeated runs
- [x] 4.3 Run the compatibility suite, the hermetic client suite, `verify.ps1`, `verify-boot.ps1`, the content validator, the preservation manifest, and `openspec validate --all --strict`, recording the observed results and any flaky surface
- [x] 4.4 Verify no windowed capture and no pixel-parity oracle is claimed, since nothing is rendered, and record that as a claim limit

## 5. Ownership and boundaries

- [x] 5.1 Assert the boundary against the capabilities that own the neighbouring surfaces — combat actions, mission vocabulary, unit behaviors, unit queues, building construction, unit instances, and unit experience — verifying that the delivered code declares no duplicate of any of them and that the owners really do project the surfaces they claim
- [x] 5.2 Record in the report the coverage limit carried from the investigation: one of ten committed magics was driven, the other nine ledger keys were observed but not driven, and no per-magic behaviour is claimed because none exists to claim

---

## Completion record (2026-10-05)

Every task below was ticked **after** the check it names was executed, not before.
The right-hand column is the observed result, not a restatement of the task.

| # | task | observed |
| --- | --- | --- |
| 1.1 | capture script | `capture_magic_fixture.py` exit `0` on three consecutive runs; containment digest `18e5e55ba85473bb` identical before and after; 78 files before and after; 19 protected fixtures untouched; no working-tree `saves/` |
| 1.2 | manifest records twelve transactions | `capture-manifest.json` holds **12** `recorded_steps`; the cap-crossing step (`31 -> 63`), the charge-destroying step (`113 -> 50`), the out-of-table id (`99`), and the float-key hazard (`str(1.0) -> '1.0'`) are each named |
| 1.3 | fixture-replay parity test | `test_magic_parity.py`, **26** tests, `OK`; proven to fail by tampering — altering a recorded ledger value gave 5 failures, altering `resources_after.mana` gave 4, and restoring the byte-identical files returned `OK` |
| 2.1 | envelope refuses a client-sent count | nine named reasons; `client_dictated_count` proven end to end. **Two defects found and fixed here** (see below) |
| 2.2 | identity validation | committed 10-row table; a non-canonical form refused rather than coerced; each refusal leaves the document byte-identical |
| 2.3 | derived transition | stops at the cap; never reduces; **above the cap refused**, not clamped — and the above-cap refusal is a **modern-only** authority with no preserved-server counterpart |
| 2.4 | two-part proof over eight slots | a changed resource fails the proof; `mana` and `privateState.energy` both included, asserted as the complete set rather than a seven-slot subset |
| 2.5 | validation ahead of the write | all nine validations ordered ahead of the write; each refusal path byte-identical; the module's function inventory pinned |
| 2.6 | route and live phase | `magic-live` registered; runs against a disposable corpus, tears the service down, releases port 5056, asserts a disposable save mutated |
| 3.1 | typed read-only projection | `magic_flow.gd`; committed content verbatim; fails closed on an unresolvable payload |
| 3.2 | hermetic suite | **618** checks plain, **621** with `--report`, exit `0`, empty stderr |
| 3.3 | no damage-computing helper | **23** absent helpers plus the whole **48**-function static inventory pinned; five injections each produced 3-5 independent failures, each followed by a byte-identical restore |
| 3.4 | vocabulary guards | the reported damage vocabulary is read to compute nothing, gate nothing, and derive no limit; no magnitude synthesized for the committed entry whose description promises one |
| 3.5 | source re-derivation | branch names and spans, dispatcher count cross-checked against `tools/command-catalog/verify_commands.py` (**63**, not the regex's **62**), 8-slot row shape, bag key union, absence of damage-shaped keys — all re-derived on every run |
| 3.6 | non-vacuous measurement | five perturbation modes against counted inputs (rename-branch 2, identifier-class 3, comment-attack 1, apostrophe 2, ledger-key 3 failures) all exit non-zero |
| 4.1 | capture verification | exit `0`; containment digest unchanged; every prior fixture byte-identical |
| 4.2 | deterministic report | `damage-report-v1` via `--report`; digest `ec0df2d0...904e21`, 36,245 bytes in LF form, byte-identical across three consecutive runs |
| 4.3 | full battery | `verify.ps1` exit `0`; `verify-boot.ps1` exit `0` with **43 hermetic suites and 22 live phases**; compat `Ran 2662 tests ... OK` exit `0`; content validator exit `0` `result: valid`; manifest 3,258 entries exit `0`; `openspec validate --all --strict` **64 passed, 0 failed** |
| 4.4 | no capture or pixel parity claimed | recorded as a claim limit; nothing is rendered |
| 5.1 | ownership boundary | asserted against `godot-combat-actions`, `godot-mission-vocabulary`, `godot-unit-behaviors`, `godot-unit-queues`, `godot-building-construction`, `godot-unit-instances`, `godot-unit-experience`; the owners really do project what they claim |
| 5.2 | coverage limit | one of ten committed magics driven; the other nine ledger keys observed but not driven; no per-magic behaviour claimed |

### Requirements changed during Apply, and why

**The post-execution proof requirement was corrected, not silently narrowed.** It
originally asked for "the counter changed by exactly the derived delta", which is
**impossible by construction**: the service must refuse both preserved
asymmetries while the preserved dispatcher is left unchanged and still writes its
own numbers, so `matches_derived` is false on five of seven successful steps.
Asserting equality would have failed every one of them and asserting nothing
would have left the half vacuous. The requirement now pins what actually executed
and requires the derived value to be **reported beside** the recorded one with an
explicit agreement flag.

**Two further scenarios were added** to requirements that already existed: the
above-cap refusal (a fourth divergence, refused rather than clamped, because
`min(cap, before + 1)` applied to 113 **returns the cap** — the exact
charge-destroying decrease being refused) and the absent-identity divergence
(both preserved branches write an absent key at **zero**, so the preserved
"acquire a spell you hold none of" path increments nothing at all).

### Two defects found in the delivered envelope

Both were **reported by the implementation subagent rather than worked around**,
and both had been **pinned as expected behaviour by the test suite** — so the
inversion is what the assertions now assert, which is what pinning was for.

1. `refused_client_keys` lower-cased the *request* key and compared it against
   `PROTOCOL_KEYS`, two members of which are camelCase. Measured refused set was
   exactly `["first_number", "ts", "tries", "commands"]` — `publishActions` and
   `accessToken` were silently accepted. Fixed by folding both sides, with an
   import-time assertion that neither tuple may ever hold a mixed-case member
   again, and the legacy wire spellings preserved in
   `PROTOCOL_KEY_WIRE_SPELLINGS`.
2. `CONSUMER_RULES` named four rules while its own docstring said only `token`
   and `quoted` can establish a consumer. The suite had already carried the
   stricter pair as `ESTABLISHING_RULES`; the module now declares that pair.

### The eighth flaky surface, found by this battery and closed

`test_collection_endpoint`'s containment test asserted whole-document equality
across two `/v0/bootstrap` responses, which carry a wall clock. It failed once in
four full-suite runs, and a second run surfaced a **nested** instance of the same
defect (`player_info.last_logged_in`). The `/v0/session` half of that same test
was fixed for this exact class on the stored-item-placement line; the bootstrap
half had been missed. It now asserts the differing set is a **subset** of the
documented time-dependent fields, that each exempt field is present and a
positive integer on **both** sides, and that the exempt timestamp is never
**earlier** — true of a clock, false of an incrementing ledger. Proven by
injection. This is the **second** recorded flaky surface in this project closed
rather than re-run.

### Three corrections to the committed investigation

Recorded in `docs/legacy-m10-damage.md` §7.1-7.2 rather than by quiet edits, and
each independently re-measured before acceptance:

1. §5.5 read `command.py 6 sites` and then listed **eight** lines. The eight are
   correct; the sentence conflated four assignment statements with six subscript
   occurrences, two membership tests, and two local bindings.
2. `config["magics"]` is a **list** of ten rows with native `id` 1..10, not a
   `dict`.
3. `get_game_config.py` has **zero** occurrences of `magic`, case-insensitively —
   the serving module's own confirmation of the zero-consumer finding.

And **one measurement of mine was false outright**: I asserted the legacy `use`
arm and the derived transition "agree only at a recorded counter of zero."
Measured over the whole legal domain they are *literally the same formula*
`min(cap, x + 1)` and agree at **every** counter 0..50. The entire divergence is
about `buy` and about the absent-key arm. Correction 4 — the branch-count regex
reading 62 where the catalog says 63 — **recurred** in the implementation module
for the same reason, which is recorded as the finding: recording a correction is
not the same as preventing the class, and `branch_count_agrees_with_catalog()`
now guards it mechanically in both layers.

### A recorded documentation gap, left visible rather than backfilled

M10 line 2 (`godot-combat-actions`) shipped without a `README.md` section, so
this is the first combat-line section present. Writing up another line's delivered
evidence from memory is how a wrong figure reaches a specification, so that gap is
recorded here for the combat line instead of filled on its behalf.
