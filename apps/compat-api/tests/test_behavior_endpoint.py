#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/resurrect`` behaviour tests (OpenSpec ``godot-unit-behaviors``).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so the suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across revival execution.

Every test snapshots the corpus at its own start and asserts its post-condition
against that snapshot, so the suite is order-independent.  Tests that need a
resurrectable ledger entry set one up through :func:`set_ledger` (in memory
**and** on the corpus file, exactly as the delivered level and expand suites do
for their own disagreement states) and re-take their baseline afterwards, so the
"nothing changed" claim is always about the request under test.  That seeding is a
**disposable-corpus-only** mechanism: it is not the executed-legacy fixture the
change deliberately does not claim, and it never touches a committed save.

The committed corpus is itself a **refusal** case: its
``privateState["deadHeroes"]`` is present and ``{}``, and it places only
buildings, so **0 of 40** placed rows are resurrectable.  Every executing success
case therefore begins from a seeded ledger naming a committed **unit** id.

Covered:

* **a successful revival** — the ledger entry decrements and is **deleted at
  zero**, the addressed map key now records the **derived** item id at the
  **addressed** cell, **every one of the seven stored resources is unchanged**,
  the response carries both gates, the derived map key and item id, the recorded
  committed ``resurrectable`` and ``syringes``, the **no-echo** of the discarded
  ``used_syringe``, and the persisted corpus file matches the response.
* **the five refusals** — ``unresolvable_cell``, ``ambiguous_cell``,
  ``unresolvable_ledger_entry``, ``ambiguous_ledger``, and
  ``not_resurrectable`` — each with its named code, an **empty** payload, and a
  corpus left byte-identical.
* **the derived, not client-supplied, target** — a request carrying ``map_key``,
  ``index``, ``item_id``, ``used_syringe``, ``syringe``, ``cost``, ``price``,
  ``resources_changed``, and ``vector`` changes nothing and is never echoed.
* **the two-part post-execution proof** — a ledger entry that is **not** deleted,
  a row that does not record the derived item id, a row that does not record the
  addressed cell, and **any** stored resource that moved, each fail closed with
  ``internal_error`` rather than reporting legacy's success.  Each is exercised
  by a stub that lets the real dispatcher run and rewrites only the **post**
  read.
* **the fail-closed projection** — an absent ledger, a non-object ledger, a
  non-string key, a non-integer count, an over-long row, and a non-row, each
  reported unresolvable with its recorded state intact.
* **the two gates and the three doors** — both named with their recorded source
  lines, no third invented, ``kill`` recorded as never reaching the ledger, and
  ``push_dead_unit`` recorded as an engine helper rather than a branch.
* **the seed seam** — its format, its refusals, and that an absent variable
  leaves the save untouched.
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import compat_test_harness as harness

import behavior_envelope
import compat_legacy
import compat_service

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed corpus's own cells.  Row 1 is the committed Command Center at
# (51, 41); the corpus places 40 rows across 40 DISTINCT cells, so no cell is
# ambiguous until a test creates one.
COMMITTED_KEY = "1"
COMMITTED_CELL = (51, 41)
COMMITTED_ITEM = 26
COMMITTED_PLACEMENTS = 40
COMMITTED_DISTINCT_CELLS = 40

# A committed unit that IS resurrectable (426 of 429 units carry the flag) and a
# committed building that is NOT (0 of 470 buildings do).
RESURRECTABLE_UNIT = 1001
NON_RESURRECTABLE_BUILDING = 23
AMBIGUOUS_LEDGER_UNIT = 1040

RESOURCE_NAMES = behavior_envelope.RESOURCE_NAMES


def set_ledger(bag: Optional[Dict[str, int]]) -> Dict[str, int]:
    """Write the disposable corpus's dead-hero ledger, in memory **and** on disk.

    ``engine.resurrect_hero`` mutates ``privateState["deadHeroes"]`` in place
    (``engine.py:172-181``) and the endpoint reads the in-memory save through
    the legacy accessors while this suite's post-execution assertions read the
    persisted file, so both representations are written here: a test-only,
    contained mechanism, never a claim about legacy behaviour, and never touching
    a working-tree save.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["privateState"][behavior_envelope.LEDGER_KEY] = dict(bag or {})
    write_corpus(save)
    return dict(bag or {})


def set_cells(extra: Dict[str, Tuple[int, int]]) -> None:
    """Move or add placement rows so a cell collision can be exercised."""
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    rows = save["maps"][0]["items"]
    for key, (x, y) in extra.items():
        if key not in rows:
            rows[key] = [COMMITTED_ITEM, x, y, 0, 0, [], {}, 1]
            continue
        rows[key][1] = x
        rows[key][2] = y
    write_corpus(save)


def write_corpus(save: Dict[str, Any]) -> None:
    path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def reset_cells() -> None:
    """Restore the committed corpus's own placement rows."""
    seed = harness.load_seed()
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["maps"][0]["items"] = copy.deepcopy(seed["maps"][0]["items"])
    write_corpus(save)


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
        raise AssertionError("a revival execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def resurrect_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/resurrect", json=payload)  # type: ignore[union-attr]


def corpus_save() -> Dict[str, Any]:
    return harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]


def ledger_now() -> Dict[str, Any]:
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    return save["privateState"][behavior_envelope.LEDGER_KEY]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def intent(x: Any = COMMITTED_CELL[0], y: Any = COMMITTED_CELL[1]) -> Dict[str, Any]:
    """The whole contract: a save identity and a cell, and nothing else."""
    return {"user_id": PID, "x": x, "y": y}


def seeded() -> Dict[str, Any]:
    """Reset to the committed placements plus one seeded resurrectable entry."""
    reset_cells()
    set_ledger({"%d" % RESURRECTABLE_UNIT: 2})
    return snapshot()


def snapshot() -> Dict[str, Any]:
    return {
        "ledger": copy.deepcopy(ledger_now()),
        "resources": copy.deepcopy(resources_now()),
        "items": copy.deepcopy(BOOT.map_items(PID)),  # type: ignore[union-attr]
    }


class Result:
    """A captured response plus the app that produced it (see the level suite)."""

    def __init__(self, app: Any, response: Any) -> None:
        self.app = app
        self.response = response

    @property
    def status_code(self) -> int:
        return int(self.response.status_code)

    def get_json(self) -> Any:
        return self.response.get_json()


def _save_document_rewritten_after_execution(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]]
):
    """A ``save_document`` stub that rewrites only the **post**-execution read."""
    original = BOOT.save_document  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, Any]:
        state["seen"] += 1
        save = original(user_id)
        if state["seen"] == 1:
            return save
        return transform(copy.deepcopy(save))

    return stub


def _map_items_rewritten_after_execution(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]]
):
    """A ``map_items`` stub that rewrites only the **post**-execution read."""
    original = BOOT.map_items  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, Any]:
        state["seen"] += 1
        items = original(user_id)
        if state["seen"] == 1:
            return items
        return transform(items)

    return stub


def _resources_rewritten_after_execution(
    transform: Callable[[Dict[str, int]], Dict[str, int]]
):
    """A ``resources`` stub that rewrites only the **post**-execution read."""
    original = BOOT.resources  # type: ignore[union-attr]
    state = {"seen": 0}

    def stub(user_id: str) -> Dict[str, int]:
        state["seen"] += 1
        values = original(user_id)
        if state["seen"] == 1:
            return values
        return transform(values)

    return stub


def post_with_save_stub(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]], payload: Dict[str, Any]
) -> Result:
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.save_document  # type: ignore[union-attr]
    BOOT.save_document = _save_document_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/resurrect", json=payload))
    finally:
        BOOT.save_document = original  # type: ignore[assignment]


def post_with_items_stub(
    transform: Callable[[Dict[str, Any]], Dict[str, Any]], payload: Dict[str, Any]
) -> Result:
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.map_items  # type: ignore[union-attr]
    BOOT.map_items = _map_items_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/resurrect", json=payload))
    finally:
        BOOT.map_items = original  # type: ignore[assignment]


