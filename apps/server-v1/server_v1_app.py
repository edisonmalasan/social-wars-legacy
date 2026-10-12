#!/usr/bin/env python3
"""The HTTP surface: two routes, and no arithmetic (design D2).

``create_app`` returns a FastAPI application with exactly two delivered routes,
``POST /v1/collect`` and ``POST /v1/collection``.  Each route's entire job, per
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

Both response bodies come from the domain value's own ``payload()``, with the
protocol name added and nothing else.  A refusal therefore carries the reason
the domain chose, never a per-route rewording, and the client can distinguish
the two surfaces by their ``result`` field — the spec's "the client can
distinguish it from a transport failure" scenario.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server_v1_collection import complete_collection
from server_v1_collect import collect
from server_v1_content import CommittedContent
from server_v1_intent import intent_from_json
from server_v1_outcomes import SUCCESS_HTTP_STATUS, Outcome
from server_v1_refusals import Refusal
from server_v1_repository import SaveRepository
from server_v1_settings import PROTOCOL

#: The two delivered routes, named so a test enumerates routes from a
#: declaration rather than from a regex over the source.  One row per route:
#: adding a route adds a row, and ``test_app.py`` asserts this mapping agrees
#: with the paths declared below.
ROUTES: Dict[str, str] = {
    "POST /v1/collect": "collect",
    "POST /v1/collection": "collection",
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


__all__ = ["COLLECT_PATH", "COLLECTION_PATH", "ROUTES", "ROUTE_PREFIX", "create_app"]
