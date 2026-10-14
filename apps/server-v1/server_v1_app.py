#!/usr/bin/env python3
"""The HTTP surface: five routes, and no arithmetic (design D2).

``create_app`` returns a FastAPI application with exactly five delivered routes,
``POST /v1/collect``, ``POST /v1/collection``, ``POST /v1/combat``,
``POST /v1/magic``, and ``POST /v1/reward``.  Each route's entire job, per
design D2, is:

1. hand the request bytes to :mod:`server_v1_intent`, which turns them into an
   intent or refuses;
2. call the domain service;
3. translate the returned outcome into HTTP.

The route has **no arithmetic, no refusal vocabulary, and no domain value
construction**.  It never adds, scales, clamps, or floors; it never names a
refusal code; it never constructs a :class:`~server_v1_outcomes.Success`, a
:class:`~server_v1_economy.ResourceDerivation`, or a
:class:`~server_v1_refusals.Refusal`.  It reads a status out of the closed
:data:`~server_v1_refusals.REFUSAL_HTTP_STATUS` table through the domain value's
own ``http_status`` property.

Those are three properties the module docstring claims and
``tests/test_boundary_invariant.py`` asserts by walking the AST of this file.
A second place a route could invent a status — a literal ``409`` in a branch —
is therefore not merely discouraged here, it is a test failure, and so is a
second derivation or a success assembled by hand.  Even JSON decoding lives in
the intent module (:func:`server_v1_intent.intent_from_json`) so that the
transport never has to name ``malformed_request``.

The success status is the one thing the transport is allowed to know without
asking: :data:`~server_v1_outcomes.SUCCESS_HTTP_STATUS`, ``200``.

All response bodies come from the domain value's own ``payload()``, with
the protocol name added and nothing else.  A refusal therefore carries the reason
the domain chose, never a per-route rewording, and the client can distinguish the
surfaces by their ``result`` field — the spec's "the client can distinguish it
from a transport failure" scenario.

**All five handler bodies are identical but for three tokens**: the path
constant, the action string, and the domain function.  The magic surface carries
**two** preserved operations and they travel inside the parsed intent rather than
as a route parameter, which is what keeps a single handler total instead of
growing a per-operation branch here.  The reward surface carries **two** as well,
and it adds a third reason the identical-body guard is load-bearing rather than
merely tidy: reward is the first action with **no addressing field**
(:data:`server_v1_intent.NO_ADDRESSING_FIELD_ACTIONS`), so a handler that grew a
per-action branch to read a cursor would be a transport inventing an address the
request never gave.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server_v1_collection import complete_collection
from server_v1_collect import collect
from server_v1_combat import apply_combat
from server_v1_content import CommittedContent
from server_v1_intent import intent_from_json
from server_v1_magic import apply_magic
from server_v1_outcomes import SUCCESS_HTTP_STATUS, Outcome
from server_v1_refusals import Refusal
from server_v1_repository import SaveRepository
from server_v1_reward import advance_reward
from server_v1_settings import PROTOCOL

#: The five delivered routes, named so a test enumerates routes from a
#: declaration rather than from a regex over the source.  One row per route:
#: adding a route adds a row, and ``test_app.py`` asserts this mapping agrees
#: with the paths declared below.
ROUTES: Dict[str, str] = {
    "POST /v1/collect": "collect",
    "POST /v1/collection": "collection",
    "POST /v1/combat": "combat",
    "POST /v1/magic": "magic",
    "POST /v1/reward": "reward",
}

ROUTE_PREFIX = "/v1"

#: The route path as a **literal**, not ``ROUTE_PREFIX + "/collect"``.
#:
#: The concatenation form was the first version of this and had to be removed:
#: it is a ``BinOp`` in the transport, and
#: ``tests/test_app.TransportStructureTests`` asserts the transport declares no
#: arithmetic operator.  Writing the path out costs one repeated literal and
#: buys a guard that is both satisfiable and strict -- the third recorded
#: instance in this repository of a guard that could only be satisfied by
#: deleting correct code.  ``test_the_route_path_is_the_declared_one`` asserts
#: the two agree, so the duplication cannot drift.
COLLECT_PATH = "/v1/collect"

#: The second route this line delivers.  A literal for the same reason
#: :data:`COLLECT_PATH` is: a ``BinOp`` in the transport is a failed invariant,
#: and the concatenation form was the first version of the first one.
#:
#: **The path is ``/v1/collection`` and not ``/v1/complete_collection``**, so it
#: parallels ``/v1/collect`` rather than the legacy branch's command name.  The
#: reason is recorded rather than incidental: a route path is a *client*
#: surface, and naming it after the legacy command would make v1's vocabulary a
#: subset of ``command.py``'s 63 branch names, which is the inheritance the
#: boundary exists to stop.  ``tests/test_app.py`` asserts the literal agrees
#: with ``ROUTE_PREFIX`` so the duplication cannot drift.
COLLECTION_PATH = "/v1/collection"

#: The third route this line delivers, and a literal for the same reason as the
#: other two.  **A third route means the concatenation mistake could have been
#: made a second time**, so the reason is restated rather than cross-referenced:
#: a ``BinOp`` in this module is a failed invariant, and
#: ``tests/test_app.TransportStructureTests`` walks the AST of this file and fails
#: on one.
#:
#: The path is ``/v1/magic`` rather than ``/v1/buy_magic``, for the same reason
#: :data:`COLLECTION_PATH` is not ``/v1/complete_collection``: the route names the
#: **surface**, and the surface carries both preserved operations, so no single
#: legacy branch name would describe it.  ``tests/test_app.py`` asserts the
#: literal agrees with :data:`ROUTE_PREFIX` so the duplication cannot drift.
MAGIC_PATH = "/v1/magic"

#: The fourth route this line delivers, and a literal for the same reason as the
#: other three.
#:
#: The path is ``/v1/combat``, and **not** ``/v1/attack`` and not
#: ``/v1/end_attack``.  Both rejected spellings are worth naming because each
#: would assert something false about what the route can do: ``attack`` names a
#: second action the route does not have (there is one, design D1), and
#: ``end_attack`` inherits the legacy command name -- the inheritance
#: :data:`COLLECTION_PATH` records as the reason a route names the **surface**.
#: ``combat`` is the surface: it is what a client asks about, and the preserved
#: branch's own name for a transaction that destroys rows is not something this
#: route can do, because it destroys nothing.
COMBAT_PATH = "/v1/combat"

#: The fifth route this line delivers, and a literal for the same reason as the
#: other four.
#:
#: The path is ``/v1/reward``, and **not** ``/v1/win_daily_bonus`` and not
#: ``/v1/weekly_reward``.  Both rejected spellings name **one** of the two
#: preserved arms, and the route carries both -- as ``/v1/magic`` carries
#: ``buy_magic`` and ``use_magic`` -- so no single legacy branch name would
#: describe it.  ``reward`` is the surface, for the reason
#: :data:`COLLECTION_PATH` records.
#:
#: **The declaration order here is a pinned property, not an accident.**  The
#: route is declared **last**, after ``MAGIC_PATH``, because a test in
#: ``apps/client-godot/tests/test_reward_v1.gd`` asserts both that this literal
#: is the final ``*_PATH`` declaration in this module and that no delivered v1
#: test reaches forward across it.  The second half is the shape that has bitten
#: this repository twice -- ``apps/compat-api``'s envelope modules slice a route
#: out of its service file between markers, and two suites there cut at
#: ``@app.post("/v0/level_up")``, which reached across every route declared
#: between them -- so a new route landed in a forbidden slot and broke four
#: delivered guards at once.  Declaring last, and asserting it, makes the
#: placement a checked property rather than something a future line discovers.
REWARD_PATH = "/v1/reward"


def create_app(
    content: CommittedContent,
    repository: SaveRepository,
    clock: Callable[[], int],
) -> FastAPI:
    """Build the v1 application over an injected content, store, and clock.

    All three are injected rather than reached for, which is what makes the
    route testable against a disposable corpus with a pinned clock — the
    fixture comparison in ``tests/test_parity_v0_collect.py`` needs the server's
    clock to *be* the recorded capture instant, and a request field is not a
    legitimate way to set it.
    """
    app = FastAPI(title="Social Wars Server v1", version=PROTOCOL)

    @app.post(COLLECT_PATH)
    async def post_collect(request: Request) -> JSONResponse:
        """Adapt one collection intent, call the domain, translate the outcome."""
        body = await request.body()
        parsed = intent_from_json("collect", body)
        if isinstance(parsed, Refusal):
            return JSONResponse(
                status_code=parsed.http_status, content=_envelope(parsed)
            )

        outcome: Outcome = collect(parsed, content, repository, clock())
        if isinstance(outcome, Refusal):
            return JSONResponse(
                status_code=outcome.http_status, content=_envelope(outcome)
            )
        return JSONResponse(status_code=SUCCESS_HTTP_STATUS, content=_envelope(outcome))

    @app.post(COLLECTION_PATH)
    async def post_collection(request: Request) -> JSONResponse:
        body = await request.body()
        parsed = intent_from_json("collection", body)
        if isinstance(parsed, Refusal):
            return JSONResponse(
                status_code=parsed.http_status, content=_envelope(parsed)
            )

        outcome: Outcome = complete_collection(parsed, content, repository, clock())
        if isinstance(outcome, Refusal):
            return JSONResponse(
                status_code=outcome.http_status, content=_envelope(outcome)
            )
        return JSONResponse(status_code=SUCCESS_HTTP_STATUS, content=_envelope(outcome))

    @app.post(COMBAT_PATH)
    async def post_combat(request: Request) -> JSONResponse:
        """Adapt one combat intent, call the domain, translate the outcome.

        Body for body identical to the other three, and for the reason
        :func:`post_magic` records: there is nothing about a combat request the
        transport interprets.  In particular the transport does **not** decide
        whether the request carries a destruction shape -- that recognition
        happens in the intent layer and the refusal is the domain's, so a route
        that grew a ``destruction_request`` branch here would be a transport
        deciding a question about what a transaction would have destroyed.

        The route is a *report*, so its success status is the same
        ``SUCCESS_HTTP_STATUS`` the mutating routes use: the request succeeded
        and the answer is that nothing changed.  A route whose success meant "a
        battle happened" would be the anti-pattern design D1 refuses.
        """
        body = await request.body()
        parsed = intent_from_json("combat", body)
        if isinstance(parsed, Refusal):
            return JSONResponse(
                status_code=parsed.http_status, content=_envelope(parsed)
            )

        outcome: Outcome = apply_combat(parsed, content, repository, clock())
        if isinstance(outcome, Refusal):
            return JSONResponse(
                status_code=outcome.http_status, content=_envelope(outcome)
            )
        return JSONResponse(status_code=SUCCESS_HTTP_STATUS, content=_envelope(outcome))

    @app.post(MAGIC_PATH)
    async def post_magic(request: Request) -> JSONResponse:
        """Adapt one magic intent, call the domain, translate the outcome.

        Deliberately identical to the other handlers, body for body.  The routes
        have nothing to distinguish them: the operation the client
        asked for is **inside the parsed intent**, not a second parameter here,
        so a new route cannot grow a per-route branch without failing the
        structural guard that compares these function bodies
        (``tests/test_app.py::test_every_route_handler_has_the_same_body_shape``,
        which is what makes this claim true rather than asserted).
        """
        body = await request.body()
        parsed = intent_from_json("magic", body)
        if isinstance(parsed, Refusal):
            return JSONResponse(
                status_code=parsed.http_status, content=_envelope(parsed)
            )

        outcome: Outcome = apply_magic(parsed, content, repository, clock())
        if isinstance(outcome, Refusal):
            return JSONResponse(
                status_code=outcome.http_status, content=_envelope(outcome)
            )
        return JSONResponse(status_code=SUCCESS_HTTP_STATUS, content=_envelope(outcome))

    @app.post(REWARD_PATH)
    async def post_reward(request: Request) -> JSONResponse:
        """Adapt one reward intent, call the domain, translate the outcome.

        The fifth identical handler, and the one whose shape the identical-body
        guard most needs to hold: a reward request carries **no addressing
        field** and an **operation**, so the two things a handler is most
        tempted to read -- a row and an action-specific parameter -- are exactly
        the two this surface does not have.  The operation travels inside the
        parsed intent, the cursor is derived by the domain from the recorded
        document, and this handler has nothing to do with either.
        """
        body = await request.body()
        parsed = intent_from_json("reward", body)
        if isinstance(parsed, Refusal):
            return JSONResponse(
                status_code=parsed.http_status, content=_envelope(parsed)
            )

        outcome: Outcome = advance_reward(parsed, content, repository, clock())
        if isinstance(outcome, Refusal):
            return JSONResponse(
                status_code=outcome.http_status, content=_envelope(outcome)
            )
        return JSONResponse(status_code=SUCCESS_HTTP_STATUS, content=_envelope(outcome))

    return app


def _envelope(value: Any) -> Dict[str, Any]:
    """Wrap a domain value for the wire, adding only the protocol name.

    The body is the domain value's own ``payload()``.  Nothing here restates,
    reorders away, or adds a decision: if the two surfaces ever stopped being
    distinguishable, this function would be the place it broke, and
    ``tests/test_app.py`` asserts they are not.
    """
    body = dict(value.payload())
    body["protocol"] = PROTOCOL
    return body


__all__ = [
    "COLLECT_PATH",
    "COMBAT_PATH",
    "COLLECTION_PATH",
    "MAGIC_PATH",
    "REWARD_PATH",
    "ROUTES",
    "ROUTE_PREFIX",
    "create_app",
]
