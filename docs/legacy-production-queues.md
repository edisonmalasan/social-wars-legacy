# Legacy production queues — investigation record

**Status:** investigation only. No behaviour is implemented and no fixture is captured.
This record establishes the M8 line 3 (`queues`) contract from committed source and
records the two structural gaps that must shape the change.

**Date:** 2026-10-01 · **Milestone:** M8 — Units, line 3 of 8 · **Predecessors:**
`2026-10-01-unit-definitions` (line 1), `2026-10-01-unit-instances` (line 2)

**Facts not re-derived here:** the queue's `attr` keys are `nu` (count), `ts` (start
instant), and `ui` (optional queued unit id), deleted together at zero
(`engine.py:183-213`); `training_time` lives on **buildings**, not units; no committed
unit is store-listed; and a unit instance is a map row whose garrison is a nested row.

---

## 1. The three queue commands carry no intent beyond a map index

All three dispatcher branches (`command.py`) take only a map index, plus a unit id for
the atom-fusion variant:

| Command | Args | Effect |
| --- | --- | --- |
| `push_queue_unit` | `args[0]` index | `nu += 1` (or set to 1), `ts = timestamp_now()` |
| `push_queue_unit2` | `args[0]` atom-fusion index, `args[1]` unit_id | the same, plus `ui = unit_id` |
| `pop_queue_unit` | `args[0]` index | decrement; at zero **delete `nu`, `ts`, and `ui`**; otherwise refresh `ts` |

Each branch resolves the row with `map_get_item`, prints an error and returns early if
the row is missing, and otherwise calls its engine helper. **That is the whole branch.**

**No validation of any kind is performed.** `push_queue_unit` does not check that the
item is a training producer, does not read `training_time`, does not check `min_level`,
does not cap `nu`, and does not refuse a second queue on a row that already has one. Any
placed row can be queued, and the queue length is unbounded.

## 2. The legacy server never evaluates a queue's elapsed time

Every occurrence of `attr["ts"]` in the legacy source is either a **write**
(`= timestamp_now()`) or a **deletion** (`del attr["ts"]`). There is exactly **one**
branch that reads it back, and it is not a general queue path — see §3.

So a queue's progress is **entirely client-side**: the client counts down locally from
the `ts` it can read out of the save, and the server has no notion of a queue being
ready. This is the single most important fact for the `production` line, and it means
**no server-side "is this queue complete?" rule exists to reproduce.**

## 3. `soulmixer_speedup` — the only time evaluation, and the author called it useless

`command.py`, the `soulmixer_speedup` branch:

```python
start = atom_fusion[6]["ts"]
now = timestamp_now()
sm_training_time = int(get_attribute_from_item_id(atom_fusion[6]["ui"], "sm_training_time"))
remaining_time = sm_training_time - (now - start)
cash_cost = ceil(remaining_time / 3600)
# Set start timestamp to 0 so that if refreshed, the timer will be gone
atom_fusion[6]["ts"] = 0
```

Four facts follow, each of which constrains what may be claimed:

1. **It reads `ts` and `ui` off the item's `attr`**, so it is only reachable after a
   `push_queue_unit2` has set both. A fresh row with an empty `attr` raises a
   `KeyError` on `atom_fusion[6]["ts"]` — a real, documentable failure mode, and direct
   evidence that this branch is not a general queue operation.
2. **It looks up `sm_training_time` on the *queued unit*, not on the building.** The
   duration is a property of what is being trained, read through `ui`.
3. **`sm_training_time - (now - start)` treats the field as SECONDS**, because the cost
   divides by 3600. The committed values begin at 4000 and run through 84 distinct
   values.
4. **The legacy author marked the calculation as throwaway in the source comment —
   "Quite useless cost calculation for understanding it" — and the branch charges
   nothing.** It only *prints* `Cost: {cash_cost} cash` and then sets `ts = 0` so a
   later refresh sees no timer. So the speedup is a no-op on every balance and destroys
   the timer.

**Therefore no speedup cost may be implemented, and no timer semantics may be claimed
from this branch.** Reproducing a formula the legacy source itself labels useless, and
which never charges anything, would invent an economy.

## 4. `sm_training_time` is a soul-mixer field, not a training duration

| Measure | Value |
| --- | --- |
| Units **with** `sm_training_time` | **300 of 429** |
| Units **without** | **129** — including `923` Gorilla, `933` Wild Elephant, `1001` Worker I, `1013` Truck |
| Distinct values | **84**, from 4000 upward |
| Buildings with the field | **0 of 470** |

`sm` is the *soul mixer* / atom-fusion path. So for the 129 units lacking the field, the
`soulmixer_speedup` lookup returns nothing and the `int(...)` conversion would raise —
a second reason the branch cannot be treated as a general queue completion rule.

## 5. There is no command that completes a queue or materialises a unit

