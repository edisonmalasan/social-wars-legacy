#!/usr/bin/env python3
"""Offline unit tests for ``combat_envelope`` (OpenSpec tasks 2.1-2.4, 4.1-4.3).

No server, no socket, no network: this module imports the derivation and asserts
it against **the committed bytes themselves** -- ``command.py``, ``engine.py``,
the normalized units package, and every committed save document -- so every
recorded constant is a **measurement** rather than a restatement of this
module's own prose (task 4.1).  A constant that drifts from the source fails here
instead of being published.

Covered:

* the closed three-action vocabulary, the command each action dispatches, and
  the one value each action may name;
* the **re-derived field inventory**: the branch's own membership tests read as
  bytes, the row-removal loop located by searching for its **call**, and the
  three-way fate partition asserted -- with no key list transcribed anywhere,
  and with a guard that fails the run if one is;
* **selective** row eligibility: slot 0 equal to the item id **and** slot 7
  truthy, the first eligible row by the save's own recorded map-key order (which
  is not a sort), and a refusal when nothing matches;
* the **two** ledger gates and no third, the two reachable arms (increment and
  key creation), and an absent flag treated as a refusal rather than a zero;
* the three refused client-key families, one of them built from the **derived**
  inventory rather than transcribed;
* the neutral resource vector and the refusal of every non-zero slot;
* the derived batch envelope, including the server-written client blob whose two
  subtraction operands are chosen so the branch's own arithmetic yields exactly
  one;
* the two kill contracts, delivered differently: a row removal that structurally
  cannot reach the ledger, and an item-keyed command with no write statement at
  all;
* the recorded divergences and the two **measured corrections** against the
  committed prose, carried side by side rather than silently replaced;
* the whole module's function inventory against a pinned list, so an invented
  ``damage_for`` / ``honour_for`` / ``mission_complete`` / ``destruction_count``
  helper fails the run wherever it is added (task 4.3).
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import textwrap
import unittest
from typing import Any, Dict, List, Optional

import compat_test_harness as harness  # noqa: F401  (path setup)

import combat_envelope as C
import placement_envelope as P

REPO = harness.REPO_ROOT
LEGACY_SOURCE = REPO / "command.py"
ENGINE_SOURCE = REPO / "engine.py"
UNITS_PACKAGE = REPO / "packages" / "game-content" / "normalized" / "units.json"
SAVE_ROOTS = ("villages", "tests/saves")

#: The whole function inventory of ``combat_envelope``.  This is the
#: anti-invention gate: any helper added to the module shows up here and fails
#: the run, which is what makes task 4.3's absence checks structural rather than
#: a matter of reading the module.
EXPECTED_MODULE_FUNCTIONS = [
    "_branch_span",
    "_row_removal_region",
    "_strip_string_literals",
    "actions",
    "address_row",
    "branches",
    "build_envelope",
    "clear_derived_identity",
    "combat_payload",
    "committed_resurrectable",
    "conflicts",
    "derive_field_inventory",
    "expected_ledger_increment",
    "gates",
    "is_action",
    "is_item_id",
    "is_map_key",
    "neutral_vector",
    "project_combat",
    "project_ledger",
    "refusals",
    "refused_client_keys",
    "select_eligible_rows",
    "set_derived_identity",
    "team_asymmetry",
    "validate_vector",
    "validation_order",
]

#: Helper names whose mere existence would be an invented combat rule.  Matched
#: as SUBSTRINGS of the declared name as well as by whole name, because an
#: earlier by-name guard in this repository matched only the exact name and so
#: missed a suffixed helper wearing the same disguise.
FORBIDDEN_HELPER_FRAGMENTS = (
    "damage",
    "defence",
    "defense",
    "honour",
    "honor",
    "reward",
    "mission",
    "hit_chance",
    "hitchance",
    "casualt",
    "destroy_count",
    "destruction_count",
    "lost_count",
    "rows_to_destroy",
    "combat_time",
    "time_to_kill",
    "travel_time",
)

#: Identifiers that legitimately carry one of the fragments above because they
#: name the recorded **absence** or the recorded refusal instead of a rule.
FORBIDDEN_HELPER_EXEMPT = ("NO_COST_OR_REWARD", "NO_SYRINGE_COST", "END_ATTACK_COMMAND")


def module_source() -> str:
    return pathlib.Path(C.__file__).read_text(encoding="utf-8")


def module_functions() -> List[str]:
    tree = ast.parse(module_source())
    return sorted(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def module_code_identifiers() -> List[str]:
    """Every identifier the module's CODE declares, binds, or reads.

    Docstrings, comments, and string literals are excluded by parsing rather than
    by scanning, so a recorded refusal sentence that happens to use the word
    "damage" can never be mistaken for a computation.
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


