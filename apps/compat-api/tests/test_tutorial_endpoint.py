#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/tutorial`` behavior tests (OpenSpec task 2.2).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so the suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; the
suite also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across tutorial completion.

Every test resets to the committed corpus state and asserts its post-condition
against that reset, so the suite is order-independent.

Covered:

* **the completing transition** — the gate fired, the flag reached exactly the
  committed ``1``, the response reports ``dispatched`` and names the flag leaf as
  the only change, and the whole map, the store, every other ``playerInfo``
  field, the whole ``privateState``, and all 40 placements are unchanged.
* **the two no-op cases answered 200, not an error** — a declining step and an
  already-completed flag both return ``{"result": "success"}`` with
  ``dispatched: false`` and ``changed: []``, faithfully mirroring the executed
  legacy responses.  Refusing either would be a divergence with no evidence.
* **the three legacy 500-raising shapes** — a string step, a missing step, and a
  ``null`` step each get a named code, an empty payload, and a byte-identical
  save.  A ``bool`` and a ``float`` are refused the same way.
* **the two-part post-execution proof**, and crucially its **non-tautology** —
  each clause is exercised by a stub that lets the real dispatcher run and only
  rewrites the **post**-execution read, so "every stored resource is unchanged"
  is shown to be a check rather than a vacuous property of a command that
  provably can mint.
* **intent-only input** — a client-supplied completion outcome, stored flag, or
  resource vector changes nothing, because no code path consults one.
* **no invented bound** — extreme integers are accepted exactly as legacy
  accepts them; the gate's missing bounds are not closed here.
* **fail-closed paths** — an unreadable flag, a malformed body, and an unknown
  user each return their documented structured error with the corpus
  byte-unchanged.
"""

from __future__ import annotations

import copy
import json
import os
import re
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import tutorial_envelope as T

#: A **route** decorator, matching the delivered guards' convention.  The four
#: ``@app.errorhandler`` blocks are deliberately excluded: they sit between two
#: routes, so including them would make a route slice span a handler too — a
#: pre-existing property of the module that no delivered guard relies on.
ROUTE_DECORATOR = re.compile(r'^@app\.(?:get|post)\("/v0/')

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
# The app is held in a module global on purpose: Flask's test client resolves its
# JSON decoder through a weak reference to the app, so an app that goes out of
# scope turns every later ``get_json()`` into a mis-read rather than an error.
APP = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed corpus's own tutorial facts.
COMMITTED_FLAG = 0
COMMITTED_PLACEMENTS = 40
RESOURCE_NAMES = ("xp", "gold", "wood", "steel", "oil", "cash", "mana")

FLAG_LEAF = "/playerInfo/completed_tutorial"


def set_state(flag: int = COMMITTED_FLAG) -> None:
    """Set the recorded flag, in memory **and** on disk.

    Legacy ``complete_tutorial`` assigns ``playerInfo["completed_tutorial"]`` in
    place and ``engine.apply_resources`` assigns the resource slots in place, so
    the flag lives in the in-memory save the endpoint reads and in the persisted
    corpus file.  Both representations are updated here: the endpoint reads the
    in-memory save through the legacy accessors, while this suite's
    post-execution assertions read the persisted file, and the only thing that
    keeps the two in step during normal operation is the legacy dispatcher
    persisting the whole save after each batch.  So the reset rewrites the
    disposable corpus file from the same in-memory document — a test-only,
    contained mechanism, never a claim about legacy behavior, and never touching
    a working-tree save.

    A test that deliberately replaces ``playerInfo`` with a non-mapping repairs
    it here rather than trying to assign into it, so a destructive fail-closed
    test can never poison the corpus for the tests that follow it.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    if not isinstance(save.get("playerInfo"), dict):
        save["playerInfo"] = copy.deepcopy(harness.load_seed()["playerInfo"])
    save["playerInfo"]["completed_tutorial"] = flag
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, APP, CLIENT, PID, WORKING_TREE_PRE
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
        raise AssertionError("a tutorial execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def tutorial_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/tutorial", json=payload)  # type: ignore[union-attr]


