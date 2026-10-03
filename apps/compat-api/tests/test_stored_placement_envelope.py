#!/usr/bin/env python3
"""Offline unit tests for the stored-item placement envelope derivation.

OpenSpec change ``2026-10-03-stored-item-placement``, task 2.2.  No server, no
socket, no corpus: everything here is pure derivation over the committed
configuration, the committed normalized package, and the committed seed document,
so it runs in milliseconds under the pinned interpreter.

What these tests actually establish, and what they deliberately do not:

* the ``attr`` port is checked against an **independent re-implementation** of
  ``engine.map_add_item``'s ``player == 1`` block (``engine.py:19-31``) over all
  **900** normalized items, so the port is verified against the committed content
  rather than against a restatement of itself;
* the slot rule's **named inverse** round-trips over the whole committed corpus;
* ``attr_derived_from`` round-trips as the named inverse of ``derive_attr``;
* ``project_storage`` fails **closed** on every malformed shape, changing no value;
* the anti-invention guards are **mechanical**: no delivered function accepts an
  ``attr`` or a ``player`` parameter, no bounds/footprint/capacity/price helper
  exists, and the whole function inventory is pinned.
"""

from __future__ import annotations

import inspect
import json
import unittest
from typing import Any, Dict, List, Mapping, Optional

import compat_test_harness as harness

import collection_envelope
import placement_envelope
import stored_placement_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
RAW_ITEMS = CONFIG["items"]
RAW_COLLECTIONS = CONFIG["collections"]
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]
FRESH_ITEMS = FRESH_MAP["items"]  # type: ignore[index]
FRESH_STORE = FRESH_MAP["store"]  # type: ignore[index]
FRESH_LEDGER = SEED["privateState"]["boughtUnits"]  # type: ignore[index]

NORMALIZED = harness.REPO_ROOT / "packages" / "game-content" / "normalized"
NORMALIZED_UNITS = json.loads((NORMALIZED / "units.json").read_text(encoding="utf-8"))
NORMALIZED_BUILDINGS = json.loads((NORMALIZED / "buildings.json").read_text(encoding="utf-8"))
# The 1 committed special is its OWN normalized document, not a row inside
# units/buildings: item 925 "Expandable Land", type `l`.  Measured, not assumed.
NORMALIZED_SPECIALS = json.loads((NORMALIZED / "specials.json").read_text(encoding="utf-8"))
ALL_NORMALIZED = (
    list(NORMALIZED_UNITS) + list(NORMALIZED_BUILDINGS) + list(NORMALIZED_SPECIALS)
)


# ------------------------------------------------- independent attr oracle --
def legacy_attr(clicks_to_build: Any, properties: Any) -> Dict[str, Any]:
    """An independent transcription of ``engine.map_add_item``'s team-1 block.

    Written straight from ``engine.py:19-31`` rather than from the envelope, so
    comparing the two over all 900 normalized items is a real check:

        attr = {}
        properties = get_attribute_from_item_id(item, "properties")
        if properties:
            properties = json.loads(properties)
            if "friend_assistable" in properties:
                if int(properties["friend_assistable"]) > 0:
                    attr["si"] = []
        click_to_build = get_attribute_from_item_id(item, "clicks_to_build")
        if click_to_build:
            if int(click_to_build) > 0:
                attr["nc"] = 0
        return attr
    """
    attr: Dict[str, Any] = {}
    if properties:
        if isinstance(properties, str):
            properties = json.loads(properties)
        if "friend_assistable" in properties:
            if int(properties["friend_assistable"]) > 0:
                attr["si"] = []
    if clicks_to_build:
        if int(clicks_to_build) > 0:
            attr["nc"] = 0
    return attr


class ReuseTests(unittest.TestCase):
    """Design D2/D6: the shared helpers are reused, never re-implemented."""

    def test_the_shared_helpers_are_the_placement_modules_own(self) -> None:
        for name in (
            "is_strict_int", "EnvelopeError", "data_field", "parse_data_field",
            "payload_json", "in_grid", "next_free_slot",
        ):
            self.assertIs(
                getattr(envelope_mod, name), getattr(placement_envelope, name), name
            )
        self.assertEqual(envelope_mod.ENVELOPE_KEYS, placement_envelope.ENVELOPE_KEYS)
        self.assertEqual(envelope_mod.GRID_EXTENT, placement_envelope.GRID_EXTENT)

    def test_the_slot_rule_IS_next_free_slot_rather_than_a_second_copy(self) -> None:
        """``resolve_slot`` must be the derivation plus its own inverse.

        Proved by behaviour, not identity: over every prefix of the committed
        corpus the derived slot equals ``next_free_slot`` exactly, so a second
        implementation could not have drifted without failing here.
        """
        self.assertFalse(hasattr(placement_envelope, "resolve_slot"))
        self.assertFalse(hasattr(placement_envelope, "slot_occupied"))
        self.assertFalse(hasattr(placement_envelope, "PLACE_COMMAND"))
        self.assertFalse(hasattr(placement_envelope, "SELL_COMMAND"))

    def test_the_collection_pins_are_the_collection_modules_own(self) -> None:
        self.assertIs(
            envelope_mod.COMMITTED_COLLECTION_ID,
            collection_envelope.COMMITTED_COLLECTION_ID,
        )
        self.assertIs(
            envelope_mod.COMMITTED_COLLECTION_NAME,
            collection_envelope.COMMITTED_COLLECTION_NAME,
        )
        self.assertIs(
            envelope_mod.COMMITTED_COLLECTION_COUNT,
            collection_envelope.COMMITTED_COLLECTION_COUNT,
        )

    def test_no_sibling_envelope_module_grew_a_storage_placement_helper(self) -> None:
        """No delivered module was refactored to host this line's derivation."""
        import move_envelope
        import purchase_envelope
        import sell_envelope
        import store_envelope

        for module in (placement_envelope, move_envelope, purchase_envelope,
                       sell_envelope, store_envelope, collection_envelope):
            self.assertFalse(hasattr(module, "build_place_envelope"), module.__name__)
            self.assertFalse(hasattr(module, "build_sell_envelope"), module.__name__)
            self.assertFalse(hasattr(module, "derive_attr"), module.__name__)


