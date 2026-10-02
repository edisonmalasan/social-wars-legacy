#!/usr/bin/env python3
"""Derivation of the six legacy quest-command envelopes and the quest model.

M9 line 2 (``quests``) — the largest M9 surface: **six** undelivered branches,
one of which mutates nothing at all and one of which destroys player state from a
**client-computed** count.

What legacy actually does (established — ``docs/legacy-m9-quests.md`` §1–§6,
re-measured against the committed source by the hermetic suite in the same run)
    ====================== ========= ==============================================
    branch                  lines    effect on the player's quest state
    ====================== ========= ==============================================
    ``set_goals``           68-74    delegates to ``engine.py:96-100``: stores a
                                      **client-sent** ``[visited, currentStep]``
                                      pair and grows the list ON DEMAND
    ``complete_goal``       76-79    **NOTHING AT ALL** — resolves the committed
                                      title, prints it, returns
    ``set_quest_var``       87-117   writes **any** client-invented key into
                                      ``currentQuestVars``; ``id`` also aliases
                                      ``idCurrentMission``; ``idSimpleChapter`` is
                                      **explicitly ignored**
    ``collect_mission``     430-442  writes a **stringified** mission id, stamps
                                      ``timestampLastChapter``, **clears**
                                      ``currentQuestVars``, and **wraps** above 99
    ``admin_set_quest_rank`` 745-750 ``privateState["questsRank"][str(index)] = difficulty``,
                                      both client-sent, no bound
    ``end_quest``           752-806  ``map["questTimes"][str(quest_id)] = time_now``,
                                      **and destroys rows** by a **client-computed**
                                      ``lost = max(0, unit[2] - unit[3])``
    ====================== ========= ==============================================

**`complete_goal` writes NOTHING (design D3).**  It reads a goal id, resolves the
committed title through ``get_attribute_from_goal_id``, prints it, and returns.
A goal "completes" by being narrated in a ``print`` statement.  The branch is
therefore **delivered as a no-op on purpose**: the endpoint executes the real
branch, the post-execution proof requires the **whole** quest state to be
byte-identical, and the suite asserts the absence of any completion flag,
ledger, or accessor so the claim is mechanical rather than a promise.

**`end_quest`'s destruction count is REFUSED and the refusal is a DIVERGENCE
(design D2).**  The legacy branch parses one client-authored JSON blob, reads
``win``, ``duration``, ``units``, ``map``, ``difficulty``, ``voluntary_end`` and
``quest_id`` from it, and then destroys placed rows through ``map_lose_item``
(``command.py:796``) using a count the **client** computed.  Reproducing that is
exactly the anti-pattern ``AGENTS.md`` names as "Bad" — a client dictating an
authoritative outcome.  This line therefore derives the blob **server-side** with
``units`` as an **empty list**: the destruction loop
``for unit in units:`` (``command.py:790``) iterates zero times, ``map_lose_item``
is never reached, and every placed row is left **byte-identical** — proved over
the **complete** ``items`` mapping, never a selected subset.  The legacy server
DOES destroy rows on this command, so the difference is recorded as a
**divergence**, not as achieved parity.  ``capture_quest_fixture.py`` probe 4
executes the legacy destruction against the live server so the divergence is
evidenced rather than asserted.

**No quest reward is paid and no stored resource moves (design D6).**  Only the
committed ``id`` and ``title`` fields are read by anything: ``reward`` has
**zero** legacy consumers and is **uniformly the value ``10``** on all **91**
entries, so it carries no information even if it were read.  ``do_command``
applies the request's per-command resource vector **before** dispatch
(``command.py:40``, ``engine.py:251-271``), so any price a client attached would
be a client-trusted mint or burn: the derived vector is **NEUTRAL** and every
action's post-execution proof requires that **every** stored resource be
**unchanged**.

**No bound, membership test, or clamp is added except the two the legacy branches
themselves apply (design D4/D5).**  ``set_goals`` grows the goals list on demand
with **no upper bound** — ``set_goals(500)`` appends 350 entries — and that
absence is reproduced and recorded as a Server v1 / M13 gap, never silently
closed.  ``set_quest_var`` accepts **any** key against the eight its own comment
enumerates (``command.py:97-106``); inventing a closed set of eight would reject
keys the legacy server happily persisted.  The one key the branch **itself**
ignores — ``idSimpleChapter`` (``command.py:91-95``) — is refused here too,
because that is a recorded legacy behaviour rather than an absence.

**The two type facts are REPRODUCED, not normalized (design D8).**  The corpus
records ``idCurrentMission`` as an **integer** ``0`` while ``collect_mission``
writes a **string** (``command.py:438``), and the corpus records
``currentQuestVars`` as a recorded **``None``** which both ``set_quest_var``
(``command.py:113-114``) and ``collect_mission`` (``command.py:440``) convert to
a dict as a side effect.  Normalizing either would hide a real legacy shape
divergence; both are reproduced and asserted.

**`unlockedQuestIndex` is REPORTED and NEVER WRITTEN (design D7).**  It has
**zero** legacy sites across the seven modules, so it is projected as content and
consumed by nothing — the **ninth** zero-consumer committed field in this
project.

**`fast_forward` is RECORDED as a quest-state writer and delivered NOT AT ALL
(design D9).**  It subtracts a **client-supplied** number of seconds from every
``questTimes`` entry (``command.py:942-944``) and from ``timestampLastChapter``
(``command.py:911``), making quest timing client-writable for the same reason
research timing is: nothing reads it.  ``version.py:38-44`` initializes
``questTimes`` from ``None`` to ``{}`` — a **migration path**, not gameplay.

**`map_lose_item` is one of the dead-hero ledger's doors (design D10).**
``engine.py:215-228`` calls ``push_dead_unit`` at line **223**, and its only
**two** callers are ``command.py:796`` inside ``end_quest`` (``command.py:
752-806``) and ``command.py:872`` inside ``end_attack``.  This line's refusal
removes the quest-side reach from the modern service, and the record says so, so
the ledger owner and the quest owner describe the same relationship the same
way.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field``, and
    ``EnvelopeError`` — so every delivered derivation, its fixture, and its
    suite keep passing untouched.

The committed corpus target
    ``tests/saves/fresh-player.json`` holds ``privateState["goals"]`` with
    **151** entries **all ``None``**, ``questsRank`` ``{}``,
    ``unlockedQuestIndex`` ``0``, ``maps[0]["currentQuestVars"]`` **``None``**,
    ``maps[0]["questTimes"]`` ``{}``, ``maps[0]["idCurrentMission"]`` **integer**
    ``0``, and ``maps[0]["timestampLastChapter"]`` ``0``.  Every one of the six
    branches is therefore exercisable against the corpus **as committed**, with
    **no fabricated player state**.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

# One shared derivation.  The placement module is imported unchanged — nothing
# here is renamed, moved, or re-implemented.
from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    data_field,
    is_strict_int,
    parse_data_field,
    payload_json,
)

# ------------------------------------------------------------ the state --
# The three committed private-state keys a quest occupies, and the four map
# keys.  Established by MEASUREMENT over the seven legacy modules, counted as
# QUOTED occurrences so a comment can never be mistaken for code, and
# re-measured by the hermetic suite in the same run:
#   goals                 3 occurrences / 3 lines (engine.py:97 write;
#                        get_game_config.py:142,146 are the committed CONFIG
#                        table, not the save)
#   questsRank            1 / 1  (command.py:750)
#   unlockedQuestIndex    0 / 0
#   currentQuestVars      5 / 5  (command.py:107,113,114,116; 440)
#   questTimes            6 / 6  (command.py:802, 942; version.py:39,40,41,43)
#   idCurrentMission      2 / 2  (command.py:111, 438)
#   timestampLastChapter  3 / 2  (command.py:439; command.py:911 carries the
#                        token TWICE, reading and writing it in one expression)
#
# MEASURED CORRECTION: the committed investigation records TWO sites for
# timestampLastChapter.  That is a correct DISTINCT-LINE count and an
# incomplete OCCURRENCE count; both are recorded here and asserted separately
# rather than silently reconciled, following the precedent M9 line 1 set by
# counting occurrences per line and recording the two counts separately.
KEY_GOALS = "goals"
KEY_RANKS = "questsRank"
KEY_UNLOCKED_INDEX = "unlockedQuestIndex"
PRIVATE_KEYS: Tuple[str, str, str] = (KEY_GOALS, KEY_RANKS, KEY_UNLOCKED_INDEX)

KEY_QUEST_VARS = "currentQuestVars"
KEY_QUEST_TIMES = "questTimes"
KEY_MISSION = "idCurrentMission"
KEY_LAST_CHAPTER = "timestampLastChapter"
MAP_KEYS: Tuple[str, str, str, str] = (
    KEY_QUEST_VARS,
    KEY_QUEST_TIMES,
    KEY_MISSION,
    KEY_LAST_CHAPTER,
)

#: The seven quest fields, in the order the projection reports them.
QUEST_FIELDS: Tuple[str, ...] = (
    KEY_GOALS,
    KEY_RANKS,
    KEY_QUEST_VARS,
    KEY_QUEST_TIMES,
    KEY_MISSION,
    KEY_LAST_CHAPTER,
    KEY_UNLOCKED_INDEX,
)

# ------------------------------------------------------------ commands --
SET_GOALS_COMMAND = "set_goals"
COMPLETE_GOAL_COMMAND = "complete_goal"
SET_QUEST_VAR_COMMAND = "set_quest_var"
COLLECT_MISSION_COMMAND = "collect_mission"
ADMIN_SET_QUEST_RANK_COMMAND = "admin_set_quest_rank"
END_QUEST_COMMAND = "end_quest"
QUEST_COMMANDS: Tuple[str, ...] = (
    SET_GOALS_COMMAND,
    COMPLETE_GOAL_COMMAND,
    SET_QUEST_VAR_COMMAND,
    COLLECT_MISSION_COMMAND,
    ADMIN_SET_QUEST_RANK_COMMAND,
    END_QUEST_COMMAND,
)
FAST_FORWARD_COMMAND = "fast_forward"

# The endpoint's own action vocabulary.  **Closed**: ``fast_forward`` is
# deliberately ABSENT (design D9), because its ``seconds`` argument is
# client-supplied and no evidence constrains what a client sends.
ACTION_SET_GOAL = "set_goal"
ACTION_COMPLETE_GOAL = "complete_goal"
ACTION_SET_QUEST_VAR = "set_quest_var"
ACTION_COLLECT_MISSION = "collect_mission"
ACTION_SET_QUEST_RANK = "set_quest_rank"
ACTION_END_QUEST = "end_quest"
ACTIONS: Tuple[str, ...] = (
    ACTION_SET_GOAL,
    ACTION_COMPLETE_GOAL,
    ACTION_SET_QUEST_VAR,
    ACTION_COLLECT_MISSION,
    ACTION_SET_QUEST_RANK,
    ACTION_END_QUEST,
)
ACTION_COMMANDS = {
    ACTION_SET_GOAL: SET_GOALS_COMMAND,
    ACTION_COMPLETE_GOAL: COMPLETE_GOAL_COMMAND,
    ACTION_SET_QUEST_VAR: SET_QUEST_VAR_COMMAND,
    ACTION_COLLECT_MISSION: COLLECT_MISSION_COMMAND,
    ACTION_SET_QUEST_RANK: ADMIN_SET_QUEST_RANK_COMMAND,
    ACTION_END_QUEST: END_QUEST_COMMAND,
}

#: How each action is addressed — the ONE value a client may name, because it is
#: the branch's own addressing and never an outcome.  Everything else is derived.
ACTION_ADDRESSING = {
    ACTION_SET_GOAL: "goal index",
    ACTION_COMPLETE_GOAL: "goal index",
    ACTION_SET_QUEST_VAR: "quest-variable key",
    ACTION_COLLECT_MISSION: "mission identifier",
    ACTION_SET_QUEST_RANK: "rank index",
    ACTION_END_QUEST: "quest identifier",
}

#: The client-sent request key carrying each action's addressing.  The intent body
#: is exactly ``user_id`` + ``action`` + this key, so no other value is even
#: expressible.
ACTION_ADDRESSING_KEY = {
    ACTION_SET_GOAL: "goal_index",
    ACTION_COMPLETE_GOAL: "goal_index",
    ACTION_SET_QUEST_VAR: "key",
    ACTION_COLLECT_MISSION: "mission",
    ACTION_SET_QUEST_RANK: "quest_index",
    ACTION_END_QUEST: "quest_id",
}

# ------------------------------------------------------------- derived --
#: The progress pair the service writes for ``set_goals``.  The legacy branch
#: stores whatever the client sent (``progress = json.loads(args[1])``) and
#: reads **none of it** back: ``goals`` has three sites, one write
#: (``engine.py:100``) and two in the committed CONFIG table
#: (``get_game_config.py:142,146``), never the save.  A ``[0, 0]`` pair asserts
#: **no** progress at all, which is the only honest derivation, and it cannot
#: change any authoritative outcome because nothing consumes the pair.
DERIVED_PROGRESS: Tuple[int, int] = (0, 0)
DERIVED_PROGRESS_NOTE = (
    "The zero pair. The legacy branch persists whatever the client sends and "
    "reads none of it back, so a client-sent progress pair cannot influence any "
    "outcome the server computes. Deriving [0, 0] asserts NO progress rather "
    "than inventing one, exactly as M9 line 1 derived DERIVED_CASH = 0 for the "
    "discarded research price: a derived value that claims nothing, in place of "
    "a client value that could claim anything"
)

#: The value the service writes for a quest variable.  ``True`` is a **marker**,
#: not a claim: the legacy branch stores ``currentQuestVars[key] = value``
#: verbatim (``command.py:116``) and all five ``currentQuestVars`` sites are
#: writes or the chapter clear, so the stored value is read by nothing.
DERIVED_QUEST_VALUE: Any = True
DERIVED_QUEST_VALUE_NOTE = (
    "A constant marker, not a quest value. The branch persists whatever the "
    "client sends and reads it back NOWHERE - all five currentQuestVars sites "
    "are writes or the chapter clear - so the service writes a constant that "
    "asserts nothing rather than a client value that could assert anything. The "
    "client-sent value is IGNORED, exactly as a client-sent amount or price is "
    "ignored elsewhere in this project"
)

#: The rank difficulty the service writes.  ``admin_set_quest_rank`` applies no
#: bound of its own (``command.py:745-750``), so the derived value is the FLOOR
#: of the only difficulty clamp in the six branches — ``max(1, min(3, ...))`` at
#: ``command.py:782`` inside ``end_quest`` — which is a committed, non-client
#: number rather than an invented one.
DERIVED_DIFFICULTY = 1
DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 3
DERIVED_DIFFICULTY_NOTE = (
    "admin_set_quest_rank writes a CLIENT-SENT difficulty with no bound at all "
    "(command.py:750). The derived value is 1, the FLOOR of the only difficulty "
    "clamp any of the six branches contains - max(1, min(3, ...)) at "
    "command.py:782 - so the number is taken from committed source rather than "
    "invented, and no client number is persisted"
)

#: The `end_quest` blob the service derives, server-side, in full.  ``units`` is
#: an EMPTY list and that empty list **IS** the refusal (design D2): the legacy
#: destruction loop `for unit in units:` (command.py:790) iterates zero times,
#: so `map_lose_item` is never called and every placed row is byte-identical.
DERIVED_UNITS: Tuple[Any, ...] = ()
DERIVED_DURATION = 0
DERIVED_MAP = 0
DERIVED_WIN: Any = True
DERIVED_VOLUNTARY_END: Any = True
DERIVED_DIFFICULTY_FIELD = DERIVED_DIFFICULTY

END_QUEST_REFUSAL = (
    "THE DESTRUCTION COUNT IS REFUSED, AND THE DIFFERENCE FROM THE LEGACY SERVER "
    "IS A DIVERGENCE, NOT PARITY. The legacy branch parses ONE client-authored "
    "JSON blob and destroys placed rows through map_lose_item (command.py:796) "
    "using a count the CLIENT computed: `lost = max(0, unit[2] - unit[3])` "
    "(command.py:792). This service derives the blob server-side with `units` as "
    "an EMPTY LIST, so the destruction loop iterates zero times, map_lose_item is "
    "never reached, and every placed row is left byte-identical - proved after "
    "execution over the COMPLETE items mapping. What the endpoint accepts is the "
    "quest identifier and nothing else: the client-supplied `units`, `lost`, "
    "`duration`, `map`, `difficulty`, `win`, and `voluntary_end` are all ignored, "
    "and the values the legacy branch only PRINTS (command.py:803-806) are "
    "derived rather than trusted. This is the single place in this repository "
    "where the modern service deliberately does NOT reproduce legacy behaviour, "
    "and it is recorded here rather than left for a reader to infer"
)

#: The one key the legacy ``set_quest_var`` branch EXPLICITLY ignores
#: (``command.py:91-95``).  Refusing it reproduces a legacy behaviour rather
#: than inventing a membership rule (design D5).
QUEST_VAR_IGNORED_KEY = "idSimpleChapter"

#: The key that ALSO aliases ``map["idCurrentMission"]`` (``command.py:110-111``).
QUEST_VAR_ALIAS_KEY = "id"

#: The eight keys the branch's OWN comment enumerates (``command.py:97-106``).
#: Recorded as CONTENT and enforced **nowhere**: there is no membership test in
#: the branch, and a client-invented key is accepted and persisted (design D5).
QUEST_VAR_COMMENT_KEYS: Tuple[str, ...] = (
    "id",
    "spawned",
    "ended",
    "visited",
    "activators",
    "boss",
    "treasure",
    "killed",
)
QUEST_VAR_COMMENT_NOTE = (
    "RECORDED AS CONTENT AND NEVER ENFORCED, SO THE ACCEPTED SET IS UNBOUNDED. "
    "The legacy branch's own comment (command.py:97-106) enumerates these eight "
    "keys, and there is NO membership test anywhere in it: a client-invented key "
    "is accepted and persisted, which is what the endpoint reproduces (design "
    "D5). Inventing a closed set of eight would reject keys the legacy server "
    "happily stored, which would make this service STRICTER than legacy in the "
    "unexamined direction. The ONE key that is refused is the one the legacy "
    "branch itself ignores: "
    + QUEST_VAR_IGNORED_KEY
    + " (command.py:91-95), where the source's own comment explains the game "
    "resets chapters past 9 and the key is dropped so a player can reach "
    "chapter 99"
)

#: The chapter wrap bound (``command.py:432-436``).  A wrap, **not** a
#: rejection: the source's own comment admits uncertainty past chapter 99.
MISSION_WRAP_BOUND = 99
MISSION_WRAP_TARGET = 1
MISSION_WRAP_NOTE = (
    "A WRAP, NOT A REJECTION. The branch's only guard is `if next_mission > 99: "
    "next_mission = 1` (command.py:432-436), and the source's own comment admits "
    "'I'm not sure what to do' past chapter 99. The endpoint reproduces the wrap "
    "rather than refusing an out-of-range identifier, because refusing would be "
    "stricter than legacy in the direction D4/D5 forbid"
)

# ------------------------------------------------------------ the branches --
# The recorded command contract, one record per branch, with the committed
# source lines that fix its arguments and its effects.  The ABSENCE of
# validation is a field of every record, because it is the fact that most needs
# stating (design D4/D5).
BRANCHES: Tuple[Dict[str, Any], ...] = (
    {
        "command": SET_GOALS_COMMAND,
        "action": ACTION_SET_GOAL,
        "source": "command.py:68-74",
        "args": ["goal index", "json progress pair"],
        "argument_order": "goal-then-progress",
        "reads": ["args[0]", "args[1]", "json.loads", "the committed title"],
        "writes": ["privateState[goals][goal_index]"],
        "delegates_to": "engine.py:96-100 (engine.set_goals)",
        "mutates": True,
        "effect": "the addressed goal's entry is REPLACED by the progress pair, "
            + "and the goals list is grown ON DEMAND with None padding until it "
            + "can address the index",
        "grows_list_on_demand": True,
        "upper_bound": None,
        "client_supplied_value": "the progress pair, which the service DERIVES "
            + "(quest_envelope.DERIVED_PROGRESS)",
        "validation": "none: no bounds check, no clamp, no membership test, no "
            + "exception guard, and no existence check. A goal index of 500 "
            + "appends 350 entries from one client-sent identifier, and that "
            + "absence is reproduced, not closed",
        "reads_a_price": False,
        "charges": False,
    },
    {
        "command": COMPLETE_GOAL_COMMAND,
        "action": ACTION_COMPLETE_GOAL,
        "source": "command.py:76-79",
        "args": ["goal index"],
        "argument_order": "goal",
        "reads": ["args[0]", "the committed title"],
        "writes": [],
        "delegates_to": None,
        "mutates": False,
        "effect": "NOTHING AT ALL: the branch resolves the committed title "
            + "through get_attribute_from_goal_id, prints it, and returns. There "
            + "is no completion flag, no ledger, and no reward - a goal "
            + "'completes' by being narrated in a print statement",
        "grows_list_on_demand": False,
        "upper_bound": None,
        "client_supplied_value": "none: the branch takes one identifier and "
            + "persists nothing",
        "validation": "none: no bounds check, no clamp, no membership test, and "
            + "no existence check. get_attribute_from_goal_id calls int(id) on the "
            + "client value with no guard, so a non-numeric goal id RAISES rather "
            + "than refusing - a legacy crash path, recorded, not reproduced",
        "reads_a_price": False,
        "charges": False,
    },
    {
        "command": SET_QUEST_VAR_COMMAND,
        "action": ACTION_SET_QUEST_VAR,
        "source": "command.py:87-117",
        "args": ["key", "value"],
        "argument_order": "key-then-value",
        "reads": ["args[0]", "args[1]", "map[currentQuestVars]"],
        "writes": ["map[currentQuestVars][key]", "map[idCurrentMission] (the "
                   + "`id` alias only)"],
        "delegates_to": None,
        "mutates": True,
        "effect": "ANY client-supplied key is persisted into the quest-variable "
            + "map, which is SELF-HEALED from the corpus's recorded None to an "
            + "empty dict first (command.py:113-114); the key `id` ALSO overwrites "
            + "the current mission identifier (command.py:110-111)",
        "grows_list_on_demand": False,
        "upper_bound": None,
        "client_supplied_value": "the value, which the service DERIVES; the key "
            + "is the branch's own addressing and is accepted unbounded",
        "validation": "NONE beyond the ONE key the branch itself ignores: "
            + QUEST_VAR_IGNORED_KEY
            + ". There is no membership test against the eight keys the branch's "
            + "own comment enumerates, so an invented key is accepted and "
            + "persisted",
        "reads_a_price": False,
        "charges": False,
    },
    {
        "command": COLLECT_MISSION_COMMAND,
        "action": ACTION_COLLECT_MISSION,
        "source": "command.py:430-442",
        "args": ["mission identifier"],
        "argument_order": "mission",
        "reads": ["args[0]"],
        "writes": ["map[idCurrentMission]", "map[timestampLastChapter]",
                   "map[currentQuestVars]"],
        "delegates_to": None,
        "mutates": True,
        "effect": "the current mission identifier is written as a STRING "
            + "(command.py:438) where the committed corpus records an INTEGER 0; "
            + "the last-chapter instant is stamped with the wall clock; and the "
            + "quest-variable map is CLEARED to an empty dict (command.py:440), "
            + "converting the corpus's recorded None as a side effect",
        "grows_list_on_demand": False,
        "upper_bound": None,
        "client_supplied_value": "the mission identifier, which is the branch's "
            + "own addressing; it WRAPS above 99 rather than being rejected",
        "validation": "the ONLY guard is `if next_mission > 99: next_mission = 1` "
            + "- a WRAP, not a rejection. No bounds check, no clamp, no "
            + "membership test, and no existence check otherwise",
        "reads_a_price": False,
        "charges": False,
    },
    {
        "command": ADMIN_SET_QUEST_RANK_COMMAND,
        "action": ACTION_SET_QUEST_RANK,
        "source": "command.py:745-750",
        "args": ["rank index", "difficulty"],
        "argument_order": "index-then-difficulty",
        "reads": ["args[0]", "args[1]"],
        "writes": ["privateState[questsRank][str(index)]"],
        "delegates_to": None,
        "mutates": True,
        "effect": "the addressed rank's difficulty is written under the "
            + "STRINGIFIED index, and nothing else. Both values are client-sent "
            + "in legacy; the service derives the difficulty and accepts the index "
            + "as addressing",
        "grows_list_on_demand": False,
        "upper_bound": None,
        "client_supplied_value": "the difficulty, which the service DERIVES; the "
            + "index is the addressing and is accepted unbounded - a negative "
            + "value is simply a distinct string key, so nothing is aliased",
        "validation": "none: no bounds check, no clamp, no membership test, and "
            + "no existence check. The rank map is written with no validation on "
            + "either side of the assignment",
        "reads_a_price": False,
        "charges": False,
    },
    {
        "command": END_QUEST_COMMAND,
        "action": ACTION_END_QUEST,
        "source": "command.py:752-806",
        "args": ["json blob"],
        "argument_order": "blob",
        "reads": ["args[0]", "json.loads", "win", "duration", "units", "map",
                  "difficulty", "voluntary_end", "quest_id"],
        "writes": ["map[questTimes][str(quest_id)]", "and, in LEGACY ONLY, placed "
                   + "rows via map_lose_item - REFUSED here"],
        "delegates_to": "engine.map_lose_item (engine.py:215-228) in LEGACY ONLY",
        "mutates": True,
        "effect": "the quest-time map gains one entry under the STRINGIFIED "
            + "quest id, stamped with the wall clock. The client-computed "
            + "destruction count is NOT reproduced: the service derives the blob "
            + "with an EMPTY unit list, so no placed row is touched",
        "grows_list_on_demand": False,
        "upper_bound": None,
        "client_supplied_value": "EVERYTHING in legacy - seven keys of one "
            + "authored blob. The service derives all seven and accepts only the "
            + "quest identifier",
        "validation": "only `if not quest_id: return` (command.py:798-800), and "
            + "that check runs AFTER the destruction loop - so a legacy request "
            + "with no quest id still destroys units and then returns. `difficulty` "
            + "is the ONLY clamped value in the branch: max(1, min(3, ...))",
        "reads_a_price": False,
        "charges": False,
        "destruction": "REFUSED",
        "destruction_note": END_QUEST_REFUSAL,
        "only_clamped_value": True,
        "difficulty_clamp": "max(1, min(3, ...)) at command.py:782",
    },
)

#: The branch count, pinned so a widening or narrowing of the closed set fails a
#: run instead of silently shipping a different contract.
BRANCH_COUNT = 6

#: The one branch that mutates nothing at all (design D3).
NO_OP_COMMAND = COMPLETE_GOAL_COMMAND

# --------------------------------------------------------- the writers --
#: Every writer of quest state.  Six are dispatcher branches; the SEVENTH is
#: ``fast_forward`` and is offered by NO action and by NO route (design D9).
WRITERS: Tuple[Dict[str, Any], ...] = (
    {
        "writer": "command:" + SET_GOALS_COMMAND,
        "source": "command.py:68-74 delegating to engine.py:96-100",
        "kind": "dispatcher-branch",
        "fields_written": [KEY_GOALS],
        "client_writable": False,
    },
    {
        "writer": "command:" + COMPLETE_GOAL_COMMAND,
        "source": "command.py:76-79",
        "kind": "dispatcher-branch",
        "fields_written": [],
        "client_writable": False,
        "note": "this branch WRITES NOTHING AT ALL - recorded so the writer "
            + "inventory is complete rather than flattering",
    },
    {
        "writer": "command:" + SET_QUEST_VAR_COMMAND,
        "source": "command.py:87-117",
        "kind": "dispatcher-branch",
        "fields_written": [KEY_QUEST_VARS, KEY_MISSION],
        "client_writable": False,
    },
    {
        "writer": "command:" + COLLECT_MISSION_COMMAND,
        "source": "command.py:430-442",
        "kind": "dispatcher-branch",
        "fields_written": [KEY_MISSION, KEY_LAST_CHAPTER, KEY_QUEST_VARS],
        "client_writable": False,
    },
    {
        "writer": "command:" + ADMIN_SET_QUEST_RANK_COMMAND,
        "source": "command.py:745-750",
        "kind": "dispatcher-branch",
        "fields_written": [KEY_RANKS],
        "client_writable": False,
    },
    {
        "writer": "command:" + END_QUEST_COMMAND,
        "source": "command.py:752-806 (write at 802)",
        "kind": "dispatcher-branch",
        "fields_written": [KEY_QUEST_TIMES],
        "client_writable": False,
    },
    {
        "writer": "command:" + FAST_FORWARD_COMMAND,
        "source": "command.py:942-944 (questTimes) and command.py:911 "
            + "(timestampLastChapter)",
        "kind": "engine-side decrement inside a dispatcher branch",
        "fields_written": [KEY_QUEST_TIMES, KEY_LAST_CHAPTER],
        "client_writable": True,
    },
)

#: Seven writers of quest state: six branches and ``fast_forward``.
WRITER_COUNT = 7
#: The one writer that is not a quest branch.
WRITER_FAST_FORWARD = "command:" + FAST_FORWARD_COMMAND

FAST_FORWARD_CONTRACT = (
    "RECORDED AND IMPLEMENTED NOT AT ALL. Quest state has SEVEN writers: the six "
    "branches and fast_forward, which is NOT a quest branch. fast_forward "
    "(command.py:905) subtracts a CLIENT-SUPPLIED number of seconds "
    "(`seconds = args[0]`, command.py:906) from every questTimes entry "
    "(command.py:942-944) and from timestampLastChapter (command.py:911), both "
    "clamped at zero. That makes quest timing CLIENT-WRITABLE in exactly the way "
    "M9 line 1 found the research instant client-writable, and for the same "
    "reason: NO legacy branch reads a quest instant to decide anything. It is "
    "named here because an instant trusted by nothing is the only elapsed-time "
    "input the quest system has. NO fast-forward operation is delivered by this "
    "endpoint, by the client's facade, by either GameApi implementation, or by "
    "the client's flow, and no elapsed-time, remaining-time, readiness, or "
    "completion behaviour is derived from any quest instant anywhere in this "
    "repository (design D9)"
)

#: The committed save-migration initialization of the quest-time map.  A
#: **migration path**, not gameplay (design D9).
MIGRATION = {
    "field": KEY_QUEST_TIMES,
    "where": "version.py:38-44",
    "effect": "if the map carries no questTimes it is set to None, and if it is "
        + "then not a dict it is coerced to {} and the 'quest fix' is printed",
    "kind": "save-migration",
    "is_gameplay": False,
    "note": "RECORDED AS A MIGRATION PATH, NOT AS QUEST BEHAVIOUR. version.py "
        + "runs once per save load and repairs the quest-time map's SHAPE. It "
        + "resolves no goal, advances no chapter, awards nothing, and reads no "
        + "quest content, so counting it as a seventh quest behaviour would "
        + "overstate what the migration does",
}

# --------------------------------------------------- the recorded absences --
NO_REWARD = (
    "NO QUEST REWARD IS PAID AND NONE EXISTS. MEASURED as QUOTED occurrences "
    "across the seven legacy modules, only two committed quest fields are read by "
    "anything: `id` (8 occurrences: command.py 2, get_game_config.py 6) and "
    "`title` (2 occurrences, both `print` statements). `reward` has ZERO, and it "
    "is committed on all 91 entries UNIFORMLY the value 10 - so it carries no "
    "information even if it were read. `hint`, `description`, `kind`, "
    "`legacy_id`, `source_file`, `source_layer` and `content_version` all have "
    "ZERO as well. This settles the quest-economy question in the strongest "
    "available form: there is no quest reward to pay, no per-quest cost, and no "
    "quest price, because no committed quest field is read except the identifier "
    "and the title - and the title is read solely to print it. A line that "
    "derived a payout from a uniform 10 would fabricate a uniform payout that is "
    "not a payout at all (design D6)"
)

NO_RESOURCE_MOVE = (
    "NO STORED RESOURCE MOVES ON ANY QUEST ACTION. do_command applies the "
    "request's per-command resource vector BEFORE dispatch (command.py:40; "
    "engine.py:251-271) as max(current + delta, 0) per resource, so any price a "
    "client attached to a quest command would be a client-trusted mint or burn. "
    "The derived vector is therefore NEUTRAL and every action's post-execution "
    "proof requires that EVERY stored resource - all seven of them, compared over "
    "the complete set rather than a selected subset - be UNCHANGED (design D6)"
)

NO_COMPLETION = (
    "NO COMPLETION STATE EXISTS, AND THE SUITE ASSERTS THE ABSENCE STRUCTURALLY. "
    "complete_goal writes NOTHING AT ALL (command.py:76-79): it resolves the "
    "committed title, prints it, and returns. So there is no completion flag, no "
    "completion ledger, no completion accessor, and no reward for finishing a "
    "goal - a goal 'completes' by being narrated in a print statement. The "
    "endpoint executes the real branch and its post-execution proof requires the "
    "WHOLE quest state to be byte-identical, and the client's whole module "
    "function inventory is pinned, so a mark_goal_complete or is_goal_complete "
    "helper fails the run wherever it is added (design D3)"
)

NO_BOUNDS = (
    "NO BOUND IS ADDED TO THE ON-DEMAND GOALS LIST. engine.set_goals grows the "
    "list on demand (engine.py:98-99): `while goal >= len(goals): goals.append("
    "None)`. There is no upper bound, so a client-sent goal index of 500 appends "
    "350 entries from ONE identifier, and the endpoint reproduces that absence "
    "rather than closing it - a bound the legacy server does not have would make "
    "this service STRICTER than legacy in the unexamined direction, which is a "
    "parity break in the opposite sense from the one this line refuses. The "
    "recorded absence is a Server v1 / M13 gap, NOT permission to invent a limit. "
    "The ONE structural refusal here is a NEGATIVE goal index, because Python "
    "would otherwise write goals[-1] - aliasing the LAST entry - and goals[-1000] "
    "would raise; that is the same structural rule the expansion line applied to "
    "a negative expansion id, and it is recorded rather than invented (design D4)"
)

NO_MEMBERSHIP = (
    "NO MEMBERSHIP TEST IS ADDED TO THE QUEST-VARIABLE WRITER. The legacy branch "
    "accepts ANY client-invented key (command.py:116) against the eight keys its "
    "own comment enumerates (command.py:97-106), so inventing a closed set of "
    "eight would reject keys the legacy server happily persisted. The endpoint "
    "records the eight as CONTENT, accepts what the client sends, and refuses "
    "exactly ONE key - idSimpleChapter - because that is the one key the legacy "
    "branch ITSELF ignores (command.py:91-95), which is a recorded behaviour "
    "rather than an absence (design D5)"
)

NO_ELAPSED = (
    "NO ELAPSED-TIME BEHAVIOUR IS DERIVED FROM ANY QUEST INSTANT. No legacy "
    "branch reads timestampLastChapter or any questTimes entry to decide "
    "anything: the quest-time map has six sites, of which two are the branch "
    "write at command.py:802 and the fast_forward write at command.py:942-944, "
    "and four are the save migration at version.py:39-43. So there is no "
    "chapter duration, no remaining chapter time, no cooldown, and no readiness "
    "rule to reproduce, and this contract computes none of them (design D9)"
)

#: The five refusal families, each with its non-empty recorded reason.  They are
#: stated as requirements (design D3/D4/D5/D6/D9), not as omissions.
REFUSALS: Tuple[Dict[str, Any], ...] = (
    {"refusal": "no_reward", "implemented": False, "reason": NO_REWARD},
    {"refusal": "no_resource_move", "implemented": False, "reason": NO_RESOURCE_MOVE},
    {"refusal": "no_completion", "implemented": False, "reason": NO_COMPLETION},
    {"refusal": "no_bounds", "implemented": False, "reason": NO_BOUNDS},
    {"refusal": "no_membership", "implemented": False, "reason": NO_MEMBERSHIP},
    {"refusal": "no_elapsed", "implemented": False, "reason": NO_ELAPSED},
)

#: The refused destruction, as a separate recorded family so it cannot be lost
#: inside the five above.
REFUSED_DESTRUCTION = {
    "refusal": "destruction_count",
    "implemented": False,
    "command": END_QUEST_COMMAND,
    "legacy_behaviour": "destroys placed rows via map_lose_item (command.py:796) "
        "using the CLIENT-COMPUTED count max(0, unit[2] - unit[3]) "
        "(command.py:792)",
    "modern_behaviour": "destroys nothing: the derived blob carries an EMPTY LIST "
        "of units, so the destruction loop iterates zero times, map_lose_item is "
        "never reached, and every placed row is left byte-identical over the "
        "COMPLETE items mapping",
    "status": "DIVERGENCE, NOT PARITY",
    "reason": END_QUEST_REFUSAL,
}

# ------------------------------------------------- the structural refusals --
REASON_MISSING_ACTION = "missing_action"
REASON_INVALID_ACTION = "invalid_action"
REASON_MISSING_GOAL_INDEX = "missing_goal_index"
REASON_INVALID_GOAL_INDEX = "invalid_goal_index"
REASON_MISSING_KEY = "missing_key"
REASON_INVALID_KEY = "invalid_key"
REASON_IGNORED_KEY = "ignored_quest_var_key"
REASON_MISSING_MISSION = "missing_mission"
REASON_INVALID_MISSION = "invalid_mission"
REASON_MISSING_QUEST_INDEX = "missing_quest_index"
REASON_INVALID_QUEST_INDEX = "invalid_quest_index"
REASON_MISSING_QUEST_ID = "missing_quest_id"
REASON_INVALID_QUEST_ID = "invalid_quest_id"
REASON_ABSENT_STATE = "unresolvable_quest_state"
REASON_INVALID_VECTOR = "invalid_vector"
REASON_INVALID_TIMESTAMP = "invalid_timestamp"
REASON_INVALID_PAYLOAD = "invalid_payload"

#: The refusal reasons reachable from a request, in the endpoint's own order.
STRUCTURAL_REFUSALS: Tuple[str, ...] = (
    REASON_MISSING_ACTION,
    REASON_INVALID_ACTION,
    REASON_MISSING_GOAL_INDEX,
    REASON_INVALID_GOAL_INDEX,
    REASON_MISSING_KEY,
    REASON_INVALID_KEY,
    REASON_IGNORED_KEY,
    REASON_MISSING_MISSION,
    REASON_INVALID_MISSION,
    REASON_MISSING_QUEST_INDEX,
    REASON_INVALID_QUEST_INDEX,
    REASON_MISSING_QUEST_ID,
    REASON_INVALID_QUEST_ID,
    REASON_ABSENT_STATE,
)

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The map fields that hold a slot of the 8-slot vector.  ``cash`` and ``mana``
# live outside the map, so they are absent here by construction.
MAP_RESOURCE_FIELDS: Tuple[str, ...] = ("xp", "gold", "wood", "oil", "steel")

# ------------------------------------------------- the committed corpus pins --
COMMITTED_GOALS_LENGTH = 151
COMMITTED_GOALS_ALL_NONE = True
COMMITTED_RANKS: Dict[str, Any] = {}
COMMITTED_UNLOCKED_INDEX = 0
COMMITTED_QUEST_TIMES: Dict[str, Any] = {}
COMMITTED_QUEST_VARS_IS_NULL = True
COMMITTED_MISSION: Any = 0
COMMITTED_LAST_CHAPTER = 0
COMMITTED_PLACEMENTS = 40
COMMITTED_RESOURCE_BEFORE: Dict[str, int] = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}

# ------------------------------------------------- the committed content --
#: The ten committed quest fields, and the MEASURED quoted-occurrence count each
#: has across the seven legacy modules.  Re-measured by the hermetic suite in the
#: same run; a discrepancy fails the suite rather than publishing a new table.
COMMITTED_FIELD_CONSUMERS: Tuple[Dict[str, Any], ...] = (
    {"field": "id", "quoted_occurrences": 8,
     "where": ["command.py", "get_game_config.py"], "used": True},
    {"field": "title", "quoted_occurrences": 2,
     "where": ["command.py"], "used": True,
     "note": "both occurrences are `print` statements; the title is resolved only "
             "to be narrated"},
    {"field": "hint", "quoted_occurrences": 0, "where": [], "used": False},
    {"field": "description", "quoted_occurrences": 0, "where": [], "used": False},
    {"field": "reward", "quoted_occurrences": 0, "where": [], "used": False,
     "note": "UNIFORMLY 10 on all 91 committed entries and read by NOTHING, so it "
             "carries no information even if it were read"},
    {"field": "kind", "quoted_occurrences": 0, "where": [], "used": False},
    {"field": "legacy_id", "quoted_occurrences": 0, "where": [], "used": False},
    {"field": "source_file", "quoted_occurrences": 0, "where": [], "used": False},
    {"field": "source_layer", "quoted_occurrences": 0, "where": [], "used": False},
    {"field": "content_version", "quoted_occurrences": 0, "where": [], "used": False},
)
COMMITTED_FIELD_COUNT = 10
#: The two fields that DO have a consumer.
COMMITTED_FIELDS_READ: Tuple[str, ...] = ("id", "title")
#: The eight that do NOT.
COMMITTED_FIELDS_UNREAD: Tuple[str, ...] = (
    "legacy_id", "kind", "source_file", "source_layer", "content_version",
    "hint", "description", "reward",
)
COMMITTED_QUEST_ENTRIES = 91
COMMITTED_REWARD_VALUE: Any = 10
#: The amount this contract pays for a quest: **zero**, and never a function of
#: the committed ``reward`` field.  Delivered as a constant so the suite can
#: assert it and so the response can report it, and named without the committed
#: field's own name so "no code identifier is named after ``reward``" stays
#: mechanically checkable over this module's bindings.
REWARD_PAID = 0
COMMITTED_ID_MIN = 1
COMMITTED_ID_MAX = 91
#: The goal-id space is ONE-BASED ``1..91`` and the accessor is fail-closed:
#: ``get_game_config.py:144-146`` returns ``None`` for an id outside the table,
#: and ``int(id)`` is called on the client value with no guard.
COMMITTED_GOAL_INDEX_SOURCE = "get_game_config.py:142-150"

CONTENT_RECORD_NOTE = (
    "REPORTED AND NEVER USED. The committed quest content is read by the legacy "
    "server for exactly two things: an identifier lookup (get_game_config.py:142 "
    "and 144-146) and a title to print (command.py:74 and 79). Nothing else. So "
    "the endpoint uses the committed content ONLY to resolve an identifier and "
    "read its title, and derives NO reward, cost, requirement, schedule, or "
    "completion rule from it (design D6). `hint` and `description` exist to be "
    "DISPLAYED BY THE FLASH CLIENT and are read by no server branch; MEASURED, "
    "every one of the 91 committed `hint` values is EMPTY and every `description` "
    "is non-empty. No code identifier in this repository is named after the "
    "reward field, which is what makes the 'reported, never used' claim "
    "mechanical rather than editorial"
)

#: The zero-consumer fact, following the ``resurrectable`` precedent.
ZERO_CONSUMER_FIELDS: Tuple[Dict[str, Any], ...] = (
    {
        "field": "privateState[unlockedQuestIndex]",
        "quoted_sites": 0,
        "written_by": [],
        "read_by": [],
        "consequence": "committed player state with ZERO legacy consumers. It is "
            + "projected as content and consumed by nothing, and NO delivered "
            + "operation writes it",
        "ordinal": "the NINTH zero-consumer committed field in this project, "
            + "after unit_capacity, the level curve's reward_type/reward_amount, "
            + "the collect family, max_frame, velocity, syringes, and training_time",
    },
)

#: The dead-hero ledger doors this line touches (design D10).
LEDGER_DOOR = {
    "door": "map_lose_item",
    "source": "engine.py:215-228",
    "calls_helper_at": "engine.py:223 (push_dead_unit)",
    "is_a_dispatcher_branch": False,
    "callers": ["command.py:796 (end_quest)", "command.py:872 (end_attack)"],
    "modern_behaviour": "the quest-side caller is REFUSED here: the derived "
        + "end_quest blob carries an empty unit list, so map_lose_item is never "
        + "reached through this endpoint and no dead-hero ledger entry is written "
        + "by a quest action",
    "status": "the quest path's reach into the dead-hero ledger is recorded, "
        + "REFUSED, and asserted byte-identical on the whole placed-row set",
}

# -------------------------------------------------- the input guardrails --
#: Keys a client may attach that the service **ignores**.  Recorded so each
#: refusal is enumerable rather than editorial, and asserted by the endpoint's
#: own tests as changing nothing.
IGNORED_CLIENT_KEYS: Tuple[str, ...] = (
    "progress", "visited", "currentStep", "value", "difficulty", "win",
    "duration", "map", "units", "lost", "voluntary_end", "reward", "price",
    "cost", "resources_changed", "vector", "seconds", "fast_forward",
    "complete", "completed", "unlocked_quest_index", "unlockedQuestIndex",
)

#: The client values the service **persists**.  Empty, and asserted empty: no
#: client-supplied progress pair, value, rank, outcome, or destroyed-unit count
#: is ever written.
PERSISTED_CLIENT_VALUES: Tuple[str, ...] = ()

__all__ = [
    "ACTION_ADDRESSING",
    "ACTION_ADDRESSING_KEY",
    "ACTION_COLLECT_MISSION",
    "ACTION_COMPLETE_GOAL",
    "ACTION_COMMANDS",
    "ACTION_END_QUEST",
    "ACTION_SET_GOAL",
    "ACTION_SET_QUEST_RANK",
    "ACTION_SET_QUEST_VAR",
    "ACTIONS",
    "ADMIN_SET_QUEST_RANK_COMMAND",
    "BRANCHES",
    "BRANCH_COUNT",
    "COLLECT_MISSION_COMMAND",
    "COMMAND_RECORDS",
    "COMMITTED_FIELDS_READ",
    "COMMITTED_FIELDS_UNREAD",
    "COMMITTED_FIELD_CONSUMERS",
    "COMMITTED_FIELD_COUNT",
    "COMMITTED_GOALS_ALL_NONE",
    "COMMITTED_GOALS_LENGTH",
    "COMMITTED_GOAL_INDEX_SOURCE",
    "COMMITTED_ID_MAX",
    "COMMITTED_ID_MIN",
    "COMMITTED_LAST_CHAPTER",
    "COMMITTED_MISSION",
    "COMMITTED_PLACEMENTS",
    "COMMITTED_QUEST_ENTRIES",
    "COMMITTED_QUEST_TIMES",
    "COMMITTED_QUEST_VARS_IS_NULL",
    "COMMITTED_RANKS",
    "COMMITTED_REWARD_VALUE",
    "COMMITTED_RESOURCE_BEFORE",
    "COMMITTED_UNLOCKED_INDEX",
    "REWARD_PAID",
    "COMPLETE_GOAL_COMMAND",
    "CONTENT_RECORD_NOTE",
    "DERIVED_DIFFICULTY",
    "DERIVED_DIFFICULTY_FIELD",
    "DERIVED_DIFFICULTY_NOTE",
    "DERIVED_DURATION",
    "DERIVED_MAP",
    "DERIVED_PROGRESS",
    "DERIVED_PROGRESS_NOTE",
    "DERIVED_QUEST_VALUE",
    "DERIVED_QUEST_VALUE_NOTE",
    "DERIVED_UNITS",
    "DERIVED_VOLUNTARY_END",
    "DERIVED_WIN",
    "DIFFICULTY_MAX",
    "DIFFICULTY_MIN",
    "ENVELOPE_KEYS",
    "END_QUEST_COMMAND",
    "END_QUEST_REFUSAL",
    "EnvelopeError",
    "FAST_FORWARD_COMMAND",
    "FAST_FORWARD_CONTRACT",
    "IGNORED_CLIENT_KEYS",
    "KEY_GOALS",
    "KEY_LAST_CHAPTER",
    "KEY_MISSION",
    "KEY_QUEST_TIMES",
    "KEY_QUEST_VARS",
    "KEY_RANKS",
    "KEY_UNLOCKED_INDEX",
    "LEDGER_DOOR",
    "MAP_KEYS",
    "MAP_RESOURCE_FIELDS",
    "MIGRATION",
    "MISSION_WRAP_BOUND",
    "MISSION_WRAP_NOTE",
    "MISSION_WRAP_TARGET",
    "NO_BOUNDS",
    "NO_COMPLETION",
    "NO_ELAPSED",
    "NO_MEMBERSHIP",
    "NO_REWARD",
    "NO_RESOURCE_MOVE",
    "NO_OP_COMMAND",
    "PERSISTED_CLIENT_VALUES",
    "PRIVATE_KEYS",
    "QUEST_COMMANDS",
    "QUEST_FIELDS",
    "QUEST_VAR_ALIAS_KEY",
    "QUEST_VAR_COMMENT_KEYS",
    "QUEST_VAR_COMMENT_NOTE",
    "QUEST_VAR_IGNORED_KEY",
    "REASON_ABSENT_STATE",
    "REASON_IGNORED_KEY",
    "REASON_INVALID_ACTION",
    "REASON_INVALID_GOAL_INDEX",
    "REASON_INVALID_KEY",
    "REASON_INVALID_MISSION",
    "REASON_INVALID_PAYLOAD",
    "REASON_INVALID_QUEST_ID",
    "REASON_INVALID_QUEST_INDEX",
    "REASON_INVALID_TIMESTAMP",
    "REASON_INVALID_VECTOR",
    "REASON_MISSING_ACTION",
    "REASON_MISSING_GOAL_INDEX",
    "REASON_MISSING_KEY",
    "REASON_MISSING_MISSION",
    "REASON_MISSING_QUEST_ID",
    "REASON_MISSING_QUEST_INDEX",
    "REFUSALS",
    "REFUSED_DESTRUCTION",
    "RESOURCE_VECTOR_SLOTS",
    "SET_GOALS_COMMAND",
    "SET_QUEST_VAR_COMMAND",
    "STRUCTURAL_REFUSALS",
    "WRITER_COUNT",
    "WRITER_FAST_FORWARD",
    "WRITERS",
    "ZERO_CONSUMER_FIELDS",
    "build_envelope",
    "clamp_difficulty",
    "command_for_action",
    "copy_state",
    "data_field",
    "derived_quest",
    "expected_state",
    "is_action",
    "is_goal_index",
    "is_mission",
    "is_quest_id",
    "is_quest_rank_index",
    "is_quest_var_key",
    "is_strict_int",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
    "project_quests",
    "resolve_state",
    "snapshot_state",
    "validate_vector",
]

#: ``COMMAND_RECORDS`` is the recorded **command** vocabulary in committed
#: dispatcher order, kept as a name of its own so a caller never has to map an
#: action name onto a command name by hand.
COMMAND_RECORDS: Tuple[Dict[str, str], ...] = tuple(
    {"command": record["command"], "action": record["action"]}
    for record in BRANCHES
)


# ------------------------------------------------------------ the vocabulary --
def is_action(value: Any) -> bool:
    """Whether ``value`` names one of the six closed quest actions.

    The set is **closed**: ``fast_forward`` is deliberately ABSENT (design D9),
    because its ``seconds`` argument is client-supplied and no evidence
    constrains what a client sends.  Anything outside the set is refused before
    the dispatcher runs, so an unknown action can never reach a legacy branch
    that would treat it as an unhandled command.
    """
    return isinstance(value, str) and value in ACTIONS


def command_for_action(action: str) -> str:
    """The legacy command name one closed action derives.

    Raises :class:`EnvelopeError` with ``invalid_action`` for anything outside
    the closed vocabulary, so a caller cannot map an unvalidated action onto a
    branch.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_INVALID_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    return ACTION_COMMANDS[str(action)]