def flag_now() -> Optional[Any]:
    return BOOT.completed_tutorial(PID)  # type: ignore[union-attr]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def items_now() -> Any:
    return BOOT.map_items(PID)  # type: ignore[union-attr]


def intent(step: int = T.GATE_EXACT_ARM) -> Dict[str, Any]:
    """The whole contract: a save id and a step, nothing else."""
    return {"user_id": PID, "step": step}


def pristine() -> Dict[str, Any]:
    """Reset to the committed corpus state and snapshot it."""
    set_state()
    return {
        "flag": flag_now(),
        "resources": copy.deepcopy(resources_now()),
        "items": copy.deepcopy(items_now()),
    }


def unchanged(snapshot: Dict[str, Any]) -> None:
    self = unittest.TestCase()
    self.assertEqual(flag_now(), snapshot["flag"])
    self.assertEqual(resources_now(), snapshot["resources"])
    self.assertEqual(items_now(), snapshot["items"])


class Result:
    """A captured response plus the app that produced it.

    The app must stay referenced while the test reads the response: Flask's
    test client resolves the JSON decoder through a weak reference to the app, so
    returning only the response and letting the app go out of scope turns every
    later ``get_json()`` into a ``ReferenceError``.
    """

    def __init__(self, app: Any, response: Any) -> None:
        self.app = app
        self.response = response

    @property
    def status_code(self) -> int:
        return int(self.response.status_code)

    def get_json(self) -> Any:
        return self.response.get_json()


def _flag_rewritten_after_execution(transform: Callable[[Optional[Any]], Optional[Any]]):
    """A ``completed_tutorial`` stub that rewrites only the **post**-execution read.

    The endpoint reads the recorded flag twice — once before dispatch (for the
    unresolvable refusal, the ``already_completed`` decision, and the response's
    ``flag_before``) and once after (for the structural half of the proof and
    ``flag_after``).  Rewriting only the second read lets each clause of that half
    fail in isolation, while the real dispatcher still wrote the true flag.
    """
    original = BOOT.completed_tutorial  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Optional[Any]:
        state["seen"] += 1
        value = original(user_id)
        if state["seen"] == 1:
            return value
        return transform(value)

    return stub


def _resources_rewritten_after_execution(
    transform: Callable[[Dict[str, int]], Dict[str, int]]
):
    """A ``resources`` stub that rewrites only the **post**-execution read."""
    original = BOOT.resources  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, int]:
        state["seen"] += 1
        values = original(user_id)
        if state["seen"] == 1:
            return values
        return transform(values)

    return stub


def post_with_flag_stub(
    transform: Callable[[Optional[Any]], Optional[Any]], payload: Any
) -> Result:
    """Run one intent against a ``BOOT`` whose post flag read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.completed_tutorial  # type: ignore[union-attr]
    BOOT.completed_tutorial = _flag_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/tutorial", json=payload))
    finally:
        BOOT.completed_tutorial = original  # type: ignore[assignment]


def post_with_resources_stub(
    transform: Callable[[Dict[str, int]], Dict[str, int]], payload: Any
) -> Result:
    """Run one intent against a ``BOOT`` whose post resource read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.resources  # type: ignore[union-attr]
    BOOT.resources = _resources_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/tutorial", json=payload))
    finally:
        BOOT.resources = original  # type: ignore[assignment]


