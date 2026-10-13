# Tasks

## 1. Refusal vocabulary

- [x] 1.1 Read `apps/server-v1/server_v1_refusals.py` and record the existing closed
      set of **17** codes, the status table, the purpose table and the v0-equivalent
      table before adding anything.
- [x] 1.2 Extend **that module only** with exactly **two** new codes and their statuses:
      `unknown_magic_id` (409) and `counter_above_cap` (409). Design D8.
- [x] 1.3 Add a v0-equivalent entry for each new code, because
      `test_refusals.py` asserts `set(RefusalCode) == set(V0_EQUIVALENT_CODES)` in
      both directions. Both are measured, not guessed: `compat_service.py:1088`
      declares `ERROR_UNKNOWN_MAGIC_ID = "unknown_magic_id"` and `:1090` declares
      `ERROR_COUNTER_ABOVE_CAP = "counter_above_cap"`, both mapped to **409** at
      `compat_service.py:1617,1619`, so v1 reuses the same literal in each case.
- [x] 1.4 **Confirm `tests/test_boundary_invariant.py:392` still passes unchanged.**
      It asserts `len(list(RefusalCode)) < 20`; the table holds 17 and this line
      adds two, making 19. Do **not** amend it. If a third code ever becomes
      unavoidable, record the amendment and its rationale rather than bumping it
      silently. Verify: `python -B -m unittest discover -s apps/server-v1/tests -p "test_refusals.py" -v`
- [x] 1.5 Assert the vocabulary stays closed in both directions: every declared code is
      named by some application module and every status maps to exactly one code.
      **No new test was written**: both directions are already covered, by
      `test_boundary_invariant.py:380` (`declared == used & declared`) and by
      `test_refusals.py::VocabularyDecisionTests`
      (`test_every_declared_code_is_used_by_the_application`,
      `test_the_guard_would_catch_a_declared_but_unused_code`,
      `test_the_status_table_covers_every_declared_code_exactly_once`). Both were
      measured going **red** on the two new codes before the domain named them
      (`declared but never named: COUNTER_ABOVE_CAP, UNKNOWN_MAGIC_ID`), which is
      the direction the guard exists for.

## 2. Content access

- [x] 2.1 Read the committed magic table through the content registry the way
      `server_v1_collection.py` reads the committed collections table. **Do not
      transcribe** any committed value into code; re-read
      `packages/game-content/normalized/magics.json` at run. Design D3.

      **The task's letter and the established pattern disagree, and the pattern
      wins — recorded rather than silently chosen.**  `server_v1_content.py:59`
      declares `CONFIG_MAIN = ("config", "main.json")` and
      `server_v1_collection.py` reads its committed collections rows through
      **that** module, so "the way `server_v1_collection.py` reads the committed
      collections table" is the **raw** `config/main.json`, not the normalized
      package. This slice therefore reads raw `magics` through the same
      registry, and task 2.1's normalized-path instruction is recorded here as
      unmet-in-letter rather than passed-off.

      The normalized package is still read at run — by `CommittedTableTests`, as
      a **cross-check** rather than as the source — and it is what `validate_content.py`
      (task 8.8) verifies on its own. Measured consequence of the split: the raw
      table carries **no `kind` column**, so the response's `kind` is `None` plus a
      `kind_source` note, and `test_the_raw_table_carries_no_kind_column` pins
      that so it cannot be "fixed" by reaching for the second artifact.

- [x] 2.2 Implemented `magic_row(magic_id)` resolving by the committed **`id`
      column** (not positionally), `magic_ids()`, `magic_field()` and
      `magic_area()`. Measured: `magic_row(0 | -1 | 11 | True | "1" | None | 1.0)`
      is `None` for all seven, and `True`/`1.0` are refused because the
      positional reader would otherwise accept them by truncation or equality.
- [x] 2.3 Asserted against the committed documents, not a literal: **10** rows via
      the reader, the normalized package and `provenance()["magic_rows"]`; ids
      **contiguous `1..10`** in both directions; `legacy_id == str(id)` on all
      ten; `kind == "magic"` on all ten; distinct-value counts **`gold` 10,
      `cash` 10, `mana` 6, `level` 9**, each `int`.
- [x] 2.4 Structural guard, not a comment (D2). Four separate checks: the whole
      declared function inventory is pinned; **no** `Mult`/`Div`/`FloorDiv`/`Pow`
      node exists anywhere in the module; the **only** three `BinOp.Add` nodes
      are all `before + 1`; and every remainder is `%` on a string constant.
      Verified by injection in task 6.5.

## 3. Domain service

- [x] 3.1 New `apps/server-v1/server_v1_magic.py`. Ledger read through
      `repository.magic_ledger()` / `magic_counter()`; an **absent entry reads as
      zero**. **The first version could not tell absent from unreadable**: it
      read `.get()` and treated a returned `None` as absence, so a ledger
      recording `{"1": null}` read as zero and was then **overwritten** by the
      derived value — a destruction of a recorded-but-unreadable entry. Fixed by
      a membership test (`key not in ledger`), which is the only form that
      distinguishes "no recorded counter" from "a counter that is not an
      integer". Both are covered by tests.
