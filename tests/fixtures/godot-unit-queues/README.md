# Executed-legacy production-queue fixture (`godot-unit-queues`)

The executed-legacy parity oracle for the Compatibility API v0 queue endpoint:
a real **`push_queue_unit`** followed by a real **`pop_queue_unit`** on the
committed corpus's **own real placed training producer**, both carrying a
**neutral** vector, captured from the real legacy Flask server (design D3 of the
`godot-unit-queues` OpenSpec change).  No Flash, browser, Ruffle, ActionScript,
or external network was involved - only the legacy server on loopback under the
pinned interpreter.

This is M8 line 3 of 8, and the first M8 line that can own a **real**
executed-legacy fixture **without fabricating any player state**: the committed
fresh-player save places **id 26, Command Center, at map key `1`**, with
`training_time` 5, `min_level` 1, `group_type` `COMMAND_CENTER`, and the row
`[26, 51, 41, 0, 0, [], {}, 1]` - an **empty** attribute bag.  Both queue
commands are therefore exercisable against the corpus exactly as committed.

Like the move and collect fixtures, it carries **one** time-dependent state
value: `push_queue_unit` stamps `attr["ts"]` with the wall clock
(`engine.py:189`).  That single stamp appears in the push step's `after.json`
and in the pop step's `before.json`.  The pop's `after.json` carries **no** stamp
at all, because the three-key teardown removed it again - so that after-state is
the **seed** byte-for-byte, which is the strongest round-trip statement this pair
can make.

## What is NOT in this fixture, stated up front

**A push and a pop were captured.  No completion was captured, because no
completion command exists.**

The dispatcher has **63 named branches** and the `complete_*` family is exactly
`complete_collection`, `complete_goal`, and `complete_tutorial`.  **No command
completes a queue** and **no command materialises a unit from one**.  Worse for
any expectation of a countdown: every occurrence of `attr["ts"]` in the legacy
source is a **write** (`engine.py:189`, `engine.py:198`) or a **deletion**
(`engine.py:202`); the single branch that reads it back is `soulmixer_speedup`,
which is not a general queue path.  So the legacy server **never evaluates a
queue's elapsed time**, there is **no** server-side "is this queue ready?" rule
to reproduce, and this fixture says **nothing** about a finished queue.

That absence is a **recorded property of the legacy contract, not a missing
feature**.  The `production` line owns the missing completion as its finding
rather than inheriting a fixture that pretends otherwise.  Neither a readiness
helper, a remaining-time helper, nor a progress ratio is implemented anywhere in
this change.

## How it was captured

```bash
python -B apps/compat-api/capture_queue_fixture.py
```

`python` is the pinned CPython 3.9.13 executable
(`C:/Users/Edison/AppData/Local/Temp/opencode/cpython39/pkg/tools/python.exe`).
The tool starts `python -B server.py` inside a disposable copy under the
system temp root (root `*.py`, `config/`, `mods/`, `villages/`,
`templates/`, `saves/` seeded from `tests/saves/fresh-player.json`), waits
for `127.0.0.1:5055`, executes three recorded requests, runs one **probe** request
against the same live server (below), stops the server (`taskkill /T /F` +
port-free re-check), re-checks the working-tree containment snapshot and the
**ten** committed boot/placement/purchase/move/sell/store/upgrade/construction/
collect/expand fixture digests, discards the copy, and only then publishes this
directory.  The opt-in legacy command recorder env var
(`SOCIALWARS_COMMAND_RECORD_DIR`) is stripped from the child.

Exit codes (identical meanings to the boot, placement, purchase, move, sell,
store, upgrade, construction, collect, expand, and level captures):

===== ======================================================================
Code  Meaning
===== ======================================================================
0     Fixtures written; server stopped; containment held; copy discarded
2     Environment/usage error (interpreter not 3.9, bad arguments, seed missing)
3     Port conflict: 127.0.0.1:5055 already in use
4     Legacy server failed to start, crashed, or the port stayed busy
5     A legacy request failed or the executed transaction did not match the
      derived envelope
6     Containment violation (working-tree bytes changed, a committed fixture
      directory changed, or the disposable corpus saves changed during
      server startup / login)
7     Fixture write failure
===== ======================================================================

## Layout

