#!/usr/bin/env python3
"""Offline unit tests for the upgrade envelope derivation and the upgrade
capture tool's published contract (OpenSpec task 2.1 / task 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the fixture intent, the
committed ``UPGR`` reason, the Wall I -> Wall II tier reference, and the
neutral price vectors against the bytes the legacy server actually loads, and
the shared-helper round trip proves the two-command envelope travels through
the placement module's unchanged serialization (design D8).

The **order** of the two commands is asserted directly and repeatedly: it is
the one part of this contract that is not a style choice, because the reverse
order destroys the building while legacy still reports success.
"""

from __future__ import annotations

import json
import time
import unittest
from typing import Dict, Optional

import compat_test_harness as harness

import capture_upgrade_fixture as capture
import upgrade_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]

# The reason that would route a row through push_dead_unit.  The committed
# upgrade reason is derived server-side, so this value must never be reachable
# through the endpoint (design D2/D3).
COMBAT_REASON = "KILL"

# The committed legacy constant (constants.py:970).
LEGACY_SELL_REASON_UPGRADE = "UPGR"


def item_by_id(item_id: int) -> dict:
    for entry in CONFIG["items"]:
        if int(entry["id"]) == item_id:
            return entry
    raise AssertionError("config has no item id %d" % item_id)


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
        # The upgrade derivation is additive: placement and its siblings keep
        # their own.
        self.assertFalse(hasattr(placement_envelope, "neutral_vector"))
        self.assertFalse(hasattr(placement_envelope, "UPGRADE_REASON"))

    def test_the_two_commands_and_the_reason_are_the_documented_ones(self) -> None:
        # command.py:149-168 (sell) and command.py:42-58 (buy), plus the
        # committed upgrade reason at constants.py:970.
        self.assertEqual(envelope_mod.SELL_COMMAND, "sell")
        self.assertEqual(envelope_mod.BUY_COMMAND, "buy")
        self.assertEqual(envelope_mod.UPGRADE_REASON, LEGACY_SELL_REASON_UPGRADE)
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)
        self.assertEqual(envelope_mod.DEFAULT_UNKNOWN, 0)
        self.assertEqual(envelope_mod.BUY_REASON, "")

    def test_the_committed_reason_is_not_the_combat_reason(self) -> None:
        """``command.py:159`` compares the reason against exactly "KILL"."""
        self.assertNotEqual(envelope_mod.UPGRADE_REASON, COMBAT_REASON)

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.upgrade_envelope, envelope_mod)
        self.assertEqual(
            compat_service.ERROR_NO_UPGRADE_PATH, "no_upgrade_path"
        )
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
        self.assertTrue(envelope_mod.is_strict_int(12))
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int("12"))
        self.assertFalse(envelope_mod.is_strict_int(12.0))
        self.assertFalse(envelope_mod.is_strict_int(None))


class NeutralVectorTests(unittest.TestCase):
    """Design D4: the derived vector is all zeros on BOTH commands."""

    def test_the_vector_is_eight_zeros(self) -> None:
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.neutral_vector()
        first[6] = -999
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_both_commands_carry_their_own_neutral_vector(self) -> None:
        built = self_built()
        self.assertEqual(len(built["commands"]), 2)
        self.assertEqual(built["commands"][0][3], [0] * 8)
        self.assertEqual(built["commands"][1][3], [0] * 8)
        # Independent lists: mutating one must not touch the other.
        self.assertIsNot(built["commands"][0][3], built["commands"][1][3])

    def test_the_vector_leaves_every_stored_resource_alone(self) -> None:
        vector = envelope_mod.neutral_vector()
        self.assertEqual(vector[1], 0)  # xp
        for index in (2, 3, 4, 5):  # gold, wood, oil, steel
            self.assertEqual(vector[index], 0)
        self.assertEqual(vector[6], 0)  # cash
        self.assertEqual(vector[7], 0)  # mana
        for value in (0, 4, 5, 2000):
            self.assertEqual(max(value + 0, 0), value)


def self_built(**overrides):
    """A built envelope with the fixture's own values, ts pinned."""
    arguments = {
        "item_index": capture.FIXTURE_ITEM_INDEX,
        "target_item_id": capture.FIXTURE_TARGET_ITEM_ID,
        "x": capture.FIXTURE_X,
        "y": capture.FIXTURE_Y,
        "player": 1,
        "orientation": 0,
        "ts": 1700000000,
    }
    arguments.update(overrides)
    return envelope_mod.build_envelope(**arguments)


