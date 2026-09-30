#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/queue`` vs the executed-legacy queue
fixture (OpenSpec task 2.4).

No server and no network: the endpoint runs through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and ``test_no_server_is_running`` asserts that neither the legacy port
(5055) nor the Compatibility API port (5056) is listening.

What is replayed
    The committed transaction under ``tests/fixtures/godot-unit-queues/`` - one
    real ``push_queue_unit`` followed by one real ``pop_queue_unit`` on map key
    **1**, each carrying the **neutral** vector
    ``[0, 0, 0, 0, 0, 0, 0, 0]``, executed by the legacy server in a disposable
    copy against the fresh-player corpus.  Map key 1 is the corpus's **own real
    placed training producer** (id 26, Command Center, ``training_time`` 5,
    ``min_level`` 1) with an **empty** attribute bag, so the pair is exercised
    with **no fabricated player state**.  The endpoint derives the very same
    envelopes from the very same module, so the replay compares:

    * the response ``result`` against the captured legacy response body;
    * the response's ``action``, ``map_key``, and the two rows against the
      recorded states - the ``attr`` bag by value for the count, the key set, the
      three-key teardown, and every key the branch does not own, and the
      **documented** exception of the start instant below;
    * the response's ``queue`` projection against the recorded after-state's bag;
    * the response's ``resources`` against the values read from the captured
      after-state - all seven slots are stable and the captured movement is the
      derived neutral vector, which is nothing;
    * the corpus save after execution against the captured after-state, leaf for
      leaf, with **exactly one** documented normalization - the branch's own
      wall-clock ``attr["ts"]`` stamp, the fixture's single time-dependent value;
    * the shared derivation against the recorded request envelopes, exactly (the
      recorded ``ts`` is passed back into the derivation).

The single documented normalization
    ``push_queue_unit`` writes ``attr["ts"] = timestamp_now()``
    (``engine.py:189``), so the captured ``ts`` is a **wall-clock reading** and is
    the fixture's only time-dependent value (the capture's manifest says so, and
    names the two files it appears in).  The replay therefore compares the start
    instant by **shape and direction** - present, a non-negative integer, and not
    earlier than the pre-execution one - and compares **everything else by
    value**.  That is the only pruning in this suite, and it is asserted rather
    than assumed: the comparison helper reports which pointers it skipped and the
    test asserts the skipped set is exactly that one path.

The parity claim covers this one recorded transaction against the fresh-player
corpus (see the fixture README's claim limits).  In particular the fixture
evidences a **push and a pop only**: the legacy server has **no** completion
command and no unit-materialising command, so nothing about a finished queue is
evidenced, and the manifest records that absence.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness

import compat_legacy
import compat_service
import queue_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-unit-queues"
PUSH_STEP = "command_push_queue_unit"
POP_STEP = "command_pop_queue_unit"
LOGIN_STEP = "login_post"
FIXTURE_MAP_KEY = 1
FIXTURE_ITEM = 26
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")
COMMITTED_RESOURCES = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}
# The ONE pointer the comparison prunes, for the one documented reason.
PRUNED_POINTER = "/maps/0/items/%d/6/ts" % FIXTURE_MAP_KEY
# The same pointer relative to an addressed ROW, for row-to-row comparisons.
PRUNED_ROW_POINTER = "/6/ts"

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


def load_step(name: str) -> Dict[str, Any]:
    base = FIXTURES / "steps" / name
    return {
        "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
        "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
        "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
        "meta": json.loads(
            (base / "response.meta.json").read_text(encoding="utf-8")
        ),
        "body": (base / "response.body").read_bytes(),
    }