```
tests/fixtures/godot-unit-queues/
  README.md                     (this file, hand-authored)
  capture-manifest.json         (generated: schema, interpreter, server,
                                 corpus, the captured-pair and the
                                 missing-completion records, intent with the
                                 established/derived split and every decision,
                                 the executed probe, both transactions,
                                 time-dependent leaves, containment digests,
                                 cleanup)
  steps/
    login_post/                 POST / -> 302, save byte-unchanged
      request.json              form + headers (sanitized)
      before.json               full canonical save
      response.body             the executed 302 body
      response.meta.json        status/headers/size/sha256 (sanitized)
      after.json                full canonical save (equal to before)
    command_push_queue_unit/    POST .../command.php -> 200
      request.json              form incl. the exact `data` field (sanitized)
      before.json               full canonical save
      response.body             `{"result":"success"}`
      response.meta.json        status/headers/size/sha256 (sanitized)
      after.json                full canonical save with
                                `maps[0].items["1"][6] = {"nu": 1, "ts": <stamp>}`
    command_pop_queue_unit/     POST .../command.php -> 200
      request.json              form incl. the exact `data` field (sanitized)
      before.json               full canonical save (the pushed row)
      response.body             `{"result":"success"}`
      response.meta.json        status/headers/size/sha256 (sanitized)
      after.json                full canonical save; the addressed row's bag
                                is `{}` again, so this document equals the seed
```

`before.json` / `after.json` are the complete parsed save documents in a
canonical serialization (sorted keys, 2-space indent, ensure-ASCII,
trailing newline), so the SHA-256 recorded per step is stable regardless of the
disposable server's own JSON formatting.

`request.json` is the exact sent request: the form fields, the headers actually
sent, and the `data` field byte-for-byte.  `user_key` is redacted as
`<redacted>`; `Cookie` / `Set-Cookie` are redacted in the recorded headers; the
`data` field's `accessToken` is the crafted **empty** placeholder, never a token
value (the sanitizer would redact it if that ever changed).  The live requests
always send the real values - only the records are redacted, which is also what
keeps these fields byte-stable across reruns.

## The recorded requests

Both command steps carry the six keys `command()` parses, with the four
documented placeholders (`first_number` 0, `publishActions` [], `tries` 1,
`accessToken` ""), the current `ts` (parsed and then **unread** by legacy code,
so parity normalizes it), and **exactly one** command with the **neutral**
vector `[0, 0, 0, 0, 0, 0, 0, 0]`:

```
[[0,"push_queue_unit",[1],[0,0,0,0,0,0,0,0]]]
[[0,"pop_queue_unit",[1],[0,0,0,0,0,0,0,0]]]
```

The legacy map index `[1]` is the queue commands' **only** argument.  No cost, no
duration, no training time, no count, no readiness, and no outcome is sent.

## The recorded effects

| Step | `attr` before | `attr` after | Other leaves changed |
| --- | --- | --- | --- |
| `command_push_queue_unit` | `{}` | `{"nu": 1, "ts": <stamp>}` | **none** |
| `command_pop_queue_unit` | `{"nu": 1, "ts": <stamp>}` | `{}` | **none** |

* Placement count stays **`40`** throughout, and **every** other row is
  byte-identical.  `store`, `privateState`, `playerInfo`, and **every** other map
  field are byte-identical (the check is over the whole key set, so the field the
  corpus does not record - `map_sizes` - is proven to stay absent).
* **Every** stored resource is unchanged: `xp 4`, `gold 2000`, `wood 2000`,
  `oil 2000`, `steel 2000`, `playerInfo.cash 5`, `privateState.mana 0`.  Legacy's
  per-resource `max(current + delta, 0)` clamp is therefore never exercised -
  a claim limit, not a proof of neutrality on its own, which is what Probe 1
  below is for.
* The pop's `after.json` equals the **seed** byte-for-byte: the three-key
  teardown restored the row's bag.

## The three-key teardown

`pop_queue_unit` deletes **`nu`, `ts`, and `ui` TOGETHER** when the count
reaches zero (`engine.py:198-204`).  No committed branch deletes one of them on
its own, so a save never carries a partial queue teardown.  This contract is a
no inspection of the dispatcher would reveal, which is why it is recorded in the
envelope module, the client projection, the endpoint, and the manifest.

## Probe 1 - why the neutral vector's proof is not a tautology

After both recorded steps, and on the same live server and the same disposable
copy, one further request is executed and recorded in the **manifest** rather
than as a step:

```
push_queue_unit([1]) with a CLIENT-SENT vector [0, 500, 0, 0, 0, 0, 0, 0]
```

It answers the question the endpoint's second post-execution proof half exists
for.  A queue command is dispatched like every other command with a
client-sent 8-slot vector, and `do_command` applies it **before** the branch
(`command.py:40`, `engine.py:251-271`).  The probe establishes that a non-zero
slot **does** move a balance through this very branch - it moved `xp` from `4` to
`504` - so proving after execution that **every** stored resource is **unchanged**
is a real check and not a tautology.  Without probe 1 the "nothing moved" proof
would prove nothing.

## Established versus derived

