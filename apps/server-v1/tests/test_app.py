#!/usr/bin/env python3
"""The HTTP surface: one route, no arithmetic, and the two bodies distinguishable.

Design D2's claim is about the **transport**, and a transport claim tested only
by reading the source is not tested.  So this file does three things: it drives
the real ASGI application object in-process, it asserts the response shapes the
spec requires, and it re-asserts the structural property by walking the AST of
``server_v1_app.py`` -- the same file
``test_boundary_invariant.TransportNamesNoReasonTests`` walks, kept here as well
because *this* file's conclusions depend on it and a guard's sensitivity does
not transfer between modules by assertion alone.

The injected clock is what makes the fixture comparison deterministic, and it is
injected through ``create_app`` rather than through a request field: a server's
clock is not something a client may set.

**No socket, no new dependency, no external network.**  The caller is
``asgi_caller``, which speaks ASGI directly, because
``fastapi.testclient.TestClient`` requires ``httpx`` and design D4 does not add
it.  ``test_live_server.py`` binds a real port and closes the gap this file
leaves; this file is deliberately not it, because a test that binds can fail for
reasons unrelated to what it is testing -- one of the four recorded flaky
surfaces this repository has around ports.
"""

from __future__ import annotations

import ast
import asyncio
import json
import unittest
from typing import Any, Dict, List

import harness
from asgi_caller import call_asgi
from harness import (
    REPO_ROOT,
    FilesystemSaveRepository,
    build_corpus,
    load_content,
    remove_corpus,
    seed_player_id,
)
from server_v1_app import (
    COLLECT_PATH,
    MAGIC_PATH,
    ROUTE_PREFIX,
    ROUTES,
    create_app,
)
from server_v1_outcomes import SUCCESS_HTTP_STATUS

FIXTURE_INSTANT = 1790705901
PLAYER_KEY = "player_id"
ROW_KEY = "row"
UNKNOWN_PLAYER = "00000000-0000-4000-8000-0000000000ff"


def transport_source() -> ast.Module:
    return ast.parse(
        (harness.SERVICE_DIR / "server_v1_app.py").read_text(encoding="utf-8"),
        filename="server_v1_app.py",
    )


def non_docstring_strings(tree: ast.Module) -> List[str]:
    """String constants, with docstrings excluded.

    Excluded because a docstring is prose *about* a rule and would satisfy any
    guard that scans for a name -- the recorded defect class this repository has
    now met several times.
    """
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", []) or []
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


class Route:
    """A synchronous facade over the in-process ASGI caller.

    **Why not ``fastapi.testclient``:** it requires ``httpx``, which design D4
    does not add, and the failure mode is worth recording because it was *not* a
    skip.  ``starlette.testclient`` raises ``RuntimeError`` -- not
    ``ImportError`` -- so this file's first version, wrapped in
    ``try: from fastapi.testclient import TestClient / except ImportError``,
    produced two ``ERROR`` entries and zero runs.  A guard that reports "skip"
    when it means "broken" is worse than no guard.

    See ``asgi_caller`` for what this does and does not exercise.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    def post(self, json_body: Any = None, raw: bytes = None) -> Any:
        body = raw if raw is not None else json.dumps(json_body or {}).encode("utf-8")
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(call_asgi(self.app, "POST", COLLECT_PATH, body))
        finally:
            loop.close()


class TransportStructureTests(unittest.TestCase):
    """The structural half, asserted about this file's own subject."""

    def test_the_inventory_is_not_empty(self) -> None:
        """A guard satisfied by an empty scan is the defect class itself.

        The set is exact and is **extended**, never loosened, when a route is
        added: ``POST /v1/magic`` was appended by the third deliver line and the
        assertion stayed an equality, so a fourth route still has to be added
        here deliberately.
        """
        self.assertIsInstance(transport_source(), ast.Module)
        self.assertEqual(
            {"POST /v1/collect", "POST /v1/collection", "POST /v1/magic"},
            set(ROUTES),
        )

    def test_the_route_path_is_the_declared_one(self) -> None:
        """The literal cannot drift from ``ROUTE_PREFIX`` without failing here."""
        self.assertEqual(ROUTE_PREFIX + "/collect", COLLECT_PATH)
        self.assertEqual("/v1/collect", COLLECT_PATH)
        self.assertEqual(ROUTE_PREFIX + "/magic", MAGIC_PATH)
        self.assertEqual("/v1/magic", MAGIC_PATH)

    def test_the_transport_declares_no_arithmetic_operator(self) -> None:
        """No ``+``, ``-``, ``*``, ``/``: the transport may not compute anything.

        ``%`` is excluded when its left operand is a string literal, which is
        interpolation.  This is the check that makes "the route has no
        arithmetic" a mechanical claim rather than a claim about reading.

        **This guard caught correct code, and the code was changed rather than
        the guard relaxed.**  The route decorator originally read
        ``@app.post(ROUTE_PREFIX + "/collect")``, which is a ``BinOp``.  That is
        string concatenation, not arithmetic, so the guard was right about the
        form and wrong about the intent -- but weakening it to "allow ``Add``
        when either operand is a string" is a hole any later expression walks
        through, so the declaration is now a literal and
        ``test_the_route_path_is_the_declared_one`` keeps the two in step.
        """
        tree = transport_source()
        offenders: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Mod):
                    left = node.left
                    if isinstance(left, ast.Constant) and isinstance(left.value, str):
                        continue
                offenders.append(ast.dump(node))
        self.assertEqual([], offenders)

    def test_the_transport_never_writes_a_status_literal_besides_success(self) -> None:
        """A per-route ``409`` is exactly how v0 grew 24 answers to one question.

        The one status the transport may know is the success status, which it
        imports by name from the outcomes module; every refusal status is read
        out of the closed table through the domain value's own property.
        """
        found = {
            literal
            for literal in non_docstring_strings(transport_source())
            if literal in {"400", "404", "409", "422", "500", "503"}
        }
        self.assertEqual(set(), found)

    def test_the_transport_names_no_refusal_code(self) -> None:
        codes = {
            node.attr
            for node in ast.walk(transport_source())
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "RefusalCode"
        }
        self.assertEqual(set(), codes)

    def test_the_route_prefix_is_v1_and_not_v0(self) -> None:
        self.assertEqual("/v1", ROUTE_PREFIX)
        self.assertNotIn("/v0", ROUTE_PREFIX)


