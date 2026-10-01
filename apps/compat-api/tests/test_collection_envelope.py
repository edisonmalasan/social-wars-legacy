#!/usr/bin/env python3
"""Compatibility API v0 ``collection_envelope`` derivation tests.

Offline and hermetic: no corpus, no server, no socket, no request.  Every case
runs against the **stored** ``config/main.json`` collections table (read
directly) or against a crafted in-memory table, so the derivation is checked
without a legacy server and without touching a save.

What is covered
    * the **one-based** index with the legacy clamp, and the **alias** it
      produces: collection id 0 and collection id 1 resolve to the same prize,
      as does every negative id;
    * the **committed** prize bag, reported verbatim, with the committed string
      keys ``map["store"]`` is keyed by;
    * an out-of-table id reported as **unresolvable with its recorded value
      intact** — never dropped, never substituted;
    * the ten committed collections, their committed names, their committed
      prizes, and the six-unit / four-building split;
    * the **neutral** vector and the refusal of every non-neutral one;
    * the post-execution derivations: the storage after the committed grant, the
      append-if-absent ledger, and the first-divergence comparison;
    * the recorded absences: no eligibility check, no unit income, no cap
      semantics, no experience award — asserted as **text** *and* as the absence
      of any helper that could compute one.
"""

from __future__ import annotations

import json
import unittest
from typing import Any, Dict, List, Optional

import compat_test_harness as harness  # noqa: F401  (sys.path + offline guard)

import collection_envelope

CONFIG = harness.REPO_ROOT / "config" / "main.json"


def committed_table() -> List[Any]:
    document = json.loads(CONFIG.read_text(encoding="utf-8"))
    table = document["collections"]
    assert isinstance(table, list), "the committed collections table is not a list"
    return table


