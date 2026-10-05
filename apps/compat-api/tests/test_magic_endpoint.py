#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/magic`` endpoint tests (OpenSpec ``godot-damage``).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so this suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across every magic execution.

**What this route delivers, and what the refusal is for.**  One call carries
exactly one legacy command through the **unchanged** dispatcher --
``buy_magic`` or ``use_magic`` -- and moves exactly one number: the counter the
request's magic identity names.  It applies **no** damage, **no** effect, and
**no** price, because none is reachable: the ten committed magics have zero
legacy consumers, the ledger has zero readers, and the one committed field that
would have carried a magnitude (``Attack Boost``) never records a multiplier.

**The refusal order is the contract, and it is asserted as one.**  All eight of
:meth:`magic_envelope.project_magic`'s checks resolve before the dispatch, so a
refused request provably leaves the whole recorded document byte-identical --
and this suite asserts that per refusal reason rather than trusting the claim.

**The committed corpus exercises the interesting arms, and this is measured.**
``tests/saves/fresh-player.json`` records an **empty** ledger, so its own first
counter is the ``else``-arm divergence; every other arm -- a present counter, the
recorded literal cap, an above-cap counter, an unreadable ledger, an unreadable
counter -- is reached by writing the **disposable corpus only**, exactly as the
delivered combat suite seeds its own disagreement states.  That seeding is a test
mechanism, never the executed-legacy fixture (which lives under
``tests/fixtures/godot-damage/``), and it never touches a committed save.

**How the post-execution proof halves are exercised.**  Each stub rewrites only
the read that happens **after** ``execute_commands`` returned, detected by
wrapping the boot's own ``execute_commands`` rather than by counting accessor
calls -- ``LegacyBoot.resources`` itself calls ``save_document`` internally, so
a call-counting stub would rewrite the *pre*-execution read and silently test
something else.  The transform receives a **deep copy**, so a proof-failure test
never corrupts the recorded corpus file it is asserted against elsewhere.

Covered:

* **a successful counter transition** -- both actions, a present and an absent
  key, the recorded literal cap, with the persisted corpus matching the response
  and **every one of the eight stored resources unchanged**.
* **the divergence between the derived transition and the recorded one** -- the
  suite pins that design D5's "changed by exactly the derived delta" is
  **unreachable by construction** here, and pins the two helpers that disagree so
  a future edit that quietly reconciled them would fail rather than pass.
* **the client-dictated-count refusal** -- all eleven count keys, the four
  protocol keys that are actually refused, and the **two that are not**, which is
  a measured defect in the shared envelope recorded here because the envelope is
  single-source and must not be edited from this suite.
* **every other refusal** -- a closed action vocabulary, an absent, mistyped, or
  non-canonical identity, an identity outside the committed table, an unreadable
  ledger, an unreadable counter, and an above-cap counter -- each with its named
  code, an **empty** payload, and the corpus left **byte-identical**.
* **the post-execution proof** -- each of the eight resource slots individually,
  a missing slot, a wrong counter, a reordered ledger, a key that appeared, and
  the addressed key vanishing, each failing closed with ``internal_error``.
* **the recorded non-rules** -- no damage, no cost or reward, no magic effect, a
  ledger with no readers, and a cap that is a literal, each marked so a deliberate
  omission cannot be read as a gap.
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
import magic_envelope as M

SERVICE = Path(__file__).resolve().parents[1] / "compat_service.py"

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed fresh-player corpus records an EMPTY ledger, so nothing in the
# committed state exercises a present counter.  These are the arms, each named
# for the branch behaviour it reaches.
PRESENT = 2
AT_CAP_MINUS_ONE = 49
AT_CAP = 50
ABOVE_CAP = 63
ABSENT_KEY = 3

#: What the UNCHANGED legacy ``buy_magic`` arm writes for a recorded
#: before of :data:`PRESENT`: ``before + min(cap, before + 1)``, which is
#: ``2 + 3`` -- never ``2 + 1``, which is the derived transition.
LEGACY_BUY_AFTER = PRESENT + (PRESENT + 1)

#: A committed magic identity the fresh-player corpus does NOT key, so the
#: ``else`` arm is reached without any seeding beyond the recorded empty ledger.
COMMITTED_ID = 1

#: An identity inside the committed 1..10 table but a float on the wire, which is
#: what ``str()`` would key on -- the recorded second-ledger-key defect.
FLOAT_ID = 3

#: Outside the committed table entirely, so ``unknown_magic_id`` is a content
#: refusal rather than a shape one.
UNCOMMITTED_ID = 99

#: The eight stored resource slots the proof compares.  Seven come from
#: ``LegacyBoot.resources``; ``energy`` does not, and its absence there is the
#: reason the eighth slot has to be read off the document.
RESOURCE_NAMES = M.RESOURCE_NAMES
ACCESSOR_RESOURCE_NAMES = tuple(
    name for name in RESOURCE_NAMES if name != "energy"
)
DOCUMENT_ONLY_RESOURCE = "energy"


# ------------------------------------------------------------- corpus seeding --
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


def ledger_now() -> Any:
    private = save_now().get(M.PRIVATE_STATE_KEY)
    if not isinstance(private, dict):
        return None
    return private.get(M.LEDGER_KEY)


def resources_now() -> Dict[str, Any]:
    """All **eight** stored slots, the same set the route's proof compares."""
    slots: Dict[str, Any] = dict(BOOT.resources(PID))  # type: ignore[union-attr]
    private = save_now().get(M.PRIVATE_STATE_KEY)
    if isinstance(private, dict) and DOCUMENT_ONLY_RESOURCE in private:
        slots[DOCUMENT_ONLY_RESOURCE] = private[DOCUMENT_ONLY_RESOURCE]
    return slots


def snapshot() -> Dict[str, Any]:
    return {
        "ledger": copy.deepcopy(ledger_now()),
        "resources": resources_now(),
        "bytes": save_path().read_bytes(),
    }


def bare() -> Dict[str, Any]:
    """Reset the disposable ledger to the committed corpus's own empty state."""
    save = save_now()
    save[M.PRIVATE_STATE_KEY][M.LEDGER_KEY] = {}
    write_corpus(save)
    return snapshot()


def seeded(ledger: Any) -> Dict[str, Any]:
    """Reset the disposable ledger to a caller-chosen recorded state.

    Written in memory **and** through the corpus file, because the legacy branch
    mutates ``privateState["magics"]`` in place and the byte-identity assertions
    compare the persisted document.  Never a committed save.
    """
    save = save_now()
    save[M.PRIVATE_STATE_KEY][M.LEDGER_KEY] = ledger
    write_corpus(save)
    return snapshot()


def write_ledger_verbatim(raw: Any) -> None:
    """Write an **unreadable** ledger shape straight to the corpus file.

    Needed for the shapes ``json.dump`` cannot produce for a dict -- ``None``, a
    list, a string, a number -- because a save document has to hold them to be
    exercised at all.
    """
    with open(save_path(), "w", encoding="utf-8", newline="\n") as stream:
        document = save_now()
        document[M.PRIVATE_STATE_KEY][M.LEDGER_KEY] = raw
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
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a magic execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def magic_now(payload: Any) -> Any:
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/magic", json=payload)  # type: ignore[union-attr]


def intent(action: str = "buy", magic_id: Any = COMMITTED_ID, **extra: Any) -> Dict[str, Any]:
    """The whole contract: a save identity, an action, and one magic identity.

    There is deliberately **no** count parameter.  A caller that wants one passes
    it through ``extra``, which is how the refusal tests build their payloads.
    """
    payload: Dict[str, Any] = {"user_id": PID, "action": action, "magic_id": magic_id}
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
    count: ``_magic_snapshot`` calls ``save_document`` and then ``resources``,
    and ``resources`` itself calls ``save_document`` internally, so a
    call-counting stub rewrites the pre-execution ledger read instead of the
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
            return Result(app, app.test_client().post("/v0/magic", json=payload))


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
        private = document[M.PRIVATE_STATE_KEY]
        if value is _ABSENT:
            private.pop(DOCUMENT_ONLY_RESOURCE, None)
        else:
            private[DOCUMENT_ONLY_RESOURCE] = value
        return document

    return transform


