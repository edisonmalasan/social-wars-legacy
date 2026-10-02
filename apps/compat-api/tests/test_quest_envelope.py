#!/usr/bin/env python3
"""Offline envelope/derivation tests for the M9 quest line (``quest_envelope``).

No server, no socket, no corpus: this module is pure.  Every figure the quest
contract records is **re-measured here** out of the committed legacy source, the
committed content package, and the committed corpus save, and a discrepancy fails
the run instead of publishing a different contract.

Covered:

* the **closed six-action vocabulary** and each action's legacy command, and that
  ``fast_forward`` is absent from it by decision D9;
* the **six-branch inventory** — each branch's recorded source line range,
  arguments, reads, writes, and whether it mutates anything — including that
  ``complete_goal`` **writes nothing at all**, that ``set_goals`` grows the goals
  list on demand with **no upper bound**, that ``set_quest_var`` accepts **any**
  key, that ``collect_mission`` writes a **stringified** identifier and **wraps**
  above 99, and that ``admin_set_quest_rank`` writes a client-sent pair with no
  bound;
* the **committed-content inventory**, with every consumer count **measured** as
  QUOTED occurrences across the seven legacy modules, so the claim that only
  ``id`` and ``title`` are read — and that ``reward`` has **zero** and is
  **uniformly 10** — is a measurement rather than a restatement;
* the **writer inventory** — six branches plus ``fast_forward``, its two write
  sites, and its client-supplied seconds — and the **save migration** recorded as
  a migration rather than as quest behaviour;
* the **state resolution** fail-closed paths, and that a recorded ``None``
  ``currentQuestVars`` resolves as a recorded null rather than as an empty map;
* the **read-only projection** and its explicitly **empty** ``derived`` block;
* the **derived effect** of each action and the **post-execution comparison**,
  including the unbounded growth, the wrap, the refused ignored key, and the
  no-op branch's whole-state identity;
* the **anti-invention guard**: the module's whole function inventory is compared
  against a pinned list, so a ``quest_reward`` / ``quest_remaining_time`` /
  ``quest_progress_ratio`` / ``mark_goal_complete`` / ``is_goal_complete`` helper
  fails the run wherever it is added, and **no delivered code identifier or
  computation is named after the committed reward field**;
* the **dead-hero ledger door**: ``end_quest`` is one of ``map_lose_item``'s only
  two callers, and the quest path's reach is **refused** here (design D10).
"""

from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import quest_envelope as envelope

REPO_ROOT = harness.REPO_ROOT
LEGACY_MODULES = (
    "command.py",
    "engine.py",
    "sessions.py",
    "server.py",
    "constants.py",
    "get_game_config.py",
    "version.py",
)
QUESTS_JSON = REPO_ROOT / "packages" / "game-content" / "normalized" / "quests.json"
CORPUS_SAVE = harness.SEED_SAVE


