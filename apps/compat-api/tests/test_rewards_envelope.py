#!/usr/bin/env python3
"""Offline unit tests for ``rewards_envelope`` (OpenSpec tasks 2.1-2.7, 5.1-5.4).

No server, no socket, no network: this module imports the derivation and asserts
it against **the committed bytes themselves** -- all **eleven** top-level legacy
modules, the committed ``globals`` package, and every committed save document --
so every recorded constant is a **measurement** rather than a restatement of the
delivered module's own prose.

Covered:

* the **re-measured** eleven-module schedule census, the type-letter decoder
  searches with their **positive controls**, the letter-named declarations, the
  save-only field census, and the two cursor distributions -- each re-derived from
  the committed bytes on **every run**, with the **subject count printed before any
  absence verdict is believed** (task 3.3's vacuous-census guard);
* the closed two-action vocabulary, the derived inverse command map, the
  **explicit** empty addressing-key table and the function that raises rather than
  defaulting (D13), and the derived argument counts;
* the pinned refusal order, the seven grant-shaped classes, and each refusal's
  **reachability** through the typed entry point -- including why every one of them
  is reachable here when five of the quests line's were not (task 3.5's shape);
* both cursors and both instants read with the two recorded-state refusals kept
  apart, the derived weekly bound **re-derived from the committed schedule**, the
  literal daily bound beside its rejected derivation, and both successors
  transcribed from the preserved branches;
* the reachability report as a **set difference in both directions** with
  ``selection_performed`` false, and the whole-document leaf allowlist that
  carries the four-part grant proof (D6) with **container paths** so a created
  key is a difference (D9);
* the neutral resource vector, the derived batch envelope, and the typed
  :class:`RewardResult` payload -- with a guard that **no field is named after a
  granted, paid, or awarded reward**;
* the whole static-function inventory, **by-name and substring** anti-invention
  guards (D7, task 3.4), the absence of every helper :data:`ABSENT_HELPERS` names,
  and the arithmetic/call surface the module is allowed to have;
* the two ownership boundaries asserted **mechanically** rather than in prose
  (tasks 5.3 and 5.4): no delivered identifier is named after ``boughtUnits``,
  ``store``, or ``maps[0].items``, none is named after a schedule type letter,
  and each owning capability exists in ``openspec/specs/`` so the boundary is a
  hand-off and not an orphan.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import unittest
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness  # noqa: F401  (path setup)

import placement_envelope as P
import rewards_envelope as R

REPO = harness.REPO_ROOT
GLOBALS_PACKAGE = REPO / "packages" / "game-content" / "normalized" / "globals.json"
RANKING_PACKAGE = (
    REPO / "packages" / "game-content" / "normalized" / "level_ranking_reward.json"
)
SAVE_ROOTS = ("villages", "tests/saves")

#: The **eleven** top-level legacy modules the census is measured over.  Read
#: from the contract rather than restated, and then *verified against it* -- the
#: two must be the same eleven names, and the suite fails if either drifts.
LEGACY_MODULES = R.SCHEDULE_CENSUS_MODULES


# --------------------------------------------------------------- the sources --
def module_source() -> str:
    return pathlib.Path(R.__file__).read_text(encoding="utf-8")


def module_functions() -> List[str]:
    """Every module-scope function the delivered derivation declares.

    The **whole** inventory, not a filtered view: this is the anti-invention gate,
    so an added helper shows up here whatever it is called.
    """
    return sorted(
        node.name
        for node in ast.parse(module_source()).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def module_code_identifiers() -> List[str]:
    """Every identifier the module's CODE declares, binds, or reads.

    Docstrings, comments, and string literals are excluded by **parsing** rather
    than by scanning, so a recorded refusal sentence that happens to use the word
    "grant" can never be mistaken for a computation.
    """
    names: List[str] = []
    for node in ast.walk(ast.parse(module_source())):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            names.append(node.arg)
    return sorted(set(names))


def module_tree() -> ast.Module:
    """The module's AST, parsed **once**.

    A docstring's node identity is only stable within one parse, so every
    consumer of "the literals this module uses" must share this tree; parsing per
    caller silently compares ``id()`` values from two different objects, which
    this suite already recorded as a defect class in the other direction.
    """
    global _TREE
    if _TREE is None:
        _TREE = ast.parse(module_source())
    return _TREE


_TREE: Optional[ast.Module] = None


def module_docstring_nodes() -> set:
    """The string nodes that are docstrings -- prose, not values.

    The module-level docstring is a **single** multi-line ``ast.Constant``, so a
    scan over every string literal treats this line's own recorded refusal
    sentences -- which necessarily name the letters they refuse -- as if they were
    expressions pairing a letter with a value.  Excluding them is the narrowest
    fix that leaves the scan over real literals untouched.
    """
    tree = module_tree()
    holders: List[ast.AST] = [tree]
    holders.extend(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    found: set = set()
    for holder in holders:
        body = getattr(holder, "body", None)
        if not body:
            continue
        first = body[0]
        if not isinstance(first, ast.Expr):
            continue
        value = first.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            found.add(id(value))
    return found


def module_code_literals() -> List[str]:
    """Every string literal the module's code uses, docstrings excluded."""
    docstrings = module_docstring_nodes()
    return [
        node.value for node in ast.walk(module_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def _letter_pairing_nodes(tree: ast.AST) -> List[str]:
    """Every place a type letter is **used** as a key or a comparison operand.

    Three forms, and only three, are the ones that could decode a letter:

    * a ``Dict`` key,
    * a ``Subscript`` slice,
    * either operand of a ``Compare``.

    A string constant in any other position -- an argument, a format field, a
    note, a regex -- is a *report* of the vocabulary, never a decoding of it, so
    the scan stops here rather than growing an exemption list.
    """
    letters = set(R.TYPE_LETTERS)
    found: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if (isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                        and key.value in letters):
                    found.append("dict key %r" % key.value)
        elif isinstance(node, ast.Subscript):
            index = node.slice
            if (isinstance(index, ast.Constant)
                    and isinstance(index.value, str)
                    and index.value in letters):
                found.append("subscript %r" % index.value)
        elif isinstance(node, ast.Compare):
            operands = [node.left] + list(node.comparators)
            for operand in operands:
                if (isinstance(operand, ast.Constant)
                        and isinstance(operand.value, str)
                        and operand.value in letters):
                    found.append("compare operand %r" % operand.value)
    return found


def module_bound_identifiers() -> List[str]:
    """Every identifier the module **binds** -- the names it introduces.

    Deliberately narrower than :func:`module_code_identifiers`, which also returns
    *read* names such as ``dict.items``.  A guard about what this line is
    responsible for introducing has to be scoped to what it introduces; including
    builtins would make the guard unsatisfiable for a reason that has nothing to
    do with the line's own boundary.
    """
    names: List[str] = []
    for node in ast.walk(module_tree()):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.append(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            names.append(node.arg)
    return sorted(set(names))


def legacy_text(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


def legacy_lines(name: str) -> List[str]:
    return legacy_text(name).split("\n")


def _corpus_texts() -> Dict[str, str]:
    return {name: legacy_text(name) for name in LEGACY_MODULES}


def pattern_hits(pattern: str) -> Tuple[int, int]:
    """``(occurrences, distinct lines)`` of one regex over the whole corpus.

    Both numbers are returned because this project has twice caught a recorded
    figure that was one of the two taken for the other, so the pair is measured
    together and reported separately.
    """
    compiled = re.compile(pattern)
    occurrences = 0
    lines_hit = 0
    for text in _corpus_texts().values():
        occurrences += len(compiled.findall(text))
        lines_hit += sum(1 for line in text.split("\n") if compiled.search(line))
    return occurrences, lines_hit


def name_occurrences(name: str) -> Dict[str, int]:
    """Whole-file occurrence counts of one literal name, per module."""
    return {
        module: text.count(name)
        for module, text in _corpus_texts().items()
        if name in text
    }


def committed_globals() -> Dict[str, Any]:
    """The committed ``globals`` package as ``key -> value``."""
    rows = json.loads(GLOBALS_PACKAGE.read_text(encoding="utf-8"))
    return {str(row["key"]): row.get("value") for row in rows}


def committed_save_documents() -> List[Tuple[str, Dict[str, Any]]]:
    """Every committed save document that carries a ``privateState`` object.

    ``tests/saves`` and ``villages`` are the two roots the corpus lives in; the
    third location is ``villages/quest/``, which is a subdirectory of the second
    and is therefore counted separately rather than missed.
    """
    documents: List[Tuple[str, Dict[str, Any]]] = []
    candidates: List[Tuple[str, pathlib.Path]] = []
    for root in SAVE_ROOTS:
        directory = REPO / root
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            candidates.append(("%s/%s" % (root, path.name), path))
    quest = REPO / "villages" / "quest"
    if quest.is_dir():
        for path in sorted(quest.glob("*.json")):
            candidates.append(("villages/quest/%s" % path.name, path))
    for relative, path in candidates:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(document, dict) and isinstance(document.get("privateState"), dict):
            documents.append((relative, document))
    return documents


def seeded_save() -> Dict[str, Any]:
    """The committed fresh-player corpus, read fresh so no test can mutate it."""
    return json.loads(harness.SEED_SAVE.read_text(encoding="utf-8"))


def crafted_save(cursor_value: Any = 0, stamp_value: Any = 0,
                 cursor_key: Optional[str] = None,
                 stamp_key: Optional[str] = None,
                 with_private_state: bool = True) -> Dict[str, Any]:
    """A minimal save carrying one cursor and one instant, for refusal paths."""
    private: Dict[str, Any] = {}
    if cursor_value is not _ABSENT:
        private[cursor_key or R.WEEKLY_CURSOR_KEY] = cursor_value
    if stamp_value is not _ABSENT:
        private[stamp_key or R.WEEKLY_STAMP_KEY] = stamp_value
    if not with_private_state:
        return {"maps": [{"items": {}}]}
    return {"privateState": private}


class _Absent:
    """Sentinel so ``None`` stays a real value a cursor could hold."""


_ABSENT = _Absent()


def weekly_schedule() -> Any:
    return committed_globals()[R.WEEKLY_SCHEDULE_KEY]


def daily_schedule() -> Any:
    return committed_globals()[R.DAILY_SCHEDULE_KEY]


# =========================================================== the census itself --
class ScheduleCensusTests(unittest.TestCase):
    """Task 3.3: the consumer census is **re-measured**, and its subjects named
    before any absence verdict is believed."""

    def test_the_census_names_its_subject_count_before_any_absence_verdict(self) -> None:
        """The vacuous-census guard (task 3.3), in the order the task states.

        A census that finds nothing because it read nothing has failed in this
        project three times.  The subject count is therefore printed **first**,
        and the absence verdict is only accepted once the corpus has been shown
        to be non-empty -- an assertion about the eleven modules' sizes rather
        than about the schedules.
        """
        texts = _corpus_texts()
        measured = [
            (module, len(texts[module]), len(texts[module].split("\n")))
            for module in LEGACY_MODULES
        ]
        total_characters = sum(size for _module, size, _lines in measured)
        total_lines = sum(count for _module, _size, count in measured)
        print(
            "[test] reward census subjects: %d modules, %d characters, %d lines"
            % (len(measured), total_characters, total_lines)
        )
        for module, size, count in measured:
            with self.subTest(module=module):
                self.assertGreater(size, 0, "empty census subject")
                self.assertGreater(count, 1, "census subject has no lines")
        # And the eleven names the contract claims are the eleven it will read.
        self.assertEqual(len(measured), 11)
        self.assertEqual(tuple(measured[i][0] for i in range(11)), LEGACY_MODULES)
        for name in LEGACY_MODULES:
            with self.subTest(module=name):
                self.assertTrue((REPO / name).is_file(), name)

    def test_every_recorded_schedule_consumer_count_is_re_measured(self) -> None:
        self.assertEqual(len(R.SCHEDULES), 11)
        for row in R.SCHEDULES:
            name = str(row["name"])
            with self.subTest(schedule=name):
                per_module = name_occurrences(name)
                total = sum(per_module.values())
                self.assertEqual(total, int(row["consumers"]))
                if int(row["consumers"]) == 0:
                    self.assertEqual(per_module, {})
                    self.assertIsNone(row["consumed_for"])
                else:
                    self.assertNotEqual(per_module, {})
                    self.assertIsNotNone(row["consumed_for"])

    def test_exactly_one_schedule_has_a_consumer_and_it_is_read_for_length_only(self) -> None:
        with_consumers = [
            str(row["name"])
            for row in R.SCHEDULES
            if int(row["consumers"]) > 0
        ]
        self.assertEqual(with_consumers, ["MONDAY_BONUS_REWARDS"])
        self.assertEqual(R.SCHEDULES_WITH_NO_CONSUMER_COUNT, 10)
        self.assertNotIn("MONDAY_BONUS_REWARDS", R.SCHEDULES_WITH_NO_CONSUMER)
        # The single occurrence is the length read, located by line.
        occurrences = name_occurrences("MONDAY_BONUS_REWARDS")
        self.assertEqual(occurrences, {"get_game_config.py": 1})
        line_number, line = next(
            (number, text)
            for number, text in enumerate(legacy_lines("get_game_config.py"), 1)
            if "MONDAY_BONUS_REWARDS" in text
        )
        self.assertEqual(line_number, 197)
        self.assertIn("get_weekly_reward_length", " ".join(legacy_lines("get_game_config.py")))
        self.assertIn("length only", str(R.SCHEDULES[3]["consumed_for"]))

    def test_the_census_module_list_is_the_whole_top_level_corpus(self) -> None:
        """The census is over *all* top-level legacy modules, not a chosen subset."""
        top_level = sorted(
            path.name
            for path in REPO.glob("*.py")
            if path.is_file() and not path.name.startswith("__")
        )
        self.assertEqual(sorted(LEGACY_MODULES), top_level)

    def test_the_census_note_states_what_it_does_not_claim(self) -> None:
        note = R.SCHEDULE_CENSUS_NOTE
        self.assertIn("preserved server", note)
        self.assertIn("served", note)
        self.assertIn("NO claim", note)
        for name in LEGACY_MODULES:
            with self.subTest(module=name):
                self.assertIn(name, note)

    def test_the_ranking_table_is_re_measured_and_is_owned_as_content_only(self) -> None:
        """Task 5.2: the table is real, has no consumer, and is owned elsewhere."""
        self.assertEqual(R.RANKING_REWARD_TABLE, "level_ranking_reward")
        self.assertEqual(R.RANKING_REWARD_CONSUMERS, 0)
        self.assertEqual(name_occurrences("level_ranking_reward"), {})
        entries = json.loads(RANKING_PACKAGE.read_text(encoding="utf-8"))
        self.assertIsInstance(entries, list)
        self.assertEqual(len(entries), R.RANKING_REWARD_ENTRY_COUNT)
        ownership = R.RANKING_REWARD_OWNERSHIP
        self.assertIn("economy-schedules-normalization", ownership)
        self.assertIn("content-validation", ownership)
        self.assertIn("delivers NO gameplay", ownership)
        for capability in ("economy-schedules-normalization", "content-validation"):
            with self.subTest(capability=capability):
                self.assertTrue((REPO / "openspec" / "specs" / capability).is_dir())


# ============================================== the decoder searches, measured --
class TypeLetterRefusalTests(unittest.TestCase):
    """D10: the letters are reported UNDECODED, and the refusal is measured."""

    def test_every_decoder_search_is_re_measured_and_still_finds_nothing(self) -> None:
        self.assertEqual(len(R.DECODER_SEARCHES), 6)
        total = 0
        for row in R.DECODER_SEARCHES:
            with self.subTest(search=str(row["search"])):
                occurrences, _lines = pattern_hits(str(row["pattern"]))
                self.assertEqual(occurrences, int(row["hits"]))
                total += occurrences
        self.assertEqual(total, R.DECODER_SEARCH_HIT_TOTAL)
        self.assertEqual(total, 0)

    def test_the_positive_controls_prove_the_patterns_can_fire(self) -> None:
        """A zero from a pattern that never matches is not a measurement.

        Three controls, each carrying **its own** regex, each re-derived here.
        One of them exists because of a measured correction in this project: a
        control was labelled "a subscript by a string key" while counting an
        **unquoted** list index, so both the label and the figure were wrong.  The
        corrected figure is 515 occurrences over 409 lines, and the mislabelled
        measurement is retained as its own third control rather than deleted.
        """
        self.assertEqual(len(R.DECODER_POSITIVE_CONTROLS), 3)
        measured: List[int] = []
        for row in R.DECODER_POSITIVE_CONTROLS:
            with self.subTest(search=str(row["search"])):
                occurrences, _lines = pattern_hits(str(row["pattern"]))
                self.assertEqual(occurrences, int(row["hits"]))
                measured.append(occurrences)
        self.assertEqual(measured, [4, 515, 244])
        # Every control must fire, and each must fire far more often than any of
        # the six single-letter patterns -- which find nothing at all.
        self.assertTrue(all(occurrences > 0 for occurrences in measured))
        self.assertGreater(min(measured), R.DECODER_SEARCH_HIT_TOTAL)

    def test_the_recorded_correction_survives_as_its_own_row(self) -> None:
        rows = {str(row["search"]): int(row["hits"]) for row in R.DECODER_POSITIVE_CONTROLS}
        self.assertIn("a subscript by a string key", rows)
        self.assertEqual(rows["a subscript by a string key"], 515)
        # The mislabelled search is named for what it actually was.
        self.assertIn(
            "an unquoted subscript, a list index rather than a string key", rows
        )
        source = module_source()
        self.assertIn("MEASURED CORRECTION", source)
        self.assertIn("234", source)
        self.assertIn("515", source)
        self.assertIn("409", source)

    def test_no_single_letter_dictionary_key_exists_in_any_module(self) -> None:
        occurrences, lines = pattern_hits(r"[\"'][a-zA-Z][\"']\s*:")
        self.assertEqual((occurrences, lines), (0, 0))
        # The two-letter control is the nearest thing that does exist, and it is
        # four -- so "no single-letter key" is a property of the corpus and not a
        # broken pattern.
        self.assertEqual(pattern_hits(r"[\"'][a-zA-Z]{2}[\"']\s*:"), (4, 4))

    def test_the_three_letters_are_each_declared_once_under_a_resource_name(self) -> None:
        self.assertEqual(R.TYPE_LETTERS, ("g", "u", "c"))
        self.assertEqual(len(R.LETTER_NAMED_DECLARATIONS), 3)
        for row in R.LETTER_NAMED_DECLARATIONS:
            declared_as = str(row["declared_as"])
            with self.subTest(declaration=declared_as):
                per_module = name_occurrences(declared_as)
                self.assertEqual(sum(per_module.values()), int(row["occurrences_total"]))
                self.assertEqual(len(per_module), 1, "declared in more than one module")
                (module, count), = per_module.items()
                self.assertEqual(count, 1, "the declaration is not the only occurrence")
                self.assertEqual(module, "constants.py")
                self.assertEqual(int(row["consumers"]), 0)
                # The recorded declaration line, located rather than trusted.
                line_number, line = next(
                    (number, text)
                    for number, text in enumerate(legacy_lines(module), 1)
                    if declared_as in text
                )
                self.assertEqual(line_number, int(str(row["declared_at"]).split(":")[1]))
                self.assertIn('= "%s"' % row["letter"], line)
        # The two costs declarations are one line apart and the unit type is not.
        lines = legacy_lines("constants.py")
        self.assertEqual(int(str(R.LETTER_NAMED_DECLARATIONS[0]["declared_at"]).split(":")[1]) + 1,
                         int(str(R.LETTER_NAMED_DECLARATIONS[1]["declared_at"]).split(":")[1]))

    def test_no_legacy_module_iterates_the_costs_vocabulary(self) -> None:
        """The measured nuance: nothing bridges costs to the reward type field."""
        bridges = 0
        for text in _corpus_texts().values():
            for line in text.split("\n"):
                if re.search(r"for\s+\w+\s+in\s+.*\bcosts\b", line):
                    bridges += 1
        self.assertEqual(bridges, 0)
        self.assertIn("no legacy module iterates costs", R.TYPE_LETTERS_UNDECODED_NOTE.lower())

    def test_the_undecoded_note_names_the_letters_and_claims_no_decoding(self) -> None:
        note = R.TYPE_LETTERS_UNDECODED_NOTE
        self.assertIn("NOT DECODED", note)
        for declared_as in (
            str(row["declared_as"]) for row in R.LETTER_NAMED_DECLARATIONS
        ):
            with self.subTest(declaration=declared_as):
                self.assertIn(declared_as, note)
        self.assertIn("an INVENTION", note)


# ================================================= the save-only field census --
class SaveOnlyFieldTests(unittest.TestCase):
    """D11: seven fields present in every committed save and in no source line."""

    def test_the_document_count_is_re_measured_before_the_field_count(self) -> None:
        documents = committed_save_documents()
        print(
            "[test] save-only census subjects: %d committed save documents"
            % len(documents)
        )
        self.assertEqual(len(documents), R.SAVE_ONLY_DOCUMENT_COUNT)
        self.assertEqual(len(R.SAVE_ONLY_FIELDS), 7)
        self.assertEqual(len(set(R.SAVE_ONLY_FIELDS)), 7)

    def test_the_seven_fields_are_in_every_committed_save_document(self) -> None:
        missing: List[str] = []
        for relative, document in committed_save_documents():
            private = document["privateState"]
            for field in R.SAVE_ONLY_FIELDS:
                if field not in private:
                    missing.append("%s/%s" % (relative, field))
        self.assertEqual(missing, [])

    def test_no_save_only_field_is_read_by_any_legacy_module(self) -> None:
        """Whole-**token** absence for all seven, which is the actual claim.

        One of the seven has a whole-file substring occurrence -- ``betWin``
        inside ``betWinner`` at ``auctions.py:176`` -- and that is recorded as an
        artifact rather than dropped, so the naive whole-file count is not the
        claim being made here.  The claim is that no module **reads** the field,
        which is what the whole-token form measures.
        """
        for field in R.SAVE_ONLY_FIELDS:
            with self.subTest(field=field):
                occurrences, lines = pattern_hits(r"\b%s\b" % field)
                self.assertEqual((occurrences, lines), (0, 0),
                                 "%s is read by a legacy module" % field)
        # Exactly one field has a substring occurrence, and it is on the record.
        with_occurrence = [f for f in R.SAVE_ONLY_FIELDS if name_occurrences(f)]
        self.assertEqual(with_occurrence, ["betWin"])
        self.assertEqual(R.SAVE_ONLY_DOCUMENT_COUNT, 33)

    def test_the_one_substring_artifact_is_recorded_rather_than_dropped(self) -> None:
        """"``betWin`` matches inside the longer identifier ``betWinner``."""
        self.assertIn("betWin", R.SAVE_ONLY_FIELDS)
        per_module = name_occurrences("betWin")
        self.assertEqual(per_module, {"auctions.py": 1})
        line_number, line = next(
            (number, text)
            for number, text in enumerate(legacy_lines("auctions.py"), 1)
            if "betWin" in text
        )
        self.assertEqual(line_number, 176)
        # The occurrence is a substring of a different identifier, not a read of
        # this field: the whole-token form finds nothing anywhere.
        self.assertEqual(pattern_hits(r"\bbetWin\b"), (0, 0))
        self.assertIn("betWinner", line)
        self.assertIn("SUBSTRING artifact", R.SAVE_ONLY_NOTE)

    def test_the_origin_is_labelled_an_inference_not_a_measurement(self) -> None:
        self.assertEqual(R.SAVE_ONLY_ORIGIN_STATUS, "inference, not a measurement")
        self.assertIn("ORIGIN IS LABELLED AN INFERENCE", R.SAVE_ONLY_NOTE)
        self.assertIn("no rule", R.SAVE_ONLY_NOTE.lower())


class CursorDistributionTests(unittest.TestCase):
    """The recorded distributions are what make the weekly mismatch reachable."""

    def _distribution(self, key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for _relative, document in committed_save_documents():
            value = str(document["privateState"].get(key))
            counts[value] = counts.get(value, 0) + 1
        return dict(sorted(counts.items()))

    def test_both_distributions_are_re_measured_over_the_committed_documents(self) -> None:
        self.assertEqual(len(R.CURSOR_DISTRIBUTIONS), 2)
        for row in R.CURSOR_DISTRIBUTIONS:
            key = str(row["cursor"])
            with self.subTest(cursor=key):
                measured = self._distribution(key)
                self.assertEqual(measured, dict(row["distribution"]))
                self.assertEqual(
                    sum(measured.values()), int(row["documents"]),
                    "the distribution does not account for every document",
                )
                advanced = sum(
                    count for value, count in measured.items() if value != "0"
                )
                self.assertEqual(advanced, int(row["advanced_documents"]))

    def test_the_weekly_distribution_reaches_unaddressable_positions(self) -> None:
        """Seven documents carry a non-zero weekly cursor, so the mismatch is
        reachable from committed state rather than hypothetical.

        The corrected figure, measured rather than asserted: the seven land on
        exactly ``{2, 3, 4}``, and **two** of those (3 and 4) name no schedule
        entry.  The delivered note once said ``1..4`` and "three of which"; both
        were wrong -- ``1..4`` is what all thirty-three documents reach
        collectively, the twenty-six at cursor 0 being the only ones that land on
        1 -- and the correction is recorded in the module rather than made
        silently.
        """
        rows = {str(row["cursor"]): row for row in R.CURSOR_DISTRIBUTIONS}
        weekly = rows[R.WEEKLY_CURSOR_KEY]
        self.assertEqual(weekly["advanced_documents"], 7)
        bound = R.weekly_bound(weekly_schedule())
        cardinality = R.schedule_cardinality(weekly_schedule())
        advanced_values = [
            int(value) for value in weekly["distribution"] if value != "0"
        ]
        # The advanced *cursors*, not the document counts: every recorded value
        # must actually land somewhere the branch would write.
        landed = sorted({R.weekly_successor(value, bound) for value in advanced_values})
        self.assertEqual(landed, [2, 3, 4])
        unaddressable = sorted(set(landed) - set(range(cardinality)))
        self.assertEqual(unaddressable, [3, 4])
        self.assertEqual(len(unaddressable), 2)
        # The recorded note now says exactly that, and the stale figures are gone.
        note = str(weekly["note"])
        self.assertIn("MEASURED CORRECTION", note)
        self.assertIn("TWO", note)
        # The superseded figures survive only inside the correction's own quote,
        # so they are visible as what they were rather than deleted.
        self.assertIn("1..4", note)
        self.assertIn("not three", note)
        # And the collective set over all thirty-three is 1..4, as recorded.
        all_landed = sorted(
            {R.weekly_successor(int(value), bound) for value in weekly["distribution"]}
        )
        self.assertEqual(all_landed, [1, 2, 3, 4])

    def test_a_committed_document_really_does_record_the_landing_on_four(self) -> None:
        """``villages/Neutral.json`` at 3 and ``villages/Nerri.json`` at 2."""

        by_name = dict(committed_save_documents())
        for name, recorded in (("villages/Neutral.json", 3), ("villages/Nerri.json", 2)):
            with self.subTest(document=name):
                private = by_name[name]["privateState"]
                self.assertEqual(private[R.WEEKLY_CURSOR_KEY], recorded)
                successor = R.weekly_successor(recorded, R.weekly_bound(weekly_schedule()))
                self.assertEqual(successor, recorded + 1)
                self.assertGreaterEqual(
                    successor, R.schedule_cardinality(weekly_schedule())
                )


# ========================================================= the action surface --
class ActionVocabularyTests(unittest.TestCase):
    """D13: a closed two-action vocabulary with no addressing key at all."""

    def test_the_action_set_is_closed_and_exactly_two_actions(self) -> None:
        self.assertEqual(R.ACTIONS, ("weekly", "daily"))
        self.assertEqual(len(R.ACTIONS), 2)
        self.assertTrue(R.is_action("weekly"))
        self.assertTrue(R.is_action("daily"))
        for outside in ("", "WEEKLY", "weekly ", "grant", "reward", None, 1, True,
                        ["weekly"], {"action": "weekly"}):
            with self.subTest(action=outside):
                self.assertFalse(R.is_action(outside))

    def test_each_action_names_its_preserved_command(self) -> None:
        self.assertEqual(R.ACTION_COMMAND, {"weekly": "weekly_reward",
                                            "daily": "win_daily_bonus"})
        self.assertEqual(R.command_for_action("weekly"), "weekly_reward")
        self.assertEqual(R.command_for_action("daily"), "win_daily_bonus")
        for outside in ("", "unknown", None, 3):
            with self.subTest(action=outside):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.command_for_action(outside)  # type: ignore[arg-type]
                self.assertEqual(caught.exception.code, R.REASON_UNKNOWN_ACTION)

    def test_the_inverse_command_map_is_derived_and_injective(self) -> None:
        self.assertEqual(R.ACTION_FOR_COMMAND,
                         {"weekly_reward": "weekly", "win_daily_bonus": "daily"})
        self.assertEqual(len(R.ACTION_FOR_COMMAND), len(R.ACTION_COMMAND))
        for action, command in R.ACTION_COMMAND.items():
            with self.subTest(action=action):
                self.assertEqual(R.ACTION_FOR_COMMAND[command], action)
        # And the round trip through the public helpers, so the inverse cannot
        # disagree with either table.
        for action in R.ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(
                    R.command_for_action(R.ACTION_FOR_COMMAND[R.command_for_action(action)]),
                    R.command_for_action(action),
                )

    def test_each_action_addresses_exactly_one_cursor_and_one_instant(self) -> None:
        self.assertEqual(R.ACTION_CURSOR_KEY,
                         {"weekly": "weeklyRewardIndex", "daily": "bonusNextId"})
        self.assertEqual(R.ACTION_STAMP_KEY,
                         {"weekly": "timeStampMondayBonus", "daily": "timestampLastBonus"})
        self.assertEqual(R.CURSOR_STAMP,
                         {"weeklyRewardIndex": "timeStampMondayBonus",
                          "bonusNextId": "timestampLastBonus"})
        self.assertEqual(R.CURSORS, ("weeklyRewardIndex", "bonusNextId"))
        self.assertEqual(R.INSTANTS, ("timeStampMondayBonus", "timestampLastBonus"))
        # The two cursors are disjoint and cover the whole cursor table, so a
        # third cursor could not be added without breaking this suite.
        self.assertEqual(
            sorted(R.ACTION_CURSOR_KEY.values()), sorted(R.CURSOR_STAMP)
        )
        self.assertEqual(
            sorted(R.ACTION_STAMP_KEY.values()), sorted(R.CURSOR_STAMP.values())
        )

    def test_the_addressing_key_table_is_explicitly_empty_and_looking_one_up_raises(
        self,
    ) -> None:
        """The quests line's largest cross-layer defect was an addressing key
        treated as universal.  Here the absence is *stated*, not defaulted."""
        self.assertEqual(R.ACTION_ADDRESSING_KEY, {})
        self.assertIsInstance(R.ACTION_ADDRESSING_KEY, dict)
        for action in R.ACTIONS + ("unknown", "", None):
            with self.subTest(action=action):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.addressing_key_for(action)  # type: ignore[arg-type]
                self.assertEqual(caught.exception.code, R.REASON_BAD_REQUEST)
        self.assertIn("EXPLICIT", R.ADDRESSING_KEY_NOTE)
        self.assertIn("addressing key", R.ADDRESSING_KEY_NOTE)

    def test_the_argument_counts_are_recorded_and_match_the_derived_arguments(self) -> None:
        self.assertEqual(R.ACTION_ARGUMENT_COUNT, {"weekly": 0, "daily": 2})
        self.assertEqual(R.derived_args_for("weekly", 0), [])
        self.assertEqual(R.derived_args_for("daily", 3), [0, 3])
        for action in R.ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(
                    len(R.derived_args_for(action, 2)),
                    R.ACTION_ARGUMENT_COUNT[action],
                )

    def test_the_weekly_empty_argument_list_is_what_selects_the_non_granting_arm(self) -> None:
        """``command.py:346`` chooses the arm on ``len(args) > 4``."""
        long_arm = next(row for row in R.WEEKLY_ARMS if row["arm"] == "long")
        short_arm = next(row for row in R.WEEKLY_ARMS if row["arm"] == "short")
        self.assertEqual(long_arm["test"], "len(args) > 4")
        self.assertEqual(short_arm["test"], "len(args) <= 4")
        self.assertEqual(len(R.derived_args_for("weekly", 0)), 0)
        self.assertLessEqual(len(R.derived_args_for("weekly", 0)), 4)

    def test_the_daily_grant_argument_is_derived_at_zero_so_no_arm_is_taken(self) -> None:
        granting = next(row for row in R.DAILY_ARMS if row["arm"] == "granting")
        resources = next(row for row in R.DAILY_ARMS if row["arm"] == "resources")
        self.assertEqual(granting["test"], "item > 0")
        self.assertEqual(resources["test"], "item <= 0")
        self.assertEqual(R.derived_args_for("daily", 7)[0], R.DERIVED_DAILY_ITEM)
        self.assertEqual(R.DERIVED_DAILY_ITEM, 0)
        self.assertIn("command.py", R.DERIVED_DAILY_ITEM_SOURCE)

    def test_derived_args_for_refuses_an_unknown_action_and_a_bad_cursor(self) -> None:
        with self.assertRaises(P.EnvelopeError) as caught:
            R.derived_args_for("unknown", 0)
        self.assertEqual(caught.exception.code, R.REASON_UNKNOWN_ACTION)
        for bad in (None, "3", 1.0, True, [0]):
            with self.subTest(cursor=bad):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.derived_args_for("daily", bad)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_CURSOR)


# ======================================================= the refusal contract --
class RefusalOrderTests(unittest.TestCase):
    """The pinned order, and why it is a strict improvement on its opposite."""

    def test_the_pinned_order_is_twelve_and_splits_request_shape_from_state(self) -> None:
        self.assertEqual(len(R.VALIDATION_ORDER), 12)
        self.assertEqual(R.VALIDATION_ORDER, (
            "bad_request",
            "unknown_action",
            "client_supplied_item",
            "client_supplied_item_index",
            "client_supplied_cell",
            "client_supplied_player",
            "client_supplied_next_id",
            "client_supplied_amount",
            "client_supplied_price",
            "absent_reward_cursor",
            "invalid_reward_cursor",
            "absent_reward_instant",
        ))
        self.assertEqual(R.REQUEST_SHAPE_REFUSALS, R.VALIDATION_ORDER[:9])
        self.assertEqual(R.RECORDED_STATE_REFUSALS, R.VALIDATION_ORDER[9:])
        self.assertEqual(R.STRUCTURAL_REFUSALS, R.VALIDATION_ORDER)
        self.assertEqual(len(R.REQUEST_SHAPE_REFUSALS), 9)
        self.assertEqual(len(R.RECORDED_STATE_REFUSALS), 3)

    def test_seven_grant_shaped_classes_are_refused_by_name(self) -> None:
        self.assertEqual(len(R.CLIENT_KEY_REFUSALS), 7)
        self.assertEqual(
            [key for key, _reason in R.CLIENT_KEY_REFUSALS],
            ["item", "item_index", "cell", "player", "next_id", "amount", "price"],
        )
        self.assertEqual(
            R.REFUSAL_REASON_ORDER,
            tuple(reason for _key, reason in R.CLIENT_KEY_REFUSALS),
        )

    def test_the_two_cell_coordinates_are_two_keys_and_one_class(self) -> None:
        """Two request keys resolve one reason, which is why the order is data."""
        self.assertEqual(R.REFUSAL_KEY_MAP["cell"], "client_supplied_cell")
        self.assertEqual(R.REFUSAL_KEY_MAP["x"], "client_supplied_cell")
        self.assertEqual(R.REFUSAL_KEY_MAP["y"], "client_supplied_cell")
        keys_for_cell = sorted(
            key for key, reason in R.REFUSAL_KEY_MAP.items()
            if reason == "client_supplied_cell"
        )
        self.assertEqual(keys_for_cell, ["cell", "x", "y"])
        self.assertEqual(R.REQUEST_KEYS,
                         ("user_id", "action", "item", "item_index", "cell",
                          "player", "next_id", "amount", "price", "x", "y"))
        self.assertEqual(len(R.REQUEST_KEYS), 11)
        self.assertEqual(R.REQUEST_KEYS[:2], ("user_id", "action"))

    def test_a_two_fault_request_is_refused_by_the_pinned_first_class(self) -> None:
        """Order is a claim about *which* refusal a two-fault request gets."""
        payload = {"action": "weekly", "price": 1, "item": 105, "next_id": 9}
        self.assertEqual(R.request_grant_keys(payload), ["item", "next_id", "price"])
        with self.assertRaises(P.EnvelopeError) as caught:
            R.validate_request(payload)
        self.assertEqual(caught.exception.code, R.REASON_CLIENT_SUPPLIED_ITEM)
        # The reverse order in the literal changes nothing, which is what makes
        # the answer a decision rather than an accident.
        reordered = {"action": "weekly", "item": 105, "price": 1, "next_id": 9}
        with self.assertRaises(P.EnvelopeError) as again:
            R.validate_request(reordered)
        self.assertEqual(again.exception.code, caught.exception.code)

    def test_request_grant_keys_is_empty_for_a_non_object(self) -> None:
        for payload in (None, "weekly", 3, ["item"]):
            with self.subTest(payload=payload):
                self.assertEqual(R.request_grant_keys(payload), [])

    def test_request_grant_keys_lists_each_carried_class_once(self) -> None:
        self.assertEqual(R.request_grant_keys({"user_id": 1, "action": "daily"}), [])
        self.assertEqual(R.request_grant_keys({"x": 0, "y": 0}), ["x", "y"])
        self.assertEqual(R.request_grant_keys({"item_index": 4}), ["item_index"])

    def test_the_request_shape_half_is_walked_in_the_pinned_order(self) -> None:
        for payload, expected in (
            (None, "bad_request"),
            ("weekly", "bad_request"),
            ({}, "unknown_action"),
            ({"action": "monthly"}, "unknown_action"),
            ({"action": "WEEKLY"}, "unknown_action"),
            ({"action": "weekly", "amount": 1}, "client_supplied_amount"),
            ({"action": "daily", "price": 5}, "client_supplied_price"),
            ({"action": "weekly", "player": 3}, "client_supplied_player"),
            ({"action": "weekly", "x": 1}, "client_supplied_cell"),
        ):
            with self.subTest(payload=payload, expected=expected):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.validate_request(payload)
                self.assertEqual(caught.exception.code, expected)

    def test_a_well_formed_request_resolves_to_its_action(self) -> None:
        self.assertEqual(R.validate_request({"user_id": 1, "action": "weekly"}), "weekly")
        self.assertEqual(R.validate_request({"action": "daily"}), "daily")

    def test_the_ordering_note_records_why_the_cursor_check_cannot_come_first(self) -> None:
        note = R.VALIDATION_ORDER_NOTE
        self.assertIn("BEFORE THE INSTANT STAMP", note)
        self.assertIn("byte-identical", note)
        self.assertIn("FOR THE WRONG REASON", note)
        self.assertIn("performs no validation at all", note)
        # The reason the request half must precede the state half is recorded on
        # the pinned order itself rather than in the note, so it is read from the
        # source where it is written: the addressed cursor cannot even be *named*
        # until the action is, because each action addresses a different key.
        self.assertIn(
            "cannot even be named until the action is",
            module_source(),
            "the ordering rationale is no longer recorded beside the pinned order",
        )

    def test_the_rejected_ignored_cursor_alternative_is_retained(self) -> None:
        """D2: refusing is chosen over ignoring, and the choice is on the record."""
        note = R.CLIENT_CURSOR_REJECTED_ALTERNATIVE
        self.assertIn("REJECTED ALTERNATIVE", note)
        self.assertIn("level_up", note)
        self.assertIn("Ignoring is right when the ignored value is decorative", note)
        self.assertIn("WRONG for a cursor", note)
        # And the choice is real: a next_id is refused, not ignored.
        with self.assertRaises(P.EnvelopeError) as caught:
            R.validate_request({"action": "daily", "next_id": 99})
        self.assertEqual(caught.exception.code, R.REASON_CLIENT_SUPPLIED_NEXT_ID)


class RefusalReachabilityTests(unittest.TestCase):
    """Task 3.5: every documented refusal must be **reachable**, and the reason
    the quests line's five were not is recorded here rather than repeated."""

    def test_every_request_shape_refusal_is_reachable_from_a_request_body(self) -> None:
        bodies: List[Tuple[Any, str]] = [
            (None, R.REASON_BAD_REQUEST),
            ({"action": "monthly"}, R.REASON_UNKNOWN_ACTION),
            ({"action": "weekly", "item": 105}, R.REASON_CLIENT_SUPPLIED_ITEM),
            ({"action": "weekly", "item_index": 4}, R.REASON_CLIENT_SUPPLIED_ITEM_INDEX),
            ({"action": "weekly", "cell": [1, 2]}, R.REASON_CLIENT_SUPPLIED_CELL),
            ({"action": "weekly", "player": 3}, R.REASON_CLIENT_SUPPLIED_PLAYER),
            ({"action": "daily", "next_id": 9}, R.REASON_CLIENT_SUPPLIED_NEXT_ID),
            ({"action": "daily", "amount": 1}, R.REASON_CLIENT_SUPPLIED_AMOUNT),
            ({"action": "daily", "price": 5}, R.REASON_CLIENT_SUPPLIED_PRICE),
        ]
        reached = set()
        for body, expected in bodies:
            with self.subTest(expected=expected):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.validate_request(body)
                self.assertEqual(caught.exception.code, expected)
                reached.add(caught.exception.code)
        self.assertEqual(reached, set(R.REQUEST_SHAPE_REFUSALS))

    def test_every_recorded_state_refusal_is_reachable_from_a_recorded_state(self) -> None:
        reached = set()
        cases: List[Tuple[Dict[str, Any], str, str]] = [
            # absent cursor: the addressed key is not in the save at all
            (crafted_save(cursor_value=_ABSENT, stamp_value=0),
             R.ACTION_WEEKLY, R.REASON_ABSENT_CURSOR),
            # invalid cursor: the key is present and unreadable
            (crafted_save(cursor_value="3", stamp_value=0),
             R.ACTION_WEEKLY, R.REASON_INVALID_CURSOR),
            # absent instant: the addressed instant is missing
            (crafted_save(cursor_value=0, stamp_value=_ABSENT),
             R.ACTION_WEEKLY, R.REASON_ABSENT_STAMP),
            # no privateState at all -- the cursor is unaddressable
            (crafted_save(with_private_state=False),
             R.ACTION_WEEKLY, R.REASON_ABSENT_CURSOR),
        ]
        for document, action, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.derive_reward(document, action, weekly_schedule())
                self.assertEqual(caught.exception.code, expected)
                reached.add(caught.exception.code)
        self.assertEqual(reached, set(R.RECORDED_STATE_REFUSALS))

    def test_no_refusal_is_vacuous_and_every_reason_is_reachable_somewhere(self) -> None:
        """The quests line shipped five refusals no request could ever reach.

        The mechanism there was a **required** parameter: the transport had to
        send an addressing key, so the "that key is missing" refusal had no input
        that could produce it.  This line cannot repeat that defect for two
        structural reasons, and both are asserted rather than asserted-about:

        * there is **no addressing parameter at all** -- ``ACTION_ADDRESSING_KEY``
          is empty and :func:`addressing_key_for` raises -- so no refusal is
          gated on a value the caller is required to supply;
        * the three recorded-state refusals are driven by the **save**, not by the
          request, and the suite drives each of them from a crafted save above.

        The three **derivation** refusals are a different case and are reported as
        such: they are raised by committed-content and envelope checks, so a
        well-formed request cannot produce them.  They are recorded as unreachable
        from a request rather than dressed up as reachable.
        """
        request_reachable = set(R.REQUEST_SHAPE_REFUSALS) | set(R.RECORDED_STATE_REFUSALS)
        self.assertEqual(len(request_reachable), 12)
        self.assertEqual(R.ACTION_ADDRESSING_KEY, {})
        # Three reasons are **derivation** refusals, owned by a content or
        # envelope check rather than by the request.  They are recorded as
        # unreachable from a request, and each is asserted to exist as a named
        # constant so the record cannot rot into prose.
        unreachable_from_a_request = {
            R.REASON_INVALID_SCHEDULE: "REASON_INVALID_SCHEDULE",
            R.REASON_INVALID_VECTOR: "REASON_INVALID_VECTOR",
            R.REASON_INVALID_TIMESTAMP: "REASON_INVALID_TIMESTAMP",
        }
        for reason, constant in unreachable_from_a_request.items():
            with self.subTest(reason=reason):
                self.assertNotIn(reason, request_reachable)
                self.assertTrue(hasattr(R, constant))
                self.assertEqual(getattr(R, constant), reason)
        # The three are disjoint from the twelve, so nothing is double-counted.
        self.assertEqual(set(unreachable_from_a_request) & request_reachable, set())
        # No refusal reason is listed twice, and none is missing a constant.
        reasons = [
            R.REASON_BAD_REQUEST, R.REASON_UNKNOWN_ACTION, R.REASON_ABSENT_CURSOR,
            R.REASON_ABSENT_STAMP, R.REASON_INVALID_CURSOR, R.REASON_INVALID_VECTOR,
            R.REASON_INVALID_TIMESTAMP, R.REASON_INVALID_SCHEDULE,
        ] + [reason for _key, reason in R.CLIENT_KEY_REFUSALS]
        self.assertEqual(len(reasons), len(set(reasons)))


# ======================================================= the recorded state --
class RecordedStateReadTests(unittest.TestCase):
    """Both cursors and both instants, read copied and never aliased."""

    def test_the_save_object_is_resolved_before_anything_is_read(self) -> None:
        document = crafted_save(cursor_value=2, stamp_value=11)
        private = R.resolve_private_state(document)
        self.assertIs(private, document[R.PRIVATE_STATE_KEY])
        self.assertEqual(R.resolve_document(document), private)
        for bad in (None, "save", 3, ["privateState"]):
            with self.subTest(save=bad):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.resolve_private_state(bad)
                self.assertEqual(caught.exception.code, R.REASON_BAD_REQUEST)
        # A save with no privateState object is refused, never defaulted.
        for bad in ({}, {"privateState": None}, {"privateState": []}, {"privateState": 3}):
            with self.subTest(save=bad):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.resolve_private_state(bad)
                self.assertEqual(caught.exception.code, R.REASON_ABSENT_CURSOR)

    def test_a_read_cursor_is_copied_so_the_legacy_write_cannot_alias_it(self) -> None:
        document = crafted_save(cursor_value=3, stamp_value=7)
        read = R.read_cursor(document, "weekly")
        self.assertEqual(read, 3)
        self.assertIsInstance(read, int)
        # The legacy dispatcher writes through this very dict; a by-reference read
        # would report the after-state, so the copy is asserted by mutation.
        document[R.PRIVATE_STATE_KEY][R.WEEKLY_CURSOR_KEY] = 99
        self.assertEqual(read, 3)

    def test_each_cursor_is_read_only_from_its_own_key(self) -> None:
        document = {"privateState": {
            R.WEEKLY_CURSOR_KEY: 1, R.DAILY_CURSOR_KEY: 4,
            R.WEEKLY_STAMP_KEY: 11, R.DAILY_STAMP_KEY: 22,
        }}
        self.assertEqual(R.read_cursor(document, "weekly"), 1)
        self.assertEqual(R.read_cursor(document, "daily"), 4)
        self.assertEqual(R.read_stamp(document, "weekly"), 11)
        self.assertEqual(R.read_stamp(document, "daily"), 22)
        # Each cursor refuses the other's key, so the mapping is not a lookup that
        # happens to agree: removing the daily cursor leaves weekly readable and
        # daily refused.
        del document[R.PRIVATE_STATE_KEY][R.DAILY_CURSOR_KEY]
        self.assertEqual(R.read_cursor(document, "weekly"), 1)
        with self.assertRaises(P.EnvelopeError) as caught:
            R.read_cursor(document, "daily")
        self.assertEqual(caught.exception.code, R.REASON_ABSENT_CURSOR)

    def test_an_absent_key_and_an_unreadable_value_get_two_different_reasons(self) -> None:
        """Answering both with one reason would make half the pinned order dead."""
        self.assertEqual(R.REASON_ABSENT_CURSOR, "absent_reward_cursor")
        self.assertEqual(R.REASON_INVALID_CURSOR, "invalid_reward_cursor")
        self.assertNotEqual(R.REASON_ABSENT_CURSOR, R.REASON_INVALID_CURSOR)
        absent = crafted_save(cursor_value=_ABSENT, stamp_value=0)
        unreadable = crafted_save(cursor_value="3", stamp_value=0)
        with self.assertRaises(P.EnvelopeError) as first:
            R.read_cursor(absent, "weekly")
        self.assertEqual(first.exception.code, R.REASON_ABSENT_CURSOR)
        with self.assertRaises(P.EnvelopeError) as second:
            R.read_cursor(unreadable, "weekly")
        self.assertEqual(second.exception.code, R.REASON_INVALID_CURSOR)

    def test_a_bool_is_not_accepted_as_a_recorded_integer(self) -> None:
        for value in (True, False, 1.0, "0", None, [], {}):
            with self.subTest(value=value):
                document = crafted_save(cursor_value=value, stamp_value=0)
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.read_cursor(document, "weekly")
                self.assertEqual(caught.exception.code, R.REASON_INVALID_CURSOR)
        # ... and a real int is accepted, so the guard is not a blanket refusal.
        self.assertEqual(
            R.read_cursor(crafted_save(cursor_value=0, stamp_value=0), "weekly"), 0
        )

    def test_an_absent_instant_is_refused_rather_than_created(self) -> None:
        """A created key changes privateState's size and would break the exact
        leaf allowlist that carries the four-part grant proof."""
        document = crafted_save(cursor_value=0, stamp_value=_ABSENT)
        with self.assertRaises(P.EnvelopeError) as caught:
            R.read_stamp(document, "weekly")
        self.assertEqual(caught.exception.code, R.REASON_ABSENT_STAMP)
        self.assertNotIn(R.WEEKLY_STAMP_KEY, document[R.PRIVATE_STATE_KEY])
        # And no committed document needs the refusal: every one carries both.
        for relative, saved in committed_save_documents():
            private = saved["privateState"]
            for key in R.INSTANTS:
                with self.subTest(document=relative, instant=key):
                    self.assertIn(key, private)

    def test_both_readers_refuse_an_unknown_action(self) -> None:
        for reader in (R.read_cursor, R.read_stamp):
            with self.subTest(reader=reader.__name__):
                with self.assertRaises(P.EnvelopeError) as caught:
                    reader(crafted_save(), "monthly")
                self.assertEqual(caught.exception.code, R.REASON_UNKNOWN_ACTION)

    def test_both_instant_readers_share_the_invalid_reason_for_an_unreadable_value(
        self,
    ) -> None:
        for key, action in (
            (R.WEEKLY_STAMP_KEY, "weekly"), (R.DAILY_STAMP_KEY, "daily")
        ):
            with self.subTest(instant=key):
                document = crafted_save(cursor_value=0, stamp_value="x", stamp_key=key)
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.read_stamp(document, action)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_CURSOR)


# =================================================== the derived bounds (D3/D4) --
class BoundTests(unittest.TestCase):
    """Task 3.2: the bounds are **re-derived from the committed schedule** here, so
    a legacy edit fails this suite rather than silently contradicting it."""

    def test_the_weekly_bound_is_re_derived_from_the_committed_schedule(self) -> None:
        """``get_weekly_reward_length``'s rule, transcribed: floor 1, then the
        maximum length over the entries whose ``value`` is a **list**."""
        schedule = weekly_schedule()
        self.assertIsInstance(schedule, list)
        self.assertEqual(R.WEEKLY_BOUND_FLOOR, 1)
        expected = 1
        for entry in schedule:
            if isinstance(entry.get("value"), list):
                expected = max(expected, len(entry["value"]))
        self.assertEqual(expected, 5)
        self.assertEqual(R.weekly_bound(schedule), expected)
        # The bound is the maximum entry length, never the entry count -- the two
        # differ, and design D3 requires both to be visible.
        self.assertEqual(R.schedule_cardinality(schedule), 3)
        self.assertNotEqual(R.weekly_bound(schedule), R.schedule_cardinality(schedule))
        self.assertEqual(R.weekly_bound(schedule) - R.schedule_cardinality(schedule), 2)

    def test_the_bound_is_re_derived_from_the_committed_bytes_on_every_run(self) -> None:
        """The committed schedule's shape is read, not assumed."""
        rows = committed_globals()
        self.assertEqual(len(rows), 105)
        schedule = rows[R.WEEKLY_SCHEDULE_KEY]
        self.assertEqual(len(schedule), 3)
        for entry in schedule:
            with self.subTest(entry=entry):
                self.assertIsInstance(entry, dict)
                self.assertEqual(sorted(entry), ["type", "value"])
        list_valued = [e for e in schedule if isinstance(e["value"], list)]
        self.assertEqual(len(list_valued), 1)
        self.assertEqual(len(list_valued[0]["value"]), 5)
        self.assertEqual(R.weekly_bound(schedule), len(list_valued[0]["value"]))

    def test_the_floor_is_load_bearing_and_transcribed_verbatim(self) -> None:
        """A schedule whose every value were a scalar returns 1, not 0."""
        self.assertEqual(R.weekly_bound([{"type": "g", "value": 2500}]), 1)
        self.assertEqual(R.weekly_bound([{"type": "g", "value": 2500},
                                         {"type": "c", "value": 5}]), 1)
        self.assertIn("get_weekly_reward_length", R.WEEKLY_BOUND_SOURCE)
        self.assertEqual(R.WEEKLY_BOUND_SOURCE,
                         "get_game_config.py:195-204 (get_weekly_reward_length)")
        # The seed and the max-over-lists are in the preserved source, verified as
        # bytes rather than taken on trust.  The source tests the shape with
        # ``type(value) == list`` and not ``isinstance``; the delivered derivation
        # uses ``isinstance``, which agrees on every committed entry and is the
        # stricter reading for a subclass -- recorded here rather than asserted
        # as identical.
        source = legacy_text("get_game_config.py").split("\n")
        body = "\n".join(source[194:204])
        self.assertIn("length = 1", body)
        self.assertIn("max(", body)
        self.assertIn("type(value) == list", body)
        self.assertNotIn("isinstance", body)
        # Both readings agree on the committed schedule, so the difference is
        # unobservable here -- which is why it is a note and not a defect.
        committed = weekly_schedule()
        by_type = 1
        by_instance = 1
        for entry in committed:
            value = entry["value"]
            if type(value) == list:  # noqa: E721  (the preserved spelling)
                by_type = max(by_type, len(value))
            if isinstance(value, list):
                by_instance = max(by_instance, len(value))
        self.assertEqual(by_type, by_instance)
        self.assertEqual(by_type, R.weekly_bound(committed))

    def test_a_malformed_weekly_entry_is_refused_rather_than_skipped(self) -> None:
        """Skipping would let a broken rung change the derived bound silently."""
        for schedule in ([], None, {}, "x", 5):
            with self.subTest(schedule=schedule):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.weekly_bound(schedule)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_SCHEDULE)
        for entry in ([5], [None], [{"value": 1}, 7], [{"type": "g"}]):
            with self.subTest(entry=entry):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.weekly_bound(entry)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_SCHEDULE)

    def test_the_daily_bound_is_the_hardcoded_literal_and_not_a_derivation(self) -> None:
        """D4: the literal at ``command.py:451``, with the rejected alternative
        retained so the five-equals-five agreement is not mistaken for provenance."""
        self.assertEqual(R.DAILY_BOUND_LITERAL, 5)
        self.assertEqual(R.daily_bound(), 5)
        self.assertEqual(R.DAILY_WRAP_TARGET, 1)
        self.assertIn("command.py:451", R.DAILY_BOUND_SOURCE)
        self.assertIn("hardcoded literal", R.DAILY_BOUND_SOURCE)
        # The literal is transcribed from the preserved source, located by line.
        lines = legacy_lines("command.py")
        line_number, line = next(
            (number, text) for number, text in enumerate(lines, 1)
            if "if next_id > 5:" in text
        )
        self.assertEqual(line_number, 451)
        self.assertIn("next_id = 1", lines[line_number])
        # The agreement with the daily schedule is a coincidence, and the record
        # says so -- while the entry count is reported rather than used.
        self.assertEqual(len(daily_schedule()), 5)
        self.assertEqual(R.DAILY_SCHEDULE_CARDINALITY, 5)
        rejected = R.DAILY_BOUND_REJECTED_DERIVATION
        self.assertIn("REJECTED ALTERNATIVE", rejected)
        self.assertIn("NOT provenance", rejected)
        self.assertIn("coincidence", rejected)

    def test_the_daily_bound_equals_the_literal_not_the_committed_entry_count(self) -> None:
        """Even where the two agree, the delivered bound is the literal."""
        self.assertEqual(R.daily_bound(), R.DAILY_BOUND_LITERAL)
        self.assertEqual(R.daily_bound(), len(daily_schedule()))
        # The derivation returns the constant; changing the caller's schedule
        # cannot move it, which is what "not content-derived" means mechanically.
        self.assertEqual(R.daily_bound(), 5)


class SuccessorTests(unittest.TestCase):
    """Both successors, transcribed from the preserved branches' own arithmetic."""

    def test_the_weekly_successor_is_the_branchs_modulo_over_the_derived_bound(self) -> None:
        bound = R.weekly_bound(weekly_schedule())
        self.assertEqual(
            [(before, R.weekly_successor(before, bound)) for before in range(5)],
            [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)],
        )
        # The preserved expression is the same modulo, located in the source.
        source = legacy_text("command.py")
        self.assertIn('(save["privateState"]["weeklyRewardIndex"] + 1) %', source)
        self.assertIn("get_weekly_reward_length()", source)

    def test_the_daily_successor_increments_and_wraps_onto_the_first_position(self) -> None:
        self.assertEqual(
            [(before, R.daily_successor(before)) for before in range(5)],
            [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
        )
        # Above the literal it wraps onto 1, which is the backwards move design D5
        # records as a divergence of the preserved branch.
        self.assertEqual(R.daily_successor(5), 1)
        self.assertEqual(R.daily_successor(6), 1)
        self.assertEqual(R.daily_successor(99), 1)

    def test_both_successors_refuse_an_unreadable_recorded_cursor(self) -> None:
        for bad in (None, "3", 1.5, True, [], {}):
            with self.subTest(before=bad):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.weekly_successor(bad, 5)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_CURSOR)
                with self.assertRaises(P.EnvelopeError) as also:
                    R.daily_successor(bad)
                self.assertEqual(also.exception.code, R.REASON_INVALID_CURSOR)

    def test_the_weekly_successor_refuses_an_underivable_bound(self) -> None:
        """A bound of zero is refused rather than raising a ZeroDivisionError."""
        for bound in (0, -1, None, "5", 2.5, True):
            with self.subTest(bound=bound):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.weekly_successor(0, bound)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_SCHEDULE)

    def test_the_reachable_ranges_are_derived_from_the_branches_own_arithmetic(self) -> None:
        """Both closed ranges, computed rather than transcribed."""
        weekly = sorted({R.weekly_successor(v, 5) for v in range(5)})
        daily = sorted({R.daily_successor(v) for v in range(5)})
        self.assertEqual(weekly, [0, 1, 2, 3, 4])
        self.assertEqual(daily, [1, 2, 3, 4, 5])
        self.assertEqual(list(R.WEEKLY_REACHABLE), weekly)
        self.assertEqual(list(R.DAILY_REACHABLE), daily)
        self.assertEqual(R.ACTION_REACHABLE,
                         {"weekly": (0, 1, 2, 3, 4), "daily": (1, 2, 3, 4, 5)})


