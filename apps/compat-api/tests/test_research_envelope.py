#!/usr/bin/env python3
"""Offline unit tests for ``research_envelope`` (OpenSpec tasks 3.1/3.2/4.1/4.2).

No server, no socket, no network: this module imports the derivation and asserts
it against **the committed bytes themselves** — the seven legacy root modules,
the twenty-two normalized content files, ``config/main.json``, and the
committed corpus save — so every recorded constant is a **measurement** rather
than a restatement of this module's own prose (task 4.4).  A constant that drifts
from the source fails here instead of being published.

Covered:

* the closed four-action vocabulary and the command each derives;
* the **exact** argument list of every branch, including the cash branch's
  ``[cash, track]`` shape and the module's derived cash value;
* the derived counter effect of every branch on every track, including the item
  branch's **paired** step-and-instant reset and the cash branch's
  instant-only zeroing;
* the **five** writers of the research instant, the four branch writers and the
  ``fast_forward`` writer, measured out of ``command.py``;
* the fail-closed vector resolution: absent, non-list, wrong length,
  non-integer, and negative;
* the **copy** contract, which is what keeps the endpoint's before-snapshot from
  aliasing the live state the dispatcher mutates in place;
* the four refusal families, each with a non-empty recorded reason;
* the **measured** content-absence findings, including the two figures the M9
  investigation and this line's proposal got **wrong**;
* the read-only projection, and that it computes **nothing** from the counters;
* the whole module's static-function inventory against a pinned list, so a
  ``research_price`` / ``research_duration`` / ``is_research_complete`` /
  ``research_ready`` / ``unlock_research`` helper fails the run wherever it is
  added (task 4.3).
"""

from __future__ import annotations

import ast
import copy
import json
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness  # noqa: F401  (path setup)

import research_envelope

REPO = harness.REPO_ROOT
LEGACY_MODULES = (
    "command.py",
    "engine.py",
    "sessions.py",
    "server.py",
    "constants.py",
    "get_game_config.py",
    "version.py",
)

# The whole static-function inventory of ``research_envelope``.  The
# anti-invention gate: any helper added to the module shows up here and fails the
# run, which is what makes task 4.3's absence checks structural.
EXPECTED_MODULE_FUNCTIONS = [
    "build_envelope",
    "command_for_action",
    "copy_vector",
    "derived_research",
    "expected_state",
    "is_action",
    "is_track",
    "neutral_vector",
    "project_research",
    "resolve_vector",
    "snapshot_counters",
    "validate_vector",
]

#: Helper names whose mere existence would be an invented rule.
FORBIDDEN_HELPERS = [
    "research_price",
    "research_duration",
    "is_research_complete",
    "research_ready",
    "unlock_research",
    "research_step_count",
    "research_reward",
    "research_remaining",
    "research_cost",
    "research_time_left",
    "fast_forward",
]


def module_source() -> str:
    return Path(research_envelope.__file__).read_text(encoding="utf-8")


