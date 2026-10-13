# Tasks

## 1. Refusal vocabulary

- [ ] 1.1 Read `apps/server-v1/server_v1_refusals.py` and record the existing closed
      set of **17** codes, the status table, the purpose table and the v0-equivalent
      table before adding anything.
- [ ] 1.2 Extend **that module only** with exactly **two** new codes and their statuses:
      `unknown_magic_id` (409) and `counter_above_cap` (409). Design D8.
- [ ] 1.3 Add a v0-equivalent entry for each new code, because
      `test_refusals.py` asserts `set(RefusalCode) == set(V0_EQUIVALENT_CODES)` in
      both directions.
- [ ] 1.4 **Confirm `tests/test_boundary_invariant.py:392` still passes unchanged.**
      It asserts `len(list(RefusalCode)) < 20`; the table holds 17 and this line
      adds two, making 19. Do **not** amend it. If a third code ever becomes
      unavoidable, record the amendment and its rationale rather than bumping it
      silently. Verify: `python -B -m unittest discover -s apps/server-v1/tests -p "test_refusals.py" -v`
- [ ] 1.5 Assert the vocabulary stays closed in both directions: every declared code is
      named by some application module and every status maps to exactly one code.

## 2. Content access

- [ ] 2.1 Read the committed magic table through the content registry the way
      `server_v1_collection.py` reads the committed collections table. **Do not
      transcribe** any committed value into code; re-read
      `packages/game-content/normalized/magics.json` at run. Design D3.
- [ ] 2.2 Implement committed-row lookup by the committed `id` column, reporting the
      resolved row, and refusing an identity no committed row carries.
- [ ] 2.3 Assert the module derives its table figures rather than hard-coding them:
      10 rows, ids `1..10` contiguous with no gaps, `legacy_id` the string form of
      `id` on every row, `kind == "magic"` on all ten, and the distinct-value counts
      for `gold` (10), `cash` (10), `mana` (6) and `level` (9).
- [ ] 2.4 Assert no delivered helper reads any committed numeric magic column to
      produce a value. This is a structural guard, not a comment (D2); verify it
      fires by injection in task 6.5.

## 3. Domain service

- [ ] 3.1 New `apps/server-v1/server_v1_magic.py`. Ledger read: obtain the addressed
      counter's recorded prior value, treating an absent entry as zero. Design D4.
- [ ] 3.2 Implement the bounded derivation against the **recorded literal cap**, with
      the rejected content-derivation alternative retained in the module docstring,
      as `godot-damage` established. Design D6.
- [ ] 3.3 Refuse a recorded counter already above the bound with `counter_above_cap`,
      reporting the recorded value and the bound rather than rewriting it. D6.
- [ ] 3.4 Implement both operations over the **same** derived transition, and report
      in the payload that they are the same transition. Design D7.
- [ ] 3.5 Report the committed row verbatim — `gold`, `cash`, `mana`, `level`,
      `target`, `area`, `name`, `kind` — with no value computed from any of them,
      and report the player's recorded `maps[0].level` beside the committed
      `level` without comparing them. Design D5.
- [ ] 3.6 Resolve **all** three refusals — `unknown_magic_id`, `counter_above_cap`,
      and `unreadable_state` for an absent or non-object ledger — **before** any
      ledger write. Design D8.
- [ ] 3.7 Assert no delivered helper decrements a counter, reads a ledger entry to
      answer ownership, compares a player level against a committed magic level, or
      computes a price, charge, mana cost, shortfall, multiplier, or effect amount.
      Three separate absences, three separate guards.

## 4. Intent layer

- [ ] 4.1 Add one `INTENT_SCHEMAS` row for the magic action with the closed key set
      `{player_id, magic_id, operation}`, and one `ADDRESSING_FIELDS` row with
      `magic_id` as the addressing field.
- [ ] 4.2 Add the declared closed operation-value set `{"buy", "use"}` as data, and
      refuse any other value as `malformed_request`. Do **not** add a branch to the
      transport. Design D1.
- [ ] 4.3 Do **not** add `magic_id` to `NON_NEGATIVE_ADDRESSING`. Unlike line 2's
      collection id there is **no** positional clamp to alias, because the preserved
      branches never index the committed table; zero and every negative simply name
      no committed row and are refused as `unknown_magic_id`. Design D3.
- [ ] 4.4 Assert the intent module names no refusal code outside its own import, and
      that a request carrying a delta key is refused as `client_supplied_delta`
      before the closed-key check runs.

## 5. Route

