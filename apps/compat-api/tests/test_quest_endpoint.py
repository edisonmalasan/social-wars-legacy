#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/quests`` behavior tests (OpenSpec task 3).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so the suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across quest execution.

The committed corpus holds every quest field at its **initial** value —
``goals`` 151 entries all ``None``, ``questsRank`` ``{}``,
``unlockedQuestIndex`` ``0``, ``currentQuestVars`` a recorded **``None``**,
``questTimes`` ``{}``, ``idCurrentMission`` an **integer** ``0``,
``timestampLastChapter`` ``0`` — so all six branches are exercisable against it
**with no fabricated player state**.

Covered:

* **all six branches** — the derived quest state, the **whole** state compared
  field by field, the no-op branch's byte-identity, the chapter branch's
  stringified identifier and cleared map, the refused ignored key, the wrap, the
  unbounded goals growth, the derived rank difficulty, and **every** placed row
  byte-identical plus **every one of the seven stored resources unchanged**.
* **intent only** — a request carrying ``progress``, ``value``, ``difficulty``,
  ``win``, ``voluntary_end``, ``duration``, ``map``, ``units``, ``lost``,
  ``reward``, ``price``, ``cost``, ``resources_changed``, ``vector``,
  ``seconds``, and ``fast_forward`` changes nothing, and the response **echoes
  no ignored value**.
* **the refused destruction count** — the derived blob's ``units`` is an empty
  list, every placed row is byte-identical, and the response reports the
  difference from the legacy server as a **divergence**; plus a test that a
  stubbed post-execution row change is caught, and a test that proves a
  **selected-subset** row comparison would be insufficient.
* **the two-part post-execution proof** — a quest state that does not match the
  derived result, and **any** stored resource that moved, each fail closed with
  ``internal_error``.  Each is exercised by a stub that lets the real dispatcher
  run and rewrites only the **post** read.
* **the structural refusals** — every per-action missing and invalid addressing,
  the ignored quest-variable key, an unresolvable quest state, and the shared
  identity refusals, each with its named code and an **empty** payload.
* **the recorded absences** — the route computes no reward, no completion, no
  remaining time and no progress ratio, adds no bound and no membership rule,
  names no unlocked-quest write, and offers no fast-forward operation.
* **session/bootstrap byte-identity** after quest intents, and that every other
  delivered route is untouched.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import textwrap
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import quest_envelope as envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
APP = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

COMMITTED_RESOURCES = dict(envelope.COMMITTED_RESOURCE_BEFORE)
#: Every action with the addressing the fixture uses for it.
ALL_INTENTS = [
    (envelope.ACTION_SET_GOAL, 2),
    (envelope.ACTION_COMPLETE_GOAL, 2),
    (envelope.ACTION_SET_QUEST_VAR, "spawned"),
    (envelope.ACTION_COLLECT_MISSION, 5),
    (envelope.ACTION_SET_QUEST_RANK, 3),
    (envelope.ACTION_END_QUEST, 7),
]


def seed_state() -> Dict[str, Any]:
    """The committed corpus's own quest state, reset **in memory and on disk**.

    The quest branches mutate these containers in place (``engine.set_goals``
    appends to ``goals``; ``map_lose_item`` deletes from ``items``), so the reset
    updates both representations — exactly the mechanism the legacy dispatcher
    itself uses to keep them in step.  It is a test-only, contained reset and
    never a claim about legacy behaviour or a working-tree write.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["privateState"][envelope.KEY_GOALS] = [None] * (
        envelope.COMMITTED_GOALS_LENGTH
    )
    save["privateState"][envelope.KEY_RANKS] = {}
    save["privateState"][envelope.KEY_UNLOCKED_INDEX] = (
        envelope.COMMITTED_UNLOCKED_INDEX
    )
    first_map = save["maps"][0]
    first_map[envelope.KEY_QUEST_VARS] = None
    first_map[envelope.KEY_QUEST_TIMES] = {}
    first_map[envelope.KEY_MISSION] = envelope.COMMITTED_MISSION
    first_map[envelope.KEY_LAST_CHAPTER] = envelope.COMMITTED_LAST_CHAPTER
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")
    return envelope.snapshot_state(save)


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, APP, PID, WORKING_TREE_PRE
    ORIGINAL_CWD = os.getcwd()
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


def intent(action: str, addressing: Any) -> Dict[str, Any]:
    """The whole contract: a save id, a closed action, and its addressing."""
    body: Dict[str, Any] = {"user_id": PID, "action": action}
    body[envelope.ACTION_ADDRESSING_KEY[action]] = addressing
    return body


def quests_now(payload: Dict[str, Any]) -> Result:
    with harness.offline():
        return Result(APP, CLIENT.post("/v0/quests", json=payload))  # type: ignore


def quest_state_now() -> Dict[str, Any]:
    return envelope.snapshot_state(BOOT.save_document(PID))  # type: ignore[union-attr]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def items_now() -> Dict[str, Any]:
    return BOOT.map_items(PID)  # type: ignore[union-attr]


class Result:
    """A captured response plus the app that produced it.

    Flask's test client resolves the JSON decoder through a weak reference to the
    app, so returning only the response and letting the app go out of scope turns
    every later ``get_json()`` into a ``ReferenceError``.
    """

    def __init__(self, app: Any, response: Any) -> None:
        self.app = app
        self.response = response

    @property
    def status_code(self) -> int:
        return int(self.response.status_code)

    def get_json(self) -> Any:
        return self.response.get_json()


@contextmanager
def patched_boot(name: str, value: Any) -> Iterator[None]:
    """Install an instance-level stub on ``BOOT`` and restore it EXACTLY."""
    had = name in BOOT.__dict__  # type: ignore[union-attr]
    original = BOOT.__dict__[name] if had else None  # type: ignore[union-attr,index]
    setattr(BOOT, name, value)  # type: ignore[union-attr]
    try:
        yield
    finally:
        if had:
            setattr(BOOT, name, original)  # type: ignore[union-attr]
        else:
            delattr(BOOT, name)  # type: ignore[union-attr]


def _post_only_the_second_read(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]],
    payload: Dict[str, Any],
    attribute: str = "save_document",
) -> Result:
    """Run one intent with the POST-execution read of ``attribute`` rewritten.

    The endpoint reads the save **twice** — once before dispatch for the
    derivation and once after it for the proof — through the same accessor, so
    rewriting only the second read reproduces a persisted state legacy could
    never report while leaving the real dispatcher's own write untouched.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    real = getattr(BOOT, attribute)
    state = {"seen": 0}

    def stub(user_id: str, _attribute: str = attribute) -> Dict[str, Any]:
        state["seen"] += 1
        document = real(user_id)
        if state["seen"] == 1:
            return document
        if _attribute == "save_document":
            return transform(copy.deepcopy(document))
        value = transform(document)
        setattr(app, "_stubbed_value", value)
        return value

    with patched_boot(attribute, stub):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/quests", json=payload))


