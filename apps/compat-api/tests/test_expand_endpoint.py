#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/expand`` behavior tests (OpenSpec task 2.3).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection.  The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across expansion
execution.

Every test snapshots the ledger at its own start and asserts its
post-condition against that snapshot, so the suite is order-independent.
Mutating tests take dedicated expansion ids, and no test asserts an
absolute balance or an absolute ledger after another test may already
have moved it.

Covered:

* **a successful free expansion** — the committed free row derives the
  all-zero debit, the owned list grows by **exactly one** entry equal to
  the sent id **at the end** with the existing ``[35, 36, 45, 46]``
  unchanged, in order, and not deduplicated, every one of the seven
  stored resources is **unchanged**, the response carries both lists, the
  derived ``debit``, the committed ``price`` row, and the current
  ``resources``, and the persisted ledger is exactly what the response
  reported.
* **a priced expansion** — exercised by stubbing the *committed row*
  accessor with a purchasable priced row (no committed row on this corpus
  is purchasable **and** priced, so the real combination is
  content-unreachable; design D3 refuses 94 of the 98 committed rows and
  the four free ones cost nothing).  The debit lands in exactly the gold
  and cash slots as negative entries and **every** stored resource
  changes by exactly the derived debit, which is the first value-level
  assertion in this family over a **server-derived debit**.
* **the two-part post-execution proof** — a ledger that did not grow by
  exactly the sent id at the end, a ledger that was prepended to, a
  ledger whose existing entries were reordered or deduplicated, a
  shortened resource movement, a resource that moved when the derived
  debit says zero, and a resource that did not move each fail closed with
  ``internal_error`` rather than reporting legacy's success.  Each is
  exercised by a stub that lets the real dispatcher run and only rewrites
  the **post**-execution read.
* **the two guards and the two content refusals** —
  ``unknown_expansion_id`` (an out-of-range id, exercised against the
  real accessor), ``already_expanded`` (a real owned id),
  ``expansion_requirements_unmet`` (every priced committed row, exercised
  against the real accessor), and ``insufficient_resources`` (a stubbed
  priced row the balance cannot cover).  Every one leaves the corpus
  **byte-identical**.
* **the derived, not client-supplied, debit** — a request carrying
  ``coins``, ``cash``, ``price``, ``amount``, ``neighbors``,
  ``inventory_qte``, ``time``, ``price_type``, ``resources_changed``, and
  ``debit`` changes nothing: the server's own derivation wins.
* **fail-closed paths** — every structurally unresolvable input in the spec
  returns its documented structured error with the corpus byte-unchanged
  and no ledger rewritten.
* **session/bootstrap byte-identity** is retained after expansions, and
  the legacy accessors agree with the persisted map.
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import compat_test_harness as harness

import compat_legacy
import compat_service
import expand_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The fixture intent: expansion id 0, a committed free row, so the derived
# debit is the all-zero vector.  The four free indexes are the only
# purchasable ones on this corpus, and each mutating test takes a dedicated
# one after resetting the ledger to the committed value.
FREE_INDEXES = (0, 1, 2, 3)
FIXTURE_EXPANSION_ID = 0
COMMITTED_LEDGER = [35, 36, 45, 46]
# One owned id per real duplicate refusal, and the out-of-range boundary.
OWNED_INDEX = 35
OUT_OF_RANGE = (98, 99, 999, 10 ** 9)
NEGATIVE = (-1, -35, -(10 ** 9))
# Real committed rows carrying a requirement (the corpus consequence: 94 of
# 98 rows, and every id the corpus owns).
BLOCKED_INDEXES = (4, 5, 33, 36, 45, 46, 97)

RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")
SLOT_OF = {"xp": 1, "gold": 2, "wood": 3, "oil": 4, "steel": 5, "cash": 6, "mana": 7}


# The committed corpus's balances.  Restored by :func:`reset_ledger` alongside
# the ledger, so a priced test that spends gold or cash cannot make a later
# test's affordability boundary unreachable.  The corpus is shared by the whole
# module and every mutating test takes a dedicated expansion id.
COMMITTED_RESOURCES: Dict[str, int] = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}


def reset_ledger(
    expansions: List[int], resources: Optional[Dict[str, int]] = None
) -> None:
    """Restore the ledger (and optionally the balances) in memory **and** on disk.

    Legacy appends to the ledger **in place** and **no** legacy command removes
    an expansion, so a test that has already expanded a free id resets it here
    so its own snapshot is the state it means to assert about.  The committed
    corpus's ``[35, 36, 45, 46]`` is restored verbatim: the ids are never
    reordered, rewritten, or deduplicated.

    Both representations are updated: the endpoint reads the **in-memory** save
    through the legacy accessors, while this suite's post-execution assertions
    read the **persisted** corpus file, and the only thing that keeps the two
    in step during normal operation is the legacy dispatcher persisting the
    whole save after each batch.  So the reset rewrites the disposable corpus
    file from the same in-memory document — a test-only, contained mechanism,
    never a claim about legacy behavior, and never touching a working-tree
    save.
    """
    values = dict(COMMITTED_RESOURCES if resources is None else resources)
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    first_map = save["maps"][0]
    first_map["expansions"] = list(expansions)
    first_map["xp"] = values["xp"]
    first_map["gold"] = values["gold"]
    first_map["wood"] = values["wood"]
    first_map["oil"] = values["oil"]
    first_map["steel"] = values["steel"]
    save["playerInfo"]["cash"] = values["cash"]
    save["privateState"]["mana"] = values["mana"]
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
    # expansion execution this module performed.
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("an expansion execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def expand_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/expand", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def ledger_now() -> List[Any]:
    return list(BOOT.map_expansions(PID))  # type: ignore[union-attr]


def corpus_ledger() -> List[Any]:
    return list(corpus_save()["maps"][0]["expansions"])  # type: ignore[index]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def intent(expansion_id: int) -> Dict[str, Any]:
    return {"user_id": PID, "expansion_id": expansion_id}


def pristine_free(expansion_id: int) -> Dict[str, Any]:
    """Reset the ledger to the committed value and snapshot it.

    Returns the post-reset ledger, so a test's own assertions are made
    against the state it actually started from.  The corpus save file is
    **not** re-persisted here beyond the reset itself: only an executing
    ``command()`` writes it during the request under test, which is exactly
    the property under test.
    """
    reset_ledger(COMMITTED_LEDGER)
    return copy.deepcopy(ledger_now())


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


def _ledger_rewritten_after_execution(transform: Callable[[List[Any]], List[Any]]):
    """A ``map_expansions`` stub that rewrites only the **post**-execution read.

    The endpoint reads the ledger twice: once before dispatch (for the
    duplicate guard and the response's ``expansions_before``) and once after
    (for the structural half of the proof and ``expansions_after``).
    Rewriting only the second read is what lets each clause of that half be
    exercised in isolation: the ledger the real dispatcher actually persisted
    is replaced with one that violates exactly that clause, so exactly one
    clause can fail.
    """
    original = BOOT.map_expansions  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str):
        ledger = list(original(user_id))
        state["seen"] += 1
        if state["seen"] == 1:
            return ledger
        return transform(ledger)

    return stub


def _resources_rewritten_after_execution(
    transform: Callable[[Dict[str, int]], Dict[str, int]]
):
    """A ``resources`` stub that rewrites only the **post**-execution read.

    The endpoint reads the pre-execution resources before dispatch (for the
    value-level half of the proof) and again afterwards (for the response).
    Rewriting only the second read is what lets each resource clause fail on
    its own while the real dispatcher still wrote the true movement to the
    save.
    """
    original = BOOT.resources  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, int]:
        state["seen"] += 1
        if state["seen"] == 1:
            return original(user_id)
        return transform(original(user_id))

    return stub