def suite_string_literals() -> List[str]:
    """Every string constant in THIS module, taken whole rather than tokenised.

    The no-transcription guard compares these against the derived inventory as
    whole literals, so tokenising here would turn one literal naming two keys
    into two tokens and hide exactly the case the guard exists to catch.
    """
    literals: List[str] = []
    own = pathlib.Path(__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(own)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
    return literals


def suite_key_collections(keys: "set[str]") -> List[List[str]]:
    """Every list/tuple/set/dict of THIS module whose members are all keys.

    This is the shape a transcribed inventory would take.  A single key named on
    its own -- which the two perturbation tests must do -- is not one of these,
    which is the distinction that keeps the guard strict without making it
    unsatisfiable.
    """
    found: List[List[str]] = []
    own = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(own):
        members: List[Any] = []
        if isinstance(node, (ast.List, ast.Set)):
            members = node.elts
        elif isinstance(node, ast.Tuple):
            members = node.elts
        elif isinstance(node, ast.Dict):
            members = list(node.keys)
        if len(members) < 2:
            continue
        if all(
            isinstance(member, ast.Constant)
            and isinstance(member.value, str)
            and member.value in keys
            for member in members
        ):
            found.append([member.value for member in members])  # type: ignore[union-attr]
    return found


def legacy_lines(name: str) -> List[str]:
    return (REPO / name).read_text(encoding="utf-8").split("\n")


def derived_inventory() -> Dict[str, Any]:
    """The inventory, derived once per call from the committed source bytes."""
    return C.derive_field_inventory()


def committed_documents() -> List[Dict[str, Any]]:
    """Every committed save document that carries a ``maps[0].items`` object."""
    documents: List[Dict[str, Any]] = []
    for root in SAVE_ROOTS:
        directory = REPO / root
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if not isinstance(document, dict):
                continue
            maps = document.get("maps")
            if not isinstance(maps, list) or not maps:
                continue
            first = maps[0]
            if not isinstance(first, dict) or not isinstance(first.get("items"), dict):
                continue
            documents.append(
                {"path": "%s/%s" % (root, path.name), "document": document}
            )
    return documents


def committed_unit_ids() -> Dict[str, Optional[int]]:
    """``legacy_id -> committed resurrectable``, with ``None`` for an absent flag."""
    package = json.loads(UNITS_PACKAGE.read_text(encoding="utf-8"))
    rows = package["units"] if isinstance(package, dict) else package
    table: Dict[str, Optional[int]] = {}
    for row in rows:
        properties = row.get("properties")
        flag = properties.get("resurrectable") if isinstance(properties, dict) else None
        table[str(row["legacy_id"])] = None if flag is None else int(flag)
    return table


def unit_rows(items: Dict[str, Any], table: Dict[str, Optional[int]]) -> int:
    return sum(
        1
        for row in items.values()
        if isinstance(row, list)
        and len(row) == C.MAP_ROW_SLOTS
        and str(row[C.SLOT_ITEM_ID]) in table
    )


def crafted_row(
    item_id: int, team: int = 1, cell: int = 0, attr: Optional[Dict[str, Any]] = None
) -> List[Any]:
    """One 8-slot row in the committed shape, built in memory."""
    return [item_id, cell, cell, 1700000000, 0, [], {} if attr is None else attr, team]


class VocabularyTests(unittest.TestCase):
    """The closed three-action vocabulary and what each action dispatches."""

    def test_the_vocabulary_is_closed_and_holds_exactly_three_actions(self) -> None:
        self.assertEqual(C.ACTION_COUNT, 3)
        self.assertEqual(
            C.ACTIONS,
            (C.ACTION_RESOLVE, C.ACTION_KILL, C.ACTION_KILL_IID),
        )
        self.assertEqual(len(set(C.ACTIONS)), C.ACTION_COUNT)

    def test_each_action_derives_its_committed_command(self) -> None:
        self.assertEqual(C.ACTION_COMMAND[C.ACTION_RESOLVE], C.END_ATTACK_COMMAND)
        self.assertEqual(C.ACTION_COMMAND[C.ACTION_KILL], C.KILL_COMMAND)
        self.assertEqual(C.ACTION_COMMAND[C.ACTION_KILL_IID], C.KILL_IID_COMMAND)
        # Measured against the preserved source: each name is a dispatcher branch.
        source = LEGACY_SOURCE.read_text(encoding="utf-8")
        for action in C.ACTIONS:
            with self.subTest(action=action):
                self.assertIn(
                    'elif cmd == "%s":' % C.ACTION_COMMAND[action], source
                )

    def test_each_action_names_exactly_one_addressing_value(self) -> None:
        self.assertEqual(
            sorted(set(C.ACTION_ADDRESSING_KEY.values())),
            ["item_id", "map_key"],
        )
        for action in C.ACTIONS:
            with self.subTest(action=action):
                self.assertIn(action, C.ACTION_ADDRESSING_KEY)
                self.assertTrue(C.ACTION_ADDRESSING[action])
        self.assertEqual(C.ACTION_ADDRESSING_KEY[C.ACTION_KILL], "map_key")
        for action in (C.ACTION_RESOLVE, C.ACTION_KILL_IID):
            with self.subTest(action=action):
                self.assertEqual(C.ACTION_ADDRESSING_KEY[action], "item_id")

    def test_the_two_identities_are_never_exchanged(self) -> None:
        # The one place a mix-up would be silent: both the combat resolution and
        # the item-keyed kill address an item id, while only the row removal
        # addresses a map key.
        self.assertNotIn(C.ACTION_ADDRESSING_KEY[C.ACTION_KILL], C.ACTION_ADDRESSING)
        self.assertEqual(
            {C.ACTION_ADDRESSING_KEY[a] for a in (C.ACTION_RESOLVE, C.ACTION_KILL_IID)},
            {"item_id"},
        )

    def test_an_unknown_or_mistyped_action_is_refused(self) -> None:
        for value in ("", "Resolve", "resolve ", "end_attack", "sell", None, 1, True,
                      [], {}, b"resolve"):
            with self.subTest(action=value):
                self.assertFalse(C.is_action(value))

    def test_every_delivered_action_is_accepted(self) -> None:
        for action in C.ACTIONS:
            with self.subTest(action=action):
                self.assertTrue(C.is_action(action))

    def test_the_branch_records_are_fresh_dicts(self) -> None:
        branches = C.branches()
        self.assertEqual(len(branches), C.ACTION_COUNT)
        branches[0]["command"] = "tampered"
        self.assertNotEqual(C.branches()[0]["command"], "tampered")
        for record in C.branches():
            with self.subTest(action=record["action"]):
                self.assertIn(record["addressing_key"], ("item_id", "map_key"))
                self.assertTrue(record["source"].startswith("command.py:"))

    def test_only_the_resolution_reaches_the_ledger(self) -> None:
        reaches = {
            record["action"]: record["reaches_ledger"] for record in C.branches()
        }
        self.assertEqual(
            reaches, {C.ACTION_RESOLVE: True, C.ACTION_KILL: False,
                      C.ACTION_KILL_IID: False}
        )

    def test_the_row_removal_and_the_item_keyed_kill_destroy_differently(self) -> None:
        destroys = {
            record["action"]: record["destroys_rows"] for record in C.branches()
        }
        self.assertEqual(
            destroys,
            {C.ACTION_RESOLVE: True, C.ACTION_KILL: True, C.ACTION_KILL_IID: False},
        )


class FieldInventoryTests(unittest.TestCase):
    """Task 4.1: the inventory is re-derived from the branch, never transcribed."""

    def test_the_branch_is_found_and_bounded(self) -> None:
        inventory = derived_inventory()
        self.assertTrue(inventory["ok"])
        self.assertEqual(inventory["source"], "command.py")
        self.assertEqual(inventory["branch"], C.END_ATTACK_COMMAND)
        start, end = inventory["branch_span"]
        self.assertGreater(start, 0)
        self.assertGreater(end, start)
        # The span is the branch's own lines, so it must be readable back.
        lines = legacy_lines("command.py")
        self.assertEqual(lines[start - 1].strip(), 'elif cmd == "%s":' % C.END_ATTACK_COMMAND)

    def test_the_row_removal_region_is_located_by_searching_for_the_call(self) -> None:
        region = derived_inventory()["row_removal_region"]
        self.assertIsNotNone(region)
        start, end = region  # type: ignore[misc]
        lines = legacy_lines("command.py")
        inside = lines[start - 1 : end]
        self.assertTrue(
            any(C._ROW_REMOVAL_CALL in line for line in inside),  # type: ignore[attr-defined]
            "the region does not contain the row-removal call",
        )
        self.assertTrue(any(line.strip().startswith("for ") for line in inside))

    def test_every_read_key_is_classified_by_exactly_one_fate(self) -> None:
        inventory = derived_inventory()
        records = inventory["keys"]
        self.assertEqual(len(records), inventory["key_count"])
        fates = [record["fate"] for record in records]
        self.assertEqual(sorted(set(fates)), sorted(C.FATES))
        for fate in C.FATES:
            with self.subTest(fate=fate):
                self.assertEqual(fates.count(fate), len(inventory[fate]))
        self.assertTrue(inventory["partition"])
        self.assertEqual(
            sorted(inventory["discarded"] + inventory["print_only"]
                   + inventory["mutation_path"]),
            sorted(record["key"] for record in records),
        )

    def test_a_discarded_key_has_no_post_test_occurrence_at_all(self) -> None:
        inventory = derived_inventory()
        for record in inventory["keys"]:
            if record["fate"] != "discarded":
                continue
            with self.subTest(key=record["key"]):
                self.assertEqual(record["post_test_sites"], [])
                self.assertEqual(record["post_test_site_count"], 0)
                self.assertFalse(record["inside_row_removal_region"])

    def test_a_print_only_key_has_occurrences_but_none_inside_the_loop(self) -> None:
        inventory = derived_inventory()
        region = inventory["row_removal_region"]
        for record in inventory["keys"]:
            if record["fate"] != "print_only":
                continue
            with self.subTest(key=record["key"]):
                self.assertGreater(record["post_test_site_count"], 0)
                self.assertFalse(record["inside_row_removal_region"])
                for site in record["post_test_sites"]:
                    line = int(site.split(":")[1])
                    self.assertFalse(region[0] <= line < region[1])  # type: ignore[index]

    def test_the_mutation_path_is_inside_the_row_removal_region(self) -> None:
        inventory = derived_inventory()
        region = inventory["row_removal_region"]
        for record in inventory["keys"]:
            if record["fate"] != "mutation_path":
                continue
            with self.subTest(key=record["key"]):
                self.assertTrue(record["inside_row_removal_region"])
                for site in record["post_test_sites"]:
                    line = int(site.split(":")[1])
                    self.assertTrue(region[0] <= line < region[1])  # type: ignore[index]

    def test_exactly_one_key_reaches_the_mutation_path(self) -> None:
        # The one structural claim that makes the inventory worth deriving: the
        # whole branch writes through a single client key.
        self.assertEqual(len(derived_inventory()["mutation_path"]), 1)

    def test_every_declaration_line_is_inside_the_branch_span(self) -> None:
        inventory = derived_inventory()
        start, end = inventory["branch_span"]
        lines = legacy_lines("command.py")
        for record in inventory["keys"]:
            with self.subTest(key=record["key"]):
                declared = int(record["tested_at"].split(":")[1])
                self.assertTrue(start <= declared < end)
                self.assertIn(
                    'if "%s" in response:' % record["key"], lines[declared - 1]
                )

    def test_occurrences_and_distinct_lines_are_recorded_separately(self) -> None:
        # A key repeated on one line would make the two counts differ; recording
        # both is what keeps "occurrences per line" from being read as "lines".
        for record in derived_inventory()["keys"]:
            with self.subTest(key=record["key"]):
                self.assertGreaterEqual(
                    record["post_test_site_count"], record["post_test_distinct_lines"]
                )
                self.assertEqual(
                    len(record["post_test_sites"]),
                    record["post_test_distinct_lines"],
                )
                self.assertLessEqual(record["post_test_site_count"],
                                    len(set(record["post_test_sites"])))

    def test_the_discard_count_exceeds_the_committed_record_and_says_so(self) -> None:
        inventory = derived_inventory()
        correction = inventory["correction"]
        self.assertEqual(inventory["key_count"], correction["measured_read_key_count"])
        self.assertEqual(
            len(inventory["discarded"]), correction["measured_discarded_count"]
        )
        # The committed record under-counts, and the correction says so rather
        # than replacing the figure.
        self.assertLess(correction["recorded_read_key_count"], inventory["key_count"])
        self.assertLess(
            correction["recorded_discarded_count"], len(inventory["discarded"])
        )
        self.assertLess(
            correction["recorded_discarded_count_in_the_own_table"],
            len(inventory["discarded"]),
        )
        self.assertTrue(correction["record_left_intact"])

    def test_the_counting_rules_are_recorded_and_non_empty(self) -> None:
        correction = derived_inventory()["correction"]
        self.assertGreaterEqual(len(correction["counting_rules_measured"]), 3)
        for rule in correction["counting_rules_measured"]:
            with self.subTest(rule=rule[:40]):
                self.assertTrue(rule.strip())

    def test_the_derivation_is_re_run_on_every_call(self) -> None:
        first = derived_inventory()
        second = derived_inventory()
        self.assertEqual(first["keys"], second["keys"])
        self.assertIsNot(first, second)

    def test_a_legacy_edit_moves_the_inventory(self) -> None:
        """The drift guard, proven rather than trusted: a renamed key is measured.

        The source is supplied as **text**, so this needs no edit to a preserved
        file; if the derivation were transcribed rather than read, the renamed
        key would simply be absent and this test would fail.
        """
        source = LEGACY_SOURCE.read_text(encoding="utf-8")
        branch = source.split('elif cmd == "%s":' % C.END_ATTACK_COMMAND, 1)[1]
        renamed = branch.replace(
            'if "victim_units" in response:', 'if "victim_rows" in response:', 1
        )
        self.assertNotEqual(renamed, branch)
        mutated = C.derive_field_inventory(source.split(
            'elif cmd == "%s":' % C.END_ATTACK_COMMAND, 1)[0]
            + 'elif cmd == "%s":' % C.END_ATTACK_COMMAND + renamed)
        self.assertTrue(mutated["ok"])
        self.assertEqual(mutated["key_count"], derived_inventory()["key_count"])
        self.assertIn("victim_rows", mutated["key_names"])
        self.assertNotIn("victim_units", mutated["key_names"])

    def test_a_dropped_membership_test_lowers_the_count(self) -> None:
        source = LEGACY_SOURCE.read_text(encoding="utf-8")
        head, branch = source.split(
            'elif cmd == "%s":' % C.END_ATTACK_COMMAND, 1
        )
        dropped = branch.replace('        if "win" in response:\n', "", 1)
        self.assertNotEqual(dropped, branch)
        mutated = C.derive_field_inventory(
            head + 'elif cmd == "%s":' % C.END_ATTACK_COMMAND + dropped
        )
        self.assertTrue(mutated["ok"])
        self.assertEqual(
            mutated["key_count"], derived_inventory()["key_count"] - 1
        )
        self.assertNotIn("win", mutated["key_names"])

    def test_a_source_without_the_branch_is_refused_not_defaulted(self) -> None:
        for text in ("", "def f():\n    pass\n", 'elif cmd == "other":\n    pass\n'):
            with self.subTest(text=text[:20]):
                inventory = C.derive_field_inventory(text)
                self.assertFalse(inventory["ok"])
                self.assertTrue(inventory["reason"])
                self.assertEqual(inventory["keys"], [])
                self.assertEqual(inventory["key_count"], 0)
                self.assertFalse(inventory["partition"])
                self.assertEqual(inventory["discarded"], [])
                self.assertEqual(inventory["print_only"], [])
                self.assertEqual(inventory["mutation_path"], [])

    def test_a_branch_reading_no_keys_is_refused(self) -> None:
        inventory = C.derive_field_inventory(
            'elif cmd == "%s":\n    print(1)\n\nelif cmd == "next":\n    pass\n'
            % C.END_ATTACK_COMMAND
        )
        self.assertFalse(inventory["ok"])
        self.assertIn("no client keys", inventory["error"])

    def test_a_string_literal_cannot_contribute_a_use(self) -> None:
        """Quote-stripped scanning: a comment or a literal is not a use.

        Without the strip, a key named only inside a comment or a string would be
        filed as print-only rather than discarded, and the discarded set would
        under-report.
        """
        source = (
            'elif cmd == "%s":\n'
            '    if "alpha" in response:\n'
            '        alpha = response["alpha"]\n'
            '    # alpha is deliberately ignored downstream\n'
            '    print("alpha")\n'
            '    if "beta" in response:\n'
            '        beta = response["beta"]\n'
            '    print(beta)\n'
            '\n'
            'elif cmd == "next_branch":\n'
            '    pass\n' % C.END_ATTACK_COMMAND
        )
        inventory = C.derive_field_inventory(source)
        self.assertTrue(inventory["ok"])
        self.assertEqual(sorted(inventory["key_names"]), ["alpha", "beta"])
        self.assertEqual(inventory["discarded"], ["alpha"])
        self.assertEqual(inventory["print_only"], ["beta"])
        self.assertEqual(inventory["mutation_path"], [])

    def test_an_apostrophe_inside_a_string_does_not_desynchronise_the_lexer(self) -> None:
        source = (
            'elif cmd == "%s":\n'
            "    note = \"it's not a use\"\n"
            '    if "alpha" in response:\n'
            '        alpha = response["alpha"]\n'
            '    if "beta" in response:\n'
            '        beta = response["beta"]\n'
            '    print(beta)\n'
            '\n'
            'elif cmd == "next_branch":\n'
            '    pass\n' % C.END_ATTACK_COMMAND
        )
        inventory = C.derive_field_inventory(source)
        self.assertTrue(inventory["ok"])
        self.assertEqual(inventory["discarded"], ["alpha"])
        self.assertEqual(inventory["print_only"], ["beta"])

    def test_this_suite_transcribes_no_derived_key(self) -> None:
        """No key is written into this suite, so the drift guard cannot rot.

        Prose is excluded by reading only string **constants**, and the check is
        over whole word tokens, so naming a key in a docstring or inside a
        sentence is neither required nor detected -- a transcription would be a
        literal in a collection or a comparison.
        """
        keys = set(derived_inventory()["key_names"])
        # (1) No string constant here names TWO derived keys, which is what an
        # enumeration written as prose or as a comma list would look like.
        for literal in suite_string_literals():
            named = [
                key for key in keys
                if re.search(r"\b%s\b" % re.escape(key), literal)
            ]
            self.assertLessEqual(
                len(named), 1,
                "test_combat_envelope names %r in one literal; the inventory "
                "must stay derived" % (named,),
            )
        # (2) No collection literal here consists of derived keys, which is what
        # a transcribed inventory would look like.
        self.assertEqual(suite_key_collections(keys), [])
        # Individual derived keys ARE named, deliberately: proving the
        # derivation is not transcribed requires perturbing one, and this suite
        # does that twice (``test_a_legacy_edit_moves_the_inventory`` and
        # ``test_a_dropped_membership_test_lowers_the_count``). What must not
        # exist is a LIST of them, which is why (1) and (2) are the whole guard.

    def test_the_derivation_is_exported_and_the_public_names_all_exist(self) -> None:
        for name in C.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(C, name))


