#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/tutorial`` vs the executed-legacy
tutorial fixture (OpenSpec task 2.4).

No server and no network: the endpoint runs through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and :meth:`NoServerTest.test_no_server_is_running` asserts that neither
the legacy port (5055) nor the Compatibility API port (5056) is listening.

What is replayed
----------------

The committed fixture under ``tests/fixtures/godot-tutorial/`` — **two**
disposable rounds, because ``playerInfo.completed_tutorial`` is ``0`` in the seed
and ``1`` after any completing step, so the ``0 -> 1`` transition is exercisable
exactly once per disposable copy:

============================  ==========================================
round                         recorded steps
============================  ==========================================
``neutral``                   ``login_post``, ``command_tutorial_15``,
                              ``command_tutorial_15_again``
``minting``                   ``login_post``, ``command_tutorial_15_minting``
============================  ==========================================

Both captured before-states are byte-identical to the committed seed, asserted
here, so the freshly built disposable corpus already **is** the captured
before-state and no save is fabricated or rewritten to make the replay line up.

Compared, leaf for leaf, with **no normalization whatsoever**:

* the response ``result`` against each captured legacy response body;
* the response ``flag_before`` / ``flag_after`` against the recorded value in the
  captured states, and against the value the committed gate derives for the
  recorded step;
* the response ``resources`` against the values read from the captured after-state;
* the response ``gate`` against the committed gate record;
* the shared derivation against the recorded request envelope, exactly (the
  recorded ``ts`` is passed back into the derivation);
* the corpus save after execution against the captured after-state, leaf for
  leaf.

**No clock normalization is needed, and none exists.** The only wall-clock field
in the request is the envelope ``ts``, which is recorded but never compared,
because it is the capture instant. No leaf of any captured after-state carries a
clock reading: the parity transaction moves only the flag, and the anchor's
movement is the client ladder's exact arithmetic under ``max(current + delta, 0)``.

The minting anchor
------------------

The parity transaction is the **neutral** one: the flag moves and nothing else
does. The **minting** round is a second recorded transaction whose whole purpose
is to be the endpoint's proof anchor — one legacy request moved **all seven**
stored resources alongside the flag through this very command. This suite
therefore asserts:

* the anchor really did move all seven resources and the flag (eight leaves), with
  the discarded ``unknown`` slot absent from the diff;
* the derivation **refuses** to express that ladder, so the endpoint's
  "no stored resource moved" half of its post-execution proof is a check with
  something real to catch rather than a vacuous property;
* the executed probe — the same ladder on a **non-completing** step — moved the
  seven resources with the flag untouched, which is what separates "completing
  the tutorial mints resources" from "the client-sent vector moves resources".

