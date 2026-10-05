#!/usr/bin/env python3
"""Derivation of the legacy reward-command envelopes and the reward model.

M10 line 1 (``rewards``) — the two **reward cursors**, and the first M10 line
whose delivered surface is a **transition with no grant behind it at all**.

What legacy actually does (established — ``docs/legacy-m10-rewards.md``,
measured across all **eleven** top-level legacy modules)

    Two dispatcher branches in ``command.py``, twenty lines apart:

    ========================================= ====== =====================================
    branch                                    lines   effect on the addressed private state
    ========================================= ====== =====================================
    ``weekly_reward``                          345-363 stamp ``timeStampMondayBonus``;
                                                     ``weeklyRewardIndex = (v + 1) %
                                                     get_weekly_reward_length()``
    ``win_daily_bonus``                        444-463 stamp ``timestampLastBonus``;
                                                     ``bonusNextId = args[1] + 1``,
                                                     wrapped to ``1`` above a **literal 5**
    ========================================= ====== =====================================

    Both arms of both branches also take **grant-shaped values from the client**
    and neither charges nor credits anything (``command.py:345-358`` places a row
    through ``engine.map_add_item`` and calls ``engine.bought_unit_add`` when the
    client sent five arguments; ``command.py:444-463`` calls ``bought_unit_add``
    **and** ``add_store_item`` when ``args[0] > 0``).  Measured across both
    executed arms: **no stored resource moves**.

**The primary finding is a structural mismatch, not a missing reader (design
D1).**  Both cursors are mis-sized against their own schedules:

    ==================== ========== ================================== ======= ==============
    cursor               bound      how the bound was obtained           rungs   unaddressable
    ==================== ========== ================================== ======= ==============
    ``weeklyRewardIndex`` 5         ``get_weekly_reward_length()`` —     3       **3, 4**
                                     ``max(len(value))`` over the rungs
                                     whose ``value`` is a **list**
    ``bonusNextId``       5         a **hardcoded literal** at           5       **5**
                                     ``command.py:451``
    ==================== ========== ================================== ======= ==============

    So two of five weekly positions and one of five daily positions name **no
    schedule entry at all**, and the mismatch is a disagreement between two
    committed pieces of the *same* feature rather than an absence of code.  It is
    reachable from committed recorded state without any fabrication:
    ``villages/Neutral.json`` records the weekly cursor at **3**, so one recorded
    transaction lands on **4**, and ``villages/Nerri.json`` records **2** and lands
    on **3**.  Both land outside the schedule, which is why the line can
    demonstrate the finding by execution rather than by argument.

**Nothing is granted, and the four-part proof makes that non-tautological
(design D6).**  A grant could land in four distinct places, and every successful
action is checked against all four: no map row, no bought-units append, no
storage entry, and the **complete** stored resource set the service exposes
unchanged.  This module implements the **whole-document leaf allowlist** that
carries that proof — the changed leaves of the recorded document must be a
subset of ``{the addressed cursor, the addressed instant}`` — because a
whole-document diff cannot miss a fifth landing place, and because it names no
foreign field.

**The type letters are reported UNDECODED (design D10).**  The weekly schedule's
own vocabulary is ``g``, ``u``, ``c``.  Six independent searches across all
eleven legacy modules for any letter→resource mapping return **zero**, so
reading ``g`` as gold and ``c`` as cash would be an **invention**, not a
reproduction.  A measured nuance strengthens the refusal: the same three letters
are each declared exactly once in ``constants.py`` under resource-flavoured
names — ``COST_GOLD`` (``constants.py:888``), ``COST_CASH`` (``:889``) and
``TYPE_UNIT`` (``constants.py:857``) — and every one of those three names has
exactly **one** occurrence in total, the declaration itself, and **zero**
consumers.  They belong to the item ``costs`` and item-``type`` vocabularies;
**no legacy module iterates ``costs``**, so nothing bridges them to the reward
``type`` field.

**The daily bound is the recorded literal, and the rejected derivation is
retained (design D4).**  ``command.py:451`` wraps with a hardcoded ``> 5 → 1``.
``DAILY_GOLD_REWARDS`` holds exactly five entries, so its entry count **agrees**
with the literal — and the agreement is a coincidence of the value distribution,
not provenance: the preserved source contains **no reference at all** to that
schedule (measured: zero occurrences across all eleven modules).  The literal is
delivered as the literal; :data:`DAILY_BOUND_REJECTED_DERIVATION` retains the
content-derivation alternative so no later reader can mistake the agreement for a
derivation.

**The instant is stamped and no rule is derived from it (design D8).**  Both
branches write a wall-clock instant.  ``timeStampMondayBonus`` has exactly one
live write and its only other occurrence is **commented out**; it has **no
reader**, so there is no window, cooldown, weekly-period, or "already claimed"
test to reproduce, and none is invented.  Its *name* invites exactly the rule
this contract refuses to write, which is why the absence is a recorded
requirement.  Because the stamp is wall-clock it is a **volatile field**: a
successful execution cannot be compared by whole-document equality, while a
**refusal still can**, because every refusal resolves before the stamp
(design D9).

**Both client-sent values are recorded as divergences, never as parity (design
D5).**  The granted **item** is the obvious one.  The **next id** is the sharper
case, because the divergence is visible inside the preserved source and not only
in the executed record: the branch advances a client-supplied cursor and then, if
it exceeds the literal, **overwrites it with the first position** — so a client
that sent a larger value would have had its recorded cursor moved **backwards**.
A third divergence is recorded with them: the weekly branch selects between
granting and not granting on the client's **argument count**, so the same command
with different arities has two different effects.  This contract has **no arm**;
it reports the boundary and each arm's recorded effect.

**No cursor ever selects a schedule entry (design D3/D7).**  The delivered code
performs no indexing of either schedule by any cursor value, and
:data:`ABSENT_HELPERS` records the helpers that are structurally absent: a
grant helper, a cursor-to-rung selector, a type-letter decoder, an eligibility
test, a cooldown/window test, and an already-claimed comparison.  The reachability
**report** is a set difference over two ranges and deliberately performs no
lookup.

**Ten zero-consumer schedules and seven save-only fields are reported with no
rule (design D11).**  The schedule census is a statement about the **preserved
server's source**: the whole ``globals`` object is *served* to clients, so a
Flash client could have read any of the eleven schedules, and this contract makes
**no claim about what any client did**.  The seven save-only fields are present in
every committed save and in no source line; their origin is labelled an
**inference** from those two measurements rather than a measurement.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field`` and ``EnvelopeError``
    — so every delivered derivation, its fixture, and its suite keep passing
    untouched.  No helper here re-implements one of them.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

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

# ------------------------------------------------------------- the cursors --
# The two reward cursors and the two instants their branches stamp, in the
# committed private-state vocabulary (established: command.py:361-363 and
# 454-455, read from ``save["privateState"]``).
PRIVATE_STATE_KEY = "privateState"

WEEKLY_CURSOR_KEY = "weeklyRewardIndex"
DAILY_CURSOR_KEY = "bonusNextId"
WEEKLY_STAMP_KEY = "timeStampMondayBonus"
DAILY_STAMP_KEY = "timestampLastBonus"

#: ``cursor key -> stamped instant key``.  Both branches write exactly one
#: instant and one cursor, and the mapping is what makes the post-execution
#: leaf allowlist exact.
CURSOR_STAMP: Dict[str, str] = {
    WEEKLY_CURSOR_KEY: WEEKLY_STAMP_KEY,
    DAILY_CURSOR_KEY: DAILY_STAMP_KEY,
}

CURSORS: Tuple[str, str] = (WEEKLY_CURSOR_KEY, DAILY_CURSOR_KEY)
INSTANTS: Tuple[str, str] = (WEEKLY_STAMP_KEY, DAILY_STAMP_KEY)

# ------------------------------------------------------------- the commands --
WEEKLY_COMMAND = "weekly_reward"
DAILY_COMMAND = "win_daily_bonus"

#: The endpoint's own action vocabulary (design D13): the client names an
#: **outcome** and the service chooses the preserved command.  Closed, and echoed
#: exactly as sent.
ACTION_WEEKLY = "weekly"
ACTION_DAILY = "daily"
ACTIONS: Tuple[str, str] = (ACTION_WEEKLY, ACTION_DAILY)

ACTION_COMMAND: Dict[str, str] = {
    ACTION_WEEKLY: WEEKLY_COMMAND,
    ACTION_DAILY: DAILY_COMMAND,
}

#: The **inverse** of :data:`ACTION_COMMAND`, derived rather than hand-written,
#: because a second copy of a two-entry mapping is exactly where the two reward
#: branches could silently swap.  The inversion is asserted total and injective
#: below: if a third action were ever added with a duplicate command name, the
#: import would fail here rather than at the first request.
ACTION_FOR_COMMAND: Dict[str, str] = {
    command: action for action, command in ACTION_COMMAND.items()
}

assert len(ACTION_FOR_COMMAND) == len(ACTION_COMMAND), (
    "two actions share one command name; the inverse is not injective"
)

#: ``action -> the addressed cursor``.  One cursor per action, so the request
#: carries no addressing key at all (design D13).
ACTION_CURSOR_KEY: Dict[str, str] = {
    ACTION_WEEKLY: WEEKLY_CURSOR_KEY,
    ACTION_DAILY: DAILY_CURSOR_KEY,
}

#: ``action -> the stamped instant``.
ACTION_STAMP_KEY: Dict[str, str] = {
    ACTION_WEEKLY: WEEKLY_STAMP_KEY,
    ACTION_DAILY: DAILY_STAMP_KEY,
}

#: **EXPLICIT, and deliberately empty** (design D13).  Neither preserved branch
#: addresses a map row, a collection, a track, or any other identity — both are
#: whole-player private-state writes — so neither action carries an addressing
#: key.  This is recorded as an empty mapping **rather than left to a default**
#: because the quests line's largest cross-layer defect was exactly this shape:
#: a transport that assumed one addressing key was universal while the service
#: read a per-action one.  An empty table cannot be misread as "look it up
#: somewhere"; :func:`addressing_key_for` raises rather than defaulting, so a
#: caller that wants one is told there is none.
ACTION_ADDRESSING_KEY: Dict[str, str] = {}

ADDRESSING_KEY_NOTE = (
    "RECORDED EXPLICITLY RATHER THAN DEFAULTED (design D13). Both preserved "
    "branches write only whole-player private state - weeklyRewardIndex with "
    "timeStampMondayBonus, bonusNextId with timestampLastBonus - and neither "
    "names a map row, a collection, a track, or any other identity, so NEITHER "
    "action carries an addressing key. The quests line's largest cross-layer "
    "defect was a transport that sent one fixed 'addressing' key while the "
    "service read a per-action key; a transport here must send no addressing key "
    "at all, and this table plus addressing_key_for() are how that absence is "
    "stated rather than assumed"
)

#: The number of arguments each action's derived command carries.  The weekly
#: action sends **zero** — which is what selects the preserved branch's short arm
#: (``len(args) > 4`` is false at ``command.py:346``) — and the daily action
#: sends exactly the two the branch reads, both derived here.
ACTION_ARGUMENT_COUNT: Dict[str, int] = {
    ACTION_WEEKLY: 0,
    ACTION_DAILY: 2,
}

#: The daily branch reads ``args[0]`` as the granted item and ``args[1]`` as the
#: next cursor id (``command.py:445-446``).  The first is **derived** at zero so
#: the branch's ``item > 0`` test is false and it takes the ``else`` arm that
#: prints "Rewarded resources" and grants nothing (``command.py:462-463``); the
#: second is the **recorded cursor**, which the branch advances by one itself.
DERIVED_DAILY_ITEM = 0
DERIVED_DAILY_ITEM_SOURCE = "command.py:458 (item > 0)"

#: Width of the legacy resource vector.  ``engine.apply_resources``
#: (``engine.py:251-271``) unpacks exactly eight slots, in this order: unknown,
#: xp, gold, wood, oil, steel, cash, mana.  MEASURED CORRECTION to this comment,
#: which first listed seven names and dropped ``oil`` between wood and steel --
#: the count was right and the enumeration was wrong, which is the worse defect of
#: the two because it reads as a transcription of the source.  All eight are
#: written to the save except ``unknown``, which is read and discarded.
#:
#: ``privateState.energy`` is a real ninth stored resource under its own name and
#: is **not** a slot of this vector: ``apply_resources`` never writes it, and the
#: eight-slot mutation vector has no room for it.  The route's snapshot therefore
#: carries nine slots, and the energy half of the "no stored resource moved" proof
#: comes from the whole-document containment half rather than from this vector.
RESOURCE_VECTOR_SLOTS = 8

# ----------------------------------------------------------- the two bounds --
#: ``get_weekly_reward_length`` seeds its accumulator at 1
#: (``get_game_config.py:198``) and then takes ``max`` over the entries whose
#: ``value`` is a **list`` (``:199-202``).  Transcribed verbatim, because the seed
#: is load-bearing: a schedule whose every value were a scalar would return 1.
WEEKLY_BOUND_FLOOR = 1
WEEKLY_BOUND_SOURCE = "get_game_config.py:195-204 (get_weekly_reward_length)"

#: The **hardcoded literal** at ``command.py:451`` and the position it wraps to.
#: Transcribed from the preserved source; never derived from content (design D4).
DAILY_BOUND_LITERAL = 5
DAILY_WRAP_TARGET = 1
DAILY_BOUND_SOURCE = "command.py:451-452 (a hardcoded literal, `if next_id > 5:`)"

DAILY_BOUND_REJECTED_DERIVATION = (
    "REJECTED ALTERNATIVE, RETAINED ON PURPOSE (design D4). DAILY_GOLD_REWARDS "
    "holds exactly five entries, so its entry count agrees with the literal at "
    "command.py:451, and the two numbers could be read as one deriving the "
    "other. THEY ARE NOT. The preserved source contains NO reference to that "
    "schedule at all: measured across all eleven top-level legacy modules "
    "(auctions.py, bundle.py, command.py, constants.py, engine.py, "
    "get_game_config.py, get_player_info.py, legacy_command_recorder.py, "
    "server.py, sessions.py, version.py) the name DAILY_GOLD_REWARDS occurs "
    "ZERO times. The agreement is therefore a coincidence of the value "
    "distribution and NOT provenance, and this contract applies the literal as "
    "the literal. This note exists so a later reader who notices that five "
    "equals five cannot conclude that a derivation was chosen and then dropped: "
    "it never was. The same reasoning runs the other way round for the weekly "
    "bound, which IS derived - but from the schedule's LIST-VALUED entries, not "
    "from its entry count, and the two numbers differ (5 against 3)"
)

# ------------------------------------------------- the index bases and reach --
#: Both reachability reports read a cursor as a **zero-based** position into its
#: own schedule.  That reading is **derived-provisional**: it is recorded with
#: the one-based alternative retained, and it is the reading under which the
#: committed mismatch is a *mismatch* rather than an absence of one - a one-based
#: reading of ``MONDAY_BONUS_REWARDS`` would make its three rungs cover weekly
#: positions 1..3 and leave 4 and 5 unaddressed instead of 3 and 4.
SCHEDULE_INDEX_BASE = 0
SCHEDULE_INDEX_BASE_ALTERNATIVE = 1
SCHEDULE_INDEX_BASE_STATUS = (
    "DERIVED-PROVISIONAL, with the alternative retained. Both reachability "
    "reports read a cursor as a ZERO-BASED position into its own schedule "
    "(SCHEDULE_INDEX_BASE = 0). The preserved server never indexes either "
    "schedule, so nothing in the source fixes the base; what fixes it here is "
    "that the zero-based reading is the one under which the committed data "
    "carries a MISMATCH: weeklyRewardIndex is recorded at 0..3 across the "
    "committed documents and the zero-based reading makes the derived bound (5) "
    "exceed the schedule's cardinality (3). A one-based reading would still "
    "leave positions unaddressed - 4 and 5 weekly, 5 daily - but it would do so "
    "on a different set, so the reported difference would name positions that "
    "are not the ones the recorded cursors reach. Both readings are recorded; "
    "neither is asserted as fact, and neither is used to select a schedule entry "
    "because this contract never selects one at all (design D3)"
)

#: The positions each cursor can **reach**, over every non-negative recorded
#: value.  Both are closed ranges, computed by the preserved branch's own
#: arithmetic rather than asserted:
#:
#: * weekly — ``(v + 1) % 5`` for every ``v`` in ``0..4`` yields exactly
#:   ``0..4``;
#: * daily  — ``v + 1`` clamped to the literal yields exactly ``1..5``.
#:
#: Both sets therefore name every position the branch can write, and the
#: difference against each schedule's cardinality is the line's finding.
WEEKLY_REACHABLE: Tuple[int, ...] = tuple(range(0, DAILY_BOUND_LITERAL))
DAILY_REACHABLE: Tuple[int, ...] = tuple(range(DAILY_WRAP_TARGET, DAILY_BOUND_LITERAL + 1))

#: ``action -> the reachable positions``, reported beside each schedule.
ACTION_REACHABLE: Dict[str, Tuple[int, ...]] = {
    ACTION_WEEKLY: WEEKLY_REACHABLE,
    ACTION_DAILY: DAILY_REACHABLE,
}

#: ``action -> the committed schedule whose positions the cursor is measured
#: against**.  The weekly schedule is read for its **length only** by the single
#: legacy consumer (``get_game_config.py:197``); the daily schedule is read by
#: **nothing at all**.
ACTION_SCHEDULE_KEY: Dict[str, str] = {
    ACTION_WEEKLY: "MONDAY_BONUS_REWARDS",
    ACTION_DAILY: "DAILY_GOLD_REWARDS",
}

#: The two schedule keys by name, **derived from** :data:`ACTION_SCHEDULE_KEY`
#: rather than transcribed beside it.  The fixture capture needs to index the
#: committed ``globals`` object with them, and a second hand-written copy of a
#: schedule name is a place where a mistranscription could hide: the weekly bound
#: this line derives is computed *from that very object*, so a wrong key here
#: would silently produce a wrong bound that still looked self-consistent.  One
#: table, two names.
WEEKLY_SCHEDULE_KEY = ACTION_SCHEDULE_KEY[ACTION_WEEKLY]
DAILY_SCHEDULE_KEY = ACTION_SCHEDULE_KEY[ACTION_DAILY]

#: The committed globals section the eleven reward schedules live in.
GLOBALS_KEY = "globals"

# ---------------------------------------------------- the eleven schedules --
#: Every committed ``globals`` entry whose name carries a reward, a bonus, or a
#: prize, with the **measured** number of occurrences of that exact name across
#: all eleven top-level legacy modules.  Ten of the eleven have **zero**, and the
#: one that does not is read for its **length only** - ``get_game_config.py:197``
#: passes the list to ``get_weekly_reward_length`` and no code path returns a
#: rung, an item, or an amount from it.
SCHEDULES: Tuple[Dict[str, Any], ...] = (
    {
        "name": "ALLIANCE_DAILY_BONUS_REWARDS",
        "consumers": 0,
        "consumed_for": None,
    },
    {
        "name": "DAILY_GOLD_REWARDS",
        "consumers": 0,
        "consumed_for": None,
    },
    {
        "name": "MANA_REWARD_PER_LEVEL",
        "consumers": 0,
        "consumed_for": None,
    },
    {
        "name": "MONDAY_BONUS_REWARDS",
        "consumers": 1,
        "consumed_for": "length only, via get_weekly_reward_length "
            + "(get_game_config.py:197)",
    },
    {"name": "NEWFRIENDS_REWARD_DESCRIPTION", "consumers": 0, "consumed_for": None},
    {"name": "NEWFRIENDS_REWARD_ID_UNIT", "consumers": 0, "consumed_for": None},
    {"name": "NEWFRIENDS_REWARD_SCALE_UNIT", "consumers": 0, "consumed_for": None},
    {"name": "PRIZE_COLLECTIONS_CASH", "consumers": 0, "consumed_for": None},
    {"name": "RECRUITMENT_PRIZE", "consumers": 0, "consumed_for": None},
    {"name": "REWARDS_CHAPTERS", "consumers": 0, "consumed_for": None},
    {"name": "REWARDS_QUESTS", "consumers": 0, "consumed_for": None},
)

SCHEDULE_COUNT = len(SCHEDULES)
SCHEDULE_NAMES: Tuple[str, ...] = tuple(str(row["name"]) for row in SCHEDULES)
SCHEDULES_WITH_NO_CONSUMER: Tuple[str, ...] = tuple(
    str(row["name"]) for row in SCHEDULES if int(row["consumers"]) == 0
)
SCHEDULES_WITH_NO_CONSUMER_COUNT = len(SCHEDULES_WITH_NO_CONSUMER)

#: The commit the schedules are counted against, so a reader knows exactly what
#: "zero consumers" was measured over.
SCHEDULE_CENSUS_MODULES: Tuple[str, ...] = (
    "auctions.py",
    "bundle.py",
    "command.py",
    "constants.py",
    "engine.py",
    "get_game_config.py",
    "get_player_info.py",
    "legacy_command_recorder.py",
    "server.py",
    "sessions.py",
    "version.py",
)
SCHEDULE_CENSUS_NOTE = (
    "A STATEMENT ABOUT THE PRESERVED SERVER'S SOURCE, AND NOTHING ELSE. The "
    "whole globals object is SERVED to clients, so a Flash client could have "
    "read any of these eleven schedules; 'zero consumers' means no preserved "
    "server module names the schedule, and this repository makes NO claim about "
    "what any client did with the bytes it was served. The count is over all "
    "eleven top-level legacy modules: "
    + ", ".join(SCHEDULE_CENSUS_MODULES)
    + " (design D11)"
)

#: The committed ranking-reward table, owned as normalized content by
#: ``economy-schedules-normalization`` and ``content-validation``, and
#: **undelivered as gameplay** by this line.  Those are two different states and
#: the record does not collapse them (design D11, task 5.2).
RANKING_REWARD_TABLE = "level_ranking_reward"
RANKING_REWARD_CONSUMERS = 0
RANKING_REWARD_ENTRY_COUNT = 50
RANKING_REWARD_OWNERSHIP = (
    "OWNED AS NORMALIZED CONTENT, UNDELIVERED AS GAMEPLAY. The table holds 50 "
    "committed entries and has ZERO occurrences across all eleven top-level "
    "legacy modules. It is delivered as normalized content by the "
    "economy-schedules-normalization and content-validation capabilities; this "
    "line delivers NO gameplay that reads it, and neither statement implies the "
    "other: content being validated is not content being played"
)

# ------------------------------------------------------- the type letters --
#: The weekly schedule's own type vocabulary, verbatim, and **undecoded**.
TYPE_LETTERS: Tuple[str, str, str] = ("g", "u", "c")

#: The six independent searches, each with its **regex**, so the count is a
#: measurement a test can re-derive rather than a figure this module asserts, and
#: each with its **measured** hit count across all eleven legacy modules.  Every
#: one is zero, which is why reading a letter as a resource name would be an
#: invention rather than a reproduction (design D10).
DECODER_SEARCHES: Tuple[Dict[str, Any], ...] = (
    {
        "search": "a single-letter key 'g' followed by gold or coins",
        "pattern": r"[\"']g[\"']\s*:\s*[\"']?(gold|coins)",
        "hits": 0,
    },
    {
        "search": "a single-letter key 'c' followed by cash",
        "pattern": r"[\"']c[\"']\s*:\s*[\"']?cash",
        "hits": 0,
    },
    {
        "search": "a single-letter key 'u' followed by unit",
        "pattern": r"[\"']u[\"']\s*:\s*[\"']?unit",
        "hits": 0,
    },
    {
        "search": "any single-letter dictionary key at all",
        "pattern": r"[\"'][a-zA-Z][\"']\s*:",
        "hits": 0,
    },
    {
        "search": "any branch comparing a type field against a one-letter string",
        "pattern": r"[\"']type[\"']\s*==\s*[\"'][a-zA-Z][\"']",
        "hits": 0,
    },
    {
        "search": "any subscript of a reward object by its 'type' key",
        "pattern": r"\[[\"']type[\"']\]",
        "hits": 0,
    },
)
DECODER_SEARCH_COUNT = len(DECODER_SEARCHES)
DECODER_SEARCH_HIT_TOTAL = sum(int(row["hits"]) for row in DECODER_SEARCHES)

#: Positive controls for the six searches above, so a zero is a measurement
#: rather than a broken pattern.  Two-letter dictionary keys and string-keyed
#: subscripts both match abundantly in the same corpus, which is what makes the
#: single-letter results meaningful.
#:
#: MEASURED CORRECTION, retained here rather than quietly fixed.  This table was
#: first written with the second control at **234** occurrences under the label
#: "a subscript by a string key".  Re-measuring with the regexes now carried
#: above gives **515** occurrences and **409** distinct lines for that pattern.
#: 234 is the distinct-line count of a **different** pattern -- an **unquoted**
#: subscript ``\\w\\[[a-zA-Z0-9]*\\]`` (244 occurrences over 234 lines), which
#: matches list indices rather than string keys.  The recorded number was
#: therefore a real measurement of the wrong search, and its label was wrong with
#: it: labelling an unquoted list index "a subscript by a string key" would have
#: claimed a string-keyed search that was never counted.  The conclusion is
#: unchanged -- the control still matches an order of magnitude more often than
#: any single-letter pattern -- but the figure and the pattern are now the ones
#: the label names, and both are re-derived by the offline suite.
DECODER_POSITIVE_CONTROLS: Tuple[Dict[str, Any], ...] = (
    {
        "search": "a two-letter dictionary key",
        "pattern": r"[\"'][a-zA-Z]{2}[\"']\s*:",
        "hits": 4,
    },
    {
        "search": "a subscript by a string key",
        "pattern": r"\[[\"'][a-zA-Z_][a-zA-Z0-9_]*[\"']\]",
        "hits": 515,
    },
    {
        "search": "an unquoted subscript, a list index rather than a string key",
        "pattern": r"\w\[[a-zA-Z0-9]*\]",
        "hits": 244,
    },
)
DECODER_POSITIVE_CONTROL_NOTE = (
    "The six zero results above are MEASURED, not assumed. These positive "
    "controls run over the same eleven modules with the same machinery -- every "
    "row now carries its own regex, and the offline suite re-derives every count "
    "from the committed bytes on each run -- and all match abundantly, so the "
    "single-letter patterns are specific rather than silent. A census that "
    "reports only zeros and never checks that its own patterns fire has produced "
    "the vacuous-census defect three times in this "
    "project, so the controls are part of the record"
)

#: The measured nuance that **strengthens** the refusal.  The same three letters
#: are each declared exactly once under a resource-flavoured name, and every one
#: of those names has exactly one occurrence in total - the declaration - and
#: zero consumers.  They belong to the item ``costs`` and item-``type``
#: vocabularies, and **no legacy module iterates ``costs``**, so nothing bridges
#: them to the reward ``type`` field.
LETTER_NAMED_DECLARATIONS: Tuple[Dict[str, Any], ...] = (
    {
        "letter": "g",
        "declared_as": "COST_GOLD",
        "declared_at": "constants.py:888",
        "occurrences_total": 1,
        "consumers": 0,
        "belongs_to": "the item costs vocabulary",
    },
    {
        "letter": "c",
        "declared_as": "COST_CASH",
        "declared_at": "constants.py:889",
        "occurrences_total": 1,
        "consumers": 0,
        "belongs_to": "the item costs vocabulary",
    },
    {
        "letter": "u",
        "declared_as": "TYPE_UNIT",
        "declared_at": "constants.py:857",
        "occurrences_total": 1,
        "consumers": 0,
        "belongs_to": "the item type vocabulary",
    },
)
LETTER_NAMED_DECLARATION_COUNT = len(LETTER_NAMED_DECLARATIONS)

TYPE_LETTERS_UNDECODED_NOTE = (
    "REPORTED VERBATIM AND NOT DECODED (design D10). The weekly schedule's own "
    "vocabulary is 'g', 'u' and 'c'. Six independent searches across all eleven "
    "top-level legacy modules for any letter-to-resource mapping return ZERO in "
    "each case, and two positive controls confirm the patterns themselves fire "
    "on the same corpus, so the zeros are measurements rather than silence. "
    "Reading 'g' as gold and 'c' as cash is the obvious next step and would be "
    "an INVENTION, not a reproduction: no preserved module maps any of these "
    "letters onto a stored resource slot, an item category, or a grant shape. A "
    "measured nuance strengthens the refusal rather than weakening it - the same "
    "three letters are each declared exactly once in constants.py under "
    "resource-flavoured names (COST_GOLD at constants.py:888, COST_CASH at "
    "constants.py:889, TYPE_UNIT at constants.py:857), every one of those three "
    "names has exactly ONE occurrence in total, the declaration itself, and ZERO "
    "consumers, they belong to the item costs and item-type vocabularies rather "
    "than to the reward type field, and NO legacy module iterates costs at all, "
    "so nothing bridges them"
)

# ------------------------------------------------- the seven save-only fields --
#: Present in **every** committed save document and in **no** source line.  Their
#: origin is an **inference** from those two measurements, not a measurement.
SAVE_ONLY_FIELDS: Tuple[str, ...] = (
    "attacksSent",
    "attacksPack",
    "attacksReceived",
    "bestUnit",
    "betWin",
    "spyings",
    "strategy",
)
SAVE_ONLY_FIELD_COUNT = len(SAVE_ONLY_FIELDS)
SAVE_ONLY_DOCUMENT_COUNT = 33

SAVE_ONLY_ORIGIN_STATUS = "inference, not a measurement"
SAVE_ONLY_NOTE = (
    "SAVE-ONLY FIELDS, REPORTED WITH NO RULE. Each of these %d fields is present "
    "in all %d committed save documents and occurs ZERO times in any of the "
    "eleven top-level legacy modules. MEASURED CORRECTION to the committed "
    "investigation, which recorded 39 documents and reported the field count as "
    "39/39: the committed document census is **33**, being the two documents "
    "under tests/saves plus the eight under villages/ plus the twenty-three "
    "under villages/quest/. The non-zero distributions match the investigation "
    "exactly and only the denominator and the zero count differ, so no conclusion "
    "changes. A SUBSTRING artifact is also recorded rather than dropped: "
    "'betWin' has exactly one whole-file occurrence, at auctions.py:176, inside "
    "the longer identifier betWinner - so it is not a consumer of this field. "
    "Their ORIGIN IS LABELLED AN INFERENCE: written by some client this "
    "repository does not contain, read by nothing this repository does contain. "
    "That is a conclusion drawn from total source absence alongside universal "
    "save presence, and it is not itself a measurement (design D11)"
    % (SAVE_ONLY_FIELD_COUNT, SAVE_ONLY_DOCUMENT_COUNT)
)

#: The two cursors' recorded distributions across the same census, reported
#: because they are what makes the weekly mismatch **reachable** from committed
#: state rather than hypothetical.
CURSOR_DISTRIBUTIONS: Tuple[Dict[str, Any], ...] = (
    {
        "cursor": WEEKLY_CURSOR_KEY,
        "documents": SAVE_ONLY_DOCUMENT_COUNT,
        "distribution": {"0": 26, "1": 5, "2": 1, "3": 1},
        "advanced_documents": 7,
        "note": "MEASURED CORRECTION, retained here rather than quietly fixed. "
            + "This note first read 'so those seven can reach positions 1..4 - "
            + "three of which name no schedule entry'. Both figures were wrong. "
            + "The seven advanced documents record the cursors 1 (five times), 2 "
            + "and 3, so under the derived bound of 5 they land on exactly {2, 3, "
            + "4} - and the schedule's cardinality is 3, so TWO of those "
            + "positions (3 and 4) name no entry, not three. The set 1..4 is what "
            + "all thirty-three documents reach collectively, including the "
            + "twenty-six at cursor 0, which land on 1; it is not what the seven "
            + "reach. The corrected pair is asserted against the committed "
            + "documents by the offline suite on every run",
    },
    {
        "cursor": DAILY_CURSOR_KEY,
        "documents": SAVE_ONLY_DOCUMENT_COUNT,
        "distribution": {"0": 7, "2": 24, "3": 2},
        "advanced_documents": 26,
        "note": "twenty-six of the thirty-three recorded documents carry a "
            + "non-zero cursor, so the daily path has genuinely run against "
            + "committed documents",
    },
)

# ------------------------------------------------------ the preserved arms --
#: The private-state list the weekly branch's long arm appends to, named here
#: **without naming it after itself** (task 5.3).  ``engine.bought_unit_add``
#: (``engine.py:86-89``) deduplicates into it, and the field is **owned by the
#: ``godot-unit-instances`` capability**; this contract neither delivers nor
#: interprets it, it only appears as a *name* so the fixture capture can read
#: what the preserved oracle actually did to it and report the divergence.  The
#: constant is deliberately not called after the field, so no delivered
#: identifier in this package carries that shape, and the boundary stays a
#: hand-off to an owning capability rather than an orphan.
WEEKLY_UNIT_LIST_KEY = "boughtUnits"

#: The storage mapping the daily branch's granting arm writes to, for the same
#: reason and under the same rule: **owned by ``godot-stored-item-placement``**.
DAILY_STORE_KEY = "store"

#: The placed-row mapping the weekly branch's long arm writes to, owned by
#: ``godot-building-placement``.
MAP_ITEMS_KEY = "items"

#: The weekly branch's two arms, selected by the client's **argument count** and
#: by nothing else (``command.py:346``).  This contract has **no arm**; the table
#: is the boundary report (design D5).
WEEKLY_ARMS: Tuple[Dict[str, Any], ...] = (
    {
        "arm": "long",
        "selected_when": "the client sent five or more arguments",
        "test": "len(args) > 4",
        "source": "command.py:346",
        "grant_shaped": True,
        "effect": "the branch reads five client-supplied values - the map index, "
            + "the item id, the two cell coordinates and the player team - places "
            + "a row through engine.map_add_item, records the item through "
            + "engine.bought_unit_add, and prints 'Won <name>'",
        "printed": "Won <name>",
        "reproduced": False,
    },
    {
        "arm": "short",
        "selected_when": "the client sent four or fewer arguments",
        "test": "len(args) <= 4",
        "source": "command.py:357",
        "grant_shaped": False,
        "effect": "the branch grants nothing at all, prints 'Won resources', and "
            + "falls straight through to the stamp and the cursor advance",
        "printed": "Won resources",
        "reproduced": False,
    },
)

#: The daily branch's two arms, selected by the **client-supplied item** and by
#: nothing else (``command.py:458``).
DAILY_ARMS: Tuple[Dict[str, Any], ...] = (
    {
        "arm": "granting",
        "selected_when": "the client sent a positive item",
        "test": "item > 0",
        "source": "command.py:458",
        "grant_shaped": True,
        "effect": "the branch calls engine.bought_unit_add AND "
            + "engine.add_store_item, then prints 'Put <name> in storage'. The "
            + "first helper DEDUPLICATES (it appends only when the id is "
            + "absent, engine.py:86-89) and the second ACCUMULATES (it "
            + "increments an existing key, engine.py:70-75), so one granted id "
            + "lands in two places by two different rules",
        "printed": "Put <name> in storage",
        "reproduced": False,
    },
    {
        "arm": "resources",
        "selected_when": "the client sent zero or a negative item",
        "test": "item <= 0",
        "source": "command.py:462",
        "grant_shaped": False,
        "effect": "the branch grants nothing, moves no resource, and prints "
            + "'Rewarded resources'",
        "printed": "Rewarded resources",
        "reproduced": False,
    },
)

ARMS_REPORT_NOTE = (
    "THE ARM BOUNDARY IS REPORTED, NOT REPRODUCED (design D5). Both preserved "
    "branches select between granting and not granting on a value the CLIENT "
    "sent - the weekly branch on its own ARGUMENT COUNT, so the same command "
    "with different arities has two different effects, and the daily branch on "
    "the sign of a client-supplied item id. This contract has NO arm: it always "
    "sends the non-granting argument list, always grants nothing, and reports "
    "both arms' recorded effects so a reader sees what the arity and the sign "
    "would have selected. Reproducing either arm would mean accepting the "
    "grant-shaped value from a client, which is exactly what the request "
    "contract refuses"
)

#: The three recorded divergences, each with the reason it is a divergence and
#: never parity.
DIVERGENCES: Tuple[Dict[str, str], ...] = (
    {
        "id": "client_sent_item",
        "summary": "the granted item id is taken from the client",
        "where": "command.py:348 (weekly) and command.py:445 (daily)",
        "consequence": "a recorded transaction establishes NOTHING about what "
            + "was granted, because the grant was whatever the client asked for",
        "reproduced": False,
    },
    {
        "id": "client_sent_next_id",
        "summary": "the next cursor id is taken from the client and then "
            + "overwritten when it exceeds the literal",
        "where": "command.py:446 and 451-452",
        "consequence": "the preserved branch advances a CLIENT-SUPPLIED value, "
            + "so a client that sent a larger id would have had its recorded "
            + "cursor moved BACKWARDS onto the first position. This divergence "
            + "is observable in the preserved SOURCE, not only in an executed "
            + "record, which is what makes it the sharper of the two",
        "reproduced": False,
    },
    {
        "id": "client_sent_argument_count",
        "summary": "the weekly arm is selected by the client's argument count",
        "where": "command.py:346",
        "consequence": "the same command with five arguments places a row and "
            + "with four grants nothing, so the preserved command name alone "
            + "does not determine what it did",
        "reproduced": False,
    },
)

#: The rejected alternative to refusing a client-supplied cursor (design D2).
CLIENT_CURSOR_REJECTED_ALTERNATIVE = (
    "REJECTED ALTERNATIVE, RETAINED ON PURPOSE (design D2). A client-supplied "
    "next id could be IGNORED rather than refused: read the request, discard the "
    "value, and derive the successor from the recorded cursor anyway, which is "
    "what the /v0/level_up route does with a client-supplied level. That "
    "alternative was rejected and is recorded here so the choice is visible. "
    "Ignoring is right when the ignored value is decorative - the client learns "
    "nothing and the server is unaffected. It is WRONG for a cursor: the next id "
    "is precisely the value this operation derives, so acknowledging a request "
    "while substituting a different value answers SUCCESS for an input the "
    "operation did not honour, and a client that sent next_id 99 would be told "
    "the advance succeeded. REFUSING keeps the contract honest, so a "
    "grant-shaped argument is answered with a named code, an empty payload and "
    "no mutation instead"
)

# ------------------------------------------------- the structural refusals --
REASON_BAD_REQUEST = "bad_request"
REASON_UNKNOWN_ACTION = "unknown_action"
REASON_CLIENT_SUPPLIED_ITEM = "client_supplied_item"
REASON_CLIENT_SUPPLIED_ITEM_INDEX = "client_supplied_item_index"
REASON_CLIENT_SUPPLIED_CELL = "client_supplied_cell"
REASON_CLIENT_SUPPLIED_PLAYER = "client_supplied_player"
REASON_CLIENT_SUPPLIED_NEXT_ID = "client_supplied_next_id"
REASON_CLIENT_SUPPLIED_AMOUNT = "client_supplied_amount"
REASON_CLIENT_SUPPLIED_PRICE = "client_supplied_price"
REASON_ABSENT_CURSOR = "absent_reward_cursor"
REASON_ABSENT_STAMP = "absent_reward_instant"
REASON_INVALID_CURSOR = "invalid_reward_cursor"
REASON_INVALID_VECTOR = "invalid_vector"
REASON_INVALID_TIMESTAMP = "invalid_timestamp"
REASON_INVALID_SCHEDULE = "invalid_reward_schedule"

#: One refusal per **grant-shaped argument class** the two preserved branches
#: read from a client, in the pinned order they are resolved.  ``item_index`` is
#: the weekly map index (``command.py:347``), ``cell`` covers both coordinates
#: (``:348-349``), ``player`` is the team (``:351``), ``item`` is the granted id
#: (``command.py:348`` weekly and ``:445`` daily), ``next_id`` is the daily
#: cursor (``:446``), and ``amount`` and ``price`` are the two remaining shapes a
#: reader would expect a reward request to carry and which neither branch has.
CLIENT_KEY_REFUSALS: Tuple[Tuple[str, str], ...] = (
    ("item", REASON_CLIENT_SUPPLIED_ITEM),
    ("item_index", REASON_CLIENT_SUPPLIED_ITEM_INDEX),
    ("cell", REASON_CLIENT_SUPPLIED_CELL),
    ("player", REASON_CLIENT_SUPPLIED_PLAYER),
    ("next_id", REASON_CLIENT_SUPPLIED_NEXT_ID),
    ("amount", REASON_CLIENT_SUPPLIED_AMOUNT),
    ("price", REASON_CLIENT_SUPPLIED_PRICE),
)

#: ``reason -> the request keys that resolve it``, so a request carrying several
#: grant shapes is refused by the FIRST in this table rather than by whichever
#: the caller happened to check first.  Several request keys map to one reason:
#: the two cell coordinates are two keys and one class.
REFUSAL_KEY_MAP: Dict[str, str] = {}
for _client_key, _reason in CLIENT_KEY_REFUSALS:
    REFUSAL_KEY_MAP.setdefault(_client_key, _reason)
REFUSAL_KEY_MAP["x"] = REASON_CLIENT_SUPPLIED_CELL
REFUSAL_KEY_MAP["y"] = REASON_CLIENT_SUPPLIED_CELL

#: Every key a request may carry: the save id, the action, and the seven
#: grant-shaped classes with their aliases.  Anything else is not a reward
#: request at all and is refused structurally.  The grant-shaped keys are listed
#: in :data:`CLIENT_KEY_REFUSALS` order rather than sorted, because the order a
#: refusal is *resolved* in is pinned and a sorted list would hide which of two
#: carried grant shapes answers first.
REQUEST_KEYS: Tuple[str, ...] = (
    "user_id",
    "action",
) + tuple(REFUSAL_KEY_MAP)

#: ``reason -> the request keys that resolve it``, resolved in this order: the
#: seven classes in their pinned order, then the two cell aliases.  Separate from
#: :data:`REFUSAL_KEY_MAP` because that table is keyed the other way round (key to
#: reason) and a single map cannot pin both directions.
REFUSAL_REASON_ORDER: Tuple[str, ...] = tuple(reason for _, reason in CLIENT_KEY_REFUSALS)

#: The refusals, in the order they are resolved.  **Every one resolves before the
#: cursor write and before the instant stamp**, so a refused request leaves the
#: whole recorded document byte-identical (design D9).  The ordering is recorded
#: as data rather than left implicit in a caller, and :data:`VALIDATION_ORDER_NOTE`
#: says both why the stamp ordering is load-bearing rather than incidental and
#: why the **request's own shape is checked before the player's own state**.
#:
#: The order is the one the ``/v0/magic`` route already established: the request's
#: shape first (is this a request at all, does it name one of the two outcomes, does
#: it carry a grant shape), and the player's recorded state last.  It is a strict
#: improvement on the opposite order, and the reason is measurable rather than
#: stylistic: **the addressed cursor cannot even be named until the action is**,
#: because each action addresses a different key, so an ``absent_cursor`` check
#: placed before ``unknown_action`` could not be evaluated and would be a
#: vacuous check rather than a strict one.  Both halves of the delivered surface
#: are refusals, so no rule is weakened whichever order is chosen; this one is
#: recorded so a later reader cannot mistake the ordering for arbitrary.
VALIDATION_ORDER: Tuple[str, ...] = (
    REASON_BAD_REQUEST,
    REASON_UNKNOWN_ACTION,
) + tuple(reason for _, reason in CLIENT_KEY_REFUSALS) + (
    REASON_ABSENT_CURSOR,
    REASON_INVALID_CURSOR,
    REASON_ABSENT_STAMP,
)

VALIDATION_ORDER_NOTE = (
    "EVERY REFUSAL RESOLVES BEFORE ANY WRITE, INCLUDING BEFORE THE INSTANT "
    "STAMP (design D9). Structural, content, and argument-shape validation all "
    "complete first, so a refused request provably leaves the whole recorded "
    "document byte-identical - both cursors and both instants included. The "
    "stamp ordering is the non-obvious half and it is load-bearing rather than "
    "incidental: a refusal that ran far enough to stamp would leave a "
    "WALL-CLOCK difference in a document that is supposed to be unchanged, which "
    "would either make the byte-identity assertion fail FOR THE WRONG REASON or "
    "force it to be weakened to accommodate that. Keeping the assertion exact is "
    "the whole point of the ordering. The preserved server's ordering cannot be "
    "reproduced because it performs no validation at all, so this requirement "
    "exists to make the SERVICE's refusals safe rather than to match a recorded "
    "ordering"
)

#: The refusals that are about the **request itself** rather than about the
#: player's recorded state: a body that is not an object, an action outside the
#: closed vocabulary, and the seven grant-shaped classes.  Recorded as data so the
#: route's own ordering is checkable against one derivation.
REQUEST_SHAPE_REFUSALS: Tuple[str, ...] = (
    REASON_BAD_REQUEST,
    REASON_UNKNOWN_ACTION,
) + tuple(reason for _, reason in CLIENT_KEY_REFUSALS)

#: The refusals that are about the **player's recorded state**: the addressed
#: cursor absent, unreadable, or paired with an instant the branch would have to
#: create.  Each one is a property of the recorded corpus, never of a foreign field.
RECORDED_STATE_REFUSALS: Tuple[str, ...] = (
    REASON_ABSENT_CURSOR,
    REASON_INVALID_CURSOR,
    REASON_ABSENT_STAMP,
)

#: Every refusal this route can answer, as the two halves above in the pinned
#: order.  Equal to :data:`VALIDATION_ORDER`; kept as its own name because the
#: distinction it draws - request shape versus recorded state - is what the
#: ordering is for.
STRUCTURAL_REFUSALS: Tuple[str, ...] = REQUEST_SHAPE_REFUSALS + RECORDED_STATE_REFUSALS

assert STRUCTURAL_REFUSALS == VALIDATION_ORDER, (
    "the two refusal tables disagree; VALIDATION_ORDER is the pinned one"
)

# --------------------------------------------------------- the grant refusal --
NO_GRANT = (
    "NOTHING IS GRANTED, AND THE FOUR-PART PROOF MAKES THAT NON-TAUTOLOGICAL "
    "(design D6). A grant could land in four distinct places, and every "
    "successful action is checked against all four: (1) no map row - the "
    "placed-row count is unchanged and every existing row is byte-identical; "
    "(2) no bought-units append - that list is byte-identical, which also "
    "covers the preserved helper's DEDUPLICATING behaviour at engine.py:86-89; "
    "(3) no storage entry - the store is byte-identical, which also covers the "
    "preserved helper's ACCUMULATING behaviour at engine.py:70-75; (4) no "
    "stored resource moved - the COMPLETE stored resource set the service "
    "exposes is byte-identical, compared as a set and NOT as a subset. This "
    "module carries the four-part proof as a WHOLE-DOCUMENT LEAF ALLOWLIST: the "
    "changed leaves must be a subset of the addressed cursor and the addressed "
    "instant, and nothing else. A whole-document diff cannot miss a fifth "
    "landing place, and it names no foreign field. Together with the addressed "
    "cursor having moved by exactly the derived transition, this makes 'this "
    "grants nothing' a VERIFIED PROPERTY rather than an absence of evidence: an "
    "implementation that quietly placed a row, appended a bought unit, or derived "
    "an amount would fail the proof. The preserved server charges and credits "
    "nothing in either branch - measured across both executed arms - so any "
    "amount would be invention"
)

NO_ELIGIBILITY = (
    "NO ELIGIBILITY, COOLDOWN, WINDOW, PERIOD, OR ALREADY-CLAIMED RULE IS "
    "DERIVED FROM THE STAMPED INSTANT (design D8). Both preserved branches "
    "stamp a wall-clock instant, and a write is reproducible parity, so the "
    "stamp is written. Nothing else is. timeStampMondayBonus has exactly ONE "
    "live write (command.py:361) and its only other occurrence is COMMENTED "
    "OUT; it has NO reader, so there is no window, no cooldown, no weekly "
    "period, no reset boundary and no already-claimed test to reproduce, and "
    "none is invented. Its NAME invites exactly the rule this contract refuses "
    "to write, which is why the absence is recorded as a requirement rather than "
    "left as an implementation detail"
)

NO_CURSOR_SELECTION = (
    "NO CURSOR EVER SELECTS A SCHEDULE ENTRY (design D3/D7). The weekly bound "
    "is derived from the schedule's LIST-VALUED entries - the maximum entry "
    "length over the entries whose value is a list - and never from its entry "
    "count, and the response reports BOTH numbers plus the set difference in both "
    "directions so the mismatch is visible rather than hidden inside a number. "
    "The delivered code performs no indexing of either schedule by any cursor "
    "value: there is no helper that maps a cursor position to a rung, a type "
    "letter, or an amount, and the reachability report is a set difference over "
    "two ranges that deliberately performs no lookup"
)

#: The helpers that are **structurally absent**, with the reason each one would
#: undo.  The delivered modules ship none of them, and an injected one is caught
#: by a whole static-function inventory pin, an exact by-name guard, and a
#: substring guard (design D7).
ABSENT_HELPERS: Tuple[Dict[str, str], ...] = (
    {
        "capability": "grant",
        "would": "place a row, append a bought unit, or create a storage entry",
        "forbidden_because": NO_GRANT,
    },
    {
        "capability": "cursor-to-rung selection",
        "would": "index a schedule by a cursor value, or map a cursor position "
            + "onto a rung, a type letter, or an amount",
        "forbidden_because": NO_CURSOR_SELECTION,
    },
    {
        "capability": "type-letter decoding",
        "would": "map a schedule type letter onto a resource slot, a resource "
            + "name, or a grant shape",
        "forbidden_because": TYPE_LETTERS_UNDECODED_NOTE,
    },
    {
        "capability": "eligibility, cooldown, window, or already-claimed test",
        "would": "compare the stamped instant against the current time, or gate "
            + "an action on an elapsed interval",
        "forbidden_because": NO_ELIGIBILITY,
    },
)

#: The exact and substring name fragments that must not appear as an identifier
#: in the delivered modules.  Recorded here so the guard that enforces it reads
#: its list from the contract rather than restating it.
FORBIDDEN_IDENTIFIER_FRAGMENTS: Tuple[str, ...] = (
    "bought_unit",
    "boughtUnits",
    "buy_stored",
    "map_add_item",
)

__all__ = [
    "ACTION_ADDRESSING_KEY",
    "ACTION_ARGUMENT_COUNT",
    "ACTION_COMMAND",
    "ACTION_CURSOR_KEY",
    "ACTION_DAILY",
    "ACTION_FOR_COMMAND",
    "ACTION_REACHABLE",
    "ACTION_SCHEDULE_KEY",
    "ACTION_STAMP_KEY",
    "ACTION_WEEKLY",
    "ACTIONS",
    "ABSENT_HELPERS",
    "ADDRESSING_KEY_NOTE",
    "ARMS_REPORT_NOTE",
    "CLIENT_CURSOR_REJECTED_ALTERNATIVE",
    "CLIENT_KEY_REFUSALS",
    "CURSORS",
    "CURSOR_DISTRIBUTIONS",
    "CURSOR_STAMP",
    "DAILY_SCHEDULE_KEY",
    "DAILY_STORE_KEY",
    "DAILY_ARMS",
    "DAILY_BOUND_LITERAL",
    "DAILY_BOUND_REJECTED_DERIVATION",
    "DAILY_BOUND_SOURCE",
    "DAILY_COMMAND",
    "DAILY_CURSOR_KEY",
    "DAILY_REACHABLE",
    "DAILY_SCHEDULE_CARDINALITY",
    "DAILY_STAMP_KEY",
    "DAILY_WRAP_TARGET",
    "DECODER_POSITIVE_CONTROL_NOTE",
    "DECODER_POSITIVE_CONTROLS",
    "DECODER_SEARCH_COUNT",
    "DECODER_SEARCH_HIT_TOTAL",
    "DECODER_SEARCHES",
    "DERIVED_DAILY_ITEM",
    "DERIVED_DAILY_ITEM_SOURCE",
    "DIVERGENCES",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "FORBIDDEN_IDENTIFIER_FRAGMENTS",
    "GLOBALS_KEY",
    "INSTANTS",
    "LETTER_NAMED_DECLARATIONS",
    "LETTER_NAMED_DECLARATION_COUNT",
    "MAP_ITEMS_KEY",
    "NO_CURSOR_SELECTION",
    "NO_ELIGIBILITY",
    "NO_GRANT",
    "PRIVATE_STATE_KEY",
    "RANKING_REWARD_CONSUMERS",
    "RANKING_REWARD_ENTRY_COUNT",
    "RANKING_REWARD_OWNERSHIP",
    "RANKING_REWARD_TABLE",
    "REASON_ABSENT_CURSOR",
    "REASON_ABSENT_STAMP",
    "REASON_BAD_REQUEST",
    "REASON_CLIENT_SUPPLIED_AMOUNT",
    "REASON_CLIENT_SUPPLIED_CELL",
    "REASON_CLIENT_SUPPLIED_ITEM",
    "REASON_CLIENT_SUPPLIED_ITEM_INDEX",
    "REASON_CLIENT_SUPPLIED_NEXT_ID",
    "REASON_CLIENT_SUPPLIED_PLAYER",
    "REASON_CLIENT_SUPPLIED_PRICE",
    "REASON_INVALID_CURSOR",
    "REASON_INVALID_SCHEDULE",
    "REASON_INVALID_TIMESTAMP",
    "REASON_INVALID_VECTOR",
    "REASON_UNKNOWN_ACTION",
    "REFUSAL_KEY_MAP",
    "REFUSAL_REASON_ORDER",
    "RECORDED_STATE_REFUSALS",
    "REQUEST_KEYS",
    "REQUEST_SHAPE_REFUSALS",
    "RESOURCE_VECTOR_SLOTS",
    "SAVE_ONLY_DOCUMENT_COUNT",
    "SAVE_ONLY_FIELDS",
    "SAVE_ONLY_FIELD_COUNT",
    "SAVE_ONLY_NOTE",
    "SAVE_ONLY_ORIGIN_STATUS",
    "SCHEDULE_COUNT",
    "SCHEDULE_CENSUS_MODULES",
    "SCHEDULE_CENSUS_NOTE",
    "SCHEDULE_INDEX_BASE",
    "SCHEDULE_INDEX_BASE_ALTERNATIVE",
    "SCHEDULE_INDEX_BASE_STATUS",
    "SCHEDULE_NAMES",
    "SCHEDULES",
    "SCHEDULES_WITH_NO_CONSUMER",
    "SCHEDULES_WITH_NO_CONSUMER_COUNT",
    "STRUCTURAL_REFUSALS",
    "TYPE_LETTERS",
    "VALIDATION_ORDER",
    "VALIDATION_ORDER_NOTE",
    "WEEKLY_ARMS",
    "WEEKLY_BOUND_FLOOR",
    "WEEKLY_BOUND_SOURCE",
    "WEEKLY_COMMAND",
    "WEEKLY_CURSOR_KEY",
    "WEEKLY_REACHABLE",
    "WEEKLY_SCHEDULE_KEY",
    "WEEKLY_STAMP_KEY",
    "WEEKLY_UNIT_LIST_KEY",
    "RewardResult",
    "addressing_key_for",
    "allowed_leaf_paths",
    "allowed_paths_problem",
    "build_envelope",
    "committed_schedule_entries",
    "command_for_action",
    "data_field",
    "daily_bound",
    "daily_successor",
    "derive_reward",
    "derived_args_for",
    "document_leaves",
    "is_action",
    "is_strict_int",
    "leaf_diff",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
    "read_cursor",
    "read_stamp",
    "reachable_report",
    "resolve_document",
    "resolve_private_state",
    "request_grant_keys",
    "schedule_cardinality",
    "validate_request",
    "validate_vector",
    "weekly_bound",
    "weekly_successor",
]


# ------------------------------------------------------- the typed result --
class RewardResult(NamedTuple):
    """One derived reward transition, with every report it must carry.

    **No field here is named after a granted, paid, or awarded reward**, and none
    reports one (the capability's first requirement).  The delivered surface is a
    cursor transition, two bounds, and a reported addressability gap — so the
    fields are: which action ran, which preserved command it derived, the
    addressed cursor's before/after/change, the bound and how the bound was
    obtained, the stamped instant, the arguments derived for the branch, and the
    four read-only reports.
    """

    action: str
    command: str
    cursor_key: str
    cursor_before: int
    cursor_after: int
    cursor_change: int
    bound: int
    bound_source: str
    bound_rejected_alternative: Optional[str]
    stamp_key: str
    stamp_before: int
    stamp_is_volatile: bool
    derived_args: List[int]
    grant: Dict[str, Any]
    bounds: Dict[str, Any]
    reachability: Dict[str, Dict[str, Any]]
    schedules: Tuple[Dict[str, Any], ...]
    schedule_entries: Dict[str, List[Dict[str, Any]]]
    type_letters: Tuple[Dict[str, Any], ...]
    arms: Dict[str, Any]
    divergences: Tuple[Dict[str, str], ...]
    volatile_fields: Tuple[str, ...]

    def payload(self) -> Dict[str, Any]:
        """The JSON-safe projection this route answers with."""
        return {
            "action": self.action,
            "command": self.command,
            "cursor": {
                "key": self.cursor_key,
                "before": self.cursor_before,
                "after": self.cursor_after,
                "change": self.cursor_change,
            },
            "bound": self.bound,
            "bound_source": self.bound_source,
            "bound_rejected_alternative": self.bound_rejected_alternative,
            "instant": {
                "key": self.stamp_key,
                # The wall clock is not derivable, so the branch writes it and the
                # response reports only what the RECORD recorded beforehand. The
                # executed value is a wall clock and is compared by shape, never by
                # equality.
                "stamped": True,
                "volatile": self.stamp_is_volatile,
                "value_before": self.stamp_before,
                "note": NO_ELIGIBILITY,
            },
            "derived_args": list(self.derived_args),
            "grant": dict(self.grant),
            "bounds": dict(self.bounds),
            "reachability": {key: dict(value) for key, value in self.reachability.items()},
            "schedules": [dict(row) for row in self.schedules],
            "schedule_entries": {
                key: [dict(row) for row in value]
                for key, value in self.schedule_entries.items()
            },
            "type_letters": [dict(row) for row in self.type_letters],
            "arms": {
                "weekly": [dict(row) for row in WEEKLY_ARMS],
                "daily": [dict(row) for row in DAILY_ARMS],
                "note": ARMS_REPORT_NOTE,
            },
            "divergences": [dict(row) for row in self.divergences],
            "volatile_fields": list(self.volatile_fields),
        }


# ------------------------------------------------------------ the vocabulary --
def is_action(value: Any) -> bool:
    """Whether ``value`` names one of the two closed reward actions.

    The set is **closed**: the branches' grant arms are deliberately absent, so
    there is no action that places a row, appends a bought unit, or creates a
    storage entry.  Anything outside the set is refused before the dispatcher
    runs, so an unknown action can never reach a legacy branch that would treat
    it as an unhandled command.
    """
    return isinstance(value, str) and value in ACTIONS


def command_for_action(action: str) -> str:
    """The preserved command name one closed action derives.

    Raises :class:`EnvelopeError` with ``unknown_action`` for anything outside
    the closed vocabulary, so a caller cannot map an unvalidated action onto a
    branch.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    return ACTION_COMMANDS_FOR[str(action)]


#: Local alias so :func:`command_for_action` reads without a module-global
#: forward reference, while :data:`ACTION_COMMAND` stays the public table.
ACTION_COMMANDS_FOR = ACTION_COMMAND


def request_grant_keys(payload: Any) -> List[str]:
    """The request keys this contract refuses, in the order they resolve.

    A grant-shaped key is **refused by name**, not ignored, because a cursor sent
    by a client is the very value this operation derives: acknowledging such a
    request while substituting a derived value would answer success for an input
    the operation did not honour (design D2).  The returned list is in
    :data:`REFUSAL_REASON_ORDER` rather than in request order, so a request
    carrying two grant shapes is refused by the **pinned** first class rather than
    by whichever key happened to be written first, and a caller that reports only
    one reason is reporting a decision rather than an accident.
    """
    if not isinstance(payload, dict):
        return []
    carried: List[str] = []
    for _client_key, reason in CLIENT_KEY_REFUSALS:
        for key in sorted(k for k in REFUSAL_KEY_MAP if REFUSAL_KEY_MAP[k] == reason):
            if key in payload:
                carried.append(key)
    return carried


def validate_request(payload: Any) -> str:
    """Resolve one request body into an action, or raise the first refusal.

    This walks the first half of :data:`VALIDATION_ORDER` **in that pinned order**
    and nothing else: a body that is not an object, an action outside the closed
    vocabulary, and the seven grant-shaped classes.  The recorded-state half lives
    in :func:`derive_reward`, which runs after this returns and before any write,
    so the two halves together still resolve before the cursor write and before
    the instant stamp (design D9).

    Splitting the order here rather than in the route is deliberate: the order is
    a claim about **which** refusal a two-fault request gets, and it can only be
    enforced in one place.  The route's job is to map a reason onto a status and a
    code.
    """
    if not isinstance(payload, dict):
        raise EnvelopeError(
            REASON_BAD_REQUEST,
            "the request body is %s, not an object" % type(payload).__name__,
        )
    if "action" not in payload:
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action is required and must be one of %s"
            % ", ".join(sorted(ACTIONS)),
        )
    action = payload["action"]
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    carried = request_grant_keys(payload)
    if carried:
        reason = REFUSAL_KEY_MAP[carried[0]]
        raise EnvelopeError(
            reason,
            "this operation derives the cursor, the granted item, and every "
            "amount from its own recorded state and committed content, so a "
            "request may not carry %s (a grant-shaped key); design D2 refuses "
            "such a request by name rather than ignoring it"
            % ", ".join(carried),
        )
    return str(action)


