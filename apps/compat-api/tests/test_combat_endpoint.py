#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/combat`` endpoint tests (OpenSpec ``godot-combat-actions``).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so this suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across every combat execution.

**What the committed corpus can and cannot exercise.**  The committed
``tests/saves/fresh-player.json`` places **40 rows, every one a committed
building** (20 on team 1, 20 on team 3) and records an **empty** ledger, so a
``resolve`` can never be *positive* against it: there is no committed unit row
for ``map_lose_item`` to match.  Every executing success case therefore seeds a
unit row into the **disposable corpus only**, exactly as the delivered level,
expand, and behaviour suites seed their own disagreement states.  That seeding
is a test mechanism, not the executed-legacy fixture (which lives under
``tests/fixtures/godot-combat-actions/``), and it never touches a committed save.

**How the post-execution proof halves are exercised.**  Each stub rewrites only
the read that happens **after** ``execute_commands`` returned, detected by
wrapping the boot's own ``execute_commands`` rather than by counting accessor
calls -- ``resources()`` alone calls ``save_document`` three times, so a
call-counting stub would rewrite the *pre*-execution ledger read and silently
test something else.  The transform receives a **deep copy**, so the recorded
corpus file is never itself corrupted by a proof-failure test.

Covered:

* **a successful resolution** -- the **first** eligible row in the save's own
  recorded map-key order is removed, **exactly one** row, the ledger increments
  by exactly one, **every one of the seven stored resources is unchanged**, and
  the persisted corpus file matches the response.
* **the identity, not a count** -- a request naming two eligible rows removes
  the first by *recorded insertion order* and **not** the numerically smallest
  key, which is the whole of design D1.
* **both ledger gates and no third** -- an absent ``resurrectable`` flag, a
  committed building, and a truthy-but-not-team-one row each destroy the row and
  write **no** ledger entry, with both gates reported as having declined.
* **the ledger's key order and values** -- an existing entry increments **in
  place** and an absent one is created at the **end**, so the persisted order is
  a value comparison rather than a re-ordering.
* **``kill`` and ``kill_iid``** -- the former deletes the addressed row and never
  touches the ledger; the latter is delivered as a proven no-op (design D5), not
  refused.
* **the client-dictated destruction refusal** -- all three key families, a
  **separate named code** from the eligibility check (design D2), fired **before**
  the addressing is required and before any player state is read.
* **every other refusal** -- a closed action vocabulary, absent and ill-typed
  addressing, an unknown user, an unknown save, a missing or non-object body,
  ``no_eligible_row``, ``unaddressable_row``, and an unreadable ledger -- each
  with its named code, an **empty** payload, and a corpus left byte-identical.
* **the four-part post-execution proof** -- each half failing closed with
  ``internal_error`` rather than reporting the legacy success.  The row count is
  checked **last** and is therefore implied by the key-set half for every
  reachable destruction; the suite proves that ordering rather than pretending
  the half is independent.
* **the recorded refusals and non-rules** -- no combat, no cost or reward, no
  syringe cost, and no added placement validation, each carrying a specific
  reason and each marked ``implemented: False`` so a deliberate omission cannot
  be read as a gap.
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import compat_test_harness as harness

import combat_envelope
import compat_legacy
import compat_service

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed corpus's own first row: item 26 (Command Center) at (51, 41) on
# player team 1.  It is a committed BUILDING, which is exactly what ``kill`` needs
# (that branch is type-agnostic) and exactly what ``resolve`` cannot use.
#
# Item 26 is also the corpus's ONLY identity placed exactly once, which is what
# makes it the right committed row for the recorded-order precedence case: any
# identity placed at several keys would make the "first eligible" answer depend
# on all of them.  That is measured, not assumed, by
# :meth:`CommittedCorpusTests.test_each_committed_identity_used_here_is_placed_once`.
COMMITTED_KEY = "1"
COMMITTED_ITEM = 26
COMMITTED_CELL = (51, 41)
COMMITTED_PLACEMENTS = 40
COMMITTED_TEAM_ONE_ROWS = 20
COMMITTED_TEAM_THREE_ROWS = 20
ABSENT_MAP_KEY = 999999

# Committed identities used by the seeded rows.  Each is read through
# ``_committed_item``, i.e. the RAW configuration, so these figures are the ones
# ``engine.push_dead_unit`` itself would have seen.
UNIT_RESURRECTABLE = 1001  # type 'u', properties carry resurrectable '1'
UNIT_FLAG_ABSENT = 923     # type 'u', the key is ABSENT from properties entirely
# A committed building the committed corpus does NOT place, so the seeded row is
# genuinely the first eligible one and nothing committed competes with it.
UNPLACED_BUILDING = 12     # type 'b', no resurrectable key at all
CORPUS_PLACED_BUILDING = COMMITTED_ITEM
CORPUS_PLACED_BUILDING_KEY = COMMITTED_KEY

# Seeded placement keys.  Deliberately inserted in this ORDER and not in numeric
# order, so "first eligible row" and "numerically smallest key" are different
# answers and the suite can tell them apart.
SEEDED_FIRST = "43"
SEEDED_SECOND = "42"
SEEDED_TEAM_THREE = "44"
SEEDED_BUILDING = "45"
SEEDED_CELL = (900, 900)

RESOURCE_NAMES = combat_envelope.RESOURCE_NAMES


# ------------------------------------------------------------- corpus seeding --
def write_corpus(save: Dict[str, Any]) -> None:
    path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def save_now() -> Dict[str, Any]:
    return BOOT.save_document(PID)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    """The **persisted** corpus document, which the legacy batch wrote."""
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def items_now() -> Dict[str, Any]:
    return copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def reset_placements() -> None:
    """Restore the committed corpus's own 40 placement rows."""
    seed = harness.load_seed()
    save = save_now()
    save["maps"][0]["items"] = copy.deepcopy(seed["maps"][0]["items"])
    write_corpus(save)


def seed_row(key: str, item_id: int, team: int = 1) -> None:
    """Add one placed row to the disposable corpus (slot shape per ``engine.py:8-31``)."""
    save = save_now()
    rows = save["maps"][0]["items"]
    offset = len(rows)
    rows[key] = [item_id, SEEDED_CELL[0] + offset, SEEDED_CELL[1] + offset, 0, 0, [], {}, team]
    write_corpus(save)


def set_ledger(bag: Optional[Dict[str, int]]) -> Dict[str, int]:
    """Write the disposable corpus's dead-hero ledger, in memory **and** on disk.

    ``engine.push_dead_unit`` mutates ``privateState["deadHeroes"]`` in place and
    this suite asserts against the persisted file, so both representations are
    written here.  Never a committed save, and never a claim about legacy
    behaviour -- the same contained mechanism the behaviour suite uses.
    """
    save = save_now()
    save["privateState"][combat_envelope.LEDGER_KEY] = dict(bag or {})
    write_corpus(save)
    return dict(bag or {})


def ledger_now() -> Dict[str, Any]:
    return save_now()["privateState"][combat_envelope.LEDGER_KEY]


def snapshot() -> Dict[str, Any]:
    return {
        "items": items_now(),
        "ledger": copy.deepcopy(ledger_now()),
        "resources": resources_now(),
        "bytes": (CORPUS / "saves" / ("%s.save.json" % PID)).read_bytes(),  # type: ignore[operator]
    }