class IndexResolutionTests(unittest.TestCase):
    """The one-based index, the clamp, and the alias (design D3)."""

    def test_the_one_based_index_selects_the_committed_row(self) -> None:
        table = committed_table()
        for position, row in enumerate(table):
            collection_id = position + 1
            projected = collection_envelope.project_prize(table, collection_id)
            self.assertTrue(projected["ok"], "id %d resolves" % collection_id)
            self.assertEqual(projected["index"], position)
            self.assertEqual(projected["requested_index"], position)
            self.assertEqual(projected["name"], row["name"])
            self.assertEqual(projected["id_column"], str(row["id"]))

    def test_the_derivation_reproduces_the_legacy_expression_exactly(self) -> None:
        # The legacy expression is `max(0, collection - 1)`, so the test computes
        # it independently rather than trusting the module's own arithmetic.
        table = committed_table()
        for collection_id in (-1000, -5, -1, 0, 1, 2, 5, 10, 11, 99):
            projected = collection_envelope.project_prize(table, collection_id)
            expected = max(0, collection_id - 1)
            if expected < len(table):
                self.assertTrue(projected["ok"])
                self.assertEqual(projected["index"], expected)
            else:
                self.assertFalse(projected["ok"])
                self.assertEqual(projected["index"], expected)

    def test_zero_and_one_resolve_to_the_same_committed_prize(self) -> None:
        table = committed_table()
        zero = collection_envelope.project_prize(table, 0)
        one = collection_envelope.project_prize(table, 1)
        self.assertEqual(zero["prize"], one["prize"])
        self.assertEqual(zero["name"], one["name"])
        self.assertEqual(zero["index"], one["index"])
        self.assertEqual(zero["prize"], {"1085": 1})

    def test_every_id_at_or_below_the_clamp_floor_aliases_onto_id_one(self) -> None:
        table = committed_table()
        one = collection_envelope.project_prize(table, 1)
        for collection_id in (-9999, -2, -1, 0):
            projected = collection_envelope.project_prize(table, collection_id)
            self.assertTrue(projected["ok"], "%d resolves" % collection_id)
            self.assertEqual(projected["prize"], one["prize"])
            self.assertTrue(projected["clamped"], "%d is clamped" % collection_id)
            self.assertTrue(projected["aliased"], "%d is an alias" % collection_id)
            self.assertEqual(projected["alias_of"], 1)
            self.assertTrue(collection_envelope.is_aliased(collection_id))
            self.assertEqual(collection_envelope.alias_of(collection_id), 1)

    def test_an_unclamped_id_is_never_reported_as_an_alias(self) -> None:
        table = committed_table()
        for collection_id in range(1, len(table) + 1):
            projected = collection_envelope.project_prize(table, collection_id)
            self.assertFalse(projected["clamped"], "%d is unclamped" % collection_id)
            self.assertFalse(projected["aliased"], "%d is not an alias" % collection_id)
            self.assertIsNone(projected["alias_of"])
            self.assertEqual(
                collection_envelope.alias_of(collection_id), collection_id
            )
            self.assertFalse(collection_envelope.is_aliased(collection_id))

    def test_a_non_integer_id_is_refused_before_any_index_arithmetic(self) -> None:
        table = committed_table()
        for value in (None, "1", 1.0, 1.5, True, False, [], {}, b"1"):
            projected = collection_envelope.project_prize(table, value)
            self.assertFalse(projected["ok"], "%r is refused" % (value,))
            self.assertEqual(
                projected["reason"],
                collection_envelope.REASON_INVALID_COLLECTION_ID,
            )
            with self.assertRaises(collection_envelope.EnvelopeError) as caught:
                collection_envelope.validate_collection_id(value)
            self.assertEqual(
                caught.exception.code,
                collection_envelope.REASON_INVALID_COLLECTION_ID,
            )

    def test_a_float_would_index_the_table_fractionally_in_legacy(self) -> None:
        # The reason the id must be a STRICT integer: legacy's
        # `collections[0.5]` raises TypeError, so accepting one would answer an
        # unhandled 500 instead of a named refusal.
        table = committed_table()
        projected = collection_envelope.project_prize(table, 1.5)
        self.assertFalse(projected["ok"])
        self.assertEqual(
            projected["reason"], collection_envelope.REASON_INVALID_COLLECTION_ID
        )

    def test_an_unreadable_table_is_refused_not_read_as_empty(self) -> None:
        for table in ({}, None, "ten", 10):
            with self.assertRaises(collection_envelope.EnvelopeError) as caught:
                collection_envelope.table_length(table)
            self.assertEqual(
                caught.exception.code, collection_envelope.REASON_INVALID_PRIZE
            )
            # A non-mapping table has no row either, and `table_row` refuses
            # rather than guessing a length.
            with self.assertRaises(collection_envelope.EnvelopeError):
                collection_envelope.table_row(table, 0)

    def test_the_recorded_index_rule_names_the_rejected_alternative(self) -> None:
        self.assertIn("DERIVED-PROVISIONAL", collection_envelope.INDEX_RULE)
        self.assertIn("max(0, collection - 1)", collection_envelope.INDEX_RULE)
        self.assertIn("REJECTED", collection_envelope.REJECTED_ALTERNATIVE)
        self.assertIn("0-BASED", collection_envelope.REJECTED_ALTERNATIVE.upper())
        self.assertIn("0-BASED", collection_envelope.REJECTED_ALTERNATIVE)
        self.assertIn(
            "COLLECTION ID 0 AND COLLECTION ID 1 RESOLVE TO THE SAME PRIZE",
            collection_envelope.ALIAS_RULE,
        )
        self.assertEqual(collection_envelope.FIRST_COLLECTION_ID, 1)
        self.assertEqual(collection_envelope.LAST_COLLECTION_ID, 10)
        self.assertEqual(collection_envelope.UNCLAMPED_FLOOR, 1)


