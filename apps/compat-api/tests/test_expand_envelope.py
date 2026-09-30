#!/usr/bin/env python3
"""Offline unit tests for the expand envelope derivation and the expand
capture tool's published contract (OpenSpec tasks 2.1 / 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the
pinned interpreter.  The real-config cross-checks pin the fixture intent, the
committed ``expansion_prices`` schedule's length, its free indexes, the
saturated rows, the committed row for the fixture id, the derived all-zero
debit, and the six always-zero vector slots against the bytes the legacy server
actually loads, and the shared-helper round trip proves the single-command
envelope travels through the placement module's unchanged serialization.

The four derived decisions are asserted as behavior, not comments:

* **D1** the price comes from the 98-entry positional ``expansion_prices``
  schedule, indexed by the expansion id itself — an id outside it is ``None``
  and never priced, which is the evidence for the endpoint's range guard;
* **D2** the schedule's gold-named ``coins`` is the client's ``gold`` and is
  **negated** into slot 2 while ``cash`` is negated into slot 6, and the six
  slots no expansion price names are always zero;
* **D3** a row recording a positive ``neighbors`` or ``inventory_qte`` is
  reported by :func:`unmet_requirements` so the endpoint can refuse it before
  the dispatcher runs, and the module itself has no way to *satisfy* one;
* **D6** the vector is a **debit**, so :func:`validate_vector` refuses any
  positive entry — a positive slot is a client-trusted mint and a negative
  magnitude is a client-trusted burn, which is exactly what the endpoint's
  value-level post-execution proof exists to catch.
"""

from __future__ import annotations

import ast
import json
import textwrap
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import capture_expand_fixture as capture
import expand_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]

# The committed schedule, read from the committed config here rather than
# hardcoded a second time.
SCHEDULE: Any = CONFIG["expansion_prices"]


def free_row(coins: int = 0, cash: int = 0) -> Dict[str, int]:
    """A committed-shaped row with no requirement, for the derivation tests."""
    return {"coins": coins, "cash": cash, "neighbors": 0, "inventory_qte": 0}


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
        # The expand derivation is additive: the delivered siblings keep their
        # own, and the collect module's helpers are untouched.
        self.assertFalse(hasattr(placement_envelope, "resource_vector_for"))
        self.assertFalse(hasattr(placement_envelope, "unmet_requirements"))
        self.assertFalse(hasattr(placement_envelope, "COLLECT_RESOURCE_SLOTS"))
        self.assertFalse(hasattr(placement_envelope, "DEBIT_SLOTS"))

    def test_the_command_is_the_documented_legacy_name(self) -> None:
        # command.py:211-216, and the expand row of docs/legacy-protocol/commands.json.
        self.assertEqual(envelope_mod.EXPAND_COMMAND, "expand")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)
        self.assertEqual(envelope_mod.GOLD_SLOT, 2)
        self.assertEqual(envelope_mod.CASH_SLOT, 6)

    def test_the_debit_mapping_is_exactly_the_two_committed_price_fields(self) -> None:
        """Design D2: only ``coins`` and ``cash`` are a price, and each is
        negated into its own server slot."""
        self.assertEqual(
            envelope_mod.DEBIT_SLOTS,
            {"coins": envelope_mod.GOLD_SLOT, "cash": envelope_mod.CASH_SLOT},
        )
        self.assertEqual(
            envelope_mod.PRICE_FIELDS, ("coins", "cash")
        )
        self.assertEqual(envelope_mod.COMMITTED_ROW_FIELDS, ("coins", "cash", "neighbors", "inventory_qte"))
        # The two requirement fields are NOT price fields: applying one would
        # be the invented requirement rule design D3 refuses.
        self.assertEqual(
            envelope_mod.REQUIREMENT_FIELDS, ("neighbors", "inventory_qte")
        )
        for field in envelope_mod.REQUIREMENT_FIELDS:
            with self.subTest(field=field):
                self.assertNotIn(field, envelope_mod.PRICE_FIELDS)
                self.assertNotIn(field, envelope_mod.DEBIT_SLOTS)

    def test_exactly_six_slots_can_never_be_filled(self) -> None:
        """Slot 0 is unread and no expansion price names experience, wood, oil,
        steel, or mana, so slots 0/1/3/4/5/7 are structurally zero."""
        self.assertEqual(
            envelope_mod.ALWAYS_ZERO_SLOTS, (0, 1, 3, 4, 5, 7)
        )
        self.assertEqual(len(envelope_mod.ALWAYS_ZERO_SLOTS), 6)
        complement = [
            index
            for index in range(envelope_mod.RESOURCE_VECTOR_SLOTS)
            if index not in envelope_mod.ALWAYS_ZERO_SLOTS
        ]
        self.assertEqual(complement, [2, 6])
        self.assertEqual(sorted(envelope_mod.DEBIT_SLOTS.values()), complement)

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.expand_envelope, envelope_mod)
        self.assertEqual(
            compat_service.ERROR_MISSING_EXPANSION_ID, "missing_expansion_id"
        )
        self.assertEqual(
            compat_service.ERROR_INVALID_EXPANSION_ID, "invalid_expansion_id"
        )
        self.assertEqual(
            compat_service.ERROR_UNKNOWN_EXPANSION_ID, "unknown_expansion_id"
        )
        self.assertEqual(compat_service.ERROR_ALREADY_EXPANDED, "already_expanded")
        self.assertEqual(
            compat_service.ERROR_EXPANSION_REQUIREMENTS_UNMET,
            "expansion_requirements_unmet",
        )
        self.assertEqual(
            compat_service.ERROR_INSUFFICIENT_RESOURCES, "insufficient_resources"
        )


def _dedented(block: str) -> str:
    """A route slice dedented so it parses as a standalone module."""
    return textwrap.dedent(block.lstrip("\n"))


class StrictIntTests(unittest.TestCase):
    def test_ints_but_not_bools_or_other_types(self) -> None:
        self.assertTrue(envelope_mod.is_strict_int(0))
        self.assertTrue(envelope_mod.is_strict_int(4))
        self.assertFalse(envelope_mod.is_strict_int(True))
        self.assertFalse(envelope_mod.is_strict_int("0"))
        self.assertFalse(envelope_mod.is_strict_int(4.0))
        self.assertFalse(envelope_mod.is_strict_int(None))


