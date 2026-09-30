#!/usr/bin/env python3
"""Derivation of the legacy production-queue command envelopes and the queue model.

M8 line 3 (``queues``), the **eleventh** state-mutating surface of Compatibility
API v0 and the first one whose legacy command has **no server-side rule at all**
to reproduce: ``command.push_queue_unit`` and ``command.pop_queue_unit`` each read
exactly one positional argument (the legacy map index), resolve the row through
``engine.map_get_item``, and call an engine helper that writes three keys of the
row's own attribute bag.  That is the **whole** branch (``command.py:676-708``),
and this module is the single place where that intent becomes the legacy batch
envelope, so the executed-legacy fixture capture
(``capture_queue_fixture.py``) and the Compatibility API ``POST /v0/queue``
endpoint are checked against *one* derivation — exactly the arrangement the ten
delivered lines already use (design D4/D6).

What legacy actually does (established — ``docs/legacy-production-queues.md``)
    ``push_queue_unit`` (``command.py:676-685``) takes ``args[0]`` as the legacy
    map index, looks the row up, prints an error and returns early if it is
    missing, and otherwise calls ``engine.push_queue_unit``
    (``engine.py:183-189``): ``nu`` is incremented when present and **set to 1**
    when absent, and ``ts`` is stamped with ``timestamp_now()``.

    ``pop_queue_unit`` (``command.py:699-708``) takes ``args[0]`` as well and
    calls ``engine.pop_queue_unit`` (``engine.py:191-204``): when ``nu`` is
    **absent** the helper returns without writing anything (an inert, recorded
    no-op); otherwise it decrements, and when the result is still positive it
    writes ``nu`` and re-stamps ``ts``, and when it reaches **zero** it deletes
    ``nu``, ``ts``, and ``ui`` **together** — the three-key teardown.

    ``push_queue_unit2`` (``command.py:687-697`` →
    ``engine.py:206-213``) is the atom-fusion variant: the same push **plus**
    ``ui = args[1]``, a **client-supplied** unit id.  **It is deliberately not
    exposed by this endpoint** (design D7): the id originates from a client
    argument, no evidence establishes which ids a client actually sends, and the
    projection reports an unresolvable id rather than coercing it — so offering
    the intent here would manufacture a value nothing in the repository supplies.

**No validation of any kind is performed (established).**  The three branches do
not check that the item is a training producer, do not read ``training_time``,
do not check ``min_level``, and **do not cap ``nu``**.  Any placed row can be
queued and the queue length is unbounded.  The recorded absence is a *property of
the legacy contract*, **not permission**: this contract implements none of those
checks and — deliberately — **adds no bound on the count** (design D5), because
the engine sets none and an invented cap would be a rule the legacy server does
not have.

**No elapsed-time evaluation and no completion (established, design D1/D2).**
Every occurrence of ``attr["ts"]`` in the legacy source is a **write**
(``= timestamp_now()``) or a **deletion** (``del attr["ts"]``).  Exactly one
branch reads it back — ``soulmixer_speedup`` — and it is not a general queue
path (see :data:`SPEEDUP_CONTRACT` below).  The dispatcher has 63 named branches
and the ``complete_*`` family is exactly ``complete_collection``,
``complete_goal``, and ``complete_tutorial``: **no command completes a queue and
no command materialises a unit from one.**  So a queue's progress is entirely
client-side, there is no server-side readiness rule to reproduce, and this module
therefore computes **no** readiness, **no** remaining time, **no** progress ratio,
and **no** completion.  The absence is a recorded contract, stated here and in the
endpoint, not a missing feature.

A queue's cost is client-sent (established)
    ``do_command`` calls ``engine.apply_resources(save, map, resources_changed)``
    with the request's per-command vector **before** dispatch (``command.py:40``,
    ``engine.py:251-271``), applying each slot as ``max(current + delta, 0)``.
    Any cost attached to queueing is therefore an **untrusted client delta** — the
    same pattern ``collect`` and ``expand`` already refuse.  The derived vector
    is **NEUTRAL** (design D4) and the endpoint's post-execution proof requires
    that **every** stored resource be **unchanged**, which is what forecloses a
    client minting or burning a balance through this command.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field``, ``EnvelopeError``,
    ``GRID_EXTENT``, and ``in_grid`` — so every delivered derivation, its fixture,
    and its suite keeps passing untouched.  A queue has **no target cell and no
    footprint**, so ``GRID_EXTENT`` and ``in_grid`` are re-exported only to keep
    the sibling modules' import shape identical (``expand_envelope`` and
    ``store_envelope`` do the same); nothing here validates a cell and that is not
    a gameplay claim.

The committed corpus target
    ``tests/saves/fresh-player.json`` places **id 26, Command Center, at map key
    1**, with ``training_time`` 5, ``min_level`` 1, ``group_type``
    ``COMMAND_CENTER``, and the row ``[26, 51, 41, 0, 0, [], {}, 1]`` — an
    **empty** attribute bag.  Both queue commands are therefore exercisable
    against a **real placed training producer** with **no fabricated player
    state**, which is what makes this the first M8 line that can own a real
    executed-legacy fixture.

The ``soulmixer_speedup`` contract — recorded, implemented NOT AT ALL (design D6)
    The one branch that reads a queue's start instant needs **both** ``ts``
    **and** ``ui`` in the addressed row's attribute bag, so it raises
    ``KeyError`` on a fresh row; it reads the duration from the **queued unit**
    (``get_attribute_from_item_id(atom_fusion[6]["ui"], "sm_training_time")``)
    rather than from the building — a *soul-mixer* field present on 300 of the
    committed 429 units and on **0 of 470** buildings; it reads the value as
    **seconds** (``ceil(remaining / 3600)``), **charges nothing** (it only prints
    ``"Cost: N cash"``), and sets ``ts = 0`` so a later refresh sees no timer.  Its
    own source comment calls the calculation *"Quite useless cost calculation for
    understanding it"* (``command.py:732-743``).  Reproducing a formula the
    legacy source itself labels useless, and which never charges anything, would
    invent an economy — so :data:`SPEEDUP_CONTRACT` is **recorded** and **no**
    cost, **no** timer, and **no** speedup is implemented anywhere in this
    repository.  Where the legacy branch would fail on a missing key, this module
    **refuses with a named reason** instead of raising.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions []``,
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are parsed
    and then unread by legacy code, so a time-dependent ``ts`` has no behavioral
    effect and parity normalizes it.  Each batch carries **exactly one** command:
    ``[0, "push_queue_unit", [map_key], neutral]`` or
    ``[0, "pop_queue_unit", [map_key], neutral]``.

No gameplay validation
    Legacy performs no ownership, state, or gameplay validation of any kind for
    these commands — it will queue a decoration, and it will queue the same row
    twice.  Whether a row is a training producer, what a queue costs, how long it
    takes, and whether a player may queue at all are **all** client-side
    derivations this contract deliberately does not make.  The one structural
    check the endpoint adds is addressability: an index that names no row fails
    closed rather than reaching legacy's silent early return, which still
    persists the batch.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

# One shared derivation.  The placement module is imported unchanged — nothing
# here is renamed, moved, or re-implemented.
from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    GRID_EXTENT,
    data_field,
    in_grid,
    is_strict_int,
    parse_data_field,
    payload_json,
)

# ---------------------------------------------------------------- the keys --
# The three committed attribute-bag keys a production queue occupies
# (established, engine.py:183-213).  They live in a map row's SEVENTH slot, the
# ``attr`` bag, and nowhere else.
KEY_COUNT = "nu"
KEY_START = "ts"
KEY_UNIT_ID = "ui"
QUEUE_KEYS = (KEY_COUNT, KEY_START, KEY_UNIT_ID)

# The three-key teardown, recorded because no inspection of the dispatcher would
# reveal it: the keys die TOGETHER at a count of zero.
TEARDOWN = (
    "when the count reaches zero, pop_queue_unit deletes nu, ts, and ui "
    "TOGETHER (engine.py:198-204): the three keys are never torn down "
    "independently, no committed branch deletes one of them on its own, and a "
    "save therefore never carries a partial queue teardown"
)

# ------------------------------------------------------------- the commands --
PUSH_COMMAND = "push_queue_unit"
POP_COMMAND = "pop_queue_unit"
# The atom-fusion push is recorded and deliberately NOT offered.
ATOM_FUSION_COMMAND = "push_queue_unit2"

# The endpoint's own action vocabulary (design D2): the client names an OUTCOME
# and the service chooses the legacy command.  Closed, and echoed exactly as
# sent.  ``push_queue_unit2`` is absent from it by decision, not by oversight.
ACTION_PUSH = "push"
ACTION_POP = "pop"
ACTIONS = (ACTION_PUSH, ACTION_POP)
ACTION_COMMANDS = {ACTION_PUSH: PUSH_COMMAND, ACTION_POP: POP_COMMAND}

# The recorded command contract, one record per command, with the committed
# source lines that fix its arguments and its effects.  The absence of validation
# is a field of every record, because it is the fact that most needs stating.
COMMANDS = (
    {
        "command": PUSH_COMMAND,
        "action": ACTION_PUSH,
        "args": ["map index"],
        "effect": "nu becomes (nu + 1) when present and 1 when absent; ts is "
        "stamped with timestamp_now(); nothing else is written",
        "source": "command.py:676-685 -> engine.py:183-189",
        "validation": "none: not producer-ness, not training_time, not "
        "min_level, and no bound on the count",
        "offered": True,
    },
    {
        "command": POP_COMMAND,
        "action": ACTION_POP,
        "args": ["map index"],
        "effect": "with nu ABSENT the helper returns and nothing is written "
        "(an inert, recorded no-op); otherwise nu is decremented, and a "
        "positive result writes nu and re-stamps ts, while zero DELETES nu, ts, "
        "and ui together",
        "source": "command.py:699-708 -> engine.py:191-204",
        "validation": "none: not producer-ness, not training_time, not "
        "min_level, and no bound on the count",
        "offered": True,
    },
    {
        "command": ATOM_FUSION_COMMAND,
        "action": "",
        "args": ["map index", "unit_id"],
        "effect": "the same push, plus ui = the client-supplied unit id",
        "source": "command.py:687-697 -> engine.py:206-213",
        "validation": "none: the unit id is not checked against the content",
        "offered": False,
        "why_not_offered": "the id is a CLIENT-SUPPLIED argument and no "
        "evidence establishes which ids a client actually sends, so this "
        "endpoint offers no intent that would have to invent one; the client "
        "projection reports an unresolvable ui with its recorded value intact "
        "rather than coercing it (design D7)",
    },
)

# --------------------------------------------------- the recorded absences --
NO_VALIDATION = (
    "NO VALIDATION IS PERFORMED BY THE LEGACY SERVER AND NONE IS IMPLEMENTED "
    "HERE. push_queue_unit, pop_queue_unit, and push_queue_unit2 do not check "
    "that the item is a training producer, do not read training_time, do not "
    "check min_level, and do not cap nu. Any placed row can be queued, a row "
    "that already carries a queue can be queued again, and the queue length is "
    "unbounded. The recorded absence of a count bound is NOT permission to "
    "invent one (design D5): a cap the engine does not set would be a rule the "
    "legacy server does not have, and an authoritative limit belongs to a later "
    "server-authoritative milestone"
)

NO_ELAPSED_TIME = (
    "NO ELAPSED-TIME EVALUATION IS IMPLEMENTED. Every occurrence of attr['ts'] "
    "in the legacy source is a WRITE (engine.py:189, engine.py:198) or a "
    "DELETION (engine.py:202); the single branch that reads it back is "
    "soulmixer_speedup, which is not a general queue path. The dispatcher has 63 "
    "named branches and the complete_* family is exactly complete_collection, "
    "complete_goal, and complete_tutorial: NO command completes a queue and no "
    "command materialises a unit from one. There is therefore no server-side "
    "'is this queue ready?' rule to reproduce, so this contract computes NO "
    "readiness, NO remaining time, NO progress ratio, and NO completion (design "
    "D1/D2). The absence is a recorded property of the legacy contract, not a "
    "missing feature; a future line may introduce completion only as its own "
    "deliverable, with its own evidence"
)

SPEEDUP_CONTRACT = (
    "RECORDED VERBATIM AND IMPLEMENTED NOT AT ALL. The legacy soulmixer_speedup "
    "branch (command.py:727-743) requires BOTH ts AND ui in the addressed row's "
    "attribute bag, so it raises KeyError on a fresh row; it reads the training "
    "duration from the QUEUED UNIT (get_attribute_from_item_id(...['ui'], "
    "'sm_training_time')) rather than from the building; it reads that value as "
    "SECONDS (remaining = sm_training_time - (now - start), cost = "
    "ceil(remaining / 3600)); it CHARGES NOTHING, printing only 'Cost: N cash'; "
    "and it sets ts = 0 so a later refresh sees no timer. Its own source comment "
    "reads 'Quite useless cost calculation for understanding it'. NO cost is "
    "computed here, NO balance is changed, and NO speedup is offered: "
    "reproducing a formula the legacy source itself labels useless, and which "
    "never charges anything, would invent an economy (design D6). Where the "
    "legacy branch would fail on a missing key, this contract REFUSES with a "
    "named reason instead of raising"
)

# The committed coverage of the duration field the speedup branch reads, recorded
# as content and never applied as a rule.
SPEEDUP_FIELD = "sm_training_time"
SPEEDUP_FIELD_COVERAGE = (
    "sm_training_time is a SOUL-MIXER field, not a general training duration: it "
    "is present on 300 of the 429 committed units, absent from the other 129 "
    "(including 923 Gorilla, 933 Wild Elephant, 1001 Worker I, and 1013 Truck), "
    "takes 84 distinct values beginning at 4000, and is present on 0 of the 470 "
    "committed buildings. training_time is the opposite: 130 of 470 buildings "
    "carry a positive one and 0 of 429 units do, and NO queue branch reads "
    "either field (design D5)"
)

# The refusal reasons the recorded speedup contract can produce.  These are the
# named answers to the two keys the legacy branch requires, and they exist so the
# contract can refuse where the legacy code would raise.
REASON_MISSING_START = "missing_start_instant"
REASON_MISSING_UNIT_ID = "missing_queued_unit_id"
REASON_ABSENT_QUEUE = "absent_queue"

# The two failure modes the recorded speedup contract explicitly does NOT
# reproduce.
REFUSAL_NOTE = (
    "the legacy branch RAISES KeyError when the attribute bag lacks ts or ui, "
    "and would raise again inside int(...) for a queued unit that carries no "
    "sm_training_time (129 of the 429 committed units). This contract reproduces "
    "neither crash: it names the unmet precondition and refuses, and it never "
    "reads the duration field at all"
)

# The derived cost is never computed, so the divisor the legacy formula used is
# recorded as a fact about a formula this repository does not implement.
SPEEDUP_COST_DIVISOR = 3600
SPEEDUP_COST_FORMULA = "ceil(remaining_seconds / 3600)"
SPEEDUP_COST_IMPLEMENTED = False
SPEEDUP_COST_NOTE = (
    "the shape above is RECORDED for completeness only. No cost is computed, no "
    "balance is changed, and no speedup purchase is offered anywhere in this "
    "repository, because the legacy branch charges nothing and its own author "
    "labelled the calculation useless"
)

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The committed corpus's own queue target, pinned so a config or corpus drift
# fails a run instead of publishing a different fixture.
COMMITTED_MAP_KEY = 1
COMMITTED_ITEM_ID = 26
COMMITTED_ITEM_NAME = "Command Center"
COMMITTED_TRAINING_TIME = 5
COMMITTED_MIN_LEVEL = 1
COMMITTED_GROUP_TYPE = "COMMAND_CENTER"
COMMITTED_PLACEMENTS = 40
COMMITTED_RESOURCE_BEFORE = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}

__all__ = [
    "ACTION_COMMANDS",
    "ACTION_POP",
    "ACTION_PUSH",
    "ACTIONS",
    "ATOM_FUSION_COMMAND",
    "COMMANDS",
    "COMMITTED_GROUP_TYPE",
    "COMMITTED_ITEM_ID",
    "COMMITTED_ITEM_NAME",
    "COMMITTED_MAP_KEY",
    "COMMITTED_MIN_LEVEL",
    "COMMITTED_PLACEMENTS",
    "COMMITTED_RESOURCE_BEFORE",
    "COMMITTED_TRAINING_TIME",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "GRID_EXTENT",
    "KEY_COUNT",
    "KEY_START",
    "KEY_UNIT_ID",
    "NO_ELAPSED_TIME",
    "NO_VALIDATION",
    "POP_COMMAND",
    "PUSH_COMMAND",
    "QUEUE_KEYS",
    "REASON_ABSENT_QUEUE",
    "REASON_MISSING_START",
    "REASON_MISSING_UNIT_ID",
    "RESOURCE_VECTOR_SLOTS",
    "SPEEDUP_CONTRACT",
    "SPEEDUP_COST_DIVISOR",
    "SPEEDUP_COST_FORMULA",
    "SPEEDUP_COST_IMPLEMENTED",
    "SPEEDUP_COST_NOTE",
    "SPEEDUP_FIELD",
    "SPEEDUP_FIELD_COVERAGE",
    "TEARDOWN",
    "build_envelope",
    "data_field",
    "derived_queue",
    "expected_attr",
    "in_grid",
    "is_action",
    "is_strict_int",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
    "project_queue",
    "speedup_refusal",
    "validate_vector",
]


# ------------------------------------------------------------ the vocabulary --
def is_action(value: Any) -> bool:
    """Whether ``value`` names one of the two closed queue actions.

    The set is **closed** and deliberately does **not** include the atom-fusion
    push: see :data:`COMMANDS` and design D7.  Anything outside it is refused
    before the dispatcher runs, so an unknown action can never reach a legacy
    branch that would treat it as an unhandled command.
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
            "invalid_action",
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    return ACTION_COMMANDS[str(action)]