# =========================================================== the reachability --
class ReachabilityTests(unittest.TestCase):
    """A set difference in **both** directions, and never a schedule lookup."""

    def setUp(self) -> None:
        self.weekly = R.reachable_report(
            R.weekly_bound(weekly_schedule()),
            R.schedule_cardinality(weekly_schedule()),
            R.WEEKLY_REACHABLE,
        )
        self.daily = R.reachable_report(
            R.daily_bound(),
            R.schedule_cardinality(daily_schedule()),
            R.DAILY_REACHABLE,
        )

    def test_the_report_carries_both_differences_and_its_own_parameters(self) -> None:
        for report in (self.weekly, self.daily):
            with self.subTest(bound=report["bound"]):
                self.assertEqual(
                    sorted(report),
                    ["answerable", "answerable_not_reachable", "bound", "cardinality",
                     "index_base", "index_base_status", "reachable",
                     "reachable_not_answerable", "selection_performed"],
                )
                self.assertTrue(
                    report["reachable_not_answerable"]
                    or report["answerable_not_reachable"]
                )

    def test_the_weekly_mismatch_names_three_and_four(self) -> None:
        self.assertEqual(self.weekly["bound"], 5)
        self.assertEqual(self.weekly["cardinality"], 3)
        self.assertEqual(self.weekly["reachable"], [0, 1, 2, 3, 4])
        self.assertEqual(self.weekly["answerable"], [0, 1, 2])
        self.assertEqual(self.weekly["reachable_not_answerable"], [3, 4])
        self.assertEqual(self.weekly["answerable_not_reachable"], [])

    def test_the_daily_mismatch_names_five_and_zero_in_opposite_directions(self) -> None:
        """Both directions differ here, which is the reason for reporting both."""
        self.assertEqual(self.daily["bound"], 5)
        self.assertEqual(self.daily["cardinality"], 5)
        self.assertEqual(self.daily["reachable"], [1, 2, 3, 4, 5])
        self.assertEqual(self.daily["answerable"], [0, 1, 2, 3, 4])
        self.assertEqual(self.daily["reachable_not_answerable"], [5])
        self.assertEqual(self.daily["answerable_not_reachable"], [0])
        self.assertTrue(self.daily["answerable_not_reachable"],
                        "the second direction is never empty in practice")

    def test_no_selection_is_performed_and_the_index_base_is_recorded_provisional(
        self,
    ) -> None:
        for report in (self.weekly, self.daily):
            with self.subTest(bound=report["bound"]):
                self.assertIs(report["selection_performed"], False)
                self.assertEqual(report["index_base"], R.SCHEDULE_INDEX_BASE)
                self.assertEqual(report["index_base"], 0)
                self.assertEqual(report["index_base_status"],
                                 R.SCHEDULE_INDEX_BASE_STATUS)
        self.assertEqual(R.SCHEDULE_INDEX_BASE_ALTERNATIVE, 1)
        status = R.SCHEDULE_INDEX_BASE_STATUS
        self.assertIn("DERIVED-PROVISIONAL", status)
        self.assertIn("neither is asserted as fact", status)

    def test_the_reachable_range_is_a_parameter_because_both_bounds_are_five(self) -> None:
        """The two reports must not be conflatable, and both bounds are 5."""
        self.assertEqual(self.weekly["bound"], self.daily["bound"])
        self.assertNotEqual(self.weekly["reachable"], self.daily["reachable"])
        self.assertNotEqual(self.weekly["reachable_not_answerable"],
                            self.daily["reachable_not_answerable"])

    def test_the_report_refuses_an_underivable_bound_or_cardinality(self) -> None:
        for bound in (0, -1, None, "5", 1.5, True):
            with self.subTest(bound=bound):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.reachable_report(bound, 3, R.WEEKLY_REACHABLE)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_SCHEDULE)
        for cardinality in (-1, None, "3", 1.5, True):
            with self.subTest(cardinality=cardinality):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.reachable_report(5, cardinality, R.WEEKLY_REACHABLE)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_SCHEDULE)

    def test_no_schedule_lookup_survives_in_the_reachability_report(self) -> None:
        """A lookup would need the schedule; the signature never receives one."""
        import inspect

        parameters = list(inspect.signature(R.reachable_report).parameters)
        self.assertEqual(parameters, ["bound", "cardinality", "reachable"])
        for banned in ("schedule", "entries", "letters", "types", "schedule_name"):
            with self.subTest(parameter=banned):
                self.assertNotIn(banned, parameters)
        # And the function performs no indexing of any container it was handed.
        body = ast.unparse(ast.parse(module_source()))
        node = next(
            item for item in ast.walk(ast.parse(module_source()))
            if isinstance(item, ast.FunctionDef) and item.name == "reachable_report"
        )
        subscripts = [
            child for child in ast.walk(node) if isinstance(child, ast.Subscript)
        ]
        # Only local ``dict``/``set`` literals are indexed; there is no lookup of
        # a passed-in container by an index.
        self.assertTrue(all(
            isinstance(child.value, (ast.Name, ast.Dict, ast.List, ast.Tuple, ast.Set))
            for child in subscripts
        ))
        del body


