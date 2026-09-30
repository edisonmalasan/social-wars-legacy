# Tasks

## 1. Queue projection and the recorded contracts

- [x] 1.1 Implement `apps/client-godot/scripts/units/unit_queue.gd`: a typed read-only projection of a placed row's `attr` bag carrying the committed count (`nu`), start instant (`ts`), and optional queued unit id (`ui`), reporting presence and values verbatim, an absent queue as **absent** (never count 0 with instant 0), and the recorded three-key teardown rule — verify: `test_unit_queues.gd` covers a full queue, a count-only queue, a count+instant queue, an absent queue, a malformed value per key, and the teardown record.
- [x] 1.2 Record the three commands' exact effects and their **absence of validation** in the same module, and record that the client adds none (D5): the push/push-with-id/pop effects, the map-index-only argument shape, and an explicit statement that no producer, duration, level, or **count bound** is enforced because the legacy engine enforces none — verify: the suite asserts no bound is applied to any count and that the recorded absence is present as content.
- [x] 1.3 Record the `soulmixer_speedup` contract **without implementing it** (D6): the `ts`+`ui` two-key precondition, the duration read from the **queued unit**, the `sm_training_time` coverage recorded as content (300 of 429 units, 0 of 470 buildings), the **seconds** reading, the cost shape divided by an hour, the fact that **nothing is charged**, the start-instant teardown, and the legacy "quite useless" verdict; and **refuse** with a named error where the legacy command would fail on a missing key — verify: the suite asserts no cost is computed, no balance path exists, and the unmet precondition is refused rather than crashing.
- [x] 1.4 Implement the queued-id resolution (D7): resolve `ui` through the registry's `units` domain, and report an unresolvable id as **unresolvable with its recorded value intact** — never dropped, never coerced — verify: the suite covers a resolving id, an unresolvable id, and an absent id, and asserts nothing is substituted.

## 2. Executed-legacy fixture and the guarded endpoint

- [x] 2.1 Implement the capture tool under `apps/compat-api/` reusing the ten delivered captures' disposable-copy harness (pinned-interpreter and containment checks, seed from `tests/saves/fresh-player.json`, a crafted `data` envelope for `push_queue_unit` on map key 1 then `pop_queue_unit` on the same key, POST to `…/command.php`, sanitized `request.json`, full before/after saves, response, `capture-manifest.json`, `README.md`) — verify: offline tests for envelope construction and sanitization pass, and the manifest records the source row as **id 26 Command Center at map key 1** with `training_time` 5 and an empty `attr` bag.
- [x] 2.2 Run the capture and commit `tests/fixtures/godot-unit-queues/`; confirm containment and assert the fixture's structural facts (D3): the push sets `nu` and `ts` on the Command Center's `attr` and changes nothing else; the pop removes both together; **every stored resource is byte-identical**; the placement count and all 40 rows are byte-identical; and the manifest states that **no completion was captured and that no completion command exists** — verify: the capture exits 0, a rerun reproduces the committed fixture byte-identically apart from the documented time-dependent field, and the ten delivered fixture directories are untouched.
- [x] 2.3 Implement `apps/compat-api/queue_envelope.py` (the push/pop batch envelopes, each with exactly one command and a **neutral** vector) and the `POST /v0/queue` route: intent validation fail-closed (JSON object, resolvable save id, a target key, **any client-supplied cost/duration/count/readiness key ignored**), read the pre-execution `attr` bag and `resources`, dispatch through the unchanged `command()` dispatcher, and the **two-part post-execution proof** (the recorded `attr` bag matches the derived result **and every stored resource is unchanged**), plus the response carrying the projected queue and the resources — verify: new tests cover a push, a pop, a refused precondition, the ignored client keys, every fail-closed code, and retained session/bootstrap byte-identity, all with no server.
- [x] 2.4 Implement the offline fixture-replay parity suite and assert that the compat suite **grows** (it is no longer unchanged, because this line adds an endpoint) — verify: parity tests pass with no network and `git status` shows no `saves/` or `tests/saves/` change after the run.

