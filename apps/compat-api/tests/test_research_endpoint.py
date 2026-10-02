#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/research`` behavior tests (OpenSpec task 3.3/3.4).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so the suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across research execution.

The committed corpus carries every research counter at ``[0, 0]``, so all four
branches are exercisable against it **with no fabricated player state**.

Covered:

* **the four branches over both tracks** — the derived counters, the item
  branch's **paired** step-and-instant reset, the cash branch's **instant-only**
  zeroing, the reset branch's three-counter zeroing, the **unaddressed** track
  byte-identical, and **every one of the seven stored resources unchanged**.
* **intent only** — a request carrying ``step``, ``item``, ``timestamp``,
  ``instant``, ``cash``, ``price``, ``cost``, ``step_count``, ``reward``,
  ``remaining``, ``ready``, ``resources_changed``, ``vector``, and
  ``seconds`` changes nothing, and the response **echoes no ignored value**.
* **the two-part post-execution proof** — a vector that does not match the
  derived result, and **any** stored resource that moved, each fail closed with
  ``internal_error``.  Each is exercised by a stub that lets the real dispatcher
  run and rewrites only the **post** read.
* **the two structural refusals** — a track that is not an integer, and a
  research state that does not resolve — each with its named code, an **empty**
  payload, and a byte-identical vector before and after.
* **the full-resource comparison**, and a test that proves a selected-subset
  comparison would be **insufficient**: every one of the seven stored resources
  is compared, not a selected few.
* **the recorded absences** — the route contains no price, readiness,
  completion, remaining-time, unlock, bound, or reward computation, and offers no
  fast-forward action.
* **session/bootstrap byte-identity** after research intents, and that every
  other delivered route is untouched.
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
import research_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")
COMMITTED_RESOURCES = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}
# Every action the endpoint offers, over both tracks: the eight branch-track
# combinations.
ALL_INTENTS = [
    (action, track)
    for action in sorted(research_envelope.ACTIONS)
    for track in (0, 1)
]


def pristine_vector() -> Dict[str, Any]:
    """The committed initial research vector, reset **in memory and on disk**.

    The legacy research branches mutate these very lists in place
    (``save["privateState"]["researchStepNumber"][_type] += 1``), so the reset
    updates both representations — exactly the mechanism the legacy dispatcher
    itself uses to keep them in step.  It is a test-only, contained reset and
    never a claim about legacy behaviour or a working-tree write.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    for key in research_envelope.COUNTERS:
        save["privateState"][key] = list(research_envelope.COMMITTED_VECTOR[key])
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")
    return research_envelope.snapshot_counters(save)


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE
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
        raise AssertionError("a research execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def research_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/research", json=payload)  # type: ignore[union-attr]


def vector_now() -> Dict[str, List[int]]:
    return research_envelope.snapshot_counters(BOOT.save_document(PID))  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def intent(action: str, track: Any = 0) -> Dict[str, Any]:
    """The whole contract: a save id, a closed action, and a track."""
    return {"user_id": PID, "action": action, "track": track}


class Result:
    """A captured response plus the app that produced it.

    Flask's test client resolves the JSON decoder through a weak reference to
    the app, so returning only the response and letting the app go out of scope
    turns every later ``get_json()`` into a ``ReferenceError``.
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
    """Install an instance-level stub on ``BOOT`` and restore it EXACTLY.

    A plain ``setattr``/``restore`` pair would leave the *unbound* class function
    behind in the instance dictionary and every later call would miss its
    ``self`` argument — a failure that shows up as an unrelated ``TypeError``
    several tests later.
    """
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


def _resources_rewritten_after_execution(
    transform: Callable[[Dict[str, int]], Dict[str, int]]
) -> Callable[[str], Dict[str, int]]:
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


