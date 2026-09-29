#!/usr/bin/env python3
"""Offline unit tests for the store envelope derivation and the store capture
tool's published contract (OpenSpec task 2.1 / task 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the fixture intent, the
single-argument shape, the deliberately-unwritten ``boughtUnits`` bookkeeping,
the neutral resource vector, and the absence of any storing price or capacity
rule against the bytes the legacy server actually loads, and the shared-helper
round trip proves the store envelope travels through the placement module's
unchanged serialization (design D6).
"""

from __future__ import annotations

import json
import time
import unittest

import compat_test_harness as harness

import capture_store_fixture as capture
import store_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]

# The fresh-player corpus slots the already committed fixtures address, so the
# store fixture's slot stays independently readable (design D10).
MOVE_FIXTURE_INDEX = 11
SELL_FIXTURE_INDEX = 20


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
        # The store derivation is additive: placement keeps its own.
        self.assertFalse(hasattr(placement_envelope, "neutral_vector"))
        self.assertFalse(hasattr(placement_envelope, "STORE_COMMAND"))

    def test_every_sibling_module_keeps_its_own_derivation(self) -> None:
        """No delivered envelope module was refactored (design D6)."""
        import move_envelope
        import placement_envelope
        import purchase_envelope
        import sell_envelope

        self.assertIsNot(envelope_mod.neutral_vector, sell_envelope.neutral_vector)
        self.assertIsNot(envelope_mod.neutral_vector, move_envelope.neutral_vector)
        self.assertIsNot(envelope_mod.build_envelope, sell_envelope.build_envelope)
        self.assertIsNot(envelope_mod.build_envelope, move_envelope.build_envelope)
        self.assertFalse(hasattr(placement_envelope, "STORE_COMMAND"))
        self.assertFalse(hasattr(sell_envelope, "STORE_COMMAND"))
        self.assertFalse(hasattr(purchase_envelope, "STORE_COMMAND"))
        self.assertFalse(hasattr(move_envelope, "STORE_COMMAND"))

    def test_the_command_and_the_vector_width_are_the_documented_ones(self) -> None:
        # command.py:218-232 binds exactly args[0]; engine.apply_resources
        # (engine.py:251-271) reads exactly eight slots.
        self.assertEqual(envelope_mod.STORE_COMMAND, "store_item")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.store_envelope, envelope_mod)
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
        self.assertTrue(envelope_mod.is_strict_int(2))
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int("2"))
        self.assertFalse(envelope_mod.is_strict_int(2.0))
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
        built = envelope_mod.build_envelope(item_index=2, ts=1700000000)
        self.assertEqual(built["commands"][0][3], [0] * 8)

    def test_mutating_one_envelope_never_changes_the_next(self) -> None:
        first = envelope_mod.build_envelope(item_index=2, ts=1700000000)
        first["commands"][0][3][6] = 500
        second = envelope_mod.build_envelope(item_index=3, ts=1700000000)
        self.assertEqual(second["commands"][0][3], [0] * 8)


