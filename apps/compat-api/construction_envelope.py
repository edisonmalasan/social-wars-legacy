#!/usr/bin/env python3
"""Derivation of the three legacy construction-timing command envelopes.

The construction deliver line of M7: the client sends a *construction intent*
(a save id, the legacy map index of a placement the player already owns, and
one **action** naming an outcome) and never a duration, a price, or a resource
delta.  This module is the single place where that intent becomes the legacy
batch envelope, so the executed-legacy fixture capture
(``capture_construction_fixture.py``) and the Compatibility API ``POST
/v0/construction`` endpoint are checked against *one* derivation — exactly the
arrangement the placement, purchase, move, sell, store, and upgrade deliver
lines already use.

Shared derivation: the serialization and structural helpers are imported
unchanged from :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
``payload_json``, ``data_field``, ``parse_data_field``, ``EnvelopeError``,
``GRID_EXTENT``, and ``in_grid`` — so every delivered derivation, its fixture,
and its suite keeps passing untouched.  A construction has no target cell, so
``GRID_EXTENT`` and ``in_grid`` are re-exported only to keep the sibling
modules' import shape identical (``store_envelope`` and ``move_envelope`` do
the same); nothing here validates a cell and this is not a gameplay claim.

Why exactly these three commands (design D1)
    The committed dispatcher has no single ``construction`` branch: the click
    to build lifecycle is spread over three named branches, recorded in
    ``docs/legacy-protocol/commands.json`` as ``activate``
    (``command.py:412-429``), ``add_click`` (``command.py:525-536``), and
    ``activate_item_click`` (``command.py:537-548``).  Between them they write
    **only** the addressed row's ``timestamp`` (``item[3]``) and its attribute
    bag (``item[6]``), which is why the endpoint can name the post-condition of
    each action exactly.  The friend-assist cluster (``buy_si_help`` /
    ``finish_si`` and the ``attr["si"]`` bag, ``command.py:549-572``,
    ``engine.py:137-147``) shares that bag and is deliberately **out of
    scope**: this contract must not imply a friend can be hired.

The action vocabulary is the service's own, not legacy's (design D2)
    ``"start"``, ``"click"``, and ``"finish"`` name *outcomes*; the client
    chooses an outcome and the service chooses the command and every one of its
    arguments.  The vocabulary is **closed**: anything else fails closed with
    ``invalid_action`` and the legacy dispatcher never runs.

The start duration is derived from committed content (design D2)
    ``build_envelope_start`` is the only builder that takes a second input, and
    it is a **positive** integer: the endpoint resolves it from the addressed
    placement's item's committed ``build_time`` through
    :meth:`compat_legacy.LegacyBoot.item_build_time`, never from a client.  A
    missing, non-integer, or non-positive committed build time fails closed
    (``no_build_time``) instead of being coerced, and a non-positive value can
    never reach this module (``invalid_duration``) — see the clearing branch
    below.  Unlike every previous line, this contract has **no derived
    placeholder argument at all**: the client cannot influence the countdown.

The clearing branch is documented and never used (design D6)
    ``activate`` with a **non-positive** duration does not cancel a build: it
    re-stamps the row's timestamp and **clears the whole attribute bag**,
    destroying the click counter ``nc`` and any friend-assistance entries
    ``si`` (``command.py:421-428``; recorded in
    ``docs/legacy-construction-timing.md``, probe C).  This contract therefore
    only ever sends a positive derived duration and exposes **no "cancel
    build" action**.  Any future cancel path must not route through
    ``activate(..., 0)``.

Neutral price vector — and the no-cost claim (design D4)
    ``resources_changed`` is the legacy 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]`` applied *before* the
    branch (``command.py:40``, ``engine.apply_resources``,
    ``engine.py:251-271``).  The derived vector is **all zeros** on every
    action.  The committed configuration records no price for building: item
    ``cost`` is ``"0"`` and ``cost_type`` is ``null`` across all items (dead
    fields), ``costs`` prices the *purchase* only, and the loaded
    ``BUILD_SPEEDUP_PRICING = [5, 1]`` / ``BUILD_SPEEDUP_MIN_TIME = 10`` globals
    price a construction *speedup* — a mechanism deliberately out of scope,
    whose command is not in this contract.  The catalog records that prices
    travel entirely through the client-sent deltas (the server computes none),
    so deriving a price here would be fabrication and accepting a client-sent
    one would let any client mint resources.  A zero vector is also the only choice that cannot corrupt
    a resource balance.  **This change therefore claims no building cost at
    all**, and nothing about what building costs in the legacy client.  The
    price question belongs to Server v1 (M13) and to the later *resources*
    deliver line.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions []``,
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.  Unlike the upgrade line, this
    batch carries **exactly one** command per call: the three commands are three
    outcomes, not one transaction.

No gameplay validation
    Ownership, whether the placement is a building at all, whether a build may
    start on a row that already carries construction state, the click
    threshold, and the remaining time are **not** enforced here: **no branch
    compares ``nc`` with ``clicks_to_build``**, the threshold and
    ``cp - (now - item[3])`` are pure client derivations from committed config
    plus the row's own state, and legacy performs no validation of any kind.
    Offering the right action is the client's job by design D5, and
    authoritative validation belongs to Server v1 (M13).

Provenance: established versus derived
    **Established** from committed legacy source and the four executed-legacy
    probes recorded in ``docs/legacy-construction-timing.md``: the three
    commands' argument shapes and effects; that they write only ``item[3]`` and
    ``item[6]``; that ``nc`` is seeded by the *purchase* half
    (``engine.map_add_item``, ``engine.py:25-28``) and not by these commands;
    the ``cp``/timestamp shape of an activation; that a non-positive duration
    clears the whole bag; and that **no server-side completion rule exists**.
    **Derived and never observed from the Flash client**: that a real
    construction sends these commands, and that the duration a client sends is
    the item's committed ``build_time`` rather than its ``activation`` field or
    a speedup-adjusted figure.  Flash is never executed in this repository, so
    those are recorded as derived-provisional together with the neutral price
    vectors.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

# One shared derivation.  The placement module is imported unchanged —
# nothing here is renamed, moved, or re-implemented.
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

# The three legacy commands this deliver line executes (design D1).  All three
# names are read by the committed dispatcher; cluster 2 (buy_si_help /
# finish_si) is out of scope by the change's non-goals.
ACTIVATE_COMMAND = "activate"
ADD_CLICK_COMMAND = "add_click"
ACTIVATE_ITEM_CLICK_COMMAND = "activate_item_click"

# The closed action vocabulary (design D2).  These are the service's own outcome
# names, NOT legacy command names: the client picks an outcome and the service
# picks the command and derives every argument.  The set is closed, so an
# unknown value fails closed before the dispatcher runs.
ACTION_START = "start"
ACTION_CLICK = "click"
ACTION_FINISH = "finish"
ACTIONS = frozenset((ACTION_START, ACTION_CLICK, ACTION_FINISH))

# The endpoint's action -> legacy command, and the endpoint's
# action -> envelope builder / post-execution proof selector.  Kept here so the
# closed vocabulary has exactly one definition in the repository.
ACTION_COMMANDS: Dict[str, str] = {
    ACTION_START: ACTIVATE_COMMAND,
    ACTION_CLICK: ADD_CLICK_COMMAND,
    ACTION_FINISH: ACTIVATE_ITEM_CLICK_COMMAND,
}

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

__all__ = [
    "ACTION_CLICK",
    "ACTION_COMMANDS",
    "ACTION_FINISH",
    "ACTION_START",
    "ACTIONS",
    "ACTIVATE_COMMAND",
    "ACTIVATE_ITEM_CLICK_COMMAND",
    "ADD_CLICK_COMMAND",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "GRID_EXTENT",
    "RESOURCE_VECTOR_SLOTS",
    "build_envelope_click",
    "build_envelope_finish",
    "build_envelope_start",
    "data_field",
    "in_grid",
    "is_action",
    "is_strict_int",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
]


def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D4).

    A fresh list on every call so a caller can never mutate the derivation for
    the next one.  Every action carries it.  This is the same derivation
    boundary the move, sell, store, and upgrade lines took: the committed
    configuration records no price for building, a client-sent delta would let
    any client mint resources, and therefore **no building cost is claimed**.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def is_action(value: Any) -> bool:
    """True for a string inside the closed action vocabulary.

    A non-string is never an action: ``True`` is not ``"start"``, and the
    service must fail such a body closed with ``invalid_action`` rather than
    coercing it.
    """
    return isinstance(value, str) and value in ACTIONS


def _validate_item_index(item_index: Any) -> None:
    if not is_strict_int(item_index):
        raise EnvelopeError(
            "invalid_item_index",
            "item_index must be an integer, got %s" % type(item_index).__name__,
        )


def _resolve_ts(ts: Optional[int]) -> int:
    if ts is None:
        ts = int(time.time())
    if not is_strict_int(ts) or ts < 0:
        raise EnvelopeError("invalid_timestamp", "ts must be a non-negative integer")
    return ts


def _single_command_envelope(
    command: str,
    args: List[Any],
    ts: Optional[int],
) -> Dict[str, Any]:
    """The six-key legacy batch envelope carrying exactly one command."""
    return {
        "first_number": 0,
        "publishActions": [],
        "ts": _resolve_ts(ts),
        "tries": 1,
        "accessToken": "",
        "commands": [[0, command, args, neutral_vector()]],
    }


def build_envelope_start(
    item_index: Any,
    duration: Any,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key batch envelope for one ``activate`` command.

    ``item_index`` is the legacy map key as an integer; whether it names a row
    in the caller's save is *not* checked here (the endpoint resolves it
    against the corpus before executing, and legacy's ``activate`` is a silent
    no-op on a missing row).  ``duration`` is the **positive** countdown the
    row records as ``attr["cp"]``, derived server-side from the item's
    committed ``build_time`` — never from a client.

    Raises :class:`EnvelopeError` with ``invalid_item_index``,
    ``invalid_duration``, or ``invalid_timestamp``.  The non-positive-duration
    refusal is load-bearing, not cosmetic: legacy would **clear the row's whole
    attribute bag** (``command.py:425-427``), destroying the click counter and
    any friend-assist entries, so this contract refuses to derive a "cancel"
    at all (design D6).
    """
    _validate_item_index(item_index)
    if not is_strict_int(duration) or duration <= 0:
        raise EnvelopeError(
            "invalid_duration",
            "duration must be a positive integer, got %s"
            % (
                type(duration).__name__
                if not is_strict_int(duration)
                else repr(duration)
            ),
        )
    return _single_command_envelope(
        ACTIVATE_COMMAND, [item_index, duration], ts
    )


