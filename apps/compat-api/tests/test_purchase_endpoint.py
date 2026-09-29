#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/purchase`` behavior tests (OpenSpec task 2.2).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection. The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across purchase
execution.

Covered, per task 2.2:

* **derivations** — the committed config's cash price lands in exactly the
  cash slot the response reports (the legacy ``max(…, 0)`` clamp included),
  the storage mapping is the persisted one read back from disk, and the
  response's ``resources`` mirror the persisted resource values;
* **clamping, not rejection** — an item priced above current cash still
  executes, with cash clamped to zero (legacy behavior; authoritative
  validation belongs to Server v1 / M13);
* **no client-supplied price, quantity, or resource delta** is honored;
* **fail-closed paths** — every structurally unresolvable input in the spec
  (non-object body, missing/invalid/unknown save id, missing/invalid/unknown
  item id, a config price that is not a cash price) returns its documented
  structured error with the corpus byte-unchanged and no storage entry
  written;
* **session/bootstrap byte-identity** is retained after purchases.
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
import purchase_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# Config facts pinned by the committed config (see the fixture README):
VICTORY_ARCH = 105  # Victory Arch — costs {"c":5}, min_level 1, in_store 1
SCULPTURE = 107  # Sculpture — costs {"c":7}: exceeds the fresh 5 cash
HOUSE_I = 1  # House I — costs {"w":30}: not a cash price at all
NO_COSTS_ITEM = 26  # Command Center — costs {"g":1000}: not a cash price


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
    # every purchase execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a purchase execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def purchase(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/purchase", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def store() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["store"]  # type: ignore[index]