class CompletingTransitionTests(unittest.TestCase):
    """The one state transition this line delivers."""

    def test_a_completing_step_writes_the_committed_flag(self) -> None:
        pristine()
        response = tutorial_now(intent(15))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["result"], "success")
        self.assertEqual(flag_now(), T.COMMITTED_FLAG_AFTER)

    def test_the_response_reports_the_transition_verbatim(self) -> None:
        pristine()
        body = tutorial_now(intent(15)).get_json()
        tutorial = body["tutorial"]
        self.assertEqual(tutorial["command"], "complete_tutorial")
        self.assertEqual(tutorial["step"], 15)
        self.assertEqual(tutorial["step_kind"], "integer")
        self.assertEqual(tutorial["record"], "playerInfo")
        self.assertEqual(tutorial["key"], "completed_tutorial")
        self.assertEqual(tutorial["flag_before"], COMMITTED_FLAG)
        self.assertEqual(tutorial["flag_after"], T.COMMITTED_FLAG_AFTER)
        self.assertTrue(tutorial["flag_moved"])
        self.assertTrue(tutorial["gate_satisfied"])
        self.assertEqual(tutorial["gate_arm"], "exact_arm")
        self.assertFalse(tutorial["already_completed"])
        self.assertFalse(tutorial["in_gate_hole"])
        self.assertIsNone(tutorial["no_op_reason"])
        self.assertTrue(tutorial["dispatched"])
        self.assertTrue(tutorial["resolvable"])
        self.assertIs(tutorial["completed"], True)
        self.assertEqual(tutorial["stored"], T.COMMITTED_FLAG_AFTER)

    def test_the_reported_change_is_exactly_the_flag_leaf(self) -> None:
        pristine()
        body = tutorial_now(intent(15)).get_json()
        self.assertEqual(body["changed"], [FLAG_LEAF])

    def test_every_stored_resource_is_unchanged(self) -> None:
        before = pristine()
        tutorial_now(intent(15))
        after = resources_now()
        for name in RESOURCE_NAMES:
            self.assertEqual(after[name], before["resources"][name], name)

    def test_the_placements_and_the_map_are_untouched(self) -> None:
        before = pristine()
        tutorial_now(intent(15))
        self.assertEqual(items_now(), before["items"])
        self.assertEqual(len(items_now()), COMMITTED_PLACEMENTS)

    def test_the_store_and_private_state_are_untouched(self) -> None:
        pristine()
        # Deep-copied for the same reason as the playerInfo comparison above.
        before = copy.deepcopy(BOOT.save_document(PID))  # type: ignore[union-attr]
        tutorial_now(intent(15))
        after = BOOT.save_document(PID)  # type: ignore[union-attr]
        self.assertEqual(after["maps"][0]["store"], before["maps"][0]["store"])
        self.assertEqual(after["privateState"], before["privateState"])

    def test_only_the_flag_changed_in_player_info(self) -> None:
        pristine()
        # Deep-copied: save_document returns the LIVE in-memory save, so an
        # uncopied "before" would be the same object execution mutates and this
        # comparison would be vacuously empty — the same tautology this line
        # exists to avoid.
        before = copy.deepcopy(BOOT.save_document(PID))  # type: ignore[union-attr]
        tutorial_now(intent(15))
        after = BOOT.save_document(PID)  # type: ignore[union-attr]
        differing = [
            name
            for name in after["playerInfo"]
            if after["playerInfo"][name] != before["playerInfo"][name]
        ]
        self.assertEqual(differing, ["completed_tutorial"])

    def test_the_map_never_gains_a_flag_key(self) -> None:
        pristine()
        tutorial_now(intent(15))
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        self.assertNotIn(T.FLAG_KEY, save["maps"][0])

    def test_the_corpus_save_file_actually_mutated(self) -> None:
        # Non-tautological: the transition reaches the *persisted* save, not only
        # the in-memory document the accessors read.
        pristine()
        path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
        before = path.read_text(encoding="utf-8")
        tutorial_now(intent(15))
        after = path.read_text(encoding="utf-8")
        self.assertNotEqual(before, after)
        saved = json.loads(after)
        self.assertEqual(saved["playerInfo"]["completed_tutorial"], T.COMMITTED_FLAG_AFTER)

    def test_the_lower_arm_also_completes(self) -> None:
        pristine()
        body = tutorial_now(intent(25)).get_json()
        self.assertEqual(flag_now(), T.COMMITTED_FLAG_AFTER)
        self.assertEqual(body["tutorial"]["gate_arm"], "lower_arm")

    def test_no_upper_or_lower_bound_is_closed(self) -> None:
        # Legacy accepts every integer, so this endpoint must too.  Closing a
        # bound the legacy server does not have would be an invented rule, and
        # authoritative validation belongs to Server v1 (M13).
        for step in (10 ** 9, 2 ** 62):
            set_state()
            self.assertEqual(tutorial_now(intent(step)).status_code, 200, step)
            self.assertEqual(flag_now(), T.COMMITTED_FLAG_AFTER, step)
        for step in (-1, -10 ** 9, 0):
            set_state()
            body = tutorial_now(intent(step)).get_json()
            self.assertFalse(body["tutorial"]["gate_satisfied"], step)
            self.assertEqual(flag_now(), COMMITTED_FLAG, step)