class RefusedClientKeyTests(unittest.TestCase):
    """Task 2.1 / D2: three refused families, one of them derived."""

    def test_a_destruction_count_key_is_refused(self) -> None:
        inventory = derived_inventory()["key_names"]
        for key in C.DESTRUCTION_COUNT_KEYS:
            with self.subTest(key=key):
                self.assertEqual(
                    C.refused_client_keys({"item_id": 1, key: 3}, inventory), [key]
                )

    def test_both_subtraction_operands_are_refused(self) -> None:
        inventory = derived_inventory()["key_names"]
        self.assertEqual(sorted(C.SENT_SURVIVED_KEYS), ["sent", "survived"])
        self.assertEqual(
            C.refused_client_keys({"item_id": 1, "sent": 3, "survived": 1}, inventory),
            ["sent", "survived"],
        )

    def test_the_legacy_payload_keys_are_refused_from_the_derived_inventory(self) -> None:
        # The whole point of D4: this family is built by re-reading the branch,
        # so a legacy edit that adds or renames a read key moves the refusal set
        # with it rather than leaving a transcribed gap.
        inventory = derived_inventory()["key_names"]
        payload = {"user_id": "u", "action": "resolve", "item_id": 1020}
        payload.update({key: True for key in inventory})
        self.assertEqual(
            C.refused_client_keys(payload, inventory), sorted(inventory)
        )

    def test_a_pure_intent_request_refuses_nothing(self) -> None:
        inventory = derived_inventory()["key_names"]
        self.assertEqual(
            C.refused_client_keys(
                {"user_id": "u", "action": "resolve", "item_id": 1020}, inventory
            ),
            [],
        )

    def test_the_row_removal_intent_refuses_nothing_either(self) -> None:
        inventory = derived_inventory()["key_names"]
        self.assertEqual(
            C.refused_client_keys(
                {"user_id": "u", "action": "kill", "map_key": 1639}, inventory
            ),
            [],
        )

    def test_the_result_is_sorted_and_deduplicated(self) -> None:
        inventory = derived_inventory()["key_names"]
        refused = C.refused_client_keys(
            {"lost": 2, "count": 2, "send": 0, "sent": 1, "lost": 3}, inventory
        )
        self.assertEqual(refused, sorted(set(refused)))
        self.assertIn("lost", refused)
        self.assertIn("sent", refused)
        self.assertNotIn("send", refused)

    def test_an_underivable_inventory_widens_nothing(self) -> None:
        # The documented degradation: with no derivable inventory only the two
        # transcribed families are refused, and that is reported rather than
        # silently padded with invented names.
        self.assertEqual(C.refused_client_keys({"lost": 3}, []), ["lost"])
        self.assertEqual(C.refused_client_keys({"survived": 0}, []), ["survived"])
        self.assertEqual(C.refused_client_keys({"victim_units": 1}, []), [])

    def test_a_non_mapping_payload_refuses_nothing_rather_than_crashing(self) -> None:
        for payload in (None, [], 15, "x"):
            with self.subTest(payload=payload):
                self.assertEqual(C.refused_client_keys(payload, []), [])

    def test_the_count_families_are_disjoint_from_the_derived_keys(self) -> None:
        # A key cannot be in both families: that would make a refusal ambiguous
        # and would mean the derived set had drifted onto a transcribed name.
        inventory = set(derived_inventory()["key_names"])
        self.assertEqual(inventory & set(C.DESTRUCTION_COUNT_KEYS), set())
        self.assertEqual(inventory & set(C.SENT_SURVIVED_KEYS), set())

    def test_the_refusal_rule_names_the_legacy_arithmetic_and_the_bad_pattern(self) -> None:
        rule = C.CLIENT_DICTATED_REFUSAL
        self.assertIn("max(0, unit[2] - unit[3])", rule)
        self.assertIn("command.py:868", rule)
        self.assertIn("A", rule)
        self.assertIn("Bad", rule)
        self.assertIn("DIVERGENCE", rule)

    def test_the_exhaustion_note_says_exhaustion_is_not_a_check(self) -> None:
        note = C.REFUSED_COUNT_NOTE
        self.assertIn("EXHAUSTION OF", note)
        self.assertIn("NOT A CHECK", note)
        self.assertIn("engine.py:218-227", note)
        self.assertIn("no clamp is applied", note)

    def test_the_printed_count_is_recorded_as_a_request_not_an_outcome(self) -> None:
        note = C.PRINTED_COUNT_IS_A_REQUEST
        self.assertIn("command.py:871", note)
        self.assertIn(":872", note)
        self.assertIn("923", note)
        self.assertIn("ASKED FOR", note)


class EligibilityTests(unittest.TestCase):
    """D1: eligibility is exactly what ``map_lose_item`` tests, in its own order."""

    def test_a_matching_row_with_a_truthy_team_is_eligible(self) -> None:
        selection = C.select_eligible_rows({"7": crafted_row(1020)}, 1020)
        self.assertTrue(selection["ok"])
        self.assertEqual(selection["eligible_keys"], ["7"])
        self.assertEqual(selection["addressed_key"], "7")

    def test_the_first_match_by_RECORDED_order_wins_and_it_is_not_a_sort(self) -> None:
        # The discriminator the fixture exists for: the recorded order puts
        # 2425 before 897, so a sorted implementation would answer 897.
        items = {
            "2425": crafted_row(1020, cell=1),
            "1022": crafted_row(1020, cell=2),
            "898": crafted_row(1020, cell=3),
            "897": crafted_row(1020, cell=4),
        }
        selection = C.select_eligible_rows(items, 1020)
        self.assertEqual(selection["eligible_keys"], ["2425", "1022", "898", "897"])
        self.assertEqual(selection["addressed_key"], "2425")
        self.assertNotEqual(selection["addressed_key"], "897")
        self.assertEqual(selection["eligible_count"], 4)

    def test_a_row_whose_team_is_falsy_is_never_eligible(self) -> None:
        # engine.py:221 tests ``map_items[index][7]``, so any falsy team excludes
        # the row -- while the ledger gate requires the team to be exactly one.
        for team in (0, None, "", False, []):
            with self.subTest(team=team):
                selection = C.select_eligible_rows({"7": crafted_row(1020, team=team)},
                                                   1020)
                self.assertFalse(selection["ok"])
                self.assertEqual(selection["reason"], C.REASON_NO_ELIGIBLE_ROW)
        for team in (1, 2, 3, "x", [0]):
            with self.subTest(team=team):
                self.assertTrue(
                    C.select_eligible_rows({"7": crafted_row(1020, team=team)}, 1020)["ok"]
                )

    def test_a_row_of_another_item_id_is_never_eligible(self) -> None:
        selection = C.select_eligible_rows({"7": crafted_row(999)}, 1020)
        self.assertFalse(selection["ok"])
        self.assertEqual(selection["eligible_count"], 0)

    def test_a_malformed_row_can_neither_be_destroyed_nor_be_a_candidate(self) -> None:
        for row in ([], [1020], [1020] * 7, [1020] * 9, "1020x8", {"item": 1020},
                    None, 1020):
            with self.subTest(row=str(row)[:20]):
                selection = C.select_eligible_rows({"7": row}, 1020)
                self.assertFalse(selection["ok"])
                self.assertEqual(selection["eligible_count"], 0)

    def test_no_eligible_row_is_a_named_refusal_not_an_empty_success(self) -> None:
        selection = C.select_eligible_rows({}, 923)
        self.assertFalse(selection["ok"])
        self.assertEqual(selection["reason"], C.REASON_NO_ELIGIBLE_ROW)
        self.assertEqual(selection["eligible_keys"], [])
        self.assertFalse(selection["addressed"])
        self.assertIsNone(selection["addressed_key"])
        self.assertIsNone(selection["addressed_row"])
        self.assertIn("engine.py:221", selection["error"])

    def test_a_non_integer_identity_is_refused_before_the_rows_are_read(self) -> None:
        for value in ("1020", None, 1020.0, True, [1020], {}):
            with self.subTest(value=value):
                selection = C.select_eligible_rows({"7": crafted_row(1020)}, value)
                self.assertFalse(selection["ok"])
                self.assertEqual(selection["reason"], C.REASON_INVALID_ITEM_ID)

    def test_a_non_mapping_placement_set_is_refused(self) -> None:
        for value in (None, [], "items", 15):
            with self.subTest(value=value):
                selection = C.select_eligible_rows(value, 1020)
                self.assertFalse(selection["ok"])
                self.assertEqual(selection["reason"], C.REASON_INVALID_PAYLOAD)

    def test_the_addressed_row_is_a_copy_so_the_caller_cannot_mutate_the_save(self) -> None:
        items = {"7": crafted_row(1020)}
        selection = C.select_eligible_rows(items, 1020)
        selection["addressed_row"][0] = -1
        self.assertEqual(items["7"][0], 1020)

    def test_the_row_removal_helper_matches_exactly_these_two_conditions(self) -> None:
        # Measured against the preserved helper, so the two conditions above are
        # not an assertion about intent but a reading of the source.
        engine = ENGINE_SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "if map_items[index][0] == item and map_items[index][7]:", engine
        )
        self.assertIn("def map_lose_item(", engine)
        self.assertIn("while qty > 0:", engine)
        self.assertIn("if not deleted:", engine)


