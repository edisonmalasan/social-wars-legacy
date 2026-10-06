#!/usr/bin/env python3
"""Offline unit tests for ``darts_envelope`` (OpenSpec tasks 6.1 / 6.4).

No server, no socket, no network, and no corpus mutation: everything here is
either a pure derivation over one intent or a **measurement** of the committed
bytes themselves -- the eleven legacy root modules, ``config/main.json``, the
normalized content package, and the 33 canonical save documents -- so every
recorded constant here is derived at run time rather than restated from this
line's own prose (the standing rule that a figure asserted rather than measured
is worthless, established by corrections C1-C4 of
``docs/legacy-m11-darts.md``).

The three derived decisions are asserted as behavior:

* **D6 / design D6** the derived vector is **neutral** -- ``[0]*8`` -- because the
  committed ``PREMIUM_ACCOUNTS`` amount has **zero** consumers, which is measured
  here over all eleven modules rather than asserted;
* **D3 / D7** the shot's second slot is **derived** as ``False`` and is never
  accepted from a client, because ``command.py:595`` indexes ``args[1]``
  unconditionally -- so it cannot be omitted either -- and a falsy value makes
  the branch's conditional ``dartsGotExtra`` write not execute;
* **D3 / D8** the shot list is **unbounded** and the shot index is **never tested
  against the committed schedule**, which is asserted *positively* against the
  corpus: a committed document records the shot index ``0``, absent from the
  committed ``1..27`` ids, so a membership test would contradict the save.

Measured refusals, all structural, all before dispatch:

* the action vocabulary is closed at **four** names;
* ``seed``, ``shot_index``, and ``package_index`` must each be a strict integer,
  where ``bool`` is refused (``isinstance(True, int)`` is true, so this is a real
  hole and it is closed);
* the two invented rules -- a shot-list length bound and a schedule-membership
  test -- have **no** function that could express them, which is why the
  whole-module function inventory is pinned rather than a name list.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import unittest
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness  # noqa: F401  (path setup)

import darts_envelope as envelope_mod

REPO = harness.REPO_ROOT

#: The **eleven** legacy root modules.  The first seven are the original set the
#: earlier delivered lines searched; the four extras were added by this line's
#: investigation because their absence is what makes the ``fast_forward`` and
#: weekly-reset findings safe to claim (``docs/legacy-m11-darts.md`` A5).
LEGACY_MODULES = (
    "command.py",
    "engine.py",
    "sessions.py",
    "server.py",
    "constants.py",
    "version.py",
    "auctions.py",
    "bundle.py",
    "get_game_config.py",
    "get_player_info.py",
    "legacy_command_recorder.py",
)

#: The darts and premium fields, all in ``privateState``.
DARTS_FIELDS = (
    "dartsRandomSeed",
    "dartsBalloonsShot",
    "dartsGotExtra",
    "dartsHasFree",
    "timeStampDartsReset",
    "timeStampDartsNewFree",
    "timeStampEndPremium",
)

#: The whole function inventory of ``darts_envelope``.  This is the gate: any
#: helper added to the module fails here even when its name borrows no reserved
#: word, which is exactly the limitation the name-based guard below was measured
#: to have (an injected ``premium_charge`` fires **one** guard, not two).
EXPECTED_MODULE_FUNCTIONS = [
    "_command_entry",
    "_command_for",
    "build_envelope",
    "neutral_vector",
]

#: Helper names whose mere existence would be an invented rule.
FORBIDDEN_HELPERS = [
    "premium_charge",
    "premium_price",
    "cost_for",
    "in_schedule",
    "shot_limit",
    "max_shots",
    "verify_win",
    "normalize",
    "weekday",
    "seed_schedule",
]

#: Identifiers that may carry these words, because they are the module's own
#: RECORDED refusals rather than an implementation of the refused rule.
RECORDED_REFUSAL_NAMES = {
    "DERIVED_SHOT_OUTCOME",
    "REASON_UNKNOWN_ACTION",
    "REASON_INVALID_SEED",
    "REASON_INVALID_SHOT_INDEX",
    "REASON_INVALID_PACKAGE_INDEX",
    "REASON_BAD_REQUEST",
    "REASONS",
}

#: Words whose presence in an identifier would mean an invented rule, with the
#: documented exemptions.
GUARDED_WORDS = {
    "price": {"NO_PRICE"},
    "charge": {"NO_CHARGE"},
    "cost": set(),
    "weekday": set(),
    "week": {"week"},
    "win": set(),
    "verify": set(),
    "membership": set(),
    "bound": {"shot_list_length_bound"},
}


# --------------------------------------------------------------------------
# committed-byte readers
# --------------------------------------------------------------------------


def module_source() -> str:
    return Path(envelope_mod.__file__).read_text(encoding="utf-8")


def module_code() -> str:
    """The module's source with **comments and docstrings blanked**.

    Used for every "no delivered code does X" guard, because this module's prose
    *deliberately* names each refused rule in its docstring -- the refusal must be
    documented, and a docstring must therefore never be able to fail a code guard.
    Docstring lines are blanked by **line range** taken from the AST, never by
    string substitution: a multi-line docstring's ``repr()`` does not appear
    verbatim in its own source, so the substitution silently matched nothing.

    Non-docstring string literals are **kept**, because in this codebase every
    persistence field is reached through a dict subscript and so its name lives
    inside a string.
    """
    return _blank_docstrings(module_source())


def module_functions() -> List[str]:
    tree = ast.parse(module_source())
    return sorted(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def module_identifiers() -> List[str]:
    """Every identifier the module's **code** declares or references.

    Parsed from the AST rather than grepped, so a word inside a docstring or a
    comment cannot contribute -- the class of defect corrections C1 and C2 of
    ``docs/legacy-m11-darts.md`` exist to prevent.
    """
    tree = ast.parse(module_source())
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
    return names


def legacy_text(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


def code_only_lines(name: str) -> List[Tuple[int, str]]:
    """``(line, text)`` over **uncommented** source lines of a legacy module.

    Comments are blanked, string contents are **preserved**.  That asymmetry is
    deliberate and load-bearing: every persistence field in this codebase is
    reached through a dict subscript, so the field name lives *inside* a string.
    A probe that erased strings reported zero consumers for a field plainly
    assigned at ``command.py:578`` -- the instrument fault recorded above.
    """
    out: List[Tuple[int, str]] = []
    for number, line in enumerate(legacy_text(name).split("\n"), 1):
        out.append((number, _strip_comment(line)))
    return out


def _strip_comment(line: str) -> str:
    """Blank a trailing ``#`` comment, respecting quotes. String contents kept."""
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return line[:index]
    return line