- [ ] 5.1 Add the route literal `MAGIC_PATH` to `apps/server-v1/server_v1_app.py` as a
      **literal**, not a concatenation — `test_app.TransportStructureTests` asserts the
      transport declares no arithmetic operator, and the concatenation form is the
      recorded first version of the first route. Design D2 of the boundary.
- [ ] 5.2 Register the route in the `ROUTES` declaration so `test_app.py`'s
      enumeration still agrees with the paths declared below.
- [ ] 5.3 Implement the handler in the shape of the two existing ones: hand the bytes
      to the intent module, call the domain, translate the returned outcome through
      `_envelope`. No arithmetic, no refusal vocabulary, no domain value construction.
- [ ] 5.4 Confirm no route was added, moved or removed in `apps/compat-api/**`, and
      that no `command.py` route slice this line depends on changed.
      `tools/route-coverage` guards this and must not be edited.

## 6. Client surface

- [ ] 6.1 Register the magic intent on the `ServerV1Api` facade in the exact shape of
      the existing forwarders, with its own typed result module and `_failure` factory.
- [ ] 6.2 Do **not** widen `GameApi` unless a declared return type genuinely differs;
      line 1 recorded the single widening it needed and line 2 added none.
- [ ] 6.3 New hermetic suite `res://tests/test_magic_v1.gd`, re-deriving every
      committed-table figure from the committed package on each run rather than
      asserting a transcribed constant.
- [ ] 6.4 Cover each refusal independently: unknown identity, non-canonical identity
      form, counter above the bound, client-supplied delta, unknown request field,
      operation outside the closed set, unknown player, unreadable ledger.
- [ ] 6.5 Add anti-invention guards in the established shape — pin the domain module's
      whole function inventory, and refuse an invented helper by name and by
      substring — and **prove them by injection**: inject an invented price helper, an
      invented level-gate helper, and an invented decrement helper; record the measured
      failure count of each; restore byte-identically and verify by digest. Design D2,
      D5, D4.
- [ ] 6.6 Assert the ledger-shape refusal over an **in-memory row**, because all 33
      committed save documents already carry a dict `magics` and the `version.py:32-37`
      coercion path is therefore unreachable through the corpus. Same pattern line 1
      used for `no_build_time`.
- [ ] 6.7 Write the deterministic report via `--report=` to
      `apps/client-godot/evidence/magic-v1/report.json`, generated from the live model
      so it cannot drift from the code it documents. Record the report's own raw
      digest **and a measured** pure-LF flag, because `godot-market-trade` shipped a
      sibling report that hard-coded that flag and copying a field *and its value*
      across file forms is how a guard becomes a lie.
- [ ] 6.8 Amend the two count pins **in place**, as established for a count an incoming
      line legitimately moves: `test_auction_schedule.gd` and `test_market_trade.gd`,
      **52 → 53** hermetic and **25 → 26** live phases. Confirm their live-phase regexes
      already read the widened `$serverV1Phases` list, and do not assume it.
- [ ] 6.9 Measure whether the delivered client source names a `test_stored_item_placement.gd`
      boundary token. If it does, amend that suite's ownership hand-off **only**, the
      way `godot-unit-collection` and line 1 each did, and do not loosen the
      whole-tree absence for any other file. If it does not, record that no amendment
      was needed rather than editing it.

## 7. Live phase

- [ ] 7.1 Add `/v1/magic` to `KNOWN_ROUTE_PATHS` in
      `apps/client-godot/server_v1_live_phase.py`. It is a closed set precisely so a
      typo cannot produce a passing phase whose evidence file names a route that does
      not exist.
- [ ] 7.2 Register `magic-live-v1` in `apps/client-godot/verify-boot.ps1`'s
      `$serverV1Phases` list, on the v1 port, with its explicit `--route-path`.
- [ ] 7.3 The phase drives **both** operations against a disposable corpus on
      loopback and **seeds nothing**: the fresh corpus's `{}` ledger is already
      exercisable, so the only mutation is the ledger key. Assert for each operation
      that the corpus save mutated, that exactly one leaf path changed, and that all
      seven stored resources are byte-identical across both.
- [ ] 7.4 Assert the corpus save was removed afterwards, the v1 port was released, no
      working-tree `saves/` exists, and no `socialwars-server-v1-*` directory is left.
- [ ] 7.5 Note and do **not** change: the harness's `readiness()` probe posts to
      `COLLECT_PATH` by design. Record it rather than generalising it.

## 8. Verification actually run

Record only what was run, with its observed result:

