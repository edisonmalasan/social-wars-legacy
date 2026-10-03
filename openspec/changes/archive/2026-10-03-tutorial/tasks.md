# Tasks

## 1. Executed-legacy fixture

- [x] 1.1 Add `apps/compat-api/capture_tutorial_fixture.py` using the shared `capture_legacy_fixtures` harness, recording two transactions against a disposable corpus over `127.0.0.1:5055`: the completing transition (step `15`, neutral vector, flag `0 -> 1` with exactly one changed field) and the minting transaction (step `15`, ladder `[101,3,7,11,13,17,19,23]`, flag `0 -> 1` with all seven stored resources moved). Verify the capture exits `0`, that working-tree containment is reported UNCHANGED, that the port is released, and that the disposable copy is removed.
- [x] 1.2 Write `tests/fixtures/godot-tutorial/` with the request/response/before/after for both transactions and a README recording the containment, the exit code, the measured changed-field sets, and the claim limits; verify the fixture manifest's digests are byte-identical across two consecutive runs.
- [x] 1.3 Add executed-legacy parity tests that replay both fixture transactions against the legacy derivation, asserting the completing case moves the flag and nothing else and the minting case moves all seven resources. Verify `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` exits `0`.

## 2. Compatibility API endpoint

- [x] 2.1 Add `apps/compat-api/tutorial_envelope.py` with the intent-only envelope and the gate derivation: one named gate predicate over the committed disjunction (`>= 25` or `== 15`), a named record of the nine-value hole, the absent bounds, and the three refused input shapes, plus the envelope builder that emits **only** the step and no outcome, flag, or resource vector. Verify unit tests cover the gate across the whole boundary table, both accepted arms, the nine hole values, a float, a bool, and each refused shape.
- [x] 2.2 Add the `/v0/tutorial` endpoint to `compat_service.py` accepting `{user_id, step}`, deriving completion server-side, refusing a non-numeric, missing, or null step with a named code, an empty payload, and no state change, and carrying the post-execution proof that every stored resource is unchanged. Verify unit tests cover the accepting case, all three refusals, the already-complete no-op, and that the proof fails when a resource does move.
- [x] 2.3 Add a test asserting the endpoint refuses any request carrying an outcome, a stored flag, or a resource vector, and that no request field other than the step influences the result. Verify the test fails if such a field is honoured, then restore and re-run.

## 3. Godot tutorial state projection

- [x] 3.1 Add `apps/client-godot/scripts/progression/tutorial_flow.gd` as a typed read-only projection carrying the recorded completion flag verbatim from the save-level `playerInfo`, failing closed on an absent or wrongly-typed `playerInfo`, deriving no step, ratio, remaining time, or completion, and reporting no `playerInfo` field as belonging to a map. Verify the delivered suite exercises every path.
- [x] 3.2 Add the named gate mirror in the flow module with a named inverse and assert it agrees with the compatibility gate across the whole boundary table. Verify the suite fails on any disagreement, then restore.
- [x] 3.3 Add `apps/client-godot/tests/test_tutorial.gd` as the new hermetic suite, including the guard that it builds no request body and the anti-invention pin on the module's whole static-function inventory. Verify the suite exits `0` and that injecting one invented helper produces independent failures, after which the byte-identical restore returns it to `0`.

## 4. Client transport and live phase

- [x] 4.1 Add the `complete_tutorial_town(step)` forwarder to `apps/client-godot/scripts/gameapi/game_api.gd` in the exact shape of the existing forwarders, plus the fake implementation's behaviour in `fake_api.gd`. Verify `test_game_api_fake.gd` and `test_project_scope.gd` still pass.
- [x] 4.2 Add the `tutorial-live` phase to `apps/client-godot/verify-boot.ps1`, driving one accepted tutorial completion against the loopback service with its typed response and post-state proof, and asserting a disposable corpus save mutated. Register the new hermetic suite in the same script and update the recorded suite and phase counts. Verify the script exits `0`.
- [x] 4.3 Run `powershell -File apps/client-godot/verify.ps1` and `powershell -File apps/client-godot/verify-boot.ps1`, then inspect the whole verify log and every `verify-boot/*.err.txt` for `[test] FAIL`, `^ERROR:`, and `SCRIPT ERROR` lines, re-running before treating any failure as a regression given the three recorded flaky surfaces. Verify both scripts exit `0`.