def branch_body(command: str) -> Tuple[int, int, List[Tuple[int, str]]]:
    """``(first_line, last_line, comment_stripped_lines)`` of one dispatcher branch.

    ``last_line`` is the line **before** the next branch, so the two are
    adjacent.  Measured out of ``command.py`` rather than hardcoded, so a branch
    that moved would still be found and its contents still be measured.
    """
    lines = legacy_text("command.py").split("\n")
    start = None
    for index, line in enumerate(lines):
        if line.strip() == 'elif cmd == "%s":' % command:
            start = index
            break
    if start is None:
        raise AssertionError("no dispatcher branch named %r" % command)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("elif cmd ==") or stripped.startswith("if cmd =="):
            return (
                start + 1,
                index,
                [
                    # Absolute line numbers: ``start + number + 1``, not ``number
                    # + 1``.  A relative numbering silently turns every measured
                    # line number into a small offset, which is how a test can
                    # assert ``918`` and observe ``14`` and read it as a defect in
                    # the code under test rather than in the probe.
                    (start + number + 1, _strip_comment(text))
                    for number, text in enumerate(lines[start:index])
                ],
            )
    raise AssertionError("unterminated branch %r" % command)


def fast_forward_body() -> Tuple[int, int, List[Tuple[int, str]]]:
    """``fast_forward``'s span, found by its **content** rather than its end.

    It is the last branch in the dispatcher, so there is no following
    ``elif cmd ==`` to stop at.  Its terminator is the next top-level ``def``.
    """
    lines = legacy_text("command.py").split("\n")
    start = None
    for index, line in enumerate(lines):
        if line.strip() == 'elif cmd == "fast_forward":':
            start = index
            break
    if start is None:
        raise AssertionError("no fast_forward branch")
    stop = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("def ") or lines[index].strip().startswith(
            'elif cmd == "'
        ):
            stop = index
            break
    return (
        start + 1,
        stop,
        [
            (start + number + 1, _strip_comment(text))
            for number, text in enumerate(lines[start:stop])
        ],
    )


def canonical_documents() -> List[Tuple[str, Dict[str, Any]]]:
    """The 33 canonical corpus documents, re-derived every run.

    The definition is the settled one (``tests/saves`` + ``villages``, excluding
    ``tests/saves/manifest.json``, counting a document carrying at least one
    map).  Correction **C3** replaced an earlier whole-repository walk whose
    denominator of 231 was inflated roughly sevenfold by 200 generated
    ``tests/fixtures/**`` ``before.json``/``after.json`` pairs.
    """
    documents: List[Tuple[str, Dict[str, Any]]] = []
    for root in ("tests/saves", "villages"):
        base = REPO / root
        for directory, _subdirs, names in os.walk(str(base)):
            for name in sorted(names):
                if not name.endswith(".json") or name == "manifest.json":
                    continue
                path = os.path.join(directory, name)
                relative = os.path.relpath(path, str(REPO)).replace(os.sep, "/")
                try:
                    document = json.loads(
                        io.open(path, encoding="utf-8").read()
                    )
                except ValueError:
                    continue
                maps = document.get("maps")
                if isinstance(maps, list) and any(
                    isinstance(entry, dict) for entry in maps
                ):
                    documents.append((relative, document))
    documents.sort()
    return documents


def _blank_docstrings(source: str) -> str:
    """Blank every module/class/function docstring, by AST line range."""
    lines = source.split("\n")
    blanked = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            start = first.lineno
            stop = getattr(first.value, "end_lineno", start) or start
            blanked.update(range(start, stop + 1))
    return "\n".join(
        "" if number in blanked else _strip_comment(line)
        for number, line in enumerate(lines, 1)
    )


def _route_code() -> str:
    """The ``/v0/darts`` route body with its docstring blanked.

    The route is located through the **whole parsed module** rather than by
    slicing text: an extracted fragment cannot be parsed on its own, so an
    ``ast.parse``-based docstring blanker raises ``SyntaxError: unmatched ')'`` on
    the trailing ``app.config[...]`` line and the guard would pass vacuously.
    """
    service_path = REPO / "apps" / "compat-api" / "compat_service.py"
    source = service_path.read_text(encoding="utf-8")
    lines = source.split("\n")
    blanked = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef) or node.name != "v0_darts":
            continue
        body = getattr(node, "body", [])
        first = body[0]
        start = first.lineno
        stop = getattr(first.value, "end_lineno", start) or start
        blanked.update(range(start, stop + 1))
        return "\n".join(
            "" if number in blanked else _strip_comment(line)
            for number, line in enumerate(lines, 1)
            if node.lineno <= number <= node.end_lineno
        )
    raise AssertionError("no v0_darts route in compat_service.py")


def config() -> Dict[str, Any]:
    return json.loads((REPO / "config" / "main.json").read_text(encoding="utf-8"))


def darts_schedule_ids() -> List[int]:
    rows = json.loads(
        (REPO / "packages" / "game-content" / "normalized" / "darts_items.json")
        .read_text(encoding="utf-8")
    )
    return sorted(int(row["id"]) for row in rows)


# --------------------------------------------------------------------------
# vocabulary
# --------------------------------------------------------------------------


class VocabularyTests(unittest.TestCase):
    """Task 6.1: the action set is closed and matches the delivered transitions."""

    def test_the_vocabulary_is_closed_and_holds_exactly_four_actions(self) -> None:
        self.assertEqual(
            list(envelope_mod.ACTIONS),
            [
                "darts_reset",
                "darts_new_free",
                "darts_shoot_balloon",
                "buy_premium_account",
            ],
        )

    def test_each_action_is_the_committed_command_name(self) -> None:
        for command in envelope_mod.ACTIONS:
            with self.subTest(action=command):
                first, _last, _lines = branch_body(command)
                self.assertGreater(first, 0)

    def test_no_fifth_darts_command_exists_in_the_preserved_server(self) -> None:
        """``fast_forward`` touches ``timeStampDartsNewFree`` but is **absent** from
        the vocabulary by decision -- no fast-forward operation is delivered."""
        found = sorted(
            match.group(1)
            for match in re.finditer(
                r'^\s*elif cmd == "(\w+)":', legacy_text("command.py"), re.MULTILINE
            )
            if "darts" in match.group(1) or "premium" in match.group(1)
        )
        self.assertEqual(found, sorted(envelope_mod.ACTIONS))

    def test_fast_forward_is_absent_from_the_vocabulary_by_decision(self) -> None:
        self.assertNotIn("fast_forward", envelope_mod.ACTIONS)
        self.assertIn("fast_forward", legacy_text("command.py"))


# --------------------------------------------------------------------------
# branch effects, measured out of command.py
# --------------------------------------------------------------------------