class AddressRowTests(unittest.TestCase):
    """``kill`` addresses a map key, and only a map key."""

    def test_an_addressed_key_resolves_to_its_row(self) -> None:
        resolved = C.address_row({"1639": crafted_row(1076)}, 1639)
        self.assertTrue(resolved["ok"])
        self.assertEqual(resolved["row"][0], 1076)
        self.assertTrue(resolved["addressed"])

    def test_an_absent_key_is_a_named_refusal_with_the_legacy_divergence_named(self) -> None:
        resolved = C.address_row({"1639": crafted_row(1076)}, 999999)
        self.assertFalse(resolved["ok"])
        self.assertEqual(resolved["reason"], C.REASON_UNADDRESSABLE_ROW)
        self.assertIn("command.py:173-176", resolved["error"])
        self.assertIsNone(resolved["row"])

    def test_a_string_key_is_refused_rather_than_coerced(self) -> None:
        for value in ("1639", None, 1639.0, True, []):
            with self.subTest(value=value):
                resolved = C.address_row({"1639": crafted_row(1076)}, value)
                self.assertFalse(resolved["ok"])
                self.assertEqual(resolved["reason"], C.REASON_INVALID_MAP_KEY)

    def test_a_non_mapping_placement_set_is_refused(self) -> None:
        resolved = C.address_row([], 1639)
        self.assertFalse(resolved["ok"])
        self.assertEqual(resolved["reason"], C.REASON_INVALID_PAYLOAD)

    def test_the_resolved_row_is_a_copy(self) -> None:
        items = {"1639": crafted_row(1076)}
        resolved = C.address_row(items, 1639)
        resolved["row"][0] = -1
        self.assertEqual(items["1639"][0], 1076)

    def test_the_legacy_branch_prints_and_returns_for_an_absent_row(self) -> None:
        # The divergence the refusal replaces: legacy answers success.
        lines = legacy_lines("command.py")
        block = "\n".join(lines[168:181])
        self.assertIn("Error: item not found.", block)
        self.assertIn("return", block)


class LedgerGateTests(unittest.TestCase):
    """Exactly two gates, two reachable arms, and an absent flag is a refusal."""

    def test_both_gates_are_recorded_in_the_helpers_own_order(self) -> None:
        self.assertEqual(C.GATE_COUNT, 2)
        self.assertEqual(
            [gate["gate"] for gate in C.gates()],
            ["player_team_one", "resurrectable_positive"],
        )
        for gate in C.gates():
            with self.subTest(gate=gate["gate"]):
                self.assertTrue(gate["committed"])
                self.assertIn("engine.py", gate["source"])

    def test_no_third_gate_is_invented_and_the_absence_is_named(self) -> None:
        rule = C.NO_THIRD_GATE
        self.assertIn("EXACTLY TWO", rule)
        for absent in ("no level check", "no cost check", "no capacity check",
                       "no cooldown", "no per-type check"):
            with self.subTest(absent=absent):
                self.assertIn(absent, rule)

    def test_both_gates_holding_creates_the_key_at_one(self) -> None:
        derived = C.expected_ledger_increment({}, 1020, 1, 5)
        self.assertTrue(derived["written"])
        self.assertFalse(derived["present_before"])
        self.assertEqual(derived["count_before"], 0)
        self.assertEqual(derived["count_after"], 1)
        self.assertEqual(derived["entries"], {"1020": 1})
        self.assertEqual(derived["item_id"], "1020")

    def test_both_gates_holding_increments_an_existing_key_without_adding_one(self) -> None:
        derived = C.expected_ledger_increment({"1034": 4, "1020": 7}, 1034, 1, 5)
        self.assertTrue(derived["written"])
        self.assertTrue(derived["present_before"])
        self.assertEqual(derived["count_before"], 4)
        self.assertEqual(derived["count_after"], 5)
        self.assertEqual(derived["entries"], {"1034": 5, "1020": 7})
        self.assertEqual(len(derived["entries"]), 2)

    def test_a_row_off_team_one_is_destroyed_yet_never_recorded(self) -> None:
        # engine.py:151 returns False, and map_lose_item has already popped the
        # row: the team asymmetry, exercised at the gate level only.
        for team in (0, 2, 3, None, "x"):
            with self.subTest(team=team):
                derived = C.expected_ledger_increment({}, 1020, team, 5)
                self.assertFalse(derived["written"])
                self.assertEqual(derived["entries"], {})
                self.assertFalse(derived["gates"]["player_team_one"]["holds"])

    def test_an_absent_flag_is_a_refusal_and_never_a_zero(self) -> None:
        derived = C.expected_ledger_increment({}, 1020, 1, None)
        self.assertFalse(derived["written"])
        self.assertEqual(derived["entries"], {})
        gate = derived["gates"]["resurrectable_positive"]
        self.assertFalse(gate["present"])
        self.assertIsNone(gate["recorded_flag"])

    def test_a_zero_flag_is_refused_too(self) -> None:
        for flag in (0, "0", " 0 ", "00"):
            with self.subTest(flag=flag):
                derived = C.expected_ledger_increment({}, 1020, 1, flag)
                self.assertFalse(derived["written"])
                self.assertEqual(derived["entries"], {})

    def test_a_boolean_flag_is_refused_rather_than_read_as_one_or_zero(self) -> None:
        # ``bool`` is an ``int`` in Python, so an implicit conversion would read
        # ``True`` as a positive count.  A committed flag is a string or an
        # integer, never a boolean, so a boolean is a type error.
        for flag in (True, False):
            with self.subTest(flag=flag):
                with self.assertRaises(C.EnvelopeError) as caught:
                    C.expected_ledger_increment({}, 1020, 1, flag)
                self.assertEqual(caught.exception.code, C.REASON_INVALID_ITEM_ID)

    def test_the_committed_string_flag_is_converted_explicitly(self) -> None:
        # The committed normalized package stores the flag as a STRING, and a
        # non-empty String is truthy, so an implicit truth test would read "0" as
        # positive.
        self.assertTrue(C.expected_ledger_increment({}, 1020, 1, "3")["written"])
        self.assertFalse(C.expected_ledger_increment({}, 1020, 1, "0")["written"])

    def test_the_raw_configuration_string_is_accepted_as_the_legacy_reads_it(self) -> None:
        # The RAW string is ``committed_resurrectable``'s input, which decodes it
        # the way ``engine.py:154-162`` does; ``expected_ledger_increment`` takes
        # the ALREADY-READ flag, so passing a blob to it is a type error rather
        # than a decode.  The two stages are asserted separately below.
        raw = '{"harvester": "1", "resurrectable": "2"}'
        self.assertEqual(C.committed_resurrectable(raw), 2)
        self.assertTrue(
            C.expected_ledger_increment({}, 1020, 1, C.committed_resurrectable(raw))[
                "written"
            ]
        )
        for bad in ('{"resurrectable": "two"}', 2.5, [2], {"a": 1}, True):
            with self.subTest(flag=str(bad)[:20]):
                with self.assertRaises(C.EnvelopeError) as caught:
                    C.expected_ledger_increment({}, 1020, 1, bad)
                self.assertEqual(caught.exception.code, C.REASON_INVALID_ITEM_ID)

    def test_an_unreadable_ledger_is_refused_rather_than_read_as_empty(self) -> None:
        for ledger in (None, [], "hero", 15, {"a": "1"}, {1: 1}, {"a": True}):
            with self.subTest(ledger=str(ledger)[:20]):
                with self.assertRaises(C.EnvelopeError) as caught:
                    C.expected_ledger_increment(ledger, 1020, 1, 5)
                self.assertEqual(caught.exception.code, C.REASON_INVALID_LEDGER)

    def test_an_empty_ledger_is_readable_because_it_is_a_committed_shape(self) -> None:
        self.assertTrue(C.expected_ledger_increment({}, 1020, 1, None)["entries"] == {})

    def test_the_ledger_projection_is_the_shared_one_not_a_second_copy(self) -> None:
        import behavior_envelope

        self.assertEqual(
            C.project_ledger({"1020": 2}), behavior_envelope.project_ledger({"1020": 2})
        )
        self.assertEqual(
            C.committed_resurrectable({"resurrectable": "4"}),
            behavior_envelope.committed_resurrectable({"resurrectable": "4"}),
        )
        self.assertEqual(C.LEDGER_KEY, behavior_envelope.LEDGER_KEY)
        self.assertEqual(C.PLAYER_TEAM, behavior_envelope.PLAYER_TEAM)

    def test_the_ledger_saves_own_two_locations_are_recorded(self) -> None:
        self.assertEqual(C.PRIVATE_STATE_KEY, "privateState")
        self.assertEqual(C.LEDGER_KEY, "deadHeroes")

    def test_the_two_gates_are_the_only_ones_the_helper_checks(self) -> None:
        # Measured out of the preserved helper's body.
        engine = ENGINE_SOURCE.read_text(encoding="utf-8")
        start = engine.index("def push_dead_unit(")
        end = engine.index("def resurrect_hero(")
        body = engine[start:end]
        self.assertIn("if item[7] != 1:", body)
        self.assertIn('if "resurrectable" not in properties:', body)
        self.assertIn('if int(properties["resurrectable"]) > 0:', body)
        for absent in ("level", "cost", "capacity", "cooldown"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, body)


