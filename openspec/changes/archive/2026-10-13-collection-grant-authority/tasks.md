# Tasks

## 1. Refusal vocabulary

- [x] 1.1 Read `apps/server-v1/server_v1_refusals.py` and record the existing closed
      set of 12 codes and their status table before adding anything.
- [x] 1.2 Extend **that module only** with the codes this line needs, each with its
      status: aliased id, unresolvable id, not eligible (with missing ids), already
      claimed, and insufficient cash. Design D8: the route may not grow its own answer.
- [x] 1.3 Assert the vocabulary is closed: no route handler in `apps/server-v1/` names a
      refusal code that is absent from the table.

## 2. Domain service

- [x] 2.1 Read the committed collections table through the content registry the way
      `collect` reads its income content. **Do not transcribe** any committed value into
      code; re-read it from `packages/game-content/normalized/collections.json` at run.
- [x] 2.2 Implement committed-table lookup with the legacy `max(0, collection - 1)`
      positional index, returning the resolved id, whether the clamp moved it, and the
      aliased-from id. Design D2, D3.
- [x] 2.3 Refuse an id that clamps to the first row (zero and every negative) and an id
      that resolves to nothing. Design D3.
- [x] 2.4 Implement eligibility: the caller must hold **every** committed `item_ids`
      entry in `maps[0].store`. Report the missing committed ids on refusal. D4.
- [x] 2.5 Implement the once-only check against `privateState.collections`, and the
      ledger append that makes it so. D6.
- [x] 2.6 Implement the price derivation from committed `cashPrice` and the cash debit
      through the existing economy authority. D5.
- [x] 2.7 Assert the module derives its table figures rather than hard-coding them:
      all 10 rows, 5 `item_ids` each, 50 distinct requirement ids across disjoint rows,
      and the 8 distinct `cashPrice` values.

## 3. Route

- [x] 3.1 Implement `POST /v1/collection` accepting **only** `{user_id, collection_id}`.
      D1.
- [x] 3.2 Refuse a request carrying any of: a resource delta, a prize, a quantity, a
      price, a held-item list, a requirement list, or an eligibility assertion. Refused
      as a structural input error, never clamped. D1.
- [x] 3.3 Translate every domain refusal through the single status table. D8.
- [x] 3.4 Add a live-phase registration for `collection-live` in
      `apps/client-godot/verify-boot.ps1`'s server-v1 phase list, alongside the existing
      `server-v1-live`.
- [x] 3.5 Confirm no route was added, moved, or removed in `apps/compat-api/**`, and
      that no `command.py` route slice this line depends on changed. `tools/route-coverage`
      guards this and must not be edited.

## 4. Client surface

- [x] 4.1 Register the `complete_collection` intent on the `ServerV1Api` facade in the
      exact shape of the existing forwarders, with its typed result module.
- [x] 4.2 Add the typed result and its `_failure` factory, following the shape line 1
      established.
- [x] 4.3 Do **not** widen `GameApi` a second time unless a declared return type
      genuinely differs; line 1 recorded the single widening it needed.

## 5. Hermetic suite

- [x] 5.1 New `res://tests/test_collection_v1.gd`, re-deriving every committed-table
      figure from the committed package on each run rather than asserting a transcribed
      constant.
- [x] 5.2 Cover each refusal independently: aliased id, unresolvable id, ineligible,
      already claimed, unaffordable, and a client-supplied delta.
- [x] 5.3 Assert each refusal leaves storage, ledger, and all stored resources unchanged.
- [x] 5.4 Assert the success proof is **non-tautological**: cash moves by exactly the
      derived `cashPrice` and every other stored resource by exactly zero, while the
      ledger gains exactly one id.
- [x] 5.5 Add an anti-invention guard in the established shape: pin the domain module's
      whole static-function inventory, and refuse an invented helper by name and by
      substring. **Prove it by injection** - inject an invented eligibility or price
      helper, observe the failures, restore byte-identically, and record the measured
      failure counts.
- [x] 5.6 Write the deterministic report via `--report=` to
      `apps/client-godot/evidence/collection-v1/report.json`, generated from the live
      model so it cannot drift from the code it documents.

## 6. Live phase

- [x] 6.1 `collection-live` issues **two** completions against a disposable corpus on
      loopback: the first must be granted and mutate the save; the second, naming the
      same collection, must be refused and leave the save byte-identical.