# --------------------------------------------------------- derived vector --
def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D4).

    A queue's cost is **client-sent**: ``do_command`` applies the request's
    per-command vector before the branch runs (``command.py:40``,
    ``engine.py:251-271``), so any price a client attached to a queue would be a
    client-trusted mint or burn.  The committed configuration records no queueing
    price, so the only honest vector is the neutral one, and a fresh list is
    returned on every call so a caller can never mutate the derivation for the
    next one.  **No queue cost is claimed** in either direction — reproducing a
    client-sent price would invent an economy, and refusing to price a queue the
    legacy server prices not at all is the recorded boundary.
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
            "invalid_vector",
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value):
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d must be an integer, got %r" % (index, value),
            )
        if value != 0:
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d is %r: a queue moves no resource, so "
                "only the neutral all-zero vector is derivable" % (index, value),
            )
    return list(vector)


# ------------------------------------------------------- the derived queue --
def _bag_of(attr: Any) -> Dict[str, Any]:
    """The queue's attribute bag, copied; a refusal when it is not an object.

    A bag that is ``None`` or a list is a shape this contract cannot reason
    about, so it is refused with a named reason rather than read as an empty
    queue: an empty bag and a missing one are the same thing, but a bag that is
    not a bag is a different thing entirely.
    """
    if isinstance(attr, dict):
        return {str(key): attr[key] for key in attr}
    raise EnvelopeError(
        "invalid_attr",
        "the addressed row's attribute bag must be an object, found %s"
        % type(attr).__name__,
    )