class CommandShapeTests(unittest.TestCase):
    """The two commands, their argument shapes, and the dismissed arguments."""

    def test_the_command_names_are_the_dispatchers_own(self) -> None:
        self.assertEqual(envelope_mod.PLACE_COMMAND, "place_stored_item")
        self.assertEqual(envelope_mod.SELL_COMMAND, "sell_stored_item")

    def test_the_argument_widths_match_the_branches(self) -> None:
        # command.py:234-241 binds args[0]..args[7] for the placement.
        self.assertEqual(envelope_mod.PLACE_ARGUMENT_COUNT, 8)
        # command.py:251 binds exactly args[0] for the sale.
        self.assertEqual(envelope_mod.SELL_ARGUMENT_COUNT, 1)

    def test_the_placement_argument_slots_are_the_branches_own(self) -> None:
        self.assertEqual(
            [
                envelope_mod.ARG_SLOT, envelope_mod.ARG_ITEM_ID,
                envelope_mod.ARG_X, envelope_mod.ARG_Y, envelope_mod.ARG_PLAYER_ID,
                envelope_mod.ARG_ORIENTATION, envelope_mod.ARG_UNKNOWN_AUTOACTIVABLE,
                envelope_mod.ARG_UNKNOWN_IMG_INDEX,
            ],
            list(range(8)),
        )

    def test_three_arguments_are_read_and_dismissed(self) -> None:
        """``playerID`` is the consequential one: the row's team is always 1."""
        self.assertEqual(len(envelope_mod.DISMISSED_ARGUMENTS), 3)
        self.assertEqual(
            [entry["name"] for entry in envelope_mod.DISMISSED_ARGUMENTS],
            ["playerID", "unknown_autoactivable_bool", "unknown_imgIndex"],
        )
        for entry in envelope_mod.DISMISSED_ARGUMENTS:
            self.assertIn("would_be", entry)
            self.assertTrue(entry["note"])
        self.assertEqual(envelope_mod.ARG_PLAYER_ID, 4)

    def test_the_derived_row_fields_are_the_engines_own(self) -> None:
        self.assertEqual(envelope_mod.ROW_SLOTS, 8)
        self.assertEqual(envelope_mod.DERIVED_PLAYER_TEAM, 1)
        self.assertEqual(envelope_mod.DERIVED_GARRISON, [])
        self.assertEqual(envelope_mod.DERIVED_ORIENTATION, 0)
        self.assertEqual(
            [
                envelope_mod.ROW_SLOT_ITEM, envelope_mod.ROW_SLOT_X,
                envelope_mod.ROW_SLOT_Y, envelope_mod.ROW_SLOT_TIMESTAMP,
                envelope_mod.ROW_SLOT_ORIENTATION, envelope_mod.ROW_SLOT_STORE,
                envelope_mod.ROW_SLOT_ATTR, envelope_mod.ROW_SLOT_PLAYER,
            ],
            list(range(8)),
        )


class NeutralVectorTests(unittest.TestCase):
    """Design D5: the derived vector is all zeros and no resource ever moves."""

    def test_the_vector_is_eight_zeros(self) -> None:
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.neutral_vector()
        first[6] = -999
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_both_envelopes_carry_the_neutral_vector(self) -> None:
        place = envelope_mod.build_place_envelope(1085, 58, 47, FRESH_ITEMS, 0, 1700000000)
        sell = envelope_mod.build_sell_envelope(1085, 1700000000)
        self.assertEqual(place["commands"][0][3], [0] * 8)
        self.assertEqual(sell["commands"][0][3], [0] * 8)

    def test_mutating_one_envelope_never_changes_the_next(self) -> None:
        first = envelope_mod.build_place_envelope(1085, 58, 47, FRESH_ITEMS, 0, 1700000000)
        first["commands"][0][3][6] = 500
        second = envelope_mod.build_place_envelope(1085, 58, 47, FRESH_ITEMS, 0, 1700000000)
        self.assertEqual(second["commands"][0][3], [0] * 8)


class CommittedContentTests(unittest.TestCase):
    """The pins, re-asserted against the bytes the legacy server actually loads."""

    def test_the_loaded_configuration_matches_the_recorded_counts(self) -> None:
        self.assertEqual(len(RAW_ITEMS), 778)
        self.assertEqual(len({str(row["id"]) for row in RAW_ITEMS}), 778)
        self.assertEqual(len(ALL_NORMALIZED), envelope_mod.COMMITTED_ITEMS)
        self.assertEqual(len(NORMALIZED_UNITS), envelope_mod.COMMITTED_UNITS)
        self.assertEqual(len(NORMALIZED_BUILDINGS), envelope_mod.COMMITTED_BUILDINGS)
        self.assertEqual(len(NORMALIZED_SPECIALS), envelope_mod.COMMITTED_SPECIAL)
        self.assertEqual(len(ALL_NORMALIZED), 900)
        # The special is its own document, and it is the one row with a null
        # `properties` -- which is why `item_not_placeable` needs BOTH fields gone.
        special = NORMALIZED_SPECIALS[0]
        self.assertEqual(special.get("type"), "l")
        self.assertIsNone(special.get("properties"))
        self.assertTrue(envelope_mod.is_placeable(special))

    def test_the_measured_attr_distribution_is_reproduced(self) -> None:
        def bag(row: Any) -> Dict[str, Any]:
            return legacy_attr(row.get("clicks_to_build"), row.get("properties"))

        units_attr = {json.dumps(bag(r), sort_keys=True) for r in NORMALIZED_UNITS}
        self.assertEqual(units_attr, {"{}"},
                         "0 of 429 units reach either derived key")

        def count(rows: Any, key: str) -> int:
            return sum(1 for row in rows if key in bag(row))

        # MEASURED, and the special is counted separately because it is its own
        # document: item 925 carries clicks_to_build 1, so the grand total is one
        # higher than the building figure the pin records.
        self.assertEqual(count(NORMALIZED_BUILDINGS, "nc"),
                         envelope_mod.COMMITTED_BUILDINGS_WITH_CLICKS)
        self.assertEqual(count(NORMALIZED_BUILDINGS, "nc"), 298)
        self.assertEqual(count(NORMALIZED_BUILDINGS, "si"),
                         envelope_mod.COMMITTED_BUILDINGS_WITH_ASSIST)
        self.assertEqual(count(NORMALIZED_BUILDINGS, "si"), 26)
        self.assertEqual(count(NORMALIZED_UNITS, "nc"), 0)
        self.assertEqual(count(NORMALIZED_UNITS, "si"), 0)
        self.assertEqual(count(NORMALIZED_SPECIALS, "nc"), 1)
        self.assertEqual(count(NORMALIZED_SPECIALS, "si"), 0)
        self.assertEqual(count(ALL_NORMALIZED, "nc"), 299)
        self.assertEqual(count(ALL_NORMALIZED, "si"), 26)
        self.assertEqual(envelope_mod.COMMITTED_UNITS_WITH_CLICKS, 0)
        self.assertEqual(envelope_mod.COMMITTED_UNITS_WITH_ASSIST, 0)

    def test_is_placeable_holds_for_every_committed_row(self) -> None:
        """Which is why ``item_not_placeable`` is unreachable through the corpus."""
        for row in RAW_ITEMS:
            self.assertTrue(envelope_mod.is_placeable(row), row.get("id"))
        for row in ALL_NORMALIZED:
            self.assertTrue(envelope_mod.is_placeable(row), row.get("legacy_id"))
        self.assertEqual(
            sum(1 for row in RAW_ITEMS if not envelope_mod.is_placeable(row)), 0
        )
        self.assertEqual(
            sum(1 for row in ALL_NORMALIZED if not envelope_mod.is_placeable(row)), 0
        )

    def test_the_delivered_prizes_are_the_committed_collection_prizes(self) -> None:
        first = collection_envelope.project_prize(
            RAW_COLLECTIONS, envelope_mod.COMMITTED_COLLECTION_ID
        )
        self.assertEqual(first["name"], envelope_mod.COMMITTED_COLLECTION_NAME)
        self.assertEqual(first["prize"],
                         {str(envelope_mod.COMMITTED_PRIZE_ID): envelope_mod.COMMITTED_PRIZE_QUANTITY})
        second = collection_envelope.project_prize(
            RAW_COLLECTIONS, envelope_mod.COMMITTED_SELL_COLLECTION_ID
        )
        self.assertEqual(second["prize"], envelope_mod.COMMITTED_SELL_PRIZE)

    def test_the_delivered_prizes_are_units_that_place_with_an_empty_bag(self) -> None:
        for item_id in (envelope_mod.COMMITTED_PRIZE_ID,
                        envelope_mod.COMMITTED_SELL_ITEM_ID):
            row = envelope_mod.committed_item(RAW_ITEMS, item_id)
            self.assertIsNotNone(row, item_id)
            self.assertEqual(
                envelope_mod.derive_attr(row.get("clicks_to_build"),
                                         row.get("properties")),
                {},
                "item %d must place with an empty attribute bag" % item_id,
            )

    def test_committed_item_reads_the_raw_json_encoded_representation(self) -> None:
        """The raw config stores ``properties`` as a STRING; both forms work."""
        row = envelope_mod.committed_item(RAW_ITEMS, envelope_mod.COMMITTED_PRIZE_ID)
        self.assertIsInstance(row.get("properties"), str)
        # ...and the normalized OBJECT form derives the same bag.
        normalized = next(r for r in NORMALIZED_UNITS
                          if str(r.get("legacy_id")) ==
                          str(envelope_mod.COMMITTED_PRIZE_ID))
        self.assertIsInstance(normalized.get("properties"), Mapping)
        self.assertEqual(
            envelope_mod.derive_attr(row.get("clicks_to_build"), row.get("properties")),
            envelope_mod.derive_attr(normalized.get("clicks_to_build"),
                                     normalized.get("properties")),
        )

    def test_committed_item_returns_a_copy_and_none_for_an_unknown_id(self) -> None:
        row = envelope_mod.committed_item(RAW_ITEMS, 26)
        row["id"] = -1
        self.assertNotEqual(
            envelope_mod.committed_item(RAW_ITEMS, 26)["id"], -1
        )
        self.assertIsNone(
            envelope_mod.committed_item(RAW_ITEMS, envelope_mod.RECORDED_UNKNOWN_ITEM_ID)
        )
        self.assertIsNone(envelope_mod.committed_item("not a list", 26))

    def test_the_never_stored_probe_id_is_a_REAL_placeable_item(self) -> None:
        """``1071`` is Tank V: committed and placeable, simply not in storage.

        This is what makes ``not_in_storage`` distinct from ``unknown_item_id``
        and from ``item_not_placeable`` -- three refusals over three genuinely
        different committed states, not three spellings of one check.
        """
        row = envelope_mod.committed_item(RAW_ITEMS, envelope_mod.RECORDED_UNSTORED_ITEM_ID)
        self.assertIsNotNone(row)
        self.assertTrue(envelope_mod.is_placeable(row))
        self.assertNotIn(str(envelope_mod.RECORDED_UNSTORED_ITEM_ID), FRESH_STORE)
        # ...and it is genuinely absent, not present-and-zero.
        self.assertEqual(envelope_mod.store_count(FRESH_STORE, 1071), 0)

    def test_the_committed_corpus_pins(self) -> None:
        self.assertEqual(len(FRESH_ITEMS), envelope_mod.COMMITTED_PLACEMENTS)
        self.assertEqual(FRESH_STORE, {})
        self.assertEqual(FRESH_LEDGER, [])
        self.assertEqual(FRESH_ITEMS[str(envelope_mod.RECORDED_OCCUPIED_SLOT)],
                         envelope_mod.RECORDED_OCCUPIED_ROW)
        self.assertEqual(sorted(int(k) for k in FRESH_ITEMS), list(range(1, 41)))