def legacy_text(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def quoted_occurrences(field: str) -> Dict[str, int]:
    """Quoted occurrences of ``field``, per module and in total.

    Counted as QUOTED so a comment or a recorded non-claim can never be
    mistaken for code.
    """
    per: Dict[str, int] = {}
    total = 0
    pattern = re.compile(r'"%s"' % re.escape(field))
    for name in LEGACY_MODULES:
        count = len(pattern.findall(legacy_text(name)))
        if count:
            per[name] = count
        total += count
    per["total"] = total
    return per


def distinct_lines(field: str) -> int:
    """Distinct source LINES carrying a quoted ``field``.

    Separate from :func:`quoted_occurrences`, because ``command.py:911`` reads and
    writes ``timestampLastChapter`` in one expression — two occurrences on one
    line — and the investigation recorded the line count.
    """
    pattern = re.compile(r'"%s"' % re.escape(field))
    total = 0
    for name in LEGACY_MODULES:
        total += sum(1 for line in legacy_text(name).split("\n") if pattern.search(line))
    return total


def branch_lines() -> Dict[str, List[int]]:
    """The inclusive line range of every quest branch, from ``command.py``.

    The end is measured as the last **non-blank** line before the next dispatcher
    branch, so a trailing separator line never inflates a recorded range.
    """
    lines = legacy_text("command.py").split("\n")
    found: Dict[str, List[int]] = {}
    for index, line in enumerate(lines, 1):
        match = re.search(r'cmd == "([a-z_]+)"', line)
        if not match:
            continue
        name = match.group(1)
        if name not in envelope.QUEST_COMMANDS:
            continue
        # The range runs to the line before the NEXT dispatcher branch, which is
        # measured rather than assumed.
        end = len(lines)
        for later in range(index, len(lines)):
            if re.search(r'(?:el)?if cmd == "', lines[later]):
                end = later
                break
        while end > index and lines[end - 1].strip() == "":
            end -= 1
        found[name] = [index, end]
    return found


def code_names(module: Path) -> List[str]:
    """Every executable name the module binds, from its AST.

    Docstrings and comments are dropped by construction, so a prose mention of a
    refused rule can never be mistaken for behaviour.
    """
    names: List[str] = []
    tree = ast.parse(module.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.FunctionDef):
            names.append(node.name)
    return names


def declared_functions() -> List[str]:
    tree = ast.parse(Path(envelope.__file__).read_text(encoding="utf-8"))
    return sorted(
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    )


class VocabularyTests(unittest.TestCase):
    """The closed action vocabulary."""

    def test_the_vocabulary_is_closed_and_holds_exactly_six_actions(self) -> None:
        self.assertEqual(len(envelope.ACTIONS), 6)
        self.assertEqual(len(envelope.QUEST_COMMANDS), 6)
        self.assertEqual(envelope.BRANCH_COUNT, 6)
        self.assertEqual(len(envelope.BRANCHES), 6)
        self.assertEqual(
            sorted(envelope.ACTIONS),
            sorted(envelope.ACTION_COMMANDS.keys()),
        )

    def test_each_action_derives_its_committed_command(self) -> None:
        measured = branch_lines()
        self.assertEqual(sorted(measured), sorted(envelope.QUEST_COMMANDS))
        for action in envelope.ACTIONS:
            command = envelope.command_for_action(action)
            self.assertEqual(envelope.ACTION_COMMANDS[action], command)
            self.assertIn(command, measured)

    def test_unknown_actions_are_refused_before_the_dispatcher(self) -> None:
        for value in (None, 7, "", "SET_GOAL", "complete_goal ", "end_quests"):
            self.assertFalse(envelope.is_action(value))
            with self.assertRaises(envelope.EnvelopeError) as caught:
                envelope.command_for_action(value)
            self.assertEqual(caught.exception.code, "invalid_action")

    def test_fast_forward_is_absent_from_the_vocabulary_by_decision(self) -> None:
        self.assertFalse(envelope.is_action(envelope.FAST_FORWARD_COMMAND))
        self.assertNotIn(envelope.FAST_FORWARD_COMMAND, envelope.QUEST_COMMANDS)
        self.assertIn("IMPLEMENTED NOT AT ALL", envelope.FAST_FORWARD_CONTRACT)


class BranchInventoryTests(unittest.TestCase):
    """The six recorded branch contracts, measured against the source."""

    def test_the_six_branch_line_ranges_are_the_recorded_ones(self) -> None:
        measured = branch_lines()
        for record in envelope.BRANCHES:
            self.assertIn(record["command"], measured)
            self.assertEqual(
                measured[record["command"]], _expected_range(record["command"]),
                "%s line range drifted" % record["command"],
            )

    def test_the_dispatcher_has_no_seventh_quest_branch(self) -> None:
        lines = legacy_text("command.py").split("\n")
        quest_ish = sorted({
            match.group(1)
            for line in lines
            for match in [re.search(r'cmd == "([a-z_]+)"', line)]
            if match and any(token in match.group(1)
                             for token in ("goal", "quest", "mission", "chapter"))
        })
        self.assertEqual(quest_ish, sorted(envelope.QUEST_COMMANDS))

    def test_complete_goal_writes_nothing_at_all(self) -> None:
        record = _record(envelope.COMPLETE_GOAL_COMMAND)
        self.assertFalse(record["mutates"])
        self.assertEqual(record["writes"], [])
        self.assertIsNone(record["delegates_to"])
        self.assertEqual(envelope.NO_OP_COMMAND, envelope.COMPLETE_GOAL_COMMAND)
        lines = legacy_text("command.py").split("\n")
        block = "\n".join(lines[75:80])
        self.assertIn('get_attribute_from_goal_id(goal_id, "title")', block)
        self.assertIn("print(", block)
        for forbidden in ("map[", "privateState[", "save[", "engine."):
            self.assertNotIn(forbidden, block)

    def test_set_goals_grows_the_list_on_demand_with_no_upper_bound(self) -> None:
        record = _record(envelope.SET_GOALS_COMMAND)
        self.assertTrue(record["mutates"])
        self.assertTrue(record["grows_list_on_demand"])
        self.assertIsNone(record["upper_bound"])
        engine = legacy_text("engine.py").split("\n")
        helper = "\n".join(engine[95:100])
        self.assertIn("while goal >= len(goals):", helper)
        self.assertIn("goals.append(None)", helper)
        self.assertIn("goals[goal] = progress", helper)
        # The executed capture grew the list to 501 entries — appending exactly
        # 350 `None` entries from ONE client-sent index of 500.
        self.assertEqual(501 - envelope.COMMITTED_GOALS_LENGTH, 350)
        state = envelope.snapshot_state(
            json.loads(CORPUS_SAVE.read_text(encoding="utf-8"))
        )
        self.assertEqual(
            len(envelope.derived_quest(state, envelope.ACTION_SET_GOAL, 500)
                ["derived_state"][envelope.KEY_GOALS]),
            501,
        )

    def test_set_quest_var_writes_any_key_and_the_branch_ignores_one(self) -> None:
        record = _record(envelope.SET_QUEST_VAR_COMMAND)
        self.assertIn("currentQuestVars", " ".join(record["writes"]))
        lines = legacy_text("command.py").split("\n")
        block = "\n".join(lines[86:117])
        self.assertIn('if key == "%s"' % envelope.QUEST_VAR_IGNORED_KEY, block)
        self.assertIn("return", block)
        self.assertIn('if key == "%s"' % envelope.QUEST_VAR_ALIAS_KEY, block)
        self.assertIn('map["idCurrentMission"] = value', block)
        self.assertIn('map["currentQuestVars"][key] = value', block)
        # No membership test against the eight enumerated keys.  `id` is the one
        # key that legitimately appears, as the ALIAS (command.py:110-111), so
        # it is excluded here and asserted separately above.
        for key in envelope.QUEST_VAR_COMMENT_KEYS:
            if key == envelope.QUEST_VAR_ALIAS_KEY:
                continue
            self.assertNotIn('key == "%s"' % key, block)
        self.assertEqual(len(envelope.QUEST_VAR_COMMENT_KEYS), 8)

    def test_collect_mission_stringifies_wraps_and_clears(self) -> None:
        record = _record(envelope.COLLECT_MISSION_COMMAND)
        lines = legacy_text("command.py").split("\n")
        block = "\n".join(lines[429:442])
        self.assertIn("if next_mission > 99:", block)
        self.assertIn("next_mission = 1", block)
        self.assertIn('map["idCurrentMission"] = str(next_mission)', block)
        self.assertIn('map["timestampLastChapter"] = time_now', block)
        self.assertIn('map["currentQuestVars"] = {}', block)
        self.assertNotIn("next_mission = None", block)
        self.assertNotIn("raise", block)
        self.assertEqual(envelope.MISSION_WRAP_BOUND, 99)
        self.assertEqual(envelope.MISSION_WRAP_TARGET, 1)
        self.assertEqual(envelope.wrap_mission(150), 1)
        self.assertEqual(envelope.wrap_mission(99), 99)
        self.assertEqual(envelope.wrap_mission(1), 1)

    def test_admin_set_quest_rank_writes_a_client_pair_with_no_bound(self) -> None:
        record = _record(envelope.ADMIN_SET_QUEST_RANK_COMMAND)
        lines = legacy_text("command.py").split("\n")
        block = "\n".join(lines[744:750])
        self.assertIn('privateState["questsRank"][str(quest_index)] = difficulty',
                      block)
        # No bound, clamp, exception guard, or existence check.  `" if "` is used
        # rather than `"if "` so the branch's own `elif` header cannot satisfy
        # the needle.
        for forbidden in ("max(", "min(", "raise", " if ", "assert", "try:"):
            self.assertNotIn(forbidden, block)
        self.assertTrue(envelope.is_quest_rank_index(999999))
        self.assertTrue(envelope.is_quest_rank_index(-5))

    def test_end_quest_is_refused_and_its_clamp_is_recorded(self) -> None:
        record = _record(envelope.END_QUEST_COMMAND)
        self.assertEqual(record["destruction"], "REFUSED")
        self.assertTrue(record["only_clamped_value"])
        self.assertEqual(record["difficulty_clamp"],
                         "max(1, min(3, ...)) at command.py:782")
        lines = legacy_text("command.py").split("\n")
        block = "\n".join(lines[751:807])
        self.assertIn("lost = max(0, unit[2] - unit[3])", block)
        self.assertIn("map_lose_item(map, privateState, unit[0], lost)", block)
        self.assertIn('map["questTimes"][str(quest_id)] = time_now', block)
        self.assertEqual(envelope.clamp_difficulty(0), 1)
        self.assertEqual(envelope.clamp_difficulty(9), 3)
        self.assertEqual(envelope.clamp_difficulty(2), 2)
        with self.assertRaises(envelope.EnvelopeError):
            envelope.clamp_difficulty("2")

    def test_every_branch_records_the_absence_of_validation(self) -> None:
        for record in envelope.BRANCHES:
            self.assertIsInstance(record["validation"], str)
            self.assertNotEqual(record["validation"].strip(), "")
            self.assertIsInstance(record["reads"], list)
            self.assertIsInstance(record["writes"], list)
            self.assertIsInstance(record["mutates"], bool)
            self.assertFalse(record["charges"])
            self.assertFalse(record["reads_a_price"])


def _record(command: str) -> Dict[str, Any]:
    for record in envelope.BRANCHES:
        if record["command"] == command:
            return record
    raise AssertionError("no recorded branch for %r" % command)


def _expected_range(command: str) -> List[int]:
    return {
        envelope.SET_GOALS_COMMAND: [68, 74],
        envelope.COMPLETE_GOAL_COMMAND: [76, 79],
        envelope.SET_QUEST_VAR_COMMAND: [87, 117],
        envelope.COLLECT_MISSION_COMMAND: [430, 442],
        envelope.ADMIN_SET_QUEST_RANK_COMMAND: [745, 750],
        envelope.END_QUEST_COMMAND: [752, 806],
    }[command]


class ContentInventoryTests(unittest.TestCase):
    """Task 2.4: the committed-content inventory, measured."""

    def test_the_committed_quest_content_has_91_uniform_entries(self) -> None:
        rows = json.loads(QUESTS_JSON.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), envelope.COMMITTED_QUEST_ENTRIES)
        self.assertEqual({row["kind"] for row in rows}, {"quest"})
        shapes = {tuple(sorted(row.keys())) for row in rows}
        self.assertEqual(len(shapes), 1)
        self.assertEqual(
            sorted(next(iter(shapes))), sorted(
                record["field"] for record in envelope.COMMITTED_FIELD_CONSUMERS
            ),
        )
        ids = sorted(row["id"] for row in rows)
        self.assertEqual(ids[0], envelope.COMMITTED_ID_MIN)
        self.assertEqual(ids[-1], envelope.COMMITTED_ID_MAX)
        self.assertEqual(len(set(ids)), len(ids))

    def test_the_reward_field_is_uniform_and_has_zero_legacy_consumers(self) -> None:
        rows = json.loads(QUESTS_JSON.read_text(encoding="utf-8"))
        rewards = {row["reward"] for row in rows}
        self.assertEqual(rewards, {envelope.COMMITTED_REWARD_VALUE})
        measured = quoted_occurrences("reward")
        self.assertEqual(measured["total"], 0, measured)
        for name in LEGACY_MODULES:
            self.assertNotIn(name, measured)

    def test_only_the_identifier_and_the_title_have_consumers(self) -> None:
        for record in envelope.COMMITTED_FIELD_CONSUMERS:
            measured = quoted_occurrences(record["field"])
            self.assertEqual(
                measured["total"], record["quoted_occurrences"],
                "%s consumer count drifted: %r" % (record["field"], measured),
            )
            expected_modules = sorted(record["where"])
            self.assertEqual(
                sorted(name for name in measured if name != "total"),
                expected_modules,
                "%s is read from %r, not %r"
                % (record["field"], measured, expected_modules),
            )
        read = sorted(record["field"] for record in envelope.COMMITTED_FIELD_CONSUMERS
                      if record["quoted_occurrences"] > 0)
        self.assertEqual(read, sorted(envelope.COMMITTED_FIELDS_READ))
        unread = sorted(record["field"] for record in envelope.COMMITTED_FIELD_CONSUMERS
                        if record["quoted_occurrences"] == 0)
        self.assertEqual(unread, sorted(envelope.COMMITTED_FIELDS_UNREAD))
        self.assertEqual(len(envelope.COMMITTED_FIELDS_UNREAD), 8)
        self.assertIn("reward", envelope.COMMITTED_FIELDS_UNREAD)

    def test_the_measured_hint_and_description_facts(self) -> None:
        rows = json.loads(QUESTS_JSON.read_text(encoding="utf-8"))
        empty_hints = sum(1 for row in rows if not row["hint"])
        self.assertEqual(empty_hints, len(rows))
        self.assertTrue(all(row["description"] for row in rows))

    def test_the_goal_index_source_is_measured_and_fail_closed(self) -> None:
        lines = legacy_text("get_game_config.py").split("\n")
        block = "\n".join(lines[141:150])
        self.assertIn('goals_id_to_goals_index = {int(item["id"])', block)
        self.assertIn("def get_goal_from_id", block)
        self.assertIn("def get_attribute_from_goal_id", block)
        self.assertIn("else None", block)
        self.assertIn("if int(id) in goals_id_to_goals_index else None", block)

    def test_no_code_identifier_is_named_after_the_reward_field(self) -> None:
        """Design D6 made mechanical: the claim is checkable, not editorial."""
        names = code_names(Path(envelope.__file__))
        for forbidden in ("quest_reward", "reward_for", "reward_amount",
                          "reward_paid_for", "goal_reward", "quest_payout"):
            self.assertNotIn(forbidden, names)
        # `reward_paid` IS delivered, but as a constant ZERO the response
        # reports — never as an amount derived from the committed field.
        self.assertEqual(envelope.REWARD_PAID, 0)

    def test_the_content_record_note_states_both_type_facts(self) -> None:
        self.assertIn("REPORTED AND NEVER USED", envelope.CONTENT_RECORD_NOTE)
        self.assertIn("hint", envelope.CONTENT_RECORD_NOTE)
        self.assertIn("display", envelope.CONTENT_RECORD_NOTE.lower())