class _Absent:
    """Sentinel: remove the slot rather than set it to a value."""


_ABSENT = _Absent()


# ----------------------------------------------------------- corpus integrity --
class CommittedCorpusTests(unittest.TestCase):
    """Measure the committed corpus instead of assuming what it contains."""

    def test_the_committed_ledger_is_empty_so_the_first_arm_is_the_else_arm(self) -> None:
        seed = harness.load_seed()
        self.assertEqual(seed[M.PRIVATE_STATE_KEY][M.LEDGER_KEY], {})
        self.assertEqual(len(bare()["bytes"]), len(save_path().read_bytes()))

    def test_the_committed_corpus_records_every_one_of_the_eight_slots(self) -> None:
        slots = bare()["resources"]
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

    def test_the_committed_magics_are_ten_rows_keyed_by_a_native_integer_id(self) -> None:
        magics = BOOT.config().get("magics")  # type: ignore[union-attr]
        self.assertIsInstance(magics, list)
        self.assertEqual(len(magics), M.COMMITTED_MAGIC_COUNT)
        ids = [row["id"] for row in magics]
        self.assertEqual(ids, list(range(1, M.COMMITTED_MAGIC_COUNT + 1)))
        self.assertEqual(min(ids), M.COMMITTED_MAGIC_ID_MIN)
        self.assertEqual(max(ids), M.COMMITTED_MAGIC_ID_MAX)
        self.assertEqual(len(set(ids)), len(ids), "no duplicate id")
        # Measured, not assumed: the loaded configuration is a LIST, so a dict
        # lookup would have raised.  The docstring records the list shape.
        for value in (COMMITTED_ID, FLOAT_ID, UNCOMMITTED_ID):
            with self.subTest(magic_id=value):
                row = compat_service._committed_magic(BOOT, value)  # type: ignore[arg-type]
                if value == UNCOMMITTED_ID:
                    self.assertIsNone(row)
                else:
                    self.assertEqual(row, magics[value - 1])
                    self.assertIsNot(
                        row, magics[value - 1],
                        "the accessor returns a copy, never the loaded row",
                    )


