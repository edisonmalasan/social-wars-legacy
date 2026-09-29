#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/collect`` vs the executed-legacy
collect fixture (OpenSpec task 2.4).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any socket
tries to connect), and ``test_no_server_is_running`` asserts that neither the
legacy port (5055) nor the Compatibility API port (5056) is listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-collect/`` — one real ``collect`` command
carrying the **content-derived** payout ``[0, 3, 0, 60, 0, 0, 0, 0]``
(``xp 1 x 3`` and ``wood 20 x 3``, the top committed ladder rung) executed by
the legacy server in a disposable copy against the fresh-player corpus, on the
placed **Tree** (item id 905) at map slot ``2`` anchored at ``(53,39)``.  The
endpoint derives the very same envelope from the very same module, so the
replay compares:

* the response ``result`` against the captured legacy response body;
* the response ``previous`` against the captured **before**-state row at that
  legacy key (entry for entry, no normalization);
* the response ``row`` against the captured **after**-state row at that key,
  field for field, with the row's re-stamped wall-clock collection instant
  documented and normalized (proved below);
* the response ``payout`` against the recorded request's resource vector,
  exactly;
* the response ``tier`` and ``reference_time`` against the committed ladder
  and the row's own pre-execution instant (the reference instant is a
  service-side value legacy never recorded, so it is derived here, not
  compared);
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable, and the captured movement is the
  derived payout);
* the corpus save after execution against the captured after-state, leaf for
  leaf, under the same documented normalization;
* the shared derivation against the recorded request envelope, exactly (the
  recorded ``ts`` is passed back into the derivation).

Documented time-dependent fields: **the state carries exactly one**, the
addressed row's re-stamped ``item[3]`` — the collection instant, written by
``collect``'s ``item[3] = time_now()`` and read by no branch as anything but
data (``command.py:145``).  Every other leaf of the recorded state is
byte-stable, which is asserted here by a leaf-level diff of the recorded
before- and after-states: exactly **three** leaves differ — the collection
instant and the two resources the derived payout pays.  The envelope ``ts``
inside the recorded request is the other time-dependent field; it is asserted
to be a positive integer before the envelope comparison and then held fixed by
passing it back into the derivation.

The parity claim covers this one recorded transaction against the
fresh-player corpus (see the fixture README's claim limits).
"""

from __future__ import annotations

import copy
import json
import os
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness

import collect_envelope
import compat_legacy
import compat_service

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-collect"
STEP = "command_collect"
LOGIN_STEP = "login_post"
FIXTURE_INDEX = 2
FIXTURE_ITEM_ID = 905  # Tree
FIXTURE_ANCHOR = (53, 39)
FIXTURE_COLLECT_AMOUNT = 20
FIXTURE_COLLECT_TYPE = "w"
FIXTURE_COLLECT_XP = 1
FIXTURE_EXPECTED_TIER = 3
FIXTURE_EXPECTED_VECTOR = [0, 3, 0, 60, 0, 0, 0, 0]
# The one documented time-dependent leaf of the recorded state: the row's
# re-stamped wall-clock collection instant.
ROW_TIMESTAMP_POINTER = "/maps/0/items/%d/3" % FIXTURE_INDEX
ROW_TIMESTAMP = re.compile(r"^/maps/0/items/%d/3$" % FIXTURE_INDEX)
# A second pair of dedicated rows, used by the follow-up replays so the module's
# shared corpus stays readable and the fixture's own row keeps its meaning.
SECOND_INDEX = 21  # Trees at (47,30)
THIRD_INDEX = 22  # Trees at (41,34)
FOURTH_INDEX = 23  # Small forest at (45,31)
FOREST_ITEM_ID = 931

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

    Parsing goes through :func:`collect_envelope.parse_data_field`, which also
    verifies the recorded 64-hex digest against the payload.
    """
    return collect_envelope.parse_data_field(FIXTURE["request"]["form"]["data"])


def recorded_intent() -> Dict[str, Any]:
    """The recorded intent, derived from the recorded command list."""
    envelope = recorded_envelope()
    entry = envelope["commands"][0]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "item_index": entry[2][0],
        "vector": entry[3],
        "command": entry[1],
        "map_id": entry[0],
    }


