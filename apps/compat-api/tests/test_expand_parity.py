#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/expand`` vs the executed-legacy
expand fixture (OpenSpec task 2.4).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any socket
tries to connect), and ``test_no_server_is_running`` asserts that neither the
legacy port (5055) nor the Compatibility API port (5056) is listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-expand/`` — one real ``expand`` command
carrying the **content-derived debit** ``[0, 0, 0, 0, 0, 0, 0, 0]`` (the
committed free row for expansion id ``0``: ``coins 0`` / ``cash 0``) executed
by the legacy server in a disposable copy against the fresh-player corpus,
whose owned-expansions ledger is ``[35, 36, 45, 46]``.  The endpoint derives
the very same envelope from the very same module, so the replay compares:

* the response ``result`` against the captured legacy response body;
* the response ``expansions_before`` against the captured **before**-state
  ledger, exactly;
* the response ``expansions_after`` against the captured **after**-state
  ledger, exactly — the two-part proof's structural half, with no
  normalization at all;
* the response ``debit`` against the recorded request's resource vector,
  exactly;
* the response ``price`` against the committed schedule row the derivation
  read, exactly;
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable, and the captured movement is the
  derived debit — which is nothing);
* the corpus save after execution against the captured after-state, leaf for
  leaf, **with no normalization whatsoever** — this fixture's recorded state
  carries no time-dependent leaf, so the whole after-state must match
  exactly;
* the shared derivation against the recorded request envelope, exactly (the
  recorded ``ts`` is passed back into the derivation).

**No clock normalization exists in this suite**, and that is the point: an
expansion writes an int the client sent into a list and the derived debit is
the all-zero vector, so the recorded state carries no wall-clock reading at
all — unlike the collect fixture, whose addressed row carried the collection
instant.  A leaf-level diff of the captured before- and after-states proves
it: exactly **one** leaf differs, and it is the appended id.

The parity claim covers this one recorded transaction against the
fresh-player corpus (see the fixture README's claim limits).
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import expand_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-expand"
STEP = "command_expand"
LOGIN_STEP = "login_post"
FIXTURE_EXPANSION_ID = 0
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_EXPECTED_BEFORE = [35, 36, 45, 46]
FIXTURE_EXPECTED_AFTER = [35, 36, 45, 46, 0]
FIXTURE_PRICE = {"coins": 0, "cash": 0, "neighbors": 0, "inventory_qte": 0}
# A second pair of free indexes, used by the follow-up replays so the module's
# shared corpus stays readable and the fixture's own id keeps its meaning.
SECOND_INDEX = 1
THIRD_INDEX = 2
FOURTH_INDEX = 3
# Stored resource name -> index in the legacy 8-slot vector, the mapping the
# recorded request's debit is compared through slot by slot.
SLOT_OF = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5, "cash": 6, "mana": 7}

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


def load_fixture() -> Dict[str, Any]:
    base = FIXTURES / "steps" / STEP
    return {
        "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
        "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
        "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
        "meta": json.loads(
            (base / "response.meta.json").read_text(encoding="utf-8")
        ),
        "body": (base / "response.body").read_bytes(),
        "manifest": json.loads(
            (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
        ),
    }


def recorded_envelope() -> Dict[str, Any]:
    """The executed legacy envelope, parsed from the recorded ``data`` field.

    Parsing goes through :func:`expand_envelope.parse_data_field`, which also
    verifies the recorded 64-hex digest against the payload.
    """
    return expand_envelope.parse_data_field(FIXTURE["request"]["form"]["data"])


def recorded_intent() -> Dict[str, Any]:
    """The recorded intent, derived from the recorded command list."""
    envelope = recorded_envelope()
    entry = envelope["commands"][0]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "expansion_id": entry[2][0],
        "vector": entry[3],
        "command": entry[1],
        "map_id": entry[0],
    }


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE, FIXTURE
    ORIGINAL_CWD = os.getcwd()
    FIXTURE = load_fixture()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("an expansion execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def expand_town(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/expand", json=payload)  # type: ignore[union-attr]


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
    """The seven slots the endpoint reports, read from a save document."""
    first_map = document["maps"][0]
    return {
        "xp": first_map["xp"],
        "gold": first_map["gold"],
        "wood": first_map["wood"],
        "oil": first_map["oil"],
        "steel": first_map["steel"],
        "cash": document["playerInfo"]["cash"],
        "mana": document["privateState"]["mana"],
    }