def post_with_ledger_stub(
    transform: Callable[[List[Any]], List[Any]], payload: Dict[str, Any]
) -> Result:
    """Run one intent against a ``BOOT`` whose post ledger read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.map_expansions  # type: ignore[union-attr]
    BOOT.map_expansions = _ledger_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/expand", json=payload))
    finally:
        BOOT.map_expansions = original  # type: ignore[assignment]


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
            return Result(app, app.test_client().post("/v0/expand", json=payload))
    finally:
        BOOT.resources = original  # type: ignore[assignment]


def post_with_price_row(row: Any, payload: Dict[str, Any]) -> Result:
    """Run one intent against a ``BOOT`` whose committed row is stubbed.

    The **priced** path and the ``insufficient_resources`` refusal are
    content-unreachable against the committed corpus: under design D3 a row
    recording a positive ``neighbors`` or ``inventory_qte`` is refused, and
    the four requirement-free rows cost nothing, so no committed row is both
    purchasable *and* priced.  Each is therefore exercised by stubbing the
    *accessor* to return the fail-closed (or purchasable-priced) row the
    endpoint must handle, exactly as the delivered collect line stubs
    ``item_max_collects`` for its ``capped_collection`` path.  The accessors'
    own rules are covered against the real configuration by
    :class:`ExpansionContentAccessorTests`.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.expansion_price  # type: ignore[union-attr]
    addressed = payload["expansion_id"]
    BOOT.expansion_price = (  # type: ignore[assignment]
        lambda expansion_id: row if expansion_id == addressed else original(expansion_id)
    )
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/expand", json=payload))
    finally:
        BOOT.expansion_price = original  # type: ignore[assignment]


def free_row(coins: int = 0, cash: int = 0) -> Dict[str, int]:
    """A purchasable priced row in the committed shape."""
    return {"coins": coins, "cash": cash, "neighbors": 0, "inventory_qte": 0}


def assert_ledger_grew_by_one(
    case: unittest.TestCase,
    before: List[Any],
    after: Any,
    sent: int,
) -> None:
    """Assert the structural half of the post-execution proof."""
    case.assertEqual(after, list(before) + [sent])
    case.assertEqual(len(after), len(before) + 1)
    case.assertEqual(after[-1], sent)
    case.assertEqual(after[:-1], before)


class FreeExpansionSuccessTests(unittest.TestCase):
    """A successful free expansion, with both proof halves satisfied for real."""

    def test_the_free_row_expands_and_reports_the_whole_derivation(self) -> None:
        before_ledger = pristine_free(FIXTURE_EXPANSION_ID)
        before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        before = resources_now()
        self.assertEqual(before_ledger, COMMITTED_LEDGER)

        response = expand_now(intent(FIXTURE_EXPANSION_ID))

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
                "expansions_before",
                "expansions_after",
                "debit",
                "price",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        # The legacy result: command.php returns exactly this whenever
        # command() returns without raising.
        self.assertEqual(payload["result"], "success")

        # The ledger, both sides, and the structural proof half.
        self.assertEqual(payload["expansions_before"], before_ledger)
        self.assertEqual(
            payload["expansions_after"],
            before_ledger + [FIXTURE_EXPANSION_ID],
        )
        assert_ledger_grew_by_one(
            self, before_ledger, payload["expansions_after"], FIXTURE_EXPANSION_ID
        )
        # The persisted ledger is exactly what the response reported, read
        # from the corpus file and through the legacy accessor.
        self.assertEqual(corpus_ledger(), payload["expansions_after"])
        self.assertEqual(ledger_now(), payload["expansions_after"])
        # The response never aliases the live list: the legacy dispatcher
        # appends to that very list in place, so a by-reference read would
        # report the after-state on both sides.
        self.assertIsNot(payload["expansions_before"], payload["expansions_after"])

        # The derived debit: a free committed row derives the all-zero vector.
        self.assertEqual(payload["debit"], [0] * 8)
        self.assertEqual(len(payload["debit"]), expand_envelope.RESOURCE_VECTOR_SLOTS)
        for slot in expand_envelope.ALWAYS_ZERO_SLOTS:
            with self.subTest(slot=slot):
                self.assertEqual(payload["debit"][slot], 0)
        for slot, value in enumerate(payload["debit"]):
            with self.subTest(slot=slot):
                self.assertLessEqual(value, 0)

        # The committed schedule row the derivation came from.
        self.assertEqual(
            payload["price"],
            {"coins": 0, "cash": 0, "neighbors": 0, "inventory_qte": 0},
        )
        self.assertEqual(
            payload["price"], BOOT.expansion_price(FIXTURE_EXPANSION_ID)  # type: ignore[union-attr]
        )
        self.assertEqual(BOOT.expansion_price_count(), 98)  # type: ignore[union-attr]

        # The money: every stored resource UNCHANGED, because the derived
        # debit is the all-zero vector.  This is the value-level half of the
        # proof, and it is the only correct outcome for a free row.
        self.assertEqual(set(payload["resources"]), set(RESOURCE_NAMES))
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(payload["resources"][name], before[name])
        # The reported balances ARE the save's balances.
        self.assertEqual(corpus_save()["maps"][0]["gold"], payload["resources"]["gold"])  # type: ignore[index]
        self.assertEqual(corpus_save()["maps"][0]["wood"], payload["resources"]["wood"])  # type: ignore[index]
        self.assertEqual(corpus_save()["playerInfo"]["cash"], payload["resources"]["cash"])  # type: ignore[index]
        self.assertEqual(corpus_save()["privateState"]["mana"], payload["resources"]["mana"])  # type: ignore[index]

        # An expansion rewrites no placement at all.
        self.assertEqual(BOOT.map_items(PID), before_items)  # type: ignore[union-attr]
        self.assertEqual(len(BOOT.map_items(PID)), 40)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), {})  # type: ignore[union-attr]
        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_each_free_index_expands_identically(self) -> None:
        """The four requirement-free committed rows are the only purchasable
        ones on this corpus, and each derives the same all-zero debit."""
        for offset, expansion_id in enumerate(FREE_INDEXES):
            with self.subTest(expansion_id=expansion_id):
                before_ledger = pristine_free(expansion_id)
                before = resources_now()
                response = expand_now(intent(expansion_id))
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(
                    payload["expansions_after"], before_ledger + [expansion_id]
                )
                self.assertEqual(payload["debit"], [0] * 8)
                self.assertEqual(payload["price"]["coins"], 0)
                self.assertEqual(payload["price"]["cash"], 0)
                self.assertEqual(payload["price"]["neighbors"], 0)
                self.assertEqual(payload["price"]["inventory_qte"], 0)
                self.assertEqual(payload["resources"], before)

    def test_the_existing_ids_are_never_rewritten_or_normalized(self) -> None:
        """Design D1's second consequence: the corpus's own four ids are
        recorded as incoherent under the chosen schedule and the endpoint must
        tolerate them verbatim — same values, same order, not deduplicated,
        not rewritten, not coerced."""
        pristine_free(FIXTURE_EXPANSION_ID)
        before_ledger = ledger_now()
        self.assertEqual(before_ledger, [35, 36, 45, 46])

        response = expand_now(intent(FIXTURE_EXPANSION_ID))

        self.assertEqual(response.status_code, 200)
        after = response.get_json()["expansions_after"]
        # Every pre-existing entry survives at its own index.
        for index, expansion_id in enumerate(COMMITTED_LEDGER):
            with self.subTest(expansion_id=expansion_id):
                self.assertEqual(after[index], expansion_id)
        self.assertEqual(len(after), 5)
        # Not deduplicated, and not sorted: 0 goes last, and 45 stays before
        # 46 even though 0 is the smallest.
        self.assertEqual(after, [35, 36, 45, 46, 0])
        self.assertNotEqual(after, sorted(after))
        self.assertEqual(len(set(after)), len(after))


