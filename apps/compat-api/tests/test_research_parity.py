#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/research`` vs the executed-legacy
research fixture (OpenSpec task 2.3).

No server and no network: the endpoint runs through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and ``test_no_server_is_running`` asserts that neither the legacy port
(5055) nor the Compatibility API port (5056) is listening.

What is replayed
    The committed transaction under ``tests/fixtures/godot-research/`` — all
    **four** legacy research branches over **both** tracks, eight branch-track
    combinations, each carrying the **neutral** vector
    ``[0, 0, 0, 0, 0, 0, 0, 0]``, executed by the legacy server in a disposable
    copy against the fresh-player corpus.  Every counter in that corpus sits at
    ``[0, 0]``, so the set is exercisable with **no fabricated player state**.

    The endpoint derives the very same envelopes from the very same module, so
    the replay compares:

    * the response ``result`` against each captured legacy response body;
    * the response's ``action``, ``track``, and both projections against the
      recorded states — every derived counter by value, the **unaddressed** track
      and every counter the branch does not write by value, and the **stamped
      instant** by the one documented exception below;
    * the response's ``resources`` against the values read from the captured
      after-states — all seven slots are stable and the captured movement is the
      derived neutral vector, which is nothing;
    * the corpus save after each execution against the recorded after-state, leaf
      for leaf, with **exactly one** documented normalization — the research
      instant the step branch stamped from the wall clock;
    * the shared derivation against the recorded request envelopes, exactly (the
    recorded ``ts`` is passed back into the derivation).

The single documented normalization
    ``next_research_step`` writes ``timeStampDoResearch[_type] = time_now``
    (``command.py:272``), so the captured instant is a **wall-clock reading** and
    is the fixture's only time-dependent STATE value (the capture's manifest says
    so and names the four files it appears in).  The replay therefore compares
    that instant by **shape and direction** — present, a non-negative integer, and
    not earlier than the pre-execution one — and compares **everything else by
    value**.  That is the only pruning in this suite, and it is asserted rather
    than assumed: the comparison helper reports which pointers it skipped and the
    test asserts the skipped set is exactly the recorded ones.