# ------------------------------------------------------- the successful path --
class SuccessfulCounterTests(unittest.TestCase):
    """Both actions through the real dispatcher, with the eight-slot proof."""

    def test_buy_adds_the_charges_the_unchanged_legacy_arm_adds(self) -> None:
        seeded({"1": PRESENT})
        response = magic_now(intent("buy", 1))
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["protocol"], "compat-v0")
        self.assertEqual(body["result"], "success")
        self.assertEqual(body["action"], "buy")
        self.assertEqual(body["command"], M.BUY_COMMAND)
        self.assertEqual(body["counter"]["ledger_key"], "1")
        self.assertEqual(body["counter"]["before"], PRESENT)
        self.assertEqual(body["counter"]["present_before"], True)
        self.assertEqual(body["counter"]["derived_after"], PRESENT + 1)
        self.assertEqual(body["counter"]["recorded_after"], LEGACY_BUY_AFTER)
        self.assertEqual(
            body["counter"]["legacy_expected_after"], LEGACY_BUY_AFTER
        )
        self.assertEqual(body["counter"]["matches_derived"], False)
        self.assertEqual(body["changed"], ["/privateState/%s/1" % M.LEDGER_KEY])
        self.assertEqual(ledger_now(), {"1": LEGACY_BUY_AFTER})

    def test_use_assigns_the_charges_the_unchanged_legacy_arm_assigns(self) -> None:
        seeded({"1": PRESENT})
        response = magic_now(intent("use", 1))
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["command"], M.USE_COMMAND)
        self.assertEqual(body["counter"]["derived_after"], PRESENT + 1)
        self.assertEqual(body["counter"]["recorded_after"], PRESENT + 1)
        self.assertEqual(body["counter"]["matches_derived"], True)
        self.assertEqual(ledger_now(), {"1": PRESENT + 1})

    def test_an_absent_key_takes_the_legacy_else_arm_and_is_written_at_zero(self) -> None:
        before = bare()
        self.assertEqual(before["ledger"], {})
        response = magic_now(intent("use", COMMITTED_ID))
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["counter"]["present_before"], False)
        self.assertEqual(body["counter"]["derived_after"], 1)
        self.assertEqual(body["counter"]["recorded_after"], 0)
        self.assertEqual(body["counter"]["matches_derived"], False)
        self.assertEqual(body["counter"]["legacy_absent_arm_writes_zero"], True)
        self.assertEqual(body["changed"], ["/privateState/%s/1" % M.LEDGER_KEY])
        self.assertEqual(ledger_now(), {"1": 0})
        # The created key is appended, never sorted into place.
        self.assertEqual(list(ledger_now()), ["1"])

    def test_the_derived_transition_never_falls_below_the_before_value(self) -> None:
        for action in M.ACTIONS:
            for before in (0, PRESENT, AT_CAP_MINUS_ONE, AT_CAP):
                with self.subTest(action=action, before=before):
                    seeded({str(COMMITTED_ID): before})
                    body = magic_now(intent(action, COMMITTED_ID)).get_json()
                    counter = body["counter"]
                    self.assertEqual(counter["derived_change"], 0 if before >= AT_CAP else 1)
                    self.assertGreaterEqual(
                        counter["derived_after"], counter["before"]
                    )
                    self.assertEqual(counter["decreased"], False)

    def test_the_cap_is_the_recorded_literal_and_the_derived_value_saturates(self) -> None:
        seeded({str(COMMITTED_ID): AT_CAP_MINUS_ONE})
        body = magic_now(intent("use", COMMITTED_ID)).get_json()
        self.assertEqual(body["counter"]["cap"], M.COUNTER_CAP)
        self.assertEqual(body["counter"]["cap"], 50)
        self.assertEqual(body["counter"]["capped"], True)
        self.assertEqual(body["counter"]["derived_after"], AT_CAP)
        self.assertEqual(tuple(body["counter"]["cap_is_literal"]), M.CAP_SOURCE_LINES)
        self.assertEqual(
            body["counter"]["rejected_cap_derivation"],
            M.REJECTED_CAP_DERIVATION,
        )

    def test_every_one_of_the_eight_stored_resources_is_unchanged(self) -> None:
        for action in M.ACTIONS:
            with self.subTest(action=action):
                before = seeded({str(COMMITTED_ID): PRESENT})
                body = magic_now(intent(action, COMMITTED_ID)).get_json()
                self.assertEqual(len(RESOURCE_NAMES), M.RESOURCE_NAME_COUNT)
                self.assertEqual(body["resource_count"], len(RESOURCE_NAMES))
                self.assertEqual(
                    sorted(body["resources"].keys()),
                    sorted(RESOURCE_NAMES),
                    "the response reports all eight slots, never a subset",
                )
                for name in RESOURCE_NAMES:
                    with self.subTest(resource=name):
                        self.assertEqual(body["resources"][name], before["resources"][name])
                self.assertEqual(resources_now(), before["resources"])

    def test_no_price_is_charged_so_the_neutral_vector_is_what_the_caller_sees(self) -> None:
        for action in M.ACTIONS:
            with self.subTest(action=action):
                before = seeded({str(COMMITTED_ID): PRESENT})
                body = magic_now(intent(action, COMMITTED_ID)).get_json()
                self.assertEqual(body["no_cost_or_reward"], M.NO_COST_OR_REWARD)
                self.assertEqual(
                    M.neutral_vector(),
                    [0] * len(RESOURCE_NAMES),
                    "the derived vector is the neutral all-zero one",
                )
                self.assertEqual(
                    {name: body["resources"][name] - before["resources"][name]
                     for name in RESOURCE_NAMES},
                    {name: 0 for name in RESOURCE_NAMES},
                )

    def test_the_persisted_corpus_matches_the_response(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT, "5": 9})
        body = magic_now(intent("buy", COMMITTED_ID)).get_json()
        persisted = corpus_save()
        self.assertEqual(
            persisted[M.PRIVATE_STATE_KEY][M.LEDGER_KEY],
            {"1": LEGACY_BUY_AFTER, "5": 9},
        )
        self.assertEqual(
            persisted[M.PRIVATE_STATE_KEY][M.LEDGER_KEY]["1"],
            body["counter"]["recorded_after"],
        )

    def test_every_unaddressed_entry_is_byte_identical_and_keeps_its_position(self) -> None:
        before = seeded({"7": 4, "1": PRESENT, "3": 1, "9": 0})
        response = magic_now(intent("use", COMMITTED_ID))
        self.assertEqual(response.status_code, 200, response.get_json())
        after = ledger_now()
        self.assertEqual(list(after), ["7", "1", "3", "9"], "the key order is unchanged")
        for key in ("7", "3", "9"):
            with self.subTest(entry=key):
                self.assertEqual(after[key], before["ledger"][key])
        self.assertNotEqual(after["1"], before["ledger"]["1"])

    def test_the_committed_corpus_save_is_never_written(self) -> None:
        seed_path = harness.SEED_SAVE
        before = seed_path.read_bytes()
        seeded({str(COMMITTED_ID): PRESENT})
        self.assertEqual(magic_now(intent("buy", COMMITTED_ID)).status_code, 200)
        self.assertEqual(
            seed_path.read_bytes(), before,
            "the committed corpus save is byte-identical after a magic action",
        )

    def test_the_response_carries_the_whole_derived_contract(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        body = magic_now(intent("use", COMMITTED_ID)).get_json()
        self.assertEqual(body["addressing"]["key"], M.ACTION_ADDRESSING_KEY["use"])
        self.assertEqual(body["addressing"]["value"], COMMITTED_ID)
        self.assertEqual(body["addressing"]["kind"], "magic_id")
        self.assertIn("nothing else", body["addressing"]["note"])
        self.assertEqual(
            [step["step"] for step in body["validation_order"]],
            [step["step"] for step in M.VALIDATION_ORDER],
        )
        self.assertEqual(body["write_step"], M.WRITE_STEP)
        self.assertEqual(body["write_step"], 9)
        self.assertEqual(body["ordering_rule"], M.ORDERING_RULE)
        self.assertEqual(body["counter"]["refused_count"], M.CLIENT_DICTATED_REFUSAL)
        self.assertEqual(body["ledger_has_no_readers"], M.LEDGER_HAS_NO_READERS)
        self.assertEqual(body["no_damage"], M.NO_DAMAGE)
        self.assertEqual(body["no_magic_effect"], M.NO_MAGIC_EFFECT)
        self.assertEqual(
            body["reported_damage_vocabulary"], M.reported_vocabulary()
        )
        self.assertEqual(body["divergence"], M.divergences())
        self.assertEqual(body["divergence_count"], M.DIVERGENCE_COUNT)
        self.assertEqual(body["provenance"], M.PROVENANCE)
        self.assertEqual(
            body["refusals"],
            [
                M.REASON_INVALID_ACTION,
                M.REASON_CLIENT_DICTATED_COUNT,
                M.REASON_MISSING_MAGIC_ID,
                M.REASON_INVALID_MAGIC_ID,
                M.REASON_NON_CANONICAL_MAGIC_ID,
                M.REASON_UNKNOWN_MAGIC_ID,
                M.REASON_INVALID_LEDGER,
                M.REASON_INVALID_COUNTER,
                M.REASON_COUNTER_ABOVE_CAP,
            ],
        )


# ------------------------------- the derived/recorded divergence (design D5) --
class DerivedVersusRecordedTests(unittest.TestCase):
    """Design D5's proof half is unreachable here, and that is pinned as a fact.

    Design D5 asks for "the counter changed by exactly the derived delta".  It
    cannot be true of this route's own executions, because design D3 requires
    refusing both legacy defects while the dispatcher still runs unchanged -- so
    the two disagree by construction.  These tests make the disagreement
    explicit and total rather than leaving it to a reader of the response.
    """

    def test_the_two_helpers_disagree_for_every_reachable_buy(self) -> None:
        # Measured, not assumed: at a recorded before of ZERO the two happen to
        # agree, because the legacy arm adds `min(cap, 0 + 1)` = 1 to 0.  Every
        # other reachable before disagrees, and the agreement is pinned below
        # rather than skipped, so this loop cannot be mistaken for "always".
        for before in (PRESENT, AT_CAP_MINUS_ONE, AT_CAP):
            with self.subTest(before=before):
                derived = M.derive_counter_transition(before, M.COUNTER_CAP)
                recorded = compat_service._legacy_recorded_after("buy", before, True, M.COUNTER_CAP)
                self.assertEqual(derived["after"], min(M.COUNTER_CAP, before + 1))
                self.assertEqual(recorded, before + min(M.COUNTER_CAP, before + 1))
                self.assertNotEqual(
                    derived["after"], recorded,
                    "D5: the derived delta and the legacy arithmetic differ",
                )

    def test_zero_is_the_one_before_value_at_which_the_two_helpers_agree(self) -> None:
        derived = M.derive_counter_transition(0, M.COUNTER_CAP)
        recorded = compat_service._legacy_recorded_after("buy", 0, True, M.COUNTER_CAP)
        self.assertEqual(derived["after"], 1)
        self.assertEqual(recorded, 0 + 1)
        self.assertEqual(derived["after"], recorded)

    def test_the_two_helpers_disagree_for_every_absent_key(self) -> None:
        for action in M.ACTIONS:
            with self.subTest(action=action):
                derived = M.derive_counter_transition(0, M.COUNTER_CAP)
                recorded = compat_service._legacy_recorded_after(action, 0, False, M.COUNTER_CAP)
                self.assertEqual(derived["after"], 1)
                self.assertEqual(recorded, 0)
                self.assertNotEqual(derived["after"], recorded)

    def test_the_two_helpers_agree_only_for_use_below_the_cap(self) -> None:
        for before in (0, PRESENT, AT_CAP_MINUS_ONE, AT_CAP):
            with self.subTest(before=before):
                derived = M.derive_counter_transition(before, M.COUNTER_CAP)
                recorded = compat_service._legacy_recorded_after("use", before, True, M.COUNTER_CAP)
                self.assertEqual(derived["after"], recorded)

    def test_the_legacy_expectation_is_the_recorded_arithmetic_not_a_transition(self) -> None:
        # The executed fixture's own ladder, read off
        # `tests/fixtures/godot-damage/capture-manifest.json`: the sequential
        # ladder 2 -> 3 -> 7 -> 15 -> 31 -> 63 -> 113.  Applied to the SEQUENCE
        # of recorded befores each step is `before + min(cap, before + 1)`, so
        # the helper's own output starts one higher than the ladder and then
        # rejoins it -- which is the point: the ladder is the executed result,
        # not the formula's output for a single before.
        self.assertEqual(
            [
                compat_service._legacy_recorded_after("buy", before, True, M.COUNTER_CAP)
                for before in (2, 3, 7, 15, 31, 63)
            ],
            [5, 7, 15, 31, 63, 113],
        )
        ladder = [2]
        for _ in range(6):
            ladder.append(
                compat_service._legacy_recorded_after(
                    "buy", ladder[-1], True, M.COUNTER_CAP
                )
            )
        self.assertEqual(ladder, [2, 5, 11, 23, 47, 95, 145])


    def test_the_derived_transition_is_never_written_to_a_save(self) -> None:
        for action in M.ACTIONS:
            with self.subTest(action=action):
                before = seeded({str(COMMITTED_ID): PRESENT})
                body = magic_now(intent(action, COMMITTED_ID)).get_json()
                derived = body["counter"]["derived_after"]
                recorded = body["counter"]["recorded_after"]
                self.assertEqual(
                    recorded, ledger_now()[str(COMMITTED_ID)],
                    "the persisted value is the recorded one",
                )
                if derived != recorded:
                    self.assertNotEqual(
                        ledger_now()[str(COMMITTED_ID)], derived,
                        "the derived number is reported and never stored",
                    )
                self.assertEqual(before["ledger"][str(COMMITTED_ID)], PRESENT)

    def test_an_above_cap_counter_is_refused_before_the_legacy_arm_can_reduce_it(self) -> None:
        # `min(50, 113 + 1)` is 50 -- the charge-destroying decrease this line
        # exists to refuse, wearing this service's clothes.  It is refused, and
        # the whole document is byte-identical, so the decrease never happens.
        before = seeded({str(COMMITTED_ID): ABOVE_CAP})
        response = magic_now(intent("use", COMMITTED_ID))
        self.assertEqual(response.status_code, 409, response.get_json())
        self.assertEqual(
            response.get_json()["error"]["code"], "counter_above_cap"
        )
        self.assertEqual(snapshot()["bytes"], before["bytes"])
        self.assertEqual(ledger_now(), {"1": ABOVE_CAP})


# ------------------------------------- the client-dictated count refusal (D2) --
class ClientDictatedCountTests(unittest.TestCase):
    """Design D2: a named, separate guard reached before anything is read."""

    def assertRefused(self, payload: Dict[str, Any], needle: str = "count keys") -> Dict[str, Any]:
        before = snapshot()
        response = magic_now(payload)
        self.assertEqual(response.status_code, 400, response.get_json())
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "client_dictated_count")
        self.assertEqual(
            sorted(body.keys()), ["error", "ok", "protocol"],
            "a refusal carries an EMPTY payload: no state field at all",
        )
        self.assertEqual(sorted(body["error"].keys()), ["code", "message"])
        self.assertIn(needle, body["error"]["message"])
        self.assertEqual(snapshot()["bytes"], before["bytes"])
        return body

    def test_every_recorded_count_key_is_refused(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        for key in M.COUNT_KEYS:
            with self.subTest(key=key):
                self.assertRefused(intent("buy", COMMITTED_ID, **{key: 5}))

    def test_the_closed_count_list_is_the_eleven_recorded_keys(self) -> None:
        self.assertEqual(len(M.COUNT_KEYS), 11)
        self.assertEqual(M.CLIENT_DICTATED_REFUSAL["keys"], list(M.COUNT_KEYS))
        self.assertEqual(M.CLIENT_DICTATED_REFUSAL["reason"], M.REASON_CLIENT_DICTATED_COUNT)

    def test_all_six_protocol_keys_are_refused_end_to_end(self) -> None:
        # Previously this asserted that only FOUR of the six were refused, because
        # `refused_client_keys` folded the request key and compared it against a
        # `PROTOCOL_KEYS` holding two camelCase members.  Both sides are folded now,
        # so the endpoint refuses all six -- and this asserts the refusal arrives
        # with the endpoint's OWN named code and no partial payload, not merely
        # that the shared guard names the key.
        seeded({str(COMMITTED_ID): PRESENT})
        for key in M.PROTOCOL_KEYS:
            with self.subTest(key=key):
                self.assertRefused(intent("buy", COMMITTED_ID, **{key: 1}))
        # Every case spelling of a protocol key is refused too, because a client
        # that renamed one casing is still naming protocol plumbing.
        for key in ("publishActions", "accessToken",
                    "PUBLISHACTIONS", "AccessToken"):
            with self.subTest(spelling=key):
                self.assertRefused(intent("buy", COMMITTED_ID, **{key: 1}))

    def test_a_refused_protocol_key_leaves_the_ledger_untouched(self) -> None:
        # The refusal is real, not a 409 with the write already done: the guard
        # runs ahead of player state, so the counter is exactly where it was.
        seeded({str(COMMITTED_ID): PRESENT})
        self.assertRefused(intent("buy", COMMITTED_ID, publishActions=1))
        self.assertEqual(ledger_now(), {str(COMMITTED_ID): PRESENT})

    def test_the_guard_is_the_shared_one_and_is_not_re_implemented_here(self) -> None:
        source = SERVICE.read_text(encoding="utf-8")
        route = route_source()
        self.assertEqual(
            route.count("magic_envelope.refused_client_keys("), 1,
            "the closed list is called once and never restated",
        )
        self.assertNotIn("COUNT_KEYS", route)
        self.assertNotIn("PROTOCOL_KEYS", route)

    def test_it_is_a_separate_named_refusal_from_every_other_one(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        # The same identity with an uncommitted id and a count: the count
        # refusal wins, so the two cannot be one another.
        body = self.assertRefused(intent("buy", UNCOMMITTED_ID, amount=3))
        self.assertNotEqual(body["error"]["code"], M.REASON_UNKNOWN_MAGIC_ID)

    def test_it_fires_before_the_identity_is_required(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        without_count = {"user_id": PID, "action": "buy"}
        self.assertEqual(
            magic_now(without_count).get_json()["error"]["code"],
            M.REASON_MISSING_MAGIC_ID,
            "the same request without a count reaches step 3",
        )
        body = self.assertRefused(
            {"user_id": PID, "action": "buy", "value": 3}
        )
        self.assertNotIn(
            M.REASON_MISSING_MAGIC_ID, body["error"]["message"],
            "step 2 precedes step 3, so the identity is never demanded",
        )

    def test_it_fires_before_any_player_state_is_read(self) -> None:
        # An unreadable ledger AND a client count: the count refusal wins, so no
        # player state was consulted to reach it.
        write_ledger_verbatim(None)
        before = snapshot()
        response = magic_now(intent("buy", COMMITTED_ID, delta=1))
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(
            response.get_json()["error"]["code"], "client_dictated_count"
        )
        self.assertEqual(snapshot()["bytes"], before["bytes"])

    def test_it_fires_on_both_actions(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        for action in M.ACTIONS:
            with self.subTest(action=action):
                self.assertRefused(intent(action, COMMITTED_ID, charges=2))

    def test_it_is_step_two_of_eight_and_reads_no_player_state(self) -> None:
        step = M.VALIDATION_ORDER[1]
        self.assertEqual(step["step"], 2)
        self.assertEqual(step["key"], "no_client_dictated_count")
        self.assertEqual(step["reads_player_state"], False)


# ------------------------------------------------------ the refusal ordering --
class RefusalOrderTests(unittest.TestCase):
    """The order is one chain, and every link is asserted to precede the next."""

    def test_the_eight_checks_are_declared_in_the_delivered_order(self) -> None:
        self.assertEqual(
            [step["key"] for step in M.VALIDATION_ORDER],
            [
                "action_in_closed_vocabulary",
                "no_client_dictated_count",
                "identity_present",
                "identity_well_typed",
                "identity_in_committed_table",
                "ledger_readable",
                "counter_readable",
                "transition_derived",
            ],
        )
        self.assertEqual(M.VALIDATION_ORDER_STEPS, 8)
        self.assertEqual(M.WRITE_STEP, 9)
        self.assertEqual(
            [step["reads_player_state"] for step in M.VALIDATION_ORDER],
            [False] * 5 + [True] * 3,
            "only steps 6-8 read the player's own state",
        )

    def test_an_invalid_action_outranks_a_client_count(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        response = magic_now({"user_id": PID, "action": "cast", "count": 5})
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(response.get_json()["error"]["code"], M.REASON_INVALID_ACTION)

    def test_a_client_count_outranks_a_missing_identity(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        response = magic_now({"user_id": PID, "action": "buy", "count": 5})
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(
            response.get_json()["error"]["code"], M.REASON_CLIENT_DICTATED_COUNT
        )

    def test_a_missing_identity_outranks_a_non_canonical_one(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        payload = intent("buy", COMMITTED_ID)
        del payload["magic_id"]
        response = magic_now(payload)
        self.assertEqual(response.get_json()["error"]["code"], M.REASON_MISSING_MAGIC_ID)
        self.assertEqual(
            magic_now(intent("buy", 1.0)).get_json()["error"]["code"],
            M.REASON_NON_CANONICAL_MAGIC_ID,
        )

    def test_a_non_canonical_identity_outranks_an_uncommitted_one(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        response = magic_now(intent("buy", 1.0))
        self.assertEqual(
            response.get_json()["error"]["code"], M.REASON_NON_CANONICAL_MAGIC_ID
        )

    def test_the_content_check_runs_before_the_ledger_is_read(self) -> None:
        # An uncommitted identity AND an unreadable ledger: the content refusal
        # wins, so a request naming something that is not a spell never consults
        # the player's own state (VALIDATION_ORDER step 5 before step 6).
        write_ledger_verbatim(None)
        before = snapshot()
        response = magic_now(intent("buy", UNCOMMITTED_ID))
        self.assertEqual(response.status_code, 409, response.get_json())
        self.assertEqual(response.get_json()["error"]["code"], M.REASON_UNKNOWN_MAGIC_ID)
        self.assertEqual(snapshot()["bytes"], before["bytes"])

    def test_an_unreadable_ledger_outranks_an_unreadable_counter(self) -> None:
        write_ledger_verbatim(None)
        response = magic_now(intent("buy", COMMITTED_ID))
        self.assertEqual(response.status_code, 500, response.get_json())
        self.assertEqual(response.get_json()["error"]["code"], "unresolvable_ledger")

    def test_the_write_step_is_reported_after_the_eight_checks(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        body = magic_now(intent("buy", COMMITTED_ID)).get_json()
        self.assertEqual(body["write_step"], M.VALIDATION_ORDER_STEPS + 1)
        self.assertEqual(body["ordering_rule"]["steps"], M.VALIDATION_ORDER_STEPS)
        self.assertEqual(body["ordering_rule"]["write_step"], M.WRITE_STEP)


# ------------------------------------------------------------ every refusal --
class RefusalTests(unittest.TestCase):
    """Each named code, an empty payload, and a byte-identical corpus."""

    def assertRefused(
        self,
        payload: Any,
        code: str,
        status: int,
        before: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if before is None:
            before = snapshot()
        response = magic_now(payload)
        self.assertEqual(response.status_code, status, response.get_json())
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(sorted(body.keys()), ["error", "ok", "protocol"])
        self.assertEqual(sorted(body["error"].keys()), ["code", "message"])
        after = snapshot()
        self.assertEqual(after["ledger"], before["ledger"], "no ledger entry moved")
        self.assertEqual(after["resources"], before["resources"])
        self.assertEqual(
            after["bytes"], before["bytes"],
            "a refusal leaves the whole recorded document byte-identical",
        )
        return body

    def test_the_action_vocabulary_is_closed(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        for action in ("cast", "Buy", "buy ", "", None, 1, True):
            with self.subTest(action=action):
                self.assertRefused(
                    intent("buy", COMMITTED_ID) | {"action": action},
                    M.REASON_INVALID_ACTION, 400,
                )

    def test_a_missing_action_is_named(self) -> None:
        before = seeded({str(COMMITTED_ID): PRESENT})
        payload = intent("buy", COMMITTED_ID)
        del payload["action"]
        body = self.assertRefused(payload, "missing_action", 400, before)
        self.assertEqual(body["error"]["message"], "action is required")

    def test_a_missing_identity_is_named(self) -> None:
        before = seeded({str(COMMITTED_ID): PRESENT})
        payload = intent("buy", COMMITTED_ID)
        del payload["magic_id"]
        self.assertRefused(payload, M.REASON_MISSING_MAGIC_ID, 400, before)

    def test_an_ill_typed_identity_is_refused_and_not_coerced(self) -> None:
        before = seeded({str(COMMITTED_ID): PRESENT})
        for value in ([1], {"id": 1}, True, False, (1,), [1, 2]):
            with self.subTest(magic_id=value):
                self.assertRefused(
                    intent("buy", value), M.REASON_INVALID_MAGIC_ID, 400, before
                )
        # A `None` is ABSENT rather than ill-typed, so it takes step 3's reason.
        self.assertRefused(
            intent("buy", None), M.REASON_MISSING_MAGIC_ID, 400, before
        )

    def test_a_string_or_float_identity_is_non_canonical_and_never_coerced(self) -> None:
        before = seeded({str(COMMITTED_ID): PRESENT})
        for value in ("1", 1.0, "01", " 1"):
            with self.subTest(magic_id=value):
                body = self.assertRefused(
                    intent("buy", value), M.REASON_NON_CANONICAL_MAGIC_ID, 400, before
                )
                self.assertIn(M.REASON_NON_CANONICAL_MAGIC_ID, body["error"]["message"])

    def test_a_float_identity_never_creates_the_recorded_second_ledger_key(self) -> None:
        # The executed fixture drove `use_magic 1.0` and the legacy branch keyed
        # the ledger on `str(magic_id)`, creating a SECOND, unrelated key "1.0".
        before = seeded({str(COMMITTED_ID): PRESENT})
        self.assertRefused(
            intent("use", 1.0), M.REASON_NON_CANONICAL_MAGIC_ID, 400, before
        )
        self.assertNotIn("1.0", ledger_now())

    def test_an_identity_outside_the_committed_table_is_refused(self) -> None:
        before = seeded({str(COMMITTED_ID): PRESENT})
        for value in (0, -1, M.COMMITTED_MAGIC_COUNT + 1, UNCOMMITTED_ID):
            with self.subTest(magic_id=value):
                body = self.assertRefused(
                    intent("buy", value), M.REASON_UNKNOWN_MAGIC_ID, 409, before
                )
                self.assertIn(M.REASON_UNKNOWN_MAGIC_ID, body["error"]["message"])

    def test_every_committed_identity_is_accepted(self) -> None:
        # The refusal is bounded by the committed table, so this pins both ends:
        # all ten ids execute and none of them is refused.
        for magic_id in range(
            M.COMMITTED_MAGIC_ID_MIN, M.COMMITTED_MAGIC_ID_MAX + 1
        ):
            with self.subTest(magic_id=magic_id):
                seeded({})
                response = magic_now(intent("use", magic_id))
                self.assertEqual(response.status_code, 200, response.get_json())
                self.assertEqual(list(ledger_now()), [str(magic_id)])

    def test_an_unreadable_ledger_is_reported_and_never_defaulted(self) -> None:
        for raw in (None, [], "1001", 5, {"1": "2"}, {"1": True}, {"1": -1}, {"1": 1.0}):
            with self.subTest(ledger=raw):
                write_ledger_verbatim(raw)
                before = snapshot()
                mapping = (
                    isinstance(raw, dict)
                )
                code = (
                    M.REASON_INVALID_COUNTER if mapping else M.REASON_INVALID_LEDGER
                )
                status = 409 if mapping else 500
                served = "unreadable_counter" if mapping else "unresolvable_ledger"
                body = self.assertRefused(
                    intent("buy", COMMITTED_ID), served, status, before
                )
                self.assertIn(
                    code, body["error"]["message"],
                    "the envelope's own reason is carried in the message",
                )

    def test_a_present_counter_of_a_non_integer_is_refused(self) -> None:
        before = seeded({"1": "2"})
        body = self.assertRefused(
            intent("buy", COMMITTED_ID), "unreadable_counter", 409, before
        )
        self.assertIn(M.REASON_INVALID_COUNTER, body["error"]["message"])

    def test_a_counter_above_the_cap_is_refused_rather_than_reduced(self) -> None:
        for action in M.ACTIONS:
            for value in (M.COUNTER_CAP + 1, 113, 10 ** 6):
                with self.subTest(action=action, counter=value):
                    before = seeded({str(COMMITTED_ID): value})
                    body = self.assertRefused(
                        intent(action, COMMITTED_ID), "counter_above_cap", 409, before
                    )
                    self.assertIn(M.REASON_COUNTER_ABOVE_CAP, body["error"]["message"])
                    self.assertEqual(ledger_now(), {"1": value})

    def test_a_counter_exactly_at_the_cap_is_not_refused(self) -> None:
        for action in M.ACTIONS:
            with self.subTest(action=action):
                seeded({str(COMMITTED_ID): AT_CAP})
                response = magic_now(intent(action, COMMITTED_ID))
                self.assertEqual(response.status_code, 200, response.get_json())
                self.assertEqual(response.get_json()["counter"]["capped"], True)

    def test_an_unknown_user_is_refused(self) -> None:
        before = seeded({str(COMMITTED_ID): PRESENT})
        self.assertRefused(
            {"user_id": "does-not-exist-0000", "action": "buy", "magic_id": COMMITTED_ID},
            "unknown_user_id", 404, before,
        )

    def test_a_missing_or_non_object_body_is_refused(self) -> None:
        before = seeded({str(COMMITTED_ID): PRESENT})
        with harness.offline():
            response = CLIENT.post("/v0/magic", data="not json")  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_payload")
        self.assertEqual(snapshot()["bytes"], before["bytes"])
        with harness.offline():
            response = CLIENT.post("/v0/magic", json={})  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_user_id")
        self.assertEqual(snapshot()["bytes"], before["bytes"])

    def test_every_refusal_reason_reached_by_this_suite_is_declared(self) -> None:
        declared = {
            M.REASON_INVALID_ACTION,
            M.REASON_CLIENT_DICTATED_COUNT,
            M.REASON_MISSING_MAGIC_ID,
            M.REASON_INVALID_MAGIC_ID,
            M.REASON_NON_CANONICAL_MAGIC_ID,
            M.REASON_UNKNOWN_MAGIC_ID,
            M.REASON_INVALID_LEDGER,
            M.REASON_INVALID_COUNTER,
            M.REASON_COUNTER_ABOVE_CAP,
        }
        self.assertEqual(len(declared), 9)
        self.assertEqual(
            [step["key"] for step in M.VALIDATION_ORDER][1:],
            [
                "no_client_dictated_count",
                "identity_present",
                "identity_well_typed",
                "identity_in_committed_table",
                "ledger_readable",
                "counter_readable",
                "transition_derived",
            ],
        )
        # The envelope declares TWELVE reasons; the route answers nine of them and
        # the remaining three belong to the envelope's own machinery
        # (`validate_vector`, `build_envelope`'s stamp sentinel and its payload
        # shape), not to `project_magic`.  The mapping covers all twelve, so a
        # reason that ever started being returned by this route would already
        # have a status and a code.
        envelope_reasons = set(magic_envelope_reason_names())
        self.assertEqual(len(envelope_reasons), 12)
        self.assertTrue(
            declared < envelope_reasons,
            "every answered reason is a declared one",
        )
        self.assertEqual(
            envelope_reasons - declared,
            {M.REASON_INVALID_VECTOR, M.REASON_INVALID_TIMESTAMP, M.REASON_INVALID_PAYLOAD},
        )

    def test_no_reason_project_magic_can_return_is_unmapped(self) -> None:
        # The projection's own `reason` vocabulary, read from its refusal table
        # rather than from the route, so a new projection reason cannot reach the
        # route without a status and a code.
        projection_reasons = {
            M.REASON_INVALID_ACTION,
            M.REASON_MISSING_MAGIC_ID,
            M.REASON_INVALID_MAGIC_ID,
            M.REASON_NON_CANONICAL_MAGIC_ID,
            M.REASON_UNKNOWN_MAGIC_ID,
            M.REASON_INVALID_LEDGER,
            M.REASON_INVALID_COUNTER,
            M.REASON_COUNTER_ABOVE_CAP,
        }
        mapping = refusal_mapping_source()
        for reason in sorted(projection_reasons):
            with self.subTest(reason=reason):
                self.assertIn(symbol_for(reason), mapping)
        self.assertNotIn(M.REASON_CLIENT_DICTATED_COUNT, projection_reasons)
        self.assertIn(symbol_for(M.REASON_CLIENT_DICTATED_COUNT), mapping)


def symbol_for(reason: str) -> str:
    """The `magic_envelope` constant a reason string is declared under.

    The mapping table keys its entries by the SYMBOLIC constant, so an
    assertion that looked for the reason's string literal would fail against
    a mapping that is in fact complete.
    """
    return "magic_envelope.REASON_%s" % reason.upper()


def magic_envelope_reason_names() -> List[str]:
    """Every ``REASON_*`` the envelope declares, by prefix rather than by import."""
    text = M.__file__
    assert text is not None
    source = Path(text).read_text(encoding="utf-8")
    return re.findall(r'^REASON_[A-Z_]+ = "([a-z_]+)"$', source, re.MULTILINE)


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

    # --- half (b): the eight resource slots ---------------------------------
    def test_each_of_the_seven_accessor_slots_is_individually_checked(self) -> None:
        self.assertEqual(len(ACCESSOR_RESOURCE_NAMES), 7)
        for name in ACCESSOR_RESOURCE_NAMES:
            with self.subTest(resource=name):
                seeded({str(COMMITTED_ID): PRESENT})
                result = post_with(
                    "resources", slot_moved(name), intent("use", COMMITTED_ID)
                )
                self.assertFailsClosed(result, "resource %s is" % name)

    def test_the_document_only_eighth_slot_is_individually_checked(self) -> None:
        # `energy` is NOT one of `LegacyBoot.resources`' seven, so it is read off
        # the document.  If it were not compared, a stub moving it would pass.
        self.assertIn(DOCUMENT_ONLY_RESOURCE, RESOURCE_NAMES)
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            document_energy(_ABSENT),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "resource energy is missing")

    def test_a_missing_accessor_slot_fails_closed_rather_than_defaulting_to_zero(self) -> None:
        for name in ("mana", "xp"):
            with self.subTest(resource=name):
                seeded({str(COMMITTED_ID): PRESENT})
                result = post_with(
                    "resources", slot_absent(name), intent("use", COMMITTED_ID)
                )
                self.assertFailsClosed(result, "resource %s is missing" % name)

    def test_every_eight_slot_is_named_in_the_missing_slot_message(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "resources", slot_absent("mana"), intent("use", COMMITTED_ID)
        )
        message = result.get_json()["error"]["message"]
        self.assertIn("FULL eight-slot resource set", message)
        self.assertIn("never a subset", message)

    # --- half (a): the ledger ------------------------------------------------
    def ledger_transform(self, mutate: Callable[[Dict[str, Any]], None]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        def transform(document: Dict[str, Any]) -> Dict[str, Any]:
            mutate(document[M.PRIVATE_STATE_KEY][M.LEDGER_KEY])
            return document

        return transform

    def test_a_counter_that_moved_by_the_wrong_amount_fails_closed(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("1", 99)),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "not the %d the unchanged legacy" % (PRESENT + 1))

    def test_a_counter_that_did_not_move_at_all_fails_closed(self) -> None:  # noqa: D401
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("1", PRESENT)),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "not the %d the unchanged legacy" % (PRESENT + 1))

    def test_a_derived_value_written_instead_of_the_recorded_one_fails_closed(self) -> None:
        # The D5/D3 collision is the one case where the derived number IS the
        # recorded one, so this half is what forecloses a future edit that wrote
        # `derived_after` and passed by accident.
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("1", PRESENT + 1)),
            intent("buy", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "not the %d the unchanged legacy" % LEGACY_BUY_AFTER)
        self.assertIn(
            "deliberately NOT written",
            result.get_json()["error"]["message"],
            "the message states that the derived number is not the stored one",
        )

    def test_a_neighbouring_entry_that_moved_fails_closed(self) -> None:
        seeded({"7": 4, str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("7", 5)),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "ledger['7'] is 5")

    def test_a_neighbouring_entry_that_vanished_fails_closed(self) -> None:
        seeded({"7": 4, str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.pop("7")),
            intent("use", COMMITTED_ID),
        )
        # A removed key changes the ORDER as well as the contents, and the order
        # half runs first, so the stronger message is the one reported.
        self.assertFailsClosed(result, "key order is ['1']")

    def test_a_reordered_ledger_fails_closed(self) -> None:
        seeded({"7": 4, "1": PRESENT, "3": 1})

        def reverse(ledger: Dict[str, Any]) -> None:
            reordered = {key: ledger[key] for key in reversed(list(ledger))}
            ledger.clear()
            ledger.update(reordered)

        result = post_with(
            "save_document", self.ledger_transform(reverse),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "key order is")

    def test_an_extra_key_that_appeared_fails_closed(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("99", 0)),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "key order is")

    def test_the_addressed_key_vanishing_fails_closed(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.pop("1")),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "key order is []")

    def test_a_counter_written_as_a_non_integer_fails_closed(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("1", "3")),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "not an integer")

    def test_a_bool_counter_fails_closed_rather_than_reading_as_one(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("1", True)),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "not an integer")

    def test_a_whole_ledger_replacement_fails_closed(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.clear()),
            intent("use", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "key order is")

    def test_a_ledger_that_is_not_a_mapping_after_execution_fails_closed(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})

        def unmap(document: Dict[str, Any]) -> Dict[str, Any]:
            document[M.PRIVATE_STATE_KEY][M.LEDGER_KEY] = "not a ledger"
            return document

        result = post_with("save_document", unmap, intent("use", COMMITTED_ID))
        self.assertFailsClosed(result, "is NoneType after execution")

    def test_an_integer_ledger_key_is_hand_edited_only_and_is_reported(self) -> None:
        # MEASURED, and the route's answer was a crash before this test existed:
        # `project_ledger` tolerates an integer key, `json.dump` writes its string
        # form to disk, but the boot keeps the INTEGER key in its in-memory
        # document -- so `sorted(ledger_after)` over the mixed set raised
        # `TypeError: '<' not supported between instances of 'str' and 'int'`
        # and escaped as an unhandled 500 traceback rather than a routed answer.
        #
        # The legacy server cannot produce this state: it keys the ledger on
        # `str(magic_id)` (command.py:658-660, 670-672), so an integer key is
        # only reachable by hand-editing a save.  The route therefore does not
        # refuse it -- inventing a reason would be an invention -- it answers and
        # REPORTS the condition.
        self.assertTrue(M.project_ledger({1: 0})["ok"])
        seeded({1: 0})
        self.assertEqual(
            list(ledger_now()), [1],
            "the in-memory document keeps the integer key json.dump wrote away",
        )
        self.assertEqual(
            list(corpus_save()[M.PRIVATE_STATE_KEY][M.LEDGER_KEY]), ["1"],
            "the persisted document has the string form",
        )
        response = magic_now(intent("use", COMMITTED_ID))
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["counter"]["ledger_key"], "1")
        self.assertEqual(
            body["counter"]["ledger_after_keys_are_strings"], False,
            "the answer states that a non-string key is present",
        )
        self.assertEqual(
            body["counter"]["ledger_after"], ["1", "1"],
            "both keys render to the same string, which is why the flag exists",
        )

    def test_the_all_string_flag_is_true_for_every_committed_shape(self) -> None:
        for ledger in ({}, {"1": 0}, {"7": 4, "1": 2, "3": 1}):
            with self.subTest(ledger=sorted(ledger)):
                seeded(dict(ledger))
                body = magic_now(intent("use", COMMITTED_ID)).get_json()
                self.assertEqual(
                    body["counter"]["ledger_after_keys_are_strings"], True
                )

    def test_the_ledger_appearing_at_execution_time_is_structurally_unreachable(self) -> None:
        # The branch exists as defence in depth, but `_magic_snapshot` returns
        # ``None`` for a missing ledger and `project_magic(None, ...)` is
        # `invalid_ledger`, which refuses BEFORE the dispatch.  So the only way
        # to reach the branch would be for the pre-execution read to disagree
        # with the post-execution one, which the stub below fakes.
        seeded({str(COMMITTED_ID): PRESENT})

        def drop_ledger(document: Dict[str, Any]) -> Dict[str, Any]:
            document[M.PRIVATE_STATE_KEY].pop(M.LEDGER_KEY, None)
            return document

        result = post_with("save_document", drop_ledger, intent("use", COMMITTED_ID))
        self.assertFailsClosed(result, "is NoneType after execution")

    def test_the_proof_fails_closed_and_leaves_the_ledger_the_legacy_arm_wrote(self) -> None:
        # A proof failure is a SERVER refusal, and it reports no state at all --
        # so the persisted ledger is whatever the unchanged dispatcher wrote and
        # is never the derived number.
        seeded({str(COMMITTED_ID): PRESENT})
        result = post_with(
            "save_document",
            self.ledger_transform(lambda ledger: ledger.__setitem__("7", 5)),
            intent("buy", COMMITTED_ID),
        )
        self.assertFailsClosed(result, "key order is ['1', '7']")
        self.assertEqual(
            ledger_now(), {"1": LEGACY_BUY_AFTER},
            "the legacy arm wrote and persisted; the stub never reached the "
            "file, and the proof refused to report the answer",
        )


# ---------------------------------------------- the recorded non-rules --------
class RecordedNonRuleTests(unittest.TestCase):
    """Each deliberate omission is reported so it cannot read as a gap."""

    def test_no_damage_is_reported_on_every_answer(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        body = magic_now(intent("buy", COMMITTED_ID)).get_json()
        self.assertEqual(body["no_damage"], M.NO_DAMAGE)
        self.assertIn(
            "No damage is resolved", M.NO_DAMAGE["verdict"]
        )
        self.assertIsNone(M.NO_DAMAGE["committed_content_has_no_amount"]["field"])
        self.assertEqual(
            M.NO_DAMAGE["no_storage_evidence"]["private_state_damage_shaped_keys"], 0
        )

    def test_no_cost_or_reward_is_reported_with_its_measurement(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        body = magic_now(intent("use", COMMITTED_ID)).get_json()
        self.assertEqual(body["no_cost_or_reward"], M.NO_COST_OR_REWARD)
        self.assertEqual(M.NO_COST_OR_REWARD["price"], "none charged")
        self.assertEqual(M.NO_COST_OR_REWARD["reward"], "none paid")
        self.assertEqual(M.NO_COST_OR_REWARD["measured"]["slots_that_moved"], 0)
        self.assertEqual(
            M.NO_COST_OR_REWARD["measured"]["resource_names"], list(RESOURCE_NAMES)
        )

    def test_the_ledger_is_reported_as_having_no_readers(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        body = magic_now(intent("buy", COMMITTED_ID)).get_json()
        self.assertEqual(body["ledger_has_no_readers"], M.LEDGER_HAS_NO_READERS)
        self.assertEqual(M.LEDGER_HAS_NO_READERS["read_sites"], 0)
        self.assertEqual(M.LEDGER_HAS_NO_READERS["ledger_write_sites"], 4)

    def test_the_divergences_are_reported_and_are_not_parity(self) -> None:
        seeded({str(COMMITTED_ID): PRESENT})
        body = magic_now(intent("buy", COMMITTED_ID)).get_json()
        self.assertEqual(body["divergence_count"], M.DIVERGENCE_COUNT)
        for entry in body["divergence"]:
            with self.subTest(divergence=entry["id"]):
                self.assertIn(
                    entry["classification"],
                    {
                        "divergence",
                        "refused, not reproduced",
                        "recorded decision, not a reproduction",
                    },
                )
                self.assertTrue(entry["authority"])
                self.assertIn("legacy_behaviour", entry)
                self.assertIn("service_behaviour", entry)

    def test_the_non_claims_are_carried_and_not_delivered(self) -> None:
        claims = M.non_claims()
        self.assertEqual(len(claims), 11)
        self.assertEqual(len(claims), len(set(claims)), "no duplicated non-claim")
        for claim in claims:
            self.assertIsInstance(claim, str)
            self.assertTrue(claim)
        self.assertIn("No damage is resolved, computed, applied, or stored.", claims)
        self.assertIn(
            "The cap is the recorded literal, not a derivation from committed "
            "content.",
            claims,
        )
        self.assertIn(
            "No pixel parity is claimed and no windowed capture is claimed; "
            "nothing is rendered.",
            claims,
        )

    def test_the_damage_vocabulary_is_reported_verbatim_not_applied(self) -> None:
        vocabulary = M.reported_vocabulary()
        self.assertIn("cost_tokens", vocabulary)
        self.assertIn("mission_types_owned_elsewhere", vocabulary)
        self.assertIn("reset_instants", vocabulary)
        self.assertIn("no_op_branch", vocabulary)
        self.assertEqual(
            vocabulary["no_op_branch"]["command"], M.NO_OP_COMMAND
        )
        # And none of it is reachable from this route's two actions.
        self.assertEqual(M.MAGIC_COMMANDS, (M.BUY_COMMAND, M.USE_COMMAND))
        self.assertNotIn(M.NO_OP_COMMAND, M.ACTION_COMMAND.values())

    def test_no_committed_damage_field_has_a_legacy_consumer(self) -> None:
        self.assertEqual(len(M.ZERO_CONSUMER_DAMAGE_FIELDS), 7)
        source_text = M.legacy_source_text()
        for field in M.ZERO_CONSUMER_DAMAGE_FIELDS:
            with self.subTest(field=field):
                counts = M.count_field_consumers(source_text, field)
                # The two rules the envelope's own docstring names as able to
                # establish a consumer.  `attack` reads a non-zero `code_only`
                # figure -- a recorded measurement, and the reason the token
                # rules are the ones this assertion uses.
                self.assertEqual(counts["token"], 0)
                self.assertEqual(counts["quoted"], 0)
        self.assertEqual(
            M.count_field_consumers(source_text, "attack")["code_only"], 5,
            "measured, not asserted: the substring view is the only non-zero one",
        )
        for field in M.ZERO_CONSUMER_DAMAGE_FIELDS[1:]:
            with self.subTest(field=field):
                self.assertEqual(
                    sum(M.count_field_consumers(source_text, field).values()), 0,
                    "every other damage-shaped field is absent under all six rules",
                )


# ------------------------------------------------------- structural guards --
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
    """The ``/v0/magic`` route slice: its own ``def`` up to the next decorator.

    The slice is the region the combat and stored-placement suites already parse
    as "exactly one function"; reusing that definition here is what makes this
    suite's structural claim the *same* claim rather than a second, weaker one.
    """
    text = source()
    start = text.index("def v0_magic(")
    following = [offset for offset in decorator_offsets(text) if offset > start]
    if not following:
        raise AssertionError("no route decorator follows v0_magic")
    end = following[0]
    span = text[start:end]
    if not span.startswith("def v0_magic("):
        raise AssertionError("the route slice does not begin at its own def")
    return span


def refusal_mapping_source() -> str:
    """The `_magic_refusal` helper's status-by-reason table.

    The mapping lives at MODULE scope on purpose -- a helper declared inside
    the route slice would break the one-function-per-route invariant -- so
    this reads the helper's own body rather than the route.
    """
    start = source().index("def _magic_refusal(")
    text = source()[start:]
    begin = text.index("status_by_reason = {")
    end = text.index("status_by_reason.get(", begin)
    return text[begin:end]


def module_scope_functions() -> List[str]:

    tree = ast.parse(source())
    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]


class StructuralTests(unittest.TestCase):
    """Where the route and its helpers live, pinned as a bounded set."""

    def test_the_route_slice_parses_as_exactly_one_function(self) -> None:
        tree = ast.parse(textwrap.dedent(route_source().lstrip("\n")))
        self.assertEqual(
            [node.name for node in tree.body if isinstance(node, ast.FunctionDef)],
            ["v0_magic"],
        )

    def test_no_helper_is_declared_inside_the_route_slice(self) -> None:
        span = route_source()
        for helper in ("_magic_snapshot", "_magic_refusal", "_committed_magic",
                       "_legacy_recorded_after"):
            with self.subTest(helper=helper):
                self.assertNotIn("def %s(" % helper, span)
        tree = ast.parse(textwrap.dedent(span.lstrip("\n")))
        self.assertEqual(len(tree.body), 1)

    def test_the_route_sits_between_combat_and_place_stored(self) -> None:
        markers = [
            line.strip()
            for line in source().split("\n")
            if line.strip().startswith("@app.")
        ]
        names = [marker.split("/")[-1].rstrip('")') for marker in markers]
        self.assertIn("magic", names)
        self.assertLess(names.index("combat"), names.index("magic"))
        self.assertLess(names.index("magic"), names.index("place_stored"))
        # The two delivered invariants the combat and stored-placement suites own.
        self.assertEqual(markers[0], '@app.post("/v0/tutorial")')
        self.assertEqual(markers[-1], '@app.post("/v0/level_up")')

    def test_every_magic_helper_is_declared_at_module_scope(self) -> None:
        names = module_scope_functions()
        for helper in ("_magic_snapshot", "_magic_refusal", "_committed_magic",
                       "_legacy_recorded_after"):
            with self.subTest(helper=helper):
                self.assertIn(helper, names)

    def test_no_further_magic_helper_can_be_added_silently(self) -> None:
        # A BOUNDED guard rather than a whole-module inventory: it cannot break
        # when an unrelated route adds its own helper, but it does fail if a
        # fifth magic-named helper appears without a review of this file.
        names = module_scope_functions()
        magic_named = sorted(n for n in names if "magic" in n.lower())
        self.assertEqual(
            magic_named,
            ["_committed_magic", "_magic_refusal", "_magic_snapshot"],
        )
        self.assertNotIn("_legacy_recorded_after", magic_named)
        self.assertEqual(
            len(names), len(set(names)), "no duplicate module-scope name"
        )

    def test_the_refusal_mapping_covers_every_reason_this_route_can_answer(self) -> None:
        # Eleven of the envelope's twelve reasons, not twelve: `invalid_payload`
        # is the service's own body-shape rejection, answered by
        # `_resolve_user_id` before this route exists, so `_magic_refusal` never
        # sees it.  Naming the exception is what keeps the count honest instead
        # of quietly asserting a scope that was never true.
        mapping = refusal_mapping_source()
        reasons = [
            reason
            for reason in magic_envelope_reason_names()
            if reason != M.REASON_INVALID_PAYLOAD
        ]
        self.assertEqual(len(reasons), 11)
        for reason in reasons:
            with self.subTest(reason=reason):
                self.assertIn(symbol_for(reason), mapping)
        self.assertNotIn(symbol_for(M.REASON_INVALID_PAYLOAD), mapping)

    def test_an_unmapped_reason_fails_closed_as_a_server_fault(self) -> None:
        # `_magic_refusal`'s fallback: an unknown reason is a bug in the mapping,
        # so it answers 500 rather than blaming a request that did nothing wrong.
        # `error_response` returns `(body, status)`, the Flask view convention.
        body, status = compat_service._magic_refusal(
            "a_reason_that_is_not_declared", "boom"
        )
        self.assertEqual(status, 500)
        self.assertEqual(body["error"]["code"], "unresolvable_ledger")
        self.assertIn("a_reason_that_is_not_declared", body["error"]["message"])

    def test_the_route_never_writes_a_derived_counter(self) -> None:
        # The derived number is read from the projection and reported; it is
        # never the operand of a write to a save.
        span = route_source()
        self.assertIn('"derived_after": derived_after', span)
        self.assertNotIn('ledger["%s"] = derived_after' % "anything", span)
        writes = re.findall(r"ledger_after\[[^\]]+\]\s*=\s*", span)
        self.assertEqual(writes, [], "the route never assigns into a ledger")

    def test_the_service_adds_no_new_dependency_and_no_socket(self) -> None:
        span = route_source()
        for forbidden in ("requests", "urllib", "socket", "subprocess", "open("):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, span)