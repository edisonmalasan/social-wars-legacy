#!/usr/bin/env python3
"""Derivation of the legacy ``store_item`` command envelope.

The store deliver line of M7: the client sends a *store intent* (a save id
and the legacy map index of a placement the player already owns) and never a
quantity, a price, or a resource delta.  This module is the single place where
that intent becomes the legacy batch envelope, so the executed-legacy fixture
capture (``capture_store_fixture.py``) and the Compatibility API ``POST
/v0/store`` endpoint are checked against *one* derivation — exactly the
arrangement the placement, purchase, move, and sell deliver lines already use
(design D6).

Shared derivation (design D6): the serialization and structural helpers are
imported unchanged from :mod:`placement_envelope` — ``is_strict_int``,
``ENVELOPE_KEYS``, ``payload_json``, ``data_field``, ``parse_data_field``, and
``EnvelopeError`` — so the placement, purchase, move, and sell derivations,
their fixtures, and their suites keep passing untouched.  This module adds only
what a store needs: the ``store_item`` command name, the **neutral** resource
vector, and ``build_envelope``.  ``GRID_EXTENT`` and ``in_grid`` are re-exported
only for the same reason the move and sell modules do it (a store has no target
cell, so nothing here validates one; the re-export keeps the four sibling
modules' import shape identical and is not a gameplay claim).

Why this command (design D1)
    ``store_item`` is the only legacy branch that moves a *placed* row into
    storage.  It reads exactly one positional arg — ``item_index`` — pops the
    row with ``engine.map_pop_item(map, item_index)`` (``engine.py:42-47``,
    i.e. ``map["items"].pop(str(item_index))``), and on a missing row logs an
    error and returns early (a silent no-op that still persists the batch).
    Otherwise it reads the item id from the popped row (``item[0]``) and calls
    ``engine.add_store_item(map, item_id)`` (``engine.py:70-76``), which
    increments ``map["store"][str(item_id)]`` by its default quantity ``1``.
    It **writes nothing else** (``command.py:218-232``).  The catalog row for
    ``store_item`` (``docs/legacy-protocol/commands.md`` and the
    ``store_item`` entry of ``docs/legacy-protocol/commands.json``) records the
    same single argument, the same pop-then-increment writes, the same silent
    missing-item early return, and that the client "moves any indexed item into
    storage; no capacity check".  ``place_stored_item`` is the *reverse*
    direction (storage to map — the obvious next slice, and already rejected
    twice as the placement and move alternatives), ``sell_stored_item`` sells
    out of storage, and ``store_add_items`` is the client-chosen grant path
    already deferred by the purchase line, so all three are rejected here.
    Which command the Flash client actually sends for a player-initiated store
    is **never observed** (Flash is never executed), so the choice is recorded
    as derived-provisional together with every other value below.

The branch deliberately does NOT write ``boughtUnits``
    Unlike ``buy`` (``command.py:53``), ``place_stored_item``
    (``command.py:246``), and ``buy_stored_item_cash``
    (``command.py:478-479``), ``store_item`` never calls
    ``engine.bought_unit_add`` (``engine.py:86-90``): a building the player
    puts into storage is *not* appended to ``privateState.boughtUnits``.  That is reproduced exactly here
    and asserted in the fixture and the compat tests rather than "fixed" — the
    contract never sends anything the branch does not read, so no client can
    smuggle the bookkeeping in through an argument or a vector.

Neutral price derivation — and the no-cost claim (design D2)
    ``resources_changed`` is the legacy 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]`` applied *before* the
    branch (``command.py:40``, ``engine.apply_resources``,
    ``engine.py:251-271``).  The derived vector is **all zeros**.  The
    committed configuration records no price for storing anything: every
    item's ``cost`` is ``"0"`` and every ``cost_type`` is ``null`` (dead
    fields) and ``costs`` prices the *purchase* only.  The catalog records that
    the client simply "moves any indexed item into storage" — the server
    computes no price — so deriving one here would be fabrication, and
    accepting a client-sent one would let any client mint resources and break
    the intent-only contract the four delivered lines established.  A zero
    vector is also the only choice that cannot corrupt a resource balance;
    legacy's per-resource ``max(..., 0)`` clamp means an observed Flash delta,
    if one exists, would arrive inside deltas we never observe.  **Storing is
    therefore free in this stage, stated as a derivation boundary rather than a
    claim that the legacy client charges nothing.**  The price question
    belongs to Server v1 (M13) and to the later *resources* deliver line.

No capacity rule (design D2 / non-goals)
    The catalog states plainly that there is **no capacity check** in legacy,
    and none is derived here: storage entries are plain ``{item id: quantity}``
    integers with no limit, no expiry, and no ownership rule anywhere in the
    committed configuration.  Inventing one would be fabricating behavior, so
    **no capacity rule is claimed** — and the branch's own bound (it only ever
    moves an item the player already has placed) is the only limit legacy has.

No quantity argument
    ``engine.add_store_item(map, item_id)`` is called without its third
    argument, so legacy's default quantity is exactly ``1`` and the branch
    reads no other positional arg.  The contract therefore carries **no**
    quantity: a client cannot ask to store two copies, and cannot guess a
    parameter the branch would ignore.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` —
    with ``ts`` the current time (or a supplied one) and the other four
    values as documented placeholders (``first_number`` 0,
    ``publishActions`` [], ``tries`` 1, ``accessToken`` "").  All five
    non-``commands`` fields are parsed and then unread by legacy code, so a
    time-dependent ``ts`` has no behavioral effect and parity normalizes it.

Command entry
    ``[0, "store_item", [item_index], neutral_vector]`` — the leading ``0`` is
    the map id (the SW always sends map 0, and the corpus has exactly one map),
    the argument list is the single positional argument the branch reads, and
    the trailing vector is the resource delta applied *before* the branch.

No gameplay validation
    Addressability, ownership, whether the placement is a building rather than
    a unit, and whether the player may store it at all are **not** checked
    here: legacy ``store_item`` performs no validation of any kind, the client
    offers the action only for a selected and addressable placement, and
    anti-cheat validation belongs to Server v1 (M13).  A store has no target
    cell, so there is no grid input to bound-check.
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
STORE_COMMAND = "store_item"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

__all__ = [
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "GRID_EXTENT",
    "RESOURCE_VECTOR_SLOTS",
    "STORE_COMMAND",
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
    for the next one.  This is the same boundary the move and sell lines
    took: the committed configuration records no storing price, a client-sent
    delta would let any client mint resources, and therefore **no storing cost
    is claimed** — and, because the catalog records that legacy has no
    capacity check at all, **no capacity rule is claimed** either.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def build_envelope(item_index: Any, ts: Optional[int] = None) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one ``store_item`` command.

    ``item_index`` is the legacy map key as an integer; whether it names a row
    in the caller's save is *not* checked here (the endpoint resolves it
    against the corpus before executing, and legacy itself is a silent no-op
    on a missing row).  A store has no target cell, no price, no reason, and
    no quantity, so ``item_index`` is the only input beyond the timestamp.
    ``ts`` defaults to the current time (derived-provisional; parsed but unread
    by legacy code, so parity normalizes it).  Raises
    :class:`EnvelopeError` with ``invalid_item_index`` or
    ``invalid_timestamp``; gameplay validation (does the player own it, is it
    addressable, may it be stored at all) is the client's job by design D5.
    """
    if not is_strict_int(item_index):
        raise EnvelopeError(
            "invalid_item_index",
            "item_index must be an integer, got %s" % type(item_index).__name__,
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
            [0, STORE_COMMAND, [item_index], neutral_vector()]
        ],
    }
