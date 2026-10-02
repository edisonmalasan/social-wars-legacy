#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/quests`` vs the executed-legacy quest
fixture (OpenSpec task 5.2).

No server and no network: the endpoint runs through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and ``test_no_server_is_running`` asserts that neither the legacy port
(5055) nor the Compatibility API port (5056) is listening.

What is replayed
    The committed transaction under ``tests/fixtures/godot-quests/`` — **all six**
    legacy quest branches, each carrying the **neutral** vector
    ``[0, 0, 0, 0, 0, 0, 0, 0]``, executed by the legacy server in a disposable
    copy against the fresh-player corpus.  The committed corpus holds every quest
    field at its **initial** value, so the set is exercisable with **no
    fabricated player state** and this line records **no** absent fixture.

    The endpoint derives the very same envelopes from the very same module, so
    the replay compares:

    * the response ``result`` against each captured legacy response body;
    * the response's ``action``, ``command``, ``addressing``, and both
      projections against the recorded states — every derived value by value,
      every **untouched** quest field by value, and the two wall-clock stamps by
      the one documented exception below;
    * the response's ``resources`` against the values read from the captured
      after-states — all seven slots are stable and the captured movement is the
      derived neutral vector, which is nothing;
    * the corpus save after each execution against the recorded after-state, leaf
      for leaf, with exactly the two documented normalizations;
    * **every placed row** against the recorded after-state, over the COMPLETE
      ``items`` mapping, which is what proves the refused destruction count
      stayed refused through a real replay;
    * the shared derivation against the recorded request envelopes, exactly (the
      recorded ``ts`` is passed back into the derivation).

The two documented normalizations
    ``collect_mission`` writes ``timestampLastChapter = time_now``
    (``command.py:439``) and ``end_quest`` writes
    ``questTimes[str(quest_id)] = time_now`` (``command.py:802``), so those two
    captured values are **wall-clock readings** and are the fixture's only
    time-dependent STATE values (its manifest says so and names the files they
    appear in).  The replay therefore compares them by **shape and direction** —
    present, a non-negative integer, and not earlier than the pre-execution one —
    and compares **everything else by value**.  Those are the only two prunes in
    this suite, and they are asserted rather than assumed: the comparison helper
    reports which pointers it skipped and the tests assert the skipped set is
    exactly the recorded ones.

