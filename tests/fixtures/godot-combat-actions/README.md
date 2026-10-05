# Executed-legacy combat-actions fixture (`end_attack`, `kill`, `kill_iid`)

The executed-legacy parity oracle for the Compatibility API v0 `POST /v0/combat`
endpoint: thirteen real transactions against the real legacy Flask server
(`command.py:808-885` for `end_attack`, `command.py:169-181` for `kill`, and
`command.py:183-187` for `kill_iid`), captured from a disposable copy of the
repository (design D1/D5/D8 of the `combat-actions` OpenSpec change). No Flash,
Ruffle, ActionScript, or browser was involved, no external network was used, and
every request went to the legacy server on **127.0.0.1:5055**.

This is the **first executed-legacy fixture for combat**, and it exists because
the delivered capability refuses the one thing the preserved server does. The
manifest records that difference as a **divergence**, not as parity.

## What was captured

Thirteen transactions plus one recorded login, each against its own disposable
server, seeded from one of two committed village documents:

| # | step | command | crafted payload | status | rows removed | leaves changed |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `resolve_first_by_recorded_order` | `end_attack` | `units [[1020, 0, 1, 0]]` | 200 | `2425` | 8 |
| 2 | `resolve_absent_attacker_units` | `end_attack` | blob with no `attacker_units` | **500** | none | 0 |
| 3 | `resolve_empty_payload` | `end_attack` | `{}` | 200 | none | 0 |
| 4 | `resolve_absent_victim` | `end_attack` | `units [[1020, 0, 1, 0]]`, no `victim` | **500** | none | 0 |
| 5 | `resolve_batch_discarded_on_raise` | `end_attack` | two commands, second raises | **500** | none | 0 |
| 6 | `resolve_empty_attacker_units` | `end_attack` | `units []` | 200 | none | 0 |
| 7 | `client_dictated_count_two` | `end_attack` | `units [[1020, 0, 3, 1]]` | 200 | **`2425`, `1022`** | 15 |
| 8 | `resolve_no_eligible_row` | `end_attack` | `units [[923, 0, 1, 0]]` | 200 | none | 0 |
| 9 | `kill_unit_row` | `kill` | `[1639, 0]` | 200 | `1639` | 7 |
| 10 | `kill_missing_row` | `kill` | `[999999, 0]` | 200 | none | 0 |
| 11 | `kill_iid_no_op` | `kill_iid` | `[1076, 0]` | 200 | none | 0 |
| 12 | `ledger_increment_existing` | `end_attack` | `units [[1034, 0, 1, 0]]` | 200 | `37521` | 8 |
| 13 | `ledger_key_created` | `end_attack` | `units [[1023, 0, 1, 0]]` | 200 | `20239` | 8 |

The `pid` is read from `playerInfo.pid` **in the document**, never derived from a
filename stem: for three of the eight committed village saves the two disagree,
and for `initial.json` the pid is `null`, which `build_disposable` refuses.

### Why two seeds

`villages/AcidCaos.json` has an **empty** `deadHeroes` ledger, so the key-creation
branch and the first-eligible-row selection are both observable from nothing.
`villages/Neutral.json` holds **28** ledger keys, so the **increment** branch is
observable as `4 -> 5` while the key count stands still. One seed cannot show
both arms; recording both is what makes them distinguishable rather than
asserted.

## The order of record is NOT the snapshot order

This is the finding most likely to mislead a future replay, so it is stated
first and in its own section.

`map_lose_item` pops the first row it matches while walking the save's **own
insertion order** (`for index in map_items`, `engine.py:218-227`). It does not
sort. For item `1020` in the destruction seed:

| ordering | eligible keys, in order | first |
| --- | --- | --- |
| **committed village document** | `2425, 1022, 898, 3151, 3423, 897, 6627` | **`2425`** |
| `before.json` / `after.json` snapshot | `1022, 2425, 3151, 3423, 6627, 897, 898` | `1022` |
| numeric minimum | - | `897` |

The oracle removed **`2425`**, which measures the committed order end to end.

