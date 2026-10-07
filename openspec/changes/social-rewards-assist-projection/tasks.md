# Tasks

## 1. Typed projection module

- [x] 1.1 Add `apps/client-godot/scripts/social/construction_assist_state.gd` with the typed
  read-only record: presence, recorded length, and each element's recorded type and value
  verbatim. Verify: the module compiles and the suite in 2.1 exercises it.
- [x] 1.2 Implement the three fail-closed refusals — absent bag, non-object bag, non-list
  `si` value — each with a distinct code, changing no recorded value and reporting no
  length or element. Verify: one hermetic case per refusal asserting the recorded slots
  travel untouched beside the refusal.
- [x] 1.3 Make a missing key and an empty list distinct reported states, and pass an
  unexpected element **type** through verbatim rather than refusing it. Verify: a
  hermetic case with one row lacking the key and one carrying `[]` reports them
  differently, and a case with a non-integer element reports the element without a
  refusal.
- [x] 1.4 Record the `si` expansion as the quoted source comment including its
  *"because the game expects it"* clause, and record that no assist, reward or friend
  meaning is attached to the projection. Verify: hermetic assertions on both strings,
  with the literal read from the legacy source rather than transcribed.

## 2. Recorded dispatcher table

- [x] 2.1 Add `apps/client-godot/scripts/social/assist_transitions.gd` holding the three
  recorded dispatchers as data — `buy_si_help` (`command.py:549`), `finish_si` (`:561`),
  and the differently-named `set_resource_allies` (`:637`) calling `finish_si` at `:644` —
  each effect quoted from source and each carrying `reproduced: false`. Verify: hermetic
  assertions that the count is three, that all three are named with their lines, and
  that **every** entry carries the flag.
- [x] 2.2 Record that only the addressed map slot must resolve — no `friend_assistable`,
  type or team check exists — and record that the absent flag check is **not** enforced
  client-side, with the two unflagged corpus carriers retained rather than refused.
  Verify: hermetic assertions on the recorded precondition and a case placing a
  `friend_assistable`-less row that reports rather than refuses.
- [x] 2.3 Record the `0` sentinel with its quoted meaning, the friend arm's
  zero-consumer measurement, and the instant stamp as owned by `godot-social-state`.
  Verify: hermetic assertions; the ownership hand-off is asserted to exist.

## 3. Corpus measurement and the gift census

- [x] 3.1 Re-derive the corpus measurement per run against the explicit 10-document
  allow-list: 3,372 placed rows, 53 carrying `si`, 3 non-empty, 7 elements, one distinct
  value. Assert every comparison is **non-vacuous** so an empty input fails rather than
  passes. Verify: hermetic assertions on each figure plus an injected empty allow-list
  that must fail.
- [x] 3.2 Record the three reconciliation facts — 2 unflagged carriers, 2 flagged ids
  placed without `si`, 8 of 26 flagged ids never placed — and record the candidate
  explanations as **candidates**, asserting `si` does not imply the flag in either
  direction. Verify: hermetic assertions naming both ids sets and both directions.
- [x] 3.3 Record `giftable` and `gift_level` with their committed distributions and
  zero-consumer measurement, claiming **no ordinal position**, and list the overlap with
  the other recorded instances. Verify: hermetic assertions on both fields and an
  assertion that no delivered identifier claims an ordinal.
- [x] 3.4 Amend `unit_behaviors.gd`'s units-only `gift_level` census row with the
  buildings-side measurement and add `giftable` as a recorded row, completing that
  census rather than duplicating it. Verify: `test_unit_behaviors.gd` passes at its
  prior check count plus the added assertions.

## 4. Ownership assertions

- [x] 4.1 Assert the `friend_assistable` derivation is owned by
  `godot-stored-item-placement` by checking its spec exists **and** that the delivered
  derivation names the same committed field, so a rename on either side fails. Verify:
  hermetic assertion; renaming the field in the owning module must fail the suite.
- [x] 4.2 Assert `godot-social-state` exists as the owner of the recorded instant stamp
  and of the state fields, and `social-tables-normalization` as the owner of the three
  social tables — without projecting those rows. Verify: hermetic assertions on the
  recipient's existence; the uniform-value census is asserted as a census and the
  social-item table's internal structure is **not** reported.

## 5. Guard proofs by injection

- [x] 5.1 Implement the whole-function inventory pin compared as a sorted unique set with
  the declaration count pinned separately, plus the case-insensitive **substring**
  reserved-name guard. Verify: the pin rejects an injected helper.
- [x] 5.2 Prove each refusal guard by injection against a byte-identical copy, restoring
  the file each time and recording the restored SHA-256 in the report. Include one probe
  borrowing **no** reserved word so the belt is shown necessary rather than redundant.
  Verify: every probe exits non-zero; the restored digest equals the pre-probe digest.