class VectorTests(unittest.TestCase):
    """A combat action moves no resource, so only the neutral vector derives."""

    def test_the_neutral_vector_is_eight_zeros(self) -> None:
        self.assertEqual(C.neutral_vector(), [0] * C.RESOURCE_VECTOR_SLOTS)
        self.assertEqual(C.RESOURCE_VECTOR_SLOTS, 8)

    def test_the_neutral_vector_is_a_fresh_list_every_call(self) -> None:
        first = C.neutral_vector()
        first[2] = 999999
        self.assertEqual(C.neutral_vector(), [0] * 8)

    def test_a_neutral_vector_validates(self) -> None:
        self.assertEqual(C.validate_vector([0] * 8), [0] * 8)

    def test_every_single_slot_may_not_be_moved(self) -> None:
        for index in range(C.RESOURCE_VECTOR_SLOTS):
            for magnitude in (1, -1, 101, 10 ** 9):
                with self.subTest(slot=index, value=magnitude):
                    vector = [0] * C.RESOURCE_VECTOR_SLOTS
                    vector[index] = magnitude
                    with self.assertRaises(C.EnvelopeError) as caught:
                        C.validate_vector(vector)
                    self.assertEqual(caught.exception.code, C.REASON_INVALID_VECTOR)

    def test_a_wrong_width_or_a_non_integer_slot_is_refused(self) -> None:
        for bad in ([0] * 7, [0] * 9, "00000000", None, [0] * 7 + ["x"],
                    [0] * 7 + [True]):
            with self.subTest(bad=str(bad)[:20]):
                with self.assertRaises(C.EnvelopeError) as caught:
                    C.validate_vector(bad)
                self.assertEqual(caught.exception.code, C.REASON_INVALID_VECTOR)

    def test_a_client_vector_is_never_accepted_by_the_envelope_builder(self) -> None:
        with self.assertRaises(TypeError):
            C.build_envelope(C.ACTION_KILL, 1639, vector=[1, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(
            C.build_envelope(C.ACTION_KILL, 1639)["commands"][0][3], [0] * 8
        )

    def test_the_proof_covers_every_stored_resource_and_not_a_subset(self) -> None:
        self.assertEqual(
            sorted(C.RESOURCE_NAMES),
            ["cash", "gold", "mana", "oil", "steel", "wood", "xp"],
        )
        self.assertEqual(len(C.RESOURCE_NAMES), 7)


class EnvelopeTests(unittest.TestCase):
    """The derived batch, and the server-written client blob."""

    def test_the_envelope_carries_exactly_the_six_legacy_keys(self) -> None:
        envelope = C.build_envelope(C.ACTION_KILL, 1639)
        self.assertEqual(sorted(envelope), sorted(C.ENVELOPE_KEYS))
        self.assertEqual(len(envelope), 6)

    def test_the_batch_carries_exactly_one_command_with_a_neutral_vector(self) -> None:
        for action, addressing in (
            (C.ACTION_RESOLVE, 1020),
            (C.ACTION_KILL, 1639),
            (C.ACTION_KILL_IID, 1076),
        ):
            with self.subTest(action=action):
                C.set_derived_identity(addressing)
                try:
                    envelope = C.build_envelope(action, addressing)
                finally:
                    C.clear_derived_identity()
                self.assertEqual(len(envelope["commands"]), 1)
                entry = envelope["commands"][0]
                self.assertEqual(entry[0], 0)
                self.assertEqual(entry[1], C.ACTION_COMMAND[action])
                self.assertEqual(entry[3], [0] * C.RESOURCE_VECTOR_SLOTS)
                self.assertEqual(len(entry), 4)

    def test_each_action_derives_its_own_argument_list(self) -> None:
        C.set_derived_identity(1020)
        try:
            resolve = C.build_envelope(C.ACTION_RESOLVE, 1020)["commands"][0]
        finally:
            C.clear_derived_identity()
        kill = C.build_envelope(C.ACTION_KILL, 1639)["commands"][0]
        kill_iid = C.build_envelope(C.ACTION_KILL_IID, 1076)["commands"][0]
        self.assertEqual(kill[2], [1639, C.DERIVED_REASON])
        self.assertEqual(kill_iid[2], [1076, C.DERIVED_REASON])
        self.assertEqual(len(resolve[2]), 2)
        # ``args[0]`` is the blob, ``args[1]`` is bound to `unknown` and never read.
        self.assertEqual(resolve[2][1], C.DERIVED_UNKNOWN)

    def test_the_derived_blob_carries_one_tuple_and_no_other_read_key(self) -> None:
        C.set_derived_identity(1020)
        try:
            payload = json.loads(C.combat_payload(C.ACTION_RESOLVE))
        finally:
            C.clear_derived_identity()
        self.assertEqual(sorted(payload), sorted([C.COMBAT_PAYLOAD_KEY, "victim"]))
        self.assertEqual(payload[C.COMBAT_PAYLOAD_KEY], [[1020, 0, 1, 0]])

    def test_the_derived_operands_make_the_branchs_own_arithmetic_yield_one(self) -> None:
        # max(0, unit[2] - unit[3]) == 1, with BOTH numbers written by this
        # server rather than received from a client.
        self.assertEqual(C.DERIVED_SENT, 1)
        self.assertEqual(C.DERIVED_SURVIVED, 0)
        C.set_derived_identity(1020)
        try:
            unit = json.loads(C.combat_payload(C.ACTION_RESOLVE))[
                C.COMBAT_PAYLOAD_KEY
            ][0]
        finally:
            C.clear_derived_identity()
        self.assertEqual(max(0, unit[2] - unit[3]), 1)

    def test_the_derived_blob_is_deterministic(self) -> None:
        # Every call inside the recorded identity: a third call AFTER the reset
        # would compare against the cleared default, which is a different test
        # (see ``test_the_identity_is_reset_so_no_stale_value_reaches_the_wire``).
        C.set_derived_identity(1020)
        try:
            first = C.combat_payload(C.ACTION_RESOLVE)
            second = C.combat_payload(C.ACTION_RESOLVE)
            third = C.combat_payload(C.ACTION_RESOLVE)
        finally:
            C.clear_derived_identity()
        self.assertEqual(first, second)
        self.assertEqual(first, third)
        # Compact separators, which is what makes the wire bytes reproducible
        # for a fixture.  Key ORDER is asserted against the parsed document
        # rather than the text: the victim name is a two-word string, so
        # "no space anywhere" would be false.
        self.assertNotIn(", ", first)
        self.assertNotIn(": ", first)
        self.assertEqual(
            list(json.loads(first)),
            [C.COMBAT_PAYLOAD_KEY, "victim"],
        )

    def test_the_victim_record_exists_only_so_the_branchs_final_print_can_read_it(self) -> None:
        C.set_derived_identity(1020)
        try:
            payload = json.loads(C.combat_payload(C.ACTION_RESOLVE))
        finally:
            C.clear_derived_identity()
        self.assertEqual(payload["victim"], {"name": C.DERIVED_VICTIM_NAME})
        self.assertEqual(C.DERIVED_VICTIM_NAME, "derived")
        lines = legacy_lines("command.py")
        self.assertIn('if "name" in victim:', "\n".join(lines[870:880]))

    def test_the_identity_is_reset_so_no_stale_value_reaches_the_wire(self) -> None:
        C.set_derived_identity(1020)
        self.assertEqual(C._DERIVED_IDENTITY, 1020)  # type: ignore[attr-defined]
        C.clear_derived_identity()
        self.assertEqual(C._DERIVED_IDENTITY, 0)  # type: ignore[attr-defined]
        payload = json.loads(C.combat_payload(C.ACTION_RESOLVE))
        self.assertEqual(payload[C.COMBAT_PAYLOAD_KEY][0][0], 0)

    def test_a_non_integer_identity_cannot_be_recorded(self) -> None:
        for value in ("1020", None, 1020.0, True, []):
            with self.subTest(value=value):
                with self.assertRaises(C.EnvelopeError) as caught:
                    C.set_derived_identity(value)
                self.assertEqual(caught.exception.code, C.REASON_INVALID_ITEM_ID)

    def test_the_row_removal_dispatches_no_client_blob(self) -> None:
        with self.assertRaises(C.EnvelopeError) as caught:
            C.combat_payload(C.ACTION_KILL)
        self.assertEqual(caught.exception.code, C.REASON_INVALID_ACTION)

    def test_an_unknown_action_is_refused_by_both_the_blob_and_the_envelope(self) -> None:
        with self.assertRaises(C.EnvelopeError) as caught:
            C.combat_payload("nope")
        self.assertEqual(caught.exception.code, C.REASON_INVALID_ACTION)
        with self.assertRaises(C.EnvelopeError) as caught:
            C.build_envelope("nope", 1)
        self.assertEqual(caught.exception.code, C.REASON_INVALID_ACTION)

    def test_a_mistyped_addressing_is_refused_by_the_envelope_builder(self) -> None:
        with self.assertRaises(C.EnvelopeError) as caught:
            C.build_envelope(C.ACTION_KILL, "1639")
        self.assertEqual(caught.exception.code, C.REASON_INVALID_MAP_KEY)
        with self.assertRaises(C.EnvelopeError) as caught:
            C.build_envelope(C.ACTION_KILL_IID, 1076.0)
        self.assertEqual(caught.exception.code, C.REASON_INVALID_ITEM_ID)

    def test_a_bad_timestamp_is_refused(self) -> None:
        for bad in (-1, "now", 1.5, True):
            with self.subTest(bad=bad):
                with self.assertRaises(C.EnvelopeError) as caught:
                    C.build_envelope(C.ACTION_KILL, 1639, ts=bad)
                self.assertEqual(caught.exception.code, C.REASON_INVALID_TIMESTAMP)

    def test_the_timestamp_defaults_to_the_current_time(self) -> None:
        import time

        before = int(time.time())
        envelope = C.build_envelope(C.ACTION_KILL, 1639)
        self.assertGreaterEqual(envelope["ts"], before)

    def test_no_key_anywhere_in_the_envelope_can_carry_a_client_number(self) -> None:
        C.set_derived_identity(1020)
        try:
            envelope = C.build_envelope(C.ACTION_RESOLVE, 1020)
        finally:
            C.clear_derived_identity()
        vocabulary = ("lost", "count", "sent", "survived", "damage", "attack",
                      "defense", "reward", "honour", "resources_changed", "user_id")
        for name in list(envelope):
            with self.subTest(key=name):
                lowered = str(name).lower()
                for word in vocabulary:
                    self.assertNotIn(word, lowered)

    def test_the_data_field_round_trips_through_the_shared_serializer(self) -> None:
        envelope = C.build_envelope(C.ACTION_KILL, 1639)
        # The shared serializer, imported rather than re-wrapped: this line adds
        # no envelope primitive of its own, so the round trip is the earlier
        # delivered line's byte form.
        field = P.data_field(envelope)
        self.assertEqual(field[64], ";")
        self.assertEqual(P.parse_data_field(field)["commands"], envelope["commands"])


class ProjectionTests(unittest.TestCase):
    """Every check resolves above the write, and the destruction is always one."""

    def items(self) -> Dict[str, Any]:
        return {
            "2425": crafted_row(1020, 1, attr={"xp": 109}),
            "897": crafted_row(1020, 3),
            "5": crafted_row(1076, 1),
        }

    def item_of(self, item_id: int) -> Optional[Dict[str, Any]]:
        return {"properties": '{"resurrectable": "3"}'}

    #: ``None`` is a legitimate ledger value to project -- it is what a save
    #: without the key reads as -- so "omit the argument" needs its own marker
    #: rather than sharing ``None`` with it.
    LEDGER_OMITTED = object()

    def project(self, action: Any = C.ACTION_RESOLVE, addressing: Any = 1020,
                items: Any = None,
                ledger: Any = LEDGER_OMITTED) -> Dict[str, Any]:
        return C.project_combat(
            self.items() if items is None else items,
            {} if ledger is self.LEDGER_OMITTED else ledger,
            action,
            addressing,
            self.item_of,
        )

    def test_a_resolvable_resolution_projects_one_destruction_and_one_increment(self) -> None:
        projection = self.project()
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["command"], C.END_ATTACK_COMMAND)
        self.assertEqual(projection["addressing_key"], "item_id")
        self.assertEqual(projection["destruction"], 1)
        self.assertTrue(projection["ledger_written"])
        self.assertEqual(projection["ledger_after"]["entries"], {"1020": 1})
        self.assertEqual(projection["eligible"]["addressed_key"], "2425")

    def test_the_destruction_is_one_however_many_rows_match(self) -> None:
        items = {
            "%d" % index: crafted_row(1020) for index in range(20)
        }
        projection = self.project(addressing=1020, items=items)
        self.assertEqual(projection["eligible"]["eligible_count"], 20)
        self.assertEqual(projection["eligible"]["addressed_key"], "0")
        self.assertEqual(projection["destruction"], 1)
        self.assertEqual(projection["ledger_after"]["count_after"], 1)

    def test_a_declined_gate_destroys_the_row_and_writes_no_ledger_entry(self) -> None:
        items = {"5": crafted_row(1076, team=3)}
        projection = self.project(addressing=1076, items=items)
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["destruction"], 1)
        self.assertFalse(projection["ledger_written"])
        self.assertEqual(projection["ledger_after"]["entries"], {})
        self.assertFalse(
            projection["ledger_after"]["gates"]["player_team_one"]["holds"]
        )

    def test_the_row_removal_projects_one_destruction_and_never_a_ledger_write(self) -> None:
        projection = self.project(action=C.ACTION_KILL, addressing=5)
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["command"], C.KILL_COMMAND)
        self.assertEqual(projection["addressing_key"], "map_key")
        self.assertEqual(projection["destruction"], 1)
        self.assertFalse(projection["ledger_written"])
        self.assertEqual(projection["ledger_after"]["entries"], {})
        self.assertIsNone(projection["ledger_after"]["item_id"])

    def test_the_row_removal_is_addressed_by_key_not_by_item_id(self) -> None:
        # Key 5 holds item 1076, so addressing the ITEM instead must not resolve.
        projection = self.project(action=C.ACTION_KILL, addressing=1076)
        self.assertFalse(projection["ok"])
        self.assertEqual(projection["reason"], C.REASON_UNADDRESSABLE_ROW)

    def test_the_item_keyed_kill_projects_nothing_at_all(self) -> None:
        projection = self.project(action=C.ACTION_KILL_IID, addressing=1020)
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["command"], C.KILL_IID_COMMAND)
        self.assertEqual(projection["destruction"], 0)
        self.assertFalse(projection["ledger_written"])
        self.assertIsNone(projection["addressed_row"])
        self.assertIsNone(projection["eligible"])
        self.assertEqual(projection["ledger_after"]["entries"], {})

    def test_an_unknown_action_is_refused_before_anything_is_read(self) -> None:
        for value in ("nope", None, 15, True, b"resolve"):
            with self.subTest(value=value):
                projection = self.project(action=value)
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["reason"], C.REASON_INVALID_ACTION)
                self.assertIsNone(projection["ledger_before"])
                self.assertIsNone(projection["eligible"])

    def test_a_mistyped_addressing_is_refused_before_the_ledger_is_read(self) -> None:
        projection = self.project(addressing="1020")
        self.assertFalse(projection["ok"])
        self.assertEqual(projection["reason"], C.REASON_INVALID_ITEM_ID)
        self.assertIsNone(projection["ledger_before"])
        projection = self.project(action=C.ACTION_KILL, addressing=None)
        self.assertEqual(projection["reason"], C.REASON_INVALID_MAP_KEY)

    def test_an_unreadable_ledger_is_refused_before_a_row_is_addressed(self) -> None:
        for ledger in (None, [], "hero", {"a": "1"}):
            with self.subTest(ledger=str(ledger)[:12]):
                projection = self.project(ledger=ledger)
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["reason"], C.REASON_INVALID_LEDGER)
                self.assertIsNone(projection["addressed_row"])

    def test_an_unreadable_ledger_also_refuses_a_proven_no_op(self) -> None:
        # The ledger is read for every action, so an unreadable save cannot be
        # answered "success" on the strength of the no-op branch doing nothing.
        projection = self.project(action=C.ACTION_KILL_IID, addressing=1020, ledger=None)
        self.assertFalse(projection["ok"])
        self.assertEqual(projection["reason"], C.REASON_INVALID_LEDGER)

    def test_no_eligible_row_is_refused_rather_than_destroying_nothing(self) -> None:
        projection = self.project(addressing=923)
        self.assertFalse(projection["ok"])
        self.assertEqual(projection["reason"], C.REASON_NO_ELIGIBLE_ROW)
        self.assertEqual(projection["destruction"], 0)
        self.assertFalse(projection["ledger_written"])
        self.assertIsNone(projection["ledger_after"])

    def test_an_unaddressable_key_is_refused_rather_than_deleting_nothing(self) -> None:
        projection = self.project(action=C.ACTION_KILL, addressing=999999)
        self.assertFalse(projection["ok"])
        self.assertEqual(projection["reason"], C.REASON_UNADDRESSABLE_ROW)
        self.assertEqual(projection["destruction"], 0)

    def test_every_refusal_leaves_the_placements_and_ledger_untouched(self) -> None:
        # The structural half of D3: a refusal returns before a write, so the
        # projection reports no destruction and no ledger entry.
        for action, addressing, ledger in (
            (C.ACTION_RESOLVE, 923, {}),
            (C.ACTION_KILL, 999999, {}),
            (C.ACTION_KILL_IID, "1020", {}),
            (C.ACTION_RESOLVE, 1020, None),
            ("nope", 1020, {}),
        ):
            with self.subTest(action=action, addressing=str(addressing)):
                projection = self.project(
                    action=action, addressing=addressing, ledger=ledger
                )
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["destruction"], 0)
                self.assertFalse(projection["ledger_written"])

    def test_the_projection_copies_the_inventory_rather_than_deriving_twice(self) -> None:
        inventory = derived_inventory()
        projection = C.project_combat(
            self.items(), {}, C.ACTION_KILL, 5, self.item_of, inventory
        )
        self.assertIs(projection["inventory"], inventory)
        # An underivable inventory is accepted and reported, not defaulted.
        empty = {"ok": False, "key_names": [], "reason": "invalid_payload"}
        projection = C.project_combat(
            self.items(), {}, C.ACTION_KILL, 5, self.item_of, empty
        )
        self.assertTrue(projection["ok"])
        self.assertIs(projection["inventory"], empty)

    def test_the_projection_reports_the_ordering_and_both_gates(self) -> None:
        projection = self.project()
        self.assertEqual(
            len(projection["validation_order"]), C.VALIDATION_ORDER_STEPS
        )
        self.assertEqual(projection["validation_order"][-1]["check"],
                         "post_execution_proof")
        self.assertEqual(
            [step for step in projection["validation_order"]
             if step["check"] == "destruction"][0]["step"], C.DESTRUCTION_STEP
        )
        self.assertEqual(len(projection["gates"]), C.GATE_COUNT)
        self.assertIn("before dispatch", projection["ordering_rule"])

    def test_the_projection_reports_a_neutral_vector_and_never_a_resource_delta(self) -> None:
        projection = self.project()
        self.assertEqual(projection["resource_delta"], [0] * C.RESOURCE_VECTOR_SLOTS)
        for derived in ("damage", "defence", "reward", "honour", "ratio", "progress"):
            with self.subTest(derived=derived):
                self.assertNotIn(derived, projection)

    def test_an_unknown_committed_item_yields_no_flag_and_no_ledger_entry(self) -> None:
        projection = C.project_combat(
            {"7": crafted_row(99999)}, {}, C.ACTION_RESOLVE, 99999, lambda _i: None
        )
        self.assertTrue(projection["ok"])
        self.assertIsNone(projection["committed_resurrectable"])
        self.assertFalse(projection["ledger_written"])
        self.assertEqual(projection["destruction"], 1)

    def test_the_accessor_is_unused_so_committed_content_is_never_read_from_here(self) -> None:
        source = module_source()
        self.assertNotIn("get_attribute_from_item_id", source)
        self.assertNotIn("boot.config", source)


