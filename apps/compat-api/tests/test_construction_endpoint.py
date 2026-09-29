#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/construction`` behavior tests (OpenSpec task 2.3).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection.  The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across construction
execution.

Every test snapshots the corpus map at its own start and asserts its
post-condition against that snapshot, so the suite is order-independent.
Mutating tests take dedicated rows, and no test asserts an absolute
attribute-bag value on a row another test may already have touched.

Covered:

* **the three actions** — ``"start"`` records the derived countdown and
  re-stamps the row's start instant, ``"click"`` raises the click counter,
  and ``"finish"`` consumes it, each with its own post-condition and each
  carrying both rows, the resolved action, and the resources.  A full
  start → click → finish walk, a second click, a click on a row the purchase
  half never seeded, and a completion of an unseeded row are all covered.
* **the derived duration** — it comes from the addressed placement's item's
  committed ``build_time`` through the legacy configuration, never from a
  client: a client-supplied ``duration`` cannot influence it, and an item
  whose committed build time cannot be resolved to a positive integer is
  answered ``no_build_time`` **before** the dispatcher runs.  Because a
  non-positive duration would make legacy *clear* the row's whole attribute
  bag, the refusal is asserted as a behavior, not a formality.
* **the per-action post-execution proof** — a vanished row, a row without an
  attribute bag, a row that stopped being eight fields, a start without the
  derived countdown, a click without an integer counter of at least one, and
  a completion that still carries one each fail closed with
  ``internal_error`` rather than reporting legacy's success.  Each is
  exercised by a stubbed survivor that lets the real dispatcher run and only
  rewrites the **post**-execution read.
* **the neutral resource vector** — no resource moves, so **no building cost
  is claimed**, and no client-supplied duration, price, quantity, or resource
  delta is honored anywhere in the contract.
* **fail-closed paths** — every structurally unresolvable input in the spec
  (non-object body, missing/invalid/unknown save id, missing/invalid/unknown
  item index, missing/non-string/unknown action) returns its documented
  structured error with the corpus byte-unchanged and no row rewritten.
* **session/bootstrap byte-identity** is retained after constructions, and
  the legacy accessors agree with the persisted map.
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
import construction_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed fresh-player corpus is keyed "1".."40".  Four rows belong to
# the other committed fixtures and are therefore never mutated by a *success*
# here: slot 11 (the construction fixture's row, which the move fixture
# repositions in its own independent transaction), slot 12 (the upgrade
# fixture's Wall I), slot 20 (the sell fixture's Turret I), and slot 2 (the
# store fixture's Tree).  Every other mutating test below takes a dedicated
# row, and each assertion is expressed against the test's own snapshot.
FIXTURE_INDEX = 11
FIXTURE_ITEM_ID = 22  # Turret I
FIXTURE_BUILD_TIME = 5
FIXTURE_CLICKS_TO_BUILD = 1
FIXTURE_ANCHOR = (58, 48)

# Dedicated rows, each chosen for the committed content the test needs.  The
# addressed item's committed build_time / clicks_to_build is noted per row.
WALK_INDEX = 3  # Wall I: 1 / 1
SECOND_CLICK_INDEX = 4  # Wall I: 1 / 1
NO_CLEAR_INDEX = 5  # Wall I: 1 / 1
NO_BUILD_TIME_INDEX = 6  # Wall I: 1 / 1 (the accessor is stubbed; never runs)
DURATION_INDEX = 37  # Broken Bridge: 5 / 1 — a build time that is not 1
ACCESSOR_INDEX = 38  # Space Station: 5 / 0
CLICK_INDEX = 33  # Broken Bridge: 5 / 1
FINISH_INDEX = 1  # the Command Center: 5 / 1
EMPTY_INDEX = 21  # Trees: 180 / 0 — no click seed, empty attribute bag
ALIAS_INDEX = 8  # Wall I: 1 / 1
PERSIST_INDEX = 7  # Wall I: 1 / 1
# Rows used by the post-execution-proof stubs; each is a real placement the
# real dispatcher then mutates for real before the proof refuses to claim it.
PROOF_START_MISSING_CP = 29  # Bridge: 5 / 0
PROOF_START_WRONG_CP = 30  # Bridge: 5 / 0
PROOF_CLICK_MISSING_NC = 31  # Bridge: 5 / 0
PROOF_CLICK_ZERO_NC = 32  # Bridge: 5 / 0
PROOF_CLICK_STRING_NC = 34  # Bridge: 5 / 0
PROOF_FINISH_KEPT_NC = 39  # Small Harbour: 5 / 0
PROOF_ROW_ABSENT = 40  # Harbour: 5 / 0
PROOF_NO_BAG = 35  # Bridge: 5 / 0
PROOF_NOT_EIGHT = 36  # Bridge: 5 / 0
PROOF_UNREPORTABLE = 9  # Wall I: 1 / 1 (the dispatcher never runs)
PROOF_RAISING = 10  # Wall I: 1 / 1 (the dispatcher never runs)
TREE_ITEM_ID = 905
# The other fixtures' rows, which a construction must leave byte-identical.
FIXTURE_FOREIGN_ROWS = ("12", "20", "2")