class WriterInventoryTests(unittest.TestCase):
    """Seven writers of quest state, and one save migration."""

    def test_the_writer_inventory_holds_seven_entries(self) -> None:
        self.assertEqual(len(envelope.WRITERS), envelope.WRITER_COUNT)
        self.assertEqual(envelope.WRITER_COUNT, 7)
        commands = [
            entry["writer"].split(":", 1)[1] for entry in envelope.WRITERS
        ]
        branch_entries = [name for name in commands
                          if name != envelope.FAST_FORWARD_COMMAND]
        self.assertEqual(sorted(branch_entries),
                         sorted(envelope.QUEST_COMMANDS))
        self.assertEqual(len(branch_entries), 6)
        self.assertIn(envelope.FAST_FORWARD_COMMAND, commands)
        # The no-op branch is in the inventory too, so it is complete rather
        # than flattering.
        self.assertIn(envelope.COMPLETE_GOAL_COMMAND, commands)
        for entry in envelope.WRITERS:
            self.assertIn("fields_written", entry)
            self.assertIsInstance(entry["client_writable"], bool)
            self.assertIn("source", entry)

    def test_the_no_op_branch_is_recorded_as_writing_nothing(self) -> None:
        entry = _writer(envelope.COMPLETE_GOAL_COMMAND)
        self.assertEqual(entry["fields_written"], [])
        self.assertIn("NOTHING AT ALL", entry["note"])

    def test_fast_forward_is_the_seventh_writer_and_names_both_sites(self) -> None:
        entry = _writer(envelope.FAST_FORWARD_COMMAND)
        self.assertTrue(entry["client_writable"])
        self.assertIn("command.py:942-944", entry["source"])
        self.assertIn("command.py:911", entry["source"])
        self.assertEqual(sorted(entry["fields_written"]),
                         ["questTimes", "timestampLastChapter"])
        lines = legacy_text("command.py").split("\n")
        self.assertIn("seconds = args[0]", lines[905])
        self.assertIn("questTimes[key] = max(0, questTimes[key] - seconds)",
                      "\n".join(lines[940:944]))

    def test_the_quest_field_sites_are_measured_against_the_record(self) -> None:
        # Two counts are asserted SEPARATELY, because they differ: the
        # investigation recorded DISTINCT LINES, while this suite counts
        # OCCURRENCES.  They agree for six of the seven keys and disagree for
        # `timestampLastChapter`, whose fast-forward line reads and writes the
        # token TWICE (command.py:911).
        for key, occurrences, lines in (
            (envelope.KEY_GOALS, 3, 3),
            (envelope.KEY_RANKS, 1, 1),
            (envelope.KEY_UNLOCKED_INDEX, 0, 0),
            (envelope.KEY_QUEST_VARS, 5, 5),
            (envelope.KEY_QUEST_TIMES, 6, 6),
            (envelope.KEY_MISSION, 2, 2),
            (envelope.KEY_LAST_CHAPTER, 3, 2),
        ):
            measured = quoted_occurrences(key)["total"]
            self.assertEqual(
                measured, occurrences,
                "privateState/map key %r has %d quoted occurrences, not the "
                "recorded %d" % (key, measured, occurrences),
            )
            self.assertEqual(
                distinct_lines(key), lines,
                "privateState/map key %r has %d distinct lines, not the "
                "recorded %d" % (key, distinct_lines(key), lines),
            )

    def test_the_last_chapter_token_appears_twice_on_the_fast_forward_line(self) -> None:
        """MEASURED CORRECTION of the investigation's distinct-LINE count."""
        line = legacy_text("command.py").split("\n")[910]
        self.assertEqual(
            line.count('"%s"' % envelope.KEY_LAST_CHAPTER), 2,
            "command.py:911 is expected to read and write the token twice",
        )
        self.assertIn('map["%s"] = max(0, map["%s"] - seconds)'
                      % (envelope.KEY_LAST_CHAPTER, envelope.KEY_LAST_CHAPTER), line)

    def test_the_unlocked_quest_index_has_zero_legacy_sites(self) -> None:
        self.assertEqual(
            quoted_occurrences(envelope.KEY_UNLOCKED_INDEX)["total"], 0
        )
        record = envelope.ZERO_CONSUMER_FIELDS[0]
        self.assertEqual(record["quoted_sites"], 0)
        self.assertEqual(record["written_by"], [])
        self.assertEqual(record["read_by"], [])

    def test_the_migration_is_recorded_as_a_migration(self) -> None:
        migration = envelope.MIGRATION
        self.assertEqual(migration["field"], envelope.KEY_QUEST_TIMES)
        self.assertEqual(migration["where"], "version.py:38-44")
        self.assertFalse(migration["is_gameplay"])
        self.assertEqual(migration["kind"], "save-migration")
        lines = legacy_text("version.py").split("\n")
        block = "\n".join(lines[37:44])
        self.assertIn('if "questTimes" not in map', block)
        self.assertIn('map["questTimes"] = None', block)
        self.assertIn('map["questTimes"] = {}', block)