class ContractTests(unittest.TestCase):
    """The two kill contracts, the divergence, and the team asymmetry."""

    def test_the_row_removal_contract_states_structural_non_participation(self) -> None:
        contract = C.KILL_CONTRACT
        self.assertTrue(contract["deletes_addressed_row"])
        self.assertFalse(contract["reaches_ledger"])
        self.assertEqual(contract["ledger_references"], 0)
        self.assertIn("push_dead_unit", contract["note"])
        self.assertIn("property of the branch", contract["note"])

    def test_the_row_removal_branch_really_holds_no_ledger_reference(self) -> None:
        lines = legacy_lines("command.py")
        block = "\n".join(lines[168:181])
        self.assertIn('cmd == "kill"', "\n".join(lines[160:185]))
        for absent in ("deadHeroes", "push_dead_unit", "privateState"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, block)

    def test_the_item_keyed_contract_states_it_writes_nothing(self) -> None:
        contract = C.KILL_IID_CONTRACT
        self.assertFalse(contract["statement_writes_save_state"])
        self.assertEqual(
            sorted(contract["local_bindings"]), ["item_id", "reason_str"]
        )
        self.assertEqual(contract["mutates"], [])
        self.assertFalse(contract["resources_move"])
        self.assertFalse(contract["reaches_ledger"])
        self.assertEqual(contract["delivered"], "as a proven no-op")
        self.assertEqual(contract["not_delivered"], "as a refusal")
        self.assertIn("intent is unknown", contract["why"].lower())

    def test_the_item_keyed_branch_binds_two_locals_and_prints(self) -> None:
        # The claim is "NO WRITE STATEMENT AT ALL", which is about the SAVE, not
        # about assignment syntax: the branch does bind `item_id` and
        # `reason_str` from `args`, so "contains no `=`" would be false and
        # would have to be restated as "writes nothing".  Measured over the
        # branch body rather than asserted.
        lines = legacy_lines("command.py")
        block = "\n".join(lines[182:187])
        self.assertIn('cmd == "%s"' % C.KILL_IID_COMMAND, block)
        self.assertIn("print(", block)
        body = textwrap.dedent("\n".join(lines[183:187]))
        tree = ast.parse(body)
        statements = [
            node for node in tree.body if not isinstance(node, ast.Expr)
        ] + [node for node in tree.body if isinstance(node, ast.Expr)]
        assigned = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
        self.assertEqual(len(assigned), 2)
        for node in assigned:
            for target in node.targets:
                # A bare local only: no subscript, attribute, or starred target,
                # so nothing in the save can be written through it.
                with self.subTest(target=ast.dump(target)):
                    self.assertIsInstance(target, ast.Name)
        self.assertTrue(statements)
        # And no call other than the print and the one it formats with.
        calls = sorted(
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        )
        self.assertEqual(calls, ["get_name_from_item_id", "print", "str"])

    def test_the_divergence_is_recorded_and_never_reported_as_parity(self) -> None:
        record = C.DIVERGENCE_RECORD
        self.assertEqual(record["status"], "DIVERGENCE, NOT PARITY")
        self.assertIn("ARBITRARY", record["legacy_status"])
        self.assertIn("AT MOST ONE", record["modern_status"])
        self.assertTrue(record["recorded_not_narrowed"])
        self.assertIn("never observed", record["unobserved_request_shape"])

    def test_the_team_asymmetry_is_recorded_not_exercised_and_not_refused(self) -> None:
        record = C.team_asymmetry()
        self.assertEqual(record["status"], "RECORDED, NOT EXERCISED, NOT REFUSED")
        self.assertFalse(record["exercised"])
        self.assertFalse(record["refused"])
        self.assertIn("DESTROYED", record["consequence"])
        self.assertIn("truthy", record["row_removal_helper"]["accepts"].lower())
        self.assertIn("TEAM 1 ONLY", record["ledger_helper"]["accepts"])
        self.assertFalse(record["row_removal_helper"]["is_dispatcher_branch"])
        self.assertFalse(record["ledger_helper"]["is_dispatcher_branch"])

    def test_no_committed_unit_row_is_on_a_team_other_than_one(self) -> None:
        # Task 4.2: the reason the asymmetry is unreachable, measured.
        table = committed_unit_ids()
        offenders = 0
        rows = 0
        for record in committed_documents():
            items = record["document"]["maps"][0]["items"]
            for row in items.values():
                if not (isinstance(row, list) and len(row) == C.MAP_ROW_SLOTS):
                    continue
                if str(row[C.SLOT_ITEM_ID]) not in table:
                    continue
                rows += 1
                if row[C.SLOT_PLAYER] != 1:
                    offenders += 1
        self.assertGreater(rows, 0)
        self.assertEqual(offenders, 0)
        self.assertEqual(rows, C.TEAM_ASYMMETRY["committed_unit_rows"])
        self.assertEqual(
            C.TEAM_ASYMMETRY["committed_unit_rows_on_team_one"], rows
        )

    def test_the_asymmetry_is_not_refused_by_any_refusal_reason(self) -> None:
        # No refusal REASON is about the team.  Measured over the closed reason
        # vocabulary rather than the prose of the rules, which legitimately
        # mentions the team when explaining that it is not checked.
        declared = sorted(
            entry["refusal"] for entry in C.refusals()
        ) + sorted(
            str(step.get("code", "")) for step in C.validation_order()
        )
        self.assertEqual([r for r in declared if "team" in r], [])
        for name in dir(C):
            with self.subTest(name=name):
                if not name.startswith("REASON_"):
                    continue
                self.assertNotIn("team", str(getattr(C, name)).lower())

    def test_the_refusal_families_separate_the_enforced_from_the_declined(self) -> None:
        entries = {entry["refusal"]: entry for entry in C.refusals()}
        self.assertTrue(entries["client_dictated_destruction"]["implemented"])
        for declined in ("combat_resolution", "no_cost_or_reward", "syringe_cost",
                         "placement_validation"):
            with self.subTest(refusal=declined):
                self.assertFalse(entries[declined]["implemented"])
        for entry in C.refusals():
            with self.subTest(refusal=entry["refusal"]):
                self.assertTrue(entry["rule"].strip())

    def test_the_no_combat_rule_names_the_zero_consumer_fields(self) -> None:
        rule = C.NO_COMBAT
        for field in ("attack", "defense", "life", "attack_interval", "attack_range",
                      "best_against", "best_against_mult", "velocity"):
            with self.subTest(field=field):
                self.assertIn(field, rule)
        # The rule shouts the phrase in caps, so the check is case-folded rather
        # than the prose made quiet.
        self.assertIn("zero legacy consumers", rule.lower())
        self.assertIn("mission", rule.lower())

    def test_the_no_cost_rule_names_every_discarded_key_it_claims(self) -> None:
        # The rule names its keys in prose; which of the DERIVED discarded keys
        # that covers is measured here rather than transcribed, so this suite
        # never carries a key list of its own.
        rule = C.NO_COST_OR_REWARD
        named = [
            key for key in derived_inventory()["key_names"]
            if re.search(r"\b%s\b" % re.escape(key), rule)
        ]
        self.assertGreaterEqual(len(named), 3)
        for key in named:
            with self.subTest(key=key):
                self.assertIn(key, derived_inventory()["discarded"])

    def test_the_placement_validation_absence_is_recorded_as_a_server_gap(self) -> None:
        rule = C.NO_PLACEMENT_VALIDATION
        for absent in ("occupancy", "bounds", "type", "terrain"):
            with self.subTest(absent=absent):
                self.assertIn(absent, rule.lower())
        self.assertIn("M13", rule)

    def test_the_syringe_rule_names_the_field_and_its_zero_consumers(self) -> None:
        self.assertIn("syringes", C.NO_SYRINGE_COST)
        self.assertIn("zero legacy consumers", C.NO_SYRINGE_COST)

    def test_the_ordering_rule_names_the_persistence_boundary(self) -> None:
        rule = C.ORDERING_RULE
        self.assertIn("command.py:30,32", rule)
        self.assertIn("BATCH", rule)
        self.assertIn("866", rule)
        self.assertIn("874", rule)

    def test_the_validation_order_places_the_write_after_every_check(self) -> None:
        steps = C.validation_order()
        self.assertEqual(len(steps), C.VALIDATION_ORDER_STEPS)
        self.assertEqual([step["step"] for step in steps], list(range(1, 11)))
        before = [step for step in steps if step["resolves"] == "before dispatch"]
        self.assertEqual(max(step["step"] for step in before), C.DESTRUCTION_STEP - 1)
        write = [step for step in steps if step["resolves"] == "THE WRITE STEP"]
        self.assertEqual(len(write), 1)
        self.assertEqual(write[0]["step"], C.DESTRUCTION_STEP)
        self.assertEqual(steps[-1]["check"], "post_execution_proof")
        self.assertEqual(steps[-1]["resolves"], "after dispatch")

    def test_the_client_dictated_check_precedes_the_eligibility_check(self) -> None:
        codes = {
            step["check"]: step.get("code")
            for step in C.validation_order()
            if step.get("code")
        }
        self.assertEqual(
            codes["no_client_dictated_destruction_key"],
            C.REASON_CLIENT_DICTATED_DESTRUCTION,
        )
        self.assertEqual(
            codes["eligible_row_resolves"], C.REASON_NO_ELIGIBLE_ROW
        )
        order = [step["step"] for step in C.validation_order()]
        self.assertLess(
            order.index(2), order.index(4),
            "the client-dictated guard must resolve before eligibility",
        )