class PurchaseDerivationTests(unittest.TestCase):
    """The observable effects of the derived legacy envelope."""

    def test_success_reports_legacy_result_storage_and_resources(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_store = copy.deepcopy(store())

        response = purchase({"user_id": PID, "item_id": VICTORY_ARCH})

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
                "store",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # The legacy result: the command.php route returns exactly this
        # whenever command() returns without raising.
        self.assertEqual(payload["result"], "success")

        # The full post-execution storage mapping, incremented by exactly one.
        expected_store = dict(before_store)
        expected_store[str(VICTORY_ARCH)] = expected_store.get(str(VICTORY_ARCH), 0) + 1
        self.assertEqual(payload["store"], expected_store)

        # Only cash moves, by exactly the derived price (fresh cash == 5).
        expected = dict(before)
        expected["cash"] = max(before["cash"] - 5, 0)
        self.assertEqual(payload["resources"], expected)
        self.assertEqual(payload["resources"]["cash"], 0)

        # The response is read back from what actually landed on disk.
        saved = corpus_save()
        self.assertEqual(saved["maps"][0]["store"], payload["store"])
        self.assertEqual(saved["playerInfo"]["cash"], payload["resources"]["cash"])
        self.assertEqual(saved["maps"][0]["gold"], payload["resources"]["gold"])
        # Legacy buy_stored_item_cash records the bought item id.
        self.assertIn(VICTORY_ARCH, saved["privateState"]["boughtUnits"])
        # ... and places nothing on the map.
        self.assertEqual(
            saved["maps"][0]["items"], harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        )

        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_second_purchase_increments_the_same_storage_entry(self) -> None:
        before_resources = BOOT.resources(PID)  # type: ignore[union-attr]
        before = copy.deepcopy(store())

        response = purchase({"user_id": PID, "item_id": VICTORY_ARCH})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        key = str(VICTORY_ARCH)
        self.assertEqual(payload["store"][key], before.get(key, 0) + 1)
        # bought_unit_add appends only when absent (engine.bought_unit_add).
        saved = corpus_save()
        self.assertEqual(
            [value for value in saved["privateState"]["boughtUnits"] if value == VICTORY_ARCH],
            [VICTORY_ARCH],
        )
        # The price always applies under the legacy max(..., 0) clamp.
        self.assertEqual(
            payload["resources"]["cash"], max(before_resources["cash"] - 5, 0)
        )

    def test_the_applied_delta_is_only_the_derived_cash_slot(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]

        response = purchase({"user_id": PID, "item_id": VICTORY_ARCH})

        self.assertEqual(response.status_code, 200)
        resources = response.get_json()["resources"]
        self.assertEqual(resources["cash"], max(before["cash"] - 5, 0))
        for key in ("xp", "gold", "wood", "oil", "steel", "mana"):
            self.assertEqual(resources[key], before[key])
        self.assertEqual(
            set(resources), {"xp", "gold", "wood", "oil", "steel", "cash", "mana"}
        )

    def test_insufficient_cash_clamps_at_zero_and_never_rejects(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        self.assertLess(before["cash"], 7)  # Sculpture costs 7 cash

        response = purchase({"user_id": PID, "item_id": SCULPTURE})

        # Clamp, never rejection: legacy apply_resources does max(..., 0).
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["resources"]["cash"], max(before["cash"] - 7, 0))
        self.assertEqual(payload["resources"]["cash"], 0)
        for key in ("xp", "gold", "wood", "oil", "steel", "mana"):
            self.assertEqual(payload["resources"][key], before[key])
        # The purchase still happened: storage gained the item.
        self.assertEqual(payload["store"][str(SCULPTURE)], 1)
        self.assertIn(SCULPTURE, corpus_save()["privateState"]["boughtUnits"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_client_supplied_price_quantity_and_deltas_are_ignored(self) -> None:
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        store_before = copy.deepcopy(store())

        response = purchase(
            {
                "user_id": PID,
                "item_id": VICTORY_ARCH,
                "quantity": 99,
                "price": 0,
                "resources_changed": [0, 999, 999, 999, 999, 999, 999, 999],
                "resources": {"cash": 999999},
                "result": "hacked",
                "store": {"1": 42},
            }
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The server's own derivation wins; the extra keys are ignored.
        self.assertEqual(payload["result"], "success")
        expected = dict(before)
        expected["cash"] = max(before["cash"] - 5, 0)
        self.assertEqual(payload["resources"], expected)
        # Exactly one unit, not 99; the client's own store claim is dropped.
        key = str(VICTORY_ARCH)
        self.assertEqual(payload["store"][key], store_before.get(key, 0) + 1)
        self.assertNotIn("1", payload["store"])


class PurchaseFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation (D3)."""

    def setUp(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_store = copy.deepcopy(store())
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]

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
        self.assertEqual(store(), self.before_store)
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_non_object_bodies(self) -> None:
        with harness.offline():
            responses = [
                CLIENT.post("/v0/purchase"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/purchase", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/purchase", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/purchase", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {"item_id": VICTORY_ARCH}
        self.assert_fail_closed(purchase({}), 400, "missing_user_id")
        self.assert_fail_closed(
            purchase({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            purchase({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            purchase({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(
            purchase({"user_id": "ghost", **base}), 404, "unknown_user_id"
        )

    def test_item_id_failures(self) -> None:
        self.assert_fail_closed(
            purchase({"user_id": PID}), 400, "missing_item_id"
        )
        for bad in ("105", 105.0, True, None, [105]):
            with self.subTest(item_id=bad):
                self.assert_fail_closed(
                    purchase({"user_id": PID, "item_id": bad}), 400, "invalid_item_id"
                )
        self.assert_fail_closed(
            purchase({"user_id": PID, "item_id": 999999999}), 404, "unknown_item_id"
        )

    def test_a_price_that_is_not_cash_fails_closed(self) -> None:
        for item_id, label in (
            (HOUSE_I, "wood-priced"),
            (NO_COSTS_ITEM, "gold-priced"),
        ):
            with self.subTest(item=item_id, label=label):
                response = purchase({"user_id": PID, "item_id": item_id})
                self.assert_fail_closed(response, 400, "costs_not_cash")
                self.assertIn("cash price", response.get_json()["error"]["message"])


class PurchaseContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_purchases(self) -> None:
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

    def test_purchases_never_touch_working_tree_saves(self) -> None:
        response = purchase({"user_id": PID, "item_id": VICTORY_ARCH})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_derived_envelope_is_the_purchase_command(self) -> None:
        """The endpoint's derivation is the one shared module's derivation."""
        vector = purchase_envelope.cash_cost_vector(
            BOOT.item_costs(SCULPTURE)  # type: ignore[union-attr]
        )
        self.assertEqual(vector, [0, 0, 0, 0, 0, 0, -7, 0])
        envelope = purchase_envelope.build_envelope(
            item_id=SCULPTURE, costs=BOOT.item_costs(SCULPTURE), ts=1700000000  # type: ignore[union-attr]
        )
        self.assertEqual(envelope["commands"][0][1], "buy_stored_item_cash")
        self.assertEqual(envelope["commands"][0][2], [SCULPTURE])


class PurchaseSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/purchase")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 405)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "method_not_allowed")

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(compat_service.ERROR_COSTS_NOT_CASH, "costs_not_cash")
        self.assertEqual(compat_service.ERROR_MISSING_ITEM_ID, "missing_item_id")
        self.assertEqual(compat_service.ERROR_INVALID_ITEM_ID, "invalid_item_id")
        self.assertEqual(compat_service.ERROR_UNKNOWN_ITEM_ID, "unknown_item_id")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
