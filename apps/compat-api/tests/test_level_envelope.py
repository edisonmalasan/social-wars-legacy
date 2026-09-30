#!/usr/bin/env python3
"""Offline unit tests for the level-curve derivation and the level capture
tool's published contract (OpenSpec tasks 2.1 / 1.1).

No server, no socket, no corpus: everything here is pure derivation over the
committed config and seed documents, so it runs in milliseconds under the pinned
interpreter.  The real-config cross-checks pin the committed curve's entry
count, its first thresholds and final threshold, the strictly-increasing and
no-duplicate property, the distinct-name census, the reward vocabularies, the
corpus's own `xp 4 / level 1` case, the derived level, and the neutral vector
against the bytes the legacy server actually loads.  The shared-helper round
trip proves the single-command envelope travels through the placement module's
unchanged serialization.

The three derived decisions are asserted as behavior, not comments:

* **D1** the curve is **one-based** — stored level *n* is ``levels[n - 1]`` — and
  the conversion lives in exactly one named function,
  ``entry_index_for_level``, which is the only place a level becomes an index.
  The **rejected zero-based** alternative is contradicted by the corpus, and the
  boundary cases are covered from both sides of every threshold;
* **D3** the envelope's level is the **derived** one and the vector is
  **neutral**, so :func:`validate_vector` refuses anything that would move a
  balance — the derivation cannot express vector smuggling at all;
* **D4/D7** the edges refuse **gracefully** rather than raising (a level below 1,
  an experience above the final threshold), the curve is preserved **verbatim**
  (no rebalancing), and the committed reward fields are never turned into a
  payout.
"""

from __future__ import annotations

import ast
import json
import re
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import capture_level_fixture as capture
import level_envelope as envelope_mod

CONFIG = json.loads((harness.REPO_ROOT / "config" / "main.json").read_text(encoding="utf-8"))
SEED = harness.load_seed()
FRESH_MAP = SEED["maps"][0]  # type: ignore[index]

# The committed curve, read from the committed config here rather than
# hardcoded a second time.
CURVE: Any = CONFIG["levels"]
THRESHOLDS = [int(row["exp_required"]) for row in CURVE]


class SharedHelperTests(unittest.TestCase):
    """One shared derivation: the helpers are reused, not re-implemented."""

    def test_the_shared_helpers_are_the_placement_modules_own(self) -> None:
        import placement_envelope

        self.assertIs(envelope_mod.is_strict_int, placement_envelope.is_strict_int)
        self.assertIs(envelope_mod.EnvelopeError, placement_envelope.EnvelopeError)
        self.assertIs(envelope_mod.data_field, placement_envelope.data_field)
        self.assertIs(envelope_mod.parse_data_field, placement_envelope.parse_data_field)
        self.assertIs(envelope_mod.payload_json, placement_envelope.payload_json)
        self.assertIs(envelope_mod.in_grid, placement_envelope.in_grid)
        self.assertEqual(envelope_mod.ENVELOPE_KEYS, placement_envelope.ENVELOPE_KEYS)
        self.assertEqual(envelope_mod.GRID_EXTENT, placement_envelope.GRID_EXTENT)
        # The level derivation is additive: the delivered siblings keep their own
        # helpers, untouched.
        for foreign in (
            "derived_level_for",
            "entry_index_for_level",
            "entry_for_level",
            "thresholds_from_entries",
            "resource_vector_for",
            "unmet_requirements",
            "payout_for",
        ):
            with self.subTest(helper=foreign):
                self.assertFalse(hasattr(placement_envelope, foreign))

    def test_the_command_is_the_documented_legacy_name(self) -> None:
        # command.py:81-85, and the level_up row of docs/legacy-protocol/commands.json.
        self.assertEqual(envelope_mod.LEVEL_UP_COMMAND, "level_up")
        self.assertEqual(envelope_mod.RESOURCE_VECTOR_SLOTS, 8)

    def test_every_slot_can_never_be_filled(self) -> None:
        """Design D5: a level-up moves no resource, so **all eight** slots are
        always zero — there is no slot this derivation can fill."""
        self.assertEqual(
            envelope_mod.ALWAYS_ZERO_SLOTS, (0, 1, 2, 3, 4, 5, 6, 7)
        )
        self.assertEqual(len(envelope_mod.ALWAYS_ZERO_SLOTS), 8)

    def test_the_provenance_constants_are_the_documented_ones(self) -> None:
        """Design D1 in machine-readable form, reported verbatim by the endpoint."""
        self.assertEqual(envelope_mod.INDEX_BASE, "one-based")
        self.assertEqual(envelope_mod.DERIVATION_STATUS, "derived-provisional")
        self.assertEqual(envelope_mod.REJECTED_ALTERNATIVE, "zero-based")

    def test_the_endpoint_uses_this_module(self) -> None:
        import compat_service

        self.assertIs(compat_service.level_envelope, envelope_mod)
        self.assertEqual(
            compat_service.ERROR_LEVEL_ALREADY_CURRENT, "level_already_current"
        )
        self.assertEqual(compat_service.ERROR_XP_BELOW_THRESHOLD, "xp_below_threshold")