def _writer(command: str) -> Dict[str, Any]:
    for entry in envelope.WRITERS:
        if entry["writer"] == "command:" + command:
            return entry
    raise AssertionError("no recorded writer for %r" % command)


class StateResolutionTests(unittest.TestCase):
    """Fail-closed resolution, and the recorded ``None`` that must survive."""

    def setUp(self) -> None:
        self.save = json.loads(CORPUS_SAVE.read_text(encoding="utf-8"))
        self.state = envelope.snapshot_state(self.save)

    def test_the_committed_corpus_resolves_and_matches_the_pins(self) -> None:
        goals = self.state[envelope.KEY_GOALS]
        self.assertEqual(len(goals), envelope.COMMITTED_GOALS_LENGTH)
        self.assertTrue(all(entry is None for entry in goals))
        self.assertEqual(self.state[envelope.KEY_RANKS],
                         envelope.COMMITTED_RANKS)
        self.assertEqual(self.state[envelope.KEY_UNLOCKED_INDEX],
                         envelope.COMMITTED_UNLOCKED_INDEX)
        self.assertEqual(self.state[envelope.KEY_QUEST_TIMES],
                         envelope.COMMITTED_QUEST_TIMES)
        self.assertEqual(self.state[envelope.KEY_MISSION],
                         envelope.COMMITTED_MISSION)
        self.assertEqual(self.state[envelope.KEY_LAST_CHAPTER],
                         envelope.COMMITTED_LAST_CHAPTER)

    def test_a_null_quest_variable_field_is_reported_as_a_recorded_null(self) -> None:
        self.assertIsNone(self.state[envelope.KEY_QUEST_VARS])
        projection = envelope.project_quests(self.state)
        self.assertTrue(projection["current_quest_vars_is_null"])
        self.assertIsNone(projection["fields"][envelope.KEY_QUEST_VARS])
        self.assertNotEqual(projection["fields"][envelope.KEY_QUEST_VARS], {})

    def test_every_malformed_shape_is_refused_with_the_field_named(self) -> None:
        private = self.save["privateState"]
        first_map = self.save["maps"][0]
        without_private = {
            key: value for key, value in private.items()
            if key not in (envelope.KEY_GOALS, envelope.KEY_RANKS,
                           envelope.KEY_UNLOCKED_INDEX)
        }
        without_map = {
            key: value for key, value in first_map.items()
            if key not in envelope.MAP_KEYS
        }
        cases = [
            (None, first_map),
            ("nope", first_map),
            ([], first_map),
            (private, None),
            (private, "nope"),
            (private, []),
            (without_private, first_map),
            (dict(private, **{envelope.KEY_GOALS: {}}), first_map),
            (dict(private, **{envelope.KEY_RANKS: []}), first_map),
            (dict(private, **{envelope.KEY_UNLOCKED_INDEX: "0"}), first_map),
            (dict(private, **{envelope.KEY_UNLOCKED_INDEX: None}), first_map),
            (private, without_map),
            (private, dict(first_map, **{envelope.KEY_QUEST_VARS: []})),
            (private, dict(first_map, **{envelope.KEY_QUEST_TIMES: []})),
            (private, dict(first_map, **{envelope.KEY_MISSION: 1.5})),
            (private, dict(first_map, **{envelope.KEY_MISSION: None})),
            (private, dict(first_map, **{envelope.KEY_LAST_CHAPTER: "0"})),
            (private, dict(first_map, **{envelope.KEY_LAST_CHAPTER: 1.5})),
        ]
        for state_private, map_value in cases:
            with self.assertRaises(envelope.EnvelopeError) as caught:
                envelope.resolve_state(state_private, map_value)
            self.assertEqual(caught.exception.code,
                             envelope.REASON_ABSENT_STATE)
            self.assertNotEqual(str(caught.exception).strip(), "")

    def test_the_goals_list_length_is_not_constrained(self) -> None:
        """The on-demand growth is a legacy behaviour, so any length resolves."""
        for length in (0, 1, 151, 501):
            state = envelope.snapshot_state(dict(
                self.save,
                privateState=dict(
                    self.save["privateState"],
                    **{envelope.KEY_GOALS: [None] * length},
                ),
            ))
            self.assertEqual(len(state[envelope.KEY_GOALS]), length)

    def test_the_mission_field_reports_all_three_measured_shapes(self) -> None:
        for value in (0, 5, "5", True):
            state = envelope.snapshot_state(dict(
                self.save,
                maps=[dict(self.save["maps"][0], **{envelope.KEY_MISSION: value})],
            ))
            self.assertEqual(state[envelope.KEY_MISSION], value)
        projection = envelope.project_quests(state)
        self.assertEqual(projection["mission_is_string"],
                         isinstance(state[envelope.KEY_MISSION], str))

    def test_snapshot_state_refuses_a_save_with_no_first_map(self) -> None:
        for save in (None, "nope", {}, {"maps": []}, {"maps": [1]},
                     {"maps": []}):
            with self.assertRaises(envelope.EnvelopeError):
                envelope.snapshot_state(save)

    def test_the_resolution_copies_never_alias_the_live_save(self) -> None:
        state = envelope.snapshot_state(self.save)
        state[envelope.KEY_GOALS].append("mutated")
        state[envelope.KEY_QUEST_VARS] = {"mutated": True}
        fresh = envelope.snapshot_state(self.save)
        self.assertEqual(len(fresh[envelope.KEY_GOALS]),
                         envelope.COMMITTED_GOALS_LENGTH)
        self.assertIsNone(fresh[envelope.KEY_QUEST_VARS])
        self.assertEqual(len(self.save["privateState"][envelope.KEY_GOALS]),
                         envelope.COMMITTED_GOALS_LENGTH)


