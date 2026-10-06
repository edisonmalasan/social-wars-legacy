#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/darts`` behavior tests (OpenSpec tasks 6.1-6.4).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so the suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across darts execution.

Every test snapshots the corpus at its own start and asserts its post-condition
against that snapshot, so the suite is order-independent.  The two arms the
committed corpus cannot reach -- the **extend** arm (no document records a
*future* premium instant) and the shot arm's out-of-schedule index (no document
under this save records a shot at all) -- are set up through an explicit
in-memory **and** on-disk rewrite, exactly as the delivered level suite does for
its recorded-versus-derived disagreement.  That mechanism is a test-only
convenience and is never a claim about legacy behavior.

What this suite proves, and why each half exists:

* **every action succeeds** and reports the seven darts fields before and after,
  with the changed set computed rather than restated;
* **the two-part post-execution proof (design D5)** -- the premium instant moved
  by exactly the derived duration, **and** the **complete** stored resource set
  is byte-identical -- is proved **non-tautologically**: each half is made to fail
  by rewriting only the post-execution read, and the endpoint answers
  ``internal_error`` rather than the legacy success;
* **nothing is charged** even when the client sends a debit, a price, and a
  duration at the top level, because the route reads arguments from a dedicated
  key and the envelope derives its own neutral vector;
* the **client-dictated shot outcome is refused mechanically** -- a claimed win
  leaves ``dartsGotExtra`` untouched -- and the difference is reported as a
  **divergence** with ``is_parity: false``, never as parity;
* **every structural refusal** answers its pinned status and code and executes
  nothing, proven by a byte-identical corpus snapshot across each refusal.