def bare() -> Dict[str, Any]:
    """Reset BOTH halves of the disposable corpus to the committed state.

    Both, deliberately: ``set_ledger`` writes through the corpus file, so a test
    that resets only the placements inherits the previous test's ledger and would
    fail against a state it never set up.
    """
    reset_placements()
    set_ledger({})
    return snapshot()


def seeded(
    item_id: int = UNIT_RESURRECTABLE,
    team: int = 1,
    second: bool = False,
    ledger: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Reset to the committed placements plus the seeded rows and ledger."""
    reset_placements()
    seed_row(SEEDED_FIRST, item_id, team)
    if second:
        seed_row(SEEDED_SECOND, item_id, team)
    set_ledger(ledger if ledger is not None else {})
    return snapshot()


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
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a combat execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def combat_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/combat", json=payload)  # type: ignore[union-attr]


def intent(action: str = "resolve", **extra: Any) -> Dict[str, Any]:
    """The whole contract: a save identity, an action, and one identity or key."""
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

    The trigger is ``execute_commands`` returning, not an accessor call count:
    ``_combat_snapshot`` calls ``map_items``, ``save_document`` and ``resources``
    in that order and ``resources`` itself calls ``save_document`` twice, so a
    call-counting stub rewrites the pre-execution ledger read instead of the
    post-execution one and would pass for the wrong reason.
    """

    def __init__(
        self,
        attribute: str,
        transform: Callable[[Any], Any],
    ) -> None:
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
            return Result(app, app.test_client().post("/v0/combat", json=payload))


class _DerivedDestruction:
    """Rewrite ONE field of the read-only projection the route dispatches on.

    Used only to reach the row-count half of the proof, which is otherwise
    implied by the key-set half (see :class:`PostExecutionProofFailureTests`).
    The projection's ledger derivation is passed through untouched, so the stub
    perturbs the *count* and nothing else.
    """

    def __init__(self, replacement: int) -> None:
        self.replacement = replacement
        self._original = combat_envelope.project_combat

    def __enter__(self) -> "_DerivedDestruction":
        original = self._original

        def stub(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            projection = original(*args, **kwargs)
            projection["destruction"] = self.replacement
            return projection

        combat_envelope.project_combat = stub  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: Any) -> None:
        combat_envelope.project_combat = self._original  # type: ignore[assignment]


def post_with_derived_destruction(replacement: int, payload: Dict[str, Any]) -> Result:
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    with _DerivedDestruction(replacement):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/combat", json=payload))


# ------------------------------------------------------- the successful path --
class SuccessfulResolveTests(unittest.TestCase):
    """One resolution through the real dispatcher, with its four-part proof."""

    def test_exactly_one_row_is_removed_and_the_ledger_increments(self) -> None:
        before = seeded(ledger={"1001": 2})
        response = combat_now(intent(item_id=UNIT_RESURRECTABLE))
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["protocol"], "compat-v0")
        self.assertEqual(body["result"], "success")
        self.assertEqual(body["action"], "resolve")
        self.assertEqual(body["command"], combat_envelope.END_ATTACK_COMMAND)
        self.assertEqual(body["destruction"]["count"], 1)
        self.assertEqual(body["destruction"]["derived_key"], SEEDED_FIRST)
        self.assertEqual(body["destruction"]["rows_before"], COMMITTED_PLACEMENTS + 1)
        self.assertEqual(body["destruction"]["rows_after"], COMMITTED_PLACEMENTS)
        self.assertEqual(body["ledger_written"], True)
        self.assertEqual(ledger_now(), {"1001": 3})
        self.assertNotIn(SEEDED_FIRST, items_now())
        self.assertEqual(
            len(items_now()), len(before["items"]) - 1, "exactly one row is gone"
        )

    def test_every_other_row_is_byte_identical(self) -> None:
        before = seeded()
        combat_now(intent(item_id=UNIT_RESURRECTABLE))
        after = items_now()
        self.assertEqual(
            sorted(set(after)),
            sorted(set(before["items"]) - {SEEDED_FIRST}),
            "the only key-set difference is the derived key",
        )
        for key in before["items"]:
            if key == SEEDED_FIRST:
                continue
            with self.subTest(placement=key):
                self.assertEqual(after[key], before["items"][key])

    def test_the_first_eligible_row_is_the_first_IN_RECORDED_ORDER(self) -> None:
        # Two eligible rows for one identity, inserted in NON-numeric order, so
        # "first eligible" and "numerically smallest key" are different answers.
        seeded(second=True)
        self.assertLess(
            int(SEEDED_SECOND),
            int(SEEDED_FIRST),
            "the second seeded key is numerically smaller",
        )
        self.assertEqual(
            list(items_now()),
            list(items_now()),
            "insertion order is the save's own order",
        )
        body = combat_now(intent(item_id=UNIT_RESURRECTABLE)).get_json()
        self.assertEqual(
            body["destruction"]["eligible_keys"],
            [SEEDED_FIRST, SEEDED_SECOND],
            "both rows are eligible and reported in recorded order",
        )
        self.assertEqual(
            body["destruction"]["derived_key"],
            SEEDED_FIRST,
            "the FIRST in recorded order is destroyed, not the smallest key",
        )
        self.assertEqual(body["destruction"]["eligible_count"], 2)
        self.assertEqual(body["destruction"]["count"], 1)
        remaining = items_now()
        self.assertIn(SEEDED_SECOND, remaining)
        self.assertNotIn(SEEDED_FIRST, remaining)

    def test_the_ledger_and_the_derivation_agree_by_value(self) -> None:
        seeded(ledger={"500": 3, "1001": 4})
        body = combat_now(intent(item_id=UNIT_RESURRECTABLE)).get_json()
        # `project_ledger` is a DISPLAY projection and sorts its keys, so
        # `ledger_before` is sorted; `ledger_after` is read off the live ledger
        # and therefore keeps the recorded order.  Both orders are asserted
        # explicitly rather than left to whichever the reader assumes.
        self.assertEqual(
            body["ledger_before"],
            [{"item_id": "1001", "count": 4}, {"item_id": "500", "count": 3}],
            "the shared projection reports in sorted order",
        )
        self.assertEqual(
            body["ledger_after"],
            [{"item_id": "500", "count": 3}, {"item_id": "1001", "count": 5}],
            "the persisted ledger keeps its recorded insertion order",
        )
        self.assertEqual(
            body["ledger_gates"]["player_team_one"]["holds"], True
        )
        self.assertEqual(
            body["ledger_gates"]["resurrectable_positive"]["holds"], True
        )
        self.assertEqual(
            body["changed"],
            ["/maps/0/items/%s" % SEEDED_FIRST, "/privateState/deadHeroes/1001"],
        )

    def test_every_stored_resource_is_unchanged(self) -> None:
        before = seeded()
        body = combat_now(intent(item_id=UNIT_RESURRECTABLE)).get_json()
        self.assertEqual(len(RESOURCE_NAMES), 7)
        self.assertEqual(
            sorted(body["resources"].keys()),
            sorted(RESOURCE_NAMES),
            "the response reports every stored resource, never a subset",
        )
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(body["resources"][name], before["resources"][name])

    def test_the_persisted_corpus_matches_the_response(self) -> None:
        seeded(ledger={"1001": 1})
        body = combat_now(intent(item_id=UNIT_RESURRECTABLE)).get_json()
        persisted = corpus_save()
        self.assertNotIn(SEEDED_FIRST, persisted["maps"][0]["items"])
        self.assertEqual(
            persisted["privateState"][combat_envelope.LEDGER_KEY], {"1001": 2}
        )

    def test_the_committed_corpus_save_is_never_written(self) -> None:
        seed_path = harness.SEED_SAVE
        before = seed_path.read_bytes()
        seeded()
        self.assertEqual(
            combat_now(intent(item_id=UNIT_RESURRECTABLE)).status_code, 200
        )
        self.assertEqual(
            seed_path.read_bytes(),
            before,
            "the committed corpus save is byte-identical after a resolution",
        )

    def test_the_response_carries_the_whole_derived_contract(self) -> None:
        seeded()
        body = combat_now(intent(item_id=UNIT_RESURRECTABLE)).get_json()
        self.assertEqual(body["addressing"]["key"], "item_id")
        self.assertEqual(body["addressing"]["value"], UNIT_RESURRECTABLE)
        self.assertEqual(body["addressing"]["kind"], combat_envelope.ACTION_ADDRESSING["resolve"])
        self.assertEqual(
            [entry["check"] for entry in body["validation_order"]],
            [entry["check"] for entry in combat_envelope.VALIDATION_ORDER],
        )
        self.assertEqual(body["destruction"]["refused_count"], combat_envelope.CLIENT_DICTATED_REFUSAL)
        self.assertIn("Lost", body["destruction"]["printed_count_is_request"])
        self.assertEqual(body["gates"], combat_envelope.gates())
        self.assertIn("EXACTLY TWO GATES", body["no_third_gate"])
        self.assertEqual(
            body["team_asymmetry"]["status"],
            "RECORDED, NOT EXERCISED, NOT REFUSED",
        )
        self.assertEqual(body["divergence"]["status"], "DIVERGENCE, NOT PARITY")
        self.assertEqual(body["field_inventory"]["key_count"], 12)
        self.assertEqual(body["field_inventory"]["partition"], True)
        self.assertEqual(
            body["correction"]["field_inventory"]["measured_discarded_count"], 9
        )
        self.assertEqual(
            body["correction"]["field_inventory"]["recorded_discarded_count"], 7
        )
        self.assertEqual(
            body["correction"]["corpus"]["measured_neutral_ledger_keys"], 28
        )
        self.assertIsNone(body["kill_contract"])
        self.assertIsNone(body["kill_iid_contract"])


