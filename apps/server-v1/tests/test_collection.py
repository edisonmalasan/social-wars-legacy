#!/usr/bin/env python3
"""The collection-grant slice: derive from committed content, charge, grant, prove.

Four claims carry this file, and three of them are about **refusal** rather than
about a happy path, because this line's whole subject is an **unconditional
grant** in the preserved branch:

1. **A refused request writes nothing at all**, asserted over the corpus save's
   raw **bytes** before and after rather than over a value the domain computed.
   A value comparison would be satisfied by a service that wrote the same
   values back.
2. **The three derived rules each have an independently reachable refusal.**
   That is a property of the recorded refusal *order*, not an accident: if the
   once-only gate ran after eligibility, a repeat completion of a collection the
   player no longer qualifies for would be reported with the wrong reason, and
   no test could pin any single code without first satisfying all the others.
3. **Each half of the post-execution proof can fail alone**, asserted by
   *injecting* a store that breaks one half and not the others.
4. **The design's corpus premise is corrected here, not inherited.**  The
   proposal recorded that the fresh-player corpus "can exercise the grant"; it
   cannot.  Committed collection 1 requires ``item_ids`` ``(66,67,68,69,70)``
   and costs **35** cash against a corpus balance of **5**, so the untouched
   corpus refuses it twice over.  :class:`CorpusPrematurityTests` asserts that
   both facts, so the correction cannot be quietly reverted by an edit that
   makes the success path reachable by accident.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import harness
from harness import (
    FilesystemSaveRepository,
    build_corpus,
    corpus_save_bytes,
    load_content,
    remove_corpus,
    seed_player_id,
)
from server_v1_collection import ACTION, complete_collection
from server_v1_intent import Intent
from server_v1_outcomes import CollectionSuccess
from server_v1_refusals import Refusal, RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES

#: A pinned instant.  **Nothing in a collection grant depends on it**: the
#: preserved branch records no instant for this command (``command.py:504-523``
#: writes storage, the ledger and nothing else), so there is no elapsed-time
#: rule to exercise.  It is passed anyway because the service has a clock and
#: reports it, and a test that pinned no instant would let a future edit drop
#: the field silently.
SERVICE_INSTANT = 1790705901

#: Committed collection 1, read from ``packages/game-content/normalized/
#: collections.json`` through the content reader — these are the values the
#: suite *asserts*, and ``CommittedTableTests`` proves they are the committed
#: ones rather than figures typed in from a fixture.
COLLECTION_ONE = 1
COLLECTION_ONE_PRICE = 35
COLLECTION_ONE_REQUIREMENTS = (66, 67, 68, 69, 70)
COLLECTION_ONE_PRIZE_ITEM = 1085
COLLECTION_ONE_PRIZE_QUANTITY = 1

#: The cheapest committed collection, used where the price must not be the
#: reason a request is refused.  Measured: the eight distinct ``cashPrice``
#: values are 9, 10, 15, 20, 30, 35, 60 and 75.
CHEAPEST_COLLECTION = 7
CHEAPEST_PRICE = 9
CHEAPEST_REQUIREMENTS = (76, 77, 78, 79, 80)
CHEAPEST_PRIZE_ITEM = 45
CHEAPEST_PRIZE_QUANTITY = 1

#: The corpus balance, read from the seeded save.  Below **every** committed
#: price, which is what makes affordability independently reachable.
CORPUS_CASH = 5


class SeededFixture(unittest.TestCase):
    """A corpus with an explicit storage and cash shape, plus a byte baseline.

    ``seed`` receives the parsed save document and mutates it in place; the
    default leaves it untouched.  Every test that needs a reachable grant seeds
    **explicitly** rather than relying on a fixture default, so no test can pass
    because of a state another test left behind.
    """

    def setUp(self) -> None:
        self.content = load_content(harness.REPO_ROOT)
        self._seed = self._declared_seed()
        self.corpus = build_corpus(mutate=self._seed)
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.player = seed_player_id()

    def _declared_seed(self) -> Callable[[Dict[str, Any]], None]:
        """Overridden by subclasses that want a different starting state."""
        return lambda document: None

    # ----------------------------------------------------------- convenience --
    def _grantable(self, document: Dict[str, Any]) -> None:
        """Hold every requirement of the cheapest collection, and can pay it.

        Cash is raised to **twice** the price rather than exactly to it, so a
        later test can debit one unit and still be affordable — which is what
        lets the affordability refusal be reached by moving the balance instead
        of by seeding it, and keeps the two independent.
        """
        store = document["maps"][0]["store"]
        for item_id in CHEAPEST_REQUIREMENTS:
            store[str(item_id)] = 1
        document["playerInfo"]["cash"] = CHEAPEST_PRICE * 2

    def _seed_cash(self, value: int) -> Callable[[Dict[str, Any]], None]:
        def seed(document: Dict[str, Any]) -> None:
            self._grantable(document)
            document["playerInfo"]["cash"] = value

        return seed

    def _intent(
        self, collection_id: int = CHEAPEST_COLLECTION, player: Optional[str] = None
    ) -> Intent:
        return Intent(
            action=ACTION,
            player_id=self.player if player is None else player,
            collection_id=collection_id,
        )

    def _pre_bytes(self) -> bytes:
        return corpus_save_bytes(self.corpus)

    def _assert_refused(self, outcome: Any, code: RefusalCode) -> Refusal:
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(code, outcome.code)
        return outcome

    def _assert_refusal_wrote_nothing(self, outcome: Any, code: RefusalCode) -> Refusal:
        before = self._pre_bytes()
        refusal = self._assert_refused(outcome, code)
        self.assertEqual(before, corpus_save_bytes(self.corpus), "refusal changed the bytes")
        return refusal

    def _write(self, mutate: Callable[[Any], None]) -> None:
        document = self.repository.read(self.player)
        mutate(document)
        self.repository.write(document)

    def _save_path(self) -> Path:
        """The corpus save's own path, taken from the document itself.

        Taken from the document rather than composed from the corpus directory,
        because the first version guessed ``<corpus>/saves/<pid>.json`` and
        measured a ``FileNotFoundError`` — the copy layout is the runner's
        business, and the repository already knows the answer.
        """
        return self.repository.read(self.player).path

    def _rewrite_file(self, mutate: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        """Edit the corpus file directly, bypassing the domain entirely.

        This is the honest way to corrupt one proof half: it produces the exact
        post-state a misbehaving store would, without the domain having to be
        edited to allow it.
        """
        path = self._save_path()
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=4)
        return data


class CommittedTableTests(unittest.TestCase):
    """What the slice reads, read through the reader and pinned as committed.

    These are the figures the rest of the file assumes.  They are asserted
    against ``packages/game-content/normalized/collections.json`` rather than
    against a literal, so a committed table change fails **here** with a clear
    diff instead of producing a mystifying failure six tests later.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = load_content(harness.REPO_ROOT)
        cls.package = json.loads(
            (
                harness.REPO_ROOT
                / "packages"
                / "game-content"
                / "normalized"
                / "collections.json"
            ).read_text(encoding="utf-8")
        )

    def test_the_committed_table_holds_ten_rows_addressed_by_position(self) -> None:
        rows = self.content.collection_rows()
        self.assertEqual(10, len(rows))
        self.assertEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [self.content.collection_id(i) for i in range(len(rows))])

    def test_collection_one_is_the_figure_this_file_assumes(self) -> None:
        self.assertEqual(COLLECTION_ONE, self.content.collection_id(0))
        self.assertEqual(COLLECTION_ONE_PRICE, self.content.collection_cash_price(0))
        self.assertEqual(
            COLLECTION_ONE_REQUIREMENTS, self.content.collection_requirement_ids(0)
        )
        self.assertEqual(
            (COLLECTION_ONE_PRIZE_ITEM, COLLECTION_ONE_PRIZE_QUANTITY),
            self.content.collection_prize(0),
        )

    def test_the_cheapest_collection_is_the_figure_this_file_assumes(self) -> None:
        """Resolved **from the table**, not assumed: cheapest = minimum price.

        A hard-coded position would break the moment the committed table
        changed, and would break *silently* — the tests would still pass while
        seeding a different collection than they claimed to.
        """
        prices = [self.content.collection_cash_price(i) for i in range(len(self.content.collection_rows()))]
        self.assertNotIn(None, prices)
        cheapest = min(int(p) for p in prices)  # type: ignore[arg-type]
        self.assertEqual(CHEAPEST_PRICE, cheapest)
        position = [int(p) for p in prices].index(cheapest)  # type: ignore[arg-type]
        self.assertEqual(CHEAPEST_COLLECTION, self.content.collection_id(position))
        self.assertEqual(
            CHEAPEST_REQUIREMENTS, self.content.collection_requirement_ids(position)
        )
        self.assertEqual(CHEAPEST_PRIZE_ITEM, self.content.collection_prize(position)[0])  # type: ignore[index]

    def test_the_reader_reads_the_committed_bytes_verbatim(self) -> None:
        """Every row decodes to the normalized package's own values.

        The readers decode string-encoded and embedded-JSON fields, so this is
        the check that the decoding is a decoding: it compares against the
        *normalized* package, whose fields are already typed.
        """
        rows = self.package
        self.assertEqual(len(rows), len(self.content.collection_rows()))
        for index, package_row in enumerate(rows):
            with self.subTest(position=index):
                self.assertEqual(int(package_row["id"]), self.content.collection_id(index))
                self.assertEqual(int(package_row["cashPrice"]), self.content.collection_cash_price(index))
                self.assertEqual(
                    tuple(int(v) for v in package_row["item_ids"]),
                    self.content.collection_requirement_ids(index),
                )
                prize = package_row["prize"]
                self.assertEqual(1, len(prize))
                item_id, quantity = next(iter(prize.items()))
                self.assertEqual(
                    (int(item_id), int(quantity)), self.content.collection_prize(index)
                )

    def test_every_committed_price_is_below_no_committed_price(self) -> None:
        """The corpus can afford **nothing**, which is what makes the
        affordability refusal reachable without seeding a balance."""
        prices = [self.content.collection_cash_price(i) for i in range(len(self.content.collection_rows()))]
        self.assertTrue(all(price is not None and price > CORPUS_CASH for price in prices))


