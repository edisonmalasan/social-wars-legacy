#!/usr/bin/env python3
"""Derivation of the legacy research-command envelopes and the research model.

M9 line 1 (``research``) — the **fourth** two-track counter surface this
project delivers after ``queue``, ``collection``, and ``behavior``, and the
first one whose commands take a **track index** instead of a map row.

What legacy actually does (established — ``docs/legacy-m9-progression.md``
§11–§13, measured by the hermetic suite in the same run)
    Four dispatcher branches in ``command.py``:

    ==================================== ========= ================================================
    branch                                lines    effect on the addressed track
    ==================================== ========= ================================================
    ``next_research_step(_type)``         268-274  step ``+= 1``; instant ``= time_now``
    ``research_buy_step_cash(cash,_type)`` 276-282  instant ``= 0``; **``cash`` read and DISCARDED**
    ``next_research_item(_type)``         284-291  item ``+= 1``; step ``= 0``; instant ``= 0``
    ``reset_research_item(_type)``        293-300  step ``= 0``; item ``= 0``; instant ``= 0``
    ==================================== ========= ================================================

    The item branch's step reset and instant reset happen **TOGETHER**, in one
    branch, and no other branch resets the step counter — that pairing is
    recorded in :data:`BRANCHES` and asserted by the suite.

**The counters are WRITE-ONLY (established, and the sharpest finding of the
line).**  ``researchStepNumber`` has exactly **3** sites and ``researchItemNumber``
exactly **2**, every one of them a write.  ``timeStampDoResearch`` has exactly
**5**: the four branch writes plus a single read at ``command.py:923`` — and
**that read is itself a write**, because it sits inside ``fast_forward``
(``command.py:905-...``) and does
``research_timers[i] = max(0, research_timers[i] - seconds)`` where
``seconds = args[0]`` is **client-supplied** (``command.py:906``).  So the
research instant has **five writers, four of them branches**, and the fifth
makes the instant **client-writable**.  :data:`FAST_FORWARD_CONTRACT` records
that; **no fast-forward route is implemented anywhere in this repository**
(design D7).

**Nothing anywhere reads a research counter to decide anything.**  A guard
audit of all four branches finds **no** bounds check, **no** numeric clamp,
**no** membership test, **no** exception guard, and **no** existence check.
There is therefore **no** completion test, **no** readiness test, **no**
remaining-time computation, **no** unlock gate, and **no** cost check to
reproduce, and this module computes **none** of them (design D1).  The
delivered feature is the counter mechanics themselves; every derivation beyond
the four recorded effects is refused.

**No price is charged and no stored resource moves (design D3).**
``research_buy_step_cash`` is structurally identical to M8 line 8's
``used_syringe``: it takes the price off the client's argument list, prints
"Buy research step for …", and moves no balance.  ``do_command`` applies the
request's per-command resource vector **before** dispatch (``command.py:40``,
``engine.py:251-271``), so any price a client attached would be a
**client-trusted** mint or burn.  The derived vector is therefore **NEUTRAL**,
and every action's post-execution proof requires that **every** stored resource
be **unchanged**.

**No committed research content exists (design D4).**  No normalized package
carries a research *section*, and no ``config/main.json`` content key is one.
The measured facts are narrower and are recorded in :data:`CONTENT_ABSENCE`:
``research`` appears in exactly **two** normalized files — once inside
``buildings.json``'s building ``256`` ``name`` ("Research Lab"), and in three
``images.json`` rows whose asset names begin ``popupResearchCenter``.  **MEASURED
CORRECTION**: the M9 investigation and the line's proposal both state that
``research`` appears in exactly **one** normalized file and that
``config/main.json`` has **no** key containing ``research`` at any depth.  Both
figures are **wrong** — see :data:`CONTENT_ABSENCE`.  The *conclusion* survives
untouched: there is **no committed research cost, step count, unlock
requirement, or reward**, so none may be derived.

**The two tracks are REPORTED and structurally unusable (design D5).**
``TYPE_AREA_51`` and ``TYPE_ROBOTIC`` appear **only** inside the four branch
comments and are **defined nowhere** in the server.  Their mapping to the
committed building identifiers (``ID_BUILDING_AREA_51 = 139``,
``ID_BUILDING_ROBOTIC_CENTER = 86``) therefore rests on the comment's own word
order together with the four ``print`` statements' own display list
``["Area 51", "Robotic Center"][_type]`` — two independent pieces of evidence in
the committed source.  The mapping is recorded in :data:`TRACKS` and used for
**nothing**: no counter value, no unlock, no requirement, and no cost is derived
from it, and no code identifier in this repository is named after either track
constant.

**No bound, membership rule, or clamp is added (design D6).**  A client could
name track ``7`` and Python would raise ``IndexError`` on a 2-element list; a
client could name ``999`` and the counter would grow without limit.  Both are
legacy behaviours, so the endpoint enforces only **structural** input validity —
the track is an integer inside the two the vector holds, and the vector itself is
well-formed — and records the rest as a Server v1 / M13 gap.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field``, and
    ``EnvelopeError`` — so every delivered derivation, its fixture, and its
    suite keep passing untouched.

The committed corpus target
    ``tests/saves/fresh-player.json`` holds all three counters at ``[0, 0]`` of
    length 2.  That is why this line is the **first M9 line with a real
    executed-legacy fixture**: every one of the four branches is exercisable
    against the corpus as committed, with no fabricated player state.
"""