The dispatcher has **63 named branches**. The `complete_*` family is exactly three:
`complete_collection`, `complete_goal`, `complete_tutorial` — none of them a queue. The
unit-related branches are `add_xp_unit`, `pop_unit`, `push_unit`, `resurrect_hero`,
`unit_collections_completed`, and `rt_open_graph_unit`.

**So the legacy server has no production path at all.** A queue can be pushed and
popped, but nothing server-side turns a completed queue into a unit. A placed unit can
only enter the map through `buy` (client-chosen `item_id`, no store check),
`pop_unit` (out of an existing garrison), or `resurrect_hero` (from a dead-unit count).
Combined with the earlier finding that **no unit is store-listed** and the real unit
sources are `offer_packs` and `darts_items` — both later milestones — this closes off
any claim that a player can obtain or produce a unit through the queue.

## 6. A queue's cost is client-sent

`do_command` applies the per-command resource vector **before** dispatching the branch:

```python
apply_resources(save, map, resources_changed)
```

`resources_changed` comes from the request. So any cost attached to queueing is an
**untrusted client delta** — the same pattern `collect` and `expand` already refuse, and
recorded in the command catalog as *read but unused* on the arguments side. **No queue
cost may be implemented**, and any future cost belongs to server-authoritative
validation (M13), where the price is derived server-side from committed content.

## 7. What the corpus can exercise

The committed fresh-player map places **id 26, Command Center, at map key 1**, with
`training_time` 5, `min_level` 1, `group_type` `COMMAND_CENTER`, and the row
`[26, 51, 41, 0, 0, [], {}, 1]` — an **empty `attr` bag**.

That makes the plain queue pair genuinely exercisable **without fabricating any player
state**:

| Operation | Exercisable? | Note |
| --- | --- | --- |
| `push_queue_unit` on key 1 | **Yes** | adds `nu: 1` and `ts: <server now>` to a real placed producer's empty `attr` |
| `pop_queue_unit` on key 1 | **Yes** | after a push, deletes `nu` and `ts` together |
| `pop_queue_unit` on a fresh row | **Yes, and inert** | `nu` absent → the helper returns without change |
| `push_queue_unit2` | **Yes** | sets `ui` from a client-sent unit id — a client-chosen id, since no unit is otherwise obtainable |
| `soulmixer_speedup` | **No** | needs `ts` *and* `ui` in the same `attr`; a fresh row raises `KeyError` |
| any completion | **No** | no such command exists |

**This is the first M8 line that can own a real executed-legacy fixture**, and the
investigation deliberately reserves it: the recorded `push`/`pop` pair against the
Command Center is the natural oracle for the `production` line, where the missing piece
— a server-side completion — is itself the finding.

## 8. The consequence for M8 line 3

`queues` is deliverable, and its honest shape is narrower than the roadmap wording
suggests:

- a typed, read-only **queue projection** over a placed row's `attr` bag: the committed
  count, the recorded start instant, the optional queued unit id, whether a queue is
  present, and the established teardown rule;
- the **three commands' exact effects** established, with the absence of validation
  recorded as a fact rather than reproduced as permission;
- the **`soulmixer_speedup` contract recorded, not implemented**: the seconds reading,
  the `ui`-based duration lookup, the `ceil(remaining / 3600)` shape, the `ts = 0`
  teardown, the empty-`attr` `KeyError`, and the author's own "quite useless" verdict —
  with **no cost charged and no timer semantics claimed**;
- **no elapsed-time evaluation**, because the legacy server has none;
- **no completion**, because no such command exists;
- **no queue cost**, because the vector is client-sent;
- an executed-legacy fixture **for the push/pop pair only**, with the completion question
  recorded as the gap it is.

**What must not be claimed:** that a queue completes, that a queue produces a unit, that a
speedup costs anything, that `training_time` or `sm_training_time` is a general training
duration, or that any client-visible rule gates queueing.

## 9. Established versus derived

**Established from committed source:** the three branches' exact arguments and effects;
the absence of any validation; that every `attr["ts"]` use is a write or a deletion
except in `soulmixer_speedup`; that branch's four lines, its comment, its `KeyError` on
an empty `attr`, its `ceil(remaining / 3600)` cost, and that it charges nothing; the
300-of-429 `sm_training_time` coverage, its 84 distinct values, and its absence from all
buildings; the 63 dispatcher branches and the absence of any queue-completion command;
`apply_resources` running before dispatch with a request-supplied vector; and the
Command Center row at key 1 with its empty `attr` bag.

**Derived** (provisional, reversible): that a queue projection is read-only with no
endpoint; that the push/pop fixture belongs to the `production` line rather than this
one; that `MAX`-style bounds on `nu` are not implemented because the legacy engine sets
none.

**Not established, and not claimed:** how the Flash client presented a queue; what
"complete" means in the client; whether a queue consumes building content; the atomic
fusion system's own semantics beyond this one branch; and where a player actually gets a
unit in normal play.