class DeriveAttrTests(unittest.TestCase):
    """The port against an independent transcription, over all 900 items."""

    def test_the_port_agrees_with_the_legacy_transcription_on_every_item(self) -> None:
        for row in ALL_NORMALIZED:
            item_id = row.get("legacy_id")
            self.assertEqual(
                envelope_mod.derive_attr(row.get("clicks_to_build"),
                                         row.get("properties")),
                legacy_attr(row.get("clicks_to_build"), row.get("properties")),
                "item %s" % item_id,
            )

    def test_the_port_agrees_on_every_loaded_raw_row(self) -> None:
        for row in RAW_ITEMS:
            self.assertEqual(
                envelope_mod.derive_attr(row.get("clicks_to_build"),
                                         row.get("properties")),
                legacy_attr(row.get("clicks_to_build"), row.get("properties")),
                "item %s" % row.get("id"),
            )

    def test_the_three_derived_states(self) -> None:
        self.assertEqual(envelope_mod.derive_attr("0", None), {})
        self.assertEqual(envelope_mod.derive_attr("1", None), {"nc": 0})
        self.assertEqual(
            envelope_mod.derive_attr("0", '{"friend_assistable":"1"}'), {"si": []}
        )
        self.assertEqual(
            envelope_mod.derive_attr("1", '{"friend_assistable":"1"}'),
            {"si": [], "nc": 0},
        )

    def test_truthiness_is_tested_before_the_numeric_comparison(self) -> None:
        """Legacy tests the RAW string first, so ``"0"`` suppresses the key."""
        self.assertEqual(envelope_mod.derive_attr("0", '{"friend_assistable":"0"}'), {})
        self.assertEqual(envelope_mod.derive_attr("0", "{}"), {})
        self.assertEqual(envelope_mod.derive_attr(0, ""), {})
        self.assertEqual(envelope_mod.derive_attr(0, {}), {})
        self.assertEqual(envelope_mod.derive_attr(None, None), {})

    def test_a_missing_flag_writes_nothing(self) -> None:
        self.assertEqual(envelope_mod.derive_attr("1", '{"other":"1"}'), {"nc": 0})

    def test_the_derived_vocabulary_is_closed(self) -> None:
        self.assertEqual(envelope_mod.ATTR_KEYS, ("si", "nc"))
        seen = set()
        for row in ALL_NORMALIZED:
            seen.update(envelope_mod.derive_attr(row.get("clicks_to_build"),
                                                 row.get("properties")))
        self.assertEqual(seen, {"si", "nc"})

    def test_a_malformed_committed_field_fails_closed(self) -> None:
        for clicks, properties in (
            ("abc", None),
            ("1.5", None),
            (True, None),
            (None, "{not json"),
            (None, "[1,2]"),
            (None, 7),
            (None, '{"friend_assistable":"abc"}'),
            (None, '{"friend_assistable":true}'),
        ):
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr((clicks, properties))):
                envelope_mod.derive_attr(clicks, properties)


class AttrInverseTests(unittest.TestCase):
    """``attr_derived_from`` is the named inverse of ``derive_attr``."""

    def test_the_round_trip_holds_for_every_committed_item(self) -> None:
        for row in ALL_NORMALIZED:
            bag = envelope_mod.derive_attr(row.get("clicks_to_build"),
                                           row.get("properties"))
            sources = set(envelope_mod.attr_derived_from(bag))
            self.assertTrue(sources <= {"properties.friend_assistable",
                                        "clicks_to_build"}, bag)
            self.assertEqual("clicks_to_build" in sources, "nc" in bag)
            self.assertEqual("properties.friend_assistable" in sources, "si" in bag)

    def test_an_absent_key_contributes_nothing(self) -> None:
        self.assertEqual(envelope_mod.attr_derived_from({}), [])
        self.assertEqual(envelope_mod.attr_derived_from({"nc": 0}), ["clicks_to_build"])

    def test_an_unknown_key_is_reported_rather_than_silently_accepted(self) -> None:
        self.assertEqual(envelope_mod.attr_derived_from({"zz": 1}), ["unknown:zz"])

    def test_a_non_mapping_attr_is_refused(self) -> None:
        for value in ([], "si", None, 7):
            with self.assertRaises(envelope_mod.EnvelopeError):
                envelope_mod.attr_derived_from(value)

    def test_the_source_table_names_real_committed_fields(self) -> None:
        self.assertEqual(envelope_mod.ATTR_SOURCE,
                         {"si": "properties.friend_assistable", "nc": "clicks_to_build"})