def build_envelope_click(item_index: Any, ts: Optional[int] = None) -> Dict[str, Any]:
    """Derive the six-key batch envelope for one ``add_click`` command.

    ``command.add_click`` reads exactly one positional arg — the legacy map
    key — and calls ``engine.add_click(item)`` (``engine.py:125-130``), which
    raises ``attr["nc"]``, seeding it to ``1`` when absent.  The counter is
    **seeded** by the purchase half (``engine.map_add_item``,
    ``engine.py:25-28``), not here, and **no branch compares it** with the
    item's ``clicks_to_build``: the threshold is the client's.

    Raises :class:`EnvelopeError` with ``invalid_item_index`` or
    ``invalid_timestamp``.
    """
    _validate_item_index(item_index)
    return _single_command_envelope(ADD_CLICK_COMMAND, [item_index], ts)


def build_envelope_finish(item_index: Any, ts: Optional[int] = None) -> Dict[str, Any]:
    """Derive the six-key batch envelope for one ``activate_item_click`` command.

    ``command.activate_item_click`` reads exactly one positional arg — the
    legacy map key — and calls ``engine.activate_item_click(item)``
    (``engine.py:132-135``), which deletes ``attr["nc"]``.  That deletion is the
    only construction write the executed fixture does **not** capture (it is
    established by the recorded investigation's probe C instead), and the
    endpoint proves it with the ``finish`` post-condition.

    Raises :class:`EnvelopeError` with ``invalid_item_index`` or
    ``invalid_timestamp``.
    """
    _validate_item_index(item_index)
    return _single_command_envelope(ACTIVATE_ITEM_CLICK_COMMAND, [item_index], ts)