def is_goal_index(value: Any) -> bool:
    """Whether ``value`` is a goal index the on-demand list can address.

    A **non-negative** strict integer.  That is the ONLY goal rule here: the
    legacy helper grows the list on demand with **no upper bound**, so a large
    index is accepted here too and the unbounded growth is reproduced rather
    than closed (design D4).  A **negative** index is refused *structurally*,
    because Python would otherwise write ``goals[-1]`` — aliasing the LAST entry
    — and ``goals[-1000]`` would raise.  That is the same structural rule the
    expansion line applied to a negative expansion id, and the legacy aliasing
    is recorded in :data:`NO_BOUNDS` rather than reproduced.
    """
    return is_strict_int(value) and int(value) >= 0


def is_quest_var_key(value: Any) -> bool:
    """Whether ``value`` is a quest-variable key the branch would persist.

    Any non-empty string.  **No membership test** against the eight keys the
    branch's own comment enumerates (design D5): the legacy branch accepts an
    invented key, so this does too.  The one key refused here is the one the
    branch **itself** ignores — :data:`QUEST_VAR_IGNORED_KEY` — and it is refused
    by the caller with its own reason, because a refusal and a validity check
    are different things.
    """
    return isinstance(value, str) and value.strip() != ""


def is_mission(value: Any) -> bool:
    """Whether ``value`` is a mission identifier the branch can wrap.

    Any strict integer, **including** one above :data:`MISSION_WRAP_BOUND`:
    the branch's only guard WRAPS such a value to
    :data:`MISSION_WRAP_TARGET` rather than rejecting it (design D4), so a
    refusal would be stricter than legacy in the direction D4 forbids.
    """
    return is_strict_int(value)