def post_with_resources_stub(
    transform: Callable[[Dict[str, int]], Dict[str, int]],
    payload: Dict[str, Any],
) -> Result:
    """Run one intent against a ``BOOT`` whose post resource read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    with patched_boot("resources", _resources_rewritten_after_execution(transform)):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/research", json=payload))


def post_with_state_stub(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]],
    payload: Dict[str, Any],
    attribute: str = "save_document",
) -> Result:
    """Run one intent against a ``BOOT`` whose post-execution save read is stubbed.

    The endpoint reads the save **twice** — once before dispatch for the
    derivation and once after it for the proof — through the same accessor, so
    rewriting only the second read reproduces a persisted state legacy could
    never report while leaving the pre-execution derivation and the real
    dispatcher's own write untouched.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    real = getattr(BOOT, attribute)
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, Any]:
        state["seen"] += 1
        document = real(user_id)
        if state["seen"] == 1:
            return document
        return transform(document)

    with patched_boot(attribute, stub):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/research", json=payload))


class SuccessfulIntentTests(unittest.TestCase):
    """Every branch, every track: the derived effect and nothing else."""

    def test_all_eight_branch_track_combinations_succeed_and_derive_their_effect(
        self,
    ) -> None:
        for action, track in ALL_INTENTS:
            with self.subTest(action=action, track=track):
                before = pristine_vector()
                resources_before = copy.deepcopy(resources_now())
                items_before = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
                derived = research_envelope.derived_research(before, track, action)
                response = research_now(intent(action, track))
                self.assertEqual(response.status_code, 200)
                body = response.get_json()
                self.assertTrue(body["ok"])
                self.assertEqual(body["protocol"], "compat-v0")
                self.assertEqual(body["result"], "success")
                self.assertEqual(body["action"], action)
                self.assertEqual(body["track"], track)
                self.assertEqual(body["command"], derived["command"])
                # The response's own before/after projections.
                self.assertEqual(body["previous"]["counters"], before)
                self.assertEqual(len(body["previous"]["tracks"]), 2)
                self.assertEqual(body["previous"]["derived"], {})
                after = body["research"]["counters"]
                expected = research_envelope.expected_state(
                    before, action, track, after
                )
                self.assertIsNone(expected, expected)
                # The derived block: the service's own values, never the client's.
                if derived["stamps_instant"]:
                    self.assertIsNone(body["derived"]["instant"])
                    self.assertTrue(body["derived"]["stamps_instant"])
                else:
                    self.assertEqual(body["derived"]["instant"],
                                     derived["instant"])
                    self.assertFalse(body["derived"]["stamps_instant"])
                self.assertEqual(body["derived"]["step"], derived["step"])
                self.assertEqual(body["derived"]["item"], derived["item"])
                self.assertEqual(sorted(body["derived"]["written"]),
                                 sorted(derived["written"]))
                # Every stored resource is unchanged: the no-price proof.
                self.assertEqual(resources_now(), resources_before)
                self.assertEqual(body["resources"], resources_before)
                # And the placement map is untouched: a research command writes no
                # row at all.
                self.assertEqual(BOOT.map_items(PID), items_before)  # type: ignore[union-attr]
                self.assertEqual(len(BOOT.map_items(PID)), 40)  # type: ignore[union-attr]
                self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_step_branch_increments_the_step_and_stamps_the_instant(self) -> None:
        before = pristine_vector()
        response = research_now(intent("next_step", 0))
        self.assertEqual(response.status_code, 200)
        after = vector_now()
        self.assertEqual(after["researchStepNumber"], [1, 0])
        self.assertEqual(after["researchItemNumber"], [0, 0])
        self.assertGreater(after["timeStampDoResearch"][0], 0)
        self.assertEqual(after["timeStampDoResearch"][1],
                         before["timeStampDoResearch"][1])
        # A second step increments again.
        response = research_now(intent("next_step", 0))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(vector_now()["researchStepNumber"], [2, 0])

    def test_the_item_branch_resets_the_step_and_the_instant_together(self) -> None:
        # Set the track up first: a step must be in flight for the pairing to be
        # observable at all.
        pristine_vector()
        research_now(intent("next_step", 0))
        primed = vector_now()
        self.assertEqual(primed["researchStepNumber"], [1, 0])
        self.assertGreater(primed["timeStampDoResearch"][0], 0)
        response = research_now(intent("next_item", 0))
        self.assertEqual(response.status_code, 200)
        after = vector_now()
        self.assertEqual(after["researchStepNumber"], [0, 0])
        self.assertEqual(after["researchItemNumber"], [1, 0])
        self.assertEqual(after["timeStampDoResearch"], [0, 0])
        body = response.get_json()
        self.assertTrue(body["derived"]["paired_reset"])
        self.assertEqual(sorted(body["derived"]["written"]),
                         ["researchItemNumber", "researchStepNumber",
                          "timeStampDoResearch"])

    def test_the_cash_branch_zeroes_only_the_instant_and_charges_nothing(self) -> None:
        pristine_vector()
        research_now(intent("next_step", 0))
        research_now(intent("next_item", 0))
        research_now(intent("next_step", 0))
        primed = vector_now()
        self.assertEqual(primed["researchStepNumber"], [1, 0])
        resources_before = copy.deepcopy(resources_now())
        response = research_now(intent("buy_step_cash", 0))
        self.assertEqual(response.status_code, 200)
        after = vector_now()
        # ONLY the instant moved: the step and item counters survived intact.
        self.assertEqual(after["researchStepNumber"], [1, 0])
        self.assertEqual(after["researchItemNumber"], [1, 0])
        self.assertEqual(after["timeStampDoResearch"], [0, 0])
        body = response.get_json()
        self.assertEqual(body["cash_charged"], 0)
        self.assertTrue(body["cash_argument_ignored"])
        self.assertFalse(body["price_computed"])
        self.assertEqual(body["resources"], resources_before)

    def test_the_reset_branch_zeroes_all_three_counters_of_one_track_only(self) -> None:
        pristine_vector()
        for track in (0, 1):
            research_now(intent("next_step", track))
        research_now(intent("next_item", 0))
        research_now(intent("next_item", 1))
        primed = vector_now()
        self.assertEqual(primed["researchStepNumber"], [0, 0])
        self.assertEqual(primed["researchItemNumber"], [1, 1])
        # Put a step in flight on track 1 only, then reset track 0.
        research_now(intent("next_step", 1))
        response = research_now(intent("reset_item", 0))
        self.assertEqual(response.status_code, 200)
        after = vector_now()
        self.assertEqual(after["researchItemNumber"], [0, 1])
        self.assertEqual(after["researchStepNumber"], [0, 1])
        self.assertGreater(after["timeStampDoResearch"][1], 0)
        self.assertEqual(after["timeStampDoResearch"][0], 0)

    def test_a_full_cycle_returns_the_vector_to_its_initial_state(self) -> None:
        pristine_vector()
        for action in ("next_step", "next_item", "reset_item"):
            self.assertEqual(research_now(intent(action, 0)).status_code, 200)
        self.assertEqual(vector_now(), research_envelope.COMMITTED_VECTOR)

    def test_the_response_reports_both_tracks_with_their_committed_building_ids(
        self,
    ) -> None:
        pristine_vector()
        response = research_now(intent("next_step", 0))
        body = response.get_json()
        self.assertEqual(body["tracks"], [0, 1])
        self.assertEqual(
            [(record["track"], record["name"], record["building_id"])
             for record in body["tracks_source"]],
            [(0, "TYPE_AREA_51", 139), (1, "TYPE_ROBOTIC", 86)],
        )
        self.assertFalse(any(record["defined_in_server"]
                             for record in body["tracks_source"]))

    def test_the_response_states_that_no_fast_forward_is_offered(self) -> None:
        pristine_vector()
        response = research_now(intent("next_step", 0))
        self.assertIs(response.get_json()["fast_forward_offered"], False)

    def test_the_response_carries_no_readiness_or_derived_field(self) -> None:
        pristine_vector()
        body = research_now(intent("next_step", 0)).get_json()
        self.assertEqual(sorted(body["research"]),
                         ["counters", "derived", "track_count", "tracking_note",
                          "tracks", "tracks_source", "verbatim"])
        for row in body["research"]["tracks"]:
            self.assertEqual(sorted(row), ["instant", "item", "step", "track"])