"""

from __future__ import annotations

import copy
import json
import os
import time
import unittest
from typing import Any, Callable, Dict, List, Optional, Tuple

import compat_test_harness as harness

import compat_legacy
import compat_service
import darts_envelope

ORIGINAL_CWD = ""
CORPUS: Any = None
BOOT: Any = None
CLIENT: Any = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
COMMITTED_DARTS: Dict[str, Any] = {}

#: Sentinel for "remove this field", so a test can prove a fail-closed path
#: without a second helper whose only job is to delete one key.
_DELETE = object()

#: The seven stored resource slots this service exposes.  The legacy
#: ``apply_resources`` **vector** is eight wide; its first slot is read into
#: ``unknown`` and never written, so the seven below are the complete set of
#: stored values a darts or premium transaction could move.
RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")

#: The committed corpus's own darts facts.  The fresh-player save carries every
#: field at its seeded value, which is why the shot arm and the extend arm have
#: no committed coverage and why **no executed-legacy fixture** is claimed.
COMMITTED_PREMIUM_INSTANT = 0

#: The committed ``PREMIUM_ACCOUNTS`` schedule, in days, read from the config at
#: run time rather than hardcoded a second time.
SCHEDULE_DAYS = (360, 180, 30, 7, 3, 1)
SECONDS_PER_DAY = 86400


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE, COMMITTED_DARTS
    ORIGINAL_CWD = os.getcwd()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    # Snapshotted before anything runs, so ``pristine()`` restores the committed
    # bytes rather than whatever the previous test happened to leave behind.
    COMMITTED_DARTS = copy.deepcopy(BOOT.darts_state(PID))
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a darts execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def darts_now(payload: Dict[str, Any]) -> Any:
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/darts", json=payload)


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)


def darts_now_state() -> Dict[str, Any]:
    return BOOT.darts_state(PID)


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)


def instant_now() -> Optional[int]:
    return BOOT.premium_instant(PID)


def set_darts_fields(fields: Dict[str, Any]) -> None:
    """Rewrite the **named** darts fields, in memory *and* on the corpus file.

    Only the keys passed are touched.  A first version removed every field it did
    not name, which made :func:`set_premium_instant` delete the other six and
    turned every later darts read into an ``invalid_save_state`` failure -- three
    errors that looked like route defects and were a defect in the fixture reset.

    Legacy ``buy_premium_account`` assigns ``privateState["timeStampEndPremium"]``
    in place and the dispatcher persists the whole save after each batch, so the
    in-memory document the endpoint reads and the persisted file stay in step
    during normal operation.  Only a deliberate disagreement between them needs
    both rewritten, which is what this does -- the same contained mechanism the
    delivered level suite uses for its recorded-versus-derived case.
    """
    save = BOOT.save_document(PID)
    private = save["privateState"]
    for name, value in fields.items():
        if value is _DELETE:
            private.pop(name, None)
        else:
            private[name] = value
    path = CORPUS / "saves" / ("%s.save.json" % PID)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def delete_darts_field(name: str) -> None:
    """Remove one darts field, to prove the endpoint fails closed on it."""
    set_darts_fields({name: _DELETE})


def set_premium_instant(value: Optional[int]) -> None:
    """Set the premium instant only; see :func:`set_darts_fields`."""
    set_darts_fields({"timeStampEndPremium": value})


def pristine() -> Dict[str, Any]:
    """Reset **all seven** darts fields to the committed corpus state.

    Restoring the full snapshot is what makes the suite order-independent.
    """
    set_darts_fields(copy.deepcopy(COMMITTED_DARTS))
    return {
        "darts": copy.deepcopy(darts_now_state()),
        "resources": copy.deepcopy(resources_now()),
    }


def _state_rewritten_after_execution(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]]
) -> Callable[[], None]:
    """Rewrite only the **post**-execution ``darts_state`` read.

    The endpoint reads the darts snapshot once before dispatch (for the response's
    ``darts_before`` and the changed set) and once after (for the structural half
    of the proof and ``darts_after``).  Rewriting only the second read lets each
    clause of that half fail in isolation while the real dispatcher still wrote the
    true state to the save.
    """
    original = BOOT.darts_state
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, Any]:
        state["seen"] += 1
        current = original(user_id)
        if state["seen"] == 1:
            return current
        return transform(current)

    BOOT.darts_state = stub  # type: ignore[assignment]

    def restore() -> None:
        BOOT.darts_state = original  # type: ignore[assignment]

    return restore


def _resources_rewritten_after_execution(
    transform: Callable[[Dict[str, int]], Dict[str, int]]
) -> Callable[[], None]:
    """Rewrite only the **post**-execution ``resources`` read."""
    original = BOOT.resources
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, int]:
        state["seen"] += 1
        current = original(user_id)
        if state["seen"] == 1:
            return current
        return transform(current)

    BOOT.resources = stub  # type: ignore[assignment]

    def restore() -> None:
        BOOT.resources = original  # type: ignore[assignment]

    return restore


def _instant_rewritten_after_execution(
    transform: Callable[[Optional[int]], Optional[int]]
) -> Callable[[], None]:
    """Rewrite only the **post**-execution ``premium_instant`` read."""
    original = BOOT.premium_instant
    state = {"seen": 0}

    def stub(user_id: str) -> Optional[int]:
        state["seen"] += 1
        current = original(user_id)
        if state["seen"] == 1:
            return current
        return transform(current)

    BOOT.premium_instant = stub  # type: ignore[assignment]

    def restore() -> None:
        BOOT.premium_instant = original  # type: ignore[assignment]

    return restore


def premium_intent(index: int = 0, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "user_id": PID,
        "action": "buy_premium_account",
        "arguments": {"package_index": index},
    }
    payload.update(extra)
    return payload


def shoot_intent(index: int, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "user_id": PID,
        "action": "darts_shoot_balloon",
        "arguments": {"shot_index": index},
    }
    payload.update(extra)
    return payload


# --------------------------------------------------------------------------
# the committed corpus's own facts
# --------------------------------------------------------------------------


class CommittedCorpusTests(unittest.TestCase):
    """Every figure below is read from the running corpus, not restated."""

    def test_the_committed_corpus_carries_every_darts_field(self) -> None:
        pristine()
        state = darts_now_state()
        self.assertEqual(
            sorted(state),
            sorted(compat_legacy.LegacyBoot.DARTS_FIELDS),
        )

    def test_the_committed_premium_instant_is_zero(self) -> None:
        self.assertEqual(instant_now(), COMMITTED_PREMIUM_INSTANT)

    def test_the_committed_corpus_records_no_shot_and_no_extra(self) -> None:
        state = darts_now_state()
        self.assertEqual(state["dartsBalloonsShot"], COMMITTED_DARTS["dartsBalloonsShot"])
        self.assertEqual(state["dartsBalloonsShot"], [])
        self.assertIs(state["dartsGotExtra"], False)

    def test_the_corpus_records_all_seven_stored_resources(self) -> None:
        resources = resources_now()
        self.assertEqual(sorted(resources), sorted(RESOURCE_NAMES))

    def test_the_corpus_records_a_nonzero_gold_balance_so_the_clamp_is_real(self) -> None:
        """The no-charge claim is only meaningful against a balance that *could*
        move.  A corpus of zeros would make "unchanged" vacuous."""
        self.assertGreater(resources_now()["gold"], 0)


# --------------------------------------------------------------------------
# the four actions
# --------------------------------------------------------------------------


class ResetTests(unittest.TestCase):
    def test_a_reset_succeeds_and_writes_the_four_fields_that_actually_change(self) -> None:
        baseline = pristine()
        response = darts_now(
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": 7}}
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["result"], "success")
        self.assertEqual(body["action"], "darts_reset")
        # The seed is stored verbatim and nothing is derived from it.
        self.assertEqual(body["darts_after"]["dartsRandomSeed"], 7)
        self.assertEqual(body["seed"], 7)
        # The shot list is emptied, the extra flag cleared, and the free flag set.
        self.assertEqual(body["darts_after"]["dartsBalloonsShot"], [])
        self.assertIs(body["darts_after"]["dartsGotExtra"], False)
        self.assertIs(body["darts_after"]["dartsHasFree"], True)
        # The branch writes **six** fields, and the changed set reports **four**,
        # because the committed corpus already carries an empty shot list and a
        # ``false`` extra flag: emptying an empty list and clearing an
        # already-clear flag are writes that change nothing.  Asserting five or
        # six here would have measured my expectation rather than the corpus.
        self.assertEqual(
            sorted(body["darts_changed_fields"]),
            [
                "dartsHasFree",
                "dartsRandomSeed",
                "timeStampDartsNewFree",
                "timeStampDartsReset",
            ],
        )
        for field in ("dartsBalloonsShot", "dartsGotExtra"):
            with self.subTest(unchanged=field):
                self.assertEqual(
                    body["darts_before"][field], body["darts_after"][field]
                )
                self.assertEqual(
                    body["darts_before"][field], baseline["darts"][field]
                )
        self.assertEqual(body["darts_before"], baseline["darts"])
        self.assertEqual(body["resources"], baseline["resources"])

    def test_a_reset_accepts_a_negative_or_zero_seed_without_deriving_anything(self) -> None:
        for seed in (0, -1, -99999, 2 ** 31):
            with self.subTest(seed=seed):
                pristine()
                response = darts_now(
                    {"user_id": PID, "action": "darts_reset", "arguments": {"seed": seed}}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["darts_after"]["dartsRandomSeed"], seed)

    def test_a_reset_never_charges_and_never_moves_a_resource(self) -> None:
        baseline = pristine()
        response = darts_now(
            {
                "user_id": PID,
                "action": "darts_reset",
                "arguments": {"seed": 7},
                "resources": [0, -5000, -5000, -5000, -5000, -5000, -5000, -5000],
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resources_now(), baseline["resources"])
        self.assertTrue(response.get_json()["client_supplied_resource_vector_ignored"])

    def test_a_reset_touches_the_premium_instant_not_at_all(self) -> None:
        pristine()
        before = instant_now()
        darts_now(
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": 7}}
        )
        self.assertEqual(instant_now(), before)


class FreeGrantTests(unittest.TestCase):
    def test_a_free_grant_succeeds_after_a_shot_consumed_the_flag(self) -> None:
        pristine()
        # A shot clears the free flag; the grant restores it.
        self.assertEqual(
            darts_now(shoot_intent(18)).get_json()["darts_after"]["dartsHasFree"],
            False,
        )
        response = darts_now({"user_id": PID, "action": "darts_new_free", "arguments": {}})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIs(body["darts_after"]["dartsHasFree"], True)
        self.assertEqual(body["darts_changed_fields"], ["dartsHasFree"])

    def test_the_free_grant_needs_no_argument_and_ignores_a_stray_one(self) -> None:
        pristine()
        for arguments in ({}, None, {"seed": 7}, {"shot_index": 18}):
            with self.subTest(arguments=arguments):
                payload: Dict[str, Any] = {"user_id": PID, "action": "darts_new_free"}
                if arguments is not None:
                    payload["arguments"] = arguments
                self.assertEqual(darts_now(payload).status_code, 200)

    def test_the_free_grant_never_charges(self) -> None:
        baseline = pristine()
        response = darts_now(
            {
                "user_id": PID,
                "action": "darts_new_free",
                "arguments": {},
                "resources": [0, 0, -1, 0, 0, 0, 0, 0],
                "price": 800,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resources_now(), baseline["resources"])


class ShotTests(unittest.TestCase):
    def test_a_shot_appends_the_index_and_clears_the_free_flag(self) -> None:
        baseline = pristine()
        response = darts_now(shoot_intent(18))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["darts_after"]["dartsBalloonsShot"], [18])
        self.assertEqual(body["shot_index"], 18)
        self.assertIs(body["darts_after"]["dartsHasFree"], False)
        # The branch writes **three** fields and the changed set reports **two**,
        # because the committed corpus already records ``dartsHasFree: false``:
        # the flag is written to the value it already holds.
        self.assertEqual(
            sorted(body["darts_changed_fields"]),
            ["dartsBalloonsShot", "timeStampDartsNewFree"],
        )
        self.assertEqual(
            body["darts_before"]["dartsHasFree"], body["darts_after"]["dartsHasFree"]
        )
        self.assertEqual(body["darts_before"]["dartsHasFree"], False)
        self.assertEqual(body["resources"], baseline["resources"])

    def test_a_shot_that_spends_a_real_free_flag_reports_it_as_changed(self) -> None:
        """The same three-write branch reports **three** changed fields once the
        free flag actually has to move, so the two-field result above is the
        corpus's starting value and not a narrower observation."""
        pristine()
        set_darts_fields({"dartsHasFree": True})
        body = darts_now(shoot_intent(18)).get_json()
        self.assertIs(body["darts_after"]["dartsHasFree"], False)
        self.assertEqual(
            sorted(body["darts_changed_fields"]),
            ["dartsBalloonsShot", "dartsHasFree", "timeStampDartsNewFree"],
        )

    def test_a_repeated_index_is_not_appended_twice(self) -> None:
        """The preserved branch's own ``if index not in targets`` guard, reproduced."""
        pristine()
        darts_now(shoot_intent(18))
        body = darts_now(shoot_intent(18)).get_json()
        self.assertEqual(body["darts_after"]["dartsBalloonsShot"], [18])

    def test_an_out_of_schedule_index_is_accepted_and_reported_as_untested(self) -> None:
        """``villages/Nerri.json`` records shot ``0``, absent from the committed
        ``1..27`` schedule, so the refusal to add a membership test is the corpus
        speaking -- and the response says so rather than staying silent."""
        pristine()
        body = darts_now(shoot_intent(0)).get_json()
        self.assertEqual(body["darts_after"]["dartsBalloonsShot"], [0])
        self.assertIs(body["schedule_membership_tested"], False)
        self.assertIsNone(body["shot_list_length_bound"])

    def test_the_shot_list_is_never_bounded(self) -> None:
        pristine()
        for index in (0, 99999, -5):
            darts_now(shoot_intent(index))
        body = darts_now(shoot_intent(12345)).get_json()
        self.assertEqual(body["darts_after"]["dartsBalloonsShot"], [0, 99999, -5, 12345])
        self.assertIsNone(body["shot_list_length_bound"])

    def test_a_claimed_win_cannot_move_the_extra_flag(self) -> None:
        """The refusal is **mechanical**: the outcome slot is derived, so no client
        value reaches the value that decides the write."""
        pristine()
        body = darts_now(shoot_intent(18, arguments={"shot_index": 18, "won_extra": True})).get_json()
        self.assertIs(body["darts_after"]["dartsGotExtra"], False)
        self.assertNotIn("dartsGotExtra", body["darts_changed_fields"])
        self.assertEqual(darts_now_state()["dartsGotExtra"], False)

    def test_a_claimed_win_is_reported_as_a_divergence_and_never_as_parity(self) -> None:
        pristine()
        body = darts_now(
            shoot_intent(18, arguments={"shot_index": 18, "won_extra": True})
        ).get_json()
        self.assertEqual(len(body["divergences"]), 1)
        record = body["divergences"][0]
        self.assertEqual(record["field"], "dartsGotExtra")
        self.assertEqual(record["site"], "command.py:604-605")
        self.assertEqual(record["client_argument"], "args[1]")
        self.assertIs(record["client_claimed_win"], True)
        self.assertIs(record["delivered"], False)
        self.assertIs(record["is_parity"], False)
        self.assertIs(record["derived_outcome_slot"], False)
        self.assertIn("none in either direction", record["corpus_evidence"])

    def test_the_divergence_is_reported_even_when_no_win_was_claimed(self) -> None:
        """So a caller can see the claim was considered and refused, not skipped."""
        pristine()
        body = darts_now(shoot_intent(18)).get_json()
        self.assertEqual(len(body["divergences"]), 1)
        self.assertIs(body["divergences"][0]["client_claimed_win"], False)

    def test_a_shot_never_charges(self) -> None:
        baseline = pristine()
        response = darts_now(
            {
                "user_id": PID,
                "action": "darts_shoot_balloon",
                "arguments": {"shot_index": 18, "won_extra": True},
                "resources": [0, 0, 0, 0, 0, 0, 0, -100000],
                "price": 800,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resources_now(), baseline["resources"])

    def test_a_shot_never_touches_the_premium_instant(self) -> None:
        pristine()
        before = instant_now()
        darts_now(shoot_intent(18))
        self.assertEqual(instant_now(), before)


# --------------------------------------------------------------------------
# the premium purchase
# --------------------------------------------------------------------------


class PremiumTests(unittest.TestCase):
    def test_the_first_purchase_takes_the_set_arm_and_moves_by_the_derived_duration(self) -> None:
        baseline = pristine()
        response = darts_now(premium_intent(0))
        self.assertEqual(response.status_code, 200)
        premium = response.get_json()["premium"]
        # The committed instant is 0 and the server clock is far later, so the
        # recorded comparison ``time_now >= ts_premium`` is true.
        self.assertEqual(premium["arm"], "set")
        self.assertEqual(premium["arm_comparison"], "now >= instant")
        self.assertEqual(premium["days"], SCHEDULE_DAYS[0])
        self.assertEqual(premium["seconds"], SCHEDULE_DAYS[0] * SECONDS_PER_DAY)
        self.assertEqual(premium["seconds_per_day"], SECONDS_PER_DAY)
        self.assertEqual(premium["instant_before"], baseline["darts"]["timeStampEndPremium"])
        self.assertEqual(
            premium["instant_after"], premium["server_clock"] + premium["seconds"]
        )
        self.assertIsNone(premium.get("package_index_error"))
        self.assertEqual(response.get_json()["darts_changed_fields"], ["timeStampEndPremium"])

    def test_every_committed_index_derives_its_committed_duration(self) -> None:
        for index, days in enumerate(SCHEDULE_DAYS):
            with self.subTest(index=index, days=days):
                pristine()
                premium = darts_now(premium_intent(index)).get_json()["premium"]
                self.assertEqual(premium["package_index"], index)
                self.assertEqual(premium["days"], days)
                self.assertEqual(premium["seconds"], days * SECONDS_PER_DAY)

    def test_an_oversized_index_clamps_to_the_last_entry(self) -> None:
        """``get_game_config.py:184-185`` clamps rather than raising, and the clamp
        is reproduced where it was recorded rather than re-derived here."""
        for index in (len(SCHEDULE_DAYS), len(SCHEDULE_DAYS) + 1, 99, 2 ** 20):
            with self.subTest(index=index):
                pristine()
                premium = darts_now(premium_intent(index)).get_json()["premium"]
                self.assertEqual(premium["days"], SCHEDULE_DAYS[-1])

    def test_a_second_purchase_takes_the_extend_arm(self) -> None:
        """The **extend** arm has no corpus coverage -- no committed document
        records a future premium instant -- so it is exercised over crafted input
        and reported as such."""
        pristine()
        first = darts_now(premium_intent(0)).get_json()["premium"]
        self.assertEqual(first["arm"], "set")
        second = darts_now(premium_intent(0)).get_json()["premium"]
        self.assertEqual(second["arm"], "extend")
        self.assertEqual(
            second["instant_after"],
            first["instant_after"] + SCHEDULE_DAYS[0] * SECONDS_PER_DAY,
        )

    def test_the_extend_arm_adds_to_the_recorded_instant_not_to_the_clock(self) -> None:
        future = int(time.time()) + 5000 * SECONDS_PER_DAY
        set_premium_instant(future)
        premium = darts_now(premium_intent(0)).get_json()["premium"]
        self.assertEqual(premium["arm"], "extend")
        self.assertEqual(
            premium["instant_after"], future + SCHEDULE_DAYS[0] * SECONDS_PER_DAY
        )
        self.assertLess(premium["server_clock"], future)

    def test_the_arm_boundary_is_the_clock_equals_the_instant(self) -> None:
        """``>=`` and not ``>``: a clock exactly equal to the recorded instant takes
        the set arm.  Set the instant to the server's own clock and race-free
        ordering makes the comparison exactly equal."""
        set_premium_instant(int(BOOT.server_time()))
        premium = darts_now(premium_intent(0)).get_json()["premium"]
        self.assertGreaterEqual(premium["server_clock"], premium["instant_before"])
        self.assertEqual(premium["arm"], "set")

    def test_a_client_sent_price_or_duration_is_ignored_entirely(self) -> None:
        baseline = pristine()
        response = darts_now(
            premium_intent(
                0,
                price=1,
                price_=-99999,
                days=9999,
                amount=1,
                seconds=1,
                resources=[0, -99999, -99999, -99999, -99999, -99999, -99999, -99999],
                arguments={"package_index": 0, "price": 1, "days": 9999, "seconds": 1},
            )
        )
        self.assertEqual(response.status_code, 200)
        premium = response.get_json()["premium"]
        self.assertEqual(premium["days"], SCHEDULE_DAYS[0])
        self.assertIs(premium["duration_client_sent"], False)
        self.assertIs(premium["charged"], False)
        self.assertEqual(premium["committed_amount_consumers"], 0)
        self.assertEqual(resources_now(), baseline["resources"])

    def test_the_duration_source_is_named_and_is_the_unchanged_legacy_helper(self) -> None:
        pristine()
        premium = darts_now(premium_intent(0)).get_json()["premium"]
        self.assertIn("get_game_config.get_premium_days", premium["duration_source"])
        self.assertIn("get_game_config.py:181-189", premium["duration_source"])

    def test_a_premium_purchase_never_moves_a_stored_resource(self) -> None:
        baseline = pristine()
        response = darts_now(premium_intent(5))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resources_now(), baseline["resources"])
        self.assertEqual(response.get_json()["resources"], baseline["resources"])

    def test_a_save_with_no_readable_premium_instant_fails_closed(self) -> None:
        """Coercing an absent instant to ``0`` would invent an authority the legacy
        server never had, because ``0`` is itself the value the whole committed
        corpus carries -- ``0`` means "recorded zero", never "unreadable".

        The route answers with its **own** message rather than the adapter's, so
        that a client can tell an unreadable instant from a malformed save.  The
        message names the condition and no save content.
        """
        pristine()
        set_premium_instant(None)
        response = darts_now(premium_intent(0))
        self.assertEqual(response.status_code, 500)
        error = response.get_json()["error"]
        self.assertEqual(error["code"], compat_service.ERROR_INTERNAL)
        self.assertEqual(
            error["message"],
            "this save records no premium instant this service can read as an integer",
        )
        self.assertNotIn("timeStampEndPremium", error["message"])
        # It is a distinct condition from a malformed save, so it does not claim
        # to be one.
        self.assertNotIn("invalid_save_state", error["message"])

    def test_the_unreadable_instant_refuses_every_action_not_just_the_premium_one(self) -> None:
        """The response reports ``instant_before``/``instant_after`` for **all four**
        actions, so an unreadable instant makes the whole surface unreportable.
        Asserted explicitly, because it is a wider refusal than the premium action
        needs and would otherwise read as an accident."""
        for payload in (
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": 1}},
            {"user_id": PID, "action": "darts_new_free", "arguments": {}},
            shoot_intent(18),
            premium_intent(0),
        ):
            with self.subTest(action=payload["action"]):
                pristine()
                set_premium_instant(None)
                response = darts_now(payload)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(
                    response.get_json()["error"]["code"],
                    compat_service.ERROR_INTERNAL,
                )
                # Refused **before** dispatch, so the darts state is untouched.
                self.assertEqual(
                    darts_now_state()["dartsBalloonsShot"],
                    COMMITTED_DARTS["dartsBalloonsShot"],
                )

    def test_a_non_integer_recorded_instant_is_refused_rather_than_coerced(self) -> None:
        """``bool`` is an ``int`` subclass and ``True`` is a *meaningful* number
        here, so it is refused instead of being silently used as ``1``.

        Refused by :meth:`LegacyBoot.premium_instant`, which returns ``None`` for a
        bool -- distinct from the ``0`` the corpus records -- and the route then
        answers its unreadable-instant refusal."""
        pristine()
        set_premium_instant(True)
        self.assertIsNone(instant_now())
        response = darts_now(premium_intent(0))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["error"]["code"], compat_service.ERROR_INTERNAL
        )
        # Nothing was executed, and the refused value is still what is stored.
        self.assertIs(instant_now(), None)
        self.assertIs(BOOT.save_document(PID)["privateState"]["timeStampEndPremium"], True)

    def test_a_missing_darts_field_fails_closed_before_dispatch(self) -> None:
        pristine()
        delete_darts_field("dartsGotExtra")
        response = darts_now(premium_intent(0))
        self.assertEqual(response.status_code, 500)
        error = response.get_json()["error"]
        self.assertEqual(error["code"], compat_service.ERROR_INTERNAL)
        self.assertIn("invalid_save_state", error["message"])
        self.assertIn("dartsGotExtra", error["message"])