class BranchEffectTests(unittest.TestCase):
    """Every branch effect is measured, not restated."""

    def test_the_reset_branch_writes_exactly_the_six_recorded_fields(self) -> None:
        _first, _last, lines = branch_body("darts_reset")
        body = "\n".join(text for _number, text in lines)
        self.assertEqual(
            sorted(set(re.findall(r'privateState\["(\w+)"\]', body))),
            sorted(
                [
                    "dartsRandomSeed",
                    "dartsBalloonsShot",
                    "dartsGotExtra",
                    "dartsHasFree",
                    "timeStampDartsReset",
                    "timeStampDartsNewFree",
                ]
            ),
        )

    def test_the_free_branch_writes_exactly_two_fields_and_takes_no_argument(self) -> None:
        _first, _last, lines = branch_body("darts_new_free")
        body = "\n".join(text for _number, text in lines)
        self.assertEqual(
            sorted(set(re.findall(r'privateState\["(\w+)"\]', body))),
            ["dartsHasFree", "timeStampDartsNewFree"],
        )
        self.assertEqual(re.findall(r"args\[(\d)\]", body), [])

    def test_the_shoot_branch_reads_two_arguments_and_writes_three_fields(self) -> None:
        _first, _last, lines = branch_body("darts_shoot_balloon")
        body = "\n".join(text for _number, text in lines)
        self.assertEqual(sorted(set(re.findall(r"args\[(\d)\]", body))), ["0", "1"])
        # Four fields are *reached* through a subscript, but ``dartsBalloonsShot``
        # is reached by the read that binds the alias the branch then appends to,
        # so exactly **three** are writes.
        self.assertEqual(
            sorted(set(re.findall(r'privateState\["(\w+)"\]', body))),
            [
                "dartsBalloonsShot",
                "dartsGotExtra",
                "dartsHasFree",
                "timeStampDartsNewFree",
            ],
        )
        writes = sorted(
            set(
                re.findall(
                    r'privateState\["(\w+)"\] = ', body
                )
            )
        )
        self.assertEqual(
            writes, ["dartsGotExtra", "dartsHasFree", "timeStampDartsNewFree"]
        )
        self.assertIn('privateState["dartsBalloonsShot"]', body)
        self.assertIn("targets = privateState[\"dartsBalloonsShot\"]", body)

    def test_the_shoot_branch_appends_only_when_the_index_is_absent(self) -> None:
        _first, _last, lines = branch_body("darts_shoot_balloon")
        body = "\n".join(text for _number, text in lines)
        self.assertIn("if index not in targets:", body)
        self.assertIn("targets.append(index)", body)

    def test_the_shoot_branch_appends_without_any_bound_or_membership_test(self) -> None:
        _first, _last, lines = branch_body("darts_shoot_balloon")
        body = "\n".join(text for _number, text in lines)
        guard = body[body.index("if index not in targets:") :]
        for banned in ("len(targets)", "range(", "darts_items", "darts_item"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, guard)

    def test_the_premium_branch_writes_the_instant_on_exactly_two_arms(self) -> None:
        _first, _last, lines = branch_body("buy_premium_account")
        body = "\n".join(text for _number, text in lines)
        self.assertEqual(
            sorted(set(re.findall(r'privateState\["(\w+)"\]', body))),
            ["timeStampEndPremium"],
        )
        self.assertIn("if time_now >= ts_premium:", body)
        self.assertIn(
            "privateState[\"timeStampEndPremium\"] = time_now + days * 86400", body
        )
        self.assertIn(
            "privateState[\"timeStampEndPremium\"] += days * 86400", body
        )

    def test_the_premium_branch_reads_exactly_one_argument(self) -> None:
        _first, _last, lines = branch_body("buy_premium_account")
        body = "\n".join(text for _number, text in lines)
        self.assertEqual(sorted(set(re.findall(r"args\[(\d)\]", body))), ["0"])


# --------------------------------------------------------------------------
# the derived shot outcome (D3/D7)
# --------------------------------------------------------------------------


class DerivedShotOutcomeTests(unittest.TestCase):
    """The single most consequential line in the module."""

    def test_the_outcome_slot_is_derived_false_and_never_client_supplied(self) -> None:
        self.assertIs(envelope_mod.DERIVED_SHOT_OUTCOME, False)

    def test_the_branch_indexes_the_second_slot_unconditionally(self) -> None:
        """Why the slot cannot simply be omitted."""
        _first, _last, lines = branch_body("darts_shoot_balloon")
        body = "\n".join(text for _number, text in lines)
        self.assertIn("won_extra = args[1]", body)
        # Not guarded, not defaulted: a bare subscript assignment.
        assignment = [t for t in body.split("\n") if "args[1]" in t][0]
        self.assertNotIn("args[0]", assignment)
        self.assertNotIn("if", assignment.strip())

    def test_a_truthy_outcome_is_the_only_thing_that_writes_the_flag(self) -> None:
        _first, _last, lines = branch_body("darts_shoot_balloon")
        body = "\n".join(text for _number, text in lines)
        self.assertIn("if won_extra:", body)
        self.assertIn('privateState["dartsGotExtra"] = True', body)
        # Exactly two guarded reads of the client value, both the truthiness test.
        self.assertEqual(body.count("if won_extra:"), 2)

    def test_the_envelope_sends_the_derived_slot_and_ignores_a_client_claim(self) -> None:
        for claimed in (True, False, 1, 0, "yes", None, [], {"a": 1}):
            with self.subTest(claimed=claimed):
                built = envelope_mod.build_envelope(
                    "darts_shoot_balloon",
                    {"shot_index": 5, "won_extra": claimed},
                    ts=1,
                )
                self.assertEqual(built["commands"][0][2], [5, False])

    def test_the_client_won_flag_cannot_reach_the_envelope_in_any_slot(self) -> None:
        built = envelope_mod.build_envelope(
            "darts_shoot_balloon",
            {"shot_index": 5, "won_extra": True, "won": True, "result": "win"},
            ts=1,
        )
        self.assertNotIn(True, built["commands"][0][2])
        self.assertEqual(len(built["commands"][0][2]), 2)

    def test_the_corpus_records_no_won_shot_in_either_direction(self) -> None:
        """Correction **C4**: ``dartsGotExtra`` is ``false`` in **33 of 33**.
        So the refusal has **no corpus evidence either way** and the divergence is
        recorded as such rather than as a measured difference."""
        distribution = Counter(
            (document.get("privateState") or {}).get("dartsGotExtra")
            for _path, document in canonical_documents()
        )
        self.assertEqual(dict(distribution), {False: 33})


# --------------------------------------------------------------------------
# the neutral vector (D6)
# --------------------------------------------------------------------------