def addressing_key_for(action: str) -> None:
    """Always :class:`EnvelopeError`: **no** reward action has an addressing key.

    Design D13 records that neither preserved branch addresses a row, a
    collection, a track, or any other identity, and
    :data:`ACTION_ADDRESSING_KEY` is the **explicit** empty mapping that says so.
    This function is the checked half: a caller that reaches for an addressing key
    is told there is none rather than handed ``None``, ``""``, or a default that
    some transport might then guess at.  The quests line's largest cross-layer
    defect was exactly that guess.
    """
    raise EnvelopeError(
        REASON_BAD_REQUEST,
        "the %r action addresses no row, collection, track, or identity, so it "
        "has no addressing key (%s)" % (action, ADDRESSING_KEY_NOTE.split(". ")[0]),
    )


# ------------------------------------------------------------- derived vector --
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D6).

    A reward action's grant is **client-sent**: ``do_command`` applies the
    request's per-command vector before the branch runs (``command.py:40``,
    ``engine.py:251-271``), so any amount a client attached to a reward command
    would be a client-trusted mint or burn.  The preserved server charges and
    credits nothing in either branch — measured across both executed arms — so
    the only honest vector is the neutral one, and a fresh list is returned on
    every call so a caller can never mutate the derivation for the next one.
    **No price is claimed in either direction.**
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
                "resources_changed slot %d is %r: a reward action moves no "
                % (index, value)
                + "resource, so only the neutral all-zero vector is derivable",
            )
    return list(vector)


