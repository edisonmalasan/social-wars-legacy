# Legacy contract: M10 `mission completion`

**Status:** investigation. No proposal, no code.
**Scope:** the M10 deliver item `mission completion`, recorded before any implementation, per
the project's standing rule that a committed investigation precedes a proposal.
**Verdict:** **`mission completion` is CLOSABLE BY MEASUREMENT. It has no undelivered
surface.** The preserved server contains no mission-completion mechanism: a 64-name
vocabulary that nothing reads, a mission pointer with two writers and no reader, one branch
whose name is the deliver item that mutates nothing at all, no completion ledger, and no
mission or chapter content to complete one from. Every part is already owned by a delivered
capability.

This document exists because that verdict is the kind of claim that is easy to assert and
hard to earn. Everything below is measured, and the **five** measurement defects found
while measuring it are recorded in §9 rather than quietly fixed — the third being the one
that nearly inverted the corpus finding, and the fourth being a detection pattern that
under-counted the very thing it was sent to find.

---

## 1. The vocabulary is declared 64 times and consumed zero times

`godot-mission-vocabulary` recorded this and specified that the finding be re-measured on
every run rather than inherited. Re-measured here across **all eleven** top-level legacy
modules (`auctions.py`, `bundle.py`, `command.py`, `constants.py`, `engine.py`,
`get_game_config.py`, `get_player_info.py`, `legacy_command_recorder.py`, `server.py`,
`sessions.py`, `version.py`):

| measurement | value |
| --- | --- |
| `MISSION_*` declarations in `constants.py` | **64** |
| declarations at indented scope, `constants.py:984-1047` | 64 |
| distinct declared values | **64** |
| numbering gaps | **`[9, 10, 20, 57]`** |
| `MISSION_NONE` / maximum value | `0` / `67` |
| occurrences of any `MISSION_*` name **outside** `constants.py` | **0** |

Eleven modules, not the seven this project's earlier probes walked. The census is wider
than the one it inherits, and the finding survives the widening.

**This count is non-vacuous, and that had to be established before believing it.** My first
pattern anchored the identifier at column zero and therefore found **zero** declarations —
which then reported "0 names with any occurrence outside `constants.py`" as a
*confirmation*. It confirmed nothing: it had tested zero names. See §9.1. A census whose
subject list is empty produces the same output as a clean one, which is why the declaration
count is measured and printed before any consumer result is believed.

## 2. The mission pointer: two writers, zero readers

The whole of mission *position* is two fields on `maps[0]`.

| field | occurrences | distinct lines | every site | readers |
| --- | --- | --- | --- | --- |
| `idCurrentMission` | **2** | **2** | `command.py:111`, `command.py:438` | **0** |
| `timestampLastChapter` | **3** | **2** | `command.py:439`; `command.py:911` carries the token **twice** | **0** |

All four sites are **writes**. `command.py:911` is a read-modify inside `fast_forward` —
`map["timestampLastChapter"] = max(0, map["timestampLastChapter"] - seconds)` — so it is a
writer that consumes its own previous value while a **client-supplied** number of seconds
is subtracted.

The two writers of the pointer are not equivalent, and the difference is the only
substantive behaviour attached to it:

- **`collect_mission`** (`command.py:430-442`) takes `args[0]` as the next mission, clamps
  **only** the upper bound (`if next_mission > 99: next_mission = 1`), writes it as
  **`str(next_mission)`**, stamps `timestampLastChapter` with the current time, and clears
  `currentQuestVars`. Its own comments record the reasoning: *"chapters 1 - 8 are
  scripted"*, *"starting chapters 9+ works, the game has 90 entries"*, *"I'm going to allow a
  restart after chapter 99"*.
- **`set_quest_var`** (`command.py:87-117`) writes the pointer **only** when
  `args[0] == "id"`, taking the new value from **client-supplied `args[1]`** with **no
  validation of any kind**. The branch's own comment at `command.py:109` is
  `# TODO: Check that those values are actually the same`.

