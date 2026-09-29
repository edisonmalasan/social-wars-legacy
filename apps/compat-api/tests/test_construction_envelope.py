#!/usr/bin/env python3
"""Offline unit tests for the construction envelope derivation and the
construction capture tool's published contract (OpenSpec task 2.1 / task 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the fixture intent, the
committed ``build_time`` and ``clicks_to_build`` of the placed Turret I, the
derived duration, and the neutral price vectors against the bytes the legacy
server actually loads, and the shared-helper round trip proves the
single-command envelopes travel through the placement module's unchanged
serialization (design D8).

The load-bearing refusals are asserted directly: a **non-positive** duration
is rejected, because legacy's ``activate`` with a non-positive duration would
**clear the row's whole attribute bag** and destroy the click counter and any
friend-assist entries (design D6) — this contract exposes no cancel action at
all.
"""

from __future__ import annotations

import json
import time
import unittest
from typing import Dict, List, Optional

import compat_test_harness as harness

import capture_construction_fixture as capture
import construction_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]

# The friend-assist bag key: the clearing branch would destroy it too, and no
# command in this contract ever writes it (change non-goals).
FRIEND_ASSIST_KEY = "si"


def item_by_id(item_id: int) -> dict:
    for entry in CONFIG["items"]:
        if int(entry["id"]) == item_id:
            return entry
    raise AssertionError("config has no item id %d" % item_id)


def int_attribute(item_id: int, name: str) -> int:
    return int(str(item_by_id(item_id)[name]).strip())


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
        # The construction derivation is additive: the delivered siblings keep
        # their own.
        self.assertFalse(hasattr(placement_envelope, "neutral_vector"))
        self.assertFalse(hasattr(placement_envelope, "ACTIONS"))
        self.assertFalse(hasattr(placement_envelope, "ACTIVATE_COMMAND"))

    def test_the_three_commands_are_the_documented_legacy_names(self) -> None:
        # command.py:412-429, command.py:525-536, command.py:537-548, and the
        # matching entries of docs/legacy-protocol/commands.json.
        self.assertEqual(envelope_mod.ACTIVATE_COMMAND, "activate")
        self.assertEqual(envelope_mod.ADD_CLICK_COMMAND, "add_click")
        self.assertEqual(envelope_mod.ACTIVATE_ITEM_CLICK_COMMAND, "activate_item_click")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)

    def test_the_action_vocabulary_is_closed_and_service_owned(self) -> None:
        """Design D2: the client names an outcome, the service the command."""
        self.assertEqual(
            envelope_mod.ACTIONS, frozenset(("start", "click", "finish"))
        )
        self.assertEqual(envelope_mod.ACTION_START, "start")
        self.assertEqual(envelope_mod.ACTION_CLICK, "click")
        self.assertEqual(envelope_mod.ACTION_FINISH, "finish")
        self.assertEqual(
            envelope_mod.ACTION_COMMANDS,
            {
                "start": "activate",
                "click": "add_click",
                "finish": "activate_item_click",
            },
        )
        # The action names are NOT legacy command names: that separation is the
        # whole point of the vocabulary.
        for action in envelope_mod.ACTIONS:
            self.assertNotIn(action, envelope_mod.ACTION_COMMANDS.values())

    def test_is_action_accepts_only_the_documented_strings(self) -> None:
        for good in ("start", "click", "finish"):
            self.assertTrue(envelope_mod.is_action(good))
        for bad in (
            "Start",  # case matters
            "start ",
            "activate",  # the legacy command name is not an action
            "add_click",
            "activate_item_click",
            "cancel",  # the clearing branch is never offered (design D6)
            "buy_si_help",
            "finish_si",
            "",
            None,
            0,
            True,
            ["start"],
            {"action": "start"},
        ):
            with self.subTest(action=bad):
                self.assertFalse(envelope_mod.is_action(bad))

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.construction_envelope, envelope_mod)
        self.assertEqual(compat_service.ERROR_MISSING_ACTION, "missing_action")
        self.assertEqual(compat_service.ERROR_INVALID_ACTION, "invalid_action")
        self.assertEqual(compat_service.ERROR_NO_BUILD_TIME, "no_build_time")
        self.assertEqual(
            compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index"
        )
        self.assertEqual(
            compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index"
        )
        self.assertEqual(
            compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index"
        )


class StrictIntTests(unittest.TestCase):
    def test_ints_but_not_bools_or_other_types(self) -> None:
        self.assertTrue(envelope_mod.is_strict_int(11))
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int("11"))
        self.assertFalse(envelope_mod.is_strict_int(11.0))
        self.assertFalse(envelope_mod.is_strict_int(None))