# ------------------------------------------------------------ the recorded state --
def resolve_private_state(save_document: Any) -> Dict[str, Any]:
    """The save's ``privateState`` object, or a named refusal.

    Both cursors and both instants live in ``privateState`` and nowhere else —
    ``command.py:361-363`` and ``454-455`` both write through
    ``save["privateState"]`` — so this is the single place the addressable
    private state is resolved from, and it is resolved **before** any cursor
    write.  A document that is not an object, or that has no ``privateState``
    object, is refused rather than defaulted: defaulting would invent an address
    the service cannot address.
    """
    if not isinstance(save_document, dict):
        raise EnvelopeError(
            REASON_BAD_REQUEST,
            "the save is %s, not an object" % type(save_document).__name__,
        )
    private = save_document.get(PRIVATE_STATE_KEY)
    if not isinstance(private, dict):
        raise EnvelopeError(
            REASON_ABSENT_CURSOR,
            "the save carries no %r object, so neither reward cursor is "
            "addressable" % PRIVATE_STATE_KEY,
        )
    return private


def resolve_document(save_document: Any) -> Dict[str, Any]:
    """:func:`resolve_private_state` under its whole-save name."""
    return resolve_private_state(save_document)


def _private_int(private: Dict[str, Any], key: str, absent_reason: str,
                 invalid_reason: str) -> int:
    """One recorded private-state integer, copied out, or a named refusal.

    **Copies are mandatory, not hygiene.**  The legacy dispatcher writes into this
    very dict (``save["privateState"]["weeklyRewardIndex"] = ...``), so a value
    returned by reference would alias the live state and the endpoint's "before"
    reading would report the after-state.

    **The two reasons are kept apart, and that separation is measured rather than
    cosmetic.**  A **missing** key and a key holding something that is not an
    integer are two different conditions with two different answers -- one says
    the save has no recorded value, the other says the recorded value cannot be
    read -- and :data:`VALIDATION_ORDER` pins them as adjacent but distinct
    (``absent_reward_cursor`` then ``invalid_reward_cursor``).  Answering both
    with the absent reason would make the second entry of the pinned order
    **unreachable from a request**, which is exactly the sort of vacuous check this
    project has caught itself shipping three times.
    """
    if key not in private:
        raise EnvelopeError(
            absent_reason,
            "the save's %r carries no %r, so this reward operation has no "
            "recorded value to derive from" % (PRIVATE_STATE_KEY, key),
        )
    value = private[key]
    if not is_strict_int(value):
        raise EnvelopeError(
            invalid_reason,
            "the save's %r is %r, not an integer"
            % ("%s/%s" % (PRIVATE_STATE_KEY, key), value),
        )
    return int(value)


