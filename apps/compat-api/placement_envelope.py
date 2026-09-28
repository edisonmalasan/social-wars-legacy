#!/usr/bin/env python3
"""Shared derivation of the legacy ``buy`` command envelope (design D3/D4).

Both the fixture capture tool (``capture_placement_fixture.py``) and the
Compatibility API placement endpoint build the exact same legacy batch
envelope from a placement intent, so parity between the executed-legacy
capture and the endpoint is checked against *one* derivation.

The envelope reproduces what the Flash client would have sent; because Flash
is never executed, every value below is **derived-provisional** (recorded in
design D4 and the change docs, never observed):

``resources_changed``
    The negated config ``costs`` mapped onto the legacy 8-slot vector
    ``[unknown, xp, gold, wood, oil, steel, cash, mana]``
    (``engine.apply_resources``), keys ``g/w/o/s/c`` only — the closed
    vocabulary present in the committed config (verified over all 900
    items).  XP is deliberately ``0`` (deferred to the *XP basics* deliver
    line).

``args`` slot
    The smallest positive integer absent from ``map["items"]`` (legacy map
    keys are ``1..N``; the committed fresh save seeds to ``41``).

``args`` placeholders
    ``player=1`` (all 40 fresh placements use player team 1),
    ``orientation`` passthrough (defaults to ``0``), ``unknown=0``,
    ``reason=""`` — unobservable placeholders, documented.

Envelope keys
    Exactly the six keys ``command()`` parses — ``first_number``,
    ``publishActions``, ``ts``, ``tries``, ``accessToken``, ``commands``
    (see ``docs/legacy-protocol/commands.md``) — with ``ts`` as the current
    time and the other values as documented placeholders.  All five
    non-``commands`` fields are parsed and then unread by legacy code, so a
    time-dependent ``ts`` has no behavioral effect (parity normalizes it).

``data`` field
    ``<64-hex sha256>;<payload>`` — the legacy ``command.php`` asserts only
    that byte 64 is ``;`` and never verifies the digest; the serialization
    here (compact, sorted keys) is chosen for deterministic fixture bytes.

Grid bounds
    ``GRID_EXTENT = 100`` is the M6 derived-provisional town extent
    (``apps/client-godot/scripts/town/iso.gd``).  Validation is
    **anchor-based** (``0..99``): footprints may extend past the edge, as
    the committed fresh save's Harbour anchored at ``(99,92)`` with width
    10 already reaches ``x=108``.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Mapping, Optional

# Anchor grid extent: legacy map anchors observed in the committed fresh
# save are all within 0..99 (largest observed anchor is (99, 92)); one
# footprint (Harbour, width 10 at x=99) reaches x=108, so bounds are
# checked on the anchor only.  Must match Godot `Iso.GRID_EXTENT` (M6).
GRID_EXTENT = 100

# config `costs` key -> index in the legacy 8-slot resource vector
# [unknown, xp, gold, wood, oil, steel, cash, mana] (engine.apply_resources).
COST_SLOTS: Dict[str, int] = {"g": 2, "w": 3, "o": 4, "s": 5, "c": 6}

# Legacy `buy` args[4]: player team. All 40 fresh placements use 1.
PLAYER_TEAM = 1

# The six envelope keys `command()` parses (docs/legacy-protocol/commands.md).
ENVELOPE_KEYS = ("first_number", "publishActions", "ts", "tries", "accessToken", "commands")


class EnvelopeError(Exception):
    """A value the derivation cannot map onto the legacy envelope.

    ``code`` is a stable machine code the Compatibility API endpoint turns
    into a structured JSON error; the message never contains save content.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def is_strict_int(value: Any) -> bool:
    """True for ``int`` but not ``bool`` (``isinstance(True, int)`` is True)."""
    return isinstance(value, int) and not isinstance(value, bool)


def in_grid(x: Any, y: Any) -> bool:
    """Anchor cell inside the shared town grid (``0..GRID_EXTENT-1``)."""
    return (
        is_strict_int(x)
        and is_strict_int(y)
        and 0 <= x < GRID_EXTENT
        and 0 <= y < GRID_EXTENT
    )