class NeutralVectorTests(unittest.TestCase):
    """Nothing is charged -- a **refusal**, and measured as one."""

    def test_the_neutral_vector_is_eight_zeros(self) -> None:
        self.assertEqual(envelope_mod.neutral_vector(), [0, 0, 0, 0, 0, 0, 0, 0])

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.neutral_vector()
        first[0] = 99
        self.assertEqual(envelope_mod.neutral_vector()[0], 0)

    def test_the_vector_width_is_the_legacy_eight_slot_shape(self) -> None:
        """``apply_resources`` unpacks exactly **eight** slots and **discards** the
        first -- ``unknown`` is read and never written -- so a seven-slot derived
        vector would be a shape error rather than a neutral value."""
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)
        lines = legacy_text("engine.py").split("\n")
        start = [
            number
            for number, text in enumerate(lines)
            if text.startswith("def apply_resources")
        ]
        self.assertEqual(len(start), 1)
        body = "\n".join(_strip_comment(t) for t in lines[start[0] : start[0] + 25])
        for slot in range(8):
            with self.subTest(slot=slot):
                self.assertIn("resource[%d]" % slot, body)
        # Slot 0 is read into a name nothing else uses, and it is never written.
        self.assertIn("unknown = resource[0]", body)
        self.assertNotIn("unknown", body[body.index("map[\"xp\"]") :])
        # Seven write targets, each clamped at zero, and all seven are what this
        # service's ``resources()`` accessor exposes.
        self.assertEqual(body.count("max("), 7)
        for target in (
            'map["xp"]',
            'map["gold"]',
            'map["wood"]',
            'map["oil"]',
            'map["steel"]',
            'save["playerInfo"]["cash"]',
            'save["privateState"]["mana"]',
        ):
            with self.subTest(target=target):
                self.assertIn(target + " = max(", body)

    def test_the_vector_is_applied_before_the_branch_and_not_after(self) -> None:
        """The reason "nothing is charged" is a **refusal, not parity**.

        Measured shape: the dispatcher loops the batch and calls
        ``do_command(USERID, map_id, cmd, args, resources_changed)``
        (``command.py:30``); ``do_command`` takes that vector as a **parameter**,
        applies it at ``:40``, and only then enters the ``if cmd == ...`` chain at
        ``:42``.  So a client that paired a debit with this purchase would have
        moved a balance inside the preserved server, before any darts branch ran.
        """
        lines = legacy_text("command.py").split("\n")
        apply_at = [n for n, t in enumerate(lines) if "apply_resources(save, map, resources_changed)" in t][0]
        dispatch_at = [
            n for n, t in enumerate(lines) if "do_command(USERID, map_id, cmd, args, resources_changed)" in t
        ][0]
        self.assertEqual((dispatch_at + 1, apply_at + 1), (30, 40))
        # Every branch opens at or after :42, so no branch precedes the application.
        branch_at = [
            n for n, t in enumerate(lines) if t.strip() == 'if cmd == "buy":'
        ][0]
        self.assertGreater(branch_at, apply_at)
        self.assertEqual(
            len([n for n, t in enumerate(lines) if 'elif cmd == "' in t]), 62
        )

    def test_a_client_sent_debit_would_really_move_a_balance_through_apply_resources(self) -> None:
        """Non-tautological by construction: the clamp is a real
        ``max(current + delta, 0)``, so a negative delta on a non-zero balance is
        not a no-op.  Measured out of the legacy body rather than assumed."""
        lines = legacy_text("engine.py").split("\n")
        start = [
            number
            for number, text in enumerate(lines)
            if text.startswith("def apply_resources")
        ][0]
        body = "\n".join(_strip_comment(t) for t in lines[start : start + 25])
        self.assertEqual(body.count("= max("), 7)
        self.assertIn('map["gold"] = max(map["gold"] + gold, 0)', body)
        self.assertIn('save["privateState"]["mana"] = max(save["privateState"]["mana"] + mana, 0)', body)

    def test_the_committed_amount_has_zero_consumers(self) -> None:
        """``PREMIUM_ACCOUNTS`` carries a price beside every duration and nothing
        reads it -- measured over all eleven modules."""
        schedule = config()["globals"]["PREMIUM_ACCOUNTS"]
        self.assertEqual(len(schedule), 6)
        for row in schedule:
            self.assertIn("price", row)
            self.assertIn("time", row)

        # The only consumer of the committed schedule at all is the one helper.
        schedule_sites = sorted(
            name for name in LEGACY_MODULES if "PREMIUM_ACCOUNTS" in legacy_text(name)
        )
        self.assertEqual(schedule_sites, ["get_game_config.py"])
        self.assertEqual(legacy_text("get_game_config.py").count("PREMIUM_ACCOUNTS"), 1)

    def test_get_premium_days_returns_the_duration_and_never_the_amount(self) -> None:
        lines = legacy_text("get_game_config.py").split("\n")
        start = [n for n, t in enumerate(lines) if "def get_premium_days" in t][0]
        stop = start + 1
        while stop < len(lines) and not lines[stop].startswith("def "):
            stop += 1
        body = "\n".join(_strip_comment(t) for t in lines[start:stop])
        self.assertIn('return package["time"]', body)
        self.assertIn("return 0", body)
        self.assertNotIn("price", body)

    def test_the_committed_durations_and_amounts_are_read_verbatim(self) -> None:
        schedule = config()["globals"]["PREMIUM_ACCOUNTS"]
        self.assertEqual([row["time"] for row in schedule], [360, 180, 30, 7, 3, 1])
        self.assertEqual([row["price"] for row in schedule], [800, 450, 80, 40, 20, 8])

    def test_the_route_code_never_reads_the_committed_amount(self) -> None:
        """Checked over the route's **code**, with its docstring blanked.  The
        route's prose deliberately names ``PREMIUM_ACCOUNTS`` to record that the
        committed amount has zero consumers, and its ``internal_error`` message
        names the schedule too -- neither is a *read*, so the guard targets the two
        forms that would be one: a subscript and a ``.get()``."""
        route = _route_code()
        for banned in ('["price"]', '.get("price")', '["PREMIUM_ACCOUNTS"]', '.get("PREMIUM_ACCOUNTS")'):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, route)
        self.assertIn('"charged": False', route)
        self.assertIn('"committed_amount_consumers": 0', route)

    def test_the_route_ignores_a_client_sent_amount_even_when_it_is_valid(self) -> None:
        """The route reads its arguments from the ``arguments`` key only, so a
        top-level ``price``/``days``/``resources`` cannot be mistaken for one."""
        route = _route_code()
        self.assertIn('arguments = payload.get("arguments", {})', route)
        self.assertIn('darts_envelope.build_envelope(action, arguments)', route)


# --------------------------------------------------------------------------
# the two refused invented rules (D3/D8)
# --------------------------------------------------------------------------


