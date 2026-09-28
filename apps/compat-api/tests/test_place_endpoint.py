#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/place`` behavior tests (OpenSpec task 2.1).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection. The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``tests/saves/``) stay byte-identical across placement execution.

Covered, per task 2.1:

* **derivations** — the committed config price vector lands in exactly
  the resources the response reports (``w`` → wood, ``g`` → gold with
  the legacy ``max(…, 0)`` clamp at zero), the slot comes from the
  save's own smallest-free-slot rule, and the persisted entry matches
  what legacy ``engine.map_add_item`` writes (field order, ``attr``
  from ``clicks_to_build``, ``boughtUnits`` bookkeeping);
* **fail-closed paths** — every structurally unresolvable input in the
  spec (non-object body, missing/invalid/unknown save id, missing/
  invalid/unknown item id, non-integer or out-of-grid coordinates,
  non-integer orientation) returns its documented structured error with
  the corpus byte-unchanged and no entry allocated;
* **no client-supplied resource delta** is ever honored;
* **session/bootstrap byte-identity** is retained after placements.

The tests derive their expectations from the live save state rather than
hard-coded counters, so they are order-independent within the module.
"""

from __future__ import annotations

import copy
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import placement_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# Config facts pinned by the committed config (see the fixture README):
HOUSE_I = 1  # House I — costs {"w":30}, 2x2, clicks_to_build 1
WOOD_FACTORY_III = 10  # Wood Factory III — costs {"g":6000}: exceeds fresh gold
WALL_I = 23  # Wall I — costs {"w":5}


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE
    ORIGINAL_CWD = os.getcwd()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    # The corpus is discarded, but the working tree must be untouched by
    # every placement execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a placement execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def place(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/place", json=payload)  # type: ignore[union-attr]


def current_slot() -> int:
    return placement_envelope.next_free_slot(BOOT.map_items(PID))  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


class PlaceDerivationTests(unittest.TestCase):
    """The observable effects of the derived legacy envelope."""

    def test_success_reports_legacy_result_persisted_entry_and_resources(self) -> None:
        slot = current_slot()
        before = BOOT.resources(PID)  # type: ignore[union-attr]

        response = place({"user_id": PID, "item_id": HOUSE_I, "x": 51, "y": 39})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            set(payload),
            {
                "protocol",
                "ok",
                "game_version",
                "server_time",
                "result",
                "placement",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # The legacy result: the command.php route returns exactly this
        # whenever command() returns without raising.
        self.assertEqual(payload["result"], "success")

        placement = payload["placement"]
        self.assertIsInstance(placement, list)
        self.assertEqual(len(placement), 8)
        # Field order, spec: item, x, y, timestamp, orientation, store, attr, player.
        self.assertEqual(placement[0], HOUSE_I)
        self.assertEqual(placement[1], 51)
        self.assertEqual(placement[2], 39)
        self.assertIsInstance(placement[3], int)
        self.assertGreater(placement[3], 0)  # wall clock — documented time-dependent
        self.assertEqual(placement[4], 0)  # orientation
        self.assertEqual(placement[5], [])  # store
        # Legacy attr rule: clicks_to_build 1 > 0 -> {"nc": 0}.
        self.assertEqual(placement[6], {"nc": 0})
        self.assertEqual(placement[7], 1)  # player team 1

        # resources_changed = negated config costs on the legacy vector:
        # only wood moves, by exactly 30 (fresh stock never clamps here).
        expected = dict(before)
        expected["wood"] = max(before["wood"] - 30, 0)
        self.assertEqual(payload["resources"], expected)

        # The response is read back from what actually landed on disk.
        saved = corpus_save()
        self.assertEqual(saved["maps"][0]["items"][str(slot)], placement)
        self.assertEqual(saved["maps"][0]["wood"], expected["wood"])
        # Legacy buy records the bought item id for player team 1.
        self.assertIn(HOUSE_I, saved["privateState"]["boughtUnits"])

        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_second_placement_uses_the_next_free_slot(self) -> None:
        slot = current_slot()
        before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]

        response = place({"user_id": PID, "item_id": WALL_I, "x": 60, "y": 39})

        self.assertEqual(response.status_code, 200)
        placement = response.get_json()["placement"]
        saved_items = corpus_save()["maps"][0]["items"]
        # Exactly one new entry, at the derived slot, identical to disk.
        self.assertEqual(set(saved_items), set(before_items) | {str(slot)})
        self.assertEqual(saved_items[str(slot)], placement)
        self.assertEqual(placement[0], WALL_I)

    def test_cost_vector_applies_with_the_legacy_clamp_at_zero(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]

        response = place(
            {"user_id": PID, "item_id": WOOD_FACTORY_III, "x": 70, "y": 39}
        )

        # Clamp, never rejection: legacy apply_resources does max(…, 0).
        self.assertEqual(response.status_code, 200)
        resources = response.get_json()["resources"]
        self.assertEqual(resources["gold"], max(before["gold"] - 6000, 0))
        self.assertEqual(resources["gold"], 0)  # 2000 fresh gold < 6000 price
        for key in ("xp", "wood", "oil", "steel", "cash", "mana"):
            self.assertEqual(resources[key], before[key])

        saved = corpus_save()
        self.assertEqual(saved["maps"][0]["gold"], 0)
        self.assertEqual(saved["playerInfo"]["cash"], resources["cash"])
        self.assertEqual(saved["privateState"]["mana"], resources["mana"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_client_supplied_resource_deltas_are_ignored(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]

        response = place(
            {
                "user_id": PID,
                "item_id": HOUSE_I,
                "x": 80,
                "y": 39,
                "resources_changed": [0, 999, 999, 999, 999, 999, 999, 999],
                "resources": {"gold": 999999},
                "result": "hacked",
            }
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The server's own derivation wins; the extra keys are ignored.
        self.assertEqual(payload["result"], "success")
        expected = dict(before)
        expected["wood"] = max(before["wood"] - 30, 0)
        self.assertEqual(payload["resources"], expected)
        self.assertEqual(payload["resources"]["gold"], before["gold"])


class PlaceFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation (D5)."""

    def setUp(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]

    def assert_fail_closed(self, response, status: int, code: str) -> None:
        self.assertEqual(response.status_code, status)
        body = response.get_json()
        self.assertIsInstance(body, dict)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        # Every failure path precedes legacy execution: no mutation anywhere.
        self.assertEqual(harness.save_hashes(CORPUS), self.before_hashes)  # type: ignore[arg-type]
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_non_object_bodies(self) -> None:
        with harness.offline():
            responses = [
                CLIENT.post("/v0/place"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/place", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/place", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/place", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        self.assert_fail_closed(place({}), 400, "missing_user_id")
        self.assert_fail_closed(place({"user_id": ""}), 400, "missing_user_id")
        self.assert_fail_closed(place({"user_id": None}), 400, "missing_user_id")
        self.assert_fail_closed(place({"user_id": 123}), 400, "invalid_user_id")
        self.assert_fail_closed(place({"user_id": "ghost"}), 404, "unknown_user_id")

    def test_item_id_failures(self) -> None:
        base: Dict[str, Any] = {"user_id": PID, "x": 51, "y": 39}
        self.assert_fail_closed(place(dict(base)), 400, "missing_item_id")
        self.assert_fail_closed(
            place({**base, "item_id": "1"}), 400, "invalid_item_id"
        )
        self.assert_fail_closed(
            place({**base, "item_id": True}), 400, "invalid_item_id"
        )
        self.assert_fail_closed(
            place({**base, "item_id": 999999999}), 404, "unknown_item_id"
        )

    def test_coordinate_failures(self) -> None:
        base: Dict[str, Any] = {"user_id": PID, "item_id": HOUSE_I}
        self.assert_fail_closed(place({**base, "y": 39}), 400, "invalid_coordinates")
        self.assert_fail_closed(
            place({**base, "x": "51", "y": 39}), 400, "invalid_coordinates"
        )
        self.assert_fail_closed(
            place({**base, "x": 51.5, "y": 39}), 400, "invalid_coordinates"
        )
        self.assert_fail_closed(
            place({**base, "x": 100, "y": 39}), 400, "invalid_coordinates"
        )
        self.assert_fail_closed(
            place({**base, "x": 51, "y": -1}), 400, "invalid_coordinates"
        )
        self.assert_fail_closed(
            place({**base, "x": 51, "y": 99.5}), 400, "invalid_coordinates"
        )
        self.assert_fail_closed(
            place({**base, "x": True, "y": 39}), 400, "invalid_coordinates"
        )

    def test_orientation_failure(self) -> None:
        self.assert_fail_closed(
            place(
                {"user_id": PID, "item_id": HOUSE_I, "x": 51, "y": 39, "orientation": "0"}
            ),
            400,
            "invalid_orientation",
        )


class PlaceContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_placements(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        with harness.offline():
            session = CLIENT.get("/v0/session")  # type: ignore[union-attr]
            bootstrap = CLIENT.post(  # type: ignore[union-attr]
                "/v0/bootstrap", json={"user_id": PID}
            )
        self.assertEqual(session.status_code, 200)
        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_placements_never_touch_working_tree_saves(self) -> None:
        response = place({"user_id": PID, "item_id": HOUSE_I, "x": 90, "y": 90})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class PlaceSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/place")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 405)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "method_not_allowed")

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
