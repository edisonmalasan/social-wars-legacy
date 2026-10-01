# Legacy unit behaviour: investigation

Scope: M8 line 8, `basic behaviors` — the **final** M8 line. This record establishes the
legacy contract before implementation.

## Summary

**This line is not a refusal, and that is the finding.** Of twenty-two behavioural
committed fields, twenty have **zero** legacy consumers, exactly as the last three
lines found. But **two do not**, and one of them is the **first committed field in this
project whose legacy consumer is a mutation of private state rather than a read**:

| Field | Present | Distinct | Legacy reads |
| --- | --- | --- | --- |
| **`resurrectable`** (`properties` flag) | **426 of 429 units**, **0 of 470 buildings** | — | **2** — `engine.py:159,162` |
| **`clicks_to_build`** | 429 of 429 units | 3 | **1** — `engine.py:26` |

Everything else measured zero across the seven legacy modules: `attack` (131 distinct),
`attack_interval` (12), `attack_range` (14), `best_against` (5), `best_against_mult` (5),
`defense` (1), `life` (150), `velocity` (11), `collect_type`, `collect_xp`, `max_collects`,
`syringes` (6), `volume` (3), `training_time`, `unit_capacity`, `expiration`, `population`,
`min_level` (21), `activation`, `gift_level` (8), `build_time`, and every behavioural
`properties` flag (`animal` on 2, `bulldozable` on 424, `fireman` on 1, `ft_armored` on 157,
`ft_building` on 2, `ft_flying` on 135, `ft_ground` on 134, `harvester` on 5, `healer` on 3,
`human` on 126, `mechanic` on 301, `seeStealthUnits` on 427, `waterborne` on 2, `worker` on 5).

So the **eighth** candidate zero-consumer field is **not** one. `resurrectable` gates a real
counter.

## 1. The death/resurrection counter

`privateState["deadHeroes"]` is a **string-keyed count per item id**. Three dispatcher branches
reach it, and each behaves differently:

### `kill(index, reason)` — `command.py:169-181`

Deletes the row and prints. It **never touches `deadHeroes`**. A combat kill records no death.

### `sell(index, reason)` — `command.py:149-167`

```python
resurrectable = False
if reason == "KILL":
    resurrectable = push_dead_unit(save["privateState"], item)
name = str(get_name_from_item_id(item[0]))
map_delete_item(map, item_index)
```