class InventedRuleRefusalTests(unittest.TestCase):
    """No shot-list bound, no schedule-membership test -- asserted positively."""

    def test_the_committed_schedule_runs_one_to_twenty_seven(self) -> None:
        ids = darts_schedule_ids()
        self.assertEqual(len(ids), 27)
        self.assertEqual(ids, list(range(1, 28)))

    def test_a_canonical_document_records_a_shot_index_absent_from_it(self) -> None:
        """``villages/Nerri.json`` records shot ``0``.  A membership test would
        contradict the save, so the corpus is the *reason* the rule is refused."""
        in_schedule = set(darts_schedule_ids())
        out_of_schedule: List[Tuple[str, int]] = []
        for path, document in canonical_documents():
            for index in (document.get("privateState") or {}).get(
                "dartsBalloonsShot", []
            ):
                if index not in in_schedule:
                    out_of_schedule.append((path, index))
        self.assertEqual(out_of_schedule, [("villages/Nerri.json", 0)])

    def test_the_module_never_reads_the_committed_schedule(self) -> None:
        code = module_code()
        for banned in ("darts_items", "packages", "game-content", "main.json"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, code)

    def test_no_shot_list_bound_is_expressible(self) -> None:
        code = module_code()
        for banned in ("len(targets)", "max_shots", "shot_limit", "MAX_SHOTS"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, code)

    def test_a_negative_or_huge_shot_index_is_still_accepted(self) -> None:
        """Neither refused rule may leak in as a range test.  ``0`` and ``99999``
        are both delivered; ``-1`` is too, because the legacy branch stores it."""
        for index in (-1, 0, 27, 28, 99999):
            with self.subTest(index=index):
                built = envelope_mod.build_envelope(
                    "darts_shoot_balloon", {"shot_index": index}, ts=1
                )
                self.assertEqual(built["commands"][0][2], [index, False])


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


class RefusalTests(unittest.TestCase):
    """Every structural refusal, with a recorded reason and no partial build."""

    def test_the_reason_set_is_closed(self) -> None:
        self.assertEqual(
            list(envelope_mod.REASONS),
            [
                "bad_request",
                "unknown_darts_action",
                "invalid_darts_seed",
                "invalid_shot_index",
                "invalid_package_index",
            ],
        )

    def test_every_reason_is_reachable_through_the_public_entry(self) -> None:
        cases = [
            ("unknown_darts_action", "nope", {}),
            ("invalid_darts_seed", "darts_reset", {"seed": "x"}),
            ("invalid_shot_index", "darts_shoot_balloon", {"shot_index": "x"}),
            ("invalid_package_index", "buy_premium_account", {"package_index": None}),
            ("bad_request", "darts_reset", ["not", "an", "object"]),
        ]
        for reason, action, arguments in cases:
            with self.subTest(reason=reason):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope(action, arguments, ts=1)
                self.assertEqual(caught.exception.code, reason)
                self.assertTrue(str(caught.exception))

    def test_a_bool_is_refused_where_an_int_is_required(self) -> None:
        """``isinstance(True, int)`` is true, so this hole is real and closed."""
        for action, key in (
            ("darts_reset", "seed"),
            ("darts_shoot_balloon", "shot_index"),
            ("buy_premium_account", "package_index"),
        ):
            with self.subTest(action=action):
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.build_envelope(action, {key: True}, ts=1)

    def test_a_float_is_refused_rather_than_coerced(self) -> None:
        """JSON decodes every number as a float in some stacks, so this is the
        refusal that stops ``18.0`` from silently becoming ``18``."""
        for action, key in (
            ("darts_reset", "seed"),
            ("darts_shoot_balloon", "shot_index"),
            ("buy_premium_account", "package_index"),
        ):
            with self.subTest(action=action):
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.build_envelope(action, {key: 1.5}, ts=1)

    def test_a_missing_required_argument_is_refused_rather_than_defaulted(self) -> None:
        for action in ("darts_reset", "darts_shoot_balloon", "buy_premium_account"):
            with self.subTest(action=action):
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.build_envelope(action, {}, ts=1)

    def test_the_free_branch_needs_no_argument_at_all(self) -> None:
        built = envelope_mod.build_envelope("darts_new_free", None, ts=1)
        self.assertEqual(built["commands"][0][2], [])

    def test_an_unknown_action_is_refused_before_any_argument_is_read(self) -> None:
        """A bad action must not partially validate -- the request has to fail as
        a whole rather than report an argument error for a command it would never
        have dispatched."""
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.build_envelope("nope", {"seed": "x"}, ts=1)
        self.assertEqual(caught.exception.code, "unknown_darts_action")

    def test_a_non_action_is_refused(self) -> None:
        for action in (None, 5, [], {"a": 1}, True):
            with self.subTest(action=action):
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.build_envelope(action, {}, ts=1)

    def test_a_bad_timestamp_fails_closed(self) -> None:
        for ts in (-1, "x", 1.5, True):
            with self.subTest(ts=ts):
                with self.assertRaises(envelope_mod.EnvelopeError):
                    envelope_mod.build_envelope("darts_new_free", {}, ts=ts)

    def test_a_refusal_message_never_carries_save_content(self) -> None:
        for action, arguments in (
            ("darts_reset", {"seed": "SECRET-TOKEN"}),
            ("darts_shoot_balloon", {"shot_index": "SECRET-TOKEN"}),
            ("buy_premium_account", {"package_index": "SECRET-TOKEN"}),
        ):
            with self.subTest(action=action):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.build_envelope(action, arguments, ts=1)
                # The message names the *type*, never the value.
                self.assertNotIn("SECRET-TOKEN", str(caught.exception))


# --------------------------------------------------------------------------
# envelope construction
# --------------------------------------------------------------------------


