# Proposal

## Why

M8 has delivered six of its eight lines. Line 7 is `animations`, and its investigation is committed
as `docs/legacy-unit-animations.md` (PR #237, merged `ff77e8f`).

The investigation was scoped by an explicit caution: **do not infer animation semantics from M4's
converted unit package**, which establishes asset and timeline **linkage** only. That caution turned
out to be load-bearing rather than theoretical, because the single most tempting reading of the
evidence is wrong, and the package refutes it:

- **The legacy server has no animation rule and no animation command.** Of the **63** named
  `command.py` branches, five contain animation vocabulary as a *substring*, and every one is an
  artifact: `move` and `orient` are the movement line's commands, `batch_remove` and
  `remove_inventory_item` contain the letters of "move" inside "re**move**", and `end_attack` is
  combat termination.
- **Six animation-adjacent committed fields have zero legacy consumers.** `max_frame`,
  `img_name`, `attack`, `attack_interval`, `attack_range`, and `velocity` are each present on all
  **429** committed units, and each has **zero** reads across the seven legacy modules, as does the
  `animal` `properties` flag. **`max_frame` is the seventh zero-consumer committed field in this
  project** — after `unit_capacity`, `training_time`, the level curve's reward fields, the
  `collect` family, and the movement fields — and it is a near-constant: **`5` on 427 of the 429**
  units, `2` on exactly ids **923** and **933**, and `1`/`2` on all 470 buildings. A field that says
  `5` on 427 of 429 definitions and is read by nothing is not a per-unit animation setting.
- **The animation states exist, and they live in the asset rather than in the content or the
  server.** The one committed converted unit package parsed `10033_wild_elephant.swf` and recorded
  **sprite 63 with 29 frames and five named states**: `QUIETO` at frame 1, `ANDAR` at 6, `ATAQUE`
  at 11, `MUERTE` at 16, and `PICAR` at 21. That establishes the **labels and their frame
  positions**, and nothing further: M4's own recorded limit is *no tessellation, no playback
  semantics, labels names-only*, so there is **no** recorded loop, state machine, transition,
  priority, interrupt, per-state duration, or mapping from any server event to any state. `MUERTE`
  is a state the delivered `godot-unit-production` capability already found **unreachable**, since
  no legacy command produces a unit and none kills one.
- **A measured contradiction settles the scope.** For that same unit the committed `max_frame` is
  **2** while the parsed root `frame_count` is **1** and the sprite holding the five labels has
  **29** frames — and the content's own `img_name` equals the converted package's `legacy_id`, so
  both describe the same unit and **disagree**. `max_frame` is therefore **not** the asset's frame
  count, and a line that adopted it as one would be **wrong**. This is recorded as **one** data
  point and derived-provisional: sufficient to **refuse** adopting `max_frame` as a frame count, not
  sufficient to claim what it means, and not a measurement of any other unit — only **one**
  converted unit package and **one** building package are committed, so no distribution over the
  corpus is measurable at all.

## What Changes

- **A typed, read-only asset-timeline linkage projection**: the animation labels, their recorded
  frame positions, the per-sprite frame counts, and the recorded frame rate, each reported
  **verbatim**, plus the committed `max_frame` reported **as content with its zero-consumer status
  and its measured non-equivalence to the asset's frame count**.
- **The animation-field inventory**, recording the six animation-adjacent committed fields with
  their zero-consumer statements and their committed distributions, naming the seventh
  zero-consumer field in this project.
- **The refusals as stated requirements**: no frame duration, no loop count, no state machine, no
  transition rule, no priority or interrupt, no playback order, no per-state timing, no animation
  trigger, and no mapping from any legacy command to any state. Each recorded with its reason.
- **The `max_frame` non-equivalence as a requirement**, so no later line can quietly adopt it as a
  frame count on the strength of its name.
- **Tests and evidence** — a hermetic suite asserting the projection, the inventory, the refusals,
  and the **absence** of any duration, loop, state-machine, transition, or playback helper; plus a
  deterministic `unit-animations-report-v1` report.

### Explicitly not in this change

**No executed-legacy animation fixture**, because there is **no animation behaviour for the legacy
server to have**. **No Compatibility API endpoint and no compat change**: with no server-selected
state there is no intent to send, so the compat suite must stay green **unchanged**. **No playback**
of any kind — no loop, no state machine, no transition, no priority, no interrupt, no per-state
timing. **No adoption of `max_frame` as a frame count**, which the measurement refutes. **No claim
about any unit other than the Wild Elephant**, the single committed converted package. **No
generalisation** from that one data point. **No `basic behaviors`** — its own later line. Legacy
sources, configs, saves, the fifteen delivered fixture directories, conversion packages, and
registry manifests stay byte-identical. No Flash, Ruffle, ActionScript, or browser executes, and no
network is used.

## Capabilities

### New Capabilities

- `godot-unit-animations`: a unit's animation asset as a typed, read-only linkage projection — the
  labels, their frame positions, the per-sprite frame counts, and the recorded rate reported
  **strictly as linkage** — together with the animation-field inventory, the `max_frame`
  non-equivalence, and the explicit refusals of every playback rule.

### Modified Capabilities

- `godot-unit-definitions`: its asset-linkage requirement now **delegates** the animation reading to
  `godot-unit-animations`, so sprite resolution and animation timeline linkage each have one owner
  while the definitions capability keeps ownership of the static field model.
- `godot-unit-movement`: its `animate_move` entry in the recorded absent-helper list is **completed**
  by the animations line, which is where animation refusals live, so the movement capability's
  "no animation is implemented" claim stays true and traceable to one owner.
- `godot-compatibility-boot`: unchanged in behaviour, but its execution boundary now notes that unit
  **animation** is committed content and asset linkage read through the content registry, and
  therefore **not** a GameApi operation — no route, no compat surface, no client intent.

## Impact

- **Godot client** — a new `scripts/units/unit_animations.gd`, a new `tests/test_unit_animations.gd`,
  scope-test allow-list entries, and evidence under
  `apps/client-godot/evidence/unit-animations/`.
- **Compatibility API v0** — **unmodified.** No endpoint, so the compat suite must stay green
  **unchanged** at its current count.
- **Legacy** — unchanged and read only, including `command.py` and `engine.py`.
- **Content package and conversion packages** — unchanged and read only. The labels and frame
  positions resolve through the committed converted package and the registry's `units` domain, so the
  manifest digests remain the gate.
- **Verification** — `verify-boot.ps1` gains the hermetic suite (34 hermetic); the guard baseline,
  hash manifest, content validator, and both batteries stay green.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap Project Status
  ledger, recording the executed commands, the projection surface, and the claim limits.