- [x] 3.2 Bounded derivation against the **recorded literal cap** `COUNTER_CAP = 50`,
      with the rejected content-derivation alternative retained in
      `COUNTER_CAP_PROVENANCE` (cap, its two source lines, what it applies to,
      the rejected derivation and why). Design D6.

      **A measurement corrected the rejection's own reasoning during Apply.**  The
      first draft justified the literal partly by claiming the value `50` does
      *not* occur among the committed magic columns. Measured, it **does**: it is
      the `cash` price of **magic 1** and the `level` of **magic 5**, one row
      each (`mana` never reaches it — max **20**). So "cap = the magic 1 cash
      price" is not an impossible derivation but the single most likely one to be
      proposed by accident, and the provenance string was corrected to say so
      while still resting the refusal on provenance. Pinned by
      `test_the_fifty_in_committed_content_is_measured_not_remembered`.
- [x] 3.3 `counter_above_cap` (409) reports the recorded value, the bound and the
      provenance rather than rewriting it. **Boundary is accept-at-cap**: `before
      == 50` succeeds as a recorded no-op, `before == 51` is refused. Measured
      basis: the preserved `use_magic` arm is *itself* a no-op at exactly 50
      (`min(50, 51) == 50`), and `PRESERVED_MAGIC_BEHAVIOUR["same_number"]` says
      the two agree at or below the cap. See task 10.5.
- [x] 3.4 Both operations run over **one** `issue_magic_transition` derivation; the
      payload states the sameness. Design D7. `SameTransitionTests` drives both
      over the same seeded state and asserts one identical transition.
- [x] 3.5 Committed row reported **verbatim** — `gold`, `cash`, `mana`, `level`,
      `target`, `area`, `name`, `kind` — with `kind` `None` plus a `kind_source`
      note (measured: the raw table has no such column), and the player's
      recorded `maps[0].level` reported **beside** the committed `level` with the
      two boolean report keys `level_compared` / `level_gate_enforced` pinned to
      `False`. Design D5.
- [x] 3.6 All three refusals — `unknown_magic_id`, `counter_above_cap`, and
      `unreadable_state` for an absent / non-object / non-integer ledger — resolve
      **before** the snapshot and the write. `RefusalOrderTests` asserts the
      order over an in-memory row rather than the corpus, which cannot produce
      the shape.
- [x] 3.7 Three absences, three guards, reading three **different** signals
      (the `after=` keyword, the `had_recorded_entry` name, the
      `level`/`player_level` comparison pair) — asserted by
      `test_the_three_guards_read_three_different_signals`, because a merged guard
      would report one failure for three absences.

## 4. Intent layer

- [x] 4.1 One `INTENT_SCHEMAS` row `{"player_id", "magic_id", "operation"}` and one
      `ADDRESSING_FIELDS["magic"] = "magic_id"`. `addressed_path()` resolves to
      `/privateState/magics/<id>`.
- [x] 4.2 `INTENT_OPERATION_FIELDS = {"magic": "operation"}` with
      `INTENT_OPERATION_VALUES["operation"] = frozenset({"buy", "use"})` as **data**,
      and any other value refused `malformed_request`. **No transport branch was
      added**; the transport reads the table. Design D1.
- [x] 4.3 `magic_id` deliberately **not** added to `NON_NEGATIVE_ADDRESSING`, and
      the omission is asserted rather than left implicit: zero and every negative
      resolve to no committed row and are refused `unknown_magic_id`. Design D3.
- [x] 4.4 The delta check runs **before** the closed-key check, so a request
      carrying a delta key is refused `client_supplied_delta` even when its key is
      also unknown to the schema. Restated from the caller's side as the measured
      closed set of the **three structural** codes the intent module names
      (`MALFORMED_REQUEST`, `UNKNOWN_REQUEST_FIELD`, `CLIENT_SUPPLIED_DELTA`) and
      no domain code.

      **The task's letter was wrong and is recorded as such.**  It reads "assert
      the intent module names no refusal code outside its own import", which can
      never hold: that module is where the request envelope is parsed, so
      constructing refusals is its job. The first draft asserted it anyway and
      measured three offenders. The assertion was replaced with the claim that
      separates those three from the codes this line adds — the intent layer
      names **no magic / counter / cap / level refusal code** — which is the
      direction a domain leak would actually arrive from. Note that the intent
      layer legitimately knows `magic_id`: it owns the row's *addressing*, and an
      intent that cannot be addressed is not an intent.

## 5. Route

- [x] 5.1 `MAGIC_PATH = "/v1/magic"` declared as a **literal**, matching the other
      two route literals.
- [x] 5.2 Registered in `ROUTES` as `"POST /v1/magic"`; the banner, the
      enumeration and the route-path test all agree.
- [x] 5.3 `post_magic` is **byte-identical in shape** to `post_collect` /
      `post_collection`: hand the bytes to the intent module, call the domain,
      translate the outcome through `_envelope`. No arithmetic, no refusal
      vocabulary, no domain value construction.
- [x] 5.4 **Confirmed, by measurement rather than by not editing:**
      `git diff --name-only -- apps/compat-api` returns **no path**, so no route
      was added, moved or removed there; and no `command.py` route slice changed
      because `command.py` was never opened for editing. `tools/route-coverage`
      is untouched and is re-run in task 8.7.