class BuildEnvelopeTests(unittest.TestCase):
    def build(self, **overrides):
        arguments = {"item_index": 2, "ts": 1700000000}
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

    def test_single_store_item_command(self) -> None:
        built = self.build()
        self.assertEqual(len(built["commands"]), 1)
        map_id, cmd, args, vector = built["commands"][0]
        self.assertEqual(map_id, 0)
        self.assertEqual(cmd, "store_item")
        self.assertEqual(args, [2])
        self.assertEqual(vector, [0] * 8)

    def test_the_argument_list_is_exactly_the_one_the_branch_reads(self) -> None:
        # command.py:219 binds args[0] and nothing else; the branch reads no
        # reason, no quantity, and no coordinates.
        args = self.build()["commands"][0][2]
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0], 2)

    def test_there_is_no_quantity_argument_to_supply(self) -> None:
        """Legacy calls add_store_item(map, item_id): quantity is always 1."""
        signature = envelope_mod.build_envelope.__code__.co_varnames[
            : envelope_mod.build_envelope.__code__.co_argcount
        ]
        self.assertEqual(signature, ("item_index", "ts"))
        args = self.build()["commands"][0][2]
        self.assertNotIn(1, args)
        self.assertEqual(len(args), 1)

    def test_any_integer_index_is_accepted(self) -> None:
        """Addressability is the endpoint's job, not the derivation's."""
        for index in (0, 1, 2, 20, 41, 999999, -1):
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
            ({"item_index": "2"}, "invalid_item_index"),
            ({"item_index": 2.0}, "invalid_item_index"),
            ({"item_index": None}, "invalid_item_index"),
            ({"item_index": [2]}, "invalid_item_index"),
            ({"ts": -1}, "invalid_timestamp"),
            ({"ts": "1700000000"}, "invalid_timestamp"),
            ({"ts": True}, "invalid_timestamp"),
        ]
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(**overrides)
                self.assertEqual(caught.exception.code, code)

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(item_index="2")
        message = str(caught.exception)
        self.assertIn("integer", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class SharedSerializationTests(unittest.TestCase):
    """The store envelope travels through the unchanged shared helpers."""

    def built(self):
        return envelope_mod.build_envelope(item_index=2, ts=1700000000)

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

    def test_the_store_payload_carries_exactly_one_command(self) -> None:
        data = envelope_mod.data_field(self.built())
        payload = json.loads(data[65:])
        self.assertEqual(
            payload["commands"],
            [[0, "store_item", [2], [0, 0, 0, 0, 0, 0, 0, 0]]],
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

    def test_the_fixture_item_is_a_one_by_one_map_decoration(self) -> None:
        """A placed decoration, not a shop item: `in_store` 0."""
        tree = item_by_id(capture.FIXTURE_ITEM_ID)
        self.assertEqual(tree["name"], capture.FIXTURE_ITEM_NAME)
        self.assertEqual(tree["type"], "b")
        self.assertEqual(int(tree["width"]), 1)
        self.assertEqual(int(tree["height"]), 1)
        self.assertEqual(tree["in_store"], "0")
        # The one price the config records for it buys the building; a store
        # never carries that price (design D2), which is exactly why the
        # derived vector is neutral instead of "the item's price".
        self.assertEqual(tree["costs"], '{"w":30}')
        self.assertNotIn(-30, envelope_mod.neutral_vector())

    def test_the_committed_config_records_no_storing_price(self) -> None:
        """Design D2: nothing in the committed config prices a store.

        ``cost``/``cost_type`` are dead fields and ``costs`` prices the
        purchase only, so the neutral vector is the only derivable choice and
        this change claims no storing cost at all.
        """
        costs_keys = set()
        for entry in CONFIG["items"]:
            self.assertEqual(entry.get("cost"), "0")
            self.assertIsNone(entry.get("cost_type"))
            raw = entry.get("costs")
            if raw not in (None, ""):
                costs_keys |= set(json.loads(raw).keys())
        self.assertTrue(costs_keys <= {"g", "w", "o", "s", "c"})
        self.assertNotIn("store", costs_keys)
        self.assertNotIn("sell", costs_keys)

    def test_the_committed_config_records_no_storage_capacity_rule(self) -> None:
        """The catalog says legacy has no capacity check; nothing adds one.

        No global mentions a capacity, the only "store" global is the news
        store (a web-store link, not a storage limit), and every "limit"
        global governs resources, towers, silos, walls, depots, or selected
        objects — none of them storage.  So **no capacity rule is claimed**.
        """
        globals_keys = {str(key).lower() for key in CONFIG["globals"]}
        self.assertEqual(sorted(k for k in globals_keys if "capac" in k), [])
        self.assertEqual(sorted(k for k in globals_keys if "store" in k), ["news_store"])
        limit_globals = sorted(k for k in globals_keys if k.startswith("limit_") or "limit" in k)
        for name in limit_globals:
            with self.subTest(limit_global=name):
                self.assertNotIn("store", name)
                self.assertNotIn("storage", name)

    def test_the_fresh_save_can_execute_the_fixture_store(self) -> None:
        row = FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        self.assertEqual(len(FRESH_ITEMS), capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE)
        self.assertEqual(len(row), 8)
        self.assertEqual(int(row[0]), capture.FIXTURE_ITEM_ID)
        self.assertEqual([row[1], row[2]], [capture.FIXTURE_X, capture.FIXTURE_Y])
        # The storage starts empty, so the increment is directly observable.
        self.assertEqual(FRESH_MAP["store"], capture.FIXTURE_EXPECTED_STORE_BEFORE)
        self.assertEqual(
            SEED["privateState"]["boughtUnits"], []  # type: ignore[index]
        )

    def test_the_fixture_target_differs_from_the_move_and_sell_fixtures(self) -> None:
        """All three fixtures stay independently readable (design D10)."""
        self.assertEqual(FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)], [905, 53, 39, 0, 0, [], {}, 1])
        self.assertEqual(FRESH_ITEMS[str(MOVE_FIXTURE_INDEX)], [22, 58, 48, 0, 0, [], {}, 1])
        self.assertEqual(FRESH_ITEMS[str(SELL_FIXTURE_INDEX)], [22, 41, 48, 0, 0, [], {}, 1])
        self.assertEqual(
            capture.FIXTURE_ITEM_INDEX,
            2,
        )
        for other in (MOVE_FIXTURE_INDEX, SELL_FIXTURE_INDEX):
            self.assertNotEqual(capture.FIXTURE_ITEM_INDEX, other)

    def test_only_one_row_holds_the_tree_decoration(self) -> None:
        """Storing slot 2 cannot disturb the move or sell fixture rows."""
        tree_slots = sorted(
            int(key) for key, row in FRESH_ITEMS.items() if int(row[0]) == 905
        )
        self.assertEqual(tree_slots, [2])

    def test_the_fixture_row_carries_no_unit_or_storage_payload(self) -> None:
        """A plain placed decoration: no stored unit list, no stored items."""
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
        self.assertEqual(capture.FIXTURE_ITEM_INDEX, 2)
        self.assertEqual(capture.FIXTURE_ITEM_ID, 905)
        self.assertEqual(capture.FIXTURE_ITEM_NAME, "Tree")
        self.assertEqual((capture.FIXTURE_X, capture.FIXTURE_Y), (53, 39))
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_AFTER, 39)
        self.assertEqual(capture.FIXTURE_EXPECTED_STORE_BEFORE, {})
        self.assertEqual(capture.FIXTURE_EXPECTED_STORE_AFTER, {"905": 1})
        self.assertIn("Tree decoration", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_store_item"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-store",
        )

    def test_derived_fixture_envelope_pins_the_expected_values(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        self.assertEqual(built["commands"][0][1], "store_item")
        self.assertEqual(built["commands"][0][2], [2])
        self.assertEqual(built["commands"][0][3], capture.FIXTURE_EXPECTED_VECTOR)
        capture.verify_envelope(built)

    def test_protected_fixtures_are_the_five_committed_ones(self) -> None:
        self.assertEqual(
            [relative for relative, _label in capture.PROTECTED_FIXTURES],
            [
                "tests/fixtures/godot-compatibility-boot",
                "tests/fixtures/godot-building-placement",
                "tests/fixtures/godot-item-purchase",
                "tests/fixtures/godot-building-move",
                "tests/fixtures/godot-building-sell",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        for mutate in (
            lambda entry: entry.__setitem__("commands", [entry["commands"][0], entry["commands"][0]]),
            lambda entry: entry["commands"][0].__setitem__(0, 1),
            lambda entry: entry["commands"][0].__setitem__(1, "sell"),
            lambda entry: entry["commands"][0].__setitem__(2, [11]),
            lambda entry: entry["commands"][0].__setitem__(2, [2, 1]),
            lambda entry: entry["commands"][0].__setitem__(3, [0, 0, 0, 0, 0, 0, 30, 0]),
        ):
            with self.subTest(mutate=mutate):
                candidate = envelope_mod.build_envelope(
                    item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
                )
                mutate(candidate)
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_envelope(candidate)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_envelope_verification_rejects_a_missing_envelope_key(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        del built["tries"]
        with self.assertRaises(capture.CaptureError) as caught:
            capture.verify_envelope(built)
        self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def stored_after(self):
        """The after-state the executed transaction must produce."""
        after = json.loads(json.dumps(SEED))
        del after["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)]
        after["maps"][0]["store"] = dict(capture.FIXTURE_EXPECTED_STORE_AFTER)
        return after

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        capture.verify_transaction(json.loads(json.dumps(SEED)), self.stored_after(), built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        items = lambda doc: doc["maps"][0]["items"]  # noqa: E731
        cases = {
            "the row survived": lambda doc: items(doc).__setitem__(
                str(capture.FIXTURE_ITEM_INDEX), [905, 53, 39, 0, 0, [], {}, 1]
            ),
            "a second row was removed": lambda doc: items(doc).pop("10"),
            "another row changed": lambda doc: items(doc).__setitem__(
                "10", [23, 59, 48, 0, 0, [], {}, 1]
            ),
            "the storage entry never landed": lambda doc: doc["maps"][0].__setitem__(
                "store", {}
            ),
            "the storage quantity drifted": lambda doc: doc["maps"][0].__setitem__(
                "store", {"905": 2}
            ),
            "another storage entry appeared": lambda doc: doc["maps"][0].__setitem__(
                "store", {"905": 1, "22": 1}
            ),
            "boughtUnits changed": lambda doc: doc["privateState"].__setitem__(
                "boughtUnits", [905]
            ),
            "deadHeroes changed": lambda doc: doc["privateState"].__setitem__(
                "deadHeroes", {"22": True}
            ),
            "another privateState field changed": lambda doc: doc[
                "privateState"
            ].__setitem__("mana", 7),
            "playerInfo changed": lambda doc: doc["playerInfo"].__setitem__("cash", 6),
            "a resource changed": lambda doc: doc["maps"][0].__setitem__("gold", 0),
            "the map timestamp changed": lambda doc: doc["maps"][0].__setitem__(
                "timestamp", 1234567890
            ),
        }
        for label, mutate in sorted(cases.items()):
            with self.subTest(case=label):
                after = self.stored_after()
                mutate(after)
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(json.loads(json.dumps(SEED)), after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_transaction_verification_rejects_a_multi_argument_envelope(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, ts=1700000000
        )
        built["commands"][0][2] = [2, 5]
        with self.assertRaises(capture.CaptureError) as caught:
            capture.verify_transaction(
                json.loads(json.dumps(SEED)), self.stored_after(), built
            )
        self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


class SanitizationTests(unittest.TestCase):
    """Recorded requests carry no user_key or token values."""

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
