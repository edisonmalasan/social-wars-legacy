#!/usr/bin/env python3
"""Offline unit tests for the purchase envelope derivation and the purchase
capture tool's published contract (OpenSpec task 2.1 / task 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the closed cash-only
price rule (design D2) against the bytes the legacy server actually loads, and
the shared-helper round trip proves the purchase envelope travels through the
placement module's unchanged serialization (design D6).
"""

from __future__ import annotations

import json
import time
import unittest

import compat_test_harness as harness

import capture_purchase_fixture as capture
import purchase_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]


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
        self.assertEqual(envelope_mod.ENVELOPE_KEYS, placement_envelope.ENVELOPE_KEYS)
        self.assertEqual(envelope_mod.COST_SLOTS, placement_envelope.COST_SLOTS)
        # The purchase derivation is additive: placement keeps its own.
        self.assertFalse(hasattr(placement_envelope, "cash_cost_vector"))
        self.assertFalse(hasattr(placement_envelope, "PURCHASE_COMMAND"))

    def test_the_cash_slot_is_the_legacy_cash_slot(self) -> None:
        # [unknown, xp, gold, wood, oil, steel, cash, mana]
        self.assertEqual(envelope_mod.CASH_SLOT, 6)
        self.assertEqual(envelope_mod.CASH_COST_KEY, "c")
        self.assertEqual(envelope_mod.PURCHASE_COMMAND, "buy_stored_item_cash")


class StrictIntTests(unittest.TestCase):
    def test_ints_but_not_bools_or_other_types(self) -> None:
        self.assertTrue(envelope_mod.is_strict_int(105))
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int("105"))
        self.assertFalse(envelope_mod.is_strict_int(105.0))
        self.assertFalse(envelope_mod.is_strict_int(None))