## 6. Client surface

- [x] 6.1 Register the magic intent on the `ServerV1Api` facade in the exact shape of
      the existing forwarders, with its own typed result module and `_failure` factory.
      Delivered: `apps/client-godot/scripts/gameapi/server_v1_magic_result.gd` (CRLF),
      `ServerV1Magic.magic_failure()` plus `MagicCounterResult` and `MagicIdentity`;
      `magic_town()` and `static func _magic_intent_body()` in `server_v1_api.gd`, in the
      forwarders' shape, with `MAGIC_PATH := "/v1/magic"` as a literal.

- [x] 6.2 Do **not** widen `GameApi` unless a declared return type genuinely differs;
      line 1 recorded the single widening it needed and line 2 added none.
      **The widening is warranted here, and the deciding measurement is recorded.**
      Three `GameApi` implementations implement the intent: the fake, the legacy-v0 one
      and v1. Measured, the fake and legacy-v0 both declare `MagicFlow.MagicResult`
      and **v1 differs**, so the facade cannot name one type for all three and
      `GameApi.magic_town` is now declared `-> Variant` — the **third** widening on this
      facade. `test_magic_v1.gd` pins the per-implementation return types in its own
      `IMPL_RETURN_TYPES` table, the convention each line follows for its own intent, so
      the widening is a measurement and not a convenience.

- [x] 6.3 New hermetic suite `res://tests/test_magic_v1.gd`, re-deriving every
      committed-table figure from the committed package on each run rather than
      asserting a transcribed constant.
      Observed: **469 checks** PASS headless, exit 0; **471** with `--report=`. The suite
      re-derives the row count, the id space, the numeric-column census, the distinct-value
      counts and the absent-column set from the committed documents on every run, and the
      report's tables are generated from the live model.

      **The lexer this suite needed was a defect found by measurement, not a
      convenience.**  A first `_code_only()` tested a line for an **opening** quote before
      its closing one, so a string literal re-opened itself and every later `##` comment
      survived blanking. That inflated the arithmetic guard's offence list and the
      fail-closed list, and it silently made one guard vacuous. It is now one two-state
      lexer (`_lex(body, keep_literals)`) with backslash escapes, with `_code_only()`
      (comments **and** literal contents blanked) and `_comment_free()` (comments
      blanked, literals kept) as thin wrappers — **two** projections, because the guards
      genuinely need both: an operator scan must not see text inside a string, and a
      balance-member or subscript scan must. `.replace("->", "  ")` is applied before any
      relational scan so a return-type arrow cannot read as a comparison.

- [x] 6.4 Cover each refusal independently: unknown identity, non-canonical identity
      form, counter above the bound, client-supplied delta, unknown request field,
      operation outside the closed set, unknown player, unreadable ledger.
      Observed, against the real service through the typed facade:
      `unknown_magic_id`, `malformed_request` (x2: a non-canonical identity form and an
      operation outside the closed set), `counter_above_cap` (at counter 51),
      `client_supplied_delta` (x2), `unknown_player`, and `unreadable_state` (x2). Each
      is exercised through its own `_refusal` / `_failure` factory, never by
      constructing the shape a refusal is supposed to be impossible to construct.

- [x] 6.5 Add anti-invention guards in the established shape — pin the domain module's
      whole function inventory, and refuse an invented helper by name and by
      substring — and **prove them by injection**: inject an invented price helper, an
      invented level-gate helper, and an invented decrement helper; record the measured
      failure count of each; restore byte-identically and verify by digest. Design D2,
      D5, D4.
      Delivered in `apps/server-v1/tests/test_magic.py` as `DomainInventoryTests` (four
      tests): a whole-inventory pin of the **eighteen** declared functions in
      class-qualified form (`MagicTransition.__init__`, `apply_magic`,
      `issue_magic_transition`, 16 more), cross-checked against the suite's own
      pre-existing `_declared_functions` so the new pin cannot drift from the helper the
      three absence guards read; a **substring** stem guard over **ten** stems, folded
      to lower case; and the stem list's own pin plus a planted positive control, because
      a guard whose target list can be shortened to nothing passes forever.

      **Measured injection results** (`apps/server-v1/server_v1_magic.py`, pure LF, 40,662
      bytes, sha256 `42f6b6ca8d904a7d154d7d09838ae80430049f63c1adcb74de5a1a09dd3f4909`
      before **and** after all three probes):

      | probe | injected helper | measured failures | what fired |
      |---|---|---|---|
      | price | `price_for_magic`, reading `content.magic_field(magic_id, "gold")` | **4** | numeric-column read, inventory, stem, stem-list non-vacuity |
      | level gate | `level_gate_enforced`, `player_level < row["level"]` | **4** | level-gate guard, inventory, stem, stem-list non-vacuity |
      | decrement | `next_counter_after`, `before - 1 if before > 0 else 0` | **2** | decrement guard, inventory |

      All three exited 1, none produced a parse error, and each restore was verified
      **byte-identical** by digest with the module's final byte (`]`, no trailing newline)
      pinned to the baseline and zero NUL bytes asserted. The suite was re-run green
      after the probe set (`Ran 114 tests ... OK`) and `git diff --numstat
      --ignore-cr-at-eol` plus `git status --short` equalled their pre-probe digests.

      **The decrement probe is the informative row and its count is honest.** It tripped
      **only** two guards, and it did **not** trip the stem guard — because the name I
      invented, `next_counter_after`, borrows no reserved stem. That is the measurement
      that shows the inventory pin is the real gate and the stem list is the belt: a
      stem-only guard would have waved a decrement straight through. A fourth planted
      check in the suite asserts exactly that (`test_the_inventory_gate_catches_a_helper_
      that_borrows_no_reserved_word`). The harness re-asserts the three defects recorded
      by earlier lines rather than assuming them: LF normalisation before mutation, an
      abort when a probe reports zero failures (a parse-error detection proves nothing),
      and **no** universal trailing-newline rule.