class NoOpCaseTests(unittest.TestCase):
    """Both no-op cases answer 200, faithfully mirroring legacy."""

    def test_an_already_completed_flag_is_a_reported_no_op(self) -> None:
        set_state(T.COMMITTED_FLAG_AFTER)
        before = pristine_after_completion()
        body = tutorial_now(intent(15)).get_json()
        tutorial = body["tutorial"]
        self.assertEqual(body["result"], "success")
        self.assertFalse(tutorial["dispatched"])
        self.assertEqual(tutorial["no_op_reason"], "already_completed")
        self.assertTrue(tutorial["already_completed"])
        self.assertFalse(tutorial["flag_moved"])
        self.assertEqual(tutorial["flag_before"], T.COMMITTED_FLAG_AFTER)
        self.assertEqual(tutorial["flag_after"], T.COMMITTED_FLAG_AFTER)
        self.assertEqual(body["changed"], [])
        self.assertEqual(flag_now(), before["flag"])
        self.assertEqual(resources_now(), before["resources"])

    def test_a_declining_step_is_a_reported_no_op(self) -> None:
        pristine()
        before = {
            "flag": flag_now(),
            "resources": copy.deepcopy(resources_now()),
        }
        body = tutorial_now(intent(24)).get_json()
        tutorial = body["tutorial"]
        self.assertEqual(body["result"], "success")
        self.assertFalse(tutorial["dispatched"])
        self.assertEqual(tutorial["no_op_reason"], "gate_declined")
        self.assertFalse(tutorial["gate_satisfied"])
        self.assertEqual(tutorial["gate_arm"], "none")
        self.assertTrue(tutorial["in_gate_hole"])
        self.assertFalse(tutorial["flag_moved"])
        self.assertEqual(tutorial["flag_before"], COMMITTED_FLAG)
        self.assertEqual(tutorial["flag_after"], COMMITTED_FLAG)
        self.assertIs(tutorial["completed"], False)
        self.assertEqual(body["changed"], [])
        self.assertEqual(flag_now(), before["flag"])
        self.assertEqual(resources_now(), before["resources"])

    def test_every_one_of_the_nine_hole_steps_declines(self) -> None:
        for step in T.gate_hole_steps():
            pristine()
            body = tutorial_now(intent(step)).get_json()
            self.assertFalse(body["tutorial"]["gate_satisfied"], step)
            self.assertTrue(body["tutorial"]["in_gate_hole"], step)
            self.assertEqual(flag_now(), COMMITTED_FLAG, step)
            self.assertEqual(body["changed"], [], step)

    def test_a_declining_step_still_reports_the_gate_record(self) -> None:
        pristine()
        body = tutorial_now(intent(24)).get_json()
        self.assertEqual(body["gate"], T.gate_record())


def pristine_after_completion() -> Dict[str, Any]:
    """Snapshot a corpus whose flag is already the committed post-value."""
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["playerInfo"]["completed_tutorial"] = T.COMMITTED_FLAG_AFTER
    path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")
    return {
        "flag": flag_now(),
        "resources": copy.deepcopy(resources_now()),
    }


