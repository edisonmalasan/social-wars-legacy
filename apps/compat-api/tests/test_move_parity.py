#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/move`` vs the executed-legacy move
fixture (OpenSpec task 2.3).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any
socket tries to connect), and ``test_no_server_is_running`` asserts that
neither the legacy port (5055) nor the Compatibility API port (5056) is
listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-move/`` — one real ``move`` command
executed by the legacy server in a disposable copy (the Turret I, item id
22, at map slot ``11``, moved from ``(58,48)`` to ``(58,47)`` against the
fresh-player corpus).  The test posts the *intent* recorded in that
fixture's request to the endpoint and compares:

* the response ``result`` against the captured legacy response body;
* the response ``placement`` against the captured after-state row at that
  legacy key (entry for entry, no normalization);
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable and, under the neutral vector,
  identical to the before-state);
* the corpus save after execution against the captured after-state, leaf
  for leaf;
* the shared derivation against the recorded request envelope, exactly
  (the recorded ``ts`` is passed back into the derivation).

Documented time-dependent fields: **the state carries none**, and that is
asserted rather than assumed.  ``command.move`` writes exactly ``item[1]``
and ``item[2]`` — the row's own ``timestamp`` field is left alone — and
``engine.apply_resources``'s timestamp write is commented out in legacy
(``engine.py:269``), so the fixture's ``after.json`` is byte-identical
across reruns and the state comparison below needs **no** normalization at
all.  The one time-dependent field is the envelope ``ts`` inside the
recorded request, which is asserted to be a positive integer before the
envelope comparison and then held fixed by passing it back into the
derivation.  The parity claim covers this one recorded transaction against
the fresh-player corpus (see the fixture README's claim limits).
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
import move_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-move"
STEP = "command_move"

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

    Parsing goes through :func:`move_envelope.parse_data_field`, which
    also verifies the recorded 64-hex digest against the payload.
    """
    return move_envelope.parse_data_field(FIXTURE["request"]["form"]["data"])


def recorded_intent() -> Dict[str, Any]:
    envelope = recorded_envelope()
    command = envelope["commands"][0]
    args = command[2]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "item_index": args[0],
        "x": args[1],
        "y": args[2],
        "frame": args[3],
        "string": args[4],
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
        raise AssertionError("a move execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def move(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/move", json=payload)  # type: ignore[union-attr]


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
    """The seven slots the endpoint reports, read from a save document."""
    first_map = document["maps"][0]
    return {
        "xp": first_map["xp"],
        "gold": first_map["gold"],
        "wood": first_map["wood"],
        "oil": first_map["oil"],
        "steel": first_map["steel"],
        "cash": document["playerInfo"]["cash"],
        "mana": document["privateState"]["mana"],
    }


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_recorded_before_state_equals_the_committed_seed(self) -> None:
        # The replay corpus is seeded from tests/saves/fresh-player.json,
        # so the fixture's before-state must be that same document.
        self.assertEqual(FIXTURE["before"], harness.load_seed())
        row = FIXTURE["before"]["maps"][0]["items"]["11"]
        self.assertEqual(row, [22, 58, 48, 0, 0, [], {}, 1])
        self.assertEqual(len(FIXTURE["before"]["maps"][0]["items"]), 40)

    def test_recorded_envelope_is_exactly_the_shared_derivation(self) -> None:
        intent = recorded_intent()
        envelope = recorded_envelope()

        # The one time-dependent input: a positive integer, held fixed below.
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)

        rebuilt = move_envelope.build_envelope(
            item_index=intent["item_index"],
            x=intent["x"],
            y=intent["y"],
            frame=intent["frame"],
            string=intent["string"],
            ts=envelope["ts"],
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        self.assertEqual(sorted(envelope), sorted(move_envelope.ENVELOPE_KEYS))
        # The documented placeholders, the command, and the neutral vector.
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["command"], "move")
        self.assertEqual(intent["item_index"], 11)
        self.assertEqual([intent["x"], intent["y"]], [58, 47])
        self.assertEqual(intent["frame"], 0)
        self.assertEqual(intent["string"], "")
        self.assertEqual(intent["resources_changed"], [0, 0, 0, 0, 0, 0, 0, 0])

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_effect(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        row = after["maps"][0]["items"]["11"]
        self.assertEqual(row, [22, 58, 47, 0, 0, [], {}, 1])
        # Everything else in the row is the value legacy already held.
        self.assertEqual(row[3:], before["maps"][0]["items"]["11"][3:])
        # A move places nothing, stores nothing, and records no purchase.
        self.assertEqual(len(after["maps"][0]["items"]), 40)
        self.assertEqual(sorted(after["maps"][0]["items"]), sorted(before["maps"][0]["items"]))
        self.assertEqual(after["maps"][0]["store"], before["maps"][0]["store"])
        self.assertEqual(
            after["privateState"]["boughtUnits"], before["privateState"]["boughtUnits"]
        )
        # The neutral vector moves no resource at all.
        self.assertEqual(resources_of(after), resources_of(before))

    def test_the_executed_state_carries_no_time_dependent_field(self) -> None:
        """The move writes two coordinates and neither of them is a clock.

        Legacy writes both ``item[1]`` and ``item[2]``; the derived target
        keeps ``x=58``, so only the ``y`` leaf is observably different — and
        it is a cell, not a timestamp.
        """
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
        # Exactly the addressed row's coordinates, and nothing else anywhere.
        # The derived target keeps x=58, so only the y index differs.
        self.assertEqual(differences, ["/maps/0/items/11/2"])
        for path in differences:
            with self.subTest(path=path):
                self.assertNotIn("timestamp", path)
                self.assertNotIn("logged_in", path)


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the intent replayed through ``/v0/move``."""

    def test_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])

        response = move(
            {
                "user_id": intent["user_id"],
                "item_index": intent["item_index"],
                "x": intent["x"],
                "y": intent["y"],
            }
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    superset: placement + resources, design D4).
        legacy_body = json.loads(FIXTURE["body"])
        self.assertEqual(payload["result"], legacy_body["result"])
        self.assertEqual(payload["result"], "success")

        # 2. The placement equals the captured after-state row at that legacy
        #    key, field for field (no normalization: no clock is stored).
        captured_row = FIXTURE["after"]["maps"][0]["items"][str(intent["item_index"])]
        self.assertEqual(payload["placement"], captured_row)

        # 3. Resources equal the values read from the captured after-state
        #    (all seven applied slots are stable fields, and the neutral
        #    vector leaves them identical to the before-state).
        self.assertEqual(payload["resources"], resources_of(FIXTURE["after"]))
        self.assertEqual(payload["resources"], resources_of(FIXTURE["before"]))

        # 4. The endpoint read back what it persisted: the corpus row and the
        #    response placement are the same eight-field entry.
        raw_corpus_after = harness.read_seeded_save(CORPUS)
        self.assertEqual(
            raw_corpus_after["maps"][0]["items"][str(intent["item_index"])],
            payload["placement"],
        )

        # 5. The corpus save after execution equals the captured after-state
        #    for every leaf, with no normalization required: the move writes no
        #    time-dependent field (proven above).
        self.assertEqual(
            harness.diff_documents(FIXTURE["after"], raw_corpus_after), []
        )

        # 6. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_replayed_row_moves_again_and_only_the_row_moves(self) -> None:
        """A second move from the after-state is stable, not cumulative."""
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        intent = recorded_intent()

        response = move(
            {
                "user_id": intent["user_id"],
                "item_index": intent["item_index"],
                "x": 57,
                "y": 48,
            }
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual([payload["placement"][1], payload["placement"][2]], [57, 48])
        # Resources are still untouched after two moves.
        self.assertEqual(payload["resources"], resources_of(after_first))
        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        for key in after_first["maps"][0]["items"]:
            if key == str(intent["item_index"]):
                continue
            with self.subTest(key=key):
                self.assertEqual(
                    after_second["maps"][0]["items"][key],
                    after_first["maps"][0]["items"][key],
                )
        self.assertEqual(len(after_second["maps"][0]["items"]), 40)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_recorded_index_is_addressable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rule agrees with the recorded row."""
        intent = recorded_intent()
        self.assertTrue(BOOT.has_map_item(PID, intent["item_index"]))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, intent["item_index"])  # type: ignore[union-attr]
        self.assertEqual(row[1:3], [intent["x"], intent["y"]])
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]


class MoveParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        self.assertTrue((FIXTURES / "steps" / STEP / "request.json").is_file())
        self.assertTrue((FIXTURES / "steps" / "login_post" / "after.json").is_file())

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "a move execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()
