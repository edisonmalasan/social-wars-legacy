# Tasks

## 1. Refusal vocabulary

- [ ] 1.1 Read `apps/server-v1/server_v1_refusals.py` and record the existing closed
      set of **19** codes, the status table, the purpose table and the v0-equivalent
      table before adding anything. **Re-measure, do not inherit line 3's 19.**
- [ ] 1.2 Extend **that module only** with exactly **one** new code and its status:
      `client_dictated_destruction` (409). Design D5.
- [ ] 1.3 Add a v0-equivalent entry, because `test_refusals.py` asserts
      `set(RefusalCode) == set(V0_EQUIVALENT_CODES)` in **both** directions. The v0
      counterpart is `apps/compat-api/combat_envelope.CLIENT_DICTATED_REFUSAL`, so v1
      reuses the same literal. **Do not copy v0's status**: v0's is a 4xx because v0
      applies the client vector before dispatch, while v1's is a 409 conflict; record
      that difference in the module's own comment rather than leaving it implicit.
- [ ] 1.4 **Amend `apps/server-v1/tests/test_boundary_invariant.py:492`** from
      `assertLess(len(list(RefusalCode)), 20)` to `< 21`, and record **in that file**
      why 21 was chosen: the table holds 19, this line adds one, and the pin exists to
      force the ceiling decision into the open. A bound that cannot be reached without
      a decision is a decision prompt. Do **not** weaken the assertion to `<=`.
- [ ] 1.5 **Amend line 3's three assertions on that pin**, which will otherwise fail:
      `apps/server-v1/tests/test_magic.py:2024` and `:2039` both assert
      `assertEqual(19, len(list(RefusalCode)))`, and `:2037` asserts the **exact
      spelling** of the boundary invariant's line
      (`"self.assertLess(len(list(RefusalCode)), 20)"`). A guard that pins its own text
      is unusual; it is not over-specification and it must move with the guard. Record
      the same rationale in that file.
- [ ] 1.6 Assert the vocabulary stays closed in both directions. **Expect no new test
      to be written**: `test_boundary_invariant.py:483` already asserts
      `declared == used & declared` and `test_refusals.py::VocabularyDecisionTests`
      already covers both directions. Measure the two new-code failures going **red**
      before the domain names them — the direction the guard exists for — and record
      the observed message.
- [ ] 1.7 **Do not add** three codes, one per un-derivable quantity (`honor`,
      `resources`, `resources_victim`, `townhall_gold`). Those four are read and
      discarded by the branch and are closed by the existing `client_supplied_delta`
      key-name channel. Three codes for one decision is how a closed vocabulary stops
      being closed. Recorded as a rejected alternative in `design.md` D5.

## 2. Content access

- [ ] 2.1 Read the committed **unit** table through the existing content registry, in
      the same style as `server_v1_magic.py` and `server_v1_collection.py`. **Do not
      transcribe** any committed value into code; re-read the committed package at run.

      **The task's letter and the established pattern disagree, and the pattern wins —
      recorded rather than silently chosen.** Those two modules read **raw**
      `config/main.json` through `server_v1_content.py` (`CONFIG_MAIN`), not the
      normalized package, and line 3 recorded the same divergence and resolved it the
      same way. This slice therefore follows the established pattern, and the normalized
      package is read at run as a **cross-check** rather than as the source.

- [ ] 2.2 Implement the identity lookup resolving by the committed **`legacy_id`**, and
      confirm the three committed id spaces have **zero overlap** — measured: **429**
      units (`type: "u"`), **470** buildings (`type: "b"`), **1** special
      (`type: "l"`). That is what makes "name a committed unit row" a real constraint and
      not a formality, and the suite re-derives the overlap every run rather than
      asserting a constant.
- [ ] 2.3 Implement the gate readers: committed `resurrectable` **verbatim**, with
      **absent reported as absent and never as zero** (`engine.py:159-162` returns
      `False` on an absent key, so reading it as `0` would be a fabrication), and the
      recorded player team from the save. Design D3.