class ScheduleLengthTests(unittest.TestCase):
    def test_the_committed_schedule_resolves_to_98(self) -> None:
        self.assertEqual(envelope_mod.schedule_length(SCHEDULE), 98)
        self.assertEqual(
            envelope_mod.schedule_length(SCHEDULE), envelope_mod.COMMITTED_SCHEDULE_LENGTH
        )

    def test_only_a_non_empty_sequence_is_a_schedule(self) -> None:
        """A string, a mapping, an empty sequence, or a non-sequence is "not a
        schedule" and is reported by the caller's own refusal, never coerced
        into a length."""
        for bad in (None, (), [], "coins", b"coins", {"0": {}}, 42, 4.0, True):
            with self.subTest(schedule=bad):
                self.assertIsNone(envelope_mod.schedule_length(bad))
        self.assertEqual(envelope_mod.schedule_length([{}]), 1)
        self.assertEqual(envelope_mod.schedule_length(({}, {})), 2)


class PriceForTests(unittest.TestCase):
    """Design D1: the id indexes the positional schedule, out of range is None."""

    def test_each_index_resolves_to_its_own_committed_row(self) -> None:
        for index, row in enumerate(SCHEDULE):
            with self.subTest(index=index):
                self.assertEqual(envelope_mod.price_for(index, SCHEDULE), row)

    def test_the_corpus_owned_ids_are_all_valid_indexes(self) -> None:
        """The decisive D1 evidence, asserted: the corpus's own
        ``[35, 36, 45, 46]`` indexes the 98-entry table."""
        owned = envelope_mod.COMMITTED_OWNED_EXPANSIONS
        self.assertEqual(list(owned), [35, 36, 45, 46])
        self.assertEqual(len(owned), len(FRESH_MAP["expansions"]))
        for expansion_id in owned:
            with self.subTest(expansion_id=expansion_id):
                self.assertIsNotNone(
                    envelope_mod.price_for(expansion_id, SCHEDULE)
                )

    def test_the_owned_ids_are_neither_four_entry_indexes_nor_levels(self) -> None:
        """…and they are NOT valid ``town_prices`` / ``map_prices`` indexes and
        NOT a level set, which is what rules those readings out."""
        for name in ("town_prices", "map_prices"):
            with self.subTest(schedule=name):
                other = CONFIG[name]
                self.assertEqual(len(other), 4)
                for expansion_id in envelope_mod.COMMITTED_OWNED_EXPANSIONS:
                    self.assertGreaterEqual(expansion_id, len(other))
        levels = sorted(
            int(entry["level"]) for entry in CONFIG["town_prices"]
        )
        self.assertEqual(levels, [15, 25, 35, 45])
        owned = set(envelope_mod.COMMITTED_OWNED_EXPANSIONS)
        # 35 and 45 are levels; 36 and 46 are not, so the set as a whole is
        # not a level set.
        self.assertEqual(owned & set(levels), {35, 45})
        self.assertNotIn(36, levels)
        self.assertNotIn(46, levels)

    def test_an_out_of_range_id_is_none_and_never_priced(self) -> None:
        """The evidence for the endpoint's range guard: the legacy server
        accepted ``expand(999)`` answering success, so the service must not
        price an id the table does not cover."""
        for bad in (98, 99, 999, 10 ** 9, -1, -98, -(10 ** 9)):
            with self.subTest(expansion_id=bad):
                self.assertIsNone(envelope_mod.price_for(bad, SCHEDULE))
        self.assertEqual(len(SCHEDULE), 98)
        self.assertIsNotNone(envelope_mod.price_for(97, SCHEDULE))
        self.assertIsNone(envelope_mod.price_for(98, SCHEDULE))

    def test_a_non_integer_id_fails_closed(self) -> None:
        """Legacy would raise ``int("abc")`` out of the branch and answer an
        unhandled HTTP 500, so this derivation refuses it."""
        for bad in (True, "0", 0.0, None, [0], {"id": 0}, 1.0):
            with self.subTest(expansion_id=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.price_for(bad, SCHEDULE)
                self.assertEqual(caught.exception.code, "invalid_expansion_id")

    def test_a_schedule_that_is_not_a_sequence_fails_closed(self) -> None:
        for bad in (None, [], "coins", {"0": free_row()}):
            with self.subTest(schedule=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.assertEqual(
                        envelope_mod.price_for(0, bad),
                        envelope_mod.price_for(0, bad),
                    )
                self.assertEqual(caught.exception.code, "invalid_price")

    def test_the_row_is_a_copy_and_is_never_coerced(self) -> None:
        row = envelope_mod.price_for(0, SCHEDULE)
        self.assertIsNot(row, SCHEDULE[0])
        row["coins"] = 999999  # type: ignore[index]
        self.assertEqual(envelope_mod.price_for(0, SCHEDULE)["coins"], 0)  # type: ignore[index]
        self.assertEqual(SCHEDULE[0]["coins"], 0)

    def test_a_non_mapping_row_is_returned_verbatim_for_the_derivation(self) -> None:
        """The accessor never coerces; the shape refusal lives in the helpers
        that read the row, so the row is handed on unchanged."""
        for bad_row in ("0", 42, None, ["coins", 0]):
            with self.subTest(row=bad_row):
                self.assertEqual(
                    envelope_mod.price_for(0, [bad_row]), bad_row
                )
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.unmet_requirements(bad_row)
                self.assertEqual(caught.exception.code, "invalid_price")
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.resource_vector_for(bad_row)
                self.assertEqual(caught.exception.code, "invalid_price")


class UnmetRequirementsTests(unittest.TestCase):
    """Design D3: an unevaluable requirement is reported, never invented."""

    def test_a_row_with_no_requirement_is_purchasable(self) -> None:
        for coins, cash in ((0, 0), (2500, 5), (100000, 20)):
            with self.subTest(coins=coins, cash=cash):
                self.assertEqual(
                    envelope_mod.unmet_requirements(free_row(coins, cash)), []
                )

    def test_a_positive_neighbor_requirement_is_reported(self) -> None:
        row = free_row(2500, 5)
        row["neighbors"] = 1
        self.assertEqual(envelope_mod.unmet_requirements(row), ["neighbors"])

    def test_a_positive_inventory_requirement_is_reported(self) -> None:
        row = free_row(2500, 5)
        row["inventory_qte"] = 30
        self.assertEqual(
            envelope_mod.unmet_requirements(row), ["inventory_qte"]
        )

    def test_both_requirements_are_reported_in_the_committed_order(self) -> None:
        row = {"coins": 100000, "cash": 20, "neighbors": 15, "inventory_qte": 30}
        self.assertEqual(
            envelope_mod.unmet_requirements(row), ["neighbors", "inventory_qte"]
        )
        # Order is stable regardless of the mapping's insertion order.
        reordered = {
            "inventory_qte": 30,
            "neighbors": 15,
            "cash": 20,
            "coins": 100000,
        }
        self.assertEqual(
            envelope_mod.unmet_requirements(reordered), ["neighbors", "inventory_qte"]
        )

    def test_a_negative_requirement_is_not_treated_as_satisfied(self) -> None:
        """A negative requirement is content this contract cannot read as a
        zero, so it fails closed rather than being treated as no requirement."""
        for field in envelope_mod.REQUIREMENT_FIELDS:
            with self.subTest(field=field):
                row = free_row()
                row[field] = -1
                self.assertEqual(envelope_mod.unmet_requirements(row), [field])

    def test_an_unusable_requirement_value_fails_closed(self) -> None:
        for bad in ("1", 1.0, True, [1], {"count": 1}):
            with self.subTest(value=bad):
                row = free_row()
                row["neighbors"] = bad
                self.assertEqual(
                    envelope_mod.unmet_requirements(row), ["neighbors"]
                )

    def test_an_absent_or_null_requirement_is_not_a_requirement(self) -> None:
        for row in (
            {"coins": 0, "cash": 0},
            {"coins": 0, "cash": 0, "neighbors": None, "inventory_qte": None},
        ):
            with self.subTest(row=sorted(row)):
                self.assertEqual(envelope_mod.unmet_requirements(row), [])

    def test_a_row_that_is_not_a_mapping_fails_closed(self) -> None:
        for bad in ("0", 42, None, ["coins"], 0.0, True):
            with self.subTest(row=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.unmet_requirements(bad)
                self.assertEqual(caught.exception.code, "invalid_price")

    def test_the_corpus_consequence_is_true_of_the_real_schedule(self) -> None:
        """94 of the 98 committed rows record a requirement — including every
        id the corpus owns — so the only purchasable entries are indexes 0..3.
        Stated rather than worked around, and asserted here."""
        blocked = [
            index
            for index, row in enumerate(SCHEDULE)
            if envelope_mod.unmet_requirements(row)
        ]
        self.assertEqual(len(blocked), 94)
        self.assertEqual(blocked, [index for index in range(98) if index not in (0, 1, 2, 3)])
        for owned in envelope_mod.COMMITTED_OWNED_EXPANSIONS:
            with self.subTest(expansion_id=owned):
                row = envelope_mod.price_for(owned, SCHEDULE)
                self.assertEqual(
                    envelope_mod.unmet_requirements(row),
                    ["neighbors", "inventory_qte"],
                )
                self.assertEqual(row["neighbors"], 15)
                self.assertEqual(row["inventory_qte"], 30)
        for free in envelope_mod.COMMITTED_FREE_INDEXES:
            with self.subTest(expansion_id=free):
                self.assertEqual(
                    envelope_mod.unmet_requirements(
                        envelope_mod.price_for(free, SCHEDULE)
                    ),
                    [],
                )
        self.assertEqual(
            tuple(envelope_mod.COMMITTED_FREE_INDEXES), (0, 1, 2, 3)
        )


class ResourceVectorTests(unittest.TestCase):
    """Design D2: the derived 8-slot DEBIT."""

    def test_a_free_row_derives_the_all_zero_vector(self) -> None:
        vector = envelope_mod.resource_vector_for(free_row())
        self.assertEqual(vector, [0] * 8)
        self.assertEqual(len(vector), envelope_mod.RESOURCE_VECTOR_SLOTS)
        # A zero-cost row is LEGAL, not a refusal.
        for index in envelope_mod.COMMITTED_FREE_INDEXES:
            with self.subTest(expansion_id=index):
                self.assertEqual(
                    envelope_mod.resource_vector_for(
                        envelope_mod.price_for(index, SCHEDULE)
                    ),
                    [0] * 8,
                )

    def test_a_priced_row_derives_a_negative_gold_and_cash_debit(self) -> None:
        """The debit's shape for a row priced ``coins C, cash K`` is
        ``[0, 0, -C, 0, 0, 0, -K, 0]``."""
        for index in range(4, 98):
            with self.subTest(index=index):
                row = envelope_mod.price_for(index, SCHEDULE)
                vector = envelope_mod.resource_vector_for(row)
                self.assertEqual(vector[envelope_mod.GOLD_SLOT], -row["coins"])
                self.assertEqual(vector[envelope_mod.CASH_SLOT], -row["cash"])
                self.assertEqual(len(vector), 8)

    def test_the_cheapest_priced_row_debits_2500_gold_and_5_cash(self) -> None:
        self.assertEqual(
            envelope_mod.resource_vector_for(
                envelope_mod.price_for(4, SCHEDULE)
            ),
            [0, 0, -2500, 0, 0, 0, -5, 0],
        )
        self.assertEqual(
            envelope_mod.resource_vector_for(
                envelope_mod.price_for(5, SCHEDULE)
            ),
            [0, 0, -5000, 0, 0, 0, -8, 0],
        )

    def test_the_saturated_rows_debit_100000_gold_and_20_cash(self) -> None:
        for index in (14, 33, 35, 36, 45, 46, 97):
            with self.subTest(index=index):
                self.assertEqual(
                    envelope_mod.resource_vector_for(
                        envelope_mod.price_for(index, SCHEDULE)
                    ),
                    [0, 0, -100000, 0, 0, 0, -20, 0],
                )

    def test_every_slot_that_must_stay_zero_stays_zero(self) -> None:
        """Across the whole committed schedule, on a priced and a free row."""
        for index in range(len(SCHEDULE)):
            with self.subTest(index=index):
                vector = envelope_mod.resource_vector_for(
                    envelope_mod.price_for(index, SCHEDULE)
                )
                for slot in envelope_mod.ALWAYS_ZERO_SLOTS:
                    self.assertEqual(vector[slot], 0)
                for slot, value in enumerate(vector):
                    self.assertLessEqual(value, 0)

    def test_only_the_two_named_slots_can_be_non_zero(self) -> None:
        movable = sorted(envelope_mod.DEBIT_SLOTS.values())
        for index in range(len(SCHEDULE)):
            with self.subTest(index=index):
                vector = envelope_mod.resource_vector_for(
                    envelope_mod.price_for(index, SCHEDULE)
                )
                paying = [slot for slot, value in enumerate(vector) if value]
                self.assertTrue(set(paying) <= set(movable))

    def test_a_cash_only_row_lands_in_the_cash_slot_alone(self) -> None:
        self.assertEqual(
            envelope_mod.resource_vector_for(free_row(0, 20)),
            [0, 0, 0, 0, 0, 0, -20, 0],
        )

    def test_a_gold_only_row_lands_in_the_gold_slot_alone(self) -> None:
        self.assertEqual(
            envelope_mod.resource_vector_for(free_row(100000, 0)),
            [0, 0, -100000, 0, 0, 0, 0, 0],
        )

    def test_the_requirement_fields_are_never_applied_as_a_price(self) -> None:
        """A row whose requirements are huge still debits only its price: the
        requirements are the endpoint's refusal, not a derived cost."""
        row = {
            "coins": 2500,
            "cash": 5,
            "neighbors": 15,
            "inventory_qte": 30,
        }
        self.assertEqual(
            envelope_mod.resource_vector_for(row),
            [0, 0, -2500, 0, 0, 0, -5, 0],
        )
        self.assertEqual(
            envelope_mod.unmet_requirements(row), ["neighbors", "inventory_qte"]
        )

    def test_a_missing_cost_fails_closed(self) -> None:
        for row in (
            {"cash": 5, "neighbors": 0, "inventory_qte": 0},
            {"coins": 2500, "neighbors": 0, "inventory_qte": 0},
            {"neighbors": 0, "inventory_qte": 0},
            {},
        ):
            with self.subTest(row=sorted(row)):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.resource_vector_for(row)
                self.assertEqual(caught.exception.code, "invalid_cost")

    def test_a_non_integer_or_negative_cost_fails_closed(self) -> None:
        """A negative cost would put a POSITIVE entry on the legacy vector — a
        client-trusted mint — so it is refused rather than sent."""
        for field in envelope_mod.PRICE_FIELDS:
            for bad in (True, "0", 0.0, None, [0], {"coins": 0}, -1, -(10 ** 9)):
                with self.subTest(field=field, cost=bad):
                    row = free_row()
                    row[field] = bad
                    with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                        envelope_mod.resource_vector_for(row)
                    self.assertEqual(caught.exception.code, "invalid_cost")

    def test_no_committed_row_can_produce_a_non_debit(self) -> None:
        """The whole-table sweep: no committed row can ever mint a resource,
        because every committed cost is a non-negative integer."""
        for index in range(len(SCHEDULE)):
            with self.subTest(index=index):
                vector = envelope_mod.resource_vector_for(
                    envelope_mod.price_for(index, SCHEDULE)
                )
                for slot, value in enumerate(vector):
                    self.assertIsInstance(value, int)
                    self.assertNotIsInstance(value, bool)
                    self.assertLessEqual(value, 0)

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.resource_vector_for(free_row(2500, 5))
        first[envelope_mod.GOLD_SLOT] = -1
        second = envelope_mod.resource_vector_for(free_row(2500, 5))
        self.assertEqual(second[envelope_mod.GOLD_SLOT], -2500)

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.resource_vector_for({"coins": "SECRET", "cash": 0})
        message = str(caught.exception)
        self.assertIn("coins", message)
        self.assertNotIn("0000", message)  # no save ids leak into an error


class ValidateVectorTests(unittest.TestCase):
    """The vector is a DEBIT, so a positive slot is refused outright."""

    def test_a_valid_debit_passes(self) -> None:
        for vector in (
            [0] * 8,
            [0, 0, -2500, 0, 0, 0, -5, 0],
            [0, 0, -100000, 0, 0, 0, -20, 0],
        ):
            with self.subTest(vector=vector):
                self.assertEqual(envelope_mod.validate_vector(vector), vector)

    def test_a_positive_slot_is_refused(self) -> None:
        """A positive entry is a client-trusted mint; the clamp's reachability
        and design D6's refusal exist precisely so a wrong price can never be
        sent as one."""
        for slot in range(8):
            vector = [0] * 8
            vector[slot] = 1
            with self.subTest(slot=slot):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.validate_vector(vector)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_an_always_zero_slot_filled_is_refused(self) -> None:
        for slot in envelope_mod.ALWAYS_ZERO_SLOTS:
            vector = [0] * 8
            vector[slot] = -1
            with self.subTest(slot=slot):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.validate_vector(vector)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_a_malformed_vector_fails_closed(self) -> None:
        cases: List[Any] = [
            None,
            [0] * 7,
            [0] * 9,
            "00000000",
            (0,) * 8,
            {"vector": [0] * 8},
            [0, 3.0, 0, 0, 0, 0, 0, 0],  # a float slot
            [0, True, 0, 0, 0, 0, 0, 0],  # a bool slot
        ]
        for vector in cases:
            with self.subTest(vector=vector):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.validate_vector(vector)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_validation_returns_a_copy(self) -> None:
        vector = [0, 0, -2500, 0, 0, 0, -5, 0]
        checked = envelope_mod.validate_vector(vector)
        self.assertIsNot(checked, vector)
        checked[envelope_mod.GOLD_SLOT] = -1
        self.assertEqual(vector[envelope_mod.GOLD_SLOT], -2500)


class BuildEnvelopeTests(unittest.TestCase):
    """The six keys and exactly one command, with the derived debit."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        arguments: Dict[str, Any] = {
            "expansion_id": capture.FIXTURE_EXPANSION_ID,
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

    def test_the_batch_carries_exactly_one_expand_command(self) -> None:
        commands = self.build()["commands"]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0], 0)
        self.assertEqual(commands[0][1], "expand")

    def test_the_argument_list_is_exactly_the_one_the_branch_reads(self) -> None:
        # command.py:212 binds a single positional arg.
        args = self.build()["commands"][0][2]
        self.assertEqual(args, [capture.FIXTURE_EXPANSION_ID])
        self.assertEqual(len(args), 1)

    def test_the_command_carries_the_derived_debit_verbatim(self) -> None:
        self.assertEqual(
            self.build()["commands"][0][3], capture.FIXTURE_EXPECTED_VECTOR
        )
        priced = envelope_mod.build_envelope(
            expansion_id=4,
            vector=envelope_mod.resource_vector_for(
                envelope_mod.price_for(4, SCHEDULE)
            ),
            ts=1700000000,
        )
        self.assertEqual(priced["commands"][0][3], [0, 0, -2500, 0, 0, 0, -5, 0])

    def test_any_integer_id_is_accepted(self) -> None:
        """Range and ownership are the endpoint's job, not the derivation's:
        legacy's ``expand`` appends whatever int it is given."""
        for expansion_id in (0, 1, 3, 35, 97, 999, 10 ** 9, -1):
            with self.subTest(expansion_id=expansion_id):
                self.assertEqual(
                    self.build(expansion_id=expansion_id)["commands"][0][2],
                    [expansion_id],
                )

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = envelope_mod.build_envelope(
            expansion_id=capture.FIXTURE_EXPANSION_ID,
            vector=list(capture.FIXTURE_EXPECTED_VECTOR),
        )
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_a_non_integer_id_fails_closed(self) -> None:
        for bad in (True, "0", 0.0, None, [0], {"id": 0}):
            with self.subTest(expansion_id=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(expansion_id=bad)
                self.assertEqual(caught.exception.code, "invalid_expansion_id")

    def test_a_bad_timestamp_fails_closed(self) -> None:
        for bad in (-1, "1700000000", True, 1700000000.0):
            with self.subTest(ts=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(ts=bad)
                self.assertEqual(caught.exception.code, "invalid_timestamp")

    def test_a_malformed_or_minting_vector_fails_closed(self) -> None:
        cases: List[Any] = [
            None,
            [0] * 7,
            [0] * 9,
            [0, 0, 1, 0, 0, 0, 0, 0],  # a gold mint
            [0, 0, 0, 0, 0, 0, 1, 0],  # a cash mint
            [0, 0, 0, 0, 0, 0, 0, 1],  # a mana mint
            [0, -1, 0, 0, 0, 0, 0, 0],  # a filled always-zero slot (xp)
            [0, 0, 0, 0, -1, 0, 0, 0],  # a filled always-zero slot (oil)
            [0, 0, -2500, 0, 0, 0, -5, 5],  # a filled always-zero slot (mana)
        ]
        for vector in cases:
            with self.subTest(vector=vector):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(vector=vector)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_a_named_slot_may_carry_a_debit(self) -> None:
        """The complement of the always-zero rule: slots 2 and 6 are exactly
        the two a derived debit may fill."""
        self.assertEqual(
            self.build(vector=[0, 0, -2500, 0, 0, 0, -5, 0])["commands"][0][3],
            [0, 0, -2500, 0, 0, 0, -5, 0],
        )

    def test_the_id_is_validated_before_the_vector(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(expansion_id="0", vector=[0] * 7)
        self.assertEqual(caught.exception.code, "invalid_expansion_id")


class SharedSerializationTests(unittest.TestCase):
    """The single-command envelope travels through the unchanged helpers."""

    def test_roundtrip_through_the_legacy_field_format(self) -> None:
        built = envelope_mod.build_envelope(
            expansion_id=capture.FIXTURE_EXPANSION_ID,
            vector=list(capture.FIXTURE_EXPECTED_VECTOR),
            ts=1700000000,
        )
        data = envelope_mod.data_field(built)
        self.assertEqual(len(data.split(";", 1)[0]), 64)
        self.assertEqual(data[64], ";")
        self.assertEqual(envelope_mod.parse_data_field(data), built)

    def test_serialization_is_deterministic(self) -> None:
        built = envelope_mod.build_envelope(
            expansion_id=capture.FIXTURE_EXPANSION_ID,
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
            payload["commands"],
            [[0, "expand", [0], [0, 0, 0, 0, 0, 0, 0, 0]]],
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


class NoLandEffectTests(unittest.TestCase):
    """Design D4: no terrain, grid, cell, or placement-bound logic anywhere."""

    def test_the_derivation_reads_no_grid_constant_but_the_re_export(self) -> None:
        self.assertEqual(envelope_mod.GRID_EXTENT, 100)
        self.assertTrue(envelope_mod.in_grid(0, 0))
        # ``GRID_EXTENT`` and ``in_grid`` are re-exported only to keep the
        # sibling modules' import shape identical.  The executable body of the
        # module never mentions either, which is asserted against the AST
        # rather than against the raw text (so the docstrings, which *name* the
        # gap on purpose, do not count as behaviour).
        tree = ast.parse(Path(envelope_mod.__file__).read_text(encoding="utf-8"))
        code_names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
        for forbidden in ("GRID_EXTENT", "in_grid"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)

    def test_the_module_mentions_no_land_geometry_as_behaviour(self) -> None:
        source = Path(envelope_mod.__file__).read_text(encoding="utf-8")
        # The vocabulary is named, and so is the gap, but never as behaviour.
        for token in ("terrain", "buildable", "footprint", "placement bound"):
            with self.subTest(token=token):
                self.assertIn(token, source)
        # No executable name in the module is a land/grid/cell concept, and no
        # function takes a coordinate.
        tree = ast.parse(source)
        code_names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
            elif isinstance(node, ast.arg):
                code_names.append(node.arg)
        for forbidden in (
            "terrain",
            "buildable",
            "buildable_cell",
            "footprint",
            "placement_bound",
            "grid_size",
            "cell",
            "cells",
            "x",
            "y",
            "width",
            "height",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)

    def test_the_endpoint_reads_no_land_geometry_either(self) -> None:
        """The route reads the ledger, the schedule, and the resources — and
        nothing else.  Asserted against the expand route's own AST."""
        import compat_service

        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = source[source.index("def v0_expand()"):]
        route = route[: route.index("@app.errorhandler(400)")]
        code_names: List[str] = []
        for node in ast.walk(ast.parse(_dedented(route))):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
        for forbidden in (
            "terrain",
            "buildable",
            "footprint",
            "placement_bound",
            "grid_size",
            "in_grid",
            "GRID_EXTENT",
            "cell",
            "cells",
            "x",
            "y",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)
        # …while the gap IS stated in the route's docstring.
        for named in ("No land, grid, cell, or placement-bound effect", "design D4"):
            with self.subTest(named=named):
                self.assertIn(named, route)

    def test_the_derivation_only_reads_two_committed_price_fields(self) -> None:
        """The whole committed row is read for the two prices and the two
        requirements, and nothing else exists on it to read."""
        self.assertEqual(
            sorted(envelope_mod.COMMITTED_ROW_FIELDS),
            sorted(["coins", "cash", "neighbors", "inventory_qte"]),
        )
        fields_in_rows: set = set()
        for row in SCHEDULE:
            self.assertIsInstance(row, dict)
            fields_in_rows.update(row)
        self.assertEqual(fields_in_rows, set(envelope_mod.COMMITTED_ROW_FIELDS))


class RealConfigCrossCheckTests(unittest.TestCase):
    """The committed config and seed must satisfy every closed assumption."""

    def test_the_fixture_row_is_the_committed_free_row(self) -> None:
        self.assertEqual(
            capture.config_expansion_price(capture.FIXTURE_EXPANSION_ID),
            capture.FIXTURE_PRICE,
        )
        self.assertEqual(
            envelope_mod.price_for(0, SCHEDULE), capture.FIXTURE_PRICE
        )
        self.assertEqual(
            capture.config_expansion_price(0),
            {"coins": 0, "cash": 0, "neighbors": 0, "inventory_qte": 0},
        )

    def test_the_committed_schedule_census_matches_the_investigation(self) -> None:
        """docs/legacy-town-expansion.md and the committed economy package."""
        self.assertEqual(len(SCHEDULE), 98)
        self.assertEqual(
            sorted(SCHEDULE[0]), ["cash", "coins", "inventory_qte", "neighbors"]
        )
        # Every committed field is a fully native number, never a string.
        for row in SCHEDULE:
            for field in envelope_mod.COMMITTED_ROW_FIELDS:
                self.assertIsInstance(row[field], int)
                self.assertNotIsInstance(row[field], bool)
                self.assertGreaterEqual(row[field], 0)
        for index in (0, 1, 2, 3):
            with self.subTest(index=index):
                self.assertEqual(SCHEDULE[index], capture.FIXTURE_PRICE)
        self.assertEqual(
            SCHEDULE[4], {"coins": 2500, "cash": 5, "neighbors": 1, "inventory_qte": 1}
        )
        self.assertEqual(
            SCHEDULE[5], {"coins": 5000, "cash": 8, "neighbors": 2, "inventory_qte": 2}
        )
        self.assertEqual(
            SCHEDULE[97], {"coins": 100000, "cash": 20, "neighbors": 15, "inventory_qte": 30}
        )

    def test_the_per_field_saturation_indexes(self) -> None:
        self.assertEqual(
            {
                field: next(
                    index
                    for index, row in enumerate(SCHEDULE)
                    if row[field] == SCHEDULE[-1][field]
                )
                for field in envelope_mod.COMMITTED_ROW_FIELDS
            },
            {"coins": 14, "cash": 11, "neighbors": 18, "inventory_qte": 33},
        )
        self.assertEqual(
            next(
                index
                for index, row in enumerate(SCHEDULE)
                if row == SCHEDULE[-1]
            ),
            33,
        )

    def test_the_zero_cost_set_and_the_requirement_free_set_are_the_same(self) -> None:
        zero_cost = [
            index
            for index, row in enumerate(SCHEDULE)
            if envelope_mod.resource_vector_for(row) == [0] * 8
        ]
        requirement_free = [
            index
            for index, row in enumerate(SCHEDULE)
            if not envelope_mod.unmet_requirements(row)
        ]
        self.assertEqual(zero_cost, [0, 1, 2, 3])
        self.assertEqual(requirement_free, [0, 1, 2, 3])
        self.assertEqual(zero_cost, requirement_free)

    def test_the_fresh_save_carries_the_committed_ledger(self) -> None:
        self.assertEqual(
            FRESH_MAP["expansions"], list(capture.FIXTURE_EXPECTED_EXPANSIONS_BEFORE)
        )
        self.assertEqual(
            FRESH_MAP["expansions"], list(envelope_mod.COMMITTED_OWNED_EXPANSIONS)
        )
        self.assertEqual(FRESH_MAP["level"], capture.FIXTURE_EXPECTED_LEVEL)
        self.assertEqual(
            FRESH_MAP["increasedPopulation"],
            capture.FIXTURE_EXPECTED_INCREASED_POPULATION,
        )
        self.assertNotIn("map_sizes", FRESH_MAP)
        self.assertEqual(len(FRESH_ITEMS), capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE)

    def test_the_pre_migration_save_carries_the_same_ledger(self) -> None:
        """The ledger is part of the preserved corpus, not migration damage."""
        pre = json.loads(
            (harness.REPO_ROOT / "tests" / "saves" / "fresh-player-pre-migration.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            pre["maps"][0]["expansions"],
            list(capture.FIXTURE_EXPECTED_EXPANSIONS_BEFORE),
        )

    def test_the_fresh_save_starts_with_the_resources_the_fixture_leaves_alone(
        self,
    ) -> None:
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
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_AFTER,
            capture.FIXTURE_EXPECTED_RESOURCE_BEFORE,
        )
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_DELTA,
            {"xp": 0, "gold": 0, "wood": 0, "oil": 0, "steel": 0, "cash": 0, "mana": 0},
        )

    def test_the_fixture_does_not_touch_another_fixtures_rows(self) -> None:
        """Every delivered fixture stays independently readable: an expansion
        rewrites no placement at all, so all 40 rows are untouched."""
        for key in ("2", "11", "12", "20", "21"):
            with self.subTest(key=key):
                self.assertIn(key, FRESH_ITEMS)
        # The collect/store fixture row, the construction/move row, the
        # upgrade row, and the sell row.
        self.assertEqual(int(FRESH_ITEMS["2"][0]), 905)
        self.assertEqual(int(FRESH_ITEMS["11"][0]), 22)
        self.assertEqual(int(FRESH_ITEMS["12"][0]), 23)
        self.assertEqual(int(FRESH_ITEMS["20"][0]), 22)

    def test_no_committed_branch_prices_or_validates_an_expansion(self) -> None:
        """The committed command catalog records the same: the branch only
        appends, and the catalog's own security note says the client unlocks
        any id with no verification."""
        catalog = json.loads(
            (harness.REPO_ROOT / "docs" / "legacy-protocol" / "commands.json").read_text(
                encoding="utf-8"
            )
        )
        by_name = {entry["name"]: entry for entry in catalog["commands"]}
        expand_entry = by_name["expand"]
        self.assertEqual(
            expand_entry["args"]["positional"], ["args[0] expansion (int-like)"]
        )
        self.assertEqual(expand_entry["args"]["shape"], "exactly 1 positional arg")
        self.assertEqual(
            expand_entry["state_writes"], ["map[expansions] += [int(expansion)]"]
        )
        self.assertEqual(expand_entry["state_reads"], ["map[expansions]"])
        self.assertEqual(expand_entry["classification"], "handled")
        self.assertEqual(expand_entry["domain"], "town")
        writes = " ".join(expand_entry["state_writes"])
        for absent in (
            "expansion_prices",
            "town_prices",
            "map_prices",
            "neighbors",
            "inventory_qte",
            "bought_unit_add",
            "push_dead_unit",
            "items",
        ):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, writes)
        effects = " ".join(expand_entry["resource_effects"])
        self.assertIn("client-sent deltas", effects)
        self.assertIn("clamped at zero", effects)
        security = " ".join(expand_entry["security_notes"])
        self.assertIn("no adjacency, level, or cost verification", security)
        trust = " ".join(expand_entry["client_trust"])
        self.assertIn("expansion id", trust)
        self.assertIn("resources_changed deltas", trust)


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_EXPANSION_ID, 0)
        self.assertEqual(capture.FIXTURE_PRICE, {
            "coins": 0, "cash": 0, "neighbors": 0, "inventory_qte": 0,
        })
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(capture.FIXTURE_EXPECTED_EXPANSIONS_BEFORE, [35, 36, 45, 46])
        self.assertEqual(
            capture.FIXTURE_EXPECTED_EXPANSIONS_AFTER, [35, 36, 45, 46, 0]
        )
        self.assertEqual(capture.FIXTURE_SCHEDULE_LENGTH, 98)
        self.assertEqual(capture.FIXTURE_FREE_INDEXES, (0, 1, 2, 3))
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_AFTER, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_LEVEL, 1)
        self.assertEqual(capture.FIXTURE_EXPECTED_INCREASED_POPULATION, 0)
        self.assertFalse(capture.FIXTURE_EXPECTED_MAP_SIZES_PRESENT)
        self.assertIn("expansion id 0", capture.TARGET_RULE)
        self.assertIn("none of them could have been bought", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_expand"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-expand",
        )

    def test_the_config_resolvers_apply_the_documented_rules(self) -> None:
        self.assertEqual(len(capture.config_expansion_schedule()), 98)
        self.assertEqual(
            capture.config_expansion_price(0), capture.FIXTURE_PRICE
        )
        self.assertEqual(
            capture.config_expansion_price(4),
            {"coins": 2500, "cash": 5, "neighbors": 1, "inventory_qte": 1},
        )
        # Out of range is None, never a coerced row.
        for bad in (98, 999, -1, -(10 ** 9)):
            with self.subTest(expansion_id=bad):
                self.assertIsNone(capture.config_expansion_price(bad))

    def test_the_fixture_batch_is_the_derived_single_command(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(
            built["commands"], [[0, "expand", [0], [0, 0, 0, 0, 0, 0, 0, 0]]]
        )
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        capture.verify_envelope(built)

    def test_the_batch_is_composed_from_the_shared_derivation(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        debit = envelope_mod.resource_vector_for(
            capture.config_expansion_price(capture.FIXTURE_EXPANSION_ID)
        )
        rebuilt = envelope_mod.build_envelope(
            expansion_id=capture.FIXTURE_EXPANSION_ID, vector=debit, ts=1700000000
        )
        self.assertEqual(built, rebuilt)
        self.assertEqual(built["commands"][0][3], debit)
        self.assertEqual(debit, [0] * 8)

    def test_protected_fixtures_are_the_nine_committed_ones(self) -> None:
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
                "tests/fixtures/godot-building-collect",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        cases: Dict[str, Any] = {
            "no command": lambda env: env["commands"].pop(),
            "two commands": lambda env: env["commands"].append(list(env["commands"][0])),
            "another id": lambda env: env["commands"][0][2].__setitem__(0, 1),
            "an extra argument": lambda env: env["commands"][0][2].append(0),
            "another command name": lambda env: env["commands"][0].__setitem__(1, "buy"),
            "a priced vector": lambda env: env["commands"][0][3].__setitem__(2, -2500),
            "a cash debit": lambda env: env["commands"][0][3].__setitem__(6, -5),
            "a filled unknown slot": lambda env: env["commands"][0][3].__setitem__(0, -1),
            "a filled mana slot": lambda env: env["commands"][0][3].__setitem__(7, -1),
            "a minting vector": lambda env: env["commands"][0][3].__setitem__(2, 2500),
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

    def test_all_three_probes_are_recorded_with_their_evidence(self) -> None:
        """Probe 1 establishes the single append and the clamp's reachability;
        probe 2 is the evidence for the range and duplicate guards; probe 3 for
        the structural id check."""
        self.assertEqual(len(capture.PROBES), 3)
        first, second, third = capture.PROBES
        self.assertEqual(first["probe"], 1)
        self.assertIn("expand(4)", first["commands"][0])
        self.assertIn("expand(5)", first["commands"][1])
        self.assertIn("[0,0,-5000,0,0,0,-8,0]", first["commands"][1])
        self.assertEqual(
            first["expansions_after"], [35, 36, 45, 46, 4, 5]
        )
        self.assertEqual(
            first["changed_top_level_map_keys"], ["expansions", "gold"]
        )
        self.assertIn("changes NOTHING else", first["established"])
        self.assertIn("command.py:211-216", first["established"])
        self.assertIn("clamp finally bit, for real", first["clamp_reached"])
        self.assertIn("landed on 0", first["clamp_reached"])
        self.assertEqual(second["probe"], 2)
        self.assertIn("expand(999)", second["commands"][0])
        self.assertIn("duplicate", second["commands"][1])
        self.assertIn("expand(-1)", second["commands"][2])
        self.assertIn('success', second["responses"])
        self.assertIn("NO. The server accepts 999", second["established"])
        self.assertIn("unknown_expansion_id", second["consequence"])
        self.assertIn("already_expanded", second["consequence"])
        self.assertEqual(third["probe"], 3)
        self.assertIn('int("abc")', third["response"])
        self.assertIn("unhandled HTTP 500", third["response"])
        self.assertIn("does not guard it", third["established"])
        self.assertIn("invalid_expansion_id", third["consequence"])

    def test_time_dependent_fields_are_named_and_the_state_has_none(self) -> None:
        """The manifest publishes exactly which leaves move between runs — and
        the recorded state has NO time-dependent leaf, which is stated rather
        than invented."""
        source = Path(capture.__file__).read_text(encoding="utf-8")
        self.assertIn('"time_dependent_fields"', source)
        self.assertIn('"state_leaves": []', source)
        self.assertIn("exactly these 8 paths", source)
        self.assertIn("/executed_at_utc in capture-manifest.json", source)

    def test_transaction_verification_accepts_the_derived_after_state(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        before = json.loads(json.dumps(SEED))
        after = derived_expand_state()
        capture.verify_transaction(before, after, built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        cases: Dict[str, Any] = {
            "the ledger did not grow": lambda: derived_expand_state(
                expansions=[35, 36, 45, 46]
            ),
            "the ledger grew by two": lambda: derived_expand_state(
                expansions=[35, 36, 45, 46, 0, 1]
            ),
            "the sent id was not appended": lambda: derived_expand_state(
                expansions=[35, 36, 45, 46, 1]
            ),
            "the sent id was prepended": lambda: derived_expand_state(
                expansions=[0, 35, 36, 45, 46]
            ),
            "an existing entry changed": lambda: derived_expand_state(
                expansions=[35, 36, 45, 47, 0]
            ),
            "the existing entries were reordered": lambda: derived_expand_state(
                expansions=[36, 35, 45, 46, 0]
            ),
            "the existing entries were deduplicated": lambda: derived_expand_state(
                expansions=[35, 36, 45, 0]
            ),
            "a placement row changed": lambda: derived_expand_state(
                item_cell=(54, 39)
            ),
            "a placement row was removed": lambda: derived_expand_state(
                drop_item="12"
            ),
            "a placement row appeared": lambda: derived_expand_state(
                add_item="41"
            ),
            "the map level moved": lambda: derived_expand_state(level=2),
            "the population moved": lambda: derived_expand_state(population=1),
            "the storage changed": lambda: derived_expand_state(store={"905": 1}),
            "map_sizes appeared": lambda: derived_expand_state(map_sizes=[0]),
            "a map key appeared": lambda: derived_expand_state(
                extra_map_key=("map_sizes", [0])
            ),
            "a private-state field changed": lambda: derived_expand_state(
                bought=[905]
            ),
            "deadHeroes changed": lambda: derived_expand_state(
                dead_heroes={"905": True}
            ),
            "playerInfo changed": lambda: derived_expand_state(cash=4),
            "gold moved": lambda: derived_expand_state(gold=1999),
            "cash moved": lambda: derived_expand_state(cash=4),
            "xp moved": lambda: derived_expand_state(xp=5),
            "mana moved": lambda: derived_expand_state(mana=1),
            "wood moved": lambda: derived_expand_state(wood=2001),
        }
        for label, build in sorted(cases.items()):
            with self.subTest(case=label):
                before = json.loads(json.dumps(SEED))
                after = build()
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


def derived_expand_state(
    expansions: Optional[List[int]] = None,
    item_cell: Optional[Any] = None,
    drop_item: Optional[str] = None,
    add_item: Optional[str] = None,
    level: int = 1,
    population: int = 0,
    store: Optional[Dict[str, int]] = None,
    map_sizes: Optional[List[int]] = None,
    extra_map_key: Optional[Any] = None,
    gold: int = 2000,
    cash: int = 5,
    xp: int = 4,
    mana: int = 0,
    wood: int = 2000,
    bought: Optional[List[int]] = None,
    dead_heroes: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """A fresh-save copy carrying the derived expansion, overridable.

    Defaults are the executed outcome — the ledger carrying the one appended
    id and every other byte the committed seed's — so every override in the
    mismatch table names exactly one deviation from it.
    """
    document = json.loads(json.dumps(SEED))
    first_map = document["maps"][0]
    first_map["expansions"] = list(
        expansions
        if expansions is not None
        else capture.FIXTURE_EXPECTED_EXPANSIONS_AFTER
    )
    if item_cell is not None:
        first_map["items"]["2"][1] = item_cell[0]
        first_map["items"]["2"][2] = item_cell[1]
    if drop_item is not None:
        first_map["items"].pop(drop_item, None)
    if add_item is not None:
        first_map["items"][add_item] = [22, 10, 10, 0, 0, [], {}, 1]
    first_map["level"] = level
    first_map["increasedPopulation"] = population
    if store is not None:
        first_map["store"] = dict(store)
    if map_sizes is not None:
        first_map["map_sizes"] = list(map_sizes)
    if extra_map_key is not None:
        first_map[extra_map_key[0]] = extra_map_key[1]
    first_map["gold"] = gold
    first_map["wood"] = wood
    first_map["xp"] = xp
    document["playerInfo"]["cash"] = cash
    document["privateState"]["mana"] = mana
    if bought is not None:
        document["privateState"]["boughtUnits"] = list(bought)
    if dead_heroes is not None:
        document["privateState"]["deadHeroes"] = dict(dead_heroes)
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
            "Date": "Mon, 30 Sep 2026 15:30:46 GMT",
            "Set-Cookie": "session=SESSION-TOKEN-SECRET; HttpOnly; Path=/",
            "Content-Type": "text/html; charset=utf-8",
        }
        sanitized = capture.sanitize_headers(headers)
        self.assertEqual(sanitized["Set-Cookie"], capture.REDACTED)
        self.assertEqual(sanitized["Date"], headers["Date"])
        self.assertNotIn("SESSION-TOKEN-SECRET", json.dumps(sanitized))


if __name__ == "__main__":
    unittest.main()
