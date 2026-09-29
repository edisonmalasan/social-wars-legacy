#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/sell`` behavior tests (OpenSpec task 2.2).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection. The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across sell
execution.

Every test snapshots the corpus map at its own start and asserts its
post-condition against that snapshot, so the suite is order-independent.

Covered, per task 2.2:

* **derivations** — the row the response reports is the eight-field row
  exactly as it was read *before* execution (design D5), the row is absent
  from the persisted save afterwards, every other row is byte-identical, and
  the response's ``resources`` mirror the persisted resource values;
* **neutral resources** — no resource moves, because the derived vector is
  all zeros, so **no refund is claimed**; no client-supplied reason, refund,
  price, or resource delta is honored anywhere in the contract;
* **fail-closed paths** — every structurally unresolvable input in the spec
  (non-object body, missing/invalid/unknown save id, missing/invalid/unknown
  item index) returns its documented structured error with the corpus
  byte-unchanged and no row removed;
* **the removal proof** — a row that survives execution is a 500, never a
  claimed removal;
* **session/bootstrap byte-identity** is retained after sells.
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
import sell_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed fresh-player corpus is keyed "1".."40" and the sell fixture
# targets slot 20 (the first Turret I; slot 11 is the second and the move
# fixture's row).  A sell is *destructive*, so every test that needs a
# successful removal takes its own row: the module shares one disposable
# corpus, and distinct rows keep the suite order-independent no matter how
# the loader orders the methods.
FIXTURE_INDEX = 20
FIXTURE_ITEM_ID = 22
FIXTURE_ANCHOR = (41, 48)
MOVE_FIXTURE_INDEX = 11  # the move fixture's row: a second Turret I
# One dedicated row per destructive test, so no two of them collide.
CONTRACT_PROOF_INDEX = 40  # the removal-proof stub actually removes this row
CONTRACT_UNREPORTABLE_INDEX = 39  # the 500-before-execution test removes none
CONTRACT_PERSISTENCE_INDEX = 19
DOUBLE_SELL_INDEX = 24
EXTRA_KEYS_INDEX = 25
SECOND_ROW_INDEX = 26
THIRD_ROW_INDEX = 27
# The reason that would route a row through push_dead_unit.  The endpoint
# accepts no reason, so it must be unreachable (design D3).
COMBAT_REASON = "KILL"


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
    # every sell execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a sell execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def sell(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/sell", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def map_items() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["items"]  # type: ignore[index]


def intent(index: int) -> Dict[str, Any]:
    return {"user_id": PID, "item_index": index}


def assert_only_removed(
    case: unittest.TestCase,
    before_items: Dict[str, Any],
    index: int,
) -> None:
    """Assert exactly the addressed row vanished and nothing else changed."""
    after_items = map_items()
    key = str(index)
    case.assertIn(key, before_items)
    case.assertNotIn(key, after_items)
    case.assertEqual(len(after_items), len(before_items) - 1)
    for other in before_items:
        if other == key:
            continue
        with case.subTest(key=other):
            case.assertEqual(after_items[other], before_items[other])


