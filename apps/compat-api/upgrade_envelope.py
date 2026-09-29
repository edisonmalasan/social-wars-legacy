#!/usr/bin/env python3
"""Derivation of the legacy two-command upgrade batch envelope.

The upgrade deliver line of M7: the client sends an *upgrade intent* (a save
id and the legacy map index of a placement the player already owns) and never a
target tier, a reason, a cell, an orientation, a player team, a price, or a
resource delta.  This module is the single place where that intent becomes the
legacy batch envelope, so the executed-legacy fixture capture
(``capture_upgrade_fixture.py``) and the Compatibility API ``POST /v0/upgrade``
endpoint are checked against *one* derivation — exactly the arrangement the
placement, purchase, move, sell, and store deliver lines already use.

Shared derivation: the serialization and structural helpers are imported
unchanged from :mod:`placement_envelope` — ``is_strict_int``,
``ENVELOPE_KEYS``, ``payload_json``, ``data_field``, ``parse_data_field``,
``EnvelopeError``, ``GRID_EXTENT``, and ``in_grid`` — so every delivered
derivation, its fixture, and its suite keeps passing untouched.  This module
adds only what an upgrade needs: the two legacy command names, the committed
upgrade reason, the neutral resource vector, and ``build_envelope``.

Why exactly this pair, in exactly this order (design D1)
    There is **no** ``upgrade`` branch in the legacy dispatcher: the 63 named
    ``command.py`` branches (``docs/legacy-protocol/commands.json``) contain
    none, so a single ``upgrade`` command would fall through to the unhandled
    branch and change nothing.  The only branch that consumes a *reason* is
    ``sell`` (``command.py:149-168``), and committed legacy source defines the
    upgrade reason: ``constants.py:970`` ``SELL_REASON_UPGRADE = "UPGR"``.  The
    only branch that can *create* a placement is ``buy``
    (``command.py:42-58``), and it takes the map key and the cell **from the
    client** — ``map_add_item(map, item_index, item_id, x, y, ...)`` — so a
    sale followed by a purchase can reuse the exact key and cell of the row it
    replaces.  The two branches therefore compose into one batch, and the
    composition was executed against the real legacy server: sell-then-buy
    upgrades the row in place, while the *reverse* order also answers
    ``{"result":"success"}`` and leaves the key **absent** — legacy reports
    success for a batch that destroys the building, which is why the endpoint
    proves the post-state rather than trusting the status (design D3).

    What is **established** here: the two command names and their argument
    lists, the ``UPGR`` reason constant, the client-supplied key and cell of
    ``buy``, the fresh-row semantics of ``engine.map_add_item``, the
    ``bought_unit_add`` record, the forced order, and the resulting state.
    What is **derived and never observed from the Flash client**: that the
    Flash client sends exactly this pair, and the values of the buy half's
    ``orientation``, ``playerID``, ``unknown``, and ``reason`` arguments plus
    the neutral price vector.  Flash is never executed in this repository, so
    those are recorded as derived-provisional together with everything else
    below.

The buy half's arguments (design D2)
    ``[item_index, target_item_id, x, y, player, orientation, unknown, reason]``
    (``command.py:42-58``).  ``item_index``, ``x``, and ``y`` are the row's own
    key and cell, which is *how* the pair reuses them — legacy would append a
    new row otherwise.  ``player`` and ``orientation`` come from the same row
    (``player == 1`` selects the ``bought_unit_add`` record and the
    click-to-build seed, ``engine.py:15-29``).  ``unknown = 0`` and
    ``reason = ""`` are the same documented placeholders the placement line
    uses; legacy binds both and discards them.

Fresh-row semantics are documented, not "fixed" (design D5)
    ``engine.map_add_item`` (``engine.py:8-31``) writes a **new** eight-field
    row: a wall-clock ``timestamp``, ``store []``, and — for a ``player == 1``
    item whose config has ``clicks_to_build > 0`` — ``attr {"nc": 0}``, the
    click-to-build counter.  The replaced row's ``timestamp``, ``store``, and
    ``attr`` are **not** carried over.  Reproducing that exactly is the point:
    the upgraded building is present and unfinished, and consuming ``nc``
    belongs to the ``activate`` / ``add_click`` / ``finish_si`` family, which
    the construction-timers deliver line owns.

Neutral price vector — and the no-cost claim (design D4)
    ``resources_changed`` is the legacy 8-slot vector ``[unknown, xp, gold,
    wood, oil, steel, cash, mana]`` applied *before* each branch
    (``command.py:40``, ``engine.apply_resources``, ``engine.py:251-271``).
    The derived vector is **all zeros** on **both** commands.  The committed
    configuration records no upgrade price anywhere: every item's ``cost`` is
    ``"0"`` and every ``cost_type`` is ``null`` (dead fields), ``costs`` prices
    the *purchase* only, and the 139 ``premium_upgrade_costs`` entries belong
    to the separate premium upgrade path (``btnUpgradeCash`` /
    ``CmdPremiumUpgrade``), whose relationship to this contract is unproven.
    The catalog records that prices travel entirely through the client-sent
    deltas — the server computes none — so deriving a price here would be
    fabrication and accepting a client-sent one would let any client mint
    resources and break the intent-only contract the five delivered lines
    established.  A zero vector is also the only choice that cannot corrupt a
    resource balance.  **This change therefore claims no upgrade cost at
    all** — not the target tier's ``costs``, not the difference between tiers,
    and nothing about ``premium_upgrade_costs``.  The price question belongs to
    Server v1 (M13) and to the later *resources* deliver line.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands`` — with
    ``ts`` the current time (or a supplied one) and the other four values as
    documented placeholders (``first_number`` 0, ``publishActions []``,
    ``tries`` 1, ``accessToken`` "").  All five non-``commands`` fields are
    parsed and then unread by legacy code, so a time-dependent ``ts`` has no
    behavioral effect and parity normalizes it.  ``command()`` executes the
    commands in list order and persists the save **once** after the whole batch
    (``command.py:19-32``), so the two commands are atomic with respect to the
    save file.

Command entries
    ``[0, "sell", [item_index, reason], neutral_vector]`` then
    ``[0, "buy", [item_index, target_item_id, x, y, player, orientation,
    unknown, buy_reason], neutral_vector]`` — the leading ``0`` is the map id
    (the SW always sends map 0, and the corpus has exactly one map), the
    argument lists are the positional arguments each branch reads, and the
    trailing vectors are the resource deltas applied *before* the branch.  The
    **order is forced** and is not a style choice: see the reverse-order
    negative oracle recorded in the fixture README and manifest.

No gameplay validation
    Addressability, ownership, and the legacy client's own upgrade rules — the
    level gate ("You need to be level #0# to upgrade this building."), the
    daily limit (``numUpgradesToday`` / ``lastUpgrades/``), and the space
    check ("No space to upgrade") — are **not** enforced here: none of them is
    enforced by the legacy server, none can be reproduced from the repository,
    and the level gate is additionally *inexercisable on the committed corpus*
    (the fresh save's ``maps[0].level`` is 1 and no item's next tier has
    ``min_level <= 1``, the lowest being 5).  Offering the action only for a
    selected, addressable placement that has a resolvable next tier is the
    client's job by design D7, and authoritative validation belongs to Server v1
    (M13).
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

# The two legacy commands this deliver line executes, in the forced order
# (design D1).  Both names are read by the committed dispatcher.
SELL_COMMAND = "sell"
BUY_COMMAND = "buy"

# The committed upgrade reason (design D1/D2): constants.py:970
# ``SELL_REASON_UPGRADE = "UPGR"``.  Derived server-side from committed legacy
# source and never accepted from a client, so no client can claim another
# reason (and in particular cannot claim the combat reason that would route the
# row through push_dead_unit and the resurrectable-unit path).
UPGRADE_REASON = "UPGR"

# Width of the legacy resource vector [unknown, xp, gold, wood, oil, steel,
# cash, mana] (engine.apply_resources, engine.py:251-271).
RESOURCE_VECTOR_SLOTS = 8

# The buy half's discarded placeholders, identical to the ones the placement
# line already uses (command.py binds both and reads neither).
DEFAULT_UNKNOWN = 0
BUY_REASON = ""

__all__ = [
    "BUY_COMMAND",
    "BUY_REASON",
    "DEFAULT_UNKNOWN",
    "ENVELOPE_KEYS",
    "EnvelopeError",
    "GRID_EXTENT",
    "RESOURCE_VECTOR_SLOTS",
    "SELL_COMMAND",
    "UPGRADE_REASON",
    "build_envelope",
    "data_field",
    "in_grid",
    "is_strict_int",
    "neutral_vector",
    "parse_data_field",
    "payload_json",
]


def neutral_vector() -> List[int]:
    """The derived all-zero ``resources_changed`` (design D4).

    A fresh list on every call so a caller can never mutate the derivation for
    the next one.  Both commands carry it.  This is the same derivation
    boundary the move, sell, and store lines took: the committed configuration
    records no upgrade price, a client-sent delta would let any client mint
    resources, and therefore **no upgrade cost is claimed**.
    """
    return [0] * RESOURCE_VECTOR_SLOTS


def build_envelope(
    item_index: Any,
    target_item_id: Any,
    x: Any,
    y: Any,
    player: Any,
    orientation: Any,
    reason: str = UPGRADE_REASON,
    unknown: Any = DEFAULT_UNKNOWN,
    buy_reason: str = BUY_REASON,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one upgrade: two commands.

    ``item_index`` is the legacy map key as an integer, reused by **both**
    commands so the purchase writes over the key the sale removed; whether it
    names a row in the caller's save is *not* checked here (the endpoint
    resolves it against the corpus before executing, and legacy's ``sell`` is a
    silent no-op on a missing row).  ``target_item_id``, ``x``, ``y``,
    ``player``, and ``orientation`` are the endpoint's own derivation from the
    row being replaced and the committed configuration — never client input.
    ``reason`` defaults to the committed ``UPGR`` constant and is validated for
    type only; ``unknown`` and ``buy_reason`` are the documented discarded
    placeholders.  ``ts`` defaults to the current time (derived-provisional;
    parsed but unread by legacy code, so parity normalizes it).

    Raises :class:`EnvelopeError` with ``invalid_item_index``,
    ``invalid_target_item_id``, ``invalid_coordinates``, ``invalid_player``,
    ``invalid_orientation``, ``invalid_reason``, ``invalid_unknown``,
    ``invalid_buy_reason``, or ``invalid_timestamp``.  Every value is checked
    structurally; gameplay validation (does the player own it, is it
    addressable, does it have a next tier at all) belongs to the client by
    design D7 and to Server v1 (M13).
    """
    if not is_strict_int(item_index):
        raise EnvelopeError(
            "invalid_item_index",
            "item_index must be an integer, got %s" % type(item_index).__name__,
        )
    if not is_strict_int(target_item_id):
        raise EnvelopeError(
            "invalid_target_item_id",
            "target_item_id must be an integer, got %s" % type(target_item_id).__name__,
        )
    if not in_grid(x, y):
        raise EnvelopeError(
            "invalid_coordinates",
            "x and y must be integers with anchors inside the 0..%d town grid, "
            "got %s/%s" % (GRID_EXTENT - 1, type(x).__name__, type(y).__name__),
        )
    if not is_strict_int(player):
        raise EnvelopeError(
            "invalid_player",
            "player must be an integer, got %s" % type(player).__name__,
        )
    if not is_strict_int(orientation):
        raise EnvelopeError(
            "invalid_orientation",
            "orientation must be an integer, got %s" % type(orientation).__name__,
        )
    if not isinstance(reason, str):
        raise EnvelopeError(
            "invalid_reason",
            "reason must be a string, got %s" % type(reason).__name__,
        )
    if not is_strict_int(unknown):
        raise EnvelopeError(
            "invalid_unknown",
            "unknown must be an integer, got %s" % type(unknown).__name__,
        )
    if not isinstance(buy_reason, str):
        raise EnvelopeError(
            "invalid_buy_reason",
            "buy_reason must be a string, got %s" % type(buy_reason).__name__,
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
            [0, SELL_COMMAND, [item_index, reason], neutral_vector()],
            [
                0,
                BUY_COMMAND,
                [
                    item_index,
                    target_item_id,
                    x,
                    y,
                    player,
                    orientation,
                    unknown,
                    buy_reason,
                ],
                neutral_vector(),
            ],
        ],
    }
