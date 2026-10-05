# Legacy contract: M10 `death`

**Status:** investigation. No proposal, no code.
**Scope:** the M10 deliver item `death`, recorded before any implementation, per
the project's standing rule that a committed investigation precedes a proposal.
**Verdict:** **`death` is CLOSABLE BY MEASUREMENT. It has no undelivered
surface.** Every door into legacy death is already owned by a delivered
capability, and the shared row-removal helper it reaches through is already
recorded, by name, by its owner.

This document exists because that verdict is the kind of claim that is easy to
assert and hard to earn. Everything below is measured, and the two measurement
defects found while measuring it are recorded in §6 rather than quietly fixed.

---

## 1. There is no "death" vocabulary at all

The first measurement is the one that reframes the line. Token-exact occurrences
across the seven legacy root modules (`command.py`, `engine.py`, `sessions.py`,
`server.py`, `constants.py`, `version.py`, `get_game_config.py`):

| token | occurrences | distinct lines | files |
| --- | --- | --- | --- |
| `kill` | 1 | 1 | `command.py` |
| `deadHeroes` | 16 | 14 | `engine.py`, `version.py` |
| `push_dead_unit` | 4 | 4 | `command.py`, `engine.py` |
| `map_lose_item` | 4 | 4 | `command.py`, `engine.py` |
| `resurrectable` | 5 | 5 | `command.py`, `engine.py` |
| `used_syringe` | 1 | 1 | `command.py` |
| `dead` | **0** | 0 | — |
| `death` | **0** | 0 | — |
| `die` | **0** | 0 | — |
| `resurrect` | **0** | 0 | — |
| `revive` | **0** | 0 | — |
| `syringe` | **0** | 0 | — |

The words the roadmap deliver item is named for **do not occur in the legacy
server**. The mechanism is a *ledger* called `deadHeroes` holding a **count per
item id**, and it is reachable only through three helpers and two branches. So
`death` as an item names a concept the preserved server never wrote down, which
is precisely why it needed measuring rather than delivering.

This continues a pattern the project has recorded repeatedly: `unit XP` was
assumed dead and was not; `completed_tutorial` was assumed dead and was not;
`resurrectable` was assumed dead and was not. **The standing instruction is to
measure one's own fields**, and it is why the words being zero does not settle
the question by itself.

## 2. The four doors

Every statement that can remove a placed row or increment the ledger, with the
dispatcher branch that reaches it. The dispatcher matches **`cmd`**, not
`command`; see §6.1 for why that mattered.

| # | door | branch | row removed? | ledger touched? |
| --- | --- | --- | --- | --- |
| 1 | `sell` with `reason == "KILL"` | `sell` (`command.py:149-167`) | yes, `map_delete_item` at `:162` | yes, `push_dead_unit` at `:160` |
| 2 | `kill` | `kill` (`command.py:169-179`) | yes, `map_delete_item` at `:179` | **never** |
| 3 | `map_lose_item` from `end_quest` | `end_quest` (`command.py:796`) | yes, `map_pop_item` | yes, via `push_dead_unit` |
| 4 | `map_lose_item` from `end_attack` | `end_attack` (`command.py:872`) | yes, `map_pop_item` | yes, via `push_dead_unit` |

Doors 3 and 4 are the **same helper** reached from two different branches owned
by two different capabilities.

### 2.1 `sell` classifies death from a client-sent string

```python
elif cmd == "sell":          # command.py:149
    item_index = args[0]
    reason     = args[1]     # client-sent
    ...
    resurrectable = False
    if reason == "KILL":     # :159
        resurrectable = push_dead_unit(save["privateState"], item)
    map_delete_item(map, item_index)   # :162
```

The decision to record a death is taken on a **string the client sent**. The
modern `/v0/sell` endpoint accepts **no reason at all**, which is why the legacy
`KILL` reason is unreachable there; that refusal is already specified and
delivered by `godot-building-sell`.

### 2.2 `kill` reads its reason and discards it

```python
elif cmd == "kill":          # command.py:169
    item_index = args[0]
    reason     = args[1]     # read...
    item = map_get_item(map, item_index)
    if not item: ... return
    name = get_name_from_item_id(item[0])
    map_delete_item(map, item_index)   # :179  ...and `reason` is never used
```

