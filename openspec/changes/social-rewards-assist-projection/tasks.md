# Tasks

## 1. Typed projection module

- [ ] 1.1 Add `apps/client-godot/scripts/social/construction_assist_state.gd` with the typed
  read-only record: presence, recorded length, and each element's recorded type and value
  verbatim. Verify: the module compiles and the suite in 2.1 exercises it.
- [ ] 1.2 Implement the three fail-closed refusals — absent bag, non-object bag, non-list
  `si` value — each with a distinct code, changing no recorded value and reporting no
  length or element. Verify: one hermetic case per refusal asserting the recorded slots
  travel untouched beside the refusal.
- [ ] 1.3 Make a missing key and an empty list distinct reported states, and pass an
  unexpected element **type** through verbatim rather than refusing it. Verify: a
  hermetic case with one row lacking the key and one carrying `[]` reports them
  differently, and a case with a non-integer element reports the element without a
  refusal.
- [ ] 1.4 Record the `si` expansion as the quoted source comment including its
  *"because the game expects it"* clause, and record that no assist, reward or friend
  meaning is attached to the projection. Verify: hermetic assertions on both strings,
  with the literal read from the legacy source rather than transcribed.

## 2. Recorded dispatcher table

- [ ] 2.1 Add `apps/client-godot/scripts/social/assist_transitions.gd` holding the three
  recorded dispatchers as data — `buy_si_help` (`command.py:549`), `finish_si` (`:561`),
  and the differently-named `set_resource_allies` (`:637`) calling `finish_si` at `:644` —
  each effect quoted from source and each carrying `reproduced: false`. Verify: hermetic
  assertions that the count is three, that all three are named with their lines, and
  that **every** entry carries the flag.
- [ ] 2.2 Record that only the addressed map slot must resolve — no `friend_assistable`,
  type or team check exists — and record that the absent flag check is **not** enforced
  client-side, with the two unflagged corpus carriers retained rather than refused.
  Verify: hermetic assertions on the recorded precondition and a case placing a
  `friend_assistable`-less row that reports rather than refuses.
- [ ] 2.3 Record the `0` sentinel with its quoted meaning, the friend arm's
  zero-consumer measurement, and the instant stamp as owned by `godot-social-state`.
  Verify: hermetic assertions; the ownership hand-off is asserted to exist.

## 3. Corpus measurement and the gift census

- [ ] 3.1 Re-derive the corpus measurement per run against the explicit 10-document
  allow-list: 3,372 placed rows, 53 carrying `si`, 3 non-empty, 7 elements, one distinct
  value. Assert every comparison is **non-vacuous** so an empty input fails rather than
  passes. Verify: hermetic assertions on each figure plus an injected empty allow-list
  that must fail.
- [ ] 3.2 Record the three reconciliation facts — 2 unflagged carriers, 2 flagged ids
  placed without `si`, 8 of 26 flagged ids never placed — and record the candidate
  explanations as **candidates**, asserting `si` does not imply the flag in either
  direction. Verify: hermetic assertions naming both ids sets and both directions.
- [ ] 3.3 Record `giftable` and `gift_level` with their committed distributions and
  zero-consumer measurement, claiming **no ordinal position**, and list the overlap with
  the other recorded instances. Verify: hermetic assertions on both fields and an
  assertion that no delivered identifier claims an ordinal.
- [ ] 3.4 Amend `unit_behaviors.gd`'s units-only `gift_level` census row with the
  buildings-side measurement and add `giftable` as a recorded row, completing that
  census rather than duplicating it. Verify: `test_unit_behaviors.gd` passes at its
  prior check count plus the added assertions.

## 4. Ownership assertions

- [ ] 4.1 Assert the `friend_assistable` derivation is owned by
  `godot-stored-item-placement` by checking its spec exists **and** that the delivered
  derivation names the same committed field, so a rename on either side fails. Verify:
  hermetic assertion; renaming the field in the owning module must fail the suite.
- [ ] 4.2 Assert `godot-social-state` exists as the owner of the recorded instant stamp
  and of the state fields, and `social-tables-normalization` as the owner of the three
  social tables — without projecting those rows. Verify: hermetic assertions on the
  recipient's existence; the uniform-value census is asserted as a census and the
  social-item table's internal structure is **not** reported.

## 5. Guard proofs by injection

- [ ] 5.1 Implement the whole-function inventory pin compared as a sorted unique set with
  the declaration count pinned separately, plus the case-insensitive **substring**
  reserved-name guard. Verify: the pin rejects an injected helper.
- [ ] 5.2 Prove each refusal guard by injection against a byte-identical copy, restoring
  the file each time and recording the restored SHA-256 in the report. Include one probe
  borrowing **no** reserved word so the belt is shown necessary rather than redundant.
  Verify: every probe exits non-zero; the restored digest equals the pre-probe digest.
- [ ] 5.3 Harden the probe harness per D8: assert zero NUL bytes and a final newline on
  every restore, abort loudly when an anchor is absent, and require `git diff --numstat
  --ignore-cr-at-eol` and `git status --short` to equal their pre-probe values. Verify:
  an absent anchor aborts loudly rather than silently skipping.

## 6. Registration and reporting

- [ ] 6.1 Register the new hermetic suite in `verify-boot.ps1` and confirm the live-phase
  count stays at **23**. Verify: `verify-boot.ps1` runs the new suite and passes.
- [ ] 6.2 Add the suite's paths to `test_project_scope.gd`'s allow-list and re-run it.
  Verify: `test_project_scope.gd` passes at its prior count plus the added entries.
- [ ] 6.3 Write the deterministic report via the suite's own `--report=` flag so its
  tables derive from the live model, and confirm it is byte-identical across three runs
  with the digest recorded. Verify: three runs, one digest, LF form stated.

## 7. Documentation

- [ ] 7.1 Add the client README section recording the delivered surface, the commands
  actually run with their observed results, and the claim limits. Verify: section names
  the report digest and every claim limit.
- [ ] 7.2 Add the `AGENTS.md` verified-commands section for this line, recording the
  observed check counts and the baseline assertions. Verify: every command listed was
  actually executed in this change.
- [ ] 7.3 Update the roadmap `Project Status` ledger and cursor as the root
  orchestrator, recording M11 line 4's lifecycle. Verify: `openspec list --json` and the
  ledger agree.

## 8. Integration verification

- [ ] 8.1 Run the full battery and every affected sibling suite, recording observed
  counts and before/after deltas: `verify.ps1`, `verify-boot.ps1`, the compat suite at
  its **3077** baseline, the content validator, the preservation manifest, and
  `openspec validate --all --strict`. Verify: each exits 0 and its count is recorded.
- [ ] 8.2 Inspect the log files for `[test] FAIL`, `^ERROR:` and `SCRIPT ERROR` lines and
  confirm the diff contains no unintended change to a generated artifact, re-generating
  the boot report only if its bytes genuinely changed. Verify: zero error lines; the boot
  report diff is itemised.
- [ ] 8.3 Record the nine known flaky surfaces' status for this change, re-running any
  that fired rather than recording them as passed. Verify: each is either clean or
  named with its recorded cause.
