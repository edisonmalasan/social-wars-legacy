#!/usr/bin/env python3
"""Offline parity tests: Compatibility API v0 vs the captured legacy fixtures
(OpenSpec task 2.4).

Everything here runs with **no server and no network**: responses come from
Flask's in-process test client, the ``offline`` guard fails the run if any
socket tries to connect, and ``test_no_server_is_running`` asserts that neither
the legacy port (5055) nor the Compatibility API port (5056) is listening.

Comparison rules come from ``tests/fixtures/godot-compatibility-boot/field-stability.json``:

* ``get_game_config`` — every leaf except ``darts_items[*].start_date`` must be
  byte-for-byte equal as parsed JSON; the pruned dates must match the legacy
  ``%Y-%m-%d %H:%M:%S`` layout on both sides.
* ``get_player_info`` — every leaf except ``timestamp`` and
  ``playerInfo.last_logged_in`` must be equal, with neighbors compared as a
  pid-keyed mapping (legacy array order follows ``os.listdir()``); the pruned
  timestamps must be positive and equal within each response.
* ``/v0/session`` — game version and saves against the save list parsed out of
  the executed login page.
"""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path
from typing import Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""

LEGACY_PORT = 5055
DATE_LAYOUT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def field_to_pattern(field: str) -> str:
    """Translate a field-stability field name into its leaf-path pattern."""
    parts = []
    for token in field.split("."):
        parts.append(token[:-3] + r"/\d+" if token.endswith("[*]") else token)
    return "^/" + "/".join(parts) + "$"


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID
    ORIGINAL_CWD = os.getcwd()
    CORPUS = harness.build_test_corpus()  # untouched fresh-player seed
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    CLIENT = compat_service.create_app(BOOT).test_client()


def tearDownModule() -> None:
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def _bootstrap() -> Dict[str, object]:
    with harness.offline():
        response = CLIENT.post("/v0/bootstrap", json={"user_id": PID})
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert isinstance(payload, dict)
    return payload


