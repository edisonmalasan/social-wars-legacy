#!/usr/bin/env python3
"""Offline unit tests for the collect envelope derivation and the collect
capture tool's published contract (OpenSpec tasks 2.1 / 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the fixture intent, the
committed ``collect`` / ``collect_type`` / ``collect_xp`` / ``max_collects`` of
the placed Tree, the committed ladder, the derived top-rung payout, and the
two always-zero vector slots against the bytes the legacy server actually
loads, and the shared-helper round trip proves the single-command envelope
travels through the placement module's unchanged serialization (design D8).

The six derived-provisional decisions are asserted as behavior, not comments:

* **D1** the multiplier is applied to the amount and the elapsed time is
  clamped at the top rung — never extrapolated;
* **D2** ``collect_xp`` scales with the same rung as the amount;
* **D3** below the first rung :func:`tier_for` returns ``None`` so the caller
  fails closed, and a sub-rung amount is never derived;
* **D4** only an uncapped item is implemented — the derivation itself refuses a
  non-integer or negative amount or experience, and the cap refusal lives in
  the endpoint;
* **D5** the shared-field refusal lives in the endpoint (a row carrying ``cp`` or
  ``nc`` must never reach the dispatcher), so this module asserts that the
  derivation has **no** input that could express it;
* **D6** only the five committed resource types map, and the unread slot 0 and
  the never-produced mana slot 7 are always zero.
"""

from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import capture_collect_fixture as capture
import collect_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]

# The committed ladder, used as the derivation's input in unit tests.  It is
# read from the committed config here rather than hardcoded a second time.
LADDER: Any = (
    CONFIG["globals"]["COLLECT_MINUTES"],
    CONFIG["globals"]["COLLECT_MULTIPLIER"],
)
TOP_TIER = len(CONFIG["globals"]["COLLECT_MULTIPLIER"]) - 1

# The friend-assist bag key: no command in this contract writes it, and a row
# carrying it is still collectible (the change's non-goals keep it out of scope).
FRIEND_ASSIST_KEY = "si"


def _scale(value: int, multiplier: float) -> int:
    """The derivation's own rung scaling, mirrored for readable assertions.

    ``collect_envelope._scale`` rounds a fractional product half up so a float
    can never reach legacy's integer vector; the committed multipliers and
    amounts are chosen so every product is already whole.
    """
    product = float(value) * float(multiplier)
    if product <= 0:
        return 0
    if float(product).is_integer():
        return int(product)
    return int(product + 0.5)


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
        # The collect derivation is additive: the delivered siblings keep their
        # own, and the construction module's helpers are untouched.
        self.assertFalse(hasattr(placement_envelope, "payout_for"))
        self.assertFalse(hasattr(placement_envelope, "tier_for"))
        self.assertFalse(hasattr(placement_envelope, "COLLECT_RESOURCE_SLOTS"))

    def test_the_command_is_the_documented_legacy_name(self) -> None:
        # command.py:136-147, and the collect row of docs/legacy-protocol/commands.json.
        self.assertEqual(envelope_mod.COLLECT_COMMAND, "collect")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)
        self.assertEqual(envelope_mod.EXPERIENCE_SLOT, 1)
        self.assertEqual(envelope_mod.ALWAYS_ZERO_SLOTS, (0, 7))

    def test_the_resource_vocabulary_is_closed_and_covers_the_committed_set(self) -> None:
        """Design D6: exactly the five committed collect types, no mana."""
        self.assertEqual(
            envelope_mod.COLLECT_RESOURCE_SLOTS,
            {"g": 2, "w": 3, "o": 4, "s": 5, "c": 6},
        )
        committed = {entry["collect_type"] for entry in CONFIG["items"]}
        self.assertEqual(committed, set(envelope_mod.COLLECT_RESOURCE_SLOTS))
        # No item records a mana collect type, so slot 7 is never payable.
        self.assertNotIn(7, envelope_mod.COLLECT_RESOURCE_SLOTS.values())

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.collect_envelope, envelope_mod)
        self.assertEqual(
            compat_service.ERROR_CAPPED_COLLECTION, "capped_collection"
        )
        self.assertEqual(
            compat_service.ERROR_UNKNOWN_COLLECT_TYPE, "unknown_collect_type"
        )
        self.assertEqual(compat_service.ERROR_NO_INCOME, "no_income")
        self.assertEqual(compat_service.ERROR_TOO_EARLY, "too_early")
        self.assertEqual(
            compat_service.ERROR_CONSTRUCTION_IN_PROGRESS, "construction_in_progress"
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
        self.assertTrue(envelope_mod.is_strict_int(2))
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int("2"))
        self.assertFalse(envelope_mod.is_strict_int(2.0))
        self.assertFalse(envelope_mod.is_strict_int(None))


