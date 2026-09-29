#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/move`` behavior tests (OpenSpec task 2.2).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection. The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across move
execution.

Covered, per task 2.2:

* **derivations** — the row the response reports is the one persisted in
  the corpus save, with the requested cell at indices 1 and 2 and every
  other field of the row untouched, and the response's ``resources`` mirror
  the persisted resource values;
* **neutral resources** — no resource moves, because the derived vector is
  all zeros, and no client-supplied price, resource delta, ``frame``, or
  ``string`` is honored;
* **fail-closed paths** — every structurally unresolvable input in the spec
  (non-object body, missing/invalid/unknown save id, missing/invalid/unknown
  item index, non-integer or out-of-grid coordinates) returns its documented
  structured error with the corpus byte-unchanged and no row moved;
* **session/bootstrap byte-identity** is retained after moves.
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
import move_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The fixture intent, derived under the rule the executed-legacy capture
# documents: the Turret I at map slot 11, moved to the Manhattan-nearest
# free one-step neighbour (58,48) -> (58,47).
TURRET_INDEX = 11
TURRET_ITEM_ID = 22
FREE_TARGET = (58, 47)
OCCUPIED_TARGET = (59, 48)  # a Wall I row one step east of the anchor


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
    # every move execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a move execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def move(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/move", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def map_items() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["items"]  # type: ignore[index]


def intent(x: int, y: int, index: int = TURRET_INDEX) -> Dict[str, Any]:
    return {"user_id": PID, "item_index": index, "x": x, "y": y}


