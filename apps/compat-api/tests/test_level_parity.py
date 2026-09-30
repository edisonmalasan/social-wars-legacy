#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/level_up`` vs the executed-legacy
level fixture (OpenSpec task 2.4).

No server and no network: the endpoint runs through Flask's in-process
test client under the ``offline`` guard (which fails the run if any socket
tries to connect), and ``test_no_server_is_running`` asserts that neither the
legacy port (5055) nor the Compatibility API port (5056) is listening.

What is replayed: the committed transaction under
``tests/fixtures/godot-building-xp/`` — one real ``level_up`` command carrying
the **service-derived** level ``1`` and the **neutral** vector
``[0, 0, 0, 0, 0, 0, 0, 0]``, executed by the legacy server in a disposable
copy against the fresh-player corpus, whose stored experience is ``4`` and whose
recorded level is ``1``.  The endpoint derives the very same envelope from the
very same module, so the replay compares:

* the response ``result`` against the captured legacy response body;
* the response ``level_before`` / ``level_after`` against the recorded level in
  the captured states, and against the level the committed curve derives for the
  recorded experience;
* the response ``derived_level`` against the same derivation;
* the response ``curve`` against the committed curve the derivation read —
  entries, index base, derivation status, rejected alternative, the entry's own
  name and threshold, and the next level's;
* the response ``resources`` against the values read from the captured
  after-state (all seven slots are stable, and the captured movement is the
  derived neutral vector — which is nothing);
* the corpus save after execution against the captured after-state, leaf for
  leaf, **with no normalization whatsoever** — this fixture's recorded state
  carries no time-dependent leaf, so the whole after-state must match exactly;
* the shared derivation against the recorded request envelope, exactly (the
  recorded ``ts`` is passed back into the derivation).

**The committed corpus lands in the endpoint's own ``level_already_current``
refusal**, and the parity suite asserts exactly that: with ``xp 4`` the curve
derives level 1 and the save already records 1, so there is nothing to do and
the corpus must be left byte-identical.  That is the recorded condition, not a
gap in the replay — the executed transaction itself wrote an identical value,
and the level **movement** the success path promises is established by the
fixture's own probe 1.