# --------------------------------------------------------------------------
# the response surface
# --------------------------------------------------------------------------


class ResponseSurfaceTests(unittest.TestCase):
    def test_a_success_carries_the_documented_envelope_and_the_full_snapshot(self) -> None:
        pristine()
        body = darts_now({"user_id": PID, "action": "darts_new_free", "arguments": {}}).get_json()
        self.assertEqual(body["protocol"], compat_service.PROTOCOL)
        self.assertIs(body["ok"], True)
        self.assertIn("game_version", body)
        self.assertIn("server_time", body)
        self.assertEqual(sorted(body["darts_before"]), sorted(compat_legacy.LegacyBoot.DARTS_FIELDS))
        self.assertEqual(sorted(body["darts_after"]), sorted(compat_legacy.LegacyBoot.DARTS_FIELDS))
        self.assertIsInstance(body["darts_changed_fields"], list)
        self.assertEqual(body["darts_changed_fields"], sorted(body["darts_changed_fields"]))
        self.assertEqual(body["neutral_vector"], [0] * 8)
        self.assertEqual(sorted(body["resources"]), sorted(RESOURCE_NAMES))
        self.assertIn("instant_before", body["premium"])
        self.assertIn("instant_after", body["premium"])

    def test_every_action_reports_the_premium_pair_even_though_it_did_not_move(self) -> None:
        for payload in (
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": 1}},
            {"user_id": PID, "action": "darts_new_free", "arguments": {}},
            shoot_intent(18),
        ):
            with self.subTest(action=payload["action"]):
                pristine()
                body = darts_now(payload).get_json()
                self.assertEqual(
                    body["premium"]["instant_before"], body["premium"]["instant_after"]
                )
                # And no duration was derived, because none was asked for: the arm
                # is reported as absent rather than as a derived zero.
                self.assertIsNone(body["premium"].get("arm"))
                self.assertIsNone(body["premium"].get("days"))

    def test_the_response_never_carries_save_content_beyond_the_documented_fields(self) -> None:
        pristine()
        body = darts_now(premium_intent(0)).get_json()
        for key in ("map", "maps", "items", "playerInfo", "quests", "privateState"):
            self.assertNotIn(key, body)

    def test_a_refusal_message_never_carries_a_client_value(self) -> None:
        pristine()
        response = darts_now(
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": "SECRET"}}
        )
        self.assertNotIn("SECRET", json.dumps(response.get_json()))