# ======================================================= the whole-document proof --
class WholeDocumentProofTests(unittest.TestCase):
    """D6/D9: the four-part grant proof as a two-path leaf allowlist."""

    def test_the_allowlist_is_exactly_the_addressed_cursor_and_instant(self) -> None:
        self.assertEqual(
            R.allowed_leaf_paths("weekly"),
            ["/privateState/weeklyRewardIndex", "/privateState/timeStampMondayBonus"],
        )
        self.assertEqual(
            R.allowed_leaf_paths("daily"),
            ["/privateState/bonusNextId", "/privateState/timestampLastBonus"],
        )
        for action in R.ACTIONS:
            with self.subTest(action=action):
                paths = R.allowed_leaf_paths(action)
                self.assertEqual(len(paths), 2)
                self.assertEqual(paths[0],
                                 "/privateState/%s" % R.ACTION_CURSOR_KEY[action])
                self.assertEqual(paths[1],
                                 "/privateState/%s" % R.ACTION_STAMP_KEY[action])
                # No map row, no bought-units list, no store, no resource.
                joined = " ".join(paths)
                for foreign in (R.MAP_ITEMS_KEY, R.WEEKLY_UNIT_LIST_KEY,
                                R.DAILY_STORE_KEY):
                    with self.subTest(foreign=foreign):
                        self.assertNotIn("/%s" % foreign, joined)
                self.assertFalse(any(path.startswith("/maps") for path in paths))

    def test_a_transition_touches_only_the_two_allowed_paths(self) -> None:
        before = seeded_save()
        after = json.loads(json.dumps(before))
        after[R.PRIVATE_STATE_KEY][R.WEEKLY_CURSOR_KEY] += 1
        after[R.PRIVATE_STATE_KEY][R.WEEKLY_STAMP_KEY] = 1791066504
        changed = R.leaf_diff(before, after)
        self.assertEqual(
            changed,
            ["/privateState/timeStampMondayBonus", "/privateState/weeklyRewardIndex"],
        )
        self.assertIsNone(R.allowed_paths_problem("weekly", changed))

    def test_each_of_the_four_grant_places_is_caught(self) -> None:
        """The proof is only worth anything if it fails on all four landings."""
        before = seeded_save()
        allowed = R.allowed_leaf_paths("weekly")
        mutations: List[Tuple[str, Any]] = [
            ("a placed row", lambda d: d["maps"][0]["items"].__setitem__("99", [22, 1, 1, 0, 0, [], {}, 1])),
            ("a bought-units append",
             lambda d: d[R.PRIVATE_STATE_KEY][R.WEEKLY_UNIT_LIST_KEY].append(105)),
            ("a storage entry",
             lambda d: d["maps"][0][R.DAILY_STORE_KEY].__setitem__("1085", 1)),
            ("a stored resource moved",
             lambda d: d["maps"][0].__setitem__("gold", d["maps"][0]["gold"] + 2500)),
        ]
        for label, mutate in mutations:
            with self.subTest(landing=label):
                after = json.loads(json.dumps(before))
                mutate(after)
                changed = R.leaf_diff(before, after)
                problem = R.allowed_paths_problem("weekly", changed)
                self.assertIsNotNone(problem, "%s was not caught" % label)
                # The named offender is the landing itself, never an allowed path.
                offenders = [p for p in changed if p not in allowed]
                self.assertTrue(offenders)
                self.assertIn(offenders[0].lstrip("/"), problem)

    def test_a_created_key_is_a_difference_even_when_its_value_is_empty(self) -> None:
        """A leaves-only projection would report no change for an added empty
        object, and the proof would pass on a grant it exists to catch."""
        before = {"privateState": {"weeklyRewardIndex": 0}}
        after = {"privateState": {"weeklyRewardIndex": 0, "granted": {}}}
        changed = R.leaf_diff(before, after)
        self.assertEqual(changed, ["/privateState", "/privateState/granted"])
        self.assertIsNotNone(R.allowed_paths_problem("weekly", changed))
        # And the container marker is what carries it.
        leaves = R.document_leaves(after)
        self.assertEqual(leaves["/privateState/granted"], "<object:0>")
        self.assertEqual(leaves["/privateState"], "<object:2>")
        self.assertEqual(leaves[""], "<object:1>")
        self.assertEqual(leaves["/privateState/weeklyRewardIndex"], 0)

    def test_a_removed_key_and_a_resized_container_are_differences(self) -> None:
        before = {"a": 1, "b": [1, 2, 3], "c": {"d": 1}}
        after = {"a": 1, "b": [1, 2], "c": {}}
        # ``/c`` differs too: its size marker goes from one key to none, which is
        # the container half of the projection doing its job.
        self.assertEqual(
            R.leaf_diff(before, after),
            ["/b", "/b/2", "/c", "/c/d"],
        )

    def test_containers_carry_size_markers_and_leaves_carry_their_values(self) -> None:
        document = {"s": "x", "n": 1, "f": 1.5, "t": True, "z": None,
                    "l": [1, "a"], "o": {"k": []}}
        leaves = R.document_leaves(document)
        self.assertEqual(leaves[""], "<object:7>")
        self.assertEqual(leaves["/l"], "<array:2>")
        self.assertEqual(leaves["/l/0"], 1)
        self.assertEqual(leaves["/l/1"], "a")
        self.assertEqual(leaves["/o"], "<object:1>")
        self.assertEqual(leaves["/o/k"], "<array:0>")
        self.assertIs(leaves["/t"], True)
        self.assertIsNone(leaves["/z"])
        self.assertEqual(leaves["/n"], 1)
        self.assertEqual(leaves["/f"], 1.5)

    def test_an_identical_document_has_no_changed_paths(self) -> None:
        before = seeded_save()
        after = json.loads(json.dumps(before))
        self.assertEqual(R.leaf_diff(before, after), [])
        self.assertIsNone(R.allowed_paths_problem("weekly", []))
        # And the projections themselves agree, so the emptiness is real.
        self.assertEqual(R.document_leaves(before), R.document_leaves(after))

    def test_allowed_paths_problem_names_the_first_offending_path_in_sorted_order(
        self,
    ) -> None:
        changed = ["/privateState/weeklyRewardIndex", "/maps/0/items/9", "/b"]
        problem = R.allowed_paths_problem("weekly", changed)
        self.assertIsNotNone(problem)
        self.assertIn("/b", problem)
        self.assertNotIn("/maps/0/items/9", problem.split("-")[0])
        # The message names both allowed paths so a reader sees the whole set.
        self.assertIn("weeklyRewardIndex", problem)
        self.assertIn("timeStampMondayBonus", problem)

    def test_allowed_leaf_paths_refuses_an_unknown_action(self) -> None:
        for action in ("monthly", "", None, 1):
            with self.subTest(action=action):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.allowed_leaf_paths(action)
                self.assertEqual(caught.exception.code, R.REASON_UNKNOWN_ACTION)

    def test_the_no_grant_note_states_the_four_parts_and_the_carrier(self) -> None:
        note = R.NO_GRANT
        # The note is prose; the four parts are named **keys**, and they live in
        # the grant block rather than here.  Both are checked, in the right place.
        for part in ("(1) no map row", "(2) no bought-units append",
                     "(3) no storage entry", "(4) no stored resource moved"):
            with self.subTest(part=part):
                self.assertIn(part, note)
        self.assertIn("WHOLE-DOCUMENT LEAF ALLOWLIST", note)
        self.assertIn("cannot miss a fifth landing place", note)
        self.assertIn("VERIFIED PROPERTY", note)


