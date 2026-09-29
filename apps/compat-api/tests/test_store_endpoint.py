#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/store`` behavior tests (OpenSpec task 2.2).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection. The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across store
execution.

Every test snapshots the corpus map and storage at its own start and asserts
its post-condition against that snapshot, so the suite is order-independent.

Covered, per task 2.2:

* **the two-sided superset** — the response reports the eight-field row as it
  was read *before* execution (design D5) *and* the full post-execution
  storage mapping, so the client performs no arithmetic for pre-existing
  contents, *and* the current resources;
* **both post-execution proofs** — a row that survives execution and a
  storage entry that never landed are each a 500, never a claimed move
  (including stubbed survivors that must fail closed);
* **the ``add_store_item`` semantics** — an absent key is created with
  quantity 1 and an existing one is incremented by exactly 1;
* **the branch's non-write** — ``privateState.boughtUnits`` stays ``[]``
  (unlike ``buy`` / ``place_stored_item`` / ``buy_stored_item_cash``, this
  branch never calls ``bought_unit_add``);
* **neutral resources** — no resource moves, because the derived vector is
  all zeros, so **no storing cost is claimed** and **no capacity rule is
  claimed**; no client-supplied quantity, price, or resource delta is honored
  anywhere in the contract;
* **fail-closed paths** — every structurally unresolvable input in the spec
  (non-object body, missing/invalid/unknown save id, missing/invalid/unknown
  item index) returns its documented structured error with the corpus
  byte-unchanged and nothing stored or removed;
* **session/bootstrap byte-identity** is retained after stores.
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
import store_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed fresh-player corpus is keyed "1".."40" with an **empty**
# storage, and the store fixture targets slot 2 (the Tree decoration, item
# 905; slots 11 and 20 are the move and sell fixtures' Turret I rows).  A
# store is *destructive*, so every test that needs a successful move takes its
# own row: the module shares one disposable corpus, and distinct rows keep the
# suite order-independent no matter how the loader orders the methods.
FIXTURE_INDEX = 2
FIXTURE_ITEM_ID = 905
FIXTURE_ANCHOR = (53, 39)
FIXTURE_ROW = [905, 53, 39, 0, 0, [], {}, 1]
MOVE_FIXTURE_INDEX = 11  # the move fixture's row: a Turret I
SELL_FIXTURE_INDEX = 20  # the sell fixture's row: the other Turret I
TURRET_ITEM_ID = 22
# One dedicated row per destructive test, so no two of them collide.
CONTRACT_PROOF_INDEX = 40  # the removal-proof stub actually removes this row
CONTRACT_STORAGE_PROOF_INDEX = 38  # the storage-proof stub still removes it
CONTRACT_UNREPORTABLE_INDEX = 39  # the 500-before-execution test removes none
CONTRACT_NON_MAPPING_STORE_INDEX = 37  # a non-mapping storage after execution
CONTRACT_NO_ITEM_ID_INDEX = 36  # never reaches the dispatcher
CONTRACT_LEGACY_FAILURE_INDEX = 35  # never reaches the dispatcher
CONTRACT_PERSISTENCE_INDEX = 19
DOUBLE_STORE_INDEX = 24
EXTRA_KEYS_INDEX = 25
SECOND_ROW_INDEX = 26
THIRD_ROW_INDEX = 27
FOURTH_ROW_INDEX = 28
FIFTH_ROW_INDEX = 29


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
    # every store execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a store execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def store(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/store", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def map_items() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["items"]  # type: ignore[index]


def map_store() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["store"]  # type: ignore[index]


def intent(index: int) -> Dict[str, Any]:
    return {"user_id": PID, "item_index": index}


def assert_only_stored(
    case: unittest.TestCase,
    before_items: Dict[str, Any],
    before_store: Dict[str, Any],
    index: int,
    item_id: int,
) -> None:
    """Assert exactly the addressed row vanished and one storage entry grew."""
    after_items = map_items()
    after_store = map_store()
    key = str(index)
    case.assertIn(key, before_items)
    case.assertNotIn(key, after_items)
    case.assertEqual(len(after_items), len(before_items) - 1)
    for other in before_items:
        if other == key:
            continue
        with case.subTest(key=other):
            case.assertEqual(after_items[other], before_items[other])
    expected_store = dict(before_store)
    stored_key = str(item_id)
    expected_store[stored_key] = expected_store.get(stored_key, 0) + 1
    case.assertEqual(after_store, expected_store)