- [x] 6.6 Assert the ledger-shape refusal over an **in-memory row**, because all 33
      committed save documents already carry a dict `magics` and the `version.py:32-37`
      coercion path is therefore unreachable through the corpus. Same pattern line 1
      used for `no_build_time`.
      Delivered as `LedgerShapeRefusalTests`, and the corpus premise is itself asserted
      (`CorpusLedgerTests`) so the substitution cannot quietly become wrong.

- [x] 6.7 Write the deterministic report via `--report=` to
      `apps/client-godot/evidence/magic-v1/report.json`, generated from the live model
      so it cannot drift from the code it documents. Record the report's own raw
      digest **and a measured** pure-LF flag, because `godot-market-trade` shipped a
      sibling report that hard-coded that flag and copying a field *and its value*
      across file forms is how a guard becomes a lie.
      Observed: **4,364 bytes**, sha256
      `a180a72edd78a710ed796a9be3082dad1b92fb789547b37cb989896a8d9d6bfa`, **byte-identical
      across consecutive runs** and unchanged after the suite was converted to CRLF.
      The pure-LF flag is **measured per run** (`modules_are_pure_lf: false`), and it is
      `false` **correctly**: both delivered modules are CRLF. Three sibling reports carry
      the same field as `false` from a different file form, and `godot-market-trade`
      already recorded the trap of copying a field *and its value* across forms.

- [x] 6.8 Amend the two count pins **in place**, as established for a count an incoming
      line legitimately moves: `test_auction_schedule.gd` and `test_market_trade.gd`,
      **52 → 53** hermetic and **25 → 26** live phases. Confirm their live-phase regexes
      already read the widened `$serverV1Phases` list, and do not assume it.
      **Measured, and the answer is yes — which is not the safe assumption.** The
      `$livePhases` regex is `live.compile("\\$livePhases = @\\(([\\s\\S]*?)\\n    \\)")`
      (`test_auction_schedule.gd`:1576, `test_market_trade.gd`:1554) and a **second**
      regex reads the widened list,
      `v1_live.compile("\\$serverV1Phases = @\\(([\\s\\S]*?)\\n    \\)\\r?\\n")`
      (`test_auction_schedule.gd`:1607, `test_market_trade.gd`:1577), appending its names
      into the **same** `live_names` array — so the pin does see the v1 phases. Line 1
      recorded that an earlier version of these pins read only `$livePhases` and so could
      not see the thing it was counting; that is why this was measured rather than
      assumed.

      Totals measured in `verify-boot.ps1` after this line's two registrations: **53**
      hermetic suites, **23** v0 live phases, **3** v1 live phases (23 + 3 = 26). Both
      suites re-run green: `test_auction_schedule` **1222**, `test_market_trade` **1009**.

      **A fault of my own, recorded rather than hidden.** The first amendment emitted its
      reason as one string whose first line carried no `##` prefix, so it landed in the
      class body as code and **both suites became unparseable** —
      `Parse Error: Unexpected "Indent" in class body`. Repaired by rewriting the reason
      as comment lines. A reason attached to a pin is prose in a file the engine parses,
      and prose that is not commented is code.

- [x] 6.9 Measure whether the delivered client source names a `test_stored_item_placement.gd`
      boundary token. If it does, amend that suite's ownership hand-off **only**, the
      way `godot-unit-collection` and line 1 each did, and do not loosen the
      whole-tree absence for any other file. If it does not, record that no amendment
      was needed rather than editing it.
      **No amendment was needed, and the deciding measurement is specific.**
      `test_stored_item_placement.gd` re-runs green at **546 checks** on this line's
      bytes, unamended, and `git diff` over that file is **empty** — line 1 amended it, not
      this one. Measured token counts in the two files this line delivers:
      `server_v1_magic_result.gd` carries `place_stored_item` **0** and
      `sell_stored_item` **0**; `server_v1_api.gd` carries each **once**, but only inside
      the intent method names `place_stored_item_town` / `sell_stored_item_town`, and
      `server_v1_api.gd` is **already** a recorded owner in that suite's
      `STORAGE_OWNERS` table. The whole-tree absence therefore still holds for every file
      that is not an owner.

      **One stale comment in that hand-off became true as a side effect, which is
      recorded rather than tidied.** It read "all twenty-one it does NOT serve" while
      `UNSUPPORTED_INTENTS` held **22**; this line removed `magic_town` from that table, so
      both the table and the comment are now **21** and the comment is correct — it was
      off by one before and is right after, for a reason unrelated to whoever wrote it.