**`before.json` and `after.json` are NOT the order of record.** The fixture writer
sorts keys: `capture_legacy_fixtures.py:457 write_json -> json.dump(...,
sort_keys=True)`. The snapshots are therefore lexicographic, the first three
committed keys are `3, 4, 5` and the first three snapshot keys are `100, 102,
1022`, and `snapshot_order_differs_from_committed_order` is `true`.

**Consequence for a replay: rebuild the disposable corpus from the committed
village document, never from `before.json`.** Resetting from `before.json`
replays against the sorted order and removes `1022` instead of `2425` — and the
resulting document still compares equal **leaf for leaf**, because the harness's
`json_diff` walks keys rather than positions. The mis-ordering is therefore
invisible to the diff, which is why it is measured here instead of being assumed
harmless.

## The central divergence, measured

Step 7 is the transaction this capability exists to refuse.

The client sent `A = 3` and `B = 1`, so the oracle computed
`max(0, 3 - 1) == 2` and destroyed **two** rows (`2425` and `1022`), incrementing
the ledger twice. The delivered endpoint derives **`units: []`**, destroys
**exactly one** row, and increments **once**.

`parity_with_delivered_endpoint` is `true` for the other **twelve** transactions
and `false` for this one. Reproducing the subtraction would make the modern server
a pass-through for a client-computed casualty figure, which is the anti-pattern
`AGENTS.md` names as "Bad", so the count is refused **before dispatch** under its
own named guard, separately from the D1 eligibility check.

The count is not narrowed for either side. Narrowing the oracle's side would need
a combat rule the preserved source does not contain — the two subtracted numbers
are labelled only `A` and `B` and nothing establishes what they mean. Narrowing
this side would need a pre-write validation the legacy branch does not perform.

## The batch is the persistence boundary

Steps 2, 4, and 5 answer **HTTP 500**, and in all three the persisted document is
**byte-identical** to its before state. That is not a coincidence of the probe:

- an omitted `attacker_units` raises at `command.py:866`, **before** the write
  loop runs;
- an omitted `victim` raises at `command.py:874`, **after** `map_lose_item` has
  already run;
- yet a raise anywhere skips `save_session` entirely, because `command.py`
  dispatches the **whole batch** before saving (`command.py:30,32`).

So the failure mode is a **discarded** save, never a partially applied one. The
practical consequence for this capability is recorded as a requirement: a refused
combat request must leave the persisted document untouched, which is what the
endpoint's no-resource-moved and key-set proofs assert.

A third guard was found by measurement rather than by reading: an **empty** blob
short-circuits at `command.py:818`'s `if not response:` and answers **success**
with no change, so the key that raises against a non-empty blob is answered
successfully against an empty one. That is step 3.

## What the fixture establishes

The twelve facts the manifest marks `established`, in its own words:

1. The destruction count is `max(0, unit[2] - unit[3])` on two **client-supplied**
   numbers (`command.py:868`), labelled only `A` and `B`, with nothing establishing
   what they mean.
2. That count is applied **per popped row**: one request with `A=3, B=1`
   incremented the ledger twice and removed two rows.
3. The oracle's safety against over-deletion is **exhaustion of matches**, not a
   check: `engine.py:218-227` loops `while qty > 0` and returns the moment one
   pass finds no match.
4. A row is selected by item id (slot 0) **plus a truthy team** (slot 7) —
   `engine.py:221` — and popped in the save's own recorded map-key order.
5. The ledger increment is behind **exactly two** committed gates: player team 1
   (`engine.py:151`) and a committed `resurrectable` flag greater than zero
   (`engine.py:159,162`). An absent flag is a **refusal**, never a zero.
6. Both ledger arms are reachable and distinct: a count that moves while the key
   count does not (`4 -> 5`, 28 keys), and a key created at 1 (`28 -> 29` keys).
7. `kill` deletes a row **by map key**, and the branch contains **no** reference to
   `privateState['deadHeroes']` and no `push_dead_unit` call at all.
8. `kill_iid` contains **no write statement at all** — its entire body is one
   `print` — so nothing can move and no request can change that.
9. The two unguarded absent-value dereferences sit on **opposite sides** of the
   write loop, and the server answers HTTP 500 in both cases.
10. The persisted state is byte-identical anyway, because the **batch** is the
    persistence boundary.
