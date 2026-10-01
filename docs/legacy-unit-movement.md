# Legacy unit movement — investigation record

**Status:** investigation only. No movement rule is implemented and no fixture is captured,
because the legacy server has **no movement rule to reproduce**.

**Date:** 2026-10-01 · **Milestone:** M8 — Units, line 6 of 8 · **Predecessors:** lines 1–5
delivered and archived

**Facts not re-derived here:** a unit instance is a map row with a nested garrison; the queue
keys `nu`/`ts`/`ui`; `training_time`, `unit_capacity`, and the level curve's reward fields have
zero legacy consumers; six of the ten committed collections grant a unit; and `godot-production`
and `godot-unit-queues` already established that **every** `attr["ts"]` use in the legacy source
is a write or a deletion.

---

## 1. The headline: there is no movement rule, and the one move command is already delivered

The entire `move` branch:

```python
elif cmd == "move":
    item_index = args[0]
    x = args[1]
    y = args[2]
    frame = args[3]
    string = args[4]
    item = map_get_item(map, item_index)
    if not item:
        print("Error: item not found.")
        return
    # Move item
    item[1] = x
    item[2] = y
```

It **rewrites the row's two coordinate slots to client-supplied values** and does nothing else.
There is **no** check that the row is a unit, **no** occupancy check, **no** bounds check, **no**
terrain check, and no use of a speed or a path. `frame` and `string` are read and **unused** —
which the delivered `godot-building-move` capability already recorded.

**So `move` is type-agnostic: it would rewrite a unit row's coordinates exactly as it rewrites a
building's.** And the command itself is **already delivered** — as M7's `building-move` line.
There is therefore **no new server behaviour** for a unit-movement line to add.

### The complete set of coordinate writes

Across `command.py`, `engine.py`, `sessions.py`, `server.py`, `constants.py`,
`get_game_config.py`, and `version.py`, there are only **six** writes to a row's slots 0, 1, or 2:

| Where | What |
| --- | --- |
| `command.py:132-133` (`move`) | `item[1] = x`, `item[2] = y` — the **only** branch that moves an existing row between cells |
| `command.py:403-405` (`pop_unit`) | `unit[0] = item_id`, `unit[1] = x`, `unit[2] = y` — a **garrison** row being placed from the map, at **client-supplied** coordinates and with the item id **overwritten** |
| `engine.py:62` (`pop_unit` helper) | `item[0] = ...` — pops the garrison match, no coordinates |

So exactly two branches write coordinates, and the second only does so when a row leaves a
garrison. `orient` (`item[4] = int(orientation)`) is the only rotation command, and is likewise a
plain client-supplied slot write.

## 2. Eight more committed movement-adjacent fields have zero legacy consumers

Measured across the seven legacy modules:

| Committed field | Legacy reads | Units with a positive value | Buildings with a positive value |
| --- | --- | --- | --- |
| **`velocity`** | **0** | **429 of 429** | 145 of 470 |
| `max_elem_vol` | **0** | 5 | 39 |
| `width` | **0** | 429 | 470 |
| `height` | **0** | 429 | 470 |
| `elevation` | **0** | 429 | 470 |
| `attack_range` | **0** | 429 | 184 |
| `ft_flying` (properties) | **0** | 135 | 8 |
| `ft_ground` (properties) | **0** | 134 | 0 |

**`velocity` is the sharpest instance in the whole project.** It is non-zero on **every one of the
429 committed unit definitions** — it looks exactly like a movement rule — and **no legacy branch
reads it**. This is the **sixth** committed content field with no legacy consumer, after
`unit_capacity`, `training_time`, the level curve's `reward_type`/`reward_amount`, and the
`collect`-family fields.

`elevation` and `width`/`height` also matter here specifically: the delivered M6 town work
already recorded the **iso-engine tile geometry as a known evidence gap** — the legacy SWF's
`TILE_SIZE`, `EI_TILE_HEIGHT_PIXELS`, and grid dimensions were never extracted, so pixel parity
with the Flash client is not claimed. Since `elevation` is unread server-side and the tile
geometry is unrecorded, **no terrain-aware movement can be derived from either source.**

## 3. `fast_forward` is the only time-manipulating command, and it is worth naming

