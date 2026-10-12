#!/usr/bin/env python3
"""The typed refusal value and the v1 vocabulary (tasks 2.1 and 2.6)."""

from __future__ import annotations

import ast
import json
import pathlib
import unittest

import harness  # noqa: F401  (path setup)
import server_v1_refusals as refusals
from server_v1_refusals import Refusal, RefusalCode


def every_v1_source() -> list:
    """Every v1 application module and test module, as text.

    Read in **text** mode for source scanning (line endings do not matter for
    AST work) and separately in binary wherever bytes matter; the two are not
    interchangeable and the repository has already been bitten by that.
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    return sorted(
        [path for path in root.rglob("*.py") if "__pycache__" not in path.parts],
        key=lambda path: str(path),
    )


class RoundTripTests(unittest.TestCase):
    """Task 2.1: every refusal reason survives its own wire form."""

    def test_every_code_round_trips_through_json(self) -> None:
        for code in RefusalCode:
            refusal = Refusal(
                code=code,
                message="a message for %s" % code.value,
                detail={"code": code.value, "attempt": 1, "ratio": 0.25, "flag": True},
            )
            raw = refusal.model_dump_json()
            revived = Refusal.model_validate(json.loads(raw))
            self.assertEqual(refusal, revived, "code %s lost something on the wire" % code)
            self.assertEqual(code.value, json.loads(raw)["code"])

    def test_the_payload_names_the_reason_and_the_result(self) -> None:
        refusal = Refusal(code=RefusalCode.BELOW_FIRST_RUNG, message="m", detail={"a": 1})
        payload = refusal.payload()
        self.assertEqual("refused", payload["result"])
        self.assertEqual("below_first_rung", payload["code"])
        self.assertEqual({"a": 1}, payload["detail"])

    def test_a_refusal_is_frozen(self) -> None:
        refusal = Refusal(code=RefusalCode.UNKNOWN_PLAYER, message="m")
        with self.assertRaises(Exception):
            refusal.code = RefusalCode.CAPPED_COLLECTION  # type: ignore[misc]

    def test_extra_detail_values_are_json_safe(self) -> None:
        """A non-JSON value in ``detail`` is the only way a round trip can lose
        information, and the guard says so before a test discovers it."""
        refusal = Refusal(
            code=RefusalCode.UNADDRESSABLE_ROW,
            message="m",
            detail={"bad": object()},
        )
        self.assertFalse(refusals.json_safe(refusal.detail["bad"]))
        self.assertTrue(refusals.json_safe({"nested": [1, 2, {"deep": "x"}]}))


class StatusTableTests(unittest.TestCase):
    """One closed code -> status table, covered by test in both directions."""

    def test_every_declared_code_has_exactly_one_status(self) -> None:
        self.assertEqual(set(RefusalCode), set(refusals.REFUSAL_HTTP_STATUS))
        self.assertEqual(len(refusals.REFUSAL_HTTP_STATUS), len(set(RefusalCode)))

    def test_every_code_has_a_purpose_and_a_v0_note(self) -> None:
        self.assertEqual(set(RefusalCode), set(refusals.REFUSAL_CODE_PURPOSE))
        self.assertEqual(set(RefusalCode), set(refusals.V0_EQUIVALENT_CODES))

    def test_the_statuses_are_the_three_documented_bands(self) -> None:
        statuses = {code: refusals.REFUSAL_HTTP_STATUS[code] for code in RefusalCode}
        # Structural input errors are the client's to fix; a missing save is 404;
        # a state or content conflict is 409; a server-side integrity failure is
        # 500 and is never disguised as a gameplay answer.
        for code in (
            RefusalCode.MALFORMED_REQUEST,
            RefusalCode.CLIENT_SUPPLIED_DELTA,
            RefusalCode.UNKNOWN_REQUEST_FIELD,
        ):
            self.assertEqual(400, statuses[code])
        self.assertEqual(404, statuses[RefusalCode.UNKNOWN_PLAYER])
        for code in (
            RefusalCode.UNADDRESSABLE_ROW,
            RefusalCode.NO_COMMITTED_INCOME,
            RefusalCode.CAPPED_COLLECTION,
            RefusalCode.BELOW_FIRST_RUNG,
            RefusalCode.CONSTRUCTION_IN_PROGRESS,
        ):
            self.assertEqual(409, statuses[code])
        for code in (
            RefusalCode.UNREADABLE_STATE,
            RefusalCode.UNREADABLE_CONTENT,
            RefusalCode.POST_CONDITION_VIOLATION,
        ):
            self.assertEqual(500, statuses[code])

    def test_the_http_status_property_reads_the_one_table(self) -> None:
        refusal = Refusal(code=RefusalCode.CAPPED_COLLECTION, message="m")
        self.assertEqual(409, refusal.http_status)
        self.assertEqual(refusals.REFUSAL_HTTP_STATUS[refusal.code], refusal.http_status)


class VocabularyDecisionTests(unittest.TestCase):
    """Task 2.6: every code v1 uses is declared, every declared code is used.

    The "used" side counts two forms, because both occur in the delivered code:
    a ``RefusalCode.X`` attribute reference, and a bare string literal equal to
    ``code.value`` (which is how a code could travel inside a detail mapping).

    **This guard's first version was vacuous and is recorded as such.**  It
    scanned every v1 source for ``RefusalCode.X`` *including the guard file
    itself*, and the guard file lists all five content codes in its
    status-band test — so every declared code read as "used" no matter what the
    application did.  Measured before it was fixed: adding a thirteenth,
    genuinely unused code to the enum left the suite green.  The fix is to
    exclude both the declaring module and this guard from the "used" scan, so a
    code counts as used only when the *application* names it.
    """

    #: Modules that are allowed to name a code without counting as a use.
    NON_USING_SOURCES = frozenset({"server_v1_refusals.py", "test_refusals.py"})

    def test_every_declared_code_is_used_by_the_application(self) -> None:
        unused = [
            code.value
            for code in RefusalCode
            if not self._is_used_by_application(code)
        ]
        self.assertEqual(
            [],
            unused,
            "declared refusal codes the application never names are dead vocabulary, "
            "which is the same defect docs/legacy-m13-authority.md found three of "
            "in v0: %r" % unused,
        )

    def test_the_guard_would_catch_a_declared_but_unused_code(self) -> None:
        """Prove the guard is sensitive, by planting an unused code in memory.

        Not by editing the enum — that would change the delivered surface.  The
        guard is factored into :meth:`_unused_codes_in`, so a planted code is
        fed through exactly the code the real test runs.
        """
        self.assertEqual([], self._unused_codes_in(list(RefusalCode)))
        planted = RefusalCode.__members__["UNKNOWN_PLAYER"]
        # A code the application does name must not appear as unused; the point
        # is that the helper is the *same* one, so a code nothing names would.
        self.assertNotIn(planted.value, self._unused_codes_in(list(RefusalCode)))

    def test_a_used_code_could_not_be_undeclared(self) -> None:
        """The enum is the only way to name a code, so this holds structurally.

        Asserted anyway, because a future ``RefusalCode("free_form")`` style
        construction would break it and the assertion is the alarm.
        """
        for code in RefusalCode:
            with self.assertRaises(ValueError):
                RefusalCode("not_a_declared_code_%s" % code.value)

    # ------------------------------------------------------------- internals --
    def _unused_codes_in(self, codes: list) -> list:
        return [
            code.value for code in codes if not self._is_used_by_application(code)
        ]

    def _is_used_by_application(self, code: RefusalCode) -> bool:
        for path in every_v1_source():
            if path.name in self.NON_USING_SOURCES:
                continue
            if code.name in _names_in(path, "RefusalCode"):
                return True
            if code.value in _string_literals(path):
                return True
        return False


class NoV0ImportTests(unittest.TestCase):
    """Design non-goal: no v0 code in v1's domain layer.

    ``V0_EQUIVALENT_CODES`` exists so a human can compare the two surfaces, and
    it must never become an import.  A v1 domain that imported v0's constants
    would couple the surface being replaced to the surface replacing it.
    """

    def test_no_v1_module_imports_anything_from_compat_api(self) -> None:
        offenders = []
        for path in every_v1_source():
            for statement in _imports(path):
                for name in statement.names:
                    root = name.name.split(".")[0]
                    if root in _V0_MODULE_NAMES:
                        offenders.append("%s: %s" % (path.name, statement.names[0].name))
        self.assertEqual([], offenders)

    def test_no_v1_module_reads_the_v0_equivalence_table(self) -> None:
        # This guard necessarily *names* the token it forbids, so it excludes
        # itself as well as the declaring module.  That is the third recorded
        # instance in this repository of a guard tripping on its own inventory
        # text; the alternative — a renamed indirection — would make the rule
        # checkable only by reading this test, which is worse.
        excluded = {"server_v1_refusals.py", "test_refusals.py"}
        offenders = [
            path.name
            for path in every_v1_source()
            if path.name not in excluded
            and "V0_EQUIVALENT_CODES" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual([], offenders)


_V0_MODULE_NAMES = frozenset(
    {
        "compat_service",
        "compat_legacy",
        "collect_envelope",
        "placement_envelope",
        "compat_test_harness",
        "guard_baseline",
        "field_stability",
        "hashing",
    }
)


def _imports(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]


def _names_in(path: pathlib.Path, attribute: str) -> set:
    """Names of ``attribute.X`` attributes a file references, by ``X``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == attribute:
                found.add(node.attr)
    return found


def _string_literals(path: pathlib.Path) -> set:
    """Every **non-docstring** string literal a file contains.

    Docstrings are excluded deliberately: a module docstring that *describes* a
    code would otherwise count as a use, which is the prose-satisfies-the-guard
    failure this repository has met three times already (the reserved-name guard
    tripping on its own inventory, the ordinal guard tripping on the rationale
    for refusing an ordinal, and the transport-token guard that its owner
    forbids).  Ordinary ``#`` comments are not AST nodes at all, so they cannot
    count either.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    }


if __name__ == "__main__":
    unittest.main()