class StoreDerivationTests(unittest.TestCase):
    """The observable effects of the derived legacy envelope."""

    def test_success_reports_legacy_result_both_sides_and_resources(
        self,
    ) -> None:
        index = FIXTURE_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())
        before_store = copy.deepcopy(map_store())
        before_row = list(before_items[str(index)])

        response = store(intent(index))

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
                "store",
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
        # client asked to store.
        self.assertEqual(payload["removed"], before_row)
        self.assertEqual(len(payload["removed"]), 8)
        self.assertEqual(payload["removed"], FIXTURE_ROW)
        self.assertEqual(payload["removed"][0], FIXTURE_ITEM_ID)
        self.assertEqual(
            [payload["removed"][1], payload["removed"][2]], list(FIXTURE_ANCHOR)
        )
        self.assertEqual(payload["removed"][3:], before_row[3:])
        # It is a copy, not an alias of live state.
        payload["removed"][0] = 0

        # The full post-execution storage mapping (design D4): string keys to
        # integer quantities, returned whole so the client does no arithmetic.
        self.assertEqual(payload["store"], BOOT.map_store(PID))  # type: ignore[union-attr]
        self.assertEqual(payload["store"], map_store())
        self.assertIsInstance(payload["store"], dict)
        for stored_key, quantity in payload["store"].items():
            with self.subTest(stored_key=stored_key):
                self.assertIsInstance(stored_key, str)
                self.assertIsInstance(quantity, int)
        self.assertEqual(payload["store"][str(FIXTURE_ITEM_ID)], 1)

        # Neutral price vector: no stored resource moves at all, so this
        # endpoint claims no storing cost (design D2).
        self.assertEqual(payload["resources"], before)
        self.assertEqual(
            set(payload["resources"]),
            {"xp", "gold", "wood", "oil", "steel", "cash", "mana"},
        )
        # Every value in the response is what actually landed on disk.
        self.assertEqual(corpus_save()["maps"][0]["gold"], payload["resources"]["gold"])
        self.assertEqual(corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"])
        self.assertEqual(corpus_save()["privateState"]["mana"], payload["resources"]["mana"])

        # Both halves really landed, and only those.
        assert_only_stored(self, before_items, before_store, index, FIXTURE_ITEM_ID)
        # The branch deliberately records no purchase.
        self.assertEqual(corpus_save()["privateState"]["boughtUnits"], [])
        self.assertEqual(corpus_save()["privateState"]["deadHeroes"], {})

        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_storing_a_second_row_of_the_same_item_increments_the_entry(
        self,
    ) -> None:
        """engine.add_store_item adds exactly 1 to an existing entry."""
        before = copy.deepcopy(map_store())
        first = store(intent(SELL_FIXTURE_INDEX))
        self.assertEqual(first.status_code, 200)
        after_first = copy.deepcopy(map_store())
        self.assertEqual(
            after_first[str(TURRET_ITEM_ID)],
            before.get(str(TURRET_ITEM_ID), 0) + 1,
        )

        second = store(intent(MOVE_FIXTURE_INDEX))
        self.assertEqual(second.status_code, 200)
        after_second = copy.deepcopy(map_store())
        self.assertEqual(
            after_second[str(TURRET_ITEM_ID)],
            after_first[str(TURRET_ITEM_ID)] + 1,
        )
        self.assertEqual(
            second.get_json()["store"], after_second
        )
        self.assertEqual(second.get_json()["removed"], [22, 58, 48, 0, 0, [], {}, 1])
        self.assertNotIn(str(MOVE_FIXTURE_INDEX), map_items())
        self.assertNotIn(str(SELL_FIXTURE_INDEX), map_items())
        self.assertEqual(corpus_save()["privateState"]["boughtUnits"], [])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_response_store_mapping_is_a_superset_not_only_the_new_entry(
        self,
    ) -> None:
        """Entries other tests already stored travel back whole."""
        before_items = copy.deepcopy(map_items())
        before_store = copy.deepcopy(map_store())
        stored_key = str(int(before_items[str(SECOND_ROW_INDEX)][0]))
        response = store(intent(SECOND_ROW_INDEX))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        for key, quantity in before_store.items():
            with self.subTest(stored_key=key):
                self.assertIn(key, payload["store"])
                expected = quantity + 1 if key == stored_key else quantity
                self.assertEqual(payload["store"][key], expected)
        self.assertEqual(payload["store"], map_store())

    def test_storing_a_row_twice_is_a_structured_error_not_a_second_move(
        self,
    ) -> None:
        index = DOUBLE_STORE_INDEX
        first = store(intent(index))
        self.assertEqual(first.status_code, 200)
        before_items = copy.deepcopy(map_items())
        before_store = copy.deepcopy(map_store())
        # A stale index after a prior store: legacy would silently no-op and
        # persist, so the endpoint must fail closed instead.
        second = store(intent(index))
        self.assertEqual(second.status_code, 404)
        body = second.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "unknown_item_index")
        self.assertEqual(map_items(), before_items)
        self.assertEqual(map_store(), before_store)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_two_rows_store_independently(self) -> None:
        before_items = copy.deepcopy(map_items())
        before_store = copy.deepcopy(map_store())
        first = store(intent(FOURTH_ROW_INDEX))
        self.assertEqual(first.status_code, 200)
        after_first_store = copy.deepcopy(map_store())
        second = store(intent(FIFTH_ROW_INDEX))
        self.assertEqual(second.status_code, 200)
        payload = second.get_json()
        # The second response reports the row as it stood before *its* own
        # execution, which the first store left untouched.
        self.assertEqual(
            payload["removed"], before_items[str(FIFTH_ROW_INDEX)]
        )
        self.assertEqual(payload["store"], map_store())
        self.assertNotIn(str(FOURTH_ROW_INDEX), map_items())
        self.assertNotIn(str(FIFTH_ROW_INDEX), map_items())
        self.assertEqual(len(map_items()), len(before_items) - 2)
        self.assertEqual(
            map_store()[str(int(before_items[str(FOURTH_ROW_INDEX)][0]))],
            before_store.get(str(int(before_items[str(FOURTH_ROW_INDEX)][0])), 0) + 1,
        )
        self.assertIn(str(FIXTURE_ITEM_ID), after_first_store)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_client_supplied_quantity_price_and_deltas_are_ignored(self) -> None:
        """Design D2/D3: nothing but the index enters the contract.

        In particular a client-supplied ``quantity`` cannot store two copies:
        legacy's ``add_store_item`` is called without its third argument, so
        the increment is always exactly 1.
        """
        index = EXTRA_KEYS_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())
        before_store = copy.deepcopy(map_store())
        item_id = int(before_items[str(index)][0])

        response = store(
            dict(
                intent(index),
                quantity=99,
                resources_changed=[0, 999, 999, 999, 999, 999, 999, 999],
                resources={"cash": 999999},
                price=[0, 0, 0, 0, 0, 0, 500, 0],
                store={str(item_id): 99},
                result="hacked",
                removed=[0, 0, 0, 0, 0, [], {}, 0],
                capacity=0,
            )
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The server's own derivation wins; the extra keys are ignored.
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["removed"], before_items[str(index)])
        # Exactly one landed, whatever the client asked for.
        assert_only_stored(self, before_items, before_store, index, item_id)
        self.assertEqual(payload["store"][str(item_id)], before_store.get(str(item_id), 0) + 1)
        # The neutral vector: no cost, no mint, nothing changed.
        self.assertEqual(payload["resources"], before)
        self.assertEqual(corpus_save()["playerInfo"]["cash"], before["cash"])
        self.assertEqual(corpus_save()["privateState"]["boughtUnits"], [])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_derived_envelope_is_the_store_item_command(self) -> None:
        built = store_envelope.build_envelope(item_index=FIXTURE_INDEX, ts=1700000000)
        self.assertEqual(built["commands"][0][1], "store_item")
        self.assertEqual(built["commands"][0][2], [FIXTURE_INDEX])
        self.assertEqual(built["commands"][0][3], [0] * 8)
        self.assertEqual(compat_service.store_envelope, store_envelope)

    def test_the_branch_writes_no_bought_units_bookkeeping(self) -> None:
        """Unlike buy / place_stored_item / buy_stored_item_cash (design D2)."""
        built = store_envelope.build_envelope(item_index=FIXTURE_INDEX, ts=1700000000)
        self.assertEqual(len(built["commands"][0][2]), 1)
        self.assertEqual(corpus_save()["privateState"]["boughtUnits"], [])
        self.assertEqual(BOOT.save_document(PID)["privateState"]["boughtUnits"], [])  # type: ignore[union-attr]


class StoreFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation (D5)."""

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
                CLIENT.post("/v0/store"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/store", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/store", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/store", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {"item_index": FIXTURE_INDEX}
        self.assert_fail_closed(store({}), 400, "missing_user_id")
        self.assert_fail_closed(
            store({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            store({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            store({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(store({"user_id": "ghost", **base}), 404, "unknown_user_id")

    def test_item_index_failures(self) -> None:
        self.assert_fail_closed(
            store({"user_id": PID}), 400, "missing_item_index"
        )
        for bad in ("2", 2.0, True, None, [2]):
            with self.subTest(item_index=bad):
                self.assert_fail_closed(
                    store({"user_id": PID, "item_index": bad}),
                    400,
                    "invalid_item_index",
                )

    def test_an_unknown_item_index_fails_closed(self) -> None:
        """Legacy would log an error, return early, and still persist.

        The endpoint answers a structured 404 instead, so a stale index can
        never be reported as a successful store (design D5).
        """
        for index in (0, 41, 999999999, -1):
            with self.subTest(item_index=index):
                response = store(intent(index))
                self.assert_fail_closed(response, 404, "unknown_item_index")
                self.assertIn(
                    str(index), response.get_json()["error"]["message"]
                )

    def test_an_unresolvable_index_moves_nothing(self) -> None:
        before = copy.deepcopy(map_items())
        before_store = copy.deepcopy(map_store())
        response = store(intent(41))
        self.assert_fail_closed(response, 404, "unknown_item_index")
        self.assertEqual(map_items(), before)
        self.assertEqual(map_store(), before_store)


class StoreContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_stores(self) -> None:
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

    def test_stores_never_touch_working_tree_saves(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        before_items = copy.deepcopy(map_items())
        before_store = copy.deepcopy(map_store())
        response = store(intent(CONTRACT_PERSISTENCE_INDEX))
        self.assertEqual(response.status_code, 200)
        # The corpus save shrank by a row and gained a storage entry; the
        # working tree did not move.
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        item_id = int(before_items[str(CONTRACT_PERSISTENCE_INDEX)][0])
        assert_only_stored(
            self, before_items, before_store, CONTRACT_PERSISTENCE_INDEX, item_id
        )
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
        # map_store is the very mapping the persistence and the endpoint read.
        self.assertEqual(BOOT.map_store(PID), map_store())  # type: ignore[union-attr]

    def test_a_row_the_legacy_dispatcher_kept_is_a_500_not_a_success(self) -> None:
        """The first post-execution proof fails closed (design D5).

        Legacy ``store_item`` on a missing row is a silent no-op, so a key
        that survives execution would otherwise be reported as a removal that
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
                response = app.test_client().post("/v0/store", json=intent(index))
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

    def test_a_storage_entry_that_never_landed_is_a_500(self) -> None:
        """The second post-execution proof fails closed (design D4).

        The endpoint returns the storage mapping whole, so a mapping without
        the stored item's id would let the client render a storage the save
        does not show.  The stub reports an empty mapping; the dispatcher still
        ran for real and the row is really gone and really stored on disk.
        """
        index = CONTRACT_STORAGE_PROOF_INDEX
        item_id = int(BOOT.map_item(PID, index)[0])  # type: ignore[index,union-attr]
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_store  # type: ignore[union-attr]
        BOOT.map_store = lambda user_id: {}  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/store", json=intent(index))
        finally:
            BOOT.map_store = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("storage", body["error"]["message"])
        # Both halves really happened on disk; only the proof was stubbed.
        self.assertNotIn(str(index), map_items())
        self.assertEqual(map_store()[str(item_id)], 1)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_non_mapping_storage_is_a_500(self) -> None:
        """A storage the save cannot report fails closed after execution."""
        index = CONTRACT_NON_MAPPING_STORE_INDEX
        item_id = int(BOOT.map_item(PID, index)[0])  # type: ignore[index,union-attr]
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_store  # type: ignore[union-attr]
        BOOT.map_store = lambda user_id: "not a mapping"  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/store", json=intent(index))
        finally:
            BOOT.map_store = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("storage", body["error"]["message"])
        self.assertNotIn(str(index), map_items())
        self.assertEqual(map_store()[str(item_id)], 1)
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
                response = app.test_client().post("/v0/store", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("placement", body["error"]["message"])
        self.assertIn(str(index), map_items())
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_without_an_integer_item_id_is_a_500(self) -> None:
        """The storage proof needs the popped row's item id (design D4)."""
        index = CONTRACT_NO_ITEM_ID_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        BOOT.map_item = lambda user_id, key: ["not-an-int", 0, 0, 0, 0, [], {}, 1]  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/store", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("item id", body["error"]["message"])
        # Never reached the dispatcher: the row and the storage stand.
        self.assertIn(str(index), map_items())
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_legacy_execution_failure_is_a_500(self) -> None:
        """A dispatcher that raises after validation is server-side."""
        index = CONTRACT_LEGACY_FAILURE_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.execute_commands  # type: ignore[union-attr]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]

        def explode(user_id: str, envelope: Dict[str, object]) -> None:
            raise RuntimeError("legacy blew up")

        BOOT.execute_commands = explode  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/store", json=intent(index))
        finally:
            BOOT.execute_commands = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("execution failed", body["error"]["message"])
        # Nothing was popped: the row and the storage stand.
        self.assertIn(str(index), map_items())
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class StoreSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/store")  # type: ignore[union-attr]
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
            unknown = CLIENT.get("/v0/store/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index")
        self.assertEqual(compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")
        self.assertEqual(compat_service.ERROR_INVALID_PAYLOAD, "invalid_payload")
        self.assertEqual(compat_service.ERROR_INTERNAL, "internal_error")

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