class LadderTests(unittest.TestCase):
    """The committed ladder is the rung source, and it is validated as a pair."""

    def test_the_committed_ladder_resolves_to_the_documented_pair(self) -> None:
        minutes, multipliers = envelope_mod.collect_ladder(LADDER)
        self.assertEqual(list(minutes), [5, 60, 240, 480])
        self.assertEqual(list(multipliers), [0.25, 1, 2, 3])
        # The committed COLLECT_HELP_SECONDS exists and is deliberately unused
        # here: a friend-help duration is a social mechanism out of scope.
        self.assertEqual(CONFIG["globals"]["COLLECT_HELP_SECONDS"], 3600)

    def test_a_mapping_shaped_ladder_is_accepted_too(self) -> None:
        minutes, multipliers = envelope_mod.collect_ladder(
            {"minutes": [1], "multipliers": [2]}
        )
        self.assertEqual(minutes, (1,))
        self.assertEqual(multipliers, (2.0,))

    def test_a_malformed_ladder_fails_closed(self) -> None:
        cases: List[Any] = [
            ([], []),  # empty
            ([5], [1, 2]),  # mismatched lengths
            ([5, 60], [1]),  # mismatched lengths
            ([0, 60], [1, 2]),  # a non-positive threshold
            ([60, 5], [1, 2]),  # non-monotonic thresholds
            ([5, 5.5], [1, 2]),  # a fractional threshold
            ([5, 60], [1, 0]),  # a non-positive multiplier
            ([5, 60], [1, -2]),  # a negative multiplier
            (["5", "60"], [1, 2]),  # a string threshold
            (None, [1, 2]),  # an absent half
            ("5,60", [1, 2]),  # not a sequence
            ([1, 2],),  # not a pair
            ({"minutes": [1, 2, 3]},),  # not a pair
            (42, 42),  # not a sequence at all
        ]
        for ladder in cases:
            with self.subTest(ladder=ladder):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.collect_ladder(ladder)
                self.assertEqual(caught.exception.code, "no_tier")

    def test_a_non_finite_multiplier_is_refused(self) -> None:
        for bad in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(multiplier=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.collect_ladder(([5], [bad]))
                self.assertEqual(caught.exception.code, "no_tier")


class TierForTests(unittest.TestCase):
    """Design D1/D3: the reached rung, the top clamp, and the no-rung refusal."""

    def test_no_rung_is_reached_below_the_first_threshold(self) -> None:
        """Design D3: the caller must fail closed, never derive a quarter.

        The committed threshold is 5 *minutes*, so the first rung is reached at
        300 seconds — not at 5.  Comparing the raw minutes value against a
        seconds-valued elapsed time would pay the top rung within seconds.
        """
        for elapsed in (0, 1, 4, 5, 59, 60, 299):
            with self.subTest(elapsed=elapsed):
                self.assertIsNone(envelope_mod.tier_for(elapsed, LADDER))

    def test_each_threshold_reaches_its_own_rung(self) -> None:
        cases = [
            (300, 0),
            (301, 0),
            (3599, 0),
            (3600, 1),
            (3601, 1),
            (14399, 1),
            (14400, 2),
            (14401, 2),
            (28799, 2),
            (28800, 3),
        ]
        for elapsed, expected in cases:
            with self.subTest(elapsed=elapsed):
                self.assertEqual(envelope_mod.tier_for(elapsed, LADDER), expected)

    def test_the_committed_thresholds_are_minutes_and_the_elapsed_time_seconds(self) -> None:
        """The unit conversion, asserted at each exact boundary."""
        self.assertEqual(envelope_mod.SECONDS_PER_COMMITTED_MINUTE, 60)
        self.assertEqual(
            [envelope_mod.threshold_seconds_for(tier, LADDER) for tier in range(4)],
            [300, 3600, 14400, 28800],
        )
        thresholds = (300, 3600, 14400, 28800)
        for tier, threshold in enumerate(thresholds):
            with self.subTest(tier=tier):
                # One second below the threshold the previous rung is still the
                # reached one (and rung 0 has no previous rung at all).
                if tier == 0:
                    self.assertIsNone(envelope_mod.tier_for(threshold - 1, LADDER))
                else:
                    self.assertEqual(
                        envelope_mod.tier_for(threshold - 1, LADDER), tier - 1
                    )
                self.assertEqual(envelope_mod.tier_for(threshold, LADDER), tier)

    def test_threshold_seconds_for_refuses_a_tier_outside_the_ladder(self) -> None:
        for bad in (-1, 4, True, "0", None):
            with self.subTest(tier=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.threshold_seconds_for(bad, LADDER)
                self.assertEqual(caught.exception.code, "no_tier")

    def test_the_elapsed_time_is_clamped_at_the_top_rung(self) -> None:
        """Design D1: no extrapolation past the last committed rung."""
        for elapsed in (28800, 28801, 10 ** 6, 10 ** 9, 10 ** 15):
            with self.subTest(elapsed=elapsed):
                self.assertEqual(
                    envelope_mod.tier_for(elapsed, LADDER), TOP_TIER
                )

    def test_a_unbounded_elapsed_time_reaches_the_top_rung(self) -> None:
        """The corpus consequence: every row's item[3] is 0, so the elapsed
        time is unbounded and the top rung is deterministic."""
        self.assertEqual(envelope_mod.tier_for(2 ** 31, LADDER), TOP_TIER)

    def test_a_non_integer_or_negative_elapsed_time_fails_closed(self) -> None:
        for bad in (True, "300", 300.0, None, [300], {"s": 300}, -1, -(10 ** 9)):
            with self.subTest(elapsed=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.tier_for(bad, LADDER)
                self.assertEqual(caught.exception.code, "no_tier")

    def test_multiplier_for_returns_the_committed_rung_multiplier(self) -> None:
        for tier, expected in enumerate([0.25, 1, 2, 3]):
            with self.subTest(tier=tier):
                self.assertEqual(envelope_mod.multiplier_for(tier, LADDER), expected)

    def test_multiplier_for_refuses_a_tier_outside_the_ladder(self) -> None:
        for bad in (-1, 4, 99, True, "0", 1.0, None):
            with self.subTest(tier=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.multiplier_for(bad, LADDER)
                self.assertEqual(caught.exception.code, "no_tier")

    def test_the_ladder_itself_is_validated_by_every_rung_helper(self) -> None:
        for bad in (None, (), ([5], )):
            with self.subTest(ladder=bad):
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.tier_for(10 ** 9, bad)
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.multiplier_for(0, bad)


class PayoutTests(unittest.TestCase):
    """Design D1/D2/D6: the derived 8-slot vector."""

    def test_the_top_rung_pays_the_committed_amount_scaled_threefold(self) -> None:
        # The Tree: collect 20, collect_xp 1, collect_type "w", top rung x3.
        vector = envelope_mod.payout_for(
            amount=20,
            resource_type="w",
            experience=1,
            tier=TOP_TIER,
            ladder=LADDER,
        )
        self.assertEqual(vector, [0, 3, 0, 60, 0, 0, 0, 0])
        self.assertEqual(len(vector), envelope_mod.RESOURCE_VECTOR_SLOTS)

    def test_each_rung_scales_both_the_amount_and_the_experience(self) -> None:
        """Design D1 + D2: the same rung scales both, never one alone.

        The committed multipliers are ``0.25, 1, 2, 3``, so the Tree's committed
        amount of 20 pays ``5, 20, 40, 60`` and its committed experience of 1
        pays ``0 (0.25 rounds down), 1, 2, 3`` — the same rung driving both,
        which is exactly what a flat-experience reading would not do.
        """
        for tier, multiplier in enumerate([0.25, 1, 2, 3]):
            with self.subTest(tier=tier):
                vector = envelope_mod.payout_for(
                    amount=20, resource_type="w", experience=1, tier=tier, ladder=LADDER
                )
                self.assertEqual(vector[1], _scale(1, multiplier))
                self.assertEqual(vector[3], _scale(20, multiplier))
        # The three rungs whose multiplier is not 1 must differ from a flat
        # payout, and the one whose multiplier IS 1 must equal it.
        flat_amount = envelope_mod.payout_for(
            amount=20, resource_type="w", experience=0, tier=1, ladder=LADDER
        )
        self.assertEqual(flat_amount[3], 20)
        for tier in (0, 2, 3):
            with self.subTest(tier=tier):
                vector = envelope_mod.payout_for(
                    amount=20, resource_type="w", experience=0, tier=tier, ladder=LADDER
                )
                self.assertNotEqual(vector[3], 20)
        # A flat experience would be 1 at every rung; three of the four are not.
        flat_xp = [
            envelope_mod.payout_for(
                amount=0, resource_type="w", experience=1, tier=tier, ladder=LADDER
            )[1]
            for tier in range(4)
        ]
        self.assertEqual(flat_xp, [0, 1, 2, 3])

    def test_the_first_rung_derives_a_quarter_rather_than_nothing(self) -> None:
        # 20 x 0.25 = 5 and 1 x 0.25 rounds to 0.  Both are consequences of the
        # committed 0.25 multiplier, not invented sub-rungs.
        vector = envelope_mod.payout_for(
            amount=20, resource_type="w", experience=1, tier=0, ladder=LADDER
        )
        self.assertEqual(vector, [0, 0, 0, 5, 0, 0, 0, 0])

    def test_each_resource_type_lands_in_its_committed_slot(self) -> None:
        """Design D6: the closed mapping, and only the named slot moves."""
        expected = {"g": 2, "w": 3, "o": 4, "s": 5, "c": 6}
        for resource_type, slot in sorted(expected.items()):
            with self.subTest(collect_type=resource_type):
                vector = envelope_mod.payout_for(
                    amount=20, resource_type=resource_type, experience=0, tier=TOP_TIER, ladder=LADDER
                )
                self.assertEqual(vector[slot], 60)
                paying = [index for index, value in enumerate(vector) if value]
                self.assertEqual(paying, [slot])

    def test_a_cash_collection_lands_in_the_cash_slot(self) -> None:
        """The committed census has 2 cash-bearing items, so the mapping is
        real, and it pays the ``playerInfo.cash`` slot (engine.py:267)."""
        vector = envelope_mod.payout_for(
            amount=20, resource_type="c", experience=0, tier=0, ladder=LADDER
        )
        self.assertEqual(vector, [0, 0, 0, 0, 0, 0, 5, 0])
        # 20 x 0.25 is exactly 5, so no rounding is involved on this path.
        self.assertEqual(vector[6], 5)

    def test_a_fractional_product_rounds_to_a_whole_resource(self) -> None:
        """The committed multipliers and amounts are chosen so every product is
        already an integer; the rounding only guards a future fractional
        multiplier from putting a float on legacy's integer vector."""
        self.assertEqual(_scale(10, 0.25), 3)  # 2.5 rounds half up
        self.assertEqual(_scale(7, 0.25), 2)  # 1.75 rounds to 2
        self.assertEqual(_scale(20, 0.25), 5)
        self.assertEqual(_scale(1, 0.25), 0)
        for amount in (10, 100, 150, 250, 350, 500, 1800, 3600):
            for multiplier in (0.25, 1, 2, 3):
                with self.subTest(amount=amount, multiplier=multiplier):
                    scaled = _scale(amount, multiplier)
                    self.assertIsInstance(scaled, int)
                    self.assertNotIsInstance(scaled, bool)
                    self.assertGreaterEqual(scaled, 0)

    def test_the_unread_and_mana_slots_are_always_zero(self) -> None:
        """Design D6: slot 0 is unread, slot 7 is never produced."""
        for resource_type in sorted(envelope_mod.COLLECT_RESOURCE_SLOTS):
            for tier in range(len(LADDER[1])):
                with self.subTest(collect_type=resource_type, tier=tier):
                    vector = envelope_mod.payout_for(
                        amount=100,
                        resource_type=resource_type,
                        experience=40,
                        tier=tier,
                        ladder=LADDER,
                    )
                    self.assertEqual(vector[0], 0)
                    self.assertEqual(vector[7], 0)

    def test_an_unmapped_collect_type_fails_closed(self) -> None:
        """Design D6: refused, never coerced into an assumed resource."""
        for bad in (
            "m",  # a mana type no item records
            "M",  # case is not normalized
            "W",
            "energy",
            "",
            None,
            3,
            True,
            ["w"],
            {"type": "w"},
        ):
            with self.subTest(collect_type=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.payout_for(
                        amount=20, resource_type=bad, experience=1, tier=0, ladder=LADDER
                    )
                self.assertEqual(caught.exception.code, "unknown_collect_type")

    def test_a_non_integer_or_negative_amount_fails_closed(self) -> None:
        for bad in (True, "20", 20.0, None, [20], {"collect": 20}, -1, -(10 ** 9)):
            with self.subTest(amount=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.payout_for(
                        amount=bad, resource_type="w", experience=1, tier=0, ladder=LADDER
                    )
                self.assertEqual(caught.exception.code, "invalid_amount")

    def test_a_non_integer_or_negative_experience_fails_closed(self) -> None:
        for bad in (True, "1", 1.0, None, [1], -1):
            with self.subTest(experience=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.payout_for(
                        amount=20, resource_type="w", experience=bad, tier=0, ladder=LADDER
                    )
                self.assertEqual(caught.exception.code, "invalid_experience")

    def test_zero_is_a_derived_amount_and_a_derived_experience(self) -> None:
        """``collect 0`` is committed content, not an unusable value: the
        endpoint's ``no_income`` refusal lives upstream of this module, so the
        derivation still derives an all-zero payout for it."""
        vector = envelope_mod.payout_for(
            amount=0, resource_type="g", experience=0, tier=TOP_TIER, ladder=LADDER
        )
        self.assertEqual(vector, [0] * 8)

    def test_the_validation_order_is_amount_then_type_then_experience(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.payout_for(
                amount=-1, resource_type="m", experience=-1, tier=0, ladder=LADDER
            )
        self.assertEqual(caught.exception.code, "invalid_amount")
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.payout_for(
                amount=1, resource_type="m", experience=-1, tier=0, ladder=LADDER
            )
        self.assertEqual(caught.exception.code, "unknown_collect_type")
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.payout_for(
                amount=1, resource_type="g", experience=-1, tier=-1, ladder=LADDER
            )
        self.assertEqual(caught.exception.code, "invalid_experience")

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.payout_for(
            amount=20, resource_type="w", experience=1, tier=TOP_TIER, ladder=LADDER
        )
        first[3] = -999
        second = envelope_mod.payout_for(
            amount=20, resource_type="w", experience=1, tier=TOP_TIER, ladder=LADDER
        )
        self.assertEqual(second[3], 60)

    def test_a_never_exercised_clamp_stays_unexercised(self) -> None:
        """The derived payouts are credits on positive balances, so legacy's
        ``max(current + delta, 0)`` never bites.  This is the claim the fixture
        README and the manifest record."""
        for balance in (0, 1, 5, 2000):
            for slot, delta in (
                (1, 3),
                (3, 60),
                (6, 2),
            ):
                with self.subTest(balance=balance, slot=slot):
                    self.assertGreater(max(balance + delta, 0), balance)

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.payout_for(
                amount=20, resource_type="SECRET-TOKEN", experience=1, tier=0, ladder=LADDER
            )
        message = str(caught.exception)
        self.assertIn("collect_type", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class BuildEnvelopeTests(unittest.TestCase):
    """The six keys and exactly one command, with the derived payout."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        arguments: Dict[str, Any] = {
            "item_index": capture.FIXTURE_ITEM_INDEX,
            "vector": list(capture.FIXTURE_EXPECTED_VECTOR),
            "ts": 1700000000,
        }
        arguments.update(overrides)
        return envelope_mod.build_envelope(**arguments)

    def test_the_envelope_has_exactly_the_six_legacy_keys(self) -> None:
        built = self.build()
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        self.assertEqual(built["first_number"], 0)
        self.assertEqual(built["publishActions"], [])
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(built["tries"], 1)
        self.assertEqual(built["accessToken"], "")

    def test_the_batch_carries_exactly_one_collect_command(self) -> None:
        commands = self.build()["commands"]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0], 0)
        self.assertEqual(commands[0][1], "collect")

    def test_the_argument_list_is_exactly_the_one_the_branch_reads(self) -> None:
        # command.py:137 binds a single positional arg.
        args = self.build()["commands"][0][2]
        self.assertEqual(args, [capture.FIXTURE_ITEM_INDEX])
        self.assertEqual(len(args), 1)

    def test_the_command_carries_the_derived_payout_verbatim(self) -> None:
        self.assertEqual(
            self.build()["commands"][0][3], capture.FIXTURE_EXPECTED_VECTOR
        )

    def test_any_integer_index_is_accepted(self) -> None:
        """Addressability is the endpoint's job, not the derivation's."""
        for index in (0, 2, 41, 999999):
            with self.subTest(item_index=index):
                self.assertEqual(
                    self.build(item_index=index)["commands"][0][2], [index]
                )

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            vector=list(capture.FIXTURE_EXPECTED_VECTOR),
        )
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_a_non_integer_index_fails_closed(self) -> None:
        for bad in (True, "2", 2.0, None, [2], {"index": 2}):
            with self.subTest(item_index=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(item_index=bad)
                self.assertEqual(caught.exception.code, "invalid_item_index")

    def test_a_bad_timestamp_fails_closed(self) -> None:
        for bad in (-1, "1700000000", True, 1700000000.0):
            with self.subTest(ts=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(ts=bad)
                self.assertEqual(caught.exception.code, "invalid_timestamp")

    def test_a_malformed_vector_fails_closed(self) -> None:
        cases: List[Any] = [
            None,
            [0] * 7,
            [0] * 9,
            "00000000",
            (0,) * 8,
            {"vector": [0] * 8},
            [-1, 3, 0, 60, 0, 0, 0, 0],  # a negative delta
            [0, 3, 0, -60, 0, 0, 0, 0],
            [0, 3.0, 0, 60, 0, 0, 0, 0],  # a float slot
            [0, True, 0, 60, 0, 0, 0, 0],  # a bool slot
        ]
        for vector in cases:
            with self.subTest(vector=vector):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(vector=vector)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_the_index_is_validated_before_the_vector(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(item_index="2", vector=[0] * 7)
        self.assertEqual(caught.exception.code, "invalid_item_index")

    def test_a_negative_delta_can_never_be_sent(self) -> None:
        """A negative slot is exactly what would exercise legacy's clamp, and
        this contract refuses to send one (design D8's value-level proof)."""
        for slot in range(8):
            vector = [0] * 8
            vector[slot] = -1
            with self.subTest(slot=slot):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(vector=vector)
                self.assertEqual(caught.exception.code, "invalid_vector")


class SharedSerializationTests(unittest.TestCase):
    """The single-command envelope travels through the unchanged helpers."""

    def test_roundtrip_through_the_legacy_field_format(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            vector=list(capture.FIXTURE_EXPECTED_VECTOR),
            ts=1700000000,
        )
        data = envelope_mod.data_field(built)
        self.assertEqual(len(data.split(";", 1)[0]), 64)
        self.assertEqual(data[64], ";")
        self.assertEqual(envelope_mod.parse_data_field(data), built)

    def test_serialization_is_deterministic(self) -> None:
        built = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX,
            vector=list(capture.FIXTURE_EXPECTED_VECTOR),
            ts=1700000000,
        )
        first = envelope_mod.payload_json(built)
        second = envelope_mod.payload_json(built)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith('{"accessToken":"","commands":['))

    def test_the_payload_carries_exactly_the_established_command(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        payload = json.loads(envelope_mod.data_field(built)[65:])
        self.assertEqual(
            payload["commands"], [[0, "collect", [2], [0, 3, 0, 60, 0, 0, 0, 0]]]
        )
        self.assertEqual(payload["first_number"], 0)
        self.assertEqual(payload["publishActions"], [])
        self.assertEqual(payload["tries"], 1)
        self.assertEqual(payload["accessToken"], "")

    def test_malformed_fields_fail_closed(self) -> None:
        good = envelope_mod.data_field(capture.build_fixture_envelope(ts=1700000000))
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
        tree = item_by_id(capture.FIXTURE_ITEM_ID)
        self.assertEqual(tree["name"], capture.FIXTURE_ITEM_NAME)
        self.assertEqual(tree["type"], "b")
        self.assertEqual(int_attribute(capture.FIXTURE_ITEM_ID, "collect"),
                         capture.FIXTURE_COLLECT_AMOUNT)
        self.assertEqual(tree["collect_type"], capture.FIXTURE_COLLECT_TYPE)
        self.assertEqual(int_attribute(capture.FIXTURE_ITEM_ID, "collect_xp"),
                         capture.FIXTURE_COLLECT_XP)
        self.assertEqual(int_attribute(capture.FIXTURE_ITEM_ID, "max_collects"),
                         capture.FIXTURE_MAX_COLLECTS)
        self.assertEqual(
            capture.config_collect_amount(capture.FIXTURE_ITEM_ID),
            capture.FIXTURE_COLLECT_AMOUNT,
        )
        self.assertEqual(
            capture.config_collect_type(capture.FIXTURE_ITEM_ID),
            capture.FIXTURE_COLLECT_TYPE,
        )
        self.assertEqual(
            capture.config_collect_xp(capture.FIXTURE_ITEM_ID),
            capture.FIXTURE_COLLECT_XP,
        )
        self.assertEqual(
            capture.config_max_collects(capture.FIXTURE_ITEM_ID),
            capture.FIXTURE_MAX_COLLECTS,
        )

    def test_the_committed_census_matches_the_recorded_investigation(self) -> None:
        """docs/legacy-collect-income.md, over the 778 stored items."""
        items = CONFIG["items"]
        self.assertEqual(len(items), 778)
        types: Dict[str, int] = {}
        zero_collect = 0
        zero_xp = 0
        zero_cap = 0
        for entry in items:
            key = str(entry.get("collect_type"))
            types[key] = types.get(key, 0) + 1
            if str(entry.get("collect")).strip() == "0":
                zero_collect += 1
            if str(entry.get("collect_xp")).strip() == "0":
                zero_xp += 1
            if str(entry.get("max_collects")).strip() == "0":
                zero_cap += 1
        self.assertEqual(types, {"g": 731, "w": 23, "o": 11, "s": 11, "c": 2})
        self.assertEqual(zero_collect, 727)
        self.assertEqual(zero_xp, 419)
        self.assertEqual(zero_cap, 767)
        self.assertEqual(
            sorted(
                str(entry.get("max_collects"))
                for entry in items
                if str(entry.get("max_collects")).strip() != "0"
            ),
            ["100", "100", "25", "25", "25", "25", "25", "25", "25", "25", "25"],
        )
        # No item records a mana collect type, so slot 7 is never payable.
        self.assertNotIn("m", types)

    def test_every_committed_collect_type_maps_onto_a_payable_slot(self) -> None:
        for entry in CONFIG["items"]:
            with self.subTest(item_id=entry["id"]):
                self.assertIn(entry["collect_type"], envelope_mod.COLLECT_RESOURCE_SLOTS)

    def test_only_zero_caps_are_implemented_and_the_corpus_records_zero(self) -> None:
        """Design D4: the corpus's income rows all record 0, so the refusal
        is unreachable against the committed corpus and is stub-covered."""
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        for key, row in sorted(seed_items.items()):
            with self.subTest(key=key):
                cap = int_attribute(int(row[0]), "max_collects")
                self.assertEqual(cap, 0)
                self.assertEqual(
                    capture.config_max_collects(int(row[0])), 0
                )

    def test_the_ladder_is_the_committed_pair(self) -> None:
        minutes, multipliers = capture.config_ladder()
        self.assertEqual(list(minutes), capture.FIXTURE_LADDER_MINUTES)
        self.assertEqual(list(multipliers), capture.FIXTURE_LADDER_MULTIPLIERS)
        self.assertEqual(list(minutes), [5, 60, 240, 480])
        self.assertEqual(list(multipliers), [0.25, 1, 2, 3])

    def test_the_fresh_save_can_execute_the_fixture_collection(self) -> None:
        row = FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)]
        self.assertEqual(len(FRESH_ITEMS), capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE)
        self.assertEqual(len(row), 8)
        self.assertEqual(int(row[0]), capture.FIXTURE_ITEM_ID)
        self.assertEqual([row[1], row[2]], [capture.FIXTURE_X, capture.FIXTURE_Y])
        self.assertEqual(row[4], 0)  # orientation
        self.assertEqual(row[5], [])  # store
        self.assertEqual(row[6], {})  # attr: no construction state
        self.assertEqual(row[3], 0)  # collection instant: never collected
        self.assertEqual(row[7], 1)  # player team

    def test_every_corpus_row_starts_uncollected_and_without_construction(self) -> None:
        """The determinism the fixture relies on: all 40 rows carry item[3] == 0
        and attr == {}, so the top rung applies and no row is refused for
        construction state."""
        for key, row in sorted(FRESH_ITEMS.items()):
            with self.subTest(key=key):
                self.assertEqual(row[3], 0)
                self.assertEqual(row[6], {})

    def test_the_fresh_save_starts_with_the_resources_the_fixture_moves(self) -> None:
        self.assertEqual(FRESH_MAP["xp"], 4)
        for name in ("gold", "wood", "oil", "steel"):
            self.assertEqual(FRESH_MAP[name], 2000)
        self.assertEqual(SEED["playerInfo"]["cash"], 5)  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["mana"], 0)  # type: ignore[index]
        self.assertEqual(FRESH_MAP["store"], {})
        self.assertEqual(SEED["privateState"]["boughtUnits"], [])  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["deadHeroes"], {})  # type: ignore[index]
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_BEFORE,
            {
                "xp": 4,
                "gold": 2000,
                "wood": 2000,
                "oil": 2000,
                "steel": 2000,
                "cash": 5,
                "mana": 0,
            },
        )

    def test_the_corpus_income_rows_are_exactly_the_decorations(self) -> None:
        """The recorded claim limit: the real factories are not placed, so the
        only income-bearing rows are the Tree and the forest rows."""
        income = sorted(
            int(row[0]) for row in FRESH_ITEMS.values() if int_attribute(int(row[0]), "collect")
        )
        self.assertEqual(income, [905, 930, 930, 930, 930, 930, 930, 931, 931])
        self.assertEqual(int(FRESH_ITEMS["2"][0]), 905)
        self.assertEqual(int(FRESH_ITEMS["21"][0]), 930)
        self.assertEqual(int(FRESH_ITEMS["23"][0]), 931)
        # And the derived payout for each of them is the same top-rung vector.
        for item_id in sorted(set(income)):
            with self.subTest(item_id=item_id):
                self.assertEqual(
                    int_attribute(item_id, "collect"),
                    capture.FIXTURE_COLLECT_AMOUNT,
                )
                self.assertEqual(
                    item_by_id(item_id)["collect_type"],
                    capture.FIXTURE_COLLECT_TYPE,
                )
                self.assertEqual(
                    envelope_mod.payout_for(
                        amount=int_attribute(item_id, "collect"),
                        resource_type=item_by_id(item_id)["collect_type"],
                        experience=int_attribute(item_id, "collect_xp"),
                        tier=TOP_TIER,
                        ladder=LADDER,
                    ),
                    capture.FIXTURE_EXPECTED_VECTOR,
                )

    def test_the_fixture_row_is_the_store_fixtures_row_and_only_that(self) -> None:
        """Design D10: all nine committed fixtures stay readable.  The collect
        and store fixtures share slot 2 because each capture seeds a **fresh**
        corpus, so their transactions are independent; the construction (11),
        move (11), upgrade (12), and sell (20) fixtures use other rows."""
        self.assertEqual(
            FRESH_ITEMS[str(capture.FIXTURE_ITEM_INDEX)],
            [capture.FIXTURE_ITEM_ID, capture.FIXTURE_X, capture.FIXTURE_Y, 0, 0, [], {}, 1],
        )
        self.assertEqual(int(FRESH_ITEMS["11"][0]), 22)  # construction/move fixture
        self.assertEqual(int(FRESH_ITEMS["12"][0]), 23)  # upgrade fixture: Wall I
        self.assertEqual(int(FRESH_ITEMS["20"][0]), 22)  # sell fixture: Turret I

    def test_no_committed_branch_compares_the_collection_content(self) -> None:
        """The catalog records the same for the collect entry: the branch only
        stamps the timer, and the income travels through client-sent deltas."""
        catalog = json.loads(
            (harness.REPO_ROOT / "docs" / "legacy-protocol" / "commands.json").read_text(
                encoding="utf-8"
            )
        )
        by_name = {entry["name"]: entry for entry in catalog["commands"]}
        collect_entry = by_name["collect"]
        writes = " ".join(collect_entry["state_writes"])
        self.assertIn("item[3] = time_now", writes)
        self.assertIn("missing item logs an error and returns early", writes)
        for absent in (
            "COLLECT_MINUTES",
            "COLLECT_MULTIPLIER",
            "max_collects",
            "collect_type",
            "bought_unit_add",
            "push_dead_unit",
        ):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, writes)
        # Exactly one positional arg and exactly one state write, so the
        # envelope's single argument and the endpoint's single-row proof are
        # both pinned to the committed catalog.
        self.assertEqual(
            collect_entry["args"]["positional"], ["args[0] item_index"]
        )
        self.assertEqual(len(collect_entry["state_writes"]), 1)
        self.assertEqual(collect_entry["state_reads"], ["map item at item_index"])
        effects = " ".join(collect_entry["resource_effects"])
        self.assertIn("client-sent deltas", effects)
        self.assertIn("clamped at zero", effects)
        self.assertIn("the branch only stamps the timer", effects)
        self.assertEqual(collect_entry["classification"], "handled")
        self.assertEqual(collect_entry["domain"], "economy")


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_ITEM_INDEX, 2)
        self.assertEqual(capture.FIXTURE_ITEM_ID, 905)
        self.assertEqual(capture.FIXTURE_ITEM_NAME, "Tree")
        self.assertEqual((capture.FIXTURE_X, capture.FIXTURE_Y), (53, 39))
        self.assertEqual(capture.FIXTURE_COLLECT_AMOUNT, 20)
        self.assertEqual(capture.FIXTURE_COLLECT_TYPE, "w")
        self.assertEqual(capture.FIXTURE_COLLECT_XP, 1)
        self.assertEqual(capture.FIXTURE_MAX_COLLECTS, 0)
        self.assertEqual(capture.FIXTURE_LADDER_MINUTES, [5, 60, 240, 480])
        self.assertEqual(capture.FIXTURE_LADDER_MULTIPLIERS, [0.25, 1, 2, 3])
        self.assertEqual(capture.FIXTURE_EXPECTED_TIER, 3)
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0, 3, 0, 60, 0, 0, 0, 0])
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_AFTER, 40)
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_DELTA, {"xp": 3, "wood": 60}
        )
        self.assertIn("Tree", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_collect"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-collect",
        )

    def test_the_config_resolvers_apply_the_documented_rules(self) -> None:
        """Absent, non-integer, and negative mean no resolvable value; a
        resolved 0 stays a real value because ``collect "0"`` is committed
        content 727 of 778 items record."""
        self.assertEqual(capture.config_collect_amount(905), 20)
        self.assertEqual(capture.config_collect_type(905), "w")
        self.assertEqual(capture.config_collect_xp(905), 1)
        self.assertEqual(capture.config_max_collects(905), 0)
        # An id the config does not resolve has no attribute at all.
        for resolver in (
            capture.config_collect_amount,
            capture.config_collect_type,
            capture.config_collect_xp,
            capture.config_max_collects,
        ):
            with self.subTest(resolver=resolver.__name__):
                self.assertIsNone(resolver(999999))
                self.assertIsNone(resolver(-1))
        # ``collect "0"`` is a real resolved 0, not a refusal: the endpoint
        # turns it into ``no_income``, upstream of the derivation.
        self.assertEqual(capture.config_collect_amount(22), 0)
        self.assertEqual(capture.config_collect_xp(22), 0)
        self.assertEqual(capture.config_collect_amount(23), 0)

    def test_the_fixture_batch_is_the_derived_single_command(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(
            built["commands"],
            [[0, "collect", [2], [0, 3, 0, 60, 0, 0, 0, 0]]],
        )
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        capture.verify_envelope(built)

    def test_the_batch_is_composed_from_the_shared_derivation(self) -> None:
        """The captured request and the endpoint can never drift apart."""
        built = capture.build_fixture_envelope(ts=1700000000)
        payout = envelope_mod.payout_for(
            amount=capture.FIXTURE_COLLECT_AMOUNT,
            resource_type=capture.FIXTURE_COLLECT_TYPE,
            experience=capture.FIXTURE_COLLECT_XP,
            tier=capture.FIXTURE_EXPECTED_TIER,
            ladder=(capture.FIXTURE_LADDER_MINUTES, capture.FIXTURE_LADDER_MULTIPLIERS),
        )
        rebuilt = envelope_mod.build_envelope(
            item_index=capture.FIXTURE_ITEM_INDEX, vector=payout, ts=1700000000
        )
        self.assertEqual(built, rebuilt)
        self.assertEqual(built["commands"][0][3], payout)
        # The top rung is the one every corpus row reaches, because every
        # row's item[3] is 0.
        self.assertEqual(
            envelope_mod.tier_for(2 ** 31, LADDER), capture.FIXTURE_EXPECTED_TIER
        )

    def test_protected_fixtures_are_the_eight_committed_ones(self) -> None:
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
                "tests/fixtures/godot-building-construction",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        cases = {
            "no command": lambda env: env["commands"].pop(),
            "two commands": lambda env: env["commands"].append(list(env["commands"][0])),
            "another index": lambda env: env["commands"][0][2].__setitem__(0, 11),
            "an extra argument": lambda env: env["commands"][0][2].append(0),
            "another command name": lambda env: env["commands"][0].__setitem__(1, "buy"),
            "a neutral vector": lambda env: env["commands"][0][3].__setitem__(3, 0),
            "a client-sent amount": lambda env: env["commands"][0][3].__setitem__(3, 1),
            "a filled mana slot": lambda env: env["commands"][0][3].__setitem__(7, 1),
            "a filled unknown slot": lambda env: env["commands"][0][3].__setitem__(0, 1),
            "a gold payout": lambda env: env["commands"][0][3].__setitem__(2, 60),
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

    def test_both_probes_are_recorded_with_their_evidence(self) -> None:
        """Task 1.3: probe 1 establishes the branch's single write and the
        verbatim vector; probe 2 is the evidence for design D5's refusal."""
        self.assertEqual(len(capture.PROBES), 2)
        first, second = capture.PROBES
        self.assertEqual(first["probe"], 1)
        self.assertEqual(first["command"], "collect(2)")
        self.assertEqual(first["vector"], [0, 7, -5, 60, 0, 0, 0, 0])
        self.assertIn("ONLY the row's timestamp", first["established"])
        self.assertIn("verbatim", first["established"])
        self.assertIn("command.py:136-147", first["established"])
        self.assertIn("clamp did not bite", first["clamp_not_exercised"])
        self.assertEqual(second["probe"], 2)
        self.assertIn("activate(11, 3600)", second["command"])
        self.assertIn("cp", second["row_after"])
        self.assertIn("SURVIVED", second["established"])
        self.assertIn("construction_in_progress", second["consequence"])
        self.assertIn("never observed", second["not_observed_from_client"])

    def test_time_dependent_fields_are_named_as_json_pointers(self) -> None:
        """The capture publishes exactly which leaves move between runs."""
        source = Path(capture.__file__).read_text(encoding="utf-8")
        self.assertIn('"time_dependent_fields"', source)
        self.assertIn("/maps/0/items/%d/3", source)
        self.assertIn("/transaction/row_after/3", source)
        self.assertIn("/transaction/steps/1/save_after_sha256", source)
        self.assertIn("/executed_at_utc in capture-manifest.json", source)

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        before = json.loads(json.dumps(SEED))
        after = derived_collect_state()
        self.assertEqual(
            before["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)],
            [capture.FIXTURE_ITEM_ID, capture.FIXTURE_X, capture.FIXTURE_Y, 0, 0, [], {}, 1],
        )
        capture.verify_transaction(before, after, built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        key = str(capture.FIXTURE_ITEM_INDEX)

        def destroy() -> Dict[str, Any]:
            document = derived_collect_state()
            document["maps"][0]["items"].pop(key)
            return document

        def remove_another() -> Dict[str, Any]:
            document = derived_collect_state()
            document["maps"][0]["items"].pop("12")
            return document

        def change_another() -> Dict[str, Any]:
            document = derived_collect_state()
            document["maps"][0]["items"]["12"] = [23, 46, 49, 0, 0, [], {}, 1]
            return document

        cases: Dict[str, Any] = {
            "the row was destroyed": destroy,
            "another row was removed": remove_another,
            "another row changed": change_another,
            "a wrong item id": lambda: derived_collect_state(item=930),
            "a different cell": lambda: derived_collect_state(x=54),
            "a non-wall-clock collection time": lambda: derived_collect_state(
                timestamp=0
            ),
            "a collection time that did not move forward": lambda: derived_collect_state(
                timestamp=-1
            ),
            "construction state appeared": lambda: derived_collect_state(
                attr={"cp": 5}
            ),
            "a changed player team": lambda: derived_collect_state(player=0),
            "a changed orientation": lambda: derived_collect_state(orientation=3),
            "a stored-unit payload appeared": lambda: derived_collect_state(
                store=[1]
            ),
            "storage changed": lambda: derived_collect_state(store_map={"905": 1}),
            "wood did not move": lambda: derived_collect_state(wood=2000),
            "wood moved by the wrong amount": lambda: derived_collect_state(wood=2059),
            "gold moved": lambda: derived_collect_state(gold=2001),
            "xp did not move": lambda: derived_collect_state(xp=4),
            "xp moved by the wrong amount": lambda: derived_collect_state(xp=6),
            "a private-state field changed": lambda: derived_collect_state(bought=[905]),
            "deadHeroes changed": lambda: derived_collect_state(
                dead_heroes={"905": True}
            ),
            "mana changed": lambda: derived_collect_state(mana=3),
        }
        for label, build in sorted(cases.items()):
            with self.subTest(case=label):
                before = json.loads(json.dumps(SEED))
                after = build()
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


def derived_collect_state(
    item: int = capture.FIXTURE_ITEM_ID,
    x: int = capture.FIXTURE_X,
    y: int = capture.FIXTURE_Y,
    timestamp: int = 1790000000,
    orientation: int = 0,
    store: Optional[list] = None,
    attr: Optional[dict] = None,
    player: int = 1,
    store_map: Optional[dict] = None,
    wood: int = 2060,
    xp: int = 7,
    gold: Optional[int] = None,
    bought: Optional[list] = None,
    dead_heroes: Optional[dict] = None,
    mana: Optional[int] = None,
) -> Dict[str, Any]:
    """A fresh-save copy carrying the derived collection, overridable.

    Defaults are the executed outcome, so every override in the mismatch table
    names exactly one deviation from it.  ``wood`` and ``xp`` default to the
    documented post-values (``2000 + 60`` and ``4 + 3``) rather than to the
    seed's, and a mismatch case passes its own value to name one deviation.
    """
    document = json.loads(json.dumps(SEED))
    document["maps"][0]["items"][str(capture.FIXTURE_ITEM_INDEX)] = [
        item,
        x,
        y,
        timestamp,
        orientation,
        list(store) if store is not None else [],
        dict(attr) if attr is not None else {},
        player,
    ]
    document["maps"][0]["wood"] = wood
    document["maps"][0]["xp"] = xp
    if bought is not None:
        document["privateState"]["boughtUnits"] = list(bought)
    if dead_heroes is not None:
        document["privateState"]["deadHeroes"] = dead_heroes
    if store_map is not None:
        document["maps"][0]["store"] = store_map
    if wood is not None:
        document["maps"][0]["wood"] = wood
    if xp is not None:
        document["maps"][0]["xp"] = xp
    if gold is not None:
        document["maps"][0]["gold"] = gold
    if mana is not None:
        document["privateState"]["mana"] = mana
    return document


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