class RecordedOrderPrecedenceTests(unittest.TestCase):
    """D1's ordering rule, proved against **committed** rows only.

    The committed corpus places committed building 26 at map key ``1`` and
    nowhere else, so a seeded row at key ``43`` is a second eligible row for that
    identity.  The derivation must therefore choose the committed key, purely on
    recorded order, with nothing about the seeded row able to win -- and it must
    not win *merely* by being the smaller key either, which is why
    :meth:`test_the_committed_row_wins_although_it_is_numerically_smaller`
    states the coincidence instead of leaving it to be mistaken for a rule.
    """

    def test_the_committed_row_wins_on_recorded_order_alone(self) -> None:
        before = seeded(item_id=CORPUS_PLACED_BUILDING)
        self.assertEqual(
            before["items"][CORPUS_PLACED_BUILDING_KEY][0],
            CORPUS_PLACED_BUILDING,
            "the committed corpus really places that building at that key",
        )
        body = combat_now(intent(item_id=CORPUS_PLACED_BUILDING)).get_json()
        self.assertEqual(
            body["destruction"]["eligible_keys"],
            [CORPUS_PLACED_BUILDING_KEY, SEEDED_FIRST],
            "both rows are eligible; the committed one is recorded first",
        )
        self.assertEqual(
            body["destruction"]["derived_key"], CORPUS_PLACED_BUILDING_KEY
        )
        self.assertEqual(body["destruction"]["count"], 1)
        after = items_now()
        self.assertNotIn(CORPUS_PLACED_BUILDING_KEY, after)
        self.assertIn(SEEDED_FIRST, after, "the later eligible row survives")

    def test_the_committed_row_wins_although_it_is_numerically_smaller(self) -> None:
        """State the coincidence, so this test cannot be read as a min-key rule.

        The committed key ``1`` is both recorded first AND numerically smallest,
        so on its own this case does not distinguish the two readings.  The
        distinction is carried by
        :meth:`SuccessfulResolveTests.test_the_first_eligible_row_is_the_first_IN_RECORDED_ORDER`,
        whose seeded pair is inserted in non-numeric order.  Asserting it here
        means the committed case can never be mistaken for a min-key rule.
        """
        seeded(item_id=CORPUS_PLACED_BUILDING)
        keys = list(items_now())
        eligible = combat_envelope.select_eligible_rows(
            items_now(), CORPUS_PLACED_BUILDING
        )
        self.assertEqual(
            [key for key in eligible["eligible_keys"] if key in keys],
            eligible["eligible_keys"],
            "the eligible list is in the save's own recorded order",
        )
        self.assertLess(
            int(CORPUS_PLACED_BUILDING_KEY),
            int(SEEDED_FIRST),
            "the winning committed key is ALSO numerically smaller here",
        )
        body = combat_now(intent(item_id=CORPUS_PLACED_BUILDING)).get_json()
        self.assertEqual(body["destruction"]["derived_key"], CORPUS_PLACED_BUILDING_KEY)

    def test_the_recorded_order_is_reported_on_every_answer(self) -> None:
        seeded()
        body = combat_now(intent(item_id=UNIT_RESURRECTABLE)).get_json()
        self.assertIn("recorded map-key", body["destruction"]["order"])
        self.assertIn("insertion", body["destruction"]["order"])
        self.assertIn(
            "BATCH", combat_envelope.ORDERING_RULE,
            "the ordering rule records the measured persistence boundary",
        )

    def test_the_committed_map_key_order_is_its_json_order(self) -> None:
        seed = harness.load_seed()
        keys = list(seed["maps"][0]["items"])
        self.assertEqual(keys[:6], ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(len(keys), COMMITTED_PLACEMENTS)
        self.assertEqual(keys, sorted(keys, key=int))
        self.assertEqual(
            items_now(), seed["maps"][0]["items"],
            "the derived order is the save's own, not a re-sort",
        )


# -------------------------------------------------------------- the two gates --
class GateTests(unittest.TestCase):
    """Both gates, and no third: the row dies, the ledger does not move."""

    def _assert_destroyed_without_a_ledger_write(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        before = snapshot()
        response = combat_now(payload)
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["destruction"]["count"], 1)
        self.assertFalse(body["ledger_written"], "neither gate held")
        self.assertEqual(body["ledger_before"], [])
        self.assertEqual(body["ledger_after"], [])
        self.assertEqual(body["changed"], ["/maps/0/items/%s" % SEEDED_FIRST])
        self.assertEqual(
            ledger_now(), before["ledger"], "the ledger is byte-identical"
        )
        self.assertNotIn(SEEDED_FIRST, items_now(), "the row was still destroyed")
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(body["resources"][name], before["resources"][name])
        return body

    def test_an_absent_resurrectable_flag_is_not_a_zero(self) -> None:
        seeded(item_id=UNIT_FLAG_ABSENT)
        body = self._assert_destroyed_without_a_ledger_write(
            intent(item_id=UNIT_FLAG_ABSENT)
        )
        self.assertEqual(body["ledger_gates"]["resurrectable_positive"]["present"], False)
        self.assertEqual(body["ledger_gates"]["resurrectable_positive"]["holds"], False)
        self.assertEqual(body["ledger_gates"]["player_team_one"]["holds"], True)

    def test_a_committed_building_is_destroyed_but_never_entered_the_ledger(self) -> None:
        seeded(item_id=UNPLACED_BUILDING)
        body = self._assert_destroyed_without_a_ledger_write(
            intent(item_id=UNPLACED_BUILDING)
        )
        self.assertEqual(body["ledger_gates"]["resurrectable_positive"]["recorded_flag"], None)

    def test_a_truthy_non_team_one_row_is_the_recorded_asymmetry(self) -> None:
        # The asymmetry is not exercised by the COMMITTED corpus -- every one of
        # the 441 committed unit rows across the committed save documents is on
        # team one -- so it is seeded here on the disposable corpus, which is
        # recorded rather than hidden.
        seeded(team=3)
        body = self._assert_destroyed_without_a_ledger_write(
            intent(item_id=UNIT_RESURRECTABLE)
        )
        self.assertEqual(body["ledger_gates"]["player_team_one"]["recorded_team"], 3)
        self.assertEqual(body["ledger_gates"]["player_team_one"]["required"], 1)
        self.assertEqual(body["ledger_gates"]["player_team_one"]["holds"], False)
        self.assertEqual(body["ledger_gates"]["resurrectable_positive"]["holds"], True)
        self.assertEqual(
            body["team_asymmetry"]["consequence"],
            "a non-team-one unit row would be DESTROYED and would never "
            "ENTER THE LEDGER",
        )
        self.assertFalse(body["team_asymmetry"]["refused"])
        self.assertFalse(body["team_asymmetry"]["exercised"])

    def test_a_falsy_team_row_is_not_eligible_at_all(self) -> None:
        seeded(team=0)
        before = snapshot()
        response = combat_now(intent(item_id=UNIT_RESURRECTABLE))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "no_eligible_row")
        self.assertEqual(items_now(), before["items"])

    def test_exactly_two_gates_are_reported_and_no_third_is_invented(self) -> None:
        seeded()
        body = combat_now(intent(item_id=UNIT_RESURRECTABLE)).get_json()
        self.assertEqual(
            [gate["gate"] for gate in body["gates"]],
            ["player_team_one", "resurrectable_positive"],
        )
        self.assertEqual(len(body["ledger_gates"]), 2)
        self.assertEqual(
            sorted(body["ledger_gates"]), ["player_team_one", "resurrectable_positive"]
        )
        for gate in body["gates"]:
            self.assertTrue(gate["committed"])
            self.assertTrue(str(gate["source"]).startswith("engine.py:"))