- [x] 6.2 Assert the corpus save mutated on the grant, was removed afterwards, port
      5057 was released, and no working-tree `saves/` exists.
- [x] 6.3 Confirm `verify-boot.ps1`'s hermetic-suite and live-phase counts and its guard
      digest behave as the count-pin suites expect; amend the two pins in
      `test_auction_schedule.gd` and `test_market_trade.gd` **in place**, as established,
      since this line legitimately moves both counts.

## 7. Verification actually run

Record only what was run, with its observed result:

- [x] 7.1 `python -B -m unittest discover -s apps/server-v1/tests -p "test_*.py" -v`
- [x] 7.2 The hermetic collection suite, with and without `--report=`
- [x] 7.3 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
      - expected unchanged at the recorded baseline, and re-run rather than assumed
- [x] 7.4 `powershell -File apps/client-godot/verify.ps1`
- [x] 7.5 `powershell -File apps/client-godot/verify-boot.ps1`
- [x] 7.6 `python -B -m unittest discover -s tools/route-coverage/tests -p "test_*.py" -v`
      - **corrected while running it**: the `-s tools/route-coverage` form written in the
        proposal discovers **0 tests** and exits 0, because `tools/route-coverage/tests`
        has no `__init__.py` and unittest 3.9 discovery does not recurse into a
        non-package directory. A command that reports `Ran 0 tests ... OK` is not a pass;
        the corrected form runs **44 tests**. The tool itself was not edited.
- [x] 7.7 `python -B packages/game-content/tools/validate_content.py`
- [x] 7.8 `python -B tools/hash-manifest/hash_manifest.py verify`
- [x] 7.9 `openspec validate --all --strict`
- [x] 7.10 `git status` showing no content-package, fixture, save, config, village,
      conversion-package, registry-manifest, or legacy-source byte changed.

## 8. Claim limits to record before merging

- [x] 8.1 Record that eligibility (`item_ids`) and price (`cashPrice`) are **derived**,
      each with its rejected alternative, and that both are the two decisions to revisit
      if contrary evidence appears.
- [x] 8.2 Record the three divergences from the preserved branch: the once-only
      refusal, the alias refusal, and the committed price debit. None is parity.
- [x] 8.3 Record that the item ids in `item_ids` are neither confirmed committed units
      nor present in the fresh corpus, and that this does not affect the rule, which is
      membership in storage.
- [x] 8.4 Record that absence of a server rule says nothing about what the Flash client
      displayed.
- [x] 8.5 Do **not** claim an ordinal for either new zero-consumer-turned-consumer
      field; four conflicting ordinals already exist over four different scopes.

## Apply-stage corrections and measured results

Recorded rather than quietly edited, in the shape `godot-market-trade` and
`godot-construction-assist` established.

### A live-phase evidence file named the wrong route, and nothing failed

`server_v1_live_phase.py` wrote `"route": "POST %s" % COLLECT_PATH` into
**every** phase summary, so `collection-live-v1` recorded `POST /v1/collect`
while it had just driven `POST /v1/collection`. Two things made this worse
rather than better:

* the phase genuinely passed -- the grant, the `collection_already_claimed`
  refusal, and the corpus mutation were all real; and
* `verify-boot.ps1` asserted `$v1Summary.route -eq "POST /v1/collect"` for
  **every** v1 phase, so the battery **agreed with the bug**.

The route under test is chosen by the Godot suite the caller passes, not by the
harness, so the harness cannot derive it. It is now an explicit
`--route-path` argument defaulting to the collect path, restricted to the
closed set `KNOWN_ROUTE_PATHS`, and `verify-boot.ps1` derives its expectation
from the phase table's new `RoutePath` key. Measured: the collect phase still
reports `POST /v1/collect` (14 checks) and the collection phase reports
`POST /v1/collection` (15 checks); an unknown `--route-path` is refused with a
named message and exit 1.

### The marker `Test` values are regular expressions

The generalised per-phase marker loop first compared with PowerShell's literal
`-eq`/`-ne`. `verify-boot.ps1` then failed on **exactly** the four groups whose
`Test` is a pattern -- `'"wood":\d+'`, `'^[0-9a-f]{32}$'`, `'"cash":-\d+'`,
`'.*\b7\b.*'` -- and passed the seven whose `Test` is a bare number. The
operator is now `-match`/`-notmatch`, with an unknown `Op` failing loudly. The
semantics were confirmed against **11 positives and 6 negative controls**
before the battery was re-run, rather than discovered by a 30-minute round
trip.