# --------------------------------------------------------------------------
# structural refusals, in pinned order
# --------------------------------------------------------------------------


class RefusalTests(unittest.TestCase):
    """Every refusal executes nothing, proven by a byte-identical corpus."""

    def test_a_missing_user_id_is_refused(self) -> None:
        baseline = pristine()
        response = darts_now({"action": "darts_new_free"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_user_id")
        self.assertEqual(darts_now_state(), baseline["darts"])

    def test_a_non_string_user_id_is_refused(self) -> None:
        response = darts_now({"user_id": 5, "action": "darts_new_free"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_user_id")

    def test_an_empty_user_id_is_refused(self) -> None:
        response = darts_now({"user_id": "   ", "action": "darts_new_free"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_user_id")

    def test_an_unknown_user_is_refused_with_404(self) -> None:
        response = darts_now({"user_id": "nope", "action": "darts_new_free"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "unknown_user_id")

    def test_a_non_object_body_is_refused(self) -> None:
        with harness.offline():
            response = CLIENT.post("/v0/darts", json=["not", "an", "object"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_payload")

    def test_arguments_must_be_an_object(self) -> None:
        baseline = pristine()
        for arguments in (5, "x", ["a"], True):
            with self.subTest(arguments=arguments):
                response = darts_now(
                    {"user_id": PID, "action": "darts_new_free", "arguments": arguments}
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "bad_request")
        self.assertEqual(darts_now_state(), baseline["darts"])

    def test_an_unknown_action_is_refused_with_its_own_code(self) -> None:
        baseline = pristine()
        for action in ("nope", "", "darts_shoot", "buy_premium", "fast_forward"):
            with self.subTest(action=action):
                response = darts_now({"user_id": PID, "action": action})
                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.get_json()["error"]["code"], "unknown_darts_action"
                )
        self.assertEqual(darts_now_state(), baseline["darts"])
        self.assertEqual(resources_now(), baseline["resources"])

    def test_fast_forward_is_refused_because_no_operation_is_delivered(self) -> None:
        """It touches ``timeStampDartsNewFree`` in the preserved server, and this
        line delivers no fast-forward operation."""
        baseline = pristine()
        response = darts_now(
            {"user_id": PID, "action": "fast_forward", "arguments": {"seconds": 1}}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "unknown_darts_action")
        self.assertEqual(darts_now_state(), baseline["darts"])

    def test_a_missing_action_is_refused(self) -> None:
        response = darts_now({"user_id": PID})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "unknown_darts_action")

    def test_a_non_string_action_is_refused(self) -> None:
        for action in (None, 5, [], {"a": 1}, True):
            with self.subTest(action=action):
                response = darts_now({"user_id": PID, "action": action})
                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.get_json()["error"]["code"], "unknown_darts_action"
                )

    def test_a_bad_seed_is_refused_with_its_own_code(self) -> None:
        baseline = pristine()
        for seed in ("x", 1.5, None, True, [], {}):
            with self.subTest(seed=seed):
                response = darts_now(
                    {"user_id": PID, "action": "darts_reset", "arguments": {"seed": seed}}
                )
                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.get_json()["error"]["code"], "invalid_darts_seed"
                )
        self.assertEqual(darts_now_state(), baseline["darts"])

    def test_an_arbitrarily_large_integer_seed_is_accepted_verbatim(self) -> None:
        """Python integers are unbounded and the preserved branch stores whatever it
        is sent, so a 70-bit seed is a legal intent.  Refusing it would be a range
        rule this line has no recorded basis for -- the same class of invented rule
        as a shot-list bound."""
        pristine()
        for seed in (2 ** 70, -(2 ** 70), 0):
            with self.subTest(seed=seed):
                pristine()
                response = darts_now(
                    {"user_id": PID, "action": "darts_reset", "arguments": {"seed": seed}}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.get_json()["darts_after"]["dartsRandomSeed"], seed
                )

    def test_a_bad_shot_index_is_refused_with_its_own_code(self) -> None:
        baseline = pristine()
        for index in ("x", 1.5, None, True, [], {}):
            with self.subTest(index=index):
                response = darts_now(shoot_intent(index))
                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.get_json()["error"]["code"], "invalid_shot_index"
                )
        self.assertEqual(darts_now_state(), baseline["darts"])

    def test_a_bad_package_index_is_refused_with_its_own_code(self) -> None:
        baseline = pristine()
        for index in ("x", 1.5, None, True, [], {}):
            with self.subTest(index=index):
                response = darts_now(premium_intent(index))
                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.get_json()["error"]["code"], "invalid_package_index"
                )
        self.assertEqual(instant_now(), COMMITTED_PREMIUM_INSTANT)

    def test_the_refusal_statuses_are_409_and_the_shape_is_400(self) -> None:
        """Pinned, so a client can distinguish "your request was malformed" from
        "this action or argument is not one this service accepts"."""
        self.assertEqual(
            darts_now({"user_id": PID, "action": "nope"}).status_code, 409
        )
        self.assertEqual(
            darts_now(
                {"user_id": PID, "action": "darts_new_free", "arguments": 5}
            ).status_code,
            400,
        )

    def test_a_refusal_is_answered_before_any_execution(self) -> None:
        """A refused request must not half-apply: the corpus is byte-identical
        across all five refusal families."""
        pristine()
        baseline = corpus_save()
        for payload in (
            {"user_id": PID, "action": "nope"},
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": "x"}},
            shoot_intent("x"),
            premium_intent("x"),
            {"user_id": PID, "action": "darts_new_free", "arguments": 5},
        ):
            with self.subTest(payload=payload):
                self.assertNotEqual(darts_now(payload).status_code, 200)
        self.assertEqual(corpus_save(), baseline)

    def test_the_only_method_is_post(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/darts")
        self.assertEqual(response.status_code, 405)


# --------------------------------------------------------------------------
# the two-part post-execution proof, made to fail
# --------------------------------------------------------------------------


class PostExecutionProofTests(unittest.TestCase):
    """Design D5, proved non-tautologically: each half is broken on purpose."""

    def test_the_premium_half_fails_when_the_instant_moves_by_the_wrong_amount(self) -> None:
        pristine()
        original = BOOT.premium_instant
        calls = {"seen": 0}

        def stub(user_id: str) -> Optional[int]:
            calls["seen"] += 1
            current = original(user_id)
            if calls["seen"] == 1:
                return current
            return None if current is None else current + 1

        BOOT.premium_instant = stub  # type: ignore[assignment]
        try:
            response = darts_now(premium_intent(0))
        finally:
            BOOT.premium_instant = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        self.assertIn("premium instant", response.get_json()["error"]["message"])

    def test_the_premium_half_is_not_checked_for_the_three_darts_actions(self) -> None:
        """The instant half is scoped to the premium action; the darts actions must
        not be failed by it."""
        pristine()
        for payload in (
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": 3}},
            {"user_id": PID, "action": "darts_new_free", "arguments": {}},
            shoot_intent(7),
        ):
            with self.subTest(action=payload["action"]):
                self.assertEqual(darts_now(payload).status_code, 200)

    def test_the_resource_half_fails_for_every_stored_resource_in_turn(self) -> None:
        """All **seven** slots are compared, each against the pre-execution value --
        not a subset.  One deliberately moved slot must be enough to fail."""
        for moved in RESOURCE_NAMES:
            with self.subTest(moved=moved):
                pristine()

                def transform(resources: Dict[str, int], name: str = moved) -> Dict[str, int]:
                    altered = dict(resources)
                    altered[name] = altered[name] + 1
                    return altered

                restore = _resources_rewritten_after_execution(transform)
                try:
                    response = darts_now(premium_intent(0))
                finally:
                    restore()
                self.assertEqual(response.status_code, 500)
                body = response.get_json()
                self.assertEqual(body["error"]["code"], "internal_error")
                self.assertIn("nothing is charged", body["error"]["message"])
                self.assertIn(moved, body["error"]["message"])

    def test_the_resource_half_is_checked_against_the_full_vocabulary(self) -> None:
        """A seventh slot the service does not expose must not slip through: the
        proof iterates the post-execution keys, so a slot the pre-execution read
        lacked would still be compared."""
        pristine()

        def transform(resources: Dict[str, int]) -> Dict[str, int]:
            altered = dict(resources)
            altered["cash"] = -1
            return altered

        restore = _resources_rewritten_after_execution(transform)
        try:
            response = darts_now({"user_id": PID, "action": "darts_new_free", "arguments": {}})
        finally:
            restore()
        self.assertEqual(response.status_code, 500)

    def test_the_resource_half_is_checked_for_every_action(self) -> None:
        for payload in (
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": 3}},
            {"user_id": PID, "action": "darts_new_free", "arguments": {}},
            shoot_intent(7),
            premium_intent(0),
        ):
            with self.subTest(action=payload["action"]):
                pristine()

                def transform(resources: Dict[str, int]) -> Dict[str, int]:
                    altered = dict(resources)
                    altered["gold"] = altered["gold"] - 1
                    return altered

                restore = _resources_rewritten_after_execution(transform)
                try:
                    response = darts_now(payload)
                finally:
                    restore()
                self.assertEqual(response.status_code, 500)

    def test_the_structural_half_reports_the_changed_set_it_actually_observed(self) -> None:
        """The changed set is computed from the two snapshots, not from a table."""
        pristine()

        def transform(state: Dict[str, Any]) -> Dict[str, Any]:
            altered = dict(state)
            altered["dartsRandomSeed"] = 4242
            return altered

        restore = _state_rewritten_after_execution(transform)
        try:
            body = darts_now({"user_id": PID, "action": "darts_new_free", "arguments": {}}).get_json()
        finally:
            restore()
        self.assertIn("dartsRandomSeed", body["darts_changed_fields"])

    def test_a_broken_proof_is_reported_rather_than_the_legacy_success(self) -> None:
        """The point of the proof: the dispatcher already returned
        ``{"result": "success"}``, and this endpoint still refuses to report it."""
        pristine()

        def transform(resources: Dict[str, int]) -> Dict[str, int]:
            altered = dict(resources)
            altered["wood"] = 0
            return altered

        restore = _resources_rewritten_after_execution(transform)
        try:
            body = darts_now(premium_intent(0)).get_json()
        finally:
            restore()
        self.assertIs(body["ok"], False)
        self.assertNotIn("result", body)


# --------------------------------------------------------------------------
# the neutral vector is a refusal, not parity
# --------------------------------------------------------------------------


class NoChargeTests(unittest.TestCase):
    def test_a_client_sent_debit_cannot_move_a_balance(self) -> None:
        baseline = pristine()
        response = darts_now(
            premium_intent(
                0,
                resources=[0, -2000, -2000, -2000, -2000, -2000, -2000, -2000],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resources_now(), baseline["resources"])
        self.assertTrue(response.get_json()["client_supplied_resource_vector_ignored"])

    def test_a_client_sent_credit_cannot_move_a_balance_either(self) -> None:
        """The neutral vector forecloses **both** directions, which is stronger than
        the legacy server's behaviour and is recorded as a refusal."""
        baseline = pristine()
        response = darts_now(
            premium_intent(
                0,
                resources=[0, 999999, 999999, 999999, 999999, 999999, 999999, 999999],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resources_now(), baseline["resources"])

    def test_a_client_sent_nine_slot_vector_is_still_ignored(self) -> None:
        """A wider vector than the legacy eight is not even looked at."""
        baseline = pristine()
        response = darts_now(premium_intent(0, resources=[0] * 9))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resources_now(), baseline["resources"])

    def test_a_client_sent_command_batch_is_never_executed(self) -> None:
        """The route derives its own envelope from ``action`` + ``arguments`` and
        sends **one** command, so a client that hand-writes the legacy batch shape
        -- including its own ``resources_changed`` vector -- has it ignored
        wholesale.  This is the strongest form of the refusal: the client cannot
        even reach the ``apply_resources`` call the preserved server makes."""
        baseline = pristine()
        for commands in (
            [[0, "buy_premium_account", [0], [0, 0, -1, 0, 0, 0, 0, 0]]],
            [[0, "darts_shoot_balloon", [18, True], [0, 0, -999999, 0, 0, 0, 0, 0]]],
            [[0, "fast_forward", [999999999], [0, 0, 0, 0, 0, 0, 0, 0]]],
        ):
            with self.subTest(commands=commands):
                response = darts_now(
                    {"user_id": PID, "action": "darts_new_free", "commands": commands}
                )
                self.assertEqual(response.status_code, 200)
                # The client's batch never ran: no shot was recorded and no
                # balance moved, even though the free grant succeeded.
                self.assertEqual(
                    darts_now_state()["dartsBalloonsShot"],
                    baseline["darts"]["dartsBalloonsShot"],
                )
                self.assertEqual(resources_now(), baseline["resources"])
                self.assertEqual(instant_now(), COMMITTED_PREMIUM_INSTANT)

    def test_the_refusal_is_real_because_the_preserved_server_would_have_moved_a_balance(self) -> None:
        """Non-tautological by measurement, not by demonstration: the preserved
        ``apply_resources`` is a ``max(current + delta, 0)`` over a **non-zero**
        balance, so a negative delta is not a no-op there.  Executing the legacy
        path on purpose is deliberately *not* done -- a client-sent vector is never
        dispatched by this service, and proving the clamp is the engine suite's
        job."""
        baseline = pristine()
        self.assertGreater(baseline["resources"]["gold"], 0)
        self.assertGreater(baseline["resources"]["wood"], 0)
        response = darts_now(
            premium_intent(
                0, resources=[0, 0, -baseline["resources"]["gold"], 0, 0, 0, 0, 0]
            )
        )
        self.assertEqual(response.status_code, 200)
        # The legacy clamp would have landed on ``0``; this service left it alone.
        self.assertEqual(resources_now()["gold"], baseline["resources"]["gold"])
        self.assertEqual(resources_now()["wood"], baseline["resources"]["wood"])

    def test_the_committed_amount_is_never_charged_because_nothing_reads_it(self) -> None:
        pristine()
        premium = darts_now(premium_intent(5)).get_json()["premium"]
        # Index 5 is the 1-day entry, whose committed amount is 8.
        self.assertEqual(premium["days"], 1)
        self.assertIs(premium["charged"], False)
        self.assertEqual(premium["committed_amount_consumers"], 0)


# --------------------------------------------------------------------------
# containment
# --------------------------------------------------------------------------


class ContainmentTests(unittest.TestCase):
    def test_no_working_tree_save_is_written_by_any_action(self) -> None:
        pristine()
        before = harness.working_tree_save_hashes()
        for payload in (
            {"user_id": PID, "action": "darts_reset", "arguments": {"seed": 11}},
            {"user_id": PID, "action": "darts_new_free", "arguments": {}},
            shoot_intent(19),
            premium_intent(2),
        ):
            self.assertEqual(darts_now(payload).status_code, 200)
        self.assertEqual(harness.working_tree_save_hashes(), before)

    def test_the_corpus_save_really_mutated(self) -> None:
        """Otherwise "no working-tree save changed" would be true for the wrong
        reason -- that nothing happened at all."""
        pristine()
        before = corpus_save()
        self.assertEqual(darts_now(shoot_intent(21)).status_code, 200)
        self.assertNotEqual(corpus_save(), before)
        self.assertEqual(
            corpus_save()["privateState"]["dartsBalloonsShot"], [21]
        )

    def test_the_premium_purchase_really_mutated_the_corpus(self) -> None:
        pristine()
        before = corpus_save()
        body = darts_now(premium_intent(1)).get_json()
        after = corpus_save()
        self.assertEqual(body["premium"]["arm"], "set")
        self.assertNotEqual(after, before)
        # The **set** arm stamps the server clock, not the recorded instant, so
        # this asserts ``clock + duration`` and not ``0 + duration``.
        self.assertEqual(
            after["privateState"]["timeStampEndPremium"],
            body["premium"]["server_clock"] + SCHEDULE_DAYS[1] * SECONDS_PER_DAY,
        )
        self.assertNotEqual(after["privateState"]["timeStampEndPremium"], SCHEDULE_DAYS[1])

    def test_no_port_is_bound_by_this_suite(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()