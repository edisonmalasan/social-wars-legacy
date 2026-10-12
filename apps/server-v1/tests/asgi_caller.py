#!/usr/bin/env python3
"""An in-process ASGI caller, so the transport is tested without a new dependency.

``fastapi.testclient.TestClient`` needs ``httpx``, which design decision D4 does
not add -- and that is the right call: ``httpx`` would be the **only**
test-only dependency in a runtime manifest that otherwise pins what the service
needs, and the alternative was checked rather than assumed.

What is checked here, by measurement:

* ``fastapi`` 0.128.8 imports and builds an app without ``httpx`` installed;
* ``starlette.testclient`` raises ``ModuleNotFoundError: httpx`` and refuses to
  work, so the first version of ``test_app.py`` could not run at all.  The
  import failure was an ``ERROR`` on ``setUpClass``, not a skip -- the
  ``try``/``except ImportError`` around it did not catch
  ``RuntimeError``, which is what Starlette raises.  Both facts are recorded
  because "the suite skips" and "the suite errors" are different outcomes and
  only one of them was true.

So this module speaks the ASGI protocol directly: it builds the scope, feeds
the request body through ``receive``, and collects what the app sends.  That is
the *same* application object, the same routing, the same middleware stack and
the same exception handling a real request goes through -- only the socket is
missing.

**What this does not do:** it does not exercise uvicorn's HTTP parsing, so a
request this caller could not encode is not a request that would fail in
production.  ``test_live_server.py`` binds a real port and closes that gap; this
file is deliberately not it.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple


class AsgiResponse:
    """What an ASGI app sent back: status, headers, and body bytes."""

    def __init__(self, status: int, headers: List[Tuple[bytes, bytes]], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self.body = body

    @property
    def content(self) -> bytes:
        return self.body

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def header(self, name: str) -> Optional[str]:
        wanted = name.lower().encode("ascii")
        for key, value in self.headers:
            if key.lower() == wanted:
                return value.decode("ascii")
        return None

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return "<AsgiResponse %d %r>" % (self.status, self.body[:120])


async def call_asgi(
    app: Any,
    method: str,
    path: str,
    body: bytes = b"",
    content_type: str = "application/json",
    query_string: bytes = b"",
) -> AsgiResponse:
    """Drive ``app`` through one request/response cycle, in-process.

    Awaited by the caller's ``asyncio`` run; the returned value is the
    collected response.  No socket is opened and no port is bound.
    """
    scope: Dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "root_path": "",
        "headers": [
            (b"host", b"127.0.0.1"),
            (b"content-type", content_type.encode("ascii")),
            (b"content-length", str(len(body)).encode("ascii")),
        ],
        "client": ("127.0.0.1", 0),
        "server": ("127.0.0.1", 0),
    }

    sent = False

    async def receive() -> Dict[str, Any]:
        nonlocal sent
        if sent:
            # ASGI requires ``receive`` to keep answering after the body is
            # consumed; an app that awaits it again must see disconnect.
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    status = 500
    headers: List[Tuple[bytes, bytes]] = []
    chunks: List[bytes] = []

    async def send(message: Dict[str, Any]) -> None:
        nonlocal status, headers
        if message["type"] == "http.response.start":
            status = int(message["status"])
            headers = list(message.get("headers") or [])
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    return AsgiResponse(status, headers, b"".join(chunks))


__all__ = ["AsgiResponse", "call_asgi"]