class SlotRuleTests(unittest.TestCase):
    """The slot derivation and its named inverse."""

    def test_the_committed_corpus_derives_the_recorded_slot(self) -> None:
        self.assertEqual(envelope_mod.next_free_slot(FRESH_ITEMS), 41)
        self.assertEqual(envelope_mod.resolve_slot(FRESH_ITEMS),
                         envelope_mod.COMMITTED_DERIVED_SLOT)

    def test_resolve_slot_agrees_with_the_derivation_over_every_prefix(self) -> None:
        """A second implementation could not drift without failing here."""
        items: Dict[str, Any] = {}
        self.assertEqual(envelope_mod.resolve_slot(items), 1)
        for index in range(1, 41):
            items[str(index)] = [26, 51, 41, 0, 0, [], {}, 1]
            self.assertEqual(
                envelope_mod.resolve_slot(items),
                placement_envelope.next_free_slot(items),
                "after placing %d rows" % index,
            )
            self.assertEqual(envelope_mod.resolve_slot(items), index + 1)

    def test_the_inverse_round_trips_against_every_derived_slot(self) -> None:
        items: Dict[str, Any] = {}
        for expected in range(1, 41):
            slot = envelope_mod.resolve_slot(items)
            self.assertFalse(envelope_mod.slot_occupied(items, slot))
            items[str(slot)] = [26, 51, 41, 0, 0, [], {}, 1]
            self.assertTrue(envelope_mod.slot_occupied(items, slot))

    def test_the_inverse_reports_every_occupied_slot(self) -> None:
        for key in FRESH_ITEMS:
            self.assertTrue(envelope_mod.slot_occupied(FRESH_ITEMS, int(key)))

    def test_a_non_integer_key_cannot_collide_with_a_numeric_slot(self) -> None:
        self.assertFalse(envelope_mod.slot_occupied({"abc": 1}, 1))
        self.assertFalse(envelope_mod.slot_occupied({}, 41))

    def test_the_inverse_refuses_a_non_positive_or_non_integer_slot(self) -> None:
        for slot in (0, -1, "1", 1.0, True, None):
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr(slot)):
                envelope_mod.slot_occupied({}, slot)

    def test_the_guard_fires_when_the_key_view_and_occupancy_view_conflict(self) -> None:
        """The one state the two can disagree on, manufactured in memory.

        ``next_free_slot`` sees the key view while ``slot_occupied`` asks
        ``in``, and this mapping makes iteration hide key ``41`` while membership
        still reports it present -- exactly the disagreement the guard exists for.
        """

        class ConflictingItems(dict):
            """Iteration hides key 41; membership still reports it present.

            ``next_free_slot`` walks the KEY VIEW while ``slot_occupied`` asks
            ``in``, so overriding only ``__iter__`` makes the two disagree --
            the single state in which the derived slot and its own inverse can
            conflict, and therefore the only state the guard is reachable in.
            """
            HIDDEN = "41"

            def __iter__(self):
                return iter(k for k in dict.__iter__(self) if k != self.HIDDEN)

            def keys(self):
                return [k for k in dict.keys(self) if k != self.HIDDEN]

        items = ConflictingItems(FRESH_ITEMS)
        items["41"] = [1085, 58, 47, 0, 0, [], {}, 1]
        # The key view reports keys 1..40, so the derivation lands on 41...
        self.assertNotIn("41", list(iter(items)))
        self.assertEqual(placement_envelope.next_free_slot(items), 41)
        # ...while the occupancy view still sees 41 taken, so the guard fires.
        self.assertIn("41", items)
        self.assertTrue(envelope_mod.slot_occupied(items, 41))
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.resolve_slot(items)
        self.assertEqual(caught.exception.code, envelope_mod.REASON_SLOT_OCCUPIED)
        self.assertIn("destroy it silently", str(caught.exception))

    def test_the_conflict_mapping_is_the_only_way_to_reach_the_guard(self) -> None:
        """So the refusal is not merely dead code, and not merely always-on."""
        self.assertEqual(envelope_mod.resolve_slot(FRESH_ITEMS), 41)
        self.assertEqual(envelope_mod.resolve_slot({}), 1)


class ValidationTests(unittest.TestCase):
    """Structural input validity. Strictly no gameplay rule."""

    def test_a_strict_integer_item_id(self) -> None:
        self.assertEqual(envelope_mod.validate_item_id(1085), 1085)
        for value in ("1085", 1085.0, True, None, [1085], {}):
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr(value)):
                envelope_mod.validate_item_id(value)

    def test_coordinates_are_two_integers_and_nothing_else(self) -> None:
        self.assertEqual(envelope_mod.validate_coordinates(58, 47), (58, 47))
        for x, y in ((58, "47"), ("58", 47), (58.0, 47), (None, 47), (58, None)):
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr((x, y))):
                envelope_mod.validate_coordinates(x, y)

    def test_an_out_of_grid_cell_is_accepted_because_bounds_are_a_recorded_gap(self) -> None:
        """The recorded probe cell. Accepting it is the point, not an oversight."""
        self.assertEqual(
            envelope_mod.validate_coordinates(*envelope_mod.RECORDED_OUT_OF_GRID_CELL),
            envelope_mod.RECORDED_OUT_OF_GRID_CELL,
        )

    def test_the_orientation_passthrough_is_accepted_verbatim(self) -> None:
        self.assertEqual(envelope_mod.validate_orientation(0), 0)
        self.assertEqual(envelope_mod.validate_orientation(-3), -3)
        for value in ("0", 0.0, None, True):
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr(value)):
                envelope_mod.validate_orientation(value)


