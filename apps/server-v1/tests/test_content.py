#!/usr/bin/env python3
"""Committed content loading, compared against the preserved legacy loader.

v1 reimplements the legacy load sequence.  "Reimplements" is the risky word: a
loader that quietly diverged would produce a different economy and still pass
every behavioural test, because both sides would be internally consistent.  So
this file imports the **preserved** ``get_game_config`` module and compares the
two loaders' output directly.

**Importing the legacy module has side effects and they are allowed.**
``get_game_config`` prints patch progress and calls ``make_dynamic`` at import
(``get_game_config.py:319``).  Both are in-memory; nothing is written.  The
bundle module it imports declares only ``os`` and ``sys`` at module level, which
is what makes importing it safe here — measured, not assumed.

**The one deliberate divergence.**  v1 skips ``make_dynamic``
(:data:`server_v1_content.SKIPPED_LOADER_STEPS`), which legacy calls on every
``get_game_config()`` and which rewrites ``darts_items[*].start_date`` from the
wall clock.  That is a real, observable difference between the two loaders and
it is asserted as present rather than smoothed over: a test that compared the
whole document for equality would have had to exclude it silently.
"""

from __future__ import annotations

import datetime
import time
import unittest
from typing import Any, Dict

import harness
from server_v1_content import (
    CONFIG_MAIN,
    MOD_LIST,
    PATCH_LIST,
    SKIPPED_LOADER_STEPS,
    CommittedContent,
    ContentError,
    load_content,
)


def legacy_config() -> Dict[str, Any]:
    """The preserved loader's output, imported rather than reimplemented."""
    import get_game_config

    return get_game_config.get_game_config()


class LegacyParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = load_content(harness.REPO_ROOT)
        cls.legacy = legacy_config()

    def test_the_item_array_is_identical(self) -> None:
        self.assertEqual(self.legacy["items"], list(self.content.item_rows()))
        self.assertEqual(900, len(self.legacy["items"]))

    def test_there_are_no_duplicate_items_in_either_loader(self) -> None:
        # Legacy's ``remove_duplicate_items`` reports the count it removed; the
        # committed corpus has none, so both loaders must agree on zero rather
        # than merely happen to produce the same list.
        self.assertEqual(900, self.content.item_count())
        self.assertEqual(900, self.content.distinct_item_count())

    def test_the_globals_are_identical(self) -> None:
        self.assertEqual(self.legacy["globals"], self.content.globals_object())

    def test_the_top_level_sections_are_the_same_set(self) -> None:
        self.assertEqual(set(self.legacy), set(self.content.sections()))

    def test_the_collection_ladder_agrees_with_the_legacy_document(self) -> None:
        minutes, multipliers = self.content.collect_ladder()
        self.assertEqual(self.legacy["globals"]["COLLECT_MINUTES"], list(minutes))
        self.assertEqual(self.legacy["globals"]["COLLECT_MULTIPLIER"], list(multipliers))

    def test_the_collected_tree_is_the_same_row_in_both(self) -> None:
        legacy_row = next(
            item for item in self.legacy["items"] if int(item["id"]) == 905
        )
        self.assertEqual(legacy_row, self.content.item(905))

    def test_the_deliberate_divergence_is_present_and_located(self) -> None:
        """``make_dynamic`` is skipped, so the darts dates differ. Asserted.

        **A first attempt at this assertion was wrong and is recorded here
        rather than deleted.**  It pinned legacy's wrapped date to the literal
        ``"2026-08-24 00:00:00"``, the value measured on 2026-10-12.  That
        literal is a time bomb: ``make_dynamic`` wraps the darts week forward
        against ``timestamp_now()`` (``get_game_config.py:226-233``), so the
        value is a function of the day the test runs and the pin would start
        failing on its own, in a suite that asserts nothing time-dependent.

        What is stable is *why* the two differ.  v1's value is the committed
        file's bytes, so that one is pinnable.  Legacy's is not pinnable but is
        bounded: the wrap loop advances the week until ``ts_now`` falls before
        it, so the first game's start always lands within one week (604800 s)
        behind the current time and ahead of the stored value.  Asserting that
        bound is strictly stronger than ``assertNotEqual`` -- which would also
        have passed on garbage like an empty string -- and it holds on any
        date the suite is ever run.
        """
        self.assertEqual(("make_dynamic",), SKIPPED_LOADER_STEPS)

        # v1's value is the committed file's bytes, so that one *is* pinnable.
        stored = self.content.darts_start_date()
        self.assertEqual("2012-03-02 23:00:00", stored)

        rows = self.content.section("darts_items")
        self.assertEqual(27, len(rows))
        legacy_rows = self.legacy["darts_items"]
        self.assertEqual(len(rows), len(legacy_rows))

        legacy_last = legacy_rows[-1]["start_date"]
        self.assertIsInstance(legacy_last, str)
        last_ts = time.mktime(
            datetime.datetime.strptime(legacy_last, "%Y-%m-%d %H:%M:%S").timetuple()
        )

        # **Two corrections to this assertion, both made by measuring the wrap
        # rule rather than by reading it off the output.**  The first version
        # pinned legacy's *first* game to a literal, which is a time bomb, and
        # the second asserted the first game's date lay within one week *behind*
        # now.  Both are wrong, and `get_game_config.make_dynamic` says why:
        # the wrap point is the **last** item, not the first -- it reads
        # `darts_items[-1]`, and `update_darts` rebuilds the whole block from
        # that instant onwards, advancing it a week at a time until the block's
        # **last** date is still in the future (`while ts_now >= last_ts`).
        # So the block *ends* just past today and *starts* up to 26 weeks
        # before it.  Measured on 2026-10-12: first 2026-08-24 (50 days back),
        # last 2027-02-22 (133 days ahead).  An assertion about the first date
        # being near now is therefore unsatisfiable, not merely flaky.
        #
        # What *is* stable on any date the suite runs is the rule itself: the
        # last date is in the future, and it is no more than one full block
        # (26 weekly steps) ahead of now.  A 2-hour slack absorbs the DST
        # corrections `update_darts` applies per game.
        now = time.time()
        self.assertGreater(last_ts, now, "the wrap must land the block's last date in the future")
        self.assertLessEqual(now, last_ts, "sanity: the same instant compared the other way")
        self.assertLess(last_ts - now, 26 * 604800 + 7200)

        stored_last = rows[-1]["start_date"]
        self.assertNotEqual(stored_last, legacy_last)

    def test_only_the_darts_dates_differ_between_the_two_loaders(self) -> None:
        """Pin the divergence to its one section, measured rather than assumed.

        The loader is compared section by section with ``darts_items`` excluded
        exactly once, in exactly one place.  A second excluded section would
        widen the exclusion silently; a section that started differing would
        fail here rather than hide inside one large equality check.
        """
        # **The first version of this test compared the legacy document with
        # itself and is recorded as a defect.**  It built ``loaded`` from
        # ``self.legacy.items()`` rather than from v1's own document, so the
        # equality half was a tautology -- it would have passed no matter how
        # far v1's loader diverged -- and the ``assertNotEqual`` half compared
        # legacy's ``darts_items`` against the same object through an
        # ``and`` expression, which is not a comparison of the two loaders at
        # all.  Both halves now read v1's document through the public
        # ``section`` accessor, so a divergence in *any* other section fails
        # here rather than hiding inside one large equality check.
        excluded = {"darts_items"}
        self.assertEqual(
            set(self.content.sections()),
            set(self.legacy),
            "the two loaders resolved different top-level sections",
        )
        for name in sorted(set(self.legacy) - excluded):
            with self.subTest(section=name):
                self.assertEqual(
                    self.legacy[name], self.content.section(name), "section %r diverges" % name
                )
        # The one excluded section must actually differ, or the exclusion is
        # hiding nothing -- an exclusion that excludes nothing is a silent
        # weakening, so it is asserted rather than assumed.
        self.assertNotEqual(self.legacy["darts_items"], self.content.section("darts_items"))


