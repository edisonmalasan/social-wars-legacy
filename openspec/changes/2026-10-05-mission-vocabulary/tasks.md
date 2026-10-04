# Tasks

## 1. Committed vocabulary table with a byte-faithfulness guard

- [x] 1.1 Commit the mission-type vocabulary table under the Godot client's
  content area with all 64 `MISSION_*` entries, each carrying its exact
  `legacy_id` name and integer value, read from `constants.py:984-1047`.
- [x] 1.2 Extract the legacy declarations **as bytes** in the test helper, using a
  pattern anchored on the declaration form, and assert that the committed table's
  name and value are byte-equal to the extraction for **every** entry.
- [x] 1.3 Assert the table's entry count (**64**) and its numbering-gap set
  (**`9`, `10`, `20`, `57`**) match the extraction, so a partial or padded table
  fails rather than passing.
- [x] 1.4 Prove the drift guard fails by **injection** in three directions — a
  mistranscribed value, a mistranscribed name, and a removed entry — and restore
  the file byte-identically, recording each observed failure.

## 2. Godot mission vocabulary projection

- [x] 2.1 Add a typed read-only `MissionVocabulary` projection module carrying
  each declaration's name and value exactly as committed, in committed value order,
  failing **closed** on an absent table, a non-array, a missing name, or a
  non-integer value.
- [x] 2.2 Add the read-only accessor for the three committed mission-adjacent
  globals, obtained through the **existing normalized content registry** so that
  no second copy of them exists anywhere in the client.
- [x] 2.3 Report the numbering gaps and the near-duplicate declarations as recorded
  content, with **no** renumbering, gap-closing, deduplication, or preferred-member
  selection.
- [x] 2.4 Derive **no** category, grouping, ordering beyond committed value, cap,
  limit, price, or rule from any entry or global; record the zero-consumer finding
  as a named accessor rather than only as prose.
- [x] 2.5 Declare **no** mission **state**: the module shall not project, derive,
  reconcile, or report the mission identifier, the last-chapter instant, or the
  current quest-variable map.

## 3. Structural guards for the zero-consumer finding

- [x] 3.1 Pin the delivered module's **whole static-function inventory**, so that
  adding a dispatch, trigger, or resolution helper fails the suite.
- [x] 3.2 Add a **by-name guard** failing when any delivered code identifier is
  named after a mission type or a `MISSION_`-prefixed constant, matched as a
  substring so a suffixed helper wearing the vocabulary is also caught.
- [x] 3.3 Prove both guards by **injection and restore**, recording the observed
  independent failure count for each, and assert that the restored byte-identical
  file returns the suite to its passing state and exit `0`.
- [x] 3.4 Assert the ownership boundary structurally: the projection's own file
  walk finds **no** mission-state identifier in the delivered module, and the
  existing quest capability is confirmed present and to remain the single owner.

## 4. Hermetic suite, evidence report, and integration

- [x] 4.1 Add `apps/client-godot/tests/test_mission_vocabulary.gd` as a new hermetic
  suite registered in `verify-boot.ps1`, covering the verbatim projection, the
  fail-closed paths, the drift guard, the gaps, the near-duplicates, the globals,
  the zero-consumer guards, and the ownership boundary.
- [x] 4.2 Have the suite write the deterministic `mission-vocabulary-report-v1`
  report under `apps/client-godot/evidence/mission-vocabulary/`, generated from the
  projection module's own data so its tables cannot drift from the code they
  document; verify the digest is byte-identical across **three** consecutive runs.
- [x] 4.3 Amend `test_content_registry.gd` / `test_project_scope.gd` **only** if a
  measured boundary claim they make has become false, and record which claim and
  why.
- [x] 4.4 Add the per-line section to `apps/client-godot/README.md` and the
  `Verified … commands` section to `AGENTS.md`, with counts **re-measured on the
  merged state** rather than quoted from this file.
- [x] 4.5 Record explicitly that the line adds **no** Compatibility API endpoint,
  **no** executed-legacy fixture, and **no** live phase, with the reason, and
  confirm the compat suite, the content validator, the preservation manifest, and
  `openspec validate --all --strict` are unchanged.

## Integration review (root orchestrator)

- [x] 5.1 Verify against the active change artifacts that no requirement is
  satisfied by an assertion alone where a structural guard was specified.
- [x] 5.2 Confirm the recorded claim that the line delivers no behaviour is
  mechanically true: the delivered module contains no arithmetic, no comparison,
  and no dispatch keyed on a mission value.
- [x] 5.3 Confirm `git status` shows no content-package, fixture, save, config,
  village, conversion-package, or legacy-source byte changed.
- [x] 5.4 Confirm the roadmap's M10 cursor and deliver list still match the
  investigation's verdict, and that no later M10 line is treated as pre-authorised.

## Verification record (measured on the merged branch, 2026-10-05)

Every figure below was **re-measured on the final tree**, not quoted from
`proposal.md`, `design.md`, or this file. Commands and results are reproduced
verbatim in the `AGENTS.md` section of the same name.

### Batteries and suites actually run

