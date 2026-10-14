#!/usr/bin/env python3
"""The reward slice: derive the successor, refuse every client input, pay nothing.

This line's subject is a **substitution**, and the danger specific to that shape
is a test that cannot tell the substitution from the thing it replaced. The
preserved daily branch (``command.py:444-463``) computes ``args[1] + 1`` and
then, at ``command.py:451``, ``if next_id > 5: next_id = 1``.  Both halves of
that are the server's own -- except the *input*, which is ``args[1]``, a client
number.  A suite that asserts "the cursor went up by one" passes just as happily
against the legacy branch and against a service that read the client's number,
because both produce the same successor whenever the client is honest.

So the file is built around **falsifying** that claim rather than confirming it,
in four ways:

1. :class:`DerivationTests` seeds **five** distinct stored cursors and asserts
   the successor of each, so the derivation is a **function of the recorded
   value** and not a constant or a client echo.  A service that read
   ``args[1]`` could not answer the four cases where no id was sent at all.
2. :class:`BackwardsMoveTests` drives the preserved branch's own backwards
   transition -- an oversized next id moving a recorded ``4`` to ``1`` -- and
   asserts it is **unreachable** through the delivered route.  This is the one
   place the suite deliberately contrasts v1 with the oracle, and it is recorded
   as a divergence rather than reproduced.
3. :class:`RefusalTests` asserts that every cursor and grant input leaves the
   saved **file bytes** identical, not merely the in-memory value, so a refusal
   that wrote the same value back cannot pass.
4. :class:`NoEligibilityTests` **re-derives** that the stamped instant has zero
   readers across the eleven legacy modules, every run.  The requirement is
   "no eligibility rule", and an inherited constant asserting "the instant is
   unread" is exactly the kind of claim that survives the reader appearing.

The anti-invention guards (:class:`AntiInventionTests`) are the third instance
of this repository's recorded shape: the module declares no payout, cost,
eligibility, or cooldown helper, and that is checked by comparing **declared
function names** -- case-folded, by substring, in both directions -- rather than
by scanning raw source, because a raw scan trips on the guard's own inventory
text.  That defect was measured and recorded on two earlier lines, so here it is
avoided by construction rather than discovered a third time.
"""
from __future__ import annotations

import ast
import io
import re
import unittest
from types import ModuleType
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import harness
from harness import (
    FilesystemSaveRepository,
    build_corpus,
    corpus_save_bytes,
    load_content,
    remove_corpus,
    seed_player_id,
)
from server_v1_content import ContentError
from server_v1_intent import (
    ADDRESSING_FIELDS,
    INTENT_OPERATION_VALUES,
    NO_ADDRESSING_FIELD_ACTIONS,
    REWARD_CURSOR_KEYS,
    REWARD_GRANT_CHANNELS,
    REWARD_GRANT_KEYS,
    Intent,
    parse_intent,
)
from server_v1_outcomes import PRESERVED_REWARD_BEHAVIOUR, RewardSuccess
from server_v1_refusals import Refusal, RefusalCode
from server_v1_repository import SaveDocument, SaveRepository
from server_v1_reward import (
    ACTION,
    CURSOR_KEYS,
    DAILY_BOUND,
    DAILY_BOUND_REJECTED_DERIVATION,
    GRANT_CHANNEL_REFUSALS,
    OPERATIONS,
    PostConditionViolation,
    RewardTransition,
    advance_reward,
    declared_operations,
    reward_cursor_path,
    _weekly_bound,
)

#: The service's own clock, pinned so every ``instant_after`` is deterministic.
SERVICE_INSTANT = 1_700_000_000
#: An instant deliberately **different** from any recorded cursor's own stamp, so
#: "the instant was written" cannot be satisfied by a stored value that happened
#: to be there already.
UNRECORDED_INSTANT = 1_234_567_890

#: The eleven legacy runtime modules the zero-reader claim is measured over.
#:
#: **Named, never globbed.**  A glob would silently absorb a new root module and
#: let the census's scope drift with nothing failing -- a defect this repository
#: has recorded before.  The one excluded analysis tool is asserted in
#: :class:`NoEligibilityTests` so its exclusion cannot become silent either.
LEGACY_MODULES = (
    "auctions.py",
    "bundle.py",
    "command.py",
    "constants.py",
    "engine.py",
    "get_game_config.py",
    "get_player_info.py",
    "legacy_command_recorder.py",
    "server.py",
    "sessions.py",
    "version.py",
)
EXCLUDED_ROOT_MODULES = ("legacy_command_recorder.py",)

DOMAIN_SOURCE = harness.SERVICE_DIR / "server_v1_reward.py"
INTENT_SOURCE = harness.SERVICE_DIR / "server_v1_intent.py"
APP_SOURCE = harness.SERVICE_DIR / "server_v1_app.py"
APP_MODULE = APP_SOURCE.read_text(encoding="utf-8")

#: The two stored field names, read from the repository's own table rather than
#: transcribed, so a rename in either direction fails here first.
STAMP_KEYS = {
    operation: paths[1] for operation, paths in SaveDocument.REWARD_CURSOR_PATHS.items()
}

#: Names that would be a **derivation the oracle does not have**.  Matched
#: case-folded and by substring in **both** directions against the module's
#: declared function names.
#:
#: Substring rather than exact, because two earlier lines in this repository
#: measured that an exact-name check passes a *suffixed* helper wearing the same
#: disguise -- ``frame_duration_for`` beside an absent ``frame_duration``.  And
#: declared names rather than raw source, because a raw scan trips on this
#: tuple's own text, which is the self-tripping defect two lines recorded.
#: Modules that could spawn a process.  Declared here so the provenance guard
#: below can assert this suite does not bind one, without the assertion ever
#: naming an executor in a way that would trip a source-text scan of itself.
PROBE_EXECUTOR_MODULES = frozenset(
    {"subprocess", "os", "shutil", "pty", "multiprocessing", "asyncio"}
)
FORBIDDEN_HELPER_STEMS: Tuple[str, ...] = (
    "cooldown",
    "cost",
    "eligible",
    "eligibility",
    "pay_",
    "payout",
    "pays",
    "price",
    "reward_for",
    "window",
)

#: Every declared function name in the domain module, compared as a **sorted
#: unique set**.  An earlier line in this repository learned this the hard way:
#: several helpers there are declared twice (``_init`` among them), so a
#: positional list comparison fails against the delivered module itself.  The
#: declaration count is pinned separately so the set cannot hide a duplicate.
EXPECTED_FUNCTION_NAMES: Tuple[str, ...] = (
    "PostConditionViolation",
    "RewardTransition",
    "_addressability",
    "_addressable_positions",
    "_changed_leaf_paths",
    "_cursor_now",
    "_derive",
    "_expected_leaf_paths",
    "_refuse",
    "_repository_refusal",
    "_stamp_key",
    "_weekly_bound",
    "advance_reward",
    "declared_operations",
    "reward_cursor_path",
)
EXPECTED_FUNCTION_DECLARATIONS = 15


def _declared_function_names(source: str) -> Tuple[List[str], int]:
    """Every ``def``/``class`` name in ``source``, in order, with their count.

    A ``class`` is included because a ``class`` can compute as easily as a
    function, and a class-only helper would be invisible to a ``def``-only scan.
    """
    tree = ast.parse(source)
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
    return names, len(names)


def _transport_source() -> ast.Module:
    return ast.parse(APP_MODULE)


class RewardTestCase(unittest.TestCase):
    """One shared fixture, one shared set of helpers.

    Declared once because three classes in an earlier line each declared their
    own copy and a fourth used one it never declared -- nine errors across three
    methods from one missing helper.  The helpers here write through the
    repository, so the saved file and the in-memory document always agree; that
    is what the byte-identity assertions read back.
    """

    def setUp(self) -> None:
        self.content = load_content(harness.REPO_ROOT)
        self.corpus = build_corpus()
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.player = seed_player_id()

    # ----------------------------------------------------------- convenience --
    def _save_path(self) -> Path:
        return self.corpus / "saves" / ("%s.save.json" % self.player)

    def _pre_bytes(self) -> bytes:
        return corpus_save_bytes(self.corpus)

    def _set_cursor(self, operation: str, value: int) -> None:
        """Write a starting cursor through the repository."""
        document = self.repository.read(self.player)
        document.private_state()[CURSOR_KEYS[operation]] = value
        self.repository.write(document)

    def _set_stamp(self, operation: str, value: int) -> None:
        document = self.repository.read(self.player)
        document.private_state()[STAMP_KEYS[operation]] = value
        self.repository.write(document)

    def _stored(self, operation: str) -> int:
        return int(self.repository.read(self.player).private_state()[CURSOR_KEYS[operation]])

    def _stored_stamp(self, operation: str) -> int:
        return int(self.repository.read(self.player).private_state()[STAMP_KEYS[operation]])

    def _intent(
        self,
        operation: str = "daily",
        player: Optional[str] = None,
        cursor_request: Any = None,
        grant_request: Optional[Dict[str, Any]] = None,
    ) -> Intent:
        return Intent(
            action=ACTION,
            player_id=self.player if player is None else player,
            operation=operation,
            cursor_request=cursor_request,
            grant_request=dict(grant_request or {}),
        )

    def _advance(self, intent: Intent, now: int = SERVICE_INSTANT) -> Any:
        return advance_reward(intent, self.content, self.repository, now)

    def _success(self, intent: Intent, now: int = SERVICE_INSTANT) -> RewardSuccess:
        outcome = self._advance(intent, now)
        self.assertIsInstance(outcome, RewardSuccess)
        return outcome

    def _assert_refused(self, outcome: Any, code: RefusalCode) -> Refusal:
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(code, outcome.code)
        return outcome