def derived_queue(attr: Any, action: str) -> Dict[str, Any]:
    """What one queue command does to a row's attribute bag — derived, not read.

    Returns
        ``{action, command, changed, count, start_instant, queued_unit_id,
        teardown, no_op, other_keys}`` describing the **derived** post-execution
        bag, or raises :class:`EnvelopeError` with ``invalid_action`` /
        ``invalid_attr``.

    ``count`` and ``queued_unit_id`` are the exact values the branch writes, and
    ``other_keys`` is the set of every committed bag key the branch does **not**
    touch — both are exactly checkable after execution.  ``start_instant`` is
    ``None`` **only** when the branch writes no new instant (an inert pop), and is
    ``True`` otherwise: the branch stamps the wall clock, so the *value* is not
    derivable and is compared by **shape** (a strict integer) and by direction
    (**not backwards**) instead.  The comparison is deliberately ``>=`` and not
    ``>``: :func:`engine.timestamp_now` has **one-second** resolution, so two
    commands inside the same second legitimately stamp the same value, and a
    strict "moves forward" rule would refuse a correct transaction.  ``teardown``
    records whether the three-key teardown fires, and ``no_op`` records legacy's
    inert pop on a row whose ``nu`` is absent — a real, recorded behaviour rather
    than an error.
    """
    if not is_action(action):
        raise EnvelopeError(
            "invalid_action",
            "action must be one of %s, got %r" % (", ".join(sorted(ACTIONS)), action),
        )
    bag = _bag_of(attr)
    action_text = str(action)
    command = ACTION_COMMANDS[action_text]
    other_keys = sorted(key for key in bag if key not in QUEUE_KEYS)
    has_count = KEY_COUNT in bag
    has_unit = KEY_UNIT_ID in bag
    if has_count and not is_strict_int(bag[KEY_COUNT]):
        # A non-strict count (a bool, a float, a numeric string) is a shape this
        # contract refuses rather than compares against a coerced value: legacy
        # would raise out of the helper, and a silently coerced count would make
        # the post-execution proof compare against a number the save never held.
        raise EnvelopeError(
            "invalid_attr",
            "the addressed row's %r is %r, not an integer" % (KEY_COUNT, bag[KEY_COUNT]),
        )
    if has_count and bag[KEY_COUNT] < 0:
        raise EnvelopeError(
            "invalid_attr",
            "the addressed row's %r is %r, not a non-negative count"
            % (KEY_COUNT, bag[KEY_COUNT]),
        )
    if action_text == ACTION_PUSH:
        count = (bag[KEY_COUNT] + 1) if has_count else 1
        return {
            "action": action_text,
            "command": command,
            "changed": True,
            "no_op": False,
            "count": count,
            # A push always stamps the start instant; the VALUE is the wall clock.
            "start_instant": True,
            "queued_unit_id": bag.get(KEY_UNIT_ID),
            "keeps_unit_id": has_unit,
            "teardown": False,
            "other_keys": other_keys,
        }
    # pop
    if not has_count:
        # engine.py:193-194: the helper returns without writing anything.
        return {
            "action": action_text,
            "command": command,
            "changed": False,
            "no_op": True,
            "count": None,
            "start_instant": False,
            "queued_unit_id": bag.get(KEY_UNIT_ID),
            "keeps_unit_id": has_unit,
            "teardown": False,
            "other_keys": other_keys,
        }
    remaining = bag[KEY_COUNT] - 1
    if remaining > 0:
        return {
            "action": action_text,
            "command": command,
            "changed": True,
            "no_op": False,
            "count": remaining,
            # A partial decrement REFRESHES the start instant (engine.py:198).
            "start_instant": True,
            "queued_unit_id": bag.get(KEY_UNIT_ID),
            "keeps_unit_id": has_unit,
            "teardown": False,
            "other_keys": other_keys,
        }
    return {
        "action": action_text,
        "command": command,
        "changed": True,
        "no_op": False,
        "count": None,
        "start_instant": False,
        "queued_unit_id": None,
        "keeps_unit_id": False,
        "teardown": True,
        "other_keys": other_keys,
    }