class CashCostVectorTests(unittest.TestCase):
    """Design D2: exactly one cash component, every other slot zero."""

    def test_cash_only_string_price_negates_into_the_cash_slot(self) -> None:
        self.assertEqual(
            envelope_mod.cash_cost_vector('{"c":5}'), [0, 0, 0, 0, 0, 0, -5, 0]
        )
        self.assertEqual(
            envelope_mod.cash_cost_vector('{"c":1}'), [0, 0, 0, 0, 0, 0, -1, 0]
        )

    def test_string_and_dict_forms_are_equivalent(self) -> None:
        self.assertEqual(
            envelope_mod.cash_cost_vector('{"c":5}'),
            envelope_mod.cash_cost_vector({"c": 5}),
        )

    def test_zero_cash_price_is_a_zero_vector(self) -> None:
        self.assertEqual(envelope_mod.cash_cost_vector('{"c":0}'), [0] * 8)

    def test_absent_and_empty_prices_are_not_cash_prices(self) -> None:
        for costs in (None, ""):
            with self.subTest(costs=costs):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.cash_cost_vector(costs)
                self.assertEqual(caught.exception.code, "costs_not_cash")

    def test_empty_object_is_not_a_cash_price(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.cash_cost_vector("{}")
        self.assertEqual(caught.exception.code, "costs_not_cash")

    def test_other_only_and_mixed_prices_are_not_cash_prices(self) -> None:
        for costs in ('{"g":5}', '{"w":30}', '{"o":1}', '{"s":2}',
                      '{"c":5,"w":30}', '{"c":5,"g":1000}', '{"m":5}'):
            with self.subTest(costs=costs):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.cash_cost_vector(costs)
                self.assertEqual(caught.exception.code, "costs_not_cash")

    def test_unparseable_json_is_a_broken_config(self) -> None:
        for costs in ("{not json", "{", '{"c":5'):
            with self.subTest(costs=costs):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.cash_cost_vector(costs)
                self.assertEqual(caught.exception.code, "costs_invalid")

    def test_non_object_decoded_form_is_a_broken_config(self) -> None:
        for costs in ("[1,2]", "5", '"5"', "null", "true"):
            with self.subTest(costs=costs):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.cash_cost_vector(costs)
                self.assertEqual(caught.exception.code, "costs_invalid")

    def test_non_object_python_type_is_a_broken_config(self) -> None:
        for costs in ([1, 2], 5, 5.0, True, object()):
            with self.subTest(costs=type(costs).__name__):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.cash_cost_vector(costs)
                self.assertEqual(caught.exception.code, "costs_invalid")

    def test_non_integer_amounts_are_a_broken_config(self) -> None:
        for costs in ('{"c":"5"}', '{"c":true}', '{"c":5.0}', '{"c":null}',
                      '{"c":[5]}'):
            with self.subTest(costs=costs):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.cash_cost_vector(costs)
                self.assertEqual(caught.exception.code, "costs_invalid")

    def test_a_broken_amount_wins_over_the_key_check(self) -> None:
        """Documented precedence: unresolvable config before price shape."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.cash_cost_vector('{"g":"5"}')
        self.assertEqual(caught.exception.code, "costs_invalid")

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.cash_cost_vector('{"g":5}')
        message = str(caught.exception)
        self.assertIn("cash price", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class BuildEnvelopeTests(unittest.TestCase):
    def build(self, **overrides):
        arguments = {"item_id": 105, "costs": '{"c":5}', "ts": 1700000000}
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

    def test_single_purchase_command_carries_only_the_item_id(self) -> None:
        built = self.build()
        self.assertEqual(len(built["commands"]), 1)
        map_id, cmd, args, vector = built["commands"][0]
        self.assertEqual(map_id, 0)
        self.assertEqual(cmd, "buy_stored_item_cash")
        self.assertEqual(args, [105])
        self.assertEqual(vector, [0, 0, 0, 0, 0, 0, -5, 0])

    def test_the_item_id_is_the_only_positional_argument(self) -> None:
        # command.py:475-480 reads args[0] and nothing else.
        args = self.build(item_id=107, costs='{"c":7}')["commands"][0][2]
        self.assertEqual(args, [107])

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = self.build(ts=None)
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_structurally_invalid_input_fails_closed(self) -> None:
        cases = [
            ({"item_id": True}, "invalid_item_id"),
            ({"item_id": "105"}, "invalid_item_id"),
            ({"item_id": 105.0}, "invalid_item_id"),
            ({"costs": '{"w":30}'}, "costs_not_cash"),
            ({"costs": None}, "costs_not_cash"),
            ({"costs": "{oops"}, "costs_invalid"),
            ({"costs": '{"c":"5"}'}, "costs_invalid"),
            ({"ts": -1}, "invalid_timestamp"),
            ({"ts": "1700000000"}, "invalid_timestamp"),
            ({"ts": True}, "invalid_timestamp"),
        ]
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(**overrides)
                self.assertEqual(caught.exception.code, code)

    def test_item_id_is_checked_before_costs(self) -> None:
        """An unresolvable id is the client's error, whatever the price."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(item_id="105", costs="{oops")
        self.assertEqual(caught.exception.code, "invalid_item_id")


class SharedSerializationTests(unittest.TestCase):
    """The purchase envelope travels through the unchanged shared helpers."""

    def built(self):
        return envelope_mod.build_envelope(
            item_id=105, costs='{"c":5}', ts=1700000000
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

    def test_the_purchase_payload_carries_exactly_one_command(self) -> None:
        data = envelope_mod.data_field(self.built())
        payload = json.loads(data[65:])
        self.assertEqual(payload["commands"], [
            [0, "buy_stored_item_cash", [105], [0, 0, 0, 0, 0, 0, -5, 0]]
        ])

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

    def test_the_fixture_item_is_a_cash_priced_store_building(self) -> None:
        victory_arch = item_by_id(capture.FIXTURE_ITEM_ID)
        self.assertEqual(victory_arch["name"], capture.FIXTURE_ITEM_NAME)
        self.assertEqual(victory_arch["costs"], capture.FIXTURE_COSTS_RAW)
        self.assertEqual(int(victory_arch["in_store"]), 1)
        self.assertEqual(int(victory_arch["min_level"]), 1)
        self.assertEqual(victory_arch["type"], "b")

    def test_the_clamp_fixture_item_is_also_cash_priced(self) -> None:
        sculpture = item_by_id(107)
        self.assertEqual(sculpture["name"], "Sculpture")
        self.assertEqual(sculpture["costs"], '{"c":7}')
        self.assertEqual(
            envelope_mod.cash_cost_vector(sculpture.get("costs")),
            [0, 0, 0, 0, 0, 0, -7, 0],
        )

    def test_known_item_cash_vectors(self) -> None:
        self.assertEqual(
            envelope_mod.cash_cost_vector(item_by_id(105).get("costs")),
            [0, 0, 0, 0, 0, 0, -5, 0],
        )
        # House I is wood-priced: not derivable for a cash purchase.
        self.assertEqual(item_by_id(1).get("costs"), '{"w":30}')
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.cash_cost_vector(item_by_id(1).get("costs"))
        self.assertEqual(caught.exception.code, "costs_not_cash")

    def test_the_fresh_save_can_execute_the_fixture_purchase(self) -> None:
        price = 5
        self.assertEqual(FRESH_MAP["level"], 1)
        self.assertEqual(SEED["playerInfo"]["cash"], price)  # type: ignore[index]
        self.assertEqual(FRESH_MAP["store"], {})
        self.assertEqual(SEED["privateState"]["boughtUnits"], [])  # type: ignore[index]
        # Fully payable, so the recorded transaction is not a clamped one.
        self.assertGreaterEqual(SEED["playerInfo"]["cash"], price)  # type: ignore[index]
        # No other resource moves: the vector zeroes every other slot.
        self.assertEqual(envelope_mod.cash_cost_vector('{"c":5}')[6], -price)
        self.assertEqual(
            [value for index, value in enumerate(envelope_mod.cash_cost_vector('{"c":5}'))
             if index != 6],
            [0, 0, 0, 0, 0, 0, 0],
        )

    def test_no_config_item_price_is_a_mixed_or_unknown_resource(self) -> None:
        """The closed committed vocabulary: only g/w/o/s/c amounts, integers."""
        keys = set()
        for entry in CONFIG["items"]:
            raw = entry.get("costs")
            if raw is None or raw == "":
                continue
            parsed = json.loads(raw)
            self.assertIsInstance(parsed, dict)
            for key, amount in parsed.items():
                keys.add(str(key))
                self.assertIsInstance(amount, int)
                self.assertNotIsInstance(amount, bool)
        self.assertTrue(keys <= {"g", "w", "o", "s", "c"})


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_ITEM_ID, 105)
        self.assertEqual(capture.FIXTURE_ITEM_NAME, "Victory Arch")
        self.assertEqual(capture.FIXTURE_COSTS_RAW, '{"c":5}')
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0, 0, 0, 0, 0, 0, -5, 0])
        self.assertIn("min_level", capture.ITEM_SELECTION_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(
            capture.STEPS, ("login_post", "command_buy_stored_item_cash")
        )

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-item-purchase",
        )

    def test_derived_fixture_envelope_pins_the_expected_values(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=capture.FIXTURE_ITEM_ID,
            costs=item_by_id(capture.FIXTURE_ITEM_ID).get("costs"),
            ts=1700000000,
        )
        self.assertEqual(built["commands"][0][1], "buy_stored_item_cash")
        self.assertEqual(built["commands"][0][2], [105])
        self.assertEqual(built["commands"][0][3], capture.FIXTURE_EXPECTED_VECTOR)

    def test_protected_fixtures_are_the_committed_boot_and_placement_dirs(self) -> None:
        self.assertEqual(
            [relative for relative, _label in capture.PROTECTED_FIXTURES],
            [
                "tests/fixtures/godot-compatibility-boot",
                "tests/fixtures/godot-building-placement",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=capture.FIXTURE_ITEM_ID, costs=capture.FIXTURE_COSTS_RAW,
            ts=1700000000,
        )
        # A drifting config price must fail the run, not publish a new fixture.
        with self.assertRaises(capture.CaptureError) as caught:
            capture.verify_envelope(built, '{"c":9}')
        self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=capture.FIXTURE_ITEM_ID, costs=capture.FIXTURE_COSTS_RAW,
            ts=1700000000,
        )
        before = json.loads(json.dumps(SEED))
        after = json.loads(json.dumps(SEED))
        # A storage purchase must not have placed anything.
        after["maps"][0]["items"]["41"] = [105, 51, 39, 0, 0, [], {"nc": 0}, 1]
        with self.assertRaises(capture.CaptureError) as caught:
            capture.verify_transaction(before, after, built)
        self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=capture.FIXTURE_ITEM_ID, costs=capture.FIXTURE_COSTS_RAW,
            ts=1700000000,
        )
        before = json.loads(json.dumps(SEED))
        after = json.loads(json.dumps(SEED))
        after["playerInfo"]["cash"] = 0
        after["maps"][0]["store"] = {"105": 1}
        after["privateState"]["boughtUnits"] = [105]
        capture.verify_transaction(before, after, built)


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
            item_id=capture.FIXTURE_ITEM_ID, costs=capture.FIXTURE_COSTS_RAW,
            ts=1700000000,
        )
        data = envelope_mod.data_field(built)
        self.assertEqual(capture.sanitize_data_field(data), data)

    def test_non_empty_access_token_is_redacted_in_the_data_field(self) -> None:
        built = envelope_mod.build_envelope(
            item_id=capture.FIXTURE_ITEM_ID, costs=capture.FIXTURE_COSTS_RAW,
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