class CorrectionTests(unittest.TestCase):
    """The falsified figures, carried beside the measured ones (task 5.3)."""

    def test_the_field_inventory_correction_pairs_both_numbers(self) -> None:
        correction = C.conflicts()["field_inventory"]
        self.assertNotEqual(
            correction["recorded_read_key_count"], correction["measured_read_key_count"]
        )
        self.assertNotEqual(
            correction["recorded_discarded_count"], correction["measured_discarded_count"]
        )
        self.assertEqual(correction["key_absent_from_the_recorded_table"], "voluntary_end")
        self.assertEqual(correction["omitted_in_both"], "voluntary_end (command.py:839-840)")

    def test_the_recorded_inventory_did_not_match_its_own_table_either(self) -> None:
        correction = C.conflicts()["field_inventory"]
        self.assertNotEqual(
            correction["recorded_discarded_count"],
            correction["recorded_discarded_count_in_the_own_table"],
        )

    def test_the_measured_figures_are_re_derived_here_and_match(self) -> None:
        inventory = derived_inventory()
        self.assertEqual(
            inventory["key_count"], C.FIELD_INVENTORY_CORRECTION["measured_read_key_count"]
        )
        self.assertEqual(
            len(inventory["discarded"]),
            C.FIELD_INVENTORY_CORRECTION["measured_discarded_count"],
        )

    def test_the_corpus_correction_is_measured_here_and_matches(self) -> None:
        correction = C.conflicts()["corpus"]
        documents = committed_documents()
        table = committed_unit_ids()
        placed = 0
        unit_rows = 0
        team_one = 0
        resurrectable = 0
        non_empty = 0
        for record in documents:
            items = record["document"]["maps"][0]["items"]
            placed += sum(
                1 for row in items.values()
                if isinstance(row, list) and len(row) == C.MAP_ROW_SLOTS
            )
            for row in items.values():
                if not (isinstance(row, list) and len(row) == C.MAP_ROW_SLOTS):
                    continue
                identity = str(row[C.SLOT_ITEM_ID])
                if identity not in table:
                    continue
                unit_rows += 1
                if row[C.SLOT_PLAYER] == 1:
                    team_one += 1
                flag = table[identity]
                if flag is not None and flag > 0:
                    resurrectable += 1
            private = record["document"].get("privateState")
            ledger = private.get(C.LEDGER_KEY) if isinstance(private, dict) else None
            if isinstance(ledger, dict) and ledger:
                non_empty += 1
        self.assertEqual(correction["measured_documents"], len(documents))
        self.assertEqual(correction["measured_placed_rows"], placed)
        self.assertEqual(correction["measured_unit_rows"], unit_rows)
        self.assertEqual(correction["measured_unit_rows_on_team_one"], team_one)
        self.assertEqual(correction["measured_unit_rows_resurrectable"], resurrectable)
        self.assertEqual(
            correction["measured_documents_with_non_empty_ledger"], non_empty
        )

    def test_the_document_and_ledger_counts_falsify_the_committed_record(self) -> None:
        correction = C.conflicts()["corpus"]
        self.assertNotEqual(
            correction["recorded_documents"], correction["measured_documents"]
        )
        self.assertNotEqual(
            correction["recorded_documents_with_non_empty_ledger"],
            correction["measured_documents_with_non_empty_ledger"],
        )
        self.assertNotEqual(
            correction["recorded_neutral_ledger_keys"],
            correction["measured_neutral_ledger_keys"],
        )

    def test_the_reproducing_figures_are_listed_and_the_failing_ones_named(self) -> None:
        correction = C.conflicts()["corpus"]
        self.assertGreaterEqual(len(correction["reproduces_exactly"]), 5)
        self.assertEqual(len(correction["does_not_reproduce"]), 3)
        self.assertGreaterEqual(len(correction["counting_rules_measured"]), 5)

    def test_the_ledger_is_private_state_and_not_a_map_key(self) -> None:
        # A census reading maps[0].deadHeroes measures zero documents, which is
        # how the recorded figure of four was mis-derived.
        for record in committed_documents():
            with self.subTest(document=record["path"]):
                self.assertNotIn(C.LEDGER_KEY, record["document"]["maps"][0])

    def test_the_neutral_ledger_holds_the_measured_key_count(self) -> None:
        correction = C.conflicts()["corpus"]
        document = REPO / "villages" / "Neutral.json"
        save = json.loads(document.read_text(encoding="utf-8"))
        ledger = save["privateState"][C.LEDGER_KEY]
        self.assertEqual(len(ledger), correction["measured_neutral_ledger_keys"])

    def test_both_correction_blocks_are_deep_copies(self) -> None:
        first = C.conflicts()
        first["field_inventory"]["measured_read_key_count"] = 999
        first["corpus"]["measured_documents"] = 999
        self.assertNotEqual(C.conflicts()["field_inventory"]["measured_read_key_count"], 999)
        self.assertNotEqual(C.conflicts()["corpus"]["measured_documents"], 999)