from __future__ import annotations

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

# ------------------------------------------------------------- the counters --
# The three committed private-state keys a research track occupies, in the
# committed order the four branches write them.  (established: command.py:271,
# 272, 287, 288, 289, 296, 297, 298)
KEY_STEP = "researchStepNumber"
KEY_ITEM = "researchItemNumber"
KEY_INSTANT = "timeStampDoResearch"
COUNTERS: Tuple[str, str, str] = (KEY_STEP, KEY_ITEM, KEY_INSTANT)

# Width of every research vector: one entry per track.  Both tracks, always.
TRACK_COUNT = 2

# ------------------------------------------------------------- the commands --
STEP_COMMAND = "next_research_step"
CASH_COMMAND = "research_buy_step_cash"
ITEM_COMMAND = "next_research_item"
RESET_COMMAND = "reset_research_item"

# The endpoint's own action vocabulary (design D2): the client names an OUTCOME
# and the service chooses the legacy command.  Closed, and echoed exactly as
# sent.
ACTION_STEP = "next_step"
ACTION_BUY_STEP_CASH = "buy_step_cash"
ACTION_ITEM = "next_item"
ACTION_RESET = "reset_item"
ACTIONS: Tuple[str, ...] = (ACTION_STEP, ACTION_BUY_STEP_CASH, ACTION_ITEM, ACTION_RESET)
ACTION_COMMANDS = {
    ACTION_STEP: STEP_COMMAND,
    ACTION_BUY_STEP_CASH: CASH_COMMAND,
    ACTION_ITEM: ITEM_COMMAND,
    ACTION_RESET: RESET_COMMAND,
}

# The branch that also takes a (discarded) cash amount first, so its argument
# list is ``[cash, track]`` while every other branch's is ``[track]``.  The
# contract is what makes the two shapes checkable rather than hand-written.
CASH_ACTION = ACTION_BUY_STEP_CASH
CASH_ARGUMENT_INDEX = 0
TRACK_ARGUMENT_INDEX = {ACTION_BUY_STEP_CASH: 1}

#: The cash value the service derives for the cash branch.  **Derived**, never
#: client-supplied (design D2), and **discarded** by the branch
#: (``command.py:277`` reads ``args[0]`` and never uses it).  Zero is the only
#: honest choice: it asserts no price at all, and because the branch discards
#: the value it cannot change what the executed transaction writes.
DERIVED_CASH = 0

# ------------------------------------------------------------- the branches --
# The recorded command contract, one record per branch, with the committed
# source lines that fix its arguments and its effects.  The ABSENCE of
# validation is a field of every record, because it is the fact that most needs
# stating (design D6).
BRANCHES: Tuple[Dict[str, Any], ...] = (
    {
        "command": STEP_COMMAND,
        "action": ACTION_STEP,
        "source": "command.py:268-274",
        "args": ["track index"],
        "argument_order": "track",
        "counters_written": [KEY_STEP, KEY_INSTANT],
        "effect": "the step counter is INCREMENTED and the research instant is "
            + "stamped with time_now; the item counter is untouched",
        "stamps_instant": True,
        "paired_reset": False,
        "reads_a_price": False,
        "charges": False,
        "validation": "none: no bounds check, no clamp, no membership test, no "
            + "exception guard, and no existence check",
    },
    {
        "command": CASH_COMMAND,
        "action": ACTION_BUY_STEP_CASH,
        "source": "command.py:276-282",
        "args": ["cash", "track index"],
        "argument_order": "cash-then-track",
        "counters_written": [KEY_INSTANT],
        "effect": "the research instant is ZEROED and nothing else is written; "
            + "the step and item counters are untouched",
        "stamps_instant": False,
        "paired_reset": False,
        "reads_a_price": True,
        "charges": False,
        "price_note": "the branch reads args[0] as `cash` (command.py:277) and "
            + "NEVER uses it: it prints 'Buy research step for …' and moves no "
            + "balance. This is the same shape as M8 line 8's discarded "
            + "`used_syringe`",
        "validation": "none: no bounds check, no clamp, no membership test, no "
            + "exception guard, and no existence check — and no cost validation "
            + "either, because the only cost-token match in the branch is its "
            + "own parameter name",
    },
    {
        "command": ITEM_COMMAND,
        "action": ACTION_ITEM,
        "source": "command.py:284-291",
        "args": ["track index"],
        "argument_order": "track",
        "counters_written": [KEY_ITEM, KEY_STEP, KEY_INSTANT],
        "effect": "the item counter is INCREMENTED and the step counter AND the "
            + "research instant are RESET TOGETHER, in this one branch "
            + "(command.py:288-289)",
        "stamps_instant": False,
        # The pairing is the whole point of this record, and it is asserted by
        # the suite against the committed source rather than trusted.
        "paired_reset": True,
        "paired_reset_note": "the step reset and the instant reset happen "
            + "TOGETHER at command.py:288 and command.py:289, in the same "
            + "branch; no other branch resets the step counter, and no "
            + "committed branch ever resets the instant alone",
        "reads_a_price": False,
        "charges": False,
        "validation": "none: no bounds check, no clamp, no membership test, no "
            + "exception guard, and no existence check",
    },
    {
        "command": RESET_COMMAND,
        "action": ACTION_RESET,
        "source": "command.py:293-300",
        "args": ["track index"],
        "argument_order": "track",
        "counters_written": [KEY_ITEM, KEY_STEP, KEY_INSTANT],
        "effect": "all THREE counters are set to 0 for the addressed track and "
            + "nothing else is written",
        "stamps_instant": False,
        "paired_reset": False,
        "reads_a_price": False,
        "charges": False,
        "validation": "none: no bounds check, no clamp, no membership test, no "
            + "exception guard, and no existence check",
    },
)