**A milestone-opening sentence is imprecise, and the correction matters.**
`docs/legacy-m10-missions.md` records that `collect_mission` *"is the **only**
mission-mutating command in the preserved server"*. Measured: it is the only **dedicated**
mission command, but `set_quest_var` is a **second writer** of the mission pointer. Nothing
delivered changes as a result — `godot-quests` already records the aliasing explicitly, by
both the field table (`apps/compat-api/quest_envelope.py:150`, listing `command.py:111, 438`)
and the alias note (`quest_envelope.py:333`, *"The key that ALSO aliases
`map["idCurrentMission"]` (`command.py:110-111`)"*). The imprecision is in the prose, not in
the delivered record.

## 3. Only 5 of 63 branches touch mission state

The branch inventory is the authoritative one from `tools/command-catalog/verify_commands.py`,
imported rather than re-derived: `verify_commands.py` reports `command_branches: 63` and
`"result": "agreement"`. This is the fourth census in this project where a locally-written
branch detector was the wrong tool.

| branch | span | mission state it touches |
| --- | --- | --- |
| `set_quest_var` | `command.py:87-118` | `idCurrentMission`, `currentQuestVars` |
| `collect_mission` | `command.py:430-443` | `idCurrentMission`, `timestampLastChapter`, `currentQuestVars` |
| `admin_set_quest_rank` | `command.py:745-751` | `questsRank` |
| `end_quest` | `command.py:752-807` | `questTimes` |
| `fast_forward` | `command.py:905-947` | `questTimes`, `timestampLastChapter` |
| **the other 58** | — | **none** |

**The two branches a mission completion would plausibly hook touch nothing at all.**
`end_attack` (`command.py:808`) and `kill` (`command.py:169`) are the combat outcomes that
`MISSION_KILLED_ENEMY` (67) and `MISSION_ASSAULTS_WON` (46) would most naturally be resolved
from, and neither appears in the table above. The same holds for `kill_iid`, `sell`,
`complete_collection`, `win_daily_bonus`, and every other combat-adjacent branch.

## 4. `complete_goal`, the branch named for this deliver item, mutates nothing

```python
elif cmd == "complete_goal":            # command.py:76
    goal_id = args[0]

    print(f"Goal '", get_attribute_from_goal_id(goal_id, "title"), "' completed.", sep='')
```

That is the entire branch, spanning `command.py:76-79`. A goal "completes" by being narrated
in a `print`. `godot-quests` measured and specified this; it is re-confirmed here because it
is the single most direct reading of the deliver item's name, and a re-confirmation that
disagreed would have reopened the line.

`godot-quests` also measured that `complete_goal` is not even reachable through the delivered
typed client, because the addressing is a required parameter.

## 5. There is no completion ledger

A recorded completion needs an append. Scanning all 63 branch bodies for `.append(` yields
exactly **three**, and none is a mission ledger:

| branch | appends to | what it is |
| --- | --- | --- |
| `complete_collection` | `map["collections"]` | a unit-collection id, delivered by `godot-unit-collection` |
| `darts_shoot_balloon` | `privateState["dartsBalloonsShot"]` (via a local alias) | a darts target index |
| `rt_open_graph_unit` | `privateState["publishedOpenGraphUnit"]` | a social publish record |

No `completedMissions`, `finishedMissions`, or equivalent key exists. Searching every
`privateState` key across all committed documents yields **47 distinct keys** and **not one**
of them is mission- or chapter-shaped.

## 6. There is no mission or chapter content to complete one from

| measurement | value |
| --- | --- |
| `config/main.json` top-level keys | **20** |
| top-level keys matching `mission`, `chapter`, `stage`, `campaign`, `scenario` | **NONE** |
| case-insensitive occurrences of `mission` in the whole document | **4** |
| `goals` entries | **91** |
| `goals` entry keys | `description`, `hint`, `id`, `reward`, `title` |
| `goals` entries whose serialized form mentions `chapter` | **0** |
| distinct `goals` `reward` values | **`[10]`** — the **integer**, on all 91 |

All four `mission` occurrences are accounted for: **one** is a quest hint string (*"Prepare
you army... Your mission is to destroy 5 enemy buildings!"*) and **three** are committed
globals. All three live under the document's **`globals`** object, **not** at its top level —
which is why the table above finds no mission-shaped top-level key and these three are
nonetheless committed content:

| global (`config["globals"][…]`) | value |
| --- | --- |
| `NUM_ACTIVE_MISSIONS` | `5` |
| `PERMISSION_PACK_UNITS` | `[10, 20, 30, 40]` |
| `PERMISSION_COSTS` | `{"10": 10, "20": 20, "30": 30, "40": 40}` |

`godot-mission-vocabulary` records all three as committed content and specifies that
**`NUM_ACTIVE_MISSIONS` is not turned into an active-mission bound** and that no cap, limit
or price is derived from any of them. This investigation does not derive one either. There
is no mission table, no chapter table, and no per-mission requirement, so there is nothing a
completion rule could be derived **from**. Deriving one would be invention.

## 7. The corpus does carry a mission pointer, and the type split is the writer's fingerprint

This is the finding that nearly went the other way, and it is the reason §9.3 exists.

| measurement | value |
| --- | --- |
| committed save documents with a `maps[0]` | **39** |
| of those, carrying `maps[0].idCurrentMission` | **39 / 39** |
| of those, carrying `maps[0].timestampLastChapter` | **39 / 39** |
| mission- or chapter-shaped `maps[0]` keys, union over all documents | exactly the two above |
| recorded types of `idCurrentMission` | **34 `int`**, **5 `str`** |
| distinct recorded values | `0` ×34, `'1'`, `'2'` ×2, `'3'`, `'23'` |

The five documents carrying a **string** are exactly the five carrying a **non-zero** value:

| document | `idCurrentMission` | type | `timestampLastChapter` |
| --- | --- | --- | --- |
| `Kiriakos.json` | `'1'` | `str` | `0` |
| `AcidCaos.json` | `'2'` | `str` | `1705746145` |
| `Scarlet.json` | `'2'` | `str` | `1688751780` |
| `Neutral.json` | `'3'` | `str` | `1705795693` |
| `Nerri.json` | `'23'` | `str` | `1672944733` |

That is a perfect correlation, and it is the fingerprint of `collect_mission`'s
`str(next_mission)`: a mission pointer advanced through the dedicated mission command is a
**string**, and one never advanced is the **integer** `0` the migration left behind. `'23'`
also corroborates the branch comment that chapters past 8 exist — the clamp is at `> 99`, not
at 8.

So the mission pointer is **real, populated, and progressed across the corpus** — and it is
still **read by nothing**. The corpus proves the field is exercised; it does not make the
field load-bearing. That distinction is the whole finding.

## 8. Every part is owned

Ownership is tested by **role name as well as source identifier**, because a closure claim is
only as strong as its ownership test. `docs/legacy-m10-death.md` §6.2 records the failure
that motivated this: a literal-identifier probe reported a door as unowned because its owner
described the behaviour by role and never used the branch's source name.

| component | owner | evidence |
| --- | --- | --- |
| the 64 `MISSION_*` names and their zero-consumer finding | `godot-mission-vocabulary` | requirement *"The zero-consumer finding is recorded structurally, not merely asserted"* (`spec.md:66`) |
| `idCurrentMission`, `timestampLastChapter` as reported state | `godot-quests` | `spec.md:8` *"the current mission identifier, the last-chapter instant"*; `spec.md:19` requires each *"reported exactly as recorded"* |
| both writers of the pointer, including the `set_quest_var` alias | `godot-quests` | `quest_envelope.py:150` lists `command.py:111, 438`; `:333` names the aliasing key |
| the only dedicated mission command, `collect_mission` | `godot-quests` | `spec.md:41, 63` |
| `complete_goal` mutating nothing | `godot-quests` | `spec.md:39`; `spec.md:3` *"the branch that mutates nothing"* |
| mission state not re-projected | `godot-mission-vocabulary` | requirement *"Mission state is owned by the quest capability and is not re-projected here"* (`spec.md:123`), scenario at `:149` |

**One precisely-scoped gap is closed by this document, and nothing else is.** The delivered
record states the zero-reader fact for the chapter **instant** — `quest_envelope.py:711-719`,
`NO_ELAPSED`: *"No legacy branch reads `timestampLastChapter` or any `questTimes` entry to
decide anything"* — but it does **not** state it for the mission **pointer**. The field table
implies it (2 occurrences, 2 lines, both writes), and implication is not the claim a closure
needs. §2 states it directly. No code, spec, or artifact changes with this closure.

## 9. Five measurement defects found while measuring this

### 9.1 A vacuous census that reported a confirmation

The `MISSION_*` declaration pattern anchored at column zero:

```
^(MISSION_[A-Z_0-9]+)\s*=        ->  0 names
^\s*(MISSION_[A-Z_0-9]+)\s*=     -> 64 names
```

The declarations are indented inside a class body at `constants.py:984`. With zero names
collected, the consumer loop ran zero iterations and printed *"MISSION_\* names with ANY
occurrence outside constants.py: 0"* followed by *"(none -- the zero-consumer finding
re-measures)"*. That line read as a **successful independent confirmation** of a delivered
finding. It was the absence of a subject, not the absence of a consumer.

The fixed probe prints the declaration count **and exits non-zero** if it is zero, so a
vacuous census can never again be reported as a clean one. This is the **second** vacuous or
wrong-subject census in this project after the `push_queue_unit2` regex that failed twice.

**The class recurred immediately afterwards, in the claim-verification script.** A local
variable holding one field's site list was **rebound** to another field's site list, so the
check *"every `idCurrentMission` site is a write"* silently ran against the
`timestampLastChapter` lines and returned a clean, plausible `False`. Nothing about the output
distinguished it from a real result — the same failure mode as the vacuous census above,
reached by a different route: not an empty subject list but a **wrong** one. Each field now
has its own variable, and the verification run reports **78 passing claims, 0 failures, and 3
recorded as not mechanically checkable** rather than silently counting the last group as
passing.

### 9.2 A branch span that swallowed the function tail

The dispatcher is an `elif` chain, which is **flat in source and nested in the AST**.
`ast.If.end_lineno` therefore runs to the end of the whole chain, so slicing `start-1:end`
gave **every** branch an end of line 956. First result: *"branches whose body mentions any
mission-state field: **61 of 63**"* — with `buy`, `move`, `sell`, `orient`, `expand`, and
`weekly_reward` all credited with touching `idCurrentMission` and `timestampLastChapter`.
The same bug reported *"branches that append to a ledger"* as **all 63**, every one of them
appending to `collections`.

Fixed by slicing each branch from its own line to the line before the next branch starts.
The true figure is **5 of 63**. This is the **fourth** branch-inventory census failure in
this project (`command ==` vs `cmd ==` twice, `push_queue_unit2` twice), and the fix is the
one that generalizes: import `verify_commands.extract_command_branches` rather than
re-deriving the inventory.

### 9.3 The wrong container, which inverted a corpus finding

The first corpus probe searched **`privateState`** for mission state and reported *"none: NO
committed save document carries mission state."* The mission fields are on **`maps[0]`**. The
correct figure is **39 of 39 documents carry both fields, and 5 of them carry a non-zero
pointer**.

This is the most consequential of the three, because the wrong answer was a clean, confident,
well-formatted absence — and it was absence in the direction that would have made the closure
*easier*. The evidence in §7 is the opposite: the field is exercised, populated, and typed
inconsistently by exactly the branch that writes it. A probe that reports an absence is not
self-checking, and this one would have shipped an unearned figure.

### 9.4 A detection pattern that under-counted the thing it was sent to find

The first ledger scan looked for a direct subscript append, `[key].append(`, and reported
**two** append sites. The true figure is **three**. The missed one is `darts_shoot_balloon`,
whose append goes through a **local alias**:

```python
targets = privateState["dartsBalloonsShot"]     # command.py:598
if index not in targets:
    targets.append(index)                       # command.py:600
```

The alias is two lines above the append and is what makes the pattern blind. This is the
same failure direction as §9.3 — an under-count rather than an over-count — and it is the
more seductive of the two, because a **smaller** set of completion ledgers is a *tidier*
closure. A detection rule that misses sites cannot be validated by its own output: it
reported a confident "2" with no indication that a third existed. It was caught only because
the figure was cross-read against the branch bodies by hand. The fixed rule resolves the
alias first and then matches the append, and the check now asserts **both** the count and
the resolved target of each site.

### 9.5 The ownership check failed in exactly the way §8 warns about

The first ownership probe demanded the literal string `NUM_ACTIVE_MISSIONS` inside
`godot-mission-vocabulary`'s spec and reported the globals as **unowned**. That spec names
all three globals by **role** — *"the active mission count, the permission pack unit list,
and the permission cost table"* (`spec.md:97-98`) — because it reads them through the
normalized content registry and must not re-transcribe their key names. The committed name
lives only in the client module, as `GLOBAL_ACTIVE_MISSION_COUNT := "NUM_ACTIVE_MISSIONS"`.

This is `docs/legacy-m10-death.md` §6.2 recurring **inside this very document**, which is the
strongest available evidence that the warning is worth writing down: the failure is not a
mistake one makes once, it is the default behaviour of a literal grep against prose
specifications. The probe now matches role names as well as identifiers, and a claim of
ownership is only recorded when at least one of the two matches.

## 10. The closure

`mission completion` is **CLOSED BY MEASUREMENT**. There is no undelivered surface, for four
independently sufficient reasons:

1. **No vocabulary consumer.** 64 declarations, 0 occurrences outside `constants.py`.
   Owned by `godot-mission-vocabulary`, which specifies the re-measurement.
2. **No reader of the mission pointer.** 2 writers, 0 readers; `timestampLastChapter`
   likewise 2 writers, 0 readers. Owned by `godot-quests`, with the pointer's zero-reader
   fact added by §8.
3. **No mechanism.** `complete_goal` mutates nothing; the two combat branches a completion
   would hook touch no mission state; there is no completion ledger; 58 of 63 branches touch
   no mission state at all. Owned by `godot-quests`.
4. **No content.** No mission or chapter table among the 20 committed keys; the 91 `goals`
   entries never mention a chapter and their `reward` is uniformly `10`; the three
   mission-adjacent globals are reported and unenforced by specification.

Nothing in M10 remains undelivered except **`rewards`**, the milestone's last deliver item.
It is **not** pre-authorised, and `weekly_reward` (`command.py:345-363`) and
`win_daily_bonus` (`command.py:444-463`) both **mutate state and grant a client-sent item id**
— so on the evidence of this investigation it is a plausible real surface rather than
another closure, and it requires its own committed investigation.

## 11. Claim limits

- This is a statement about the **preserved server**, measured over eleven top-level legacy
  modules. It says nothing about what the Flash client did with any of it, and no claim is
  made about what a player ever saw.
- **No mission completion is implemented, and none is claimed to have existed.** The verdict
  is that there is nothing to reproduce, not that a feature was left out.
- The `elapsed`/`ready`/completion vocabulary is **not** translated into English state words
  anywhere, because nothing selects a state for a translation to name.
- `NUM_ACTIVE_MISSIONS = 5` is **not** turned into an active-mission bound, a concurrency
  limit, or a cap, and `PERMISSION_PACK_UNITS` / `PERMISSION_COSTS` are **not** turned into a
  price. All three remain reported content only.
- The numbering gaps `[9, 10, 20, 57]` are **reported and never closed**; nothing is
  synthesised to fill one. The two overlapping declaration families are reported unresolved,
  with no preferred member.
- The corpus type split in §7 is a **correlation with one writer**, not a proven provenance.
  `set_quest_var` writes the pointer from unvalidated client input and could in principle
  produce an integer; the committed corpus happens to contain no such document. The claim is
  that all five **strings** are non-zero and all **thirty-four integers** are zero.
- The `> 99` clamp and the 1–8/9+ chapter commentary are reproduced here as **recorded
  behaviour**. No chapter schedule, duration, or unlock rule is derived from them, and none
  exists to derive.
- **Ownership is established by role name as well as source identifier.** A capability that
  described mission state without naming either key would not have been found by this probe,
  and that limitation is inherited deliberately from `docs/legacy-m10-death.md` §6.2.
- §2's correction to `docs/legacy-m10-missions.md` narrows a prose sentence. It changes no
  delivered code, spec, or test, and `openspec validate --all --strict` is unchanged.
- No executed-legacy fixture is captured and none is fabricated: there is no mission
  completion behaviour for the legacy server to have.
- **No Flash, Ruffle, ActionScript, or browser executes** in any measurement in this
  document, and **no network is used**.