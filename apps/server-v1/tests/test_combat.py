#!/usr/bin/env python3
"""The combat slice: resolve an identity, destroy nothing, prove it.

This line's subject is the **absence of a rule**, and the centre of gravity of
this file is therefore inverted relative to every sibling slice. ``test_magic.py``
tests a rule that holds; this one tests the claim that there is no rule to hold,
and the danger specific to that shape is a guard that passes because it is
looking at the wrong thing. Four claims carry the file.

1. **No derivation, and that is structural rather than editorial** (design D2).
   The committed table carries nine combat columns -- ``attack``, ``defense``,
   ``life``, ``attack_interval``, ``attack_range``, ``best_against``,
   ``best_against_mult``, ``min_level`` and ``syringes`` -- and not one of them
   names this branch's outcome. :class:`NoDerivationTests` therefore does not
   check that no damage *happened* (the success path proves that too, from the
   other direction); it walks the AST of ``server_v1_combat.py`` and requires that
   **no arithmetic node exists in the module at all**. Reading a column is the
   only way to produce a value from it, so a guard at the arithmetic site is
   strictly upstream of a guard at the answer site -- and unlike the answer site
   it cannot be satisfied by a module that reports a hard-coded number instead.
2. **The two ``push_dead_unit`` gates are reported, and the two ways a reader can
   collapse them are each closed separately.** ``resurrectable`` **absent** must
   stay distinguishable from ``resurrectable`` **zero**
   (:class:`GateReportTests`), and ``row_present: false`` must stay
   distinguishable from a row on the wrong team
   (:class:`IdentityResolutionTests`). One combined assertion would pass when only
   one of the two distinctions survived.
3. **The post-execution proof is the whole document, and it is falsifiable.**
   The instrument here is different from ``test_magic.py``'s, and the difference is
   not cosmetic: that slice's domain **writes**, so tampering rides its ``write``
   method. This one writes **nothing at all**, so a write-tampering harness would
   never fire and would report a green suite proving nothing. The instrument is
   therefore a repository whose **second read** is preceded by an on-disk edit --
   see :class:`PostConditionProofTests`, which isolates all five halves and states
   the one that cannot be isolated.
4. **The committed oracle is read as bytes and never re-captured**
   (:class:`CommittedOracleTests`). The fixture under
   ``tests/fixtures/godot-combat-actions/`` was archived by a delivered line on
   2026-10-05; re-running the capture would produce the same bytes for a different
   commit, and every figure asserted from it is therefore re-measured here from
   the committed files rather than inherited.
"""

from __future__ import annotations

import ast
import json
import re
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
from server_v1_combat import (
    ACTION,
    DEAD_HERO_LEDGER_PATH,
    IDENTITY_COMMITTED_FIELDS,
    LEDGER_TEAM,
    MAP_LOSE_ITEM_CALL_SITES,
    NONE_DEREFERENCE_FACTS,
    TEAM_ASYMMETRY,
    ZERO_CONSUMER_COMBAT_FIELDS,
    apply_combat,
)
from server_v1_content import CommittedContent
from server_v1_intent import (
    ADDRESSING_FIELDS,
    DESTRUCTION_KEYS,
    INTENT_OPERATION_FIELDS,
    INTENT_SCHEMAS,
    NO_OPERATION_FIELD_ACTIONS,
    NON_NEGATIVE_ADDRESSING,
    Intent,
    parse_intent,
)
from server_v1_outcomes import PRESERVED_COMBAT_BEHAVIOUR, CombatSuccess
from server_v1_refusals import REFUSAL_HTTP_STATUS, Refusal, RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES

#: A pinned instant.  Nothing in a transaction that destroys nothing depends on
#: it -- the preserved branch records no instant for this action -- but it is
#: passed anyway, because the service has a clock and reports it, and a test that
#: pinned none would let a future edit drop the field silently.
SERVICE_INSTANT = 1790705901

#: A committed unit whose ``resurrectable`` key is **present** -- the string
#: ``"1"``.  ``1001`` is Worker I.  Asserted against committed content in
#: :class:`CommittedUnitTableTests`, so a content change fails here rather than
#: turning every gate expectation into a coincidence.
RESURRECTABLE_UNIT = 1001

#: A committed unit whose ``resurrectable`` key is **absent**.  Three ids are:
#: 923 (Gorilla), 933 and 1176.  This is the identity the live phase drives,
#: because an absent key is the case that must stay distinguishable from a zero.
ABSENT_FLAG_UNIT = 923

#: A committed **building** id and the one committed **special** id.  Neither may
#: resolve as a unit: the three id spaces have zero overlap, and that is what makes
#: "name a committed unit row" a real constraint rather than a formality.
BUILDING_ID = 22
SPECIAL_ID = 1

#: The preserved branch's own destruction wire shape, carried verbatim.  Executing
#: ``combat_payload('resolve')`` at v0 returns ``{"attacker_units": [[0,0,1,0]]}``
#: with the trailing ``0`` being the payload builder's derived identity, and the
#: committed fixture step 7 destroyed **two** rows at v0's counterpart for
#: ``A=3, B=1``.  v0's reported ``destruction: 1`` is therefore an artefact of the
#: payload's construction and is **not** carried forward as a rule -- see
#: :meth:`DestructionRefusalTests.test_v0s_reported_one_is_an_artefact_and_is_not_carried`.
DESTRUCTION_SHAPE = [[0, 0, 3, 1]]

#: The committed fresh-player corpus, measured in :class:`CorpusTests` rather than
#: transcribed: 40 placed rows, 11 distinct item ids, **no unit row at all**, an
#: empty dead-hero ledger, and two teams.  These are the figures the design's
#: "row_present is an absence, not a refusal" decision rests on.
CORPUS_ROW_COUNT = 40
CORPUS_DISTINCT_ITEM_IDS = 11

#: The one committed fixture the oracle is read from.  Read as bytes.
ORACLE_ROOT = harness.REPO_ROOT / "tests" / "fixtures" / "godot-combat-actions"

#: The legacy runtime modules the zero-consumer census is measured over.  Named
#: rather than globbed: a glob would silently absorb a new root module and make
#: the census's scope drift without anything failing.  ``legacy_command_recorder``
#: is excluded on purpose -- it is an analysis tool, not a served module -- and its
#: exclusion is asserted in :class:`NoDerivationTests` so it cannot become silent.
LEGACY_MODULES = (
    "auctions.py",
    "bundle.py",
    "command.py",
    "constants.py",
    "engine.py",
    "get_game_config.py",
    "get_player_info.py",
    "server.py",
    "sessions.py",
    "version.py",
)
EXCLUDED_ROOT_MODULES = ("legacy_command_recorder.py",)

DOMAIN_SOURCE = harness.SERVICE_DIR / "server_v1_combat.py"
INTENT_SOURCE = harness.SERVICE_DIR / "server_v1_intent.py"
APP_SOURCE = harness.SERVICE_DIR / "server_v1_app.py"

#: "Leave this key out" -- distinct from carrying ``None``.
#:
#: The default for ``destruction`` cannot be ``None``, because ``None`` is itself one
#: of the shapes under test: the preserved branch's ``attacker_units`` list is walked
#: and each element is indexed, so ``None`` is a real request body value.  With a
#: ``None`` default, ``_body(destruction=None)`` silently **omitted** the key, and
#: the refusal test it belonged to saw a success payload and failed on a
#: ``subTest`` named ``value=None``.  A sentinel is the only way to say "absent"
#: without colliding with a value the request may legitimately carry.
ABSENT = object()


def _code_only(text: str) -> str:
    """Strip comments and string literals, leaving executable Python.

    A **two-state lexer**, not a regex, because the regular form desynchronises on
    an apostrophe inside a double-quoted string -- recorded in this repository when
    ``test_unit_behaviors`` hit it -- and because a dict key *is* a string literal,
    so a comment-aware regex that keeps strings cannot tell code from prose.  Every
    guard below that scans for a name depends on this being right, so
    :class:`LexerTests` proves it by planting both kinds of text.
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


def _qualified_functions(tree: ast.Module) -> Set[str]:
    """Declared functions as ``Class.method`` where a class owns them.

    A method contributes **only** its qualified name.  A first draft in this
    repository added the bare name for every function *and* the qualified name for
    every method, so the set measured larger than the module declares and the
    inventory pin had to name the surplus.  Collapsing a method to its bare name is
    also what would make ``__init__`` ambiguous about its owner.
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


#: The **whole** declared inventory of the combat domain module.  Thirteen, with
#: no class in the module, so qualified and unqualified names coincide -- and that
#: coincidence is asserted rather than assumed, because it is what lets one
#: helper serve both pins.
EXPECTED_COMBAT_FUNCTIONS = (
    "_changed_leaf_paths",
    "_checks",
    "_committed_report",
    "_destruction_refusal",
    "_destruction_report",
    "_gate_report",
    "_proof_refusal",
    "_refuse",
    "_repository_refusal",
    "_rows_report",
    "_serialise",
    "_unknown_unit",
    "apply_combat",
)

#: Stems an invented mechanism helper would carry.  Nineteen, and **substring**
#: rather than exact: ``godot-friends`` measured that an exact-name check passes a
#: helper merely *prefixed* with a reserved word, and ``godot-construction-assist``
#: measured the same for a case-sensitive one (``Friend_Of``).  This is the belt;
#: :class:`DomainInventoryTests`' inventory pin is the gate.
#:
#: The list is chosen so that **every delivered name is clean** against it.  The
#: obvious candidate ``destruction`` is deliberately absent: the module legitimately
#: owns ``_destruction_refusal`` and ``_destruction_report``, and adding the stem
#: would have forced a rename of correct code to satisfy a guard.  ``destroy`` is
#: present and ``destruction`` is not, because they are different words and the
#: invented helpers under test are spelled with the former.
RESERVED_COMBAT_STEMS = (
    "attack",
    "chance",
    "count",
    "credit",
    "damage",
    "defense",
    "destroy",
    "health",
    "hit",
    "honor",
    "kill",
    "ledger",
    "loss",
    "lost",
    "outcome",
    "pay",
    "payout",
    "resurrect",
    "victim",
)

#: The arithmetic nodes the domain must not contain anywhere (design D2, task 2.5).
#: Structural rather than editorial: "this slice derives nothing" is then
#: mechanically true rather than argued.
ARITHMETIC_NODES = (
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.LShift,
    ast.BitAnd,
)

#: The five proof checks, **in the enforced order**.  Order is load-bearing and the
#: reverse of line 3's: the leaf census runs *before* the whole-document
#: comparison here, because a leaf census names what moved while a byte comparison
#: can only say that something did.
PROOF_CHECK_ORDER = (
    "identity_resolved_to_reported_row",
    "reported_gates_match_content_and_state",
    "no_leaf_path_changed",
    "whole_document_unchanged",
    "resources_unchanged",
)


class LexerTests(unittest.TestCase):
    """The two-state lexer, proved by planting both kinds of text."""

    def test_a_comment_is_removed_and_its_code_is_kept(self) -> None:
        planted = "x = 1  # damage_for(unit)\ny = 2\n"
        stripped = _code_only(planted)
        self.assertNotIn("damage_for", stripped)
        self.assertIn("x = 1", stripped)
        self.assertIn("y = 2", stripped)

    def test_a_string_literal_is_replaced_and_its_code_is_kept(self) -> None:
        planted = "name = 'destroy_one_row'\ncount = len(rows)\n"
        stripped = _code_only(planted)
        self.assertNotIn("destroy_one_row", stripped)
        self.assertIn('""', stripped)
        self.assertIn("count = len(rows)", stripped)

    def test_a_name_inside_a_docstring_cannot_satisfy_a_guard(self) -> None:
        planted = '"""honor_payout(honor) is what this module does not do."""\nvalue = 1\n'
        self.assertNotIn("honor_payout", _code_only(planted))

    def test_an_apostrophe_inside_a_double_quoted_string_does_not_desynchronise(
        self,
    ) -> None:
        """The defect this lexer exists to avoid.

        ``text[index : index + 3] == quote * 3`` is checked on the *opening* quote
        only for the triple form; a naive implementation that treats an
        apostrophe inside a double-quoted string as an opening single quote blanks
        everything after it, and a guard scanning the remainder then reports zero
        findings and passes.  The planted text therefore has real code on **both**
        sides of the apostrophe.
        """
        planted = 'note = "it isn\'t here"\nafter = damage_for(unit)\n'
        stripped = _code_only(planted)
        self.assertIn("after =", stripped)
        self.assertIn("damage_for", stripped)