def post_with_resources_stub(
    transform: Callable[[Dict[str, int]], Dict[str, int]], payload: Dict[str, Any]
) -> Result:
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    original = BOOT.resources  # type: ignore[union-attr]
    BOOT.resources = _resources_rewritten_after_execution(transform)  # type: ignore[assignment]
    try:
        with harness.offline():
            return Result(app, app.test_client().post("/v0/resurrect", json=payload))
    finally:
        BOOT.resources = original  # type: ignore[assignment]


# ---------------------------------------------------------------- envelope --
class EnvelopeTests(unittest.TestCase):
    """The six-key batch envelope and the neutral vector (design D1/D3)."""

    def test_the_envelope_carries_exactly_one_command(self) -> None:
        built = behavior_envelope.build_envelope(7, RESURRECTABLE_UNIT, 4, 9, ts=5)
        self.assertEqual(tuple(built.keys()), behavior_envelope.ENVELOPE_KEYS)
        self.assertEqual(len(built["commands"]), 1)
        self.assertEqual(built["commands"][0][0], 0)
        self.assertEqual(built["commands"][0][1], "resurrect_hero")
        self.assertEqual(
            built["commands"][0][2], [7, RESURRECTABLE_UNIT, 4, 9, 0]
        )
        self.assertEqual(
            built["commands"][0][3], [0] * behavior_envelope.RESOURCE_VECTOR_SLOTS
        )

    def test_the_derived_syringe_is_the_documented_inert_zero(self) -> None:
        built = behavior_envelope.build_envelope(1, RESURRECTABLE_UNIT, 4, 9, ts=5)
        args = built["commands"][0][2]
        self.assertEqual(len(args), behavior_envelope.LEGACY_ARGUMENT_COUNT)
        self.assertEqual(args[behavior_envelope.ARG_USED_SYRINGE], 0)
        self.assertEqual(
            behavior_envelope.DERIVED_USED_SYRINGE,
            0,
            "the discarded argument is sent as a literal zero",
        )
        self.assertIn(
            "DISCARD", behavior_envelope.SYRINGE_DISCARD_NOTE
        )
        self.assertIn("NO SYRINGE COST", behavior_envelope.SYRINGE_DISCARD_NOTE)
        self.assertIn("NEVER ECHOES", behavior_envelope.SYRINGE_DISCARD_NOTE)

    def test_the_other_four_arguments_are_never_client_supplied(self) -> None:
        built = behavior_envelope.build_envelope(3, 1001, 4, 9, ts=5)
        args = built["commands"][0][2]
        self.assertEqual(args[behavior_envelope.ARG_INDEX], 3)
        self.assertEqual(args[behavior_envelope.ARG_ITEM_ID], 1001)
        self.assertEqual(args[behavior_envelope.ARG_X], 4)
        self.assertEqual(args[behavior_envelope.ARG_Y], 9)

    def test_only_the_neutral_vector_is_derivable(self) -> None:
        self.assertEqual(
            behavior_envelope.neutral_vector(),
            [0] * behavior_envelope.RESOURCE_VECTOR_SLOTS,
        )
        with self.assertRaises(behavior_envelope.EnvelopeError) as raised:
            behavior_envelope.validate_vector([0, 1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(raised.exception.code, "invalid_vector")
        with self.assertRaises(behavior_envelope.EnvelopeError):
            behavior_envelope.validate_vector([0, -1, 0, 0, 0, 0, 0, 0])
        with self.assertRaises(behavior_envelope.EnvelopeError):
            behavior_envelope.validate_vector([0] * 7)
        with self.assertRaises(behavior_envelope.EnvelopeError):
            behavior_envelope.validate_vector([0.0] * 8)

    def test_a_fresh_vector_is_returned_every_call(self) -> None:
        first = behavior_envelope.neutral_vector()
        first[0] = 5
        self.assertEqual(behavior_envelope.neutral_vector()[0], 0)

    def test_structural_failures_are_named(self) -> None:
        for payload, code in (
            ({"map_key": "1", "item_id": 1, "x": 1, "y": 1}, "invalid_map_key"),
            ({"map_key": 1, "item_id": "1", "x": 1, "y": 1}, "invalid_item_id"),
            ({"map_key": 1, "item_id": 1, "x": 1, "y": "1"}, "invalid_cell"),
            ({"map_key": 1, "item_id": 1, "x": True, "y": 1}, "invalid_cell"),
            ({"map_key": 1, "item_id": 1, "x": 1, "y": 400}, "invalid_cell"),
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(behavior_envelope.EnvelopeError) as raised:
                    behavior_envelope.build_envelope(ts=5, **payload)
                self.assertEqual(raised.exception.code, code)
        with self.assertRaises(behavior_envelope.EnvelopeError) as raised:
            behavior_envelope.build_envelope(1, 1001, 1, 1, ts=-1)
        self.assertEqual(raised.exception.code, "invalid_timestamp")

    def test_ts_defaults_to_a_non_negative_integer(self) -> None:
        built = behavior_envelope.build_envelope(1, RESURRECTABLE_UNIT, 4, 9)
        self.assertIsInstance(built["ts"], int)
        self.assertGreaterEqual(built["ts"], 0)


# ------------------------------------------------------------ the ledger --
class LedgerProjectionTests(unittest.TestCase):
    """The fail-closed projection and the delete-at-zero rule (design D1)."""

    def test_every_recorded_entry_is_reported_verbatim(self) -> None:
        for raw, expected in (
            ({}, []),
            ({"1001": 1}, [{"item_id": "1001", "count": 1}]),
            ({"1001": 7, "1040": 2}, [
                {"item_id": "1001", "count": 7},
                {"item_id": "1040", "count": 2},
            ]),
            ({"1001": 999999}, [{"item_id": "1001", "count": 999999}]),
        ):
            with self.subTest(raw=raw):
                projection = behavior_envelope.project_ledger(raw)
                self.assertTrue(projection["ok"])
                self.assertTrue(projection["resolvable"])
                self.assertEqual(projection["entries"], expected)

    def test_no_threshold_cap_or_clamp_is_applied(self) -> None:
        projection = behavior_envelope.project_ledger({"1001": 1000000})
        self.assertEqual(projection["entries"], [{"item_id": "1001", "count": 1000000}])
        self.assertEqual(projection["total"], 1000000)
        # A count of zero is reported as recorded, never normalised away and
        # never read as absent: the projection reports, it does not judge.
        self.assertEqual(
            behavior_envelope.project_ledger({"1001": 0})["entries"],
            [{"item_id": "1001", "count": 0}],
        )

    def test_an_absent_ledger_is_unresolvable_with_its_state_intact(self) -> None:
        projection = behavior_envelope.project_ledger(None)
        self.assertFalse(projection["ok"])
        self.assertFalse(projection["resolvable"])
        self.assertEqual(projection["reason"], "invalid_ledger")
        self.assertEqual(projection["entries"], [])
        self.assertEqual(projection["entry_count"], 0)
        self.assertEqual(projection["recorded_state"], None)
        self.assertFalse(projection["recorded_present"])
        self.assertIn("ABSENT", projection["error"])

    def test_a_non_object_ledger_is_refused(self) -> None:
        for raw in ([], ["1001"], "1001", 5, 1.5, True):
            with self.subTest(raw=raw):
                projection = behavior_envelope.project_ledger(raw)
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["reason"], "invalid_ledger")
                self.assertEqual(projection["entries"], [])
                self.assertEqual(projection["recorded_state"], raw)

    def test_a_non_string_key_is_refused_and_not_coerced(self) -> None:
        projection = behavior_envelope.project_ledger({1001: 1})
        self.assertFalse(projection["ok"])
        self.assertEqual(projection["reason"], "invalid_ledger")
        self.assertIn("not the text of an item id", projection["error"])

    def test_a_non_integer_count_is_refused_and_not_coerced(self) -> None:
        for raw in ({"1001": "1"}, {"1001": 1.5}, {"1001": True}, {"1001": None}):
            with self.subTest(raw=raw):
                projection = behavior_envelope.project_ledger(raw)
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["reason"], "invalid_ledger")
                self.assertEqual(projection["entries"], [])
                self.assertEqual(projection["recorded_keys"], ["1001"])

    def test_the_ledger_entries_accessor_agrees_with_the_projection(self) -> None:
        self.assertEqual(
            behavior_envelope.ledger_entries({"1001": 2, "1040": 1}),
            {"1001": 2, "1040": 1},
        )
        with self.assertRaises(behavior_envelope.EnvelopeError):
            behavior_envelope.ledger_entries(None)

    def test_the_decrement_deletes_the_key_at_zero(self) -> None:
        derived = behavior_envelope.expected_ledger({"1001": 1}, RESURRECTABLE_UNIT)
        self.assertEqual(derived["entries"], {})
        self.assertTrue(derived["removed"])
        self.assertEqual(derived["count_before"], 1)
        self.assertEqual(derived["count_after"], 0)
        self.assertTrue(
            derived["removed"],
            "reaching zero DELETES the key rather than storing a zero",
        )

    def test_the_decrement_keeps_a_count_above_one(self) -> None:
        derived = behavior_envelope.expected_ledger({"1001": 3}, RESURRECTABLE_UNIT)
        self.assertEqual(derived["entries"], {"1001": 2})
        self.assertFalse(derived["removed"])
        self.assertEqual(derived["count_after"], 2)

    def test_an_absent_entry_is_a_silent_no_op(self) -> None:
        derived = behavior_envelope.expected_ledger({"1001": 1}, 1040)
        self.assertEqual(derived["entries"], {"1001": 1})
        self.assertFalse(derived["present_before"])
        self.assertFalse(derived["removed"])
        self.assertEqual(derived["count_before"], 0)

    def test_the_divergence_check_names_the_first_difference(self) -> None:
        self.assertIsNone(
            behavior_envelope.ledger_divergence({"1001": 1}, {}, RESURRECTABLE_UNIT)
        )
        not_deleted = behavior_envelope.ledger_divergence(
            {"1001": 1}, {"1001": 1}, RESURRECTABLE_UNIT
        )
        self.assertIn("still holds", not_deleted)
        stale = behavior_envelope.ledger_divergence(
            {"1001": 2}, {"1001": 5}, RESURRECTABLE_UNIT
        )
        self.assertIn("the derived", stale)
        # A seed the legacy increment never produces: an extra entry appears.
        extra = behavior_envelope.ledger_divergence(
            {"1001": 1}, {"1001": 0, "1040": 1}, RESURRECTABLE_UNIT
        )
        self.assertTrue(
            extra is not None, "an invented ledger entry is a divergence"
        )
        self.assertIn("still holds", extra)
        self.assertIn(
            "unreadable",
            behavior_envelope.ledger_divergence({"1001": 1}, None, RESURRECTABLE_UNIT),
        )

    def test_the_migration_note_is_recorded_and_is_not_behaviour(self) -> None:
        self.assertIn("version.py:26-30", behavior_envelope.LEDGER_MIGRATION_NOTE)
        self.assertIn("MIGRATION", behavior_envelope.LEDGER_MIGRATION_NOTE)


# ------------------------------------------------- the gates and the doors --
class GatesAndDoorsTests(unittest.TestCase):
    """Both gates named, no third invented, three doors classified."""

    def test_exactly_two_gates_are_named_with_their_source_lines(self) -> None:
        gates = behavior_envelope.gates()
        self.assertEqual(len(gates), behavior_envelope.GATE_COUNT)
        self.assertEqual(len(gates), 2)
        names = [str(gate["gate"]) for gate in gates]
        self.assertEqual(names, ["player_team_one", "resurrectable_positive"])
        self.assertEqual(gates[0]["source"], "engine.py:151 (push_dead_unit)")
        self.assertEqual(gates[1]["source"], "engine.py:159,162 (push_dead_unit)")
        for gate in gates:
            self.assertTrue(gate["committed"])
            self.assertTrue(str(gate["checks"]))
            self.assertTrue(str(gate["note"]))

    def test_no_third_gate_is_invented(self) -> None:
        self.assertIn("EXACTLY TWO GATES", behavior_envelope.NO_THIRD_GATE)
        self.assertIn("no third", behavior_envelope.NO_THIRD_GATE.lower())
        self.assertEqual(len(behavior_envelope.gates()), 2)

    def test_the_three_doors_are_named_and_classified(self) -> None:
        inventory = behavior_envelope.command_inventory()
        self.assertEqual(
            [entry["command"] for entry in inventory],
            ["kill", "sell", "resurrect_hero"],
        )
        reaching = [entry for entry in inventory if entry["reaches_ledger"]]
        self.assertEqual(
            [entry["command"] for entry in reaching],
            ["sell", "resurrect_hero"],
        )
        self.assertEqual(len(reaching), behavior_envelope.LEDGER_REACHING_COMMAND_COUNT)
        self.assertEqual(
            tuple(behavior_envelope.ledger_reaching_commands()),
            behavior_envelope.LEDGER_REACHING_COMMANDS,
        )
        self.assertEqual(
            tuple(behavior_envelope.BRANCHES_THAT_BYPASS_LEDGER), ("kill",)
        )

    def test_kill_is_recorded_as_never_touching_the_ledger(self) -> None:
        kill = behavior_envelope.command_inventory()[0]
        self.assertFalse(kill["reaches_ledger"])
        self.assertIn("NEVER touches", kill["effect"])
        self.assertIn("command.py:169-181", kill["source"])

    def test_sell_reaches_the_ledger_only_behind_the_combat_guard(self) -> None:
        sell = behavior_envelope.command_inventory()[1]
        self.assertTrue(sell["reaches_ledger"])
        self.assertEqual(sell["guard"], "reason == 'KILL'")
        self.assertIn("push_dead_unit", sell["through"])
        self.assertIn("closed_in_practice", sell)
        self.assertIn("godot-building-sell", sell["closed_in_practice"])

    def test_the_engine_helpers_are_distinguished_from_branches(self) -> None:
        helpers = behavior_envelope.ENGINE_HELPERS
        self.assertEqual(
            [entry["helper"] for entry in helpers],
            ["push_dead_unit", "resurrect_hero"],
        )
        for entry in helpers:
            self.assertFalse(entry["is_dispatcher_branch"])
        self.assertEqual(
            behavior_envelope.NAMED_BRANCH_COUNT,
            63,
            "the dispatcher branch count stays distinct from the "
            "ledger-reaching count, which is 2",
        )
        self.assertEqual(behavior_envelope.LEDGER_REACHING_COMMAND_COUNT, 2)

    def test_resurrect_hero_records_the_discard_and_the_client_placement(self) -> None:
        branch = behavior_envelope.command_inventory()[2]
        self.assertTrue(branch["reaches_ledger"])
        self.assertIn("DELETES the key", branch["effect"])
        self.assertIn("CLIENT-SUPPLIED", branch["mutates_also"])
        self.assertIn("DISCARDED", branch["discarded_argument"])
        self.assertIn("command.py:625-635", branch["source"])


# ------------------------------------------------------ the committed fields --
class CommittedContentTests(unittest.TestCase):
    """The measured committed distributions, against the loaded configuration."""

    def _loaded_items(self) -> List[Dict[str, Any]]:
        items = BOOT.config().get("items")  # type: ignore[union-attr]
        self.assertIsInstance(items, list)
        return [row for row in items if isinstance(row, dict)]

    def _flag_positive(self, rows: List[Dict[str, Any]]) -> Tuple[int, int]:
        positive = 0
        carried = 0
        for row in rows:
            raw = row.get("properties")
            decoded: Any = raw
            if isinstance(raw, (str, bytes)):
                decoded = json.loads(raw)
            if not isinstance(decoded, dict):
                continue
            if behavior_envelope.RESURRECTABLE_FLAG not in decoded:
                continue
            carried += 1
            try:
                if int(str(decoded[behavior_envelope.RESURRECTABLE_FLAG])) > 0:
                    positive += 1
            except (TypeError, ValueError):
                continue
        return positive, carried

    def test_resurrectable_is_positive_on_426_of_429_units(self) -> None:
        rows = self._loaded_items()
        units = [row for row in rows if row.get("type") == "u"]
        buildings = [row for row in rows if row.get("type") == "b"]
        self.assertEqual(
            len(units), behavior_envelope.RESURRECTABLE_UNITS_OF
        )
        self.assertEqual(
            len(buildings), behavior_envelope.RESURRECTABLE_BUILDINGS_OF
        )
        positive, carried = self._flag_positive(units)
        self.assertEqual(carried, positive, "every carried flag is positive")
        self.assertEqual(
            positive, behavior_envelope.RESURRECTABLE_UNITS_POSITIVE
        )
        self.assertEqual(
            self._flag_positive(buildings)[0],
            behavior_envelope.RESURRECTABLE_BUILDINGS_POSITIVE,
        )

    def test_resurrectable_is_a_unit_only_flag(self) -> None:
        self.assertIn("UNIT-ONLY", behavior_envelope.UNIT_ONLY_NOTE)
        self.assertIn("426", behavior_envelope.UNIT_ONLY_NOTE)
        self.assertIn("470", behavior_envelope.UNIT_ONLY_NOTE)

    def test_syringes_has_six_distinct_unit_values_and_no_legacy_consumer(self) -> None:
        rows = self._loaded_items()
        units = {
            str(row.get("syringes"))
            for row in rows
            if row.get("type") == "u"
        }
        buildings = {
            str(row.get("syringes"))
            for row in rows
            if row.get("type") == "b"
        }
        self.assertEqual(units, set(behavior_envelope.SYRINGES_UNIT_VALUES))
        self.assertEqual(len(units), 6)
        self.assertEqual(buildings, set(behavior_envelope.SYRINGES_BUILDING_VALUES))
        distribution: Dict[str, int] = {}
        for row in rows:
            if row.get("type") != "u":
                continue
            distribution[str(row.get("syringes"))] = (
                distribution.get(str(row.get("syringes")), 0) + 1
            )
        self.assertEqual(distribution, behavior_envelope.SYRINGES_UNIT_VALUES)

    def test_clicks_to_build_is_zero_on_every_unit(self) -> None:
        rows = self._loaded_items()
        units: Dict[str, int] = {}
        buildings: Dict[str, int] = {}
        specials: Dict[str, int] = {}
        for row in rows:
            kind = str(row.get("type"))
            target = (
                units if kind == "u"
                else buildings if kind == "b"
                else specials
            )
            text = str(row.get("clicks_to_build"))
            target[text] = target.get(text, 0) + 1
        self.assertEqual(units, behavior_envelope.CLICKS_TO_BUILD_UNIT_VALUES)
        self.assertEqual(buildings, behavior_envelope.CLICKS_TO_BUILD_BUILDING_VALUES)
        # The committed investigation records "3 distinct"; measured over the
        # whole committed content it is 2, and the 299th row carrying a 1 is the
        # single committed special rather than a building.
        distinct = sorted(set(units) | set(buildings) | set(specials))
        self.assertEqual(
            len(distinct), behavior_envelope.CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT
        )
        self.assertEqual(
            behavior_envelope.CLICKS_TO_BUILD_DISTINCT_RECORDED, 3
        )
        self.assertIn(
            "CORRECTION", behavior_envelope.CLICKS_TO_BUILD_CORRECTION
        )
        self.assertEqual(
            specials,
            {"1": 1},
            "the single committed special (id 925, type 'l') is the row the "
            "recorded third value counted",
        )
        self.assertIn(
            "REFERENCED AND NOT REIMPLEMENTED",
            behavior_envelope.CLICKS_TO_BUILD_BOUNDARY,
        )
        self.assertIn("engine.py:26", behavior_envelope.CLICKS_TO_BUILD_BOUNDARY)
        self.assertIn(
            "godot-building-construction", behavior_envelope.CLICKS_TO_BUILD_BOUNDARY
        )

    def test_the_zero_consumer_field_count_is_measured_not_asserted(self) -> None:
        fields = [entry["field"] for entry in behavior_envelope.ZERO_CONSUMER_FIELDS]
        self.assertEqual(len(fields), behavior_envelope.ZERO_CONSUMER_COUNT)
        self.assertEqual(len(set(fields)), behavior_envelope.ZERO_CONSUMER_COUNT)
        # MEASURED CORRECTION: the committed investigation says "twenty" and then
        # names twenty-one.  The named list is countable and every entry measures
        # zero, so the count is 21 — and with the two consumed fields the
        # behavioural total is 23, not 22.
        self.assertEqual(behavior_envelope.ZERO_CONSUMER_COUNT, 21)
        self.assertEqual(behavior_envelope.ZERO_CONSUMER_COUNT_RECORDED, 20)
        self.assertEqual(behavior_envelope.BEHAVIOURAL_FIELD_COUNT, 23)
        self.assertEqual(behavior_envelope.BEHAVIOURAL_FIELD_COUNT_RECORDED, 22)
        self.assertEqual(
            behavior_envelope.ZERO_CONSUMER_COUNT + len(
                behavior_envelope.CONSUMED_BEHAVIOURAL_FIELDS
            ),
            behavior_envelope.BEHAVIOURAL_FIELD_COUNT,
        )
        consumed = {
            str(entry["field"]) for entry in behavior_envelope.CONSUMED_BEHAVIOURAL_FIELDS
        }
        self.assertEqual(consumed, {"resurrectable", "clicks_to_build"})
        self.assertFalse(
            consumed & set(fields), "the two consumed fields are not in the zero set"
        )
        for entry in behavior_envelope.CONSUMED_BEHAVIOURAL_FIELDS:
            self.assertGreater(int(entry["legacy_reads"]), 0)
            self.assertTrue(str(entry["source"]))
        for name in behavior_envelope.COMBAT_FIELDS:
            self.assertIn(name, fields)

    def test_the_committed_flag_inventory_is_recorded(self) -> None:
        flags = {
            entry["flag"]: entry for entry in behavior_envelope.UNIT_PROPERTY_FLAGS
        }
        self.assertEqual(len(flags), 15)
        self.assertEqual(flags["resurrectable"]["positive"], 426)
        self.assertEqual(flags["resurrectable"]["carried"], 426)
        self.assertEqual(flags["ft_flying"]["positive"], 135)
        self.assertEqual(flags["ft_flying"]["carried"], 137)
        for entry in behavior_envelope.UNIT_PROPERTY_FLAGS:
            self.assertGreater(int(entry["positive"]), 0)

    def test_the_committed_flag_positive_counts_are_measured(self) -> None:
        rows = self._loaded_items()
        units = [row for row in rows if row.get("type") == "u"]
        for entry in behavior_envelope.UNIT_PROPERTY_FLAGS:
            name = str(entry["flag"])
            positive = 0
            carried = 0
            for row in units:
                decoded = row.get("properties")
                if isinstance(decoded, (str, bytes)):
                    decoded = json.loads(decoded)
                if not isinstance(decoded, dict) or name not in decoded:
                    continue
                carried += 1
                try:
                    if int(str(decoded[name])) > 0:
                        positive += 1
                except (TypeError, ValueError):
                    continue
            with self.subTest(flag=name):
                self.assertEqual(positive, entry["positive"])
                self.assertEqual(carried, entry.get("carried", positive))

    def test_the_committed_field_distributions_are_measured(self) -> None:
        rows = self._loaded_items()
        units = [row for row in rows if row.get("type") == "u"]
        for entry in behavior_envelope.ZERO_CONSUMER_FIELDS:
            name = str(entry["field"])
            distinct = len({str(row.get(name)) for row in units})
            with self.subTest(field=name):
                if entry["unit_distinct"] is None:
                    continue
                self.assertEqual(distinct, entry["unit_distinct"])


# ------------------------------------------------ the cell and target resolution --
class ResolutionTests(unittest.TestCase):
    """The cell resolution and both gates, before the dispatcher runs."""

    def test_a_cell_resolves_to_the_key_whose_row_records_it(self) -> None:
        items = BOOT.map_items(PID)  # type: ignore[union-attr]
        resolved = behavior_envelope.address_cell(
            items, COMMITTED_CELL[0], COMMITTED_CELL[1]
        )
        self.assertTrue(resolved["ok"])
        self.assertTrue(resolved["resolved"])
        self.assertEqual(resolved["map_key"], int(COMMITTED_KEY))
        self.assertEqual(resolved["occupant_item_id"], COMMITTED_ITEM)
        self.assertEqual(
            items[COMMITTED_KEY][1],
            COMMITTED_CELL[0],
            "the committed row really records that cell",
        )

    def test_an_unrecorded_cell_is_refused(self) -> None:
        resolved = behavior_envelope.address_cell(BOOT.map_items(PID), 0, 0)  # type: ignore[union-attr]
        self.assertFalse(resolved["ok"])
        self.assertEqual(resolved["reason"], "unresolvable_cell")
        self.assertEqual(resolved["map_key"], None)
        self.assertEqual(resolved["map_keys"], [])

    def test_two_rows_on_one_cell_are_refused_not_disambiguated(self) -> None:
        items = {
            "3": [23, 10, 10, 0, 0, [], {}, 1],
            "4": [23, 10, 10, 0, 0, [], {}, 1],
        }
        resolved = behavior_envelope.address_cell(items, 10, 10)
        self.assertFalse(resolved["ok"])
        self.assertTrue(resolved["ambiguous"])
        self.assertEqual(resolved["reason"], "ambiguous_cell")
        self.assertEqual(resolved["map_keys"], ["3", "4"])

    def test_a_row_that_is_not_a_row_stands_at_no_cell(self) -> None:
        for items in (
            {"5": "not a row"},
            {"5": [1, 2]},
            {"5": {"item": 1}},
        ):
            with self.subTest(items=items):
                resolved = behavior_envelope.address_cell(items, 2, 2)
                self.assertFalse(resolved["ok"])
                self.assertEqual(resolved["reason"], "unresolvable_cell")

    def test_the_derived_target_names_both_gates(self) -> None:
        target = behavior_envelope.resolve_target(
            BOOT.map_items(PID),  # type: ignore[union-attr]
            {"1001": 1},
            COMMITTED_CELL[0],
            COMMITTED_CELL[1],
            lambda item_id: {"properties": json.dumps({"resurrectable": "1"})},
        )
        self.assertTrue(target["ok"])
        self.assertEqual(target["item_id"], 1001)
        self.assertEqual(target["count_before"], 1)
        self.assertEqual(target["committed_resurrectable"], 1)
        self.assertEqual(len(target["gates"]), 2)
        self.assertIsNone(target["refusal"])
        self.assertIn("LEDGER CHOOSES WHAT IS", target["resolution_rule"])
        self.assertIn("REJECTED", target["rejected_resolution"])

    def test_an_empty_ledger_resolves_to_no_ledger_entry(self) -> None:
        target = behavior_envelope.resolve_target(
            BOOT.map_items(PID),  # type: ignore[union-attr]
            {},
            COMMITTED_CELL[0],
            COMMITTED_CELL[1],
            lambda item_id: None,
        )
        self.assertFalse(target["ok"])
        self.assertEqual(target["reason"], "unresolvable_ledger_entry")

    def test_an_absent_flag_is_not_resurrectable(self) -> None:
        target = behavior_envelope.resolve_target(
            BOOT.map_items(PID),  # type: ignore[union-attr]
            {"23": 1},
            COMMITTED_CELL[0],
            COMMITTED_CELL[1],
            lambda item_id: {"properties": json.dumps({"ft_building": "1"})},
        )
        self.assertFalse(target["ok"])
        self.assertEqual(target["reason"], "not_resurrectable")
        self.assertIsNone(target["committed_resurrectable"])
        self.assertIn("NO resurrectable flag", target["error"])

    def test_a_zero_flag_is_not_resurrectable(self) -> None:
        target = behavior_envelope.resolve_target(
            BOOT.map_items(PID),  # type: ignore[union-attr]
            {"23": 1},
            COMMITTED_CELL[0],
            COMMITTED_CELL[1],
            lambda item_id: {"properties": json.dumps({"resurrectable": "0"})},
        )
        self.assertFalse(target["ok"])
        self.assertEqual(target["reason"], "not_resurrectable")
        self.assertEqual(target["committed_resurrectable"], 0)
        self.assertIn("not 0", target["error"].replace("greater than zero", "not 0"))

    def test_a_two_entry_ledger_is_refused_rather_than_tie_broken(self) -> None:
        target = behavior_envelope.resolve_target(
            BOOT.map_items(PID),  # type: ignore[union-attr]
            {"1001": 1, "1040": 1},
            COMMITTED_CELL[0],
            COMMITTED_CELL[1],
            lambda item_id: None,
        )
        self.assertFalse(target["ok"])
        self.assertEqual(target["reason"], "ambiguous_ledger")
        self.assertIn("no rule for choosing", target["error"])

    def test_the_resurrectable_flag_is_read_in_every_encoding(self) -> None:
        self.assertEqual(
            behavior_envelope.committed_resurrectable({"resurrectable": "1"}), 1
        )
        self.assertEqual(
            behavior_envelope.committed_resurrectable({"resurrectable": 3}), 3
        )
        self.assertEqual(
            behavior_envelope.committed_resurrectable({"resurrectable": 0}), 0
        )
        self.assertEqual(
            behavior_envelope.committed_resurrectable({"resurrectable": "0"}), 0
        )
        self.assertEqual(
            behavior_envelope.committed_resurrectable({"resurrectable": -2}), -2
        )
        self.assertIsNone(
            behavior_envelope.committed_resurrectable({"resurrectable": True}),
            "a bool is not a committed flag value",
        )
        self.assertIsNone(
            behavior_envelope.committed_resurrectable({"resurrectable": "nope"})
        )
        self.assertIsNone(behavior_envelope.committed_resurrectable({}))
        self.assertIsNone(behavior_envelope.committed_resurrectable(None))
        self.assertIsNone(
            behavior_envelope.committed_resurrectable(""),
            "an EMPTY blob is an absent flag, exactly as push_dead_unit's falsy "
            "properties test sees it",
        )
        with self.assertRaises(behavior_envelope.EnvelopeError):
            behavior_envelope.committed_resurrectable("not json")
        self.assertEqual(
            behavior_envelope.committed_resurrectable(
                json.dumps({"resurrectable": "1"})
            ),
            1,
            "the RAW configuration string is accepted too, which is what the "
            "legacy helper json.loads",
        )
        with self.assertRaises(behavior_envelope.EnvelopeError):
            behavior_envelope.committed_resurrectable("{not json")

    def test_syringes_is_read_from_the_item_row_not_from_properties(self) -> None:
        self.assertEqual(
            behavior_envelope.committed_syringes({"syringes": "3"}), 3
        )
        self.assertEqual(behavior_envelope.committed_syringes({"syringes": 0}), 0)
        self.assertIsNone(behavior_envelope.committed_syringes({}))
        self.assertIsNone(behavior_envelope.committed_syringes(None))
        self.assertIsNone(behavior_envelope.committed_syringes({"syringes": "x"}))
        self.assertIsNone(behavior_envelope.committed_syringes({"syringes": True}))

    def test_the_whole_projection_reports_both_ledgers(self) -> None:
        projection = behavior_envelope.project_resurrection(
            BOOT.map_items(PID),  # type: ignore[union-attr]
            {"1001": 1},
            COMMITTED_CELL[0],
            COMMITTED_CELL[1],
            lambda item_id: {
                "properties": json.dumps({"resurrectable": "1"}),
                "syringes": "1",
            },
        )
        self.assertEqual(projection["count_before"], 1)
        self.assertEqual(projection["count_after"], 0)
        self.assertTrue(projection["removed"])
        self.assertEqual(projection["ledger_after"]["entries"], [])
        self.assertEqual(
            projection["syringe_charged"],
            0,
            "no syringe cost is charged",
        )
        self.assertEqual(projection["resource_delta"], [0] * 8)
        self.assertEqual(
            projection["projection"]["committed_syringes"], 1
        )

    def test_a_refused_projection_derives_no_after_ledger(self) -> None:
        projection = behavior_envelope.project_resurrection(
            BOOT.map_items(PID),  # type: ignore[union-attr]
            {},
            COMMITTED_CELL[0],
            COMMITTED_CELL[1],
            lambda item_id: None,
        )
        self.assertIsNone(projection["ledger_after"])
        self.assertFalse(projection["removed"])


# ------------------------------------------------------------- the endpoint --
class SuccessfulRevivalTests(unittest.TestCase):
    """One revival through the real dispatcher, with its two-part proof."""

    def test_a_successful_revival_applies_the_derived_decrement(self) -> None:
        before = seeded()
        response = resurrect_now(intent())
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["protocol"], "compat-v0")
        self.assertEqual(body["result"], "success")
        self.assertEqual(body["map_key"], int(COMMITTED_KEY))
        self.assertEqual(body["item_id"], RESURRECTABLE_UNIT)
        self.assertEqual(body["count_before"], 2)
        self.assertEqual(body["count_after"], 1)
        self.assertFalse(body["removed"])
        self.assertEqual(body["cell"], list(COMMITTED_CELL))
        self.assertEqual(body["occupant_item_id"], COMMITTED_ITEM)
        self.assertEqual(ledger_now(), {"1001": 1})

    def test_the_second_revival_deletes_the_entry_at_zero(self) -> None:
        seeded()
        self.assertEqual(resurrect_now(intent()).status_code, 200)
        response = resurrect_now(intent())
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["count_before"], 1)
        self.assertEqual(body["count_after"], 0)
        self.assertTrue(body["removed"], "reaching zero DELETES the key")
        self.assertEqual(body["ledger_after"], [])
        self.assertEqual(
            ledger_now(), {}, "the persisted ledger holds no zero-valued key"
        )
        persisted = corpus_save()["privateState"][behavior_envelope.LEDGER_KEY]
        self.assertEqual(persisted, {})

    def test_the_two_part_proof_holds(self) -> None:
        before = seeded()
        response = resurrect_now(intent())
        body = response.get_json()
        # Half one: the ledger moved by exactly the derived decrement and nothing
        # else.  Half two: EVERY stored resource is unchanged.
        self.assertEqual(
            body["ledger_before"], [{"item_id": "1001", "count": 2}]
        )
        self.assertEqual(body["ledger_after"], [{"item_id": "1001", "count": 1}])
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(body["resources"][name], before["resources"][name])
                self.assertIn(name, body["resources"])

    def test_the_proof_compares_the_full_resource_set(self) -> None:
        self.assertEqual(len(RESOURCE_NAMES), 7)
        self.assertEqual(
            tuple(sorted(RESOURCE_NAMES)),
            ("cash", "gold", "mana", "oil", "steel", "wood", "xp"),
        )
        body = resurrect_now(intent()).get_json()
        self.assertEqual(
            sorted(body["resources"].keys()),
            sorted(RESOURCE_NAMES),
            "the response reports every stored resource, never a subset",
        )

    def test_the_revived_row_records_the_derived_id_and_cell(self) -> None:
        seeded()
        body = resurrect_now(intent()).get_json()
        self.assertEqual(body["placement_before"][0], COMMITTED_ITEM)
        self.assertEqual(body["placement_after"][0], RESURRECTABLE_UNIT)
        self.assertEqual(body["placement_after"][1], COMMITTED_CELL[0])
        self.assertEqual(body["placement_after"][2], COMMITTED_CELL[1])
        self.assertEqual(
            body["placement_after"][behavior_envelope.SLOT_PLAYER],
            behavior_envelope.PLAYER_TEAM,
            "the revived row is on player team 1, matching the increment gate",
        )
        self.assertEqual(
            body["placement_after"][6],
            {},
            "a revived UNIT seeds no construction-click counter: the committed "
            "clicks_to_build is 0 on all 429 units",
        )

    def test_the_response_reports_both_gates_and_the_committed_flags(self) -> None:
        seeded()
        body = resurrect_now(intent()).get_json()
        self.assertEqual(
            [gate["gate"] for gate in body["gates"]],
            ["player_team_one", "resurrectable_positive"],
        )
        self.assertEqual(body["committed_resurrectable"], 1)
        self.assertEqual(
            body["committed_syringes"],
            1,
            "the committed syringes field is reported as CONTENT ONLY",
        )

    def test_the_response_records_the_three_refusals(self) -> None:
        seeded()
        body = resurrect_now(intent()).get_json()
        names = [entry["refusal"] for entry in body["refusals"]]
        self.assertEqual(
            names, ["syringe_cost", "combat_resolution", "placement_validation"]
        )
        for entry in body["refusals"]:
            self.assertFalse(entry["implemented"])
            self.assertTrue(str(entry["rule"]))
        self.assertIn("NO THIRD IS INVENTED", body["no_third_gate"])

    def test_the_derived_resolution_is_recorded_on_every_answer(self) -> None:
        seeded()
        body = resurrect_now(intent()).get_json()
        self.assertIn("LEDGER CHOOSES WHAT IS", body["resolution"]["rule"])
        self.assertIn("REJECTED", body["resolution"]["rejected_alternative"])
        self.assertEqual(body["resolution"]["derivation_status"], "derived")
        self.assertIn("DERIVED, NOT ASSERTED", body["resolution"]["pairing"])
        self.assertIn(
            "REFERENCED AND NOT REIMPLEMENTED", body["clicks_to_build"]
        )