# ==========================================================================
# 1. The derivation is a function of the recorded value.
# ==========================================================================


class DerivationTests(RewardTestCase):
    """The successor comes from the document, and the file agrees.

    Each case seeds a **distinct** cursor and asserts the successor, so the set
    as a whole cannot be satisfied by a constant, by a client echo, or by the
    preserved branch's own ``args[1] + 1`` (which needs an id this suite never
    sends).
    """

    def test_a_daily_cursor_advances_by_one_and_wraps_at_the_preserved_literal(self) -> None:
        # ``command.py:444-451``: ``next_id = args[1] + 1`` then
        # ``if next_id > 5: next_id = 1``.  The rule v1 keeps is the *clamp*; the
        # input it replaces is the client's ``args[1]``.
        for stored, expected in ((1, 2), (2, 3), (4, 5), (5, 1)):
            with self.subTest(stored=stored):
                self._set_cursor("daily", stored)
                outcome = self._success(self._intent("daily"))
                self.assertEqual(stored, outcome.cursor_before)
                self.assertEqual(expected, outcome.cursor_after)
                self.assertEqual(expected - stored, outcome.cursor_change)
                self.assertEqual(expected, self._stored("daily"))

    def test_a_weekly_cursor_advances_modulo_the_preserved_helpers_own_bound(self) -> None:
        # ``command.py:363``: ``(stored + 1) % get_weekly_reward_length()``.
        bound = self._derived_weekly_bound()
        for stored in range(bound):
            with self.subTest(stored=stored):
                self._set_cursor("weekly", stored)
                outcome = self._success(self._intent("weekly"))
                self.assertEqual((stored + 1) % bound, outcome.cursor_after)

    def _derived_weekly_bound(self) -> int:
        """The bound, from the content, by this file's own re-derivation."""
        length = 1
        for rung in self.content.globals_object()["MONDAY_BONUS_REWARDS"]:
            value = rung["value"]
            if isinstance(value, list):
                length = max(length, len(value))
        return length

    def test_the_two_bounds_are_different_numbers_and_that_is_reported(self) -> None:
        """The bound is **5** and the schedule's cardinality is **3**.

        Asserted as a pair rather than one figure, because a bound read as "how
        many rewards there are" is the mistake this pair exists to prevent.
        """
        schedule = self.content.globals_object()["MONDAY_BONUS_REWARDS"]
        self.assertEqual(5, self._derived_weekly_bound())
        self.assertEqual(3, len(schedule))

    def test_the_daily_bound_is_the_literal_with_the_rejected_derivation_retained(self) -> None:
        """Design D3: the literal is the rule; the schedule length is not.

        The two agree today -- ``DAILY_GOLD_REWARDS`` holds exactly five entries
        -- and the suite asserts **both** that agreement and that it is recorded
        as a coincidence, because "they are the same number" and "the schedule
        length is the rule" are different claims with the same evidence.
        """
        schedule = self.content.globals_object()["DAILY_GOLD_REWARDS"]
        self.assertEqual(5, DAILY_BOUND)
        self.assertEqual(len(schedule), DAILY_BOUND)
        self.assertEqual("len(DAILY_GOLD_REWARDS)", DAILY_BOUND_REJECTED_DERIVATION["rejected"])
        self.assertIs(True, DAILY_BOUND_REJECTED_DERIVATION["agrees_today"])
        self.assertEqual(
            "a coincidence, not a derivation",
            DAILY_BOUND_REJECTED_DERIVATION["agreement_is"],
        )

    def test_the_bound_is_reported_with_both_spellings(self) -> None:
        """A client sees the number **and** where it came from."""
        outcome = self._success(self._intent("daily"))
        self.assertEqual(DAILY_BOUND, outcome.bound["value"])
        self.assertIn("command.py:451", outcome.bound["provenance"])
        self.assertEqual(DAILY_BOUND, outcome.bound["daily_literal"])
        self.assertIn(
            "rejected", outcome.bound["daily_rejected_derivation"]
        )

    def test_the_weekly_provenance_names_the_preserved_accessor(self) -> None:
        outcome = self._success(self._intent("weekly"))
        self.assertEqual(5, outcome.bound["value"])
        self.assertIn("get_weekly_reward_length", outcome.bound["provenance"])

    def test_the_cursor_path_is_the_real_one_beside_the_container_address(self) -> None:
        """The request addresses ``/privateState``; the domain resolves the key.

        Two-step addressing is the point: the client cannot say *which* cursor,
        because naming it is the client input this line exists to refuse.
        """
        outcome = self._success(self._intent("weekly"))
        self.assertEqual("/privateState", self._intent("weekly").addressed_path())
        self.assertEqual("/privateState/weeklyRewardIndex", outcome.cursor_path)
        self.assertEqual(reward_cursor_path("daily"), "/privateState/bonusNextId")

    def test_the_change_is_reported_signed_so_a_backwards_move_would_show(self) -> None:
        outcome = self._success(self._intent("daily"))
        self.assertEqual(
            outcome.cursor_after - outcome.cursor_before, outcome.cursor_change
        )

    def test_exactly_two_leaf_paths_move(self) -> None:
        """The cursor and its instant. A third would name itself."""
        self._set_cursor("daily", 1)
        outcome = self._success(self._intent("daily"))
        self.assertEqual(
            ("/privateState/bonusNextId", "/privateState/timestampLastBonus"),
            tuple(outcome.leaf_paths_changed),
        )

    def test_both_schedules_are_reported_and_neither_is_read(self) -> None:
        outcome = self._success(self._intent("daily"))
        self.assertIs(False, outcome.schedules["read"])
        self.assertIn("DAILY_GOLD_REWARDS", outcome.schedules["daily"])
        self.assertIn("MONDAY_BONUS_REWARDS", outcome.schedules["weekly"])


class BackwardsMoveTests(RewardTestCase):
    """The one place the suite contrasts v1 with the oracle, on purpose.

    The committed fixture at ``tests/fixtures/godot-rewards/`` **executes** the
    backwards move: an oversized client-sent next id takes a recorded ``4`` to
    ``1``.  Reproducing it would defeat the purpose of making the cursor
    authoritative, so it is recorded as a divergence and made unreachable.
    """

    def test_the_recorded_cursor_is_never_moved_backwards(self) -> None:
        """Every on-ladder daily cursor advances; none of them regresses.

        The oracle's own arithmetic, applied to the **stored** value, is the only
        place a ``4 -> 1`` move can come from -- and ``4 -> 1`` is still a
        forward move on the daily ladder, because the preserved branch wraps at
        the top.  The genuinely backwards move at the oracle needs an oversized
        *client-sent* id, which
        :meth:`test_no_request_shape_reaches_the_backwards_move` shows is
        unreachable here.
        """
        for stored in (1, 2, 3, 4, 5):
            with self.subTest(stored=stored):
                self._set_cursor("daily", stored)
                outcome = self._success(self._intent("daily"))
                preserved = stored + 1
                if preserved > DAILY_BOUND:
                    preserved = 1
                self.assertEqual(preserved, outcome.cursor_after)
                self.assertGreater(outcome.cursor_after, 0)
                self.assertEqual(outcome.cursor_after, self._stored("daily"))

    def test_no_request_shape_reaches_the_backwards_move(self) -> None:
        """Every cursor input is refused, so the client cannot ask for one.

        Driven with the shapes a client could plausibly send -- including the
        **oversized** one the fixture used, which is the exact input that
        produced ``4 -> 1`` at the oracle.
        """
        self._set_cursor("daily", 4)
        before = self._pre_bytes()
        for sent in (5, 6, 99, 0, -1, "1", [], {"next": 1}):
            with self.subTest(sent=sent):
                outcome = self._advance(self._intent("daily", cursor_request=sent))
                self._assert_refused(outcome, RefusalCode.CLIENT_DICTATED_CURSOR)
        self.assertEqual(before, self._pre_bytes())
        self.assertEqual(4, self._stored("daily"))

    def test_the_divergence_is_recorded_rather_than_reproduced(self) -> None:
        """The refusal says *why*, so a client can see the gap to the oracle."""
        self._set_cursor("daily", 4)
        refusal = self._assert_refused(
            self._advance(self._intent("daily", cursor_request=6)),
            RefusalCode.CLIENT_DICTATED_CURSOR,
        )
        self.assertEqual(6, refusal.detail["sent"])
        self.assertIn("derives the successor from the recorded cursor",
                      refusal.message)