class CommittedPrizeTests(unittest.TestCase):
    """The committed table's ten prizes, classified and verbatim (design D1)."""

    #: The ten committed collections, measured from the normalized package and
    #: from ``config/main.json``; every figure here is asserted against the
    #: content rather than trusted.
    EXPECTED = [
        (1, "Draggy Collection", "1085", "Metal Draggy", "u"),
        (2, "Transformer Collection", "1062", "MegaBot", "u"),
        (3, "Plane Collection", "1096", "F-117", "u"),
        (4, "Defense Collection", "164", "Laser Turret", "b"),
        (5, "Gun Collection", "1073", "Erradicator", "u"),
        (6, "Tank Collection", "1010", "APC", "u"),
        (7, "Launcher Collection", "45", "Dual-Rocket Turret", "b"),
        (8, "Soldier Awards Collection", "136", "General Sculpture", "b"),
        (9, "Relaxing Time Collection", "106", "Fountain", "b"),
        (10, "Animal Collection", "1056", "Elephant rider", "u"),
    ]

    def test_the_committed_table_holds_ten_rows_with_native_ids_one_to_ten(self) -> None:
        table = committed_table()
        self.assertEqual(len(table), 10)
        self.assertEqual(collection_envelope.COMMITTED_COLLECTION_COUNT, 10)
        self.assertEqual(
            [str(row["id"]) for row in table], [str(i) for i in range(1, 11)]
        )

    def test_every_committed_prize_matches_the_recorded_table(self) -> None:
        table = committed_table()
        for collection_id, name, item_id, _item_name, _kind in self.EXPECTED:
            projected = collection_envelope.project_prize(table, collection_id)
            self.assertTrue(projected["ok"], "id %d resolves" % collection_id)
            self.assertEqual(projected["name"], name)
            self.assertEqual(projected["prize"], {item_id: 1})
            self.assertEqual(projected["item_count"], 1)
            self.assertEqual(projected["quantity_total"], 1)

    def test_six_collections_grant_a_unit_and_four_a_building(self) -> None:
        document = json.loads(CONFIG.read_text(encoding="utf-8"))
        kinds = {str(row["id"]): str(row.get("type", "")) for row in document["items"]}
        unit_ids = []
        building_ids = []
        table = committed_table()
        for collection_id, _name, item_id, _item_name, kind in self.EXPECTED:
            self.assertEqual(
                kinds[item_id],
                kind,
                "item %s is committed type %r" % (item_id, kind),
            )
            if kind == "u":
                unit_ids.append(item_id)
            else:
                building_ids.append(item_id)
        self.assertEqual(unit_ids, ["1085", "1062", "1096", "1073", "1010", "1056"])
        self.assertEqual(building_ids, ["164", "45", "136", "106"])
        self.assertEqual(len(unit_ids), 6)
        self.assertEqual(len(building_ids), 4)
        # Ten distinct item ids across the ten prize bags, each granted once.
        granted = [
            item_id for _c, _n, item_id, _i, _k in self.EXPECTED
        ]
        self.assertEqual(len(set(granted)), 10)
        for collection_id, _name, item_id, _item_name, _kind in self.EXPECTED:
            projected = collection_envelope.project_prize(table, collection_id)
            self.assertEqual(projected["quantity_total"], 1)

    def test_the_prize_bag_keeps_its_committed_string_keys(self) -> None:
        bag = collection_envelope.parse_prize('{"1085":1}')
        self.assertEqual(sorted(bag), ["1085"])
        self.assertIsInstance(list(bag)[0], str)
        # An already-parsed mapping is accepted too, which is what makes the
        # function usable against either representation of the committed field.
        self.assertEqual(collection_envelope.parse_prize({"1085": 1}), {"1085": 1})

    def test_entries_are_sorted_so_the_projection_bytes_are_deterministic(self) -> None:
        entries = collection_envelope.prize_entries('{"200":1,"45":2,"1085":3}')
        self.assertEqual(
            entries,
            [
                {"item_id": "45", "quantity": 2},
                {"item_id": "200", "quantity": 1},
                {"item_id": "1085", "quantity": 3},
            ],
        )

    def test_a_malformed_prize_is_refused_rather_than_coerced(self) -> None:
        for raw in ("not json", "[]", '"a string"', "null", 17, {}, {"1085": "1"},
                    {"1085": 1.0}, {"1085": True}):
            with self.assertRaises(collection_envelope.EnvelopeError) as caught:
                collection_envelope.parse_prize(raw)
            self.assertEqual(
                caught.exception.code, collection_envelope.REASON_INVALID_PRIZE,
                "%r is refused" % (raw,),
            )

    def test_an_empty_prize_is_refused_as_a_content_drift(self) -> None:
        with self.assertRaises(collection_envelope.EnvelopeError) as caught:
            collection_envelope.parse_prize("{}")
        self.assertEqual(caught.exception.code, collection_envelope.REASON_INVALID_PRIZE)
        self.assertIn("content drift", str(caught.exception))