def read_cursor(save_document: Any, action: str) -> int:
    """The addressed cursor's recorded value, or a named refusal.

    Raises ``unknown_action`` for an action outside the closed vocabulary and
    ``absent_reward_cursor`` / ``invalid_reward_cursor`` for a cursor that is
    absent or unreadable.  Both refusal reasons resolve before any write and
    before the instant stamp (design D9).
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    private = resolve_private_state(save_document)
    return _private_int(
        private,
        ACTION_CURSOR_KEY[str(action)],
        REASON_ABSENT_CURSOR,
        REASON_INVALID_CURSOR,
    )


def read_stamp(save_document: Any, action: str) -> int:
    """The addressed instant's recorded value, or a named refusal.

    The instant is read for two reasons and no others: the response reports the
    pre-request value, and the endpoint fails closed when the branch would have to
    **create** the key.  A created key would change the size of ``privateState``
    and so break the exact leaf allowlist that carries the four-part grant proof
    (design D6/D9); every one of the 33 committed save documents carries both
    instants, so this refusal has no committed case and exists to keep the proof
    exact rather than to model a real one.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    private = resolve_private_state(save_document)
    return _private_int(
        private,
        ACTION_STAMP_KEY[str(action)],
        REASON_ABSENT_STAMP,
        REASON_INVALID_CURSOR,
    )


