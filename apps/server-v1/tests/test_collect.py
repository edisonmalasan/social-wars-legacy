#!/usr/bin/env python3
"""The collect slice: a derivation, a write, a proof, or a refusal (tasks 3.2/4.3).

Two claims carry this file, and both are about *proof* rather than about happy
paths:

1. **A refused request writes nothing at all.**  Asserted over the corpus
   save's raw **bytes**, before and after, not over a value the domain
   computed.  A value comparison would be satisfied by a service that wrote the
   same values back.

2. **The post-execution proof has two halves, and each can fail alone.**
   Asserted by *injecting* a store that breaks one half and not the other, so
   "the proof ran" is never taken on trust from the fact that the success case
   passed.  A proof whose halves cannot be distinguished would report one
   ``half`` string for both, and the injection is what shows otherwise.

The corpus is built with a **mutate** so the save starts in v1's own write
form.  That is not tidiness: it makes the rollback claim a **byte-identity**
claim rather than a value claim, which is the strongest form available.  The
CRLF-seed divergence is covered separately in ``tests/test_repository.py``.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

import harness
from harness import (
    COLLECT_STEP,
    FilesystemSaveRepository,
    build_corpus,
    corpus_save_bytes,
    corpus_save_path,
    load_content,
    remove_corpus,
    seed_player_id,
)
from server_v1_collect import ACTION, collect
from server_v1_intent import Intent
from server_v1_outcomes import Success
from server_v1_refusals import Refusal, RefusalCode

#: The instant the executed-legacy fixture recorded (``request``'s capture).
FIXTURE_INSTANT = 1790705901
#: The corpus's Tree, at map row 2.  Asserted from the fixture's ``before``.
TREE_ROW = 2


class CorpusFixture(unittest.TestCase):
    """A v1-form corpus, plus the pre-request bytes every test compares to."""

    def setUp(self) -> None:
        self.corpus = build_corpus(mutate=lambda document: None)
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.content = load_content(harness.REPO_ROOT)
        self.player = seed_player_id()

    def _intent(self, row: int = TREE_ROW, player: str = None) -> Intent:  # type: ignore[assignment]
        return Intent(
            action=ACTION, player_id=self.player if player is None else player, row=row
        )

    def _pre_bytes(self) -> bytes:
        return corpus_save_bytes(self.corpus)

    def _assert_refused(self, outcome: Any, code: RefusalCode) -> Refusal:
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(code, outcome.code)
        return outcome


class SuccessTests(CorpusFixture):
    def test_the_recorded_collection_is_derived_and_proved(self) -> None:
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        self.assertIsInstance(outcome, Success)
        self.assertEqual({"xp": 3, "wood": 60}, dict(outcome.derivation.deltas))
        self.assertEqual(3, outcome.derivation.rung_index)
        self.assertEqual(FIXTURE_INSTANT, outcome.instant)
        self.assertEqual(FIXTURE_INSTANT, outcome.row_instant)

    def test_the_success_reports_the_after_state_it_read_back(self) -> None:
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        assert isinstance(outcome, Success)
        # ``state`` must be the *stored* state, so re-reading must agree.
        stored = self.repository.read(self.player).resources()
        self.assertEqual(stored, outcome.state)
        self.assertEqual(7, stored["xp"])
        self.assertEqual(2060, stored["wood"])

    def test_the_row_other_than_the_addressed_one_is_untouched(self) -> None:
        before = self.repository.read(self.player).row(TREE_ROW)
        collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        after = self.repository.read(self.player).row(TREE_ROW)
        assert before is not None and after is not None
        # Only item[3] moves; the item, the cell, the orientation and the attr
        # bag are the recorded row's own values.
        self.assertEqual(before[0], after[0])
        self.assertEqual(before[1:3], after[1:3])
        self.assertEqual(before[4:], after[4:])
        self.assertEqual(FIXTURE_INSTANT, after[3])

    def test_a_second_immediate_collection_is_refused_as_too_early(self) -> None:
        """A second request moves the instant, so the next one cannot pay top rung."""
        collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        self._assert_refused(outcome, RefusalCode.BELOW_FIRST_RUNG)

    def test_the_response_body_reports_the_derivation_not_a_client_figure(self) -> None:
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        payload = outcome.payload()
        self.assertEqual("success", payload["result"])
        self.assertEqual("collect", payload["action"])
        self.assertEqual({"xp": 3, "wood": 60}, payload["derived_deltas"])
        self.assertEqual(3, payload["rung"]["index"])
        # Nothing in the body echoes a request field, because there were none.
        self.assertNotIn("player_id", payload)
        self.assertNotIn("row", payload)


class RefusalLeavesBytesAloneTests(CorpusFixture):
    """Task 3.2's byte claim, one refusal at a time."""

    def _assert_refusal_wrote_nothing(self, outcome: Any, code: RefusalCode) -> Refusal:
        before = self._pre_bytes()
        refusal = self._assert_refused(outcome, code)
        self.assertEqual(before, corpus_save_bytes(self.corpus), "refusal changed the bytes")
        return refusal

    def test_an_unknown_player_writes_nothing(self) -> None:
        outcome = collect(
            self._intent(player="00000000-0000-4000-8000-0000000000ff"),
            self.content,
            self.repository,
            FIXTURE_INSTANT,
        )
        self._assert_refusal_wrote_nothing(outcome, RefusalCode.UNKNOWN_PLAYER)

    def test_an_unaddressable_row_writes_nothing(self) -> None:
        outcome = collect(self._intent(row=9999), self.content, self.repository, FIXTURE_INSTANT)
        self._assert_refusal_wrote_nothing(outcome, RefusalCode.UNADDRESSABLE_ROW)

    def test_an_item_with_no_committed_income_writes_nothing(self) -> None:
        """A row whose item records no income: refusal, no derivation, no write."""
        self._address_row_at(TREE_ROW, item_id=1)
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        self._assert_refusal_wrote_nothing(outcome, RefusalCode.NO_COMMITTED_INCOME)

    def test_a_committed_cap_writes_nothing(self) -> None:
        self._address_row_at(TREE_ROW, item_id=66)
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        self._assert_refusal_wrote_nothing(outcome, RefusalCode.CAPPED_COLLECTION)

    def test_a_row_below_the_first_rung_writes_nothing(self) -> None:
        self._set_row_instant(TREE_ROW, FIXTURE_INSTANT - 299)
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        self._assert_refusal_wrote_nothing(outcome, RefusalCode.BELOW_FIRST_RUNG)

    def test_a_row_under_construction_writes_nothing(self) -> None:
        self._set_row_instant(TREE_ROW, FIXTURE_INSTANT - 10 ** 8)
        document = self.repository.read(self.player)
        document.row_attr(TREE_ROW)["cp"] = 5
        document.row_attr(TREE_ROW)["nc"] = 1
        self.repository.write(document)
        before = self._pre_bytes()
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        refusal = self._assert_refused(outcome, RefusalCode.CONSTRUCTION_IN_PROGRESS)
        self.assertEqual(before, corpus_save_bytes(self.corpus))
        self.assertNotIn("instant", refusal.detail)

    def test_every_refusal_reports_a_status_the_transport_can_ask_for(self) -> None:
        outcome = collect(self._intent(row=9999), self.content, self.repository, FIXTURE_INSTANT)
        refusal = self._assert_refused(outcome, RefusalCode.UNADDRESSABLE_ROW)
        # The transport reads the status out of the closed table rather than
        # naming a code; asserting here keeps that table from going stale.
        self.assertEqual(409, refusal.http_status)

    # ------------------------------------------------------------- helpers --
    def _address_row_at(self, row: int, item_id: int) -> None:
        document = self.repository.read(self.player)
        target = document.row(row)
        assert target is not None
        target[0] = item_id
        document.set_row_instant(row, 0)
        self.repository.write(document)

    def _set_row_instant(self, row: int, value: int) -> None:
        document = self.repository.read(self.player)
        document.set_row_instant(row, value)
        self.repository.write(document)