## 3. GameApi operations and client flow

- [x] 3.1 Add the typed `QueueResult` and its parse functions to `scripts/gameapi/boot_data.gd`, and `push_queue_unit_town(map_key)` / `pop_queue_unit_town(map_key)` to `scripts/gameapi/game_api.gd` — verify: `test_game_api_fake.gd` extended for typed shape, structured failure, and **ignored client keys** passes headless.
- [x] 3.2 Implement both operations in `fake_api.gd` as a deterministic in-memory double over the committed fixture, changing **only** the recorded `attr` bag and **no** resource, mirroring the endpoint's refusals — verify: the fake suite covers a push, a pop, a pop on an absent queue, an unmet precondition, and each fail-closed code with no process, server, or socket.
- [x] 3.3 Implement both in `legacy_v0_api.gd` (loopback JSON POST, typed result mapping, structured-error passthrough, the endpoint named only inside the legacy-v0 implementation) with live coverage — verify: the live GameApi suite passes inside `verify-boot.ps1`'s live phases and produces the same typed shapes as the fake.
- [x] 3.4 Add `scripts/units/queue_flow.gd` (pure, mirroring `level_flow.gd`) exposing the projection, the **presence** decision, the recorded teardown, the recorded speedup facts, the recorded refusals, and the display text — with **no** readiness, remaining-time, or progress helper — verify: the helpers are unit-covered and the module depends on no node, request, or clock, and the suite asserts no readiness helper exists.

## 4. Battery, live phase, and evidence

- [x] 4.1 Update the project-scope allow-list; register `test_unit_queues` in the hermetic list (**30** hermetic suites) and add a fourteenth live phase `queue-live` that starts the Compatibility API over a disposable corpus, pushes and pops, asserts the typed response and its **two-part** post-state proof including that **no** resource moved, asserts via `compat_live_phase.py --expect-save-mutation` that a corpus save mutated, and tears down asserting port release and corpus cleanup with no working-tree `saves/` — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with the new phase.
- [x] 4.2 Write the deterministic `unit-queues-report-v1` report into `apps/client-godot/evidence/unit-queues/` (headless, via `--report=<path>`) recording the three commands' effects, the recorded absence of validation, the three-key teardown, the corpus measurement, the fixture's before/after, the recorded speedup contract, the established-versus-derived split naming the legacy "quite useless" verdict, and every non-claim from the delta — verify: the report is committed, lists all required fields, and a rerun reproduces its committed bytes.
- [x] 4.3 Run the full preservation battery in the final state — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `validate_content.py` exits 0, `hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, the ten delivered fixture directories and every delivered slice's evidence are unchanged apart from the new fixture directory and the per-run battery report, and `git diff` shows no legacy, config, save, or content-package byte changed.

## 5. Documentation and integration review

- [x] 5.1 Document the slice in `apps/client-godot/README.md`, `apps/compat-api/README.md`, and `AGENTS.md` (the queue contract, the two structural gaps, the recorded speedup facts, the endpoint contract, the evidence paths, and the claim limits) — verify: each documented command matches one run successfully in this change, and the "no completion, no elapsed time, no cost" limits are stated wherever the slice is described.
- [x] 5.2 Record the residual gaps: the legacy server has **no** completion and **no** elapsed-time evaluation, so a queue can never be shown to finish; the `soulmixer_speedup` cost is recorded but unimplemented and its formula is labelled useless by the legacy author; `sm_training_time` is absent from 129 units and all buildings; no count bound; no acquisition; production, collection, movement, animations, and behaviours remain undelivered; parity covers one recorded push/pop transaction against the fresh-player corpus with no progressed saves available; and no pixel-parity oracle exists — verify: each gap is in the report's non-claims and the ledger.
- [x] 5.3 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D8, `specs/`, and `docs/legacy-production-queues.md`; run `openspec validate unit-queues --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

