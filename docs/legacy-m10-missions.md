# The M10 mission investigation — mission loading and mission state

**Date:** 2026-10-05
**Milestone:** M10 — Missions and Combat
**Scope of this record:** the **first** M10 objective in roadmap and dependency
order, *mission loading / mission state*.
**Status:** investigation only. This document proposes no implementation.

---

## 0. Summary

The measurement overturns the premise of the objective in a useful way.

**M10's "mission state" half is already delivered.** The legacy server has
**exactly one** mission-mutating command, `collect_mission`, and the `godot-quests`
line already delivers it — with a captured executed-legacy fixture, a
content-independent projection of all three mission save fields, and two spec
requirements that name its stringification divergence.

**M10's "mission loading" half has no oracle at all.** There is no
mission-loading command, and **no mission map exists**: every one of the **10**
committed save documents holds `maps` of length **1** with `default_map` `0`.

What remains undelivered is therefore **not behaviour but vocabulary**: a
**64-constant** mission-type enumeration with **zero consumers**, and **three**
committed mission-adjacent globals with **zero consumers**. That is a real,
bounded, evidence-backed content line of exactly the shape M8's `unit-definitions`
line established, and it is the line this investigation recommends. It also
carries direct value for the later M10 combat lines, because the vocabulary
**names the combat events the game recognised** while nothing reads them.

Two corrections to my own first pass are recorded in §8 rather than quietly
fixed: the constant count is **64**, not the 63 a raw grep suggested, and the
three "consumer" sites a first classifier reported are **substring artifacts**.

---

## 1. Method

Counts, not impressions. Every figure below was produced by a script over the
**eleven legacy root modules** (3,833 lines) or over the committed corpus, and
each is reproducible from the committed tree:

| question | method |
| --- | --- |
| which commands touch missions | case-insensitive `mission` sweep over all 11 modules |
| do the mission constants have consumers | every occurrence of every `MISSION_*` name, minus its own definition line |
| read vs write on mission fields | classify every occurrence of the field key as write or read |
| does mission content exist | `config/main.json` key sweep + the normalized packages |
| is there a mission map | map multiplicity across every committed save |
| numbering integrity | value extraction, duplicate and gap analysis |

Scope note: the mission constants live in **legacy `constants.py`**, not in the
normalized content package. That distinction matters — it is a legacy source
vocabulary, not committed content — and §6 records what the normalized package
does and does not carry.

---

## 2. The one mission command, and it is already delivered

`command.py:430-442` is the entirety of mission mutation:

```python
elif cmd == "collect_mission":
    next_mission = args[0]
    if next_mission > 99:
        # chapters 1 - 8 are scripted
        # starting chapters 9+ works, the game has 90 entries so there's technically infinite chapters
        # so I'm not sure what to do, so I'm going to allow a restart after chapter 99, the next chapter will be 1
        next_mission = 1

    map["idCurrentMission"] = str(next_mission)
    map["timestampLastChapter"] = time_now
    map["currentQuestVars"] = {}

    print("Advanced to mission", str(next_mission))
```

Measured properties:

- the mission number is `args[0]`, **entirely client-supplied**;
- the only guard is an **upper** bound (`> 99`) with **no lower bound** and **no
  type check**, so a client-sent string or boolean reaches `str()` unchecked;
- it writes **three** fields, and resets `currentQuestVars` to `{}`;
- it **reads nothing** — no mission state is consulted to decide anything.

**The overlap with M9 is total.** `collect_mission` is one of the six quest
branches the `godot-quests` line delivered, and:

| evidence | where |
| --- | --- |
| spec requirement naming the stringification divergence | `openspec/specs/godot-quests/spec.md:41`, `:62-63` |
| captured executed-legacy transaction | `tests/fixtures/godot-quests/steps/command_collect_mission/` |
| envelope, service route, client flow, live phase | `quest_envelope.py`, `compat_service.py`, `quest_flow.gd`, `quests-live` |

The one other mission write is `command.py:111`, inside `set_quest_var`'s
`if key == "id":` arm — also delivered by `godot-quests`.

**Nothing about mission state is left to build.**

---

## 3. The mission save fields are write-only

| field | writes | reads | write sites |
| --- | --- | --- | --- |
| `idCurrentMission` | **2** | **0** | `command.py:111`, `command.py:438` |
| `timestampLastChapter` | **2** | **0** | `command.py:439`, `command.py:911` |
| `currentQuestVars` | 3 | 2 | `command.py:114`, `:116`, `:440`; reads at `:107`, `:113` |

Two consequences worth recording:

1. **`idCurrentMission` has zero readers.** Nothing ever consults the current
   chapter to gate anything, so advancing it changes nothing a player can do.
   This is the same write-only shape M9 established for the research counters.
2. **`timestampLastChapter` is client-writable.** Its second write is
   `command.py:911`, inside `fast_forward`, which subtracts a **client-supplied**
   number of seconds — so the chapter instant is not server-authoritative, and is
   already recorded as such by `godot-quests` (spec line 157 names the last-chapter
   instant among the fields a client can move).

