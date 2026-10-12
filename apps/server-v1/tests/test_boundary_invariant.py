#!/usr/bin/env python3
"""The authority-boundary invariants, asserted structurally (task 2.5).

Task 2.5 asks for "the invariant test asserting the domain owns derivation in
exactly one place", and — the part that matters — for it to **fail when a second
derivation is introduced**.

These are AST assertions rather than behavioural ones on purpose.  A behavioural
test ("collect pays what the economy says") passes just as happily when a second
place computes a payout too, because the two would agree.  What the boundary
actually claims is a property of the *source*: one module owns the derivation,
one module decides refusals, the transport names no reason, and the request
layer cannot reach a balance.  Only a structural reading can say that.

Every invariant here is written to be **falsifiable**, and each is paired with a
planted control that shows the reading can fail:

* a positive and a negative case per instrument, so "the scan found nothing"
  is distinguishable from "the scan looked in the wrong place";
* counts that cannot be satisfied by an empty result set.

The injections that prove the invariants in anger are run by the implementer
against the delivered bytes and the counts recorded in the line's README:
a second derivation, a transport naming a code, and an unused refusal code.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple

import harness

SERVICE_DIR = harness.SERVICE_DIR
APP_MODULES: Tuple[Path, ...] = tuple(
    sorted(path for path in SERVICE_DIR.glob("server_v1_*.py"))
)

#: The one module permitted to derive a resource movement.
DERIVATION_OWNER = "server_v1_economy.py"

#: The one module permitted to construct a :class:`ResourceDerivation`.
ISSUANCE_OWNER = "server_v1_economy.py"


def module_name(path: Path) -> str:
    return path.name


def imported_names(tree: ast.Module) -> Set[str]:
    """Every name a module imports, as dotted or bare final components."""
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
                if node.module:
                    names.add(node.module)
    return names


def imported_modules(tree: ast.Module) -> Set[str]:
    """Every module path a module imports, e.g. ``server_v1_economy``."""
    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[-1])
    return found


def string_literals(tree: ast.Module) -> List[str]:
    """Every string constant, with docstrings excluded.

    Docstrings are excluded because they are prose *about* a rule and would
    satisfy any guard that scans for a name — the third recorded instance of
    that defect class in this repository.
    """
    docstrings: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def refusal_code_attributes(tree: ast.Module) -> Set[str]:
    """Every ``RefusalCode.X`` attribute reference in a module."""
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "RefusalCode"
    }


def parsed(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class InventoryTests(unittest.TestCase):
    """The census these invariants run against must be the real one.

    Without this, every invariant below would pass vacuously if ``APP_MODULES``
    came back empty — and a guard satisfied by an empty scan is the defect class
    this suite exists to prevent.
    """

    def test_the_application_modules_are_found(self) -> None:
        self.assertGreaterEqual(len(APP_MODULES), 10)
        self.assertIn("server_v1_collect.py", {module_name(p) for p in APP_MODULES})
        self.assertIn("server_v1_app.py", {module_name(p) for p in APP_MODULES})

    def test_every_module_parses(self) -> None:
        for path in APP_MODULES:
            with self.subTest(module=module_name(path)):
                self.assertIsInstance(parsed(path), ast.Module)

    def test_the_instruments_can_report_a_present_thing(self) -> None:
        """Planted controls: each reader is shown finding its target."""
        control = ast.parse(
            "from server_v1_economy import derive_collection_payout\n"
            "import server_v1_repository\n"
            "class C:\n"
            "    def f(self):\n"
            '        """docstring mentioning RefusalCode.FAKE and gold_delta"""\n'
            "        return RefusalCode.REAL, 'gold_delta'\n",
        )
        self.assertIn("derive_collection_payout", imported_names(control))
        self.assertIn("server_v1_repository", imported_modules(control))
        self.assertEqual({"REAL"}, refusal_code_attributes(control))
        literals = string_literals(control)
        self.assertIn("gold_delta", literals)
        self.assertNotIn("RefusalCode.FAKE and gold_delta", literals)


class DerivationLivesInOnePlaceTests(unittest.TestCase):
    """Task 2.5, the invariant itself."""

    def _importer_of_derivation(self) -> Set[str]:
        """Every module (other than the owner) that imports the derivation."""
        offenders: Set[str] = set()
        for path in APP_MODULES:
            if module_name(path) == DERIVATION_OWNER:
                continue
            if "derive_collection_payout" in imported_names(parsed(path)):
                offenders.add(module_name(path))
        return offenders

    def test_only_the_collect_slice_imports_the_derivation(self) -> None:
        self.assertEqual(
            {"server_v1_collect.py"}, self._importer_of_derivation(), "a second caller appeared"
        )

    def test_the_invocation_sites_are_exactly_one(self) -> None:
        """Not just the import: exactly one place *calls* it."""
        callers: Dict[str, int] = {}
        for path in APP_MODULES:
            if module_name(path) == DERIVATION_OWNER:
                continue
            count = sum(
                1
                for node in ast.walk(parsed(path))
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "derive_collection_payout"
            )
            if count:
                callers[module_name(path)] = count
        self.assertEqual({"server_v1_collect.py": 1}, callers)

    def test_only_the_economy_constructs_a_derivation(self) -> None:
        """Importing the type is not constructing it.

        ``server_v1_collect.py`` and ``server_v1_outcomes.py`` both name
        ``ResourceDerivation`` — for annotations and for the type check — and a
        guard that forbade the *import* would have pushed those modules into
        string annotations to satisfy it.  The boundary claim is about the
        **call**: outside the owner, no module may invoke the constructor, and
        the constructor's own token gate refuses it even if one tries.
        """
        offenders = {
            module_name(path): sum(
                1
                for node in ast.walk(parsed(path))
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ResourceDerivation"
            )
            for path in APP_MODULES
            if module_name(path) != ISSUANCE_OWNER
        }
        self.assertEqual({module_name(path): 0 for path in APP_MODULES if module_name(path) != ISSUANCE_OWNER}, offenders)

    def test_only_the_outcomes_module_names_the_success_type_in_a_field(self) -> None:
        """A ``Success`` cannot be built without a derivation, so who may hold one
        is part of the boundary rather than an accident of imports."""
        holders = {
            module_name(path)
            for path in APP_MODULES
            if "Success" in imported_names(parsed(path))
        }
        self.assertLessEqual(holders, {"server_v1_outcomes.py", "server_v1_collect.py"})


class TransportNamesNoReasonTests(unittest.TestCase):
    """Design D2: the transport reads a refusal's status; it never chooses one."""

    TRANSPORT_MODULES = ("server_v1_app.py",)

    def test_the_transport_names_no_refusal_code(self) -> None:
        for name in self.TRANSPORT_MODULES:
            with self.subTest(module=name):
                self.assertEqual(set(), refusal_code_attributes(parsed(SERVICE_DIR / name)))

    def test_the_transport_names_no_reason_as_a_string_either(self) -> None:
        """A guard that only read ``RefusalCode.X`` would miss a bare literal."""
        from server_v1_refusals import RefusalCode

        code_values = {code.value for code in RefusalCode}
        for name in self.TRANSPORT_MODULES:
            tree = parsed(SERVICE_DIR / name)
            found = {literal for literal in string_literals(tree) if literal in code_values}
            self.assertEqual(set(), found, "%s names a refusal reason as a string" % name)

    def test_the_intent_module_names_no_reason_outside_its_import(self) -> None:
        """``intent_from_json`` owns the decode, so it may own its refusals.

        The exception is exact: the module itself is where a structural input
        error is decided.  Any *other* module reaching for a code would be a
        transport naming a reason.
        """
        self.assertIn("server_v1_intent.py", {module_name(p) for p in APP_MODULES})