Implementation was delegated to a worker. The root **independently re-verified the
captured fixture's bytes** rather than trusting the suite, ran the batteries itself in the
final state, and recorded one flaky guard the worker did not surface.

### The fixture, verified from its bytes

The root read the committed capture directly rather than relying on the suite's own
assertions:

| Step | Command Center (map key 1) `attr` | Stored resources |
| --- | --- | --- |
| login | `{}` | gold 2000, wood 2000, steel 2000, oil 2000, xp 4, energy 50, mana 0 |
| **push** | `{'nu': 1, 'ts': 1790797415}` | **byte-identical** |
| **pop** | `{}` — both keys removed together | **byte-identical** |

The push sets a count of 1 and a start instant; the pop tears both keys down **together**,
exactly as `engine.py:191-205` specifies; and every resource is unchanged across all three
steps with 40 rows throughout. **This is what makes the "no resource moved" half of the
endpoint's two-part proof non-tautological** — the transaction really happened while no
balance moved, which is the property that forecloses the client-sent `apply_resources` path
for a command that must not move a balance. It is the family's **third** proof form,
alongside collect's "moved by exactly a derived delta" and expand's "moved by exactly a
derived debit".

The fixture manifest was audited for the statements the design requires, and all are
present: a push and a pop were captured, **no completion was captured**, **no completion
command exists**, the target row is identified as id 26 Command Center, and the unchanged
resources are recorded.

### A flaky guard the worker did not surface

The root's first `verify-boot.ps1` run **failed** on `test_town_xp`. The cause is not a
regression: the suite passes with **exit 0 and 767 checks** on every direct run, and what
tripped the guard was a benign engine shutdown line —

    ERROR: 1 RID allocations of type 'PN18TextServerAdvanced22ShapedTextDataAdvancedE' were leaked at exit.

`verify-boot.ps1` treats any line matching `^ERROR:` as a script error, so a
**nondeterministic** text-server RID leak at process exit can fail the battery. Two
consecutive reruns after the failure passed clean. The allocation is a Label/text-server
one and is unrelated to queue code.

Recorded as a **carried follow-up** rather than papered over: the guard should be narrowed
to `SCRIPT ERROR` or a fatal-error allowlist. Widening or suppressing it here would have
masked a real signal, and narrowing it is a separate correction to the verification
tooling, outside this change's scope.

### Requirement-to-evidence map

| Requirement | Evidence |
| --- | --- |
| A queue is a count, a start instant, and an optional queued unit id | `unit_queue.gd` typed read-only `Queue`; `test_unit_queues.gd` **411 checks** (423 with `--report`) — a full queue, count-only, count+instant, an absent queue, a malformed value per key, and the recorded three-key teardown |
| No elapsed-time evaluation and no completion | the flow offers no readiness, remaining-time, or progress helper, and the suite asserts their **absence**; the fixture manifest records that no completion exists and none was captured |
| The three commands and their recorded lack of validation | the recorded contract names each command's arguments and effects, states that no validation is performed, and applies **no** count bound to any count |
| The atom-fusion speedup recorded without a cost or a timer | the two-key precondition, the duration's source, the seconds reading, the cost shape, the nothing-charged fact, and the "quite useless" verdict are all recorded; the suite asserts no cost is computed, no balance path exists, and an unmet precondition is **refused rather than crashed** |
| A queued unit id resolves through content; an unresolvable one is reported | a resolving id, an unresolvable id, and an absent id are covered, and nothing is substituted |
| An executed-legacy fixture for the push and pop pair | `tests/fixtures/godot-unit-queues/` — a disposable-copy capture against the real placed Command Center, re-runnable, containment verified, and **no** fabricated player state; the ten delivered fixture directories are untouched |
| Queue intents carry no cost, duration, or outcome | `POST /v0/queue` accepts a closed action set, **ignores** any client-supplied cost/duration/count/readiness key, and proves both the derived `attr` bag and that every stored resource is unchanged; the live phase reports `push_count=1 pop_torn_down=true resources_unchanged=true refused=unknown_map_key` |
| Evidence and claim limits | `evidence/unit-queues/report.json`, schema `unit-queues-report-v1`, digest `807477db...92090`, byte-identical across reruns |
| Containment and preservation | see below |