- [ ] 2.4 Record the **team asymmetry** as content of the response, never reconcile it:
      `map_lose_item` accepts any truthy team (`engine.py:221`), `push_dead_unit`
      requires **exactly** team 1 (`engine.py:151`). v0's `TEAM_ASYMMETRY` records the
      same fact without exercising or refusing it.
- [ ] 2.5 Structural guard, not a comment (D2): **no** `Mult`/`Div`/`FloorDiv`/`Mod`/
      `Pow`/`LShift`/`BitAnd` node anywhere in `server_v1_combat.py`. The claim "this
      domain derives nothing" is then mechanically true rather than argued. Prove it by
      injection in 6.5.
- [ ] 2.6 Assert against the committed documents, not literals: unit row count, the
      `legacy_id` set, the zero overlap with buildings and specials, `resurrectable`
      presence and absence per row, and that an absent key is distinguishable from a
      recorded zero.

## 3. Domain service

- [ ] 3.1 New `apps/server-v1/server_v1_combat.py`. It resolves the identity, resolves
      and **reports** both gates, refuses the destruction set, and **writes nothing**.
      There is no write path in this module and the suite asserts the whole function
      inventory has no mutator.
- [ ] 3.2 **Report absence rather than refusing on it.** An identity with no row on the
      recorded map reports `row_present: false` and no team, and the operation succeeds.
      This is measured-necessary: `tests/saves/fresh-player.json` places **40** rows and
      **0** unit rows, so refusing would leave the fresh corpus with **no** exercisable
      success and the live phase with nothing to drive. Design D3's rejected
      alternative records the reasoning.
- [ ] 3.3 The client-dictated figure, where one is present, is **reported** beside the
      named refusal code, never applied and never narrowed. Measured background for
      tasks.md's reviewer: v0's `destruction: 1` is an artefact of
      `combat_payload`'s own construction — executing `combat_payload('resolve')`
      returns `{"attacker_units":[[0,0,1,0]],...}` with the trailing `0` being
      `_DERIVED_IDENTITY` — and the committed fixture step **7** destroyed **two** rows
      at v0's counterpart for `A=3, B=1`. **Do not carry v0's `1` forward as a rule.**
- [ ] 3.4 All refusals — `client_dictated_destruction`, the out-of-table identity, the
      structural channel's own codes — resolve **before** any snapshot or write, and
      since there is no write, assert the ordering structurally. Design D4.
- [ ] 3.5 Record the two `None`-deref facts as **unreachable in v1**, with their real
      status: reachability in the preserved server is **established by execution**
      (fixture steps 2 and 4, HTTP 500, save byte-identical), while whether a real
      client ever sent either shape is **unknown**. Do not restate it the way
      `docs/legacy-m13-line4-candidates.md` §8 does; see `design.md` §Corrections C4.

## 4. Intent layer

- [ ] 4.1 One `INTENT_SCHEMAS` row `{"player_id", "unit_id"}` and one
      `ADDRESSING_FIELDS["combat"] = "unit_id"`. `addressed_path()` resolves to the
      unit's row path. **No operation field** — the route has exactly one action, and a
      second name over it would be line 3's D7 problem restated with nothing to
      distinguish. Design D1.
- [ ] 4.2 The route's action vocabulary is **v1's own**, never `command.py`'s branch
      name. `/v1/combat`, not `/v1/end_attack`: naming a v1 route after a legacy command
      would make v1's vocabulary a subset of the 63 branch names, which is the
      inheritance line 2 recorded the boundary exists to stop.
- [ ] 4.3 `unit_id` deliberately **not** added to `NON_NEGATIVE_ADDRESSING`, and the
      omission asserted rather than left implicit: zero and every negative resolve to no
      committed unit row and are refused by the out-of-table refusal. Same shape as line
      3's `magic_id` decision.
- [ ] 4.4 The delta check runs **before** the closed-key check, restated from the
      caller's side as the measured closed set of the **three structural** codes the
      intent module names (`MALFORMED_REQUEST`, `UNKNOWN_REQUEST_FIELD`,
      `CLIENT_SUPPLIED_DELTA`) and **no** combat-domain code. Note the shape already in
      the table: `DELTA_KEYS` already contains `damage`, `result`, `outcome`, `life`,
      `hp`, `health`, so `"damage": 3` is refused **400** here while
      `"attacker_units": [[0,0,3,1]]` is refused **409** by the domain. Two encodings of
      one request, two different mistakes, two different answers — record that in the
      module rather than leaving it to be discovered as an inconsistency.