class EnvelopeTests(unittest.TestCase):
    def test_the_envelope_has_exactly_the_six_legacy_keys(self) -> None:
        built = envelope_mod.build_envelope("darts_new_free", {}, ts=1)
        self.assertEqual(
            sorted(built, key=lambda key: key.lower()),
            [
                "accessToken",
                "commands",
                "first_number",
                "publishActions",
                "tries",
                "ts",
            ],
        )
        self.assertEqual(len(built), 6)
        self.assertEqual(built["first_number"], 0)
        self.assertEqual(built["publishActions"], [])
        self.assertEqual(built["tries"], 1)
        self.assertEqual(built["accessToken"], "")

    def test_the_envelope_keys_are_the_shared_serialization_keys(self) -> None:
        import placement_envelope

        built = envelope_mod.build_envelope("darts_new_free", {}, ts=1)
        self.assertEqual(sorted(built), sorted(placement_envelope.ENVELOPE_KEYS))

    def test_each_call_carries_exactly_one_command(self) -> None:
        for action, arguments in (
            ("darts_reset", {"seed": 7}),
            ("darts_new_free", {}),
            ("darts_shoot_balloon", {"shot_index": 18}),
            ("buy_premium_account", {"package_index": 0}),
        ):
            with self.subTest(action=action):
                built = envelope_mod.build_envelope(action, arguments, ts=1)
                self.assertEqual(len(built["commands"]), 1)

    def test_every_command_carries_map_zero_and_the_neutral_vector(self) -> None:
        for action, arguments in (
            ("darts_reset", {"seed": 7}),
            ("darts_new_free", {}),
            ("darts_shoot_balloon", {"shot_index": 18}),
            ("buy_premium_account", {"package_index": 0}),
        ):
            with self.subTest(action=action):
                row = envelope_mod.build_envelope(action, arguments, ts=1)["commands"][0]
                self.assertEqual(len(row), 4)
                self.assertEqual(row[0], 0)
                self.assertEqual(row[3], [0] * 8)

    def test_the_argument_list_is_exactly_the_one_each_branch_reads(self) -> None:
        expected = {
            "darts_reset": ["seed"],
            "darts_new_free": [],
            "darts_shoot_balloon": ["shot_index", "<derived outcome>"],
            "buy_premium_account": ["package_index"],
        }
        widths = {
            "darts_reset": 1,
            "darts_new_free": 0,
            "darts_shoot_balloon": 2,
            "buy_premium_account": 1,
        }
        for action, keys in expected.items():
            with self.subTest(action=action):
                arguments: Dict[str, Any] = {"seed": 7, "shot_index": 18, "package_index": 0}
                args = envelope_mod.build_envelope(action, arguments, ts=1)["commands"][0][2]
                self.assertEqual(len(args), widths[action])
                if keys and "<derived outcome>" not in keys:
                    self.assertEqual(args, [arguments[keys[0]]])

    def test_ts_defaults_to_the_current_time(self) -> None:
        import time as _time

        before = int(_time.time())
        built = envelope_mod.build_envelope("darts_new_free", {})
        after = int(_time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_an_extra_key_this_action_does_not_read_changes_nothing(self) -> None:
        plain = envelope_mod.build_envelope("darts_new_free", {}, ts=1)
        noisy = envelope_mod.build_envelope(
            "darts_new_free",
            {"seed": 3, "shot_index": 9, "package_index": 2, "resources": [9] * 8},
            ts=1,
        )
        self.assertEqual(plain, noisy)

    def test_the_data_field_round_trips_through_the_shared_serializer(self) -> None:
        for action, arguments in (
            ("darts_reset", {"seed": 7}),
            ("darts_new_free", {}),
            ("darts_shoot_balloon", {"shot_index": 18}),
            ("buy_premium_account", {"package_index": 5}),
        ):
            with self.subTest(action=action):
                built = envelope_mod.build_envelope(action, arguments, ts=1234)
                self.assertEqual(
                    json.loads(envelope_mod.payload_json(built)), built
                )

    def test_serialization_is_deterministic(self) -> None:
        first = envelope_mod.payload_json(
            envelope_mod.build_envelope("darts_shoot_balloon", {"shot_index": 18}, ts=1)
        )
        second = envelope_mod.payload_json(
            envelope_mod.build_envelope("darts_shoot_balloon", {"shot_index": 18}, ts=1)
        )
        self.assertEqual(first, second)


# --------------------------------------------------------------------------
# the weekly reset, reported and never delivered
# --------------------------------------------------------------------------


class WeeklyResetTests(unittest.TestCase):
    """``engine.reset_stuff`` is the only time-derived mutation in this surface."""

    def test_reset_stuff_writes_the_reset_instant_to_zero_not_to_the_clock(self) -> None:
        _first, _last, lines = branch_body("darts_reset")  # sanity: branches resolve
        lines = legacy_text("engine.py").split("\n")
        start = [n for n, t in enumerate(lines) if t.startswith("def reset_stuff")][0]
        body = "\n".join(_strip_comment(t) for t in lines[start : start + 25])
        self.assertIn('privateState["timeStampDartsReset"] = 0', body)
        # The literal zero, never ``now``: the branch stamps the server clock into
        # three *local* variables and writes none of them to this field.
        self.assertNotIn(
            'privateState["timeStampDartsReset"] = now', body
        )

    def test_the_existence_guard_is_reproduced_and_measured(self) -> None:
        lines = legacy_text("engine.py").split("\n")
        start = [n for n, t in enumerate(lines) if t.startswith("def reset_stuff")][0]
        body = "\n".join(_strip_comment(t) for t in lines[start : start + 25])
        self.assertIn('if "timeStampDartsReset" in privateState:', body)
        self.assertEqual(
            body.count('if "timeStampDartsReset" in privateState:'), 1
        )

    def test_the_offset_is_a_literal_and_the_weekday_rationale_stays_a_comment(self) -> None:
        lines = legacy_text("engine.py").split("\n")
        start = [n for n, t in enumerate(lines) if t.startswith("def reset_stuff")][0]
        window = lines[start : start + 25]
        code = "\n".join(_strip_comment(t) for t in window)
        # The code carries the literal twice -- once added to the recorded reset
        # instant, once added to ``now`` -- and computes no weekday from it.
        self.assertEqual(code.count("259200"), 2)
        self.assertIn("temp // 604800 != last_darts_reset // 604800", code)
        for banned in ("weekday", "timedelta", "strftime", "Thursday", "Monday"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, code)
        # The rationale survives as a comment, which is where it belongs.
        raw = "\n".join(window)
        self.assertIn("thursday", raw)
        self.assertIn("monday", raw)

    def test_the_envelope_delivers_no_weekday_helper_and_never_calls_it(self) -> None:
        """Checked over **code**, not raw source: this module's docstring
        deliberately names the weekday rationale to record that it was not
        implemented, and a docstring must not be able to fail a code guard."""
        code = module_code()
        for banned in ("weekday", "reset_stuff", "259200", "604800", "timedelta"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, code)

    def test_the_new_player_seed_writes_the_instant_to_zero_too(self) -> None:
        found = [
            (number, text)
            for number, text in code_only_lines("sessions.py")
            if "timeStampDartsReset" in text
        ]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], 121)
        self.assertIn('village["privateState"]["timeStampDartsReset"] = 0', found[0][1])


# --------------------------------------------------------------------------
# the client-sent fields, and the commented-out fast-forward line (C1)
# --------------------------------------------------------------------------


