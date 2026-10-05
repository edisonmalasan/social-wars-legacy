#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/reward`` endpoint tests (OpenSpec ``godot-rewards``).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so this suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories stay byte-identical across
every reward execution.

**What this route delivers, and what the refusal is for.**  One call carries
exactly one legacy command through the **unchanged** dispatcher --
``weekly_reward`` or ``win_daily_bonus`` -- and moves exactly two numbers: one
reward **cursor** and one **stamped instant**.  It grants nothing, selects no
schedule entry, and prices nothing, because none is derivable: the grant arms of
both branches take their only input from a client, and six independent searches
across all eleven legacy modules find no letter-to-resource mapping.

**The four-part grant proof is exercised as ONE containment check.**  The route
compares the changed leaves of the **whole** recorded document against an
allowlist of exactly two paths.  This suite drives that proof to failure at each
of the four landing places a grant could use -- a map row, the bought-units
list, the storage, and each stored resource slot -- so "nothing is granted" is a
verified property rather than an absence of evidence.

**Every refusal is asserted with whole-document byte identity, including the
instant.**  All eleven request-reachable reasons resolve before the cursor write
and before the wall-clock stamp (design D9), so a refused request provably leaves
every recorded byte unchanged.  That is the whole reason the ordering is a
requirement and not an implementation detail: a refusal that ran far enough to
stamp would leave a difference in a document that is supposed to be unchanged.

**How the post-execution proof cases are driven.**  Each stub rewrites only the
read that happens **after** ``execute_commands`` returned, detected by wrapping
the boot's own ``execute_commands`` rather than by counting accessor calls --
``LegacyBoot.resources`` itself calls ``save_document`` internally, so a
call-counting stub would rewrite the *pre*-execution read and silently test
something else.  The transform receives a **deep copy**, so a proof-failure test
never corrupts the recorded corpus file it is asserted against elsewhere.

Covered:

* **both successful cursor transitions** -- the recorded weekly modulo and the
  recorded daily wrap, with the persisted corpus matching the response, the
  stamped instant reported as volatile rather than by value, and **every one of
  the eight stored resources unchanged**.
* **all eleven request-reachable refusals** -- each with its named code, an
  **empty** payload, and the whole document **byte-identical**.
* **the four-part grant proof** -- each landing place, each resource slot, a
  missing slot, an unaddressed cursor that moved, a container that appeared, and
  an unstamped instant, each failing closed with ``internal_error``.
* **the cursor proof** -- a cursor that moved by the wrong amount, that did not
  move, or that vanished.
* **the snapshot** -- a deep copy, so a mutated snapshot cannot alias the live
  document the after-state is read from.
* **an unknown user**, answered 404 before any of the reward machinery runs.

Deliberately **not** claimed: that a pixel-parity oracle exists, that a windowed
capture was taken, or that the exercised cursor values match any committed
client's behaviour.  Nothing is rendered.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import re
import textwrap
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import compat_test_harness as harness

import compat_legacy
import compat_service
import rewards_envelope as R

SERVICE = Path(__file__).resolve().parents[1] / "compat_service.py"
ENVELOPE = Path(__file__).resolve().parents[1] / "rewards_envelope.py"

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

#: The eight stored resource slots the proof compares.  Seven come from
#: ``LegacyBoot.resources``; ``energy`` does not, and its absence there is the
#: reason the eighth slot has to be read off the document.
RESOURCE_NAMES = (
    "cash", "gold", "mana", "oil", "steel", "wood", "xp", "energy",
)
ACCESSOR_RESOURCE_NAMES = tuple(
    name for name in RESOURCE_NAMES if name != "energy"
)
DOCUMENT_ONLY_RESOURCE = "energy"

#: The recorded cursors the committed fresh-player corpus carries, read rather
#: than assumed -- ``weeklyRewardIndex`` 0 and ``bonusNextId`` 0.
RECORDED_WEEKLY_CURSOR = 0
RECORDED_DAILY_CURSOR = 0

#: The committed corpus's own four private-state values, so every seeded reset
#: returns the corpus to the state the fixture captured against.
COMMITTED_PRIVATE: Dict[str, Any] = {}

UNKNOWN_USER = "does-not-exist-0000000000000000"


# ------------------------------------------------------------- corpus helpers --
def save_path() -> Path:
    return CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]


