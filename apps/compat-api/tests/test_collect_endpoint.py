#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/collect`` behavior tests (OpenSpec task 2.3).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection.  The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across collection
execution.

Every test snapshots the corpus map at its own start and asserts its
post-condition against that snapshot, so the suite is order-independent.
Mutating tests take dedicated rows, and no test asserts an absolute
resource balance after another test may already have moved it.

Covered:

* **a successful collection** — the derived payout lands in exactly the slot
  the addressed item's committed ``collect_type`` names plus the experience
  slot, the row's collection instant moves **strictly forward**, the response
  carries both rows, the derived ``payout``, the ladder ``tier``, the
  ``reference_time``, and the current ``resources``, and the persisted row is
  exactly what the response reported.
* **the two-part post-execution proof** — a vanished row, a row that stopped
  being eight fields, a non-integer collection instant, a collection instant
  that did not move forward, a shortened resource movement, a resource that
  moved when the derived payout says zero, and a resource that did not move
  each fail closed with ``internal_error`` rather than reporting legacy's
  success.  Each is exercised by a stub that lets the real dispatcher run and
  only rewrites the **post**-execution read.
* **the five content/guard refusals** — ``construction_in_progress`` (a row
  carrying ``cp`` or ``nc``, exercised for real against a row seeded by the
  delivered construction derivation), ``too_early`` (a stubbed instant, because
  no corpus row has a recent one), ``capped_collection``, ``unknown_collect_type``
  and ``no_income`` (stubbed accessors, because every corpus item records a cap
  of ``0``, a committed type, and — for 39 of the 40 placed rows — a zero
  amount).  Every one leaves the corpus **byte-identical**.
* **the derived, not client-supplied, payout** — a request carrying ``amount``,
  ``resource``, ``tier``, ``time``, ``price``, ``resources_changed``,
  ``collect``, ``collect_type``, ``collect_xp``, and ``max_collects`` changes
  nothing: the server's own derivation wins.
* **fail-closed paths** — every structurally unresolvable input in the spec
  returns its documented structured error with the corpus byte-unchanged and no
  row rewritten.
* **session/bootstrap byte-identity** is retained after collections, and the
  legacy accessors agree with the persisted map.
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import compat_test_harness as harness

import collect_envelope
import compat_legacy
import compat_service

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The fixture row: the collect fixture's Tree at map slot 2.  The store fixture
# targets the same row in its own independent transaction, so this suite only
# ever compares it against its own snapshot.
FIXTURE_INDEX = 2
FIXTURE_ITEM_ID = 905  # Tree
FIXTURE_ANCHOR = (53, 39)
FIXTURE_COLLECT_AMOUNT = 20
FIXTURE_COLLECT_TYPE = "w"
FIXTURE_COLLECT_XP = 1

# The corpus's only income-bearing rows are the nine decorations — the Tree at
# slot 2 and the eight forest rows at slots 21-28 — because the real factories
# are not placed (a recorded claim limit, not an accident).  That is fewer rows
# than this suite has mutating tests, so each test that needs a pristine
# income-bearing row calls :func:`reset_row` first: the row is restored to the
# committed seed's ``item[3] == 0`` and ``attr == {}`` **in the live in-memory
# save** before its own snapshot, so every test stays order-independent and
# asserts against the state it actually started from.  Restoring is test setup,
# never a claim about legacy behavior: the collection itself is always executed
# by the unchanged legacy dispatcher.
INCOME_ROWS = tuple(range(21, 29))
# Rows with **no** committed income, used only where the test refuses before the
# income is ever read (an unreadable row) or never needs it.
NO_INCOME_INDEX = 3  # Wall I
ALIAS_INDEX = 4  # Wall I: accessor checks only

RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")


def reset_row(index: int, instant: int = 0, attr: Optional[Dict[str, int]] = None) -> None:
    """Restore a row to the committed seed's shape, in memory **and** on disk.

    The seed records every row with ``item[3] == 0`` and ``attr == {}``, which
    is what makes the top ladder rung deterministic and the construction-state
    refusal unreachable.  A test that has already collected or built a row
    resets it here so its own snapshot is the state it means to assert about.

    Both representations are updated: the endpoint reads the **in-memory** save
    through the legacy accessors, while this suite's post-execution assertions
    read the **persisted** corpus file, and the only thing that keeps the two in
    step during normal operation is the legacy dispatcher persisting the whole
    save after each batch.  So the reset rewrites the disposable corpus file
    from the same in-memory document — a test-only, contained mechanism, never a
    claim about legacy behavior, and never touching a working-tree save.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    row = save["maps"][0]["items"][str(index)]
    row[3] = instant
    row[6] = {} if attr is None else dict(attr)
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


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
    # collection execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a collection execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def collect_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/collect", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def map_items() -> Dict[str, Any]:
    return corpus_save()["maps"][0]["items"]  # type: ignore[index]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def ladder() -> Any:
    return BOOT.collect_ladder()  # type: ignore[union-attr]


def intent(index: int) -> Dict[str, Any]:
    return {"user_id": PID, "item_index": index}


def row_of(items: Dict[str, Any], index: int) -> List[Any]:
    return list(items[str(index)])


def item_of(items: Dict[str, Any], index: int) -> int:
    return int(items[str(index)][0])


def pristine(index: int, instant: int = 0, attr: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Reset a row to its committed shape and snapshot the map around it.

    Returns the post-reset map snapshot, so a test's own assertions are made
    against the state it actually started from.  The corpus save file is **not**
    re-persisted here: only an executing ``command()`` writes it, and every
    refusal test proves the file is byte-identical across its request, which is
    exactly the property under test.
    """
    reset_row(index, instant, attr)
    return copy.deepcopy(map_items())


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
    # No key is added or removed: a collection never creates or destroys a
    # placement.
    case.assertEqual(len(after_items), len(before_items))
    for other in before_items:
        if other == key:
            continue
        with case.subTest(key=other):
            case.assertEqual(after_items[other], before_items[other])