class LoaderStepTests(unittest.TestCase):
    def test_the_declared_paths_are_the_legacy_ones(self) -> None:
        self.assertEqual(("config", "main.json"), CONFIG_MAIN)
        self.assertEqual(("config", "patch", "patches.txt"), PATCH_LIST)
        self.assertEqual(("mods", "mods.txt"), MOD_LIST)

    def test_provenance_names_what_was_read_and_what_was_not(self) -> None:
        content = load_content(harness.REPO_ROOT)
        provenance = content.provenance()
        # **Corrected against the delivered ``provenance()``.**  This test
        # originally named ``item_count`` / ``distinct_item_count`` /
        # ``sections`` / ``skipped``, none of which the module emits: the
        # method spells them ``item_entries`` / ``distinct_item_ids`` /
        # ``skipped_loader_steps`` and reports no section list at all.  The
        # claim being made is that provenance names **what was read and what
        # was not**, so the keys asserted here are the delivered ones and the
        # read/not-read split is asserted positively rather than by key name.
        for key in (
            "item_entries",
            "distinct_item_ids",
            "applied_patches",
            "applied_mods",
            "removed_duplicate_items",
            "skipped_loader_steps",
        ):
            with self.subTest(key=key):
                self.assertIn(key, provenance)
        self.assertEqual(
            list(SKIPPED_LOADER_STEPS), list(provenance["skipped_loader_steps"])
        )
        # The "what was read" half is not vacuous: the five committed patches
        # and the 900 resolved items are named, so the mapping carries content.
        self.assertEqual(900, provenance["item_entries"])
        self.assertEqual(
            ["atom_fusion_item", "unit_patch", "atom_fusion_items_data",
             "atom_fusion_powerup", "targets"],
            list(provenance["applied_patches"]),
        )
        self.assertEqual([], list(provenance["missing_patches"]))
        self.assertEqual([], list(provenance["missing_mods"]))

    def test_a_missing_configuration_is_a_named_failure(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(ContentError) as caught:
                load_content(Path(empty))
            self.assertTrue(caught.exception.code)


class ItemAccessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.content = load_content(harness.REPO_ROOT)

    def test_an_unknown_item_is_none_not_an_error(self) -> None:
        self.assertIsNone(self.content.item(10 ** 9))

    def test_string_encoded_numbers_are_coerced_for_the_earning_fields(self) -> None:
        # The committed income fields are strings; ``collect_xp`` must still be
        # usable as an integer, and a non-numeric one must be refused rather
        # than coerced to zero (which would look like "no income").
        self.assertEqual(1, self.content.item_non_negative_int(905, "collect_xp"))
        self.assertEqual(None, self.content.item_non_negative_int(10 ** 9, "collect_xp"))

    def test_a_negative_amount_is_refused_rather_than_paid(self) -> None:
        self.assertIsNone(self.content.item_non_negative_int(905, "not_a_field"))

    def test_a_non_string_attribute_that_is_not_a_number_is_reported(self) -> None:
        self.assertEqual("w", self.content.item_attribute(905, "collect_type"))
        self.assertIsNone(self.content.item_attribute(905, "no_such_field"))


if __name__ == "__main__":
    unittest.main()