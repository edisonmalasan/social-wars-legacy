#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/place`` vs the executed-legacy
placement fixture (OpenSpec task 2.2).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any
socket tries to connect), and ``test_no_server_is_running`` asserts that
neither the legacy port (5055) nor the Compatibility API port (5056) is
listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-placement/`` — one real ``buy`` command
executed by the legacy server in a disposable copy (House I at ``(51,39)``).
The test posts the *intent* recorded in that fixture's request to the
endpoint and compares:

* the response ``result`` against the captured legacy response body;
* the response ``placement`` entry against the captured after-state
  entry field-by-field, except the entry's ``timestamp``;
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable);
* the corpus save after execution against the captured after-state,
  except that same ``timestamp``;
* the shared derivation against the recorded request envelope, exactly
  (the recorded ``ts`` is passed back into the derivation).

Documented time-dependent fields (normalized, never silently dropped):
the placement entry's wall-clock ``timestamp`` on both sides — in the
fixture's ``after.json`` and in the endpoint's corpus save — is replaced
by ``0`` before the state comparison, and the fixture's envelope ``ts``
is asserted to be a positive integer before the envelope comparison.
Everything else must be equal leaf-for-leaf. The parity claim covers
this one recorded transaction against the fresh-player corpus (see the
fixture README's claim limits).
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import placement_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-placement"

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


def load_fixture() -> Dict[str, Any]:
    base = FIXTURES / "steps" / "command_buy"
    return {
        "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
        "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
        "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
        "meta": json.loads(
            (base / "response.meta.json").read_text(encoding="utf-8")
        ),
        "body": (base / "response.body").read_bytes(),
    }


def recorded_envelope() -> Dict[str, Any]:
    """The executed legacy envelope, parsed from the recorded ``data`` field.

    Parsing goes through :func:`placement_envelope.parse_data_field`, which
    also verifies the recorded 64-hex digest against the payload.
    """
    return placement_envelope.parse_data_field(
        FIXTURE["request"]["form"]["data"]
    )


def recorded_intent() -> Dict[str, Any]:
    envelope = recorded_envelope()
    command = envelope["commands"][0]
    args = command[2]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "item_id": args[1],
        "x": args[2],
        "y": args[3],
        "orientation": args[5],
        "args": args,
        "resources_changed": command[3],
        "slot": str(args[0]),
    }


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE, FIXTURE
    ORIGINAL_CWD = os.getcwd()
    FIXTURE = load_fixture()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a placement execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_recorded_before_state_equals_the_committed_seed(self) -> None:
        # The replay corpus is seeded from tests/saves/fresh-player.json,
        # so the fixture's before-state must be that same document.
        self.assertEqual(FIXTURE["before"], harness.load_seed())

    def test_recorded_envelope_is_exactly_the_shared_derivation(self) -> None:
        intent = recorded_intent()
        envelope = recorded_envelope()

        # Documented time-dependent input (design D4): a positive integer.
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)

        rebuilt = placement_envelope.build_envelope(
            item_id=intent["item_id"],
            x=intent["x"],
            y=intent["y"],
            costs=BOOT.item_costs(intent["item_id"]),  # type: ignore[union-attr]
            items=FIXTURE["before"]["maps"][0]["items"],
            orientation=intent["orientation"],
            ts=envelope["ts"],
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        # The documented placeholders (design D4) and the derived vector.
        self.assertEqual(
            intent["args"], [41, 1, 51, 39, 1, 0, 0, ""]
        )
        self.assertEqual(intent["resources_changed"], [0, 0, 0, -30, 0, 0, 0, 0])

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_effects(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        entry = after["maps"][0]["items"]["41"]
        self.assertEqual(len(entry), 8)
        self.assertEqual(
            [entry[0], entry[1], entry[2]], [1, 51, 39]
        )
        self.assertIsInstance(entry[3], int)  # wall clock — time-dependent
        self.assertGreater(entry[3], 0)
        self.assertEqual(entry[4], 0)
        self.assertEqual(entry[5], [])
        self.assertEqual(entry[6], {"nc": 0})
        self.assertEqual(entry[7], 1)
        self.assertEqual(after["maps"][0]["wood"], before["maps"][0]["wood"] - 30)
        self.assertEqual(after["maps"][0]["gold"], before["maps"][0]["gold"])
        self.assertEqual(after["playerInfo"]["cash"], before["playerInfo"]["cash"])
        self.assertEqual(after["privateState"]["boughtUnits"], [1])


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the intent replayed through ``/v0/place``."""

    def test_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])

        with harness.offline():
            response = CLIENT.post(  # type: ignore[union-attr]
                "/v0/place",
                json={
                    "user_id": intent["user_id"],
                    "item_id": intent["item_id"],
                    "x": intent["x"],
                    "y": intent["y"],
                    "orientation": intent["orientation"],
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    superset: placement + resources, design D7).
        legacy_body = json.loads(FIXTURE["body"])
        self.assertEqual(payload["result"], legacy_body["result"])
        self.assertEqual(payload["result"], "success")

        # 2. Placement equals the captured entry field-by-field, except the
        #    documented time-dependent timestamp.
        fixture_entry = FIXTURE["after"]["maps"][0]["items"][intent["slot"]]
        placement = payload["placement"]
        self.assertEqual(len(placement), 8)
        for index in (0, 1, 2, 4, 5, 6, 7):
            self.assertEqual(
                placement[index],
                fixture_entry[index],
                "placement field %d differs from the executed legacy entry"
                % index,
            )
        self.assertIsInstance(placement[3], int)
        self.assertGreater(placement[3], 0)

        # 3. Resources equal the values read from the captured after-state
        #    (all seven applied slots are stable fields).
        after_map = FIXTURE["after"]["maps"][0]
        expected_resources = {
            "xp": after_map["xp"],
            "gold": after_map["gold"],
            "wood": after_map["wood"],
            "oil": after_map["oil"],
            "steel": after_map["steel"],
            "cash": FIXTURE["after"]["playerInfo"]["cash"],
            "mana": FIXTURE["after"]["privateState"]["mana"],
        }
        self.assertEqual(payload["resources"], expected_resources)

        # 4. The endpoint read back what it persisted: the corpus entry and
        #    the response placement are the same document.
        raw_corpus_after = harness.read_seeded_save(CORPUS)
        self.assertEqual(
            raw_corpus_after["maps"][0]["items"][intent["slot"]], payload["placement"]
        )

        # 5. The corpus save after execution equals the captured after-state
        #    for every leaf, after normalizing the one documented
        #    time-dependent field (the entry's wall-clock timestamp) on
        #    both sides. Both normalized values are proven to be real
        #    positive timestamps before being zeroed.
        fixture_ts = fixture_entry[3]
        corpus_ts = raw_corpus_after["maps"][0]["items"][intent["slot"]][3]
        self.assertIsInstance(fixture_ts, int)
        self.assertGreater(fixture_ts, 0)
        self.assertIsInstance(corpus_ts, int)
        self.assertGreater(corpus_ts, 0)

        expected_after = copy.deepcopy(FIXTURE["after"])
        normalized_corpus = copy.deepcopy(raw_corpus_after)
        expected_after["maps"][0]["items"][intent["slot"]][3] = 0
        normalized_corpus["maps"][0]["items"][intent["slot"]][3] = 0
        self.assertEqual(
            harness.diff_documents(expected_after, normalized_corpus), []
        )

        # 6. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class PlaceParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())


if __name__ == "__main__":
    unittest.main()
