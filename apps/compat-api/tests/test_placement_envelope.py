#!/usr/bin/env python3
"""Offline unit tests for the shared placement envelope derivation and the
capture tool's sanitization (OpenSpec task 1.1).

No server, no socket, no corpus: everything here is pure derivation over
the committed config and seed documents, so it runs in milliseconds under
the pinned interpreter.  The real-config cross-checks pin the closed cost
vocabulary (design D4) and the anchor-bounds rule (design D5, corrected
during Apply) against the bytes the legacy server actually loads.
"""

from __future__ import annotations

import json
import time
import unittest

import compat_test_harness as harness

import capture_placement_fixture as capture
import placement_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_ITEMS = SEED["maps"][0]["items"]  # type: ignore[index]


def item_by_id(item_id: int) -> dict:
    for entry in CONFIG["items"]:
        if int(entry["id"]) == item_id:
            return entry
    raise AssertionError("config has no item id %d" % item_id)


class StrictIntTests(unittest.TestCase):
    def test_ints_but_not_bools_or_other_types(self) -> None:
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertTrue(envelope_mod.is_strict_int(51))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int(False))
        self.assertFalse(envelope_mod.is_strict_int("51"))
        self.assertFalse(envelope_mod.is_strict_int(51.0))
        self.assertFalse(envelope_mod.is_strict_int(None))


class GridBoundsTests(unittest.TestCase):
    """Design D5 (corrected): bounds are anchor-based, 0..99."""

    def test_anchor_inside_grid(self) -> None:
        self.assertTrue(envelope_mod.in_grid(0, 0))
        self.assertTrue(envelope_mod.in_grid(51, 39))
        self.assertTrue(envelope_mod.in_grid(99, 99))

    def test_anchor_outside_grid(self) -> None:
        self.assertFalse(envelope_mod.in_grid(100, 0))
        self.assertFalse(envelope_mod.in_grid(0, 100))
        self.assertFalse(envelope_mod.in_grid(-1, 5))
        self.assertFalse(envelope_mod.in_grid(5, -1))

    def test_non_integers_never_count_as_in_grid(self) -> None:
        self.assertFalse(envelope_mod.in_grid(True, 5))
        self.assertFalse(envelope_mod.in_grid("51", 39))
        self.assertFalse(envelope_mod.in_grid(51.0, 39.0))

    def test_grid_extent_matches_the_godot_constant(self) -> None:
        self.assertEqual(envelope_mod.GRID_EXTENT, 100)