### A claim in the evidence report was prose wearing a guard's clothes

`client_compares_two_reported_grant_fields: false` named
`_check_observed_success_parses` as its enforcement, which is a description, not
a check. Probe P4 (`if source["position"] != source["requested_id"]`) produced
**no failure at all** until `_check_no_field_reconciliation` existed. The new
guard failed on nothing when it first used `_code_only`, because that scanner
deletes string literals -- which is where a GDScript field name lives. A
separate `_comments_only` scanner was added, and the claim's `enforced_by`
entry now names the real guard and records why it was added by a probe.

A second claim was transcribed rather than measured: the report's
`facade_return_type` was the literal `"Variant"`. Probe P7 falsified the
*guard* correctly but showed the report field was not reading it, so the report
now calls `_return_type_of`.

### Nine injection probes, all detected, measured

Failures measured: **1, 1, 2, 2, 3, 3, 1, 2, 1** (16 total), every probe exit
1, every restore verified byte-identical by digest against
`94bebcd0...` (`server_v1_api.gd`), `63d1ac4f...`
(`server_v1_collection_result.gd`) and `fa8e6470...` (`game_api.gd`). P1
borrowed **no** reserved stem and fired only the inventory gate (1 failure);
P1b borrowed `collection_price` and fired the belt as well (3) -- the
`godot-market-trade` probe-2-versus-probe-8 pair reproduced. The harness gained
a **no-op-mutation abort** after P7's `str.replace` silently matched nothing and
scored zero failures for the wrong reason.

The evidence report records both delivered modules' raw digests **and a
measured** `pure_lf` flag per module, because `server_v1_api.gd` is CRLF in this
checkout and the new module is LF. `godot-market-trade` shipped a sibling
report that hard-coded that flag to `false`; copying a field *and its value*
across file forms is how a guard becomes a lie.

### Verification actually run, at the final committed state

| Command | Observed |
| --- | --- |
| `unittest discover -s apps/server-v1/tests` | `Ran 260 tests ... OK`, exit 0 (210 baseline, +50) |
| `unittest discover -s apps/compat-api/tests` | `Ran 3077 tests ... OK`, exit 0 -- **unchanged**, re-run not assumed; `git diff --name-only -- apps/compat-api` empty |
| `test_collection_v1.gd` | `PASS ... checks=403`, exit 0 (389 and 401 were intermediate, before the reconciliation guard and the report's digest block) |
| `test_collection_v1.gd -- --report=...` | 3,309 bytes, sha256 `faa3f6e81148e5167229579df4fcf09641044a5f126ca0cf9f3994676e3301ba`, byte-identical across runs |
| `unittest discover -s tools/route-coverage/tests` | `Ran 44 tests ... OK`, exit 0 |
| `validate_content.py` | exit 0, `result: valid` -- 23 outputs, 22 schemas, 604 references |
| `hash_manifest.py verify` | 3,258 entries, 758,423,699 bytes, commit `e8c98a0...`, exit 0 |
| `verify.ps1` | exit 0, `PASS all checks succeeded` (re-run at final state) |
| `verify-boot.ps1` | exit 0, `PASS all checks succeeded` -- 84 commands, 259 assertions, 52 hermetic suites, 25 live phases, guard digest `fe968674...` identical before and after |
| log census | 84 recorded logs present, **168 files** scanned (both `.out` and `.err`), **0** `SCRIPT ERROR` / `^ERROR:` / `[test] FAIL` lines |
| `openspec validate --all --strict` | 77 passed / 0 failed |
| `git status --short` | no content-package, fixture, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed; `tools/` untouched |

`boot-report.json`'s diff was **inspected, not assumed**: exactly two commands
added (`test_collection_v1`, `collection-live-v1`), 26 `log` renumberings,
`environment.git_commit` advanced, `generated_utc` changed; `service`,
`inputs`, `switch` and `claim_limits` byte-identical.

### Count pins

`test_auction_schedule.gd` and `test_market_trade.gd` amended **in place**,
51 -> **52** hermetic and 24 -> **25** live phases, as established for a count
an incoming line legitimately moves.
