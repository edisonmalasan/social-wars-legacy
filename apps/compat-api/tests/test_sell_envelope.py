#!/usr/bin/env python3
"""Offline unit tests for the sell envelope derivation and the sell capture
tool's published contract (OpenSpec task 2.1 / task 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the fixture intent, the
derived empty reason (design D3), and the neutral price vector (design D2)
against the bytes the legacy server actually loads, and the shared-helper
round trip proves the sell envelope travels through the placement module's
unchanged serialization (design D7).
"""

from __future__ import annotations

import json
import time
import unittest

import compat_test_harness as harness

import capture_sell_fixture as capture
import sell_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]

# The reason the legacy branch would route a row through push_dead_unit.  It
# is the value the endpoint must never be able to produce (design D3).
COMBAT_REASON = "KILL"


def item_by_id(item_id: int) -> dict:
    for entry in CONFIG["items"]:
        if int(entry["id"]) == item_id:
            return entry
    raise AssertionError("config has no item id %d" % item_id)


class SharedHelperTests(unittest.TestCase):
    """Design D7: the shared helpers are reused, not re-implemented."""

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
        # The sell derivation is additive: placement keeps its own.
        self.assertFalse(hasattr(placement_envelope, "neutral_vector"))
        self.assertFalse(hasattr(placement_envelope, "SELL_COMMAND"))

    def test_the_command_and_derived_reason_are_the_documented_ones(self) -> None:
        # command.py:149-168: two positional args, the second only a log label
        # apart from the "KILL" comparison.
        self.assertEqual(envelope_mod.SELL_COMMAND, "sell")
        self.assertEqual(envelope_mod.DEFAULT_REASON, "")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.sell_envelope, envelope_mod)
        self.assertEqual(
            compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index"
        )
        self.assertEqual(
            compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index"
        )
        self.assertEqual(
            compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index"
        )
        self.assertEqual(compat_service.ERROR_INVALID_REASON, "invalid_reason")


class StrictIntTests(unittest.TestCase):
    def test_ints_but_not_bools_or_other_types(self) -> None:
        self.assertTrue(envelope_mod.is_strict_int(20))
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int("20"))
        self.assertFalse(envelope_mod.is_strict_int(20.0))
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
        built = envelope_mod.build_envelope(item_index=20, ts=1700000000)
        self.assertEqual(built["commands"][0][3], [0] * 8)


