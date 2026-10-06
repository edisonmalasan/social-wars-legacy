# Tasks

## 1. Correct the two mis-filed fields in `godot-social-state`

- [x] 1.1 Correct `social_state.gd`'s record for `timeStampEndPremium`: remove the note *"a single instant write"* and any client-sent characterisation, and record instead that the branch writes the instant **twice** (one per arm) with a **server-derived** value. Verify by reading `command.py:612-623` and asserting in the suite that the record names two writes and no client-sent value.
- [x] 1.2 Move `timeStampEndPremium` and `crossPromotionsFinished` out of the social field set into an explicit `FOREIGN_FIELDS` table naming `godot-darts` as owner, keeping all **nineteen** measured fields present so the existing coverage requirement still holds. Verify the delivered suite still reports nineteen measured fields and now describes seventeen as social.
- [x] 1.3 Add the hand-off check: `godot-social-state` verifies the named owning capability exists and really projects both fields, so the correction cannot orphan them. Verify by injecting a misspelled owner name and observing the suite fail.
- [x] 1.4 Extend `test_social_state.gd` for all three corrections and record the correction's cause in the suite's boundary notes, visibly rather than as a quiet edit. Verify the suite exits 0 and report the re-measured check count (do not carry forward a remembered count).

## 2. Darts state projection over the six recorded fields

- [x] 2.1 Create `scripts/darts/darts_state.gd` as a typed read-only projection of the six measured darts fields (`dartsBalloonsShot`, `dartsGotExtra`, `dartsHasFree`, `dartsRandomSeed`, `timeStampDartsNewFree`, `timeStampDartsReset`) with each field's recorded storage document, its recorded value, and its document count. Verify with `godot --headless --path apps/client-godot --script res://tests/test_darts_state.gd` reporting the six fields and failing closed on each malformed shape.
- [x] 2.2 Add the corpus measurement the projection reports: count committed documents carrying a played darts state, a distinct seed count, and each field's recorded value distribution, re-derived every run. Verify the counts are re-derived rather than asserted by temporarily changing a recorded number and observing the suite fail.
- [x] 2.3 Record that `tests/saves/fresh-player.json` carries every darts field at its initial value and cannot exercise the shot, free, or premium arms, so any coverage of those arms over it is reported as crafted input. Verify the suite names the corpus document it uses and reports the fresh-player limitation.

## 3. Server-derived premium duration, clamp, and arm selection

- [x] 3.1 Create `scripts/darts/premium_purchase.gd` deriving the duration from the committed schedule read through `ContentRegistry.get_entry("globals", "PREMIUM_ACCOUNTS")`, never from a client value, preserving the recorded `time` unit and multiplying by the recorded `86400` only where the preserved branch does. Verify the derivation reproduces `360, 180, 30, 7, 3, 1` days from the committed entry and that no delivered code reads `config/main.json`.
- [x] 3.2 Reproduce the recorded oversized-index clamp (`get_game_config.py:184-185`) and the recorded missing-duration fallback (`return 0`), and assert both rather than letting an out-of-range index error. Verify each boundary from both sides, including an index at the last entry, one past it, and an entry with no `time`.
- [x] 3.3 Implement the two-arm selection on the server's own clock against the recorded instant, and report which arm was taken. Verify the set arm for a past instant, the extend arm for a future instant, and the boundary where the clock equals the instant exactly.
- [x] 3.4 Record that the **extend arm has no corpus coverage** — no committed document records a future premium instant — so its coverage is reported as crafted input, and add the guard asserting the module derives nothing from a client-supplied instant or duration. Verify by injecting a client-duration parameter and observing an independent failure.

## 4. Week-boundary reset as a derived predicate

- [x] 4.1 Create `scripts/darts/week_reset.gd` as a pure predicate over the recorded instant, the server clock, and the recorded constants, reproducing the recorded offset, week length, and floor-division week comparison, and reproducing the recorded existence guard for a document lacking the instant. Verify both arms of the predicate and the missing-instant path.
- [x] 4.2 Assert the recorded branch writes the instant to **zero** rather than to the server clock, and deliver no route that performs the write. Verify the predicate returns a verdict only and that a mutation attempt fails a guard.
- [x] 4.3 Report the source's intent comment — that the offset exists because timestamp zero is a Thursday and the reset should land on Monday — **as a comment**, deriving no weekday rule from it. Verify the suite asserts no delivered identifier implements a weekday computation.