# ----------------------------------------------------------------- the bounds --
def weekly_bound(schedule: Any) -> int:
    """``get_weekly_reward_length``'s own result, derived the same way (design D3).

    The preserved helper (``get_game_config.py:195-204``) seeds ``length = 1``
    and then takes ``max`` over the entries whose ``value`` is a **list**.  That
    is the whole rule, and it is transcribed here rather than approximated:

    * the floor is load-bearing — a schedule whose every ``value`` were a scalar
      returns **1**, not 0;
    * the bound is the maximum entry length over **list-valued** entries, so it is
      the item list *inside* one rung, never the number of rungs;
    * anything that is not a list of two-key objects with a ``value`` is
      unresolvable, and is refused rather than skipped — skipping would let a
      malformed rung change the derived bound silently.

    The bound is therefore **5** for the committed schedule, while its cardinality
    is **3**: the two numbers differ, and both are reported side by side.
    """
    if not isinstance(schedule, list) or not schedule:
        raise EnvelopeError(
            REASON_INVALID_SCHEDULE,
            "the committed weekly schedule is %s, not a non-empty list"
            % type(schedule).__name__,
        )
    length = WEEKLY_BOUND_FLOOR
    for position, entry in enumerate(schedule):
        if not isinstance(entry, dict) or "value" not in entry:
            raise EnvelopeError(
                REASON_INVALID_SCHEDULE,
                "weekly schedule entry %d is not an object carrying a 'value', "
                "so no bound is derivable from it" % position,
            )
        value = entry["value"]
        if isinstance(value, list):
            length = max(length, len(value))
    return int(length)