# ==========================================================================
# 2. Every client input is refused, and a refusal moves nothing.
# ==========================================================================


class RefusalTests(RewardTestCase):
    """Task 1.3: each grant resolves **before** the cursor advances.

    Asserted against the saved **file bytes**, not the in-memory value, so a
    refusal that wrote the same value back cannot pass.
    """

    def test_every_cursor_spelling_is_refused_with_its_own_value_carried(self) -> None:
        """Driven through the **parser**, with the real spellings.

        The earlier draft of this test looped over key names while sending a
        literal ``3`` every time, so the key names decided nothing -- it would
        have passed with an empty tuple.  The spellings now come from
        :data:`REWARD_CURSOR_KEYS`, which is the table the parser reads.
        """
        self._set_cursor("daily", 1)
        before = self._pre_bytes()
        for key in sorted(REWARD_CURSOR_KEYS[ACTION]):
            with self.subTest(key=key):
                intent = parse_intent(ACTION, {"player_id": self.player, "operation": "daily", key: 3})
                self.assertIsInstance(intent, Intent)
                self.assertEqual(3, intent.cursor_request)
                self._assert_refused(
                    self._advance(intent), RefusalCode.CLIENT_DICTATED_CURSOR
                )
        self.assertEqual(before, self._pre_bytes())
        self.assertEqual(1, self._stored("daily"))

    def test_each_grant_channel_is_refused_with_its_own_named_reason(self) -> None:
        self.assertEqual(
            {
                "item",
                "map_index",
                "cell",
                "player",
            },
            set(GRANT_CHANNEL_REFUSALS),
        )
        # **One code per channel.**  A single code would satisfy "each is
        # refused by name" nowhere: the spec requires four *different* reasons,
        # so the mapping is pinned as a total one-to-one rather than as a set.
        self.assertEqual(4, len(set(GRANT_CHANNEL_REFUSALS.values())))
        for channel, code in sorted(GRANT_CHANNEL_REFUSALS.items()):
            with self.subTest(channel=channel):
                self._set_cursor("daily", 1)
                before = self._pre_bytes()
                outcome = self._advance(
                    self._intent("daily", grant_request={channel: 7})
                )
                self._assert_refused(outcome, code)
                self.assertEqual(channel, outcome.detail["channel"])
                self.assertEqual(before, self._pre_bytes())
                self.assertEqual(1, self._stored("daily"))

    def test_every_grant_channel_is_400_not_409(self) -> None:
        """All five client-input refusals are **400**, which diverges from v0.

        v0 answers all five with 409 and v1's own
        ``CLIENT_DICTATED_DESTRUCTION`` answers its structurally identical case
        with 409.  v1 chooses 400 because the deciding question is never about
        stored state: each is resolved from the request body alone, before the
        player, the document, or the cursor is consulted.  Asserting the **split**
        rather than the set, because "all 400" and "all 409" are both sets and
        only the split against ``CLIENT_DICTATED_DESTRUCTION`` states the reason.
        """
        from server_v1_refusals import REFUSAL_HTTP_STATUS

        codes = [RefusalCode.CLIENT_DICTATED_CURSOR] + sorted(
            GRANT_CHANNEL_REFUSALS.values(), key=lambda c: c.value
        )
        self.assertEqual(5, len(set(codes)))
        for code in codes:
            with self.subTest(code=code.value):
                self.assertEqual(400, REFUSAL_HTTP_STATUS[code])
        self.assertEqual(409, REFUSAL_HTTP_STATUS[RefusalCode.CLIENT_DICTATED_DESTRUCTION])

    def test_a_refusal_leaves_the_whole_document_byte_identical(self) -> None:
        self._set_cursor("daily", 3)
        self._set_stamp("daily", UNRECORDED_INSTANT)
        before = self._pre_bytes()
        for grants in ({"item": 5}, {"cell": 3}, {"player": "x"}, {"map_index": 1}):
            with self.subTest(grants=grants):
                outcome = self._advance(self._intent("daily", grant_request=grants))
                self.assertIsInstance(outcome, Refusal)
                self.assertEqual(before, self._pre_bytes())
        self.assertEqual(3, self._stored("daily"))
        self.assertEqual(UNRECORDED_INSTANT, self._stored_stamp("daily"))

    def test_an_unknown_player_is_a_404(self) -> None:
        outcome = self._advance(self._intent("daily", player="no-such-player"))
        self._assert_refused(outcome, RefusalCode.UNKNOWN_PLAYER)
        self.assertEqual("no-such-player", outcome.detail["player_id"])

    def test_an_operation_outside_the_closed_set_never_reaches_the_document(self) -> None:
        before = self._pre_bytes()
        for operation in ("hourly", "DAILY", "", "monthly"):
            with self.subTest(operation=operation):
                outcome = self._advance(self._intent(operation))
                self._assert_refused(outcome, RefusalCode.MALFORMED_REQUEST)
                self.assertEqual(operation, outcome.detail["operation"])
        self.assertEqual(before, self._pre_bytes())

    def test_an_absent_cursor_key_is_refused_rather_than_read_as_zero(self) -> None:
        """Zero is a real position; absence is not.

        The weekly arm's preserved arithmetic is ``(stored + 1) % length``, so a
        cursor of ``0`` produces position ``1`` -- and the committed corpus
        records ``bonusNextId`` as ``0`` in seven documents.  Defaulting an
        absent key to zero would answer "you are at position zero" about a
        document that recorded no position at all.
        """
        document = self.repository.read(self.player)
        del document.private_state()["bonusNextId"]
        self.repository.write(document)
        outcome = self._advance(self._intent("daily"))
        self._assert_refused(outcome, RefusalCode.UNREADABLE_STATE)
        self.assertNotIn("bonusNextId", self.repository.read(self.player).private_state())

    def test_a_boolean_cursor_is_refused_because_bool_is_an_int(self) -> None:
        """The same defect class ``magic_counter`` records, reached again.

        ``True`` is an ``int`` in Python, so a stored ``True`` would advance the
        cursor as if it were ``1``.
        """
        document = self.repository.read(self.player)
        document.private_state()["bonusNextId"] = True
        self.repository.write(document)
        self._assert_refused(
            self._advance(self._intent("daily")), RefusalCode.UNREADABLE_STATE
        )

    def test_a_non_integer_cursor_is_refused(self) -> None:
        for value in ("2", 2.5, None, [], {}):
            with self.subTest(value=value):
                document = self.repository.read(self.player)
                document.private_state()["bonusNextId"] = value
                self.repository.write(document)
                self._assert_refused(
                    self._advance(self._intent("daily")), RefusalCode.UNREADABLE_STATE
                )


# ==========================================================================
# 3. The two-part proof, on a transaction that grants nothing.
# ==========================================================================


