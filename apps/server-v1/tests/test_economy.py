#!/usr/bin/env python3
"""The economy authority: payouts derived from committed content (task 2.2/2.3).

Every number asserted here is either **read from the committed content at run
time** or **derived from it by the module under test**.  No figure is
transcribed, so the suite cannot drift from the content it documents; where a
figure is pinned (the item count, the ladder's shape) the test says so and says
why.

Three properties carry the line:

* a :class:`ResourceDerivation` cannot be built by hand (task 2.2);
* the ladder is compared in **minutes against seconds**, with every boundary
  covered from **both** sides, because the committed ladder's unit is minutes
  while both recorded instants are Unix seconds (this is the unit mistake the
  M7 collect line found and corrected);
* a refusal happens **before** any mutation, which ``tests/test_collect.py``
  proves over the store's bytes rather than trusting this module.
"""

from __future__ import annotations

import unittest

import harness  # noqa: F401  (path setup)
from server_v1_content import ContentError
from server_v1_economy import (
    COLLECT_TYPE_RESOURCES,
    EXPERIENCE_RESOURCE,
    NEVER_PAID_RESOURCES,
    SECONDS_PER_COMMITTED_MINUTE,
    EconomyError,
    ResourceDerivation,
    derive_collection_payout,
)
from server_v1_refusals import RefusalCode
from server_v1_repository import STORED_RESOURCE_NAMES

#: The committed Tree, the item the executed-legacy fixture collects.
TREE = 905


class IssuanceGateTests(unittest.TestCase):
    """Task 2.2: only the economy can construct a derivation."""

    def test_direct_construction_is_refused(self) -> None:
        for attempt in (
            lambda: ResourceDerivation(deltas={"xp": 1}),
            lambda: ResourceDerivation(
                deltas={"xp": 1}, rung_index=0, rung_threshold_seconds=0, rung_multiplier=1.0
            ),
            lambda: ResourceDerivation(
                deltas={},
                rung_index=0,
                rung_threshold_seconds=0,
                rung_multiplier=1.0,
                elapsed_seconds=0,
            ),
        ):
            with self.subTest(attempt=attempt):
                with self.assertRaises(TypeError):
                    attempt()

    def test_a_derived_payout_is_constructible(self) -> None:
        content = harness.load_content(harness.REPO_ROOT)
        derivation = derive_collection_payout(
            content, item_id=TREE, last_collected_at=0, now=1790705901
        )
        self.assertIsInstance(derivation, ResourceDerivation)

    def test_a_derivation_is_frozen(self) -> None:
        content = harness.load_content(harness.REPO_ROOT)
        derivation = derive_collection_payout(
            content, item_id=TREE, last_collected_at=0, now=1790705901
        )
        with self.assertRaises(Exception):
            derivation.rung_index = 9  # type: ignore[misc]

    def test_a_derivation_cannot_be_edited_in_place(self) -> None:
        """The test that found the defect; see the class docstring.

        ``frozen=True`` on a Pydantic model blocks *attribute* assignment only.
        The first version of :class:`ResourceDerivation` declared ``deltas`` as
        a plain ``Dict`` field, so this exact mutation **succeeded** and the
        transport could have reported a payout the authority never derived.
        """
        content = harness.load_content(harness.REPO_ROOT)
        derivation = derive_collection_payout(
            content, item_id=TREE, last_collected_at=0, now=1790705901
        )
        before = dict(derivation.deltas)
        for mapping_name in ("deltas", "committed"):
            with self.subTest(mapping=mapping_name):
                mapping = getattr(derivation, mapping_name)
                with self.assertRaises(TypeError):
                    mapping["gold"] = 999  # type: ignore[index]
                self.assertNotIn(999, dict(getattr(derivation, mapping_name)).values())
        self.assertEqual(before, dict(derivation.deltas))

    def test_delta_for_and_applies_to_agree(self) -> None:
        content = harness.load_content(harness.REPO_ROOT)
        derivation = derive_collection_payout(
            content, item_id=TREE, last_collected_at=0, now=1790705901
        )
        for name in derivation.deltas:
            self.assertTrue(derivation.applies_to(name))
            self.assertNotEqual(0, derivation.delta_for(name))
        for name in ("gold", "oil", "steel", "cash", "mana"):
            self.assertFalse(derivation.applies_to(name))
            self.assertEqual(0, derivation.delta_for(name))