class PricedExpansionTests(unittest.TestCase):
    """A priced expansion through a stubbed purchasable committed row.

    **No committed row is both purchasable and priced** on this corpus: under
    design D3 a row recording a positive ``neighbors`` or ``inventory_qte`` is
    refused, and the four requirement-free rows cost nothing.  So the priced
    path is exercised by stubbing the *committed row accessor* with a row of
    the committed shape — the derivation, the envelope, the dispatcher, and
    the two-part proof are all the real ones.
    """

    def test_a_priced_row_debits_gold_and_cash_and_proves_the_movement(self) -> None:
        expansion_id = FREE_INDEXES[1]
        before_ledger = pristine_free(expansion_id)
        before = resources_now()
        # Sized from the *current* balance so the affordability refusal (which
        # is a content refusal and answers first) never fires here, and so the
        # suite stays order-independent.
        coins = before["gold"]
        cash = before["cash"]
        row = free_row(coins=coins, cash=cash)

        response = post_with_price_row(row, intent(expansion_id))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # The ledger grew by exactly the sent id at the end.
        self.assertEqual(
            payload["expansions_after"], before_ledger + [expansion_id]
        )
        assert_ledger_grew_by_one(
            self, before_ledger, payload["expansions_after"], expansion_id
        )
        # The debit: the row's gold-named coins negated into the gold slot and
        # its cash negated into the cash slot; every other slot zero.
        self.assertEqual(
            payload["debit"], [0, 0, -coins, 0, 0, 0, -cash, 0]
        )
        self.assertEqual(payload["debit"][expand_envelope.GOLD_SLOT], -coins)
        self.assertEqual(payload["debit"][expand_envelope.CASH_SLOT], -cash)
        for slot in expand_envelope.ALWAYS_ZERO_SLOTS:
            with self.subTest(slot=slot):
                self.assertEqual(payload["debit"][slot], 0)
        self.assertEqual(payload["price"], row)
        # The value-level half: EVERY stored resource changed by EXACTLY the
        # derived debit — gold and cash down, the other five untouched.
        expected = {
            name: before[name] + payload["debit"][SLOT_OF[name]]
            for name in RESOURCE_NAMES
        }
        self.assertEqual(payload["resources"], expected)
        self.assertEqual(payload["resources"]["gold"], 0)
        self.assertEqual(payload["resources"]["cash"], 0)
        for name in ("xp", "wood", "oil", "steel", "mana"):
            with self.subTest(resource=name):
                self.assertEqual(payload["resources"][name], before[name])
        self.assertEqual(BOOT.resources(PID)["gold"], payload["resources"]["gold"])  # type: ignore[union-attr]
        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_partly_affordable_priced_row_lands_in_exactly_its_slots(self) -> None:
        """A debit the balance covers but does not exhaust, in both named
        resources at once: the movement is the derived debit, not a clamp."""
        expansion_id = FREE_INDEXES[1]
        before_ledger = pristine_free(expansion_id)
        before = resources_now()
        coins, cash = before["gold"] // 2, before["cash"]

        response = post_with_price_row(
            free_row(coins=coins, cash=cash), intent(expansion_id)
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["debit"], [0, 0, -coins, 0, 0, 0, -cash, 0])
        self.assertEqual(payload["resources"]["gold"], before["gold"] - coins)
        self.assertEqual(payload["resources"]["cash"], 0)
        for name in ("xp", "wood", "oil", "steel", "mana"):
            with self.subTest(resource=name):
                self.assertEqual(payload["resources"][name], before[name])
        self.assertEqual(
            payload["expansions_after"], before_ledger + [expansion_id]
        )

    def test_a_cash_only_priced_row_lands_in_the_cash_slot_alone(self) -> None:
        """The debit is per **named resource**, not per slot index: a row
        priced in cash alone leaves gold and the five other resources alone."""
        expansion_id = FREE_INDEXES[2]
        before_ledger = pristine_free(expansion_id)
        before = resources_now()

        response = post_with_price_row(free_row(0, before["cash"]), intent(expansion_id))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["debit"], [0, 0, 0, 0, 0, 0, -before["cash"], 0]
        )
        self.assertEqual(payload["resources"]["cash"], 0)
        for name in ("xp", "gold", "wood", "oil", "steel", "mana"):
            with self.subTest(resource=name):
                self.assertEqual(payload["resources"][name], before[name])
        self.assertEqual(
            payload["expansions_after"], before_ledger + [expansion_id]
        )

    def test_a_gold_only_priced_row_lands_in_the_gold_slot_alone(self) -> None:
        expansion_id = FREE_INDEXES[3]
        before_ledger = pristine_free(expansion_id)
        before = resources_now()

        response = post_with_price_row(
            free_row(before["gold"], 0), intent(expansion_id)
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["debit"], [0, 0, -before["gold"], 0, 0, 0, 0, 0]
        )
        self.assertEqual(payload["resources"]["gold"], 0)
        for name in ("xp", "wood", "oil", "steel", "cash", "mana"):
            with self.subTest(resource=name):
                self.assertEqual(payload["resources"][name], before[name])
        self.assertEqual(
            payload["expansions_after"], before_ledger + [expansion_id]
        )

    def test_a_priced_row_spending_the_whole_balance_lands_exactly_on_zero(self) -> None:
        """The affordability refusal makes the clamp a no-op, so a debit equal
        to the balance must land on **exactly** ``0`` and the proof must still
        pass — the case that would otherwise be indistinguishable from a
        short charge."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        before = resources_now()

        response = post_with_price_row(
            free_row(before["gold"], before["cash"]), intent(expansion_id)
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["resources"]["gold"], 0)
        self.assertEqual(payload["resources"]["cash"], 0)
        self.assertEqual(
            payload["resources"]["gold"], before["gold"] + payload["debit"][2]
        )
        self.assertEqual(
            payload["resources"]["cash"], before["cash"] + payload["debit"][6]
        )


class ExpansionContentAccessorTests(unittest.TestCase):
    """The committed-configuration resolution rules (task 2.2 / D1 / D3)."""

    def test_the_committed_schedule_resolves(self) -> None:
        self.assertEqual(BOOT.expansion_price_count(), 98)  # type: ignore[union-attr]
        self.assertIsInstance(BOOT.expansion_price_count(), int)  # type: ignore[union-attr]
        self.assertEqual(len(BOOT.config()["expansion_prices"]), 98)  # type: ignore[union-attr]

    def test_a_resolving_id_returns_its_committed_row_verbatim(self) -> None:
        for expansion_id in (0, 4, 5, 33, 35, 36, 45, 46, 97):
            with self.subTest(expansion_id=expansion_id):
                row = BOOT.expansion_price(expansion_id)  # type: ignore[union-attr]
                self.assertIsInstance(row, dict)
                self.assertEqual(
                    sorted(row), ["cash", "coins", "inventory_qte", "neighbors"]
                )
                for field in expand_envelope.COMMITTED_ROW_FIELDS:
                    self.assertIsInstance(row[field], int)
                    self.assertNotIsInstance(row[field], bool)
                    self.assertGreaterEqual(row[field], 0)
        # Verbatim, never coerced or copied into a different shape.
        self.assertEqual(
            BOOT.expansion_price(4),  # type: ignore[union-attr]
            {"coins": 2500, "cash": 5, "neighbors": 1, "inventory_qte": 1},
        )

    def test_the_returned_row_is_a_copy_of_the_configuration(self) -> None:
        """A caller mutating the returned mapping must never reach the loaded
        legacy configuration."""
        row = BOOT.expansion_price(0)  # type: ignore[union-attr]
        row["coins"] = 999999  # type: ignore[index]
        self.assertEqual(BOOT.expansion_price(0)["coins"], 0)  # type: ignore[union-attr]
        self.assertEqual(BOOT.config()["expansion_prices"][0]["coins"], 0)  # type: ignore[union-attr]

    def test_an_out_of_range_id_has_no_committed_row(self) -> None:
        """The evidence for the endpoint's range guard: the legacy server does
        no range check at all (an executed-legacy probe had ``expand(999)``
        answer success)."""
        for bad in (98, 99, 999, 10 ** 9, -1, -35, -(10 ** 9)):
            with self.subTest(expansion_id=bad):
                self.assertIsNone(BOOT.expansion_price(bad))  # type: ignore[union-attr]
        self.assertIsNotNone(BOOT.expansion_price(97))  # type: ignore[union-attr]

    def test_a_non_integer_id_has_no_committed_row(self) -> None:
        """``True`` is an ``int`` in Python, so an ``isinstance`` check alone
        would index the schedule as ``1`` and return a *priced* row for a
        boolean."""
        for bad in ("0", 0.0, True, None, [0], {"id": 0}):
            with self.subTest(expansion_id=bad):
                self.assertIsNone(BOOT.expansion_price(bad))  # type: ignore[union-attr]

    def test_a_negative_id_never_resolves_from_the_end_of_the_list(self) -> None:
        """``schedule[-1]`` is the last (saturated) row in Python, so a negative
        id would otherwise be priced from a positive one."""
        for bad in (-1, -35, -97, -(10 ** 9)):
            with self.subTest(expansion_id=bad):
                self.assertIsNone(BOOT.expansion_price(bad))  # type: ignore[union-attr]
        # …and the id space really is 0..97 inclusive.
        self.assertIsNotNone(BOOT.expansion_price(0))  # type: ignore[union-attr]
        self.assertIsNotNone(BOOT.expansion_price(97))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.expansion_price(98))  # type: ignore[union-attr]

    def test_the_owned_ledger_accessor_copies_and_never_rewrites(self) -> None:
        """The legacy dispatcher appends to that very list in place, so the
        accessor returns a copy and the response's ``expansions_before`` can
        never alias the live ledger."""
        pristine_free(FIXTURE_EXPANSION_ID)
        first = ledger_now()
        second = ledger_now()
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        first.append(999)
        self.assertEqual(ledger_now(), COMMITTED_LEDGER)
        self.assertEqual(corpus_ledger(), COMMITTED_LEDGER)

    def test_a_map_with_no_ledger_raises_rather_than_inventing_one(self) -> None:
        """A missing ``expansions`` list is a state this service cannot reason
        about; the accessor raises ``invalid_save_state`` rather than
        pretending the player owns nothing."""
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        saved = save["maps"][0].pop("expansions")
        try:
            with self.assertRaises(compat_legacy.LegacyBootError) as caught:
                BOOT.map_expansions(PID)  # type: ignore[union-attr]
            self.assertEqual(caught.exception.code, "invalid_save_state")
        finally:
            save["maps"][0]["expansions"] = saved
        pristine_free(FIXTURE_EXPANSION_ID)

    def test_a_non_list_ledger_raises_too(self) -> None:
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        saved = save["maps"][0]["expansions"]
        save["maps"][0]["expansions"] = {"0": True}
        try:
            with self.assertRaises(compat_legacy.LegacyBootError) as caught:
                BOOT.map_expansions(PID)  # type: ignore[union-attr]
            self.assertEqual(caught.exception.code, "invalid_save_state")
        finally:
            save["maps"][0]["expansions"] = saved
        pristine_free(FIXTURE_EXPANSION_ID)

    def test_the_committed_census_matches_the_investigation(self) -> None:
        schedule = BOOT.config()["expansion_prices"]  # type: ignore[union-attr]
        self.assertEqual(len(schedule), 98)
        for index in range(4):
            with self.subTest(index=index):
                self.assertEqual(schedule[index]["coins"], 0)
                self.assertEqual(schedule[index]["cash"], 0)
        self.assertEqual(
            schedule[4], {"coins": 2500, "cash": 5, "neighbors": 1, "inventory_qte": 1}
        )
        self.assertEqual(
            schedule[5], {"coins": 5000, "cash": 8, "neighbors": 2, "inventory_qte": 2}
        )
        self.assertEqual(
            schedule[97],
            {"coins": 100000, "cash": 20, "neighbors": 15, "inventory_qte": 30},
        )

    def test_the_four_entry_schedules_are_present_and_unused(self) -> None:
        """``town_prices`` / ``map_prices`` exist and are deliberately not the
        id space: the corpus's own ledger is not a level set and is not a
        four-entry index."""
        config = BOOT.config()  # type: ignore[union-attr]
        for name in ("town_prices", "map_prices"):
            with self.subTest(schedule=name):
                self.assertEqual(len(config[name]), 4)
                self.assertEqual(
                    sorted(int(entry["level"]) for entry in config[name]),
                    [15, 25, 35, 45],
                )
        # Identical values, preserved as separate schedules and never
        # deduplicated.
        self.assertEqual(config["town_prices"], config["map_prices"])
        levels = {int(entry["level"]) for entry in config["town_prices"]}
        self.assertEqual(set(COMMITTED_LEDGER) & levels, {35, 45})
        self.assertNotIn(36, levels)
        self.assertNotIn(46, levels)
        for expansion_id in COMMITTED_LEDGER:
            with self.subTest(expansion_id=expansion_id):
                self.assertGreaterEqual(expansion_id, 4)


class DerivedDebitTests(unittest.TestCase):
    """The debit is derived, not client-supplied (design D5)."""

    def test_client_supplied_debit_keys_are_ignored(self) -> None:
        expansion_id = FREE_INDEXES[1]
        before_ledger = pristine_free(expansion_id)
        before = resources_now()
        response = expand_now(
            dict(
                intent(expansion_id),
                coins=999999,
                cash=999999,
                price=999999,
                price_type="cash",
                amount=999999,
                neighbors=0,
                inventory_qte=0,
                requirements_met=True,
                time=1,
                now=0,
                result="hacked",
                debit=[0, 0, 999999, 0, 0, 0, 999999, 0],
                resources_changed=[0, 0, 999999, 0, 0, 0, 0, 0],
                resources={"gold": 999999, "cash": 999999},
                expansions_after=[999999],
                expansions_before=[],
            )
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["result"], "success")
        # The server's own derivation wins on every field.
        self.assertEqual(payload["expansions_before"], before_ledger)
        self.assertEqual(
            payload["expansions_after"], before_ledger + [expansion_id]
        )
        self.assertEqual(payload["debit"], [0] * 8)
        self.assertEqual(payload["price"]["coins"], 0)
        self.assertNotEqual(payload["debit"][2], 999999)
        self.assertNotEqual(payload["debit"][6], 999999)
        # No mint: not one balance moved.
        self.assertEqual(payload["resources"], before)
        self.assertEqual(corpus_ledger(), payload["expansions_after"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_derived_debit_never_carries_a_positive_slot(self) -> None:
        """A positive entry is a client-trusted mint and a negative magnitude a
        client-trusted burn; this contract sends neither sign error."""
        for expansion_id in FREE_INDEXES:
            with self.subTest(expansion_id=expansion_id):
                pristine_free(expansion_id)
                response = expand_now(intent(expansion_id))
                self.assertEqual(response.status_code, 200)
                debit = response.get_json()["debit"]
                for slot, value in enumerate(debit):
                    with self.subTest(slot=slot):
                        self.assertIsInstance(value, int)
                        self.assertNotIsInstance(value, bool)
                        self.assertLessEqual(value, 0)


class GuardAndRefusalTests(unittest.TestCase):
    """The two guards and the two content refusals, each byte-identical.

    ``setUp`` takes a baseline so a test that never reaches a request still has
    one; each test then **re-takes** the baseline after whatever setup it
    needs (resetting the ledger to the committed value), so the "nothing
    changed" claim is always about the request under test and never about the
    test's own setup.
    """

    def setUp(self) -> None:
        self.baseline()

    def baseline(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_ledger = copy.deepcopy(ledger_now())
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.before_resources = copy.deepcopy(resources_now())
        self.before_store = copy.deepcopy(BOOT.map_store(PID))  # type: ignore[union-attr]

    def assert_refused(self, response: Any, status: int, code: str) -> None:
        self.assertEqual(response.status_code, status)
        body = response.get_json()
        self.assertIsInstance(body, dict)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)
        # Never a partial payload.
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(set(body["error"]), {"code", "message"})
        # Every refusal precedes legacy execution: no mutation anywhere.
        self.assertEqual(harness.save_hashes(CORPUS), self.before_hashes)  # type: ignore[arg-type]
        self.assertEqual(ledger_now(), self.before_ledger)
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), self.before_store)  # type: ignore[union-attr]
        self.assertEqual(resources_now(), self.before_resources)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_an_id_outside_the_committed_schedule_is_refused(self) -> None:
        """Design D1, first guard.  The legacy server has no range check at
        all — an executed-legacy probe had ``expand(999)`` answer success — so
        an id the committed table does not price is refused before dispatch."""
        pristine_free(FIXTURE_EXPANSION_ID)
        for expansion_id in OUT_OF_RANGE:
            with self.subTest(expansion_id=expansion_id):
                self.baseline()
                response = expand_now(intent(expansion_id))
                self.assert_refused(response, 404, "unknown_expansion_id")
                self.assertIn(str(expansion_id), response.get_json()["error"]["message"])
                self.assertIn("98 rows", response.get_json()["error"]["message"])

    def test_a_negative_id_is_refused(self) -> None:
        """The probe's third case: legacy answers success; the service refuses.

        A negative id is refused as **structurally invalid**, not as
        out-of-range: the committed schedule's id space is ``0..97`` and
        Python would otherwise resolve ``-1`` to the schedule's *last* row,
        pricing a negative id from a positive one.  It therefore never reaches
        the range check and the corpus is untouched either way.
        """
        pristine_free(FIXTURE_EXPANSION_ID)
        for expansion_id in NEGATIVE:
            with self.subTest(expansion_id=expansion_id):
                self.baseline()
                response = expand_now(intent(expansion_id))
                self.assert_refused(response, 400, "invalid_expansion_id")
                self.assertIn(
                    "must not be negative", response.get_json()["error"]["message"]
                )

    def test_the_range_boundary_is_exact(self) -> None:
        """Index 97 is the last committed row; index 98 is out of range."""
        pristine_free(FIXTURE_EXPANSION_ID)
        # 97 is a committed row but records a requirement, so it is refused as
        # blocked rather than as unknown — the boundary is the range check, and
        # the content refusal is downstream of it.
        self.assertIsNotNone(BOOT.expansion_price(97))  # type: ignore[union-attr]
        self.baseline()
        response = expand_now(intent(97))
        self.assert_refused(response, 409, "expansion_requirements_unmet")

    def test_an_already_owned_id_is_refused(self) -> None:
        """Design D1, second guard.  The probe's second case: a duplicate
        ``expand(35)`` answered success; the service refuses it so the ledger
        can never gain a repeat."""
        pristine_free(FIXTURE_EXPANSION_ID)
        for expansion_id in COMMITTED_LEDGER:
            with self.subTest(expansion_id=expansion_id):
                self.baseline()
                response = expand_now(intent(expansion_id))
                self.assert_refused(response, 409, "already_expanded")
                self.assertIn(
                    str(expansion_id), response.get_json()["error"]["message"]
                )
        # The ledger keeps every entry exactly once, in order.
        self.assertEqual(ledger_now(), COMMITTED_LEDGER)
        self.assertEqual(len(set(ledger_now())), len(ledger_now()))

    def test_a_just_expanded_id_is_refused_on_a_repeat(self) -> None:
        """The duplicate guard is enforced against the **live** ledger, not
        only the committed one: an id bought a moment ago is refused too."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        first = expand_now(intent(expansion_id))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            first.get_json()["expansions_after"], COMMITTED_LEDGER + [expansion_id]
        )

        self.baseline()
        second = expand_now(intent(expansion_id))

        self.assert_refused(second, 409, "already_expanded")
        # The refused repeat left the ledger exactly where the first one put it.
        self.assertEqual(ledger_now(), COMMITTED_LEDGER + [expansion_id])

    def test_a_priced_committed_row_is_refused_for_its_requirement(self) -> None:
        """Design D3, against the real accessor.  **94 of the 98 committed
        rows** record a positive ``neighbors`` or ``inventory_qte``, so the
        corpus consequence is that the only purchasable entries are the free
        indexes 0..3.  The four indexes the corpus **owns** are excluded here
        because the duplicate guard answers first for them; they are covered
        by :meth:`test_every_owned_id_is_blocked_by_its_requirement`."""
        pristine_free(FIXTURE_EXPANSION_ID)
        unowned = tuple(
            index
            for index in BLOCKED_INDEXES
            if index not in COMMITTED_LEDGER
        )
        self.assertTrue(unowned)
        for expansion_id in unowned:
            with self.subTest(expansion_id=expansion_id):
                self.baseline()
                response = expand_now(intent(expansion_id))
                self.assert_refused(response, 409, "expansion_requirements_unmet")
                message = response.get_json()["error"]["message"]
                self.assertIn("neighbors", message)
                self.assertIn("inventory_qte", message)
                self.assertIn("nothing this service can read", message)

    def test_every_owned_id_is_blocked_by_its_requirement(self) -> None:
        """The corpus consequence, stated rather than hidden: **none of the
        four ids the corpus owns could have been bought** under the
        requirements rule.  The duplicate guard answers first while they are
        owned, so the requirement path is exercised for the same ids once they
        are not — proven by pointing the request at a ledger without them."""
        pristine_free(FIXTURE_EXPANSION_ID)
        # While owned, the duplicate guard answers first.
        for expansion_id in COMMITTED_LEDGER:
            with self.subTest(expansion_id=expansion_id, ledger="committed"):
                self.baseline()
                response = expand_now(intent(expansion_id))
                self.assert_refused(response, 409, "already_expanded")
        # Un-owned, the requirement refusal answers for each.
        reset_ledger([])
        try:
            for expansion_id in COMMITTED_LEDGER:
                with self.subTest(expansion_id=expansion_id, ledger="empty"):
                    self.baseline()
                    response = expand_now(intent(expansion_id))
                    self.assert_refused(
                        response, 409, "expansion_requirements_unmet"
                    )
                    row = BOOT.expansion_price(expansion_id)  # type: ignore[union-attr]
                    self.assertEqual(row["neighbors"], 15)
                    self.assertEqual(row["inventory_qte"], 30)
                    # And the derived debit it would have paid is the
                    # saturated one, which the refusal keeps unreached.
                    self.assertEqual(
                        expand_envelope.resource_vector_for(row),
                        [0, 0, -100000, 0, 0, 0, -20, 0],
                    )
        finally:
            reset_ledger(COMMITTED_LEDGER)

    def test_the_requirements_check_precedes_the_affordability_check(self) -> None:
        """A row that is both blocked and unaffordable is refused for the
        requirement first: that is the rule that refuses rather than invents,
        and the affordability question is never reached for a row the player
        could not buy anyway."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        before = resources_now()
        # A purchasable row the balance cannot cover, reached through the
        # *requirements* accessor shape: the row records a positive
        # ``neighbors`` and a cost far above the balance.
        blocked = {
            "coins": before["gold"] + 1,
            "cash": before["cash"] + 1,
            "neighbors": 1,
            "inventory_qte": 1,
        }
        self.baseline()
        response = post_with_price_row(blocked, intent(expansion_id))
        self.assert_refused(response, 409, "expansion_requirements_unmet")
        # The same cost with no requirement IS the affordability refusal, so
        # the ordering is what distinguishes the two.
        self.baseline()
        affordable_shape = post_with_price_row(
            free_row(coins=before["gold"] + 1, cash=before["cash"] + 1),
            intent(expansion_id),
        )
        self.assert_refused(affordable_shape, 409, "insufficient_resources")

    def test_the_duplicate_check_precedes_the_requirements_check(self) -> None:
        """An id that is both owned and blocked answers ``already_expanded``:
        the ledger check is the cheaper, more specific one and it is what
        protects the ledger."""
        pristine_free(FIXTURE_EXPANSION_ID)
        self.baseline()
        response = expand_now(intent(35))
        self.assert_refused(response, 409, "already_expanded")

    def test_an_unaffordable_balance_is_refused(self) -> None:
        """Design D6, the recorded alternative to reproducing the clamp.  The
        debit is server-derived, so the endpoint knows the balance does not
        cover it; a partially applied charge would be indistinguishable from a
        wrong derivation."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        before = resources_now()
        # The refusal names the first resource the loop finds short, and the
        # loop is over the alphabetically-sorted named slots, so ``cash`` is
        # named whenever cash is also short.  Each case therefore names exactly
        # which resource it made short.
        cases = (
            (before["gold"] + 1, 0, "gold"),
            (0, before["cash"] + 1, "cash"),
            (10 ** 9, 10 ** 9, "cash"),
            (before["gold"], 10 ** 9, "cash"),
            (10 ** 9, 0, "gold"),
        )
        for coins, cash, short in cases:
            with self.subTest(coins=coins, cash=cash):
                self.baseline()
                response = post_with_price_row(
                    free_row(coins, cash), intent(expansion_id)
                )
                self.assert_refused(response, 409, "insufficient_resources")
                # The message names the resource that is short, the cost, and
                # the balance — never save content beyond the adapter's own
                # numbers.
                message = response.get_json()["error"]["message"]
                self.assertIn(short, message)
                self.assertIn(
                    str(coins if short == "gold" else cash), message
                )
                self.assertIn(
                    str(before[short]), message
                )

    def test_the_unaffordable_message_names_the_short_resource(self) -> None:
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        self.baseline()
        gold_short = post_with_price_row(
            free_row(coins=10 ** 6, cash=0), intent(expansion_id)
        )
        self.assertIn("gold", gold_short.get_json()["error"]["message"])
        cash_short = post_with_price_row(
            free_row(coins=0, cash=10 ** 6), intent(expansion_id)
        )
        self.assertIn("cash", cash_short.get_json()["error"]["message"])

    def test_a_balance_one_short_of_the_debit_is_refused(self) -> None:
        """The refusal is at the exact boundary: a debit the balance covers
        exactly is accepted (and lands on exactly ``0``), and one it misses by
        a single unit is refused with the corpus byte-identical."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        before = resources_now()

        self.baseline()
        exact = post_with_price_row(free_row(before["gold"], 0), intent(expansion_id))
        self.assertEqual(exact.status_code, 200)
        self.assertEqual(exact.get_json()["resources"]["gold"], 0)

        # The exact case really spent the gold, so the balances are back at the
        # committed value before the one-short case is measured.
        pristine_free(expansion_id)
        self.baseline()
        one_short = post_with_price_row(
            free_row(before["gold"] + 1, 0), intent(expansion_id)
        )
        self.assert_refused(one_short, 409, "insufficient_resources")

    def test_the_error_constants_are_the_documented_ones(self) -> None:
        self.assertEqual(compat_service.ERROR_ALREADY_EXPANDED, "already_expanded")
        self.assertEqual(
            compat_service.ERROR_EXPANSION_REQUIREMENTS_UNMET,
            "expansion_requirements_unmet",
        )
        self.assertEqual(
            compat_service.ERROR_INSUFFICIENT_RESOURCES, "insufficient_resources"
        )
        self.assertEqual(
            compat_service.ERROR_UNKNOWN_EXPANSION_ID, "unknown_expansion_id"
        )
        self.assertEqual(
            compat_service.ERROR_MISSING_EXPANSION_ID, "missing_expansion_id"
        )
        self.assertEqual(
            compat_service.ERROR_INVALID_EXPANSION_ID, "invalid_expansion_id"
        )
        # And every one of them is documented in the module's error table, the
        # documented place where the status mapping is written down.
        table = Path(compat_service.__file__).read_text(encoding="utf-8")
        for code in (
            "missing_expansion_id",
            "invalid_expansion_id",
            "unknown_expansion_id",
            "already_expanded",
            "expansion_requirements_unmet",
            "insufficient_resources",
        ):
            with self.subTest(code=code):
                self.assertIn("``%s``" % code, table)


class ExpandFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation."""

    def setUp(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_ledger = copy.deepcopy(ledger_now())
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]

    def assert_fail_closed(self, response: Any, status: int, code: str) -> None:
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
        self.assertEqual(ledger_now(), self.before_ledger)
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_non_object_bodies(self) -> None:
        with harness.offline():
            responses = [
                CLIENT.post("/v0/expand"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/expand", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/expand", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/expand", json=7),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        base: Dict[str, Any] = {"expansion_id": FIXTURE_EXPANSION_ID}
        self.assert_fail_closed(expand_now({}), 400, "missing_user_id")
        self.assert_fail_closed(
            expand_now({"user_id": "", **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            expand_now({"user_id": None, **base}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            expand_now({"user_id": 123, **base}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(
            expand_now({"user_id": "ghost", **base}), 404, "unknown_user_id"
        )

    def test_expansion_id_failures(self) -> None:
        self.assert_fail_closed(
            expand_now({"user_id": PID}), 400, "missing_expansion_id"
        )
        for bad in ("0", 0.0, True, None, [0], {"id": 0}):
            with self.subTest(expansion_id=bad):
                self.assert_fail_closed(
                    expand_now({"user_id": PID, "expansion_id": bad}),
                    400,
                    "invalid_expansion_id",
                )

    def test_a_negative_id_is_structurally_invalid(self) -> None:
        """A negative id never reaches the range check, so a content question is
        never answered for it."""
        for bad in (-1, -35, -(10 ** 9)):
            with self.subTest(expansion_id=bad):
                self.assert_fail_closed(
                    expand_now({"user_id": PID, "expansion_id": bad}),
                    400,
                    "invalid_expansion_id",
                )

    def test_a_non_integer_id_never_reaches_the_legacy_500(self) -> None:
        """Probe 3: ``expand("abc")`` raised an unhandled HTTP 500 inside the
        legacy branch.  The structural check answers 400 instead, and the
        ledger is untouched."""
        pristine_free(FIXTURE_EXPANSION_ID)
        # The baseline is taken **after** the setup reset, so the
        # "nothing changed" claim is about the request and not the setup.
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_ledger = list(ledger_now())
        self.before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        response = expand_now({"user_id": PID, "expansion_id": "abc"})
        self.assert_fail_closed(response, 400, "invalid_expansion_id")

    def test_the_structural_check_precedes_every_content_refusal(self) -> None:
        """A non-integer id is not a content question, so the structural check
        answers first rather than the client being told the id is unknown."""
        response = post_with_price_row(
            free_row(0, 0), {"user_id": PID, "expansion_id": "abc"}
        )
        self.assert_fail_closed(response, 400, "invalid_expansion_id")

    def test_a_ledger_the_service_cannot_read_is_a_500(self) -> None:
        """A ledger entry this service cannot reason about as an integer fails
        closed rather than being coerced, compared, or rewritten."""
        pristine_free(FIXTURE_EXPANSION_ID)
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        saved = save["maps"][0]["expansions"]
        save["maps"][0]["expansions"] = list(saved) + ["35"]
        try:
            with harness.offline():
                response = CLIENT.post(  # type: ignore[union-attr]
                    "/v0/expand", json=intent(FREE_INDEXES[1])
                )
        finally:
            save["maps"][0]["expansions"] = saved
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("cannot reason about", body["error"]["message"])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        pristine_free(FIXTURE_EXPANSION_ID)

    def test_a_missing_ledger_is_a_500_before_execution(self) -> None:
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        saved = save["maps"][0].pop("expansions")
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        try:
            with harness.offline():
                response = CLIENT.post(  # type: ignore[union-attr]
                    "/v0/expand", json=intent(FIXTURE_EXPANSION_ID)
                )
        finally:
            save["maps"][0]["expansions"] = saved
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        # Nothing ran: the corpus file is byte-identical.
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_malformed_committed_row_is_a_500_before_execution(self) -> None:
        """A committed row the loaded configuration cannot describe as a price
        is a server-side derivation failure, never coerced into a debit.

        Two shapes reach two different refusals, and both are 500 with no
        mutation: a row that is not a mapping at all is ``invalid_price``, and
        a mapping whose costs are absent, non-integer, boolean, or **negative**
        is ``invalid_cost`` — the negative case being the one that would put a
        positive entry (a client-trusted mint) on the legacy vector.
        """
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        cases: Dict[str, Any] = {
            "invalid_price": (
                "coins 0",
                42,
                ["coins", 0],
            ),
            "invalid_cost": (
                {"cash": 0},  # no coins at all
                {"coins": 0},  # no cash at all
                {},  # neither
                {"coins": -1, "cash": 0},  # a negative cost: a mint
                {"coins": "0", "cash": 0},  # a string cost
                {"coins": 0.0, "cash": 0},  # a float cost
                {"coins": True, "cash": 0},  # a bool cost
                {"coins": 0, "cash": -5},  # a negative cash cost
                {"coins": 0, "cash": None},  # a null cost
            ),
        }
        for expected_code, rows in sorted(cases.items()):
            for bad in rows:
                with self.subTest(expected=expected_code, row=bad):
                    before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
                    before_ledger = list(ledger_now())
                    response = post_with_price_row(bad, intent(expansion_id))
                    self.assertEqual(response.status_code, 500)
                    body = response.get_json()
                    self.assertFalse(body["ok"])
                    self.assertEqual(body["error"]["code"], "internal_error")
                    # The message carries the derivation's own machine code and
                    # never save content.
                    self.assertIn(expected_code, body["error"]["message"])
                    self.assertEqual(set(body), {"protocol", "ok", "error"})
                    # Nothing ran.
                    self.assertEqual(
                        harness.save_hashes(CORPUS), before  # type: ignore[arg-type]
                    )
                    self.assertEqual(ledger_now(), before_ledger)
                    self.assertEqual(
                        harness.working_tree_save_hashes(), WORKING_TREE_PRE
                    )

    def test_a_row_the_schedule_cannot_produce_is_a_500(self) -> None:
        """The range check already passed, so an absent row for an id the
        configuration says it holds is a content failure — not an
        ``unknown_expansion_id``, and never a price invented from nothing."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        response = post_with_price_row(None, intent(expansion_id))
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("produced no row for id %d" % expansion_id, body["error"]["message"])
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(ledger_now(), COMMITTED_LEDGER)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_legacy_execution_raising_is_a_500(self) -> None:
        """A dispatcher failure after validation passed is a structured 500."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        before = ledger_now()
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.execute_commands  # type: ignore[union-attr]

        def explode(user_id, envelope):
            raise RuntimeError("legacy blew up")

        BOOT.execute_commands = explode  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/expand", json=intent(expansion_id))
        finally:
            BOOT.execute_commands = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("RuntimeError", body["error"]["message"])
        self.assertEqual(ledger_now(), before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_error_code_constants_match_the_documented_names(self) -> None:
        self.assertEqual(
            compat_service.ERROR_MISSING_EXPANSION_ID, "missing_expansion_id"
        )
        self.assertEqual(
            compat_service.ERROR_INVALID_EXPANSION_ID, "invalid_expansion_id"
        )
        self.assertEqual(
            compat_service.ERROR_UNKNOWN_EXPANSION_ID, "unknown_expansion_id"
        )
        self.assertEqual(compat_service.ERROR_INVALID_PAYLOAD, "invalid_payload")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")
        self.assertEqual(compat_service.ERROR_MISSING_USER_ID, "missing_user_id")
        self.assertEqual(compat_service.ERROR_INVALID_USER_ID, "invalid_user_id")


class PostExecutionProofTests(unittest.TestCase):
    """Design D5: both halves of the proof, or a structured 500.

    Each test resets the ledger it uses, runs the **real** legacy dispatcher,
    and only rewrites the **post**-execution read, so the ledger and the
    resources the save really holds are the true ones and the reported
    divergence is the only thing that fails.
    """

    def assert_internal(self, response: Any, fragment: str) -> None:
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn(fragment, body["error"]["message"])
        # Not a success and not a partial payload.
        self.assertNotIn("expansions_after", body)
        self.assertNotIn("result", body)
        self.assertNotIn("debit", body)
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_ledger_that_did_not_grow_is_a_500_not_a_success(self) -> None:
        """The structural half.  No expand branch can fail to append, so the
        stub reproduces a post-state legacy could never report; the endpoint
        must refuse it anyway rather than trust the legacy status.

        The stub strips the appended id, so the reported ledger is exactly the
        pre-execution one — the strongest form of "did not grow".
        """
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_ledger_stub(
            lambda ledger: list(ledger)[:-1], intent(expansion_id)
        )
        self.assert_internal(response, "not the documented")

    def test_a_ledger_that_grew_by_two_is_a_500(self) -> None:
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_ledger_stub(
            lambda ledger: list(ledger) + [expansion_id, 1],
            intent(expansion_id),
        )
        self.assert_internal(response, "not the documented")
        # The real dispatcher appended exactly one, so the save really grew by
        # one even though the service refused to claim it.
        self.assertEqual(ledger_now(), COMMITTED_LEDGER + [expansion_id])

    def test_a_ledger_with_another_appended_id_is_a_500(self) -> None:
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_ledger_stub(
            lambda ledger: list(ledger) + [7], intent(expansion_id)
        )
        self.assert_internal(response, "not the documented")

    def test_a_prepended_id_is_a_500(self) -> None:
        """The append is at the **end**: a ledger the id was prepended to is
        not the documented post-state even though it contains the id."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_ledger_stub(
            lambda ledger: [expansion_id] + list(ledger), intent(expansion_id)
        )
        self.assert_internal(response, "at the end")

    def test_a_reordered_ledger_is_a_500(self) -> None:
        """The existing entries must be **in order**: legacy neither orders nor
        reorders, so a reordered read is a divergence."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_ledger_stub(
            lambda ledger: list(reversed(list(ledger))), intent(expansion_id)
        )
        self.assert_internal(response, "not the documented")

    def test_a_deduplicated_ledger_is_a_500(self) -> None:
        """Legacy does **not** deduplicate, so a read in which an owned id has
        vanished would be a silent ledger normalization the endpoint must never
        report — the existing entries are required to be unchanged."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_ledger_stub(
            lambda ledger: list(ledger)[:-2] + [ledger[-1]], intent(expansion_id)
        )
        self.assert_internal(response, "not the documented")

    def test_a_wrong_typed_ledger_is_a_500(self) -> None:
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_ledger_stub(
            lambda ledger: [str(value) for value in list(ledger) + [expansion_id]],
            intent(expansion_id),
        )
        self.assert_internal(response, "not the documented")

    def test_a_shortened_debit_is_reported_not_trusted(self) -> None:
        """The value-level half.  A movement the derived debit does not explain
        is a reported failure, not a success — this is the clause that would
        catch a wrong server-derived price."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        response = post_with_resources_stub(
            lambda values: dict(values, gold=values["gold"] + 1), intent(expansion_id)
        )
        self.assert_internal(response, "resource gold")
        message = response.get_json()["error"]["message"]
        self.assertIn("derived", message)
        self.assertIn("the derived debit is 0", message)

    def test_a_resource_the_derived_debit_leaves_alone_moving_is_a_500(self) -> None:
        """A derived free row carries zeros in **all eight** slots, so any
        movement in any balance means the reported resources are not the
        derived ones."""
        expansion_id = FREE_INDEXES[2]
        pristine_free(expansion_id)
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                response = post_with_resources_stub(
                    lambda values, moved=name: dict(
                        values, **{moved: values[moved] + 1}
                    ),
                    intent(expansion_id),
                )
                self.assert_internal(response, "resource %s" % name)
                pristine_free(expansion_id)

    def test_a_priced_debit_that_did_not_land_is_a_500(self) -> None:
        """The value-level half over a real priced row: the gold debit is
        derived server-side, so a gold balance that did not move by exactly it
        is a divergence legacy's status can never show."""
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
        before = resources_now()
        coins = before["gold"]
        row = free_row(coins=coins, cash=before["cash"])
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original_price = BOOT.expansion_price  # type: ignore[union-attr]
        original_resources = BOOT.resources  # type: ignore[union-attr]
        state = {"seen": 0}

        def stub_resources(user_id: str) -> Dict[str, int]:
            state["seen"] += 1
            values = original_resources(user_id)
            if state["seen"] == 1:
                return values
            # Report the gold as if the derived debit had not landed at all.
            return dict(values, gold=values["gold"] + coins)

        def stub_price(index: int) -> Any:
            if index == expansion_id:
                return dict(row)
            return original_price(index)

        BOOT.expansion_price = stub_price  # type: ignore[assignment]
        BOOT.resources = stub_resources  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/expand", json=intent(expansion_id))
        finally:
            BOOT.expansion_price = original_price  # type: ignore[assignment]
            BOOT.resources = original_resources  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("resource gold", body["error"]["message"])
        self.assertIn(
            "the derived debit is %d" % -coins, body["error"]["message"]
        )
        # The real dispatcher applied the full derived debit to the save; the
        # stub only rewrote the reported read.
        self.assertEqual(
            BOOT.resources(PID)["gold"], 0  # type: ignore[union-attr]
        )
        self.assertEqual(ledger_now(), COMMITTED_LEDGER + [expansion_id])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_proof_source_contains_both_halves(self) -> None:
        """The endpoint reads the pre-execution ledger **and** the
        pre-execution resources *before* dispatch, and requires both the exact
        append and the exact resource movement."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        self.assertIn("expansions_before = boot.map_expansions(user_id)", source)
        self.assertIn("resources_before = boot.resources(user_id)", source)
        self.assertIn(
            "expected_list = list(expansions_before) + [expansion_id]", source
        )
        self.assertIn(
            "expected = resources_before[name] + debit_by_name[name]", source
        )
        # Both reads and the dispatcher call live inside the expand route, and
        # both pre-execution reads precede the dispatch.
        route = source[source.index("def v0_expand()"):]
        route = route[: route.index("@app.errorhandler(400)")]
        self.assertLess(
            route.index("expansions_before = boot.map_expansions(user_id)"),
            route.index("boot.execute_commands(user_id, envelope_payload)"),
        )
        self.assertLess(
            route.index("resources_before = boot.resources(user_id)"),
            route.index("boot.execute_commands(user_id, envelope_payload)"),
        )
        self.assertLess(
            route.index("boot.execute_commands(user_id, envelope_payload)"),
            route.index("expected_list = list(expansions_before) + [expansion_id]"),
        )
        self.assertLess(
            route.index("expected_list = list(expansions_before) + [expansion_id]"),
            route.index("expected = resources_before[name] + debit_by_name[name]"),
        )


class ExpansionContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_expansions(self) -> None:
        expansion_id = FREE_INDEXES[1]
        pristine_free(expansion_id)
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

    def test_expansions_never_touch_working_tree_saves(self) -> None:
        expansion_id = FREE_INDEXES[1]
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        before_ledger = pristine_free(expansion_id)
        response = expand_now(intent(expansion_id))
        self.assertEqual(response.status_code, 200)
        # The corpus save changed; the working tree did not move.
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(ledger_now(), before_ledger + [expansion_id])
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_an_expansion_leaves_every_placement_alone(self) -> None:
        """Design D4 in the delivered sense: the ledger grows and **no** row
        moves, so no placement, grid, cell, or bound changed."""
        expansion_id = FREE_INDEXES[2]
        pristine_free(expansion_id)
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.assertEqual(before_items, seed_items)

        response = expand_now(intent(expansion_id))

        self.assertEqual(response.status_code, 200)
        # Every one of the 40 rows is byte-identical, including the rows the
        # other nine committed fixtures address.
        self.assertEqual(BOOT.map_items(PID), before_items)  # type: ignore[union-attr]
        for key in ("2", "11", "12", "20", "21"):
            with self.subTest(key=key):
                self.assertEqual(BOOT.map_items(PID)[key], seed_items[key])  # type: ignore[union-attr]
        self.assertEqual(len(BOOT.map_items(PID)), 40)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), {})  # type: ignore[union-attr]
        self.assertEqual(
            BOOT.save_document(PID)["privateState"]["boughtUnits"], []  # type: ignore[union-attr]
        )
        self.assertEqual(
            BOOT.save_document(PID)["privateState"]["deadHeroes"], {}  # type: ignore[union-attr]
        )
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_legacy_accessors_agree_with_the_map(self) -> None:
        pristine_free(FIXTURE_EXPANSION_ID)
        self.assertEqual(ledger_now(), COMMITTED_LEDGER)
        self.assertEqual(BOOT.expansion_price_count(), 98)  # type: ignore[union-attr]
        self.assertIsNotNone(BOOT.expansion_price(0))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.expansion_price(98))  # type: ignore[union-attr]
        self.assertTrue(BOOT.has_map_item(PID, 2))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]

    def test_the_endpoint_derives_the_legacy_envelope_it_sends(self) -> None:
        """One derivation: the endpoint, the fixture, and this suite build the
        same six-key envelope from the same module."""
        built = expand_envelope.build_envelope(
            expansion_id=0, vector=[0] * 8, ts=1700000000
        )
        self.assertEqual(
            built["commands"], [[0, "expand", [0], [0, 0, 0, 0, 0, 0, 0, 0]]]
        )
        self.assertEqual(sorted(built), sorted(expand_envelope.ENVELOPE_KEYS))
        self.assertIs(compat_service.expand_envelope, expand_envelope)

    def test_the_endpoint_carries_no_land_grid_or_placement_logic(self) -> None:
        """Design D4: the unlock ledger and nothing else."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = source[source.index("def v0_expand()"):]
        route = route[: route.index("@app.errorhandler(400)")]
        import ast

        code_names: List[str] = []
        for node in ast.walk(ast.parse(route)):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
        for forbidden in (
            "terrain",
            "buildable",
            "footprint",
            "placement_bound",
            "grid_size",
            "in_grid",
            "GRID_EXTENT",
            "cell",
            "cells",
            "x",
            "y",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)
        # …and the gap is named rather than left for a reader to discover.
        self.assertIn("No land, grid, cell, or placement-bound effect", route)
        self.assertIn("design D4", route)


class ExpansionSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/expand")  # type: ignore[union-attr]
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
            unknown = CLIENT.get("/v0/expand/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_delivered_state_mutating_routes_still_exist(self) -> None:
        """This is the ninth state-mutating surface; the other eight are
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
            "/v0/expand",
        ):
            with self.subTest(route=route):
                self.assertIn('@app.post("%s")' % route, source)

    def test_the_persistence_scope_names_every_mutating_route(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        scope = source[source.index("Persistence scope"):]
        scope = scope[: scope.index('"""', source.index("Persistence scope"))]
        for route in (
            "/v0/place",
            "/v0/purchase",
            "/v0/move",
            "/v0/sell",
            "/v0/store",
            "/v0/upgrade",
            "/v0/construction",
            "/v0/collect",
            "/v0/expand",
        ):
            with self.subTest(route=route):
                self.assertIn(route, scope)

    def test_the_module_docstring_documents_the_expand_surface(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        for named in (
            "POST /v0/expand",
            "expansions_before",
            "expansions_after",
            "debit",
            "expansion_requirements_unmet",
            "insufficient_resources",
            "already_expanded",
            "unknown_expansion_id",
            "expansion_gold.jpg",
            "expansion_cash.jpg",
        ):
            with self.subTest(named=named):
                self.assertIn(named, source)

    def test_loopback_constants(self) -> None:
        self.assertEqual(compat_service.HOST, "127.0.0.1")
        self.assertEqual(compat_service.DEFAULT_PORT, 5056)

    def test_no_server_is_running(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5055))
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":
    unittest.main()