# The action vocabulary and the commands it resolves to (design D2).
ACTION_START = construction_envelope.ACTION_START
ACTION_CLICK = construction_envelope.ACTION_CLICK
ACTION_FINISH = construction_envelope.ACTION_FINISH


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
    # construction execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a construction execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def construct(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/construction", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def map_items() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["items"]  # type: ignore[index]


def bought_units() -> List[Any]:
    return list(corpus_save()["privateState"]["boughtUnits"])


def intent(index: int, action: str) -> Dict[str, Any]:
    return {"user_id": PID, "item_index": index, "action": action}


def build_time(item_id: int) -> Optional[int]:
    """The endpoint's own resolution rule, read from the live configuration."""
    return BOOT.item_build_time(item_id)  # type: ignore[union-attr]


def row_of(items: Dict[str, Any], index: int) -> List[Any]:
    return list(items[str(index)])


def assert_only_touched(
    case: unittest.TestCase,
    before_items: Dict[str, Any],
    index: int,
) -> None:
    """Assert exactly the addressed row changed and nothing else moved."""
    after_items = map_items()
    key = str(index)
    case.assertIn(key, before_items)
    case.assertIn(key, after_items)
    # No key is added or removed: a construction action never creates or
    # destroys a placement.
    case.assertEqual(len(after_items), len(before_items))
    for other in before_items:
        if other == key:
            continue
        with case.subTest(key=other):
            case.assertEqual(after_items[other], before_items[other])


def _absent_after_execution(index: int):
    """A ``has_map_item`` stub: resolves before, absent after.

    The endpoint resolves the index once before executing and once after, so a
    two-call stub reproduces the post-state a destroyed row would leave behind
    without touching the real legacy dispatcher.  No construction command can
    do that — every one of them writes only ``item[3]`` and ``item[6]`` — which
    is exactly why the proof exists and must fail closed.
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

    The endpoint reads the row once before execution (for ``previous``) and
    once after (for ``row``).  Rewriting only the second read is what lets each
    clause of the per-action proof be exercised in isolation: the attribute bag
    the real dispatcher actually wrote is replaced with one that violates
    exactly that action's post-condition, so exactly one clause can fail.
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


def _with_attr(row: List[Any], attr: Any) -> List[Any]:
    return list(row[:6]) + [attr] + list(row[7:])


def _without_countdown(row: List[Any]) -> List[Any]:
    """A start's row with the countdown removed: the ``cp`` clause alone fails."""
    return _with_attr(
        row, {key: value for key, value in dict(row[6]).items() if key != "cp"}
    )


def _wrong_countdown(row: List[Any]) -> List[Any]:
    """A start's row with a countdown the item's build time does not name."""
    return _with_attr(row, dict(row[6], cp=3600))


def _without_counter(row: List[Any]) -> List[Any]:
    """A click's row with the counter removed: the ``nc >= 1`` clause fails."""
    return _with_attr(
        row, {key: value for key, value in dict(row[6]).items() if key != "nc"}
    )


def _zero_counter(row: List[Any]) -> List[Any]:
    """A click's row whose counter is present but zero: the "at least 1"
    clause fails."""
    return _with_attr(row, dict(row[6], nc=0))


def _string_counter(row: List[Any]) -> List[Any]:
    """A click's row whose counter is a string: the "strict int" clause fails."""
    return _with_attr(row, dict(row[6], nc="1"))


def _counter_kept(row: List[Any]) -> List[Any]:
    """A completion's row that still carries the counter: the ``finish``
    clause fails."""
    return _with_attr(row, dict(row[6], nc=1))


def _no_attribute_bag(row: List[Any]) -> List[Any]:
    """A row whose attribute bag is not a mapping."""
    return _with_attr(row, "not a bag")


def _not_eight_fields(row: List[Any]) -> List[Any]:
    """A row that stopped being an eight-field entry."""
    return list(row[:7])


class Result:
    """A captured response plus the app that produced it.

    The app must stay referenced while the test reads the response: Flask's
    test client resolves the JSON decoder through a weak reference to the app,
    so returning only the response and letting the app go out of scope turns
    every later ``get_json()`` into a ``ReferenceError``.
    """

    def __init__(self, app: Any, response: Any) -> None:
        self.app = app
        self.response = response

    @property
    def status_code(self) -> int:
        return int(self.response.status_code)

    def get_json(self) -> Any:
        return self.response.get_json()


def post_only(index: int, transform, payload: Dict[str, Any]) -> Result:
    """Run one intent against a ``BOOT`` whose **post** read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.map_item  # type: ignore[union-attr]
    BOOT.map_item = _row_rewritten_after_execution(index, transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/construction", json=payload))
    finally:
        BOOT.map_item = original  # type: ignore[assignment]


def post_with_absent_survivor(index: int, payload: Dict[str, Any]) -> Result:
    """Run one intent against a ``BOOT`` whose row vanishes after execution."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.has_map_item  # type: ignore[union-attr]
    BOOT.has_map_item = _absent_after_execution(index)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/construction", json=payload))
    finally:
        BOOT.has_map_item = original  # type: ignore[assignment]


