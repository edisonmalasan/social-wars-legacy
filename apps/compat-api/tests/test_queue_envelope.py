#!/usr/bin/env python3
"""Offline unit tests for the production-queue derivation and the queue capture
tool's published contract (OpenSpec tasks 1.1 / 2.1 / 2.2).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the pinned
interpreter.  The real-config cross-checks pin the corpus's own queue target (id
26 Command Center at map key 1, `training_time` 5, `min_level` 1,
`group_type` `COMMAND_CENTER`, an empty attribute bag), the seven stored
resources, the placement count, and the neutral vector against the bytes the
legacy server actually loads.  The shared-helper round trip proves the
single-command envelope travels through the placement module's unchanged
serialization.

The design decisions are asserted as behaviour, not comments:

* **D1/D2** the derivation exposes **no** readiness, remaining time, progress
  ratio, or completion, because the legacy server has none to reproduce - and
  that absence is asserted structurally, by the module's own function inventory
  and by the absence of any completion command in the recorded contract;
* **D4** the derived vector is **neutral** and :func:`validate_vector` refuses
  anything that would move a balance, so the derivation cannot express vector
  smuggling at all;
* **D5** the recorded absence of validation is content, and **no count bound** is
  applied to any count;
* **D6** the ``soulmixer_speedup`` contract is recorded verbatim and
  **unimplemented**: the module has no cost function, and the two-key
  precondition is a **named refusal** rather than a raised ``KeyError``;
* **D7** the atom-fusion push is **not** offered, and a projected queued unit id
  is reported exactly as recorded.
"""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List

import compat_test_harness as harness

import capture_queue_fixture as capture
import queue_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]

# The queue keys, in the inventory order the projection and the manifest use.
THREE_KEYS = ("nu", "ts", "ui")


def committed_item(item_id: int) -> Dict[str, Any]:
    for row in CONFIG["items"]:
        if isinstance(row, dict) and int(row.get("id", -1)) == item_id:
            return row
    raise AssertionError("the committed config resolves no item %d" % item_id)