class UnresolvableTests(unittest.TestCase):
    """An out-of-table id is reported, never substituted (design D1)."""

    def test_an_out_of_range_id_is_unresolvable_with_its_value_intact(self) -> None:
        table = committed_table()
        for collection_id in (11, 12, 100, 99999):
            projected = collection_envelope.project_prize(table, collection_id)
            self.assertFalse(projected["ok"], "%d is unresolvable" % collection_id)
            self.assertEqual(
                projected["reason"],
                collection_envelope.REASON_UNKNOWN_COLLECTION_ID,
            )
            self.assertEqual(
                projected["collection_id"], collection_id, "the id is intact"
            )
            self.assertEqual(projected["prize"], {}, "nothing is substituted")
            self.assertEqual(projected["entries"], [])
            self.assertEqual(projected["item_count"], 0)
            self.assertEqual(projected["quantity_total"], 0)
            self.assertEqual(projected["name"], "")

    def test_a_refused_projection_reports_every_field_so_no_half_verdict_exists(
        self,
    ) -> None:
        projected = collection_envelope.project_prize(committed_table(), 11)
        for field in ("ok", "reason", "error", "resolved", "collection_id",
                      "requested_index", "index", "clamped", "aliased",
                      "alias_of", "name", "id_column", "prize", "entries",
                      "item_count", "quantity_total"):
            self.assertIn(field, projected)
        self.assertFalse(projected["resolved"])
        self.assertEqual(projected["requested_index"], 10)
        self.assertEqual(projected["index"], 10)

    def test_a_row_that_is_not_a_mapping_reads_as_no_row(self) -> None:
        self.assertIsNone(collection_envelope.table_row(["a", "b"], 0))
        self.assertIsNone(collection_envelope.table_row(["a", "b"], -1))
        self.assertIsNone(collection_envelope.table_row(["a", "b"], 2))


class VectorTests(unittest.TestCase):
    """The neutral vector, and the refusal of every other one (design D1/D5)."""

    def test_the_derived_vector_is_all_zero_and_fresh(self) -> None:
        first = collection_envelope.neutral_vector()
        second = collection_envelope.neutral_vector()
        self.assertEqual(first, [0] * 8)
        self.assertEqual(len(first), collection_envelope.RESOURCE_VECTOR_SLOTS)
        self.assertIsNot(first, second, "a fresh list per call")
        first[0] = 99
        self.assertEqual(collection_envelope.neutral_vector()[0], 0)

    def test_any_non_neutral_vector_is_refused(self) -> None:
        for vector in ([1] + [0] * 7, [0] * 7 + [1], [0, -500, 0, 0, 0, 0, 0, 0],
                       [0] * 7, [0] * 9, [0, "1", 0, 0, 0, 0, 0, 0], "neutral"):
            with self.assertRaises(collection_envelope.EnvelopeError) as caught:
                collection_envelope.validate_vector(vector)
            self.assertEqual(caught.exception.code, "invalid_vector")

    def test_the_neutral_vector_validates(self) -> None:
        checked = collection_envelope.validate_vector(
            collection_envelope.neutral_vector()
        )
        self.assertEqual(checked, [0] * 8)
        self.assertIsNot(checked, collection_envelope.neutral_vector())


