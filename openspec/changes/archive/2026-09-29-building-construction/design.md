# Design

## Context

See `proposal.md` — Why. This is the seventh change in the same family, and the
second treated investigation-first: the contract was established and recorded in
`docs/legacy-construction-timing.md` before this design was written, so this
section summarizes that evidence rather than repeating the investigation.

### Established from committed legacy source

| Fact | Evidence |
| --- | --- |
| `activate(item_index, duration)` writes `item[3] = time_now()` and, when `duration > 0`, sets `item[6]["cp"] = duration`; when the duration is non-positive it **clears the whole attribute bag** `item[6] = {}` | `command.py:412-428` |
| `add_click(item_index)` raises `item[6]["nc"]`, seeding it to `1` when absent | `command.py:525-535`, `engine.py:125-130` |
| `activate_item_click(item_index)` deletes `item[6]["nc"]` | `command.py:537-548`, `engine.py:132-135` |
| The click counter is seeded by the **purchase** half, not by these commands: `engine.map_add_item` writes `attr["nc"] = 0` for a `player == 1` item whose config has `clicks_to_build > 0` | `engine.py:25-28` — this is why the delivered `building-upgrade` fixture's row is `[24, 45, 49, <ts>, 0, [], {"nc": 0}, 1]` |
| **No server-side completion rule exists**: no branch compares `nc` with `clicks_to_build` | the five branches write only `item[3]` and `item[6]`; the comparison is the client's |
| The friend-assist bag is a separate mechanism: `map_add_item` seeds `attr["si"] = []` for `properties.friend_assistable > 0`, and `buy_si_help` / `finish_si` append and delete `0` entries | `engine.py:20-24`, `engine.py:137-147`, `command.py:549-572` |
| Config: `clicks_to_build` is `1` for 261 buildings and `0` for 154; the corpus's placed buildings are all `1`. `build_time` is the per-item duration (1 walls, 5 Turret I / Command Center, 600 Turret II, 3600 Command Center II). `activation` is `0` for the corpus's placed buildings but `1`/`6`/`3600`/`10800`/`21600`/`86400` for others. `UPGRADE_SPEEDUP_PRICING = [5, 1]` prices *speedups*, not builds | `config/main.json` |
| The fresh corpus has **no construction in progress**: all 40 rows have `attr = {}`, timestamp `0`, `store = []` | the committed `tests/saves/fresh-player.json` |

### Established by executing the real legacy server

Four probes, each in a disposable copy seeded from `tests/saves/fresh-player.json`,
all loopback under the pinned interpreter, all writing nothing into the
repository, all copies removed on exit.

1. **Counter's life in one batch** — `buy` (Turret I `22` at `(55, 40)`, key 41)
   then `add_click(41)`: 40 → 41 placements, `boughtUnits [] → [22]`, row
   `[22, 55, 40, <ts>, 0, [], {"nc": 1}, 1]`. The purchase seeded `{"nc": 0}` and
   one click reached the item's `clicks_to_build = 1`.
2. **An activation countdown** — `activate(11, 3600)` on the placed Turret I:
   `[22, 58, 48, 0, 0, [], {}, 1]` → `[22, 58, 48, <ts>, 0, [], {"cp": 3600}, 1]`.
   Remaining time is therefore `cp - (now - item[3])`, a pure client derivation
   over data the server never interprets.
3. **Finishing, and a zero activation** — `add_click(11)`, `activate_item_click(11)`,
   then `activate(11, 0)`: final row `[22, 58, 48, <ts>, 0, [], {}, 1]`. The counter
   is gone, `cp` was never set, and the zero-duration activation re-stamped the
   timestamp after clearing the bag.
