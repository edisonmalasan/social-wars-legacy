# Proposal

## Why

M8 line 1 (`unit-definitions`, delivered and archived as
`2026-10-01-unit-definitions`) established the **static** half of a unit: 429 committed
`UnitDefinition`s, typed, read-only, resolved through `ContentRegistry`, with the
static-definition/player-instance boundary drawn as a stated requirement. M8 line 2
delivers the **other half of that boundary** — the player-owned instance — and this
investigation-first line is scoped by what the committed evidence actually supports.

The investigation record `docs/legacy-unit-instances.md` (PR #208, merged as
`235b4d2`) established the contract from committed source. Its findings are
decisive, and two of them are not what a reader would assume:

- **There is no separate unit-instance type in the legacy save.** A unit instance
  **is a map item row** — the same eight-slot shape every building uses
  (`engine.py:31`) — and `push_unit` (`engine.py:54-57`) is
  `building[5].append(unit)` plus a slot-3 timestamp. A **garrisoned unit is a row
  nested inside another row's slot 5**: a row within a row. `pop_unit` scans that
  slot for a matching `item[0]`, pops it, and `map_add_item_from_item` writes it back
  under a new key. (Slot 5 is *not* shared with player storage; `add_store_item`
  writes to the separate `map["store"]` dictionary, which the delivered
  `building-store` line already used.)
- **The production queue is a counter, not a list.** `push_queue_unit`,
  `push_queue_unit2`, and `pop_queue_unit` (`engine.py:183-213`) mutate the
  **building's own `attr` bag**: `nu` is a count, `ts` a start instant, and `ui` an
  optional queued unit id that only the atom-fusion path sets — and the teardown
  **deletes all three together** when the count reaches zero. Nothing about this is
  visible from the dispatcher.

Three content findings constrain the line, and each has no legacy consequence:

- **`unit_capacity` occurs zero times** across `engine.py`, `command.py`,
  `sessions.py`, `server.py`, and `constants.py`. The engine appends to slot 5
  unconditionally, so **no capacity rule may be enforced**. This is the same shape as
  the level curve's unread `reward_type` that the delivered `building-xp` line
  refused to pay: a committed field with no committed consumer gets recorded, not
  invented into a rule.
- **The 130 training producers and the 48 garrison-capable buildings are disjoint
  sets** — no producer garrons, and no garrison-capable building trains.
  `training_time` lives on buildings, not units (0 of 429 units have it).
- **No unit is store-listed** (`in_store` is 0 for all 429). The only committed
  tables referencing unit ids are `offer_packs` (109 refs) and `darts_items` (44) —
  **later milestones**, not this one.

And one reachability fact decides the whole shape of the change: **the corpus
contains no unit row to observe.** 40 rows, 11 distinct item ids, all committed
`type` `b`; 0 units; 0 non-empty slot 5; **every `attr` bag is `{}`**.

## What Changes

- **A typed, read-only `UnitInstance`** that wraps one legacy map row together with
  its resolved `UnitDefinition`, exposing the row's own fields verbatim (item id,
  cell, instant, orientation, player team), its `attr` bag, and its **nested garrison
  rows** — each nested row parsed as a `UnitInstance` in its own right, because the
  evidence says a garrisoned unit is a row within a row. It is a **new type**, never
  a widened `UnitDefinition`, honouring the boundary M8 line 1 drew.
- **A projection** that reads every unit instance out of a parsed map by resolving
  each row's committed `type` against the content package, so a corpus that *did*
  contain units would light up without the projection changing. Against the committed
  corpus it returns **zero** instances, and that zero is asserted rather than
  tolerated.
- **The garrison container contract**, recorded and typed: a row's slot 5 is a list
  of nested rows, never an id list, and the engine never checks it against
  `unit_capacity`.
- **The dead-unit counter contract**, recorded: `privateState["deadHeroes"]` is an
  integer count keyed by item id that **discards the row**, so a dead unit leaves no
  instance behind and is not modelled as one.