**No clock normalization exists in this suite**, and that is the point: a
``level_up`` writes the integer the client sent into the map and the derived
vector is neutral, so the recorded state carries no wall-clock reading at all —
unlike the collect fixture, whose addressed row carried the collection instant.
A leaf-level diff of the captured before- and after-states proves it: **zero**
leaves differ, because the derived level already equals the recorded one.

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
import level_envelope

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-xp"
STEP = "command_level_up"
LOGIN_STEP = "login_post"
FIXTURE_LEVEL = 1
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_XP = 4
FIXTURE_RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")

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

    Parsing goes through :func:`level_envelope.parse_data_field`, which also
    verifies the recorded 64-hex digest against the payload.
    """
    return level_envelope.parse_data_field(FIXTURE["request"]["form"]["data"])


def recorded_intent() -> Dict[str, Any]:
    """The recorded intent, derived from the recorded command list."""
    envelope = recorded_envelope()
    entry = envelope["commands"][0]
    return {
        "user_id": FIXTURE["request"]["form"]["USERID"],
        "level": entry[2][0],
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
        raise AssertionError("a level-up execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def level_up_town(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/level_up", json=payload)  # type: ignore[union-attr]


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
    """Every JSON-pointer leaf at which two documents differ."""

    def walk(one: Any, other: Any, path: str, out: List[str]) -> None:
        if isinstance(one, dict) and isinstance(other, dict):
            for key in sorted(set(one) | set(other)):
                child = "%s/%s" % (path, key)
                if key not in one or key not in other:
                    out.append(child)
                    continue
                walk(one[key], other[key], child, out)
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
        self.assertEqual(FIXTURE["before"]["maps"][0]["level"], FIXTURE_LEVEL)  # type: ignore[index]
        self.assertEqual(FIXTURE["before"]["maps"][0]["xp"], FIXTURE_XP)  # type: ignore[index]
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

        # The committed curve, read through the loaded configuration, and the
        # level derived from the recorded experience by the single named
        # conversion.
        rows = [
            BOOT.level_entry(position)  # type: ignore[union-attr]
            for position in range(BOOT.level_entry_count())  # type: ignore[union-attr]
        ]
        thresholds = level_envelope.thresholds_from_entries(rows)
        derived = level_envelope.derived_level_for(FIXTURE_XP, thresholds)
        self.assertEqual(derived, FIXTURE_LEVEL)
        self.assertEqual(
            level_envelope.entry_index_for_level(FIXTURE_LEVEL), 0
        )
        rebuilt = level_envelope.build_envelope(
            level=derived, vector=level_envelope.neutral_vector(), ts=envelope["ts"]
        )
        # Byte-for-byte: same inputs, same recorded ts, same envelope.
        self.assertEqual(rebuilt, envelope)
        self.assertEqual(sorted(rebuilt), sorted(level_envelope.ENVELOPE_KEYS))
        self.assertEqual(rebuilt["first_number"], 0)
        self.assertEqual(rebuilt["publishActions"], [])
        self.assertEqual(rebuilt["tries"], 1)
        self.assertEqual(rebuilt["accessToken"], "")
        # The single command, its derived argument, and its neutral vector.
        self.assertEqual(intent["command"], "level_up")
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["level"], FIXTURE_LEVEL)
        self.assertEqual(intent["vector"], FIXTURE_EXPECTED_VECTOR)
        self.assertEqual(len(envelope["commands"]), 1)
        self.assertEqual(len(envelope["commands"][0][2]), 1)
        # Every slot is zero: a level-up moves no resource.
        for slot in level_envelope.ALWAYS_ZERO_SLOTS:
            with self.subTest(slot=slot):
                self.assertEqual(intent["vector"][slot], 0)

    def test_recorded_response_is_the_legacy_result(self) -> None:
        self.assertEqual(json.loads(FIXTURE["body"]), {"result": "success"})
        self.assertEqual(FIXTURE["meta"]["status"], 200)

    def test_recorded_after_state_shows_the_derived_level(self) -> None:
        before = FIXTURE["before"]
        after = FIXTURE["after"]

        # The level equals the derived value — the promised post-state.
        self.assertEqual(after["maps"][0]["level"], FIXTURE_LEVEL)  # type: ignore[index]
        # …and the recorded fact that it did NOT move, because the corpus already
        # recorded the level the curve derives for its 4 experience.  Stated,
        # not papered over.
        self.assertEqual(before["maps"][0]["level"], FIXTURE_LEVEL)  # type: ignore[index]
        self.assertFalse(
            FIXTURE["manifest"]["transaction"]["level_moved"]
        )
        self.assertIn(
            "level_already_current", FIXTURE["manifest"]["transaction"]["level_moved_note"]
        )

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
        self.assertEqual(after["maps"][0]["store"], before["maps"][0]["store"])  # type: ignore[index]
        self.assertEqual(after["maps"][0]["increasedPopulation"], before["maps"][0]["increasedPopulation"])  # type: ignore[index]
        self.assertNotIn("map_sizes", after["maps"][0])  # type: ignore[index]
        self.assertNotIn("map_sizes", before["maps"][0])  # type: ignore[index]
        # The whole key set, so no un-named field could have moved.
        self.assertEqual(
            sorted(after["maps"][0]), sorted(before["maps"][0])  # type: ignore[index]
        )
        for field in sorted(set(before["maps"][0]) | set(after["maps"][0])):  # type: ignore[index]
            with self.subTest(field=field):
                self.assertEqual(
                    after["maps"][0].get(field),  # type: ignore[index]
                    before["maps"][0].get(field),  # type: ignore[index]
                )
        # A level-up stores nothing, buys nothing, and kills nothing.
        self.assertEqual(after["privateState"], before["privateState"])  # type: ignore[index]
        self.assertEqual(after["playerInfo"], before["playerInfo"])  # type: ignore[index]
        # Every stored resource is unchanged, because the derived vector is the
        # neutral one.
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

    def test_the_recorded_state_carries_no_differing_leaf_at_all(self) -> None:
        """The absence of any clock reading, proved — and the recorded reason the
        level did not move.

        **Zero** leaves differ between the recorded before- and after-states: the
        derived level already equalled the recorded one, so the branch wrote an
        identical value and nothing else changed either.  The collect fixture's
        after-state carried three differing leaves; this one carries none, and
        the state is therefore byte-stable across reruns with no normalization
        at all.
        """
        differences = leaf_differences(FIXTURE["before"], FIXTURE["after"])
        self.assertEqual(differences, [])
        self.assertEqual(
            FIXTURE["manifest"]["transaction"]["recorded_leaf_differences"], []
        )
        # The map-level timestamp is not rewritten either (apply_resources'
        # write is commented out in legacy, engine.py:269).
        self.assertEqual(
            FIXTURE["after"]["maps"][0]["timestamp"],  # type: ignore[index]
            FIXTURE["before"]["maps"][0]["timestamp"],  # type: ignore[index]
        )
        # And the two recorded save documents really are byte-identical.
        self.assertEqual(
            (FIXTURES / "steps" / STEP / "after.json").read_bytes(),
            (FIXTURES / "steps" / STEP / "before.json").read_bytes(),
        )

    def test_the_manifest_records_the_executed_probe(self) -> None:
        """Probe 1 is what makes the endpoint's "nothing moved" proof real
        rather than a tautology: the branch moves the level, and a client-sent
        vector moves a balance."""
        probes = FIXTURE["manifest"]["probes"]
        self.assertEqual(len(probes), 1)
        probe = probes[0]
        self.assertEqual(probe["probe"], 1)
        self.assertTrue(probe["executed_in_this_capture"])
        self.assertIn("level_up([2])", probe["commands"][0])
        self.assertEqual(probe["level_before"], 1)
        self.assertEqual(probe["level_after"], 2)
        self.assertEqual(probe["xp_before"], 4)
        self.assertEqual(probe["xp_after"], 504)
        self.assertEqual(probe["changed_top_level_map_keys"], ["level", "xp"])
        self.assertEqual(probe["leaf_differences"], ["/maps/0/level", "/maps/0/xp"])
        self.assertIn("command.py:81-85", probe["established"])
        self.assertIn("resource-minting exploit", probe["why_it_matters"])

    def test_the_manifest_records_the_curve_and_the_provenance(self) -> None:
        intent_block = FIXTURE["manifest"]["intent"]
        self.assertEqual(intent_block["level_sent"], FIXTURE_LEVEL)
        self.assertIn("one-based", intent_block["target_rule"])
        self.assertIn("level_already_current", intent_block["target_rule"])
        self.assertIn("probe 1", intent_block["target_rule"])

        index_rule = intent_block["index_base_rule"]
        self.assertIn("ONE-BASED", index_rule)
        self.assertIn("levels[n - 1]", index_rule)
        self.assertIn("DERIVED-PROVISIONAL", index_rule)
        self.assertIn("ZERO-BASED", index_rule)
        # The rejected alternative and the corpus contradiction that rejects it.
        self.assertIn("CONTRADICTS", index_rule)
        self.assertIn("implies level 0 while the save records level 1", index_rule)
        self.assertIn("entry_index_for_level", index_rule)

        derived = intent_block["derived"]
        self.assertEqual(derived["command"], "level_up")
        self.assertEqual(derived["args"], [FIXTURE_LEVEL])
        self.assertEqual(derived["resources_changed"], FIXTURE_EXPECTED_VECTOR)
        self.assertTrue(derived["vector_is_neutral"])
        self.assertEqual(
            derived["resource_vector"],
            "unknown, xp, gold, wood, oil, steel, cash, mana",
        )
        self.assertEqual(
            derived["envelope_keys"],
            ["accessToken", "commands", "first_number", "publishActions", "tries", "ts"],
        )
        self.assertIn("entry_index_for_level", derived["conversion"])

        curve = derived["curve"]
        self.assertEqual(curve["key"], "levels")
        self.assertEqual(curve["entries"], 100)
        self.assertFalse(curve["stable_id"])
        self.assertEqual(curve["id_space"], "the stored level 1..100")
        self.assertEqual(curve["index_base"], "one-based")
        self.assertEqual(curve["derivation_status"], "derived-provisional")
        self.assertEqual(curve["rejected_alternative"], "zero-based")
        self.assertEqual(
            sorted(curve["fields"]),
            ["exp_required", "name", "reward_amount", "reward_type"],
        )
        self.assertEqual(curve["first_thresholds"], [0, 40, 60, 100, 200, 350, 550, 800])
        self.assertEqual(curve["final_threshold"], 2016089205)
        self.assertTrue(curve["strictly_increasing"])
        self.assertEqual(curve["duplicate_thresholds"], 0)
        self.assertEqual(curve["distinct_names"], 44)
        self.assertTrue(curve["name_is_a_label"])
        self.assertEqual(curve["reward_types"], ["c", "g", "s", "w"])
        self.assertEqual(curve["reward_amounts"], [1, 50, 250])
        # The first and second entries are the one-based reading's own facts.
        # The snapshot is a tuple of pairs in the module and a list of lists once
        # the manifest's JSON round trip has been through it.
        self.assertEqual(
            [list(pair) for pair in curve["first_entry"]],
            [["name", "Slave"], ["exp_required", 0], ["reward_type", "s"],
             ["reward_amount", 50]],
        )
        self.assertEqual(
            [list(pair) for pair in curve["second_entry"]],
            [["name", "Servant"], ["exp_required", 40], ["reward_type", "w"],
             ["reward_amount", 250]],
        )
        self.assertEqual(list(curve["final_entry"][1]), ["exp_required", 2016089205])
        self.assertFalse(curve["read_by_the_legacy_server"])

    def test_the_manifest_records_every_decision_with_its_provenance(self) -> None:
        decisions = FIXTURE["manifest"]["intent"]["derived"]["decisions"]
        for name in (
            "D1_index_base",
            "D2_recorded_level_unverified",
            "D3_derived_target",
            "D4_fail_closed_refusals",
            "D5_two_part_proof",
            "D6_unaffordable_next_level",
            "D7_no_tuning_no_rewards",
        ):
            with self.subTest(decision=name):
                self.assertIn(name, decisions)
                self.assertTrue(decisions[name].strip())
        d1 = decisions["D1_index_base"]
        self.assertIn("ONE-BASED", d1)
        self.assertIn("DERIVED-PROVISIONAL", d1)
        self.assertIn("REJECTED alternative", d1)
        self.assertIn("ZERO-BASED", d1)
        self.assertIn("xp 4 the zero-based curve implies level 0", d1)
        self.assertIn("shift EVERY level by one", d1)
        self.assertIn("entry_index_for_level", d1)
        self.assertIn("NOT evidence", decisions["D2_recorded_level_unverified"])
        self.assertIn("level_already_current", decisions["D2_recorded_level_unverified"])
        self.assertIn("IGNORED", decisions["D3_derived_target"])
        self.assertIn("level 99", decisions["D3_derived_target"])
        self.assertIn("BEFORE the dispatcher runs", decisions["D4_fail_closed_refusals"])
        self.assertIn("EVERY stored resource is UNCHANGED", decisions["D5_two_part_proof"])
        self.assertIn("smuggling", decisions["D5_two_part_proof"])
        self.assertIn("information only", decisions["D6_unaffordable_next_level"])
        self.assertIn("VERBATIM", decisions["D7_no_tuning_no_rewards"])
        self.assertIn("REFUSED rather than invented", decisions["D7_no_tuning_no_rewards"])

        intent_block = FIXTURE["manifest"]["intent"]
        self.assertIn("NO level reward is paid", intent_block["reward_rule"])
        self.assertIn("add_xp_unit", intent_block["unit_xp_rule"])
        self.assertIn("0 of its 40 placed", intent_block["unit_xp_rule"])
        status = intent_block["derived"]["status"]
        self.assertIn("command.py:81-85", status)
        self.assertIn("zero references", status)
        self.assertIn("NEVER one observed a Flash client send", status)

    def test_the_manifest_records_the_claim_limits(self) -> None:
        transaction = FIXTURE["manifest"]["transaction"]
        self.assertEqual(transaction["stored_xp_before"], FIXTURE_XP)
        self.assertEqual(transaction["level_before"], FIXTURE_LEVEL)
        self.assertEqual(transaction["level_after"], FIXTURE_LEVEL)
        self.assertEqual(transaction["derived_level"], FIXTURE_LEVEL)
        self.assertEqual(transaction["recorded_leaf_differences"], [])
        self.assertEqual(transaction["placement_count_before"], 40)
        self.assertEqual(transaction["placement_count_after"], 40)
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
        # The clamp is never exercised, and why that is a claim limit rather
        # than a proof of neutrality on its own.
        self.assertFalse(transaction["clamp_exercised"])
        self.assertIn("max(current + delta, 0)", transaction["clamp_note"])
        self.assertIn("probe 1", transaction["clamp_note"])
        # No reward, stated twice.
        self.assertFalse(transaction["reward_paid"])
        self.assertIn("reward_type", transaction["reward_note"])
        self.assertIn("neutral vector", transaction["reward_note"])
        # What the branch writes.
        self.assertEqual(len(transaction["level_up_writes"]), 3)
        self.assertIn("command.py:40", transaction["level_up_writes"][0])
        self.assertIn("engine.py:251-271", transaction["level_up_writes"][0])
        self.assertIn("command.py:81-85", transaction["level_up_writes"][1])
        self.assertIn("zero references", transaction["level_up_writes"][2])
        # The containment and cleanup records.
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertTrue(containment["working_tree_saves_unchanged"])
        self.assertTrue(containment["loopback_only"])
        self.assertTrue(containment["no_flash_browser_external_network"])
        self.assertTrue(containment["protected_fixtures"]["identical"])
        self.assertEqual(len(containment["protected_fixtures"]["paths"]), 10)
        self.assertEqual(
            containment["pre_combined_sha256"], containment["post_combined_sha256"]
        )
        self.assertTrue(FIXTURE["manifest"]["cleanup"]["server_stopped_within_run"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["startup_preserved_seed"])
        self.assertTrue(FIXTURE["manifest"]["corpus"]["login_preserved_seed"])

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
    first, ``test_b_...`` replays the recorded intent (whose outcome is the
    refusal the recorded state corresponds to), and the follow-ups build on that
    with their own states.
    """

    def test_a_the_recorded_state_is_resolvable_in_the_replay_corpus(self) -> None:
        """The endpoint's own resolution rules agree with the recorded intent:
        the curve resolves, the recorded level is readable, and the derived level
        equals the recorded one."""
        intent = recorded_intent()
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        self.assertEqual(BOOT.map_level(PID), FIXTURE_LEVEL)  # type: ignore[union-attr]
        self.assertEqual(BOOT.level_entry_count(), 100)  # type: ignore[union-attr]
        self.assertEqual(BOOT.level_entry(0)["name"], "Slave")  # type: ignore[union-attr,index]
        self.assertEqual(BOOT.level_entry(0)["exp_required"], 0)  # type: ignore[union-attr,index]
        self.assertEqual(BOOT.level_entry(1)["name"], "Servant")  # type: ignore[union-attr,index]
        self.assertIsNone(BOOT.level_entry(100))  # type: ignore[union-attr]
        # The derived level for the recorded experience is the recorded level.
        rows = [
            BOOT.level_entry(position)  # type: ignore[union-attr]
            for position in range(BOOT.level_entry_count())  # type: ignore[union-attr]
        ]
        self.assertEqual(
            level_envelope.derived_level_for(FIXTURE_XP, level_envelope.thresholds_from_entries(rows)),
            FIXTURE_LEVEL,
        )
        self.assertEqual(intent["level"], FIXTURE_LEVEL)
        # The rejected zero-based reading is still contradicted by the corpus.
        self.assertNotEqual(FIXTURE_LEVEL, 0)

    def test_b_the_endpoint_refuses_the_recorded_state_and_leaves_it_identical(
        self,
    ) -> None:
        """The recorded condition replayed: with the fixture's before-state the
        endpoint answers ``level_already_current`` — which is exactly what the
        recorded transaction's identical level documents — and the corpus is
        byte-identical."""
        intent = recorded_intent()
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        working_before = harness.working_tree_save_hashes()

        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])

        response = level_up_town({"user_id": intent["user_id"]})

        self.assertEqual(response.status_code, 409)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "level_already_current")
        # Never a partial payload.
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertIn("already 1", body["error"]["message"])
        # Nothing ran.
        self.assertEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        self.assertEqual(BOOT.map_level(PID), FIXTURE_LEVEL)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), working_before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_c_the_recorded_after_state_is_reproduced_from_a_disagreement(self) -> None:
        """The success path, replayed: from a state whose recorded level is
        **below** the derived one, the endpoint writes exactly the fixture's
        level, moves no resource, and leaves every other leaf byte-identical to
        the captured after-state.

        This is the parity claim's executing half.  The corpus is seeded from the
        committed save and its stored experience is set to the curve's second
        threshold, so the derived level is 2 while the recorded level is 1 — the
        recorded-versus-derived disagreement design D2 exists to report.  The
        recorded fixture itself cannot show a *movement*, because on the
        committed corpus the derived level already equals the recorded one; the
        post-state is therefore compared leaf for leaf with the one leaf that
        necessarily differs (``/maps/0/level``) named.
        """
        self.assertEqual(harness.read_seeded_save(CORPUS), FIXTURE["before"])
        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        save["maps"][0]["xp"] = 40  # the curve's second threshold -> level 2
        save["maps"][0]["level"] = FIXTURE_LEVEL  # the recorded level, below it
        self._persist()

        response = level_up_town({"user_id": str(harness.load_seed()["playerInfo"]["pid"])})  # type: ignore[index]

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            sorted(payload),
            sorted(
                [
                    "protocol",
                    "ok",
                    "game_version",
                    "server_time",
                    "result",
                    "derived_level",
                    "level_before",
                    "level_after",
                    "curve",
                    "resources",
                ]
            ),
        )
        # 1. Response equals the captured legacy response for the field the
        #    legacy response had; the rest is the documented superset.
        self.assertEqual(payload["result"], json.loads(FIXTURE["body"])["result"])
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # 2. Both levels, and the derived one from the committed curve.
        self.assertEqual(payload["level_before"], FIXTURE_LEVEL)
        self.assertEqual(payload["derived_level"], 2)
        self.assertEqual(payload["level_after"], 2)
        self.assertEqual(BOOT.map_level(PID), 2)  # type: ignore[union-attr]
        # 3. The curve facts, read from the committed curve.
        curve = payload["curve"]
        self.assertEqual(curve["entries"], 100)
        self.assertEqual(curve["index_base"], "one-based")
        self.assertEqual(curve["derivation_status"], "derived-provisional")
        self.assertEqual(curve["rejected_alternative"], "zero-based")
        self.assertEqual(curve["entry_name"], "Servant")
        self.assertEqual(curve["entry_exp_required"], 40)
        self.assertEqual(curve["xp"], 40)
        # 4. No reward, and no resource movement.
        self.assertNotIn("reward", json.dumps(payload, sort_keys=True))
        resources_after = resources_of(harness.read_seeded_save(CORPUS))  # type: ignore[arg-type]
        self.assertEqual(payload["resources"], resources_after)
        movement = {
            name: resources_after[name] - resources_of(FIXTURE["before"])[name]
            for name in FIXTURE_RESOURCE_NAMES
        }
        # The only movement is the **test-only** experience the replay set (4 ->
        # 40); the level-up itself moved nothing, which is the point.
        self.assertEqual(
            movement,
            {"cash": 0, "gold": 0, "mana": 0, "oil": 0, "steel": 0, "wood": 0, "xp": 36},
        )
        # 5. The corpus save differs from the captured after-state at exactly two
        #    leaves: ``/maps/0/level`` (the one a level-up owns) and
        #    ``/maps/0/xp`` (the test-only experience the disagreement needs).
        #    Nothing else moved.
        raw_after = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(
            leaf_differences(FIXTURE["after"], raw_after),
            ["/maps/0/level", "/maps/0/xp"],
        )
        # With the fixture's own level and experience restored, the documents are
        # equal leaf for leaf with no normalization at all — the strongest form
        # of the parity claim.
        restored = copy.deepcopy(raw_after)
        restored["maps"][0]["level"] = FIXTURE["after"]["maps"][0]["level"]  # type: ignore[index]
        restored["maps"][0]["xp"] = FIXTURE["after"]["maps"][0]["xp"]  # type: ignore[index]
        self.assertEqual(harness.diff_documents(FIXTURE["after"], restored), [])
        self.assertEqual(leaf_differences(FIXTURE["after"], restored), [])
        # 6. Persistence happened in the corpus and nowhere else.
        self.assertNotEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        # Restore the shared corpus so a later replay starts from the fixture.
        save["maps"][0]["xp"] = FIXTURE_XP
        save["maps"][0]["level"] = FIXTURE_LEVEL
        self._persist()

    def _persist(self) -> None:
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
        with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(save, stream, indent=4)
            stream.write("\n")


