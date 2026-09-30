# Tasks

## 1. Executed-legacy level fixture

- [x] 1.1 Implement the level capture tool under `apps/compat-api/` (disposable-copy harness shared with the ten delivered captures: pinned-interpreter and containment checks, seed from `tests/saves/fresh-player.json`, crafted `<64-hex>;<json>` `data` envelope for one `level_up` command carrying a **neutral** vector and the service-derived level, POST to `…/command.php`, sanitized `request.json`, full `before.json`/`after.json` saves, `response.body` + `response.meta.json`, `capture-manifest.json`, `README.md`) with offline unit tests for the envelope construction and sanitization — verify: `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` passes with the new tests included.
- [x] 1.2 Run the capture, commit `tests/fixtures/godot-building-xp/`, and confirm containment — verify: the capture exits 0, a rerun exits 0 and reproduces the committed fixture byte-identically except the documented time-dependent fields, every working-tree legacy source/config/village/save hash is identical before and after, and the ten delivered fixture directories with their manifests are untouched.
- [x] 1.3 Assert the fixture's structural facts before publishing — verify: `level` moves from the stored value to the service-derived value, **all seven resources are byte-identical** (the neutral vector is what makes the level-only proof meaningful), the placement count stays 40, every other row, the storage, the private state, and the player info are byte-identical, the response is `{"result":"success"}`, and the login step leaves the save byte-identical.

## 2. Level-up execution endpoint (Compatibility API v0)

- [x] 2.1 Implement `apps/compat-api/level_envelope.py`: the **single named one-based schedule conversion** (documented as derived-provisional with the rejected zero-based alternative and the corpus contradiction in its docstring), the committed schedule accessors, `entry_for_level(stored_level)`, `derived_level_for(exp)`, `threshold_for(level)` / `next_threshold(exp)`, `remaining_for(exp)`, and `build_envelope(level, vector=None, ts=None)` producing the six-key batch envelope with exactly one `[0, "level_up", [level], vector]` command and a **neutral** vector by default. Reuse the placement envelope's shared helpers unchanged — verify: new `test_level_envelope.py` covers every ladder boundary (below the first threshold, exactly on each of the first thresholds, between thresholds, above the final threshold), the corpus's own `xp 4 / level 1` case, the one named conversion being the only indexing path, the neutral vector, the refusal paths, the shared-helper round trip, and real-config cross-checks.
- [x] 2.2 Add the content accessors in `compat_legacy.py` (delivered accessor style, returning `None` for absent or unusable values rather than coercing): the committed schedule's entry count, an entry by position, and the map's recorded level — verify: new tests in `test_level_endpoint.py` cover a resolving entry, the first and last entries, an absent position, and the corpus's recorded level.
- [x] 2.3 Implement the `POST /v0/level_up` route: intent validation fail-closed (JSON object, resolvable save id; **any client-supplied `level` key ignored**), read the pre-execution recorded level **and** the pre-execution `resources`, derive the level from the stored experience, refuse `level_already_current` (409) when the recorded level already equals the derived level and `xp_below_threshold` (409) when the experience cannot reach the next level, build the derived envelope, execute the unchanged `command()` dispatcher, the post-execution proof (the recorded level is exactly the derived level **and every stored resource is unchanged**), corpus-only persistence, and the superset response (legacy `result` + the derived level + the recorded level before and after + the curve facts used + `resources`) — verify: new `test_level_endpoint.py` covers the successful level-up with **both** proof halves, each refusal with a byte-identical corpus, the ignored client-supplied level, every fail-closed code, and retained session/bootstrap byte-identity, all passing with no server.
- [x] 2.4 Implement the offline fixture-replay parity suite — verify: `test_level_parity.py` passes with no network and `git status` shows no `saves/` or `tests/saves/` changes after the full compat test run.

## 3. GameApi level-up operation

