#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/upgrade`` vs the executed-legacy
upgrade fixture (OpenSpec task 2.4).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any
socket tries to connect), and ``test_no_server_is_running`` asserts that
neither the legacy port (5055) nor the Compatibility API port (5056) is
listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-upgrade/`` — one real two-command
upgrade batch (``sell`` with the committed ``UPGR`` reason, then ``buy``
of the next tier) executed by the legacy server in a disposable copy
(the Wall I, item id 23, at map slot ``12`` anchored at ``(45,49)``,
upgraded to the Wall II, item id 24, against the fresh-player corpus).
The test posts the *intent* recorded in that fixture's request to the
endpoint and compares:

* the response ``result`` against the captured legacy response body;
* the response ``removed`` against the captured **before**-state row at
  that legacy key (entry for entry, no normalization);
* the response ``upgraded`` against the captured **after**-state row at
  that key, field for field, with the new row's wall-clock
  ``timestamp`` documented and normalized (proved below);
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable and, under the neutral
  vectors, identical to the before-state);
* the corpus save after execution against the captured after-state,
  leaf for leaf, under the same documented normalization;
* the shared derivation against the recorded request envelope, exactly
  (the recorded ``ts`` is passed back into the derivation).

Documented time-dependent fields: **the state carries exactly one**,
the new row's ``timestamp``.  It is written by
``engine.map_add_item``'s ``timestamp_now()`` default
(``engine.py:13-14``), because the buy half writes a *fresh* row rather
than editing the replaced one — the replaced row's own timestamp,
``store``, and ``attr`` are not carried over (design D5).  Every other
leaf of the recorded state is byte-stable, which is asserted here by a
leaf-level diff of the recorded before- and after-states: exactly four
leaves differ and only one of them is a clock reading.  The envelope
``ts`` inside the recorded request is the other time-dependent field;
it is asserted to be a positive integer before the envelope comparison
and then held fixed by passing it back into the derivation.