def schedule_cardinality(schedule: Any) -> int:
    """The schedule's **entry count**, reported beside the derived bound.

    This is the number the derived bound is **not**: design D3 requires both
    numbers to be visible, because a reader who received only the bound would not
    know that some of its positions name nothing.
    """
    if not isinstance(schedule, list):
        raise EnvelopeError(
            REASON_INVALID_SCHEDULE,
            "the committed schedule is %s, not a list" % type(schedule).__name__,
        )
    return len(schedule)


def daily_bound() -> int:
    """The **hardcoded literal** at ``command.py:451``, never content-derived.

    :data:`DAILY_BOUND_REJECTED_DERIVATION` records the rejected
    content-derivation alternative and why the agreement between this literal and
    ``DAILY_GOLD_REWARDS``'s entry count is a coincidence of the value
    distribution rather than provenance (design D4).
    """
    return DAILY_BOUND_LITERAL


# --------------------------------------------------------- the successors --
def weekly_successor(before: Any, bound: Any) -> int:
    """The weekly successor: ``(before + 1) % bound`` (``command.py:363``).

    Transcribed from the branch, not invented: the legacy expression is
    ``(save["privateState"]["weeklyRewardIndex"] + 1) %
    get_weekly_reward_length()``, so the bound is the schedule's **derived**
    length and the arithmetic is a modulo.  A bound of zero is refused rather
    than raising, because a service that would divide by an unaddressable
    position is not delivering behaviour; the committed schedule derives 5.
    """
    if not is_strict_int(before):
        raise EnvelopeError(
            REASON_INVALID_CURSOR,
            "the recorded weekly cursor is %r, not an integer" % (before,),
        )
    if not is_strict_int(bound) or int(bound) <= 0:
        raise EnvelopeError(
            REASON_INVALID_SCHEDULE,
            "the derived weekly bound is %r, so no successor is derivable"
            % (bound,),
        )
    return (int(before) + 1) % int(bound)