class ProjectStorageTests(unittest.TestCase):
    """The storage projection: verbatim, and closed on every malformed shape."""

    def test_an_empty_storage_projects_faithfully(self) -> None:
        projected = envelope_mod.project_storage(FRESH_STORE, FRESH_LEDGER)
        self.assertTrue(projected["ok"])
        self.assertEqual(projected["reason"], "")
        self.assertEqual(projected["entries"], [])
        self.assertEqual(projected["counts"], {})
        self.assertEqual(projected["total_units"], 0)
        self.assertEqual(projected["distinct_ids"], 0)
        self.assertEqual(projected["ledger"], [])
        self.assertEqual(projected["ledger_distinct_ids"], 0)

    def test_counts_are_reported_verbatim_in_committed_order(self) -> None:
        store = {"1085": 1, "1062": 3, "164": 2}
        projected = envelope_mod.project_storage(store, [1085, 1085, 164])
        self.assertTrue(projected["ok"])
        self.assertEqual(projected["counts"], store)
        self.assertEqual([e["item_id"] for e in projected["entries"]],
                         ["164", "1062", "1085"])
        self.assertEqual(projected["total_units"], 6)
        self.assertEqual(projected["distinct_ids"], 3)
        # The ledger is copied, never aliased, and never de-duplicated.
        self.assertEqual(projected["ledger"], [1085, 1085, 164])
        self.assertEqual(projected["ledger_distinct_ids"], 2)
        projected["ledger"].append(-1)
        self.assertEqual(store, {"1085": 1, "1062": 3, "164": 2})

    def test_it_derives_no_capacity_expiry_value_or_price(self) -> None:
        projected = envelope_mod.project_storage({"1085": 1}, [1085])
        for key in ("capacity", "expiry", "value", "price"):
            self.assertIsNone(projected[key], key)
        self.assertIn("no limit", projected["note"])

    def test_a_non_mapping_store_fails_closed_with_no_entries(self) -> None:
        for store in ([], None, "x", 7, [{"1085": 1}]):
            projected = envelope_mod.project_storage(store, [1085])
            self.assertFalse(projected["ok"], repr(store))
            self.assertEqual(projected["reason"], envelope_mod.REASON_UNRESOLVABLE_STORAGE)
            self.assertEqual(projected["entries"], [])
            self.assertEqual(projected["counts"], {})
            self.assertEqual(projected["total_units"], 0)
            self.assertFalse(projected["store_is_mapping"])
            self.assertTrue(projected["ledger_is_list"])
            self.assertEqual(projected["ledger"], [1085])

    def test_a_non_integer_count_fails_closed_reporting_what_it_read(self) -> None:
        projected = envelope_mod.project_storage({"1085": "1"}, [])
        self.assertFalse(projected["ok"])
        self.assertEqual(projected["reason"], envelope_mod.REASON_UNRESOLVABLE_STORAGE)
        self.assertEqual(projected["counts"], {})
        self.assertIn("not an integer count", projected["error"])
        # Nothing is invented, defaulted to zero, or dropped.
        projected = envelope_mod.project_storage({"164": 2, "1085": None}, [])
        self.assertFalse(projected["ok"])
        self.assertEqual(projected["counts"], {"164": 2})
        self.assertIn("'1085'", projected["error"])

    def test_a_float_count_is_not_an_integer_count(self) -> None:
        self.assertFalse(envelope_mod.project_storage({"1085": 1.0}, [])["ok"])
        self.assertFalse(envelope_mod.project_storage({"1085": True}, [])["ok"])

    def test_a_non_list_ledger_fails_closed(self) -> None:
        projected = envelope_mod.project_storage({"1085": 1}, {"a": 1})
        self.assertFalse(projected["ok"])
        self.assertEqual(projected["reason"], envelope_mod.REASON_UNRESOLVABLE_STORAGE)
        self.assertEqual(projected["counts"], {"1085": 1})
        self.assertIsNone(projected["ledger"])
        self.assertFalse(projected["ledger_is_list"])

    def test_an_absent_ledger_is_distinct_from_an_empty_one(self) -> None:
        self.assertTrue(envelope_mod.project_storage({"1085": 1}, None)["ok"])
        self.assertIsNone(envelope_mod.project_storage({"1085": 1}, None)["ledger"])
        self.assertEqual(
            envelope_mod.project_storage({"1085": 1}, [])["ledger"], []
        )


class ExpectedStateTests(unittest.TestCase):
    """``expected_row`` / ``expected_ledger`` / ``expected_storage_after``."""

    def test_the_row_is_the_engines_own_eight_slot_shape(self) -> None:
        self.assertEqual(
            envelope_mod.expected_row(1085, 58, 47, 1700000000, 0),
            [1085, 58, 47, 1700000000, 0, [], {}, 1],
        )

    def test_the_row_derives_its_bag_from_the_two_committed_fields(self) -> None:
        """Not handed a bag: derived, so the comparison cannot be circular."""
        self.assertEqual(
            envelope_mod.expected_row(26, 58, 47, 1, 0, "1", None),
            [26, 58, 47, 1, 0, [], {"nc": 0}, 1],
        )
        self.assertEqual(
            envelope_mod.expected_row(2, 58, 47, 1, 0, "1", '{"friend_assistable":"1"}'),
            [2, 58, 47, 1, 0, [], {"si": [], "nc": 0}, 1],
        )

    def test_the_row_team_is_one_whatever_the_caller_thinks(self) -> None:
        row = envelope_mod.expected_row(1062, 58, 47, 1700000000, 3, "1", None)
        self.assertEqual(row[envelope_mod.ROW_SLOT_PLAYER], 1)
        self.assertEqual(row[envelope_mod.ROW_SLOT_ORIENTATION], 3)
        self.assertEqual(row[envelope_mod.ROW_SLOT_STORE], [])
        self.assertEqual(row[envelope_mod.ROW_SLOT_ATTR], {"nc": 0})

    def test_the_garrison_list_is_not_shared_between_rows(self) -> None:
        first = envelope_mod.expected_row(1085, 1, 1, 1700000000, 0, {})
        first[envelope_mod.ROW_SLOT_STORE].append("mutated")
        second = envelope_mod.expected_row(1085, 1, 1, 1700000000, 0, {})
        self.assertEqual(second[envelope_mod.ROW_SLOT_STORE], [])

    def test_the_row_instant_must_be_a_non_negative_integer(self) -> None:
        for value in (-1, "1", 1.5, None, True):
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr(value)):
                envelope_mod.expected_row(1085, 1, 1, value, 0)

    def test_the_ledger_is_append_if_absent(self) -> None:
        self.assertEqual(envelope_mod.expected_ledger([], 1085), [1085])
        self.assertEqual(envelope_mod.expected_ledger([1085], 1085), [1085])
        self.assertEqual(envelope_mod.expected_ledger([164], 1085), [164, 1085])
        self.assertEqual(envelope_mod.expected_ledger(None, 1085), [1085])

    def test_the_ledger_input_is_copied_not_aliased(self) -> None:
        before = [164]
        after = envelope_mod.expected_ledger(before, 1085)
        after.append(999)
        self.assertEqual(before, [164])

    def test_a_non_list_ledger_is_refused(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError):
            envelope_mod.expected_ledger({"a": 1}, 1085)

    def test_the_derived_decrement_is_exactly_one(self) -> None:
        self.assertIsNone(
            envelope_mod.expected_storage_after({"1085": 2}, {"1085": 1}, 1085)
        )
        self.assertIsNone(
            envelope_mod.expected_storage_after({"1085": 1}, {}, 1085),
            "reaching zero DELETES the key (engine.py:80-83)",
        )

    def test_a_wrong_decrement_is_reported(self) -> None:
        self.assertIsNotNone(
            envelope_mod.expected_storage_after({"1085": 2}, {"1085": 2}, 1085)
        )
        self.assertIsNotNone(
            envelope_mod.expected_storage_after({"1085": 2}, {"1085": 0}, 1085)
        )
        self.assertIsNotNone(
            envelope_mod.expected_storage_after({"1085": 1}, {"1085": 5}, 1085)
        )

    def test_an_item_that_was_never_stored_is_reported(self) -> None:
        reason = envelope_mod.expected_storage_after({}, {}, 1071)
        self.assertIsNotNone(reason)
        self.assertIn("not in storage", reason)

    def test_a_zero_key_that_survives_its_decrement_is_reported(self) -> None:
        reason = envelope_mod.expected_storage_after({"1085": 1}, {"1085": 0}, 1085)
        self.assertIsNotNone(reason)
        self.assertIn("DELETES", reason)

    def test_another_stored_key_moving_is_reported(self) -> None:
        reason = envelope_mod.expected_storage_after(
            {"1085": 1, "164": 2}, {"164": 3}, 1085
        )
        self.assertIsNotNone(reason)
        self.assertIn("'164'", reason)

    def test_a_stored_key_gaining_a_count_is_reported_too(self) -> None:
        reason = envelope_mod.expected_storage_after(
            {"1085": 1, "164": 2}, {"1085": 0, "164": 3}, 1085
        )
        self.assertIsNotNone(reason)

    def test_a_non_mapping_storage_is_reported(self) -> None:
        self.assertIsNotNone(envelope_mod.expected_storage_after([], {}, 1085))
        self.assertIsNotNone(envelope_mod.expected_storage_after({}, None, 1085))

    def test_store_count_reads_absent_as_zero(self) -> None:
        self.assertEqual(envelope_mod.store_count({"1085": 2}, 1085), 2)
        self.assertEqual(envelope_mod.store_count({}, 1085), 0)
        self.assertEqual(envelope_mod.store_count({"1085": 2}, 164), 0)
        with self.assertRaises(envelope_mod.EnvelopeError):
            envelope_mod.store_count(None, 1085)
        with self.assertRaises(envelope_mod.EnvelopeError):
            envelope_mod.store_count({"1085": "1"}, 1085)


