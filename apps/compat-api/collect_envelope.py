#!/usr/bin/env python3
"""Derivation of the legacy ``collect`` command envelope and its payout.

The collect deliver line of M7, and the **first** line in this family whose
derived resource vector is deliberately *not* neutral: the committed
configuration describes a building's income (``collect``, ``collect_type``,
``collect_xp``, ``max_collects``) and the collection ladder
(``COLLECT_MINUTES`` / ``COLLECT_MULTIPLIER``), so the service can derive a
real payout instead of refusing to invent one.  Every rung and every rule
behind it is therefore **derived-provisional** and named below.

The client sends an *intent only* — a save id and the legacy map index of a
placement the player already owns — and never an amount, a resource, a tier, a
time, a price, or a resource delta.  This module is the single place where that
intent becomes the legacy batch envelope, so the executed-legacy fixture
capture (``capture_collect_fixture.py``) and the Compatibility API ``POST
/v0/collect`` endpoint are checked against *one* derivation, exactly as the
placement, purchase, move, sell, store, upgrade, and construction deliver lines
already do.

Shared derivation: the serialization and structural helpers are imported
unchanged from :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
``payload_json``, ``data_field``, ``parse_data_field``, ``EnvelopeError``,
``GRID_EXTENT``, and ``in_grid`` — so every delivered derivation, its fixture,
and its suite keeps passing untouched.  A collection has no target cell, so
``GRID_EXTENT`` and ``in_grid`` are re-exported only to keep the sibling
modules' import shape identical (``store_envelope`` and ``move_envelope`` do
the same); nothing here validates a cell and this is not a gameplay claim.

What legacy actually does (established)
    ``command.collect`` takes exactly one positional argument, resolves the row
    with ``engine.map_get_item``, and writes **only** ``item[3] = time_now``
    (``command.py:136-147``; the ``collect`` row of
    ``docs/legacy-protocol/commands.json`` and ``commands.md``).  A missing row
    logs an error and returns early while the batch still persists, so the
    endpoint resolves the index itself rather than reporting that no-op as a
    success.  The **income is not computed by the server at all**:
    ``engine.apply_resources`` runs *before* the branch (``command.py:40``,
    ``engine.py:251-271``) and applies the client-sent 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]`` verbatim, per resource,
    as ``max(current + delta, 0)``.  The clamp is a legacy bug candidate
    (legacy's own comment on ``engine.py:252`` says the intent was to detect
    negative balances), not a rule this contract reproduces: it only bites when
    a delta would drive a balance below zero, and **none of the derived payouts
    below can do that** — they are non-negative credits added to a balance
    legacy never lets go below zero, so the clamp is never exercised by this
    line's own transactions.

The six derivation decisions (design D1-D6)
    **D1 — the multiplier is applied to the amount (derived-provisional).**
    ``amount = collect x COLLECT_MULTIPLIER[r]`` where ``r`` is the highest
    committed rung whose ``COLLECT_MINUTES[r]`` threshold the elapsed seconds
    ``now - row[3]`` has reached, **clamped at the top rung** and never
    extrapolated.  Supporting evidence: the two globals are parallel four-element
    arrays and the amount is otherwise a constant, so a ladder that did not
    scale the amount would have no effect at all.  *Rejected alternative:*
    scaling nothing (a flat ``collect``) or extrapolating past the last rung —
    both would make ``COLLECT_MULTIPLIER`` dead content.  *No legacy branch
    reads either global*, so the formula itself is derived and the claim is
    limited to "a payout that grows in four committed rungs", never to a
    specific amount the legacy client sends.

    **D2 — ``collect_xp`` scales with the same rung (derived-provisional).**
    The experience is part of the same payout, and applying the committed ladder
    to only the amount would leave the vector internally inconsistent.
    *Rejected alternative:* a flat ``collect_xp`` — equally unobservable, and
    recorded here so a later change can revisit it with evidence instead of
    rediscovering it.

    **D3 — below the first rung, no collection is offered and none is executed
    (derived-provisional).**  ``COLLECT_MINUTES[0] = 5`` with a multiplier of
    ``0.25`` leaves the sub-five-minute case unspecified: a quarter, nothing, or
    a refusal.  The safe reading invents no amount, so :func:`tier_for` returns
    ``None`` and the endpoint fails closed with ``too_early``.  *Rejected
    alternative:* deriving a sub-first-rung amount from the ``0.25`` multiplier,
    and silently paying nothing.

    **D4 — a non-zero ``max_collects`` fails closed; only ``0`` is implemented
    (derived-provisional).**  ``0`` on 767 of 778 stored items reads as "no
    cap", and the corpus's income rows all record ``0``.  What a non-zero value
    caps — one collection, a daily total, or a building's lifetime output — is
    unobserved and the three readings imply different payouts, so the endpoint
    answers ``capped_collection`` (409) rather than picking one.  *Rejected
    alternatives:* treating the cap as a per-collection limit, and ignoring it.

    **D5 — a collection is refused on a row carrying construction state, in both
    layers (established risk, derived rule).**  ``item[3]`` serves as *both* a
    construction start instant (written by ``activate``) and a last-collection
    instant (written by ``collect``).  The executed probe recorded in
    ``docs/legacy-collect-income.md`` and in this change's design settled the
    overlap: ``activate(11, 3600)`` then ``collect(11)`` left the row as
    ``[22, 58, 48, <collect instant>, 0, [], {"cp": 3600}, 1]`` — ``item[3]``
    moved to the **collect** instant while the countdown **survived**, silently
    restarting an active build's timer, and legacy answered
    ``{"result":"success"}``.  So the client offers no ``Collect`` action for
    such a row **and** the endpoint fails closed with
    ``construction_in_progress`` *before* the dispatcher runs.  The two-layer
    choice is deliberate: the compat layer exists precisely so client-supplied
    intent cannot destroy server state, and a single client-side check would be
    a client-trust assumption.  What is established is that legacy does **not**
    prevent this and reports success; what remains derived is that the legacy
    client would never ask.

    **D6 — only the five committed resource types are produced, and mana never
    is (derived-provisional).**  ``collect_type`` values in the committed config
    are exactly ``g`` (731), ``w`` (23), ``o`` (11), ``s`` (11), and ``c`` (2),
    mapping onto the vector's gold, wood, oil, steel, and cash slots.  The
    ``mana`` slot stays zero because **no item records a mana collect type**, and
    the unread ``unknown`` slot 0 stays zero as every delivered line does.  A
    ``collect_type`` outside the five fails closed with
    ``unknown_collect_type`` rather than being coerced, so a content change can
    never silently pay the wrong resource.  *Rejected alternative:* adding a
    ``"m"`` mapping for a content value no item records.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions []``,
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.  The batch carries **exactly
    one** command.

No gameplay validation
    Ownership, whether the placement is a building at all, and every
    cap-adjacent rule are **not** enforced here: no branch reads
    ``COLLECT_MINUTES`` / ``COLLECT_MULTIPLIER`` / ``max_collects``, and legacy
    performs no validation of any kind.  Offering the action is the client's job
    by the change's D9, and authoritative validation belongs to Server v1 (M13).

Provenance: established versus derived
    **Established** from committed legacy source and the two executed-legacy
    probes recorded in ``docs/legacy-collect-income.md``: the command's argument
    shape and its single effect (``item[3] = time_now``); that the income is the
    client-sent vector applied verbatim per resource under the ``max(…, 0)``
    clamp; the content fields that describe a building's income and the ladder
    globals; the corpus facts (the only income-bearing placed rows are the
    decorations — the **Tree** ``905`` at slot 2 and the **Trees** /
    **Small forest** ``930`` / ``931`` at slots 21-28, each ``collect 20``,
    ``collect_type "w"``, ``collect_xp 1``; all 40 rows carry ``item[3] == 0``);
    and that a collection on a just-started construction overwrites the build's
    start instant while the countdown survives, with legacy answering success.
    **Derived and never observed from the Flash client**: D1-D6 above.  Flash is
    never executed in this repository, so the claim is that a payout grows in
    four committed rungs derived from an item's committed income fields, never
    any specific amount the legacy client pays.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any, Dict, List, Optional, Tuple

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

# The single legacy command this deliver line executes (established,
# command.py:136-147).
COLLECT_COMMAND = "collect"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The index of each resource the vector's ``collect_type`` can name, and the
# experience slot.  The mapping is **closed** (design D6): exactly the five
# collect types present in the committed configuration — g 731, w 23, o 11,
# s 11, c 2 out of the 778 stored items — map onto the five payable slots.
# Slot 0 (``unknown``) is unread by every branch and slot 7 (``mana``) is never
# produced because no item records a mana collect type, so both stay zero.
COLLECT_RESOURCE_SLOTS: Dict[str, int] = {"g": 2, "w": 3, "o": 4, "s": 5, "c": 6}
EXPERIENCE_SLOT = 1
# The slots this derivation can never fill, asserted by the suite and enforced
# by :func:`payout_for` itself (design D6).
ALWAYS_ZERO_SLOTS = (0, 7)

# The committed ladder's unit.  ``COLLECT_MINUTES = [5, 60, 240, 480]`` is
# expressed in **minutes**, while both a row's ``item[3]`` and the service's
# ``now`` are Unix **seconds** — so the elapsed time is compared against each
# rung's threshold converted with this factor, and never against the raw
# minutes value.  Getting this wrong would make a five-minute rung read as
# five *seconds* and pay the top rung within the first seconds of a build, so
# the conversion is asserted by the suite at the exact boundary (299/300,
# 3599/3600, 14399/14400, 28799/28800 seconds).
SECONDS_PER_COMMITTED_MINUTE = 60

__all__ = [
    "ALWAYS_ZERO_SLOTS",
    "COLLECT_COMMAND",
    "COLLECT_RESOURCE_SLOTS",
    "ENVELOPE_KEYS",
    "EXPERIENCE_SLOT",
    "EnvelopeError",
    "GRID_EXTENT",
    "RESOURCE_VECTOR_SLOTS",
    "SECONDS_PER_COMMITTED_MINUTE",
    "build_envelope",
    "collect_ladder",
    "data_field",
    "in_grid",
    "is_strict_int",
    "multiplier_for",
    "parse_data_field",
    "payout_for",
    "payload_json",
    "threshold_seconds_for",
    "tier_for",
    "validate_vector",
]


def collect_ladder(ladder: Any) -> Tuple[Tuple[int, ...], Tuple[float, ...]]:
    """Validate a committed ladder and return it as a pair of tuples.

    ``ladder`` is the ``(COLLECT_MINUTES, COLLECT_MULTIPLIER)`` pair read from
    the loaded configuration's ``globals`` — never from a client and never from
    a save.  Both halves must be non-empty sequences of equal length,
    ``minutes`` positive integers in non-decreasing order, and ``multipliers``
    positive numbers.  A ladder the committed configuration does not describe is
    refused whole rather than half-used, because a mismatched pair would
    silently pay the wrong amount.

    Raises :class:`EnvelopeError` with ``no_tier`` — a content-side problem, not
    client input.
    """
    minutes_raw, multipliers_raw = _split_ladder(ladder)
    minutes_tuple = _numeric_tuple(minutes_raw)
    multipliers_tuple = _numeric_tuple(multipliers_raw)
    if not minutes_tuple or len(minutes_tuple) != len(multipliers_tuple):
        raise EnvelopeError(
            "no_tier",
            "the committed collection ladder is not a non-empty pair of equal "
            "length: %r / %r"
            % (list(minutes_tuple), list(multipliers_tuple)),
        )
    previous: Optional[float] = None
    for value in minutes_tuple:
        if value != int(value) or int(value) <= 0:
            raise EnvelopeError(
                "no_tier",
                "a committed ladder threshold is not a positive integer: %r" % (value,),
            )
        if previous is not None and value < previous:
            raise EnvelopeError(
                "no_tier",
                "the committed ladder thresholds are not monotonic: %r"
                % (list(minutes_tuple),),
            )
        previous = value
    for value in multipliers_tuple:
        if value <= 0:
            raise EnvelopeError(
                "no_tier", "a committed ladder multiplier is not positive: %r" % (value,)
            )
    return (
        tuple(int(value) for value in minutes_tuple),
        tuple(multipliers_tuple),
    )


def threshold_seconds_for(tier: Any, ladder: Any) -> int:
    """A rung's committed threshold in **seconds**, or a refusal.

    ``COLLECT_MINUTES`` is committed in minutes, so this is the only place the
    unit conversion happens; the client's next-rung countdown and the endpoint's
    rung selection must both use it rather than reading the raw minutes value.
    """
    minutes_tuple, _multipliers_tuple = collect_ladder(ladder)
    if not is_strict_int(tier) or tier < 0 or tier >= len(minutes_tuple):
        raise EnvelopeError(
            "no_tier",
            "tier must be an index inside the committed ladder, got %r" % (tier,),
        )
    return int(minutes_tuple[tier]) * SECONDS_PER_COMMITTED_MINUTE


def tier_for(elapsed_seconds: Any, ladder: Any) -> Optional[int]:
    """The highest committed rung the elapsed time has reached, or ``None``.

    Design **D1**: ``elapsed_seconds`` is ``now - row[3]`` measured against the
    service's own clock, and the answer is the highest index ``r`` whose
    ``COLLECT_MINUTES[r]`` threshold the elapsed time has reached, **clamped at
    the top rung** — an elapsed time beyond the last threshold returns the last
    index and never extrapolates.  The committed thresholds are minutes and the
    elapsed time is seconds, so the comparison goes through
    :func:`threshold_seconds_for`.

    Design **D3**: when *no* rung is reached the answer is ``None`` so the
    caller fails closed (``too_early``) instead of deriving a sub-first-rung
    amount from the ``0.25`` multiplier.

    A non-integer or negative elapsed time is refused with ``no_tier`` rather
    than clamped: a row whose recorded instant lies in the future is a state
    this contract must report, not silently pay for.
    """
    if not is_strict_int(elapsed_seconds) or elapsed_seconds < 0:
        raise EnvelopeError(
            "no_tier",
            "elapsed seconds must be a non-negative integer, got %s"
            % type(elapsed_seconds).__name__,
        )
    minutes_tuple, _multipliers_tuple = collect_ladder(ladder)
    reached: Optional[int] = None
    for index, threshold in enumerate(minutes_tuple):
        if elapsed_seconds >= threshold * SECONDS_PER_COMMITTED_MINUTE:
            reached = index
    return reached


def multiplier_for(tier: Any, ladder: Any) -> float:
    """The committed multiplier of a rung, or a refusal.

    Design **D1**/``D2``: the same rung scales both the amount and the
    experience.  A tier outside the committed ladder fails closed with
    ``no_tier`` so no extrapolated multiplier can ever reach the vector.
    """
    _minutes_tuple, multipliers_tuple = collect_ladder(ladder)
    if not is_strict_int(tier) or tier < 0 or tier >= len(multipliers_tuple):
        raise EnvelopeError(
            "no_tier",
            "tier must be an index inside the committed ladder, got %r" % (tier,),
        )
    return multipliers_tuple[tier]


def payout_for(
    amount: Any,
    resource_type: Any,
    experience: Any,
    tier: Any,
    ladder: Any,
) -> List[int]:
    """The derived 8-slot ``resources_changed`` for one collection.

    Design **D1**/``D2**: the committed amount lands in the slot its committed
    resource type names and the committed experience in the experience slot,
    each multiplied by the committed multiplier of the reached rung.  Design
    **D6**: the unread ``unknown`` slot 0 and the never-produced ``mana`` slot 7
    are always zero, and a ``collect_type`` outside the committed five fails
    closed with ``unknown_collect_type`` rather than being coerced.

    A fresh list on every call, so a caller can never mutate the derivation for
    the next one.  Raises :class:`EnvelopeError` with ``invalid_amount``,
    ``unknown_collect_type``, ``invalid_experience``, or ``no_tier``.
    """
    if not is_strict_int(amount) or amount < 0:
        raise EnvelopeError(
            "invalid_amount",
            "the committed collection amount must be a non-negative integer, got %s"
            % type(amount).__name__,
        )
    slot = (
        COLLECT_RESOURCE_SLOTS.get(resource_type)
        if isinstance(resource_type, str)
        else None
    )
    if slot is None:
        raise EnvelopeError(
            "unknown_collect_type",
            "collect_type must be one of %s, got %r"
            % (sorted(COLLECT_RESOURCE_SLOTS), resource_type),
        )
    if not is_strict_int(experience) or experience < 0:
        raise EnvelopeError(
            "invalid_experience",
            "the committed collection experience must be a non-negative integer, got %s"
            % type(experience).__name__,
        )
    multiplier = multiplier_for(tier, ladder)
    vector = [0] * RESOURCE_VECTOR_SLOTS
    vector[EXPERIENCE_SLOT] = _scale(experience, multiplier)
    vector[slot] = _scale(amount, multiplier)
    # Belt and braces: the two slots this derivation can never fill (design D6).
    for index in ALWAYS_ZERO_SLOTS:
        vector[index] = 0
    return vector


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` before it is sent to legacy.

    The vector must be a list of exactly eight **non-negative** integers.
    Legacy applies each slot with ``max(current + delta, 0)`` and the income
    here is always a credit, so a negative or non-integer entry is an
    unresolvable derivation rather than a client value; it fails closed with
    ``invalid_vector`` instead of being sent.  (A negative delta is exactly the
    shape that would exercise legacy's clamp, and this contract never produces
    one.)
    """
    if not isinstance(vector, list) or len(vector) != RESOURCE_VECTOR_SLOTS:
        raise EnvelopeError(
            "invalid_vector",
            "resources_changed must be a list of %d slots, got %r"
            % (RESOURCE_VECTOR_SLOTS, vector),
        )
    for index, value in enumerate(vector):
        if not is_strict_int(value) or value < 0:
            raise EnvelopeError(
                "invalid_vector",
                "resources_changed slot %d must be a non-negative integer, got %r"
                % (index, value),
            )
    return list(vector)