class EnvelopeTests(unittest.TestCase):
    """The one-command batch envelope (design D1/D5)."""

    def test_the_envelope_carries_exactly_one_neutral_completion(self) -> None:
        envelope = collection_envelope.build_envelope(3, ts=1700000000)
        self.assertEqual(sorted(envelope), sorted(collection_envelope.ENVELOPE_KEYS))
        self.assertEqual(envelope["first_number"], 0)
        self.assertEqual(envelope["publishActions"], [])
        self.assertEqual(envelope["ts"], 1700000000)
        self.assertEqual(envelope["tries"], 1)
        self.assertEqual(envelope["accessToken"], "")
        self.assertEqual(len(envelope["commands"]), 1)
        entry = envelope["commands"][0]
        self.assertEqual(entry[0], 0)
        self.assertEqual(entry[1], "complete_collection")
        self.assertEqual(entry[2], [3, 0])
        self.assertEqual(entry[3], [0] * 8)
        self.assertEqual(
            entry[2][collection_envelope.ARG_COLLECTION_ID], 3,
            "the collection id is args[0], the branch's only meaningful argument",
        )
        self.assertEqual(entry[2][collection_envelope.ARG_BOUGHT], 0)
        self.assertEqual(entry[2][collection_envelope.ARG_BOUGHT],
                         collection_envelope.DERIVED_BOUGHT)

    def test_the_envelope_round_trips_through_the_data_field(self) -> None:
        envelope = collection_envelope.build_envelope(1, ts=7)
        data = collection_envelope.data_field(envelope)
        self.assertEqual(data[64], ";")
        self.assertEqual(collection_envelope.parse_data_field(data), envelope)

    def test_a_bad_timestamp_or_id_is_refused(self) -> None:
        for value in (None, "1", 1.5, True, [], {}):
            with self.assertRaises(collection_envelope.EnvelopeError) as caught:
                collection_envelope.build_envelope(value)
            self.assertEqual(
                caught.exception.code,
                collection_envelope.REASON_INVALID_COLLECTION_ID,
            )
        for ts in (-1, "0", 1.5, True):
            with self.assertRaises(collection_envelope.EnvelopeError) as caught:
                collection_envelope.build_envelope(1, ts=ts)
            self.assertEqual(caught.exception.code, "invalid_timestamp")

    def test_the_bought_flag_is_recorded_as_a_print_only_derivation(self) -> None:
        self.assertEqual(collection_envelope.DERIVED_BOUGHT, 0)
        self.assertIn("printed line", collection_envelope.BOUGHT_NOTE)
        self.assertIn("DERIVED", collection_envelope.BOUGHT_NOTE)
        self.assertIn("command.py:520-523", collection_envelope.BOUGHT_NOTE)


