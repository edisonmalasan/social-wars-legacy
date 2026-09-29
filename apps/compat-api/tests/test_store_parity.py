#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/store`` vs the executed-legacy store
fixture (OpenSpec task 2.3).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any
socket tries to connect), and ``test_no_server_is_running`` asserts that
neither the legacy port (5055) nor the Compatibility API port (5056) is
listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-store/`` — one real ``store_item`` command
executed by the legacy server in a disposable copy (the Tree decoration,
item id 905, at map slot ``2`` anchored at ``(53,39)``, moved from the map
into the empty storage of the fresh-player corpus).  The test posts the
*intent* recorded in that fixture's request to the endpoint and compares:

* the response ``result`` against the captured legacy response body;
* the response ``removed`` against the captured **before**-state row at that
  legacy key (entry for entry, no normalization) and against the fact that
  the key is absent from the captured after-state;
* the response ``store`` against the captured after-state's whole storage
  mapping (the two-sided superset of design D4);
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable and, under the neutral vector,
  identical to the before-state);
* the corpus save after execution against the captured after-state, leaf
  for leaf;
* the shared derivation against the recorded request envelope, exactly
  (the recorded ``ts`` is passed back into the derivation).

Documented time-dependent fields: **the state carries none**, and that is
asserted rather than assumed.  ``command.store_item`` pops one row,
increments one storage entry, and writes nothing else — the popped row's own
``timestamp`` field is not written anywhere — and ``engine.apply_resources``'s
timestamp write is commented out in legacy (``engine.py:269``), so the
fixture's ``after.json`` is byte-identical across reruns and the state
comparison below needs **no** normalization at all.  The one time-dependent
field is the envelope ``ts`` inside the recorded request, which is asserted to
be a positive integer before the envelope comparison and then held fixed by
passing it back into the derivation.  The parity claim covers this one
recorded transaction against the fresh-player corpus (see the fixture README's
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
import store_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-store"
STEP = "command_store_item"
LOGIN_STEP = "login_post"
FIXTURE_INDEX = 2
FIXTURE_ITEM_ID = 905
FIXTURE_ROW = [905, 53, 39, 0, 0, [], {}, 1]
# The move fixture's row (a Turret I), used by the follow-up replay test so
# the two fixtures stay independently readable.
MOVE_FIXTURE_INDEX = 11
MOVE_FIXTURE_ROW = [22, 58, 48, 0, 0, [], {}, 1]

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

    Parsing goes through :func:`store_envelope.parse_data_field`, which
    also verifies the recorded 64-hex digest against the payload.
    """
    return store_envelope.parse_data_field(FIXTURE["request"]["form"]["data"])


def recorded_intent() -> Dict[str, Any]:
    envelope = recorded_envelope()
    command = envelope["commands"][0]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "item_index": command[2][0],
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
        raise AssertionError("a store execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def store(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/store", json=payload)  # type: ignore[union-attr]


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
        row = FIXTURE["before"]["maps"][0]["items"][str(FIXTURE_INDEX)]
        self.assertEqual(row, FIXTURE_ROW)
        self.assertEqual(len(FIXTURE["before"]["maps"][0]["items"]), 40)
        # The storage starts empty, which is why the increment is observable.
        self.assertEqual(FIXTURE["before"]["maps"][0]["store"], {})
        self.assertEqual(FIXTURE["before"]["privateState"]["boughtUnits"], [])

    def test_recorded_envelope_is_exactly_the_shared_derivation(self) -> None:
        intent = recorded_intent()
        envelope = recorded_envelope()

        # The one time-dependent input: a positive integer, held fixed below.
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)

        rebuilt = store_envelope.build_envelope(
            item_index=intent["item_index"],
            ts=envelope["ts"],
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        self.assertEqual(sorted(envelope), sorted(store_envelope.ENVELOPE_KEYS))
        # The documented command, its single argument, and the neutral vector.
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["command"], "store_item")
        self.assertEqual(intent["item_index"], FIXTURE_INDEX)
        self.assertEqual(intent["resources_changed"], [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(len(envelope["commands"][0][2]), 1)

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_effect(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        self.assertNotIn(str(FIXTURE_INDEX), after["maps"][0]["items"])
        self.assertEqual(len(after["maps"][0]["items"]), 39)
        self.assertEqual(
            sorted(after["maps"][0]["items"], key=int),
            sorted(set(before["maps"][0]["items"]) - {str(FIXTURE_INDEX)}, key=int),
        )
        for key in before["maps"][0]["items"]:
            if key == str(FIXTURE_INDEX):
                continue
            with self.subTest(key=key):
                self.assertEqual(
                    after["maps"][0]["items"][key], before["maps"][0]["items"][key]
                )
        # The storage gained exactly the popped row's item id, with the
        # quantity legacy's add_store_item default of 1.
        self.assertEqual(after["maps"][0]["store"], {str(FIXTURE_ITEM_ID): 1})
        # This branch records no purchase: unlike buy / place_stored_item /
        # buy_stored_item_cash it never calls bought_unit_add.
        self.assertEqual(after["privateState"], before["privateState"])
        self.assertEqual(after["privateState"]["boughtUnits"], [])
        self.assertEqual(after["privateState"]["deadHeroes"], {})
        # The neutral vector moves no resource at all.
        self.assertEqual(resources_of(after), resources_of(before))
        self.assertEqual(
            resources_of(after),
            {
                "xp": 4,
                "gold": 2000,
                "wood": 2000,
                "oil": 2000,
                "steel": 2000,
                "cash": 5,
                "mana": 0,
            },
        )

    def test_the_executed_state_carries_no_time_dependent_field(self) -> None:
        """The store pops one row, bumps one storage entry, writes no clock.

        ``command.store_item`` writes nothing but those two facts and
        ``apply_resources``' timestamp write is commented out in legacy
        (``engine.py:269``), so the only differences between the recorded
        before- and after-states are the removed key and the storage entry —
        no ``timestamp``, no ``logged_in``, no other clock reading.
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
        # Exactly the removed row's key and the added storage entry — nothing
        # else anywhere in the document. The walk descends into objects, so
        # the storage container itself is never a difference leaf.
        self.assertEqual(
            sorted(differences),
            ["/maps/0/items/2", "/maps/0/store/905"],
        )
        for path in differences:
            with self.subTest(path=path):
                self.assertNotIn("timestamp", path)
                self.assertNotIn("logged_in", path)

    def test_the_top_level_diff_is_exactly_the_move_legacy_derives(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        before_keys = set(before["maps"][0]["items"])
        after_keys = set(after["maps"][0]["items"])
        # Legacy map keys are strings: engine.map_pop_item looks the row up
        # by ``str(index)`` (engine.py:42-47).
        self.assertEqual(
            sorted(before_keys - after_keys, key=int), [str(FIXTURE_INDEX)]
        )
        self.assertEqual(after_keys - before_keys, set())
        # Everything outside maps[0].items and maps[0].store is byte-identical.
        self.assertEqual(after["playerInfo"], before["playerInfo"])
        self.assertEqual(after["privateState"], before["privateState"])
        after_map = {
            k: v for k, v in after["maps"][0].items() if k not in ("items", "store")
        }
        before_map = {
            k: v for k, v in before["maps"][0].items() if k not in ("items", "store")
        }
        self.assertEqual(after_map, before_map)


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the intent replayed through ``/v0/store``.

    A store is destructive and the module shares one disposable corpus, so
    the mutating tests are ordered by name: ``test_a_...`` replays the
    recorded transaction first (its assertions require the corpus to still
    be at the fixture's before-state), and the two follow-ups build on that
    result with their own dedicated rows.
    """

    def test_a_the_recorded_index_is_addressable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rule agrees with the recorded row."""
        intent = recorded_intent()
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        self.assertTrue(BOOT.has_map_item(PID, intent["item_index"]))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, intent["item_index"])  # type: ignore[union-attr]
        self.assertEqual(row, FIXTURE_ROW)
        self.assertEqual(
            row, FIXTURE["before"]["maps"][0]["items"][str(intent["item_index"])]
        )
        self.assertEqual(BOOT.map_store(PID), {})  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]

    def test_b_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])

        response = store(
            {"user_id": intent["user_id"], "item_index": intent["item_index"]}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    two-sided superset: removed + store + resources, design D4).
        legacy_body = json.loads(FIXTURE["body"])
        self.assertEqual(payload["result"], legacy_body["result"])
        self.assertEqual(payload["result"], "success")

        # 2. The removed row equals the captured *before*-state row at that
        #    legacy key, field for field (no normalization: no clock is
        #    stored, and the persisted save no longer holds the row).
        captured_row = FIXTURE["before"]["maps"][0]["items"][str(intent["item_index"])]
        self.assertEqual(payload["removed"], captured_row)
        self.assertEqual(len(payload["removed"]), 8)
        self.assertNotIn(
            str(intent["item_index"]), FIXTURE["after"]["maps"][0]["items"]
        )

        # 3. The storage mapping is the captured after-state's whole mapping.
        self.assertEqual(payload["store"], FIXTURE["after"]["maps"][0]["store"])
        self.assertEqual(payload["store"], {str(FIXTURE_ITEM_ID): 1})

        # 4. Resources equal the values read from the captured after-state
        #    (all seven applied slots are stable fields, and the neutral
        #    vector leaves them identical to the before-state).
        self.assertEqual(payload["resources"], resources_of(FIXTURE["after"]))
        self.assertEqual(payload["resources"], resources_of(FIXTURE["before"]))

        # 5. The endpoint proved both halves from the persisted save, not from
        #    its own copies.
        raw_corpus_after = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertNotIn(
            str(intent["item_index"]), raw_corpus_after["maps"][0]["items"]
        )
        self.assertFalse(BOOT.has_map_item(PID, intent["item_index"]))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.map_item(PID, intent["item_index"]))  # type: ignore[union-attr]
        self.assertIn(str(FIXTURE_ITEM_ID), BOOT.map_store(PID))  # type: ignore[union-attr]
        # The branch writes no bought-units bookkeeping.
        self.assertEqual(
            raw_corpus_after["privateState"]["boughtUnits"],
            FIXTURE["before"]["privateState"]["boughtUnits"],
        )

        # 6. The corpus save after execution equals the captured after-state
        #    for every leaf, with no normalization required: the store writes
        #    no time-dependent field (proven above).
        self.assertEqual(
            harness.diff_documents(FIXTURE["after"], raw_corpus_after), []
        )

        # 7. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_c_the_replayed_store_is_stable_not_cumulative(self) -> None:
        """A second store of the same index is a structured error."""
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]

        response = store(
            {"user_id": intent["user_id"], "item_index": intent["item_index"]}
        )

        self.assertEqual(response.status_code, 404)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "unknown_item_index")
        # Nothing changed on the second call: no second increment either.
        self.assertEqual(
            harness.read_seeded_save(CORPUS), after_first  # type: ignore[arg-type]
        )
        self.assertEqual(
            after_first["maps"][0]["store"], {str(FIXTURE_ITEM_ID): 1}
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_d_a_different_row_stores_independently_after_the_replay(self) -> None:
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]

        response = store({"user_id": intent["user_id"], "item_index": MOVE_FIXTURE_INDEX})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["removed"], MOVE_FIXTURE_ROW)
        # The whole mapping travels back, so the previously stored Tree is
        # still there and the Turret I joins it.
        self.assertEqual(
            payload["store"], {str(FIXTURE_ITEM_ID): 1, "22": 1}
        )
        self.assertEqual(payload["resources"], resources_of(after_first))
        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        for key in after_first["maps"][0]["items"]:
            if key in (str(intent["item_index"]), str(MOVE_FIXTURE_INDEX)):
                continue
            with self.subTest(key=key):
                self.assertEqual(
                    after_second["maps"][0]["items"][key],
                    after_first["maps"][0]["items"][key],
                )
        self.assertEqual(
            len(after_second["maps"][0]["items"]),
            len(after_first["maps"][0]["items"]) - 1,
        )
        self.assertEqual(
            after_second["privateState"]["boughtUnits"],
            FIXTURE["before"]["privateState"]["boughtUnits"],
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class StoreParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        self.assertTrue((FIXTURES / "steps" / STEP / "request.json").is_file())
        self.assertTrue((FIXTURES / "steps" / LOGIN_STEP / "after.json").is_file())
        manifest = json.loads(
            (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["schema"], "godot-building-store/legacy-capture-v1"
        )
        self.assertEqual(
            [step["name"] for step in manifest["transaction"]["steps"]],
            ["login_post", "command_store_item"],
        )
        self.assertEqual(manifest["transaction"]["store_after"], {"905": 1})
        self.assertFalse(manifest["transaction"]["storing_cost_claimed"])
        self.assertFalse(manifest["transaction"]["capacity_rule_claimed"])

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "a store execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()