class SuccessfulIntentTests(unittest.TestCase):
    """Every branch, the derived effect, and nothing else."""

    def setUp(self) -> None:
        seed_state()

    def test_all_six_branches_succeed_and_derive_their_effect(self) -> None:
        for action, addressing in ALL_INTENTS:
            before = quest_state_now()
            resources_before = resources_now()
            items_before = copy.deepcopy(items_now())
            result = quests_now(intent(action, addressing))
            self.assertEqual(result.status_code, 200, (action, result.get_json()))
            body = result.get_json()
            after = quest_state_now()
            divergence = envelope.expected_state(before, action, addressing,
                                                 after)
            self.assertIsNone(divergence, (action, divergence))
            self.assertEqual(body["action"], action)
            self.assertEqual(body["command"],
                             envelope.ACTION_COMMANDS[action])
            self.assertEqual(body["addressing"], addressing)
            self.assertEqual(body["addressing_kind"],
                             envelope.ACTION_ADDRESSING[action])
            self.assertEqual(body["quest_state"], after)
            self.assertEqual(body["resources"], resources_before,
                             "every stored resource is unchanged")
            self.assertEqual(items_now(), items_before,
                             "every placed row is byte-identical")
            self.assertEqual(body["reward_paid"], 0)
            self.assertFalse(body["reward_derived_from_content"])
            self.assertFalse(body["fast_forward_offered"])

    def test_the_projection_reports_all_seven_fields_and_derives_nothing(
        self,
    ) -> None:
        result = quests_now(intent(envelope.ACTION_SET_GOAL, 2))
        body = result.get_json()
        for block in (body["quests"], body["previous"]):
            self.assertEqual(block["quest_field_names"],
                             list(envelope.QUEST_FIELDS))
            self.assertEqual(block["derived"], {})
            self.assertIsNone(block["completion_state"])
            self.assertTrue(block["verbatim"])
            self.assertFalse(block["unlocked_quest_index_written"])
        self.assertEqual(body["previous"]["goals_length"],
                         envelope.COMMITTED_GOALS_LENGTH)
        self.assertTrue(body["previous"]["current_quest_vars_is_null"])

    def test_the_progress_pair_is_the_derived_zero_pair(self) -> None:
        result = quests_now(intent(envelope.ACTION_SET_GOAL, 2))
        body = result.get_json()
        self.assertEqual(body["derived"]["progress_pair"],
                         list(envelope.DERIVED_PROGRESS))
        self.assertEqual(body["quest_state"][envelope.KEY_GOALS][2], [0, 0])
        self.assertEqual(len(body["quest_state"][envelope.KEY_GOALS]),
                         envelope.COMMITTED_GOALS_LENGTH)

    def test_the_goals_list_grows_on_demand_with_no_upper_bound(self) -> None:
        """Design D4 reproduced, not closed: 350 appended entries from index 500."""
        result = quests_now(intent(envelope.ACTION_SET_GOAL, 500))
        self.assertEqual(result.status_code, 200, result.get_json())
        state = result.get_json()["quest_state"]
        self.assertEqual(len(state[envelope.KEY_GOALS]), 501)
        self.assertEqual(state[envelope.KEY_GOALS][500], [0, 0])
        self.assertEqual(state[envelope.KEY_GOALS][150], None)

    def test_the_no_op_branch_leaves_the_whole_state_byte_identical(self) -> None:
        before = quest_state_now()
        items_before = copy.deepcopy(items_now())
        result = quests_now(intent(envelope.ACTION_COMPLETE_GOAL, 2))
        self.assertEqual(result.status_code, 200, result.get_json())
        body = result.get_json()
        self.assertFalse(body["derived"]["mutates"])
        self.assertEqual(body["derived"]["written"], [])
        self.assertEqual(quest_state_now(), before,
                         "complete_goal writes NOTHING AT ALL")
        self.assertEqual(body["quest_state"], before)
        self.assertEqual(items_now(), items_before)

    def test_the_chapter_branch_stringifies_and_clears(self) -> None:
        """Design D8: both type facts reproduced, never normalized."""
        result = quests_now(intent(envelope.ACTION_COLLECT_MISSION, 5))
        body = result.get_json()
        state = body["quest_state"]
        self.assertEqual(state[envelope.KEY_MISSION], "5")
        self.assertTrue(body["quests"]["mission_is_string"])
        self.assertEqual(state[envelope.KEY_QUEST_VARS], {})
        self.assertFalse(body["quests"]["current_quest_vars_is_null"])
        self.assertGreater(state[envelope.KEY_LAST_CHAPTER], 0)
        self.assertEqual(body["derived"]["wrapped_mission"], 5)

    def test_an_out_of_range_mission_wraps_rather_than_being_rejected(self) -> None:
        result = quests_now(intent(envelope.ACTION_COLLECT_MISSION, 150))
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(result.get_json()["quest_state"][envelope.KEY_MISSION],
                         "1")
        self.assertEqual(result.get_json()["derived"]["wrapped_mission"], 1)

    def test_the_quest_variable_map_self_heals_from_the_recorded_null(self) -> None:
        self.assertIsNone(quest_state_now()[envelope.KEY_QUEST_VARS])
        result = quests_now(intent(envelope.ACTION_SET_QUEST_VAR, "boss"))
        body = result.get_json()
        self.assertEqual(body["quest_state"][envelope.KEY_QUEST_VARS],
                         {"boss": envelope.DERIVED_QUEST_VALUE})
        self.assertEqual(body["derived"]["quest_var_value"],
                         envelope.DERIVED_QUEST_VALUE)

    def test_an_invented_quest_variable_key_is_accepted_and_persisted(self) -> None:
        result = quests_now(intent(envelope.ACTION_SET_QUEST_VAR,
                                   "a_client_invented_key"))
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(
            result.get_json()["quest_state"][envelope.KEY_QUEST_VARS],
            {"a_client_invented_key": envelope.DERIVED_QUEST_VALUE},
        )

    def test_the_id_key_also_overwrites_the_current_mission(self) -> None:
        result = quests_now(intent(envelope.ACTION_SET_QUEST_VAR, "id"))
        self.assertEqual(result.status_code, 200, result.get_json())
        body = result.get_json()
        self.assertEqual(sorted(body["derived"]["written"]),
                         sorted([envelope.KEY_MISSION, envelope.KEY_QUEST_VARS]))
        self.assertEqual(body["quest_state"][envelope.KEY_MISSION],
                         envelope.DERIVED_QUEST_VALUE)

    def test_the_rank_difficulty_is_derived_never_client_sent(self) -> None:
        payload = intent(envelope.ACTION_SET_QUEST_RANK, 3)
        payload["difficulty"] = 3
        result = quests_now(payload)
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(result.get_json()["quest_state"][envelope.KEY_RANKS],
                         {"3": envelope.DERIVED_DIFFICULTY})
        self.assertEqual(result.get_json()["derived"]["difficulty"],
                         envelope.DERIVED_DIFFICULTY)

    def test_the_unlocked_quest_index_is_never_written(self) -> None:
        for action, addressing in ALL_INTENTS:
            seed_state()
            result = quests_now(intent(action, addressing))
            self.assertEqual(result.status_code, 200, (action, result.get_json()))
            self.assertEqual(
                result.get_json()["quest_state"][envelope.KEY_UNLOCKED_INDEX],
                envelope.COMMITTED_UNLOCKED_INDEX,
                "%s wrote the unlocked-quest index" % action,
            )
            self.assertFalse(
                result.get_json()["unlocked_quest_index_written"], action)

    def test_a_full_cycle_leaves_every_resource_unchanged(self) -> None:
        resources_before = resources_now()
        for action, addressing in ALL_INTENTS:
            quests_now(intent(action, addressing))
        self.assertEqual(resources_now(), resources_before)
        self.assertEqual(resources_now(), COMMITTED_RESOURCES)