The parity claim covers these recorded transactions against the fresh-player
corpus only; see the fixture README's claim limits.
"""

from __future__ import annotations

import copy
import json
import os
import socket
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import tutorial_envelope as T

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-tutorial"

NEUTRAL_ROUND = "neutral"
MINTING_ROUND = "minting"
COMPLETING_STEP = "command_tutorial_15"
REPEAT_STEP = "command_tutorial_15_again"
ANCHOR_STEP = "command_tutorial_15_minting"
LOGIN_STEP = "login_post"

FIXTURE_FLAG_BEFORE = T.COMMITTED_FLAG_BEFORE
FIXTURE_FLAG_AFTER = T.COMMITTED_FLAG_AFTER
FIXTURE_STEP = T.MINTING_STEP
FIXTURE_VECTOR = [0] * T.RESOURCE_VECTOR_SLOTS
FIXTURE_RESOURCE_NAMES = ("xp", "gold", "wood", "steel", "oil", "cash", "mana")
FLAG_LEAF = "/%s/%s" % (T.PLAYER_INFO_RECORD, T.FLAG_KEY)

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
# Held globally on purpose: Flask's test client resolves its JSON decoder through
# a weak reference to the app, so an app that goes out of scope turns a later
# ``get_json()`` into a mis-read rather than an error.
APP = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
MANIFEST: Dict[str, Any] = {}
LOADED: Dict[str, Dict[str, Any]] = {}


def load_round(round_name: str) -> Dict[str, Any]:
    """Every recorded step of one round, plus the shared manifest."""
    steps: Dict[str, Any] = {}
    for step_name in (LOGIN_STEP, COMPLETING_STEP, REPEAT_STEP, ANCHOR_STEP):
        base = FIXTURES / "steps" / round_name / step_name
        if not base.is_dir():
            continue
        steps[step_name] = {
            "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
            "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
            "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
            "meta": json.loads(
                (base / "response.meta.json").read_text(encoding="utf-8")
            ),
            "body": (base / "response.body").read_bytes(),
        }
    return steps


def recorded_envelope(step: Dict[str, Any]) -> Dict[str, Any]:
    """The executed legacy envelope, parsed from the recorded ``data`` field.

    Parsing goes through :func:`tutorial_envelope.parse_data_field`, which also
    verifies the recorded 64-hex digest against the payload.
    """
    return T.parse_data_field(step["request"]["form"]["data"])


def recorded_intent(step: Dict[str, Any]) -> Dict[str, Any]:
    """The recorded intent, derived from the recorded command list."""
    entry = recorded_envelope(step)["commands"][0]
    return {
        "user_id": step["request"]["form"]["USERID"],
        "step": entry[2][0],
        "vector": entry[3],
        "command": entry[1],
        "map_id": entry[0],
    }


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, APP, CLIENT, PID, WORKING_TREE_PRE
    global MANIFEST, LOADED
    ORIGINAL_CWD = os.getcwd()
    MANIFEST = json.loads(
        (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
    )
    LOADED = {
        NEUTRAL_ROUND: load_round(NEUTRAL_ROUND),
        MINTING_ROUND: load_round(MINTING_ROUND),
    }
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a tutorial execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def tutorial_town(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/tutorial", json=payload)  # type: ignore[union-attr]


def reset_flag() -> None:
    """Put the in-memory save and the persisted file back at the seed flag.

    Both representations are written because the endpoint reads the in-memory
    save through the legacy accessors while the post-execution assertions read the
    persisted file, and the legacy dispatcher is what keeps the two in step.  The
    value written is the committed seed value, never a fabricated one.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["playerInfo"]["completed_tutorial"] = FIXTURE_FLAG_BEFORE
    path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


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

    collected: List[str] = []
    walk(left, right, "", collected)
    return collected


class FixtureShapeTests(unittest.TestCase):
    """The committed fixture is what this suite claims to replay."""

    def test_the_fixture_exists_and_declares_its_schema(self) -> None:
        self.assertTrue(FIXTURES.is_dir())
        self.assertEqual(MANIFEST["fixture"], "godot-tutorial")
        self.assertEqual(MANIFEST["schema"], "tutorial-fixture-v1")

    def test_both_rounds_are_recorded(self) -> None:
        rounds = {round_record["round"]: round_record for round_record in MANIFEST["rounds"]}
        self.assertEqual(sorted(rounds), [MINTING_ROUND, NEUTRAL_ROUND])
        self.assertEqual(
            [step["name"] for step in rounds[NEUTRAL_ROUND]["steps"]],
            [COMPLETING_STEP, REPEAT_STEP],
        )
        self.assertEqual(
            [step["name"] for step in rounds[MINTING_ROUND]["steps"]],
            [ANCHOR_STEP],
        )

    def test_two_rounds_were_recorded_for_the_corpus_reason(self) -> None:
        # The reason is structural, not stylistic: the 0 -> 1 transition is
        # exercisable once per disposable copy.
        self.assertIn(
            "per disposable copy", MANIFEST["why_two_rounds"].lower()
        )
        self.assertIn("not stylistic", MANIFEST["why_two_rounds"])

    def test_the_first_command_of_each_round_starts_from_the_committed_seed(self) -> None:
        # Both rounds' FIRST command has the seed as its before-state, which is
        # why the 0 -> 1 transition was capturable once per round.  The second
        # neutral step deliberately does NOT: its before-state is what its own
        # first step wrote, which is exactly why the repeat is recorded at all.
        seed = harness.load_seed()
        self.assertEqual(LOADED[NEUTRAL_ROUND][COMPLETING_STEP]["before"], seed)
        self.assertEqual(LOADED[MINTING_ROUND][ANCHOR_STEP]["before"], seed)

    def test_the_repeat_starts_from_the_completing_step_s_own_after_state(self) -> None:
        completing = LOADED[NEUTRAL_ROUND][COMPLETING_STEP]
        repeat = LOADED[NEUTRAL_ROUND][REPEAT_STEP]
        self.assertEqual(repeat["before"], completing["after"])
        self.assertNotEqual(repeat["before"], harness.load_seed())
        # ...and it changed nothing further.
        self.assertEqual(repeat["after"], completing["after"])

    def test_the_login_step_mutated_nothing(self) -> None:
        seed = harness.load_seed()
        for round_name, steps in LOADED.items():
            login = steps[LOGIN_STEP]
            self.assertEqual(login["after"], seed, round_name)
            self.assertEqual(login["meta"]["status"], 302, round_name)

    def test_no_player_state_was_fabricated(self) -> None:
        self.assertFalse(MANIFEST["target"]["fabricated_state"])
        self.assertTrue(MANIFEST["target"]["the_map_has_no_such_key"])

    def test_every_legacy_response_is_the_documented_success(self) -> None:
        for round_name, steps in LOADED.items():
            for step_name, step in steps.items():
                if step_name == LOGIN_STEP:
                    continue
                body = json.loads(step["body"].decode("utf-8"))
                self.assertEqual(body, {"result": "success"}, "%s/%s" % (round_name, step_name))
                self.assertEqual(step["meta"]["status"], 200)

    def test_the_recorded_request_carries_the_derived_intent_only(self) -> None:
        for round_name, steps in LOADED.items():
            for step_name, step in steps.items():
                if step_name == LOGIN_STEP:
                    continue
                form = step["request"]["form"]
                # USERID and user_key are transport; the only gameplay content is
                # the derived envelope, and the user_key is redacted in the record.
                self.assertEqual(sorted(form), ["USERID", "data", "language", "user_key"])
                envelope = recorded_envelope(step)
                self.assertEqual(len(envelope["commands"]), 1)
                entry = envelope["commands"][0]
                self.assertEqual(entry[0], 0)
                self.assertEqual(entry[1], "complete_tutorial")
                self.assertEqual(entry[2], [FIXTURE_STEP])
                self.assertEqual(len(entry[2]), 1)
                self.assertEqual(entry[1], recorded_intent(step)["command"])