# --------------------------------------------------------- the ledger's order --
class LedgerOrderTests(unittest.TestCase):
    """Recorded insertion order survives, and a new key is appended."""

    def test_an_existing_entry_increments_in_place(self) -> None:
        seeded(ledger={"500": 3, "1001": 2, "600": 9})
        combat_now(intent(item_id=UNIT_RESURRECTABLE))
        self.assertEqual(
            list(ledger_now()), ["500", "1001", "600"], "the key order is unchanged"
        )
        self.assertEqual(ledger_now(), {"500": 3, "1001": 3, "600": 9})

    def test_an_absent_entry_is_created_at_the_end(self) -> None:
        seeded(ledger={"500": 3, "600": 9})
        combat_now(intent(item_id=UNIT_RESURRECTABLE))
        self.assertEqual(list(ledger_now()), ["500", "600", "1001"])
        self.assertEqual(ledger_now(), {"500": 3, "600": 9, "1001": 1})

    def test_the_persisted_file_keeps_the_recorded_order(self) -> None:
        seeded(ledger={"500": 3, "600": 9})
        combat_now(intent(item_id=UNIT_RESURRECTABLE))
        persisted = corpus_save()["privateState"][combat_envelope.LEDGER_KEY]
        self.assertEqual(list(persisted), ["500", "600", "1001"])


# ------------------------------------------------------------- kill / kill_iid --
class KillTests(unittest.TestCase):
    """``kill`` deletes the addressed row and NEVER touches the ledger."""

    def test_the_addressed_row_is_deleted_and_the_ledger_stays(self) -> None:
        before = snapshot()
        response = combat_now(intent(action="kill", map_key=int(COMMITTED_KEY)))
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["command"], combat_envelope.KILL_COMMAND)
        self.assertEqual(body["destruction"]["derived_key"], COMMITTED_KEY)
        self.assertEqual(body["destruction"]["count"], 1)
        self.assertFalse(body["ledger_written"])
        self.assertNotIn(COMMITTED_KEY, items_now())
        self.assertEqual(
            items_now(),
            {
                key: row
                for key, row in before["items"].items()
                if key != COMMITTED_KEY
            },
            "every other row is byte-identical",
        )
        self.assertEqual(ledger_now(), before["ledger"])
        self.assertEqual(body["changed"], ["/maps/0/items/%s" % COMMITTED_KEY])

    def test_the_kill_contract_is_reported_on_the_answer(self) -> None:
        bare()
        before = snapshot()
        body = combat_now(
            intent(action="kill", map_key=int(COMMITTED_KEY))
        ).get_json()
        contract = body["kill_contract"]
        self.assertEqual(contract, combat_envelope.KILL_CONTRACT)
        self.assertTrue(contract["deletes_addressed_row"])
        self.assertFalse(contract["reaches_ledger"])
        self.assertEqual(contract["ledger_references"], 0)
        self.assertIn("divergence and not parity", contract["missing_row_behaviour"])
        self.assertIsNone(body["kill_iid_contract"])
        for name in RESOURCE_NAMES:
            self.assertEqual(body["resources"][name], before["resources"][name])

    def test_a_committed_team_three_row_is_also_removable(self) -> None:
        # `kill` is type- and team-agnostic: it deletes whatever stands at the
        # key, which is why the live phase can use the committed Command Center.
        before = snapshot()
        key = next(
            str(key)
            for key, row in before["items"].items()
            if row[combat_envelope.SLOT_PLAYER] == 3
        )
        body = combat_now(intent(action="kill", map_key=int(key))).get_json()
        self.assertEqual(body["destruction"]["derived_key"], key)
        self.assertNotIn(key, items_now())
        self.assertEqual(ledger_now(), before["ledger"])