class DerivedReasonTests(unittest.TestCase):
    """Design D3: the reason is derived, never chosen."""

    def test_the_default_reason_is_the_empty_string(self) -> None:
        built = envelope_mod.build_envelope(item_index=20, ts=1700000000)
        self.assertEqual(built["commands"][0][2][1], "")

    def test_the_empty_reason_is_behaviourally_inert_in_legacy(self) -> None:
        """command.py:159 compares the reason against exactly "KILL"."""
        self.assertNotEqual(envelope_mod.DEFAULT_REASON, COMBAT_REASON)

    def test_the_derivation_can_never_produce_the_combat_reason(self) -> None:
        """No accepted input yields "KILL" without a deliberate override.

        The endpoint calls ``build_envelope(item_index=...)`` and never
        passes a reason, so ``push_dead_unit`` is unreachable through the
        contract (design D3 / the risk table).  This test documents that the
        only way to reach the combat reason is to call ``build_envelope``
        with an explicit non-empty reason, which the service never does.
        """
        for kwargs in ({}, {"ts": 0}, {"ts": 1700000000}):
            with self.subTest(kwargs=kwargs):
                built = envelope_mod.build_envelope(item_index=20, **kwargs)
                self.assertNotEqual(built["commands"][0][2][1], COMBAT_REASON)

    def test_a_non_string_reason_fails_closed(self) -> None:
        for bad in (0, None, ["KILL"], True, 1.0):
            with self.subTest(reason=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope(item_index=20, reason=bad)
                self.assertEqual(caught.exception.code, "invalid_reason")


class BuildEnvelopeTests(unittest.TestCase):
    def build(self, **overrides):
        arguments = {"item_index": 20, "ts": 1700000000}
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

    def test_single_sell_command(self) -> None:
        built = self.build()
        self.assertEqual(len(built["commands"]), 1)
        map_id, cmd, args, vector = built["commands"][0]
        self.assertEqual(map_id, 0)
        self.assertEqual(cmd, "sell")
        self.assertEqual(args, [20, ""])
        self.assertEqual(vector, [0] * 8)

    def test_the_argument_list_is_exactly_the_two_the_branch_reads(self) -> None:
        # command.py:150-151 binds args[0] and args[1] and nothing else.
        args = self.build()["commands"][0][2]
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0], 20)  # item_index
        self.assertEqual(args[1], "")  # derived reason, a log label only

    def test_the_reason_defaults_but_can_be_supplied(self) -> None:
        built = self.build(reason="BULLDOZE")
        self.assertEqual(built["commands"][0][2], [20, "BULLDOZE"])

    def test_any_integer_index_is_accepted(self) -> None:
        """Addressability is the endpoint's job, not the derivation's."""
        for index in (0, 1, 20, 41, 999999, -1):
            with self.subTest(item_index=index):
                built = envelope_mod.build_envelope(item_index=index, ts=1700000000)
                self.assertEqual(built["commands"][0][2][0], index)

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = self.build(ts=None)
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_structurally_invalid_input_fails_closed(self) -> None:
        cases = [
            ({"item_index": True}, "invalid_item_index"),
            ({"item_index": "20"}, "invalid_item_index"),
            ({"item_index": 20.0}, "invalid_item_index"),
            ({"item_index": None}, "invalid_item_index"),
            ({"reason": 0}, "invalid_reason"),
            ({"reason": None}, "invalid_reason"),
            ({"ts": -1}, "invalid_timestamp"),
            ({"ts": "1700000000"}, "invalid_timestamp"),
            ({"ts": True}, "invalid_timestamp"),
        ]
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(**overrides)
                self.assertEqual(caught.exception.code, code)

    def test_the_index_is_checked_before_the_reason(self) -> None:
        """An unresolvable index is the first thing reported."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(item_index="20", reason=0)
        self.assertEqual(caught.exception.code, "invalid_item_index")

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(item_index="20")
        message = str(caught.exception)
        self.assertIn("integer", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class SharedSerializationTests(unittest.TestCase):
    """The sell envelope travels through the unchanged shared helpers."""

    def built(self):
        return envelope_mod.build_envelope(item_index=20, ts=1700000000)

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

    def test_the_sell_payload_carries_exactly_one_command(self) -> None:
        data = envelope_mod.data_field(self.built())
        payload = json.loads(data[65:])
        self.assertEqual(
            payload["commands"],
            [[0, "sell", [20, ""], [0, 0, 0, 0, 0, 0, 0, 0]]],
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
        # The one price the config records for it buys the building; a sell
        # never carries that price (design D2), which is exactly why the
        # derived vector is neutral instead of "the item's price".
        self.assertEqual(turret["costs"], '{"s":125}')
        self.assertNotIn(-125, envelope_mod.neutral_vector())

    def test_the_committed_config_records_no_building_sale_refund_rule(self) -> None:
        """Design D2: nothing in the committed config prices a building sale.

        ``cost``/``cost_type`` are dead fields, ``costs`` prices the purchase
        only, and the only sell-named global (``MARKET_SELL_PERCENTAGE``)
        governs the *resource* market next to ``MARKET_BASE_COSTS`` and
        ``MARKET_AMOUNT_TRADE`` ("SELL 100 WOOD ON MARKET") — not building
        sales.  So the neutral vector is the only derivable choice, and this
        change claims no refund at all.
        """
        costs_keys = set()
        for entry in CONFIG["items"]:
            self.assertEqual(entry.get("cost"), "0")
            self.assertIsNone(entry.get("cost_type"))
            raw = entry.get("costs")
            if raw not in (None, ""):
                costs_keys |= set(json.loads(raw).keys())
        self.assertTrue(costs_keys <= {"g", "w", "o", "s", "c"})
        self.assertNotIn("sell", costs_keys)
        globals_keys = {str(key).lower() for key in CONFIG["globals"]}
        sell_globals = sorted(key for key in globals_keys if "sell" in key)
        self.assertEqual(sell_globals, ["market_sell_percentage"])
        market = CONFIG["globals"]["MARKET_SELL_PERCENTAGE"]
        self.assertEqual(market, 0.75)
        # Its siblings place it in the resource market, not a building sale.
        self.assertIn("MARKET_BASE_COSTS", CONFIG["globals"])
        self.assertIn("MARKET_AMOUNT_TRADE", CONFIG["globals"])
        self.assertFalse([key for key in globals_keys if "refund" in key])
        # The only "building" globals are the ally-building constant and the
        # build-speedup pair: none of them is a sale price.
        building_globals = sorted(key for key in globals_keys if "build" in key)
        self.assertEqual(
            building_globals,
            ["allies_building", "build_speedup_min_time", "build_speedup_pricing"],
        )

    def test_the_fresh_save_can_execute_the_fixture_sell(self) -> None:
        row = FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        self.assertEqual(len(FRESH_ITEMS), capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE)
        self.assertEqual(len(row), 8)
        self.assertEqual(int(row[0]), capture.FIXTURE_ITEM_ID)
        self.assertEqual([row[1], row[2]], [capture.FIXTURE_X, capture.FIXTURE_Y])

    def test_the_fixture_target_differs_from_the_move_fixture(self) -> None:
        """The two fixtures stay independently readable (design D10)."""
        turret_slots = sorted(
            int(key) for key, row in FRESH_ITEMS.items() if int(row[0]) == 22
        )
        self.assertEqual(turret_slots, [11, 20])
        self.assertEqual(
            FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)],
            [22, 41, 48, 0, 0, [], {}, 1],
        )
        self.assertNotEqual(
            FRESH_ITEMS["11"], FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        )

    def test_the_fixture_row_carries_no_unit_or_storage_payload(self) -> None:
        """A plain placed building: no stored unit list, no stored items."""
        row = FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        self.assertEqual(row[5], [])  # store (units inside the building)
        self.assertEqual(row[6], {})  # attr
        self.assertEqual(FRESH_MAP["store"], {})

    def test_the_neutral_vector_leaves_every_stored_resource_alone(self) -> None:
        vector = envelope_mod.neutral_vector()
        self.assertEqual(vector[1], 0)  # xp
        for index in (2, 3, 4, 5):  # gold, wood, oil, steel
            self.assertEqual(vector[index], 0)
        self.assertEqual(vector[6], 0)  # cash
        self.assertEqual(vector[7], 0)  # mana
        # A neutral vector means the clamp never changes a value.
        for value in (0, 4, 5, 2000):
            self.assertEqual(max(value + 0, 0), value)

    def test_the_fresh_save_starts_with_the_resources_the_fixture_keeps(self) -> None:
        self.assertEqual(FRESH_MAP["xp"], 4)
        for name in ("gold", "wood", "oil", "steel"):
            self.assertEqual(FRESH_MAP[name], 2000)
        self.assertEqual(SEED["playerInfo"]["cash"], 5)  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["mana"], 0)  # type: ignore[index]


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_ITEM_INDEX, 20)
        self.assertEqual(capture.FIXTURE_ITEM_ID, 22)
        self.assertEqual(capture.FIXTURE_ITEM_NAME, "Turret I")
        self.assertEqual((capture.FIXTURE_X, capture.FIXTURE_Y), (41, 48))
        self.assertEqual(capture.FIXTURE_REASON, "")
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_AFTER, 39)
        self.assertIn("second Turret I", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_sell"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-sell",
        )

    def test_derived_fixture_envelope_pins_the_expected_values(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        self.assertEqual(built["commands"][0][1], "sell")
        self.assertEqual(built["commands"][0][2], [20, ""])
        self.assertEqual(built["commands"][0][3], capture.FIXTURE_EXPECTED_VECTOR)
        capture.verify_envelope(built)

    def test_protected_fixtures_are_the_four_committed_ones(self) -> None:
        self.assertEqual(
            [relative for relative, _label in capture.PROTECTED_FIXTURES],
            [
                "tests/fixtures/godot-compatibility-boot",
                "tests/fixtures/godot-building-placement",
                "tests/fixtures/godot-item-purchase",
                "tests/fixtures/godot-building-move",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        # A drifting index must fail the run, not publish a new fixture.
        built["commands"][0][2] = [11, ""]
        with self.assertRaises(capture.CaptureError) as caught:
            capture.verify_envelope(built)
        self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_envelope_verification_rejects_a_client_chosen_combat_reason(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        built["commands"][0][2] = [20, "KILL"]
        with self.assertRaises(capture.CaptureError) as caught:
            capture.verify_envelope(built)
        self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        before = json.loads(json.dumps(SEED))
        after = json.loads(json.dumps(SEED))
        del after["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)]
        capture.verify_transaction(before, after, built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        cases = {
            "the row survived": lambda doc: doc["maps"][0]["items"].__setitem__(
                str(capture.FIXTURE_ITEM_INDEX), [22, 41, 48, 0, 0, [], {}, 1]
            ),
            "a second row was removed": lambda doc: doc["maps"][0]["items"].pop("10"),
            "another row changed": lambda doc: doc["maps"][0]["items"].__setitem__(
                "10", [23, 59, 48, 0, 0, [], {}, 1]
            ),
            "a resource changed": lambda doc: doc["maps"][0].__setitem__("gold", 0),
            "storage changed": lambda doc: doc["maps"][0].__setitem__("store", {"22": 1}),
            "boughtUnits changed": lambda doc: doc["privateState"].__setitem__(
                "boughtUnits", [22]
            ),
            "deadHeroes changed": lambda doc: doc["privateState"].__setitem__(
                "deadHeroes", {"22": True}
            ),
            "another privateState field changed": lambda doc: doc[
                "privateState"
            ].__setitem__("mana", 7),
            "the map timestamp changed": lambda doc: doc["maps"][0].__setitem__(
                "timestamp", 1234567890
            ),
        }
        for label, mutate in sorted(cases.items()):
            with self.subTest(case=label):
                before = json.loads(json.dumps(SEED))
                after = json.loads(json.dumps(SEED))
                del after["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)]
                mutate(after)
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


class SanitizationTests(unittest.TestCase):
    """Design D10: recorded requests carry no user_key or token values."""

    def test_form_user_key_is_always_redacted(self) -> None:
        form = {"USERID": "pid", "user_key": "S3CRET", "language": "en"}
        sanitized = capture.sanitize_form(form)
        self.assertEqual(sanitized["user_key"], capture.REDACTED)
        self.assertEqual(sanitized["USERID"], "pid")
        self.assertNotIn("S3CRET", json.dumps(sanitized))

    def test_crafted_empty_token_keeps_the_exact_sent_bytes(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        data = envelope_mod.data_field(built)
        self.assertEqual(capture.sanitize_data_field(data), data)

    def test_non_empty_access_token_is_redacted_in_the_data_field(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
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
