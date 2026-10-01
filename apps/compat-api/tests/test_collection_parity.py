#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/collection`` vs the executed-legacy
collection fixture (OpenSpec task 3.4).

No server and no network: the endpoint runs through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and ``test_no_server_is_running`` asserts that neither the legacy port
(5055) nor the Compatibility API port (5056) is listening.

What is replayed
    The committed transaction under ``tests/fixtures/godot-unit-collection/`` -
    one real ``complete_collection`` on collection id **1** ("Draggy
    Collection"), carrying the **neutral** vector ``[0, 0, 0, 0, 0, 0, 0, 0]``,
    executed by the legacy server in a disposable copy against the fresh-player
    corpus, whose ``maps[0]["store"]`` is ``{}`` and whose
    ``privateState["collections"]`` is ``[]``.  The committed prize is unit
    ``1085`` Metal Draggy, so this is the project's **first content-derived,
    server-authoritative unit acquisition**, exercised with **no fabricated
    player state**.  The endpoint derives the very same envelope from the very
    same module, so the replay compares:

    * the response ``result`` against the captured legacy response body;
    * the response's ``collection_id``, ``grant``, and ``prize`` against the
      recorded states - the granted id and quantity **by value** against the
      committed bag, and both ledgers entry by entry;
    * the response's ``index`` block against the one-based derivation, with the
      rejected zero-based alternative retained and no clamping on this id;
    * the response's ``resources`` against the values read from the captured
      after-state - all seven slots are stable and the captured movement is the
      derived neutral vector, which is nothing;
    * the corpus save after execution against the captured after-state, leaf for
      leaf, with **NO** normalization at all: this transaction writes no clock
      value, so every leaf is compared by value;
    * the shared derivation against the recorded request envelope, exactly (the
      recorded ``ts`` is passed back into the derivation).

**No normalization is applied, and that is asserted.**  Unlike the move,
collect, and queue fixtures this transaction carries **no** time-dependent
state value: ``complete_collection`` writes only the storage and the collection
ledger, and neither touches a clock.  The capture's manifest lists no
``state_leaves`` at all, and the suite asserts that emptiness — so a future
re-capture that started stamping a clock would fail here rather than silently
acquire an unchecked difference.

The parity claim covers this one recorded transaction against the fresh-player
corpus (see the fixture README's claim limits).  In particular the fixture
evidences a **grant into storage and not a unit placed on the map**: the
stored-item placement step was deliberately not chained, so the placement count
is unchanged at 40 and no map row is written.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import collection_envelope
import compat_legacy
import compat_service

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-unit-collection"
COMPLETE_STEP = "command_complete_collection"
LOGIN_STEP = "login_post"
FIXTURE_COLLECTION_ID = 1
FIXTURE_COLLECTION_NAME = "Draggy Collection"
FIXTURE_PRIZE_ID = "1085"
FIXTURE_PRIZE_QUANTITY = 1
FIXTURE_EXPECTED_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
FIXTURE_PLACEMENTS = 40
FIXTURE_RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")
COMMITTED_RESOURCES = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


def load_step(name: str) -> Dict[str, Any]:
    base = FIXTURES / "steps" / name
    return {
        "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
        "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
        "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
        "meta": json.loads(
            (base / "response.meta.json").read_text(encoding="utf-8")
        ),
        "body": (base / "response.body").read_bytes(),
    }


def load_fixture() -> Dict[str, Any]:
    fixture = {
        "login": load_step(LOGIN_STEP),
        "complete": load_step(COMPLETE_STEP),
        "manifest": json.loads(
            (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
        ),
        "readme": (FIXTURES / "README.md").read_text(encoding="utf-8"),
    }
    data = fixture["complete"]["request"]["form"]["data"]
    envelope = collection_envelope.parse_data_field(data)
    entry = envelope["commands"][0]
    fixture["complete"]["envelope"] = envelope
    fixture["complete"]["intent"] = {
        "user_id": fixture["complete"]["request"]["form"]["USERID"],
        "collection_id": entry[2][0],
        "bought_flag": entry[2][1],
        "command": entry[1],
        "map_id": entry[0],
        "vector": entry[3],
    }
    return fixture


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


def complete_now(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/collection", json=payload)  # type: ignore[union-attr]


def reset_state(store: Optional[Dict[str, Any]] = None,
                ledger: Optional[List[Any]] = None) -> None:
    """Reset the storage and ledger to the committed corpus state, in place."""
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["maps"][0]["store"] = json.loads(json.dumps({} if store is None else store))
    save["privateState"]["collections"] = list(
        [] if ledger is None else ledger
    )
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
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
            if len(one) != len(other):
                out.append(path)
                return
            for index, (a, b) in enumerate(zip(one, other)):
                walk(a, b, "%s/%d" % (path, index), out)
        elif one != other:
            out.append(path or "/")

    paths: List[str] = []
    walk(left, right, "", paths)
    return paths


class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivation rules."""

    def test_the_recorded_request_carries_exactly_one_neutral_completion(self) -> None:
        intent = FIXTURE["complete"]["intent"]
        self.assertEqual(intent["user_id"], PID)
        self.assertEqual(intent["collection_id"], FIXTURE_COLLECTION_ID)
        self.assertEqual(intent["bought_flag"], collection_envelope.DERIVED_BOUGHT)
        self.assertEqual(intent["map_id"], 0)
        self.assertEqual(intent["command"], "complete_collection")
        self.assertEqual(intent["vector"], FIXTURE_EXPECTED_VECTOR)
        envelope = FIXTURE["complete"]["envelope"]
        self.assertEqual(len(envelope["commands"]), 1)
        self.assertEqual(sorted(envelope), sorted(collection_envelope.ENVELOPE_KEYS))

    def test_the_derivation_reproduces_the_recorded_envelope_exactly(self) -> None:
        # The recorded `ts` is passed back in, so the derivation is compared on
        # everything a clock could not explain away.
        recorded = FIXTURE["complete"]["envelope"]
        derived = collection_envelope.build_envelope(
            collection_id=FIXTURE_COLLECTION_ID, ts=int(recorded["ts"])
        )
        self.assertEqual(derived, recorded)

    def test_the_recorded_request_redacts_its_secrets(self) -> None:
        form = FIXTURE["complete"]["request"]["form"]
        self.assertEqual(form["user_key"], "<redacted>")
        self.assertEqual(form["USERID"], PID)
        # ``accessToken`` is the crafted EMPTY placeholder, so the redactor leaves
        # it untouched and the recorded field stays the exact sent bytes with a
        # digest that still verifies - which is what lets the replay parse it.
        recorded = collection_envelope.parse_data_field(form["data"])
        self.assertEqual(recorded["accessToken"], "")
        self.assertEqual(recorded["commands"][0][1], "complete_collection")

    def test_the_capture_against_the_committed_corpus_state(self) -> None:
        before = FIXTURE["complete"]["before"]
        self.assertEqual(before["maps"][0]["store"], {})
        self.assertEqual(before["privateState"]["collections"], [])
        self.assertEqual(resources_of(before), COMMITTED_RESOURCES)
        self.assertEqual(len(before["maps"][0]["items"]), FIXTURE_PLACEMENTS)
        self.assertEqual(
            FIXTURE["login"]["before"], before,
            "the login step's before-state IS the corpus, byte-for-byte",
        )

    def test_the_capture_recorded_the_committed_grant_and_one_appended_id(self) -> None:
        after = FIXTURE["complete"]["after"]
        self.assertEqual(after["maps"][0]["store"], {FIXTURE_PRIZE_ID: 1})
        self.assertEqual(after["privateState"]["collections"], [FIXTURE_COLLECTION_ID])
        self.assertEqual(resources_of(after), COMMITTED_RESOURCES)
        self.assertEqual(len(after["maps"][0]["items"]), FIXTURE_PLACEMENTS)
        self.assertEqual(after["maps"][0]["items"], before_items())
        self.assertEqual(after["playerInfo"], FIXTURE["complete"]["before"]["playerInfo"])
        # The legacy HTTP route serializes compactly with a trailing newline; the
        # **parsed** body is the contract, so it is compared as JSON.
        self.assertEqual(
            json.loads(FIXTURE["complete"]["body"].decode("utf-8")),
            {"result": "success"},
        )

    def test_the_capture_declares_no_time_dependent_state_leaf(self) -> None:
        # This is what licenses the suite to apply NO clock normalization, and it
        # is asserted rather than assumed: a re-capture that started stamping a
        # clock would fail here instead of quietly acquiring an unchecked leaf.
        time_dependent = FIXTURE["manifest"]["time_dependent_fields"]
        self.assertEqual(time_dependent["state_leaves"], [])
        self.assertEqual(
            FIXTURE["complete"]["changed_leaves"]
            if "changed_leaves" in FIXTURE["complete"]
            else FIXTURE["manifest"]["transaction"]["changed_leaves"],
            ["/maps/0/store/1085", "/privateState/collections"],
        )

    def test_the_manifest_records_the_derivation_and_the_stopped_scope(self) -> None:
        manifest = FIXTURE["manifest"]
        self.assertEqual(manifest["schema"], "godot-unit-collection/legacy-capture-v1")
        self.assertTrue(manifest["grant"]["derived_from_committed_content"])
        self.assertIn("committed collections table", manifest["grant"]["derivation"])
        self.assertFalse(manifest["captured"]["stored_item_placement_chained"])
        self.assertIn("SEPARATE carried follow-up",
                      manifest["captured"]["note"])
        self.assertFalse(manifest["recorded_steps"]["unit_placed"])
        self.assertFalse(manifest["recorded_steps"]["xp_awarded"])
        self.assertFalse(manifest["recorded_steps"]["income_derived"])
        self.assertFalse(manifest["recorded_steps"]["cap_interpreted"])
        self.assertFalse(manifest["recorded_steps"]["eligibility_checked"])
        self.assertTrue(manifest["containment"]["identical"])
        self.assertTrue(manifest["containment"]["loopback_only"])
        self.assertEqual(
            len(manifest["containment"]["protected_fixtures"]["paths"]), 12
        )
        self.assertEqual(len(manifest["probes"]), 2)
        for probe in manifest["probes"]:
            self.assertTrue(probe["executed_in_this_capture"])

    def test_the_probes_record_the_two_executed_guarantees(self) -> None:
        probes = FIXTURE["manifest"]["probes"]
        neutral = probes[0]
        self.assertEqual(neutral["xp_before"], 4)
        self.assertEqual(neutral["xp_after"], 504)
        self.assertEqual(neutral["ledger_before"], [FIXTURE_COLLECTION_ID])
        self.assertEqual(neutral["ledger_after"], [FIXTURE_COLLECTION_ID])
        self.assertEqual(neutral["store_after"], {"1085": 2})
        self.assertIn(
            "ONLY when it is absent",
            FIXTURE["manifest"]["recorded_steps"]["grant_writes"][3],
        )
        self.assertIn("idempotent while the GRANT is not", probes[0]["ledger_note"])
        eligibility = probes[1]
        self.assertEqual(eligibility["ledger_after"], [FIXTURE_COLLECTION_ID, 10])
        self.assertIn("1056", str(eligibility["store_after"]))
        self.assertIn("NO eligibility check exists", eligibility["established"])

    def test_the_fixture_readme_states_the_claim_limits(self) -> None:
        readme = FIXTURE["readme"]
        # Fragments rather than whole sentences: the README wraps, so a phrase is
        # matched on the two halves that can never drift apart.
        self.assertIn("content-derived, server-authoritative", readme)
        self.assertIn("unit acquisition in the project", readme)
        self.assertIn("deliberately NOT chained", readme)
        self.assertIn("NOT a unit placed on the map", readme)
        self.assertIn("no eligibility check", readme.lower())
        self.assertIn("not a committed content field at all", readme)
        self.assertIn("no unit income, no cap semantics, and no experience",
                      readme.lower())


def before_items() -> Any:
    return FIXTURE["complete"]["before"]["maps"][0]["items"]


class ParityTests(unittest.TestCase):
    """The endpoint reproduces the recorded transaction exactly."""

    def setUp(self) -> None:
        reset_state()

    def test_the_response_reproduces_the_captured_legacy_result(self) -> None:
        response = complete_now({"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["result"], "success")
        self.assertEqual(
            json.loads(FIXTURE["complete"]["body"].decode("utf-8"))["result"],
            body["result"],
        )

    def test_the_grant_matches_the_committed_bag_by_value(self) -> None:
        body = complete_now(
            {"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID}
        ).get_json()
        recorded = FIXTURE["complete"]["after"]["maps"][0]["store"]
        self.assertEqual(body["grant"]["item_id"], FIXTURE_PRIZE_ID)
        self.assertEqual(body["grant"]["quantity"], FIXTURE_PRIZE_QUANTITY)
        self.assertEqual(body["prize"]["bag"], recorded)
        self.assertEqual(body["store_before"], FIXTURE["complete"]["before"]["maps"][0]["store"])
        self.assertEqual(body["store_after"], recorded)
        self.assertEqual(
            BOOT.map_store(PID), recorded  # type: ignore[union-attr]
        )

    def test_the_ledger_grew_by_exactly_one_appended_id(self) -> None:
        body = complete_now(
            {"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID}
        ).get_json()
        self.assertEqual(body["ledger_before"],
                         FIXTURE["complete"]["before"]["privateState"]["collections"])
        self.assertEqual(body["ledger_after"],
                         FIXTURE["complete"]["after"]["privateState"]["collections"])
        self.assertTrue(body["ledger_appended"])
        self.assertEqual(
            BOOT.private_collections(PID),  # type: ignore[union-attr]
            FIXTURE["complete"]["after"]["privateState"]["collections"],
        )

    def test_the_index_block_matches_the_derivation(self) -> None:
        body = complete_now(
            {"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID}
        ).get_json()
        self.assertEqual(body["index"]["base"], "one-based")
        self.assertEqual(body["index"]["derivation_status"], "derived-provisional")
        self.assertEqual(body["index"]["rejected_alternative"], "zero-based")
        self.assertEqual(body["index"]["requested"], 0)
        self.assertEqual(body["index"]["resolved"], 0)
        self.assertFalse(body["index"]["clamped"])
        self.assertFalse(body["index"]["aliased"])
        self.assertIsNone(body["index"]["alias_of"])
        self.assertEqual(body["index"]["rule"], collection_envelope.INDEX_RULE)
        self.assertEqual(body["index"]["alias_rule"], collection_envelope.ALIAS_RULE)

    def test_the_resources_are_unchanged_by_both_sides(self) -> None:
        body = complete_now(
            {"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID}
        ).get_json()
        self.assertEqual(body["resources"], COMMITTED_RESOURCES)
        self.assertEqual(resources_of(FIXTURE["complete"]["after"]),
                         COMMITTED_RESOURCES)
        self.assertEqual(BOOT.resources(PID), COMMITTED_RESOURCES)  # type: ignore[union-attr]

    def test_the_corpus_after_execution_equals_the_capture_leaf_for_leaf(self) -> None:
        complete_now({"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID})
        # NO normalization: this transaction writes no clock value, so every leaf
        # is compared by value and the differing set must be exactly the two the
        # capture recorded.
        differing = leaf_differences(
            FIXTURE["complete"]["before"], BOOT.save_document(PID)  # type: ignore[union-attr]
        )
        self.assertEqual(
            differing,
            FIXTURE["manifest"]["transaction"]["changed_leaves"],
            "the endpoint's after-state differs at exactly the captured leaves",
        )

    def test_a_client_supplied_prize_does_not_change_the_replayed_grant(self) -> None:
        reset_state()
        body = complete_now({
            "user_id": PID,
            "collection_id": FIXTURE_COLLECTION_ID,
            "prize": {"905": 42},
            "item_id": 905,
            "quantity": 42,
            "cost": 5000,
        }).get_json()
        self.assertEqual(body["grant"]["item_id"], FIXTURE_PRIZE_ID)
        self.assertEqual(body["grant"]["quantity"], FIXTURE_PRIZE_QUANTITY)
        self.assertEqual(
            BOOT.map_store(PID),  # type: ignore[union-attr]
            FIXTURE["complete"]["after"]["maps"][0]["store"],
        )
        self.assertEqual(BOOT.resources(PID), COMMITTED_RESOURCES)  # type: ignore[union-attr]

    def test_no_placement_is_written_so_the_map_is_unchanged(self) -> None:
        complete_now({"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID})
        self.assertEqual(
            BOOT.map_items(PID), before_items()  # type: ignore[union-attr]
        )
        self.assertEqual(len(BOOT.map_items(PID)), FIXTURE_PLACEMENTS)  # type: ignore[union-attr]
        self.assertFalse(
            FIXTURE["manifest"]["recorded_steps"]["unit_placed"],
            "the fixture places no unit: the stored-item round trip is a "
            "separate carried follow-up",
        )

    def test_the_working_tree_saves_are_untouched_by_the_replay(self) -> None:
        complete_now({"user_id": PID, "collection_id": FIXTURE_COLLECTION_ID})
        self.assertEqual(WORKING_TREE_PRE, harness.working_tree_save_hashes())


class NoServerTests(unittest.TestCase):
    """The replay opened no connection and started no service."""

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(
                harness.port_is_free("127.0.0.1", port),
                "nothing is listening on 127.0.0.1:%d" % port,
            )

    def test_the_corpus_lives_in_the_system_temp_root(self) -> None:
        self.assertIsNotNone(CORPUS)
        self.assertFalse(str(CORPUS).startswith(str(harness.REPO_ROOT)))
        temp_root = Path(os.environ.get("TEMP", "/tmp"))
        self.assertTrue(str(CORPUS).startswith(str(temp_root)))
        self.assertFalse((harness.REPO_ROOT / "saves").exists())


if __name__ == "__main__":
    unittest.main()