class GrantProofShapeTests(unittest.TestCase):
    """The proof the response *reports*, which must carry all four parts."""

    def _grant_block(self, action: str) -> Dict[str, Any]:
        result = R.derive_reward(seeded_save(), action, weekly_schedule(),
                                 daily_schedule(), ts=1)
        return dict(result.grant)

    def test_the_grant_block_reports_all_four_parts_and_nothing_granted(self) -> None:
        for action in R.ACTIONS:
            with self.subTest(action=action):
                grant = self._grant_block(action)
                self.assertIs(grant["grants_nothing"], True)
                for part in ("part_1_no_map_row", "part_2_no_bought_units_append",
                             "part_3_no_storage_entry",
                             "part_4_no_stored_resource_moved"):
                    with self.subTest(part=part):
                        self.assertIn(part, grant)
                        self.assertTrue(str(grant[part]).strip())
                self.assertIn("as a set and not as a", grant["part_4_no_stored_resource_moved"])
                self.assertEqual(grant["allowed_leaf_paths"],
                                 R.allowed_leaf_paths(action))
                self.assertIn("FOUR-PART PROOF", grant["note"])
                # Nothing in the block names an amount, a resource, or a grant
                # shape as a value.
                self.assertNotIn("amount", grant)
                self.assertNotIn("items", grant)


