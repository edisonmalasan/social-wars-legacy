#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/queue`` behavior tests (OpenSpec task 2.3).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection.  The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across queue execution.

Every test resets the addressed row's attribute bag to a known state first and
asserts its post-condition against that snapshot, so the suite is
order-independent and no test can pass on a neighbour's mutation.

The committed corpus is the corpus's **own real placed training producer**:
``maps[0].items["1"]`` is ``[26, 51, 41, 0, 0, [], {}, 1]`` - id 26, Command
Center, ``training_time`` 5, ``min_level`` 1 - with an **empty** bag, so both
queue commands are exercisable against it **with no fabricated player state**.
That is the first M8 line able to say so.

Covered:

* **a successful push** - the recorded ``attr`` bag carries exactly the derived
  count and a start instant strictly forward, the row's own other fields are
  untouched, **every one of the seven stored resources is unchanged**, the
  response carries the legacy ``result``, the resolved ``action`` and
  ``map_key``, both rows, the projected ``queue``, and the current
  ``resources``.
* **a successful pop** - the **three-key teardown**, an **inert pop** on a row
  whose count is absent, and a **partial decrement** that refreshes the instant
  and keeps a queued unit id.
* **the derived, not client-supplied, effect** - a request carrying ``count``,
  ``cost``, ``price``, ``training_time``, ``duration``, ``ready``,
  ``remaining``, ``resources_changed``, ``vector``, and ``unit_id`` changes
  nothing.
* **the two-part post-execution proof** - a bag that does not match the derived
  result, and **any** stored resource that moved, each fail closed with
  ``internal_error`` rather than reporting legacy's success.  Each is exercised
  by a stub that lets the real dispatcher run and only rewrites the **post**
  read.
* **fail-closed paths** - every structurally unresolvable input returns its
  documented structured error with the corpus byte-unchanged.
* **the recorded absences** - the module declares no readiness, remaining-time,
  progress-ratio, completion, cost, or count-bound helper, and the route
  contains none of them either.
* **session/bootstrap byte-identity** is retained after queue intents, and the
  legacy accessors agree with the persisted map.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import queue_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed corpus's own queue target and resources.
QUEUE_MAP_KEY = 1
QUEUE_ITEM = 26
QUEUE_ROW = [26, 51, 41, 0, 0, [], {}, 1]
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
# A second real placed row, used to prove a queue intent rewrites no other row.
SPARE_MAP_KEY = 2
# A key the committed corpus does not place at.
UNKNOWN_MAP_KEY = 9999


def reset_attr(bag: Optional[Dict[str, Any]] = None) -> None:
    """Reset the addressed row's attribute bag, in memory **and** on disk.

    Both legacy queue helpers mutate the row's own ``attr`` dict **in place**
    (``engine.py:185-189`` writes ``nu``/``ts``; ``engine.py:200-204`` deletes
    three keys), so the bag lives in the in-memory save the endpoint reads and
    in the persisted corpus file.  Both representations are updated here, which
    is exactly the mechanism the legacy dispatcher itself uses to keep them in
    step.  It is a test-only, contained reset - never a claim about legacy
    behaviour and never a working-tree write.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["maps"][0]["items"][str(QUEUE_MAP_KEY)][6] = copy.deepcopy(
        {} if bag is None else bag
    )
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


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
        raise AssertionError("a queue execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def queue_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/queue", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def row_attr_now() -> Dict[str, Any]:
    return BOOT.map_item_attr(PID, QUEUE_MAP_KEY)  # type: ignore[union-attr]


def row_now() -> List[Any]:
    return list(BOOT.map_item(PID, QUEUE_MAP_KEY))  # type: ignore[union-attr]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def intent(action: str, map_key: Optional[int] = QUEUE_MAP_KEY) -> Dict[str, Any]:
    """The whole contract: a save id, a target key, and a closed action."""
    return {"user_id": PID, "map_key": map_key, "action": action}


def pristine() -> Dict[str, Any]:
    """Reset to the committed corpus state and snapshot it."""
    reset_attr()
    return {
        "attr": copy.deepcopy(row_attr_now()),
        "resources": copy.deepcopy(resources_now()),
        "items": copy.deepcopy(BOOT.map_items(PID)),  # type: ignore[union-attr]
    }


class Result:
    """A captured response plus the app that produced it.

    The app must stay referenced while the test reads the response: Flask's test
    client resolves the JSON decoder through a weak reference to the app, so
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