def post_with_unresolvable_build_time(index: int, payload: Dict[str, Any]) -> Result:
    """Run one intent against a ``BOOT`` whose build time cannot be resolved.

    Every item the committed corpus places carries a positive ``build_time``
    (verified: all 40 rows resolve), so the ``no_build_time`` path is
    exercised by stubbing the *accessor* to return ``None`` for the addressed
    row's item, which is exactly the fail-closed input the endpoint must refuse
    before the dispatcher runs.  The accessor's own rule is covered against the
    real configuration by :class:`ItemBuildTimeTests`, including every committed
    item whose ``build_time`` is ``"0"``.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.item_build_time  # type: ignore[union-attr]
    addressed = int(map_items()[str(index)][0])

    def stub(item_id: int) -> Optional[int]:
        if int(item_id) == addressed:
            return None
        return original(item_id)

    BOOT.item_build_time = stub  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/construction", json=payload))
    finally:
        BOOT.item_build_time = original  # type: ignore[assignment]


class ConstructionActionTests(unittest.TestCase):
    """The observable effects of the three derived legacy commands."""

    def test_a_start_records_the_derived_countdown_and_reports_both_rows(self) -> None:
        index = FIXTURE_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())
        before_bought = bought_units()
        before_row = row_of(before_items, index)

        response = construct(intent(index, ACTION_START))

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
                "previous",
                "row",
                "action",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # The legacy result: command.php returns exactly this whenever
        # command() returns without raising.
        self.assertEqual(payload["result"], "success")
        # The resolved action, echoed from the closed vocabulary.
        self.assertEqual(payload["action"], ACTION_START)

        # The row as read *before* execution.
        self.assertEqual(payload["previous"], before_row)
        self.assertEqual(len(payload["previous"]), 8)

        # The row re-read from the persisted save *after* execution.
        row = payload["row"]
        self.assertEqual(len(row), 8)
        self.assertEqual(row[0], before_row[0])  # same item
        self.assertEqual([row[1], row[2]], list(FIXTURE_ANCHOR))  # same cell
        self.assertEqual(row[4], before_row[4])  # orientation
        self.assertEqual(row[5], [])  # store
        self.assertEqual(row[7], before_row[7])  # player team
        # The start instant is a fresh wall-clock stamp; remaining time is
        # cp - (now - item[3]), a pure client derivation no branch computes.
        self.assertIsInstance(row[3], int)
        self.assertGreater(row[3], 0)
        self.assertGreater(row[3], before_row[3])
        # The post-condition: attr carries the derived countdown.
        self.assertEqual(row[6], {"cp": FIXTURE_BUILD_TIME})
        self.assertEqual(row[6]["cp"], build_time(FIXTURE_ITEM_ID))

        # The persisted row is exactly what the response reported.
        self.assertEqual(map_items()[str(index)], row)

        # Neutral derived vector: no stored resource moves, so this endpoint
        # claims no building cost (design D4).
        self.assertEqual(payload["resources"], before)
        self.assertEqual(
            set(payload["resources"]),
            {"xp", "gold", "wood", "oil", "steel", "cash", "mana"},
        )
        self.assertEqual(corpus_save()["maps"][0]["gold"], payload["resources"]["gold"])
        self.assertEqual(
            corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"]
        )
        self.assertEqual(
            corpus_save()["privateState"]["mana"], payload["resources"]["mana"]
        )

        # A construction writes no purchase, no storage, and no dead unit.
        self.assertEqual(corpus_save()["maps"][0]["store"], {})
        self.assertEqual(bought_units(), before_bought)
        self.assertEqual(corpus_save()["privateState"]["deadHeroes"], {})
        # No key is added or removed; exactly one row changed.
        self.assertEqual(len(map_items()), len(before_items))
        assert_only_touched(self, before_items, index)
        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_click_raises_the_click_counter(self) -> None:
        index = CLICK_INDEX
        before_items = copy.deepcopy(map_items())
        before_row = row_of(before_items, index)
        before_resources = BOOT.resources(PID)  # type: ignore[union-attr]
        self.assertEqual(before_row[6], {})

        response = construct(intent(index, ACTION_CLICK))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["action"], ACTION_CLICK)
        self.assertEqual(payload["previous"], before_row)
        row = payload["row"]
        # add_click seeds the counter to 1 when the purchase half never wrote
        # one (engine.py:125-130) — the fresh corpus row carries attr {}.
        self.assertEqual(row[6], {"nc": 1})
        # A click does not start a countdown: cp is absent, not zero.
        self.assertNotIn("cp", row[6])
        # The timestamp is untouched by add_click.
        self.assertEqual(row[3], before_row[3])
        self.assertEqual(row[0:3], before_row[0:3])
        self.assertEqual(row[4:], before_row[4:6] + [row[6]] + before_row[7:])
        self.assertEqual(map_items()[str(index)], row)
        self.assertEqual(payload["resources"], before_resources)
        assert_only_touched(self, before_items, index)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_finish_consumes_the_click_counter(self) -> None:
        index = FINISH_INDEX
        # Give the row a counter the way the purchase half would.
        BOOT.execute_commands(  # type: ignore[union-attr]
            PID, construction_envelope.build_envelope_click(item_index=index)
        )
        before_items = copy.deepcopy(map_items())
        before_row = row_of(before_items, index)
        self.assertEqual(before_row[6], {"nc": 1})

        response = construct(intent(index, ACTION_FINISH))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["action"], ACTION_FINISH)
        self.assertEqual(payload["previous"], before_row)
        row = payload["row"]
        # The post-condition: the completion carries no click counter.
        self.assertNotIn("nc", row[6])
        # activate_item_click deletes only nc, so an empty bag stays empty.
        self.assertEqual(row[6], {})
        # The timestamp is untouched by a completion.
        self.assertEqual(row[3], before_row[3])
        self.assertEqual(row[0:3], before_row[0:3])
        self.assertEqual(map_items()[str(index)], row)
        assert_only_touched(self, before_items, index)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_full_start_click_finish_walk(self) -> None:
        """The state machine a player walks, in order, on one row."""
        index = WALK_INDEX
        before = BOOT.resources(PID)  # type: ignore[union-attr]
        before_items = copy.deepcopy(map_items())
        start_row = row_of(before_items, index)
        duration = build_time(int(start_row[0]))
        self.assertEqual(start_row[6], {})

        started = construct(intent(index, ACTION_START))
        self.assertEqual(started.status_code, 200)
        start_payload = started.get_json()
        self.assertEqual(start_payload["row"][6], {"cp": duration})

        clicked = construct(intent(index, ACTION_CLICK))
        self.assertEqual(clicked.status_code, 200)
        click_payload = clicked.get_json()
        self.assertEqual(click_payload["previous"], start_payload["row"])
        self.assertEqual(click_payload["row"][6], {"cp": duration, "nc": 1})
        # The click did not move the start instant.
        self.assertEqual(click_payload["row"][3], start_payload["row"][3])

        finished = construct(intent(index, ACTION_FINISH))
        self.assertEqual(finished.status_code, 200)
        finish_payload = finished.get_json()
        self.assertEqual(finish_payload["previous"], click_payload["row"])
        # The countdown the client needs for its readout survives the
        # completion; only nc is deleted.
        self.assertEqual(finish_payload["row"][6], {"cp": duration})

        # The item, cell, orientation, store, and player never moved, and no
        # resource ever moved: **no building cost is claimed**.
        final = finish_payload["row"]
        self.assertEqual(final[0], start_row[0])
        self.assertEqual(final[1:3], start_row[1:3])
        self.assertEqual(final[4], start_row[4])
        self.assertEqual(final[5], start_row[5])
        self.assertEqual(final[7], start_row[7])
        self.assertEqual(finish_payload["resources"], before)
        assert_only_touched(self, before_items, index)

    def test_a_second_click_keeps_raising_the_counter(self) -> None:
        """A repeat is a real second click, not a cumulative corruption."""
        index = SECOND_CLICK_INDEX
        first = construct(intent(index, ACTION_CLICK))
        self.assertEqual(first.status_code, 200)
        first_payload = first.get_json()
        self.assertEqual(first_payload["row"][6], {"nc": 1})

        second = construct(intent(index, ACTION_CLICK))
        self.assertEqual(second.status_code, 200)
        second_payload = second.get_json()
        self.assertEqual(second_payload["previous"], first_payload["row"])
        self.assertEqual(second_payload["row"][6], {"nc": 2})
        # The server never compares the counter with clicks_to_build: reaching
        # the item's requirement is the client's decision, so a second click is
        # a legitimate second legacy command.
        self.assertGreater(second_payload["row"][6]["nc"], FIXTURE_CLICKS_TO_BUILD)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_completion_on_a_row_with_no_counter_is_still_a_success(self) -> None:
        """``activate_item_click`` deletes ``nc`` only when it is present."""
        index = EMPTY_INDEX
        before_items = copy.deepcopy(map_items())
        response = construct(intent(index, ACTION_FINISH))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertNotIn("nc", payload["row"][6])
        self.assertEqual(payload["row"][6], before_items[str(index)][6])
        assert_only_touched(self, before_items, index)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_start_never_clears_the_row_attribute_bag(self) -> None:
        """Design D6: the clearing branch is unreachable through this contract.

        Legacy's ``activate`` with a **non-positive** duration clears the whole
        bag, destroying ``nc`` and any ``si`` entries.  A start always sends the
        item's positive committed build time, so a row that already carries
        construction state keeps it.
        """
        index = NO_CLEAR_INDEX
        item_id = int(map_items()[str(index)][0])
        seeded = construct(intent(index, ACTION_CLICK))
        self.assertEqual(seeded.status_code, 200)
        self.assertEqual(seeded.get_json()["row"][6], {"nc": 1})

        response = construct(intent(index, ACTION_START))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # cp is added; the existing counter survives.
        self.assertEqual(payload["row"][6], {"nc": 1, "cp": build_time(item_id)})
        self.assertIn("nc", payload["row"][6])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_each_action_derives_exactly_the_documented_command(self) -> None:
        built = {
            ACTION_START: construction_envelope.build_envelope_start(
                item_index=FIXTURE_INDEX, duration=FIXTURE_BUILD_TIME, ts=1700000000
            ),
            ACTION_CLICK: construction_envelope.build_envelope_click(
                item_index=FIXTURE_INDEX, ts=1700000000
            ),
            ACTION_FINISH: construction_envelope.build_envelope_finish(
                item_index=FIXTURE_INDEX, ts=1700000000
            ),
        }
        self.assertEqual(
            [payload["commands"][0][1] for payload in built.values()],
            ["activate", "add_click", "activate_item_click"],
        )
        self.assertEqual(built[ACTION_START]["commands"][0][2], [FIXTURE_INDEX, 5])
        self.assertEqual(built[ACTION_CLICK]["commands"][0][2], [FIXTURE_INDEX])
        self.assertEqual(built[ACTION_FINISH]["commands"][0][2], [FIXTURE_INDEX])
        for payload in built.values():
            self.assertEqual(payload["commands"][0][3], [0] * 8)
        self.assertIs(compat_service.construction_envelope, construction_envelope)


class ItemBuildTimeTests(unittest.TestCase):
    """The committed-configuration resolution rule (design D2)."""

    def test_a_resolving_build_time_is_returned_as_a_positive_int(self) -> None:
        self.assertEqual(build_time(FIXTURE_ITEM_ID), FIXTURE_BUILD_TIME)
        self.assertIsInstance(build_time(FIXTURE_ITEM_ID), int)
        self.assertNotIsInstance(build_time(FIXTURE_ITEM_ID), bool)
        self.assertGreater(build_time(FIXTURE_ITEM_ID) or 0, 0)

    def test_the_known_committed_durations_resolve(self) -> None:
        """Walls 1, Turret I 5, Turret II 600, Command Center 5, Trees 180."""
        expected = {23: 1, 22: 5, 57: 600, 26: 5, 905: 180}
        for item_id, seconds in sorted(expected.items()):
            with self.subTest(item_id=item_id):
                self.assertEqual(build_time(item_id), seconds)

    def test_a_non_resolvable_id_means_no_build_time(self) -> None:
        """An id the loaded configuration cannot index has no duration."""
        for bad in (999999, -1, "not an item", None):
            with self.subTest(item_id=bad):
                self.assertIsNone(build_time(bad))  # type: ignore[arg-type]

    def test_a_zero_or_negative_build_time_is_never_coerced(self) -> None:
        """The documented "non-positive means none" rule, over the real config.

        427 items record ``build_time "0"`` in the **loaded** config this
        service derives from (the five ordered patches add entries to the stored
        ``config/main.json``, where 306 of the 778 stored items record ``"0"``
        and none of them is a building).  Sending that as an ``activate``
        duration would make legacy **clear the row's whole attribute bag**
        (``command.py:425-427``), so the accessor must return ``None`` for every
        one of them rather than a zero.  An absent attribute and a non-integer
        value are the same case and are covered by the id rule above.
        """
        items = BOOT.config()["items"]  # type: ignore[union-attr]
        zero_bearing = [
            int(entry["id"])
            for entry in items
            if str(entry.get("build_time")).strip() == "0"
        ]
        self.assertEqual(len(zero_bearing), 427)
        for item_id in zero_bearing[:20]:
            with self.subTest(item_id=item_id):
                self.assertIsNone(build_time(item_id))
        # And none of them is placed in the committed corpus, so the
        # ``no_build_time`` path is only reachable for a row the corpus does
        # not carry — which is why the endpoint's test stubs the accessor.
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        placed = {int(row[0]) for row in seed_items.values()}
        self.assertEqual(placed & set(zero_bearing), set())

    def test_no_committed_item_resolves_to_a_non_positive_build_time(self) -> None:
        """The rule is not special-cased: every resolved value is positive.

        The whole-config sweep is asserted through the endpoint's own accessor
        so a future config entry with a zero or negative ``build_time`` can
        never be coerced into a clearing ``activate(..., 0)``.
        """
        items = BOOT.config()["items"]  # type: ignore[union-attr]
        resolved = 0
        for entry in items:
            item_id = int(entry["id"])
            value = build_time(item_id)
            if value is None:
                continue
            resolved += 1
            self.assertGreater(value, 0)
        self.assertGreater(resolved, 0)
        self.assertLessEqual(resolved, len(items))

    def test_every_placed_row_of_the_committed_corpus_is_startable(self) -> None:
        """The corpus consequence: no ``no_build_time`` failure is reachable."""
        for key, row in harness.load_seed()["maps"][0]["items"].items():  # type: ignore[index]
            with self.subTest(key=key):
                self.assertIsNotNone(build_time(int(row[0])))


class DerivedDurationTests(unittest.TestCase):
    """The countdown is derived from committed content, never from a client."""

    def test_a_client_supplied_duration_is_ignored(self) -> None:
        """Design D2: the extra keys cannot reach the legacy command."""
        index = DURATION_INDEX
        before_items = copy.deepcopy(map_items())
        before_row = row_of(before_items, index)
        response = construct(
            dict(
                intent(index, ACTION_START),
                duration=1,
                duration_seconds=1,
                cp=1,
                build_time=1,
                activation=1,
                time=1,
                countdown=1,
                resources_changed=[0, 0, 0, 0, 0, 0, 500, 0],
                price=[0, 0, 0, 0, 0, 0, 500, 0],
                resources={"cash": 999999},
                count=99,
                clicks_to_build=99,
                result="hacked",
                previous=[0, 0, 0, 0, 0, [], {}, 0],
                row=[0, 0, 0, 0, 0, [], {}, 0],
                action_after="hacked",
            )
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["result"], "success")
        # The server's own derivation wins: the committed build time, not the
        # client's 1.
        self.assertEqual(payload["previous"], before_row)
        self.assertEqual(payload["row"][6]["cp"], build_time(int(before_row[0])))
        self.assertNotEqual(payload["row"][6]["cp"], 1)
        # The action is the server's resolved vocabulary value.
        self.assertEqual(payload["action"], ACTION_START)
        # No mint: the neutral vector left every resource alone.
        self.assertEqual(
            payload["resources"], BOOT.resources(PID)  # type: ignore[union-attr]
        )
        assert_only_touched(self, before_items, index)
        self.assertEqual(corpus_save()["playerInfo"]["cash"], 5)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_response_row_always_records_the_accessors_duration(self) -> None:
        index = ACCESSOR_INDEX
        response = construct(intent(index, ACTION_START))
        self.assertEqual(response.status_code, 200)
        row = response.get_json()["row"]
        self.assertEqual(row[6]["cp"], build_time(int(row[0])))

    def test_a_derived_non_positive_duration_would_be_a_500_not_a_command(self) -> None:
        """Belt and braces on the accessor.

        ``item_build_time`` already refuses a non-positive value, so the
        ``no_build_time`` path is the one a caller sees.  The
        ``invalid_duration`` branch is a second, content-unreachable refusal;
        the derivation's own refusal is asserted here so a future refactor
        cannot delete the guard, and the endpoint's mapping of it is a 500
        because it would be a server-side derivation failure rather than a
        client mistake.
        """
        self.assertEqual(compat_service.ERROR_INVALID_DURATION, "invalid_duration")
        with self.assertRaises(construction_envelope.EnvelopeError) as caught:
            construction_envelope.build_envelope_start(item_index=FIXTURE_INDEX, duration=0)
        self.assertEqual(caught.exception.code, "invalid_duration")
        source = Path_read_text(compat_service.__file__)
        self.assertIn('failure.code == "invalid_duration"', source)
        self.assertIn("500, ERROR_INTERNAL, failure.code", source)

    def test_a_click_and_a_completion_never_derive_a_duration(self) -> None:
        """Only ``start`` reads committed build time, so only it can fail
        ``no_build_time``."""
        index = NO_BUILD_TIME_INDEX
        for action in (ACTION_CLICK, ACTION_FINISH):
            with self.subTest(action=action):
                response = post_with_unresolvable_build_time(index, intent(index, action))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["action"], action)
        # The same row's start, by contrast, fails closed before execution.
        self.assertEqual(
            post_with_unresolvable_build_time(
                index, intent(index, ACTION_START)
            ).status_code,
            400,
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class NoBuildTimeTests(unittest.TestCase):
    """A row that cannot be started is never handed a coerced duration (D3)."""

    def setUp(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.before_store = copy.deepcopy(BOOT.map_store(PID))  # type: ignore[union-attr]

    def test_a_placement_with_no_build_time_fails_closed(self) -> None:
        index = NO_BUILD_TIME_INDEX
        addressed = int(self.before_items[str(index)][0])
        response = post_with_unresolvable_build_time(index, intent(index, ACTION_START))
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "no_build_time")
        self.assertIn(str(addressed), body["error"]["message"])
        # Never a partial payload.
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(set(body["error"]), {"code", "message"})
        # The dispatcher never ran: the corpus is untouched, and in particular
        # the row's attribute bag was **not** cleared (that is what a
        # non-positive duration would do to it).
        self.assertEqual(harness.save_hashes(CORPUS), self.before_hashes)  # type: ignore[arg-type]
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), self.before_store)  # type: ignore[union-attr]
        self.assertEqual(map_items()[str(index)], self.before_items[str(index)])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_omitted_clearing_branch_is_never_reachable(self) -> None:
        """Design D6 as a behavior, not a comment.

        With the build time unresolvable the endpoint answers
        ``no_build_time`` instead of sending a non-positive duration, and the
        row's bag survives: the two ways legacy would clear it (a resolved zero
        and a clearing ``activate``) are both refused.
        """
        index = NO_BUILD_TIME_INDEX
        with self.assertRaises(construction_envelope.EnvelopeError) as caught:
            construction_envelope.build_envelope_start(item_index=index, duration=0)
        self.assertEqual(caught.exception.code, "invalid_duration")
        self.assertEqual(
            post_with_unresolvable_build_time(index, intent(index, ACTION_START))
            .get_json()["error"]["code"],
            "no_build_time",
        )
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_error_constant_and_code_are_the_documented_ones(self) -> None:
        self.assertEqual(compat_service.ERROR_NO_BUILD_TIME, "no_build_time")


class ConstructionFailClosedTests(unittest.TestCase):
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
                CLIENT.post("/v0/construction"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/construction", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/construction", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/construction", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {"item_index": FIXTURE_INDEX, "action": ACTION_START}
        self.assert_fail_closed(construct({}), 400, "missing_user_id")
        self.assert_fail_closed(
            construct({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            construct({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            construct({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(
            construct({"user_id": "ghost", **base}), 404, "unknown_user_id"
        )

    def test_item_index_failures(self) -> None:
        self.assert_fail_closed(
            construct({"user_id": PID, "action": ACTION_START}),
            400,
            "missing_item_index",
        )
        for bad in ("11", 11.0, True, None, [11]):
            with self.subTest(item_index=bad):
                self.assert_fail_closed(
                    construct(
                        {"user_id": PID, "item_index": bad, "action": ACTION_START}
                    ),
                    400,
                    "invalid_item_index",
                )

    def test_an_unknown_item_index_fails_closed(self) -> None:
        """Legacy would log an error, return early, and still persist.

        The endpoint answers a structured 404 instead, so a stale index can
        never be reported as a successful construction (design D3).
        """
        for index in (0, 41, 999999999, -1):
            for action in (ACTION_START, ACTION_CLICK, ACTION_FINISH):
                with self.subTest(item_index=index, action=action):
                    response = construct(intent(index, action))
                    self.assert_fail_closed(response, 404, "unknown_item_index")
                    self.assertIn(str(index), response.get_json()["error"]["message"])

    def test_an_unresolvable_index_rewrites_no_row(self) -> None:
        before = copy.deepcopy(map_items())
        self.assert_fail_closed(
            construct(intent(41, ACTION_CLICK)), 404, "unknown_item_index"
        )
        self.assertEqual(map_items(), before)

    def test_a_missing_action_fails_closed(self) -> None:
        self.assert_fail_closed(
            construct({"user_id": PID, "item_index": FIXTURE_INDEX}),
            400,
            "missing_action",
        )
        # Present but null is not an action: nothing is coerced.
        self.assert_fail_closed(
            construct(
                {"user_id": PID, "item_index": FIXTURE_INDEX, "action": None}
            ),
            400,
            "invalid_action",
        )

    def test_a_non_string_action_fails_closed(self) -> None:
        for bad in (0, 1, True, ["start"], {"action": "start"}):
            with self.subTest(action=bad):
                self.assert_fail_closed(
                    construct(
                        {
                            "user_id": PID,
                            "item_index": FIXTURE_INDEX,
                            "action": bad,
                        }
                    ),
                    400,
                    "invalid_action",
                )

    def test_an_action_outside_the_documented_set_fails_closed(self) -> None:
        for bad in (
            "Start",  # case matters
            "start ",
            "activate",  # a legacy command name is not an action
            "add_click",
            "activate_item_click",
            "cancel",  # the clearing branch is never offered (design D6)
            "upgrade",
            "build",
            "construct",
            "",
        ):
            with self.subTest(action=bad):
                self.assert_fail_closed(
                    construct(intent(FIXTURE_INDEX, bad)), 400, "invalid_action"
                )

    def test_the_action_error_names_the_documented_set(self) -> None:
        message = construct(intent(FIXTURE_INDEX, "cancel")).get_json()["error"][
            "message"
        ]
        for action in sorted(construction_envelope.ACTIONS):
            self.assertIn(action, message)

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(compat_service.ERROR_MISSING_ACTION, "missing_action")
        self.assertEqual(compat_service.ERROR_INVALID_ACTION, "invalid_action")
        self.assertEqual(compat_service.ERROR_NO_BUILD_TIME, "no_build_time")
        self.assertEqual(compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index")
        self.assertEqual(compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_PAYLOAD, "invalid_payload")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")


class PostExecutionProofTests(unittest.TestCase):
    """Design D3: each action's post-condition is proved or the answer is 500."""

    def test_a_start_without_the_derived_countdown_is_a_500(self) -> None:
        index = PROOF_START_MISSING_CP
        response = post_only(index, _without_countdown, intent(index, ACTION_START))
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("countdown", body["error"]["message"])
        # The real dispatcher ran, so the row really was started even though
        # the service refused to claim it.
        self.assertEqual(
            map_items()[str(index)][6], {"cp": build_time(929)}  # the Bridge
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_start_with_the_wrong_countdown_is_a_500(self) -> None:
        index = PROOF_START_WRONG_CP
        response = post_only(index, _wrong_countdown, intent(index, ACTION_START))
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        # The message names both the observed and the derived countdown, so the
        # failure is reported rather than hidden.
        self.assertIn("countdown", body["error"]["message"])
        self.assertIn("3600", body["error"]["message"])
        self.assertIn(str(build_time(929)), body["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_click_without_a_counter_is_a_500(self) -> None:
        index = PROOF_CLICK_MISSING_NC
        response = post_only(index, _without_counter, intent(index, ACTION_CLICK))
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("click counter", body["error"]["message"])
        # The real dispatcher ran: the counter really was raised.
        self.assertEqual(map_items()[str(index)][6], {"nc": 1})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_click_whose_counter_is_zero_is_a_500(self) -> None:
        index = PROOF_CLICK_ZERO_NC
        response = post_only(index, _zero_counter, intent(index, ACTION_CLICK))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        self.assertIn("at least 1", response.get_json()["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_click_whose_counter_is_not_an_integer_is_a_500(self) -> None:
        index = PROOF_CLICK_STRING_NC
        response = post_only(index, _string_counter, intent(index, ACTION_CLICK))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        self.assertIn("integer", response.get_json()["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_completion_that_kept_the_counter_is_a_500(self) -> None:
        index = PROOF_FINISH_KEPT_NC
        BOOT.execute_commands(  # type: ignore[union-attr]
            PID, construction_envelope.build_envelope_click(item_index=index)
        )
        response = post_only(index, _counter_kept, intent(index, ACTION_FINISH))
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("still carries the click counter", body["error"]["message"])
        # The real dispatcher ran, so the counter really was deleted.
        self.assertNotIn("nc", map_items()[str(index)][6])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_the_legacy_dispatcher_destroyed_is_a_500_not_a_success(self) -> None:
        """The row-survival half of the proof.

        No construction command can remove a row, so the stub reproduces a
        post-state legacy could never report; the endpoint must refuse it anyway
        rather than trust the legacy success status.
        """
        index = PROOF_ROW_ABSENT
        response = post_with_absent_survivor(index, intent(index, ACTION_CLICK))
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("keep the placement entry", body["error"]["message"])
        # Not a success and not a partial payload.
        self.assertNotIn("row", body)
        self.assertNotIn("result", body)
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_without_an_attribute_bag_is_a_500(self) -> None:
        index = PROOF_NO_BAG
        response = post_only(index, _no_attribute_bag, intent(index, ACTION_CLICK))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        self.assertIn("attribute bag", response.get_json()["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_that_stopped_being_eight_fields_is_a_500(self) -> None:
        index = PROOF_NOT_EIGHT
        response = post_only(index, _not_eight_fields, intent(index, ACTION_CLICK))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        self.assertIn("eight-field", response.get_json()["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_the_service_cannot_report_is_a_500_before_execution(self) -> None:
        """A non-list row fails closed before the dispatcher ever runs."""
        index = PROOF_UNREPORTABLE
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        BOOT.map_item = lambda user_id, key: "not a row"  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post(
                    "/v0/construction", json=intent(index, ACTION_CLICK)
                )
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        # Nothing ran: the row is untouched.
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_legacy_execution_raising_is_a_500(self) -> None:
        """A dispatcher failure after validation passed is a structured 500."""
        index = PROOF_RAISING
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.execute_commands  # type: ignore[union-attr]
        before = copy.deepcopy(map_items())

        def explode(user_id, envelope):
            raise RuntimeError("legacy blew up")

        BOOT.execute_commands = explode  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post(
                    "/v0/construction", json=intent(index, ACTION_CLICK)
                )
        finally:
            BOOT.execute_commands = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("RuntimeError", body["error"]["message"])
        self.assertEqual(map_items(), before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)


class ConstructionContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_constructions(self) -> None:
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

    def test_constructions_never_touch_working_tree_saves(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        before_items = copy.deepcopy(map_items())
        response = construct(intent(PERSIST_INDEX, ACTION_CLICK))
        self.assertEqual(response.status_code, 200)
        # The corpus save changed; the working tree did not move.
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        assert_only_touched(self, before_items, PERSIST_INDEX)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_legacy_accessors_agree_with_the_map(self) -> None:
        self.assertTrue(BOOT.has_map_item(PID, ALIAS_INDEX))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 0))  # type: ignore[union-attr]
        row = BOOT.map_item(PID, ALIAS_INDEX)  # type: ignore[union-attr]
        self.assertIsInstance(row, list)
        self.assertEqual(len(row), 8)  # type: ignore[arg-type]
        self.assertEqual(
            row, BOOT.map_items(PID)[str(ALIAS_INDEX)]  # type: ignore[union-attr]
        )
        self.assertIsNone(BOOT.map_item(PID, 41))  # type: ignore[union-attr]

    def test_a_construction_leaves_the_other_fixtures_rows_alone(self) -> None:
        """The fixtures stay independently readable (design D10).

        The construction fixture targets slot 11 and the move fixture
        repositions that same row in its own independent transaction; the
        upgrade (12), sell (20), and store (2) fixtures use other rows, which
        this endpoint must never touch.
        """
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        before_items = copy.deepcopy(map_items())
        for other in FIXTURE_FOREIGN_ROWS:
            with self.subTest(key=other):
                self.assertEqual(before_items[other], seed_items[other])
        start_row = row_of(before_items, FIXTURE_INDEX)
        response = construct(intent(FIXTURE_INDEX, ACTION_START))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["previous"], start_row)
        self.assertEqual([payload["row"][1], payload["row"][2]], list(FIXTURE_ANCHOR))
        self.assertEqual(payload["row"][6], {"cp": FIXTURE_BUILD_TIME})
        for other in FIXTURE_FOREIGN_ROWS:
            self.assertEqual(map_items()[other], seed_items[other])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_response_never_aliases_the_live_row(self) -> None:
        """``previous`` must be a copy: legacy mutates that very list."""
        before = row_of(map_items(), ALIAS_INDEX)
        response = construct(intent(ALIAS_INDEX, ACTION_CLICK))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNot(payload["previous"], map_items()[str(ALIAS_INDEX)])
        self.assertIsNot(payload["row"], map_items()[str(ALIAS_INDEX)])
        self.assertEqual(payload["previous"], before)


class ConstructionSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/construction")  # type: ignore[union-attr]
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
            unknown = CLIENT.get("/v0/construction/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


def Path_read_text(module_file) -> str:
    """A module's own source, for the published-constant checks."""
    from pathlib import Path as _Path

    return _Path(module_file).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