class RecordTests(unittest.TestCase):
    """Provenance and the explicit non-claims."""

    def test_the_provenance_names_every_owner_and_source(self) -> None:
        record = C.PROVENANCE
        self.assertEqual(record["capability"], "godot-combat-actions")
        self.assertEqual(record["legacy_source"], "command.py")
        self.assertEqual(record["combat_branch"], "end_attack (command.py:808-885)")
        self.assertEqual(record["kill_branch"], "kill (command.py:169-181)")
        self.assertEqual(record["kill_iid_branch"], "kill_iid (command.py:183-187)")
        self.assertEqual(record["ledger_fourth_door_owner"], "godot-unit-behaviors")
        self.assertEqual(record["quest_path_caller"], "godot-quests")

    def test_the_non_claims_cover_every_required_refusal(self) -> None:
        joined = " ".join(C.NON_CLAIMS)
        for required in (
            "FLASH, RUFFLE, ACTIONSCRIPT, OR BROWSER",
            "NO CLIENT-DICTATED DESTRUCTION COUNT IS REPRODUCED",
            "NO DAMAGE, HEALTH, DEFENCE, HIT CHANCE, OR LIFE ARITHMETIC",
            "NO MISSION IS DISPATCHED, RESOLVED, OR COMPLETED",
            "NO HONOUR OR REWARD IS PAID",
            "NO SYRINGE COST IS CHARGED",
            "NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED",
            "TEAM ASYMMETRY",
            "NO WINDOWED CAPTURE AND NO PIXEL-PARITY",
        ):
            with self.subTest(claim=required[:40]):
                self.assertIn(required, joined)

    def test_the_non_claims_leave_the_ledger_and_the_village_documents_named(self) -> None:
        joined = " ".join(C.NON_CLAIMS)
        self.assertIn("godot-mission-vocabulary", joined)
        # The non-claims are upper-case headings, so the case is folded here
        # rather than the record rewritten into mixed case.
        self.assertIn("committed village", joined.lower())


class AntiInventionGuardTests(unittest.TestCase):
    """Task 4.3: the whole function inventory, plus the structural absences."""

    def test_the_module_declares_exactly_the_pinned_functions(self) -> None:
        self.assertEqual(module_functions(), EXPECTED_MODULE_FUNCTIONS)

    def test_no_helper_name_carries_an_invented_combat_rule(self) -> None:
        declared = module_functions()
        for fragment in FORBIDDEN_HELPER_FRAGMENTS:
            with self.subTest(fragment=fragment):
                offenders = [
                    name for name in declared
                    if fragment in name.lower()
                    and name not in FORBIDDEN_HELPER_EXEMPT
                ]
                self.assertEqual(offenders, [])

    def test_the_module_source_declares_no_such_helper_either(self) -> None:
        code = module_source()
        for fragment in FORBIDDEN_HELPER_FRAGMENTS:
            with self.subTest(fragment=fragment):
                self.assertIsNone(
                    re.search(r"^\s*def\s+\w*%s\w*\s*\(" % re.escape(fragment),
                              code, re.MULTILINE),
                    "combat_envelope declares a helper carrying %r" % fragment,
                )

    def test_no_code_identifier_names_a_damage_honour_reward_or_mission_rule(self) -> None:
        identifiers = module_code_identifiers()
        for token in ("damage", "defence", "defense", "honour", "honor", "reward",
                      "mission", "casualt", "hit_chance", "clamp"):
            with self.subTest(token=token):
                offenders = [
                    name for name in identifiers
                    if token in name.lower() and name not in FORBIDDEN_HELPER_EXEMPT
                ]
                self.assertEqual(
                    offenders, [],
                    "combat_envelope names an identifier carrying %r" % token,
                )

    def test_the_module_derives_no_arithmetic_from_the_request(self) -> None:
        """No multiplication, division, or subtraction over client input.

        ``max``/``min``/``int`` are deliberately not banned: this module uses
        them for structural validation and the ledger's own increment, never to
        compute a quantity from a combat field.
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
                    continue
                if isinstance(inner.op, ast.Mod) and _is_modulo_of_a_string(inner):
                    continue
                if isinstance(inner.op, ast.Mod):
                    offenders.append("%s:Mod" % function.name)
        self.assertEqual(sorted(set(offenders)), [])

    def test_the_module_computes_no_time_or_pow_based_quantity(self) -> None:
        tree = ast.parse(module_source())
        banned_calls = {"pow", "sqrt", "exp", "log", "log2", "log10", "round",
                        "trunc", "hypot", "atan2", "fmod"}
        for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for inner in ast.walk(function):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                    with self.subTest(function=function.name, call=inner.func.id):
                        self.assertNotIn(inner.func.id, banned_calls)

    def test_the_module_opens_no_file_except_the_one_legacy_source(self) -> None:
        tree = ast.parse(module_source())
        opened: List[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "open":
                continue
            opened.append(ast.dump(node.args[0]) if node.args else "<no argument>")
        self.assertEqual(len(opened), 1)
        # The only ``open`` is the ``command.py`` byte read, and its path is
        # built by ``os.path.join`` from the declared relative constant.  The
        # check is over the call itself rather than the local name it is bound
        # to, so renaming that local cannot silently change what is verified.
        path_joins = [
            ast.dump(node) for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "join"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "path"
        ]
        self.assertEqual(len(path_joins), 1)
        # The join takes the declared constant by NAME rather than a literal, so
        # the check is over the argument node: a transcription of "command.py"
        # here instead of the constant would fail, which is the point.
        self.assertIn("LEGACY_SOURCE_RELATIVE", path_joins[0])
        self.assertEqual(C.LEGACY_SOURCE_RELATIVE, "command.py")
        self.assertTrue((REPO / C.LEGACY_SOURCE_RELATIVE).is_file())
        # And no other filesystem entry point is present at all, so this guard
        # cannot be satisfied while some other read exists.
        for banned in ("remove", "rename", "unlink", "rmdir", "makedirs",
                       "listdir", "walk", "exists", "write_text", "write_bytes"):
            with self.subTest(entry_point=banned):
                self.assertIsNone(
                    re.search(r"\b%s\s*\(" % banned, module_source())
                )

    def test_the_module_reports_the_correction_and_never_fabricates_a_figure(self) -> None:
        joined = " ".join(C.NON_CLAIMS) + " " + json.dumps(
            C.conflicts(), sort_keys=True
        )
        self.assertIn("MEASURED", joined.upper())
        # The falsified figure survives ONLY as the recorded side of a pair: the
        # measured side is a different number, which is the whole point of the
        # correction rather than a replacement.
        correction = C.CORPUS_CORRECTION
        self.assertNotEqual(
            correction["recorded_neutral_ledger_keys"],
            correction["measured_neutral_ledger_keys"],
        )
        self.assertGreater(
            correction["recorded_neutral_ledger_keys"],
            correction["measured_neutral_ledger_keys"],
        )
        self.assertEqual(
            correction["measured_neutral_ledger_keys"],
            len(
                json.loads(
                    (REPO / "villages" / "Neutral.json").read_text(encoding="utf-8")
                )["privateState"][C.LEDGER_KEY]
            ),
        )


def _is_modulo_of_a_string(node: ast.BinOp) -> bool:
    """True for ``"a" % b``, which is string formatting rather than arithmetic."""
    return isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)


def _is_sequence_repetition(node: ast.BinOp) -> bool:
    """True for ``[x] * n`` and ``"x" * n``, which build a sequence.

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


class OfflineGuardTest(unittest.TestCase):
    """"Pure derivation, no socket" is checked rather than asserted."""

    def test_the_suite_runs_under_the_socket_guard(self) -> None:
        with harness.offline():
            self.assertTrue(derived_inventory()["ok"])
            self.assertTrue(
                C.select_eligible_rows({"7": crafted_row(1020)}, 1020)["ok"]
            )
            C.set_derived_identity(1020)
            try:
                self.assertTrue(C.combat_payload(C.ACTION_RESOLVE).startswith("{"))
            finally:
                C.clear_derived_identity()


if __name__ == "__main__":
    unittest.main()