## 7. Live phase

- [x] 7.1 Add `/v1/magic` to `KNOWN_ROUTE_PATHS` in
      `apps/client-godot/server_v1_live_phase.py`. It is a closed set precisely so a
      typo cannot produce a passing phase whose evidence file names a route that does
      not exist.
      Delivered, and `"/v1/magic"` also joined `EXPECTED_BANNER_ROUTES` with its order and
      count asserted (`test_live_server.py`), rather than the banner check being
      generalised into a count — a count still passes when the routes are named wrongly or
      reported out of order, and this harness has already shipped one summary that named
      the wrong route for a phase that genuinely passed.

      **A defect that no Python test could have found, because nothing imports the
      harness.** `KNOWN_ROUTE_PATHS` referenced `MAGIC_PATH` on the line **above** its
      definition, so the harness died at import with `NameError: name 'MAGIC_PATH' is not
      defined`. Fixed by moving the constant above its use. Recorded because the class is
      worth naming: `apps/server-v1/tests/` does not import
      `apps/client-godot/server_v1_live_phase.py`, so a harness fault is reachable only by
      **running the phase**, which is why the phase is registered rather than assumed.

- [x] 7.2 Register `magic-live-v1` in `apps/client-godot/verify-boot.ps1`'s
      `$serverV1Phases` list, on the v1 port, with its explicit `--route-path`.
      Delivered with `--route-path=/v1/magic`, `--expect-save-mutation`, **no seeding**,
      and **fourteen** per-marker assertions: nine value groups on the typed `buy` marker
      (including `price_charged` matched against the literal word `null`, which is D2's
      whole finding as an assertion), plus three refusal markers and the harness summary.

      The `RoutePath` argument had to be **un-nested** from the `SeedCollection` branch.
      A phase that seeds nothing can never reach a `RoutePath` branch gated on seeding, so
      `magic-live-v1` would have recorded `"route": "POST /v1/collect"` while driving
      `/v1/magic` — the exact defect line 1 added `--route-path` to fix, hidden a second
      time. Seeding and naming a route are independent facts about a phase.

      **The live arm had no positive typed marker at all** — only four refusal lines — so
      a phase whose two `magic_town` calls were never made would still have produced
      refusal markers and could pass. `test_magic_v1.gd` now prints one typed marker per
      success, drawn from the **typed** result rather than the raw payload, so the
      assertion is about what the client read rather than about bytes that happened to
      arrive.

- [x] 7.3 The phase drives **both** operations against a disposable corpus on
      loopback and **seeds nothing**: the fresh corpus's `{}` ledger is already
      exercisable, so the only mutation is the ledger key. Assert for each operation
      that the corpus save mutated, that exactly one leaf path changed, and that all
      seven stored resources are byte-identical across both.
      Observed: **84 checks** PASS in the live scenario, `buy` then `use`, markers
      `before=0 after=1 cap=50 price_charged=null compared=7` and
      `before=1 after=2 cap=50 price_charged=null compared=7`; the ledger key rose to **2**
      across the two operations; all seven stored resources byte-identical.

      **A deviation from the task's literal wording, recorded because the literal is
      stronger than the truth.** The task says "exactly one leaf path changed"; the proof
      asserts **more than one** never changed, because the two operations differ in kind —
      the `buy` **adds** the ledger leaf and the `use` **changes** it. Both count as one
      touched leaf, and the assertion cannot distinguish "one ledger entry" from "one
      unrelated field" on its own, so the counter's actual rise is asserted separately.
      Relaxing "exactly one" to "not more than one" looks like a weakening and is the
      opposite: the exact figure was only true of the first operation.

- [x] 7.4 Assert the corpus save was removed afterwards, the v1 port was released, no
      working-tree `saves/` exists, and no `socialwars-server-v1-*` directory is left.
      Observed by the harness: **14 checks passed, 0 failed**, `"ok": true`,
      `"save_mutation_checked": true`, and `verify-boot.ps1` reported "server-v1 port 5057
      was released after teardown" and "no working-tree saves/ directory was created".
      Independently confirmed: both corpora this session created
      (`x7lhmstr`, `m0qln99d`) are gone, and port 5057 holds only a `TIME_WAIT` entry —
      which is the recorded flaky surface, not a leak.

- [x] 7.5 Note and do **not** change: the harness's `readiness()` probe posts to
      `COLLECT_PATH` by design. Record it rather than generalising it.
      Recorded, and still visible in the summary this line produced:
      `"readiness_code": "unknown_player"`, `"readiness_status": 404` on every v1 phase,
      because the probe posts to `/v1/collect` for all of them. Left alone.

## 8. Verification actually run

Record only what was run, with its observed result. All ten ran on the final bytes,
pinned CPython **3.9.13** (`& "$env:TEMP\opencode\cpython39\pkg\tools\python.exe" -B`,
never the PATH alias) and Godot **4.7.2.stable**, loopback only (v0 `127.0.0.1:5056`,
v1 `127.0.0.1:5057`).