# ========================================================= the neutral vector --
class NeutralVectorTests(unittest.TestCase):
    """A reward action moves no stored resource, and the derivation cannot say
    that it does."""

    def test_the_vector_is_eight_slots_of_zero(self) -> None:
        vector = R.neutral_vector()
        self.assertEqual(vector, [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(len(vector), 8)
        self.assertEqual(R.RESOURCE_VECTOR_SLOTS, 8)
        self.assertIsInstance(R.RESOURCE_VECTOR_SLOTS, int)
        # The width is the declared constant, never a derived length -- so a
        # changed width cannot silently follow a changed table.
        self.assertEqual(len(vector), R.RESOURCE_VECTOR_SLOTS)

    def test_the_eight_slots_are_the_eight_legacy_unpacks_in_committed_order(self) -> None:
        """``engine.apply_resources`` unpacks eight slots; the enumeration and the
        count are both re-derived from the preserved source, because a count that
        is right beside a list that is wrong is the worse defect of the two.

        ``oil`` sits between wood and steel.  A first draft of this comment
        listed seven names and dropped it; the correction is in the module.
        """
        body = "\n".join(legacy_text("engine.py").split("\n")[250:271])
        unpacks = re.findall(r"^\s*(\w+) = resource\[(\d+)\]$", body, re.MULTILINE)
        self.assertEqual(
            unpacks,
            [("unknown", "0"), ("xp", "1"), ("gold", "2"), ("wood", "3"),
             ("oil", "4"), ("steel", "5"), ("cash", "6"), ("mana", "7")],
        )
        self.assertEqual(len(unpacks), R.RESOURCE_VECTOR_SLOTS)
        self.assertEqual(len(unpacks), 8)
        # Seven of the eight are written to the save; ``unknown`` is discarded.
        self.assertIn("map[\"gold\"] = max(map[\"gold\"] + gold, 0)", body)
        self.assertIn("save[\"privateState\"][\"mana\"]", body)
        # And the clamp is ``max(current + delta, 0)``, which is why a negative
        # slot is a burn rather than a rejection: seven writes, seven clamps.
        self.assertEqual(body.count("max("), 7)

    def test_energy_is_a_stored_resource_but_never_a_slot_of_the_vector(self) -> None:
        """A real ninth resource under its own name, and the vector's blind spot."""
        body = "\n".join(legacy_text("engine.py").split("\n")[250:271])
        self.assertNotIn("energy", body)
        # Nor does any other module write it through this vector.
        self.assertEqual(pattern_hits(r"\benergy\b"), (0, 0))
        # The committed corpus carries it by its own name.
        self.assertEqual(seeded_save()["privateState"]["energy"], 50)
        # So the energy half of the no-resource-moved proof cannot come from the
        # vector: it comes from the whole-document containment half.
        self.assertIn("never writes it", module_source())
        self.assertNotIn("/privateState/energy", R.allowed_leaf_paths("weekly"))
        # ... and an energy change IS caught by the allowlist, as a foreign path.
        before = seeded_save()
        after = json.loads(json.dumps(before))
        after["privateState"]["energy"] = 999
        self.assertIn("/privateState/energy", R.leaf_diff(before, after))
        self.assertIsNotNone(R.allowed_paths_problem("weekly", ["/privateState/energy"]))

    def test_a_fresh_list_is_returned_so_one_call_cannot_poison_the_next(self) -> None:
        first = R.neutral_vector()
        first[0] = 999
        self.assertEqual(R.neutral_vector(), [0] * 8)
        self.assertIsNot(R.neutral_vector(), R.neutral_vector())

    def test_every_non_zero_slot_is_refused(self) -> None:
        """A positive entry is a client-trusted mint and a negative one a burn."""
        for index in range(R.RESOURCE_VECTOR_SLOTS):
            for value in (1, -1, 2500):
                vector = R.neutral_vector()
                vector[index] = value
                with self.subTest(slot=index, value=value):
                    with self.assertRaises(P.EnvelopeError) as caught:
                        R.validate_vector(vector)
                    self.assertEqual(caught.exception.code, R.REASON_INVALID_VECTOR)

    def test_a_wrong_width_or_a_non_list_is_refused(self) -> None:
        for vector in ([0] * 7, [0] * 9, [], None, "00000000", {"0": 0}, (0,) * 8):
            with self.subTest(vector=vector):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.validate_vector(vector)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_VECTOR)

    def test_a_non_integer_slot_is_refused_even_at_zero(self) -> None:
        """``True`` is worth 1 under legacy's arithmetic, so bool is not an int."""
        for value in (True, False, 0.0, "0", None):
            vector = R.neutral_vector()
            vector[2] = value
            with self.subTest(value=value):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.validate_vector(vector)
                self.assertEqual(caught.exception.code, R.REASON_INVALID_VECTOR)

    def test_the_valid_neutral_vector_is_returned_as_a_copy(self) -> None:
        vector = R.neutral_vector()
        returned = R.validate_vector(vector)
        self.assertEqual(returned, vector)
        self.assertIsNot(returned, vector)
        returned[0] = 1
        self.assertEqual(vector[0], 0)


class EnvelopeTests(unittest.TestCase):
    """The derived six-key batch envelope: one command, a neutral vector."""

    def test_the_envelope_carries_exactly_one_command_and_a_neutral_vector(self) -> None:
        envelope = R.build_envelope("weekly", 3, ts=1)
        self.assertEqual(sorted(envelope), sorted(P.ENVELOPE_KEYS))
        self.assertEqual(envelope["first_number"], 0)
        self.assertEqual(envelope["publishActions"], [])
        self.assertEqual(envelope["tries"], 1)
        self.assertEqual(envelope["accessToken"], "")
        self.assertEqual(envelope["ts"], 1)
        self.assertEqual(len(envelope["commands"]), 1)
        self.assertEqual(envelope["commands"][0][0], 0)
        self.assertEqual(envelope["commands"][0][1], "weekly_reward")
        self.assertEqual(envelope["commands"][0][2], [])
        self.assertEqual(envelope["commands"][0][3], [0] * 8)

    def test_the_daily_command_carries_exactly_the_two_derived_arguments(self) -> None:
        envelope = R.build_envelope("daily", 4, ts=1)
        command = envelope["commands"][0]
        self.assertEqual(command[1], "win_daily_bonus")
        self.assertEqual(command[2], [0, 4])
        self.assertEqual(command[3], [0] * 8)

    def test_the_argument_count_is_checked_against_the_recorded_table(self) -> None:
        """The derivation and the recorded table cannot disagree silently."""
        self.assertEqual(R.ACTION_ARGUMENT_COUNT, {"weekly": 0, "daily": 2})
        for action in R.ACTIONS:
            with self.subTest(action=action):
                command = R.build_envelope(action, 0, ts=1)["commands"][0]
                self.assertEqual(len(command[2]), R.ACTION_ARGUMENT_COUNT[action])

    def test_the_envelope_is_json_serialisable_and_carries_no_wall_clock_value(self) -> None:
        envelope = R.build_envelope("weekly", 0, ts=1)
        text = P.payload_json(envelope)
        self.assertIsInstance(text, str)
        self.assertIn("weekly_reward", text)
        # With an explicit ts the envelope is byte-deterministic, which is what
        # makes the fixture's envelope comparison possible at all.
        self.assertEqual(P.payload_json(R.build_envelope("weekly", 0, ts=1)), text)

    def test_the_default_stamp_is_the_current_time_and_the_only_time_reference(self) -> None:
        import time as wall_clock

        before = int(wall_clock.time())
        envelope = R.build_envelope("weekly", 0)
        after = int(wall_clock.time())
        self.assertGreaterEqual(envelope["ts"], before)
        self.assertLessEqual(envelope["ts"], after)
        # And the module's only time reference is that default, verified by AST
        # rather than by reading: no elapsed-time comparison could exist.
        node = next(
            item for item in ast.walk(ast.parse(module_source()))
            if isinstance(item, ast.FunctionDef) and item.name == "build_envelope"
        )
        attributes = [
            (child.attr, child.lineno) for child in ast.walk(node)
            if isinstance(child, ast.Attribute)
        ]
        # Exactly one time reference -- the ``ts=None`` default -- and one string
        # join, which builds a refusal message.  No elapsed-time comparison could
        # exist here, which is what design D8 requires.
        self.assertEqual(sorted(attr for attr, _line in attributes), ["join", "time"])
        time_lines = [line for attr, line in attributes if attr == "time"]
        self.assertEqual(len(time_lines), 1)
        self.assertIn("int(time.time())", module_source())

    def test_a_bad_action_cursor_vector_or_stamp_is_refused(self) -> None:
        with self.assertRaises(P.EnvelopeError) as caught:
            R.build_envelope("monthly", 0, ts=1)
        self.assertEqual(caught.exception.code, R.REASON_UNKNOWN_ACTION)
        for cursor in ("3", None, 1.5, True):
            with self.subTest(cursor=cursor):
                with self.assertRaises(P.EnvelopeError) as also:
                    R.build_envelope("daily", cursor, ts=1)
                self.assertEqual(also.exception.code, R.REASON_INVALID_CURSOR)
        for stamp in (-1, "1", 1.5, True):
            with self.subTest(stamp=stamp):
                with self.assertRaises(P.EnvelopeError) as also:
                    R.build_envelope("weekly", 0, ts=stamp)
                self.assertEqual(also.exception.code, R.REASON_INVALID_TIMESTAMP)


# ============================================================ the typed result --
class RewardResultTests(unittest.TestCase):
    """Task 2.1: the typed transition, and no field named after a reward."""

    def test_no_field_is_named_after_a_granted_paid_or_awarded_reward(self) -> None:
        forbidden = ("reward", "prize", "amount", "gold", "cash", "xp", "wood",
                     "steel", "oil", "mana", "awarded", "paid", "payout", "bonus")
        for field in R.RewardResult._fields:
            with self.subTest(field=field):
                for token in forbidden:
                    self.assertNotIn(token, field.lower())
        for action in R.ACTIONS:
            result = R.derive_reward(seeded_save(), action, weekly_schedule(),
                                     daily_schedule(), ts=1)
            for key in result.payload():
                with self.subTest(action=action, key=key):
                    for token in forbidden:
                        self.assertNotIn(token, key.lower())

    def test_the_payload_carries_exactly_the_reported_keys(self) -> None:
        result = R.derive_reward(seeded_save(), "weekly", weekly_schedule(),
                                 daily_schedule(), ts=1)
        self.assertEqual(sorted(result.payload()), [
            "action", "arms", "bound", "bound_rejected_alternative", "bound_source",
            "bounds", "command", "cursor", "derived_args", "divergences", "grant",
            "instant", "reachability", "schedule_entries", "schedules",
            "type_letters", "volatile_fields",
        ])

    def test_the_cursor_block_reports_before_after_and_change(self) -> None:
        for action, key in (("weekly", "weeklyRewardIndex"), ("daily", "bonusNextId")):
            with self.subTest(action=action):
                save = seeded_save()
                result = R.derive_reward(save, action, weekly_schedule(),
                                         daily_schedule(), ts=1)
                block = result.payload()["cursor"]
                self.assertEqual(sorted(block), ["after", "before", "change", "key"])
                self.assertEqual(block["key"], key)
                self.assertEqual(block["before"], save["privateState"][key])
                self.assertEqual(
                    block["change"], block["after"] - block["before"])
                self.assertEqual(result.cursor_change, block["change"])
                if action == "weekly":
                    expected = R.weekly_successor(block["before"], R.weekly_bound(weekly_schedule()))
                else:
                    expected = R.daily_successor(block["before"])
                self.assertEqual(block["after"], expected)

    def test_the_instant_is_reported_as_stamped_volatile_and_by_previous_value(self) -> None:
        for action, key in (("weekly", "timeStampMondayBonus"),
                            ("daily", "timestampLastBonus")):
            with self.subTest(action=action):
                save = seeded_save()
                result = R.derive_reward(save, action, weekly_schedule(),
                                         daily_schedule(), ts=1)
                block = result.payload()["instant"]
                self.assertEqual(block["key"], key)
                self.assertIs(block["stamped"], True)
                self.assertIs(block["volatile"], True)
                # The executed wall clock is never reported by value: the recorded
                # pre-request value is, and the executed one is compared by shape.
                self.assertEqual(block["value_before"], save["privateState"][key])
                self.assertEqual(result.stamp_before, block["value_before"])
                self.assertIn("NO ELIGIBILITY", block["note"])

    def test_the_volatile_fields_name_the_stamped_instant_and_the_server_time(self) -> None:
        for action in R.ACTIONS:
            with self.subTest(action=action):
                result = R.derive_reward(seeded_save(), action, weekly_schedule(),
                                         daily_schedule(), ts=1)
                stamp_path = "/%s/%s" % (R.PRIVATE_STATE_KEY, R.ACTION_STAMP_KEY[action])
                self.assertEqual(list(result.volatile_fields),
                                 [stamp_path, "server_time"])
                # The cursor is deliberately NOT volatile: it is the deterministic
                # half of the transition.
                cursor_path = "/%s/%s" % (R.PRIVATE_STATE_KEY, R.ACTION_CURSOR_KEY[action])
                self.assertNotIn(cursor_path, result.volatile_fields)

    def test_the_bounds_block_shows_bound_and_cardinality_side_by_side(self) -> None:
        result = R.derive_reward(seeded_save(), "weekly", weekly_schedule(),
                                 daily_schedule(), ts=1)
        bounds = result.payload()["bounds"]
        self.assertEqual(sorted(bounds), ["daily", "note", "weekly"])
        weekly = bounds["weekly"]
        self.assertEqual(weekly["bound"], 5)
        self.assertEqual(weekly["cardinality"], 3)
        self.assertEqual(weekly["exceeds_cardinality_by"], 2)
        self.assertEqual(weekly["schedule"], "MONDAY_BONUS_REWARDS")
        self.assertEqual(weekly["floor"], 1)
        self.assertIn("never the entry count", weekly["derived_from"])
        daily = bounds["daily"]
        self.assertEqual(daily["bound"], 5)
        self.assertEqual(daily["cardinality"], 5)
        self.assertEqual(daily["wrap_target"], 1)
        self.assertEqual(daily["exceeds_cardinality_by"], 0)
        self.assertEqual(daily["schedule"], "DAILY_GOLD_REWARDS")
        self.assertIn("REJECTED ALTERNATIVE", daily["rejected_alternative"])
        self.assertIn("NO CURSOR EVER SELECTS", bounds["note"])

    def test_the_schedule_census_and_its_entries_are_reported_undecoded(self) -> None:
        result = R.derive_reward(seeded_save(), "weekly", weekly_schedule(),
                                 daily_schedule(), ts=1)
        payload = result.payload()
        self.assertEqual(len(payload["schedules"]), 11)
        self.assertEqual(payload["schedules"][3]["name"], "MONDAY_BONUS_REWARDS")
        entries = payload["schedule_entries"]
        self.assertEqual(sorted(entries), ["DAILY_GOLD_REWARDS", "MONDAY_BONUS_REWARDS"])
        for row in entries["MONDAY_BONUS_REWARDS"]:
            with self.subTest(position=row["position"]):
                self.assertIs(row["decoded"], False)
                self.assertIsNone(row["mapped_to_resource"])
                self.assertEqual(row["position"], entries["MONDAY_BONUS_REWARDS"]
                                 .index(row))
        # The list-valued rung is the one that counts toward the derived bound.
        counted = [row for row in entries["MONDAY_BONUS_REWARDS"]
                   if row["counts_toward_weekly_bound"]]
        self.assertEqual([row["position"] for row in counted], [1])
        self.assertEqual(counted[0]["value_shape"], "list")
        # The daily schedule's committed zero is surfaced rather than filtered.
        zero_rows = [row for row in entries["DAILY_GOLD_REWARDS"]
                     if row["committed_value_is_zero"]]
        self.assertEqual([row["position"] for row in zero_rows], [4])
        self.assertEqual(zero_rows[0]["entry"], 0)

    def test_the_type_letters_are_reported_undecoded_with_the_search_result(self) -> None:
        result = R.derive_reward(seeded_save(), "daily", weekly_schedule(),
                                 daily_schedule(), ts=1)
        letters = result.payload()["type_letters"]
        self.assertEqual([row["letter"] for row in letters], ["g", "u", "c"])
        for row in letters:
            with self.subTest(letter=row["letter"]):
                self.assertIs(row["decoded"], False)
                self.assertIsNone(row["mapped_to_resource"])
                self.assertEqual(row["decoder_search_hits"], 0)
                self.assertEqual(row["decoder_searches"], 6)
                self.assertEqual(len(row["declared_elsewhere_as"]), 1)
                self.assertIn("NOT DECODED", row["note"])

    def test_both_arms_of_each_branch_are_reported_and_neither_is_reproduced(self) -> None:
        arms = R.derive_reward(seeded_save(), "weekly", weekly_schedule(),
                               daily_schedule(), ts=1).payload()["arms"]
        self.assertEqual(sorted(arms), ["daily", "note", "weekly"])
        for side, expected in (("weekly", ("long", "short")),
                               ("daily", ("granting", "resources"))):
            with self.subTest(branch=side):
                self.assertEqual(tuple(row["arm"] for row in arms[side]), expected)
                for row in arms[side]:
                    self.assertIs(row["reproduced"], False)
                    self.assertIn("command.py", row["source"])
                    self.assertIsInstance(row["grant_shaped"], bool)
        self.assertIn("REPORTED, NOT REPRODUCED", arms["note"])
        # Each recorded printed line is a real legacy print, verified in source.
        source = legacy_text("command.py")
        for printed in ("Won resources", "Rewarded resources"):
            with self.subTest(printed=printed):
                self.assertIn('"%s"' % printed, source)

    def test_the_three_divergences_are_reported_and_none_is_claimed_as_parity(self) -> None:
        result = R.derive_reward(seeded_save(), "daily", weekly_schedule(),
                                 daily_schedule(), ts=1)
        divergences = result.payload()["divergences"]
        self.assertEqual([row["id"] for row in divergences],
                         ["client_sent_item", "client_sent_next_id",
                          "client_sent_argument_count"])
        for row in divergences:
            with self.subTest(divergence=row["id"]):
                self.assertIs(row["reproduced"], False)
                self.assertIn("command.py", row["where"])
                self.assertTrue(row["consequence"].strip())
        # The sharper one is observable in the preserved source itself.
        lines = legacy_lines("command.py")
        line_number, line = next(
            (number, text) for number, text in enumerate(lines, 1)
            if "next_id = args[1] + 1" in text
        )
        self.assertEqual(line_number, 446)
        self.assertIn("next_id = args[1] + 1", line)
        self.assertIn("if next_id > 5:", "\n".join(lines))
        self.assertIn("next_id = 1", "\n".join(lines))

    def test_the_result_is_json_serialisable_through_the_shared_helper(self) -> None:
        for action in R.ACTIONS:
            result = R.derive_reward(seeded_save(), action, weekly_schedule(),
                                     daily_schedule(), ts=1)
            text = P.payload_json(result.payload())
            with self.subTest(action=action):
                self.assertIsInstance(text, str)
                round_tripped = json.loads(text)
                self.assertEqual(sorted(round_tripped), sorted(result.payload()))

    def test_derive_reward_refuses_every_structural_fault_before_it_returns(
        self,
    ) -> None:
        """``derive_reward`` performs no write at all, so every refusal it can
        raise resolves before its caller writes anything (D9).  Each case below
        is the *typed entry point*, not an inner helper, so the guarantee is
        about the delivered surface rather than about a function's internals."""
        save = seeded_save()
        # Each row is (save, action, weekly, daily, expected).  The action is a
        # **separate** argument and is named explicitly: an earlier draft packed
        # it into the save position, so the schedule was passed as the action and
        # every schedule fault below was silently answered ``unknown_action``.
        cases: List[Tuple[Any, ...]] = [
            (save, "monthly", weekly_schedule(), daily_schedule(),
             R.REASON_UNKNOWN_ACTION),
            (save, None, weekly_schedule(), daily_schedule(),
             R.REASON_UNKNOWN_ACTION),
            ("not an object", "weekly", weekly_schedule(), daily_schedule(),
             R.REASON_BAD_REQUEST),
            (save, "weekly", None, daily_schedule(), R.REASON_INVALID_SCHEDULE),
            (save, "weekly", [], daily_schedule(), R.REASON_INVALID_SCHEDULE),
            (save, "weekly", [{"no": "value"}], daily_schedule(),
             R.REASON_INVALID_SCHEDULE),
        ]
        for document, action, weekly, daily, expected in cases:
            with self.subTest(expected=expected, action=repr(action)):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.derive_reward(document, action, weekly, daily)
                self.assertEqual(caught.exception.code, expected)
        # A recorded-state fault, through the same entry point.
        for document, expected in (
            (crafted_save(cursor_value=_ABSENT, stamp_value=0), R.REASON_ABSENT_CURSOR),
            (crafted_save(cursor_value="x", stamp_value=0), R.REASON_INVALID_CURSOR),
            (crafted_save(cursor_value=0, stamp_value=_ABSENT), R.REASON_ABSENT_STAMP),
        ):
            with self.subTest(expected=expected):
                with self.assertRaises(P.EnvelopeError) as caught:
                    R.derive_reward(document, "weekly", weekly_schedule())
                self.assertEqual(caught.exception.code, expected)

    def test_derive_reward_performs_no_write_to_the_document_it_reads(self) -> None:
        """The strongest form of D9's guarantee: the derivation is a pure read,
        so the four-part proof cannot be weakened by an in-place mutation."""
        before = json.dumps(seeded_save(), sort_keys=True)
        for action in R.ACTIONS:
            with self.subTest(action=action):
                result = R.derive_reward(seeded_save(), action, weekly_schedule(),
                                         daily_schedule(), ts=1)
                self.assertIsInstance(result, R.RewardResult)
        self.assertEqual(json.dumps(seeded_save(), sort_keys=True), before)
        # And the committed corpus on disk is untouched, byte for byte.
        self.assertEqual(
            harness.SEED_SAVE.read_bytes(),
            (REPO / "tests" / "saves" / "fresh-player.json").read_bytes(),
        )

    def test_a_daily_schedule_of_none_falls_back_without_deriving_the_bound(self) -> None:
        """The daily schedule is read by no branch, so no caller can derive its
        length from a legacy helper; the recorded cardinality is used instead."""
        result = R.derive_reward(seeded_save(), "daily", weekly_schedule(), None, ts=1)
        payload = result.payload()
        self.assertEqual(payload["bounds"]["daily"]["bound"], 5)
        self.assertEqual(payload["bounds"]["daily"]["cardinality"], 5)
        self.assertEqual(payload["schedule_entries"]["DAILY_GOLD_REWARDS"], [])
        # The weekly schedule is still required, because its bound IS derived.
        with self.assertRaises(P.EnvelopeError) as caught:
            R.derive_reward(seeded_save(), "daily", None, daily_schedule(), ts=1)
        self.assertEqual(caught.exception.code, R.REASON_INVALID_SCHEDULE)


# ===================================================== the anti-invention gate --
#: The **whole** function inventory of ``rewards_envelope``, pinned by name.  This
#: is the real gate: an invented helper of any kind fails the run here, and the
#: fragment guards below are the belt that names *why* a specific one would be
#: wrong.  The list is read from the module rather than filtered, so a helper
#: added under an unremarkable name still fails.
EXPECTED_MODULE_FUNCTIONS = sorted([
    "_private_int",
    "addressing_key_for",
    "allowed_leaf_paths",
    "allowed_paths_problem",
    "build_envelope",
    "command_for_action",
    "committed_schedule_entries",
    "daily_bound",
    "daily_successor",
    "derive_reward",
    "derived_args_for",
    "document_leaves",
    "is_action",
    "leaf_diff",
    "neutral_vector",
    "read_cursor",
    "read_stamp",
    "reachable_report",
    "request_grant_keys",
    "resolve_document",
    "resolve_private_state",
    "schedule_cardinality",
    "validate_request",
    "validate_vector",
    "weekly_bound",
    "weekly_successor",
])

#: Names an invented rule would plausibly take.  Matched as **substrings** of the
#: declared name as well as by whole name, because an earlier by-name guard in
#: this repository matched only the exact name and so missed a suffixed helper
#: wearing the same disguise -- the exact defect task 3.4 names.
FORBIDDEN_HELPER_FRAGMENTS = (
    # grant shapes
    "grant",
    "award",
    "payout",
    "prize",
    "reward_for",
    "amount",
    "price",
    "cost",
    # cursor-to-rung selection
    "select",
    "rung",
    "lookup",
    "index_schedule",
    "schedule_at",
    "entry_for",
    # type-letter decoding
    "decode",
    "letter",
    "map_type",
    "type_to",
    "type_map",
    # eligibility / cooldown / window / already-claimed
    "eligible",
    "eligibility",
    "cooldown",
    "window",
    "period",
    "claimed",
    "ready_for",
    "available",
    # grant landing places
    "add_store",
    "place_row",
    "bought",
    "map_item",
)

#: The two identifiers that legitimately carry a fragment above because they name
#: the recorded **absence** or the recorded **refusal** rather than a rule:
#: ``request_grant_keys`` reports the *refused* grant-shaped keys, and nothing else
#: in the module does.
FORBIDDEN_HELPER_EXEMPT = (
    # Reports the *refused* grant-shaped keys, so it names the refusal rather
    # than a rule.  The one legitimate carrier of the "grant" fragment.
    "request_grant_keys",
)

#: Fragments that only a **non-def** line could carry, checked against the whole
#: raw source.  ``payload`` and ``payout`` are deliberately absent from
#: :data:`FORBIDDEN_HELPER_FRAGMENTS` for this reason: ``payload`` is a substring
#: of the ordinary English word in ``RewardResult.payload``, and a fragment that
#: matches a delivered name is a fragment that would have to be exempted -- which
#: is exactly how a guard stops being a guard.
RAW_SOURCE_FRAGMENTS = tuple(
    fragment for fragment in FORBIDDEN_HELPER_FRAGMENTS
    if fragment not in ("reward_for", "place_row")
)


class AntiInventionGuardTests(unittest.TestCase):
    """D7 / task 3.4: the whole inventory, plus by-name and substring guards."""

    def test_the_module_declares_exactly_the_pinned_functions(self) -> None:
        declared = module_functions()
        self.assertEqual(declared, EXPECTED_MODULE_FUNCTIONS)
        self.assertEqual(len(declared), 26)
        self.assertEqual(len(set(declared)), 26)

    def test_no_helper_name_carries_an_invented_reward_rule(self) -> None:
        for fragment in FORBIDDEN_HELPER_FRAGMENTS:
            with self.subTest(fragment=fragment):
                offenders = [
                    name for name in module_functions()
                    if fragment in name.lower()
                    and name not in FORBIDDEN_HELPER_EXEMPT
                ]
                self.assertEqual(offenders, [])

    def test_the_module_source_declares_no_such_helper_either(self) -> None:
        """A second, independent form of the same guard over the raw bytes.

        The inventory pin reads the parsed tree; this reads the text and matches
        **module-level** definitions only.  Both levels are needed: a module-level
        definition is what the inventory pins, and a nested ``def`` inside a
        function would satisfy neither -- so the nested case is checked here too,
        against the same fragment list, with ``walk`` exempt because it is the
        module's own recursive projection helper and carries no fragment.
        """
        code = module_source()
        module_level = [
            line for line in code.split("\n")
            if re.match(r"^def\s", line)
        ]
        self.assertEqual(len(module_level), 26)
        for line in module_level:
            name = re.match(r"^def\s+(\w+)", line).group(1)  # type: ignore[union-attr]
            with self.subTest(helper=name):
                for fragment in FORBIDDEN_HELPER_FRAGMENTS:
                    if fragment in name.lower() and name not in FORBIDDEN_HELPER_EXEMPT:
                        self.fail("module-level helper %r carries %r" % (name, fragment))
        # Nested definitions, with the same fragments.
        nested = re.findall(r"^\s+def\s+(\w+)", code, re.MULTILINE)
        for name in nested:
            with self.subTest(nested=name):
                if name in FORBIDDEN_HELPER_EXEMPT:
                    continue
                for fragment in FORBIDDEN_HELPER_FRAGMENTS:
                    self.assertNotIn(fragment, name.lower())
        self.assertIn("walk", nested, "the nested projection helper is gone")
        # And the text form: no ``def`` line at either level carries a fragment.
        for line in code.split("\n"):
            if not re.match(r"^\s*(?:async\s+)?def\s+(\w+)", line):
                continue
            name = re.match(r"^\s*(?:async\s+)?def\s+(\w+)", line).group(1)  # type: ignore[union-attr]
            if name in FORBIDDEN_HELPER_EXEMPT:
                continue
            for fragment in FORBIDDEN_HELPER_FRAGMENTS:
                with self.subTest(helper=name, fragment=fragment):
                    self.assertNotIn(fragment, name.lower())
        self.assertEqual(RAW_SOURCE_FRAGMENTS,
                         tuple(f for f in FORBIDDEN_HELPER_FRAGMENTS
                               if f not in ("reward_for", "place_row")))

    def test_the_substring_guard_catches_a_suffixed_disguise(self) -> None:
        """Proven here rather than trusted, because it is the defect task 3.4
        names: a by-name check alone lets this through."""
        disguised = [
            "grant_row", "grant_rows_for", "selects_rung", "decode_type_letter",
            "cooldown_remaining", "already_claimed", "add_store_entry",
            "place_row_from", "schedule_at_cursor", "award_amount",
        ]
        for name in disguised:
            with self.subTest(helper=name):
                lowered = name.lower()
                caught = any(fragment in lowered for fragment in FORBIDDEN_HELPER_FRAGMENTS)
                self.assertTrue(caught, "the substring guard missed %r" % name)
                # And it is caught by a fragment, not by an exact-name list.
                self.assertNotIn(name, FORBIDDEN_HELPER_EXEMPT)

    def test_no_absent_helper_from_the_record_is_delivered(self) -> None:
        """:data:`ABSENT_HELPERS` is the contract, checked against the module."""
        self.assertEqual(len(R.ABSENT_HELPERS), 4)
        capabilities = [str(row["capability"]) for row in R.ABSENT_HELPERS]
        self.assertEqual(capabilities, [
            "grant",
            "cursor-to-rung selection",
            "type-letter decoding",
            "eligibility, cooldown, window, or already-claimed test",
        ])
        for row in R.ABSENT_HELPERS:
            with self.subTest(capability=str(row["capability"])):
                self.assertTrue(str(row["would"]).strip())
                self.assertTrue(str(row["forbidden_because"]).strip())
        # The four recorded absences, checked by their own vocabulary.
        declared = [name.lower() for name in module_functions()]
        for banned in ("grant_row", "add_grant", "select_rung", "rung_for",
                       "decode_type", "letter_to", "is_eligible", "cooldown",
                       "window_", "already_claimed", "claimed_at"):
            with self.subTest(helper=banned):
                self.assertNotIn(banned, declared)

    def test_no_code_identifier_names_a_type_letter(self) -> None:
        """Task 5.4: the "undecoded" claim is mechanical, not prose.

        No identifier may be **exactly** a type letter, and no identifier may
        **contain** one as a whole underscore-separated token -- so neither
        ``g`` nor ``reward_g`` nor ``letter_g`` can be introduced while the suite
        passes.  Substring matching is not used, because it would fire on
        legitimate words that merely contain the letter.
        """
        identifiers = module_code_identifiers()
        letters = set(R.TYPE_LETTERS)
        for name in identifiers:
            tokens = set(filter(None, re.split(r"[^A-Za-z0-9]+", name)))
            with self.subTest(identifier=name):
                self.assertNotIn(name, letters)
                self.assertEqual(tokens & letters, set())

    def test_no_code_identifier_is_named_after_the_weekly_bound_source_or_a_rung(
        self,
    ) -> None:
        """The refusal is about the *reward* letters; this is the schedule side."""
        identifiers = module_code_identifiers()
        for token in ("rung", "prize_pool", "reward_tier", "tier", "ladder"):
            with self.subTest(token=token):
                offenders = [
                    name for name in identifiers
                    if token in name.lower().split("_")
                ]
                self.assertEqual(offenders, [])

    def test_the_module_derives_no_arithmetic_from_the_request(self) -> None:
        """No multiplication, division, or power over anything.

        ``+``, ``-`` and ``%`` are not banned and each is checked against a pinned
        purpose instead: the successors transcribe the branches' own ``+ 1`` and
        modulo, the differences report a bound against a cardinality, and ``%``
        elsewhere is string formatting.  Every one of those is a derived value
        from the **recorded state or committed content**, never from a request.
        """
        tree = ast.parse(module_source())
        banned = {ast.Mult, ast.Div, ast.FloorDiv, ast.Pow}
        offenders: List[str] = []
        for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for inner in ast.walk(function):
                if not isinstance(inner, ast.BinOp):
                    continue
                if type(inner.op) in banned:
                    if isinstance(inner.op, ast.Mult) and _is_sequence_repetition(inner):
                        continue
                    offenders.append("%s:%s" % (function.name, type(inner.op).__name__))
        # The one multiplication is the neutral vector's repetition.
        self.assertEqual(sorted(set(offenders)), [])
        # Every ``%`` is either string formatting or the weekly successor's modulo.
        modulo_outside: List[str] = []
        for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for inner in ast.walk(function):
                if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Mod):
                    if _is_modulo_of_a_string(inner):
                        continue
                    if function.name == "weekly_successor":
                        continue
                    modulo_outside.append("%s:%d" % (function.name, inner.lineno))
        self.assertEqual(sorted(modulo_outside), [])

    def test_the_module_computes_no_derived_quantity_by_another_route(self) -> None:
        """No float, exponent, or rounding helper can produce an amount."""
        banned_calls = {"pow", "sqrt", "exp", "log", "log2", "log10", "round",
                        "trunc", "hypot", "atan2", "fmod", "comb", "factorial",
                        "gcd", "lcm", "fsum", "prod"}
        tree = ast.parse(module_source())
        for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for inner in ast.walk(function):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                    with self.subTest(function=function.name, call=inner.func.id):
                        self.assertNotIn(inner.func.id, banned_calls)

    def test_the_module_reaches_no_wall_clock_other_than_the_one_default(self) -> None:
        """A second clock read would be an eligibility window in waiting."""
        tree = ast.parse(module_source())
        clock_reads = [
            (function.name, inner.lineno)
            for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            for inner in ast.walk(function)
            if isinstance(inner, ast.Attribute) and inner.attr == "time"
        ]
        self.assertEqual(len(clock_reads), 1)
        self.assertEqual(clock_reads[0][0], "build_envelope")
        # And no comparison of the stamped instant against anything.
        for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for inner in ast.walk(function):
                if isinstance(inner, ast.Compare):
                    for operand in [inner.left] + list(inner.comparators):
                        with self.subTest(function=function.name, line=inner.lineno):
                            self.assertFalse(
                                isinstance(operand, ast.Name)
                                and "stamp" in operand.id.lower()
                                and "before" not in operand.id.lower(),
                                "%s compares the stamped instant" % function.name,
                            )

    def test_the_module_opens_no_file_at_all(self) -> None:
        """Every value here is passed in, so a file read would be a hidden census
        whose figure could drift from the recorded one."""
        tree = ast.parse(module_source())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in ("open", "read_text", "read_bytes", "load",
                                    "loads", "Path", "urlopen"):
                continue
            # ``json`` is not imported here and ``Path`` is never called, so any
            # occurrence would be a new dependency on the filesystem.
            with self.subTest(call=node.func.id):
                self.fail("rewards_envelope reads from the filesystem: %s" % node.func.id)
        # ``walk`` is the module's own recursive projection helper, not an
        # ``os.walk``; it is checked by name above rather than banned here.
        for banned in ("remove", "rename", "unlink", "rmdir", "makedirs",
                       "listdir", "exists", "write_text", "write_bytes",
                       "urlopen", "system", "popen", "eval", "exec", "compile",
                       "__import__", "setattr", "delattr", "import_module"):
            with self.subTest(entry_point=banned):
                self.assertIsNone(re.search(r"\b%s\s*\(" % banned, module_source()))
        self.assertNotIn("import os", module_source())
        self.assertNotIn("import pathlib", module_source())
        self.assertNotIn("import json", module_source())

    def test_the_module_imports_only_what_the_shared_derivation_provides(self) -> None:
        """A new import could smuggle a whole rule in behind it."""
        tree = ast.parse(module_source())
        imported: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        # ``__future__`` is required by the module's own annotations and adds no
        # capability; everything else must be the standard library's typing plus
        # the one clock and the one shared derivation.
        self.assertEqual(
            sorted(imported), ["__future__", "placement_envelope", "time", "typing"]
        )

    def test_the_shared_serialization_helpers_are_not_reimplemented(self) -> None:
        """One shared derivation: every helper is the placement module's object."""
        for name in ("is_strict_int", "ENVELOPE_KEYS", "payload_json", "data_field",
                     "parse_data_field", "EnvelopeError"):
            with self.subTest(helper=name):
                self.assertTrue(hasattr(R, name))
                self.assertIs(getattr(R, name), getattr(P, name))

    def test_the_module_exports_exactly_its_public_surface(self) -> None:
        """``__all__`` is pinned in count and in content."""
        self.assertEqual(len(R.__all__), len(set(R.__all__)))
        self.assertEqual(len(R.__all__), 134)
        for name in R.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(R, name))
        # Everything public is exported, so a new public name cannot be added
        # quietly: it must appear here too.
        exported = set(R.__all__)
        for required in ("ACTIONS", "ACTION_COMMAND", "ACTION_FOR_COMMAND",
                         "ACTION_ADDRESSING_KEY", "CURSORS", "INSTANTS",
                         "CURSOR_STAMP", "VALIDATION_ORDER", "CLIENT_KEY_REFUSALS",
                         "REQUEST_KEYS", "ABSENT_HELPERS", "NO_GRANT",
                         "NO_ELIGIBILITY", "NO_CURSOR_SELECTION", "RewardResult",
                         "TYPE_LETTERS", "DECODER_SEARCHES", "SCHEDULES",
                         "SAVE_ONLY_FIELDS", "CURSOR_DISTRIBUTIONS",
                         "DIVERGENCES", "WEEKLY_ARMS", "DAILY_ARMS",
                         "FORBIDDEN_IDENTIFIER_FRAGMENTS", "RESOURCE_VECTOR_SLOTS"):
            with self.subTest(name=required):
                self.assertIn(required, exported)

    def test_the_module_declares_no_class_besides_the_typed_result(self) -> None:
        classes = sorted(
            node.name for node in ast.parse(module_source()).body
            if isinstance(node, ast.ClassDef)
        )
        self.assertEqual(classes, ["RewardResult"])

    def test_no_type_letter_is_mapped_onto_a_resource_anywhere_in_the_module(self) -> None:
        """The strongest form of D10: **no string literal in the delivered code**
        is a letter-to-resource mapping, and no expression compares one.

        Scanned over string **literals** rather than over the raw text, because a
        raw-text scan fires on this module's own recorded search patterns -- the
        six ``DECODER_SEARCHES`` regexes literally contain the sequences
        ``"g": (gold|coins)`` and are *supposed* to.  A guard that cannot tell a
        recorded pattern from a mapping would be a guard that cannot be satisfied,
        so the scan is taken over the parsed literals where the distinction exists.
        """
        resource_names = ("gold", "cash", "mana", "wood", "steel", "oil", "xp",
                          "coins", "coins_gold", "unknown")
        literals = module_code_literals()
        # 1. No literal *is* a mapping of the shape ``{"g": "gold"}``.
        for literal in literals:
            parsed = None
            try:
                parsed = json.loads(literal)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if key in R.TYPE_LETTERS and isinstance(value, str):
                        self.fail("a delivered literal maps %r onto %r" % (key, value))
        # 2. No literal *is* a letter, except the recorded vocabulary tuple itself
        #    and the recorded search labels that name one.
        letter_literals = [
            literal for literal in literals
            if isinstance(literal, str) and len(literal) == 1
            and literal in R.TYPE_LETTERS
        ]
        self.assertEqual(sorted(set(letter_literals)), ["c", "g", "u"])
        #    Each occurs only inside the vocabulary declaration or the recorded
        #    letter-named declarations -- checked by locating them.
        code = module_source()
        self.assertEqual(
            sum(1 for line in code.split("\n") if '"%s"' % "g" in line
                and "TYPE_LETTERS" in line),
            1,
        )
        # 3. No source line holds a letter key followed by a resource name -- the
        #    raw-text form, restricted to the lines that literally carry one of the
        #    six recorded search patterns, because those regexes contain the very
        #    sequence this refuses and are *supposed* to.
        #
        #    A defect found by running this: the letter alternation was never
        #    grouped, so the pattern compiled to ``[\"']g`` OR ``u`` OR
        #    ``c[\"']\s*:\s*...`` and matched a bare ``u`` on line 1 of the
        #    module.  Every alternation interpolated here is therefore wrapped in
        #    a non-capturing group, and the wrapper is asserted rather than
        #    trusted.
        recorded_pattern_lines = set()
        for number, text in enumerate(module_source().split("\n"), 1):
            if any(str(row["pattern"]) in text for row in R.DECODER_SEARCHES):
                recorded_pattern_lines.add(number)
        letters = "(?:%s)" % "|".join(R.TYPE_LETTERS)
        names = "(?:%s)" % "|".join(resource_names)
        mapping_shape = r"[\"']%s[\"']\s*:\s*[\"']?%s" % (letters, names)
        equality_shape = r"[\"']%s[\"']\s*==\s*[\"']?%s" % (letters, names)
        for shape, positive in ((mapping_shape, "\"g\": 'gold'"),
                                (equality_shape, "\"g\" == 'gold'")):
            with self.subTest(shape=shape):
                self.assertIn("(?:", shape)
                # The grouping is what makes the shape a shape: the ungrouped
                # form matches a bare letter in prose, the grouped one does not.
                self.assertIsNone(re.search(shape, "a note about u and c"))
                self.assertIsNotNone(re.search(shape, positive))
        for number, text in enumerate(module_source().split("\n"), 1):
            if number in recorded_pattern_lines:
                continue
            with self.subTest(line=number):
                self.assertIsNone(re.search(mapping_shape, text))
                self.assertIsNone(re.search(equality_shape, text))
        # The exemption skips exactly the six recorded pattern lines, so it is
        # skipping real lines rather than silently skipping nothing.
        self.assertEqual(len(recorded_pattern_lines), 6)

    def test_no_literal_pairs_a_type_letter_with_another_identifier(self) -> None:
        """No *pairing* of a type letter with a value exists, structurally.

        Two earlier drafts of this guard were both text scans and both had to be
        withdrawn after they were run.  A bare substring test fired on every
        English word containing ``g``; the quoted-letter successor form then fired
        on the module's own prose -- ``'bonusNextId'``, ``'win_daily_bonus'``, and
        the long ``REJECTED ALTERNATIVE`` notes -- because those are *strings this
        line stores*, and a note that explains why ``"g"`` is undecoded has to name
        ``"g"``.  Each fix grew an exemption list, and an exemption list longer
        than the vocabulary it guards is the recorded way a guard stops being a
        guard in this project.

        The form used here is structural: it looks for an ``ast.Constant`` holding
        a bare type letter in a position where Python would be *using* it as a
        mapping key or a comparison operand -- a dict key, a subscript, or either
        side of a ``Compare``.  Prose can never reach those positions, so no
        exemption is needed and none is granted.
        """
        paired = _letter_pairing_nodes(module_tree())
        self.assertEqual(
            paired, [],
            "a type letter is used as a key or a comparison operand",
        )
        # The detector is proven able to fire rather than trusted to be silent:
        # each pairing form is fed to it in isolation, and each must be caught.
        for label, source in (
            ("dict", "M = {'g': 'gold'}"),
            ("subscript", "M['u']"),
            ("compare", "if letter == 'c':\n    pass\n"),
        ):
            with self.subTest(form=label):
                found = _letter_pairing_nodes(ast.parse(source))
                self.assertEqual(len(found), 1)
        # And the bare letters really are present in the module, so the scan above
        # is over a populated set.  They appear in exactly **two** places: the
        # vocabulary declaration itself, and the per-rung ``"letter"`` field that
        # *reports* each committed rung's letter verbatim.  Both are pinned by
        # source line so a new occurrence cannot hide inside either.
        self.assertEqual(sorted(R.TYPE_LETTERS), ["c", "g", "u"])
        letter_nodes = sorted(
            (node.lineno, node.value)
            for node in ast.walk(module_tree())
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and node.value in R.TYPE_LETTERS
        )
        self.assertEqual(
            letter_nodes,
            [(453, "c"), (453, "g"), (453, "u"),
             (549, "g"), (557, "c"), (565, "u")],
        )
        # Both sites are a *report*: a tuple the module iterates, and a dict
        # value under a "letter" key.  Neither is a decoding of the letter, which
        # is the distinction the structural scan above draws.
        report_line = module_source().split("\n")[548]
        self.assertIn('"letter": "g"', report_line)

    def test_the_schedules_are_reported_verbatim_and_never_deduplicated(self) -> None:
        """The census is a record, so a duplicate or an omission is a defect."""
        self.assertEqual(len(R.SCHEDULE_NAMES), len(set(R.SCHEDULE_NAMES)))
        self.assertEqual(R.SCHEDULE_COUNT, 11)
        # Two committed names differ only by suffix; both are separate entries and
        # must not be collapsed.
        self.assertIn("RECRUITMENT_PRIZE", R.SCHEDULE_NAMES)
        self.assertIn("PRIZE_COLLECTIONS_CASH", R.SCHEDULE_NAMES)
        # The eleven are exactly the committed names carrying a reward, bonus, or
        # prize -- re-derived from the committed package rather than trusted.
        rows = committed_globals()
        expected = sorted(
            key for key in rows
            if re.search(r"REWARD|BONUS|PRIZE", key)
        )
        self.assertEqual(sorted(R.SCHEDULE_NAMES), expected)
        self.assertEqual(len(expected), 11)

    def test_the_bound_rejected_alternatives_are_retained_rather_than_dropped(
        self,
    ) -> None:
        """Two recorded choices are visible: D2's refusal and D4's literal."""
        self.assertIn("REJECTED ALTERNATIVE", R.CLIENT_CURSOR_REJECTED_ALTERNATIVE)
        self.assertIn("REJECTED ALTERNATIVE", R.DAILY_BOUND_REJECTED_DERIVATION)
        # And neither is empty: both name what was rejected and why.
        for note in (R.CLIENT_CURSOR_REJECTED_ALTERNATIVE,
                     R.DAILY_BOUND_REJECTED_DERIVATION):
            self.assertGreater(len(note), 200)
        # The weekly bound note is the third retained alternative, in a comment.
        self.assertIn("REJECTED ALTERNATIVE, RETAINED ON PURPOSE (design D4)",
                      module_source())


