# Tasks

## 1. Record the falsified premise and the corrected cursor

- [x] 1.1 Correct `docs/DEVELOPMENT_ROADMAP.md`'s Project Status: the M11 cursor still names `magics`/`mana` as the next unmeasured follow-up, though that surface shipped inside M10 line 3 (`godot-damage`) as the magic-counter ledger, and `friends` is still described there as "zero legacy occurrences". Verify by `git diff` that the correction is confined to the new status entries and the superseded cursor, and that no prior entry is edited.
- [x] 1.2 Record in the status block that this line's proposal is the active OpenSpec change, that the investigation contract is `docs/legacy-m11-friends.md` (PR #321, merge `3df888a`, content `82b6df9`), and that no Compat API change is expected so the compat suite must remain at 3077. Verify by reading the added block back.

## 2. Deliver the roster projection module

- [x] 2.1 Create `apps/client-godot/scripts/social/friends_roster.gd` as a pure, read-only projection over `PlayerInfoPayload.raw`, with a typed entry exposing the **12** carried `playerInfo` keys and the **6** `maps[0]`-derived fields (`xp`, `level`, `gold`, `wood`, `oil`, `steel`) separately, and **no** index, ordering, or mutating accessor. Verify by running `godot --headless --path apps/client-godot --script res://tests/test_friends.gd` and confirming the projection assertions pass.
- [x] 2.2 Add the fail-closed refusal codes for an absent roster, a non-list roster, and a non-object entry — discriminating shape **before** invoking any parser, per design D5 and the `godot-mission-vocabulary` instrument note. Verify that a malformed roster yields a refusal rather than an empty projection, and that the refusal tests emit **no** engine `ERROR:` line, since `verify-boot.ps1` treats any `^ERROR:` as a script error.
- [x] 2.3 Pin the two-pid literal exclusion as a named constant with its recorded reason, and record beside it the rejected content-derived alternative per design D4. Verify that the derivation yields **5** members from the committed corpus and that the exclusion is not derived from a file count.

## 3. Report the boundaries and refusals

- [x] 3.1 Report the two roster channels and their differing per-entry field counts without deduplicating them (design D6), and record that the Flash-variable channel occurs nowhere in the live v0 envelope — measured this stage, not asserted.
- [x] 3.2 Report that no roster entry carries a `privateState` key, by intersecting each entry's keys against the recording player's and reporting the empty intersection, rather than asserting the absence.
- [x] 3.3 Record the visit surface as a **divergence not reproduced** — the discarded-pid branch, the `""`-with-HTTP-200 failure mode, and the `privateState` exposure — and deliver no visit payload. Verify by searching the delivered module for any visit, world, or leaderboard capability and confirming there is none.

## 4. Enforce the refusals structurally and prove the guards by injection

- [x] 4.1 Add the reserved-name inventory matched case-insensitively **and by substring**, the whole-inventory pin over the module's static functions in **both** directions, and the arithmetic/ordering guard scoped to ordering between committed values — **not** a blanket comparison ban, which `godot-social-state`'s post-archive review showed would condemn legitimate `typeof` discrimination. Verify each guard is non-vacuous by confirming the suite fails when a deliberately invented helper is introduced.
- [x] 4.2 Run **every** injection the design requires — a friendship-selection helper, a relationship-named helper, a **suffixed** helper wearing a reserved name, an assist or consent helper, a helper computing arithmetic over committed values, and a helper ordering two roster positions — and record each probe's failure count and the restored file's SHA-256 in the evidence report. Verify every probe was **detected** (non-zero failures) and that each restore is byte-identical by digest, and that the suite returns to its passing state and exit 0 after each restore.
- [x] 4.3 Record in the report that the instrument failures found during 2.x/4.x are recorded with their cause rather than edited away, and that the projection is read from a **top-level** `neighbors` in the legacy fixture document but from `player_info.neighbors` in the v0 envelope — the trap recorded in design D9. Verify the suite does not reuse `harness.by_pid`/`sort_neighbors` against the envelope without descending first.