class KillIidTests(unittest.TestCase):
    """``kill_iid`` is delivered as a proven no-op, not refused (design D5)."""

    def test_the_no_op_changes_nothing_and_succeeds(self) -> None:
        before = seeded()
        response = combat_now(intent(action="kill_iid", item_id=UNIT_RESURRECTABLE))
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["command"], combat_envelope.KILL_IID_COMMAND)
        self.assertEqual(body["destruction"]["count"], 0)
        self.assertEqual(body["destruction"]["rows_after"], body["destruction"]["rows_before"])
        self.assertIsNone(body["destruction"]["derived_key"])
        self.assertIsNone(body["destruction"]["derived_row"])
        self.assertFalse(body["ledger_written"])
        self.assertEqual(body["changed"], [], "a proven no-op changes nothing")
        self.assertEqual(items_now(), before["items"])
        self.assertEqual(ledger_now(), before["ledger"])
        self.assertEqual(
            corpus_save(),
            json.loads(before["bytes"].decode("utf-8")),
            "the persisted document is identical, not merely equivalent",
        )
        # The raw BYTES cannot be compared here: the legacy batch's own
        # `save_session` re-serialises the document with its own newline
        # convention, so even a proven no-op rewrites the file.  The document
        # comparison above is the claim that matters; this comment records why
        # the stronger byte form is unavailable rather than leaving the weaker
        # check silently in its place.

    def test_the_no_op_contract_is_proven_from_the_branch_not_one_request(self) -> None:
        seeded()
        body = combat_now(intent(action="kill_iid", item_id=UNIT_RESURRECTABLE)).get_json()
        contract = body["kill_iid_contract"]
        self.assertEqual(contract, combat_envelope.KILL_IID_CONTRACT)
        self.assertEqual(contract["local_bindings"], ["item_id", "reason_str"])
        self.assertFalse(contract["statement_writes_save_state"])
        self.assertEqual(contract["mutates"], [])
        self.assertFalse(contract["resources_move"])
        self.assertEqual(contract["delivered"], "as a proven no-op")
        self.assertEqual(contract["not_delivered"], "as a refusal")
        self.assertFalse(contract["reaches_ledger"])
        self.assertIn("WRITES NOTHING", contract["why"])
        self.assertIsNone(body["kill_contract"])

    def test_it_is_reachable_for_an_identity_with_no_placed_row(self) -> None:
        before = seeded()
        response = combat_now(intent(action="kill_iid", item_id=UNIT_FLAG_ABSENT))
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(items_now(), before["items"])


# ------------------------------------- the client-dictated destruction refusal --
class ClientDictatedDestructionTests(unittest.TestCase):
    """Design D2: a named, separate refusal reached before anything else."""

    def assertRefused(
        self, payload: Dict[str, Any], code: str, status: int = 400
    ) -> Dict[str, Any]:
        before = snapshot()
        response = combat_now(payload)
        self.assertEqual(response.status_code, status, response.get_json())
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(
            sorted(body.keys()),
            ["error", "ok", "protocol"],
            "a refusal carries an EMPTY payload: no state field at all",
        )
        self.assertEqual(sorted(body["error"].keys()), ["code", "message"])
        after = snapshot()
        self.assertEqual(after["items"], before["items"], "no row moved")
        self.assertEqual(after["ledger"], before["ledger"])
        self.assertEqual(after["resources"], before["resources"])
        self.assertEqual(after["bytes"], before["bytes"], "the corpus file is unchanged")
        return body

    def test_every_destruction_count_key_is_refused(self) -> None:
        seeded()
        for key in combat_envelope.DESTRUCTION_COUNT_KEYS:
            with self.subTest(key=key):
                payload = intent(item_id=UNIT_RESURRECTABLE)
                payload[key] = 5
                self.assertRefused(payload, "client_dictated_destruction")

    def test_both_subtraction_operands_are_refused(self) -> None:
        seeded()
        for key in combat_envelope.SENT_SURVIVED_KEYS:
            with self.subTest(key=key):
                payload = intent(item_id=UNIT_RESURRECTABLE)
                payload[key] = 1
                self.assertRefused(payload, "client_dictated_destruction")

    def test_every_derived_legacy_payload_key_is_refused(self) -> None:
        seeded()
        inventory = combat_envelope.derive_field_inventory()
        self.assertTrue(inventory["ok"])
        for key in inventory["key_names"]:
            with self.subTest(key=key):
                payload = intent(item_id=UNIT_RESURRECTABLE)
                payload[key] = {"anything": True}
                self.assertRefused(payload, "client_dictated_destruction")

    def test_the_refusal_is_separate_from_the_eligibility_check(self) -> None:
        # The SAME request without the client count resolves successfully, so the
        # two refusals cannot be one another.
        seeded()
        payload = intent(item_id=UNIT_RESURRECTABLE)
        payload["lost"] = 5
        body = self.assertRefused(payload, "client_dictated_destruction")
        self.assertIn("client-supplied combat payload keys", body["error"]["message"])
        self.assertNotEqual(
            body["error"]["code"],
            "no_eligible_row",
            "D2: a separate, NAMED refusal -- never the eligibility check",
        )
        self.assertEqual(
            combat_envelope.REFUSALS[0]["refusal"], "client_dictated_destruction"
        )
        self.assertTrue(combat_envelope.REFUSALS[0]["implemented"])

    def test_it_fires_before_the_addressing_is_required(self) -> None:
        seeded()
        body = self.assertRefused(
            {"user_id": PID, "action": "resolve", "lost": 3},
            "client_dictated_destruction",
        )
        self.assertNotEqual(
            body["error"]["code"],
            "missing_item_id",
            "step 2 precedes step 3, so no addressing is demanded",
        )

    def test_it_fires_before_any_player_state_is_read(self) -> None:
        # An identity that could never resolve AND a client count: the count
        # refusal wins, so no player state was consulted to reach it.
        before = snapshot()
        response = combat_now({"user_id": PID, "action": "resolve", "item_id": 0, "sent": 1})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"], "client_dictated_destruction"
        )
        self.assertEqual(snapshot()["bytes"], before["bytes"])

    def test_it_works_on_every_action(self) -> None:
        seeded()
        for action, addressing in (
            ("resolve", {"item_id": UNIT_RESURRECTABLE}),
            ("kill", {"map_key": int(COMMITTED_KEY)}),
            ("kill_iid", {"item_id": UNIT_RESURRECTABLE}),
        ):
            with self.subTest(action=action):
                payload = intent(action=action, **addressing)
                payload["survived"] = 0
                self.assertRefused(payload, "client_dictated_destruction")