class MoveDerivationTests(unittest.TestCase):
    """The observable effects of the derived legacy envelope."""

    def test_success_reports_legacy_result_persisted_row_and_resources(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())
        before_row = list(before_items[str(TURRET_INDEX)])

        response = move(intent(*FREE_TARGET))

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

        # The persisted eight-field row, with only x/y written.
        expected_row = list(before_row)
        expected_row[1], expected_row[2] = FREE_TARGET
        self.assertEqual(payload["placement"], expected_row)
        self.assertEqual(len(payload["placement"]), 8)
        self.assertEqual(payload["placement"][0], TURRET_ITEM_ID)
        # Every other field of the row is the value legacy already held.
        self.assertEqual(payload["placement"][3:], before_row[3:])

        # Neutral price vector: no stored resource moves at all.
        self.assertEqual(payload["resources"], before)
        self.assertEqual(
            set(payload["resources"]),
            {"xp", "gold", "wood", "oil", "steel", "cash", "mana"},
        )

        # The response is read back from what actually landed on disk.
        saved = map_items()
        self.assertEqual(saved[str(TURRET_INDEX)], payload["placement"])
        self.assertEqual(
            corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"]
        )
        self.assertEqual(corpus_save()["maps"][0]["gold"], payload["resources"]["gold"])
        # Nothing else about the map changed.
        self.assertEqual(sorted(saved), sorted(before_items))
        self.assertEqual(len(saved), 40)
        for key in before_items:
            if key == str(TURRET_INDEX):
                continue
            with self.subTest(key=key):
                self.assertEqual(saved[key], before_items[key])
        self.assertEqual(corpus_save()["maps"][0]["store"], {})
        self.assertEqual(corpus_save()["privateState"]["boughtUnits"], [])

        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_moving_a_row_twice_is_the_second_cell_not_the_first(self) -> None:
        first = move(intent(*FREE_TARGET))
        self.assertEqual(first.status_code, 200)
        second = move(intent(57, 48))
        self.assertEqual(second.status_code, 200)
        payload = second.get_json()
        self.assertEqual(payload["placement"][1], 57)
        self.assertEqual(payload["placement"][2], 48)
        self.assertEqual(map_items()[str(TURRET_INDEX)], payload["placement"])
        self.assertEqual(
            harness.working_tree_save_hashes(), WORKING_TREE_PRE
        )

    def test_a_move_to_the_occupied_neighbour_is_not_rejected(self) -> None:
        """Occupancy is a client-side rule (design D5), not a server one.

        Legacy ``move`` performs no collision check at all, so the endpoint
        reproduces that: the target is written and the response is a success.
        This test documents the boundary — it is not a gameplay claim.
        """
        response = move(intent(*OCCUPIED_TARGET))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["result"], "success")
        self.assertEqual(
            [payload["placement"][1], payload["placement"][2]], list(OCCUPIED_TARGET)
        )
        # The two rows now share a cell, exactly as legacy would leave them.
        items = map_items()
        self.assertEqual(items["9"][1], 59)
        self.assertEqual(items["9"][2], 48)
        self.assertEqual(items[str(TURRET_INDEX)][1:3], list(OCCUPIED_TARGET))
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_anchor_bound_is_accepted_at_both_grid_edges(self) -> None:
        for x, y in ((0, 0), (99, 99)):
            with self.subTest(x=x, y=y):
                response = move(intent(x, y))
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(
                    [payload["placement"][1], payload["placement"][2]], [x, y]
                )

    def test_client_supplied_price_deltas_frame_and_string_are_ignored(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_row = copy.deepcopy(map_items()[str(TURRET_INDEX)])

        response = move(
            dict(
                intent(*FREE_TARGET),
                resources_changed=[0, 999, 999, 999, 999, 999, 999, 999],
                resources={"cash": 999999},
                price=[0, 0, 0, 0, 0, 0, -500, 0],
                frame=3,
                string="client-supplied",
                result="hacked",
                placement=[0, 0, 0, 0, 0, [], {}, 0],
            )
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The server's own derivation wins; the extra keys are ignored.
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["resources"], before)
        expected_row = list(before_row)
        expected_row[1], expected_row[2] = FREE_TARGET
        # frame/string are the module's placeholders, never the client's, and
        # legacy discards them either way, so the row is unchanged apart from
        # the cell.
        self.assertEqual(payload["placement"], expected_row)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_derived_envelope_is_the_move_command(self) -> None:
        built = move_envelope.build_envelope(
            item_index=TURRET_INDEX, x=FREE_TARGET[0], y=FREE_TARGET[1],
            ts=1700000000,
        )
        self.assertEqual(built["commands"][0][1], "move")
        self.assertEqual(
            built["commands"][0][2], [TURRET_INDEX, FREE_TARGET[0], FREE_TARGET[1], 0, ""]
        )
        self.assertEqual(built["commands"][0][3], [0] * 8)
        self.assertEqual(compat_service.move_envelope, move_envelope)


class MoveFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation (D3)."""

    def setUp(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.before_store = copy.deepcopy(BOOT.map_store(PID))  # type: ignore[union-attr]

    def assert_fail_closed(self, response, status: int, code: str) -> None:
        self.assertEqual(response.status_code, status)
        body = response.get_json()
        self.assertIsInstance(body, dict)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)
        # Never a partial payload: only the three documented error keys.
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(set(body["error"]), {"code", "message"})
        # Every failure path precedes legacy execution: no mutation anywhere.
        self.assertEqual(harness.save_hashes(CORPUS), self.before_hashes)  # type: ignore[arg-type]
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), self.before_store)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_non_object_bodies(self) -> None:
        with harness.offline():
            responses = [
                CLIENT.post("/v0/move"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/move", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/move", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/move", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {
            "item_index": TURRET_INDEX, "x": FREE_TARGET[0], "y": FREE_TARGET[1],
        }
        self.assert_fail_closed(move({}), 400, "missing_user_id")
        self.assert_fail_closed(
            move({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            move({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            move({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(move({"user_id": "ghost", **base}), 404, "unknown_user_id")

    def test_item_index_failures(self) -> None:
        self.assert_fail_closed(
            move({"user_id": PID, "x": 58, "y": 47}), 400, "missing_item_index"
        )
        for bad in ("11", 11.0, True, None, [11]):
            with self.subTest(item_index=bad):
                self.assert_fail_closed(
                    move({"user_id": PID, "item_index": bad, "x": 58, "y": 47}),
                    400,
                    "invalid_item_index",
                )

    def test_an_unknown_item_index_fails_closed(self) -> None:
        """Legacy would log an error, return early, and still persist.

        The endpoint answers a structured 404 instead, so a stale index can
        never be reported as a successful move (design D3).
        """
        for index in (0, 41, 999999999, -1):
            with self.subTest(item_index=index):
                response = move(intent(FREE_TARGET[0], FREE_TARGET[1], index))
                self.assert_fail_closed(response, 404, "unknown_item_index")
                self.assertIn(
                    str(index), response.get_json()["error"]["message"]
                )

    def test_coordinate_failures(self) -> None:
        for x, y in ((None, 47), (58, None), ("58", 47), (58, "47"), (58, 47.5),
                     (58, True), (-1, 47), (58, -1), (100, 47), (58, 100)):
            with self.subTest(x=x, y=y):
                self.assert_fail_closed(
                    move({"user_id": PID, "item_index": TURRET_INDEX, "x": x, "y": y}),
                    400,
                    "invalid_coordinates",
                )

    def test_coordinates_are_validated_before_the_dispatcher_even_runs(self) -> None:
        """An unresolvable cell is a 400, never a partial write."""
        before = copy.deepcopy(map_items()[str(TURRET_INDEX)])
        response = move({"user_id": PID, "item_index": TURRET_INDEX, "x": 100, "y": 100})
        self.assert_fail_closed(response, 400, "invalid_coordinates")
        self.assertEqual(map_items()[str(TURRET_INDEX)], before)


class MoveContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_moves(self) -> None:
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

    def test_moves_never_touch_working_tree_saves(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        # A cell the row is not already on, so the save really mutates and the
        # assertion below is about a real write rather than a no-op.
        current = map_items()[str(TURRET_INDEX)][1:3]
        target = (0, 0) if list(current) != [0, 0] else (1, 1)
        response = move(intent(*target))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["placement"][1:3], list(target))
        # The corpus save moved; the working tree did not.
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_legacy_accessors_agree_with_the_map(self) -> None:
        self.assertTrue(BOOT.has_map_item(PID, TURRET_INDEX))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 0))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, TURRET_INDEX)  # type: ignore[union-attr]
        self.assertIsInstance(row, list)
        self.assertEqual(len(row), 8)  # type: ignore[arg-type]
        self.assertEqual(
            row, BOOT.map_items(PID)[str(TURRET_INDEX)]  # type: ignore[union-attr]
        )
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]

    def test_a_row_the_legacy_dispatcher_dropped_is_a_500_not_a_success(self) -> None:
        """The read-back guard mirrors ``/v0/place``'s persisted-entry check.

        Legacy ``move`` on a missing row is a silent no-op, so a row that
        vanishes between resolution and read-back would otherwise be reported
        as a move that never happened.
        """
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        BOOT.map_item = lambda user_id, index: None  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post(
                    "/v0/move", json=intent(*FREE_TARGET)
                )
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("placement", body["error"]["message"])


class MoveSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/move")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 405)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "method_not_allowed")

    def test_the_other_routes_are_untouched(self) -> None:
        with harness.offline():
            self.assertEqual(CLIENT.get("/v0/session").status_code, 200)  # type: ignore[union-attr]
            self.assertEqual(  # type: ignore[union-attr]
                CLIENT.post("/v0/bootstrap", json={"user_id": PID}).status_code, 200
            )
            unknown = CLIENT.get("/v0/move/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index")
        self.assertEqual(compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_COORDINATES, "invalid_coordinates")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
