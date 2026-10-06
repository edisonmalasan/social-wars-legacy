# Tasks — `godot-social-state`

## 1. Model

- [x] 1.1 Define the typed read-only social state projection, one entry per measured field, each carrying its recorded storage location (`privateState` or `maps[]`).
- [x] 1.2 Record the nineteen measured fields exactly; assert the list equals the investigation's list in both directions, so an added or dropped field fails.
- [x] 1.3 Represent an absent field as **absent**, distinct from a committed empty value, and never coerce one to the other.
- [x] 1.4 Carry the recorded uniform value and its document count per field; add no derived meaning.
- [x] 1.5 Record the written fields with their writing branch, and `questsRank` as read-**and**-written. (Corrected in Apply: this task originally said "read-without-written", which the measurement disproved. There are **seven** written fields — `resourceAlliesMarket` plus six in `OTHER_WRITTEN_FIELDS` — not six.)

## 2. Census

- [x] 2.1 Implement the re-derived zero-occurrence census over the declared legacy module list, counting whole-identifier tokens AND quoted subscripts as two separate forms and summing them, so a field reached through a string literal is not scored as absent.
- [x] 2.2 Pin the expected **12**-field zero-occurrence set and require the recomputed set to equal it in **both** directions. (The proposal said 13; re-derivation found 12, because `questsRank` is read *and* written. Corrected in Apply.)
- [x] 2.3 Pin `questsRank` outside that group and assert **both** its reader and its writer in `admin_set_quest_rank`, not a single reader.
- [x] 2.4 Self-check the instrument: prove the token matcher is non-vacuously exercised and refuses substring matches inside longer identifiers.

## 3. Recorded surfaces

- [x] 3.1 Record `set_resource_allies` as writing `resourceAlliesMarket` from a client-supplied argument, with source line.
- [x] 3.2 Record the addressed-row instant stamp and `finish_si` call verbatim, deriving **no** semantics from it.
- [x] 3.3 Deliver **no endpoint** for either write, and assert the delivered route set is empty.
- [x] 3.4 Record `world_id` and `worldChange` as save keys with zero legacy occurrences.
- [x] 3.5 Record the absence of score-like arithmetic in the dispatcher.
- [x] 3.6 Name the rejected unit-loss and auction-bet readings so they are not re-counted as scores.

## 4. Refusals

- [x] 4.1 Refuse to decode any `neighbor_assists` reward; assert no delivered rule derives from one.
- [x] 4.2 Refuse to charge any `findable_items` coin value.
- [x] 4.3 Refuse to select a `social_items` worker or apply a worker cost.
- [x] 4.4 Refuse to derive an assist task, eligibility window, or relationship rule.
- [x] 4.5 Refuse to synthesize a populated example of any uniformly empty field.
- [x] 4.6 Assert the delivered module contains no arithmetic on, and no **ordering** comparison between, committed social values. (Narrowed in Apply: a blanket `==` ban would condemn the `typeof` discrimination the projection legitimately uses, so the guard claims only that no field is ordered against another.)

## 5. Guards

- [x] 5.1 Pin the absent-helper inventory (`assist_reward`, `friend_level`, `visit_state`, `score_for`, and the rest agreed at Apply).
- [x] 5.2 Match that inventory case-insensitively **and** by substring, so a suffixed helper wearing a reserved name is caught.
- [x] 5.3 **Prove guard 5.1/5.2 fails**: inject a reserved helper, confirm independent failures and non-zero exit.
- [x] 5.4 Inject a *suffixed* helper carrying a reserved name and confirm the substring check catches it.
- [x] 5.5 Restore the file byte-identically and confirm the suite returns to its passing state and exit 0.
- [x] 5.6 **Prove guard 4.6 fails**: inject a comparison between two committed social values and confirm the suite fails.
- [x] 5.7 Record the injection results in the evidence report, including the pre/post SHA-256 of the restored file.

## 6. Boundary

- [x] 6.1 Assert `social-tables-normalization` exists and retains ownership of the three content tables.
- [x] 6.2 Assert this capability projects no content row from those tables.
- [x] 6.3 Record the absence of an executed-legacy fixture and the reason, as a delivered property.

## 7. Evidence

- [x] 7.1 Emit a deterministic report from the suite's own live projection, so its tables cannot drift from the code they document.
- [x] 7.2 Confirm the report digest is byte-identical across **three** consecutive runs.
- [x] 7.3 Record the census field counts, the uniform-value table, the written-field table, and the guard inventory in the report.

