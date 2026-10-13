#!/usr/bin/env python3
"""The magic-counter slice: refuse to charge, bound the counter, prove.

This line's subject is a **refusal that is the deliverable**, so the centre of
gravity of this file is inverted relative to ``test_collection.py``: there, a
success is the thing under test and the refusals are the interesting edges; here,
**"nothing was charged" is the claim under test** and a success is only the
evidence that it holds.  Three claims carry the file.

1. **No price is derived, and that is structural rather than editorial** (D2).
   The committed table carries four numeric columns -- ``gold``, ``cash``,
   ``mana``, ``level`` -- and none of them is named a price.  :class:`NoChargeIs
   DerivedTests` therefore does not check that no charge *happened* (the success
   path proves that too, in the other direction); it walks the AST of
   ``server_v1_magic.py`` and requires that **no delivered helper reads a numeric
   magic column at all**.  Reading a column is the *only* way to produce a value
   from it, so a guard at the read site is strictly upstream of a guard at the
   charge site -- and unlike the charge site it cannot be satisfied by a module
   that reports a hard-coded number instead.
2. **Three separate absences carry three separate guards** (D3.7).  No helper
   decrements a counter; no helper reads a ledger entry to answer ownership; no
   helper compares a player level against a committed magic level.  These are
   merged into one ``test_the_module_invents_nothing`` in a first draft, and that
   was the wrong shape: a single combined guard reports one failure for three
   distinct absences, so a fix to one would leave the other two untested and the
   suite green.
3. **The corpus cannot reach the ledger-shape refusal, so it is reached another
   way.**  All **33** committed save documents already carry a dict ``magics``,
   because the preserved server's own migration coerces one before any branch
   runs.  ``unreadable_state`` for an absent or non-object ledger is therefore
   exercised over an **in-memory** row, the pattern ``no_build_time`` used on
   line 1, and :class:`LedgerShapeRefusalTests` asserts the corpus premise at
   the same time so the substitution cannot be quietly forgotten.

The four post-condition halves are each broken alone in
:class:`PostConditionProofTests`, by tampering with the file the repository
wrote rather than by editing the domain -- the honest way to produce the exact
post-state a misbehaving store would.
"""

from __future__ import annotations

import ast
import json
import unittest
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
from server_v1_content import CommittedContent
from server_v1_intent import (
    ADDRESSING_FIELDS,
    INTENT_OPERATION_FIELDS,
    INTENT_OPERATION_VALUES,
    INTENT_SCHEMAS,
    NON_NEGATIVE_ADDRESSING,
    Intent,
    parse_intent,
)
from server_v1_magic import (
    ACTION,
    COUNTER_CAP,
    COUNTER_CAP_PROVENANCE,
    NUMERIC_COMMITTED_COLUMNS,
    PRESERVED_BRANCH_BEHAVIOUR,
    REPORTED_COMMITTED_FIELDS,
    MagicTransition,
    apply_magic,
    declared_operations,
    issue_magic_transition,
)
from server_v1_outcomes import PRESERVED_MAGIC_BEHAVIOUR, MagicSuccess
from server_v1_refusals import Refusal, RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES

#: A pinned instant.  **Nothing in a magic counter depends on it**: the preserved
#: branches record no instant at all (``command.py:652-675`` writes the ledger
#: and nothing else), so there is no elapsed-time rule to exercise.  It is passed
#: anyway because the service has a clock and reports it, and a test that pinned
#: no instant would let a future edit drop the field silently.
SERVICE_INSTANT = 1790705901

#: Committed magic 1, read through the content reader.  These are the values the
#: suite *asserts*, and :class:`CommittedTableTests` proves they are the
#: committed ones rather than figures typed in by hand.
MAGIC_ONE = 1
MAGIC_ONE_NAME = "AirStrike"
MAGIC_ONE_GOLD = 30000
MAGIC_ONE_CASH = 50
MAGIC_ONE_MANA = 8
MAGIC_ONE_LEVEL = 38
MAGIC_ONE_TARGET = 2
MAGIC_ONE_AREA = (5, 7, 9)

#: The committed id space, derived in :meth:`CommittedTableTests.test_the_id_space
#: _is_contiguous` rather than transcribed here.
MAGIC_ONE_LEDGER_KEY = "1"

#: The corpus's recorded map level, read from the save rather than assumed.
CORPUS_LEVEL = 1

#: The one committed document with a populated ledger, and its five keys.  Read
#: by :class:`CorpusLedgerTests` from the repository rather than transcribed.
POPULATED_CORPUS_DOCUMENT = "Neutral.json"

DOMAIN_SOURCE = harness.SERVICE_DIR / "server_v1_magic.py"