## 5. Route

- [ ] 5.1 `COMBAT_PATH = "/v1/combat"` declared as a **literal**, matching the other
      three route literals.
- [ ] 5.2 Registered in `ROUTES` as `"POST /v1/combat"`; the banner, the enumeration and
      the route-path test all agree.
- [ ] 5.3 `post_combat` is **byte-identical in shape** to `post_collect` /
      `post_collection` / `post_magic`: hand the bytes to the intent module, call the
      domain, translate the outcome through `_envelope`. No arithmetic, no refusal
      vocabulary, no domain value construction. Assert the transport names no refusal
      code — an established invariant of the boundary, restated not re-decided (D10).
- [ ] 5.4 **Confirm, by measurement rather than by not editing:**
      `git diff --name-only -- apps/compat-api` returns **no path**, so no v0 route was
      added, moved or removed; and `tools/route-coverage/` is untouched. Its suite
      re-runs in 8.7 at **44** tests. The routed/unrouted split therefore stays
      **39**/**24**.

## 6. Client surface

- [ ] 6.1 Register the combat intent on the `ServerV1Api` facade in the exact shape of
      the existing forwarders, with its own typed result module and `_failure` factory,
      and `COMBAT_PATH := "/v1/combat"` as a literal.
- [ ] 6.2 Widen `GameApi` **only** if the three implementations genuinely disagree on
      the return type, and measure that disagreement rather than assuming it: the fake,
      the legacy-v0 one and v1 must each be inspected. Line 1 recorded the first
      widening, line 3 the third.
- [ ] 6.3 New hermetic suite `res://tests/test_combat_v1.gd`, re-deriving the id-space
      overlap, the gate figures and the corpus figures from the committed documents on
      each run, with its report generated from the live model.

      **Constraint on what this suite may name, and it is an existing guard rather than
      a new one.** `test_combat_actions.gd` scans the **whole client tree**
      (`res://scripts` + `res://tests`) for thirteen needle fragments — `resolve_damage`,
      `damage_for`, `apply_attack`, `hit_chance`, `honor_for`, `reward_for`,
      `complete_mission`, `lost_count`, `resolve_type`, `is_occupied`, `in_bounds`,
      `terrain_at`, `frame_duration`, `travel_time` — read with string contents blanked.
      A delivered client source using any of them fails that suite **correctly**. Note
      that suite's count is **not** a fixed number: it walks the tree, so it rises by
      design as this line adds two sources.
- [ ] 6.4 Cover each refusal independently against the real service through the typed
      facade: destruction figure, out-of-table identity, non-canonical identity form,
      client-supplied delta (in both encodings), unknown request field, unknown player,
      unreadable state. Each through its own `_refusal` / `_failure` factory, never by
      constructing the shape a refusal is supposed to make impossible.
- [ ] 6.5 Add anti-invention guards in the established shape and **prove them by
      injection**: pin the domain module's whole function inventory; a case-folded
      **substring** stem guard over the invented-mechanism names, in **both**
      directions; the arithmetic-node guard from 2.5; and the stem list's own pin plus
      a planted positive control, because a guard whose target list can be shortened to
      nothing passes forever.

      Record the **measured** failure count of each probe. Three probes, minimum:

      | probe | injected helper | expected to trip |
      |---|---|---|
      | destruction count | `destruction_count_for(unit)` computing from request fields | arithmetic guard, inventory, stem, stem-list non-vacuity |
      | payout | `honor_payout(honor)` | inventory, stem, stem-list non-vacuity |
      | no reserved word | `resolve_unit_outcome(a, b)` — borrows **no** reserved stem | inventory only |

      The third row is the informative one and its count is **expected to be the
      lowest**: `godot-friends` and `godot-construction-assist` both measured that the
      inventory pin is the real gate and the stem list the belt. Restore every file
      **byte-identically** and verify by digest, with the module's final byte pinned to
      the baseline and zero NUL bytes asserted. Re-run the suite green after the probe
      set and require `git diff --numstat --ignore-cr-at-eol` plus `git status --short`
      to equal their pre-probe values.

      **The harness must re-assert the recorded defects rather than assume them**: LF
      normalisation before mutation; an **abort** when a probe reports zero
      `[test] FAIL` lines, because a parse-error detection proves nothing about a guard
      (`godot-unit-experience` recorded a GDScript slip that produced six silent
      passes); and **no universal trailing-newline rule** — pin the restored file's
      final byte to the baseline and *report* its newline state instead.
- [ ] 6.6 Measure whether either delivered client source names a boundary token owned
      by `test_stored_item_placement.gd`, and amend that suite's ownership hand-off
      **only** if it does, the way `godot-unit-collection` and line 1 each did. Do not
      loosen the whole-tree absence for any other file. If no amendment is needed,
      record that rather than editing it.
- [ ] 6.7 Write the deterministic report via `--report=` to
      `apps/client-godot/evidence/combat-v1/report.json`, generated from the live model.
      Record the report's own raw digest **and a measured** pure-LF flag.
      `godot-market-trade` shipped a sibling report that hard-coded that flag, and
      copying a field *and its value* across file forms is how a guard becomes a lie —
      three sibling reports carry it as `false` correctly, from CRLF files.
- [ ] 6.8 Amend the two count pins **in place**, as established for a count an incoming
      line legitimately moves: `test_auction_schedule.gd:165-166` and
      `test_market_trade.gd:212-213`, **53 → 54** hermetic and **26 → 27** live phases.
- [ ] 6.9 **Fix two stale pin messages while bumping them.** `test_market_trade.gd:1562`
      and `:1604` still read "fifty-two hermetic suites" and "twenty-five live phases"
      while the constants are 53 and 26 — a value/prose mismatch **left by line 3** and
      never corrected. This line moves both numbers, so it corrects both strings.
      `test_auction_schedule.gd`'s messages are already generic and need no such fix;
      check rather than assume.
- [ ] 6.10 Confirm — by measurement — that the count pins' live-phase regexes read the
      **widened** `$serverV1Phases` list before bumping the live count. Line 1 recorded
      that an earlier version of these pins read only `$livePhases` and so could not
      see the thing it was counting, and line 1 fixed it; verify rather than assume. The
      per-surface "no live phase mentions market/auction" checks must also run over the
      widened list. Note `test_market_trade.gd`'s per-surface check is scoped to
      "market" and "auction" only, so a phase named `combat-live-v1` should not trip
      it — **verify that, do not assume it**.

## 7. Live phase

- [ ] 7.1 Add `/v1/combat` to `KNOWN_ROUTE_PATHS` in
      `apps/client-godot/server_v1_live_phase.py`. It is a closed set precisely so a
      typo cannot produce a passing phase whose evidence file names a route that does
      not exist. Join `EXPECTED_BANNER_ROUTES` with its order and count asserted, rather
      than generalising the banner check into a count.
- [ ] 7.2 Register `combat-live-v1` in `apps/client-godot/verify-boot.ps1`'s
      `$serverV1Phases` list, on the v1 port, with its explicit `--route-path`, **and
      without `--expect-save-mutation`**.

      **This is the correct answer, not an omission, and it is the one place this line
      inverts a harness convention.** Every prior v1 phase asserts the corpus save
      mutated. This transaction destroys nothing and writes nothing, so there is no
      mutation to assert; the phase's assertion is the **whole-document byte-identity**
      instead. The harness's `ExpectSaveMutation` defaults to `$false`, so the flag is
      simply not set — and that absence must be recorded in the phase's own
      `Assertions` string so a reader does not read the omission as a mistake.
- [ ] 7.3 The phase drives one resolve against a disposable corpus on loopback and
      asserts: the typed response carries the committed row, the `resurrectable` gate
      verbatim, `row_present: false` and no team (the fresh corpus places **0** unit
      rows), and the whole persisted document including `privateState["deadHeroes"]`
      is byte-identical before and after.

      **Seed nothing and address a committed unit identity, not a map key.** Measured:
      `tests/saves/fresh-player.json` places 40 rows, 11 distinct ids, **all committed
      buildings**, 0 unit rows, with `deadHeroes: {}`. So the *identity* resolves from
      committed content while the *row* is legitimately absent, and that combination is
      the interesting case rather than a degenerate one.
- [ ] 7.4 Assert the corpus save was removed afterwards, the v1 port was released, no
      working-tree `saves/` exists, and no `socialwars-server-v1-*` directory is left.
- [ ] 7.5 Note and do **not** change: the harness's `readiness()` probe posts to
      `COLLECT_PATH` by design, so every v1 phase records
      `"readiness_code": "unknown_player"`. Record it rather than generalising it.
- [ ] 7.6 Print one typed marker per response from the **typed result** rather than the
      raw payload, so the assertion is about what the client read rather than bytes
      that happened to arrive. Line 3 recorded that a live arm with no positive typed
      marker can still produce refusal markers and pass with the success path never
      taken.

## 8. Verification actually run

Record only what was run, with its observed result. Interpreter is the pinned CPython
**3.9.13** (`& "$env:TEMP\opencode\cpython39\pkg\tools\python.exe" -B`, **never** the
PATH alias), engine Godot **4.7.2.stable**, loopback only (v0 `127.0.0.1:5056`, v1
`127.0.0.1:5057`). Baselines re-measured before this change and **unchanged** by it:

- [ ] 8.1 `python -B -m unittest discover -s apps/server-v1/tests -p "test_*.py" -v`
      → the recorded baseline is **`Ran 376 tests`**; this line must report its own
      count against it. **Expect and record a flaky error rather than chasing it**:
      `test_live_server.PortBindingTests.test_run_py_refuses_to_start_on_a_busy_port`
      failed once on the baseline run at a `TIME_WAIT` socket on **5057**, and that file
      then passed twice consecutively. **Re-run before treating it as a regression.**
- [ ] 8.2 `godot --headless --path apps/client-godot --script res://tests/test_combat_v1.gd`
      and the same with `--report=<repo>/apps/client-godot/evidence/combat-v1/report.json`
      → record both counts, the report's byte count and its sha256, and confirm the
      report is byte-identical across consecutive runs.
- [ ] 8.3 `python -B -m unittest discover -s apps/server-v1/tests -p "test_refusals.py" -v`
      → run this **before** 1.4 and 1.5 as well as after, so the two amendments are
      witnessed rather than assumed.
- [ ] 8.4 The v1 live phase standalone, against a disposable corpus on loopback
      → record the harness's own check count, `"ok": true`, the route it actually drove,
      and the Godot suite's `PASS` count.
- [ ] 8.5 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
      — expected unchanged at the recorded baseline of **3077**, and **re-run rather
      than assumed** → report the observed count and confirm
      `git diff --name-only -- apps/compat-api` returns **no path**.
- [ ] 8.6 `powershell -File apps/client-godot/verify.ps1`
- [ ] 8.7 `powershell -File apps/client-godot/verify-boot.ps1`
      → record the totals this line produces: **54** hermetic suites (was 53),
      **23** v0 live phases, **4** v1 live phases, **27** total. Record the guard digest
      before and after, and count the **referenced** logs — not
      `.godot/verify-boot/`, which is never cleaned, so a clean zero computed over it is
      a statement about every run ever made rather than about this one.
- [ ] 8.8 `python -B -m unittest discover -s tools/route-coverage/tests -p "test_*.py" -v`
      — **the correct form is `-s tools/route-coverage/tests`**, which discovers **44**
      tests. The `-s tools/route-coverage` form discovers **0** tests and **exits 0**,
      because `tools/route-coverage/tests` has no `__init__.py`; a command reporting
      `Ran 0 tests ... OK` is not a pass. Run **both** and record both counts, so the
      correction is a measurement rather than a note.
- [ ] 8.9 `python -B packages/game-content/tools/validate_content.py`
- [ ] 8.10 `python -B tools/hash-manifest/hash_manifest.py verify`
- [ ] 8.11 `openspec validate --all --strict` → the recorded baseline is
      **78 passed, 0 failed**. Note that the total alone never says which stage is
      done: during a change the composition is main specs plus one change, and after
      Sync it is main specs with zero changes. Record the composition, not just the sum.
- [ ] 8.12 `git status --short` showing no content-package, fixture, save, config,
      village, conversion-package, registry-manifest, or legacy-source byte changed. No
      `.pyc` (this line's own `py_compile` will create one if run — delete it, do not
      allow-list it), and no working-tree `saves/`.

      The regenerated `apps/client-godot/evidence/boot/boot-report.json` must be
      **diffed and every insertion accounted for**: a `log` renumbering and a content
      change look alike in a long insertion diff, and inserting one hermetic suite plus
      one live phase displaces every later index in both lists.

## 9. Claim limits to record before merging

- [ ] 9.1 Record that **this line derives nothing at all**, and that the reason is
      §4 of the selection record: **0 of 29** remaining pool branches have a committed
      value naming their outcome. `end_attack` is the strongest available target, which
      is not the same as a good one, and the selection record says so itself.
- [ ] 9.2 Record that **no parity is claimed against the legacy server**. The oracle is
      `tests/fixtures/godot-combat-actions/` — **13 transactions**, 10 carrying
      `end_attack`, 11 occurrences, over 14 `request.json` files including the login —
      read as committed bytes and **never re-captured**. The fixture was archived on
      **2026-10-05** by a delivered line; re-capturing it would produce the same bytes
      for a different commit.
- [ ] 9.3 Record the **established/unknown split** on the two `None` dereferences
      precisely, because the binding selection record states it more weakly than the
      evidence supports:
      **established** — both are reachable, executed, HTTP 500, save byte-identical, and
      a raise anywhere discards the whole save because `command.py:30,32` dispatches the
      batch before saving; **unknown** — whether a *real client* ever sent either shape,
      since the Flash client was never executed and every fixture payload is crafted.
      State that this **corrects** `docs/legacy-m13-line4-candidates.md` §8 without
      editing that document.
- [ ] 9.4 Record that the **destruction is refused in full and nothing is destroyed**,
      and specifically that **v0's `destruction: 1` was not carried forward**: it is an
      artefact of `combat_payload`'s construction, and the same v0 route destroyed **two**
      rows for `A=3, B=1` (fixture step **7**), a divergence the fixture manifest records
      as such. Reproducing either "one" or "all eligible" would be an invention, and
      the second is the client-dictated destruction wearing a different spelling.
- [ ] 9.5 Record that the two committed gates are **reported, not enforced**, that an
      absent committed `resurrectable` is reported as **absent and never as zero**, and
      that the team asymmetry between `map_lose_item`'s truthy test and `push_dead_unit`'s
      exact-`1` test is **recorded and not reconciled** — the latter is **unknown**, and
      every committed unit row being on team 1 is why it is unexercisable.
- [ ] 9.6 Record that the **first half** of the post-execution proof is a
      **specification** check and not an evidence claim, because v1 is the only
      implementation writing the save on this path. Record that the second half is the
      **whole-document** comparison, not only the addressed subtree and not only the
      seven stored resources, and that it is falsifiable because **any** destruction of
      **any** size fails it.
- [ ] 9.7 Record that the live phase **deliberately asserts no save mutation**, and that
      this is the first v1 phase to do so. Every prior v1 phase asserts the corpus save
      mutated; this one cannot, because the transaction writes nothing. The
      `--expect-save-mutation` flag is absent by design, not by oversight.
- [ ] 9.8 Record that **no combat rule is resolved**: damage, health, defence, hit
      chance, attack outcome, and life/interval arithmetic are absent. The census is
      re-derived every run and each zero is **rule-scoped** — "zero consumers" means
      zero under the named rule over the named modules, never "never used"
      unqualified.
- [ ] 9.9 Record that **nothing is rendered**, so there is **no windowed capture and no
      pixel-parity oracle** for this line.
- [ ] 9.10 Record that **absence of a server-side rule says nothing about what the
      Flash client displayed, sent, or expected**, permanently unestablished here. Load-
      bearing: this line has **no derivation at all**, so every rule it specifies is
      derived from committed content or the preserved branch, and none was observed.
- [ ] 9.11 Record that **no ordinal is claimed** — for any zero-consumer field, for the
      recorded flaky surfaces, or for anything else. The surrounding sections of this
      repository already disagree on the flaky-surface count over different scopes, and a
      single number over that class would repeat a mistake already recorded once.
- [ ] 9.12 Record the **`map_lose_item` call-site figure** as **two** branches reaching
      **one** helper, and that `godot-unit-behaviors`'s "three doors" counted
      `push_dead_unit`'s callers and `map_lose_item` separately. That archived line is
      **not** edited; the discrepancy is recorded here and this line's suite names the
      module at each call site.

## 10. Instrument faults and corrections

Recorded rather than quietly edited, in the shape `godot-market-trade` and
`godot-construction-assist` established.

- [ ] 10.1 Record that **this line's own measurement, not an inherited one, produced the
      twelve-field inventory's "three read after assignment, one reaching stored
      state"** figure, by reading the span directly. The selection record §9.6 records
      that its own "uses after assignment" tally over-counted because it included the
      pre-initialiser lines `:826-837`; do not reuse that tally and do not present this
      figure as the selection record's.
- [ ] 10.2 Record the **`attack` substring trap** for this line specifically: 12
      whole-file and 5 code-only occurrences, all twelve inside `end_attack`,
      `attacker`, `attacker_units`, `flash_reload_attack`, whole-word **0**. Reporting
      `12` without that sentence is the exact trap §4 of the selection record names.
- [ ] 10.3 Record the **two stale pin message strings** left by line 3
      (`test_market_trade.gd:1562` and `:1604`, "fifty-two" / "twenty-five" against
      constants 53 / 26) and that this line corrected them while bumping. A pin whose
      message disagrees with its constant is a small lie that survives re-runs.
- [ ] 10.4 If the Apply stage finds that the selection record's `end_attack` span or any
      line attribution differs from this design's, correct **this design file** in a
      corrections section rather than editing the numbers in place. **One correction is
      already owed and recorded:** `design.md` §Corrections C3 — the selection record
      says `attacker_units = None` is at `command.py:837` and it is at **`:836`**
      (`:837` is blank). C1 (the guard at line **492**, not the `:392` line 3's archived
      proposal cites) and C2 (the pins measured at 53 / 26) are recorded for the same
      reason.
- [ ] 10.5 Record the **`test_combat_actions.gd` whole-tree needle scan** as a
      constraint the delivered client sources had to be written under, and confirm it
      still passes with **two more files** in its walk. Its count is not a fixed number
      and rises by design; do not pin it.
- [ ] 10.6 **GDScript and PowerShell traps, all measured in this repository and all
      reusable**: `RegEx` has **no** `MULTILINE` flag on this engine; every JSON number
      decodes as a `float`; `String(PackedByteArray)` does not exist (use
      `FileAccess.get_file_as_string`); `%r` emits an engine `ERROR:` line that fails
      `verify-boot.ps1`; `for x in (a, b, c)` is a grouping expression and a **parse
      error**; `test_base.gd` records a function abort as a **PASS**, so a crashed
      function is invisible; capturing a native command into a PowerShell **variable**
      silently yields zero lines, so pipe to `Out-File`; suites are written pure LF and
      converted to CRLF at the end; and `test_project_scope.gd` catches a stray
      `__pycache__/*.pyc` — **delete, never allow-list**. Note that
      `test_project_scope.gd` is owned by `verify.ps1`, not `verify-boot.ps1`.
- [ ] 10.7 **Recorded flaky surfaces, none fixed by this line**, each with its honest
      owner: the `test_no_server_is_running` port assertions on 5055/5056; the
      `verify-boot.ps1` `^ERROR:` guard catching a nondeterministic RID-leak or shutdown
      line; the display-sensitive `verify.ps1`; `test_collect_endpoint`'s sub-second
      `too_early` budget (owned by `godot-building-collect`); `test_base.gd` recording an
      abort as a pass; and **`tests/test_live_server.py` failing on a `TIME_WAIT` socket
      at 5057**, which is this line's own service and was measured once on the baseline
      run. Re-run before treating any of them as a regression, and claim **no** ordinal
      over the class (9.11).