The two `currentQuestVars` reads are the self-heal at `:113` and a dead local
alias at `:107` (`questVars` is assigned and never used again). Neither is a
consumer, and §3 of the M9 closure already examined both.

**Corpus state, already projected verbatim** by `godot-quests` (spec lines 8–9):
`idCurrentMission` `0`, `timestampLastChapter` `0`, `currentQuestVars` `None`.

---

## 4. There is no mission map and no mission loading

This was the premise most likely to be wrong, so it was measured directly.

**Every** committed save document holds exactly **one** map:

| save | `maps` | `default_map` |
| --- | --- | --- |
| `tests/saves/fresh-player-pre-migration.json` | 1 | 0 |
| `tests/saves/fresh-player.json` | 1 | 0 |
| `villages/AcidCaos.json` | 1 | 0 |
| `villages/General_Mike_30.json` | 1 | 0 |
| `villages/General_Mike_31.json` | 1 | 0 |
| `villages/Kiriakos.json` | 1 | 0 |
| `villages/Nerri.json` | 1 | 0 |
| `villages/Neutral.json` | 1 | 0 |
| `villages/Scarlet.json` | 1 | 0 |
| `villages/initial.json` | 1 | 0 |

There is **no** command that loads, creates, or switches a mission map. The
dispatcher resolves a map by client-supplied index at `command.py:37`
(`map = save["maps"][map_id]`), and with a single-element `maps` list any
`map_id` other than `0` is an out-of-range access — a structural fact, recorded
here and deliberately **not** turned into a new refusal, because inventing a
bounds rule the oracle lacks would fabricate behaviour.

So a "mission" in this codebase is **not** a place to load. It is a single
integer chapter counter on the player's own single map.

---

## 5. The vocabulary: 64 constants, zero consumers

`constants.py:984-1047` defines **64** `MISSION_*` constants with **64 distinct
values** spanning **0..67** and **no duplicates**. The numbering has **four gaps:
`9`, `10`, `20`, `57`.**

**Zero occurrences of any `MISSION_*` name exist outside `constants.py`.** The
vocabulary is entirely unread: no branch dispatches on a mission type, no save
field stores one, and no response echoes one.

The vocabulary nonetheless carries real content, and this is the finding that
makes a bounded line worth proposing. It is a **client-event vocabulary**: it
names what the game considered a trackable mission event. Among the 64:

- **combat** — `MISSION_ATTACK_PLAYER` (37), `MISSION_ATTACK_FRIEND` (38),
  `MISSION_CAPTURED_SUBCATFUNC`/`_ID` (11, 12), `MISSION_ASSAULTS_WON` (46),
  `MISSION_WIN_ASSAULTS_SAME_LEVEL` (58),
  `MISSION_WIN_ASSAULTS_MORE_LEVEL` (59), `MISSION_REVENGE_ASAULT` (60),
  `MISSION_COORDINATED_ATTACK` (61), `MISSION_DEFEAT_ALL_TROLLS` (30),
  `MISSION_KILL_TOWER_WITH_SCORPION` (66), `MISSION_KILLED_ENEMY` (67),
  `MISSION_SACRIFICE_UNIT` (63), `MISSION_PROTECT_WITH_WALLS` (51)
- **economy** — `MISSION_EXPAND` (24), `MISSION_MARKET_TRADE` (40),
  `MISSION_STORE_SUBCATFUNCS`/`_ID` (41, 42), `MISSION_PLACE_STORED_ITEM` (62)
- **units** — `MISSION_TRAIN_IDS_IN_ID` (55), `MISSION_CONVERT_UNIT` (64),
  `MISSION_POP_UNIT_SUBCATFUNC` (48), `MISSION_MOVE_UNITS` (18)
- **social** — `MISSION_HELP_FRIENDS` (23), `MISSION_GIFT_SEND` (35),
  `MISSION_SPY_PLAYER` (45), `MISSION_RECRUIT_MARKET_FRIEND` (32),
  `MISSION_COMPLETE_SOCIAL_SUBCAT`/`_ID` (43, 44)

Two internal oddities are content facts, reproduced rather than normalised:

- **17 `MISSION_DESTROYED`** sits between 16 `MISSION_DESTROYED_ID` and 18
  `MISSION_MOVE_UNITS` — a near-duplicate of the 15/16 pair with no distinct use.
- **31 `MISSION_COMPLETE_QUEST_IN_MAP`** and **47 `MISSION_COMPLETE_QUEST`** are
  two spellings of one idea, with no committed rule reconciling them.

**This vocabulary is the single most useful artifact for scoping M10's later
lines.** It says what the game *named* — and, because nothing reads it, it
justifies no behaviour whatsoever. Recording the combat names is how a later
combat line can say "the oracle named this event and never implemented it"
instead of inventing a trigger.

---

## 6. Committed content

`config/main.json` has **no** top-level mission key. Four nested hits exist:

| location | value | legacy consumers |
| --- | --- | --- |
| `goals` (array of objects) | quest text mentioning missions | the `quests` line |
| `globals.NUM_ACTIVE_MISSIONS` | `5` | **zero** |
| `globals.PERMISSION_PACK_UNITS` | `[10, 20, 30, 40]` | **zero** |
| `globals.PERMISSION_COSTS` | keys `10, 20, 30, 40` | **zero** |

All three globals are normalized (present in
`packages/game-content/normalized/globals.json`), so they are committed content
— and all three have **zero** legacy consumers. `NUM_ACTIVE_MISSIONS` = `5` is
the most suggestive: it implies a cap on concurrent missions that **nothing
enforces**.

The `MISSION_*` constants are **not** in the normalized package; they exist only
in legacy `constants.py`. One committed quest (`legacy_id` `40`) mentions a
mission in its text.

So the committed content picture is: **three zero-consumer globals, one quest
whose prose mentions missions, and no mission table whatsoever.**

---

## 7. Verdict and the bounded line that is supported

| M10 first objective | verdict |
| --- | --- |
| mission **state** | **already delivered** by `godot-quests`, with a captured executed-legacy fixture |
| mission **loading** | **no oracle** — no command, no mission map, single map in all 10 saves |
| mission **vocabulary** | **undelivered**, 64 constants + 3 globals, **zero consumers** |

**Recommended bounded line: the mission vocabulary.** Deliver a typed, read-only
projection of the 64 committed `MISSION_*` constants and the three committed
mission-adjacent globals, reporting names, values, and gaps **verbatim**; record
the zero-consumer finding structurally; and derive **no** behaviour, trigger,
unlock, reward, or completion rule. This is the same shape as M8's
`unit-definitions` line — committed vocabulary the client verifies — and it is the
only undelivered mission surface the oracle supports.

**Deliberately not proposed:**

- any mission-loading mechanism (no oracle);
- any mission completion or reward (the vocabulary has no consumer, and the M9
  lesson is that inventing a schedule is not a migration);
- any enforcement of `NUM_ACTIVE_MISSIONS` (committed, unread);
- a map-index bounds refusal for `command.py:37` (recorded, not invented);
- a second capture of `collect_mission` (already captured by `godot-quests`).

**On an executed-legacy fixture:** not needed for a vocabulary line, because
there is no behaviour to capture — the same finding that removed the fixture from
M8's movement and animations lines. `collect_mission` itself **is** capturable
and **has already been captured**; no player state need be fabricated, because
the committed corpus carries real mission state.

---

## 8. Corrections this investigation makes to itself

Recorded rather than quietly fixed, per the project's standing practice.

1. **The constant count is 64, not 63.** A raw case-insensitive grep for
   `mission` returns 71 lines; the first arithmetic on that implied 63
   constants. Extracting definitions by pattern gives **64**
   (`constants.py:984-1047`), each with a distinct value.
2. **Three "consumer" sites are substring artifacts.** A first classifier
   reported consumers at `constants.py:997`, `:998`, and `:1012`. All three are
   *inside the constant list*: `MISSION_DESTROYED` is a **prefix** of
   `MISSION_DESTROYED_SUBCATFUNC` and `MISSION_DESTROYED_ID`, and
   `MISSION_COMPLETE_QUEST` is a prefix of `MISSION_COMPLETE_QUEST_IN_MAP`. The
   decisive check is that **zero** `MISSION_*` occurrences exist outside
   `constants.py` at all. This is the same substring-artifact pattern M8 found in
   the animation-vocabulary sweep.
3. **"Mission loading" does not mean loading a mission.** The brief's framing
   invited a mission-map reading; measurement shows the concept is a chapter
   counter on the player's own single map, so the loading half has no oracle.
4. A measurement-tooling trap worth recording: an inspection script opened files
   in **text mode**, which silently translated CRLF to LF and briefly made a
   CRLF working tree look LF-only. Every file is now read as **bytes** before any
   write, and every edit asserts its anchor matches exactly once before
   replacing.

---

## 9. Claim limits

- **This document delivers no code and no behaviour.** It is a contract for a
  possible line, not an implementation of one.
- **"Zero consumers" means zero occurrences outside the definitions**, not zero
  conceptual relevance. The vocabulary names real events; nothing dispatches on
  them.
- The `idCurrentMission` upper-bound guard (`> 99`) was read from source and is
  **derived-provisional** — it was established by earlier executed probes under
  the `quests` line, and no probe was re-run here.
- The corpus figures describe the **committed** save documents only. A save with
  `maps` of length greater than one would change §4's conclusion, and none is
  committed.
- The three globals' **values** are committed and reported verbatim; their
  intended meaning (a cap, a pack size, a price) is **not** derived, because
  nothing reads them.
- The four numbering gaps and the two near-duplicate pairs are reported as
  content, **not** normalised, deduplicated, or renumbered.
- No Flash, Ruffle, ActionScript, or browser executed, and no network was used,
  in producing this record.
