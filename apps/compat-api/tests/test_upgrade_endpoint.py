#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/upgrade`` behavior tests (OpenSpec task 2.3).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection.  The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across upgrade
execution.

Every test snapshots the corpus map at its own start and asserts its
post-condition against that snapshot, so the suite is order-independent.
Mutating tests take dedicated rows, and every assertion about a
cumulative field (``privateState.boughtUnits``) is expressed as a delta
against the test's own snapshot rather than as an absolute value.

Covered:

* **derivations** — the target tier comes from the committed configuration's
  ``upgrades_to``, never from the client; the response carries the
  eight-field row exactly as it was read *before* execution (``removed``) and
  the eight-field row **re-read from the persisted save afterwards**
  (``upgraded``), the second at the derived target tier and the first row's
  cell, with legacy's fresh-row semantics reproduced rather than "fixed" (a
  new timestamp, ``store []``, and the click-to-build seed ``{"nc": 0}``);
  every other row is byte-identical and the placement count does not move.
* **the post-execution proof** — a key that vanished, a row holding a
  different item id, and a row at a different cell each fail closed with
  ``internal_error`` rather than reporting legacy's success.  The key-absent
  case is exactly the outcome the **reverse command order** produces, which
  the legacy server itself reports as a success, and that outcome is
  reproduced here by running the real reverse-order batch through the
  unchanged legacy dispatcher.
* **no upgrade path** — a placement whose item has no resolvable next tier
  answers ``no_upgrade_path`` (400) before the dispatcher runs, so it is never
  reduced to a bare sale.
* **neutral resources** — no resource moves, because both derived vectors are
  all zeros, so **no upgrade cost is claimed**; no client-supplied target
  tier, reason, coordinates, orientation, player, quantity, price, or resource
  delta is honored anywhere in the contract.
* **fail-closed paths** — every structurally unresolvable input in the spec
  (non-object body, missing/invalid/unknown save id, missing/invalid/unknown
  item index) returns its documented structured error with the corpus
  byte-unchanged and no row removed or rewritten.
* **session/bootstrap byte-identity** is retained after upgrades.
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
import upgrade_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed fresh-player corpus is keyed "1".."40".  The upgrade fixture
# targets slot 12 (a Wall I at (45,49)); the move and sell fixtures use slots
# 11 and 20 (Turret Is) and the store fixture slot 2 (the Tree decoration), so
# every committed fixture stays independently readable.  An upgrade *replaces*
# a row rather than removing it, so the mutating tests below take their own
# rows and never share one.
FIXTURE_INDEX = 12
FIXTURE_ITEM_ID = 23  # Wall I
FIXTURE_TARGET_ITEM_ID = 24  # Wall II
FIXTURE_ANCHOR = (45, 49)
SECOND_ROW_INDEX = 13  # Wall I at (44,49)
SECOND_ANCHOR = (44, 49)
THIRD_ROW_INDEX = 14  # Wall I at (43,49)
THIRD_ANCHOR = (43, 49)
FOURTH_ROW_INDEX = 15  # Wall I at (42,49)
FIFTH_ROW_INDEX = 17  # Wall I at (40,49)
NO_PATH_INDEX = 2  # the Tree decoration's slot: upgrades_to "-1" (store fixture row)
TREE_ITEM_ID = 905  # the Tree decoration's item id
THIRD_TIER_ITEM_ID = 25  # Wall III, one tier above Wall II
# The reason that would route a row through push_dead_unit.  The endpoint
# accepts no reason, so it must be unreachable (design D2).
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
    # The corpus is discarded, but the working tree must be untouched by every
    # upgrade execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("an upgrade execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def upgrade(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/upgrade", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def map_items() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["items"]  # type: ignore[index]


def bought_units() -> List[Any]:
    return list(corpus_save()["privateState"]["boughtUnits"])


def bought_after(before: List[Any], item: int) -> List[Any]:
    """Legacy's ``bought_unit_add`` rule (engine.py:86-89).

    The list appends the item **only when it is not already listed**, so an
    upgrade of a tier that was bought or upgraded elsewhere does not grow it
    again.  On the committed corpus, which starts empty, this is a plain
    ``[24]``; the rule is asserted here rather than assumed.
    """
    return list(before) if item in before else list(before) + [item]