def committed_ladder() -> Any:
    return BOOT.collect_ladder()  # type: ignore[union-attr]


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
        raise AssertionError("a collection execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def collect_income(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/collect", json=payload)  # type: ignore[union-attr]


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


def row_at(document: Dict[str, Any], index: int = FIXTURE_INDEX) -> List[Any]:
    return list(document["maps"][0]["items"][str(index)])


def normalize_row_timestamp(document: Dict[str, Any]) -> Tuple[Any, List[Tuple[str, Any]]]:
    """Prune the one documented time-dependent leaf and report what it held."""
    return harness.prune_paths(document, [ROW_TIMESTAMP])


def leaf_differences(left: Any, right: Any) -> List[str]:
    """Every JSON-pointer leaf at which two documents differ."""

    def walk(one: Any, other: Any, path: str, out: List[str]) -> None:
        if isinstance(one, dict) and isinstance(other, dict):
            for key in sorted(set(one) | set(other)):
                walk(one.get(key), other.get(key), "%s/%s" % (path, key), out)
        elif (
            isinstance(one, list)
            and isinstance(other, list)
            and len(one) == len(other)
        ):
            for index, (first, second) in enumerate(zip(one, other)):
                walk(first, second, "%s/%d" % (path, index), out)
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
        row = row_at(FIXTURE["before"])
        self.assertEqual(row, [FIXTURE_ITEM_ID, 53, 39, 0, 0, [], {}, 1])
        self.assertEqual(len(FIXTURE["before"]["maps"][0]["items"]), 40)
        # The login step left the corpus untouched.
        login_after = json.loads(
            (FIXTURES / "steps" / LOGIN_STEP / "after.json").read_text(encoding="utf-8")
        )
        login_before = json.loads(
            (FIXTURES / "steps" / LOGIN_STEP / "before.json").read_text(encoding="utf-8")
        )
        self.assertEqual(login_after, login_before)

    def test_recorded_envelope_is_exactly_the_shared_derivation(self) -> None:
        intent = recorded_intent()
        envelope = recorded_envelope()

        # The one time-dependent input: a positive integer, held fixed below.
        self.assertIsInstance(envelope["ts"], int)
        self.assertGreater(envelope["ts"], 0)

        # The income fields and the ladder are the addressed item's own committed
        # content, resolved through the loaded configuration, never client
        # values.
        before_row = row_at(FIXTURE["before"])
        item_id = int(before_row[0])
        self.assertEqual(
            BOOT.item_collect_amount(item_id), FIXTURE_COLLECT_AMOUNT  # type: ignore[union-attr]
        )
        self.assertEqual(
            BOOT.item_collect_type(item_id), FIXTURE_COLLECT_TYPE  # type: ignore[union-attr]
        )
        self.assertEqual(
            BOOT.item_collect_xp(item_id), FIXTURE_COLLECT_XP  # type: ignore[union-attr]
        )
        self.assertEqual(BOOT.item_max_collects(item_id), 0)  # type: ignore[union-attr]
        ladder = committed_ladder()
        self.assertEqual(list(ladder[0]), [5, 60, 240, 480])
        self.assertEqual(list(ladder[1]), [0.25, 1, 2, 3])

        # Every corpus row's item[3] is 0, so the elapsed time is unbounded and
        # the TOP rung is the deterministic one the recorded vector carries.
        self.assertEqual(
            collect_envelope.tier_for(2 ** 31, ladder), FIXTURE_EXPECTED_TIER
        )
        payout = collect_envelope.payout_for(
            amount=FIXTURE_COLLECT_AMOUNT,
            resource_type=FIXTURE_COLLECT_TYPE,
            experience=FIXTURE_COLLECT_XP,
            tier=FIXTURE_EXPECTED_TIER,
            ladder=ladder,
        )
        rebuilt = collect_envelope.build_envelope(
            item_index=intent["item_index"], vector=payout, ts=envelope["ts"]
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        self.assertEqual(sorted(rebuilt), sorted(collect_envelope.ENVELOPE_KEYS))
        self.assertEqual(rebuilt["first_number"], 0)
        self.assertEqual(rebuilt["publishActions"], [])
        self.assertEqual(rebuilt["tries"], 1)
        self.assertEqual(rebuilt["accessToken"], "")
        # The single command, its argument, and its derived vector.
        self.assertEqual(intent["command"], "collect")
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["item_index"], FIXTURE_INDEX)
        self.assertEqual(intent["vector"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(len(envelope["commands"]), 1)
        # The unread and never-produced slots are zero (design D6).
        for slot in collect_envelope.ALWAYS_ZERO_SLOTS:
            self.assertEqual(intent["vector"][slot], 0)

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_collection(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]
        key = str(FIXTURE_INDEX)
        # No key is added or removed.
        self.assertIn(key, after["maps"][0]["items"])
        self.assertEqual(len(after["maps"][0]["items"]), 40)
        self.assertEqual(
            sorted(after["maps"][0]["items"], key=int),
            sorted(before["maps"][0]["items"], key=int),
        )
        before_row = row_at(before)
        after_row = row_at(after)
        self.assertEqual(len(after_row), 8)
        self.assertEqual(after_row[0], FIXTURE_ITEM_ID)  # same item
        self.assertEqual([after_row[1], after_row[2]], list(FIXTURE_ANCHOR))  # same cell
        self.assertEqual(after_row[4], before_row[4])  # orientation
        self.assertEqual(after_row[5], [])  # store
        self.assertEqual(after_row[6], before_row[6])  # attr: a collection adds none
        self.assertEqual(before_row[6], {})
        self.assertEqual(after_row[7], before_row[7])  # player team
        # A fresh wall-clock collection instant, strictly greater than the
        # before-state's committed 0.
        self.assertIsInstance(after_row[3], int)
        self.assertGreater(after_row[3], 0)
        self.assertGreater(after_row[3], before_row[3])
        for key_other in before["maps"][0]["items"]:
            if key_other == key:
                continue
            with self.subTest(key=key_other):
                self.assertEqual(
                    after["maps"][0]["items"][key_other],
                    before["maps"][0]["items"][key_other],
                )
        # A collection stores nothing, buys nothing, and kills nothing.
        self.assertEqual(after["maps"][0]["store"], before["maps"][0]["store"])
        self.assertEqual(after["privateState"], before["privateState"])
        self.assertEqual(after["playerInfo"], before["playerInfo"])
        # The derived payout landed in exactly the wood and experience slots.
        self.assertEqual(
            resources_of(after),
            {"xp": 7, "gold": 2000, "wood": 2060, "oil": 2000, "steel": 2000, "cash": 5, "mana": 0},
        )
        self.assertEqual(
            resources_of(before),
            {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000, "cash": 5, "mana": 0},
        )
        movement = {
            name: resources_of(after)[name] - resources_of(before)[name]
            for name in resources_of(after)
        }
        self.assertEqual(movement["xp"], 3)
        self.assertEqual(movement["wood"], 60)
        for name in ("gold", "oil", "steel", "cash", "mana"):
            with self.subTest(resource=name):
                self.assertEqual(movement[name], 0)

    def test_the_recorded_state_carries_exactly_three_differing_leaves(self) -> None:
        """The normalization this suite applies is the *whole* clock surface.

        Exactly three leaves differ between the recorded before- and
        after-states: the row's re-stamped collection instant (the only clock
        reading) and the two resource leaves the derived payout pays.  Nothing
        else moved — in particular no attribute-bag entry, because a collection
        writes none.
        """
        differences = leaf_differences(FIXTURE["before"], FIXTURE["after"])
        self.assertEqual(
            sorted(differences),
            sorted(
                [
                    "/maps/0/items/%d/3" % FIXTURE_INDEX,
                    "/maps/0/xp",
                    "/maps/0/wood",
                ]
            ),
        )
        self.assertEqual(
            [path for path in differences if path == ROW_TIMESTAMP_POINTER],
            [ROW_TIMESTAMP_POINTER],
        )
        # The map-level timestamp is not rewritten either (apply_resources'
        # write is commented out in legacy, engine.py:269).
        self.assertEqual(
            FIXTURE["after"]["maps"][0]["timestamp"],
            FIXTURE["before"]["maps"][0]["timestamp"],
        )

    def test_the_manifest_records_both_probes(self) -> None:
        """Task 1.3: both executed probes are recorded with their evidence."""
        probes = FIXTURE["manifest"]["probes"]
        self.assertEqual(len(probes), 2)
        first, second = probes
        self.assertEqual(first["probe"], 1)
        self.assertEqual(first["command"], "collect(2)")
        self.assertIn("ONLY the row's timestamp", first["established"])
        self.assertIn("verbatim", first["established"])
        self.assertIn("clamp did not bite", first["clamp_not_exercised"])
        self.assertEqual(second["probe"], 2)
        self.assertIn("activate(11, 3600)", second["command"])
        self.assertIn("cp", second["row_after"])
        self.assertIn("SURVIVED", second["established"])
        self.assertIn("construction_in_progress", second["consequence"])
        self.assertIn("never observed", second["not_observed_from_client"])

    def test_the_manifest_records_the_derived_payout_and_the_rung(self) -> None:
        intent_block = FIXTURE["manifest"]["intent"]
        self.assertEqual(intent_block["item_index"], FIXTURE_INDEX)
        self.assertEqual(intent_block["item_id"], FIXTURE_ITEM_ID)
        self.assertEqual(intent_block["cell"], list(FIXTURE_ANCHOR))
        derived = intent_block["derived"]
        self.assertEqual(derived["command"], "collect")
        self.assertEqual(derived["args"], [FIXTURE_INDEX])
        self.assertEqual(derived["resources_changed"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(derived["tier"], FIXTURE_EXPECTED_TIER)
        self.assertEqual(derived["collect"], FIXTURE_COLLECT_AMOUNT)
        self.assertEqual(derived["collect_type"], FIXTURE_COLLECT_TYPE)
        self.assertEqual(derived["collect_xp"], FIXTURE_COLLECT_XP)
        self.assertEqual(derived["max_collects"], 0)
        # The whole committed ladder, with the Tree's payout at every rung.
        ladder = derived["ladder"]
        self.assertEqual(ladder["minutes"], [5, 60, 240, 480])
        self.assertEqual(ladder["multipliers"], [0.25, 1, 2, 3])
        self.assertEqual([rung["index"] for rung in ladder["rungs"]], [0, 1, 2, 3])
        self.assertEqual(
            [rung["tree_payout"]["amount"] for rung in ladder["rungs"]],
            [5, 20, 40, 60],
        )
        self.assertEqual(
            [rung["tree_payout"]["experience"] for rung in ladder["rungs"]],
            [0, 1, 2, 3],
        )
        # The six decisions, each named and each marked derived-provisional.
        decisions = derived["decisions"]
        for name in (
            "D1_amount_formula",
            "D2_experience_scaling",
            "D3_sub_first_rung",
            "D4_cap_semantics",
            "D5_shared_field",
            "D6_resource_mapping",
        ):
            with self.subTest(decision=name):
                self.assertIn(name, decisions)
                self.assertTrue(decisions[name].strip())
        for name in (
            "D1_amount_formula",
            "D2_experience_scaling",
            "D3_sub_first_rung",
            "D4_cap_semantics",
            "D6_resource_mapping",
        ):
            with self.subTest(decision=name):
                self.assertIn("DERIVED-PROVISIONAL", decisions[name])
        self.assertIn("ESTABLISHED RISK, DERIVED RULE", decisions["D5_shared_field"])
        self.assertIn("Rejected alternative", decisions["D1_amount_formula"])
        self.assertIn("Rejected alternative", decisions["D2_experience_scaling"])
        self.assertIn("Rejected alternatives", decisions["D3_sub_first_rung"])
        self.assertIn("EXACTLY the derived delta", decisions["D8_two_part_proof"])
        self.assertIn("never any specific amount", derived["status"])
        # The intent-only and the proof decisions.
        self.assertIn("only the save id and", decisions["D7_intent_only"])
        self.assertIn("EXACTLY the derived delta", decisions["D8_two_part_proof"])

    def test_the_manifest_records_the_claim_limits(self) -> None:
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertFalse(transaction["clamp_exercised"])
        self.assertIn("max(current + delta, 0)", transaction["clamp_note"])
        self.assertFalse(transaction["cap_semantics_implemented"])
        self.assertIn("refused with capped_collection", transaction["cap_note"])
        self.assertFalse(transaction["friend_assist_in_scope"])
        self.assertIn("construction_in_progress", transaction["construction_overlap"])
        self.assertTrue(transaction["other_rows_unchanged"])
        self.assertTrue(transaction["private_state_unchanged"])
        self.assertTrue(transaction["player_info_unchanged"])
        self.assertEqual(transaction["row_before"], [FIXTURE_ITEM_ID, 53, 39, 0, 0, [], {}, 1])
        self.assertEqual(transaction["attr_before"], {})
        self.assertEqual(transaction["attr_after"], {})
        self.assertEqual(transaction["placement_count_before"], 40)
        self.assertEqual(transaction["placement_count_after"], 40)
        self.assertEqual(
            transaction["resource_delta"],
            {
                "cash": 0,
                "gold": 0,
                "mana": 0,
                "oil": 0,
                "steel": 0,
                "wood": 60,
                "xp": 3,
            },
        )
        self.assertEqual(transaction["response_body"], '{"result": "success"}')
        # The containment and cleanup records.
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertTrue(containment["working_tree_saves_unchanged"])
        self.assertTrue(containment["loopback_only"])
        self.assertTrue(containment["no_flash_browser_external_network"])
        self.assertTrue(containment["protected_fixtures"]["identical"])
        self.assertEqual(
            len(containment["protected_fixtures"]["paths"]), 8
        )
        self.assertEqual(
            containment["pre_combined_sha256"], containment["post_combined_sha256"]
        )
        self.assertTrue(FIXTURE["manifest"]["cleanup"]["server_stopped_within_run"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["startup_preserved_seed"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["login_preserved_seed"])

    def test_the_manifest_records_the_time_dependent_leaves(self) -> None:
        record = FIXTURE["manifest"]["time_dependent_fields"]
        leaves = " ".join(record["leaves"])
        self.assertIn("/maps/0/items/2/3", leaves)
        self.assertIn("/transaction/row_after/3", leaves)
        self.assertIn("/transaction/steps/1/save_after_sha256", leaves)
        self.assertIn("exactly these 11 paths", record["rule"])
        self.assertIn("STRICTLY GREATER", record["documented_normalization"])
        self.assertIn("top committed rung applies deterministically", record["stable_by_derivation"])


class EndpointReplayTests(unittest.TestCase):
    """The executing parity check: the recorded intent replayed offline.

    The module shares one disposable corpus, so the mutating tests are ordered
    by name: ``test_a_...`` inspects the corpus at the fixture's before-state
    first, ``test_b_...`` replays the recorded transaction (its assertions
    require that before-state), and the follow-ups build on that result with
    their own dedicated rows.
    """

    def test_a_the_recorded_index_is_addressable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rule agrees with the recorded row."""
        intent = recorded_intent()
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        self.assertTrue(BOOT.has_map_item(PID, intent["item_index"]))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, intent["item_index"])  # type: ignore[union-attr]
        self.assertEqual(row, [FIXTURE_ITEM_ID, 53, 39, 0, 0, [], {}, 1])
        self.assertEqual(row, row_at(FIXTURE["before"]))
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]
        # The income content resolves from the committed configuration.
        self.assertEqual(
            BOOT.item_collect_amount(int(row[0])), FIXTURE_COLLECT_AMOUNT  # type: ignore[union-attr]
        )
        self.assertEqual(
            BOOT.item_collect_type(int(row[0])), FIXTURE_COLLECT_TYPE  # type: ignore[union-attr]
        )
        ladder = committed_ladder()
        self.assertEqual(
            collect_envelope.tier_for(2 ** 31, ladder), FIXTURE_EXPECTED_TIER
        )

    def test_b_endpoint_replays_the_recorded_transaction(self) -> None:
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        # The replay starts exactly at the fixture's before-state.
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        captured_before_row = row_at(FIXTURE["before"])
        captured_after_row = row_at(FIXTURE["after"])

        response = collect_income(
            {"user_id": intent["user_id"], "item_index": intent["item_index"]}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        # 1. Response equals the captured legacy response for the field the
        #    legacy response had (the rest of the envelope is the documented
        #    superset: previous + row + payout + tier + reference_time +
        #    resources, design D8).
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
                    "previous",
                    "row",
                    "payout",
                    "tier",
                    "reference_time",
                    "resources",
                ]
            ),
        )

        # 2. ``previous`` equals the captured *before*-state row at that legacy
        #    key, field for field (no normalization: it carries no clock value
        #    beyond the corpus's own 0).
        self.assertEqual(payload["previous"], captured_before_row)
        self.assertEqual(len(payload["previous"]), 8)

        # 3. The post-execution row: the re-stamped collection instant compared
        #    structurally, never by value.
        row = payload["row"]
        self.assertEqual(len(row), 8)
        self.assertIsInstance(row[3], int)
        self.assertNotIsInstance(row[3], bool)
        self.assertGreater(row[3], 0)
        self.assertGreater(row[3], captured_before_row[3])
        # A collection writes only the instant: the attribute bag is untouched,
        # so the row is still collectible and still buildable.
        self.assertEqual(row[6], captured_before_row[6])

        # 4. The derived payout equals the recorded request's vector exactly, and
        #    the rung is the top committed one the corpus deterministically
        #    reaches.
        self.assertEqual(payload["payout"], intent["vector"])
        self.assertEqual(payload["payout"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(payload["tier"], FIXTURE_EXPECTED_TIER)
        # The reference instant is the service's own clock, and the elapsed time
        # it implies reaches the top rung from the row's committed 0.
        self.assertIsInstance(payload["reference_time"], int)
        self.assertGreater(payload["reference_time"], 0)
        self.assertGreaterEqual(
            payload["reference_time"] - captured_before_row[3],
            collect_envelope.threshold_seconds_for(
                FIXTURE_EXPECTED_TIER, committed_ladder()
            ),
        )

        # 5. The final row equals the captured *after*-state row, field for
        #    field, with the row's re-stamped wall-clock collection instant
        #    documented and normalized.  Every other field — item, cell,
        #    orientation, store, attr, player — must match exactly.
        replay = list(row)
        self.assertEqual(len(replay), 8)
        replay_stamp = replay.pop(3)
        captured = list(captured_after_row)
        captured_stamp = captured.pop(3)
        self.assertEqual(replay, captured)
        # The normalization itself: both are positive wall-clock stamps, and the
        # replay's is not earlier than the before-state's.
        self.assertGreater(replay_stamp, 0)
        self.assertGreater(replay_stamp, captured_before_row[3])
        self.assertGreater(captured_stamp, 0)
        # The attribute bag is not merely equal after normalization: it is
        # empty in both, which is the structural overlap the D5 refusal exists
        # to protect.  Index 5 is `item[6]` once `item[3]` is popped.
        self.assertEqual(captured[5], {})

        # 6. Resources equal the values read from the captured after-state, and
        #    the movement is exactly the recorded derived vector.
        self.assertEqual(payload["resources"], resources_of(FIXTURE["after"]))
        self.assertEqual(payload["resources"]["xp"], 7)
        self.assertEqual(payload["resources"]["wood"], 2060)
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
                "wood": 60,
                "xp": 3,
            },
        )
        for name, slot in (
            ("xp", 1),
            ("gold", 2),
            ("wood", 3),
            ("oil", 4),
            ("steel", 5),
            ("cash", 6),
            ("mana", 7),
        ):
            with self.subTest(slot=slot):
                self.assertEqual(movement[name], intent["vector"][slot])

        # 7. The endpoint proved the collection from the persisted save, not
        #    from its own copy of the row.
        raw_corpus_after = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertIn(str(intent["item_index"]), raw_corpus_after["maps"][0]["items"])
        self.assertEqual(
            raw_corpus_after["maps"][0]["items"][str(intent["item_index"])],
            payload["row"],
        )

        # 8. The corpus save after execution equals the captured after-state
        #    for every leaf, under exactly the one documented normalization.
        pruned_replay, collected_replay = normalize_row_timestamp(raw_corpus_after)
        pruned_capture, collected_capture = normalize_row_timestamp(FIXTURE["after"])
        # The normalization removed a real leaf on both sides.
        self.assertEqual(
            [path for path, _value in collected_replay], [ROW_TIMESTAMP_POINTER]
        )
        self.assertEqual(
            [path for path, _value in collected_capture], [ROW_TIMESTAMP_POINTER]
        )
        # Without the normalization the two states differ in exactly that one
        # leaf — asserted, so the normalization can never silently widen.
        unnormalized = harness.diff_documents(FIXTURE["after"], raw_corpus_after)
        self.assertEqual(
            [entry.split(":", 1)[0] for entry in unnormalized],
            [ROW_TIMESTAMP_POINTER],
        )
        self.assertEqual(harness.diff_documents(pruned_capture, pruned_replay), [])

        # 9. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_c_a_second_row_replays_the_same_derivation(self) -> None:
        """The endpoint's answer is a function of the addressed row, not of the
        fixture: a different decoration produces the same derivation from its
        own committed content and its own instant."""
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]

        response = collect_income(
            {"user_id": intent["user_id"], "item_index": SECOND_INDEX}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["previous"],
            after_first["maps"][0]["items"][str(SECOND_INDEX)],
        )
        self.assertEqual(payload["payout"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(payload["tier"], FIXTURE_EXPECTED_TIER)
        self.assertEqual(payload["row"][6], {})
        self.assertGreater(payload["row"][3], 0)
        after_second = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        for key in after_first["maps"][0]["items"]:
            if key in (str(intent["item_index"]), str(SECOND_INDEX)):
                continue
            with self.subTest(key=key):
                self.assertEqual(
                    after_second["maps"][0]["items"][key],
                    after_first["maps"][0]["items"][key],
                )
        self.assertEqual(
            len(after_second["maps"][0]["items"]), len(after_first["maps"][0]["items"])
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_d_the_construction_state_refusal_keeps_the_replayed_row(self) -> None:
        """Design D5 replayed against the live corpus: a row the delivered
        construction line has just started is refused, and the build's start
        instant and countdown survive untouched — the corruption the executed
        probe demonstrated."""
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        item_id = int(after_first["maps"][0]["items"][str(SECOND_INDEX)][0])
        build_time = BOOT.item_build_time(item_id)  # type: ignore[union-attr]
        self.assertIsNotNone(build_time)
        # Start a real construction through the unchanged legacy dispatcher.
        BOOT.execute_commands(  # type: ignore[union-attr]
            PID,
            {
                "first_number": 0,
                "publishActions": [],
                "ts": 1700000000,
                "tries": 1,
                "accessToken": "",
                "commands": [[0, "activate", [SECOND_INDEX, build_time], [0] * 8]],
            },
        )
        started = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        build_start = started["maps"][0]["items"][str(SECOND_INDEX)][3]
        self.assertEqual(
            started["maps"][0]["items"][str(SECOND_INDEX)][6], {"cp": build_time}
        )

        response = collect_income(
            {"user_id": intent["user_id"], "item_index": SECOND_INDEX}
        )

        self.assertEqual(response.status_code, 409)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "construction_in_progress")
        # The refused row is byte-identical: the start instant and the
        # countdown both survive.
        after_refusal = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(
            after_refusal["maps"][0]["items"][str(SECOND_INDEX)],
            started["maps"][0]["items"][str(SECOND_INDEX)],
        )
        self.assertEqual(after_refusal["maps"][0]["items"][str(SECOND_INDEX)][3], build_start)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_e_the_replayed_transaction_matches_the_committed_fixture_shape(self) -> None:
        """The rows the fixture records are the rows the endpoint produces, and
        the response shape is the documented superset."""
        intent = recorded_intent()
        after_first = copy.deepcopy(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        response = collect_income(
            {"user_id": intent["user_id"], "item_index": THIRD_INDEX}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["previous"], after_first["maps"][0]["items"][str(THIRD_INDEX)])
        # Identical response shape to the fixture's own transaction, only the row
        # index differs.
        self.assertEqual(
            sorted(payload),
            sorted(
                [
                    "protocol",
                    "ok",
                    "game_version",
                    "server_time",
                    "result",
                    "previous",
                    "row",
                    "payout",
                    "tier",
                    "reference_time",
                    "resources",
                ]
            ),
        )
        self.assertEqual(payload["payout"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(payload["tier"], FIXTURE_EXPECTED_TIER)
        self.assertEqual(list(payload["row"])[0], 930)  # the Trees
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class CollectParitySurfaceTests(unittest.TestCase):
    """The replay ran offline: no server, no socket."""

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))

    def test_fixture_directory_is_the_committed_one(self) -> None:
        self.assertTrue((FIXTURES / "capture-manifest.json").is_file())
        self.assertTrue((FIXTURES / "README.md").is_file())
        self.assertTrue((FIXTURES / "steps" / STEP / "request.json").is_file())
        self.assertTrue((FIXTURES / "steps" / LOGIN_STEP / "after.json").is_file())

    def test_the_fixture_readme_states_the_provenance_split_and_the_claims(self) -> None:
        """Task 1.3 plus the recorded claim limits."""
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn('{"result":"success"}', readme)
        self.assertIn("Established from committed legacy source", readme)
        self.assertIn("Derived and never observed from the Flash client", readme)
        # Both probes.
        self.assertIn("Probe 1", readme)
        self.assertIn("Probe 2", readme)
        self.assertIn("construction_in_progress", readme)
        # The six decisions.
        for name in (
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "D6",
        ):
            with self.subTest(decision=name):
                self.assertIn(name, readme)
        self.assertIn("derived-provisional", readme)
        # The derived payout and rung.
        self.assertIn("[0,3,0,60,0,0,0,0]", readme)  # the recorded request
        self.assertIn("[0, 3, 0, 60, 0,", readme)  # the derived payout
        self.assertIn("tier 3", readme)
        # The documented time-dependent leaf and the claim limits.
        self.assertIn("/maps/0/items/2/3", readme)
        self.assertIn("clamp is never exercised", readme)
        self.assertIn("decorations", readme)
        self.assertIn("**No cap semantics are implemented.**", readme)
        self.assertIn("No Flash, Ruffle, ActionScript, or browser", readme)
        self.assertIn("no external network", readme)
        self.assertIn("no pixel-parity oracle", readme)

    def test_the_fixture_readme_records_the_executed_outcome(self) -> None:
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        # The row before and after, the movement, and the invariants.
        self.assertIn("[905, 53, 39, 0, 0, [], {}, 1]", readme)
        self.assertIn("xp 4 ", readme)
        self.assertIn("7", readme)
        self.assertIn("wood 2000 ", readme)
        self.assertIn("2060", readme)
        self.assertIn("stays `40`", readme)
        self.assertIn("`item[3]`", readme)

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "a collection execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()