class IntentOnlyTests(unittest.TestCase):
    """No client value is trusted, and none is echoed (design D2)."""

    IGNORED_KEYS = (
        "step", "item", "timestamp", "instant", "cash", "price", "cost",
        "step_count", "reward", "remaining", "ready", "duration",
        "resources_changed", "vector", "seconds", "fast_forward", "type",
        "unlock", "requirement",
    )

    def test_a_request_carrying_every_derived_key_changes_nothing(self) -> None:
        before = pristine_vector()
        payload = intent("next_step", 1)
        payload.update({
            "step": 999, "item": 999, "timestamp": 1, "instant": 1,
            "cash": 2500, "price": 2500, "cost": 2500, "step_count": 999,
            "reward": "gold", "remaining": 42, "ready": True,
            "duration": 3600, "resources_changed": [0, 0, -2500, 0, 0, 0, 0, 0],
            "vector": [0, 0, -2500, 0, 0, 0, 0, 0], "seconds": 9999999,
            "fast_forward": 9999999, "type": 7, "unlock": True,
            "requirement": "none",
        })
        resources_before = copy.deepcopy(resources_now())
        response = research_now(payload)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        after = vector_now()
        # The counters moved exactly as the branch dictates and NOTHING else:
        # the unaddressed track's step counter is 0, not 999.
        self.assertEqual(after["researchStepNumber"], [0, 1])
        self.assertEqual(after["researchItemNumber"], [0, 0])
        self.assertEqual(after["researchStepNumber"][0], before
                         ["researchStepNumber"][0])
        # The client's cash, price, vector, and seconds were IGNORED and not
        # echoed: the only cash figure in the response is the derived zero, and
        # the client's negative gold delta did not move a balance.
        self.assertEqual(body["cash_charged"], 0)
        self.assertEqual(resources_now(), resources_before)
        for key in self.IGNORED_KEYS:
            with self.subTest(key=key):
                self.assertNotIn(key, body)

    def test_the_client_sends_only_a_player_identifier_an_action_and_a_track(
        self,
    ) -> None:
        pristine_vector()
        body = research_now(intent("next_item", 1)).get_json()
        # The save identity is NEVER echoed back, and neither is any ignored
        # key.  `action` and `track` ARE echoed — exactly as the queue endpoint
        # echoes its `action` and `map_key` — so the client can confirm the
        # service resolved the intent it sent and nothing else.
        self.assertNotIn("user_id", body)
        for key in self.IGNORED_KEYS:
            with self.subTest(key=key):
                self.assertNotIn(key, body)
        self.assertEqual(body["action"], "next_item")
        self.assertEqual(body["track"], 1)

    def test_the_module_derives_the_cash_argument_server_side(self) -> None:
        self.assertEqual(research_envelope.DERIVED_CASH, 0)
        envelope = research_envelope.build_envelope(
            track=1, action="buy_step_cash", ts=1700000000
        )
        self.assertEqual(envelope["commands"][0][2], [0, 1])