class ProjectionTests(unittest.TestCase):
    """The read-only projection, and the empty ``derived`` block."""

    def setUp(self) -> None:
        self.save = json.loads(CORPUS_SAVE.read_text(encoding="utf-8"))
        self.state = envelope.snapshot_state(self.save)

    def test_all_seven_fields_are_reported_verbatim(self) -> None:
        projection = envelope.project_quests(self.state)
        self.assertEqual(len(envelope.QUEST_FIELDS), 7)
        self.assertEqual(projection["quest_field_names"],
                         list(envelope.QUEST_FIELDS))
        self.assertEqual(projection["goals_length"],
                         envelope.COMMITTED_GOALS_LENGTH)
        self.assertEqual(projection["goals_null_entries"],
                         envelope.COMMITTED_GOALS_LENGTH)
        self.assertTrue(projection["verbatim"])

    def test_the_projection_declares_itself_resolved(self) -> None:
        """Every returned projection is resolved; refusals raise instead.

        The client's typed parser requires ``resolvable is True`` on both the
        after and the previous projection, so a projection that omitted the flag
        was refused by the client as ``bad_response`` while every offline check
        passed.  The flag is therefore pinned here, and the second half of this
        test pins that it is never ``False`` in a returned projection.
        """
        for state in (self.state,
                      dict(self.state, **{envelope.KEY_QUEST_VARS: {}}),
                      dict(self.state, **{envelope.KEY_QUEST_VARS: None})):
            projection = envelope.project_quests(state)
            self.assertIs(projection["ok"], True)
            self.assertIs(projection["resolvable"], True)
        for bad in (None, "nope", [], {}, {"goals": []},
                    dict(self.state, **{envelope.KEY_GOALS: {}})):
            with self.assertRaises(envelope.EnvelopeError):
                envelope.project_quests(bad)

    def test_the_projection_derives_nothing_at_all(self) -> None:
        projection = envelope.project_quests(self.state)
        self.assertEqual(projection["derived"], {})
        self.assertIsNone(projection["completion_state"])
        self.assertEqual(projection["reward_paid"], 0)
        self.assertFalse(projection["reward_derived_from_content"])
        self.assertFalse(projection["unlocked_quest_index_written"])

    def test_the_projection_refuses_a_malformed_state(self) -> None:
        for bad in (None, "nope", [], {}, {"goals": []}):
            with self.assertRaises(envelope.EnvelopeError):
                envelope.project_quests(bad)

    def test_the_projection_carries_the_branch_and_writer_inventories(self) -> None:
        projection = envelope.project_quests(self.state)
        self.assertEqual(projection["branch_count"], envelope.BRANCH_COUNT)
        self.assertEqual(len(projection["branches"]), envelope.BRANCH_COUNT)
        self.assertEqual(projection["writer_count"], envelope.WRITER_COUNT)
        self.assertEqual(len(projection["writers"]), envelope.WRITER_COUNT)
        self.assertIn("IMPLEMENTED NOT AT ALL", projection["fast_forward"])
        self.assertFalse(projection["migration"]["is_gameplay"])

    def test_the_projection_carries_the_content_inventory_and_the_refusals(self) -> None:
        projection = envelope.project_quests(self.state)
        self.assertEqual(len(projection["content_fields"]),
                         envelope.COMMITTED_FIELD_COUNT)
        self.assertEqual(len(projection["refusals"]), len(envelope.REFUSALS))
        self.assertEqual(projection["refused_destruction"]["status"],
                         "DIVERGENCE, NOT PARITY")

    def test_the_projection_copies_and_never_mutates(self) -> None:
        projection = envelope.project_quests(self.state)
        projection["fields"][envelope.KEY_GOALS].append("mutated")
        projection["fields"][envelope.KEY_RANKS]["mutated"] = True
        again = envelope.project_quests(self.state)
        self.assertEqual(len(again["fields"][envelope.KEY_GOALS]),
                         envelope.COMMITTED_GOALS_LENGTH)
        self.assertEqual(again["fields"][envelope.KEY_RANKS], {})