class IgnoredValueTests(unittest.TestCase):
    """The client sends intent only, and the discarded syringe is never echoed."""

    def test_every_derived_value_is_ignored(self) -> None:
        before = seeded()
        payload = intent()
        payload.update(
            {
                "map_key": 39,
                "index": 39,
                "item_id": COMMITTED_ITEM,
                "used_syringe": 5,
                "syringe": 5,
                "syringes": 99,
                "count": 99,
                "cost": {"gold": 1000},
                "price": {"gold": 1000},
                "resources_changed": [0, 1, 0, 0, 0, 0, 0, 0],
                "vector": [0, 1, 0, 0, 0, 0, 0, 0],
                "reason": "KILL",
            }
        )
        body = resurrect_now(payload).get_json()
        self.assertEqual(body["map_key"], int(COMMITTED_KEY))
        self.assertEqual(body["item_id"], RESURRECTABLE_UNIT)
        self.assertEqual(body["count_after"], 1)
        self.assertEqual(ledger_now(), {"1001": 1})
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(body["resources"][name], before["resources"][name])

    def test_a_smuggled_resource_vector_moves_nothing(self) -> None:
        before = seeded()
        payload = intent()
        payload["resources_changed"] = [0, 0, 0, 0, 0, 0, 0, 0]
        body = resurrect_now(payload).get_json()
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                self.assertEqual(body["resources"][name], before["resources"][name])

    def test_the_discarded_syringe_is_never_echoed(self) -> None:
        seeded()
        payload = intent()
        payload["used_syringe"] = 7
        body = resurrect_now(payload).get_json()
        self.assertEqual(body["syringe"]["charged"], 0)
        self.assertFalse(body["syringe"]["echoed"])
        self.assertEqual(body["syringe"]["discarded_argument"], 0)
        self.assertNotIn(
            payload["used_syringe"],
            [
                body["syringe"]["charged"],
                body["syringe"]["discarded_argument"],
                body["committed_syringes"],
            ],
            "the client's discarded syringe count appears in no typed answer field",
        )
        self.assertIn("DISCARD", body["syringe"]["note"])
        self.assertIn("NO SYRINGE COST", body["syringe"]["rule"])