# -------------------------------------------------------- the other refusals --
class RefusalTests(unittest.TestCase):
    """Every other refusal: a named code, an empty payload, no state change."""

    def assertRefused(
        self, payload: Dict[str, Any], code: str, status: int = 409
    ) -> Dict[str, Any]:
        before = snapshot()
        response = combat_now(payload)
        self.assertEqual(response.status_code, status, response.get_json())
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(sorted(body.keys()), ["error", "ok", "protocol"])
        self.assertEqual(sorted(body["error"].keys()), ["code", "message"])
        after = snapshot()
        self.assertEqual(after["items"], before["items"], "no row moved")
        self.assertEqual(after["ledger"], before["ledger"])
        self.assertEqual(after["resources"], before["resources"])
        self.assertEqual(after["bytes"], before["bytes"])
        return body

    def test_the_action_vocabulary_is_closed(self) -> None:
        bare()
        for action in ("attack", "End_Attack", "resolve ", "", None, 1, True):
            with self.subTest(action=action):
                response = combat_now(
                    {"user_id": PID, "action": action, "item_id": UNIT_RESURRECTABLE}
                )
                self.assertEqual(response.status_code, 400, response.get_json())
                self.assertEqual(
                    response.get_json()["error"]["code"], "invalid_action"
                )

    def test_a_missing_action_is_named(self) -> None:
        before = snapshot()
        response = combat_now({"user_id": PID, "item_id": UNIT_RESURRECTABLE})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_action")
        self.assertEqual(snapshot()["items"], before["items"])

    def test_each_action_requires_its_own_addressing(self) -> None:
        bare()
        for action, code in (
            ("resolve", "missing_item_id"),
            ("kill", "missing_map_key"),
            ("kill_iid", "missing_item_id"),
        ):
            with self.subTest(action=action):
                response = combat_now({"user_id": PID, "action": action})
                self.assertEqual(response.status_code, 400, response.get_json())
                self.assertEqual(response.get_json()["error"]["code"], code)

    def test_an_ill_typed_addressing_is_refused_and_not_coerced(self) -> None:
        bare()
        for action, key in (
            ("resolve", "item_id"),
            ("kill", "map_key"),
            ("kill_iid", "item_id"),
        ):
            for value in ("1", 1.0, True, None, [1], {"id": 1}):
                with self.subTest(action=action, key=key, value=value):
                    response = combat_now(
                        intent(action=action, **{key: value})
                    )
                    self.assertEqual(response.status_code, 400, response.get_json())
                    self.assertEqual(
                        response.get_json()["error"]["code"],
                        "invalid_item_id" if key == "item_id" else "invalid_map_key",
                    )

    def test_the_committed_corpus_places_no_unit_row_so_resolve_refuses(self) -> None:
        bare()
        body = self.assertRefused(
            intent(item_id=UNIT_RESURRECTABLE), "no_eligible_row"
        )
        self.assertIn("slot 0 equals the item id", body["error"]["message"])
        self.assertIn("truthy", body["error"]["message"])

    def test_kill_at_an_absent_key_is_refused(self) -> None:
        bare()
        body = self.assertRefused(
            intent(action="kill", map_key=ABSENT_MAP_KEY), "unaddressable_row", 409
        )
        self.assertIn(
            "divergence and not parity",
            combat_envelope.KILL_CONTRACT["missing_row_behaviour"],
        )
        self.assertIn("answers success", body["error"]["message"])

    def test_an_unreadable_ledger_is_reported_not_defaulted(self) -> None:
        for raw in (None, [], "1001", 5, {1001: 1}, {"1001": "1"}, {"1001": True}):
            with self.subTest(ledger=raw):
                reset_placements()
                set_ledger({})
                seed_row(SEEDED_FIRST, UNIT_RESURRECTABLE)
                save = save_now()
                save["privateState"][combat_envelope.LEDGER_KEY] = raw
                write_corpus(save)
                before = snapshot()
                response = combat_now(intent(item_id=UNIT_RESURRECTABLE))
                self.assertEqual(response.status_code, 500, response.get_json())
                self.assertEqual(
                    response.get_json()["error"]["code"], "unresolvable_ledger"
                )
                self.assertEqual(snapshot()["items"], before["items"])

    def test_an_unknown_user_is_refused(self) -> None:
        seeded()
        response = combat_now(
            {"user_id": "does-not-exist-0000", "action": "kill_iid", "item_id": UNIT_RESURRECTABLE}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "unknown_user_id")

    def test_a_missing_or_non_object_body_is_refused(self) -> None:
        with harness.offline():
            response = CLIENT.post("/v0/combat", data="not json")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_payload")
        with harness.offline():
            response = CLIENT.post("/v0/combat", json={})  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_user_id")

    def test_every_conflict_reason_is_declared_and_mapped(self) -> None:
        self.assertEqual(
            {entry["refusal"] for entry in combat_envelope.REFUSALS},
            {
                "client_dictated_destruction",
                "combat_resolution",
                "no_cost_or_reward",
                "syringe_cost",
                "placement_validation",
            },
        )
        self.assertEqual(len(combat_envelope.REFUSALS), 5)
        # The refusal / non-rule split: exactly ONE entry is an enforced guard,
        # and the four `implemented: False` entries are deliberate omissions.
        enforced = [
            entry for entry in combat_envelope.REFUSALS if entry["implemented"]
        ]
        self.assertEqual(len(enforced), 1)
        self.assertEqual(enforced[0]["refusal"], "client_dictated_destruction")