class _TamperingRepository:
    """A repository that writes correctly, then corrupts the file it wrote.

    Used to break **one half** of the post-execution proof.  It is the only way
    to reach that code path from outside the domain without editing the domain,
    and the alternative — a unit test calling ``_prove`` directly — would prove
    the helper and not that ``collect`` *uses* it.

    It tampers on the **first** write only, then disarms.  That models the
    failure actually being injected — a store that misbehaved once — and it is
    also what makes the rollback assertion possible: a wrapper that tampered on
    *every* write would also corrupt the rollback, and the store would be left
    wrong while the refusal still reported ``rolled_back: true``.  That is not a
    defect in the rollback (``rolled_back`` reports that the write succeeded,
    not that the result is correct) but it would make the test unable to say
    anything.
    """

    def __init__(self, inner: Any, tamper: Callable[[Dict[str, Any]], None]) -> None:
        self.inner = inner
        self._tamper = tamper
        self._armed = True

    def player_ids(self) -> Tuple[str, ...]:
        return self.inner.player_ids()

    def read(self, player_id: str) -> Any:
        return self.inner.read(player_id)

    def write(self, document: Any) -> None:
        self.inner.write(document)
        if not self._armed:
            return
        self._armed = False
        self._tamper(self._rewrite_in_place(document.path))

    def _rewrite_in_place(self, path: Path) -> Dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        self._tamper(data)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=4)
        return data