class DerivedEffectTests(unittest.TestCase):
    """The derived effect of each action, and the post-execution comparison."""

    def setUp(self) -> None:
        self.save = json.loads(CORPUS_SAVE.read_text(encoding="utf-8"))
        self.state = envelope.snapshot_state(self.save)

    def _stamped(self, derived: Dict[str, Any]) -> Dict[str, Any]:
        after = envelope.copy_state(derived["derived_state"])
        if derived["stamps_chapter"]:
            after[envelope.KEY_LAST_CHAPTER] = 1700000000
        if derived["stamps_instant"]:
            after[envelope.KEY_QUEST_TIMES] = dict(
                after[envelope.KEY_QUEST_TIMES])
            after[envelope.KEY_QUEST_TIMES][str(derived["addressing"])] = (
                1700000000)
        return after

    def test_every_action_derives_its_recorded_written_set(self) -> None:
        expected = {
            envelope.ACTION_SET_GOAL: [envelope.KEY_GOALS],
            envelope.ACTION_COMPLETE_GOAL: [],
            envelope.ACTION_SET_QUEST_VAR: [envelope.KEY_QUEST_VARS],
            envelope.ACTION_COLLECT_MISSION: [
                envelope.KEY_MISSION, envelope.KEY_LAST_CHAPTER,
                envelope.KEY_QUEST_VARS,
            ],
            envelope.ACTION_SET_QUEST_RANK: [envelope.KEY_RANKS],
            envelope.ACTION_END_QUEST: [envelope.KEY_QUEST_TIMES],
        }
        addressing = {
            envelope.ACTION_SET_GOAL: 2,
            envelope.ACTION_COMPLETE_GOAL: 2,
            envelope.ACTION_SET_QUEST_VAR: "boss",
            envelope.ACTION_COLLECT_MISSION: 5,
            envelope.ACTION_SET_QUEST_RANK: 3,
            envelope.ACTION_END_QUEST: 7,
        }
        for action in envelope.ACTIONS:
            derived = envelope.derived_quest(self.state, action, addressing[action])
            self.assertEqual(derived["written"], expected[action], action)
            self.assertEqual(
                sorted(derived["untouched"]),
                sorted(set(envelope.QUEST_FIELDS) - set(expected[action])),
            )
            self.assertEqual(
                envelope.expected_state(
                    self.state, action, addressing[action],
                    self._stamped(derived),
                ),
                None,
            )

    def test_set_goals_stores_the_derived_pair_and_grows_without_bound(self) -> None:
        derived = envelope.derived_quest(self.state, envelope.ACTION_SET_GOAL, 2)
        goals = derived["derived_state"][envelope.KEY_GOALS]
        self.assertEqual(len(goals), envelope.COMMITTED_GOALS_LENGTH)
        self.assertEqual(goals[2], list(envelope.DERIVED_PROGRESS))
        self.assertIsNone(goals[3])
        grown = envelope.derived_quest(self.state, envelope.ACTION_SET_GOAL, 500)
        self.assertEqual(
            len(grown["derived_state"][envelope.KEY_GOALS]), 501)
        self.assertEqual(
            grown["derived_state"][envelope.KEY_GOALS][500],
            list(envelope.DERIVED_PROGRESS),
        )

    def test_the_no_op_branch_derives_a_byte_identical_state(self) -> None:
        derived = envelope.derived_quest(self.state,
                                         envelope.ACTION_COMPLETE_GOAL, 2)
        self.assertFalse(derived["mutates"])
        for key in envelope.QUEST_FIELDS:
            self.assertEqual(derived["derived_state"][key], self.state[key])
        # …and any move at all is named as a divergence.
        moved = envelope.copy_state(self.state)
        moved[envelope.KEY_GOALS] = list(moved[envelope.KEY_GOALS])
        moved[envelope.KEY_GOALS][0] = [1, 1]
        divergence = envelope.expected_state(
            self.state, envelope.ACTION_COMPLETE_GOAL, 2, moved)
        self.assertIsNotNone(divergence)
        self.assertIn("NOTHING AT ALL", divergence)

    def test_set_quest_var_self_heals_the_recorded_null(self) -> None:
        derived = envelope.derived_quest(self.state,
                                         envelope.ACTION_SET_QUEST_VAR, "boss")
        variables = derived["derived_state"][envelope.KEY_QUEST_VARS]
        self.assertIsInstance(variables, dict)
        self.assertEqual(variables, {"boss": envelope.DERIVED_QUEST_VALUE})

    def test_set_quest_var_id_also_overwrites_the_mission(self) -> None:
        derived = envelope.derived_quest(self.state,
                                         envelope.ACTION_SET_QUEST_VAR, "id")
        self.assertEqual(sorted(derived["written"]),
                         sorted([envelope.KEY_MISSION, envelope.KEY_QUEST_VARS]))
        self.assertEqual(derived["derived_state"][envelope.KEY_MISSION],
                         envelope.DERIVED_QUEST_VALUE)

    def test_set_quest_var_accepts_an_invented_key_and_refuses_one_key(self) -> None:
        for invented in ("zzz", "a_client_invented_key", " ", "0"):
            if invented.strip() == "":
                with self.assertRaises(envelope.EnvelopeError) as caught:
                    envelope.derived_quest(self.state,
                                           envelope.ACTION_SET_QUEST_VAR, invented)
                self.assertEqual(caught.exception.code,
                                 envelope.REASON_INVALID_KEY)
                continue
            derived = envelope.derived_quest(self.state,
                                             envelope.ACTION_SET_QUEST_VAR, invented)
            self.assertEqual(
                derived["derived_state"][envelope.KEY_QUEST_VARS],
                {invented: envelope.DERIVED_QUEST_VALUE},
            )
        with self.assertRaises(envelope.EnvelopeError) as caught:
            envelope.derived_quest(self.state, envelope.ACTION_SET_QUEST_VAR,
                                   envelope.QUEST_VAR_IGNORED_KEY)
        self.assertEqual(caught.exception.code, envelope.REASON_IGNORED_KEY)

    def test_collect_mission_stringifies_wraps_and_clears(self) -> None:
        derived = envelope.derived_quest(self.state,
                                         envelope.ACTION_COLLECT_MISSION, 5)
        self.assertEqual(derived["derived_state"][envelope.KEY_MISSION], "5")
        self.assertEqual(derived["derived_state"][envelope.KEY_QUEST_VARS], {})
        self.assertTrue(derived["stamps_chapter"])
        wrapped = envelope.derived_quest(self.state,
                                         envelope.ACTION_COLLECT_MISSION, 150)
        self.assertEqual(wrapped["derived_state"][envelope.KEY_MISSION], "1")

    def test_the_rank_difficulty_is_derived_never_client_sent(self) -> None:
        derived = envelope.derived_quest(self.state,
                                         envelope.ACTION_SET_QUEST_RANK, 3)
        self.assertEqual(derived["derived_state"][envelope.KEY_RANKS],
                         {"3": envelope.DERIVED_DIFFICULTY})

    def test_end_quest_derives_one_entry_and_never_a_destruction(self) -> None:
        derived = envelope.derived_quest(self.state,
                                         envelope.ACTION_END_QUEST, 7)
        self.assertEqual(derived["written"], [envelope.KEY_QUEST_TIMES])
        self.assertTrue(derived["stamps_instant"])
        self.assertEqual(derived["destruction"], "refused")
        blob = envelope.end_quest_blob(7)
        self.assertEqual(blob["units"], [])
        self.assertEqual(blob["quest_id"], 7)
        self.assertEqual(blob["difficulty"], envelope.DERIVED_DIFFICULTY)

    def test_the_unlocked_index_is_untouched_by_every_action(self) -> None:
        for action in envelope.ACTIONS:
            addressing: Any = "boss" if action == envelope.ACTION_SET_QUEST_VAR else 2
            derived = envelope.derived_quest(self.state, action, addressing)
            self.assertEqual(
                derived["derived_state"][envelope.KEY_UNLOCKED_INDEX],
                envelope.COMMITTED_UNLOCKED_INDEX,
                "%s wrote the unlocked-quest index" % action,
            )
            self.assertIn(envelope.KEY_UNLOCKED_INDEX, derived["untouched"])

    def test_every_divergence_is_named(self) -> None:
        cases = [
            (envelope.ACTION_SET_GOAL, 2, envelope.KEY_GOALS,
             ["nope"] + [None] * 150, "not the derived"),
            (envelope.ACTION_COLLECT_MISSION, 5, envelope.KEY_MISSION, 7,
             "not the derived"),
            (envelope.ACTION_SET_QUEST_RANK, 3, envelope.KEY_RANKS,
             {"3": 99}, "not the derived"),
            (envelope.ACTION_SET_QUEST_VAR, "boss", envelope.KEY_QUEST_VARS,
             {"boss": "client"}, "not the derived"),
        ]
        for action, addressing, key, value, phrase in cases:
            derived = envelope.derived_quest(self.state, action, addressing)
            after = self._stamped(derived)
            after[key] = value
            divergence = envelope.expected_state(self.state, action, addressing,
                                                 after)
            self.assertIsNotNone(divergence)
            self.assertIn(phrase, divergence)

    def test_an_untouched_field_that_moved_is_named(self) -> None:
        derived = envelope.derived_quest(self.state, envelope.ACTION_END_QUEST, 7)
        after = self._stamped(derived)
        after[envelope.KEY_RANKS] = {"9": 3}
        divergence = envelope.expected_state(
            self.state, envelope.ACTION_END_QUEST, 7, after)
        self.assertIsNotNone(divergence)
        self.assertIn("untouched", divergence)

    def test_a_missing_field_is_named(self) -> None:
        derived = envelope.derived_quest(self.state, envelope.ACTION_END_QUEST, 7)
        after = self._stamped(derived)
        del after[envelope.KEY_RANKS]
        divergence = envelope.expected_state(
            self.state, envelope.ACTION_END_QUEST, 7, after)
        self.assertIsNotNone(divergence)
        self.assertIn("carries no", divergence)

    def test_a_missing_or_non_positive_quest_time_is_named(self) -> None:
        for value in (None, "x", 0, -1):
            after = dict(envelope.snapshot_state(self.save))
            after[envelope.KEY_QUEST_TIMES] = {"7": value}
            divergence = envelope.expected_state(
                self.state, envelope.ACTION_END_QUEST, 7, after)
            self.assertIsNotNone(divergence, value)
        # Another quest time must not move.
        after = dict(envelope.snapshot_state(self.save))
        after[envelope.KEY_QUEST_TIMES] = {"7": 1700000000, "8": 5}
        divergence = envelope.expected_state(
            self.state, envelope.ACTION_END_QUEST, 7, after)
        self.assertIsNotNone(divergence)
        self.assertIn("another quest time", divergence)

    def test_a_backwards_chapter_stamp_is_named(self) -> None:
        derived = envelope.derived_quest(self.state,
                                         envelope.ACTION_COLLECT_MISSION, 5)
        after = self._stamped(derived)
        after[envelope.KEY_LAST_CHAPTER] = 0
        saved = self.state[envelope.KEY_LAST_CHAPTER]
        if saved:
            divergence = envelope.expected_state(
                self.state, envelope.ACTION_COLLECT_MISSION, 5, after)
            self.assertIsNotNone(divergence)

    def test_a_negative_goal_index_is_refused_structurally(self) -> None:
        for bad in (-1, -1000):
            with self.assertRaises(envelope.EnvelopeError) as caught:
                envelope.derived_quest(self.state, envelope.ACTION_SET_GOAL, bad)
            self.assertEqual(caught.exception.code,
                             envelope.REASON_INVALID_GOAL_INDEX)
        self.assertTrue(envelope.is_goal_index(0))
        self.assertTrue(envelope.is_goal_index(500))

    def test_a_non_integer_addressing_is_refused_per_action(self) -> None:
        cases = [
            (envelope.ACTION_COMPLETE_GOAL, "2", envelope.REASON_INVALID_GOAL_INDEX),
            (envelope.ACTION_SET_QUEST_VAR, 7, envelope.REASON_INVALID_KEY),
            (envelope.ACTION_COLLECT_MISSION, "5",
             envelope.REASON_INVALID_MISSION),
            (envelope.ACTION_SET_QUEST_RANK, None,
             envelope.REASON_INVALID_QUEST_INDEX),
            (envelope.ACTION_END_QUEST, "seven", envelope.REASON_INVALID_QUEST_ID),
        ]
        for action, addressing, code in cases:
            with self.assertRaises(envelope.EnvelopeError) as caught:
                envelope.derived_quest(self.state, action, addressing)
            self.assertEqual(caught.exception.code, code, action)

    def test_a_boolean_is_not_a_strict_integer_addressing(self) -> None:
        for action in (envelope.ACTION_SET_GOAL, envelope.ACTION_COMPLETE_GOAL,
                       envelope.ACTION_COLLECT_MISSION,
                       envelope.ACTION_SET_QUEST_RANK,
                       envelope.ACTION_END_QUEST):
            with self.assertRaises(envelope.EnvelopeError):
                envelope.derived_quest(self.state, action, True)

    def test_the_derivation_refuses_an_unknown_action(self) -> None:
        with self.assertRaises(envelope.EnvelopeError) as caught:
            envelope.derived_quest(self.state, "teleport", 1)
        self.assertEqual(caught.exception.code, envelope.REASON_INVALID_ACTION)

    def test_the_derivation_refuses_a_state_missing_a_field(self) -> None:
        partial = {key: value for key, value in self.state.items()
                   if key != envelope.KEY_RANKS}
        with self.assertRaises(envelope.EnvelopeError) as caught:
            envelope.derived_quest(partial, envelope.ACTION_END_QUEST, 7)
        self.assertEqual(caught.exception.code, envelope.REASON_ABSENT_STATE)