## 5. Wire the suite in and re-verify the committed oracles

- [x] 5.1 Write `apps/client-godot/tests/test_friends.gd` as a hermetic suite that **re-verifies** both committed executed captures leaf-by-leaf rather than re-deriving the corpus, and that records the coverage limit that the saves-loop half has **no** executed evidence. Verify the suite passes at exit 0 and that the coverage limit is asserted, not merely noted.
- [x] 5.2 Register the suite in `apps/client-godot/verify-boot.ps1`, and amend `apps/client-godot/tests/test_project_scope.gd`'s allow-list with the three new paths (the module, the suite, and the evidence report). Verify by re-running `test_project_scope.gd` and confirming the count **rose** rather than staying at 2053.
- [x] 5.3 Add `--report=<path>` support writing the deterministic `friends-report-v1` report under `apps/client-godot/evidence/friends/`, with its tables derived from the live module and this run's measurements so they cannot drift from the code they document. Verify the report is **byte-identical across three consecutive runs** by digest.

## 6. Verification

- [x] 6.1 Run and record: `test_friends.gd`, `test_social_state.gd`, `test_project_scope.gd`, `test_content_registry.gd`, `test_game_api_fake.gd`, `test_scene_build.gd`; `verify.ps1`; `verify-boot.ps1`; the compat suite; `validate_content.py`; `hash_manifest.py verify`; `openspec validate --all --strict`. Verify `test_social_state.gd` is **unchanged** at 405 and the compat suite is **unchanged** at 3077 — a changed count on either would mean the spec amendment or design D1 was not honoured.
- [x] 6.2 Confirm `verify-boot.ps1` exits 0 with the hermetic suite count raised by one, the live phase count **unchanged** at 23 per design D8, the guard digest identical before and after, and every battery log file free of `[test] FAIL`, `SCRIPT ERROR`, and `^ERROR:`. Verify the regenerated `boot-report.json` diff is **inspected rather than assumed** and contains only the timestamp, the advanced commit, and the one added suite entry.
- [x] 6.3 Confirm via `git status` that no legacy source, config, village, save, content package, conversion package, registry manifest, or prior fixture byte changed, and confirm no working-tree `saves/` exists. Record the preservation manifest entry count and byte total.
- [x] 6.4 Re-run the injections of 4.2 **against the final state** rather than trusting that an earlier run still holds, since a later edit can silently restore a guard's coverage. Verify each still produces non-zero failures and each restore is still byte-identical.

## 7. Containment for the injection harness itself

These are the harness requirements, added after three defects were measured in a
guard-proof harness during this change's proposal stage (design D7). Each would
have produced a false "all guards proven" record, so they are gates on the
Apply stage's own verification, not on the delivered behaviour.

- [x] 7.1 The injection harness must capture each target file's SHA-256 **before** writing the probe, and compare the restored file against **that** digest. A self-comparison such as `sha256(after) == sha256(after)` is vacuous and is **not** acceptable evidence of a byte-identical restore.
- [x] 7.2 Every restore assertion must additionally check that the restored file contains **zero NUL bytes** and **ends with the expected newline**. A digest alone did not catch the measured corruption, because the corruption was at the byte level the digest was never taken over.
- [x] 7.3 Every probe must name the exact text it manipulates and the exact check it expects to fire, and the harness must **fail loudly when the target text is absent** rather than skipping the probe. Three probes in the measured harness were mis-targeted and two named another check's message; all three silently degraded into "not detected".
- [x] 7.4 After the injection run, confirm containment by re-measuring each touched file's digest, `git status --short`, and `git diff --numstat --ignore-cr-at-eol`, and require all three to equal their pre-probe values. Verify a probe run against a **tracked** file in particular, because that is where the measured corruption occurred.
- [x] 7.5 When reviewing a tracked-file diff for unintended breadth, use `git diff --numstat --ignore-cr-at-eol` **and** confirm the file is not classified as binary. Record in the report if a diff's insertion/deletion count disagrees between the two readings, because the measured cause was NUL bytes at EOF and not the `core.autocrlf=true` checkout form.
