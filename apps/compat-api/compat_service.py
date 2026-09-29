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

``POST /v0/upgrade`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, removed, upgraded,
    resources}`` — an intent only, and the sixth state-mutating surface.  An
    upgrade is **one legacy batch with two commands in a forced order**: a
    ``sell`` carrying the committed upgrade reason ``"UPGR"``
    (``constants.py:970``) followed by a ``buy`` of the target tier that
    reuses the row's own map key, cell, orientation, and player team
    (``command.py:42-58``: ``buy`` takes its key and cell from the client,
    which is exactly how the pair replaces the row in place).  The legacy batch
    envelope is derived internally — the target tier from the committed
    configuration's ``upgrades_to``, the reason from the committed legacy
    constant, the cell / orientation / player from the row being replaced, and
    the **neutral** derived resource vector on **both** commands (design
    D2/D4 of the ``building-upgrade`` change) — the unchanged legacy
    ``command()`` dispatcher executes it in-process, and the answer carries
    the legacy ``result`` plus the two-sided authoritative superset: the
    eight-field row **as it was read before execution** (``removed``), the
    eight-field row **re-read from the persisted save after execution**
    (``upgraded``), and the current ``resources`` (design D5).  The contract
    accepts no client-supplied target tier, reason, coordinates, orientation,
    player, quantity, price, or resource deltas — the extra keys are ignored.

    Because the committed configuration records no upgrade price anywhere, the
    derived vector is neutral and **this service claims no upgrade cost of any
    kind** — not the target tier's ``costs``, not the difference between
    tiers, and nothing about ``premium_upgrade_costs``.  ``item_index`` must
    resolve to a row in the corpus save *before* the dispatcher runs, because
    legacy's missing-item path is a silent early return that still persists
    the save; a placement whose item has no resolvable next tier answers
    ``no_upgrade_path`` (400) before the dispatcher runs, so a building that
    cannot be upgraded is never reduced to a bare sale; and after execution
    the endpoint proves **all three** facts of the replacement — the key still
    exists, its item id equals the derived target tier, and its cell equals the
    pre-execution cell — failing closed with ``internal_error`` otherwise.
    That proof exists because legacy answers ``{"result":"success"}`` for the
    *reverse* command order while leaving the key absent, so a success status
    is not evidence of an upgrade.  The legacy client's own upgrade rules — the
    level gate, the daily-upgrade limit, and the space check — are known to
    exist and are deliberately **not** enforced here: none is enforced by the
    legacy server and none can be reproduced from the repository.

``POST /v0/construction`` with JSON ``{"user_id", "item_index", "action"}``
    ``{protocol, ok, game_version, server_time, result, previous, row, action,
    resources}`` — an intent only, and the seventh state-mutating surface.  One
    call carries **exactly one** of the three legacy construction commands; the
    action names an *outcome* and the service chooses the command and derives
    every argument (design D2 of the ``building-construction`` change):
    ``"start"`` → ``activate`` with a duration derived from the addressed
    placement's item's committed ``build_time``, ``"click"`` → ``add_click``,
    ``"finish"`` → ``activate_item_click``.  The action vocabulary is **closed**;
    anything else fails closed with ``invalid_action`` before the dispatcher
    runs.  The unchanged legacy ``command()`` dispatcher executes the batch
    in-process, and the answer carries the legacy ``result`` plus the
    authoritative superset: the eight-field row **as it was read before
    execution** (``previous``), the eight-field row **re-read from the
    persisted save after execution** (``row``), the **resolved** ``action``,
    and the current ``resources`` (design D5).  Unlike every earlier line this
    contract carries **no derived placeholder argument at all**, and it accepts
    no client-supplied duration, price, quantity, or resource deltas — the
    extra keys (``duration``, ``price``, ``resources_changed``, ``count``, …)
    are ignored, so no client value can influence the countdown.

    A placement whose item has **no resolvable positive committed build time**
    answers ``no_build_time`` (400) before the dispatcher runs, so an
    unbuildable row is never handed a coerced duration.  That refusal is
    load-bearing: legacy's ``activate`` with a non-positive duration does not
    cancel a build, it **clears the row's whole attribute bag**, destroying
    the click counter and any friend-assistance entries
    (``command.py:425-427``), so this contract only ever sends a positive
    derived duration and exposes **no cancel action** (design D6).

    Because the committed configuration records no price for building, the
    derived vector is neutral and **this service claims no building cost at
    all**; the loaded ``BUILD_SPEEDUP_PRICING`` / ``BUILD_SPEEDUP_MIN_TIME``
    globals price a *speedup*, which is a separate mechanism deliberately out
    of scope (design D4).  No
    branch compares the click counter with the item's ``clicks_to_build``, so
    the completion threshold and the remaining time (``cp - (now - item[3])``)
    are **client-side derivations with no server enforcement**; whether a build
    may start on a row that already carries construction state is the client's
    call, and authoritative validation belongs to Server v1 (M13).

    After execution the endpoint proves the per-action post-condition
    (design D3) and fails closed with ``internal_error`` on any other outcome:
    the row still exists and is a list (a construction action must never
    destroy a row), and then ``start`` → ``attr["cp"]`` equals the derived
    duration, ``click`` → ``attr["nc"]`` is present and at least ``1``,
    ``finish`` → ``attr["nc"]`` is absent.

``POST /v0/collect`` with JSON ``{"user_id", "item_index"}``
    ``{protocol, ok, game_version, server_time, result, previous, row, payout,
    tier, reference_time, resources}`` — an intent only, and the eighth
    state-mutating surface.  This is the **first** line in this family whose
    derived resource vector is deliberately *not* neutral, because for the
    first time the committed configuration describes the action's effect
    (design D1-D6 of the ``building-collect`` change).  The unchanged legacy
    ``command()`` dispatcher executes one ``collect`` command in-process; that
    branch writes **only** ``item[3] = time_now`` (``command.py:136-147``) and
    the income is the client-sent 8-slot vector applied verbatim per resource
    as ``max(current + delta, 0)`` by ``engine.apply_resources`` before the
    branch runs (``engine.py:251-271``), so the payout this service derives is
    **the vector it sends**.  The answer carries the legacy ``result`` plus the
    authoritative superset: the eight-field row **as it was read before
    execution** (``previous``), the eight-field row **re-read from the persisted
    save after execution** (``row``), the derived ``payout`` and the ladder
    ``tier`` it came from, the ``reference_time`` the elapsed time was computed
    against, and the current ``resources`` (design D8).

    Nothing but the save id and the index enters the contract: no amount,
    resource, tier, time, price, or resource delta is accepted from a client —
    the extra keys (``amount``, ``resource``, ``tier``, ``time``, ``price``,
    ``resources_changed``, ``collect``, ``collect_type``, ``collect_xp``,
    ``max_collects``, …) are ignored.  The payout is therefore derived entirely
    from committed content and the addressed row's own state: the amount from
    the item's committed ``collect``, the resource from its committed
    ``collect_type``, the experience from its committed ``collect_xp``, each
    scaled by the committed ladder rung (``COLLECT_MINUTES`` /
    ``COLLECT_MULTIPLIER``) the row's elapsed time has actually reached,
    **clamped at the top rung**.  The vector's unread ``unknown`` slot and its
    never-produced ``mana`` slot are always zero.

    Five content/guard conflicts fail closed with **409** and no mutation, each
    a **derived-provisional** decision that refuses rather than guesses:
    ``capped_collection`` for an item whose committed ``max_collects`` is
    non-zero (only ``0`` is implemented, because nothing says what a non-zero
    cap limits), ``unknown_collect_type`` for a ``collect_type`` outside the
    committed five ``g/w/o/s/c`` (the committed census is 731/23/11/11/2 and no
    item records a mana type), ``no_income`` for an item whose committed
    ``collect`` is ``0`` (727 of 778 stored items, including 39 of the corpus's
    40 placed rows), ``too_early`` when no committed rung is reached
    (``COLLECT_MINUTES[0] = 5``; a sub-rung amount would be invented), and
    ``construction_in_progress`` for a row whose attribute bag carries a
    countdown ``cp`` or a click counter ``nc``.

    That last refusal is **required, not defensive** (design D5): ``item[3]``
    is *both* a construction start instant (written by ``activate``) and a
    last-collection instant (written by ``collect``), and an executed-legacy
    probe showed ``activate(11, 3600)`` followed by ``collect(11)`` leaving
    ``[22, 58, 48, <collect instant>, 0, [], {"cp": 3600}, 1]`` — the build's
    start instant overwritten while the countdown survived, silently restarting
    an active build's timer, with the legacy server answering
    ``{"result":"success"}``.  The delivered construction line reads that same
    field as a build's start instant, so this endpoint refuses the collection
    **before** the dispatcher runs and the corpus is left byte-identical.

    After execution the endpoint proves the post-state in **two** ways
    (design D8) and fails closed with ``internal_error`` on any other outcome:
    the row still exists, is an eight-field list, and its recorded collection
    instant moved **strictly forward**; **and** every stored resource changed by
    **exactly** the derived delta.  The second check is what makes a reduced or
    diverging payout *reported* rather than trusted — legacy's ``max(…, 0)``
    clamp would otherwise let a short credit look like a success.  The
    pre-execution ``resources`` are read **before** dispatch so the comparison
    is against the state the batch actually started from.

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
``missing_item_index``   400  ``/v0/move``, ``/v0/sell``, ``/v0/store``,
                                ``/v0/upgrade``, ``/v0/construction``, or
                                ``/v0/collect`` body carries no ``item_index``
``invalid_item_index``   400  ``item_index`` present but not an integer (``bool``
                                excluded)
``unknown_item_index``   404  integer index that names no row in the save's
                                ``map["items"]`` (legacy would silently no-op)
``no_upgrade_path``      400  ``/v0/upgrade``: the addressed placement's item
                                has no resolvable next tier in the committed
                                configuration (missing reference, the ``-1`` /
                                ``0`` sentinels, or an unresolvable id) — the
                                legacy dispatcher never runs, so such a row is
                                never reduced to a bare sale
``missing_action``       400  ``/v0/construction`` body carries no ``action``
``invalid_action``       400  ``action`` present but not a string, or outside
                                the closed set ``{"start", "click", "finish"}``
``no_build_time``        400  ``/v0/construction`` with ``action "start"``: the
                                addressed placement's item has no resolvable
                                **positive** committed ``build_time`` (absent,
                                non-integer, zero, or negative) — the legacy
                                dispatcher never runs, so a non-positive
                                duration can never reach ``activate`` and
                                clear the row's whole attribute bag
``invalid_duration``     400  derived start duration is not a positive integer
                                (server-side derivation failure; never client
                                input)
``capped_collection``    409  ``/v0/collect``: the addressed placement's item
                                records a **non-zero** committed ``max_collects``
                                — only ``0`` is implemented, because nothing in
                                the repository says whether a non-zero cap
                                limits one collection, a daily total, or a
                                building's lifetime output.  The legacy
                                dispatcher never runs, and the cap is never
                                interpreted
``unknown_collect_type`` 409  ``/v0/collect``: the addressed placement's item
                                records a ``collect_type`` outside the
                                committed vocabulary ``{g, w, o, s, c}`` (the
                                census is 731/23/11/11/2 over the 778 stored
                                items, and no item records a mana type, so the
                                vector's ``mana`` slot is always zero).  The
                                value is refused, never coerced into an assumed
                                resource
``no_income``            409  ``/v0/collect``: the addressed placement's item
                                records a committed collection amount of ``0``,
                                or none it can describe (absent, non-integer, or
                                negative) — 727 of the 778 stored items and 39 of
                                the corpus's 40 placed rows.  The legacy
                                dispatcher never runs
``too_early``            409  ``/v0/collect``: the addressed row's elapsed time
                                since its recorded collection instant has
                                reached **no** committed ladder rung
                                (``COLLECT_MINUTES[0] = 5``), so a payout would
                                have to be invented.  No corpus row carries a
                                recent instant, so this path is covered by a
                                stubbed instant rather than by a fixture
``construction_in_progress``
                          409  ``/v0/collect``: the addressed row's attribute
                                bag carries a construction countdown (``cp``) or
                                a build-click counter (``nc``).  ``collect``
                                writes the same ``item[3]`` that
                                ``activate`` stamps as a build's start instant,
                                and an executed-legacy probe showed the
                                countdown surviving the overwrite while the
                                legacy server answered success.  Refused before
                                the dispatcher runs, so the delivered
                                construction timers are never corrupted
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
``POST /v0/move``, ``POST /v0/sell``, ``POST /v0/store``,
``POST /v0/upgrade``, ``POST /v0/construction``, and ``POST /v0/collect``
execute the unchanged legacy ``command()`` dispatcher, which
persists through legacy ``save_session`` into the **service corpus's**
``saves/`` and nowhere else; the service never opens a working-tree file for
writing, and it never binds anywhere except ``127.0.0.1`` (the bind address
lives here so both the start command and the tests read one constant).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, jsonify, request

import compat_legacy
import collect_envelope
import construction_envelope
import move_envelope
import placement_envelope
import purchase_envelope
import sell_envelope
import store_envelope
import upgrade_envelope

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
ERROR_NO_UPGRADE_PATH = "no_upgrade_path"
ERROR_MISSING_ACTION = "missing_action"
ERROR_INVALID_ACTION = "invalid_action"
ERROR_NO_BUILD_TIME = "no_build_time"
ERROR_CAPPED_COLLECTION = "capped_collection"
ERROR_UNKNOWN_COLLECT_TYPE = "unknown_collect_type"
ERROR_NO_INCOME = "no_income"
ERROR_TOO_EARLY = "too_early"
ERROR_CONSTRUCTION_IN_PROGRESS = "construction_in_progress"
ERROR_INVALID_REASON = "invalid_reason"
ERROR_INVALID_COORDINATES = "invalid_coordinates"
ERROR_INVALID_ORIENTATION = "invalid_orientation"
ERROR_INVALID_DURATION = "invalid_duration"
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

    @app.post("/v0/upgrade")
    def v0_upgrade() -> Tuple[Dict[str, Any], int]:
        """Execute one upgrade intent through the unchanged legacy path.

        An upgrade is one legacy batch with **two** commands in a forced
        order — a ``sell`` with the committed ``UPGR`` reason followed by a
        ``buy`` of the target tier reusing the row's own key and cell
        (design D1).  Validation is structural fail-closed (design D3/D7): a
        JSON object body, a resolvable save, an integer item index that names
        a row in the corpus save, and a placement whose item has a resolvable
        next tier in the committed configuration.  Whether the building is
        upgradeable *today* is the client's job — legacy performs no
        validation of any kind — and the legacy client's level gate, daily
        limit, and space check are deliberately not implemented (design D6);
        authoritative validation belongs to Server v1 (M13).  The index is
        resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:154-156``) is a silent early return
        that still persists the save: reporting that as a success would claim an
        upgrade that never happened.

        Nothing but the index enters the contract: no target tier, no reason,
        no coordinates, no orientation, no player, no quantity, no price, and
        no resource deltas are accepted from a client — the extra keys are
        ignored.  Because the committed configuration records no upgrade
        price, the derived vector is neutral, so **this endpoint claims no
        upgrade cost of any kind** (design D4).

        After execution the endpoint proves the replacement from the persisted
        save with all three documented facts (design D3) and fails closed with
        ``internal_error`` on any other outcome — including the outcome the
        *reverse* command order produces, which the legacy server itself
        reports as a success.
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
        if not upgrade_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to upgrade is the one the two derived commands replace.
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
        # Copies: the legacy dispatcher deletes this very list from the map
        # and writes a new one in its place, so the response must never alias
        # live state.
        removed_row = list(removed)
        if len(removed_row) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not an eight-field row",
            )
        source_item_id = removed_row[0]
        if not upgrade_envelope.is_strict_int(source_item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to upgrade",
            )
        # The cell, orientation, and player come from the row being replaced:
        # the buy half reuses the very same key and cell so the pair upgrades
        # in place instead of re-keying the building (design D2).
        source_x, source_y = removed_row[1], removed_row[2]
        source_orientation = removed_row[4]
        source_player = removed_row[7]

        # The target tier comes from the committed configuration's
        # ``upgrades_to``, never from the client.  ``None`` means the item has
        # no upgrade path (missing reference, the -1/0 sentinels, or an id the
        # config does not resolve), and answering here — before the dispatcher
        # runs — is exactly what keeps an un-upgradeable building from being
        # reduced to a bare sale (design D3).
        try:
            target_item_id = boot.item_upgrade_to(source_item_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if target_item_id is None:
            return error_response(
                400,
                ERROR_NO_UPGRADE_PATH,
                "item %d has no resolvable next tier in the configuration"
                % source_item_id,
            )

        # Derive the legacy envelope (design D2/D4/D8): the committed reason,
        # the neutral resource vector on both commands, and the buy half's
        # discarded placeholders are the module's, never the client's.
        try:
            envelope_payload = upgrade_envelope.build_envelope(
                item_index=item_index,
                target_item_id=target_item_id,
                x=source_x,
                y=source_y,
                player=source_player,
                orientation=source_orientation,
            )
        except upgrade_envelope.EnvelopeError as failure:
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result —
        # which is precisely why it is NOT taken as proof of an upgrade.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the replacement from the persisted save (design D3).  All three
        # facts are required: the key still exists, its item id is the derived
        # target tier, and its cell is the pre-execution cell.  The reverse
        # command order — which legacy also reports as a success — leaves the
        # key absent and is caught by the first check; reporting either row
        # without proving it would be a fabricated authoritative answer.
        try:
            still_present = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not keep the placement entry at its key",
            )
        try:
            upgraded = boot.map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(upgraded, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist the upgraded placement entry",
            )
        upgraded_row = list(upgraded)
        if len(upgraded_row) != 8 or not upgrade_envelope.is_strict_int(
            upgraded_row[0]
        ):
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist an eight-field upgraded row",
            )
        if upgraded_row[0] != target_item_id:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d holds item %r after execution, not the "
                "derived target tier %r"
                % (item_index, upgraded_row[0], target_item_id),
            )
        if [upgraded_row[1], upgraded_row[2]] != [source_x, source_y]:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d sits at %r after execution, not at the "
                "pre-execution cell %r"
                % (item_index, [upgraded_row[1], upgraded_row[2]], [source_x, source_y]),
            )
        return (
            envelope(
                boot,
                result="success",
                removed=removed_row,
                upgraded=upgraded_row,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/construction")
    def v0_construction() -> Tuple[Dict[str, Any], int]:
        """Execute one construction intent through the unchanged legacy path.

        One call carries **exactly one** of the three legacy construction
        commands, chosen by the closed action vocabulary (design D2): a
        ``"start"`` derives ``activate`` with a duration read from the
        addressed placement's item's committed ``build_time``, a ``"click"``
        derives ``add_click``, and a ``"finish"`` derives
        ``activate_item_click``.  The three commands are three *outcomes* of one
        client-side state machine, not one transaction, so they are never
        composed into a single batch here.

        Validation is structural fail-closed (design D3/D7): a JSON object body,
        a resolvable save, an integer item index that names a row in the corpus
        save, an action inside the closed set, and — for a start only — an item
        whose committed build time resolves to a **positive** integer.  The
        index is resolved here rather than left to legacy, because legacy's
        missing-item path (``command.py:416-419``, ``528-531``, ``539-542``)
        logs an error and returns early while the batch still persists:
        reporting that as a success would claim a state change that never
        happened.  Legacy performs no ownership, state, or gameplay validation
        of any kind: whether a build may start on a row that already carries
        construction state, and whether the counter has reached the item's
        ``clicks_to_build`` (which **no** branch compares), are client-side
        rules exactly as they were Flash's; authoritative validation belongs to
        Server v1 (M13).

        Nothing but the index and the action enters the contract: no duration,
        price, quantity, or resource delta is accepted from a client — the
        extra keys are ignored.  The start duration is therefore derived from
        committed content alone, which is why this line has no derived
        placeholder argument at all.  Because the committed configuration
        records no price for building, the derived vector is neutral, so
        **this endpoint claims no building cost** (design D4).  A non-positive
        duration is refused twice over — ``no_build_time`` when committed
        content cannot supply one, ``invalid_duration`` if the derivation ever
        produced one — because legacy's ``activate`` with a non-positive
        duration **clears the addressed row's whole attribute bag**
        (``command.py:425-427``), destroying the click counter and any
        friend-assist entries; this contract therefore exposes no cancel action
        at all (design D6).

        After execution the endpoint proves the per-action post-condition
        (design D3) and fails closed with ``internal_error`` on any other
        outcome: the row still exists and is a list, and then the action's own
        check — a start carries the derived countdown, a click carries a
        counter of at least one, a completion carries none.  Reporting a
        construction that the persisted save does not show would be a fabricated
        authoritative answer.
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
        if not construction_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        if "action" not in payload:
            return error_response(400, ERROR_MISSING_ACTION, "action is required")
        action = payload["action"]
        if not construction_envelope.is_action(action):
            return error_response(
                400,
                ERROR_INVALID_ACTION,
                "action must be one of %s"
                % ", ".join(sorted(construction_envelope.ACTIONS)),
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op, and the row the
        # client asked to build is the row the three commands mutate in place.
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
            previous = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(previous, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # Copies: the legacy dispatcher mutates this very row **in place** —
        # ``activate`` writes ``item[3]`` and ``item[6]``, and
        # ``add_click`` / ``activate_item_click`` mutate the same attribute-bag
        # dict — so a shallow list copy would still alias the live bag and the
        # "before" row would report the after-state.  The bag and the stored-unit
        # payload are copied too.
        previous_row = list(previous)
        if isinstance(previous_row[6], dict):
            previous_row[6] = dict(previous_row[6])
        if isinstance(previous_row[5], list):
            previous_row[5] = list(previous_row[5])
        if len(previous_row) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not an eight-field row",
            )
        source_item_id = previous_row[0]
        if not construction_envelope.is_strict_int(source_item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to build",
            )

        # The start duration comes from the item's committed ``build_time``,
        # never from the client.  ``None`` means no resolvable positive
        # duration (absent, non-integer, zero, or negative), and answering here
        # — before the dispatcher runs — is what keeps an unbuildable row from
        # ever reaching ``activate``'s attribute-bag-clearing branch
        # (design D3/D6).  Only a start resolves one: a click and a completion
        # carry no duration argument at all.
        duration: Optional[int] = None
        if action == construction_envelope.ACTION_START:
            try:
                duration = boot.item_build_time(source_item_id)
            except compat_legacy.LegacyBootError as failure:
                return _legacy_boot_error(failure)
            if duration is None:
                return error_response(
                    400,
                    ERROR_NO_BUILD_TIME,
                    "item %d has no resolvable positive committed build time"
                    % source_item_id,
                )

        # Derive the legacy envelope (design D2/D4): the command, every one of
        # its arguments, and the neutral resource vector are the module's, never
        # the client's.
        try:
            if action == construction_envelope.ACTION_START:
                assert duration is not None
                envelope_payload = construction_envelope.build_envelope_start(
                    item_index=item_index, duration=duration
                )
            elif action == construction_envelope.ACTION_CLICK:
                envelope_payload = construction_envelope.build_envelope_click(
                    item_index=item_index
                )
            else:
                envelope_payload = construction_envelope.build_envelope_finish(
                    item_index=item_index
                )
        except construction_envelope.EnvelopeError as failure:
            if failure.code == "invalid_duration":
                # A server-side derivation failure: committed content
                # produced a duration this contract must never send.
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command()
        # returns without raising, so reaching here IS the legacy result —
        # which is precisely why it is NOT taken as proof of a construction.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the per-action post-condition from the persisted save
        # (design D3).  A construction action must never destroy the row, and
        # each action has an exactly checkable post-condition: a start records
        # the derived countdown, a click raises the counter to at least one,
        # and a completion consumes it.  Any other outcome — including a
        # surviving row the action never touched — is reported, not claimed.
        try:
            still_present = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not keep the placement entry at its key",
            )
        try:
            updated = boot.map_item(user_id, item_index)
            resources = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(updated, list) or len(updated) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist an eight-field placement row",
            )
        updated_row = list(updated)
        attr = updated_row[6]
        if not isinstance(attr, dict):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d carries no attribute bag after execution"
                % item_index,
            )
        if action == construction_envelope.ACTION_START:
            assert duration is not None
            if attr.get("cp") != duration:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "the row at index %d records countdown %r after execution, "
                    "not the derived build time %r"
                    % (item_index, attr.get("cp"), duration),
                )
        elif action == construction_envelope.ACTION_CLICK:
            clicks = attr.get("nc")
            if not construction_envelope.is_strict_int(clicks) or clicks < 1:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "the row at index %d records click counter %r after "
                    "execution, not an integer of at least 1"
                    % (item_index, clicks),
                )
        else:
            if "nc" in attr:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "the row at index %d still carries the click counter %r "
                    "after a completion"
                    % (item_index, attr.get("nc")),
                )
        return (
            envelope(
                boot,
                result="success",
                previous=previous_row,
                row=updated_row,
                action=action,
                resources=resources,
            ),
            200,
        )

    @app.post("/v0/collect")
    def v0_collect() -> Tuple[Dict[str, Any], int]:
        """Execute one collection intent through the unchanged legacy path.

        One call carries **exactly one** legacy ``collect`` command, whose
        single argument is the addressed placement's legacy map index
        (``command.py:136-147``).  That branch writes **only**
        ``item[3] = time_now``; the income travels in the client-sent 8-slot
        resource vector, which ``engine.apply_resources`` applies before the
        branch runs as ``max(current + delta, 0)`` per resource
        (``command.py:40``, ``engine.py:251-271``).  This line is therefore the
        first in the family whose derived vector is **not** neutral: the
        committed configuration describes the income, so the vector is derived
        from it and never from a client.

        Validation is structural fail-closed first, then the content and guard
        refusals, all **before** the dispatcher runs (design D1-D6): a JSON
        object body, a resolvable save, an integer item index that names a row
        in the corpus save, a row that carries no construction state, an item
        with a usable committed income and no cap, a collect type inside the
        committed vocabulary, and an elapsed time that has reached a committed
        ladder rung.  The index is resolved here rather than left to legacy
        because legacy's missing-item path (``command.py:139-142``) logs an
        error and returns early while the batch still persists: reporting that
        as a success would claim a state change that never happened.

        The construction-state refusal is load-bearing rather than defensive.
        ``item[3]`` is *both* a construction start instant (written by
        ``activate``) and a last-collection instant (written by ``collect``),
        and an executed-legacy probe showed ``activate(11, 3600)`` then
        ``collect(11)`` leaving ``[22, 58, 48, <collect instant>, 0, [],
        {"cp": 3600}, 1]``: the build's start instant overwritten while the
        countdown survived, silently restarting an active build's timer, with
        the legacy server answering ``{"result":"success"}``.  The delivered
        construction line reads that same field as a build's start instant, so
        this endpoint refuses a row carrying ``cp`` or ``nc`` **before**
        executing and leaves the corpus byte-identical (design D5).

        The remaining four refusals are derived-provisional and refuse rather
        than guess: a non-zero committed ``max_collects`` is never interpreted
        (only ``0`` is implemented), a ``collect_type`` outside the committed
        five is never coerced into an assumed resource, a committed amount of
        ``0`` (727 of 778 stored items) is not an income, and an elapsed time
        that reached no committed rung (``COLLECT_MINUTES[0] = 5``) must not
        have a payout invented for it.  No legacy branch reads any of the
        content behind these rules, so every one of them is marked
        derived-provisional wherever it is recorded; authoritative validation
        belongs to Server v1 (M13).

        Nothing but the save id and the index enters the contract: no amount,
        resource, tier, time, price, or resource delta is accepted from a
        client — the extra keys are ignored, so no client value can influence
        the payout.  Legacy performs no ownership, state, or gameplay
        validation of any kind, so the endpoint's own validation is structural
        fail-closed only.

        After execution the endpoint proves the post-state in **two** ways
        (design D8) and fails closed with ``internal_error`` on any other
        outcome: the row still exists, is an eight-field list, and its recorded
        collection instant moved **strictly forward**; **and** every stored
        resource changed by **exactly** the derived delta.  The value-level
        check is what turns a reduced or diverging payout — including one a
        clamp would have shortened — into a reported failure instead of a
        trusted success, and the pre-execution ``resources`` are read before
        dispatch so the comparison starts from the state the batch actually saw.
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
        if not collect_envelope.is_strict_int(item_index):
            return error_response(
                400, ERROR_INVALID_ITEM_INDEX, "item_index must be an integer"
            )

        # Resolve the index against the corpus before deriving, and read the
        # eight-field row while it is still there: an index that names no row
        # must fail closed, never reach legacy's silent no-op.
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
            previous = boot.map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(previous, list):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not a row this service can report",
            )
        # Copies: the legacy dispatcher mutates this very row **in place** —
        # ``collect`` writes ``item[3]`` — so a shallow list copy would still
        # alias the live list and the "before" row would report the
        # after-state.  The **length is checked before any field is indexed**,
        # so a row that is not an eight-field entry is reported rather than
        # raising an IndexError out of the route.
        if len(previous) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement is not an eight-field row",
            )
        previous_row = list(previous)
        if isinstance(previous_row[6], dict):
            previous_row[6] = dict(previous_row[6])
        if isinstance(previous_row[5], list):
            previous_row[5] = list(previous_row[5])
        source_item_id = previous_row[0]
        if not collect_envelope.is_strict_int(source_item_id):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer item id to collect",
            )
        collection_instant = previous_row[3]
        if not collect_envelope.is_strict_int(collection_instant):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no integer collection instant",
            )

        # Design D5: refuse a row carrying construction state before anything
        # else can be derived.  A countdown (``cp``) or a build-click counter
        # (``nc``) means ``item[3]`` is a construction start instant, and
        # executing ``collect`` here would overwrite it while the countdown
        # survived — silently restarting an active build's timer, which the
        # legacy server nonetheless reports as a success.
        attr = previous_row[6]
        if isinstance(attr, dict):
            for key in ("cp", "nc"):
                if key in attr:
                    return error_response(
                        409,
                        ERROR_CONSTRUCTION_IN_PROGRESS,
                        "the placement at index %d is under construction "
                        "(attr['%s'] = %r); collecting it would overwrite the "
                        "build's start instant" % (item_index, key, attr[key]),
                    )
        elif attr not in ({}, None):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the addressed placement carries no readable attribute bag",
            )

        # The pre-execution resources are read **before** dispatch so the
        # value-level post-execution proof compares against the state the batch
        # actually started from (design D8).
        try:
            resources_before = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # The four income fields come from the item's committed content, never
        # from a client.  ``None`` means the committed content cannot describe
        # them, and each of the three refusals answers before the dispatcher
        # runs (design D4/D6).
        try:
            amount = boot.item_collect_amount(source_item_id)
            resource_type = boot.item_collect_type(source_item_id)
            experience = boot.item_collect_xp(source_item_id)
            cap = boot.item_max_collects(source_item_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if amount is None or amount <= 0:
            return error_response(
                409,
                ERROR_NO_INCOME,
                "item %d records no committed collection income" % source_item_id,
            )
        if cap is None or cap != 0:
            return error_response(
                409,
                ERROR_CAPPED_COLLECTION,
                "item %d records a committed collection cap of %r, and this "
                "service implements only the uncapped 0" % (source_item_id, cap),
            )
        if resource_type is None or (
            isinstance(resource_type, str)
            and resource_type not in collect_envelope.COLLECT_RESOURCE_SLOTS
        ):
            return error_response(
                409,
                ERROR_UNKNOWN_COLLECT_TYPE,
                "item %d records collect_type %r, which is not one of %s"
                % (
                    source_item_id,
                    resource_type,
                    sorted(collect_envelope.COLLECT_RESOURCE_SLOTS),
                ),
            )

        # The elapsed time is measured against this service's own clock, never
        # a client value, and never extrapolated past the top rung (design D1).
        reference_time = boot.server_time()
        ladder = boot.collect_ladder()
        if ladder is None:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the committed collection ladder does not resolve",
            )
        try:
            elapsed = reference_time - collection_instant
            tier = collect_envelope.tier_for(elapsed, ladder)
        except collect_envelope.EnvelopeError as failure:
            return error_response(500, ERROR_INTERNAL, failure.code)
        # Design D3: below the first committed rung no amount is invented.
        if tier is None:
            first_rung_seconds = collect_envelope.threshold_seconds_for(0, ladder)
            return error_response(
                409,
                ERROR_TOO_EARLY,
                "the placement at index %d has been collecting for %d seconds, "
                "which reaches no committed ladder rung (the first waits %d "
                "seconds, committed as %d minutes)"
                % (item_index, elapsed, first_rung_seconds, ladder[0][0]),
            )

        # Derive the legacy envelope (design D1/D2/D6): the command, its single
        # argument, and the content-derived payout are the module's, never the
        # client's.
        try:
            payout = collect_envelope.payout_for(
                amount=amount,
                resource_type=resource_type,
                experience=experience,
                tier=tier,
                ladder=ladder,
            )
            envelope_payload = collect_envelope.build_envelope(
                item_index=item_index, vector=payout
            )
        except collect_envelope.EnvelopeError as failure:
            if failure.code == "unknown_collect_type":
                return error_response(409, failure.code, str(failure))
            if failure.code == "invalid_vector":
                # A server-side derivation failure: the committed content
                # produced a vector this contract must never send.
                return error_response(500, ERROR_INTERNAL, failure.code)
            return error_response(400, failure.code, str(failure))
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)

        # Execute the unchanged legacy command dispatcher in-process.  It
        # persists via legacy save_session into this corpus only; the legacy
        # HTTP route returns {"result": "success"} whenever command() returns
        # without raising, so reaching here IS the legacy result — which is
        # precisely why it is NOT taken as proof that the payout landed.
        try:
            boot.execute_commands(user_id, envelope_payload)
        except Exception as failure:  # legacy raised after validation passed
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy command execution failed: %s" % type(failure).__name__,
            )

        # Prove the post-state (design D8).  A collection must never destroy a
        # row and must re-stamp its collection instant **forward**; the
        # reported value is legacy's own wall clock, so the comparison is
        # structural and never by value.
        try:
            still_present = boot.has_map_item(user_id, item_index)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not still_present:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not keep the placement entry at its key",
            )
        try:
            updated = boot.map_item(user_id, item_index)
            resources_after = boot.resources(user_id)
        except compat_legacy.LegacyBootError as failure:
            return _legacy_boot_error(failure)
        if not isinstance(updated, list) or len(updated) != 8:
            return error_response(
                500,
                ERROR_INTERNAL,
                "legacy execution did not persist an eight-field placement row",
            )
        updated_row = list(updated)
        new_instant = updated_row[3]
        if not collect_envelope.is_strict_int(new_instant):
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d records a non-integer collection instant "
                "%r after execution" % (item_index, new_instant),
            )
        if new_instant <= collection_instant:
            return error_response(
                500,
                ERROR_INTERNAL,
                "the row at index %d records collection instant %r after "
                "execution, which does not move strictly forward from %r"
                % (item_index, new_instant, collection_instant),
            )
        # The value-level half of the proof: every stored resource must have
        # moved by **exactly** the derived delta.  A clamp that reduced a
        # payout, a partial application, or any other divergence is reported
        # here rather than returned as a success.
        payout_by_name = {
            "xp": payout[collect_envelope.EXPERIENCE_SLOT],
            "gold": payout[2],
            "wood": payout[3],
            "oil": payout[4],
            "steel": payout[5],
            "cash": payout[6],
            "mana": payout[7],
        }
        for name in sorted(payout_by_name):
            expected = max(resources_before[name] + payout_by_name[name], 0)
            if resources_after[name] != expected:
                return error_response(
                    500,
                    ERROR_INTERNAL,
                    "resource %s is %r after execution, not the derived %r "
                    "(it was %r, the derived delta is %r)"
                    % (
                        name,
                        resources_after[name],
                        expected,
                        resources_before[name],
                        payout_by_name[name],
                    ),
                )
        return (
            envelope(
                boot,
                result="success",
                previous=previous_row,
                row=updated_row,
                payout=payout,
                tier=tier,
                reference_time=reference_time,
                resources=resources_after,
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