- [x] 5.3 Harden the probe harness per D8: assert zero NUL bytes and a final newline on
  every restore, abort loudly when an anchor is absent, and require `git diff --numstat
  --ignore-cr-at-eol` and `git status --short` to equal their pre-probe values. Verify:
  an absent anchor aborts loudly rather than silently skipping.

## 6. Registration and reporting

- [x] 6.1 Register the new hermetic suite in `verify-boot.ps1` and confirm the live-phase
  count stays at **23**. Verify: `verify-boot.ps1` runs the new suite and passes.
- [x] 6.2 Add the suite's paths to `test_project_scope.gd`'s allow-list and re-run it.
  Verify: `test_project_scope.gd` passes at its prior count plus the added entries.
- [x] 6.3 Write the deterministic report via the suite's own `--report=` flag so its
  tables derive from the live model, and confirm it is byte-identical across three runs
  with the digest recorded. Verify: three runs, one digest, LF form stated.

## 7. Documentation

- [x] 7.1 Add the client README section recording the delivered surface, the commands
  actually run with their observed results, and the claim limits. Verify: section names
  the report digest and every claim limit.
- [x] 7.2 Add the `AGENTS.md` verified-commands section for this line, recording the
  observed check counts and the baseline assertions. Verify: every command listed was
  actually executed in this change.
- [x] 7.3 Update the roadmap `Project Status` ledger and cursor as the root
  orchestrator, recording M11 line 4's lifecycle. Verify: `openspec list --json` and the
  ledger agree.

## 8. Integration verification

- [x] 8.1 Run the full battery and every affected sibling suite, recording observed
  counts and before/after deltas: `verify.ps1`, `verify-boot.ps1`, the compat suite at
  its **3077** baseline, the content validator, the preservation manifest, and
  `openspec validate --all --strict`. Verify: each exits 0 and its count is recorded.
- [x] 8.2 Inspect the log files for `[test] FAIL`, `^ERROR:` and `SCRIPT ERROR` lines and
  confirm the diff contains no unintended change to a generated artifact, re-generating
  the boot report only if its bytes genuinely changed. Verify: zero error lines; the boot
  report diff is itemised.
- [x] 8.3 Record the nine known flaky surfaces' status for this change, re-running any
  that fired rather than recording them as passed. Verify: each is either clean or
  named with its recorded cause.

## Deviations and corrections, recorded rather than tidied

### Task 5.3 -- the final-newline rule was rewritten, not satisfied

Task 5.3 specified "assert zero NUL bytes and a final newline on every restore".
The NUL assertion is kept as written. **The final-newline assertion was
rewritten**, because it was not doing the job it was written for. It asserted a
universal *content* rule -- every probed file ends with a newline -- which is true
of the two modules this change authored and **false of `stored_item_flow.gd`**, a
pre-existing delivered file that legitimately ends with `return out` and no
newline. So the rule was not detecting truncation; it was asserting a style
property, and it aborted the probe set rather than proving anything.

The replacement preserves the actual intent -- catch a truncated write -- by
pinning the restored file's **final byte to the baseline** instead of to a
newline, and by *reporting* each file's newline state in the harness output
rather than guarding it. A truncation still fails; a file with no trailing
newline probes cleanly. This is recorded rather than quietly swapped because a
universal content rule dressed as a restore rule is the same defect class this
project has now recorded several times: it looks like a guard and is not one.

A tautological check was written during this fix and removed before it shipped:
a condition testing that a file both lacks and ends with a newline can never be
true. Dead code that reads as a guard is the exact hazard, so it was deleted
rather than kept.

### Task 4.1 -- the ownership probe found a real defect in the guard it was proving

Task 4.1 required that "renaming the field in the owning module must fail the
suite". Proving it took **two** probes, not one, and the second one found a
vacuous guard that the first could not see:

- Probe 7 renames the committed gate field `friend_assistable` across all five
  occurrences in `stored_item_flow.gd`. It fires **2** guards. The third
  ownership check names the bag key `si`, which that rename does not touch, so
  two is the correct result and not a shortfall -- and that is recorded on the
  probe row rather than left to look like an undercount.
- Probe 8 renames the bag key `si` to `s1`. On its **first run it exited 0**,
  which is the finding: the check matched `si` as a **bare two-character
  substring**, and `si` occurs inside "assist", "position" and "using"
  throughout the owner module, so the check **could never fail**.

All three names are now matched as the **quoted literal** a GDScript source
would carry, and the suite additionally asserts that the bare substring form is
*still present* after the rename, so the reason the quoted form is required cannot
be unlearned.

### Counts corrected during Apply

- The recorded injection set grew from six probes to **eight**: measured failure
  counts **6, 5, 5, 4, 1, 2, 2, 1**, summing to **26**.
- The suite grew from 401 to **495** checks, and the report from 18,352 bytes
  (`9aff8f4c...d1711`) to **21,384** bytes (`776aa8c7...10e94`).
- The report is written in **LF form**, so its raw and LF byte counts are equal
  (21,384 both ways) and its digest needs no form qualifier.