def _row_rewritten_after_execution(index: int, transform: Callable[[List[Any]], Any]):
    """A ``map_item`` stub that rewrites only the **post**-execution read.

    The endpoint reads the row once before execution (for ``previous``) and
    once after (for ``row``).  Rewriting only the second read is what lets each
    clause of the two-part proof be exercised in isolation: the row the real
    dispatcher actually persisted is replaced with one that violates exactly
    that clause, so exactly one clause can fail.
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


def _resources_rewritten_after_execution(transform: Callable[[Dict[str, int]], Dict[str, int]]):
    """A ``resources`` stub that rewrites only the **post**-execution read.

    The endpoint reads the pre-execution resources before dispatch (for the
    value-level proof) and again afterwards (for the response).  Rewriting only
    the second read is what lets each resource clause of the proof fail on its
    own while the real dispatcher still wrote the true movement to the save.
    """
    original = BOOT.resources  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, int]:
        state["seen"] += 1
        if state["seen"] == 1:
            return original(user_id)
        return transform(original(user_id))

    return stub


def _with_stamp(row: List[Any], stamp: Any) -> List[Any]:
    """A row whose recorded collection instant is replaced."""
    return list(row[:3]) + [stamp] + list(row[4:])


def _not_eight_fields(row: List[Any]) -> List[Any]:
    """A row that stopped being an eight-field entry."""
    return list(row[:7])


def _stalled_stamp(row: List[Any]) -> List[Any]:
    """A collection instant that did not move strictly forward.

    The pre-execution instant is the committed ``0`` (every corpus row starts
    there), so echoing it back is the strongest form of "not strictly forward":
    the branch reported the same clock reading it started with.
    """
    return _with_stamp(row, 0)


def _not_an_int_stamp(row: List[Any]) -> List[Any]:
    """A collection instant that is not an integer."""
    return _with_stamp(row, "1790000000")


def _absent_after_execution(index: int):
    """A ``has_map_item`` stub: resolves before, absent after.

    The endpoint resolves the index once before executing and once after, so a
    two-call stub reproduces the post-state a destroyed row would leave behind
    without touching the real legacy dispatcher.  No collect branch can do
    that — it writes only ``item[3]`` — which is exactly why the proof exists
    and must fail closed.
    """
    original = BOOT.has_map_item  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str, key: int) -> bool:
        if key != index:
            return original(user_id, key)
        state["seen"] += 1
        return state["seen"] == 1

    return stub


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


def post_with_map_item_stub(
    index: int, transform: Callable[[List[Any]], Any], payload: Dict[str, Any]
) -> Result:
    """Run one intent against a ``BOOT`` whose post read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.map_item  # type: ignore[union-attr]
    BOOT.map_item = _row_rewritten_after_execution(index, transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/collect", json=payload))
    finally:
        BOOT.map_item = original  # type: ignore[assignment]


def post_with_resources_stub(
    transform: Callable[[Dict[str, int]], Dict[str, int]], payload: Dict[str, Any]
) -> Result:
    """Run one intent against a ``BOOT`` whose post resource read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.resources  # type: ignore[union-attr]
    BOOT.resources = _resources_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/collect", json=payload))
    finally:
        BOOT.resources = original  # type: ignore[assignment]


def post_with_absent_survivor(index: int, payload: Dict[str, Any]) -> Result:
    """Run one intent against a ``BOOT`` whose row vanishes after execution."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.has_map_item  # type: ignore[union-attr]
    BOOT.has_map_item = _absent_after_execution(index)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/collect", json=payload))
    finally:
        BOOT.has_map_item = original  # type: ignore[assignment]


def post_with_accessor(
    name: str, transform, payload: Dict[str, Any]
) -> Result:
    """Run one intent against a ``BOOT`` whose content accessor is stubbed.

    The three content refusals (``capped_collection``,
    ``unknown_collect_type``, ``no_income``) are **content-unreachable against
    the committed corpus**: every placed item records ``max_collects "0"``, a
    ``collect_type`` inside the committed vocabulary, and — for 39 of the 40
    rows — a ``collect`` of ``"0"``.  Each is therefore exercised by stubbing
    the *accessor* to return the fail-closed input the endpoint must refuse
    before the dispatcher runs, exactly as the delivered construction line
    stubs ``item_build_time`` for its ``no_build_time`` path.  The accessors'
    own rules are covered against the real configuration by
    :class:`ItemIncomeAccessorTests`.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = getattr(BOOT, name)  # type: ignore[union-attr]
    key = str(int(payload["item_index"]))
    addressed = int(map_items()[key][0]) if key in map_items() else None
    if addressed is None:
        # An index that names no row: the addressability check must answer
        # first, so the content accessor is never consulted.  The stub is a
        # tripwire that raises if it ever is.
        def tripwire(item_id: int) -> None:
            raise AssertionError(
                "the content accessor was consulted for an index that names no row"
            )

        setattr(BOOT, name, tripwire)  # type: ignore[union-attr]
    else:
        setattr(BOOT, name, transform(original, addressed))  # type: ignore[union-attr]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/collect", json=payload))
    finally:
        setattr(BOOT, name, original)  # type: ignore[union-attr]


def capped(amount: Optional[int] = 25):
    """An accessor stub returning a non-zero cap for the addressed item."""

    def transform(original, addressed: int):
        def stub(item_id: int) -> Optional[int]:
            if int(item_id) == addressed:
                return amount
            return original(item_id)

        return stub

    return transform


def typed(resource_type: Optional[str]):
    """An accessor stub returning an uncommitted collect type."""

    def transform(original, addressed: int):
        def stub(item_id: int) -> Optional[str]:
            if int(item_id) == addressed:
                return resource_type
            return original(item_id)

        return stub

    return transform


def income(amount: Optional[int]):
    """An accessor stub returning a resolved (or unusable) amount."""

    def transform(original, addressed: int):
        def stub(item_id: int) -> Optional[int]:
            if int(item_id) == addressed:
                return amount
            return original(item_id)

        return stub

    return transform


def post_with_stubbed_instant(index: int, instant: int, payload: Dict[str, Any]) -> Result:
    """Run one intent against a ``BOOT`` whose row carries a stubbed instant.

    The endpoint reads the row's ``item[3]`` through ``map_item`` — once before
    dispatch (to compute the elapsed time) and once after (for the proof).  The
    stub rewrites **only the first** read, so the post-execution read is the
    row the real dispatcher persisted.  That is what makes a ``too_early``
    refusal reachable: no corpus row carries a recent instant, and a stub on
    both reads would also break the "moved strictly forward" proof for a
    collection that legitimately succeeds at the boundary.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.map_item  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str, key: int):
        row = original(user_id, key)
        if key != index or not isinstance(row, list):
            return row
        state["seen"] += 1
        return _with_stamp(list(row), instant) if state["seen"] == 1 else list(row)

    BOOT.map_item = stub  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/collect", json=payload))
    finally:
        BOOT.map_item = original  # type: ignore[assignment]