#: The branch count, pinned so a widening or narrowing of the closed set fails a
#: run instead of silently shipping a different contract.
BRANCH_COUNT = 4

# ---------------------------------------------------------- the four writers --
# Every write to the research instant, with the committed source line.  Four are
# branches; the FIFTH is ``fast_forward`` and is **not** a branch and **not**
# offered by any action (design D7).
INSTANT_WRITERS: Tuple[Dict[str, Any], ...] = (
    {
        "writer": "command:" + STEP_COMMAND,
        "source": "command.py:272",
        "kind": "dispatcher-branch",
        "effect": "instant = time_now",
        "client_writable": False,
    },
    {
        "writer": "command:" + CASH_COMMAND,
        "source": "command.py:280",
        "kind": "dispatcher-branch",
        "effect": "instant = 0",
        "client_writable": False,
    },
    {
        "writer": "command:" + ITEM_COMMAND,
        "source": "command.py:289",
        "kind": "dispatcher-branch",
        "effect": "instant = 0 (together with the step counter's reset)",
        "client_writable": False,
    },
    {
        "writer": "command:" + RESET_COMMAND,
        "source": "command.py:298",
        "kind": "dispatcher-branch",
        "effect": "instant = 0",
        "client_writable": False,
    },
    {
        "writer": "command:fast_forward",
        "source": "command.py:923 (read), command.py:927 (write)",
        "kind": "engine-side decrement inside a dispatcher branch",
        "effect": "for every track: instant = max(0, instant - seconds), where "
            + "`seconds` is the CLIENT-SUPPLIED args[0] (command.py:906)",
        "client_writable": True,
    },
)

#: Five writers of the research instant, four of them dispatcher branches.
INSTANT_WRITER_COUNT = 5
#: The one writer that is not a research branch.
INSTANT_WRITER_FAST_FORWARD = "command:fast_forward"
FAST_FORWARD_COMMAND = "fast_forward"

FAST_FORWARD_CONTRACT = (
    "RECORDED AND IMPLEMENTED NOT AT ALL. The research instant has FIVE writers "
    "(command.py:272, 280, 289, 298, and 927), and the FIFTH is not a research "
    "branch at all: fast_forward (command.py:905) reads the instant at "
    "command.py:923 and subtracts a CLIENT-SUPPLIED number of seconds from "
    "every track's entry at command.py:927, clamped at zero. That makes the "
    "research instant client-writable in exactly the way M8 line 6 found a "
    "row's instant client-writable, and it is named here because it is the ONLY "
    "elapsed-time input the research system has - an instant trusted by "
    "nothing, in a system where nothing reads it. NO fast-forward operation is "
    "delivered by this endpoint, by the client's GameApi, or by the client's "
    "flow, and no elapsed-time, remaining-time, readiness, or completion "
    "behaviour is derived from the instant anywhere in this repository (design "
    "D7)"
)

# --------------------------------------------------- the two tracks, reported --
# The committed track names, carried as **data** so that no code identifier in
# this repository is named after either of them (design D5): the constants
# appear only inside the four branch comments and are defined nowhere in the
# server, so a value equal to a legacy constant name is not evidence that the
# constant exists.
TRACK_NAME_PRIMARY = "TYPE_AREA_51"
TRACK_NAME_SECONDARY = "TYPE_ROBOTIC"

#: The committed building identifiers the two track names resolve to
#: (constants.py:299-300).
COMMITTED_BUILDING_ROBOTIC_CENTER = 86
COMMITTED_BUILDING_AREA_51 = 139
#: The legacy constant names those identifiers are assigned at, recorded so a
#: reader can go and check them without this module adopting them as its own.
COMMITTED_BUILDING_CONSTANTS = {
    "robotic": "constants.py:299 ID_BUILDING_ROBOTIC_CENTER = 86",
    "area_51": "constants.py:300 ID_BUILDING_AREA_51 = 139",
}