4. **The fixture transaction** — `activate(11, 5)` then `add_click(11)`:
   `[22, 58, 48, 0, 0, [], {}, 1]` → `[22, 58, 48, <ts>, 0, [], {"cp": 5, "nc": 1}, 1]`,
   40 → 40 placements, the whole `privateState` (`boughtUnits []`, `deadHeroes {}`),
   the storage, `playerInfo`, and all seven resources byte-identical, response
   `{"result":"success"}`. The two-command form was chosen over the three-command
   one because it leaves **both** the countdown and the click counter visible in
   the committed after-state, which is what makes it a useful oracle; the third
   step's effect is covered by probe 3 and by the endpoint's per-action proofs.

## Goals / Non-Goals

**Goals:**

- One executed-legacy construction transaction captured from the real legacy
  server, committed with full before/after state, manifest, and README.
- One intent-only v0 endpoint that derives one of the three legacy commands from
  an action plus committed content, executes the unchanged dispatcher in-process,
  and answers with an authoritative superset naming both sides of the in-place
  update — with a per-action proof that the post-state is the one the action
  promises.
- One typed `GameApi.build_construction()` operation with the fake/live
  implementations interchangeable behind it.
- A client build flow whose single step follows the row's own state, plus a
  construction readout (click progress and remaining countdown), with exactly one
  intent, cancellation with no state change, and an authoritative apply that rolls
  back completely on any failure.
- Evidence, provenance, claim limits, documentation, and battery integration
  matching the delivered lines.

**Non-Goals:**

- **The friend-assist cluster** (`buy_si_help`, `finish_si`, the `attr["si"]`
  bag): friend assistance is social behavior that happens to share the attribute
  bag, and this line must not imply a friend can be hired.
- **Speedups** and the `UPGRADE_SPEEDUP_PRICING` global: "Upgrade instantly for…"
  exists in the static inventory, but no speedup command is in the three-command
  contract, and inventing one would fabricate a price.
- The premium upgrade path, `orient`, `collect`, town expansion, resources, XP,
  and any server-authoritative timer validation (Server v1 / M13).

## Decisions

**D1 — The contract is one of three legacy commands over one row's construction
state.** `activate` starts a countdown (or clears the bag), `add_click` records a
build click, `activate_item_click` completes the build. The corpus row chosen for
the fixture is the **Turret I (`22`) at map slot 11** anchored at `(58, 48)` —
`build_time 5`, `clicks_to_build 1` — the same row the move fixture repositions in
its own independent transaction, so the two stay independently readable because
each seeds a fresh corpus. Alternatives: a purchase-then-build fixture (probe 1
shows it works, but it re-derives the placement contract the `building-placement`
line already owns); and the upgrade row's `{"nc": 0}` (the most attractive option,
since the upgrade delta points at it, but consuming it would need a
`sell`+`buy`+build batch that re-derives the upgrade contract inside a second
change — deferred, and named in the risks).

**D2 — One endpoint, one action enum, and a duration derived from committed
content.** `POST /v0/construction` accepts only `{user_id, item_index, action}`
with `action ∈ {"start", "click", "finish"}`; the **start duration is derived from
the item's committed `build_time`**, so unlike every previous line this
contract has no derived placeholder argument at all — the client cannot influence
the countdown. A non-integer or non-positive committed build time fails closed
rather than being coerced. The three actions are the endpoint's own vocabulary,
documented as such; they are not legacy command names, because the client chooses
an *outcome* and the service chooses the command.

**D3 — A per-action post-execution proof, because each action has an exactly
checkable post-condition.** After execution the endpoint requires: the row still
exists and is a list (a construction action must never destroy a row); and then,
per action, `start` → `attr["cp"]` equals the derived duration, `click` →
`attr["nc"]` is present and at least `1`, `finish` → `attr["nc"]` is absent. Any
other outcome is a fail-closed `internal_error`. This is the upgrade line's lesson
applied where it is cheap: the post-conditions are derivable from the config and
the action, so the check costs nothing and removes any chance of reporting a
success that did not do what the action promised.