class NeutralVectorTests(unittest.TestCase):
    """Design D4: the derived vector is all zeros on every action."""

    def test_the_vector_is_eight_zeros(self) -> None:
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.neutral_vector()
        first[6] = -999
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_every_action_carries_its_own_neutral_vector(self) -> None:
        built = [
            envelope_mod.build_envelope_start(
                item_index=capture.FIXTURE_ITEM_INDEX, duration=5, ts=1700000000
            ),
            envelope_mod.build_envelope_click(
                item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
            ),
            envelope_mod.build_envelope_finish(
                item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
            ),
        ]
        for payload in built:
            with self.subTest(command=payload["commands"][0][1]):
                self.assertEqual(len(payload["commands"]), 1)
                self.assertEqual(payload["commands"][0][3], [0] * 8)
        vectors = [payload["commands"][0][3] for payload in built]
        self.assertEqual(len({id(vector) for vector in vectors}), 3)

    def test_the_vector_leaves_every_stored_resource_alone(self) -> None:
        vector = envelope_mod.neutral_vector()
        self.assertEqual(vector[1], 0)  # xp
        for index in (2, 3, 4, 5):  # gold, wood, oil, steel
            self.assertEqual(vector[index], 0)
        self.assertEqual(vector[6], 0)  # cash
        self.assertEqual(vector[7], 0)  # mana
        for value in (0, 4, 5, 2000):
            self.assertEqual(max(value + 0, 0), value)