def intent(index: int) -> Dict[str, Any]:
    return {"user_id": PID, "item_index": index}


def assert_only_replaced(
    case: unittest.TestCase,
    before_items: Dict[str, Any],
    index: int,
) -> None:
    """Assert exactly the addressed row was rewritten and nothing else moved."""
    after_items = map_items()
    key = str(index)
    case.assertIn(key, before_items)
    case.assertIn(key, after_items)
    # The key is reused: the count does not move at all.
    case.assertEqual(len(after_items), len(before_items))
    for other in before_items:
        if other == key:
            continue
        with case.subTest(key=other):
            case.assertEqual(after_items[other], before_items[other])


def _absent_after_execution(index: int):
    """A ``has_map_item`` stub: resolves before, absent after.

    The endpoint resolves the index once before executing and once after, so a
    two-call stub reproduces the *post-state* the reverse command order leaves
    behind (the key deleted) without touching the real legacy dispatcher.
    """
    original = BOOT.has_map_item  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str, key: int) -> bool:
        if key != index:
            return original(user_id, key)
        state["seen"] += 1
        return state["seen"] == 1

    return stub


def _row_rewritten_after_execution(index: int, transform):
    """A ``map_item`` stub that rewrites only the **post**-execution read.

    The endpoint reads the row once before execution (for ``removed`` and the
    derivation) and once after (for ``upgraded``).  Rewriting only the second
    read is what lets each half of the post-execution proof be exercised in
    isolation: the cell or the item id the real dispatcher actually wrote is
    replaced with a wrong one, so exactly one proof clause can fail.
    """
    original = BOOT.map_item  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str, key: int):
        row = original(user_id, key)
        if key != index or not isinstance(row, list):
            return row
        state["seen"] += 1
        return transform(list(row)) if state["seen"] > 1 else list(row)

    return stub


def _wrong_cell(row: List[Any]) -> List[Any]:
    return [row[0], 0, 0] + row[3:]


def _wrong_tier(row: List[Any]) -> List[Any]:
    # The real dispatcher wrote the derived target tier; shift it so the
    # item-id clause of the proof is the only one that can fail.
    return [row[0] + 1] + row[1:]


def next_tier(item_id: int) -> Optional[int]:
    """The endpoint's own resolution rule, read from the live config."""
    return BOOT.item_upgrade_to(item_id)  # type: ignore[union-attr]