**Established from committed legacy source** (`command.py:676-708`,
`engine.py:183-213`): the three dispatcher branches take only a map index (plus a
unit id for `push_queue_unit2`); `push_queue_unit` increments `nu` or sets it to
`1` and stamps `ts`; `pop_queue_unit` is inert when `nu` is absent, decrements
otherwise, re-stamps `ts` on a partial decrement, and deletes all three keys
together at zero; **none of the three validates anything** - not that the item is
a training producer, not `training_time`, not `min_level`, and **no cap on
`nu`**; every `attr["ts"]` use in the source is a write or a deletion except
`soulmixer_speedup`'s read; that branch's four lines, its `KeyError` on an empty
bag, its `ceil(remaining / 3600)` cost, and the fact that it **charges nothing**;
its own source comment, *"Quite useless cost calculation for understanding it"*;
the 63-branch dispatcher and the absence of any queue-completion command; and
`apply_resources` running before dispatch with a request-supplied vector.

**Derived and never observed from the Flash client**: that a real client sends
exactly these two batches, and that the derived vectors are neutral.  The claim is
about what the legacy server does with a map index, **never** about what a Flash
client sent.  No Flash, Ruffle, ActionScript, or browser is executed anywhere in
this repository, so nothing here is observed from the real client.

## The decisions, in the manifest

* **D1** - the projection is **read-only** and reports presence and values
  without deciding readiness.  No `is_complete()`, no remaining time, no progress
  ratio, because the legacy server has no such rule to reproduce.
* **D2** - "no server-side completion" is a **recorded requirement**, so the
  absence reads as a property of the contract rather than a missing feature.
* **D3** - the fixture is the push/pop pair against the Command Center, and the
  completion question is recorded as the gap it is.
* **D4** - the derived vector is **neutral** and the endpoint's proof asserts
  that **every** stored resource is unchanged.
* **D5** - no cost, no duration semantics, and **no count bound**: the engine
  sets none, and the recorded absence is not a licence to invent a cap.
* **D6** - `soulmixer_speedup` is recorded verbatim and **implemented not at
  all**: no cost, no timer, no speedup, and a **named refusal** where the legacy
  code would raise `KeyError`.
* **D7** - the queued unit id resolves through the content registry on the
  client, and an unresolvable id is **reported with its recorded value intact**,
  never dropped and never coerced.  `push_queue_unit2` is **not** exposed by the
  endpoint, because its id is a client-supplied argument no evidence constrains.
* **D8** - deterministic evidence, claim limits, and containment.

## Claim limits

* Parity covers **one recorded push/pop transaction** against the **fresh-player
  corpus**: no progressed player, no other map row, and no other command.
* This fixture evidences a **push and a pop**, not a produced unit.  The legacy
  server has no completion command and no unit-materialising command, so nothing
  about a finished queue is evidenced.
* No queue **cost** is claimed or implemented in either direction.  The committed
  configuration records no queueing price and the legacy price vector is
  **client-sent**, so the derived vector is neutral and a server-derived price
  belongs to a later server-authoritative milestone.
* No `training_time` or `sm_training_time` **duration semantics** are claimed.
  `training_time` is a building field (130 of 470 buildings, 0 of 429 units) that
  **no** queue branch reads; `sm_training_time` is a soul-mixer field (300 of 429
  units, **0 of 470** buildings) that only `soulmixer_speedup` reads.
* No **speedup cost**, no **timer**, and no **speedup purchase** are implemented.
  The recorded formula divides an hour and charges nothing, and the legacy author
  labelled it useless.
* No **count bound** is implemented.  The engine sets none, and a documented
  absence is not permission to invent a cap.
* No **unit** is created, trained, spawned, or placed by anything captured here,
  and no acquisition is claimed: no committed unit is store-listed and the real
  unit sources are the later-milestone offer-pack and darts systems.
* No **readiness, remaining time, or progress ratio** is computed anywhere.
* `in_grid`, `GRID_EXTENT`, `cell`, and every placement concern are **absent**
  from the queue derivation: a queue command has no target cell and no footprint,
  so nothing here is a gameplay claim.
* The legacy **missing-row** path is a silent early return that still persists the
  batch, so the endpoint resolves the key against the corpus **before** dispatch
  and answers `unknown_map_key` rather than reporting a no-op as a success.
* No **pixel-parity oracle** against the legacy client exists.
* The committed corpus, the ten delivered fixture directories, legacy sources,
  configs, villages, conversion packages, and registry manifests are all
  **byte-identical** after the run; the working tree's `saves/` is never created.
* No Flash, Ruffle, ActionScript, or browser was involved, and no network beyond
  loopback `127.0.0.1` was used.