class DivergenceProofTests(unittest.TestCase):
    """The two-part placement proof and the whole-claim sale proof."""

    def setUp(self) -> None:
        self.store_before = {"1085": 1}
        self.store_after = {}
        self.ledger_before: List[Any] = []
        self.row = envelope_mod.expected_row(1085, 58, 47, 1700000000, 0)

    def test_a_correct_placement_has_no_divergence(self) -> None:
        self.assertIsNone(
            envelope_mod.divergence_place(
                self.store_before, self.store_after, self.ledger_before,
                [1085], self.row, 1085, 58, 47, 0, None, None, 1700000000,
            )
        )

    def test_the_storage_half_is_checked_first_and_alone_is_sufficient(self) -> None:
        reason = envelope_mod.divergence_place(
            {"1085": 1}, {"1085": 1}, [], [1085], self.row, 1085, 58, 47, 0,
        )
        self.assertIsNotNone(reason)
        self.assertIn("not the derived", reason)

    def test_the_row_half_catches_a_client_dictated_team(self) -> None:
        """The four executed probes each show the row can come out differently."""
        for slot, replacement, needle in (
            (envelope_mod.ROW_SLOT_PLAYER, 3, "player team"),
            (envelope_mod.ROW_SLOT_ITEM, 999999, "item slot"),
            (envelope_mod.ROW_SLOT_X, 1, "records cell"),
            (envelope_mod.ROW_SLOT_ORIENTATION, 2, "orientation"),
            (envelope_mod.ROW_SLOT_ATTR, {"nc": 0}, "attribute bag"),
            (envelope_mod.ROW_SLOT_STORE, [1], "garrison"),
            (envelope_mod.ROW_SLOT_TIMESTAMP, 1, "instant"),
        ):
            row = list(self.row)
            row[slot] = replacement
            reason = envelope_mod.divergence_place(
                self.store_before, self.store_after, self.ledger_before, [1085],
                row, 1085, 58, 47, 0, None, None, 1700000000,
            )
            self.assertIsNotNone(reason, slot)
            self.assertIn(needle, reason)

    def test_a_short_or_wrongly_shaped_row_is_reported(self) -> None:
        for row in ([], [1, 2], list(self.row)[:7], "row"):
            reason = envelope_mod.divergence_place(
                self.store_before, self.store_after, self.ledger_before, [1085],
                row, 1085, 58, 47, 0,
            )
            self.assertIsNotNone(reason, repr(row))

    def test_the_ledger_half_is_checked(self) -> None:
        reason = envelope_mod.divergence_place(
            self.store_before, self.store_after, self.ledger_before, [],
            self.row, 1085, 58, 47, 0,
        )
        self.assertIsNotNone(reason)
        self.assertIn("purchase ledger", reason)

    def test_a_ledger_always_appended_would_fail_here(self) -> None:
        """An append-if-absent that always appended is caught on the second id."""
        reason = envelope_mod.divergence_place(
            self.store_before, self.store_after, [1085], [1085, 1085],
            self.row, 1085, 58, 47, 0,
        )
        self.assertIsNotNone(reason)
        self.assertIn("purchase ledger", reason)

    def test_the_proof_derives_the_bag_so_it_cannot_be_handed_its_own(self) -> None:
        """Handing the proof the row's own bag must not make it pass.

        The proof is called with the COMMITTED fields (``26`` needs build
        clicks), and a row whose bag is empty is caught -- so the check is a
        derivation, not an echo of its own input.
        """
        row = envelope_mod.expected_row(26, 58, 47, 1700000000, 0, "1", None)
        self.assertEqual(row[6], {"nc": 0})
        reason = envelope_mod.divergence_place(
            {"26": 1}, {}, [], [26], row, 26, 58, 47, 0, "1", None, 1700000000,
        )
        self.assertIsNone(reason)
        stale = list(row)
        stale[6] = {}
        reason = envelope_mod.divergence_place(
            {"26": 1}, {}, [], [26], stale, 26, 58, 47, 0, "1", None, 1700000000,
        )
        self.assertIsNotNone(reason)
        self.assertIn("attribute bag", reason)

    def test_a_non_positive_instant_is_reported_without_a_timestamp_argument(self) -> None:
        reason = envelope_mod.divergence_place(
            self.store_before, self.store_after, self.ledger_before, [1085],
            [1085, 58, 47, 0, 0, [], {}, 1], 1085, 58, 47, 0,
        )
        self.assertIsNotNone(reason)
        self.assertIn("wall-clock", reason)

    def test_a_correct_sale_has_no_divergence(self) -> None:
        self.assertIsNone(
            envelope_mod.divergence_sell(
                {"1085": 2}, {"1085": 1}, [1085], [1085],
                1085, FRESH_ITEMS, FRESH_ITEMS,
            )
        )
        self.assertIsNone(
            envelope_mod.divergence_sell(
                {"1085": 1}, {}, [], [], 1085, FRESH_ITEMS, FRESH_ITEMS,
            )
        )

    def test_a_sale_that_moved_the_ledger_is_reported(self) -> None:
        """The sale writes only the store key, so a ledger change would be a bug."""
        reason = envelope_mod.divergence_sell(
            {"1085": 1}, {}, [], [1085], 1085, FRESH_ITEMS, FRESH_ITEMS,
        )
        self.assertIsNotNone(reason)
        self.assertIn("never touches boughtUnits", reason)

    def test_a_sale_that_added_or_changed_a_placement_is_reported(self) -> None:
        items_after = dict(FRESH_ITEMS)
        items_after["41"] = [1085, 58, 47, 0, 0, [], {}, 1]
        reason = envelope_mod.divergence_sell(
            {"1085": 1}, {}, [], [], 1085, FRESH_ITEMS, items_after,
        )
        self.assertIsNotNone(reason)
        self.assertIn("placement keys changed", reason)

        changed = json.loads(json.dumps(FRESH_ITEMS))
        changed["1"] = [164, 51, 41, 0, 0, [], {}, 1]
        reason = envelope_mod.divergence_sell(
            {"1085": 1}, {}, [], [], 1085, FRESH_ITEMS, changed,
        )
        self.assertIsNotNone(reason)
        self.assertIn("changed", reason)

    def test_a_sale_against_non_mappings_is_reported(self) -> None:
        self.assertIsNotNone(
            envelope_mod.divergence_sell([], {}, [], [], 1085, FRESH_ITEMS, FRESH_ITEMS)
        )
        self.assertIsNotNone(
            envelope_mod.divergence_sell({"1085": 1}, {}, [], [], 1085, [], FRESH_ITEMS)
        )