class UpgradeDerivationTests(unittest.TestCase):
    """The observable effects of the derived two-command legacy envelope."""

    def test_success_reports_legacy_result_both_rows_and_resources(self) -> None:
        index = FIXTURE_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())
        before_row = list(before_items[str(index)])
        before_bought = bought_units()

        response = upgrade(intent(index))

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
                "upgraded",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # The legacy result: command.php returns exactly this whenever
        # command() returns without raising — which, per the reverse-order
        # negative oracle, is not itself proof of an upgrade.
        self.assertEqual(payload["result"], "success")

        # The row as read *before* execution.
        self.assertEqual(payload["removed"], before_row)
        self.assertEqual(len(payload["removed"]), 8)
        self.assertEqual(
            [payload["removed"][1], payload["removed"][2]], list(FIXTURE_ANCHOR)
        )

        # The row re-read from the persisted save *after* execution: the
        # derived target tier at the same cell, with legacy's fresh-row
        # semantics reproduced rather than "fixed" (design D5).  The target is
        # the configuration's own resolution of the row's current item, so the
        # assertion holds however many times the row was upgraded before.
        upgraded = payload["upgraded"]
        self.assertEqual(len(upgraded), 8)
        self.assertEqual(upgraded[0], next_tier(int(before_row[0])))
        self.assertEqual([upgraded[1], upgraded[2]], list(FIXTURE_ANCHOR))
        self.assertEqual(upgraded[4], before_row[4])  # orientation
        self.assertEqual(upgraded[5], [])  # store
        self.assertEqual(upgraded[6], {"nc": 0})  # the construction seed
        self.assertEqual(upgraded[7], before_row[7])  # player team
        # The replaced row's timestamp is NOT carried over: the buy half
        # stamps the current time.  Compared structurally, never by value.
        self.assertIsInstance(upgraded[3], int)
        self.assertGreater(upgraded[3], 0)
        # The replaced row carried no attr; the fresh row is seeded.
        self.assertEqual(before_row[6], {})
        self.assertNotEqual(upgraded[6], before_row[6])

        # The persisted row is exactly what the response reported.
        self.assertEqual(map_items()[str(index)], upgraded)

        # Neutral price vectors: no stored resource moves at all, so this
        # endpoint claims no upgrade cost (design D4).
        self.assertEqual(payload["resources"], before)
        self.assertEqual(
            set(payload["resources"]),
            {"xp", "gold", "wood", "oil", "steel", "cash", "mana"},
        )
        self.assertEqual(corpus_save()["maps"][0]["gold"], payload["resources"]["gold"])
        self.assertEqual(corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"])
        self.assertEqual(corpus_save()["privateState"]["mana"], payload["resources"]["mana"])

        # The purchase half records the new tier (legacy's bought_unit_add appends
        # only when the item is not already listed); nothing else moves.
        self.assertEqual(bought_units(), bought_after(before_bought, upgraded[0]))
        self.assertEqual(corpus_save()["maps"][0]["store"], {})
        self.assertEqual(corpus_save()["privateState"]["deadHeroes"], {})

        # The key is reused: exactly that one row was rewritten.
        assert_only_replaced(self, before_items, index)

        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_upgrading_the_same_row_twice_advances_it_one_more_tier(self) -> None:
        """A repeat is a real second upgrade, not a cumulative corruption."""
        index = FOURTH_ROW_INDEX
        start_row = list(map_items()[str(index)])
        first = upgrade(intent(index))
        self.assertEqual(first.status_code, 200)
        first_payload = first.get_json()
        self.assertEqual(
            first_payload["upgraded"][0], next_tier(int(start_row[0]))
        )
        before_bought = bought_units()
        before_second = copy.deepcopy(map_items())
        second = upgrade(intent(index))
        self.assertEqual(second.status_code, 200)
        payload = second.get_json()
        # The second call advances one more tier, in place.
        self.assertEqual(payload["removed"][0], first_payload["upgraded"][0])
        self.assertEqual(
            payload["upgraded"][0], next_tier(int(first_payload["upgraded"][0]))
        )
        # The cell is reused: only the item id and the fresh row's fields move.
        self.assertEqual(payload["upgraded"][1:3], payload["removed"][1:3])
        assert_only_replaced(self, before_second, index)
        self.assertEqual(
            bought_units(),
            bought_after(bought_after(before_bought, first_payload["upgraded"][0]),
                         payload["upgraded"][0]),
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_two_rows_upgrade_independently(self) -> None:
        before_items = copy.deepcopy(map_items())
        first = upgrade(intent(SECOND_ROW_INDEX))
        self.assertEqual(first.status_code, 200)
        after_first = copy.deepcopy(map_items())
        second = upgrade(intent(THIRD_ROW_INDEX))
        self.assertEqual(second.status_code, 200)
        payload = second.get_json()
        self.assertEqual(payload["removed"], after_first[str(THIRD_ROW_INDEX)])
        self.assertEqual(
            payload["resources"], BOOT.resources(PID)  # type: ignore[union-attr]
        )
        # Each row keeps its own cell: the buy half reuses the row's anchor.
        self.assertEqual(
            [payload["upgraded"][1], payload["upgraded"][2]], list(THIRD_ANCHOR)
        )
        self.assertNotEqual(after_first[str(SECOND_ROW_INDEX)][0], FIXTURE_ITEM_ID)
        # The placement count never moves: the pair reuses keys.
        self.assertEqual(len(map_items()), len(before_items))
        assert_only_replaced(self, after_first, THIRD_ROW_INDEX)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_upgrading_one_wall_leaves_the_other_fixtures_rows_alone(self) -> None:
        """The fixtures stay independently readable (design D10).

        The upgrade fixture targets slot 12 while the move/sell/store fixtures
        use slots 11, 20, and 2; an upgrade must address exactly the row the
        client named.  The other three rows are never upgraded by this suite,
        so they stay at the committed seed's values.
        """
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        before_items = copy.deepcopy(map_items())
        for other in ("11", "20", "2"):
            with self.subTest(key=other):
                self.assertEqual(before_items[other], seed_items[other])
        start_row = list(before_items[str(FIXTURE_INDEX)])
        response = upgrade(intent(FIXTURE_INDEX))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["removed"], start_row)
        self.assertEqual(payload["upgraded"][0], next_tier(int(start_row[0])))
        self.assertEqual(
            [payload["upgraded"][1], payload["upgraded"][2]],
            [start_row[1], start_row[2]],
        )
        assert_only_replaced(self, before_items, FIXTURE_INDEX)
        self.assertEqual(map_items()["11"], seed_items["11"])
        self.assertEqual(map_items()["20"], seed_items["20"])
        self.assertEqual(map_items()["2"], seed_items["2"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_client_supplied_tier_reason_cell_and_deltas_are_ignored(self) -> None:
        """Design D2/D4: nothing but the index enters the contract.

        In particular a client-supplied ``target_item_id`` cannot pick the
        tier and a client-supplied ``reason`` — including the combat ``KILL``
        reason — is ignored, so ``push_dead_unit`` is unreachable through this
        surface and the dead-unit pool cannot be touched.
        """
        index = SECOND_ROW_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())

        response = upgrade(
            dict(
                intent(index),
                target_item_id=1,
                item_id=1,
                reason=COMBAT_REASON,
                buy_reason="hacked",
                x=0,
                y=0,
                to_cell=[99, 99],
                orientation=7,
                player=0,
                unknown=42,
                resources_changed=[0, 999, 999, 999, 999, 999, 999, 999],
                resources={"cash": 999999},
                price=[0, 0, 0, 0, 0, 0, 500, 0],
                result="hacked",
                removed=[0, 0, 0, 0, 0, [], {}, 0],
                upgraded=[0, 0, 0, 0, 0, [], {}, 0],
            )
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The server's own derivation wins; the extra keys are ignored.
        self.assertEqual(payload["result"], "success")
        self.assertEqual(payload["removed"], before_items[str(index)])
        self.assertEqual(
            payload["upgraded"][0], next_tier(int(before_items[str(index)][0]))
        )
        # The row's own cell, orientation, and player team, not the client's.
        self.assertEqual(
            [payload["upgraded"][1], payload["upgraded"][2]], list(SECOND_ANCHOR)
        )
        self.assertEqual(payload["upgraded"][4], before_items[str(index)][4])
        self.assertEqual(payload["upgraded"][7], before_items[str(index)][7])
        # The neutral vectors: no mint, nothing changed.
        self.assertEqual(payload["resources"], before)
        assert_only_replaced(self, before_items, index)
        self.assertEqual(corpus_save()["privateState"]["deadHeroes"], {})
        self.assertEqual(corpus_save()["playerInfo"]["cash"], before["cash"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_bought_units_list_follows_legacys_deduplicating_append(self) -> None:
        """engine.bought_unit_add appends only a not-yet-listed item.

        The captured fixture records the corpus's empty list gaining the target
        tier, which both rules produce; this test pins the actual rule so a
        second upgrade to an already-listed tier is not expected to grow the
        list again.
        """
        index = FOURTH_ROW_INDEX
        before = bought_units()
        response = upgrade(intent(index))
        self.assertEqual(response.status_code, 200)
        target = response.get_json()["upgraded"][0]
        self.assertEqual(bought_units(), bought_after(before, target))
        self.assertEqual(bought_after([24], 24), [24])
        self.assertEqual(bought_after([24], 25), [24, 25])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_derived_envelope_is_the_two_documented_commands(self) -> None:
        built = upgrade_envelope.build_envelope(
            item_index=FIXTURE_INDEX,
            target_item_id=FIXTURE_TARGET_ITEM_ID,
            x=FIXTURE_ANCHOR[0],
            y=FIXTURE_ANCHOR[1],
            player=1,
            orientation=0,
            ts=1700000000,
        )
        self.assertEqual(len(built["commands"]), 2)
        self.assertEqual(built["commands"][0][1], "sell")
        self.assertEqual(built["commands"][0][2], [FIXTURE_INDEX, "UPGR"])
        self.assertEqual(built["commands"][1][1], "buy")
        self.assertEqual(
            built["commands"][1][2],
            [FIXTURE_INDEX, FIXTURE_TARGET_ITEM_ID, 45, 49, 1, 0, 0, ""],
        )
        self.assertEqual(built["commands"][0][3], [0] * 8)
        self.assertEqual(built["commands"][1][3], [0] * 8)
        self.assertIs(compat_service.upgrade_envelope, upgrade_envelope)

    def test_the_derived_reason_is_never_the_combat_reason(self) -> None:
        """The envelope the endpoint builds cannot route through KILL."""
        built = upgrade_envelope.build_envelope(
            item_index=FIXTURE_INDEX,
            target_item_id=FIXTURE_TARGET_ITEM_ID,
            x=FIXTURE_ANCHOR[0],
            y=FIXTURE_ANCHOR[1],
            player=1,
            orientation=0,
            ts=1700000000,
        )
        self.assertNotEqual(built["commands"][0][2][1], COMBAT_REASON)
        self.assertEqual(upgrade_envelope.UPGRADE_REASON, "UPGR")


class ItemUpgradeToTests(unittest.TestCase):
    """The committed-configuration resolution rule (design D2/D3)."""

    def test_a_resolving_tier_is_returned_as_an_int(self) -> None:
        self.assertEqual(BOOT.item_upgrade_to(FIXTURE_ITEM_ID), FIXTURE_TARGET_ITEM_ID)  # type: ignore[union-attr]
        self.assertIsInstance(BOOT.item_upgrade_to(FIXTURE_ITEM_ID), int)  # type: ignore[union-attr]

    def test_the_minus_one_sentinel_means_no_path(self) -> None:
        # The Tree decoration (item 905) records upgrades_to "-1"; the store
        # fixture's row holds it, so this is the same "no path" case the
        # endpoint answers with no_upgrade_path.
        self.assertIsNone(BOOT.item_upgrade_to(TREE_ITEM_ID))  # type: ignore[union-attr]

    def test_an_id_that_resolves_to_nothing_means_no_path(self) -> None:
        self.assertIsNone(BOOT.item_upgrade_to(999999))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.item_upgrade_to(-1))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.item_upgrade_to("not an item"))  # type: ignore[union-attr]

    def test_both_documented_sentinels_mean_no_path(self) -> None:
        """The normalized package's RELATION_NONE is exactly (-1, 0)."""
        self.assertEqual(compat_legacy.RELATION_NONE, (-1, 0))
        terminal = [
            entry
            for entry in BOOT.config()["items"]  # type: ignore[union-attr]
            if str(entry.get("upgrades_to")) in ("-1", "0")
        ]
        self.assertTrue(terminal)
        # Every terminal item resolves to no path through the accessor.
        for entry in terminal[:5]:
            with self.subTest(item=entry["id"]):
                self.assertIsNone(
                    BOOT.item_upgrade_to(int(entry["id"]))  # type: ignore[union-attr]
                )


class NoUpgradePathTests(unittest.TestCase):
    """A building that cannot be upgraded is never a bare sale (D3)."""

    def setUp(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.before_store = copy.deepcopy(BOOT.map_store(PID))  # type: ignore[union-attr]
        self.before_bought = bought_units()

    def test_a_placement_with_no_next_tier_fails_closed(self) -> None:
        self.assertEqual(self.before_items[str(NO_PATH_INDEX)][0], 905)
        response = upgrade(intent(NO_PATH_INDEX))
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "no_upgrade_path")
        self.assertIn("905", body["error"]["message"])
        # Never a partial payload.
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(set(body["error"]), {"code", "message"})
        # The dispatcher never ran: the corpus is untouched and no sale
        # happened.
        self.assertEqual(harness.save_hashes(CORPUS), self.before_hashes)  # type: ignore[arg-type]
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), self.before_store)  # type: ignore[union-attr]
        self.assertIn(str(NO_PATH_INDEX), map_items())
        self.assertEqual(bought_units(), self.before_bought)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_error_constant_and_code_are_the_documented_ones(self) -> None:
        self.assertEqual(compat_service.ERROR_NO_UPGRADE_PATH, "no_upgrade_path")


class UpgradeFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation (D3/D7)."""

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
                CLIENT.post("/v0/upgrade"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/upgrade", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/upgrade", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/upgrade", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {"item_index": FIXTURE_INDEX}
        self.assert_fail_closed(upgrade({}), 400, "missing_user_id")
        self.assert_fail_closed(
            upgrade({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            upgrade({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            upgrade({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(upgrade({"user_id": "ghost", **base}), 404, "unknown_user_id")

    def test_item_index_failures(self) -> None:
        self.assert_fail_closed(
            upgrade({"user_id": PID}), 400, "missing_item_index"
        )
        for bad in ("12", 12.0, True, None, [12]):
            with self.subTest(item_index=bad):
                self.assert_fail_closed(
                    upgrade({"user_id": PID, "item_index": bad}),
                    400,
                    "invalid_item_index",
                )

    def test_an_unknown_item_index_fails_closed(self) -> None:
        """Legacy would log an error, return early, and still persist.

        The endpoint answers a structured 404 instead, so a stale index can
        never be reported as a successful upgrade (design D3).
        """
        for index in (0, 41, 999999999, -1):
            with self.subTest(item_index=index):
                response = upgrade(intent(index))
                self.assert_fail_closed(response, 404, "unknown_item_index")
                self.assertIn(
                    str(index), response.get_json()["error"]["message"]
                )

    def test_an_unresolvable_index_rewrites_no_row(self) -> None:
        before = copy.deepcopy(map_items())
        response = upgrade(intent(41))
        self.assert_fail_closed(response, 404, "unknown_item_index")
        self.assertEqual(map_items(), before)


class UpgradeContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_upgrades(self) -> None:
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

    def test_upgrades_never_touch_working_tree_saves(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        before_items = copy.deepcopy(map_items())
        response = upgrade(intent(SECOND_ROW_INDEX))
        self.assertEqual(response.status_code, 200)
        # The corpus save changed; the working tree did not move.
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        assert_only_replaced(self, before_items, SECOND_ROW_INDEX)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_legacy_accessors_agree_with_the_map(self) -> None:
        self.assertTrue(BOOT.has_map_item(PID, SECOND_ROW_INDEX))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 0))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, SECOND_ROW_INDEX)  # type: ignore[union-attr]
        self.assertIsInstance(row, list)
        self.assertEqual(len(row), 8)  # type: ignore[arg-type]
        self.assertEqual(
            row, BOOT.map_items(PID)[str(SECOND_ROW_INDEX)]  # type: ignore[union-attr]
        )
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]

    def test_a_key_the_legacy_dispatcher_destroyed_is_a_500_not_a_success(self) -> None:
        """The post-execution proof catches the reverse-order outcome (D3).

        The stub makes the proof observe the key as *absent* while the real
        dispatcher runs, which is precisely the state the **reverse command
        order** leaves behind — a batch legacy itself answers
        ``{"result":"success"}`` for.  The endpoint must refuse to report it.
        """
        index = FOURTH_ROW_INDEX
        start_row = list(map_items()[str(index)])
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.has_map_item  # type: ignore[union-attr]
        BOOT.has_map_item = _absent_after_execution(index)  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/upgrade", json=intent(index))
        finally:
            BOOT.has_map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("keep the placement entry", body["error"]["message"])
        # The dispatcher ran for real, so the row really was upgraded even
        # though the service refused to claim it.
        self.assertEqual(map_items()[str(index)][0], next_tier(int(start_row[0])))
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_holding_a_different_tier_is_a_500(self) -> None:
        """The proof's item-id half: a wrong tier is never reported."""
        index = FIFTH_ROW_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        BOOT.map_item = _row_rewritten_after_execution(index, _wrong_tier)  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/upgrade", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("target tier", body["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_that_moved_to_another_cell_is_a_500(self) -> None:
        """The proof's cell half: a relocated row is never reported."""
        index = FIFTH_ROW_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        BOOT.map_item = _row_rewritten_after_execution(index, _wrong_cell)  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/upgrade", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("pre-execution cell", body["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_the_service_cannot_report_is_a_500_before_execution(self) -> None:
        """A non-list row fails closed before the dispatcher ever runs."""
        index = FIFTH_ROW_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        BOOT.map_item = lambda user_id, key: "not a row"  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/upgrade", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        # Nothing was sold and nothing was bought.
        self.assertIn(int(map_items()[str(index)][0]), (23, 24, 25))
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_legacy_execution_raising_is_a_500(self) -> None:
        """A dispatcher failure after validation passed is a structured 500."""
        index = FIFTH_ROW_INDEX
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.execute_commands  # type: ignore[union-attr]
        before = copy.deepcopy(map_items())

        def explode(user_id, envelope):
            raise RuntimeError("legacy blew up")

        BOOT.execute_commands = explode  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/upgrade", json=intent(index))
        finally:
            BOOT.execute_commands = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("RuntimeError", body["error"]["message"])
        self.assertEqual(map_items(), before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class ReverseOrderOracleTests(unittest.TestCase):
    """The negative oracle, re-derived offline against real legacy code.

    Design D1/D3: the reverse batch also answers ``{"result":"success"}`` and
    leaves the key **absent** (40 -> 39).  That is reproduced here by running
    the reversed pair through the *unchanged* legacy ``command()`` dispatcher
    in a disposable corpus — no server, no network — and it is exactly the
    post-state the endpoint's three-part proof rejects.
    """

    def test_the_reverse_order_destroys_the_row_and_legacy_still_succeeds(self) -> None:
        corpus = harness.build_test_corpus()
        try:
            boot = compat_legacy.initialize(corpus)
            index = FIXTURE_INDEX
            before_items = copy.deepcopy(boot.map_items(PID))
            # The established pair, reversed.
            envelope = upgrade_envelope.build_envelope(
                item_index=index,
                target_item_id=FIXTURE_TARGET_ITEM_ID,
                x=FIXTURE_ANCHOR[0],
                y=FIXTURE_ANCHOR[1],
                player=1,
                orientation=0,
                ts=1700000000,
            )
            envelope["commands"].reverse()
            self.assertEqual(
                [entry[1] for entry in envelope["commands"]], ["buy", "sell"]
            )

            # command.php answers {"result": "success"} whenever command()
            # returns without raising, so reaching here IS that success.
            boot.execute_commands(PID, envelope)

            # …and yet the building is gone, not upgraded.
            after = harness.read_seeded_save(corpus)
            after_items = after["maps"][0]["items"]
            self.assertNotIn(str(index), after_items)
            self.assertEqual(len(after_items), len(before_items) - 1)
            # The purchase half still ran, so the bought-units list gained the
            # target tier even though the building was destroyed.
            self.assertIn(FIXTURE_TARGET_ITEM_ID, after["privateState"]["boughtUnits"])
        finally:
            os.chdir(ORIGINAL_CWD)
            harness.remove_corpus(corpus)
            # Re-initialize over this module's own corpus: legacy's session
            # state is a process singleton, so the second corpus's load must be
            # undone for the remaining tests to see their own corpus.
            compat_legacy.initialize(CORPUS)

    def test_the_endpoint_proof_rejects_exactly_that_outcome(self) -> None:
        """A batch that leaves the key absent can never be a 200 upgrade."""
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.has_map_item  # type: ignore[union-attr]
        BOOT.has_map_item = _absent_after_execution(THIRD_ROW_INDEX)  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post(
                    "/v0/upgrade", json=intent(THIRD_ROW_INDEX)
                )
        finally:
            BOOT.has_map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertFalse(body["ok"])
        # Not a success and not a partial payload.
        self.assertNotIn("upgraded", body)
        self.assertNotIn("result", body)
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class UpgradeSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/upgrade")  # type: ignore[union-attr]
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
            unknown = CLIENT.get("/v0/upgrade/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index")
        self.assertEqual(compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index")
        self.assertEqual(compat_service.ERROR_NO_UPGRADE_PATH, "no_upgrade_path")
        self.assertEqual(compat_service.ERROR_INVALID_PAYLOAD, "invalid_payload")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
