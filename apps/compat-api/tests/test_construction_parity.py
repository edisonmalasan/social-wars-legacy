#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/construction`` vs the executed-legacy
construction fixture (OpenSpec task 2.4).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any
socket tries to connect), and ``test_no_server_is_running`` asserts that
neither the legacy port (5055) nor the Compatibility API port (5056) is
listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-construction/`` — one real **two-command**
construction batch (``activate`` carrying the item's committed ``build_time``,
then ``add_click``) executed by the legacy server in a disposable copy (the
placed Turret I, item id 22, at map slot ``11`` anchored at ``(58,48)``,
against the fresh-player corpus).  The endpoint executes **one** command per
request, so the replay posts the two recorded actions in order — ``"start"``
then ``"click"`` — against the two dedicated rows, and compares:

* the response ``result`` against the captured legacy response body;
* the response ``previous`` of the first call against the captured
  **before**-state row at that legacy key (entry for entry, no normalization);
* the response ``row`` of the second call against the captured **after**-state
  row at that key, field for field, with the row's re-stamped wall-clock start
  time documented and normalized (proved below);
* the response ``action`` of each call against the recorded command it stands
  for (``activate`` → ``start``, ``add_click`` → ``click``);
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable and, under the neutral vectors,
  identical to the before-state);
* the corpus save after execution against the captured after-state, leaf for
  leaf, under the same documented normalization;
* the shared derivation against the recorded request envelope, exactly (the
  recorded ``ts`` is passed back into the derivation).

Documented time-dependent fields: **the state carries exactly one**, the
addressed row's re-stamped ``timestamp`` — the construction's start instant,
written by ``activate``'s ``item[3] = time_now()`` and read by no branch as
anything but data (``command.py:421-424``).  Every other leaf of the recorded
state is byte-stable, which is asserted here by a leaf-level diff of the
recorded before- and after-states: exactly two leaves differ and only one of
them is a clock reading.  The envelope ``ts`` inside the recorded request is
the other time-dependent field; it is asserted to be a positive integer before
the envelope comparison and then held fixed by passing it back into the
derivation.