```python
elif cmd == "fast_forward":
    seconds = args[0]
    ...
    for index in items:
        data = items[index]
        data[3] = max(0, data[3] - seconds)
        if data[6]:
            if "ts" in data[6]:
                data[6]["ts"] = max(0, data[6]["ts"] - seconds)
```

`fast_forward` shifts **every** row's slot-3 instant **and** every row's `attr["ts"]` **backwards
by a client-supplied number of seconds**. That is a client-supplied time manipulation, and it can
make a queue's start instant arbitrarily old.

**It changes nothing observable here, and the reason is exactly the `unit-production` refusal:**
since no branch evaluates a queue's elapsed time, shifting the instant has no effect on any
outcome. This is recorded because it is the input a **client-side** readiness check would trust —
which is precisely the invented rule `godot-unit-production` refuses. Naming it makes the refusal
concrete: a future line that added a client-side readiness check would be trusting a
**client-writable** instant.

## 4. What the corpus can exercise

The committed fresh-player corpus has **no unit row** (40 rows across 11 distinct ids, all
committed `type` `b`).

| Operation | Exercisable? | Why |
| --- | --- | --- |
| `move` on a **building** row | **Yes** | already delivered as `godot-building-move` |
| `move` on a **unit** row | **No** | no unit row exists |
| `orient` on any row | **Yes** | a plain client-supplied slot write |
| `fast_forward` | **Yes** | but with no observable effect, since nothing evaluates elapsed time |
| any velocity-, terrain-, or path-aware movement | **No** | the fields are unread and the tile geometry is an M6 evidence gap |

So **no unit-movement fixture is capturable** — not because the corpus lacks a convenient state,
but because **there is no movement behaviour to capture**.

## 5. The consequence for M8 line 6

`movement` is deliverable, and its honest shape is a **projection plus an explicit refusal**:

- a typed, read-only **placement projection** for a placed row: its cell coordinates, its
  orientation, its committed footprint (`width`/`height`/`elevation`) reported **as content only**,
  and its committed `velocity` reported **as content only** with the recorded statement that no
  legacy branch reads it;
- the **movement-command inventory** recording that `move` is **type-agnostic** and already
  delivered, that `orient` is a plain slot write, and that `pop_unit` is the only other coordinate
  writer — so a reader can see there is **no unit-specific movement command** to reproduce;
- the **`fast_forward` recording**, naming it as the client-writable instant that a client-side
  readiness check would trust, which is why no readiness check is implemented;
- **no velocity, path, terrain, occupancy, or travel-time semantics**, each with its recorded
  reason;
- **no endpoint and no fixture** — there is nothing to expose and nothing to capture.

**This is a real deliverable, not a stub.** Without it, `velocity` — non-zero on all 429 unit
definitions — is exactly the kind of field a later line would reach for to build a movement or
travel-time model, with a `fast_forward`-writable instant as its clock. The record closes that door
with the evidence attached.

**What must not be claimed:** that a unit moves, that it moves at its committed velocity, that
movement is terrain- or elevation-aware, that occupancy or bounds are enforced server-side, that
any travel time is computed, that `fast_forward` is a legitimate clock, or that a client-visible
movement rule exists.

## 6. Established versus derived

**Established from committed source:** the whole `move` branch and its five arguments, including
`frame` and `string` read-but-unused; that `move` performs no type, occupancy, bounds, terrain, or
speed check; the complete six-write set for a row's slots 0–2 and which branches perform them;
`orient`'s single slot write; `fast_forward`'s client-supplied time shift over every row's slot 3
and `attr["ts"]`; the **zero** legacy reads of `velocity`, `max_elem_vol`, `width`, `height`,
`elevation`, `attack_range`, `ft_flying`, and `ft_ground`; `velocity` being positive on all 429
units and 145 buildings; the absence of any movement-named dispatcher branch beyond `move`; the
corpus's lack of unit rows; and the M6 tile-geometry evidence gap.

**Derived** (provisional, reversible): that the line's deliverable should be a projection plus a
refusal rather than a movement model; that the movement inventory belongs here rather than to a
later animation line; and that no endpoint is warranted while no server-derived movement exists.

**Not established, and not claimed:** what the Flash client displayed while a unit moved; how the
client animated or interpolated a move; whether the client enforced occupancy or bounds before
sending; the tile geometry and therefore any pixel-level position; and whether the committed
`velocity` was ever consumed by the Flash client itself.