## 5. Documentation and integration checks

- [x] 5.1 Document the tutorial deliver line in `apps/client-godot/README.md` following the existing "Building collection"/"Level progression" sections, including the evidence steps, the claim limits, and the deliberate input-shape divergence. Verify the documented commands are exactly the ones executed.
- [x] 5.2 Run the content validator and the preservation manifest, and confirm `git status` shows no legacy, config, save, village, content-package, conversion-package, registry-manifest, or prior-fixture byte changed. Verify `python -B packages/game-content/tools/validate_content.py` exits `0` and `python -B tools/hash-manifest/hash_manifest.py verify` exits `0`.
- [x] 5.3 Run `openspec validate tutorial --strict` and confirm the change validates with no warning that Archive would refuse, then review the full diff against the committed investigation record.

## Integration review (root orchestrator)

All **fifteen** tasks are discharged. Two of them carried verification clauses
that were **not** met on first execution, and both are recorded below rather
than quietly ticked.

### Task 1.2's digest clause was measured false and the requirement restated

The task asked for "the fixture manifest's digests to be byte-identical across
two consecutive runs". Diffing two consecutive captures field by field shows
they are **not**, and the cause is four wall-clock surfaces, not state:
`executed_at_utc` in the manifest, `captured_at_utc` in each step record, the
`Date` response header, and the signed `form.data` -- which embeds a wall-clock
`ts`, so its HMAC changes too. Everything else is byte-identical: every
`before.json`, every `after.json`, every `response.body`, and every other
manifest field including all three outcomes. The fixture README now carries the
measured four-field table instead of the asserted two, and the suite reads the
client ladder out of the committed `request.json` so it cannot drift.

### Task 2.3's verification clause found the guard was thinner than the claim

The task asked that the test "fail if such a field is honoured, then restore and
re-run". Running that check produced the line's second substantive finding.
Three narrow tests guarded the intent-only requirement, each sending one field
name. Temporarily making the route honour a client-sent `completed_tutorial`
produced **exactly one** failure across all **1912** tests -- only
`test_a_client_supplied_stored_flag_is_ignored` caught it. The requirement held,
but it held by accident rather than by proof.