TRACKS: Tuple[Dict[str, Any], ...] = (
    {
        "track": 0,
        "name": TRACK_NAME_PRIMARY,
        "display_name": "Area 51",
        "building_id": COMMITTED_BUILDING_AREA_51,
        "building_constant": COMMITTED_BUILDING_CONSTANTS["area_51"],
        "where_named": "only inside the four branch comments "
            + "(command.py:269, 278, 285, 294)",
        "defined_in_server": False,
    },
    {
        "track": 1,
        "name": TRACK_NAME_SECONDARY,
        "display_name": "Robotic Center",
        "building_id": COMMITTED_BUILDING_ROBOTIC_CENTER,
        "building_constant": COMMITTED_BUILDING_CONSTANTS["robotic"],
        "where_named": "only inside the four branch comments "
            + "(command.py:269, 278, 285, 294)",
        "defined_in_server": False,
    },
)

TRACK_RECORD_NOTE = (
    "REPORTED AND NEVER USED. The two track names exist ONLY inside the four "
    "branch comments and are DEFINED NOWHERE in the legacy server: zero "
    "definitions and zero non-comment uses across command.py, engine.py, "
    "sessions.py, server.py, constants.py, get_game_config.py, and "
    "version.py. Their mapping to the committed building identifiers rests on "
    "the comment's own word order plus two further pieces of the committed "
    "source: the four print statements' display list "
    "[\"Area 51\", \"Robotic Center\"][_type]. That is enough to REPORT the "
    "mapping and is not enough to DERIVE anything from it, so no counter "
    "value, unlock, requirement, or cost is computed from a track's name or "
    "building id (design D5). No code identifier in this repository is named "
    "after either track constant, which is what makes the 'never used' claim "
    "mechanical rather than editorial"
)

# ----------------------------------------------------- the recorded absences --
NO_PRICE = (
    "NO RESEARCH PRICE IS CHARGED AND NO STORED RESOURCE MOVES. No committed "
    "content records a research cost, a step count, an unlock requirement, or a "
    "reward, and the one price-taking branch charges nothing: "
    "research_buy_step_cash reads a client-supplied cash value and discards it "
    "(command.py:277), printing 'Buy research step for …' and moving no "
    "balance. Because do_command applies the request's per-command vector "
    "BEFORE dispatch (command.py:40, engine.py:251-271), any price a client "
    "attached would be a client-trusted mint or burn, so the derived vector is "
    "NEUTRAL and every action's post-execution proof requires that EVERY "
    "stored resource be UNCHANGED (design D3). Deriving a price from any "
    "committed field would invent an economy the content does not contain"
)

NO_READINESS = (
    "NO COMPLETION, READINESS, REMAINING-TIME, OR UNLOCK SEMANTICS ARE "
    "IMPLEMENTED, because the legacy server has NONE to reproduce. The three "
    "research counters are WRITE-ONLY: every occurrence of researchStepNumber "
    "and researchItemNumber in the seven legacy modules is a WRITE (3 sites and "
    "2 sites respectively, all writes), and the single read of "
    "timeStampDoResearch outside its own branches is command.py:923 inside "
    "fast_forward - and that read is itself a write. So NOTHING anywhere reads a "
    "research counter to decide anything: there is no server-side completion "
    "test, no readiness test, no remaining-time computation, no unlock gate, "
    "and no cost check. This contract therefore computes NO readiness, NO "
    "remaining time, NO progress ratio, NO completion fraction, and NO derived "
    "step count (design D1). The absence is a recorded property of the legacy "
    "contract, not a missing feature; a later line may introduce any of them "
    "only as its own deliverable, with its own evidence"
)

NO_BOUNDS = (
    "NO COUNTER BOUND, MEMBERSHIP RULE, OR CLAMP IS ADDED. A guard audit of all "
    "four branches finds no bounds check, no numeric clamp, no membership test, "
    "no exception guard, and no existence check: a client naming a track outside "
    "the vector would raise IndexError in legacy, and a client naming a large "
    "track number would let the counter grow without limit. Both are legacy "
    "behaviours, and reproducing them means NOT inventing validation (design "
    "D6). The recorded absence is NOT permission to invent a bound: the only "
    "structural checks here are that the track is an integer the vector "
    "addresses and that the vector itself is well-formed, because a service "
    "that cannot address its own state is not delivering behaviour. An "
    "authoritative limit belongs to Server v1 / M13"
)

NO_REWARD = (
    "NO REWARD IS PAID, AND NONE EXISTS. There is no committed reward for "
    "research anywhere in the content - not even a zero-valued one - so there "
    "is nothing to derive one from and none is invented (design D4). This is the "
    "same shape as the committed level curve's unread reward_type/reward_amount "
    "fields and the quests table's unread reward: a recorded field with no "
    "consumer is a fact, and reading one as a promise would be an invention"
)

#: The four refusal families, each with its non-empty recorded reason.  They are
#: stated as requirements (design D4/D6), not as omissions.
REFUSALS: Tuple[Dict[str, str], ...] = (
    {"refusal": "no_price", "implemented": False, "reason": NO_PRICE},
    {"refusal": "no_readiness", "implemented": False, "reason": NO_READINESS},
    {"refusal": "no_bounds", "implemented": False, "reason": NO_BOUNDS},
    {"refusal": "no_reward", "implemented": False, "reason": NO_REWARD},
)