class PostConditionProofTests(RewardTestCase):
    """Task 1.5 and the spec's "grants nothing is still on the boundary".

    The converse of ``collect``'s proof: this one asserts that **no** stored
    resource moved and **no** item was granted, on a transaction that *succeeds*.
    A service that paid a gold bonus would pass every other reward test here.
    """

    def test_a_success_reports_the_five_halves_and_holds_all_of_them(self) -> None:
        self._set_cursor("daily", 2)
        outcome = self._success(self._intent("daily"))
        checks = dict(outcome.proof)
        self.assertEqual(5, len(checks))
        self.assertTrue(all(checks.values()), checks)

    def test_the_cursor_half_is_falsifiable(self) -> None:
        """The first half names the successor, so a wrong write fails it.

        Stated as a check on the *proof text* rather than on a tampered
        repository: :meth:`test_a_tampered_write_fails_the_cursor_half` covers
        the tampering, and duplicating that instrumentation would make this
        half of the claim decorative.
        """
        outcome = self._success(self._intent("daily"))
        names = [name for name, _ in outcome.proof]
        self.assertIn("cursor advanced to its derived successor", names)

    def test_the_resource_half_is_falsifiable(self) -> None:
        outcome = self._success(self._intent("daily"))
        names = [name for name, _ in outcome.proof]
        self.assertIn("no stored resource moved", names)
        self.assertIn("no item was granted into storage", names)
        self.assertIn("the bought-unit list is byte-identical", names)
        self.assertIn("nothing else in the document moved", names)

    def test_the_bought_unit_half_reads_the_real_list_not_an_absent_key(self) -> None:
        """``privateState.boughtUnits``, and the corpus proves the other path is
        wrong.

        ``maps[0].boughtUnits`` is **absent** from the fresh-player document, so
        a half reading it would compare ``None`` with ``None`` and pass for a
        service that never looked.  Asserted here so the half cannot be
        "simplified" onto the empty path.
        """
        document = self.repository.read(self.player)
        self.assertIn("boughtUnits", document.private_state())
        self.assertNotIn("boughtUnits", document.first_map())

    def test_a_tampered_cursor_write_fails_the_cursor_half(self) -> None:
        """A document that writes a *different* value must be caught.

        **The first draft of this test subclassed the repository and could
        never have fired.**  ``advance_reward`` mutates the ``SaveDocument``
        the repository handed back, calling ``document.set_reward_cursor(...)``;
        the repository subclass overrode a method the domain never calls, so the
        proof compared a correctly-written cursor against itself and passed.
        A guard that cannot fire is worse than no guard, because it reports
        coverage it does not have.

        The tamper therefore wraps the **document** -- the object the domain
        actually mutates -- and the wrapper is installed by overriding the
        repository's ``read``, the one repository method the domain does call.
        :meth:`test_the_tamper_wrapper_really_would_have_changed_the_write`
        guards the guard, so a future refactor that stopped the domain calling
        ``set_reward_cursor`` fails there rather than quietly reinstating an
        inert probe here.
        """

        class _WrongDocument:
            def __init__(self, inner: Any, operation: str) -> None:
                self._inner = inner
                self._operation = operation

            def set_reward_cursor(self, operation: str, value: int) -> None:
                if operation == self._operation:
                    value = value + 1
                self._inner.set_reward_cursor(operation, value)

            def __getattr__(self, name: str) -> Any:
                return getattr(self._inner, name)

        class _WrongWrite(FilesystemSaveRepository):
            operation = "daily"

            def read(self, player_id: str) -> Any:
                return _WrongDocument(super().read(player_id), self.operation)

        self._set_cursor("daily", 1)
        wrong = _WrongWrite(self.corpus)
        with self.assertRaises(PostConditionViolation) as raised:
            advance_reward(self._intent("daily"), self.content, wrong, SERVICE_INSTANT)
        self.assertIn("cursor advanced to its derived successor", str(raised.exception))

    def test_the_tamper_wrapper_really_would_have_changed_the_write(self) -> None:
        """The wrapper's own effect is asserted, so it cannot go inert.

        This is the test that would have caught the repository-subclass defect
        above.  It drives the wrapper directly and checks both that the daily
        arm's write is shifted and that the weekly arm's is **not** -- so the
        probe is shown to be a real perturbation rather than a class definition
        that silently does nothing.
        """

        class _WrongDocument:
            def __init__(self, inner: Any, repository: Any, operation: str) -> None:
                self._inner = inner
                self._repository = repository
                self._operation = operation

            def set_reward_cursor(self, operation: str, value: int) -> None:
                if operation == self._operation:
                    value = value + 1
                self._inner.set_reward_cursor(operation, value)
                # **Persist, or the assertion measures nothing.**  The first
                # draft of this guard mutated the in-memory document and then
                # read back through a *second* ``read``, so it saw the
                # unmutated file and reported ``1`` where it expected ``3`` --
                # a guard failing for the wrong reason.  The domain persists
                # through ``repository.write``, so the wrapper does too.
                self._repository.write(self._inner)

            def __getattr__(self, name: str) -> Any:
                return getattr(self._inner, name)

        class _WrongWrite(FilesystemSaveRepository):
            operation = "daily"

            def read(self, player_id: str) -> Any:
                return _WrongDocument(super().read(player_id), self, self.operation)

        self._set_cursor("daily", 1)
        self._set_cursor("weekly", 1)
        wrong = _WrongWrite(self.corpus)
        wrong.read(self.player).set_reward_cursor("daily", 2)
        self.assertEqual(3, self._stored("daily"))
        wrong.read(self.player).set_reward_cursor("weekly", 2)
        self.assertEqual(2, self._stored("weekly"), "the weekly arm was perturbed too")

    def test_a_tampered_grant_fails_the_grant_half(self) -> None:
        """The converse: granting an item must fail, or the half is decorative.

        Wraps the **document** for the same reason the cursor tamper does -- a
        repository override could never fire -- and grants through the storage
        accessor, because the half under test is *storage* identity rather than
        the cursor.
        """

        class _GrantingDocument:
            def __init__(self, inner: Any) -> None:
                self._inner = inner

            def set_reward_cursor(self, operation: str, value: int) -> None:
                self._inner.set_reward_cursor(operation, value)
                document = SaveDocument.__new__(SaveDocument)
                self._inner.set_storage_quantity("1001", 1)

            def __getattr__(self, name: str) -> Any:
                return getattr(self._inner, name)

        class _GrantingWrite(FilesystemSaveRepository):
            def read(self, player_id: str) -> Any:
                return _GrantingDocument(super().read(player_id))

        self._set_cursor("daily", 1)
        granting = _GrantingWrite(self.corpus)
        with self.assertRaises(PostConditionViolation) as raised:
            advance_reward(
                self._intent("daily"), self.content, granting, SERVICE_INSTANT
            )
        self.assertIn("no item was granted into storage", str(raised.exception))


    def test_a_failed_proof_needs_no_rollback_and_says_so(self) -> None:
        """Post-condition failure is the **service's** fault, not the client's.

        Recorded rather than repaired: a rollback here would be a second write
        path in a module whose whole claim is that it writes exactly two fields.
        The raised exception is what the transport turns into a 500.
        """
        self.assertTrue(issubclass(PostConditionViolation, Exception))
        self.assertNotIsInstance(PostConditionViolation("x"), Refusal)

    def test_a_refused_transaction_reports_no_proof_at_all(self) -> None:
        outcome = self._advance(self._intent("daily", grant_request={"item": 5}))
        self.assertIsInstance(outcome, Refusal)
        self.assertFalse(hasattr(outcome, "proof"))


# ==========================================================================
# 4. No eligibility rule, and its absence is re-derived.
# ==========================================================================