class CommittedUnitTableTests(unittest.TestCase):
    """Task 2.2 and 2.6: the committed figures, re-measured every run."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = load_content(harness.REPO_ROOT)

    def test_the_committed_unit_table_holds_four_hundred_and_twenty_nine_rows(self) -> None:
        self.assertEqual(429, len(self.content.unit_ids()))
        self.assertEqual(429, len(self.content.unit_rows()))

    def test_every_unit_row_declares_the_unit_type_column(self) -> None:
        for row in self.content.unit_rows():
            self.assertEqual("u", row.get("type"), row.get("id"))

    def test_the_three_committed_id_spaces_have_zero_overlap(self) -> None:
        """Re-derived every run rather than asserted as a constant.

        This is what makes ``unaddressable_row`` a real constraint: a building id
        and the one special id must be refused for the *same measured reason* as a
        nonsense number, not by a special case.
        """
        units = set(self.content.unit_ids())
        buildings = set(self.content.ids_for_type("b"))
        specials = set(self.content.ids_for_type("l"))
        self.assertEqual(470, len(buildings))
        self.assertEqual(1, len(specials))
        self.assertEqual(set(), units & buildings)
        self.assertEqual(set(), units & specials)
        self.assertEqual(set(), buildings & specials)

    def test_the_id_column_is_a_string_and_the_reader_keyed_on_it(self) -> None:
        """``legacy_id`` is the committed ``id`` column, not the array position.

        Asserted because a reader that keyed on ``enumerate`` position instead
        would resolve a *different* unit for every id above 1001 and nothing else
        in this file would notice.
        """
        row = self.content.unit_row(RESURRECTABLE_UNIT)
        self.assertIsNotNone(row)
        self.assertEqual(str(RESURRECTABLE_UNIT), row.get("id"))
        self.assertEqual("Worker I", row.get("name"))

    def test_resurrectable_is_present_on_four_hundred_and_twenty_six_units(self) -> None:
        present = [
            unit_id
            for unit_id in self.content.unit_ids()
            if self.content.unit_flag(unit_id, "resurrectable") is not None
        ]
        self.assertEqual(426, len(present))

    def test_the_key_is_absent_on_exactly_three_units(self) -> None:
        absent = [
            unit_id
            for unit_id in self.content.unit_ids()
            if self.content.unit_flag(unit_id, "resurrectable") is None
        ]
        self.assertEqual([923, 933, 1176], sorted(absent))

    def test_an_absent_key_is_not_a_recorded_zero(self) -> None:
        """Task 2.3, the distinction the whole gate report rests on.

        ``engine.py:159-160`` returns ``False`` on an absent key rather than
        reading one, so ``None`` and ``False`` are different facts about the
        committed row and the reader must keep them different.
        """
        self.assertIsNone(self.content.unit_flag(ABSENT_FLAG_UNIT, "resurrectable"))
        self.assertIsNone(
            self.content.unit_flag_is_positive(ABSENT_FLAG_UNIT, "resurrectable")
        )
        self.assertNotEqual(False, self.content.unit_flag(ABSENT_FLAG_UNIT, "resurrectable"))

    def test_the_only_recorded_value_is_the_string_one(self) -> None:
        """The committed encoding is a **string**, and it is never a truthiness test.

        A bare truthiness check would answer ``True`` for the committed ``"0"``,
        because a non-empty String is truthy in every language this project has run.
        The flag is therefore compared as a number, exactly as the preserved helper
        does.
        """
        values = {
            self.content.unit_flag(unit_id, "resurrectable")
            for unit_id in self.content.unit_ids()
            if self.content.unit_flag(unit_id, "resurrectable") is not None
        }
        self.assertEqual({"1"}, values)
        self.assertTrue(all(isinstance(value, str) for value in values))

    def test_the_flag_lives_inside_the_embedded_json_properties_string(self) -> None:
        """A correction to the design's and the task's wording, measured.

        Neither the design nor task 2.3 places ``resurrectable`` at the top level
        of the committed row; it lives inside the ``properties`` column, which the
        committed table stores as an **embedded JSON string**.  Asserted here so the
        correction cannot be lost, and so a future reader that looked for a
        top-level column would fail here rather than silently read ``None``.
        """
        row = self.content.unit_row(RESURRECTABLE_UNIT)
        self.assertIsNone(row.get("resurrectable"))
        properties = self.content.unit_properties(RESURRECTABLE_UNIT)
        self.assertIsInstance(properties, dict)
        self.assertEqual("1", properties["resurrectable"])
        self.assertIsInstance(row.get("properties"), str)

    def test_no_committed_building_carries_the_key(self) -> None:
        """0 of 470, re-derived rather than inherited.

        The counterpart of the unit-side census, and the reason the gate report can
        say an identity with no unit row has no committed ``resurrectable`` either.
        """
        carriers = [
            building_id
            for building_id in self.content.ids_for_type("b")
            if isinstance(self.content.item(building_id), dict)
            and isinstance(self.content.item(building_id).get("properties"), str)
            and "resurrectable" in self.content.item(building_id)["properties"]
        ]
        self.assertEqual([], carriers)

    def test_the_nine_reported_columns_are_top_level_strings_on_the_row(self) -> None:
        """Every column the response reports verbatim exists and is a string."""
        row = self.content.unit_row(RESURRECTABLE_UNIT)
        for field in ZERO_CONSUMER_COMBAT_FIELDS:
            self.assertIsInstance(row.get(field), str, field)

    def test_an_identity_no_committed_row_carries_resolves_to_nothing(self) -> None:
        for unit_id in (0, -1, 1, 5, 22, 1432, 99999):
            with self.subTest(unit_id=unit_id):
                self.assertIsNone(self.content.unit_row(unit_id))

    def test_the_committed_unit_id_space_is_not_contiguous(self) -> None:
        """Recorded because it is why ``unit_id`` is not clamped.

        Two ids below 1000 (923 and 933) and a run from 1001 mean a positional
        clamp would resolve some ids to a different unit rather than to nothing,
        which is exactly the ambiguity the refusal avoids.
        """
        unit_ids = self.content.unit_ids()
        self.assertEqual(923, min(unit_ids))
        self.assertEqual(1431, max(unit_ids))
        self.assertNotEqual(list(range(min(unit_ids), max(unit_ids) + 1)), list(unit_ids))


class NoDerivationTests(unittest.TestCase):
    """Task 2.5 and design D2: no arithmetic node exists in the module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        cls.code = _code_only(cls.source)
        cls.tree = ast.parse(cls.source.replace("\r\n", "\n"), filename=str(DOMAIN_SOURCE))

    def test_the_module_declares_no_arithmetic_node_anywhere(self) -> None:
        found = sorted(
            "%s at line %d" % (type(node).__name__, getattr(node, "lineno", 0))
            for node in ast.walk(self.tree)
            if isinstance(node, ARITHMETIC_NODES)
        )
        self.assertEqual([], found)

    def test_the_arithmetic_node_list_is_pinned_against_the_ast_module(self) -> None:
        """The guard's own target list, so a node class cannot be dropped from it.

        Every class named is a real ``ast`` node type: a typo in this tuple would
        otherwise turn the guard into a scan for a class that never matches, and
        ``test_the_module_declares_no_arithmetic_node_anywhere`` would pass
        vacuously forever.
        """
        for node_type in ARITHMETIC_NODES:
            self.assertTrue(issubclass(node_type, ast.AST), node_type.__name__)
        self.assertEqual(
            7,
            len(ARITHMETIC_NODES),
            "a node class was removed from the guard's own list",
        )

    def test_the_guard_would_catch_a_planted_arithmetic_node(self) -> None:
        """The guard is **tested**, not trusted.

        A planted ``unit_id // 2`` inside the module's own source is scanned with
        the same walk.  ``test_base.gd``'s GDScript equivalent recorded six silent
        passes from an untested guard, and the shape is identical: a guard that
        cannot fail is not a guard.
        """
        planted = ast.parse("def derived(unit_id):\n    return unit_id // 2\n")
        found = [node for node in ast.walk(planted) if isinstance(node, ARITHMETIC_NODES)]
        self.assertEqual(1, len(found))
        self.assertIs(ast.FloorDiv, type(found[0]))

    def test_the_module_never_converts_a_committed_combat_column_to_a_number(self) -> None:
        """The upstream guard: reading a column is the only way to value it.

        Stronger than an arithmetic-node check, because a module could compute a
        count with a library call and no ``*`` or ``//``.
        """
        for field in ZERO_CONSUMER_COMBAT_FIELDS:
            with self.subTest(field=field):
                self.assertNotIn("int(%s" % field, self.code)
                self.assertNotIn("float(%s" % field, self.code)

    def test_the_reported_field_table_is_pinned_against_what_the_module_reads(self) -> None:
        """A member added to the table has to be a member the module touches.

        Otherwise the table could grow into a list of columns the response claims
        to report while no code path ever reads them, and the "reported verbatim"
        claim would become an assertion about a literal.
        """
        # Read over the **raw source**, not ``self.code``: the module names these
        # columns as string literals inside ZERO_CONSUMER_COMBAT_FIELDS, and the
        # two-state lexer blanks every literal -- so a code-only scan for a column
        # name can only ever report zero.  That was the defect in the first draft.
        for field in ZERO_CONSUMER_COMBAT_FIELDS:
            with self.subTest(field=field):
                self.assertIn('"%s"' % field, self.source)
        self.assertEqual(9, len(ZERO_CONSUMER_COMBAT_FIELDS))
        self.assertTrue(
            set(ZERO_CONSUMER_COMBAT_FIELDS) <= set(self.content_row_fields()),
            "the reported table names a column the committed unit row does not carry",
        )

    def content_row_fields(self) -> Set[str]:
        content = load_content(harness.REPO_ROOT)
        row = content.unit_row(RESURRECTABLE_UNIT)
        return set(row or {})

    def test_the_zero_consumer_census_is_re_derived_and_the_attack_trap_is_named(
        self,
    ) -> None:
        """Task 10.2: ``attack`` is the trap, and reporting ``12`` without the
        sentence is the mistake.

        Measured over the ten declared legacy runtime modules: ``attack`` has
        **12** whole-file occurrences, **5** code-only ones, and **0** whole-word
        ones -- every one of the twelve inside a longer identifier
        (``end_attack``, ``attacker``, ``attacker_units``).  The other eight
        columns have **no** occurrence in any view.  Both halves are asserted
        together because a census reporting only one of them reads as a much
        stronger statement than it is.
        """
        measured = {field: self._legacy_census(field) for field in ZERO_CONSUMER_COMBAT_FIELDS}
        self.assertEqual(
            {"whole_file": 12, "code_only": 5, "whole_word": 0},
            measured["attack"],
        )
        for field in ZERO_CONSUMER_COMBAT_FIELDS:
            if field == "attack":
                continue
            with self.subTest(field=field):
                self.assertEqual(
                    {"whole_file": 0, "code_only": 0, "whole_word": 0},
                    measured[field],
                )

    def _legacy_census(self, field: str) -> Dict[str, int]:
        pattern = re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(field))
        whole_file = code_only = whole_word = 0
        for name in LEGACY_MODULES:
            text = (harness.REPO_ROOT / name).read_text(encoding="utf-8")
            whole_file += text.count(field)
            code_only += _code_only(text).count(field)
            whole_word += len(pattern.findall(text))
        return {"whole_file": whole_file, "code_only": code_only, "whole_word": whole_word}

    def test_every_attack_occurrence_is_inside_a_longer_identifier(self) -> None:
        """The reason the whole-word count is zero, asserted directly.

        Without this the census would report ``0`` and a reader could not tell a
        field nobody reads from a field whose name is a permanent substring of four
        other names -- which is the difference between a census and a grep.

        **The boundary test is a conjunction, and getting it wrong is the trap this
        method exists to close.**  An occurrence is a standalone token when
        *neither* side of it is an identifier character.  The first draft asserted
        the negation of a four-way **disjunction**, which requires both sides to be
        non-identifiers to pass -- so ``end_attack``, joined by an underscore on the
        left only, failed here even though it is exactly the case the census is
        about.  Underscore is an identifier character, so ``end_attack`` and
        ``attacker_units`` are longer identifiers and pass, and a genuine
        standalone ``attack`` would fail on either side.

        Scanned over **all ten** legacy modules, not ``command.py`` alone, so the
        occurrence count here is the census's own count and the two cannot drift.
        Measured split: ``command.py`` 11, ``server.py`` 1 (inside
        ``"flash_reload_attack"``), 12 in total.  An earlier draft scanned only
        ``command.py`` and asserted 12, so it failed on the count while every
        boundary assertion passed -- which is exactly the signal that the scope,
        not the boundary rule, was wrong.
        """
        checked = 0
        per_module: Dict[str, int] = {}
        for name in LEGACY_MODULES:
            text = (harness.REPO_ROOT / name).read_text(encoding="utf-8")
            found = text.replace("\r\n", "\n").count("attack")
            if found:
                per_module[name] = found
            for line in text.replace("\r\n", "\n").split("\n"):
                for match in re.finditer("attack", line):
                    checked += 1
                    before = line[match.start() - 1] if match.start() else ""
                    after = line[match.end()] if match.end() < len(line) else ""
                    left_bare = not (before.isalnum() or before == "_")
                    right_bare = not (after.isalnum() or after == "_")
                    self.assertFalse(
                        left_bare and right_bare,
                        "%s: attack appears as a standalone token on: %s"
                        % (name, line.strip()),
                    )
        self.assertEqual({"command.py": 11, "server.py": 1}, per_module)
        self.assertEqual(12, checked, "the census and this method disagree")
        census = self._legacy_census("attack")
        self.assertEqual(
            checked,
            census["whole_file"],
            "the whole-file census and this method disagree",
        )
        self.assertEqual(0, census["whole_word"], "a standalone attack exists after all")

    def test_the_census_scope_names_every_root_module_or_names_the_exclusion(self) -> None:
        """A glob would let the census's scope drift without anything failing."""
        roots = {path.name for path in harness.REPO_ROOT.glob("*.py")}
        self.assertEqual(
            set(LEGACY_MODULES) | set(EXCLUDED_ROOT_MODULES),
            roots,
            "a root module appeared or vanished; name it or exclude it explicitly",
        )