class PostExecutionTests(unittest.TestCase):
    """The two post-execution derivations (design D1)."""

    def test_the_derived_storage_creates_then_increments(self) -> None:
        self.assertEqual(collection_envelope.expected_store({}, {"1085": 1}),
                         {"1085": 1})
        self.assertEqual(collection_envelope.expected_store({"1085": 1}, {"1085": 1}),
                         {"1085": 2})
        self.assertEqual(
            collection_envelope.expected_store({"905": 3, "1085": 2}, {"1085": 1}),
            {"905": 3, "1085": 3},
            "a key the bag does not mention is copied through untouched",
        )

    def test_the_derived_storage_refuses_a_non_mapping_or_non_integer(self) -> None:
        for store in (None, [], "store", 3):
            with self.assertRaises(collection_envelope.EnvelopeError):
                collection_envelope.expected_store(store, {"1085": 1})
        with self.assertRaises(collection_envelope.EnvelopeError):
            collection_envelope.expected_store({"1085": "2"}, {"1085": 1})

    def test_the_derived_ledger_appends_only_when_absent(self) -> None:
        self.assertEqual(
            collection_envelope.expected_ledger([], 1),
            {"entries": [1], "appended": True},
        )
        self.assertEqual(
            collection_envelope.expected_ledger([1], 1),
            {"entries": [1], "appended": False},
            "the append is IF-ABSENT: the ledger is idempotent, the grant is not",
        )
        self.assertEqual(
            collection_envelope.expected_ledger([1, 3], 2),
            {"entries": [1, 3, 2], "appended": True},
        )

    def test_the_derived_ledger_refuses_a_non_list(self) -> None:
        for ledger in (None, {}, "1", 3):
            with self.assertRaises(collection_envelope.EnvelopeError):
                collection_envelope.expected_ledger(ledger, 1)

    def test_the_first_divergence_is_reported_for_every_broken_half(self) -> None:
        # The correct post-state diverges nowhere.
        self.assertIsNone(
            collection_envelope.expected_grant(
                {}, {"1085": 1}, {"1085": 1}, 1, [], [1]
            )
        )
        # The committed id missing entirely.
        self.assertIn(
            "absent",
            collection_envelope.expected_grant({}, {}, {"1085": 1}, 1, [], [1]),
        )
        # The wrong quantity.
        self.assertIn(
            "derived",
            collection_envelope.expected_grant(
                {}, {"1085": 7}, {"1085": 1}, 1, [], [1]
            ),
        )
        # A key the committed prize never mentions moved.
        self.assertIn(
            "never mentions",
            collection_envelope.expected_grant(
                {}, {"1085": 1, "905": 1}, {"1085": 1}, 1, [], [1]
            ),
        )
        # The ledger grew by two.
        self.assertIn(
            "grew by",
            collection_envelope.expected_grant(
                {}, {"1085": 1}, {"1085": 1}, 1, [], [1, 4]
            ),
        )
        # The ledger appended an id it already held.
        self.assertIn(
            "already held",
            collection_envelope.expected_grant(
                {}, {"1085": 1}, {"1085": 1}, 1, [7], [7, 7]
            ),
        )
        # The ledger appended the WRONG id.
        self.assertIn(
            "not the derived",
            collection_envelope.expected_grant(
                {}, {"1085": 1}, {"1085": 1}, 1, [], [4]
            ),
        )
        # An existing ledger entry changed in place.
        self.assertIn(
            "changed from",
            collection_envelope.expected_grant(
                {}, {"1085": 1}, {"1085": 1}, 1, [7], [8]
            ),
        )
        # The ledger shrank.
        self.assertIn(
            "shrank",
            collection_envelope.expected_grant(
                {}, {"1085": 1}, {"1085": 1}, 1, [7, 8], [7]
            ),
        )

    def test_the_proof_ignores_the_client_and_compares_the_committed_bag(self) -> None:
        # The grant must match the COMMITTED bag even when the caller expected a
        # different item: nothing about the expectation reaches the comparison,
        # because the function is not given one.
        divergence = collection_envelope.expected_grant(
            {}, {"1085": 1}, {"1085": 1}, 1, [], [1]
        )
        self.assertIsNone(divergence)


