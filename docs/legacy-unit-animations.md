# Legacy unit animation: investigation

Scope: M8 line 7, `animations`. This record establishes the legacy contract
before any implementation, and it deliberately does **not** take M4's converted
unit package as evidence of animation *behaviour* — that package is committed
with an explicit "no playback semantics" limit, and the one finding below is
precisely a case where reading it as behaviour would have been wrong.

## Summary

**The legacy server has no animation rule, no animation command, and reads none
of the six animation-adjacent committed fields.** The animation states that do
exist live in the **SWF asset timeline**, and they were never extracted into the
modern runtime. So the line's deliverable is an **asset-timeline linkage
projection plus an explicit refusal** of playback, looping, state machines, and
transitions — with **no endpoint and no fixture**, for the same reasons the
`movement` line delivered a projection and refusals.

## 1. No legacy animation command exists

`command.py` has **63** named dispatcher branches. Five contain animation
vocabulary as a *substring*, and every one is an artifact:

| Branch | Why it is not an animation command |
| --- | --- |
| `move` | the type-agnostic coordinate write, already delivered as `godot-building-move` |
| `orient` | a plain client-supplied write of row slot 4 |
| `batch_remove` | contains the letters of `move` inside "re**move**" |
| `remove_inventory_item` | likewise |
| `end_attack` | combat termination, not animation; and see §3 on `attack` |

**There is no branch that starts, stops, advances, loops, or selects an
animation.** Nothing in the seven legacy modules animates anything.

## 2. Six animation-adjacent committed fields, every one with zero legacy consumers

Measured over the seven modules (`command.py`, `engine.py`, `sessions.py`,
`server.py`, `constants.py`, `get_game_config.py`, `version.py`):

| Committed field | Present on units | Distinct values | Legacy reads |
| --- | --- | --- | --- |
| **`max_frame`** | **429 of 429** | **2** | **0** |
| `img_name` | 429 of 429 | 401 | **0** |
| `attack` | 429 of 429 | 131 | **0** |
| `attack_interval` | 429 of 429 | 12 | **0** |
| `attack_range` | 429 of 429 | 14 | **0** |
| `velocity` | 429 of 429 | 11 | **0** |

Plus one `properties` flag with animation-adjacent meaning: `animal`, **0**
reads.

`attack_range` and `velocity` are already recorded as zero-consumer by
`docs/legacy-unit-movement.md`; they are listed here because they belong to this
line's inventory. **`max_frame` is the seventh zero-consumer committed field in
the project**, after `unit_capacity`, `training_time`, the level curve's
`reward_type`/`reward_amount`, the `collect` family, and the movement fields.

### `max_frame` is a near-constant, and it is not what it looks like

| Domain | Distribution |
| --- | --- |
| units (429) | **`5` on 427**, `2` on exactly 2 — ids **923** and **933** |
| buildings (470) | `1` or `2` |

A field that says `5` on 427 of 429 unit definitions and is read by nothing is
not a per-unit animation setting. And §4 shows it is **not** the frame count of
the asset the content names. Its committed encoding is a JSON **number**
(`"max_frame": 2`), unlike the `properties` flags, which are **strings**.

## 3. The animation states exist in the asset, not in the content or the server

The one committed converted unit package,
`assets/converted/units/10033_wild_elephant/package.json`, parsed
`assets/sprites/10033_wild_elephant.swf` and recorded its timeline. Its root
timeline is **one frame with no labels and no removals**, and its single
placement is `move: False` — but its **sprite 63** carries **29 frames and five
named animation states**:

| Label | Frame | Reading |
| --- | --- | --- |
| `QUIETO` | 1 | idle |
| `ANDAR` | 6 | walk |
| `ATAQUE` | 11 | attack |
| `MUERTE` | 16 | death |
| `PICAR` | 21 | peck / gather |

Five further sprites carry `frame_count` 20 with no labels, and one carries 7
with no labels. The recorded `frame_rate` is `30.0`.

**What this establishes:** five named animation states exist in the committed
asset timeline, at recorded frame positions, for this one unit.