class EnvelopeTests(unittest.TestCase):
    """The legacy batch envelopes, one command and a neutral vector."""

    ADDRESSING = {
        envelope.ACTION_SET_GOAL: 2,
        envelope.ACTION_COMPLETE_GOAL: 2,
        envelope.ACTION_SET_QUEST_VAR: "boss",
        envelope.ACTION_COLLECT_MISSION: 5,
        envelope.ACTION_SET_QUEST_RANK: 3,
        envelope.ACTION_END_QUEST: 7,
    }

    def test_each_action_carries_exactly_one_command_with_a_neutral_vector(
        self,
    ) -> None:
        for action, addressing in self.ADDRESSING.items():
            envelope_payload = envelope.build_envelope(action, addressing,
                                                       ts=1700000000)
            self.assertEqual(sorted(envelope_payload),
                             sorted(envelope.ENVELOPE_KEYS))
            self.assertEqual(len(envelope_payload["commands"]), 1)
            entry = envelope_payload["commands"][0]
            self.assertEqual(entry[0], 0)
            self.assertEqual(entry[1], envelope.ACTION_COMMANDS[action])
            self.assertEqual(entry[3], [0] * envelope.RESOURCE_VECTOR_SLOTS)

    def test_the_argument_shapes_are_the_committed_ones(self) -> None:
        built = {
            action: envelope.build_envelope(action, addressing, ts=1700000000)
            for action, addressing in self.ADDRESSING.items()
        }
        self.assertEqual(built[envelope.ACTION_SET_GOAL]["commands"][0][2],
                         [2, "[0,0]"])
        self.assertEqual(built[envelope.ACTION_COMPLETE_GOAL]["commands"][0][2], [2])
        self.assertEqual(built[envelope.ACTION_SET_QUEST_VAR]["commands"][0][2],
                         ["boss", envelope.DERIVED_QUEST_VALUE])
        self.assertEqual(built[envelope.ACTION_COLLECT_MISSION]["commands"][0][2],
                         [5])
        self.assertEqual(
            built[envelope.ACTION_SET_QUEST_RANK]["commands"][0][2],
            [3, envelope.DERIVED_DIFFICULTY],
        )
        blob = json.loads(built[envelope.ACTION_END_QUEST]["commands"][0][2][0])
        self.assertEqual(blob, envelope.end_quest_blob(7))

    def test_the_progress_pair_is_the_derived_zero_pair(self) -> None:
        self.assertEqual(list(envelope.DERIVED_PROGRESS), [0, 0])
        entry = envelope.build_envelope(envelope.ACTION_SET_GOAL, 2,
                                         ts=1700000000)["commands"][0]
        self.assertEqual(json.loads(entry[2][1]), [0, 0])

    def test_a_structurally_invalid_request_is_refused(self) -> None:
        cases = [
            ("teleport", 1, envelope.REASON_INVALID_ACTION),
            (envelope.ACTION_SET_GOAL, -1, envelope.REASON_INVALID_GOAL_INDEX),
            (envelope.ACTION_COMPLETE_GOAL, "2",
             envelope.REASON_INVALID_GOAL_INDEX),
            (envelope.ACTION_SET_QUEST_VAR, "",
             envelope.REASON_INVALID_KEY),
            (envelope.ACTION_SET_QUEST_VAR, envelope.QUEST_VAR_IGNORED_KEY,
             envelope.REASON_IGNORED_KEY),
            (envelope.ACTION_COLLECT_MISSION, None,
             envelope.REASON_INVALID_MISSION),
            (envelope.ACTION_SET_QUEST_RANK, "3",
             envelope.REASON_INVALID_QUEST_INDEX),
            (envelope.ACTION_END_QUEST, "7", envelope.REASON_INVALID_QUEST_ID),
        ]
        for action, addressing, code in cases:
            with self.assertRaises(envelope.EnvelopeError) as caught:
                envelope.build_envelope(action, addressing)
            self.assertEqual(caught.exception.code, code, (action, addressing))

    def test_a_negative_timestamp_is_refused(self) -> None:
        with self.assertRaises(envelope.EnvelopeError) as caught:
            envelope.build_envelope(envelope.ACTION_SET_GOAL, 2, ts=-1)
        self.assertEqual(caught.exception.code, envelope.REASON_INVALID_TIMESTAMP)

    def test_only_the_neutral_vector_is_derivable(self) -> None:
        neutral = envelope.neutral_vector()
        self.assertEqual(neutral, [0] * envelope.RESOURCE_VECTOR_SLOTS)
        self.assertEqual(envelope.validate_vector(neutral), neutral)
        self.assertIsNot(envelope.neutral_vector(),
                         envelope.neutral_vector())
        for bad in ([1] + [0] * 7, [0] * 7 + [-5], [0] * 7, [0] * 8 + [0],
                    ["0"] * 8, None):
            with self.assertRaises(envelope.EnvelopeError) as caught:
                envelope.validate_vector(bad)
            self.assertEqual(caught.exception.code,
                             envelope.REASON_INVALID_VECTOR)

    def test_the_data_field_round_trips_through_the_shared_serializer(self) -> None:
        built = envelope.build_envelope(envelope.ACTION_SET_QUEST_VAR, "boss",
                                        ts=1700000000)
        data = envelope.data_field(built)
        self.assertEqual(envelope.parse_data_field(data), built)
        self.assertIn(built["commands"][0][1], data)