class UpgradeReasonTests(unittest.TestCase):
    """Design D2: the reason is the committed constant, derived server-side."""

    def test_the_default_reason_is_the_committed_upgrade_constant(self) -> None:
        built = self_built()
        self.assertEqual(built["commands"][0][2][1], LEGACY_SELL_REASON_UPGRADE)

    def test_the_derivation_never_produces_the_combat_reason(self) -> None:
        """No accepted input reaches "KILL" without a deliberate override.

        The endpoint never passes a reason, so ``push_dead_unit`` is
        unreachable through the contract (design D2/D3).
        """
        for kwargs in ({}, {"ts": 0}, {"ts": 1700000000}):
            with self.subTest(kwargs=kwargs):
                built = envelope_mod.build_envelope(
                    item_index=12,
                    target_item_id=24,
                    x=45,
                    y=49,
                    player=1,
                    orientation=0,
                    **kwargs,
                )
                self.assertNotEqual(built["commands"][0][2][1], COMBAT_REASON)

    def test_a_non_string_reason_fails_closed(self) -> None:
        for bad in (0, None, ["UPGR"], True, 1.0):
            with self.subTest(reason=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self_built(reason=bad)
                self.assertEqual(caught.exception.code, "invalid_reason")

    def test_a_non_string_buy_reason_fails_closed(self) -> None:
        for bad in (0, None, ["x"], True, 1.0):
            with self.subTest(buy_reason=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self_built(buy_reason=bad)
                self.assertEqual(caught.exception.code, "invalid_buy_reason")


class BuildEnvelopeTests(unittest.TestCase):
    def test_envelope_has_exactly_the_six_legacy_keys(self) -> None:
        built = self_built()
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        self.assertEqual(built["first_number"], 0)
        self.assertEqual(built["publishActions"], [])
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(built["tries"], 1)
        self.assertEqual(built["accessToken"], "")

    def test_the_batch_carries_exactly_two_commands_in_the_forced_order(self) -> None:
        """Design D1: sell first, then buy.  The reverse destroys the row."""
        built = self_built()
        commands = built["commands"]
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][1], "sell")
        self.assertEqual(commands[1][1], "buy")
        # Both on map 0 (the SW always sends map 0; the corpus has one map).
        self.assertEqual(commands[0][0], 0)
        self.assertEqual(commands[1][0], 0)

    def test_the_sell_argument_list_is_exactly_the_two_the_branch_reads(self) -> None:
        # command.py:150-151 binds args[0] and args[1] and nothing else.
        args = self_built()["commands"][0][2]
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0], capture.FIXTURE_ITEM_INDEX)  # item_index
        self.assertEqual(args[1], LEGACY_SELL_REASON_UPGRADE)  # committed reason

    def test_the_buy_argument_list_is_exactly_the_eight_the_branch_reads(self) -> None:
        # command.py:43-50 binds eight positional args and reads six of them.
        args = self_built()["commands"][1][2]
        self.assertEqual(len(args), 8)
        self.assertEqual(
            args,
            [
                capture.FIXTURE_ITEM_INDEX,
                capture.FIXTURE_TARGET_ITEM_ID,
                capture.FIXTURE_X,
                capture.FIXTURE_Y,
                1,  # playerID, the row's own team
                0,  # orientation, the row's own
                0,  # unknown, documented placeholder
                "",  # reason, documented placeholder legacy discards
            ],
        )

    def test_the_buy_half_reuses_the_sales_key(self) -> None:
        """How the pair replaces the row instead of re-keying the map."""
        built = self_built()
        self.assertEqual(
            built["commands"][0][2][0],
            built["commands"][1][2][0],
        )

    def test_the_reason_defaults_but_can_be_supplied(self) -> None:
        built = self_built(reason="BLDZE")
        self.assertEqual(built["commands"][0][2], [12, "BLDZE"])

    def test_any_integer_index_target_and_player_are_accepted(self) -> None:
        """Addressability and the tier are the endpoint's job, not the
        derivation's (design D7)."""
        for index, target, player in ((0, 24, 1), (41, 905, 0), (999999, 1, 1)):
            with self.subTest(item_index=index, player=player):
                built = envelope_mod.build_envelope(
                    item_index=index,
                    target_item_id=target,
                    x=0,
                    y=0,
                    player=player,
                    orientation=0,
                    ts=1700000000,
                )
                self.assertEqual(built["commands"][0][2][0], index)
                self.assertEqual(built["commands"][1][2][0], index)
                self.assertEqual(built["commands"][1][2][1], target)
                self.assertEqual(built["commands"][1][2][4], player)

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = self_built(ts=None)
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_structurally_invalid_input_fails_closed(self) -> None:
        cases = [
            ({"item_index": True}, "invalid_item_index"),
            ({"item_index": "12"}, "invalid_item_index"),
            ({"item_index": 12.0}, "invalid_item_index"),
            ({"item_index": None}, "invalid_item_index"),
            ({"target_item_id": "24"}, "invalid_target_item_id"),
            ({"target_item_id": 24.0}, "invalid_target_item_id"),
            ({"target_item_id": True}, "invalid_target_item_id"),
            ({"target_item_id": None}, "invalid_target_item_id"),
            ({"x": "45"}, "invalid_coordinates"),
            ({"y": None}, "invalid_coordinates"),
            ({"x": -1}, "invalid_coordinates"),
            ({"x": 100}, "invalid_coordinates"),
            ({"y": 100}, "invalid_coordinates"),
            ({"player": "1"}, "invalid_player"),
            ({"player": True}, "invalid_player"),
            ({"player": None}, "invalid_player"),
            ({"orientation": "0"}, "invalid_orientation"),
            ({"orientation": 0.0}, "invalid_orientation"),
            ({"reason": 0}, "invalid_reason"),
            ({"unknown": "0"}, "invalid_unknown"),
            ({"unknown": True}, "invalid_unknown"),
            ({"buy_reason": 0}, "invalid_buy_reason"),
            ({"ts": -1}, "invalid_timestamp"),
            ({"ts": "1700000000"}, "invalid_timestamp"),
            ({"ts": True}, "invalid_timestamp"),
        ]
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self_built(**overrides)
                self.assertEqual(caught.exception.code, code)

    def test_the_validation_order_is_index_then_target_then_cell(self) -> None:
        """The unresolvable value closest to the contract is reported first."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self_built(item_index="12", target_item_id="24")
        self.assertEqual(caught.exception.code, "invalid_item_index")
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self_built(target_item_id="24", x="45")
        self.assertEqual(caught.exception.code, "invalid_target_item_id")
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self_built(x="45", player="1")
        self.assertEqual(caught.exception.code, "invalid_coordinates")

    def test_both_coordinate_bound_edges_are_accepted(self) -> None:
        """0 and GRID_EXTENT-1 are inside; the anchor rule is unchanged."""
        for x, y in ((0, 0), (0, 99), (99, 0), (99, 99)):
            with self.subTest(x=x, y=y):
                built = self_built(x=x, y=y)
                self.assertEqual(
                    [built["commands"][1][2][2], built["commands"][1][2][3]], [x, y]
                )
        for x, y in ((-1, 0), (0, -1), (100, 0), (0, 100)):
            with self.subTest(x=x, y=y):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self_built(x=x, y=y)
                self.assertEqual(caught.exception.code, "invalid_coordinates")

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self_built(item_index="12")
        message = str(caught.exception)
        self.assertIn("integer", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class SharedSerializationTests(unittest.TestCase):
    """The two-command envelope travels through the unchanged shared helpers."""

    def test_roundtrip_through_the_legacy_field_format(self) -> None:
        built = self_built()
        data = envelope_mod.data_field(built)
        self.assertEqual(len(data.split(";", 1)[0]), 64)
        self.assertEqual(data[64], ";")
        self.assertEqual(envelope_mod.parse_data_field(data), built)

    def test_serialization_is_deterministic(self) -> None:
        built = self_built()
        first = envelope_mod.payload_json(built)
        second = envelope_mod.payload_json(built)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith('{"accessToken":"","commands":['))

    def test_the_payload_carries_exactly_the_two_established_commands(self) -> None:
        """The contract verified against the real legacy server, verbatim."""
        payload = json.loads(envelope_mod.data_field(self_built())[65:])
        self.assertEqual(
            payload["commands"],
            [
                [0, "sell", [12, "UPGR"], [0, 0, 0, 0, 0, 0, 0, 0]],
                [0, "buy", [12, 24, 45, 49, 1, 0, 0, ""], [0, 0, 0, 0, 0, 0, 0, 0]],
            ],
        )
        self.assertEqual(payload["first_number"], 0)
        self.assertEqual(payload["publishActions"], [])
        self.assertEqual(payload["tries"], 1)
        self.assertEqual(payload["accessToken"], "")

    def test_malformed_fields_fail_closed(self) -> None:
        good = envelope_mod.data_field(self_built())
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

    def test_the_fixture_pair_is_the_one_the_committed_config_names(self) -> None:
        wall_one = item_by_id(capture.FIXTURE_ITEM_ID)
        wall_two = item_by_id(capture.FIXTURE_TARGET_ITEM_ID)
        self.assertEqual(wall_one["name"], capture.FIXTURE_ITEM_NAME)
        self.assertEqual(wall_two["name"], capture.FIXTURE_TARGET_ITEM_NAME)
        self.assertEqual(wall_one["type"], "b")
        self.assertEqual(int(wall_one["width"]), 1)
        self.assertEqual(int(wall_one["height"]), 1)
        # The next tier is the item's OWN config reference, resolved with the
        # documented -1/0-and-unresolvable-means-none rule.
        self.assertEqual(int(wall_one["upgrades_to"]), capture.FIXTURE_TARGET_ITEM_ID)
        self.assertEqual(capture.config_upgrade_reference(capture.FIXTURE_ITEM_ID),
                         capture.FIXTURE_TARGET_ITEM_ID)
        # The target has clicks_to_build > 0, which is why the fresh row
        # carries attr {"nc": 0} (engine.py:25-29).
        self.assertGreater(int(wall_two["clicks_to_build"]), 0)

    def test_the_committed_config_records_no_upgrade_price(self) -> None:
        """Design D4: nothing in the committed config prices a normal upgrade.

        ``cost``/``cost_type`` are dead fields and ``costs`` prices the purchase
        only, so the neutral vector is the only derivable choice and this
        change claims no upgrade cost.  The one upgrade-priced field in the
        committed config is ``premium_upgrade_costs``, a **separate** premium
        path (139 items carry a non-empty value, mostly unique decorations);
        it is not consulted by this contract at all, and neither tier of the
        fixture even carries one.
        """
        costs_keys = set()
        premium_populated = 0
        for entry in CONFIG["items"]:
            self.assertEqual(entry.get("cost"), "0")
            self.assertIsNone(entry.get("cost_type"))
            raw = entry.get("costs")
            if raw not in (None, ""):
                costs_keys |= set(json.loads(raw).keys())
            if entry.get("premium_upgrade_costs") not in (None, "", "[]", "{}"):
                premium_populated += 1
        self.assertTrue(costs_keys <= {"g", "w", "o", "s", "c"})
        self.assertNotIn("upgrade", costs_keys)
        # The premium upgrade price class exists but is a distinct path: the
        # only upgrade-named global is the speed-up pricing constant the Flash
        # client's "Upgrade instantly for" copy matches, not a tier price.
        self.assertEqual(premium_populated, 139)
        upgrade_globals = sorted(k for k in CONFIG["globals"] if "UPGRAD" in k.upper())
        self.assertEqual(upgrade_globals, ["UPGRADE_SPEEDUP_PRICING"])
        self.assertEqual(CONFIG["globals"]["UPGRADE_SPEEDUP_PRICING"], [5, 1])
        # Neither tier of the fixture carries a premium upgrade price.
        self.assertEqual(item_by_id(capture.FIXTURE_ITEM_ID)["premium_upgrade_costs"], "")
        self.assertEqual(
            item_by_id(capture.FIXTURE_TARGET_ITEM_ID)["premium_upgrade_costs"], ""
        )
        # Neither tier's own purchase price leaks into the neutral vector.
        wall_two = item_by_id(capture.FIXTURE_TARGET_ITEM_ID)
        self.assertEqual(wall_two["costs"], '{"s":15}')
        self.assertNotIn(-15, envelope_mod.neutral_vector())

    def test_the_fresh_save_can_execute_the_fixture_upgrade(self) -> None:
        row = FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        self.assertEqual(len(FRESH_ITEMS), capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE)
        self.assertEqual(len(row), 8)
        self.assertEqual(int(row[0]), capture.FIXTURE_ITEM_ID)
        self.assertEqual([row[1], row[2]], [capture.FIXTURE_X, capture.FIXTURE_Y])
        # The buy half reuses the row's own orientation and player team.
        self.assertEqual(row[4], 0)
        self.assertEqual(row[7], 1)
        self.assertEqual(row[5], [])  # store
        self.assertEqual(row[6], {})  # attr

    def test_the_fixture_row_carries_no_unit_or_storage_payload(self) -> None:
        self.assertEqual(FRESH_MAP["store"], {})
        self.assertEqual(SEED["privateState"]["boughtUnits"], [])  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["deadHeroes"], {})  # type: ignore[index]

    def test_the_fixture_slot_differs_from_every_delivered_fixture(self) -> None:
        """Design D10: all six committed fixtures stay independently readable."""
        for index in (capture.FIXTURE_ITEM_INDEX,):
            self.assertNotIn(index, (11, 20, 2))
        self.assertEqual(
            FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)], [23, 45, 49, 0, 0, [], {}, 1]
        )
        # A wall segment, distinct from the other fixtures' buildings.
        self.assertEqual(int(FRESH_ITEMS["11"][0]), 22)  # move fixture: Turret I
        self.assertEqual(int(FRESH_ITEMS["20"][0]), 22)  # sell fixture: Turret I
        self.assertEqual(int(FRESH_ITEMS["2"][0]), 905)  # store fixture: Tree
        wall_slots = sorted(
            int(key) for key, row in FRESH_ITEMS.items() if int(row[0]) == 23
        )
        self.assertIn(capture.FIXTURE_ITEM_INDEX, wall_slots)

    def test_the_fresh_save_starts_with_the_resources_the_fixture_keeps(self) -> None:
        self.assertEqual(FRESH_MAP["xp"], 4)
        for name in ("gold", "wood", "oil", "steel"):
            self.assertEqual(FRESH_MAP[name], 2000)
        self.assertEqual(SEED["playerInfo"]["cash"], 5)  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["mana"], 0)  # type: ignore[index]

    def test_the_level_gate_is_inexercisable_on_the_committed_corpus(self) -> None:
        """Design D6: the gap is recorded with its corpus evidence.

        The fresh save's ``maps[0].level`` is 1 and **no placement in the
        committed corpus** has a next tier with ``min_level <= 1`` — the lowest
        reachable from a placed row is 5 (Turret I -> Turret II) and the
        fixture's own target tier needs 9 — so enforcing the legacy client's
        level gate would make this deliver line unreachable on the corpus the
        project preserves.  The rule is therefore named as unimplemented with
        its evidence, not invented.

        Precisely: exactly one item in the whole committed config has a next
        tier with ``min_level == 1`` (item 10042, the "Chained Revolution
        Bonus 99" reward reached from Silo II, item 200), and Silo II is **not
        placed** in the fresh-player corpus, so it is unreachable there.
        """
        by_id = {int(entry["id"]): entry for entry in CONFIG["items"]}
        self.assertEqual(FRESH_MAP["level"], 1)
        reachable = sorted(
            {
                int(by_id[int(by_id[int(row[0])]["upgrades_to"])]["min_level"])
                for row in FRESH_ITEMS.values()
                if int(by_id[int(row[0])]["upgrades_to"]) > 0
            }
        )
        self.assertEqual(reachable[0], 5)  # Turret II
        self.assertGreater(reachable[0], FRESH_MAP["level"])
        self.assertFalse([level for level in reachable if level <= 1])
        self.assertGreater(
            int(item_by_id(capture.FIXTURE_TARGET_ITEM_ID)["min_level"]),
            FRESH_MAP["level"],
        )
        # The single whole-config exception, and why it is unreachable here.
        exception = sorted(
            int(by_id[int(entry["upgrades_to"])]["min_level"])
            for entry in CONFIG["items"]
            if int(entry["upgrades_to"]) > 0
        )
        self.assertEqual(exception[0], 1)
        self.assertNotIn(200, {int(row[0]) for row in FRESH_ITEMS.values()})


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_ITEM_INDEX, 12)
        self.assertEqual(capture.FIXTURE_ITEM_ID, 23)
        self.assertEqual(capture.FIXTURE_ITEM_NAME, "Wall I")
        self.assertEqual(capture.FIXTURE_TARGET_ITEM_ID, 24)
        self.assertEqual(capture.FIXTURE_TARGET_ITEM_NAME, "Wall II")
        self.assertEqual((capture.FIXTURE_X, capture.FIXTURE_Y), (45, 49))
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE, 40)
        # The key is reused, so the count does not move at all.
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_AFTER, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_BOUGHT_UNITS_BEFORE, [])
        self.assertEqual(capture.FIXTURE_EXPECTED_BOUGHT_UNITS_AFTER, [24])
        self.assertEqual(capture.FIXTURE_EXPECTED_ATTR_AFTER, {"nc": 0})
        self.assertIn("Wall I", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_upgrade"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-upgrade",
        )

    def test_the_config_resolver_applies_the_documented_none_rule(self) -> None:
        """-1, 0, a missing reference, and an unresolvable id mean no path."""
        self.assertEqual(capture.RELATION_NONE, (-1, 0))
        # The Tree decoration records upgrades_to "-1".
        self.assertIsNone(capture.config_upgrade_reference(905))
        # An id the config does not resolve has no path either.
        self.assertIsNone(capture.config_upgrade_reference(999999))

    def test_derived_fixture_envelope_pins_the_expected_values(self) -> None:
        built = self_built()
        self.assertEqual(built["commands"][0][1], "sell")
        self.assertEqual(built["commands"][0][2], [12, "UPGR"])
        self.assertEqual(built["commands"][1][2], [12, 24, 45, 49, 1, 0, 0, ""])
        self.assertEqual(built["commands"][0][3], capture.FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(built["commands"][1][3], capture.FIXTURE_EXPECTED_VECTOR)
        capture.verify_envelope(built)

    def test_protected_fixtures_are_the_six_committed_ones(self) -> None:
        self.assertEqual(
            [relative for relative, _label in capture.PROTECTED_FIXTURES],
            [
                "tests/fixtures/godot-compatibility-boot",
                "tests/fixtures/godot-building-placement",
                "tests/fixtures/godot-item-purchase",
                "tests/fixtures/godot-building-move",
                "tests/fixtures/godot-building-sell",
                "tests/fixtures/godot-building-store",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = self_built()
        cases = {
            "one command only": lambda env: env["commands"].pop(),
            "reversed order": lambda env: env["commands"].reverse(),
            "another index": lambda env: env["commands"][1][2].__setitem__(0, 11),
            "another target": lambda env: env["commands"][1][2].__setitem__(1, 25),
            "another cell": lambda env: env["commands"][1][2].__setitem__(2, 44),
            "a client-chosen reason": lambda env: env["commands"][0][2].__setitem__(
                1, "KILL"
            ),
            "an empty reason": lambda env: env["commands"][0][2].__setitem__(1, ""),
            "a non-neutral sell vector": lambda env: env["commands"][0][3].__setitem__(
                6, -500
            ),
            "a non-neutral buy vector": lambda env: env["commands"][1][3].__setitem__(
                2, -500
            ),
            "another map id": lambda env: env["commands"][1].__setitem__(0, 1),
            "extra envelope keys": lambda env: env.__setitem__("extra", 1),
        }
        for label, mutate in sorted(cases.items()):
            with self.subTest(case=label):
                drifted = json.loads(json.dumps(built))
                mutate(drifted)
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_envelope(drifted)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_the_negative_oracle_is_recorded_with_its_consequence(self) -> None:
        """Task 1.3: the reverse order destroys the row and still succeeds."""
        oracle = capture.NEGATIVE_ORACLE
        self.assertEqual(oracle["response_body"], '{"result": "success"}')
        self.assertEqual(oracle["http_status"], 200)
        self.assertEqual(oracle["placement_count_before"], 40)
        self.assertEqual(oracle["placement_count_after"], 39)
        self.assertIn("absent", oracle["key_12_afterwards"])
        self.assertIn("internal_error", oracle["consequence"])
        # The oracle's recorded commands are the established pair, reversed.
        self.assertEqual(
            [entry[1] for entry in oracle["envelope_commands"]], ["buy", "sell"]
        )
        self.assertEqual(
            [entry[2] for entry in oracle["envelope_commands"]],
            [[12, 24, 45, 49, 1, 0, 0, ""], [12, "UPGR"]],
        )

    def test_time_dependent_fields_are_named_as_json_pointers(self) -> None:
        """The capture publishes exactly which leaves move between runs."""
        source = Path_read_text(capture.__file__)
        self.assertIn('"time_dependent_fields"', source)
        self.assertIn("/maps/0/items/%d/3", source)
        self.assertIn("/transaction/upgraded_row_after/3", source)
        self.assertIn("/transaction/steps/1/save_after_sha256", source)

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = self_built()
        before = json.loads(json.dumps(SEED))
        after = _derived_upgrade_state()
        self.assertEqual(before["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)],
                         [23, 45, 49, 0, 0, [], {}, 1])
        capture.verify_transaction(before, after, built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = self_built()
        key = str(capture.FIXTURE_ITEM_INDEX)

        def destroy():
            """The reverse-order outcome: the key is gone, the count fell."""
            document = _derived_upgrade_state()
            document["maps"][0]["items"].pop(key)
            return document

        def remove_another():
            document = _derived_upgrade_state()
            document["maps"][0]["items"].pop("11")
            return document

        def change_another():
            document = _derived_upgrade_state()
            document["maps"][0]["items"]["11"] = [23, 59, 48, 0, 0, [], {}, 1]
            return document

        cases = {
            "the row was destroyed": destroy,
            "another row was removed": remove_another,
            "another row changed": change_another,
            "a wrong target tier": lambda: _derived_upgrade_state(
                item=25
            ),
            "the old tier stayed": lambda: _derived_upgrade_state(item=23),
            "a different cell": lambda: _derived_upgrade_state(x=46),
            "a non-wall-clock timestamp": lambda: _derived_upgrade_state(timestamp=0),
            "a missing construction seed": lambda: _derived_upgrade_state(attr={}),
            "a changed player team": lambda: _derived_upgrade_state(player=0),
            "a changed orientation": lambda: _derived_upgrade_state(orientation=3),
            "a carried-over stored-unit payload": lambda: _derived_upgrade_state(
                store=[1]
            ),
            "boughtUnits did not gain the tier": lambda: _derived_upgrade_state(
                bought=[]
            ),
            "boughtUnits gained something else": lambda: _derived_upgrade_state(
                bought=[23]
            ),
            "storage changed": lambda: _derived_upgrade_state(store_map={"24": 1}),
            "a resource changed": lambda: _derived_upgrade_state(gold=0),
            "the map timestamp changed": lambda: _derived_upgrade_state(
                map_timestamp=1234567890
            ),
            "deadHeroes changed": lambda: _derived_upgrade_state(dead_heroes={"23": True}),
            "mana changed": lambda: _derived_upgrade_state(mana=7),
        }
        for label, build in sorted(cases.items()):
            with self.subTest(case=label):
                before = json.loads(json.dumps(SEED))
                after = build()
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


def _derived_upgrade_state(
    item: int = capture.FIXTURE_TARGET_ITEM_ID,
    x: int = capture.FIXTURE_X,
    timestamp: int = 1790000000,
    orientation: int = 0,
    store: Optional[list] = None,
    attr: Optional[dict] = None,
    player: int = 1,
    bought: Optional[list] = None,
    store_map: Optional[dict] = None,
    gold: Optional[int] = None,
    map_timestamp: Optional[int] = None,
    dead_heroes: Optional[dict] = None,
    mana: Optional[int] = None,
) -> Dict[str, object]:
    """A fresh-save copy carrying the derived upgrade, field-overridable.

    Defaults are the executed outcome, so every override in the mismatch table
    names exactly one deviation from it.
    """
    document = json.loads(json.dumps(SEED))
    document["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)] = [
        item,
        x,
        capture.FIXTURE_Y,
        timestamp,
        orientation,
        list(store) if store is not None else [],
        dict(attr) if attr is not None else {"nc": 0},
        player,
    ]
    document["privateState"]["boughtUnits"] = (
        list(bought) if bought is not None else [capture.FIXTURE_TARGET_ITEM_ID]
    )
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
        data = envelope_mod.data_field(self_built())
        self.assertEqual(capture.sanitize_data_field(data), data)

    def test_non_empty_access_token_is_redacted_in_the_data_field(self) -> None:
        built = self_built()
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