def module_functions() -> List[str]:
    tree = ast.parse(module_source())
    return sorted(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def legacy_text(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


def counter_sites(counter: str) -> List[Dict[str, Any]]:
    """Every occurrence of one counter across the seven legacy modules."""
    sites: List[Dict[str, Any]] = []
    for name in LEGACY_MODULES:
        for line_number, line in enumerate(legacy_text(name).split("\n"), 1):
            count = line.count(counter)
            if count:
                sites.append(
                    {
                        "module": name,
                        "line": line_number,
                        "occurrences": count,
                        "text": line.strip(),
                    }
                )
    return sites


def branch_line_range(branch: str) -> List[int]:
    """``[first, last]`` of one dispatcher branch, measured out of command.py."""
    lines = legacy_text("command.py").split("\n")
    start = None
    for index, line in enumerate(lines):
        if line.strip() == 'elif cmd == "%s":' % branch:
            start = index
            break
    if start is None:
        raise AssertionError("no dispatcher branch named %r" % branch)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("elif cmd ==") or stripped == "elif cmd ==":
            # ``index`` is 0-based and names the NEXT branch, so the previous
            # branch's last line is ``index - 1`` in 1-based numbering.
            return [start + 1, index - 1]
    raise AssertionError("branch %r is the last branch; no terminator" % branch)


def private_state_of(document: Dict[str, Any]) -> Dict[str, Any]:
    return document["privateState"]


class VocabularyTests(unittest.TestCase):
    """The closed action set and the command each action derives."""

    def test_the_vocabulary_is_closed_and_holds_exactly_four_actions(self) -> None:
        self.assertEqual(
            sorted(research_envelope.ACTIONS),
            ["buy_step_cash", "next_item", "next_step", "reset_item"],
        )
        self.assertEqual(len(research_envelope.ACTIONS), 4)
        self.assertEqual(research_envelope.BRANCH_COUNT, 4)
        self.assertEqual(len(research_envelope.BRANCHES), 4)

    def test_each_action_derives_its_committed_command(self) -> None:
        self.assertEqual(
            research_envelope.ACTION_COMMANDS,
            {
                "next_step": "next_research_step",
                "buy_step_cash": "research_buy_step_cash",
                "next_item": "next_research_item",
                "reset_item": "reset_research_item",
            },
        )
        for action in research_envelope.ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(
                    research_envelope.command_for_action(action),
                    research_envelope.ACTION_COMMANDS[action],
                )

    def test_unknown_actions_are_refused_before_the_dispatcher(self) -> None:
        for value in ["", "fast_forward", "NEXT_STEP", "step", None, 0, []]:
            with self.subTest(value=value):
                self.assertFalse(research_envelope.is_action(value))
                with self.assertRaises(research_envelope.EnvelopeError) as caught:
                    research_envelope.command_for_action(value)
                self.assertEqual(caught.exception.code, "invalid_action")

    def test_fast_forward_is_absent_from_the_vocabulary_by_decision(self) -> None:
        """Design D7: the recorded fourth writer is offered by no action."""
        self.assertEqual(research_envelope.FAST_FORWARD_COMMAND, "fast_forward")
        for action in research_envelope.ACTIONS:
            with self.subTest(action=action):
                self.assertNotEqual(
                    research_envelope.ACTION_COMMANDS[action],
                    research_envelope.FAST_FORWARD_COMMAND,
                )
        self.assertNotIn("fast_forward", research_envelope.ACTIONS)


class TrackTests(unittest.TestCase):
    """Two tracks, reported; the mapping structurally unusable (design D5)."""

    def test_two_tracks_are_reported_with_their_committed_building_ids(self) -> None:
        self.assertEqual(research_envelope.TRACK_COUNT, 2)
        self.assertEqual(len(research_envelope.TRACKS), 2)
        self.assertEqual(
            [(record["track"], record["name"], record["building_id"])
             for record in research_envelope.TRACKS],
            [(0, "TYPE_AREA_51", 139), (1, "TYPE_ROBOTIC", 86)],
        )

    def test_the_committed_building_ids_are_measured_out_of_constants(self) -> None:
        text = legacy_text("constants.py").split("\n")
        for constant, expected in (
            ("ID_BUILDING_AREA_51", 139),
            ("ID_BUILDING_ROBOTIC_CENTER", 86),
        ):
            with self.subTest(constant=constant):
                matches = [
                    (index, line.strip())
                    for index, line in enumerate(text, 1)
                    if line.strip().startswith("%s = " % constant)
                ]
                self.assertEqual(len(matches), 1, matches)
                self.assertEqual(matches[0][1], "%s = %d" % (constant, expected))

    def test_the_track_names_exist_only_in_the_four_branch_comments(self) -> None:
        """They are **undefined** in the server, which is the whole finding."""
        command_lines = legacy_text("command.py").split("\n")
        comment_lines = [
            index
            for index, line in enumerate(command_lines, 1)
            if "#" in line
            and (research_envelope.TRACK_NAME_PRIMARY in line
                 or research_envelope.TRACK_NAME_SECONDARY in line)
        ]
        self.assertEqual(comment_lines, [269, 278, 285, 294])
        for name in LEGACY_MODULES:
            text = legacy_text(name)
            for token in (research_envelope.TRACK_NAME_PRIMARY,
                          research_envelope.TRACK_NAME_SECONDARY):
                occurrences = text.count(token)
                with self.subTest(module=name, token=token):
                    # Only the four comments carry them, so occurrences equal the
                    # comment-line count and every one is inside a comment.
                    self.assertEqual(occurrences, 4 if name == "command.py" else 0)
        for record in research_envelope.TRACKS:
            with self.subTest(track=record["track"]):
                self.assertFalse(record["defined_in_server"])

    def test_no_module_identifier_is_named_after_either_track_constant(self) -> None:
        """Design D5 made mechanical: the mapping can never be mistaken for a used one."""
        tree = ast.parse(module_source())
        declared: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                declared.append(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                declared.append(node.id)
            elif isinstance(node, ast.arg):
                declared.append(node.arg)
            elif isinstance(node, ast.keyword) and node.arg:
                declared.append(node.arg)
        forbidden = {
            research_envelope.TRACK_NAME_PRIMARY,
            research_envelope.TRACK_NAME_SECONDARY,
        }
        self.assertEqual(
            sorted(set(declared) & forbidden), [],
            "no declared identifier in research_envelope may be named after a "
            "track constant",
        )
        # And the names survive only as STRING values inside the two track
        # records, which is exactly how they are reported.
        names = [record["name"] for record in research_envelope.TRACKS]
        self.assertEqual(names, ["TYPE_AREA_51", "TYPE_ROBOTIC"])

    def test_only_the_two_tracks_are_accepted_and_no_bound_is_invented(self) -> None:
        self.assertTrue(research_envelope.is_track(0))
        self.assertTrue(research_envelope.is_track(1))
        for value in [2, 7, 999, -1, "0", None, True, 1.0]:
            with self.subTest(value=value):
                self.assertFalse(research_envelope.is_track(value))


class BranchEffectTests(unittest.TestCase):
    """The four recorded effects, measured against the committed source."""

    def test_the_four_branch_line_ranges_are_the_recorded_ones(self) -> None:
        measured = {
            record["command"]: branch_line_range(record["command"])
            for record in research_envelope.BRANCHES
        }
        self.assertEqual(
            measured,
            {
                "next_research_step": [268, 274],
                "research_buy_step_cash": [276, 282],
                "next_research_item": [284, 291],
                "reset_research_item": [293, 300],
            },
        )
        for record in research_envelope.BRANCHES:
            with self.subTest(command=record["command"]):
                self.assertEqual(record["source"],
                                 "command.py:%d-%d" % tuple(measured[record["command"]]))

    def test_the_step_branch_increments_the_step_and_stamps_the_instant(self) -> None:
        derived = research_envelope.derived_research(
            research_envelope.COMMITTED_VECTOR, 0,
            research_envelope.ACTION_STEP,
        )
        self.assertEqual(derived["command"], "next_research_step")
        self.assertEqual(derived["step"], 1)
        self.assertTrue(derived["stamps_instant"])
        self.assertEqual(derived["instant"], True)
        self.assertEqual(derived["item"], 0)
        self.assertEqual(
            sorted(derived["written"]), ["researchStepNumber", "timeStampDoResearch"]
        )
        # A second step on the same track increments again.
        again = research_envelope.derived_research(
            {key: ([derived["step"], 0] if key == "researchStepNumber" else list(value))
             for key, value in research_envelope.COMMITTED_VECTOR.items()},
            0, research_envelope.ACTION_STEP,
        )
        self.assertEqual(again["step"], 2)

    def test_the_cash_branch_zeroes_the_instant_and_charges_nothing(self) -> None:
        before = {
            "researchStepNumber": [4, 0],
            "researchItemNumber": [2, 0],
            "timeStampDoResearch": [1700000000, 0],
        }
        derived = research_envelope.derived_research(
            before, 0, research_envelope.ACTION_BUY_STEP_CASH
        )
        self.assertEqual(derived["command"], "research_buy_step_cash")
        self.assertEqual(derived["written"], ["timeStampDoResearch"])
        self.assertTrue(derived["instant_only"])
        self.assertEqual(derived["instant"], 0)
        self.assertEqual(derived["step"], 4, "the step counter is untouched")
        self.assertEqual(derived["item"], 2, "the item counter is untouched")
        self.assertTrue(derived["reads_a_price"])
        self.assertFalse(derived["charges"])
        self.assertFalse(derived["stamps_instant"])

    def test_the_item_branch_paired_reset_is_recorded_as_paired(self) -> None:
        before = {
            "researchStepNumber": [3, 0],
            "researchItemNumber": [1, 0],
            "timeStampDoResearch": [1700000000, 0],
        }
        derived = research_envelope.derived_research(
            before, 0, research_envelope.ACTION_ITEM
        )
        self.assertEqual(derived["command"], "next_research_item")
        self.assertEqual(derived["item"], 2, "the item counter increments")
        self.assertEqual(derived["step"], 0, "the step counter resets")
        self.assertEqual(derived["instant"], 0, "the research instant resets")
        self.assertTrue(derived["paired_reset"])
        # …and the pairing is measured out of the source: the two reset writes
        # are ADJACENT lines in the SAME branch, and no other branch resets the
        # step counter at all.
        record = next(
            entry for entry in research_envelope.BRANCHES
            if entry["command"] == "next_research_item"
        )
        self.assertTrue(record["paired_reset"])
        self.assertIn("TOGETHER", record["paired_reset_note"])
        lines = legacy_text("command.py").split("\n")
        self.assertIn("researchStepNumber", lines[287])
        self.assertIn("= 0", lines[287])
        self.assertIn("timeStampDoResearch", lines[288])
        self.assertIn("= 0", lines[288])
        step_writes = [
            index for index, line in enumerate(lines, 1)
            if "researchStepNumber" in line and "= 0" in line
        ]
        self.assertEqual(step_writes, [288, 297])

    def test_the_reset_branch_zeroes_all_three_counters(self) -> None:
        before = {
            "researchStepNumber": [9, 1],
            "researchItemNumber": [4, 2],
            "timeStampDoResearch": [1700000000, 1700000001],
        }
        derived = research_envelope.derived_research(
            before, 1, research_envelope.ACTION_RESET
        )
        self.assertEqual(derived["command"], "reset_research_item")
        self.assertEqual(derived["step"], 0)
        self.assertEqual(derived["item"], 0)
        self.assertEqual(derived["instant"], 0)
        self.assertEqual(sorted(derived["written"]),
                         sorted(research_envelope.COUNTERS))
        # The committed source writes them in the order item, step, instant.
        self.assertEqual(derived["written"],
                         ["researchItemNumber", "researchStepNumber",
                          "timeStampDoResearch"])

    def test_every_branch_records_the_absence_of_validation(self) -> None:
        for record in research_envelope.BRANCHES:
            with self.subTest(command=record["command"]):
                self.assertIn("none", record["validation"])
                for token in ("bounds", "clamp", "membership", "guard"):
                    self.assertIn(token, record["validation"])
                self.assertFalse(record["charges"])

    def test_a_branch_touches_exactly_one_track(self) -> None:
        before = {
            "researchStepNumber": [1, 2],
            "researchItemNumber": [3, 4],
            "timeStampDoResearch": [5, 6],
        }
        for action in research_envelope.ACTIONS:
            for track in (0, 1):
                with self.subTest(action=action, track=track):
                    derived = research_envelope.derived_research(
                        before, track, action
                    )
                    self.assertEqual(derived["track"], track)
                    self.assertEqual(derived["other_track"], 1 - track)
                    self.assertEqual(
                        sorted(derived["untouched_counters"]),
                        sorted(key for key in research_envelope.COUNTERS
                               if key not in derived["written"]),
                    )

    def test_the_derivation_refuses_an_unaddressable_track_or_action(self) -> None:
        for track in [2, -1, "0", None]:
            with self.subTest(track=track):
                with self.assertRaises(research_envelope.EnvelopeError) as caught:
                    research_envelope.derived_research(
                        research_envelope.COMMITTED_VECTOR, track,
                        research_envelope.ACTION_STEP,
                    )
                self.assertEqual(caught.exception.code, "invalid_track")
        with self.assertRaises(research_envelope.EnvelopeError) as caught:
            research_envelope.derived_research(
                research_envelope.COMMITTED_VECTOR, 0, "fast_forward"
            )
        self.assertEqual(caught.exception.code, "invalid_action")


class WriterTests(unittest.TestCase):
    """Five writers of the research instant, four of them branches (design D7)."""

    def test_the_writer_inventory_holds_five_entries(self) -> None:
        self.assertEqual(research_envelope.INSTANT_WRITER_COUNT, 5)
        self.assertEqual(len(research_envelope.INSTANT_WRITERS), 5)
        branches = [
            entry for entry in research_envelope.INSTANT_WRITERS
            if entry["kind"] == "dispatcher-branch"
        ]
        self.assertEqual(len(branches), 4)

    def test_the_four_branch_writers_are_measured_out_of_command(self) -> None:
        sites = counter_sites("timeStampDoResearch")
        self.assertEqual(len(sites), 5)
        self.assertEqual([entry["line"] for entry in sites], [272, 280, 289, 298, 923])
        branch_sites = [entry for entry in sites if entry["line"] != 923]
        self.assertEqual(len(branch_sites), 4)
        recorded = [
            entry for entry in research_envelope.INSTANT_WRITERS
            if entry["kind"] == "dispatcher-branch"
        ]
        self.assertEqual(
            [entry["source"] for entry in recorded],
            ["command.py:%d" % entry["line"] for entry in branch_sites],
        )

    def test_fast_forward_is_the_fifth_writer_and_its_seconds_are_client_sent(self) -> None:
        fast = next(
            entry for entry in research_envelope.INSTANT_WRITERS
            if entry["writer"] == research_envelope.INSTANT_WRITER_FAST_FORWARD
        )
        self.assertTrue(fast["client_writable"])
        self.assertIn("command.py:923", fast["source"])
        self.assertIn("command.py:927", fast["source"])
        lines = legacy_text("command.py").split("\n")
        self.assertEqual(lines[905 - 1].strip(), 'elif cmd == "fast_forward":')
        self.assertIn("seconds = args[0]", lines[906 - 1])
        self.assertIn('privateState["timeStampDoResearch"]', lines[923 - 1])
        self.assertIn(
            "research_timers[i] = max(0, research_timers[i] - seconds)", lines[927 - 1]
        )
        self.assertIn("CLIENT-SUPPLIED", research_envelope.FAST_FORWARD_CONTRACT)
        self.assertIn("IMPLEMENTED NOT AT ALL", research_envelope.FAST_FORWARD_CONTRACT)


class CounterSiteTests(unittest.TestCase):
    """The write-only property, measured (the line's sharpest finding)."""

    def test_the_step_counter_has_three_sites_and_every_one_is_a_write(self) -> None:
        sites = counter_sites("researchStepNumber")
        self.assertEqual(len(sites), 3)
        self.assertEqual(sum(entry["occurrences"] for entry in sites), 3)
        for entry in sites:
            with self.subTest(line=entry["line"]):
                self.assertEqual(entry["module"], "command.py")
                self.assertIn("[_type]", entry["text"])
                self.assertNotIn("==", entry["text"])

    def test_the_item_counter_has_two_sites_and_every_one_is_a_write(self) -> None:
        sites = counter_sites("researchItemNumber")
        self.assertEqual(len(sites), 2)
        self.assertEqual(sum(entry["occurrences"] for entry in sites), 2)
        self.assertEqual([entry["line"] for entry in sites], [287, 296])
        for entry in sites:
            with self.subTest(line=entry["line"]):
                self.assertEqual(entry["module"], "command.py")
                self.assertIn("]", entry["text"])

    def test_the_instant_counter_has_five_sites_and_only_one_reads_it(self) -> None:
        sites = counter_sites("timeStampDoResearch")
        self.assertEqual(len(sites), 5)
        self.assertEqual(sum(entry["occurrences"] for entry in sites), 5)
        reads = [
            entry for entry in sites
            if not (entry["text"].endswith("= 0")
                    or entry["text"].endswith("= time_now")
                    or "+= 1" in entry["text"])
        ]
        self.assertEqual(len(reads), 1)
        self.assertEqual(reads[0]["line"], 923)
        self.assertIn("research_timers = ", reads[0]["text"])
        self.assertEqual([entry["line"] for entry in sites], [272, 280, 289, 298, 923])

    def test_the_single_non_write_occurrence_is_the_fast_forward_read(self) -> None:
        """Every occurrence is classified: three step writes, two item writes,
        four instant writes, and exactly ONE read — at command.py:923."""
        classified: List[str] = []
        for counter in research_envelope.COUNTERS:
            for entry in counter_sites(counter):
                text = entry["text"]
                if text.startswith("research_timers = "):
                    classified.append("read command.py:%d" % entry["line"])
                elif "+= 1" in text:
                    classified.append("increment command.py:%d" % entry["line"])
                elif text.endswith("= 0"):
                    classified.append("zero command.py:%d" % entry["line"])
                elif text.endswith("= time_now"):
                    classified.append("stamp command.py:%d" % entry["line"])
                else:
                    classified.append("UNCLASSIFIED command.py:%d %s"
                                      % (entry["line"], text))
        self.assertEqual(
            sorted(classified),
            sorted(
                ["increment command.py:271", "zero command.py:288",
                 "zero command.py:297", "increment command.py:287",
                 "zero command.py:296", "stamp command.py:272",
                 "zero command.py:280", "zero command.py:289",
                 "zero command.py:298", "read command.py:923"]
            ),
        )
        # …and the four instant WRITES are the only branch writes of it, so the
        # instant's single reader is the fast_forward decrement.
        self.assertEqual(
            sum(1 for entry in classified if entry.startswith("read")), 1
        )

    def test_the_recorded_corpus_vector_matches_the_committed_save(self) -> None:
        seed = json.loads(
            (REPO / "tests" / "saves" / "fresh-player.json").read_text(encoding="utf-8")
        )
        private = private_state_of(seed)
        for counter in research_envelope.COUNTERS:
            with self.subTest(counter=counter):
                self.assertEqual(private[counter], [0, 0])
                self.assertEqual(len(private[counter]), research_envelope.TRACK_COUNT)
                self.assertEqual(
                    research_envelope.COMMITTED_VECTOR[counter], private[counter]
                )
        self.assertEqual(research_envelope.COMMITTED_PLACEMENTS,
                         len(seed["maps"][0]["items"]))
        self.assertEqual(
            research_envelope.COMMITTED_RESOURCE_BEFORE,
            {
                "xp": seed["maps"][0]["xp"],
                "gold": seed["maps"][0]["gold"],
                "wood": seed["maps"][0]["wood"],
                "oil": seed["maps"][0]["oil"],
                "steel": seed["maps"][0]["steel"],
                "cash": seed["playerInfo"]["cash"],
                "mana": seed["privateState"]["mana"],
            },
        )
        # No placed row mentions a research counter at all.
        for key, row in seed["maps"][0]["items"].items():
            with self.subTest(row=key):
                self.assertNotIn("research", json.dumps(row).lower())


class VectorTests(unittest.TestCase):
    """Fail-closed resolution and the copy contract."""

    def test_a_well_formed_private_state_resolves_to_copies(self) -> None:
        source = {
            "researchStepNumber": [1, 2],
            "researchItemNumber": [3, 4],
            "timeStampDoResearch": [5, 6],
        }
        resolved = research_envelope.resolve_vector(source)
        self.assertEqual(resolved, source)
        self.assertIsNot(resolved["researchStepNumber"],
                         source["researchStepNumber"])
        resolved["researchStepNumber"][0] = 99
        self.assertEqual(source["researchStepNumber"], [1, 2])

    def test_every_malformed_shape_is_refused_with_the_state_named(self) -> None:
        base = dict(research_envelope.COMMITTED_VECTOR)
        cases = [
            ({}, "unresolvable_research_state"),
            ({"researchStepNumber": {}, "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": "00", "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": [0], "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": [0, 0, 0], "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": ["0", 0], "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": [1.5, 0], "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": [True, 0], "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": [None, 0], "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": [-1, 0], "researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchItemNumber": [0, 0],
              "timeStampDoResearch": [0, 0]}, "unresolvable_research_state"),
            ({"researchStepNumber": [0, 0], "timeStampDoResearch": [0, 0]},
             "unresolvable_research_state"),
            (None, "unresolvable_research_state"),
            ("nope", "unresolvable_research_state"),
        ]
        for state, code in cases:
            with self.subTest(state=state):
                with self.assertRaises(research_envelope.EnvelopeError) as caught:
                    research_envelope.resolve_vector(state)
                self.assertEqual(caught.exception.code, code)
                self.assertNotEqual(str(caught.exception), "")

    def test_snapshot_counters_reads_the_private_state_of_a_whole_save(self) -> None:
        seed = json.loads(
            (REPO / "tests" / "saves" / "fresh-player.json").read_text(encoding="utf-8")
        )
        self.assertEqual(research_envelope.snapshot_counters(seed),
                         research_envelope.COMMITTED_VECTOR)
        with self.assertRaises(research_envelope.EnvelopeError) as caught:
            research_envelope.snapshot_counters({"maps": []})
        self.assertEqual(caught.exception.code, "unresolvable_research_state")


class ProjectionTests(unittest.TestCase):
    """The read-only projection, and that it derives nothing (design D1)."""

    def test_both_tracks_and_all_three_counters_are_reported_verbatim(self) -> None:
        vector = {
            "researchStepNumber": [7, 0],
            "researchItemNumber": [2, 5],
            "timeStampDoResearch": [1700000000, 0],
        }
        projection = research_envelope.project_research(vector)
        self.assertEqual(projection["track_count"], 2)
        self.assertEqual(len(projection["tracks"]), 2)
        self.assertEqual(
            projection["tracks"],
            [
                {"track": 0, "step": 7, "item": 2, "instant": 1700000000},
                {"track": 1, "step": 0, "item": 5, "instant": 0},
            ],
        )
        self.assertEqual(projection["counters"], vector)
        self.assertTrue(projection["verbatim"])

    def test_the_projection_derives_nothing_at_all(self) -> None:
        projection = research_envelope.project_research(
            research_envelope.COMMITTED_VECTOR
        )
        self.assertEqual(projection["derived"], {})
        # A 10-billion-second stamp derives no remaining time: there is no field
        # in which one could hide.
        stamped = research_envelope.project_research({
            "researchStepNumber": [3, 0],
            "researchItemNumber": [1, 0],
            "timeStampDoResearch": [10000000000, 0],
        })
        for row in stamped["tracks"]:
            with self.subTest(row=row):
                self.assertEqual(sorted(row), ["instant", "item", "step", "track"])
        self.assertEqual(stamped["derived"], {})

    def test_the_projection_reports_the_tracks_without_using_them(self) -> None:
        projection = research_envelope.project_research(
            research_envelope.COMMITTED_VECTOR
        )
        self.assertEqual(len(projection["tracks_source"]), 2)
        for record in projection["tracks_source"]:
            with self.subTest(track=record["track"]):
                self.assertIn("building_id", record)
                self.assertIn("TYPE_", record["name"])
        self.assertIn("REPORTED AND NEVER USED", projection["tracking_note"])

    def test_the_projection_copies_and_never_mutates(self) -> None:
        vector = {
            "researchStepNumber": [1, 1],
            "researchItemNumber": [2, 2],
            "timeStampDoResearch": [3, 3],
        }
        snapshot = copy.deepcopy(vector)
        projection = research_envelope.project_research(vector)
        self.assertEqual(vector, snapshot)
        projection["counters"]["researchStepNumber"][0] = 42
        projection["tracks"][0]["step"] = 42
        self.assertEqual(vector, snapshot)

    def test_the_projection_refuses_a_non_object_state(self) -> None:
        for value in [None, [], "00", 7]:
            with self.subTest(value=value):
                with self.assertRaises(research_envelope.EnvelopeError) as caught:
                    research_envelope.project_research(value)
                self.assertEqual(caught.exception.code, "unresolvable_research_state")


class ExpectedStateTests(unittest.TestCase):
    """The pure half of the post-execution proof (design D3)."""

    def apply(self, before: Dict[str, List[int]], action: str, track: int,
              after: Dict[str, List[int]]) -> Optional[str]:
        return research_envelope.expected_state(before, action, track, after)

    def test_a_correct_post_state_has_no_divergence(self) -> None:
        before = dict(research_envelope.COMMITTED_VECTOR)
        after = {
            "researchStepNumber": [1, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [1700000000, 0],
        }
        self.assertIsNone(self.apply(before, "next_step", 0, after))
        # An unstamped shape is also accepted: the instant is compared by SHAPE.
        after["timeStampDoResearch"] = [0, 0]
        self.assertIsNone(self.apply(before, "next_step", 0, after))

    def test_every_divergence_is_named(self) -> None:
        before = dict(research_envelope.COMMITTED_VECTOR)
        # Wrong step value.
        after = {
            "researchStepNumber": [5, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [0, 0],
        }
        message = self.apply(before, "next_step", 0, after)
        self.assertIsNotNone(message)
        self.assertIn("step counter", message)
        # The unaddressed track moved.
        after = {
            "researchStepNumber": [1, 3],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [0, 0],
        }
        message = self.apply(before, "next_step", 0, after)
        self.assertIsNotNone(message)
        self.assertIn("UNADDRESSED track", message)
        # An untouched counter of the addressed track moved.
        after = {
            "researchStepNumber": [1, 0],
            "researchItemNumber": [4, 0],
            "timeStampDoResearch": [0, 0],
        }
        message = self.apply(before, "next_step", 0, after)
        self.assertIsNotNone(message)
        self.assertIn("never writes", message)
        # The instant moved BACKWARDS on a stamping branch.
        before_stamped = {
            "researchStepNumber": [1, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [1700000000, 0],
        }
        after_backwards = {
            "researchStepNumber": [2, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [1600000000, 0],
        }
        message = self.apply(before_stamped, "next_step", 0, after_backwards)
        self.assertIsNotNone(message)
        self.assertIn("backwards", message)
        # A non-integer stamp on a stamping branch.
        after_shape = {
            "researchStepNumber": [2, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": ["1700000000", 0],
        }
        message = self.apply(before_stamped, "next_step", 0, after_shape)
        self.assertIsNotNone(message)
        self.assertIn("not an integer", message)
        # A missing counter entirely.
        after_missing = {
            "researchStepNumber": [2, 0],
            "researchItemNumber": [0, 0],
        }
        message = self.apply(before_stamped, "next_step", 0, after_missing)
        self.assertIsNotNone(message)
        self.assertIn("not a 2-entry vector", message)

    def test_a_zeroed_instant_is_required_by_the_cash_branch(self) -> None:
        before = {
            "researchStepNumber": [0, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [1700000000, 1700000001],
        }
        # The addressed track's instant survived: the cash branch must zero it.
        survived = {
            "researchStepNumber": [0, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [1700000000, 1700000001],
        }
        message = self.apply(before, "buy_step_cash", 1, survived)
        self.assertIsNotNone(message)
        self.assertIn("research instant", message)
        self.assertIn("1700000001", message)
        # The derived zeroing itself is accepted.
        zeroed = {
            "researchStepNumber": [0, 0],
            "researchItemNumber": [0, 0],
            "timeStampDoResearch": [1700000000, 0],
        }
        self.assertIsNone(self.apply(before, "buy_step_cash", 1, zeroed))


class EnvelopeTests(unittest.TestCase):
    """The derived legacy batch envelope (design D2/D3)."""

    def test_each_action_carries_exactly_one_command_with_a_neutral_vector(self) -> None:
        for action in research_envelope.ACTIONS:
            for track in (0, 1):
                with self.subTest(action=action, track=track):
                    envelope = research_envelope.build_envelope(
                        track=track, action=action, ts=1700000000
                    )
                    self.assertEqual(
                        sorted(envelope), sorted(research_envelope.ENVELOPE_KEYS)
                    )
                    self.assertEqual(len(envelope["commands"]), 1)
                    entry = envelope["commands"][0]
                    self.assertEqual(entry[0], 0)
                    self.assertEqual(entry[1], research_envelope.ACTION_COMMANDS[action])
                    self.assertEqual(
                        entry[3], [0] * research_envelope.RESOURCE_VECTOR_SLOTS
                    )
                    self.assertEqual(entry[3], research_envelope.neutral_vector())

    def test_the_cash_branch_takes_cash_then_track_and_the_others_only_track(self) -> None:
        cash = research_envelope.build_envelope(
            track=1, action=research_envelope.ACTION_BUY_STEP_CASH, ts=1700000000
        )
        self.assertEqual(cash["commands"][0][2], [0, 1])
        self.assertEqual(cash["commands"][0][2][0],
                         research_envelope.DERIVED_CASH)
        for action in ("next_step", "next_item", "reset_item"):
            with self.subTest(action=action):
                envelope = research_envelope.build_envelope(
                    track=0, action=action, ts=1700000000
                )
                self.assertEqual(envelope["commands"][0][2], [0])

    def test_the_derived_cash_is_zero_and_never_client_supplied(self) -> None:
        self.assertEqual(research_envelope.DERIVED_CASH, 0)
        # The module accepts no cash parameter at all, so there is no channel
        # through which a client price could reach the envelope.
        parameters = module_function_parameters("build_envelope")
        self.assertEqual(parameters, ["track", "action", "ts"])
        self.assertNotIn("cash", parameters)

    def test_a_structurally_invalid_request_is_refused(self) -> None:
        for track in [2, -1, "0", None, 1.0, True]:
            with self.subTest(track=track):
                with self.assertRaises(research_envelope.EnvelopeError) as caught:
                    research_envelope.build_envelope(track=track, action="next_step")
                self.assertEqual(caught.exception.code, "invalid_track")
        with self.assertRaises(research_envelope.EnvelopeError) as caught:
            research_envelope.build_envelope(track=0, action="fast_forward")
        self.assertEqual(caught.exception.code, "invalid_action")
        with self.assertRaises(research_envelope.EnvelopeError) as caught:
            research_envelope.build_envelope(track=0, action="next_step", ts=-1)
        self.assertEqual(caught.exception.code, "invalid_timestamp")

    def test_only_the_neutral_vector_is_derivable(self) -> None:
        self.assertEqual(research_envelope.neutral_vector(),
                         [0] * research_envelope.RESOURCE_VECTOR_SLOTS)
        self.assertEqual(research_envelope.RESOURCE_VECTOR_SLOTS, 8)
        for bad in ([0] * 7, [1] + [0] * 7, [0] * 6 + [2500, 0],
                    [0] * 6 + [-5, 0], "00000000", None, [0] * 7 + ["0"]):
            with self.subTest(vector=bad):
                with self.assertRaises(research_envelope.EnvelopeError) as caught:
                    research_envelope.validate_vector(bad)
                self.assertEqual(caught.exception.code, "invalid_vector")
        self.assertEqual(
            research_envelope.validate_vector([0] * 8), [0] * 8
        )

    def test_neutral_vector_hands_out_a_fresh_list_every_call(self) -> None:
        first = research_envelope.neutral_vector()
        first[0] = 99
        self.assertEqual(research_envelope.neutral_vector()[0], 0)

    def test_the_data_field_round_trips_through_the_shared_serializer(self) -> None:
        envelope = research_envelope.build_envelope(track=0, action="next_item")
        data = research_envelope.data_field(envelope)
        self.assertEqual(data[64], ";")
        self.assertEqual(research_envelope.parse_data_field(data), envelope)


class RefusalFamilyTests(unittest.TestCase):
    """The four refusal families, each with a non-empty reason (task 4.1)."""

    def test_all_four_families_are_recorded_and_none_is_implemented(self) -> None:
        names = sorted(record["refusal"] for record in research_envelope.REFUSALS)
        self.assertEqual(names, ["no_bounds", "no_price", "no_readiness", "no_reward"])
        for record in research_envelope.REFUSALS:
            with self.subTest(refusal=record["refusal"]):
                self.assertFalse(record["implemented"])
                self.assertNotEqual(record["reason"].strip(), "")
                self.assertGreater(len(record["reason"]), 200)

    def test_the_price_family_names_the_discarded_cash_and_the_neutral_vector(self) -> None:
        for phrase in ("research_buy_step_cash", "discards", "NEUTRAL",
                       "command.py:40", "every action"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, research_envelope.NO_PRICE)

    def test_the_readiness_family_names_the_write_only_property(self) -> None:
        for phrase in ("WRITE-ONLY", "command.py:923", "fast_forward",
                       "no server-side completion"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, research_envelope.NO_READINESS)

    def test_the_bounds_family_states_that_none_is_invented(self) -> None:
        for phrase in ("NO COUNTER BOUND", "IndexError", "Server v1 / M13",
                       "NOT permission"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, research_envelope.NO_BOUNDS)

    def test_the_reward_family_states_that_none_exists(self) -> None:
        for phrase in ("NO REWARD IS PAID", "not even a zero-valued one",
                       "no consumer"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, research_envelope.NO_REWARD)

    def test_the_two_structural_refusals_are_the_only_ones_reachable(self) -> None:
        self.assertEqual(
            sorted(research_envelope.STRUCTURAL_REFUSALS),
            ["invalid_track", "unresolvable_research_state"],
        )


class ContentAbsenceTests(unittest.TestCase):
    """The measured content findings, including two CORRECTED figures (task 4.2)."""

    def normalized_files(self) -> List[Path]:
        return sorted((REPO / "packages" / "game-content" / "normalized").glob("*.json"))

    def test_no_normalized_package_carries_a_research_section(self) -> None:
        files = self.normalized_files()
        self.assertEqual(len(files), 23)
        for path in files:
            with self.subTest(path=path.name):
                document = json.loads(path.read_text(encoding="utf-8"))
                # Every normalized output is a top-level ARRAY of domain rows, so
                # there is no key of any kind to be a research section.
                self.assertIsInstance(document, list)
                for row in document:
                    if isinstance(row, dict):
                        self.assertFalse(
                            any("research" == str(key).lower() for key in row),
                            "%s carries a research key" % path.name,
                        )

    def test_research_appears_in_TWO_normalized_files_not_one(self) -> None:
        """MEASURED CORRECTION of the M9 investigation and this line's proposal.

        Both state ``research`` appears in exactly ONE normalized file and only
        inside one ``name``.  It appears in TWO: ``buildings.json`` once and
        ``images.json`` three times over.
        """
        counts: Dict[str, int] = {}
        for path in self.normalized_files():
            found = path.read_text(encoding="utf-8").lower().count("research")
            if found:
                counts[path.name] = found
        self.assertEqual(counts, {"buildings.json": 1, "images.json": 6})
        self.assertEqual(len(counts), 2)

    def test_the_buildings_occurrence_is_the_research_lab_name(self) -> None:
        buildings = json.loads(
            (REPO / "packages" / "game-content" / "normalized" / "buildings.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(len(buildings), 470)
        matched = [
            row for row in buildings
            if isinstance(row, dict) and "research" in json.dumps(row).lower()
        ]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["legacy_id"], "256")
        self.assertEqual(matched[0]["name"], "Research Lab")
        # legacy_id is the STRING "256" here, not the integer 256.
        self.assertIsInstance(matched[0]["legacy_id"], str)

    def test_the_images_occurrences_are_three_popup_asset_rows(self) -> None:
        images = json.loads(
            (REPO / "packages" / "game-content" / "normalized" / "images.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(len(images), 607)
        matched = [
            row for row in images
            if isinstance(row, dict) and "research" in json.dumps(row).lower()
        ]
        self.assertEqual(len(matched), 3)
        self.assertEqual(
            sorted(row["legacy_id"] for row in matched),
            [
                "popupResearchCenter_buildingProcess.swf",
                "popupResearchCenter_buildingProcess_2.swf",
                "popupResearchCenter_buildingProcess_3.swf",
            ],
        )
        for row in matched:
            with self.subTest(asset=row["legacy_id"]):
                self.assertEqual(row["path"], row["legacy_id"])
                self.assertEqual(row["locale"], "en")

    def test_config_has_no_research_section_but_three_research_image_keys(self) -> None:
        """MEASURED CORRECTION: ``config/main.json`` DOES have research keys.

        The investigation and the proposal both state it has **no** key
        containing ``research`` at any depth.  It has three, all under
        ``/images``, plus one string value (``/items/244/name``).
        """
        document = json.loads(
            (REPO / "config" / "main.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(document), 20)
        keys: List[str] = []

        def walk(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for key in node:
                    child = "%s/%s" % (path, key)
                    if "research" in str(key).lower():
                        keys.append(child)
                    walk(node[key], child)
            elif isinstance(node, list):
                for index, item in enumerate(node):
                    walk(item, "%s/%d" % (path, index))

        walk(document, "")
        self.assertEqual(
            sorted(keys),
            [
                "/images/popupResearchCenter_buildingProcess.swf",
                "/images/popupResearchCenter_buildingProcess_2.swf",
                "/images/popupResearchCenter_buildingProcess_3.swf",
            ],
        )
        # None of the twenty top-level content keys names research.
        for key in document:
            with self.subTest(key=key):
                self.assertNotIn("research", str(key).lower())
        # Exactly one string VALUE contains it, and it is the building's name.
        values: List[str] = []

        def walk_values(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for key in node:
                    walk_values(node[key], "%s/%s" % (path, key))
            elif isinstance(node, list):
                for index, item in enumerate(node):
                    walk_values(item, "%s/%d" % (path, index))
            elif isinstance(node, str) and "research" in node.lower():
                values.append(path)

        walk_values(document, "")
        self.assertEqual(values, ["/items/244/name"])

    def test_no_committed_cost_step_unlock_or_reward_field_exists(self) -> None:
        """The conclusion the corrections leave untouched: there is nothing to use."""
        for token in ("research_price", "research_cost", "research_step",
                      "research_unlock", "research_reward",
                      "researchSteps", "researchRequirements"):
            with self.subTest(token=token):
                for path in self.normalized_files():
                    self.assertNotIn(token, path.read_text(encoding="utf-8"))
                self.assertNotIn(token, (REPO / "config" / "main.json")
                                 .read_text(encoding="utf-8"))

    def test_the_recorded_content_absence_states_both_corrections(self) -> None:
        for phrase in ("TWO normalized files", "images.json", "MEASURED CORRECTION",
                       "THREE keys containing the word", "/items/244/name",
                       "no committed research cost, step"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, research_envelope.CONTENT_ABSENCE)
        self.assertEqual(len(research_envelope.COMMITTED_CONTENT_FACTS), 3)
        facts = {record["fact"] for record in research_envelope.COMMITTED_CONTENT_FACTS}
        self.assertEqual(facts, {"the research-lab building",
                                 "the research-center process popups",
                                 "the two track building identifiers"})

    def test_the_committed_facts_are_reported_and_never_used_as_rules(self) -> None:
        for record in research_envelope.COMMITTED_CONTENT_FACTS:
            with self.subTest(fact=record["fact"]):
                self.assertTrue(
                    "never used" in record["used_as"]
                    or "no gameplay semantics are claimed" in record["used_as"],
                    record["used_as"],
                )


class LedgerDoorTests(unittest.TestCase):
    """Task 5.1/5.2: the dead-hero ledger has FOUR doors, not three."""

    def test_map_lose_item_is_a_fourth_door_and_calls_push_dead_unit(self) -> None:
        lines = legacy_text("engine.py").split("\n")
        self.assertEqual(lines[214].strip(),
                         "def map_lose_item(map: dict, privateState: dict, item: int, "
                         "quantity: int):")
        self.assertIn("push_dead_unit(privateState, _item)", lines[222])
        # It is an ENGINE HELPER, not a dispatcher branch.
        command_lines = legacy_text("command.py").split("\n")
        self.assertFalse(
            any('cmd == "map_lose_item"' in line for line in command_lines)
        )
        self.assertIn("map_lose_item", command_lines[5])  # imported by command.py
        calls = [
            index for index, line in enumerate(command_lines, 1)
            if "map_lose_item(" in line and "import" not in line
        ]
        # Reached from the QUEST path (end_quest) and the ATTACK path (end_attack).
        self.assertEqual(calls, [796, 872])
        self.assertLess(calls[0], 807)

    def test_push_dead_unit_has_exactly_two_call_sites_in_the_legacy_tree(self) -> None:
        """One from ``sell`` (command.py) and one from ``map_lose_item``
        (engine.py) — the two sites that make the door count FOUR when the
        dispatcher branches are counted alongside the engine helpers."""
        command_lines = legacy_text("command.py").split("\n")
        calls = [
            index for index, line in enumerate(command_lines, 1)
            if "push_dead_unit(" in line and "import" not in line
        ]
        self.assertEqual(calls, [160])
        engine_lines = legacy_text("engine.py").split("\n")
        helper_calls = [
            index for index, line in enumerate(engine_lines, 1)
            if "push_dead_unit(" in line and not line.strip().startswith("def ")
        ]
        self.assertEqual(helper_calls, [223])
        self.assertEqual(len(calls) + len(helper_calls), 2)
        # …and `kill` reaches neither: it deletes the row and never touches the
        # ledger, which is what keeps the death path distinct from the quest path.
        kill_block = "\n".join(command_lines[168:181])
        self.assertNotIn("push_dead_unit", kill_block)
        self.assertIn("map_delete_item", kill_block)


def module_function_parameters(name: str) -> List[str]:
    tree = ast.parse(module_source())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return [argument.arg for argument in node.args.args]
    raise AssertionError("no function named %r" % name)


def module_code_identifiers() -> List[str]:
    """Every identifier the module's CODE declares or binds.

    Docstrings, comments, and every string literal are excluded by parsing
    rather than by scanning, so a recorded refusal sentence that happens to use
    the word "ready" can never be mistaken for behaviour.
    """
    names: List[str] = []
    for node in ast.walk(ast.parse(module_source())):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.append(node.id)
        elif isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            names.append(node.arg)
    return sorted(set(names))


class AntiInventionGuardTests(unittest.TestCase):
    """Task 4.3: the whole function inventory, compared against a pinned list."""

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
                    re.search(r"^\s*def\s+%s\s*\(" % re.escape(name), code,
                              re.MULTILINE),
                    "research_envelope declares %s" % name,
                )

    def test_no_code_identifier_mentions_a_cost_a_readiness_or_an_unlock(self) -> None:
        """The structural half of task 4.3's guard, over parsed code only."""
        identifiers = module_code_identifiers()
        for token in ("ready", "complete", "remaining", "progress", "price",
                      "cost", "unlock", "duration", "elapsed", "reward",
                      "fast_forward_seconds"):
            with self.subTest(token=token):
                offenders = [
                    name for name in identifiers
                    if token in name.lower() and name.lower() != token
                ]
                # `NO_PRICE`/`NO_READINESS`/`NO_REWARD`/`DERIVED_CASH` are the
                # RECORDED absences and their refusal codes, so they are the one
                # documented exemption.
                self.assertEqual(
                    [name for name in offenders
                     if not name.startswith("NO_")
                     and name not in ("DERIVED_CASH", "REASON_INVALID_CASH",
                                      "REASON_MISSING_TRACK")],
                    [],
                    "research_envelope names an identifier carrying %r" % token,
                )

    def test_the_module_computes_no_derived_research_value(self) -> None:
        """No function's body calls a numeric/time helper that could turn a
        counter into a duration, a ratio, or a completion, so the "nothing is
        derived from the counters" claim is mechanical rather than prose.

        ``int`` / ``float`` / ``str`` / ``max`` / ``min`` are deliberately NOT in
        the banned set: this module uses them for **structural** validation and
        fail-closed coercion, never to compute a quantity from a counter.
        """
        tree = ast.parse(module_source())
        banned_calls = {"time", "pow", "sqrt", "exp", "log", "log2", "log10",
                        "round", "trunc", "hypot", "atan2", "fmod"}
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                    self.assertNotIn(
                        inner.func.id, banned_calls,
                        "%s calls %s(), which could derive a value from a "
                        "counter" % (node.name, inner.func.id),
                    )


if __name__ == "__main__":
    unittest.main()