| Check | Observed |
| --- | --- |
| `test_mission_vocabulary.gd` | **208 checks**, PASS (the 41st hermetic suite) |
| the same, with `--report=` | **211 checks**, PASS |
| `test_project_scope.gd` | **1,832 checks**, PASS (was 1,798) |
| `test_content_registry.gd` | 87 checks, PASS — **unchanged** |
| `test_game_api_fake.gd` | 1,322 checks, PASS — **unchanged** |
| `test_scene_build.gd` | 36 checks, PASS — **unchanged** |
| `test_quests.gd` | 1,223 checks, PASS — **unchanged** |
| `test_tutorial.gd` | 639 checks, PASS — **unchanged** |
| `test_unit_experience.gd` | **2,470 checks**, PASS (was 2,430) |
| `verify.ps1` | **PASS all checks succeeded** |
| `verify-boot.ps1` | **PASS all checks succeeded**; **41** hermetic suites, **20** live phases |
| `verify-boot.ps1` guard digest | `6978b959…ff348` **identical before and after** |
| battery log files inspected | **682**, with zero `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines |
| compat suite | `Ran 2187 tests in 63.502s` then `OK`, exit `0` — unchanged at the 2,187 baseline — **unchanged** |
| content validator | `result: valid` — 22 outputs, 21 schemas, 604 references |
| preservation manifest | 3,258 entries, exit `0` |
| `openspec validate --all --strict` | **62 passed, 0 failed** |

`test_project_scope` and `test_unit_experience` rise with **every** delivered
line that adds a client source, because both walk the client tree. Re-measure
before quoting either.

### Evidence

`apps/client-godot/evidence/mission-vocabulary/report.json`, the deterministic
`mission-vocabulary-report-v1` report, written by the suite itself via
`--report=` so its tables derive from the live projection and cannot drift from
the code they document. SHA-256 `1aeee8d2ce13361c1a5da3875d140c651f26bd2e56d7c86b7ba1a0203ba6f4b`,
13,850 bytes, byte-identical across **four** consecutive runs (task 4.2 asked
for three).

`apps/client-godot/evidence/boot/boot-report.json` was **regenerated** by the
battery, because registering a suite invalidates its bytes. The change was
verified rather than assumed: the assertion-name multiset grew from 204 to 206
and the command-name multiset from 67 to 68, with **nothing removed** in either,
the additions being exactly `test_mission_vocabulary exits 0 (got 0)`,
`test_mission_vocabulary reports PASS`, and `test_mission_vocabulary`. No other
top-level key differs except `environment.git_commit` and `generated_utc`. The
long list of positional `CHG` lines in a naive diff is an **index shift** from
inserting the suite at index 45, not a change to any existing assertion.

### Injection results (task 3.3) — all eight detected

Every injection was followed by a byte-identical restore that returned the suite
to its 208-check passing state and exit `0`.

| Injection | Independent failures |
| --- | --- |
| invented dispatch helper `resolve_type` | 5 |
| helper named after a mission type `mission_killed_enemy` | 5 |
| suffixed absent helper `damage_for`, caught by the substring check | 5 |
| mission-state reference `"timestampLastChapter"` | 4 |
| mistranscribed value, colliding with another entry | 3 |
| mistranscribed value, clean | 3 |
| mistranscribed name | 2 |
| removed entry | 3 |

### Three defects this line found in its own work, and how each was closed

1. **The projection silently dropped entries.** Found by injection, not by
   reading. The ordering pass scanned `range(first, last)` using the *last entry
   in file order* as its upper bound, so mistranscribing one value above the
   committed range shrank the projection from **64** entries to **63** — and it
   surfaced as an entry-count mismatch rather than as the value mismatch it
   actually was, which is what made it worth recording. The first fix, a min/max
   computation, was then **refused by the suite's own guard** because it added
   exactly two comparisons over a committed value. The final fix sorts the value
   keys, which keeps the "no comparison of one committed value against another"
   claim literally true and makes the projection independent of storage order; a
   regression check covers it.
2. **The by-name guard was case-sensitive** (task 3.2), so
   `mission_killed_enemy` would have slipped past it. Strengthened only after
   measuring that the module is clean case-insensitively and that a lower-cased
   probe is caught by a folded comparison but not by the exact-case one.
3. **A deliberate refusal test failed the battery.** `JSON.parse_string` emits an
   engine `ERROR:` line for malformed input and `verify-boot.ps1` treats any
   `^ERROR:` as a script error, so testing the "arbitrary text" refusal would
   have failed verification even though the suite passed. A document that does
   not begin with `{` cannot be an object, so it is now refused *before* the
   parser is invoked, with the identical verdict and no engine error — coverage
   kept rather than dropped.

### Task 4.3 — which existing boundary claim was amended, and why

`test_project_scope.gd` **named all three new files** before they were
allow-listed: the client script, the content table, and the evidence report. Its
boundary claim had not become false, but its file set is a positive assertion, so
the allow-list was extended. **`test_content_registry.gd` was not touched at
all** (87 checks, unchanged), which is the expected outcome: the three mission
globals are read *through* the existing registry, so the registry gains no entry.

### Task 4.5 — no endpoint, no fixture, no live phase, with the reason

This line adds **no** Compatibility API endpoint, **no** executed-legacy fixture,
and **no** live phase. The reason is the finding itself: the vocabulary has
**zero** legacy consumers, so there is no transaction to capture and no request
for an endpoint to serve. The live-phase count staying at **20** across a line
that registers a new hermetic suite is the evidence that this is true rather than
asserted. The compat suite, the content validator, the preservation manifest,
and `openspec validate --all --strict` are all unchanged.
