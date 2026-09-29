#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/purchase`` vs the executed-legacy
purchase fixture (OpenSpec task 2.3).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any
socket tries to connect), and ``test_no_server_is_running`` asserts that
neither the legacy port (5055) nor the Compatibility API port (5056) is
listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-item-purchase/`` — one real ``buy_stored_item_cash``
command executed by the legacy server in a disposable copy (Victory Arch,
item id 105, price ``{"c": 5}``, against the fresh-player corpus).  The
test posts the *intent* recorded in that fixture's request to the endpoint
and compares:

* the response ``result`` against the captured legacy response body;
* the response ``store`` against the captured after-state storage mapping;
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable);
* the corpus save after execution against the captured after-state, leaf
  for leaf;
* the shared derivation against the recorded request envelope, exactly
  (the recorded ``ts`` is passed back into the derivation).

Documented time-dependent fields: **the state carries none**. Unlike the
placement transaction, ``buy_stored_item_cash`` writes no wall-clock value
(``engine.add_store_item`` and ``engine.bought_unit_add`` store no
timestamp, and ``engine.apply_resources``'s timestamp write is commented
out), so the fixture's ``after.json`` is byte-identical across reruns and
the state comparison below needs **no** normalization at all — asserted
here rather than assumed.  The one time-dependent field is the envelope
``ts`` inside the recorded request, which is asserted to be a positive
integer before the envelope comparison and then held fixed by passing it
back into the derivation.  The parity claim covers this one recorded
transaction against the fresh-player corpus (see the fixture README's
claim limits).
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
import purchase_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-item-purchase"
STEP = "command_buy_stored_item_cash"

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


def load_fixture() -> Dict[str, Any]:
    base = FIXTURES / "steps" / STEP
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

    Parsing goes through :func:`purchase_envelope.parse_data_field`, which
    also verifies the recorded 64-hex digest against the payload.
    """
    return purchase_envelope.parse_data_field(
        FIXTURE["request"]["form"]["data"]
    )


def recorded_intent() -> Dict[str, Any]:
    envelope = recorded_envelope()
    command = envelope["commands"][0]
    args = command[2]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "item_id": args[0],
        "resources_changed": command[3],
        "command": command[1],
        "map_id": command[0],
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
        raise AssertionError("a purchase execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_recorded_before_state_equals_the_committed_seed(self) -> None:
        # The replay corpus is seeded from tests/saves/fresh-player.json,
        # so the fixture's before-state must be that same document.
        self.assertEqual(FIXTURE["before"], harness.load_seed())
        self.assertEqual(
            FIXTURE["before"]["playerInfo"]["cash"], 5
        )
        self.assertEqual(FIXTURE["before"]["maps"][0]["store"], {})

    def test_recorded_envelope_is_exactly_the_shared_derivation(self) -> None:
        intent = recorded_intent()
        envelope = recorded_envelope()

        # The one time-dependent input: a positive integer, held fixed below.
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)

        rebuilt = purchase_envelope.build_envelope(
            item_id=intent["item_id"],
            costs=BOOT.item_costs(intent["item_id"]),  # type: ignore[union-attr]
            ts=envelope["ts"],
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        self.assertEqual(sorted(envelope), sorted(purchase_envelope.ENVELOPE_KEYS))
        # The documented placeholders, the command, and the cash-only vector.
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["command"], "buy_stored_item_cash")
        self.assertEqual(intent["item_id"], 105)
        self.assertEqual(intent["resources_changed"], [0, 0, 0, 0, 0, 0, -5, 0])

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_effects(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        self.assertEqual(after["maps"][0]["store"], {"105": 1})
        self.assertEqual(after["playerInfo"]["cash"], 0)
        self.assertEqual(before["playerInfo"]["cash"], 5)
        self.assertEqual(after["privateState"]["boughtUnits"], [105])
        # A storage purchase places nothing on the map.
        self.assertEqual(after["maps"][0]["items"], before["maps"][0]["items"])
        for key in ("xp", "gold", "wood", "oil", "steel"):
            self.assertEqual(after["maps"][0][key], before["maps"][0][key])
        self.assertEqual(after["privateState"]["mana"], before["privateState"]["mana"])

    def test_the_executed_state_carries_no_time_dependent_field(self) -> None:
        """The purchase writes three leaves and none of them is a clock."""
        differences: List[str] = []

        def walk(left: Any, right: Any, path: str) -> None:
            if isinstance(left, dict) and isinstance(right, dict):
                for key in sorted(set(left) | set(right)):
                    walk(left.get(key), right.get(key), "%s/%s" % (path, key))
            elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
                for index, (one, other) in enumerate(zip(left, right)):
                    walk(one, other, "%s/%d" % (path, index))
            elif left != right:
                differences.append(path)

        walk(FIXTURE["before"], FIXTURE["after"], "")
        self.assertEqual(
            differences,
            ["/maps/0/store/105", "/playerInfo/cash", "/privateState/boughtUnits"],
        )
        for path in differences:
            with self.subTest(path=path):
                self.assertNotIn("timestamp", path)
                self.assertNotIn("logged_in", path)


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the intent replayed through ``/v0/purchase``."""

    def test_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])

        with harness.offline():
            response = CLIENT.post(  # type: ignore[union-attr]
                "/v0/purchase",
                json={"user_id": intent["user_id"], "item_id": intent["item_id"]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    superset: store + resources, design D4).
        legacy_body = json.loads(FIXTURE["body"])
        self.assertEqual(payload["result"], legacy_body["result"])
        self.assertEqual(payload["result"], "success")

        # 2. The storage mapping equals the captured after-state storage,
        #    entry for entry (no normalization: no clock is stored).
        self.assertEqual(
            payload["store"], FIXTURE["after"]["maps"][0]["store"]
        )

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

        # 4. The endpoint read back what it persisted: the corpus storage and
        #    the response store are the same document.
        raw_corpus_after = harness.read_seeded_save(CORPUS)
        self.assertEqual(raw_corpus_after["maps"][0]["store"], payload["store"])

        # 5. The corpus save after execution equals the captured after-state
        #    for every leaf, with no normalization required: the purchase
        #    writes no time-dependent field (proven above).
        self.assertEqual(
            harness.diff_documents(FIXTURE["after"], raw_corpus_after), []
        )

        # 6. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_replayed_save_still_matches_a_second_replay(self) -> None:
        """A second purchase from the after-state is stable, not cumulative."""
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        intent = recorded_intent()

        with harness.offline():
            response = CLIENT.post(  # type: ignore[union-attr]
                "/v0/purchase",
                json={"user_id": intent["user_id"], "item_id": intent["item_id"]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The storage entry increments; cash was already 0 and clamps again.
        self.assertEqual(payload["store"]["105"], 2)
        self.assertEqual(payload["resources"]["cash"], 0)
        # bought_unit_add appends only when absent, so it stays length 1.
        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(after_second["privateState"]["boughtUnits"], [105])
        self.assertEqual(after_second["maps"][0]["items"], after_first["maps"][0]["items"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class PurchaseParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        self.assertTrue((FIXTURES / "steps" / STEP / "request.json").is_file())
        self.assertTrue((FIXTURES / "steps" / "login_post" / "after.json").is_file())


if __name__ == "__main__":
    unittest.main()
