#!/usr/bin/env python3
"""Derivation of the legacy ``buy_stored_item_cash`` command envelope.

The purchase deliver line of M7: the client sends a *purchase intent* (a save
id and an item id) and never a price, a quantity, or a resource delta.  This
module is the single place where that intent becomes the legacy batch envelope,
so the executed-legacy fixture capture
(``capture_purchase_fixture.py``) and the Compatibility API ``POST /v0/purchase``
endpoint are checked against *one* derivation — exactly the arrangement the
placement deliver line already uses (design D6).

Shared derivation (design D6): the serialization and structural helpers are
imported unchanged from :mod:`placement_envelope` — ``is_strict_int``,
``ENVELOPE_KEYS``, ``payload_json``, ``data_field``, ``parse_data_field``,
``EnvelopeError``, and ``COST_SLOTS`` — so the placement derivation, its
fixture, and its suite keep passing untouched.  This module adds only what a
purchase needs: the **cash-only** price vector and ``build_envelope``.

Why this command (design D1)
    ``buy_stored_item_cash`` is the only legacy branch that both names a
    purchase and writes purchase state for a single item:
    ``bought_unit_add(save, item_id)`` plus ``add_store_item(map, item_id)``
    with quantity defaulting to 1 (``command.py:475-480``,
    ``engine.py:70-89``).  It performs no validation of its own, and — like
    every dispatcher branch — it runs after the pre-dispatch
    ``apply_resources(save, map, resources_changed)`` (``command.py:40``,
    ``engine.py:251-271``).  Which command the Flash client actually sends for
    a shop purchase is **never observed** (Flash is never executed), so the
    choice is recorded as derived-provisional together with every other value
    below.

Cash-only price derivation (design D2)
    ``resources_changed`` is the legacy 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]``
    (``engine.apply_resources``).  Exactly one slot may be non-zero: the
    **cash** slot (index 6), carrying the negated ``c`` component of the
    item's raw config ``costs``.  ``docs/legacy-protocol/commands.md`` row 49
    and ``docs/legacy-protocol/commands.json`` record that "cash price travels
    through client-sent deltas", and the branch name itself is a cash purchase,
    so the price is derived onto that one slot and every other slot is ``0``.
    An item whose parsed ``costs`` is not exactly ``{"c": <int>}`` fails
    closed before the dispatcher runs:

    ``costs_not_cash``
        absent, empty, another resource, or a mixed price — the config does
        not price this item in cash, so no price can be derived for *this*
        command without inventing one (a 400: the client should not have
        offered the item).
    ``costs_invalid``
        the config value itself is unresolvable — unparseable JSON, not a JSON
        object, or a non-integer amount (a 500: the server-side config is
        broken, exactly as in placement).

    The cash-only restriction is a **derivation boundary, not a gameplay
    rule**: any-price storage acquisition is the separate ``store_add_items``
    batch-grant path, which this change explicitly does not cover.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` —
    with ``ts`` the current time (or a supplied one) and the other four values
    as documented placeholders (``first_number`` 0, ``publishActions`` [],
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.

Command entry
    ``[0, "buy_stored_item_cash", [item_id], vector]`` — the leading ``0`` is
    the map id (the SW always sends map 0, and the corpus has exactly one map),
    the argument list is the single positional item id the branch reads, and
    the trailing vector is the resource delta applied *before* the branch.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

# Design D6: one shared derivation.  The placement module is imported
# unchanged — nothing here is renamed, moved, or re-implemented.
from placement_envelope import (  # noqa: F401
    COST_SLOTS,
    ENVELOPE_KEYS,
    EnvelopeError,
    data_field,
    is_strict_int,
    parse_data_field,
    payload_json,
)

# The one legacy command this deliver line executes (design D1).
PURCHASE_COMMAND = "buy_stored_item_cash"

# The cash slot of the legacy 8-slot resource vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
CASH_SLOT = COST_SLOTS["c"]

# The only accepted config cost key (design D2).
CASH_COST_KEY = "c"

__all__ = [
    "CASH_COST_KEY",
    "CASH_SLOT",
    "COST_SLOTS",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "PURCHASE_COMMAND",
    "build_envelope",
    "cash_cost_vector",
    "data_field",
    "is_strict_int",
    "parse_data_field",
    "payload_json",
]


def cash_cost_vector(costs: Any) -> List[int]:
    """The negated cash price as the legacy 8-slot ``resources_changed``.

    ``costs`` is the raw config attribute: a JSON-encoded string (the form the
    committed config uses), an already-parsed dict, or ``None``/``""`` for
    items with no price.  The parsed value must be a JSON object whose keys are
    exactly ``{"c"}``; its amount becomes ``-amount`` in the cash slot and
    every other slot stays ``0``.

    Failure codes (design D2), checked in this order so a broken config is
    never mistaken for a non-cash price:

    1. ``costs_invalid`` — the value cannot be resolved at all: unparseable
       JSON, a decoded non-object (including ``null``), or a non-integer
       amount (``bool`` excluded).
    2. ``costs_not_cash`` — the value resolves but does not price the item in
       cash alone: absent, empty, another resource, or a mixed price.
    """
    vector = [0] * 8
    if costs is None or costs == "":
        raise EnvelopeError(
            "costs_not_cash",
            "item has no config costs, so no cash price is derivable",
        )
    parsed = costs
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except ValueError as error:
            raise EnvelopeError(
                "costs_invalid", "config costs is not valid JSON: %s" % error
            )
    if not isinstance(parsed, dict):
        raise EnvelopeError(
            "costs_invalid",
            "config costs must decode to a JSON object, got %s"
            % type(parsed).__name__,
        )
    for key, amount in parsed.items():
        if not is_strict_int(amount):
            raise EnvelopeError(
                "costs_invalid",
                "config costs amount for %r must be an integer, got %s"
                % (key, type(amount).__name__),
            )
    keys = {str(key) for key in parsed}
    if keys != {CASH_COST_KEY}:
        raise EnvelopeError(
            "costs_not_cash",
            "config costs keys %s are not exactly ['%s']; this command's price "
            "must be a cash price" % (sorted(keys), CASH_COST_KEY),
        )
    vector[CASH_SLOT] = -parsed[CASH_COST_KEY]
    return vector


def build_envelope(
    item_id: Any,
    costs: Any,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one purchase.

    ``costs`` is the raw config attribute of ``item_id``; ``ts`` defaults to
    the current time (derived-provisional — legacy parses it and never reads
    it, so parity normalizes it).  Raises :class:`EnvelopeError` with
    ``invalid_item_id``, ``costs_invalid``, ``costs_not_cash``, or
    ``invalid_timestamp``; gameplay validation (the level gate and cash
    affordability) is the client's job by design D5.
    """
    if not is_strict_int(item_id):
        raise EnvelopeError(
            "invalid_item_id", "item_id must be an integer, got %s" % type(item_id).__name__
        )
    vector = cash_cost_vector(costs)
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
        "commands": [[0, PURCHASE_COMMAND, [item_id], vector]],
    }