class NoInventedRuleTests(unittest.TestCase):
    """Task 3.3, 3.5 and design D3: nothing is invented, reconciled, or derived."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        cls.code = _code_only(cls.source)

    def test_the_team_asymmetry_is_recorded_as_data_and_never_reconciled(self) -> None:
        self.assertIs(False, TEAM_ASYMMETRY["reconciled"])
        for key in ("selector_test", "ledger_test", "consequence", "why_not_reconciled"):
            self.assertIsInstance(TEAM_ASYMMETRY[key], str)
            self.assertTrue(TEAM_ASYMMETRY[key])
        self.assertIn("engine.py:221", TEAM_ASYMMETRY["selector_test"])
        self.assertIn("engine.py:151", TEAM_ASYMMETRY["ledger_test"])

    def test_the_ledger_team_is_the_recorded_literal_and_is_never_a_derivation(self) -> None:
        """``LEDGER_TEAM`` is compared against a stored slot, not a committed column."""
        self.assertEqual(1, LEDGER_TEAM)
        self.assertIn("LEDGER_TEAM", self.code)
        # No committed content column names a team value, so nothing in the module
        # may read one: a team reader would be inventing the correspondence.
        self.assertNotIn("team_value", self.code)

    def test_the_absent_value_facts_split_established_from_unknown(self) -> None:
        """Task 3.5 and 9.3, restated.

        The binding selection record states the reachability more weakly than the
        evidence supports.  What is **established** is that both shapes execute and
        answer HTTP 500 with a byte-identical save; what remains **unknown** is
        whether a real client ever sent either, because the Flash client was never
        executed and every committed fixture payload is crafted.
        """
        self.assertIs(False, NONE_DEREFERENCE_FACTS["representable_in_v1"])
        self.assertEqual("established by execution", NONE_DEREFERENCE_FACTS["reachability"])
        self.assertEqual("unknown", NONE_DEREFERENCE_FACTS["did_a_real_client_send_either"])
        self.assertIs(True, NONE_DEREFERENCE_FACTS["a_raise_discards_the_whole_save"])
        self.assertIn("command.py:30,32", NONE_DEREFERENCE_FACTS["a_raise_discards_evidence"])

    def test_the_two_none_dereferences_are_named_on_the_wire(self) -> None:
        """The wire text abbreviates the second line number as ``:874``.

        An earlier draft asserted ``"command.py:874"`` and failed: the committed
        value spells the pair once (``command.py:866``) and abbreviates the second
        (``:874``).  Asserting the exact spelling is the point -- the value is
        **carried verbatim** onto the refusal body, so a reader parsing the line
        numbers out of it needs the text that is actually sent.
        """
        self.assertIn("absent_value", PRESERVED_COMBAT_BEHAVIOUR)
        text = PRESERVED_COMBAT_BEHAVIOUR["absent_value"]
        self.assertIn("command.py:866 and :874", text)
        self.assertNotIn("command.py:874", text, "the committed text spells it differently")
        self.assertIn("established by execution", text)

    def test_map_lose_item_has_two_call_sites_and_this_line_names_the_module(self) -> None:
        """Task 9.12: **two** branches reach **one** helper.

        ``godot-unit-behaviors`` called the dead-hero ledger's entry "three doors",
        counting ``push_dead_unit``'s own two callers and ``map_lose_item``
        separately.  That archived line is **not** edited; the discrepancy is
        recorded here and the module is named at each call site so neither figure
        is inherited blindly.
        """
        self.assertEqual(2, len(MAP_LOSE_ITEM_CALL_SITES))
        self.assertEqual(
            (("command.py", "796", "end_quest"), ("command.py", "872", "end_attack")),
            MAP_LOSE_ITEM_CALL_SITES,
        )
        for module, line, branch in MAP_LOSE_ITEM_CALL_SITES:
            text = (harness.REPO_ROOT / module).read_text(encoding="utf-8").replace("\r\n", "\n")
            lines = text.split("\n")
            # The branch head is spelled ``elif cmd == "<name>":``, and the call
            # site must be inside that branch's own span -- so the span is cut
            # from the head to the next ``elif``/``if command`` at the same
            # indent, not merely searched for anywhere in the file.
            heads = [
                index
                for index, value in enumerate(lines)
                if value.strip() == 'elif cmd == "%s":' % branch
            ]
            self.assertEqual(1, len(heads), "%s head" % branch)
            head = heads[0]
            indent = len(lines[head]) - len(lines[head].lstrip())
            end = len(lines)
            for index in range(head + 1, len(lines)):
                stripped = lines[index].strip()
                if not stripped or stripped.startswith("#"):
                    continue
                width = len(lines[index]) - len(lines[index].lstrip())
                if width == indent and stripped.startswith(("if ", "elif ", "def ")):
                    end = index
                    break
            span = "\n".join(lines[head:end])
            self.assertIn("map_lose_item(", span, "%s does not call the helper" % branch)
            self.assertEqual(
                int(line) - 1,
                next(
                    index
                    for index, value in enumerate(lines[head:end], start=head)
                    if "map_lose_item(" in value
                ),
                "the recorded call-site line moved in %s" % module,
            )

    def test_the_dead_hero_ledger_path_is_named_as_a_pointer(self) -> None:
        self.assertEqual("/privateState/deadHeroes", DEAD_HERO_LEDGER_PATH)

    def test_no_helper_credits_or_debits_the_dead_hero_ledger(self) -> None:
        """The absence, asserted at the name level against a *reserved* list.

        ``ledger`` is a reserved stem, so a helper named ``credit_ledger`` is
        already caught by :class:`DomainInventoryTests`; this assertion is the
        reader-facing half -- the module's own text must not contain a write to the
        ledger key at all.
        """
        self.assertNotIn("deadHeroes", self.code)
        self.assertNotIn("push_dead_unit", self.code)

    def test_the_module_names_no_committed_combat_rule(self) -> None:
        """A named rule would be a resolver, and there is none.

        Asserted over the code (not the prose), so a comment explaining why there
        is no rule cannot satisfy it and a rule cannot hide behind a comment.
        """
        for token in ("attack_interval", "attack_range", "best_against_mult"):
            with self.subTest(token=token):
                self.assertNotIn('"%s"' % token, self.code)


class SeededFixture(unittest.TestCase):
    """A disposable corpus plus a byte baseline.

    ``_declared_seed`` is overridden by the subclasses that need a different
    starting state; the default leaves the committed fresh-player corpus
    untouched, which is itself the interesting case for this slice.
    """

    def setUp(self) -> None:
        self.content = load_content(harness.REPO_ROOT)
        self._seed = self._declared_seed()
        self.corpus = build_corpus(mutate=self._seed)
        self.addCleanup(remove_corpus, self.corpus)
        self.repository = FilesystemSaveRepository(self.corpus)
        self.player = seed_player_id()

    def _declared_seed(self) -> Callable[[Dict[str, Any]], None]:
        return lambda document: None

    # ----------------------------------------------------------- convenience --
    def _seed_row(self, unit_id: int, team: Any, key: str = "999") -> None:
        """Place one recorded row carrying ``unit_id`` on ``team``.

        The committed row shape is **eight** slots, slot 0 the item id and slot 7
        the team; a first draft wrote nine and the repository refused the document,
        which surfaced as a ``Refusal`` rather than as the shape error it was.
        """
        document = self.repository.read(self.player)
        items = document.snapshot()["maps"][0]["items"]
        items[key] = [unit_id, 10, 20, 0, 0, [], {}, team]
        self._write_items(items)

    def _write_items(self, items: Dict[str, Any]) -> None:
        document = self.repository.read(self.player)
        snapshot = document.snapshot()
        snapshot["maps"][0]["items"] = items
        self._replace_document(snapshot)

    def _replace_document(self, snapshot: Dict[str, Any]) -> None:
        path = self.repository.read(self.player).path
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(snapshot, stream, indent=4)

    def _intent(
        self,
        unit_id: Optional[int] = ABSENT_FLAG_UNIT,
        player: Optional[str] = None,
        destruction: Any = ABSENT,
    ) -> Intent:
        parsed = parse_intent(
            ACTION,
            self._body(
                unit_id=ABSENT_FLAG_UNIT if unit_id is None else unit_id,
                player_id=self.player if player is None else player,
                destruction=destruction,
            ),
        )
        self.assertIsInstance(parsed, Intent)
        return parsed  # type: ignore[return-value]

    def _body(
        self,
        unit_id: Any = ABSENT_FLAG_UNIT,
        player_id: Any = "p",
        destruction: Any = ABSENT,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"player_id": player_id, "unit_id": unit_id}
        if destruction is not ABSENT:
            body["attacker_units"] = destruction
        return body

    def _apply(self, intent: Intent, content: Any = None) -> Any:
        return apply_combat(
            intent,
            self.content if content is None else content,
            self.repository,
            SERVICE_INSTANT,
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

    def _assert_success(self, intent: Optional[Intent] = None) -> CombatSuccess:
        outcome = self._apply(self._intent() if intent is None else intent)
        self.assertIsInstance(outcome, CombatSuccess)
        return outcome  # type: ignore[return-value]

    def _save_path(self) -> Path:
        return self.repository.read(self.player).path

    def _resources(self) -> Dict[str, int]:
        return self.repository.read(self.player).resources()

    def _tampering_read_repository(self, tamper: Callable[[Dict[str, Any]], None]):
        """A repository whose **second read** is preceded by an on-disk edit.

        **This is the whole instrument, and it differs from ``test_magic.py``'s on
        purpose.**  That slice's domain writes, so tampering rides its ``write``
        method.  This one has **no write path at all** -- there is no mutator
        anywhere in the declared inventory -- so a write-tampering harness would
        never fire once and the suite would go green while proving nothing.

        ``apply_combat`` reads the store twice (once for the snapshot, once to read
        it back), and the whole-document proof compares the two.  Tampering
        immediately before the second parse is therefore the only way to produce the
        exact post-state a misbehaving store would, and it is what makes the proof
        falsifiable rather than vacuous.
        """
        inner = self.repository
        path = self._save_path()
        reads = [0]

        class _Tampering:
            def player_ids(self) -> Tuple[str, ...]:
                return inner.player_ids()

            def read(self, player_id: str) -> Any:
                reads[0] += 1
                if reads[0] == 2:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    tamper(data)
                    with open(path, "w", encoding="utf-8", newline="\n") as stream:
                        json.dump(data, stream, indent=4)
                return inner.read(player_id)

            def write(self, document: Any) -> None:  # pragma: no cover - unused
                inner.write(document)

        return _Tampering()


class DomainInventoryTests(unittest.TestCase):
    """Task 6.5: the whole-inventory pin, and the reserved-stem belt around it.

    The pin is the gate because it is **exact**: a helper at all -- invented,
    refactored or borrowed -- changes the set and fails the suite.  The stem check
    is the belt: it is what names *why* an addition would be wrong, and it is kept
    only because a name-shaped guard survives being bypassed.

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

    def test_the_whole_declared_inventory_is_exactly_these_thirteen(self) -> None:
        self.assertEqual(set(EXPECTED_COMBAT_FUNCTIONS), self.qualified)
        self.assertEqual(13, len(self.qualified))

    def test_qualified_and_unqualified_names_coincide_because_no_class_owns_a_helper(
        self,
    ) -> None:
        """The one helper that lets a single list serve both pins is *asserted*.

        A future edit that introduced a class would silently make
        :meth:`test_the_whole_declared_inventory_is_exactly_these_thirteen` pass
        while the other three absence guards kept reading bare names.
        """
        self.assertEqual(self.qualified, self.unqualified)
        self.assertEqual([], [node.name for node in self.tree.body if isinstance(node, ast.ClassDef)])

    def test_no_declared_function_name_carries_a_reserved_stem(self) -> None:
        """Direction one: a name containing a stem is an offender."""
        offenders = sorted(
            "%s carries %s" % (name, stem)
            for name in self.qualified
            for stem in RESERVED_COMBAT_STEMS
            if stem in name.lower()
        )
        self.assertEqual([], offenders)

    def test_the_reserved_stem_list_cannot_be_satisfied_by_emptying_itself(self) -> None:
        """Direction two, and the guard's own non-vacuity proof.

        Two separate things are asserted, because either alone is worthless:

        * the stem list is **itself pinned**, so a shortening -- the edit someone
          makes when a legitimate helper name collides with a stem -- fails here;
        * the predicate **does fire** over planted names, so a stem list that
          stopped matching leaves the direction-one test green on nothing.
        """
        self.assertEqual(19, len(RESERVED_COMBAT_STEMS))
        self.assertEqual(
            (
                "attack", "chance", "count", "credit", "damage", "defense",
                "destroy", "health", "hit", "honor", "kill", "ledger", "loss",
                "lost", "outcome", "pay", "payout", "resurrect", "victim",
            ),
            RESERVED_COMBAT_STEMS,
        )
        planted = (
            "destruction_count_for",      # task 6.5 probe one, trips `count`
            "honor_payout",               # task 6.5 probe two, trips two stems
            "unit_damage_calculator",     # the invented damage rule
            "Hit_Chance_For",             # case-folded
            "credit_ledger",              # suffixed helper wearing a stem
            "next_lost_row",              # a longer stem inside a shorter name
            "resolve_Outcome",            # case-folded outcome
        )
        for name in planted:
            with self.subTest(name=name):
                self.assertTrue(
                    any(stem in name.lower() for stem in RESERVED_COMBAT_STEMS),
                    "the planted positive control did not fire: %s" % name,
                )

    def test_the_inventory_gate_catches_a_helper_that_borrows_no_reserved_word(self) -> None:
        """The third task-6.5 probe, run against the **same predicate** the suite uses.

        ``resolve_unit_outcome`` was going to borrow nothing, and its
        ``outcome`` makes that untrue -- the planted name below is the honest one,
        a bare identifier with no stem in it at all.  It is caught by the inventory
        pin alone, which is the measurement that shows the pin is the real gate and
        the stem list the belt.
        """
        planted = "resolve_actor_pair"
        self.assertFalse(any(stem in planted.lower() for stem in RESERVED_COMBAT_STEMS))
        self.assertNotIn(planted, self.qualified)

    def test_a_stem_cannot_be_hidden_by_a_comment_naming_it(self) -> None:
        """The stem scan reads the **module's own name inventory**, not its prose.

        A comment saying ``# honor_payout is refused`` must not make the stem list
        report an offender, and must not make a real offender invisible either.
        Asserted both ways in one method, because each alone is a check that can
        pass for the wrong reason.
        """
        self.assertNotIn("honor_payout", self.qualified)
        self.assertIn("honor_payout", self.source)  # the prose may mention it