# ------------------------------------------------- the post-execution proof --
class PostExecutionProofFailureTests(unittest.TestCase):
    """Each proof half fails closed rather than reporting the legacy success."""

    def assertFailsClosed(self, result: Result, needle: str) -> Dict[str, Any]:
        self.assertEqual(result.status_code, 500, result.get_json())
        body = result.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn(needle, body["error"]["message"])
        self.assertEqual(sorted(body.keys()), ["error", "ok", "protocol"])
        return body

    # --- half (a): the placements -------------------------------------------
    def test_a_row_that_survived_the_destruction_fails_closed(self) -> None:
        seeded()

        def restored(items: Dict[str, Any]) -> Dict[str, Any]:
            items[SEEDED_FIRST] = [UNIT_RESURRECTABLE, 1, 1, 0, 0, [], {}, 1]
            return items

        result = post_with("map_items", restored, intent(item_id=UNIT_RESURRECTABLE))
        self.assertFailsClosed(result, "the only permitted difference is the derived key")

    def test_a_second_row_being_destroyed_fails_closed(self) -> None:
        seeded(second=True)

        def doubled(items: Dict[str, Any]) -> Dict[str, Any]:
            items.pop(SEEDED_SECOND, None)
            return items

        result = post_with("map_items", doubled, intent(item_id=UNIT_RESURRECTABLE))
        self.assertFailsClosed(result, "the placement set is")

    def test_a_neighbouring_row_that_changed_fails_closed(self) -> None:
        seeded()

        def moved(items: Dict[str, Any]) -> Dict[str, Any]:
            items[COMMITTED_KEY] = list(items[COMMITTED_KEY])
            items[COMMITTED_KEY][combat_envelope.SLOT_CELL_X] = 77
            return items

        result = post_with("map_items", moved, intent(item_id=UNIT_RESURRECTABLE))
        self.assertFailsClosed(result, "destroys the derived row and rewrites nothing else")

    def test_every_neighbouring_row_is_checked(self) -> None:
        for victim in ("1", "20", "21", "40"):
            with self.subTest(placement=victim):
                seeded()

                def moved(
                    items: Dict[str, Any], key: str = victim
                ) -> Dict[str, Any]:
                    items[key] = list(items[key])
                    items[key][combat_envelope.SLOT_CELL_Y] = 12345
                    return items

                result = post_with("map_items", moved, intent(item_id=UNIT_RESURRECTABLE))
                self.assertFailsClosed(result, "placement %s changed" % victim)

    # --- half (b): the ledger ------------------------------------------------
    def test_a_reordered_ledger_fails_closed(self) -> None:
        seeded(ledger={"500": 3, "1001": 2})

        def reordered(save: Dict[str, Any]) -> Dict[str, Any]:
            bag = save["privateState"][combat_envelope.LEDGER_KEY]
            save["privateState"][combat_envelope.LEDGER_KEY] = {
                key: bag[key] for key in reversed(list(bag))
            }
            return save

        result = post_with("save_document", reordered, intent(item_id=UNIT_RESURRECTABLE))
        self.assertFailsClosed(result, "key order is")

    def test_a_wrong_ledger_value_fails_closed(self) -> None:
        seeded(ledger={"500": 3, "1001": 2})

        def wrong(save: Dict[str, Any]) -> Dict[str, Any]:
            save["privateState"][combat_envelope.LEDGER_KEY]["1001"] = 99
            return save

        result = post_with("save_document", wrong, intent(item_id=UNIT_RESURRECTABLE))
        self.assertFailsClosed(result, "not the derived")

    def test_a_ledger_that_grew_a_key_while_both_gates_declined_fails_closed(self) -> None:
        seeded(item_id=UNPLACED_BUILDING)

        def invented(save: Dict[str, Any]) -> Dict[str, Any]:
            save["privateState"][combat_envelope.LEDGER_KEY]["23"] = 1
            return save

        result = post_with("save_document", invented, intent(item_id=UNPLACED_BUILDING))
        self.assertFailsClosed(result, "key order is")

    def test_a_ledger_that_moved_a_value_while_both_gates_declined_fails_closed(self) -> None:
        seeded(item_id=UNPLACED_BUILDING, ledger={"500": 3})

        def moved(save: Dict[str, Any]) -> Dict[str, Any]:
            save["privateState"][combat_envelope.LEDGER_KEY]["500"] = 4
            return save

        result = post_with("save_document", moved, intent(item_id=UNPLACED_BUILDING))
        self.assertFailsClosed(result, "ledger['500'] is 4")

    def test_the_declined_write_need_no_third_ledger_guard(self) -> None:
        """Both halves above SUBSUME a 'the ledger moved' guard; none is kept.

        Measured, not assumed.  When both gates decline the derived entry set is
        the pre-execution set value for value, so the ORDER half rejects any added,
        removed, or re-ordered key and the VALUE half rejects any changed value.
        Together they make ``ledger_after == ledger_snapshot`` the only reachable
        outcome, which is why the route carries no third check and a guard for it
        would be unreachable rather than defensive.  Both arms are exercised above
        so this claim is measured on every run instead of trusted.
        """
        self.assertNotIn(
            "while both gates declined",
            Path(compat_service.__file__).read_text(encoding="utf-8"),
            "the unreachable third ledger guard is not in the route either",
        )
        # And the derivation that makes it unreachable: a declined write returns
        # the pre-execution entry set unchanged, including when the identity is
        # ALREADY present -- the case where a buggy `+=` would have moved it.
        entries = combat_envelope.expected_ledger_increment(
            {"12": 3}, UNPLACED_BUILDING, combat_envelope.PLAYER_TEAM, None
        )
        self.assertFalse(entries["written"])
        self.assertEqual(entries["entries"], {"12": 3})
        self.assertTrue(entries["present_before"])
        self.assertEqual(entries["count_before"], 3)
        self.assertEqual(entries["count_after"], 3)

    def test_a_ledger_that_appeared_fails_closed(self) -> None:
        seeded()
        save = save_now()
        del save["privateState"][combat_envelope.LEDGER_KEY]
        write_corpus(save)
        before = items_now()
        # An absent ledger is refused BEFORE dispatch, so nothing is executed and
        # the proof is never reached -- which is the ordering claim itself.
        response = combat_now(intent(item_id=UNIT_RESURRECTABLE))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "unresolvable_ledger")
        self.assertEqual(items_now(), before)

    def test_a_non_object_ledger_after_execution_fails_closed(self) -> None:
        seeded()

        def broken(save: Dict[str, Any]) -> Dict[str, Any]:
            save["privateState"][combat_envelope.LEDGER_KEY] = ["1001"]
            return save

        result = post_with("save_document", broken, intent(item_id=UNIT_RESURRECTABLE))
        self.assertFailsClosed(result, "after execution")

    # --- half (c): the resources ---------------------------------------------
    def test_any_moved_resource_fails_closed(self) -> None:
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                seeded()

                def moved(values: Dict[str, int], key: str = name) -> Dict[str, int]:
                    out = dict(values)
                    out[key] = out[key] + 1
                    return out

                result = post_with("resources", moved, intent(item_id=UNIT_RESURRECTABLE))
                self.assertFailsClosed(result, "moves no resource")

    def test_a_resource_missing_from_one_side_fails_closed(self) -> None:
        seeded()

        def dropped(values: Dict[str, int]) -> Dict[str, int]:
            out = dict(values)
            out.pop("gold")
            return out

        result = post_with("resources", dropped, intent(item_id=UNIT_RESURRECTABLE))
        self.assertFailsClosed(result, "the FULL resource set, never a subset")

    def test_a_client_vector_cannot_smuggle_a_resource(self) -> None:
        seeded()
        before = resources_now()
        payload = intent(item_id=UNIT_RESURRECTABLE)
        # A vector under a name the D2 refusal does not own is still ignored:
        # the endpoint never reads it, and the derived vector is the neutral one.
        payload["resource_delta"] = {"gold": 1000000}
        body = combat_now(payload).get_json()
        self.assertEqual(resources_now(), before)
        for name in RESOURCE_NAMES:
            self.assertEqual(body["resources"][name], before[name])

    # --- half (d): the row count, checked LAST -------------------------------
    def test_the_row_count_half_is_checked_after_the_key_set_half(self) -> None:
        seeded(second=True)
        # A stub that both removes a second row and would leave the count wrong.
        # The KEY-SET half must be the one that fires, which is what "count last"
        # means in practice.
        def doubled(items: Dict[str, Any]) -> Dict[str, Any]:
            items.pop(SEEDED_SECOND, None)
            return items

        result = post_with("map_items", doubled, intent(item_id=UNIT_RESURRECTABLE))
        body = self.assertFailsClosed(result, "the placement set is")
        self.assertNotIn("placed rows after execution", body["error"]["message"])

    def test_the_row_count_half_is_independently_reachable(self) -> None:
        seeded()
        # The key-set half already pins the number of removed keys, so the count
        # half can only fire when the DERIVED count disagrees with it. Perturbing
        # the derivation alone reaches it, and the row really was destroyed --
        # so this is the one case where the count half is the sole failure.
        result = post_with_derived_destruction(
            0, intent(item_id=UNIT_RESURRECTABLE)
        )
        body = self.assertFailsClosed(result, "placed rows after execution")
        self.assertIn("41", body["error"]["message"])
        self.assertIn("not the derived 41", body["error"]["message"])

    def test_the_count_half_agrees_with_the_key_set_half_for_every_action(self) -> None:
        # The redundancy claim, asserted rather than asserted-in-prose: for every
        # action the derived destruction is 0 or 1 and the derived key is absent
        # exactly then, so the two halves can never disagree on a reachable path.
        for action, addressing in (
            ("resolve", {"item_id": UNIT_RESURRECTABLE}),
            ("kill", {"map_key": int(COMMITTED_KEY)}),
            ("kill_iid", {"item_id": UNIT_RESURRECTABLE}),
        ):
            with self.subTest(action=action):
                seeded()
                response = combat_now(intent(action=action, **addressing))
                body = response.get_json()
                removed = 0 if body["destruction"]["derived_key"] is None else 1
                self.assertEqual(
                    body["destruction"]["count"],
                    removed,
                    "the derived count equals the derived key-set difference",
                )
                self.assertIn(body["destruction"]["count"], (0, 1))