- [x] 3.1 Add the typed `LevelUpResult` (the derived level, the recorded level before and after, the curve facts, `resources`, and the shared protocol/version/server-time/result fields with structured-failure fields) and its parse functions to `scripts/gameapi/boot_data.gd`, and `level_up_town(user_id)` to `scripts/gameapi/game_api.gd` — verify: `test_game_api_fake.gd` extended for typed-shape, curve-parse, structured-failure, and ignored-client-level coverage passes headless.
- [x] 3.2 Implement `level_up_town()` in `fake_api.gd` as the documented deterministic in-memory double over the committed level fixture (derive the level from the **fixture's own** committed schedule and the player's stored experience through the same named conversion, set the recorded level to the derived value, change **no** resource, mirror the endpoint's refusal codes, and change nothing else) — verify: the fake suite covers a successful level-up, the already-current refusal, the below-threshold refusal, a disagreement case, and each fail-closed code with no process, server, or socket.
- [x] 3.3 Implement `level_up_town()` in `legacy_v0_api.gd` (loopback JSON POST to the endpoint, typed result mapping, structured-error passthrough, the endpoint named only inside the legacy-v0 implementation) with live coverage against a running Compatibility API v0 — verify: the live GameApi suite passes inside `verify-boot.ps1`'s live phases and produces the same typed shapes as the fake.

## 4. Client progression flow

- [x] 4.1 Add a new pure `scripts/town/level_flow.gd` mirroring `resource_projection.gd` and `collection_flow.gd` (no node, request, or clock): the committed schedule as read from the content package, the **one named one-based conversion** (mirroring the service's, with the derived-provisional interpretation documented in the module), `derived_level_for(exp)`, `name_for(level)`, `next_threshold(exp)`, `remaining(exp)`, `progress_ratio(exp)`, the agreement/disagreement decision, the refusal reasons (`level_already_current`, `xp_below_threshold`), and the display text — verify: the helpers are unit-covered through the new suite at every ladder boundary and the corpus's own case, and depend on no node, request, or clock.
- [x] 4.2 Implement the flow in the town scene: a level readout (derived level, committed name, stored experience, next threshold, remaining experience, and an explicit agreement or disagreement line naming both values when they differ), an `Expand`-independent eighth mode for the level-up action mutually exclusive with all **ten** delivered modes, a confirm naming the **derived** level as derived, exactly one `GameApi.level_up_town()` intent, local refusals with no request, and success applying only the authoritative response (the recorded level and the HUD balances from the response) with a full snapshot-and-rollback — verify: the new `tests/test_town_xp.gd` covers the readout in agreement and disagreement, every boundary case, action gating, every refusal, one request per confirm, cancellation with a byte-identical town, mutual exclusion with all ten delivered modes, the authoritative apply including the response-wins rule, and transport and structured-failure rollback, while all ten delivered suites still pass unchanged.
- [x] 4.3 Update the project-scope allow-list for the new script, suite, and evidence files — verify: `test_project_scope.gd` and `test_scene_build.gd` pass with the new entries and no forbidden token outside the legacy-v0 implementation.

## 5. Batteries, live phase, and evidence

- [x] 5.1 Register `test_town_xp` in the hermetic suite list and add a thirteenth live phase `level-up-live` to `verify-boot.ps1` (start the Compatibility API over a disposable corpus, level up once, assert the typed response and its **two-part** post-state proof including that **no** resource moved, assert that a refused level-up left the corpus byte-identical, assert via `compat_live_phase.py --expect-save-mutation` that a corpus save mutated, tear down asserting port release and corpus cleanup with no working-tree `saves/`) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with every documented marker, including the new phase.
- [x] 5.2 Capture the windowed XP evidence and the deterministic report into `apps/client-godot/evidence/building-xp/` (fake-API windowed capture of the level readout; headless `xp-report-v1` with the committed curve facts, the derived and recorded levels, the disagreement state, the input digests, the projection-constants pointer, the established-versus-derived provenance split naming the one-based interpretation **with its rejected zero-based alternative**, and every non-claim from the delta) — verify: both files are committed, the report lists all required fields, and a rerun of the report step reproduces its committed bytes.
- [x] 5.3 Run the full preservation battery in the final state — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, `python -B apps/compat-api/guard_baseline.py verify` exits 0 with identical digests before and after, the committed M4/M6 and every delivered slice's evidence bytes are unchanged apart from the regenerated per-run battery report, and `git diff` shows no legacy/fixture/save byte change beyond the sanctioned new fixture directory, new script and suite, and new evidence files.

## 6. Documentation and integration review

- [x] 6.1 Update `docs/legacy-xp-basics.md` with the resolutions, document the slice in `apps/client-godot/README.md` and `apps/compat-api/README.md` (the curve model, the one named conversion, the disagreement reporting, the guarded intent, the endpoint contract, evidence paths, and claim limits including the rejected zero-based alternative), and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one that was run successfully in this change, and the one-based interpretation is marked derived-provisional everywhere it is recorded.
- [x] 6.2 Perform the integration review: re-read the final diff against `proposal.md`/`design.md`/`specs/` and the investigation record, run `openspec validate building-xp --strict` and both batteries once more, and record residual gaps (the index base derived from one corpus data point; no level reward paid because no legacy branch reads one; unit XP and tutorial out of scope because the corpus cannot exercise them; the curve preserved verbatim with no rebalancing; the disagreement reporting deliberately not reconciling; parity over one recorded transaction) — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

## Review record (orchestrator, Apply stage)

Re-read the final diff against `proposal.md`, `design.md` D1-D8, the spec, and the
investigation record, then re-ran both batteries myself in the final state.

### Requirement-to-evidence map

| Requirement | Evidence |
| --- | --- |
| Committed-curve level model | `level_envelope.py` (`entry_index_for_level`, `level_for_entry_index`, round trip asserted for all 100 entries; AST-asserted that no caller does its own level arithmetic) mirrored by `LevelFlow` in `level_flow.gd`; `test_level_envelope.py` (87 tests) covers below-first, each first threshold, between, above-final, and the corpus case `xp 4 / level 1`. |
| Level and progress readout | `test_town_xp.gd` covers the readout in agreement and disagreement plus every boundary; root re-read the committed `xp-report-v1`: `curve.corpus_xp 4`, `curve.corpus_level 1`, `derivation_status derived-provisional`, `rejected_alternative zero-based`, and the contradiction quoted verbatim. |
| Stored-versus-derived disagreement reported | the readout names both values and the experience separating them; nothing reconciles, prefers, or rewrites the save; covered hermetically in both states. |
| Level-up intent, service-derived target | `POST /v0/level_up` accepts only `{user_id}`; the ignored-client-level path is asserted in `test_level_endpoint.py`; the two 409 refusals return before the dispatcher with a byte-identical corpus. |
| Typed operation | `LevelCurve`/`LevelUpResult` in `boot_data.gd`, `level_up_town()` on both implementations, `LevelCurve` deliberately carries **no** reward field; `test_game_api_fake.gd` 1106 checks, `test_game_api_live.gd` 487. |
| Client flow | `test_town_xp.gd` **767 checks**: readout in both states, every boundary, action gating, every refusal, one request per confirm, cancellation byte-identity, mutual exclusion with all nine armed modes, response-wins, transport and structured-failure rollback. |
| Evidence and claim limits | `evidence/building-xp/{level-up.png,report.json}`; digest `f64a5bec…52a0`, byte-identical across runs. |
| Containment | See below. |

### Verification actually run in the final state (by the root)

| Check | Result |
| --- | --- |
| `res://tests/test_town_xp.gd` | 767 checks, PASS |
| `verify.ps1` | exit 0 |
| `verify-boot.ps1` | exit 0 — 27 hermetic suites, 13 live phases, guard digest `6978b959…ff348` pre=post, port released, no working-tree `saves/` |
| compat discovery | `Ran 1109 tests ... OK`, exit 0 (947 before this change) |
| `hash_manifest.py verify` | exit 0 — 3,258 entries |
| `openspec validate building-xp --strict` | exit 0 |

### The corpus being already at its derived level — and what it forced

The one-based reading predicted the corpus would be **self-consistent**, and it is: the
service derives level 1 for `xp 4`, matching the recorded level. Two honest consequences
followed, both recorded rather than papered over:

1. **The fixture's own transaction moves nothing** — `level` 1 to 1, all seven resources
   byte-identical — recorded as `level_moved: false` with a note. The compat worker then
   established level *movement* with a recorded probe in the same run (`level_up([2])` with a
   client-sent experience vector moved `level 1` to `2` and `xp 4` to `504`, changed map keys
   exactly `['level', 'xp']`), which is what makes the endpoint's "no resource moved" proof
   non-tautological.
2. **The `level-up-live` phase deliberately does not assert a corpus save mutation.** The
   endpoint refuses `level_already_current` before the dispatcher runs, so no corpus save can
   change; passing the mutation flag would either fail honestly or force another command into
   the phase and misattribute its evidence. The phase asserts the refusal, its code, its
   empty payload and the corpus's byte-identity, and `verify-boot.ps1` carries both a comment
   and a summary-marker assertion recording the deliberate absence. **A successful live
   level-up is therefore unproven** and is recorded as a claim limit; the success path rests
   on the fake double and the hermetic flow over an in-memory experience.

### Correction made during Apply — my own investigation record was off by one

The record wrote "from level 49 onward" for the `Conqueror` saturation, which was a
**zero-based position** in a curve whose index base is one-based: the first `Conqueror` row is
at curve index 44, i.e. one-based level **45**. Corrected in the record, and the client
module derives the one-based value and records the discrepancy rather than carrying the slip
forward.

### Accepted worker deviations

- `level-up-live` omits the mutation flag, as described above.
- Client helpers take the committed schedule as a trailing parameter
  (`derived_level_for(exp, schedule)`), because a pure module with no state must be handed it;
  documented in the module comment.
- The client conversion returns `null` for a non-integer where the service raises
  `invalid_level` — a client must not raise out of a render pass; the two agree on every value
  the curve can produce, and the difference is documented.
- The tenth delivered M7 line (resources) is **read-only and has no armed state**, so mutual
  exclusion covers the **nine** armed modes; the new mode is labelled the eighth of the
  mutually-exclusive family, matching the change's own wording.
- The windowed capture shows the **refused** path, because the corpus cannot advance; the
  capture flow asserts the action is not offered and fails loudly if the evaluation ever offers
  one, so it cannot silently become a fabricated success.

### Residual gaps (all recorded as claim limits, none blocking)

- The one-based index is derived from **one** corpus data point; a zero-based reading would
  shift every level, and the single named conversion makes it a one-function change.
- A successful live level-up is unproven (unreachable from the committed corpus).
- No level reward is paid or displayed; unit XP and tutorial are out of scope; the curve is
  preserved verbatim with no rebalancing.
- The disagreement reporting deliberately does not reconcile.
- Parity covers one recorded transaction against the fresh-player corpus; no pixel-parity
  oracle exists; the committed capture shows the refused path and runs the fake double.
- The report pins `level_flow.gd` and `fake_api.gd` behaviour, so editing either makes it
  stale and it must be regenerated — the same coupling the sibling reports carry.

