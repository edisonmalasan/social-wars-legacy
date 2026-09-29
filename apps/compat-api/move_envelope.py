#!/usr/bin/env python3
"""Derivation of the legacy ``move`` command envelope.

The move deliver line of M7: the client sends a *move intent* (a save id, the
legacy map index of a placement the player already owns, and a target cell)
and never a price, a resource delta, or the two arguments legacy discards.
This module is the single place where that intent becomes the legacy batch
envelope, so the executed-legacy fixture capture
(``capture_move_fixture.py``) and the Compatibility API ``POST /v0/move``
endpoint are checked against *one* derivation — exactly the arrangement the
placement and purchase deliver lines already use (design D6).

Shared derivation (design D6): the serialization and structural helpers are
imported unchanged from :mod:`placement_envelope` — ``is_strict_int``,
``ENVELOPE_KEYS``, ``payload_json``, ``data_field``, ``parse_data_field``,
``EnvelopeError``, ``GRID_EXTENT``, and ``in_grid`` — so the placement and
purchase derivations, their fixtures, and their suites keep passing
untouched.  This module adds only what a move needs: the ``move`` command
name, the **neutral** price vector, and ``build_envelope``.

Why this command (design D1)
    ``move`` is the only legacy branch that repositions an already placed
    item.  It reads exactly five positional args — ``item_index``, ``x``,
    ``y``, ``frame``, ``string`` — resolves the row with
    ``engine.map_get_item(map, item_index)`` (``engine.py:36-40``, i.e.
    ``map["items"][str(item_index)]``) and then writes ``item[1] = x`` and
    ``item[2] = y`` and **nothing else** (``command.py:119-134``).  The
    catalog row for ``move`` (``docs/legacy-protocol/commands.md`` and the
    ``move`` entry of ``docs/legacy-protocol/commands.json``) records the
    same five arguments and the same two writes, plus the fact that a missing
    item logs an error and returns early — a silent no-op that still
    persists the save, which is why the endpoint resolves the index itself
    before executing and never treats legacy's early return as success.
    Which command the Flash client actually sends for a drag is **never
    observed** (Flash is never executed), so the choice is recorded as
    derived-provisional together with every other value below.

Neutral price derivation (design D2)
    ``resources_changed`` is the legacy 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]`` applied *before*
    the branch (``command.py:40``, ``engine.apply_resources``,
    ``engine.py:251-271``).  The derived vector is **all zeros**: the
    committed configuration records no move price anywhere — every item's
    ``cost`` is ``"0"`` and every ``cost_type`` is ``null`` (dead fields),
    ``costs`` prices the *purchase* only, and none of the globals records a
    move cost — so no price is derivable.  Inventing one from the item's
    purchase price would be fabricating behavior, and accepting a
    client-sent price would break the intent-only contract the two delivered
    lines established.  A zero vector is also the only choice that cannot
    corrupt a resource balance, and legacy's per-resource ``max(..., 0)``
    clamp means an observed Flash price, if one exists, would arrive inside
    the deltas we never observe.  This is a **derivation boundary, stated as
    a claim limit**: the service claims neither that moving is free in the
    legacy client nor that it costs anything.

``args`` placeholders (design D6)
    ``frame = 0`` and ``string = ""`` — legacy reads both and discards them
    (they are only bound to local names, ``command.py:123-124``), so the
    client never chooses them.  Both are derived-provisional like the rest of
    the envelope.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` —
    with ``ts`` the current time (or a supplied one) and the other four values
    as documented placeholders (``first_number`` 0, ``publishActions`` [],
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.

Command entry
    ``[0, "move", [item_index, x, y, frame, string], neutral_vector]`` — the
    leading ``0`` is the map id (the SW always sends map 0, and the corpus has
    exactly one map), the argument list is the five positional arguments the
    branch reads, and the trailing vector is the resource delta applied
    *before* the branch.

Grid bounds
    Bounds are **anchor-based** (``0..GRID_EXTENT-1``), the same rule the
    placement derivation uses: footprints may extend past the edge, as the
    committed fresh save's Harbour anchored at ``(99,92)`` with width 10
    already reaches ``x=108``.  Occupancy, ownership, and collision are *not*
    checked here — legacy checks nothing, the client marks invalid targets
    itself (design D5), and anti-cheat validation belongs to Server v1 (M13).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

# Design D6: one shared derivation.  The placement module is imported
# unchanged — nothing here is renamed, moved, or re-implemented.
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

# The one legacy command this deliver line executes (design D1).
MOVE_COMMAND = "move"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The two arguments legacy reads and discards (command.py:123-124), so the
# derivation always sends these values and the client never chooses them.
DEFAULT_FRAME = 0
DEFAULT_STRING = ""

__all__ = [
    "DEFAULT_FRAME",
    "DEFAULT_STRING",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "GRID_EXTENT",
    "MOVE_COMMAND",
    "RESOURCE_VECTOR_SLOTS",
    "build_envelope",
    "data_field",
    "in_grid",
    "is_strict_int",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
]


def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D2).

    A fresh list on every call so a caller can never mutate the derivation
    for the next one.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def build_envelope(
    item_index: Any,
    x: Any,
    y: Any,
    frame: Any = DEFAULT_FRAME,
    string: Any = DEFAULT_STRING,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one ``move`` command.

    ``item_index`` is the legacy map key as an integer; whether it names a row
    in the caller's save is *not* checked here (the endpoint resolves it
    against the corpus before executing, and legacy itself is a silent no-op
    on a missing row).  ``ts`` defaults to the current time
    (derived-provisional; parsed but unread by legacy code, so parity
    normalizes it).  Raises :class:`EnvelopeError` with
    ``invalid_item_index``, ``invalid_coordinates``, ``invalid_frame``,
    ``invalid_string``, or ``invalid_timestamp``; gameplay validation
    (occupancy, the no-op cell, ownership) is the client's job by design D5.
    """
    if not is_strict_int(item_index):
        raise EnvelopeError(
            "invalid_item_index",
            "item_index must be an integer, got %s" % type(item_index).__name__,
        )
    if not is_strict_int(x) or not is_strict_int(y):
        raise EnvelopeError(
            "invalid_coordinates",
            "x and y must be integers, got %s/%s" % (type(x).__name__, type(y).__name__),
        )
    if not in_grid(x, y):
        raise EnvelopeError(
            "invalid_coordinates",
            "anchor (%r, %r) is outside the 0..%d town grid" % (x, y, GRID_EXTENT - 1),
        )
    if not is_strict_int(frame):
        raise EnvelopeError(
            "invalid_frame",
            "frame must be an integer, got %s" % type(frame).__name__,
        )
    if not isinstance(string, str):
        raise EnvelopeError(
            "invalid_string",
            "string must be a string, got %s" % type(string).__name__,
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
        "commands": [
            [0, MOVE_COMMAND, [item_index, x, y, frame, string], neutral_vector()]
        ],
    }