**D4 — Neutral price vector; no construction cost is claimed.** The derived
`resources_changed` is the all-zero vector on every action, the same boundary the
move, sell, store, and upgrade lines took: the server computes no price, no config
field prices a build, `UPGRADE_SPEEDUP_PRICING` prices speedups (out of scope), and
a client-sent delta would let any client mint resources. The change therefore
claims nothing about what building costs in the legacy client.

**D5 — The threshold and the timing are client-side derivations, exposed as
explicit steps.** No branch compares `nc` with `clicks_to_build`, so the client
decides that a build is complete; and `cp` plus `item[3]` give a remaining time
the server never computes. The client therefore shows click progress as
`nc / clicks_to_build`, remaining time as `cp - (now - item[3])`, and offers one
primary step that follows the row's state: no construction state → `start`; a
counter below the requirement → `click`; a counter that reached it → `finish`; a
countdown running with the counter consumed → nothing to do. This is a
**deliberately explicit, player-triggered** rendering of a loop the legacy client
drives automatically, and the change claims nothing about the legacy client's
automatic timing.

**D6 — The clearing behavior of `activate` is documented, never used as a
cancel.** A non-positive duration clears the **entire** attribute bag, which would
destroy `nc` and any `si` entries. The contract therefore only ever sends a
positive derived duration, never exposes a "cancel build" action, and the risk is
recorded: any future cancel path must not route through `activate(…, 0)`.

**D7 — One more action on the selection-driven surface, with a construction
readout.** The delivered surface already offers `Move`, `Sell`, `Store`, and
`Upgrade`; `Build` joins them, mutually exclusive with the other four. The
construction readout (progress and remaining time) renders for any selected
placement whose row carries construction state, and the pure state-machine helpers
live in a new `construction_flow.gd` beside `placement_flow.gd` and `move_flow.gd`
so the town view and the suite consume the same functions.

**D8 — Evidence, claim limits, and containment.** A windowed fake-API capture
driving the flow a player uses plus a headless deterministic
`construction-report-v1` report (inputs and digests, the intent and its resolved
action, the derived duration and the config field it came from, both rows, the
click counter, the countdown, the projection-constants pointer, the
established-versus-derived split, and explicit non-claims), byte-identical across
reruns. Execution and containment carry forward unchanged: unchanged legacy
`command()` in-process over a disposable corpus, loopback only, no new packages,
both batteries plus the guard baseline and the 3,258-entry hash manifest green in
the final state, and the orchestrator-run integration review as the fallback for
the unavailable dedicated verification workflow.

## Risks / Trade-offs

- **The commands and the duration are derived, never observed** → the boundary is
  drawn exactly where the evidence stops, and every artifact carries it: the
  commands' shapes, effects, seeding rule, and absence of a completion rule are
  established by committed source and four executed probes; that a real
  construction sends them, and that a client sends `build_time` rather than
  `activation` or a speedup-adjusted figure, are not observed.
- **Three actions in one endpoint is a wider surface than the family's
  single-command endpoints** → the alternative (three endpoints) would triple the
  transport surface for three commands that are one state machine; the action enum
  is closed, fail-closed on an unknown value, and each action has its own
  post-execution proof and its own tests.
- **The corpus cannot show a build in progress without starting one** → that is
  what the fixture does, and the client's readout is covered by the suite
  constructing each state directly rather than by mutating the corpus.
- **Not consuming the upgrade row's `{"nc": 0}` leaves the most natural
  cross-line story open** → recorded as a deliberate boundary (D1) and as an
  explicit follow-up in the claim limits, because consuming it would re-derive the
  upgrade contract inside this change; the cheaper alternative — covering the
  counter's origin with the endpoint's own tests over the delivered upgrade
  fixture — is what the suite does.
- **A fifth mode on one surface** → modes stay mutually exclusive, each keeps its
  own state, and the six delivered suites must stay green, so a regression shows
  up in an existing suite rather than hiding behind the new one.
