#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/place_stored`` and ``/v0/sell_stored`` behavior
tests (OpenSpec task 3.2 of ``2026-10-03-stored-item-placement``).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so the suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; the
suite also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across every transaction.

Every test resets the storage, the ``boughtUnits`` ledger **and** the placements
to the committed corpus state first and asserts its post-condition against that
snapshot, so the suite is order-independent and no test can pass on a
neighbour's mutation.

The committed corpus supplies the scenario with **no fabricated player state**:
``maps[0]["store"] == {}``, ``privateState["boughtUnits"] == []``, and the map
holds exactly 40 placements under keys ``"1"``..``"40"``.  Item ``1085`` -- the
committed prize of collection 1 -- is a real committed unit, so the storage is
seeded here exactly the way the collection route's own fixture seeds it (one
``complete_collection``) rather than by writing a bag into the save by hand.

Covered:

* **a successful placement** - the derived map slot is the smallest absent
  positive integer (``41``), the row equals the derived row in all seven
  server-owned slots, exactly one stored unit is consumed, the ledger grows by
  exactly one appended id, every other placement is byte-identical, and all
  seven stored resources are unchanged.
* **the intent-only body** - a request carrying ``index``, ``slot``, ``map_key``,
  ``row``, ``attr``, ``player``, ``playerID``, ``quantity``, ``count``, ``price``,
  ``cost``, ``resources``, ``vector`` and ``timestamp`` changes nothing.
* **the four refusals**, each ``409`` with nothing executed: ``not_in_storage``
  for a committed placeable unit that was never stored, ``unknown_item_id`` for
  an id resolving to no committed definition, ``unresolvable_storage`` for a
  storage shape the projection cannot read, and ``slot_occupied`` for a derived
  slot an existing row already holds.
* **the two content refusals split on the record's own wording** - a missing
  committed row (``unknown_item_id``) is a different refusal from a row that
  carries neither derived field (``item_not_placeable``), and each is measured
  unreachable from the other on the committed content.
* **the post-execution proof** - a row that does not match the derivation, a
  placement at another slot, a ledger that grew wrongly, a sale that consumed
  the wrong count, a sale that rewrote a row, and **any** stored resource that
  moved, each fail closed with ``internal_error`` rather than reporting legacy's
  success.  Each stub lets the **real** dispatcher run and rewrites only the
  reads that happen **after** it returns, so no proof is tautological.
* **a sale** - exactly one stored unit is consumed, **no** placement is added,
  removed or rewritten, the ledger is untouched, and **no** resource is
  credited.
* **fail-closed structural paths** - every structurally invalid input returns
  its documented ``400``/``404`` with nothing executed.
* **the recorded absences** - neither route contains an occupancy check, a
  bounds check, a price, a refund or a capacity rule.
* **route placement** is pinned from this side too, because the two routes sit
  in the only interior gap no delivered guard's end marker reaches, and their
  three helpers had to be hoisted to module scope to keep the first route's
  slice holding exactly one function.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import textwrap
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import compat_test_harness as harness

import collection_envelope
import compat_legacy
import compat_service
import stored_placement_envelope as envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT: Any = None
APP: Any = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# Every committed figure is imported from the shared envelope module rather than
# restated here, and the collection pins from the collection module that owns
# the one-based index.
SEED_COLLECTION_ID = collection_envelope.COMMITTED_COLLECTION_ID
SEED_PRIZE_ID = envelope.COMMITTED_PRIZE_ID
SELL_COLLECTION_ID = envelope.COMMITTED_SELL_COLLECTION_ID
SELL_ITEM_ID = envelope.COMMITTED_SELL_ITEM_ID
PLACED_SLOT = envelope.COMMITTED_DERIVED_SLOT
PLACED_CELL = envelope.COMMITTED_CELL
UNSTORED_ITEM_ID = envelope.RECORDED_UNSTORED_ITEM_ID
UNKNOWN_ITEM_ID = envelope.RECORDED_UNKNOWN_ITEM_ID
OCCUPIED_SLOT = envelope.RECORDED_OCCUPIED_SLOT
OUT_OF_GRID_CELL = envelope.RECORDED_OUT_OF_GRID_CELL
RESOURCE_NAMES = ("cash", "gold", "mana", "oil", "steel", "wood", "xp")


def save_path() -> Path:
    return CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]