def project_queue(attr: Any) -> Dict[str, Any]:
    """The **read-only** projection of one row's queue, verbatim.

    Returns
        ``{present, count, start_instant, queued_unit_id, keys, absent_is_absent}``

    The three committed keys are reported **exactly as the bag holds them**: a
    bag carrying none of them is ``present: False`` with ``count`` and
    ``start_instant`` **absent** (a named absence, never a count of zero paired
    with an instant of zero — the two would be indistinguishable from a real
    queue that had just been emptied), and a bag carrying a key reports that
    key's value verbatim with no scaling, rounding, or defaulting.

    **Nothing else is computed.**  There is deliberately **no** readiness, **no**
    remaining time, **no** progress ratio, and **no** completion, because the
    legacy server has none of those rules to reproduce (design D1/D2).  The
    ``queued_unit_id`` is reported **as recorded** — never resolved here, never
    coerced, never dropped: the id comes from a client-supplied argument and no
    evidence establishes which ids a client actually sends (design D7), so
    resolving or substituting it server-side would invent a value.

    Raises :class:`EnvelopeError` with ``invalid_attr`` when the bag is not an
    object, so a malformed save is refused rather than read as an empty queue.
    """
    bag = _bag_of(attr)
    present = KEY_COUNT in bag or KEY_START in bag or KEY_UNIT_ID in bag
    return {
        "present": present,
        "count": bag.get(KEY_COUNT),
        "start_instant": bag.get(KEY_START),
        "queued_unit_id": bag.get(KEY_UNIT_ID),
        "keys": [key for key in QUEUE_KEYS if key in bag],
        "absent_is_absent": True,
    }