# --------------------------------------------------------- the content facts --
CONTENT_ABSENCE = (
    "NO COMMITTED RESEARCH CONTENT IS INVENTED. MEASURED over all 22 normalized "
    "files and config/main.json in the same run as this capture: (1) NO "
    "normalized package carries a research SECTION - no file has a top-level "
    "key of any research kind, and all 22 are top-level arrays of domain rows; "
    "(2) the string 'research' appears in exactly TWO normalized files, not "
    "one: buildings.json, ONCE, inside the `name` of legacy_id \"256\" "
    "(\"Research Lab\"), and images.json, in exactly THREE rows whose "
    "`legacy_id`/`path` are popupResearchCenter_buildingProcess.swf and its "
    "_2 and _3 variants - six occurrences in total, all asset references; (3) "
    "config/main.json has ZERO top-level content keys naming research and ZERO "
    "nested content-section keys, but it does have THREE keys containing the "
    "word, all of them under /images (the asset-namespace whose keys are asset "
    "paths by construction), and exactly ONE string value containing it, "
    "/items/244/name = \"Research Lab\". MEASURED CORRECTION: the M9 "
    "investigation and this line's proposal both state that 'research' appears "
    "in exactly ONE normalized file and only inside one `name`, and that "
    "config/main.json has NO key containing 'research' at any depth. BOTH "
    "FIGURES ARE WRONG - it is two files and it is three image keys plus one "
    "value - and both are corrected here rather than shipped. The CONCLUSION is "
    "unchanged and is what matters: there is no committed research cost, step "
    "count, unlock requirement, or reward to derive a schedule from, so none "
    "is invented and no price, step count, requirement, or reward is computed "
    "anywhere in this repository (design D4)"
)

#: The committed facts that ARE reported as content, exactly as measured.
COMMITTED_CONTENT_FACTS: Tuple[Dict[str, Any], ...] = (
    {
        "fact": "the research-lab building",
        "domain": "buildings",
        "legacy_id": "256",
        "name": "Research Lab",
        "where": "packages/game-content/normalized/buildings.json, one `name` value",
        "used_as": "reported; never used to price, time, or gate anything",
    },
    {
        "fact": "the research-center process popups",
        "domain": "images",
        "legacy_ids": [
            "popupResearchCenter_buildingProcess.swf",
            "popupResearchCenter_buildingProcess_2.swf",
            "popupResearchCenter_buildingProcess_3.swf",
        ],
        "where": "packages/game-content/normalized/images.json, three rows' "
            + "`legacy_id` and `path`",
        "used_as": "asset references; no gameplay semantics are claimed from "
            + "them and no asset is rendered",
    },
    {
        "fact": "the two track building identifiers",
        "domain": "legacy constants",
        "area_51": COMMITTED_BUILDING_AREA_51,
        "robotic_center": COMMITTED_BUILDING_ROBOTIC_CENTER,
        "where": "constants.py:299-300",
        "used_as": "reported; never used to derive a counter, an unlock, or a cost",
    },
)

# ---------------------------------------------- the structural input refusals --
REASON_MISSING_TRACK = "missing_track"
REASON_INVALID_TRACK = "invalid_track"
REASON_ABSENT_STATE = "unresolvable_research_state"
REASON_INVALID_VECTOR = "invalid_vector"
REASON_INVALID_TIMESTAMP = "invalid_timestamp"
REASON_INVALID_CASH = "invalid_cash"
REASON_INVALID_ACTION = "invalid_action"

#: The refusal reasons the endpoint can answer with for a **structurally**
#: unresolvable research request.  Only these two are reachable from a request:
#: the track, and the research state itself.
STRUCTURAL_REFUSALS: Tuple[str, str] = (REASON_INVALID_TRACK, REASON_ABSENT_STATE)

# Width of the legacy resource vector [unknown, xp, gold, wood, steel, cash,
# mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# ------------------------------------------------- the committed corpus pins --
# The committed corpus's own research vector, pinned so a corpus drift fails a
# run instead of publishing a different fixture.
COMMITTED_VECTOR: Dict[str, List[int]] = {
    KEY_STEP: [0, 0],
    KEY_ITEM: [0, 0],
    KEY_INSTANT: [0, 0],
}
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
#: The eight branch-track combinations the committed capture covers.
CAPTURED_COMBINATIONS = 8

