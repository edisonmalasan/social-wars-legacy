#!/usr/bin/env python3
"""Offline unit tests for the move envelope derivation and the move capture
tool's published contract (OpenSpec task 2.1 / task 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the fixture intent and
the neutral price derivation (design D2) against the bytes the legacy server
actually loads, and the shared-helper round trip proves the move envelope
travels through the placement module's unchanged serialization (design D6).
"""

from __future__ import annotations

import json
import time
import unittest

import compat_test_harness as harness

import capture_move_fixture as capture
import move_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]


def item_by_id(item_id: int) -> dict:
    for entry in CONFIG["items"]:
        if int(entry["id"]) == item_id:
            return entry
    raise AssertionError("config has no item id %d" % item_id)


class SharedHelperTests(unittest.TestCase):
    """Design D6: the shared helpers are reused, not re-implemented."""

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
        # The move derivation is additive: placement keeps its own.
        self.assertFalse(hasattr(placement_envelope, "neutral_vector"))
        self.assertFalse(hasattr(placement_envelope, "MOVE_COMMAND"))

    def test_the_command_and_placeholders_are_the_documented_ones(self) -> None:
        # command.py:119-134: five positional args, the last two discarded.
        self.assertEqual(envelope_mod.MOVE_COMMAND, "move")
        self.assertEqual(envelope_mod.DEFAULT_FRAME, 0)
        self.assertEqual(envelope_mod.DEFAULT_STRING, "")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.move_envelope, envelope_mod)
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
    """Design D2: the derived vector is all zeros in all eight slots."""

    def test_the_vector_is_eight_zeros(self) -> None:
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.neutral_vector()
        first[6] = -999
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_the_built_envelope_carries_the_neutral_vector(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=11, x=58, y=47, ts=1700000000
        )
        self.assertEqual(built["commands"][0][3], [0] * 8)