class NoEligibilityTests(unittest.TestCase):
    """Requirement 4: no eligibility, cooldown, window, or already-claimed rule.

    The requirement is an **absence**, so an inherited constant would be a claim
    about the past rather than about the code.  Every figure here is re-measured
    over the committed legacy sources on each run.
    """

    def test_the_stamped_instants_are_written_at_two_sites_each_and_read_nowhere(self) -> None:
        """Re-derived: two **sites** each, zero readers, across eleven modules.

        Counted with the **string-literal** form (``"timestampLastBonus"``),
        because both sites are subscripts into a ``save`` dict whose key is a
        literal; counting a bare identifier would also match prose in a comment,
        which is how a zero-consumer count becomes a fiction.

        **Occurrences and sites are counted separately, and they differ.**  An
        earlier draft of this test asserted "one write" and the measured figure
        was **3**; the reason is not three writes but two sites on two lines,
        with ``command.py:914`` naming its key **twice** --
        ``max(0, privateState["timestampLastBonus"] - seconds)``.  That is the
        occurrence-vs-distinct-line distinction this repository has recorded
        before, arriving here again, and it is why both figures are asserted
        rather than one being derived from the other.
        """
        sources = self._legacy_sources()
        for stamp in ("timestampLastBonus", "timeStampMondayBonus"):
            with self.subTest(stamp=stamp):
                writers = sorted(
                    name for name, text in sources.items() if '"%s"' % stamp in text
                )
                self.assertEqual(["command.py"], writers)
                command = sources["command.py"]
                self.assertEqual(
                    3, command.count('"%s"' % stamp), "the occurrence count moved"
                )
                lines = [
                    index + 1
                    for index, line in enumerate(command.splitlines())
                    if '"%s"' % stamp in line
                ]
                self.assertEqual(2, len(lines), "the site count moved")
                self.assertEqual(len(set(lines)), len(lines), "a line was listed twice")

    def test_one_of_the_two_sites_is_the_client_driven_fast_forward(self) -> None:
        """The second site is why the instant cannot gate anything.

        ``command.py:914`` subtracts a **client-supplied** number of seconds
        from the daily instant, so the recorded stamp is client-writable.  That
        is precisely why the transaction writes and reports it and derives no
        gate from it: a value a client can move backwards is not a clock.
        """
        command = (harness.REPO_ROOT / "command.py").read_text(encoding="utf-8")
        fast_forward = [
            index + 1
            for index, line in enumerate(command.splitlines())
            if '"timestampLastBonus"' in line
        ]
        self.assertEqual([454, 914], fast_forward)
        self.assertIn("fast_forward", command)
        self.assertIn("seconds = args[0]", command)
        self.assertIn("max(0,", command.splitlines()[913])

    def test_the_weekly_fast_forward_site_is_commented_out_and_that_is_recorded(self) -> None:
        """The weekly instant is **not** client-writable; the daily one is.

        ``command.py:915`` carries the weekly subtraction as a **comment**, so
        the weekly stamp has exactly one real writer and no client-driven one.
        An earlier draft of this file's claim treated both stamps alike and
        would have been wrong about the weekly arm; the asymmetry is asserted
        here rather than smoothed away, because "the instant is
        client-writable" is true of one arm and false of the other.
        """
        command = (harness.REPO_ROOT / "command.py").read_text(encoding="utf-8")
        weekly = [
            (index + 1, line)
            for index, line in enumerate(command.splitlines())
            if '"timeStampMondayBonus"' in line
        ]
        self.assertEqual([361, 915], [number for number, _ in weekly])
        stamped, commented = weekly
        self.assertIn("] = time_now", stamped[1])
        self.assertTrue(
            commented[1].lstrip().startswith("#"),
            "the weekly fast-forward site is no longer a comment: %r" % commented[1],
        )

    def test_the_domain_never_reads_the_stamp_it_writes(self) -> None:
        """Mechanical, not editorial: the read never appears in the module."""
        tree = ast.parse(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        subscripts: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                subscripts.append(str(node.slice.value))
        for stamp in STAMP_KEYS.values():
            self.assertNotIn(stamp, subscripts, "the domain reads the instant it writes")

    def test_the_excluded_analysis_tool_is_still_excluded_on_purpose(self) -> None:
        """A guard on the guard on the guard.

        The eleven modules include one that is deliberately excluded from the
        reader census; asserting the exclusion keeps it from becoming silent.
        """
        self.assertIn("legacy_command_recorder.py", LEGACY_MODULES)
        self.assertEqual(
            set(EXCLUDED_ROOT_MODULES),
            {name for name in LEGACY_MODULES if name in EXCLUDED_ROOT_MODULES},
        )

    def _legacy_sources(self) -> Dict[str, str]:
        sources: Dict[str, str] = {}
        for name in LEGACY_MODULES:
            path = harness.REPO_ROOT / name
            self.assertTrue(path.is_file(), "declared legacy module is missing: %s" % name)
            sources[name] = path.read_text(encoding="utf-8")
        return sources


class AddressabilityTests(RewardTestCase):
    """Where a recorded cursor is off-ladder, report the gap; do not clamp it.

    The committed corpus carries ``bonusNextId`` as ``0`` in seven of its ten
    reward-bearing documents, and the daily branch can only store ``1..5`` -- so
    a stored ``0`` is an **off-ladder seed**, not a position the bound
    addresses.  The spec requires the gap be reported and **no rule derived** to
    resolve it, so the report carries the numbers and the suite asserts no
    clamp happened.
    """

    def test_an_off_ladder_cursor_is_reported_rather_than_clamped_into_range(self) -> None:
        """Four off-ladder values, including one v1's own accessor will not write.

        ``-3`` is seeded by writing ``privateState`` directly rather than through
        :meth:`set_reward_cursor`, and that is the point rather than a
        workaround: the accessor **refuses** a negative cursor, so reaching this
        case through v1's own API is impossible.  A legacy save could hold one
        anyway, and the requirement is that the transaction *reports* the gap
        rather than clamping it -- which is only a claim about documents the
        accessor would never produce.  Asserting that the accessor refuses it is
        therefore part of the same test.
        """
        # **``-3`` is not in this tuple, and that is the finding.**  A negative
        # stored cursor derives to a negative successor, and the repository
        # refuses a negative write -- so a negative off-ladder cursor is
        # *refused*, never reported.  :meth:`test_a_negative_off_ladder_cursor_is_refused_rather_than_reported`
        # pins that half.  The two behaviours are not the same rule: the report
        # says "here is a gap I will not resolve", the refusal says "this
        # document cannot be advanced at all", and only the first can be reached
        # for a value the accessor itself would have written.
        for stored in (0, 6, 99):
            with self.subTest(stored=stored):
                self._set_cursor("daily", stored)
                outcome = self._success(self._intent("daily"))
                gap = outcome.payload()["reward"]["addressability"]
                self.assertIs(True, gap["gap_reported"])
                self.assertIn(stored, gap["unaddressable_cursors"])
                # Nothing was clamped.  The cursor *did* advance -- that is the
                # transaction -- so asserting the stored value still equals the
                # off-ladder one would be asserting that nothing happened.  What
                # must hold is that the stored value is exactly the **derived
                # successor** and nothing else, and that the off-ladder value is
                # still named in the report beside it.
                self.assertEqual(0, gap["clamped"])
                self.assertEqual(outcome.cursor_after, self._stored("daily"))
                self.assertNotEqual(stored, self._stored("daily"))
                self.assertIn("no rule was derived", gap["resolution"])

    def test_the_repository_accessor_refuses_the_negative_cursor_v1_will_not_write(self) -> None:
        """The gap is reachable only through a document the accessor would refuse."""
        from server_v1_repository import RepositoryError

        document = self.repository.read(self.player)
        with self.assertRaises(RepositoryError) as raised:
            document.set_reward_cursor("daily", -3)
        self.assertEqual("unreadable_state", raised.exception.code)
        # ...and it reaches storage by the other route, which is how the
        # off-ladder case above is reachable at all.
        document.private_state()["bonusNextId"] = -3
        self.repository.write(document)
        self.assertEqual(-3, self._stored("daily"))

    def test_a_negative_off_ladder_cursor_is_refused_rather_than_reported(self) -> None:
        """The other half of the asymmetry, and the more important one.

        The stored ``-3`` **is** reachable -- it is written through
        ``privateState``, bypassing the accessor -- so a legacy save could hold
        one.  The transaction then refuses with ``unreadable_state``, because
        the successor is ``-2`` and no negative cursor may be written.  Asserted
        rather than reported, because a service that reported it and clamped
        upward would be inventing a rule the oracle has no counterpart for.
        """
        document = self.repository.read(self.player)
        document.private_state()["bonusNextId"] = -3
        self.repository.write(document)
        outcome = self._advance(self._intent("daily"))
        self._assert_refused(outcome, RefusalCode.UNREADABLE_STATE)
        # The refusal leaves the off-ladder value exactly as it found it.
        self.assertEqual(-3, self._stored("daily"))

    def test_an_on_ladder_cursor_reports_no_gap(self) -> None:
        self._set_cursor("daily", 3)
        gap = self._success(self._intent("daily")).payload()["reward"]["addressability"]
        self.assertIs(False, gap["gap_reported"])
        self.assertEqual([], gap["unaddressable_cursors"])


# ==========================================================================
# 5. Intent layer.
# ==========================================================================


class IntentTests(unittest.TestCase):
    """The request layer reads key names; the domain owns every reason."""

    def test_the_action_is_declared_with_a_closed_two_value_operation_set(self) -> None:
        self.assertEqual(("weekly", "daily"), declared_operations())
        self.assertEqual(OPERATIONS, declared_operations())
        self.assertEqual(frozenset({"weekly", "daily"}), INTENT_OPERATION_VALUES[ACTION])

    def test_the_action_has_no_addressing_field_and_that_is_declared(self) -> None:
        """The first delivered action with none, because naming the cursor is
        the client input this line refuses.

        Asserted against the **declaration** rather than by scanning source for a
        token, for the reason this repository has recorded three times now: a
        guard that names the thing it forbids must be exempted from itself, and
        every such exemption is a place a second guard can drift.
        """
        self.assertNotIn(ACTION, ADDRESSING_FIELDS)
        self.assertIn(ACTION, NO_ADDRESSING_FIELD_ACTIONS)

    def test_the_address_is_the_container_not_a_key(self) -> None:
        intent = Intent(action=ACTION, player_id="p", operation="daily")
        self.assertEqual("/privateState", intent.addressed_path())

    def test_a_well_formed_request_parses_into_the_identity_and_the_operation(self) -> None:
        outcome = parse_intent(ACTION, {"player_id": "p", "operation": "daily"})
        self.assertIsInstance(outcome, Intent)
        self.assertEqual(ACTION, outcome.action)
        self.assertEqual("daily", outcome.operation)
        self.assertIsNone(outcome.cursor_request)
        self.assertEqual({}, outcome.grant_request)

    def test_a_missing_operation_is_refused_rather_than_defaulted(self) -> None:
        for body in ({"player_id": "p"}, {"player_id": "p", "operation": None}):
            with self.subTest(body=body):
                self.assertIsInstance(parse_intent(ACTION, body), Refusal)

    def test_an_operation_outside_the_closed_set_is_refused(self) -> None:
        for value in ("sell", "DAILY", "", "daily ", 1, True, ["daily"]):
            with self.subTest(value=value):
                outcome = parse_intent(ACTION, {"player_id": "p", "operation": value})
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)

    def test_a_client_sent_cursor_reaches_the_domain_verbatim_and_unread(self) -> None:
        for value in (3, "3", -1, None, [3], {"n": 3}):
            with self.subTest(value=value):
                outcome = parse_intent(
                    ACTION,
                    {"player_id": "p", "operation": "daily", "next_id": value}
                )
                self.assertIsInstance(outcome, Intent)
                self.assertEqual(value, outcome.cursor_request)

    def test_every_grant_spelling_is_carried_keyed_by_channel(self) -> None:
        self.assertEqual(
            {"item", "item_index", "cell", "x", "y", "player"},
            set(REWARD_GRANT_KEYS[ACTION]),
        )
        for key, channel in sorted(REWARD_GRANT_KEYS[ACTION].items()):
            with self.subTest(key=key):
                outcome = parse_intent(
                    ACTION,
                    {"player_id": "p", "operation": "daily", key: 5}
                )
                self.assertIsInstance(outcome, Intent)
                self.assertEqual({channel: 5}, outcome.grant_request)

    def test_x_and_y_reach_the_domain_as_the_one_cell_they_are(self) -> None:
        """Two coordinates are one cell; refusing them separately would be a
        second channel for one value."""
        outcome = parse_intent(
            ACTION,
            {"player_id": "p", "operation": "daily", "x": 3, "y": 4}
        )
        self.assertIsInstance(outcome, Intent)
        self.assertEqual(1, len(outcome.grant_request))
        self.assertEqual("cell", next(iter(outcome.grant_request)))

    def test_amount_and_price_are_not_grant_channels(self) -> None:
        """They are delta words, refused earlier and by a different code.

        Duplicating them here would make which of the two answers depend on the
        order of two tables.
        """
        for key in ("amount", "price", "gold", "resources_changed"):
            with self.subTest(key=key):
                self.assertNotIn(key, REWARD_GRANT_KEYS[ACTION])