### Verification actually run in the final state (by the root)

| Check | Result |
| --- | --- |
| `test_unit_queues.gd` | exit 0, **411 checks** (423 with `--report`) |
| `test_unit_definitions.gd` | exit 0, **213 checks** |
| `test_unit_instances.gd` | exit 0, **437 checks** |
| `test_content_registry.gd` | exit 0, **87 checks** |
| `test_game_api_fake.gd` | exit 0, **1205 checks** (was 1106) |
| `test_project_scope.gd` | exit 0, **1441 checks** (was 1339) |
| `test_scene_build.gd` | exit 0, **36 checks** |
| `verify.ps1` | exit **0** — content package, both conversion packages, and all four registry manifests byte-unchanged |
| `verify-boot.ps1` | exit **0** on two consecutive final-state runs — 30 hermetic suites, **14** live phases; guard digests identical pre/post (`6978b959...ff348`) |
| compat suite | `Ran 1257 tests ... OK`, exit 0 — **grown** from 1109 (**+148**), because this line adds an endpoint |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | exit 0, 3,258 entries |
| `openspec validate --all --strict` | **51 passed, 0 failed** at Apply; **52** after the spec sync |
| fixture capture | exit 0, containment identical, re-runnable |

`git status` showed no legacy, config, save, content-package, or prior-fixture byte changed.
No Flash, Ruffle, ActionScript, or browser executed; every network call is loopback.

### Accepted deviations

- **The new `/v0/queue` route is placed above the `v0_level_up` route**, because two
  delivered level tests slice the service source from the level route to the closing
  `app.config` line, and a route decorator between them broke their dedent. Found and
  fixed during this stage; the alternative was editing two delivered tests, which is the
  larger change.
- **The recorded wall-clock instant is read from the committed capture** in the fake
  double and the hermetic suite rather than re-pinned as a literal, so a re-capture cannot
  silently desynchronize them. This follows the delivered lines' fixture-derived-epoch
  lesson. The load-bearing assertions (count exactly 1, pop-before IS push-after, teardown
  returns the bag to empty, every resource unchanged) are unchanged.
- **The compat suite grows rather than staying unchanged**, unlike the previous two M8
  lines. That is correct: this line adds a state-mutating endpoint.

### Residual gaps (recorded, non-blocking)

- **The legacy server has no completion and no elapsed-time evaluation**, so a queue can
  never be shown to finish. This is the finding, and it is the `production` line's to own.
- The `soulmixer_speedup` cost is **recorded but unimplemented**, and the legacy author's
  own comment calls the formula useless; it also charges nothing.
- `sm_training_time` is **absent from 129 units and all 470 buildings**, so it cannot be a
  general training duration.
- **No cost, no count bound, and no acquisition** are claimed. No committed unit is
  store-listed; the real sources are the later-milestone `offer_packs` and `darts_items`.
- **Production, collection, movement, animations, and basic behaviors remain undelivered**,
  each its own later M8 line.
- Parity covers **one recorded push/pop transaction** against the fresh-player corpus; no
  progressed-player save is available, and the corpus places only one training producer.
- No pixel-parity oracle exists, and nothing here speaks for what the Flash client displayed
  or how a player obtained a unit.
- **Carried follow-up:** `verify-boot.ps1`'s `^ERROR:` guard is broad enough to fail on a
  benign engine shutdown RID-leak warning.