def expected_attr(before_attr: Any, action: str, after_attr: Any) -> Optional[str]:
    """The first way the persisted bag diverges from the derived result, or None.

    The **pure** half of the endpoint's post-execution proof, kept here so the
    capture tool, the endpoint, and the offline tests all compare against ONE
    derivation instead of three hand-written checks (design D4).

    Every committed key the branch does not own is compared **by value**; the
    count is compared by value; and the start instant is compared by **shape** —
    a strict integer, and **not earlier** than the pre-execution one — because
    the branch stamps the wall clock and the value is not derivable.  "Not
    earlier" rather than "strictly later" is the honest direction for a
    **one-second-resolution** clock, under which two commands in the same second
    legitimately stamp the same instant.  A non-strict count (a bool, a float, a
    string) is a refusal upstream, never a comparison against a coerced value.
    """
    derived = derived_queue(before_attr, action)
    before = _bag_of(before_attr)
    after = _bag_of(after_attr)
    for key in derived["other_keys"]:
        if key not in after:
            return "attribute key %r was removed by a command that never owns it" % key
        if after[key] != before[key]:
            return "attribute key %r changed from %r to %r" % (key, before[key], after[key])
    extra = sorted(key for key in after if key not in QUEUE_KEYS and key not in before)
    if extra:
        return "a command that owns no key outside the queue added %r" % (extra,)
    if derived["no_op"]:
        if after != before:
            return "an inert pop on a row whose count is absent wrote %r" % (
                {key: after[key] for key in sorted(after) if before.get(key) != after[key]},
            )
        return None
    if derived["teardown"]:
        for key in QUEUE_KEYS:
            if key in after:
                return "the three-key teardown left %r behind" % key
        return None
    if KEY_COUNT not in after:
        return "the count is absent after a %s that derives a count" % derived["action"]
    if after[KEY_COUNT] != derived["count"]:
        return "the count is %r after a %s, not the derived %r" % (
            after[KEY_COUNT],
            derived["action"],
            derived["count"],
        )
    if KEY_START not in after:
        return "the start instant is absent after a %s that stamps one" % derived["action"]
    stamp = after[KEY_START]
    if not is_strict_int(stamp):
        return "the start instant is %r, not an integer" % (stamp,)
    previous = before.get(KEY_START)
    if is_strict_int(previous) and stamp < previous:
        return "the start instant %r moves backwards from %r" % (stamp, previous)
    if derived["keeps_unit_id"]:
        if KEY_UNIT_ID not in after:
            return "a push removed the queued unit id, which it never writes"
        if after[KEY_UNIT_ID] != derived["queued_unit_id"]:
            return "the queued unit id is %r, not the untouched %r" % (
                after[KEY_UNIT_ID],
                derived["queued_unit_id"],
            )
    elif KEY_UNIT_ID in after:
        return (
            "a push invented the queued unit id %r, which only the atom-fusion "
            "branch writes" % (after[KEY_UNIT_ID],)
        )
    return None