# --------------------------------------------------- the recorded non-rules --
class RecordedNonRuleTests(unittest.TestCase):
    """Each deliberate omission carries a specific reason and is marked False."""

    def test_no_combat_is_recorded_with_its_reason(self) -> None:
        self.assertIn("NO COMBAT IS RESOLVED", combat_envelope.NO_COMBAT)
        for field in ("attack", "defense", "life", "attack_interval", "attack_range"):
            self.assertIn(field, combat_envelope.NO_COMBAT)
        self.assertIn("godot-mission-vocabulary", combat_envelope.NO_COMBAT)

    def test_no_cost_or_reward_is_recorded_with_its_reason(self) -> None:
        self.assertIn("NO HONOUR, REWARD, OR RESOURCE MOVEMENT", combat_envelope.NO_COST_OR_REWARD)
        for field in ("honor", "resources", "resources_victim", "townhall_gold"):
            self.assertIn(field, combat_envelope.NO_COST_OR_REWARD)
        self.assertIn("EVERY stored resource", combat_envelope.NO_COST_OR_REWARD)

    def test_no_syringe_cost_is_recorded_with_its_reason(self) -> None:
        self.assertIn("NO SYRINGE COST IS CHARGED", combat_envelope.NO_SYRINGE_COST)
        self.assertIn("zero legacy consumers", combat_envelope.NO_SYRINGE_COST)

    def test_no_placement_validation_is_added(self) -> None:
        self.assertIn(
            "NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED",
            combat_envelope.NO_PLACEMENT_VALIDATION,
        )
        self.assertIn("M13", combat_envelope.NO_PLACEMENT_VALIDATION)

    def test_the_client_count_refusal_names_the_bad_pattern(self) -> None:
        self.assertIn("REFUSED, NEVER REPRODUCED", combat_envelope.CLIENT_DICTATED_REFUSAL)
        self.assertIn("max(0, unit[2] - unit[3])", combat_envelope.CLIENT_DICTATED_REFUSAL)
        self.assertIn("EXHAUSTION OF MATCHES", combat_envelope.REFUSED_COUNT_NOTE)

    def test_the_printed_count_is_recorded_as_a_request_not_an_outcome(self) -> None:
        self.assertIn("REPORTS WHAT THE CLIENT ASKED FOR", combat_envelope.PRINTED_COUNT_IS_A_REQUEST)
        self.assertIn("923", combat_envelope.PRINTED_COUNT_IS_A_REQUEST)

    def test_the_validation_order_places_the_write_at_step_nine(self) -> None:
        self.assertEqual(combat_envelope.DESTRUCTION_STEP, 9)
        steps = [entry["step"] for entry in combat_envelope.VALIDATION_ORDER]
        self.assertEqual(steps, list(range(1, 11)))
        write = next(
            entry for entry in combat_envelope.VALIDATION_ORDER
            if entry["check"] == "destruction"
        )
        self.assertEqual(write["resolves"], "THE WRITE STEP")
        after = combat_envelope.VALIDATION_ORDER[9]
        self.assertEqual(after["resolves"], "after dispatch")
        for entry in combat_envelope.VALIDATION_ORDER[:8]:
            self.assertEqual(entry["resolves"], "before dispatch")

    def test_the_ordering_rule_records_the_measured_batch_boundary(self) -> None:
        self.assertIn("the persistence boundary is the BATCH", combat_envelope.ORDERING_RULE)
        self.assertIn("command.py:874", combat_envelope.ORDERING_RULE)


# ----------------------------------------------------------------- the corpus --
class CommittedCorpusTests(unittest.TestCase):
    """The committed corpus's own measurement -- why ``resolve`` needs seeding."""

    def test_the_committed_corpus_places_forty_building_rows(self) -> None:
        seed = harness.load_seed()
        items = seed["maps"][0]["items"]
        self.assertEqual(len(items), COMMITTED_PLACEMENTS)
        types = {
            int(row["id"]): row.get("type")
            for row in BOOT.config()["items"]  # type: ignore[union-attr]
            if isinstance(row, dict)
        }
        unit_rows = [
            int(row[0]) for row in items.values() if types.get(int(row[0])) == "u"
        ]
        self.assertEqual(
            unit_rows, [], "the committed corpus places NO unit row at all"
        )

    def test_the_committed_corpus_is_split_across_two_teams(self) -> None:
        seed = harness.load_seed()
        items = seed["maps"][0]["items"]
        teams = {}
        for row in items.values():
            teams[row[combat_envelope.SLOT_PLAYER]] = (
                teams.get(row[combat_envelope.SLOT_PLAYER], 0) + 1
            )
        self.assertEqual(teams, {1: COMMITTED_TEAM_ONE_ROWS, 3: COMMITTED_TEAM_THREE_ROWS})

    def test_the_committed_ledger_is_present_and_empty(self) -> None:
        seed = harness.load_seed()
        self.assertIn(combat_envelope.LEDGER_KEY, seed["privateState"])
        self.assertEqual(seed["privateState"][combat_envelope.LEDGER_KEY], {})

    def test_the_committed_identities_are_measured_from_the_loaded_config(self) -> None:
        rows = {
            int(row["id"]): row
            for row in BOOT.config()["items"]  # type: ignore[union-attr]
            if isinstance(row, dict)
        }
        self.assertEqual(rows[UNIT_RESURRECTABLE].get("type"), "u")
        self.assertEqual(rows[UNIT_FLAG_ABSENT].get("type"), "u")
        self.assertEqual(rows[UNPLACED_BUILDING].get("type"), "b")
        self.assertEqual(
            combat_envelope.committed_resurrectable(
                rows[UNIT_RESURRECTABLE][combat_envelope.PROPERTIES_FIELD]
            ),
            1,
        )
        self.assertIsNone(
            combat_envelope.committed_resurrectable(
                rows[UNIT_FLAG_ABSENT][combat_envelope.PROPERTIES_FIELD]
            ),
            "the flag is ABSENT on this unit, not zero",
        )
        self.assertIsNone(
            combat_envelope.committed_resurrectable(
                rows[UNPLACED_BUILDING][combat_envelope.PROPERTIES_FIELD]
            )
        )

    def test_each_committed_identity_used_here_is_placed_once(self) -> None:
        """The premise of the recorded-order case, MEASURED rather than assumed.

        The first draft of that case named committed building 23 as "placed at map
        key 3" -- true, and also true of eleven other keys, so the eligible set had
        eleven committed rows and the expectation was simply wrong.  This test is
        the guard that makes that class of mistake fail here rather than as a
        confusing assertion diff.
        """
        items = harness.load_seed()["maps"][0]["items"]
        for item_id in (
            COMMITTED_ITEM,
            UNIT_RESURRECTABLE,
            UNIT_FLAG_ABSENT,
            UNPLACED_BUILDING,
        ):
            with self.subTest(item_id=item_id):
                keys = [
                    key for key, row in items.items() if int(row[0]) == int(item_id)
                ]
                self.assertLessEqual(
                    len(keys), 1,
                    "item %s is placed at %r; a multi-key identity cannot carry the "
                    "recorded-order precedence case" % (item_id, keys),
                )

    def test_the_committed_row_shape_matches_the_slot_constants(self) -> None:
        seed = harness.load_seed()
        for key, row in seed["maps"][0]["items"].items():
            with self.subTest(placement=key):
                self.assertEqual(len(row), combat_envelope.MAP_ROW_SLOTS)
                self.assertIsInstance(row[combat_envelope.SLOT_ITEM_ID], int)
                self.assertIn(
                    row[combat_envelope.SLOT_PLAYER], (1, 3),
                    "every committed row is on a team the ledger gate can read",
                )


if __name__ == "__main__":
    unittest.main()