class BuildEnvelopeTests(unittest.TestCase):
    def build(self, **overrides):
        arguments = {"item_index": 11, "x": 58, "y": 47, "ts": 1700000000}
        arguments.update(overrides)
        return envelope_mod.build_envelope(**arguments)

    def test_envelope_has_exactly_the_six_legacy_keys(self) -> None:
        built = self.build()
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        self.assertEqual(built["first_number"], 0)
        self.assertEqual(built["publishActions"], [])
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(built["tries"], 1)
        self.assertEqual(built["accessToken"], "")

    def test_single_move_command(self) -> None:
        built = self.build()
        self.assertEqual(len(built["commands"]), 1)
        map_id, cmd, args, vector = built["commands"][0]
        self.assertEqual(map_id, 0)
        self.assertEqual(cmd, "move")
        self.assertEqual(args, [11, 58, 47, 0, ""])
        self.assertEqual(vector, [0] * 8)

    def test_the_argument_list_is_exactly_the_five_the_branch_reads(self) -> None:
        # command.py:120-124 binds args[0..4] and nothing else.
        args = self.build()["commands"][0][2]
        self.assertEqual(len(args), 5)
        self.assertEqual(
            [args[0], args[1], args[2]], [11, 58, 47]
        )  # item_index, x, y
        self.assertEqual(args[3], 0)  # frame placeholder, read and discarded
        self.assertEqual(args[4], "")  # string placeholder, read and discarded

    def test_the_placeholders_default_but_can_be_supplied(self) -> None:
        built = self.build(frame=7, string="anything")
        self.assertEqual(built["commands"][0][2], [11, 58, 47, 7, "anything"])

    def test_coordinate_bound_edges(self) -> None:
        """Anchor-based 0..99, both edges, one step outside each."""
        for x, y in ((0, 0), (99, 99), (0, 99), (99, 0), (58, 47)):
            with self.subTest(x=x, y=y):
                built = envelope_mod.build_envelope(
                    item_index=11, x=x, y=y, ts=1700000000
                )
                self.assertEqual(built["commands"][0][2][1:3], [x, y])
        for x, y in ((-1, 0), (0, -1), (100, 0), (0, 100), (100, 100)):
            with self.subTest(x=x, y=y):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope(
                        item_index=11, x=x, y=y, ts=1700000000
                    )
                self.assertEqual(caught.exception.code, "invalid_coordinates")

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = self.build(ts=None)
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_structurally_invalid_input_fails_closed(self) -> None:
        cases = [
            ({"item_index": True}, "invalid_item_index"),
            ({"item_index": "11"}, "invalid_item_index"),
            ({"item_index": 11.0}, "invalid_item_index"),
            ({"item_index": None}, "invalid_item_index"),
            ({"x": "58"}, "invalid_coordinates"),
            ({"y": 47.5}, "invalid_coordinates"),
            ({"x": -1}, "invalid_coordinates"),
            ({"y": 100}, "invalid_coordinates"),
            ({"frame": "0"}, "invalid_frame"),
            ({"frame": True}, "invalid_frame"),
            ({"string": 0}, "invalid_string"),
            ({"string": None}, "invalid_string"),
            ({"ts": -1}, "invalid_timestamp"),
            ({"ts": "1700000000"}, "invalid_timestamp"),
            ({"ts": True}, "invalid_timestamp"),
        ]
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(**overrides)
                self.assertEqual(caught.exception.code, code)

    def test_item_index_is_checked_before_coordinates(self) -> None:
        """An unresolvable index is the client's error, whatever the cell."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(item_index="11", x="58")
        self.assertEqual(caught.exception.code, "invalid_item_index")

    def test_coordinates_are_checked_before_the_placeholders(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(x=-1, frame="0")
        self.assertEqual(caught.exception.code, "invalid_coordinates")

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(x=1000, y=1000)
        message = str(caught.exception)
        self.assertIn("town grid", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class SharedSerializationTests(unittest.TestCase):
    """The move envelope travels through the unchanged shared helpers."""

    def built(self):
        return envelope_mod.build_envelope(
            item_index=11, x=58, y=47, ts=1700000000
        )

    def test_roundtrip_through_the_legacy_field_format(self) -> None:
        data = envelope_mod.data_field(self.built())
        self.assertEqual(len(data.split(";", 1)[0]), 64)
        self.assertEqual(data[64], ";")
        self.assertEqual(envelope_mod.parse_data_field(data), self.built())

    def test_serialization_is_deterministic(self) -> None:
        first = envelope_mod.payload_json(self.built())
        second = envelope_mod.payload_json(self.built())
        self.assertEqual(first, second)
        self.assertTrue(first.startswith('{"accessToken":"","commands":['))

    def test_the_move_payload_carries_exactly_one_command(self) -> None:
        data = envelope_mod.data_field(self.built())
        payload = json.loads(data[65:])
        self.assertEqual(
            payload["commands"],
            [[0, "move", [11, 58, 47, 0, ""], [0, 0, 0, 0, 0, 0, 0, 0]]],
        )

    def test_malformed_fields_fail_closed(self) -> None:
        good = envelope_mod.data_field(self.built())
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

    def test_the_fixture_item_is_a_one_by_one_building(self) -> None:
        turret = item_by_id(capture.FIXTURE_ITEM_ID)
        self.assertEqual(turret["name"], capture.FIXTURE_ITEM_NAME)
        self.assertEqual(turret["type"], "b")
        self.assertEqual(int(turret["width"]), 1)
        self.assertEqual(int(turret["height"]), 1)
        # The one price the config records for it buys the building; a move
        # never carries that price (design D2), which is exactly why the
        # derived vector is neutral instead of "the item's price".
        self.assertEqual(turret["costs"], '{"s":125}')
        self.assertNotIn(-125, envelope_mod.neutral_vector())

    def test_the_committed_config_records_no_move_price(self) -> None:
        """Design D2: nothing in the committed config prices a move.

        ``cost``/``cost_type`` are dead fields, ``costs`` prices the purchase
        only, and no global mentions a move cost — so the neutral vector is
        the only derivable choice, and no config key could contradict it.
        """
        costs_keys = set()
        for entry in CONFIG["items"]:
            self.assertEqual(entry.get("cost"), "0")
            self.assertIsNone(entry.get("cost_type"))
            raw = entry.get("costs")
            if raw not in (None, ""):
                costs_keys |= set(json.loads(raw).keys())
        self.assertTrue(costs_keys <= {"g", "w", "o", "s", "c"})
        self.assertNotIn("move", costs_keys)
        globals_keys = {str(key).lower() for key in CONFIG["globals"]}
        self.assertFalse([key for key in globals_keys if "move" in key])

    def test_the_fresh_save_can_execute_the_fixture_move(self) -> None:
        row = FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        self.assertEqual(len(FRESH_ITEMS), capture.FIXTURE_EXPECTED_PLACEMENTS)
        self.assertEqual(len(row), 8)
        self.assertEqual(int(row[0]), capture.FIXTURE_ITEM_ID)
        self.assertEqual(
            [row[1], row[2]], [capture.FIXTURE_FROM_X, capture.FIXTURE_FROM_Y]
        )

    def test_the_derived_target_is_free_and_inside_the_grid(self) -> None:
        occupied = {(row[1], row[2]) for row in FRESH_ITEMS.values()}
        self.assertNotIn((capture.FIXTURE_TO_X, capture.FIXTURE_TO_Y), occupied)
        self.assertTrue(
            envelope_mod.in_grid(capture.FIXTURE_TO_X, capture.FIXTURE_TO_Y)
        )
        # The four one-step neighbours of the anchor, two of them occupied.
        anchor = (capture.FIXTURE_FROM_X, capture.FIXTURE_FROM_Y)
        neighbours = [
            (anchor[0] + dx, anchor[1] + dy)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
        ]
        free = sorted(
            (cell for cell in neighbours if cell not in occupied),
            key=lambda cell: (cell[1], cell[0]),
        )
        self.assertEqual(free, [(58, 47), (57, 48)])
        # Row-major tiebreak (smallest y, then smallest x) selects (58,47).
        self.assertEqual(free[0], (capture.FIXTURE_TO_X, capture.FIXTURE_TO_Y))

    def test_the_neutral_vector_leaves_every_stored_resource_alone(self) -> None:
        vector = envelope_mod.neutral_vector()
        self.assertEqual(vector[1], 0)  # xp
        for index in (2, 3, 4, 5):  # gold, wood, oil, steel
            self.assertEqual(vector[index], 0)
        self.assertEqual(vector[6], 0)  # cash
        self.assertEqual(vector[7], 0)  # mana
        # A neutral vector means the clamp never changes a value.
        for value in (0, 4, 2000):
            self.assertEqual(max(value + 0, 0), value)


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_ITEM_INDEX, 11)
        self.assertEqual(capture.FIXTURE_ITEM_ID, 22)
        self.assertEqual(capture.FIXTURE_ITEM_NAME, "Turret I")
        self.assertEqual(
            (capture.FIXTURE_FROM_X, capture.FIXTURE_FROM_Y), (58, 48)
        )
        self.assertEqual((capture.FIXTURE_TO_X, capture.FIXTURE_TO_Y), (58, 47))
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS, 40)
        self.assertIn("Manhattan", capture.TARGET_RULE)
        self.assertIn("row-major", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_move"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-move",
        )

    def test_derived_fixture_envelope_pins_the_expected_values(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            x=capture.FIXTURE_TO_X,
            y=capture.FIXTURE_TO_Y,
            frame=capture.FIXTURE_FRAME,
            string=capture.FIXTURE_STRING,
            ts=1700000000,
        )
        self.assertEqual(built["commands"][0][1], "move")
        self.assertEqual(built["commands"][0][2], [11, 58, 47, 0, ""])
        self.assertEqual(built["commands"][0][3], capture.FIXTURE_EXPECTED_VECTOR)
        capture.verify_envelope(built)

    def test_protected_fixtures_are_the_committed_boot_placement_and_purchase(
        self,
    ) -> None:
        self.assertEqual(
            [relative for relative, _label in capture.PROTECTED_FIXTURES],
            [
                "tests/fixtures/godot-compatibility-boot",
                "tests/fixtures/godot-building-placement",
                "tests/fixtures/godot-item-purchase",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            x=capture.FIXTURE_TO_X,
            y=capture.FIXTURE_TO_Y,
            ts=1700000000,
        )
        # A drifting target cell must fail the run, not publish a new fixture.
        built["commands"][0][2] = [11, 57, 48, 0, ""]
        with self.assertRaises(capture.CaptureError) as caught:
            capture.verify_envelope(built)
        self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            x=capture.FIXTURE_TO_X,
            y=capture.FIXTURE_TO_Y,
            ts=1700000000,
        )
        before = json.loads(json.dumps(SEED))
        after = json.loads(json.dumps(SEED))
        after["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)][2] = (
            capture.FIXTURE_TO_Y
        )
        capture.verify_transaction(before, after, built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            x=capture.FIXTURE_TO_X,
            y=capture.FIXTURE_TO_Y,
            ts=1700000000,
        )
        cases = {
            "a second row moved": lambda doc: doc["maps"][0]["items"].__setitem__(
                "10", [23, 59, 48, 0, 0, [], {}, 1]
            ),
            "the row's timestamp changed": lambda doc: doc["maps"][0]["items"][
                str(capture.FIXTURE_ITEM_INDEX)
            ].__setitem__(3, 1700000000),
            "a resource changed": lambda doc: doc["maps"][0].__setitem__("gold", 0),
            "storage changed": lambda doc: doc["maps"][0].__setitem__(
                "store", {"22": 1}
            ),
            "boughtUnits changed": lambda doc: doc["privateState"].__setitem__(
                "boughtUnits", [22]
            ),
            "a row was removed": lambda doc: doc["maps"][0]["items"].pop("10"),
        }
        for label, mutate in sorted(cases.items()):
            with self.subTest(case=label):
                before = json.loads(json.dumps(SEED))
                after = json.loads(json.dumps(SEED))
                after["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)][2] = (
                    capture.FIXTURE_TO_Y
                )
                mutate(after)
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


class SanitizationTests(unittest.TestCase):
    """Design D9: recorded requests carry no user_key or token values."""

    def test_form_user_key_is_always_redacted(self) -> None:
        form = {"USERID": "pid", "user_key": "S3CRET", "language": "en"}
        sanitized = capture.sanitize_form(form)
        self.assertEqual(sanitized["user_key"], capture.REDACTED)
        self.assertEqual(sanitized["USERID"], "pid")
        self.assertNotIn("S3CRET", json.dumps(sanitized))

    def test_crafted_empty_token_keeps_the_exact_sent_bytes(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            x=capture.FIXTURE_TO_X,
            y=capture.FIXTURE_TO_Y,
            ts=1700000000,
        )
        data = envelope_mod.data_field(built)
        self.assertEqual(capture.sanitize_data_field(data), data)

    def test_non_empty_access_token_is_redacted_in_the_data_field(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            x=capture.FIXTURE_TO_X,
            y=capture.FIXTURE_TO_Y,
            ts=1700000000,
        )
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