class RefusedDestructionTests(unittest.TestCase):
    """Design D2: the destruction count is refused, as a divergence."""

    def setUp(self) -> None:
        seed_state()

    def test_the_derived_blob_carries_an_empty_unit_list(self) -> None:
        result = quests_now(intent(envelope.ACTION_END_QUEST, 7))
        self.assertEqual(result.status_code, 200, result.get_json())
        body = result.get_json()
        self.assertEqual(body["end_quest_blob"]["units"], [])
        self.assertEqual(body["end_quest_blob"]["quest_id"], 7)
        self.assertEqual(body["end_quest_blob"]["difficulty"],
                         envelope.DERIVED_DIFFICULTY)

    def test_the_blob_belongs_to_the_end_quest_branch_alone(self) -> None:
        """The other five responses carry **no** blob.

        The client's typed parser requires the block for `end_quest` and
        refuses a response that carries one for any other action, so this is a
        wire contract on both sides rather than a presentation choice. It was
        violated in the other direction — the client demanded the block
        unconditionally — and every offline check still passed.
        """
        for action, addressing in ALL_INTENTS:
            result = quests_now(intent(action, addressing))
            self.assertEqual(result.status_code, 200, result.get_json())
            body = result.get_json()
            if action == envelope.ACTION_END_QUEST:
                self.assertIsInstance(body["end_quest_blob"], dict,
                                      "%s must carry the derived blob" % action)
            else:
                self.assertIsNone(body["end_quest_blob"],
                                  "%s must carry NO blob" % action)

    def test_both_projections_declare_themselves_resolved(self) -> None:
        """The typed parser requires ``resolvable`` on the after **and**
        before projections, so a projection without it is a client refusal.

        Every quest response's `quests` and `previous` blocks must therefore
        carry the flag; this was omitted and the client refused all six live
        responses as ``bad_response`` while every offline check passed.
        """
        for action, addressing in ALL_INTENTS:
            body = quests_now(intent(action, addressing)).get_json()
            for block in ("quests", "previous"):
                self.assertIs(body[block]["resolvable"], True,
                              "%s/%s" % (action, block))
                self.assertIs(body[block]["ok"], True,
                              "%s/%s" % (action, block))
            self.assertEqual(body["quests"]["derived"], {})

    def test_the_response_reports_the_divergence_and_the_proof(self) -> None:
        result = quests_now(intent(envelope.ACTION_END_QUEST, 7))
        destruction = result.get_json()["destruction"]
        self.assertEqual(destruction["status"], "REFUSED")
        self.assertEqual(destruction["legacy_status"], "DIVERGENCE, NOT PARITY")
        self.assertTrue(destruction["client_supplied_units_ignored"])
        self.assertEqual(destruction["derived_units"], 0)
        self.assertTrue(destruction["placed_rows_byte_identical"])
        self.assertEqual(destruction["placed_rows_before"], 40)
        self.assertEqual(destruction["placed_rows_after"], 40)
        self.assertEqual(destruction["ledger_door"]["door"], "map_lose_item")
        self.assertEqual(
            destruction["ledger_door"]["calls_helper_at"],
            "engine.py:223 (push_dead_unit)")

    def test_every_placed_row_is_byte_identical_over_the_complete_set(self) -> None:
        items_before = copy.deepcopy(items_now())
        result = quests_now(intent(envelope.ACTION_END_QUEST, 7))
        items_after = items_now()
        self.assertEqual(sorted(items_after, key=int),
                         sorted(items_before, key=int))
        self.assertEqual(len(items_after), envelope.COMMITTED_PLACEMENTS)
        for key in items_before:
            self.assertEqual(items_after[key], items_before[key], key)

    def test_a_client_supplied_destruction_count_is_ignored(self) -> None:
        items_before = copy.deepcopy(items_now())
        payload = intent(envelope.ACTION_END_QUEST, 7)
        payload["units"] = [[26, 0, 5, 0]]
        payload["lost"] = 5
        result = quests_now(payload)
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(items_now(), items_before)
        self.assertEqual(len(items_now()), envelope.COMMITTED_PLACEMENTS)
        self.assertEqual(result.get_json()["end_quest_blob"]["units"], [])
        self.assertNotIn("[[26, 0, 5, 0]]", json.dumps(result.get_json()))

    def test_a_moved_placed_row_fails_closed(self) -> None:
        def moved(items: Dict[str, Any]) -> Dict[str, Any]:
            moved_items = dict(items)
            moved_items["1"] = [999, 0, 0, 0, 0, [], {}, 1]
            return moved_items

        result = _post_with_items_stub(
            moved, intent(envelope.ACTION_END_QUEST, 7))
        self.assertEqual(result.status_code, 500, result.get_json())
        self.assertEqual(result.get_json()["error"]["code"], "internal_error")
        self.assertIn("destruction count is refused by contract",
                      result.get_json()["error"]["message"])

    def test_a_selected_subset_row_comparison_would_be_insufficient(self) -> None:
        """A proof over ONE row cannot see a row that changed elsewhere."""
        items_before = copy.deepcopy(items_now())
        watched = "1"
        moved_key = "39"
        self.assertIn(watched, items_before)
        self.assertIn(moved_key, items_before)
        self.assertNotEqual(watched, moved_key)
        seen: Dict[str, Dict[str, Any]] = {}

        def moved_elsewhere(items: Dict[str, Any]) -> Dict[str, Any]:
            seen["before"] = copy.deepcopy(items)
            moved_items = dict(items)
            moved_items[moved_key] = [999, 0, 0, 0, 0, [], {}, 1]
            return moved_items

        result = _post_with_items_stub(
            moved_elsewhere, intent(envelope.ACTION_END_QUEST, 7))
        self.assertEqual(result.status_code, 500, result.get_json())
        self.assertIn("map keys ['%s']" % moved_key,
                      result.get_json()["error"]["message"])
        # The row a SELECTED SUBSET proof would have compared is byte-identical
        # even in the very mapping the route compared, while a row elsewhere
        # moved — so a one-row proof would have passed on this transaction.
        self.assertEqual(seen["before"][watched], items_before[watched])
        self.assertEqual(items_now(), items_before,
                         "the disposable corpus itself is untouched")

    def test_the_route_never_calls_the_legacy_destruction_helper(self) -> None:
        """Checked on the AST, so the docstring may NAME the refusal."""
        names = route_code_names()
        for forbidden in ("map_lose_item", "map_pop_item", "push_dead_unit",
                          "map_delete_item", "apply_resources"):
            self.assertNotIn(forbidden, names, forbidden)
        # …and it does prove the whole placed-row set.
        self.assertIn("map_items", names)
        self.assertIn("deepcopy", names)