def leaf_differences(left: Any, right: Any) -> List[str]:
    """Every JSON-pointer leaf at which two documents differ.

    Unlike the delivered collect suite's version, a list of **unequal** length
    is walked element by element rather than reported whole, so the single
    appended expansion id surfaces as the one leaf
    ``/maps/0/expansions/4`` instead of the whole ``/maps/0/expansions`` array.
    An element present on only one side is reported at its own index, so a
    pure append can never hide behind a length mismatch.
    """

    def walk(one: Any, other: Any, path: str, out: List[str]) -> None:
        if isinstance(one, dict) and isinstance(other, dict):
            for key in sorted(set(one) | set(other)):
                if key not in one:
                    out.append("%s/%s" % (path, key))
                    continue
                if key not in other:
                    out.append("%s/%s" % (path, key))
                    continue
                walk(one[key], other[key], "%s/%s" % (path, key), out)
        elif isinstance(one, list) and isinstance(other, list):
            for index in range(max(len(one), len(other))):
                child = "%s/%d" % (path, index)
                if index >= len(one) or index >= len(other):
                    out.append(child)
                    continue
                walk(one[index], other[index], child, out)
        elif one != other:
            out.append(path or "/")

    paths: List[str] = []
    walk(left, right, "", paths)
    return paths


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_recorded_before_state_equals_the_committed_seed(self) -> None:
        # The replay corpus is seeded from tests/saves/fresh-player.json, so
        # the fixture's before-state must be that same document.
        self.assertEqual(FIXTURE["before"], harness.load_seed())
        self.assertEqual(
            FIXTURE["before"]["maps"][0]["expansions"], FIXTURE_EXPECTED_BEFORE  # type: ignore[index]
        )
        self.assertEqual(len(FIXTURE["before"]["maps"][0]["items"]), 40)  # type: ignore[index]
        # The login step left the corpus untouched.
        login_after = json.loads(
            (FIXTURES / "steps" / LOGIN_STEP / "after.json").read_text(encoding="utf-8")
        )
        login_before = json.loads(
            (FIXTURES / "steps" / LOGIN_STEP / "before.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(login_after, login_before)

    def test_recorded_envelope_is_exactly_the_shared_derivation(self) -> None:
        intent = recorded_intent()
        envelope = recorded_envelope()

        # The one time-dependent input: a positive integer, held fixed below.
        # It is the ONLY clock anywhere in this fixture, and it is an envelope
        # field legacy parses and never reads.
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)

        # The debit is the addressed id's own committed schedule row, resolved
        # through the loaded configuration, never a client value.
        self.assertEqual(
            BOOT.expansion_price(FIXTURE_EXPANSION_ID), FIXTURE_PRICE  # type: ignore[union-attr]
        )
        self.assertEqual(BOOT.expansion_price_count(), 98)  # type: ignore[union-attr]
        debit = expand_envelope.resource_vector_for(
            BOOT.expansion_price(FIXTURE_EXPANSION_ID)  # type: ignore[union-attr]
        )
        self.assertEqual(debit, [0] * 8)
        # The requirement rule the endpoint enforces, checked against the real
        # schedule: the fixture's own row is purchasable.
        self.assertEqual(
            expand_envelope.unmet_requirements(
                BOOT.expansion_price(FIXTURE_EXPANSION_ID)  # type: ignore[union-attr]
            ),
            [],
        )
        rebuilt = expand_envelope.build_envelope(
            expansion_id=intent["expansion_id"], vector=debit, ts=envelope["ts"]
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        self.assertEqual(sorted(rebuilt), sorted(expand_envelope.ENVELOPE_KEYS))
        self.assertEqual(rebuilt["first_number"], 0)
        self.assertEqual(rebuilt["publishActions"], [])
        self.assertEqual(rebuilt["tries"], 1)
        self.assertEqual(rebuilt["accessToken"], "")
        # The single command, its argument, and its derived debit.
        self.assertEqual(intent["command"], "expand")
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["expansion_id"], FIXTURE_EXPANSION_ID)
        self.assertEqual(intent["vector"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(len(envelope["commands"]), 1)
        # The six slots this derivation can never fill are zero (design D2),
        # and the whole vector is a debit.
        for slot in expand_envelope.ALWAYS_ZERO_SLOTS:
            with self.subTest(slot=slot):
                self.assertEqual(intent["vector"][slot], 0)
        for slot, value in enumerate(intent["vector"]):
            with self.subTest(slot=slot):
                self.assertLessEqual(value, 0)

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_expansion(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]

        # The ledger grew by exactly one entry, equal to the sent id, appended
        # at the end, with the existing four unchanged, in order, and not
        # deduplicated.
        self.assertEqual(after["maps"][0]["expansions"], FIXTURE_EXPECTED_AFTER)  # type: ignore[index]
        self.assertEqual(after["maps"][0]["expansions"][:-1], FIXTURE_EXPECTED_BEFORE)  # type: ignore[index]
        self.assertEqual(after["maps"][0]["expansions"][-1], FIXTURE_EXPANSION_ID)  # type: ignore[index]
        self.assertEqual(len(after["maps"][0]["expansions"]), 5)  # type: ignore[index]
        self.assertEqual(
            len(set(after["maps"][0]["expansions"])), 5  # type: ignore[index]
        )
        # Not sorted: the appended 0 is last even though it is the smallest.
        self.assertNotEqual(after["maps"][0]["expansions"], sorted(after["maps"][0]["expansions"]))  # type: ignore[index]
        # Every id the corpus owns survived verbatim.
        for index, expansion_id in enumerate(FIXTURE_EXPECTED_BEFORE):
            with self.subTest(expansion_id=expansion_id):
                self.assertEqual(after["maps"][0]["expansions"][index], expansion_id)  # type: ignore[index]

        # No placement is added, removed, or changed.
        self.assertEqual(len(after["maps"][0]["items"]), 40)  # type: ignore[index]
        self.assertEqual(
            sorted(after["maps"][0]["items"], key=int),  # type: ignore[index]
            sorted(before["maps"][0]["items"], key=int),  # type: ignore[index]
        )
        for key in before["maps"][0]["items"]:  # type: ignore[index]
            with self.subTest(key=key):
                self.assertEqual(
                    after["maps"][0]["items"][key],  # type: ignore[index]
                    before["maps"][0]["items"][key],  # type: ignore[index]
                )
        # The other map scalars the executed probe recorded as untouched.
        self.assertEqual(after["maps"][0]["level"], before["maps"][0]["level"])  # type: ignore[index]
        self.assertEqual(
            after["maps"][0]["increasedPopulation"],  # type: ignore[index]
            before["maps"][0]["increasedPopulation"],  # type: ignore[index]
        )
        self.assertNotIn("map_sizes", after["maps"][0])  # type: ignore[index]
        self.assertNotIn("map_sizes", before["maps"][0])  # type: ignore[index]
        # The whole key set, so no un-named field could have moved.
        self.assertEqual(
            sorted(after["maps"][0]), sorted(before["maps"][0])  # type: ignore[index]
        )
        for field in sorted(set(before["maps"][0]) | set(after["maps"][0])):  # type: ignore[index]
            if field == "expansions":
                continue
            with self.subTest(field=field):
                self.assertEqual(
                    after["maps"][0].get(field),  # type: ignore[index]
                    before["maps"][0].get(field),  # type: ignore[index]
                )
        # An expansion stores nothing, buys nothing, and kills nothing.
        self.assertEqual(after["maps"][0]["store"], before["maps"][0]["store"])  # type: ignore[index]
        self.assertEqual(after["privateState"], before["privateState"])  # type: ignore[index]
        self.assertEqual(after["playerInfo"], before["playerInfo"])  # type: ignore[index]
        # Every stored resource is unchanged, because the derived debit is the
        # all-zero vector.
        self.assertEqual(
            resources_of(after),
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
        self.assertEqual(resources_of(after), resources_of(before))
        movement = {
            name: resources_of(after)[name] - resources_of(before)[name]
            for name in resources_of(after)
        }
        self.assertEqual(
            movement,
            {
                "cash": 0,
                "gold": 0,
                "mana": 0,
                "oil": 0,
                "steel": 0,
                "wood": 0,
                "xp": 0,
            },
        )

    def test_the_recorded_state_carries_exactly_one_differing_leaf(self) -> None:
        """The absence of any clock reading, proved.

        Exactly **one** leaf differs between the recorded before- and
        after-states: the appended expansion id.  The collect fixture's
        after-state carried three (the collection instant plus two resources);
        this one carries one, and the state is therefore byte-stable across
        reruns with no normalization at all.
        """
        differences = leaf_differences(FIXTURE["before"], FIXTURE["after"])
        self.assertEqual(differences, ["/maps/0/expansions/4"])
        # The reported leaf is the appended slot itself: it exists in the
        # after-state and not in the before-state.
        self.assertEqual(
            len(FIXTURE["before"]["maps"][0]["expansions"]),  # type: ignore[index]
            len(FIXTURE_EXPECTED_BEFORE),
        )
        self.assertEqual(
            FIXTURE["after"]["maps"][0]["expansions"][4],  # type: ignore[index]
            FIXTURE_EXPANSION_ID,
        )
        # The map-level timestamp is not rewritten either (apply_resources'
        # write is commented out in legacy, engine.py:269).
        self.assertEqual(
            FIXTURE["after"]["maps"][0]["timestamp"],  # type: ignore[index]
            FIXTURE["before"]["maps"][0]["timestamp"],  # type: ignore[index]
        )

    def test_the_manifest_records_all_three_probes(self) -> None:
        """Probe 1 establishes the single append and the clamp's reachability;
        probe 2 is the evidence for the range and duplicate guards; probe 3 for
        the structural id check."""
        probes = FIXTURE["manifest"]["probes"]
        self.assertEqual(len(probes), 3)
        first, second, third = probes
        self.assertEqual(first["probe"], 1)
        self.assertIn("expand(4)", first["commands"][0])
        self.assertIn("expand(5)", first["commands"][1])
        self.assertIn("[0,0,-5000,0,0,0,-8,0]", first["commands"][1])
        self.assertEqual(first["expansions_after"], [35, 36, 45, 46, 4, 5])
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
        self.assertIn("success", second["responses"])
        self.assertIn("NO. The server accepts 999", second["established"])
        self.assertIn("unknown_expansion_id", second["consequence"])
        self.assertIn("already_expanded", second["consequence"])
        self.assertEqual(third["probe"], 3)
        self.assertIn('int("abc")', third["response"])
        self.assertIn("unhandled HTTP 500", third["response"])
        self.assertIn("invalid_expansion_id", third["consequence"])

    def test_the_manifest_records_the_derived_debit_and_the_schedule(self) -> None:
        intent_block = FIXTURE["manifest"]["intent"]
        self.assertEqual(intent_block["expansion_id"], FIXTURE_EXPANSION_ID)
        self.assertIn("expansion id 0", intent_block["target_rule"])
        self.assertIn("none of them could have been bought", intent_block["target_rule"])
        derived = intent_block["derived"]
        self.assertEqual(derived["command"], "expand")
        self.assertEqual(derived["args"], [FIXTURE_EXPANSION_ID])
        self.assertEqual(derived["resources_changed"], FIXTURE_EXPECTED_VECTOR)
        self.assertTrue(derived["vector_is_a_debit"])
        self.assertEqual(derived["price"], FIXTURE_PRICE)
        self.assertEqual(
            derived["resource_vector"],
            "unknown, xp, gold, wood, oil, steel, cash, mana",
        )
        self.assertEqual(
            derived["always_zero_slots"], list(expand_envelope.ALWAYS_ZERO_SLOTS)
        )
        self.assertEqual(
            derived["envelope_keys"],
            ["accessToken", "commands", "first_number", "publishActions", "tries", "ts"],
        )
        # The committed schedule, and the corpus consequence.
        schedule = derived["schedule"]
        self.assertEqual(schedule["key"], "expansion_prices")
        self.assertEqual(schedule["entries"], 98)
        self.assertFalse(schedule["stable_id"])
        self.assertEqual(schedule["id_space"], "the positional index 0..97")
        self.assertEqual(
            sorted(schedule["fields"]),
            ["cash", "coins", "inventory_qte", "neighbors"],
        )
        self.assertEqual(schedule["requirement_free_indexes"], [0, 1, 2, 3])
        self.assertEqual(schedule["zero_cost_indexes"], [0, 1, 2, 3])
        self.assertEqual(schedule["rows_recording_a_requirement"], 94)
        self.assertEqual(
            schedule["field_saturation_first_index"],
            {"coins": 14, "cash": 11, "neighbors": 18, "inventory_qte": 33},
        )
        self.assertEqual(
            schedule["first_index_whose_row_equals_the_last_row"], 33
        )
        self.assertEqual(schedule["unused_schedules"]["town_prices"], 4)
        self.assertEqual(schedule["unused_schedules"]["map_prices"], 4)
        # The price-field provenance, per field.
        price_fields = derived["price_fields"]
        self.assertIn("expansion_gold.jpg", price_fields["coins"])
        self.assertIn("ESTABLISHED", price_fields["coins"])
        self.assertIn("slot 2", price_fields["coins"])
        self.assertIn("slot 6", price_fields["cash"])
        for field in ("neighbors", "inventory_qte"):
            with self.subTest(field=field):
                self.assertIn("UNEVALUABLE", price_fields[field])
                self.assertIn("expansion_requirements_unmet", price_fields[field])
        # The decisions, each named and each marked with its provenance.
        decisions = derived["decisions"]
        for name in (
            "D1_id_space",
            "D2_gold_naming",
            "D3_requirements",
            "D4_land_gap",
            "D5_intent_and_proof",
            "D6_affordability",
        ):
            with self.subTest(decision=name):
                self.assertIn(name, decisions)
                self.assertTrue(decisions[name].strip())
        self.assertIn("DERIVED", decisions["D1_id_space"])
        self.assertIn("Rejected alternatives", decisions["D1_id_space"])
        self.assertIn("unknown_expansion_id", decisions["D1_id_space"])
        self.assertIn("already_expanded", decisions["D1_id_space"])
        self.assertIn("ESTABLISHED BY COMMITTED ASSET", decisions["D2_gold_naming"])
        self.assertIn("expansion_gold.jpg", decisions["D2_gold_naming"])
        self.assertIn("letter set", decisions["D2_gold_naming"])
        self.assertIn("DERIVED", decisions["D3_requirements"])
        self.assertIn("94 of the 98", decisions["D3_requirements"])
        self.assertIn("ZERO-COST", decisions["D3_requirements"])
        self.assertIn("NOT IMPLEMENTED and NOT CLAIMED", decisions["D4_land_gap"])
        self.assertIn("tile -> cell geometry", decisions["D4_land_gap"])
        self.assertIn("EXACTLY the derived debit", decisions["D5_intent_and_proof"])
        self.assertIn("Rejected alternative", decisions["D6_affordability"])
        self.assertIn("landed on 0", decisions["D6_affordability"])
        # The status line's established/derived split.
        status = derived["status"]
        self.assertIn("command.py:211-216", status)
        self.assertIn("clamp is REACHABLE", status)
        self.assertIn("NEVER that it is the price a coherent player pays", status)

    def test_the_manifest_records_the_claim_limits(self) -> None:
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertEqual(transaction["expansions_before"], FIXTURE_EXPECTED_BEFORE)
        self.assertEqual(transaction["expansions_after"], FIXTURE_EXPECTED_AFTER)
        self.assertEqual(transaction["expansion_id_sent"], FIXTURE_EXPANSION_ID)
        self.assertEqual(transaction["ledger_grew_by"], 1)
        self.assertTrue(transaction["existing_entries_unchanged"])
        self.assertFalse(transaction["existing_entries_reordered"])
        self.assertFalse(transaction["deduplicated"])
        self.assertEqual(transaction["placement_count_before"], 40)
        self.assertEqual(transaction["placement_count_after"], 40)
        self.assertEqual(transaction["map_level_before"], 1)
        self.assertEqual(transaction["map_level_after"], 1)
        self.assertFalse(transaction["map_sizes_present_before"])
        self.assertFalse(transaction["map_sizes_present_after"])
        self.assertEqual(transaction["increased_population_before"], 0)
        self.assertEqual(transaction["increased_population_after"], 0)
        self.assertEqual(transaction["store_after"], {})
        self.assertEqual(transaction["bought_units_before"], [])
        self.assertEqual(transaction["bought_units_after"], [])
        self.assertEqual(transaction["dead_heroes_after"], {})
        self.assertTrue(transaction["other_rows_unchanged"])
        self.assertTrue(transaction["other_map_fields_unchanged"])
        self.assertTrue(transaction["map_key_set_unchanged"])
        self.assertTrue(transaction["private_state_unchanged"])
        self.assertTrue(transaction["player_info_unchanged"])
        self.assertEqual(
            transaction["resource_delta"],
            {
                "cash": 0,
                "gold": 0,
                "mana": 0,
                "oil": 0,
                "steel": 0,
                "wood": 0,
                "xp": 0,
            },
        )
        self.assertEqual(transaction["response_body"], '{"result": "success"}')
        # The clamp and the requirements rule, both named.
        self.assertFalse(transaction["clamp_exercised"])
        self.assertIn("max(current + delta, 0)", transaction["clamp_note"])
        self.assertIn("probe 1", transaction["clamp_note"])
        self.assertIn("insufficient_resources", transaction["clamp_note"])
        self.assertTrue(transaction["requirements_rule_enforced"])
        self.assertIn(
            "expansion_requirements_unmet", transaction["requirements_note"]
        )
        self.assertIn("94 rows", transaction["requirements_note"])
        # The land gap, recorded as a gap and not as a feature.
        self.assertFalse(transaction["land_effect"])
        self.assertIn("unlock ledger", transaction["land_note"])
        self.assertIn("NOT claimed", transaction["land_note"])
        # What the branch writes.
        self.assertEqual(len(transaction["expand_writes"]), 3)
        self.assertIn("command.py:40", transaction["expand_writes"][0])
        self.assertIn("command.py:211-216", transaction["expand_writes"][1])
        self.assertIn("three references", transaction["expand_writes"][2])
        # The containment and cleanup records.
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertTrue(containment["working_tree_saves_unchanged"])
        self.assertTrue(containment["loopback_only"])
        self.assertTrue(containment["no_flash_browser_external_network"])
        self.assertTrue(containment["protected_fixtures"]["identical"])
        self.assertEqual(len(containment["protected_fixtures"]["paths"]), 9)
        self.assertEqual(
            containment["pre_combined_sha256"], containment["post_combined_sha256"]
        )
        self.assertTrue(FIXTURE["manifest"]["cleanup"]["server_stopped_within_run"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["startup_preserved_seed"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["login_preserved_seed"])
        # The intent block's land rule, and the schedule rule that names the
        # derived id space.
        intent_block = FIXTURE["manifest"]["intent"]
        self.assertIn("DERIVED", intent_block["schedule_rule"])
        self.assertIn("unknown_expansion_id", intent_block["schedule_rule"])
        self.assertIn("NOT APPLICABLE", intent_block["land_rule"])
        self.assertIn("unlock LEDGER", intent_block["land_rule"])
        self.assertIn("PopupExpandMC", intent_block["land_rule"])
        self.assertIn("btnBuyExpandTileMC", intent_block["land_rule"])
        self.assertIn("expansion_gold.jpg", intent_block["land_rule"])
        self.assertIn("known evidence gap", intent_block["land_rule"])

    def test_the_manifest_records_the_time_dependent_leaves(self) -> None:
        """The recorded **state** has no time-dependent leaf, and the manifest
        says so with an empty list rather than inventing one."""
        record = FIXTURE["manifest"]["time_dependent_fields"]
        self.assertEqual(record["state_leaves"], [])
        self.assertIn("carry NO ", record["rule"])
        self.assertIn("exactly these 8 paths", record["rule"])
        leaves = " ".join(record["leaves"])
        self.assertIn("/executed_at_utc in capture-manifest.json", leaves)
        self.assertIn("captured_at_utc", leaves)
        self.assertIn("/headers/Date", leaves)
        self.assertIn("the envelope ts", leaves)
        # Exactly eight named leaves, and not one of them in the state.
        self.assertEqual(len(record["leaves"]), 8)
        for leaf in record["leaves"]:
            with self.subTest(leaf=leaf):
                self.assertNotIn("after.json", leaf)
                self.assertNotIn("before.json", leaf)
        self.assertIn("no wall-clock reading", record["stable_by_derivation"])
        self.assertIn("applies NO clock normalization", record["documented_normalization"])


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the recorded intent replayed offline.

    The module shares one disposable corpus, so the mutating tests are ordered
    by name: ``test_a_...`` inspects the corpus at the fixture's before-state
    first, ``test_b_...`` replays the recorded transaction (its assertions
    require that before-state), and the follow-ups build on that result with
    their own dedicated free indexes.
    """

    def test_a_the_recorded_index_is_resolvable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rules agree with the recorded intent:
        the id prices from the committed schedule, records no requirement, and
        is not yet owned."""
        intent = recorded_intent()
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        self.assertEqual(BOOT.map_expansions(PID), FIXTURE_EXPECTED_BEFORE)  # type: ignore[union-attr]
        self.assertEqual(BOOT.expansion_price_count(), 98)  # type: ignore[union-attr]
        self.assertEqual(
            BOOT.expansion_price(intent["expansion_id"]), FIXTURE_PRICE  # type: ignore[union-attr]
        )
        self.assertNotIn(
            intent["expansion_id"],
            BOOT.map_expansions(PID),  # type: ignore[union-attr]
        )
        # The out-of-range and the duplicate cases the recorded intent is not:
        # both are refusals the legacy server would have accepted.
        self.assertIsNone(BOOT.expansion_price(98))  # type: ignore[union-attr]
        self.assertIn(35, BOOT.map_expansions(PID))  # type: ignore[union-attr]

    def test_b_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])

        response = expand_town(
            {"user_id": intent["user_id"], "expansion_id": intent["expansion_id"]}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    superset: both ledgers + the derived debit + the committed row +
        #    the current resources, design D5).
        legacy_body = json.loads(FIXTURE["body"])
        self.assertEqual(payload["result"], legacy_body["result"])
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        self.assertEqual(
            sorted(payload),
            sorted(
                [
                    "protocol",
                    "ok",
                    "game_version",
                    "server_time",
                    "result",
                    "expansions_before",
                    "expansions_after",
                    "debit",
                    "price",
                    "resources",
                ]
            ),
        )

        # 2. ``expansions_before`` equals the captured *before*-state ledger,
        #    exactly, and never aliases the live list (the legacy dispatcher
        #    appends to that very list in place).
        self.assertEqual(payload["expansions_before"], FIXTURE_EXPECTED_BEFORE)
        self.assertIsNot(payload["expansions_before"], BOOT.map_expansions(PID))  # type: ignore[union-attr]

        # 3. ``expansions_after`` equals the captured *after*-state ledger,
        #    exactly — the structural half of the two-part proof, with **no**
        #    normalization, because the state carries no clock reading.
        self.assertEqual(payload["expansions_after"], FIXTURE_EXPECTED_AFTER)
        self.assertEqual(
            payload["expansions_after"],
            payload["expansions_before"] + [FIXTURE_EXPANSION_ID],
        )
        self.assertEqual(payload["expansions_after"][:-1], FIXTURE_EXPECTED_BEFORE)
        self.assertNotEqual(
            payload["expansions_after"], sorted(payload["expansions_after"])
        )

        # 4. The derived debit equals the recorded request's vector exactly, and
        #    the committed row is the one the derivation read.
        self.assertEqual(payload["debit"], intent["vector"])
        self.assertEqual(payload["debit"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(payload["price"], FIXTURE_PRICE)
        for slot in expand_envelope.ALWAYS_ZERO_SLOTS:
            with self.subTest(slot=slot):
                self.assertEqual(payload["debit"][slot], 0)

        # 5. Resources equal the values read from the captured after-state, and
        #    the movement is exactly the recorded derived vector — which is
        #    nothing, so every one of the seven is unchanged.
        self.assertEqual(payload["resources"], resources_of(FIXTURE["after"]))
        movement = {
            name: payload["resources"][name] - resources_of(FIXTURE["before"])[name]
            for name in payload["resources"]
        }
        self.assertEqual(
            movement,
            {
                "cash": 0,
                "gold": 0,
                "mana": 0,
                "oil": 0,
                "steel": 0,
                "wood": 0,
                "xp": 0,
            },
        )
        for name, slot in SLOT_OF.items():
            with self.subTest(slot=slot):
                self.assertEqual(movement[name], intent["vector"][slot])

        # 6. The endpoint proved the expansion from the persisted save, not
        #    from its own copy of the ledger.
        raw_corpus_after = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(
            raw_corpus_after["maps"][0]["expansions"], payload["expansions_after"]  # type: ignore[index]
        )
        self.assertEqual(BOOT.map_expansions(PID), payload["expansions_after"])  # type: ignore[union-attr]

        # 7. The corpus save after execution equals the captured after-state
        #    for **every leaf, with no normalization at all** — the strongest
        #    form of the parity claim, and only possible because this fixture's
        #    state carries no clock reading.
        differences = harness.diff_documents(FIXTURE["after"], raw_corpus_after)
        self.assertEqual(differences, [])
        self.assertEqual(
            leaf_differences(FIXTURE["after"], raw_corpus_after), []
        )

        # 8. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_c_a_second_free_index_replays_the_same_derivation(self) -> None:
        """The endpoint's answer is a function of the addressed id, not of the
        fixture: a different committed free row produces the same derivation
        from its own committed content."""
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]

        response = expand_town(
            {"user_id": intent["user_id"], "expansion_id": SECOND_INDEX}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["expansions_before"],
            after_first["maps"][0]["expansions"],
        )
        self.assertEqual(
            payload["expansions_after"],
            after_first["maps"][0]["expansions"] + [SECOND_INDEX],
        )
        self.assertEqual(payload["debit"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(payload["price"], FIXTURE_PRICE)
        # The second append did not disturb the first, and the pre-existing
        # ids are still in their committed order.
        self.assertEqual(
            payload["expansions_after"][:5], FIXTURE_EXPECTED_AFTER
        )
        self.assertEqual(
            payload["expansions_after"][:-1], FIXTURE_EXPECTED_AFTER
        )
        self.assertEqual(len(payload["expansions_after"]), 6)
        # And still no resource moved.
        self.assertEqual(payload["resources"], resources_of(after_first))
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_d_the_requirements_refusal_keeps_the_replayed_ledger(self) -> None:
        """Design D3 replayed against the live corpus: a **priced** committed
        row — 94 of the 98 — is refused for its unevaluable requirement, and
        the ledger keeps the ids the earlier replays appended."""
        intent = recorded_intent()
        after_second = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        before_ledger = after_second["maps"][0]["expansions"]  # type: ignore[index]
        self.assertEqual(before_ledger, FIXTURE_EXPECTED_AFTER + [SECOND_INDEX])

        # Index 4 is a real committed row priced 2500 gold / 5 cash with
        # neighbors 1 / inventory_qte 1.
        row = BOOT.expansion_price(4)  # type: ignore[union-attr]
        self.assertEqual(row, {"coins": 2500, "cash": 5, "neighbors": 1, "inventory_qte": 1})

        response = expand_town({"user_id": intent["user_id"], "expansion_id": 4})

        self.assertEqual(response.status_code, 409)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "expansion_requirements_unmet")
        # The refused expansion left the ledger byte-identical: no append, and
        # no balance moved either.
        after_refusal = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(after_refusal["maps"][0]["expansions"], before_ledger)  # type: ignore[index]
        self.assertEqual(resources_of(after_refusal), resources_of(after_second))
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_e_the_duplicate_refusal_keeps_the_replayed_ledger(self) -> None:
        """Design D1's second guard replayed: an id the ledger already contains
        — including one an earlier replay just bought — is refused, so the
        ledger can never gain a repeat."""
        intent = recorded_intent()
        after_third = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        before_ledger = after_third["maps"][0]["expansions"]  # type: ignore[index]
        for owned in (FIXTURE_EXPECTED_AFTER[0], FIXTURE_EXPECTED_AFTER[-1], SECOND_INDEX):
            with self.subTest(owned=owned):
                response = expand_town(
                    {"user_id": intent["user_id"], "expansion_id": owned}
                )
                self.assertEqual(response.status_code, 409)
                body = response.get_json()
                self.assertEqual(body["error"]["code"], "already_expanded")
        after_refusals = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(after_refusals["maps"][0]["expansions"], before_ledger)  # type: ignore[index]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_f_the_replayed_transaction_matches_the_committed_fixture_shape(self) -> None:
        """The ledger the fixture records is the ledger the endpoint produces,
        and the response shape is the documented superset."""
        intent = recorded_intent()
        response = expand_town(
            {"user_id": intent["user_id"], "expansion_id": THIRD_INDEX}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # Identical response shape to the fixture's own transaction, only the
        # expansion id differs.
        self.assertEqual(
            sorted(payload),
            sorted(
                [
                    "protocol",
                    "ok",
                    "game_version",
                    "server_time",
                    "result",
                    "expansions_before",
                    "expansions_after",
                    "debit",
                    "price",
                    "resources",
                ]
            ),
        )
        self.assertEqual(payload["debit"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(payload["price"], FIXTURE_PRICE)
        self.assertEqual(payload["expansions_after"][-1], THIRD_INDEX)
        # The pre-existing ids are still in the committed order, with the three
        # replays' appends after them.
        self.assertEqual(
            payload["expansions_after"][:5], FIXTURE_EXPECTED_AFTER
        )
        self.assertEqual(
            payload["expansions_after"][5:],
            [SECOND_INDEX, THIRD_INDEX],
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_g_the_fourth_free_index_also_expands(self) -> None:
        """Every requirement-free committed row is purchasable, and each is
        appended at the end without touching the ids already there."""
        intent = recorded_intent()
        response = expand_town(
            {"user_id": intent["user_id"], "expansion_id": FOURTH_INDEX}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["expansions_after"][-1], FOURTH_INDEX)
        self.assertEqual(
            payload["expansions_after"][:4], FIXTURE_EXPECTED_BEFORE
        )
        self.assertEqual(payload["debit"], [0] * 8)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class ExpandParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        self.assertTrue((FIXTURES / "steps" / STEP / "request.json").is_file())
        self.assertTrue((FIXTURES / "steps" / LOGIN_STEP / "after.json").is_file())

    def test_the_fixture_readme_states_the_provenance_split_and_the_claims(
        self,
    ) -> None:
        """Task 1.3 plus the recorded claim limits."""
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn('{"result":"success"}', readme)
        self.assertIn("Established from committed legacy source", readme)
        self.assertIn("**Derived and never observed from the Flash client**", readme)
        # All three probes.
        self.assertIn("Probe 1", readme)
        self.assertIn("Probe 2", readme)
        self.assertIn("Probe 3", readme)
        self.assertIn("already_expanded", readme)
        self.assertIn("expansion_requirements_unmet", readme)
        self.assertIn("insufficient_resources", readme)
        # The decisions.
        for name in ("D1", "D2", "D3", "D4", "D5", "D6"):
            with self.subTest(decision=name):
                self.assertIn(name, readme)
        # The committed asset evidence and the derived debit.
        self.assertIn("expansion_gold.jpg", readme)
        self.assertIn("expansion_cash.jpg", readme)
        self.assertIn("PopupExpandMC", readme)
        self.assertIn("btnBuyExpandTileMC", readme)
        self.assertIn("[0,0,0,0,0,0,0,0]", readme)  # the recorded request
        self.assertIn("[0, 0, 0, 0, 0, 0, 0, 0]", readme)  # the derived debit
        # The land gap, named as a gap.
        self.assertIn("No claim is made about any area of the town", readme)
        self.assertIn("unlock ledger", readme)
        self.assertIn("known evidence gap", readme)
        self.assertIn("tile → cell geometry", readme)
        # The clamp and the corpus consequence, stated not hidden.
        self.assertIn("The clamp is not exercised by this fixture", readme)
        self.assertIn(
            "No id the corpus owns could have been bought", readme
        )
        self.assertIn("94 of the 98", readme)
        self.assertIn("0..3", readme)
        # The determinism claim and its verified leaf count.
        self.assertIn("no time-dependent field", readme)
        self.assertIn("exactly 8 differing file+pointer paths", readme)
        self.assertIn("state_leaves", readme)
        # The closure claims.
        self.assertIn("No Flash, Ruffle, ActionScript, or browser", readme)
        self.assertIn("no external network", readme)
        self.assertIn("no pixel-parity oracle", readme)

    def test_the_fixture_readme_records_the_executed_outcome(self) -> None:
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        # The ledger before and after, the invariants, and the single leaf.
        self.assertIn("`[35, 36, 45, 46]`", readme)
        self.assertIn("`[35, 36, 45, 46, 0]`", readme)
        self.assertIn("**exactly one** entry", readme)
        self.assertIn("stays `40`", readme)
        self.assertIn("`/maps/0/expansions/4`", readme)
        self.assertIn("byte-identical across reruns", readme)
        self.assertIn("**nine** already committed fixture", readme)

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "an expansion execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()
