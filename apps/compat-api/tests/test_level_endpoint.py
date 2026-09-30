#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/level_up`` behavior tests (OpenSpec task 2.3).

No server and no socket: every request goes through Flask's in-process
test client under the ``offline`` guard, so the suite binds no port and
opens no connection.  The corpus is disposable and lives in the system
temp root; every test also proves the *working-tree* save directories
(``saves/`` and ``tests/saves/``) stay byte-identical across level-up
execution.

Every test snapshots the corpus at its own start and asserts its
post-condition against that snapshot, so the suite is order-independent.
Tests that need a recorded-versus-derived **disagreement** set up one
through :func:`set_state` (in memory **and** on the corpus file, exactly as
the delivered expand suite does for its ledger) and re-take their baseline
afterwards, so the "nothing changed" claim is always about the request under
test.

The committed corpus is itself a **refusal** case: it records ``xp 4`` /
``level 1`` while the curve places level 1 at 0 experience, so the derived
level already equals the recorded one and the endpoint answers
``level_already_current``.  Every executing success case therefore begins from
a state whose recorded level is *below* the derived level — a disagreement the
legacy server has no opinion about — and each refusal is exercised both
against the committed corpus and against a disagreement state.

Covered:

* **a successful level-up** — the recorded level moves to exactly the derived
  level, **every one of the seven stored resources is unchanged**, the response
  carries the legacy ``result``, both levels, the committed ``curve`` facts
  including the one-based provenance and its rejected alternative, and the
  current ``resources``, and the persisted level is exactly what the response
  reported.
* **the two refusals** — ``level_already_current`` (the committed corpus) and
  ``xp_below_threshold`` (a recorded level the stored experience cannot
  support), each leaving the corpus **byte-identical**.
* **the derived, not client-supplied, level** — a request carrying ``level``,
  ``new_level``, ``xp``, ``experience``, ``reward_type``, ``reward_amount``,
  ``resources_changed``, and more changes nothing.
* **the two-part post-execution proof** — a recorded level that is not exactly
  the derived level, and **any** stored resource that moved, each fail closed
  with ``internal_error`` rather than reporting legacy's success.  Each is
  exercised by a stub that lets the real dispatcher run and only rewrites the
  **post**-execution read.
* **fail-closed paths** — every structurally unresolvable input in the spec
  returns its documented structured error with the corpus byte-unchanged and no
  level written.
* **the content accessors** — the committed curve's length, a resolving entry,
  an absent position, and the map's recorded level (design D2).
* **session/bootstrap byte-identity** is retained after level-ups, and the
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

import compat_legacy
import compat_service
import level_envelope

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed corpus's own progression facts.  These land in the
# ``level_already_current`` refusal by construction: the curve places level 1 at
# 0 experience and the corpus records 4 experience at level 1.
COMMITTED_XP = 4
COMMITTED_LEVEL = 1
COMMITTED_ENTRIES = 100
# A recorded level **below** the derived one, so a success is reachable.  The
# curve's second threshold is 40, so 40 experience derives level 2 while a
# recorded level of 1 has not caught up — the recorded-versus-derived
# disagreement design D2 exists to report.
DISAGREEMENT_XP = 40
DISAGREEMENT_DERIVED = 2
DISAGREEMENT_RECORDED = 1
# A recorded level **above** what the stored experience supports.
AHEAD_XP = 4
AHEAD_LEVEL = 9

RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")