class WriterTests(unittest.TestCase):
    def test_the_reset_instant_has_five_uncommented_code_sites(self) -> None:
        """Correction **C1**: a whole-file count credits ``command.py:917``, which
        is **commented out**, and ``:915`` beside it is a *different* field
        (``timeStampMondayBonus``).  Blanking comments gives the real figure of
        **five** sites across three modules, of which exactly **three** write."""
        sites: List[Tuple[str, int, str]] = []
        for name in LEGACY_MODULES:
            for number, text in code_only_lines(name):
                if "timeStampDartsReset" in text:
                    sites.append((name, number, text.strip()))
        self.assertEqual(
            [(name, number) for name, number, _text in sites],
            [
                ("command.py", 581),
                ("engine.py", 243),
                ("engine.py", 246),
                ("engine.py", 249),
                ("sessions.py", 121),
            ],
        )
        writes = [site for site in sites if "= 0" in site[2] or "= time_now" in site[2]]
        self.assertEqual(
            [(name, number) for name, number, _text in writes],
            [("command.py", 581), ("engine.py", 249), ("sessions.py", 121)],
        )
        # The two engine.py sites at 243 and 246 are the existence guard and the
        # offset read; neither writes.
        self.assertIn('if "timeStampDartsReset" in privateState:', sites[1][2])
        self.assertIn("= privateState[\"timeStampDartsReset\"] + 259200", sites[2][2])

    def test_a_whole_file_count_would_credit_the_commented_line(self) -> None:
        """The instrument fault, pinned: ``command.py`` holds **3** occurrences on
        **2** lines, and blanking the comment leaves **1** on **1** line.  A
        whole-file occurrence count would report the reset instant as written twice
        in ``fast_forward``, which it is not."""
        raw = legacy_text("command.py").count("timeStampDartsReset")
        raw_lines = sum(
            1 for line in legacy_text("command.py").split("\n") if "timeStampDartsReset" in line
        )
        code_only = sum(
            1
            for _number, text in code_only_lines("command.py")
            if "timeStampDartsReset" in text
        )
        self.assertEqual((raw, raw_lines, code_only), (3, 2, 1))
        self.assertGreater(raw, code_only)

    def test_the_commented_fast_forward_line_is_not_a_fourth_writer(self) -> None:
        lines = legacy_text("command.py").split("\n")
        self.assertTrue(lines[916].strip().startswith("#"))
        self.assertIn("timeStampDartsReset", lines[916])
        # :915 is a *different* field, also commented, and is not a darts writer.
        self.assertTrue(lines[914].strip().startswith("#"))
        self.assertIn("timeStampMondayBonus", lines[914])

    def test_fast_forward_touches_exactly_one_darts_instant_and_it_is_uncommented(self) -> None:
        first, last, lines = fast_forward_body()
        self.assertEqual((first, last), (905, 947))
        darts = [
            (number, text)
            for number, text in lines
            if "privateState[" in text and "Darts" in text
        ]
        # Comment stripping has already blanked the reset line, so exactly **one**
        # darts instant survives in the branch's code -- the new-free instant.
        self.assertEqual(len(darts), 1)
        self.assertEqual(darts[0][0], 918)
        self.assertIn("timeStampDartsNewFree", darts[0][1])
        # And the other one is still there in the **raw** source, commented out.
        raw = legacy_text("command.py").split("\n")
        self.assertTrue(raw[916].strip().startswith("#"))
        self.assertIn("timeStampDartsReset", raw[916])


# --------------------------------------------------------------------------
# the corpus measurement, re-derived every run (D9)
# --------------------------------------------------------------------------


class CorpusMeasurementTests(unittest.TestCase):
    """Every corpus figure is **re-derived**, never asserted (design D9)."""

    def test_the_canonical_corpus_is_thirty_three_documents(self) -> None:
        documents = canonical_documents()
        self.assertEqual(len(documents), 33)
        sources = Counter(path.split("/")[0] for path, _document in documents)
        self.assertEqual(dict(sources), {"tests": 2, "villages": 31})

    def test_every_canonical_document_carries_a_map(self) -> None:
        for path, document in canonical_documents():
            with self.subTest(path=path):
                self.assertTrue(
                    any(isinstance(entry, dict) for entry in document["maps"])
                )

    def test_generated_fixtures_are_excluded_from_the_denominator(self) -> None:
        """Correction **C3**: the generated ``tests/fixtures/**`` documents are
        derived copies, and each fixture records *both* sides of a transaction, so
        counting them inflated the denominator roughly sevenfold.  The figure is
        re-derived rather than pinned, because every later capture adds a pair --
        that growth is exactly why the inflated denominator was wrong."""
        for path, _document in canonical_documents():
            self.assertNotIn("tests/fixtures/", path)
        generated = 0
        for directory, _subdirs, names in os.walk(str(REPO / "tests" / "fixtures")):
            for name in names:
                if name in ("before.json", "after.json"):
                    generated += 1
        self.assertGreater(generated, 100)
        self.assertGreater(generated, 3 * len(canonical_documents()))

    def test_every_canonical_document_carries_all_seven_darts_fields(self) -> None:
        for path, document in canonical_documents():
            private = document.get("privateState") or {}
            for field in DARTS_FIELDS:
                with self.subTest(path=path, field=field):
                    self.assertIn(field, private)

    def test_the_recorded_field_distributions_are_re_derived(self) -> None:
        documents = canonical_documents()
        expectations = {
            "dartsRandomSeed": 15,
            "timeStampDartsReset": 15,
            "timeStampDartsNewFree": 21,
            "dartsHasFree": 2,
            "dartsGotExtra": 1,
            "timeStampEndPremium": 2,
        }
        for field, expected in expectations.items():
            with self.subTest(field=field):
                values = {
                    (document.get("privateState") or {}).get(field)
                    for _path, document in documents
                }
                self.assertEqual(len(values), expected)

    def test_the_recorded_value_distributions_are_re_derived(self) -> None:
        documents = canonical_documents()

        def distribution(field: str) -> Dict[Any, int]:
            counter = Counter(
                json.dumps((document.get("privateState") or {}).get(field), sort_keys=True)
                for _path, document in documents
            )
            return {key: count for key, count in sorted(counter.items())}

        self.assertEqual(distribution("dartsHasFree"), {"false": 7, "true": 26})
        self.assertEqual(distribution("dartsGotExtra"), {"false": 33})
        self.assertEqual(
            distribution("timeStampEndPremium"), {"0": 32, "1682945878": 1}
        )
        self.assertEqual(
            distribution("dartsBalloonsShot"),
            {"[]": 30, "[0]": 1, "[18]": 1, "[18, 17]": 1},
        )

    def test_exactly_one_document_records_a_nonzero_premium_instant(self) -> None:
        live = [
            path
            for path, document in canonical_documents()
            if (document.get("privateState") or {}).get("timeStampEndPremium")
        ]
        self.assertEqual(live, ["villages/Neutral.json"])

    def test_that_instant_is_in_the_past_and_both_arms_are_reachable(self) -> None:
        """The **extend** arm needs ``time_now < instant``; the only live instant is
        in the past, so the extend arm has **no corpus coverage** and is reported
        as crafted input."""
        import time as _time

        instant = 1682945878
        self.assertLess(instant, int(_time.time()))

    def test_the_premium_account_flag_is_absent_from_every_document(self) -> None:
        for path, document in canonical_documents():
            with self.subTest(path=path):
                self.assertNotIn("premiumAccount", json.dumps(document))

    def test_three_documents_record_a_played_shot_and_one_is_out_of_schedule(self) -> None:
        """Three of the 33, and **the fresh-player corpus is not one of them** --
        so the shot arm has no coverage over the document this line drives."""
        played = [
            (path, (document.get("privateState") or {})["dartsBalloonsShot"])
            for path, document in canonical_documents()
            if (document.get("privateState") or {})["dartsBalloonsShot"]
        ]
        self.assertEqual(
            played,
            [
                ("villages/AcidCaos.json", [18, 17]),
                ("villages/Nerri.json", [0]),
                ("villages/Scarlet.json", [18]),
            ],
        )
        self.assertNotIn("tests/saves/fresh-player.json", [path for path, _s in played])

    def test_the_fresh_player_corpus_carries_every_darts_field_at_initial_value(self) -> None:
        """The reason no executed-legacy fixture is claimed (task 6.3): every field
        sits at its seeded value -- seed ``0``, no shots, no extra, **no free shot
        taken**, and a zero premium instant.  The free arm and the extend arm are
        therefore unreachable over it and any coverage of them is crafted input."""
        document = json.loads(
            (REPO / "tests" / "saves" / "fresh-player.json").read_text(encoding="utf-8")
        )
        private = document["privateState"]
        self.assertEqual(private["timeStampEndPremium"], 0)
        self.assertIs(private["dartsGotExtra"], False)
        self.assertIs(private["dartsHasFree"], False)
        self.assertEqual(private["dartsBalloonsShot"], [])
        self.assertEqual(private["dartsRandomSeed"], 0)
        self.assertEqual(private["timeStampDartsReset"], 0)
        self.assertEqual(private["timeStampDartsNewFree"], 0)

    def test_the_seed_comment_at_new_player_creation_matches_what_is_seeded(self) -> None:
        """``sessions.py:120`` seeds the reset instant to ``0`` with the comment
        *"Make sure that the game will initialize targets by calling
        darts_reset"*.  The corpus records ``0``, so the seed and the comment
        agree."""
        lines = legacy_text("sessions.py").split("\n")
        self.assertIn("calling darts_reset", lines[119])
        self.assertIn('village["privateState"]["timeStampDartsReset"] = 0', lines[120])