def load_fixture() -> Dict[str, Any]:
    fixture = {
        "login": load_step(LOGIN_STEP),
        "push": load_step(PUSH_STEP),
        "pop": load_step(POP_STEP),
        "manifest": json.loads(
            (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
        ),
    }
    for step, action in (("push", "push"), ("pop", "pop")):
        data = fixture[step]["request"]["form"]["data"]
        envelope = queue_envelope.parse_data_field(data)
        entry = envelope["commands"][0]
        fixture[step]["envelope"] = envelope
        fixture[step]["intent"] = {
            "user_id": fixture[step]["request"]["form"]["USERID"],
            "map_key": entry[2][0],
            "action": action,
            "command": entry[1],
            "map_id": entry[0],
            "vector": entry[3],
        }
    return fixture


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
        raise AssertionError("a queue execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def queue_now(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/queue", json=payload)  # type: ignore[union-attr]


def row_attr(document: Dict[str, Any]) -> Dict[str, Any]:
    return document["maps"][0]["items"][str(FIXTURE_MAP_KEY)][6]  # type: ignore[index]


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
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


def leaf_differences(left: Any, right: Any) -> List[str]:
    """Every JSON-pointer leaf at which two documents differ."""

    def walk(one: Any, other: Any, path: str, out: List[str]) -> None:
        if isinstance(one, dict) and isinstance(other, dict):
            for key in sorted(set(one) | set(other)):
                child = "%s/%s" % (path, key)
                if key not in one or key not in other:
                    out.append(child)
                    continue
                walk(one[key], other[key], child, out)
        elif isinstance(one, list) and isinstance(other, list):
            for index in range(max(len(one), len(other))):
                child = "%s/%d" % (path, index)
                if index >= len(one) or index >= len(other):
                    out.append(child)
                    continue
                walk(one[index], other[index], child, out)
        elif one != other:
            out.append(path or "/")

    paths: List[str] = []
    walk(left, right, "", paths)
    return paths


def pruned_differences(
    expected: Any, actual: Any, pruned: str
) -> Tuple[List[str], List[str]]:
    """Every differing leaf, split into the pruned one and the kept ones.

    Both lists are returned so the prune is **asserted**, not assumed: the test
    that uses this helper checks that the pruned set is exactly the one pointer
    the fixture's manifest names as time-dependent, and that the kept set is
    empty.
    """
    differing = leaf_differences(expected, actual)
    skipped = [pointer for pointer in differing if pointer == pruned]
    kept = [pointer for pointer in differing if pointer != pruned]
    return kept, skipped


def committed_item(item_id: int) -> Dict[str, Any]:
    """The committed configuration's own item row, read from the stored config.

    Read directly rather than through the legacy adapter, because the queue
    service needs no content accessor: nothing about a queue is priced, timed, or
    gated, so adding one to the adapter would be a capability this contract does
    not have.
    """
    document = json.loads(
        (harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8")
    )
    for row in document["items"]:
        if isinstance(row, dict) and int(row.get("id", -1)) == item_id:
            return row
    raise AssertionError("the committed config resolves no item %d" % item_id)


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_recorded_before_state_equals_the_committed_seed(self) -> None:
        # The replay corpus is seeded from tests/saves/fresh-player.json, so the
        # fixture's first before-state must be that same document.
        self.assertEqual(FIXTURE["push"]["before"], harness.load_seed())
        self.assertEqual(
            FIXTURE["push"]["before"]["maps"][0]["items"][str(FIXTURE_MAP_KEY)],
            [FIXTURE_ITEM, 51, 41, 0, 0, [], {}, 1],
        )
        self.assertEqual(row_attr(FIXTURE["push"]["before"]), {})
        self.assertEqual(
            len(FIXTURE["push"]["before"]["maps"][0]["items"]), 40
        )
        # The login step left the corpus untouched.
        self.assertEqual(FIXTURE["login"]["after"], FIXTURE["login"]["before"])

    def test_recorded_envelopes_are_exactly_the_shared_derivation(self) -> None:
        for step, command in (
            ("push", "push_queue_unit"),
            ("pop", "pop_queue_unit"),
        ):
            with self.subTest(step=step):
                intent = FIXTURE[step]["intent"]
                envelope = FIXTURE[step]["envelope"]
                # The one time-dependent input: a positive integer, held fixed
                # below.  It is an envelope field legacy parses and never reads.
                self.assertIsInstance(envelope["ts"], int)
                self.assertGreater(envelope["ts"], 0)
                rebuilt = queue_envelope.build_envelope(
                    map_key=intent["map_key"],
                    action=intent["action"],
                    ts=envelope["ts"],
                )
                # Byte-for-byte: same inputs, same recorded ts, same envelope.
                self.assertEqual(rebuilt, envelope)
                self.assertEqual(
                    sorted(rebuilt), sorted(queue_envelope.ENVELOPE_KEYS)
                )
                self.assertEqual(len(envelope["commands"]), 1)
                self.assertEqual(intent["map_id"], 0)
                self.assertEqual(intent["command"], command)
                # The map index is the command's ONLY argument.
                self.assertEqual(intent["map_key"], FIXTURE_MAP_KEY)
                self.assertEqual(len(envelope["commands"][0][2]), 1)
                # Every slot is zero: a queue moves no resource.
                self.assertEqual(intent["vector"], FIXTURE_EXPECTED_VECTOR)
                self.assertEqual(intent["vector"], queue_envelope.neutral_vector())
                self.assertEqual(intent["user_id"], PID)

    def test_recorded_responses_are_the_legacy_result(self) -> None:
        for step in ("push", "pop"):
            with self.subTest(step=step):
                self.assertEqual(json.loads(FIXTURE[step]["body"]), {"result": "success"})
                self.assertEqual(FIXTURE[step]["meta"]["status"], 200)

    def test_the_recorded_after_states_show_the_documented_effects(self) -> None:
        push_after = row_attr(FIXTURE["push"]["after"])
        self.assertEqual(sorted(push_after), ["nu", "ts"])
        self.assertEqual(push_after["nu"], 1)
        self.assertIsInstance(push_after["ts"], int)
        self.assertGreater(push_after["ts"], 0)
        # The push changed nothing else: two leaves under the addressed bag, the
        # added count and the wall-clock stamp.
        self.assertEqual(
            leaf_differences(FIXTURE["push"]["before"], FIXTURE["push"]["after"]),
            ["/maps/0/items/1/6/nu", PRUNED_POINTER],
        )
        # The pop tore all three keys down together, and its after-state is the
        # seed byte-for-byte.
        self.assertEqual(row_attr(FIXTURE["pop"]["before"]), push_after)
        self.assertEqual(row_attr(FIXTURE["pop"]["after"]), {})
        self.assertEqual(
            leaf_differences(FIXTURE["pop"]["before"], FIXTURE["pop"]["after"]),
            ["/maps/0/items/1/6/nu", PRUNED_POINTER],
        )
        self.assertEqual(
            (FIXTURES / "steps" / POP_STEP / "after.json").read_bytes(),
            (FIXTURES / "steps" / PUSH_STEP / "before.json").read_bytes(),
        )
        # No placement is added, removed, or changed by either step.
        for step in ("push", "pop"):
            with self.subTest(step=step):
                before = FIXTURE[step]["before"]["maps"][0]["items"]  # type: ignore[index]
                after = FIXTURE[step]["after"]["maps"][0]["items"]  # type: ignore[index]
                self.assertEqual(sorted(after, key=int), sorted(before, key=int))
                self.assertEqual(len(after), 40)
                for key in before:
                    if str(key) == str(FIXTURE_MAP_KEY):
                        continue
                    with self.subTest(step=step, key=key):
                        self.assertEqual(after[key], before[key])
                self.assertEqual(
                    after[str(FIXTURE_MAP_KEY)][0], FIXTURE_ITEM
                )
                self.assertEqual(after[str(FIXTURE_MAP_KEY)][1:6], [51, 41, 0, 0, []])
        seed = harness.load_seed()
        for step in ("push", "pop"):
            with self.subTest(step=step):
                after = FIXTURE[step]["after"]
                self.assertEqual(after["maps"][0]["store"], seed["maps"][0]["store"])
                self.assertEqual(after["privateState"], seed["privateState"])
                self.assertEqual(after["playerInfo"], seed["playerInfo"])
                self.assertEqual(
                    after["maps"][0]["expansions"], seed["maps"][0]["expansions"]
                )
                self.assertNotIn("map_sizes", after["maps"][0])
                self.assertEqual(
                    after["maps"][0]["increasedPopulation"],
                    seed["maps"][0]["increasedPopulation"],
                )
        # Every stored resource is unchanged, because the derived vector is the
        # neutral one.
        for step in ("push", "pop"):
            with self.subTest(step=step):
                self.assertEqual(resources_of(FIXTURE[step]["after"]), COMMITTED_RESOURCES)
                self.assertEqual(
                    resources_of(FIXTURE[step]["after"]),
                    resources_of(FIXTURE[step]["before"]),
                )
        self.assertEqual(
            {
                name: resources_of(FIXTURE["pop"]["after"])[name]
                - resources_of(FIXTURE["push"]["before"])[name]
                for name in FIXTURE_RESOURCE_NAMES
            },
            {name: 0 for name in FIXTURE_RESOURCE_NAMES},
        )

    def test_the_manifest_records_the_probe_it_actually_executed(self) -> None:
        """Probe 1 is what makes the endpoint's "nothing moved" proof real rather
        than a tautology: a **client-sent** non-zero slot moves a balance through
        this very branch."""
        probes = FIXTURE["manifest"]["probes"]
        self.assertEqual(len(probes), 1)
        probe = probes[0]
        self.assertEqual(probe["probe"], 1)
        self.assertTrue(probe["executed_in_this_capture"])
        self.assertIn("push_queue_unit([1])", probe["commands"][0])
        self.assertIn("[0, 500, 0, 0, 0, 0, 0, 0]", probe["commands"][0])
        self.assertEqual(probe["xp_before"], 4)
        self.assertEqual(probe["xp_after"], 504)
        self.assertEqual(probe["changed_top_level_map_keys"], ["items", "xp"])
        self.assertEqual(
            probe["leaf_differences"],
            ["/maps/0/items/1/6/nu", PRUNED_POINTER, "/maps/0/xp"],
        )
        self.assertIn("command.py:676-685", probe["established"])
        self.assertIn("resource-minting exploit", probe["why_it_matters"])

    def test_the_manifest_records_the_captured_pair_and_the_missing_completion(
        self,
    ) -> None:
        """The fixture's honesty requirement: a push and a pop were captured, and
        NO completion was captured because none exists."""
        captured = FIXTURE["manifest"]["captured"]
        self.assertTrue(captured["push"])
        self.assertTrue(captured["pop"])
        self.assertFalse(captured["completion"])
        self.assertFalse(captured["completion_captured"])
        self.assertFalse(captured["completion_command_exists"])
        self.assertIn("NO COMPLETION WAS", captured["note"])
        self.assertIn("complete_collection", captured["note"])
        self.assertIn("complete_goal", captured["note"])
        self.assertIn("complete_tutorial", captured["note"])
        self.assertIn("nothing about a finished queue", captured["note"])
        absent = captured["no_server_side_completion"]
        self.assertEqual(absent["dispatcher_named_branches"], 63)
        self.assertEqual(
            sorted(absent["complete_family"]),
            ["complete_collection", "complete_goal", "complete_tutorial"],
        )
        self.assertIsNone(absent["queue_completion_command"])
        self.assertIsNone(absent["unit_materialising_command"])
        self.assertEqual(
            sorted(absent["attr_ts_uses"]),
            ["deletions", "readers", "writes"],
        )
        self.assertIn("engine.py:189", absent["attr_ts_uses"]["writes"])
        self.assertIn("engine.py:202", absent["attr_ts_uses"]["deletions"])
        # And the transaction block states the same absence in machine-readable
        # form, so a reader of the numbers alone still sees it.
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertFalse(transaction["unit_produced"])
        self.assertFalse(transaction["readiness_computed"])
        self.assertFalse(transaction["count_bound_applied"])
        self.assertIn("no command that", transaction["unit_note"])
        self.assertIn("NO readiness", transaction["readiness_note"])
        self.assertIn("NO maximum count", transaction["count_bound_note"])

    def test_the_manifest_records_the_target_and_the_recorded_contract(self) -> None:
        target = FIXTURE["manifest"]["target"]
        self.assertEqual(target["map_key"], FIXTURE_MAP_KEY)
        self.assertEqual(target["item_id"], 26)
        self.assertEqual(target["item_name"], "Command Center")
        self.assertEqual(target["training_time"], 5)
        self.assertEqual(target["min_level"], 1)
        self.assertEqual(target["group_type"], "COMMAND_CENTER")
        self.assertEqual(target["cell"], [51, 41])
        self.assertEqual(target["attr_before"], {})
        self.assertFalse(target["fabricated_state"])
        self.assertIn("NO fabricated player state", target["target_rule"])

        intent = FIXTURE["manifest"]["intent"]
        self.assertEqual(intent["map_key_sent"], FIXTURE_MAP_KEY)
        self.assertIn("ONLY argument", intent["map_key_rule"])
        self.assertIn("CLIENT-SENT", intent["vector_rule"])
        self.assertIn("NEUTRAL", intent["vector_rule"])
        self.assertTrue(intent["derived"]["vector_is_neutral"])
        self.assertEqual(intent["derived"]["commands_per_batch"], 1)
        self.assertEqual(
            intent["derived"]["push"]["resources_changed"], FIXTURE_EXPECTED_VECTOR
        )
        self.assertEqual(
            intent["derived"]["pop"]["resources_changed"], FIXTURE_EXPECTED_VECTOR
        )
        contract = intent["command_contract"]
        self.assertEqual(
            [record["command"] for record in contract],
            ["push_queue_unit", "pop_queue_unit", "push_queue_unit2"],
        )
        offered = [record["command"] for record in contract if record["offered_by_the_endpoint"]]
        self.assertEqual(offered, ["push_queue_unit", "pop_queue_unit"])
        self.assertIn("CLIENT-SUPPLIED", contract[2]["why_not_offered"])
        self.assertIn("NO VALIDATION", intent["no_validation"])
        self.assertIn("NO ELAPSED-TIME EVALUATION", intent["no_elapsed_time"])
        self.assertIn("TOGETHER", intent["teardown"])
        speedup = intent["speedup_contract"]
        self.assertTrue(speedup["recorded"])
        self.assertFalse(speedup["implemented"])
        self.assertFalse(speedup["charges_anything"])
        self.assertIn("KeyError", speedup["precondition"])
        self.assertIn("sm_training_time", speedup["duration_source"])
        self.assertIn("SECONDS", speedup["unit_reading"])
        self.assertIn("3600", speedup["cost_formula"])
        self.assertIn("ts = 0", speedup["teardown"])
        self.assertIn("Quite useless", speedup["author_verdict"])
        self.assertIn("300 of the 429", speedup["field_coverage"])
        self.assertIn("no speedup intent", speedup["endpoint_action"])

    def test_the_manifest_records_the_two_transactions(self) -> None:
        transactions = FIXTURE["manifest"]["transactions"]
        self.assertEqual(len(transactions), 2)
        self.assertEqual(
            [record["action"] for record in transactions], ["push", "pop"]
        )
        self.assertEqual(transactions[0]["command"], "push_queue_unit")
        self.assertEqual(transactions[1]["command"], "pop_queue_unit")
        self.assertEqual(transactions[0]["attr_before"], {})
        self.assertEqual(sorted(transactions[0]["attr_after"]), ["nu", "ts"])
        self.assertEqual(transactions[0]["attr_after"]["nu"], 1)
        self.assertTrue(transactions[0]["derived"]["start_instant"])
        self.assertFalse(transactions[0]["derived"]["teardown"])
        self.assertEqual(transactions[1]["attr_after"], {})
        self.assertTrue(transactions[1]["derived"]["teardown"])
        self.assertTrue(transactions[1]["derived"]["changed"])
        for record in transactions:
            with self.subTest(action=record["action"]):
                self.assertEqual(record["changed_row_pointer"], "/maps/0/items/1/6")
                # The push ADDS the two keys and the pop DELETES them, so both
                # transactions differ at exactly those two pointers: the count
                # (recorded by value) and the wall-clock stamp (time-dependent).
                self.assertEqual(
                    record["changed_leaves"],
                    ["/maps/0/items/1/6/nu", PRUNED_POINTER],
                )
                self.assertEqual(
                    record["projection_after"]["absent_is_absent"], True
                )
        self.assertEqual(
            transactions[1]["projection_after"],
            {
                "present": False,
                "count": None,
                "start_instant": None,
                "queued_unit_id": None,
                "keys": [],
                "absent_is_absent": True,
            },
        )

    def test_the_manifest_records_the_time_dependent_leaves(self) -> None:
        """The recorded state carries exactly ONE time-dependent value, in exactly
        the two files the manifest names, and the list is not empty."""
        record = FIXTURE["manifest"]["time_dependent_fields"]
        self.assertEqual(len(record["state_leaves"]), 2)
        joined = " ".join(record["state_leaves"])
        self.assertIn(PUSH_STEP, joined)
        self.assertIn(POP_STEP, joined)
        self.assertIn(PRUNED_POINTER, joined)
        self.assertIn("push_queue_unit stamps", record["rule"])
        stable = " ".join(record["stable_state_leaves"])
        self.assertIn("equal to the seed", stable)
        # The record-metadata and envelope-clock surface, and nothing in the state.
        self.assertGreaterEqual(len(record["leaves"]), 11)
        for leaf in record["leaves"]:
            with self.subTest(leaf=leaf):
                self.assertNotIn("after.json is byte-stable", leaf)
        self.assertIn("compared by SHAPE", record["stable_by_derivation"])
        self.assertIn("NOT moving backwards", record["documented_normalization"])

    def test_the_manifest_records_the_claim_limits_and_containment(self) -> None:
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertEqual(transaction["response_body"], '{"result": "success"}')
        self.assertEqual(transaction["map_key"], FIXTURE_MAP_KEY)
        self.assertEqual(transaction["placement_count_before"], 40)
        self.assertEqual(transaction["placement_count_after"], 40)
        self.assertFalse(transaction["map_sizes_present_before"])
        self.assertFalse(transaction["map_sizes_present_after"])
        self.assertEqual(transaction["store_after"], {})
        self.assertEqual(transaction["bought_units_after"], [])
        self.assertEqual(transaction["dead_heroes_after"], {})
        self.assertEqual(
            transaction["resource_delta"],
            {name: 0 for name in FIXTURE_RESOURCE_NAMES},
        )
        self.assertTrue(transaction["other_rows_unchanged"])
        self.assertTrue(transaction["other_map_fields_unchanged"])
        self.assertTrue(transaction["map_key_set_unchanged"])
        self.assertTrue(transaction["private_state_unchanged"])
        self.assertTrue(transaction["player_info_unchanged"])
        self.assertFalse(transaction["clamp_exercised"])
        self.assertIn("probe 1", transaction["clamp_note"])
        self.assertEqual(len(transaction["queue_writes"]), 3)
        self.assertIn("engine.py:183-189", transaction["queue_writes"][1])
        self.assertIn("engine.py:191-204", transaction["queue_writes"][2])
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertTrue(containment["working_tree_saves_unchanged"])
        self.assertTrue(containment["loopback_only"])
        self.assertTrue(containment["no_flash_browser_external_network"])
        self.assertTrue(containment["protected_fixtures"]["identical"])
        self.assertEqual(len(containment["protected_fixtures"]["paths"]), 10)
        self.assertEqual(
            containment["pre_combined_sha256"], containment["post_combined_sha256"]
        )
        self.assertTrue(FIXTURE["manifest"]["cleanup"]["server_stopped_within_run"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["startup_preserved_seed"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["login_preserved_seed"])


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the recorded intent replayed offline.

    The module shares one disposable corpus, so the mutating tests are ordered by
    name: ``test_a_...`` inspects the corpus at the fixture's before-state first
    and ``test_b_...`` replays the whole recorded pair.
    """

    def test_a_the_recorded_state_is_resolvable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rules agree with the recorded intent:
        the key addresses a real row, the row is an eight-field entry with an
        object bag, and the committed content behind it is a training producer."""
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["push"]["before"])
        self.assertTrue(BOOT.has_map_item(PID, FIXTURE_MAP_KEY))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, FIXTURE_MAP_KEY)  # type: ignore[union-attr]
        self.assertEqual(row, [FIXTURE_ITEM, 51, 41, 0, 0, [], {}, 1])
        self.assertEqual(BOOT.map_item_attr(PID, FIXTURE_MAP_KEY), {})  # type: ignore[union-attr]
        self.assertEqual(BOOT.resources(PID), COMMITTED_RESOURCES)  # type: ignore[union-attr]
        item = committed_item(FIXTURE_ITEM)
        self.assertEqual(item["name"], "Command Center")
        self.assertEqual(int(str(item["training_time"]).strip()), 5)
        self.assertEqual(int(str(item["min_level"]).strip()), 1)
        self.assertEqual(
            FIXTURE["push"]["intent"]["map_key"],
            FIXTURE["pop"]["intent"]["map_key"],
        )

    def test_b_the_recorded_pair_replays_through_the_endpoint(self) -> None:
        """The executing half of the parity claim: both recorded intents are
        replayed offline, in the recorded order, against the corpus the fixture
        was captured on.

        The endpoint derives the same envelopes from the same module, so the
        post-state must match the captured one at **every** leaf except the one
        documented wall-clock stamp - and the response must agree with both
        recorded after-states field for field.
        """
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # --- the recorded push ------------------------------------------------
        push = queue_now(dict(FIXTURE["push"]["intent"]))
        self.assertEqual(push.status_code, 200)
        body = push.get_json()
        self.assertEqual(body["result"], json.loads(FIXTURE["push"]["body"])["result"])
        self.assertEqual(body["protocol"], "compat-v0")
        self.assertTrue(body["ok"])
        self.assertEqual(body["action"], "push")
        self.assertEqual(body["map_key"], FIXTURE_MAP_KEY)
        # The two rows, against the recorded states.
        self.assertEqual(
            body["previous"], FIXTURE["push"]["before"]["maps"][0]["items"][  # type: ignore[index]
                str(FIXTURE_MAP_KEY)
            ]
        )
        self.assertEqual(body["previous"][0], FIXTURE_ITEM)
        self.assertEqual(body["row"][0], FIXTURE_ITEM)
        self.assertEqual(body["row"][1:6], [51, 41, 0, 0, []])
        self.assertEqual(body["row"][7], 1)
        self.assertEqual(body["row"][6]["nu"], 1)
        self.assertNotIn("ui", body["row"][6])
        # The projected queue, against the recorded after-state's bag.
        recorded_push_attr = row_attr(FIXTURE["push"]["after"])
        self.assertTrue(body["queue"]["present"])
        self.assertEqual(body["queue"]["count"], recorded_push_attr["nu"])
        self.assertEqual(body["queue"]["keys"], ["nu", "ts"])
        self.assertIsNone(body["queue"]["queued_unit_id"])
        # The start instant: present, integral, and not earlier - the ONE
        # comparison that is not by value, for the ONE documented reason.
        stamp = body["row"][6]["ts"]
        self.assertIsInstance(stamp, int)
        self.assertGreater(stamp, 0)
        self.assertGreaterEqual(stamp, FIXTURE["push"]["before"]["maps"][0]["items"][  # type: ignore[index]
            str(FIXTURE_MAP_KEY)
        ][6].get("ts", 0))
        # The resources, against the recorded after-state, by value.
        self.assertEqual(body["resources"], COMMITTED_RESOURCES)
        self.assertEqual(
            body["resources"], resources_of(FIXTURE["push"]["after"])
        )
        # The corpus save against the captured after-state, with exactly the one
        # documented prune.
        raw_after_push = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        kept, skipped = pruned_differences(
            FIXTURE["push"]["after"], raw_after_push, PRUNED_POINTER
        )
        self.assertEqual(kept, [], "the push replay matches every value but the stamp")
        self.assertEqual(skipped, [PRUNED_POINTER])
        # And the push really persisted.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)

        # --- the recorded pop -------------------------------------------------
        pop = queue_now(dict(FIXTURE["pop"]["intent"]))
        self.assertEqual(pop.status_code, 200)
        pop_body = pop.get_json()
        self.assertEqual(pop_body["result"], json.loads(FIXTURE["pop"]["body"])["result"])
        self.assertEqual(pop_body["action"], "pop")
        self.assertEqual(pop_body["map_key"], FIXTURE_MAP_KEY)
        # The pop's PREVIOUS row is the row the recorded push produced - up to the
        # one documented, time-dependent wall-clock stamp, which the replay
        # re-stamps with its own.
        kept, skipped = pruned_differences(
            FIXTURE["pop"]["before"]["maps"][0]["items"][str(FIXTURE_MAP_KEY)],  # type: ignore[index]
            pop_body["previous"],
            PRUNED_ROW_POINTER,
        )
        self.assertEqual(kept, [], "the pop's previous row matches the recorded push")
        self.assertEqual(skipped, [PRUNED_ROW_POINTER])
        # The three-key teardown, verbatim.
        self.assertEqual(pop_body["row"][6], {})
        self.assertEqual(
            pop_body["queue"],
            {
                "present": False,
                "count": None,
                "start_instant": None,
                "queued_unit_id": None,
                "keys": [],
                "absent_is_absent": True,
            },
        )
        self.assertEqual(pop_body["row"][0], FIXTURE_ITEM)
        self.assertEqual(pop_body["row"][1:6], [51, 41, 0, 0, []])
        self.assertEqual(pop_body["resources"], COMMITTED_RESOURCES)
        # The pop's after-state is the SEED, byte for byte, with no prune at all -
        # the strongest form of the round-trip claim.
        raw_after_pop = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(
            leaf_differences(FIXTURE["pop"]["after"], raw_after_pop), []
        )
        self.assertEqual(
            harness.read_seeded_save(CORPUS), harness.load_seed()  # type: ignore[arg-type]
        )
        # No balance moved at all, which is what the second proof half asserts.
        self.assertEqual(
            {
                name: raw_after_pop["maps"][0].get(name, 0)  # type: ignore[index]
                - FIXTURE["push"]["before"]["maps"][0].get(name, 0)  # type: ignore[index]
                for name in ("gold", "wood", "oil", "steel")
            },
            {"gold": 0, "wood": 0, "oil": 0, "steel": 0},
        )
        self.assertEqual(
            raw_after_pop["playerInfo"]["cash"],  # type: ignore[index]
            FIXTURE["push"]["before"]["playerInfo"]["cash"],  # type: ignore[index]
        )
        self.assertEqual(
            raw_after_pop["privateState"]["mana"],  # type: ignore[index]
            FIXTURE["push"]["before"]["privateState"]["mana"],  # type: ignore[index]
        )
        # Nothing left the corpus: the round trip restored the seed exactly.
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_c_the_replay_leaves_no_surviving_queue(self) -> None:
        """After the recorded pair the corpus is byte-identical to the seed, so the
        replay's own follow-up state is the seed - and a third pop on it is the
        recorded inert no-op, which is asserted rather than assumed."""
        self.assertEqual(harness.read_seeded_save(CORPUS), harness.load_seed())
        response = queue_now({"user_id": PID, "map_key": FIXTURE_MAP_KEY, "action": "pop"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["result"], "success")
        self.assertFalse(body["queue"]["present"])
        self.assertIsNone(body["queue"]["count"])
        self.assertEqual(body["row"][6], {})
        self.assertEqual(
            harness.read_seeded_save(CORPUS), harness.load_seed()
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class QueueParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket, no working-tree write."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        for step in (LOGIN_STEP, PUSH_STEP, POP_STEP):
            with self.subTest(step=step):
                self.assertTrue((FIXTURES / "steps" / step / "request.json").is_file())
                self.assertTrue((FIXTURES / "steps" / step / "before.json").is_file())
                self.assertTrue((FIXTURES / "steps" / step / "after.json").is_file())

    def test_the_fixture_readme_states_the_provenance_split_and_the_claims(self) -> None:
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn('{"result":"success"}', readme)
        self.assertIn("**Established from committed legacy source**", readme)
        self.assertIn(
            "**Derived and never observed from the Flash client**", readme
        )
        # The recorded pair, verbatim.
        self.assertIn('[[0,"push_queue_unit",[1],[0,0,0,0,0,0,0,0]]]', readme)
        self.assertIn('[[0,"pop_queue_unit",[1],[0,0,0,0,0,0,0,0]]]', readme)
        self.assertIn("[0, 0, 0, 0, 0, 0, 0, 0]", readme)
        # The probe.
        self.assertIn("Probe 1", readme)
        self.assertIn("push_queue_unit([1])", readme)
        self.assertIn("[0, 500, 0, 0, 0, 0, 0, 0]", readme)
        # The decisions.
        for name in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"):
            with self.subTest(decision=name):
                self.assertIn("**%s**" % name, readme)
        # The structural absences.
        self.assertIn("A push and a pop were captured.", readme)
        self.assertIn("**63 named branches**", readme)
        self.assertIn("complete_collection", readme)
        self.assertIn("complete_goal", readme)
        self.assertIn("complete_tutorial", readme)
        self.assertIn("completes a queue", readme)
        self.assertIn("about a finished queue", readme)
        self.assertIn("readiness", readme)
        self.assertIn("no count bound", readme.lower())
        self.assertIn("TOGETHER", readme)
        self.assertIn("Quite useless cost calculation for understanding it", readme)
        self.assertIn("push_queue_unit2", readme)
        # The recorded outcome.
        self.assertIn("**id 26, Command Center, at map key `1`**", readme)
        self.assertIn("`training_time` 5", readme)
        self.assertIn("`min_level` 1", readme)
        self.assertIn("stays **`40`**", readme)
        self.assertIn("`xp 4`, `gold 2000`", readme)
        self.assertIn("`playerInfo.cash 5`, `privateState.mana 0`", readme)
        self.assertIn("the **seed** byte-for-byte", readme)
        # The containment count and the closure claims.
        self.assertIn("**ten** committed", readme)
        self.assertIn("No Flash, Ruffle, ActionScript, or browser", readme)
        self.assertIn("no network beyond", readme)
        self.assertIn("No **pixel-parity oracle**", readme)
        self.assertIn("external network was involved", readme)

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "a queue execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()