The gap was closed on its own branch and PR (#268, `test/`), so the archive
stage stays specs-and-ledger only: `test_no_client_supplied_field_is_ever_read`
now sends **twenty** field names across **both** a completing and a declining
step and compares the **whole response** minus a named volatile-key list, plus
the persisted flag and every stored resource, and
`test_the_volatile_key_list_is_exactly_the_one_that_varies` stops that helper
from silently growing. With the injection still in place the sweep fails; after
the byte-identical restore (SHA-256 `d75bf31c...6d0`) the suite is green at
`Ran 1914 tests ... OK`. No production code changed.

A first attempt at the injection appeared to **pass**: it was placed before the
`try:` block that assigns `flag_before`, so the real read overwrote it. Only
after moving it inside the route's own function span did it bite. Recorded
because an injection that cannot fail is indistinguishable from one that is
guarding nothing.

### The task tick itself was missed at Apply

The Apply stage (PR #266) delivered and verified all fifteen tasks but left
**every box unchecked**, because the implementation workers were instructed not
to edit `openspec/**`. The Sync stage correctly touched specs only, and the
Archive stage is where the boxes are ticked -- after verification rather than
during it. Recorded so the ledger does not imply the tick was contemporaneous
with the work.

### Three injections, all proven rather than trusted

| injected | result | restored |
| --- | --- | --- |
| `static func tutorial_total_steps() -> int` in the flow module | **3** independent failures, exit 1 | byte-identical, `9ea3ff1b...0d6`, exit 0, 637 checks |
| the `/v0/tutorial` route moved after another route | **3** independent failures, exit 1, file still compiled | byte-identical, `D75BF31C...D6D0` |
| `flag_before = payload["completed_tutorial"]` in the route | **1** failure, then **2** once the sweep existed | byte-identical, `D75BF31C...6d0` |

### Corrections made during the line

- The fixture README asserted "31 village saves, 30 recording `1`". That was
  asserted rather than measured and is wrong on both counts: `villages/` holds
  **8** files, **7** recording `1` and `initial.json` recording `0`. Corrected in
  place with the measurement recorded, and asserted by the suite.
- The client ladder was restated from memory as `[0, 3, 0, 60, 0, 0, 0, 0]`.
  The committed ladder is `[101, 3, 7, 11, 13, 17, 19, 23]`.
- A GDScript `%`-binding slip in the live phase's marker line made the suite
  unparseable and `verify-boot.ps1` fail while every hermetic suite it had
  already run was green; caught by inspecting `verify-boot/*.err.txt` rather than
  trusting the exit code alone, which is the reason that practice exists.

### Deviations and refused work

- **`game_api.gd`, `legacy_v0_api.gd`, `fake_api.gd`, and `level_flow.gd`
  edited**, as on every previous line: all 19 live phases drive the `GameApi`
  facade, so the forwarder had to exist there, and `level_flow.gd`'s scope claim
  was corrected from "the level surface" to unit experience only.
- **The legacy HTTP 500 for the three raising input shapes was not reproduced.**
  Named refusal codes were used instead. A crash is not a behaviour.
- **Coercing a malformed step to `0`** so it merely declines was rejected for
  the same reason, which is why `invalid_step` / `missing_step` / `null_step`
  exist rather than a silent decline.
- **The float step is refused although legacy completes on `15.0`**, recorded as
  `LEGACY_ACCEPTS_FLOAT_STEP := true` -- a divergence stated rather than hidden.
- **No bound, membership test, or exception guard was added to the gate.** The
  legacy branch has none, so closing them would make the modern service stricter
  than the oracle. Recorded as a Server v1 / M13 gap.
- **The two no-op verdicts answer 200, not an error**, because legacy answers
  `{"result": "success"}` and changes nothing in both.

### The load-bearing ordering constraint

The endpoint checks the **flag before the gate**, so once a tutorial completes,
every later step answers `already_completed` and `gate_declined` becomes
unreachable for the rest of that save's life. The committed corpus starts at the
seed value, so the hole step must be sent **first**. `tutorial-live` is written
in exactly that order and says so in its own comment, because any other order
would silently prove only the third verdict while reading as full coverage.

### Verification at the end of the line

- fixture capture: exit **0**, containment **UNCHANGED**, on five consecutive runs
- compat suite: **`Ran 1914 tests ... OK`** (1912 before PR #268), exit 0
- `test_tutorial.gd`: **639 checks** (642 with `--report`), the **38th** hermetic suite
- `verify.ps1` exit **0**; `verify-boot.ps1` exit **0** with **38 hermetic suites and 19 live phases**, guard digest `6978b959...ff348` identical pre/post, **264** log files with zero `[test] FAIL` / `^ERROR:` / `SCRIPT ERROR`
- content validator exit 0, `result: valid`, 21 schemas; preservation manifest **3,258** entries, exit 0
- `openspec validate tutorial --strict` exit 0; `openspec validate --all --strict` exit 0
- evidence: `evidence/tutorial/report.json`, `tutorial-report-v1`, digest **`05f7b12d...c38b`**, 10,634 bytes, byte-identical across three runs

### Residual gaps

- **No stored step** and **no un-complete path** -- `tutorial_step` is a local at
  `command.py:61` and is never persisted, so a mid-tutorial save is
  unrepresentable in the legacy shape.
- **No reward**, **no progress display, step count, ratio, or remaining time.**
- **No gate bounds**, no membership test, no exception guard -- Server v1 / M13.
- **`completed_tutorial` has zero legacy readers**, the tenth committed field in
  this project with no legacy consumer, and the flag is one-way.
- **Zero committed tutorial content** exists: no step list, no count, no gate
  definition, no text. The eight committed village saves are the only progressed
  evidence for the field.
- **The offline double is not the endpoint**; it exists so the no-op verdicts are
  demonstrable without a service.
- **Parity covers three recorded transactions** against the fresh-player corpus
  only, and no progressed-player save exists beyond the villages.
- **No pixel parity** and **no windowed capture**: nothing is rendered.
- **A fourth recorded flaky surface** was added this line: the live phase's
  marker line originally bound `%` to the last string of a concatenation, which
  is a parse error rather than a wrong count -- caught by reading the log files
  rather than the exit code.
