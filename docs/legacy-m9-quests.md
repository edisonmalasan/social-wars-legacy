# M9 line 2 — Quests: the legacy contract established by measurement

**Recorded 2026-10-02 by the root orchestrator, before any M9 line 2 proposal.**

`docs/legacy-m9-progression.md` §3–§5 measured the quest branches at survey depth while establishing the
milestone-wide contract. This record goes to the depth a proposal needs and the survey did not answer:
**what each branch reads versus writes**, **which committed quest fields any legacy module reads**, **how
the corpus behaves under each branch**, and **what the committed quest content can and cannot support.**

Every figure is measured from the committed source, not asserted.

---

## 1. Six branches, and what each one actually writes

| Branch | `command.py` | Reads | Writes |
| --- | --- | --- | --- |
| `set_goals(goal_id, json_progress)` | 68 | `args[0]`, `args[1]`, `json.loads` | **nothing directly** — delegates to `engine.py:96` |
| `complete_goal(goal_id)` | 76 | `args[0]` | **NOTHING AT ALL** |
| `set_quest_var(key, value)` | 87 | `args[0]`, `args[1]` | `map["idCurrentMission"]`, `map["currentQuestVars"]`, `map["currentQuestVars"][key]` |
| `collect_mission(next_mission)` | 430 | `args[0]` | `map["idCurrentMission"]`, `map["timestampLastChapter"]`, `map["currentQuestVars"]` |
| `admin_set_quest_rank(quest_index, difficulty)` | 745 | `args[0]`, `args[1]` | `privateState["questsRank"][str(quest_index)]` |
| `end_quest(json_blob)` | 752 | `args[0]`, `json.loads`, plus **six** keys from the parsed blob | `map["questTimes"][str(quest_id)]`, and destroys rows via `map_lose_item` |

**`complete_goal` is the sharpest case in M9.** It reads a goal id, resolves the goal's committed title
through `get_attribute_from_goal_id`, prints it, and **writes nothing**. A goal "completes" by being
narrated in a `print` statement. This is the same *shape* as `research_buy_step_cash` reading a cash
amount it discards, but stronger: here there is **no** client amount and **no** state at all.

## 2. Only TWO committed quest fields are read by anything

Measured as **quoted** occurrences across the seven legacy modules, so comments and prose cannot
contribute:

| Committed field | Quoted legacy occurrences | Where |
| --- | --- | --- |
| `id` | **8** | `command.py` 2, `get_game_config.py` 6 |
| `title` | **2** | `command.py` 2 — the two `print` statements |
| `hint` | **0** | — |
| `description` | **0** | — |
| **`reward`** | **0** | — |
| `kind` | **0** | — |
| `legacy_id` | **0** | — |
| `source_file` | **0** | — |
| `source_layer` | **0** | — |
| `content_version` | **0** | — |

**`reward` is read by nothing.** It is committed on all **91** entries and is **uniformly the value `10`**
on every one of them — so it carries **no information even if it were read**. `hint` and `description` are
likewise read by nothing: the committed quest content exists to be *displayed by the Flash client*, and
the server only ever needed the id and the title.

**This settles the quest-economy question in the strongest available form:** there is no quest reward to
pay, no per-quest cost, and no quest price, because **no committed quest field is read except the id and
the title**, and the title is read solely to print it.

## 3. The committed quest content

`packages/game-content/normalized/quests.json` holds **91** entries, every one `kind: "quest"`, every one
carrying the same ten fields (`legacy_id`, `kind`, `source_file`, `source_layer`, `content_version`,
`id`, `title`, `hint`, `description`, `reward`). Committed `id` values run **`1..91`**.

The server indexes them at **import time** (`get_game_config.py:142`):

```python
goals_id_to_goals_index = {int(item["id"]): i for i, item in enumerate(__game_config["goals"])}

def get_goal_from_id(id: int) -> dict:
    items_index = goals_id_to_goals_index[int(id)] if int(id) in goals_id_to_goals_index
    return __game_config["goals"][items_index] if items_index is not None else None
```

Two consequences, both measured rather than assumed:

- the goal id space is **1-based `1..91`**, and the accessor is **fail-closed**: an id outside the table
  yields `None`, and `get_attribute_from_goal_id` returns `None` for a missing attribute;
- `int(id)` is called on the **client-supplied** value with **no** guard, so a non-numeric goal id raises
  rather than refusing — a legacy crash path, recorded, not reproduced.

## 4. The corpus can exercise every one of the six branches

| State | Value | Consequence |
| --- | --- | --- |
| `privateState["goals"]` | **151** entries, **all `None`** | `set_goals` is exercisable at any id below 151 with **no** padding |
| `privateState["questsRank"]` | `{}` | `admin_set_quest_rank` exercisable, creating its key |
| `privateState["unlockedQuestIndex"]` | `0` | present, and **written by nothing** — see §5 |
| `maps[0]["currentQuestVars"]` | **`None`** | `set_quest_var` must handle a **null** field, which it self-heals |
| `maps[0]["questTimes"]` | `{}` | `end_quest` exercisable, creating its key |
| `maps[0]["idCurrentMission"]` | `0` (**integer**) | `collect_mission` exercisable — and it writes a **string**, see §6 |

**Why the corpus holds 151 `None` entries.** The `set_goals` helper grows the list on demand:

```python
def set_goals(privateState: dict, goal: int, progress: list):
    goals = privateState["goals"]
    while goal >= len(goals):
        goals.append(None)
    goals[goal] = progress
```

A client walked goal ids up to 150 and the server padded the list to accommodate — writing a value for
**none** of them. Measured padding behaviour: `set_goals(0)` and `set_goals(150)` need **no** padding at
this corpus, while `set_goals(500)` would append **350** entries from a single client-sent id. **There is
no upper bound**, which is a Server v1 / M13 gap and must not be silently closed.

## 5. Two committed quest-state keys are written by nothing

| Key | Legacy sites | Where |
| --- | --- | --- |
| `privateState["unlockedQuestIndex"]` | **0** | **written and read by nothing** |
| `privateState["goals"]` | 3 | `engine.py:97` (write), `get_game_config.py:142,146` (**the committed *config* table, not the save**) |
| `map["questTimes"]` | 6 | `command.py:802` (write), `command.py:942` (**`fast_forward` write**), `version.py:39-43` (**migration init**) |
| `map["currentQuestVars"]` | 5 | `command.py:107,113,114,116` (`set_quest_var`), `command.py:440` (`collect_mission` clears it) |
| `map["idCurrentMission"]` | 2 | `command.py:111` (`set_quest_var`'s `id` alias), `command.py:438` (`collect_mission`) |
| `map["timestampLastChapter"]` | 2 | `command.py:439` (write), `command.py:911` (**`fast_forward` write**) |

Two findings here:

- **`unlockedQuestIndex` is committed player state with zero legacy consumers.** It is the **ninth**
  zero-consumer committed field in this project, after `unit_capacity`, the level curve's
  `reward_type`/`reward_amount`, the `collect` family, `max_frame`, `velocity`, and `syringes`.
- **`fast_forward` writes quest state too**, subtracting a client-supplied number of seconds from every
  `questTimes` entry (`command.py:942-944`) and from `timestampLastChapter` (`command.py:911`) — so quest
  timing is **client-writable** in exactly the way the research instant is, and for the same reason:
  nothing reads it to decide anything.
- `version.py:38-44` initializes `questTimes` to `None` then coerces it to `{}` — a **migration path**,
  not gameplay, and recorded as such rather than treated as behaviour.

## 6. The branch shapes a proposal must reproduce exactly

- **`set_quest_var`** writes **any** client-invented key into `currentQuestVars`. The source's own comment
  enumerates **eight** keys (`id`, `spawned`, `ended`, `visited`, `activators`, `boss`, `treasure`,
  `killed`) and there is **no membership test**, so an invented key is accepted and persisted. The key `id`
  **also** aliases `map["idCurrentMission"]`, and `idSimpleChapter` is **explicitly ignored** — the source's
  comment explains the game resets chapters past 9, so the key is dropped to let players reach chapter 99.
- **`collect_mission`** writes `map["idCurrentMission"] = str(next_mission)` — **stringified**, against a
  corpus that records the **integer** `0`. It also sets `timestampLastChapter` and **clears**
  `currentQuestVars` to `{}`, converting the corpus's `None` into a dict as a side effect. Its only guard is
  `if next_mission > 99: next_mission = 1` — a **wrap, not a rejection**, with the source's own comment
  admitting uncertainty about chapters past 99.
- **`end_quest`** is the **most client-sent branch in the project**. It parses one client-authored JSON blob
  and reads `win`, `duration`, `units`, `map`, `difficulty`, `voluntary_end`, and `quest_id` from it;
  `difficulty` is the **only** clamped value (`max(1, min(3, …))`). It then destroys player state by a
  **client-computed** count:

  ```python
  lost = max(0, unit[2] - unit[3])   # number of loses is A - B
  if lost > 0:
      map_lose_item(map, privateState, unit[0], lost)
  ```

## 7. The authority decision this line must make

**`end_quest`'s destruction count is client-dictated.** Reproducing it would be exactly the anti-pattern
`AGENTS.md` names as "Bad" — a client dictating an authoritative outcome. The line must therefore:

- **refuse** the client-computed destruction count rather than implement it, and record the refusal as a
  **divergence** from the legacy server, not as parity;
- derive whatever the service legitimately can — the `quest_id` key, the recorded `win`/`difficulty`
  values it echoes, the `difficulty` clamp, the `id > 99` wrap — and ignore the rest;
- prove every refusal with a **byte-identical before/after state**, the proof form the M7 and M8 lines
  established.

**No quest reward may be paid.** `reward` has **zero** legacy reads and is uniformly `10`, so paying it
would invent an economy from a constant.

**`unlockedQuestIndex` must be reported as content and never written**, matching the `resurrectable` /
`resurrect_hero` shape M8 line 8 delivered — and like that line, `map_lose_item` reaching
`push_dead_unit` means an `end_quest` loss **does** push onto the dead-hero ledger, so the ledger's
fourth door is delivered here too and the two capabilities must agree.

## How these figures were measured

Read-only scripts run with pinned CPython 3.9.13 and `-B` over `command.py`, `engine.py`, `sessions.py`,
`server.py`, `constants.py`, `get_game_config.py`, `version.py`,
`packages/game-content/normalized/quests.json`, and `tests/saves/fresh-player.json`. Field-occupancy
figures were counted as **quoted** occurrences so that comments and recorded non-claims can never be
mistaken for code. No save, config, content package, fixture, or legacy source was modified, and no
preserved byte changed.

Nothing is inferred from any converted asset package.