def set_state(xp: int = COMMITTED_XP, level: int = COMMITTED_LEVEL) -> None:
    """Set the stored experience and recorded level, in memory **and** on disk.

    Legacy ``level_up`` assigns ``map["level"]`` in place and
    ``engine.apply_resources`` assigns ``map["xp"]`` in place, so both fields
    live in the in-memory save the endpoint reads and in the persisted corpus
    file.  Both representations are updated here: the endpoint reads the
    in-memory save through the legacy accessors, while this suite's
    post-execution assertions read the persisted file, and the only thing that
    keeps the two in step during normal operation is the legacy dispatcher
    persisting the whole save after each batch.  So the reset rewrites the
    disposable corpus file from the same in-memory document — a test-only,
    contained mechanism, never a claim about legacy behavior, and never touching
    a working-tree save.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    first_map = save["maps"][0]
    first_map["xp"] = xp
    first_map["level"] = level
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
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a level-up execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def level_up_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/level_up", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def level_now() -> Optional[int]:
    return BOOT.map_level(PID)  # type: ignore[union-attr]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def intent() -> Dict[str, Any]:
    """The whole contract: a save id and nothing else."""
    return {"user_id": PID}


def pristine() -> Dict[str, Any]:
    """Reset to the committed corpus state and snapshot it."""
    set_state()
    return {
        "level": level_now(),
        "resources": copy.deepcopy(resources_now()),
        "items": copy.deepcopy(BOOT.map_items(PID)),  # type: ignore[union-attr]
    }


def disagreement() -> Dict[str, Any]:
    """Reset to a recorded-versus-derived disagreement and snapshot it."""
    set_state(xp=DISAGREEMENT_XP, level=DISAGREEMENT_RECORDED)
    return {
        "level": level_now(),
        "resources": copy.deepcopy(resources_now()),
        "items": copy.deepcopy(BOOT.map_items(PID)),  # type: ignore[union-attr]
    }


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


def _level_rewritten_after_execution(transform: Callable[[Optional[int]], Optional[int]]):
    """A ``map_level`` stub that rewrites only the **post**-execution read.

    The endpoint reads the recorded level twice — once before dispatch (for the
    two refusals and the response's ``level_before``) and once after (for the
    structural half of the proof and ``level_after``).  Rewriting only the second
    read lets each clause of that half fail in isolation, while the real
    dispatcher still wrote the true level to the save.
    """
    original = BOOT.map_level  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Optional[int]:
        state["seen"] += 1
        level = original(user_id)
        if state["seen"] == 1:
            return level
        return transform(level)

    return stub


def _resources_rewritten_after_execution(
    transform: Callable[[Dict[str, int]], Dict[str, int]]
):
    """A ``resources`` stub that rewrites only the **post**-execution read.

    The endpoint reads the pre-execution resources before dispatch (for the
    value-level half of the proof) and again afterwards (for the response).
    Rewriting only the second read lets each resource clause fail on its own.
    """
    original = BOOT.resources  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, int]:
        state["seen"] += 1
        values = original(user_id)
        if state["seen"] == 1:
            return values
        return transform(values)

    return stub


def post_with_level_stub(
    transform: Callable[[Optional[int]], Optional[int]], payload: Dict[str, Any]
) -> Result:
    """Run one intent against a ``BOOT`` whose post level read is stubbed."""
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.map_level  # type: ignore[union-attr]
    BOOT.map_level = _level_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/level_up", json=payload))
    finally:
        BOOT.map_level = original  # type: ignore[assignment]


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
            return Result(app, app.test_client().post("/v0/level_up", json=payload))
    finally:
        BOOT.resources = original  # type: ignore[assignment]


class LevelContentAccessorTests(unittest.TestCase):
    """The committed-configuration and save resolution rules (task 2.2)."""

    def test_the_committed_curve_resolves(self) -> None:
        self.assertEqual(BOOT.level_entry_count(), COMMITTED_ENTRIES)  # type: ignore[union-attr]
        self.assertIsInstance(BOOT.level_entry_count(), int)  # type: ignore[union-attr]
        self.assertEqual(len(BOOT.config()["levels"]), COMMITTED_ENTRIES)  # type: ignore[union-attr]

    def test_a_resolving_position_returns_its_committed_entry_verbatim(self) -> None:
        for position in (0, 1, 4, 48, 49, 98, 99):
            with self.subTest(position=position):
                entry = BOOT.level_entry(position)  # type: ignore[union-attr]
                self.assertIsInstance(entry, dict)
                self.assertEqual(
                    sorted(entry),  # type: ignore[arg-type]
                    ["exp_required", "name", "reward_amount", "reward_type"],
                )
                self.assertIsInstance(entry["exp_required"], int)  # type: ignore[index]
                self.assertNotIsInstance(entry["exp_required"], bool)  # type: ignore[index]
                self.assertIsInstance(entry["name"], str)  # type: ignore[index]
        self.assertEqual(BOOT.level_entry(0),  # type: ignore[union-attr]
                         {"name": "Slave", "exp_required": 0, "reward_type": "s",
                          "reward_amount": 50})
        self.assertEqual(BOOT.level_entry(1),  # type: ignore[union-attr]
                         {"name": "Servant", "exp_required": 40, "reward_type": "w",
                          "reward_amount": 250})

    def test_the_returned_entry_is_a_copy_of_the_configuration(self) -> None:
        """A caller mutating the returned mapping must never reach the loaded
        legacy configuration."""
        entry = BOOT.level_entry(0)  # type: ignore[union-attr]
        entry["name"] = "MUTATED"  # type: ignore[index]
        entry["exp_required"] = 999999  # type: ignore[index]
        self.assertEqual(BOOT.level_entry(0)["name"], "Slave")  # type: ignore[union-attr,index]
        self.assertEqual(BOOT.level_entry(0)["exp_required"], 0)  # type: ignore[union-attr,index]
        self.assertEqual(BOOT.config()["levels"][0]["name"], "Slave")  # type: ignore[union-attr,index]
        self.assertEqual(BOOT.config()["levels"][0]["exp_required"], 0)  # type: ignore[union-attr,index]

    def test_an_absent_position_has_no_committed_entry(self) -> None:
        for bad in (100, 101, 999, 10 ** 9, -1, -100, -(10 ** 9)):
            with self.subTest(position=bad):
                self.assertIsNone(BOOT.level_entry(bad))  # type: ignore[union-attr]
        self.assertIsNotNone(BOOT.level_entry(99))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.level_entry(100))  # type: ignore[union-attr]

    def test_a_non_integer_position_has_no_committed_entry(self) -> None:
        """``True`` is an ``int`` in Python, so an ``isinstance`` check alone
        would read the first entry for a boolean."""
        for bad in ("0", 0.0, True, None, [0], {"position": 0}):
            with self.subTest(position=bad):
                self.assertIsNone(BOOT.level_entry(bad))  # type: ignore[union-attr]

    def test_a_negative_position_never_resolves_from_the_end_of_the_curve(self) -> None:
        """``entries[-1]`` is the top level in Python, so a negative position
        would otherwise read a real entry for a value this accessor must refuse."""
        for bad in (-1, -100, -(10 ** 9)):
            with self.subTest(position=bad):
                self.assertIsNone(BOOT.level_entry(bad))  # type: ignore[union-attr]
        # …and the position space really is 0..99 inclusive.
        self.assertIsNotNone(BOOT.level_entry(0))  # type: ignore[union-attr]
        self.assertIsNotNone(BOOT.level_entry(99))  # type: ignore[union-attr]

    def test_the_recorded_level_accessor_reports_the_committed_value(self) -> None:
        pristine()
        self.assertEqual(level_now(), COMMITTED_LEVEL)
        self.assertEqual(BOOT.map_level(PID), 1)  # type: ignore[union-attr]
        # It is read by value, and it changes only when a level-up writes it.
        set_state(level=7)
        self.assertEqual(level_now(), 7)
        pristine()

    def test_the_recorded_level_accessor_returns_none_for_unusable_values(self) -> None:
        """Design D2: a level this service cannot read as an integer is never
        coerced into one."""
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        first_map = save["maps"][0]
        saved = first_map["level"]
        for bad in ("1", 1.0, True, None, [1], {"level": 1}):
            with self.subTest(level=bad):
                first_map["level"] = bad
                self.assertIsNone(BOOT.map_level(PID))  # type: ignore[union-attr]
        first_map.pop("level")
        self.assertIsNone(BOOT.map_level(PID))  # type: ignore[union-attr]
        first_map["level"] = saved
        self.assertEqual(level_now(), saved)
        # …and a level below 1 is a readable integer, not an absent one: the
        # graceful refusal belongs to the conversion, not the accessor.
        for value in (0, -1, -(10 ** 9)):
            with self.subTest(level=value):
                first_map["level"] = value
                self.assertEqual(level_now(), value)
        pristine()

    def test_the_committed_census_matches_the_investigation(self) -> None:
        curve = BOOT.config()["levels"]  # type: ignore[union-attr]
        self.assertEqual(len(curve), COMMITTED_ENTRIES)
        thresholds = [int(row["exp_required"]) for row in curve]
        self.assertEqual(thresholds[:8], list(level_envelope.COMMITTED_FIRST_THRESHOLDS))
        self.assertEqual(thresholds[-1], level_envelope.COMMITTED_FINAL_THRESHOLD)
        # Strictly increasing, no duplicate, no non-positive gap.
        self.assertEqual(len(set(thresholds)), len(thresholds))
        self.assertTrue(all(b > a for a, b in zip(thresholds, thresholds[1:])))
        # The name is a label, not an identifier.
        self.assertEqual(len({row["name"] for row in curve}), 44)
        self.assertEqual({row["name"] for row in curve[48:]}, {"Conqueror"})
        # The reward fields exist and are consumed by nothing.
        self.assertEqual(
            sorted({row["reward_type"] for row in curve}),
            list(level_envelope.COMMITTED_REWARD_TYPES),
        )
        self.assertEqual(
            sorted({row["reward_amount"] for row in curve}),
            list(level_envelope.COMMITTED_REWARD_AMOUNTS),
        )

    def test_the_committed_curve_is_the_one_the_derivation_reads(self) -> None:
        """One content source: the adapter's ladder is the committed ladder, and
        the service derives its level from that and nothing else."""
        rows = [
            BOOT.level_entry(position)  # type: ignore[union-attr]
            for position in range(BOOT.level_entry_count())  # type: ignore[union-attr]
        ]
        thresholds = level_envelope.thresholds_from_entries(rows)
        self.assertEqual(thresholds, BOOT.config()["levels"] and thresholds)
        self.assertEqual(
            level_envelope.derived_level_for(COMMITTED_XP, thresholds), COMMITTED_LEVEL
        )
        self.assertEqual(
            level_envelope.derived_level_for(DISAGREEMENT_XP, thresholds),
            DISAGREEMENT_DERIVED,
        )


class LevelUpSuccessTests(unittest.TestCase):
    """A successful level-up, with both proof halves satisfied for real."""

    def test_the_derived_level_is_written_and_nothing_else_moves(self) -> None:
        before = disagreement()
        self.assertEqual(before["level"], DISAGREEMENT_RECORDED)
        self.assertEqual(before["resources"]["xp"], DISAGREEMENT_XP)
        response = level_up_now(intent())

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
                "derived_level",
                "level_before",
                "level_after",
                "curve",
                "resources",
            },
        )
        self.assertEqual(payload["protocol"], "compat-v0")
        self.assertTrue(payload["ok"])
        self.assertIsInstance(payload["server_time"], int)
        # The legacy result: command.php returns exactly this whenever
        # command() returns without raising.
        self.assertEqual(payload["result"], "success")

        # Both levels, and the structural proof half: the recorded level is
        # EXACTLY the derived one.
        self.assertEqual(payload["derived_level"], DISAGREEMENT_DERIVED)
        self.assertEqual(payload["level_before"], DISAGREEMENT_RECORDED)
        self.assertEqual(payload["level_after"], DISAGREEMENT_DERIVED)
        self.assertEqual(level_now(), DISAGREEMENT_DERIVED)
        # The persisted level is exactly what the response reported, read from
        # the corpus file and through the legacy accessor.
        self.assertEqual(corpus_save()["maps"][0]["level"], payload["level_after"])  # type: ignore[index]

        # The value-level half: **every** stored resource is unchanged, because
        # the derived vector is neutral.
        self.assertEqual(set(payload["resources"]), set(RESOURCE_NAMES))
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(payload["resources"][name], before["resources"][name])
        self.assertEqual(payload["resources"], resources_now())

        # A level-up rewrites no placement at all.
        self.assertEqual(BOOT.map_items(PID), before["items"])  # type: ignore[union-attr]
        self.assertEqual(len(BOOT.map_items(PID)), 40)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), {})  # type: ignore[union-attr]
        self.assertEqual(
            BOOT.save_document(PID)["privateState"],  # type: ignore[union-attr]
            harness.load_seed()["privateState"],
        )
        # Persistence is corpus-only.
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_curve_block_reports_the_committed_facts_and_provenance(self) -> None:
        disagreement()
        response = level_up_now(intent())
        self.assertEqual(response.status_code, 200)
        curve = response.get_json()["curve"]

        self.assertEqual(
            set(curve),
            {
                "entries",
                "index_base",
                "derivation_status",
                "rejected_alternative",
                "entry_name",
                "entry_exp_required",
                "next_level",
                "next_name",
                "next_exp_required",
                "remaining",
                "xp",
            },
        )
        self.assertEqual(curve["entries"], COMMITTED_ENTRIES)
        # Design D1 reported verbatim: the interpretation, its status, and the
        # rejected alternative, so a client mirrors them instead of re-deriving.
        self.assertEqual(curve["index_base"], "one-based")
        self.assertEqual(curve["derivation_status"], "derived-provisional")
        self.assertEqual(curve["rejected_alternative"], "zero-based")
        # The derived level's own committed entry — level 2 is ``levels[1]``,
        # which is exactly the one-based reading.
        self.assertEqual(curve["entry_name"], "Servant")
        self.assertEqual(curve["entry_exp_required"], 40)
        # The next level's threshold and the remaining experience.
        self.assertEqual(curve["next_level"], 3)
        self.assertEqual(curve["next_name"], "Peon")
        self.assertEqual(curve["next_exp_required"], 60)
        self.assertEqual(curve["remaining"], 20)
        self.assertEqual(curve["xp"], DISAGREEMENT_XP)

    def test_the_curve_block_reports_a_completed_curve_rather_than_extending_it(
        self,
    ) -> None:
        """At the curve's top the next-level fields are ``null``: a finished
        curve is reported, never invented beyond."""
        top = level_envelope.COMMITTED_FINAL_THRESHOLD
        set_state(xp=top, level=1)
        try:
            response = level_up_now(intent())
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            curve = payload["curve"]
            self.assertEqual(payload["derived_level"], COMMITTED_ENTRIES)
            self.assertEqual(payload["level_after"], COMMITTED_ENTRIES)
            self.assertEqual(curve["entry_name"], "Conqueror")
            self.assertEqual(curve["entry_exp_required"], top)
            self.assertIsNone(curve["next_level"])
            self.assertIsNone(curve["next_name"])
            self.assertIsNone(curve["next_exp_required"])
            self.assertIsNone(curve["remaining"])
            self.assertEqual(curve["xp"], top)
            # And every stored resource is still unchanged.
            self.assertEqual(payload["resources"]["xp"], top)
            self.assertEqual(payload["resources"]["gold"], 2000)
        finally:
            pristine()

    def test_the_response_never_carries_a_reward_or_a_payout(self) -> None:
        """Design D7: the committed reward fields are consumed by no legacy
        branch, so nothing resembling a reward may appear."""
        disagreement()
        payload = level_up_now(intent()).get_json()
        serialized = json.dumps(payload, sort_keys=True)
        for absent in ("reward_type", "reward_amount", "payout", "reward"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, serialized)
        self.assertNotIn("reward", sorted(payload["curve"]))

    def test_every_ladder_rung_advances_to_its_own_level(self) -> None:
        """The sweep: for each of the curve's first thresholds, a recorded level
        below the derived one advances to exactly that level and moves no
        resource."""
        thresholds = [
            int(row["exp_required"])
            for row in BOOT.config()["levels"]  # type: ignore[union-attr]
        ]
        # Rung 1 is skipped: the curve's floor is level 1, so a recorded level of
        # 1 already equals the derived level there and the request is a
        # ``level_already_current`` refusal instead (covered separately).
        for index, required in enumerate(thresholds[1:6], start=1):
            derived = index + 1
            with self.subTest(threshold=required, derived=derived):
                set_state(xp=required, level=1)
                response = level_up_now(intent())
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(payload["derived_level"], derived)
                self.assertEqual(payload["level_before"], 1)
                self.assertEqual(payload["level_after"], derived)
                self.assertEqual(level_now(), derived)
                self.assertEqual(payload["curve"]["entry_exp_required"], required)
                self.assertEqual(payload["resources"]["xp"], required)
                for name in ("gold", "wood", "oil", "steel", "cash", "mana"):
                    with self.subTest(resource=name):
                        self.assertEqual(payload["resources"][name], resources_now()[name])

    def test_a_second_request_on_the_new_level_is_refused_as_already_current(self) -> None:
        """The endpoint's own post-state is what the next request sees, so a
        repeated level-up on the same player is a ``level_already_current``.
        """
        disagreement()
        first = level_up_now(intent())
        self.assertEqual(first.status_code, 200)
        after_first = level_now()
        self.assertEqual(after_first, DISAGREEMENT_DERIVED)

        before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        second = level_up_now(intent())
        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            second.get_json()["error"]["code"], "level_already_current"
        )
        self.assertEqual(harness.save_hashes(CORPUS), before_hashes)  # type: ignore[arg-type]
        self.assertEqual(level_now(), after_first)
        pristine()


class DerivedLevelTests(unittest.TestCase):
    """The level is derived, not client-supplied (design D3)."""

    def test_client_supplied_level_keys_are_ignored(self) -> None:
        before = disagreement()
        response = level_up_now(
            dict(
                intent(),
                level=99,
                new_level=99,
                xp=2016089205,
                experience=2016089205,
                exp_required=0,
                entry_index=42,
                reward_type="g",
                reward_amount=250,
                resources_changed=[0, 0, 999999, 0, 0, 0, 0, 0],
                vector=[0, 0, 999999, 0, 0, 0, 0, 0],
                result="hacked",
                level_after=1,
            )
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["result"], "success")
        # The server's own derivation wins on every field.
        self.assertEqual(payload["derived_level"], DISAGREEMENT_DERIVED)
        self.assertEqual(payload["level_after"], DISAGREEMENT_DERIVED)
        self.assertNotEqual(payload["level_after"], 99)
        self.assertEqual(payload["curve"]["xp"], DISAGREEMENT_XP)
        self.assertNotEqual(payload["curve"]["xp"], 2016089205)
        self.assertEqual(level_now(), DISAGREEMENT_DERIVED)
        # No mint: not one balance moved.
        self.assertEqual(payload["resources"], before["resources"])
        self.assertEqual(corpus_save()["maps"][0]["xp"], DISAGREEMENT_XP)  # type: ignore[index]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        pristine()

    def test_the_client_cannot_reach_the_curve_floor_by_supplying_experience(self) -> None:
        """A client-supplied experience never enters the derivation: the level
        is computed from the **stored** value only."""
        set_state(xp=0, level=1)
        try:
            response = level_up_now(dict(intent(), xp=2016089205))
            # The stored experience 0 meets the curve's floor, so the derived
            # level is 1 — and the recorded level is already 1.
            self.assertEqual(response.status_code, 409)
            self.assertEqual(
                response.get_json()["error"]["code"], "level_already_current"
            )
        finally:
            pristine()

    def test_the_derived_vector_is_always_neutral(self) -> None:
        """Design D5: the module the endpoint sends cannot express a non-neutral
        vector, so no smuggling attempt can be composed."""
        self.assertEqual(level_envelope.neutral_vector(), [0] * 8)
        for slot in range(8):
            for value in (1, -1, 2500, -2500):
                vector = [0] * 8
                vector[slot] = value
                with self.subTest(slot=slot, value=value):
                    with self.assertRaises(level_envelope.EnvelopeError) as caught:
                        level_envelope.validate_vector(vector)
                    self.assertEqual(caught.exception.code, "invalid_vector")
        # And the envelope the endpoint actually sends.
        envelope = level_envelope.build_envelope(level=DISAGREEMENT_DERIVED)
        self.assertEqual(envelope["commands"][0][3], [0] * 8)


class GuardAndRefusalTests(unittest.TestCase):
    """Both refusals, each leaving the corpus byte-identical (design D4).

    ``setUp`` takes a baseline so a test that never reaches a request still has
    one; each test then **re-takes** the baseline after whatever setup it needs,
    so the "nothing changed" claim is always about the request under test.
    """

    def setUp(self) -> None:
        self.baseline()

    def baseline(self) -> None:
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_level = level_now()
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
        self.assertEqual(level_now(), self.before_level)
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(BOOT.map_store(PID), self.before_store)  # type: ignore[union-attr]
        self.assertEqual(resources_now(), self.before_resources)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_the_committed_corpus_is_already_current(self) -> None:
        """The recorded condition, stated as a test: the corpus records ``xp 4``
        at ``level 1`` and the curve places level 1 at 0 experience, so the
        derived level already equals the recorded one.  Executing ``level_up``
        there would rewrite an identical value."""
        pristine()
        self.assertEqual(level_now(), COMMITTED_LEVEL)
        self.assertEqual(resources_now()["xp"], COMMITTED_XP)
        self.assertEqual(
            level_envelope.derived_level_for(
                COMMITTED_XP,
                level_envelope.thresholds_from_entries(
                    [BOOT.level_entry(p) for p in range(COMMITTED_ENTRIES)]  # type: ignore[union-attr]
                ),
            ),
            COMMITTED_LEVEL,
        )

        self.baseline()
        response = level_up_now(intent())
        self.assert_refused(response, 409, "level_already_current")
        message = response.get_json()["error"]["message"]
        self.assertIn("already 1", message)
        self.assertIn("4 stored experience", message)

    def test_a_recorded_level_the_experience_cannot_support_is_refused(self) -> None:
        """Design D4's second refusal: a recorded level **above** what the
        stored experience supports.  The disagreement is reported with both
        values and the threshold that separates them, never reconciled."""
        set_state(xp=AHEAD_XP, level=AHEAD_LEVEL)
        try:
            self.assertEqual(level_now(), AHEAD_LEVEL)
            self.baseline()
            response = level_up_now(intent())
            self.assert_refused(response, 409, "xp_below_threshold")
            message = response.get_json()["error"]["message"]
            self.assertIn("stored experience %d" % AHEAD_XP, message)
            self.assertIn("recorded level %d" % AHEAD_LEVEL, message)
            self.assertIn("threshold is 1113", message)
            self.assertIn("derives level 1", message)
        finally:
            pristine()

    def test_a_recorded_level_beyond_the_curve_is_refused(self) -> None:
        """A recorded level the committed curve has no entry for cannot be
        checked against any threshold, so no advancement is derivable."""
        set_state(xp=AHEAD_XP, level=COMMITTED_ENTRIES + 1)
        try:
            self.baseline()
            response = level_up_now(intent())
            self.assert_refused(response, 409, "xp_below_threshold")
            message = response.get_json()["error"]["message"]
            self.assertIn("no entry in the committed curve", message)
            self.assertIn("holds %d levels" % COMMITTED_ENTRIES, message)
        finally:
            pristine()

    def test_a_recorded_level_below_the_curve_floor_is_refused(self) -> None:
        """A level of 0 or below has no committed entry either — and it is never
        coerced into the floor."""
        for recorded in (0, -1, -(10 ** 9)):
            with self.subTest(level=recorded):
                set_state(xp=AHEAD_XP, level=recorded)
                try:
                    self.baseline()
                    response = level_up_now(intent())
                    self.assert_refused(response, 409, "xp_below_threshold")
                    self.assertIn("no entry in the committed curve", response.get_json()["error"]["message"])
                finally:
                    pristine()

    def test_the_already_current_check_precedes_the_threshold_check(self) -> None:
        """A recorded level that both equals the derived level **and** has no
        committed entry answers ``level_already_current``: the derived level is
        the cheaper, more specific fact."""
        # xp 0 derives level 1; a recorded level of 0 has no entry, and it does
        # not equal 1 either, so this exercises the threshold refusal instead.
        set_state(xp=0, level=0)
        try:
            self.baseline()
            response = level_up_now(intent())
            self.assert_refused(response, 409, "xp_below_threshold")
        finally:
            pristine()

    def test_a_refusal_on_a_disagreement_state_leaves_the_disagreement(self) -> None:
        """Design D2: the recorded-versus-derived disagreement is reported and
        never reconciled — the stored level is exactly what it was."""
        set_state(xp=DISAGREEMENT_XP - 1, level=DISAGREEMENT_RECORDED + 1)
        try:
            # xp 39 derives level 1; the recorded level 2 sits above it.
            self.baseline()
            response = level_up_now(intent())
            self.assert_refused(response, 409, "xp_below_threshold")
            self.assertEqual(level_now(), DISAGREEMENT_RECORDED + 1)
            self.assertEqual(resources_now()["xp"], DISAGREEMENT_XP - 1)
        finally:
            pristine()

    def test_the_error_constants_are_the_documented_ones(self) -> None:
        self.assertEqual(
            compat_service.ERROR_LEVEL_ALREADY_CURRENT, "level_already_current"
        )
        self.assertEqual(compat_service.ERROR_XP_BELOW_THRESHOLD, "xp_below_threshold")
        self.assertEqual(compat_service.ERROR_INVALID_PAYLOAD, "invalid_payload")
        self.assertEqual(compat_service.ERROR_MISSING_USER_ID, "missing_user_id")
        self.assertEqual(compat_service.ERROR_INVALID_USER_ID, "invalid_user_id")
        self.assertEqual(compat_service.ERROR_UNKNOWN_USER_ID, "unknown_user_id")
        # …and both are documented in the module's error table, the documented
        # place where the status mapping is written down.
        table = Path(compat_service.__file__).read_text(encoding="utf-8")
        for code in ("level_already_current", "xp_below_threshold"):
            with self.subTest(code=code):
                self.assertIn("``%s``" % code, table)


class LevelUpFailClosedTests(unittest.TestCase):
    """Structurally unresolvable input fails closed with no mutation."""

    def setUp(self) -> None:
        pristine()
        self.before_hashes = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        self.before_level = level_now()
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
        self.assertEqual(level_now(), self.before_level)
        self.assertEqual(BOOT.map_items(PID), self.before_items)  # type: ignore[union-attr]
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_non_object_bodies(self) -> None:
        with harness.offline():
            responses = [
                CLIENT.post("/v0/level_up"),  # no body at all
                CLIENT.post(  # type: ignore[union-attr]
                    "/v0/level_up", data="hello", content_type="text/plain"
                ),
                CLIENT.post("/v0/level_up", json=[1, 2, 3]),  # type: ignore[union-attr]
                CLIENT.post("/v0/level_up", json=7),  # type: ignore[union-attr]
                CLIENT.post("/v0/level_up", json="level"),  # type: ignore[union-attr]
            ]
        for response in responses:
            self.assert_fail_closed(response, 400, "invalid_payload")

    def test_user_id_failures(self) -> None:
        self.assert_fail_closed(level_up_now({}), 400, "missing_user_id")
        self.assert_fail_closed(level_up_now({"user_id": ""}), 400, "missing_user_id")
        self.assert_fail_closed(
            level_up_now({"user_id": None}), 400, "missing_user_id"
        )
        self.assert_fail_closed(
            level_up_now({"user_id": "   "}), 400, "missing_user_id"
        )
        self.assert_fail_closed(level_up_now({"user_id": 123}), 400, "invalid_user_id")
        self.assert_fail_closed(
            level_up_now({"user_id": ["pid"]}), 400, "invalid_user_id"
        )
        self.assert_fail_closed(
            level_up_now({"user_id": "ghost"}), 404, "unknown_user_id"
        )

    def test_an_unreadable_recorded_level_is_a_500_before_execution(self) -> None:
        """Design D2: a level this service cannot read as an integer is never
        coerced into a starting point for the comparison."""
        save = BOOT.save_document(PID)  # type: ignore[union-attr]
        first_map = save["maps"][0]
        saved = first_map["level"]
        first_map["level"] = "1"
        try:
            response = level_up_now(intent())
        finally:
            first_map["level"] = saved
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("no level this service can read", body["error"]["message"])
        # Nothing ran: the corpus file is byte-identical.
        self.assertEqual(harness.save_hashes(CORPUS), self.before_hashes)  # type: ignore[arg-type]
        self.assertEqual(level_now(), saved)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_curve_the_configuration_cannot_supply_is_a_500(self) -> None:
        """A content-side failure, never a client value: the committed curve is
        unreadable, so no level is derivable and nothing is executed."""
        disagreement()
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        original = BOOT.level_entry_count  # type: ignore[union-attr]
        BOOT.level_entry_count = lambda: None  # type: ignore[assignment]
        try:
            response = level_up_now(intent())
        finally:
            BOOT.level_entry_count = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("committed level curve does not resolve", body["error"]["message"])
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(level_now(), DISAGREEMENT_RECORDED)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        pristine()

    def test_a_non_increasing_curve_is_a_500_before_execution(self) -> None:
        """A committed curve the contract cannot describe as a ladder is reported
        rather than resolved into a level model."""
        disagreement()
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        original = BOOT.level_entry  # type: ignore[union-attr]

        def stub(position: Any) -> Any:
            # Duplicate the second entry's threshold onto the first, so the ladder
            # is no longer strictly increasing.
            if position == 0:
                return dict(BOOT.config()["levels"][1])  # type: ignore[union-attr]
            return original(position)

        BOOT.level_entry = stub  # type: ignore[assignment]
        try:
            response = level_up_now(intent())
        finally:
            BOOT.level_entry = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertEqual(body["error"]["message"], "unknown_level")
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(level_now(), DISAGREEMENT_RECORDED)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        pristine()

    def test_a_curve_entry_without_a_threshold_is_a_500_before_execution(self) -> None:
        disagreement()
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        original = BOOT.level_entry  # type: ignore[union-attr]

        def stub(position: Any) -> Any:
            if position == 2:
                return {"name": "Peon", "reward_type": "s", "reward_amount": 250}
            return original(position)

        BOOT.level_entry = stub  # type: ignore[assignment]
        try:
            response = level_up_now(intent())
        finally:
            BOOT.level_entry = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertEqual(body["error"]["message"], "unknown_level")
        self.assertEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(level_now(), DISAGREEMENT_RECORDED)
        pristine()

    def test_legacy_execution_raising_is_a_500(self) -> None:
        """A dispatcher failure after validation passed is a structured 500."""
        disagreement()
        before = level_now()
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        original = BOOT.execute_commands  # type: ignore[union-attr]

        def explode(user_id, envelope):
            raise RuntimeError("legacy blew up")

        BOOT.execute_commands = explode  # type: ignore[assignment]
        try:
            with harness.offline():
                response = app.test_client().post("/v0/level_up", json=intent())
        finally:
            BOOT.execute_commands = original  # type: ignore[assignment]
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("RuntimeError", body["error"]["message"])
        self.assertEqual(level_now(), before)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        pristine()


class PostExecutionProofTests(unittest.TestCase):
    """Design D5: both halves of the proof, or a structured 500.

    Each test resets the corpus to a disagreement state, runs the **real**
    legacy dispatcher, and only rewrites the **post**-execution read, so the
    level and the resources the save really holds are the true ones and the
    reported divergence is the only thing that fails.
    """

    def assert_internal(self, response: Any, fragment: str) -> None:
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn(fragment, body["error"]["message"])
        # Not a success and not a partial payload.
        self.assertNotIn("derived_level", body)
        self.assertNotIn("result", body)
        self.assertNotIn("curve", body)
        self.assertNotIn("resources", body)
        self.assertEqual(set(body), {"protocol", "ok", "error"})
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_a_level_that_is_not_the_derived_level_is_a_500_not_a_success(self) -> None:
        """The structural half.  No level_up branch can fail to write the value
        it was given, so the stub reproduces a post-state legacy could never
        report; the endpoint must refuse it anyway rather than trust the legacy
        status."""
        disagreement()
        response = post_with_level_stub(lambda level: 99, intent())
        self.assert_internal(response, "not the derived")

    def test_a_level_that_did_not_move_is_a_500(self) -> None:
        """The strongest form: the reported level is exactly the pre-execution
        one, so nothing advanced."""
        disagreement()
        response = post_with_level_stub(lambda level: DISAGREEMENT_RECORDED, intent())
        self.assert_internal(response, "not the derived")

    def test_a_level_one_short_of_the_derived_level_is_a_500(self) -> None:
        disagreement()
        response = post_with_level_stub(
            lambda level: DISAGREEMENT_DERIVED - 1, intent()
        )
        self.assert_internal(response, "not the derived")

    def test_a_level_one_past_the_derived_level_is_a_500(self) -> None:
        """The branch writes exactly what it was given — so an off-by-one in the
        conversion would surface here rather than pass."""
        disagreement()
        response = post_with_level_stub(
            lambda level: DISAGREEMENT_DERIVED + 1, intent()
        )
        self.assert_internal(response, "not the derived")

    def test_a_level_the_service_cannot_read_afterwards_is_a_500(self) -> None:
        disagreement()
        response = post_with_level_stub(lambda level: None, intent())
        self.assert_internal(response, "not the derived")

    def test_a_non_integer_level_afterwards_is_a_500(self) -> None:
        disagreement()
        response = post_with_level_stub(lambda level: "2", intent())  # type: ignore[return-value]
        self.assert_internal(response, "not the derived")

    def test_a_moved_resource_is_reported_not_trusted(self) -> None:
        """The value-level half.  A balance the **neutral** vector leaves alone
        moving means the reported resources are not the derived ones — the check
        that distinguishes a correct level-up from a resource-minting exploit."""
        disagreement()
        response = post_with_resources_stub(
            lambda values: dict(values, gold=values["gold"] + 1), intent()
        )
        self.assert_internal(response, "resource gold")
        message = response.get_json()["error"]["message"]
        self.assertIn("pre-execution", message)
        self.assertIn("moves no resource", message)

    def test_every_resource_that_moved_is_a_500(self) -> None:
        """All seven slots of the neutral vector, one at a time."""
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                disagreement()
                response = post_with_resources_stub(
                    lambda values, moved=name: dict(
                        values, **{moved: values[moved] + 1}
                    ),
                    intent(),
                )
                self.assert_internal(response, "resource %s" % name)

    def test_a_resource_that_disappeared_is_a_500(self) -> None:
        """The other direction: a balance the vector never touches must still be
        there unchanged."""
        disagreement()
        response = post_with_resources_stub(
            lambda values: dict(values, mana=values["mana"] + 5), intent()
        )
        self.assert_internal(response, "resource mana")

    def test_the_proof_source_contains_both_halves(self) -> None:
        """The endpoint reads the recorded level **and** the resources *before*
        dispatch, and requires both the exact level and the exact absence of
        movement."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        self.assertIn("level_before = boot.map_level(user_id)", source)
        self.assertIn("resources_before = boot.resources(user_id)", source)
        self.assertIn("if level_after != derived:", source)
        self.assertIn(
            "if resources_after[name] != resources_before[name]:", source
        )
        # Both pre-execution reads and both proof halves live inside the level
        # route, in the documented order.
        route = source[source.index("def v0_level_up()"):]
        route = route[: route.index('app.config["COMPAT_LEGACY_CORPUS"]')]
        self.assertLess(
            route.index("level_before = boot.map_level(user_id)"),
            route.index("boot.execute_commands(user_id, envelope_payload)"),
        )
        self.assertLess(
            route.index("resources_before = boot.resources(user_id)"),
            route.index("boot.execute_commands(user_id, envelope_payload)"),
        )
        self.assertLess(
            route.index("boot.execute_commands(user_id, envelope_payload)"),
            route.index("if level_after != derived:"),
        )
        self.assertLess(
            route.index("if level_after != derived:"),
            route.index("if resources_after[name] != resources_before[name]:"),
        )
        # And both refusals precede the dispatcher too.
        self.assertLess(
            route.index("ERROR_LEVEL_ALREADY_CURRENT"),
            route.index("boot.execute_commands(user_id, envelope_payload)"),
        )
        self.assertLess(
            route.index("ERROR_XP_BELOW_THRESHOLD"),
            route.index("boot.execute_commands(user_id, envelope_payload)"),
        )