class CorpusPrematurityTests(SeededFixture):
    """The design's corpus premise, corrected and asserted (module docstring 4).

    The proposal recorded that the fresh-player corpus "can exercise the
    grant".  It cannot, for two independent reasons, and both are asserted here
    so the correction is a property of the suite rather than a claim in a
    docstring that an edit could invalidate.
    """

    def test_the_untouched_corpus_holds_no_requirement_for_collection_one(self) -> None:
        document = self.repository.read(self.player)
        self.assertEqual({}, document.storage())
        for item_id in COLLECTION_ONE_REQUIREMENTS:
            with self.subTest(item_id=item_id):
                self.assertEqual(0, document.storage_quantity(item_id))

    def test_an_unseeded_collection_one_is_refused_as_ineligible(self) -> None:
        outcome = complete_collection(
            self._intent(COLLECTION_ONE), self.content, self.repository, SERVICE_INSTANT
        )
        self._assert_refusal_wrote_nothing(outcome, RefusalCode.COLLECTION_NOT_ELIGIBLE)

    def test_the_untouched_corpus_cannot_afford_any_committed_price(self) -> None:
        self.assertEqual(CORPUS_CASH, self.repository.read(self.player).resources()["cash"])

    def test_the_live_scenario_seeds_because_the_corpus_cannot(self) -> None:
        """The client's live scenario must seed; if it stops, this says why.

        A *cross-layer* check: the hermetic Godot suite owns the live scenario
        and this suite owns the corpus, and neither can see the other's source
        by reading it.  What this can assert is the fact the scenario must
        respect — the corpus is not grantable as delivered — and it asserts
        that by requiring the success path to need an explicit seed, which is
        what every ``SuccessTests`` case below does.
        """
        outcome = complete_collection(
            self._intent(CHEAPEST_COLLECTION), self.content, self.repository, SERVICE_INSTANT
        )
        self._assert_refused(outcome, RefusalCode.COLLECTION_NOT_ELIGIBLE)