def daily_successor(before: Any) -> int:
    """The daily successor: ``before + 1``, wrapped to 1 above the literal.

    Transcribed from the branch's own two statements (``command.py:446`` and
    ``451-452``): the legacy expression is ``next_id = args[1] + 1`` followed by
    ``if next_id > 5: next_id = 1``.  This contract feeds it the **recorded**
    cursor rather than a client value, so the same arithmetic produces the
    successor — and the wrap means a recorded cursor at or above the literal
    moves **onto** the first position, which is the backwards move design D5
    records as a divergence of the preserved branch when the client sends a
    larger value.
    """
    if not is_strict_int(before):
        raise EnvelopeError(
            REASON_INVALID_CURSOR,
            "the recorded daily cursor is %r, not an integer" % (before,),
        )
    successor = int(before) + 1
    if successor > DAILY_BOUND_LITERAL:
        return DAILY_WRAP_TARGET
    return successor


def derived_args_for(action: str, cursor_before: int) -> List[int]:
    """The arguments the derived command carries — all derived, none accepted.

    * **weekly** — an **empty** argument list.  That is the whole mechanism by
      which no row is placed: the preserved branch's arm is chosen by
      ``len(args) > 4`` (``command.py:346``), and zero arguments selects the
      short arm, which grants nothing, prints "Won resources", stamps and
      advances.  Design D5 records the arity-selected arm as a divergence; this
      contract simply always sends the non-granting list.
    * **daily** — exactly the two values the branch reads, both derived: the
      granted item at **zero** (so ``item > 0`` is false and the branch takes the
      ``else`` arm that grants nothing) and the **recorded cursor** (which the
      branch advances by one itself, so its write and this contract's derivation
      are the same number without the branch ever seeing a client value).

    Neither value is ever taken from a client: a request carrying an item, a
    next id, or any other grant shape is **refused by name** before this function
    is reached (design D2).
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    name = str(action)
    if name == ACTION_WEEKLY:
        return []
    if not is_strict_int(cursor_before):
        raise EnvelopeError(
            REASON_INVALID_CURSOR,
            "the recorded daily cursor is %r, not an integer" % (cursor_before,),
        )
    return [DERIVED_DAILY_ITEM, int(cursor_before)]


# ------------------------------------------------------------ the reachability --
def reachable_report(bound: int, cardinality: int,
                     reachable: Tuple[int, ...]) -> Dict[str, Any]:
    """One cursor's reachability against one schedule — a set difference only.

    Returns ``{index_base, reachable, answerable, reachable_not_answerable,
    answerable_not_reachable, bound, cardinality, selection_performed}``.

    ``answerable`` is ``range(cardinality)`` under the recorded zero-based index
    base and ``reachable`` is the **caller's** closed range of positions that
    cursor can actually reach, taken from :data:`ACTION_REACHABLE`; both
    differences are reported so the mismatch is visible in **both** directions
    rather than hidden inside one number.  The reachable range is a **parameter**
    rather than a lookup by bound on purpose: both cursors' bounds are the same
    number (5), so a table keyed by bound could not tell the two reports apart —
    the weekly cursor reaches ``0..4`` by a modulo while the daily cursor reaches
    ``1..5`` by a wrap, and conflating them would report the wrong reachable set
    for one of the two.  The function performs **no schedule lookup**: it never
    indexes a schedule by a cursor, never maps a position onto a rung, a type
    letter, or an amount (design D3/D7), and ``selection_performed`` is the
    machine-readable statement of that.
    """
    if not is_strict_int(bound) or int(bound) <= 0:
        raise EnvelopeError(
            REASON_INVALID_SCHEDULE,
            "the bound is %r, so no reachability report is derivable" % (bound,),
        )
    if not is_strict_int(cardinality) or int(cardinality) < 0:
        raise EnvelopeError(
            REASON_INVALID_SCHEDULE,
            "the schedule cardinality is %r, so no reachability report is "
            "derivable" % (cardinality,),
        )
    reach = set(int(item) for item in reachable)
    answerable = set(range(int(cardinality)))
    return {
        "index_base": SCHEDULE_INDEX_BASE,
        "index_base_status": SCHEDULE_INDEX_BASE_STATUS,
        "reachable": sorted(reach),
        "answerable": sorted(answerable),
        "reachable_not_answerable": sorted(reach - answerable),
        "answerable_not_reachable": sorted(answerable - reach),
        "bound": int(bound),
        "cardinality": int(cardinality),
        "selection_performed": False,
    }





# ------------------------------------------------------------ the whole-document proof --
def document_leaves(document: Any) -> Dict[str, Any]:
    """Every node of a JSON document keyed by its JSON-pointer path.

    **Container paths are included**, carrying a size marker rather than a
    value.  That is deliberate and load-bearing: a grant could create a key whose
    value is itself empty, and a leaves-only projection would report **no change
    at all** for it, which would make the four-part proof pass on a grant it was
    written to catch.  Including containers means an added, removed, or emptied
    object or array is a change, whether or not it has leaves.

    The root path is the empty string, so a document whose top level changed size
    is a change too.
    """
    out: Dict[str, Any] = {}

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            out[path] = "<object:%d>" % len(node)
            for key in sorted(node):
                walk(node[key], "%s/%s" % (path, key))
        elif isinstance(node, list):
            out[path] = "<array:%d>" % len(node)
            for index, value in enumerate(node):
                walk(value, "%s/%d" % (path, index))
        else:
            out[path] = node

    walk(document, "")
    return out


def leaf_diff(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
    """The JSON-pointer paths at which two documents differ, sorted.

    A path present on one side only is a difference, not a skip: the union of
    both key sets is walked, so a key the comparison never looked at cannot pass
    as unchanged.
    """
    before_map = document_leaves(before)
    after_map = document_leaves(after)
    return sorted(
        path
        for path in set(before_map) | set(after_map)
        if before_map.get(path) != after_map.get(path)
    )


def allowed_leaf_paths(action: str) -> List[str]:
    """The **only** leaf paths a successful action may change.

    Exactly two: the addressed cursor and the addressed instant.  Every other
    path — a map row, the bought-units list, the store, any stored resource, any
    cursor or instant this operation does not address — is outside the allowlist,
    so the four-part grant proof is expressed as a single whole-document
    containment check that **cannot miss a fifth landing place** and that names no
    foreign field (design D6).
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    name = str(action)
    return [
        "/%s/%s" % (PRIVATE_STATE_KEY, ACTION_CURSOR_KEY[name]),
        "/%s/%s" % (PRIVATE_STATE_KEY, ACTION_STAMP_KEY[name]),
    ]


def allowed_paths_problem(action: str, changed: List[str]) -> Optional[str]:
    """The first changed leaf path outside the allowlist, or :data:`None`.

    The pure half of the four-part proof, kept here so the capture, the endpoint,
    and the offline tests all compare against **one** derivation instead of
    three hand-written checks.
    """
    allowed = set(allowed_leaf_paths(action))
    for path in sorted(changed):
        if path not in allowed:
            return (
                "the %r action changed /%s, which is outside the two paths it may "
                "change (%s); a reward operation places nothing, appends nothing, "
                "creates nothing, and moves no stored resource"
                % (
                    action,
                    path.lstrip("/"),
                    ", ".join(sorted(item.lstrip("/") for item in allowed)),
                )
            )
    return None