__all__ = [
    "ACTION_BUY_STEP_CASH",
    "ACTION_COMMANDS",
    "ACTION_ITEM",
    "ACTION_RESET",
    "ACTION_STEP",
    "ACTIONS",
    "BRANCHES",
    "BRANCH_COUNT",
    "CASH_ACTION",
    "CASH_ARGUMENT_INDEX",
    "CASH_COMMAND",
    "COMMITTED_BUILDING_AREA_51",
    "COMMITTED_BUILDING_CONSTANTS",
    "COMMITTED_BUILDING_ROBOTIC_CENTER",
    "COMMITTED_CONTENT_FACTS",
    "COMMITTED_PLACEMENTS",
    "COMMITTED_RESOURCE_BEFORE",
    "COMMITTED_VECTOR",
    "CONTENT_ABSENCE",
    "COUNTERS",
    "CAPTURED_COMBINATIONS",
    "DERIVED_CASH",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "FAST_FORWARD_COMMAND",
    "FAST_FORWARD_CONTRACT",
    "INSTANT_WRITER_COUNT",
    "INSTANT_WRITER_FAST_FORWARD",
    "INSTANT_WRITERS",
    "ITEM_COMMAND",
    "KEY_INSTANT",
    "KEY_ITEM",
    "KEY_STEP",
    "NO_BOUNDS",
    "NO_PRICE",
    "NO_READINESS",
    "NO_REWARD",
    "REASON_ABSENT_STATE",
    "REASON_INVALID_ACTION",
    "REASON_INVALID_CASH",
    "REASON_INVALID_TRACK",
    "REASON_INVALID_TIMESTAMP",
    "REASON_INVALID_VECTOR",
    "REASON_MISSING_TRACK",
    "REFUSALS",
    "RESET_COMMAND",
    "RESOURCE_VECTOR_SLOTS",
    "STEP_COMMAND",
    "STRUCTURAL_REFUSALS",
    "TRACKS",
    "TRACK_COUNT",
    "TRACK_NAME_PRIMARY",
    "TRACK_NAME_SECONDARY",
    "TRACK_RECORD_NOTE",
    "TRACK_ARGUMENT_INDEX",
    "build_envelope",
    "command_for_action",
    "copy_vector",
    "data_field",
    "derived_research",
    "expected_state",
    "is_action",
    "is_strict_int",
    "is_track",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
    "project_research",
    "resolve_vector",
    "snapshot_counters",
    "validate_vector",
]


# ------------------------------------------------------------ the vocabulary --
def is_action(value: Any) -> bool:
    """Whether ``value`` names one of the four closed research actions.

    The set is **closed**: ``fast_forward`` is deliberately **absent** (design
    D7), because its ``seconds`` argument is client-supplied and no evidence
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


def is_track(value: Any) -> bool:
    """Whether ``value`` is a strict integer the two-entry vector addresses.

    ``0`` and ``1`` are the two tracks; anything else is refused **structurally**
    (the endpoint must be able to address its own state).  That is the ONLY
    track rule here: the legacy branches add no membership test, so a track
    outside the vector would raise ``IndexError`` in legacy — a behaviour this
    contract records (design D6) and does not reproduce.
    """
    return is_strict_int(value) and 0 <= int(value) < TRACK_COUNT


# --------------------------------------------------------- derived vector --
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D3).

    A research action's price is **client-sent**: ``do_command`` applies the
    request's per-command vector before the branch runs (``command.py:40``,
    ``engine.py:251-271``), so any price a client attached to a research command
    would be a client-trusted mint or burn.  The committed configuration records
    no research price at all (:data:`CONTENT_ABSENCE`), so the only honest
    vector is the neutral one, and a fresh list is returned on every call so a
    caller can never mutate the derivation for the next one.  **No research
    price is claimed in either direction** — refusing to price research the
    legacy server charges nothing for is the recorded boundary.
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
                "resources_changed slot %d must be an integer, got %r" % (index, value),
            )
        if value != 0:
            raise EnvelopeError(
                REASON_INVALID_VECTOR,
                "resources_changed slot %d is %r: a research action moves no "
                % (index, value)
                + "resource, so only the neutral all-zero vector is derivable",
            )
    return list(vector)


# ------------------------------------------------------------ the vector --
def copy_vector(value: Any) -> List[int]:
    """A fresh copy of one committed research counter vector."""
    return [int(entry) for entry in value]


def resolve_vector(private_state: Any) -> Dict[str, List[int]]:
    """The three committed counter vectors, copied, or a named refusal.

    Returns ``{counter: [v0, v1]}`` for all three committed keys, or raises
    :class:`EnvelopeError` with ``unresolvable_research_state`` naming the first
    counter that is absent, not a list, the wrong length, not all integers, or
    negative.

    **Copies are mandatory, not hygiene.**  The legacy dispatcher mutates these
    very lists in place (``save["privateState"]["researchStepNumber"][_type] +=
    1``), so a vector returned by reference would alias the live state and the
    endpoint's "before" snapshot would report the after-state — the exact
    aliasing ``LegacyBoot.private_collections`` exists to prevent.
    """
    if not isinstance(private_state, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the save's private state is %s, not an object"
            % type(private_state).__name__,
        )
    resolved: Dict[str, List[int]] = {}
    for key in COUNTERS:
        if key not in private_state:
            raise EnvelopeError(
                REASON_ABSENT_STATE,
                "the save's private state carries no %r, so no research track "
                "is addressable" % key,
            )
        value = private_state[key]
        if not isinstance(value, list):
            raise EnvelopeError(
                REASON_ABSENT_STATE,
                "the save's private state %r is %s, not a list"
                % (key, type(value).__name__),
            )
        if len(value) != TRACK_COUNT:
            raise EnvelopeError(
                REASON_ABSENT_STATE,
                "the save's private state %r holds %d entries, not the %d tracks"
                % (key, len(value), TRACK_COUNT),
            )
        for index, entry in enumerate(value):
            if not is_strict_int(entry):
                raise EnvelopeError(
                    REASON_ABSENT_STATE,
                    "the save's private state %r[%d] is %r, not an integer"
                    % (key, index, entry),
                )
            if int(entry) < 0:
                raise EnvelopeError(
                    REASON_ABSENT_STATE,
                    "the save's private state %r[%d] is %r, not a non-negative "
                    "counter" % (key, index, entry),
                )
        resolved[key] = copy_vector(value)
    return resolved


def snapshot_counters(save_document: Any) -> Dict[str, List[int]]:
    """:func:`resolve_vector` over a whole save document's ``privateState``."""
    if not isinstance(save_document, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the save is %s, not an object" % type(save_document).__name__,
        )
    return resolve_vector(save_document.get("privateState"))