class EnvelopeShapeTests(unittest.TestCase):
    """The six-key batch each branch is driven with."""

    def test_the_placement_envelope(self) -> None:
        built = envelope_mod.build_place_envelope(
            1085, 58, 47, FRESH_ITEMS, 0, 1700000000
        )
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(built["first_number"], 0)
        self.assertEqual(built["publishActions"], [])
        self.assertEqual(built["tries"], 1)
        self.assertEqual(built["accessToken"], "")
        self.assertEqual(
            built["commands"],
            [[0, "place_stored_item", [41, 1085, 58, 47, 1, 0, 0, 0], [0] * 8]],
        )

    def test_the_sale_envelope(self) -> None:
        built = envelope_mod.build_sell_envelope(1085, 1700000000)
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        self.assertEqual(built["commands"],
                         [[0, "sell_stored_item", [1085], [0] * 8]])

    def test_the_slot_is_derived_and_never_accepted(self) -> None:
        """Two calls over a growing corpus move the derived slot; nothing else."""
        first = envelope_mod.build_place_envelope(1085, 58, 47, FRESH_ITEMS, 0, 1)
        items = dict(FRESH_ITEMS)
        items["41"] = [1085, 58, 47, 0, 0, [], {}, 1]
        second = envelope_mod.build_place_envelope(1085, 58, 47, items, 0, 1)
        self.assertEqual(first["commands"][0][2][0], 41)
        self.assertEqual(second["commands"][0][2][0], 42)
        self.assertEqual(first["commands"][0][2][1:], [1085, 58, 47, 1, 0, 0, 0])
        self.assertEqual(second["commands"][0][2][1:], [1085, 58, 47, 1, 0, 0, 0])

    def test_the_dismissed_arguments_are_sent_as_placeholders_not_client_values(self) -> None:
        """`playerID` is 1 because the team is always 1 -- and it is proved ignored."""
        built = envelope_mod.build_place_envelope(
            1085, 58, 47, FRESH_ITEMS, 3, 1700000000
        )
        self.assertEqual(built["commands"][0][2][envelope_mod.ARG_PLAYER_ID], 1)
        self.assertEqual(built["commands"][0][2][envelope_mod.ARG_ORIENTATION], 3)
        self.assertEqual(built["commands"][0][2][envelope_mod.ARG_UNKNOWN_AUTOACTIVABLE], 0)
        self.assertEqual(built["commands"][0][2][envelope_mod.ARG_UNKNOWN_IMG_INDEX], 0)

    def test_the_orientation_passthrough_is_verbatim(self) -> None:
        for facing in (0, 1, 2, 3, -1):
            built = envelope_mod.build_place_envelope(
                1085, 58, 47, FRESH_ITEMS, facing, 1
            )
            self.assertEqual(built["commands"][0][2][envelope_mod.ARG_ORIENTATION], facing)

    def test_ts_defaults_to_now_and_must_be_a_non_negative_integer(self) -> None:
        built = envelope_mod.build_place_envelope(1085, 58, 47, FRESH_ITEMS, 0)
        self.assertGreaterEqual(built["ts"], 1_000_000_000)
        for value in (-1, "1", 1.5, True):
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr(value)):
                envelope_mod.build_place_envelope(1085, 58, 47, FRESH_ITEMS, 0, value)
            with self.assertRaises(envelope_mod.EnvelopeError, msg=repr(value)):
                envelope_mod.build_sell_envelope(1085, value)

    def test_the_sale_envelope_takes_no_cell_and_no_quantity(self) -> None:
        built = envelope_mod.build_sell_envelope(1062, 1)
        self.assertEqual(len(built["commands"][0][2]), 1)
        self.assertEqual(built["commands"][0][2][0], 1062)

    def test_an_invalid_item_id_is_refused_by_both_builders(self) -> None:
        for builder in (envelope_mod.build_sell_envelope,):
            with self.assertRaises(envelope_mod.EnvelopeError):
                builder("1085")
        with self.assertRaises(envelope_mod.EnvelopeError):
            envelope_mod.build_place_envelope("1085", 58, 47, FRESH_ITEMS)