# --------------------------------------------------------------------------
# the anti-invention guard
# --------------------------------------------------------------------------


class AntiInventionGuardTests(unittest.TestCase):
    """The whole-module inventory is the gate; the name list is the belt."""

    def test_the_module_declares_exactly_the_pinned_functions(self) -> None:
        self.assertEqual(module_functions(), EXPECTED_MODULE_FUNCTIONS)

    def test_no_helper_named_after_an_invented_rule_exists(self) -> None:
        declared = module_functions()
        for name in FORBIDDEN_HELPERS:
            with self.subTest(helper=name):
                self.assertNotIn(name, declared)

    def test_the_module_source_carries_no_forbidden_helper_declaration(self) -> None:
        code = module_source()
        for name in FORBIDDEN_HELPERS:
            with self.subTest(helper=name):
                self.assertIsNone(
                    re.search(r"^\s*def\s+%s\s*\(" % re.escape(name), code, re.MULTILINE),
                    "darts_envelope declares %s" % name,
                )

    def test_no_code_identifier_implements_a_refused_rule(self) -> None:
        identifiers = module_identifiers()
        for word, exemptions in GUARDED_WORDS.items():
            with self.subTest(word=word):
                offenders = sorted(
                    name
                    for name in identifiers
                    if word in name.lower()
                    and name not in RECORDED_REFUSAL_NAMES
                    and name not in exemptions
                )
                self.assertEqual(offenders, [])

    def test_the_module_computes_no_duration_and_no_price(self) -> None:
        """Mechanical rather than prose: the only multiplication in the module is
        the list repeat that builds the eight-zero vector, and there is **no**
        division, floor division, power, or in-place arithmetic anywhere.  So no
        committed schedule entry could be turned into a number of seconds here,
        even by accident.

        ``Mod`` is excluded from the banned set because it is the ``%`` inside the
        refusal *messages*, which format a type name rather than compute anything.
        """
        tree = ast.parse(module_code())
        multiplication: List[str] = []
        banned: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Mult):
                    multiplication.append(ast.unparse(node))
                elif isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Pow)):
                    banned.append(type(node.op).__name__)
            if isinstance(node, ast.AugAssign) and isinstance(
                node.op, (ast.Mult, ast.Div, ast.FloorDiv)
            ):
                banned.append("AugAssign")
        self.assertEqual(banned, [])
        self.assertEqual(len(multiplication), 1)
        self.assertIn("RESOURCE_VECTOR_SLOTS", multiplication[0])
        # The repeat's operands: a literal zero and the slot count, never a value.
        self.assertTrue(multiplication[0].startswith("[0] *"))

    def test_the_module_imports_no_content_package(self) -> None:
        """Exactly three imports, and **none** of them can reach committed content:
        the schedule is read inside the legacy server, from the index alone."""
        tree = ast.parse(module_code())
        imported: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        self.assertEqual(
            sorted(imported),
            ["__future__", "placement_envelope", "time", "typing"],
        )

    def test_the_shared_helpers_are_re_exported_unchanged(self) -> None:
        """The serialization helpers come from ``placement_envelope`` so every
        earlier delivered line keeps passing untouched."""
        import placement_envelope

        for name in ("ENVELOPE_KEYS", "EnvelopeError", "is_strict_int", "payload_json"):
            with self.subTest(name=name):
                self.assertIs(getattr(envelope_mod, name), getattr(placement_envelope, name))

    def test_the_endpoint_uses_this_module(self) -> None:
        service = (REPO / "apps" / "compat-api" / "compat_service.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("import darts_envelope", service)
        self.assertIn("darts_envelope.build_envelope(action, arguments)", service)

    def test_the_route_code_derives_no_rule_of_its_own(self) -> None:
        """The two refused rules cannot appear even as a report-only computation,
        and the route reports both as absent rather than silently omitting them."""
        route = _route_code()
        for banned in ("darts_items", "len(", "in set(", "shots <", "shots >"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, route)
        self.assertIn("shot_list_length_bound=None", route)
        self.assertIn("schedule_membership_tested=False", route)

    def test_the_route_source_documents_both_refusals_in_its_prose(self) -> None:
        """The prose is required: a refusal nobody can read is not a refusal."""
        service = (REPO / "apps" / "compat-api" / "compat_service.py").read_text(
            encoding="utf-8"
        )
        route = service[service.index('"/v0/darts"') :]
        route = route[: route.index("app.config[")]
        for named in ("divergence", "dartsGotExtra", "darts_items", "PREMIUM_ACCOUNTS"):
            with self.subTest(named=named):
                self.assertIn(named, route)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()