# ------------------------------------------------------- the derived effect --
def derived_research(before: Dict[str, List[int]], track: Any,
                     action: str) -> Dict[str, Any]:
    """What one research command does to the addressed track — derived, not read.

    Returns
        ``{action, command, track, step, item, instant, stamps_instant,
        paired_reset, reads_a_price, charges, untouched_counters, other_track}``

    ``step`` and ``item`` are the exact values the branch writes.  ``instant`` is
    ``None`` when the branch writes no new instant and the wall clock when it
    does: the step branch stamps ``time_now``, which is not derivable, so it is
    reported as the sentinel ``True`` and compared **by shape** (a strict
    integer) and **by direction** (**not backwards**) after execution, exactly as
    the queue's start instant is.  ``engine.timestamp_now`` has **one-second**
    resolution, so two commands inside the same second legitimately stamp the
    same value and a strict "moves forward" rule would refuse a correct
    transaction.

    ``untouched_counters`` names every counter the branch does **not** write, and
    ``other_track`` is the addressed track's neighbour's full vector: both are
    exactly checkable after execution, which is what proves a branch touches one
    track and nothing else.
    """
    if not is_track(track):
        raise EnvelopeError(
            REASON_INVALID_TRACK,
            "track must be an integer in 0..%d, got %r" % (TRACK_COUNT - 1, track),
        )
    if not is_action(action):
        raise EnvelopeError(
            REASON_INVALID_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    resolved = {key: list(value) for key, value in before.items()}
    for key in COUNTERS:
        if key not in resolved:
            raise EnvelopeError(
                REASON_ABSENT_STATE, "the before state carries no %r" % key
            )
        if not isinstance(resolved[key], list) or len(resolved[key]) != TRACK_COUNT:
            raise EnvelopeError(
                REASON_ABSENT_STATE,
                "the before state's %r is not a %d-entry vector" % (key, TRACK_COUNT),
            )
    index = int(track)
    action_text = str(action)
    command = ACTION_COMMANDS[action_text]
    step = resolved[KEY_STEP][index]
    item = resolved[KEY_ITEM][index]
    instant = resolved[KEY_INSTANT][index]
    written: List[str] = []
    stamps_instant = False
    paired_reset = False
    if action_text == ACTION_STEP:
        step = step + 1
        stamps_instant = True
        written = [KEY_STEP, KEY_INSTANT]
    elif action_text == ACTION_BUY_STEP_CASH:
        instant = 0
        written = [KEY_INSTANT]
    elif action_text == ACTION_ITEM:
        item = item + 1
        step = 0
        instant = 0
        paired_reset = True
        written = [KEY_ITEM, KEY_STEP, KEY_INSTANT]
    else:  # ACTION_RESET
        step = 0
        item = 0
        instant = 0
        written = [KEY_ITEM, KEY_STEP, KEY_INSTANT]
    return {
        "action": action_text,
        "command": command,
        "track": index,
        "step": step,
        "item": item,
        "instant": True if stamps_instant else instant,
        "stamps_instant": stamps_instant,
        "paired_reset": paired_reset,
        "reads_a_price": action_text == ACTION_BUY_STEP_CASH,
        "charges": False,
        "instant_only": action_text == ACTION_BUY_STEP_CASH,
        "written": written,
        "untouched_counters": [key for key in COUNTERS if key not in written],
        "other_track": TRACK_COUNT - 1 - index,
        "before": {key: copy_vector(value) for key, value in resolved.items()},
    }


def project_research(vector: Dict[str, List[int]]) -> Dict[str, Any]:
    """The **read-only** projection of the counter vector, verbatim.

    Returns
        ``{track_count, tracks, counters, tracks_source, derived: {}}``

    Each track's three counters are reported **exactly as the vector holds
    them**: no scaling, no rounding, no defaulting, no clamping.  ``derived`` is
    an **empty** mapping on purpose — it is the machine-readable statement that
    this projection computes **nothing** from the counters: no remaining time,
    no progress ratio, no completion fraction, and no derived step count
    (design D1).  ``tracks_source`` is the two committed track records, reported
    as content and never used (design D5).
    """
    if not isinstance(vector, dict):
        raise EnvelopeError(
            REASON_ABSENT_STATE,
            "the research state is %s, not an object" % type(vector).__name__,
        )
    rows: List[Dict[str, Any]] = []
    for index in range(TRACK_COUNT):
        rows.append(
            {
                "track": index,
                "step": copy_vector(vector.get(KEY_STEP, [0, 0]))[index],
                "item": copy_vector(vector.get(KEY_ITEM, [0, 0]))[index],
                "instant": copy_vector(vector.get(KEY_INSTANT, [0, 0]))[index],
            }
        )
    return {
        "track_count": TRACK_COUNT,
        "counters": {key: copy_vector(vector[key]) for key in COUNTERS},
        "tracks": rows,
        "verbatim": True,
        "derived": {},
        "tracks_source": [
            {key: value for key, value in record.items()} for record in TRACKS
        ],
        "tracking_note": TRACK_RECORD_NOTE,
    }


def expected_state(before: Dict[str, List[int]], action: str, track: Any,
                   after: Dict[str, List[int]]) -> Optional[str]:
    """The first way the persisted vector diverges from the derived result, or None.

    The **pure** half of the endpoint's post-execution proof, kept here so the
    capture tool, the endpoint, and the offline tests all compare against ONE
    derivation instead of three hand-written checks (design D3).

    Every counter the branch does **not** own is compared **by value**, for the
    addressed track *and* for the untouched track; the derived counters are
    compared by value except the stamped instant, which is compared by **shape**
    (a strict integer) and **not earlier** than the pre-execution one.
    """
    derived = derived_research(before, track, action)
    for key in COUNTERS:
        if key not in after or not isinstance(after[key], list) \
                or len(after[key]) != TRACK_COUNT:
            return ("the persisted %r is not a %d-entry vector after a %s"
                    % (key, TRACK_COUNT, derived["action"]))
    index = int(track)
    other = 1 - index
    for key in COUNTERS:
        if key in derived["untouched_counters"]:
            if after[key][index] != before[key][index]:
                return ("%s changed the addressed track's %r from %r to %r, which "
                        "the branch never writes"
                        % (derived["action"], key, before[key][index],
                           after[key][index]))
        if after[key][other] != before[key][other]:
            return ("%s changed the UNADDRESSED track's %r from %r to %r"
                    % (derived["action"], key, before[key][other], after[key][other]))
    if after[KEY_STEP][index] != derived["step"]:
        return ("the step counter is %r after a %s, not the derived %r"
                % (after[KEY_STEP][index], derived["action"], derived["step"]))
    if after[KEY_ITEM][index] != derived["item"]:
        return ("the item counter is %r after a %s, not the derived %r"
                % (after[KEY_ITEM][index], derived["action"], derived["item"]))
    stamp = after[KEY_INSTANT][index]
    if derived["stamps_instant"]:
        if not is_strict_int(stamp):
            return ("the research instant is %r, not an integer" % (stamp,))
        previous = before[KEY_INSTANT][index]
        if is_strict_int(previous) and int(stamp) < int(previous):
            return ("the research instant %r moves backwards from %r"
                    % (stamp, previous))
    elif stamp != derived["instant"]:
        return ("the research instant is %r after a %s, not the derived %r"
                % (stamp, derived["action"], derived["instant"]))
    return None


# ------------------------------------------------------------ the envelope --
def build_envelope(track: Any, action: str,
                   ts: Optional[int] = None) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one research command.

    ``track`` is the research track index and ``action`` names the closed outcome
    the service derives a command from.  The batch carries **exactly one**
    command and a **neutral** vector (design D3): no cost, no duration, no step
    count, and no outcome is expressed here, because none is derivable and none
    is accepted from a client.

    **The cash branch's argument list is ``[cash, track]`` and every other
    branch's is ``[track]``** — the shape the committed source fixes, recorded so
    the two can never be confused.  The ``cash`` value is :data:`DERIVED_CASH`
    (**0**), derived server-side and never taken from a client (design D2); the
    branch discards it anyway, so no price is claimed in either direction.

    ``ts`` defaults to the current time (derived-provisional; parsed but unread
    by legacy code, so parity normalizes it).  Raises :class:`EnvelopeError` with
    ``invalid_track``, ``invalid_action``, ``invalid_vector``, or
    ``invalid_timestamp``.  What a research step costs, how long it takes, and
    whether a track may be advanced at all are the client's business by design
    D6: the legacy branches validate nothing.
    """
    if not is_track(track):
        raise EnvelopeError(
            REASON_INVALID_TRACK,
            "track must be an integer in 0..%d, got %r"
            % (TRACK_COUNT - 1, track),
        )
    checked = validate_vector(neutral_vector())
    command = command_for_action(action)
    if not is_strict_int(DERIVED_CASH) or DERIVED_CASH < 0:
        raise EnvelopeError(REASON_INVALID_CASH, "the derived cash must be a "
                            "non-negative integer")
    args: List[int] = [int(track)]
    if str(action) == CASH_ACTION:
        args = [DERIVED_CASH, int(track)]
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
