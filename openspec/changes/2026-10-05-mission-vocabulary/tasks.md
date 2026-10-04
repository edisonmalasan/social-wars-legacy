# Tasks

## 1. Committed vocabulary table with a byte-faithfulness guard

- [ ] 1.1 Commit the mission-type vocabulary table under the Godot client's
  content area with all 64 `MISSION_*` entries, each carrying its exact
  `legacy_id` name and integer value, read from `constants.py:984-1047`.
- [ ] 1.2 Extract the legacy declarations **as bytes** in the test helper, using a
  pattern anchored on the declaration form, and assert that the committed table's
  name and value are byte-equal to the extraction for **every** entry.
- [ ] 1.3 Assert the table's entry count (**64**) and its numbering-gap set
  (**`9`, `10`, `20`, `57`**) match the extraction, so a partial or padded table
  fails rather than passing.
- [ ] 1.4 Prove the drift guard fails by **injection** in three directions — a
  mistranscribed value, a mistranscribed name, and a removed entry — and restore
  the file byte-identically, recording each observed failure.

## 2. Godot mission vocabulary projection

- [ ] 2.1 Add a typed read-only `MissionVocabulary` projection module carrying
  each declaration's name and value exactly as committed, in committed value order,
  failing **closed** on an absent table, a non-array, a missing name, or a
  non-integer value.
- [ ] 2.2 Add the read-only accessor for the three committed mission-adjacent
  globals, obtained through the **existing normalized content registry** so that
  no second copy of them exists anywhere in the client.
- [ ] 2.3 Report the numbering gaps and the near-duplicate declarations as recorded
  content, with **no** renumbering, gap-closing, deduplication, or preferred-member
  selection.
- [ ] 2.4 Derive **no** category, grouping, ordering beyond committed value, cap,
  limit, price, or rule from any entry or global; record the zero-consumer finding
  as a named accessor rather than only as prose.
- [ ] 2.5 Declare **no** mission **state**: the module shall not project, derive,
  reconcile, or report the mission identifier, the last-chapter instant, or the
  current quest-variable map.

## 3. Structural guards for the zero-consumer finding

- [ ] 3.1 Pin the delivered module's **whole static-function inventory**, so that
  adding a dispatch, trigger, or resolution helper fails the suite.
- [ ] 3.2 Add a **by-name guard** failing when any delivered code identifier is
  named after a mission type or a `MISSION_`-prefixed constant, matched as a
  substring so a suffixed helper wearing the vocabulary is also caught.
- [ ] 3.3 Prove both guards by **injection and restore**, recording the observed
  independent failure count for each, and assert that the restored byte-identical
  file returns the suite to its passing state and exit `0`.
- [ ] 3.4 Assert the ownership boundary structurally: the projection's own file
  walk finds **no** mission-state identifier in the delivered module, and the
  existing quest capability is confirmed present and to remain the single owner.

## 4. Hermetic suite, evidence report, and integration

- [ ] 4.1 Add `apps/client-godot/tests/test_mission_vocabulary.gd` as a new hermetic
  suite registered in `verify-boot.ps1`, covering the verbatim projection, the
  fail-closed paths, the drift guard, the gaps, the near-duplicates, the globals,
  the zero-consumer guards, and the ownership boundary.
- [ ] 4.2 Have the suite write the deterministic `mission-vocabulary-report-v1`
  report under `apps/client-godot/evidence/mission-vocabulary/`, generated from the
  projection module's own data so its tables cannot drift from the code they
  document; verify the digest is byte-identical across **three** consecutive runs.
- [ ] 4.3 Amend `test_content_registry.gd` / `test_project_scope.gd` **only** if a
  measured boundary claim they make has become false, and record which claim and
  why.
- [ ] 4.4 Add the per-line section to `apps/client-godot/README.md` and the
  `Verified … commands` section to `AGENTS.md`, with counts **re-measured on the
  merged state** rather than quoted from this file.
- [ ] 4.5 Record explicitly that the line adds **no** Compatibility API endpoint,
  **no** executed-legacy fixture, and **no** live phase, with the reason, and
  confirm the compat suite, the content validator, the preservation manifest, and
  `openspec validate --all --strict` are unchanged.

## Integration review (root orchestrator)

- [ ] 5.1 Verify against the active change artifacts that no requirement is
  satisfied by an assertion alone where a structural guard was specified.
- [ ] 5.2 Confirm the recorded claim that the line delivers no behaviour is
  mechanically true: the delivered module contains no arithmetic, no comparison,
  and no dispatch keyed on a mission value.
- [ ] 5.3 Confirm `git status` shows no content-package, fixture, save, config,
  village, conversion-package, or legacy-source byte changed.
- [ ] 5.4 Confirm the roadmap's M10 cursor and deliver list still match the
  investigation's verdict, and that no later M10 line is treated as pre-authorised.
