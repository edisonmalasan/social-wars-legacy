# Proposal

## Why

M8 has delivered two of its eight lines: `unit definitions` (the static, typed
`UnitDefinition` over the 429 committed definitions) and `unit instances` (the
player-owned `UnitInstance` wrapping a legacy map row, with a nested garrison). Both were
scoped by committed investigations, and both had a boundary drawn that the next line
inherits.

M8 line 3 is `queues`, and its investigation is committed as
`docs/legacy-production-queues.md` (PR #213). That investigation found **two structural
gaps** that decide what this line can honestly be, and neither is what a reader would
assume:

- **The legacy server never evaluates a queue's elapsed time.** Every `attr["ts"]` use in
  the legacy source is a **write** (`= timestamp_now()`) or a **deletion**
  (`engine.py:183-213`). A queue's progress is therefore **entirely client-side**, and
  there is **no server-side "is this queue complete?" rule to reproduce**. A modern client
  that computed one would be inventing a rule the legacy server does not have.
- **The legacy server has no production path at all.** The dispatcher has 63 named
  branches and the `complete_*` family is exactly `complete_collection`, `complete_goal`,
  and `complete_tutorial` — none of them a queue. A queue can be pushed and popped, but
  **nothing server-side turns a completed queue into a unit**. A placed unit can only
  enter the map through `buy` (client-chosen id, no store check), `pop_unit` out of an
  existing garrison, or `resurrect_hero` from a dead-unit count.

Two further facts constrain what may be claimed:

- The **only** branch that reads `ts` back is `soulmixer_speedup`, and it is not a general
  queue path. It needs both `ts` **and** `ui` in the item's `attr` (so it raises
  `KeyError` on a fresh row), reads the duration from the **queued unit's**
  `sm_training_time` — present on **300 of 429** units and **absent from all 470
  buildings**, so it is a *soul mixer* field rather than a general training duration —
  treats it as **seconds** (`ceil(remaining / 3600)`), **charges nothing** (it only
  *prints* the cost), and sets `ts = 0` so a later refresh sees no timer. Its own source
  comment reads **"Quite useless cost calculation for understanding it"**.
- A queue's **cost is client-sent**: `do_command` calls `apply_resources` with the
  request's per-command vector *before* dispatching the branch, the same untrusted
  pattern `collect` and `expand` already refuse.

And the three commands themselves are thinner than their names suggest: each takes **only
a map index** (plus a unit id for the atom-fusion variant) and performs **no validation at
all** — not that the item is a training producer, not `training_time`, not `min_level`, not
a cap on the count. Any placed row can be queued.

## What Changes

- **A typed, read-only queue projection** over a placed row's `attr` bag, carrying the
  three committed keys the investigation established: the **count** (`nu`), the
  **start instant** (`ts`), and the **optional queued unit id** (`ui`), with the
  **three-key teardown** rule that a pop to zero deletes all three together. It reports
  whether a queue is present and its committed values, and resolves the queued unit id
  against the content package when one is present.
- **The three commands' exact effects recorded as content**, including the **absence of
  validation** as a recorded fact — not reproduced as permission, and not "fixed" by
  adding a check the legacy server does not have.
- **The `soulmixer_speedup` contract recorded, not implemented**: the `ts`+`ui`
  precondition, the `KeyError` on an empty `attr`, the duration read from the **queued
  unit** rather than the building, the **seconds** reading, the `ceil(remaining / 3600)`
  shape, the `ts = 0` teardown, and the author's own "quite useless" verdict — with **no
  cost charged and no timer semantics claimed**.
- **An executed-legacy fixture for the `push`/`pop` pair only**, captured against the
  committed corpus's real placed training producer — **id 26, Command Center, at map key
  1**, `training_time` 5, `min_level` 1, with an **empty `attr` bag**. This is the first
  M8 line that can own a real fixture **without fabricating a player state**.
- **Tests and evidence** — a hermetic suite over the projection, the recorded contracts,
  and the refusals; the fixture-replay parity tests; a live battery phase; and a
  deterministic `unit-queues-report-v1` report.

### Explicitly not in this change

**No elapsed-time evaluation and no completion**, because the legacy server has neither:
nothing here decides whether a queue is ready, and nothing materialises a unit from a
queue. **No queue cost**, because the vector is client-sent. **No speedup cost and no
timer semantics**, because the legacy branch charges nothing and its own author called the
formula useless. **No bounds on the count**, because the legacy engine sets none — the
recorded absence is not a licence to invent a cap. **No `training_time` or
`sm_training_time` duration semantics**, because `training_time` is a building field no
legacy branch reads for a queue and `sm_training_time` belongs to the soul-mixer path
only. **No production**: a unit is not created, trained, or placed, and the recorded
`push`/`pop` pair is a projection and a fixture, not a production rule. **No acquisition**:
no unit is store-listed and the real sources are the later-milestone `offer_packs` and
`darts_items`. Also out of scope: `collection`, `movement`, `animations`, and `basic
behaviors` (each its own later M8 line), the premium speedup purchase itself (a cost, and
a cost is refused), any change to M8 lines 1-2 or the eleven M7 lines, and any pixel
parity. Legacy sources, configs, saves, villages, the ten delivered fixture directories,
conversion packages, and registry manifests stay byte-identical. No Flash, Ruffle,
ActionScript, or browser executes, and every network call is loopback.

## Capabilities

### New Capabilities

- `godot-unit-queues`: the production queue as a typed, read-only projection of a placed
  row's `attr` bag — the committed count, start instant, and optional queued unit id, the
  three-key teardown, the recorded absence of server-side elapsed-time evaluation and of
  any completion command, the `soulmixer_speedup` contract recorded without cost or timer
  semantics, and an executed-legacy fixture for the `push`/`pop` pair against a real
  placed training producer.

### Modified Capabilities

- `godot-compatibility-boot`: the execution boundary names this capability's endpoints, so
  the `GameApi` abstraction requirement records the two guarded queue intents — a push
  and a pop — each of which sends **only a map key** and no cost, duration, completion, or
  readiness outcome.
- `godot-unit-instances`: the reserved-key inventory this capability fulfils, so a row's
  queue keys are no longer merely reserved.

## Impact

- **Godot client** — a new `scripts/units/unit_queue.gd` (the projection and the recorded
  contracts) and `scripts/units/queue_flow.gd` (the derived display layer), a new
  `tests/test_unit_queues.gd`, scope-test allow-list entries, and evidence under
  `apps/client-godot/evidence/unit-queues/`.
- **Compatibility API v0** — a new `queue_envelope.py`, a `POST /v0/queue` endpoint, and
  the two post-execution proofs; the compat suite **grows**.
- **Executed-legacy fixture** — a new `tests/fixtures/godot-unit-queues/` captured from a
  disposable copy of the legacy server, alongside the ten delivered fixture directories.
- **Legacy** — unchanged and read only.
- **Content package** — unchanged and read only; the queued unit id is resolved through
  the registry's `units` domain, so the manifest digests remain the gate.
- **Verification** — `verify-boot.ps1` gains the hermetic suite (30 hermetic) and a
  fourteenth live phase; the guard baseline, hash manifest, content validator, and both
  batteries stay green.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, `apps/compat-api/README.md`,
  and the roadmap Project Status ledger.