The parity claim covers these two recorded transactions against the
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
import construction_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-construction"
STEP = "command_construction"
LOGIN_STEP = "login_post"
FIXTURE_INDEX = 11
FIXTURE_ITEM_ID = 22  # Turret I
FIXTURE_BUILD_TIME = 5
FIXTURE_ANCHOR = (58, 48)
# The one documented time-dependent leaf of the recorded state: the row's
# re-stamped wall-clock start instant.
ROW_TIMESTAMP_POINTER = "/maps/0/items/%d/3" % FIXTURE_INDEX
ROW_TIMESTAMP = re.compile(r"^/maps/0/items/%d/3$" % FIXTURE_INDEX)
# A second pair of dedicated rows, used by the follow-up replays so the module's
# shared corpus stays readable and the fixture's own row keeps its meaning.
SECOND_INDEX = 12  # Wall I at (45,49) — the upgrade fixture's row
SECOND_ANCHOR = (45, 49)
THIRD_INDEX = 13  # Wall I at (44,49)
FOURTH_INDEX = 14  # Wall I at (43,49)

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

    Parsing goes through :func:`construction_envelope.parse_data_field`, which
    also verifies the recorded 64-hex digest against the payload.
    """
    return construction_envelope.parse_data_field(FIXTURE["request"]["form"]["data"])


def recorded_intent() -> Dict[str, Any]:
    """The two recorded actions, derived from the recorded command list."""
    envelope = recorded_envelope()
    activate_entry, click_entry = envelope["commands"]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "item_index": activate_entry[2][0],
        "duration": activate_entry[2][1],
        "click_args": click_entry[2],
        "command_order": [activate_entry[1], click_entry[1]],
        "map_id": activate_entry[0],
        # The action each recorded command stands for, and the builder the
        # endpoint uses for it.
        "actions": [
            construction_envelope.ACTION_START,
            construction_envelope.ACTION_CLICK,
        ],
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
        raise AssertionError("a construction execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def construct(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/construction", json=payload)  # type: ignore[union-attr]


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


def row_at(document: Dict[str, Any], index: int = FIXTURE_INDEX) -> List[Any]:
    return list(document["maps"][0]["items"][str(index)])


def normalize_row_timestamp(document: Dict[str, Any]) -> Tuple[Any, List[Tuple[str, Any]]]:
    """Prune the one documented time-dependent leaf and report what it held."""
    return harness.prune_paths(document, [ROW_TIMESTAMP])


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
        row = row_at(FIXTURE["before"])
        self.assertEqual(row, [FIXTURE_ITEM_ID, 58, 48, 0, 0, [], {}, 1])
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

        # The duration is the addressed item's committed build time, resolved
        # through the loaded configuration, never a client value.
        before_row = row_at(FIXTURE["before"])
        self.assertEqual(
            BOOT.item_build_time(int(before_row[0])), FIXTURE_BUILD_TIME  # type: ignore[union-attr]
        )

        rebuilt_start = construction_envelope.build_envelope_start(
            item_index=intent["item_index"],
            duration=FIXTURE_BUILD_TIME,
            ts=envelope["ts"],
        )
        rebuilt_click = construction_envelope.build_envelope_click(
            item_index=intent["item_index"], ts=envelope["ts"]
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelopes.
        self.assertEqual(rebuilt_start["commands"], envelope["commands"][:1])
        self.assertEqual(rebuilt_click["commands"], envelope["commands"][1:])
        for rebuilt in (rebuilt_start, rebuilt_click):
            self.assertEqual(sorted(rebuilt), sorted(construction_envelope.ENVELOPE_KEYS))
            self.assertEqual(rebuilt["ts"], envelope["ts"])
            self.assertEqual(rebuilt["first_number"], 0)
            self.assertEqual(rebuilt["publishActions"], [])
            self.assertEqual(rebuilt["tries"], 1)
            self.assertEqual(rebuilt["accessToken"], "")
        # The two commands, their order, and their argument lists.
        self.assertEqual(intent["command_order"], ["activate", "add_click"])
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["item_index"], FIXTURE_INDEX)
        self.assertEqual(intent["duration"], FIXTURE_BUILD_TIME)
        self.assertEqual(intent["click_args"], [FIXTURE_INDEX])
        # Both vectors are neutral.
        for entry in envelope["commands"]:
            self.assertEqual(entry[3], [0, 0, 0, 0, 0, 0, 0, 0])

    def test_the_recorded_batch_never_carries_the_completing_command(self) -> None:
        """Task 1.3: the third command is covered, not captured."""
        names = [entry[1] for entry in recorded_envelope()["commands"]]
        self.assertNotIn("activate_item_click", names)
        self.assertEqual(recorded_intent()["actions"], ["start", "click"])

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_construction(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        key = str(FIXTURE_INDEX)
        # No key is added or removed.
        self.assertIn(key, after["maps"][0]["items"])
        self.assertEqual(len(after["maps"][0]["items"]), 40)
        self.assertEqual(
            sorted(after["maps"][0]["items"], key=int),
            sorted(before["maps"][0]["items"], key=int),
        )
        before_row = row_at(before)
        after_row = row_at(after)
        self.assertEqual(len(after_row), 8)
        self.assertEqual(after_row[0], FIXTURE_ITEM_ID)  # same item
        self.assertEqual([after_row[1], after_row[2]], list(FIXTURE_ANCHOR))  # same cell
        self.assertEqual(after_row[4], before_row[4])  # orientation
        self.assertEqual(after_row[5], [])  # store
        self.assertEqual(after_row[7], before_row[7])  # player team
        # The countdown equals the item's committed build time and the counter
        # equals its clicks_to_build — neither is compared by any branch.
        self.assertEqual(after_row[6], {"cp": FIXTURE_BUILD_TIME, "nc": 1})
        self.assertEqual(before_row[6], {})
        # The two recorded bag values are the item's own committed content,
        # read live from the loaded configuration.
        by_id = {int(entry["id"]): entry for entry in BOOT.config()["items"]}
        self.assertEqual(
            int(by_id[FIXTURE_ITEM_ID]["clicks_to_build"]),
            after_row[6]["nc"],
        )
        self.assertEqual(
            int(by_id[FIXTURE_ITEM_ID]["build_time"]), after_row[6]["cp"]
        )
        # A fresh wall-clock start instant, never the before-state's 0.
        self.assertIsInstance(after_row[3], int)
        self.assertGreater(after_row[3], 0)
        self.assertGreater(after_row[3], before_row[3])
        for key_other in before["maps"][0]["items"]:
            if key_other == key:
                continue
            with self.subTest(key=key_other):
                self.assertEqual(
                    after["maps"][0]["items"][key_other],
                    before["maps"][0]["items"][key_other],
                )
        # A construction stores nothing, buys nothing, and kills nothing.
        self.assertEqual(after["maps"][0]["store"], before["maps"][0]["store"])
        self.assertEqual(after["privateState"], before["privateState"])
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

        Exactly three leaves differ between the recorded before- and
        after-states, and only one of them is a clock reading: the row's
        re-stamped start instant.  The other two are the two attribute-bag
        entries the batch writes — the countdown and the click counter.
        """
        differences = leaf_differences(FIXTURE["before"], FIXTURE["after"])
        self.assertEqual(
            sorted(differences),
            sorted(
                [
                    "/maps/0/items/%d/3" % FIXTURE_INDEX,
                    "/maps/0/items/%d/6/cp" % FIXTURE_INDEX,
                    "/maps/0/items/%d/6/nc" % FIXTURE_INDEX,
                ]
            ),
        )
        self.assertEqual(
            [path for path in differences if path == ROW_TIMESTAMP_POINTER],
            [ROW_TIMESTAMP_POINTER],
        )
        # The map-level timestamp is not rewritten either (apply_resources'
        # write is commented out in legacy, engine.py:269).
        self.assertEqual(
            FIXTURE["after"]["maps"][0]["timestamp"],
            FIXTURE["before"]["maps"][0]["timestamp"],
        )

    def test_the_manifest_records_the_omitted_third_step(self) -> None:
        """Task 1.3: the completing command is recorded and covered."""
        omitted = FIXTURE["manifest"]["omitted_step"]
        self.assertEqual(omitted["command"], "activate_item_click")
        self.assertEqual(omitted["args"], [FIXTURE_INDEX])
        self.assertIn("BOTH", omitted["why_not_captured"])
        self.assertIn("docs/legacy-construction-timing.md", omitted["established_by"])
        self.assertIn("internal_error", omitted["covered_by"])
        self.assertIn("never observed", omitted["not_observed_from_client"])

    def test_the_manifest_records_the_derived_duration_and_the_claim_limits(self) -> None:
        intent_block = FIXTURE["manifest"]["intent"]
        self.assertEqual(intent_block["item_index"], FIXTURE_INDEX)
        self.assertEqual(intent_block["cell"], list(FIXTURE_ANCHOR))
        self.assertEqual(intent_block["actions"], ["start", "click"])
        self.assertEqual(
            intent_block["derived"]["duration"], FIXTURE_BUILD_TIME
        )
        self.assertIn("build_time", intent_block["derived"]["duration_source"])
        self.assertIn("derived from committed content", intent_block["derived"]["activate"]["duration_status"])
        self.assertIn("WHOLE attribute bag", intent_block["derived"]["activate"]["clearing_branch"])
        self.assertIn("no server-side completion rule exists", intent_block["derived"]["add_click"]["threshold_status"])
        self.assertIn("NO building cost is claimed", intent_block["derived"]["status"])
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertFalse(transaction["building_cost_claimed"])
        self.assertFalse(transaction["speedups_in_scope"])
        self.assertFalse(transaction["friend_assist_in_scope"])
        self.assertFalse(transaction["cancel_action_offered"])
        self.assertEqual(transaction["attr_after"], {"cp": 5, "nc": 1})
        self.assertEqual(transaction["attr_before"], {})
        self.assertEqual(transaction["row_before"], [FIXTURE_ITEM_ID, 58, 48, 0, 0, [], {}, 1])

    def test_the_manifest_records_the_time_dependent_leaves(self) -> None:
        record = FIXTURE["manifest"]["time_dependent_fields"]
        leaves = " ".join(record["leaves"])
        self.assertIn("/maps/0/items/11/3", leaves)
        self.assertIn("/transaction/row_after/3", leaves)
        self.assertIn("/transaction/steps/1/save_after_sha256", leaves)


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the recorded actions replayed offline.

    The module shares one disposable corpus, so the mutating tests are ordered
    by name: ``test_a_...`` inspects the corpus at the fixture's before-state
    first, ``test_b_...`` replays the recorded transaction (its assertions
    require that before-state), and the follow-ups build on that result with
    their own dedicated rows.
    """

    def test_a_the_recorded_index_is_addressable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rule agrees with the recorded row."""
        intent = recorded_intent()
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        self.assertTrue(BOOT.has_map_item(PID, intent["item_index"]))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, intent["item_index"])  # type: ignore[union-attr]
        self.assertEqual(row, [FIXTURE_ITEM_ID, 58, 48, 0, 0, [], {}, 1])
        self.assertEqual(row, row_at(FIXTURE["before"]))
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]
        # The duration resolves from the committed configuration.
        self.assertEqual(
            BOOT.item_build_time(int(row[0])), FIXTURE_BUILD_TIME  # type: ignore[union-attr]
        )

    def test_b_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        captured_before_row = row_at(FIXTURE["before"])
        captured_after_row = row_at(FIXTURE["after"])

        # --- the recorded start -------------------------------------------
        started = construct(
            {
                "user_id": intent["user_id"],
                "item_index": intent["item_index"],
                "action": construction_envelope.ACTION_START,
            }
        )
        self.assertEqual(started.status_code, 200)
        start_payload = started.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    superset: previous + row + action + resources, design D5).
        legacy_body = json.loads(FIXTURE["body"])
        self.assertEqual(start_payload["result"], legacy_body["result"])
        self.assertEqual(start_payload["result"], "success")
        self.assertEqual(start_payload["protocol"], "compat-v0")
        self.assertTrue(start_payload["ok"])
        self.assertEqual(start_payload["action"], intent["actions"][0])

        # 2. ``previous`` equals the captured *before*-state row at that legacy
        #    key, field for field (no normalization: it carries no clock value
        #    beyond the corpus's own 0).
        self.assertEqual(start_payload["previous"], captured_before_row)
        self.assertEqual(len(start_payload["previous"]), 8)

        # 3. The start's post-execution row: the derived countdown, and a
        #    re-stamped start instant compared structurally, never by value.
        start_row = start_payload["row"]
        self.assertEqual(len(start_row), 8)
        self.assertEqual(start_row[6], {"cp": FIXTURE_BUILD_TIME})
        self.assertIsInstance(start_row[3], int)
        self.assertGreater(start_row[3], 0)
        self.assertGreater(start_row[3], captured_before_row[3])

        # --- the recorded click -------------------------------------------
        clicked = construct(
            {
                "user_id": intent["user_id"],
                "item_index": intent["item_index"],
                "action": construction_envelope.ACTION_CLICK,
            }
        )
        self.assertEqual(clicked.status_code, 200)
        click_payload = clicked.get_json()
        self.assertEqual(click_payload["action"], intent["actions"][1])
        # The click reads the row the start left behind.
        self.assertEqual(click_payload["previous"], start_row)
        self.assertEqual(click_payload["row"][6], {"cp": FIXTURE_BUILD_TIME, "nc": 1})

        # 4. The final row equals the captured *after*-state row, field for
        #    field, with the row's re-stamped wall-clock start time documented
        #    and normalized.  Every other field — item, cell, orientation,
        #    store, attr, player — must match exactly.
        replay = list(click_payload["row"])
        self.assertEqual(len(replay), 8)
        replay_stamp = replay.pop(3)
        captured = list(captured_after_row)
        captured_stamp = captured.pop(3)
        self.assertEqual(replay, captured)
        # The normalization itself: both are positive wall-clock stamps, and the
        # replay's is not earlier than the before-state's.
        self.assertIsInstance(replay_stamp, int)
        self.assertGreater(replay_stamp, 0)
        self.assertGreater(replay_stamp, captured_before_row[3])
        self.assertIsInstance(captured_stamp, int)
        self.assertGreater(captured_stamp, 0)

        # 5. Resources equal the values read from the captured after-state
        #    (all seven applied slots are stable fields, and the neutral vectors
        #    leave them identical to the before-state).
        self.assertEqual(click_payload["resources"], resources_of(FIXTURE["after"]))
        self.assertEqual(click_payload["resources"], resources_of(FIXTURE["before"]))
        self.assertEqual(start_payload["resources"], resources_of(FIXTURE["before"]))

        # 6. The endpoint proved the construction from the persisted save, not
        #    from its own copy of the row.
        raw_corpus_after = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertIn(str(intent["item_index"]), raw_corpus_after["maps"][0]["items"])
        self.assertEqual(
            raw_corpus_after["maps"][0]["items"][str(intent["item_index"])],
            click_payload["row"],
        )

        # 7. The corpus save after execution equals the captured after-state
        #    for every leaf, under exactly the one documented normalization.
        pruned_replay, collected_replay = normalize_row_timestamp(raw_corpus_after)
        pruned_capture, collected_capture = normalize_row_timestamp(FIXTURE["after"])
        # The normalization removed a real leaf on both sides.
        self.assertEqual(
            [path for path, _value in collected_replay], [ROW_TIMESTAMP_POINTER]
        )
        self.assertEqual(
            [path for path, _value in collected_capture], [ROW_TIMESTAMP_POINTER]
        )
        # Without the normalization the two states differ in exactly that one
        # leaf — asserted, so the normalization can never silently widen.
        unnormalized = harness.diff_documents(FIXTURE["after"], raw_corpus_after)
        self.assertEqual(
            [entry.split(":", 1)[0] for entry in unnormalized],
            [ROW_TIMESTAMP_POINTER],
        )
        self.assertEqual(harness.diff_documents(pruned_capture, pruned_replay), [])

        # 8. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_c_the_replay_is_stable_not_cumulative(self) -> None:
        """Finishing the replayed build consumes the counter, keeping the
        countdown the client's readout needs."""
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]

        response = construct(
            {
                "user_id": intent["user_id"],
                "item_index": intent["item_index"],
                "action": construction_envelope.ACTION_FINISH,
            }
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["previous"], after_first["maps"][0]["items"][str(intent["item_index"])]
        )
        # Only nc is deleted; the countdown survives for the remaining-time
        # readout the client derives from it and the row's start time.
        self.assertEqual(payload["row"][6], {"cp": FIXTURE_BUILD_TIME})
        self.assertEqual(payload["row"][3], payload["previous"][3])
        self.assertEqual(payload["resources"], resources_of(after_first))
        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(
            len(after_second["maps"][0]["items"]), len(after_first["maps"][0]["items"])
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_d_a_different_row_constructs_independently_after_the_replay(self) -> None:
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        start = construct(
            {
                "user_id": intent["user_id"],
                "item_index": SECOND_INDEX,
                "action": construction_envelope.ACTION_START,
            }
        )
        self.assertEqual(start.status_code, 200)
        start_payload = start.get_json()
        # The fixture's row carries item 22's build time 5; this row is a Wall I
        # with build_time 1, so the duration is that row's own content.
        self.assertEqual(start_payload["previous"], [23, 45, 49, 0, 0, [], {}, 1])
        self.assertEqual(
            start_payload["row"][6], {"cp": BOOT.item_build_time(23)}  # type: ignore[union-attr]
        )
        self.assertEqual([start_payload["row"][1], start_payload["row"][2]], list(SECOND_ANCHOR))

        click = construct(
            {
                "user_id": intent["user_id"],
                "item_index": SECOND_INDEX,
                "action": construction_envelope.ACTION_CLICK,
            }
        )
        self.assertEqual(click.status_code, 200)
        self.assertEqual(click.get_json()["row"][6], {"cp": 1, "nc": 1})
        self.assertEqual(click.get_json()["resources"], resources_of(after_first))

        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        for key in after_first["maps"][0]["items"]:
            if key in (str(intent["item_index"]), str(SECOND_INDEX)):
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

    def test_e_the_replayed_transaction_matches_the_committed_fixture_shape(self) -> None:
        """The rows the fixture records are the rows the endpoint produces."""
        intent = recorded_intent()
        response = construct(
            {
                "user_id": intent["user_id"],
                "item_index": THIRD_INDEX,
                "action": construction_envelope.ACTION_START,
            }
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["previous"], [23, 44, 49, 0, 0, [], {}, 1])
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
                    "previous",
                    "row",
                    "action",
                    "resources",
                ]
            ),
        )
        self.assertEqual(payload["row"][:2], [23, 44])
        self.assertEqual(payload["row"][6], {"cp": 1})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class ConstructionParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        self.assertTrue((FIXTURES / "steps" / STEP / "request.json").is_file())
        self.assertTrue((FIXTURES / "steps" / LOGIN_STEP / "after.json").is_file())

    def test_the_fixture_readme_states_the_provenance_split_and_the_claims(self) -> None:
        """Task 1.3 plus the recorded claim limits."""
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn('{"result":"success"}', readme)
        self.assertIn("Established from committed legacy source", readme)
        self.assertIn("Derived and never observed from the Flash client", readme)
        self.assertIn("No building cost is claimed", readme)
        self.assertIn("No server-side completion rule exists", readme)
        self.assertIn("client-side derivations", readme)
        self.assertIn("BUILD_SPEEDUP_PRICING", readme)
        self.assertIn("friend-assist", readme.lower())
        self.assertIn("internal_error", readme)
        self.assertIn("no_build_time", readme)
        # The documented time-dependent leaf, however the arrow is rendered.
        self.assertIn("/maps/0/items/11/3", readme)
        self.assertIsNotNone(
            re.search(r"`?\{\}`?\s*(?:→|->)\s*`?\{\"cp\": 5, \"nc\": 1\}`?", readme),
            "the README must record the attribute bag the batch writes",
        )

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "a construction execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()