class LevelUpContractTests(unittest.TestCase):
    """Retained guarantees: boot endpoints never persist, saves stay put."""

    def test_session_and_bootstrap_stay_byte_identical_after_level_ups(self) -> None:
        disagreement()
        response = level_up_now(intent())
        self.assertEqual(response.status_code, 200)
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
        pristine()

    def test_level_ups_never_touch_working_tree_saves(self) -> None:
        disagreement()
        before = harness.save_hashes(CORPUS)  # type: ignore[arg-type]
        response = level_up_now(intent())
        self.assertEqual(response.status_code, 200)
        # The corpus save changed; the working tree did not move.
        self.assertNotEqual(harness.save_hashes(CORPUS), before)  # type: ignore[arg-type]
        self.assertEqual(level_now(), DISAGREEMENT_DERIVED)
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)
        pristine()

    def test_a_level_up_leaves_every_placement_alone(self) -> None:
        """The whole ``items`` mapping is byte-identical, including the rows the
        other ten committed fixtures address."""
        disagreement()
        seed_items = harness.load_seed()["maps"][0]["items"]  # type: ignore[index]
        before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        self.assertEqual(before_items, seed_items)

        response = level_up_now(intent())

        self.assertEqual(response.status_code, 200)
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
        pristine()

    def test_the_legacy_accessors_agree_with_the_map(self) -> None:
        disagreement()
        self.assertEqual(level_now(), DISAGREEMENT_RECORDED)
        self.assertEqual(BOOT.level_entry_count(), 100)  # type: ignore[union-attr]
        self.assertIsNotNone(BOOT.level_entry(0))  # type: ignore[union-attr]
        self.assertIsNone(BOOT.level_entry(100))  # type: ignore[union-attr]
        self.assertEqual(resources_now()["xp"], DISAGREEMENT_XP)
        self.assertTrue(BOOT.has_map_item(PID, 2))  # type: ignore[union-attr]
        self.assertFalse(BOOT.has_map_item(PID, 41))  # type: ignore[union-attr]
        pristine()

    def test_the_endpoint_derives_the_legacy_envelope_it_sends(self) -> None:
        """One derivation: the endpoint, the fixture, and this suite build the
        same six-key envelope from the same module."""
        built = level_envelope.build_envelope(level=2, ts=1700000000)
        self.assertEqual(
            built["commands"], [[0, "level_up", [2], [0, 0, 0, 0, 0, 0, 0, 0]]]
        )
        self.assertEqual(sorted(built), sorted(level_envelope.ENVELOPE_KEYS))
        self.assertIs(compat_service.level_envelope, level_envelope)

    def test_the_endpoint_resolves_every_level_through_the_named_conversion(self) -> None:
        """Design D1's single-named-place requirement, asserted on the route: the
        conversion is the envelope module's, and the route contains no level
        arithmetic of its own."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = source[source.index("def v0_level_up()"):]
        route = route[: route.index('app.config["COMPAT_LEGACY_CORPUS"]')]
        self.assertIn("level_envelope.entry_index_for_level(", route)
        self.assertIn("level_envelope.derived_level_for(", route)
        self.assertIn("level_envelope.entry_for_level(", route)
        self.assertIn("level_envelope.threshold_for(", route)
        self.assertIn("level_envelope.next_threshold(", route)
        self.assertIn("level_envelope.remaining_for(", route)
        # No ``levels[level - 1]``-style arithmetic survives in the route.
        self.assertNotRegex(route, r"rows\[\s*level\s*[-+]")

    def test_the_endpoint_carries_no_grid_or_placement_logic(self) -> None:
        """Design D7 in the delivered sense: the level ledger and nothing else."""
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = source[source.index("def v0_level_up()"):]
        route = route[: route.index('app.config["COMPAT_LEGACY_CORPUS"]')]
        import ast
        import textwrap

        code_names: List[str] = []
        for node in ast.walk(ast.parse(textwrap.dedent(route.lstrip("\n")))):
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
            "map_item",
            "map_items",
            "item_index",
            "orientation",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)
        # …and the boundaries are stated rather than left for a reader to find.
        for named in ("Design D1", "Design D4", "Design D5", "Design D7"):
            with self.subTest(named=named):
                self.assertIn(named, route)


class LevelUpSurfaceTests(unittest.TestCase):
    """Route surface: methods, loopback, and the no-server guarantee."""

    def test_get_is_not_allowed(self) -> None:
        with harness.offline():
            response = CLIENT.get("/v0/level_up")  # type: ignore[union-attr]
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
            unknown = CLIENT.get("/v0/level_up/unknown")  # type: ignore[union-attr]
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error"]["code"], "not_found")

    def test_the_delivered_state_mutating_routes_still_exist(self) -> None:
        """This is the tenth state-mutating surface; the other nine are
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
            "/v0/level_up",
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
            "/v0/level_up",
        ):
            with self.subTest(route=route):
                self.assertIn(route, scope)

    def test_the_module_docstring_documents_the_level_surface(self) -> None:
        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        for named in (
            "POST /v0/level_up",
            "derived_level",
            "level_before",
            "level_after",
            "curve",
            "level_already_current",
            "xp_below_threshold",
            "one-based",
            "zero-based",
            "derived-provisional",
            "xp_below_threshold",
            "add_xp_unit",
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