11. An empty blob answers success with no change (`command.py:818`).
12. Under a **neutral** vector, every stored resource is byte-identical in all
    thirteen transactions, and the only leaves that ever move belong to a
    destroyed row or to the ledger.

## Determinism and rerun behavior

`request_captured_at_utc` is the **only** field that changes between reruns, and
it is recorded per step. Everything else — the transaction records, the before and
after states, the manifest — reproduces byte for byte, and `ts` is pinned to the
constant `1700000000` so it is not volatile. `resource_vector` is
`[0, 0, 0, 0, 0, 0, 0, 0]` in every transaction, **neutral by construction**.

Each transaction ran against **its own** disposable server, thirteen starts. That
is not an optimisation: `sessions.load_saves()` caches the corpus in a module
global at import, so a running server never re-reads the seed file. Restoring the
seed between probes on one server leaves the in-memory corpus already mutated.

## Containment

- 13 disposables, each removed by the harness's own `finally` block.
- The fixture is staged **outside** the working tree and published only after
  every check passed, so a failed run writes nothing into the repository.
- Containment digest `18e5e55b…a724` over the groups `config`, `mods`,
  `root_python`, `saves`, `templates`, `tests/saves`, `villages` is **identical
  before and after**, and both seed digests are unchanged.
- No working-tree `saves/` directory exists afterwards
  (`working_tree_saves_absent: true`).
- All 17 pre-existing protected fixtures are byte-unchanged.
- The service binds `127.0.0.1` only, and every request is loopback.

## Claim limits

- **No combat rule is resolved or claimed.** Damage, health, defence, hit chance,
  attack outcome, and life/interval arithmetic are absent. `attack`, `defense`,
  `life`, `attack_interval`, `attack_range`, `best_against`, `best_against_mult`,
  and `velocity` each measure **zero** legacy consumers, so the committed numbers
  are content and never rules.
- **No mission dispatch, resolution, completion, or reward.** Mission vocabulary
  stays owned by `godot-mission-vocabulary`.
- **No honour, reward, or resource movement.** `honor`, `resources`,
  `resources_victim`, and `townhall_gold` are read and discarded, and every
  transaction ran under a neutral vector and moved nothing.
- **No occupancy, bounds, type, or terrain validation.** `map_lose_item` tests
  only the item id and the team's truthiness, and this contract reproduces that
  absence rather than filling it.
- **The team asymmetry is recorded, not exercised and not refused** —
  `map_lose_item` accepts any truthy team while `push_dead_unit` requires team one
  — because every one of the 441 committed unit rows is on team one.
- **The modern endpoint does not reproduce the oracle's destruction count**, by
  design, and the manifest records the difference rather than reporting parity by
  omission.
- **Nothing is claimed about what the real Flash client sent.** The client was
  never executed; every payload here is crafted.
- **No partially applied save** exists anywhere in this fixture, because a raise
  anywhere in a batch skips `save_session`.
- Parity covers **thirteen** transactions against **two** village corpora. No
  progressed-player save is available, and `tests/saves/fresh-player.json` places
  **no unit row at all**, which is why the committed capture cannot also cover
  the live phase's `kill`-on-a-real-row path.

## Derived, not observed

Three items are recorded as derived rather than established, so a later line does
not inherit them as facts:

- that the **recorded map-key order**, rather than a sort, is the selection order
  (it rests on `for index in map_items` walking insertion order plus the committed
  corpus's out-of-order insertions, and on the oracle removing `2425` rather than
  `897`);
- the choice of `AcidCaos.json` and `Neutral.json` as the two disposable seeds;
- that the `reason` argument of `kill` and `kill_iid` has no stored effect, each
  branch using it only inside an f-string.

## How it was captured

```bash
python -B apps/compat-api/capture_combat_fixture.py
```

Interpreter: **CPython 3.9 (pinned)**. The child processes run
`python -B server.py` with `PYTHONUNBUFFERED=1` set **for this capture only**,
through a defaulted parameter on `start_server`; `child_environment()` is
untouched, so no existing capture's log changes. The printed branch lines are
evidence — the destruction counts are read from the server's own output.

`debug_note`: `server.py` runs `app.run(..., debug=False)`, so a failing request
answers the framework's plain error page with no traceback and no absolute path;
the capture asserts the body does not leak the disposable's filesystem layout.