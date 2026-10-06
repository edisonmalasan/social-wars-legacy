#!/usr/bin/env python3
"""Derivation of the legacy darts and premium command envelopes.

The darts deliver line of M11: the client sends an **intent** (a save id, and
for each action only the arguments the preserved branch actually takes from a
client) and never a price, a resource delta, a duration, or a shot outcome.
This module is the single place where that intent becomes a legacy batch
envelope, so the Compatibility API ``POST /v0/darts`` endpoint is checked
against *one* derivation (design D10).

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` -- ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``EnvelopeError`` -- so every earlier delivered line keeps
    passing untouched.  This module adds only the darts action set, the four
    command names, the **neutral** vector, and the one *derived* value this line
    contributes.

The four commands (``command.py:573-623``)
    ``darts_reset``            ``[seed]``                    six writes
    ``darts_new_free``         ``[]``                        two writes
    ``darts_shoot_balloon``    ``[index, False]``            three writes
    ``buy_premium_account``    ``[package_index]``           one write

Why the shot envelope carries ``False`` in its second slot
    This is the single most consequential line in the module, so it is stated
    plainly.  The preserved branch reads ``won_extra = args[1]`` and, **only
    when that value is truthy**, writes ``dartsGotExtra = True``
    (``command.py:604-605``).  Two facts follow, and both are used:

    1.  ``args[1]`` **must** be present.  The branch indexes it unconditionally,
        so an envelope carrying only the shot index would raise ``IndexError``
        inside the legacy dispatcher and answer 500.  Refusing to send it is
        therefore not an option even for a refusal.
    2.  A **falsy** value makes the branch write nothing at all: the conditional
        write is skipped and the branch takes its ``else`` print arm
        (``command.py:607-610``).

    So the outcome slot is **derived as ``False``**, by this service, never taken
    from the client.  That makes the refusal *mechanical* rather than advisory:
    a client claiming a win cannot move ``dartsGotExtra``, because the value
    that decides it was never the client's to set.  The refusal is reported as a
    **divergence** from the preserved branch, not as parity -- the legacy server
    *would* have honoured the claim, and reproducing that would be precisely the
    ``apply_client_state``-shaped anti-pattern this project forbids.

Neutral price derivation (design D6)
    ``resources_changed`` is the legacy 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]``, applied through
    ``engine.apply_resources`` (``engine.py:251-271``) **before** the branch,
    with a per-resource ``max(current + delta, 0)`` clamp.  The derived vector is
    **all zeros**: the committed ``PREMIUM_ACCOUNTS`` schedule carries an amount
    beside every duration, and that amount has **zero consumers** across all
    eleven legacy modules -- ``get_premium_days`` returns the committed
    *duration* and never reads the committed amount beside it
    (``get_game_config.py:181-189``).  Nothing charges a premium account.

    "Nothing is charged" is a **refusal, not parity**, and the distinction
    matters: because ``apply_resources`` applies a *client-sent* vector before
    dispatch, a legacy client could pair any debit with this purchase.  This
    service derives the vector, so a client-sent one cannot move a balance -- but
    no claim is made about what the Flash client did.

What is **not** derived here (design D3/D8)
    *  No ``seed`` semantics.  The seed is stored verbatim; nothing orders,
       bounds, or seeds anything from it, because no legacy branch reads it.
    *  No shot-list length bound and **no** schedule-membership test.  The
       preserved branch appends whenever the index is absent
       (``command.py:599-600``), and ``villages/Nerri.json`` records the shot
       index ``0``, which is **absent** from the committed darts schedule's
       ``1..27`` ids.  Adding a membership test would therefore *contradict* the
       corpus rather than reproduce the branch.
    *  No premium duration.  The duration comes from the committed schedule
       through ``get_premium_days``, inside the legacy server, from the index
       alone.
    *  No weekday rule, although ``engine.reset_stuff``'s comment explains its
       3-day offset by a Thursday/Monday rationale (``engine.py:244``).  The
       offset is a literal ``259200``; the rationale stays a comment.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from placement_envelope import (  # noqa: F401
    ENVELOPE_KEYS,
    EnvelopeError,
    is_strict_int,
    payload_json,
)

# The four legacy commands this deliver line executes (command.py:573-623).
RESET_COMMAND = "darts_reset"
FREE_COMMAND = "darts_new_free"
SHOOT_COMMAND = "darts_shoot_balloon"
PREMIUM_COMMAND = "buy_premium_account"

#: The closed action set.  A request naming anything else is refused before any
#: derivation runs, so an unknown action can never reach the dispatcher.
ACTIONS = (RESET_COMMAND, FREE_COMMAND, SHOOT_COMMAND, PREMIUM_COMMAND)

#: Width of the legacy resource vector ``[unknown, xp, gold, wood, oil, steel,
#: cash, mana]`` (``engine.apply_resources``, ``engine.py:251-271``).
RESOURCE_VECTOR_SLOTS = 8

#: The **derived** shot outcome.  See the module docstring: the branch indexes
#: ``args[1]`` unconditionally, so the slot cannot be omitted, and a falsy value
#: makes the branch's conditional ``dartsGotExtra`` write not execute.  It is
#: derived here and never accepted from a client.
DERIVED_SHOT_OUTCOME = False

# Refusal codes, in the order the endpoint applies them.
REASON_BAD_REQUEST = "bad_request"
REASON_UNKNOWN_ACTION = "unknown_darts_action"
REASON_INVALID_SEED = "invalid_darts_seed"
REASON_INVALID_SHOT_INDEX = "invalid_shot_index"
REASON_INVALID_PACKAGE_INDEX = "invalid_package_index"

#: Every reason this module can raise.  A reason outside this set is a bug in the
#: endpoint's status mapping, not a client's mistake.
REASONS = (
    REASON_BAD_REQUEST,
    REASON_UNKNOWN_ACTION,
    REASON_INVALID_SEED,
    REASON_INVALID_SHOT_INDEX,
    REASON_INVALID_PACKAGE_INDEX,
)

__all__ = [
    "ACTIONS",
    "DERIVED_SHOT_OUTCOME",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "FREE_COMMAND",
    "PREMIUM_COMMAND",
    "REASONS",
    "REASON_BAD_REQUEST",
    "REASON_INVALID_PACKAGE_INDEX",
    "REASON_INVALID_SEED",
    "REASON_INVALID_SHOT_INDEX",
    "REASON_UNKNOWN_ACTION",
    "RESET_COMMAND",
    "RESOURCE_VECTOR_SLOTS",
    "SHOOT_COMMAND",
    "build_envelope",
    "is_strict_int",
    "neutral_vector",
    "payload_json",
]


def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D6).

    A fresh list on every call so a caller can never mutate the derivation
    for the next one.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def _command_entry(name: str, args: List[Any]) -> List[Any]:
    """One command row: ``[map_id, name, args, neutral_vector]``.

    The leading ``0`` is the map id -- the SW always sends map 0 and the corpus
    has exactly one map -- and the trailing vector is the resource delta applied
    *before* the branch.
    """
    return [0, name, args, neutral_vector()]


def _command_for(action: str, arguments: Dict[str, Any]) -> List[Any]:
    """Derive the single command row for ``action``.

    Raises :class:`EnvelopeError` for an unknown action before reading any
    argument, so an unrecognised request cannot partially validate.
    """
    if not isinstance(action, str) or action not in ACTIONS:
        raise EnvelopeError(
            REASON_UNKNOWN_ACTION,
            "action must be one of %s, got %r"
            % (", ".join(ACTIONS), action),
        )
    if action == RESET_COMMAND:
        seed = arguments.get("seed")
        if not is_strict_int(seed):
            raise EnvelopeError(
                REASON_INVALID_SEED,
                "seed must be an integer, got %s" % type(seed).__name__,
            )
        # Stored verbatim; nothing is derived from it (design D3).
        return _command_entry(RESET_COMMAND, [seed])
    if action == FREE_COMMAND:
        # The branch reads no argument at all (command.py:586-591).
        return _command_entry(FREE_COMMAND, [])
    if action == SHOOT_COMMAND:
        index = arguments.get("shot_index")
        if not is_strict_int(index):
            raise EnvelopeError(
                REASON_INVALID_SHOT_INDEX,
                "shot_index must be an integer, got %s" % type(index).__name__,
            )
        # No length bound, no schedule-membership test, and a DERIVED outcome --
        # see the module docstring for why the second slot must be present.
        return _command_entry(SHOOT_COMMAND, [index, DERIVED_SHOT_OUTCOME])
    package_index = arguments.get("package_index")
    if not is_strict_int(package_index):
        raise EnvelopeError(
            REASON_INVALID_PACKAGE_INDEX,
            "package_index must be an integer, got %s" % type(package_index).__name__,
        )
    # The legacy helper clamps an oversized index to the last entry
    # (get_game_config.py:184-185), so no bound is imposed here and the clamp
    # stays where it was recorded.
    return _command_entry(PREMIUM_COMMAND, [package_index])


def build_envelope(
    action: Any,
    arguments: Optional[Dict[str, Any]] = None,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one darts action.

    Exactly one legacy command is derived per call.  ``arguments`` is a mapping
    of this action's client-sent inputs; keys this action does not read are
    ignored rather than rejected, so a client sending an extra key changes
    nothing.  ``ts`` defaults to the current time (derived-provisional; parsed
    and then unread by legacy code, so parity normalizes it).

    Raises :class:`EnvelopeError` with any code from :data:`REASONS`.
    """
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise EnvelopeError(
            REASON_BAD_REQUEST,
            "arguments must be an object, got %s" % type(arguments).__name__,
        )
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
        "commands": [_command_for(action, arguments)],
    }