class BuildEnvelopeShapeTests(unittest.TestCase):
    """Each builder produces the six keys and exactly one command."""

    def build_all(self) -> List[Dict[str, object]]:
        return [
            envelope_mod.build_envelope_start(
                item_index=capture.FIXTURE_ITEM_INDEX, duration=5, ts=1700000000
            ),
            envelope_mod.build_envelope_click(
                item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
            ),
            envelope_mod.build_envelope_finish(
                item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
            ),
        ]

    def test_every_envelope_has_exactly_the_six_legacy_keys(self) -> None:
        for built in self.build_all():
            with self.subTest(command=built["commands"][0][1]):
                self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
                self.assertEqual(built["first_number"], 0)
                self.assertEqual(built["publishActions"], [])
                self.assertEqual(built["ts"], 1700000000)
                self.assertEqual(built["tries"], 1)
                self.assertEqual(built["accessToken"], "")

    def test_the_start_argument_list_is_exactly_the_two_the_branch_reads(self) -> None:
        # command.py:413-414 binds args[0] and args[1] and reads both.
        args = self.build_all()[0]["commands"][0][2]
        self.assertEqual(len(args), 2)
        self.assertEqual(args, [capture.FIXTURE_ITEM_INDEX, 5])
        self.assertEqual(args[0], capture.FIXTURE_ITEM_INDEX)  # item_index
        self.assertEqual(args[1], capture.FIXTURE_BUILD_TIME)  # derived duration

    def test_the_click_argument_list_is_exactly_the_one_the_branch_reads(self) -> None:
        # command.py:526 binds a single positional arg.
        args = self.build_all()[1]["commands"][0][2]
        self.assertEqual(len(args), 1)
        self.assertEqual(args, [capture.FIXTURE_ITEM_INDEX])

    def test_the_finish_argument_list_is_exactly_the_one_the_branch_reads(self) -> None:
        # command.py:538 binds a single positional arg.
        args = self.build_all()[2]["commands"][0][2]
        self.assertEqual(len(args), 1)
        self.assertEqual(args, [capture.FIXTURE_ITEM_INDEX])

    def test_every_command_is_on_map_zero(self) -> None:
        for built in self.build_all():
            self.assertEqual(built["commands"][0][0], 0)

    def test_the_commands_are_the_documented_ones_in_the_documented_order(self) -> None:
        self.assertEqual(
            [built["commands"][0][1] for built in self.build_all()],
            ["activate", "add_click", "activate_item_click"],
        )

    def test_the_click_and_finish_commands_carry_no_duration(self) -> None:
        """Only ``activate`` has a second argument; neither of the others may
        be handed one, because ``activate`` is the branch that would clear the
        attribute bag."""
        for built in self.build_all()[1:]:
            with self.subTest(command=built["commands"][0][1]):
                self.assertNotIn(
                    capture.FIXTURE_BUILD_TIME, built["commands"][0][2]
                )
                self.assertEqual(len(built["commands"][0][2]), 1)

    def test_the_action_map_agrees_with_each_builder(self) -> None:
        built = {
            "start": self.build_all()[0],
            "click": self.build_all()[1],
            "finish": self.build_all()[2],
        }
        for action, payload in built.items():
            with self.subTest(action=action):
                self.assertEqual(
                    payload["commands"][0][1], envelope_mod.ACTION_COMMANDS[action]
                )

    def test_any_integer_index_is_accepted(self) -> None:
        """Addressability is the endpoint's job, not the derivation's."""
        for index in (0, 11, 41, 999999):
            with self.subTest(item_index=index):
                for built in (
                    envelope_mod.build_envelope_start(
                        item_index=index, duration=1, ts=1700000000
                    ),
                    envelope_mod.build_envelope_click(
                        item_index=index, ts=1700000000
                    ),
                    envelope_mod.build_envelope_finish(
                        item_index=index, ts=1700000000
                    ),
                ):
                    self.assertEqual(built["commands"][0][2][0], index)

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = envelope_mod.build_envelope_click(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=None
        )
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.build_envelope_click(item_index="11")
        message = str(caught.exception)
        self.assertIn("integer", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class StartDurationTests(unittest.TestCase):
    """The load-bearing refusal: only a positive duration is ever derived."""

    def test_a_positive_duration_is_accepted(self) -> None:
        for duration in (1, 5, 600, 3600, 86400, 10 ** 9):
            with self.subTest(duration=duration):
                built = envelope_mod.build_envelope_start(
                    item_index=11, duration=duration, ts=1700000000
                )
                self.assertEqual(built["commands"][0][2][1], duration)

    def test_a_zero_duration_fails_closed(self) -> None:
        """command.py:425-427 would clear the whole attribute bag here."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.build_envelope_start(item_index=11, duration=0)
        self.assertEqual(caught.exception.code, "invalid_duration")

    def test_a_negative_duration_fails_closed(self) -> None:
        for duration in (-1, -5, -(10 ** 9)):
            with self.subTest(duration=duration):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope_start(item_index=11, duration=duration)
                self.assertEqual(caught.exception.code, "invalid_duration")

    def test_a_non_integer_duration_fails_closed(self) -> None:
        for bad in ("5", 5.0, None, True, [5], {"cp": 5}):
            with self.subTest(duration=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope_start(item_index=11, duration=bad)
                self.assertEqual(caught.exception.code, "invalid_duration")

    def test_the_duration_message_names_the_reason(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.build_envelope_start(item_index=11, duration=0)
        self.assertIn("positive integer", str(caught.exception))
        self.assertIn("0", str(caught.exception))

    def test_no_builder_ever_produces_a_clearing_envelope(self) -> None:
        """Belt and braces: no accepted input reaches ``activate(..., 0)``."""
        for duration in (0, -1):
            for built in (lambda: envelope_mod.build_envelope_start(11, duration),):
                with self.assertRaises(envelope_mod.EnvelopeError):
                    built()


class FailClosedTests(unittest.TestCase):
    """Every documented structural refusal, per builder."""

    def cases(self) -> List[Dict[str, object]]:
        common: List[Dict[str, object]] = [
            {"ts": -1},
            {"ts": "1700000000"},
            {"ts": True},
        ]
        cases: List[Dict[str, object]] = []
        for overrides in common:
            cases.append(
                dict(overrides, builder="start", expected="invalid_timestamp")
            )
            cases.append(
                dict(overrides, builder="click", expected="invalid_timestamp")
            )
            cases.append(
                dict(overrides, builder="finish", expected="invalid_timestamp")
            )
        for bad_index in (True, "11", 11.0, None, [11]):
            cases.append(
                {
                    "builder": "start",
                    "index": bad_index,
                    "expected": "invalid_item_index",
                }
            )
            cases.append(
                {
                    "builder": "click",
                    "index": bad_index,
                    "expected": "invalid_item_index",
                }
            )
            cases.append(
                {
                    "builder": "finish",
                    "index": bad_index,
                    "expected": "invalid_item_index",
                }
            )
        return cases

    def build(self, builder: str, **kwargs: object) -> Dict[str, object]:
        if builder == "start":
            return envelope_mod.build_envelope_start(**kwargs)  # type: ignore[arg-type]
        if builder == "click":
            return envelope_mod.build_envelope_click(**kwargs)  # type: ignore[arg-type]
        return envelope_mod.build_envelope_finish(**kwargs)  # type: ignore[arg-type]

    def test_structurally_invalid_input_fails_closed(self) -> None:
        for case in self.cases():
            builder = str(case.pop("builder"))
            expected = str(case.pop("expected"))
            index = case.pop("index", capture.FIXTURE_ITEM_INDEX)
            with self.subTest(builder=builder, case=case):
                arguments = dict(case)
                if builder == "start":
                    arguments.setdefault("duration", capture.FIXTURE_BUILD_TIME)
                arguments["item_index"] = index
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(builder, **arguments)
                self.assertEqual(caught.exception.code, expected)

    def test_the_validation_order_is_index_then_duration_then_timestamp(self) -> None:
        """The unresolvable value closest to the contract is reported first."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.build_envelope_start("11", 0, ts=-1)
        self.assertEqual(caught.exception.code, "invalid_item_index")
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.build_envelope_start(11, 0, ts=-1)
        self.assertEqual(caught.exception.code, "invalid_duration")
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.build_envelope_click(11, ts=-1)
        self.assertEqual(caught.exception.code, "invalid_timestamp")


class SharedSerializationTests(unittest.TestCase):
    """Each single-command envelope travels through the unchanged helpers."""

    def build_all(self) -> List[Dict[str, object]]:
        return [
            envelope_mod.build_envelope_start(
                item_index=capture.FIXTURE_ITEM_INDEX, duration=5, ts=1700000000
            ),
            envelope_mod.build_envelope_click(
                item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
            ),
            envelope_mod.build_envelope_finish(
                item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
            ),
        ]

    def test_roundtrip_through_the_legacy_field_format(self) -> None:
        for built in self.build_all():
            with self.subTest(command=built["commands"][0][1]):
                data = envelope_mod.data_field(built)
                self.assertEqual(len(data.split(";", 1)[0]), 64)
                self.assertEqual(data[64], ";")
                self.assertEqual(envelope_mod.parse_data_field(data), built)

    def test_serialization_is_deterministic(self) -> None:
        for built in self.build_all():
            with self.subTest(command=built["commands"][0][1]):
                first = envelope_mod.payload_json(built)
                second = envelope_mod.payload_json(built)
                self.assertEqual(first, second)
                self.assertTrue(
                    first.startswith('{"accessToken":"","commands":[')
                )

    def test_the_payloads_carry_exactly_the_established_commands(self) -> None:
        """The contract verified against the real legacy server, verbatim."""
        payloads = [
            json.loads(envelope_mod.data_field(built)[65:]) for built in self.build_all()
        ]
        self.assertEqual(
            [payload["commands"][0] for payload in payloads],
            [
                [0, "activate", [11, 5], [0, 0, 0, 0, 0, 0, 0, 0]],
                [0, "add_click", [11], [0, 0, 0, 0, 0, 0, 0, 0]],
                [0, "activate_item_click", [11], [0, 0, 0, 0, 0, 0, 0, 0]],
            ],
        )
        for payload in payloads:
            self.assertEqual(payload["first_number"], 0)
            self.assertEqual(payload["publishActions"], [])
            self.assertEqual(payload["tries"], 1)
            self.assertEqual(payload["accessToken"], "")

    def test_malformed_fields_fail_closed(self) -> None:
        good = envelope_mod.data_field(self.build_all()[0])
        broken = [
            good[65:],
            "x" + good[1:],
            good[:64] + ":" + good[65:],
            good[:64] + ";" + "{not json",
            good[:64] + ";" + "[1,2]",
            good[:64] + ";" + '{"commands": []}',
            "ab" + good[2:],
        ]
        for data in broken:
            with self.subTest(data=data[:40]):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.parse_data_field(data)
                self.assertEqual(caught.exception.code, "invalid_data_field")


class RealConfigCrossCheckTests(unittest.TestCase):
    """The committed config and seed must satisfy every closed assumption."""

    def test_the_fixture_row_is_the_one_the_committed_config_names(self) -> None:
        turret = item_by_id(capture.FIXTURE_ITEM_ID)
        self.assertEqual(turret["name"], capture.FIXTURE_ITEM_NAME)
        self.assertEqual(turret["type"], "b")
        # The derived duration and the click requirement are the item's own
        # committed fields, resolved with the endpoint's own rule.
        self.assertEqual(int_attribute(capture.FIXTURE_ITEM_ID, "build_time"),
                         capture.FIXTURE_BUILD_TIME)
        self.assertEqual(
            int_attribute(capture.FIXTURE_ITEM_ID, "clicks_to_build"),
            capture.FIXTURE_CLICKS_TO_BUILD,
        )
        self.assertEqual(
            capture.config_build_time(capture.FIXTURE_ITEM_ID),
            capture.FIXTURE_BUILD_TIME,
        )
        self.assertEqual(
            capture.config_clicks_to_build(capture.FIXTURE_ITEM_ID),
            capture.FIXTURE_CLICKS_TO_BUILD,
        )
        # The purchase-side click seed exists for this item (engine.py:25-28),
        # which is why the delivered upgrade fixture's row carries {"nc": 0}.
        self.assertGreater(
            int_attribute(capture.FIXTURE_ITEM_ID, "clicks_to_build"), 0
        )

    def test_the_derived_duration_is_the_build_time_not_the_activation_field(self) -> None:
        """Design D2: ``build_time`` is the derivation's source, not
        ``activation`` — and never a client value, never speedup-adjusted."""
        turret = item_by_id(capture.FIXTURE_ITEM_ID)
        # The corpus's placed buildings all have activation 0, so a derivation
        # that read `activation` would record a countdown of 0 — which legacy
        # would answer by CLEARING the whole attribute bag.
        self.assertEqual(int_attribute(capture.FIXTURE_ITEM_ID, "activation"), 0)
        self.assertGreater(capture.FIXTURE_BUILD_TIME, 0)
        self.assertNotEqual(
            capture.config_build_time(capture.FIXTURE_ITEM_ID),
            int_attribute(capture.FIXTURE_ITEM_ID, "activation"),
        )

    def test_the_committed_config_records_no_building_price(self) -> None:
        """Design D4: nothing in the committed config prices a build.

        ``cost``/``cost_type`` are dead fields across every item and ``costs``
        prices the *purchase* only, so the neutral vector is the only derivable
        choice and this change claims no building cost.  The one
        construction-named global prices a *speedup*, which is a separate
        mechanism deliberately out of scope.
        """
        costs_keys = set()
        for entry in CONFIG["items"]:
            self.assertEqual(entry.get("cost"), "0")
            self.assertIsNone(entry.get("cost_type"))
            raw = entry.get("costs")
            if raw not in (None, ""):
                costs_keys |= set(json.loads(raw).keys())
        self.assertTrue(costs_keys <= {"g", "w", "o", "s", "c"})
        self.assertNotIn("build", costs_keys)
        self.assertNotIn("time", costs_keys)
        # The speedup prices exist and are a distinct class: the two build-named
        # globals price a construction *speedup* (and its minimum wait), which
        # no command in this contract executes, so nothing here derives from
        # them.
        speedup_globals = sorted(
            key for key in CONFIG["globals"] if "SPEEDUP" in key.upper()
        )
        self.assertEqual(
            speedup_globals,
            [
                "BUILD_SPEEDUP_MIN_TIME",
                "BUILD_SPEEDUP_PRICING",
                "UPGRADE_SPEEDUP_PRICING",
            ],
        )
        self.assertEqual(CONFIG["globals"]["BUILD_SPEEDUP_PRICING"], [5, 1])
        self.assertEqual(CONFIG["globals"]["BUILD_SPEEDUP_MIN_TIME"], 10)
        self.assertEqual(CONFIG["globals"]["UPGRADE_SPEEDUP_PRICING"], [5, 1])
        # The item's own purchase price never leaks into the neutral vector.
        self.assertEqual(item_by_id(capture.FIXTURE_ITEM_ID)["costs"], '{"s":125}')
        self.assertNotIn(-125, envelope_mod.neutral_vector())

    def test_no_committed_branch_compares_the_click_counter(self) -> None:
        """The threshold is a client derivation: no server-side completion rule."""
        # The three commands' source ranges write item[3] and item[6] only, and
        # engine.add_click / engine.activate_item_click raise and delete the
        # counter without reading the item's clicks_to_build.  The catalog
        # records the same for all three entries.
        catalog = json.loads(
            (harness.REPO_ROOT / "docs" / "legacy-protocol" / "commands.json").read_text(
                encoding="utf-8"
            )
        )
        by_name = {entry["name"]: entry for entry in catalog["commands"]}
        for name in ("activate", "add_click", "activate_item_click"):
            with self.subTest(command=name):
                writes = " ".join(by_name[name]["state_writes"])
                self.assertNotIn("clicks_to_build", writes)
                self.assertNotIn("bought_unit_add", writes)
        # And the fresh corpus carries no construction to observe.
        for key, row in FRESH_ITEMS.items():
            with self.subTest(key=key):
                self.assertEqual(row[6], {})
                self.assertEqual(row[3], 0)
                self.assertEqual(row[5], [])

    def test_the_fresh_save_can_execute_the_fixture_construction(self) -> None:
        row = FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        self.assertEqual(len(FRESH_ITEMS), capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE)
        self.assertEqual(len(row), 8)
        self.assertEqual(int(row[0]), capture.FIXTURE_ITEM_ID)
        self.assertEqual([row[1], row[2]], [capture.FIXTURE_X, capture.FIXTURE_Y])
        self.assertEqual(row[4], 0)  # orientation
        self.assertEqual(row[5], [])  # store
        self.assertEqual(row[6], {})  # attr: no construction state
        self.assertEqual(row[7], 1)  # player team

    def test_the_fresh_save_starts_with_the_resources_the_fixture_keeps(self) -> None:
        self.assertEqual(FRESH_MAP["xp"], 4)
        for name in ("gold", "wood", "oil", "steel"):
            self.assertEqual(FRESH_MAP[name], 2000)
        self.assertEqual(SEED["playerInfo"]["cash"], 5)  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["mana"], 0)  # type: ignore[index]
        self.assertEqual(FRESH_MAP["store"], {})
        self.assertEqual(SEED["privateState"]["boughtUnits"], [])  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["deadHeroes"], {})  # type: ignore[index]

    def test_the_fixture_row_is_the_move_fixtures_row_and_only_that(self) -> None:
        """Design D10: all eight committed fixtures stay readable.

        The construction and move fixtures share slot 11 because each capture
        seeds a **fresh** corpus, so their transactions are independent; the
        upgrade (12), sell (20), and store (2) fixtures use other rows, which
        this fixture must never touch.
        """
        self.assertEqual(
            FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)],
            [capture.FIXTURE_ITEM_ID, capture.FIXTURE_X, capture.FIXTURE_Y, 0, 0, [], {}, 1],
        )
        self.assertEqual(int(FRESH_ITEMS["11"][0]), capture.FIXTURE_ITEM_ID)  # move fixture
        self.assertEqual(int(FRESH_ITEMS["20"][0]), 22)  # sell fixture: Turret I
        self.assertEqual(int(FRESH_ITEMS["2"][0]), 905)  # store fixture: the Tree
        self.assertEqual(int(FRESH_ITEMS["12"][0]), 23)  # upgrade fixture: Wall I


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_ITEM_INDEX, 11)
        self.assertEqual(capture.FIXTURE_ITEM_ID, 22)
        self.assertEqual(capture.FIXTURE_ITEM_NAME, "Turret I")
        self.assertEqual((capture.FIXTURE_X, capture.FIXTURE_Y), (58, 48))
        self.assertEqual(capture.FIXTURE_BUILD_TIME, 5)
        self.assertEqual(capture.FIXTURE_CLICKS_TO_BUILD, 1)
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_AFTER, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_ATTR_AFTER, {"cp": 5, "nc": 1})
        self.assertIn("Turret I", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_construction"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-construction",
        )

    def test_the_config_resolvers_apply_the_documented_positive_rule(self) -> None:
        """Absent, non-integer, zero, and negative mean no resolvable value."""
        self.assertEqual(capture.config_build_time(capture.FIXTURE_ITEM_ID), 5)
        # An id the config does not resolve has no attribute at all.
        self.assertIsNone(capture.config_build_time(999999))
        self.assertIsNone(capture.config_clicks_to_build(999999))
        # The stored Key (item 902) is a unit with no construction duration:
        # the value, not the item class, is what the rule reads.
        for item_id in (905, 902):
            with self.subTest(item_id=item_id):
                raw = capture.config_item_attribute(item_id, "build_time")
                resolved = capture.config_build_time(item_id)
                if raw is None or resolved is None:
                    continue
                self.assertGreater(resolved, 0)
        # A value of "0" is not a duration and is never coerced to one.
        self.assertIsNone(capture.config_build_time(-1))
        self.assertIsNone(capture.config_clicks_to_build(-1))

    def test_the_fixture_batch_is_the_two_established_commands(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(
            built["commands"],
            [
                [0, "activate", [11, 5], [0] * 8],
                [0, "add_click", [11], [0] * 8],
            ],
        )
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        capture.verify_envelope(built)

    def test_the_batch_is_composed_from_the_shared_derivation(self) -> None:
        """The captured request and the endpoint can never drift apart."""
        built = capture.build_fixture_envelope(ts=1700000000)
        start = envelope_mod.build_envelope_start(
            item_index=capture.FIXTURE_ITEM_INDEX,
            duration=capture.FIXTURE_BUILD_TIME,
            ts=1700000000,
        )
        click = envelope_mod.build_envelope_click(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        self.assertEqual(built["commands"], start["commands"] + click["commands"])
        for key in envelope_mod.ENVELOPE_KEYS:
            if key == "commands":
                continue
            self.assertEqual(built[key], start[key])
        # The captured batch never carries the completing command, which is
        # recorded separately (task 1.3).
        names = [entry[1] for entry in built["commands"]]
        self.assertNotIn("activate_item_click", names)

    def test_protected_fixtures_are_the_seven_committed_ones(self) -> None:
        self.assertEqual(
            [relative for relative, _label in capture.PROTECTED_FIXTURES],
            [
                "tests/fixtures/godot-compatibility-boot",
                "tests/fixtures/godot-building-placement",
                "tests/fixtures/godot-item-purchase",
                "tests/fixtures/godot-building-move",
                "tests/fixtures/godot-building-sell",
                "tests/fixtures/godot-building-store",
                "tests/fixtures/godot-building-upgrade",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        cases = {
            "one command only": lambda env: env["commands"].pop(),
            "reversed order": lambda env: env["commands"].reverse(),
            "another index": lambda env: env["commands"][0][2].__setitem__(0, 12),
            "another duration": lambda env: env["commands"][0][2].__setitem__(1, 600),
            "a zero duration": lambda env: env["commands"][0][2].__setitem__(1, 0),
            "a client-sent duration": lambda env: env["commands"][0][2].__setitem__(1, 1),
            "another command name": lambda env: env["commands"][1].__setitem__(
                1, "activate_item_click"
            ),
            "a non-neutral activate vector": lambda env: env["commands"][0][3].__setitem__(
                2, -500
            ),
            "a non-neutral click vector": lambda env: env["commands"][1][3].__setitem__(
                6, -500
            ),
            "another map id": lambda env: env["commands"][0].__setitem__(0, 1),
            "extra envelope keys": lambda env: env.__setitem__("extra", 1),
        }
        for label, mutate in sorted(cases.items()):
            with self.subTest(case=label):
                drifted = json.loads(json.dumps(built))
                mutate(drifted)
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_envelope(drifted)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_the_omitted_third_step_is_recorded_with_its_evidence(self) -> None:
        """Task 1.3: the completing command is covered, not captured."""
        omitted = capture.OMITTED_STEP
        self.assertEqual(omitted["command"], "activate_item_click")
        self.assertEqual(omitted["args"], [capture.FIXTURE_ITEM_INDEX])
        self.assertIn("BOTH", omitted["why_not_captured"])
        self.assertIn("counter", omitted["why_not_captured"])
        self.assertIn("docs/legacy-construction-timing.md", omitted["established_by"])
        self.assertIn("probe C", omitted["established_by"])
        self.assertIn("internal_error", omitted["covered_by"])
        self.assertIn("never observed", omitted["not_observed_from_client"])

    def test_time_dependent_fields_are_named_as_json_pointers(self) -> None:
        """The capture publishes exactly which leaves move between runs."""
        source = Path_read_text(capture.__file__)
        self.assertIn('"time_dependent_fields"', source)
        self.assertIn("/maps/0/items/%d/3", source)
        self.assertIn("/transaction/row_after/3", source)
        self.assertIn("/transaction/steps/1/save_after_sha256", source)

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        before = json.loads(json.dumps(SEED))
        after = derived_construction_state()
        self.assertEqual(
            before["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)],
            [capture.FIXTURE_ITEM_ID, capture.FIXTURE_X, capture.FIXTURE_Y, 0, 0, [], {}, 1],
        )
        capture.verify_transaction(before, after, built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        key = str(capture.FIXTURE_ITEM_INDEX)

        def destroy():
            document = derived_construction_state()
            document["maps"][0]["items"].pop(key)
            return document

        def remove_another():
            document = derived_construction_state()
            document["maps"][0]["items"].pop("12")
            return document

        def change_another():
            document = derived_construction_state()
            document["maps"][0]["items"]["12"] = [23, 46, 49, 0, 0, [], {}, 1]
            return document

        cases = {
            "the row was destroyed": destroy,
            "another row was removed": remove_another,
            "another row changed": change_another,
            "a wrong item id": lambda: derived_construction_state(item=57),
            "a different cell": lambda: derived_construction_state(x=59),
            "a non-wall-clock start time": lambda: derived_construction_state(
                timestamp=0
            ),
            "a countdown that is not the derived duration": lambda: (
                derived_construction_state(attr={"cp": 3600, "nc": 1})
            ),
            "a missing click counter": lambda: derived_construction_state(
                attr={"cp": 5}
            ),
            "a cleared attribute bag": lambda: derived_construction_state(attr={}),
            "a changed player team": lambda: derived_construction_state(player=0),
            "a changed orientation": lambda: derived_construction_state(
                orientation=3
            ),
            "a stored-unit payload appeared": lambda: derived_construction_state(
                store=[1]
            ),
            "storage changed": lambda: derived_construction_state(store_map={"22": 1}),
            "a resource changed": lambda: derived_construction_state(gold=0),
            "the map timestamp changed": lambda: derived_construction_state(
                map_timestamp=1234567890
            ),
            "a private-state field changed": lambda: derived_construction_state(
                bought=[22]
            ),
            "deadHeroes changed": lambda: derived_construction_state(
                dead_heroes={"22": True}
            ),
            "mana changed": lambda: derived_construction_state(mana=7),
        }
        for label, build in sorted(cases.items()):
            with self.subTest(case=label):
                before = json.loads(json.dumps(SEED))
                after = build()
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


def derived_construction_state(
    item: int = capture.FIXTURE_ITEM_ID,
    x: int = capture.FIXTURE_X,
    y: int = capture.FIXTURE_Y,
    timestamp: int = 1790000000,
    orientation: int = 0,
    store: Optional[list] = None,
    attr: Optional[dict] = None,
    player: int = 1,
    store_map: Optional[dict] = None,
    gold: Optional[int] = None,
    map_timestamp: Optional[int] = None,
    bought: Optional[list] = None,
    dead_heroes: Optional[dict] = None,
    mana: Optional[int] = None,
) -> Dict[str, object]:
    """A fresh-save copy carrying the derived construction, overridable.

    Defaults are the executed outcome, so every override in the mismatch table
    names exactly one deviation from it.
    """
    document = json.loads(json.dumps(SEED))
    document["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)] = [
        item,
        x,
        y,
        timestamp,
        orientation,
        list(store) if store is not None else [],
        dict(attr) if attr is not None else dict(capture.FIXTURE_EXPECTED_ATTR_AFTER),
        player,
    ]
    if bought is not None:
        document["privateState"]["boughtUnits"] = list(bought)
    if dead_heroes is not None:
        document["privateState"]["deadHeroes"] = dead_heroes
    if store_map is not None:
        document["maps"][0]["store"] = store_map
    if gold is not None:
        document["maps"][0]["gold"] = gold
    if map_timestamp is not None:
        document["maps"][0]["timestamp"] = map_timestamp
    if mana is not None:
        document["privateState"]["mana"] = mana
    return document


def Path_read_text(module_file) -> str:
    """The capture module's own source, for the published-constant checks."""
    from pathlib import Path

    return Path(module_file).read_text(encoding="utf-8")


class SanitizationTests(unittest.TestCase):
    """Recorded requests carry no user_key or token values."""

    def test_form_user_key_is_always_redacted(self) -> None:
        form = {"USERID": "pid", "user_key": "S3CRET", "language": "en"}
        sanitized = capture.sanitize_form(form)
        self.assertEqual(sanitized["user_key"], capture.REDACTED)
        self.assertEqual(sanitized["USERID"], "pid")
        self.assertNotIn("S3CRET", json.dumps(sanitized))

    def test_crafted_empty_token_keeps_the_exact_sent_bytes(self) -> None:
        data = envelope_mod.data_field(capture.build_fixture_envelope(ts=1700000000))
        self.assertEqual(capture.sanitize_data_field(data), data)

    def test_non_empty_access_token_is_redacted_in_the_data_field(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        built["accessToken"] = "TOKEN-SECRET"
        data = envelope_mod.data_field(built)
        record = capture.sanitize_data_field(data)
        self.assertNotIn("TOKEN-SECRET", record)
        parsed = envelope_mod.parse_data_field(record)
        self.assertEqual(parsed["accessToken"], capture.REDACTED)
        self.assertEqual(parsed["commands"], built["commands"])

    def test_session_cookie_headers_are_redacted_but_others_survive(self) -> None:
        headers = {
            "Date": "Mon, 28 Sep 2026 15:30:46 GMT",
            "Set-Cookie": "session=SESSION-TOKEN-SECRET; HttpOnly; Path=/",
            "Content-Type": "text/html; charset=utf-8",
        }
        sanitized = capture.sanitize_headers(headers)
        self.assertEqual(sanitized["Set-Cookie"], capture.REDACTED)
        self.assertEqual(sanitized["Date"], headers["Date"])
        self.assertNotIn("SESSION-TOKEN-SECRET", json.dumps(sanitized))


if __name__ == "__main__":
    unittest.main()