# -------------------------------------------------- the recorded speedup --
def speedup_refusal(attr: Any) -> Dict[str, Any]:
    """The recorded speedup contract's precondition check — and nothing else.

    Returns
        ``{ok, reason, error, keys_present, refuses_instead_of_raising,
        contract, cost_implemented}``

    ``ok`` is ``True`` only when the addressed row's bag carries **both** the
    start instant and the queued unit id, which are the two keys the legacy branch
    requires.  When either is missing the answer is a **named refusal** — the
    legacy branch raises ``KeyError`` there, and this contract reproduces no
    crash.  Even on ``ok`` the function computes **no cost**: it returns the
    recorded contract and the statement that the cost is not implemented, so no
    caller can mistake an "ok" for a price.
    """
    keys: List[str] = []
    reason = ""
    message = ""
    if attr is None:
        reason = REASON_ABSENT_QUEUE
        message = (
            "the addressed row has no attribute bag at all, so it carries "
            "neither the start instant nor the queued unit id the legacy "
            "speedup branch requires: it would raise KeyError on "
            "atom_fusion[6]['ts'] and this contract refuses instead"
        )
    else:
        bag = _bag_of(attr)
        for key in (KEY_START, KEY_UNIT_ID):
            if key in bag:
                keys.append(key)
        if KEY_START not in keys:
            reason = REASON_MISSING_START
            message = (
                "the addressed row's attribute bag carries no start instant, "
                "which the legacy speedup branch requires: it would raise "
                "KeyError on atom_fusion[6]['ts'] and this contract refuses "
                "instead"
            )
        elif KEY_UNIT_ID not in keys:
            reason = REASON_MISSING_UNIT_ID
            message = (
                "the addressed row's attribute bag carries no queued unit id, "
                "which the legacy speedup branch requires to read the "
                "duration: it would raise KeyError on atom_fusion[6]['ui'] "
                "and this contract refuses instead"
            )
    return {
        "ok": reason == "",
        "reason": reason,
        "error": message,
        "keys_present": keys,
        "refuses_instead_of_raising": reason != "",
        "contract": SPEEDUP_CONTRACT,
        "cost_implemented": False,
    }