class RaisingShapeRefusalTests(unittest.TestCase):
    """The line's one deliberate divergence, confined to failure handling."""

    def _refused(self, payload: Any, code: str) -> None:
        before = {
            "flag": flag_now(),
            "resources": copy.deepcopy(resources_now()),
            "items": copy.deepcopy(items_now()),
        }
        response = tutorial_now(payload)
        self.assertEqual(response.status_code, 400, payload)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], code)
        # An empty payload: the refusal says nothing about the save.
        self.assertIsNone(body.get("tutorial"))
        self.assertIsNone(body.get("changed"))
        # And the corpus is byte-identical.
        self.assertEqual(flag_now(), before["flag"])
        self.assertEqual(resources_now(), before["resources"])
        self.assertEqual(items_now(), before["items"])

    def test_a_string_step_is_refused(self) -> None:
        pristine()
        self._refused({"user_id": PID, "step": "15"}, "invalid_step")

    def test_a_missing_step_is_refused(self) -> None:
        pristine()
        self._refused({"user_id": PID}, "missing_step")

    def test_a_null_step_is_refused(self) -> None:
        pristine()
        self._refused({"user_id": PID, "step": None}, "null_step")

    def test_a_boolean_step_is_refused(self) -> None:
        pristine()
        self._refused({"user_id": PID, "step": True}, "invalid_step")

    def test_a_float_step_is_refused(self) -> None:
        # Legacy COMPLETES on 15.0; refusing it leaves the flag untouched, which
        # is the same state outcome a declined step produces.  The measured
        # legacy fact is recorded rather than reproduced.
        pristine()
        self._refused({"user_id": PID, "step": 15.0}, "invalid_step")

    def test_a_container_step_is_refused(self) -> None:
        pristine()
        for value in ([15], {"step": 15}):
            self._refused({"user_id": PID, "step": value}, "invalid_step")

    def test_a_non_object_body_is_refused(self) -> None:
        pristine()
        response = tutorial_now([15])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_payload")

    def test_the_refusal_precedes_any_dispatch(self) -> None:
        # If a malformed step had been dispatched, the legacy branch would have
        # raised and, in the legacy server, escaped as HTTP 500.  Here the corpus
        # must be untouched and the flag unmoved.
        pristine()
        response = tutorial_now({"user_id": PID, "step": "15"})
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(flag_now(), COMMITTED_FLAG)