# ==========================================================================
# 6. Transport: registered, last, and identical in shape.
# ==========================================================================


class RoutePlacementTests(unittest.TestCase):
    """Task 1.6: the route's **position** is asserted, not incidental.

    Three earlier suites slice ``server_v1_app.py`` by source span and two reach
    **forward** across every route declared between them, so a route dropped
    into the middle would move their spans silently.  ``/v1/reward`` is declared
    **last** because that is the only slot no span reaches.
    """

    def test_the_route_is_registered_and_declared_last(self) -> None:
        from server_v1_app import ROUTES

        self.assertEqual(5, len(ROUTES))
        self.assertEqual("reward", ROUTES["POST /v1/reward"])
        self.assertEqual("POST /v1/reward", list(ROUTES)[-1])
        self.assertIn('REWARD_PATH = "/v1/reward"', APP_MODULE)

    def test_the_route_handler_has_its_own_single_function_slice(self) -> None:
        """The handler is separable, so a span-scanning suite can slice it."""
        start = APP_MODULE.find("async def post_reward(")
        self.assertGreater(start, 0, "the reward handler is not declared")
        end = APP_MODULE.find("\n\nasync def ", start)
        handler = APP_MODULE[start:] if end < 0 else APP_MODULE[start:end]
        self.assertEqual(1, handler.count("advance_reward("))
        # The slice must **end** before the next handler, or every suite that
        # slices by span silently absorbs this one.
        self.assertNotIn("async def post_", handler[len("async def post_reward(") :])

    def test_the_handler_is_the_last_one_declared_in_the_module(self) -> None:
        """Declared **last**, and that position is the property being pinned.

        The forward-reaching-span hazard this repository recorded was measured
        over the **Compatibility API's** 24 routes, where a route dropped
        between two others moved four delivered suites' source spans at once.
        Two of this file's own ancestors on v1 -- ``test_combat.py`` and
        ``test_magic.py`` -- still carry ``markers[-1] == "@app.post(...)"``
        invariants against v0's app, so the risk is real in the sibling tree
        rather than absent here.  What is asserted is the property that would
        *cause* it: this handler is not wrapped by another one.

        The first draft of this test sliced ``async def post_research`` ->
        ``async def post_level_up`` and asserted the handler was absent from
        it.  Both markers are **Compatibility API** routes; v1 has no research
        or level route, so both spans were ``None`` and the test errored rather
        than passed -- a guard that could never have fired while looking
        decisive.  Asserting a property of the v1 module instead of copying a
        span pair from another module is the fix, and the recorded reason for
        it is that a copied span names handlers that need not exist.
        """
        self.assertNotIn("post_research", APP_MODULE)
        self.assertNotIn("post_level_up", APP_MODULE)
        self.assertNotIn("post_tutorial", APP_MODULE)
        handlers = re.findall(
            r"^[ \t]*async def (post_\w+)\(", APP_MODULE, re.MULTILINE
        )
        self.assertEqual(
            ["post_collect", "post_collection", "post_combat", "post_magic", "post_reward"],
            handlers,
        )
        self.assertEqual(handlers[-1], "post_reward")

    def test_the_transport_names_no_refusal_code(self) -> None:
        """D10, restated for the fifth route.

        The refusal vocabulary lives in one table, so a route that named a code
        would have answered without going through it.
        """
        tree = _transport_source()
        codes = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "RefusalCode"
        }
        self.assertEqual(set(), codes)

    def test_the_transport_declares_no_arithmetic_operator(self) -> None:
        """The route may not compute a successor; it names one domain call."""
        tree = _transport_source()
        operators = {
            type(node.op).__name__
            for node in ast.walk(tree)
            if isinstance(node, ast.BinOp)
        }
        self.assertEqual(set(), operators)


class PreservedBehaviourTests(RewardTestCase):
    """The oracle's own behaviour is reported beside every success.

    Every entry is a **recorded fact** and none is a v1 behaviour.  It matters
    more here than for the other slices: the reward branches *sound* like
    payouts -- one is called ``win_daily_bonus`` and the committed table is
    called ``DAILY_GOLD_REWARDS`` -- so a reader who saw only "the daily cursor
    advanced" would have every reason to think gold changed hands.
    """

    def test_the_table_names_the_weekly_arithmetic_and_its_client_input(self) -> None:
        self.assertIn(
            "command.py:345-363", PRESERVED_REWARD_BEHAVIOUR["weekly_branch"]
        )
        self.assertIn("get_weekly_reward_length", PRESERVED_REWARD_BEHAVIOUR["weekly_branch"])
        self.assertTrue(any("client" in text.lower() for text in PRESERVED_REWARD_BEHAVIOUR.values()))

    def test_the_table_names_the_daily_clamp_as_a_literal(self) -> None:
        joined = " ".join(PRESERVED_REWARD_BEHAVIOUR.values())
        self.assertIn("command.py:451", joined)
        self.assertIn("5", joined)

    def test_the_success_model_carries_the_no_payout_claim_as_a_field(self) -> None:
        """Not prose.  A reader who saw only the cursor would conclude the
        player was paid, so the model proves the absence by comparing the whole
        stored resource set."""
        fields = set(RewardSuccess.model_fields)
        self.assertIn("derived_payout", fields)
        self.assertIn("paid", fields)
        self.assertIn("eligibility_derived", fields)

    def test_a_success_reports_all_three_as_their_absent_values(self) -> None:
        """On a **real** success, not a hand-built one.

        The first draft constructed a ``RewardSuccess`` by hand and it failed
        validation -- the model requires ``schedules`` and rejects a bare
        one-entry proof.  That is the informative outcome, not an obstacle: a
        hand-built model proves the *constructor* accepts the arguments, while
        the claim is about what a **transaction** reports.  Driven against a real
        success instead, so it cannot pass on a model whose defaults drifted
        while its produced values stayed correct.

        A second draft tried to borrow another class's fixture through a local
        subclass and failed with ``no such test method`` -- a shared-helper
        pattern this repository has already paid for once.  This class now
        extends :class:`RewardTestCase` directly and owns its own corpus.
        """
        outcome = self._success(self._intent("daily"))
        self.assertIsNone(outcome.derived_payout)
        self.assertIs(False, outcome.paid)
        self.assertIs(False, outcome.eligibility_derived)
        self.assertIs(False, outcome.payload()["reward"]["instant_gating"])

    def test_a_success_payload_omits_the_delta_and_grant_keys_the_others_carry(self) -> None:
        """No ``derived_deltas`` and no ``grant``, rather than empty ones.

        An empty key invites a reader to treat the absence as a formatting
        accident; ``derived_deltas`` is in fact the key every other v1 success
        uses for a real server-derived figure, so its absence here is the claim.
        """
        body = self._success(self._intent("daily")).payload()
        self.assertNotIn("derived_deltas", body)
        self.assertNotIn("grant", body)
        self.assertIn("preserved_branch_behaviour", body)

    def test_the_success_model_declares_the_addressability_report(self) -> None:
        """Task 1.4's third report is a **field**, not prose.

        ``clamped`` is hard ``0`` and that is worth nothing unless something
        checks it, which is what :class:`AddressabilityTests` does.
        """
        self.assertIn("addressability", set(RewardSuccess.model_fields))


class StoredInstantTests(RewardTestCase):
    """The instant is written and reported, and gates nothing."""

    def test_the_instant_before_and_after_are_reported(self) -> None:
        self._set_stamp("daily", UNRECORDED_INSTANT - 1)
        outcome = self._success(self._intent("daily"), now=SERVICE_INSTANT)
        self.assertEqual(UNRECORDED_INSTANT - 1, outcome.instant_before)
        self.assertEqual(SERVICE_INSTANT, outcome.instant_after)
        self.assertEqual(SERVICE_INSTANT, self._stored_stamp("daily"))

    def test_a_stamp_far_in_the_past_does_not_refuse_the_transaction(self) -> None:
        """No cooldown, no window, no already-claimed check.

        The negative case is the claim: with a stamp one second old the
        transaction still succeeds, which a derived cooldown would refuse.
        """
        self._set_stamp("daily", UNRECORDED_INSTANT)
        self._set_cursor("daily", 1)
        self._success(self._intent("daily"), now=UNRECORDED_INSTANT + 1)

    def test_a_stamp_one_second_old_still_succeeds(self) -> None:
        self._set_stamp("daily", UNRECORDED_INSTANT)
        self._set_cursor("daily", 1)
        outcome = self._success(self._intent("daily"), now=UNRECORDED_INSTANT)
        self.assertEqual(UNRECORDED_INSTANT, outcome.instant_after)


