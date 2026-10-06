# Tasks — `godot-social-state`

## 1. Model

- [ ] 1.1 Define the typed read-only social state projection, one entry per measured field, each carrying its recorded storage location (`privateState` or `maps[]`).
- [ ] 1.2 Record the nineteen measured fields exactly; assert the list equals the investigation's list in both directions, so an added or dropped field fails.
- [ ] 1.3 Represent an absent field as **absent**, distinct from a committed empty value, and never coerce one to the other.
- [ ] 1.4 Carry the recorded uniform value and its document count per field; add no derived meaning.
- [ ] 1.5 Record the six written fields with their writing branch, and `questsRank` as read-without-written.

## 2. Census

- [ ] 2.1 Implement the re-derived zero-occurrence census over the declared legacy module list, using whole-identifier tokens with comments and string literals stripped.
- [ ] 2.2 Pin the expected 13-field zero-occurrence set and require the recomputed set to equal it in **both** directions.
- [ ] 2.3 Pin `questsRank` outside that group and assert its single reader.
- [ ] 2.4 Self-check the instrument: prove the token matcher is non-vacuously exercised and refuses substring matches inside longer identifiers.

## 3. Recorded surfaces

- [ ] 3.1 Record `set_resource_allies` as writing `resourceAlliesMarket` from a client-supplied argument, with source line.
- [ ] 3.2 Record the addressed-row instant stamp and `finish_si` call verbatim, deriving **no** semantics from it.
- [ ] 3.3 Deliver **no endpoint** for either write, and assert the delivered route set is empty.
- [ ] 3.4 Record `world_id` and `worldChange` as save keys with zero legacy occurrences.
- [ ] 3.5 Record the absence of score-like arithmetic in the dispatcher.
- [ ] 3.6 Name the rejected unit-loss and auction-bet readings so they are not re-counted as scores.

## 4. Refusals

- [ ] 4.1 Refuse to decode any `neighbor_assists` reward; assert no delivered rule derives from one.
- [ ] 4.2 Refuse to charge any `findable_items` coin value.
- [ ] 4.3 Refuse to select a `social_items` worker or apply a worker cost.
- [ ] 4.4 Refuse to derive an assist task, eligibility window, or relationship rule.
- [ ] 4.5 Refuse to synthesize a populated example of any uniformly empty field.
- [ ] 4.6 Assert the delivered module contains no comparison of one committed social value against another.

## 5. Guards

- [ ] 5.1 Pin the absent-helper inventory (`assist_reward`, `friend_level`, `visit_state`, `score_for`, and the rest agreed at Apply).
- [ ] 5.2 Match that inventory case-insensitively **and** by substring, so a suffixed helper wearing a reserved name is caught.
- [ ] 5.3 **Prove guard 5.1/5.2 fails**: inject a reserved helper, confirm independent failures and non-zero exit.
- [ ] 5.4 Inject a *suffixed* helper carrying a reserved name and confirm the substring check catches it.
- [ ] 5.5 Restore the file byte-identically and confirm the suite returns to its passing state and exit 0.
- [ ] 5.6 **Prove guard 4.6 fails**: inject a comparison between two committed social values and confirm the suite fails.
- [ ] 5.7 Record the injection results in the evidence report, including the pre/post SHA-256 of the restored file.

## 6. Boundary

- [ ] 6.1 Assert `social-tables-normalization` exists and retains ownership of the three content tables.
- [ ] 6.2 Assert this capability projects no content row from those tables.
- [ ] 6.3 Record the absence of an executed-legacy fixture and the reason, as a delivered property.

## 7. Evidence

- [ ] 7.1 Emit a deterministic report from the suite's own live projection, so its tables cannot drift from the code they document.
- [ ] 7.2 Confirm the report digest is byte-identical across **three** consecutive runs.
- [ ] 7.3 Record the census field counts, the uniform-value table, the written-field table, and the guard inventory in the report.

## 8. Wiring and verification

- [ ] 8.1 Register the suite in `verify-boot.ps1`'s hermetic list and update its hardcoded suite count.
- [ ] 8.2 Run the suite; record the observed check count.
- [ ] 8.3 Run `verify.ps1` — record exit code.
- [ ] 8.4 Run `verify-boot.ps1` — record exit code, hermetic suite count, live phase count, guard digest equality, and log inspection results.
- [ ] 8.5 Run the compat suite — record the test count and confirm it is **unchanged**, since this line adds no endpoint and does not touch `apps/compat-api/**`.
- [ ] 8.6 Run `validate_content.py` — record exit code and result.
- [ ] 8.7 Run `hash_manifest.py verify` — record entry count and exit code.
- [ ] 8.8 Run `openspec validate --all --strict` — record the item count and failure count.
- [ ] 8.9 Confirm `git status` shows no content-package, fixture, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed.