class RefusalTests(unittest.TestCase):
    """Every content refusal: a named code, an empty payload, no ledger change."""

    def assertRefused(
        self, payload: Dict[str, Any], code: str, status: int = 409
    ) -> Dict[str, Any]:
        before = snapshot()
        response = resurrect_now(payload)
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
        self.assertEqual(after["ledger"], before["ledger"], "the ledger is unchanged")
        self.assertEqual(after["items"], before["items"], "no row moved")
        self.assertEqual(after["resources"], before["resources"])
        persisted = corpus_save()["privateState"][behavior_envelope.LEDGER_KEY]
        self.assertEqual(persisted, before["ledger"], "the corpus file is unchanged")
        return body

    def test_the_committed_corpus_is_refused_because_its_ledger_is_empty(self) -> None:
        reset_cells()
        set_ledger({})
        body = self.assertRefused(intent(), "unresolvable_ledger_entry")
        self.assertIn("EMPTY", body["error"]["message"])

    def test_a_cell_no_row_records_is_refused(self) -> None:
        set_ledger({"1001": 1})
        body = self.assertRefused({"user_id": PID, "x": 0, "y": 0}, "unresolvable_cell")
        self.assertIn("no placement row records the cell", body["error"]["message"])

    def test_two_rows_on_one_cell_are_refused(self) -> None:
        reset_cells()
        set_ledger({"1001": 1})
        set_cells({COMMITTED_KEY: (10, 10), "3": (10, 10)})
        self.assertRefused({"user_id": PID, "x": 10, "y": 10}, "ambiguous_cell")
        reset_cells()

    def test_a_building_entry_is_refused_as_not_resurrectable(self) -> None:
        reset_cells()
        set_ledger({"%d" % NON_RESURRECTABLE_BUILDING: 1})
        body = self.assertRefused(intent(), "not_resurrectable")
        self.assertIn("resurrectable", body["error"]["message"])

    def test_a_two_entry_ledger_is_refused(self) -> None:
        reset_cells()
        set_ledger(
            {"%d" % RESURRECTABLE_UNIT: 1, "%d" % AMBIGUOUS_LEDGER_UNIT: 1}
        )
        body = self.assertRefused(intent(), "ambiguous_ledger")
        self.assertIn("no rule for choosing", body["error"]["message"])

    def test_an_absent_coordinate_is_a_missing_cell(self) -> None:
        seeded()
        before = snapshot()
        for payload in ({"user_id": PID, "y": 1}, {"user_id": PID, "x": 1}, {"user_id": PID}):
            with self.subTest(payload=payload):
                response = resurrect_now(payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "missing_cell")
        self.assertEqual(snapshot()["items"], before["items"])

    def test_a_non_integer_coordinate_is_an_invalid_cell(self) -> None:
        seeded()
        before = snapshot()
        for x, y in (("1", 1), (1, "1"), (True, 1), (1.5, 1), (1, 1.5), (-1, 1),
                     (1, 100), (None, 1)):
            with self.subTest(cell=(x, y)):
                response = resurrect_now({"user_id": PID, "x": x, "y": y})
                self.assertEqual(response.status_code, 400, response.get_json())
                self.assertEqual(
                    response.get_json()["error"]["code"], "invalid_cell"
                )
        self.assertEqual(snapshot()["items"], before["items"])

    def test_an_unknown_user_is_refused(self) -> None:
        seeded()
        response = resurrect_now(
            {"user_id": "does-not-exist-0000", "x": 1, "y": 1}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "unknown_user_id")

    def test_a_missing_or_non_object_body_is_refused(self) -> None:
        with harness.offline():
            response = CLIENT.post(  # type: ignore[union-attr]
                "/v0/resurrect", data="not json"
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_payload")
        with harness.offline():
            response = CLIENT.post("/v0/resurrect", json={})  # type: ignore[union-attr]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "missing_user_id")

    def test_every_conflict_reason_is_declared(self) -> None:
        self.assertEqual(
            set(behavior_envelope.CONFLICT_REASONS),
            {
                "unresolvable_cell",
                "ambiguous_cell",
                "unresolvable_ledger_entry",
                "ambiguous_ledger",
                "not_resurrectable",
            },
        )


class PostExecutionProofFailureTests(unittest.TestCase):
    """Each proof half fails closed rather than reporting legacy's success."""

    def test_a_ledger_entry_that_is_not_deleted_fails_closed(self) -> None:
        # Seeded at 1 so the derived decrement DELETES the key: leaving it in
        # place is the only way the delete-at-zero half can fail.
        reset_cells()
        set_ledger({"%d" % RESURRECTABLE_UNIT: 1})

        def restore(save: Dict[str, Any]) -> Dict[str, Any]:
            save["privateState"][behavior_envelope.LEDGER_KEY] = {"1001": 1}
            return save

        result = post_with_save_stub(restore, intent())
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.get_json()["error"]["code"], "internal_error")
        self.assertIn("still holds", result.get_json()["error"]["message"])

    def test_a_stale_count_after_the_revival_fails_closed(self) -> None:
        seeded()

        def wrong(save: Dict[str, Any]) -> Dict[str, Any]:
            save["privateState"][behavior_envelope.LEDGER_KEY] = {"1001": 5}
            return save

        result = post_with_save_stub(wrong, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("derived", result.get_json()["error"]["message"])

    def test_a_row_that_does_not_record_the_derived_item_fails_closed(self) -> None:
        seeded()

        def wrong(items: Dict[str, Any]) -> Dict[str, Any]:
            items[str(COMMITTED_KEY)] = list(items[str(COMMITTED_KEY)])
            items[str(COMMITTED_KEY)][0] = COMMITTED_ITEM
            return items

        result = post_with_items_stub(wrong, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("not the derived", result.get_json()["error"]["message"])

    def test_a_row_that_does_not_record_the_addressed_cell_fails_closed(self) -> None:
        seeded()

        def wrong(items: Dict[str, Any]) -> Dict[str, Any]:
            items[str(COMMITTED_KEY)] = list(items[str(COMMITTED_KEY)])
            items[str(COMMITTED_KEY)][1] = 77
            return items

        result = post_with_items_stub(wrong, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("not the addressed", result.get_json()["error"]["message"])

    def test_a_missing_row_after_the_revival_fails_closed(self) -> None:
        seeded()

        def gone(items: Dict[str, Any]) -> Dict[str, Any]:
            items.pop(str(COMMITTED_KEY), None)
            return items

        result = post_with_items_stub(gone, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("holds no committed row", result.get_json()["error"]["message"])

    def test_any_moved_resource_fails_closed(self) -> None:
        for name in RESOURCE_NAMES:
            with self.subTest(resource=name):
                seeded()

                def moved(values: Dict[str, int], key: str = name) -> Dict[str, int]:
                    out = dict(values)
                    out[key] = out[key] + 1
                    return out

                result = post_with_resources_stub(moved, intent())
                self.assertEqual(result.status_code, 500)
                self.assertEqual(
                    result.get_json()["error"]["code"], "internal_error"
                )
                self.assertIn(
                    "no syringe cost is charged", result.get_json()["error"]["message"]
                )

    def test_a_resource_missing_from_one_side_fails_closed(self) -> None:
        seeded()

        def dropped(values: Dict[str, int]) -> Dict[str, int]:
            out = dict(values)
            out.pop("gold")
            return out

        result = post_with_resources_stub(dropped, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("FULL resource set", result.get_json()["error"]["message"])


# --------------------------------------------------------- the verification seam --
class SeedSeamTests(unittest.TestCase):
    """The opt-in disposable-corpus seed, and its named refusals."""

    def test_the_seam_is_absent_by_default(self) -> None:
        previous = os.environ.pop(behavior_envelope.SEED_ENVIRONMENT, None)
        try:
            result = behavior_envelope.seed_ledger_from_environment(
                {"privateState": {}}, None
            )
        finally:
            if previous is not None:
                os.environ[behavior_envelope.SEED_ENVIRONMENT] = previous
        self.assertFalse(result["seeded"])
        self.assertEqual(result["reason"], "not requested")
        self.assertEqual(result["after"], None)

    def test_the_seam_writes_only_when_asked(self) -> None:
        save = {"privateState": {behavior_envelope.LEDGER_KEY: {}}}
        result = behavior_envelope.seed_ledger_from_environment(save, "1001=2")
        self.assertTrue(result["seeded"])
        self.assertEqual(result["before"], {})
        self.assertEqual(result["after"], {"1001": 2})
        self.assertEqual(
            save["privateState"][behavior_envelope.LEDGER_KEY], {"1001": 2}
        )

    def test_a_malformed_seed_is_a_named_refusal_not_a_silent_no_op(self) -> None:
        for value in ("", "bogus", "1001", "1001=0", "1001=x", "=1", "1001=1,"):
            with self.subTest(value=value):
                save = {"privateState": {behavior_envelope.LEDGER_KEY: {}}}
                result = behavior_envelope.seed_ledger_from_environment(save, value)
                self.assertFalse(result["seeded"])
                self.assertEqual(result["reason"], behavior_envelope.SEED_ENVIRONMENT)
                self.assertTrue(result["error"])
                self.assertEqual(
                    save["privateState"][behavior_envelope.LEDGER_KEY], {},
                    "a refused seed leaves the save untouched",
                )

    def test_a_seed_needs_a_private_state(self) -> None:
        for save in ({}, {"privateState": None}, {"privateState": []}):
            with self.subTest(save=save):
                result = behavior_envelope.seed_ledger_from_environment(save, "1001=1")
                self.assertFalse(result["seeded"])
                self.assertEqual(result["reason"], behavior_envelope.SEED_ENVIRONMENT)
                self.assertIn("privateState", result["error"])

    def test_the_parser_returns_none_only_when_absent(self) -> None:
        self.assertIsNone(behavior_envelope.parse_seed(None))
        self.assertEqual(
            behavior_envelope.parse_seed("1001=1,1040=2"),
            {"1001": 1, "1040": 2},
        )
        with self.assertRaises(behavior_envelope.EnvelopeError):
            behavior_envelope.parse_seed("nope")

    def test_the_seed_is_not_part_of_any_committed_artifact(self) -> None:
        self.assertEqual(
            behavior_envelope.SEED_ENVIRONMENT, "COMPAT_SEED_DEAD_HEROES"
        )


# ------------------------------------------------------------ the refusals --
class RecordedRefusalTests(unittest.TestCase):
    """Each refusal family carries a non-empty, specific reason."""

    def test_no_syringe_cost_is_recorded_with_its_reason(self) -> None:
        self.assertIn("NO SYRINGE COST IS CHARGED", behavior_envelope.NO_SYRINGE_COST)
        self.assertIn("args[4]", behavior_envelope.NO_SYRINGE_COST)
        self.assertIn("every stored resource is unchanged", behavior_envelope.NO_SYRINGE_COST)

    def test_no_combat_is_recorded_with_its_reason(self) -> None:
        self.assertIn("NO COMBAT IS RESOLVED", behavior_envelope.NO_COMBAT)
        for field in behavior_envelope.COMBAT_FIELDS:
            self.assertIn(field, behavior_envelope.NO_COMBAT)

    def test_no_placement_validation_is_recorded_with_its_reason(self) -> None:
        self.assertIn(
            "NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION",
            behavior_envelope.NO_PLACEMENT_VALIDATION,
        )
        self.assertIn("M13", behavior_envelope.NO_PLACEMENT_VALIDATION)

    def test_the_derivation_carries_the_rejected_alternative(self) -> None:
        self.assertIn("REJECTED", behavior_envelope.REJECTED_RESOLUTION)
        self.assertIn("slot 0", behavior_envelope.REJECTED_RESOLUTION)

    def test_the_pairing_is_recorded_as_derived(self) -> None:
        self.assertIn(
            "THE DEATH/RESURRECTION PAIRING IS DERIVED",
            behavior_envelope.DERIVED_PAIRING,
        )

    def test_the_no_fixture_reason_names_the_corpus_cause(self) -> None:
        reason = behavior_envelope.FIXTURE_NOT_CAPTURED
        self.assertIn("NO EXECUTED-LEGACY BEHAVIOUR FIXTURE WAS CAPTURED", reason)
        self.assertIn("CORPUS LIMITATION", reason)
        self.assertIn("NOT, as on the three refusal lines", reason)
        self.assertIn("MANUFACTURING A UNIT ROW", reason)
        self.assertIn("godot-unit-instances", reason)


# ----------------------------------------------------------------- the corpus --
def _resurrectable_item_ids(rows: Any) -> set:
    """Every item id whose committed ``properties`` carry a positive flag.

    The raw configuration stores ``properties`` as a JSON **string** and leaves
    it **empty** on some rows, so an empty or absent blob is an absent flag — a
    refusal, never a zero — rather than a decode failure.
    """
    out = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        raw = row.get("properties")
        decoded: Any = raw
        if isinstance(raw, (str, bytes)):
            text = raw.strip()
            if text == "":
                continue
            try:
                decoded = json.loads(text)
            except ValueError:
                continue
        if not isinstance(decoded, dict):
            continue
        flag = decoded.get(behavior_envelope.RESURRECTABLE_FLAG)
        if flag is None:
            continue
        try:
            if int(str(flag)) > 0:
                out.add(int(row.get("id")))
        except (TypeError, ValueError):
            continue
    return out


class CommittedCorpusTests(unittest.TestCase):
    """The committed corpus's own measurement — the absent-fixture cause."""

    def test_the_committed_corpus_places_40_rows_on_40_distinct_cells(self) -> None:
        seed = harness.load_seed()
        items = seed["maps"][0]["items"]
        self.assertEqual(len(items), COMMITTED_PLACEMENTS)
        cells = {(row[1], row[2]) for row in items.values()}
        self.assertEqual(len(cells), COMMITTED_DISTINCT_CELLS)

    def test_the_committed_ledger_is_present_and_empty(self) -> None:
        seed = harness.load_seed()
        self.assertIn(behavior_envelope.LEDGER_KEY, seed["privateState"])
        self.assertEqual(seed["privateState"][behavior_envelope.LEDGER_KEY], {})

    def test_no_committed_placed_row_is_resurrectable(self) -> None:
        seed = harness.load_seed()
        items = seed["maps"][0]["items"]
        rows = BOOT.config()["items"]  # type: ignore[union-attr]
        resurrectable = _resurrectable_item_ids(rows)
        placed = {int(row[0]) for row in items.values()}
        self.assertEqual(len(resurrectable), 426)
        self.assertEqual(
            placed & resurrectable,
            set(),
            "0 of the 40 committed placed rows are resurrectable",
        )

    def test_the_committed_corpus_places_no_unit_row(self) -> None:
        seed = harness.load_seed()
        items = seed["maps"][0]["items"]
        rows = BOOT.config()["items"]  # type: ignore[union-attr]
        types = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                types[int(row.get("id"))] = row.get("type")
            except (TypeError, ValueError):
                continue
        unit_rows = [
            int(row[0]) for row in items.values() if types.get(int(row[0])) == "u"
        ]
        self.assertEqual(
            unit_rows, [], "the committed corpus places NO unit row at all"
        )

    def test_the_committed_corpus_is_never_written(self) -> None:
        seed_path = harness.SEED_SAVE
        before = seed_path.read_bytes()
        seeded()
        self.assertEqual(
            resurrect_now(intent()).status_code, 200
        )
        self.assertEqual(
            seed_path.read_bytes(),
            before,
            "the committed corpus save is byte-identical after a revival",
        )


if __name__ == "__main__":
    unittest.main()