class CostVectorTests(unittest.TestCase):
    def test_known_keys_negate_into_the_legacy_slots(self) -> None:
        vector = envelope_mod.cost_vector({"g": 1000, "w": 30, "o": 1, "s": 2, "c": 5})
        self.assertEqual(vector, [0, 0, -1000, -30, -1, -2, -5, 0])

    def test_json_string_and_dict_forms_are_equivalent(self) -> None:
        self.assertEqual(
            envelope_mod.cost_vector('{"w":30}'),
            envelope_mod.cost_vector({"w": 30}),
        )

    def test_absent_and_empty_costs_are_a_zero_vector(self) -> None:
        self.assertEqual(envelope_mod.cost_vector(None), [0] * 8)
        self.assertEqual(envelope_mod.cost_vector(""), [0] * 8)
        self.assertEqual(envelope_mod.cost_vector("{}"), [0] * 8)

    def test_unknown_cost_key_fails_closed(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.cost_vector({"m": 5})
        self.assertEqual(caught.exception.code, "costs_unknown_key")

    def test_non_integer_amounts_fail_closed(self) -> None:
        for costs in ({"w": "30"}, {"w": True}, {"w": 30.5}, {"w": None}):
            with self.subTest(costs=costs):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.cost_vector(costs)
                self.assertEqual(caught.exception.code, "costs_invalid")

    def test_invalid_json_string_fails_closed(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.cost_vector("{not json")
        self.assertEqual(caught.exception.code, "costs_invalid")

    def test_non_object_decoded_form_fails_closed(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.cost_vector("[1, 2]")
        self.assertEqual(caught.exception.code, "costs_invalid")


class NextFreeSlotTests(unittest.TestCase):
    def test_empty_map_starts_at_one(self) -> None:
        self.assertEqual(envelope_mod.next_free_slot({}), 1)

    def test_contiguous_fresh_save_seeds_to_forty_one(self) -> None:
        self.assertEqual(envelope_mod.next_free_slot(FRESH_ITEMS), 41)

    def test_gap_is_reused_before_new_slots(self) -> None:
        self.assertEqual(envelope_mod.next_free_slot({"1": [], "3": []}), 2)

    def test_unparseable_keys_are_ignored(self) -> None:
        # Documented: a non-numeric key can never equal str(next_slot).
        self.assertEqual(envelope_mod.next_free_slot({"1": [], "abc": []}), 2)

    def test_zero_is_not_used_as_a_slot(self) -> None:
        self.assertEqual(envelope_mod.next_free_slot({"0": []}), 1)


class BuildEnvelopeTests(unittest.TestCase):
    def build(self, **overrides):
        arguments = {
            "item_id": 1,
            "x": 51,
            "y": 39,
            "costs": '{"w":30}',
            "items": FRESH_ITEMS,
            "orientation": 0,
            "ts": 1700000000,
        }
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

    def test_single_buy_command_carries_the_derived_args_and_vector(self) -> None:
        built = self.build()
        self.assertEqual(len(built["commands"]), 1)
        map_id, cmd, args, vector = built["commands"][0]
        self.assertEqual(map_id, 0)
        self.assertEqual(cmd, "buy")
        self.assertEqual(args, [41, 1, 51, 39, 1, 0, 0, ""])
        self.assertEqual(vector, [0, 0, 0, -30, 0, 0, 0, 0])

    def test_slot_tracks_the_items_state(self) -> None:
        items = dict(FRESH_ITEMS)
        items["41"] = []
        self.assertEqual(self.build(items=items)["commands"][0][2][0], 42)

    def test_orientation_passes_through(self) -> None:
        self.assertEqual(self.build(orientation=3)["commands"][0][2][5], 3)

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = self.build(ts=None)
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_structurally_invalid_input_fails_closed(self) -> None:
        cases = [
            ({"item_id": True}, "invalid_item_id"),
            ({"item_id": "1"}, "invalid_item_id"),
            ({"x": "51"}, "invalid_coordinates"),
            ({"y": 39.0}, "invalid_coordinates"),
            ({"orientation": "0"}, "invalid_orientation"),
            ({"ts": -1}, "invalid_timestamp"),
            ({"ts": "1700000000"}, "invalid_timestamp"),
        ]
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(**overrides)
                self.assertEqual(caught.exception.code, code)


class DataFieldTests(unittest.TestCase):
    def built(self):
        return envelope_mod.build_envelope(
            item_id=1, x=51, y=39, costs='{"w":30}',
            items=FRESH_ITEMS, orientation=0, ts=1700000000,
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
        # Sorted keys: accessToken sorts before commands (json.dumps
        # sort_keys=True), so byte order cannot depend on dict insertion.
        self.assertTrue(first.startswith('{"accessToken":"","commands":['))

    def test_malformed_fields_fail_closed(self) -> None:
        good = envelope_mod.data_field(self.built())
        broken = [
            good[65:],                       # no digest/semicolon prefix
            "x" + good[1:],                  # digest not hex
            good[:64] + ":" + good[65:],     # byte 64 is not ';'
            good[:64] + ";" + "{not json",   # payload not JSON
            good[:64] + ";" + "[1,2]",       # payload not an object
            good[:64] + ";" + '{"commands": []}',  # missing legacy keys
            "ab" + good[2:],                 # digest does not match payload
        ]
        for data in broken:
            with self.subTest(data=data[:40]):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.parse_data_field(data)
                self.assertEqual(caught.exception.code, "invalid_data_field")


class RealConfigCrossCheckTests(unittest.TestCase):
    """The committed config and seed must satisfy every closed assumption."""

    def test_every_item_cost_parses_with_the_closed_vocabulary(self) -> None:
        nonzero_slots = set()
        for entry in CONFIG["items"]:
            vector = envelope_mod.cost_vector(entry.get("costs"))
            self.assertEqual(len(vector), 8)
            for index, value in enumerate(vector):
                if value:
                    nonzero_slots.add(index)
        # Only the five cost-mapped slots (gold..cash) may ever be nonzero.
        self.assertEqual(nonzero_slots, {2, 3, 4, 5, 6})

    def test_known_item_vectors(self) -> None:
        house = item_by_id(1)
        self.assertEqual(house["name"], "House I")
        self.assertEqual(envelope_mod.cost_vector(house.get("costs")), [0, 0, 0, -30, 0, 0, 0, 0])
        command_center = item_by_id(26)
        self.assertEqual(command_center["name"], "Command Center")
        self.assertEqual(
            envelope_mod.cost_vector(command_center.get("costs")),
            [0, 0, -1000, 0, 0, 0, 0, 0],
        )

    def test_every_fresh_anchor_is_inside_the_grid(self) -> None:
        for slot, entry in FRESH_ITEMS.items():
            with self.subTest(slot=slot):
                self.assertTrue(envelope_mod.in_grid(entry[1], entry[2]))

    def test_a_fresh_footprint_crosses_the_edge_so_bounds_stay_anchor_only(self) -> None:
        """The evidence that corrected design D5: footprints already overflow."""
        crossing = []
        for slot, entry in FRESH_ITEMS.items():
            item = item_by_id(int(entry[0]))
            width = int(item.get("width") or 1)
            height = int(item.get("height") or 1)
            if entry[1] + width > envelope_mod.GRID_EXTENT or entry[2] + height > envelope_mod.GRID_EXTENT:
                crossing.append((slot, item["name"], entry[1], entry[2], width, height))
        self.assertEqual(
            [name for _, name, _, _, _, _ in crossing],
            ["Harbour"],
        )
        slot, _name, x, _y, width, _height = crossing[0]
        self.assertEqual(slot, "40")
        # Footprint columns x..x+width-1 = 99..108, past the 0..99 grid.
        self.assertEqual((x, width), (99, 10))


class SanitizationTests(unittest.TestCase):
    """Design D9: recorded requests carry no user_key or token values."""

    def test_form_user_key_is_always_redacted(self) -> None:
        form = {"USERID": "pid", "user_key": "S3CRET", "language": "en"}
        sanitized = capture.sanitize_form(form)
        self.assertEqual(sanitized["user_key"], capture.REDACTED)
        self.assertEqual(sanitized["USERID"], "pid")
        self.assertEqual(sanitized["language"], "en")
        self.assertNotIn("S3CRET", json.dumps(sanitized))

    def test_non_empty_access_token_is_redacted_in_the_data_field(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=1, x=51, y=39, costs='{"w":30}',
            items=FRESH_ITEMS, orientation=0, ts=1700000000,
        )
        built["accessToken"] = "TOKEN-SECRET"
        data = envelope_mod.data_field(built)
        record = capture.sanitize_data_field(data)
        self.assertNotIn("TOKEN-SECRET", record)
        parsed = envelope_mod.parse_data_field(record)
        self.assertEqual(parsed["accessToken"], capture.REDACTED)
        self.assertEqual(parsed["commands"], built["commands"])

    def test_crafted_empty_token_keeps_the_exact_sent_bytes(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=1, x=51, y=39, costs='{"w":30}',
            items=FRESH_ITEMS, orientation=0, ts=1700000000,
        )
        data = envelope_mod.data_field(built)
        self.assertEqual(capture.sanitize_data_field(data), data)

    def test_recorded_request_never_leaks_secrets(self) -> None:
        result = {
            "method": "POST",
            "target": "/dynamic/menvswomen/srvsexwars/command.php",
            "path": "/dynamic/menvswomen/srvsexwars/command.php",
            "query": {},
            "headers_sent": {
                "Host": "127.0.0.1:5055",
                "Cookie": "session=SESSION-TOKEN-SECRET",
            },
        }
        built = envelope_mod.build_envelope(
            item_id=1, x=51, y=39, costs='{"w":30}',
            items=FRESH_ITEMS, orientation=0, ts=1700000000,
        )
        built["accessToken"] = "TOKEN-SECRET"
        form = {
            "USERID": "00000000-0000-4000-8000-000000000001",
            "user_key": "FORM-SECRET",
            "language": "en",
            "data": envelope_mod.data_field(built),
        }
        record = capture.request_record(result, form, "test note")
        rendered = json.dumps(record)
        self.assertNotIn("FORM-SECRET", rendered)
        self.assertNotIn("TOKEN-SECRET", rendered)
        self.assertNotIn("SESSION-TOKEN-SECRET", rendered)
        self.assertEqual(record["form"]["user_key"], capture.REDACTED)
        self.assertEqual(record["headers_sent"]["Cookie"], capture.REDACTED)
        self.assertEqual(record["headers_sent"]["Host"], "127.0.0.1:5055")
        # The commands payload survives sanitization untouched.
        parsed = envelope_mod.parse_data_field(record["form"]["data"])
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
        self.assertEqual(sanitized["Content-Type"], headers["Content-Type"])
        self.assertNotIn("SESSION-TOKEN-SECRET", json.dumps(sanitized))


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_ITEM_ID, 1)
        self.assertEqual((capture.FIXTURE_ANCHOR_X, capture.FIXTURE_ANCHOR_Y), (51, 39))
        self.assertEqual(capture.FIXTURE_ORIENTATION, 0)
        self.assertIn("row-major", capture.ANCHOR_RULE)

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-placement",
        )

    def test_derived_fixture_envelope_pins_the_expected_values(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=capture.FIXTURE_ITEM_ID,
            x=capture.FIXTURE_ANCHOR_X,
            y=capture.FIXTURE_ANCHOR_Y,
            costs=item_by_id(1).get("costs"),
            items=FRESH_ITEMS,
            orientation=capture.FIXTURE_ORIENTATION,
            ts=1700000000,
        )
        self.assertEqual(built["commands"][0][2], [41, 1, 51, 39, 1, 0, 0, ""])
        self.assertEqual(built["commands"][0][3], [0, 0, 0, -30, 0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