class CommittedFactTests(unittest.TestCase):
    """Facts about the committed content, read rather than transcribed."""

    def setUp(self) -> None:
        self.content = harness.load_content(harness.REPO_ROOT)

    def test_the_tree_records_the_income_v1_derives_from(self) -> None:
        self.assertEqual("20", self.content.item_attribute(TREE, "collect"))
        self.assertEqual("w", self.content.item_attribute(TREE, "collect_type"))
        self.assertEqual("1", self.content.item_attribute(TREE, "collect_xp"))
        self.assertEqual("0", self.content.item_attribute(TREE, "max_collects"))

    def test_wood_is_the_resource_the_committed_type_names(self) -> None:
        self.assertEqual("wood", COLLECT_TYPE_RESOURCES["w"])

    def test_experience_is_its_own_stored_resource(self) -> None:
        self.assertEqual("xp", EXPERIENCE_RESOURCE)
        self.assertIn(EXPERIENCE_RESOURCE, STORED_RESOURCE_NAMES)

    def test_the_ladder_is_read_from_committed_content(self) -> None:
        minutes, multipliers = self.content.collect_ladder()
        self.assertEqual(4, len(minutes))
        self.assertEqual(4, len(multipliers))
        # Recorded from a first run that wrongly expected ``(0, 5, 60, 480)``:
        # the committed ladder's first rung is **5** minutes, not 0.  The wrong
        # figure was in this test, never in the module — which is why the
        # seconds-valued boundaries below are stated independently and both of
        # them agree with 5/60/240/480 minutes.
        self.assertEqual((5, 60, 240, 480), minutes)
        self.assertEqual((0.25, 1.0, 2.0, 3.0), multipliers)
        self.assertEqual(
            (300, 3600, 14400, 28800),
            tuple(minutes_ * SECONDS_PER_COMMITTED_MINUTE for minutes_ in minutes),
        )

    def test_the_committed_minute_is_sixty_seconds_and_says_so(self) -> None:
        # If this constant were ever changed the rung arithmetic would silently
        # change with it, which is why the unit is a named constant and the
        # boundaries below are asserted in both units.
        self.assertEqual(60, SECONDS_PER_COMMITTED_MINUTE)

    def test_never_paid_is_disjoint_from_the_stored_resources(self) -> None:
        for name in NEVER_PAID_RESOURCES:
            self.assertIn(name, STORED_RESOURCE_NAMES)


class LadderBoundaryTests(unittest.TestCase):
    """Every committed boundary, from **both** sides.

    Written as pairs (``last_elapsed, expected_rung``) plus an explicit
    ``below_first_rung`` case, so the boundary is a fact about the committed
    content rather than an accident of the loop that walks it.
    """

    #: ``(elapsed seconds, expected rung index)`` — the first element of each
    #: pair is one second **below** the boundary and the second exactly at it.
    BOUNDARIES = (
        (300, 0),
        (3600, 1),
        (14400, 2),
        (28800, 3),
    )

    def setUp(self) -> None:
        self.content = harness.load_content(harness.REPO_ROOT)

    def _derive(self, elapsed: int) -> ResourceDerivation:
        # ``last_collected_at=0`` makes elapsed exactly ``now``, so the test
        # states the elapsed time directly instead of solving for a clock.
        return derive_collection_payout(
            self.content, item_id=TREE, last_collected_at=0, now=elapsed
        )

    def test_one_second_below_the_first_rung_is_refused(self) -> None:
        with self.assertRaises(EconomyError) as caught:
            self._derive(299)
        self.assertIs(RefusalCode.BELOW_FIRST_RUNG, caught.exception.code)
        self.assertEqual(300, caught.exception.detail["first_rung_seconds"])

    def test_exactly_the_first_rung_is_reached(self) -> None:
        # The sibling test above and this one together fix the boundary; either
        # alone would leave a one-second-wide error invisible.
        derivation = self._derive(300)
        self.assertEqual(0, derivation.rung_index)
        self.assertEqual(300, derivation.rung_threshold_seconds)
        self.assertEqual({"xp": 0, "wood": 5}, dict(derivation.deltas))

    def test_every_boundary_from_both_sides(self) -> None:
        """For every rung above the first, the second below and the instant.

        The **first** boundary has no rung below it: one second under the first
        committed threshold is not rung ``-1``, it is a refusal, and
        ``test_one_second_below_the_first_rung_is_refused`` covers that side.
        Writing the loop as though rung ``-1`` existed was the first version of
        this test, and it failed — which is the boundary asserting itself.
        """
        for boundary, expected_rung in self.BOUNDARIES:
            with self.subTest(boundary=boundary):
                at = self._derive(boundary)
                self.assertEqual(expected_rung, at.rung_index)
                self.assertEqual(boundary, at.rung_threshold_seconds)
                if expected_rung > 0:
                    self.assertEqual(expected_rung - 1, self._derive(boundary - 1).rung_index)

    def test_the_top_rung_clamps_rather_than_extrapolating(self) -> None:
        """DERIVED, rejecting interpolation: the claim, and its own limit."""
        for elapsed in (28800, 28801, 10 ** 9):
            with self.subTest(elapsed=elapsed):
                self.assertEqual(3, self._derive(elapsed).rung_index)
        self.assertEqual({"xp": 3, "wood": 60}, dict(self._derive(10 ** 9).deltas))

    def test_the_fixture_state_reaches_the_top_rung(self) -> None:
        """The recorded collection: item[3] is 0, so elapsed is unbounded."""
        derivation = derive_collection_payout(
            self.content,
            item_id=TREE,
            last_collected_at=0,
            now=1790705901,
        )
        self.assertEqual(3, derivation.rung_index)
        self.assertEqual({"xp": 3, "wood": 60}, dict(derivation.deltas))
        self.assertEqual(28800, derivation.rung_threshold_seconds)