def persist(save: Dict[str, Any]) -> None:
    with open(save_path(), "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


# The committed placements, snapshotted ONCE before any test can mutate the
# corpus.  ``harness.read_seeded_save`` reads the LIVE corpus file, so calling it
# from ``committed_items`` would make the "committed" baseline accumulate every
# row an earlier test left behind -- the suite would then compare a placement
# against itself.  The snapshot is what makes the suite order-independent, and
# ``reset_state`` restores from it rather than from the live file.
COMMITTED_ITEMS: Dict[str, Any] = {}


def committed_items() -> Dict[str, Any]:
    return copy.deepcopy(COMMITTED_ITEMS)


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, APP, PID, WORKING_TREE_PRE
    global COMMITTED_ITEMS
    ORIGINAL_CWD = os.getcwd()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()
    COMMITTED_ITEMS = copy.deepcopy(
        harness.read_seeded_save(CORPUS)["maps"][0]["items"]  # type: ignore[index]
    )


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a stored-placement transaction wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def reset_state(store: Optional[Dict[str, Any]] = None,
                ledger: Optional[List[Any]] = None,
                items: Optional[Dict[str, Any]] = None) -> None:
    """Reset the storage, the ledger and the placements, in memory **and** on disk.

    ``place_stored_item`` appends to ``map["items"]`` in place and
    ``remove_store_item`` deletes from ``map["store"]`` in place, so all three
    live in the in-memory save the routes read *and* in the persisted corpus
    file.  Every representation is updated here, which is exactly the mechanism
    the legacy dispatcher itself uses to keep them in step.  The placements are
    ALWAYS reset -- to the committed 40 unless the caller installs its own -- so
    no test can inherit an earlier test's row.  It is a test-only, contained
    reset: never a claim about legacy behaviour and never a working-tree write.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["maps"][0]["store"] = copy.deepcopy({} if store is None else store)
    save["privateState"]["boughtUnits"] = copy.deepcopy([] if ledger is None else ledger)
    save["maps"][0]["items"] = committed_items() if items is None else copy.deepcopy(items)
    persist(save)


def seed_storage() -> None:
    """Put the committed collection prize into storage through the delivered route.

    This is deliberately NOT ``reset_state(store={...})``: the collection route
    is the project's only content-derived acquisition path, so seeding through it
    keeps the scenario free of any fabricated player state.
    """
    reset_state()
    with harness.offline():
        response = CLIENT.post(  # type: ignore[union-attr]
            "/v0/collection", json={"user_id": PID, "collection_id": SEED_COLLECTION_ID}
        )
    assert response.status_code == 200, response.get_json()
    assert store_now() == {str(SEED_PRIZE_ID): 1}, store_now()


class Result:
    """A captured response plus the app that produced it.

    The app must stay referenced while the test reads the response: Flask's test
    client resolves the JSON decoder through a weak reference to the app, so
    returning only the response and letting the app go out of scope turns every
    later ``get_json()`` into a ``ReferenceError``.
    """

    def __init__(self, app: Any, response: Any) -> None:
        self.app = app
        self.response = response

    @property
    def status_code(self) -> int:
        return int(self.response.status_code)

    def get_json(self) -> Any:
        return self.response.get_json()

    def code(self) -> str:
        return self.get_json()["error"]["code"]

    def message(self) -> str:
        return self.get_json()["error"]["message"]


def place_now(payload: Dict[str, Any]) -> Result:
    with harness.offline():
        response = CLIENT.post("/v0/place_stored", json=payload)  # type: ignore[union-attr]
    return Result(APP, response)


def sell_now(payload: Dict[str, Any]) -> Result:
    with harness.offline():
        response = CLIENT.post("/v0/sell_stored", json=payload)  # type: ignore[union-attr]
    return Result(APP, response)


def place_intent(item_id: Any = SEED_PRIZE_ID, x: Any = PLACED_CELL[0],
                 y: Any = PLACED_CELL[1], **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"user_id": PID, "item_id": item_id, "x": x, "y": y}
    payload.update(extra)
    return payload


def sell_intent(item_id: Any = SEED_PRIZE_ID, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"user_id": PID, "item_id": item_id}
    payload.update(extra)
    return payload


def store_now() -> Dict[str, Any]:
    return dict(BOOT.map_store(PID))  # type: ignore[union-attr]


def ledger_now() -> List[Any]:
    private = BOOT.save_document(PID).get("privateState")  # type: ignore[union-attr]
    return list(private.get("boughtUnits") or [])


def items_now() -> Dict[str, Any]:
    return dict(BOOT.map_items(PID))  # type: ignore[union-attr]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


@contextmanager
def patched_boot(name: str, value: Any) -> Iterator[None]:
    """Install an instance-level stub on ``BOOT`` and restore it EXACTLY.

    A plain ``setattr``/``restore`` pair would leave the *unbound* class function
    behind in the instance dictionary when the attribute was not an instance
    attribute to begin with, and every later call would then miss its ``self``
    argument.  This restores the instance dictionary itself.
    """
    had = name in BOOT.__dict__  # type: ignore[union-attr]
    original = BOOT.__dict__[name] if had else None  # type: ignore[union-attr,index]
    setattr(BOOT, name, value)  # type: ignore[union-attr]
    try:
        yield
    finally:
        if had:
            setattr(BOOT, name, original)  # type: ignore[union-attr]
        else:
            BOOT.__dict__.pop(name, None)  # type: ignore[union-attr]


@contextmanager
def after_dispatch(name: str, mutate: Callable[[Any], Any]) -> Iterator[None]:
    """Rewrite only the reads of ``name`` that happen AFTER the dispatcher ran.

    Both routes read the storage state once before ``execute_commands`` and once
    after.  A stub that rewrote **both** reads would let the proof compare a
    mutated value with itself, which is exactly the tautology these tests exist
    to foreclose; this one lets the real dispatcher run untouched and rewrites
    only what it could not have produced.
    """
    state = {"dispatched": False}
    original_dispatch = BOOT.execute_commands  # type: ignore[union-attr]
    original = getattr(BOOT, name)

    def dispatch(user_id: str, payload: Any) -> Any:
        result = original_dispatch(user_id, payload)
        state["dispatched"] = True
        return result

    def read(user_id: str) -> Any:
        value = original(user_id)
        return mutate(value) if state["dispatched"] else value

    with patched_boot("execute_commands", dispatch), patched_boot(name, read):
        yield


@contextmanager
def stripped_fields(item_id: int, fields: Tuple[str, ...]) -> Iterator[None]:
    """Remove ``fields`` from one committed row, then restore them EXACTLY.

    ``BOOT.config()`` hands back the **loaded** configuration object, so a
    removal here is process-wide.  The original values -- including absence --
    are therefore captured and restored in the ``finally``, which is what makes
    the two content-drift tests order-independent.
    """
    saved: List[Tuple[Dict[str, Any], str, Any, bool]] = []
    for entry in BOOT.config()["items"]:  # type: ignore[union-attr]
        if int(entry["id"]) == item_id:
            for name in fields:
                saved.append((entry, name, entry.get(name), name in entry))
                entry.pop(name, None)
    assert saved, "the committed row for %d was not found" % item_id
    try:
        yield
    finally:
        for entry, name, value, present in saved:
            if present:
                entry[name] = value
            else:
                entry.pop(name, None)


@contextmanager
def with_hidden_conflict(hidden: str) -> Iterator[None]:
    """Present the placements with ``hidden`` present but not iterable.

    ``slot_occupied`` is the named inverse of the slot derivation, so the two can
    only disagree on a corpus whose key view and occupancy view conflict.  The
    committed corpus holds keys ``"1"``..``"40"``, so hiding ``"41"`` before it
    is added would be a no-op: the key is added **first** and only then hidden,
    which is the only shape in which a derived slot can collide.
    """
    class Hiding(dict):  # type: ignore[type-arg]
        def __iter__(self):  # noqa: D105 - a mapping view, deliberately partial
            return iter([k for k in dict.__iter__(self) if k != hidden])

        def keys(self):  # noqa: D105
            return [k for k in dict.keys(self) if k != hidden]

        def __contains__(self, key):  # noqa: D105
            return dict.__contains__(self, key)

        def get(self, key, default=None):  # noqa: D105
            return dict.__getitem__(self, key) if dict.__contains__(self, key) else default

        def __len__(self):  # noqa: D105
            return len([k for k in dict.keys(self) if k != hidden])

    wrapper = Hiding(BOOT.map_items(PID))  # type: ignore[union-attr]
    assert str(hidden) in wrapper, "the hidden key must be added before it is hidden"
    with patched_boot("map_items", lambda user_id: wrapper if user_id == PID else {}):
        yield


def source() -> str:
    return Path(compat_service.__file__).read_text(encoding="utf-8")


def route_source(name: str) -> str:
    """The route's own source span, from its ``def`` to the next ``@app.`` line.

    This is the delivered markers' own convention, restated so a failure names
    the route rather than the helper under test.
    """
    text = source()
    start = text.index("def %s()" % name)
    markers: List[int] = []
    cursor = 0
    for line in text.split("\n"):
        if line.strip().startswith("@app."):
            markers.append(cursor)
        cursor += len(line) + 1
    following = [offset for offset in markers if offset > start]
    end = following[0] if following else text.index('app.config["COMPAT_LEGACY_CORPUS"]')
    return text[start:end]


def code_names(fragment: str) -> List[str]:
    tree = ast.parse(textwrap.dedent(fragment.lstrip("\n")))
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
    return names


# ---------------------------------------------------------------------------
# The accepted transaction
# ---------------------------------------------------------------------------


class SuccessfulPlacementTests(unittest.TestCase):
    """One placement against the seeded committed corpus."""

    def setUp(self) -> None:
        seed_storage()
        self.before_items = copy.deepcopy(items_now())
        self.before_resources = copy.deepcopy(resources_now())
        self.response = place_now(place_intent())
        self.assertEqual(self.response.status_code, 200, self.response.get_json())
        self.body = self.response.get_json()

    def test_the_result_is_the_legacy_success_string(self) -> None:
        self.assertEqual(self.body["result"], "success")

    def test_the_slot_is_the_derived_free_slot_not_a_client_value(self) -> None:
        self.assertEqual(self.body["placement"]["map_key"], PLACED_SLOT)
        self.assertEqual(self.body["placement"]["slot_rule"], envelope.SLOT_RULE)
        self.assertEqual(self.body["placement"]["command"], envelope.PLACE_COMMAND)
        self.assertIn(str(PLACED_SLOT), items_now())
        self.assertEqual(len(items_now()), len(self.before_items) + 1)

    def test_the_row_is_the_derived_row(self) -> None:
        row = items_now()[str(PLACED_SLOT)]
        self.assertEqual(len(row), envelope.ROW_SLOTS)
        self.assertEqual(row[envelope.ROW_SLOT_ITEM], SEED_PRIZE_ID)
        self.assertEqual((row[envelope.ROW_SLOT_X], row[envelope.ROW_SLOT_Y]), PLACED_CELL)
        self.assertEqual(row[envelope.ROW_SLOT_ORIENTATION], envelope.DERIVED_ORIENTATION)
        self.assertEqual(row[envelope.ROW_SLOT_STORE], envelope.DERIVED_GARRISON)
        self.assertEqual(row[envelope.ROW_SLOT_ATTR], {})
        self.assertEqual(row[envelope.ROW_SLOT_PLAYER], envelope.DERIVED_PLAYER_TEAM)
        self.assertIsInstance(row[envelope.ROW_SLOT_TIMESTAMP], int)

    def test_the_reported_row_equals_the_stored_row(self) -> None:
        self.assertEqual(self.body["row"]["slots"], items_now()[str(PLACED_SLOT)])
        self.assertEqual(self.body["row"]["attr"], {})
        self.assertEqual(self.body["row"]["player"], envelope.DERIVED_PLAYER_TEAM)

    def test_the_attribute_bag_is_derived_and_reported_verbatim(self) -> None:
        # A unit derives no bag at all, so the reported sources are empty and
        # `attr_derived_from` (the named inverse) reads the bag back to say so.
        self.assertEqual(self.body["row"]["attr"], {})
        self.assertEqual(self.body["row"]["attr_rule"], envelope.ATTR_RULE)
        self.assertEqual(self.body["row"]["attr_derived_from"], [])
        self.assertEqual(envelope.attr_derived_from({}), [])

    def test_exactly_one_stored_unit_is_consumed(self) -> None:
        self.assertEqual(self.body["quantity"]["consumed"], envelope.QUANTITY)
        self.assertEqual(self.body["quantity"]["count_before"], 1)
        self.assertEqual(self.body["quantity"]["count_after"], 0)
        self.assertEqual(self.body["quantity"]["rule"], envelope.QUANTITY_RULE)
        self.assertEqual(store_now(), {})

    def test_the_ledger_grows_by_exactly_one_appended_id(self) -> None:
        self.assertEqual(self.body["ledger_before"], [])
        self.assertEqual(self.body["ledger_after"], [SEED_PRIZE_ID])
        self.assertEqual(ledger_now(), [SEED_PRIZE_ID])
        self.assertEqual(self.body["ledger_rule"], envelope.LEDGER_RULE)

    def test_every_other_placement_is_byte_identical(self) -> None:
        after = items_now()
        for key, row in self.before_items.items():
            self.assertEqual(after[key], row, key)

    def test_no_stored_resource_moves(self) -> None:
        self.assertEqual(resources_now(), self.before_resources)
        self.assertEqual(sorted(self.body["resources"]), sorted(RESOURCE_NAMES))
        self.assertEqual(self.body["resources"], self.before_resources)

    def test_the_response_carries_the_recorded_absences(self) -> None:
        self.assertEqual(self.body["geometry"]["bounds_refused"], False)
        self.assertEqual(self.body["geometry"]["cell_occupancy_refused"], False)
        self.assertEqual(self.body["geometry"]["note"], envelope.GEOMETRY_GAP)
        self.assertEqual(len(self.body["refusals"]), envelope.REFUSAL_COUNT)

    def test_the_read_and_discarded_legacy_arguments_are_named(self) -> None:
        dismissed = self.body["refused"]["dismissed_arguments"]
        self.assertEqual(dismissed, [dict(entry) for entry in envelope.DISMISSED_ARGUMENTS])
        self.assertEqual([entry["name"] for entry in dismissed],
                         ["playerID", "unknown_autoactivable_bool", "unknown_imgIndex"])

    def test_every_ignored_body_key_is_named_in_the_envelope(self) -> None:
        # The keys the route ignores are pinned by the shared module, not by a
        # restatement here.
        self.assertEqual(sorted(envelope.PLACE_INTENT_REQUIRED_KEYS),
                         sorted(("user_id", "item_id", "x", "y")))
        self.assertEqual(sorted(envelope.SELL_INTENT_KEYS), sorted(("user_id", "item_id")))
        for key in ("index", "slot", "attr", "player", "quantity", "price"):
            self.assertIn(key, envelope.PLACE_INTENT_IGNORED_KEYS, key)


class SuccessfulSaleTests(unittest.TestCase):
    """One sale against the seeded committed corpus."""

    def setUp(self) -> None:
        seed_storage()
        self.before_items = copy.deepcopy(items_now())
        self.before_ledger = copy.deepcopy(ledger_now())
        self.before_resources = copy.deepcopy(resources_now())
        self.response = sell_now(sell_intent())
        self.assertEqual(self.response.status_code, 200, self.response.get_json())
        self.body = self.response.get_json()

    def test_the_result_is_the_legacy_success_string(self) -> None:
        self.assertEqual(self.body["result"], "success")

    def test_the_sale_names_the_legacy_command_and_no_price(self) -> None:
        self.assertEqual(self.body["sale"]["command"], envelope.SELL_COMMAND)

    def test_exactly_one_stored_unit_is_consumed(self) -> None:
        self.assertEqual(store_now(), {})
        self.assertEqual(self.body["quantity"]["count_before"], 1)
        self.assertEqual(self.body["quantity"]["count_after"], 0)
        self.assertEqual(self.body["quantity"]["consumed"], envelope.QUANTITY)

    def test_no_resource_is_credited(self) -> None:
        self.assertEqual(resources_now(), self.before_resources)
        self.assertEqual(self.body["sale"]["credited"], False)
        self.assertIsNone(self.body["sale"]["refund"])
        self.assertEqual(self.body["sale"]["note"], envelope.NO_REFUND_NOTE)

    def test_no_placement_is_added_removed_or_rewritten(self) -> None:
        self.assertEqual(items_now(), self.before_items)
        self.assertEqual(self.body["placements"]["before"], len(self.before_items))
        self.assertEqual(self.body["placements"]["after"], len(self.before_items))
        self.assertEqual(self.body["placements"]["untouched"], True)

    def test_the_ledger_is_untouched(self) -> None:
        self.assertEqual(ledger_now(), self.before_ledger)
        self.assertEqual(self.body["ledger_before"], self.before_ledger)
        self.assertEqual(self.body["ledger_after"], self.before_ledger)


# ---------------------------------------------------------------------------
# Intent-only bodies
# ---------------------------------------------------------------------------


class DismissedArgumentTests(unittest.TestCase):
    """Every client-supplied row, slot, team, count and price is ignored."""

    def setUp(self) -> None:
        seed_storage()

    def test_a_smuggled_row_slot_team_count_and_price_change_nothing(self) -> None:
        smuggled = {
            "index": 1,
            "slot": 1,
            "map_key": 1,
            "row": [999, 0, 0, 1, 0, [], {"nc": 9}, 3],
            "attr": {"nc": 9},
            "player": 3,
            "playerID": 3,
            "quantity": 5,
            "count": 5,
            "price": 999999,
            "cost": 999999,
            "resources": {"gold": 999999},
            "vector": [999999, 0, 0, 0, 0, 0, 0, 0],
            "timestamp": 1,
            "attributes": {"cp": 99},
        }
        response = place_now(place_intent(**smuggled))
        self.assertEqual(response.status_code, 200, response.get_json())
        row = items_now()[str(PLACED_SLOT)]
        self.assertEqual(row[envelope.ROW_SLOT_ATTR], {})
        self.assertEqual(row[envelope.ROW_SLOT_PLAYER], envelope.DERIVED_PLAYER_TEAM)
        self.assertEqual(row[envelope.ROW_SLOT_ITEM], SEED_PRIZE_ID)
        self.assertNotEqual(row[envelope.ROW_SLOT_TIMESTAMP], 1)
        # The committed row 1 (Command Center) is untouched by the smuggled index.
        self.assertEqual(items_now()["1"], committed_items()["1"])
        # Exactly one stored unit is consumed, not five.
        self.assertEqual(store_now(), {})
        self.assertEqual(response.get_json()["quantity"]["consumed"], envelope.QUANTITY)

    def test_a_client_supplied_slot_is_not_honoured(self) -> None:
        response = place_now(place_intent(slot=3, index=3, map_key=3))
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["placement"]["map_key"], PLACED_SLOT)
        self.assertNotIn("3", [
            key for key, row in items_now().items() if row[envelope.ROW_SLOT_ITEM] == SEED_PRIZE_ID
        ])
        self.assertEqual(len(items_now()), len(committed_items()) + 1)

    def test_a_client_supplied_sale_quantity_and_price_change_nothing(self) -> None:
        response = sell_now(sell_intent(quantity=5, price=999999, refund=999999))
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(store_now(), {})
        self.assertEqual(response.get_json()["quantity"]["consumed"], envelope.QUANTITY)
        self.assertEqual(response.get_json()["sale"]["credited"], False)

    def test_a_client_supplied_sale_index_is_not_honoured(self) -> None:
        response = sell_now(sell_intent(index=1, playerID=3, item=[26], row=[26]))
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(items_now(), committed_items())


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------


class RefusalTests(unittest.TestCase):
    """Each refusal answers 409, moves nothing, and names its own condition."""

    def setUp(self) -> None:
        reset_state()
        self.before = copy.deepcopy(BOOT.save_document(PID))  # type: ignore[union-attr]
        self.before_resources = copy.deepcopy(resources_now())

    def assertRefused(self, response: Result, code: str) -> None:
        self.assertEqual(response.status_code, 409, response.get_json())
        self.assertEqual(response.code(), code, response.get_json())

    def assertCorpusUnchanged(self) -> None:
        current = copy.deepcopy(BOOT.save_document(PID))  # type: ignore[union-attr]
        self.assertEqual(current, self.before)
        self.assertEqual(resources_now(), self.before_resources)

    def test_a_committed_placeable_unit_that_was_never_stored_is_refused(self) -> None:
        response = place_now(place_intent(item_id=UNSTORED_ITEM_ID))
        self.assertRefused(response, "not_in_storage")
        self.assertIn("is not in storage", response.message())
        self.assertCorpusUnchanged()

    def test_the_never_stored_item_is_a_real_committed_placeable_unit(self) -> None:
        # "Never stored" is not "unknown": the two refusals are distinct and the
        # corpus must be able to tell them apart.
        row = next(
            entry for entry in BOOT.config()["items"]  # type: ignore[union-attr]
            if int(entry["id"]) == UNSTORED_ITEM_ID
        )
        self.assertTrue(envelope.is_placeable(row), row)

    def test_an_id_resolving_to_no_committed_definition_is_refused(self) -> None:
        seed_storage()
        response = place_now(place_intent(item_id=UNKNOWN_ITEM_ID))
        self.assertRefused(response, "unknown_item_id")
        self.assertIn("no committed definition", response.message())
        self.assertEqual(store_now(), {str(SEED_PRIZE_ID): 1})
        self.assertEqual(items_now(), committed_items())
        self.assertEqual(resources_now(), self.before_resources)

    def test_a_row_carrying_neither_derived_field_is_refused(self) -> None:
        # Unreachable from the committed content (measured: 0 of 900), so the
        # committed row is stripped in memory only -- the `no_build_time`
        # precedent -- and restored byte-identically in the `finally`.
        seed_storage()
        with stripped_fields(SEED_PRIZE_ID, ("properties", "clicks_to_build")):
            response = place_now(place_intent())
        self.assertRefused(response, "item_not_placeable")
        self.assertIn("neither", response.message())
        self.assertEqual(store_now(), {str(SEED_PRIZE_ID): 1})
        self.assertEqual(items_now(), committed_items())
        self.assertEqual(resources_now(), self.before_resources)

    def test_the_two_content_refusals_are_measured_unreachable_from_the_corpus(self) -> None:
        table = BOOT.config()["items"]  # type: ignore[union-attr]
        stripped = [
            int(entry["id"]) for entry in table
            if not envelope.is_placeable(entry)
        ]
        self.assertEqual(stripped, [], stripped)
        for item_id in (UNKNOWN_ITEM_ID,):
            self.assertIsNone(envelope.committed_item(table, item_id), item_id)

    def test_an_unreadable_storage_shape_is_refused_not_coerced(self) -> None:
        # A dict SHAPE whose one count is not an integer.  A *list* store is a
        # different refusal owned by a different layer: `map_store` itself
        # rejects a non-mapping with `invalid_save_state` before this route's
        # projection ever runs, so it is covered by the accessor, not here.
        seed_storage()
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        save["maps"][0]["store"] = {"1085": "one"}
        persist(save)
        try:
            response = place_now(place_intent())
            self.assertRefused(response, "unresolvable_storage")
            self.assertEqual(save["maps"][0]["store"], {"1085": "one"})
            self.assertEqual(items_now(), committed_items())
        finally:
            save["maps"][0]["store"] = {str(SEED_PRIZE_ID): 1}
            persist(save)

    def test_a_derived_slot_an_existing_row_holds_is_refused(self) -> None:
        items = committed_items()
        items[str(OCCUPIED_SLOT)] = copy.deepcopy(envelope.RECORDED_OCCUPIED_ROW)
        items[str(PLACED_SLOT)] = copy.deepcopy(envelope.RECORDED_OCCUPIED_ROW)
        reset_state(store={str(SEED_PRIZE_ID): 1}, items=items)
        with with_hidden_conflict(str(PLACED_SLOT)):
            response = place_now(place_intent())
        self.assertRefused(response, "slot_occupied")
        self.assertIn(str(PLACED_SLOT), response.message())
        self.assertEqual(items_now()[str(PLACED_SLOT)], envelope.RECORDED_OCCUPIED_ROW)
        self.assertEqual(items_now()[str(OCCUPIED_SLOT)], envelope.RECORDED_OCCUPIED_ROW)
        self.assertEqual(store_now(), {str(SEED_PRIZE_ID): 1})
        self.assertEqual(resources_now(), self.before_resources)

    def test_a_sale_of_nothing_is_refused_rather_than_reported_as_success(self) -> None:
        response = sell_now(sell_intent(item_id=UNSTORED_ITEM_ID))
        self.assertRefused(response, "not_in_storage")
        self.assertIn("silent no-op", response.message())
        self.assertCorpusUnchanged()

    def test_a_sale_of_an_unknown_id_is_refused(self) -> None:
        seed_storage()
        response = sell_now(sell_intent(item_id=UNKNOWN_ITEM_ID))
        self.assertRefused(response, "not_in_storage")
        self.assertEqual(store_now(), {str(SEED_PRIZE_ID): 1})

    def test_a_sale_of_an_unreadable_storage_shape_is_refused(self) -> None:
        seed_storage()
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        save["maps"][0]["store"] = {"1085": "one"}
        persist(save)
        try:
            self.assertRefused(sell_now(sell_intent()), "unresolvable_storage")
        finally:
            save["maps"][0]["store"] = {str(SEED_PRIZE_ID): 1}
            persist(save)

    def test_every_refusal_is_listed_in_the_response(self) -> None:
        seed_storage()
        body = place_now(place_intent()).get_json()
        codes = [entry["refusal"] for entry in body["refusals"]]
        self.assertEqual(codes, [entry["refusal"] for entry in envelope.REFUSALS])
        for code in ("not_in_storage", "slot_occupied", "unknown_item_id",
                     "item_not_placeable"):
            self.assertIn(code, codes, code)
        for entry in body["refusals"]:
            self.assertEqual(entry["status"], 409, entry["refusal"])
            self.assertTrue(entry["implemented"], entry["refusal"])
            self.assertTrue(entry["divergence"], entry["refusal"])


# ---------------------------------------------------------------------------
# Structural fail-closed paths
# ---------------------------------------------------------------------------


class StructuralRefusalTests(unittest.TestCase):
    """Every structurally invalid body answers 400/404 with nothing executed."""

    def setUp(self) -> None:
        seed_storage()

    def assertNothingExecuted(self) -> None:
        self.assertEqual(items_now(), committed_items())
        self.assertEqual(store_now(), {str(SEED_PRIZE_ID): 1})
        self.assertEqual(ledger_now(), [])

    def test_a_missing_save_is_refused(self) -> None:
        response = place_now({"item_id": SEED_PRIZE_ID, "x": 1, "y": 1})
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(response.code(), "missing_user_id")
        self.assertNothingExecuted()

    def test_an_unknown_save_is_refused(self) -> None:
        response = place_now(place_intent(user_id="00000000-0000-4000-8000-000000000009"))
        self.assertEqual(response.status_code, 404, response.get_json())
        self.assertEqual(response.code(), "unknown_user_id")
        self.assertNothingExecuted()

    def test_a_missing_item_id_is_refused(self) -> None:
        response = place_now({"user_id": PID, "x": 1, "y": 1})
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(response.code(), "missing_item_id")
        self.assertNothingExecuted()

    def test_a_non_integer_item_id_is_refused(self) -> None:
        for bad in ("1085", 1085.5, None, [1], {"id": 1}):
            response = place_now(place_intent(item_id=bad))
            self.assertEqual(response.status_code, 400, (bad, response.get_json()))
            self.assertEqual(response.code(), "invalid_item_id", bad)
        self.assertNothingExecuted()

    def test_a_missing_or_non_integer_cell_is_refused(self) -> None:
        for payload in (
            {"user_id": PID, "item_id": SEED_PRIZE_ID, "y": 1},
            {"user_id": PID, "item_id": SEED_PRIZE_ID, "x": 1},
            {"user_id": PID, "item_id": SEED_PRIZE_ID, "x": "58", "y": 47},
            {"user_id": PID, "item_id": SEED_PRIZE_ID, "x": 58.5, "y": 47},
            {"user_id": PID, "item_id": SEED_PRIZE_ID, "x": None, "y": 47},
        ):
            response = place_now(payload)
            self.assertEqual(response.status_code, 400, (payload, response.get_json()))
            self.assertEqual(response.code(), "invalid_coordinates")
        self.assertNothingExecuted()

    def test_a_non_integer_orientation_is_refused(self) -> None:
        for bad in ("0", 1.5, [0], None):
            response = place_now(place_intent(orientation=bad))
            self.assertEqual(response.status_code, 400, (bad, response.get_json()))
            self.assertEqual(response.code(), "invalid_orientation")
        self.assertNothingExecuted()

    def test_an_omitted_orientation_uses_the_derived_default(self) -> None:
        response = place_now({"user_id": PID, "item_id": SEED_PRIZE_ID,
                              "x": PLACED_CELL[0], "y": PLACED_CELL[1]})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["placement"]["orientation"],
                         envelope.DERIVED_ORIENTATION)

    def test_an_out_of_grid_cell_is_stored_verbatim_not_refused(self) -> None:
        # The recorded M6 geometry gap: refusing it would fabricate a bound the
        # oracle does not have.
        response = place_now(place_intent(x=OUT_OF_GRID_CELL[0], y=OUT_OF_GRID_CELL[1]))
        self.assertEqual(response.status_code, 200, response.get_json())
        row = items_now()[str(PLACED_SLOT)]
        self.assertEqual(
            (row[envelope.ROW_SLOT_X], row[envelope.ROW_SLOT_Y]), OUT_OF_GRID_CELL
        )

    def test_a_non_object_body_is_refused(self) -> None:
        with harness.offline():
            response = CLIENT.post(  # type: ignore[union-attr]
                "/v0/place_stored", data="[]", content_type="application/json"
            )
        self.assertEqual(response.status_code, 400)
        self.assertNothingExecuted()

    def test_the_sale_refuses_a_missing_and_a_non_integer_item_id(self) -> None:
        response = sell_now({"user_id": PID})
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(response.code(), "missing_item_id")
        response = sell_now(sell_intent(item_id="1085"))
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(response.code(), "invalid_item_id")
        response = sell_now({"item_id": SEED_PRIZE_ID})
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(response.code(), "missing_user_id")
        response = sell_now(sell_intent(user_id="00000000-0000-4000-8000-000000000009"))
        self.assertEqual(response.status_code, 404, response.get_json())
        self.assertNothingExecuted()


# ---------------------------------------------------------------------------
# The post-execution proofs
# ---------------------------------------------------------------------------


class PostExecutionProofTests(unittest.TestCase):
    """Each proof half fails closed instead of reporting legacy's success.

    Every stub lets the **real** dispatcher run and rewrites only the reads that
    happen **after** it returns, so the assertion is about the proof and not about
    a faked legacy.
    """

    def setUp(self) -> None:
        seed_storage()
        self.before_items = copy.deepcopy(items_now())
        self.before_resources = copy.deepcopy(resources_now())

    def assertProofFailed(self, response: Result) -> None:
        self.assertEqual(response.status_code, 500, response.get_json())
        self.assertEqual(response.code(), "internal_error", response.get_json())

    def test_a_row_that_does_not_match_the_derivation_fails_closed(self) -> None:
        def wrong_team(items: Dict[str, Any]) -> Dict[str, Any]:
            row = list(items[str(PLACED_SLOT)])
            row[envelope.ROW_SLOT_PLAYER] = 3
            items[str(PLACED_SLOT)] = row
            return items

        with after_dispatch("map_items", wrong_team):
            response = place_now(place_intent())
        self.assertProofFailed(response)
        self.assertIn("derived row", response.message())

    def test_a_row_with_a_smuggled_attribute_bag_fails_closed(self) -> None:
        def smuggled(items: Dict[str, Any]) -> Dict[str, Any]:
            row = list(items[str(PLACED_SLOT)])
            row[envelope.ROW_SLOT_ATTR] = {"nc": 9}
            items[str(PLACED_SLOT)] = row
            return items

        with after_dispatch("map_items", smuggled):
            response = place_now(place_intent())
        self.assertProofFailed(response)

    def test_a_placement_at_another_slot_fails_closed(self) -> None:
        def moved(items: Dict[str, Any]) -> Dict[str, Any]:
            # `pop` with a default: the stub must not raise, or the failure
            # would be the stub's own KeyError and not the proof's verdict.
            items["7"] = items.pop(str(PLACED_SLOT), None)
            return items

        with after_dispatch("map_items", moved):
            response = place_now(place_intent())
        self.assertProofFailed(response)

    def test_a_ledger_that_grew_by_two_fails_closed(self) -> None:
        def doubled(save: Dict[str, Any]) -> Dict[str, Any]:
            out = dict(save)
            out["privateState"] = dict(save["privateState"])
            out["privateState"]["boughtUnits"] = list(
                out["privateState"].get("boughtUnits") or []
            ) + [SEED_PRIZE_ID]
            return out

        with after_dispatch("save_document", doubled):
            response = place_now(place_intent())
        self.assertProofFailed(response)

    def test_a_ledger_that_never_grew_fails_closed(self) -> None:
        def emptied(save: Dict[str, Any]) -> Dict[str, Any]:
            out = dict(save)
            out["privateState"] = dict(save["privateState"])
            out["privateState"]["boughtUnits"] = []
            return out

        with after_dispatch("save_document", emptied):
            response = place_now(place_intent())
        self.assertProofFailed(response)

    def test_any_stored_resource_that_moved_fails_closed(self) -> None:
        # Proves the "no resource moves" half is not tautological: the before
        # read is untouched and only the after read is minted.
        for name in sorted(self.before_resources):
            def minted(resources: Dict[str, int], key: str = name) -> Dict[str, int]:
                moved = dict(resources)
                moved[key] = moved[key] + 1
                return moved

            with after_dispatch("resources", minted):
                response = place_now(place_intent())
            self.assertProofFailed(response)
            self.assertIn(name, response.message())
            seed_storage()

    def test_a_sale_that_credits_a_resource_fails_closed(self) -> None:
        def credited(resources: Dict[str, int]) -> Dict[str, int]:
            moved = dict(resources)
            moved["cash"] = moved["cash"] + 500
            return moved

        with after_dispatch("resources", credited):
            response = sell_now(sell_intent())
        self.assertProofFailed(response)
        self.assertIn("credits NOTHING", response.message())

    def test_a_sale_that_consumed_the_wrong_count_fails_closed(self) -> None:
        def over_consumed(store: Dict[str, Any]) -> Dict[str, Any]:
            out = dict(store)
            out["999"] = 1
            return out

        with after_dispatch("map_store", over_consumed):
            response = sell_now(sell_intent())
        self.assertProofFailed(response)

    def test_a_sale_that_consumed_nothing_fails_closed(self) -> None:
        # The real dispatcher already emptied the store, so a stub that returned
        # the value untouched would return `{}` -- the very reading the proof
        # compares -- and the assertion would be tautologically true.  The stub
        # therefore mints the pre-execution storage instead.
        def untouched(store: Dict[str, Any]) -> Dict[str, Any]:
            return {str(SEED_PRIZE_ID): 1}

        with after_dispatch("map_store", untouched):
            response = sell_now(sell_intent())
        self.assertProofFailed(response)

    def test_a_sale_that_rewrote_a_placement_fails_closed(self) -> None:
        def rewritten(items: Dict[str, Any]) -> Dict[str, Any]:
            row = list(items["1"])
            row[envelope.ROW_SLOT_X] = 0
            items["1"] = row
            return items

        with after_dispatch("map_items", rewritten):
            response = sell_now(sell_intent())
        self.assertProofFailed(response)

    def test_a_sale_that_appended_to_the_ledger_fails_closed(self) -> None:
        def appended(save: Dict[str, Any]) -> Dict[str, Any]:
            out = dict(save)
            out["privateState"] = dict(save["privateState"])
            out["privateState"]["boughtUnits"] = list(
                out["privateState"].get("boughtUnits") or []
            ) + [SELL_ITEM_ID]
            return out

        with after_dispatch("save_document", appended):
            response = sell_now(sell_intent())
        self.assertProofFailed(response)

    def test_a_committed_field_the_derivation_cannot_read_is_the_services_error(self) -> None:
        # `properties` is a raw JSON-encoded string in the loaded config; a
        # committed value the derivation cannot read the way legacy's `int()`
        # reads it is content drift, so it is the service's 500 and never the
        # client's 400.
        saved: List[Tuple[Dict[str, Any], Any]] = []
        for entry in BOOT.config()["items"]:  # type: ignore[union-attr]
            if int(entry["id"]) == SEED_PRIZE_ID:
                saved.append((entry, entry["properties"]))
                entry["properties"] = "{not json"
        assert saved
        try:
            response = place_now(place_intent())
            self.assertProofFailed(response)
            self.assertEqual(response.message(), "item_properties_invalid")
            self.assertEqual(items_now(), self.before_items)
            self.assertEqual(store_now(), {str(SEED_PRIZE_ID): 1})
        finally:
            for entry, value in saved:
                entry["properties"] = value

    def test_a_legacy_failure_after_validation_is_reported_not_claimed(self) -> None:
        def raising(user_id: str, payload: Any) -> None:
            raise RuntimeError("legacy raised")

        with patched_boot("execute_commands", raising):
            response = place_now(place_intent())
        self.assertProofFailed(response)
        self.assertIn("legacy command execution failed", response.message())

    def test_a_legacy_failure_on_the_sale_is_reported_not_claimed(self) -> None:
        def raising(user_id: str, payload: Any) -> None:
            raise RuntimeError("legacy raised")

        with patched_boot("execute_commands", raising):
            response = sell_now(sell_intent())
        self.assertProofFailed(response)
        self.assertIn("legacy command execution failed", response.message())


# ---------------------------------------------------------------------------
# The second recorded scenario: the committed sale prize
# ---------------------------------------------------------------------------


class SecondPrizesTests(unittest.TestCase):
    """The line is not hard-wired to collection 1's prize."""

    def test_the_other_committed_unit_prize_places_and_sells_like_the_first(self) -> None:
        reset_state()
        with harness.offline():
            response = CLIENT.post(  # type: ignore[union-attr]
                "/v0/collection",
                json={"user_id": PID, "collection_id": SELL_COLLECTION_ID},
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(store_now(), {str(SELL_ITEM_ID): 1})
        placed = place_now(place_intent(item_id=SELL_ITEM_ID))
        self.assertEqual(placed.status_code, 200, placed.get_json())
        self.assertEqual(placed.get_json()["placement"]["map_key"], PLACED_SLOT)
        self.assertEqual(placed.get_json()["ledger_after"], [SELL_ITEM_ID])
        self.assertEqual(store_now(), {}, "the placement consumed the stored prize")
        # The sale half needs the storage again, and the collection route cannot
        # re-grant it: collection 2 is already in the player's ledger.  The
        # storage is therefore re-seeded through the test-only reset, which also
        # restores the placements -- so "the sale removed nothing" is asserted
        # against the committed 40 rather than against a row this test made.
        reset_state(store={str(SELL_ITEM_ID): 1})
        sold = sell_now(sell_intent(item_id=SELL_ITEM_ID))
        self.assertEqual(sold.status_code, 200, sold.get_json())
        self.assertEqual(store_now(), {})
        self.assertEqual(items_now(), committed_items())


# ---------------------------------------------------------------------------
# The recorded absences, asserted over the route source
# ---------------------------------------------------------------------------


class RecordedAbsenceTests(unittest.TestCase):
    """Neither route computes anything legacy does not."""

    def setUp(self) -> None:
        seed_storage()
        self.place_route = route_source("v0_place_stored")
        self.sell_route = route_source("v0_sell_stored")

    def test_the_placement_route_derives_the_slot_and_checks_no_occupancy(self) -> None:
        names = code_names(self.place_route)
        # The slot rule is reached only through the shared derivation, so the
        # route contains no occupancy test of its own -- and no spelling of one.
        self.assertIn("resolve_slot", names)
        for absent in ("slot_occupied", "is_occupied", "cell_occupied", "occupied_cells",
                       "find_free_cell", "in_bounds", "inside_grid", "within_bounds",
                       "grid_bounds", "MAP_SIZE"):
            self.assertNotIn(absent, names, absent)

    def test_neither_route_computes_a_price_or_a_refund(self) -> None:
        for route in (self.place_route, self.sell_route):
            names = code_names(route)
            for absent in ("price_of", "refund_of", "resale_price", "credit",
                           "charge", "cost_of", "sell_price"):
                self.assertNotIn(absent, names, absent)

    def test_neither_route_invents_a_capacity_or_stock_rule(self) -> None:
        for route in (self.place_route, self.sell_route):
            names = code_names(route)
            for absent in ("capacity", "max_stored", "stock", "capacity_left"):
                self.assertNotIn(absent, names, absent)

    def test_the_routes_read_no_price_constant(self) -> None:
        for route in (self.place_route, self.sell_route):
            self.assertNotIn("COST_", route)
            self.assertNotIn("PRICE", route)

    def test_the_sale_route_adds_no_placement(self) -> None:
        for absent in ("map_put_item", "push_map_item", "map_add_item"):
            self.assertNotIn(absent, self.sell_route, absent)

    def test_each_route_executes_exactly_one_legacy_command(self) -> None:
        self.assertEqual(self.place_route.count("execute_commands"), 1)
        self.assertEqual(self.sell_route.count("execute_commands"), 1)
        self.assertIn(envelope.PLACE_COMMAND, self.place_route)
        self.assertIn(envelope.SELL_COMMAND, self.sell_route)

    def test_each_route_reads_the_storage_state_exactly_twice(self) -> None:
        self.assertEqual(self.place_route.count("_stored_placement_state(boot, user_id)"), 2)
        self.assertEqual(self.sell_route.count("_stored_placement_state(boot, user_id)"), 2)

    def test_the_helper_block_defines_only_the_three_documented_helpers(self) -> None:
        text = source()
        start = text.index("def _stored_placement_state(")
        # Bounded by THIS line's own banner rather than by ``create_app``.
        # A later line (``godot-combat-actions``) added two more module-scope
        # helpers above ``create_app`` for exactly the same reason, and extending
        # this slice to ``create_app`` would silently fold them into an assertion
        # whose name and subject are the three stored-placement helpers. The
        # stronger whole-region claim is asserted by the test below instead.
        end = text.index("# combat actions (godot-combat-actions)")
        block = textwrap.dedent(text[start:end].lstrip("\n"))
        tree = ast.parse(block)
        self.assertEqual(
            [node.name for node in tree.body if isinstance(node, ast.FunctionDef)],
            ["_stored_placement_state", "_stored_item_row", "_stored_placement_refusal"],
        )

    def test_the_whole_module_scope_helper_region_declares_only_documented_helpers(
        self,
    ) -> None:
        # The version of the assertion above that keeps holding as lines are
        # added: EVERY module-scope helper above ``create_app`` is one of the
        # documented ones. Pinning the whole inventory is deliberate -- it makes
        # "a helper cannot hide inside a route's marker-bounded slice" the ONLY
        # way to add one, and it fails loudly the moment a helper appears that no
        # delivered suite claims.
        text = source()
        start = text.index("def envelope(")
        end = text.index("def create_app(")
        block = textwrap.dedent(text[start:end].lstrip("\n"))
        tree = ast.parse(block)
        self.assertEqual(
            [node.name for node in tree.body if isinstance(node, ast.FunctionDef)],
            [
                "envelope", "error_payload", "error_response", "_resolve_user_id",
                "_legacy_boot_error", "_seed_dead_heroes", "_committed_item",
                "_stored_placement_state", "_stored_item_row",
                "_stored_placement_refusal", "_combat_snapshot", "_combat_refusal",
                # godot-damage (M10 line 3): four more, for the reason spelled
                # out in the banner above them -- the only decorator-free gap in
                # the file sits between /v0/combat's body and /v0/place_stored's
                # decorator, so a fifth route's helpers could not live there
                # without landing inside the combat route's own marker-bounded
                # slice.  The comment naming that gap, and the pins that made it
                # load-bearing, are in test_magic_endpoint.py.
                "_magic_snapshot", "_legacy_recorded_after", "_magic_refusal",
                "_committed_magic",
                # godot-rewards (M10 line 1): two more.  This pin is the
                # hand-off mechanism the comment above describes -- a helper
                # cannot be added without a delivered suite claiming it -- so
                # this line extends the inventory rather than weakening it, and
                # the claim is moved into this suite, which already owns the
                # whole region.
                "_reward_snapshot", "_reward_refusal",
            ],
        )


class RoutePlacementTests(unittest.TestCase):
    """Where the two routes and their helpers sit is load-bearing, and pinned.

    The delivered tutorial suite pins the *first* slot (ahead of every other
    route).  This class pins the second and the module-scope consequence:

    * the two routes occupy the only interior gap no delivered guard's end
      marker reaches -- after the first route's body and before the second
      route's decorator;
    * their three helpers therefore had to be hoisted to module scope, because a
      helper inside that gap lands in the FIRST route's own marker-bounded slice,
      which the delivered invariant requires to hold exactly one function.

    Both placements actually attempted before this slot was found broke
    delivered guards; the failures were measured by running the delivered
    suites, not assumed.
    """

    def test_the_two_routes_sit_between_the_first_and_the_second_route(self) -> None:
        text = source()
        tutorial = text.index('@app.post("/v0/tutorial")')
        session = text.index('@app.get("/v0/session")')
        place = text.index('@app.post("/v0/place_stored")')
        sell = text.index('@app.post("/v0/sell_stored")')
        self.assertLess(tutorial, place)
        self.assertLess(place, sell)
        self.assertLess(sell, session)

    def test_the_helpers_are_at_module_scope_above_create_app(self) -> None:
        text = source()
        create = text.index("def create_app(")
        for helper in ("_stored_placement_state", "_stored_item_row",
                       "_stored_placement_refusal"):
            declared = text.index("def %s(" % helper)
            self.assertLess(declared, create, helper)
        # And each takes `boot` explicitly rather than closing over it.
        self.assertIn("boot: compat_legacy.LegacyBoot, user_id: str", text)

    def test_no_helper_falls_inside_any_route_slice(self) -> None:
        text = source()
        offsets: List[int] = []
        cursor = 0
        for line in text.split("\n"):
            if line.strip().startswith("@app."):
                offsets.append(cursor)
            cursor += len(line) + 1
        names = (
            "tutorial", "combat", "place_stored", "sell_stored", "session",
            "bootstrap",
            "place", "purchase", "move", "sell", "store", "upgrade",
            "construction", "collect", "expand", "queue", "collection",
            "resurrect", "quests", "research", "level_up",
        )
        for declared in names:
            start = text.index("def v0_%s(" % declared)
            following = [o for o in offsets if o > start]
            end = following[0] if following else text.index(
                'app.config["COMPAT_LEGACY_CORPUS"]'
            )
            span = text[start:end]
            for helper in ("_stored_placement_state", "_stored_item_row",
                           "_stored_placement_refusal"):
                self.assertNotIn("def %s(" % helper, span, "%s/%s" % (declared, helper))

    def test_every_route_slice_still_parses_as_exactly_one_function(self) -> None:
        # The delivered invariant, checked against every route in the file --
        # including the two new ones -- rather than against the two fragile
        # spans the tutorial suite names.
        text = source()
        offsets: List[int] = []
        cursor = 0
        for line in text.split("\n"):
            if line.strip().startswith("@app."):
                offsets.append(cursor)
            cursor += len(line) + 1
        names = (
            "tutorial", "combat", "place_stored", "sell_stored", "session",
            "bootstrap",
            "place", "purchase", "move", "sell", "store", "upgrade",
            "construction", "collect", "expand", "queue", "collection",
            "resurrect", "quests", "research", "level_up",
        )
        for declared in names:
            start = text.index("def v0_%s(" % declared)
            following = [o for o in offsets if o > start]
            end = following[0] if following else text.index(
                'app.config["COMPAT_LEGACY_CORPUS"]'
            )
            tree = ast.parse(textwrap.dedent(text[start:end].lstrip("\n")))
            self.assertEqual(
                [node.name for node in tree.body if isinstance(node, ast.FunctionDef)],
                ["v0_%s" % declared],
                declared,
            )

    def test_the_first_route_is_still_the_tutorial_route(self) -> None:
        markers = [
            line.strip() for line in source().split("\n") if line.strip().startswith("@app.")
        ]
        self.assertEqual(markers[0], '@app.post("/v0/tutorial")')
        self.assertEqual(markers[-1], '@app.post("/v0/level_up")')

    def test_the_module_scope_note_sits_where_the_helpers_are_declared(self) -> None:
        text = source()
        banner = text[:text.index("def _stored_placement_state(")].split("\n")[-14:]
        note = "\n".join(banner)
        self.assertIn("stored-item placement", note)
        self.assertIn("MODULE scope on purpose", note)

    def test_the_route_note_names_the_slot_above_the_first_decorator(self) -> None:
        text = source()
        note = text[:text.index('@app.post("/v0/tutorial")')].split("\n")[-14:]
        joined = "\n".join(note)
        self.assertIn("order is load-bearing", joined)
        self.assertIn("stored-placement routes below", joined)