def post_with_stubbed_clock(reference_time: int, payload: Dict[str, Any]) -> Result:
    """Run one intent against a ``BOOT`` whose own clock is stubbed.

    The rung the endpoint derives depends on ``now`` (design D1), so the
    lower rungs are covered by pinning the service's clock rather than by
    waiting five minutes.  Every corpus row's ``item[3]`` is ``0``, so an
    absolute reference time selects the rung deterministically.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.server_time  # type: ignore[union-attr]
    BOOT.server_time = lambda: reference_time  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/collect", json=payload))
    finally:
        BOOT.server_time = original  # type: ignore[assignment]


def seed_construction_state(index: int, attr: Dict[str, int]) -> None:
    """Give a row construction state the way the real build commands do.

    The row is reset to the committed seed's shape first, then the delivered
    construction derivation's own commands are executed against the
    **unchanged legacy dispatcher**: ``activate`` writes ``item[3]`` and
    ``item[6]["cp"]``, and ``add_click`` raises ``item[6]["nc"]``.  Design D5's
    refusal is therefore exercised against state legacy really wrote, not a
    hand-made save.  Naming only one of the two keys seeds only that one, so
    the ``nc``-only case is real too.
    """
    reset_row(index)
    if "cp" in attr:
        BOOT.execute_commands(  # type: ignore[union-attr]
            PID,
            {
                "first_number": 0,
                "publishActions": [],
                "ts": 1700000000,
                "tries": 1,
                "accessToken": "",
                "commands": [[0, "activate", [index, attr["cp"]], [0] * 8]],
            },
        )
    if "nc" in attr:
        # ``add_click`` raises the counter by one per call and seeds it to 1
        # when absent (engine.py:125-130), so the requested count is reached by
        # issuing that many clicks — each with the **neutral** vector, because
        # the counter is a construction counter, not a price.
        for _ in range(attr["nc"]):
            BOOT.execute_commands(  # type: ignore[union-attr]
                PID,
                {
                    "first_number": 0,
                    "publishActions": [],
                    "ts": 1700000000,
                    "tries": 1,
                    "accessToken": "",
                    "commands": [[0, "add_click", [index], [0] * 8]],
                },
            )


class CollectionSuccessTests(unittest.TestCase):
    """A successful collection, with the two-part proof satisfied for real."""

    def test_a_collection_pays_the_committed_income_and_reports_the_derivation(self) -> None:
        index = INCOME_ROWS[0]
        before_items = pristine(index)
        before = resources_now()
        before_row = row_of(before_items, index)
        self.assertEqual(before_row[3], 0)  # never collected

        response = collect_now(intent(index))

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
                "payout",
                "tier",
                "reference_time",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # The legacy result: command.php returns exactly this whenever
        # command() returns without raising.
        self.assertEqual(payload["result"], "success")

        # The row as read *before* execution.
        self.assertEqual(payload["previous"], before_row)
        self.assertEqual(len(payload["previous"]), 8)

        # The row re-read from the persisted save *after* execution.
        row = payload["row"]
        self.assertEqual(len(row), 8)
        self.assertEqual(row[0], before_row[0])  # same item
        self.assertEqual([row[1], row[2]], before_row[1:3])  # same cell
        self.assertEqual(row[4], before_row[4])  # orientation
        self.assertEqual(row[5], [])  # store
        self.assertEqual(row[6], before_row[6])  # attr: a collection adds nothing
        self.assertEqual(row[7], before_row[7])  # player team
        # The collection instant is a fresh wall-clock stamp that moved
        # strictly forward.
        self.assertIsInstance(row[3], int)
        self.assertNotIsInstance(row[3], bool)
        self.assertGreater(row[3], 0)
        self.assertGreater(row[3], before_row[3])
        # The persisted row is exactly what the response reported.
        self.assertEqual(map_items()[str(index)], row)

        # The derived payout: the committed amount in the slot its committed
        # collect_type names, plus the committed experience, both scaled by the
        # committed rung (design D1/D2), with the unread and mana slots zero
        # (design D6).
        minutes, multipliers = ladder()
        self.assertEqual(payload["tier"], len(multipliers) - 1)  # the top rung
        self.assertEqual(payload["payout"], [0, 3, 0, 60, 0, 0, 0, 0])
        item_id = item_of(before_items, index)
        self.assertEqual(
            payload["payout"][collect_envelope.COLLECT_RESOURCE_SLOTS["w"]],
            FIXTURE_COLLECT_AMOUNT * int(multipliers[payload["tier"]]),
        )
        self.assertEqual(
            payload["payout"][collect_envelope.EXPERIENCE_SLOT],
            FIXTURE_COLLECT_XP * int(multipliers[payload["tier"]]),
        )
        for index_always_zero in collect_envelope.ALWAYS_ZERO_SLOTS:
            self.assertEqual(payload["payout"][index_always_zero], 0)
        self.assertEqual(len(payload["payout"]), collect_envelope.RESOURCE_VECTOR_SLOTS)
        # And the committed content really is the item's own.
        self.assertEqual(BOOT.item_collect_amount(item_id), FIXTURE_COLLECT_AMOUNT)  # type: ignore[union-attr]
        self.assertEqual(BOOT.item_collect_type(item_id), FIXTURE_COLLECT_TYPE)  # type: ignore[union-attr]
        self.assertEqual(BOOT.item_collect_xp(item_id), FIXTURE_COLLECT_XP)  # type: ignore[union-attr]
        self.assertEqual(BOOT.item_max_collects(item_id), 0)  # type: ignore[union-attr]

        # The reference instant the elapsed time was computed against: the
        # service's own clock, and the elapsed window it implies.
        self.assertIsInstance(payload["reference_time"], int)
        self.assertGreater(payload["reference_time"], 0)
        self.assertGreaterEqual(payload["reference_time"], row[3])
        self.assertEqual(list(minutes), [5, 60, 240, 480])

        # The money: exactly the derived delta, in every stored resource.
        expected = {
            name: before[name] + payload["payout"][slot]
            for name, slot in (
                ("xp", 1),
                ("gold", 2),
                ("wood", 3),
                ("oil", 4),
                ("steel", 5),
                ("cash", 6),
                ("mana", 7),
            )
        }
        self.assertEqual(payload["resources"], expected)
        self.assertEqual(set(payload["resources"]), set(RESOURCE_NAMES))
        self.assertEqual(payload["resources"]["xp"], before["xp"] + 3)
        self.assertEqual(payload["resources"]["wood"], before["wood"] + 60)
        for name in ("gold", "oil", "steel", "cash", "mana"):
            with self.subTest(resource=name):
                self.assertEqual(payload["resources"][name], before[name])
        # The reported balances ARE the save's balances.
        self.assertEqual(corpus_save()["maps"][0]["gold"], payload["resources"]["gold"])
        self.assertEqual(corpus_save()["maps"][0]["wood"], payload["resources"]["wood"])
        self.assertEqual(corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"])
        self.assertEqual(corpus_save()["privateState"]["mana"], payload["resources"]["mana"])

        # A collection stores nothing, records no purchase, and kills nothing.
        self.assertEqual(
            corpus_save()["maps"][0]["store"], before_items is not None and corpus_save()["maps"][0]["store"]
        )
        self.assertEqual(corpus_save()["privateState"]["boughtUnits"], [])
        self.assertEqual(corpus_save()["privateState"]["deadHeroes"], {})
        # No key is added or removed; exactly one row changed.
        self.assertEqual(len(map_items()), len(before_items))
        assert_only_touched(self, before_items, index)
        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_an_immediate_repeat_is_too_early_not_a_second_payout(self) -> None:
        """A repeat within the first rung is **refused**, not paid twice.

        This is design D3 applied to a real second request rather than a stub:
        the first collection re-stamps the row's clock to now, so an immediate
        second one has reached no committed rung and must not mint a second
        payout.  The row keeps the first collection's instant and the balance
        keeps the first payout.
        """
        index = INCOME_ROWS[1]
        pristine(index)
        before = resources_now()
        first = collect_now(intent(index))
        self.assertEqual(first.status_code, 200)
        first_payload = first.get_json()
        self.assertEqual(first_payload["row"][6], {})
        stamped = first_payload["row"][3]
        self.assertGreater(stamped, 0)

        second = collect_now(intent(index))

        self.assertEqual(second.status_code, 409)
        body = second.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "too_early")
        # The row and the balance are exactly where the first collection left
        # them: no second stamp, no second payout.
        self.assertEqual(map_items()[str(index)][3], stamped)
        self.assertEqual(resources_now(), first_payload["resources"])
        self.assertEqual(resources_now()["wood"], before["wood"] + 60)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_repeat_after_a_later_rung_derives_the_lower_payout(self) -> None:
        """Once the first rung has elapsed, a repeat is a real second legacy
        command: the clock moves forward again and the payout is derived from
        the row's **own** elapsed time, so it is the first rung's quarter
        rather than the top rung the row paid before.

        The row's recorded instant is set one first-rung window in the past and
        the service uses its real clock, so this is a genuine end-to-end second
        collection rather than a stubbed one.
        """
        index = INCOME_ROWS[1]
        before_first = resources_now()
        first = collect_now(intent(index))
        self.assertEqual(first.status_code, 200)
        first_payload = first.get_json()
        self.assertEqual(first_payload["tier"], 3)
        self.assertEqual(before_first["wood"] + 60, first_payload["resources"]["wood"])

        first_rung_seconds = collect_envelope.threshold_seconds_for(0, ladder())
        past = BOOT.server_time() - first_rung_seconds  # type: ignore[union-attr]
        before_items = pristine(index, instant=past)
        before_second = resources_now()

        second = collect_now(intent(index))

        self.assertEqual(second.status_code, 200)
        payload = second.get_json()
        self.assertEqual(payload["previous"][3], past)
        self.assertEqual(payload["tier"], 0)
        # 20 x 0.25 = 5 wood, and 1 x 0.25 rounds to no experience.
        self.assertEqual(payload["payout"], [0, 0, 0, 5, 0, 0, 0, 0])
        self.assertEqual(payload["resources"]["wood"], before_second["wood"] + 5)
        self.assertEqual(payload["resources"]["xp"], before_second["xp"])
        # The clock moved strictly forward from the row's own prior instant.
        self.assertGreater(payload["row"][3], past)
        self.assertEqual(map_items()[str(index)], payload["row"])
        assert_only_touched(self, before_items, index)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_every_income_bearing_corpus_row_collects_the_same_way(self) -> None:
        """The corpus's only income-bearing rows are the decorations, and each
        of them pays the same derived top-rung vector."""
        for index in INCOME_ROWS:
            with self.subTest(index=index):
                before_items = pristine(index)
                before = resources_now()
                response = collect_now(intent(index))
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(payload["payout"], [0, 3, 0, 60, 0, 0, 0, 0])
                self.assertEqual(payload["tier"], 3)
                self.assertEqual(payload["resources"]["wood"], before["wood"] + 60)
                self.assertEqual(payload["resources"]["xp"], before["xp"] + 3)
                assert_only_touched(self, before_items, index)

    def test_each_rung_is_reachable_against_the_service_own_clock(self) -> None:
        """The lower rungs, covered by pinning ``now`` rather than waiting.

        Every corpus row's ``item[3]`` is ``0``, so an absolute reference time
        selects the rung deterministically: 299 seconds reaches none (the
        ``too_early`` refusal, covered in :class:`ContentRefusalTests`), 300 the
        first, 3600 the second, 14400 the third, 28800 the fourth, and a
        billionth second stays clamped at the top.  The committed global is in
        **minutes**, so the boundaries are 300/3600/14400/28800 **seconds**.
        """
        minutes, multipliers = ladder()
        seconds = [
            collect_envelope.threshold_seconds_for(tier, ladder())
            for tier in range(len(multipliers))
        ]
        self.assertEqual(list(minutes), [5, 60, 240, 480])
        self.assertEqual(list(multipliers), [0.25, 1, 2, 3])
        self.assertEqual(seconds, [300, 3600, 14400, 28800])
        cases = list(zip(seconds, range(len(seconds)))) + [(10 ** 9, 3)]
        for offset, (reference_time, expected_tier) in enumerate(cases):
            with self.subTest(reference_time=reference_time):
                index = INCOME_ROWS[offset % len(INCOME_ROWS)]
                before_items = pristine(index)
                before = resources_now()
                response = post_with_stubbed_clock(reference_time, intent(index))
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(payload["tier"], expected_tier)
                self.assertEqual(payload["reference_time"], reference_time)
                multiplier = multipliers[expected_tier]
                expected_payout = [0] * 8
                expected_payout[collect_envelope.EXPERIENCE_SLOT] = int(
                    FIXTURE_COLLECT_XP * multiplier
                )
                expected_payout[collect_envelope.COLLECT_RESOURCE_SLOTS["w"]] = int(
                    FIXTURE_COLLECT_AMOUNT * multiplier
                )
                self.assertEqual(payload["payout"], expected_payout)
                self.assertEqual(
                    payload["resources"]["wood"],
                    before["wood"] + expected_payout[3],
                )
                self.assertEqual(
                    payload["resources"]["xp"], before["xp"] + expected_payout[1]
                )
                assert_only_touched(self, before_items, index)

    def test_the_response_never_aliases_the_live_row(self) -> None:
        """``previous`` must be a copy: legacy mutates that very list."""
        index = INCOME_ROWS[2]
        before = row_of(pristine(index), index)
        response = collect_now(intent(index))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNot(payload["previous"], map_items()[str(index)])
        self.assertIsNot(payload["row"], map_items()[str(index)])
        self.assertEqual(payload["previous"], before)


class ItemIncomeAccessorTests(unittest.TestCase):
    """The committed-configuration resolution rules (tasks 2.2 / D4 / D6)."""

    def test_the_committed_income_fields_resolve(self) -> None:
        for name, expected in (
            ("item_collect_amount", 20),
            ("item_collect_type", "w"),
            ("item_collect_xp", 1),
            ("item_max_collects", 0),
        ):
            with self.subTest(accessor=name):
                value = getattr(BOOT, name)(FIXTURE_ITEM_ID)  # type: ignore[union-attr]
                self.assertEqual(value, expected)
                self.assertIsInstance(value, int if name != "item_collect_type" else str)
                self.assertNotIsInstance(value, bool)

    def test_a_non_resolving_id_has_no_income(self) -> None:
        """An id the loaded configuration cannot index yields ``None`` for all
        four fields, never a coerced value."""
        for bad in (999999, -1, "not an item", None):
            for name in (
                "item_collect_amount",
                "item_collect_type",
                "item_collect_xp",
                "item_max_collects",
            ):
                with self.subTest(item_id=bad, accessor=name):
                    self.assertIsNone(getattr(BOOT, name)(bad))  # type: ignore[union-attr]

    def test_a_zero_amount_is_a_real_value_not_a_refusal(self) -> None:
        """``collect "0"`` is committed content for 727 of the 778 stored
        items (39 of the 40 placed rows), so the accessor returns ``0`` and the
        endpoint's ``no_income`` refusal lives above it."""
        for item_id in (22, 23, 26, 929):
            with self.subTest(item_id=item_id):
                self.assertEqual(BOOT.item_collect_amount(item_id), 0)  # type: ignore[union-attr]
                self.assertIsNotNone(BOOT.item_collect_amount(item_id))  # type: ignore[union-attr]
        items = BOOT.config()["items"]  # type: ignore[union-attr]
        zero_bearing = [
            int(entry["id"])
            for entry in items
            if str(entry.get("collect")).strip() == "0"
        ]
        self.assertGreaterEqual(len(zero_bearing), 700)
        for item_id in zero_bearing[:20]:
            with self.subTest(item_id=item_id):
                self.assertEqual(BOOT.item_collect_amount(item_id), 0)  # type: ignore[union-attr]

    def test_no_committed_item_resolves_to_a_negative_income(self) -> None:
        """The whole-config sweep, so a negative value can never reach a
        legacy vector slot (which would be exactly the shape that exercises
        legacy's clamp)."""
        items = BOOT.config()["items"]  # type: ignore[union-attr]
        resolved = 0
        for entry in items:
            item_id = int(entry["id"])
            for name in (
                "item_collect_amount",
                "item_collect_xp",
                "item_max_collects",
            ):
                value = getattr(BOOT, name)(item_id)  # type: ignore[union-attr]
                if value is None:
                    continue
                resolved += 1
                self.assertGreaterEqual(value, 0)
        self.assertGreater(resolved, 0)

    def test_every_placed_row_of_the_committed_corpus_is_collectable(self) -> None:
        """The corpus consequence: the ``no_income`` / ``capped_collection`` /
        ``unknown_collect_type`` paths are only reachable for content the
        committed corpus does not place, which is why the endpoint's tests
        stub the accessors for them."""
        for key, row in harness.load_seed()["maps"][0]["items"].items():  # type: ignore[index]
            with self.subTest(key=key):
                item_id = int(row[0])
                self.assertEqual(BOOT.item_max_collects(item_id), 0)  # type: ignore[union-attr]
                self.assertIn(
                    BOOT.item_collect_type(item_id),  # type: ignore[union-attr]
                    collect_envelope.COLLECT_RESOURCE_SLOTS,
                )
                self.assertIsNotNone(BOOT.item_collect_xp(item_id))  # type: ignore[union-attr]

    def test_the_ladder_resolves_from_the_loaded_globals(self) -> None:
        minutes, multipliers = ladder()
        self.assertEqual(list(minutes), [5, 60, 240, 480])
        self.assertEqual(list(multipliers), [0.25, 1, 2, 3])
        self.assertEqual(len(minutes), len(multipliers))

    def test_the_corpus_decorations_are_the_only_income_rows(self) -> None:
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        income_rows = sorted(
            key
            for key, row in seed_items.items()
            if (BOOT.item_collect_amount(int(row[0])) or 0) > 0  # type: ignore[union-attr]
        )
        self.assertEqual(income_rows, ["2"] + [str(n) for n in range(21, 29)])
        for key in income_rows:
            with self.subTest(key=key):
                item_id = int(seed_items[key][0])
                self.assertEqual(BOOT.item_collect_type(item_id), "w")  # type: ignore[union-attr]
                self.assertEqual(BOOT.item_collect_xp(item_id), 1)  # type: ignore[union-attr]
                self.assertEqual(BOOT.item_collect_amount(item_id), 20)  # type: ignore[union-attr]