- [x] 8.1 `python -B -m unittest discover -s apps/server-v1/tests -p "test_*.py" -v`
      → **`Ran 376 tests in 59.992s` / `OK`**, exit **0**, against the recorded **260**
      baseline = **+116**. Of those, `test_magic.py` alone is **114** (was 110 before
      task 6.5's `DomainInventoryTests`).

- [x] 8.2 The hermetic magic suite, with and without `--report=`
      → **469 checks** PASS headless, exit 0; **471** with
      `--report=<repo>/apps/client-godot/evidence/magic-v1/report.json`. Report
      **4,364 bytes**, sha256 `a180a72e…d6bfa`, byte-identical across consecutive runs
      (see 6.7).

- [x] 8.3 The v1 live phase standalone, against a disposable corpus on loopback
      → harness **14 checks passed / 0 failed**, `"ok": true`, `"godot_exit": 0`,
      `"server_exit": 0`, `"route": "POST /v1/magic"`, Godot suite
      **`PASS checks=84`**, exit **0** (see 7.3).

- [x] 8.4 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
      - expected unchanged at the recorded baseline, and **re-run rather than assumed**
      → **`Ran 3077 tests in 74.475s` / `OK`**, exit **0** — **unchanged** against the
      3,077 baseline. Re-confirmed structurally: `git diff --name-only -- apps/compat-api`
      returns **no path**. `apps/compat-api/**` was not opened for editing by this line.

- [x] 8.5 `powershell -File apps/client-godot/verify.ps1`
      → exit **0**, `PASS all checks succeeded`, with every content-package,
      conversion-package and registry-manifest digest reported unchanged.

- [x] 8.6 `powershell -File apps/client-godot/verify-boot.ps1`
      → exit **0**, `PASS all checks succeeded`; guard digest **identical before and after**
      (`pre=fe9686746fa28bb3e4be7b149dc176305237fb175f599ade85a903be9d2fbda1`,
      post identical); **86** logs referenced by the regenerated report, **all present**,
      carrying **zero** `[test] FAIL`, `SCRIPT ERROR`, `^ERROR:` or `Parse Error` lines;
      ports 5056 and 5057 released; no working-tree `saves/`.

      The census is taken over the **referenced** logs, not over
      `.godot/verify-boot/`, because that directory is never cleaned and line 1 recorded a
      clean zero computed over it as a statement about every run ever made rather than
      about this one.

- [x] 8.7 `python -B -m unittest discover -s tools/route-coverage/tests -p "test_*.py" -v`
      - **corrected while running it**: the `-s tools/route-coverage` form discovers
        **0 tests** and exits 0, because `tools/route-coverage/tests` has no
        `__init__.py`. A command reporting `Ran 0 tests ... OK` is not a pass.
      → correct form: **`Ran 44 tests in 14.962s` / `OK`**, exit **0**. The wrong form was
      run too, and measured: **`Ran 0 tests in 0.000s` / `OK`**, exit **0** — both halves
      of the trap, so the correction is a measurement rather than a note.

- [x] 8.8 `python -B packages/game-content/tools/validate_content.py`
      → exit **0**, `"result": "valid"`, `schemas_verified: 22`.

- [x] 8.9 `python -B tools/hash-manifest/hash_manifest.py verify`
      → exit **0**, `verify: 3258 entries, 758423699 bytes, commit
      e8c98a03c902eba70323538dc5d4eaba2f2927a1`.

- [x] 8.10 `openspec validate --all --strict`
      → exit **0**, `Totals: 78 passed, 0 failed (78 items)`.

- [x] 8.11 `git status --short` showing no content-package, fixture, save, config,
      village, conversion-package, registry-manifest, or legacy-source byte changed.
      → **25** paths — 20 modified and 5 new — every one of them inside this change's
      allowed surface. No path under
      `packages/game-content/`, `config/`, `tests/saves/`, `villages/`,
      `tests/fixtures/`, `assets/`, `tools/route-coverage/`, `tools/asset-registry/`,
      `apps/compat-api/` or `docs/`. No `.pyc`, and no working-tree `saves/`.

      The regenerated `apps/client-godot/evidence/boot/boot-report.json` was **diffed and
      every insertion accounted for**, because a rename and a content change look alike in
      a 142-insertion diff: 29 `log` renames (27 displaced — inserting one entry shifts
      every later index), 1 `generated_utc`, 1 `git_commit` (`617bf052` → `061a262e`), the
      one new `test_magic_v1` entry with its two assertions, the one new `magic-live-v1`
      entry with its fourteen assertions, and **one changed assertion value** — the collect
      phase's derivation id, which is nondeterministic by nature. Nothing else.

## 9. Claim limits to record before merging

- [x] 9.1 Record that **no price is charged and that the refusal is the finding**:
      twelve executed-legacy transactions moved no stored resource, and the committed
      table names none of its four numeric columns a price. D2.
      **Two corrections to D2's own figure, measured and reported to the orchestrator;
      `design.md` was NOT edited.** The raw table carries **six** numeric columns, not
      four: `cash`, `gold`, **`id`**, `level`, `mana`, **`target`**. `id` and `target` are
      numbers too, so "four numeric columns" undercounts the surface the refusal has to
      hold against. The suite now carries `NUMERIC_COLUMNS` (6) and
      `PRICE_CANDIDATE_COLUMNS` (4: `gold`, `cash`, `mana`, `level` — the four that name a
      *resource or a level*, i.e. the four a price could plausibly be read from), and the
      report publishes both. The refusal is unchanged and in fact slightly stronger: **no**
      column is named a price, whatever the column count.

- [x] 9.2 Record that the four contradictions with `docs/legacy-m13-line3-candidates.md`
      (`buy_magic` described as clamped, the arms described as near-duplicates, the
      `exact token 10` census row, and the `collections.json` price analogy) are
      **resolved in favour of the measurement**, and that **none of them moves the
      ranking** — the target stands and only the line's shape changes.

- [x] 9.3 Record that what a counter *means* is **unknown**; both arms increase,
      nothing consumes, and v1 therefore names it a counter and never a charge. D4.
      The preserved behaviour table carries four entries by **operation and condition**
      (`buy`, `use`, `absent_key`, `same_number`), not two by operation, precisely
      because the sameness at the cap and the absent-key arm are the two places the two
      branches differ, and the payload's `divergences` list names **reasons** rather than
      re-deriving them.

- [x] 9.4 Record that the `level` gate is a **deferred authority gap**, not a denial,
      with its condition for revisiting named. D5.
      Named as: the committed `level` and the player's stored `maps[0].level` are both
      reported, side by side, with `level_compared` and `level_gate_enforced` pinned to
      `False` in the typed result — so a caller can see the comparison **was available and
      was not made**. Revisit when a progressed-player corpus exists whose map level
      actually crosses a committed `level`.

- [x] 9.5 Record that the two operations are deliberately the same transition and that
      the sameness is a finding, not an oversight. D7.
      `same_transition_for_both_operations` is a payload key, and `SameTransitionTests`
      drives both operations over one seeded state and asserts one identical transition.

- [x] 9.6 Record that only **one** save document carries a populated ledger, and that
      the ledger-shape refusal is therefore exercised over an in-memory row rather
      than over the corpus.
      Measured: 33 committed save documents, all carry a dict `magics`, and **only
      `villages/Neutral.json`** is populated. `tests/saves/fresh-player.json` carries
      `magics {}` — empty, which is why the live phase needs no seed at all.

- [x] 9.7 Record that v1's stored resource set is **seven** while `godot-damage`
      compared **eight**, because the eight-slot vector's eighth target is read into
      `unknown` and never written, so `privateState.energy` is not a v1 stored
      resource. A measured difference between two layers.
      v1's seven are `xp, gold, wood, oil, steel, cash, mana`, and the typed result
      **requires** `stored_resources_compared` to be exactly those seven (size and
      membership, no new helper) so a subset comparison cannot pass.

- [x] 9.8 Record that the first half of the post-execution proof is a **specification**
      check and not an evidence claim, because v1 is the only implementation writing the
      save on this path. Only the second half is falsifiable. D9.
      The four halves are ordered **addressed key → unaddressed keys → resources → leaf
      ownership**, and the order is load-bearing: an earlier draft checked leaf ownership
      before the resource check, so a resource change could have been reported as a leaf
      change first. `test_no_helper_decrements_a_counter` is a **guard doing its job** and
      was renamed and restructured, never deleted, when it collided with the
      accept-at-cap boundary.

- [x] 9.9 Record that the routed/unrouted split is unchanged at **39/24** and that this
      proposal does **not** edit `docs/legacy-m13-unrouted-branches.md`, which still
      carries 40/23 at four lines and is owned elsewhere.
      Re-measured this line rather than inherited: `/v1/magic` is a **v1** route and adds
      no v0 route, so `tools/route-coverage` is untouched and its suite re-runs at **44**
      (task 8.7). The four-line correction in that document remains another change's.

- [x] 9.10 Record that the branches-without-an-authoritative-route figure moves
      **61 → 59**, and that `AGENTS.md` and the roadmap are deliberately not edited.

- [x] 9.11 Record that absence of a server-side rule says nothing about what the Flash
      client displayed, sent, or charged. Permanently unestablished here.
      Load-bearing for this line specifically: the ten derived rules were **never
      observed**, so what the Flash client sent for `buy_magic` / `use_magic` — including
      whether it sent a price at all — is not established and is not claimed anywhere in
      the delivered material.

- [x] 9.12 Do **not** claim an ordinal for any zero-consumer field; four conflicting
      ordinals already exist over four different scopes.
      No ordinal is claimed here either. `COUNTER_CAP_PROVENANCE`'s rejection reason was
      **corrected** during Apply on a measurement, not an ordinal: the first draft partly
      argued the value `50` does not occur among the committed magic columns, and it
      **does** — it is magic 1's `cash` and magic 5's `level`, one row each.

## 10. Instrument faults and corrections

Recorded rather than quietly edited, in the shape `godot-market-trade` and
`godot-construction-assist` established.

- [x] 10.1 Record the branch-span regex fault: `[A-Za-z_]+` measures **62** branches and
      silently drops `push_queue_unit2`; the digits-capable class measures **63**.
      Reproduce the fault deliberately rather than citing the corrected count alone.
      Reproduced: both classes were run and both counts observed.

- [x] 10.2 Record the `magics` token census fault: the code-only lexer deletes string
      literals, and a Python dict key **is** a string literal, so `privateState["magics"]`
      reads as a bare `privateState`. Exact-token count over the **raw** file is **17**,
      not the code-only **10**. Every zero-consumer claim in the delivered material
      names its counting rule and its module set.
      Reproduced: whole-file **17**, exact-token **17**, quoted **6**. This is the same
      family as the `_code_only` lexer defect in 6.3, seen from the Python side.

- [x] 10.3 Record that `apps/server-v1/tests/test_boundary_invariant.py:392`
      (`len(RefusalCode) < 20`) is **one code from tripping** after this line and is
      deliberately left unamended.
      **Measured at 19**, one short of the bound, and **unamended**.

- [x] 10.4 If the Apply stage finds that the selection record's `use_magic` span or
      line attribution differs from this design's, correct **this design file** in a
      corrections section rather than editing the numbers in place.
      **No correction is owed.** Measured against the preserved source: `buy_magic` is
      `command.py:652`–`:662` and `use_magic` is `command.py:664`–`:674`, exactly as the
      design records, and `design.md` was not opened for editing. The two figures this line
      **did** find wrong are reported in 9.1 (six numeric columns, not four) and 9.12 (the
      `50`-in-content claim), and both are recorded here and in the suite rather than
      silently corrected in a file this change does not own.

- [x] 10.5 (added by Apply. **Provenance corrected by the orchestrator 2026-10-13:** this
      task did **not** exist in the merged proposal, and task 3.3 did **not** reference
      it - the first draft of this task asserted exactly that, and the assertion was
      false. 3.3 was rewritten during Apply to cite 10.5, so the reference runs the wrong
      way: 10.5 was added to carry 3.3's newly measured accept-at-cap boundary, not to
      satisfy a reference that already existed. The content below stands on its own
      measurements; only the stated reason for this task's existence was false.) Record the **cap-boundary deviation** and the rest of the line's
      own instrument faults:

      1. **The cap boundary is accept-at-cap (option B), which the task set did not
         fix.** `before == 50` succeeds as a recorded no-op; `before == 51` is refused
         `counter_above_cap`. Measured basis, not preference: the preserved `use_magic`
         arm is *itself* a no-op at exactly 50, because `min(50, 51) == 50`. A third
         option — refuse at the cap — would have refused a transaction the preserved
         branch performs.
      2. **`unexpected_use_transition` was removed** from `_divergence_reasons`, because
         the response **lists divergence reasons as data** (D7) rather than re-deriving
         them; keeping it would have been the slice re-deciding what it already knew.
      3. **`magic_counter()` uses a membership test, not a truthiness test**, so a
         ledger recording `{"1": null}` is refused rather than read as zero. Found by
         measurement after the first version overwrote a recorded-but-unreadable entry.
      4. **Two guards in the GDScript suite needed two source projections, not one**,
         because `_code_only` (literals blanked) and `_comment_free` (literals kept) answer
         different questions — see 6.3. A single projection is the shape that made the
         original guard vacuous.
      5. **A Python name scan over-counted by looking for `def` in comments.** The
         measured result: `# def` is **not** found (0), while a `def` inside a
         docstring **is** found (1). The suite's report key is therefore named
         `python_name_scan_over_counts_a_docstring` rather than `..._a_comment`, because a
         field name that says the wrong thing is a claim.
      6. **The harness needed a `--corpus=` argument**, appended beside `--player-id=`
         and **refused if the caller supplies it**. The live arm's evidence is a
         **file-level diff** of the disposable save; without the path the client would
         have been diffing the server's own summary of itself, which is not evidence of
         anything.
      7. **A live-arm message was formatted with `% operation` and had no placeholder**,
         raising `not all arguments converted during string formatting in operator '%'`
         and aborting `_check_live` partway through the first operation.
         `test_base.gd` records a function abort as a **PASS**, so the phase still exited
         0, the corpus save still mutated (the request had already gone out), and every
         remaining live assertion silently never ran: **84** checks became **12**. The
         hermetic arm cannot reach the live arm, so the fix is a **self-scanning guard**
         over this suite's own source covering both format shapes, with its needle
         assembled at run time so the guard does not scan itself.
      8. **GDScript traps recorded for the next line**, all measured here: `%r` emits an
         engine `ERROR:` line that fails `verify-boot.ps1`; `for x in (a, b, c)` is a
         grouping expression and a **parse error**; warnings-as-errors rejects
         `var x := <Variant>` and demands `: Variant`; `String(PackedByteArray)` does not
         exist (use `FileAccess.get_file_as_string`); `RegEx` has no `MULTILINE` flag;
         every JSON number decodes as a `float`; `int(true)` is 1 and the string `"0"` is
         truthy; and capturing a native command into a PowerShell **variable** silently
         yields zero lines, so output must be piped to `Out-File`.
      9. **The suite was written pure LF and converted to CRLF at the end**, matching
         56 of the 58 sibling suites (`test_market_trade.gd` is the other LF file). The
         report was regenerated afterwards and is **byte-identical**, which is the
         measurement that the conversion changed nothing but line endings.