def build_envelope(
    item_index: Any,
    vector: Any,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key batch envelope for one ``collect`` command.

    ``item_index`` is the legacy map key as an integer; whether it names a row
    in the caller's save is *not* checked here (the endpoint resolves it against
    the corpus before executing, and legacy's ``collect`` is a silent no-op on a
    missing row).  ``vector`` is the derived payout from :func:`payout_for` —
    never a client value.

    Raises :class:`EnvelopeError` with ``invalid_item_index``,
    ``invalid_vector``, or ``invalid_timestamp``.
    """
    if not is_strict_int(item_index):
        raise EnvelopeError(
            "invalid_item_index",
            "item_index must be an integer, got %s" % type(item_index).__name__,
        )
    checked = validate_vector(vector)
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
        "commands": [[0, COLLECT_COMMAND, [item_index], checked]],
    }


# ------------------------------------------------------------------ helpers --
def _split_ladder(ladder: Any) -> Tuple[Any, Any]:
    """Split a ``(minutes, multipliers)`` pair, refusing a malformed shape."""
    if isinstance(ladder, dict):
        return ladder.get("minutes"), ladder.get("multipliers")
    if isinstance(ladder, (str, bytes)) or not isinstance(ladder, Sequence):
        raise EnvelopeError(
            "no_tier",
            "the committed collection ladder must be a (minutes, multipliers) "
            "pair, got %s" % type(ladder).__name__,
        )
    if len(ladder) != 2:
        raise EnvelopeError(
            "no_tier",
            "the committed collection ladder must be a (minutes, multipliers) "
            "pair, got %d entries" % len(ladder),
        )
    return ladder[0], ladder[1]


def _numeric_tuple(values: Any) -> Tuple[float, ...]:
    """A tuple of finite numbers, or ``()`` for anything else.

    The committed globals are JSON arrays of numbers, so a non-sequence, a
    non-numeric entry, a ``bool``, or a non-finite float is simply "not a
    ladder" here and is reported by the caller's own ``no_tier`` refusal rather
    than coerced.
    """
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        return ()
    numbers: List[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return ()
        if value != value or value in (float("inf"), float("-inf")):
            return ()
        numbers.append(float(value))
    return tuple(numbers)


def _scale(value: int, multiplier: float) -> int:
    """A rung-scaled amount, rounded to a whole resource.

    The committed multipliers are ``0.25``, ``1``, ``2``, and ``3``, so every
    committed product of a committed amount is already an integer
    (``20 x 0.25 = 5``).  The rounding exists only so a future fractional
    multiplier can never put a float on the legacy vector, which
    ``engine.apply_resources`` adds to a stored integer.
    """
    scaled = float(value) * float(multiplier)
    if scaled <= 0:
        return 0
    if scaled.is_integer():
        return int(scaled)
    return int(scaled + 0.5)