A death by `kill` **never touches the ledger**, so a unit killed this way leaves
no resurrection charge. Already recorded by `godot-unit-behaviors` and by
`godot-combat-actions` ("A kill removes one addressed row and never touches the
dead-hero ledger").

### 2.3 The shared helper, and the count it trusts

```python
def map_lose_item(map, privateState, item, quantity):   # engine.py:215-228
    qty = quantity
    map_items = map["items"]
    while qty > 0:
        deleted = False
        for index in map_items:
            if map_items[index][0] == item and map_items[index][7]:
                _item = map_pop_item(map, index)       # :222 row removed
                push_dead_unit(privateState, _item)    # :223 ledger touched
                deleted = True
                break
        if not deleted:
            return          # silently stops early
        qty -= 1
```

Three properties worth recording:

* the loop runs **`quantity` times**, so one call can remove many rows;
* `quantity` is `max(0, unit[2] - unit[3])` computed **by the client** and passed
  in (`command.py:792` and `:868`, identical text in both branches) — so the
  number of rows destroyed is **client-dictated**;
* `if not deleted: return` **silently truncates** rather than reporting that it
  destroyed fewer rows than asked.

Both reaching branches refuse that count already: `godot-quests` records it as a
**measured divergence** (its probe destroyed a placed row, 40 → 39, while the
modern endpoint leaves all 40 byte-identical) and `godot-combat-actions` derives
the destroyed set server-side and refuses a client-supplied count, a client
`lost` value, **and the two operands that subtract to one**.

### 2.4 The ledger's own two gates, and the field that is read and discarded

`push_dead_unit` (`engine.py:149-170`) increments only when **both** hold: the
row is on **player team 1** (`item[7] != 1` → return) and the committed
`properties` blob contains `resurrectable` with a value `> 0`. It reads that blob
with `json.loads`, so `resurrectable` is a **`properties` key**, not a
top-level column — the same correction `godot-unit-behaviors` already recorded.

`resurrect_hero` (`command.py:630`) reads `used_syringe` from `args[4]` and
**discards it**, while the committed `syringes` field has **zero** consumers, so
**no syringe cost is ever charged**. `resurrect_hero` decrements, deletes the
key at zero, and re-places the row at **client-supplied** `index`/`x`/`y`.

## 3. Every door is owned

| door | owner capability | how the ownership is stated |
| --- | --- | --- |
| 1 `sell` + `KILL` | `godot-unit-behaviors`, `godot-building-sell` | ledger increment behind the string guard; reason refused by the modern endpoint |
| 2 `kill` | `godot-unit-behaviors`, `godot-combat-actions` | "A kill removes one addressed row and never touches the dead-hero ledger" |
| 3 `map_lose_item` from `end_quest` | `godot-quests` | client-dictated count refused, recorded as a **measured divergence** |
| 4 `map_lose_item` from `end_attack` | `godot-combat-actions` | destroyed set derived server-side, count refused |

`godot-unit-behaviors` additionally owns the **door accounting itself** and names
both reaching capabilities, so the ledger owner and the two branch owners cannot
describe the same reach differently:

* the door count is recorded as **four**, with `map_lose_item` named as the
  fourth door;
* the quest path's caller is attributed to **`godot-quests`**;
* the combat path's caller is attributed to **`godot-combat-actions`**;
* the named **dispatcher branch** count is kept separate from the **door** count,
  because `map_lose_item` is an engine helper and not a branch.

Measuring identifier mentions across all **36** `godot-*` main specs, each of
`deadHeroes`, `push_dead_unit`, and `map_lose_item` is named by exactly one
spec — `godot-unit-behaviors` — which is the correct shape for a single owner.

## 4. Why nothing else is left

The obvious remaining question is whether some death behaviour hides outside the
ledger, and the answer is inherited from the previous line rather than assumed:
`godot-damage` established that **no combat is ever resolved**. All seven
committed damage-shaping fields have **zero** legacy consumers under six
counting rules, and there is **nowhere in a save row to store damage**. A unit
therefore cannot be *killed by combat* in the preserved server — `kill`,
`map_lose_item`, and `sell` all arrive as **client-initiated** commands. There is
no simulation for a death line to reproduce.

Consistent with the damage line: the committed corpus has **no unit row at all**
(`tests/saves/fresh-player.json`: 40 placements, 11 distinct item ids, every
committed `type` `b`), and 426 of 429 units carry `resurrectable` while **0 of 470
buildings** do. A death fixture would need a manufactured unit row, which
`godot-unit-behaviors` already refused to manufacture.

## 5. The closure

`death` is closed by measurement with **no new line, no endpoint, and no
fixture**. The claims that justify it:

1. Legacy death is four doors, all enumerated above from source.
2. All four are owned by delivered capabilities, and the ownership is stated in
   those capabilities' own specs rather than asserted here.
3. The shared helper and its client-dictated count are already recorded, and
   already refused on both reaching paths.
4. No combat resolution exists, so no death arises from a simulation.
5. The corpus holds no unit row, so no fixture is obtainable without fabricating
   one — refused here as it was refused there.

**What a `death` line would have delivered, had one been written:** a fifth
door, an endpoint nobody needs, and a fixture that requires a fabricated unit
row. That is the shape of a line whose findings would all be re-statements of
`godot-unit-behaviors`, `godot-combat-actions`, and `godot-quests`.

**Roadmap consequence:** M10's deliver list is `mission loading`, `mission
state`, `combat actions`, `damage`, `death`, `mission completion`, `rewards`.
With line 1 (`mission vocabulary`, where `mission state` was found already
delivered), line 2 (`combat actions`), line 3 (`damage`), and now `death`
closed, the remaining items are **`mission completion`** and **`rewards`**.

## 6. Two measurement defects found while measuring this

Both were found by checking my own instrument rather than trusting it, and
neither is edited away.

### 6.1 The branch detector matched the wrong identifier

The first pass of the door inventory reported `-` for the enclosing branch of
**every** occurrence. The dispatcher compares **`cmd`** (`elif cmd == "sell":`),
and my pattern looked for `command ==`. `command` occurs **zero** times as a
comparison in `command.py`, so the column was void while *looking* like a
finding — it read as "no branch encloses any of this", which is a very different
and very wrong statement.

The corrected pattern finds **63** branches, agreeing with the authoritative
`tools/command-catalog/verify_commands.py` count of **63**, and the old pattern
finds **0**. Both figures are asserted so this cannot recur silently.

This is the **third** occurrence in this project of an identifier-class error
defeating a census, after the `push_queue_unit2` branch-count regex (twice: once
in the investigation, once in the implementation). The lesson already recorded is
that *recording a correction is not the same as preventing the class*; here the
prevention is to cross-check the branch count against the project tool rather
than trusting a local regex at all.

### 6.2 The ownership test was too literal and produced a false "unowned"

The first ownership probe demanded the literal string `end_attack` inside
`openspec/specs/godot-combat-actions/spec.md`, reported
**`map_lose_item` from `end_attack` as UNOWNED**, and would have concluded that
`death` is not closable.

It is owned. `godot-unit-behaviors` states the attribution explicitly and in
both directions: *"it records that the combat-resolution path is reached through
the same `map_lose_item` helper, and names `godot-combat-actions` as the
capability that delivers that caller, so a reader cannot conclude the ledger is
unreachable from combat and the two owners cannot describe the same reach
differently."*

The probe failed because `godot-combat-actions` describes the behaviour as **"a
combat resolution"** and never uses the branch's source name. A test that greps
for a source identifier inside prose specs will produce false negatives whenever
a capability names a command by role instead of by branch — which is the normal
way to write a specification.

**The generalisable finding is the uncomfortable one:** a closure-by-measurement
claim is only as strong as its ownership test, and the obvious ownership test —
grep for the branch name — is exactly the kind that is wrong for the wrong
reason. Any future closure in this project should pair the identifier search with
a **role-based** check, or state plainly that it is identifier-based.

## 7. Claim limits

- **This document closes a roadmap item; it delivers no behaviour.** No endpoint,
  no projection, no suite, and no fixture is added, and no check was run against
  a live server.
- **`death` is closed as a *deliverable*, not as an explanation of the game.** It
  does not claim the preserved server models death well. It has no death
  vocabulary, its destruction count is client-dictated at both reaching branches,
  its ledger has no readers, its `kill` path leaves no resurrection charge, and
  its helper silently truncates when it cannot find enough rows. All of that is
  recorded, and none of it is reproduced.
- **The four-door list is a statement about the seven legacy root modules.** A
  module outside that set is a measurement gap, not an absence.
- **The ownership finding is about the specs, not about code.** It shows each
  door is *claimed* by a delivered capability. It does not re-verify those
  capabilities' implementations, which their own lines did.
- **No claim is made about what the Flash client did.** Every statement is about
  the preserved server.
- **`resurrectable` is a `properties` key**, confirmed here by `json.loads` at
  `engine.py:158`; the top-level reading is refuted.
- **Not investigated here, and therefore not claimed:** mission completion, quest
  rewards, syringe costs, or any balance change. Those are separate items.