class CorpusTests(SeededFixture):
    """The committed fresh-player corpus, and why it makes this case interesting."""

    def test_the_fresh_corpus_places_no_unit_row_at_all(self) -> None:
        """Task 3.2's measured premise: the refusal alternative would be unreachable.

        ``tests/saves/fresh-player.json`` places 40 rows across 11 distinct item
        ids, every one a committed **building**.  A slice that refused an identity
        with no row would therefore have **no** exercisable success on the
        committed corpus and the live phase would have nothing to drive.
        """
        snapshot = self.repository.read(self.player).snapshot()
        items = snapshot["maps"][0]["items"]
        self.assertEqual(CORPUS_ROW_COUNT, len(items))
        ids = sorted({row[0] for row in items.values()})
        self.assertEqual(CORPUS_DISTINCT_ITEM_IDS, len(ids))
        self.assertEqual([], [i for i in ids if self.content.unit_row(i) is not None])
        self.assertEqual([22, 23, 26, 905, 907, 908, 909, 928, 929, 930, 931], ids)

    def test_the_fresh_corpus_ledger_is_empty_and_the_ledger_key_is_present(self) -> None:
        snapshot = self.repository.read(self.player).snapshot()
        self.assertIn("deadHeroes", snapshot["privateState"])
        self.assertEqual({}, snapshot["privateState"]["deadHeroes"])

    def test_the_fresh_corpus_carries_two_teams(self) -> None:
        """Keys 1-20 are team 1 and 21-40 team 3, which is what makes the asymmetry
        exercisable *in principle* -- and still unexercisable for a unit, because
        the corpus places no unit row at all."""
        items = self.repository.read(self.player).snapshot()["maps"][0]["items"]
        self.assertEqual({1, 3}, {row[7] for row in items.values()})

    def test_the_fresh_corpus_carries_the_seven_stored_resources(self) -> None:
        resources = self._resources()
        self.assertEqual(sorted(STORED_RESOURCE_NAMES), sorted(resources))
        self.assertEqual(
            {
                "xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
                "steel": 2000, "cash": 5, "mana": 0,
            },
            resources,
        )

    def test_a_row_seeded_onto_team_three_is_reported_and_not_destroyed(self) -> None:
        """The asymmetry is reportable even though it is unexercisable in game."""
        self._seed_row(RESURRECTABLE_UNIT, 3)
        success = self._assert_success(self._intent(unit_id=RESURRECTABLE_UNIT))
        gate = success.gates["gate_one_team"]
        self.assertEqual(3, gate["recorded_team"])
        self.assertIs(False, gate["every_row_would_pass"])
        self.assertEqual(CORPUS_ROW_COUNT + 1, len(self._snapshot_items()))
        self.assertEqual(self._pre_bytes(), corpus_save_bytes(self.corpus))

    def _snapshot_items(self) -> Dict[str, Any]:
        return self.repository.read(self.player).snapshot()["maps"][0]["items"]


class IdentityResolutionTests(SeededFixture):
    """Task 3.2: an identity with no row is an **absence**, and it succeeds."""

    def test_a_committed_identity_with_no_recorded_row_succeeds(self) -> None:
        outcome = self._apply(self._intent())
        self.assertIsInstance(outcome, CombatSuccess)
        self.assertEqual(ABSENT_FLAG_UNIT, outcome.unit_id)

    def test_the_row_absence_is_reported_as_an_absence_not_as_a_zero(self) -> None:
        gate = self._assert_success().gates["gate_one_team"]
        self.assertIs(False, gate["row_present"])
        self.assertEqual(0, gate["row_count"])
        self.assertEqual([], gate["rows"])
        self.assertIsNone(gate["recorded_team"])
        self.assertIsNone(gate["every_row_would_pass"])
        self.assertIsNone(gate["any_row_would_pass"])

    def test_an_absent_row_is_distinguishable_from_a_row_on_the_wrong_team(self) -> None:
        """The two ways a team verdict can be non-positive, kept apart.

        ``False`` means a recorded row exists and fails ``== 1``; **``None``** means
        there is no row at all.  An earlier draft asserted ``False`` for both and
        failed on the absent half -- which is the whole point of the test, since
        collapsing them would let a reader report a committed fact about a row that
        does not exist.  The ``row_present`` flag carries the same distinction and is
        asserted as the second, independent channel.
        """
        absent = self._assert_success().gates["gate_one_team"]
        self._seed_row(RESURRECTABLE_UNIT, 3)
        wrong_team = self._assert_success(
            self._intent(unit_id=RESURRECTABLE_UNIT)
        ).gates["gate_one_team"]

        self.assertIsNone(absent["every_row_would_pass"], "an absent row reported a verdict")
        self.assertIsNone(absent["any_row_would_pass"])
        self.assertIsNone(absent["recorded_team"])
        self.assertIs(False, absent["row_present"])
        self.assertEqual([], absent["rows"])

        self.assertIs(False, wrong_team["every_row_would_pass"], "a team-3 row passed the gate")
        self.assertIs(False, wrong_team["any_row_would_pass"])
        self.assertEqual(3, wrong_team["recorded_team"])
        self.assertIs(True, wrong_team["row_present"])
        self.assertEqual(1, len(wrong_team["rows"]))

        self.assertNotEqual(
            absent["every_row_would_pass"],
            wrong_team["every_row_would_pass"],
            "the two non-positive verdicts collapsed into one",
        )

    def test_the_committed_identity_is_reported_verbatim_with_its_keying_stated(self) -> None:
        committed = self._assert_success().committed
        row = self.content.unit_row(ABSENT_FLAG_UNIT)
        for field in IDENTITY_COMMITTED_FIELDS:
            self.assertEqual(row.get(field), committed[field])
        self.assertEqual(ABSENT_FLAG_UNIT, committed["resolved_id"])
        self.assertIn("legacy_id", committed["id_keyed_by"])
        self.assertIn("zero overlap", committed["resolved_against"])

    def test_the_nine_combat_columns_are_reported_verbatim_and_never_read(self) -> None:
        committed = self._assert_success().committed
        row = self.content.unit_row(ABSENT_FLAG_UNIT)
        self.assertEqual(9, len(committed["combat_fields"]))
        for field in ZERO_CONSUMER_COMBAT_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(row.get(field), committed["combat_fields"][field])
                self.assertIsInstance(committed["combat_fields"][field], str)
        self.assertEqual(0, committed["combat_fields_legacy_consumers"])
        self.assertIn("strings", committed["combat_fields_stored_as"])

    def test_the_instant_is_the_service_clock(self) -> None:
        self.assertEqual(SERVICE_INSTANT, self._assert_success().instant)

    def test_the_whole_document_is_byte_identical_across_the_transaction(self) -> None:
        before = self._pre_bytes()
        self._assert_success()
        self.assertEqual(before, corpus_save_bytes(self.corpus))


class GateReportTests(SeededFixture):
    """Task 2.3 and design D3: both gates, reported, never enforced."""

    def test_the_team_gate_is_reported_per_row_and_aggregated_over_all_of_them(self) -> None:
        self._seed_row(RESURRECTABLE_UNIT, 1, key="998")
        self._seed_row(RESURRECTABLE_UNIT, 3, key="999")
        gate = self._assert_success(
            self._intent(unit_id=RESURRECTABLE_UNIT)
        ).gates["gate_one_team"]
        self.assertEqual([998, 999], [row["key"] for row in gate["rows"]])
        self.assertIs(True, gate["any_row_would_pass"])
        self.assertIs(False, gate["every_row_would_pass"])
        self.assertEqual(1, gate["recorded_team"])

    def test_the_reported_row_keys_are_integers_not_the_saves_json_strings(self) -> None:
        """Measured: the save carries ``"998"`` and the report carries ``998``.

        An earlier draft compared the reported keys against ``["998", "999"]`` and
        failed; both affected assertions disagreed in the same way, which is what
        identified it as a **typing** fact rather than a reader bug.  The typing is
        load-bearing for the report's claim that it hands back what the repository
        returned, so it is asserted rather than normalised away.
        """
        self._seed_row(RESURRECTABLE_UNIT, 1, key="998")
        self._seed_row(RESURRECTABLE_UNIT, 3, key="999")
        gate = self._assert_success(
            self._intent(unit_id=RESURRECTABLE_UNIT)
        ).gates["gate_one_team"]
        self.assertEqual(
            ["998", "999"],
            [key for key in self._snapshot_items() if key in ("998", "999")],
            "the save's own keys really are JSON strings",
        )
        self.assertEqual([998, 999], [row["key"] for row in gate["rows"]])

    def _snapshot_items(self) -> Dict[str, Any]:
        return self.repository.read(self.player).snapshot()["maps"][0]["items"]

    def test_the_reported_team_verdict_is_the_preserved_exact_comparison(self) -> None:
        """``engine.py:151`` is ``item[7] != 1: return False``, so **only** team 1
        passes.  Team 0 does not, even though ``map_lose_item``'s selector is a
        truthiness test -- which is the asymmetry, reported rather than resolved.

        **Team 0 is absent from the loop on purpose.**  It is not reachable as a
        *reported verdict*: the repository refuses a document whose row records
        team 0, because the preserved placement selector never chooses one, so the
        transaction answers ``unreadable_state`` before the gate report is built.
        :meth:`test_team_zero_is_refused_by_the_repository_before_it_can_be_reported`
        asserts that separately.  Leaving 0 in the loop would have tested the
        repository twice and the gate not at all.
        """
        for team, expected in ((1, True), (3, False), (2, False), (99, False)):
            with self.subTest(team=team):
                self._seed_row(RESURRECTABLE_UNIT, team)
                gate = self._assert_success(
                    self._intent(unit_id=RESURRECTABLE_UNIT)
                ).gates["gate_one_team"]
                self.assertIs(expected, gate["every_row_would_pass"])

    def test_team_zero_is_refused_by_the_repository_before_it_can_be_reported(self) -> None:
        """The companion, so removing ``0`` from the loop above loses no coverage.

        ``map_lose_item``'s selector is a truthiness test, so team 0 *would* have
        passed the preserved gate; the repository refuses the document instead.  Both
        facts are preserved: the refusal, and the reason it names the selector.
        """
        self._seed_row(RESURRECTABLE_UNIT, 0)
        outcome = self._apply(self._intent(unit_id=RESURRECTABLE_UNIT))
        refusal = self._assert_refusal_wrote_nothing(outcome, RefusalCode.UNREADABLE_STATE)
        self.assertIn("team 0", refusal.message)
        self.assertIn("placement selector never chooses", refusal.message)
        self.assertNotIn("gates", refusal.detail)

    def test_the_resurrectable_gate_is_reported_verbatim_when_the_key_is_present(self) -> None:
        gate = self._assert_success(
            self._intent(unit_id=RESURRECTABLE_UNIT)
        ).gates["gate_two_resurrectable"]
        self.assertIs(True, gate["present"])
        self.assertEqual("1", gate["committed_value"])
        self.assertIs(True, gate["would_pass"])
        self.assertIn("embedded JSON string", gate["stored_as"])

    def test_an_absent_resurrectable_is_reported_as_absent_and_never_as_zero(self) -> None:
        """The distinction a first draft would have collapsed, kept explicit.

        ``present`` ``False`` with ``committed_value`` ``None`` is a *statement about
        the committed row*; ``would_pass`` ``None`` is the consequence.  Writing
        ``0`` for either would report a value the committed row does not carry --
        ``engine.py:159-160`` returns ``False`` on an absent key and never reads one.
        """
        gate = self._assert_success().gates["gate_two_resurrectable"]
        self.assertIs(False, gate["present"])
        self.assertIsNone(gate["committed_value"])
        self.assertIsNone(gate["would_pass"])
        self.assertIs(False, gate["absent_is_read_as_zero"])

    def test_an_absent_key_and_a_recorded_zero_would_stay_distinguishable(self) -> None:
        """The control for the test above, and it costs a planted content row.

        No committed unit records ``resurrectable: "0"`` -- all 426 are ``"1"`` --
        so the distinction is asserted over a **crafted** content row rather than
        over committed content.  That is stated here because a test which silently
        asserted a distinction over crafted input would read as a statement about
        the committed table.
        """
        absent = self._assert_success().gates["gate_two_resurrectable"]
        zero = self._content_with_flag("0").unit_flag_is_positive(
            ABSENT_FLAG_UNIT, "resurrectable"
        )
        self.assertIsNone(absent["would_pass"])
        self.assertIs(False, zero)
        self.assertNotEqual(absent["would_pass"], zero)
        # And the truthiness trap: the committed encoding is a string, so a bare
        # truthiness test would answer True for the recorded "0".
        self.assertTrue(bool("0"))

    def _content_with_flag(self, value: str) -> CommittedContent:
        """A content proxy whose one unit's ``resurrectable`` is ``value``."""
        inner = self.content
        properties_field = "resurrectable"

        class _Content:
            def unit_flag(self, unit_id: int, name: str) -> Optional[Any]:
                if unit_id == ABSENT_FLAG_UNIT and name == properties_field:
                    return value
                return inner.unit_flag(unit_id, name)

            def unit_flag_is_positive(self, unit_id: int, name: str) -> Optional[bool]:
                if unit_id == ABSENT_FLAG_UNIT and name == properties_field:
                    return int(value) > 0
                return inner.unit_flag_is_positive(unit_id, name)

            def __getattr__(self, key: str) -> Any:
                return getattr(inner, key)

        return _Content()  # type: ignore[return-value]

    def test_neither_gate_is_a_precondition(self) -> None:
        """Design D3: reported, never enforced.

        A team-3 row and an absent ``resurrectable`` are both the *worst* case for
        the preserved helper, and the transaction still succeeds -- because there is
        no operation for a gate to stand in front of.
        """
        self._seed_row(RESURRECTABLE_UNIT, 3)
        success = self._assert_success(self._intent(unit_id=RESURRECTABLE_UNIT))
        self.assertIs(False, success.gates_enforced)
        self.assertIs(False, success.gates["enforced"])
        self.assertIn("destroys", success.gates["enforced_note"])

    def test_the_ledger_path_is_reported_so_a_reader_can_see_it_was_covered(self) -> None:
        payload = self._assert_success().payload()
        self.assertIn("whole-document", payload["ledger_covered_by"])
        self.assertIn(DEAD_HERO_LEDGER_PATH, payload["ledger_covered_by"] + " " + DEAD_HERO_LEDGER_PATH)
        self.assertIs(False, payload["ledger_credited"])

    def test_every_recorded_row_is_reported_and_none_is_selected(self) -> None:
        """A report, not a selection.

        The preserved helper consumes the **first** match in the save's key order;
        this reader hands back **every** match and removes nothing, because v1
        destroys nothing and a reader that picked one would be choosing on the
        client's behalf.
        """
        self._seed_row(RESURRECTABLE_UNIT, 1, key="997")
        self._seed_row(RESURRECTABLE_UNIT, 1, key="998")
        self._seed_row(RESURRECTABLE_UNIT, 1, key="999")
        gate = self._assert_success(
            self._intent(unit_id=RESURRECTABLE_UNIT)
        ).gates["gate_one_team"]
        self.assertEqual(3, gate["row_count"])
        self.assertEqual([997, 998, 999], [row["key"] for row in gate["rows"]])
        self.assertEqual(self._pre_bytes(), corpus_save_bytes(self.corpus))