class PostExecutionProofTests(unittest.TestCase):
    """The two-part proof, shown to be a check rather than a tautology."""

    def test_a_flag_that_reached_the_wrong_value_fails_closed(self) -> None:
        pristine()
        response = post_with_flag_stub(lambda flag: 7, intent(15))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")

    def test_an_unwritten_flag_fails_closed(self) -> None:
        pristine()
        response = post_with_flag_stub(lambda flag: COMMITTED_FLAG, intent(15))
        self.assertEqual(response.status_code, 500)

    def test_a_flag_that_became_unreadable_fails_closed(self) -> None:
        pristine()
        response = post_with_flag_stub(lambda flag: None, intent(15))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["error"]["code"], "unresolvable_tutorial_state"
        )

    def test_each_moved_resource_fails_closed(self) -> None:
        for name in RESOURCE_NAMES:
            pristine()
            response = post_with_resources_stub(
                lambda values, moved=name: dict(values, **{moved: values[moved] + 1}),
                intent(15),
            )
            self.assertEqual(response.status_code, 500, name)
            self.assertEqual(response.get_json()["error"]["code"], "internal_error", name)
            self.assertIn(name, response.get_json()["error"]["message"])

    def test_the_resource_half_of_the_proof_is_not_vacuous(self) -> None:
        # The anchor: a captured executed-legacy transaction moved all seven
        # stored resources through THIS command, so the check above has something
        # real to catch.  Assert the anchor's shape here so the claim cannot rot
        # silently if the fixture is ever regenerated.
        self.assertEqual(T.MINTING_STEP, 15)
        self.assertEqual(T.MINTING_RESOURCES_MOVED, len(RESOURCE_NAMES))
        self.assertEqual(T.MINTING_CHANGED_LEAVES, T.MINTING_RESOURCES_MOVED + 1)
        self.assertEqual(len(list(T.MINTING_LADDER)), T.RESOURCE_VECTOR_SLOTS)

    def test_an_unchanged_resource_set_passes_the_proof(self) -> None:
        pristine()
        response = post_with_resources_stub(
            lambda values: dict(values), intent(15)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(flag_now(), T.COMMITTED_FLAG_AFTER)

    def test_a_dispatcher_failure_after_validation_is_a_structured_500(self) -> None:
        pristine()
        original = BOOT.execute_commands  # type: ignore[union-attr]

        def boom(user_id: str, envelope: Any) -> None:
            raise RuntimeError("legacy exploded")

        BOOT.execute_commands = boom  # type: ignore[assignment]
        try:
            response = tutorial_now(intent(15))
        finally:
            BOOT.execute_commands = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        # The exception type is reported; its message is not, because a legacy
        # exception text is not a contract.
        self.assertIn("RuntimeError", response.get_json()["error"]["message"])


class IntentOnlyInputTests(unittest.TestCase):
    """A client-supplied outcome, flag, or vector is never consulted."""

    def test_a_client_supplied_completion_outcome_is_ignored(self) -> None:
        pristine()
        body = tutorial_now(
            {"user_id": PID, "step": 24, "completed": True, "outcome": "success"}
        ).get_json()
        # The gate declined, so nothing was completed despite the client's claim.
        self.assertFalse(body["tutorial"]["gate_satisfied"])
        self.assertFalse(body["tutorial"]["dispatched"])
        self.assertEqual(flag_now(), COMMITTED_FLAG)

    def test_a_client_supplied_stored_flag_is_ignored(self) -> None:
        pristine()
        body = tutorial_now(
            {"user_id": PID, "step": 24, "completed_tutorial": 1}
        ).get_json()
        self.assertEqual(body["tutorial"]["flag_before"], COMMITTED_FLAG)
        self.assertEqual(body["tutorial"]["flag_after"], COMMITTED_FLAG)
        self.assertEqual(flag_now(), COMMITTED_FLAG)

    def test_a_client_supplied_vector_is_ignored(self) -> None:
        pristine()
        before = copy.deepcopy(resources_now())
        body = tutorial_now(
            {
                "user_id": PID,
                "step": 15,
                "resources_changed": list(T.MINTING_LADDER),
            }
        ).get_json()
        self.assertEqual(body["result"], "success")
        self.assertEqual(resources_now(), before)
        for name in RESOURCE_NAMES:
            self.assertEqual(resources_now()[name], before[name], name)

    def test_the_derived_vector_is_neutral_in_every_execution(self) -> None:
        # The only resource movement this endpoint can cause is none.
        pristine()
        tutorial_now(intent(15))
        self.assertEqual(resources_now(), BOOT.resources(PID))  # type: ignore[union-attr]

    def test_an_extra_unknown_key_does_not_change_the_outcome(self) -> None:
        first = pristine()
        tutorial_now(intent(15))
        baseline = {
            "flag": flag_now(),
            "resources": copy.deepcopy(resources_now()),
        }
        set_state()
        tutorial_now({"user_id": PID, "step": 15, "anything": [1, 2, 3]})
        self.assertEqual(flag_now(), baseline["flag"])
        self.assertEqual(resources_now(), baseline["resources"])
        del first


class FailClosedTests(unittest.TestCase):
    """Structurally unresolvable inputs, each with a documented code."""

    def test_an_unknown_user_is_a_404(self) -> None:
        pristine()
        response = tutorial_now({"user_id": "999999999", "step": 15})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "unknown_user_id")

    def test_a_missing_user_id_is_a_400(self) -> None:
        pristine()
        response = tutorial_now({"step": 15})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_user_id")

    def test_an_absent_flag_is_a_500_not_a_silent_completion(self) -> None:
        # The save carries no flag.  Never coerced to "not complete": that would
        # present an unreadable state as a decided one, and the legacy branch
        # would have written the key regardless.
        pristine()
        # Registered BEFORE the destructive edit so the corpus is restored even
        # when an assertion below fails; a poisoned corpus would fail every
        # later test in the run instead of just this one.
        self.addCleanup(set_state)
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        del save["playerInfo"]["completed_tutorial"]
        path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(save, stream, indent=4)
            stream.write("\n")
        self.assertIsNone(flag_now())
        response = tutorial_now(intent(15))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["error"]["code"], "unresolvable_tutorial_state"
        )
        self.assertIsNone(flag_now())

    def test_a_non_mapping_player_info_is_a_500(self) -> None:
        pristine()
        self.addCleanup(set_state)
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        save["playerInfo"] = "not a mapping"
        path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(save, stream, indent=4)
            stream.write("\n")
        response = tutorial_now(intent(15))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["error"]["code"], "unresolvable_tutorial_state"
        )


