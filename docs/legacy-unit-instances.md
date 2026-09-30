# Legacy unit instances — investigation record

**Status:** investigation only. No behaviour is implemented, no fixture is
captured, and nothing here is a claim about what a player sees. This record
establishes the M8 line 2 (`unit instances`) contract from committed source and
records the reachability limits that must shape the change.

**Date:** 2026-10-01 · **Milestone:** M8 — Units, line 2 of 8 · **Predecessor:**
`2026-10-01-unit-definitions` (M8 line 1, delivered)

**Facts not re-derived here** (recorded by PR #203 and by M8 line 1): the
committed fresh-player corpus has no unit placements; 0 of its 40 placed rows
carry `attr["xp"]`; M4's converted Wild Elephant package proves asset linkage and
renderability, not animation or gameplay semantics; and the content package
carries 429 committed unit definitions, now typed as static `UnitDefinition`s.

---

## 1. The headline finding: there is no separate unit-instance type

A unit instance **is a map item row** — the same eight-slot shape every building
uses. `engine.py:31` writes it:

```python
map["items"][str(index)] = [item, x, y, timestamp, orientation, store, attr, player]
```

and `push_unit` (`engine.py:54-57`) moves one row into another row's slot 5:

```python
def push_unit(unit: dict, building: dict):
    building[5].append(unit)
    building[3] = timestamp_now()
```

`pop_unit` (`engine.py:58-68`) scans that slot for a row whose `item[0]` matches
`item_id`, pops it, and `map_add_item_from_item` (`engine.py:33-35`) writes it
back onto the map under a new key.

So the legacy save has **one** row shape. A placed unit and a placed building are
indistinguishable at the storage level; the difference is the committed `type`
field of the item (`u` vs `b`). A **garrisoned** unit is a row **nested inside
another row's slot 5** — a row within a row, which is why the slot is a list.

This matters for M8 line 1's boundary, which now reads as a spec requirement: a
`UnitDefinition` is static content with no field that could hold a placement key,
coordinates, an owner, or current health. A `UnitInstance` is a **row**, and it is
therefore a genuinely new type that wraps a legacy row plus its definition — never
a widened definition.

**Correction to a natural assumption:** slot 5 is *not* shared with player
storage. `add_store_item` (`engine.py:70-75`) writes to `map["store"]`, a separate
per-map dictionary. Slot 5 is the garrison/container list. The delivered
`building-store` line already used `map["store"]`, which is consistent.

## 2. The production queue is a counter, not a list

`engine.py:183-213` — all three queue commands mutate the **building's own `attr`
bag** (slot 6), never a collection:

| Command | Effect |
| --- | --- |
| `push_queue_unit(item)` | `attr["nu"] += 1` (or set to 1), then `attr["ts"] = timestamp_now()` |
| `push_queue_unit2(item, unit_id)` | the same increment and timestamp, plus `attr["ui"] = unit_id` |
| `pop_queue_unit(item)` | decrement; if it reaches 0, **delete `nu`, `ts`, and `ui`**; otherwise refresh `ts` |

`nu` is a **count**, `ts` a **start instant**, and `ui` an optional **queued unit
id**. Only `push_queue_unit2` (the atom-fusion path) ever sets `ui`. A queue is
therefore a counter and a timestamp, and its teardown is a three-key deletion —
a non-obvious contract that no inspection of the dispatcher would reveal.

## 3. `unit_capacity` has no legacy consumer at all

Across `engine.py`, `command.py`, `sessions.py`, `server.py`, and `constants.py`,
the string `unit_capacity` occurs **zero** times. The engine never validates it:
`push_unit` appends unconditionally. The committed content carries it on **48 of
470** buildings (capacities 1, 2, 3, 4, 6, and 10), and **17 of those 48 are
reachable at the corpus's map level 1**.

**Precedent applied:** this is the same shape as the `levels` schedule's
`reward_type`/`reward_amount` in the delivered `building-xp` line — a committed
content field with no committed consumer. The correct action is to **refuse to
enforce it** and record it, not to invent a capacity check. A server-side garrison
limit belongs to Server v1 / M13, where authoritative validation lives.

## 4. Training buildings and garrison buildings are disjoint sets

- `training_time > 0`: **130 of 470 buildings**, and **0 of 429 units**. Units
  carry no training time; the producer does.
- `unit_capacity > 0`: **48 of 470 buildings**, and **0 of 429 units**.
- **Of the 130 training producers, none is garrison-capable** (all have capacity
  0). The two sets do not intersect.

So a unit is either trained by an academy, hangar, garage, or Command Center
(none of which garrons), or housed in a factory (which garrons but does not
train). Nothing in the committed content joins the two, and no legacy branch
joins them either.

## 5. No unit is store-listed; the unit sources are out of scope

`in_store` is **0 for all 429** unit definitions. Against the committed content,
the only tables that reference unit ids are:

| Source | Rows | Unit ids referenced |
| --- | --- | --- |
| `offer_packs` | 44 | 109 |
| `darts_items` | 27 | 44 |
| `social_items` | 26 | 0 |
| `inventory_items` | 90 | 0 |

Both real sources are the **offer-pack** and **darts** systems, which are later
milestones and are themselves unimplemented. The store path cannot deliver a unit
because no unit is store-listed.

The legacy `buy` branch would place one — it writes whatever `item_id` the client
sends and calls `bought_unit_add` when `playerID == 1`, with no store check — but
**no evidence establishes that a real player obtains a unit that way**, and
`in_store` is already recorded as a client-side-only rule by the delivered
`building-purchase` line. It is not treated as a unit-acquisition path.

## 6. A dead unit leaves no instance behind

`push_dead_unit` (`engine.py:160-181`) is not a dead-unit pool. It returns `False`
unless the row is on the player team (`item[7] == 1`), the item has a `properties`
bag, that bag has `resurrectable`, and its value is `> 0`. On success it
increments an **integer** in `privateState["deadHeroes"][item_id]` and
**discards the row**. `resurrect_hero` decrements that counter and deletes the key
at zero.

`resurrectable > 0` holds on **426 of 429** units, so the gate is nearly
universal — but the surviving artefact is a **count keyed by item id**, never an
instance. A dead unit therefore cannot be a player-owned instance in any sense,
and `resurrect_hero` revives by `item_id` alone with no stored row to recover.

(Also established for the carried friend-assist follow-up: `friend_assistable`
appears on **0 of 429** units, so `map_add_item` never seeds `attr["si"] = []` for
a unit. That seeding is buildings-only.)

## 7. What the corpus can and cannot exercise

The committed fresh-player map has **40 rows across 11 distinct item ids**, all of
committed `type` `b`:

| Placed id | Rows | Name | `unit_capacity` | `training_time` | `collect` |
| --- | --- | --- | --- | --- | --- |
| 23 | 16 | Wall I | 0 | 0 | 0 |
| 929 | 7 | Bridge | 0 | 0 | 0 |
| 930 | 6 | Trees | 4 | 0 | 20 |
| 22 | 2 | Turret I | 0 | 0 | 0 |
| 931 | 2 | Small forest | 4 | 0 | 20 |
| 928 | 2 | Broken Bridge | 0 | 0 | 0 |
| 26 | 1 | Command Center | 0 | **5** | 0 |
| 905 | 1 | Tree | 4 | 0 | 20 |
| 909 | 1 | Space Station | 0 | 0 | 0 |
| 907 | 1 | Small Harbour | 0 | 0 | 0 |
| 908 | 1 | Harbour | 0 | 0 | 0 |

Measured facts:

- **0** rows are units.
- **0** rows have a non-empty slot 5 — no garrison exists anywhere.
- **Every** row's `attr` bag is `{}`. `nu`, `ui`, and `ts` appear on **no** row.
- **3** placed rows are garrison-capable (905, 930, 931) — but all three are
  `collect: 20` decorations, not factories.
- **1** placed row is a training producer: **id 26, Command Center, key 1**, with
  `training_time` 5, `min_level` 1, row `[26, 51, 41, 0, 0, [], {}, 1]`.
- `privateState.deadHeroes` is `{}` and `privateState.boughtUnits` is `[]`.
- The stored `config/main.json` items carry `type` but **no `kind`** — so the
  normalized `kind: "unit"` on all 429 definitions is a **normalization artifact**,
  not a legacy field. The legacy discriminator is `type` alone.

### Reachability, stated plainly

| Operation | Exercisable against the corpus? | Why |
| --- | --- | --- |
| `push_queue_unit` / `pop_queue_unit` / `push_queue_unit2` | **Yes** | The Command Center at key 1 is a real placed training producer with an empty `attr` bag. |
| `push_unit` (garrison) | **Container only** | Three placed rows have a slot-5 list that would accept a row, but there is **no unit row to move**. |
| `pop_unit` (ungarrison) | **No** | No row has a non-empty slot 5. |
| `push_dead_unit` / `resurrect_hero` | **No** | Requires a unit row on the player team; none exists. |
| Observing any unit instance | **No** | There is no unit row anywhere in the corpus. |

## 8. The consequence for M8 line 2

**No executed-legacy fixture can be captured for a unit instance without
fabricating a player state.** The corpus contains no unit row to observe, and
every way to create one (`buy` with a client-chosen unit id) is a path no evidence
shows a player uses — the committed sources of units are the offer-pack and darts
systems, which are later milestones.

The honest deliverable for `unit instances` is therefore:

- a typed, read-only **`UnitInstance`** that wraps a legacy map row plus its
  resolved `UnitDefinition`, exposing the row's own fields verbatim (item id, cell,
  instant, orientation, player team) and its nested garrison rows, with the
  no-semantics and absent-is-not-zero rules carried over from M8 line 1;