## 5. Darts transition refusals and their structural guards

- [x] 5.1 Implement the three recorded transitions with each client-sent input named as client-sent: the reset's client `seed` stored with no semantics derived, the free grant, and the shot. Verify each transition's server-written fields against recorded state.
- [x] 5.2 Refuse the client-dictated shot outcome: no delivered route sets the got-extra flag from a client value, and the difference from the preserved branch is surfaced in the response and recorded as a **divergence**, never as parity. Verify by replaying a won-shot request and asserting the flag does not move and the divergence is reported.
- [x] 5.3 Refuse both invented rules — a shot-list length bound and a schedule-membership test — and report the corpus fact that a committed document records a shot index absent from the committed `darts_items` schedule while the preserved server accepted it. Verify the out-of-schedule shot is reported and that no maximum count or membership check exists in the delivered module.
- [x] 5.4 Prove every guard by **injection** against a byte-identical copy of each delivered module, covering a price-charging helper, a list-bound helper, a membership-test helper, a win-verification helper, a client-duration helper, and at least one injection that borrows no reserved word so the name-based guard is shown to be the belt rather than the gate. Verify each injection fails the suite with at least one independent failure and a non-zero exit, and that restoring the byte-identical file returns it to its passing state; record the restored file's digest.
- [x] 5.5 Add the whole-static-function inventory pin so an injected helper is caught even when it borrows no reserved word, and assert no delivered identifier is named after the refused behaviours. Verify by injecting an innocuously-named helper and observing the inventory pin fail.

## 6. Compatibility API route with a non-tautological no-charge proof

- [x] 6.1 Add the darts envelope and one state-mutating endpoint with a closed action set matching the delivered transitions, ignoring any client-sent resource vector outright. Verify the endpoint's structural refusals in pinned order and that a client-sent vector cannot move any stored resource.
- [x] 6.2 Give every successful action a **two-part** post-execution proof: the premium instant moved by exactly the derived duration **and** the **complete** stored resource set is byte-identical. Verify against the service's full seven-slot resource vocabulary and confirm the proof is non-tautological by mutating one resource deliberately and observing it fail.
- [x] 6.3 Add the executed-legacy capture harness decision: record **no** executed-legacy fixture is claimed, with the reason that `tests/saves/fresh-player.json` carries every darts field at its initial value and a zero premium instant, and that the extend arm is exercisable only over crafted input. Verify the manifest states this rather than leaving it implicit.
- [x] 6.4 Extend the compat test suite for the envelope, the endpoint, every refusal, and both proof halves. Verify `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py"` runs and reports the **grown** count (this line adds a route, so the count must rise above the recorded baseline).

## 7. Deterministic evidence report and project wiring

- [x] 7.1 Write the deterministic `darts-report-v1` report from the suite itself via `--report=<path>`, so its tables derive from the live projection and registry and cannot drift from the code they document. Verify the digest is byte-identical across **three** consecutive runs.
- [x] 7.2 Add the hermetic suite to `verify-boot.ps1`'s `$hermetic` array and record the suite in the battery's inventory. **Narrowed during Apply, and the narrowing is the finding rather than an omission:** no `darts-live` phase is delivered. A live phase would first have to deliver a client darts transport — an intent builder, a typed result, a `GameApi` facade forwarder, and a fake implementation — and none of those is in this change's requirements. More than that, a client able to fire `darts_shoot_balloon` is precisely the client surface this line exists to refuse: the delivered client may project darts state and report transition verdicts, and must not be able to claim a won shot or a purchased entitlement. `godot-social-state` set the precedent of a state-mutating endpoint with no live phase. Verify `verify-boot.ps1` exits 0 with the suite registered, and that the inventory count is recorded as unchanged in live phases.
- [x] 7.3 Add the new client sources to `test_project_scope.gd`'s allow-list and re-run it, reporting the re-measured count. Verify the scope suite exits 0 and that a stray build artifact is **deleted** rather than allowed for.
- [x] 7.4 Document the line in `apps/client-godot/README.md` with its commands, observed results, and claim limits, including the divergence, the unproven extend arm, the zero-consumer price, and the refused client-sent outcome. Verify every command in the new section was actually run.

## 8. Integration verification