def cost_vector(costs: Any) -> List[int]:
    """Negated config ``costs`` as the legacy 8-slot ``resources_changed``.

    ``costs`` is the raw config attribute: a JSON-encoded string (all 778
    committed occurrences), an already-parsed dict, ``None``/``""`` for
    items with no cost (122 items).  Every amount becomes ``-amount`` in
    its mapped slot; all other slots stay ``0``.  Unknown cost keys or
    non-integer amounts raise :class:`EnvelopeError` — the committed config
    vocabulary is exactly ``g/w/o/s/c`` with integer amounts, so anything
    else is an unresolvable derivation and must fail closed.
    """
    vector = [0] * 8
    if costs is None or costs == "":
        return vector
    parsed = costs
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except ValueError as error:
            raise EnvelopeError(
                "costs_invalid", "config costs is not valid JSON: %s" % error
            )
    if parsed is None:
        return vector
    if not isinstance(parsed, dict):
        raise EnvelopeError(
            "costs_invalid",
            "config costs must decode to a JSON object, got %s"
            % type(parsed).__name__,
        )
    for key, amount in parsed.items():
        slot = COST_SLOTS.get(str(key))
        if slot is None:
            raise EnvelopeError(
                "costs_unknown_key",
                "config costs key %r is not in the legacy vector mapping %s"
                % (key, sorted(COST_SLOTS)),
            )
        if not is_strict_int(amount):
            raise EnvelopeError(
                "costs_invalid",
                "config costs amount for %r must be an integer, got %s"
                % (key, type(amount).__name__),
            )
        vector[slot] = -amount
    return vector


def next_free_slot(items: Mapping[Any, Any]) -> int:
    """Smallest positive integer absent from the map's item keys.

    Legacy map keys are ``str(index)`` written by ``engine.map_add_item``;
    keys that do not parse as integers cannot collide with a numeric slot
    string and are ignored (documented, never observed in a real save).
    """
    used = set()
    for key in items:
        try:
            used.add(int(key))
        except (TypeError, ValueError):
            continue
    slot = 1
    while slot in used:
        slot += 1
    return slot


def build_envelope(
    item_id: Any,
    x: Any,
    y: Any,
    costs: Any,
    items: Mapping[Any, Any],
    orientation: Any = 0,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Derive the six-key legacy batch envelope for one ``buy`` command.

    ``items`` is ``save["maps"][0]["items"]`` as loaded before execution;
    ``costs`` is the raw config attribute of ``item_id``.  ``ts`` defaults
    to the current time (derived-provisional; parsed but unread by legacy
    code, so parity normalizes it).  Raises :class:`EnvelopeError` when the
    coordinates, orientation, or costs cannot be mapped structurally —
    gameplay validation (bounds/occupancy/affordability display) is the
    client's job by design D5.
    """
    if not is_strict_int(item_id):
        raise EnvelopeError(
            "invalid_item_id", "item_id must be an integer, got %s" % type(item_id).__name__
        )
    if not is_strict_int(x) or not is_strict_int(y):
        raise EnvelopeError(
            "invalid_coordinates",
            "x and y must be integers, got %s/%s" % (type(x).__name__, type(y).__name__),
        )
    if not is_strict_int(orientation):
        raise EnvelopeError(
            "invalid_orientation",
            "orientation must be an integer, got %s" % type(orientation).__name__,
        )
    vector = cost_vector(costs)
    slot = next_free_slot(items)
    args = [slot, item_id, x, y, PLAYER_TEAM, orientation, 0, ""]
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
        "commands": [[0, "buy", args, vector]],
    }


def payload_json(envelope: Mapping[str, Any]) -> str:
    """Deterministic payload serialization (compact, sorted keys).

    Chosen for reproducible fixture bytes; legacy never inspects the
    serialization, only parses the JSON after the ``;``.
    """
    return json.dumps(envelope, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def data_field(envelope: Mapping[str, Any]) -> str:
    """The ``command.php`` ``data`` form field: ``<64-hex>;<payload>``.

    The digest is sha256 of the UTF-8 payload bytes — legacy asserts only
    that byte 64 is ``;`` and never verifies it (documented).
    """
    payload = payload_json(envelope)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert len(digest) == 64
    return digest + ";" + payload


def parse_data_field(data: Any) -> Dict[str, Any]:
    """Inverse of :func:`data_field` for tests and fixture reading.

    Validates the structural contract of the legacy ``data`` field
    (exactly 64 hex chars, ``;`` at byte 64, decodable JSON object) and
    verifies the digest against the payload.
    """
    if not isinstance(data, str) or len(data) < 65 or data[64] != ";":
        raise EnvelopeError(
            "invalid_data_field", "data field must be '<64 hex>;<json payload>'"
        )
    digest, payload = data[:64], data[65:]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise EnvelopeError("invalid_data_field", "data field digest is not lowercase hex")
    actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if actual != digest:
        raise EnvelopeError("invalid_data_field", "data field digest does not match payload")
    try:
        envelope = json.loads(payload)
    except ValueError as error:
        raise EnvelopeError("invalid_data_field", "data payload is not JSON: %s" % error)
    if not isinstance(envelope, dict):
        raise EnvelopeError("invalid_data_field", "data payload is not a JSON object")
    missing = [key for key in ENVELOPE_KEYS if key not in envelope]
    if missing:
        raise EnvelopeError(
            "invalid_data_field", "data payload is missing keys: %s" % ", ".join(missing)
        )
    return envelope