def write_corpus(save: Dict[str, Any]) -> None:
    with open(save_path(), "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def save_now() -> Dict[str, Any]:
    return BOOT.save_document(PID)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    """The **persisted** corpus document, which the legacy batch wrote."""
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def private_now() -> Dict[str, Any]:
    return save_now()[R.PRIVATE_STATE_KEY]


def private_maybe() -> Any:
    """The private-state object, or ``None`` when the save carries none.

    Only the one refusal test that deletes it may call this; every accessor above
    indexes the key directly, which is correct for the committed corpus and is
    exactly the crash the ``absent_reward_cursor`` refusal exists to prevent.
    """
    return save_now().get(R.PRIVATE_STATE_KEY)


def cursor_now(action: str) -> Any:
    return private_now()[R.ACTION_CURSOR_KEY[action]]


def stamp_now(action: str) -> Any:
    return private_now()[R.ACTION_STAMP_KEY[action]]


def resources_now() -> Dict[str, Any]:
    """All **eight** stored slots, the same set the route's proof compares.

    A save with no private state reports ``{}`` rather than raising, mirroring
    ``compat_service._reward_snapshot``'s own guard: ``LegacyBoot.resources``
    indexes ``save["privateState"]["mana"]`` directly, so a caller that wanted to
    assert the refusal for such a save would itself crash first.  ``{}`` is the
    honest reading -- there are no stored slots to report.
    """
    private = save_now().get(R.PRIVATE_STATE_KEY)
    if not isinstance(private, dict):
        return {}
    slots: Dict[str, Any] = dict(BOOT.resources(PID))  # type: ignore[union-attr]
    if DOCUMENT_ONLY_RESOURCE in private:
        slots[DOCUMENT_ONLY_RESOURCE] = private[DOCUMENT_ONLY_RESOURCE]
    return slots


def snapshot() -> Dict[str, Any]:
    return {
        "private": copy.deepcopy(private_maybe()),
        "resources": resources_now(),
        "bytes": save_path().read_bytes(),
    }


#: The four private-state fields this suite seeds, mapped from the caller's
#: short name to the committed key.  ``seeded`` writes **all four** on every call
#: unless one is passed :data:`_ABSENT`, so no test can leak a removed key into
#: the next one -- which is a real hazard here, because an absent cursor makes
#: every later accessor refuse.
SEEDED_KEYS = {
    "weekly": R.WEEKLY_CURSOR_KEY,
    "weekly_stamp": R.WEEKLY_STAMP_KEY,
    "daily": R.DAILY_CURSOR_KEY,
    "daily_stamp": R.DAILY_STAMP_KEY,
}


def seeded(**overrides: Any) -> Dict[str, Any]:
    """Reset the disposable corpus to a complete, caller-chosen recorded state.

    Written in memory **and** through the corpus file, because the legacy
    branches mutate ``privateState`` in place and the byte-identity assertions
    compare the persisted document.  A field passed as :data:`_ABSENT` is
    **removed** rather than set, which is the only way to exercise the
    ``absent_reward_cursor`` and ``absent_reward_instant`` refusals; every other
    field is reset to its committed value, so the four refusals that remove state
    cannot make a later test fail for the wrong reason.  Never a committed save.
    """
    save = save_now()
    private = save[R.PRIVATE_STATE_KEY]
    for name, key in SEEDED_KEYS.items():
        if name in overrides:
            value = overrides.pop(name)
            if value is _ABSENT:
                private.pop(key, None)
            else:
                private[key] = value
        else:
            private[key] = COMMITTED_PRIVATE[key]
    if overrides:
        raise AssertionError("unknown seeded fields: %s" % sorted(overrides))
    write_corpus(save)
    return snapshot()


class _Absent:
    """Sentinel: remove the field rather than set it to a value."""


_ABSENT = _Absent()


class SeededTestCase(unittest.TestCase):
    """Every test starts from the committed recorded state.

    ``unittest`` orders the classes of a module **alphabetically**, and three of
    the classes below deliberately destroy recorded state to reach a refusal or a
    proof failure -- an unreadable cursor, a removed private-state object, a
    removed eighth resource slot.  Without this ``setUp`` the first class to run
    alphabetically (:class:`RefusalTests`) hands its wreckage to
    :class:`SuccessfulCursorTests`, which then reports a refusal where a success
    belongs.  That is a real hazard on this route specifically: an unreadable
    cursor is refused, so a leaked ``weekly="0"`` fails every later success case
    for the wrong reason.  ``seeded()`` resets all four fields unconditionally
    (see its docstring), so the leak cannot happen in either direction.
    """

    def setUp(self) -> None:
        seeded()


def write_private_verbatim(**fields: Any) -> None:
    """Write an **unreadable** private-state shape straight to the corpus file.

    Needed for the shapes ``json.dump`` will not produce for a dict -- ``None``,
    a list, a string, a number -- because a save document has to hold them to be
    exercised at all.  ``private=None`` writes a document with no private state
    at all.
    """
    with open(save_path(), "w", encoding="utf-8", newline="\n") as stream:
        document = save_now()
        if "private" in fields:
            if fields["private"] is None:
                document.pop(R.PRIVATE_STATE_KEY, None)
            else:
                document[R.PRIVATE_STATE_KEY] = fields["private"]
        else:
            for key, value in fields.items():
                document[R.PRIVATE_STATE_KEY][key] = value
        json.dump(document, stream, indent=4)
        stream.write("\n")


# ------------------------------------------------------------------ transport --
def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE
    ORIGINAL_CWD = os.getcwd()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    CLIENT = app.test_client()
    COMMITTED_PRIVATE.update(
        harness.load_seed()[R.PRIVATE_STATE_KEY]  # type: ignore[arg-type]
    )
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a reward execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def reward_now(payload: Any) -> Any:
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/reward", json=payload)  # type: ignore[union-attr]


def intent(action: str = R.ACTION_WEEKLY, **extra: Any) -> Dict[str, Any]:
    """The whole contract: a save identity, an action, and nothing else.

    There is deliberately **no** cursor, item, cell, player, next-id, amount or
    price parameter.  A caller that wants one passes it through ``extra``, which
    is exactly how the refusal tests build their payloads.
    """
    payload: Dict[str, Any] = {"user_id": PID, "action": action}
    payload.update(extra)
    return payload


class Result:
    """A captured response plus the app that produced it."""

    def __init__(self, app: Any, response: Any) -> None:
        self.app = app
        self.response = response

    @property
    def status_code(self) -> int:
        return int(self.response.status_code)

    def get_json(self) -> Any:
        return self.response.get_json()


# --------------------------------------------------- the post-execution stubs --
class _AfterExecution:
    """Rewrite one accessor read, and only the reads **after** execution.

    The trigger is ``execute_commands`` returning rather than an accessor call
    count: ``_reward_snapshot`` calls ``save_document`` and then ``resources``,
    and ``resources`` itself calls ``save_document`` internally, so a
    call-counting stub rewrites the pre-execution cursor read instead of the
    post-execution one and would pass for the wrong reason.
    """

    def __init__(self, attribute: str, transform: Callable[[Any], Any]) -> None:
        self.attribute = attribute
        self.transform = transform
        self.executed = False
        self._original = getattr(BOOT, attribute)  # type: ignore[union-attr]
        self._original_execute = BOOT.execute_commands  # type: ignore[union-attr]

    def _wrapper(self, user_id: str) -> Any:
        value = self._original(user_id)
        if not self.executed:
            return value
        # Deep copy, so a proof-failure test never corrupts the recorded corpus
        # file it is asserted against elsewhere.
        return self.transform(copy.deepcopy(value))

    def _execute(self, user_id: str, envelope: Dict[str, Any]) -> None:
        self._original_execute(user_id, envelope)
        self.executed = True

    def __enter__(self) -> "_AfterExecution":
        setattr(BOOT, self.attribute, self._wrapper)  # type: ignore[attr-defined]
        BOOT.execute_commands = self._execute  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: Any) -> None:
        setattr(BOOT, self.attribute, self._original)  # type: ignore[attr-defined]
        BOOT.execute_commands = self._original_execute  # type: ignore[assignment]


def post_with(
    attribute: str,
    transform: Callable[[Any], Any],
    payload: Dict[str, Any],
) -> Result:
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    with _AfterExecution(attribute, transform):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/reward", json=payload))