- [x] 8.1 Run `powershell -File apps/client-godot/verify.ps1` and `powershell -File apps/client-godot/verify-boot.ps1`, and grep the log files for `[test] FAIL`, `^ERROR:`, and `SCRIPT ERROR`. Verify both exit 0, record the hermetic-suite and live-phase counts, and confirm the guard digest is identical before and after. Re-run before treating a known-flaky surface as a regression, and say so if one fires.
- [x] 8.2 Run `python -B packages/game-content/tools/validate_content.py`, `python -B tools/hash-manifest/hash_manifest.py verify`, and `openspec validate --all --strict`. Verify all three exit 0 and record the results as observed.
- [x] 8.3 Confirm `git status` shows no legacy source, config, village, save, content-package, conversion-package, registry-manifest, or fixture byte changed, and inspect the full diff. Verify the change is confined to the new darts modules, the social-state correction, the compat route, the suites, the evidence, and the documentation.
- [x] 8.4 Record the line's verified commands in `AGENTS.md` alongside the existing milestone entries, stating the claim limits and the flaky surfaces still open. Verify the recorded figures match the run output rather than a remembered baseline.

## Corrections recorded during Apply and verified during Archive

Every box above was checked against the delivered implementation rather than
carried forward unchecked. Two task texts were contradicted by what was actually
delivered; both are recorded here rather than quietly edited away.

### C5 -- task 2.1 names a verification command for a suite that does not exist

Task 2.1 said to verify with
`godot --headless --path apps/client-godot --script res://tests/test_darts_state.gd`.
**No such suite exists.** The delivered suite is the single
`res://tests/test_darts.gd` (**610 checks**), which covers the `darts_state.gd`
projection along with the premium, week-reset, and transition modules. The task
wrote four module names and four suite names; the modules are delivered as four
files and the suites as one. **The projection requirement is satisfied** -- the
six measured fields are delivered with their storage document, value, and
document count, and each malformed shape fails closed -- but the **command as
written cannot be run**, so it is corrected here rather than left as a
verification step that would fail for anyone following it.

### C6 -- task 6.3 says "verify the manifest states this", and there is no manifest

Task 6.3 asked for a record that **no** executed-legacy fixture is claimed,
verified by checking that "the manifest" states it. **There is no fixture and no
fixture manifest**, because `docs/legacy-m11-darts.md` established that no darts
transaction is executable against the corpus: `tests/saves/fresh-player.json`
carries the seed at `0`, the shot list `[]`, `dartsGotExtra` `false`, and all
three instants `0`, while `timeStampEndPremium` is `0` in 32 of the 33 canonical
documents and the one non-zero value is in the **past**. The extend arm is
therefore exercisable only over crafted input.

The absence is recorded in **four** places, none of which is a manifest: the
committed investigation's own record, this file's task 6.3, the `AGENTS.md`
section for this line, and the evidence report's `claim_limits` (10 entries) and
`not_delivered` (6 entries), which carry corrections C3 and C4 verbatim. The
deliverable is satisfied; the **task's wording about a manifest was wrong**, and
asserting a manifest exists would be inventing evidence.

### Two verification steps required by the tasks had not been run, and were run during Archive

Both were run here rather than ticked on the strength of the mechanism existing,
and both restored byte-identically:

- **Task 1.3** required a misspelled owner name to be injected and the suite
  observed to fail. Misspelling `godot-darts` to `godot-dartz` in
  `apps/client-godot/scripts/social/social_state.gd` (**2** replacements) produced
  **2 independent failures** naming both foreign fields, and the restore is
  byte-identical at SHA-256 `b7d28e8bea508f6cbdeccf1b8baebf92b7cb5d9e781f4cf0f6c6e1c00587c37a`.
  The suite then returned to **405 checks**, exit 0.

- **Task 2.2** required a recorded corpus number to be changed temporarily and
  the suite observed to fail. Changing the pinned distinct-value count of
  `timeStampDartsReset` from `15` to `16` on line 111 of
  `apps/client-godot/scripts/darts/darts_state.gd` -- one number, nothing else --
  produced **2 independent failures** (the pinned-distribution sum and the
  re-derived distinct count), and the restore is byte-identical at SHA-256
  `0d825fa54ca54f550c3091f73ac3b2c81ca1c1ce436b16a95252fa74d4ba7453`. The suite
  then returned to **610 checks**, exit 0.

Together with the **ten** module injections already recorded in the evidence
report -- **10 detected, 0 missed, every restore byte-identical** -- the corpus
measurement is now shown to be re-derived rather than asserted, and the
hand-off is shown not to be an orphan.