- **The production-queue shape recorded as content-level facts only** — `nu`, `ts`,
  and `ui` named and typed as *reserved* `attr` keys with their established meaning
  and teardown rule, and explicitly **not** as a working queue: queueing, training,
  and production behaviour are the `queues` and `production` lines.
- **Tests and evidence** — a hermetic suite asserting the row contract, the nested
  garrison parse, the zero-instance result against the committed corpus, the
  fail-closed paths, the reserved-key inventory, and the absence of any instance
  surface on the delivered definition model; plus a deterministic
  `unit-instances-report-v1` report.

### Explicitly not in this change

**No executed-legacy fixture, and no claim that a player can obtain or place a
unit.** The corpus has no unit row, so capturing one would mean fabricating a player
state; the only path that could create one is `buy` with a client-chosen unit id,
which no evidence shows a player uses, since the committed unit sources are the
offer-pack and darts systems. This is recorded as a limitation, not worked around.

Also out of scope: **queues, production, collection, movement, animations, and basic
behaviors** — each its own later M8 line. **No endpoint and no Compatibility API
change**: an instance is read from a save, not from a server, so the compat suite
must stay green unchanged. No **capacity** rule (no legacy consumer exists). No
**acquisition**, **training**, **garrison-capacity**, **death**, or **resurrection**
behaviour. No **movement**, targeting, combat, or animation semantics. No **unit
statistics** semantics — `attack`, `defense`, `life`, and `velocity` stay the
verbatim committed numbers M8 line 1 delivered. No **pixel parity**. No change to
M8 line 1 or to the eleven M7 lines. **The first executed-legacy unit fixture
belongs to `production` (M8 line 4)**, because the Command Center at map key 1
(`training_time` 5, `min_level` 1) makes the queue genuinely exercisable against
the corpus — a concrete, evidence-backed reason to sequence it there, recorded now so
this proposal does not over-reach. Legacy sources, configs, saves, villages, fixtures,
conversion packages, and registry manifests stay byte-identical. No Flash, Ruffle,
ActionScript, or browser executes, and no network is used.

## Capabilities

### New Capabilities

- `godot-unit-instances`: the player-owned unit instance as a typed, read-only
  projection of a legacy map row — the nested garrison row, the fail-closed row
  parse, the zero-instance result against the committed corpus, the garrison
  container and dead-unit counter contracts, and the reserved production-queue
  `attr` keys — with **no** acquisition, training, movement, or gameplay semantics
  and **no** claim that a unit can be obtained or placed.

### Modified Capabilities

- `godot-unit-definitions`: the delivered static-definition boundary requirement
  gains the instance side of the contract, so a `UnitInstance` is recorded as a
  distinct player-owned type wrapping a row plus its definition, and never as a
  widened `UnitDefinition`.
- `godot-building-xp`: unchanged behaviour, but its record of the committed
  `UnitInstance` gap is superseded by this capability.

## Impact

- **Godot client** — a new `scripts/units/unit_instance.gd` and a new
  `scripts/units/unit_instance_projection.gd`, a new `tests/test_unit_instances.gd`,
  scope-test allow-list entries, and evidence under
  `apps/client-godot/evidence/unit-instances/`.
- **Compatibility API v0** — **unmodified.** An instance is read from a save, so no
  route, response field, or error code is added and the compat suite must stay green
  unchanged.
- **Legacy** — unchanged and read only, including `engine.py`, `command.py`, and
  `config/`.
- **Content package** — unchanged and read only; the projection resolves rows through
  the registry's `units` and `buildings` domains, so the manifest digests remain the
  verification gate.
- **Verification** — `verify-boot.ps1` gains the hermetic unit-instances suite
  (raising the hermetic count to 29, with no new live phase); the guard baseline, the
  hash manifest, the content validator, and both batteries stay green.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap
  Project Status ledger, recording the executed commands, the row contract, the
  recorded no-fixture limitation, and the claim limits.