class LevelParitySurfaceTests(unittest.TestCase):
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
        self.assertIn("**Established from committed legacy source", readme)
        self.assertIn("**Derived and never observed from the Flash client**", readme)
        self.assertIn("Established from committed legacy source, the committed command catalog", readme)
        # The probe.
        self.assertIn("Probe 1", readme)
        self.assertIn("level_up([2])", readme)
        self.assertIn("[0, 500, 0, 0, 0, 0, 0, 0]", readme)
        # The decisions.
        for name in ("D1", "D2", "D3", "D4", "D5", "D6", "D7"):
            with self.subTest(decision=name):
                self.assertIn(name, readme)
        # The index base, its status, and the rejected alternative.
        self.assertIn("ONE-BASED", readme)
        self.assertIn("DERIVED-PROVISIONAL", readme)
        self.assertIn("ZERO-BASED", readme)
        self.assertIn("entry_index_for_level", readme)
        self.assertIn(
            "corpus xp = 4 | stored level = 1 | level the 0-based curve implies = 0",
            readme,
        )
        self.assertIn("shift **every** level in the game by one", readme)
        # The envelope.
        self.assertIn('[[0,"level_up",[1],[0,0,0,0,0,0,0,0]]]', readme)
        self.assertIn("[0, 0, 0, 0, 0, 0, 0, 0]", readme)
        # The refusals and the corpus condition behind the first one.
        self.assertIn("level_already_current", readme)
        self.assertIn("xp_below_threshold", readme)
        self.assertIn(
            "the exact corpus condition behind the endpoint's\n  `level_already_current` refusal",
            readme,
        )
        # Design D7's non-claims.
        self.assertIn("No level reward is paid", readme)
        self.assertIn("Unit experience and tutorial progression are out of scope", readme)
        self.assertIn("The curve is preserved verbatim", readme)
        # The recorded fact that the level did not move.
        self.assertIn("did not move", readme)
        self.assertIn("exactly **zero** leaves differ", readme.lower())
        self.assertIn("/transaction/recorded_leaf_differences", readme)
        # The clamp and the determinism claim.
        self.assertIn("clamp is not exercised by this fixture", readme)
        self.assertIn("exactly 8 differing file+pointer paths", readme)
        self.assertIn("state_leaves", readme)
        # The containment count.
        self.assertIn("**ten** already committed fixture", readme)
        # The closure claims.
        self.assertIn("No Flash, Ruffle, ActionScript, or browser", readme)
        self.assertIn("no external network", readme)
        self.assertIn("no pixel-parity oracle", readme)

    def test_the_fixture_readme_records_the_executed_outcome(self) -> None:
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn("`maps[0].xp` is `4`", readme)
        self.assertIn("Level sent**: `1`", readme)
        self.assertIn("stays `40`", readme)
        self.assertIn("byte-identical across reruns", readme)
        self.assertIn("`xp 4`, `gold 2000`", readme)
        self.assertIn("`playerInfo.cash 5`, `privateState.mana 0`", readme)

    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        self.assertFalse(
            (harness.REPO_ROOT / "saves").exists(),
            "a level-up execution created a working-tree saves/ directory",
        )


if __name__ == "__main__":
    unittest.main()