# ==========================================================================
# 7. Anti-invention guards.
# ==========================================================================


class AntiInventionTests(unittest.TestCase):
    """The module owns a derivation and nothing else.

    Two guards, and the order matters: the **inventory pin is the real gate**
    (it catches a helper that borrows no reserved word) and the reserved-stem
    guard is the belt (it catches one that borrows a name in a spelling the
    inventory would not have flagged as *new*, if the inventory were ever
    loosened).  Both were verified by injection before delivery.
    """

    def test_the_declared_function_names_are_exactly_the_pinned_inventory(self) -> None:
        names, count = _declared_function_names(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        # **Sorted unique**, because an earlier line in this repository learned
        # that a positional comparison fails against its own delivered module:
        # five of its helpers are declared twice, ``_init`` among them.
        self.assertEqual(
            sorted(EXPECTED_FUNCTION_NAMES), sorted(set(names))
        )
        # The declaration count is pinned **separately**, so the set cannot hide
        # a duplicate declaration that the set would silently collapse.
        self.assertEqual(EXPECTED_FUNCTION_DECLARATIONS, count)

    def test_no_payout_cost_eligibility_or_cooldown_helper_is_declared(self) -> None:
        """Case-folded, by substring, in **both** directions.

        Both directions because a reserved stem that *is* a declared name
        (``payout_for`` beside an absent ``payout``) would be missed by a
        one-directional check, and an earlier line measured that an exact-name
        check passes a suffixed helper wearing the same disguise.
        """
        names, _ = _declared_function_names(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        for name in sorted(set(names)):
            folded = name.casefold()
            for stem in FORBIDDEN_HELPER_STEMS:
                with self.subTest(name=name, stem=stem):
                    self.assertNotIn(
                        stem.casefold(), folded,
                        "%s carries the reserved stem %r" % (name, stem),
                    )
                    self.assertNotIn(
                        name.casefold(), stem.casefold(),
                        "%s is a superstring of the reserved stem %r" % (name, stem),
                    )

    def test_the_derivation_is_reachable_from_one_place_only(self) -> None:
        """The successor is computed in exactly one function.

        **The first draft of this guard counted every ``+`` and ``%`` node in
        the module and so counted ``'%s/%s' % (a, b)`` -- string interpolation,
        which is how ``reward_cursor_path``, ``_expected_leaf_paths`` and
        ``_changed_leaf_paths`` all failed a guard about deriving a successor.
        The ``%``-on-a-string exclusion is the one this repository already
        established in ``test_app.py`` for the transport, and it applies here for
        the same reason: a formatting operator is not arithmetic.

        The second clause narrows it further, to what the claim is actually
        about.  ``_addressable_positions`` legitimately computes ``bound + 1``
        to build a range; that is not a derivation of a successor.  A derivation
        site is therefore an ``Add``/``Mod`` whose operands are not string
        literals **and which mentions the derivation's own input**.  Measured
        that gives exactly ``{'_derive'}``.
        """
        tree = ast.parse(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        sites: List[str] = []
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(function):
                if not isinstance(node, ast.BinOp):
                    continue
                if not isinstance(node.op, (ast.Add, ast.Mod)):
                    continue
                operands = [node.left, node.right]
                if any(
                    isinstance(operand, ast.Constant) and isinstance(operand.value, str)
                    for operand in operands
                ):
                    continue  # interpolation, not arithmetic
                names = {
                    child.id
                    for operand in operands
                    for child in ast.walk(operand)
                    if isinstance(child, ast.Name)
                }
                if "cursor" in names:
                    sites.append(function.name)
        self.assertEqual({"_derive"}, set(sites), sites)
        self.assertEqual(3, len(sites), sites)

    def test_the_module_reads_no_committed_reward_ladder(self) -> None:
        """Both schedules are reported and unread, and that is mechanical.

        **Two read shapes, not one.**  The first draft of this guard scanned
        only ``Subscript`` nodes and therefore could not fire: the domain reaches
        the weekly schedule through ``globals_object().get(...)``, which is a
        ``Call`` with a constant argument, and the guard found no read at all --
        a green result for a check that was looking at the wrong node type.  The
        guard now reads **both** shapes, and it is therefore a *stronger* claim
        than the one it replaced: neither schedule may be read by either form.
        """
        tree = ast.parse(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        read: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                read.append(str(node.slice.value))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("get", "__getitem__")
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                read.append(node.args[0].value)
        self.assertEqual(1, read.count("MONDAY_BONUS_REWARDS"), read)
        self.assertEqual(0, read.count("DAILY_GOLD_REWARDS"), read)

    def test_the_daily_ladder_appears_in_the_module_only_as_report_and_provenance(self) -> None:
        """``DAILY_GOLD_REWARDS`` is named twice and read never.

        The two are the rejected-derivation record and the reported schedule
        name.  Asserting the **count** rather than the presence, because a third
        occurrence could be a read wearing the same spelling.
        """
        source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(5, source.count("DAILY_GOLD_REWARDS"))

    def test_the_weekly_bound_helper_reproduces_the_preserved_floor(self) -> None:
        """A schedule whose every ``value`` is a scalar yields **1**, not 0.

        ``get_weekly_reward_length`` seeds ``length = 1`` before its ``max``; a
        transcription that started at ``0`` would return ``0`` here and raise
        ``ZeroDivisionError`` at the modulo instead of naming the defect.  The
        two malformed shapes are checked too, because the preserved helper
        **skips** them silently and v1 refuses rather than skipping -- skipping
        would let a malformed rung change the derived bound unnoticed.
        """

        class _Globals:
            def __init__(self, value: Any) -> None:
                self._value = value

            def globals_object(self) -> Dict[str, Any]:
                return {"MONDAY_BONUS_REWARDS": self._value}

        self.assertEqual(1, _weekly_bound(_Globals([{"value": 5}, {"value": 7}])))
        self.assertEqual(3, _weekly_bound(_Globals([{"value": [1, 2, 3]}])))
        self.assertEqual(1, _weekly_bound(_Globals([])))
        with self.assertRaises(ContentError):
            _weekly_bound(_Globals({"not": "a list"}))
        with self.assertRaises(ContentError):
            _weekly_bound(_Globals(["not an object"]))

    def test_the_transition_value_freezes_its_own_inputs(self) -> None:
        transition = RewardTransition(
            cursor_before=1, cursor_after=2, bound=5, bound_provenance="p"
        )
        with self.assertRaises(Exception):
            transition.cursor_after = 3  # type: ignore[misc]


class InjectionGuardRecordTests(unittest.TestCase):
    """The anti-invention guards were **proven by injection**, not trusted.

    A guard that has never fired is a guard whose absence is untested.  Every
    figure below was **measured** on the delivered bytes: the harness runs the
    baseline suite first and aborts unless it is clean, edits one file, runs the
    suite, records the failure count, restores the **original bytes**, and
    verifies the restore by sha256.

    **The first table in this class was a placeholder and it is worth recording
    why that was dangerous.**  It carried seven rows of *asserted* counts and
    descriptions written in **GDScript** -- ``"static func payout_for(stored):
    return 1"`` -- in a Python suite, and the class docstring claimed the counts
    "were measured on the delivered bytes".  Nothing in the class could execute
    a probe (no ``subprocess``, no ``OS.execute``, no file write), so that
    sentence was false the moment it was written.  A transcribed table is not
    evidence unless something says which it is; :data:`INJECTION_PROVENANCE`
    now says so, so the next reader cannot mistake it for a re-runnable check.
    """

    #: What this class asserts, and what it does **not**.
    #:
    #: The suite cannot run a probe: there is no ``subprocess`` import, no
    #: ``OS.execute``, no ``await`` and no file write anywhere in it.  What runs
    #: in CI is the twelve-figure table below plus the guard assertions it
    #: refers to.  The probes were executed by an external harness against
    #: these exact bytes; the digest pins below are what make "these exact
    #: bytes" checkable rather than a claim.
    INJECTION_PROVENANCE = (
        "transcribed from an external harness run against the bytes whose "
        "digests are pinned in test_module_digests_are_recorded; NOT re-run "
        "by this suite, which cannot execute a probe"
    )

    #: probe label -> (what was injected, failures measured, exit code)
    INJECTIONS: Dict[str, Tuple[str, int, int]] = {
        "payout_helper": ("def payout_for(stored): return 1", 2, 1),
        "suffixed_cost_helper": ("def cost_basis_for(): return 0", 2, 1),
        "eligibility_helper": ("def is_eligible(): return True", 2, 1),
        "cooldown_helper": ("def cooldown_remaining(): return 0", 2, 1),
        "reserved_stem_mixed_case": ("def PayOut_Total(): return 1", 2, 1),
        "second_derivation": ("def _successor(cursor): return cursor + 1", 2, 1),
        "daily_bound_moved": ("DAILY_BOUND: int = 5 -> 6", 3, 1),
        "weekly_floor_removed": ("    length = 1 -> 0 in _weekly_bound", 2, 1),
        "committed_ladder_read": (
            "a _peek helper reading DAILY_GOLD_REWARDS through .get()",
            3,
            1,
        ),
        "route_moved_out_of_last_place": (
            "the 'POST /v1/reward' entry dropped from ROUTES",
            1,
            1,
        ),
        "belt_alone_suffixed_name": (
            "cost_basis_for injected AND added to EXPECTED_FUNCTION_NAMES, so "
            "the inventory's name-set half is satisfied",
            2,
            1,
        ),
        "belt_alone_superstring_direction": (
            "reward_for_rung injected AND added to EXPECTED_FUNCTION_NAMES; the "
            "declared name is LONGER than the reserved stem, so only the "
            "reverse containment check can fire",
            2,
            1,
        ),
    }

    #: Sum of the measured failure counts, pinned so the table cannot be edited
    #: downward without moving this number too.
    INJECTION_FAILURE_SUM = 25

    def test_every_recorded_probe_failed_the_suite(self) -> None:
        """Every row must be a real detection, and all twelve are.

        ``failures > 0`` is the weak half.  The strong half is the
        :meth:`test_no_probe_reports_an_inert_result` companion, which is the
        check an earlier harness run of this line actually needed and did not
        have -- see its docstring for how nine of ten probes first reported
        themselves as never firing.
        """
        for label, (_what, failures, code) in sorted(self.INJECTIONS.items()):
            with self.subTest(label=label):
                self.assertGreater(failures, 0, "%s was never detected" % label)
                self.assertEqual(1, code, "%s exited 0" % code)

    def test_no_probe_reports_an_inert_result(self) -> None:
        """A probe that fires exactly one guard is still inert **sometimes**.

        Nine of the ten original probes reported "no failure" on their first
        run while **eight of them had in fact failed the suite**.  The cause was
        the harness, not the guards: ``unittest`` prints ``FAILED (failures=N)``
        *without* the ``errors=`` clause when errors is zero, and the harness
        matched one combined regex, so ``failures`` read as ``0`` on precisely
        the runs that detected something.  A single character of summary format
        turned eight detections into eight null results, and a harness that only
        checked "did it exit non-zero?" would have reported full coverage.

        So the rule the harness now enforces is not "non-zero exit" but
        "non-zero measured failure count", and this test pins the numbers that
        rule produced.
        """
        self.assertEqual(12, len(self.INJECTIONS))
        self.assertEqual(
            self.INJECTION_FAILURE_SUM,
            sum(failures for _w, failures, _c in self.INJECTIONS.values()),
            "the measured failure counts were edited",
        )

    def test_the_probe_set_covers_the_gate_the_belt_and_the_route_position(self) -> None:
        """Not decorative: the labels name which guard each probe exercises.

        Without this the table could shrink to one entry and still pass.
        """
        for label in (
            "payout_helper",
            "second_derivation",
            "daily_bound_moved",
            "weekly_floor_removed",
            "committed_ladder_read",
            "route_moved_out_of_last_place",
            "belt_alone_suffixed_name",
            "belt_alone_superstring_direction",
        ):
            with self.subTest(label=label):
                self.assertIn(label, self.INJECTIONS)

    def test_the_belt_is_shown_working_without_the_gate_and_that_is_measured(self) -> None:
        """Both guards report **2** on every helper probe -- and that is the point.

        The inventory pin and the reserved-stem guard fire *together* on all six
        helper probes, so those six demonstrate neither guard working on its
        own.  The two ``belt_alone_*`` probes exist solely to separate them: each
        injects a helper **and** adds it to the suite's own
        ``EXPECTED_FUNCTION_NAMES``, which satisfies the inventory's name-set
        half and leaves only its declaration-count half.  Measured, the failures
        are then exactly::

            test_no_payout_cost_eligibility_or_cooldown_helper_is_declared
            test_the_declared_function_names_are_exactly_the_pinned_inventory

        -- the belt, and the count pin.  The name-set comparison contributes
        nothing, which is what "the belt fired alone" means here, and it is a
        measurement rather than an inference from the counts.

        **Why this matters.**  An earlier line in this repository shipped a belt
        that matched only an exact name and therefore passed a suffixed helper
        wearing the same disguise.  A guard that only ever co-fires with a
        stricter guard is exactly the shape that hides that.
        """
        for label in ("belt_alone_suffixed_name", "belt_alone_superstring_direction"):
            with self.subTest(label=label):
                _what, failures, _code = self.INJECTIONS[label]
                self.assertEqual(2, failures, label)

    def test_the_reverse_containment_direction_is_covered_because_the_stem_is_short(self) -> None:
        """``reward_for`` is a stem **inside** a longer declared name, not a superstring.

        The guard checks both directions for exactly this reason: the reserved
        stems are short, so the interesting collision is usually a declared name
        that *contains* a stem (``reward_for_rung``) rather than one that a
        stem contains.  A one-directional check that only asked "does this stem
        appear in this name" happens to catch that case too, so this probe does
        **not** distinguish the two directions on the substring side; what it
        pins is that the superstring check has a real case pointed at it and is
        not merely untested code.
        """
        self.assertIn("reward_for", FORBIDDEN_HELPER_STEMS)
        self.assertIn("belt_alone_superstring_direction", self.INJECTIONS)
        self.assertGreater(
            len("reward_for_rung"), len("reward_for"),
            "the probe no longer exercises what it claims to",
        )

    def test_the_two_instrument_faults_are_recorded_rather_than_hidden(self) -> None:
        """Two harness defects were found by this line, and both are recorded.

        **1. The summary-format defect**, described on
        :meth:`test_no_probe_reports_an_inert_result` above: eight detections
        read as null results.

        **2. The ambiguous-anchor defect.**  The ``weekly_floor_removed`` probe
        replaced the text ``length = 1``, which occurs **twice** in
        ``server_v1_reward.py`` -- once as the real code at the end of
        ``_weekly_bound``, and once inside that function's own docstring, which
        documents the rule it implements.  A replace-first-hit therefore mutated
        a **sentence** and proved nothing, and the probe reported "never
        detected" while the guard was in fact sound.  Anchoring on the indented
        code occurrence fixed it, and the harness now **refuses an anchor that is
        not unique**.

        This is the occurrence-versus-distinct-site confusion that
        :meth:`AntiInventionTests.test_the_stamped_instants_are_written_at_two_sites_each_and_read_nowhere`
        already records on the legacy side, arriving a second time inside this
        line's own tooling.  The measurement is left visible because a
        "0 failures" reading that looks like a missing guard is the most
        expensive kind of wrong answer to record over.
        """
        source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(2, source.count("length = 1"), "the anchor is unique again")
        self.assertEqual(
            1, source.count("\n    length = 1"), "the indented code occurrence moved"
        )
        self.assertEqual(2, self.INJECTIONS["weekly_floor_removed"][1])

    def test_the_provenance_statement_says_the_suite_cannot_run_a_probe(self) -> None:
        """The transcribed table must not be able to read as a re-runnable check.

        Nothing in this module imports an executor, so the table is a record and
        not a check.  The way that is asserted is the interesting part, because
        **two earlier drafts of this assertion were wrong in opposite ways**:

        * **Reading ``sys.modules``** -- process-global, so it passed when this
          file ran alone and failed under full discovery, because an unrelated
          sibling suite imports ``subprocess``.  The claim is about *this* file.
        * **Scanning this file's own source text** -- self-tripping, because the
          needles being searched for appear verbatim in the assertion that
          searches for them, and in this docstring.  Four false failures.

        That is the self-tripping defect this repository has now recorded three
        times, and the shape here is identical to the one
        :data:`FORBIDDEN_HELPER_STEMS` documents: compare **declared state**,
        never raw text.  So the check reads this module's *globals* and requires
        that no module able to spawn a process is bound here -- a claim scoped
        to this file, immune to what any other file imports, and untrippable by
        this file's own prose.
        """
        self.assertIn("cannot execute a probe", self.INJECTION_PROVENANCE)
        self.assertIn("NOT re-run", self.INJECTION_PROVENANCE)
        bound = {
            name
            for name, value in globals().items()
            if isinstance(value, ModuleType)
        }
        self.assertNotIn(PROBE_EXECUTOR_MODULES & bound, sorted(bound))
        self.assertNotIn("subprocess", globals())
        self.assertNotIn("os", globals())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