class AppBehaviourTests(unittest.TestCase):
    """The route, driven over the real ASGI stack in-process."""

    @classmethod
    def setUpClass(cls) -> None:
        # Read-only for the whole class; no test here writes committed content.
        cls.content = load_content(REPO_ROOT)
        cls.player = seed_player_id()

    def setUp(self) -> None:
        # A fresh corpus **per test**, which is what makes the byte-identity
        # assertions meaningful: a successful collection moves the recorded
        # instant, so a shared corpus would let the first test spend the single
        # unbounded-elapsed collection and would leave a later test comparing
        # against bytes the earlier one wrote.
        self.corpus = build_corpus(mutate=lambda document: None)
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.client = Route(
            create_app(self.content, self.repository, lambda: FIXTURE_INSTANT)
        )
        self.save_path = self.corpus / "saves" / ("%s.save.json" % self.player)

    def _body(self, **extra: Any) -> Dict[str, Any]:
        body: Dict[str, Any] = {PLAYER_KEY: self.player, ROW_KEY: 2}
        body.update(extra)
        return body

    # ------------------------------------------------------------- success ---
    def test_a_valid_intent_succeeds_with_the_derived_payout(self) -> None:
        response = self.client.post(self._body())
        self.assertEqual(SUCCESS_HTTP_STATUS, response.status)
        payload = response.json()
        self.assertEqual("success", payload["result"])
        self.assertEqual("collect", payload["action"])
        self.assertEqual({"xp": 3, "wood": 60}, payload["derived_deltas"])
        self.assertEqual(3, payload["rung"]["index"])
        self.assertEqual(FIXTURE_INSTANT, payload["instant"])
        self.assertEqual("server-v1", payload["protocol"])

    def test_the_response_reports_the_derivation_and_echoes_no_request_figure(self) -> None:
        payload = self.client.post(self._body()).json()
        self.assertIn("derivation_id", payload)
        self.assertIn("rung", payload)
        # The spec requires the response to report the derivation rather than
        # echo anything the client sent.  There were no figures to echo, and the
        # addressing fields are not reflected back either.
        self.assertNotIn(PLAYER_KEY, payload)
        self.assertNotIn(ROW_KEY, payload)

    def test_the_stored_state_after_the_route_matches_the_reported_balances(self) -> None:
        """The response is not a claim; the file has to agree with it."""
        payload = self.client.post(self._body()).json()
        stored = self.repository.read(self.player).resources()
        self.assertEqual(payload["resources_after"], stored)

    # ------------------------------------------------------------ refusals ---
    def test_a_client_supplied_delta_is_refused_with_a_structural_error(self) -> None:
        before = self.save_path.read_bytes()
        for field, value in (
            ("gold", 999999),
            ("wood", 500),
            ("xp", 5000),
            ("resources_changed", [0, 9999, 0, 0, 0, 0, 0, 0]),
            ("hp", 100),
            ("damage", 40),
            ("result", "success"),
        ):
            with self.subTest(field=field):
                response = self.client.post(self._body(**{field: value}))
                self.assertEqual(400, response.status, "%s was not refused" % field)
                self.assertEqual("client_supplied_delta", response.json()["code"])
        after = self.save_path.read_bytes()
        self.assertEqual(before, after, "a refused delta request changed the bytes")

    def test_an_unknown_field_is_refused_rather_than_ignored(self) -> None:
        response = self.client.post(self._body(some_other_field=1))
        self.assertEqual(400, response.status)
        self.assertEqual("unknown_request_field", response.json()["code"])

    def test_a_malformed_body_is_refused_rather_than_crashing(self) -> None:
        for raw in (b"", b"not json", b"[1,2,3]", b'{"player_id": 7, "row": 2}'):
            with self.subTest(raw=raw[:16]):
                response = self.client.post(raw=raw)
                self.assertEqual(400, response.status)
                self.assertEqual("malformed_request", response.json()["code"])

    def test_a_gameplay_refusal_is_a_409_and_distinguishable_from_a_transport_failure(self) -> None:
        response = self.client.post(self._body(row=9999))
        self.assertEqual(409, response.status)
        payload = response.json()
        self.assertEqual("refused", payload["result"])
        self.assertEqual("unaddressable_row", payload["code"])
        # The two surfaces are distinguishable by ``result``, which is the
        # spec's own requirement.
        self.assertNotEqual("success", payload["result"])

    def test_a_refused_gameplay_request_writes_nothing(self) -> None:
        before = self.save_path.read_bytes()
        self.assertEqual(409, self.client.post(self._body(row=9999)).status)
        self.assertEqual(before, self.save_path.read_bytes())

    def test_an_unknown_player_is_a_404_not_a_gameplay_answer(self) -> None:
        response = self.client.post(json_body={PLAYER_KEY: UNKNOWN_PLAYER, ROW_KEY: 2})
        self.assertEqual(404, response.status)
        self.assertEqual("unknown_player", response.json()["code"])

    # ------------------------------------------------------------ envelopes ---
    def test_both_bodies_carry_the_protocol_and_nothing_else_is_added(self) -> None:
        success = self.client.post(self._body()).json()
        refusal = self.client.post(self._body(row=9999)).json()
        for payload in (success, refusal):
            self.assertIn("protocol", payload)
        self.assertEqual("server-v1", success["protocol"])
        self.assertEqual("server-v1", refusal["protocol"])
        # ``code`` names a reason on the refusal and is absent from success, so
        # a client can branch on one field.
        self.assertIn("code", refusal)
        self.assertNotIn("code", success)

    def test_the_response_is_valid_json_over_the_wire(self) -> None:
        raw = self.client.post(self._body()).content
        self.assertIsInstance(json.loads(raw.decode("utf-8")), dict)

    def test_the_response_is_json_content_type(self) -> None:
        content_type = self.client.post(self._body()).header("content-type")
        self.assertIsNotNone(content_type)
        self.assertTrue(content_type.startswith("application/json"))