class DestructionRefusalTests(SeededFixture):
    """Task 3.3 and 9.4: the figure is reported, never applied, never narrowed."""

    def test_the_branch_wire_shape_is_refused_by_name(self) -> None:
        refusal = self._assert_refused(
            self._apply(self._intent(destruction=DESTRUCTION_SHAPE)),
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertEqual(409, refusal.http_status)
        self.assertEqual(409, REFUSAL_HTTP_STATUS[RefusalCode.CLIENT_DICTATED_DESTRUCTION])

    def test_the_refused_figure_is_carried_verbatim_beside_the_code(self) -> None:
        refusal = self._assert_refused(
            self._apply(self._intent(destruction=DESTRUCTION_SHAPE)),
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertEqual(DESTRUCTION_SHAPE, refusal.detail["requested_destruction"])
        self.assertEqual(ABSENT_FLAG_UNIT, refusal.detail["requested_unit_id"])
        self.assertIn("verbatim", refusal.detail["requested_destruction_is"])

    def test_nothing_is_applied_and_no_count_is_derived(self) -> None:
        refusal = self._assert_refused(
            self._apply(self._intent(destruction=DESTRUCTION_SHAPE)),
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertIs(False, refusal.detail["applied"])
        self.assertIs(False, refusal.detail["count_derived"])
        self.assertEqual(0, refusal.detail["rows_destroyed"])
        self.assertIs(False, refusal.detail["ledger_credited"])

    def test_the_refusal_writes_no_row_and_no_ledger_key(self) -> None:
        """Task 3.3, at the store rather than in the detail mapping.

        The detail reports ``rows_destroyed: 0``; this asserts the **file**.  A
        refusal whose detail lied and whose store moved would satisfy the other
        test, which is why they are separate methods rather than one.
        """
        self._seed_row(RESURRECTABLE_UNIT, 1)
        before_items = dict(self._snapshot_items())
        before_ledger = dict(
            self.repository.read(self.player).snapshot()["privateState"]["deadHeroes"]
        )
        self._assert_refusal_wrote_nothing(
            self._apply(self._intent(unit_id=RESURRECTABLE_UNIT, destruction=DESTRUCTION_SHAPE)),
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertEqual(before_items, self._snapshot_items())
        self.assertEqual(before_ledger, self._snapshot()["privateState"]["deadHeroes"])
        self.assertEqual({}, before_ledger)

    def _snapshot(self) -> Dict[str, Any]:
        return self.repository.read(self.player).snapshot()

    def _snapshot_items(self) -> Dict[str, Any]:
        return self._snapshot()["maps"][0]["items"]

    def test_the_refusal_resolves_before_the_identity_is_considered(self) -> None:
        """Design D4, ordering made falsifiable.

        A request naming **no committed row at all** still reports the destruction
        refusal rather than the identity refusal.  That is the order the design
        settles: the wire shape is the security-relevant statement about the request,
        and reporting the identity first would tell a client about a committed table
        it does not need.
        """
        outcome = self._apply(self._intent(unit_id=999999, destruction=DESTRUCTION_SHAPE))
        self._assert_refused(outcome, RefusalCode.CLIENT_DICTATED_DESTRUCTION)
        self.assertEqual(999999, outcome.detail["requested_unit_id"])

    def test_every_non_null_shape_of_the_destruction_key_is_refused_not_read(self) -> None:
        """Neither ``None``-deref shape is representable, so neither is reachable.

        Task 3.5: ``command.py:866`` and ``:874`` dereference ``attacker_units`` and
        ``victim`` with no ``None`` check.  In v1 a request carrying the key is
        refused **by name** whatever its value, so the branch's two raises have no
        request encoding at all.

        **Every non-null value.**  ``None`` is the single exception and it is a real
        finding, not an omission: JSON ``null`` and an absent key are the same value
        once the request body has been read, so ``attacker_units: null`` parses to
        ``destruction_request is None`` and the key-name channel sees **no** shape.
        :meth:`test_a_json_null_destruction_shape_is_carried_as_no_shape_at_all`
        states it.  An earlier draft of this test looped over ``None`` expecting a
        refusal and failed, which is how the fact surfaced; the loop first needed a
        sentinel default (:data:`ABSENT`) precisely because ``None`` is a value the
        request may legitimately carry.
        """
        for value in ([], [[0, 0, 1, 0]], "1", 1, {"a": 1}, [[None, None, None, None]], 0):
            with self.subTest(value=value):
                self._assert_refusal_wrote_nothing(
                    self._apply(self._intent(destruction=value)),
                    RefusalCode.CLIENT_DICTATED_DESTRUCTION,
                )

    def test_a_json_null_destruction_shape_is_carried_as_no_shape_at_all(self) -> None:
        """The one encoding that is **not** refused, and why it is still safe.

        ``attacker_units: null`` is indistinguishable from an omitted key once the
        body has been decoded, so the intent carries no shape and the transaction
        succeeds.  It is **safe**, because the transaction destroys nothing on either
        path -- the difference is only whether the refusal code reaches the client.

        It is recorded rather than closed, because closing it would mean teaching the
        request layer to distinguish a present-but-null key from an absent one, and
        the destruction shape's only job is to refuse a client that sends it.  A null
        is not an attempt to dictate a count.
        """
        parsed = self._intent(destruction=None)
        self.assertIsNone(parsed.destruction_request)
        success = self._assert_success(parsed)
        self.assertIsNone(success.payload()["destruction"]["requested"])
        self.assertIs(False, success.payload()["destruction"]["applied"])
        self.assertEqual(0, success.payload()["rows_destroyed"])
        self.assertEqual(self._pre_bytes(), corpus_save_bytes(self.corpus))

    def test_the_refusal_states_that_no_rollback_was_needed(self) -> None:
        refusal = self._assert_refused(
            self._apply(self._intent(destruction=DESTRUCTION_SHAPE)),
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertIs(False, refusal.detail["rolled_back"])
        self.assertIn("nothing was ever written", refusal.detail["rollback_note"])

    def test_the_refusal_carries_the_preserved_rule_it_refuses(self) -> None:
        refusal = self._assert_refused(
            self._apply(self._intent(destruction=DESTRUCTION_SHAPE)),
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertEqual(PRESERVED_COMBAT_BEHAVIOUR["destruction"], refusal.detail["preserved_rule"])
        self.assertIn("command.py:868", refusal.detail["preserved_rule"])

    def test_the_success_half_reports_the_shape_a_client_may_not_send(self) -> None:
        destruction = self._assert_success().payload()["destruction"]
        self.assertIsNone(destruction["requested"])
        self.assertEqual(
            "client_dictated_destruction", destruction["refused_by_code"]
        )
        self.assertEqual(409, destruction["refused_status"])
        self.assertIs(False, destruction["applied"])
        self.assertIs(False, destruction["count_derived"])
        self.assertIsNone(destruction["count"])

    def test_the_success_half_records_the_three_rejected_alternatives(self) -> None:
        """Task 9.4: reproducing **either** "one" or "all eligible" would be an
        invention, and the second is the client-dictated destruction wearing a
        different spelling."""
        rejected = self._assert_success().payload()["destruction"]["rejected_alternatives"]
        self.assertEqual(
            {"destroy_one_row", "destroy_every_eligible_row", "derive_from_attack_minus_defense"},
            set(rejected),
        )
        self.assertIn("fixture", rejected["destroy_one_row"])
        self.assertIn("client-dictated", rejected["destroy_every_eligible_row"])

    def test_v0s_reported_one_is_an_artefact_and_is_not_carried(self) -> None:
        """The one number a reader is most likely to want to hard-code.

        v0's resolve action reports ``destruction: 1``; executing
        ``combat_payload('resolve')`` shows the trailing ``0`` in its
        ``attacker_units`` payload is the builder's derived identity, and the
        committed fixture step **7** destroyed **two** rows at v0's counterpart for
        ``A=3, B=1``.  So neither number is a rule, and v1 reports ``None``.
        """
        payload = self._assert_success().payload()
        self.assertIsNone(payload["derived_destruction_count"])
        self.assertEqual(0, payload["rows_destroyed"])
        self.assertNotIn(1, [payload["rows_destroyed"], payload["derived_destruction_count"]])

    def test_a_second_request_carries_no_residue_from_the_first(self) -> None:
        """A store is reusable after the refusal, asserted rather than assumed."""
        self._assert_refusal_wrote_nothing(
            self._apply(self._intent(destruction=DESTRUCTION_SHAPE)),
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertIsInstance(self._apply(self._intent()), CombatSuccess)


class OutOfTableIdentityTests(SeededFixture):
    """Task 4.3: zero and every negative resolve to no committed row."""

    def test_zero_and_every_negative_are_refused_as_unaddressable(self) -> None:
        for unit_id in (0, -1, -113, -999999):
            with self.subTest(unit_id=unit_id):
                self._assert_refusal_wrote_nothing(
                    self._apply(self._intent(unit_id=unit_id)),
                    RefusalCode.UNADDRESSABLE_ROW,
                )

    def test_a_building_id_and_the_special_id_are_refused_for_the_same_reason(self) -> None:
        """The zero-overlap consequence, asserted rather than described.

        A building id is a **real** committed id, so if the reader resolved by
        position or by the ``items`` array rather than by the ``u`` type it would
        resolve one.  Both must be refused for exactly the reason ``0`` is.
        """
        for unit_id in (BUILDING_ID, SPECIAL_ID, 26, 905):
            with self.subTest(unit_id=unit_id):
                self.assertIsNotNone(self.content.item(unit_id))
                self._assert_refusal_wrote_nothing(
                    self._apply(self._intent(unit_id=unit_id)),
                    RefusalCode.UNADDRESSABLE_ROW,
                )

    def test_the_refusal_reports_the_committed_unit_id_space(self) -> None:
        refusal = self._assert_refused(
            self._apply(self._intent(unit_id=0)), RefusalCode.UNADDRESSABLE_ROW
        )
        self.assertEqual(429, refusal.detail["committed_unit_rows"])
        self.assertEqual(429, len(refusal.detail["committed_unit_ids"]))
        self.assertEqual(list(self.content.unit_ids()), refusal.detail["committed_unit_ids"])
        self.assertIsNone(refusal.detail["resolved_row"])
        self.assertIn("type is u", refusal.detail["committed_table_is"])

    def test_the_refusal_states_that_a_non_positive_id_is_not_clamped(self) -> None:
        refusal = self._assert_refused(
            self._apply(self._intent(unit_id=-1)), RefusalCode.UNADDRESSABLE_ROW
        )
        self.assertIs(True, refusal.detail["non_positive_is_not_clamped"])
        self.assertIn("never indexes the committed table", refusal.detail["why_not_clamped"])

    def test_the_identity_refusal_is_409_and_uses_an_existing_code(self) -> None:
        self.assertEqual(409, REFUSAL_HTTP_STATUS[RefusalCode.UNADDRESSABLE_ROW])
        source = DOMAIN_SOURCE.read_text(encoding="utf-8")
        self.assertIn("RefusalCode.UNADDRESSABLE_ROW", source)
        self.assertNotIn("UNKNOWN_UNIT", source)

    def test_the_identity_refusal_resolves_before_the_snapshot(self) -> None:
        """Design D4 asserted structurally: every refusal precedes step 4.

        Read from the module's own source rather than trusted, and it is a real
        guard: a future edit that moved the identity resolution **below** the
        snapshot would leave every behavioural test in this file green -- nothing
        about an unresolvable identity is observable after the fact -- while making
        the ordering claim false.
        """
        source = DOMAIN_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n")
        body = source.split("def apply_combat(", 1)[1].split("\ndef ", 1)[0]
        for marker in (
            "_destruction_refusal(intent, unit_id)",
            "_unknown_unit(content, unit_id)",
            "document.snapshot()",
        ):
            self.assertIn(marker, body)
        self.assertLess(
            body.index("_destruction_refusal(intent, unit_id)"),
            body.index("document.snapshot()"),
        )
        self.assertLess(
            body.index("_unknown_unit(content, unit_id)"),
            body.index("document.snapshot()"),
        )


class RefusalChannelTests(SeededFixture):
    """The two store-level refusals, and the status table this slice relies on."""

    def test_an_unknown_player_is_refused_with_404(self) -> None:
        outcome = self._apply(self._intent(player="no-such-player"))
        self._assert_refused(outcome, RefusalCode.UNKNOWN_PLAYER)
        self.assertEqual(404, outcome.http_status)
        self.assertEqual(404, REFUSAL_HTTP_STATUS[RefusalCode.UNKNOWN_PLAYER])

    def test_an_unreadable_store_is_refused_with_500_and_its_cause(self) -> None:
        """``unreadable_state``, reached over the corpus by making ``maps`` unusable.

        The preserved fresh-player corpus cannot reach this shape, so it is produced
        on the **disposable** corpus's own file -- never on a committed save.

        **500, not 409.**  The refusal is about *our own* store being unusable, not
        about a client request conflicting with the state, so it carries the same
        status as ``unreadable_content`` and ``post_condition_violation`` in the
        one code->status table.  An earlier draft asserted 409 and was corrected by
        measurement against :data:`REFUSAL_HTTP_STATUS`; the disagreement here is a
        conflict of authority, and reading the table is the authority.
        """
        path = self._save_path()
        data = json.loads(path.read_text(encoding="utf-8"))
        data["maps"] = {}
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=4)
        outcome = self._apply(self._intent())
        refusal = self._assert_refused(outcome, RefusalCode.UNREADABLE_STATE)
        self.assertEqual("unreadable_state", refusal.detail["cause"])
        self.assertEqual(500, refusal.http_status)
        self.assertEqual(500, REFUSAL_HTTP_STATUS[RefusalCode.UNREADABLE_STATE])
        self.assertEqual(
            REFUSAL_HTTP_STATUS[RefusalCode.UNREADABLE_STATE],
            REFUSAL_HTTP_STATUS[RefusalCode.POST_CONDITION_VIOLATION],
            "an unusable store and a violated post-condition are the same class",
        )

    def test_every_refusal_this_slice_can_produce_reports_a_status(self) -> None:
        """The transport asks for it, so the table has to be total."""
        codes = (
            RefusalCode.UNKNOWN_PLAYER,
            RefusalCode.UNREADABLE_STATE,
            RefusalCode.UNADDRESSABLE_ROW,
            RefusalCode.CLIENT_DICTATED_DESTRUCTION,
            RefusalCode.POST_CONDITION_VIOLATION,
        )
        for code in codes:
            with self.subTest(code=code):
                self.assertIn(code, REFUSAL_HTTP_STATUS)
                self.assertIn(REFUSAL_HTTP_STATUS[code], (400, 404, 409, 500))

    def test_the_destruction_refusal_is_a_conflict_and_not_a_client_error(self) -> None:
        """Task 1.3's recorded difference from v0.

        v0's counterpart is a 4xx because v0 applies the client-sent resource
        vector **before** the dispatcher opens; v1's request is well-formed, the
        player exists, and it conflicts with what a client may decide, which is what
        a 409 says.  The difference is recorded on the code itself and asserted here.
        """
        self.assertEqual(409, REFUSAL_HTTP_STATUS[RefusalCode.CLIENT_DICTATED_DESTRUCTION])

    #: The owning test method in ``test_refusals.py`` whose name is stable.
    V0_EQUIVALENCE_OWNER = "test_every_code_has_a_purpose_and_a_v0_note"

    def test_the_v0_equivalence_of_the_new_code_is_owned_by_test_refusals(self) -> None:
        """Task 1.3, as an **ownership hand-off** rather than a restatement.

        An earlier draft read the equivalence table directly.  That is the one
        thing a v1 module must not do, and an **existing** delivered guard in
        ``test_refusals.py`` says so -- so the draft broke a cross-line
        invariant to restate a claim that line already makes in **both**
        directions over the whole vocabulary.  The claim is delegated rather
        than dropped: the owner exists, is still there under its own name, and
        still asserts set equality over the closed code set, which is stronger
        than a membership test written here.  The table's name is deliberately
        absent from this file: naming it is precisely what the owner forbids.
        """
        owner = ast.parse(
            (harness.TESTS_DIR / "test_refusals.py").read_text(encoding="utf-8")
        )
        found = [
            node
            for node in ast.walk(owner)
            if isinstance(node, ast.FunctionDef)
            and node.name == self.V0_EQUIVALENCE_OWNER
        ]
        self.assertEqual(1, len(found), "the owning assertion is gone")
        body = ast.unparse(found[0])
        self.assertIn("RefusalCode", body)
        self.assertIn("assertEqual", body)


class SuccessPayloadTests(SeededFixture):
    """The success body's own contract: nothing derived, nothing applied."""

    def test_the_payload_carries_no_derivation_key_at_all(self) -> None:
        payload = self._assert_success().payload()
        self.assertNotIn("derived_deltas", payload)
        self.assertIsNone(payload["derived_damage"])
        self.assertIsNone(payload["derived_destruction_count"])
        self.assertIs(False, payload["damage_derived"])
        self.assertIsNone(payload["derivation_performed"])

    def test_the_payload_reports_rows_destroyed_zero_and_the_proof_beside_it(self) -> None:
        payload = self._assert_success().payload()
        self.assertEqual(0, payload["rows_destroyed"])
        self.assertIs(True, payload["document_unchanged"])
        self.assertEqual([], payload["leaf_paths_changed"])
        self.assertEqual(
            [[name, True] for name in PROOF_CHECK_ORDER],
            payload["proof"],
        )

    def test_the_proof_is_reported_in_the_enforced_order_and_all_held(self) -> None:
        success = self._assert_success()
        self.assertEqual(PROOF_CHECK_ORDER, tuple(name for name, _held in success.proof))
        self.assertEqual([True] * 5, [held for _name, held in success.proof])

    def test_every_stored_resource_is_reported_and_none_moved(self) -> None:
        before = self._resources()
        payload = self._assert_success().payload()
        self.assertEqual(sorted(STORED_RESOURCE_NAMES), payload["stored_resources_compared"])
        self.assertEqual(before, payload["resources_after"])
        self.assertEqual(7, len(payload["resources_after"]))

    def test_the_action_and_the_identity_are_named_in_v1s_own_vocabulary(self) -> None:
        """Task 4.2: the route names the **surface**, never the legacy branch.

        The identity field is ``unit_id`` and the **container** is ``combat``: the
        two are different words and an earlier draft of this test read the
        container's name as the field's.

        ``end_attack`` **does** appear in the serialised payload -- inside
        ``preserved_branch_behaviour``, which cites the two call sites of
        ``map_lose_item`` as provenance.  That is required: the provenance is what
        lets a reader check the claim, and a payload that named the branch nowhere
        would be asserting its absence rather than recording it.  So the claim is
        scoped to the **naming** -- the action, the container and the absence of any
        key named after the branch -- and the provenance is checked to be the *only*
        place the name occurs.
        """
        payload = self._assert_success().payload()
        self.assertEqual("combat", payload["action"])
        self.assertIn("combat", payload)
        self.assertEqual("unit_id", payload["combat"]["identity_field"])
        self.assertEqual(ABSENT_FLAG_UNIT, payload["combat"]["unit_id"])

        # No **key** is named after the branch.
        self.assertEqual([], [key for key in payload if "attack" in key.lower()])
        # And the name reaches the body only through the recorded provenance table.
        text = json.dumps(payload)
        self.assertIn("end_attack", text)
        for key, value in payload.items():
            with self.subTest(key=key):
                if key == "preserved_branch_behaviour":
                    continue
                self.assertNotIn("end_attack", json.dumps(value))

    def test_the_team_asymmetry_is_carried_on_the_wire(self) -> None:
        payload = self._assert_success().payload()
        self.assertIs(False, payload["team_asymmetry"]["reconciled"])
        self.assertEqual(TEAM_ASYMMETRY["consequence"], payload["team_asymmetry"]["consequence"])

    def test_the_preserved_behaviour_table_is_carried_whole(self) -> None:
        payload = self._assert_success().payload()
        self.assertEqual(
            dict(PRESERVED_COMBAT_BEHAVIOUR), payload["preserved_branch_behaviour"]
        )

    def test_the_success_model_cannot_be_constructed_with_an_empty_proof(self) -> None:
        """A success reporting no proof at all is not a state this route may reach."""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            CombatSuccess(
                action=ACTION,
                unit_id=ABSENT_FLAG_UNIT,
                instant=SERVICE_INSTANT,
                state={"xp": 1},
                committed={},
                gates={},
                team_asymmetry={},
                destruction={},
                proof=(),
                leaf_paths_changed=(),
                document_unchanged=True,
            )

    def test_the_success_model_is_frozen(self) -> None:
        success = self._assert_success()
        with self.assertRaises(Exception):
            success.unit_id = 1  # type: ignore[misc]


class _DriftingContent:
    """Committed content whose ``unit_row`` answer changes on its **second** call.

    Declared once at module scope.  An earlier draft declared a byte-identical copy
    inside each of the two tests that need it, and the second silently shadowed the
    first -- which is the same "one name, two definitions" shape the inventory pin
    in :class:`DomainInventoryTests` exists to catch on the *domain* side.

    It is declared here, not inside a test, because
    ``test_qualified_and_unqualified_names_coincide_because_no_class_owns_a_helper``
    reads the domain's tree, never this file's.
    """

    def __init__(self, inner: CommittedContent) -> None:
        self._inner = inner
        self._calls = [0]

    def unit_row(self, unit_id: int) -> Any:
        row = self._inner.unit_row(unit_id)
        self._calls[0] += 1
        if self._calls[0] >= 2 and row is not None:
            return dict(row, name="TAMPERED")
        return row

    def __getattr__(self, key: str) -> Any:
        return getattr(self._inner, key)


class PostConditionProofTests(SeededFixture):
    """Each of the five halves, isolated, and the order they run in.

    **The instrument is a second-read tamper**, for the reason
    :meth:`SeededFixture._tampering_read_repository` records.  There is no write on
    this path, so the sibling slice's write-tampering harness would never fire.
    """

    def _run_with_tamper(self, tamper: Callable[[Dict[str, Any]], None]) -> Any:
        return self._apply(self._intent(), content=self.content)

    def _tampered(self, tamper: Callable[[Dict[str, Any]], None]) -> Any:
        """Drive the domain through the tampering repository."""
        intent = self._intent()
        return apply_combat(
            intent, self.content, self._tampering_read_repository(tamper), SERVICE_INSTANT
        )

    def test_the_baseline_run_through_the_tampering_repository_still_succeeds(self) -> None:
        """The control: an instrument that cannot produce a clean run is broken.

        Without it, a harness that silently stopped tampering would report five
        green halves and one green baseline for the wrong reason.
        """
        outcome = self._tampered(lambda data: None)
        self.assertIsInstance(outcome, CombatSuccess)

    def test_the_identity_half_fails_alone(self) -> None:
        """Check 1 re-reads its subject, so committed content changing under it is
        the only thing that reaches this half first."""

        intent = self._intent()
        outcome = apply_combat(
            intent, _DriftingContent(self.content), self.repository, SERVICE_INSTANT
        )
        refusal = self._assert_refused(outcome, RefusalCode.POST_CONDITION_VIOLATION)
        self.assertEqual("identity_resolved_to_reported_row", refusal.detail["half"])
        self.assertEqual(
            ["identity_resolved_to_reported_row"],
            refusal.detail["failed_checks"],
        )

    def test_the_reported_gates_half_is_reached_first_by_a_row_appearing(self) -> None:
        """Check 2 cannot be isolated, and the co-firing is what the test states.

        A row appearing under the addressed key is the tamper that reaches check 2
        first, because the gate report is recomputed against the second snapshot.
        It is not an *isolated* check-2 failure: the new row is also a new leaf, so
        checks 3 and 4 fail with it.  An earlier draft of this test asserted the
        three-check list and was corrected by measurement, because a claim that one
        half fires alone here would be false.

        ``half`` is the **first** failed check, so it does name check 2 -- which is
        the part that is isolable.
        """

        def tamper(data: Dict[str, Any]) -> None:
            data["maps"][0]["items"]["998"] = [ABSENT_FLAG_UNIT, 1, 1, 0, 0, [], {}, 1]

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("reported_gates_match_content_and_state", refusal.detail["half"])
        self.assertEqual(
            [
                "reported_gates_match_content_and_state",
                "no_leaf_path_changed",
                "whole_document_unchanged",
            ],
            refusal.detail["failed_checks"],
        )
        self.assertEqual(["/maps/0/items/998"], refusal.detail["leaf_paths_changed"])

    def test_the_leaf_census_half_fails_alone_on_a_ledger_key(self) -> None:
        """Check 3 is the census, and a ledger key is exactly the case it names.

        This is the falsifiable half for the surface that matters most: a credit to
        the dead-hero ledger is a leaf under ``/privateState``, and the census names
        it rather than reporting only that *something* changed.
        """

        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["deadHeroes"]["999"] = 1

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("no_leaf_path_changed", refusal.detail["half"])
        self.assertEqual(["/privateState/deadHeroes/999"], refusal.detail["leaf_paths_changed"])

    def test_the_leaf_census_half_fails_on_a_removed_row_and_names_it(self) -> None:
        """A destruction of **any** size fails this half, which is task 9.6's
        falsifiability claim made mechanical."""

        def tamper(data: Dict[str, Any]) -> None:
            del data["maps"][0]["items"]["1"]

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("no_leaf_path_changed", refusal.detail["half"])
        self.assertEqual(["/maps/0/items/1"], refusal.detail["leaf_paths_changed"])

    def test_the_whole_document_half_fails_alone_on_a_key_reorder(self) -> None:
        """The one instrument that isolates check 4, and it is the interesting one.

        A key reorder moves **no** leaf -- the census sorts keys before walking, so
        a reorder is invisible to it -- but it changes the serialised bytes.  That
        is why check 4 exists beside check 3: without it a reordering write would
        pass the census.  It also proves the order is load-bearing, because a
        module that ran the byte comparison first could not report this at all.
        """

        def tamper(data: Dict[str, Any]) -> None:
            current = data["maps"][0]
            data["maps"][0] = {key: current[key] for key in sorted(current, reverse=True)}

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("whole_document_unchanged", refusal.detail["half"])
        self.assertEqual(["whole_document_unchanged"], refusal.detail["failed_checks"])
        self.assertEqual([], refusal.detail["leaf_paths_changed"])

    def test_the_resources_half_cannot_be_isolated_and_that_is_stated(self) -> None:
        """The honest half of this class, and the reason it is a method.

        Every stored resource lives at a leaf path, so moving one trips the census
        **first** and ``resources_unchanged`` is reported alongside it rather than
        alone.  A suite claiming five isolable halves would have had to invent a
        resource that is not a leaf; this one measures the co-firing and states it,
        because "check 5 is unreachable on its own" is a fact about the design a
        reader needs and not a defect in the check.
        """

        def tamper(data: Dict[str, Any]) -> None:
            data["maps"][0]["gold"] = data["maps"][0]["gold"] + 5

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("no_leaf_path_changed", refusal.detail["half"])
        self.assertEqual(
            ["no_leaf_path_changed", "whole_document_unchanged", "resources_unchanged"],
            refusal.detail["failed_checks"],
        )
        self.assertEqual(["/maps/0/gold"], refusal.detail["leaf_paths_changed"])

    def test_only_four_halves_are_observable_and_that_is_stated(self) -> None:
        """The control, and the honest result.

        ``half`` is the **first** failed check, so the five checks do not produce
        five observable halves.  A leaf-path change trips the census (check 3)
        first, and a **stored resource is a leaf path**, so moving ``gold`` reports
        ``no_leaf_path_changed`` too -- not ``resources_unchanged``.  Measured:
        four distinct halves out of five checks, and ``resources_unchanged`` is
        never one of them.

        An earlier draft of this test asserted five distinct halves.  It failed, and
        the failure is the finding: "check 5 is unreachable on its own" is a fact
        about the design that a reader needs, not a defect in the check.  Asserting
        five would have required inventing a resource that is not a leaf.
        """

        def gates(data: Dict[str, Any]) -> None:
            data["maps"][0]["items"]["998"] = [ABSENT_FLAG_UNIT, 1, 1, 0, 0, [], {}, 1]

        def leaf(data: Dict[str, Any]) -> None:
            data["privateState"]["deadHeroes"]["999"] = 1

        def reorder(data: Dict[str, Any]) -> None:
            current = data["maps"][0]
            data["maps"][0] = {key: current[key] for key in sorted(current, reverse=True)}

        def resource(data: Dict[str, Any]) -> None:
            data["maps"][0]["gold"] = data["maps"][0]["gold"] + 5

        identity = apply_combat(
            self._intent(), _DriftingContent(self.content), self.repository, SERVICE_INSTANT
        ).detail["half"]

        observed = {
            "identity": identity,
            "gates": self._tampered(gates).detail["half"],
            "leaf": self._tampered(leaf).detail["half"],
            "reorder": self._tampered(reorder).detail["half"],
            "resource": self._tampered(resource).detail["half"],
        }
        self.assertEqual(
            {
                "identity": PROOF_CHECK_ORDER[0],
                "gates": PROOF_CHECK_ORDER[1],
                "leaf": PROOF_CHECK_ORDER[2],
                "reorder": PROOF_CHECK_ORDER[3],
                "resource": PROOF_CHECK_ORDER[2],
            },
            observed,
            "a half reported a name the enforced order does not carry",
        )
        self.assertEqual(4, len(set(observed.values())), "two halves reported the same name")
        self.assertNotIn(
            PROOF_CHECK_ORDER[4],
            set(observed.values()),
            "check 5 can only ever be reached after check 3 and check 4",
        )
        self.assertEqual(
            {"no_leaf_path_changed", "whole_document_unchanged", "resources_unchanged"},
            set(self._tampered(resource).detail["failed_checks"]),
            "the resource tamper must co-fire all three later checks",
        )

    def test_the_census_names_every_leaf_and_the_byte_comparison_follows_it(self) -> None:
        """Task 9.6: the **order** is the reverse of line 3's, and it is asserted.

        Read from the module's own source, because the order is a property of the
        walk and a behavioural test cannot distinguish a module that checked the
        bytes first and happened to report the census name.

        Read from the **raw** text, not through :func:`_code_only`: the three check
        names are string literals, and the lexer blanks every literal to ``""``, so
        a stripped read would raise ``ValueError`` here -- which is how this test
        first failed.  The same trap is the reason ``test_the_reported_field_table_
        is_pinned_against_what_the_module_reads`` reads raw too.
        """
        body = DOMAIN_SOURCE.read_text(encoding="utf-8")
        self.assertLess(
            body.index('"no_leaf_path_changed"'), body.index('"whole_document_unchanged"')
        )
        self.assertLess(
            body.index('"whole_document_unchanged"'), body.index('"resources_unchanged"')
        )

    def test_the_first_three_halves_are_a_specification_check_and_that_is_stated(
        self,
    ) -> None:
        """Task 9.6, first half.

        Asserted as **v1 being the only writer on this path**: the corpus save
        contains no second writer, the repository is the sole writer, and the
        domain declares no mutator at all.  That is what makes half 4 -- not half 1
        -- the one carrying the evidence weight.
        """
        self.assertEqual([], sorted(name for name in EXPECTED_COMBAT_FUNCTIONS
                                   if name.endswith(("_write", "_commit", "_save", "write"))))
        self.assertIn("specification", DOMAIN_SOURCE.read_text(encoding="utf-8"))
        self.assertIn("falsifiable", DOMAIN_SOURCE.read_text(encoding="utf-8"))

    def test_a_failed_proof_needs_no_rollback_and_says_so(self) -> None:
        """The refusal reports ``rolled_back: False`` **with the reason**, rather
        than claiming work that was never started."""

        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["deadHeroes"]["999"] = 1

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertIs(False, refusal.detail["rolled_back"])
        self.assertIn("no write", refusal.detail["rollback_note"])

    def test_the_proof_reports_the_addressed_path_and_the_half(self) -> None:
        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["deadHeroes"]["999"] = 1

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertEqual("/maps/0/items", refusal.detail["addressed_path"])
        self.assertIn("deadHeroes", refusal.detail["cause"])

    def test_the_changed_leaf_helper_reports_a_list_length_as_a_path(self) -> None:
        """The helper's list branch, reachable through the census.

        Removing an item shortens a list; the census must report that as a change
        rather than walking past the end of the shorter list, which would report
        nothing at all for a deletion.
        """

        def tamper(data: Dict[str, Any]) -> None:
            data["privateState"]["deadHeroes"] = {"1": 1, "2": 2}

        refusal = self._assert_refused(
            self._tampered(tamper), RefusalCode.POST_CONDITION_VIOLATION
        )
        self.assertIn("no_leaf_path_changed", refusal.detail["half"])


class IntentTests(unittest.TestCase):
    """Task 4.1-4.4: the closed key set, the address, and the two encodings."""

    def _body(self, **fields: Any) -> Dict[str, Any]:
        body: Dict[str, Any] = {"player_id": "p", "unit_id": RESURRECTABLE_UNIT}
        body.update(fields)
        return body

    def _parse(self, **fields: Any) -> Any:
        return parse_intent(ACTION, self._body(**fields))

    def test_the_schema_is_closed_over_exactly_two_keys(self) -> None:
        self.assertEqual(frozenset({"player_id", "unit_id"}), INTENT_SCHEMAS[ACTION])

    def test_the_route_declares_no_operation_field(self) -> None:
        """Design D1: one action, so no second name over it."""
        self.assertEqual(frozenset({"combat"}), NO_OPERATION_FIELD_ACTIONS)
        self.assertNotIn(ACTION, INTENT_OPERATION_FIELDS)
        self.assertNotIn("operation", INTENT_SCHEMAS[ACTION])
        outcome = self._parse()
        self.assertIsInstance(outcome, Intent)
        self.assertIsNone(outcome.operation)

    def test_the_addressing_field_is_the_unit_id_and_resolves_to_the_container(self) -> None:
        """``/maps/0/items``, the **container**, not a key inside it.

        A combat identity is a committed item id, and the rows it could name are
        every key whose slot 0 equals it -- none, one, or several, and which no
        JSON pointer can express.  Naming the container is the honest address.
        """
        self.assertEqual("unit_id", ADDRESSING_FIELDS[ACTION])
        outcome = self._parse()
        self.assertIsInstance(outcome, Intent)
        self.assertEqual("/maps/0/items", outcome.addressed_path())

    def test_a_well_formed_request_parses_into_the_identity(self) -> None:
        outcome = self._parse()
        self.assertIsInstance(outcome, Intent)
        self.assertEqual(RESURRECTABLE_UNIT, outcome.unit_id)
        self.assertIsNone(outcome.destruction_request)
        self.assertIsNone(outcome.row)
        self.assertIsNone(outcome.magic_id)

    def test_a_non_integer_unit_id_is_refused_at_the_parser(self) -> None:
        for value in ("1", 1001.0, True, None, [1], {}):
            with self.subTest(value=value):
                outcome = self._parse(unit_id=value)
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)

    def test_a_negative_and_a_zero_unit_id_reach_the_domain(self) -> None:
        """Task 4.3: the omission is asserted rather than left implicit."""
        self.assertNotIn(ACTION, NON_NEGATIVE_ADDRESSING)
        for unit_id in (0, -1):
            with self.subTest(unit_id=unit_id):
                outcome = self._parse(unit_id=unit_id)
                self.assertIsInstance(outcome, Intent)
                self.assertEqual(unit_id, outcome.unit_id)

    def test_the_unit_id_is_required(self) -> None:
        outcome = parse_intent(ACTION, {"player_id": "p"})
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)

    def test_a_delta_key_is_refused_before_the_closed_key_check(self) -> None:
        """Task 4.4: two encodings of one request, two different mistakes, two
        different answers -- and this one is 400 while the destruction shape is 409."""
        outcome = self._parse(damage=3)
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.CLIENT_SUPPLIED_DELTA, outcome.code)
        self.assertEqual(400, outcome.http_status)

    def test_the_preserved_destruction_shape_is_carried_and_not_refused_here(self) -> None:
        """The recognition is a **key-name** channel and it decides nothing.

        A layer that reads key names has no rule about what a transaction would
        have destroyed, so naming ``client_dictated_destruction`` here would be the
        request layer deciding a question it cannot see.
        """
        self.assertEqual({"combat": frozenset({"attacker_units"})}, DESTRUCTION_KEYS)
        outcome = self._parse(attacker_units=DESTRUCTION_SHAPE)
        self.assertIsInstance(outcome, Intent)
        self.assertEqual(DESTRUCTION_SHAPE, outcome.destruction_request)

    def test_the_destruction_shape_is_refused_as_a_conflict_not_as_a_client_error(self) -> None:
        """The two encodings, side by side, because they differ only by a spelling."""
        delta = self._parse(damage=3)
        shape = parse_intent(
            ACTION, dict(self._body(), attacker_units=DESTRUCTION_SHAPE)
        )
        self.assertIsInstance(delta, Refusal)
        self.assertIsInstance(shape, Intent)
        self.assertEqual(400, delta.http_status)
        self.assertEqual(409, REFUSAL_HTTP_STATUS[RefusalCode.CLIENT_DICTATED_DESTRUCTION])

    def test_an_unknown_request_field_is_refused(self) -> None:
        for field in ("victim", "row", "now", "operation", "quantity", "count"):
            with self.subTest(field=field):
                outcome = self._parse(**{field: 1})
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.UNKNOWN_REQUEST_FIELD, outcome.code)

    def test_a_request_carrying_both_a_delta_and_the_destruction_shape_is_a_delta(self) -> None:
        """Precedence, and it has to be ``resources``.

        An earlier draft used ``honor`` here and failed -- and the reason is a
        **correction to an inherited claim**, not a test bug.  The preserved branch
        reads and discards **four** quantities (``honor``, ``resources``,
        ``resources_victim``, ``townhall_gold``), but only ``resources`` is in
        v1's ``DELTA_KEYS``; the other three are simply unknown field names and
        answer ``unknown_request_field``.  All four still answer **400**, which is
        the status this design decided on, but only one of them is classified as a
        client-dictated delta.

        :meth:`test_every_discarded_quantity_answers_client_error_with_its_own_code`
        pins that per field, so this precedence test can rely on it.
        """
        outcome = self._parse(attacker_units=DESTRUCTION_SHAPE, resources=[0, 0, 0, 0])
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.CLIENT_SUPPLIED_DELTA, outcome.code)
        self.assertEqual(400, outcome.http_status)

    def test_every_discarded_quantity_answers_client_error_with_its_own_code(self) -> None:
        """The four discarded quantities, and **three** of them are not deltas.

        Every one answers 400, so "the discarded quantities are refused as client
        errors" is true and does not need the finer classification.  The finer
        classification is recorded here because it is what makes the precedence test
        above choose ``resources`` -- and because the earlier draft's use of
        ``honor`` read as though all four shared one channel.
        """
        measured = {}
        for field in ("honor", "resources", "resources_victim", "townhall_gold"):
            outcome = self._parse(**{field: 1})
            self.assertIsInstance(outcome, Refusal)
            measured[field] = outcome.code
            self.assertEqual(400, outcome.http_status)
        self.assertEqual(
            {
                "honor": RefusalCode.UNKNOWN_REQUEST_FIELD,
                "resources": RefusalCode.CLIENT_SUPPLIED_DELTA,
                "resources_victim": RefusalCode.UNKNOWN_REQUEST_FIELD,
                "townhall_gold": RefusalCode.UNKNOWN_REQUEST_FIELD,
            },
            measured,
            "the four discarded quantities do not share one refusal channel",
        )

    def test_a_non_object_body_is_refused(self) -> None:
        for body in ([], "x", 1, None, True):
            with self.subTest(body=body):
                outcome = parse_intent(ACTION, body)
                self.assertIsInstance(outcome, Refusal)
                self.assertIs(RefusalCode.MALFORMED_REQUEST, outcome.code)

    def test_an_unknown_action_is_refused_rather_than_parsed_with_another_schema(self) -> None:
        outcome = parse_intent("end_attack", self._body())
        self.assertIsInstance(outcome, Refusal)
        self.assertIs(RefusalCode.UNKNOWN_REQUEST_FIELD, outcome.code)
        self.assertEqual("end_attack", outcome.detail["action"])

    def test_the_intent_module_names_only_the_three_structural_codes(self) -> None:
        """Restated from the caller's side, because this line added a table to it."""
        tree = ast.parse(INTENT_SOURCE.read_text(encoding="utf-8"))
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
        for stem in ("COMBAT", "DESTRUCTION", "UNIT", "ATTACKER"):
            with self.subTest(stem=stem):
                self.assertFalse(
                    any(stem in code for code in codes),
                    "the request layer named a domain refusal code",
                )

    def test_the_request_layer_knows_the_addressing_field_and_no_derived_quantity(self) -> None:
        """The sharper pair, restated: addressing yes, derived quantities no.

        The first draft of the sibling suite asserted the whole vocabulary was
        absent and failed on ``magic_id`` -- asserting that an intent cannot be
        addressable.

        Two different scans, on purpose.  ``attacker_units`` is a **string literal**
        in the intent module's key-name table, so it survives only in the **raw**
        text; reading it through :func:`_code_only` blanks every literal to ``""``
        and the assertion cannot pass.  The three absent tokens, by contrast, are
        identifiers, so the code-only scan is the stronger one for them: a comment
        or a docstring naming ``TEAM_ASYMMETRY`` would not satisfy it.
        """
        raw = INTENT_SOURCE.read_text(encoding="utf-8")
        code = _code_only(raw)
        self.assertIn("unit_id", code)
        self.assertIn("attacker_units", raw)
        self.assertNotIn("attacker_units", code, "the lexer stopped working")
        for token in ("ZERO_CONSUMER_COMBAT_FIELDS", "TEAM_ASYMMETRY", "MAP_LOSE_ITEM_CALL_SITES"):
            with self.subTest(token=token):
                self.assertNotIn(token, code)


class RouteTests(unittest.TestCase):
    """Task 5.1-5.3: the fourth route, and the transport that carries it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = APP_SOURCE.read_text(encoding="utf-8")

    def test_the_route_path_is_declared_as_a_literal(self) -> None:
        from server_v1_app import COMBAT_PATH

        self.assertEqual("/v1/combat", COMBAT_PATH)
        self.assertIn('COMBAT_PATH = "/v1/combat"', self.source)

    def test_the_route_is_registered_in_the_route_table(self) -> None:
        from server_v1_app import ROUTES

        self.assertEqual(4, len(ROUTES))
        self.assertEqual("combat", ROUTES["POST /v1/combat"])

    def test_the_route_is_not_named_after_a_legacy_command(self) -> None:
        """Task 4.2: v1's vocabulary is not a subset of the 63 branch names."""
        from server_v1_app import ROUTES

        self.assertEqual([], [route for route in ROUTES if "attack" in route])
        self.assertNotIn("end_attack", self.source.split('"""')[0] + "" or "")

    def test_the_transport_names_no_refusal_code(self) -> None:
        """D10, restated for the fourth route."""
        tree = ast.parse(self.source)
        codes = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "RefusalCode"
        }
        self.assertEqual(set(), codes)

    def test_the_four_route_handlers_are_structurally_identical(self) -> None:
        """A per-route branch would be the change this forbids.

        Compared over the **code** with comments and strings blanked, and with a
        **leading** docstring ``Expr`` dropped: ``post_collection`` is the only one
        of the four without a docstring, so leaving it in makes that handler count
        one statement fewer than its three siblings and the comparison reports "a
        route grew a statement" for a route that grew nothing.  Measured raw
        statement counts are 7/6/7/7; after dropping the leading docstring they
        are 6 for all four.
        """
        tree = ast.parse(self.source)
        bodies = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("post_"):
                statements = list(node.body)
                if (
                    statements
                    and isinstance(statements[0], ast.Expr)
                    and isinstance(statements[0].value, ast.Constant)
                    and isinstance(statements[0].value.value, str)
                ):
                    statements = statements[1:]
                bodies[node.name] = [
                    _code_only(ast.unparse(statement)) for statement in statements
                ]
        self.assertEqual(
            {"post_collect", "post_collection", "post_combat", "post_magic"},
            set(bodies),
        )
        shapes = {name: len(segments) for name, segments in bodies.items()}
        self.assertEqual(
            {"post_collect": 6, "post_collection": 6, "post_combat": 6, "post_magic": 6},
            shapes,
        )
        self.assertEqual(1, len(set(shapes.values())), "a route grew a statement")

        # Body-for-body, with **only the domain entry point normalised**.  The four
        # handlers differ in exactly one token -- the name of the function they
        # call -- and that difference is the route's whole purpose, so demanding
        # raw equality would be demanding that the fourth route be the third route.
        # An earlier draft compared raw and failed on that single token; the fix is
        # to normalise the one legitimate difference rather than to weaken the
        # comparison to a statement count.
        #
        # The four callee names are **measured** from the module, not assumed: an
        # earlier draft invented ``apply_collect``/``apply_collection`` and both
        # are absent from the transport, so three subTests failed on replacements
        # that could never fire.  ``collect`` is normalised **last** because
        # ``complete_collection`` would otherwise survive it -- neither name is a
        # substring of the other, but the shorter is a substring of nothing else
        # here and ordering the longest first keeps that true by construction
        # rather than by luck.
        CALLEES = ("apply_combat", "apply_magic", "complete_collection", "collect")

        def normalise(segments: List[str]) -> List[str]:
            normalised = list(segments)
            for callee in CALLEES:
                normalised = [
                    segment.replace(callee + "(", "apply_X(") for segment in normalised
                ]
            return normalised

        for name in ("post_collect", "post_collection", "post_combat"):
            with self.subTest(route=name):
                self.assertEqual(
                    normalise(bodies["post_magic"]),
                    normalise(bodies[name]),
                    "%s is not body-for-body the magic route" % name,
                )
        self.assertEqual(
            1,
            len(
                {
                    tuple(normalise(segments))
                    for segments in bodies.values()
                }
            ),
            "the four handlers are not one shape",
        )

    def test_the_transport_does_not_decide_whether_a_destruction_shape_was_carried(self) -> None:
        """The refusal is the domain's, so a ``destruction_request`` branch here
        would be the transport deciding what a transaction would have destroyed."""
        body = _code_only(self.source)
        start = body.index("def post_combat")
        end = body.index("def post_magic")
        self.assertNotIn("destruction", body[start:end])


