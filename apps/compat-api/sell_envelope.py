#!/usr/bin/env python3
"""Derivation of the legacy ``sell`` command envelope.

The sell deliver line of M7: the client sends a *sell intent* (a save id and
the legacy map index of a placement the player already owns) and never a
reason, a refund, or a price.  This module is the single place where that
intent becomes the legacy batch envelope, so the executed-legacy fixture
capture (``capture_sell_fixture.py``) and the Compatibility API ``POST
/v0/sell`` endpoint are checked against *one* derivation — exactly the
arrangement the placement, purchase, and move deliver lines already use
(design D7).

Shared derivation (design D7): the serialization and structural helpers are
imported unchanged from :mod:`placement_envelope` — ``is_strict_int``,
``ENVELOPE_KEYS``, ``payload_json``, ``data_field``, ``parse_data_field``,
and ``EnvelopeError`` — so the placement, purchase, and move derivations,
their fixtures, and their suites keep passing untouched.  This module adds
only what a sell needs: the ``sell`` command name, the **neutral** resource
vector, the derived reason, and ``build_envelope``.  ``GRID_EXTENT`` and
``in_grid`` are re-exported only for the same reason the move module does it
(a sell has no target cell, so nothing here validates one; the re-export
keeps the three sibling modules' import shape identical and is not a
gameplay claim).

Why this command (design D1)
    ``sell`` is the only legacy branch that removes a *placed* row on a
    player-initiated basis.  It reads exactly two positional args —
    ``item_index`` and ``reason`` — resolves the row with
    ``engine.map_get_item(map, item_index)`` (``engine.py:36-40``, i.e.
    ``map["items"][str(item_index)]``) and then deletes it with
    ``engine.map_delete_item`` (``engine.py:48-52``) and **writes nothing
    else** (``command.py:149-168``).  The catalog row for ``sell`` (``docs/
    legacy-protocol/commands.md`` and the ``sell`` entry of
    ``docs/legacy-protocol/commands.json``) records the same two arguments,
    the same deletion, and the fact that a missing item logs an error and
    returns early — a silent no-op that still persists the save, which is why
    the endpoint resolves the index itself before executing and never treats
    legacy's early return as success.  ``sell_stored_item`` removes from
    *storage* (a later deliver line) and ``batch_remove`` is a combat/batch
    path, so both are rejected here.  Which command the Flash client actually
    sends for a player-initiated sale is **never observed** (Flash is never
    executed), so the choice is recorded as derived-provisional together with
    every other value below.

Neutral price derivation — and the no-refund claim (design D2)
    ``resources_changed`` is the legacy 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]`` applied *before*
    the branch (``command.py:40``, ``engine.apply_resources``,
    ``engine.py:251-271``).  The derived vector is **all zeros**.  The
    committed configuration records no building-sale refund rule anywhere:
    every item's ``cost`` is ``"0"`` and every ``cost_type`` is ``null``
    (dead fields), ``costs`` prices the *purchase* only, the money-adjacent
    global ``MARKET_SELL_PERCENTAGE`` (0.75) governs the *resource* market
    ("SELL 100 WOOD ON MARKET") and not building sales, and no other global
    mentions a sale refund.  The catalog records that **the refund travels
    entirely through the client-sent deltas** — the server computes no price
    — so deriving one here would be fabrication, and accepting a client-sent
    one would let any client mint resources and break the intent-only
    contract the three delivered lines established.  A zero vector is also
    the only choice that cannot corrupt a resource balance; legacy's
    per-resource ``max(..., 0)`` clamp means an observed Flash refund, if one
    exists, would arrive inside deltas we never observe.  **This change
    therefore claims no refund at all** — it is a derivation boundary, not a
    claim that selling is free in the legacy client.  The refund economics
    belong to Server v1 (M13) and to the later *resources* deliver line.

Derived reason (design D3)
    ``reason = ""``.  The branch compares it against ``"KILL"`` and otherwise
    uses it only as a log label, so the empty string is behaviorally inert —
    but the value the Flash client actually sends is unobserved (the static
    SWF inventory shows only combat/system reasons such as
    ``SELL_REASON_KILL``, ``SELL_REASON_BULLDOZE``, ``SELL_REASON_UPGRADE``,
    ``SELL_REASON_TREASURE``, and ``SELL_REASON_ACTIVATOR``, and no reason
    specific to a player-initiated sale), so this change claims nothing about
    it.  The reason is **derived, never chosen**: the endpoint accepts no
    reason from the client, so no client can claim ``"KILL"`` and reach
    ``push_dead_unit`` and the resurrectable-unit path.  That combat path
    belongs to a later milestone (M9+) and is out of scope here.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` —
    with ``ts`` the current time (or a supplied one) and the other four
    values as documented placeholders (``first_number`` 0,
    ``publishActions`` [], ``tries`` 1, ``accessToken`` "").  All five
    non-``commands`` fields are parsed and then unread by legacy code, so a
    time-dependent ``ts`` has no behavioral effect and parity normalizes it.

Command entry
    ``[0, "sell", [item_index, reason], neutral_vector]`` — the leading
    ``0`` is the map id (the SW always sends map 0, and the corpus has
    exactly one map), the argument list is the two positional arguments the
    branch reads, and the trailing vector is the resource delta applied
    *before* the branch.

No gameplay validation
    Occupancy, ownership, price, and "is this building sellable at all" are
    **not** checked here: legacy ``sell`` performs no validation of any kind,
    the client offers the action only for a selected and addressable
    placement, and anti-cheat validation belongs to Server v1 (M13).  A sell
    has no target cell, so there is no grid input to bound-check.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

# Design D7: one shared derivation.  The placement module is imported
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
SELL_COMMAND = "sell"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The derived sell reason (design D3): legacy compares it against "KILL" and
# otherwise only logs it, so the empty string is inert — and it is the one
# value that can never route a row through push_dead_unit.
DEFAULT_REASON = ""

__all__ = [
    "DEFAULT_REASON",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "GRID_EXTENT",
    "RESOURCE_VECTOR_SLOTS",
    "SELL_COMMAND",
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
    for the next one.  This is the same boundary the move line took: the
    committed configuration records no building-sale refund rule, the refund
    would travel in client-sent deltas this contract refuses, and therefore
    **no refund is claimed**.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def build_envelope(
    item_index: Any,
    reason: str = DEFAULT_REASON,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one ``sell`` command.

    ``item_index`` is the legacy map key as an integer; whether it names a row
    in the caller's save is *not* checked here (the endpoint resolves it
    against the corpus before executing, and legacy itself is a silent no-op
    on a missing row).  ``reason`` defaults to the derived empty string and is
    validated only for type — a sell has no target cell, no price, and no
    gameplay input.  ``ts`` defaults to the current time (derived-provisional;
    parsed but unread by legacy code, so parity normalizes it).  Raises
    :class:`EnvelopeError` with ``invalid_item_index``, ``invalid_reason``,
    or ``invalid_timestamp``; gameplay validation (is the building sellable,
    does the player own it) is the client's job by design D6.
    """
    if not is_strict_int(item_index):
        raise EnvelopeError(
            "invalid_item_index",
            "item_index must be an integer, got %s" % type(item_index).__name__,
        )
    if not isinstance(reason, str):
        raise EnvelopeError(
            "invalid_reason",
            "reason must be a string, got %s" % type(reason).__name__,
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
            [0, SELL_COMMAND, [item_index, reason], neutral_vector()]
        ],
    }