class OfflineExecutionTests(unittest.TestCase):
    """The suite must not depend on any running process."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(
            harness.port_is_free("127.0.0.1", LEGACY_PORT),
            "the legacy server is running; parity must not need it",
        )
        self.assertTrue(
            harness.port_is_free(compat_service.HOST, compat_service.DEFAULT_PORT),
            "a Compatibility API is running; parity must not need it",
        )

    def test_every_call_runs_under_the_socket_guard(self) -> None:
        with harness.offline():
            self.assertEqual(CLIENT.get("/v0/session").status_code, 200)


class ConfigParityTests(unittest.TestCase):
    def test_config_equals_captured_legacy_response(self) -> None:
        fixture = json.loads(
            harness.load_step("get_game_config")["body"].decode("utf-8")  # type: ignore[union-attr]
        )
        payload = _bootstrap()
        compat_config = payload["config"]

        pruned_fixture, fixture_dates = harness.prune_paths(fixture, harness.CONFIG_PRUNES)
        pruned_compat, compat_dates = harness.prune_paths(compat_config, harness.CONFIG_PRUNES)

        self.assertEqual(harness.diff_documents(pruned_fixture, pruned_compat), [])

        # Normalization: format-only, never value equality, and never a hole.
        self.assertEqual(
            sorted(path for path, _ in fixture_dates),
            sorted(path for path, _ in compat_dates),
        )
        self.assertEqual(len(fixture_dates), len(fixture["darts_items"]))
        self.assertEqual(len(compat_dates), len(compat_config["darts_items"]))
        for path, value in fixture_dates + compat_dates:
            with self.subTest(path=path):
                self.assertRegex(str(value), DATE_LAYOUT)


class PlayerInfoParityTests(unittest.TestCase):
    def test_player_info_equals_captured_legacy_response(self) -> None:
        fixture = json.loads(
            harness.load_step("get_player_info")["body"].decode("utf-8")  # type: ignore[union-attr]
        )
        payload = _bootstrap()
        compat_player_info = payload["player_info"]

        # Neighbors: pid-keyed mapping (legacy array order is environment-bound).
        fixture_neighbors = harness.by_pid(fixture["neighbors"])
        compat_neighbors = harness.by_pid(compat_player_info["neighbors"])
        self.assertEqual(
            sorted(fixture_neighbors), sorted(compat_neighbors)
        )
        self.assertGreaterEqual(len(fixture_neighbors), 1)

        fixture = harness.sort_neighbors(fixture)
        compat_player_info = harness.sort_neighbors(compat_player_info)
        pruned_fixture, fixture_stamps = harness.prune_paths(
            fixture, harness.PLAYER_PRUNES
        )
        pruned_compat, compat_stamps = harness.prune_paths(
            compat_player_info, harness.PLAYER_PRUNES
        )
        self.assertEqual(harness.diff_documents(pruned_fixture, pruned_compat), [])

        # Normalization: one positive ts_now per response, both fields equal.
        self.assertEqual(
            sorted(path for path, _ in fixture_stamps),
            ["/playerInfo/last_logged_in", "/timestamp"],
        )
        self.assertEqual(
            sorted(path for path, _ in compat_stamps),
            ["/playerInfo/last_logged_in", "/timestamp"],
        )
        for values in (dict(fixture_stamps), dict(compat_stamps)):
            with self.subTest(side=values):
                self.assertIsInstance(values["/timestamp"], int)
                self.assertGreater(values["/timestamp"], 0)
                self.assertEqual(
                    values["/playerInfo/last_logged_in"], values["/timestamp"]
                )

    def test_neighbors_order_is_not_part_of_the_comparison(self) -> None:
        fixture = json.loads(
            harness.load_step("get_player_info")["body"].decode("utf-8")  # type: ignore[union-attr]
        )
        reversed_neighbors = list(reversed(fixture["neighbors"]))
        self.assertEqual(
            harness.by_pid(reversed_neighbors), harness.by_pid(fixture["neighbors"])
        )


class SessionParityTests(unittest.TestCase):
    def test_session_equals_login_page_save_list(self) -> None:
        save_list = harness.load_step("login_page")["save_list"]  # type: ignore[index]
        with harness.offline():
            response = CLIENT.get("/v0/session")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertIs(payload["ok"], True)
        self.assertEqual(payload["game_version"], save_list["game_version"])
        self.assertEqual(payload["saves"], save_list["saves"])
        for entry in payload["saves"]:
            self.assertEqual(sorted(entry.keys()), ["id", "level", "name", "xp"])

    def test_session_and_bootstrap_agree_on_the_save_list(self) -> None:
        with harness.offline():
            session_payload = CLIENT.get("/v0/session").get_json()
        self.assertEqual(session_payload["saves"], _bootstrap()["saves"])


class FieldStabilityContractTests(unittest.TestCase):
    """The record, the fixtures, and the prune lists must not drift apart."""

    def setUp(self) -> None:
        self.record = harness.load_field_stability()

    def test_prune_patterns_are_exactly_the_recorded_fields(self) -> None:
        targets = self.record["parity_targets"]
        config_fields = [
            entry["field"]
            for entry in targets["get_game_config"]["time_dependent"]
        ]
        player_fields = [
            entry["field"] for entry in targets["get_player_info"]["time_dependent"]
        ]
        environment_fields = [
            entry["field"]
            for entry in targets["get_player_info"]["environment_dependent"]
        ]
        self.assertEqual(config_fields, ["darts_items[*].start_date"])
        self.assertEqual(player_fields, ["timestamp", "playerInfo.last_logged_in"])
        self.assertEqual(environment_fields, ["neighbors"])

        self.assertEqual(
            [pattern.pattern for pattern in harness.CONFIG_PRUNES],
            [field_to_pattern(field) for field in config_fields],
        )
        self.assertEqual(
            [pattern.pattern for pattern in harness.PLAYER_PRUNES],
            [field_to_pattern(field) for field in player_fields],
        )

    def test_recorded_observations_match_the_committed_fixtures(self) -> None:
        observed = self.record["derivation"]["observed_differences"]
        self.assertEqual(observed["get_game_config"]["differing_path_count"], 0)
        player_paths = sorted(
            entry["path"] for entry in observed["get_player_info"]["differing_paths"]
        )
        self.assertEqual(
            player_paths, ["/playerInfo/last_logged_in", "/timestamp"]
        )
        self.assertIs(observed["login_page"]["parsed_equal"], True)
        self.assertIs(observed["play_page"]["equal_after_mask"], True)
        self.assertIs(observed["login_post"]["status_equal"], True)

    def test_fixture_steps_are_all_classified(self) -> None:
        """Two of the five captured steps are documented non-parity targets."""
        non_parity = self.record["non_parity_targets"]
        self.assertEqual(
            sorted(non_parity),
            [
                "before_after_save_records",
                "login_post",
                "play_page",
                "response_meta_headers",
            ],
        )
        self.assertIn("login_post", non_parity)
        self.assertIn("play_page", non_parity)


if __name__ == "__main__":
    unittest.main()