class IntentOnlyTests(unittest.TestCase):
    """The client names its intent and nothing else."""

    IGNORED = envelope.IGNORED_CLIENT_KEYS

    def setUp(self) -> None:
        seed_state()

    def test_a_request_carrying_every_derived_key_changes_nothing(self) -> None:
        reference = quests_now(intent(envelope.ACTION_END_QUEST, 7)).get_json()
        seed_state()
        payload = intent(envelope.ACTION_END_QUEST, 7)
        for key in self.IGNORED:
            payload[key] = 999999
        payload["units"] = [[26, 0, 5, 0]]
        payload["lost"] = 5
        result = quests_now(payload)
        self.assertEqual(result.status_code, 200, result.get_json())
        body = result.get_json()
        self.assertEqual(body["quest_state"], reference["quest_state"])
        self.assertEqual(body["resources"], reference["resources"])
        self.assertEqual(body["end_quest_blob"], reference["end_quest_blob"])
        self.assertEqual(body["derived"], reference["derived"])
        self.assertEqual(body["persisted_client_values"], [])
        self.assertEqual(sorted(body["ignored_client_keys"]),
                         sorted(self.IGNORED))

    def test_the_response_echoes_no_ignored_value(self) -> None:
        payload = intent(envelope.ACTION_SET_GOAL, 2)
        payload["progress"] = [9, 9]
        payload["reward"] = 999999
        body = quests_now(payload).get_json()
        encoded = json.dumps(body)
        self.assertNotIn("999999", encoded)
        self.assertEqual(body["derived"]["progress_pair"], [0, 0])
        self.assertEqual(body["reward_paid"], 0)

    def test_the_client_sends_only_an_identity_an_action_and_an_addressing(
        self,
    ) -> None:
        for action, addressing in ALL_INTENTS:
            body = intent(action, addressing)
            self.assertEqual(
                sorted(body),
                sorted(["user_id", "action",
                        envelope.ACTION_ADDRESSING_KEY[action]]),
            )
            self.assertEqual(len(body), 3)

    def test_the_module_derives_every_written_value_server_side(self) -> None:
        for action, addressing in ALL_INTENTS:
            built = envelope.build_envelope(action, addressing, ts=1700000000)
            entry = built["commands"][0]
            self.assertEqual(entry[3], [0] * envelope.RESOURCE_VECTOR_SLOTS)
            if action == envelope.ACTION_SET_GOAL:
                self.assertEqual(json.loads(entry[2][1]),
                                 list(envelope.DERIVED_PROGRESS))
            elif action == envelope.ACTION_SET_QUEST_VAR:
                self.assertIs(entry[2][1], envelope.DERIVED_QUEST_VALUE)
            elif action == envelope.ACTION_SET_QUEST_RANK:
                self.assertEqual(entry[2][1], envelope.DERIVED_DIFFICULTY)
            elif action == envelope.ACTION_END_QUEST:
                self.assertEqual(json.loads(entry[2][0])["units"], [])


