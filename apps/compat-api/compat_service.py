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
``missing_item_id``      400  ``/v0/place`` body carries no ``item_id``
``invalid_item_id``      400  ``item_id`` present but not an integer (``bool`` excluded)
``unknown_item_id``      404  integer id absent from the loaded config
``invalid_coordinates``  400  ``x``/``y`` missing, not integers, or outside ``0..99``
``invalid_orientation``  400  ``orientation`` present but not an integer
``bad_request``          400  other malformed requests Flask rejects
``not_found``            404  unknown path
``method_not_allowed``   405  known path, unsupported method
``internal_error``       500  unhandled server failure (including legacy
                              execution raising after validation passed)
=======================  ====  =========================================================

Persistence scope (design D6, spec ``godot-compatibility-boot``): the
session and bootstrap endpoints never persist — this module never calls
``sessions.save_session`` for them and every call leaves the saves
byte-identical. ``POST /v0/place`` executes the unchanged legacy
``command()`` dispatcher, which persists through legacy ``save_session``
into the **service corpus's** ``saves/`` and nowhere else; the service
never opens a working-tree file for writing, and it never binds anywhere
except ``127.0.0.1`` (the bind address lives here so both the start
command and the tests read one constant).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, jsonify, request

import compat_legacy
import placement_envelope

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
ERROR_INVALID_COORDINATES = "invalid_coordinates"
ERROR_INVALID_ORIENTATION = "invalid_orientation"
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