The parity claim covers the eight recorded transactions against the
fresh-player corpus (see the fixture README's claim limits).  In particular the
fixture evidences the **four counter transitions only**: the counters are
write-only, so nothing about a ready step, a completed item, a remaining time,
or a reward is evidenced, and the manifest records that absence.
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
import research_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-research"
LOGIN_STEP = "login_post"
#: The eight captured branch-track combinations, in the order they execute.
STEP_NAMES = [
    "command_next_research_step_track_0",
    "command_next_research_step_track_1",
    "command_research_buy_step_cash_track_0",
    "command_research_buy_step_cash_track_1",
    "command_next_research_item_track_0",
    "command_next_research_item_track_1",
    "command_reset_research_item_track_0",
    "command_reset_research_item_track_1",
]
EXPECTED_ACTIONS = {
    "command_next_research_step_track_0": ("next_step", 0),
    "command_next_research_step_track_1": ("next_step", 1),
    "command_research_buy_step_cash_track_0": ("buy_step_cash", 0),
    "command_research_buy_step_cash_track_1": ("buy_step_cash", 1),
    "command_next_research_item_track_0": ("next_item", 0),
    "command_next_research_item_track_1": ("next_item", 1),
    "command_reset_research_item_track_0": ("reset_item", 0),
    "command_reset_research_item_track_1": ("reset_item", 1),
}
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
#: The pointer the comparison prunes **inside the counter vector**: the step
#: branch's wall-clock stamp.  This is the fixture's only time-dependent state
#: value at vector level.
PRUNED_VECTOR_POINTER = "/timeStampDoResearch/%d"
#: The same pointer relative to a whole save document.
PRUNED_SAVE_POINTER = "/privateState/timeStampDoResearch/%d"

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
    fixture: Dict[str, Any] = {"login": load_step(LOGIN_STEP)}
    for name in STEP_NAMES:
        step = load_step(name)
        data = step["request"]["form"]["data"]
        envelope = research_envelope.parse_data_field(data)
        entry = envelope["commands"][0]
        action, track = EXPECTED_ACTIONS[name]
        step["envelope"] = envelope
        step["action"] = action
        step["track"] = track
        step["command"] = entry[1]
        step["map_id"] = entry[0]
        step["args"] = entry[2]
        step["vector"] = entry[3]
        step["vector_before"] = research_envelope.snapshot_counters(step["before"])
        step["vector_after"] = research_envelope.snapshot_counters(step["after"])
        fixture[name] = step
    fixture["manifest"] = json.loads(
        (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
    )
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
        raise AssertionError("a research execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def reset_vector(name: str = STEP_NAMES[0]) -> Dict[str, List[int]]:
    """Reset the disposable corpus to the given recorded step's before-state.

    Each recorded transaction is replayed on its OWN recorded before-state, which
    is how an eight-step recording stays replayable: the suite puts the corpus
    back to the exact state the recording says the step started from, then posts
    the step's intent.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    template = FIXTURE[name]["before"]
    save["privateState"] = json.loads(json.dumps(template["privateState"]))
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")
    return research_envelope.snapshot_counters(save)


def research_now(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/research", json=payload)  # type: ignore[union-attr]


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
    expected: Any, actual: Any, pruned: List[str]
) -> Tuple[List[str], List[str]]:
    """Every differing leaf, split into the pruned ones and the kept ones.

    Both lists are returned so the prune is **asserted**, not assumed.
    """
    differing = leaf_differences(expected, actual)
    skipped = [pointer for pointer in differing if pointer in pruned]
    kept = [pointer for pointer in differing if pointer not in pruned]
    return kept, skipped


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_the_first_recorded_before_state_is_the_committed_seed(self) -> None:
        self.assertEqual(FIXTURE[STEP_NAMES[0]]["before"], harness.load_seed())
        # Every later step's before-state is the previous step's after-state, so
        # the eight steps are ONE recorded transaction.
        for index in range(1, len(STEP_NAMES)):
            with self.subTest(step=STEP_NAMES[index]):
                self.assertEqual(
                    FIXTURE[STEP_NAMES[index]]["before"],
                    FIXTURE[STEP_NAMES[index - 1]]["after"],
                )
        # The login step left the corpus untouched.
        self.assertEqual(FIXTURE["login"]["after"], FIXTURE["login"]["before"])

    def test_all_eight_branch_track_combinations_are_recorded(self) -> None:
        self.assertEqual(len(STEP_NAMES), 8)
        self.assertEqual(
            sorted(FIXTURE["manifest"]["transactions"],
                   key=lambda entry: (entry["action"], entry["track"])),
            sorted(FIXTURE["manifest"]["transactions"],
                   key=lambda entry: (entry["action"], entry["track"])),
        )
        self.assertEqual(len(FIXTURE["manifest"]["transactions"]), 8)
        self.assertEqual(
            sorted((entry["command"], entry["track"])
                   for entry in FIXTURE["manifest"]["transactions"]),
            sorted(
                (research_envelope.ACTION_COMMANDS[action], track)
                for action, track in EXPECTED_ACTIONS.values()
            ),
        )
        self.assertEqual(FIXTURE["manifest"]["captured"]["combinations"], 8)
        self.assertEqual(
            FIXTURE["manifest"]["captured"]["combination_count_expected"],
            research_envelope.CAPTURED_COMBINATIONS,
        )
        for command in ("next_research_step", "research_buy_step_cash",
                        "next_research_item", "reset_research_item"):
            with self.subTest(command=command):
                self.assertTrue(FIXTURE["manifest"]["captured"][command])
        self.assertTrue(FIXTURE["manifest"]["captured"]["both_tracks"])

    def test_the_recorded_envelopes_are_exactly_the_shared_derivation(self) -> None:
        for name in STEP_NAMES:
            with self.subTest(step=name):
                step = FIXTURE[name]
                envelope = step["envelope"]
                # The one time-dependent input: a positive integer, held fixed
                # here.  It is an envelope field legacy parses and never reads.
                self.assertIsInstance(envelope["ts"], int)
                self.assertGreater(envelope["ts"], 0)
                rebuilt = research_envelope.build_envelope(
                    track=step["track"], action=step["action"], ts=envelope["ts"]
                )
                self.assertEqual(rebuilt, envelope)
                self.assertEqual(
                    sorted(rebuilt), sorted(research_envelope.ENVELOPE_KEYS)
                )
                self.assertEqual(len(envelope["commands"]), 1)
                self.assertEqual(step["map_id"], 0)
                self.assertEqual(
                    step["command"],
                    research_envelope.ACTION_COMMANDS[step["action"]],
                )
                expected_args = [step["track"]]
                if step["action"] == research_envelope.CASH_ACTION:
                    expected_args = [research_envelope.DERIVED_CASH, step["track"]]
                self.assertEqual(step["args"], expected_args)
                # Every slot is zero: a research action moves no resource.
                self.assertEqual(step["vector"], FIXTURE_EXPECTED_VECTOR)
                self.assertEqual(step["vector"], research_envelope.neutral_vector())
                self.assertEqual(
                    step["request"]["form"]["USERID"], PID
                )

    def test_the_cash_branch_sent_the_derived_zero_not_a_client_price(self) -> None:
        for name in ("command_research_buy_step_cash_track_0",
                     "command_research_buy_step_cash_track_1"):
            with self.subTest(step=name):
                step = FIXTURE[name]
                self.assertEqual(step["args"][0], 0)
                self.assertEqual(step["args"][0], research_envelope.DERIVED_CASH)

    def test_the_recorded_responses_are_the_legacy_result(self) -> None:
        for name in STEP_NAMES:
            with self.subTest(step=name):
                self.assertEqual(json.loads(FIXTURE[name]["body"]),
                                 {"result": "success"})
                self.assertEqual(FIXTURE[name]["meta"]["status"], 200)

    def test_the_recorded_vectors_show_the_four_documented_effects(self) -> None:
        expected = {
            "command_next_research_step_track_0": (
                {"researchStepNumber": [1, 0], "researchItemNumber": [0, 0]},
                "timeStampDoResearch", 0, True,
            ),
            "command_next_research_step_track_1": (
                {"researchStepNumber": [1, 1], "researchItemNumber": [0, 0]},
                "timeStampDoResearch", 1, True,
            ),
            "command_research_buy_step_cash_track_0": (
                {"researchStepNumber": [1, 1], "researchItemNumber": [0, 0]},
                "timeStampDoResearch", 0, False,
            ),
            "command_research_buy_step_cash_track_1": (
                {"researchStepNumber": [1, 1], "researchItemNumber": [0, 0]},
                "timeStampDoResearch", 1, False,
            ),
            "command_next_research_item_track_0": (
                {"researchStepNumber": [0, 1], "researchItemNumber": [1, 0]},
                "timeStampDoResearch", 0, False,
            ),
            "command_next_research_item_track_1": (
                {"researchStepNumber": [0, 0], "researchItemNumber": [1, 1]},
                "timeStampDoResearch", 1, False,
            ),
            "command_reset_research_item_track_0": (
                {"researchStepNumber": [0, 0], "researchItemNumber": [0, 1]},
                "timeStampDoResearch", 0, False,
            ),
            "command_reset_research_item_track_1": (
                {"researchStepNumber": [0, 0], "researchItemNumber": [0, 0]},
                "timeStampDoResearch", 1, False,
            ),
        }
        for name in STEP_NAMES:
            with self.subTest(step=name):
                after = FIXTURE[name]["vector_after"]
                counters, instant_key, instant_track, stamped = expected[name]
                for key, value in counters.items():
                    self.assertEqual(after[key], value)
                instant = after[instant_key][instant_track]
                if stamped:
                    self.assertGreater(instant, 0)
                else:
                    self.assertEqual(instant, 0)

    def test_the_item_branchs_paired_reset_is_visible_in_the_recorded_state(self) -> None:
        """The step counter and the instant are reset TOGETHER.

        The recorded order is step, step, cash, cash, item, item, reset, reset —
        exactly eight steps for eight branch-track combinations — so the two cash
        steps have already zeroed both instants by the time the item steps run.
        The item branch's **step** half is therefore a real transition (1 -> 0)
        and its **instant** half is 0 -> 0.  That is recorded rather than papered
        over: the capture's manifest says so in
        ``transaction.transition_visibility``, and the pairing itself is
        established by the committed source (``command.py:287-289`` writes all
        three keys with no branch between them) rather than by this transition.
        """
        for name in ("command_next_research_item_track_0",
                     "command_next_research_item_track_1"):
            with self.subTest(step=name):
                step = FIXTURE[name]
                track = step["track"]
                self.assertEqual(step["vector_before"]["researchStepNumber"][track],
                                 1, "a step really was in flight")
                self.assertEqual(step["vector_after"]["researchStepNumber"][track], 0)
                self.assertEqual(step["vector_after"]["timeStampDoResearch"][track], 0)
                self.assertEqual(
                    step["vector_after"]["researchItemNumber"][track],
                    step["vector_before"]["researchItemNumber"][track] + 1,
                )
                self.assertEqual(leaf_differences(step["before"], step["after"]),
                                 ["/privateState/researchItemNumber/%d" % track,
                                  "/privateState/researchStepNumber/%d" % track])
        visibility = FIXTURE["manifest"]["transaction"]["transition_visibility"]
        self.assertTrue(visibility["item_step_instant_was_already_zero"])
        self.assertTrue(visibility["every_other_transition_observable"])
        self.assertIn("0 -> 0", visibility["rule"])
        self.assertIn("command.py:287-289", visibility["rule"])

    def test_the_cash_branch_touched_only_the_instant(self) -> None:
        for name in ("command_research_buy_step_cash_track_0",
                     "command_research_buy_step_cash_track_1"):
            with self.subTest(step=name):
                step = FIXTURE[name]
                track = step["track"]
                self.assertEqual(
                    step["vector_before"]["researchStepNumber"],
                    step["vector_after"]["researchStepNumber"],
                )
                self.assertEqual(
                    step["vector_before"]["researchItemNumber"],
                    step["vector_after"]["researchItemNumber"],
                )
                self.assertGreater(
                    step["vector_before"]["timeStampDoResearch"][track], 0
                )
                self.assertEqual(step["vector_after"]["timeStampDoResearch"][track], 0)

    def test_the_eight_steps_round_trip_byte_for_byte_to_the_seed(self) -> None:
        self.assertEqual(FIXTURE[STEP_NAMES[-1]]["after"], FIXTURE[STEP_NAMES[0]]["before"])
        self.assertEqual(
            (FIXTURES / "steps" / STEP_NAMES[-1] / "after.json").read_bytes(),
            (FIXTURES / "steps" / STEP_NAMES[0] / "before.json").read_bytes(),
        )

    def test_no_placement_storage_or_player_field_moved(self) -> None:
        seed = harness.load_seed()
        for name in STEP_NAMES:
            with self.subTest(step=name):
                before = FIXTURE[name]["before"]
                after = FIXTURE[name]["after"]
                self.assertEqual(sorted(after["maps"][0]["items"], key=int),
                                 sorted(before["maps"][0]["items"], key=int))
                self.assertEqual(len(after["maps"][0]["items"]), 40)
                for key in before["maps"][0]["items"]:
                    with self.subTest(step=name, key=key):
                        self.assertEqual(after["maps"][0]["items"][key],
                                         before["maps"][0]["items"][key])
                self.assertEqual(after["maps"][0]["store"], seed["maps"][0]["store"])
                self.assertEqual(after["playerInfo"], seed["playerInfo"])
                self.assertNotIn("map_sizes", after["maps"][0])
                # The private state outside the three counters is byte-identical.
                for key in after["privateState"]:
                    if key in research_envelope.COUNTERS:
                        continue
                    with self.subTest(step=name, field=key):
                        self.assertEqual(after["privateState"][key],
                                         seed["privateState"][key])
                self.assertEqual(sorted(after["privateState"]),
                                 sorted(seed["privateState"]))

    def test_every_stored_resource_is_unchanged_across_all_eight_steps(self) -> None:
        for name in STEP_NAMES:
            with self.subTest(step=name):
                step = FIXTURE[name]
                self.assertEqual(resources_of(step["after"]), COMMITTED_RESOURCES)
                self.assertEqual(resources_of(step["after"]),
                                 resources_of(step["before"]))
        self.assertEqual(
            {
                name: resources_of(FIXTURE[STEP_NAMES[-1]]["after"])[name]
                - resources_of(FIXTURE[STEP_NAMES[0]]["before"])[name]
                for name in FIXTURE_RESOURCE_NAMES
            },
            {name: 0 for name in FIXTURE_RESOURCE_NAMES},
        )

    def test_the_corpus_holds_no_research_counter_on_any_placement(self) -> None:
        seed = harness.load_seed()
        for key, row in seed["maps"][0]["items"].items():
            with self.subTest(key=key):
                self.assertNotIn("research", json.dumps(row).lower())

    def test_the_manifest_records_the_writer_inventory_it_measured(self) -> None:
        manifest = FIXTURE["manifest"]
        self.assertEqual(manifest["instant_writer_count"], 5)
        self.assertEqual(len(manifest["instant_writers"]), 5)
        self.assertEqual(
            [entry["source"] for entry in manifest["instant_writers"]],
            ["command.py:272", "command.py:280", "command.py:289",
             "command.py:298",
             "command.py:923 (read), command.py:927 (write)"],
        )
        self.assertTrue(
            manifest["instant_writers"][4]["client_writable"]
        )
        self.assertFalse(manifest["fast_forward"]["is_a_research_branch"])
        self.assertTrue(manifest["fast_forward"]["clamped"])
        self.assertIn("args[0]", manifest["fast_forward"]["seconds_source"])
        self.assertIn("CLIENT-SUPPLIED", manifest["fast_forward"]["seconds_source"])
        self.assertFalse(manifest["fast_forward"]["implemented"])

    def test_the_manifest_records_no_completion_and_no_readiness(self) -> None:
        captured = FIXTURE["manifest"]["captured"]
        self.assertFalse(captured["completion"])
        self.assertFalse(captured["completion_captured"])
        self.assertFalse(captured["completion_command_exists"])
        self.assertFalse(captured["readiness_captured"])
        self.assertIn("NO COMPLETION AND NO READINESS WERE CAPTURED",
                      captured["note"])
        absent = captured["no_server_side_completion"]
        self.assertEqual(absent["research_step_sites"], 3)
        self.assertTrue(absent["research_step_sites_all_writes"])
        self.assertEqual(absent["research_item_sites"], 2)
        self.assertTrue(absent["research_item_sites_all_writes"])
        self.assertEqual(absent["research_instant_sites"], 5)
        self.assertEqual(absent["instant_writer_count"], 5)
        self.assertFalse(absent["fast_forward_is_a_research_branch"])
        self.assertTrue(absent["fast_forward_seconds_client_supplied"])
        self.assertIsNone(absent["research_completion_command"])
        self.assertIsNone(absent["research_readiness_command"])
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertFalse(transaction["reward_paid"])
        self.assertFalse(transaction["price_computed"])
        self.assertFalse(transaction["readiness_computed"])
        self.assertFalse(transaction["counter_bound_applied"])
        self.assertTrue(transaction["round_trip_to_seed"])
        self.assertIn("NO price is computed", transaction["price_note"])
        self.assertIn("NO maximum, clamp, or membership rule",
                      transaction["counter_bound_note"])

    def test_the_manifest_records_the_three_probes_it_actually_executed(self) -> None:
        probes = FIXTURE["manifest"]["probes"]
        self.assertEqual(len(probes), 3)
        for probe in probes:
            with self.subTest(probe=probe["probe"]):
                self.assertTrue(probe["executed_in_this_capture"])
                self.assertNotEqual(probe["why_it_matters"].strip(), "")
        # Probe 1 is the evidence for the no-price claim: the branch was handed
        # cash 250 and playerInfo.cash did not move, while the client-sent
        # experience slot did.
        first = probes[0]
        self.assertEqual(first["cash_argument_sent"], 250)
        self.assertEqual(first["cash_before"], 5)
        self.assertEqual(first["cash_after"], 5)
        self.assertEqual(first["cash_moved"], 0)
        self.assertEqual(first["xp_before"], 4)
        self.assertEqual(first["xp_after"], 504)
        self.assertEqual(first["changed_top_level_map_keys"], ["xp"])
        self.assertEqual(first["leaf_differences"], ["/maps/0/xp"])
        self.assertTrue(first["other_resources_unchanged"])
        self.assertIn("DISCARDED", first["established"])
        # Probe 2 establishes the fourth writer's exact client-supplied decrement.
        second = probes[1]
        self.assertEqual(second["seconds_sent"], 60)
        self.assertEqual(
            second["instant_after"],
            max(0, second["instant_before"] - 60),
        )
        self.assertEqual(second["step_after"], second["step_before"])
        self.assertEqual(second["item_after"], second["item_before"])
        self.assertTrue(second["other_track_instant_unchanged"])
        # Probe 3 establishes the clamp.
        third = probes[2]
        self.assertEqual(third["seconds_sent"], 9999999999)
        self.assertTrue(third["clamped"])
        self.assertEqual(third["instant_after"], 0)
        self.assertTrue(third["step_unchanged"])
        self.assertTrue(third["item_unchanged"])

    def test_the_manifest_records_the_measured_content_findings(self) -> None:
        content = FIXTURE["manifest"]["content"]
        self.assertEqual(content["normalized_files"], 22)
        # MEASURED CORRECTION: TWO normalized files, not one.
        self.assertEqual(
            content["normalized_files_containing_research"],
            {"buildings.json": 1, "images.json": 6},
        )
        self.assertEqual(content["normalized_files_containing_research_count"], 2)
        # MEASURED CORRECTION: three /images keys DO contain the word.
        self.assertEqual(content["config_keys_containing_research_count"], 3)
        self.assertEqual(
            content["config_keys_containing_research"],
            [
                "/images/popupResearchCenter_buildingProcess.swf",
                "/images/popupResearchCenter_buildingProcess_2.swf",
                "/images/popupResearchCenter_buildingProcess_3.swf",
            ],
        )
        self.assertIn("MEASURED CORRECTION", content["note"])

    def test_the_manifest_records_the_tracks_and_the_paired_reset(self) -> None:
        tracks = FIXTURE["manifest"]["tracks"]
        self.assertEqual(
            [(record["track"], record["name"], record["building_id"])
             for record in tracks],
            [(0, "TYPE_AREA_51", 139), (1, "TYPE_ROBOTIC", 86)],
        )
        self.assertIn("REPORTED AND NEVER USED", FIXTURE["manifest"]["track_note"])
        self.assertEqual(FIXTURE["manifest"]["branch_count"], 4)
        paired = [
            record for record in FIXTURE["manifest"]["command_contract"]
            if record["command"] == "next_research_item"
        ][0]
        self.assertTrue(paired["paired_reset"])
        cash = [
            record for record in FIXTURE["manifest"]["command_contract"]
            if record["command"] == "research_buy_step_cash"
        ][0]
        self.assertTrue(cash["reads_a_price"])
        self.assertFalse(cash["charges"])
        self.assertEqual(cash["argument_order"], "cash-then-track")

    def test_the_manifest_states_the_containment_it_verified(self) -> None:
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertEqual(containment["pre_combined_sha256"],
                         containment["post_combined_sha256"])
        self.assertTrue(containment["working_tree_saves_unchanged"])
        self.assertTrue(containment["protected_fixtures"]["identical"])
        self.assertTrue(containment["loopback_only"])
        self.assertTrue(containment["no_flash_browser_external_network"])
        self.assertEqual(len(containment["protected_fixtures"]["paths"]), 13)


class ReplayTests(unittest.TestCase):
    """Each recorded transaction replayed against the endpoint."""

    def test_each_recorded_step_replays_to_the_recorded_post_state(self) -> None:
        for name in STEP_NAMES:
            with self.subTest(step=name):
                step = FIXTURE[name]
                before = reset_vector(name)
                self.assertEqual(before, step["vector_before"])
                response = research_now({
                    "user_id": PID,
                    "action": step["action"],
                    "track": step["track"],
                })
                self.assertEqual(response.status_code, 200)
                body = response.get_json()
                self.assertTrue(body["ok"])
                self.assertEqual(body["result"], "success")
                self.assertEqual(body["action"], step["action"])
                self.assertEqual(body["track"], step["track"])
                self.assertEqual(body["command"], step["command"])
                # The service's own before-snapshot is the recorded before-state.
                self.assertEqual(body["previous"]["counters"],
                                 step["vector_before"])
                # The persisted after-state matches the recorded one, with the
                # instant compared by SHAPE and DIRECTION only.
                persisted = research_envelope.snapshot_counters(
                    BOOT.save_document(PID)  # type: ignore[union-attr]
                )
                divergence = research_envelope.expected_state(
                    step["vector_before"], step["action"], step["track"], persisted
                )
                self.assertIsNone(divergence, divergence)
                pruned = [
                    PRUNED_VECTOR_POINTER % track
                    for track in (0, 1)
                    if derived_diffs(step, persisted, track)
                ]
                kept, skipped = pruned_differences(
                    step["vector_after"], persisted, pruned
                )
                self.assertEqual(kept, [])
                self.assertEqual(sorted(skipped), sorted(pruned))
                # A step whose recorded instants both match replays EXACTLY.
                if not pruned:
                    self.assertEqual(persisted, step["vector_after"])
                # The projection the service reports carries an EMPTY derived
                # block: nothing is computed from the counters.
                self.assertEqual(body["research"]["derived"], {})
                self.assertEqual(body["research"]["counters"], persisted)
                self.assertEqual(body["resources"], COMMITTED_RESOURCES)
                self.assertEqual(body["cash_charged"], 0)

    def test_the_whole_save_replays_with_the_one_documented_prune(self) -> None:
        """Whole-document comparison, pruned at exactly the recorded pointers."""
        for name in STEP_NAMES:
            with self.subTest(step=name):
                step = FIXTURE[name]
                reset_vector(name)
                response = research_now({
                    "user_id": PID,
                    "action": step["action"],
                    "track": step["track"],
                })
                self.assertEqual(response.status_code, 200, name)
                document = BOOT.save_document(PID)  # type: ignore[union-attr]
                persisted = research_envelope.snapshot_counters(document)
                pruned = [
                    PRUNED_SAVE_POINTER % track
                    for track in (0, 1)
                    if derived_diffs(step, persisted, track)
                ]
                kept, skipped = pruned_differences(step["after"], document, pruned)
                self.assertEqual(kept, [], "%s differs beyond the prune" % name)
                self.assertEqual(sorted(skipped), sorted(pruned))

    def test_the_replayed_eight_steps_move_no_stored_resource(self) -> None:
        for name in STEP_NAMES:
            step = FIXTURE[name]
            reset_vector(name)
            response = research_now({
                "user_id": PID,
                "action": step["action"],
                "track": step["track"],
            })
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response.get_json()["resources"],
                             COMMITTED_RESOURCES, name)
        reset_vector(STEP_NAMES[0])
        self.assertEqual(
            research_envelope.snapshot_counters(BOOT.save_document(PID)),  # type: ignore[union-attr]
            research_envelope.COMMITTED_VECTOR,
        )
        # …and replaying the LAST step on its own recorded before-state lands on
        # the committed seed again, which is the recorded round trip.
        last = FIXTURE[STEP_NAMES[-1]]
        reset_vector(STEP_NAMES[-1])
        response = research_now({
            "user_id": PID, "action": last["action"], "track": last["track"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            research_envelope.snapshot_counters(BOOT.save_document(PID)),  # type: ignore[union-attr]
            research_envelope.COMMITTED_VECTOR,
        )

    def test_a_client_supplied_counter_timestamp_and_cash_are_ignored(self) -> None:
        step = FIXTURE["command_next_research_step_track_0"]
        reset_vector()
        response = research_now({
            "user_id": PID,
            "action": step["action"],
            "track": step["track"],
            "step": 999, "item": 999, "timestamp": 1, "instant": 1, "cash": 2500,
            "price": 2500, "cost": 2500, "remaining": 42, "ready": True,
            "step_count": 999, "reward": "gold", "seconds": 9999999,
            "resources_changed": [0, 0, -2500, 0, 0, 0, 0, 0],
        })
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["previous"]["counters"], step["vector_before"])
        self.assertEqual(body["resources"], COMMITTED_RESOURCES)
        for key in ("step", "item", "timestamp", "instant", "cash", "price",
                    "cost", "remaining", "ready", "step_count", "reward",
                    "seconds", "resources_changed"):
            with self.subTest(key=key):
                self.assertNotIn(key, body)

    def test_the_cash_branch_is_replayed_with_a_client_cash_and_charges_nothing(
        self,
    ) -> None:
        step = FIXTURE["command_research_buy_step_cash_track_0"]
        reset_vector("command_research_buy_step_cash_track_0")
        self.assertGreater(step["vector_before"]["timeStampDoResearch"][0], 0)
        response = research_now({
            "user_id": PID, "action": "buy_step_cash", "track": 0,
            "cash": 999999,
        })
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        # The client's cash was ignored: the only cash figure is the derived 0.
        self.assertEqual(body["cash_charged"], 0)
        self.assertTrue(body["cash_argument_ignored"])
        self.assertFalse(body["price_computed"])
        self.assertEqual(body["resources"], COMMITTED_RESOURCES)
        persisted = research_envelope.snapshot_counters(
            BOOT.save_document(PID)  # type: ignore[union-attr]
        )
        self.assertEqual(persisted["timeStampDoResearch"][0], 0)
        self.assertEqual(persisted["researchStepNumber"],
                         step["vector_before"]["researchStepNumber"])
        self.assertEqual(persisted["researchItemNumber"],
                         step["vector_before"]["researchItemNumber"])

    def test_a_refused_intent_leaves_the_vector_byte_identical(self) -> None:
        before = reset_vector()
        for payload, status, code in (
            ({"user_id": PID, "action": "next_step", "track": "0"}, 400,
             "invalid_track"),
            ({"user_id": PID, "action": "next_step", "track": 7}, 400,
             "invalid_track"),
            ({"user_id": PID, "action": "fast_forward", "track": 0,
              "seconds": 60}, 400, "invalid_action"),
        ):
            with self.subTest(payload=payload):
                response = research_now(payload)
                self.assertEqual(response.status_code, status)
                body = response.get_json()
                self.assertEqual(body["error"]["code"], code)
                self.assertEqual(sorted(body), ["error", "ok", "protocol"])
                self.assertEqual(
                    research_envelope.snapshot_counters(
                        BOOT.save_document(PID)  # type: ignore[union-attr]
                    ),
                    before,
                )

    def test_the_working_tree_save_did_not_move(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(harness.port_is_free("127.0.0.1", port), port)


def derived_diffs(step: Dict[str, Any], persisted: Dict[str, List[int]],
                  track: int) -> bool:
    """Whether one track's research instant differs from the recorded value."""
    return (
        persisted["timeStampDoResearch"][track]
        != step["vector_after"]["timeStampDoResearch"][track]
    )


if __name__ == "__main__":
    unittest.main()