class TwoPartProofTests(unittest.TestCase):
    """The post-execution proof, both halves."""

    def setUp(self) -> None:
        seed_state()

    def test_a_state_that_does_not_match_the_derived_result_fails_closed(self) -> None:
        def wrong(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"][envelope.KEY_GOALS] = list(
                document["privateState"][envelope.KEY_GOALS])
            document["privateState"][envelope.KEY_GOALS][2] = [7, 7]
            return document

        result = _post_only_the_second_read(
            wrong, intent(envelope.ACTION_SET_GOAL, 2))
        self.assertEqual(result.status_code, 500, result.get_json())
        self.assertEqual(result.get_json()["error"]["code"], "internal_error")
        self.assertIn("does not carry the derived result",
                      result.get_json()["error"]["message"])

    def test_a_no_op_branch_that_wrote_something_fails_closed(self) -> None:
        def wrote(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"][envelope.KEY_RANKS] = {"9": 3}
            return document

        result = _post_only_the_second_read(
            wrote, intent(envelope.ACTION_COMPLETE_GOAL, 2))
        self.assertEqual(result.status_code, 500, result.get_json())
        self.assertIn("NOTHING AT ALL", result.get_json()["error"]["message"])

    def test_an_untouched_field_that_moved_fails_closed(self) -> None:
        def wrote(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"][envelope.KEY_RANKS] = {"9": 3}
            return document

        result = _post_only_the_second_read(
            wrote, intent(envelope.ACTION_END_QUEST, 7))
        self.assertEqual(result.status_code, 500, result.get_json())
        self.assertIn("untouched", result.get_json()["error"]["message"])

    def test_a_written_unlocked_index_fails_closed(self) -> None:
        def wrote(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"][envelope.KEY_UNLOCKED_INDEX] = 4
            return document

        result = _post_only_the_second_read(
            wrote, intent(envelope.ACTION_SET_GOAL, 2))
        self.assertEqual(result.status_code, 500, result.get_json())
        self.assertIn("unlockedQuestIndex",
                      result.get_json()["error"]["message"])

    def test_any_stored_resource_that_moved_fails_closed(self) -> None:
        for name in COMMITTED_RESOURCES:
            def moved(values: Dict[str, int], slot: str = name) -> Dict[str, int]:
                changed = dict(values)
                changed[slot] = changed[slot] + 1
                return changed

            result = _post_with_resources_stub(
                moved, intent(envelope.ACTION_SET_GOAL, 2))
            self.assertEqual(result.status_code, 500, name)
            self.assertEqual(result.get_json()["error"]["code"],
                             "internal_error")
            self.assertIn("moves no resource",
                          result.get_json()["error"]["message"])

    def test_the_proof_compares_every_stored_resource_not_a_subset(self) -> None:
        source = route_source()
        self.assertIn("for name in sorted(resources_after):", source)
        self.assertIn("resources_before[name]", source)
        # …and a comparison over a selected few would not fail on the missing
        # slot, which is what makes the loop the proof rather than a decoration.
        seen = []
        for name in sorted(COMMITTED_RESOURCES):
            def moved(values: Dict[str, int], slot: str = name) -> Dict[str, int]:
                changed = dict(values)
                changed[slot] = changed[slot] + 7
                return changed

            result = _post_with_resources_stub(
                moved, intent(envelope.ACTION_COMPLETE_GOAL, 2))
            self.assertEqual(result.status_code, 500, name)
            # The message names the slot, which is what makes the loop's
            # coverage observable rather than assumed.
            self.assertIn("resource %s is" % name,
                          result.get_json()["error"]["message"])
            seen.append(name in result.get_json()["error"]["message"])
        self.assertEqual(len(set(seen)), 1)
        self.assertTrue(seen[0], "every slot's failure names that slot")

    def test_the_endpoint_reads_the_stored_resource_set_in_full(self) -> None:
        calls: List[Dict[str, int]] = []
        original = BOOT.resources  # type: ignore[union-attr]

        def counting(user_id: str) -> Dict[str, int]:
            values = original(user_id)
            calls.append(values)
            return values

        with patched_boot("resources", counting):
            seed_state()
            quests_now(intent(envelope.ACTION_SET_GOAL, 2))
        self.assertEqual(len(calls), 2)
        for values in calls:
            self.assertEqual(sorted(values), sorted(COMMITTED_RESOURCES))
            self.assertEqual(len(values), 7)


def _post_with_resources_stub(
    transform: Callable[[Dict[str, int]], Dict[str, int]],
    payload: Dict[str, Any],
) -> Result:
    """Run one intent against a ``BOOT`` whose post resource read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.resources  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, int]:
        state["seen"] += 1
        values = original(user_id)
        if state["seen"] == 1:
            return values
        return transform(values)

    with patched_boot("resources", stub):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/quests", json=payload))


class RefusalTests(unittest.TestCase):
    """Every structural refusal, with its named code and an empty payload."""

    def setUp(self) -> None:
        seed_state()

    def assert_refused(self, payload: Dict[str, Any], code: str,
                       status: int = 400) -> Dict[str, Any]:
        before = quest_state_now()
        result = quests_now(payload)
        self.assertEqual(result.status_code, status, (payload, result.get_json()))
        body = result.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(sorted(body["error"]), ["code", "message"])
        self.assertNotIn("quest_state", body)
        self.assertNotIn("resources", body)
        self.assertNotIn("previous", body)
        self.assertEqual(quest_state_now(), before, "no state change")
        return body

    def test_an_unknown_or_missing_action_is_refused(self) -> None:
        self.assert_refused({"user_id": PID, "action": "teleport",
                             "goal_index": 1}, "invalid_action")
        self.assert_refused({"user_id": PID, "goal_index": 1},
                            "missing_action")
        self.assert_refused({"user_id": PID, "action": envelope.FAST_FORWARD_COMMAND,
                             "quest_id": 1}, "invalid_action")

    def test_every_missing_addressing_is_refused_with_its_own_code(self) -> None:
        for action in envelope.ACTIONS:
            code = {
                envelope.ACTION_SET_GOAL: "missing_goal_index",
                envelope.ACTION_COMPLETE_GOAL: "missing_goal_index",
                envelope.ACTION_SET_QUEST_VAR: "missing_key",
                envelope.ACTION_COLLECT_MISSION: "missing_mission",
                envelope.ACTION_SET_QUEST_RANK: "missing_quest_index",
                envelope.ACTION_END_QUEST: "missing_quest_id",
            }[action]
            self.assert_refused({"user_id": PID, "action": action}, code)

    def test_every_invalid_addressing_is_refused_with_its_own_code(self) -> None:
        cases = [
            (envelope.ACTION_SET_GOAL, -1, "invalid_goal_index"),
            (envelope.ACTION_SET_GOAL, "2", "invalid_goal_index"),
            (envelope.ACTION_SET_GOAL, True, "invalid_goal_index"),
            (envelope.ACTION_COMPLETE_GOAL, -3, "invalid_goal_index"),
            (envelope.ACTION_SET_QUEST_VAR, "", "invalid_key"),
            (envelope.ACTION_SET_QUEST_VAR, 7, "invalid_key"),
            (envelope.ACTION_COLLECT_MISSION, "5", "invalid_mission"),
            (envelope.ACTION_SET_QUEST_RANK, "3", "invalid_quest_index"),
            (envelope.ACTION_END_QUEST, "7", "invalid_quest_id"),
            (envelope.ACTION_END_QUEST, None, "invalid_quest_id"),
        ]
        for action, addressing, code in cases:
            self.assert_refused(intent(action, addressing), code)

    def test_a_negative_goal_index_message_names_the_legacy_aliasing(self) -> None:
        body = self.assert_refused(
            intent(envelope.ACTION_SET_GOAL, -1), "invalid_goal_index")
        self.assertIn("goals[-1]", body["error"]["message"])
        self.assertIn("NO upper bound", body["error"]["message"])

    def test_the_one_ignored_quest_variable_key_is_refused_with_its_own_code(
        self,
    ) -> None:
        body = self.assert_refused(
            intent(envelope.ACTION_SET_QUEST_VAR,
                   envelope.QUEST_VAR_IGNORED_KEY),
            "ignored_quest_var_key",
            status=409,
        )
        self.assertIn("command.py:91-95", body["error"]["message"])
        self.assertIn("chapter 99", body["error"]["message"])

    def test_a_large_goal_index_is_accepted_because_no_bound_is_invented(self) -> None:
        result = quests_now(intent(envelope.ACTION_SET_GOAL, 5000))
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(len(result.get_json()["quest_state"][envelope.KEY_GOALS]),
                         5001)

    def test_a_large_or_negative_rank_index_is_accepted(self) -> None:
        for index in (999999, -5):
            seed_state()
            result = quests_now(intent(envelope.ACTION_SET_QUEST_RANK, index))
            self.assertEqual(result.status_code, 200, (index, result.get_json()))
            self.assertEqual(
                result.get_json()["quest_state"][envelope.KEY_RANKS],
                {str(index): envelope.DERIVED_DIFFICULTY},
            )

    def test_an_unresolvable_quest_state_is_refused_with_its_own_code(self) -> None:
        real = BOOT.save_document  # type: ignore[union-attr]

        def unresolvable(user_id: str) -> Dict[str, Any]:
            document = copy.deepcopy(real(user_id))
            del document["privateState"][envelope.KEY_GOALS]
            return document

        with patched_boot("save_document", unresolvable):
            result = quests_now(intent(envelope.ACTION_SET_GOAL, 2))
        self.assertEqual(result.status_code, 409, result.get_json())
        self.assertEqual(result.get_json()["error"]["code"],
                         "unresolvable_quest_state")
        self.assertIn(envelope.KEY_GOALS, result.get_json()["error"]["message"])
        self.assertNotIn("quest_state", result.get_json())
        self.assertNotIn("resources", result.get_json())

    def test_the_shared_identity_refusals_come_first(self) -> None:
        self.assert_refused({"action": envelope.ACTION_END_QUEST,
                             "quest_id": 1}, "missing_user_id")
        self.assert_refused({"user_id": "", "action": envelope.ACTION_END_QUEST,
                             "quest_id": 1}, "missing_user_id")
        self.assert_refused({"user_id": 7, "action": envelope.ACTION_END_QUEST,
                             "quest_id": 1}, "invalid_user_id")
        result = quests_now({"user_id": "does-not-exist-0000",
                             "action": envelope.ACTION_END_QUEST, "quest_id": 1})
        self.assertEqual(result.status_code, 404, result.get_json())
        self.assertEqual(result.get_json()["error"]["code"], "unknown_user_id")

    def test_a_non_object_body_is_refused(self) -> None:
        for body in ([], "nope", 7, None):
            with harness.offline():
                result = Result(APP, CLIENT.post("/v0/quests", json=body))  # type: ignore
            self.assertEqual(result.status_code, 400, body)
            self.assertEqual(result.get_json()["error"]["code"],
                             "invalid_payload")


def route_source() -> str:
    """The delivered route's own source, from its function to the next route."""
    source = Path(compat_service.__file__).read_text(encoding="utf-8")
    start = source.index("def v0_quests()")
    return source[start : source.index('@app.post("/v0/research")', start)]


def route_code_names() -> List[str]:
    """Every executable name the route binds, from its AST.

    Docstrings and comments are dropped by construction, so the route may NAME
    the refused helper while never CALLING it — which is exactly the distinction
    this line has to keep.
    """
    names: List[str] = []
    tree = ast.parse("def _route():\n"
                     + textwrap.indent(route_source(), "    "))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.FunctionDef):
            names.append(node.name)
    return names


def _post_with_items_stub(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]],
    payload: Dict[str, Any],
) -> Result:
    """Run one intent with the POST-execution read of ``map_items`` rewritten.

    The endpoint reads the placement map twice — once before dispatch for the
    byte-identity proof's reference copy and once after it — through the same
    accessor, so rewriting only the second read reproduces a row change legacy
    could never report on a quest command.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    real = BOOT.map_items  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, Any]:
        state["seen"] += 1
        items = copy.deepcopy(real(user_id))
        if state["seen"] == 1:
            return items
        return transform(items)

    with patched_boot("map_items", stub):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/quests", json=payload))


class RecordedAbsenceTests(unittest.TestCase):
    """The route's refusals are asserted against its own source, not promised."""

    def test_the_route_names_every_design_decision(self) -> None:
        route = route_source()
        for decision in ("Design D2", "Design D3", "Design D4", "Design D6",
                         "Design D7", "Design D9"):
            self.assertIn(decision, route, decision)
        self.assertIn("Design D4/D5", route)
        for token in ("ERROR_UNRESOLVABLE_QUEST_STATE",
                      "ERROR_IGNORED_QUEST_VAR_KEY",
                      "ERROR_MISSING_QUEST_ID", "ERROR_INVALID_GOAL_INDEX"):
            self.assertIn(token, route, token)

    def test_the_route_computes_no_reward_and_no_price(self) -> None:
        route = route_source()
        self.assertIn("reward_paid=0", route)
        self.assertIn("reward_derived_from_content=False", route)
        for forbidden in ("reward *", "reward * int", "int(reward",
                          "COMMITTED_REWARD_VALUE", "reward =",
                          "reward_paid = ", "reward_paid=envelope"):
            self.assertNotIn(forbidden, route, forbidden)

    def test_the_route_computes_no_completion_elapsed_or_progress(self) -> None:
        route = route_source()
        for forbidden in ("completion_state =", "remaining_time",
                          "progress_ratio", "elapsed", "time_left",
                          "mark_goal_complete", "is_goal_complete",
                          "goal_complete", "completed ="):
            self.assertNotIn(forbidden, route, forbidden)
        self.assertIn("unlocked_quest_index_written=False", route)

    def test_the_route_adds_no_goal_bound_or_clamp(self) -> None:
        route = route_source()
        self.assertIn("NO upper bound", route)
        self.assertIn("goals[-1]", route)
        self.assertNotIn("len(goals)", route)
        self.assertNotIn("MAX_GOAL", route)

    def test_the_route_adds_no_membership_rule(self) -> None:
        route = route_source()
        self.assertIn("an invented one is persisted", route)
        self.assertNotIn("QUEST_VAR_COMMENT_KEYS)", route)
        self.assertNotIn("for key in envelope.QUEST_VAR_COMMENT_KEYS", route)

    def test_the_route_offers_no_fast_forward_operation(self) -> None:
        route = route_source()
        self.assertIn("fast_forward_offered=False", route)
        self.assertNotIn("FAST_FORWARD_COMMAND,", route)

    def test_the_route_derives_no_value_from_the_committed_content(self) -> None:
        route = route_source()
        for forbidden in ("get_goal_from_id", "get_attribute_from_goal_id",
                          "quests.json", "COMMITTED_REWARD_VALUE"):
            self.assertNotIn(forbidden, route, forbidden)
        self.assertIn("content_note=quest_envelope.CONTENT_RECORD_NOTE", route)

    def test_the_route_proves_over_the_complete_item_mapping(self) -> None:
        route = route_source()
        self.assertIn("items_before = copy.deepcopy(boot.map_items(user_id))",
                      route)
        self.assertIn("if items_after != items_before:", route)

    def test_the_route_contains_only_the_envelope_derivation(self) -> None:
        route = route_source()
        self.assertIn("quest_envelope.build_envelope(", route)
        self.assertIn("quest_envelope.derived_quest(", route)
        self.assertIn("quest_envelope.expected_state(", route)
        self.assertIn("boot.execute_commands(user_id, envelope_payload)", route)
        for forbidden in ("json.loads(", "subprocess", "socket", "open("):
            self.assertNotIn(forbidden, route, forbidden)

    def test_the_module_declares_no_reward_or_completion_helper(self) -> None:
        source = Path(envelope.__file__).read_text(encoding="utf-8")
        for forbidden in ("def quest_reward", "def quest_progress_ratio",
                          "def quest_remaining_time", "def mark_goal_complete",
                          "def is_goal_complete", "def fast_forward"):
            self.assertNotIn(forbidden, source, forbidden)

    def test_the_route_is_not_between_level_up_and_the_corpus_constant(self) -> None:
        """The two delivered level tests slice that span and must keep parsing."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        start = source.index("def v0_level_up()")
        span = source[start : source.index('app.config["COMPAT_LEGACY_CORPUS"]')]
        self.assertNotIn("def v0_quests(", span)
        ast.parse(textwrap.dedent(span.lstrip("\n")))

    def test_the_route_names_no_committed_reward_field(self) -> None:
        route = route_source()
        names: List[str] = []
        for node in ast.walk(ast.parse(
                "def _route():\n" + textwrap.indent(route_source(), "    "))):
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
        for forbidden in ("quest_reward", "reward_for", "goal_reward",
                          "reward_amount"):
            self.assertNotIn(forbidden, names)


class SurfaceTests(unittest.TestCase):
    """The route's surface and its neighbours."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            result = Result(APP, CLIENT.get("/v0/quests"))  # type: ignore
        self.assertEqual(result.status_code, 405)

    def test_the_other_routes_are_untouched(self) -> None:
        routes = {
            rule.rule for rule in APP.url_map.iter_rules()  # type: ignore[union-attr]
            if "GET" not in rule.methods and "POST" not in rule.methods
            and "HEAD" not in rule.methods and "OPTIONS" not in rule.methods
        }
        self.assertEqual(routes, set())
        paths = sorted(
            rule.rule for rule in APP.url_map.iter_rules()  # type: ignore[union-attr]
        )
        for expected in ("/v0/session", "/v0/bootstrap", "/v0/place",
                         "/v0/purchase", "/v0/move", "/v0/sell", "/v0/store",
                         "/v0/upgrade", "/v0/construction", "/v0/collect",
                         "/v0/expand", "/v0/queue", "/v0/collection",
                         "/v0/resurrect", "/v0/research", "/v0/quests",
                         "/v0/level_up"):
            self.assertIn(expected, paths)
        self.assertEqual(paths, sorted(set(paths)))

    def test_session_and_bootstrap_stay_byte_identical_after_an_intent(self) -> None:
        seed_state()
        with harness.offline():
            before_session = Result(APP, CLIENT.get("/v0/session")).get_json()  # type: ignore
            before_bootstrap = Result(
                APP, CLIENT.get("/v0/bootstrap?user_id=%s" % PID)).get_json()
            quests_now(intent(envelope.ACTION_END_QUEST, 7))
            after_session = Result(APP, CLIENT.get("/v0/session")).get_json()
            after_bootstrap = Result(
                APP, CLIENT.get("/v0/bootstrap?user_id=%s" % PID)).get_json()
        self.assertEqual(before_session, after_session)
        self.assertEqual(before_bootstrap, after_bootstrap)

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(harness.port_is_free("127.0.0.1", port), port)

    def test_the_delivered_state_mutating_routes_still_exist(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        for name in ("v0_place", "v0_purchase", "v0_move", "v0_sell", "v0_store",
                     "v0_upgrade", "v0_construction", "v0_collect", "v0_expand",
                     "v0_queue", "v0_collection", "v0_resurrect", "v0_research",
                     "v0_level_up", "v0_quests"):
            self.assertIn("def %s(" % name, source, name)