The parity claim covers this one recorded transaction against the
fresh-player corpus (see the fixture README's claim limits).
"""

from __future__ import annotations

import copy
import json
import os
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness

import compat_legacy
import compat_service
import upgrade_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-upgrade"
STEP = "command_upgrade"
LOGIN_STEP = "login_post"
FIXTURE_INDEX = 12
FIXTURE_ITEM_ID = 23  # Wall I
FIXTURE_TARGET_ITEM_ID = 24  # Wall II
FIXTURE_ANCHOR = (45, 49)
# The one documented time-dependent leaf of the recorded state: the fresh
# row's wall-clock timestamp.
NEW_ROW_TIMESTAMP_POINTER = "/maps/0/items/%d/3" % FIXTURE_INDEX
NEW_ROW_TIMESTAMP = re.compile(r"^/maps/0/items/%d/3$" % FIXTURE_INDEX)
# The reason that would route a row through push_dead_unit — the fixture's
# recorded reason is the committed upgrade constant, so this path is never
# reached (design D2).
COMBAT_REASON = "KILL"

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
        "manifest": json.loads(
            (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
        ),
    }


def recorded_envelope() -> Dict[str, Any]:
    """The executed legacy envelope, parsed from the recorded ``data`` field.

    Parsing goes through :func:`upgrade_envelope.parse_data_field`, which
    also verifies the recorded 64-hex digest against the payload.
    """
    return upgrade_envelope.parse_data_field(FIXTURE["request"]["form"]["data"])


def recorded_intent() -> Dict[str, Any]:
    envelope = recorded_envelope()
    sell_entry, buy_entry = envelope["commands"]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "item_index": sell_entry[2][0],
        "reason": sell_entry[2][1],
        "buy_args": buy_entry[2],
        "sell_args": sell_entry[2],
        "command_order": [sell_entry[1], buy_entry[1]],
        "map_id": sell_entry[0],
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
        raise AssertionError("an upgrade execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def upgrade(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/upgrade", json=payload)  # type: ignore[union-attr]


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


def row_at(document: Dict[str, Any]) -> List[Any]:
    return list(document["maps"][0]["items"][str(FIXTURE_INDEX)])


def normalize_new_timestamp(document: Dict[str, Any]) -> Tuple[Any, List[Tuple[str, Any]]]:
    """Prune the one documented time-dependent leaf and report what it held."""
    return harness.prune_paths(document, [NEW_ROW_TIMESTAMP])


def leaf_differences(left: Any, right: Any) -> List[str]:
    """Every JSON-pointer leaf at which two documents differ."""
    paths: List[str] = []

    def walk(one: Any, other: Any, path: str) -> None:
        if isinstance(one, dict) and isinstance(other, dict):
            for key in sorted(set(one) | set(other)):
                walk(one.get(key), other.get(key), "%s/%s" % (path, key))
        elif (
            isinstance(one, list)
            and isinstance(other, list)
            and len(one) == len(other)
        ):
            for index, (first, second) in enumerate(zip(one, other)):
                walk(first, second, "%s/%d" % (path, index))
        elif one != other:
            paths.append(path or "/")

    walk(left, right, "")
    return paths


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_recorded_before_state_equals_the_committed_seed(self) -> None:
        # The replay corpus is seeded from tests/saves/fresh-player.json, so
        # the fixture's before-state must be that same document.
        self.assertEqual(FIXTURE["before"], harness.load_seed())
        row = FIXTURE["before"]["maps"][0]["items"][str(FIXTURE_INDEX)]
        self.assertEqual(row, [23, 45, 49, 0, 0, [], {}, 1])
        self.assertEqual(len(FIXTURE["before"]["maps"][0]["items"]), 40)
        # The login step left the corpus untouched.
        login_after = json.loads(
            (FIXTURES / "steps" / LOGIN_STEP / "after.json").read_text(encoding="utf-8")
        )
        login_before = json.loads(
            (FIXTURES / "steps" / LOGIN_STEP / "before.json").read_text(encoding="utf-8")
        )
        self.assertEqual(login_after, login_before)

    def test_recorded_envelope_is_exactly_the_shared_derivation(self) -> None:
        intent = recorded_intent()
        envelope = recorded_envelope()

        # The one time-dependent input: a positive integer, held fixed below.
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)

        # The target tier is the configuration's own resolution, never a
        # client value, and the cell / orientation / player are the replaced
        # row's.
        before_row = FIXTURE["before"]["maps"][0]["items"][str(FIXTURE_INDEX)]
        self.assertEqual(BOOT.item_upgrade_to(int(before_row[0])), FIXTURE_TARGET_ITEM_ID)  # type: ignore[union-attr]

        rebuilt = upgrade_envelope.build_envelope(
            item_index=intent["item_index"],
            target_item_id=FIXTURE_TARGET_ITEM_ID,
            x=before_row[1],
            y=before_row[2],
            player=before_row[7],
            orientation=before_row[4],
            ts=envelope["ts"],
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        self.assertEqual(sorted(envelope), sorted(upgrade_envelope.ENVELOPE_KEYS))
        # The two commands, in the forced order, and the committed reason.
        self.assertEqual(intent["command_order"], ["sell", "buy"])
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["item_index"], FIXTURE_INDEX)
        self.assertEqual(intent["reason"], upgrade_envelope.UPGRADE_REASON)
        self.assertEqual(intent["reason"], "UPGR")
        self.assertNotEqual(intent["reason"], COMBAT_REASON)
        self.assertEqual(
            intent["buy_args"], [FIXTURE_INDEX, FIXTURE_TARGET_ITEM_ID, 45, 49, 1, 0, 0, ""]
        )
        # Both vectors are neutral, on both commands.
        for entry in envelope["commands"]:
            self.assertEqual(entry[3], [0, 0, 0, 0, 0, 0, 0, 0])

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_replacement(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        key = str(FIXTURE_INDEX)
        # The key is reused, so the placement count does not move.
        self.assertIn(key, after["maps"][0]["items"])
        self.assertEqual(len(after["maps"][0]["items"]), 40)
        self.assertEqual(
            sorted(after["maps"][0]["items"], key=int),
            sorted(before["maps"][0]["items"], key=int),
        )
        row_after = row_at(after)
        self.assertEqual(len(row_after), 8)
        self.assertEqual(row_after[0], FIXTURE_TARGET_ITEM_ID)
        self.assertEqual([row_after[1], row_after[2]], list(FIXTURE_ANCHOR))
        self.assertEqual(row_after[4], 0)  # orientation reused
        self.assertEqual(row_after[5], [])  # store
        self.assertEqual(row_after[6], {"nc": 0})  # click-to-build seed
        self.assertEqual(row_after[7], 1)  # player team reused
        # A fresh wall-clock timestamp, never the replaced row's 0.
        self.assertIsInstance(row_after[3], int)
        self.assertGreater(row_after[3], 0)
        for key_other in before["maps"][0]["items"]:
            if key_other == key:
                continue
            with self.subTest(key=key_other):
                self.assertEqual(
                    after["maps"][0]["items"][key_other],
                    before["maps"][0]["items"][key_other],
                )
        # An upgrade stores nothing.
        self.assertEqual(after["maps"][0]["store"], before["maps"][0]["store"])
        # The purchase half recorded the new tier; nothing else in
        # privateState moves, and deadHeroes stands because the reason is
        # "UPGR", never "KILL".
        self.assertEqual(after["privateState"]["boughtUnits"], [FIXTURE_TARGET_ITEM_ID])
        self.assertEqual(before["privateState"]["boughtUnits"], [])
        self.assertEqual(after["privateState"]["deadHeroes"], {})
        private_before = dict(before["privateState"])
        private_after = dict(after["privateState"])
        private_before.pop("boughtUnits")
        private_after.pop("boughtUnits")
        self.assertEqual(private_after, private_before)
        self.assertEqual(after["playerInfo"], before["playerInfo"])
        # The neutral vectors move no resource at all.
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

    def test_the_recorded_state_carries_exactly_one_time_dependent_leaf(self) -> None:
        """The normalization this suite applies is the *whole* clock surface.

        Exactly four leaves differ between the recorded before- and
        after-states, and only one of them is a clock reading: the fresh
        row's ``timestamp``.  The other three are the new item id, the
        click-to-build seed the buy half writes, and the grown bought-units
        list.
        """
        differences = leaf_differences(FIXTURE["before"], FIXTURE["after"])
        self.assertEqual(
            sorted(differences),
            sorted(
                [
                    "/maps/0/items/%d/0" % FIXTURE_INDEX,
                    "/maps/0/items/%d/3" % FIXTURE_INDEX,
                    "/maps/0/items/%d/6/nc" % FIXTURE_INDEX,
                    "/privateState/boughtUnits",
                ]
            ),
        )
        # Exactly one of the four is the clock reading this suite normalizes;
        # the other three are the new tier, the click-to-build seed, and the
        # bought-units list.
        self.assertEqual(
            [path for path in differences if path == NEW_ROW_TIMESTAMP_POINTER],
            [NEW_ROW_TIMESTAMP_POINTER],
        )
        self.assertFalse([path for path in differences if "logged_in" in path])
        # The map-level timestamp is not rewritten either (apply_resources'
        # write is commented out in legacy, engine.py:269).
        self.assertEqual(
            FIXTURE["after"]["maps"][0]["timestamp"],
            FIXTURE["before"]["maps"][0]["timestamp"],
        )

    def test_the_manifest_records_the_negative_oracle(self) -> None:
        """Task 1.3: the reverse order succeeds and destroys the building."""
        oracle = FIXTURE["manifest"]["negative_oracle"]
        self.assertEqual(oracle["response_body"], '{"result": "success"}')
        self.assertEqual(oracle["http_status"], 200)
        self.assertEqual(oracle["placement_count_before"], 40)
        self.assertEqual(oracle["placement_count_after"], 39)
        self.assertIn("absent", oracle["key_12_afterwards"])
        self.assertEqual(
            [entry[1] for entry in oracle["envelope_commands"]], ["buy", "sell"]
        )
        self.assertIn("internal_error", oracle["consequence"])

    def test_the_manifest_records_the_time_dependent_leaves(self) -> None:
        record = FIXTURE["manifest"]["time_dependent_fields"]
        self.assertIn("/maps/0/items/12/3", " ".join(record["leaves"]))
        self.assertIn("/transaction/upgraded_row_after/3", " ".join(record["leaves"]))


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the intent replayed through ``/v0/upgrade``.

    An upgrade rewrites a row in place and the module shares one disposable
    corpus, so the mutating tests are ordered by name: ``test_a_...`` inspects
    the corpus at the fixture's before-state first, ``test_b_...`` replays the
    recorded transaction (its assertions require that before-state), and the
    follow-ups build on that result with their own dedicated rows.
    """

    def test_a_the_recorded_index_is_addressable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rule agrees with the recorded row."""
        intent = recorded_intent()
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        self.assertTrue(BOOT.has_map_item(PID, intent["item_index"]))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, intent["item_index"])  # type: ignore[union-attr]
        self.assertEqual(row, [23, 45, 49, 0, 0, [], {}, 1])
        self.assertEqual(
            row, FIXTURE["before"]["maps"][0]["items"][str(intent["item_index"])]
        )
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]
        # The target tier resolves from the committed configuration.
        self.assertEqual(
            BOOT.item_upgrade_to(int(row[0])), FIXTURE_TARGET_ITEM_ID  # type: ignore[union-attr]
        )

    def test_b_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])

        response = upgrade(
            {"user_id": intent["user_id"], "item_index": intent["item_index"]}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    superset: removed + upgraded + resources, design D5).
        legacy_body = json.loads(FIXTURE["body"])
        self.assertEqual(payload["result"], legacy_body["result"])
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])

        # 2. The removed row equals the captured *before*-state row at that
        #    legacy key, field for field (no normalization: it carries no
        #    clock value).
        captured_before_row = row_at(FIXTURE["before"])
        self.assertEqual(payload["removed"], captured_before_row)
        self.assertEqual(len(payload["removed"]), 8)

        # 3. The upgraded row equals the captured *after*-state row, field for
        #    field, with the new row's wall-clock timestamp documented and
        #    normalized.  Every other field — item id, cell, orientation,
        #    store, attr, player — must match exactly.
        captured_after_row = row_at(FIXTURE["after"])
        upgraded = list(payload["upgraded"])
        self.assertEqual(len(upgraded), 8)
        replay_stamp = upgraded.pop(3)
        captured_stamp = captured_after_row.pop(3)
        self.assertEqual(upgraded, captured_after_row)
        # The normalization itself: both are positive wall-clock stamps, and
        # the replay's is not earlier than the replaced row's.
        self.assertIsInstance(replay_stamp, int)
        self.assertGreater(replay_stamp, 0)
        self.assertGreater(replay_stamp, captured_before_row[3])
        self.assertIsInstance(captured_stamp, int)
        self.assertGreater(captured_stamp, 0)

        # 4. Resources equal the values read from the captured after-state
        #    (all seven applied slots are stable fields, and the neutral
        #    vectors leave them identical to the before-state).
        self.assertEqual(payload["resources"], resources_of(FIXTURE["after"]))
        self.assertEqual(payload["resources"], resources_of(FIXTURE["before"]))

        # 5. The endpoint proved the replacement from the persisted save, not
        #    from its own copy of the row.
        raw_corpus_after = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertIn(str(intent["item_index"]), raw_corpus_after["maps"][0]["items"])
        self.assertEqual(raw_corpus_after["maps"][0]["items"][str(intent["item_index"])],
                         payload["upgraded"])

        # 6. The corpus save after execution equals the captured after-state
        #    for every leaf, under exactly the one documented normalization.
        pruned_replay, collected_replay = normalize_new_timestamp(raw_corpus_after)
        pruned_capture, collected_capture = normalize_new_timestamp(FIXTURE["after"])
        # The normalization removed a real leaf on both sides.
        self.assertEqual(
            [path for path, _value in collected_replay], [NEW_ROW_TIMESTAMP_POINTER]
        )
        self.assertEqual(
            [path for path, _value in collected_capture], [NEW_ROW_TIMESTAMP_POINTER]
        )
        # Without the normalization the two states differ in exactly that one
        # leaf — asserted, so the normalization can never silently widen.
        unnormalized = harness.diff_documents(FIXTURE["after"], raw_corpus_after)
        self.assertEqual(
            [entry.split(":", 1)[0] for entry in unnormalized],
            [NEW_ROW_TIMESTAMP_POINTER],
        )
        self.assertEqual(harness.diff_documents(pruned_capture, pruned_replay), [])

        # 7. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_c_the_replay_is_stable_not_cumulative(self) -> None:
        """A second upgrade of the same index is a real second tier change."""
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]

        response = upgrade(
            {"user_id": intent["user_id"], "item_index": intent["item_index"]}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["removed"][0], after_first["maps"][0]["items"][str(intent["item_index"])][0]
        )
        self.assertNotEqual(payload["upgraded"][0], payload["removed"][0])
        # The cell is reused and the placement count never moves.
        self.assertEqual(payload["upgraded"][1:3], payload["removed"][1:3])
        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(
            len(after_second["maps"][0]["items"]), len(after_first["maps"][0]["items"])
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_d_a_different_row_upgrades_independently_after_the_replay(self) -> None:
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]

        response = upgrade({"user_id": intent["user_id"], "item_index": 13})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["removed"], [23, 44, 49, 0, 0, [], {}, 1])
        self.assertEqual(payload["upgraded"][0], FIXTURE_TARGET_ITEM_ID)
        self.assertEqual(payload["resources"], resources_of(after_first))
        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        for key in after_first["maps"][0]["items"]:
            if key in (str(intent["item_index"]), "13"):
                continue
            with self.subTest(key=key):
                self.assertEqual(
                    after_second["maps"][0]["items"][key],
                    after_first["maps"][0]["items"][key],
                )
        self.assertEqual(
            len(after_second["maps"][0]["items"]), len(after_first["maps"][0]["items"])
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_e_the_replayed_transaction_matches_the_committed_fixture_only(self) -> None:
        """The rows the fixture records are the rows the endpoint produces."""
        intent = recorded_intent()
        response = upgrade({"user_id": intent["user_id"], "item_index": 15})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["removed"], [23, 42, 49, 0, 0, [], {}, 1])
        # Identical response shape to the fixture's own transaction, only the
        # row index differs.
        self.assertEqual(
            sorted(payload),
            sorted(
                [
                    "protocol",
                    "ok",
                    "game_version",
                    "server_time",
                    "result",
                    "removed",
                    "upgraded",
                    "resources",
                ]
            ),
        )
        self.assertEqual(payload["upgraded"][:2], [FIXTURE_TARGET_ITEM_ID, 42])
        self.assertEqual(payload["upgraded"][6], {"nc": 0})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class UpgradeParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        self.assertTrue((FIXTURES / "steps" / STEP / "request.json").is_file())
        self.assertTrue((FIXTURES / "steps" / LOGIN_STEP / "after.json").is_file())

    def test_the_fixture_readme_states_the_negative_oracle(self) -> None:
        """Task 1.3: the README records the reverse-order outcome."""
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn('{"result":"success"}', readme)
        self.assertIn("not evidence of an upgrade", readme)
        self.assertIn("absent", readme)
        # 40 -> 39 placements, however the arrow is rendered.
        self.assertIsNotNone(
            re.search(r"`?40`?\s*(?:→|->)\s*`?39`?", readme),
            "the README must record the reverse order's placement count",
        )
        self.assertIn("internal_error", readme)
        self.assertIn("no_upgrade_path", readme)
        # The established-versus-derived split and the non-claims.
        self.assertIn("Established from committed legacy source", readme)
        self.assertIn("Derived and never observed from the Flash client", readme)
        self.assertIn("No upgrade cost is claimed", readme)
        self.assertIn("premium_upgrade_costs", readme)
        self.assertIn("level gate", readme)
        self.assertIn("daily-upgrade limit", readme)
        self.assertIn("space check", readme)

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "an upgrade execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()