`push_dead_unit` is an **engine helper, not a branch** (consistent with the committed command
catalog's note). It (`engine.py:149-171`) returns `False` unless the row is on **player team 1**
(`item[7] == 1`) and its `properties` carry `resurrectable > 0`; otherwise it increments
`deadHeroes[str(item_id)]`, creating the key at `1`.

The `reason == "KILL"` guard is why the delivered `godot-building-sell` capability recorded that
the combat `KILL` reason "is never reached because no reason is accepted from the client". That
recorded claim is **correct and unchanged** — the delivered client sends a derived sell reason, so
this door is closed in practice while remaining open in the source.

### `resurrect_hero(index, item_id, x, y, used_syringe)` — `command.py:625-635`

```python
resurrect_hero(save["privateState"], item_id)
map_add_item(map, index, item_id, x, y)
```

`resurrect_hero` (`engine.py:172-182`) decrements `deadHeroes[str(item)]` and **deletes the key
when the count reaches zero**. The row is then re-placed at **client-supplied** `index`, `x`, and
`y`, with **no** occupancy, bounds, type, or terrain check — the same untrusted pattern the delivered
`godot-building-move` capability already records.

**`used_syringe` is read from `args[4]` and discarded.** The obvious counterpart is the committed
`syringes` field — **6 distinct values, zero legacy consumers** — so **no syringe cost is ever
charged** and the revival is free on the server. That is a recorded authority gap for Server v1
(M13), not a rule to invent here.

## 2. The second real consumer: `clicks_to_build`

`engine.py:26`, inside `map_add_item`, reads `clicks_to_build` and, when it is positive, seeds
`attr["nc"] = 0` on a freshly placed team-1 row. That is the construction-click counter, and it is
**already reported and deliberately not consumed** by the delivered `godot-building-construction`
capability, which owns the `{"nc": 0}` counter and the `add_click` command. This line **references**
it and does not reimplement it.

## 3. The corpus can exercise none of it

- `privateState["deadHeroes"]` is **present and `{}`** — an empty ledger, exactly like `store` and
  `privateState["collections"]` were before the collection line's capture.
- **0 of the 40 placed rows are resurrectable**, because `resurrectable` is on **426 of 429 units
  and 0 of 470 buildings** and the corpus places only buildings.
- The corpus places **no unit row at all**.

So the mechanism is **unit-only and real**, and a one-shot executed-legacy fixture is **not**
possible without first manufacturing a unit row — which the `unit instances` line already refused to
do and recorded as the right call.

## 4. A note on where the legacy reads their content

Both reads go through `get_attribute_from_item_id(...)` and then `json.loads(properties)`, so the
legacy server reads the **raw config string** form, while the committed normalized package stores
`properties` as an **object**. That is the **R2 coercion boundary** M8 line 1 recorded, and it means
these legacy reads are **not** against the committed normalized bytes. The committed content and the
legacy reads agree on *values*, not on *representation*.

## 5. Established versus derived

**Established** (measured, repeatable):

- the presence and distinct-value counts of all twenty-two behavioural fields, and the **zero**
  legacy-consumer count for each of the twenty;
- `resurrectable`'s **two** reads and its distribution — **426 of 429 units**, **0 of 470 buildings**;
- `clicks_to_build`'s **one** read and its seeding of `attr["nc"] = 0`;
- the three branch bodies verbatim, and that `push_dead_unit` is an engine helper while `kill` and
  `resurrect_hero` are **dispatcher branches** (63 named branches, both present);
- that `kill` never touches `deadHeroes`, that the `deadHeroes` key is **deleted** at zero, and that
  `used_syringe` is **discarded**;
- the corpus measurements: `deadHeroes` present and `{}`, **0 of 40** placed rows resurrectable,
  **0** unit rows placed.

**Derived, and labelled as such:**

- that `sell(KILL)` and `resurrect_hero` are intended as a **death/resurrection pair**. The two
  functions are complementary and the ledger is shared, but the source contains no comment or
  dispatch path asserting the pairing; the legacy author's own comment on `push_dead_unit` says only
  "Tries to push item to deadHeroes if it is ressurectable and on player team".
- that the revived row is meant to be the same unit that died. Nothing checks it: the caller supplies
  `item_id` independently of whatever was in the ledger.

## 6. What this line must therefore deliver, and refuse

**Deliver**, because the evidence supports it: the two-sided counter as a typed, server-authoritative
projection — the recorded ledger, the increment and decrement shapes, the delete-at-zero rule, the
team-1 and `resurrectable > 0` gates, the three doors and which of them reach the ledger — plus a
content-derived client intent for revival that **ignores** any client-supplied `used_syringe` and
re-derives nothing the client sends.

**Refuse**, each with its reason: no syringe cost (the `syringes` field has zero consumers, so
charging one would invent an economy); no occupancy, bounds, or type validation on the revived
placement (the legacy branch checks none, and authoritative validation belongs to Server v1 / M13);
no claim that the delivered client can reach the death door (its sell reason is derived, so the
`KILL` guard is closed in practice — an already-recorded fact); **no executed-legacy fixture**, since
the corpus places no resurrectable row and manufacturing one is refused; and **no attack, defence,
damage, or combat resolution at all**, because `attack`, `attack_interval`, `attack_range`,
`best_against`, `defense`, and `life` all measure **zero** legacy consumers — the committed numbers
are content, not rules.

## 7. This corrects the delivered `godot-unit-production` record

`godot-unit-production` states that "death and resurrection are unreachable from the delivered client
and unimplemented". That remains **true of the delivered client**, and this record does not dispute
it. But it left the underlying server behaviour unstated, and the accurate statement is sharper:
**the server implements both halves of a resurrectable-unit counter**, and only the `sell(KILL)` door
is closed in practice. A later reader consulting `production` alone would conclude the server has no
death model at all, which is wrong.

## 8. Measurement commands

Every figure came from reading committed bytes, with no Flash, Ruffle, ActionScript, browser, or
network:

```bash
python -B - <<'PY'
import json, pathlib
s = json.loads(pathlib.Path("tests/saves/fresh-player.json").read_text())
print("deadHeroes:", s["privateState"]["deadHeroes"])
PY
```

- the zero-consumer counts: a `'"field"'` / `'field'` occurrence count per field across the seven
  legacy modules;
- the branch bodies: `command.py` read directly at the recorded line ranges;
- `resurrectable` and `clicks_to_build`: counted over `packages/game-content/normalized/{units,
  buildings}.json` with the `properties` object read the way the package stores it.

## Claim limits of this record

- **No** claim about combat: `attack`, `defense`, `life`, `attack_interval`, `attack_range`,
  `best_against`, and `best_against_mult` are **content with zero consumers**, and nothing here says
  what they mean.
- The death/resurrection **pairing** is derived, as recorded in §5.
- **No** executed-legacy fixture, and **no** claim that one could be captured without manufacturing a
  unit row, which is refused.
- **No** Flash, Ruffle, ActionScript, or browser executed, and no ActionScript was decompiled; the M4
  conversion and inspection are read as committed outputs, not re-run.
- The **no-pixel-parity** and **M6 tile-geometry** gaps are unchanged.