class CommittedOracleTests(unittest.TestCase):
    """The committed fixture, read as bytes and never re-captured.

    Task 9.2: this line claims **no parity** against the legacy server.  The
    fixture was archived on 2026-10-05 by a delivered line; re-running the capture
    would produce the same bytes for a different commit, so every figure here is
    re-measured from the committed files rather than inherited from the manifest.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.steps_root = ORACLE_ROOT / "steps"
        cls.request_files = sorted(ORACLE_ROOT.rglob("request.json"))
        cls.step_dirs = sorted(path for path in cls.steps_root.iterdir() if path.is_dir())

    def test_the_oracle_directory_is_present_and_committed(self) -> None:
        self.assertTrue(ORACLE_ROOT.is_dir(), ORACLE_ROOT)
        self.assertTrue(ORACLE_ROOT.joinpath("README.md").is_file())
        self.assertTrue(ORACLE_ROOT.joinpath("capture-manifest.json").is_file())
        self.assertTrue(self.steps_root.is_dir(), self.steps_root)

    def test_the_oracle_holds_fourteen_steps_and_thirteen_transactions(self) -> None:
        """Fourteen step directories including the login; **thirteen** transactions.

        ``transaction.json`` is what separates the two.  ``login_post`` carries a
        response but no transaction, because it is the session-establishing step and
        not one of the recorded transactions.  14 steps, 13 transactions.

        An earlier draft counted *request documents* whose parent was not ``steps``,
        which is 0 -- every ``request.json`` lives inside a step directory.  The
        discriminator is ``transaction.json`` on disk, not the parent path, and this
        test replaces that vacuous count with one that measures something.
        """
        self.assertEqual(14, len(self.step_dirs))
        self.assertEqual(14, len(self.request_files))
        with_txn = [
            path for path in self.step_dirs if path.joinpath("transaction.json").is_file()
        ]
        self.assertEqual(13, len(with_txn))
        self.assertEqual(["login_post"], [p.name for p in self.step_dirs if p not in with_txn])

    def test_ten_of_them_carry_the_preserved_branch_name(self) -> None:
        """Ten transactions carrying ``end_attack``, and eleven occurrences.

        Counted **without** the surrounding quotes.  Each ``request.json`` holds the
        command batch as a JSON *string*, so the branch name is escaped inside it as
        ``\\"end_attack\\"`` and a search for ``'"end_attack"'`` matches **zero**
        occurrences in every one of the fourteen documents -- which is how an earlier
        draft of this test failed while claiming to measure a count.  One step
        (``txn_resolve_batch_discarded_on_raise``) carries it twice.
        """
        carrying = 0
        occurrences = 0
        for path in self.request_files:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(
                0,
                text.count('"end_attack"'),
                "%s: the branch name is escaped inside the command blob" % path.parent.name,
            )
            found = text.count("end_attack")
            occurrences += found
            if found:
                carrying += 1
        self.assertEqual(10, carrying)
        self.assertEqual(11, occurrences)

    def test_three_steps_answered_http_500_with_a_byte_identical_save(self) -> None:
        """Task 9.3, the established half, asserted from the committed files.

        **Three**, not two: ``txn_resolve_absent_attacker_units``,
        ``txn_resolve_absent_victim`` and ``txn_resolve_batch_discarded_on_raise``
        all answered 500, and all three have byte-identical ``before.json`` and
        ``after.json``.  An earlier draft asserted two and failed; the three are the
        preserved server's *three* ``None`` dereferences at ``command.py:866``,
        ``:871`` and ``:874`` -- so this is the same count seen from the fixture
        side, and it is why the wire message names two line numbers rather than
        three.
        """
        with_txn = [
            path
            for path in self.step_dirs
            if path.joinpath("transaction.json").is_file()
        ]
        self.assertEqual(13, len(with_txn))
        failing = []
        for path in with_txn:
            meta = json.loads(path.joinpath("response.meta.json").read_text(encoding="utf-8"))
            if meta.get("status") != 500:
                continue
            failing.append(path.name)
            self.assertEqual(
                path.joinpath("before.json").read_bytes(),
                path.joinpath("after.json").read_bytes(),
                "%s answered 500 but mutated the save" % path.name,
            )
        self.assertEqual(
            [
                "txn_resolve_absent_attacker_units",
                "txn_resolve_absent_victim",
                "txn_resolve_batch_discarded_on_raise",
            ],
            failing,
        )

    def test_the_oracle_is_read_as_bytes_and_not_re_captured(self) -> None:
        """The containment this class asserts: no capture tool runs here.

        Scanned over the **code-only** text of this file.  Raw text contains every
        forbidden token inside this class's own docstrings and forbidden-token tuples,
        so the raw scan is self-tripping -- which is the shape
        ``godot-construction-assist`` measured and fixed: a guard whose own
        inventory trips it unconditionally is not a guard.
        """
        code = _code_only(Path(__file__).read_text(encoding="utf-8"))
        for forbidden in ("subprocess", "capture_combat_fixture", "capture_legacy_fixtures"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_no_reachable_name_or_token_in_this_module_reaches_the_network(self) -> None:
        """The file is hermetic; the live phase is a different suite entirely.

        Scanned over the **code-only** text, because raw text contains every
        forbidden token inside this class's own docstrings and tuples -- a guard that
        trips on its own inventory is not a guard, which
        ``godot-construction-assist`` measured and recorded.

        ``_code_only`` blanks string literals, so it also removes every mention in
        prose; what survives is **identifiers**.  That is why this method is named
        after the network rather than after the transport module: two earlier
        drafts both spelled the forbidden module's own name into their own ``def``
        line -- ``..._opens_a_socket`` -- and tripped their own guard on it.  Two
        failures, not one, is why this method now says what it forbids rather than
        what it scans.  :meth:`test_no_delivered_identifier_carries_a_forbidden_token`
        pins the rename so it cannot be undone by a well-meaning edit.
        """
        code = _code_only(Path(__file__).read_text(encoding="utf-8"))
        for forbidden in ("socket", "urlopen", "http.server", "requests"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_no_delivered_identifier_carries_a_forbidden_token(self) -> None:
        """The rename above, pinned so it cannot be undone by a well-meaning edit.

        Declared **names** only -- the code-only scan is the other half.  Together
        they say the token appears nowhere in the module except inside prose and
        string literals, neither of which executes.
        """
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
        for forbidden in ("socket", "urlopen", "http.server", "requests", "subprocess"):
            with self.subTest(forbidden=forbidden):
                self.assertEqual(
                    [],
                    sorted(name for name in names if forbidden in name.lower()),
                )


class VocabularyTests(unittest.TestCase):
    """Task 1: the one new code, and the pin one step from tripping."""

    def test_exactly_one_code_was_added_by_this_line(self) -> None:
        """Task 1.7: **one** code, not four.

        ``honor``, ``resources``, ``resources_victim`` and ``townhall_gold`` are
        read and discarded by the preserved branch and are closed by the existing
        ``client_supplied_delta`` key-name channel.  Three or four codes for one
        decision is how a closed vocabulary stops being closed.
        """
        self.assertEqual(20, len(list(RefusalCode)))
        self.assertIn(RefusalCode.CLIENT_DICTATED_DESTRUCTION, list(RefusalCode))
        code_only = _code_only(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        named = {
            node.attr
            for node in ast.walk(ast.parse(DOMAIN_SOURCE.read_text(encoding="utf-8")))
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "RefusalCode"
        }
        self.assertEqual(
            {
                "CLIENT_DICTATED_DESTRUCTION",
                "MALFORMED_REQUEST",
                "POST_CONDITION_VIOLATION",
                "UNADDRESSABLE_ROW",
                "UNKNOWN_PLAYER",
                "UNREADABLE_CONTENT",
                "UNREADABLE_STATE",
            },
            named,
            code_only[:0],
        )

    def test_no_code_was_added_for_the_discarded_quantities(self) -> None:
        for name in ("HONOR", "TOWNHALL", "RESOURCES_VICTIM", "DAMAGE", "LIFE"):
            with self.subTest(name=name):
                self.assertNotIn(
                    name, {code.name for code in RefusalCode}, "a second code was added"
                )

    def test_the_vocabulary_is_one_code_from_tripping_the_size_pin(self) -> None:
        """Task 1.5 restated: the pin is ``< 21`` and this line leaves it at 20.

        The pin's own spelling is read from the file that holds it, so an amendment
        there fails here instead of being discovered a line later.
        """
        pin = (harness.TESTS_DIR / "test_boundary_invariant.py").read_text(encoding="utf-8")
        self.assertIn("self.assertLess(len(list(RefusalCode)), 21)", pin)
        self.assertLess(len(list(RefusalCode)), 21)
        self.assertEqual(20, len(list(RefusalCode)))

    def test_the_new_code_is_named_by_the_domain(self) -> None:
        code_only = _code_only(DOMAIN_SOURCE.read_text(encoding="utf-8"))
        self.assertIn("RefusalCode.CLIENT_DICTATED_DESTRUCTION", code_only)

    def test_the_new_code_spelling_is_the_v0_literal(self) -> None:
        self.assertEqual(
            "client_dictated_destruction", RefusalCode.CLIENT_DICTATED_DESTRUCTION.value
        )
        v0 = harness.REPO_ROOT / "apps" / "compat-api" / "combat_envelope.py"
        self.assertTrue(v0.is_file())
        self.assertIn(
            '"client_dictated_destruction"', v0.read_text(encoding="utf-8")
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()