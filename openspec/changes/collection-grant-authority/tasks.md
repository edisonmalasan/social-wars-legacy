# Tasks

## 1. Refusal vocabulary

- [ ] 1.1 Read `apps/server-v1/server_v1_refusals.py` and record the existing closed
      set of 12 codes and their status table before adding anything.
- [ ] 1.2 Extend **that module only** with the codes this line needs, each with its
      status: aliased id, unresolvable id, not eligible (with missing ids), already
      claimed, and insufficient cash. Design D8: the route may not grow its own answer.
- [ ] 1.3 Assert the vocabulary is closed: no route handler in `apps/server-v1/` names a
      refusal code that is absent from the table.

## 2. Domain service

- [ ] 2.1 Read the committed collections table through the content registry the way
      `collect` reads its income content. **Do not transcribe** any committed value into
      code; re-read it from `packages/game-content/normalized/collections.json` at run.
- [ ] 2.2 Implement committed-table lookup with the legacy `max(0, collection - 1)`
      positional index, returning the resolved id, whether the clamp moved it, and the
      aliased-from id. Design D2, D3.
- [ ] 2.3 Refuse an id that clamps to the first row (zero and every negative) and an id
      that resolves to nothing. Design D3.
- [ ] 2.4 Implement eligibility: the caller must hold **every** committed `item_ids`
      entry in `maps[0].store`. Report the missing committed ids on refusal. D4.
- [ ] 2.5 Implement the once-only check against `privateState.collections`, and the
      ledger append that makes it so. D6.
- [ ] 2.6 Implement the price derivation from committed `cashPrice` and the cash debit
      through the existing economy authority. D5.
- [ ] 2.7 Assert the module derives its table figures rather than hard-coding them:
      all 10 rows, 5 `item_ids` each, 50 distinct requirement ids across disjoint rows,
      and the 8 distinct `cashPrice` values.

## 3. Route

- [ ] 3.1 Implement `POST /v1/collection` accepting **only** `{user_id, collection_id}`.
      D1.
- [ ] 3.2 Refuse a request carrying any of: a resource delta, a prize, a quantity, a
      price, a held-item list, a requirement list, or an eligibility assertion. Refused
      as a structural input error, never clamped. D1.
- [ ] 3.3 Translate every domain refusal through the single status table. D8.
- [ ] 3.4 Add a live-phase registration for `collection-live` in
      `apps/client-godot/verify-boot.ps1`'s server-v1 phase list, alongside the existing
      `server-v1-live`.
- [ ] 3.5 Confirm no route was added, moved, or removed in `apps/compat-api/**`, and
      that no `command.py` route slice this line depends on changed. `tools/route-coverage`
      guards this and must not be edited.

## 4. Client surface

- [ ] 4.1 Register the `complete_collection` intent on the `ServerV1Api` facade in the
      exact shape of the existing forwarders, with its typed result module.
- [ ] 4.2 Add the typed result and its `_failure` factory, following the shape line 1
      established.
- [ ] 4.3 Do **not** widen `GameApi` a second time unless a declared return type
      genuinely differs; line 1 recorded the single widening it needed.

## 5. Hermetic suite

- [ ] 5.1 New `res://tests/test_collection_v1.gd`, re-deriving every committed-table
      figure from the committed package on each run rather than asserting a transcribed
      constant.
- [ ] 5.2 Cover each refusal independently: aliased id, unresolvable id, ineligible,
      already claimed, unaffordable, and a client-supplied delta.
- [ ] 5.3 Assert each refusal leaves storage, ledger, and all stored resources unchanged.
- [ ] 5.4 Assert the success proof is **non-tautological**: cash moves by exactly the
      derived `cashPrice` and every other stored resource by exactly zero, while the
      ledger gains exactly one id.
- [ ] 5.5 Add an anti-invention guard in the established shape: pin the domain module's
      whole static-function inventory, and refuse an invented helper by name and by
      substring. **Prove it by injection** - inject an invented eligibility or price
      helper, observe the failures, restore byte-identically, and record the measured
      failure counts.
- [ ] 5.6 Write the deterministic report via `--report=` to
      `apps/client-godot/evidence/collection-v1/report.json`, generated from the live
      model so it cannot drift from the code it documents.

## 6. Live phase

- [ ] 6.1 `collection-live` issues **two** completions against a disposable corpus on
      loopback: the first must be granted and mutate the save; the second, naming the
      same collection, must be refused and leave the save byte-identical.
- [ ] 6.2 Assert the corpus save mutated on the grant, was removed afterwards, port
      5057 was released, and no working-tree `saves/` exists.
- [ ] 6.3 Confirm `verify-boot.ps1`'s hermetic-suite and live-phase counts and its guard
      digest behave as the count-pin suites expect; amend the two pins in
      `test_auction_schedule.gd` and `test_market_trade.gd` **in place**, as established,
      since this line legitimately moves both counts.

## 7. Verification actually run

Record only what was run, with its observed result:

- [ ] 7.1 `python -B -m unittest discover -s apps/server-v1/tests -p "test_*.py" -v`
- [ ] 7.2 The hermetic collection suite, with and without `--report=`
- [ ] 7.3 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
      - expected unchanged at the recorded baseline, and re-run rather than assumed
- [ ] 7.4 `powershell -File apps/client-godot/verify.ps1`
- [ ] 7.5 `powershell -File apps/client-godot/verify-boot.ps1`
- [ ] 7.6 `python -B -m unittest discover -s tools/route-coverage -p "test_*.py" -v`
- [ ] 7.7 `python -B packages/game-content/tools/validate_content.py`
- [ ] 7.8 `python -B tools/hash-manifest/hash_manifest.py verify`
- [ ] 7.9 `openspec validate --all --strict`
- [ ] 7.10 `git status` showing no content-package, fixture, save, config, village,
      conversion-package, registry-manifest, or legacy-source byte changed.

## 8. Claim limits to record before merging

- [ ] 8.1 Record that eligibility (`item_ids`) and price (`cashPrice`) are **derived**,
      each with its rejected alternative, and that both are the two decisions to revisit
      if contrary evidence appears.
- [ ] 8.2 Record the three divergences from the preserved branch: the once-only
      refusal, the alias refusal, and the committed price debit. None is parity.
- [ ] 8.3 Record that the item ids in `item_ids` are neither confirmed committed units
      nor present in the fresh corpus, and that this does not affect the rule, which is
      membership in storage.
- [ ] 8.4 Record that absence of a server rule says nothing about what the Flash client
      displayed.
- [ ] 8.5 Do **not** claim an ordinal for either new zero-consumer-turned-consumer
      field; four conflicting ordinals already exist over four different scopes.