class ResponseShapeTests(unittest.TestCase):
    """The answer reports the gate record and no derived progress."""

    def test_the_gate_record_is_reported_verbatim(self) -> None:
        pristine()
        body = tutorial_now(intent(15)).get_json()
        self.assertEqual(body["gate"], T.gate_record())
        self.assertEqual(body["gate"]["lower_arm"], 25)
        self.assertEqual(body["gate"]["exact_arm"], 15)
        self.assertEqual(body["gate"]["hole_size"], 9)
        self.assertFalse(body["gate"]["has_upper_bound"])
        self.assertFalse(body["gate"]["has_lower_bound"])
        self.assertFalse(body["gate"]["has_type_check"])

    def test_the_divergence_is_reported_not_hidden(self) -> None:
        pristine()
        gate = tutorial_now(intent(15)).get_json()["gate"]
        self.assertEqual(
            gate["raising_shapes"], ["string_step", "missing_step", "null_step"]
        )
        self.assertEqual(gate["raising_status"], 500)

    def test_no_step_ratio_or_remaining_time_is_reported(self) -> None:
        pristine()
        tutorial = tutorial_now(intent(15)).get_json()["tutorial"]
        for derived in ("progress", "ratio", "remaining", "total_steps", "step_count"):
            self.assertNotIn(derived, tutorial)

    def test_the_resources_are_reported_verbatim(self) -> None:
        pristine()
        body = tutorial_now(intent(15)).get_json()
        self.assertEqual(sorted(body["resources"]), sorted(RESOURCE_NAMES))
        for name in RESOURCE_NAMES:
            self.assertEqual(body["resources"][name], resources_now()[name], name)


