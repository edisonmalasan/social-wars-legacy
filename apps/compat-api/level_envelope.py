#!/usr/bin/env python3
"""Derivation of the legacy ``level_up`` command envelope and the level model.

The XP-basics deliver line of M7 — the eleventh and last line in this family —
and the **only** one whose legacy branch has *no* committed content behind it:
``command.level_up`` takes exactly one positional argument and writes
``map["level"] = new_level`` — one line, with **no range check and no experience
validation** (``command.py:81-85``; the ``level_up`` row of
``docs/legacy-protocol/commands.json`` and ``commands.md``, whose own security
note reads "Client sets the map level directly; XP/level consistency is not
verified server-side").

Because the server has no opinion, the *client* owns the level curve entirely,
and the curve is committed content that happens to be **unused**: nothing in
``command.py``, ``engine.py``, ``sessions.py``, ``server.py``, or
``constants.py`` reads the ``levels`` schedule — zero references, repository
wide.  That absence is what makes this line the first in the family where a
**real server-side guard** is possible rather than merely an intent-only
refusal: the curve that constrains the level is committed content, and the
committed corpus proves its index base (design D1).

What legacy actually does (established)
    ``command.level_up`` binds ``args[0]`` as ``new_level`` and assigns it to
    ``map["level"]``, then prints a log line — nothing else.  The 8-slot
    resource vector ``[unknown, xp, gold, wood, oil, steel, cash, mana]`` is
    applied **before** the branch (``command.py:40``,
    ``engine.apply_resources``, ``engine.py:251-271``) as
    ``max(current + delta, 0)`` per resource, so a **client-sent** vector moves
    a balance here exactly as it does for every other command.  No branch reads
    ``maps[0].level`` for any purpose, no branch compares it against
    ``maps[0].xp``, and no branch reads the curve.

THE decision this module exists to record — D1, the index base
    **Stored level *n* is ``levels[n - 1]`` (one-based), and the conversion
    lives in exactly one named function, :func:`entry_index_for_level`.**

    *The interpretation is DERIVED-PROVISIONAL.*  The rejected alternative is
    the **zero-based** reading — ``map["level"]`` as the index itself, so stored
    level 1 would be ``levels[1]`` (``"Servant"``, ``exp_required`` 40) and
    stored level 0 would be ``levels[0]`` (``"Slave"``, ``exp_required`` 0).

    *The committed corpus contradicts zero-based.*  The recorded facts are
    ``corpus xp = 4 | stored level = 1 | level the 0-based curve implies = 0``.
    Under zero-based a player with 4 experience is recorded as level 1 while the
    curve says level 1 begins at 40 experience — a direct contradiction.  Under
    the one-based reading stored level 1 is ``levels[0]`` (``"Slave"``,
    ``exp_required`` 0) and ``4 >= 0`` holds, so **the corpus is
    self-consistent**.

    Guessing zero-based would shift **every** level in the game by one, and the
    error would stay invisible until a player noticed the wrong level name.
    That is why the decision is written down rather than absorbed into an index
    expression, why the conversion is one named function instead of arithmetic
    repeated in each caller, and why every artifact that records the derivation
    also records the rejected alternative.

    The evidence is one data point in a hand-built corpus, so the resolution is
    derived rather than established — but it is derived from the only evidence
    there is, and the rejected alternative is **actively contradicted** rather
    than merely unsupported.

The other decisions this module implements
    **D3 — the target level is derived server-side and the client never
    supplies it.**  ``build_envelope`` is the only place a level reaches the
    envelope, and the endpoint derives it from the stored experience and the
    committed thresholds; a client-supplied ``level`` (or ``new_level``, or
    ``xp``) key is ignored, exactly as the collect and expand endpoints ignore
    client-supplied amounts and prices.

    **D4 — refusals are fail-closed and precede the dispatcher.**  A recorded
    level that already equals the derived level is refused with
    ``level_already_current``, and an experience that cannot support advancing
    past the recorded level is refused with ``xp_below_threshold``.  Both are
    answered **before** ``command()`` runs, so the corpus is byte-identical on
    every error path.

    **D5 — the post-state proof is the level *and the absence of resource
    movement*.**  After execution the endpoint requires that the recorded level
    equals the derived level **and** that *every* stored resource is unchanged.
    The second half matters because ``level_up`` is dispatched with a
    client-sent vector like every other command: the neutral vector below, plus
    a proof that *nothing* moved, is what forecloses vector smuggling — a
    resource-minting exploit wearing a level-up's clothes.  Together with the
    collect line's proof (a value moved by exactly the derived credit) and the
    expand line's (a value moved by exactly the derived debit), this completes
    the family's proof set.

    **D7 — no tuning, no rewards, no unit experience, no tutorial.**  The
    committed ``exp_required`` values are preserved **verbatim**: nothing is
    rebalanced, smoothed, or interpolated.  ``reward_type`` / ``reward_amount``
    are committed on every entry and **consumed by no legacy branch**, so no
    reward is paid and no gate is derived from one — refused rather than
    invented, exactly as the expansion ``neighbors`` / ``inventory_qte``
    requirements were.  ``add_xp_unit`` is out of scope because the committed
    corpus has no unit placements and 0 of its 40 placed rows carry
    ``attr["xp"]``, and ``complete_tutorial`` is a separate progression system.

Shared derivation
    The serialization and structural helpers are imported unchanged from
    :mod:`placement_envelope` — ``is_strict_int``, ``ENVELOPE_KEYS``,
    ``payload_json``, ``data_field``, ``parse_data_field``, ``EnvelopeError``,
    ``GRID_EXTENT``, and ``in_grid`` — so every delivered derivation, its
    fixture, and its suite keeps passing untouched.  A level-up has **no target
    cell and no footprint**, so ``GRID_EXTENT`` and ``in_grid`` are re-exported
    only to keep the sibling modules' import shape identical
    (``expand_envelope`` and ``store_envelope`` do the same); nothing here
    validates a cell and that is not a gameplay claim.

The curve, as committed (``config/main.json`` -> ``levels``, and the normalized
copy under ``packages/game-content``)
    **100** entries, each ``{name, exp_required, reward_type, reward_amount}``,
    all fields fully native numbers.  ``exp_required`` is **strictly
    increasing** with **no duplicates and no non-positive gap**: ``0, 40, 60,
    100, 200, 350, 550, 800, …`` reaching ``2016089205`` at the last entry.
    ``name`` is **not** distinct (44 names across 100 entries, and every entry
    from level 49 onward is ``"Conqueror"``), so it is a **label, not an
    identifier** — which is why the readout reports a *missing* name rather than
    inventing one.  ``reward_type`` is one of ``s`` / ``w`` / ``g`` / ``c`` —
    the same *letter* vocabulary as ``items[].costs``, not the server's resource
    names — and ``reward_amount`` takes exactly three values (``1``, ``50``,
    ``250``); **nothing consumes either.**

    The corpus: ``maps[0].xp`` is the player's experience (the 8-slot vector's
    **slot 1**, written by ``engine.apply_resources``), ``maps[0].level`` is
    written **only** by ``level_up``, and the committed fresh save records
    ``xp 4`` / ``level 1`` / 40 placements / ``store {}``.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions []``,
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.  The batch carries **exactly
    one** command: ``[0, "level_up", [level], vector]``.

No gameplay validation
    Legacy performs no ownership, state, or gameplay validation of any kind for
    this command — it will set level 99, or level ``-5``, if a client asks.  The
    one guard this contract adds is the curve-derived target level, and anything
    beyond it (cross-checking other progression systems, anti-cheat validation)
    belongs to Server v1 (M13).

Provenance: established versus derived
    **Established** from committed legacy source, the committed command
    catalog, and the committed content: that ``level_up`` takes exactly one
    positional argument and writes ``map["level"] = new_level`` with no range
    check and no experience validation; that the client-sent 8-slot vector is
    applied verbatim per resource as ``max(current + delta, 0)`` before the
    branch; that **nothing in the legacy server reads the committed ``levels``
    schedule** (zero references across ``command.py``, ``engine.py``,
    ``sessions.py``, ``server.py``, ``constants.py``); that the curve has 100
    entries whose ``exp_required`` is strictly increasing from ``0`` to
    ``2016089205`` with no duplicate and no non-positive gap; that ``name`` is
    not distinct and neither ``reward_type`` nor ``reward_amount`` is consumed;
    that 0 of the corpus's 40 placed rows carry unit experience; and the corpus
    facts ``xp 4`` / ``level 1`` / 40 placements / empty storage.

    **Derived-provisional and never observed from the Flash client**: D1 — the
    one-based index interpretation, **with the rejected zero-based alternative
    and the corpus contradiction that rejects it**, recorded here, in the
    fixture README, and in the capture manifest.  Flash is never executed in
    this repository, so the claim is that the derived level is **the one the
    committed curve implies for the stored experience** — never one observed a
    real client send, and never a reward.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from collections.abc import Sequence as AbstractSequence
from typing import Any, Dict, List, Optional, Sequence, Tuple

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

# The single legacy command this deliver line executes (established,
# command.py:81-85; the ``level_up`` row of docs/legacy-protocol/commands.json).
LEVEL_UP_COMMAND = "level_up"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# Design D5: the derived vector is NEUTRAL, and *every* slot is one of the
# slots this derivation can never fill.  A level change moves no resource, so
# :func:`validate_vector` refuses anything but the all-zero vector; the
# endpoint's second post-execution proof half then requires that every stored
# resource is **unchanged**, which is what forecloses a client smuggling a
# non-neutral vector through this command.
ALWAYS_ZERO_SLOTS = (0, 1, 2, 3, 4, 5, 6, 7)

# Design D1, recorded everywhere the derivation is recorded.  These three
# constants are the machine-readable form of the decision, the rejected
# alternative, and the status; the endpoint reports them verbatim in its
# ``curve`` block and the capture manifest repeats them.
INDEX_BASE = "one-based"
DERIVATION_STATUS = "derived-provisional"
REJECTED_ALTERNATIVE = "zero-based"

# The committed level curve (config/main.json -> ``levels``, normalized under
# packages/game-content with ``legacy_id`` as the 0-based positional index).
# Cross-checked against the real configuration by the suite; recorded here so
# the derivation's own tests can state the facts they depend on.
COMMITTED_SCHEDULE_LENGTH = 100
COMMITTED_ENTRY_FIELDS = ("name", "exp_required", "reward_type", "reward_amount")
COMMITTED_FIRST_THRESHOLDS = (0, 40, 60, 100, 200, 350, 550, 800)
COMMITTED_FINAL_THRESHOLD = 2016089205
COMMITTED_DISTINCT_NAMES = 44
COMMITTED_REWARD_TYPES = ("c", "g", "s", "w")
COMMITTED_REWARD_AMOUNTS = (1, 50, 250)
COMMITTED_LEVEL_ONE_NAME = "Slave"
COMMITTED_LEVEL_TWO_NAME = "Servant"

# The committed corpus's own experience and recorded level.  These two numbers
# are the **evidence for D1**: at ``xp 4`` the zero-based reading implies level
# 0 while the save records level 1, which is the contradiction that rejects it.
COMMITTED_CORPUS_XP = 4
COMMITTED_CORPUS_LEVEL = 1
COMMITTED_CORPUS_PLACEMENTS = 40

__all__ = [
    "ALWAYS_ZERO_SLOTS",
    "COMMITTED_CORPUS_LEVEL",
    "COMMITTED_CORPUS_PLACEMENTS",
    "COMMITTED_CORPUS_XP",
    "COMMITTED_DISTINCT_NAMES",
    "COMMITTED_ENTRY_FIELDS",
    "COMMITTED_FINAL_THRESHOLD",
    "COMMITTED_FIRST_THRESHOLDS",
    "COMMITTED_LEVEL_ONE_NAME",
    "COMMITTED_LEVEL_TWO_NAME",
    "COMMITTED_REWARD_AMOUNTS",
    "COMMITTED_REWARD_TYPES",
    "COMMITTED_SCHEDULE_LENGTH",
    "DERIVATION_STATUS",
    "ENVELOPE_KEYS",
    "GRID_EXTENT",
    "INDEX_BASE",
    "LEVEL_UP_COMMAND",
    "REJECTED_ALTERNATIVE",
    "RESOURCE_VECTOR_SLOTS",
    "EnvelopeError",
    "build_envelope",
    "data_field",
    "derived_level_for",
    "entry_for_level",
    "entry_index_for_level",
    "entry_snapshot",
    "in_grid",
    "is_strict_int",
    "level_for_entry_index",
    "neutral_vector",
    "next_threshold",
    "parse_data_field",
    "payload_json",
    "remaining_for",
    "schedule_length",
    "thresholds_from_entries",
    "threshold_for",
    "validate_vector",
]


# --------------------------------------------------- the one named conversion --
def entry_index_for_level(level: Any, entries: Optional[int] = None) -> Optional[int]:
    """The committed curve's positional index for a stored level — **D1**.

    **This is the one named place the level/entry conversion exists.**  Stored
    level *n* is ``levels[n - 1]``: the schedule's index base is **one-based**.
    Every caller — the endpoint, the fixture capture, the structural checks, and
    the offline tests — resolves a level's entry through this function, and no
    other place in this repository may index the curve by its own arithmetic.  A
    change with better evidence therefore revises **one function** instead of
    auditing the codebase.

    **The interpretation is derived-provisional** (design D1).  The **rejected**
    alternative is the **zero-based** reading, under which ``map["level"]`` is
    the index itself.  The committed corpus rejects it directly:

        corpus xp = 4 | stored level = 1 | level the 0-based curve implies = 0

    Under zero-based a player with 4 experience is recorded as level 1 while the
    curve says level 1 begins at 40 experience — a contradiction.  Under this
    reading stored level 1 is ``levels[0]`` (``"Slave"``, ``exp_required`` 0)
    and ``4 >= 0`` holds, so the corpus is self-consistent.  Guessing zero-based
    would shift every level in the game by one.

    The edges **refuse gracefully and never raise**:

    * a stored level **below 1** (``0``, negatives) has no committed entry and
      returns ``None`` — Python's ``levels[-1]`` would otherwise silently
      resolve it to the curve's *last* entry;
    * a ``bool`` or any non-integer returns ``None`` too, because ``True`` is an
      ``int`` in Python and would resolve to entry ``0``;
    * when ``entries`` is supplied (the committed entry count, 100), a level
      **above** it returns ``None`` as well, because the curve has no entry to
      name.

    ``None`` therefore means exactly "the committed curve has no entry for this
    level", and the caller turns it into a structured refusal.  A non-integer is
    a different failure and raises :class:`EnvelopeError` with
    ``invalid_level``, so a malformed value can never be quietly treated as a
    level.
    """
    if not is_strict_int(level):
        raise EnvelopeError(
            "invalid_level", "level must be an integer, got %s" % type(level).__name__
        )
    if level < 1:
        return None
    if entries is not None:
        if level > entries:
            return None
    return level - 1


def level_for_entry_index(index: Any) -> Optional[int]:
    """The stored level a positional curve index names — D1's documented inverse.

    Only the *inverse* of :func:`entry_index_for_level`, needed because
    :func:`derived_level_for` finds a level by scanning the committed thresholds
    (which yields a position) and must report it as a level.  It exists as its
    own named function so the ``+ 1`` is not open-coded in a caller either; the
    round trip ``entry_index_for_level(level_for_entry_index(i)) == i`` is
    asserted for every index of the committed curve.

    ``None`` for a non-integer or an index below zero, exactly as the forward
    conversion's edges are graceful rather than raising.
    """
    if not is_strict_int(index):
        return None
    if index < 0:
        return None
    return index + 1


# ------------------------------------------------------- committed schedule --
def schedule_length(entries: Any) -> Optional[int]:
    """The committed curve's length, or ``None`` if it is not a sequence.

    A curve is a non-empty sequence of committed entries; a string, a mapping,
    or an empty sequence is "not a curve" here and is reported by the caller's
    own refusal rather than coerced into a length.  The level space of design
    **D1** is therefore exactly ``1 <= level <= schedule_length(entries)``, and
    that rule lives in one place — this function plus
    :func:`entry_index_for_level` — so the pure derivation and the service's
    adapter accessors cannot disagree about the id space.
    """
    if isinstance(entries, (str, bytes)) or not isinstance(entries, AbstractSequence):
        return None
    if not entries:
        return None
    return len(entries)


def entry_for_level(level: Any, entries: Any) -> Optional[Any]:
    """The committed curve entry a stored level names, or ``None``.

    Resolves the position through :func:`entry_index_for_level` — the single
    named conversion — and then reads the committed entry.  ``None`` means
    exactly "the committed curve has no entry for this level" (level below 1, or
    above the curve), and is a **graceful refusal, not an exception**.

    The entry is returned **verbatim** as a shallow copy — no coercion, no
    defaulting, no filtering — so the commitment to preserve
    ``exp_required`` exactly as committed is structural.  An entry that is not a
    mapping is returned as it is and refused by the helper that reads it.

    Raises :class:`EnvelopeError` with ``invalid_level`` for a non-integer level
    and with ``unknown_level`` for a curve this contract cannot read at all.
    """
    size = schedule_length(entries)
    if size is None:
        raise EnvelopeError(
            "unknown_level", "the committed level curve is not a sequence of entries"
        )
    index = entry_index_for_level(level, size)
    if index is None:
        return None
    row = entries[index]  # type: ignore[index]
    if isinstance(row, Mapping):
        return dict(row)
    return row


def entry_snapshot(row: Any) -> Tuple[Any, ...]:
    """A comparable, order-stable snapshot of a committed curve entry.

    Used by the capture tool's pre-publish checks and by the offline tests, so an
    entry is compared by its **committed field values in the committed field
    order** rather than by mapping iteration order.  An entry that is not a
    mapping is returned as a one-element tuple carrying its type name, so a
    malformed entry is still *reported* rather than raising out of a check.
    """
    if not isinstance(row, Mapping):
        return ("<%s>" % type(row).__name__,)
    return tuple((field, row.get(field)) for field in COMMITTED_ENTRY_FIELDS)


def thresholds_from_entries(entries: Any) -> List[int]:
    """The committed ``exp_required`` ladder, in committed positional order.

    The ladder is read **verbatim**: no threshold is rebalanced, smoothed, or
    interpolated (design D7).  This function only checks that the content is
    the shape this contract can derive from — every entry is a mapping with an
    integer ``exp_required``, and the thresholds are strictly increasing — so a
    curve drift is *reported* instead of producing a silently different level
    model.  A value this contract cannot read fails closed with
    ``unknown_level``; it is a content-side problem, never client input.
    """
    size = schedule_length(entries)
    if size is None:
        raise EnvelopeError(
            "unknown_level", "the committed level curve is not a sequence of entries"
        )
    thresholds: List[int] = []
    for index in range(size):
        row = entries[index]
        if not isinstance(row, Mapping) or "exp_required" not in row:
            raise EnvelopeError(
                "unknown_level",
                "the committed level curve records no exp_required at position %d"
                % index,
            )
        value = row["exp_required"]
        if not is_strict_int(value) or value < 0:
            raise EnvelopeError(
                "unknown_level",
                "the committed exp_required at position %d must be a "
                "non-negative integer, got %r" % (index, value),
            )
        if thresholds and value <= thresholds[-1]:
            raise EnvelopeError(
                "unknown_level",
                "the committed exp_required ladder is not strictly increasing at "
                "position %d (%d after %d)"
                % (index, value, thresholds[-1]),
            )
        thresholds.append(int(value))
    return thresholds


# ------------------------------------------------------------ derived levels --
def derived_level_for(exp: Any, thresholds: Sequence[int]) -> Optional[int]:
    """The level the committed curve implies for a stored experience.

    The derived level is the **highest** level whose committed ``exp_required``
    the experience meets, resolved through :func:`entry_index_for_level`'s
    one-based conversion — and **no other input determines it**: not the
    recorded level (which is unverified, design D2), not a client value (design
    D3), not anything derived from them.

    The edges **refuse gracefully and never raise**:

    * an experience **below the first committed threshold** has no level and
      returns ``None``.  The committed curve's first threshold is ``0``, so this
      cannot happen for a real save; the branch exists for a curve whose floor
      is above zero, and for an experience a curve that starts at ``40`` could
      never place.
    * an experience **above the final threshold** derives the **top** level
      (``100``) and does not raise; there is simply no next level, which
      :func:`next_threshold` reports as ``None``.

    A non-integer experience is a different failure and raises
    :class:`EnvelopeError` with ``invalid_exp`` — ``True`` is an ``int`` in
    Python and would silently place a player.

    ``None`` therefore means exactly "the committed curve's floor is above this
    experience", and the caller turns it into a structured refusal.
    """
    if not is_strict_int(exp):
        raise EnvelopeError(
            "invalid_exp", "experience must be an integer, got %s" % type(exp).__name__
        )
    if not thresholds:
        raise EnvelopeError("unknown_level", "the committed level curve is empty")
    if exp < thresholds[0]:
        return None
    derived_index = 0
    for index, required in enumerate(thresholds):
        if exp >= required:
            derived_index = index
        else:
            break
    return level_for_entry_index(derived_index)


def threshold_for(level: Any, thresholds: Sequence[int]) -> Optional[int]:
    """The committed experience a stored level requires, or ``None``.

    The stored level's own threshold, resolved through the one named conversion.
    ``None`` means "the committed curve has no entry for this level" — a level
    below 1, or above the curve — which is a graceful refusal, never an
    exception.

    Raises :class:`EnvelopeError` with ``invalid_level`` for a non-integer level
    and ``unknown_level`` for an empty ladder.
    """
    if not thresholds:
        raise EnvelopeError("unknown_level", "the committed level curve is empty")
    index = entry_index_for_level(level, len(thresholds))
    if index is None:
        return None
    return thresholds[index]


def next_threshold(exp: Any, thresholds: Sequence[int]) -> Optional[int]:
    """The experience the level **after** the derived one requires, or ``None``.

    The progress figure's target.  ``None`` means "there is no next level" —
    the experience has reached or passed the curve's final threshold — which is a
    graceful refusal, not an exception, and is what the readout reports as a
    completed curve rather than inventing a further level.

    Raises :class:`EnvelopeError` with ``invalid_exp`` for a non-integer
    experience and ``unknown_level`` for an empty ladder.
    """
    derived = derived_level_for(exp, thresholds)
    if derived is None:
        return None
    next_index = entry_index_for_level(derived + 1, len(thresholds))
    if next_index is None:
        return None
    return thresholds[next_index]


def remaining_for(exp: Any, thresholds: Sequence[int]) -> Optional[int]:
    """The experience still needed to reach the next level, or ``None``.

    The committed next threshold minus the stored experience, never negative:
    an experience **at** or **past** a threshold has already reached that level,
    so ``0`` is a real answer and not a clamp.  ``None`` means "there is no next
    level" (see :func:`next_threshold`).

    Raises :class:`EnvelopeError` with ``invalid_exp`` for a non-integer
    experience and ``unknown_level`` for an empty ladder.
    """
    target = next_threshold(exp, thresholds)
    if target is None:
        return None
    assert is_strict_int(exp)
    remaining = target - exp
    return remaining if remaining > 0 else 0


# ----------------------------------------------------------- derived vector --
def neutral_vector() -> List[int]:
    """The derived 8-slot ``resources_changed`` for a level-up: all zeros.

    Design D5.  A level change moves no resource, and the committed curve pays
    no reward (nothing consumes ``reward_type`` / ``reward_amount``, design
    D7), so the only honest vector is the neutral one.  A fresh list on every
    call, so a caller can never mutate the derivation for the next one.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def validate_vector(vector: Any) -> List[int]:
    """Check a derived ``resources_changed`` before it is sent.

    Only the **all-zero** vector is legal here.  ``level_up`` is dispatched like
    every other command with a client-sent vector, and legacy adds each slot to
    the stored balance as ``max(current + delta, 0)`` — so a positive entry is a
    client-trusted **mint** and a negative one a client-trusted **burn**, and
    either would make the endpoint's "nothing moved" proof fail in a way that
    looks like a bug.  Refusing anything but zero here is what forecloses the
    smuggling: the derivation cannot express it, so the endpoint cannot send it.
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
                "resources_changed slot %d is %r: a level-up moves no resource, so "
                "only the neutral all-zero vector is derivable"
                % (index, value),
            )
    return list(vector)


def build_envelope(
    level: Any,
    vector: Any = None,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key batch envelope for one ``level_up`` command.

    ``level`` is the **service-derived** target level (design D3) — never a
    client value.  It must be an integer of at least ``1``: the curve's floor.
    A level below 1 is refused with ``invalid_level`` here even though
    :func:`entry_index_for_level` treats it gracefully, because legacy's branch
    assigns whatever integer it is given (``map["level"] = new_level``) and would
    write it verbatim; the envelope builder is where that must never pass.

    ``vector`` defaults to the neutral :func:`neutral_vector` and is validated
    by :func:`validate_vector`, so a caller that supplies one must supply the
    neutral one.  ``ts`` defaults to the current time (derived-provisional;
    parsed but unread by legacy code, so parity normalizes it).

    Raises :class:`EnvelopeError` with ``invalid_level``, ``invalid_vector``, or
    ``invalid_timestamp``.
    """
    if not is_strict_int(level):
        raise EnvelopeError(
            "invalid_level", "level must be an integer, got %s" % type(level).__name__
        )
    if level < 1:
        raise EnvelopeError(
            "invalid_level",
            "level must be at least 1 (the committed curve's floor), got %d" % level,
        )
    if vector is None:
        vector = neutral_vector()
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
        "commands": [[0, LEVEL_UP_COMMAND, [level], checked]],
    }