class ClockInjectionTests(unittest.TestCase):
    """The clock is a constructor argument, never a request field."""

    def test_the_clock_is_not_a_field_of_the_intent_schema(self) -> None:
        from server_v1_intent import INTENT_SCHEMAS

        self.assertEqual(frozenset({"player_id", "row"}), INTENT_SCHEMAS["collect"])
        for forbidden in ("now", "time", "instant", "ts", "clock"):
            self.assertNotIn(forbidden, INTENT_SCHEMAS["collect"])

    def test_two_corpora_and_two_clocks_produce_two_different_transactions(self) -> None:
        """Proves the clock really is what moved the recorded instant.

        Both halves are needed.  A single request would also pass if the
        instant came from anywhere else in the system, because the corpus
        already carries a row that is eligible for collection; comparing two
        requests over two **separate** corpora is what makes the injected
        callable the only thing that differed.
        """
        content = load_content(REPO_ROOT)
        player = seed_player_id()
        instants = []
        for injected in (FIXTURE_INSTANT, FIXTURE_INSTANT + 86400):
            corpus = build_corpus(mutate=lambda document: None)
            self.addCleanup(remove_corpus, corpus)
            repository = FilesystemSaveRepository(corpus)
            client = Route(create_app(content, repository, lambda value=injected: value))
            response = client.post({PLAYER_KEY: player, ROW_KEY: 2})
            self.assertEqual(SUCCESS_HTTP_STATUS, response.status)
            instants.append(response.json()["instant"])
        self.assertEqual([FIXTURE_INSTANT, FIXTURE_INSTANT + 86400], instants)


if __name__ == "__main__":
    unittest.main()