class DerivedPayoutTests(unittest.TestCase):
    """The payout is derived, not client-supplied (design D7)."""

    def test_client_supplied_payout_keys_are_ignored(self) -> None:
        index = INCOME_ROWS[0]
        before_items = pristine(index)
        before_row = row_of(before_items, index)
        before = resources_now()
        response = collect_now(
            dict(
                intent(index),
                amount=999999,
                amount_=999999,
                collect=999999,
                resource="gold",
                resource_type="g",
                collect_type="g",
                collect_xp=999999,
                max_collects=0,
                tier=0,
                time=1,
                now=0,
                reference_time=0,
                price=999999,
                price_type="cash",
                resources_changed=[0, 0, 999999, 0, 0, 0, 0, 0],
                resources={"wood": 999999, "cash": 999999},
                result="hacked",
                previous=[0, 0, 0, 0, 0, [], {}, 0],
                row=[0, 0, 0, 0, 0, [], {}, 0],
                payout=[0] * 8,
            )
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["result"], "success")
        # The server's own derivation wins on every field.
        self.assertEqual(payload["previous"], before_row)
        self.assertEqual(payload["payout"], [0, 3, 0, 60, 0, 0, 0, 0])
        self.assertEqual(payload["tier"], 3)
        self.assertNotEqual(payload["payout"][3], 999999)
        self.assertEqual(payload["payout"][2], 0)  # not the client's gold
        self.assertNotEqual(payload["reference_time"], 0)
        # No mint: only the derived payout landed.
        self.assertEqual(payload["resources"]["wood"], before["wood"] + 60)
        self.assertEqual(payload["resources"]["gold"], before["gold"])
        self.assertEqual(corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        assert_only_touched(self, before_items, index)

    def test_the_vector_never_carries_a_negative_slot(self) -> None:
        """A negative slot is exactly the shape that would exercise legacy's
        ``max(..., 0)`` clamp; this contract never sends one, so the clamp is
        never exercised by its own transactions."""
        for index in (INCOME_ROWS[1],):
            pristine(index)
            response = collect_now(intent(index))
            self.assertEqual(response.status_code, 200)
            payout = response.get_json()["payout"]
            for slot, value in enumerate(payout):
                with self.subTest(slot=slot):
                    self.assertIsInstance(value, int)
                    self.assertGreaterEqual(value, 0)


class ContentRefusalTests(unittest.TestCase):
    """The five content/guard refusals, each leaving the corpus byte-identical.

    ``setUp`` takes a baseline so a test that never reaches a request still has
    one; each test then **re-takes** the baseline after whatever setup it needs
    (resetting its row to the committed seed shape, or seeding construction
    state through the real dispatcher), so the "nothing changed" claim is
    always about the request under test and never about the test's own setup.
    """

    def setUp(self) -> None:
        self.baseline()

    def baseline(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.before_store = copy.deepcopy(BOOT.map_store(PID))  # type: ignore[union-attr]

    def assert_conflict(self, response: Any, code: str) -> None:
        self.assertEqual(response.status_code, 409)
        body = response.get_json()
        self.assertIsInstance(body, dict)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)
        # Never a partial payload.
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(set(body["error"]), {"code", "message"})
        # Every failure path precedes legacy execution: no mutation anywhere.
        self.assertEqual(harness.save_hashes(CORPUS), self.before_hashes)  # type: ignore[arg-type]
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), self.before_store)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_carrying_a_countdown_is_refused(self) -> None:
        """Design D5: the executed probe showed that collecting a just-started
        build overwrites the build's start instant while the countdown
        survives, and legacy answers success.  The endpoint refuses it, so the
        delivered construction timers are never corrupted."""
        index = INCOME_ROWS[0]
        seed_construction_state(index, {"cp": 3600})
        row = row_of(BOOT.map_items(PID), index)  # type: ignore[union-attr]
        self.assertEqual(row[6]["cp"], 3600)
        self.assertGreater(row[3], 0)
        build_start = row[3]
        # The snapshot is taken **after** the construction was seeded, so the
        # refusal's "nothing changed" claim is about the construction state and
        # not about the seeding this test itself performed.
        self.baseline()

        response = collect_now(intent(index))

        self.assert_conflict(response, "construction_in_progress")
        self.assertIn("cp", response.get_json()["error"]["message"])
        self.assertIn("start instant", response.get_json()["error"]["message"])
        # The build's start instant and its countdown are byte-identical.
        after = row_of(BOOT.map_items(PID), index)  # type: ignore[union-attr]
        self.assertEqual(after[3], build_start)
        self.assertEqual(after[6], {"cp": 3600})
        # The refused row keeps its construction state, so the construction
        # line can still read the countdown and the start instant.
        self.assertEqual(map_items()[str(index)], after)

    def test_a_row_carrying_a_click_counter_is_refused(self) -> None:
        """The same rule for the other construction key: ``nc`` is the counter
        ``add_click`` raises, and a row that carries one is under construction
        just as much as one carrying a countdown."""
        index = INCOME_ROWS[1]
        seed_construction_state(index, {"nc": 1})
        row = row_of(BOOT.map_items(PID), index)  # type: ignore[union-attr]
        self.assertEqual(row[6], {"nc": 1})
        build_start = row[3]
        self.baseline()

        response = collect_now(intent(index))

        self.assert_conflict(response, "construction_in_progress")
        self.assertIn("nc", response.get_json()["error"]["message"])
        after = row_of(BOOT.map_items(PID), index)  # type: ignore[union-attr]
        self.assertEqual(after[3], build_start)
        self.assertEqual(after[6], {"nc": 1})

    def test_a_row_carrying_only_a_friend_assist_entry_is_not_refused(self) -> None:
        """The refusal names exactly ``cp`` and ``nc``: a row carrying the
        friend-assist bag (a social mechanism deliberately out of scope) is not
        a row under construction."""
        index = INCOME_ROWS[2]
        pristine(index, attr={"si": {"pid": "someone"}})
        self.baseline()

        response = collect_now(intent(index))

        self.assertEqual(response.status_code, 200)
        # The bag is neither read nor cleared by a collection.
        self.assertEqual(response.get_json()["row"][6], {"si": {"pid": "someone"}})

    def test_a_recent_instant_is_too_early(self) -> None:
        """Design D3: below the first committed rung (5 **minutes** = 300
        seconds) no collection is offered and none is executed.  No corpus row
        carries a recent instant, so the row's own instant is stubbed."""
        index = INCOME_ROWS[3]
        pristine(index)
        self.baseline()
        seconds = collect_envelope.threshold_seconds_for(0, ladder())
        reference = BOOT.server_time()  # type: ignore[union-attr]
        self.assertEqual(seconds, 300)
        response = post_with_stubbed_instant(
            index, reference - (seconds - 1), intent(index)
        )

        self.assert_conflict(response, "too_early")
        message = response.get_json()["error"]["message"]
        self.assertIn(str(seconds - 1), message)
        self.assertIn(str(seconds), message)
        self.assertIn("reaches no committed ladder rung", message)

    def test_the_rung_is_reached_at_exactly_the_first_threshold(self) -> None:
        """The refusal is at the boundary: one second later the rung is
        reached and the first rung's quarter payout is paid."""
        index = INCOME_ROWS[3]
        pristine(index)
        seconds = collect_envelope.threshold_seconds_for(0, ladder())
        reference = BOOT.server_time()  # type: ignore[union-attr]
        before = resources_now()
        response = post_with_stubbed_instant(index, reference - seconds, intent(index))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["tier"], 0)
        # 20 x 0.25 = 5 wood, and 1 x 0.25 rounds to no experience.
        self.assertEqual(payload["payout"], [0, 0, 0, 5, 0, 0, 0, 0])
        self.assertEqual(payload["resources"]["wood"], before["wood"] + 5)
        self.assertEqual(payload["resources"]["xp"], before["xp"])

    def test_a_zero_elapsed_time_is_too_early(self) -> None:
        """A row stamped this very second has reached no rung at all."""
        index = INCOME_ROWS[4]
        pristine(index)
        self.baseline()
        reference = BOOT.server_time()  # type: ignore[union-attr]
        response = post_with_stubbed_instant(index, reference, intent(index))
        self.assert_conflict(response, "too_early")
        self.assertIn(
            "reaches no committed ladder rung", response.get_json()["error"]["message"]
        )

    def test_a_non_zero_cap_is_refused(self) -> None:
        """Design D4: only ``0`` is implemented; a non-zero cap is refused
        rather than interpreted, because nothing says what it limits."""
        index = INCOME_ROWS[0]
        pristine(index)
        self.baseline()
        for cap in (1, 25, 100):
            with self.subTest(cap=cap):
                response = post_with_accessor(
                    "item_max_collects", capped(cap), intent(index)
                )
                self.assert_conflict(response, "capped_collection")
                self.assertIn(str(cap), response.get_json()["error"]["message"])

    def test_an_unusable_cap_is_refused_the_same_way(self) -> None:
        """An absent or unusable cap is not treated as "no cap"."""
        index = INCOME_ROWS[1]
        pristine(index)
        self.baseline()
        for cap in (None,):
            with self.subTest(cap=cap):
                response = post_with_accessor(
                    "item_max_collects", capped(cap), intent(index)
                )
                self.assert_conflict(response, "capped_collection")

    def test_an_unmapped_collect_type_is_refused(self) -> None:
        """Design D6: refused, never coerced into an assumed resource."""
        index = INCOME_ROWS[2]
        pristine(index)
        self.baseline()
        for resource_type in ("m", "M", "energy", "", None, "wood"):
            with self.subTest(collect_type=resource_type):
                response = post_with_accessor(
                    "item_collect_type", typed(resource_type), intent(index)
                )
                self.assert_conflict(response, "unknown_collect_type")
        message = post_with_accessor(
            "item_collect_type", typed("m"), intent(index)
        ).get_json()["error"]["message"]
        for name in sorted(collect_envelope.COLLECT_RESOURCE_SLOTS):
            self.assertIn(name, message)

    def test_a_zero_or_unusable_income_is_refused(self) -> None:
        """A committed ``collect`` of ``0`` is not an income, and an absent or
        non-integer value is never coerced into one."""
        index = INCOME_ROWS[3]
        pristine(index)
        self.baseline()
        for amount in (0, None):
            with self.subTest(amount=amount):
                response = post_with_accessor(
                    "item_collect_amount", income(amount), intent(index)
                )
                self.assert_conflict(response, "no_income")
        self.assertIn(
            "no committed collection income",
            post_with_accessor("item_collect_amount", income(0), intent(index))
            .get_json()["error"]["message"],
        )

    def test_a_placed_building_with_no_income_is_refused_for_real(self) -> None:
        """The ``no_income`` refusal is **not** only stub-reachable: 39 of the
        corpus's 40 placed rows record ``collect "0"``, so a Command Center, a
        wall, a turret, or a harbour is refused against the real accessor."""
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        barren = sorted(
            int(key)
            for key, row in seed_items.items()
            if (BOOT.item_collect_amount(int(row[0])) or 0) == 0  # type: ignore[union-attr]
        )
        self.assertIn(1, barren)  # the Command Center
        index = barren[0]
        self.baseline()

        response = collect_now(intent(index))

        self.assert_conflict(response, "no_income")
        self.assertIn(str(item_of(self.before_items, index)), response.get_json()["error"]["message"])

    def test_the_refusals_precede_every_other_derivation(self) -> None:
        """A row that is both capped and under construction is refused for the
        construction state first: that is the rule that protects state, while
        the others are content refusals."""
        index = INCOME_ROWS[4]
        seed_construction_state(index, {"cp": 5})
        self.baseline()
        response = post_with_accessor(
            "item_max_collects", capped(25), intent(index)
        )
        self.assert_conflict(response, "construction_in_progress")
        # The seed is a click-free countdown, so the message names ``cp``.
        self.assertIn("cp", response.get_json()["error"]["message"])

    def test_the_error_constants_are_the_documented_ones(self) -> None:
        self.assertEqual(compat_service.ERROR_CAPPED_COLLECTION, "capped_collection")
        self.assertEqual(
            compat_service.ERROR_UNKNOWN_COLLECT_TYPE, "unknown_collect_type"
        )
        self.assertEqual(compat_service.ERROR_NO_INCOME, "no_income")
        self.assertEqual(compat_service.ERROR_TOO_EARLY, "too_early")
        self.assertEqual(
            compat_service.ERROR_CONSTRUCTION_IN_PROGRESS, "construction_in_progress"
        )
        # And every one of them is a 409 on the route, which is proven by the
        # status codes asserted above; the module docstring's error table is the
        # documented place where the mapping is written down.
        table = (Path(compat_service.__file__).read_text(encoding="utf-8"))
        for code in (
            "capped_collection",
            "unknown_collect_type",
            "no_income",
            "too_early",
            "construction_in_progress",
        ):
            with self.subTest(code=code):
                self.assertIn("``%s``" % code, table)


class CollectFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation."""

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
                CLIENT.post("/v0/collect"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/collect", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/collect", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/collect", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {"item_index": FIXTURE_INDEX}
        self.assert_fail_closed(collect_now({}), 400, "missing_user_id")
        self.assert_fail_closed(
            collect_now({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            collect_now({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            collect_now({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(
            collect_now({"user_id": "ghost", **base}), 404, "unknown_user_id"
        )

    def test_item_index_failures(self) -> None:
        self.assert_fail_closed(
            collect_now({"user_id": PID}), 400, "missing_item_index"
        )
        for bad in ("2", 2.0, True, None, [2]):
            with self.subTest(item_index=bad):
                self.assert_fail_closed(
                    collect_now({"user_id": PID, "item_index": bad}),
                    400,
                    "invalid_item_index",
                )

    def test_an_unknown_item_index_fails_closed(self) -> None:
        """Legacy would log an error, return early, and still persist.

        The endpoint answers a structured 404 instead, so a stale index can
        never be reported as a successful collection.
        """
        for index in (0, 41, 999999999, -1):
            with self.subTest(item_index=index):
                response = collect_now(intent(index))
                self.assert_fail_closed(response, 404, "unknown_item_index")
                self.assertIn(str(index), response.get_json()["error"]["message"])

    def test_an_unresolvable_index_rewrites_no_row(self) -> None:
        before = copy.deepcopy(map_items())
        self.assert_fail_closed(collect_now(intent(41)), 404, "unknown_item_index")
        self.assertEqual(map_items(), before)

    def test_the_unknown_index_is_checked_before_the_content_refusals(self) -> None:
        """A stale index naming a non-existent row is not a content question:
        the addressability check comes first, so the client is told the index is
        unknown rather than being told the building has no income."""
        response = post_with_accessor("item_collect_amount", income(0), intent(41))
        self.assert_fail_closed(response, 404, "unknown_item_index")

    def test_a_row_the_service_cannot_report_is_a_500_before_execution(self) -> None:
        """A non-list row fails closed before the dispatcher ever runs."""
        index = INCOME_ROWS[0]
        pristine(index)
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        BOOT.map_item = lambda user_id, key: "not a row"  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/collect", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("not a row this service can report", body["error"]["message"])
        # Nothing ran: the row is untouched.
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_that_is_not_eight_fields_is_a_500_before_execution(self) -> None:
        """The length check precedes every field index, so a short row is
        reported rather than raising an ``IndexError`` out of the route."""
        index = INCOME_ROWS[1]
        pristine(index)
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.map_item  # type: ignore[union-attr]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        BOOT.map_item = lambda user_id, key: [905, 53, 39, 0]  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/collect", json=intent(index))
        finally:
            BOOT.map_item = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("eight-field", body["error"]["message"])
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_legacy_execution_raising_is_a_500(self) -> None:
        """A dispatcher failure after validation passed is a structured 500."""
        index = INCOME_ROWS[2]
        before = pristine(index)
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.execute_commands  # type: ignore[union-attr]

        def explode(user_id, envelope):
            raise RuntimeError("legacy blew up")

        BOOT.execute_commands = explode  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/collect", json=intent(index))
        finally:
            BOOT.execute_commands = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("RuntimeError", body["error"]["message"])
        self.assertEqual(map_items(), before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(compat_service.ERROR_MISSING_ITEM_INDEX, "missing_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_ITEM_INDEX, "invalid_item_index")
        self.assertEqual(compat_service.ERROR_UNKNOWN_ITEM_INDEX, "unknown_item_index")
        self.assertEqual(compat_service.ERROR_INVALID_PAYLOAD, "invalid_payload")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")
        self.assertEqual(compat_service.ERROR_MISSING_USER_ID, "missing_user_id")
        self.assertEqual(compat_service.ERROR_INVALID_USER_ID, "invalid_user_id")


class PostExecutionProofTests(unittest.TestCase):
    """Design D8: both halves of the proof, or a structured 500.

    Each test resets the row it uses, runs the **real** legacy dispatcher, and
    only rewrites the **post**-execution read, so the row and the resources the
    save really holds are the true ones and the reported divergence is the only
    thing that fails.
    """

    def assert_internal(self, response: Any, fragment: str) -> None:
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn(fragment, body["error"]["message"])
        # Not a success and not a partial payload.
        self.assertNotIn("row", body)
        self.assertNotIn("result", body)
        self.assertNotIn("payout", body)
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_row_the_legacy_dispatcher_destroyed_is_a_500_not_a_success(self) -> None:
        """The row-survival half of the proof.  No collect branch can remove a
        row, so the stub reproduces a post-state legacy could never report; the
        endpoint must refuse it anyway rather than trust the legacy status."""
        index = INCOME_ROWS[0]
        pristine(index)
        response = post_with_absent_survivor(index, intent(index))
        self.assert_internal(response, "keep the placement entry")

    def test_a_row_that_stopped_being_eight_fields_is_a_500(self) -> None:
        index = INCOME_ROWS[1]
        pristine(index)
        response = post_with_map_item_stub(index, _not_eight_fields, intent(index))
        self.assert_internal(response, "eight-field")
        # The real dispatcher ran, so the row really was collected even though
        # the service refused to claim it.
        self.assertGreater(map_items()[str(index)][3], 0)

    def test_a_collection_instant_that_is_not_an_integer_is_a_500(self) -> None:
        index = INCOME_ROWS[2]
        pristine(index)
        response = post_with_map_item_stub(index, _not_an_int_stamp, intent(index))
        self.assert_internal(response, "non-integer collection instant")

    def test_a_collection_instant_that_did_not_move_forward_is_a_500(self) -> None:
        """A collection that paid an income without re-stamping its clock is
        exactly the corruption the value-level proof exists beside, so the
        structural half catches it first."""
        index = INCOME_ROWS[3]
        pristine(index)
        response = post_with_map_item_stub(index, _stalled_stamp, intent(index))
        self.assert_internal(response, "does not move strictly forward")
        # The real dispatcher moved it; the stub only rewrote the reported read.
        self.assertGreater(map_items()[str(index)][3], 0)

    def test_a_shortened_payout_is_reported_not_trusted(self) -> None:
        """The value-level half: a wood movement the derived payout does not
        explain is a reported failure, not a success.  This is the clause that
        would catch a clamp reducing a credit — the very thing a status code
        alone could never show."""
        index = INCOME_ROWS[4]
        pristine(index)
        response = post_with_resources_stub(
            lambda values: dict(values, wood=values["wood"] - 60), intent(index)
        )
        self.assert_internal(response, "resource wood")
        message = response.get_json()["error"]["message"]
        self.assertIn("derived", message)
        self.assertIn("60", message)
        # The real dispatcher applied the full derived payout to the save; the
        # stub only rewrote the reported read, so the divergence is visible in
        # the save as well as in the refusal.
        self.assertNotEqual(map_items()[str(index)][3], 0)

    def test_a_resource_the_derived_payout_leaves_alone_moving_is_a_500(self) -> None:
        """A derived vector carries zeros in five slots; if a balance the
        derivation leaves alone moves anyway, the reported resources are not
        the derived ones."""
        index = INCOME_ROWS[5]
        pristine(index)
        response = post_with_resources_stub(
            lambda values: dict(values, gold=values["gold"] + 1), intent(index)
        )
        self.assert_internal(response, "resource gold")

    def test_an_experience_that_did_not_move_is_a_500(self) -> None:
        """The experience slot is proved exactly like a resource slot: a report
        of the **pre-execution** experience is a payout that did not land."""
        index = INCOME_ROWS[6]
        pristine(index)
        response = post_with_resources_stub(
            lambda values: dict(values, xp=values["xp"] - 3), intent(index)
        )
        self.assert_internal(response, "resource xp")
        self.assertIn("the derived delta is 3", response.get_json()["error"]["message"])

    def test_a_cash_payout_never_lands_in_the_wood_slot(self) -> None:
        """The value-level proof is per *named resource*, not per slot index: a
        payout whose only payment is wood leaves cash, oil, steel, gold, and
        mana alone, and any movement in one of them is caught."""
        index = INCOME_ROWS[7]
        pristine(index)
        for name in ("cash", "mana", "oil", "steel", "gold"):
            with self.subTest(resource=name):
                response = post_with_resources_stub(
                    lambda values, moved=name: dict(values, **{moved: values[moved] + 1}),
                    intent(index),
                )
                self.assert_internal(response, "resource %s" % name)
                # Reset so the next case starts from the same row.
                pristine(index)

    def test_the_proof_source_contains_both_halves(self) -> None:
        """The endpoint reads the pre-execution resources *before* dispatch and
        requires every stored resource to move by exactly the derived delta."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        self.assertIn("resources_before = boot.resources(user_id)", source)
        self.assertIn(
            "expected = max(resources_before[name] + payout_by_name[name], 0)", source
        )
        self.assertIn("does not move strictly forward", source)
        self.assertIn("non-integer collection instant", source)
        # Both reads and the dispatcher call live inside the collect route, and
        # the pre-execution resource read precedes the dispatch.
        route = source[source.index("def v0_collect()"):]
        self.assertLess(
            route.index("resources_before = boot.resources(user_id)"),
            route.index("boot.execute_commands(user_id, envelope_payload)"),
        )
        self.assertLess(
            route.index("boot.execute_commands(user_id, envelope_payload)"),
            route.index("payout_by_name = {"),
        )


class CollectionContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_collections(self) -> None:
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

    def test_collections_never_touch_working_tree_saves(self) -> None:
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        PERSIST_INDEX = INCOME_ROWS[0]
        before_items = pristine(PERSIST_INDEX)
        response = collect_now(intent(PERSIST_INDEX))
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

    def test_a_collection_leaves_the_other_fixtures_rows_alone(self) -> None:
        """The fixtures stay independently readable (design D10).  The collect
        and store fixtures share slot 2 because each capture seeds a **fresh**
        corpus; the construction/move (11), upgrade (12), and sell (20) rows
        must be untouched here."""
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        before_items = pristine(FIXTURE_INDEX)
        for key in ("11", "12", "20"):
            with self.subTest(key=key):
                self.assertEqual(before_items[key], seed_items[key])
        response = collect_now(intent(FIXTURE_INDEX))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["previous"], seed_items[str(FIXTURE_INDEX)])
        self.assertEqual(
            [payload["row"][1], payload["row"][2]], list(FIXTURE_ANCHOR)
        )
        self.assertEqual(payload["row"][6], {})
        for key in ("11", "12", "20"):
            with self.subTest(key=key):
                self.assertEqual(map_items()[key], seed_items[key])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_endpoint_derives_the_legacy_envelope_it_sends(self) -> None:
        """One derivation: the endpoint, the fixture, and this suite build the
        same six-key envelope from the same module."""
        built = collect_envelope.build_envelope(
            item_index=FIXTURE_INDEX, vector=[0, 3, 0, 60, 0, 0, 0, 0], ts=1700000000
        )
        self.assertEqual(
            built["commands"], [[0, "collect", [2], [0, 3, 0, 60, 0, 0, 0, 0]]]
        )
        self.assertEqual(sorted(built), sorted(collect_envelope.ENVELOPE_KEYS))
        self.assertIs(compat_service.collect_envelope, collect_envelope)


class CollectionSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/collect")  # type: ignore[union-attr]
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
            unknown = CLIENT.get("/v0/collect/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_delivered_state_mutating_routes_still_exist(self) -> None:
        """This is the eighth state-mutating surface; the other seven are
        unchanged."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        for route in (
            "/v0/place",
            "/v0/purchase",
            "/v0/move",
            "/v0/sell",
            "/v0/store",
            "/v0/upgrade",
            "/v0/construction",
            "/v0/collect",
        ):
            with self.subTest(route=route):
                self.assertIn('@app.post("%s")' % route, source)

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