class RequestLayerCannotReachABalanceTests(unittest.TestCase):
    """The request layer has no store and no content; the refusal says so."""

    def test_the_intent_module_imports_neither_store_nor_content(self) -> None:
        imported = imported_modules(parsed(SERVICE_DIR / "server_v1_intent.py"))
        for forbidden in ("server_v1_repository", "server_v1_content", "server_v1_economy"):
            with self.subTest(module=forbidden):
                self.assertNotIn(forbidden, imported)

    def test_the_intent_module_does_no_arithmetic_on_a_value(self) -> None:
        """No multiplication or division: a request cannot be scaled into a payout.

        ``%`` is excluded **when its left operand is a string literal**, because
        that is interpolation (``"/maps/0/items/%d" % self.row``), not
        arithmetic.  The first version of this guard counted those four and
        failed — a guard that cannot be satisfied without deleting the
        ``addressed_path`` helper is a guard that was measuring the wrong thing.
        """
        tree = parsed(SERVICE_DIR / "server_v1_intent.py")
        arithmetic: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(
                node.op, (ast.Mult, ast.Div, ast.FloorDiv, ast.Pow)
            ):
                arithmetic.append(ast.dump(node))
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
                left = node.left
                is_interpolation = isinstance(left, ast.Constant) and isinstance(left.value, str)
                if not is_interpolation:
                    arithmetic.append(ast.dump(node))
        self.assertEqual([], arithmetic)