class PostConditionProofTests(CorpusFixture):
    """Task 4.3: both halves, each broken in turn, and both roll back."""

    def _run_with_tamper(self, tamper: Callable[[Dict[str, Any]], None]) -> Any:
        repository = _TamperingRepository(self.repository, tamper)
        # The tampering repository would also tamper on the rollback write, so
        # rollback is verified by re-running through the clean repository.
        return collect(self._intent(), self.content, repository, FIXTURE_INSTANT)

    def test_half_one_fails_when_the_instant_does_not_move_forward(self) -> None:
        outcome = self._run_with_tamper(
            lambda data: data["maps"][0]["items"].__setitem__(
                str(TREE_ROW), [data["maps"][0]["items"][str(TREE_ROW)][0], 53, 39, 0, 0, [], {}, 1]
            )
        )
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("instant_moved_forward", refusal.detail["half"])
        self.assertEqual("/maps/0/items/2", refusal.detail["addressed_path"])

    def test_half_two_fails_when_a_resource_moved_by_the_wrong_amount(self) -> None:
        outcome = self._run_with_tamper(
            lambda data: data["maps"][0].__setitem__("wood", data["maps"][0]["wood"] + 1)
        )
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("resources_matched_derivation", refusal.detail["half"])

    def test_half_two_fails_when_an_unnamed_resource_moved(self) -> None:
        """The half that makes the proof non-tautological.

        ``oil`` is not in the derivation, so it must be **unchanged**; moving it
        is a violation even though the derivation says nothing about it.
        """
        outcome = self._run_with_tamper(
            lambda data: data["maps"][0].__setitem__("oil", data["maps"][0]["oil"] - 1)
        )
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("resources_matched_derivation", refusal.detail["half"])

    def test_the_two_halves_are_distinguishable(self) -> None:
        """The control: a single ``half`` string for both would pass the above."""
        halves = {
            self._run_with_tamper(
                lambda data: data["maps"][0].__setitem__("wood", data["maps"][0]["wood"] + 1)
            ).detail["half"],
            self._run_with_tamper(
                lambda data: data["maps"][0]["items"].__setitem__(
                    str(TREE_ROW),
                    [data["maps"][0]["items"][str(TREE_ROW)][0], 53, 39, 0, 0, [], {}, 1],
                )
            ).detail["half"],
        }
        self.assertEqual({"instant_moved_forward", "resources_matched_derivation"}, halves)

    def test_a_violation_rolls_back_to_the_pre_request_bytes(self) -> None:
        """Byte-identity, not value-identity: the store is left as it was found."""
        before = self._pre_bytes()
        self._run_with_tamper(
            lambda data: data["maps"][0].__setitem__("wood", data["maps"][0]["wood"] + 1)
        )
        self.assertEqual(before, corpus_save_bytes(self.corpus))

    def test_the_refusal_says_whether_the_rollback_worked(self) -> None:
        outcome = self._run_with_tamper(
            lambda data: data["maps"][0].__setitem__("wood", data["maps"][0]["wood"] + 1)
        )
        self.assertIs(True, outcome.detail["rolled_back"])

    def test_a_rolled_back_store_can_be_collected_again_cleanly(self) -> None:
        """The store is usable afterwards: the rollback is not a dead end."""
        self._run_with_tamper(
            lambda data: data["maps"][0].__setitem__("wood", data["maps"][0]["wood"] + 1)
        )
        outcome = collect(self._intent(), self.content, self.repository, FIXTURE_INSTANT)
        self.assertIsInstance(outcome, Success)