**What this does not establish:** any playback. M4's own recorded limit for the
unit conversion is that it produces a per-sprite timeline inventory with shape
and bitmap linkage, **no tessellation and no playback semantics**, and that its
labels are recorded **names-only**. So the frame positions are linkage evidence
and nothing more. There is **no** recorded looping rule, no state machine, no
transition, no priority, no interrupt, no per-state duration, and **no** mapping
from a server-side event to a state — because no legacy branch ever selects one.

The label names are Portuguese, and `MUERTE` (death) is a state the delivered
`production` line already found unreachable from the client: no legacy command
produces a unit and none kills one.

## 4. A measured contradiction: `max_frame` is not the asset's frame count

For the same unit, the committed definition and the parse of the asset its own
`img_name` names disagree:

| Quantity | Value | What it is |
| --- | --- | --- |
| committed `max_frame` | **2** | a per-unit **content** field on the definition |
| parsed `frame_count` | **1** | a static **parse** of that one asset file's root timeline |
| parsed sprite 63 `frame_count` | **29** | the timeline that actually holds the five labels |

The content names **exactly** the asset this package parsed
(`img_name == legacy_id == "10033_wild_elephant"`), so the two numbers describe
the same unit and **disagree**. Therefore `max_frame` is **not** the asset's
frame count, and a line that adopted it as one would be **wrong**.

**This is one data point and is recorded as derived-provisional.** It is
sufficient to *refuse* adopting `max_frame` as a frame count, which is what this
line does. It is **not** sufficient to claim what `max_frame` means, and it is
**not** a measurement of any other unit. Only **one** converted unit package and
**one** converted building package are committed, so no distribution over the
corpus can be measured at all.

## 5. Established versus derived

**Established** (measured, repeatable):

- no legacy animation command; the 63-branch inventory and the five
  substring artifacts;
- the six animation-adjacent committed fields and their **zero** legacy reads
  across seven modules, with the distributions above;
- `max_frame` present on all 429 units and all 470 buildings, with the
  distributions above;
- the five named labels at their recorded frame positions in the one committed
  converted unit package, the per-sprite frame counts, the recorded rate, and
  the root timeline's single frame with no labels;
- the recorded contradiction between committed `max_frame` and the parsed
  frame count for that one unit.

**Derived, and labelled as such:**

- that the five labels are the unit's animation states — the conversion records
  label *names and positions only*, and the reading of each name into an English
  state word is the orchestrator's, not the asset's;
- that `max_frame` is *not* an asset frame count — one data point, sufficient to
  refuse adoption, insufficient to say what it is.

## 6. What this line must therefore refuse

`max_frame`, `frame_count`, `frame_rate`, and the five label names are
**content and linkage**, reportable verbatim. From them this line derives
**nothing**: no frame duration, no loop count, no state machine, no transition
rule, no priority or interrupt, no playback order, no per-state timing, no
animation trigger, and no mapping from any legacy command to any state. It
implements **no** animation, and it adds **no** Compatibility API endpoint and
**no** executed-legacy fixture, because there is no animation behaviour for the
legacy server to have.

## 7. Measurement commands

Every figure above came from reading the committed bytes, with no Flash,
Ruffle, ActionScript, browser, or network:

```bash
python -B - <<'PY'
import json, pathlib, re
u = json.loads(pathlib.Path("packages/game-content/normalized/units.json").read_text())
print("units", len(u), "max_frame", {v: sum(1 for r in u if str(r.get("max_frame")) == v) for v in {str(r.get("max_frame")) for r in u}})
PY
```

- the six zero-consumer counts: a `'"field"'` / `'field'` occurrence count per
  field across the seven legacy modules;
- the 63-branch inventory: a `cmd == "..."` extraction from `command.py`;
- the timeline, labels, and frame counts:
  `assets/converted/units/10033_wild_elephant/package.json`, read as committed
  JSON.

## Claim limits of this record

- **No** animation is established for any unit other than the Wild Elephant, the
  single converted unit package, and even there only the *labels and frame
  positions* are established — never playback.
- **No** claim is made about what `max_frame` means.
- **No** Flash, Ruffle, ActionScript, or browser executed, and no ActionScript
  was decompiled for this record; the M4 inspection and conversion are read as
  committed outputs, not re-run.
- The **no-pixel-parity** and **M6 tile-geometry** gaps are unchanged.
- The label-name readings into English state words are the orchestrator's
  translation, retained alongside the original names so a later line can use the
  original and drop the reading.