@contextmanager
def patched_boot(name: str, value: Any) -> Iterator[None]:
    """Install an instance-level stub on ``BOOT`` and restore it EXACTLY.

    A plain ``setattr``/``restore`` pair would leave the *unbound* class function
    behind in the instance dictionary when the attribute was not an instance
    attribute to begin with, and every later call would then miss its ``self``
    argument — a failure that shows up as an unrelated ``TypeError`` several
    tests later.  This restores the instance dictionary itself.
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
):
    """A ``resources`` stub that rewrites only the **post**-execution read.

    The endpoint reads the pre-execution resources before dispatch (for the
    value-level half of the proof) and again afterwards (for the response).
    Rewriting only the second read lets each resource clause fail on its own.
    """
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
    transform: Callable[[Dict[str, int]], Dict[str, int]], payload: Dict[str, Any]
) -> Result:
    """Run one intent against a ``BOOT`` whose post resource read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    stub = _resources_rewritten_after_execution(transform)
    with patched_boot("resources", stub):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/queue", json=payload))


def post_with_attr_stub(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]], payload: Dict[str, Any]
) -> Result:
    """Run one intent against a ``BOOT`` whose post attribute-bag read is stubbed.

    The endpoint reads the bag through the **same** accessor before and after
    dispatch — ``map_item_attr`` — so rewriting only the second read reproduces a
    persisted state legacy could never report while leaving the pre-execution
    derivation and the real dispatcher's own write untouched.  This mirrors the
    delivered level-up suite's ``map_level`` stub exactly.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    real_bag = BOOT.map_item_attr  # type: ignore[union-attr]
    state = {"seen": 0}

    def bag_stub(user_id: str, index: int) -> Dict[str, Any]:
        state["seen"] += 1
        bag = real_bag(user_id, index)
        if state["seen"] == 1:
            return bag
        return transform(bag)

    with patched_boot("map_item_attr", bag_stub):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/queue", json=payload))


class QueuePushTests(unittest.TestCase):
    """A push: the derived count, a stamped instant, and nothing else."""

    def test_a_push_on_the_committed_corpus_succeeds_and_derives_count_one(self) -> None:
        before = pristine()
        self.assertEqual(before["attr"], {})
        self.assertEqual(
            BOOT.map_item(PID, QUEUE_MAP_KEY)[0], QUEUE_ITEM
        )  # type: ignore[index]
        response = queue_now(intent("push"))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(
            sorted(body),
            sorted(
                [
                    "protocol",
                    "ok",
                    "game_version",
                    "server_time",
                    "result",
                    "action",
                    "map_key",
                    "previous",
                    "row",
                    "queue",
                    "resources",
                ]
            ),
        )
        self.assertTrue(body["ok"])
        self.assertEqual(body["protocol"], "compat-v0")
        self.assertEqual(body["result"], "success")
        self.assertEqual(body["action"], "push")
        self.assertEqual(body["map_key"], QUEUE_MAP_KEY)
        # The response's two rows: the bag as read BEFORE and re-read AFTER.
        self.assertEqual(body["previous"][6], {})
        self.assertEqual(body["previous"][0], QUEUE_ITEM)
        self.assertEqual(body["row"][6]["nu"], 1)
        self.assertIsInstance(body["row"][6]["ts"], int)
        self.assertGreater(body["row"][6]["ts"], 0)
        # The projected queue, reported verbatim.
        self.assertEqual(body["queue"]["present"], True)
        self.assertEqual(body["queue"]["count"], 1)
        self.assertEqual(body["queue"]["start_instant"], body["row"][6]["ts"])
        self.assertIsNone(body["queue"]["queued_unit_id"])
        self.assertEqual(body["queue"]["keys"], ["nu", "ts"])
        # No readiness, no remaining time, no progress ratio, no completion: the
        # queue block is a projection of three keys and nothing else.
        self.assertEqual(
            sorted(body["queue"]),
            [
                "absent_is_absent",
                "count",
                "keys",
                "present",
                "queued_unit_id",
                "start_instant",
            ],
        )
        # The row's own other fields are untouched.
        self.assertEqual(body["row"][:6], QUEUE_ROW[:6])
        self.assertEqual(body["row"][7], QUEUE_ROW[7])
        # The corpus save really holds it.
        self.assertEqual(row_attr_now()["nu"], 1)
        self.assertEqual(
            corpus_save()["maps"][0]["items"][str(QUEUE_MAP_KEY)][6]["nu"], 1
        )
        # And every other placement is byte-identical.
        for key, value in before["items"].items():
            if str(key) == str(QUEUE_MAP_KEY):
                continue
            with self.subTest(key=key):
                self.assertEqual(BOOT.map_items(PID)[key], value)  # type: ignore[index]
        self.assertEqual(len(BOOT.map_items(PID)), 40)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_start_instant_is_re_stamped_and_never_earlier_on_a_second_push(
        self,
    ) -> None:
        """Two pushes in a row.  ``engine.timestamp_now`` has one-second
        resolution, so the second stamp is **not earlier** than the first and MAY
        be identical — the honest direction for this clock."""
        reset_attr()
        first = queue_now(intent("push"))
        self.assertEqual(first.status_code, 200)
        first_stamp = first.get_json()["row"][6]["ts"]
        second = queue_now(intent("push"))
        self.assertEqual(second.status_code, 200)
        body = second.get_json()
        self.assertEqual(body["queue"]["count"], 2)
        self.assertGreaterEqual(body["row"][6]["ts"], first_stamp)
        # The PREVIOUS row in the second response is the pushed row, verbatim -
        # proof the endpoint read it before execution and did not alias the bag.
        self.assertEqual(body["previous"][6]["nu"], 1)
        self.assertEqual(body["previous"][6]["ts"], first_stamp)
        reset_attr()

    def test_a_push_on_a_row_carrying_another_key_preserves_it(self) -> None:
        """Only the count, the instant, and the queued unit id are the queue's;
        every other bag key is another feature's and is preserved verbatim."""
        reset_attr({"nc": 0, "cp": 3600})
        response = queue_now(intent("push"))
        self.assertEqual(response.status_code, 200)
        bag = response.get_json()["row"][6]
        self.assertEqual(bag["nc"], 0)
        self.assertEqual(bag["cp"], 3600)
        self.assertEqual(bag["nu"], 1)
        self.assertIn("ts", bag)
        reset_attr()

    def test_a_push_never_invents_a_queued_unit_id(self) -> None:
        """The atom-fusion branch is the only writer of ``ui`` and it is not
        offered, so a push must leave the key absent."""
        reset_attr()
        response = queue_now(intent("push"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("ui", response.get_json()["row"][6])
        reset_attr()

    def test_the_committed_vector_is_always_neutral(self) -> None:
        """Design D4: the derivation cannot express a price at all."""
        self.assertEqual(queue_envelope.neutral_vector(), [0] * 8)
        with self.assertRaises(queue_envelope.EnvelopeError):
            queue_envelope.validate_vector([0, 500, 0, 0, 0, 0, 0, 0])


class QueuePopTests(unittest.TestCase):
    """A pop: the three-key teardown, the inert no-op, and the partial decrement."""

    def test_a_pop_tears_the_three_keys_down_together(self) -> None:
        reset_attr()
        self.assertEqual(queue_now(intent("push")).status_code, 200)
        response = queue_now(intent("pop"))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["action"], "pop")
        self.assertEqual(body["previous"][6]["nu"], 1)
        self.assertEqual(body["row"][6], {})
        self.assertEqual(body["queue"]["present"], False)
        self.assertIsNone(body["queue"]["count"])
        self.assertIsNone(body["queue"]["start_instant"])
        self.assertIsNone(body["queue"]["queued_unit_id"])
        self.assertEqual(body["queue"]["keys"], [])
        # The row's own other fields survived the teardown.
        self.assertEqual(body["row"][:6], QUEUE_ROW[:6])
        self.assertEqual(body["row"][7], QUEUE_ROW[7])
        self.assertEqual(row_attr_now(), {})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_pop_on_an_absent_queue_is_a_successful_inert_no_op(self) -> None:
        """engine.py:193-194 returns without writing anything.  That is a real
        recorded behaviour, reported as an absent queue - not an error, and not
        a fabricated count of zero."""
        before = pristine()
        response = queue_now(intent("pop"))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["result"], "success")
        self.assertEqual(body["row"][6], {})
        self.assertFalse(body["queue"]["present"])
        self.assertIsNone(body["queue"]["count"])
        # Nothing moved at all, and the proof accepted the no-op.
        self.assertEqual(row_attr_now(), before["attr"])
        self.assertEqual(BOOT.map_items(PID), before["items"])  # type: ignore[union-attr]
        self.assertEqual(resources_now(), before["resources"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_pop_on_an_absent_queue_preserves_an_unrelated_bag_key(self) -> None:
        reset_attr({"nc": 2})
        response = queue_now(intent("pop"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["row"][6], {"nc": 2})
        reset_attr()

    def test_a_partial_decrement_keeps_the_queue_and_refreshes_the_instant(self) -> None:
        """engine.py:196-198: a partial decrement writes the count and RE-STAMPS
        the instant.  The new stamp is never earlier; with a one-second clock it
        may be identical, which is why the assertion is "not earlier"."""
        reset_attr()
        self.assertEqual(queue_now(intent("push")).status_code, 200)
        first_stamp = row_attr_now()["ts"]
        self.assertEqual(queue_now(intent("push")).status_code, 200)
        self.assertEqual(row_attr_now()["nu"], 2)
        response = queue_now(intent("pop"))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["row"][6]["nu"], 1)
        self.assertGreaterEqual(body["row"][6]["ts"], first_stamp)
        self.assertTrue(body["queue"]["present"])
        self.assertEqual(body["queue"]["count"], 1)
        reset_attr()

    def test_a_partial_decrement_keeps_a_queued_unit_id(self) -> None:
        """engine.py:196-198 decrements and re-stamps; it does not delete ``ui``."""
        reset_attr({"nu": 3, "ts": 100, "ui": 1013})
        response = queue_now(intent("pop"))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["row"][6]["nu"], 2)
        self.assertEqual(body["row"][6]["ui"], 1013)
        self.assertEqual(body["queue"]["queued_unit_id"], 1013)
        self.assertIn("ts", body["row"][6])
        self.assertGreaterEqual(body["row"][6]["ts"], 100)
        reset_attr()

    def test_a_pop_to_zero_removes_a_queued_unit_id_too(self) -> None:
        """The three-key teardown includes ``ui`` (engine.py:203-204)."""
        reset_attr({"nu": 1, "ts": 100, "ui": 1013})
        response = queue_now(intent("pop"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["row"][6], {})
        reset_attr()


class ClientSuppliedKeyTests(unittest.TestCase):
    """Design D4: a client can never dictate a cost, duration, count, or outcome."""

    def test_every_extra_key_is_ignored(self) -> None:
        ignored = {
            "count": 99,
            "nu": 99,
            "cost": [0, 0, -500, 0, 0, 0, 0, 0],
            "price": {"g": 1000},
            "resources_changed": [0, 0, -500, 0, 0, 0, 0, 0],
            "vector": [0, 0, -500, 0, 0, 0, 0, 0],
            "training_time": 1,
            "sm_training_time": 4000,
            "duration": 1,
            "ready": True,
            "is_complete": True,
            "remaining": 0,
            "progress": 1.0,
            "unit_id": 1013,
            "ui": 1013,
            "ts": 1,
        }
        reset_attr()
        first = queue_now(intent("push"))
        self.assertEqual(first.status_code, 200)
        baseline = first.get_json()["queue"]
        reset_attr()
        with_keys = dict(intent("push"))
        with_keys.update(ignored)
        second = queue_now(with_keys)
        self.assertEqual(second.status_code, 200)
        body = second.get_json()
        # The derived count is the derived count, whatever the client claimed.
        self.assertEqual(body["queue"]["count"], baseline["count"])
        self.assertEqual(body["row"][6]["nu"], 1)
        # The client-supplied unit id was never written: only the atom-fusion
        # branch writes `ui`, and it is not offered.
        self.assertNotIn("ui", body["row"][6])
        self.assertIsNone(body["queue"]["queued_unit_id"])
        # And no balance moved.
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(body["resources"][name], COMMITTED_RESOURCES[name])
        reset_attr()

    def test_the_request_carries_only_the_key_and_the_action(self) -> None:
        """The structural half of design D4, asserted on the route's own source:
        only ``user_id``, ``map_key``, and ``action`` are ever read."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = _queue_route(source)
        for read in ('payload["map_key"]', 'payload["action"]'):
            self.assertIn(read, route)
        for never in (
            'payload.get("count")',
            'payload.get("cost")',
            'payload.get("price")',
            'payload.get("unit_id")',
            'payload.get("training_time")',
            'payload.get("resources_changed")',
        ):
            with self.subTest(never=never):
                self.assertNotIn(never, route)


class GuardAndRefusalTests(unittest.TestCase):
    """The closed action set, addressability, and the save-identity rules."""

    def test_the_atom_fusion_push_is_not_in_the_closed_vocabulary(self) -> None:
        """Design D7: its unit id is a client-supplied argument no evidence
        constrains, so the endpoint offers no intent that would have to invent
        one."""
        pristine()
        for action in ("push_queue_unit2", "atom_fusion", "fusion", "PUSH"):
            with self.subTest(action=action):
                response = queue_now(intent(action))
                self.assertEqual(response.status_code, 400)
                body = response.get_json()
                self.assertFalse(body["ok"])
                self.assertEqual(body["error"]["code"], "invalid_action")
                self.assertIn("pop, push", body["error"]["message"])
        self.assertEqual(row_attr_now(), {})

    def test_a_skill_speedup_action_is_refused(self) -> None:
        """Design D6: the endpoint offers no speedup intent at all."""
        pristine()
        for action in ("soulmixer_speedup", "speedup", "finish", "complete"):
            with self.subTest(action=action):
                response = queue_now(intent(action))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "invalid_action")
        self.assertEqual(row_attr_now(), {})

    def test_a_non_string_action_is_refused(self) -> None:
        pristine()
        for action in (1, True, None, [], {}):
            with self.subTest(action=action):
                response = queue_now(dict(intent("push"), action=action))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "invalid_action")
        self.assertEqual(row_attr_now(), {})

    def test_a_missing_action_is_refused(self) -> None:
        pristine()
        payload = intent("push")
        del payload["action"]
        response = queue_now(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_action")
        self.assertEqual(row_attr_now(), {})

    def test_a_missing_map_key_is_refused(self) -> None:
        pristine()
        payload = intent("push")
        del payload["map_key"]
        response = queue_now(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_map_key")
        self.assertEqual(row_attr_now(), {})

    def test_a_non_integer_map_key_is_refused(self) -> None:
        pristine()
        for key in ("1", 1.0, None, True, [1], {"map_key": 1}):
            with self.subTest(map_key=key):
                response = queue_now(intent("push", map_key=key))  # type: ignore[arg-type]
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.get_json()["error"]["code"], "invalid_map_key"
                )
        self.assertEqual(row_attr_now(), {})

    def test_a_key_the_corpus_does_not_place_at_is_refused(self) -> None:
        """Legacy's missing-item path is a silent early return that still
        persists the batch, so the endpoint resolves the key itself."""
        pristine()
        response = queue_now(intent("push", map_key=UNKNOWN_MAP_KEY))
        self.assertEqual(response.status_code, 404)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "unknown_map_key")
        self.assertIn(str(UNKNOWN_MAP_KEY), body["error"]["message"])
        # Never a partial payload.
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(len(BOOT.map_items(PID)), 40)  # type: ignore[union-attr]

    def test_a_negative_map_key_is_refused_rather_than_resolved_from_the_end(self) -> None:
        pristine()
        response = queue_now(intent("push", map_key=-1))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "unknown_map_key")

    def test_the_save_identity_rules_are_the_documented_ones(self) -> None:
        pristine()
        with harness.offline():
            missing = CLIENT.post("/v0/queue", json={"map_key": 1, "action": "push"})  # type: ignore[union-attr]
            empty = CLIENT.post(  # type: ignore[union-attr]
                "/v0/queue", json={"user_id": "  ", "map_key": 1, "action": "push"}
            )
            wrong_type = CLIENT.post(  # type: ignore[union-attr]
                "/v0/queue", json={"user_id": 7, "map_key": 1, "action": "push"}
            )
            unknown = CLIENT.post(  # type: ignore[union-attr]
                "/v0/queue",
                json={"user_id": "does-not-exist-0000", "map_key": 1, "action": "push"},
            )
        self.assertEqual((missing.status_code, missing.get_json()["error"]["code"]), (400, "missing_user_id"))
        self.assertEqual((empty.status_code, empty.get_json()["error"]["code"]), (400, "missing_user_id"))
        self.assertEqual((wrong_type.status_code, wrong_type.get_json()["error"]["code"]), (400, "invalid_user_id"))
        self.assertEqual((unknown.status_code, unknown.get_json()["error"]["code"]), (404, "unknown_user_id"))


class FailClosedShapeTests(unittest.TestCase):
    """A save shape this contract cannot read is a 500 before execution."""

    def test_a_row_that_is_not_eight_fields_is_a_500(self) -> None:
        with patched_boot("map_item", lambda user_id, index: [26, 51, 41]):
            response = queue_now(intent("push"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")

    def test_a_row_with_no_attribute_bag_is_a_500_before_the_dispatcher(self) -> None:
        calls = {"count": 0}
        real = BOOT.execute_commands  # type: ignore[union-attr]

        def counting(user_id: str, envelope: Dict[str, Any]) -> None:
            calls["count"] += 1
            real(user_id, envelope)

        def unreadable(user_id: str, index: int) -> Dict[str, Any]:
            raise compat_legacy.LegacyBootError("invalid_save_state", "no bag")

        with patched_boot("map_item_attr", unreadable), patched_boot(
            "execute_commands", counting
        ):
            response = queue_now(intent("push"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(calls["count"], 0, "the dispatcher never ran")

    def test_a_count_this_contract_cannot_read_is_a_500(self) -> None:
        for bad in (True, 1.5, "2", -1):
            with self.subTest(count=bad):
                reset_attr({"nu": bad})
                response = queue_now(intent("push"))
                self.assertEqual(response.status_code, 500)
                self.assertEqual(
                    response.get_json()["error"]["code"], "invalid_attr"
                )
        reset_attr()

    def test_legacy_execution_raising_is_a_500(self) -> None:
        def raising(user_id: str, envelope: Dict[str, Any]) -> None:
            raise RuntimeError("legacy blew up")

        with patched_boot("execute_commands", raising):
            response = queue_now(intent("push"))
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        reset_attr()


class PostExecutionProofTests(unittest.TestCase):
    """Design D4: both halves of the proof, or a structured 500.

    Each test runs the **real** legacy dispatcher and only rewrites the **post**
    read, so what the save really holds is the true post-state and the reported
    divergence is the only thing that fails.
    """

    def assert_internal(self, response: Any, fragment: str) -> None:
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn(fragment, body["error"]["message"])
        self.assertNotIn("queue", body)
        self.assertNotIn("result", body)
        self.assertNotIn("row", body)
        self.assertNotIn("resources", body)
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_wrong_count_is_a_500_not_a_success(self) -> None:
        reset_attr()
        self.assert_internal(
            post_with_attr_stub(lambda bag: dict(bag, nu=7), intent("push")),
            "the count is 7",
        )
        reset_attr()

    def test_a_missing_count_after_a_push_is_a_500(self) -> None:
        reset_attr()
        self.assert_internal(
            post_with_attr_stub(
                lambda bag: {"ts": bag.get("ts", 1)}, intent("push")
            ),
            "the count is absent",
        )
        reset_attr()

    def test_a_partial_teardown_is_a_500(self) -> None:
        """A save never carries one (engine.py:198-204), so a bag that keeps the
        start instant after a teardown is reported rather than claimed."""
        reset_attr({"nu": 1, "ts": 100, "ui": 1013})
        self.assert_internal(
            post_with_attr_stub(lambda bag: {"ts": 1700000000}, intent("pop")),
            "teardown left",
        )
        reset_attr()

    def test_a_teardown_that_keeps_the_queued_unit_id_is_a_500(self) -> None:
        reset_attr({"nu": 1, "ts": 100, "ui": 1013})
        self.assert_internal(
            post_with_attr_stub(lambda bag: {"ui": 1013}, intent("pop")),
            "teardown left",
        )
        reset_attr()

    def test_a_stamp_that_moves_backwards_is_a_500(self) -> None:
        """A stamp earlier than the pre-execution one is a state no branch in
        this family can produce, so it is reported rather than claimed."""
        reset_attr({"nu": 1, "ts": 1700000000})
        self.assert_internal(
            post_with_attr_stub(
                lambda bag: {"nu": 2, "ts": 1699999999}, intent("push")
            ),
            "moves backwards",
        )
        reset_attr()

    def test_an_equal_stamp_in_the_same_second_is_accepted(self) -> None:
        """``engine.timestamp_now`` has one-second resolution, so two commands
        inside the same second legitimately stamp the same instant.  The proof
        must accept it — a "strictly later" rule would refuse a correct
        transaction — and this is the regression that keeps it honest."""
        reset_attr({"nu": 1, "ts": 1700000000})
        response = post_with_attr_stub(
            lambda bag: {"nu": 2, "ts": 1700000000}, intent("push")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["queue"]["count"], 2)
        reset_attr()

    def test_a_non_integer_stamp_is_a_500(self) -> None:
        for stamp in ("1700000000", None, 1.5, True, [1]):
            with self.subTest(stamp=stamp):
                # Each case starts from the same pre-state: a push increments the
                # count, so a shared starting point would derive a different
                # count per case and test the wrong clause.
                reset_attr()
                self.assert_internal(
                    post_with_attr_stub(
                        lambda bag, value=stamp: {"nu": 1, "ts": value},
                        intent("push"),
                    ),
                    "start instant",
                )
        reset_attr()

    def test_a_key_the_branch_does_not_own_changing_is_a_500(self) -> None:
        reset_attr({"nc": 0})
        self.assert_internal(
            post_with_attr_stub(
                lambda bag: dict(bag, nc=3), intent("push")
            ),
            "'nc' changed",
        )
        reset_attr()

    def test_a_key_the_branch_does_not_own_disappearing_is_a_500(self) -> None:
        reset_attr({"nc": 0, "cp": 5})
        self.assert_internal(
            post_with_attr_stub(
                lambda bag: {"nu": 1, "ts": bag.get("ts", 1), "nc": 0},
                intent("push"),
            ),
            "'cp' was removed",
        )
        reset_attr()

    def test_a_push_that_invents_a_queued_unit_id_is_a_500(self) -> None:
        reset_attr()
        self.assert_internal(
            post_with_attr_stub(
                lambda bag: dict(bag, ui=1013), intent("push")
            ),
            "atom-fusion",
        )
        reset_attr()

    def test_an_inert_pop_that_wrote_something_is_a_500(self) -> None:
        reset_attr()
        self.assert_internal(
            post_with_attr_stub(lambda bag: dict(bag, nu=1), intent("pop")),
            "inert pop",
        )
        reset_attr()

    def test_a_row_that_vanished_after_execution_is_a_500(self) -> None:
        original = BOOT.has_map_item  # type: ignore[union-attr]
        state = {"seen": 0}

        def stub(user_id: str, index: int) -> bool:
            state["seen"] += 1
            if state["seen"] == 1:
                return original(user_id, index)
            return False

        with patched_boot("has_map_item", stub):
            response = queue_now(intent("push"))
        self.assert_internal(response, "did not keep the placement entry")
        reset_attr()

    def test_a_moved_resource_is_reported_not_trusted(self) -> None:
        """The value-level half.  A balance the **neutral** vector leaves alone
        moving means the reported resources are not the derived ones - the check
        that distinguishes a correct queue intent from a resource-minting exploit.
        """
        reset_attr()
        response = post_with_resources_stub(
            lambda values: dict(values, gold=values["gold"] + 1), intent("push")
        )
        self.assert_internal(response, "resource gold")
        message = response.get_json()["error"]["message"]
        self.assertIn("pre-execution", message)
        self.assertIn("moves no resource", message)
        reset_attr()

    def test_every_resource_that_moved_is_a_500(self) -> None:
        """All seven slots of the neutral vector, one at a time."""
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                reset_attr()
                response = post_with_resources_stub(
                    lambda values, moved=name: dict(
                        values, **{moved: values[moved] + 1}
                    ),
                    intent("push"),
                )
                self.assert_internal(response, "resource %s" % name)
        reset_attr()

    def test_a_resource_that_disappeared_is_a_500(self) -> None:
        reset_attr()
        self.assert_internal(
            post_with_resources_stub(
                lambda values: dict(values, mana=values["mana"] + 5), intent("push")
            ),
            "resource mana",
        )
        reset_attr()

    def test_a_smuggled_client_vector_would_be_caught_by_the_proof(self) -> None:
        """The whole point of the second proof half, exercised end to end: a
        resource the derivation never sends, appearing on the post read, is a
        reported failure rather than a trusted success."""
        reset_attr()
        response = post_with_resources_stub(
            lambda values: dict(values, xp=values["xp"] + 500), intent("push")
        )
        self.assert_internal(response, "resource xp")
        reset_attr()

    def test_the_proof_source_contains_both_halves(self) -> None:
        """The route reads the ``attr`` bag and the resources **before** dispatch,
        dispatches, and only then requires the derived bag and the absence of
        movement - in that order."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = _queue_route(source)
        pre_attr = route.index("previous_attr = boot.map_item_attr(user_id, map_key)")
        pre_res = route.index("resources_before = boot.resources(user_id)")
        dispatch = route.index("boot.execute_commands(user_id, envelope_payload)")
        bag_check = route.index(
            "queue_envelope.expected_attr(previous_attr, action, after_attr)"
        )
        res_check = route.index("if resources_after[name] != resources_before[name]:")
        self.assertLess(pre_attr, dispatch)
        self.assertLess(pre_res, dispatch)
        self.assertLess(dispatch, bag_check)
        self.assertLess(bag_check, res_check)
        # And every refusal precedes the dispatcher too.
        for code in (
            "ERROR_MISSING_MAP_KEY",
            "ERROR_INVALID_MAP_KEY",
            "ERROR_MISSING_ACTION",
            "ERROR_INVALID_ACTION",
            "ERROR_UNKNOWN_MAP_KEY",
            "ERROR_INVALID_ATTR",
        ):
            with self.subTest(code=code):
                self.assertLess(route.index(code), dispatch)


class QueueContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_queue_intents(self) -> None:
        pristine()
        self.assertEqual(queue_now(intent("push")).status_code, 200)
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        with harness.offline():
            session = CLIENT.get("/v0/session")  # type: ignore[union-attr]
            bootstrap = CLIENT.post(  # type: ignore[union-attr]
                "/v0/bootstrap", json={"user_id": PID}
            )
        self.assertEqual(session.status_code, 200)
        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        reset_attr()

    def test_queue_intents_never_touch_working_tree_saves(self) -> None:
        pristine()
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(queue_now(intent("push")).status_code, 200)
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(resources_now(), COMMITTED_RESOURCES)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        reset_attr()

    def test_a_queue_intent_leaves_every_other_placement_alone(self) -> None:
        pristine()
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.assertEqual(before_items, seed_items)
        self.assertEqual(queue_now(intent("push")).status_code, 200)
        self.assertEqual(queue_now(intent("pop")).status_code, 200)
        self.assertEqual(BOOT.map_items(PID), before_items)  # type: ignore[union-attr]
        self.assertEqual(len(BOOT.map_items(PID)), 40)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), {})  # type: ignore[union-attr]
        self.assertEqual(
            BOOT.save_document(PID)["privateState"]["boughtUnits"], []  # type: ignore[union-attr]
        )
        self.assertEqual(
            BOOT.save_document(PID)["privateState"]["deadHeroes"], {}  # type: ignore[union-attr]
        )
        self.assertEqual(
            BOOT.save_document(PID)["maps"][0]["expansions"], [35, 36, 45, 46]  # type: ignore[union-attr]
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_legacy_accessors_agree_with_the_map(self) -> None:
        pristine()
        self.assertEqual(BOOT.map_item(PID, QUEUE_MAP_KEY), QUEUE_ROW)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_item_attr(PID, QUEUE_MAP_KEY), {})  # type: ignore[union-attr]
        self.assertTrue(BOOT.has_map_item(PID, QUEUE_MAP_KEY))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, UNKNOWN_MAP_KEY))  # type: ignore[union-attr]
        self.assertEqual(resources_now(), COMMITTED_RESOURCES)
        # The accessor hands out a COPY, so a caller cannot reach the live bag
        # the legacy helpers mutate in place.
        bag = BOOT.map_item_attr(PID, QUEUE_MAP_KEY)  # type: ignore[union-attr]
        bag["nu"] = 99
        self.assertEqual(BOOT.map_item_attr(PID, QUEUE_MAP_KEY), {})  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_item(PID, QUEUE_MAP_KEY)[6], {})  # type: ignore[union-attr]

    def test_the_attribute_accessor_refuses_shapes_it_cannot_read(self) -> None:
        for row, label in (
            (None, "no row"),
            ([26, 51, 41, 0, 0, [], {}], "seven fields"),
            ([26, 51, 41, 0, 0, [], None, 1], "a null bag"),
            ([26, 51, 41, 0, 0, [], [], 1], "a list bag"),
        ):
            with self.subTest(row=label):
                with patched_boot(
                    "map_item", lambda user_id, index, value=row: value
                ):
                    with self.assertRaises(compat_legacy.LegacyBootError) as caught:
                        BOOT.map_item_attr(PID, QUEUE_MAP_KEY)  # type: ignore[union-attr]
                self.assertEqual(caught.exception.code, "invalid_save_state")

    def test_the_endpoint_derives_the_legacy_envelope_it_sends(self) -> None:
        """One derivation: the endpoint, the fixture, and this suite build the
        same six-key envelope from the same module."""
        self.assertIs(compat_service.queue_envelope, queue_envelope)
        for action, command in (
            ("push", "push_queue_unit"),
            ("pop", "pop_queue_unit"),
        ):
            with self.subTest(action=action):
                built = queue_envelope.build_envelope(
                    map_key=QUEUE_MAP_KEY, action=action, ts=1700000000
                )
                self.assertEqual(
                    built["commands"], [[0, command, [QUEUE_MAP_KEY], [0] * 8]]
                )

    def test_the_route_carries_no_readiness_no_cost_and_no_completion(self) -> None:
        """Design D1/D2/D5/D6 in the delivered sense: the route names no
        readiness, remaining-time, progress, completion, cost, or count-bound
        computation, and the boundaries are stated where a reader meets them."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = _queue_route(source)
        code_names: List[str] = []
        for node in ast.walk(ast.parse(_dedent(route))):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
        for forbidden in (
            "remaining",
            "is_complete",
            "is_ready",
            "progress",
            "complete_queue",
            "finish_queue",
            "cash_cost",
            "sm_training_time",
            "training_time",
            "in_grid",
            "GRID_EXTENT",
            "cell",
            "orientation",
            "footprint",
            "terrain",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)
        for named in ("Design D1", "Design D1/D2", "Design D4", "Design D5", "Design D6"):
            with self.subTest(named=named):
                self.assertIn(named, route)

    def test_the_module_docstring_documents_the_queue_surface(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        for named in (
            "POST /v0/queue",
            "map_key",
            "action",
            "push_queue_unit",
            "pop_queue_unit",
            "push_queue_unit2",
            "readiness",
            "count bound",
            "No queue cost is implemented",
            "soulmixer_speedup",
            "quite useless",
            "three-key teardown",
            "NEUTRAL",
            "godot-unit-queues",
        ):
            with self.subTest(named=named):
                self.assertIn(named, source)


class QueueSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/queue")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 405)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "method_not_allowed")

    def test_the_other_routes_are_untouched(self) -> None:
        with harness.offline():
            self.assertEqual(CLIENT.get("/v0/session").status_code, 200)  # type: ignore[union-attr]
            self.assertEqual(  # type: ignore[union-attr]
                CLIENT.post("/v0/bootstrap", json={"user_id": PID}).status_code, 200
            )
            unknown = CLIENT.get("/v0/queue/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_delivered_state_mutating_routes_still_exist(self) -> None:
        """This is the eleventh state-mutating surface; the other ten are
        unchanged."""
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
        ):
            with self.subTest(route=route):
                self.assertIn('@app.post("%s")' % route, source)

    def test_the_persistence_scope_names_every_mutating_route(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        scope = source[source.index("Persistence scope"):]
        scope = scope[: scope.index('"""', source.index("Persistence scope"))]
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
        ):
            with self.subTest(route=route):
                self.assertIn(route, scope)

    def test_the_error_table_documents_the_queue_codes(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        for named in (
            "``missing_map_key``",
            "``invalid_map_key``",
            "``unknown_map_key``",
            "``invalid_attr``",
        ):
            with self.subTest(named=named):
                self.assertIn(named, source)

    def test_the_endpoint_names_this_capability(self) -> None:
        """The execution boundary names this capability's endpoint."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        self.assertIn("godot-unit-queues", source)

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


def _queue_route(source: str) -> str:
    """The ``/v0/queue`` route body, from its decorator to the next route.

    The route is bounded by the **next** route decorator rather than by the
    closing ``app.config`` assignment, so the slice is exactly this route's own
    text wherever the routes happen to be ordered inside ``create_app``.
    """
    route = source[source.index("def v0_queue()"):]
    end = route.index("\n    @app.")
    return route[:end]


def _dedent(text: str) -> str:
    import textwrap

    return textwrap.dedent(text.lstrip("\n"))


if __name__ == "__main__":
    unittest.main()