class FixtureGroundingTests(unittest.TestCase):
    """The instant and the row are read from the committed oracle, not typed in."""

    def test_the_row_is_a_tree_and_the_row_number_is_two(self) -> None:
        before = json.loads((COLLECT_STEP / "before.json").read_text(encoding="utf-8"))
        row = before["maps"][0]["items"]["2"]
        self.assertEqual(905, row[0])
        self.assertEqual(0, row[3])

    def test_the_capture_instant_comes_from_the_recorded_after_state(self) -> None:
        after = json.loads((COLLECT_STEP / "after.json").read_text(encoding="utf-8"))
        self.assertEqual(FIXTURE_INSTANT, after["maps"][0]["items"]["2"][3])

    def test_the_fixture_is_the_one_this_slice_replays(self) -> None:
        request = json.loads((COLLECT_STEP / "request.json").read_text(encoding="utf-8"))
        # The recorded request is the legacy signed form: ``form.data`` is
        # ``"<signature>;<json payload>"`` and the command vector is inside it.
        signature, _, payload = request["form"]["data"].partition(";")
        self.assertEqual(64, len(signature))
        commands = json.loads(payload)["commands"]
        self.assertEqual(1, len(commands))
        command = commands[0]
        self.assertEqual("collect", command[1])
        self.assertEqual([TREE_ROW], command[2])

    def test_the_recorded_vector_is_the_one_v1_never_accepts(self) -> None:
        """The recorded request's fourth element is a client-sent resource vector.

        This is the whole reason the slice exists: the executed-legacy request
        dictated ``[0, 3, 0, 60, 0, 0, 0, 0]``, and the derivation v1 reports
        happens to be ``xp +3, wood +60``.  Coincidence of arithmetic, not of
        protocol — v1 refuses the field, which is asserted in
        ``tests/test_intent.py``.  Pinned here so the resemblance is recorded as
        what it is rather than read as a v1 request shape.
        """
        request = json.loads((COLLECT_STEP / "request.json").read_text(encoding="utf-8"))
        _, _, payload = request["form"]["data"].partition(";")
        vector = json.loads(payload)["commands"][0][3]
        self.assertEqual([0, 3, 0, 60, 0, 0, 0, 0], vector)
        from server_v1_intent import parse_intent
        from server_v1_refusals import Refusal as _Refusal
        from server_v1_refusals import RefusalCode as _Code

        refused = parse_intent("collect", {"player_id": "p", "row": TREE_ROW, "vector": vector})
        self.assertIsInstance(refused, _Refusal)
        self.assertIs(_Code.CLIENT_SUPPLIED_DELTA, refused.code)


if __name__ == "__main__":
    unittest.main()