class SharedHelperTests(unittest.TestCase):
    """One shared derivation: the helpers are reused, not re-implemented."""

    def test_the_shared_helpers_are_the_placement_modules_own(self) -> None:
        import placement_envelope

        self.assertIs(envelope_mod.is_strict_int, placement_envelope.is_strict_int)
        self.assertIs(envelope_mod.EnvelopeError, placement_envelope.EnvelopeError)
        self.assertIs(envelope_mod.data_field, placement_envelope.data_field)
        self.assertIs(envelope_mod.parse_data_field, placement_envelope.parse_data_field)
        self.assertIs(envelope_mod.payload_json, placement_envelope.payload_json)
        self.assertIs(envelope_mod.in_grid, placement_envelope.in_grid)
        self.assertEqual(envelope_mod.ENVELOPE_KEYS, placement_envelope.ENVELOPE_KEYS)
        self.assertEqual(envelope_mod.GRID_EXTENT, placement_envelope.GRID_EXTENT)
        # The queue derivation is additive: the delivered siblings keep their own
        # helpers, untouched.
        for foreign in (
            "payout_for",
            "tier_for",
            "threshold_seconds_for",
            "resource_vector_for",
            "unmet_requirements",
            "derived_level_for",
            "entry_index_for_level",
            "thresholds_from_entries",
            "build_envelope_start",
            "build_envelope_click",
            "neutral_vector",
            "validate_vector",
            "is_action",
        ):
            with self.subTest(helper=foreign):
                self.assertFalse(hasattr(placement_envelope, foreign))

    def test_the_command_names_are_the_documented_legacy_names(self) -> None:
        """command.py:676-708 and engine.py:183-213."""
        self.assertEqual(envelope_mod.PUSH_COMMAND, "push_queue_unit")
        self.assertEqual(envelope_mod.POP_COMMAND, "pop_queue_unit")
        self.assertEqual(envelope_mod.ATOM_FUSION_COMMAND, "push_queue_unit2")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)
        self.assertEqual(envelope_mod.QUEUE_KEYS, THREE_KEYS)

    def test_the_action_vocabulary_is_closed_and_two_wide(self) -> None:
        """Design D2: the client names an OUTCOME, the service chooses the
        command, and the atom-fusion push is absent by decision (D7)."""
        self.assertEqual(envelope_mod.ACTIONS, ("push", "pop"))
        self.assertEqual(
            envelope_mod.ACTION_COMMANDS,
            {"push": "push_queue_unit", "pop": "pop_queue_unit"},
        )
        for accepted in ("push", "pop"):
            with self.subTest(action=accepted):
                self.assertTrue(envelope_mod.is_action(accepted))
                self.assertEqual(
                    envelope_mod.command_for_action(accepted),
                    envelope_mod.ACTION_COMMANDS[accepted],
                )
        for refused in (
            "push_queue_unit2",
            "PUSH",
            "push ",
            "complete",
            "soulmixer_speedup",
            "",
            None,
            1,
            True,
        ):
            with self.subTest(action=refused):
                self.assertFalse(envelope_mod.is_action(refused))
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.command_for_action(refused)  # type: ignore[arg-type]
                self.assertEqual(caught.exception.code, "invalid_action")

    def test_the_legacy_modules_ship_no_queue_completion_command(self) -> None:
        """Design D2, asserted against the committed legacy SOURCE rather than
        restated: the dispatcher has 63 named branches, the ``complete_*`` family
        is exactly three commands, and **none** of them completes a queue."""
        source = (harness.REPO_ROOT / "command.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        named = 0
        completes: List[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if not isinstance(test, ast.Compare):
                continue
            operand = test.left
            if not (isinstance(operand, ast.Name) and operand.id == "cmd"):
                continue
            if not any(
                isinstance(op, ast.Eq) for op in test.ops
            ):  # pragma: no cover - the dispatcher only compares cmd
                continue
            names: List[str] = []
            for comparator in test.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(
                    comparator.value, str
                ):
                    names.append(comparator.value)
            for name in names:
                named += 1
                if name.startswith("complete_"):
                    completes.append(name)
        self.assertEqual(named, 63, "the dispatcher's named branch count is 63")
        self.assertEqual(
            sorted(completes),
            ["complete_collection", "complete_goal", "complete_tutorial"],
        )
        for absent in (
            "complete_queue",
            "complete_queue_unit",
            "finish_queue",
            "queue_complete",
        ):
            with self.subTest(command=absent):
                self.assertNotIn('"%s"' % absent, source)

    def test_the_legacy_helpers_write_only_the_three_keys(self) -> None:
        """engine.py:183-213: the whole economic and temporal surface of a queue
        is three attribute-bag keys, and the teardown deletes them together."""
        source = (harness.REPO_ROOT / "engine.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        helpers: Dict[str, List[str]] = {}
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name not in (
                "push_queue_unit",
                "pop_queue_unit",
                "push_queue_unit2",
            ):
                continue
            written: List[str] = []
            for inner in ast.walk(node):
                targets: Any = None
                if isinstance(inner, ast.Assign):
                    targets = inner.targets
                elif isinstance(inner, ast.AugAssign):
                    targets = [inner.target]
                elif isinstance(inner, ast.Delete):
                    targets = inner.targets
                for target in targets or []:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "attr"
                    ):
                        written.append(
                            ast.literal_eval(target.slice)  # type: ignore[attr-defined]
                        )
            helpers[node.name] = written
        self.assertEqual(
            sorted(helpers), ["pop_queue_unit", "push_queue_unit", "push_queue_unit2"]
        )
        # The push writes nu and ts, and nothing else in the whole module.
        self.assertEqual(sorted(set(helpers["push_queue_unit"])), ["nu", "ts"])
        # The atom-fusion push additionally writes ui.
        self.assertEqual(sorted(set(helpers["push_queue_unit2"])), ["nu", "ts", "ui"])
        # The pop DELETES all three together at zero, and writes nu/ts otherwise:
        # the union of the keys it touches is exactly the queue's three keys.
        self.assertEqual(sorted(set(helpers["pop_queue_unit"])), ["nu", "ts", "ui"])
        # …and every one of the queue's three keys is the ONLY key any of the
        # three helpers touches, so the queue's whole surface is three keys.
        touched: set = set()
        for keys in helpers.values():
            touched.update(keys)
        self.assertEqual(touched, {"nu", "ts", "ui"})

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.queue_envelope, envelope_mod)
        self.assertEqual(compat_service.ERROR_MISSING_MAP_KEY, "missing_map_key")
        self.assertEqual(compat_service.ERROR_INVALID_MAP_KEY, "invalid_map_key")
        self.assertEqual(compat_service.ERROR_UNKNOWN_MAP_KEY, "unknown_map_key")
        self.assertEqual(compat_service.ERROR_INVALID_ATTR, "invalid_attr")


class TheDerivedVectorTests(unittest.TestCase):
    """Design D4: neutral, and unable to express a price at all."""

    def test_the_derived_vector_is_all_zero(self) -> None:
        vector = envelope_mod.neutral_vector()
        self.assertEqual(vector, [0] * 8)
        # A fresh list on every call, so a caller cannot mutate the derivation.
        vector[2] = 999
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_validate_vector_refuses_anything_that_would_move_a_balance(self) -> None:
        self.assertEqual(envelope_mod.validate_vector([0] * 8), [0] * 8)
        refused = [
            [1] + [0] * 7,
            [0] * 8 + [1],
            [-1] + [0] * 7,
            [0, 500, 0, 0, 0, 0, 0, 0],
        ]
        for vector in refused:
            with self.subTest(vector=vector):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.validate_vector(vector)
                self.assertEqual(caught.exception.code, "invalid_vector")
        for malformed in ([], [0] * 7, [0] * 9, "00000000", None, {"0": 0}):
            with self.subTest(malformed=malformed):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.validate_vector(malformed)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_a_bool_is_not_an_integer_slot(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError):
            envelope_mod.validate_vector([True] + [0] * 7)


class TheEnvelopeTests(unittest.TestCase):
    """One command per batch, the map index its only argument, neutral vector."""

    def test_the_push_batch_is_exactly_the_documented_envelope(self) -> None:
        envelope = envelope_mod.build_envelope(
            map_key=1, action="push", ts=1700000000
        )
        self.assertEqual(
            sorted(envelope), sorted(envelope_mod.ENVELOPE_KEYS)
        )
        self.assertEqual(
            envelope["commands"], [[0, "push_queue_unit", [1], [0, 0, 0, 0, 0, 0, 0, 0]]]
        )
        self.assertEqual(len(envelope["commands"]), 1)
        self.assertEqual(len(envelope["commands"][0][2]), 1)
        self.assertEqual(envelope["first_number"], 0)
        self.assertEqual(envelope["publishActions"], [])
        self.assertEqual(envelope["tries"], 1)
        self.assertEqual(envelope["accessToken"], "")

    def test_the_pop_batch_is_exactly_the_documented_envelope(self) -> None:
        envelope = envelope_mod.build_envelope(
            map_key=1, action="pop", ts=1700000000
        )
        self.assertEqual(
            envelope["commands"], [[0, "pop_queue_unit", [1], [0, 0, 0, 0, 0, 0, 0, 0]]]
        )

    def test_the_batch_travels_through_the_unchanged_serialization(self) -> None:
        envelope = envelope_mod.build_envelope(
            map_key=7, action="push", ts=1700000000
        )
        field = envelope_mod.data_field(envelope)
        self.assertEqual(
            envelope_mod.parse_data_field(field), envelope
        )

    def test_ts_defaults_to_the_current_time_and_must_be_a_non_negative_int(self) -> None:
        envelope = envelope_mod.build_envelope(map_key=1, action="push")
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)
        for bad in (-1, "1700000000", 1.5, True):
            with self.subTest(ts=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope(map_key=1, action="push", ts=bad)
                self.assertEqual(caught.exception.code, "invalid_timestamp")

    def test_a_non_integer_map_key_is_refused(self) -> None:
        for bad in ("1", 1.0, None, True, [1], {"map_key": 1}):
            with self.subTest(map_key=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope(
                        map_key=bad, action="push", ts=1700000000
                    )
                self.assertEqual(caught.exception.code, "invalid_map_key")

    def test_a_negative_map_key_is_legal_because_legacy_never_ranges_checks(self) -> None:
        """Established: the branches do no range check at all, so the envelope
        builder does not invent one either.  Addressability is the endpoint's
        structural check, resolved against the corpus before dispatch."""
        envelope = envelope_mod.build_envelope(
            map_key=-1, action="push", ts=1700000000
        )
        self.assertEqual(envelope["commands"][0][2], [-1])


class DerivedQueueTests(unittest.TestCase):
    """engine.py:183-213, as behaviour: the increment, the no-op, the teardown."""

    def test_a_push_on_an_empty_bag_derives_count_one(self) -> None:
        derived = envelope_mod.derived_queue({}, "push")
        self.assertEqual(derived["command"], "push_queue_unit")
        self.assertTrue(derived["changed"])
        self.assertFalse(derived["no_op"])
        self.assertEqual(derived["count"], 1)
        self.assertTrue(derived["start_instant"])
        self.assertFalse(derived["teardown"])
        self.assertIsNone(derived["queued_unit_id"])
        self.assertFalse(derived["keeps_unit_id"])

    def test_a_push_increments_an_existing_count(self) -> None:
        for existing in (1, 2, 7, 9999):
            with self.subTest(existing=existing):
                derived = envelope_mod.derived_queue({"nu": existing}, "push")
                self.assertEqual(derived["count"], existing + 1)

    def test_a_pop_on_an_absent_count_is_an_inert_no_op(self) -> None:
        """engine.py:193-194 returns without writing anything.  That is a real
        recorded behaviour, not an error, and the derivation says so."""
        derived = envelope_mod.derived_queue({}, "pop")
        self.assertTrue(derived["no_op"])
        self.assertFalse(derived["changed"])
        self.assertIsNone(derived["count"])
        self.assertFalse(derived["start_instant"])

    def test_a_partial_pop_decrements_and_refreshes_the_instant(self) -> None:
        """engine.py:196-198."""
        derived = envelope_mod.derived_queue({"nu": 3, "ts": 100}, "pop")
        self.assertEqual(derived["count"], 2)
        self.assertTrue(derived["start_instant"])
        self.assertFalse(derived["teardown"])
        self.assertFalse(derived["no_op"])

    def test_a_pop_to_one_is_still_a_partial_decrement(self) -> None:
        derived = envelope_mod.derived_queue({"nu": 2, "ts": 100}, "pop")
        self.assertEqual(derived["count"], 1)
        self.assertFalse(derived["teardown"])

    def test_a_pop_to_zero_tears_the_three_keys_down_together(self) -> None:
        """engine.py:198-204: the teardown, which no inspection of the dispatcher
        would reveal."""
        derived = envelope_mod.derived_queue(
            {"nu": 1, "ts": 100, "ui": 1013}, "pop"
        )
        self.assertTrue(derived["teardown"])
        self.assertIsNone(derived["count"])
        self.assertFalse(derived["start_instant"])
        self.assertIsNone(derived["queued_unit_id"])
        self.assertFalse(derived["keeps_unit_id"])
        self.assertIn("TOGETHER", envelope_mod.TEARDOWN)
        for key in THREE_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, envelope_mod.TEARDOWN)

    def test_a_pop_at_zero_tears_down_even_without_a_queued_unit_id(self) -> None:
        derived = envelope_mod.derived_queue({"nu": 1, "ts": 100}, "pop")
        self.assertTrue(derived["teardown"])
        self.assertFalse(derived["keeps_unit_id"])

    def test_a_push_never_touches_the_queued_unit_id(self) -> None:
        """engine.py:183-189 writes nu and ts only; ui belongs to the atom-fusion
        branch, which is not offered."""
        derived = envelope_mod.derived_queue({"nu": 2, "ts": 100, "ui": 1019}, "push")
        self.assertTrue(derived["keeps_unit_id"])
        self.assertEqual(derived["queued_unit_id"], 1019)
        self.assertFalse(derived["teardown"])

    def test_a_partial_pop_keeps_the_queued_unit_id(self) -> None:
        """engine.py:196-198 decrements and re-stamps; it does not delete ui."""
        derived = envelope_mod.derived_queue({"nu": 3, "ts": 100, "ui": 1019}, "pop")
        self.assertTrue(derived["keeps_unit_id"])
        self.assertEqual(derived["queued_unit_id"], 1019)

    def test_every_bag_key_the_branch_does_not_own_is_named(self) -> None:
        derived = envelope_mod.derived_queue(
            {"nu": 1, "ts": 100, "nc": 0, "cp": 3600}, "push"
        )
        self.assertEqual(derived["other_keys"], ["cp", "nc"])

    def test_an_unknown_action_is_refused(self) -> None:
        for bad in ("push_queue_unit2", "complete", "PUSH", "", None, 3):
            with self.subTest(action=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.derived_queue({}, bad)  # type: ignore[arg-type]
                self.assertEqual(caught.exception.code, "invalid_action")

    def test_a_bag_that_is_not_an_object_is_refused(self) -> None:
        for bad in (None, [], "attr", 3, True):
            with self.subTest(attr=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.derived_queue(bad, "push")
                self.assertEqual(caught.exception.code, "invalid_attr")

    def test_a_count_this_contract_cannot_read_is_refused_not_coerced(self) -> None:
        """A bool, a float, a numeric string, and a negative count are all
        shapes legacy's helper would raise on; they are refused here."""
        for bad in (True, 1.5, "2", -1, [2]):
            with self.subTest(count=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.derived_queue({"nu": bad}, "push")
                self.assertEqual(caught.exception.code, "invalid_attr")
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.derived_queue({"nu": bad}, "pop")


class ExpectedAttrTests(unittest.TestCase):
    """The pure half of the two-part post-execution proof."""

    def test_a_correct_push_agrees(self) -> None:
        self.assertIsNone(
            envelope_mod.expected_attr({}, "push", {"nu": 1, "ts": 999})
        )

    def test_a_correct_increment_agrees(self) -> None:
        self.assertIsNone(
            envelope_mod.expected_attr({"nu": 4, "ts": 100}, "push", {"nu": 5, "ts": 999})
        )

    def test_a_correct_teardown_agrees(self) -> None:
        self.assertIsNone(
            envelope_mod.expected_attr(
                {"nu": 1, "ts": 100, "ui": 1013}, "pop", {}
            )
        )

    def test_a_correct_inert_pop_agrees(self) -> None:
        self.assertIsNone(envelope_mod.expected_attr({}, "pop", {}))
        self.assertIsNone(
            envelope_mod.expected_attr({"nc": 0}, "pop", {"nc": 0})
        )

    def test_a_partial_decrement_agrees(self) -> None:
        self.assertIsNone(
            envelope_mod.expected_attr(
                {"nu": 3, "ts": 100, "ui": 1013}, "pop", {"nu": 2, "ts": 999, "ui": 1013}
            )
        )

    def test_a_wrong_count_is_reported(self) -> None:
        message = envelope_mod.expected_attr({}, "push", {"nu": 2, "ts": 999})
        self.assertIsNotNone(message)
        self.assertIn("the count is 2", str(message))

    def test_a_partial_teardown_is_reported(self) -> None:
        """The three-key teardown is not negotiable: a save never carries one."""
        message = envelope_mod.expected_attr(
            {"nu": 1, "ts": 100, "ui": 1013}, "pop", {"ui": 1013}
        )
        self.assertIsNotNone(message)
        self.assertIn("teardown left", str(message))

    def test_an_absent_start_instant_after_a_stamping_action_is_reported(self) -> None:
        message = envelope_mod.expected_attr({}, "push", {"nu": 1})
        self.assertIsNotNone(message)
        self.assertIn("start instant is absent", str(message))

    def test_a_non_instant_stamp_is_reported(self) -> None:
        for stamp in ("1700000000", None, 1.5, True, [1]):
            with self.subTest(stamp=stamp):
                message = envelope_mod.expected_attr(
                    {}, "push", {"nu": 1, "ts": stamp}
                )
                self.assertIsNotNone(message)

    def test_a_stamp_that_moves_backwards_is_reported(self) -> None:
        message = envelope_mod.expected_attr(
            {"nu": 1, "ts": 1000}, "push", {"nu": 2, "ts": 999}
        )
        self.assertIsNotNone(message)
        self.assertIn("moves backwards", str(message))

    def test_an_equal_stamp_is_accepted_because_the_clock_is_one_second(self) -> None:
        """``engine.timestamp_now`` has one-second resolution, so two commands in
        the same second stamp the same instant; the comparison is ``>=``, and
        this is the check that keeps it that way."""
        self.assertIsNone(
            envelope_mod.expected_attr(
                {"nu": 1, "ts": 1700000000}, "push", {"nu": 2, "ts": 1700000000}
            )
        )

    def test_a_key_the_branch_does_not_own_changing_is_reported(self) -> None:
        for changed in ({"nc": 1}, {"nc": 0, "cp": 5}):
            with self.subTest(changed=changed):
                message = envelope_mod.expected_attr(
                    {"nc": 0, "cp": 0}, "push", dict({"nu": 1, "ts": 9}, **changed)
                )
                self.assertIsNotNone(message)

    def test_a_key_the_branch_does_not_own_disappearing_is_reported(self) -> None:
        message = envelope_mod.expected_attr({"nc": 3}, "push", {"nu": 1, "ts": 9})
        self.assertIsNotNone(message)
        self.assertIn("was removed", str(message))

    def test_a_key_the_branch_never_owns_appearing_is_reported(self) -> None:
        message = envelope_mod.expected_attr({}, "push", {"nu": 1, "ts": 9, "nc": 0})
        self.assertIsNotNone(message)
        self.assertIn("added", str(message))

    def test_a_push_that_invents_a_queued_unit_id_is_reported(self) -> None:
        """Only the atom-fusion branch writes ui, and it is not offered."""
        message = envelope_mod.expected_attr({}, "push", {"nu": 1, "ts": 9, "ui": 1013})
        self.assertIsNotNone(message)
        self.assertIn("atom-fusion", str(message))

    def test_a_push_that_removes_the_queued_unit_id_is_reported(self) -> None:
        message = envelope_mod.expected_attr(
            {"nu": 1, "ts": 9, "ui": 1013}, "push", {"nu": 2, "ts": 999}
        )
        self.assertIsNotNone(message)
        self.assertIn("removed the queued unit id", str(message))

    def test_a_push_that_rewrites_the_queued_unit_id_is_reported(self) -> None:
        message = envelope_mod.expected_attr(
            {"nu": 1, "ts": 9, "ui": 1013}, "push", {"nu": 2, "ts": 999, "ui": 1019}
        )
        self.assertIsNotNone(message)
        self.assertIn("not the untouched", str(message))

    def test_an_inert_pop_that_wrote_something_is_reported(self) -> None:
        message = envelope_mod.expected_attr({}, "pop", {"nu": 1})
        self.assertIsNotNone(message)
        self.assertIn("inert pop", str(message))


class ProjectQueueTests(unittest.TestCase):
    """The read-only projection: verbatim values, and absence as absence."""

    def test_an_empty_bag_is_an_absent_queue_not_a_zero(self) -> None:
        projected = envelope_mod.project_queue({})
        self.assertFalse(projected["present"])
        self.assertIsNone(projected["count"])
        self.assertIsNone(projected["start_instant"])
        self.assertIsNone(projected["queued_unit_id"])
        self.assertEqual(projected["keys"], [])
        self.assertTrue(projected["absent_is_absent"])

    def test_the_three_keys_are_reported_verbatim(self) -> None:
        projected = envelope_mod.project_queue(
            {"nu": 4, "ts": 1700000000, "ui": 1013}
        )
        self.assertTrue(projected["present"])
        self.assertEqual(projected["count"], 4)
        self.assertEqual(projected["start_instant"], 1700000000)
        self.assertEqual(projected["queued_unit_id"], 1013)
        self.assertEqual(projected["keys"], list(THREE_KEYS))

    def test_the_queued_unit_id_is_reported_as_recorded_and_never_resolved(self) -> None:
        """Design D7: the id comes from a client argument, so this projection
        reports it exactly and substitutes nothing - not a name, not a default,
        and not a drop."""
        for recorded in (1013, 999999, 0, -1):
            with self.subTest(recorded=recorded):
                projected = envelope_mod.project_queue({"nu": 1, "ui": recorded})
                self.assertEqual(projected["queued_unit_id"], recorded)

    def test_a_partial_queue_reports_only_the_keys_it_carries(self) -> None:
        for bag, expected in (
            ({"nu": 1}, ["nu"]),
            ({"nu": 2, "ts": 5}, ["nu", "ts"]),
            ({"ui": 1013}, ["ui"]),
            ({"ts": 5}, ["ts"]),
        ):
            with self.subTest(bag=bag):
                projected = envelope_mod.project_queue(bag)
                self.assertEqual(projected["keys"], expected)
                self.assertTrue(projected["present"])

    def test_unrelated_bag_keys_do_not_make_a_queue_present(self) -> None:
        projected = envelope_mod.project_queue({"nc": 0, "cp": 3600})
        self.assertFalse(projected["present"])
        self.assertIsNone(projected["count"])

    def test_a_bag_that_is_not_an_object_is_refused(self) -> None:
        for bad in (None, [], "attr", 7, True):
            with self.subTest(attr=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.project_queue(bad)
                self.assertEqual(caught.exception.code, "invalid_attr")


class RecordedAbsenceTests(unittest.TestCase):
    """The recorded contract, asserted as content the module carries."""

    def test_the_recorded_command_inventory_names_three_commands(self) -> None:
        self.assertEqual(
            [record["command"] for record in envelope_mod.COMMANDS],
            ["push_queue_unit", "pop_queue_unit", "push_queue_unit2"],
        )
        for record in envelope_mod.COMMANDS:
            with self.subTest(command=record["command"]):
                self.assertTrue(record["args"])
                self.assertTrue(record["effect"])
                self.assertIn("command.py:", record["source"])
                self.assertIn("none", record["validation"])

    def test_only_the_two_plain_commands_are_offered(self) -> None:
        offered = [record["command"] for record in envelope_mod.COMMANDS if record["offered"]]
        self.assertEqual(offered, ["push_queue_unit", "pop_queue_unit"])
        atom = envelope_mod.COMMANDS[2]
        self.assertFalse(atom["offered"])
        self.assertIn("CLIENT-SUPPLIED", atom["why_not_offered"])
        self.assertIn("unresolvable", atom["why_not_offered"])

    def test_the_absence_of_validation_is_recorded_not_inherited(self) -> None:
        statement = envelope_mod.NO_VALIDATION
        for phrase in (
            "NO VALIDATION IS PERFORMED BY THE LEGACY SERVER AND NONE IS IMPLEMENTED",
            "training producer",
            "training_time",
            "min_level",
            "NOT permission",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, statement)

    def test_the_absence_of_elapsed_time_and_completion_is_recorded(self) -> None:
        statement = envelope_mod.NO_ELAPSED_TIME
        for phrase in (
            "NO ELAPSED-TIME EVALUATION IS IMPLEMENTED",
            "WRITE",
            "DELETION",
            "soulmixer_speedup",
            "complete_collection",
            "complete_goal",
            "complete_tutorial",
            "NO readiness, NO remaining time, NO progress ratio, and NO completion",
            "not a missing feature",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, statement)

    def test_the_speedup_contract_is_recorded_and_unimplemented(self) -> None:
        statement = envelope_mod.SPEEDUP_CONTRACT
        for phrase in (
            "RECORDED VERBATIM AND IMPLEMENTED NOT AT ALL",
            "ts",
            "ui",
            "KeyError",
            "sm_training_time",
            "SECONDS",
            "CHARGES NOTHING",
            "ts = 0",
            "Quite useless cost calculation for understanding it",
            "REFUSES with a named reason",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, statement)
        self.assertFalse(envelope_mod.SPEEDUP_COST_IMPLEMENTED)
        self.assertEqual(envelope_mod.SPEEDUP_COST_DIVISOR, 3600)
        self.assertEqual(
            envelope_mod.SPEEDUP_COST_FORMULA, "ceil(remaining_seconds / 3600)"
        )
        self.assertIn("RECORDED for completeness only", envelope_mod.SPEEDUP_COST_NOTE)
        self.assertIn("KeyError", envelope_mod.REFUSAL_NOTE)
        self.assertIn("refuses", envelope_mod.REFUSAL_NOTE)

    def test_the_duration_field_coverage_is_recorded_as_content(self) -> None:
        statement = envelope_mod.SPEEDUP_FIELD_COVERAGE
        for phrase in (
            "300 of the 429 committed units",
            "129",
            "0 of the 470",
            "84 distinct values",
            "4000",
            "NO queue branch reads",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, statement)

    def test_the_two_key_precondition_is_a_named_refusal_not_a_crash(self) -> None:
        for bag, reason in (
            ({}, envelope_mod.REASON_MISSING_START),
            ({"nu": 1}, envelope_mod.REASON_MISSING_START),
            ({"ts": 100}, envelope_mod.REASON_MISSING_UNIT_ID),
            ({"ui": 1013}, envelope_mod.REASON_MISSING_START),
            ({"nu": 1, "ts": 100}, envelope_mod.REASON_MISSING_UNIT_ID),
            ({"nu": 1, "ts": 100, "nc": 0}, envelope_mod.REASON_MISSING_UNIT_ID),
            (None, envelope_mod.REASON_ABSENT_QUEUE),
        ):
            with self.subTest(bag=bag):
                answer = envelope_mod.speedup_refusal(bag)
                self.assertFalse(answer["ok"])
                self.assertEqual(answer["reason"], reason)
                self.assertTrue(answer["refuses_instead_of_raising"])
                self.assertFalse(answer["cost_implemented"])
                self.assertIn("KeyError", answer["error"])
                self.assertIs(answer["contract"], envelope_mod.SPEEDUP_CONTRACT)

    def test_both_keys_present_is_the_only_ok_answer_and_it_computes_nothing(self) -> None:
        answer = envelope_mod.speedup_refusal({"ts": 100, "ui": 1013})
        self.assertTrue(answer["ok"])
        self.assertEqual(answer["reason"], "")
        self.assertEqual(answer["keys_present"], ["ts", "ui"])
        self.assertFalse(answer["refuses_instead_of_raising"])
        self.assertFalse(answer["cost_implemented"])
        # The answer carries the recorded contract and nothing else: no cost
        # field, no remaining time, no duration read.
        self.assertEqual(
            sorted(answer),
            [
                "contract",
                "cost_implemented",
                "error",
                "keys_present",
                "ok",
                "reason",
                "refuses_instead_of_raising",
            ],
        )

    def test_the_module_declares_no_cost_no_timer_and_no_completion(self) -> None:
        """Design D1/D2/D6 as a structural fact: there is no such function to
        call, so no caller can reach one."""
        source = Path(envelope_mod.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        defined = sorted(
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        )
        self.assertEqual(
            defined,
            [
                "_bag_of",
                "build_envelope",
                "command_for_action",
                "derived_queue",
                "expected_attr",
                "is_action",
                "neutral_vector",
                "project_queue",
                "speedup_refusal",
                "validate_vector",
            ],
        )
        for absent in (
            "remaining",
            "is_complete",
            "is_ready",
            "progress_ratio",
            "complete_queue",
            "finish_queue",
            "speedup_cost",
            "cash_cost",
            "training_time_for",
        ):
            with self.subTest(name=absent):
                self.assertNotIn(absent, defined)
        # And no `ceil(` in the runtime code at all: the recorded cost shape is
        # prose and a constant, never an expression.
        body = "\n".join(
            line
            for line in source.splitlines()
            if not line.strip().startswith("#")
        )
        self.assertNotIn("math.ceil", body)
        self.assertNotIn("from math", body)

    def test_no_count_bound_is_applied_to_any_count(self) -> None:
        """Design D5: the engine sets no cap, so the derivation refuses to
        invent one.  A thousand-unit count derives a thousand-plus-one count."""
        for existing in (1, 99, 100, 1000, 10 ** 9):
            with self.subTest(existing=existing):
                self.assertEqual(
                    envelope_mod.derived_queue({"nu": existing}, "push")["count"],
                    existing + 1,
                )
                popped = envelope_mod.derived_queue({"nu": existing}, "pop")
                if existing > 1:
                    self.assertEqual(popped["count"], existing - 1)
                    self.assertFalse(popped["teardown"])
                else:
                    # Exactly one: the teardown, with no cap consulted.
                    self.assertTrue(popped["teardown"])
                    self.assertIsNone(popped["count"])
                self.assertIsNone(
                    envelope_mod.expected_attr(
                        {"nu": existing}, "push", {"nu": existing + 1, "ts": 10 ** 9 + 1}
                    )
                )


class CommittedCorpusTests(unittest.TestCase):
    """The real committed bytes: the queue target and its resources."""

    def test_the_queue_target_is_a_real_placed_training_producer(self) -> None:
        row = FRESH_MAP["items"][str(capture.FIXTURE_MAP_KEY)]
        self.assertEqual(row, [26, 51, 41, 0, 0, [], {}, 1])
        self.assertEqual(row[6], {}, "the committed bag is EMPTY")
        self.assertEqual(row[0], capture.FIXTURE_ITEM_ID)
        self.assertEqual(capture.FIXTURE_ITEM_ID, 26)
        self.assertEqual(capture.FIXTURE_MAP_KEY, 1)
        item = committed_item(26)
        self.assertEqual(item["name"], "Command Center")
        self.assertEqual(int(str(item["training_time"]).strip()), 5)
        self.assertEqual(int(str(item["min_level"]).strip()), 1)
        self.assertEqual(item["group_type"], "COMMAND_CENTER")
        self.assertEqual(item["type"], "b")

    def test_the_corpus_resource_census_matches_the_committed_bytes(self) -> None:
        resources = {
            "xp": FRESH_MAP["xp"],
            "gold": FRESH_MAP["gold"],
            "wood": FRESH_MAP["wood"],
            "oil": FRESH_MAP["oil"],
            "steel": FRESH_MAP["steel"],
            "cash": SEED["playerInfo"]["cash"],
            "mana": SEED["privateState"]["mana"],
        }
        self.assertEqual(
            resources,
            {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
             "cash": 5, "mana": 0},
        )
        self.assertEqual(resources, envelope_mod.COMMITTED_RESOURCE_BEFORE)
        self.assertEqual(len(FRESH_MAP["items"]), 40)
        self.assertEqual(FRESH_MAP["store"], {})
        self.assertEqual(FRESH_MAP["expansions"], [35, 36, 45, 46])
        self.assertEqual(SEED["privateState"]["boughtUnits"], [])
        self.assertEqual(SEED["privateState"]["deadHeroes"], {})

    def test_the_committed_unit_census_matches_the_speedup_record(self) -> None:
        """The `sm_training_time` coverage the recorded contract states is
        measured from the committed normalized package, not restated."""
        units = json.loads(
            (harness.REPO_ROOT / "packages/game-content/normalized/units.json").read_text(
                encoding="utf-8"
            )
        )
        buildings = json.loads(
            (
                harness.REPO_ROOT / "packages/game-content/normalized/buildings.json"
            ).read_text(encoding="utf-8")
        )
        carrying = [row for row in units if row.get("sm_training_time") is not None]
        self.assertEqual(len(units), 429)
        self.assertEqual(len(buildings), 470)
        self.assertEqual(len(carrying), 300)
        self.assertEqual(429 - len(carrying), 129)
        self.assertEqual(
            len({int(row["sm_training_time"]) for row in carrying}), 84
        )
        self.assertEqual(min(int(row["sm_training_time"]) for row in carrying), 4000)
        self.assertEqual(
            [row for row in buildings if row.get("sm_training_time") is not None], []
        )
        missing = {row["legacy_id"] for row in units if row.get("sm_training_time") is None}
        for named in ("923", "933", "1001", "1013"):
            self.assertIn(named, missing)
        # `training_time` is the opposite: a building field, on 130 buildings and
        # on no unit at all.
        self.assertEqual(
            len([row for row in units if int(row.get("training_time") or 0) > 0]), 0
        )
        self.assertEqual(
            len([row for row in buildings if int(row.get("training_time") or 0) > 0]), 130
        )

    def test_the_derivation_reproduces_the_recorded_pair_on_the_real_row(self) -> None:
        """The push and pop the capture recorded, derived from the committed
        row's own empty bag, so the derivation and the execution cannot drift."""
        row = FRESH_MAP["items"][str(capture.FIXTURE_MAP_KEY)]
        push = envelope_mod.derived_queue(row[6], "push")
        self.assertEqual(push["count"], 1)
        self.assertIsNone(
            envelope_mod.expected_attr(row[6], "push", {"nu": 1, "ts": 1790791620})
        )
        after_push = {"nu": 1, "ts": 1790791620}
        pop = envelope_mod.derived_queue(after_push, "pop")
        self.assertTrue(pop["teardown"])
        self.assertIsNone(envelope_mod.expected_attr(after_push, "pop", {}))
        self.assertFalse(envelope_mod.project_queue(row[6])["present"])
        self.assertFalse(envelope_mod.project_queue({})["present"])


class CaptureToolContractTests(unittest.TestCase):
    """The capture tool's published constants, pinned against the real config."""

    def test_the_pinned_target_matches_the_committed_bytes(self) -> None:
        capture.verify_target(SEED)

    def test_the_pinned_vector_and_resources_are_neutral(self) -> None:
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_BEFORE, envelope_mod.COMMITTED_RESOURCE_BEFORE
        )
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_AFTER, envelope_mod.COMMITTED_RESOURCE_BEFORE
        )
        self.assertEqual(
            set(capture.FIXTURE_EXPECTED_RESOURCE_DELTA.values()), {0}
        )

    def test_the_capture_envelopes_are_the_shared_derivation(self) -> None:
        for action, builder in (
            ("push", capture.build_push_envelope),
            ("pop", capture.build_pop_envelope),
        ):
            with self.subTest(action=action):
                envelope = builder(ts=1700000000)
                self.assertEqual(
                    envelope["commands"],
                    [[
                        0,
                        envelope_mod.ACTION_COMMANDS[action],
                        [capture.FIXTURE_MAP_KEY],
                        [0] * 8,
                    ]],
                )

    def test_the_capture_guards_ten_committed_fixture_directories(self) -> None:
        self.assertEqual(len(capture.PROTECTED_FIXTURES), 10)
        for relative, label in capture.PROTECTED_FIXTURES:
            with self.subTest(fixture=label):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_the_capture_records_the_probe_it_actually_runs(self) -> None:
        self.assertEqual(len(capture.PROBES), 1)
        probe = capture.PROBES[0]
        self.assertTrue(probe["executed_in_this_capture"])
        self.assertIn("CLIENT-SENT", probe["commands"][0])
        self.assertIn("[0, 500, 0, 0, 0, 0, 0, 0]", probe["commands"][0])
        self.assertIn("resource-minting exploit", probe["why_it_matters"])
        self.assertIn("command.py:676-685", probe["established"])

    def test_the_capture_does_not_ship_a_probe_expecting_a_teardown_round_trip(self) -> None:
        """The recorded pair's own after-state is the seed, and the capture
        asserts exactly that - a check a run must not silently weaken."""
        source = Path(capture.__file__).read_text(encoding="utf-8")
        self.assertIn("the seed byte-for-byte", source)
        self.assertIn("ROW_ATTR_POINTER", source)


if __name__ == "__main__":
    unittest.main()