def is_quest_rank_index(value: Any) -> bool:
    """Whether ``value`` is a rank index.

    Any strict integer, **with no bound in either direction**: the branch writes
    ``privateState["questsRank"][str(index)] = difficulty`` (``command.py:750``),
    so even a negative index is just a distinct string key and nothing is
    aliased.  The absence of a bound is reproduced (design D4).
    """
    return is_strict_int(value)


def is_quest_id(value: Any) -> bool:
    """Whether ``value`` is a quest identifier.

    Any strict integer, **with no bound**: the branch writes
    ``map["questTimes"][str(quest_id)]`` (``command.py:802``), so an id outside
    the committed ``1..91`` content range is a valid key and refusing it would
    be stricter than legacy (design D4).  A non-integer is refused structurally,
    because a non-numeric key would let a client invent arbitrary dict keys.
    """
    return is_strict_int(value)


def clamp_difficulty(value: Any) -> int:
    """The one clamp any of the six branches contains.

    ``end_quest`` clamps its difficulty to ``max(1, min(3, ...))``
    (``command.py:782``).  Reproducing that clamp is reproducing legacy, so a
    value outside the range lands on the nearest bound rather than being
    refused.  The endpoint does **not** send a client value through this clamp:
    it derives :data:`DERIVED_DIFFICULTY`, so a client's number is never
    persisted.  The clamp is delivered so the recorded behaviour is real rather
    than described.
    """
    if not is_strict_int(value):
        raise EnvelopeError(
            REASON_INVALID_PAYLOAD,
            "difficulty must be an integer, got %r" % (value,),
        )
    return max(DIFFICULTY_MIN, min(DIFFICULTY_MAX, int(value)))