class OneBasedConversionTests(unittest.TestCase):
    """D1: the conversion is one named function and it is one-based."""

    def test_stored_level_n_is_entry_n_minus_one(self) -> None:
        for level in range(1, len(CURVE) + 1):
            with self.subTest(level=level):
                self.assertEqual(
                    envelope_mod.entry_index_for_level(level), level - 1
                )
                # The entry is returned as a **copy** (never aliased), so the
                # comparison is by value.
                self.assertEqual(
                    envelope_mod.entry_for_level(level, CURVE), CURVE[level - 1]
                )
                self.assertIsNot(
                    envelope_mod.entry_for_level(level, CURVE), CURVE[level - 1]
                )

    def test_level_one_is_the_curves_first_entry_and_two_is_the_second(self) -> None:
        """The corpus's decisive case, spelled out: stored level 1 is
        ``levels[0]`` — ``"Slave"``, ``exp_required`` 0 — and level 2 is
        ``levels[1]`` — ``"Servant"``, ``exp_required`` 40."""
        first = envelope_mod.entry_for_level(1, CURVE)
        second = envelope_mod.entry_for_level(2, CURVE)
        self.assertEqual(first["name"], "Slave")  # type: ignore[index]
        self.assertEqual(first["exp_required"], 0)  # type: ignore[index]
        self.assertEqual(second["name"], "Servant")  # type: ignore[index]
        self.assertEqual(second["exp_required"], 40)  # type: ignore[index]

    def test_the_zero_based_alternative_is_contradicted_by_the_corpus(self) -> None:
        """The recorded evidence for D1, asserted: the corpus's ``xp 4`` with
        ``level 1`` is self-consistent only under the **one-based** reading.

        Under the rejected zero-based reading the level would be the raw index,
        so ``xp 4`` would imply level **0** — while the save records 1.  The two
        readings disagree by exactly one level, and the one that disagrees with
        the save is the rejected one.
        """
        derived = envelope_mod.derived_level_for(
            capture.FIXTURE_EXPECTED_XP, THRESHOLDS
        )
        self.assertEqual(derived, envelope_mod.entry_index_for_level(1) + 1)
        # The rejected alternative: the raw index the curve implies, no + 1.
        zero_based = max(
            index
            for index, required in enumerate(THRESHOLDS)
            if required <= capture.FIXTURE_EXPECTED_XP
        )
        self.assertEqual(zero_based, 0)
        self.assertEqual(FRESH_MAP["level"], 1)
        # So the rejected reading contradicts the save and the chosen one does
        # not: under one-based, ``xp 4 >= exp_required(1) == 0``.
        self.assertNotEqual(zero_based, FRESH_MAP["level"])
        self.assertGreaterEqual(
            capture.FIXTURE_EXPECTED_XP,
            envelope_mod.threshold_for(1, THRESHOLDS),
        )
        self.assertLess(
            capture.FIXTURE_EXPECTED_XP,
            envelope_mod.threshold_for(2, THRESHOLDS),
        )

    def test_the_conversion_and_its_inverse_round_trip_over_the_whole_curve(
        self,
    ) -> None:
        for index in range(len(CURVE)):
            with self.subTest(index=index):
                level = envelope_mod.level_for_entry_index(index)
                self.assertIsNotNone(level)
                assert level is not None
                self.assertEqual(
                    envelope_mod.entry_index_for_level(level, len(CURVE)), index
                )

    def test_a_level_below_one_is_refused_gracefully_not_raised(self) -> None:
        """Design D1's lower edge.  ``levels[-1]`` would silently resolve a
        negative level to the curve's **last** entry, so the conversion returns
        ``None`` instead — a refusal, not an exception, and not a wrong entry."""
        for level in (0, -1, -35, -(10 ** 9)):
            with self.subTest(level=level):
                self.assertIsNone(envelope_mod.entry_index_for_level(level))
                self.assertIsNone(
                    envelope_mod.entry_index_for_level(level, len(CURVE))
                )
                self.assertIsNone(envelope_mod.entry_for_level(level, CURVE))
                self.assertIsNone(envelope_mod.threshold_for(level, THRESHOLDS))

    def test_a_level_above_the_curve_is_refused_gracefully(self) -> None:
        for level in (len(CURVE) + 1, len(CURVE) + 35, 10 ** 9):
            with self.subTest(level=level):
                self.assertIsNone(
                    envelope_mod.entry_index_for_level(level, len(CURVE))
                )
                self.assertIsNone(envelope_mod.entry_for_level(level, CURVE))
        # The level space is exactly 1..100.
        self.assertIsNotNone(envelope_mod.entry_index_for_level(len(CURVE), len(CURVE)))
        self.assertIsNone(
            envelope_mod.entry_index_for_level(len(CURVE) + 1, len(CURVE))
        )

    def test_a_non_integer_level_fails_closed(self) -> None:
        """``True`` is an ``int`` in Python, so an ``isinstance`` check alone
        would resolve it to entry 0 and report a real level for a boolean."""
        for bad in ("1", 1.0, True, None, [1], {"level": 1}, 1.5):
            with self.subTest(level=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.entry_index_for_level(bad)
                self.assertEqual(caught.exception.code, "invalid_level")
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.entry_for_level(bad, CURVE)
                self.assertEqual(caught.exception.code, "invalid_level")
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.threshold_for(bad, THRESHOLDS)
                self.assertEqual(caught.exception.code, "invalid_level")

    def test_the_inverse_also_refuses_its_edges_gracefully(self) -> None:
        for bad in (None, True, "0", 0.0, -1, -(10 ** 9), [0]):
            with self.subTest(index=bad):
                self.assertIsNone(envelope_mod.level_for_entry_index(bad))
        self.assertEqual(envelope_mod.level_for_entry_index(0), 1)
        self.assertEqual(envelope_mod.level_for_entry_index(99), 100)

    def test_the_conversion_is_the_only_place_a_level_becomes_an_index(self) -> None:
        """The single-named-place requirement, asserted against the AST.

        The ``- 1`` arithmetic of D1 exists **once** in the module body, inside
        ``entry_index_for_level``, and no other function performs level/index
        arithmetic.  Docstrings *name* the decision on purpose and are excluded
        by looking at executable nodes only.
        """
        tree = ast.parse(Path(envelope_mod.__file__).read_text(encoding="utf-8"))
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("entry_index_for_level", functions)
        self.assertIn("level_for_entry_index", functions)

        def binop_arithmetic(node: ast.AST) -> bool:
            """True when the subtree is level/index arithmetic."""
            for inner in ast.walk(node):
                if isinstance(inner, ast.BinOp) and isinstance(
                    inner.op, (ast.Sub, ast.Add)
                ):
                    names = [
                        child.id
                        for child in ast.walk(inner.left)
                        if isinstance(child, ast.Name)
                    ]
                    if any(name in ("level", "index", "entries") for name in names):
                        return True
            return False

        offenders: List[str] = []
        for name, function in functions.items():
            # Skip the conversion itself and its documented inverse: those two
            # ARE the single named place (forward and inverse).
            if name in ("entry_index_for_level", "level_for_entry_index"):
                continue
            for node in ast.walk(function):
                if isinstance(node, (ast.Assign, ast.AugAssign, ast.Return)):
                    if binop_arithmetic(node):
                        offenders.append("%s (%s)" % (name, type(node).__name__))
        self.assertEqual(offenders, [])

    def test_the_endpoint_and_the_capture_resolve_levels_through_it(self) -> None:
        """D1's "one named place": both consumers call the conversion, and the
        route contains no level/index arithmetic of its own."""
        import compat_service

        service_source = Path(compat_service.__file__).read_text(encoding="utf-8")
        self.assertIn(
            "level_envelope.entry_index_for_level(", service_source
        )
        self.assertIn(
            "curve_entry = level_envelope.entry_for_level(derived, rows)", service_source
        )
        # The capture resolves its level through the module too, never by hand.
        capture_source = Path(capture.__file__).read_text(encoding="utf-8")
        self.assertIn("level_envelope.derived_level_for(", capture_source)
        self.assertIn("level_envelope.build_envelope(level=derived", capture_source)


class ScheduleAccessTests(unittest.TestCase):
    """The committed-curve accessors and their closed shapes."""

    def test_only_a_non_empty_sequence_is_a_curve(self) -> None:
        for bad in (None, (), [], "levels", b"levels", {"0": {}}, 42, 4.0, True):
            with self.subTest(entries=bad):
                self.assertIsNone(envelope_mod.schedule_length(bad))
        self.assertEqual(envelope_mod.schedule_length([{}]), 1)
        self.assertEqual(envelope_mod.schedule_length(({}, {})), 2)

    def test_the_committed_curve_resolves_to_100(self) -> None:
        self.assertEqual(envelope_mod.schedule_length(CURVE), 100)
        self.assertEqual(
            envelope_mod.schedule_length(CURVE),
            envelope_mod.COMMITTED_SCHEDULE_LENGTH,
        )

    def test_a_curve_that_is_not_a_sequence_fails_closed(self) -> None:
        for bad in (None, [], "levels", {"0": {"exp_required": 0}}):
            with self.subTest(entries=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.entry_for_level(1, bad)
                self.assertEqual(caught.exception.code, "unknown_level")
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.thresholds_from_entries(bad)
                self.assertEqual(caught.exception.code, "unknown_level")

    def test_the_returned_entry_is_a_copy_and_is_never_coerced(self) -> None:
        entry = envelope_mod.entry_for_level(1, CURVE)
        self.assertIsNot(entry, CURVE[0])
        entry["name"] = "MUTATED"  # type: ignore[index]
        self.assertEqual(envelope_mod.entry_for_level(1, CURVE)["name"], "Slave")  # type: ignore[index]
        self.assertEqual(CURVE[0]["name"], "Slave")

    def test_a_non_mapping_entry_is_returned_verbatim_for_the_shaped_helper(self) -> None:
        """The accessor never coerces; the shape check lives in the helpers."""
        for bad_row in ("Slave", 42, None, ["Slave", 0]):
            with self.subTest(row=bad_row):
                self.assertEqual(
                    envelope_mod.entry_for_level(1, [bad_row]), bad_row
                )
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.thresholds_from_entries([bad_row])
                self.assertEqual(caught.exception.code, "unknown_level")

    def test_the_snapshot_is_order_stable_and_reports_a_malformed_row(self) -> None:
        self.assertEqual(
            envelope_mod.entry_snapshot(CURVE[0]),
            (("name", "Slave"), ("exp_required", 0), ("reward_type", "s"),
             ("reward_amount", 50)),
        )
        self.assertEqual(envelope_mod.entry_snapshot("Slave"), ("<str>",))
        self.assertEqual(envelope_mod.COMMITTED_ENTRY_FIELDS,
                         ("name", "exp_required", "reward_type", "reward_amount"))


class ThresholdTests(unittest.TestCase):
    """The committed ladder, preserved verbatim and checked for shape."""

    def test_the_ladder_is_read_verbatim(self) -> None:
        self.assertEqual(envelope_mod.thresholds_from_entries(CURVE), THRESHOLDS)
        self.assertEqual(len(envelope_mod.thresholds_from_entries(CURVE)), 100)
        self.assertEqual(
            envelope_mod.thresholds_from_entries(CURVE)[-1],
            envelope_mod.COMMITTED_FINAL_THRESHOLD,
        )
        self.assertEqual(
            tuple(envelope_mod.thresholds_from_entries(CURVE)[:8]),
            envelope_mod.COMMITTED_FIRST_THRESHOLDS,
        )

    def test_a_missing_or_unusable_threshold_fails_closed(self) -> None:
        cases = (
            [{"name": "Slave"}],
            [{"exp_required": "0"}],
            [{"exp_required": 0.0}],
            [{"exp_required": True}],
            [{"exp_required": None}],
            [{"exp_required": -1}],
            [{"exp_required": 0}, {"exp_required": 0}],
            [{"exp_required": 0}, {"exp_required": -1}],
            [{"exp_required": 100}, {"exp_required": 40}],
        )
        for rows in cases:
            with self.subTest(rows=rows):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.thresholds_from_entries(rows)
                self.assertEqual(caught.exception.code, "unknown_level")

    def test_error_messages_never_carry_save_content(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.thresholds_from_entries([{"exp_required": "SECRET"}])
        message = str(caught.exception)
        self.assertIn("exp_required", message)
        self.assertNotIn("00000000", message)  # no save ids leak into an error

    def test_a_duplicate_or_flat_gap_is_refused_rather_than_silently_accepted(self) -> None:
        """Design D7: the committed curve is strictly increasing, so a duplicate
        or a non-positive gap is a content failure this contract reports rather
        than resolving into a level model."""
        self.assertEqual(len(set(THRESHOLDS)), len(THRESHOLDS))
        gaps = [b - a for a, b in zip(THRESHOLDS, THRESHOLDS[1:])]
        self.assertTrue(all(gap > 0 for gap in gaps))
        self.assertEqual(min(gaps), min(gaps))
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            envelope_mod.thresholds_from_entries([{"exp_required": 0},
                                                  {"exp_required": 0}])
        self.assertEqual(caught.exception.code, "unknown_level")


class LadderBoundaryTests(unittest.TestCase):
    """Design D1's boundary coverage: every rung from both sides."""

    def test_experience_exactly_on_each_of_the_first_thresholds(self) -> None:
        """``exp == threshold[k]`` derives level ``k + 1`` — the off-by-one's
        decisive direction."""
        for index, required in enumerate(
            envelope_mod.COMMITTED_FIRST_THRESHOLDS
        ):
            with self.subTest(threshold=required):
                self.assertEqual(
                    envelope_mod.derived_level_for(required, THRESHOLDS), index + 1
                )
                self.assertEqual(
                    envelope_mod.threshold_for(index + 1, THRESHOLDS), required
                )
                # The level below rung k+1's threshold carries the **previous**
                # rung's threshold — except at the floor, where a level below 1
                # has no committed entry at all.
                self.assertEqual(
                    envelope_mod.threshold_for(index, THRESHOLDS),
                    THRESHOLDS[index - 1] if index else None,
                )

    def test_experience_one_below_each_of_the_first_thresholds(self) -> None:
        for index, required in enumerate(
            envelope_mod.COMMITTED_FIRST_THRESHOLDS
        ):
            with self.subTest(threshold=required):
                # One below rung k+1's threshold derives level k — never k+1.
                # The committed floor is 0, so rung 1 has nothing below it and
                # the negative value is outside the curve entirely (handled by
                # the floor case below).
                if required > 0:
                    self.assertEqual(
                        envelope_mod.derived_level_for(required - 1, THRESHOLDS),
                        index,
                    )
                # …and one above derives k+1.
                self.assertEqual(
                    envelope_mod.derived_level_for(required + 1, THRESHOLDS),
                    index + 1,
                )

    def test_experience_below_the_first_threshold(self) -> None:
        """A curve whose floor is above zero: there is no level below it, so the
        derivation returns ``None`` rather than inventing level 1."""
        ladder = [40, 60, 100]
        for exp in (0, 1, 39):
            with self.subTest(exp=exp):
                self.assertIsNone(envelope_mod.derived_level_for(exp, ladder))
                self.assertIsNone(envelope_mod.next_threshold(exp, ladder))
                self.assertIsNone(envelope_mod.remaining_for(exp, ladder))
        # Exactly on the floor places level 1; between the first and second
        # rungs it advances to 2; the third rung's threshold is level 3.
        self.assertEqual(envelope_mod.derived_level_for(40, ladder), 1)
        self.assertEqual(envelope_mod.derived_level_for(59, ladder), 1)
        self.assertEqual(envelope_mod.derived_level_for(60, ladder), 2)
        self.assertEqual(envelope_mod.derived_level_for(99, ladder), 2)
        self.assertEqual(envelope_mod.derived_level_for(100, ladder), 3)
        # And the committed curve's own floor is 0, so a real save always places.
        self.assertEqual(THRESHOLDS[0], 0)
        for exp in (0, 1, 4, 39):
            with self.subTest(committed=exp):
                self.assertEqual(
                    envelope_mod.derived_level_for(exp, THRESHOLDS), 1
                )

    def test_experience_above_the_final_threshold_does_not_raise(self) -> None:
        """The upper edge refuses **gracefully**: the top level derives, and there
        is simply no next level."""
        final = envelope_mod.COMMITTED_FINAL_THRESHOLD
        for exp in (final, final + 1, final * 2, 10 ** 15, 2 ** 62):
            with self.subTest(exp=exp):
                self.assertEqual(
                    envelope_mod.derived_level_for(exp, THRESHOLDS), 100
                )
                self.assertIsNone(envelope_mod.next_threshold(exp, THRESHOLDS))
                self.assertIsNone(envelope_mod.remaining_for(exp, THRESHOLDS))
        # Exactly on the final threshold is the last rung that has no successor.
        self.assertEqual(envelope_mod.derived_level_for(final, THRESHOLDS), 100)
        self.assertEqual(envelope_mod.threshold_for(100, THRESHOLDS), final)

    def test_every_rung_of_the_whole_committed_curve_agrees_on_both_sides(self) -> None:
        """The complete sweep: for every entry, the experience exactly at its
        threshold derives that entry's level, and one less never does."""
        for index, required in enumerate(THRESHOLDS):
            with self.subTest(index=index):
                level = envelope_mod.level_for_entry_index(index)
                assert level is not None
                self.assertEqual(
                    envelope_mod.derived_level_for(required, THRESHOLDS), level
                )
                if required > 0:
                    self.assertLess(
                        envelope_mod.derived_level_for(required - 1, THRESHOLDS),  # type: ignore[arg-type]
                        level,
                    )

    def test_the_corpus_case_is_the_regression_fixture(self) -> None:
        """The corpus's own ``xp 4 / level 1`` pair, as a regression."""
        self.assertEqual(FRESH_MAP["xp"], 4)
        self.assertEqual(FRESH_MAP["level"], 1)
        self.assertEqual(
            envelope_mod.derived_level_for(FRESH_MAP["xp"], THRESHOLDS),
            FRESH_MAP["level"],
        )
        self.assertEqual(envelope_mod.COMMITTED_CORPUS_XP, 4)
        self.assertEqual(envelope_mod.COMMITTED_CORPUS_LEVEL, 1)
        # And its progress figure: the next level waits for 40, so 36 remain.
        self.assertEqual(envelope_mod.next_threshold(4, THRESHOLDS), 40)
        self.assertEqual(envelope_mod.remaining_for(4, THRESHOLDS), 36)

    def test_next_threshold_and_remaining_at_every_boundary(self) -> None:
        for index in range(len(THRESHOLDS) - 1):
            current = THRESHOLDS[index]
            following = THRESHOLDS[index + 1]
            with self.subTest(index=index):
                self.assertEqual(
                    envelope_mod.next_threshold(current, THRESHOLDS), following
                )
                self.assertEqual(
                    envelope_mod.remaining_for(current, THRESHOLDS),
                    following - current,
                )
                # ``remaining`` is never negative: an experience at or past a
                # threshold has already reached that level.
                # At the final rung the experience has already reached the top
                # of the curve, so there is no next level and no remaining.
                if index + 2 < len(THRESHOLDS):
                    self.assertEqual(
                        envelope_mod.remaining_for(following, THRESHOLDS),
                        THRESHOLDS[index + 2] - following,
                    )
                else:
                    self.assertIsNone(
                        envelope_mod.next_threshold(following, THRESHOLDS)
                    )
                    self.assertIsNone(
                        envelope_mod.remaining_for(following, THRESHOLDS)
                    )

    def test_a_non_integer_experience_fails_closed(self) -> None:
        """``True`` is an ``int`` in Python, so a boolean would silently place a
        player at level 2."""
        for bad in ("4", 4.0, True, None, [4], {"xp": 4}):
            with self.subTest(exp=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.derived_level_for(bad, THRESHOLDS)
                self.assertEqual(caught.exception.code, "invalid_exp")
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.next_threshold(bad, THRESHOLDS)
                self.assertEqual(caught.exception.code, "invalid_exp")
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.remaining_for(bad, THRESHOLDS)
                self.assertEqual(caught.exception.code, "invalid_exp")

    def test_an_empty_ladder_fails_closed(self) -> None:
        for call in (
            envelope_mod.derived_level_for,
            envelope_mod.threshold_for,
            envelope_mod.next_threshold,
            envelope_mod.remaining_for,
        ):
            with self.subTest(helper=call.__name__):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    call(1, [])
                self.assertEqual(caught.exception.code, "unknown_level")


class NeutralVectorTests(unittest.TestCase):
    """Design D5: a level-up moves no resource, so the vector is all zeros."""

    def test_the_neutral_vector_is_eight_zeros(self) -> None:
        vector = envelope_mod.neutral_vector()
        self.assertEqual(vector, [0] * 8)
        self.assertEqual(len(vector), envelope_mod.RESOURCE_VECTOR_SLOTS)
        for slot, value in enumerate(vector):
            with self.subTest(slot=slot):
                self.assertEqual(value, 0)

    def test_each_call_returns_a_fresh_list(self) -> None:
        first = envelope_mod.neutral_vector()
        first[2] = 999999
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)

    def test_validation_passes_only_the_neutral_vector(self) -> None:
        self.assertEqual(envelope_mod.validate_vector([0] * 8), [0] * 8)
        checked = envelope_mod.validate_vector([0] * 8)
        self.assertIsNot(checked, envelope_mod.ALWAYS_ZERO_SLOTS)
        self.assertEqual(checked, [0] * 8)

    def test_every_nonzero_slot_is_refused(self) -> None:
        """A positive slot is a client-trusted **mint** and a negative one a
        client-trusted **burn**; the derivation cannot express either, which is
        what forecloses the smuggling."""
        for slot in range(8):
            for value in (1, -1, 2500, -2500):
                vector = [0] * 8
                vector[slot] = value
                with self.subTest(slot=slot, value=value):
                    with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                        envelope_mod.validate_vector(vector)
                    self.assertEqual(caught.exception.code, "invalid_vector")

    def test_a_malformed_vector_fails_closed(self) -> None:
        cases: List[Any] = [
            None,
            [0] * 7,
            [0] * 9,
            "00000000",
            (0,) * 8,
            {"vector": [0] * 8},
            [0, 3.0, 0, 0, 0, 0, 0, 0],
            [0, True, 0, 0, 0, 0, 0, 0],
        ]
        for vector in cases:
            with self.subTest(vector=vector):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.validate_vector(vector)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_the_committed_rewards_are_never_turned_into_a_payout(self) -> None:
        """Design D7: the committed ``reward_type`` / ``reward_amount`` are
        consumed by no legacy branch, so no vector derived from them may exist —
        even for the richest committed reward row."""
        richest = max(CURVE, key=lambda row: int(row["reward_amount"]))
        self.assertEqual(richest["reward_amount"], 250)
        self.assertIn(richest["reward_type"], {"s", "w", "g", "c"})
        self.assertEqual(envelope_mod.neutral_vector(), [0] * 8)
        # The module has no helper that maps a reward onto a vector slot.
        for foreign in (
            "reward_vector_for",
            "payout_for_level",
            "reward_for",
            "resource_vector_for",
        ):
            with self.subTest(helper=foreign):
                self.assertFalse(hasattr(envelope_mod, foreign))


class BuildEnvelopeTests(unittest.TestCase):
    """The six keys and exactly one command, with the neutral vector."""

    def build(self, **overrides: Any) -> Dict[str, Any]:
        arguments: Dict[str, Any] = {
            "level": capture.FIXTURE_DERIVED_LEVEL,
            "ts": 1700000000,
        }
        arguments.update(overrides)
        return envelope_mod.build_envelope(**arguments)

    def test_the_envelope_has_exactly_the_six_legacy_keys(self) -> None:
        built = self.build()
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        self.assertEqual(built["first_number"], 0)
        self.assertEqual(built["publishActions"], [])
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(built["tries"], 1)
        self.assertEqual(built["accessToken"], "")

    def test_the_batch_carries_exactly_one_level_up_command(self) -> None:
        commands = self.build()["commands"]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0], 0)
        self.assertEqual(commands[0][1], "level_up")

    def test_the_argument_list_is_exactly_the_one_the_branch_reads(self) -> None:
        # command.py:82 binds a single positional arg.
        args = self.build()["commands"][0][2]
        self.assertEqual(args, [capture.FIXTURE_DERIVED_LEVEL])
        self.assertEqual(len(args), 1)

    def test_the_command_carries_the_neutral_vector_by_default(self) -> None:
        self.assertEqual(self.build()["commands"][0][3], [0] * 8)
        # …and a supplied neutral vector is accepted identically.
        self.assertEqual(
            self.build(vector=[0] * 8)["commands"][0][3], [0] * 8
        )

    def test_any_level_of_at_least_one_is_accepted(self) -> None:
        """The range check is the endpoint's job, not the derivation's:
        legacy's ``level_up`` assigns whatever integer it is given."""
        for level in (1, 2, 35, 99, 100, 10 ** 9):
            with self.subTest(level=level):
                self.assertEqual(self.build(level=level)["commands"][0][2], [level])

    def test_ts_defaults_to_current_time(self) -> None:
        before = int(time.time())
        built = envelope_mod.build_envelope(level=capture.FIXTURE_DERIVED_LEVEL)
        after = int(time.time())
        self.assertGreaterEqual(built["ts"], before)
        self.assertLessEqual(built["ts"], after)

    def test_a_non_integer_level_fails_closed(self) -> None:
        for bad in ("1", 1.0, True, None, [1], {"level": 1}):
            with self.subTest(level=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(level=bad)
                self.assertEqual(caught.exception.code, "invalid_level")

    def test_a_level_below_one_is_refused_before_it_reaches_legacy(self) -> None:
        """The graceful-refusal edge of the conversion is still a **hard refusal**
        in the envelope: legacy would assign the value verbatim, so this contract
        never sends it.  ``entry_index_for_level`` returns ``None`` for it; the
        builder refuses it outright."""
        for bad in (0, -1, -(10 ** 9)):
            with self.subTest(level=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(level=bad)
                self.assertEqual(caught.exception.code, "invalid_level")
                self.assertIn("at least 1", str(caught.exception))

    def test_a_bad_timestamp_fails_closed(self) -> None:
        for bad in (-1, "1700000000", True, 1700000000.0):
            with self.subTest(ts=bad):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(ts=bad)
                self.assertEqual(caught.exception.code, "invalid_timestamp")

    def test_a_smuggling_vector_fails_closed(self) -> None:
        """Design D5: the builder refuses any non-neutral vector, so the
        endpoint cannot send one even by mistake."""
        for vector in (
            [0] * 7,
            [0] * 9,
            [0, 500, 0, 0, 0, 0, 0, 0],  # an experience credit
            [0, 0, 999999, 0, 0, 0, 0, 0],  # a gold mint
            [0, 0, 0, 0, 0, 0, 0, -250],  # a mana burn
        ):
            with self.subTest(vector=vector):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    self.build(vector=vector)
                self.assertEqual(caught.exception.code, "invalid_vector")

    def test_the_level_is_validated_before_the_vector(self) -> None:
        with self.assertRaises(envelope_mod.EnvelopeError) as caught:
            self.build(level="1", vector=[0, 1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(caught.exception.code, "invalid_level")


class SharedSerializationTests(unittest.TestCase):
    """The single-command envelope travels through the unchanged helpers."""

    def test_roundtrip_through_the_legacy_field_format(self) -> None:
        built = envelope_mod.build_envelope(
            level=capture.FIXTURE_DERIVED_LEVEL, ts=1700000000
        )
        data = envelope_mod.data_field(built)
        self.assertEqual(len(data.split(";", 1)[0]), 64)
        self.assertEqual(data[64], ";")
        self.assertEqual(envelope_mod.parse_data_field(data), built)

    def test_serialization_is_deterministic(self) -> None:
        built = envelope_mod.build_envelope(
            level=capture.FIXTURE_DERIVED_LEVEL, ts=1700000000
        )
        first = envelope_mod.payload_json(built)
        second = envelope_mod.payload_json(built)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith('{"accessToken":"","commands":['))

    def test_the_payload_carries_exactly_the_established_command(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        payload = json.loads(envelope_mod.data_field(built)[65:])
        self.assertEqual(
            payload["commands"],
            [[0, "level_up", [1], [0, 0, 0, 0, 0, 0, 0, 0]]],
        )
        self.assertEqual(payload["first_number"], 0)
        self.assertEqual(payload["publishActions"], [])
        self.assertEqual(payload["tries"], 1)
        self.assertEqual(payload["accessToken"], "")

    def test_malformed_fields_fail_closed(self) -> None:
        good = envelope_mod.data_field(
            capture.build_fixture_envelope(ts=1700000000)
        )
        broken = [
            good[65:],
            "x" + good[1:],
            good[:64] + ":" + good[65:],
            good[:64] + ";" + "{not json",
            good[:64] + ";" + "[1,2]",
            good[:64] + ";" + '{"commands": []}',
            "ab" + good[2:],
        ]
        for data in broken:
            with self.subTest(data=data[:40]):
                with self.assertRaises(envelope_mod.EnvelopeError) as caught:
                    envelope_mod.parse_data_field(data)
                self.assertEqual(caught.exception.code, "invalid_data_field")


class NoGameplayValidationTests(unittest.TestCase):
    """Design D7: no tuning, no rewards, no unit experience, no grid."""

    def test_the_module_reads_no_grid_constant_but_the_re_export(self) -> None:
        self.assertEqual(envelope_mod.GRID_EXTENT, 100)
        self.assertTrue(envelope_mod.in_grid(0, 0))
        # The executable body never mentions either — asserted against the AST,
        # so the docstrings that *name* the gap do not count as behaviour.
        tree = ast.parse(Path(envelope_mod.__file__).read_text(encoding="utf-8"))
        code_names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
        for forbidden in ("GRID_EXTENT", "in_grid"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)

    def test_no_executable_name_is_a_reward_or_unit_experience_concept(self) -> None:
        """Design D7: nothing in the module can pay a reward or grant unit
        experience — the vocabularies are named in prose and in ``__all__``-free
        constants, never in behaviour."""
        tree = ast.parse(Path(envelope_mod.__file__).read_text(encoding="utf-8"))
        code_names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
            elif isinstance(node, ast.arg):
                code_names.append(node.arg)
        for forbidden in (
            "reward",
            "reward_type",
            "reward_amount",
            "payout",
            "unit_xp",
            "add_xp_unit",
            "tutorial",
            "complete_tutorial",
            "rebalance",
            "interpolate",
            "smooth",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)

    def test_the_committed_curve_is_never_rewritten(self) -> None:
        """Design D7 asserted on the data itself: the derivation reads the
        committed thresholds verbatim and the curve is not modified."""
        before = json.loads(json.dumps(CURVE))
        for exp in (0, 4, 40, 100, 2016089205):
            envelope_mod.derived_level_for(exp, THRESHOLDS)
        self.assertEqual(CURVE, before)

    def test_the_endpoint_route_contains_no_reward_or_unit_experience_logic(self) -> None:
        import compat_service

        source = Path(compat_service.__file__).read_text(encoding="utf-8")
        route = source[source.index("def v0_level_up()"):]
        route = route[: route.index('app.config["COMPAT_LEGACY_CORPUS"]')]
        import textwrap

        code_names: List[str] = []
        for node in ast.walk(ast.parse(textwrap.dedent(route.lstrip("\n")))):
            if isinstance(node, ast.Name):
                code_names.append(node.id)
            elif isinstance(node, ast.Attribute):
                code_names.append(node.attr)
        for forbidden in (
            "reward_type",
            "reward_amount",
            "payout",
            "add_xp_unit",
            "tutorial",
            "item_index",
            "in_grid",
            "GRID_EXTENT",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code_names)
        # …while the route's own docstring states the boundary.
        for named in ("Design D7", "unit experience", "reward"):
            with self.subTest(named=named):
                self.assertIn(named, route)


class RealConfigCrossCheckTests(unittest.TestCase):
    """The committed config and seed must satisfy every closed assumption."""

    def test_the_committed_curve_census_matches_the_investigation(self) -> None:
        """docs/legacy-xp-basics.md and the committed tables package."""
        self.assertEqual(len(CURVE), 100)
        self.assertEqual(
            sorted(CURVE[0]),
            ["exp_required", "name", "reward_amount", "reward_type"],
        )
        # Two numeric fields (native numbers, never strings) and two string
        # fields — the census's own per-field profile.
        for row in CURVE:
            for field in ("exp_required", "reward_amount"):
                with self.subTest(field=field):
                    self.assertIsInstance(row[field], int)  # type: ignore[index]
                    self.assertNotIsInstance(row[field], bool)  # type: ignore[index]
            for field in ("name", "reward_type"):
                with self.subTest(field=field):
                    self.assertIsInstance(row[field], str)  # type: ignore[index]
                    self.assertNotIsInstance(row[field], bool)  # type: ignore[index]
            self.assertGreaterEqual(row["exp_required"], 0)  # type: ignore[index]
            self.assertGreater(row["reward_amount"], 0)  # type: ignore[index]
            self.assertIn(row["reward_type"], {"s", "w", "g", "c"})  # type: ignore[index]
        self.assertEqual(
            [row["exp_required"] for row in CURVE[:8]],
            list(envelope_mod.COMMITTED_FIRST_THRESHOLDS),
        )
        self.assertEqual(
            CURVE[-1]["exp_required"], envelope_mod.COMMITTED_FINAL_THRESHOLD
        )
        self.assertEqual(CURVE[-1]["name"], "Conqueror")

    def test_the_reward_vocabularies_match_the_committed_census(self) -> None:
        self.assertEqual(
            sorted({row["reward_type"] for row in CURVE}),
            list(envelope_mod.COMMITTED_REWARD_TYPES),
        )
        self.assertEqual(
            sorted({row["reward_amount"] for row in CURVE}),
            list(envelope_mod.COMMITTED_REWARD_AMOUNTS),
        )
        # The letter vocabulary is drawn from the SAME set items[].costs uses —
        # not the server's resource names.  It is a strict **subset** of that
        # set: the curve never names oil, so ``o`` appears in costs but in no
        # level entry.
        costs_vocabulary = set()
        for item in CONFIG["items"]:
            raw = item.get("costs")
            if isinstance(raw, str) and raw:
                costs_vocabulary.update(json.loads(raw).keys())
        rewards = {row["reward_type"] for row in CURVE}
        self.assertTrue(rewards <= costs_vocabulary)
        self.assertEqual(rewards, {"s", "w", "g", "c"})
        self.assertNotIn("o", rewards)
        # …and none of them is a server resource name.
        self.assertFalse(rewards & {"gold", "wood", "oil", "steel", "cash", "mana", "xp"})

    def test_the_name_is_a_label_not_an_identifier(self) -> None:
        names = {row["name"] for row in CURVE}
        self.assertEqual(len(names), envelope_mod.COMMITTED_DISTINCT_NAMES)
        self.assertLess(len(names), len(CURVE))
        # Every entry from level 49 onward is the same label.
        self.assertEqual(
            {row["name"] for row in CURVE[48:]}, {"Conqueror"}
        )

    def test_the_fresh_save_carries_the_committed_progression_facts(self) -> None:
        self.assertEqual(FRESH_MAP["xp"], capture.FIXTURE_EXPECTED_XP)
        self.assertEqual(FRESH_MAP["xp"], envelope_mod.COMMITTED_CORPUS_XP)
        self.assertEqual(
            FRESH_MAP["level"], capture.FIXTURE_EXPECTED_LEVEL_BEFORE
        )
        self.assertEqual(FRESH_MAP["level"], envelope_mod.COMMITTED_CORPUS_LEVEL)
        self.assertEqual(len(FRESH_MAP["items"]), 40)
        self.assertEqual(len(FRESH_MAP["items"]), envelope_mod.COMMITTED_CORPUS_PLACEMENTS)
        self.assertEqual(FRESH_MAP["store"], {})
        self.assertNotIn("map_sizes", FRESH_MAP)
        self.assertEqual(FRESH_MAP["increasedPopulation"], 0)
        self.assertEqual(
            [FRESH_MAP[name] for name in ("gold", "wood", "oil", "steel")],
            [2000, 2000, 2000, 2000],
        )
        self.assertEqual(SEED["playerInfo"]["cash"], 5)  # type: ignore[index]
        self.assertEqual(SEED["privateState"]["mana"], 0)  # type: ignore[index]

    def test_the_pre_migration_save_carries_the_same_progression_facts(self) -> None:
        """The progression facts are part of the preserved corpus, not migration
        damage."""
        pre = json.loads(
            (harness.REPO_ROOT / "tests" / "saves" / "fresh-player-pre-migration.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(pre["maps"][0]["xp"], capture.FIXTURE_EXPECTED_XP)  # type: ignore[index]
        self.assertEqual(
            pre["maps"][0]["level"], capture.FIXTURE_EXPECTED_LEVEL_BEFORE  # type: ignore[index]
        )

    def test_no_committed_placement_row_carries_unit_experience(self) -> None:
        """Design D7's reason for excluding unit XP: the corpus cannot exercise
        ``add_xp_unit``."""
        with_xp = [
            key
            for key, row in FRESH_MAP["items"].items()
            if isinstance(row[6], dict) and "xp" in row[6]
        ]
        self.assertEqual(with_xp, [])
        self.assertEqual(len(FRESH_MAP["items"]), 40)

    def test_the_fixture_derives_the_documented_level(self) -> None:
        self.assertEqual(
            capture.derive_fixture_level(), capture.FIXTURE_DERIVED_LEVEL
        )
        self.assertEqual(capture.derive_fixture_level(), 1)
        self.assertEqual(capture.FIXTURE_EXPECTED_LEVEL_AFTER, 1)
        # The corpus's own level equals the derived one, which is the recorded
        # reason the transaction writes an identical value.
        self.assertEqual(
            capture.FIXTURE_EXPECTED_LEVEL_BEFORE, capture.FIXTURE_DERIVED_LEVEL
        )

    def test_the_fixture_resources_are_the_committed_ones(self) -> None:
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_BEFORE,
            {
                "xp": 4,
                "gold": 2000,
                "wood": 2000,
                "oil": 2000,
                "steel": 2000,
                "cash": 5,
                "mana": 0,
            },
        )
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_AFTER,
            capture.FIXTURE_EXPECTED_RESOURCE_BEFORE,
        )
        self.assertEqual(
            capture.FIXTURE_EXPECTED_RESOURCE_DELTA,
            {"xp": 0, "gold": 0, "wood": 0, "oil": 0, "steel": 0, "cash": 0, "mana": 0},
        )
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)

    def test_the_fixture_does_not_touch_another_fixtures_rows(self) -> None:
        """Every delivered fixture stays independently readable: a level-up
        rewrites no placement at all."""
        for key in ("2", "11", "12", "20", "21"):
            with self.subTest(key=key):
                self.assertIn(key, FRESH_MAP["items"])
        self.assertEqual(int(FRESH_MAP["items"]["2"][0]), 905)
        self.assertEqual(int(FRESH_MAP["items"]["11"][0]), 22)
        self.assertEqual(int(FRESH_MAP["items"]["12"][0]), 23)
        self.assertEqual(int(FRESH_MAP["items"]["20"][0]), 22)

    def test_the_command_catalog_records_the_established_branch(self) -> None:
        """docs/legacy-protocol/commands.json states the same: the branch assigns
        a client integer and verifies nothing."""
        catalog = json.loads(
            (harness.REPO_ROOT / "docs" / "legacy-protocol" / "commands.json").read_text(
                encoding="utf-8"
            )
        )
        entry = {item["name"]: item for item in catalog["commands"]}["level_up"]
        self.assertEqual(entry["classification"], "handled")
        self.assertEqual(entry["domain"], "progression")
        self.assertEqual(entry["args"]["shape"], "exactly 1 positional arg")
        self.assertEqual(entry["args"]["positional"], ["args[0] new_level (int)"])
        self.assertEqual(entry["state_reads"], ["map[level]"])
        self.assertEqual(
            entry["state_writes"],
            ["map[level] = new_level with no range or XP validation"],
        )
        self.assertEqual(entry["client_trust"], ["new_level value", "resources_changed deltas"])
        self.assertIn("resources_changed deltas", " ".join(entry["client_trust"]))
        security = " ".join(entry["security_notes"])
        self.assertIn("Client sets the map level directly", security)
        self.assertIn("not verified server-side", security)
        # The catalog records that the curve is not read either.
        for absent in ("levels", "exp_required", "xp", "reward"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, " ".join(entry["state_writes"]))

    def test_the_committed_source_writes_only_the_level(self) -> None:
        """The branch itself, read from the preserved source."""
        source = (harness.REPO_ROOT / "command.py").read_text(encoding="utf-8")
        start = source.index('elif cmd == "level_up":')
        branch = source[start + len('elif cmd == "level_up":'):]
        branch = branch[: branch.index("elif cmd ==")]
        self.assertIn("map[\"level\"] = new_level", branch)
        # The branch reads no curve, coerces nothing, and checks no range.  The
        # tokens are matched with a leading boundary so ``print(`` does not read
        # as ``int(``.
        for absent in ("exp_required", "levels", "int(", "range(", "max(", "xp"):
            with self.subTest(absent=absent):
                self.assertNotRegex(branch, r"(?<![A-Za-z_])" + re.escape(absent))
        # It writes exactly one assignment and nothing else.
        self.assertEqual(branch.count("map["), 1)


class CaptureContractTests(unittest.TestCase):
    """The capture tool's published constants match the verified facts."""

    def test_fixture_intent_is_the_documented_one(self) -> None:
        self.assertEqual(capture.FIXTURE_EXPECTED_XP, 4)
        self.assertEqual(capture.FIXTURE_EXPECTED_LEVEL_BEFORE, 1)
        self.assertEqual(capture.FIXTURE_DERIVED_LEVEL, 1)
        self.assertEqual(capture.FIXTURE_EXPECTED_LEVEL_AFTER, 1)
        self.assertEqual(capture.FIXTURE_SCHEDULE_LENGTH, 100)
        self.assertEqual(
            capture.FIXTURE_FIRST_THRESHOLDS,
            (0, 40, 60, 100, 200, 350, 550, 800),
        )
        self.assertEqual(capture.FIXTURE_FINAL_THRESHOLD, 2016089205)
        self.assertEqual(capture.FIXTURE_EXPECTED_VECTOR, [0] * 8)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_BEFORE, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_PLACEMENTS_AFTER, 40)
        self.assertEqual(capture.FIXTURE_EXPECTED_INCREASED_POPULATION, 0)
        self.assertFalse(capture.FIXTURE_EXPECTED_MAP_SIZES_PRESENT)
        self.assertIn("one-based", capture.TARGET_RULE)
        self.assertIn("level_already_current", capture.TARGET_RULE)
        self.assertIn("probe 1", capture.TARGET_RULE)

    def test_step_names_are_the_committed_ones(self) -> None:
        self.assertEqual(capture.STEPS, ("login_post", "command_level_up"))

    def test_output_directory_is_the_committed_fixture_path(self) -> None:
        self.assertEqual(
            capture.DEFAULT_OUT,
            harness.REPO_ROOT / "tests" / "fixtures" / "godot-building-xp",
        )

    def test_the_config_resolvers_apply_the_documented_rules(self) -> None:
        self.assertEqual(len(capture.config_level_entries()), 100)
        self.assertEqual(capture.config_level_entry(0)["name"], "Slave")  # type: ignore[index]
        self.assertEqual(capture.config_level_entry(1)["name"], "Servant")  # type: ignore[index]
        self.assertEqual(capture.config_thresholds()[:4], [0, 40, 60, 100])
        self.assertEqual(capture.config_thresholds()[-1], 2016089205)

    def test_the_fixture_batch_is_the_derived_single_command(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        self.assertEqual(built["ts"], 1700000000)
        self.assertEqual(
            built["commands"], [[0, "level_up", [1], [0, 0, 0, 0, 0, 0, 0, 0]]]
        )
        self.assertEqual(sorted(built), sorted(envelope_mod.ENVELOPE_KEYS))
        capture.verify_envelope(built)

    def test_the_batch_is_composed_from_the_shared_derivation(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        rebuilt = envelope_mod.build_envelope(
            level=capture.derive_fixture_level(),
            vector=envelope_mod.neutral_vector(),
            ts=1700000000,
        )
        self.assertEqual(built, rebuilt)
        self.assertEqual(built["commands"][0][3], envelope_mod.neutral_vector())

    def test_protected_fixtures_are_the_ten_committed_ones(self) -> None:
        self.assertEqual(
            [relative for relative, _label in capture.PROTECTED_FIXTURES],
            [
                "tests/fixtures/godot-compatibility-boot",
                "tests/fixtures/godot-building-placement",
                "tests/fixtures/godot-item-purchase",
                "tests/fixtures/godot-building-move",
                "tests/fixtures/godot-building-sell",
                "tests/fixtures/godot-building-store",
                "tests/fixtures/godot-building-upgrade",
                "tests/fixtures/godot-building-construction",
                "tests/fixtures/godot-building-collect",
                "tests/fixtures/godot-building-expand",
            ],
        )
        for relative, _label in capture.PROTECTED_FIXTURES:
            with self.subTest(relative=relative):
                self.assertTrue((harness.REPO_ROOT / relative).is_dir())

    def test_envelope_verification_rejects_a_drifted_shape(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        cases: Dict[str, Any] = {
            "no command": lambda env: env["commands"].pop(),
            "two commands": lambda env: env["commands"].append(list(env["commands"][0])),
            "another level": lambda env: env["commands"][0][2].__setitem__(0, 2),
            "an extra argument": lambda env: env["commands"][0][2].append(0),
            "another command name": lambda env: env["commands"][0].__setitem__(1, "buy"),
            "a level below one": lambda env: env["commands"][0][2].__setitem__(0, 0),
            "an experience credit": lambda env: env["commands"][0][3].__setitem__(1, 500),
            "a gold mint": lambda env: env["commands"][0][3].__setitem__(2, 2500),
            "a gold burn": lambda env: env["commands"][0][3].__setitem__(2, -2500),
            "another map id": lambda env: env["commands"][0].__setitem__(0, 1),
            "extra envelope keys": lambda env: env.__setitem__("extra", 1),
        }
        for label, mutate in sorted(cases.items()):
            with self.subTest(case=label):
                drifted = json.loads(json.dumps(built))
                mutate(drifted)
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_envelope(drifted)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_the_probe_is_recorded_with_its_evidence(self) -> None:
        """Probe 1 is what makes the "nothing moved" proof real rather than a
        tautology: it executes a client-sent vector through this very branch."""
        self.assertEqual(len(capture.PROBES), 1)
        probe = capture.PROBES[0]
        self.assertEqual(probe["probe"], 1)
        self.assertTrue(probe["executed_in_this_capture"])
        self.assertIn("level_up([2])", probe["commands"][0])
        self.assertIn("[0, 500, 0, 0, 0, 0, 0, 0]", probe["commands"][0])
        self.assertEqual(probe["level_before"], 1)
        self.assertEqual(probe["level_after"], 2)
        self.assertEqual(probe["xp_before"], 4)
        self.assertEqual(probe["xp_after"], 504)
        self.assertEqual(probe["changed_top_level_map_keys"], ["level", "xp"])
        self.assertIn("command.py:81-85", probe["established"])
        self.assertIn("engine.py:251-271", probe["established"])
        self.assertIn("resource-minting exploit", probe["why_it_matters"])
        self.assertIn("tautology", probe["why_it_matters"])
        self.assertEqual(
            capture.build_probe_envelope(ts=1700000000)["commands"],
            [[0, "level_up", [2], [0, 500, 0, 0, 0, 0, 0, 0]]],
        )

    def test_time_dependent_fields_are_named_and_the_state_has_none(self) -> None:
        source = Path(capture.__file__).read_text(encoding="utf-8")
        self.assertIn('"time_dependent_fields"', source)
        self.assertIn('"state_leaves": []', source)
        self.assertIn("exactly these 8 paths", source)
        self.assertIn("/executed_at_utc in capture-manifest.json", source)

    def test_transaction_verification_accepts_the_recorded_after_state(self) -> None:
        """The recorded outcome: the level equals the derived value and nothing
        else moved."""
        built = capture.build_fixture_envelope(ts=1700000000)
        before = json.loads(json.dumps(SEED))
        after = json.loads(json.dumps(SEED))
        capture.verify_transaction(before, after, built)

    def test_transaction_verification_rejects_a_mismatched_after_state(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        cases: Dict[str, Any] = {
            "the level moved elsewhere": lambda: derived_level_state(level=2),
            "the level was cleared": lambda: derived_level_state(level=0),
            "the level disappeared": lambda: derived_level_state(drop_level=True),
            "a placement row changed": lambda: derived_level_state(
                item_cell=(54, 39)
            ),
            "a placement row was removed": lambda: derived_level_state(drop_item="12"),
            "a placement row appeared": lambda: derived_level_state(add_item="41"),
            "the storage changed": lambda: derived_level_state(store={"905": 1}),
            "map_sizes appeared": lambda: derived_level_state(map_sizes=[0]),
            "a private-state field changed": lambda: derived_level_state(bought=[905]),
            "deadHeroes changed": lambda: derived_level_state(
                dead_heroes={"905": True}
            ),
            "playerInfo changed": lambda: derived_level_state(cash=4),
            "the experience moved": lambda: derived_level_state(xp=5),
            "gold moved": lambda: derived_level_state(gold=1999),
            "wood moved": lambda: derived_level_state(wood=2001),
            "mana moved": lambda: derived_level_state(mana=1),
        }
        for label, build in sorted(cases.items()):
            with self.subTest(case=label):
                before = json.loads(json.dumps(SEED))
                after = build()
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)

    def test_probe_verification_accepts_and_rejects_the_probe_outcomes(self) -> None:
        """The probe's structural check accepts the outcome it documents and
        rejects one where the branch wrote nothing else."""
        built = capture.build_probe_envelope(ts=1700000000)
        before = json.loads(json.dumps(SEED))
        good = probe_state(level=2, xp=504)
        facts = capture.verify_probe_transaction(before, good, built)
        self.assertEqual(facts["level_before"], 1)
        self.assertEqual(facts["level_after"], 2)
        self.assertEqual(facts["xp_after"], 504)
        self.assertEqual(facts["changed_top_level_map_keys"], ["level", "xp"])
        self.assertEqual(facts["leaf_differences"], ["/maps/0/level", "/maps/0/xp"])
        rejected = {
            "the level did not move": probe_state(level=1, xp=504),
            "the experience did not move": probe_state(level=2, xp=4),
            "a placement moved": probe_state(level=2, xp=504, item_cell=(54, 39)),
            "the store changed": probe_state(level=2, xp=504, store={"905": 1}),
        }
        for label, after in sorted(rejected.items()):
            with self.subTest(case=label):
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.verify_probe_transaction(before, after, built)
                self.assertEqual(caught.exception.exit_code, capture.EXIT_REQUEST)


def derived_level_state(
    level: int = 1,
    drop_level: bool = False,
    item_cell: Optional[Any] = None,
    drop_item: Optional[str] = None,
    add_item: Optional[str] = None,
    store: Optional[Dict[str, int]] = None,
    map_sizes: Optional[List[int]] = None,
    gold: int = 2000,
    cash: int = 5,
    xp: int = 4,
    mana: int = 0,
    wood: int = 2000,
    bought: Optional[List[int]] = None,
    dead_heroes: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """A fresh-save copy carrying the recorded after-state, overridable.

    Defaults are the executed outcome — ``maps[0].level`` equal to the derived
    value and every other byte the committed seed's — so every override in the
    mismatch table names exactly one deviation from it.
    """
    document = json.loads(json.dumps(SEED))
    first_map = document["maps"][0]
    if drop_level:
        first_map.pop("level")
    else:
        first_map["level"] = level
    if item_cell is not None:
        first_map["items"]["2"][1] = item_cell[0]
        first_map["items"]["2"][2] = item_cell[1]
    if drop_item is not None:
        first_map["items"].pop(drop_item, None)
    if add_item is not None:
        first_map["items"][add_item] = [22, 10, 10, 0, 0, [], {}, 1]
    if store is not None:
        first_map["store"] = dict(store)
    if map_sizes is not None:
        first_map["map_sizes"] = list(map_sizes)
    first_map["gold"] = gold
    first_map["wood"] = wood
    first_map["xp"] = xp
    document["playerInfo"]["cash"] = cash
    document["privateState"]["mana"] = mana
    if bought is not None:
        document["privateState"]["boughtUnits"] = list(bought)
    if dead_heroes is not None:
        document["privateState"]["deadHeroes"] = dict(dead_heroes)
    return document


def probe_state(
    level: int,
    xp: int,
    item_cell: Optional[Any] = None,
    store: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """A fresh-save copy carrying the probe's outcome, overridable."""
    document = json.loads(json.dumps(SEED))
    first_map = document["maps"][0]
    first_map["level"] = level
    first_map["xp"] = xp
    if item_cell is not None:
        first_map["items"]["2"][1] = item_cell[0]
        first_map["items"]["2"][2] = item_cell[1]
    if store is not None:
        first_map["store"] = dict(store)
    return document


class SanitizationTests(unittest.TestCase):
    """Recorded requests carry no user_key or token values."""

    def test_form_user_key_is_always_redacted(self) -> None:
        form = {"USERID": "pid", "user_key": "S3CRET", "language": "en"}
        sanitized = capture.sanitize_form(form)
        self.assertEqual(sanitized["user_key"], capture.REDACTED)
        self.assertEqual(sanitized["USERID"], "pid")
        self.assertNotIn("S3CRET", json.dumps(sanitized))

    def test_crafted_empty_token_keeps_the_exact_sent_bytes(self) -> None:
        data = envelope_mod.data_field(
            capture.build_fixture_envelope(ts=1700000000)
        )
        self.assertEqual(capture.sanitize_data_field(data), data)

    def test_non_empty_access_token_is_redacted_in_the_data_field(self) -> None:
        built = capture.build_fixture_envelope(ts=1700000000)
        built["accessToken"] = "TOKEN-SECRET"
        data = envelope_mod.data_field(built)
        record = capture.sanitize_data_field(data)
        self.assertNotIn("TOKEN-SECRET", record)
        parsed = envelope_mod.parse_data_field(record)
        self.assertEqual(parsed["accessToken"], capture.REDACTED)
        self.assertEqual(parsed["commands"], built["commands"])

    def test_session_cookie_headers_are_redacted_but_others_survive(self) -> None:
        headers = {
            "Date": "Mon, 30 Sep 2026 15:30:46 GMT",
            "Set-Cookie": "session=SESSION-TOKEN-SECRET; HttpOnly; Path=/",
            "Content-Type": "text/html; charset=utf-8",
        }
        sanitized = capture.sanitize_headers(headers)
        self.assertEqual(sanitized["Set-Cookie"], capture.REDACTED)
        self.assertEqual(sanitized["Date"], headers["Date"])
        self.assertNotIn("SESSION-TOKEN-SECRET", json.dumps(sanitized))


if __name__ == "__main__":
    unittest.main()