class RoutePlacementTests(unittest.TestCase):
    """The route's position in the file is load-bearing, and is pinned here.

    The delivered structural guards slice ``compat_service.py``'s source from
    ``def vN_x():`` up to the **next** ``@app.<method>(...)`` decorator — the
    level suite uses the corpus constant, because ``/v0/level_up`` was the last
    route when that guard was written — and require each slice to parse as
    exactly one function.  A new route declared *between* two existing ones
    therefore lands inside the preceding route's slice, at the preceding
    route's decorator indent, and the slice stops parsing.

    That was found by running the delivered suites, not by reading them: this
    route was first written after ``/v0/level_up`` and broke three guards, then
    between ``/v0/research`` and ``/v0/level_up`` and broke a fourth.  The only
    slot no slice reaches is ahead of the first route, so that is where it is
    declared, and this class asserts the property directly so a future route
    cannot reintroduce the failure by being appended in the natural place.
    """

    CORPUS_CONSTANT = 'app.config["COMPAT_LEGACY_CORPUS"]'

    def source(self) -> str:
        return Path(compat_service.__file__).read_text(encoding="utf-8")

    def decorator_lines(self, source: str) -> List[str]:
        return [
            line.strip()
            for line in source.split("\n")
            if ROUTE_DECORATOR.match(line.strip())
        ]

    def test_the_tutorial_route_is_declared_before_every_other_route(self) -> None:
        decorators = self.decorator_lines(self.source())
        self.assertGreater(len(decorators), 10)
        self.assertEqual(decorators[0], '@app.post("/v0/tutorial")')

    def test_the_level_route_is_still_the_last_one(self) -> None:
        # The level suite's end marker is the corpus constant rather than a
        # following decorator, so it depends on this being true.
        decorators = self.decorator_lines(self.source())
        self.assertEqual(decorators[-1], '@app.post("/v0/level_up")')

    def test_the_tutorial_route_is_in_no_other_routes_slice(self) -> None:
        # The invariant that broke, stated generally: the tutorial route must not
        # fall between any other route's ``def`` and whatever follows it.  Each
        # delivered family picks its own end marker (the next route decorator, or
        # ``@app.errorhandler(400)``, or the corpus constant), so this asserts the
        # property against **every** ``@app.`` decorator of any kind — a strict
        # superset of all the delivered markers, which makes it immune to their
        # differing conventions.
        source = self.source()
        starts_at = []
        cursor = 0
        for line in source.split("\n"):
            starts_at.append(cursor)
            cursor += len(line) + 1
        markers = sorted(
            starts_at[i]
            for i, line in enumerate(source.split("\n"))
            if line.strip().startswith("@app.")
        )
        corpus = source.index(self.CORPUS_CONSTANT)
        names = (
            "session", "bootstrap", "place", "purchase", "move", "sell",
            "store", "upgrade", "construction", "collect", "expand",
            "queue", "collection", "resurrect", "quests", "research",
            "level_up",
        )
        self.assertGreaterEqual(len(markers), 21)
        for name in names:
            offset = source.index("def v0_%s()" % name)
            following = [m for m in markers if m > offset]
            end = following[0] if following else corpus
            self.assertNotIn("def v0_tutorial(", source[offset:end], name)

    def test_the_two_most_fragile_delivered_spans_still_parse(self) -> None:
        # These two are the spans the two rejected placements actually broke —
        # research ends at the level decorator and level_up at the corpus
        # constant — so they are checked as they stand today.
        import ast
        import textwrap

        source = self.source()
        spans = (
            (
                "research",
                source.index("def v0_research()"),
                source.index('@app.post("/v0/level_up")'),
                "v0_research",
            ),
            (
                "level_up",
                source.index("def v0_level_up()"),
                source.index(self.CORPUS_CONSTANT),
                "v0_level_up",
            ),
            (
                "quests",
                source.index("def v0_quests()"),
                source.index('@app.post("/v0/research")'),
                "v0_quests",
            ),
            (
                "expand",
                source.index("def v0_expand()"),
                source.index("@app.errorhandler(400)"),
                "v0_expand",
            ),
        )
        for label, start, end, expected in spans:
            tree = ast.parse(textwrap.dedent(source[start:end].lstrip("\n")))
            self.assertEqual(
                [n.name for n in tree.body if isinstance(n, ast.FunctionDef)],
                [expected],
                label,
            )

    def test_the_placement_note_is_present_where_the_route_is_declared(self) -> None:
        source = self.source()
        note = source.index("@app.post(\"/v0/tutorial\")")
        # The comment sits directly above the decorator, so the reasoning
        # travels with the code rather than living only in a test.
        preceding = source[:note].split("\n")[-14:]
        self.assertIn("order is load-bearing", "\n".join(preceding))
        self.assertIn("pins this", "\n".join(preceding))


class LegacyBootAccessorTests(unittest.TestCase):
    """The ``completed_tutorial`` accessor itself (design D2)."""

    def test_it_reads_the_stored_save_not_the_in_memory_player_info(self) -> None:
        pristine()
        self.assertEqual(BOOT.completed_tutorial(PID), COMMITTED_FLAG)  # type: ignore[union-attr]
        # player_info runs the legacy in-memory get_player_info, whose side
        # effects would make it unusable as a "before" reading.
        self.assertIsInstance(BOOT.player_info(PID), dict)  # type: ignore[union-attr]

    def test_it_returns_the_value_verbatim(self) -> None:
        for value in (0, 1, 7, "1", True):
            set_state(value)  # type: ignore[arg-type]
            self.assertEqual(BOOT.completed_tutorial(PID), value)  # type: ignore[union-attr]
        set_state()

    def test_an_absent_flag_is_none_not_false(self) -> None:
        pristine()
        self.addCleanup(set_state)
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        del save["playerInfo"]["completed_tutorial"]
        path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(save, stream, indent=4)
            stream.write("\n")
        self.assertIsNone(BOOT.completed_tutorial(PID))  # type: ignore[union-attr]

    def test_an_unknown_user_is_refused_not_none(self) -> None:
        with self.assertRaises(compat_legacy.LegacyBootError):
            BOOT.completed_tutorial("999999999")  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