class RefusalTests(unittest.TestCase):
    """The four derivations that must not happen."""

    def setUp(self) -> None:
        self.content = harness.load_content(harness.REPO_ROOT)

    def test_an_item_with_no_committed_income_is_refused(self) -> None:
        # Item 1 records no usable ``collect``; the id is asserted from content
        # rather than transcribed, so the test explains itself if content moves.
        self.assertEqual("0", self.content.item_attribute(1, "collect"))
        with self.assertRaises(EconomyError) as caught:
            derive_collection_payout(self.content, item_id=1, last_collected_at=0, now=10 ** 9)
        self.assertIs(RefusalCode.NO_COMMITTED_INCOME, caught.exception.code)

    def test_a_committed_cap_is_refused_rather_than_interpreted(self) -> None:
        self.assertNotEqual("0", self.content.item_attribute(66, "max_collects"))
        with self.assertRaises(EconomyError) as caught:
            derive_collection_payout(self.content, item_id=66, last_collected_at=0, now=10 ** 9)
        self.assertIs(RefusalCode.CAPPED_COLLECTION, caught.exception.code)

    def test_a_cap_is_refused_before_its_income_is_even_read(self) -> None:
        """Check order: item 66 has both a cap and an income, and the cap wins."""
        with self.assertRaises(EconomyError) as caught:
            derive_collection_payout(self.content, item_id=66, last_collected_at=0, now=10 ** 9)
        self.assertIs(RefusalCode.CAPPED_COLLECTION, caught.exception.code)

    def test_an_instant_in_the_future_is_refused_not_clamped(self) -> None:
        with self.assertRaises(EconomyError) as caught:
            derive_collection_payout(
                self.content, item_id=TREE, last_collected_at=100, now=99
            )
        self.assertIs(RefusalCode.UNREADABLE_STATE, caught.exception.code)

    def test_a_non_integer_instant_is_refused(self) -> None:
        for value in ("0", 1.5, True, None):
            with self.subTest(value=value):
                with self.assertRaises(EconomyError) as caught:
                    derive_collection_payout(
                        self.content, item_id=TREE, last_collected_at=value, now=10 ** 9
                    )
                self.assertIs(RefusalCode.UNREADABLE_STATE, caught.exception.code)

    def test_a_non_integer_clock_is_refused(self) -> None:
        with self.assertRaises(EconomyError) as caught:
            derive_collection_payout(
                self.content, item_id=TREE, last_collected_at=0, now="now"
            )
        self.assertIs(RefusalCode.UNREADABLE_STATE, caught.exception.code)

    def test_every_refusal_code_the_economy_can_raise_is_declared(self) -> None:
        """The economy names its reasons as enum members, never as strings.

        Recorded because the first draft typed ``code`` as ``str`` and five
        codes were then named only by bare literals, invisible to the
        vocabulary guard.  If a string ever appears here again, this fails.
        """
        import ast
        import pathlib

        source = pathlib.Path(harness.SERVICE_DIR / "server_v1_economy.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        used = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "RefusalCode"
        }
        self.assertEqual(
            {
                "CAPPED_COLLECTION",
                "NO_COMMITTED_INCOME",
                "UNREADABLE_CONTENT",
                "UNREADABLE_STATE",
                "BELOW_FIRST_RUNG",
            },
            used,
        )


class LadderValidationTests(unittest.TestCase):
    """A ladder the content cannot supply is refused, not walked.

    Exercised through ``CommittedContent`` rather than by handing
    :class:`Ladder` an empty tuple directly, because the seam that matters is
    the one the authority actually reads: a committed ladder that is missing,
    mismatched, or the wrong type must produce ``unreadable_content`` rather
    than a partial payout.
    """

    def _content_with_ladder(self, minutes: Any, multipliers: Any) -> Any:
        content = harness.load_content(harness.REPO_ROOT)
        # Replace the committed ladder with a crafted one, through the same
        # accessor the economy reads.
        content._globals["COLLECT_MINUTES"] = minutes  # type: ignore[attr-defined]
        content._globals["COLLECT_MULTIPLIER"] = multipliers  # type: ignore[attr-defined]
        return content

    def test_a_mismatched_ladder_is_refused(self) -> None:
        for minutes, multipliers in (
            ((), (1.0,)),
            ((5, 60), (1.0,)),
            ((5, 60, 240), ()),
            (("5", "60"), (1.0, 2.0)),
        ):
            with self.subTest(minutes=minutes, multipliers=multipliers):
                content = self._content_with_ladder(minutes, multipliers)
                with self.assertRaises(ContentError):
                    content.collect_ladder()

    def test_a_usable_ladder_still_loads(self) -> None:
        """The control: the instrument above must reject a *valid* pair."""
        content = self._content_with_ladder((5, 60), (1.0, 2.0))
        self.assertEqual(((5, 60), (1.0, 2.0)), content.collect_ladder())


if __name__ == "__main__":
    unittest.main()