class SellDerivationTests(unittest.TestCase):
    """The observable effects of the derived legacy envelope."""

    def test_success_reports_legacy_result_the_pre_execution_row_and_resources(
        self,
    ) -> None:
        index = FIXTURE_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())
        before_row = list(before_items[str(index)])

        response = sell(intent(index))

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
                "removed",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # The legacy result: the command.php route returns exactly this
        # whenever command() returns without raising.
        self.assertEqual(payload["result"], "success")

        # The row as read *before* execution (design D5): the persisted save
        # no longer holds it, so this is the authoritative record of what the
        # client asked to remove.
        self.assertEqual(payload["removed"], before_row)
        self.assertEqual(len(payload["removed"]), 8)
        self.assertEqual(payload["removed"][0], FIXTURE_ITEM_ID)
        self.assertEqual(
            [payload["removed"][1], payload["removed"][2]], list(FIXTURE_ANCHOR)
        )
        self.assertEqual(payload["removed"][3:], before_row[3:])

        # Neutral price vector: no stored resource moves at all, so this
        # endpoint claims no refund (design D2).
        self.assertEqual(payload["resources"], before)
        self.assertEqual(
            set(payload["resources"]),
            {"xp", "gold", "wood", "oil", "steel", "cash", "mana"},
        )
        # Every value in the response is what actually landed on disk.
        self.assertEqual(corpus_save()["maps"][0]["gold"], payload["resources"]["gold"])
        self.assertEqual(corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"])
        self.assertEqual(corpus_save()["privateState"]["mana"], payload["resources"]["mana"])

        # The row is gone from the persisted save: the endpoint proved it.
        assert_only_removed(self, before_items, index)
        # Neither storage nor the purchase record nor the dead-unit pool moved.
        self.assertEqual(corpus_save()["maps"][0]["store"], {})
        self.assertEqual(corpus_save()["privateState"]["boughtUnits"], [])
        self.assertEqual(corpus_save()["privateState"]["deadHeroes"], {})

        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_selling_a_row_twice_is_a_structured_error_not_a_second_removal(self) -> None:
        index = DOUBLE_SELL_INDEX
        first = sell(intent(index))
        self.assertEqual(first.status_code, 200)
        before = copy.deepcopy(map_items())
        # A stale index after a prior removal: legacy would silently no-op and
        # persist, so the endpoint must fail closed instead.
        second = sell(intent(index))
        self.assertEqual(second.status_code, 404)
        body = second.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "unknown_item_index")
        self.assertEqual(map_items(), before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_two_rows_sell_independently(self) -> None:
        before_items = copy.deepcopy(map_items())
        first = sell(intent(SECOND_ROW_INDEX))
        self.assertEqual(first.status_code, 200)
        after_first = copy.deepcopy(map_items())
        second = sell(intent(THIRD_ROW_INDEX))
        self.assertEqual(second.status_code, 200)
        payload = second.get_json()
        self.assertEqual(payload["removed"], after_first[str(THIRD_ROW_INDEX)])
        self.assertEqual(
            payload["resources"], BOOT.resources(PID)  # type: ignore[union-attr]
        )
        self.assertNotIn(str(SECOND_ROW_INDEX), after_first)
        assert_only_removed(self, after_first, THIRD_ROW_INDEX)
        self.assertEqual(len(map_items()), len(before_items) - 2)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_selling_one_turret_leaves_the_other_turret_alone(self) -> None:
        """The two fixtures stay independently readable (design D10).

        The sell fixture targets slot 20 and the move fixture slot 11; both
        hold a Turret I, and a sell must address exactly the row the client
        named.
        """
        before_items = copy.deepcopy(map_items())
        self.assertEqual(
            before_items[str(FIXTURE_INDEX)], [22, 41, 48, 0, 0, [], {}, 1]
        )
        self.assertEqual(
            before_items[str(MOVE_FIXTURE_INDEX)], [22, 58, 48, 0, 0, [], {}, 1]
        )
        response = sell(intent(MOVE_FIXTURE_INDEX))
        self.assertEqual(response.status_code, 200)
        assert_only_removed(self, before_items, MOVE_FIXTURE_INDEX)
        # The sell fixture's row is untouched by this sale.
        self.assertEqual(
            map_items()[str(FIXTURE_INDEX)], [22, 41, 48, 0, 0, [], {}, 1]
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_client_supplied_reason_price_and_deltas_are_ignored(self) -> None:
        """Design D2/D3: nothing but the index enters the contract.

        In particular a client-supplied ``reason`` — including the combat
        ``KILL`` reason — is ignored, so ``push_dead_unit`` is unreachable
        through this surface and the dead-unit pool cannot be touched.
        """
        index = EXTRA_KEYS_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())

        response = sell(
            dict(
                intent(index),
                reason=COMBAT_REASON,
                resources_changed=[0, 999, 999, 999, 999, 999, 999, 999],
                resources={"cash": 999999},
                refund=500,
                price=[0, 0, 0, 0, 0, 0, 500, 0],
                result="hacked",
                removed=[0, 0, 0, 0, 0, [], {}, 0],
            )
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The server's own derivation wins; the extra keys are ignored.
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["removed"], before_items[str(index)])
        # The neutral vector: no refund, no mint, nothing changed.
        self.assertEqual(payload["resources"], before)
        assert_only_removed(self, before_items, index)
        self.assertEqual(corpus_save()["privateState"]["deadHeroes"], {})
        self.assertEqual(corpus_save()["playerInfo"]["cash"], before["cash"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_derived_envelope_is_the_sell_command(self) -> None:
        built = sell_envelope.build_envelope(item_index=FIXTURE_INDEX, ts=1700000000)
        self.assertEqual(built["commands"][0][1], "sell")
        self.assertEqual(built["commands"][0][2], [FIXTURE_INDEX, ""])
        self.assertEqual(built["commands"][0][3], [0] * 8)
        self.assertEqual(compat_service.sell_envelope, sell_envelope)

    def test_the_derived_reason_is_never_the_combat_reason(self) -> None:
        """The envelope the endpoint builds cannot route through KILL."""
        built = sell_envelope.build_envelope(item_index=FIXTURE_INDEX, ts=1700000000)
        self.assertNotEqual(built["commands"][0][2][1], COMBAT_REASON)
        self.assertEqual(sell_envelope.DEFAULT_REASON, "")


class SellFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation (D4)."""

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
                CLIENT.post("/v0/sell"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/sell", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/sell", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/sell", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {"item_index": FIXTURE_INDEX}
        self.assert_fail_closed(sell({}), 400, "missing_user_id")
        self.assert_fail_closed(
            sell({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            sell({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            sell({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(sell({"user_id": "ghost", **base}), 404, "unknown_user_id")

    def test_item_index_failures(self) -> None:
        self.assert_fail_closed(
            sell({"user_id": PID}), 400, "missing_item_index"
        )
        for bad in ("20", 20.0, True, None, [20]):
            with self.subTest(item_index=bad):
                self.assert_fail_closed(
                    sell({"user_id": PID, "item_index": bad}),
                    400,
                    "invalid_item_index",
                )

    def test_an_unknown_item_index_fails_closed(self) -> None:
        """Legacy would log an error, return early, and still persist.

        The endpoint answers a structured 404 instead, so a stale index can
        never be reported as a successful sale (design D4).
        """
        for index in (0, 41, 999999999, -1):
            with self.subTest(item_index=index):
                response = sell(intent(index))
                self.assert_fail_closed(response, 404, "unknown_item_index")
                self.assertIn(
                    str(index), response.get_json()["error"]["message"]
                )

    def test_an_unresolvable_index_removes_no_row(self) -> None:
        before = copy.deepcopy(map_items())
        response = sell(intent(41))
        self.assert_fail_closed(response, 404, "unknown_item_index")
        self.assertEqual(map_items(), before)


class SellContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_sells(self) -> None:
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

    def test_sells_never_touch_working_tree_saves(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        before_items = copy.deepcopy(map_items())
        response = sell(intent(CONTRACT_PERSISTENCE_INDEX))
        self.assertEqual(response.status_code, 200)
        # The corpus save shrank by a row; the working tree did not move.
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        assert_only_removed(self, before_items, CONTRACT_PERSISTENCE_INDEX)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_legacy_accessors_agree_with_the_map(self) -> None:
        self.assertTrue(BOOT.has_map_item(PID, MOVE_FIXTURE_INDEX))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 0))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, MOVE_FIXTURE_INDEX)  # type: ignore[union-attr]
        self.assertIsInstance(row, list)
        self.assertEqual(len(row), 8)  # type: ignore[arg-type]
        self.assertEqual(
            row, BOOT.map_items(PID)[str(MOVE_FIXTURE_INDEX)]  # type: ignore[union-attr]
        )
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]

    def test_a_row_the_legacy_dispatcher_kept_is_a_500_not_a_success(self) -> None:
        """The post-execution removal proof fails closed (design D5).

        Legacy ``sell`` on a missing row is a silent no-op, so a key that
        survives execution would otherwise be reported as a removal that
        never happened.  The stub makes the *proof* report the key as still
        present; the dispatcher still ran for real, so the corpus really did
        lose the row — the 500 is exactly the "never claim a removal you
        cannot prove" boundary.
        """
        index = CONTRACT_PROOF_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.has_map_item  # type: ignore[union-attr]
        BOOT.has_map_item = lambda user_id, key: True  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/sell", json=intent(index))
        finally:
            BOOT.has_map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("placement", body["error"]["message"])
        # The dispatcher ran for real, so the row really is gone even though
        # the service refused to claim the removal.
        self.assertNotIn(str(index), map_items())
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_the_service_cannot_report_is_a_500(self) -> None:
        """A non-list row fails closed before the dispatcher ever runs."""
        index = CONTRACT_UNREPORTABLE_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        BOOT.map_item = lambda user_id, key: "not a row"  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/sell", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn(str(index), map_items())
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class SellSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/sell")  # type: ignore[union-attr]
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
            unknown = CLIENT.get("/v0/sell/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index")
        self.assertEqual(compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_REASON, "invalid_reason")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")
        self.assertEqual(compat_service.ERROR_INVALID_PAYLOAD, "invalid_payload")

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