def wrap_mission(value: Any) -> int:
    """The mission identifier the branch will actually store.

    Reproduces the branch's ONLY guard: ``if next_mission > 99: next_mission =
    1`` (``command.py:432-436``).  A wrap, not a rejection — see
    :data:`MISSION_WRAP_NOTE`.
    """
    if not is_mission(value):
        raise EnvelopeError(
            REASON_INVALID_MISSION, "mission must be an integer, got %r" % (value,)
        )
    mission = int(value)
    return MISSION_WRAP_TARGET if mission > MISSION_WRAP_BOUND else mission


# ------------------------------------------------------------ derived vector --
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D6).

    A quest action's price would be **client-sent**: ``do_command`` applies the
    request's per-command vector before the branch runs (``command.py:40``,
    ``engine.py:251-271``), so any price a client attached would be a
    client-trusted mint or burn.  The committed configuration records no quest
    price at all, so the only honest vector is the neutral one, and a fresh list
    is returned on every call so a caller can never mutate the derivation for the
    next one.  **No quest price is claimed in either direction.**
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` before it is sent.

    Only the **all-zero** vector is legal here.  A positive entry would be a
    client-trusted **mint** and a negative one a client-trusted **burn** under
    legacy's ``max(current + delta, 0)`` clamp, and either would make the
    endpoint's "nothing moved" proof fail in a way that looks like a bug.
    Refusing anything but zero here is what forecloses the smuggling: the
    derivation cannot express it, so the endpoint cannot send it.
    """
    if not isinstance(vector, list) or len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            REASON_INVALID_VECTOR,
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value):
            raise EnvelopeError(
                REASON_INVALID_VECTOR,
                "resources_changed slot %d must be an integer, got %r"
                % (index, value),
            )
        if value != 0:
            raise EnvelopeError(
                REASON_INVALID_VECTOR,
                "resources_changed slot %d is %r: a quest action moves no "
                % (index, value)
                + "resource, so only the neutral all-zero vector is derivable",
            )
    return list(vector)


# ------------------------------------------------------------- the state --
def _copy_goals(value: Any) -> List[Any]:
    return list(value)


def _copy_ranks(value: Any) -> Dict[str, Any]:
    return {str(key): value[key] for key in value}


def _copy_vars(value: Any) -> Any:
    """A fresh copy of the quest-variable map, or ``None`` preserved as ``None``.

    The committed corpus records this field as **``None``**, and both
    ``set_quest_var`` and ``collect_mission`` self-heal it to a dict (design
    D8).  Copying must therefore preserve the recorded null rather than turning
    it into an empty map, because an empty map presented in place of a recorded
    null is exactly the substitution this contract refuses.
    """
    if value is None:
        return None
    return {str(key): value[key] for key in value}


def _copy_times(value: Any) -> Dict[str, Any]:
    return {str(key): value[key] for key in value}


def resolve_state(private_state: Any, first_map: Any) -> Dict[str, Any]:
    """The seven committed quest fields, copied, or a named refusal.

    Returns a mapping of the seven fields exactly as the save holds them, or
    raises :class:`EnvelopeError` with ``unresolvable_quest_state`` naming the
    first field that is absent or of the wrong type.

    **Copies are mandatory, not hygiene.**  The legacy branches mutate these very
    containers in place (``engine.set_goals`` appends to ``goals``;
    ``map_lose_item`` deletes from ``items``), so a state returned by reference
    would alias the live save and the endpoint's "before" snapshot would report
    the after-state.

    The ``goals`` list is required to be a list but its length is **not**
    constrained: the on-demand growth is a legacy behaviour, so any length
    resolves.  ``currentQuestVars`` is the one field whose recorded **``None``**
    is a legitimate state and is preserved rather than refused (design D8).
    """
    if not isinstance(private_state, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the save's private state is %s, not an object"
            % type(private_state).__name__,
        )
    if not isinstance(first_map, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the save's first map is %s, not an object"
            % type(first_map).__name__,
        )
    state: Dict[str, Any] = {}
    for key in PRIVATE_KEYS:
        if key not in private_state:
            raise EnvelopeError(
                REASON_ABSENT_STATE,
                "the save's private state carries no %r, so no quest field is "
                "addressable" % key,
            )
    for key in MAP_KEYS:
        if key not in first_map:
            raise EnvelopeError(
                REASON_ABSENT_STATE,
                "the save's first map carries no %r, so no quest field is "
                "addressable" % key,
            )
    goals = private_state[KEY_GOALS]
    if not isinstance(goals, list):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "privateState[%r] is %s, not a list"
            % (KEY_GOALS, type(goals).__name__),
        )
    ranks = private_state[KEY_RANKS]
    if not isinstance(ranks, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "privateState[%r] is %s, not an object"
            % (KEY_RANKS, type(ranks).__name__),
        )
    unlocked = private_state[KEY_UNLOCKED_INDEX]
    if not is_strict_int(unlocked):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "privateState[%r] is %r, not an integer"
            % (KEY_UNLOCKED_INDEX, unlocked),
        )
    quest_vars = first_map[KEY_QUEST_VARS]
    if quest_vars is not None and not isinstance(quest_vars, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "maps[0][%r] is %s, neither an object nor a recorded null"
            % (KEY_QUEST_VARS, type(quest_vars).__name__),
        )
    quest_times = first_map[KEY_QUEST_TIMES]
    if not isinstance(quest_times, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "maps[0][%r] is %s, not an object"
            % (KEY_QUEST_TIMES, type(quest_times).__name__),
        )
    # The mission field is read **loosely on purpose** and for a measured reason.
    # Three shapes occur in real legacy state, and refusing any of them would
    # hide a shape divergence rather than report it:
    #   * an INTEGER  - what the committed corpus records (0), and what a save
    #     has held since the chapter system was introduced;
    #   * a STRING    - what collect_mission writes (command.py:438
    #     `str(next_mission)`), so the two never agree and normalizing either
    #     would hide it (design D8);
    #   * a BOOLEAN   - what the `id` alias writes when the service derives a
    #     marker value (command.py:111 writes the SAME value it stores in the
    #     bag), so `isinstance(True, int)` is the whole reason the check below
    #     is `isinstance(..., (int, str))` rather than a strict one.
    mission = first_map[KEY_MISSION]
    if not isinstance(mission, (int, str)):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "maps[0][%r] is %s, neither an integer, a boolean, nor a string"
            % (KEY_MISSION, type(mission).__name__),
        )
    last_chapter = first_map[KEY_LAST_CHAPTER]
    if not is_strict_int(last_chapter):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "maps[0][%r] is %r, not an integer"
            % (KEY_LAST_CHAPTER, last_chapter),
        )
    state[KEY_GOALS] = _copy_goals(goals)
    state[KEY_RANKS] = _copy_ranks(ranks)
    state[KEY_UNLOCKED_INDEX] = int(unlocked)
    state[KEY_QUEST_VARS] = _copy_vars(quest_vars)
    state[KEY_QUEST_TIMES] = _copy_times(quest_times)
    # The mission is carried VERBATIM - never coerced - so the three measured
    # shapes (integer, string, boolean) each stay distinguishable in the
    # projection instead of collapsing into one another.
    state[KEY_MISSION] = mission
    state[KEY_LAST_CHAPTER] = int(last_chapter)
    return state


def snapshot_state(save_document: Any) -> Dict[str, Any]:
    """:func:`resolve_state` over a whole save document."""
    if not isinstance(save_document, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the save is %s, not an object" % type(save_document).__name__,
        )
    maps = save_document.get("maps")
    if not isinstance(maps, list) or not maps or not isinstance(maps[0], dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE, "the save carries no readable first map"
        )
    return resolve_state(save_document.get("privateState"), maps[0])


def copy_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """A fresh copy of a resolved quest state, so a caller may keep it."""
    out: Dict[str, Any] = {}
    for key in QUEST_FIELDS:
        value = state.get(key)
        if key == KEY_QUEST_VARS:
            out[key] = _copy_vars(value)
        elif key in (KEY_GOALS,):
            out[key] = list(value) if isinstance(value, list) else value
        elif key in (KEY_RANKS, KEY_QUEST_TIMES):
            out[key] = _copy_ranks(value) if isinstance(value, dict) else value
        else:
            out[key] = value
    return out


# ------------------------------------------------------- the derived effect --
def _pad_goals(before: List[Any], index: int) -> List[Any]:
    """The goals list after ``engine.set_goals`` writes one index.

    Reproduces the on-demand growth verbatim (``engine.py:98-100``): the list is
    padded with ``None`` until it can address ``index``, then that entry is
    replaced.  **No upper bound** — a client-sent index of 500 grows the list by
    350 entries (design D4).
    """
    goals = list(before)
    while index >= len(goals):
        goals.append(None)
    return goals


def derived_quest(before: Dict[str, Any], action: Any, addressing: Any,
                  ) -> Dict[str, Any]:
    """What one quest command does to the quest state — derived, not read.

    Returns
        ``{action, command, addressing, addressing_kind, written, untouched,
        derived_state, stamps_instant, stamps_chapter, mutates, notes}``

    ``derived_state`` is the **complete** expected post-state: every field the
    branch does not write is copied from the before-state verbatim, so the
    comparison in :func:`expected_state` covers the whole state rather than a
    selected subset.  The two wall-clock fields are reported as the sentinel
    ``True`` rather than a value, because ``time_now`` is not derivable; they are
    compared by **shape** and **direction** after execution instead.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_INVALID_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    action_text = str(action)
    command = ACTION_COMMANDS[action_text]
    if not isinstance(before, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the before state is %s, not an object" % type(before).__name__,
        )
    # The seven fields are checked on the CALLER's state, before any copy: a
    # partial state must fail closed rather than have its missing field dropped
    # by the copier and read as a state that simply does not own one.
    for key in QUEST_FIELDS:
        if key not in before:
            raise EnvelopeError(
                REASON_ABSENT_STATE, "the before state carries no %r" % key
            )
    state = copy_state(before)
    written: List[str] = []
    stamps_instant = False
    stamps_chapter = False
    mutates = True
    notes: List[str] = []

    if action_text == ACTION_SET_GOAL:
        if not is_goal_index(addressing):
            raise EnvelopeError(
                REASON_INVALID_GOAL_INDEX,
                "goal_index must be a non-negative integer, got %r" % (addressing,),
            )
        index = int(addressing)
        state[KEY_GOALS] = _pad_goals(state[KEY_GOALS], index)
        state[KEY_GOALS][index] = list(DERIVED_PROGRESS)
        written = [KEY_GOALS]
        notes.append(DERIVED_PROGRESS_NOTE)
    elif action_text == ACTION_COMPLETE_GOAL:
        if not is_goal_index(addressing):
            raise EnvelopeError(
                REASON_INVALID_GOAL_INDEX,
                "goal_index must be a non-negative integer, got %r" % (addressing,),
            )
        mutates = False
        notes.append(NO_COMPLETION)
    elif action_text == ACTION_SET_QUEST_VAR:
        key = addressing
        if not is_quest_var_key(key):
            raise EnvelopeError(
                REASON_INVALID_KEY,
                "key must be a non-empty string, got %r" % (addressing,),
            )
        if str(key) == QUEST_VAR_IGNORED_KEY:
            raise EnvelopeError(
                REASON_IGNORED_KEY,
                "the legacy branch explicitly IGNORES %r (command.py:91-95), so "
                "refusing it reproduces legacy rather than inventing a rule"
                % QUEST_VAR_IGNORED_KEY,
            )
        name = str(key)
        current = state[KEY_QUEST_VARS]
        variables = _copy_vars(current) if isinstance(current, dict) else {}
        # The self-heal is reproduced (command.py:113-114): a recorded None
        # becomes a dict as a side effect of writing any key at all.
        variables[name] = DERIVED_QUEST_VALUE
        state[KEY_QUEST_VARS] = variables
        written = [KEY_QUEST_VARS]
        if name == QUEST_VAR_ALIAS_KEY:
            state[KEY_MISSION] = DERIVED_QUEST_VALUE
            written = [KEY_QUEST_VARS, KEY_MISSION]
        notes.append(DERIVED_QUEST_VALUE_NOTE)
        notes.append(QUEST_VAR_COMMENT_NOTE)
    elif action_text == ACTION_COLLECT_MISSION:
        if not is_mission(addressing):
            raise EnvelopeError(
                REASON_INVALID_MISSION,
                "mission must be an integer, got %r" % (addressing,),
            )
        mission = wrap_mission(addressing)
        state[KEY_MISSION] = str(mission)
        state[KEY_LAST_CHAPTER] = True
        stamps_chapter = True
        state[KEY_QUEST_VARS] = {}
        written = [KEY_MISSION, KEY_LAST_CHAPTER, KEY_QUEST_VARS]
        notes.append(MISSION_WRAP_NOTE)
    elif action_text == ACTION_SET_QUEST_RANK:
        if not is_quest_rank_index(addressing):
            raise EnvelopeError(
                REASON_INVALID_QUEST_INDEX,
                "quest_index must be an integer, got %r" % (addressing,),
            )
        ranks = _copy_ranks(state[KEY_RANKS])
        ranks[str(addressing)] = DERIVED_DIFFICULTY
        state[KEY_RANKS] = ranks
        written = [KEY_RANKS]
        notes.append(DERIVED_DIFFICULTY_NOTE)
    else:  # ACTION_END_QUEST
        if not is_quest_id(addressing):
            raise EnvelopeError(
                REASON_INVALID_QUEST_ID,
                "quest_id must be an integer, got %r" % (addressing,),
            )
        times = _copy_times(state[KEY_QUEST_TIMES])
        times[str(addressing)] = True
        state[KEY_QUEST_TIMES] = times
        written = [KEY_QUEST_TIMES]
        stamps_instant = True
        notes.append(END_QUEST_REFUSAL)
        notes.append(LEDGER_DOOR["status"])
    return {
        "action": action_text,
        "command": command,
        "addressing": addressing if isinstance(addressing, str) else int(addressing),
        "addressing_kind": ACTION_ADDRESSING[action_text],
        "written": written,
        "untouched": [key for key in QUEST_FIELDS if key not in written],
        "derived_state": state,
        "stamps_instant": stamps_instant,
        "stamps_chapter": stamps_chapter,
        "mutates": mutates,
        "notes": notes,
        "reward_paid": REWARD_PAID,
        "destruction": "refused",
    }


def end_quest_blob(quest_id: Any) -> Dict[str, Any]:
    """The server-derived ``end_quest`` JSON blob, in full.

    Every value is :data:`DERIVED_*`.  ``units`` is an **empty list** and that
    empty list **is** the refusal: the legacy destruction loop
    ``for unit in units:`` (``command.py:790``) iterates zero times, so
    ``map_lose_item`` is never called and no placed row is touched.
    ``difficulty`` is :data:`DERIVED_DIFFICULTY`, the floor of the branch's own
    clamp, so no client number is sent.
    """
    if not is_quest_id(quest_id):
        raise EnvelopeError(
            REASON_INVALID_QUEST_ID,
            "quest_id must be an integer, got %r" % (quest_id,),
        )
    return {
        "difficulty": DERIVED_DIFFICULTY_FIELD,
        "duration": DERIVED_DURATION,
        "map": DERIVED_MAP,
        "quest_id": int(quest_id),
        "units": list(DERIVED_UNITS),
        "voluntary_end": DERIVED_VOLUNTARY_END,
        "win": DERIVED_WIN,
    }


def project_quests(state: Dict[str, Any]) -> Dict[str, Any]:
    """The **read-only** projection of the quest state, verbatim.

    Returns
        ``{ok, resolvable, fields, verbatim, derived: {}, branches,
        branch_count, writers, ...}``

    Each of the seven committed fields is reported **exactly as recorded**: no
    scaling, no rounding, no defaulting, no clamping, and no value derived from
    another.  A recorded **``None``** ``currentQuestVars`` is reported as a
    recorded null — ``current_quest_vars_is_null`` is ``true`` and the field
    holds ``None`` — and is **never** presented as an empty map (design D8).
    ``derived`` is an **empty** mapping on purpose: it is the machine-readable
    statement that this projection computes **nothing** — no completion state, no
    remaining time, no progress ratio, and no reward (design D1/D3/D6/D9).

    ``ok`` and ``resolvable`` are ``True`` in **every** projection this function
    returns, because every structural problem raises :class:`EnvelopeError`
    instead of returning a partial projection.  The flags exist so a client can
    distinguish "the state resolved" from "the state was reported anyway", which
    is the same contract :mod:`behavior_envelope` and the client's own
    ``QuestFlow.parse_result`` both rely on.
    """
    if not isinstance(state, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the quest state is %s, not an object" % type(state).__name__,
        )
    for key in QUEST_FIELDS:
        if key not in state:
            raise EnvelopeError(
                REASON_ABSENT_STATE, "the quest state carries no %r" % key
            )
    goals = state[KEY_GOALS]
    if not isinstance(goals, list):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the quest state's %r is not a list" % KEY_GOALS,
        )
    quest_vars = state[KEY_QUEST_VARS]
    return {
        "ok": True,
        "resolvable": True,
        "fields": {
            KEY_GOALS: list(goals),
            KEY_RANKS: _copy_ranks(state[KEY_RANKS]),
            KEY_QUEST_VARS: _copy_vars(quest_vars),
            KEY_QUEST_TIMES: _copy_times(state[KEY_QUEST_TIMES]),
            KEY_MISSION: state[KEY_MISSION],
            KEY_LAST_CHAPTER: state[KEY_LAST_CHAPTER],
            KEY_UNLOCKED_INDEX: state[KEY_UNLOCKED_INDEX],
        },
        "goals_length": len(goals),
        "goals_null_entries": sum(1 for entry in goals if entry is None),
        "current_quest_vars_is_null": quest_vars is None,
        "mission_is_string": isinstance(state[KEY_MISSION], str),
        "quest_field_names": list(QUEST_FIELDS),
        "verbatim": True,
        "derived": {},
        "reward_paid": REWARD_PAID,
        "reward_derived_from_content": False,
        "completion_state": None,
        "unlocked_quest_index_written": False,
        "unlocked_index_note": ZERO_CONSUMER_FIELDS[0]["consequence"],
        "branches": [dict(record) for record in BRANCHES],
        "branch_count": BRANCH_COUNT,
        "writers": [dict(record) for record in WRITERS],
        "writer_count": WRITER_COUNT,
        "fast_forward": FAST_FORWARD_CONTRACT,
        "migration": dict(MIGRATION),
        "content_note": CONTENT_RECORD_NOTE,
        "content_fields": [dict(record) for record in COMMITTED_FIELD_CONSUMERS],
        "refusals": [
            {"refusal": record["refusal"], "implemented": record["implemented"],
             "reason": record["reason"]}
            for record in REFUSALS
        ],
        "refused_destruction": dict(REFUSED_DESTRUCTION),
    }


def expected_state(before: Dict[str, Any], action: str, addressing: Any,
                   after: Dict[str, Any]) -> Optional[str]:
    """The first way the persisted quest state diverges from the derived result.

    The **pure** half of the endpoint's post-execution proof, kept here so the
    capture tool, the endpoint, and the offline tests all compare against ONE
    derivation instead of three hand-written checks (design D6).

    **Every** field is compared: the fields the branch writes by value, except
    the two wall-clock fields which are compared by **shape** and **direction**;
    and every field the branch does **not** own compared by value, so a branch
    that reached one more field than the record names fails here.
    """
    derived = derived_quest(before, action, addressing)
    expected = derived["derived_state"]
    for key in QUEST_FIELDS:
        if key not in after:
            return "the persisted quest state carries no %r after a %s" % (
                key, derived["action"]
            )
    # The no-op branch is checked over the WHOLE state FIRST, so its divergence
    # is reported as the no-op breach it is rather than as a per-field write the
    # branch does not own: `complete_goal` writes NOTHING AT ALL, and every one
    # of its seven fields must be byte-identical (design D3).
    if not derived["mutates"]:
        for key in QUEST_FIELDS:
            if after[key] != before[key]:
                return ("the no-op branch %s changed %r from %r to %r, but the "
                        % (derived["command"], key, before[key], after[key])
                        + "branch writes NOTHING AT ALL")
        return None
    for key in derived["untouched"]:
        if after[key] != before[key]:
            return ("%s changed the untouched %r from %r to %r, which the branch "
                    % (derived["action"], key, before[key], after[key])
                    + "never writes")
    for key in derived["written"]:
        if key == KEY_QUEST_TIMES:
            stamp = after[key].get(str(addressing), None)
            if not is_strict_int(stamp):
                return ("the quest time for %r is %r, not an integer"
                        % (addressing, stamp,))
            if stamp <= 0:
                return ("the quest time for %r is %r, not a positive stamp"
                        % (addressing, stamp,))
            others_before = {
                name: value for name, value in before[key].items()
                if name != str(addressing)
            }
            others_after = {
                name: value for name, value in after[key].items()
                if name != str(addressing)
            }
            if others_after != others_before:
                return ("%s changed another quest time: %r -> %r"
                        % (derived["action"], others_before, others_after))
            continue
        if key == KEY_LAST_CHAPTER:
            stamp = after[key]
            if not is_strict_int(stamp):
                return ("the last-chapter instant is %r, not an integer" % (stamp,))
            previous = before[key]
            if is_strict_int(previous) and int(stamp) < int(previous):
                return ("the last-chapter instant %r moves backwards from %r"
                        % (stamp, previous))
            continue
        if after[key] != expected[key]:
            return ("%r is %r after a %s, not the derived %r"
                    % (key, after[key], derived["action"], expected[key]))
    return None


# ------------------------------------------------------------ the envelope --
def build_envelope(action: str, addressing: Any,
                   ts: Optional[int] = None) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one quest command.

    ``action`` names the closed outcome the service derives a command from, and
    ``addressing`` is that branch's own addressing — the ONE value a client may
    name.  Every other value is :data:`DERIVED_*`.

    The batch carries **exactly one** command and a **neutral** vector (design
    D6): no reward, no cost, no price, and no outcome is expressed here, because
    none is derivable and none is accepted from a client.  For ``set_quest_var``
    the branch's argument list is ``[key, value]``; for ``set_goals`` it is
    ``[goal_index, json_progress]``; for ``end_quest`` it is ``[json_blob]``;
    and for the remaining three it is the single addressing value.  The shapes
    are recorded here rather than assembled per-branch by hand.

    Raises :class:`EnvelopeError` with ``invalid_action``, one of the per-action
    addressing codes, ``invalid_vector``, or ``invalid_timestamp``.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_INVALID_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    checked = validate_vector(neutral_vector())
    command = command_for_action(action)
    action_text = str(action)
    args: List[Any]
    if action_text == ACTION_SET_GOAL:
        if not is_goal_index(addressing):
            raise EnvelopeError(
                REASON_INVALID_GOAL_INDEX,
                "goal_index must be a non-negative integer, got %r" % (addressing,),
            )
        args = [int(addressing), json.dumps(list(DERIVED_PROGRESS),
                                           separators=(",", ":"), sort_keys=True)]
    elif action_text == ACTION_COMPLETE_GOAL:
        if not is_goal_index(addressing):
            raise EnvelopeError(
                REASON_INVALID_GOAL_INDEX,
                "goal_index must be a non-negative integer, got %r" % (addressing,),
            )
        args = [int(addressing)]
    elif action_text == ACTION_SET_QUEST_VAR:
        if not is_quest_var_key(addressing):
            raise EnvelopeError(
                REASON_INVALID_KEY,
                "key must be a non-empty string, got %r" % (addressing,),
            )
        if str(addressing) == QUEST_VAR_IGNORED_KEY:
            raise EnvelopeError(
                REASON_IGNORED_KEY,
                "the legacy branch explicitly IGNORES %r (command.py:91-95)"
                % QUEST_VAR_IGNORED_KEY,
            )
        args = [str(addressing), DERIVED_QUEST_VALUE]
    elif action_text == ACTION_COLLECT_MISSION:
        if not is_mission(addressing):
            raise EnvelopeError(
                REASON_INVALID_MISSION,
                "mission must be an integer, got %r" % (addressing,),
            )
        args = [int(addressing)]
    elif action_text == ACTION_SET_QUEST_RANK:
        if not is_quest_rank_index(addressing):
            raise EnvelopeError(
                REASON_INVALID_QUEST_INDEX,
                "quest_index must be an integer, got %r" % (addressing,),
            )
        args = [int(addressing), DERIVED_DIFFICULTY]
    else:  # ACTION_END_QUEST
        blob = end_quest_blob(addressing)
        args = [json.dumps(blob, separators=(",", ":"), sort_keys=True)]
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError(REASON_INVALID_TIMESTAMP,
                            "ts must be a non-negative integer")
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, command, args, checked]],
    }