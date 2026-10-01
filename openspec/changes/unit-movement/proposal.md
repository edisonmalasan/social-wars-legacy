# Proposal

## Why

M8 has delivered five of its eight lines: `unit definitions`, `unit instances`, `queues`,
`production`, and `collection`. Line 6 is `movement`, and its investigation is committed as
`docs/legacy-unit-movement.md` (PR #229, merged `5cd47a1`).

Two findings from that investigation decide the line's shape, and both are the kind that only
executing against committed source reveals:

- **The legacy server has no movement rule, and the one move command is already delivered.**
  `move` rewrites the row's two coordinate slots to client-supplied values and does nothing else:
  **no type check, no occupancy check, no bounds check, no terrain check, and no speed**, with
  `frame` and `string` read but **unused** — which the delivered `godot-building-move` capability
  already recorded. **`move` is type-agnostic**, so it would rewrite a unit row exactly as it
  rewrites a building's, and the command itself **ships as M7's `building-move`**. There is
  therefore **no new server behaviour** for a unit-movement line to add. Across the seven legacy
  modules there are only **six** writes to a row's slots 0–2, and exactly **two** branches write
  coordinates: `move`, and `pop_unit` releasing a garrison row at client-supplied coordinates with
  the item id overwritten. `orient` is a plain client-supplied slot write.

- **Eight more committed movement-adjacent fields have zero legacy consumers**, and
  **`velocity` is the sharpest instance in the whole project**: positive on **all 429** committed
  unit definitions, and **read by nothing**. That is the **sixth** committed content field with no
  legacy consumer, after `unit_capacity`, `training_time`, the level curve's
  `reward_type`/`reward_amount`, and the `collect` family. `elevation`, `width`, and `height`
  additionally **cannot** yield terrain-aware movement, because the legacy SWF's tile geometry was
  never extracted — the recorded M6 evidence gap.

And one adjacent command deserves naming precisely: **`fast_forward`** shifts every row's slot-3
instant **and** every row's `attr["ts"]` backwards by a **client-supplied** number of seconds. It
has **no observable effect** — precisely because nothing evaluates elapsed time — and it is named
because it is the **client-writable instant a client-side readiness check would trust**, which is
the invented rule the delivered `godot-unit-production` capability already refuses.

## What Changes

- **A typed, read-only placement projection** for a unit row: its cell coordinates, its
  orientation, its committed footprint (`width`, `height`, `elevation`), and its committed
  `velocity` — each reported **strictly as committed content**, with no value derived from it.
- **The movement-command inventory**, recording that `move` is **type-agnostic** and **already
  delivered** through M7, that `orient` is a plain slot write, that `pop_unit` is the only other
  coordinate writer, and that `fast_forward` is the client-writable instant — so a reader can see
  there is **no unit-specific movement command** to reproduce.
- **The `velocity` and footprint refusals as stated requirements**: the committed values are
  reportable as content, and **no** velocity-based travel time, path, terrain interaction,
  occupancy, bounds behaviour, readiness, or interpolation is derived.
- **Tests and evidence** — a hermetic suite asserting the projection, the recorded inventory, the
  refusals, and the **absence** of any travel-time, path, terrain, occupancy, bounds, readiness, or
  interpolation helper; plus a deterministic `unit-movement-report-v1` report.

### Explicitly not in this change

**No executed-legacy movement fixture**, because there is **no unit-specific movement behaviour to
capture** and the committed corpus contains **no unit row** — a stronger statement than a corpus
limitation. **No Compatibility API endpoint and no compat change**: with no server-derived movement
to expose there is no intent to send, so the compat suite must stay green **unchanged**. **No
velocity-based travel time, no path, no terrain or elevation interaction, no occupancy or bounds
behaviour, no readiness, and no interpolation or animation of a move** — each with its recorded
reason. **No animation**: the `animations` line is separate, and M4's converted unit package
establishes asset and timeline **linkage only**, never playback correctness or gameplay
behaviour. **No pixel parity**, and the M6 tile-geometry gap stays a recorded gap. **No change** to
M8 lines 1–5 or the eleven M7 lines — in particular `godot-building-move` is **not** reimplemented
here, only referenced. No `basic behaviors` — its own later line. Legacy sources, configs, saves,
villages, the thirteen delivered fixture directories, conversion packages, and registry manifests
stay byte-identical. No Flash, Ruffle, ActionScript, or browser executes, and no network is used.

## Capabilities

### New Capabilities

- `godot-unit-movement`: the placement of a unit row as a typed, read-only projection — cell,
  orientation, footprint, elevation, and `velocity` reported **strictly as committed content** —
  together with the movement-command inventory (including that `move` is type-agnostic and already
  delivered, and that `fast_forward` makes the row instant client-writable) and the explicit
  refusals of travel time, paths, terrain, occupancy, bounds, readiness, and interpolation.

### Modified Capabilities

- `godot-unit-instances`: the instance projection gains the placement fields named as
  cell-wrapping rather than duplicating them, so the movement capability owns the placement
  *view* while the instance capability keeps ownership of the row.
- `godot-unit-production`: its refusal of any client-trusted readiness is reinforced by naming
  `fast_forward` as the **client-writable** instant such a rule would read.
- `godot-building-move`: its claim limits recorded that occupancy and bounds are enforced
  client-side only and that no cost is known; that finding now also names the **unread**
  `velocity` and footprint fields, so a later line cannot mistake a move for movement.
- `godot-compatibility-boot`: unchanged in behaviour, but its execution boundary notes that unit
  **movement** is committed content read through the content registry and is therefore **not** a
  GameApi operation — no route, no compat surface, no client intent.

## Impact

- **Godot client** — a new `scripts/units/unit_movement.gd`, a new `tests/test_unit_movement.gd`,
  scope-test allow-list entries, and evidence under `apps/client-godot/evidence/unit-movement/`.
- **Compatibility API v0** — **unmodified.** No endpoint, so the compat suite must stay green
  **unchanged** at its current count.
- **Legacy** — unchanged and read only, including `command.py` and `engine.py`.
- **Content package** — unchanged and read only; the footprint and `velocity` values resolve
  through the registry's `units` domain, so the manifest digests remain the gate.
- **Verification** — `verify-boot.ps1` gains the hermetic suite (33 hermetic); the guard baseline,
  hash manifest, content validator, and both batteries stay green.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap Project Status
  ledger, recording the executed commands, the projection surface, and the claim limits.