class RefusalFamilyTests(unittest.TestCase):
    """Task 4.1: the refusals as stated requirements."""

    def test_every_family_is_recorded_with_a_non_empty_reason(self) -> None:
        self.assertGreaterEqual(len(envelope.REFUSALS), 6)
        for record in envelope.REFUSALS:
            self.assertFalse(record["implemented"])
            self.assertNotEqual(record["reason"].strip(), "")
            self.assertIn(record["refusal"],
                          ("no_reward", "no_resource_move", "no_completion",
                           "no_bounds", "no_membership", "no_elapsed"))

    def test_the_reward_family_states_the_zero_consumer_uniform_fact(self) -> None:
        self.assertIn("ZERO", envelope.NO_REWARD)
        self.assertIn("UNIFORMLY", envelope.NO_REWARD)
        self.assertIn("91", envelope.NO_REWARD)
        self.assertEqual(envelope.REWARD_PAID, 0)

    def test_the_completion_family_states_the_no_op_branch(self) -> None:
        self.assertIn("NOTHING AT ALL", envelope.NO_COMPLETION)
        self.assertIn("complete_goal", envelope.NO_COMPLETION)

    def test_the_bounds_family_states_that_none_is_invented(self) -> None:
        self.assertIn("NO BOUND IS ADDED", envelope.NO_BOUNDS)
        self.assertIn("Server v1 / M13", envelope.NO_BOUNDS)
        self.assertIn("350", envelope.NO_BOUNDS)

    def test_the_membership_family_states_the_one_refused_key(self) -> None:
        self.assertIn("NO MEMBERSHIP TEST IS ADDED", envelope.NO_MEMBERSHIP)
        self.assertIn(envelope.QUEST_VAR_IGNORED_KEY, envelope.NO_MEMBERSHIP)
        self.assertIn("UNBOUNDED", envelope.QUEST_VAR_COMMENT_NOTE.upper())

    def test_the_resource_family_names_the_neutral_vector(self) -> None:
        self.assertIn("NEUTRAL", envelope.NO_RESOURCE_MOVE)
        self.assertIn("command.py:40", envelope.NO_RESOURCE_MOVE)
        self.assertIn("engine.py:251-271", envelope.NO_RESOURCE_MOVE)

    def test_the_elapsed_family_states_that_no_instant_is_read(self) -> None:
        self.assertIn("NO ELAPSED-TIME BEHAVIOUR", envelope.NO_ELAPSED)

    def test_the_refused_destruction_is_recorded_as_a_divergence(self) -> None:
        record = envelope.REFUSED_DESTRUCTION
        self.assertFalse(record["implemented"])
        self.assertEqual(record["status"], "DIVERGENCE, NOT PARITY")
        self.assertIn("map_lose_item", record["legacy_behaviour"])
        self.assertIn("EMPTY LIST", record["modern_behaviour"])
        self.assertIn("unit[2] - unit[3]", record["reason"])

    def test_no_client_value_is_persisted(self) -> None:
        self.assertEqual(envelope.PERSISTED_CLIENT_VALUES, ())
        for key in ("progress", "value", "difficulty", "units", "lost",
                    "win", "voluntary_end", "reward"):
            self.assertIn(key, envelope.IGNORED_CLIENT_KEYS)

    def test_the_structural_refusals_are_enumerable(self) -> None:
        self.assertIn(envelope.REASON_ABSENT_STATE,
                      envelope.STRUCTURAL_REFUSALS)
        self.assertIn(envelope.REASON_IGNORED_KEY,
                      envelope.STRUCTURAL_REFUSALS)
        for code in envelope.STRUCTURAL_REFUSALS:
            self.assertNotEqual(code.strip(), "")


class LedgerDoorTests(unittest.TestCase):
    """Design D10: the quest path's reach into the dead-hero ledger."""

    def test_map_lose_item_is_reached_from_end_quest_and_end_attack(self) -> None:
        door = envelope.LEDGER_DOOR
        self.assertEqual(door["door"], "map_lose_item")
        self.assertEqual(door["source"], "engine.py:215-228")
        self.assertEqual(door["calls_helper_at"],
                         "engine.py:223 (push_dead_unit)")
        self.assertFalse(door["is_a_dispatcher_branch"])
        self.assertEqual(len(door["callers"]), 2)
        self.assertIn("command.py:796 (end_quest)", door["callers"])
        self.assertIn("command.py:872 (end_attack)", door["callers"])

    def test_the_two_callers_are_measured_out_of_the_source(self) -> None:
        engine = legacy_text("engine.py").split("\n")
        definition = next(
            index + 1 for index, line in enumerate(engine)
            if line.strip().startswith("def map_lose_item(")
        )
        self.assertEqual(definition, 215)
        calls = [
            index + 1 for index, line in enumerate(engine)
            if "push_dead_unit(" in line and "def " not in line
        ]
        self.assertEqual(calls, [223])
        command = legacy_text("command.py").split("\n")
        reached = [
            index + 1 for index, line in enumerate(command)
            if "map_lose_item(" in line and "import" not in line
        ]
        self.assertEqual(reached, [796, 872])

    def test_the_quest_side_reach_is_refused(self) -> None:
        self.assertIn("REFUSED", envelope.LEDGER_DOOR["modern_behaviour"])
        blob = envelope.end_quest_blob(7)
        self.assertEqual(blob["units"], [])


class AntiInventionGuardTests(unittest.TestCase):
    """Task 4.4: the module's whole function inventory is pinned."""

    #: The module's own functions, in commit order.  A readiness, remaining-time,
    #: price, progress-ratio, or completion helper fails the run wherever it is
    #: added.
    EXPECTED_FUNCTIONS = [
        "_copy_goals",
        "_copy_ranks",
        "_copy_times",
        "_copy_vars",
        "_pad_goals",
        "build_envelope",
        "clamp_difficulty",
        "command_for_action",
        "copy_state",
        "derived_quest",
        "end_quest_blob",
        "expected_state",
        "is_action",
        "is_goal_index",
        "is_mission",
        "is_quest_id",
        "is_quest_rank_index",
        "is_quest_var_key",
        "neutral_vector",
        "project_quests",
        "resolve_state",
        "snapshot_state",
        "validate_vector",
        "wrap_mission",
    ]

    def test_the_module_declares_exactly_the_pinned_functions(self) -> None:
        self.assertEqual(declared_functions(), sorted(self.EXPECTED_FUNCTIONS))

    def test_no_helper_named_after_an_invented_rule_exists(self) -> None:
        names = set(declared_functions())
        for forbidden in ("quest_reward", "quest_progress_ratio",
                          "quest_remaining_time", "quest_duration",
                          "mark_goal_complete", "is_goal_complete",
                          "goal_complete", "quest_ready", "quest_cost",
                          "quest_price", "quest_unlock", "fast_forward",
                          "quest_total", "quest_reward_amount"):
            self.assertNotIn(forbidden, names)

    def test_the_module_source_carries_no_forbidden_declaration(self) -> None:
        source = Path(envelope.__file__).read_text(encoding="utf-8")
        for forbidden in ("def quest_reward", "def quest_progress_ratio",
                          "def quest_remaining_time", "def mark_goal_complete",
                          "def is_goal_complete", "def fast_forward",
                          "def quest_cost", "def quest_price"):
            self.assertNotIn(forbidden, source)

    def test_no_code_identifier_mentions_a_computation_of_a_derived_value(
        self,
    ) -> None:
        names = code_names(Path(envelope.__file__))
        for forbidden in ("remaining_time", "progress_ratio", "elapsed",
                          "time_left", "cooldown", "completeness",
                          "unlock_requirement", "estimated_reward"):
            self.assertNotIn(forbidden, names)

    def test_the_module_persists_no_client_value(self) -> None:
        """A client value reaching a write would be the anti-pattern itself."""
        names = code_names(Path(envelope.__file__))
        for forbidden in ("apply_client_vector", "client_value",
                          "apply_resources", "map_lose_item", "map_pop_item"):
            self.assertNotIn(forbidden, names)

    def test_the_derived_values_are_constants_not_lookups(self) -> None:
        self.assertEqual(envelope.REWARD_PAID, 0)
        self.assertEqual(envelope.DERIVED_DIFFICULTY, 1)
        self.assertEqual(list(envelope.DERIVED_PROGRESS), [0, 0])
        self.assertEqual(list(envelope.DERIVED_UNITS), [])
        self.assertEqual(envelope.DERIVED_DURATION, 0)
        self.assertEqual(envelope.DERIVED_MAP, 0)
        self.assertIs(envelope.DERIVED_WIN, True)
        self.assertIs(envelope.DERIVED_VOLUNTARY_END, True)
        self.assertIs(envelope.DERIVED_QUEST_VALUE, True)