def slot_moved(name: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def transform(slots: Dict[str, Any]) -> Dict[str, Any]:
        slots[name] = slots.get(name, 0) + 1000
        return slots

    return transform


def slot_absent(name: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def transform(slots: Dict[str, Any]) -> Dict[str, Any]:
        slots.pop(name, None)
        return slots

    return transform


def document_energy(value: Any) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def transform(document: Dict[str, Any]) -> Dict[str, Any]:
        private = document[R.PRIVATE_STATE_KEY]
        if value is _ABSENT:
            private.pop(DOCUMENT_ONLY_RESOURCE, None)
        else:
            private[DOCUMENT_ONLY_RESOURCE] = value
        return document

    return transform


def private_mutate(mutate: Callable[[Dict[str, Any]], None]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def transform(document: Dict[str, Any]) -> Dict[str, Any]:
        mutate(document[R.PRIVATE_STATE_KEY])
        return document

    return transform


# ----------------------------------------------------------- corpus integrity --
class CommittedCorpusTests(SeededTestCase):
    """Measure the committed corpus instead of assuming what it contains."""

    def test_the_committed_seed_records_both_cursors_and_both_instants(self) -> None:
        seed_private = harness.load_seed()[R.PRIVATE_STATE_KEY]  # type: ignore[index]
        for key in R.CURSORS + R.INSTANTS:
            with self.subTest(key=key):
                self.assertIn(key, seed_private)
                self.assertIsInstance(seed_private[key], int)
        self.assertEqual(seed_private[R.WEEKLY_CURSOR_KEY], RECORDED_WEEKLY_CURSOR)
        self.assertEqual(seed_private[R.DAILY_CURSOR_KEY], RECORDED_DAILY_CURSOR)
        self.assertEqual(seed_private[R.WEEKLY_STAMP_KEY], 0)
        self.assertEqual(seed_private[R.DAILY_STAMP_KEY], 0)

    def test_the_committed_seed_records_every_one_of_the_eight_slots(self) -> None:
        slots = seeded()["resources"]
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertIn(name, slots)
        self.assertEqual(len(slots), len(RESOURCE_NAMES))
        # And the seventh/eighth split is real: `energy` is a stored resource that
        # `LegacyBoot.resources` does not expose, which is precisely why the proof
        # reads it off the document instead of trusting the accessor.
        self.assertNotIn(DOCUMENT_ONLY_RESOURCE, BOOT.resources(PID))  # type: ignore[union-attr]
        self.assertEqual(
            sorted(BOOT.resources(PID)), sorted(ACCESSOR_RESOURCE_NAMES)  # type: ignore[union-attr]
        )

    def test_the_committed_schedules_are_read_from_the_served_configuration(self) -> None:
        globals_block = BOOT.config().get(R.GLOBALS_KEY)  # type: ignore[union-attr]
        self.assertIsInstance(globals_block, dict)
        for action in R.ACTIONS:
            with self.subTest(action=action):
                key = R.ACTION_SCHEDULE_KEY[action]
                self.assertIn(key, globals_block)
                self.assertIsInstance(globals_block[key], list)
        weekly = globals_block[R.WEEKLY_SCHEDULE_KEY]
        daily = globals_block[R.DAILY_SCHEDULE_KEY]
        # Both cardinalities are DERIVED here rather than transcribed, so a
        # mistranscribed constant cannot make this pass.
        self.assertEqual(R.weekly_bound(weekly), 5)
        self.assertEqual(R.schedule_cardinality(weekly), 3)
        self.assertEqual(R.schedule_cardinality(daily), 5)
        self.assertEqual(R.daily_bound(), 5)

    def test_the_committed_corpus_save_is_never_written(self) -> None:
        seed_path = harness.SEED_SAVE
        before = seed_path.read_bytes()
        seeded()
        self.assertEqual(reward_now(intent(R.ACTION_WEEKLY)).status_code, 200)
        self.assertEqual(
            seed_path.read_bytes(), before,
            "the committed corpus save is byte-identical after a reward action",
        )


# ------------------------------------------------------- the successful path --
class SuccessfulCursorTests(SeededTestCase):
    """Both actions through the real dispatcher, with the four-part proof."""

    def test_the_weekly_cursor_advances_by_the_recorded_modulo(self) -> None:
        for before in (0, 1, 2, 3, 4):
            with self.subTest(before=before):
                seeded(weekly=before)
                response = reward_now(intent(R.ACTION_WEEKLY))
                self.assertEqual(response.status_code, 200, response.get_json())
                body = response.get_json()
                self.assertTrue(body["ok"])
                self.assertEqual(body["protocol"], "compat-v0")
                self.assertEqual(body["result"], "success")
                self.assertEqual(body["reward"]["action"], R.ACTION_WEEKLY)
                self.assertEqual(body["reward"]["command"], R.WEEKLY_COMMAND)
                self.assertEqual(body["reward"]["cursor"]["key"], R.WEEKLY_CURSOR_KEY)
                self.assertEqual(body["reward"]["cursor"]["before"], before)
                self.assertEqual(body["reward"]["cursor"]["after"], (before + 1) % 5)
                self.assertEqual(
                    body["reward"]["cursor"]["after"],
                    cursor_now(R.ACTION_WEEKLY),
                    "the persisted value is the derived successor",
                )
                self.assertEqual(
                    body["changed"],
                    sorted([
                        "/%s/%s" % (R.PRIVATE_STATE_KEY, R.WEEKLY_CURSOR_KEY),
                        "/%s/%s" % (R.PRIVATE_STATE_KEY, R.WEEKLY_STAMP_KEY),
                    ]),
                    "exactly the two paths the action may change, and nothing else",
                )

    def test_the_daily_cursor_advances_and_wraps_at_the_preserved_literal(self) -> None:
        for before, expected in ((0, 1), (1, 2), (3, 4), (4, 5), (5, 1)):
            with self.subTest(before=before, expected=expected):
                seeded(daily=before)
                response = reward_now(intent(R.ACTION_DAILY))
                self.assertEqual(response.status_code, 200, response.get_json())
                body = response.get_json()
                self.assertEqual(body["reward"]["command"], R.DAILY_COMMAND)
                self.assertEqual(body["reward"]["cursor"]["key"], R.DAILY_CURSOR_KEY)
                self.assertEqual(body["reward"]["cursor"]["before"], before)
                self.assertEqual(body["reward"]["cursor"]["after"], expected)
                self.assertEqual(
                    cursor_now(R.ACTION_DAILY), expected,
                    "the recorded wrap onto the first position is reproduced",
                )

    def test_the_weekly_bound_is_five_and_the_schedule_holds_three_entries(self) -> None:
        body = reward_now(intent(R.ACTION_WEEKLY)).get_json()
        bounds = body["reward"]["bounds"]
        self.assertEqual(bounds["weekly"]["bound"], 5)
        self.assertEqual(bounds["weekly"]["cardinality"], 3)
        self.assertEqual(bounds["weekly"]["exceeds_cardinality_by"], 2)
        self.assertEqual(bounds["weekly"]["floor"], R.WEEKLY_BOUND_FLOOR)
        self.assertEqual(body["reward"]["bound"], 5)
        self.assertEqual(body["reward"]["bound_source"], R.WEEKLY_BOUND_SOURCE)

    def test_the_daily_bound_is_the_literal_and_carries_the_rejected_derivation(self) -> None:
        body = reward_now(intent(R.ACTION_DAILY)).get_json()
        bounds = body["reward"]["bounds"]
        self.assertEqual(bounds["daily"]["bound"], R.DAILY_BOUND_LITERAL)
        self.assertEqual(bounds["daily"]["wrap_target"], R.DAILY_WRAP_TARGET)
        self.assertEqual(bounds["daily"]["cardinality"], 5)
        self.assertEqual(
            bounds["daily"]["rejected_alternative"], R.DAILY_BOUND_REJECTED_DERIVATION
        )
        self.assertEqual(
            body["reward"]["bound_rejected_alternative"],
            R.DAILY_BOUND_REJECTED_DERIVATION,
            "the weekly action reports no rejected alternative; the daily one does",
        )

    def test_the_reachability_report_names_the_unaddressable_positions(self) -> None:
        weekly = reward_now(intent(R.ACTION_WEEKLY)).get_json()["reward"]["reachability"]
        self.assertEqual(weekly[R.ACTION_WEEKLY]["selection_performed"], False)
        self.assertEqual(weekly[R.ACTION_WEEKLY]["index_base"], R.SCHEDULE_INDEX_BASE)
        self.assertEqual(weekly[R.ACTION_WEEKLY]["bound"], 5)
        self.assertEqual(weekly[R.ACTION_WEEKLY]["cardinality"], 3)
        self.assertEqual(
            weekly[R.ACTION_WEEKLY]["reachable_not_answerable"], [3, 4],
            "two of five weekly positions name no schedule entry",
        )
        daily = reward_now(intent(R.ACTION_DAILY)).get_json()["reward"]["reachability"]
        self.assertEqual(daily[R.ACTION_DAILY]["reachable_not_answerable"], [5])
        self.assertEqual(daily[R.ACTION_DAILY]["selection_performed"], False)
        # Both schedules are reported for EVERY action, because the response
        # carries both reachability reports regardless of which cursor moved.
        self.assertEqual(
            sorted(weekly), sorted(R.ACTIONS),
            "both cursors are reported even when only one moved",
        )

    def test_the_instant_is_reported_as_volatile_and_never_by_value(self) -> None:
        before = seeded()
        response = reward_now(intent(R.ACTION_WEEKLY))
        body = response.get_json()
        instant = body["reward"]["instant"]
        self.assertEqual(instant["key"], R.WEEKLY_STAMP_KEY)
        self.assertEqual(instant["stamped"], True)
        self.assertEqual(instant["volatile"], True)
        self.assertEqual(instant["value_before"], before["private"][R.WEEKLY_STAMP_KEY])
        self.assertEqual(instant["note"], R.NO_ELIGIBILITY)
        self.assertNotIn(
            "value_after", instant,
            "a wall clock is not derivable, so no executed value is reported",
        )
        self.assertIn(
            "/%s/%s" % (R.PRIVATE_STATE_KEY, R.WEEKLY_STAMP_KEY),
            body["reward"]["volatile_fields"],
        )
        # It really was written: the recorded value moved forward.
        self.assertGreater(stamp_now(R.ACTION_WEEKLY), before["private"][R.WEEKLY_STAMP_KEY])

    def test_every_one_of_the_eight_stored_resources_is_unchanged(self) -> None:
        for action in R.ACTIONS:
            with self.subTest(action=action):
                before = seeded()
                body = reward_now(intent(action)).get_json()
                self.assertEqual(len(body["resources"]), len(RESOURCE_NAMES))
                self.assertEqual(
                    sorted(body["resources"].keys()),
                    sorted(RESOURCE_NAMES),
                    "the response reports all eight slots, never a subset",
                )
                for name in RESOURCE_NAMES:
                    with self.subTest(resource=name):
                        self.assertEqual(body["resources"][name], before["resources"][name])
                self.assertEqual(resources_now(), before["resources"])

    def test_no_price_is_charged_so_the_derived_vector_is_the_neutral_one(self) -> None:
        for action in R.ACTIONS:
            with self.subTest(action=action):
                before = seeded()
                body = reward_now(intent(action)).get_json()
                self.assertEqual(body["reward"]["grant"]["grants_nothing"], True)
                self.assertEqual(
                    {name: body["resources"][name] - before["resources"][name]
                     for name in RESOURCE_NAMES},
                    {name: 0 for name in RESOURCE_NAMES},
                )
                self.assertEqual(
                    R.neutral_vector(), [0] * R.RESOURCE_VECTOR_SLOTS,
                    "the derived vector is the neutral all-zero one",
                )

    def test_the_two_derived_argument_lists_are_shaped_by_the_arms(self) -> None:
        weekly = reward_now(intent(R.ACTION_WEEKLY)).get_json()["reward"]
        self.assertEqual(weekly["derived_args"], [])
        self.assertEqual(
            weekly["derived_args"],
            [],
            "an empty argument list is what selects the non-granting short arm",
        )
        seeded(daily=2)
        daily = reward_now(intent(R.ACTION_DAILY)).get_json()["reward"]
        self.assertEqual(
            daily["derived_args"], [R.DERIVED_DAILY_ITEM, 2],
            "the item is derived at zero and the next id is the RECORDED cursor",
        )

    def test_the_persisted_corpus_matches_the_response(self) -> None:
        seeded(weekly=2)
        body = reward_now(intent(R.ACTION_WEEKLY)).get_json()
        persisted = corpus_save()[R.PRIVATE_STATE_KEY]
        self.assertEqual(persisted[R.WEEKLY_CURSOR_KEY], body["reward"]["cursor"]["after"])
        self.assertEqual(persisted[R.WEEKLY_STAMP_KEY], stamp_now(R.ACTION_WEEKLY))
        # The daily cursor was not addressed, so it is byte-identical.
        self.assertEqual(persisted[R.DAILY_CURSOR_KEY], RECORDED_DAILY_CURSOR)

    def test_the_unaddressed_cursor_and_instant_are_byte_identical(self) -> None:
        before = seeded(weekly=1, daily=3, weekly_stamp=111, daily_stamp=222)
        reward_now(intent(R.ACTION_WEEKLY))
        after = private_now()
        self.assertEqual(after[R.DAILY_CURSOR_KEY], before["private"][R.DAILY_CURSOR_KEY])
        self.assertEqual(after[R.DAILY_STAMP_KEY], before["private"][R.DAILY_STAMP_KEY])

    def test_the_response_carries_the_whole_derived_contract(self) -> None:
        body = reward_now(intent(R.ACTION_WEEKLY)).get_json()
        self.assertEqual(body["result"], "success")
        self.assertEqual(
            body["reward"]["grant"]["allowed_leaf_paths"],
            R.allowed_leaf_paths(R.ACTION_WEEKLY),
            "the response names the same two paths the proof compares",
        )
        self.assertEqual(body["reward"]["grant"]["note"], R.NO_GRANT)
        self.assertEqual(
            [row["id"] for row in body["reward"]["divergences"]],
            [row["id"] for row in R.DIVERGENCES],
        )
        for row in body["reward"]["divergences"]:
            with self.subTest(divergence=row["id"]):
                self.assertEqual(row["reproduced"], False)
                self.assertTrue(row["where"])
                self.assertTrue(row["consequence"])
        self.assertEqual(
            body["reward"]["reachability"][R.ACTION_WEEKLY]["selection_performed"],
            False,
        )


# ------------------------------------------------------------- every refusal --
class RefusalTests(SeededTestCase):
    """Each named code, an empty payload, and a byte-identical corpus.

    ``assertRefused`` compares the **whole persisted corpus file**, so the
    stamped instant is included in the byte identity: every refusal resolves
    before the stamp (design D9), and this is what holds the route to it.
    """

    def assertRefused(
        self,
        payload: Any,
        code: str,
        status: int,
        before: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if before is None:
            before = snapshot()
        response = reward_now(payload)
        self.assertEqual(response.status_code, status, response.get_json())
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(
            sorted(body.keys()), ["error", "ok", "protocol"],
            "a refusal carries an EMPTY payload: no state field at all",
        )
        self.assertEqual(sorted(body["error"].keys()), ["code", "message"])
        after = snapshot()
        self.assertEqual(
            after["private"], before["private"],
            "no private-state value moved, the stamped instant included",
        )
        self.assertEqual(after["resources"], before["resources"])
        self.assertEqual(
            after["bytes"], before["bytes"],
            "a refusal leaves the whole recorded document byte-identical",
        )
        return body

    # --- the action vocabulary ------------------------------------------------
    def test_the_action_vocabulary_is_closed(self) -> None:
        for action in ("collect", "Weekly", "weekly ", "", None, 1, True, ["weekly"]):
            with self.subTest(action=action):
                self.assertRefused(
                    intent(action), "unknown_reward_action", 409
                )

    def test_a_missing_action_is_named(self) -> None:
        before = seeded()
        payload = {"user_id": PID}
        body = self.assertRefused(payload, "unknown_reward_action", 409, before)
        self.assertIn("action is required", body["error"]["message"])

    # --- the seven grant-shaped classes --------------------------------------
    def test_every_grant_shaped_key_is_refused_by_its_own_name(self) -> None:
        for key, reason in R.CLIENT_KEY_REFUSALS:
            with self.subTest(key=key):
                for action in R.ACTIONS:
                    with self.subTest(action=action):
                        seeded()
                        self.assertRefused(intent(action, **{key: 1}), reason, 409)

    def test_both_cell_coordinates_resolve_to_one_cell_class(self) -> None:
        for key in ("x", "y"):
            with self.subTest(key=key):
                self.assertRefused(
                    intent(R.ACTION_WEEKLY, **{key: 3}),
                    R.REASON_CLIENT_SUPPLIED_CELL,
                    409,
                )

    def test_a_request_carrying_two_grant_shapes_is_refused_by_the_pinned_first(self) -> None:
        # The order is pinned, not incidental: the request is refused by the FIRST
        # class in `CLIENT_KEY_REFUSALS`, and the **write order in the request body
        # does not matter** -- which is the property a caller that checks keys in
        # dict order would fail.
        order = {key: index for index, (key, _r) in enumerate(R.CLIENT_KEY_REFUSALS)}
        for carried in (
            ("price", "item"),
            ("item", "price"),
            ("amount", "next_id"),
            ("next_id", "amount"),
            ("player", "cell", "item_index"),
            ("item_index", "cell", "player"),
        ):
            with self.subTest(carried=list(carried)):
                first = min(carried, key=lambda key: order[key])
                self.assertRefused(
                    intent(R.ACTION_DAILY, **{key: 1 for key in carried}),
                    R.REFUSAL_KEY_MAP[first],
                    409,
                )

    def test_a_refused_grant_key_leaves_the_cursor_exactly_where_it_was(self) -> None:
        before = seeded(weekly=3)
        self.assertRefused(
            intent(R.ACTION_WEEKLY, next_id=99),
            R.REASON_CLIENT_SUPPLIED_NEXT_ID,
            409,
            before,
        )
        self.assertEqual(cursor_now(R.ACTION_WEEKLY), 3)
        self.assertEqual(stamp_now(R.ACTION_WEEKLY), 0, "and nothing was stamped")

    def test_a_refused_grant_key_beats_an_absent_cursor(self) -> None:
        # The request's own shape is checked before the player's own state, so no
        # recorded field is consulted to reach this refusal.
        before = seeded(weekly=_ABSENT)
        self.assertRefused(
            intent(R.ACTION_WEEKLY, item=1055),
            R.REASON_CLIENT_SUPPLIED_ITEM,
            409,
            before,
        )

    def test_an_unknown_action_beats_a_grant_shaped_key(self) -> None:
        self.assertRefused(
            intent("collect", item=1055), "unknown_reward_action", 409
        )

    # --- the recorded state ---------------------------------------------------
    def test_an_absent_cursor_is_refused_and_not_defaulted_to_zero(self) -> None:
        for action, cursor_key in (
            (R.ACTION_WEEKLY, R.WEEKLY_CURSOR_KEY),
            (R.ACTION_DAILY, R.DAILY_CURSOR_KEY),
        ):
            with self.subTest(action=action):
                before = seeded(**{
                    "weekly" if action == R.ACTION_WEEKLY else "daily": _ABSENT
                })
                body = self.assertRefused(intent(action), "absent_reward_cursor", 409, before)
                self.assertIn(cursor_key, body["error"]["message"])
                self.assertNotIn(cursor_key, private_now(), "nothing was created")

    def test_an_unreadable_cursor_is_refused_and_not_coerced(self) -> None:
        for value in ("0", 1.0, True, False, [0], {"v": 0}, None):
            with self.subTest(cursor=value):
                before = seeded(weekly=value)
                self.assertRefused(
                    intent(R.ACTION_WEEKLY), R.REASON_INVALID_CURSOR, 409, before
                )
                self.assertEqual(cursor_now(R.ACTION_WEEKLY), value, "never rewritten")

    def test_an_absent_instant_is_refused_rather_than_created_by_the_branch(self) -> None:
        for action, stamp_key in (
            (R.ACTION_WEEKLY, R.WEEKLY_STAMP_KEY),
            (R.ACTION_DAILY, R.DAILY_STAMP_KEY),
        ):
            with self.subTest(action=action):
                before = seeded(**{
                    "weekly_stamp" if action == R.ACTION_WEEKLY else "daily_stamp": _ABSENT
                })
                body = self.assertRefused(intent(action), "absent_reward_instant", 409, before)
                self.assertIn(stamp_key, body["error"]["message"])
                self.assertNotIn(
                    stamp_key, private_now(),
                    "a created key would change the size of privateState and "
                    "break the exact leaf allowlist that carries the proof",
                )

    def test_an_unreadable_instant_is_refused(self) -> None:
        # An unreadable value is a different condition from a missing key, and the
        # two get different answers -- see `test_an_unreadable_cursor_is_refused`.
        for value in ("yesterday", 1.0, True, [0], None):
            with self.subTest(instant=value):
                before = seeded(weekly_stamp=value)
                body = self.assertRefused(
                    intent(R.ACTION_WEEKLY), R.REASON_INVALID_CURSOR, 409, before
                )
                self.assertIn(R.WEEKLY_STAMP_KEY, body["error"]["message"])

    def test_a_save_with_no_private_state_is_refused(self) -> None:
        # The one test that leaves the disposable corpus unreadable, so the whole
        # private-state object is captured first and restored in a cleanup: a save
        # with no `privateState` at all makes every later accessor raise.
        #
        # The `before` snapshot is taken **after** the removal on purpose.  Capturing
        # it before would make the byte-identity assertion vacuous in the direction
        # that matters -- it would compare the *seeded* file against the *stripped*
        # one and fail for a reason that has nothing to do with the refusal -- and
        # the `private` half would compare a dict against `None` rather than
        # `None` against `None`, which is the comparison that shows the refusal
        # created nothing.
        restored = copy.deepcopy(private_now())
        self.addCleanup(
            lambda: write_private_verbatim(
                private=copy.deepcopy(restored)
            )
        )
        write_private_verbatim(private=None)
        before = snapshot()
        self.assertIsNone(before["private"], "the save really has no private state")
        self.assertEqual(before["resources"], {}, "so it reports no stored slots")
        body = self.assertRefused(
            intent(R.ACTION_WEEKLY), "absent_reward_cursor", 409, before
        )
        self.assertIn(R.PRIVATE_STATE_KEY, body["error"]["message"])

    # --- outside the reward contract ------------------------------------------
    def test_an_unknown_user_is_refused(self) -> None:
        before = seeded()
        self.assertRefused(
            {"user_id": UNKNOWN_USER, "action": R.ACTION_WEEKLY},
            "unknown_user_id",
            404,
            before,
        )

    def test_a_missing_or_non_object_body_is_refused_by_the_shared_guard(self) -> None:
        before = seeded()
        with harness.offline():
            response = CLIENT.post("/v0/reward", data="not json")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_payload")
        self.assertEqual(snapshot()["bytes"], before["bytes"])
        with harness.offline():
            response = CLIENT.post("/v0/reward", json={})  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_user_id")
        self.assertEqual(snapshot()["bytes"], before["bytes"])

    def test_no_server_and_no_port_is_bound_by_this_suite(self) -> None:
        self.assertTrue(harness.port_is_free("127.0.0.1", 5056))


# ------------------------------------------------------------ refusal ordering --
class RefusalOrderTests(SeededTestCase):
    """The order is one chain, and every link is asserted to precede the next."""

    def test_the_two_refusal_tables_agree_with_the_pinned_order(self) -> None:
        self.assertEqual(R.STRUCTURAL_REFUSALS, R.VALIDATION_ORDER)
        self.assertEqual(
            R.REQUEST_SHAPE_REFUSALS + R.RECORDED_STATE_REFUSALS, R.VALIDATION_ORDER
        )
        self.assertEqual(len(R.REQUEST_SHAPE_REFUSALS), 9)
        self.assertEqual(len(R.RECORDED_STATE_REFUSALS), 3)
        self.assertEqual(len(R.VALIDATION_ORDER), 12)

    def test_the_request_shape_is_checked_before_the_recorded_state(self) -> None:
        self.assertEqual(R.VALIDATION_ORDER[0], R.REASON_BAD_REQUEST)
        self.assertEqual(R.VALIDATION_ORDER[1], R.REASON_UNKNOWN_ACTION)
        self.assertEqual(R.VALIDATION_ORDER[2:9], R.REFUSAL_REASON_ORDER)
        self.assertEqual(
            R.VALIDATION_ORDER[9:],
            (R.REASON_ABSENT_CURSOR, R.REASON_INVALID_CURSOR, R.REASON_ABSENT_STAMP),
        )

    def test_an_absent_cursor_outranks_an_absent_instant(self) -> None:
        seeded(weekly=_ABSENT, weekly_stamp=_ABSENT)
        self.assertEqual(
            reward_now(intent(R.ACTION_WEEKLY)).get_json()["error"]["code"],
            R.REASON_ABSENT_CURSOR,
        )

    def test_an_unreadable_cursor_outranks_an_absent_instant(self) -> None:
        seeded(weekly="0", weekly_stamp=_ABSENT)
        self.assertEqual(
            reward_now(intent(R.ACTION_WEEKLY)).get_json()["error"]["code"],
            R.REASON_INVALID_CURSOR,
        )

    def test_every_request_reachable_reason_is_declared_in_the_pinned_order(self) -> None:
        answered = [
            R.REASON_BAD_REQUEST,
            R.REASON_UNKNOWN_ACTION,
        ] + list(R.REFUSAL_REASON_ORDER) + [
            R.REASON_ABSENT_CURSOR,
            R.REASON_INVALID_CURSOR,
            R.REASON_ABSENT_STAMP,
        ]
        self.assertEqual(answered, list(R.VALIDATION_ORDER))
        self.assertEqual(len(answered), 12)


# ----------------------------------------------------------- the snapshot ------
class SnapshotTests(SeededTestCase):
    """``_reward_snapshot`` is a deep copy, and that is what the proof needs."""

    def test_the_document_half_is_deep_copied(self) -> None:
        document, _ = compat_service._reward_snapshot(BOOT, PID)
        document[R.PRIVATE_STATE_KEY][R.WEEKLY_CURSOR_KEY] = 4242
        document[R.PRIVATE_STATE_KEY]["aBrandNewKey"] = [1, 2, 3]
        live = save_now()[R.PRIVATE_STATE_KEY]
        self.assertNotEqual(live[R.WEEKLY_CURSOR_KEY], 4242)
        self.assertNotIn("aBrandNewKey", live)
        self.assertIsNot(document[R.PRIVATE_STATE_KEY], live)

    def test_the_nested_map_rows_are_not_shared_either(self) -> None:
        document, _ = compat_service._reward_snapshot(BOOT, PID)
        key = sorted(document["maps"][0]["items"])[0]
        document["maps"][0]["items"][key][0] = -999
        self.assertNotEqual(save_now()["maps"][0]["items"][key][0], -999)

    def test_the_resource_half_carries_eight_slots_including_energy(self) -> None:
        _, resources = compat_service._reward_snapshot(BOOT, PID)
        self.assertEqual(sorted(resources), sorted(RESOURCE_NAMES))
        self.assertEqual(len(resources), 8)
        self.assertIn(DOCUMENT_ONLY_RESOURCE, resources)

    def test_an_absent_eighth_slot_stays_absent_and_is_never_defaulted(self) -> None:
        # A defaulted zero compares equal across both sides and would make "no
        # resource moved" true for a slot nobody read.  The corpus is restored in a
        # cleanup because the eight-slot assertions elsewhere depend on it.
        before = seeded()
        restored = copy.deepcopy(before["private"])
        self.addCleanup(
            lambda: write_private_verbatim(
                private=copy.deepcopy(restored)
            )
        )
        document = save_now()
        document[R.PRIVATE_STATE_KEY].pop(DOCUMENT_ONLY_RESOURCE)
        write_corpus(document)
        _, resources = compat_service._reward_snapshot(BOOT, PID)
        self.assertNotIn(DOCUMENT_ONLY_RESOURCE, resources)
        self.assertEqual(len(resources), 7)
        self.assertEqual(sorted(resources), sorted(ACCESSOR_RESOURCE_NAMES))


# ------------------------------------------------- the post-execution proof ----
class PostExecutionProofFailureTests(SeededTestCase):
    """Each proof half fails closed rather than reporting the legacy success."""

    def assertFailsClosed(self, result: Result, needle: str) -> Dict[str, Any]:
        self.assertEqual(result.status_code, 500, result.get_json())
        body = result.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn(needle, body["error"]["message"])
        self.assertEqual(sorted(body.keys()), ["error", "ok", "protocol"])
        return body

    # --- the four grant landing places ---------------------------------------
    def test_part_1_a_placed_row_fails_closed(self) -> None:
        def place_row(document: Dict[str, Any]) -> Dict[str, Any]:
            items = document["maps"][0][R.MAP_ITEMS_KEY]
            key = str(max(int(name) for name in items) + 1)
            items[key] = [1055, 58, 48, 1700000000, 0, [], {}, 1]
            return document

        seeded()
        result = post_with("save_document", place_row, intent(R.ACTION_WEEKLY))
        self.assertFailsClosed(result, "maps/0/items")
        self.assertEqual(
            len(save_now()["maps"][0][R.MAP_ITEMS_KEY]), 40,
            "the stub never reached the file; the proof refused to report it",
        )

    def test_part_1_an_existing_row_that_moved_fails_closed(self) -> None:
        def move_row(document: Dict[str, Any]) -> Dict[str, Any]:
            key = sorted(document["maps"][0][R.MAP_ITEMS_KEY])[0]
            document["maps"][0][R.MAP_ITEMS_KEY][key][1] += 1
            return document

        seeded()
        self.assertFailsClosed(
            post_with("save_document", move_row, intent(R.ACTION_WEEKLY)),
            "maps/0/items",
        )

    def test_part_2_a_bought_unit_append_fails_closed(self) -> None:
        def append_unit(document: Dict[str, Any]) -> Dict[str, Any]:
            document[R.PRIVATE_STATE_KEY][R.WEEKLY_UNIT_LIST_KEY].append(1055)
            return document

        seeded()
        self.assertFailsClosed(
            post_with("save_document", append_unit, intent(R.ACTION_WEEKLY)),
            R.PRIVATE_STATE_KEY,
        )

    def test_part_3_a_storage_entry_fails_closed(self) -> None:
        def add_store(document: Dict[str, Any]) -> Dict[str, Any]:
            document["maps"][0][R.DAILY_STORE_KEY]["1055"] = 1
            return document

        seeded()
        self.assertFailsClosed(
            post_with("save_document", add_store, intent(R.ACTION_DAILY)),
            R.DAILY_STORE_KEY,
        )

    def test_part_4_each_of_the_eight_resource_slots_is_individually_checked(self) -> None:
        self.assertEqual(len(ACCESSOR_RESOURCE_NAMES), 7)
        for name in ACCESSOR_RESOURCE_NAMES:
            with self.subTest(resource=name):
                seeded()
                self.assertFailsClosed(
                    post_with("resources", slot_moved(name), intent(R.ACTION_WEEKLY)),
                    "resource %s is" % name,
                )

    def test_part_4_the_document_only_eighth_slot_is_individually_checked(self) -> None:
        # `energy` is NOT one of `LegacyBoot.resources`' seven, so it is read off
        # the document.  If it were not compared anywhere, a stub moving it would
        # pass unnoticed -- which is the whole reason the eighth slot is read at all.
        self.assertIn(DOCUMENT_ONLY_RESOURCE, RESOURCE_NAMES)
        self.assertNotIn(DOCUMENT_ONLY_RESOURCE, ACCESSOR_RESOURCE_NAMES)
        # A VALUE change is caught, and the half that catches it is the
        # whole-document containment check rather than the resource comparison.  That
        # is measured, not assumed, and it is the stronger outcome: the complaint
        # names the exact path `/privateState/energy`, so a reader is told which slot
        # moved without this test having to guess which of two checks fired.
        seeded()
        self.assertFailsClosed(
            post_with(
                "save_document", document_energy(4321), intent(R.ACTION_WEEKLY)
            ),
            "%s/%s" % (R.PRIVATE_STATE_KEY, DOCUMENT_ONLY_RESOURCE),
        )
        # A REMOVAL is caught too, and here the enclosing container is what the
        # message names, because `/privateState` sorts before the vanished path and
        # its size marker changed with it.
        seeded()
        result = post_with(
            "save_document", document_energy(_ABSENT), intent(R.ACTION_WEEKLY)
        )
        self.assertEqual(result.status_code, 500, result.get_json())
        self.assertIn(
            R.PRIVATE_STATE_KEY, result.get_json()["error"]["message"]
        )
        # CONSEQUENCE, recorded rather than worked around: because the eighth slot is
        # read off the document, EVERY difference in it is also a document
        # difference, so the resource comparison's per-slot branch for `energy` is
        # UNREACHABLE through this route -- the containment half always fires first.
        # The slot is still compared twice: the snapshot reports all eight (see
        # `SnapshotTests`), so the second comparison is a second line of defence
        # rather than the one doing the work.  Recorded here so a later reader does
        # not assume the per-slot branch is what guards `energy`.

    def test_a_missing_accessor_slot_fails_closed_rather_than_defaulting(self) -> None:
        for name in ("mana", "xp"):
            with self.subTest(resource=name):
                seeded()
                self.assertFailsClosed(
                    post_with("resources", slot_absent(name), intent(R.ACTION_WEEKLY)),
                    "'%s'" % name,
                )

    def test_the_missing_slot_message_names_the_complete_set(self) -> None:
        seeded()
        result = post_with("resources", slot_absent("mana"), intent(R.ACTION_WEEKLY))
        message = result.get_json()["error"]["message"]
        self.assertIn("exposed stored resource set", message)
        self.assertIn("every exposed slot must be present on both sides", message)
        # The message names the slot that vanished and the set it left, so a
        # reader can tell which one the proof is complaining about.
        self.assertIn("mana", message)
        self.assertIn("energy", message, "the document-only slot is named too")

    def test_the_allowlist_names_no_foreign_field(self) -> None:
        # The whole point of carrying the proof as a document-wide allowlist: it
        # compares every path against two, so it needs to know nothing about the
        # fields a grant would land in.
        for action in R.ACTIONS:
            with self.subTest(action=action):
                paths = R.allowed_leaf_paths(action)
                self.assertEqual(len(paths), 2)
                self.assertEqual(
                    paths,
                    [
                        "/%s/%s" % (R.PRIVATE_STATE_KEY, R.ACTION_CURSOR_KEY[action]),
                        "/%s/%s" % (R.PRIVATE_STATE_KEY, R.ACTION_STAMP_KEY[action]),
                    ],
                )

    def test_an_empty_container_that_appeared_fails_closed(self) -> None:
        # A grant could create a key whose value is itself empty; a leaves-only
        # projection would report no change for it.  The reported path is the
        # ENCLOSING container rather than the new key, because `leaf_diff` returns
        # the first path in sorted order and `/privateState` sorts before
        # `/privateState/anEmptyGrant` -- which is a stronger complaint, not a
        # weaker one: the whole object changed size.
        def add_empty(document: Dict[str, Any]) -> Dict[str, Any]:
            document[R.PRIVATE_STATE_KEY]["anEmptyGrant"] = {}
            return document

        seeded()
        self.assertFailsClosed(
            post_with("save_document", add_empty, intent(R.ACTION_WEEKLY)),
            "changed /%s," % R.PRIVATE_STATE_KEY,
        )

    def test_the_empty_containers_themselves_are_measured_as_changes(self) -> None:
        # The property the case above relies on, asserted directly on the shared
        # projection rather than only through a route response.
        #
        # The `before` document deliberately holds **populated** containers: an empty
        # object that stays empty is genuinely unchanged, so comparing two
        # all-empty sides would assert a difference that does not exist and would
        # pass for the wrong reason if the projection ever reported one.  Both
        # directions are covered, because the route case above creates an empty
        # container where none was and this one empties a populated one.
        populated = {"a": {"x": 1}, "b": [1], "c": {"d": 1}}
        self.assertEqual(R.leaf_diff(populated, populated), [])
        for empty in ({}, []):
            with self.subTest(empty=empty):
                emptied = {"a": dict(empty), "b": list(empty), "c": {"d": 1}}
                changed = R.leaf_diff(populated, emptied)
                self.assertIn("/a", changed, "the emptied object's own path")
                self.assertIn("/b", changed, "the emptied array's own path")
                self.assertNotIn("/c", changed, "an untouched container is not a change")
        # And the direction the route case needs: a container that APPEARS, empty.
        for empty in ({}, []):
            with self.subTest(appeared=empty):
                appeared = dict(populated)
                appeared["e"] = copy.deepcopy(empty)
                changed = R.leaf_diff(populated, appeared)
                self.assertIn("/e", changed)
                self.assertNotIn("/c", changed)
        # The size marker is what makes this work, so it is asserted rather than
        # assumed: a populated object and an empty one differ ONLY in its marker.
        markers = R.document_leaves({"a": {"x": 1}})
        empty_markers = R.document_leaves({"a": {}})
        self.assertEqual(markers["/a"], "<object:1>")
        self.assertEqual(empty_markers["/a"], "<object:0>")

    def test_the_unaddressed_cursor_moving_fails_closed(self) -> None:
        seeded(weekly=1, daily=4)
        self.assertFailsClosed(
            post_with(
                "save_document",
                private_mutate(lambda private: private.__setitem__(R.DAILY_CURSOR_KEY, 5)),
                intent(R.ACTION_WEEKLY),
            ),
            R.DAILY_CURSOR_KEY,
        )

    def test_the_unaddressed_instant_moving_fails_closed(self) -> None:
        seeded(daily_stamp=999)
        self.assertFailsClosed(
            post_with(
                "save_document",
                private_mutate(lambda private: private.__setitem__(R.DAILY_STAMP_KEY, 123)),
                intent(R.ACTION_WEEKLY),
            ),
            R.DAILY_STAMP_KEY,
        )

    def test_an_unstamped_instant_fails_closed(self) -> None:
        # Both preserved branches write it unconditionally, so its absence from
        # the changed set is a failure rather than a permitted no-op.
        def unstamp(document: Dict[str, Any]) -> Dict[str, Any]:
            document[R.PRIVATE_STATE_KEY][R.WEEKLY_STAMP_KEY] = 0
            return document

        seeded(weekly_stamp=0)
        result = post_with("save_document", unstamp, intent(R.ACTION_WEEKLY))
        self.assertFailsClosed(result, "was not stamped")
        self.assertIn(R.WEEKLY_STAMP_KEY, result.get_json()["error"]["message"])

    # --- the cursor proof ----------------------------------------------------
    def test_a_cursor_that_moved_by_the_wrong_amount_fails_closed(self) -> None:
        seeded(weekly=2)
        self.assertFailsClosed(
            post_with(
                "save_document",
                private_mutate(lambda private: private.__setitem__(R.WEEKLY_CURSOR_KEY, 4)),
                intent(R.ACTION_WEEKLY),
            ),
            "is 4 after execution, not the derived 3",
        )

    def test_a_cursor_that_did_not_move_at_all_fails_closed(self) -> None:
        seeded(weekly=2)
        self.assertFailsClosed(
            post_with(
                "save_document",
                private_mutate(lambda private: private.__setitem__(R.WEEKLY_CURSOR_KEY, 2)),
                intent(R.ACTION_WEEKLY),
            ),
            "is 2 after execution, not the derived 3",
        )

    def test_a_cursor_that_vanished_is_refused_and_reports_no_state(self) -> None:
        # MEASURED, and the status is a consequence of the route's uniform mapping
        # rather than a per-call-site decision: the post-execution `read_cursor`
        # raises the envelope's own `absent_reward_cursor`, and `_reward_refusal`
        # maps every declared reason to 409, so a vanished cursor arrives as a 409
        # with an empty payload rather than as a 500.  The preserved server cannot
        # produce this state -- both branches assign the cursor unconditionally --
        # so no committed case exists and the choice is recorded rather than
        # resolved.
        seeded(weekly=2)

        def drop(document: Dict[str, Any]) -> Dict[str, Any]:
            document[R.PRIVATE_STATE_KEY].pop(R.WEEKLY_CURSOR_KEY)
            return document

        result = post_with("save_document", drop, intent(R.ACTION_WEEKLY))
        body = result.get_json()
        self.assertEqual(result.status_code, 409)
        self.assertEqual(body["error"]["code"], R.REASON_ABSENT_CURSOR)
        self.assertEqual(sorted(body.keys()), ["error", "ok", "protocol"])

    def test_a_proof_failure_leaves_the_cursor_the_legacy_branch_wrote(self) -> None:
        # A proof failure is a SERVER refusal and reports no state at all, so the
        # persisted cursor is whatever the unchanged dispatcher wrote.
        seeded(weekly=2)
        post_with(
            "save_document",
            private_mutate(lambda private: private.__setitem__(R.DAILY_CURSOR_KEY, 5)),
            intent(R.ACTION_WEEKLY),
        )
        self.assertEqual(cursor_now(R.ACTION_WEEKLY), 3)

    def test_every_proof_failure_is_a_server_fault_not_a_client_one(self) -> None:
        # The stub is a bug in this service, so answering 409 would blame a request
        # that did nothing wrong.
        seeded()
        result = post_with("resources", slot_moved("gold"), intent(R.ACTION_WEEKLY))
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.get_json()["error"]["code"], "internal_error")


# ------------------------------------------------------- structural guards ----
def source() -> str:
    return SERVICE.read_text(encoding="utf-8")


def decorator_offsets(text: str) -> List[int]:
    """The character offset of every route decorator, in file order."""
    offsets: List[int] = []
    cursor = 0
    for line in text.split("\n"):
        if line.strip().startswith("@app."):
            offsets.append(cursor)
        cursor += len(line) + 1
    return offsets


def route_source() -> str:
    """The ``/v0/reward`` route slice: its own ``def`` up to the next decorator."""
    text = source()
    start = text.index("def v0_reward(")
    following = [offset for offset in decorator_offsets(text) if offset > start]
    if not following:
        raise AssertionError("no route decorator follows v0_reward")
    span = text[start:following[0]]
    if not span.startswith("def v0_reward("):
        raise AssertionError("the route slice does not begin at its own def")
    return span


def refusal_mapping_source() -> str:
    """The ``_reward_refusal`` helper's status-by-reason table.

    The mapping lives at MODULE scope on purpose -- a helper declared inside the
    route slice would break the one-function-per-route invariant -- so this reads
    the helper's own body rather than the route.
    """
    text = source()[source().index("def _reward_refusal("):]
    begin = text.index("status_by_reason = {")
    end = text.index("status_by_reason.get(", begin)
    return text[begin:end]


def route_code() -> str:
    """The route's own code with its **docstring removed**.

    Both structural claims below are about what the route *executes*, and the
    route's docstring deliberately quotes the preserved branches verbatim -- so it
    contains ``weeklyRewardIndex`` and names ``VALIDATION_ORDER`` while doing
    neither.  Stripping the docstring is what makes "the route never writes a
    cursor of its own" a statement about the code rather than about a quotation
    of someone else's code.
    """
    tree = ast.parse(textwrap.dedent(route_source().lstrip("\n")))
    function = tree.body[0]
    assert isinstance(function, ast.FunctionDef)
    if (
        function.body
        and isinstance(function.body[0], ast.Expr)
        and isinstance(function.body[0].value, ast.Constant)
    ):
        function.body = function.body[1:]
    return ast.unparse(tree)


def module_scope_functions() -> List[str]:
    tree = ast.parse(source())
    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]


def envelope_reason_constants() -> List[Tuple[str, str]]:
    """Every ``REASON_*`` the envelope declares, as ``(constant, value)`` pairs.

    Read from the module's source rather than by attribute access, so the mapping
    the service's table is checked against is derived from the declaration rather
    than from an import that could only ever agree with itself.
    """
    return re.findall(
        r'^(REASON_[A-Z_]+) = "([a-z_]+)"$',
        ENVELOPE.read_text(encoding="utf-8"),
        re.MULTILINE,
    )


def envelope_reason_names() -> List[str]:
    return [value for _name, value in envelope_reason_constants()]


def symbol_for(reason: str) -> str:
    """The ``rewards_envelope`` constant a reason string is declared under.

    The mapping table keys its entries by the SYMBOLIC constant, so an assertion
    that looked for the reason's string literal would fail against a mapping that
    is in fact complete.  The lookup goes the other way round for the same reason:
    ``absent_reward_cursor`` is declared as ``REASON_ABSENT_CURSOR``, so the
    constant name cannot be derived from the value.
    """
    for name, value in envelope_reason_constants():
        if value == reason:
            return "rewards_envelope.%s" % name
    raise AssertionError("no REASON_* constant declares %r" % reason)


class StructuralTests(unittest.TestCase):
    """Where the route and its helpers live, pinned as a bounded set."""

    def test_the_route_slice_parses_as_exactly_one_function(self) -> None:
        tree = ast.parse(textwrap.dedent(route_source().lstrip("\n")))
        self.assertEqual(
            [node.name for node in tree.body if isinstance(node, ast.FunctionDef)],
            ["v0_reward"],
        )

    def test_no_helper_is_declared_inside_the_route_slice(self) -> None:
        span = route_source()
        for helper in ("_reward_snapshot", "_reward_refusal"):
            with self.subTest(helper=helper):
                self.assertNotIn("def %s(" % helper, span)
        tree = ast.parse(textwrap.dedent(span.lstrip("\n")))
        self.assertEqual(len(tree.body), 1)

    def test_the_route_sits_between_tutorial_and_combat(self) -> None:
        markers = [
            line.strip()
            for line in source().split("\n")
            if line.strip().startswith("@app.")
        ]
        names = [marker.split("/")[-1].rstrip('")') for marker in markers]
        self.assertIn("reward", names)
        self.assertLess(names.index("tutorial"), names.index("reward"))
        self.assertLess(names.index("reward"), names.index("combat"))
        # The two delivered invariants the combat and stored-placement suites own.
        self.assertEqual(markers[0], '@app.post("/v0/tutorial")')
        self.assertEqual(markers[-1], '@app.post("/v0/level_up")')

    def test_every_reward_helper_is_declared_at_module_scope(self) -> None:
        names = module_scope_functions()
        for helper in ("_reward_snapshot", "_reward_refusal"):
            with self.subTest(helper=helper):
                self.assertIn(helper, names)

    def test_no_further_reward_helper_can_be_added_silently(self) -> None:
        names = module_scope_functions()
        reward_named = sorted(n for n in names if "reward" in n.lower())
        self.assertEqual(reward_named, ["_reward_refusal", "_reward_snapshot"])
        self.assertEqual(
            len(names), len(set(names)), "no duplicate module-scope name"
        )

    def test_every_request_reachable_reason_has_a_status_and_a_code(self) -> None:
        mapping = refusal_mapping_source()
        for reason in R.VALIDATION_ORDER:
            with self.subTest(reason=reason):
                self.assertIn(symbol_for(reason), mapping)

    def test_the_three_internal_reasons_map_to_five_hundred(self) -> None:
        mapping = refusal_mapping_source()
        for reason in (
            R.REASON_INVALID_SCHEDULE,
            R.REASON_INVALID_VECTOR,
            R.REASON_INVALID_TIMESTAMP,
        ):
            with self.subTest(reason=reason):
                self.assertIn(symbol_for(reason), mapping)
                body, status = compat_service._reward_refusal(reason, "boom")
                self.assertEqual(status, 500)
                self.assertIn(reason, body["error"]["message"])

    def test_every_request_reachable_reason_maps_to_four_oh_nine(self) -> None:
        for reason in R.VALIDATION_ORDER:
            with self.subTest(reason=reason):
                body, status = compat_service._reward_refusal(reason, "boom")
                self.assertEqual(
                    status, 409,
                    "a refusal of a well-formed request is 409, not 400",
                )
                self.assertEqual(body["error"]["code"], ERROR_CODE_BY_REASON[reason])

    def test_an_unmapped_reason_fails_closed_as_a_server_fault(self) -> None:
        # `_reward_refusal`'s fallback: an unknown reason is a bug in the mapping,
        # so it answers 500 rather than blaming a request that did nothing wrong.
        body, status = compat_service._reward_refusal(
            "a_reason_that_is_not_declared", "boom"
        )
        self.assertEqual(status, 500)
        self.assertIn("a_reason_that_is_not_declared", body["error"]["message"])

    def test_the_mapping_covers_every_reason_the_envelope_declares(self) -> None:
        mapping = refusal_mapping_source()
        declared = envelope_reason_names()
        self.assertEqual(len(declared), 15)
        for reason in declared:
            with self.subTest(reason=reason):
                self.assertIn(symbol_for(reason), mapping)

    def test_the_route_calls_the_envelope_rather_than_restating_it(self) -> None:
        code = route_code()
        self.assertEqual(code.count("rewards_envelope.validate_request(payload)"), 1)
        self.assertEqual(code.count("rewards_envelope.derive_reward("), 1)
        self.assertEqual(code.count("rewards_envelope.build_envelope("), 1)
        self.assertNotIn("VALIDATION_ORDER", code)
        self.assertNotIn("CLIENT_KEY_REFUSALS", code)

    def test_the_route_never_writes_a_cursor_of_its_own(self) -> None:
        # The cursor is advanced by the UNCHANGED legacy branch; the route reads
        # and proves, and assigns nothing into private state.
        code = route_code()
        assignments = re.findall(r"\[.PRIVATE_STATE_KEY.\]\[[^\]]+\]\s*=", code)
        self.assertEqual(
            assignments, [],
            "the route never assigns into private state; the preserved branch owns "
            "both writes",
        )
        self.assertNotIn("weeklyRewardIndex", code)
        self.assertNotIn("bonusNextId", code)
        self.assertNotIn("timeStampMondayBonus", code)
        self.assertNotIn("timestampLastBonus", code)

    def test_the_route_docstring_does_quarter_the_branches_it_does_not_run(self) -> None:
        # The counterpart of the claim above: the four legacy key names DO appear
        # in the route, in a docstring that quotes the preserved branches.  Asserted
        # explicitly so a later reader who strips the docstring does not conclude
        # the names were invented by this line.
        span = route_source()
        for key in (
            "weeklyRewardIndex",
            "bonusNextId",
            "timeStampMondayBonus",
            "timestampLastBonus",
        ):
            with self.subTest(key=key):
                self.assertIn(key, span, "quoted in the docstring")
                self.assertNotIn(key, route_code(), "and never in the code")

    def test_the_service_adds_no_new_dependency_and_no_socket(self) -> None:
        span = route_source()
        for forbidden in ("requests", "urllib", "socket", "subprocess", "open("):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, span)


#: ``reason -> the code the route answers it with``.  Pinned here rather than read
#: back from the route, so a change to a code has to be made in the test too.
ERROR_CODE_BY_REASON: Dict[str, str] = {
    R.REASON_BAD_REQUEST: "bad_request",
    R.REASON_UNKNOWN_ACTION: "unknown_reward_action",
    R.REASON_CLIENT_SUPPLIED_ITEM: "client_supplied_item",
    R.REASON_CLIENT_SUPPLIED_ITEM_INDEX: "client_supplied_item_index",
    R.REASON_CLIENT_SUPPLIED_CELL: "client_supplied_cell",
    R.REASON_CLIENT_SUPPLIED_PLAYER: "client_supplied_player",
    R.REASON_CLIENT_SUPPLIED_NEXT_ID: "client_supplied_next_id",
    R.REASON_CLIENT_SUPPLIED_AMOUNT: "client_supplied_amount",
    R.REASON_CLIENT_SUPPLIED_PRICE: "client_supplied_price",
    R.REASON_ABSENT_CURSOR: "absent_reward_cursor",
    R.REASON_INVALID_CURSOR: "invalid_reward_cursor",
    R.REASON_ABSENT_STAMP: "absent_reward_instant",
}


if __name__ == "__main__":
    unittest.main()