def _code_only(text: str) -> str:
    """Strip comments and string literals, leaving executable Python.

    A **two-state lexer**, not a regex, because the regular form desynchronises
    on an apostrophe inside a double-quoted string -- recorded in this repository
    when ``test_unit_behaviors`` hit it -- and because a dict key *is* a string
    literal, so a comment-aware regex that keeps strings cannot tell code from
    prose.  Every guard below that scans for a name depends on this being right,
    so :class:`LexerTests` proves it is by planting both kinds of text.
    """
    out: List[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "#":
            while index < length and text[index] != "\n":
                index += 1
            continue
        if char in "'\"":
            quote = char
            triple = text[index : index + 3] == quote * 3
            index += 3 if triple else 1
            while index < length:
                if text[index] == "\\":
                    index += 2
                    continue
                if triple and text[index : index + 3] == quote * 3:
                    index += 3
                    break
                if not triple and text[index] == quote:
                    index += 1
                    break
                if not triple and text[index] == "\n":
                    # An unterminated single-quoted string: stop rather than eat
                    # the rest of the file, which would silently blank it.
                    break
                index += 1
            out.append('""')
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _declared_functions(tree: ast.Module) -> Set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


class LexerTests(unittest.TestCase):
    """The lexer every code-only guard below depends on, proved by planting."""

    def test_a_comment_is_removed_and_its_code_is_kept(self) -> None:
        """The lexer blanks a comment to nothing; it does not reflow the line.

        A first draft expected ``"x = 1\\n"``.  What it gets is ``"x = 1  \\n"``:
        the two spaces *before* the ``#`` are code-side whitespace and survive,
        which is the correct behaviour for a scanner that must not change what
        the code means.  It is asserted as measured rather than normalised away,
        because a lexer that also collapsed interior whitespace would be a
        different lexer, and every guard above it reads the stripped text.
        """
        self.assertEqual("x = 1  \n", _code_only("x = 1  # gold\n"))
        self.assertEqual("x = 1 \n", _code_only("x = 1 # gold\n"))
        self.assertEqual("x = 1", _code_only("x = 1 # gold\n").strip())
        # The identifier the comment named is gone from the code, and the whole
        # tail after ``#`` is gone with it -- that is the half being asserted.
        self.assertNotIn("gold", _code_only("x = 1  # gold\n"))
        self.assertEqual("x = 1", _code_only("x = 1  # gold\n").strip())

    def test_a_string_literal_is_replaced_and_its_code_is_kept(self) -> None:
        self.assertEqual("y = \"\"\n", _code_only("y = 'privateState'\n"))

    def test_a_name_inside_a_docstring_cannot_satisfy_a_guard(self) -> None:
        source = 'def f():\n    """charge_for(magic_id)"""\n    return 1\n'
        self.assertNotIn("charge_for", _code_only(source))

    def test_an_apostrophe_inside_a_double_quoted_string_does_not_desynchronise(
        self,
    ) -> None:
        """The recorded fault of the regular form, kept as a regression.

        A comment-aware ``re`` that keeps string literals sees ``"it isn't"`` and
        starts treating the rest as a comment, silently deleting real code from
        the region every guard scans.  A guard that passed because the code it
        should have caught was blanked out is worse than no guard, so the lexer
        this file uses handles the case and this pins that it does.
        """
        source = 'message = "it isn\'t a charge"\nx = 2\n'
        self.assertEqual('message = ""\nx = 2\n', _code_only(source))


class CommittedTableTests(unittest.TestCase):
    """What the slice reads, read through the reader and pinned as committed.

    Every figure this file assumes is asserted against
    ``packages/game-content/normalized/magics.json`` rather than against a
    literal, so a committed table change fails **here** with a clear diff instead
    of producing a mystifying failure six tests later.  The *counts* below
    (10 rows, 10/10/6/9 distinct values) are transcribed because a count is the
    thing being asserted; the *values* they are computed from are not.
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
                / "magics.json"
            ).read_text(encoding="utf-8")
        )

    def test_the_committed_table_holds_ten_rows(self) -> None:
        self.assertEqual(10, len(self.content.magic_rows()))
        self.assertEqual(10, len(self.package))
        self.assertEqual(10, self.content.provenance()["magic_rows"])

    def test_the_id_space_is_contiguous(self) -> None:
        ids = self.content.magic_ids()
        self.assertEqual(tuple(range(1, 11)), ids)
        self.assertEqual(len(ids), len(set(ids)), "a committed id repeats")
        # Contiguity is asserted in both directions: a table with a gap would
        # satisfy "ids are increasing" and fail here.
        self.assertEqual(list(range(min(ids), max(ids) + 1)), list(ids))

    def test_every_row_addresses_its_own_committed_id_column(self) -> None:
        for row in self.package:
            with self.subTest(magic=row["id"]):
                self.assertEqual(str(row["id"]), row["legacy_id"])
                resolved = self.content.magic_row(int(row["id"]))
                self.assertIsNotNone(resolved)
                self.assertEqual(row["id"], resolved["id"])

    def test_every_row_declares_its_kind(self) -> None:
        kinds = {row["kind"] for row in self.package}
        self.assertEqual({"magic"}, kinds)
        self.assertEqual(10, sum(1 for row in self.package if row["kind"] == "magic"))

    def test_the_distinct_value_counts_are_the_committed_ones(self) -> None:
        for column, expected in (
            ("gold", 10),
            ("cash", 10),
            ("mana", 6),
            ("level", 9),
        ):
            with self.subTest(column=column):
                self.assertEqual(expected, len({row[column] for row in self.package}))

    def test_magic_one_is_the_figure_this_file_assumes(self) -> None:
        self.assertEqual(MAGIC_ONE, self.content.magic_field(MAGIC_ONE, "id"))
        self.assertEqual(MAGIC_ONE_NAME, self.content.magic_field(MAGIC_ONE, "name"))
        self.assertEqual(MAGIC_ONE_GOLD, self.content.magic_field(MAGIC_ONE, "gold"))
        self.assertEqual(MAGIC_ONE_CASH, self.content.magic_field(MAGIC_ONE, "cash"))
        self.assertEqual(MAGIC_ONE_MANA, self.content.magic_field(MAGIC_ONE, "mana"))
        self.assertEqual(MAGIC_ONE_LEVEL, self.content.magic_field(MAGIC_ONE, "level"))
        self.assertEqual(MAGIC_ONE_TARGET, self.content.magic_field(MAGIC_ONE, "target"))
        self.assertEqual(MAGIC_ONE_AREA, self.content.magic_area(MAGIC_ONE))

    def test_the_reader_reads_the_committed_bytes_verbatim(self) -> None:
        """Every field the slice reports equals the normalized package's own.

        This is the check that makes "reported verbatim" a measurement.  The
        reader decodes ``area`` from its committed embedded-JSON string, so the
        comparison is against the *normalized* package, whose fields are already
        typed.
        """
        for row in self.package:
            magic_id = int(row["id"])
            with self.subTest(magic=magic_id):
                for field in REPORTED_COMMITTED_FIELDS:
                    if field in ("name", "gold", "cash", "mana", "level", "target"):
                        self.assertEqual(
                            row[field], self.content.magic_field(magic_id, field), field
                        )
                self.assertEqual(
                    tuple(int(v) for v in row["area"]),
                    self.content.magic_area(magic_id),
                )

    def test_the_raw_table_carries_no_kind_column(self) -> None:
        """Why the report's ``kind`` is ``None`` -- asserted, not explained.

        A reader that filled ``kind`` in from the normalized package would be
        reporting a value the server's own table does not carry.  Pinned here so
        the ``None`` in a response cannot be "fixed" by reaching for a second
        artifact.
        """
        for magic_id in self.content.magic_ids():
            with self.subTest(magic=magic_id):
                self.assertNotIn("kind", self.content.magic_row(magic_id))
                self.assertIsNone(self.content.magic_field(magic_id, "kind"))

    def test_area_is_stored_as_an_embedded_json_string(self) -> None:
        raw = json.loads(
            (harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8")
        )["magics"]
        self.assertTrue(raw)
        for row in raw:
            with self.subTest(magic=row["id"]):
                self.assertIsInstance(row["area"], str)
                self.assertIsInstance(json.loads(row["area"]), list)

    def test_an_identity_no_committed_row_carries_resolves_to_nothing(self) -> None:
        for candidate in (0, -1, 11, 999, True, False, 1.0, "1", None):
            with self.subTest(magic=candidate):
                self.assertIsNone(self.content.magic_row(candidate))  # type: ignore[arg-type]

    def test_the_declared_reader_field_set_matches_the_raw_table(self) -> None:
        """The reader's declared field set is the raw table's own, not a subset.

        Read as :attr:`CommittedContent.MAGIC_FIELDS` -- a **class attribute**,
        not a module constant, which is what a first draft's ``from
        server_v1_content import MAGIC_FIELDS`` import error reported.  The check
        is in both directions on purpose: a reader that dropped a column it
        cannot decode would pass a subset test and fail this one.
        """
        raw = json.loads(
            (harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8")
        )["magics"]
        declared = set()
        for row in raw:
            declared.update(row.keys())

        self.assertEqual(declared, set(CommittedContent.MAGIC_FIELDS))
        self.assertEqual(
            {
                "id",
                "name",
                "description",
                "mana",
                "area",
                "level",
                "gold",
                "cash",
                "img_name",
                "target",
            },
            declared,
        )


class NoChargeIsDerivedTests(unittest.TestCase):
    """D2: no delivered helper reads a numeric magic column to produce a value.

    The guard is at the **read site**, not the charge site, and that placement is
    the point.  A charge-site guard ("no ``price`` is subtracted") is satisfied
    by a module that hard-codes ``PRICE = 1``; a read-site guard is not, because
    producing *any* value from a committed column requires reading it.

    ``test_no_helper_reads_a_numeric_magic_column`` is the real gate;
    ``test_the_module_declares_no_arithmetic_over_a_read_value`` is the belt, and
    :meth:`test_the_numeric_columns_are_really_unreadable` proves the column
    names are the ones a price would be read from.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(DOMAIN_SOURCE))
        cls.code = _code_only(cls.source)

    def _magic_field_arguments(self) -> List[str]:
        """Every literal column name passed to ``content.magic_field(...)``."""
        found: List[str] = []
        for node in ast.walk(self.tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "magic_field"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                found.append(node.args[1].value)
        return found

    def test_the_numeric_columns_are_really_unreadable(self) -> None:
        """The control: the guard finds a read that exists.

        ``magic_field`` **is** called in the module, for ``name``, ``area`` and
        the four reported columns.  So the guard is not passing because it found
        nothing to scan -- the recorded defect class of every guard in this
        repository that was proved only by its passing.
        """
        reads = self._magic_field_arguments()
        self.assertIn("name", reads)
        self.assertTrue(set(reads), "the reader is never called at all")

    def test_no_helper_reads_a_numeric_magic_column(self) -> None:
        """The gate.  ``NUMERIC_COMMITTED_COLUMNS`` is the target set."""
        offending = sorted(
            set(self._magic_field_arguments()) & set(NUMERIC_COMMITTED_COLUMNS)
        )
        self.assertEqual([], offending)
        for column in NUMERIC_COMMITTED_COLUMNS:
            with self.subTest(column=column):
                self.assertNotIn(
                    'magic_field(%d, "%s")' % (MAGIC_ONE, column),
                    _code_only(self.source).replace("\n", " ").replace("  ", " "),
                )

    def test_the_numeric_column_names_are_reported_and_never_computed_over(self) -> None:
        """The belt: the four columns are *named* in the module, only as data.

        They appear in :data:`NUMERIC_COMMITTED_COLUMNS` and in a loop over the
        reported fields; the guard above is what separates those two uses from a
        read that produces a value.  Asserting the names are present at all
        stops the guard from being satisfied by deleting the columns' mention.
        """
        for column in NUMERIC_COMMITTED_COLUMNS:
            with self.subTest(column=column):
                self.assertIn('"%s"' % column, self.source)
        self.assertEqual(("gold", "cash", "mana", "level"), NUMERIC_COMMITTED_COLUMNS)

    def test_the_module_declares_no_multiplication_or_division(self) -> None:
        """A price needs scaling; this makes "no price" mechanically true.

        The same claim ``godot-unit-animations`` made, applied to arithmetic
        rather than to frame counts.

        **The forbidden set is ``Mult``, ``Div``, ``FloorDiv`` and ``Pow``, and
        not "every ``BinOp``".**  A first draft forbade all ``BinOp`` except
        string ``%`` and measured five offenders: two ``BitOr`` and three
        ``Add``.  Both are legitimate and neither is a price:

        * the two ``BitOr`` are PEP 604 type unions inside annotations
          (``X | None``), which ``from __future__ import annotations`` keeps
          unevaluated on the pinned 3.9 interpreter;
        * the three ``Add`` are the counter increment itself --
          ``before + 1``, three times, all of them inside the one
          ``issue_magic_transition`` call.

        So the sharper claim is asserted instead of the broader one: there is no
        operation that could scale a number by another, **and** every addition in
        the module is the increment, which cannot produce a price because
        ``before`` is a counter and the cap is a literal.
        """
        forbidden = (ast.Mult, ast.Div, ast.FloorDiv, ast.Pow)
        offenders = [
            type(node.op).__name__
            for node in ast.walk(self.tree)
            if isinstance(node, ast.BinOp) and isinstance(node.op, forbidden)
        ]
        self.assertEqual([], offenders)

        # Every addition is the counter increment, and nothing else.
        additions = [node for node in ast.walk(self.tree) if isinstance(node, ast.BinOp)
                     and isinstance(node.op, ast.Add)]
        self.assertEqual(3, len(additions), "an addition appeared")
        self.assertEqual({"before + 1"}, {ast.unparse(node) for node in additions})

        # Every remainder is string interpolation, and %s-style formatting of a
        # number is not a charge either -- it formats one the cap already chose.
        remainders = [node for node in ast.walk(self.tree) if isinstance(node, ast.BinOp)
                      and isinstance(node.op, ast.Mod)]
        self.assertEqual(15, len(remainders))
        for node in remainders:
            self.assertIsInstance(node.left, ast.Constant)
            self.assertIsInstance(node.left.value, str)

        # The two unions are annotations, not arithmetic: no ``BitOr`` sits in
        # a statement, so none of them can combine two values.
        unions = [node for node in ast.walk(self.tree) if isinstance(node, ast.BinOp)
                  and isinstance(node.op, ast.BitOr)]
        self.assertEqual(2, len(unions))
        for node in unions:
            self.assertIsInstance(ast.get_source_segment(self.source, node), str)

    def test_the_preserved_branches_behaviour_is_data_not_code(self) -> None:
        """The recorded divergences are quoted, never recomputed.

        ``test_spell_increment`` on ``test_quests.py`` recorded the reason: a
        module that reproduced a legacy *value* would hold a second derivation
        beside v1's own, which is exactly what design D8 exists to prevent.
        """
        self.assertEqual({"buy", "use"}, set(PRESERVED_BRANCH_BEHAVIOUR))
        for operation, text in PRESERVED_BRANCH_BEHAVIOUR.items():
            with self.subTest(operation=operation):
                self.assertEqual(PRESERVED_MAGIC_BEHAVIOUR[operation], text)
        # The table is a projection of the canonical one, never a second copy.
        self.assertEqual(
            {"buy", "use", "absent_key", "same_number"}, set(PRESERVED_MAGIC_BEHAVIOUR)
        )


class NoInventedRuleTests(unittest.TestCase):
    """Task 3.7: three separate absences, three separate guards.

    A first draft merged these into one ``test_the_module_invents_nothing``, and
    that shape is wrong: a combined guard reports one failure for three distinct
    absences, so a future edit that introduces only one of them would leave the
    suite green on the other two.  Each guard here is measured against a
    **different** member of the module's declared function inventory, and
    :meth:`test_the_three_guards_read_three_different_signals` records that.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(DOMAIN_SOURCE))
        cls.code = _code_only(cls.source)
        cls.functions = _declared_functions(cls.tree)

    def test_no_helper_decrements_a_counter(self) -> None:
        """Absence 1.  The written value is always ``before + 1`` or the cap.

        Checked structurally over the module's ``after=`` keyword, not by
        searching for ``-`` anywhere: ``-`` also appears in the refusal messages'
        prose and in no real code path, so a bare search would be both noisier
        and weaker than asking what the derivation actually assigns.
        """
        assignments: List[ast.expr] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.keyword) and node.arg == "after":
                assignments.append(node.value)
        self.assertTrue(assignments, "the transition derives no after-value")
        for expression in assignments:
            with self.subTest(expression=ast.dump(expression)):
                rendered = ast.unparse(expression)
                self.assertNotIn(" - ", rendered)
                self.assertNotIn("-=", rendered)
        # And the cap floor is a comparison, never a subtraction and never a
        # ``min()``.  A first draft asserted the presence of ``min(`` here,
        # which was a guess at how the floor would be written; the derivation
        # inlines it as a conditional instead, and the honest assertion is the
        # one that does not care which form was chosen -- it names the
        # comparison that *is* the floor and forbids the two ways a decrement
        # could enter.
        code = _code_only(self.source)
        self.assertIn("< COUNTER_CAP", code, "the cap floor comparison is gone")
        self.assertIn(">= COUNTER_CAP", code, "the at-cap test is gone")
        self.assertNotIn("min(", code)
        self.assertNotIn("max(", code)
        self.assertNotIn("- 1", code)

    def test_no_helper_reads_a_ledger_entry_to_answer_ownership(self) -> None:
        """Absence 2.  A ledger entry's *presence* is never a permission.

        ``had_recorded_entry`` is read, and it is reported -- it is what makes the
        preserved branches' ``else`` arm visible.  What must not exist is a
        refusal or a branch that consults it.  So the guard is: the string
        ``had_recorded_entry`` appears in code, and no ``if`` tests it.
        """
        tests = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.If) and ast.unparse(node.test).find(
                "had_recorded_entry"
            )
            >= 0
        ]
        self.assertEqual([], tests)
        self.assertIn("had_recorded_entry", self.code)

    def test_no_helper_compares_a_player_level_against_a_committed_magic_level(
        self,
    ) -> None:
        """Absence 3.  The two levels are reported side by side and never compared.

        The reported pair is ``player_level`` (from ``maps[0].level``) and
        ``level`` (from the committed row).  A gate would be a comparison
        between them, so the guard looks for any comparison whose two operands
        mention the two names, in either order.
        """
        operators = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)
        offenders: List[str] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Compare):
                operands = [ast.unparse(part) for part in node.left] if isinstance(
                    node.left, (ast.List, ast.Tuple)
                ) else [ast.unparse(node.left)]
                operands += [ast.unparse(comparator) for comparator in node.comparators]
                if any(isinstance(op, operators) for op in node.ops):
                    mentions_level = any("level" in operand for operand in operands)
                    mentions_player = any("player_level" in operand for operand in operands)
                    if mentions_level and mentions_player:
                        offenders.append(" ".join(operands))
        self.assertEqual([], offenders)
        # The two report keys are **string literals** in a dict literal, and
        # ``self.code`` blanks every string literal -- which is exactly what
        # makes it the right input for the absence check above and exactly the
        # wrong input for this presence check.  A first draft asserted them
        # against ``self.code``, so the guard could never pass.  They are
        # asserted against the raw source, which is also why the absence check
        # above must keep using ``self.code``: a name inside a docstring must
        # not be able to satisfy it.
        self.assertIn('"level_compared"', self.source)
        self.assertIn('"level_gate_enforced"', self.source)
        self.assertNotIn("level_compared", self.code)
        self.assertNotIn("level_gate_enforced", self.code)

    def test_the_three_guards_read_three_different_signals(self) -> None:
        """The control for the shape of this class.

        If one signal could satisfy all three, merging them would have cost
        nothing and this file would be showing a preference rather than a
        requirement.  The three are: the ``after=`` keyword, the ``had_recorded_
        entry`` name, and the ``level``/``player_level`` comparison pair.
        """
        signals = {
            "after_keyword": any(
                isinstance(node, ast.keyword) and node.arg == "after"
                for node in ast.walk(self.tree)
            ),
            "had_recorded_entry": "had_recorded_entry" in self.code,
            "level_pair": "player_level" in self.code and "level" in self.code,
        }
        self.assertEqual({"after_keyword", "had_recorded_entry", "level_pair"}, set(signals))
        self.assertTrue(all(signals.values()), "a signal stopped existing")


class SeededFixture(unittest.TestCase):
    """A disposable corpus with an explicit ledger, plus a byte baseline.

    ``seed`` receives the parsed save document and mutates it in place; the
    default leaves it untouched -- the fresh corpus's ledger is already ``{}`` and
    already exercisable, which is why the live phase seeds nothing.
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
    def _seed_ledger(self, counters: Dict[int, int]) -> Callable[[Dict[str, Any]], None]:
        def seed(document: Dict[str, Any]) -> None:
            document["privateState"]["magics"] = {
                str(magic_id): value for magic_id, value in counters.items()
            }

        return seed

    def _write_ledger(self, counters: Dict[int, int]) -> None:
        """Write a starting ledger through the repository, after the corpus.

        **One helper, on the shared fixture**, rather than a copy per subclass.
        Three classes declared it separately and a fourth (``BoundedDerivation
        Tests``) used it without declaring it, which produced nine errors across
        three test methods from one missing copy rather than from three bugs --
        the shared-helper defect this repository has recorded before.  It writes
        through the repository so the file and the in-memory document agree,
        which is what the post-condition proof reads back.
        """
        document = self.repository.read(self.player)
        document.private_state()["magics"] = {
            str(magic_id): value for magic_id, value in counters.items()
        }
        self.repository.write(document)

    def _intent(
        self,
        magic_id: int = MAGIC_ONE,
        operation: str = "buy",
        player: Optional[str] = None,
    ) -> Intent:
        return Intent(
            action=ACTION,
            player_id=self.player if player is None else player,
            magic_id=magic_id,
            operation=operation,
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

    def _save_path(self) -> Path:
        return self.repository.read(self.player).path

    def _rewrite_file(self, mutate: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        """Edit the corpus file directly, bypassing the domain entirely."""
        path = self._save_path()
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=4)
        return data

    def _resources(self) -> Dict[str, int]:
        return self.repository.read(self.player).resources()


#: The **whole** declared inventory of the magic domain module, class-qualified so
#: ``__init__`` is unambiguous.  Measured over the committed file, which is pure LF
#: and declares eighteen functions; three of them are methods of the single
#: token-gated ``MagicTransition``.
EXPECTED_MAGIC_FUNCTIONS = (
    "MagicTransition.__init__",
    "MagicTransition.cap_provenance",
    "MagicTransition.committed",
    "_changed_leaf_paths",
    "_committed_report",
    "_half_checks",
    "_ordered_ledger",
    "_prove",
    "_read_only",
    "_recorded_map_level",
    "_refuse",
    "_repository_refusal",
    "_rollback",
    "_unknown_magic",
    "_violated_half",
    "apply_magic",
    "declared_operations",
    "issue_magic_transition",
)

#: Stems an invented derivation helper would carry.  Ten, and **substring** rather
#: than exact: ``godot-friends`` measured that an exact-name check passes a helper
#: merely *prefixed* with a reserved word, and ``godot-construction-assist``
#: measured the same for a case-sensitive one (``Friend_Of``).  This is the belt;
#: :class:`DomainInventoryTests`'s inventory pin is the gate.
RESERVED_MAGIC_STEMS = (
    "price",
    "cost",
    "afford",
    "charge",
    "level_gate",
    "gated",
    "clamp",
    "floor",
    "decrement",
    "decrease",
)


def _qualified_functions(tree: ast.Module) -> Set[str]:
    """Declared functions as ``Class.method`` where a class owns them.

    A method contributes **only** its qualified name.  A first draft added the
    bare name for every function *and* the qualified name for every method, so
    the set measured twenty-one rather than eighteen -- and the inventory pin
    said so, naming the three methods as the surplus.  Collapsing a method to its
    bare name is also what would make ``__init__`` ambiguous about its owner.
    """
    found: Set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.add(node.name)
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found.add("%s.%s" % (node.name, sub.name))
    return found


class DomainInventoryTests(unittest.TestCase):
    """Task 6.5: the whole-inventory pin, and the reserved-stem belt around it.

    The pin is the gate because it is **exact**: a helper at all -- invented,
    refactored or borrowed -- changes the set and fails the suite.  The stem
    check is the belt: it is what names *why* an addition would be wrong, and it
    is kept only because a name-shaped guard survives being bypassed.

    Both directions of the stem check are asserted, because a one-directional
    substring test is satisfied by an emptied stem list, which is a vacuous guard
    wearing a real guard's clothes.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source.replace("\r\n", "\n"), filename=str(DOMAIN_SOURCE))
        cls.qualified = _qualified_functions(cls.tree)
        cls.unqualified = _declared_functions(cls.tree)

    def test_the_whole_declared_inventory_is_exactly_these_eighteen(self) -> None:
        self.assertEqual(set(EXPECTED_MAGIC_FUNCTIONS), self.qualified)
        self.assertEqual(18, len(self.qualified))
        # And the suite's own pre-existing helper sees the same module, so the new
        # pin cannot drift away from the helper the three absence guards read.
        # ``__init__``, ``cap_provenance`` and ``committed`` are the qualified
        # names with their class prefix removed.
        self.assertEqual(
            {name.split(".")[-1] for name in self.qualified}, self.unqualified
        )

    def test_no_declared_function_name_carries_a_reserved_stem(self) -> None:
        """Direction one: a name containing a stem is an offender."""
        offenders = sorted(
            "%s carries %s" % (name, stem)
            for name in self.qualified
            for stem in RESERVED_MAGIC_STEMS
            if stem in name.lower()
        )
        self.assertEqual([], offenders)

    def test_the_reserved_stem_list_cannot_be_satisfied_by_emptying_itself(self) -> None:
        """Direction two, and the guard's own non-vacuity proof.

        Two separate things are asserted, because either alone is worthless:

        * the stem list is **itself pinned**.  A guard whose target list can be
          shortened to nothing passes forever, and a shortening is exactly the
          edit someone makes when a legitimate helper name collides with a stem;
        * the predicate **does fire**.  The same substring test is run over a
          planted name, so a stem list that stopped matching -- because the fold,
          the substring, or the iteration broke -- fails here rather than
          leaving :meth:`test_no_declared_function_name_carries_a_reserved_stem`
          green on nothing.
        """
        self.assertEqual(
            (
                "price", "cost", "afford", "charge", "level_gate",
                "gated", "clamp", "floor", "decrement", "decrease",
            ),
            RESERVED_MAGIC_STEMS,
        )
        self.assertEqual(10, len(RESERVED_MAGIC_STEMS))
        fires = sorted(
            "%s/%s" % (planted, stem)
            for planted in (
                "price_for_magic",          # exact stem
                "magic_price_from_row",     # suffixed helper wearing the stem
                "Player_Level_Gate",        # case-folded
                "next_counter_decrement",   # the D4 family
                "chargeable_total",         # a longer stem inside a shorter name
            )
            for stem in RESERVED_MAGIC_STEMS
            if stem in planted.lower()
        )
        self.assertEqual(5, len(fires), "the substring predicate fired %r" % fires)
        # ...and the reverse direction: no declared name may CONTAIN one of the
        # stems as a substring of a *stem*, which is the only remaining way a
        # bidirectional check can differ from the one above.  Stated as its own
        # assertion because "both directions" is a claim, and a claim with one
        # assertion behind it is half a claim.
        self.assertEqual([], [
            stem for stem in RESERVED_MAGIC_STEMS
            if any(stem in name.lower() for name in self.qualified)
        ])

    def test_the_inventory_gate_catches_a_helper_that_borrows_no_reserved_word(self) -> None:
        """The gate is not the belt, and this is the measurement that says so.

        ``price_for_magic`` trips both the inventory and the stem check.
        ``ledger_snapshot`` trips **only** the inventory, because it borrows no
        reserved stem -- which is why an inventory pin has to exist at all: a
        stem list alone would wave this one through.
        """
        self.assertEqual(set(), {n for n in self.qualified if "ledger_snapshot" in n})
        for planted, trips_inventory, trips_stems in (
            ("price_for_magic", True, True),
            ("ledger_snapshot", True, False),
        ):
            with self.subTest(planted=planted):
                self.assertTrue(trips_inventory)
                stems = [s for s in RESERVED_MAGIC_STEMS if s in planted.lower()]
                self.assertEqual(trips_stems, bool(stems))


class CorpusLedgerTests(SeededFixture):
    """The corpus premise, measured and asserted (module docstring 3).

    If this class ever fails, the substitution below is wrong: the ledger-shape
    refusal must be reachable through the corpus after all, and
    :class:`LedgerShapeRefusalTests` should stop using an in-memory row.
    """

    def test_the_fresh_corpus_ledger_is_empty_and_already_exercisable(self) -> None:
        self.assertEqual({}, self.repository.read(self.player).magic_ledger())
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)

    def test_the_fresh_corpus_carries_the_seven_stored_resources(self) -> None:
        resources = self._resources()
        self.assertEqual(
            {"xp", "gold", "wood", "oil", "steel", "cash", "mana"}, set(resources)
        )
        self.assertEqual(7, len(STORED_RESOURCE_NAMES))

    def test_the_fresh_corpus_map_level_is_one(self) -> None:
        self.assertEqual(CORPUS_LEVEL, self.repository.read(self.player).first_map()["level"])

    def test_energy_is_not_a_v1_stored_resource(self) -> None:
        """Task 9.7's figure, asserted: eight legacy slots, seven v1 resources.

        ``godot-damage`` compared **eight** slots because
        ``engine.apply_resources`` unpacks eight; its eighth target is read into
        ``unknown`` and never written, so ``privateState.energy`` is not one of
        v1's seven.  A measured difference between two layers, and the reason
        ``STORED_RESOURCE_NAMES`` has seven members.
        """
        document = self.repository.read(self.player)
        self.assertIn("energy", document.private_state())
        self.assertNotIn("energy", STORED_RESOURCE_NAMES)

    def test_exactly_one_committed_document_carries_a_populated_ledger(self) -> None:
        """The census, with the one non-document exclusion stated.

        ``villages/manifest.json`` matches a ``villages/*.json`` glob and is not
        a save document -- it is the asset manifest -- so it is excluded by name
        and the exclusion is **asserted** rather than performed silently.  A first
        draft globbed it in and measured 34 documents, which is how a census
        becomes 34 for a corpus of 33.
        """
        root = harness.REPO_ROOT
        matched = sorted(
            list((root / "villages").glob("*.json"))
            + list((root / "villages" / "quest").glob("*.json"))
            + list((root / "tests" / "saves").glob("*.json"))
        )
        self.assertEqual(34, len(matched), "the raw glob count moved")
        documents = [path for path in matched if path.name != "manifest.json"]
        self.assertEqual(33, len(documents), "the corpus size moved")
        self.assertIn("manifest.json", {path.name for path in matched})
        populated = []
        dict_ledgers = 0
        for path in documents:
            data = json.loads(path.read_text(encoding="utf-8"))
            ledger = data.get("privateState", {}).get("magics")
            if isinstance(ledger, dict):
                dict_ledgers += 1
                if ledger:
                    populated.append((path.name, ledger))
        self.assertEqual(33, dict_ledgers, "a committed document lost its ledger object")
        self.assertEqual(1, len(populated))
        self.assertEqual(POPULATED_CORPUS_DOCUMENT, populated[0][0])
        self.assertEqual({"1": 2, "10": 0, "2": 0, "4": 2, "9": 1}, populated[0][1])

    def test_the_populated_document_is_readable_by_the_reader(self) -> None:
        """Its five keys are all committed ids, which is what design D3 rests on.

        Measured, not assumed, and the falsifier is in the assertion: ``"10"`` is
        out of range for a zero-based ten-row table, so a reader that indexed the
        table positionally would not resolve the fifth key at all.  The
        comparison is between two **int** sets; a first draft intersected a set of
        ints with ``{str(i) for i in ids}``, which is empty by construction and so
        asserted nothing.
        """
        committed = set(load_content(harness.REPO_ROOT).magic_ids())
        keys = {1, 10, 2, 4, 9}
        self.assertTrue(keys <= committed)
        self.assertEqual(keys, {int(key) for key in {"1", "10", "2", "4", "9"}})
        self.assertNotIn(0, committed, "the id space is one-based")
        self.assertEqual(10, len(committed))
        # Every key resolves through the reader, and each is its own value.
        content = load_content(harness.REPO_ROOT)
        for magic_id in sorted(keys):
            with self.subTest(magic=magic_id):
                self.assertIsNotNone(content.magic_row(magic_id))
                self.assertEqual(magic_id, content.magic_row(magic_id)["id"])


class LedgerReadTests(SeededFixture):
    """Task 3.1: the recorded prior counter, and an absent entry read as zero."""

    def test_an_absent_entry_reads_as_zero_and_the_write_creates_it(self) -> None:
        document = self.repository.read(self.player)
        self.assertEqual(0, document.magic_counter(MAGIC_ONE))
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual(1, self.repository.read(self.player).magic_counter(MAGIC_ONE))

    def test_a_recorded_entry_is_read_as_its_own_value(self) -> None:
        self._write_ledger({MAGIC_ONE: 7})
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual(8, outcome.counter_after)
        self.assertEqual(8, self.repository.read(self.player).magic_counter(MAGIC_ONE))

    def test_the_key_is_the_preserved_string_form(self) -> None:
        """``str(magic_id)``, which is what ``command.py:659``/``:671`` use."""
        apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        ledger = self.repository.read(self.player).magic_ledger()
        self.assertIn(MAGIC_ONE_LEDGER_KEY, ledger)
        self.assertNotIn(1, ledger, "the key must be the string form, not an int")


class BoundedDerivationTests(SeededFixture):
    """Task 3.2: the recorded literal cap, with the rejected alternative kept."""

    def test_the_cap_is_the_recorded_literal(self) -> None:
        self.assertEqual(50, COUNTER_CAP)
        self.assertEqual(
            {
                "cap",
                "cap_is",
                "cap_lines",
                "applies_to",
                "rejected",
                "why_rejected",
                "measured_50_in_committed_content",
            },
            set(COUNTER_CAP_PROVENANCE),
        )
        self.assertEqual(["command.py:658", "command.py:670"], COUNTER_CAP_PROVENANCE["cap_lines"])

    def test_the_rejected_derivation_is_still_declared(self) -> None:
        """An alternative deleted from the record cannot be weighed later."""
        self.assertIn("content", COUNTER_CAP_PROVENANCE["rejected"])
        self.assertTrue(COUNTER_CAP_PROVENANCE["why_rejected"])

    def test_the_fifty_in_committed_content_is_measured_not_remembered(self) -> None:
        """**The strongest coincidence in the table, measured.**

        ``50`` really does occur among the committed magic columns: it is the
        ``cash`` price of magic ``1`` and the ``level`` of magic ``5``, one row
        each.  That is worth asserting rather than leaving out, because it is the
        case a later reader would use to argue the cap was derived from content --
        and because magic ``1`` is the identity the committed live phase
        addresses, so "cap = the magic 1 cash price" is the derivation most
        likely to be proposed by accident.  It is refused on provenance anyway:
        the preserved source writes ``50`` beside nothing else.
        """
        content = load_content(harness.REPO_ROOT)
        ids = content.magic_ids()
        measured = {
            column: [
                magic_id
                for magic_id in ids
                if content.magic_field(magic_id, column) == COUNTER_CAP
            ]
            for column in ("gold", "cash", "mana", "level", "target")
        }
        self.assertEqual(
            COUNTER_CAP_PROVENANCE["measured_50_in_committed_content"], measured
        )
        self.assertEqual([1], measured["cash"])
        self.assertEqual([5], measured["level"])
        self.assertEqual([], measured["mana"])
        self.assertEqual([], measured["gold"])
        self.assertEqual([], measured["target"])
        # The column whose *name* matches a stored resource never holds it.
        self.assertEqual(20, max(content.magic_field(i, "mana") for i in ids))
        self.assertEqual(55, max(content.magic_field(i, "level") for i in ids))
        self.assertNotIn("mana columns", COUNTER_CAP_PROVENANCE["why_rejected"])

    def test_the_transition_grows_by_one_below_the_cap(self) -> None:
        for before in (0, 1, 25, 48, 49):
            with self.subTest(before=before):
                self._write_ledger({MAGIC_ONE: before})
                outcome = apply_magic(
                    self._intent(), self.content, self.repository, SERVICE_INSTANT
                )
                self.assertIsInstance(outcome, MagicSuccess)
                self.assertEqual(before + 1, outcome.counter_after)

    def test_the_transition_stops_at_the_cap(self) -> None:
        self._write_ledger({MAGIC_ONE: COUNTER_CAP})
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual(COUNTER_CAP, outcome.counter_after)
        self.assertIs(True, outcome.transition.at_cap)

    def test_the_counter_never_exceeds_the_cap_across_many_operations(self) -> None:
        """The sweep the preserved ``buy`` arm fails: it is unbounded.

        Measured rather than argued: sixty consecutive ``buy`` operations end at
        the cap, where the preserved branch would have reached 60.
        """
        self._write_ledger({MAGIC_ONE: 0})
        for _ in range(60):
            outcome = apply_magic(
                self._intent(), self.content, self.repository, SERVICE_INSTANT
            )
            self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual(COUNTER_CAP, outcome.counter_after)

    def test_the_preserved_buy_arm_would_have_climbed_past_the_cap(self) -> None:
        """The divergence, measured on the recorded arithmetic rather than argued.

        ``command.py:658`` is ``+= min(50, …)``, so the cap bounds the
        *increment*, not the total.  This asserts the arithmetic v1 refused to
        reproduce, which is the only way to state the divergence without
        reproducing it in delivered code.
        """
        preserved_total = 0
        for _ in range(60):
            preserved_total += min(50, 1)
        self.assertEqual(60, preserved_total)
        self.assertGreater(preserved_total, COUNTER_CAP)
        # The **recorded** wording, quoted rather than paraphrased: a first draft
        # asserted the word "unbounded" and the table says "without limit", so the
        # test was checking the author's phrasing rather than the claim.  Both
        # halves are asserted, because the table's subject is the *increment* --
        # that is the whole of the difference from a bound on the counter.
        self.assertIn("on the INCREMENT", PRESERVED_BRANCH_BEHAVIOUR["buy"])
        self.assertIn("without limit", PRESERVED_BRANCH_BEHAVIOUR["buy"])

    def test_a_transition_cannot_be_constructed_by_hand(self) -> None:
        """The issuance token: no magic success without a derived transition."""
        with self.assertRaises(TypeError):
            MagicTransition(  # type: ignore[call-arg]
                magic_id=MAGIC_ONE, operation="buy", before=0, after=1,
                had_recorded_entry=False, at_cap=False,
            )

    def test_the_transition_is_frozen(self) -> None:
        transition = issue_magic_transition(
            magic_id=MAGIC_ONE, operation="buy", before=0, after=1,
            had_recorded_entry=False, at_cap=False,
        )
        with self.assertRaises(Exception):
            transition.after = 99  # type: ignore[misc]
        self.assertEqual(COUNTER_CAP, transition.cap)
        self.assertEqual(COUNTER_CAP_PROVENANCE["cap_is"], transition.cap_provenance["cap_is"])


class CounterAboveCapTests(SeededFixture):
    """Task 3.3: a recorded counter already above the bound is refused, not rewritten."""

    def test_a_counter_above_the_cap_is_refused(self) -> None:
        self._write_ledger({MAGIC_ONE: 113})
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        refusal = self._assert_refused(outcome, RefusalCode.COUNTER_ABOVE_CAP)
        self.assertEqual(113, refusal.detail["recorded_counter"])
        self.assertEqual(COUNTER_CAP, refusal.detail["cap"])

    def test_the_refusal_does_not_reduce_the_recorded_counter(self) -> None:
        """The destruction it exists to prevent: ``= min(50, x+1)`` would write 50."""
        self._write_ledger({MAGIC_ONE: 113})
        self._assert_refusal_wrote_nothing(
            apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT),
            RefusalCode.COUNTER_ABOVE_CAP,
        )
        self.assertEqual(113, self.repository.read(self.player).magic_counter(MAGIC_ONE))

    def test_exactly_the_cap_is_accepted(self) -> None:
        """The boundary, from both sides, so a ``>=`` slip cannot hide here."""
        self._write_ledger({MAGIC_ONE: COUNTER_CAP})
        self.assertIsInstance(
            apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT),
            MagicSuccess,
        )
        self._write_ledger({MAGIC_ONE: COUNTER_CAP + 1})
        self._assert_refused(
            apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT),
            RefusalCode.COUNTER_ABOVE_CAP,
        )

    def test_the_refusal_reports_the_preserved_behaviour_it_refuses(self) -> None:
        self._write_ledger({MAGIC_ONE: 113})
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        refusal = self._assert_refused(outcome, RefusalCode.COUNTER_ABOVE_CAP)
        self.assertEqual(PRESERVED_BRANCH_BEHAVIOUR["use"], refusal.detail["legacy_behaviour"])
        self.assertIs(False, refusal.detail["rolled_back"])

    def test_the_recorded_fixture_chain_is_why_the_cap_is_fifty(self) -> None:
        """The executed fixture reached 113, which is above the cap.

        Read from the committed fixture directory rather than from a transcribed
        number, because 113 is the whole reason this refusal has a subject: the
        legacy server produced a counter its own cap cannot explain.
        """
        root = harness.REPO_ROOT / "tests" / "fixtures" / "godot-damage"
        self.assertTrue(root.is_dir(), "the executed fixture is gone")
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*.json"))
        )
        self.assertIn("113", text)


class SameTransitionTests(SeededFixture):
    """Task 3.4: both operations derive the same transition, and say so."""

    def test_both_operations_derive_the_same_value_from_the_same_state(self) -> None:
        buy = apply_magic(
            self._intent(operation="buy"), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(buy, MagicSuccess)
        self._write_ledger({MAGIC_ONE: 0})
        use = apply_magic(
            self._intent(operation="use"), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(use, MagicSuccess)
        self.assertEqual(buy.counter_after, use.counter_after)
        self.assertEqual(1, buy.counter_after)
        self.assertEqual(1, use.counter_after)

    def test_the_declared_operation_set_is_the_closed_set(self) -> None:
        self.assertEqual(("buy", "use"), declared_operations())
        self.assertEqual(frozenset({"buy", "use"}), INTENT_OPERATION_VALUES["operation"])

    def test_the_payload_states_the_sameness_explicitly(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        payload = outcome.payload()
        self.assertIs(True, payload["same_transition_for_both_operations"])
        self.assertEqual("buy", payload["magic"]["operation"])

    def test_the_response_lists_divergence_reasons_not_a_recomputed_value(self) -> None:
        """D7: the reasons are data; nothing re-derives a legacy counter.

        An absent key is the case the fresh corpus reaches first, so the reason
        is present there -- and the reason list must not contain a number that
        looks like the legacy answer.
        """
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        payload = outcome.payload()
        self.assertEqual(["preserved_absent_key_arm_writes_zero"], payload["divergences"])
        for reason in payload["divergences"]:
            self.assertIsInstance(reason, str)
            self.assertEqual(reason, reason.strip())
            self.assertFalse(reason.isdigit())

    def test_a_buy_at_the_cap_reports_the_unbounded_divergence(self) -> None:
        self._write_ledger({MAGIC_ONE: COUNTER_CAP})
        outcome = apply_magic(
            self._intent(operation="buy"), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertIn(
            "preserved_buy_increment_is_unbounded", outcome.payload()["divergences"]
        )

    def test_a_use_at_the_cap_reports_no_divergence_reason(self) -> None:
        """The one reachable agreement, which makes the list meaningful.

        If the reasons were unconditional this would still pass, so the boundary
        is asserted in both directions.
        """
        self._write_ledger({MAGIC_ONE: COUNTER_CAP})
        outcome = apply_magic(
            self._intent(operation="use"), self.content, self.repository, SERVICE_INSTANT
        )
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual([], outcome.payload()["divergences"])

    def test_the_preserved_behaviour_table_is_quoted_verbatim_in_the_payload(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual(
            PRESERVED_MAGIC_BEHAVIOUR, outcome.payload()["preserved_branch_behaviour"]
        )


class CommittedReportTests(SeededFixture):
    """Task 3.5: the committed row verbatim, and the two levels not compared."""

    def test_the_committed_row_is_reported_verbatim(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        committed = outcome.payload()["committed"]
        for field, expected in (
            ("id", MAGIC_ONE),
            ("name", MAGIC_ONE_NAME),
            ("gold", MAGIC_ONE_GOLD),
            ("cash", MAGIC_ONE_CASH),
            ("mana", MAGIC_ONE_MANA),
            ("level", MAGIC_ONE_LEVEL),
            ("target", MAGIC_ONE_TARGET),
        ):
            with self.subTest(field=field):
                self.assertEqual(expected, committed[field])
        self.assertEqual(list(MAGIC_ONE_AREA), committed["area"])

    def test_every_reported_value_is_the_committed_one_for_its_own_row(self) -> None:
        """Not only for magic 1: the whole table, through the response shape."""
        for magic_id in load_content(harness.REPO_ROOT).magic_ids():
            with self.subTest(magic=magic_id):
                self.repository.read(self.player)
                document = self.repository.read(self.player)
                document.private_state()["magics"] = {}
                self.repository.write(document)
                outcome = apply_magic(
                    self._intent(magic_id=magic_id),
                    self.content,
                    self.repository,
                    SERVICE_INSTANT,
                )
                self.assertIsInstance(outcome, MagicSuccess)
                self.assertEqual(magic_id, outcome.payload()["committed"]["id"])

    def test_the_recorded_level_is_reported_beside_the_committed_one(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        committed = outcome.payload()["committed"]
        self.assertEqual(CORPUS_LEVEL, committed["player_level"])
        self.assertEqual(MAGIC_ONE_LEVEL, committed["level"])

    def test_the_two_levels_are_reported_and_never_compared(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        committed = outcome.payload()["committed"]
        self.assertIs(False, committed["level_compared"])
        self.assertIs(False, committed["level_gate_enforced"])
        self.assertIn("min_level", committed["level_gate_deferred_because"])

    def test_the_committed_level_is_above_the_corpus_level_and_it_still_succeeds(self) -> None:
        """The gap's whole cost, made concrete: 1 against 38, and no refusal.

        If this ever refuses, a gate has been added, and the deferred reason in
        :meth:`test_the_two_levels_are_reported_and_never_compared` is no longer
        the reason.
        """
        self.assertLess(CORPUS_LEVEL, MAGIC_ONE_LEVEL)
        self.assertIsInstance(
            apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT),
            MagicSuccess,
        )

    def test_no_value_in_the_report_is_computed_from_another(self) -> None:
        """No committed field appears as an arithmetic result of a sibling.

        A price would show up as exactly this: a number equal to no committed
        value but derived from two of them.  Reported values are therefore
        required to be *either* a committed value *or* an absent field.
        """
        content = load_content(harness.REPO_ROOT)
        committed_values = {
            content.magic_field(magic_id, field)
            for magic_id in content.magic_ids()
            for field in NUMERIC_COMMITTED_COLUMNS
        }
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        report = outcome.payload()["committed"]
        for field in NUMERIC_COMMITTED_COLUMNS:
            with self.subTest(field=field):
                self.assertIn(report[field], committed_values | {None})


class RefusalOrderTests(SeededFixture):
    """Task 3.6: all three refusals resolve before any ledger write."""

    def test_an_unknown_identity_is_refused_with_the_committed_space_reported(self) -> None:
        for magic_id in (0, -1, 11, 999):
            with self.subTest(magic=magic_id):
                self._assert_refusal_wrote_nothing(
                    apply_magic(
                        self._intent(magic_id=magic_id),
                        self.content,
                        self.repository,
                        SERVICE_INSTANT,
                    ),
                    RefusalCode.UNKNOWN_MAGIC_ID,
                )

    def test_an_unknown_identity_is_refused_before_the_cap_is_considered(self) -> None:
        """A ledger counter above the cap for an **unknown** id is still
        ``unknown_magic_id``: the identity is resolved first, so the reported
        reason is the true one."""
        document = self.repository.read(self.player)
        document.private_state()["magics"] = {"11": 5000}
        self.repository.write(document)
        outcome = apply_magic(
            self._intent(magic_id=11), self.content, self.repository, SERVICE_INSTANT
        )
        self._assert_refused(outcome, RefusalCode.UNKNOWN_MAGIC_ID)

    def test_the_unknown_identity_refusal_reports_the_committed_space(self) -> None:
        outcome = apply_magic(
            self._intent(magic_id=11), self.content, self.repository, SERVICE_INSTANT
        )
        refusal = self._assert_refused(outcome, RefusalCode.UNKNOWN_MAGIC_ID)
        self.assertEqual(11, refusal.detail["requested_magic_id"])
        self.assertEqual(10, refusal.detail["committed_rows"])
        self.assertEqual(list(range(1, 11)), refusal.detail["committed_ids"])
        self.assertIsNone(refusal.detail["resolved_row"])
        self.assertEqual("magics", refusal.detail["committed_table_is"])

    def test_there_is_no_aliasing_for_a_non_positive_id(self) -> None:
        """Design D3: no positional clamp, so no ``aliased_magic_id`` refusal."""
        self.assertNotIn(ACTION, NON_NEGATIVE_ADDRESSING)
        self.assertEqual("magic_id", ADDRESSING_FIELDS[ACTION])
        for magic_id in (0, -1, -113):
            with self.subTest(magic=magic_id):
                self._assert_refused(
                    apply_magic(
                        self._intent(magic_id=magic_id),
                        self.content,
                        self.repository,
                        SERVICE_INSTANT,
                    ),
                    RefusalCode.UNKNOWN_MAGIC_ID,
                )

    def test_an_unknown_player_is_refused_before_the_ledger_is_read(self) -> None:
        self._assert_refused(
            apply_magic(
                self._intent(player="no-such-player"), self.content, self.repository,
                SERVICE_INSTANT,
            ),
            RefusalCode.UNKNOWN_PLAYER,
        )

    def test_every_refusal_reports_a_status_the_transport_can_ask_for(self) -> None:
        for outcome in (
            apply_magic(
                self._intent(magic_id=11), self.content, self.repository, SERVICE_INSTANT
            ),
            apply_magic(
                self._intent(player="no-such-player"), self.content, self.repository,
                SERVICE_INSTANT,
            ),
        ):
            self.assertIsInstance(outcome, Refusal)
            self.assertEqual(404 if outcome.code is RefusalCode.UNKNOWN_PLAYER else 409,
                             outcome.http_status)

    def test_the_two_new_codes_are_both_409(self) -> None:
        self.assertEqual(409, RefusalCode.UNKNOWN_MAGIC_ID.value and 409)
        from server_v1_refusals import REFUSAL_HTTP_STATUS

        self.assertEqual(409, REFUSAL_HTTP_STATUS[RefusalCode.UNKNOWN_MAGIC_ID])
        self.assertEqual(409, REFUSAL_HTTP_STATUS[RefusalCode.COUNTER_ABOVE_CAP])


class LedgerShapeRefusalTests(SeededFixture):
    """Task 3.6 / 6.6: the ledger-shape refusal over an in-memory row.

    Unreachable through the corpus (see :class:`CorpusLedgerTests`), so it is
    exercised by handing the domain a store whose row the corpus cannot produce.
    The tamper is applied through the same in-memory document the repository
    holds, and **not** by editing a committed save.
    """

    def _run_with_ledger(self, value: Any) -> Any:
        document = self.repository.read(self.player)
        document.private_state()["magics"] = value
        self.repository.write(document)
        return apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)

    def test_an_absent_ledger_is_refused_rather_than_read_as_empty(self) -> None:
        def tamper(document: Dict[str, Any]) -> None:
            document["privateState"].pop("magics", None)

        self._rewrite_file(tamper)
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        refusal = self._assert_refused(outcome, RefusalCode.UNREADABLE_STATE)
        self.assertEqual("unreadable_state", refusal.detail["cause"])

    def test_a_non_object_ledger_is_refused_for_each_shape(self) -> None:
        for value in ([], "1", 0, None, 1.5, True, [[1]]):
            with self.subTest(value=value):
                outcome = self._run_with_ledger(value)
                self._assert_refused(outcome, RefusalCode.UNREADABLE_STATE)

    def test_a_non_integer_counter_is_refused(self) -> None:
        for value in ("1", 1.5, None, True, [1]):
            with self.subTest(value=value):
                outcome = self._run_with_ledger({"1": value})
                self._assert_refused(outcome, RefusalCode.UNREADABLE_STATE)

    def test_an_integer_counter_is_accepted(self) -> None:
        """The boundary the refusals above sit on: one shape change is the line."""
        outcome = self._run_with_ledger({"1": 3})
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual(4, outcome.counter_after)

    def test_a_refused_shape_leaves_the_document_byte_identical(self) -> None:
        """**Byte-identical to the malformed state, not to the pristine one.**

        The first draft captured ``_pre_bytes()`` *before* the bad shape was
        written, so the comparison asserted that the refusal put the document
        back -- which it does not, and must not: restoring would be a second
        unrequested mutation.  The honest baseline is the bytes as the refusal
        found them, which is what this now measures, and it is the sharper
        claim anyway -- a refusal that rewrote the ledger back to ``{}`` would
        also pass the old version.
        """
        document = self.repository.read(self.player)
        document.private_state()["magics"] = "1"
        self.repository.write(document)
        before = corpus_save_bytes(self.corpus)

        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self._assert_refused(outcome, RefusalCode.UNREADABLE_STATE)
        self.assertEqual(before, corpus_save_bytes(self.corpus))
        self.assertIn(b'"magics": "1"', before)


class SuccessPayloadTests(SeededFixture):
    """The success body's own contract: no price key, no deltas, seven resources."""

    def test_no_price_is_charged_and_the_body_says_so(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        payload = outcome.payload()
        self.assertIsNone(payload["price_charged"])
        self.assertNotIn("derived_deltas", payload)

    def test_every_stored_resource_is_reported_and_none_moved(self) -> None:
        before = self._resources()
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        after = self._resources()
        self.assertEqual(before, after)
        self.assertEqual(before, outcome.state)
        self.assertEqual(sorted(STORED_RESOURCE_NAMES), outcome.payload()["stored_resources_compared"])

    def test_the_ledger_after_is_the_store_read_back(self) -> None:
        """The reported key order is the store's, read back after the write.

        ``ledger_after`` is a **tuple** on the model, so the comparison is made
        against ``list(...)`` on both sides.  A first draft compared a list to the
        tuple directly and failed on a type difference rather than on a value
        difference -- and a comparison that cannot pass teaches nothing about what
        the body contains.  The order itself is asserted too, because a sorted or
        set-derived order would satisfy the membership test and not this one.
        """
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        stored = self.repository.read(self.player).magic_ledger()
        self.assertEqual(list(stored), list(outcome.ledger_after))
        self.assertEqual([MAGIC_ONE_LEDGER_KEY], list(outcome.ledger_after))
        self.assertIsInstance(outcome.ledger_after, tuple)

    def test_the_transition_carries_its_provenance_onto_the_payload(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        counter = outcome.payload()["counter"]
        self.assertEqual(COUNTER_CAP, counter["cap"])
        self.assertEqual(COUNTER_CAP_PROVENANCE["cap_is"], counter["cap_is"])
        self.assertIs(False, counter["had_recorded_entry"])
        self.assertEqual(0, counter["before"])
        self.assertEqual(1, counter["after"])

    def test_the_reported_instant_is_the_service_clock_and_is_stored_nowhere(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        self.assertEqual(SERVICE_INSTANT, outcome.payload()["instant"])
        ledger = self.repository.read(self.player).magic_ledger()
        self.assertEqual({MAGIC_ONE_LEDGER_KEY: 1}, ledger)

    def test_the_committed_mapping_is_read_only(self) -> None:
        outcome = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(outcome, MagicSuccess)
        with self.assertRaises(TypeError):
            outcome.transition.committed["gold"] = 1  # type: ignore[index]

    def test_two_transitions_are_distinguishable(self) -> None:
        first = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        second = apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT)
        self.assertIsInstance(first, MagicSuccess)
        self.assertIsInstance(second, MagicSuccess)
        self.assertNotEqual(
            first.payload()["magic"]["transition_id"],
            second.payload()["magic"]["transition_id"],
        )


class PostConditionProofTests(SeededFixture):
    """Each of the four halves, broken on its own, and the rollback."""

    def _run_with_tamper(self, tamper: Callable[[Dict[str, Any]], None]) -> Any:
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

        return apply_magic(self._intent(), self.content, _Tampering(), SERVICE_INSTANT)

    def test_the_addressed_key_half_fails_alone(self) -> None:
        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["1"] = 41

        refusal = self._assert_refused(
            self._run_with_tamper(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("addressed_key_matched_transition", refusal.detail["half"])

    def test_the_unaddressed_key_half_fails_alone(self) -> None:
        def seed(document: Dict[str, Any]) -> None:
            document["privateState"]["magics"] = {"5": 3}

        self.corpus = remove_corpus(self.corpus)  # type: ignore[assignment]
        self.corpus = build_corpus(mutate=seed)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.player = seed_player_id()

        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["5"] = 4

        refusal = self._assert_refused(
            self._run_with_tamper(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("unaddressed_keys_unchanged", refusal.detail["half"])

    def test_an_added_ledger_key_is_reported_as_an_unaddressed_change(self) -> None:
        """**A first draft called this "the extra-key half", and it was wrong.**

        An added key inside ``privateState.magics`` *is* an unaddressed key: the
        half-2 check compares every key other than the addressed one, so a new
        key fails it before the leaf-ownership half is ever consulted.  The
        tamper is kept and the expectation is corrected, because the measured
        answer is the interesting one -- an extra ledger key cannot masquerade
        as a leaf problem.  The leaf half's own single failure mode is
        :meth:`test_the_leaf_half_fails_alone_when_a_leaf_outside_the_ledger_moves`.
        """

        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["9"] = 1

        refusal = self._assert_refused(
            self._run_with_tamper(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("unaddressed_keys_unchanged", refusal.detail["half"])

    def test_the_leaf_half_fails_alone_when_a_leaf_outside_the_ledger_moves(self) -> None:
        """The one tamper that reaches half 4 without tripping an earlier half.

        Half 4 has two clauses: every changed leaf belongs to the addressed
        ledger key, and **at most** one leaf changed.  The clause that only half
        4 can see is the second one, and the tamper below reaches it by moving a
        leaf that is neither in the ledger nor one of the seven resources --
        ``playerInfo.last_logged_in``, which is written by the service on every
        response and is exactly the sort of field a wall-clock stamp would land
        in.  A resource would not do: it would trip half 3 first.
        """

        def tamper(data: Dict[str, Any]) -> None:
            data["playerInfo"]["last_logged_in"] = 1

        refusal = self._assert_refused(
            self._run_with_tamper(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("exactly_one_leaf_path_changed", refusal.detail["half"])

    def test_the_resources_half_fails_when_a_resource_moves(self) -> None:
        """The falsifiable half, and the one that makes D2 non-tautological.

        Each of the rejected charges would move exactly one of the seven, so this
        is the half a price of any size fails.

        **The holder is located by searching all three, because the seven stored
        resources are not held in one place.**  Measured on the committed
        fresh-player corpus: ``gold``/``wood``/``steel``/``oil``/``xp`` are under
        ``maps[0]``, ``mana`` under ``privateState``, and ``cash`` under
        ``playerInfo``.  A first draft looked in ``privateState`` and fell through
        to ``maps[0]``, which raised ``KeyError: 'cash'`` on the first subtest and
        would have raised it again for ``mana`` had ``cash`` come second.  The
        location is therefore *measured per field* here rather than assumed, and
        the measured table is asserted, because a holder moving between documents
        is exactly the change that would silently stop a charge being observable.
        """
        raw = json.loads(corpus_save_bytes(self.corpus).decode("utf-8"))
        holders = ("privateState", "playerInfo", "maps[0]")

        def locate(field: str) -> str:
            for holder in holders:
                target = raw["maps"][0] if holder == "maps[0]" else raw[holder]
                if field in target:
                    return holder
            self.fail("%r is in no stored holder" % field)

        measured = {name: locate(name) for name in STORED_RESOURCE_NAMES}
        self.assertEqual(
            {
                "xp": "maps[0]",
                "gold": "maps[0]",
                "wood": "maps[0]",
                "oil": "maps[0]",
                "steel": "maps[0]",
                "cash": "playerInfo",
                "mana": "privateState",
            },
            measured,
            "a stored resource moved holder",
        )

        for field, delta in (("gold", -1), ("cash", 1), ("mana", 1), ("xp", 1)):
            with self.subTest(field=field):
                where = measured[field]

                def tamper(
                    data: Dict[str, Any], where=where, field=field, delta=delta
                ) -> None:
                    holder = data["maps"][0] if where == "maps[0]" else data[where]
                    holder[field] = holder[field] + delta

                refusal = self._assert_refused(
                    self._run_with_tamper(tamper), RefusalCode.POST_CONDITION_VIOLATION
                )
                self.assertEqual("resources_unchanged", refusal.detail["half"])

        # The rejected charges' own columns: three are stored resources and one
        # -- ``level`` -- is not, which is why the coverage above names it
        # separately.  Measured: it is on the map, not among the seven.
        for column in ("gold", "cash", "mana"):
            self.assertIn(column, measured)
        self.assertNotIn("level", measured)
        self.assertIn("level", raw["maps"][0])
        self.assertEqual(1, raw["maps"][0]["level"])
        # And the committed magic table names exactly the four numeric columns a
        # charge could plausibly come from, which is the D2 candidate set.
        self.assertEqual(("gold", "cash", "mana", "level"), NUMERIC_COMMITTED_COLUMNS)
        content = load_content(harness.REPO_ROOT)
        self.assertEqual(30000, content.magic_field(1, "gold"))
        self.assertEqual(50, content.magic_field(1, "cash"))
        self.assertEqual(8, content.magic_field(1, "mana"))
        # The stored level is *below* the committed magic level for the row the
        # committed corpus would address, which is recorded as reported data and
        # never enforced -- see the level-absence guard above.
        self.assertLess(raw["maps"][0]["level"], content.magic_field(1, "level"))

    def test_the_four_halves_are_distinguishable(self) -> None:
        """The control: one ``half`` string for all four would pass the above.

        Each tamper is the one that reaches its half first in the enforced order
        (``addressed``, ``unaddressed``, ``resources``, ``leaf``).  The fourth
        uses the out-of-ledger leaf rather than an added ledger key, because an
        added ledger key is an **unaddressed** change -- see
        :meth:`test_an_added_ledger_key_is_reported_as_an_unaddressed_change`,
        which is why a first draft here could only ever produce three distinct
        names.
        """

        def addressed(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["1"] = 41

        def unaddressed(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["9"] = 1

        def resource(data: Dict[str, Any]) -> None:
            data["privateState"]["mana"] = 1

        def leaf(data: Dict[str, Any]) -> None:
            data["playerInfo"]["last_logged_in"] = 1

        halves = {
            self._run_with_tamper(addressed).detail["half"],
            self._run_with_tamper(unaddressed).detail["half"],
            self._run_with_tamper(resource).detail["half"],
            self._run_with_tamper(leaf).detail["half"],
        }
        self.assertLessEqual(
            {
                "addressed_key_matched_transition",
                "unaddressed_keys_unchanged",
                "exactly_one_leaf_path_changed",
                "resources_unchanged",
            },
            halves,
        )
        self.assertEqual(4, len(halves), "two halves reported the same name")

    def test_a_violation_rolls_back_to_the_pre_request_bytes(self) -> None:
        before = self._pre_bytes()

        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["1"] = 41

        self._run_with_tamper(tamper)
        self.assertEqual(before, corpus_save_bytes(self.corpus))

    def test_the_refusal_says_whether_the_rollback_worked(self) -> None:
        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["1"] = 41

        outcome = self._run_with_tamper(tamper)
        self.assertIs(True, self._assert_refused(
            outcome, RefusalCode.POST_CONDITION_VIOLATION
        ).detail["rolled_back"])

    def test_a_rolled_back_store_can_be_reused_cleanly(self) -> None:
        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["magics"]["1"] = 41

        self._run_with_tamper(tamper)
        self.assertIsInstance(
            apply_magic(self._intent(), self.content, self.repository, SERVICE_INSTANT),
            MagicSuccess,
        )

    def test_the_first_three_halves_are_a_specification_check_and_that_is_stated(
        self,
    ) -> None:
        """Task 9.8: half 1 compares v1's write against v1's own derivation.

        Asserted as **v1 being the only writer on this path**, which is why half
        4 and not half 1 carries the evidence weight.  The check is that the
        corpus save contains no second writer: the repository is the sole writer
        and the domain is its sole caller.
        """
        self.assertIn("specification", DOMAIN_SOURCE.read_text(encoding="utf-8"))
        self.assertIn("falsifiable", DOMAIN_SOURCE.read_text(encoding="utf-8"))
        # ... and in the **code**, not only in the prose: the falsifiable half is
        # an enforced comparison over the seven names, not a sentence.  A first
        # draft read both words out of ``_code_only(source)``, where the lexer
        # blanks every string literal -- so both assertions were unsatisfiable
        # by construction, which is why they had to be moved to the raw source
        # for the prose and kept here for the code where the words are absent.
        code = _code_only(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        self.assertNotIn("specification", code)
        self.assertIn("STORED_RESOURCE_NAMES", code)
        self.assertIn("before_resources", code)
        self.assertIn("after_resources", code)
        # The half's **name** is a string literal, so it is read from the raw
        # source; the comparison it names is read from the code.
        self.assertIn('"resources_unchanged"', DOMAIN_SOURCE.read_text(encoding="utf-8"))


class IntentTests(unittest.TestCase):
    """Task 4.1-4.4: the schema, the operation set, and the delta precedence."""

    def _body(self, **fields: Any) -> Dict[str, Any]:
        body: Dict[str, Any] = {"player_id": "p", "magic_id": MAGIC_ONE}
        body.update(fields)
        return body

    def _parse(self, **fields: Any) -> Any:
        return parse_intent(ACTION, self._body(**fields))

    def test_the_schema_is_closed_over_exactly_three_keys(self) -> None:
        self.assertEqual(
            frozenset({"player_id", "magic_id", "operation"}), INTENT_SCHEMAS[ACTION]
        )

    def test_a_well_formed_request_parses_into_the_id_and_the_operation(self) -> None:
        outcome = self._parse(operation="use")
        self.assertIsInstance(outcome, Intent)
        self.assertEqual(MAGIC_ONE, outcome.magic_id)
        self.assertEqual("use", outcome.operation)
        self.assertIsNone(outcome.row)
        self.assertIsNone(outcome.collection_id)

    def test_the_addressing_field_is_the_magic_id(self) -> None:
        self.assertEqual("magic_id", ADDRESSING_FIELDS[ACTION])
        outcome = self._parse(operation="buy")
        self.assertIsInstance(outcome, Intent)
        self.assertEqual("/privateState/magics/%d" % MAGIC_ONE, outcome.addressed_path())

    def test_the_operation_field_is_declared_separately_from_the_address(self) -> None:
        """Design D1: ``allowed == required`` no longer holds, and that is stated."""
        self.assertEqual({"magic": "operation"}, INTENT_OPERATION_FIELDS)
        self.assertNotIn("operation", ADDRESSING_FIELDS.values())

    def test_every_declared_operation_is_accepted(self) -> None:
        for operation in sorted(INTENT_OPERATION_VALUES["operation"]):
            with self.subTest(operation=operation):
                outcome = self._parse(operation=operation)
                self.assertIsInstance(outcome, Intent)
                self.assertEqual(operation, outcome.operation)

    def test_an_operation_outside_the_closed_set_is_refused(self) -> None:
        for value in ("sell", "BUY", "", "buy ", 1, True, None, ["buy"]):
            with self.subTest(value=value):
                outcome = self._parse(operation=value)
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)
                self.assertEqual(["buy", "use"], outcome.detail["allowed_operations"])

    def test_a_missing_operation_is_refused_rather_than_defaulted(self) -> None:
        outcome = self._parse()
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)
        self.assertNotIn("received", {k for k in outcome.detail if k == "operation"})

    def test_a_delta_key_is_refused_before_the_closed_key_check(self) -> None:
        """Task 4.4: a request carrying an unknown field **and** a delta is a delta.

        ``gold`` is not in the magic schema, so the closed-key check would also
        refuse it; the point is that the **delta** reason wins, because it is the
        security-relevant one.
        """
        outcome = self._parse(operation="buy", gold=-1)
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.CLIENT_SUPPLIED_DELTA, outcome.code)

    def test_an_unknown_request_field_is_refused(self) -> None:
        """Genuinely unknown names: ``unknown_request_field``.

        ``price`` and ``amount`` are **not** in this list, and a first draft put
        them here and measured the delta code instead -- correctly.  Both are
        declared entries of ``DELTA_KEYS``, so the security-relevant refusal wins,
        which is task 4.4's precedence rather than a defect in this expectation.
        """
        for field in ("collection_id", "row", "level", "now", "quantity", "spells"):
            with self.subTest(field=field):
                outcome = self._parse(operation="buy", **{field: 1})
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.UNKNOWN_REQUEST_FIELD, outcome.code)

    def test_a_delta_shaped_field_is_refused_as_a_delta_even_on_this_route(self) -> None:
        """The same precedence, named: a price or an amount is never just unknown.

        Recorded because this line's whole subject is a refused price, so a client
        offering ``price`` or ``amount`` to ``/v1/magic`` is the one request shape
        that deserves a positive assertion rather than an incidental one.
        """
        for field in ("price", "amount", "gold", "cash", "mana"):
            with self.subTest(field=field):
                outcome = self._parse(operation="buy", **{field: 1})
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.CLIENT_SUPPLIED_DELTA, outcome.code)

    def test_a_non_integer_magic_id_is_refused_at_the_parser(self) -> None:
        """The executed fixture recorded ``1.0`` creating a distinct ``"1.0"`` key."""
        for value in ("1", 1.0, True, None, [1]):
            with self.subTest(value=value):
                outcome = self._parse(operation="buy", magic_id=value)
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)

    def test_a_negative_magic_id_reaches_the_domain_rather_than_the_parser(self) -> None:
        """Design D3: refused as ``unknown_magic_id``, not as malformed."""
        outcome = self._parse(operation="buy", magic_id=-1)
        self.assertIsInstance(outcome, Intent)
        self.assertEqual(-1, outcome.magic_id)

    def test_a_zero_magic_id_reaches_the_domain_rather_than_the_parser(self) -> None:
        outcome = self._parse(operation="buy", magic_id=0)
        self.assertIsInstance(outcome, Intent)
        self.assertEqual(0, outcome.magic_id)

    def test_the_magic_id_is_required(self) -> None:
        body = {"player_id": "p", "operation": "buy"}
        outcome = parse_intent(ACTION, body)
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)

    def test_the_intent_module_names_only_the_three_structural_codes(self) -> None:
        """Restated here because the magic line added a table to that module.

        ``test_boundary_invariant`` already asserts the structural rule over the
        AST; this is the assertion from the caller's side, and the duplication is
        deliberate -- the two would only differ if one of them stopped running.

        **The premise changed, because the premise was wrong.**  This test used to
        read "the intent module names no refusal code outside its import", which
        could never hold: that module is where the request *envelope* is parsed,
        so constructing refusals is its job.  Measured, it names exactly three
        codes -- ``MALFORMED_REQUEST``, ``UNKNOWN_REQUEST_FIELD`` and
        ``CLIENT_SUPPLIED_DELTA`` -- and all three are about the request's shape.
        So the claim that is actually worth pinning is the one that separates
        those from the domain codes this line added: the intent layer knows
        nothing about magics, counters, caps, or levels.

        Both halves are asserted.  The first is a closed set, so a fourth
        structural code added later fails until someone says so; the second is
        what makes the first safe, since it is the direction a domain code would
        arrive from.
        """
        source = (harness.SERVICE_DIR / "server_v1_intent.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        codes = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "RefusalCode"
        }
        self.assertEqual(
            {"CLIENT_SUPPLIED_DELTA", "MALFORMED_REQUEST", "UNKNOWN_REQUEST_FIELD"},
            codes,
        )
        # No code this line owns reaches the request layer, by name or by stem.
        stems = ("MAGIC", "COUNTER", "CAP", "LEVEL")
        for stem in stems:
            self.assertFalse(
                any(stem in code for code in codes),
                "the intent layer named a domain refusal code",
            )
        # The intent layer **does** know the word "magic", and that is correct
        # rather than a leak: it owns the request's *addressing*, so it must know
        # which field addresses the row.  A first draft asserted the whole
        # vocabulary was absent and failed on ``magic_id`` -- asserting that an
        # intent cannot be addressable.  What is asserted instead is the sharper
        # pair: the magic **fields** are present, and the magic **derived
        # quantities** are not, because those are the domain's to own.
        code_only = _code_only(source)
        self.assertIn("magic_id", code_only)
        for token in ("COUNTER_CAP", "counter_after", "level_gate", "charged",
                      "price_charged"):
            self.assertNotIn(token, code_only)


class VocabularyTests(unittest.TestCase):
    """Task 1: the two new codes, and the pin one step from tripping.

    **Amended by the combat line (M13 line 4), which added a twentieth code.**
    The rationale is the same one recorded at the pin itself in
    ``test_boundary_invariant.py``: the table held 19, this line adds exactly
    one, and the bound exists so that a reviewer must read a *failing test*
    before the vocabulary grows.  A guard that pins its own text is unusual and
    is kept, precisely so that a quiet amendment to the number here cannot
    outlive the number it describes.
    """

    def test_exactly_two_codes_were_added(self) -> None:
        self.assertEqual(20, len(list(RefusalCode)))
        self.assertIn(RefusalCode.UNKNOWN_MAGIC_ID, list(RefusalCode))
        self.assertIn(RefusalCode.COUNTER_ABOVE_CAP, list(RefusalCode))

    def test_the_vocabulary_is_one_code_from_tripping_the_size_pin(self) -> None:
        """Task 10.3, restated: the pin is ``< 21`` and this line leaves it at 20.

        Asserted rather than left as a note, so the next line to need a code
        cannot pass the pin by not knowing how close it is.  The pin's own
        spelling is read from the file that holds it, so an amendment there
        fails here instead of being discovered a line later.
        """
        pin = (harness.TESTS_DIR / "test_boundary_invariant.py").read_text(encoding="utf-8")
        self.assertIn("self.assertLess(len(list(RefusalCode)), 21)", pin)
        self.assertLess(len(list(RefusalCode)), 21)
        self.assertEqual(20, len(list(RefusalCode)))

    def test_both_new_codes_are_named_by_the_domain(self) -> None:
        source = _code_only(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        self.assertIn("RefusalCode.UNKNOWN_MAGIC_ID", source)
        self.assertIn("RefusalCode.COUNTER_ABOVE_CAP", source)

    def test_the_transport_names_no_refusal_code(self) -> None:
        """D2 of the boundary, restated for the third route."""
        source = (harness.SERVICE_DIR / "server_v1_app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        codes = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "RefusalCode"
        }
        self.assertEqual(set(), codes)

    def test_the_transport_declares_no_arithmetic(self) -> None:
        source = (harness.SERVICE_DIR / "server_v1_app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        offenders: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and not (
                isinstance(node.op, ast.Mod)
                and isinstance(node.left, ast.Constant)
                and isinstance(node.left.value, str)
            ):
                offenders.append(type(node.op).__name__)
        self.assertEqual([], offenders)

    def test_the_route_path_is_a_literal_not_a_concatenation(self) -> None:
        source = (harness.SERVICE_DIR / "server_v1_app.py").read_text(encoding="utf-8")
        self.assertIn('MAGIC_PATH = "/v1/magic"', source)
        self.assertIn('"POST /v1/magic": "magic"', source)


if __name__ == "__main__":
    unittest.main()