## 8. Wiring and verification

- [x] 8.1 Register the suite in `verify-boot.ps1`'s hermetic list and in the project-scope allow-list. (No hardcoded suite count exists in that script; the array is the only registration. The allow-list needed the module, the suite, and the report path.)
- [x] 8.2 Run the suite; record the observed check count.
- [x] 8.3 Run `verify.ps1` — record exit code.
- [x] 8.4 Run `verify-boot.ps1` — record exit code, hermetic suite count, live phase count, guard digest equality, and log inspection results.
- [x] 8.5 Run the compat suite — record the test count and confirm it is **unchanged**, since this line adds no endpoint and does not touch `apps/compat-api/**`.
- [x] 8.6 Run `validate_content.py` — record exit code and result.
- [x] 8.7 Run `hash_manifest.py verify` — record entry count and exit code.
- [x] 8.8 Run `openspec validate --all --strict` — record the item count and failure count.
- [x] 8.9 Confirm `git status` shows no content-package, fixture, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed.

## Observed results (2026-10-06)

Recorded here because tasks 8.2 through 8.9 asked for observed figures, not
checkmarks. Every number below was read from a command that was actually run.

| Task | Command | Observed |
|---|---|---|
| 8.2 | `test_social_state.gd` | **361 checks**, PASS, exit 0 (328 before the injection record was added) |
| 8.3 | `verify.ps1` | `PASS all checks succeeded`, exit 0 |
| 8.4 | `verify-boot.ps1` | `PASS all checks succeeded`, exit 0; **45 hermetic suites** (44 + this one), 24 live phases, guard digest `6978b959…ff348` **identical before and after**, 884 files inspected carrying **zero** `[test] FAIL` / `^ERROR:` / `SCRIPT ERROR` lines |
| 8.5 | compat suite | `Ran 2921 tests … OK`, exit 0, **unchanged** from the 2,921 baseline |
| 8.6 | `validate_content.py` | `result: valid`, 21 schemas, exit 0 |
| 8.7 | `hash_manifest.py verify` | 3,258 entries, 758,423,699 bytes, exit 0 |
| 8.8 | `openspec validate --all --strict` | **67 passed, 0 failed** after Sync (66 before the new capability was seeded) |
| 7.2 | report digest | `703ce9ef…c894`, 17,605 bytes, byte-identical across **three** consecutive runs |

Sibling suites on the final state: `test_project_scope.gd` **1,968** (was 1,934 —
the allow-list grew by three paths), `test_content_registry.gd` **87**,
`test_scene_build.gd` **36**, both unchanged.

## Nine instrument faults found and fixed in this line

Each was caught by a self-check or by the suite's own re-derivation, never by
inspection. Recorded because the count is itself a finding: the re-derivation
guard of design D2 worked as designed on the first real legacy edit it met.

1. `world_id` is a **map** key while `worldChange` is a **`privateState`** key.
   The investigation recorded both as map keys, and the corpus search was
   map-only, so it reported one of the two. The suite's own "BOTH are carried"
   assertion caught it.
2. A `bool` parameter is passed **by value** in GDScript, so a recursive corpus
   search assigned `true` and the caller never saw it. Both world keys measured
   as absent. Fixed with an `Array` tally holder.
3. The comment/string-stripping lexer erases string literals, so every
   branch-**name** assertion was vacuous: `cmd == "set_resource_allies"` reads as
   `cmd == ""` in the stripped view. Those assertions now read raw source.
4. The module's inner class was named the same as the preloaded script, so
   every static call resolved to the inner class.
5. `Projection` is a **built-in Godot type** and cannot be used as a class name.
6. An inner class cannot resolve an outer script's static by bare name, so the
   lookup had to be inlined.
7. `%` binds tighter than `+` in GDScript, so a message split across two string
   literals formats only the second. One message raised "not all arguments
   converted" and its text was lost silently.
8. `_has_arithmetic` iterated the `<`/`>` operator offsets — it scanned for
   *ordering* operators while looking for arithmetic, so it could never fire and
   its emptiness assertion was vacuously true. Caught by its own self-check.
9. `_field_table` read the record table's columns through the projection's
   three-column `field()` accessor, so the report could not be written.

The two corrections to the committed figures are separate from the faults and
are recorded in `design.md` D2 and D9: the zero-occurrence group is **12**, not
13, because `questsRank` is read *and* written.