# ------------------------------------------------------------ the envelope --
def build_envelope(
    map_key: Any, action: str, ts: Optional[int] = None
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one queue command.

    ``map_key`` is the legacy map index as an integer — the queue commands' **only**
    positional argument — and ``action`` names the closed outcome the service
    derives a command from.  The batch carries **exactly one** command and a
    **neutral** vector (design D4): no cost, no duration, no count, and no
    readiness is expressed here, because none is derivable and none is accepted
    from a client.

    ``ts`` defaults to the current time (derived-provisional; parsed but unread by
    legacy code, so parity normalizes it).  Raises :class:`EnvelopeError` with
    ``invalid_map_key``, ``invalid_action``, ``invalid_vector``, or
    ``invalid_timestamp``.  Whether the row is a training producer, what a queue
    costs, and who may queue at all are the client's business by design D5.
    """
    if not is_strict_int(map_key):
        raise EnvelopeError(
            "invalid_map_key",
            "map_key must be an integer, got %s" % type(map_key).__name__,
        )
    checked = validate_vector(neutral_vector())
    command = command_for_action(action)
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError("invalid_timestamp", "ts must be a non-negative integer")
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": ts,
        "tries": 1,
        "accessToken": "",
        "commands": [[0, command, [map_key], checked]],
    }