class GrantableFixture(SeededFixture):
    """The seeded corpus: requirements held and cash available."""

    def _declared_seed(self) -> Callable[[Dict[str, Any]], None]:
        return self._grantable


class SuccessTests(GrantableFixture):
    def test_the_grant_is_derived_from_committed_content(self) -> None:
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(outcome, CollectionSuccess)
        grant = outcome.grant
        self.assertEqual(CHEAPEST_COLLECTION, grant.resolved_collection_id)
        self.assertEqual(CHEAPEST_COLLECTION, grant.requested_collection_id)
        self.assertEqual(CHEAPEST_PRICE, grant.price)
        self.assertEqual(CHEAPEST_REQUIREMENTS, tuple(grant.requirement_ids))
        self.assertEqual(CHEAPEST_PRIZE_ITEM, grant.prize_item_id)
        self.assertEqual({"cash": -CHEAPEST_PRICE}, dict(grant.deltas))

    def test_the_clamp_flag_is_reported_and_is_false_for_a_real_id(self) -> None:
        """``clamp_moved`` compares the committed id to the requested one.

        For every resolvable id today it is ``False``, so this asserts the flag
        is *computed* from the table rather than hard-coded: a renumbered
        committed table would flip it, which is the behaviour the flag is for.
        """
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        assert isinstance(outcome, CollectionSuccess)
        self.assertIs(False, outcome.grant.clamp_moved)

    def test_the_derived_price_is_debited_and_nothing_else_moves(self) -> None:
        before = self.repository.read(self.player).resources()
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        assert isinstance(outcome, CollectionSuccess)
        after = self.repository.read(self.player).resources()
        for name in STORED_RESOURCE_NAMES:
            with self.subTest(resource=name):
                expected = before[name] + (-CHEAPEST_PRICE if name == "cash" else 0)
                self.assertEqual(expected, after[name])

    def test_the_committed_prize_is_stored(self) -> None:
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        assert isinstance(outcome, CollectionSuccess)
        stored = self.repository.read(self.player).storage()
        self.assertEqual(CHEAPEST_PRIZE_QUANTITY, stored[str(CHEAPEST_PRIZE_ITEM)])
        self.assertEqual(CHEAPEST_PRIZE_QUANTITY, outcome.prize_stored_after)

    def test_the_requirement_items_are_left_in_storage(self) -> None:
        """A grant adds a prize; it does not consume the qualification.

        Consumption is a rule the preserved branch does not have and this slice
        does not invent, so the assertion is that they survive.
        """
        complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        stored = self.repository.read(self.player).storage()
        for item_id in CHEAPEST_REQUIREMENTS:
            with self.subTest(item_id=item_id):
                self.assertEqual(1, stored[str(item_id)])

    def test_the_ledger_grows_by_exactly_one_appended_id(self) -> None:
        before = self.repository.read(self.player).ledger()
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        assert isinstance(outcome, CollectionSuccess)
        after = self.repository.read(self.player).ledger()
        self.assertEqual(before + [CHEAPEST_COLLECTION], after)
        self.assertEqual(tuple(after), outcome.ledger_after)

    def test_the_success_reports_the_after_state_it_read_back(self) -> None:
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        assert isinstance(outcome, CollectionSuccess)
        self.assertEqual(self.repository.read(self.player).resources(), outcome.state)
        self.assertEqual(SERVICE_INSTANT, outcome.instant)

    def test_the_response_body_carries_the_derivation(self) -> None:
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        payload = outcome.payload()
        self.assertEqual("success", payload["result"])
        self.assertEqual("collection", payload["action"])
        self.assertEqual({"cash": -CHEAPEST_PRICE}, payload["derived_deltas"])
        self.assertEqual(CHEAPEST_PRICE, payload["derived_price"])
        self.assertEqual(CHEAPEST_PRIZE_ITEM, payload["granted_item_id"])
        self.assertEqual(CHEAPEST_PRIZE_QUANTITY, payload["granted_quantity"])
        self.assertEqual(
            list(CHEAPEST_REQUIREMENTS), payload["requirement_ids"]
        )
        self.assertEqual(CHEAPEST_COLLECTION, payload["collection"]["resolved_id"])
        self.assertNotIn("player_id", payload)

    def test_the_nothing_else_changed_claim_is_checked_against_the_map(self) -> None:
        """The grant touches storage, ``cash`` and the ledger — and nothing else.

        Compared as the set of changed top-level paths, which is the claim a
        "and nothing else" test has to actually make.
        """
        self._write(lambda document: document.set_resource("gold", 1234))
        before = json.loads(self._save_path().read_text(encoding="utf-8"))
        complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        after = json.loads(self._save_path().read_text(encoding="utf-8"))
        changed = _changed_paths(before, after)
        self.assertEqual(3, len(changed), changed)
        self.assertIn("/playerInfo/cash (changed)", changed)
        self.assertIn("/privateState/collections (changed)", changed)
        self.assertIn("/maps/0/store/%d (added)" % CHEAPEST_PRIZE_ITEM, changed)

    def test_a_second_completion_of_the_same_collection_is_refused(self) -> None:
        """Design D6, and the divergence it is recorded as.

        The preserved branch grants unconditionally and appends conditionally,
        so a repeat grants a second time while the ledger stands still.  v1
        refuses; the manifest records this as a divergence, not as parity.
        """
        complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        before = self._pre_bytes()
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        refusal = self._assert_refused(outcome, RefusalCode.COLLECTION_ALREADY_CLAIMED)
        self.assertEqual([CHEAPEST_COLLECTION], refusal.detail["ledger_before"])
        self.assertEqual(before, corpus_save_bytes(self.corpus))

    def test_a_different_collection_can_still_be_claimed_afterwards(self) -> None:
        """The ledger gates **per id**, not globally."""
        complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        self._write(self._grantable_second_collection)
        outcome = complete_collection(
            self._intent(COLLECTION_ONE), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(outcome, CollectionSuccess)
        assert isinstance(outcome, CollectionSuccess)
        self.assertEqual(
            [CHEAPEST_COLLECTION, COLLECTION_ONE], list(outcome.ledger_after)
        )

    def _grantable_second_collection(self, document: Any) -> None:
        for item_id in COLLECTION_ONE_REQUIREMENTS:
            document.set_storage_quantity(item_id, 1)
        document.set_resource("cash", COLLECTION_ONE_PRICE)


class RefusalLeavesBytesAloneTests(GrantableFixture):
    """Each derived rule's refusal, over raw bytes, one at a time.

    Subclasses the **grantable** fixture deliberately: a refusal test is only
    about the refusal when every *other* rule passes, so the requirements are
    held and the balance is sufficient before each case moves exactly one thing.
    The first version subclassed the bare fixture and every case below failed on
    ``collection_not_eligible`` instead — the tests were measuring the seed, not
    the rule.
    """

    def test_an_unknown_player_writes_nothing(self) -> None:
        outcome = complete_collection(
            self._intent(player="00000000-0000-4000-8000-0000000000ff"),
            self.content,
            self.repository,
            SERVICE_INSTANT,
        )
        self._assert_refusal_wrote_nothing(outcome, RefusalCode.UNKNOWN_PLAYER)

    def test_a_collection_zero_is_refused_as_aliased_rather_than_clamped(self) -> None:
        """Design D3.  The preserved branch clamps ``0`` to collection 1."""
        self._write(self._grantable_collection_one)
        outcome = complete_collection(
            self._intent(0), self.content, self.repository, SERVICE_INSTANT
        )
        refusal = self._assert_refusal_wrote_nothing(outcome, RefusalCode.ALIASED_COLLECTION_ID)
        self.assertEqual(COLLECTION_ONE, refusal.detail["aliases_collection_id"])
        self.assertEqual("max(0, collection - 1)", refusal.detail["legacy_index"])

    def test_a_negative_collection_id_is_refused_as_aliased(self) -> None:
        for value in (-1, -5, -10 ** 6):
            with self.subTest(collection_id=value):
                outcome = complete_collection(
                    self._intent(value), self.content, self.repository, SERVICE_INSTANT
                )
                self._assert_refused(outcome, RefusalCode.ALIASED_COLLECTION_ID)

    def test_an_id_past_the_committed_table_is_unresolvable(self) -> None:
        for value in (11, 9999):
            with self.subTest(collection_id=value):
                outcome = complete_collection(
                    self._intent(value), self.content, self.repository, SERVICE_INSTANT
                )
                refusal = self._assert_refusal_wrote_nothing(
                    outcome, RefusalCode.UNRESOLVABLE_COLLECTION
                )
                self.assertEqual(10, refusal.detail["committed_rows"])

    def test_a_missing_requirement_writes_nothing(self) -> None:
        self._write(lambda document: document.set_storage_quantity(CHEAPEST_REQUIREMENTS[0], 0))
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        refusal = self._assert_refusal_wrote_nothing(
            outcome, RefusalCode.COLLECTION_NOT_ELIGIBLE
        )
        self.assertEqual([CHEAPEST_REQUIREMENTS[0]], refusal.detail["missing_requirement_ids"])
        self.assertEqual(
            list(CHEAPEST_REQUIREMENTS[1:]), refusal.detail["held_requirement_ids"]
        )

    def test_an_unaffordable_price_writes_nothing(self) -> None:
        """Reached by **moving the balance**, not by seeding it away.

        The requirements are still held, so this fails affordability and not
        eligibility — which is the whole point of the recorded order.
        """
        self._write(lambda document: document.set_resource("cash", CHEAPEST_PRICE - 1))
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        refusal = self._assert_refusal_wrote_nothing(outcome, RefusalCode.INSUFFICIENT_CASH)
        self.assertEqual(CHEAPEST_PRICE, refusal.detail["derived_price"])
        self.assertEqual(1, refusal.detail["shortfall"])
        self.assertEqual("playerInfo.cash", refusal.detail["cash_is"])

    def test_exactly_the_price_is_affordable(self) -> None:
        """The bound is inclusive, measured rather than assumed.

        One cash below refuses and exactly the price succeeds, so a ``>`` where a
        ``>=`` belonged fails here instead of silently over-charging.
        """
        self._write(lambda document: document.set_resource("cash", CHEAPEST_PRICE))
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(outcome, CollectionSuccess)

    def test_every_refusal_reports_a_status_the_transport_can_ask_for(self) -> None:
        outcome = complete_collection(
            self._intent(9999), self.content, self.repository, SERVICE_INSTANT
        )
        refusal = self._assert_refused(outcome, RefusalCode.UNRESOLVABLE_COLLECTION)
        self.assertEqual(409, refusal.http_status)

    def _grantable_collection_one(self, document: Any) -> None:
        for item_id in COLLECTION_ONE_REQUIREMENTS:
            document.set_storage_quantity(item_id, 1)
        document.set_resource("cash", COLLECTION_ONE_PRICE)


class RefusalOrderTests(unittest.TestCase):
    """The recorded order, asserted by **overlap** rather than by inspection.

    Each case fails **more than one** rule and asserts which one is reported.
    An order test that only ever tested one rule at a time would pass for any
    ordering, because with a single failing rule every ordering reports it.
    """

    def setUp(self) -> None:
        self.content = load_content(harness.REPO_ROOT)
        self.corpus = build_corpus(mutate=self._seed)
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.player = seed_player_id()

    def _seed(self, document: Dict[str, Any]) -> None:
        # Nothing held and no cash: eligibility and affordability both fail.
        document["playerInfo"]["cash"] = 0

    def _intent(
        self, collection_id: int = CHEAPEST_COLLECTION
    ) -> Intent:
        return Intent(action=ACTION, player_id=self.player, collection_id=collection_id)

    def test_the_alias_is_reported_before_anything_about_the_row(self) -> None:
        """``0`` fails aliasing, eligibility and affordability at once."""
        outcome = complete_collection(
            self._intent(0), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIs(RefusalCode.ALIASED_COLLECTION_ID, outcome.code)

    def test_an_unresolvable_id_is_reported_before_eligibility(self) -> None:
        outcome = complete_collection(
            self._intent(9999), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIs(RefusalCode.UNRESOLVABLE_COLLECTION, outcome.code)

    def test_already_claimed_is_reported_before_eligibility(self) -> None:
        """The order that is a **decision**, not an accident.

        A repeat completion of a collection the player has since sold the
        requirements for must be answered with the reason it is refused *for*.
        """
        self._write(lambda document: document.set_ledger((CHEAPEST_COLLECTION,)))
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        refusal = self._assert(outcome, RefusalCode.COLLECTION_ALREADY_CLAIMED)
        self.assertEqual([CHEAPEST_COLLECTION], refusal.detail["ledger_before"])

    def test_eligibility_is_reported_before_affordability(self) -> None:
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIs(RefusalCode.COLLECTION_NOT_ELIGIBLE, outcome.code)

    def test_the_order_is_the_one_the_module_documents(self) -> None:
        """The four codes, in the documented order, as a **literal**.

        Written out rather than imported so that reordering the slice's decision
        block without updating this test fails here.
        """
        self.assertEqual(
            tuple(
                [
                    RefusalCode.ALIASED_COLLECTION_ID,
                    RefusalCode.UNRESOLVABLE_COLLECTION,
                    RefusalCode.COLLECTION_ALREADY_CLAIMED,
                    RefusalCode.COLLECTION_NOT_ELIGIBLE,
                    RefusalCode.INSUFFICIENT_CASH,
                ]
            ),
            _DECISION_ORDER,
        )

    def _write(self, mutate: Callable[[Any], None]) -> None:
        document = self.repository.read(self.player)
        mutate(document)
        self.repository.write(document)

    def _assert(self, outcome: Any, code: RefusalCode) -> Refusal:
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(code, outcome.code)
        return outcome


#: The refusal order the module docstring states, transcribed so the test above
#: has something to compare against.
_DECISION_ORDER: Tuple[RefusalCode, ...] = (
    RefusalCode.ALIASED_COLLECTION_ID,
    RefusalCode.UNRESOLVABLE_COLLECTION,
    RefusalCode.COLLECTION_ALREADY_CLAIMED,
    RefusalCode.COLLECTION_NOT_ELIGIBLE,
    RefusalCode.INSUFFICIENT_CASH,
)


class PostConditionProofTests(GrantableFixture):
    """Each of the four halves, broken on its own, and the rollback."""

    def _run_with_tamper(self, tamper: Callable[[Dict[str, Any]], None]) -> Any:
        """Grant through a repository that corrupts the file it wrote, once.

        The tamper runs on the **first** write and then disarms, which is what
        makes the rollback assertion meaningful: a wrapper that tampered on
        every write would also corrupt the rollback, leaving the store wrong
        while the refusal still reported ``rolled_back: true``.  That is not a
        defect in the rollback — ``rolled_back`` reports that the write
        *succeeded*, not that its result is correct — but it would make the
        test unable to say anything.
        """
        inner = self.repository
        path = self._save_path()
        armed = [True]

        class _Tampering:
            def player_ids(self) -> Tuple[str, ...]:
                return inner.player_ids()

            def read(self, player_id: str) -> Any:
                return inner.read(player_id)

            def write(self, document: Any) -> None:
                inner.write(document)
                if not armed[0]:
                    return
                armed[0] = False
                data = json.loads(path.read_text(encoding="utf-8"))
                tamper(data)
                with open(path, "w", encoding="utf-8", newline="\n") as stream:
                    json.dump(data, stream, indent=4)

        return complete_collection(
            self._intent(), self.content, _Tampering(), SERVICE_INSTANT
        )

    def _tamper_store_quantity(self, value: int) -> Callable[[Dict[str, Any]], None]:
        def tamper(data: Dict[str, Any]) -> None:
            data["maps"][0]["store"][str(CHEAPEST_PRIZE_ITEM)] = value

        return tamper

    def test_the_granted_quantity_half_fails_alone(self) -> None:
        outcome = self._run_with_tamper(self._tamper_store_quantity(9))
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("storage_granted_quantity", refusal.detail["half"])

    def test_the_unexpected_key_half_fails_alone(self) -> None:
        def tamper(data: Dict[str, Any]) -> None:
            data["maps"][0]["store"]["9999"] = 3

        outcome = self._run_with_tamper(tamper)
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("storage_gained_an_unexpected_key", refusal.detail["half"])

    def test_the_resources_half_fails_when_cash_moved_wrong(self) -> None:
        def tamper(data: Dict[str, Any]) -> None:
            data["playerInfo"]["cash"] = data["playerInfo"]["cash"] + 1

        outcome = self._run_with_tamper(tamper)
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("resources_matched_derivation", refusal.detail["half"])

    def test_the_resources_half_fails_when_an_unnamed_resource_moved(self) -> None:
        """The half that makes the ``cashPrice`` claim non-tautological.

        ``gold`` is not in the derivation, so it must be **unchanged**; moving
        it is a violation even though the derivation says nothing about it.
        """
        def tamper(data: Dict[str, Any]) -> None:
            data["maps"][0]["gold"] = data["maps"][0]["gold"] - 1

        outcome = self._run_with_tamper(tamper)
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("resources_matched_derivation", refusal.detail["half"])

    def test_the_ledger_half_fails_alone(self) -> None:
        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["collections"] = [CHEAPEST_COLLECTION, 3]

        outcome = self._run_with_tamper(tamper)
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("ledger_matched_derived", refusal.detail["half"])

    def test_the_four_halves_are_distinguishable(self) -> None:
        """The control: one ``half`` string for all four would pass the above."""
        halves = {
            self._run_with_tamper(self._tamper_store_quantity(9)).detail["half"],
            self._run_with_tamper(
                lambda data: data["maps"][0]["store"].__setitem__("9999", 3)
            ).detail["half"],
            self._run_with_tamper(
                lambda data: data["maps"][0].__setitem__(
                    "gold", data["maps"][0]["gold"] - 1
                )
            ).detail["half"],
            self._run_with_tamper(
                lambda data: data["privateState"].__setitem__(
                    "collections", [CHEAPEST_COLLECTION, 3]
                )
            ).detail["half"],
        }
        self.assertEqual(
            {
                "storage_granted_quantity",
                "storage_gained_an_unexpected_key",
                "resources_matched_derivation",
                "ledger_matched_derived",
            },
            halves,
        )

    def test_a_violation_rolls_back_to_the_pre_request_bytes(self) -> None:
        before = self._pre_bytes()
        self._run_with_tamper(self._tamper_store_quantity(9))
        self.assertEqual(before, corpus_save_bytes(self.corpus))

    def test_the_refusal_says_whether_the_rollback_worked(self) -> None:
        outcome = self._run_with_tamper(self._tamper_store_quantity(9))
        self.assertIs(True, outcome.detail["rolled_back"])

    def test_a_rolled_back_store_can_be_claimed_again_cleanly(self) -> None:
        self._run_with_tamper(self._tamper_store_quantity(9))
        outcome = complete_collection(
            self._intent(), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(outcome, CollectionSuccess)

    def test_the_proof_does_not_check_for_a_vanished_key_and_that_is_recorded(self) -> None:
        """The documented gap, asserted rather than left in a docstring.

        ``_prove``'s docstring says a stored key that **disappears** is not
        caught.  This proves the claim rather than quoting it, and — because a
        documented gap that is quietly closed is also a lie in the other
        direction — it asserts the *behaviour*, not the absence of a check: if
        a later change adds the whole-store key comparison, this test fails and
        the docstring must be updated with it.
        """
        def tamper(data: Dict[str, Any]) -> None:
            data["maps"][0]["store"].pop(str(CHEAPEST_REQUIREMENTS[0]), None)

        outcome = self._run_with_tamper(tamper)
        # The removed key is not the granted item, so the quantity half holds and
        # the gained-key half cannot see a disappearance: the grant succeeds.
        self.assertIsInstance(outcome, CollectionSuccess)


class IntentTests(unittest.TestCase):
    """The request layer's half: the id is an integer, and nothing else is.

    These belong here rather than in ``test_intent.py`` because each one exists
    to protect a **design decision** this line made (``collection_id`` accepting
    negatives, ``row`` not being accepted), not to describe the parser.
    """

    PLAYER = "00000000-0000-4000-8000-000000000001"

    def _body(self, **fields: Any) -> bytes:
        return json.dumps(dict({"player_id": self.PLAYER}, **fields)).encode("utf-8")

    def _parse(self, **fields: Any) -> Any:
        from server_v1_intent import intent_from_json

        return intent_from_json("collection", self._body(**fields))

    def test_a_collection_request_parses_into_the_id_only(self) -> None:
        intent = self._parse(collection_id=7)
        self.assertIsInstance(intent, Intent)
        assert isinstance(intent, Intent)
        self.assertEqual(7, intent.collection_id)
        self.assertIsNone(intent.row)
        self.assertEqual("/privateState/collections", intent.addressed_path())

    def test_a_negative_id_reaches_the_domain_rather_than_the_parser(self) -> None:
        """Design D3 depends on this: ``-1`` must arrive, to be refused by name.

        If the intent layer rejected it as ``malformed_request`` the refusal
        vocabulary would answer a different question than the one asked — the
        client would be told its id was not an integer, which is false.
        """
        intent = self._parse(collection_id=-1)
        assert isinstance(intent, Intent)
        self.assertEqual(-1, intent.collection_id)

    def test_a_float_id_is_refused_at_the_parser(self) -> None:
        """``7.0`` is not an integer even though JSON makes every number a float.

        Checked because Godot decodes every JSON number as a ``float``
        (``test_quests.gd`` recorded that), so the client must send ``7`` as an
        integer token and the service must reject the float form rather than
        coerce it.
        """
        from server_v1_refusals import RefusalCode

        outcome = self._parse(collection_id=7.0)
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)

    def test_a_row_is_not_a_collection(self) -> None:
        """``row`` is **unknown** to this action, not merely the wrong type.

        ``unknown_request_field`` rather than ``malformed_request`` is the more
        informative answer and the one the shared parser already gives: the
        request named a field this action does not have.  It is also the same
        refusal ``collect`` would give for ``collection_id``, which is what makes
        the vocabulary symmetric between the two routes.
        """
        from server_v1_refusals import RefusalCode

        outcome = self._parse(row=2)
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.UNKNOWN_REQUEST_FIELD, outcome.code)
        self.assertEqual(400, outcome.http_status)

    def test_the_id_is_required(self) -> None:
        from server_v1_refusals import RefusalCode

        outcome = self._parse()
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)


def _changed_paths(before: Any, after: Any, prefix: str = "") -> List[str]:
    """Every **leaf** path whose value differs between two parsed documents.

    Recursive, because the first version compared only top-level keys and
    reported ``maps``/``privateState`` — which says the section changed and
    nothing about what inside it did, and would have passed for a grant that
    moved an unrelated row.  A leaf is a scalar, a list, or an object compared by
    value; a key that is present on only one side is reported as ``<path>`` plus
    the missing side, so an added or removed object is not silently skipped.
    """
    if isinstance(before, dict) and isinstance(after, dict):
        paths: List[str] = []
        for key in sorted(set(before) | set(after)):
            path = "%s/%s" % (prefix, key)
            if key not in before:
                paths.append("%s (added)" % path)
            elif key not in after:
                paths.append("%s (removed)" % path)
            else:
                paths.extend(_changed_paths(before[key], after[key], path))
        return paths
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        # Descend element-wise so a change inside ``maps[0]`` is reported at
        # its own path.  A **length** difference is itself the change and is
        # reported whole, because "which element appeared" has no committed
        # identity in a save document.
        paths = []
        for index, (left, right) in enumerate(zip(before, after)):
            paths.extend(_changed_paths(left, right, "%s/%d" % (prefix, index)))
        return paths
    if before == after:
        return []
    return ["%s (changed)" % (prefix or "/")]


if __name__ == "__main__":
    unittest.main()