class TwoPartProofTests(unittest.TestCase):
    """The post-execution proof fails closed on either half (design D3)."""

    def test_a_vector_that_does_not_match_the_derived_result_fails_closed(self) -> None:
        def wrong_step(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"]["researchStepNumber"][0] = 99
            return document

        pristine_vector()
        response = post_with_state_stub(
            wrong_step, intent("next_step", 0)
        )
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("step counter", body["error"]["message"])

    def test_a_stamp_that_moved_backwards_fails_closed(self) -> None:
        # A backwards stamp is only observable against a track that ALREADY
        # carries one, so the track is primed with a real step first: the
        # endpoint's first read then holds a genuine wall-clock instant and the
        # stub rewrites only the post-execution read to a value below it.
        def backwards(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"]["timeStampDoResearch"][0] = 1
            return document

        pristine_vector()
        self.assertEqual(research_now(intent("next_step", 0)).status_code, 200)
        primed = vector_now()
        self.assertGreater(primed["timeStampDoResearch"][0], 1)
        response = post_with_state_stub(backwards, intent("next_step", 0))
        self.assertEqual(response.status_code, 500)
        self.assertIn("backwards", response.get_json()["error"]["message"])
        # The same instant is accepted when it only moves FORWARD.
        def forwards(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"]["timeStampDoResearch"][0] = (
                primed["timeStampDoResearch"][0] + 10
            )
            return document

        accepted = post_with_state_stub(forwards, intent("next_step", 0))
        self.assertEqual(accepted.status_code, 200)

    def test_the_unaddressed_track_moving_fails_closed(self) -> None:
        def other_track(document: Dict[str, Any]) -> Dict[str, Any]:
            document["privateState"]["researchStepNumber"][1] = 7
            return document

        pristine_vector()
        response = post_with_state_stub(other_track, intent("next_step", 0))
        self.assertEqual(response.status_code, 500)
        self.assertIn("UNADDRESSED track", response.get_json()["error"]["message"])

    def test_any_stored_resource_that_moved_fails_closed(self) -> None:
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                pristine_vector()

                def moved(values: Dict[str, int], slot: str = name) -> Dict[str, int]:
                    changed = dict(values)
                    changed[slot] = changed[slot] + 2500
                    return changed

                response = post_with_resources_stub(moved, intent("next_step", 0))
                self.assertEqual(response.status_code, 500)
                body = response.get_json()
                self.assertEqual(body["error"]["code"], "internal_error")
                self.assertIn("resource %s" % name, body["error"]["message"])

    def test_the_proof_compares_every_stored_resource_not_a_subset(self) -> None:
        """Task 3.4's verification: a selected-subset comparison is insufficient.

        The endpoint compares ``sorted(resources_after)`` against
        ``resources_before`` name by name.  This test proves the comparison is
        over the **complete** set by stubbing each of the seven slots in turn and
        requiring a failure for every one of them — a comparison that looked at,
        say, only ``gold`` and ``xp`` would let the other five through.
        """
        compared = set()
        pristine_vector()
        for name in RESOURCE_NAMES:
            def moved(values: Dict[str, int], slot: str = name) -> Dict[str, int]:
                changed = dict(values)
                changed[slot] = changed[slot] - 1
                return changed

            response = post_with_resources_stub(moved, intent("next_step", 0))
            self.assertEqual(
                response.status_code, 500,
                "moving %s alone must fail the proof" % name,
            )
            self.assertIn(name, response.get_json()["error"]["message"])
            compared.add(name)
        self.assertEqual(compared, set(RESOURCE_NAMES))
        self.assertEqual(len(compared), 7)

    def test_the_endpoint_reads_the_stored_resource_set_in_full(self) -> None:
        """The adapter's own accessor returns exactly seven slots, and the route
        iterates the whole mapping rather than a fixed list."""
        pristine_vector()
        response = research_now(intent("next_step", 0))
        self.assertEqual(sorted(response.get_json()["resources"]),
                         sorted(RESOURCE_NAMES))
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = source[source.index("def v0_research()"):]
        route = route[: route.index('@app.post("/v0/level_up")')]
        self.assertIn("for name in sorted(resources_after):", route)
        self.assertNotIn('["gold", "xp"]', route)


class RefusalTests(unittest.TestCase):
    """The two structural refusals, each leaving the corpus alone."""

    def test_a_track_that_is_not_an_integer_is_refused(self) -> None:
        for track in ["0", None, 1.0, True, [], {}]:
            with self.subTest(track=track):
                before = pristine_vector()
                response = research_now(intent("next_step", track))
                self.assertEqual(response.status_code, 400)
                body = response.get_json()
                self.assertFalse(body["ok"])
                self.assertEqual(body["error"]["code"], "invalid_track")
                self.assertNotEqual(body["error"]["message"], "")
                # No partial payload beyond the error itself.
                self.assertEqual(sorted(body), ["error", "ok", "protocol"])
                self.assertEqual(vector_now(), before)

    def test_a_track_outside_the_two_the_vector_addresses_is_refused(self) -> None:
        for track in [2, 7, 999, -1]:
            with self.subTest(track=track):
                before = pristine_vector()
                response = research_now(intent("next_step", track))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "invalid_track")
                self.assertEqual(vector_now(), before)

    def test_a_missing_track_is_refused_with_its_own_code(self) -> None:
        before = pristine_vector()
        payload = intent("next_step")
        payload.pop("track")
        response = research_now(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_track")
        self.assertEqual(vector_now(), before)

    def test_an_unresolvable_research_state_is_refused_with_its_own_code(self) -> None:
        malformed = [
            {},
            {"researchStepNumber": {}, "researchItemNumber": [0, 0],
             "timeStampDoResearch": [0, 0]},
            {"researchStepNumber": [0], "researchItemNumber": [0, 0],
             "timeStampDoResearch": [0, 0]},
            {"researchStepNumber": ["0", 0], "researchItemNumber": [0, 0],
             "timeStampDoResearch": [0, 0]},
            {"researchStepNumber": [-1, 0], "researchItemNumber": [0, 0],
             "timeStampDoResearch": [0, 0]},
            {"researchStepNumber": [0, 0], "researchItemNumber": [0, 0]},
        ]
        for state in malformed:
            with self.subTest(state=state):
                pristine_vector()
                save = BOOT.save_document(PID)  # type: ignore[union-attr]
                save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
                with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
                    json.dump(save, stream, indent=4)
                    stream.write("\n")
                original = BOOT.save_document  # type: ignore[union-attr]
                state_box = {"seen": 0}

                def stub(user_id: str, _state=state) -> Dict[str, Any]:
                    state_box["seen"] += 1
                    document = original(user_id)
                    if state_box["seen"] == 1:
                        for key in list(document["privateState"]):
                            if key in research_envelope.COUNTERS:
                                document["privateState"].pop(key)
                        for key, value in _state.items():
                            document["privateState"][key] = value
                    return document

                with patched_boot("save_document", stub):
                    response = research_now(intent("next_step", 0))
                self.assertEqual(response.status_code, 409)
                body = response.get_json()
                self.assertEqual(body["error"]["code"],
                                 "unresolvable_research_state")
                self.assertEqual(sorted(body), ["error", "ok", "protocol"])
                self.assertNotEqual(body["error"]["message"], "")
                pristine_vector()

    def test_an_unknown_action_and_a_missing_action_are_refused(self) -> None:
        before = pristine_vector()
        unknown = research_now(intent("fast_forward", 0))
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.get_json()["error"]["code"], "invalid_action")
        payload = intent("next_step", 0)
        payload.pop("action")
        missing = research_now(payload)
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.get_json()["error"]["code"], "missing_action")
        self.assertEqual(vector_now(), before)

    def test_the_shared_identity_refusals_come_first(self) -> None:
        for payload, code, status in (
            ({}, "missing_user_id", 400),
            ({"user_id": "  "}, "missing_user_id", 400),
            ({"user_id": 7}, "invalid_user_id", 400),
            ({"user_id": "does-not-exist-0000"}, "unknown_user_id", 404),
        ):
            with self.subTest(payload=payload):
                body = research_now(payload).get_json()
                self.assertFalse(body["ok"])
                self.assertEqual(body["error"]["code"], code)

    def test_a_non_object_body_is_refused(self) -> None:
        with harness.offline():
            response = CLIENT.post("/v0/research", json=["not", "an", "object"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_payload")


class RecordedAbsenceTests(unittest.TestCase):
    """The route computes no price, readiness, bound, or reward (D1/D4/D6/D7)."""

    def route_source(self) -> str:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = source[source.index("def v0_research()"):]
        return route[: route.index('@app.post("/v0/level_up")')]

    def route_function(self) -> Any:
        function = ast.parse(
            textwrap.dedent(self.route_source().lstrip("\n"))
        ).body[0]
        # The docstring is PROSE, and prose is exactly what these checks must
        # not read: it is dropped before the tree is walked.
        if (function.body and isinstance(function.body[0], ast.Expr)
                and isinstance(function.body[0].value, ast.Constant)
                and isinstance(function.body[0].value.value, str)):
            function.body = function.body[1:]
        return function

    def route_identifiers(self) -> List[str]:
        """Every identifier the route's CODE names or binds.

        Collected through ``ast`` rather than by scanning text, so a docstring
        sentence or a recorded refusal phrase can never be mistaken for
        behaviour.
        """
        names: List[str] = []
        for node in ast.walk(self.route_function()):
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
            elif isinstance(node, ast.arg):
                names.append(node.arg)
            elif isinstance(node, ast.keyword) and node.arg:
                names.append(node.arg)
        return names

    def route_string_constants(self) -> List[str]:
        """Every string LITERAL in the route's code, docstring excluded."""
        return [
            node.value for node in ast.walk(self.route_function())
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]

    def route_calls(self) -> List[str]:
        calls: List[str] = []
        for node in ast.walk(self.route_function()):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        return calls

    def test_the_route_names_every_design_decision(self) -> None:
        route = self.route_source()
        for named in ("Design D1", "Design D2", "Design D3", "Design D6",
                      "Design D7"):
            with self.subTest(named=named):
                self.assertIn(named, route)

    def test_the_route_computes_no_price_and_no_reward(self) -> None:
        identifiers = self.route_identifiers()
        for token in ("reward", "prize", "grant", "cost", "price"):
            with self.subTest(token=token):
                offenders = [
                    name for name in identifiers
                    if token in name.lower()
                    and name not in ("price_computed", "ERROR_INTERNAL")
                ]
                # `cash_charged` is the DERIVED zero the response reports and
                # `NO_PRICE`/`NO_REWARD` are the module's recorded refusals; the
                # route names no other cash or price quantity.
                self.assertEqual(offenders, [], sorted(set(offenders)))
        self.assertIn("cash_charged", self.route_source())
        self.assertIn("cash_argument_ignored", self.route_source())

    def test_the_route_computes_no_readiness_or_elapsed_time(self) -> None:
        identifiers = self.route_identifiers()
        for token in ("ready", "remaining", "elapsed", "duration", "complete"):
            with self.subTest(token=token):
                offenders = [name for name in identifiers if token in name.lower()]
                self.assertEqual(offenders, [], sorted(set(offenders)))
        # No clock and no arithmetic helper the route could use to derive one.
        for banned in ("time", "time_ns", "monotonic", "datetime", "now",
                       "sleep"):
            with self.subTest(call=banned):
                self.assertNotIn(banned, self.route_calls())

    def test_the_route_adds_no_counter_bound_or_clamp(self) -> None:
        for banned in ("min", "max", "clamp", "bound", "limit", "ceil", "floor",
                       "round"):
            with self.subTest(call=banned):
                self.assertNotIn(banned, self.route_calls())

    def test_the_route_derives_no_value_from_a_track_or_a_building(self) -> None:
        identifiers = self.route_identifiers()
        literals = self.route_string_constants()
        for token in ("TYPE_AREA_51", "TYPE_ROBOTIC", "139", "86"):
            with self.subTest(token=token):
                # The names appear ONLY as reported data reached through
                # `research_envelope.TRACKS`; the route neither names nor
                # computes with either of them.
                self.assertNotIn(token, identifiers)
                self.assertNotIn(token, literals)
        self.assertEqual(
            [name for name in identifiers
             if name in ("ID_BUILDING_AREA_51", "ID_BUILDING_ROBOTIC_CENTER")],
            [],
        )

    def test_the_route_offers_no_fast_forward_operation(self) -> None:
        self.assertNotIn("fast_forward", research_envelope.ACTIONS)
        identifiers = self.route_identifiers()
        self.assertNotIn("FAST_FORWARD_COMMAND", identifiers)
        self.assertNotIn(
            "build_envelope", [
                name for name in identifiers
                if name == "fast_forward"
            ],
        )
        self.assertIn("fast_forward_offered", self.route_source())

    def test_the_route_parses_and_contains_only_the_envelope_derivation(self) -> None:
        route = self.route_source()
        ast.parse(textwrap.dedent(route.lstrip("\n")))
        names: List[str] = []
        for node in ast.walk(ast.parse(textwrap.dedent(route.lstrip("\n")))):
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
        for called in ("build_envelope", "derived_research", "expected_state",
                       "snapshot_counters", "project_research", "execute_commands",
                       "resources"):
            with self.subTest(call=called):
                self.assertIn(called, names)

    def test_the_module_declares_no_price_or_readiness_helper(self) -> None:
        tree = ast.parse(Path(research_envelope.__file__).read_text(encoding="utf-8"))
        declared = sorted(
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        self.assertEqual(
            declared,
            [
                "build_envelope", "command_for_action", "copy_vector",
                "derived_research", "expected_state", "is_action", "is_track",
                "neutral_vector", "project_research", "resolve_vector",
                "snapshot_counters", "validate_vector",
            ],
        )


class SurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/research")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["error"]["code"], "method_not_allowed")

    def test_the_other_routes_are_untouched(self) -> None:
        with harness.offline():
            self.assertEqual(CLIENT.get("/v0/session").status_code, 200)  # type: ignore[union-attr]
            self.assertEqual(  # type: ignore[union-attr]
                CLIENT.post("/v0/bootstrap", json={"user_id": PID}).status_code, 200
            )
            unknown = CLIENT.get("/v0/research/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_session_and_bootstrap_stay_byte_identical_after_an_intent(self) -> None:
        pristine_vector()
        with harness.offline():
            before = CLIENT.get("/v0/session").get_json()  # type: ignore[union-attr]
            self.assertEqual(  # type: ignore[union-attr]
                research_now(intent("next_step", 0)).status_code, 200
            )
            after = CLIENT.get("/v0/session").get_json()  # type: ignore[union-attr]
            boot = CLIENT.post(  # type: ignore[union-attr]
                "/v0/bootstrap", json={"user_id": PID}
            ).get_json()
        self.assertEqual(before, after)
        # And the boot payload still reads the committed balances the intent left.
        resources = boot["player_info"]["map"]
        self.assertEqual(
            {name: resources[name] for name in ("xp", "gold", "wood", "oil",
                                                "steel")},
            {name: COMMITTED_RESOURCES[name]
             for name in ("xp", "gold", "wood", "oil", "steel")},
        )
        self.assertEqual(boot["player_info"]["playerInfo"]["cash"],
                         COMMITTED_RESOURCES["cash"])

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(harness.port_is_free("127.0.0.1", port), port)

    def test_the_delivered_state_mutating_routes_still_exist(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        for route in (
            "/v0/place",
            "/v0/purchase",
            "/v0/move",
            "/v0/sell",
            "/v0/store",
            "/v0/upgrade",
            "/v0/construction",
            "/v0/collect",
            "/v0/expand",
            "/v0/level_up",
            "/v0/queue",
            "/v0/collection",
            "/v0/resurrect",
            "/v0/research",
        ):
            with self.subTest(route=route):
                self.assertIn('@app.post("%s")' % route, source)


if __name__ == "__main__":
    unittest.main()