class Task53BoundaryTests(unittest.TestCase):
    """Task 5.3: the boundary to three owning capabilities, asserted mechanically.

    The line reads ``boughtUnits``, ``store``, and ``maps[0].items`` **by
    necessity** -- the four-part proof must name where a grant could have landed,
    and the fixture must report what the preserved oracle did to them.  What it
    must not do is **name an identifier after them**, which is what would make
    the boundary an orphan rather than a hand-off.
    """

    FOREIGN_FIELD_KEYS = ("boughtUnits", "store", "items")

    #: Measured, not assumed.  An earlier draft of this table routed
    #: ``boughtUnits`` to ``godot-unit-instances`` and ``items`` to
    #: ``godot-building-placement``; running the check showed neither spec names
    #: the field, and that the *same* spec names both of the first two fields in
    #: one sentence -- "the map-level record ``maps[0]["store"]`` together with the
    #: ledger ``privateState.boughtUnits``" (``godot-stored-item-placement``).  The
    #: measured owner is recorded instead of the assumed one.
    OWNER_CAPABILITIES = {
        "boughtUnits": "godot-stored-item-placement",
        "store": "godot-stored-item-placement",
    }

    #: ``maps[0]["items"]`` is the **measured orphan** of the three.  A search of
    #: every committed spec for six ways of naming it -- ``["items"]``,
    #: ``['items']``, ``maps[0].items``, ``maps/0/items``, a backticked
    #: ``items``, and "items" as a container noun -- returns exactly **one** hit,
    #: and it is ``offers-normalization`` describing the offer-pack ``items``
    #: content structure, which is a different field in a different document.
    #: So no capability owns this hand-off by name, and that is pinned here as a
    #: measurement rather than papered over with a plausible owner: when a spec
    #: does name it, this test fails and the note in ``rewards_envelope`` has to be
    #: revisited rather than quietly left standing.
    ORPHAN_FIELD_KEYS = ("items",)

    def test_the_three_foreign_keys_are_named_exactly_once_each(self) -> None:
        """Their **values** are necessary and are recorded as data, not as names."""
        self.assertEqual(R.WEEKLY_UNIT_LIST_KEY, "boughtUnits")
        self.assertEqual(R.DAILY_STORE_KEY, "store")
        self.assertEqual(R.MAP_ITEMS_KEY, "items")
        for key in self.FOREIGN_FIELD_KEYS:
            with self.subTest(key=key):
                holders = [
                    name for name, value in vars(R).items()
                    if value == key and isinstance(value, str)
                ]
                self.assertEqual(len(holders), 1, "%s is held by %r" % (key, holders))

    def test_no_delivered_identifier_is_named_after_a_foreign_field(self) -> None:
        """No identifier this line **binds** is named after a foreign field.

        Two earlier drafts of this guard were both unsatisfiable, and the reasons
        are recorded because they are the recorded defect classes:

        * Requiring the offenders list to be empty cannot hold, because the test
          above it *requires* the module to hold each foreign key as data, and a
          constant holding ``"store"`` has to say so -- ``DAILY_STORE_KEY`` and
          ``MAP_ITEMS_KEY`` necessarily contain ``store`` and ``items``.
        * Scanning every identifier the module *reads* cannot hold either:
          ``dict.items()`` is a builtin method, and the module calls it.  The
          single exact ``items`` token in the wider view is that call, not a name
          this line owns.

        So the scan is over **bound** names -- store-context assignments, ``def``
        and ``class`` names, argument names, keyword names -- which is exactly the
        set of names this line is responsible for introducing.  The disguised-name
        case is not lost: it is covered by the contract's own
        ``FORBIDDEN_IDENTIFIER_FRAGMENTS`` test immediately below, which matches
        multi-word fragments and is not defeated by a builtin method.
        """
        bound = module_bound_identifiers()
        functions = set(module_functions())
        for key, constant in (
            (R.WEEKLY_UNIT_LIST_KEY, "WEEKLY_UNIT_LIST_KEY"),
            (R.DAILY_STORE_KEY, "DAILY_STORE_KEY"),
            (R.MAP_ITEMS_KEY, "MAP_ITEMS_KEY"),
        ):
            with self.subTest(key=key):
                # A data constant, never a helper: a *function* named after a
                # foreign field would be a re-implementation, not a boundary.
                self.assertIn(constant, bound)
                self.assertNotIn(constant, functions)
        # No bound name is the foreign field itself.
        for key in self.FOREIGN_FIELD_KEYS:
            with self.subTest(key=key):
                self.assertEqual(
                    sorted(name for name in bound
                           if name.lower() == key.lower()),
                    [],
                )
        # And exactly two bound names carry a foreign field as a *substring*,
        # both of them the declared key constants.  The third constant,
        # ``WEEKLY_UNIT_LIST_KEY``, deliberately does **not** name the field it
        # holds, so the measured expectation is per key rather than derived from
        # the constant table: this is the number, not a formula that would hide
        # a change to it.
        expected_substrings = {
            "boughtUnits": [],
            "store": ["DAILY_STORE_KEY"],
            "items": ["MAP_ITEMS_KEY"],
        }
        for key in self.FOREIGN_FIELD_KEYS:
            with self.subTest(substring=key):
                self.assertEqual(
                    sorted(name for name in bound
                           if key.lower() in name.lower()),
                    expected_substrings[key],
                )
        self.assertEqual(sorted(expected_substrings),
                         sorted(self.FOREIGN_FIELD_KEYS))

    def test_the_modules_own_forbidden_identifier_fragment_list_holds_no_helper(
        self,
    ) -> None:
        """The contract ships the fragments; the suite enforces them."""
        self.assertEqual(R.FORBIDDEN_IDENTIFIER_FRAGMENTS,
                         ("bought_unit", "boughtUnits", "buy_stored", "map_add_item"))
        identifiers = module_code_identifiers()
        for fragment in R.FORBIDDEN_IDENTIFIER_FRAGMENTS:
            with self.subTest(fragment=fragment):
                offenders = [
                    name for name in identifiers if fragment.lower() in name.lower()
                ]
                self.assertEqual(offenders, [])

    def test_each_owning_capability_exists_in_the_specs_directory(self) -> None:
        """The boundary is a **hand-off**, so every owner must really exist.

        This is the recorded defect class from ``legacy-m10-death.md`` §6.2 and
        ``legacy-m10-mission-completion.md`` §9.5, which failed twice because
        prose specs describe behaviour by *role* and never by key name.  A hand-off
        to a capability that does not exist is an orphan, so the owners are looked
        up as **directories** under ``openspec/specs/`` -- and each is also
        required to actually mention the field it owns, so a directory that exists
        for an unrelated reason cannot satisfy the check.
        """
        specs = REPO / "openspec" / "specs"
        for key, capability in self.OWNER_CAPABILITIES.items():
            with self.subTest(key=key, capability=capability):
                directory = specs / capability
                self.assertTrue(directory.is_dir(), "no capability %r" % capability)
                spec_files = sorted(directory.glob("*.md"))
                self.assertTrue(spec_files, "capability %r has no spec" % capability)
                joined = "\n".join(
                    path.read_text(encoding="utf-8") for path in spec_files
                )
                self.assertIn(
                    key, joined,
                    "capability %r does not mention the field it owns" % capability,
                )

    def test_the_third_hand_off_is_measured_to_be_an_orphan_and_stays_measured(
        self,
    ) -> None:
        """``maps[0]["items"]`` has **no** owning capability, and that is a fact.

        The other two fields are named by one spec that reads them together.  The
        map's ``items`` container is named by **no** committed spec, in any of six
        ways of naming it.  The recorded failure mode for this project is a
        hand-off asserted rather than looked up, so this test looks it up and
        pins the negative result: if a spec ever does name the key, this fails and
        the claim in ``rewards_envelope`` has to be updated deliberately.
        """
        specs = REPO / "openspec" / "specs"
        # The literal shapes are **escaped** before use.  A first draft passed
        # ``["items"]`` to ``re.finditer`` unescaped, where the leading ``[``
        # opened a character class matching any of ``"items"`` -- so the search
        # matched almost every line in the tree and reported hundreds of hits
        # instead of one.  The escaping is applied here rather than in the shapes
        # themselves so the shapes stay readable as the literal text they are.
        literal_shapes = ('["items"]', "['items']", "maps[0].items",
                          "maps/0/items", "`items`")
        regex_shapes = (r"\bitems\s+(?:array|list|container|map|collection)\b",)
        hits: List[str] = []
        for path in sorted(specs.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            for shape in literal_shapes:
                for _ in re.finditer(re.escape(shape), text):
                    hits.append("%s: %s" % (path.parent.name, shape))
            for shape in regex_shapes:
                for _ in re.finditer(shape, text):
                    hits.append("%s: %s" % (path.parent.name, shape))
        # The single measured hit is the offer-pack content structure, a
        # different field in a different document -- so the orphan claim holds.
        self.assertEqual(hits, ["offers-normalization: `items`"])
        # And it is a *content* claim about offers, not about a map row: the
        # surrounding sentence is checked so the exemption cannot be satisfied
        # by an unrelated mention.
        offers = (specs / "offers-normalization" / "spec.md").read_text(
            encoding="utf-8")
        for match in re.finditer("`items`", offers):
            window = offers[max(0, match.start() - 120):match.end() + 120]
            self.assertNotIn("maps[0]", window)
        for key in self.ORPHAN_FIELD_KEYS:
            with self.subTest(key=key):
                self.assertNotIn(key, self.OWNER_CAPABILITIES)

    def test_the_line_claims_no_existing_capability_and_no_cursor_is_owned_twice(
        self,
    ) -> None:
        """Task 5.1: grep **role names as well as identifiers** across the specs.

        The two defect instances were both prose describing a role -- "the weekly
        reward", "the daily bonus" -- without naming the key, so a key-name-only
        grep missed them.  Both forms are searched here, across every committed
        spec file, for either cursor, either instant, and either command.
        """
        specs = REPO / "openspec" / "specs"
        identifiers = (
            R.WEEKLY_CURSOR_KEY, R.DAILY_CURSOR_KEY,
            R.WEEKLY_STAMP_KEY, R.DAILY_STAMP_KEY,
            R.WEEKLY_COMMAND, R.DAILY_COMMAND,
        )
        role_phrases = ("weekly reward", "daily bonus", "monday bonus",
                        "weekly_reward", "win_daily_bonus")
        files: List[pathlib.Path] = []
        for spec in sorted(specs.rglob("*.md")):
            files.append(spec)
        self.assertGreater(len(files), 50)
        hits: List[str] = []
        for path in files:
            capability = path.relative_to(specs).parts[0]
            if capability == "rewards":
                continue
            text = path.read_text(encoding="utf-8")
            for token in identifiers:
                if token in text:
                    hits.append("%s: %s" % (capability, token))
            lowered = text.lower()
            for phrase in role_phrases:
                if phrase in lowered:
                    hits.append("%s: role phrase %r" % (capability, phrase))
        self.assertEqual(
            hits, [],
            "an existing capability already claims a reward cursor, instant, "
            "or command: %s" % hits,
        )


def _is_sequence_repetition(node: ast.BinOp) -> bool:
    """True for ``[x] * n``, which builds a sequence rather than a quantity.

    The neutral vector is ``[0] * RESOURCE_VECTOR_SLOTS``: a repetition whose
    length is a committed constant and whose element is the literal zero.  It is
    not arithmetic over a request, and banning it would force the derivation to
    write eight zeros out longhand -- which would then be eight figures that
    could disagree with the declared width.
    """
    left = node.left
    if not isinstance(left, (ast.List, ast.Tuple, ast.Set)):
        return False
    if len(left.elts) != 1:
        return False
    element = left.elts[0]
    return isinstance(element, ast.Constant) and element.value in (0, "")


def _is_modulo_of_a_string(node: ast.BinOp) -> bool:
    """True for ``"a % b"``, which is string formatting rather than arithmetic."""
    return isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)


class OfflineGuardTest(unittest.TestCase):
    """"Pure derivation, no socket" is checked rather than asserted."""

    def test_the_suite_runs_under_the_socket_guard(self) -> None:
        with harness.offline():
            for action in R.ACTIONS:
                result = R.derive_reward(seeded_save(), action, weekly_schedule(),
                                         daily_schedule(), ts=1)
                self.assertTrue(result.payload())
                envelope = R.build_envelope(action, 0, ts=1)
                self.assertTrue(P.payload_json(envelope).startswith("[")
                                or P.payload_json(envelope).startswith("{"))
            self.assertTrue(R.leaf_diff(seeded_save(), seeded_save()) == [])
            self.assertEqual(R.weekly_bound(weekly_schedule()), 5)

