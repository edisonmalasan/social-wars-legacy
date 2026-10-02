# Proposal

## Why

M8 has delivered seven of its eight lines. Line 8 is `basic behaviors`, the milestone's **final**
deliver line, and its investigation is committed as `docs/legacy-unit-behaviors.md` (PR #244, merged
`2e98d55`).

The ledger's own instruction for this line was to **measure its own fields rather than assume the
refusal pattern repeats** — because the last three lines (`production`, `movement`, `animations`)
all resolved to a projection plus refusals. **That instruction was decisive, and the answer is the
opposite of the pattern:**

- Of **twenty-two** behavioural committed fields, **twenty** have **zero** legacy consumers across
  the seven modules, exactly as the last three lines found: `attack` (131 distinct), `defense` (1),
  `life` (150), `attack_interval` (12), `attack_range` (14), `best_against` (5),
  `best_against_mult` (5), `velocity` (11), `min_level` (21), `syringes` (6), `volume` (3),
  `gift_level` (8), `collect_type`, `collect_xp`, `max_collects`, `training_time`, `unit_capacity`,
  `expiration`, `population`, `activation`, `build_time`, and **every** behavioural `properties`
  flag.
- But **two** do not, and one of them is the **first committed field in this project whose legacy
  consumer is a mutation of private state rather than a read**: **`resurrectable`**, set on
  **426 of 429 units** and **0 of 470 buildings**, with exactly **two** reads at `engine.py:159,162`.
  **The eighth zero-consumer candidate is not one.** The second is **`clicks_to_build`**, one read at
  `engine.py:26` inside `map_add_item`, seeding `attr["nc"] = 0`.

The mechanism is `privateState["deadHeroes"]`, a string-keyed count per item id, and **three**
dispatcher branches reach it — each behaving differently, which is the finding:

| Command | Effect on the ledger |
| --- | --- |
| `kill(index, reason)` | deletes the row and **never** touches `deadHeroes` |
| `sell(index, reason)` | deletes the row; calls the `push_dead_unit` engine helper **only** when `reason == "KILL"`, incrementing the ledger when the row is on **team 1** and `resurrectable > 0` |
| `resurrect_hero(index, item_id, x, y, used_syringe)` | decrements the ledger, **deleting the key at zero**, then `map_add_item`s the row back at **client-supplied** `index`/`x`/`y` with no occupancy, bounds, type, or terrain check |

Two further facts make this the sharpest line of the milestone: **`used_syringe` is read from
`args[4]` and discarded**, while the committed `syringes` field — 6 distinct values, **zero**
consumers — is its obvious counterpart, so **no syringe cost is ever charged**; and the `KILL` guard
is exactly why the delivered `godot-building-sell` capability recorded that the combat reason "is
never reached because no reason is accepted from the client", which remains **correct and
unchanged**.

## What Changes

- **A typed, read-only dead-hero ledger projection**: the recorded per-item-id counts, the increment
  and decrement shapes, the **delete-at-zero** rule, and both gates — **team 1** and
  **`resurrectable > 0`** — each reported verbatim, with no count derived from another.
- **The three-door command inventory**, recording for each of `kill`, `sell`, and `resurrect_hero`
  whether it reaches the ledger and what else it mutates, including that `kill` never does and that
  `sell` reaches it only behind the `KILL` guard.
- **A real Compatibility API endpoint** — `POST /v0/resurrect` — accepting **only** a player
  identifier and a cell, with the **revived item id, the map key, and any syringe count derived
  server-side**, the client-supplied `used_syringe` **ignored** exactly as a client amount or price
  is ignored elsewhere. This is the first M8 line whose transaction is server-derived *and* state-
  mutating since `collection`, because it is the first line with a mechanism at all.
- **The `used_syringe` refusal as a stated requirement**: no syringe cost is charged, no resource
  moves, and the committed `syringes` field is reported as content with its zero-consumer status.
- **Tests and evidence** — a hermetic suite asserting the projection, the inventory, the refusals,
  and the **absence** of any syringe-cost, combat, damage, or occupancy helper; plus a deterministic
  `unit-behaviors-report-v1` report.

### Explicitly not in this change

**No executed-legacy fixture**, and the reason is specific rather than generic: `resurrectable` is
**unit-only** (426 of 429 units, **0 of 470 buildings**), the committed corpus places **only
buildings** and **no unit row at all**, and its `deadHeroes` is present and `{}`. Manufacturing a
unit row to make one capturable is refused, exactly as `godot-unit-instances` refused. **No syringe
cost** — the committed field has zero consumers, so charging one would invent an economy. **No
occupancy, bounds, or type validation** on the revived placement — the legacy branch checks none, and
authoritative validation belongs to Server v1 / M13. **No combat resolution of any kind** — `attack`,
`defense`, `life`, `attack_interval`, `attack_range`, `best_against`, and `best_against_mult` all
measure **zero** consumers, so the committed numbers are content, never rules. **No reimplementation
of `clicks_to_build`** — referenced only, since `godot-building-construction` owns the `{"nc": 0}`
counter. Legacy sources, configs, saves, the fifteen delivered fixture directories, conversion
packages, and registry manifests stay byte-identical. No Flash, Ruffle, ActionScript, or browser
executes, and no non-loopback traffic is used.

## Capabilities

### New Capabilities

- `godot-unit-behaviors`: the resurrectable-unit counter as a typed, server-authoritative
  projection — the recorded counts, the increment and decrement shapes, the delete-at-zero rule, and
  both gates — together with the three-door command inventory, the ignored `used_syringe`, the
  refusal of any syringe cost, and the explicit absence of combat.

### Modified Capabilities

- `godot-unit-production`: its claim that "death and resurrection are unreachable and unimplemented"
  is **completed** rather than contradicted — the statement stays true of the delivered client, but
  the server behaviour it left unstated is now recorded, so a reader consulting it alone can no
  longer conclude the server has no death model at all.
- `godot-building-sell`: its recorded claim that the combat `KILL` reason is never reached now
  **names the reason it matters** — the same guard is the only door into the dead-hero ledger, so
  this capability's derived sell reason closes the death path in practice.
- `godot-building-construction`: its deliberately unconsumed `{"nc": 0}` counter is now **named as
  the consumer of `clicks_to_build`**, which is the only committed field that seeds it.
- `godot-compatibility-boot`: unchanged in behaviour, but the new intent joins its typed operation
  list and its "what is not a GameApi operation" boundary is restated against the twenty
  zero-consumer behavioural fields.

## Impact

- **Godot client** — a new `scripts/units/unit_behaviors.gd`, a new `tests/test_unit_behaviors.gd`,
  a typed `resurrect_hero_town()` on both GameApi implementations, a `behavior_flow.gd`, scope-test
  allow-list entries, and evidence under `apps/client-godot/evidence/unit-behaviors/`.
- **Compatibility API v0** — a new `behavior_envelope.py` and `POST /v0/resurrect` endpoint. The
  compat suite will **grow**, because this line adds a state-mutating endpoint.
- **Legacy** — unchanged and read only, including `command.py` and `engine.py`.
- **Content package** — unchanged and read only; `resurrectable` and `syringes` resolve through the
  registry's `units` domain, so the manifest digests remain the gate.
- **Verification** — `verify-boot.ps1` gains the hermetic suite (**35** hermetic) and **one live
  phase**, because this is the first M8 line with a state-mutating endpoint to drive end to end.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap Project Status
  ledger, recording the executed commands, the projection surface, and the claim limits.