class ParityTransactionTests(unittest.TestCase):
    """The parity transaction: the neutral round's completing step."""

    def setUp(self) -> None:
        reset_flag()

    def step(self) -> Dict[str, Any]:
        return LOADED[NEUTRAL_ROUND][COMPLETING_STEP]

    def test_the_captured_transition_is_the_flag_and_nothing_else(self) -> None:
        step = self.step()
        self.assertEqual(
            leaf_differences(step["before"], step["after"]), [FLAG_LEAF]
        )

    def test_the_captured_flag_moved_0_to_1(self) -> None:
        step = self.step()
        self.assertEqual(step["before"]["playerInfo"][T.FLAG_KEY], FIXTURE_FLAG_BEFORE)
        self.assertEqual(step["after"]["playerInfo"][T.FLAG_KEY], FIXTURE_FLAG_AFTER)

    def test_the_derived_gate_explains_the_captured_transition(self) -> None:
        # The effect is ESTABLISHED; this asserts the derivation explains it.
        step = self.step()
        self.assertTrue(T.gate_satisfied(recorded_intent(step)["step"]))
        self.assertEqual(T.COMMITTED_FLAG_AFTER, FIXTURE_FLAG_AFTER)

    def test_the_endpoint_reproduces_the_captured_transition(self) -> None:
        reset_flag()
        intent = recorded_intent(self.step())
        self.assertEqual(intent["step"], FIXTURE_STEP)
        response = tutorial_town({"user_id": PID, "step": intent["step"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["result"],
            json.loads(self.step()["body"].decode("utf-8"))["result"],
        )

    def test_the_endpoint_reproduces_the_flag_by_value(self) -> None:
        reset_flag()
        response = tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        tutorial = response.get_json()["tutorial"]
        self.assertEqual(tutorial["flag_before"], self.step()["before"]["playerInfo"][T.FLAG_KEY])
        self.assertEqual(tutorial["flag_after"], self.step()["after"]["playerInfo"][T.FLAG_KEY])

    def test_the_endpoint_reproduces_every_stored_resource_by_value(self) -> None:
        reset_flag()
        response = tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(
            response.get_json()["resources"], resources_of(self.step()["after"])
        )

    def test_the_endpoint_leaves_the_captured_after_state_byte_identical(self) -> None:
        # Leaf for leaf, no normalization: the recorded state carries no clock
        # reading, so the whole after-state must match exactly.
        reset_flag()
        tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        differences = leaf_differences(
            harness.read_seeded_save(CORPUS), self.step()["after"]  # type: ignore[arg-type]
        )
        self.assertEqual(differences, [])

    def test_the_endpoint_reports_the_captured_change_set(self) -> None:
        reset_flag()
        response = tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(response.get_json()["changed"], [FLAG_LEAF])

    def test_the_endpoint_reports_the_committed_gate_record(self) -> None:
        reset_flag()
        response = tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(response.get_json()["gate"], T.gate_record())
        self.assertEqual(MANIFEST["gate"], T.gate_record())

    def test_the_shared_derivation_reproduces_the_recorded_envelope(self) -> None:
        step = self.step()
        recorded = recorded_envelope(step)
        derived = T.build_envelope(
            step=recorded_intent(step)["step"], ts=recorded["ts"]
        )
        self.assertEqual(derived, recorded)

    def test_the_recorded_vector_is_the_neutral_one(self) -> None:
        self.assertEqual(recorded_intent(self.step())["vector"], FIXTURE_VECTOR)

    def test_the_legacy_accessors_agree_with_the_persisted_capture(self) -> None:
        reset_flag()
        tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(BOOT.completed_tutorial(PID), FIXTURE_FLAG_AFTER)  # type: ignore[union-attr]
        self.assertEqual(BOOT.resources(PID), resources_of(self.step()["after"]))  # type: ignore[union-attr]


class IdempotentRepeatTests(unittest.TestCase):
    """The recorded repeat: legacy's no-op on an already-complete flag."""

    def setUp(self) -> None:
        reset_flag()

    def repeat_step(self) -> Dict[str, Any]:
        return LOADED[NEUTRAL_ROUND][REPEAT_STEP]

    def test_the_captured_repeat_changed_nothing(self) -> None:
        step = self.repeat_step()
        self.assertEqual(
            leaf_differences(step["before"], step["after"]), []
        )
        self.assertEqual(step["after"]["playerInfo"][T.FLAG_KEY], FIXTURE_FLAG_AFTER)

    def test_the_repeat_still_answers_success(self) -> None:
        step = self.repeat_step()
        self.assertEqual(
            json.loads(step["body"].decode("utf-8")), {"result": "success"}
        )

    def test_the_endpoint_reproduces_the_no_op_rather_than_refusing_it(self) -> None:
        # Legacy answers success and changes nothing, so the endpoint answers
        # 200 with an empty change set.  Refusing would be a divergence with no
        # evidence behind it.
        reset_flag()
        first = tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(first.status_code, 200)
        second = tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(second.status_code, 200)
        body = second.get_json()
        self.assertEqual(body["result"], "success")
        self.assertFalse(body["tutorial"]["dispatched"])
        self.assertEqual(body["tutorial"]["no_op_reason"], "already_completed")
        self.assertEqual(body["changed"], [])

    def test_the_no_op_repeats_the_captured_after_state_exactly(self) -> None:
        reset_flag()
        tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(
            leaf_differences(
                harness.read_seeded_save(CORPUS), self.repeat_step()["after"]  # type: ignore[arg-type]
            ),
            [],
        )


class MintingAnchorTests(unittest.TestCase):
    """The recorded anchor: one request, all seven resources plus the flag."""

    def setUp(self) -> None:
        reset_flag()

    def anchor_step(self) -> Dict[str, Any]:
        return LOADED[MINTING_ROUND][ANCHOR_STEP]

    def test_the_anchor_moved_every_stored_resource_and_the_flag(self) -> None:
        step = self.anchor_step()
        differences = leaf_differences(step["before"], step["after"])
        self.assertEqual(len(differences), T.MINTING_CHANGED_LEAVES)
        self.assertIn(FLAG_LEAF, differences)
        for name in FIXTURE_RESOURCE_NAMES:
            self.assertNotEqual(
                resources_of(step["after"])[name], resources_of(step["before"])[name], name
            )

    def test_the_anchor_actually_moved_all_seven(self) -> None:
        step = self.anchor_step()
        before = resources_of(step["before"])
        after = resources_of(step["after"])
        moved = [name for name in FIXTURE_RESOURCE_NAMES if after[name] != before[name]]
        self.assertEqual(len(moved), T.MINTING_RESOURCES_MOVED)
        self.assertEqual(sorted(moved), sorted(FIXTURE_RESOURCE_NAMES))

    def test_the_discarded_unknown_slot_never_reached_the_save(self) -> None:
        # Slot 0 of the ladder is the vector's ``unknown``, which
        # engine.apply_resources reads and discards (engine.py:253).
        step = self.anchor_step()
        self.assertEqual(T.MINTING_LADDER[0], 101)
        differences = leaf_differences(step["before"], step["after"])
        self.assertFalse([leaf for leaf in differences if "101" in leaf])

    def test_the_derivation_refuses_to_express_the_anchor(self) -> None:
        # This is what makes the endpoint's "no stored resource moved" proof a
        # check with something real to catch.
        with self.assertRaises(T.EnvelopeError) as caught:
            T.build_envelope(FIXTURE_STEP, vector=list(T.MINTING_LADDER))
        self.assertEqual(caught.exception.code, "invalid_vector")

    def test_the_endpoint_neutral_vector_moves_nothing(self) -> None:
        reset_flag()
        before = copy.deepcopy(BOOT.resources(PID))  # type: ignore[union-attr]
        tutorial_town({"user_id": PID, "step": FIXTURE_STEP})
        self.assertEqual(BOOT.resources(PID), before)  # type: ignore[union-attr]

    def test_the_probe_separates_completion_from_the_client_vector(self) -> None:
        # The same ladder on a NON-COMPLETING step moved the seven resources with
        # the flag untouched.  Without it, "completing the tutorial mints
        # resources" would be a live misreading of the anchor.
        probe = next(
            round_record["probe"]
            for round_record in MANIFEST["rounds"]
            if round_record["round"] == MINTING_ROUND
        )
        self.assertTrue(probe["executed_in_this_capture"])
        self.assertFalse(probe["gate_satisfied"])
        self.assertFalse(probe["observed"]["flag_moved"])
        self.assertEqual(probe["observed"]["resources_moved_count"], T.MINTING_RESOURCES_MOVED)
        self.assertEqual(probe["observed"]["changed_leaf_count"], T.MINTING_RESOURCES_MOVED)
        self.assertNotIn(FLAG_LEAF, probe["observed"]["changed_leaves"])
        self.assertIn(probe["step"], T.gate_hole_steps())


class RecordedAbsenceTests(unittest.TestCase):
    """The absences this line records rather than fills."""

    def test_the_manifest_records_the_zero_consumer_flag(self) -> None:
        absences = MANIFEST["absences"]
        self.assertEqual(absences["flag_readers_in_legacy"], T.FLAG_READER_COUNT)
        self.assertEqual(absences["flag_readers_in_legacy"], 0)
        self.assertEqual(absences["flag_writer_lines"], ["command.py:65"])

    def test_the_manifest_records_no_committed_tutorial_content(self) -> None:
        absences = MANIFEST["absences"]
        self.assertEqual(
            absences["committed_tutorial_content"]["total"],
            T.COMMITTED_CONTENT_OCCURRENCES,
        )
        self.assertEqual(absences["committed_tutorial_content"]["total"], 0)

    def test_the_manifest_records_no_reward_and_no_stored_step(self) -> None:
        absences = MANIFEST["absences"]
        self.assertTrue(absences["no_reward_paid"])
        self.assertTrue(absences["no_step_persisted"])
        self.assertFalse(absences["stored_step_introduced"])

    def test_the_manifest_records_no_gate_bounds_added(self) -> None:
        self.assertFalse(MANIFEST["absences"]["gate_bounds_added"])

    def test_the_manifest_records_the_divergence_rather_than_hiding_it(self) -> None:
        absences = MANIFEST["absences"]
        self.assertFalse(absences["legacy_raising_shapes_reproduced"])
        self.assertEqual(
            absences["legacy_raising_shapes"],
            ["string_step", "missing_step", "null_step"],
        )
        self.assertIn("confined to failure handling", absences["raising_shapes_divergence"])

    def test_the_manifest_does_not_claim_the_replay_oracle(self) -> None:
        self.assertFalse(MANIFEST["gate"]["replay_oracle_is_executed_legacy"])
        self.assertEqual(
            MANIFEST["gate"]["replay_boundary_steps"], list(T.REPLAY_BOUNDARY_STEPS)
        )

    def test_the_manifest_does_not_claim_the_minting_is_reproduced(self) -> None:
        note = MANIFEST["parity"]["minting_transaction_recorded_not_reproduced"]
        self.assertIn("recorded as a step", note)
        self.assertIn("REFUSES to reproduce", note)


class NoServerTest(unittest.TestCase):
    """'No server and no network' is checked, not asserted."""

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.5)
                self.assertNotEqual(
                    probe.connect_ex(("127.0.0.1", port)), 0, "port %d is listening" % port
                )

    def test_the_replay_runs_under_the_socket_guard(self) -> None:
        reset_flag()
        with harness.offline():
            CLIENT.post("/v0/tutorial", json={"user_id": PID, "step": FIXTURE_STEP})  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