# ----------------------------------------------------------------- the envelope --
def build_envelope(action: str, cursor_before: int,
                   ts: Optional[int] = None) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one reward command.

    ``action`` names the closed outcome the service derives a command from, and
    ``cursor_before`` is the **recorded** cursor the successor is derived from.
    The batch carries **exactly one** command and a **neutral** vector (design
    D6): no cost, no amount, no grant, and no resource delta is expressed here,
    because none is derivable and none is accepted from a client.

    The **weekly** command's argument list is **empty** and the **daily** command's
    holds the two derived values — both shapes recorded in
    :data:`ACTION_ARGUMENT_COUNT` so the two can never be confused.

    ``ts`` defaults to the current time (derived-provisional; parsed but unread by
    legacy code, so parity normalizes it).  Raises :class:`EnvelopeError` with
    ``unknown_action``, ``invalid_reward_cursor``, ``invalid_vector``, or
    ``invalid_timestamp``.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    name = str(action)
    checked = validate_vector(neutral_vector())
    args = derived_args_for(name, cursor_before)
    if len(args) != ACTION_ARGUMENT_COUNT[name]:
        raise EnvelopeError(
            REASON_INVALID_VECTOR,
            "the %r action derives %d arguments, not the recorded %d"
            % (name, len(args), ACTION_ARGUMENT_COUNT[name]),
        )
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
        "commands": [[0, command_for_action(name), args, checked]],
    }


# ------------------------------------------------------------------- the result --
def committed_schedule_entries(schedule: Any,
                               schedule_name: str) -> List[Dict[str, Any]]:
    """One schedule's committed entries, reported **verbatim** and in order.

    Every entry is reported, in committed order, under a verbatim ``entry`` key,
    with its ``type`` letter reproduced exactly as stored (where the entry has
    one) and ``decoded`` set to ``False``.  Nothing is selected, indexed by a
    cursor, normalized, or mapped onto a resource (design D3/D10).  Two committed
    facts are surfaced rather than filtered out, because both are what makes the
    bound and the schedule disagree in a way a reader would otherwise not see:

    * an entry whose committed value is **zero** is named by position
      (``DAILY_GOLD_REWARDS`` index 4 is ``0``), because a reader shown only the
      non-zero entries would conclude the schedule pays at every position;
    * a **list-valued** entry is marked, because that is precisely the entry the
      preserved ``get_weekly_reward_length`` counts toward the derived bound —
      the bound is the maximum list length, not the rung count.

    The two schedules have two different committed shapes — the weekly one is a
    list of two-key objects and the daily one is five bare numbers — and both are
    accepted and reported in full, because refusing the daily shape would refuse
    the very schedule this report exists to show.  The **weekly** shape is still
    checked exactly once and in one place: :func:`weekly_bound` refuses any weekly
    entry that is not an object carrying a ``value``, before this function is asked
    for that schedule's rows, so a broken weekly rung cannot change the reported
    cardinality silently.
    """
    if not isinstance(schedule, list):
        raise EnvelopeError(
            REASON_INVALID_SCHEDULE,
            "the committed %s schedule is %s, not a list"
            % (schedule_name, type(schedule).__name__),
        )
    rows: List[Dict[str, Any]] = []
    for position, entry in enumerate(schedule):
        # A committed entry may be a two-key object (the weekly schedule) or a bare
        # scalar (the daily schedule, which is five plain numbers).  Both shapes
        # are reproduced **verbatim** under ``entry``, and the two derived flags
        # below are computed only for the object shape, where a ``value`` key
        # exists to speak about.  Refusing a scalar entry would refuse the
        # committed daily schedule itself, which is the very entry the requirement
        # says to report in full.
        if isinstance(entry, dict):
            value = entry.get("value")
            rows.append(
                {
                    "position": position,
                    "entry": dict(entry),
                    "type": entry.get("type"),
                    "decoded": False,
                    "mapped_to_resource": None,
                    "value": value,
                    "value_shape": (
                        "list" if isinstance(value, list)
                        else type(value).__name__
                    ),
                    "counts_toward_weekly_bound": isinstance(value, list),
                    "committed_value_is_zero": (
                        value == 0 and not isinstance(value, bool)
                    ),
                }
            )
        else:
            rows.append(
                {
                    "position": position,
                    "entry": entry,
                    "type": None,
                    "decoded": False,
                    "mapped_to_resource": None,
                    "value": entry,
                    "value_shape": type(entry).__name__,
                    "counts_toward_weekly_bound": False,
                    "committed_value_is_zero": (
                        entry == 0 and not isinstance(entry, bool)
                    ),
                }
            )
    return rows


def derive_reward(save_document: Any, action: str, weekly_schedule: Any,
                  daily_schedule: Any = None,
                  ts: Optional[int] = None) -> RewardResult:
    """The typed transition and every read-only report one action carries.

    This is the single place the delivered projection is assembled, so the route
    has no derivation of its own to keep in step with the contract.  It reads the
    recorded document, derives the successor from the recorded cursor, and
    assembles the reports; it never dispatches, and it never selects a schedule
    entry.

    Every refusal it can raise is structural or argument-shaped and resolves
    **before** the caller writes anything (design D9), because this function
    performs no write at all.
    """
    if not is_action(action):
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    name = str(action)
    private = resolve_private_state(save_document)
    cursor_key = ACTION_CURSOR_KEY[name]
    stamp_key = ACTION_STAMP_KEY[name]
    before = _private_int(
        private, cursor_key, REASON_ABSENT_CURSOR, REASON_INVALID_CURSOR
    )
    # The instant is read so the response can report the pre-request value and so
    # an absent key is refused rather than created by the branch.
    stamp_before = _private_int(
        private, stamp_key, REASON_ABSENT_STAMP, REASON_INVALID_CURSOR
    )

    # The weekly bound is derived from the schedule the caller passed, so the two
    # numbers that must be visible side by side - the derived bound and the
    # schedule's own entry count - are both derived here and never transcribed.
    weekly_length = weekly_bound(weekly_schedule)
    weekly_rungs = schedule_cardinality(weekly_schedule)
    daily_length = daily_bound()
    # The daily schedule's cardinality is reported, never used to obtain the bound
    # (design D4).  It comes from the committed content the caller read, and falls
    # back to the recorded entry count when a caller has none - so the report is
    # never silently empty and the bound is never derived from it either way.
    daily_rungs = (
        DAILY_SCHEDULE_CARDINALITY
        if daily_schedule is None
        else schedule_cardinality(daily_schedule)
    )

    if name == ACTION_WEEKLY:
        bound = weekly_length
        after = weekly_successor(before, bound)
        bound_source = WEEKLY_BOUND_SOURCE
        rejected: Optional[str] = None
    else:
        bound = daily_length
        after = daily_successor(before)
        bound_source = DAILY_BOUND_SOURCE
        rejected = DAILY_BOUND_REJECTED_DERIVATION

    reports: Dict[str, Dict[str, Any]] = {
        ACTION_WEEKLY: reachable_report(weekly_length, weekly_rungs, WEEKLY_REACHABLE),
        ACTION_DAILY: reachable_report(daily_length, daily_rungs, DAILY_REACHABLE),
    }

    bounds_block = {
        "weekly": {
            "bound": weekly_length,
            "source": WEEKLY_BOUND_SOURCE,
            "derived_from": "the maximum entry length over the schedule entries "
                + "whose value is a list -- never the entry count",
            "floor": WEEKLY_BOUND_FLOOR,
            "cardinality": weekly_rungs,
            "schedule": ACTION_SCHEDULE_KEY[ACTION_WEEKLY],
            "exceeds_cardinality_by": weekly_length - weekly_rungs,
        },
        "daily": {
            "bound": daily_length,
            "source": DAILY_BOUND_SOURCE,
            "derived_from": "a hardcoded literal in the preserved source",
            "wrap_target": DAILY_WRAP_TARGET,
            "cardinality": daily_rungs,
            "cardinality_source": "the committed DAILY_GOLD_REWARDS entry count, "
                + "reported rather than derived: no branch reads that schedule, so "
                + "no caller can derive its length from a legacy helper",
            "schedule": ACTION_SCHEDULE_KEY[ACTION_DAILY],
            "exceeds_cardinality_by": daily_length - daily_rungs,
            "rejected_alternative": DAILY_BOUND_REJECTED_DERIVATION,
        },
        "note": NO_CURSOR_SELECTION,
    }

    schedule_rows: Tuple[Dict[str, Any], ...] = tuple(
        dict(row) for row in SCHEDULES
    )
    letter_rows: Tuple[Dict[str, Any], ...] = tuple(
        {
            "letter": letter,
            "decoded": False,
            "mapped_to_resource": None,
            "decoder_search_hits": DECODER_SEARCH_HIT_TOTAL,
            "decoder_searches": len(DECODER_SEARCHES),
            "declared_elsewhere_as": [
                row["declared_as"]
                for row in LETTER_NAMED_DECLARATIONS
                if row["letter"] == letter
            ],
            "note": TYPE_LETTERS_UNDECODED_NOTE,
        }
        for letter in TYPE_LETTERS
    )

    grant_block = {
        "grants_nothing": True,
        "part_1_no_map_row": "the placed-row count is unchanged and every "
            + "existing row is byte-identical",
        "part_2_no_bought_units_append": "that list is byte-identical, which "
            + "also covers the preserved helper's deduplicating behaviour",
        "part_3_no_storage_entry": "the store is byte-identical, which also "
            + "covers the preserved helper's accumulating behaviour",
        "part_4_no_stored_resource_moved": "the complete stored resource set the "
            + "service exposes is byte-identical, compared as a set and not as a "
            + "subset",
        "carried_by": "a whole-document leaf allowlist restricted to the two "
            + "paths this action may change, so a fifth landing place cannot be "
            + "missed",
        "allowed_leaf_paths": allowed_leaf_paths(name),
        "note": NO_GRANT,
    }

    return RewardResult(
        action=name,
        command=command_for_action(name),
        cursor_key=cursor_key,
        cursor_before=before,
        cursor_after=after,
        cursor_change=after - before,
        bound=bound,
        bound_source=bound_source,
        bound_rejected_alternative=rejected,
        stamp_key=stamp_key,
        # The wall clock is not derivable, so the recorded pre-request value is
        # what the response reports and the executed value is compared by shape
        # only -- never by equality.
        stamp_before=stamp_before,
        stamp_is_volatile=True,
        derived_args=derived_args_for(name, before),
        grant=grant_block,
        bounds=bounds_block,
        reachability=reports,
        schedules=schedule_rows,
        schedule_entries={
            ACTION_SCHEDULE_KEY[ACTION_WEEKLY]: committed_schedule_entries(
                weekly_schedule, ACTION_SCHEDULE_KEY[ACTION_WEEKLY]
            ),
            ACTION_SCHEDULE_KEY[ACTION_DAILY]: (
                []
                if daily_schedule is None
                else committed_schedule_entries(
                    daily_schedule, ACTION_SCHEDULE_KEY[ACTION_DAILY]
                )
            ),
        },
        type_letters=letter_rows,
        arms={"weekly": WEEKLY_ARMS, "daily": DAILY_ARMS, "note": ARMS_REPORT_NOTE},
        divergences=DIVERGENCES,
        volatile_fields=(
            "/%s/%s" % (PRIVATE_STATE_KEY, stamp_key),
            "server_time",
        ),
    )


#: ``DAILY_GOLD_REWARDS``'s committed entry count, recorded because the daily
#: schedule is read by **no** branch, so no caller derives it at runtime.  It is
#: reported - never used to obtain the bound (design D4).
DAILY_SCHEDULE_CARDINALITY = 5
