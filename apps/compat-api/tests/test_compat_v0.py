#!/usr/bin/env python3
"""Compatibility API v0 behavior tests (OpenSpec tasks 2.1, 2.2, 2.3).

No server is started: every request goes through Flask's in-process test
client, so the suite binds no port and opens no socket (the offline guard in
``compat_test_harness`` fails the run if anything tries to connect).

The corpus used here is a disposable copy whose seeded save differs from
``tests/saves/fresh-player.json`` in exactly two fields —
``maps[0].numTradesDone = 3`` with ``maps[0].timestampLastTrade = 0`` — which
is the smallest input that makes the legacy ``reset_stuff()`` day-boundary
reset observable. That lets the suite prove both halves of task 2.3 at once:
the legacy in-memory boot effects happen, and not one save byte changes.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service

COMPAT_DIR = harness.COMPAT_DIR
REPO_ROOT = harness.REPO_ROOT

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
APP = None
CLIENT = None
PID = ""


def _tweak_for_reset_proof(document: Dict[str, object]) -> None:
    """Make the legacy day-boundary reset observable without touching disk later."""
    maps = document["maps"]  # type: ignore[index]
    first = maps[0]
    first["numTradesDone"] = 3
    first["timestampLastTrade"] = 0


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, APP, CLIENT, PID
    ORIGINAL_CWD = os.getcwd()
    CORPUS = harness.build_test_corpus(mutate=_tweak_for_reset_proof)
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    APP = compat_service.create_app(BOOT)
    CLIENT = APP.test_client()


def tearDownModule() -> None:
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def _error_body(response) -> Dict[str, object]:
    payload = response.get_json()
    assert isinstance(payload, dict), "error body is not a JSON object: %r" % (payload,)
    return payload


class ServiceSurfaceTests(unittest.TestCase):
    """Task 2.1: service skeleton, loopback contract, documented start command."""

    def test_loopback_and_protocol_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)
        self.assertEqual(compat_service.PROTOCOL, "compat-v0")

    def test_app_is_bound_to_the_initialized_legacy_state(self) -> None:
        self.assertEqual(APP.config["COMPAT_LEGACY_CORPUS"], str(CORPUS))
        self.assertIsNone(APP.static_folder)
        self.assertEqual(BOOT.game_version, "alpha 0.02")  # version.version_name
        self.assertIs(compat_legacy.current(), BOOT)

    def test_documented_start_command_runs(self) -> None:
        """`python -B apps/compat-api/run.py --help` is the documented command."""
        result = subprocess.run(
            [sys.executable, "-B", str(COMPAT_DIR / "run.py"), "--help"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("loopback", result.stdout)
        self.assertIn("--corpus", result.stdout)
        self.assertIn("--keep-corpus", result.stdout)

    def test_legacy_state_is_initialized_like_server_py(self) -> None:
        """server.py order: load_saves, load_static_villages, load_quests."""
        boot = compat_legacy.current()
        self.assertEqual(boot.known_user_ids(), [PID])
        self.assertGreater(len(boot.session_list()), 0)
        # static villages loaded (neighbors come from villages/) and quests too
        players = boot.player_info(PID)
        self.assertGreaterEqual(len(players["neighbors"]), 1)


class SessionEndpointTests(unittest.TestCase):
    """Task 2.2: GET /v0/session."""

    def test_envelope_shape(self) -> None:
        response = CLIENT.get("/v0/session")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("application/json"))
        payload = response.get_json()
        self.assertEqual(
            sorted(payload.keys()),
            ["game_version", "ok", "protocol", "saves", "server_time"],
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertIs(payload["ok"], True)
        self.assertEqual(payload["game_version"], "alpha 0.02")
        self.assertIsInstance(payload["server_time"], int)
        self.assertGreater(payload["server_time"], 0)

    def test_saves_mirror_legacy_save_info(self) -> None:
        seed = harness.load_seed()
        response = CLIENT.get("/v0/session")
        saves = response.get_json()["saves"]
        self.assertEqual(len(saves), 1)
        entry = saves[0]
        self.assertEqual(
            sorted(entry.keys()), ["id", "level", "name", "xp"]
        )
        self.assertEqual(entry["id"], seed["playerInfo"]["pid"])
        self.assertEqual(entry["name"], seed["playerInfo"]["name"])
        self.assertEqual(entry["xp"], seed["maps"][0]["xp"])
        self.assertEqual(entry["level"], seed["maps"][0]["level"])

    def test_server_time_tracks_the_clock(self) -> None:
        import time

        before = int(time.time())
        payload = CLIENT.get("/v0/session").get_json()
        after = int(time.time())
        self.assertLessEqual(before, payload["server_time"])
        self.assertLessEqual(payload["server_time"], after)


class BootstrapEndpointTests(unittest.TestCase):
    """Task 2.2: POST /v0/bootstrap and its structured errors."""

    def _bootstrap(self, user_id: Optional[object] = None, **kwargs: object):
        body = {"user_id": PID if user_id is None else user_id}
        body.update(kwargs)  # type: ignore[arg-type]
        return CLIENT.post("/v0/bootstrap", json=body)

    def test_known_user_returns_both_legacy_payloads(self) -> None:
        response = self._bootstrap()
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            sorted(payload.keys()),
            [
                "config",
                "game_version",
                "ok",
                "player_info",
                "protocol",
                "saves",
                "server_time",
            ],
        )
        self.assertIs(payload["ok"], True)
        self.assertEqual(payload["protocol"], "compat-v0")
        config = payload["config"]
        self.assertIsInstance(config, dict)
        for key in ("items", "goals", "darts_items", "levels"):
            self.assertIn(key, config)
        player_info = payload["player_info"]
        self.assertEqual(
            sorted(player_info.keys()),
            [
                "map",
                "neighbors",
                "playerInfo",
                "privateState",
                "processed_errors",
                "result",
                "timestamp",
            ],
        )
        self.assertEqual(player_info["result"], "ok")
        self.assertEqual(player_info["processed_errors"], 0)
        self.assertEqual(player_info["playerInfo"]["pid"], PID)

    def test_unknown_user_is_404_and_carries_no_payload(self) -> None:
        unknown = "00000000-0000-4000-8000-0000000000ff"
        response = self._bootstrap(unknown)
        self.assertEqual(response.status_code, 404)
        payload = _error_body(response)
        self.assertEqual(sorted(payload.keys()), ["error", "ok", "protocol"])
        self.assertIs(payload["ok"], False)
        self.assertEqual(payload["error"]["code"], "unknown_user_id")
        self.assertIn(unknown, payload["error"]["message"])
        self.assertNotIn("config", payload)
        self.assertNotIn("player_info", payload)

    def test_missing_user_id_is_400(self) -> None:
        cases = [
            {},
            {"user_id": None},
            {"user_id": ""},
            {"user_id": "   "},
        ]
        for body in cases:
            with self.subTest(body=body):
                response = CLIENT.post("/v0/bootstrap", json=body)
                self.assertEqual(response.status_code, 400)
                payload = _error_body(response)
                self.assertEqual(payload["error"]["code"], "missing_user_id")
                self.assertNotIn("config", payload)
                self.assertNotIn("player_info", payload)

    def test_invalid_user_id_is_400(self) -> None:
        for value in (7, ["x"], True, 1.5):
            with self.subTest(value=value):
                response = CLIENT.post("/v0/bootstrap", json={"user_id": value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    _error_body(response)["error"]["code"], "invalid_user_id"
                )

    def test_unusable_body_is_400_invalid_payload(self) -> None:
        cases = [
            {},
            {"data": "not json", "content_type": "text/plain"},
            {"data": "", "content_type": "application/json"},
            {"json": ["not", "an", "object"]},
            {"json": "just a string"},
            {"json": None},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                response = CLIENT.post("/v0/bootstrap", **kwargs)  # type: ignore[arg-type]
                self.assertEqual(response.status_code, 400)
                payload = _error_body(response)
                self.assertEqual(payload["error"]["code"], "invalid_payload")
                self.assertNotIn("config", payload)
                self.assertNotIn("player_info", payload)

    def test_every_error_body_is_structured(self) -> None:
        responses = [
            self._bootstrap("nope"),
            CLIENT.post("/v0/bootstrap", json={}),
            CLIENT.get("/v0/bootstrap"),
            CLIENT.post("/v0/session"),
            CLIENT.get("/v0/definitely-not-here"),
        ]
        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertGreaterEqual(response.status_code, 400)
                self.assertTrue(
                    response.content_type.startswith("application/json"),
                    response.content_type,
                )
                payload = _error_body(response)
                self.assertEqual(sorted(payload.keys()), ["error", "ok", "protocol"])
                self.assertIs(payload["ok"], False)
                self.assertEqual(payload["protocol"], "compat-v0")
                self.assertEqual(
                    sorted(payload["error"].keys()), ["code", "message"]
                )
                self.assertIsInstance(payload["error"]["code"], str)
                self.assertIsInstance(payload["error"]["message"], str)

    def test_wrong_method_is_405_json(self) -> None:
        for method, path in ((CLIENT.get, "/v0/bootstrap"), (CLIENT.post, "/v0/session")):
            with self.subTest(path=path):
                response = method(path)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(
                    _error_body(response)["error"]["code"], "method_not_allowed"
                )

    def test_unknown_path_is_404_json(self) -> None:
        response = CLIENT.get("/v0/unknown")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(_error_body(response)["error"]["code"], "not_found")

    def test_unhandled_failure_is_500_json(self) -> None:
        def boom() -> object:
            raise RuntimeError("intentional test failure")

        # A throwaway app keeps the shared client's route table untouched.
        app = compat_service.create_app(BOOT)
        app.add_url_rule("/v0/__boom", endpoint="boom", view_func=boom)
        response = app.test_client().get("/v0/__boom")
        self.assertEqual(response.status_code, 500)
        payload = _error_body(response)
        self.assertEqual(payload["error"]["code"], "internal_error")


class NoPersistenceTests(unittest.TestCase):
    """Task 2.3: bytes never move, legacy boot effects still happen."""

    def test_save_bytes_identical_after_session_and_bootstrap(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.assertGreaterEqual(len(before), 1)
        self.assertEqual(CLIENT.get("/v0/session").status_code, 200)
        for _ in range(2):
            self.assertEqual(
                CLIENT.post("/v0/bootstrap", json={"user_id": PID}).status_code, 200
            )
        after = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(before, after)

    def test_legacy_boot_effects_run_without_writing(self) -> None:
        disk_before = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(disk_before["maps"][0]["numTradesDone"], 3)
        self.assertEqual(disk_before["playerInfo"]["last_logged_in"], 0)

        payload = CLIENT.post("/v0/bootstrap", json={"user_id": PID}).get_json()
        player_info = payload["player_info"]

        # reset_stuff(): the day-boundary reset ran in memory exactly as legacy
        self.assertEqual(player_info["map"]["numTradesDone"], 0)
        # get_player_info(): one ts_now assigned to both fields
        self.assertIsInstance(player_info["timestamp"], int)
        self.assertGreater(player_info["timestamp"], 0)
        self.assertEqual(
            player_info["playerInfo"]["last_logged_in"], player_info["timestamp"]
        )

        disk_after = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(disk_after["maps"][0]["numTradesDone"], 3)
        self.assertEqual(disk_after["playerInfo"]["last_logged_in"], 0)
        self.assertEqual(disk_before, disk_after)

    def test_legacy_save_session_is_never_called(self) -> None:
        import sessions as legacy_sessions

        original = legacy_sessions.save_session
        calls: List[str] = []
        legacy_sessions.save_session = lambda user_id: calls.append(str(user_id))
        try:
            self.assertEqual(CLIENT.get("/v0/session").status_code, 200)
            self.assertEqual(
                CLIENT.post("/v0/bootstrap", json={"user_id": PID}).status_code, 200
            )
        finally:
            legacy_sessions.save_session = original
        self.assertEqual(calls, [])

    def test_compat_sources_have_no_persistence_path(self) -> None:
        """AST check: the adapter and the service never name save_session."""
        for name in ("compat_service.py", "compat_legacy.py"):
            with self.subTest(module=name):
                tree = ast.parse((COMPAT_DIR / name).read_text(encoding="utf-8"))
                named = [
                    node.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Name) and node.id == "save_session"
                ]
                attributed = [
                    node.attr
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Attribute) and node.attr == "save_session"
                ]
                self.assertEqual(named, [])
                self.assertEqual(attributed, [])

        service_tree = ast.parse(
            (COMPAT_DIR / "compat_service.py").read_text(encoding="utf-8")
        )
        opens = [node for node in ast.walk(service_tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "open"]
        self.assertEqual(opens, [], "the service must not open files")

        legacy_tree = ast.parse(
            (COMPAT_DIR / "compat_legacy.py").read_text(encoding="utf-8")
        )
        for node in ast.walk(legacy_tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name == "build_corpus":
                continue
            writes = [
                call
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "open"
                and any(
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and any(flag in arg.value for flag in "wax+")
                    for arg in call.args[1:]
                )
            ]
            self.assertEqual(
                writes, [], "%s must not write files" % node.name
            )

    def test_working_tree_has_no_saves_directory(self) -> None:
        """The disposable corpus is the only place saves ever exist."""
        self.assertFalse((REPO_ROOT / "saves").exists())


if __name__ == "__main__":
    unittest.main()