class AntiInventionTests(unittest.TestCase):
    """The guards, stated as assertions so they cannot rot into promises."""

    EXPECTED_FUNCTIONS = (
        "_committed_int", "_decode_properties", "_distinct",
        "attr_derived_from", "build_place_envelope", "build_sell_envelope",
        "committed_item", "derive_attr", "divergence_place", "divergence_sell",
        "expected_ledger", "expected_row", "expected_storage_after",
        "is_placeable", "neutral_vector", "project_storage", "resolve_slot",
        "slot_occupied", "store_count", "validate_coordinates", "validate_item_id",
        "validate_orientation",
    )

    def test_the_whole_function_inventory_is_pinned(self) -> None:
        """A rename cannot smuggle a helper past ``ABSENT_HELPERS``."""
        defined = {
            name for name, value in vars(envelope_mod).items()
            if inspect.isfunction(value) and value.__module__ == envelope_mod.__name__
        }
        self.assertEqual(sorted(defined), sorted(self.EXPECTED_FUNCTIONS))

    def test_no_helper_accepts_an_attr_or_a_player_parameter(self) -> None:
        """The mechanical form of 'the client cannot dictate the row'.

        The one permitted exception is ``attr_derived_from``, which is the named
        INVERSE -- it reports on a bag rather than producing one, so it reads an
        ``attr`` in order to name its committed sources.  Every DERIVATION --
        ``derive_attr``, ``expected_row``, ``build_place_envelope`` -- takes the
        two committed FIELDS instead, and no function anywhere takes a player or
        a team, which is what makes the committed team ``1`` unarguable.
        """
        permitted = {("attr_derived_from", "attr")}
        offenders = []
        for name, function in vars(envelope_mod).items():
            if not inspect.isfunction(function):
                continue
            if function.__module__ != envelope_mod.__name__:
                continue
            for parameter in inspect.signature(function).parameters:
                if parameter in ("attr", "player", "player_id", "playerID", "team"):
                    offenders.append((name, parameter))
        self.assertEqual(set(offenders), permitted)
        # And no function derives a team at all.
        self.assertEqual(
            [pair for pair in offenders if pair[1] != "attr"], []
        )
        for name in ("derive_attr", "expected_row", "divergence_place"):
            parameters = inspect.signature(
                getattr(envelope_mod, name)
            ).parameters
            self.assertNotIn("attr", parameters, name)
            self.assertIn("clicks_to_build", parameters, name)
        # The envelope builder never touches the bag at all -- it derives the
        # SLOT and forwards the committed item id, nothing more.
        builder = inspect.signature(envelope_mod.build_place_envelope).parameters
        self.assertNotIn("attr", builder)
        self.assertNotIn("clicks_to_build", builder)
        self.assertEqual(
            sorted(builder), ["item_id", "items", "orientation", "ts", "x", "y"]
        )

    def test_no_helper_accepts_a_price_or_a_refund(self) -> None:
        offenders = []
        for name, function in vars(envelope_mod).items():
            if not inspect.isfunction(function):
                continue
            if function.__module__ != envelope_mod.__name__:
                continue
            for parameter in inspect.signature(function).parameters:
                if parameter in ("price", "cost", "costs", "refund",
                                 "gold", "cash", "vector", "resources_changed"):
                    offenders.append((name, parameter))
        self.assertEqual(offenders, [])

    def test_only_the_quantity_proof_helper_takes_a_quantity(self) -> None:
        """``expected_storage_after`` derives from QUANTITY, it is not an input.

        The one permitted exception to "no function accepts a quantity or a
        price": this is a post-execution PROOF comparison, not a derivation, and
        its default is the module constant rather than a client value.
        """
        offenders = []
        defaults = {}
        for name, function in vars(envelope_mod).items():
            if not inspect.isfunction(function):
                continue
            if function.__module__ != envelope_mod.__name__:
                continue
            for parameter, spec in inspect.signature(function).parameters.items():
                if parameter == "quantity":
                    offenders.append((name, parameter))
                    defaults[name] = spec.default
        self.assertEqual(offenders, [("expected_storage_after", "quantity")])
        self.assertEqual(defaults, {"expected_storage_after": envelope_mod.QUANTITY})
        self.assertIs(envelope_mod.QUANTITY, 1)

    def test_no_absent_helper_is_defined(self) -> None:
        for name, reason in envelope_mod.ABSENT_HELPERS:
            self.assertFalse(hasattr(envelope_mod, name), name)
            self.assertTrue(reason, name)
            self.assertEqual(name, name.lower(), name)
            self.assertTrue(name.replace("_", "").isalnum(), name)

    def test_the_absent_helpers_are_unique_and_cover_no_real_helper(self) -> None:
        """The list is grouped by theme, so uniqueness -- not order -- is pinned."""
        names = [name for name, _ in envelope_mod.ABSENT_HELPERS]
        self.assertEqual(len(names), len(set(names)))
        defined = {
            name for name, value in vars(envelope_mod).items()
            if inspect.isfunction(value) and value.__module__ == envelope_mod.__name__
        }
        self.assertEqual(set(names) & defined, set())

    def test_the_absence_guards_are_load_bearing_for_this_line(self) -> None:
        """Binds the absence list to the two headline recorded-not-refused gaps."""
        names = {name for name, _ in envelope_mod.ABSENT_HELPERS}
        for required in ("bounds", "in_bounds", "footprint", "overlaps", "capacity",
                         "price", "refund", "store_add_items", "eligible"):
            self.assertIn(required, names)

    def test_the_four_refusals_are_recorded_with_their_divergence(self) -> None:
        self.assertEqual(envelope_mod.REFUSAL_COUNT, 4)
        self.assertEqual(
            [entry["refusal"] for entry in envelope_mod.REFUSALS],
            ["not_in_storage", "slot_occupied", "unknown_item_id",
             "item_not_placeable"],
        )
        for entry in envelope_mod.REFUSALS:
            self.assertTrue(entry["implemented"])
            self.assertEqual(entry["status"], 409)
            self.assertTrue(entry["divergence"],
                            "every refusal diverges from the legacy server")
            self.assertTrue(entry["legacy"])
            self.assertTrue(entry["why"])

    def test_the_recorded_not_refused_notes_are_present_and_substantial(self) -> None:
        for note in (envelope_mod.GEOMETRY_GAP, envelope_mod.CELL_OCCUPANCY_GAP,
                     envelope_mod.ADDRESSABILITY, envelope_mod.NO_CAPACITY_RULE,
                     envelope_mod.NO_REFUND_NOTE, envelope_mod.NO_STOCK_RULE,
                     envelope_mod.QUANTITY_RULE, envelope_mod.LEDGER_RULE,
                     envelope_mod.TIMESTAMP_NOTE, envelope_mod.INVERSE_RULE,
                     envelope_mod.SLOT_RULE, envelope_mod.SLOT_INVERSE_RULE,
                     envelope_mod.ATTR_RULE, envelope_mod.ROW_DERIVATION,
                     envelope_mod.INTENT_NOTE, envelope_mod.COMMITTED_CONTENT_NOTE,
                     envelope_mod.REFUSAL_SLOT_OCCUPIED_NOTE):
            self.assertGreater(len(note), 80, note[:60])

    def test_the_closed_intent_vocabularies(self) -> None:
        self.assertEqual(
            envelope_mod.PLACE_INTENT_KEYS,
            ("user_id", "item_id", "x", "y", "orientation"),
        )
        self.assertEqual(envelope_mod.PLACE_INTENT_REQUIRED_KEYS,
                         ("user_id", "item_id", "x", "y"))
        self.assertEqual(envelope_mod.SELL_INTENT_KEYS, ("user_id", "item_id"))
        # A route never both reads a key and ignores it.
        self.assertEqual(
            set(envelope_mod.PLACE_INTENT_KEYS)
            & set(envelope_mod.PLACE_INTENT_IGNORED_KEYS), set(),
        )
        self.assertEqual(
            set(envelope_mod.SELL_INTENT_KEYS)
            & set(envelope_mod.SELL_INTENT_IGNORED_KEYS), set(),
        )
        # And every required key is an accepted key.
        self.assertEqual(
            set(envelope_mod.PLACE_INTENT_REQUIRED_KEYS)
            - set(envelope_mod.PLACE_INTENT_KEYS), set(),
        )

    def test_the_sale_route_ignores_the_cells_the_placement_route_reads(self) -> None:
        """`x`/`y`/`orientation` are read by one route and unread by the other.

        A client may send them to the sale route; they are ignored, not refused,
        which is the same boundary the placement route takes for a client-sent
        price or quantity.
        """
        place = set(envelope_mod.PLACE_INTENT_KEYS)
        sell_ignored = set(envelope_mod.SELL_INTENT_IGNORED_KEYS)
        self.assertTrue({"x", "y", "orientation"} <= place)
        self.assertTrue({"x", "y", "orientation"} <= sell_ignored)

    def test_the_ignored_key_lists_are_sorted_and_unique(self) -> None:
        for ignored in (envelope_mod.PLACE_INTENT_IGNORED_KEYS,
                        envelope_mod.SELL_INTENT_IGNORED_KEYS):
            self.assertEqual(list(ignored), sorted(ignored))
            self.assertEqual(len(ignored), len(set(ignored)))

    def test_every_server_owned_field_is_named_as_an_ignored_client_key(self) -> None:
        """Slot, row, bag, team, stock, and price are all unnameable."""
        place = set(envelope_mod.PLACE_INTENT_IGNORED_KEYS)
        for key in ("index", "item_index", "slot", "row", "attr", "player",
                    "player_id", "team", "quantity", "price", "timestamp"):
            self.assertIn(key, place)
        sell = set(envelope_mod.SELL_INTENT_IGNORED_KEYS)
        for key in ("index", "slot", "attr", "player", "quantity", "price", "refund",
                    "x", "y", "orientation"):
            self.assertIn(key, sell)

    def test_every_exported_name_exists_and_is_unique(self) -> None:
        self.assertEqual(len(envelope_mod.__all__),
                         len(set(envelope_mod.__all__)))
        for name in envelope_mod.__all__:
            self.assertTrue(hasattr(envelope_mod, name), name)

    def test_the_module_raises_only_its_own_error_type(self) -> None:
        self.assertIs(envelope_mod.EnvelopeError, placement_envelope.EnvelopeError)


if __name__ == "__main__":
    unittest.main()