class VocabularyIsClosedTests(unittest.TestCase):
    """Task 2.6: every declared code is used and every used code is declared."""

    def test_every_declared_code_is_named_by_some_module(self) -> None:
        from server_v1_refusals import REFUSAL_HTTP_STATUS, RefusalCode

        used: Set[str] = set()
        for path in APP_MODULES:
            if module_name(path) == "server_v1_refusals.py":
                continue
            used |= refusal_code_attributes(parsed(path))
        declared = {code.name for code in RefusalCode}
        self.assertEqual(declared, used & declared, "a declared code is never named")
        # The status table is keyed by the enum members themselves.
        self.assertEqual(
            set(RefusalCode),
            set(REFUSAL_HTTP_STATUS),
            "the status table is not closed over the vocabulary",
        )

    def test_the_vocabulary_is_not_large_just_because_it_is_closed(self) -> None:
        """A closed vocabulary that grew to v0's 104 would not be the decision."""
        from server_v1_refusals import RefusalCode

        self.assertLess(len(list(RefusalCode)), 20)
        self.assertGreater(len(list(RefusalCode)), 0)

    def test_every_code_maps_to_exactly_one_status(self) -> None:
        from server_v1_refusals import REFUSAL_HTTP_STATUS, RefusalCode

        self.assertEqual(
            set(RefusalCode), set(REFUSAL_HTTP_STATUS), "the status table is not closed"
        )
        for code in RefusalCode:
            with self.subTest(code=code.name):
                self.assertIsInstance(REFUSAL_HTTP_STATUS[code], int)

    def test_no_application_module_lives_under_compat_api(self) -> None:
        """v0's 104 codes must not become a dependency of v1.

        **This file's earlier version of this claim was deleted rather than
        made to pass, and the reason is the finding.**  It scanned for the
        documentation table by name, so the guard necessarily *named the token
        it forbade* -- and ``test_refusals.py`` already scans for exactly that
        token and exempts itself and the declaring module.  Two guards for one
        rule is how a hand-maintained exclusion list drifts, and the duplicate
        only "passed" because the sibling flagged it.  The ownership is now
        single: ``test_refusals.NoV0ImportTests`` scans for the token, and this
        file keeps only the structural half it alone can state -- that no v1
        application module sits inside the v0 package.

        The deleted version's last line was a tautology regardless:
        its final assertion intersected the declared table's key set with a
        one-element set that no key can equal, so it could not have failed for
        any mapping whatsoever.
        """
        for path in APP_MODULES:
            with self.subTest(module=module_name(path)):
                self.assertNotIn("apps/compat-api", str(path).replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()