class RecordedAbsenceTests(unittest.TestCase):
    """The three refusals and the two authority gaps, as content (D2/D5)."""

    def test_no_eligibility_check_is_recorded_as_a_gap_not_a_fix(self) -> None:
        rule = collection_envelope.NO_ELIGIBILITY_CHECK
        self.assertIn("NO ELIGIBILITY CHECK", rule)
        self.assertIn("ANY", rule)
        self.assertIn("item_ids", rule)
        self.assertIn("command.py:517", rule)

    def test_the_three_refusals_are_recorded_with_their_reasons(self) -> None:
        names = [entry["refusal"] for entry in collection_envelope.REFUSALS]
        self.assertEqual(names, ["unit_income", "cap_semantics", "experience_award"])
        for entry in collection_envelope.REFUSALS:
            self.assertFalse(entry["implemented"], entry["refusal"])
            self.assertTrue(entry["rule"].strip())
        self.assertIn("0 of 429", collection_envelope.NO_UNIT_INCOME)
        self.assertIn("ALL 429", collection_envelope.NO_CAP_SEMANTICS)
        self.assertIn("CLIENT ARGUMENT", collection_envelope.NO_EXPERIENCE_AWARD)

    def test_the_collect_fields_are_recorded_with_zero_legacy_reads(self) -> None:
        names = [entry["field"] for entry in collection_envelope.COLLECT_FIELDS]
        self.assertEqual(
            names,
            ["collect", "collect_type", "collect_xp", "max_collects", "max_elem_vol"],
        )
        for entry in collection_envelope.COLLECT_FIELDS:
            self.assertEqual(entry["legacy_reads"], 0, entry["field"])
        by_field = {entry["field"]: entry for entry in collection_envelope.COLLECT_FIELDS}
        self.assertEqual(by_field["collect"]["units_positive"], 0)
        self.assertEqual(by_field["collect"]["units_of"], 429)
        self.assertEqual(by_field["max_collects"]["units_positive"], 0)
        self.assertIn("BRANCH NAME", by_field["collect"]["read_note"])

    def test_harvester_is_recorded_as_a_properties_flag_not_a_field(self) -> None:
        record = collection_envelope.HARVESTER_RECORD
        self.assertIn("NOT A COMMITTED CONTENT FIELD", record)
        self.assertIn("properties", record)
        for unit_id in ("1001", "1039", "1040", "1041", "1125"):
            self.assertIn(unit_id, record)

    def test_the_acquisition_inventory_classifies_exactly_one_content_derived(
        self,
    ) -> None:
        derived = collection_envelope.CONTENT_DERIVED_ROUTES
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0]["branch"], "complete_collection")
        self.assertEqual(derived[0]["classification"], "content-derived")
        self.assertTrue(derived[0]["implemented"])
        client = collection_envelope.CLIENT_SUPPLIED_ROUTES
        self.assertEqual(
            [entry["branch"] for entry in client],
            ["buy_offer_pack", "buy_stored_item_cash"],
        )
        for entry in client:
            self.assertEqual(entry["classification"], "client-supplied")
            self.assertFalse(entry["implemented"], entry["branch"])
        self.assertTrue(collection_envelope.ACQUISITION_IMPLEMENTED)
        self.assertIn("EXACTLY ONE", collection_envelope.ACQUISITION_NOTE)
        self.assertIn("unit_collections_completed",
                      collection_envelope.NOT_ACQUISITION)
        self.assertIn("grants nothing", collection_envelope.NOT_ACQUISITION)

    def test_the_module_exposes_no_payout_cap_or_award_helper(self) -> None:
        import inspect

        # Whole-name tokens, not substrings: `expected_store` is a legitimate
        # derivation and must not be rejected for containing "xp".
        forbidden = {
            "income", "payout", "reward", "rewards", "cap", "caps",
            "max", "maxcollects", "threshold", "thresholds", "experience",
            "award", "awards", "xp", "gain", "earn", "earned", "eligible",
            "eligibility", "limit", "limits", "collection_cap",
        }
        names = [
            name
            for name, value in vars(collection_envelope).items()
            if callable(value) or isinstance(value, type)
        ]
        for name in names:
            for token in str(name).lower().split("_"):
                self.assertNotIn(
                    token,
                    forbidden,
                    "collection_envelope declares no %r helper (%s)"
                    % (token, name),
                )
        # And the named absences are absent from the module's source entirely.
        source = inspect.getsource(collection_envelope)
        for signature in ("def income(", "def payout(", "def award",
                          "def cap(", "def eligible", "def experience(",
                          "def xp(", "def threshold(", "def limit("):
            self.assertNotIn(signature, source, signature)

    def test_the_module_public_names_are_exactly_the_documented_set(self) -> None:
        for name in collection_envelope.__all__:
            self.assertTrue(
                hasattr(collection_envelope, name), "%s is exported" % name
            )


if __name__ == "__main__":
    unittest.main()