The parity claim covers the six recorded transactions against the
fresh-player corpus (see the fixture README's claim limits).  It evidences the
**quest-state transitions only**: no reward, no completion, no destruction, no
elapsed-time rule, and no quest-timing semantics is evidenced, and the manifest
records each of those absences.
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
import quest_envelope as envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-quests"
LOGIN_STEP = "login_post"
#: The six captured branches, in the order they execute.
STEP_NAMES = [
    "command_set_goals",
    "command_complete_goal",
    "command_set_quest_var",
    "command_collect_mission",
    "command_admin_set_quest_rank",
    "command_end_quest",
]
EXPECTED_ACTIONS: Dict[str, Any] = {
    "command_set_goals": (envelope.ACTION_SET_GOAL, 2),
    "command_complete_goal": (envelope.ACTION_COMPLETE_GOAL, 2),
    "command_set_quest_var": (envelope.ACTION_SET_QUEST_VAR, "spawned"),
    "command_collect_mission": (envelope.ACTION_COLLECT_MISSION, 5),
    "command_admin_set_quest_rank": (envelope.ACTION_SET_QUEST_RANK, 3),
    "command_end_quest": (envelope.ACTION_END_QUEST, 7),
}
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")
#: The two pointer PREFIXES the whole-save comparison prunes, and nothing else.
PRUNED_CHAPTER_PREFIX = "/maps/0/timestampLastChapter"
PRUNED_QUEST_TIMES_PREFIX = "/maps/0/questTimes/"
PRUNED_PREFIXES = (PRUNED_CHAPTER_PREFIX, PRUNED_QUEST_TIMES_PREFIX)

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
APP = None
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
        parsed = envelope.parse_data_field(data)
        entry = parsed["commands"][0]
        action, addressing = EXPECTED_ACTIONS[name]
        step["envelope"] = parsed
        step["action"] = action
        step["addressing"] = addressing
        step["command"] = entry[1]
        step["map_id"] = entry[0]
        step["args"] = entry[2]
        step["vector"] = entry[3]
        step["quest_before"] = envelope.snapshot_state(step["before"])
        step["quest_after"] = envelope.snapshot_state(step["after"])
        fixture[name] = step
    fixture["manifest"] = json.loads(
        (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
    )
    return fixture


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, APP, PID, WORKING_TREE_PRE, FIXTURE
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
        raise AssertionError("a quest execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def reset_state(name: str = STEP_NAMES[0]) -> Dict[str, Any]:
    """Reset the disposable corpus to the given recorded step's before-state.

    Each recorded transaction is replayed on its OWN recorded before-state, which
    is how a six-step recording stays replayable: the suite puts the corpus back
    to the exact state the recording says the step started from, then posts the
    step's intent.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    template = FIXTURE[name]["before"]
    save["privateState"] = json.loads(json.dumps(template["privateState"]))
    save["maps"] = json.loads(json.dumps(template["maps"]))
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")
    return envelope.snapshot_state(save)


def quest_now(payload: Dict[str, Any]) -> Any:
    with harness.offline():
        return CLIENT.post("/v0/quests", json=payload)  # type: ignore[union-attr]


def intent_for(name: str) -> Dict[str, Any]:
    action, addressing = EXPECTED_ACTIONS[name]
    body: Dict[str, Any] = {"user_id": PID, "action": action}
    body[envelope.ACTION_ADDRESSING_KEY[action]] = addressing
    return body


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
    expected: Any, actual: Any, prefixes: Tuple[str, ...] = PRUNED_PREFIXES
) -> Tuple[List[str], List[str]]:
    """Every differing leaf, split into the pruned ones and the kept ones.

    Both lists are returned so the prune is **asserted**, not assumed.
    """
    differing = leaf_differences(expected, actual)
    skipped = [pointer for pointer in differing
               if any(pointer == prefix or pointer.startswith(prefix)
                      for prefix in prefixes)]
    kept = [pointer for pointer in differing if pointer not in skipped]
    return kept, skipped


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_the_first_recorded_before_state_is_the_committed_seed(self) -> None:
        seed = harness.load_seed()
        first = FIXTURE[STEP_NAMES[0]]["before"]
        self.assertEqual(
            envelope.snapshot_state(seed),
            FIXTURE[STEP_NAMES[0]]["quest_before"],
        )
        state = FIXTURE[STEP_NAMES[0]]["quest_before"]
        self.assertEqual(len(state[envelope.KEY_GOALS]),
                         envelope.COMMITTED_GOALS_LENGTH)
        self.assertTrue(all(entry is None for entry in state[envelope.KEY_GOALS]))
        self.assertEqual(state[envelope.KEY_RANKS], {})
        self.assertEqual(state[envelope.KEY_UNLOCKED_INDEX], 0)
        self.assertIsNone(state[envelope.KEY_QUEST_VARS])
        self.assertEqual(state[envelope.KEY_QUEST_TIMES], {})
        self.assertEqual(state[envelope.KEY_MISSION], 0)
        self.assertEqual(state[envelope.KEY_LAST_CHAPTER], 0)
        self.assertEqual(len(first["maps"][0]["items"]),
                         envelope.COMMITTED_PLACEMENTS)

    def test_all_six_branches_are_recorded(self) -> None:
        transactions = FIXTURE["manifest"]["transactions"]
        self.assertEqual(len(transactions), len(STEP_NAMES))
        self.assertEqual(len(transactions), envelope.BRANCH_COUNT)
        self.assertEqual(
            sorted(record["command"] for record in transactions),
            sorted(envelope.QUEST_COMMANDS),
        )
        self.assertEqual(
            sorted(record["action"] for record in transactions),
            sorted(envelope.ACTIONS),
        )

    def test_the_manifest_records_no_absent_fixture(self) -> None:
        captured = FIXTURE["manifest"]["captured"]
        self.assertTrue(captured["no_absent_fixture"])
        for command in envelope.QUEST_COMMANDS:
            self.assertTrue(captured[command], command)
        self.assertFalse(captured["completion_captured"])
        self.assertFalse(captured["completion_state_exists"])
        self.assertFalse(captured["destruction_captured"])
        self.assertFalse(
            captured["destruction_command_survives_in_the_modern_endpoint"])
        self.assertFalse(captured["reward_captured"])

    def test_the_recorded_envelopes_are_exactly_the_shared_derivation(self) -> None:
        for name in STEP_NAMES:
            step = FIXTURE[name]
            rebuilt = envelope.build_envelope(
                action=step["action"], addressing=step["addressing"],
                ts=step["envelope"]["ts"],
            )
            self.assertEqual(rebuilt, step["envelope"], name)
            self.assertEqual(step["vector"], FIXTURE_EXPECTED_VECTOR, name)
            self.assertEqual(step["map_id"], 0, name)
            self.assertEqual(step["command"],
                             envelope.ACTION_COMMANDS[step["action"]], name)

    def test_the_recorded_responses_are_the_legacy_result(self) -> None:
        self.assertEqual(FIXTURE["login"]["meta"]["status"], 302)
        for name in STEP_NAMES:
            body = FIXTURE[name]["body"].decode("utf-8")
            self.assertEqual(json.loads(body), {"result": "success"}, name)
            self.assertEqual(FIXTURE[name]["meta"]["status"], 200, name)

    def test_the_recorded_login_left_the_save_byte_identical(self) -> None:
        self.assertEqual(
            leaf_differences(FIXTURE["login"]["before"],
                             FIXTURE["login"]["after"]),
            [],
        )

    def test_the_recorded_states_show_the_six_documented_effects(self) -> None:
        # 1. the progress pair is the DERIVED one at the addressed index
        goals = FIXTURE["command_set_goals"]["quest_after"][envelope.KEY_GOALS]
        self.assertEqual(goals[2], list(envelope.DERIVED_PROGRESS))
        self.assertEqual(len(goals), envelope.COMMITTED_GOALS_LENGTH)
        self.assertIsNone(goals[3])
        # 2. the no-op branch moved NOTHING
        self.assertEqual(FIXTURE["command_complete_goal"]["quest_before"],
                         FIXTURE["command_complete_goal"]["quest_after"])
        self.assertEqual(FIXTURE["manifest"]["no_op_branch"]["leaves_moved"], 0)
        # 3. the quest-variable map self-healed from None and took the marker
        variables = FIXTURE["command_set_quest_var"]["quest_after"][
            envelope.KEY_QUEST_VARS]
        self.assertIsInstance(variables, dict)
        self.assertEqual(variables, {"spawned": envelope.DERIVED_QUEST_VALUE})
        self.assertIsNone(
            FIXTURE["command_set_quest_var"]["quest_before"][
                envelope.KEY_QUEST_VARS])
        # 4. the chapter branch stringified the mission and cleared the map
        chapter = FIXTURE["command_collect_mission"]["quest_after"]
        self.assertEqual(chapter[envelope.KEY_MISSION], "5")
        self.assertEqual(chapter[envelope.KEY_QUEST_VARS], {})
        self.assertGreater(chapter[envelope.KEY_LAST_CHAPTER], 0)
        # 5. the rank map holds the DERIVED difficulty under the stringified key
        self.assertEqual(
            FIXTURE["command_admin_set_quest_rank"]["quest_after"][
                envelope.KEY_RANKS],
            {"3": envelope.DERIVED_DIFFICULTY},
        )
        # 6. end_quest gained exactly one quest-time entry and nothing else
        times = FIXTURE["command_end_quest"]["quest_after"][envelope.KEY_QUEST_TIMES]
        self.assertEqual(sorted(times), ["7"])
        self.assertGreater(times["7"], 0)

    def test_the_quest_variable_map_key_is_the_recorded_addressing(self) -> None:
        args = FIXTURE["command_set_quest_var"]["args"]
        self.assertEqual(args[0], "spawned")
        self.assertIs(args[1], envelope.DERIVED_QUEST_VALUE)

    def test_the_end_quest_step_carries_an_empty_unit_list(self) -> None:
        blob = json.loads(FIXTURE["command_end_quest"]["args"][0])
        self.assertEqual(blob, envelope.end_quest_blob(7))
        self.assertEqual(blob["units"], [])

    def test_every_placed_row_is_byte_identical_across_all_six_steps(self) -> None:
        for name in STEP_NAMES:
            step = FIXTURE[name]
            before = step["before"]["maps"][0]["items"]
            after = step["after"]["maps"][0]["items"]
            self.assertEqual(len(after), envelope.COMMITTED_PLACEMENTS, name)
            self.assertEqual(sorted(after, key=int), sorted(before, key=int), name)
            for key in before:
                self.assertEqual(after[key], before[key], (name, key))
            self.assertTrue(step["body"])
        self.assertEqual(
            FIXTURE["manifest"]["transaction"]["rows_touched_by_any_step"], 0)

    def test_no_placement_storage_or_player_field_moved(self) -> None:
        for name in STEP_NAMES:
            before = FIXTURE[name]["before"]
            after = FIXTURE[name]["after"]
            self.assertEqual(after["maps"][0]["store"],
                             before["maps"][0]["store"], name)
            self.assertEqual(after["playerInfo"], before["playerInfo"], name)
            self.assertEqual(sorted(after["maps"][0]),
                             sorted(before["maps"][0]), name)
            self.assertEqual(
                after["privateState"][envelope.KEY_UNLOCKED_INDEX],
                before["privateState"][envelope.KEY_UNLOCKED_INDEX], name)

    def test_every_stored_resource_is_unchanged_across_all_six_steps(self) -> None:
        first = FIXTURE[STEP_NAMES[0]]["before"]
        for name in STEP_NAMES:
            self.assertEqual(resources_of(FIXTURE[name]["after"]),
                             resources_of(first), name)
        self.assertEqual(sorted(resources_of(first)),
                         sorted(FIXTURE_RESOURCE_NAMES))
        self.assertEqual(resources_of(first), envelope.COMMITTED_RESOURCE_BEFORE)

    def test_the_manifest_records_the_writer_inventory_it_measured(self) -> None:
        writers = FIXTURE["manifest"]["writers"]
        self.assertEqual(len(writers), envelope.WRITER_COUNT)
        self.assertEqual(len(writers), 7)
        fast = FIXTURE["manifest"]["fast_forward"]
        self.assertTrue(fast["recorded"])
        self.assertFalse(fast["implemented"])
        self.assertTrue(fast["clamped"])
        self.assertFalse(fast["is_a_quest_branch"])
        self.assertIn("CLIENT-SUPPLIED", fast["seconds_source"])
        self.assertIn("command.py:942-944", fast["quest_times_source"])
        self.assertIn("command.py:911", fast["last_chapter_source"])
        migration = FIXTURE["manifest"]["migration"]
        self.assertFalse(migration["is_gameplay"])
        self.assertEqual(migration["where"], "version.py:38-44")

    def test_the_manifest_records_the_content_inventory_it_measured(self) -> None:
        content = FIXTURE["manifest"]["content"]
        self.assertEqual(content["entries"], envelope.COMMITTED_QUEST_ENTRIES)
        self.assertEqual(content["id_min"], envelope.COMMITTED_ID_MIN)
        self.assertEqual(content["id_max"], envelope.COMMITTED_ID_MAX)
        self.assertEqual(content["reward_value"],
                         envelope.COMMITTED_REWARD_VALUE)
        self.assertEqual(content["reward_distinct_values"], 1)
        self.assertEqual(content["field_count"], envelope.COMMITTED_FIELD_COUNT)
        self.assertEqual(sorted(content["fields_read"]),
                         sorted(envelope.COMMITTED_FIELDS_READ))
        self.assertEqual(sorted(content["fields_unread"]),
                         sorted(envelope.COMMITTED_FIELDS_UNREAD))
        self.assertEqual(content["hint_values_empty"],
                         envelope.COMMITTED_QUEST_ENTRIES)
        rewards = [record for record in content["field_consumers"]
                   if record["field"] == "reward"][0]
        self.assertEqual(rewards["quoted_occurrences"], 0)
        self.assertFalse(rewards["used"])
        self.assertEqual(len(content["zero_consumer_fields"])
                         if "zero_consumer_fields" in content else 0, 0)

    def test_the_manifest_records_the_zero_consumer_index(self) -> None:
        records = FIXTURE["manifest"]["zero_consumer_fields"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["quoted_sites"], 0)
        self.assertEqual(records[0]["written_by"], [])
        self.assertEqual(records[0]["read_by"], [])

    def test_the_manifest_records_the_divergence_and_its_executed_evidence(
        self,
    ) -> None:
        divergence = FIXTURE["manifest"]["divergence"]
        self.assertEqual(divergence["status"], "DIVERGENCE, NOT PARITY")
        self.assertIn("map_lose_item", divergence["legacy"])
        self.assertIn("EMPTY", divergence["modern"])
        self.assertIn("probe 4", divergence["executed_evidence"])
        self.assertTrue(
            divergence["recorded_step"].startswith("command_end_quest"))
        probe = FIXTURE["manifest"]["probes"][3]
        self.assertEqual(probe["probe"], 4)
        self.assertEqual(probe["rows_before"], 40)
        self.assertEqual(probe["rows_after"], 39)
        self.assertEqual(probe["rows_destroyed_by_legacy"], 1)
        self.assertEqual(probe["client_computed_lost"], 1)
        self.assertTrue(probe["recorded_end_quest_step_rows_byte_identical"])
        refused = FIXTURE["manifest"]["refused_destruction"]
        self.assertEqual(refused["status"], "DIVERGENCE, NOT PARITY")

    def test_the_manifest_records_the_five_probes_it_actually_executed(self) -> None:
        probes = FIXTURE["manifest"]["probes"]
        self.assertEqual(len(probes), 5)
        for record in probes:
            self.assertTrue(record["executed_in_this_capture"])
        growth = probes[0]
        self.assertEqual(growth["goals_before"], envelope.COMMITTED_GOALS_LENGTH)
        self.assertEqual(growth["goals_after"], 501)
        self.assertEqual(growth["appended_entries"], 350)
        self.assertEqual(growth["stored_pair"], list(envelope.DERIVED_PROGRESS))
        self.assertEqual(growth["committed_id_max"], envelope.COMMITTED_ID_MAX)
        ignored = probes[1]
        self.assertEqual(ignored["key_sent"], envelope.QUEST_VAR_IGNORED_KEY)
        self.assertEqual(ignored["changed_leaves"], [])
        self.assertTrue(ignored["invented_key_accepted"])
        wrap = probes[2]
        self.assertEqual(wrap["mission_after"], "1")
        self.assertEqual(wrap["stored_type"], "str")
        self.assertEqual(wrap["corpus_mission"], 0)
        self.assertEqual(wrap["quest_vars_after"], {})
        fast = probes[4]
        self.assertEqual(fast["seconds_sent"], 60)
        self.assertTrue(fast["unlocked_index_unchanged"])
        self.assertTrue(fast["mission_unchanged"])
        self.assertTrue(fast["ranks_unchanged"])

    def test_the_manifest_records_the_wrap_and_the_one_ignored_key(self) -> None:
        wrap = FIXTURE["manifest"]["wrap"]
        self.assertEqual(wrap["bound"], envelope.MISSION_WRAP_BOUND)
        self.assertEqual(wrap["target"], envelope.MISSION_WRAP_TARGET)
        self.assertFalse(wrap["rejection"])
        keys = FIXTURE["manifest"]["quest_var_keys"]
        self.assertEqual(keys["comment_keys"],
                         list(envelope.QUEST_VAR_COMMENT_KEYS))
        self.assertFalse(keys["enforced"])
        self.assertEqual(keys["ignored_key"], envelope.QUEST_VAR_IGNORED_KEY)
        self.assertEqual(keys["alias_key"], envelope.QUEST_VAR_ALIAS_KEY)

    def test_the_manifest_records_the_six_branch_contracts(self) -> None:
        contracts = FIXTURE["manifest"]["command_contract"]
        self.assertEqual(len(contracts), envelope.BRANCH_COUNT)
        by_command = {record["command"]: record for record in contracts}
        self.assertFalse(by_command[envelope.COMPLETE_GOAL_COMMAND]["mutates"])
        self.assertEqual(
            by_command[envelope.COMPLETE_GOAL_COMMAND]["writes"], [])
        self.assertTrue(by_command[envelope.SET_GOALS_COMMAND][
            "grows_list_on_demand"])
        self.assertIsNone(by_command[envelope.SET_GOALS_COMMAND]["upper_bound"])
        self.assertTrue(by_command[envelope.SET_GOALS_COMMAND]["delegates_to"])
        self.assertEqual(
            by_command[envelope.END_QUEST_COMMAND]["destruction"], "REFUSED")
        self.assertIn("unit[2] - unit[3]",
                      by_command[envelope.END_QUEST_COMMAND]["destruction_note"])

    def test_the_manifest_records_the_no_reward_and_no_movement_claims(self) -> None:
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertFalse(transaction["reward_paid"])
        self.assertFalse(transaction["price_computed"])
        self.assertFalse(transaction["resource_moved"])
        self.assertFalse(transaction["completion_computed"])
        self.assertFalse(transaction["goal_bound_applied"])
        self.assertFalse(transaction["quest_var_membership_applied"])
        self.assertFalse(transaction["elapsed_time_computed"])
        self.assertFalse(transaction["unlocked_index_written"])
        self.assertEqual(transaction["resource_delta"],
                         {name: 0 for name in transaction["resource_delta"]})
        self.assertTrue(transaction["no_op_step_byte_identical"])
        self.assertTrue(transaction["rows_unchanged"])
        self.assertEqual(
            transaction["placement_count_before"],
            transaction["placement_count_after"])

    def test_the_manifest_states_the_containment_it_verified(self) -> None:
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertTrue(containment["working_tree_saves_unchanged"])
        self.assertTrue(containment["loopback_only"])
        self.assertTrue(containment["no_flash_browser_external_network"])
        self.assertTrue(containment["protected_fixtures"]["identical"])
        self.assertEqual(
            containment["pre_combined_sha256"],
            containment["post_combined_sha256"],
        )
        self.assertEqual(
            containment["only_working_tree_writes"],
            "fixture files under --out")
        self.assertEqual(FIXTURE["manifest"]["exit_code"], 0)
        self.assertEqual(
            FIXTURE["manifest"]["corpus"]["seed"]["path"],
            "tests/saves/fresh-player.json")

    def test_the_manifest_names_exactly_two_time_dependent_state_values(self) -> None:
        rule = FIXTURE["manifest"]["time_dependent_fields"]["rule"]
        self.assertIn("TWO", rule)
        self.assertIn("timestampLastChapter", rule)
        self.assertIn("questTimes", rule)
        leaves = FIXTURE["manifest"]["time_dependent_fields"]["state_leaves"]
        self.assertEqual(len(leaves), 2)


class ReplayTests(unittest.TestCase):
    """The endpoint replays each recorded step to its recorded post-state."""

    def test_each_recorded_step_replays_to_the_recorded_post_state(self) -> None:
        for name in STEP_NAMES:
            step = FIXTURE[name]
            reset_state(name)
            before = envelope.snapshot_state(BOOT.save_document(PID))  # type: ignore[union-attr]
            response = quest_now(intent_for(name))
            self.assertEqual(response.status_code, 200,
                             (name, response.get_json()))
            body = response.get_json()
            self.assertEqual(body["result"], "success", name)
            self.assertEqual(body["action"], step["action"], name)
            self.assertEqual(body["command"], step["command"], name)
            self.assertEqual(body["addressing"], step["addressing"], name)
            self.assertEqual(body["addressing_kind"],
                             envelope.ACTION_ADDRESSING[step["action"]], name)
            after = envelope.snapshot_state(BOOT.save_document(PID))  # type: ignore[union-attr]
            divergence = envelope.expected_state(
                before, step["action"], step["addressing"], after)
            self.assertIsNone(divergence, (name, divergence))
            self.assertEqual(body["quest_state"], after, name)
            self.assertEqual(body["resources"],
                             resources_of(step["after"]), name)
            self.assertEqual(body["reward_paid"], 0, name)
            self.assertFalse(body["reward_derived_from_content"], name)
            self.assertFalse(body["fast_forward_offered"], name)
            self.assertFalse(body["unlocked_quest_index_written"], name)
            self.assertEqual(body["quest_state"][envelope.KEY_UNLOCKED_INDEX],
                             envelope.COMMITTED_UNLOCKED_INDEX, name)

    def test_the_whole_save_replays_with_the_two_documented_prunes(self) -> None:
        for name in STEP_NAMES:
            step = FIXTURE[name]
            derived = envelope.derived_quest(
                step["quest_before"], step["action"], step["addressing"])
            expected_skipped: List[str] = []
            if derived["stamps_chapter"]:
                expected_skipped.append(PRUNED_CHAPTER_PREFIX)
            if derived["stamps_instant"]:
                expected_skipped.append(
                    "%s%s" % (PRUNED_QUEST_TIMES_PREFIX, step["addressing"]))
            reset_state(name)
            quest_now(intent_for(name))
            actual = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
            kept, skipped = pruned_differences(step["after"], actual)
            self.assertEqual(kept, [], (name, kept))
            # The skipped set is EXACTLY the values this branch stamps from the
            # wall clock, so a second time-dependent field would fail here.
            self.assertEqual(sorted(skipped), sorted(expected_skipped),
                             (name, skipped))
            for pointer in skipped:
                self.assertTrue(
                    pointer == PRUNED_CHAPTER_PREFIX
                    or pointer.startswith(PRUNED_QUEST_TIMES_PREFIX),
                    (name, pointer),
                )

    def test_the_no_op_step_replays_to_a_byte_identical_whole_save(self) -> None:
        name = "command_complete_goal"
        reset_state(name)
        response = quest_now(intent_for(name))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["derived"]["mutates"])
        actual = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        kept, skipped = pruned_differences(FIXTURE[name]["after"], actual)
        self.assertEqual(kept, [])
        # …and the no-op needs NO prune at all: nothing time-dependent moved.
        self.assertEqual(skipped, [])

    def test_the_replayed_six_steps_move_no_stored_resource(self) -> None:
        reset_state()
        resources_before = resources_now()
        for name in STEP_NAMES:
            reset_state(name)
            quest_now(intent_for(name))
            self.assertEqual(resources_now(), resources_before, name)
        self.assertEqual(resources_now(), envelope.COMMITTED_RESOURCE_BEFORE)

    def test_the_replayed_end_quest_leaves_every_row_byte_identical(self) -> None:
        name = "command_end_quest"
        reset_state(name)
        items_before = json.loads(json.dumps(
            BOOT.map_items(PID)  # type: ignore[union-attr]
        ))
        response = quest_now(intent_for(name))
        self.assertEqual(response.status_code, 200)
        items_after = BOOT.map_items(PID)  # type: ignore[union-attr]
        self.assertEqual(items_after, items_before)
        self.assertEqual(len(items_after), envelope.COMMITTED_PLACEMENTS)
        destruction = response.get_json()["destruction"]
        self.assertEqual(destruction["status"], "REFUSED")
        self.assertEqual(destruction["derived_units"], 0)
        self.assertTrue(destruction["placed_rows_byte_identical"])

    def test_a_client_supplied_progress_key_and_difficulty_are_ignored(self) -> None:
        name = "command_admin_set_quest_rank"
        reset_state(name)
        payload = intent_for(name)
        payload["difficulty"] = 3
        payload["quest_index_alias"] = 99
        response = quest_now(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["quest_state"][envelope.KEY_RANKS],
                         {"3": envelope.DERIVED_DIFFICULTY})

    def test_the_quest_variable_step_is_replayed_with_a_client_key_and_value(
        self,
    ) -> None:
        name = "command_set_quest_var"
        reset_state(name)
        payload = intent_for(name)
        payload["value"] = "a client value"
        payload["a_client_invented_key"] = 7
        response = quest_now(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["quest_state"][envelope.KEY_QUEST_VARS],
            {"spawned": envelope.DERIVED_QUEST_VALUE},
        )

    def test_a_refused_intent_leaves_the_state_byte_identical(self) -> None:
        reset_state()
        before = envelope.snapshot_state(BOOT.save_document(PID))  # type: ignore[union-attr]
        for payload, code in (
            ({"user_id": PID, "action": envelope.ACTION_END_QUEST},
             "missing_quest_id"),
            ({"user_id": PID, "action": envelope.ACTION_SET_GOAL,
              "goal_index": -1}, "invalid_goal_index"),
            ({"user_id": PID, "action": envelope.ACTION_SET_QUEST_VAR,
              "key": envelope.QUEST_VAR_IGNORED_KEY}, "ignored_quest_var_key"),
            ({"user_id": PID, "action": "fast_forward", "quest_id": 1},
             "invalid_action"),
        ):
            response = quest_now(payload)
            self.assertEqual(response.get_json()["error"]["code"], code)
            self.assertFalse(response.get_json()["ok"])
            self.assertEqual(envelope.snapshot_state(
                BOOT.save_document(PID)), before, code)  # type: ignore[union-attr]

    def test_the_working_tree_save_did_not_move(self) -> None:
        self.assertEqual(WORKING_TREE_PRE, harness.working_tree_save_hashes())

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(harness.port_is_free("127.0.0.1", port), port)


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]