- a **projection** that reads unit instances out of a parsed map, so a corpus with
  units would light up without the code changing;
- the source-grounded contract for the garrison container and the dead-unit
  counter, recorded rather than simulated;
- **no** executed-legacy fixture, **no** endpoint, **no** acquisition, training, or
  movement behaviour, and **no** claim that a player can obtain or place a unit;
- an explicit statement that `unit_capacity` is a committed field with **no legacy
  consumer**, so no capacity rule is implemented.

**The first executed-legacy unit fixture belongs to `production` (M8 line 4)**, not
to this line, because the Command Center at key 1 makes the queue genuinely
exercisable. That is a concrete, evidence-backed reason to sequence it there, and
it is recorded now so the proposal does not over-reach.

## 9. Established versus derived

**Established from committed source** (read directly, with file and line):
the eight-slot row shape (`engine.py:31`); `push_unit`/`pop_unit` appending to
slot 5 and stamping slot 3 (`engine.py:54-68`); the three queue commands' counter,
timestamp, and unit-id semantics including the three-key teardown
(`engine.py:183-213`); `push_dead_unit`'s four conditions and its count-not-pool
result (`engine.py:160-181`); the absence of any `unit_capacity` reader across
five legacy modules; `in_store` being 0 for all 429 units; the disjointness of the
training and garrison building sets; the corpus's 40 rows / 11 distinct ids / 0
units / 0 non-empty slot 5 / all-empty `attr` bags; the Command Center row at key
1; `resurrectable` on 426 of 429 units; `friend_assistable` on 0 of 429; and the
absent `kind` in the stored config.

**Derived** (provisional, and reversible): that a `UnitInstance` should wrap a row
rather than duplicate the row's fields; that the garrison container belongs to the
building row rather than to a separate collection; that the line should be
read-only with no endpoint. Each is a design choice over an established shape, not
a legacy observation, and each is recorded as such in the proposal's design.

**Not established, and not claimed:** what a unit looks like when rendered or
animated; how a unit acquires a target; what a unit's statistics mean in play; how
long a unit lives; how a queue's elapsed time is presented; and whether any
client-visible rule gates garrisons, training, or unit availability.