- [ ] 8.1 `python -B -m unittest discover -s apps/server-v1/tests -p "test_*.py" -v`
- [ ] 8.2 The hermetic magic suite, with and without `--report=`
- [ ] 8.3 The v1 live phase standalone, against a disposable corpus on loopback
- [ ] 8.4 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
      - expected unchanged at the recorded baseline, and **re-run rather than assumed**
- [ ] 8.5 `powershell -File apps/client-godot/verify.ps1`
- [ ] 8.6 `powershell -File apps/client-godot/verify-boot.ps1`
- [ ] 8.7 `python -B -m unittest discover -s tools/route-coverage/tests -p "test_*.py" -v`
      - **corrected while running it**: the `-s tools/route-coverage` form discovers
        **0 tests** and exits 0, because `tools/route-coverage/tests` has no
        `__init__.py`. A command reporting `Ran 0 tests ... OK` is not a pass.
- [ ] 8.8 `python -B packages/game-content/tools/validate_content.py`
- [ ] 8.9 `python -B tools/hash-manifest/hash_manifest.py verify`
- [ ] 8.10 `openspec validate --all --strict`
- [ ] 8.11 `git status --short` showing no content-package, fixture, save, config,
      village, conversion-package, registry-manifest, or legacy-source byte changed.

## 9. Claim limits to record before merging

- [ ] 9.1 Record that **no price is charged and that the refusal is the finding**:
      twelve executed-legacy transactions moved no stored resource, and the committed
      table names none of its four numeric columns a price. D2.
- [ ] 9.2 Record that the four contradictions with `docs/legacy-m13-line3-candidates.md`
      (`buy_magic` described as clamped, the arms described as near-duplicates, the
      `exact token 10` census row, and the `collections.json` price analogy) are
      **resolved in favour of the measurement**, and that **none of them moves the
      ranking** — the target stands and only the line's shape changes.
- [ ] 9.3 Record that what a counter *means* is **unknown**; both arms increase,
      nothing consumes, and v1 therefore names it a counter and never a charge. D4.
- [ ] 9.4 Record that the `level` gate is a **deferred authority gap**, not a denial,
      with its condition for revisiting named. D5.
- [ ] 9.5 Record that the two operations are deliberately the same transition and that
      the sameness is a finding, not an oversight. D7.
- [ ] 9.6 Record that only **one** save document carries a populated ledger, and that
      the ledger-shape refusal is therefore exercised over an in-memory row rather
      than over the corpus.
- [ ] 9.7 Record that v1's stored resource set is **seven** while `godot-damage`
      compared **eight**, because the eight-slot vector's eighth target is read into
      `unknown` and never written, so `privateState.energy` is not a v1 stored
      resource. A measured difference between two layers.
- [ ] 9.8 Record that the first half of the post-execution proof is a **specification**
      check and not an evidence claim, because v1 is the only implementation writing
      the save on this path. Only the second half is falsifiable. D9.
- [ ] 9.9 Record that the routed/unrouted split is unchanged at **39/24** and that this
      proposal does **not** edit `docs/legacy-m13-unrouted-branches.md`, which still
      carries 40/23 at four lines and is owned elsewhere.
- [ ] 9.10 Record that the branches-without-an-authoritative-route figure moves
      **61 → 59**, and that `AGENTS.md` and the roadmap are deliberately not edited.
- [ ] 9.11 Record that absence of a server-side rule says nothing about what the Flash
      client displayed, sent, or charged. Permanently unestablished here.
- [ ] 9.12 Do **not** claim an ordinal for any zero-consumer field; four conflicting
      ordinals already exist over four different scopes.

## 10. Instrument faults and corrections

Recorded rather than quietly edited, in the shape `godot-market-trade` and
`godot-construction-assist` established.

- [ ] 10.1 Record the branch-span regex fault: `[A-Za-z_]+` measures **62** branches and
      silently drops `push_queue_unit2`; the digits-capable class measures **63**.
      Reproduce the fault deliberately rather than citing the corrected count alone.
- [ ] 10.2 Record the `magics` token census fault: the code-only lexer deletes string
      literals, and a Python dict key **is** a string literal, so `privateState["magics"]`
      reads as a bare `privateState`. Exact-token count over the **raw** file is **17**,
      not the code-only **10**. Every zero-consumer claim in the delivered material
      names its counting rule and its module set.
- [ ] 10.3 Record that `apps/server-v1/tests/test_boundary_invariant.py:392`
      (`len(RefusalCode) < 20`) is **one code from tripping** after this line and is
      deliberately left unamended.
- [ ] 10.4 If the Apply stage finds that the selection record's `use_magic` span or
      line attribution differs from this design's, correct **this design file** in a
      corrections section rather than editing the numbers in place.
