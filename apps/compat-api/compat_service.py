#!/usr/bin/env python3
"""Compatibility API v0 service (design D3, spec: bootstrap service).

Surface (loopback only, port :5056):

``GET /v0/session``
    ``{protocol, ok, game_version, server_time, saves:[{id,name,xp,level}]}``
    where ``saves`` is the legacy ``all_saves_info()`` result renamed into the
    documented envelope, mirroring the legacy login save list.

``POST /v0/bootstrap`` with JSON ``{"user_id": "<save id>"}``
    ``{protocol, ok, game_version, server_time, saves, config, player_info}``
    where ``config`` is the legacy ``get_game_config()`` payload and
    ``player_info`` is the legacy ``get_player_info()`` payload.

``POST /v0/place`` with JSON ``{"user_id", "item_id", "x", "y", "orientation"?}``
    ``{protocol, ok, game_version, server_time, result, placement, resources}``
    — an intent only. The legacy batch envelope (price vector, next free
    slot, documented placeholders) is derived internally (design D4 of the
    ``building-placement`` change), the unchanged legacy ``command()``
    dispatcher executes it in-process, and the answer carries the legacy
    ``result`` plus the authoritative superset: the persisted eight-field
    ``placement`` entry and the current ``resources`` (design D7). This is
    the one state-mutating surface; the contract accepts no client-supplied
    resource deltas — extra keys are ignored.

``POST /v0/purchase`` with JSON ``{"user_id", "item_id"}``
    ``{protocol, ok, game_version, server_time, result, store, resources}``
    — also an intent only, and the second state-mutating surface. The legacy
    batch envelope is derived internally from the item's config ``costs``
    (the cash-only price on the legacy 8-slot resource vector, one
    ``buy_stored_item_cash`` command whose single argument is the item id,
    and the documented placeholders — design D2 of the ``building-purchase``
    change), the unchanged legacy ``command()`` dispatcher executes it
    in-process, and the answer carries the legacy ``result`` plus the
    authoritative superset: the full post-execution ``store`` mapping and the
    current ``resources`` (design D4). The contract accepts no client-supplied
    price, quantity, or resource deltas — extra keys are ignored.

``POST /v0/move`` with JSON ``{"user_id", "item_index", "x", "y"}``
    ``{protocol, ok, game_version, server_time, result, placement, resources}``
    — an intent only, and the third state-mutating surface. The legacy batch
    envelope is derived internally (one ``move`` command whose five arguments
    are the legacy map index, the target coordinates, and the two documented
    placeholders the branch discards, with the **neutral** derived resource
    vector — design D2/D6 of the ``building-move`` change), the unchanged
    legacy ``command()`` dispatcher executes it in-process, and the answer
    carries the legacy ``result`` plus the authoritative superset: the
    persisted eight-field ``placement`` entry re-read from the save after
    execution and the current ``resources`` (design D4). The contract accepts
    no client-supplied price, resource deltas, ``frame``, or ``string`` — the
    extra keys are ignored. ``item_index`` is the legacy map key as an
    integer and must resolve to a row in the corpus save *before* the
    dispatcher runs, because legacy's own missing-item path is a silent no-op
    that would otherwise be reported as a success.

``POST /v0/sell`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, removed, resources}``
    — an intent only, and the fourth state-mutating surface. The legacy batch
    envelope is derived internally (one ``sell`` command whose two arguments
    are the legacy map index and the **derived** reason the branch treats as a
    log label, with the **neutral** derived resource vector — design D2/D3 of
    the ``building-sell`` change), the unchanged legacy ``command()``
    dispatcher executes it in-process, and the answer carries the legacy
    ``result`` plus the authoritative superset: the eight-field row **as it
    was read before execution** (``removed``), the current ``resources``, and
    a post-execution re-read proving the legacy key is gone from the
    persisted save (design D5). The contract accepts no client-supplied
    reason, refund, price, or resource deltas — the extra keys are ignored,
    so no client can claim the combat ``KILL`` reason and reach
    ``push_dead_unit``. Because the committed configuration records no
    building-sale refund rule, the derived vector is neutral and **this
    service claims no refund at all**. ``item_index`` must resolve to a row
    in the corpus save *before* the dispatcher runs, for the same
    missing-item reason the move line documents, and a row that survives
    execution fails closed with ``internal_error`` instead of claiming a
    removal that never happened.

``POST /v0/store`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, removed, store,
    resources}`` — an intent only, and the fifth state-mutating surface. The
    legacy batch envelope is derived internally (one ``store_item`` command
    whose single argument is the legacy map index, with the **neutral**
    derived resource vector — design D2/D6 of the ``building-store`` change),
    the unchanged legacy ``command()`` dispatcher executes it in-process, and
    the answer carries the legacy ``result`` plus the two-sided authoritative
    superset: the eight-field row **as it was read before execution**
    (``removed``), the **full post-execution storage mapping** (``store``), and
    the current ``resources`` (design D4). The contract accepts no
    client-supplied quantity, price, or resource deltas — the extra keys are
    ignored. Because the committed configuration records no price for
    storing and legacy has no capacity check at all, the derived vector is
    neutral: **this service claims no storing cost and no capacity rule**, and
    ``add_store_item``'s default quantity of exactly ``1`` is the only
    quantity the branch ever uses. The legacy branch deliberately does not
    write ``privateState.boughtUnits`` (unlike ``buy`` /
    ``place_stored_item`` / ``buy_stored_item_cash``), and this endpoint
    reproduces that exactly. ``item_index`` must resolve to a row in the
    corpus save *before* the dispatcher runs, because legacy's missing-item
    path is a silent early return that still persists the batch; and the
    endpoint additionally proves **both** halves of the move after execution
    (the popped key is absent from the map **and** the item's id is present in
    the storage), failing closed with ``internal_error`` if either is untrue.

Deviation recorded for review: the bootstrap envelope also carries ``saves``
(the session envelope plus ``config`` and ``player_info``). Design D3 lists
only ``config`` and ``player_info``; the extra key is a superset of D3 and
keeps the envelope uniform for the boot client.

Structured errors (always JSON, always ``ok:false``, never a partial payload):

=======================  ====  =========================================================
code                     HTTP  when
=======================  ====  =========================================================
``invalid_payload``      400  body missing, not JSON, or not a JSON object
``missing_user_id``      400  ``user_id`` absent, null, or an empty string
``invalid_user_id``      400  ``user_id`` present but not a string
``unknown_user_id``      404  well-formed id that names no save
``missing_item_id``      400  ``/v0/place`` or ``/v0/purchase`` body carries no ``item_id``
``invalid_item_id``      400  ``item_id`` present but not an integer (``bool`` excluded)
``unknown_item_id``      404  integer id absent from the loaded config
``missing_item_index``   400  ``/v0/move``, ``/v0/sell``, or ``/v0/store`` body
                                carries no ``item_index``
``invalid_item_index``   400  ``item_index`` present but not an integer (``bool``
                                excluded)
``unknown_item_index``   404  integer index that names no row in the save's
                                ``map["items"]`` (legacy would silently no-op)
``invalid_reason``       400  derived reason is not a string (server-side
                                derivation failure; never client input)
``invalid_coordinates``  400  ``x``/``y`` missing, not integers, or outside ``0..99``
``invalid_orientation``  400  ``orientation`` present but not an integer
``costs_not_cash``       400  ``/v0/purchase`` item's config price is not a cash
                               price (absent, empty, another resource, mixed)
``bad_request``          400  other malformed requests Flask rejects
``not_found``            404  unknown path
``method_not_allowed``   405  known path, unsupported method
``internal_error``       500  unhandled server failure (including legacy
                              execution raising after validation passed)
=======================  ====  =========================================================

Persistence scope (design D6, spec ``godot-compatibility-boot``): the
session and bootstrap endpoints never persist — this module never calls
``sessions.save_session`` for them and every call leaves the saves
byte-identical. ``POST /v0/place``, ``POST /v0/purchase``,
``POST /v0/move``, ``POST /v0/sell``, and ``POST /v0/store`` execute the
unchanged legacy
``command()`` dispatcher, which
persists through legacy ``save_session`` into the **service corpus's**
``saves/`` and nowhere else; the service never opens a working-tree file for
writing, and it never binds anywhere except ``127.0.0.1`` (the bind address
lives here so both the start command and the tests read one constant).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, jsonify, request

import compat_legacy
import move_envelope
import placement_envelope
import purchase_envelope
import sell_envelope
import store_envelope

PROTOCOL = "compat-v0"
HOST = "127.0.0.1"
DEFAULT_PORT = 5056

ERROR_INVALID_PAYLOAD = "invalid_payload"
ERROR_MISSING_USER_ID = "missing_user_id"
ERROR_INVALID_USER_ID = "invalid_user_id"
ERROR_UNKNOWN_USER_ID = "unknown_user_id"
ERROR_MISSING_ITEM_ID = "missing_item_id"
ERROR_INVALID_ITEM_ID = "invalid_item_id"
ERROR_UNKNOWN_ITEM_ID = "unknown_item_id"
ERROR_MISSING_ITEM_INDEX = "missing_item_index"
ERROR_INVALID_ITEM_INDEX = "invalid_item_index"
ERROR_UNKNOWN_ITEM_INDEX = "unknown_item_index"
ERROR_INVALID_REASON = "invalid_reason"
ERROR_INVALID_COORDINATES = "invalid_coordinates"
ERROR_INVALID_ORIENTATION = "invalid_orientation"
ERROR_COSTS_NOT_CASH = "costs_not_cash"
ERROR_BAD_REQUEST = "bad_request"
ERROR_NOT_FOUND = "not_found"
ERROR_METHOD_NOT_ALLOWED = "method_not_allowed"
ERROR_INTERNAL = "internal_error"


def envelope(boot: compat_legacy.LegacyBoot, **extra: Any) -> Dict[str, Any]:
    """The documented v0 envelope: protocol flag, legacy version, server time."""
    payload: Dict[str, Any] = {
        "protocol": PROTOCOL,
        "ok": True,
        "game_version": boot.game_version,
        "server_time": boot.server_time(),
    }
    payload.update(extra)
    return payload


def error_payload(code: str, message: str) -> Dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "ok": False,
        "error": {"code": code, "message": message},
    }


def error_response(status: int, code: str, message: str) -> Tuple[Dict[str, Any], int]:
    return error_payload(code, message), status


def _resolve_user_id(payload: Any) -> Tuple[Optional[str], Optional[Tuple[Dict[str, Any], int]]]:
    """Validate a bootstrap body; returns ``(user_id, error_response)``."""
    if payload is None:
        return None, error_response(
            400, ERROR_INVALID_PAYLOAD, "request body must be a JSON object"
        )
    if not isinstance(payload, dict):
        return None, error_response(
            400, ERROR_INVALID_PAYLOAD, "request body must be a JSON object"
        )
    if "user_id" not in payload:
        return None, error_response(400, ERROR_MISSING_USER_ID, "user_id is required")
    value = payload["user_id"]
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, error_response(
            400, ERROR_MISSING_USER_ID, "user_id must be a non-empty string"
        )
    if not isinstance(value, str):
        return None, error_response(
            400, ERROR_INVALID_USER_ID, "user_id must be a string"
        )
    return value, None


def _legacy_boot_error(
    failure: compat_legacy.LegacyBootError,
) -> Tuple[Dict[str, Any], int]:
    """Map a legacy adapter precondition failure onto a structured error.

    Messages carry only the adapter's own diagnostic (client-supplied ids
    and error codes), never save content.
    """
    if failure.code == "unknown_user_id":
        return error_response(404, ERROR_UNKNOWN_USER_ID, str(failure))
    return error_response(500, ERROR_INTERNAL, "%s: %s" % (failure.code, failure))


def create_app(legacy: Optional[compat_legacy.LegacyBoot] = None) -> Flask:
    """Build the v0 Flask app over an already-initialized legacy boot state."""
    boot = legacy if legacy is not None else compat_legacy.current()

    app = Flask(__name__, static_folder=None)

    @app.get("/v0/session")
    def v0_session() -> Response:
        return jsonify(envelope(boot, saves=boot.session_list()))

    @app.post("/v0/bootstrap")
    def v0_bootstrap() -> Tuple[Dict[str, Any], int]:
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )
        body = envelope(
            boot,
            saves=boot.session_list(),
            config=boot.config(),
            player_info=boot.player_info(user_id),
        )
        return body, 200

    @app.post("/v0/place")
    def v0_place() -> Tuple[Dict[str, Any], int]:
        """Execute one placement intent through the unchanged legacy path.

        Validation is structural fail-closed (design D5): resolvable save,
        integer item id present in config, integer anchor in the town grid.
        Gameplay rules (grid bounds display, occupancy, affordability) are
        the client's job exactly as they were Flash's — legacy ``buy``
        performs no validation either — and anti-cheat validation belongs
        to Server v1 (M13).  Every failure below returns before the legacy
        dispatcher runs, so the corpus is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_id" not in payload:
            return error_response(400, ERROR_MISSING_ITEM_ID, "item_id is required")
        item_id = payload["item_id"]
        if not placement_envelope.is_strict_int(item_id):
            return error_response(
                400, ERROR_INVALID_ITEM_ID, "item_id must be an integer"
            )
        if not boot.has_item(item_id):
            return error_response(
                404, ERROR_UNKNOWN_ITEM_ID, "no config item with id %d" % item_id
            )

        x = payload.get("x")
        y = payload.get("y")
        if (
            not placement_envelope.is_strict_int(x)
            or not placement_envelope.is_strict_int(y)
            or not placement_envelope.in_grid(x, y)
        ):
            return error_response(
                400,
                ERROR_INVALID_COORDINATES,
                "x and y must be integers with anchors inside the "
                "0..%d town grid" % (placement_envelope.GRID_EXTENT - 1),
            )

        orientation = payload.get("orientation", 0)
        if not placement_envelope.is_strict_int(orientation):
            return error_response(
                400, ERROR_INVALID_ORIENTATION, "orientation must be an integer"
            )

        # Derive the legacy envelope from this save's own state (design D4).
        try:
            envelope_payload = placement_envelope.build_envelope(
                item_id=item_id,
                x=x,
                y=y,
                costs=boot.item_costs(item_id),
                items=boot.map_items(user_id),
                orientation=orientation,
            )
        except placement_envelope.EnvelopeError as failure:
            if failure.code.startswith("costs_"):
                # Derived from committed config, not from client input:
                # the config itself is unresolvable, so this is server-side.
                return error_response(
                    500, ERROR_INTERNAL, "config costs not derivable: %s" % failure.code
                )
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        slot = envelope_payload["commands"][0][2][0]  # type: ignore[index]
        try:
            placement = boot.map_items(user_id).get(str(slot))
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(placement, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the placement entry",
            )
        return (
            envelope(
                boot,
                result="success",
                placement=placement,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/purchase")
    def v0_purchase() -> Tuple[Dict[str, Any], int]:
        """Execute one purchase intent through the unchanged legacy path.

        Validation is structural fail-closed (design D3/D5): a JSON object
        body, a resolvable save, an integer item id present in config, and a
        cash-only config price (design D2).  The level gate and cash
        affordability are gameplay rules the client owns exactly as they were
        Flash's — legacy ``buy_stored_item_cash`` performs no validation at
        all — and anti-cheat validation belongs to Server v1 (M13).  Every
        failure below returns before the legacy dispatcher runs, so the corpus
        is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_id" not in payload:
            return error_response(400, ERROR_MISSING_ITEM_ID, "item_id is required")
        item_id = payload["item_id"]
        if not purchase_envelope.is_strict_int(item_id):
            return error_response(
                400, ERROR_INVALID_ITEM_ID, "item_id must be an integer"
            )
        if not boot.has_item(item_id):
            return error_response(
                404, ERROR_UNKNOWN_ITEM_ID, "no config item with id %d" % item_id
            )

        # Derive the legacy envelope from the loaded config (design D2).  The
        # contract carries no price, quantity, or resource delta: extra keys
        # are ignored so the client's own derivation can never win.
        try:
            envelope_payload = purchase_envelope.build_envelope(
                item_id=item_id,
                costs=boot.item_costs(item_id),
            )
        except purchase_envelope.EnvelopeError as failure:
            if failure.code == ERROR_COSTS_NOT_CASH:
                # The item exists but is not priced in cash alone, so this
                # command's price is not derivable — the client should not
                # have offered the item (a derivation boundary, not a
                # gameplay rule).
                return error_response(400, ERROR_COSTS_NOT_CASH, str(failure))
            if failure.code.startswith("costs_"):
                # Derived from committed config, not from client input:
                # the config itself is unresolvable, so this is server-side.
                return error_response(
                    500, ERROR_INTERNAL, "config costs not derivable: %s" % failure.code
                )
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Read back what actually landed: the whole storage mapping (design
        # D4) so the client needs no arithmetic for pre-existing contents.
        try:
            store = boot.map_store(user_id)
        except compat_legacy.LegacyBootError:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        if not isinstance(store, dict):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        try:
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        return (
            envelope(
                boot,
                result="success",
                store=store,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/move")
    def v0_move() -> Tuple[Dict[str, Any], int]:
        """Execute one move intent through the unchanged legacy path.

        Validation is structural fail-closed (design D3/D5): a JSON object
        body, a resolvable save, an integer item index that names a row in
        the corpus save, and integer anchor coordinates inside the town grid.
        Grid bounds as a *gameplay* rule, footprint occupancy (with the moving
        building's own cells excluded), and the refusal of a no-op move to the
        cell the building already occupies are the client's job exactly as
        they were Flash's — legacy ``move`` performs no validation at all — and
        anti-cheat validation belongs to Server v1 (M13).  The item index is
        resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:126-129``) is a silent early return
        that still persists the save: reporting that as a success would claim a
        state change that never happened.  Every failure below returns before
        the legacy dispatcher runs, so the corpus is untouched on every error
        path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not move_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        x = payload.get("x")
        y = payload.get("y")
        if (
            not move_envelope.is_strict_int(x)
            or not move_envelope.is_strict_int(y)
            or not move_envelope.in_grid(x, y)
        ):
            return error_response(
                400,
                ERROR_INVALID_COORDINATES,
                "x and y must be integers with anchors inside the "
                "0..%d town grid" % (move_envelope.GRID_EXTENT - 1),
            )

        # Resolve the index against the corpus before deriving: an index that
        # names no row must fail closed, never reach legacy's silent no-op.
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )

        # Derive the legacy envelope (design D6): the neutral resource vector
        # and the discarded frame/string placeholders are the module's, never
        # the client's.  The contract carries no price or resource delta:
        # extra keys are ignored so the client's own derivation can never win.
        try:
            envelope_payload = move_envelope.build_envelope(
                item_index=item_index,
                x=x,
                y=y,
            )
        except move_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Read back what actually landed: the persisted eight-field row at that
        # key (design D4), so the client never has to reconstruct it.
        try:
            placement = boot.map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(placement, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the placement entry",
            )
        return (
            envelope(
                boot,
                result="success",
                placement=placement,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/sell")
    def v0_sell() -> Tuple[Dict[str, Any], int]:
        """Execute one sell intent through the unchanged legacy path.

        Validation is structural fail-closed (design D4/D6): a JSON object
        body, a resolvable save, and an integer item index that names a row in
        the corpus save.  Whether the building is sellable at all, who owns
        it, and what it refunds are the client's job exactly as they were
        Flash's — legacy ``sell`` performs no validation at all — and
        anti-cheat validation belongs to Server v1 (M13).  The index is
        resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:154-156``) is a silent early return
        that still persists the save: reporting that as a success would claim
        a removal that never happened.

        No reason is accepted from the client (design D3): the envelope's is
        the derived empty string, so no client can claim ``"KILL"`` and reach
        ``push_dead_unit``.  No price, refund, or resource delta is accepted
        either; the derived vector is neutral, so **this endpoint claims no
        refund** — the committed configuration records no building-sale
        refund rule and the legacy refund travels only in client-sent deltas
        (design D2).  Every failure below returns before the legacy dispatcher
        runs, so the corpus is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not sell_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to remove is the one the persisted save no longer
        # holds afterwards (design D5).
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )
        try:
            removed = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(removed, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # A copy: the in-memory row is the one the legacy dispatcher deletes
        # from the map, so the response must not alias live state.
        removed_row = list(removed)

        # Derive the legacy envelope (design D2/D3/D7): the neutral resource
        # vector and the derived reason are the module's, never the client's.
        # The contract carries no reason, refund, price, or resource delta:
        # extra keys are ignored so the client's own derivation can never win.
        try:
            envelope_payload = sell_envelope.build_envelope(item_index=item_index)
        except sell_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the removal: re-read the map after execution and fail closed
        # if the key survives.  Legacy's branch deleted it, but reporting a
        # removal that the persisted save does not show would be a fabricated
        # authoritative answer (design D5).
        try:
            still_present = boot.has_map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not remove the placement entry",
            )
        return (
            envelope(
                boot,
                result="success",
                removed=removed_row,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/store")
    def v0_store() -> Tuple[Dict[str, Any], int]:
        """Execute one store intent through the unchanged legacy path.

        Validation is structural fail-closed (design D4/D5): a JSON object
        body, a resolvable save, and an integer item index that names a row in
        the corpus save.  Whether the placement is a building the player may
        store at all, who owns it, and whether storage is full are the client's
        job exactly as they were Flash's — legacy ``store_item`` performs no
        validation at all — and anti-cheat validation belongs to Server v1
        (M13).  The index is resolved here rather than left to legacy, because
        legacy's missing-item path (``command.py:222-224``) logs an error and
        returns early while the batch still persists: reporting that as a
        success would claim a state change that never happened.

        No quantity is accepted from the client (design D3): the branch calls
        ``engine.add_store_item(map, item_id)`` without its third argument, so
        legacy's default of exactly ``1`` is the only quantity it can use.  No
        price or resource delta is accepted either; the derived vector is
        neutral, so **this endpoint claims no storing cost** — the committed
        configuration records no storing price — and, because the catalog
        records that legacy has *no* capacity check, **no capacity rule is
        claimed** either.  The legacy branch deliberately does not write
        ``privateState.boughtUnits`` (unlike ``buy`` /
        ``place_stored_item`` / ``buy_stored_item_cash``), and that is
        reproduced exactly rather than "fixed".

        Every failure below returns before the legacy dispatcher runs, so the
        corpus is untouched on every error path.
        """
        payload = request.get_json(silent=True, force=True)
        user_id, error = _resolve_user_id(payload)
        if error is not None:
            return error
        assert user_id is not None and isinstance(payload, dict)
        if user_id not in boot.known_user_ids():
            return error_response(
                404,
                ERROR_UNKNOWN_USER_ID,
                "no save exists for user_id %r" % user_id,
            )

        if "item_index" not in payload:
            return error_response(
                400, ERROR_MISSING_ITEM_INDEX, "item_index is required"
            )
        item_index = payload["item_index"]
        if not store_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to store is the one the persisted save no longer holds
        # afterwards (design D4/D5).  The item id is read from the row here for
        # the same reason: it is what legacy's ``add_store_item`` increments,
        # so it is what the storage proof below must look for.
        try:
            known = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not known:
            return error_response(
                404,
                ERROR_UNKNOWN_ITEM_INDEX,
                "no placement with index %d in this save's map" % item_index,
            )
        try:
            removed = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(removed, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # A copy: the in-memory row is the one the legacy dispatcher pops
        # from the map, so the response must not alias live state.
        removed_row = list(removed)
        item_id = removed_row[0] if removed_row else None
        if not store_envelope.is_strict_int(item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to store",
            )

        # Derive the legacy envelope (design D2/D6): the neutral resource
        # vector is the module's, never the client's.  The contract carries no
        # quantity, price, or resource delta: extra keys are ignored so the
        # client's own derivation can never win.
        try:
            envelope_payload = store_envelope.build_envelope(item_index=item_index)
        except store_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove BOTH halves of the move from the persisted save: the popped key
        # must be gone *and* the item's id must be present in the storage.
        # Reporting either half that the save does not show would be a
        # fabricated authoritative answer (design D4), so each fails closed.
        try:
            still_present = boot.has_map_item(user_id, item_index)
            store = boot.map_store(user_id)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not remove the placement entry",
            )
        if not isinstance(store, dict):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        if str(item_id) not in store:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the storage entry",
            )
        return (
            envelope(
                boot,
                result="success",
                removed=removed_row,
                store=store,
                resources=resources,
            ),
            200,
        )

    @app.errorhandler(400)
    def on_bad_request(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(400, ERROR_BAD_REQUEST, "malformed request")

    @app.errorhandler(404)
    def on_not_found(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(404, ERROR_NOT_FOUND, "unknown endpoint")

    @app.errorhandler(405)
    def on_method_not_allowed(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(405, ERROR_METHOD_NOT_ALLOWED, "method not allowed")

    @app.errorhandler(500)
    def on_internal_error(_error: Any) -> Tuple[Dict[str, Any], int]:
        return error_response(500, ERROR_INTERNAL, "internal server error")

    app.config["COMPAT_LEGACY_CORPUS"] = str(boot.corpus)
    return app
